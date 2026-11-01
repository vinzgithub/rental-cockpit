# Copyright © 2026 Vincent Fournet
"""What the « Dépenses » screen shows about an expense or an income.

As for stays, nothing here is stored: what is paid, what is left and the
payment status are always derived from the real payments linked to the
entry (FIN 01), so the list, the entry page and the Overview agree.

A *series* is a group of monthly entries created at once (loan instalments,
subscriptions): each occurrence is an ordinary entry, with its own date and
payment, that can be changed or paid on its own.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from datetime import date
from typing import Any

from .errors import RCError
from .ledger import Ledger, new_id
from .schema import category_label, label

# Payment status, from the owner's point of view.
#   unknown  nobody said whether it is settled (expense: « Paiement à confirmer »)
#   unpaid   known to be still due
#   partial  part of it was settled
#   paid     settled in full
STATES = ("unknown", "unpaid", "partial", "paid")
STATE_LABELS = {
    "expense": {"unknown": ("Paiement à confirmer", "Payment to confirm"), "unpaid": ("À payer", "To pay"),
                "partial": ("Partiellement payée", "Partly paid"), "paid": ("Payée", "Paid")},
    "income": {"unknown": ("Encaissement à confirmer", "Receipt to confirm"), "unpaid": ("À recevoir", "To receive"),
               "partial": ("Partiellement reçue", "Partly received"), "paid": ("Reçue", "Received")},
}
KIND_LABELS = {"expense": ("Dépense", "Expense"), "income": ("Recette", "Income")}
VIEWS = ("all", "to_pay", "to_confirm", "to_receive", "archived")
MAX_SERIES = 36


def _t(pair: tuple[str, str], lang: str) -> str:
    return pair[0] if lang == "fr" else pair[1]


def paid_by_entry(data: dict[str, Any]) -> dict[str, int]:
    """Money settled per entry, from the payments (one pass over the registry)."""
    paid: dict[str, int] = defaultdict(int)
    for payment in data.get("payments", {}).values():
        for link in payment["links"]:
            if link["type"] == "entry":
                paid[link["id"]] += link["amount"]
    return paid


def state_of(entry: dict[str, Any], paid: int) -> str:
    if paid >= entry["amount"]:
        return "paid"
    if paid > 0:
        return "partial"
    return "unpaid" if entry.get("payment_declared") == "unpaid" else "unknown"


def summary(data: dict[str, Any], entry: dict[str, Any], lang: str, paid: int | None = None, today: date | None = None) -> dict[str, Any]:
    """One line of the list: amounts, status and the names of what the entry points to.

    An entry dated after today (the next loan instalments, say) is *upcoming*:
    it is planned, not yet due, and stays out of « À payer » until its date.
    """
    if paid is None:
        paid = paid_by_entry(data).get(entry["id"], 0)
    prop = data["properties"].get(entry["property_id"], {})
    category = data["categories"].get(entry["category_id"], {})
    supplier = data.get("suppliers", {}).get(entry.get("supplier_id") or "", {})
    stay = data.get("stays", {}).get(entry.get("stay_id") or "")
    state = state_of(entry, paid)
    return {
        "id": entry["id"], "kind": entry["kind"], "kind_label": _t(KIND_LABELS[entry["kind"]], lang),
        "property_id": entry["property_id"], "property": prop.get("name", "—"), "property_kind": prop.get("kind", ""),
        "category_id": entry["category_id"], "category": category_label(category, lang),
        "treatment": category.get("treatment", ""), "treatment_label": label("treatment", category.get("treatment", ""), lang),
        "label": entry["label"], "amount": entry["amount"], "date": entry["date"],
        "period_start": entry.get("period_start") or "", "period_end": entry.get("period_end") or "",
        "supplier_id": entry.get("supplier_id") or "", "supplier": supplier.get("name", ""),
        "invoice_number": entry.get("invoice_number", ""),
        "stay_id": entry.get("stay_id") or "", "stay_label": (stay.get("guest_label") or stay.get("external_ref") or stay["start"]) if stay else "",
        "state": state, "state_label": _t(STATE_LABELS[entry["kind"]][state], lang),
        "paid": paid, "remaining": max(entry["amount"] - paid, 0),
        "loan_split": entry.get("loan_split"), "lines": len(entry.get("lines") or []),
        "replaces": len(entry.get("replaces") or []), "allocated": sum(a["amount"] for a in entry.get("allocations") or []),
        "series": entry.get("series"), "archived": bool(entry.get("archived")), "superseded": bool(entry.get("superseded_by")),
        "upcoming": bool(today and entry["date"] > today.isoformat()),
        "origin": (entry.get("origin") or {}).get("type", "manual"),
        "revision": int(entry.get("revision") or 0), "updated_at": entry.get("updated_at"),
    }


def detail(data: dict[str, Any], entry: dict[str, Any], lang: str, today: date | None = None) -> dict[str, Any]:
    """Everything the entry page shows: summary, payments, service lines, allocations and history."""
    payments = []
    for payment in data.get("payments", {}).values():
        for link in payment["links"]:
            if link["type"] == "entry" and link["id"] == entry["id"]:
                payments.append({"id": payment["id"], "date": payment["date"], "amount": link["amount"], "total": payment["amount"],
                                 "method": payment.get("method", ""), "note": payment.get("note", ""),
                                 "shared": len(payment["links"]) > 1})
    payments.sort(key=lambda p: (p["date"], p["id"]))
    result = summary(data, entry, lang, sum(p["amount"] for p in payments), today)
    stays = data.get("stays", {})
    linked_docs = [d for d in data.get("documents", {}).values() if entry["id"] in (d.get("entry_ids") or [])]
    result.update({
        "note": entry.get("note", ""),
        "payments": payments,
        "service_lines": entry.get("lines") or [],
        "allocations": [{**a, "stay_label": (stays.get(a["stay_id"], {}).get("guest_label") or stays.get(a["stay_id"], {}).get("external_ref") or "")}
                        for a in entry.get("allocations") or []],
        "history": [{"at": h["at"], "by": h["by"], "fields": sorted(h.get("changes", {}))} for h in entry.get("history", [])][-20:],
        "created_at": entry.get("created_at"),
        "deletable": not payments and not linked_docs and not entry.get("replaces"),
        "documents": len(linked_docs),
        # Detailed invoice: what can be split between stays, and the entries typed by hand it replaces.
        "split": split_rows(data, entry, lang) if entry["kind"] == "expense" else [],
        "replaces": [{"id": r["id"], "label": data["entries"].get(r["id"], {}).get("label", "—"),
                      "date": data["entries"].get(r["id"], {}).get("date", ""), "amount": data["entries"].get(r["id"], {}).get("amount", 0),
                      "payments": sum(m["amount"] for m in r["payments"])} for r in entry.get("replaces") or []],
        "superseded_by": ({"id": entry["superseded_by"], "label": data["entries"].get(entry["superseded_by"], {}).get("label", "—")}
                          if entry.get("superseded_by") else None),
    })
    return result


def split_rows(data: dict[str, Any], entry: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    from .suppliers import split_rows as rows  # local import: suppliers builds on this module
    return rows(data, entry, lang)


def matches(item: dict[str, Any], view: str) -> bool:
    hidden = item["archived"] or item["superseded"]
    if view == "archived":
        return hidden
    if hidden:
        return False
    if view == "to_pay":
        return item["kind"] == "expense" and item["state"] in ("unpaid", "partial") and not item["upcoming"]
    if view == "to_confirm":
        return item["kind"] == "expense" and item["state"] == "unknown"
    if view == "to_receive":
        return item["kind"] == "income" and item["state"] != "paid" and not item["upcoming"]
    return True


def search(item: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(str(item.get(key) or "") for key in ("label", "category", "supplier", "invoice_number", "property", "stay_label")).casefold()
    return all(word in haystack for word in query.casefold().split())


def totals(items: list[dict[str, Any]]) -> dict[str, int]:
    """Sums of a list, expenses and income apart (adding them together would mean nothing).

    What is still due today and what is planned later (``upcoming``) are kept apart.
    """
    result = {"expenses": 0, "income": 0, "to_pay": 0, "to_receive": 0, "upcoming": 0, "count": len(items)}
    for item in items:
        if item["archived"] or item["superseded"]:
            continue
        if item["kind"] == "expense":
            result["expenses"] += item["amount"]
            result["upcoming" if item["upcoming"] else "to_pay"] += item["remaining"]
        else:
            result["income"] += item["amount"]
            if not item["upcoming"]:
                result["to_receive"] += item["remaining"]
    return result


# --------------------------------------------------------------------------- monthly series

def add_months(day: date, months: int) -> date:
    """Same day ``months`` later, or the last day of a shorter month (31 January → 28 or 29 February)."""
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    return date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))


def create_series(ledger: Ledger, payload: dict[str, Any], months: int, today: date) -> dict[str, Any]:
    """Monthly entries created at once (loan instalments, subscriptions).

    « Déjà payé » only applies to occurrences whose date has come: the later
    ones are recorded as still to pay, and each one is settled on its own.
    """
    try:
        months = int(months)
    except (TypeError, ValueError) as exc:
        raise RCError("series_months") from exc
    if not 2 <= months <= MAX_SERIES:
        raise RCError("series_months")
    try:
        first = date.fromisoformat(str(payload.get("date") or ""))
        period = (date.fromisoformat(payload["period_start"]), date.fromisoformat(payload["period_end"])) \
            if payload.get("period_start") and payload.get("period_end") else None
    except ValueError as exc:
        raise RCError("date_format") from exc
    series_id = new_id("ser")
    created, payments = [], []
    for index in range(months):
        day = add_months(first, index)
        occurrence = {**payload, "date": day.isoformat()}
        if period:
            occurrence["period_start"] = add_months(period[0], index).isoformat()
            occurrence["period_end"] = add_months(period[1], index).isoformat()
        if payload.get("paid"):
            paid_on = date.fromisoformat(str(payload.get("paid_date") or day.isoformat())) if index == 0 else day
            if day <= today:
                occurrence["paid_date"] = paid_on.isoformat()
            else:
                occurrence.pop("paid", None)
                occurrence.pop("paid_date", None)
                occurrence["payment_declared"] = "unpaid"
        result = ledger.create_entry(occurrence)
        entry = ledger.data["entries"][result["entry"]["id"]]
        entry["series"] = {"id": series_id, "index": index + 1, "count": months}
        created.append(entry["id"])
        if result.get("payment"):
            payments.append(result["payment"]["id"])
    return {"entry": {"id": created[0]}, "series": {"id": series_id, "entries": created, "payments": len(payments)}}
