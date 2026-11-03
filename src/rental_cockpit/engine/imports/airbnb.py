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
  lines that follow them (same date): they are never added a second time,
  but each one is checked against those lines, to the cent, and gives the
  date the money was sent and the latest date it reaches the bank;
* the same confirmation code on several lines is one stay; lines that
  disagree on its dates or listing are refused rather than merged;
* a line whose nights do not match its dates is refused;
* every other line is read too, never dropped in silence: a resolution
  payout or an AirCover damage refund is an income, a « Crédit divers » a
  platform credit, a negative resolution adjustment a refund to a guest
  taken from a payout. A type this reader does not know is shown with its
  amount, to be checked by the person.
"""
from __future__ import annotations

from collections import Counter, OrderedDict
from typing import Any

from .csvtools import clean, infer_order, parse_cents, parse_day, parse_int, plain, read_table

READER_VERSION = "airbnb-fr-2"

REQUIRED = ("Type", "Code de confirmation", "Date de début", "Date de fin", "Nuits", "Voyageur", "Logement")
OPTIONAL = ("Date", "Date de réservation", "Arrivée au plus tard le", "Détails", "Code de référence", "Devise", "Montant",
            "Versé", "Frais de service", "Frais de Versement sur carte bancaire", "Frais de ménage", "Revenus bruts",
            "Taxes reversées par Airbnb", "Année des revenus")
_CANONICAL = {plain(name): name for name in (*REQUIRED, *OPTIONAL)}
_RESERVATION = "reservation"
_TRANSFER = "payout"
# Lines that are not bookings, by type (accents and case ignored).
#   compensation  resolution payout, AirCover damage refund: income of the property
#   credit        « Crédit divers » (rewards, goodwill credit): income from the platform
#   adjustment    resolution adjustment: negative = refund to a guest taken from a payout
OPERATION_TYPES = {
    "versement de resolution": "compensation",
    "credit divers": "credit",
    "regularisation de la resolution": "adjustment",
    "ajustement de la resolution": "adjustment",
}


def is_airbnb(headers: list[str]) -> bool:
    known = {_CANONICAL.get(plain(h)) for h in headers}
    return all(name in known for name in REQUIRED)


def _error(code: str, /, **params: Any) -> dict[str, Any]:
    return {"code": code, "params": params}


def parse(content: bytes) -> dict[str, Any]:
    """Normalised stays of an Airbnb export, with line numbers, errors and warnings. Writes nothing."""
    table = read_table(content)
    header_map = {h: _CANONICAL[plain(h)] for h in table["headers"] if plain(h) in _CANONICAL}
    present = set(header_map.values())
    result: dict[str, Any] = {
        "kind": "airbnb", "reader": READER_VERSION, "encoding": table["encoding"], "delimiter": table["delimiter"],
        "headers": table["headers"], "rows": [], "errors": [], "warnings": list(table["warnings"]),
        "ignored": {"transfers": 0, "other": {}}, "listings": [], "operations": [], "payouts": [],
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
    group: dict[str, Any] | None = None  # the « Payout » line the following lines belong to
    seen_keys: Counter[str] = Counter()
    for line, row in rows:
        kind = plain(row.get("Type"))
        day_text = clean(row.get("Date"), 20)
        if kind == _TRANSFER:
            result["ignored"]["transfers"] += 1
            group = _payout_line(line, row, order, result)
            continue
        if group is not None and day_text != group["date_text"]:
            group = None  # a payout covers the lines written right after it, on the same date
        if kind != _RESERVATION:
            _operation(line, row, kind, order, group, seen_keys, result, others)
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
        if group is not None and amounts.get("net") is not None:
            group["parts"].append({"kind": "stay", "ref": code, "amount": amounts["net"], "line": line})
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
            if group is not None and not existing["bank_by"]:
                existing["bank_by"], existing["payout_ref"] = group["bank_by"], group["ref"]
            continue
        stays[code] = {
            "key": f"L{line}", "lines": [line], "external_ref": code, "start": start.isoformat(), "end": end.isoformat(),
            "nights": (end - start).days, "guest_name": clean(row.get("Voyageur"), 80), "guests": None, "listing": listing,
            "raw": amounts, "paid_on": paid_on.isoformat() if paid_on else "", "errors": [], "warnings": [],
            "bank_by": group["bank_by"] if group else "", "payout_ref": group["ref"] if group else "",
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
    for payout in result["payouts"]:
        payout.pop("date_text", None)
        payout["explained"] = sum(part["amount"] for part in payout["parts"])
    result["listings"] = sorted({r["listing"] for r in (*result["rows"], *result["operations"]) if r.get("listing")})
    return result


def _payout_line(line: int, row: dict[str, Any], order: str, result: dict[str, Any]) -> dict[str, Any] | None:
    """A transfer of money already listed on the lines that follow it. Kept to check those lines against it."""
    try:
        amount = parse_cents(row.get("Versé"))
    except ValueError:
        amount = None
    sent = parse_day(row.get("Date"), order) if row.get("Date") else None
    if amount is None or sent is None:
        return None
    bank_by = parse_day(row.get("Arrivée au plus tard le"), order) if row.get("Arrivée au plus tard le") else None
    payout = {"line": line, "ref": clean(row.get("Code de référence"), 80), "date": sent.isoformat(),
              "date_text": clean(row.get("Date"), 20), "amount": amount,
              "bank_by": bank_by.isoformat() if bank_by else "", "parts": []}
    result["payouts"].append(payout)
    return payout


def _operation(line: int, row: dict[str, Any], kind: str, order: str, group: dict[str, Any] | None,
               seen: Counter[str], result: dict[str, Any], others: Counter[str]) -> None:
    """A line that is not a booking: resolution payout, platform credit, adjustment, or a type to check."""
    type_label = clean(row.get("Type"), 60) or "—"
    family = OPERATION_TYPES.get(kind, "unknown")
    problems = []
    try:
        amount = parse_cents(row.get("Montant"))
        if amount is None:
            amount = parse_cents(row.get("Revenus bruts"))
    except ValueError:
        amount = None
        problems.append(_error("imp_bad_amount", column="Montant"))
    day = parse_day(row.get("Date"), order) if row.get("Date") else None
    if day is None and not problems:
        problems.append(_error("imp_op_no_date"))
    if amount == 0 and not problems:
        others[type_label] += 1  # nothing was paid or taken: there is nothing to record
        return
    code = clean(row.get("Code de confirmation"), 80).upper()
    base = f"airbnb:{kind}:{code}:{day.isoformat() if day else ''}:{amount}"
    seen[base] += 1
    item = {
        "key": f"L{line}", "kind": "operation", "lines": [line], "family": family, "type_label": type_label,
        "external_ref": code, "listing": clean(row.get("Logement"), 300), "details": clean(row.get("Détails"), 200),
        "date": day.isoformat() if day else "", "amount": amount, "op_key": f"{base}:{seen[base]}",
        "start": "", "end": "", "errors": problems, "warnings": [],
        "paid_on": group["date"] if group else "", "bank_by": group["bank_by"] if group else "",
        "payout_ref": group["ref"] if group else "",
    }
    if dates := (parse_day(row.get("Date de début"), order), parse_day(row.get("Date de fin"), order)):
        if all(dates):
            item["start"], item["end"] = dates[0].isoformat(), dates[1].isoformat()
    if group is not None and amount is not None:
        group["parts"].append({"kind": family, "ref": code, "amount": amount, "line": line, "key": item["key"]})
    result["operations"].append(item)
