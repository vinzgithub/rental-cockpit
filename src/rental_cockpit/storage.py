# Copyright © 2026 Vincent Fournet
"""Private storage of the PDF originals (PDF 05).

Each original is kept once, named by its SHA-256, in a directory readable by
the application only (0700, files 0600), outside anything served as static
files. Writing is exclusive and synced before the registry records the
document; a file whose content no longer matches its name is never served.
Files left behind by an interrupted save are removed at start-up (DUP 03).
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from .engine.errors import RCError

_SHA = re.compile(r"[0-9a-f]{64}")


class BlobStore:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def path(self, sha: str) -> Path:
        if not _SHA.fullmatch(sha or ""):
            raise RCError("not_found")
        if self.directory.is_symlink():
            raise RCError("document_missing_blob")
        path = self.directory / f"{sha}.pdf"
        if path.is_symlink():
            raise RCError("document_missing_blob")
        return path

    def exists(self, sha: str) -> bool:
        return self.path(sha).is_file()

    def write(self, sha: str, raw: bytes) -> bool:
        """Store ``raw`` under its fingerprint. Returns ``True`` when the file is new."""
        if hashlib.sha256(raw).hexdigest() != sha:
            raise RCError("document_integrity")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.directory, 0o700)
        path = self.path(sha)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except FileExistsError:
            if hashlib.sha256(path.read_bytes()).hexdigest() == sha:
                return False
            path.unlink()  # a damaged copy is replaced by the verified bytes
            return self.write(sha, raw)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return True

    def read(self, sha: str, limit: int) -> bytes:
        """The original, checked against its fingerprint before it leaves the server."""
        path = self.path(sha)
        if not path.is_file():
            raise RCError("document_missing_blob")
        with open(path, "rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit or hashlib.sha256(raw).hexdigest() != sha:
            raise RCError("document_integrity")
        return raw

    def remove(self, sha: str) -> None:
        self.path(sha).unlink(missing_ok=True)

    def cleanup(self, referenced: set[str]) -> list[str]:
        """Remove originals no document refers to any more (an interrupted save, a deleted document)."""
        if not self.directory.is_dir() or self.directory.is_symlink():
            return []
        removed = []
        for item in self.directory.iterdir():
            name = item.name
            if item.is_symlink() or not item.is_file():
                continue
            sha = name[:-4] if name.endswith(".pdf") else ""
            if _SHA.fullmatch(sha) and sha not in referenced:
                item.unlink(missing_ok=True)
                removed.append(sha)
        return removed
