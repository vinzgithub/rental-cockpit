# Copyright © 2026 Vincent Fournet
"""Command line helpers for whoever runs the server (lost phone, forgotten password, backups).

    python -m rental_cockpit.cli reset-password <username>
    python -m rental_cockpit.cli disable-mfa <username>
    python -m rental_cockpit.cli backup
    python -m rental_cockpit.cli restore <backup.zip>
    python -m rental_cockpit.cli restore - [--yes] < backup.zip

With Docker:  docker exec -it rental-cockpit python -m rental_cockpit.cli disable-mfa <username>
The first two sign out every browser of the account. Stop the application
before ``restore`` (see docs/fr/sauvegarde.md): it replaces « Mes données ».
With ``-`` the backup is read from standard input, so the container never
needs the right to read a file of the host: the first run only checks it,
the same command with ``--yes`` restores it.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .database import Database
from .security import MIN_PASSWORD_LENGTH, hash_password

RESTORE_MAX_BYTES = 8 * 1024 ** 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m rental_cockpit.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("reset-password", help="set a new password for an account").add_argument("username")
    sub.add_parser("disable-mfa", help="turn off two-factor sign-in (lost phone and recovery codes)").add_argument("username")
    sub.add_parser("backup", help="write a backup of « Mes données » in backups/ of the data folder")
    restore = sub.add_parser("restore", help="check a backup, then replace « Mes données » with it (application stopped)")
    restore.add_argument("file", help='the backup ZIP, or "-" to read it from standard input')
    restore.add_argument("--yes", action="store_true", help="restore without asking to type the confirmation word")
    args = parser.parse_args(argv)
    if args.command in ("backup", "restore"):
        return _backup_command(args)

    db = Database(Config.from_env().db_path)
    user = db.user_by_name(args.username)
    if user is None:
        print(f"Unknown user: {args.username}", file=sys.stderr)
        return 1
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if args.command == "reset-password":
        password = getpass.getpass("New password: ")
        if len(password) < MIN_PASSWORD_LENGTH:
            print(f"Password too short (at least {MIN_PASSWORD_LENGTH} characters).", file=sys.stderr)
            return 1
        if password != getpass.getpass("Confirm: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
        db.set_password(int(user["id"]), hash_password(password), now)
        print("Password updated. Every browser has been signed out.")
    else:
        if not user["totp_secret"]:
            print("Two-factor sign-in is not on for this account.")
            return 0
        db.disable_totp(int(user["id"]), now)
        print("Two-factor sign-in turned off. Every browser has been signed out.")
        print("Sign in with the password, then turn it on again in Settings.")
    return 0


def _backup_command(args: argparse.Namespace) -> int:
    import shutil

    from .admin_routes import apply_restore, make_backup, same_figures
    from .backup import inspect_backup
    from .engine.errors import RCError
    from .storage import BlobStore
    from .web import Services

    config = Config.from_env()
    services = Services(config)
    services.blob_stores = {dataset: BlobStore(config.documents_dir(dataset)) for dataset in ("real", "demo")}
    try:
        if args.command == "backup":
            made = make_backup(services, label="rental-cockpit-sauvegarde", created_by="cli")
            print(f"Backup written: {config.data_dir / 'backups' / made['name']} ({made['size']} bytes, {made['documents']} PDF)")
            if made["missing_documents"]:
                print(f"Warning: {made['missing_documents']} PDF missing from private storage.", file=sys.stderr)
            print("It holds private data: keep it safe.")
            return 0
        staging = config.data_dir / "restore-staging" / "cli"
        shutil.rmtree(staging, ignore_errors=True)
        (config.data_dir / "restore-staging").mkdir(mode=0o700, parents=True, exist_ok=True)
        staging.mkdir(mode=0o700)
        if args.file == "-":
            source = staging / "upload.zip"
            if not _copy_stdin(source, RESTORE_MAX_BYTES):
                print(f"Backup larger than {RESTORE_MAX_BYTES // 1024 ** 3} GiB: nothing was restored.", file=sys.stderr)
                shutil.rmtree(staging, ignore_errors=True)
                return 1
        else:
            source = Path(args.file)
            try:
                source.open("rb").close()
            except OSError as exc:
                print(f"Cannot read {args.file}: {exc.strerror or exc}. Nothing was restored.", file=sys.stderr)
                print("With Docker, pass the backup on standard input instead (see docs/en/backup.md):", file=sys.stderr)
                print("  docker compose run --rm -T rental-cockpit python -m rental_cockpit.cli restore - < backup.zip", file=sys.stderr)
                shutil.rmtree(staging, ignore_errors=True)
                return 1
        summary = inspect_backup(source, staging / "staged", max_bytes=RESTORE_MAX_BYTES)
        if args.file == "-":
            source.unlink(missing_ok=True)  # the staged copy is all that is needed now
        print(f"Backup of {summary['created_at']} (version {summary['app_version']}, schema {summary['schema']}): checked.")
        print("  " + ", ".join(f"{k}: {v}" for k, v in summary["counts"].items() if v))
        print(f"  PDF: {summary['documents']}, properties: {', '.join(summary['properties']) or '-'}")
        if not args.yes and args.file == "-":
            print("Nothing was restored yet. To replace « Mes données » with this backup, run the same command again with --yes.")
            shutil.rmtree(staging, ignore_errors=True)
            return 1
        if not args.yes and input("Type REMPLACER to replace « Mes données » with this backup: ").strip() not in ("REMPLACER", "REPLACE"):
            print("Nothing was restored.")
            shutil.rmtree(staging, ignore_errors=True)
            return 1
        result = apply_restore(services, staging / "staged", created_by="cli")
        shutil.rmtree(staging, ignore_errors=True)
        print(f"Restored. The data replaced were saved first: backups/{result['safety_backup']}")
        print("Same totals as the backup." if same_figures(result, summary) else "Warning: totals differ from the backup.")
        print("Start the application again.")
        return 0
    except RCError as err:
        shutil.rmtree(config.data_dir / "restore-staging" / "cli", ignore_errors=True)
        print(err.message("en"), file=sys.stderr)
        return 1


def _copy_stdin(target: Path, limit: int) -> bool:
    """Copy the archive given on standard input to ``target`` (0600); False if it is larger than ``limit``."""
    import os

    size = 0
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        while chunk := sys.stdin.buffer.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                return False
            out.write(chunk)
    return True


if __name__ == "__main__":
    raise SystemExit(main())
