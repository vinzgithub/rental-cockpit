# Copyright © 2026 Vincent Fournet
"""Shared services and request helpers of the web application."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from .access import Access, access_for
from .config import Config
from .database import Database, Registry
from .engine.demo import build_demo
from .engine.errors import RCError
from .security import LoginThrottle, csrf_valid, looks_like_recovery_code, recovery_code_hash, totp_match

_LOGGER = logging.getLogger("rental_cockpit")

STATIC = Path(__file__).parent / "static"
DATASETS = ("real", "demo")
MAX_JSON_BYTES = 1024 * 1024
STATUS = {"forbidden": 403, "forbidden_property": 403, "forbidden_documents": 403, "login_required": 401,
          "csrf_failed": 403, "not_found": 404, "login_locked": 429, "stale_revision": 409,
          "preview_stale": 409, "upload_too_large": 413, "password_change_required": 403, "backup_too_large": 413}

MFA_PENDING_SECONDS = 300


def content_security_policy(frame_ancestors: str = "") -> str:
    """Strict policy: nothing inline, nothing from elsewhere. Framing only when explicitly allowed."""
    ancestors = f"'self' {frame_ancestors}" if frame_ancestors else "'none'"
    return ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
            f"connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors {ancestors}")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Services:
    """What the request handlers share: configuration, database, registries."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.db = Database(config.db_path)
        self.registries = {
            "real": Registry(self.db, "real"),
            "demo": Registry(self.db, "demo", factory=lambda: build_demo(self.today())),
        }
        self.registries["real"].load(create=True, now=utc_now())
        self.registries["demo"].load(create=False, now=utc_now())
        self.throttle = LoginThrottle()

    @staticmethod
    def today() -> date:
        """Today in the time zone of the process (``TZ``), never a hard-coded one."""
        return date.today()


# --------------------------------------------------------------------------- request helpers

def lang_of(request: Request, payload: dict[str, Any] | None = None) -> str:
    value = (payload or {}).get("lang") or request.query_params.get("lang") or ""
    if not value:
        value = request.headers.get("accept-language", "")
    return "fr" if str(value).lower().startswith("fr") else "en"


def error_response(err: RCError, lang: str) -> JSONResponse:
    return JSONResponse({"code": err.code, "message": err.message(lang)}, status_code=STATUS.get(err.code, 400))


async def read_json(request: Request) -> dict[str, Any]:
    if int(request.headers.get("content-length") or 0) > MAX_JSON_BYTES:
        raise RCError("upload_too_large", limit="1 Mio")
    try:
        payload = await request.json()
    except ValueError as exc:
        raise RCError("choice_invalid", field="body") from exc
    if not isinstance(payload, dict):
        raise RCError("choice_invalid", field="body")
    return payload


def require_csrf(request: Request) -> None:
    if not csrf_valid(request.session, request.headers.get("x-csrf-token")):
        raise RCError("csrf_failed")


def current_user(services: Services, request: Request):
    """The signed-in account, or a 401. A changed password ends other sessions."""
    uid = request.session.get("uid")
    user = services.db.user_by_id(int(uid)) if uid else None
    if user is None or request.session.get("sv") != user["session_version"]:
        request.session.pop("uid", None)
        raise RCError("login_required")
    return user


def dataset_of(value: Any) -> str:
    return value if value in DATASETS else "real"


def access(services: Services, user: Any, dataset: str) -> Access:
    if user["must_change_password"]:
        raise RCError("password_change_required")  # a temporary password opens nothing but the password change
    registry = services.registries[dataset]
    grants = services.db.grants_for(int(user["id"])) if user["role"] != "admin" else {}
    return access_for(user, grants, registry.snapshot(), dataset)


def period_from(params: Any) -> tuple[date, date]:
    try:
        start, end = date.fromisoformat(str(params.get("start"))), date.fromisoformat(str(params.get("end")))
    except ValueError as exc:
        raise RCError("date_format") from exc
    if end <= start or (end - start).days > 3700:
        raise RCError("date_range")
    return start, end


def scope(acc: Access, property_id: str | None) -> set[str]:
    """Properties asked for, restricted to what the caller may see (SEC 02)."""
    if property_id in (None, "", "all"):
        return set(acc.property_ids)
    acc.require_property(property_id)
    return {property_id}


def public_property(prop: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "name", "kind", "capacity", "bedrooms", "currency", "timezone", "activity_start", "unavailable", "archived", "note", "updated_at")
    return {key: prop.get(key) for key in keys}


def public_user(user: Any) -> dict[str, Any]:
    return {"id": user["id"], "username": user["username"], "name": user["display_name"] or user["username"],
            "role": user["role"], "is_admin": user["role"] == "admin", "mfa": bool(user["totp_secret"])}


def login_session(request: Request, user: Any) -> None:
    """Start a fresh signed-in session (the CSRF token is renewed too)."""
    request.session.clear()
    request.session.update(uid=int(user["id"]), sv=int(user["session_version"]))


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"




def check_second_factor(services: "Services", user: Any, code: str) -> bool:
    """A current authenticator code (each accepted once) or an unused recovery code."""
    if not user["totp_secret"]:
        return False
    step = totp_match(user["totp_secret"], code, int(user["totp_last_step"]))
    if step is not None:
        services.db.set_totp_step(int(user["id"]), step)
        return True
    if looks_like_recovery_code(code):
        return services.db.use_recovery_code(int(user["id"]), recovery_code_hash(code), utc_now())
    return False
