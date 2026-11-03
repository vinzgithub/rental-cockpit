# Copyright © 2026 Vincent Fournet
"""« Justificatifs » API: check a PDF, attach it to an expense or create the expense from it,
list, describe, detach, delete, and hand the original back after a rights check.

The PDF travels once, as the raw body of the check request (8 MiB at most).
The checked bytes wait in memory for 10 minutes, for the account that sent
them, and nothing is written until the person confirms (PDF 02). On
confirmation the original is first written to private storage, then the
entry, the document and the journal line are saved in one transaction; if
that fails, the new file is removed (DUP 03). An ``op_id`` makes a double
click harmless, and two confirmations of the same file give one document.

Readers see documents only on the properties whose PDFs they were granted
(SEC 02); a guessed identifier is refused like any other.
"""
from __future__ import annotations

import asyncio
import secrets
import threading
import time
from copy import deepcopy
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from .engine import documents as document_views
from .engine import entries as entry_views
from .engine.errors import RCError
from .engine.ledger import Ledger, read_amount, safe_filename
from .entry_routes import ENTRY_FIELDS, with_documents
from .storage import BlobStore
from .web import Services, access, current_user, dataset_of, lang_of, read_json, require_csrf, scope, utc_now

PREVIEW_SECONDS = 600
PREVIEW_COUNT = 12
PREVIEW_BYTES = 64 * 1024 * 1024
CHECK_SECONDS = 20
VIEWS = ("all", "incomplete")
DOCUMENT_FIELDS = ("supplier_id", "supplier", "invoice_number", "invoice_date", "amount", "amount_cents", "note", "revision", "updated_at")


class Previews:
    """Checked PDFs waiting for a confirmation: in memory only, for their owner, 10 minutes at most."""

    def __init__(self, clock=time.monotonic) -> None:
        self.clock = clock
        self.items: dict[str, dict[str, Any]] = {}
        self.lock = threading.Lock()

    def _expire(self) -> None:
        limit = self.clock() - PREVIEW_SECONDS
        for token in [t for t, item in self.items.items() if item["at"] < limit]:
            del self.items[token]

    def add(self, owner: str, dataset: str, raw: bytes, info: dict[str, Any], filename: str) -> str:
        with self.lock:
            self._expire()
            if len(self.items) >= PREVIEW_COUNT or sum(len(i["raw"]) for i in self.items.values()) + len(raw) > PREVIEW_BYTES:
                raise RCError("pdf_preview_busy")
            token = secrets.token_urlsafe(24)
            self.items[token] = {"owner": owner, "dataset": dataset, "raw": raw, "at": self.clock(), "filename": filename,
                                 **{k: info[k] for k in ("sha256", "size", "pages", "text_found")}}
            return token

    def get(self, token: Any, owner: str, dataset: str) -> dict[str, Any] | None:
        with self.lock:
            self._expire()
            item = self.items.get(str(token or ""))
            if item is None or item["owner"] != owner or item["dataset"] != dataset:
                return None
            return item

    def drop(self, token: Any) -> None:
        with self.lock:
            self.items.pop(str(token or ""), None)


async def read_pdf_body(request: Request) -> bytes:
    length = request.headers.get("content-length")
    if length is not None and (not length.isdigit() or int(length) > document_views.MAX_PDF_BYTES):
        raise RCError("pdf_too_large")
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > document_views.MAX_PDF_BYTES:
            raise RCError("pdf_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


async def check_pdf(raw: bytes) -> dict[str, Any]:
    """Parse the PDF in a worker thread; a file that keeps the parser busy too long is refused."""
    try:
        return await asyncio.wait_for(run_in_threadpool(document_views.inspect_pdf, raw), timeout=CHECK_SECONDS)
    except asyncio.TimeoutError as exc:
        raise RCError("pdf_too_complex") from exc


def optional_amount(payload: dict[str, Any]) -> int | None:
    """An amount typed in a form, or nothing when it is empty or not readable yet."""
    try:
        return read_amount(payload, "amount", required=False)
    except RCError:
        return None


def content_disposition(filename: str, download: bool) -> str:
    ascii_name = "".join(c if c.isascii() and c.isprintable() and c not in '"\\;' else "_" for c in filename) or "justificatif.pdf"
    return f"{'attachment' if download else 'inline'}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def register_document_routes(app: FastAPI, services: Services) -> None:
    previews = Previews()
    stores = {dataset: BlobStore(services.config.documents_dir(dataset)) for dataset in ("real", "demo")}
    services.previews = previews
    services.blob_stores = stores

    # Files left behind by an interrupted save are removed at start-up (DUP 03).
    for dataset, store in stores.items():
        data = services.registries[dataset].data
        if data is not None:
            store.cleanup({d.get("sha256", "") for d in data.get("documents", {}).values()})

    def reader(request: Request, dataset: str):
        acc = access(services, current_user(services, request), dataset)
        registry = services.registries[dataset]
        if not registry.exists:
            raise RCError("not_found")
        return acc, registry

    def document_or_404(data: dict[str, Any], acc, document_id: str) -> dict[str, Any]:
        doc = data.get("documents", {}).get(document_id)
        if doc is None:
            raise RCError("not_found")
        acc.require_documents(doc["property_id"])
        return doc

    def document_detail(data: dict[str, Any], doc: dict[str, Any], acc, lang: str) -> dict[str, Any]:
        result = document_views.summary(data, doc, lang)
        result["history"] = [{"at": h["at"], "fields": list(h.get("changes", {}))} for h in doc.get("history", [])][-20:]
        if acc.is_admin:
            # Entries of the same property it could be attached to, most recent first.
            linked = set(doc.get("entry_ids", []))
            rows = sorted((e for e in data.get("entries", {}).values()
                           if e["property_id"] == doc["property_id"] and e["id"] not in linked and not e.get("superseded_by")),
                          key=lambda e: e["date"], reverse=True)
            if doc.get("amount") is not None:
                rows.sort(key=lambda e: e["amount"] != doc["amount"])  # same amount first, still most recent first
            result["link_candidates"] = [{"id": e["id"], "label": e["label"], "date": e["date"], "amount": e["amount"], "kind": e["kind"]}
                                         for e in rows[:300]]
        return result

    # ------------------------------------------------------------------ check (nothing is written)

    @app.post("/api/documents/preview")
    async def preview(request: Request) -> dict[str, Any]:
        require_csrf(request)
        params = request.query_params
        lang = lang_of(request)
        dataset = dataset_of(params.get("dataset"))
        acc, registry = reader(request, dataset)
        acc.require_admin()
        data = registry.snapshot()
        entry_id = str(params.get("entry_id") or "")
        entry = None
        if entry_id:
            entry = data.get("entries", {}).get(entry_id)
            if entry is None:
                raise RCError("not_found")
            acc.require_property(entry["property_id"])
        raw = await read_pdf_body(request)
        info = await check_pdf(raw)
        found = document_views.suggestions(info["text"], data) if info["text_found"] else {}
        filename = safe_filename(params.get("filename"))
        token = previews.add(acc.user_id, dataset, raw, info, filename)
        same_file = [d for d in data.get("documents", {}).values() if d["sha256"] == info["sha256"]]
        if entry:
            meta = {"supplier_id": entry.get("supplier_id", ""), "invoice_number": entry.get("invoice_number", ""),
                    "invoice_date": entry["date"], "amount": entry["amount"]}
        else:
            meta = {k: found.get(k) for k in ("supplier_id", "invoice_number", "invoice_date", "amount")}
        dups = document_views.duplicates(data, lang, sha=info["sha256"], supplier_id=meta["supplier_id"] or "",
                                         invoice_number=meta["invoice_number"] or "", invoice_date=meta["invoice_date"] or "",
                                         amount=meta["amount"], exclude_entry=entry_id)
        return {
            "token": token, "expires_in": PREVIEW_SECONDS, "filename": filename, "size": info["size"], "pages": info["pages"],
            "sha256": info["sha256"], "text_found": info["text_found"], "suggestions": found, "duplicates": dups,
            "already_attached": bool(entry and any(entry_id in d.get("entry_ids", []) for d in same_file)),
            "existing_document": (document_views.summary(data, same_file[0], lang) if same_file else None),
        }

    @app.post("/api/documents/check")
    async def check(request: Request) -> dict[str, Any]:
        """Duplicates for what is typed in the form, as the person types it. Reads only."""
        require_csrf(request)
        payload = await read_json(request)
        lang = lang_of(request, payload)
        dataset = dataset_of(payload.get("dataset"))
        acc, registry = reader(request, dataset)
        acc.require_admin()
        pending = previews.get(payload.get("token"), acc.user_id, dataset)
        amount = optional_amount(payload)
        data = registry.snapshot()
        return {"duplicates": document_views.duplicates(
            data, lang, sha=(pending or {}).get("sha256", ""), supplier_id=str(payload.get("supplier_id") or ""),
            supplier=str(payload.get("supplier") or ""), invoice_number=str(payload.get("invoice_number") or ""),
            invoice_date=str(payload.get("invoice_date") or ""), amount=amount, exclude_entry=str(payload.get("entry_id") or ""))}

    # ------------------------------------------------------------------ confirm

    @app.post("/api/documents")
    async def confirm(request: Request) -> dict[str, Any]:
        require_csrf(request)
        payload = await read_json(request)
        lang = lang_of(request, payload)
        dataset = dataset_of(payload.get("dataset"))
        acc, registry = reader(request, dataset)
        acc.require_admin()
        op_id = payload.get("op_id")
        pending = previews.get(payload.get("token"), acc.user_id, dataset)
        if pending is None and not (op_id and str(op_id) in registry.snapshot().get("ops", {})):
            raise RCError("pdf_preview_expired")
        mode = "attach" if payload.get("mode") == "attach" else "create"
        store = stores[dataset]
        new_blob = False
        if pending is not None:
            try:
                new_blob = await run_in_threadpool(store.write, pending["sha256"], pending["raw"])
            except OSError as exc:  # nothing was recorded: the person can free some space and confirm again
                raise RCError("storage_full" if exc.errno == 28 else "storage_failed", detail="PDF") from exc
        document = payload.get("document") if isinstance(payload.get("document"), dict) else {}
        fields = payload.get("entry") if isinstance(payload.get("entry"), dict) else {}

        def apply(work: dict[str, Any]) -> dict[str, Any]:
            ledger = Ledger(work, acc.user_id)

            def run() -> dict[str, Any]:
                if pending is None:
                    raise RCError("pdf_preview_expired")
                file = {k: pending[k] for k in ("sha256", "size", "pages", "text_found", "filename")}
                if mode == "attach":
                    entry = ledger._get("entries", payload.get("entry_id"))
                    acc.require_property(entry["property_id"])
                    same = [d for d in work["documents"].values() if d["sha256"] == pending["sha256"]]
                    if same:
                        if entry["id"] in same[0].get("entry_ids", []):
                            raise RCError("document_already_attached")
                        if not payload.get("link_existing"):
                            raise RCError("document_duplicate", reason=document_views.REASON_LABELS["same_file"])
                        linked = ledger.link_document(same[0]["id"], entry["id"])
                        return {"entry": deepcopy(entry), "document": linked["document"]}
                    meta = {"supplier_id": entry.get("supplier_id", ""), "invoice_number": entry.get("invoice_number", ""),
                            "invoice_date": entry["date"], "amount_cents": entry["amount"], **document}
                    added = ledger.add_document({**meta, "property_id": entry["property_id"], "entry_id": entry["id"]}, file)
                    return {"entry": deepcopy(entry), "document": added["document"]}
                # « Créer une dépense depuis une facture »: the expense and its document together.
                values = {key: fields[key] for key in ENTRY_FIELDS if key in fields and key != "revision"}
                values["kind"] = "expense"
                acc.require_property(str(values.get("property_id") or ""))
                amount = optional_amount(values)
                dups = document_views.duplicates(work, lang, sha=pending["sha256"], supplier_id=str(values.get("supplier_id") or ""),
                                                 invoice_number=str(values.get("invoice_number") or ""),
                                                 invoice_date=str(values.get("date") or ""), amount=amount)
                if dups["certain"]:
                    raise RCError("document_duplicate", reason=document_views.REASON_LABELS[dups["certain"][0]["reason"]])
                if dups["probable"] and not payload.get("confirm_probable"):
                    raise RCError("document_probable", reason=document_views.REASON_LABELS[dups["probable"][0]["reason"]])
                created = ledger.create_entry(values)["entry"]
                added = ledger.add_document({"supplier_id": created.get("supplier_id", ""), "invoice_number": created.get("invoice_number", ""),
                                             "invoice_date": created["date"], "amount_cents": created["amount"],
                                             "property_id": created["property_id"], "entry_id": created["id"]}, file)
                return {"entry": created, "document": added["document"]}

            return ledger.once(op_id, run)

        try:
            result = await run_in_threadpool(lambda: registry.mutate(apply, utc_now()))
        except BaseException:
            if new_blob and pending is not None:
                referenced = {d.get("sha256") for d in (registry.snapshot().get("documents") or {}).values()}
                if pending["sha256"] not in referenced:
                    store.remove(pending["sha256"])
            raise
        previews.drop(payload.get("token"))
        data = registry.snapshot()
        entry_id = (result.get("entry") or {}).get("id")
        if entry_id in data.get("entries", {}):
            result["detail"] = with_documents(entry_views.detail(data, data["entries"][entry_id], lang, services.today()), data, acc, lang)
        doc_id = (result.get("document") or {}).get("id")
        if doc_id in data.get("documents", {}):
            result["document"] = document_views.summary(data, data["documents"][doc_id], lang)
        return result

    # ------------------------------------------------------------------ reading

    @app.get("/api/documents")
    async def list_documents(request: Request) -> dict[str, Any]:
        params = request.query_params
        lang = lang_of(request)
        dataset = dataset_of(params.get("dataset"))
        acc, registry = reader(request, dataset)
        selected = scope(acc, params.get("property_id"))
        view = params.get("view") if params.get("view") in VIEWS else "all"
        query = str(params.get("q") or "")[:80]
        data = registry.snapshot()
        items = [document_views.summary(data, d, lang) for d in data.get("documents", {}).values()
                 if d["property_id"] in selected and acc.sees_documents(d["property_id"])]
        items = [i for i in items if document_views.matches(i, query)]
        counts = {"all": len(items), "incomplete": sum(1 for i in items if i["incomplete"])}
        shown = [i for i in items if view == "all" or i["incomplete"]]
        shown.sort(key=lambda i: (i["invoice_date"] or (i["created_at"] or "")[:10], i["created_at"] or ""), reverse=True)
        hidden = sum(1 for d in data.get("documents", {}).values() if d["property_id"] in selected and not acc.sees_documents(d["property_id"]))
        return {"dataset": dataset, "role": acc.role, "view": view, "documents": shown[:500], "counts": counts,
                "hidden": hidden, "can_upload": acc.is_admin}

    @app.get("/api/documents/{document_id}")
    async def read_document(request: Request, document_id: str) -> dict[str, Any]:
        lang = lang_of(request)
        dataset = dataset_of(request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        data = registry.snapshot()
        return document_detail(data, document_or_404(data, acc, document_id), acc, lang)

    @app.get("/api/documents/{document_id}/file")
    async def document_file(request: Request, document_id: str) -> Response:
        dataset = dataset_of(request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        data = registry.snapshot()
        doc = document_or_404(data, acc, document_id)
        store = stores[dataset]
        sample = document_views.SAMPLES.get(doc.get("sample", "")) if dataset == "demo" else None
        if sample is not None and not await run_in_threadpool(store.exists, doc["sha256"]):
            await run_in_threadpool(store.write, doc["sha256"], sample())  # the demo's fictional PDF, rebuilt identically
        raw = await run_in_threadpool(store.read, doc["sha256"], document_views.MAX_PDF_BYTES)
        download = request.query_params.get("download") in ("1", "true")
        return Response(raw, media_type="application/pdf", headers={
            "Content-Disposition": content_disposition(doc.get("filename") or "justificatif.pdf", download),
            "Cache-Control": "no-store, private", "X-Content-Type-Options": "nosniff",
            # Only what cannot get in the way of the browser's own PDF viewer: the bytes were checked
            # as a PDF without script, and nosniff keeps them from ever being read as a page.
            "Content-Security-Policy": "frame-ancestors 'none'; form-action 'none'; base-uri 'none'",
        })

    # ------------------------------------------------------------------ changes

    async def change(request: Request, document_id: str, operation) -> dict[str, Any]:
        require_csrf(request)
        payload = await read_json(request)
        lang = lang_of(request, payload)
        dataset = dataset_of(payload.get("dataset") or request.query_params.get("dataset"))
        acc, registry = reader(request, dataset)
        acc.require_admin()
        document_or_404(registry.snapshot(), acc, document_id)

        def apply(work: dict[str, Any]) -> dict[str, Any]:
            ledger = Ledger(work, acc.user_id)
            return ledger.once(payload.get("op_id"), lambda: operation(ledger, payload))

        result = await run_in_threadpool(lambda: registry.mutate(apply, utc_now()))
        data = registry.snapshot()
        if document_id in data.get("documents", {}):
            result["document"] = document_detail(data, data["documents"][document_id], acc, lang)
        elif result.get("sha256") and not any(d.get("sha256") == result["sha256"] for d in data.get("documents", {}).values()):
            stores[dataset].remove(result["sha256"])  # a deleted document's original is erased from private storage
        entry_id = str(payload.get("entry_id") or "")
        if entry_id in data.get("entries", {}):
            result["detail"] = with_documents(entry_views.detail(data, data["entries"][entry_id], lang, services.today()), data, acc, lang)
        return result

    @app.patch("/api/documents/{document_id}")
    async def update_document(request: Request, document_id: str) -> dict[str, Any]:
        return await change(request, document_id, lambda ledger, payload: ledger.update_document(
            document_id, {k: payload[k] for k in DOCUMENT_FIELDS if k in payload}))

    @app.post("/api/documents/{document_id}/link")
    async def link_document(request: Request, document_id: str) -> dict[str, Any]:
        return await change(request, document_id, lambda ledger, payload: ledger.link_document(document_id, payload.get("entry_id")))

    @app.post("/api/documents/{document_id}/detach")
    async def detach_document(request: Request, document_id: str) -> dict[str, Any]:
        return await change(request, document_id, lambda ledger, payload: ledger.detach_document(document_id, payload))

    @app.delete("/api/documents/{document_id}")
    async def delete_document(request: Request, document_id: str) -> dict[str, Any]:
        return await change(request, document_id, lambda ledger, payload: ledger.delete_document(document_id, payload))
