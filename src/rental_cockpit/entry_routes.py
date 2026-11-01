# Copyright © 2026 Vincent Fournet
"""« Dépenses » API: expenses and income outside stays, their payments, the categories and the CSV exports.

Same checks as the rest of the application: signed session, CSRF token on
changes, rights resolved on the server for the requested dataset, changes
by administrators only, an ``op_id`` so a double click is applied once, and
a ``revision`` so a change made on an outdated copy is refused (409).
Readers see the entries of the properties they were granted, and can export
them; they cannot change anything.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from .engine import documents as document_views
from .engine import entries as entry_views
from .engine import exports
from .engine import stays as stay_views
from .engine import suppliers as supplier_views
from .engine.errors import RCError
from .engine.ledger import Ledger
from .engine.schema import EXPENSE_TREATMENTS, INCOME_TREATMENTS, TREATMENTS, category_label, label
from .stay_routes import VIEWS as STAY_VIEWS
from .stay_routes import _matches as stay_matches
from .stay_routes import _search as stay_search
from .web import Services, access, current_user, dataset_of, lang_of, public_property, read_json, require_csrf, scope, utc_now

ENTRY_FIELDS = ("property_id", "kind", "category_id", "label", "amount", "amount_cents", "date", "period_start", "period_end", "lines",
                "supplier_id", "stay_id", "invoice_number", "loan_split", "payment_declared", "note", "paid", "paid_date",
                "payment_method", "revision", "updated_at")
MAX_ROWS = 500


def _categories(data: dict[str, Any], lang: str) -> list[dict[str, Any]]:
    used: dict[str, int] = {}
    for entry in data.get("entries", {}).values():
        used[entry["category_id"]] = used.get(entry["category_id"], 0) + 1
    rows = [{"id": c["id"], "kind": c["kind"], "treatment": c["treatment"], "treatment_label": label("treatment", c["treatment"], lang),
             "label": category_label(c, lang), "custom_label": c.get("label", ""), "default_label": c.get("fr" if lang == "fr" else "en", ""),
             "builtin": bool(c.get("builtin")), "archived": bool(c.get("archived")), "entries": used.get(c["id"], 0)}
            for c in data.get("categories", {}).values()]
    order = {t: i for i, t in enumerate(TREATMENTS)}
    return sorted(rows, key=lambda c: (c["kind"] != "expense", order.get(c["treatment"], 9), c["archived"], c["label"].casefold()))


def with_documents(detail: dict[str, Any], data: dict[str, Any], acc, lang: str) -> dict[str, Any]:
    """The PDFs attached to an entry, for whoever was granted the documents of its property (SEC 02)."""
    allowed = acc.sees_documents(detail["property_id"])
    detail["documents_access"] = allowed
    detail["document_list"] = [document_views.summary(data, d, lang) for d in data.get("documents", {}).values()
                               if detail["id"] in d.get("entry_ids", [])] if allowed else []
    return detail


def register_entry_routes(app: FastAPI, services: Services) -> None:

    def reader(request: Request, dataset: str):
        acc = access(services, current_user(services, request), dataset)
        registry = services.registries[dataset]
        if not registry.exists:
            raise RCError("not_found")
        return acc, registry

    def entry_or_404(data: dict[str, Any], acc, entry_id: str) -> dict[str, Any]:
        entry = data.get("entries", {}).get(entry_id)
        if entry is None:
            raise RCError("not_found")
        acc.require_property(entry["property_id"])  # a guessed identifier never leaks an entry
        return entry

    async def change(request: Request, entry_id: str | None, operation) -> dict[str, Any]:
        """Common path of every change: CSRF, admin, op_id, all-or-nothing write, fresh detail back."""
        require_csrf(request)
        payload = await read_json(request)
        lang = lang_of(request, payload)
        dataset = dataset_of(payload.get("dataset") or request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        acc.require_admin()
        if entry_id is not None:
            entry_or_404(registry.snapshot(), acc, entry_id)
        elif payload.get("property_id"):
            acc.require_property(payload["property_id"])

        def apply(work: dict[str, Any]) -> dict[str, Any]:
            ledger = Ledger(work, acc.user_id)
            return ledger.once(payload.get("op_id"), lambda: operation(ledger, payload))

        result = await run_in_threadpool(lambda: registry.mutate(apply, utc_now()))
        data = registry.snapshot()
        target = (result.get("entry") or {}).get("id") or entry_id
        if target and target in data.get("entries", {}):
            result["detail"] = with_documents(entry_views.detail(data, data["entries"][target], lang, services.today()), data, acc, lang)
        return result

    def listing(request: Request) -> tuple[dict[str, Any], Any, str, list[dict[str, Any]], dict[str, int], str]:
        params = request.query_params
        lang = lang_of(request)
        dataset = dataset_of(params.get("dataset"))
        acc, registry = reader(request, dataset)
        selected = scope(acc, params.get("property_id"))
        view = params.get("view") if params.get("view") in entry_views.VIEWS else "all"
        kind = params.get("kind") if params.get("kind") in ("expense", "income") else ""
        category = str(params.get("category_id") or "")
        supplier = str(params.get("supplier_id") or "")
        year = str(params.get("year") or "")[:4]
        query = str(params.get("q") or "")[:80]
        data = registry.snapshot()
        paid = entry_views.paid_by_entry(data)
        today = services.today()
        items = [entry_views.summary(data, e, lang, paid.get(e["id"], 0), today) for e in data.get("entries", {}).values() if e["property_id"] in selected]
        items = [i for i in items if entry_views.search(i, query) and (not kind or i["kind"] == kind)
                 and (not category or i["category_id"] == category) and (not year or i["date"].startswith(year))
                 and (not supplier or i["supplier_id"] == supplier)]
        counts = {key: sum(1 for i in items if entry_views.matches(i, key)) for key in entry_views.VIEWS}
        shown = [i for i in items if entry_views.matches(i, view)]
        if view in ("to_pay", "to_confirm", "to_receive"):
            shown.sort(key=lambda i: (i["date"], i["label"].casefold()))  # oldest debt first
        else:
            # Newest first, then what is planned later (next instalments), soonest first.
            past = sorted((i for i in shown if not i["upcoming"]), key=lambda i: (i["date"], i["label"].casefold()), reverse=True)
            shown = past + sorted((i for i in shown if i["upcoming"]), key=lambda i: (i["date"], i["label"].casefold()))
        return data, acc, dataset, shown, counts, view

    # ------------------------------------------------------------------ reading

    @app.get("/api/entries")
    async def list_entries(request: Request) -> dict[str, Any]:
        lang = lang_of(request)
        data, acc, dataset, shown, counts, view = listing(request)
        years = sorted({e["date"][:4] for e in data.get("entries", {}).values() if e["property_id"] in acc.property_ids}, reverse=True)
        visible = [public_property(p) for pid, p in data["properties"].items() if pid in acc.property_ids]
        return {
            "dataset": dataset, "role": acc.role, "view": view, "today": services.today().isoformat(),
            "entries": shown[:MAX_ROWS], "more": max(len(shown) - MAX_ROWS, 0), "counts": counts,
            "totals": entry_views.totals(shown), "years": years,
            "properties": sorted(visible, key=lambda p: (p["archived"], p["name"].casefold())),
            "categories": _categories(data, lang),
            "suppliers": sorted(({"id": s["id"], "name": s["name"], "archived": bool(s.get("archived")), "categories": s.get("categories", []),
                                  "rates": s.get("rates", [])}
                                 for s in data.get("suppliers", {}).values()), key=lambda s: (s["archived"], s["name"].casefold())),
        }

    @app.get("/api/entries/{entry_id}")
    async def read_entry(request: Request, entry_id: str) -> dict[str, Any]:
        lang = lang_of(request)
        dataset = dataset_of(request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        data = registry.snapshot()
        return with_documents(entry_views.detail(data, entry_or_404(data, acc, entry_id), lang, services.today()), data, acc, lang)

    @app.get("/api/export/entries.csv")
    async def export_entries(request: Request) -> Response:
        lang = lang_of(request)
        data, _, dataset, shown, _, view = listing(request)
        name = f"rental-cockpit-{'depenses' if lang == 'fr' else 'expenses'}{'-demo' if dataset == 'demo' else ''}.csv"
        return Response(exports.entries_csv(data, shown, lang), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})

    @app.get("/api/export/stays.csv")
    async def export_stays(request: Request) -> Response:
        params = request.query_params
        lang = lang_of(request)
        dataset = dataset_of(params.get("dataset"))
        acc, registry = reader(request, dataset)
        selected = scope(acc, params.get("property_id"))
        view = params.get("view") if params.get("view") in STAY_VIEWS else "all"
        query = str(params.get("q") or "")[:80]
        data = registry.snapshot()
        today = services.today()
        items = [stay_views.summary(data, s, today, lang) for s in data.get("stays", {}).values() if s["property_id"] in selected]
        items = [i for i in items if stay_search(i, query) and stay_matches(i, view, today.isoformat())]
        items.sort(key=lambda i: (i["start"], i["end"]))
        name = f"rental-cockpit-{'sejours' if lang == 'fr' else 'stays'}{'-demo' if dataset == 'demo' else ''}.csv"
        return Response(exports.stays_csv(items, lang), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})

    # ------------------------------------------------------------------ changes

    @app.post("/api/entries")
    async def create_entry(request: Request) -> dict[str, Any]:
        def operation(ledger: Ledger, payload: dict[str, Any]) -> dict[str, Any]:
            fields = {key: payload[key] for key in ENTRY_FIELDS if key in payload}
            if payload.get("repeat_months") not in (None, "", 0, 1, "1"):
                return entry_views.create_series(ledger, fields, payload["repeat_months"], services.today())
            return ledger.create_entry(fields)
        return await change(request, None, operation)

    @app.patch("/api/entries/{entry_id}")
    async def update_entry(request: Request, entry_id: str) -> dict[str, Any]:
        def operation(ledger: Ledger, payload: dict[str, Any]) -> dict[str, Any]:
            fields = {key: payload[key] for key in ENTRY_FIELDS if key in payload and key not in ("property_id", "kind", "paid", "paid_date", "payment_method")}
            return ledger.update_entry(entry_id, fields)
        return await change(request, entry_id, operation)

    @app.post("/api/entries/{entry_id}/archive")
    async def archive_entry(request: Request, entry_id: str) -> dict[str, Any]:
        return await change(request, entry_id, lambda ledger, payload: ledger.set_entry_archived(entry_id, payload.get("archived", True) is not False))

    @app.delete("/api/entries/{entry_id}")
    async def delete_entry(request: Request, entry_id: str) -> dict[str, Any]:
        return await change(request, entry_id, lambda ledger, payload: ledger.delete_entry(entry_id))

    @app.post("/api/entries/{entry_id}/allocations")
    async def allocate_entry(request: Request, entry_id: str) -> dict[str, Any]:
        """« Répartir entre les séjours » : analytical only, the expense is still counted once."""
        return await change(request, entry_id, lambda ledger, payload: ledger.set_allocations(entry_id, payload))

    @app.get("/api/entries/{entry_id}/candidates")
    async def reconcile_candidates(request: Request, entry_id: str) -> dict[str, Any]:
        lang = lang_of(request)
        dataset = dataset_of(request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        acc.require_admin()
        data = registry.snapshot()
        entry = entry_or_404(data, acc, entry_id)
        return {"candidates": supplier_views.candidates(data, entry, lang)}

    @app.post("/api/entries/{entry_id}/reconcile")
    async def reconcile_entry(request: Request, entry_id: str) -> dict[str, Any]:
        return await change(request, entry_id, lambda ledger, payload: ledger.reconcile(entry_id, payload))

    @app.post("/api/entries/{entry_id}/unreconcile")
    async def unreconcile_entry(request: Request, entry_id: str) -> dict[str, Any]:
        return await change(request, entry_id, lambda ledger, payload: ledger.unreconcile(entry_id, payload))

    @app.post("/api/entries/{entry_id}/payments")
    async def record_payment(request: Request, entry_id: str) -> dict[str, Any]:
        """A payment made (expense) or received (income), full or partial, on its date (Cash reading)."""
        def operation(ledger: Ledger, payload: dict[str, Any]) -> dict[str, Any]:
            entry = ledger.data["entries"][entry_id]
            if entry.get("archived"):
                raise RCError("archived")
            amount = {key: payload[key] for key in ("amount", "amount_cents") if key in payload}
            result = ledger.create_payment({
                "property_id": entry["property_id"], "direction": "out" if entry["kind"] == "expense" else "in",
                "date": payload.get("date"), **amount, "links": [{"type": "entry", "id": entry_id, **amount}],
                "method": payload.get("method", ""), "note": payload.get("note", ""),
            })
            return {**result, "entry": {"id": entry_id}}
        return await change(request, entry_id, operation)

    # ------------------------------------------------------------------ categories

    @app.get("/api/categories")
    async def list_categories(request: Request) -> dict[str, Any]:
        lang = lang_of(request)
        dataset = dataset_of(request.query_params.get("dataset"))
        _, registry = reader(request, dataset)
        return {"categories": _categories(registry.snapshot(), lang),
                "treatments": {kind: [{"id": t, "label": label("treatment", t, lang)} for t in TREATMENTS if t in allowed]
                               for kind, allowed in (("expense", EXPENSE_TREATMENTS), ("income", INCOME_TREATMENTS))}}

    async def category_change(request: Request, operation) -> dict[str, Any]:
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
        result["categories"] = _categories(registry.snapshot(), lang)
        return result

    @app.post("/api/categories")
    async def create_category(request: Request) -> dict[str, Any]:
        return await category_change(request, lambda ledger, payload: ledger.create_category(
            {key: payload.get(key) for key in ("kind", "treatment", "label")}))

    @app.patch("/api/categories/{category_id}")
    async def update_category(request: Request, category_id: str) -> dict[str, Any]:
        return await category_change(request, lambda ledger, payload: ledger.update_category(
            category_id, {key: payload[key] for key in ("label", "archived", "treatment") if key in payload}))
