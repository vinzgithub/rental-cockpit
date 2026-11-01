# Copyright © 2026 Vincent Fournet
"""Airbnb « Historique des transactions » export, French version.

Only this export, whose columns were checked against genuine files, is read
as « Airbnb ». Any other file (English export, other platform) goes through
the generic CSV import, where each column is chosen by the person: no format
is guessed.

Rules kept from the original reader:

* the required columns must all be present, whatever their order or case;
* the day/month order is taken from the unambiguous dates (Airbnb writes
  MM/DD/YYYY in its French export), a file mixing both is refused;
* « Payout » lines are bank transfers of amounts already listed on the
  reservation lines: they are never added a second time;
* the same confirmation code on several lines is one stay; lines that
  disagree on its dates or listing are refused rather than merged;
* a line whose nights do not match its dates is refused.
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from typing import Any

from .csvtools import clean, infer_order, parse_cents, parse_day, parse_int, plain, read_table

READER_VERSION = "airbnb-fr-1"

REQUIRED = ("Type", "Code de confirmation", "Date de début", "Date de fin", "Nuits", "Voyageur", "Logement")
OPTIONAL = ("Date", "Date de réservation", "Arrivée au plus tard le", "Détails", "Code de référence", "Devise", "Montant",
            "Versé", "Frais de service", "Frais de Versement sur carte bancaire", "Frais de ménage", "Revenus bruts",
            "Taxes reversées par Airbnb", "Année des revenus")
_CANONICAL = {plain(name): name for name in (*REQUIRED, *OPTIONAL)}
_RESERVATION = "reservation"
_TRANSFER = "payout"


def is_airbnb(headers: list[str]) -> bool:
    known = {_CANONICAL.get(plain(h)) for h in headers}
    return all(name in known for name in REQUIRED)


def _error(code: str, **params: Any) -> dict[str, Any]:
    return {"code": code, "params": params}


def parse(content: bytes) -> dict[str, Any]:
    """Normalised stays of an Airbnb export, with line numbers, errors and warnings. Writes nothing."""
    table = read_table(content)
    header_map = {h: _CANONICAL[plain(h)] for h in table["headers"] if plain(h) in _CANONICAL}
    present = set(header_map.values())
    result: dict[str, Any] = {
        "kind": "airbnb", "reader": READER_VERSION, "encoding": table["encoding"], "delimiter": table["delimiter"],
        "headers": table["headers"], "rows": [], "errors": [], "warnings": list(table["warnings"]),
        "ignored": {"transfers": 0, "other": {}}, "listings": [],
    }
    missing = [name for name in REQUIRED if name not in present]
    if missing:
        result["errors"].append(_error("imp_airbnb_columns", columns=", ".join(missing)))
        return result

    rows = [(line, {header_map[k]: v for k, v in raw.items() if k in header_map}) for line, raw in table["rows"]]
    dates = [r.get(col, "") for _, r in rows if plain(r.get("Type")) == _RESERVATION
             for col in ("Date de début", "Date de fin", "Date de réservation", "Date")]
    order, warnings, errors = infer_order(dates, default="MDY")
    result["warnings"] += warnings
    result["errors"] += errors
    result["date_order"] = order or "?"
    if errors:
        return result

    stays: OrderedDict[str, dict[str, Any]] = OrderedDict()
    others: Counter[str] = Counter()
    for line, row in rows:
        kind = plain(row.get("Type"))
        if kind == _TRANSFER:
            result["ignored"]["transfers"] += 1
            continue
        if kind != _RESERVATION:
            others[clean(row.get("Type"), 60) or "—"] += 1
            continue
        code = clean(row.get("Code de confirmation"), 80).upper()
        start, end = parse_day(row.get("Date de début"), order), parse_day(row.get("Date de fin"), order)
        nights = parse_int(row.get("Nuits"))
        listing = clean(row.get("Logement"), 300)
        problems = []
        if not code:
            problems.append(_error("imp_no_code"))
        if not start or not end:
            problems.append(_error("imp_bad_dates"))
        elif end <= start:
            problems.append(_error("imp_dates_order"))
        elif nights is not None and nights != (end - start).days:
            problems.append(_error("imp_nights_mismatch", file=nights, dates=(end - start).days))
        if not listing:
            problems.append(_error("imp_no_listing"))
        amounts: dict[str, int | None] = {}
        for column, key in (("Revenus bruts", "gross"), ("Frais de service", "fee"), ("Montant", "net"),
                            ("Taxes reversées par Airbnb", "taxes")):
            try:
                amounts[key] = parse_cents(row.get(column)) if column in present else None
            except ValueError:
                problems.append(_error("imp_bad_amount", column=column))
                amounts[key] = None
        paid_on = parse_day(row.get("Date"), order) if row.get("Date") else None
        if problems:
            result["rows"].append({"key": f"L{line}", "lines": [line], "external_ref": code, "errors": problems,
                                   "warnings": [], "listing": listing})
            continue
        existing = stays.get(code)
        if existing is not None:
            if (existing["start"], existing["end"], existing["listing"]) != (start.isoformat(), end.isoformat(), listing):
                existing["errors"].append(_error("imp_code_conflict", code=code, line=line))
                continue
            existing["lines"].append(line)
            for key, value in amounts.items():
                if value is not None:
                    existing["raw"][key] = (existing["raw"].get(key) or 0) + value
            if paid_on and not existing["paid_on"]:
                existing["paid_on"] = paid_on.isoformat()
            continue
        stays[code] = {
            "key": f"L{line}", "lines": [line], "external_ref": code, "start": start.isoformat(), "end": end.isoformat(),
            "nights": (end - start).days, "guest_name": clean(row.get("Voyageur"), 80), "guests": None, "listing": listing,
            "raw": amounts, "paid_on": paid_on.isoformat() if paid_on else "", "errors": [], "warnings": [],
        }

    for stay in stays.values():
        raw = stay.pop("raw")
        fee = abs(raw["fee"]) if raw.get("fee") is not None else None
        net, gross = raw.get("net"), raw.get("gross")
        if gross is None and net is not None and fee is not None:
            gross = net + fee
        if gross is not None and fee is not None and net is not None and abs(gross - fee - net) > 1:
            stay["warnings"].append(_error("imp_amounts_differ"))
        stay["amounts"] = {"gross": gross, "commission": fee, "payout": net,
                           "taxes_collected": abs(raw["taxes"]) if raw.get("taxes") else None}
        stay["paid_amount"] = net if stay["paid_on"] and net and net > 0 else None
        result["rows"].append(stay)
    result["rows"].sort(key=lambda r: r["lines"][0])
    result["ignored"]["other"] = dict(others)
    result["listings"] = sorted({r["listing"] for r in result["rows"] if r.get("listing")})
    return result
