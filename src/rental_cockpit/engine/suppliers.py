# Copyright © 2026 Vincent Fournet
"""What the « Prestataires » screen shows: suppliers, their indicative rates,
their invoices, and how a detailed invoice is split between stays.

Rates are indicative only: they pre-fill a service line, they are never
applied to an amount behind the person's back (DON 02). Splitting an invoice
between stays is analytical: it explains what a cost served, it never adds a
charge (PRE 03, PRE 04).
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .entries import paid_by_entry, state_of
from .ledger import allocation_remaining
from .schema import category_label

KIND_LABELS = {
    "cleaning": ("Ménage", "Cleaning"), "linen": ("Linge", "Linen"), "travel": ("Déplacement", "Travel"), "other": ("Autre", "Other"),
    "discount": ("Remise", "Discount"), "tax": ("Taxe", "Tax"), "adjustment": ("Ajustement", "Adjustment"),
}
UNIT_LABELS = {
    "hour": ("heure", "hour"), "flat": ("forfait", "flat fee"), "set": ("lot", "set"), "unit": ("unité", "unit"),
    "km": ("km", "km"), "trip": ("déplacement", "trip"),
}
# Service lines that can be split between stays (a discount or a tax follows the invoice).
SPLITTABLE = ("cleaning", "linen", "travel", "other")
# Categories an invoice line may replace when it is reconciled with entries typed by hand.
KIND_CATEGORY = {"cleaning": "cleaning", "linen": "linen", "travel": "travel"}


def _t(pair: tuple[str, str], lang: str) -> str:
    return pair[0] if lang == "fr" else pair[1]


def summary(data: dict[str, Any], supplier: dict[str, Any], lang: str, today: date, paid: dict[str, int] | None = None) -> dict[str, Any]:
    paid = paid if paid is not None else paid_by_entry(data)
    entries = [e for e in data.get("entries", {}).values()
               if e.get("supplier_id") == supplier["id"] and not e.get("archived") and not e.get("superseded_by")]
    year = str(today.year)
    due = [e for e in entries if e["kind"] == "expense" and e["date"] <= today.isoformat()]
    return {
        "id": supplier["id"], "name": supplier["name"], "role": supplier.get("role", ""), "contact": supplier.get("contact", ""),
        "note": supplier.get("note", ""), "archived": bool(supplier.get("archived")),
        "categories": [{"id": c, "label": category_label(data["categories"].get(c), lang)} for c in supplier.get("categories", [])
                       if c in data["categories"]],
        "rates": [{**r, "kind_label": _t(KIND_LABELS.get(r["kind"], (r["kind"], r["kind"])), lang),
                   "unit_label": _t(UNIT_LABELS.get(r["unit"], (r["unit"], r["unit"])), lang)} for r in supplier.get("rates", [])],
        "entries": len(entries),
        "year": year,
        "year_total": sum(e["amount"] for e in entries if e["kind"] == "expense" and e["date"].startswith(year)),
        "to_pay": sum(max(e["amount"] - paid.get(e["id"], 0), 0) for e in due),
        "to_confirm": sum(1 for e in due if state_of(e, paid.get(e["id"], 0)) == "unknown"),
        "unallocated": sum(sum(max(r["remaining"], 0) for r in allocation_remaining(e)) for e in entries if e.get("allocations")),
        "last_date": max((e["date"] for e in entries), default=""),
        "revision": int(supplier.get("revision") or 0), "updated_at": supplier.get("updated_at"),
    }


def split_rows(data: dict[str, Any], entry: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    """What can be split between stays — each service line, or the whole entry — with what is already split."""
    stays = data.get("stays", {})
    rows = []
    for item in allocation_remaining(entry):
        line = next((li for li in entry.get("lines") or [] if li["id"] == item["line_id"]), {})
        rows.append({
            **item,
            "kind_label": _t(KIND_LABELS.get(item["kind"], (item["kind"], item["kind"])), lang) if item["kind"] else "",
            "intervention_date": line.get("intervention_date", ""),
            "allocations": [{"stay_id": a["stay_id"], "amount": a["amount"],
                             "stay_label": (stays.get(a["stay_id"], {}).get("guest_label") or stays.get(a["stay_id"], {}).get("external_ref")
                                            or stays.get(a["stay_id"], {}).get("start", "")) if a["stay_id"] else ""}
                            for a in entry.get("allocations") or [] if a.get("line_id", "") == item["line_id"]],
        })
    return rows


def suggested_stay(data: dict[str, Any], property_id: str, day: str) -> str:
    """The stay a service done on ``day`` most likely belongs to: departure that day, else the stay around it."""
    if not day:
        return ""
    stays = [s for s in data.get("stays", {}).values() if s["property_id"] == property_id and s["status"] != "cancelled"]
    leaving = [s for s in stays if s["end"] == day]
    if leaving:
        return leaving[0]["id"]
    around = [s for s in stays if s["start"] <= day < s["end"]]
    return around[0]["id"] if around else ""


def candidates(data: dict[str, Any], invoice: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    """Entries typed by hand that this invoice may replace (same property and kind of service, in its period)."""
    paid = paid_by_entry(data)
    kinds = {KIND_CATEGORY[li["kind"]] for li in invoice.get("lines") or [] if li["kind"] in KIND_CATEGORY}
    categories = kinds | {invoice["category_id"]}
    days = [li["intervention_date"] for li in invoice.get("lines") or [] if li.get("intervention_date")]
    invoice_day = date.fromisoformat(invoice["date"])
    first = min(days) if days else (invoice_day.replace(day=1) - timedelta(days=31)).isoformat()
    last = max([invoice["date"], *days])
    rows = []
    for entry in data.get("entries", {}).values():
        if (entry["id"] == invoice["id"] or entry["property_id"] != invoice["property_id"] or entry["kind"] != "expense"
                or entry.get("archived") or entry.get("superseded_by") or entry.get("replaces") or entry.get("lines")
                or entry["category_id"] not in categories or not first <= entry["date"] <= last):
            continue
        if entry.get("supplier_id") and entry["supplier_id"] != invoice.get("supplier_id"):
            continue
        rows.append({"id": entry["id"], "label": entry["label"], "date": entry["date"], "amount": entry["amount"],
                     "category": category_label(data["categories"].get(entry["category_id"]), lang),
                     "paid": paid.get(entry["id"], 0), "stay_id": entry.get("stay_id") or ""})
    return sorted(rows, key=lambda r: (r["date"], r["label"]))


def stay_costs(data: dict[str, Any], stay: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    """Costs that served a stay: shares of split invoices, and expenses linked to the stay as a whole."""
    rows = []
    for entry in data.get("entries", {}).values():
        if entry["property_id"] != stay["property_id"] or entry["kind"] != "expense" or entry.get("archived") or entry.get("superseded_by"):
            continue
        lines = {li["id"]: li for li in entry.get("lines") or []}
        shares = [a for a in entry.get("allocations") or [] if a.get("stay_id") == stay["id"]]
        for share in shares:
            line = lines.get(share.get("line_id") or "", {})
            rows.append({"entry_id": entry["id"], "label": entry["label"], "date": entry["date"], "amount": share["amount"],
                         "detail": line.get("label") or (_t(KIND_LABELS[line["kind"]], lang) if line.get("kind") in KIND_LABELS else ""),
                         "category": category_label(data["categories"].get(entry["category_id"]), lang), "share": True})
        if not shares and not entry.get("allocations") and entry.get("stay_id") == stay["id"]:
            rows.append({"entry_id": entry["id"], "label": entry["label"], "date": entry["date"], "amount": entry["amount"],
                         "detail": "", "category": category_label(data["categories"].get(entry["category_id"]), lang), "share": False})
    return sorted(rows, key=lambda r: (r["date"], r["label"]))
