# Copyright © 2026 Vincent Fournet
"""Administration API: reader accounts and their rights, backups and restore.

Administrators only, with the CSRF token on every change. A reader receives
a temporary password and chooses their own at the first sign-in; their
rights are given property by property, and access to the PDFs of a
property is a separate permission (SEC 02).

A backup is written in ``backups/`` of the data folder, then downloaded. A
restore is checked first in a staging folder and applied only after the
person types the confirmation word; the data replaced are saved in a new
backup just before (SAU 02).
"""
from __future__ import annotations

import os
import secrets
import shutil
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from . import backup
from .engine.errors import RCError
from .security import MIN_PASSWORD_LENGTH, USERNAME_RE, hash_password
from .web import Services, access, current_user, read_json, require_csrf, utc_now

RESTORE_SECONDS = 1800
CONFIRM_WORDS = {"REMPLACER", "REPLACE"}


def _max_backup_bytes() -> int:
    try:
        return max(1, int(os.environ.get("RENTAL_COCKPIT_MAX_BACKUP_MB", "2048"))) * 1024 * 1024
    except ValueError:
        return 2048 * 1024 * 1024


class Restores:
    """Backups checked and waiting for a confirmation, in a staging folder of the data folder."""

    def __init__(self, root: Path, clock=time.monotonic) -> None:
        self.root = root
        self.clock = clock
        self.items: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)  # leftovers of a previous run are never applied

    def folder(self, token: str) -> Path:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        return self.root / token

    def expire(self) -> None:
        with self.lock:
            limit = self.clock() - RESTORE_SECONDS
            for token in [t for t, item in self.items.items() if item["at"] < limit]:
                shutil.rmtree(self.items.pop(token)["folder"], ignore_errors=True)

    def add(self, token: str, owner: str, folder: Path, summary: dict[str, Any]) -> None:
        with self.lock:
            for old in [t for t, item in self.items.items() if item["owner"] == owner]:
                shutil.rmtree(self.items.pop(old)["folder"], ignore_errors=True)  # one pending restore per person
            self.items[token] = {"owner": owner, "folder": folder, "summary": summary, "at": self.clock()}

    def take(self, token: Any, owner: str) -> dict[str, Any]:
        self.expire()
        with self.lock:
            item = self.items.get(str(token or ""))
            if item is None or item["owner"] != owner:
                raise RCError("restore_expired")
            return self.items.pop(str(token))


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def same_figures(restored: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Same totals and same number of items (built-in categories added by a migration aside)."""
    def counts(figures: dict[str, Any]) -> dict[str, int]:
        return {k: v for k, v in figures["counts"].items() if k != "categories"}
    return restored["totals"] == expected["totals"] and counts(restored) == counts(expected)


def make_backup(services: Services, *, label: str, created_by: str) -> dict[str, Any]:
    """A backup of « Mes données » in ``backups/``, written while nobody can change them."""
    registry = services.registries["real"]
    store = services.blob_stores["real"]
    folder = backup.backups_dir(services.config.data_dir)
    with registry.lock:
        data = registry.snapshot()
        target = folder / f"{label}-{_stamp()}.zip"
        index = 1
        while target.exists():
            index += 1
            target = folder / f"{label}-{_stamp()}-{index}.zip"
        return backup.create_backup(data, services.db.export_accounts(), store, target, now=utc_now(), created_by=created_by)


def apply_restore(services: Services, folder: Path, *, created_by: str) -> dict[str, Any]:
    """Save the current data, then put the checked backup in their place. Raises before any change if it cannot."""
    registry = services.registries["real"]
    documents_dir = services.config.documents_dir("real")
    with registry.lock:
        safety = make_backup(services, label="avant-restauration", created_by=created_by)
        data, accounts = backup.apply_staged(folder, documents_dir)
        try:
            registry.replace(data, utc_now())
        except BaseException:
            backup.undo_swap(documents_dir)
            raise
        backup.finish_swap(documents_dir)
    grants = services.db.restore_grants(accounts, set(data.get("properties", {})))
    previews = getattr(services, "previews", None)
    if previews is not None:
        with previews.lock:
            previews.items = {t: i for t, i in previews.items.items() if i["dataset"] != "real"}
    shutil.rmtree(folder, ignore_errors=True)
    return {"safety_backup": safety["name"], **backup.fingerprint(data), "grants": grants}


def register_admin_routes(app: FastAPI, services: Services) -> None:
    restores = Restores(services.config.data_dir / "restore-staging")
    services.restores = restores

    def admin(request: Request):
        user = current_user(services, request)
        access(services, user, "real").require_admin()
        return user

    def properties() -> list[dict[str, Any]]:
        data = services.registries["real"].snapshot()
        return sorted(({"id": p["id"], "name": p["name"], "archived": bool(p.get("archived"))} for p in data.get("properties", {}).values()),
                      key=lambda p: (p["archived"], p["name"].casefold()))

    def read_grants(payload: dict[str, Any]) -> dict[str, bool]:
        known = {p["id"] for p in properties()}
        grants: dict[str, bool] = {}
        for item in payload.get("grants") or []:
            if isinstance(item, dict) and str(item.get("property_id")) in known:
                grants[str(item["property_id"])] = bool(item.get("documents"))
        return grants

    def users_view() -> dict[str, Any]:
        return {"users": services.db.list_users(), "properties": properties()}

    def reader_or_404(user_id: int) -> Any:
        target = services.db.user_by_id(user_id)
        if target is None or target["role"] != "reader":
            raise RCError("not_found")
        return target

    def checked_password(payload: dict[str, Any]) -> str:
        password = str(payload.get("password") or "")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise RCError("password_too_short", min=MIN_PASSWORD_LENGTH)
        return password

    # ------------------------------------------------------------------ reader accounts

    @app.get("/api/users")
    async def list_users(request: Request) -> dict[str, Any]:
        admin(request)
        return users_view()

    @app.post("/api/users")
    async def create_user(request: Request) -> dict[str, Any]:
        require_csrf(request)
        admin(request)
        payload = await read_json(request)
        username = str(payload.get("username") or "").strip()
        if not USERNAME_RE.fullmatch(username):
            raise RCError("username_invalid")
        password = checked_password(payload)
        display = " ".join(str(payload.get("display_name") or "").split())[:60]
        hashed = await run_in_threadpool(hash_password, password)
        await run_in_threadpool(services.db.create_reader, username, display, hashed, read_grants(payload), utc_now())
        return users_view()

    @app.patch("/api/users/{user_id}")
    async def update_user(request: Request, user_id: int) -> dict[str, Any]:
        require_csrf(request)
        admin(request)
        target = reader_or_404(user_id)
        payload = await read_json(request)
        display = " ".join(str(payload.get("display_name", target["display_name"]) or "").split())[:60]
        await run_in_threadpool(services.db.update_reader, user_id, display, read_grants(payload), utc_now())
        return users_view()

    @app.post("/api/users/{user_id}/password")
    async def reset_user_password(request: Request, user_id: int) -> dict[str, Any]:
        require_csrf(request)
        admin(request)
        reader_or_404(user_id)
        payload = await read_json(request)
        hashed = await run_in_threadpool(hash_password, checked_password(payload))
        await run_in_threadpool(services.db.reset_password, user_id, hashed, utc_now())
        return users_view()

    @app.delete("/api/users/{user_id}")
    async def delete_user(request: Request, user_id: int) -> dict[str, Any]:
        require_csrf(request)
        admin(request)
        reader_or_404(user_id)
        await run_in_threadpool(services.db.delete_reader, user_id)
        return users_view()

    # ------------------------------------------------------------------ backups

    @app.get("/api/backups")
    async def list_backups(request: Request) -> dict[str, Any]:
        admin(request)
        return {"backups": backup.list_backups(services.config.data_dir), "max_bytes": _max_backup_bytes()}

    @app.post("/api/backups")
    async def create_backup(request: Request) -> dict[str, Any]:
        require_csrf(request)
        user = admin(request)
        made = await run_in_threadpool(lambda: make_backup(services, label="rental-cockpit-sauvegarde", created_by=user["username"]))
        return {"backup": made, "backups": backup.list_backups(services.config.data_dir)}

    @app.get("/api/backups/{name}/file")
    async def download_backup(request: Request, name: str) -> FileResponse:
        admin(request)
        path = backup.backup_path(services.config.data_dir, name)
        return FileResponse(path, media_type="application/zip", filename=name,
                            headers={"Cache-Control": "no-store, private", "X-Content-Type-Options": "nosniff"})

    @app.delete("/api/backups/{name}")
    async def delete_backup(request: Request, name: str) -> dict[str, Any]:
        require_csrf(request)
        admin(request)
        backup.backup_path(services.config.data_dir, name).unlink()
        return {"backups": backup.list_backups(services.config.data_dir)}

    # ------------------------------------------------------------------ restore

    @app.post("/api/restore/check")
    async def check_restore(request: Request) -> dict[str, Any]:
        """Unpack and check a backup in a staging folder; the current data are not touched."""
        require_csrf(request)
        user = admin(request)
        limit = _max_backup_bytes()
        length = request.headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > limit):
            raise RCError("backup_too_large", limit=f"{limit // (1024 * 1024)} Mio")
        restores.expire()
        token = secrets.token_urlsafe(24)
        folder = restores.folder(token)
        folder.mkdir(mode=0o700)
        upload = folder / "upload.zip"
        size = 0
        try:
            with open(upload, "wb") as stream:
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > limit:
                        raise RCError("backup_too_large", limit=f"{limit // (1024 * 1024)} Mio")
                    stream.write(chunk)
            summary = await run_in_threadpool(backup.inspect_backup, upload, folder / "staged", max_bytes=limit * 4)
        except OSError as exc:
            shutil.rmtree(folder, ignore_errors=True)
            raise RCError("storage_full" if exc.errno == 28 else "storage_failed", detail="restore") from exc
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        upload.unlink(missing_ok=True)
        restores.add(token, str(user["id"]), folder, summary)
        current = backup.fingerprint(services.registries["real"].snapshot())
        return {"token": token, "expires_in": RESTORE_SECONDS, "backup": summary, "current": current}

    @app.post("/api/restore/apply")
    async def apply(request: Request) -> dict[str, Any]:
        require_csrf(request)
        user = admin(request)
        payload = await read_json(request)
        if str(payload.get("confirm") or "").strip() not in CONFIRM_WORDS:
            raise RCError("restore_confirm")
        item = restores.take(payload.get("token"), str(user["id"]))
        result = await run_in_threadpool(lambda: apply_restore(services, item["folder"] / "staged", created_by=user["username"]))
        shutil.rmtree(item["folder"], ignore_errors=True)
        result["same_totals"] = same_figures(result, item["summary"])
        return result
