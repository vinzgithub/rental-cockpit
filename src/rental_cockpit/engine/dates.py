# Copyright © 2026 Vincent Fournet
"""Date helpers.

All periods are half-open: ``[start, end)``. For a stay, ``start`` is the
arrival day and ``end`` the departure day, so the number of nights is simply
``(end - start).days``. The departure day is never counted as a night.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterator

MIN_YEAR = 2000
MAX_YEAR = 2100


def parse_date(value: object) -> date:
    """Strict ISO date (``YYYY-MM-DD``) within a sane range."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        parsed = value
    else:
        text = str(value or "").strip()
        if len(text) != 10:
            raise ValueError("date_format")
        try:
            parsed = date.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("date_format") from exc
    if not MIN_YEAR <= parsed.year <= MAX_YEAR:
        raise ValueError("date_range")
    return parsed


def optional_date(value: object) -> date | None:
    """Like :func:`parse_date` but an empty value gives ``None``."""
    if value in (None, ""):
        return None
    return parse_date(value)


def nights(start: date, end: date) -> int:
    """Number of nights between arrival and departure."""
    return max(0, (end - start).days)


def overlap_days(start: date, end: date, period_start: date, period_end: date) -> int:
    """Number of days (or nights) of ``[start, end)`` inside ``[period_start, period_end)``."""
    lower = max(start, period_start)
    upper = min(end, period_end)
    return max(0, (upper - lower).days)


def iter_days(start: date, end: date) -> Iterator[date]:
    """Each day of ``[start, end)``."""
    current = start
    while current < end:
        yield current
        current += timedelta(days=1)


def in_period(day: date, period_start: date, period_end: date) -> bool:
    return period_start <= day < period_end


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
