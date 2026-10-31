# Copyright © 2026 Vincent Fournet
"""Exact money handling.

Amounts are stored and computed as integer cents. Floating point numbers are
never added together. Text typed by a user or read from a file goes through
:func:`parse_amount` (strict, for forms) or :func:`parse_amount_text`
(tolerant, for imports), and both return cents or raise ``ValueError``.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

#: Upper bound accepted for one amount: one hundred million euros.
MAX_CENTS = 10_000_000_000


def parse_amount(value: object, *, allow_negative: bool = False, allow_zero: bool = False) -> int:
    """Convert a form value (``"12.50"``, ``"12,5"`` or ``12.5``) to cents.

    Only decimal notation is accepted here: ``"1250"`` means 1 250 euros, not
    cents. At most two decimals. Thousands separators are refused so that
    ``"1.250"`` can never silently become 1.25 or 1 250.
    """
    if isinstance(value, bool) or value is None:
        raise ValueError("amount_required")
    text = str(value).strip().replace(" ", "").replace(" ", "")
    if text.endswith("€"):
        text = text[:-1].strip()
    if text.count(",") + text.count(".") > 1:
        raise ValueError("amount_format")
    text = text.replace(",", ".")
    if not re.fullmatch(r"[+-]?\d{1,9}(\.\d{1,2})?", text):
        raise ValueError("amount_format")
    try:
        cents = int((Decimal(text) * 100).to_integral_exact())
    except (InvalidOperation, ArithmeticError) as exc:  # pragma: no cover - guarded by regex
        raise ValueError("amount_format") from exc
    return check_cents(cents, allow_negative=allow_negative, allow_zero=allow_zero)


def check_cents(cents: object, *, allow_negative: bool = False, allow_zero: bool = False) -> int:
    """Validate an integer amount already expressed in cents."""
    if isinstance(cents, bool) or not isinstance(cents, int):
        raise ValueError("amount_format")
    if abs(cents) > MAX_CENTS:
        raise ValueError("amount_too_large")
    if cents == 0 and not allow_zero:
        raise ValueError("amount_zero")
    if cents < 0 and not allow_negative:
        raise ValueError("amount_negative")
    return cents


def parse_amount_text(value: object) -> int | None:
    """Read an amount from an imported file; return ``None`` when the cell is empty.

    Accepts ``1 234,56 €``, ``1,234.56``, ``-12.5`` or ``(12,50)``. When both
    separators are present, the last one is the decimal separator. A single
    comma is a decimal separator. A single dot followed by exactly three digits
    is ambiguous and refused instead of guessed.
    """
    text = str(value or "").strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = re.sub(r"[^0-9,.\-+]", "", text)
    if not text or text in {"-", "+"}:
        return None
    if text.count("-") + text.count("+") > 1 or re.search(r".[+-]", text):
        raise ValueError("amount_format")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        if text.count(",") > 1:
            raise ValueError("amount_format")
        text = text.replace(",", ".")
    elif text.count(".") == 1 and re.fullmatch(r"[+-]?\d{1,3}\.\d{3}", text):
        raise ValueError("amount_ambiguous")
    elif text.count(".") > 1:
        raise ValueError("amount_format")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("amount_format") from exc
    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("amount_format")
    cents = int(amount * 100)
    if negative:
        cents = -abs(cents)
    return check_cents(cents, allow_negative=True, allow_zero=True)


def allocate(total: int, weights: list[int]) -> list[int]:
    """Split ``total`` cents proportionally to ``weights`` without losing a cent.

    Uses the largest remainder method. Ties go to the earliest share so the
    result is deterministic. ``sum(result) == total`` always holds, including
    for negative totals.
    """
    if not weights:
        return []
    weight_sum = sum(weights)
    if weight_sum <= 0 or any(w < 0 for w in weights):
        raise ValueError("allocation_weights")
    sign = -1 if total < 0 else 1
    magnitude = abs(total)
    base = [magnitude * w // weight_sum for w in weights]
    remainders = [(magnitude * w % weight_sum, -index) for index, w in enumerate(weights)]
    missing = magnitude - sum(base)
    for _, negative_index in sorted(remainders, reverse=True)[:missing]:
        base[-negative_index] += 1
    return [sign * share for share in base]


def format_cents(cents: int | None, lang: str = "fr") -> str:
    """Human readable amount, used in messages and CSV exports."""
    if cents is None:
        return "—"
    sign = "-" if cents < 0 else ""
    units, rest = divmod(abs(cents), 100)
    if lang == "fr":
        grouped = f"{units:,}".replace(",", " ")
        return f"{sign}{grouped},{rest:02d} €"
    return f"{sign}€{units:,}.{rest:02d}"
