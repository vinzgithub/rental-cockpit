# Copyright © 2026 Vincent Fournet
"""SQLite storage: accounts, rights and the two registries (real and demo).

One file, ``rental_cockpit.db``, in the data folder:

``users``       accounts of the application (no default account: the first
                visit creates the administrator);
``grants``      which properties a reader may see, and whether they may open
                PDF documents (a separate permission, SEC 02);
``registries``  the business registry of each dataset as one JSON document,
                with a revision number.

A change to a registry follows one path: lock, copy, apply the operation to
the copy, write it in a single SQLite transaction, then publish the copy in
memory. If anything fails, the previous state stays in memory and on disk:
an operation is either fully saved or not at all.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Iterator

from .engine.errors import RCError
from .engine.migrations import migrate
from .engine.schema import empty_registry

DB_SCHEMA = 1

_TABLES = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'reader')),
    must_change_password INTEGER NOT NULL DEFAULT 0,
    totp_secret TEXT,
    totp_last_step INTEGER NOT NULL DEFAULT 0,
    session_version INTEGER NOT NULL DEFAULT 1,
    language TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS grants (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    property_id TEXT NOT NULL,
    documents INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, property_id)
);
CREATE TABLE IF NOT EXISTS recovery_codes (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash TEXT NOT NULL,
    used_at TEXT,
    PRIMARY KEY (user_id, code_hash)
);
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_used_at TEXT,
    revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS registries (
    dataset TEXT PRIMARY KEY CHECK (dataset IN ('real', 'demo')),
    revision INTEGER NOT NULL,
    body TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink():
            raise RuntimeError("Refusing a symbolic link for the database")
        with self.connect() as db:
            db.executescript(_TABLES)
            db.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('schema', ?)", (str(DB_SCHEMA),))
        path.chmod(0o600)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise

    # ------------------------------------------------------------ accounts

    def count_users(self) -> int:
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def user_by_id(self, user_id: int) -> sqlite3.Row | None:
        with self.connect() as db:
            return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def user_by_name(self, username: str) -> sqlite3.Row | None:
        with self.connect() as db:
            return db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    def create_first_admin(self, username: str, display_name: str, password_hash: str, now: str) -> int | None:
        """Create the administrator only if no account exists yet (atomic check)."""
        with self.transaction() as db:
            if db.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                return None
            cursor = db.execute(
                "INSERT INTO users(username, display_name, password_hash, role, created_at, updated_at) VALUES (?, ?, ?, 'admin', ?, ?)",
                (username, display_name, password_hash, now, now),
            )
            return int(cursor.lastrowid)

    def set_password(self, user_id: int, password_hash: str, now: str) -> int:
        """New password; every other session ends (returns the new session version)."""
        with self.transaction() as db:
            db.execute("UPDATE users SET password_hash = ?, must_change_password = 0, session_version = session_version + 1, updated_at = ? WHERE id = ?",
                       (password_hash, now, user_id))
            return int(db.execute("SELECT session_version FROM users WHERE id = ?", (user_id,)).fetchone()[0])

    def enable_totp(self, user_id: int, secret: str, step: int, code_hashes: list[str], now: str) -> int:
        """Turn on two-factor sign-in with fresh recovery codes; other sessions end."""
        with self.transaction() as db:
            db.execute("UPDATE users SET totp_secret = ?, totp_last_step = ?, session_version = session_version + 1, updated_at = ? WHERE id = ?",
                       (secret, step, now, user_id))
            db.execute("DELETE FROM recovery_codes WHERE user_id = ?", (user_id,))
            db.executemany("INSERT INTO recovery_codes(user_id, code_hash) VALUES (?, ?)", [(user_id, h) for h in code_hashes])
            return int(db.execute("SELECT session_version FROM users WHERE id = ?", (user_id,)).fetchone()[0])

    def disable_totp(self, user_id: int, now: str) -> int:
        with self.transaction() as db:
            db.execute("UPDATE users SET totp_secret = NULL, totp_last_step = 0, session_version = session_version + 1, updated_at = ? WHERE id = ?",
                       (now, user_id))
            db.execute("DELETE FROM recovery_codes WHERE user_id = ?", (user_id,))
            return int(db.execute("SELECT session_version FROM users WHERE id = ?", (user_id,)).fetchone()[0])

    def replace_recovery_codes(self, user_id: int, code_hashes: list[str]) -> None:
        with self.transaction() as db:
            db.execute("DELETE FROM recovery_codes WHERE user_id = ?", (user_id,))
            db.executemany("INSERT INTO recovery_codes(user_id, code_hash) VALUES (?, ?)", [(user_id, h) for h in code_hashes])

    def use_recovery_code(self, user_id: int, code_hash: str, now: str) -> bool:
        """Consume one recovery code; ``False`` if unknown or already used (single use)."""
        with self.transaction() as db:
            cursor = db.execute("UPDATE recovery_codes SET used_at = ? WHERE user_id = ? AND code_hash = ? AND used_at IS NULL",
                                (now, user_id, code_hash))
            return cursor.rowcount == 1

    def recovery_codes_left(self, user_id: int) -> int:
        with self.connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM recovery_codes WHERE user_id = ? AND used_at IS NULL", (user_id,)).fetchone()[0])

    # ------------------------------------------------------------ API keys (read-only, for Home Assistant)

    def create_api_key(self, user_id: int, name: str, token_hash: str, now: str) -> int:
        with self.transaction() as db:
            cursor = db.execute("INSERT INTO api_keys(user_id, name, token_hash, created_at) VALUES (?, ?, ?, ?)", (user_id, name, token_hash, now))
            return int(cursor.lastrowid)

    def list_api_keys(self, user_id: int) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute("SELECT id, name, created_at, last_used_at FROM api_keys WHERE user_id = ? AND revoked_at IS NULL ORDER BY id",
                              (user_id,)).fetchall()
        return [dict(row) for row in rows]

    def revoke_api_key(self, user_id: int, key_id: int, now: str) -> bool:
        with self.transaction() as db:
            cursor = db.execute("UPDATE api_keys SET revoked_at = ? WHERE id = ? AND user_id = ? AND revoked_at IS NULL", (now, key_id, user_id))
            return cursor.rowcount == 1

    def user_for_api_key(self, token_hash: str, now: str) -> sqlite3.Row | None:
        """The account behind a valid, non-revoked key (and note when it was used)."""
        with self.transaction() as db:
            row = db.execute("SELECT id, user_id FROM api_keys WHERE token_hash = ? AND revoked_at IS NULL", (token_hash,)).fetchone()
            if row is None:
                return None
            db.execute("UPDATE api_keys SET last_used_at = ? WHERE id = ?", (now, row["id"]))
            return db.execute("SELECT * FROM users WHERE id = ?", (row["user_id"],)).fetchone()

    def set_totp_step(self, user_id: int, step: int) -> None:
        with self.transaction() as db:
            db.execute("UPDATE users SET totp_last_step = ? WHERE id = ? AND totp_last_step < ?", (step, user_id, step))

    def grants_for(self, user_id: int) -> dict[str, bool]:
        with self.connect() as db:
            rows = db.execute("SELECT property_id, documents FROM grants WHERE user_id = ?", (user_id,)).fetchall()
        return {row["property_id"]: bool(row["documents"]) for row in rows}

    # ------------------------------------------------------------ registries

    def load_registry(self, dataset: str) -> tuple[dict[str, Any] | None, int]:
        with self.connect() as db:
            row = db.execute("SELECT body, revision FROM registries WHERE dataset = ?", (dataset,)).fetchone()
        if row is None:
            return None, 0
        return json.loads(row["body"]), int(row["revision"])

    def save_registry(self, dataset: str, data: dict[str, Any], expected_revision: int, now: str) -> int:
        """Write a registry if nobody else changed it since ``expected_revision``."""
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        try:
            with self.transaction() as db:
                row = db.execute("SELECT revision FROM registries WHERE dataset = ?", (dataset,)).fetchone()
                current = int(row["revision"]) if row else 0
                if current != expected_revision:
                    raise RCError("stale_revision")
                db.execute(
                    "INSERT INTO registries(dataset, revision, body, updated_at) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(dataset) DO UPDATE SET revision = excluded.revision, body = excluded.body, updated_at = excluded.updated_at",
                    (dataset, current + 1, body, now),
                )
                return current + 1
        except sqlite3.OperationalError as exc:
            if "full" in str(exc).lower():
                raise RCError("storage_full") from exc
            raise RCError("storage_failed", detail="database") from exc


class Registry:
    """One dataset's registry, cached in memory, changed all-or-nothing."""

    def __init__(self, db: Database, dataset: str, factory: Callable[[], dict[str, Any]] = empty_registry) -> None:
        self.db = db
        self.dataset = dataset
        self.factory = factory
        self.lock = RLock()
        self.data: dict[str, Any] | None = None
        self.revision = 0

    @property
    def exists(self) -> bool:
        return self.data is not None

    def load(self, *, create: bool, now: str) -> None:
        with self.lock:
            raw, revision = self.db.load_registry(self.dataset)
            if raw is None:
                if create:
                    data = self.factory()
                    self.revision = self.db.save_registry(self.dataset, data, 0, now)
                    self.data = data
                return
            data, changed = migrate(raw)
            self.data, self.revision = data, revision
            if changed:
                self.revision = self.db.save_registry(self.dataset, data, revision, now)

    def _refresh_if_changed(self, now: str) -> None:
        _, revision = self.db.load_registry(self.dataset) if self.data is not None else (None, 0)
        if revision != self.revision:
            self.load(create=False, now=now)

    def mutate(self, operation: Callable[[dict[str, Any]], Any], now: str) -> Any:
        with self.lock:
            self._refresh_if_changed(now)
            if self.data is None:
                raise RCError("not_found")
            work = deepcopy(self.data)
            result = operation(work)
            self.revision = self.db.save_registry(self.dataset, work, self.revision, now)
            self.data = work
            return result

    def replace(self, data: dict[str, Any], now: str) -> None:
        with self.lock:
            _, current = self.db.load_registry(self.dataset)
            self.revision = self.db.save_registry(self.dataset, data, current, now)
            self.data = data

    def snapshot(self) -> dict[str, Any]:
        """The current registry; callers must treat it as read-only."""
        return self.data or {}
