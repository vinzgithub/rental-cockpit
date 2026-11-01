# Copyright © 2026 Vincent Fournet
"""What the « Séjours » screen shows about a stay, computed from the registry.

Nothing here is stored: nights, expected payout, money received, payout
status and the month-by-month share of the stay are always derived from the
stay and its payments, with the same rules as the indicators. A figure shown
on a stay therefore always matches what the Overview counts.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .dates import nights as count_nights
from .dates import parse_date
from .indicators import _slice_share, expected_payout, month_period
from .schema import label

# Payout of a stay, from the owner's point of view.
#   none        nothing to receive (cancelled without a retained amount)
#   unknown     the amounts are not known yet: nothing can be checked
#   expected    the payout is due later (the stay has not ended)
#   to_confirm  the stay has ended and no payout was recorded
#   partial     part of the expected payout was received
#   received    the expected payout was received in full
PAYOUT_STATES = ("none", "unknown", "expected", "to_confirm", "partial", "received")
PAYOUT_LABELS = {
    "none": ("Rien à recevoir", "Nothing to receive"),
    "unknown": ("Montant à compléter", "Amount to complete"),
    "expected": ("Versement attendu", "Payout expected"),
    "to_confirm": ("Versement à confirmer", "Payout to confirm"),
    "partial": ("Partiellement reçu", "Partly received"),
    "received": ("Versement reçu", "Payout received"),
}
# Where the stay stands in time, for the badge shown next to it.
STATE_LABELS = {
    "cancelled": ("Annulé", "Cancelled"),
    "provisional": ("Provisoire", "Provisional"),
    "upcoming": ("À venir", "Upcoming"),
    "in_progress": ("En cours", "In progress"),
    "finished": ("Terminé", "Finished"),
}


def received_for(data: dict[str, Any], stay_id: str) -> tuple[int, list[dict[str, Any]]]:
    """Money received for a stay and the payments behind it (oldest first)."""
    total, rows = 0, []
    for payment in data.get("payments", {}).values():
        for link in payment["links"]:
            if link["type"] == "stay" and link["id"] == stay_id:
                total += link["amount"]
                rows.append({"id": payment["id"], "date": payment["date"], "amount": link["amount"],
                             "method": payment.get("method", ""), "note": payment.get("note", ""),
                             "created_at": payment.get("created_at"), "created_by": payment.get("created_by")})
    rows.sort(key=lambda row: (row["date"], row.get("created_at") or ""))
    return total, rows


def received_by_stay(data: dict[str, Any]) -> dict[str, int]:
    """Money received per stay, computed once for a whole list."""
    totals: dict[str, int] = {}
    for payment in data.get("payments", {}).values():
        for link in payment["links"]:
            if link["type"] == "stay":
                totals[link["id"]] = totals.get(link["id"], 0) + link["amount"]
    return totals


def stay_state(stay: dict[str, Any], today: date) -> str:
    if stay["status"] == "cancelled":
        return "cancelled"
    if stay["status"] == "provisional":
        return "provisional"
    start, end = parse_date(stay["start"]), parse_date(stay["end"])
    if today < start:
        return "upcoming"
    if today < end:
        return "in_progress"
    return "finished"


def payout_state(stay: dict[str, Any], expected: int | None, received: int, today: date) -> str:
    if stay["status"] == "cancelled" and not expected and not received:
        return "none"
    if expected is None:
        return "received" if received else "unknown"
    if expected <= 0 and not received:
        return "none"
    if received >= expected:
        return "received"
    if received > 0:
        return "partial"
    if stay["status"] in ("confirmed", "completed", "cancelled") and parse_date(stay["end"]) <= today:
        return "to_confirm"
    return "expected"


def summary(data: dict[str, Any], stay: dict[str, Any], today: date, lang: str, received_map: dict[str, int] | None = None) -> dict[str, Any]:
    """One stay as listed: its own fields plus the derived figures, never stored."""
    fr = lang == "fr"
    prop = data.get("properties", {}).get(stay["property_id"], {})
    expected = expected_payout(stay)
    received = received_map.get(stay["id"], 0) if received_map is not None else received_for(data, stay["id"])[0]
    state = stay_state(stay, today)
    pay = payout_state(stay, expected, received, today)
    amounts = stay.get("amounts") or {}
    return {
        "id": stay["id"],
        "property_id": stay["property_id"],
        "property": prop.get("name", "—"),
        "property_kind": prop.get("kind", "other"),
        "start": stay["start"],
        "end": stay["end"],
        "nights": count_nights(parse_date(stay["start"]), parse_date(stay["end"])),
        "status": stay["status"],
        "status_label": label("stay_status", stay["status"], lang),
        "state": state,
        "state_label": STATE_LABELS[state][0 if fr else 1],
        "channel": stay.get("channel") or "other",
        "channel_label": label("channel", stay.get("channel") or "other", lang),
        "source": stay.get("source", "manual"),
        "external_ref": stay.get("external_ref", ""),
        "guest_label": stay.get("guest_label", ""),
        "guests": stay.get("guests"),
        "amounts": {key: amounts.get(key) for key in ("gross", "commission", "payout", "taxes_collected", "deposit")},
        "adjustments_total": sum(a["amount"] for a in stay.get("adjustments", [])),
        "expected_payout": expected,
        "received": received,
        "payout_state": pay,
        "payout_label": PAYOUT_LABELS[pay][0 if fr else 1],
        "deletable": stay.get("source") in ("manual", "demo"),
        "updated_at": stay.get("updated_at"),
        "revision": int(stay.get("revision") or 0),
    }


def _months(start: date, end: date) -> list[tuple[date, date]]:
    """Calendar months touched by the nights of ``[start, end)``."""
    months, cursor = [], date(start.year, start.month, 1)
    while cursor < end:
        first, nxt = month_period(cursor.year, cursor.month)
        months.append((first, nxt))
        cursor = nxt
    return months


def breakdown(stay: dict[str, Any]) -> list[dict[str, Any]]:
    """« Ce que ce séjour compte dans la Synthèse » — Activity reading, month by month.

    Same rule as the indicators: revenue and commission are spread night by
    night, the rounding cents are distributed once over the whole stay so the
    months always add up to the stay. A cancelled stay counts its retained
    amount once, in the month of arrival.
    """
    start, end = parse_date(stay["start"]), parse_date(stay["end"])
    amounts = stay.get("amounts") or {}
    gross, commission = amounts.get("gross"), amounts.get("commission")
    if stay["status"] == "cancelled":
        first, nxt = month_period(start.year, start.month)
        return [{"start": first.isoformat(), "end": nxt.isoformat(), "nights": 0,
                 "revenue": gross, "commission": commission,
                 "net": None if gross is None else gross - (commission or 0)}]
    rows = []
    for first, nxt in _months(start, end):
        nights = count_nights(max(start, first), min(end, nxt))
        revenue = None if gross is None else _slice_share(gross, start, end, first, nxt)
        fee = None if commission is None else _slice_share(commission, start, end, first, nxt)
        rows.append({"start": first.isoformat(), "end": nxt.isoformat(), "nights": nights, "revenue": revenue,
                     "commission": fee, "net": None if revenue is None else revenue - (fee or 0)})
    return rows


def detail(data: dict[str, Any], stay: dict[str, Any], today: date, lang: str) -> dict[str, Any]:
    """Everything the stay page shows: summary, month split, payouts, notes and history."""
    _, payments = received_for(data, stay["id"])
    result = summary(data, stay, today, lang)
    result.update({
        "note": stay.get("note", ""),
        "adjustments": stay.get("adjustments", []),
        "amounts_before_cancel": stay.get("amounts_before_cancel"),
        "breakdown": breakdown(stay),
        "payments": payments,
        "history": [{"at": h["at"], "by": h["by"], "fields": sorted(h.get("changes", {}))} for h in stay.get("history", [])][-20:],
        "created_at": stay.get("created_at"),
        "created_by": stay.get("created_by"),
        "source": stay.get("source", "manual"),
        "imported": _imported(data, stay),
    })
    # Costs that served the stay (analytical: they were already counted once as expenses).
    from .suppliers import stay_costs  # local import: suppliers builds on the entries module
    costs = stay_costs(data, stay, lang)
    result["costs"] = costs
    result["costs_total"] = sum(c["amount"] for c in costs)
    expected = result.get("expected_payout")
    result["margin"] = expected - result["costs_total"] if expected is not None and stay["status"] != "cancelled" else None
    return result


def _imported(data: dict[str, Any], stay: dict[str, Any]) -> dict[str, Any] | None:
    """The import that created the stay (file and moment), shown in « À propos » for traceability."""
    record = data.get("imports", {}).get(stay.get("origin_import") or "")
    if record is None:
        return None
    return {"id": record["id"], "at": record["at"], "file_name": record.get("file_name", ""), "kind": record.get("kind", "")}
