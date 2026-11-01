# Copyright © 2026 Vincent Fournet
"""« Séjours » API: list, read, create, change, cancel, restore, delete, payouts.

Every route goes through the same checks as the rest of the application:
signed session, CSRF token on changes, rights resolved on the server for the
requested dataset (real data or demo). Changes are administrator-only, carry
an ``op_id`` so a double click is applied once, and are written all-or-nothing.
Changing a stay needs the ``updated_at`` it was read with: if somebody else
changed it in between, the change is refused (409) instead of overwriting.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool

from .engine import stays as stay_views
from .engine.errors import RCError
from .engine.ledger import Ledger
from .engine.schema import CHANNELS, label
from .web import Services, access, current_user, dataset_of, lang_of, public_property, read_json, require_csrf, scope, utc_now

VIEWS = ("active", "past", "cancelled", "attention", "all")
STAY_FIELDS = ("property_id", "start", "end", "status", "channel", "external_ref", "guest_label", "guests", "amounts", "note",
               "updated_at", "revision")


def _matches(item: dict[str, Any], view: str, today_iso: str) -> bool:
    cancelled = item["status"] == "cancelled"
    if view == "active":
        return not cancelled and item["end"] > today_iso
    if view == "past":
        return not cancelled and item["end"] <= today_iso
    if view == "cancelled":
        return cancelled
    if view == "attention":
        return item["payout_state"] in ("to_confirm", "partial") or (not cancelled and item["payout_state"] == "unknown")
    return True


def _search(item: dict[str, Any], query: str) -> bool:
    if not query:
        return True
    haystack = " ".join(str(item.get(key) or "") for key in ("guest_label", "external_ref", "property", "channel_label")).casefold()
    return all(word in haystack for word in query.casefold().split())


def register_stay_routes(app: FastAPI, services: Services) -> None:

    def reader(request: Request, dataset: str):
        acc = access(services, current_user(services, request), dataset)
        registry = services.registries[dataset]
        if not registry.exists:
            raise RCError("not_found")
        return acc, registry

    def stay_or_404(data: dict[str, Any], acc, stay_id: str) -> dict[str, Any]:
        stay = data.get("stays", {}).get(stay_id)
        if stay is None:
            raise RCError("not_found")
        acc.require_property(stay["property_id"])  # a guessed identifier never leaks a stay
        return stay

    async def change(request: Request, stay_id: str | None, operation) -> dict[str, Any]:
        """Common path of every change: CSRF, admin, op_id, all-or-nothing write, fresh detail back."""
        require_csrf(request)
        payload = await read_json(request)
        lang = lang_of(request, payload)
        dataset = dataset_of(payload.get("dataset") or request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        acc.require_admin()
        if stay_id is not None:
            stay_or_404(registry.snapshot(), acc, stay_id)

        def apply(work: dict[str, Any]) -> dict[str, Any]:
            ledger = Ledger(work, acc.user_id)
            return ledger.once(payload.get("op_id"), lambda: operation(ledger, payload))

        result = await run_in_threadpool(lambda: registry.mutate(apply, utc_now()))
        data = registry.snapshot()
        target = (result.get("stay") or {}).get("id") or stay_id
        if target and target in data.get("stays", {}):
            result["detail"] = stay_views.detail(data, data["stays"][target], services.today(), lang)
        return result

    # ------------------------------------------------------------------ reading

    @app.get("/api/stays")
    async def list_stays(request: Request) -> dict[str, Any]:
        params = request.query_params
        lang = lang_of(request)
        dataset = dataset_of(params.get("dataset"))
        acc, registry = reader(request, dataset)
        selected = scope(acc, params.get("property_id"))
        view = params.get("view") if params.get("view") in VIEWS else "active"
        query = str(params.get("q") or "")[:80]
        data = registry.snapshot()
        today = services.today()
        today_iso = today.isoformat()
        items = [stay_views.summary(data, stay, today, lang) for stay in data.get("stays", {}).values() if stay["property_id"] in selected]
        items = [item for item in items if _search(item, query)]
        counts = {key: sum(1 for item in items if _matches(item, key, today_iso)) for key in VIEWS}
        shown = [item for item in items if _matches(item, view, today_iso)]
        shown.sort(key=lambda item: (item["start"], item["end"]), reverse=view != "active")
        visible = [public_property(p) for pid, p in data["properties"].items() if pid in acc.property_ids]
        return {
            "dataset": dataset, "role": acc.role, "view": view, "today": today_iso, "stays": shown, "counts": counts,
            "properties": sorted(visible, key=lambda p: (p["archived"], p["name"].casefold())),
            "channels": [{"id": key, "label": label("channel", key, lang)} for key in CHANNELS],
        }

    @app.get("/api/stays/{stay_id}")
    async def read_stay(request: Request, stay_id: str) -> dict[str, Any]:
        lang = lang_of(request)
        dataset = dataset_of(request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        data = registry.snapshot()
        stay = stay_or_404(data, acc, stay_id)
        result = stay_views.detail(data, stay, services.today(), lang)
        result["warnings"] = Ledger(data).stay_warnings(stay)
        return result

    # ------------------------------------------------------------------ changes

    @app.post("/api/stays")
    async def create_stay(request: Request) -> dict[str, Any]:
        def operation(ledger: Ledger, payload: dict[str, Any]) -> dict[str, Any]:
            return ledger.create_stay({key: payload[key] for key in STAY_FIELDS if key in payload}, source="manual")
        return await change(request, None, operation)

    @app.patch("/api/stays/{stay_id}")
    async def update_stay(request: Request, stay_id: str) -> dict[str, Any]:
        def operation(ledger: Ledger, payload: dict[str, Any]) -> dict[str, Any]:
            fields = {key: payload[key] for key in STAY_FIELDS if key in payload and key != "property_id"}
            return ledger.update_stay(stay_id, fields)
        return await change(request, stay_id, operation)

    @app.post("/api/stays/{stay_id}/cancel")
    async def cancel_stay(request: Request, stay_id: str) -> dict[str, Any]:
        return await change(request, stay_id, lambda ledger, payload: ledger.cancel_stay(stay_id, payload))

    @app.post("/api/stays/{stay_id}/restore")
    async def restore_stay(request: Request, stay_id: str) -> dict[str, Any]:
        return await change(request, stay_id, lambda ledger, payload: ledger.restore_stay(stay_id, payload))

    @app.delete("/api/stays/{stay_id}")
    async def delete_stay(request: Request, stay_id: str) -> dict[str, Any]:
        return await change(request, stay_id, lambda ledger, payload: ledger.delete_stay(stay_id))

    @app.post("/api/stays/{stay_id}/payouts")
    async def record_payout(request: Request, stay_id: str) -> dict[str, Any]:
        """« Versement reçu » : money received for the stay, on its date (Cash reading)."""
        def operation(ledger: Ledger, payload: dict[str, Any]) -> dict[str, Any]:
            stay = ledger.data["stays"][stay_id]
            amount = {key: payload[key] for key in ("amount", "amount_cents") if key in payload}
            result = ledger.create_payment({
                "property_id": stay["property_id"], "direction": "in", "date": payload.get("date"), **amount,
                "links": [{"type": "stay", "id": stay_id, **amount}],
                "method": payload.get("method", ""), "note": payload.get("note", ""),
            })
            return {**result, "stay": {"id": stay_id}}
        return await change(request, stay_id, operation)

    @app.delete("/api/payments/{payment_id}")
    async def delete_payment(request: Request, payment_id: str) -> dict[str, Any]:
        """Undo a recorded payment (a payout or an expense payment entered by mistake)."""
        require_csrf(request)
        payload = await read_json(request)
        dataset = dataset_of(payload.get("dataset") or request.query_params.get("dataset"))
        lang = lang_of(request, payload)
        acc, registry = reader(request, dataset)
        acc.require_admin()
        payment = registry.snapshot().get("payments", {}).get(payment_id)
        if payment is None:
            raise RCError("not_found")
        acc.require_property(payment["property_id"])
        stay_ids = [link["id"] for link in payment["links"] if link["type"] == "stay"]
        entry_ids = [link["id"] for link in payment["links"] if link["type"] == "entry"]

        def apply(work: dict[str, Any]) -> dict[str, Any]:
            ledger = Ledger(work, acc.user_id)
            return ledger.once(payload.get("op_id"), lambda: ledger.delete_payment(payment_id))

        result = await run_in_threadpool(lambda: registry.mutate(apply, utc_now()))
        data = registry.snapshot()
        if stay_ids and stay_ids[0] in data.get("stays", {}):
            result["detail"] = stay_views.detail(data, data["stays"][stay_ids[0]], services.today(), lang)
        elif entry_ids and entry_ids[0] in data.get("entries", {}):
            from .engine import entries as entry_views  # the « Dépenses » page gets its entry back
            result["detail"] = entry_views.detail(data, data["entries"][entry_ids[0]], lang)
        return result
