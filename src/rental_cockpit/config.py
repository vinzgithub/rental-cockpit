# Copyright © 2026 Vincent Fournet
"""Runtime configuration, read from environment variables.

Nothing here has a personal default: no address, no time zone, no account.
The time zone is the one of the process (``TZ`` in Docker), so the product
works the same anywhere in the world.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    data_dir: Path
    cookie_secure: bool = False
    default_locale: str = "fr"
    session_max_age: int = 7 * 24 * 3600

    @property
    def db_path(self) -> Path:
        """Accounts, rights and both registries (real and demo)."""
        return self.data_dir / "rental_cockpit.db"

    def documents_dir(self, dataset: str) -> Path:
        """Private PDF originals, named by their SHA-256. Never served as static files."""
        return self.data_dir / ("documents" if dataset == "real" else "demo-documents")

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            data_dir=Path(os.environ.get("RENTAL_COCKPIT_DATA_DIR", "./data")),
            cookie_secure=_bool(os.environ.get("RENTAL_COCKPIT_COOKIE_SECURE"), False),
            default_locale=os.environ.get("RENTAL_COCKPIT_DEFAULT_LOCALE", "fr"),
            session_max_age=int(os.environ.get("RENTAL_COCKPIT_SESSION_MAX_AGE", str(7 * 24 * 3600))),
        )


def secret_key(data_dir: Path) -> str:
    """Session signing key, generated on first start and kept in the data folder (mode 0600)."""
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = data_dir / ".secret_key"
    if path.is_symlink():
        raise RuntimeError("Refusing a symbolic link for the session key")
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    key = secrets.token_urlsafe(48)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(key)
    return key
