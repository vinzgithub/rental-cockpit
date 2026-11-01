# Copyright © 2026 Vincent Fournet
"""Rental Cockpit web application.

Run with::

    uvicorn --factory rental_cockpit.app:create_app --host 0.0.0.0 --port 8080

The application serves its own interface (static files) and a JSON API under
``/api``. It needs nothing else: no Home Assistant, no account elsewhere, no
outbound connection. Data lives in the folder given by
``RENTAL_COCKPIT_DATA_DIR``.

Every API request goes through the same checks: signed session cookie, CSRF
token on changes, rights resolved on the server for the requested dataset.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

from . import __version__
from .account_routes import register_account_routes
from .config import Config, secret_key
from .engine import indicators
from .engine.demo import build_demo
from .engine.errors import RCError, render
from .engine.ledger import Ledger
from .engine.schema import category_label
from .entry_routes import register_entry_routes
from .ha_api import register_ha_routes
from .import_routes import register_import_routes
from .security import (
    DUMMY_HASH,
    MIN_PASSWORD_LENGTH,
    USERNAME_RE,
    csrf_token,
    hash_password,
    verify_password,
)
from .stay_routes import register_stay_routes
from .supplier_routes import register_supplier_routes
from .web import (
    MFA_PENDING_SECONDS,
    STATIC,
    Services,
    access,
    check_second_factor,
    client_key,
    content_security_policy,
    current_user,
    dataset_of,
    error_response,
    lang_of,
    login_session,
    period_from,
    public_property,
    public_user,
    read_json,
    require_csrf,
    scope,
    utc_now,
)

_LOGGER = logging.getLogger("rental_cockpit")


# --------------------------------------------------------------------------- application

def create_app(config: Config | None = None) -> FastAPI:
    config = config or Config.from_env()
    services = Services(config)
    app = FastAPI(title="Rental Cockpit", version=__version__, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.services = services
    app.add_middleware(SessionMiddleware, secret_key=secret_key(config.data_dir), session_cookie="rental_cockpit_session",
                       max_age=config.session_max_age, same_site="strict", https_only=config.cookie_secure)

    csp = content_security_policy(config.frame_ancestors)

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Callable):
        response: Response = await call_next(request)
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if not config.frame_ancestors:
            response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(RCError)
    async def on_rc_error(request: Request, err: RCError):
        return error_response(err, lang_of(request))

    index_html = (STATIC / "index.html").read_text(encoding="utf-8").replace("{{VERSION}}", __version__)
    app.mount(f"/assets/{__version__}", StaticFiles(directory=STATIC), name="assets")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(index_html, headers={"Cache-Control": "no-cache"})

    @app.get("/favicon.svg")
    async def favicon() -> FileResponse:
        return FileResponse(STATIC / "favicon.svg", media_type="image/svg+xml")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    # ------------------------------------------------------------------ session and accounts

    @app.get("/api/session")
    async def session_info(request: Request) -> dict[str, Any]:
        token = csrf_token(request.session)
        base = {"version": __version__, "csrf": token, "today": services.today().isoformat(), "default_locale": config.default_locale}
        if not services.db.count_users():
            return {**base, "authenticated": False, "setup_required": True}
        try:
            user = current_user(services, request)
        except RCError:
            return {**base, "authenticated": False, "setup_required": False, "mfa_pending": bool(request.session.get("mfa_uid"))}
        real = services.registries["real"].snapshot()
        demo = services.registries["demo"].data
        acc = access(services, user, "real")
        return {
            **base, "authenticated": True, "setup_required": False, "user": public_user(user),
            "real": {"first_choice": real.get("settings", {}).get("first_choice"), "properties": len(acc.property_ids),
                     "onboarding": real.get("settings", {}).get("onboarding", {})},
            "demo": {"exists": demo is not None, "focus": (demo or {}).get("settings", {}).get("demo_focus")},
        }

    @app.post("/api/auth/setup")
    async def setup(request: Request) -> dict[str, Any]:
        """First visit: create the administrator. Refused as soon as one account exists."""
        require_csrf(request)
        payload = await read_json(request)
        username = str(payload.get("username") or "").strip()
        password = str(payload.get("password") or "")
        if not USERNAME_RE.fullmatch(username):
            raise RCError("username_invalid")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise RCError("password_too_short", min=MIN_PASSWORD_LENGTH)
        if password != str(payload.get("confirm") or ""):
            raise RCError("password_mismatch")
        display = str(payload.get("display_name") or "").strip()[:60]
        user_id = await run_in_threadpool(services.db.create_first_admin, username, display, hash_password(password), utc_now())
        if user_id is None:
            raise RCError("setup_done")
        user = services.db.user_by_id(user_id)
        login_session(request, user)
        _LOGGER.info("Administrator account created")
        return {"ok": True, "csrf": csrf_token(request.session)}

    @app.post("/api/auth/login")
    async def login(request: Request) -> dict[str, Any]:
        """Step 1: user name and password. With two-factor sign-in, step 2 asks for a code."""
        require_csrf(request)
        key = client_key(request)
        if services.throttle.locked(key):
            raise RCError("login_locked")
        payload = await read_json(request)
        user = services.db.user_by_name(str(payload.get("username") or "").strip())
        password = str(payload.get("password") or "")
        valid = await run_in_threadpool(verify_password, password, user["password_hash"] if user else DUMMY_HASH)
        if not user or not valid:
            services.throttle.failure(key)
            raise RCError("login_failed")
        if user["totp_secret"]:
            # The password is right; the session only remembers that for a few minutes,
            # and nothing is readable until the code is checked.
            request.session.clear()
            request.session.update(mfa_uid=int(user["id"]), mfa_sv=int(user["session_version"]), mfa_at=time.time())
            return {"ok": False, "mfa_required": True, "csrf": csrf_token(request.session)}
        services.throttle.success(key)
        login_session(request, user)
        return {"ok": True, "csrf": csrf_token(request.session)}

    @app.post("/api/auth/mfa")
    async def login_code(request: Request) -> dict[str, Any]:
        """Step 2: the authenticator code, or one single-use recovery code."""
        require_csrf(request)
        key = client_key(request)
        if services.throttle.locked(key):
            raise RCError("login_locked")
        uid, started = request.session.get("mfa_uid"), float(request.session.get("mfa_at") or 0)
        user = services.db.user_by_id(int(uid)) if uid else None
        if user is None or not user["totp_secret"] or time.time() - started > MFA_PENDING_SECONDS \
                or request.session.get("mfa_sv") != user["session_version"]:
            request.session.clear()
            raise RCError("mfa_expired")
        payload = await read_json(request)
        if not check_second_factor(services, user, str(payload.get("code") or "")):
            services.throttle.failure(key)
            raise RCError("totp_invalid")
        services.throttle.success(key)
        login_session(request, user)
        return {"ok": True, "csrf": csrf_token(request.session)}

    @app.post("/api/auth/logout")
    async def logout(request: Request) -> dict[str, Any]:
        require_csrf(request)
        request.session.clear()
        return {"ok": True, "csrf": csrf_token(request.session)}

    # ------------------------------------------------------------------ getting started

    @app.post("/api/start")
    async def start(request: Request) -> dict[str, Any]:
        """« Utiliser mes données » or « Découvrir avec des données fictives » (UX 02).

        The demo is built in its own registry: nothing is injected into real data."""
        require_csrf(request)
        user = current_user(services, request)
        payload = await read_json(request)
        choice = payload.get("choice")
        if choice not in ("own_data", "demo"):
            raise RCError("choice_invalid", field="choice")
        acc = access(services, user, "real")
        if choice == "demo" and services.registries["demo"].data is None:
            acc.require_admin()
            data = await run_in_threadpool(build_demo, services.today())
            services.registries["demo"].replace(data, utc_now())
        if acc.is_admin:
            def choose(work: dict[str, Any]) -> dict[str, Any]:
                if not work["settings"].get("first_choice"):
                    work["settings"]["first_choice"] = choice
                Ledger(work, acc.user_id).audit("start", choice)
                return {"first_choice": work["settings"]["first_choice"]}
            result = services.registries["real"].mutate(choose, utc_now())
        else:
            result = {"first_choice": services.registries["real"].snapshot().get("settings", {}).get("first_choice")}
        demo = services.registries["demo"].data
        return {**result, "demo": {"exists": demo is not None, "focus": (demo or {}).get("settings", {}).get("demo_focus")}}

    @app.post("/api/demo/reset")
    async def demo_reset(request: Request) -> dict[str, Any]:
        require_csrf(request)
        access(services, current_user(services, request), "real").require_admin()
        data = await run_in_threadpool(build_demo, services.today())
        services.registries["demo"].replace(data, utc_now())
        return {"focus": data["settings"]["demo_focus"]}

    # ------------------------------------------------------------------ overview

    @app.get("/api/overview")
    async def overview(request: Request) -> dict[str, Any]:
        """Everything the « Synthèse » screen shows, for one period and one reading."""
        params = request.query_params
        lang = lang_of(request)
        dataset = dataset_of(params.get("dataset"))
        user = current_user(services, request)
        acc = access(services, user, dataset)
        registry = services.registries[dataset]
        if not registry.exists:
            raise RCError("not_found")
        start, end = period_from(params)
        mode = params.get("mode") if params.get("mode") in indicators.MODES else "activity"
        selected = scope(acc, params.get("property_id"))
        data = registry.snapshot()
        result = await run_in_threadpool(lambda: indicators.compute(data, property_ids=selected, start=start, end=end, mode=mode,
                                                                    lang=lang, today=services.today()))
        visible = [public_property(p) for pid, p in data["properties"].items() if pid in acc.property_ids]
        categories = [{"id": c["id"], "kind": c["kind"], "treatment": c["treatment"], "label": category_label(c, lang)}
                      for c in data.get("categories", {}).values()]
        return {**result, "role": acc.role, "dataset": dataset, "categories": categories,
                "properties": sorted(visible, key=lambda p: (p["archived"], p["name"].casefold())),
                "settings": {k: data["settings"].get(k) for k in ("currency", "first_choice", "onboarding", "demo_focus", "demo")}}

    @app.get("/api/indicator")
    async def indicator(request: Request) -> dict[str, Any]:
        """« Comment est calculé ce montant ? » with the exact lines behind it (UX 05)."""
        params = request.query_params
        lang = lang_of(request)
        dataset = dataset_of(params.get("dataset"))
        acc = access(services, current_user(services, request), dataset)
        start, end = period_from(params)
        mode = params.get("mode") if params.get("mode") in indicators.MODES else "activity"
        selected = scope(acc, params.get("property_id"))
        data = services.registries[dataset].snapshot()
        try:
            return await run_in_threadpool(lambda: indicators.indicator_detail(
                data, str(params.get("indicator")), property_ids=selected, start=start, end=end, mode=mode, lang=lang, today=services.today()))
        except KeyError as exc:
            raise RCError("not_found") from exc

    # ------------------------------------------------------------------ properties

    @app.post("/api/properties")
    async def create_property(request: Request) -> dict[str, Any]:
        require_csrf(request)
        payload = await read_json(request)
        dataset = dataset_of(payload.get("dataset"))
        acc = access(services, current_user(services, request), dataset)
        acc.require_admin()
        fields = {key: payload[key] for key in ("name", "kind", "capacity", "bedrooms", "activity_start", "address", "note", "currency") if key in payload}

        def apply(work: dict[str, Any]) -> dict[str, Any]:
            ledger = Ledger(work, acc.user_id)
            return ledger.once(payload.get("op_id"), lambda: ledger.create_property(fields))

        return services.registries[dataset].mutate(apply, utc_now())

    register_account_routes(app, services)
    register_ha_routes(app, services)
    register_stay_routes(app, services)
    register_import_routes(app, services)
    register_entry_routes(app, services)
    register_supplier_routes(app, services)

    @app.exception_handler(Exception)
    async def on_unexpected(request: Request, err: Exception):  # pragma: no cover - defensive
        _LOGGER.exception("Unexpected error on %s", request.url.path)
        lang = lang_of(request)
        return JSONResponse({"code": "unknown", "message": render("unknown", {}, lang)}, status_code=500)

    return app
