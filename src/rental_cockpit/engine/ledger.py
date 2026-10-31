# Copyright © 2026 Vincent Fournet
"""Registry operations: properties, suppliers, categories, stays, entries, payments.

A :class:`Ledger` works on a *working copy* of the registry. The caller
(application layer) copies the registry, applies one operation, saves the
copy, and only then replaces the live registry. If anything fails, the live
registry is untouched: an operation is either fully saved or not at all.

Rules enforced here (references are to the specification):

* amounts are positive integer cents (DON 06), in euros only (DON 05);
* manual corrections keep the previous value and its author (DON 04);
* archiving never deletes history (DON 04);
* a status never replaces a known payment amount (FIN 01, FIN 06);
* service lines must add up to the invoice total (PRE 02);
* allocating a cost to stays never creates a second charge (PRE 04);
* repeated operations with the same ``op_id`` are applied once (DUP 03).
"""
from __future__ import annotations

import re
import secrets
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Callable

from . import money
from .dates import optional_date, parse_date, utc_now_iso
from .errors import RCError, from_value_error
from .schema import (
    CURRENCY,
    EXPENSE_TREATMENTS,
    INCOME_TREATMENTS,
    PAYMENT_DECLARED,
    SERVICE_KINDS,
    SERVICE_UNITS,
    STAY_SOURCES,
    STAY_STATUSES,
    TREATMENTS,
)

HISTORY_LIMIT = 100
AUDIT_LIMIT = 5000
OPS_LIMIT = 500
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# --------------------------------------------------------------------------- helpers

def new_id(prefix: str) -> str:
    """Random, unguessable identifier (``prefix-<16 hex>``)."""
    return f"{prefix}-{secrets.token_hex(8)}"


def clean_text(value: Any, field: str, limit: int, *, required: bool = False, multiline: bool = False) -> str:
    """Trimmed text without control characters. Never interpreted as HTML."""
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").strip()
    if not multiline:
        text = " ".join(text.split())
    if _CONTROL.search(text):
        raise RCError("text_invalid", field=field)
    if len(text) > limit:
        raise RCError("text_too_long", field=field, limit=limit)
    if required and not text:
        raise RCError("text_required", field=field)
    return text


def choice(value: Any, allowed: tuple[str, ...] | set[str], field: str, default: str | None = None) -> str:
    text = str(value if value not in (None, "") else (default or "")).strip()
    if text not in allowed:
        raise RCError("choice_invalid", field=field)
    return text


def read_date(value: Any, field: str) -> date:
    try:
        return parse_date(value)
    except ValueError as exc:
        raise from_value_error(exc, field) from exc


def read_optional_date(value: Any, field: str) -> date | None:
    try:
        return optional_date(value)
    except ValueError as exc:
        raise from_value_error(exc, field) from exc


def read_amount(payload: dict[str, Any], key: str = "amount", *, field: str | None = None,
                allow_negative: bool = False, allow_zero: bool = False, required: bool = True) -> int | None:
    """Amount from a payload: ``<key>_cents`` (integer) or ``<key>`` (text in euros)."""
    try:
        if payload.get(f"{key}_cents") not in (None, ""):
            return money.check_cents(payload[f"{key}_cents"], allow_negative=allow_negative, allow_zero=allow_zero)
        raw = payload.get(key)
        if raw in (None, ""):
            if required:
                raise ValueError("amount_required")
            return None
        return money.parse_amount(raw, allow_negative=allow_negative, allow_zero=allow_zero)
    except ValueError as exc:
        raise from_value_error(exc, field or key) from exc


def read_quantity(value: Any, field: str = "quantity") -> str | None:
    """Quantity kept as a decimal string (``"2.5"`` hours) to stay exact."""
    if value in (None, ""):
        return None
    try:
        quantity = Decimal(str(value).replace(",", "."))
    except InvalidOperation as exc:
        raise RCError("choice_invalid", field=field) from exc
    if not quantity.is_finite() or quantity < 0 or quantity > 100000 or quantity != quantity.quantize(Decimal("0.01")):
        raise RCError("choice_invalid", field=field)
    return format(quantity.normalize(), "f")


def iso(value: date | None) -> str:
    return value.isoformat() if value else ""


# --------------------------------------------------------------------------- ledger

class Ledger:
    """Operations on one registry working copy, on behalf of one actor."""

    def __init__(self, data: dict[str, Any], actor: str = "system", clock: Callable[[], str] = utc_now_iso) -> None:
        self.data = data
        self.actor = actor or "system"
        self.clock = clock

    # ----------------------------------------------------------------- plumbing

    def once(self, op_id: str | None, action: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        """Run ``action`` unless the same client operation was already applied.

        The interface sends a fresh ``op_id`` for each user action. A double
        click, or a network retry, sends the same one again: the stored result
        is returned and nothing is written twice (DUP 03).
        """
        if op_id:
            op_id = clean_text(op_id, "op_id", 80)
            done = self.data.setdefault("ops", {}).get(op_id)
            if done is not None:
                return {**deepcopy(done["result"]), "replayed": True}
        result = action()
        if op_id:
            ops = self.data.setdefault("ops", {})
            ops[op_id] = {"at": self.clock(), "result": deepcopy(result)}
            if len(ops) > OPS_LIMIT:
                for old in sorted(ops, key=lambda key: ops[key]["at"])[: len(ops) - OPS_LIMIT]:
                    ops.pop(old, None)
        return result

    def audit(self, action: str, target: str, result: str = "ok", detail: str = "") -> None:
        """Operational journal (SEC 05): who, when, what, on which item, outcome.

        It never stores amounts of PDFs, document content or secrets. It is a
        helpful trace, not a tamper-proof legal archive.
        """
        log = self.data.setdefault("audit", [])
        log.append({"at": self.clock(), "by": self.actor, "action": action, "target": target, "result": result, "detail": detail[:200]})
        if len(log) > AUDIT_LIMIT:
            del log[: len(log) - AUDIT_LIMIT]
        self.data["updated_at"] = self.clock()

    def _history(self, item: dict[str, Any], before: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
        changes = {f: [before.get(f), item.get(f)] for f in fields if before.get(f) != item.get(f)}
        if changes:
            history = item.setdefault("history", [])
            history.append({"at": self.clock(), "by": self.actor, "changes": deepcopy(changes)})
            if len(history) > HISTORY_LIMIT:
                del history[: len(history) - HISTORY_LIMIT]
            item["updated_at"] = self.clock()
            item["updated_by"] = self.actor
        return list(changes)

    def _get(self, collection: str, item_id: Any) -> dict[str, Any]:
        item = self.data.get(collection, {}).get(str(item_id or ""))
        if item is None:
            raise RCError("not_found")
        return item

    def _check_revision(self, item: dict[str, Any], payload: dict[str, Any]) -> None:
        expected = payload.get("updated_at")
        if expected is not None and expected != item.get("updated_at"):
            raise RCError("stale_revision")

    def _stamp(self, item: dict[str, Any]) -> dict[str, Any]:
        now = self.clock()
        item.update(created_at=now, created_by=self.actor, updated_at=now, updated_by=self.actor, history=[])
        return item

    def property(self, property_id: Any, *, writable: bool = True) -> dict[str, Any]:
        prop = self._get("properties", property_id)
        if writable and prop.get("archived"):
            raise RCError("property_archived", name=prop.get("name", ""))
        return prop

    # ----------------------------------------------------------------- properties

    def _property_fields(self, payload: dict[str, Any], current: dict[str, Any] | None = None) -> dict[str, Any]:
        current = current or {}
        get = lambda key, default=None: payload[key] if key in payload else current.get(key, default)  # noqa: E731
        currency = clean_text(get("currency", CURRENCY), "currency", 3).upper() or CURRENCY
        if currency != CURRENCY:
            raise RCError("currency_unsupported", currency=currency)
        availability = []
        for block in get("unavailable", []) or []:
            start = read_date(block.get("start"), "unavailable.start")
            end = read_date(block.get("end"), "unavailable.end")
            if end <= start:
                raise RCError("stay_dates")
            availability.append({"start": iso(start), "end": iso(end), "reason": clean_text(block.get("reason"), "reason", 120)})
        capacity = get("capacity")
        bedrooms = get("bedrooms")
        return {
            "name": clean_text(get("name"), "name", 80, required=True),
            "kind": choice(get("kind", "apartment"), ("apartment", "house", "studio", "room", "other"), "kind", "apartment"),
            "currency": currency,
            "timezone": clean_text(get("timezone", ""), "timezone", 64),
            "capacity": _small_int(capacity, "capacity"),
            "bedrooms": _small_int(bedrooms, "bedrooms"),
            "address": clean_text(get("address", ""), "address", 240, multiline=True),  # private, optional
            "activity_start": iso(read_optional_date(get("activity_start", ""), "activity_start")),
            "unavailable": sorted(availability, key=lambda b: b["start"]),
            "note": clean_text(get("note", ""), "note", 600, multiline=True),
        }

    def create_property(self, payload: dict[str, Any]) -> dict[str, Any]:
        prop = self._stamp({"id": new_id("prop"), **self._property_fields(payload), "archived": False})
        self.data["properties"][prop["id"]] = prop
        self.data["settings"]["onboarding"]["property"] = True
        self.audit("property.create", prop["id"])
        return {"property": deepcopy(prop)}

    def update_property(self, property_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        prop = self._get("properties", property_id)
        self._check_revision(prop, payload)
        before = deepcopy(prop)
        prop.update(self._property_fields(payload, prop))
        changed = self._history(prop, before, tuple(self._property_fields({}, before)))
        self.audit("property.update", prop["id"], detail=",".join(changed))
        return {"property": deepcopy(prop)}

    def set_property_archived(self, property_id: str, archived: bool) -> dict[str, Any]:
        prop = self._get("properties", property_id)
        before = deepcopy(prop)
        prop["archived"] = bool(archived)
        self._history(prop, before, ("archived",))
        self.audit("property.archive" if archived else "property.unarchive", prop["id"])
        return {"property": deepcopy(prop)}

    # ----------------------------------------------------------------- suppliers

    def _supplier_fields(self, payload: dict[str, Any], current: dict[str, Any] | None = None) -> dict[str, Any]:
        current = current or {}
        get = lambda key, default=None: payload[key] if key in payload else current.get(key, default)  # noqa: E731
        categories = [c for c in (get("categories", []) or []) if c in self.data["categories"]]
        rates = []
        for rate in get("rates", []) or []:
            rates.append({
                "kind": choice(rate.get("kind"), SERVICE_KINDS, "rates.kind"),
                "unit": choice(rate.get("unit"), SERVICE_UNITS, "rates.unit"),
                "unit_price_cents": read_amount(rate, "unit_price", field="rates.unit_price"),
                "label": clean_text(rate.get("label"), "rates.label", 80),
            })
        return {
            "name": clean_text(get("name"), "name", 120, required=True),
            "role": clean_text(get("role", ""), "role", 120),
            "contact": clean_text(get("contact", ""), "contact", 240, multiline=True),
            "categories": categories,
            "rates": rates,  # indicative only, never applied as a general truth (DON 02)
            "note": clean_text(get("note", ""), "note", 600, multiline=True),
        }

    def create_supplier(self, payload: dict[str, Any]) -> dict[str, Any]:
        supplier = self._stamp({"id": new_id("sup"), **self._supplier_fields(payload), "archived": False})
        self.data["suppliers"][supplier["id"]] = supplier
        self.audit("supplier.create", supplier["id"])
        return {"supplier": deepcopy(supplier)}

    def update_supplier(self, supplier_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        supplier = self._get("suppliers", supplier_id)
        self._check_revision(supplier, payload)
        before = deepcopy(supplier)
        supplier.update(self._supplier_fields(payload, supplier))
        self._history(supplier, before, ("name", "role", "contact", "categories", "rates", "note"))
        self.audit("supplier.update", supplier["id"])
        return {"supplier": deepcopy(supplier)}

    def set_supplier_archived(self, supplier_id: str, archived: bool) -> dict[str, Any]:
        supplier = self._get("suppliers", supplier_id)
        before = deepcopy(supplier)
        supplier["archived"] = bool(archived)
        self._history(supplier, before, ("archived",))
        self.audit("supplier.archive" if archived else "supplier.unarchive", supplier["id"])
        return {"supplier": deepcopy(supplier)}

    # ----------------------------------------------------------------- categories

    def create_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        kind = choice(payload.get("kind"), ("income", "expense"), "kind")
        allowed = INCOME_TREATMENTS if kind == "income" else EXPENSE_TREATMENTS
        category = {
            "id": new_id("cat"),
            "kind": kind,
            "treatment": choice(payload.get("treatment"), tuple(t for t in TREATMENTS if t in allowed), "treatment"),
            "label": clean_text(payload.get("label"), "label", 60, required=True),
            "fr": "", "en": "", "icon": "tag", "builtin": False, "archived": False,
        }
        self.data["categories"][category["id"]] = category
        self.audit("category.create", category["id"])
        return {"category": deepcopy(category)}

    def update_category(self, category_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        category = self._get("categories", category_id)
        if "label" in payload:
            category["label"] = clean_text(payload.get("label"), "label", 60)
        if "archived" in payload:
            category["archived"] = bool(payload["archived"])
        if "treatment" in payload and not category.get("builtin"):
            allowed = INCOME_TREATMENTS if category["kind"] == "income" else EXPENSE_TREATMENTS
            category["treatment"] = choice(payload["treatment"], tuple(t for t in TREATMENTS if t in allowed), "treatment")
        self.audit("category.update", category["id"])
        return {"category": deepcopy(category)}

    # ----------------------------------------------------------------- stays

    def _stay_amounts(self, payload: dict[str, Any], current: dict[str, Any] | None = None) -> dict[str, int | None]:
        amounts = dict((current or {}).get("amounts") or {})
        raw = payload.get("amounts", {}) or {}
        for key in ("gross", "commission", "payout", "taxes_collected", "deposit"):
            if key in raw or f"{key}_cents" in raw:
                # ``None`` means "not known yet", which is different from zero (FIN 05).
                amounts[key] = read_amount(raw, key, field=f"amounts.{key}", allow_zero=True, required=False)
            amounts.setdefault(key, None)
        return amounts

    def create_stay(self, payload: dict[str, Any], *, source: str = "manual", origin_import: str = "") -> dict[str, Any]:
        prop = self.property(payload.get("property_id"))
        start = read_date(payload.get("start"), "start")
        end = read_date(payload.get("end"), "end")
        if end <= start:
            raise RCError("stay_dates")
        external_ref = clean_text(payload.get("external_ref", ""), "external_ref", 80)
        if external_ref:
            for other in self.data["stays"].values():
                if other["property_id"] == prop["id"] and other.get("external_ref") == external_ref and other.get("source") == source:
                    raise RCError("stay_external_ref_exists", ref=external_ref)
        stay = self._stamp({
            "id": new_id("stay"),
            "property_id": prop["id"],
            "source": choice(source, STAY_SOURCES, "source"),
            "external_ref": external_ref,
            "start": iso(start),
            "end": iso(end),
            "status": choice(payload.get("status"), STAY_STATUSES, "status", "confirmed"),
            "guest_label": clean_text(payload.get("guest_label", ""), "guest_label", 80),
            "guests": _small_int(payload.get("guests"), "guests"),
            "amounts": self._stay_amounts(payload),
            "adjustments": [],
            "note": clean_text(payload.get("note", ""), "note", 600, multiline=True),
            "origin_import": origin_import,
        })
        self.data["stays"][stay["id"]] = stay
        self.data["settings"]["onboarding"]["first_record"] = True
        self.audit("stay.create", stay["id"])
        return {"stay": deepcopy(stay), "warnings": self.stay_warnings(stay)}

    def update_stay(self, stay_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        stay = self._get("stays", stay_id)
        self._check_revision(stay, payload)
        self.property(stay["property_id"])
        before = deepcopy(stay)
        if "start" in payload or "end" in payload:
            start = read_date(payload.get("start", stay["start"]), "start")
            end = read_date(payload.get("end", stay["end"]), "end")
            if end <= start:
                raise RCError("stay_dates")
            stay["start"], stay["end"] = iso(start), iso(end)
        if "status" in payload:
            stay["status"] = choice(payload["status"], STAY_STATUSES, "status")
        for key, limit in (("guest_label", 80), ("note", 600)):
            if key in payload:
                stay[key] = clean_text(payload[key], key, limit, multiline=key == "note")
        if "guests" in payload:
            stay["guests"] = _small_int(payload.get("guests"), "guests")
        if "amounts" in payload:
            stay["amounts"] = self._stay_amounts(payload, stay)
        changed = self._history(stay, before, ("start", "end", "status", "guest_label", "guests", "amounts", "note"))
        self.audit("stay.update", stay["id"], detail=",".join(changed))
        return {"stay": deepcopy(stay), "warnings": self.stay_warnings(stay)}

    def add_stay_adjustment(self, stay_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Refund or correction: added next to the original amounts, never over them (IMP 01)."""
        stay = self._get("stays", stay_id)
        self.property(stay["property_id"])
        adjustment = {
            "id": new_id("adj"),
            "date": iso(read_date(payload.get("date"), "date")),
            "amount": read_amount(payload, "amount", allow_negative=True),
            "kind": choice(payload.get("kind"), ("refund", "adjustment", "extra"), "kind", "adjustment"),
            "note": clean_text(payload.get("note"), "note", 300, required=True),
            "at": self.clock(),
            "by": self.actor,
        }
        stay.setdefault("adjustments", []).append(adjustment)
        stay["updated_at"], stay["updated_by"] = self.clock(), self.actor
        self.audit("stay.adjustment", stay["id"])
        return {"stay": deepcopy(stay)}

    def delete_stay(self, stay_id: str) -> dict[str, Any]:
        stay = self._get("stays", stay_id)
        if stay.get("source") not in ("manual", "demo"):
            raise RCError("stay_not_manual")
        links = sum(1 for p in self.data["payments"].values() for link in p["links"] if link["type"] == "stay" and link["id"] == stay_id)
        links += sum(1 for e in self.data["entries"].values() for a in e.get("allocations", []) if a.get("stay_id") == stay_id)
        links += sum(1 for e in self.data["entries"].values() if e.get("stay_id") == stay_id)
        if links:
            raise RCError("stay_linked", count=links)
        del self.data["stays"][stay_id]
        self.audit("stay.delete", stay_id)
        return {"deleted": stay_id}

    def stay_warnings(self, stay: dict[str, Any]) -> list[dict[str, Any]]:
        """Non-blocking checks shown after saving: overlap, unavailable dates."""
        warnings = []
        start, end = parse_date(stay["start"]), parse_date(stay["end"])
        if stay["status"] != "cancelled":
            for other in self.data["stays"].values():
                if other["id"] == stay["id"] or other["property_id"] != stay["property_id"] or other["status"] == "cancelled":
                    continue
                if parse_date(other["start"]) < end and start < parse_date(other["end"]):
                    warnings.append(RCError("stay_overlap", label=other.get("guest_label") or other.get("external_ref") or "—", start=other["start"], end=other["end"]).as_dict())
            prop = self.data["properties"].get(stay["property_id"], {})
            for block in prop.get("unavailable", []):
                if parse_date(block["start"]) < end and start < parse_date(block["end"]):
                    warnings.append(RCError("stay_unavailable", start=block["start"], end=block["end"]).as_dict())
        return warnings

    # ----------------------------------------------------------------- entries

    def category(self, category_id: Any, kind: str) -> dict[str, Any]:
        category = self._get("categories", category_id)
        if category["kind"] != kind:
            raise RCError("category_kind", name=category.get("label") or category.get("fr") or category["id"])
        return category

    def _lines(self, payload: dict[str, Any], total: int) -> list[dict[str, Any]]:
        lines = []
        for index, raw in enumerate(payload.get("lines") or []):
            kind = choice(raw.get("kind"), SERVICE_KINDS, "lines.kind")
            quantity = read_quantity(raw.get("quantity"))
            unit = choice(raw.get("unit"), SERVICE_UNITS, "lines.unit", "flat") if raw.get("unit") else ""
            unit_price = read_amount(raw, "unit_price", field="lines.unit_price", required=False)
            amount = read_amount(raw, "amount", field="lines.amount", allow_negative=kind in ("discount", "adjustment"), required=False)
            if amount is None and quantity is not None and unit_price is not None:
                product = Decimal(quantity) * unit_price
                if product != product.to_integral_value():
                    raise RCError("amount_format", field="lines.amount")
                amount = int(product)
            if amount is None:
                raise RCError("amount_required", field="lines.amount")
            if kind == "discount" and amount > 0:
                amount = -amount
            note = clean_text(raw.get("note", ""), "lines.note", 200)
            if kind == "adjustment" and not note:
                raise RCError("adjustment_note_required")
            lines.append({
                "id": str(raw.get("id") or f"line-{index + 1}")[:40],
                "kind": kind,
                "label": clean_text(raw.get("label", ""), "lines.label", 120),
                "quantity": quantity,
                "unit": unit,
                "unit_price_cents": unit_price,
                "amount": amount,
                "intervention_date": iso(read_optional_date(raw.get("intervention_date"), "lines.intervention_date")),
                "note": note,
            })
        if lines:
            line_total = sum(line["amount"] for line in lines)
            if line_total != total:
                raise RCError("lines_total_mismatch", lines=money.format_cents(line_total), total=money.format_cents(total))
        return lines

    def _loan_split(self, payload: dict[str, Any], category: dict[str, Any], total: int) -> dict[str, int | None] | None:
        raw = payload.get("loan_split")
        if not raw:
            return None
        if category["treatment"] != "financing":
            raise RCError("loan_split_category")
        split = {key: read_amount(raw, key, field=f"loan_split.{key}", allow_zero=True, required=False) for key in ("principal", "interest", "insurance")}
        known = [value for value in split.values() if value is not None]
        if len(known) == 3 and sum(known) != total:
            raise RCError("loan_split_mismatch", split=money.format_cents(sum(known)), total=money.format_cents(total))
        if len(known) < 3 and sum(known) > total:
            raise RCError("loan_split_mismatch", split=money.format_cents(sum(known)), total=money.format_cents(total))
        return split

    def create_entry(self, payload: dict[str, Any], *, origin: dict[str, Any] | None = None) -> dict[str, Any]:
        """Record an expense or an income (manual entry, or created from an invoice)."""
        prop = self.property(payload.get("property_id"))
        kind = choice(payload.get("kind"), ("expense", "income"), "kind", "expense")
        category = self.category(payload.get("category_id"), kind)
        if category.get("archived"):
            raise RCError("archived")
        amount = read_amount(payload, "amount")
        ref_date = read_date(payload.get("date"), "date")
        period_start = read_optional_date(payload.get("period_start"), "period_start")
        period_end = read_optional_date(payload.get("period_end"), "period_end")
        if (period_start is None) != (period_end is None) or (period_start and period_end <= period_start):
            raise RCError("stay_dates")
        supplier_id = payload.get("supplier_id") or ""
        if supplier_id:
            self._get("suppliers", supplier_id)
        stay_id = payload.get("stay_id") or ""
        if stay_id:
            stay = self._get("stays", stay_id)
            if stay["property_id"] != prop["id"]:
                raise RCError("allocation_stay_property")
        entry = self._stamp({
            "id": new_id("ent"),
            "property_id": prop["id"],
            "kind": kind,
            "category_id": category["id"],
            "label": clean_text(payload.get("label"), "label", 140, required=True),
            "amount": amount,
            "currency": CURRENCY,
            "date": iso(ref_date),
            "period_start": iso(period_start),
            "period_end": iso(period_end),
            "supplier_id": supplier_id,
            "stay_id": stay_id,
            "invoice_number": clean_text(payload.get("invoice_number", ""), "invoice_number", 80),
            "lines": self._lines(payload, amount),
            "allocations": [],
            "loan_split": self._loan_split(payload, category, amount),
            "payment_declared": choice(payload.get("payment_declared"), PAYMENT_DECLARED, "payment_declared", "unknown"),
            "superseded_by": "",
            "archived": False,
            "origin": origin or {"type": "manual"},
            "note": clean_text(payload.get("note", ""), "note", 600, multiline=True),
        })
        self.data["entries"][entry["id"]] = entry
        if payload.get("allocations"):
            self._apply_allocations(entry, payload["allocations"])
        self.data["settings"]["onboarding"]["first_record"] = True
        self.audit("entry.create", entry["id"])
        result: dict[str, Any] = {"entry": deepcopy(entry)}
        if payload.get("paid"):
            # "Payé" typed by the user is turned into a real payment with a date,
            # so the cash view knows when the money left (FIN 06).
            paid_on = payload.get("paid_date") or entry["date"]
            payment = self.create_payment({
                "property_id": prop["id"], "direction": "out" if kind == "expense" else "in",
                "date": paid_on, "amount_cents": amount,
                "links": [{"type": "entry", "id": entry["id"], "amount_cents": amount}],
                "method": payload.get("payment_method", ""),
            })
            result["payment"] = payment["payment"]
        return result

    def update_entry(self, entry_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        entry = self._get("entries", entry_id)
        self._check_revision(entry, payload)
        if entry.get("archived"):
            raise RCError("archived")
        if entry.get("superseded_by"):
            raise RCError("superseded")
        self.property(entry["property_id"])
        before = deepcopy(entry)
        if "category_id" in payload:
            entry["category_id"] = self.category(payload["category_id"], entry["kind"])["id"]
        if "amount" in payload or "amount_cents" in payload:
            entry["amount"] = read_amount(payload, "amount")
            paid = self.entry_paid(entry["id"])
            if paid > entry["amount"]:
                raise RCError("payment_exceeds", remaining=money.format_cents(entry["amount"]))
        if "date" in payload:
            entry["date"] = iso(read_date(payload["date"], "date"))
        if "period_start" in payload or "period_end" in payload:
            ps = read_optional_date(payload.get("period_start"), "period_start")
            pe = read_optional_date(payload.get("period_end"), "period_end")
            if (ps is None) != (pe is None) or (ps and pe <= ps):
                raise RCError("stay_dates")
            entry["period_start"], entry["period_end"] = iso(ps), iso(pe)
        for key, limit in (("label", 140), ("note", 600), ("invoice_number", 80)):
            if key in payload:
                entry[key] = clean_text(payload[key], key, limit, required=key == "label", multiline=key == "note")
        if "supplier_id" in payload:
            if payload["supplier_id"]:
                self._get("suppliers", payload["supplier_id"])
            entry["supplier_id"] = payload["supplier_id"] or ""
        if "payment_declared" in payload:
            entry["payment_declared"] = choice(payload["payment_declared"], PAYMENT_DECLARED, "payment_declared")
        if "lines" in payload or "amount" in payload or "amount_cents" in payload:
            entry["lines"] = self._lines({"lines": payload.get("lines", entry.get("lines"))}, entry["amount"])
        category = self.data["categories"][entry["category_id"]]
        if "loan_split" in payload:
            entry["loan_split"] = self._loan_split(payload, category, entry["amount"])
        elif entry.get("loan_split"):
            entry["loan_split"] = self._loan_split({"loan_split": entry["loan_split"]}, category, entry["amount"])
        if "allocations" in payload:
            self._apply_allocations(entry, payload["allocations"])
        else:
            self._validate_allocations(entry, entry.get("allocations", []))
        changed = self._history(entry, before, ("category_id", "amount", "date", "period_start", "period_end", "label", "note",
                                                "invoice_number", "supplier_id", "payment_declared", "lines", "allocations", "loan_split"))
        self.audit("entry.update", entry["id"], detail=",".join(changed))
        return {"entry": deepcopy(entry)}

    def set_entry_archived(self, entry_id: str, archived: bool) -> dict[str, Any]:
        entry = self._get("entries", entry_id)
        before = deepcopy(entry)
        entry["archived"] = bool(archived)
        self._history(entry, before, ("archived",))
        self.audit("entry.archive" if archived else "entry.unarchive", entry["id"])
        return {"entry": deepcopy(entry)}

    # Allocation of a cost to stays is analytical: it explains *what* a cost
    # served, it never adds a charge (PRE 03, PRE 04).

    def _validate_allocations(self, entry: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        lines = {line["id"]: line for line in entry.get("lines", [])}
        result = []
        for raw in rows:
            amount = read_amount(raw, "amount", field="allocations.amount")
            line_id = str(raw.get("line_id") or "")
            if lines and line_id not in lines:
                raise RCError("allocation_line_required")
            stay_id = str(raw.get("stay_id") or "")
            if stay_id:
                stay = self._get("stays", stay_id)
                if stay["property_id"] != entry["property_id"]:
                    raise RCError("allocation_stay_property")
            result.append({"line_id": line_id, "stay_id": stay_id, "amount": amount})
        if lines:
            for line_id, line in lines.items():
                used = sum(r["amount"] for r in result if r["line_id"] == line_id)
                if used > abs(line["amount"]):
                    raise RCError("allocation_exceeds", what=line.get("label") or line["kind"], total=money.format_cents(abs(line["amount"])))
        if sum(r["amount"] for r in result) > entry["amount"]:
            raise RCError("allocation_exceeds", what=entry["label"], total=money.format_cents(entry["amount"]))
        return result

    def _apply_allocations(self, entry: dict[str, Any], rows: list[dict[str, Any]]) -> None:
        entry["allocations"] = self._validate_allocations(entry, rows)

    def set_allocations(self, entry_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        entry = self._get("entries", entry_id)
        self._check_revision(entry, payload)
        before = deepcopy(entry)
        self._apply_allocations(entry, payload.get("allocations") or [])
        self._history(entry, before, ("allocations",))
        self.audit("entry.allocate", entry["id"])
        return {"entry": deepcopy(entry), "remaining": allocation_remaining(entry)}

    # ----------------------------------------------------------------- payments

    def entry_paid(self, entry_id: str) -> int:
        return sum(link["amount"] for p in self.data["payments"].values() for link in p["links"] if link["type"] == "entry" and link["id"] == entry_id)

    def create_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        prop = self.property(payload.get("property_id"))
        direction = choice(payload.get("direction"), ("out", "in"), "direction")
        amount = read_amount(payload, "amount")
        links = []
        for raw in payload.get("links") or []:
            link_type = choice(raw.get("type"), ("entry", "stay"), "links.type")
            target = self._get("entries" if link_type == "entry" else "stays", raw.get("id"))
            if target["property_id"] != prop["id"]:
                raise RCError("forbidden_property")
            link_amount = read_amount(raw, "amount", field="links.amount")
            if link_type == "entry":
                expected = "out" if target["kind"] == "expense" else "in"
                if direction != expected:
                    raise RCError("payment_direction")
                remaining = target["amount"] - self.entry_paid(target["id"])
                if link_amount > remaining:
                    raise RCError("payment_exceeds", remaining=money.format_cents(remaining))
            elif direction != "in":
                raise RCError("payment_direction")
            links.append({"type": link_type, "id": target["id"], "amount": link_amount})
        if not links or sum(link["amount"] for link in links) != amount:
            raise RCError("payment_links_mismatch", links=money.format_cents(sum(link["amount"] for link in links)), total=money.format_cents(amount))
        payment = self._stamp({
            "id": new_id("pay"),
            "property_id": prop["id"],
            "direction": direction,
            "date": iso(read_date(payload.get("date"), "date")),
            "amount": amount,
            "links": links,
            "method": clean_text(payload.get("method", ""), "method", 40),
            "note": clean_text(payload.get("note", ""), "note", 300),
            "origin": payload.get("origin") or {"type": "manual"},
        })
        self.data["payments"][payment["id"]] = payment
        self.audit("payment.create", payment["id"])
        return {"payment": deepcopy(payment)}

    def delete_payment(self, payment_id: str) -> dict[str, Any]:
        self._get("payments", payment_id)
        del self.data["payments"][payment_id]
        self.audit("payment.delete", payment_id)
        return {"deleted": payment_id}


# --------------------------------------------------------------------------- derived values

def entry_payment_status(data: dict[str, Any], entry: dict[str, Any]) -> tuple[str, int]:
    """(status, paid cents). Status is derived from real payments first (FIN 01)."""
    paid = sum(link["amount"] for p in data["payments"].values() for link in p["links"] if link["type"] == "entry" and link["id"] == entry["id"])
    if paid >= entry["amount"]:
        return "paid", paid
    if paid > 0:
        return "partial", paid
    return entry.get("payment_declared") or "unknown", 0


def allocation_remaining(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """What is left to allocate, per service line (or for the whole entry)."""
    rows = entry.get("allocations") or []
    if entry.get("lines"):
        result = []
        for line in entry["lines"]:
            if line["kind"] in ("discount", "tax", "adjustment"):
                continue
            used = sum(r["amount"] for r in rows if r.get("line_id") == line["id"])
            result.append({"line_id": line["id"], "kind": line["kind"], "label": line.get("label", ""), "amount": line["amount"], "allocated": used, "remaining": line["amount"] - used})
        return result
    used = sum(r["amount"] for r in rows)
    return [{"line_id": "", "kind": "", "label": entry.get("label", ""), "amount": entry["amount"], "allocated": used, "remaining": entry["amount"] - used}]


def _small_int(value: Any, field: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(str(value))
    except ValueError as exc:
        raise RCError("choice_invalid", field=field) from exc
    if not 0 <= number <= 999:
        raise RCError("choice_invalid", field=field)
    return number
