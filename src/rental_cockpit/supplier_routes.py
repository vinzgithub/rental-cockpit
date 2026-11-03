# Copyright © 2026 Vincent Fournet
"""« Prestataires » API: suppliers, their indicative rates and their invoices.

Same checks as everywhere: signed session, CSRF token on changes, changes by
administrators only, ``op_id`` against double clicks, ``revision`` against
overwriting a newer version. Suppliers are shared by every property; a
reader sees them with the totals of the properties they were granted only.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool

from .engine import entries as entry_views
from .engine import suppliers as supplier_views
from .engine.errors import RCError
from .engine.ledger import Ledger
from .engine.schema import SERVICE_KINDS, SERVICE_UNITS, category_label
from .web import Services, access, current_user, dataset_of, lang_of, read_json, require_csrf, utc_now

SUPPLIER_FIELDS = ("name", "role", "contact", "categories", "rates", "note", "revision", "updated_at")


def register_supplier_routes(app: FastAPI, services: Services) -> None:

    def reader(request: Request, dataset: str):
        acc = access(services, current_user(services, request), dataset)
        registry = services.registries[dataset]
        if not registry.exists:
            raise RCError("not_found")
        return acc, registry

    def visible(data: dict[str, Any], acc) -> dict[str, Any]:
        """The registry as the caller may see it: entries of granted properties only (totals never leak)."""
        return {**data, "entries": {k: e for k, e in data.get("entries", {}).items() if e["property_id"] in acc.property_ids}}

    def options(lang: str) -> dict[str, Any]:
        return {"kinds": [{"id": k, "label": supplier_views._t(supplier_views.KIND_LABELS[k], lang)} for k in SERVICE_KINDS],
                "units": [{"id": u, "label": supplier_views._t(supplier_views.UNIT_LABELS[u], lang)} for u in SERVICE_UNITS]}

    @app.get("/api/suppliers")
    async def list_suppliers(request: Request) -> dict[str, Any]:
        params = request.query_params
        lang = lang_of(request)
        dataset = dataset_of(params.get("dataset"))
        acc, registry = reader(request, dataset)
        data = visible(registry.snapshot(), acc)
        today = services.today()
        paid = entry_views.paid_by_entry(data)
        query = str(params.get("q") or "").casefold()[:80]
        archived = params.get("view") == "archived"
        rows = [supplier_views.summary(data, s, lang, today, paid) for s in data.get("suppliers", {}).values()]
        counts = {"active": sum(1 for r in rows if not r["archived"]), "archived": sum(1 for r in rows if r["archived"])}
        rows = [r for r in rows if r["archived"] == archived
                and all(w in f"{r['name']} {r['role']} {' '.join(c['label'] for c in r['categories'])}".casefold() for w in query.split())]
        rows.sort(key=lambda r: r["name"].casefold())
        return {"dataset": dataset, "role": acc.role, "suppliers": rows, "counts": counts, **options(lang),
                "categories": [{"id": c["id"], "label": category_label(c, lang)} for c in data["categories"].values()
                               if c["kind"] == "expense" and not c.get("archived")]}

    @app.get("/api/suppliers/{supplier_id}")
    async def read_supplier(request: Request, supplier_id: str) -> dict[str, Any]:
        lang = lang_of(request)
        dataset = dataset_of(request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        data = visible(registry.snapshot(), acc)
        supplier = data.get("suppliers", {}).get(supplier_id)
        if supplier is None:
            raise RCError("not_found")
        return supplier_views.summary(data, supplier, lang, services.today())

    async def change(request: Request, supplier_id: str | None, operation) -> dict[str, Any]:
        require_csrf(request)
        payload = await read_json(request)
        lang = lang_of(request, payload)
        dataset = dataset_of(payload.get("dataset") or request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        acc.require_admin()

        def apply(work: dict[str, Any]) -> dict[str, Any]:
            ledger = Ledger(work, acc.user_id)
            return ledger.once(payload.get("op_id"), lambda: operation(ledger, payload))

        result = await run_in_threadpool(lambda: registry.mutate(apply, utc_now()))
        data = registry.snapshot()
        target = (result.get("supplier") or {}).get("id") or supplier_id
        if target in data.get("suppliers", {}):
            result["detail"] = supplier_views.summary(data, data["suppliers"][target], lang, services.today())
        return result

    @app.post("/api/suppliers")
    async def create_supplier(request: Request) -> dict[str, Any]:
        return await change(request, None, lambda ledger, payload: ledger.create_supplier(
            {k: payload[k] for k in SUPPLIER_FIELDS if k in payload}))

    @app.patch("/api/suppliers/{supplier_id}")
    async def update_supplier(request: Request, supplier_id: str) -> dict[str, Any]:
        return await change(request, supplier_id, lambda ledger, payload: ledger.update_supplier(
            supplier_id, {k: payload[k] for k in SUPPLIER_FIELDS if k in payload}))

    @app.post("/api/suppliers/{supplier_id}/archive")
    async def archive_supplier(request: Request, supplier_id: str) -> dict[str, Any]:
        return await change(request, supplier_id, lambda ledger, payload: ledger.set_supplier_archived(
            supplier_id, payload.get("archived", True) is not False))
