# Copyright © 2026 Vincent Fournet
"""Command line helpers for whoever runs the server (lost phone, forgotten password).

    python -m rental_cockpit.cli reset-password <username>
    python -m rental_cockpit.cli disable-mfa <username>

With Docker:  docker exec -it rental-cockpit python -m rental_cockpit.cli disable-mfa <username>
Both commands sign out every browser of the account.
"""
from __future__ import annotations

import argparse
import getpass
import sys
from datetime import datetime, timezone

from .config import Config
from .database import Database
from .security import MIN_PASSWORD_LENGTH, hash_password


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m rental_cockpit.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("reset-password", help="set a new password for an account").add_argument("username")
    sub.add_parser("disable-mfa", help="turn off two-factor sign-in (lost phone and recovery codes)").add_argument("username")
    args = parser.parse_args(argv)

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


if __name__ == "__main__":
    raise SystemExit(main())
