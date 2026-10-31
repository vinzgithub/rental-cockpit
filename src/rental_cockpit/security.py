# Copyright © 2026 Vincent Fournet
"""Password hashing, CSRF, login throttling and TOTP helpers (standard library only).

Same choices as the author's other self-hosted tools: scrypt for passwords,
a per-session CSRF token, a lock after repeated failures, and RFC 6238 codes
for the optional two-factor login (switched on from the settings screen).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import struct
import time
from threading import Lock
from urllib.parse import quote, urlencode

_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
MIN_PASSWORD_LENGTH = 10
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,40}$")

TOTP_PERIOD = 30
TOTP_DIGITS = 6
TOTP_WINDOW = 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_hex, digest_hex = stored.split("$")
        if algo != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), dklen=32, n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


# A dummy hash so that an unknown user name takes as long as a wrong password.
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def csrf_token(session: dict) -> str:
    token = session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf"] = token
    return token


def csrf_valid(session: dict, provided: str | None) -> bool:
    expected = session.get("csrf")
    return bool(expected and provided and hmac.compare_digest(expected, provided))


class LoginThrottle:
    """After ``max_failures`` failures from one address, refuse attempts for ``lock_seconds``."""

    def __init__(self, max_failures: int = 5, lock_seconds: int = 300) -> None:
        self.max_failures = max_failures
        self.lock_seconds = lock_seconds
        self._state: dict[str, tuple[int, float]] = {}
        self._lock = Lock()

    def locked(self, key: str) -> bool:
        with self._lock:
            failures, until = self._state.get(key, (0, 0.0))
            return failures >= self.max_failures and time.monotonic() < until

    def failure(self, key: str) -> None:
        with self._lock:
            failures, until = self._state.get(key, (0, 0.0))
            if failures >= self.max_failures and time.monotonic() >= until:
                failures = 0
            self._state[key] = (failures + 1, time.monotonic() + self.lock_seconds)

    def success(self, key: str) -> None:
        with self._lock:
            self._state.pop(key, None)


# ----------------------------------------------------------------- TOTP (RFC 6238)

def new_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def totp_at(secret: str, step: int) -> str:
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    mac = hmac.new(key, struct.pack(">Q", step), "sha1").digest()
    offset = mac[-1] & 0x0F
    value = struct.unpack(">I", mac[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**TOTP_DIGITS).zfill(TOTP_DIGITS)


def totp_match(secret: str, code: str, last_step: int, now: float | None = None) -> int | None:
    """Time step of ``code`` if valid and newer than ``last_step`` (each code works once)."""
    code = re.sub(r"\s", "", code or "")
    if not re.fullmatch(rf"\d{{{TOTP_DIGITS}}}", code):
        return None
    current = int((time.time() if now is None else now) // TOTP_PERIOD)
    found = None
    for step in range(current - TOTP_WINDOW, current + TOTP_WINDOW + 1):
        if hmac.compare_digest(totp_at(secret, step), code) and step > last_step:
            found = step
    return found


TOTP_ISSUER = "Rental Cockpit"
RECOVERY_CODE_COUNT = 10
_RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/o, 1/l/i


def totp_uri(secret: str, account: str) -> str:
    """The ``otpauth://`` link shown as a QR code to authenticator apps."""
    label = quote(f"{TOTP_ISSUER}:{account}", safe="")
    query = urlencode({"secret": secret, "issuer": TOTP_ISSUER, "algorithm": "SHA1", "digits": TOTP_DIGITS, "period": TOTP_PERIOD}, quote_via=quote)
    return f"otpauth://totp/{label}?{query}"


def new_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    """Single-use codes such as ``k7m2q-x9fhr`` (about 50 bits each)."""
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def recovery_code_hash(code: str) -> str:
    normalized = re.sub(r"[^a-z0-9]", "", (code or "").lower())
    return hashlib.sha256(normalized.encode()).hexdigest()


def looks_like_recovery_code(code: str) -> bool:
    return len(re.sub(r"[^a-z0-9]", "", (code or "").lower())) == 10


def new_api_token() -> str:
    """A read-only API key: shown once, stored only as its SHA-256 hash."""
    return "rc_" + secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
