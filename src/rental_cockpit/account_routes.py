# Copyright © 2026 Vincent Fournet
"""« Mon compte » : password, two-factor sign-in (TOTP) and read-only API keys.

Every change here asks for the current password again (and, to turn
two-factor sign-in off, a valid code), counts in the sign-in throttle, and
signs out every other browser of the account.
"""
from __future__ import annotations

import time
from typing import Any

import segno
from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool

from .engine.errors import RCError
from .security import (
    MIN_PASSWORD_LENGTH,
    hash_password,
    new_api_token,
    new_recovery_codes,
    new_totp_secret,
    recovery_code_hash,
    token_hash,
    totp_match,
    totp_uri,
    verify_password,
)
from .web import Services, check_second_factor, client_key, current_user, public_user, read_json, require_csrf, utc_now

MFA_SETUP_SECONDS = 600
MAX_API_KEYS = 10


def register_account_routes(app: FastAPI, services: Services) -> None:
    db = services.db

    async def confirm_password(request: Request, user: Any, password: str) -> None:
        key = client_key(request)
        if services.throttle.locked(key):
            raise RCError("login_locked")
        if not await run_in_threadpool(verify_password, password, user["password_hash"]):
            services.throttle.failure(key)
            raise RCError("password_wrong")

    def keep_this_session(request: Request, session_version: int) -> None:
        """Other browsers are signed out; this one stays signed in."""
        request.session["sv"] = session_version

    @app.get("/api/account")
    async def account(request: Request) -> dict[str, Any]:
        user = current_user(services, request)
        uid = int(user["id"])
        return {
            "user": public_user(user),
            "mfa": {"enabled": bool(user["totp_secret"]), "recovery_left": db.recovery_codes_left(uid) if user["totp_secret"] else 0},
            "keys": db.list_api_keys(uid),
            "min_password_length": MIN_PASSWORD_LENGTH,
        }

    @app.post("/api/account/password")
    async def change_password(request: Request) -> dict[str, Any]:
        require_csrf(request)
        user = current_user(services, request)
        payload = await read_json(request)
        await confirm_password(request, user, str(payload.get("current") or ""))
        new = str(payload.get("new") or "")
        if len(new) < MIN_PASSWORD_LENGTH:
            raise RCError("password_too_short", min=MIN_PASSWORD_LENGTH)
        if new != str(payload.get("confirm") or ""):
            raise RCError("password_mismatch")
        version = db.set_password(int(user["id"]), await run_in_threadpool(hash_password, new), utc_now())
        keep_this_session(request, version)
        return {"ok": True}

    # ------------------------------------------------------------------ two-factor sign-in

    @app.post("/api/account/mfa/start")
    async def mfa_start(request: Request) -> dict[str, Any]:
        """Step 1 of turning it on: password, then a new secret shown as a QR code.

        The secret only lives in the signed session until a first code proves
        the authenticator app has it; nothing is stored before that."""
        require_csrf(request)
        user = current_user(services, request)
        if user["totp_secret"]:
            raise RCError("mfa_already")
        payload = await read_json(request)
        await confirm_password(request, user, str(payload.get("password") or ""))
        secret = new_totp_secret()
        request.session["mfa_setup"] = {"secret": secret, "at": time.time()}
        uri = totp_uri(secret, user["username"])
        qr = segno.make(uri, error="m").svg_data_uri(scale=5, border=2, dark="#04211f", light="#ffffff")
        return {"uri": uri, "qr": qr, "secret": " ".join(secret[i:i + 4] for i in range(0, len(secret), 4))}

    @app.post("/api/account/mfa/enable")
    async def mfa_enable(request: Request) -> dict[str, Any]:
        """Step 2: a first valid code turns it on and gives ten single-use recovery codes."""
        require_csrf(request)
        user = current_user(services, request)
        setup = request.session.get("mfa_setup") or {}
        if not setup or time.time() - float(setup.get("at", 0)) > MFA_SETUP_SECONDS:
            request.session.pop("mfa_setup", None)
            raise RCError("mfa_setup_expired")
        payload = await read_json(request)
        step = totp_match(setup["secret"], str(payload.get("code") or ""), 0)
        if step is None:
            services.throttle.failure(client_key(request))
            raise RCError("totp_invalid")
        codes = new_recovery_codes()
        version = db.enable_totp(int(user["id"]), setup["secret"], step, [recovery_code_hash(c) for c in codes], utc_now())
        request.session.pop("mfa_setup", None)
        keep_this_session(request, version)
        return {"ok": True, "recovery_codes": codes}

    @app.post("/api/account/mfa/disable")
    async def mfa_disable(request: Request) -> dict[str, Any]:
        require_csrf(request)
        user = current_user(services, request)
        if not user["totp_secret"]:
            raise RCError("mfa_not_enabled")
        payload = await read_json(request)
        await confirm_password(request, user, str(payload.get("password") or ""))
        if not check_second_factor(services, user, str(payload.get("code") or "")):
            services.throttle.failure(client_key(request))
            raise RCError("totp_invalid")
        keep_this_session(request, db.disable_totp(int(user["id"]), utc_now()))
        return {"ok": True}

    @app.post("/api/account/mfa/recovery")
    async def mfa_new_codes(request: Request) -> dict[str, Any]:
        """Ten new recovery codes; the previous ones stop working."""
        require_csrf(request)
        user = current_user(services, request)
        if not user["totp_secret"]:
            raise RCError("mfa_not_enabled")
        payload = await read_json(request)
        await confirm_password(request, user, str(payload.get("password") or ""))
        if not check_second_factor(services, user, str(payload.get("code") or "")):
            services.throttle.failure(client_key(request))
            raise RCError("totp_invalid")
        codes = new_recovery_codes()
        db.replace_recovery_codes(int(user["id"]), [recovery_code_hash(c) for c in codes])
        return {"ok": True, "recovery_codes": codes}

    # ------------------------------------------------------------------ API keys

    @app.post("/api/account/keys")
    async def create_key(request: Request) -> dict[str, Any]:
        """A read-only key for Home Assistant: shown once, stored only as a hash.

        It reads what its account may read, nothing more, and can change nothing."""
        require_csrf(request)
        user = current_user(services, request)
        payload = await read_json(request)
        name = " ".join(str(payload.get("name") or "").split())
        if not 1 <= len(name) <= 60:
            raise RCError("api_key_name")
        if len(db.list_api_keys(int(user["id"]))) >= MAX_API_KEYS:
            raise RCError("api_key_limit")
        token = new_api_token()
        key_id = db.create_api_key(int(user["id"]), name, token_hash(token), utc_now())
        return {"id": key_id, "name": name, "token": token}

    @app.delete("/api/account/keys/{key_id}")
    async def revoke_key(request: Request, key_id: int) -> dict[str, Any]:
        require_csrf(request)
        user = current_user(services, request)
        if not db.revoke_api_key(int(user["id"]), key_id, utc_now()):
            raise RCError("not_found")
        return {"ok": True}
