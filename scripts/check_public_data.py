# Copyright © 2026 Vincent Fournet
"""Refuse a commit that would publish personal data (SEC 07).

Scans every file tracked by git (text files only) for patterns that should
never appear in a public repository: e-mail addresses, private IP addresses,
IBANs, phone numbers, tokens and private keys. Images are checked for embedded
text metadata. Exit code 1 lists every finding.

Usage:  python scripts/check_public_data.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS = {
    "e-mail address": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "private IPv4 address": re.compile(r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b"),
    "IBAN": re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){3,7}\b"),
    "French phone number": re.compile(r"(?<![\d.])(?:\+33 ?|0)[1-9](?:[ .-]?\d{2}){4}(?!\d)"),
    "JSON Web Token": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
ALLOWED = {
    "e-mail address": {"noreply@github.com"},
}
TEXT_SUFFIXES = {".py", ".js", ".css", ".html", ".md", ".txt", ".toml", ".yml", ".yaml", ".json", ".svg", ".cfg", ".ini", ""}
SKIP = {"src/rental_cockpit/static/fonts/OFL-inter.txt", "src/rental_cockpit/static/fonts/OFL-source-serif-4.txt"}


def tracked_files() -> list[Path]:
    output = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout
    return [ROOT / name for name in output.decode().split("\0") if name]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        relative = path.relative_to(ROOT).as_posix()
        if relative in SKIP or not path.is_file():
            continue
        if path.suffix == ".png":
            data = path.read_bytes()
            for chunk in (b"tEXt", b"iTXt", b"zTXt", b"eXIf"):
                if chunk in data:
                    findings.append(f"{relative}: image carries a {chunk.decode()} metadata chunk")
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                if match.group(0) in ALLOWED.get(label, set()):
                    continue
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{relative}:{line}: {label}: {match.group(0)[:40]}")
    if findings:
        print("Personal data patterns found — nothing should be published as is:")
        print("\n".join(f"  {item}" for item in findings))
        return 1
    print("No personal data pattern found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
