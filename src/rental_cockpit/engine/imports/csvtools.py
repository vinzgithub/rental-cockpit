# Copyright © 2026 Vincent Fournet
"""Reading CSV files exported by other tools, without guessing silently.

Shared by the Airbnb reader and the generic CSV import: decoding (UTF-8 with
or without BOM, Windows-1252 as a stated fallback), delimiter detection,
header normalisation, day/month order inferred from unambiguous values,
amounts read to the cent. Nothing here writes anything.
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import date
from typing import Any

from .. import money

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ROWS = 20000


def clean(value: Any, limit: int = 500) -> str:
    return str(value or "").replace("\x00", "").strip()[:limit]


def plain(value: Any) -> str:
    """Lower case, no accents, single spaces: how headers and types are compared."""
    text = unicodedata.normalize("NFKD", clean(value, 200).lstrip("﻿")).casefold()
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


def decode(content: bytes) -> tuple[str, str, list[dict[str, Any]]]:
    """Text of the file, the encoding used, and a warning when the fallback was needed."""
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return content.decode(encoding), encoding, []
        except UnicodeDecodeError:
            continue
    try:
        return content.decode("cp1252"), "cp1252", [{"code": "imp_encoding_fallback", "params": {}}]
    except UnicodeDecodeError as exc:  # pragma: no cover - cp1252 decodes almost anything
        raise ValueError("imp_encoding") from exc


def delimiter_of(text: str) -> str:
    sample = text[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
    except csv.Error:
        first = sample.splitlines()[0] if sample.splitlines() else ""
        counts = {d: first.count(d) for d in (",", ";", "\t")}
        return max(counts, key=counts.get) if any(counts.values()) else ","


def read_table(content: bytes) -> dict[str, Any]:
    """Rows of a CSV file as dictionaries, with their line numbers (header = line 1)."""
    if not isinstance(content, (bytes, bytearray)) or not content.strip():
        raise ValueError("imp_empty")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("imp_too_large")
    if bytes(content[:4]) in (b"PK\x03\x04", b"%PDF") or b"\x00" in content[:4096]:
        raise ValueError("imp_not_text")  # a workbook, a PDF or another binary file
    text, encoding, warnings = decode(bytes(content))
    delimiter = delimiter_of(text)
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter)
    headers = [clean(h, 200).lstrip("﻿") for h in (reader.fieldnames or [])]
    if not any(headers):
        raise ValueError("imp_no_header")
    rows: list[tuple[int, dict[str, str]]] = []
    for raw in reader:
        if len(rows) >= MAX_ROWS:
            raise ValueError("imp_too_many_rows")
        if not raw or not any(clean(v) for k, v in raw.items() if k is not None):
            continue
        values = {clean(k, 200).lstrip("﻿"): clean(v, 1000) for k, v in raw.items() if k is not None}
        rows.append((reader.line_num, values))
    return {"encoding": encoding, "delimiter": delimiter, "headers": headers, "rows": rows, "warnings": warnings}


# --------------------------------------------------------------------------- dates

_SLASH = re.compile(r"\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:\s.*)?")


def slash_parts(value: str) -> tuple[int, int, int] | None:
    match = _SLASH.fullmatch(value or "")
    return tuple(int(x) for x in match.groups()) if match else None  # type: ignore[return-value]


def infer_order(values: list[str], default: str = "DMY") -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """Day/month order from the values that can only be read one way.

    A file mixing both is refused; a file where every date is ambiguous uses
    ``default`` and says so.
    """
    dmy = mdy = False
    for value in values:
        parts = slash_parts(value)
        if not parts:
            continue
        first, second, _ = parts
        if first > 12 >= second:
            dmy = True
        if second > 12 >= first:
            mdy = True
    if dmy and mdy:
        return "", [], [{"code": "imp_dates_mixed", "params": {}}]
    if dmy:
        return "DMY", [], []
    if mdy:
        return "MDY", [], []
    if any(slash_parts(v) for v in values):
        return default, [{"code": "imp_dates_ambiguous", "params": {"order": default}}], []
    return default, [], []


def parse_day(value: Any, order: str) -> date | None:
    text = clean(value, 50)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        pass
    parts = slash_parts(text)
    if not parts:
        return None
    first, second, year = parts
    month, day = (first, second) if order == "MDY" else (second, first)
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    text = re.sub(r"[\s  ]", "", clean(value, 50)).replace(",", ".")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return int(number) if number.is_integer() else None


def parse_cents(value: Any) -> int | None:
    """Amount in cents, ``None`` for an empty cell; raises ``ValueError`` for unreadable text."""
    text = clean(value, 80)
    if not text:
        return None
    return money.parse_amount_text(text)
