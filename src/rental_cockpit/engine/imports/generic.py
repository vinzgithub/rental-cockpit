# Copyright © 2026 Vincent Fournet
"""Generic CSV import: the person says which column holds what.

Columns are only suggested from their names (in French or English); the
suggestion is shown and can be changed before anything is written. A mapping
can be remembered for files with the same columns.
"""
from __future__ import annotations

import hashlib
import re
from datetime import timedelta
from typing import Any

from .csvtools import clean, infer_order, parse_cents, parse_day, parse_int, plain, read_table

READER_VERSION = "csv-1"

# Fields a column can feed, and words that suggest them (compared without accents).
FIELDS = ("start", "end", "nights", "external_ref", "guest_label", "guests", "gross", "commission", "payout",
          "taxes_collected", "property", "paid_on")
HINTS: dict[str, tuple[str, ...]] = {
    "start": ("date d'arrivee", "arrivee", "check-in", "checkin", "date de debut", "debut", "start", "arrival", "from"),
    "end": ("date de depart", "depart", "check-out", "checkout", "date de fin", "fin", "end", "departure", "to"),
    "nights": ("nuits", "nuitees", "nights"),
    "external_ref": ("code de confirmation", "confirmation", "reference", "ref", "booking id", "reservation id", "numero", "code"),
    "guests": ("nombre de voyageurs", "nb voyageurs", "personnes", "number of guests", "guests count", "pax", "adultes", "adults"),
    "guest_label": ("voyageur", "client", "nom", "guest", "name"),
    "gross": ("montant brut", "revenus bruts", "brut", "gross", "total", "prix", "price", "montant"),
    "commission": ("commission", "frais de service", "service fee", "fee"),
    "payout": ("montant net", "montant verse", "versement net", "net payout", "versement", "net", "payout", "verse", "paid out"),
    "taxes_collected": ("taxe de sejour", "tourist tax", "occupancy tax", "taxes"),
    "property": ("logement", "bien", "property", "listing", "location", "annonce"),
    "paid_on": ("date de paiement", "date de versement", "paid on", "payment date", "payout date"),
}
DATE_ORDERS = ("auto", "DMY", "MDY")


def signature(headers: list[str]) -> str:
    """Identifies a file layout, so a remembered mapping is only offered for the same columns."""
    return hashlib.sha256("\x1f".join(sorted(plain(h) for h in headers if h)).encode()).hexdigest()[:24]


def suggest(headers: list[str]) -> dict[str, str]:
    """Best guess of the mapping from the column names; every field at most once, every column at most once.

    A column goes to the field whose hint matches it most precisely (an exact
    name first, then the longest hint found as whole words in it).
    """
    scored = []
    for field in FIELDS:
        for header in headers:
            if not header:
                continue
            name = plain(header)
            for hint in HINTS[field]:
                if name == hint:
                    scored.append((1000 + len(hint), field, header))
                elif re.search(rf"(?<![a-z0-9]){re.escape(hint)}(?![a-z0-9])", name):
                    scored.append((len(hint), field, header))
    mapping: dict[str, str] = {}
    taken: set[str] = set()
    for _, field, header in sorted(scored, key=lambda item: -item[0]):
        if field not in mapping and header not in taken:
            mapping[field] = header
            taken.add(header)
    return mapping


def _error(code: str, /, **params: Any) -> dict[str, Any]:
    return {"code": code, "params": params}


def parse(content: bytes, mapping: dict[str, str] | None = None, date_order: str = "auto") -> dict[str, Any]:
    """Normalised stays from a CSV file and a column mapping. Writes nothing."""
    table = read_table(content)
    headers = [h for h in table["headers"] if h]
    used = {field: column for field, column in (mapping or suggest(headers)).items() if field in FIELDS and column in headers}
    result: dict[str, Any] = {
        "kind": "csv", "reader": READER_VERSION, "encoding": table["encoding"], "delimiter": table["delimiter"],
        "headers": headers, "mapping": used, "suggested": suggest(headers), "signature": signature(headers),
        "rows": [], "errors": [], "warnings": list(table["warnings"]), "ignored": {"transfers": 0, "other": {}}, "listings": [],
    }
    if "start" not in used or not ({"end", "nights"} & set(used)):
        result["errors"].append(_error("imp_csv_mapping"))
        return result
    order = date_order if date_order in ("DMY", "MDY") else ""
    if not order:
        values = [raw.get(used[f], "") for _, raw in table["rows"] for f in ("start", "end", "paid_on") if f in used]
        order, warnings, errors = infer_order(values, default="DMY")
        result["warnings"] += warnings
        result["errors"] += errors
        if errors:
            return result
    result["date_order"] = order

    seen: dict[str, int] = {}
    for line, raw in table["rows"]:
        def value(field: str, raw: dict[str, str] = raw) -> str:
            return raw.get(used[field], "") if field in used else ""
        problems = []
        start = parse_day(value("start"), order)
        end = parse_day(value("end"), order) if "end" in used else None
        nights = parse_int(value("nights")) if "nights" in used else None
        if start and not end and nights and nights > 0:
            end = start + timedelta(days=nights)
        if not start or not end:
            problems.append(_error("imp_bad_dates"))
        elif end <= start:
            problems.append(_error("imp_dates_order"))
        elif nights is not None and "end" in used and nights != (end - start).days:
            problems.append(_error("imp_nights_mismatch", file=nights, dates=(end - start).days))
        amounts: dict[str, int | None] = {}
        for field in ("gross", "commission", "payout", "taxes_collected"):
            try:
                cents = parse_cents(value(field)) if field in used else None
                amounts[field] = abs(cents) if cents is not None and field in ("commission", "taxes_collected") else cents
            except ValueError:
                problems.append(_error("imp_bad_amount", column=used[field]))
                amounts[field] = None
        ref = clean(value("external_ref"), 80)
        if ref:
            if ref in seen:
                problems.append(_error("imp_ref_twice", ref=ref, line=seen[ref]))
            seen.setdefault(ref, line)
        paid_on = parse_day(value("paid_on"), order) if value("paid_on") else None
        row = {"key": f"L{line}", "lines": [line], "external_ref": ref, "errors": problems, "warnings": [],
               "listing": clean(value("property"), 300)}
        if not problems:
            guests = parse_int(value("guests")) if "guests" in used else None
            payout = amounts["payout"]
            row.update({
                "start": start.isoformat(), "end": end.isoformat(), "nights": (end - start).days,
                "guest_name": clean(value("guest_label"), 80), "guests": guests if guests and 0 < guests < 100 else None,
                "amounts": amounts, "paid_on": paid_on.isoformat() if paid_on else "",
                "paid_amount": payout if paid_on and payout and payout > 0 else None,
            })
        result["rows"].append(row)
    result["listings"] = sorted({r["listing"] for r in result["rows"] if r.get("listing")})
    return result
