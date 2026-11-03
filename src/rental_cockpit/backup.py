# Copyright © 2026 Vincent Fournet
"""Backup and restore of « Mes données » (SAU 01, SAU 02).

A backup is one ZIP file:

``manifest.json``   format, application version, schema, date, counts, totals
                    and the SHA-256 of every other file of the archive;
``registry.json``   the business registry (properties, stays, entries,
                    payments, suppliers, documents, history…);
``accounts.json``   the accounts and their rights, by name — never a
                    password, a two-factor secret or an API key;
``documents/``      the private PDF originals, named by their SHA-256.

Restoring never writes straight away: the archive is first unpacked in a
staging folder of the data folder (« copie de recette »), every file is
checked against the manifest, the registry is migrated and validated, every
PDF is checked against its fingerprint and the totals are recomputed. Only
after an explicit confirmation is the current data saved to a new backup,
then replaced. The demo is never part of a backup: it is rebuilt on demand.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from . import __version__
from .engine.errors import RCError
from .engine.migrations import SchemaTooNew, migrate
from .engine.schema import COLLECTIONS, SCHEMA_VERSION
from .storage import BlobStore

FORMAT = "rental-cockpit-backup"
FORMAT_VERSION = 1
MAX_PDF = 8 * 1024 * 1024
MAX_JSON = 256 * 1024 * 1024
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,120}\.zip")
DOCUMENT = re.compile(r"documents/([0-9a-f]{64})\.pdf")
NOTICE = ("Cette sauvegarde contient des données privées (montants, séjours, factures PDF). Conservez-la à l'abri.",
          "This backup holds private data (amounts, stays, PDF invoices). Keep it safe.")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fingerprint(data: dict[str, Any]) -> dict[str, Any]:
    """Counts and totals compared after a restore: the same data gives the same figures (T11)."""
    entries = data.get("entries", {}).values()
    stays = data.get("stays", {}).values()
    return {
        "counts": {name: len(data.get(name, {})) for name in COLLECTIONS if isinstance(data.get(name), dict)},
        "totals": {
            "expenses": sum(e["amount"] for e in entries if e["kind"] == "expense" and not e.get("archived") and not e.get("superseded_by")),
            "income": sum(e["amount"] for e in entries if e["kind"] == "income" and not e.get("archived") and not e.get("superseded_by")),
            "payments": sum(p.get("amount", 0) for p in data.get("payments", {}).values()),
            "stays_gross": sum(int((s.get("amounts") or {}).get("gross") or 0) for s in stays if s.get("status") != "cancelled"),
        },
    }


def backups_dir(data_dir: Path) -> Path:
    folder = Path(data_dir) / "backups"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(folder, 0o700)
    return folder


def list_backups(data_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for item in backups_dir(data_dir).iterdir():
        if item.is_file() and not item.is_symlink() and NAME.fullmatch(item.name):
            stat = item.stat()
            kind = "before_restore" if item.name.startswith("avant-restauration") else "manual"
            rows.append({"name": item.name, "size": stat.st_size, "kind": kind, "modified": int(stat.st_mtime)})
    return sorted(rows, key=lambda r: r["modified"], reverse=True)


def backup_path(data_dir: Path, name: str) -> Path:
    if not NAME.fullmatch(str(name or "")):
        raise RCError("not_found")
    path = backups_dir(data_dir) / name
    if path.is_symlink() or not path.is_file():
        raise RCError("not_found")
    return path


def create_backup(data: dict[str, Any], accounts: list[dict[str, Any]], store: BlobStore, target: Path, *,
                  now: str, created_by: str) -> dict[str, Any]:
    """Write a complete, self-checked backup to ``target`` (a new file, mode 0600)."""
    data = deepcopy(data)
    files: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    tmp = target.with_name(target.name + ".part")
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as stream, zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            def put(name: str, raw: bytes, compress: bool = True) -> None:
                archive.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), raw,
                                 compress_type=zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED)
                files[name] = {"sha256": _sha(raw), "size": len(raw)}

            put("registry.json", json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
            put("accounts.json", json.dumps(accounts, ensure_ascii=False, indent=1).encode("utf-8"))
            for sha in sorted({d.get("sha256", "") for d in data.get("documents", {}).values()}):
                try:
                    put(f"documents/{sha}.pdf", store.read(sha, MAX_PDF), compress=False)
                except RCError:
                    missing.append(sha)
            manifest = {
                "format": FORMAT, "format_version": FORMAT_VERSION, "app_version": __version__, "schema": data.get("schema"),
                "created_at": now, "created_by": created_by, "notice": {"fr": NOTICE[0], "en": NOTICE[1]},
                **fingerprint(data), "documents": len(data.get("documents", {})), "missing_documents": missing, "files": files,
            }
            archive.writestr(zipfile.ZipInfo("manifest.json", date_time=(2026, 1, 1, 0, 0, 0)),
                             json.dumps(manifest, ensure_ascii=False, indent=1).encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, target)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        if exc.errno == 28:  # ENOSPC
            raise RCError("storage_full") from exc
        raise RCError("storage_failed", detail="backup") from exc
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    # The archive just written is read back and checked like any backup to restore.
    with zipfile.ZipFile(target) as archive:
        bad = archive.testzip()
    if bad is not None:
        target.unlink(missing_ok=True)
        raise RCError("storage_failed", detail="backup")
    return {"name": target.name, "size": target.stat().st_size, "documents": len(files) - 2, "missing_documents": len(missing),
            **fingerprint(data), "created_at": now}


def inspect_backup(archive_path: Path, staging: Path, *, max_bytes: int) -> dict[str, Any]:
    """Unpack and check a backup in ``staging`` without touching the current data (SAU 02)."""
    def invalid(detail: str) -> RCError:
        return RCError("backup_invalid", detail=detail)

    try:
        archive = zipfile.ZipFile(archive_path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise invalid("ce n'est pas une archive ZIP lisible") from exc
    with archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise invalid("manifeste absent ou fichiers en double")
        if sum(i.file_size for i in infos) > max_bytes:
            raise invalid("contenu trop volumineux une fois décompressé")
        for info in infos:
            name = info.filename
            if name not in ("manifest.json", "registry.json", "accounts.json") and not DOCUMENT.fullmatch(name):
                raise invalid(f"fichier inattendu « {name[:80]} »")
            if info.flag_bits & 0x1:
                raise invalid("archive chiffrée")
        try:
            manifest = json.loads(archive.read("manifest.json"))
        except ValueError as exc:
            raise invalid("manifeste illisible") from exc
        if manifest.get("format") != FORMAT or int(manifest.get("format_version") or 0) != FORMAT_VERSION:
            raise invalid("ce n'est pas une sauvegarde Rental Cockpit")
        listed = manifest.get("files") or {}
        if set(listed) != set(names) - {"manifest.json"}:
            raise invalid("la liste des fichiers ne correspond pas au manifeste")
        staging.mkdir(mode=0o700, parents=True, exist_ok=True)
        docs = staging / "documents"
        docs.mkdir(mode=0o700, exist_ok=True)
        contents: dict[str, bytes] = {}
        for name, expected in listed.items():
            info = archive.getinfo(name)
            limit = MAX_PDF if name.startswith("documents/") else MAX_JSON
            if info.file_size > limit or info.file_size != int(expected.get("size", -1)):
                raise invalid(f"taille inattendue pour « {name} »")
            raw = archive.read(name)
            if _sha(raw) != expected.get("sha256"):
                raise invalid(f"empreinte différente pour « {name} » : fichier modifié ou abîmé")
            match = DOCUMENT.fullmatch(name)
            if match:
                if _sha(raw) != match.group(1):
                    raise invalid(f"le justificatif « {name} » ne correspond pas à son nom")
                BlobStore(docs).write(match.group(1), raw)
            else:
                contents[name] = raw
    try:
        raw_registry = json.loads(contents["registry.json"])
        accounts = json.loads(contents.get("accounts.json", b"[]"))
    except (KeyError, ValueError) as exc:
        raise invalid("données illisibles") from exc
    if not isinstance(raw_registry, dict) or not isinstance(accounts, list):
        raise invalid("données illisibles")
    try:
        data, migrated = migrate(raw_registry)
    except SchemaTooNew as exc:
        raise RCError("backup_schema_newer", schema=exc.schema) from exc
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise invalid("registre incohérent") from exc
    # Every document of the registry has its PDF, checked against its fingerprint.
    present = {p.name[:-4] for p in docs.iterdir()}
    missing = sorted({d.get("sha256", "") for d in data.get("documents", {}).values()} - present)
    known_missing = set(manifest.get("missing_documents") or [])
    if set(missing) - known_missing:
        raise invalid(f"{len(set(missing) - known_missing)} justificatif(s) absent(s) de l'archive")
    figures = fingerprint(raw_registry)
    same = figures["counts"] == manifest.get("counts") and figures["totals"] == manifest.get("totals")
    if not same:
        raise invalid("les totaux ne correspondent pas au manifeste")
    (staging / "registry.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (staging / "accounts.json").write_text(json.dumps(accounts, ensure_ascii=False), encoding="utf-8")
    return {
        "created_at": manifest.get("created_at", ""), "app_version": manifest.get("app_version", ""),
        "schema": int(raw_registry.get("schema") or 1), "schema_now": SCHEMA_VERSION, "migrated": migrated,
        "counts": figures["counts"], "totals": figures["totals"], "documents": len(present), "missing_documents": missing,
        "properties": sorted(p.get("name", "") for p in data.get("properties", {}).values()),
        "accounts": [{"username": str(a.get("username", "")), "role": a.get("role", "")} for a in accounts if isinstance(a, dict)],
    }


def apply_staged(staging: Path, documents_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Put the checked PDFs in place and return the registry and accounts to install.

    The folder of the current PDFs is kept aside until the caller confirms the
    registry was saved (``finish_swap``), so a failure can put it back.
    """
    data = json.loads((staging / "registry.json").read_text(encoding="utf-8"))
    accounts = json.loads((staging / "accounts.json").read_text(encoding="utf-8"))
    aside = documents_dir.with_name(documents_dir.name + ".before-restore")
    if aside.exists():
        shutil.rmtree(aside)
    if documents_dir.exists():
        os.replace(documents_dir, aside)
    os.replace(staging / "documents", documents_dir)
    os.chmod(documents_dir, 0o700)
    return data, accounts


def undo_swap(documents_dir: Path) -> None:
    aside = documents_dir.with_name(documents_dir.name + ".before-restore")
    if aside.exists():
        if documents_dir.exists():
            shutil.rmtree(documents_dir)
        os.replace(aside, documents_dir)


def finish_swap(documents_dir: Path) -> None:
    aside = documents_dir.with_name(documents_dir.name + ".before-restore")
    if aside.exists():
        shutil.rmtree(aside)
