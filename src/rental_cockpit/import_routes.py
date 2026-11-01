# Copyright © 2026 Vincent Fournet
"""Import API: preview a file, apply it, list imports, undo the last one.

The file travels with each request (base64 in JSON): the preview never
writes, and applying re-reads the same bytes and recomputes the same plan,
so nothing is kept on the server between the two steps. The fingerprint of
the file is stored with the import to warn when the same file comes back.
"""
from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from fastapi import FastAPI, Request
from starlette.concurrency import run_in_threadpool

from .engine.errors import RCError
from .engine.imports import airbnb, generic, plan
from .engine.ledger import Ledger
from .engine.schema import CHANNELS
from .web import Services, access, current_user, dataset_of, lang_of, public_property, require_csrf, utc_now

MAX_BODY = 8 * 1024 * 1024  # a 5 MiB file in base64, plus options
STATUS_LABELS = {
    "new": ("Nouveau", "New"), "update": ("Mis à jour", "Updated"), "same": ("Déjà à jour", "Up to date"),
    "duplicate": ("Doublon probable", "Probable duplicate"), "unmapped": ("Bien non choisi", "No property chosen"),
    "error": ("Erreur", "Error"),
}
CSV_CHANNELS = CHANNELS  # an English Airbnb export read as CSV is still Airbnb
DELIMITERS = {",": ("virgule", "comma"), ";": ("point-virgule", "semicolon"), "\t": ("tabulation", "tab")}


def _dict(value: Any) -> dict[str, Any]:
    """Choices sent by the page: anything that is not an object is treated as « no choice »."""
    return value if isinstance(value, dict) else {}


async def _payload(request: Request) -> dict[str, Any]:
    length = request.headers.get("content-length") or "0"
    if not length.isdigit() or int(length) > MAX_BODY:
        raise RCError("upload_too_large", limit="5 Mio")
    body = await request.body()
    if len(body) > MAX_BODY:
        raise RCError("upload_too_large", limit="5 Mio")
    try:
        payload = json.loads(body or b"{}")
    except ValueError as exc:
        raise RCError("choice_invalid", field="body") from exc
    if not isinstance(payload, dict):
        raise RCError("choice_invalid", field="body")
    options = _dict(payload.get("options"))
    for key in ("property_map", "decisions", "mapping"):
        options[key] = {str(k): str(v) for k, v in _dict(options.get(key)).items() if isinstance(v, (str, int))}
    payload["options"] = options
    return payload


def _content(payload: dict[str, Any]) -> bytes:
    try:
        content = base64.b64decode(str(payload.get("content") or ""), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RCError("import_file", detail="base64") from exc
    if not content:
        raise RCError("import_file", detail="—")
    return content


def _read(content: bytes, payload: dict[str, Any], data: dict[str, Any], lang: str) -> dict[str, Any]:
    """Run the reader the person chose (Airbnb or generic CSV) and return its result."""
    options = payload.get("options") or {}
    kind = payload.get("kind") if payload.get("kind") in ("airbnb", "csv") else "airbnb"
    try:
        if kind == "airbnb":
            return airbnb.parse(content)
        mapping = options.get("mapping")
        date_order = options.get("date_order") if options.get("date_order") in generic.DATE_ORDERS else "auto"
        if not mapping:
            # A mapping remembered for the same columns comes first, then the suggestion from the names.
            headers = generic.parse(content, {}, "DMY")["headers"]
            profile = data.get("csv_profiles", {}).get(generic.signature(headers))
            if profile:
                mapping, date_order = profile.get("mapping") or {}, profile.get("date_order", date_order)
        return generic.parse(content, mapping or None, date_order)
    except ValueError as exc:
        raise RCError("import_file", detail=plan.render({"code": str(exc), "params": {}}, lang)) from exc


def _options(payload: dict[str, Any], parsed: dict[str, Any], data: dict[str, Any], acc) -> dict[str, Any]:
    """Which property each listing goes to: the person's choice, else what was remembered, else the only property."""
    options = dict(payload.get("options") or {})
    usable = [pid for pid, p in data["properties"].items() if pid in acc.property_ids and not p.get("archived")]
    chosen = {k: v for k, v in (options.get("property_map") or {}).items() if v in usable or v == ""}
    remembered = data.get("settings", {}).get("listing_aliases", {})
    property_map = {}
    for listing in parsed.get("listings", []):
        if listing in chosen:
            property_map[listing] = chosen[listing]
        elif remembered.get(listing) in usable:
            property_map[listing] = remembered[listing]
        elif len(usable) == 1:
            property_map[listing] = usable[0]
        else:
            property_map[listing] = ""
    options["property_map"] = property_map
    if options.get("property_id") not in usable:
        options["property_id"] = usable[0] if len(usable) == 1 else ""
    if parsed["kind"] == "csv":
        # Settings remembered with the same columns, unless the person changed them in this preview.
        profile = data.get("csv_profiles", {}).get(parsed.get("signature", "")) or {}
        if "commission_rate" not in options:
            options["commission_rate"] = profile.get("commission_rate", "")
        if "channel" not in options:
            options["channel"] = profile.get("channel", "other")
        rate = plan.commission_rate(options.get("commission_rate"))
        options["commission_rate"] = format(rate.normalize(), "f") if rate is not None else ""
        options["channel"] = options["channel"] if options["channel"] in CSV_CHANNELS else "other"
    return options


def _view(parsed: dict[str, Any], built: dict[str, Any], options: dict[str, Any], data: dict[str, Any], lang: str,
          sha: str) -> dict[str, Any]:
    fr = lang == "fr"
    names = {pid: p["name"] for pid, p in data["properties"].items()}
    rows = []
    for row in built["rows"]:
        rows.append({
            **{k: row.get(k) for k in ("key", "lines", "status", "decision", "external_ref", "listing", "start", "end", "nights",
                                       "guests", "guest_label", "amounts", "payout", "property_id", "stay_id", "twin_label",
                                       "choices", "locked")},
            "status_label": STATUS_LABELS[row["status"]][0 if fr else 1],
            "property": names.get(row.get("property_id"), ""),
            "errors": [plan.render(e, lang) for e in row["errors"]],
            "warnings": [plan.render(w, lang) for w in row["warnings"]],
            "changes": [{**c, "label": plan.FIELD_LABELS.get(c["field"], (c["field"], c["field"]))[0 if fr else 1]}
                        for c in row["changes"]],
        })
    return {
        "kind": parsed["kind"], "reader": parsed["reader"], "encoding": parsed["encoding"],
        "delimiter": DELIMITERS.get(parsed["delimiter"], (parsed["delimiter"],) * 2)[0 if fr else 1],
        "date_order": parsed.get("date_order", ""), "date_order_setting": parsed.get("date_order_setting", "auto"),
        "headers": parsed["headers"], "mapping": parsed.get("mapping", {}),
        "suggested": parsed.get("suggested", {}), "signature": parsed.get("signature", ""), "listings": parsed["listings"],
        "samples": parsed.get("samples", {}),
        "property_map": options.get("property_map", {}), "property_id": options.get("property_id", ""),
        "commission_rate": options.get("commission_rate", ""), "channel": options.get("channel", "airbnb"),
        "keep_names": bool(options.get("keep_names")), "create_payouts": options.get("create_payouts", True) is not False,
        "errors": [plan.render(e, lang) for e in built["errors"]], "notices": [plan.render(n, lang) for n in built["notices"]],
        "rows": rows, "counts": built["counts"], "can_apply": built["can_apply"], "sha256": sha,
    }


def register_import_routes(app: FastAPI, services: Services) -> None:

    def context(request: Request, payload: dict[str, Any]):
        dataset = dataset_of(payload.get("dataset") or request.query_params.get("dataset"))
        acc = access(services, current_user(services, request), dataset)
        acc.require_admin()  # importing is an administrator's job (SEC 02)
        registry = services.registries[dataset]
        if not registry.exists:
            raise RCError("not_found")
        return dataset, acc, registry

    @app.post("/api/imports/preview")
    async def preview(request: Request) -> dict[str, Any]:
        require_csrf(request)
        payload = await _payload(request)
        lang = lang_of(request, payload)
        _, acc, registry = context(request, payload)
        content = _content(payload)
        data = registry.snapshot()

        def work() -> dict[str, Any]:
            parsed = _read(content, payload, data, lang)
            options = _options(payload, parsed, data, acc)
            sha = plan.fingerprint(content)
            built = plan.build(data, parsed, options, services.today(), sha)
            return _view(parsed, built, options, data, lang, sha)

        result = await run_in_threadpool(work)
        result["properties"] = [public_property(p) for pid, p in data["properties"].items() if pid in acc.property_ids and not p.get("archived")]
        result["fields"] = list(generic.FIELDS)
        return result

    @app.post("/api/imports/apply")
    async def apply_import(request: Request) -> dict[str, Any]:
        require_csrf(request)
        payload = await _payload(request)
        lang = lang_of(request, payload)
        _, acc, registry = context(request, payload)
        content = _content(payload)
        sha = plan.fingerprint(content)

        def operation(work: dict[str, Any]) -> dict[str, Any]:
            ledger = Ledger(work, acc.user_id)

            def run() -> dict[str, Any]:
                parsed = _read(content, payload, work, lang)
                if parsed["errors"]:
                    raise RCError("import_nothing")
                options = _options(payload, parsed, work, acc)
                built = plan.build(work, parsed, options, services.today(), sha)
                expect = payload.get("expect")
                if isinstance(expect, dict) and any(built["counts"].get(k) != expect.get(k) for k in ("to_write", "payouts")):
                    # Someone changed the stays between the preview and the confirmation: show the new preview first.
                    raise RCError("preview_stale")
                result = plan.apply(ledger, built, {"kind": parsed["kind"], "reader": parsed["reader"], "sha256": sha,
                                                    "file_name": str(payload.get("file_name") or ""),
                                                    "channel": options.get("channel", "other")})
                settings = work.setdefault("settings", {})
                if payload.get("remember", True) is not False:
                    aliases = settings.setdefault("listing_aliases", {})
                    for listing, pid in options["property_map"].items():
                        if pid:
                            aliases[listing[:300]] = pid
                    if parsed["kind"] == "csv" and parsed.get("signature"):
                        work.setdefault("csv_profiles", {})[parsed["signature"]] = {
                            "mapping": parsed["mapping"], "date_order": parsed.get("date_order", "auto"), "at": ledger.clock(),
                            "headers": parsed["headers"][:60], "commission_rate": options.get("commission_rate", ""),
                            "channel": options.get("channel", "other")}
                return result

            return ledger.once(payload.get("op_id"), run)

        return await run_in_threadpool(lambda: registry.mutate(operation, utc_now()))

    @app.get("/api/imports")
    async def list_imports(request: Request) -> dict[str, Any]:
        params = request.query_params
        _, _, registry = context(request, {"dataset": params.get("dataset")})
        data = registry.snapshot()
        last = plan.last_import(data)
        items = sorted(data.get("imports", {}).values(), key=lambda i: (i["at"], i.get("seq", 0)), reverse=True)[:50]
        return {
            "imports": [plan.summary(i) for i in items],
            "last_id": last["id"] if last else None,
            "blockers": plan.undo_blockers(data, last) if last else [],
        }

    @app.post("/api/imports/{import_id}/undo")
    async def undo_import(request: Request, import_id: str) -> dict[str, Any]:
        require_csrf(request)
        payload = await _payload(request)
        _, acc, registry = context(request, payload)

        def operation(work: dict[str, Any]) -> dict[str, Any]:
            ledger = Ledger(work, acc.user_id)
            return ledger.once(payload.get("op_id"), lambda: plan.undo(ledger, import_id))

        return await run_in_threadpool(lambda: registry.mutate(operation, utc_now()))
