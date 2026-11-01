# Copyright © 2026 Vincent Fournet
"""From a read file to stays: preview, apply, undo.

The preview compares every line with the registry and says what would
happen — new stay, update of a stay already imported, nothing to change,
probable duplicate of a stay entered by hand, line in error — without
writing anything. Applying recomputes the same plan from the same file (the
server keeps nothing between the two) and writes everything in one
transaction. The last import can be undone as long as none of its stays was
changed afterwards.
"""
from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import date
from typing import Any

from ..errors import RCError
from ..indicators import expected_payout
from ..ledger import Ledger, new_id

STATUSES = ("new", "update", "same", "duplicate", "unmapped", "error")
DECISIONS = ("import", "complete", "skip")

MESSAGES: dict[str, tuple[str, str]] = {
    "imp_empty": ("Le fichier est vide.", "The file is empty."),
    "imp_too_large": ("Le fichier dépasse 5 Mio.", "The file is larger than 5 MiB."),
    "imp_too_many_rows": ("Le fichier contient plus de 20 000 lignes.", "The file has more than 20,000 lines."),
    "imp_no_header": ("Ligne d'en-tête introuvable : la première ligne doit nommer les colonnes.", "No header line: the first line must name the columns."),
    "imp_encoding": ("Encodage du fichier non reconnu (UTF-8 ou Windows-1252 attendu).", "File encoding not recognised (UTF-8 or Windows-1252 expected)."),
    "imp_encoding_fallback": ("Fichier lu en Windows-1252 (pas en UTF-8) : vérifiez les accents dans l'aperçu.", "File read as Windows-1252 (not UTF-8): check the accents in the preview."),
    "imp_airbnb_columns": ("Ce n'est pas l'export « Historique des transactions » d'Airbnb en français : colonnes absentes ({columns}). Utilisez l'import CSV générique.", "This is not Airbnb's French \"transaction history\" export: missing columns ({columns}). Use the generic CSV import."),
    "imp_dates_mixed": ("Le fichier mélange des dates JJ/MM et MM/JJ : rien n'est importé plutôt que de deviner.", "The file mixes DD/MM and MM/DD dates: nothing is imported rather than guessing."),
    "imp_dates_ambiguous": ("Toutes les dates sont ambiguës : ordre {order} utilisé. Vérifiez quelques séjours dans l'aperçu.", "Every date is ambiguous: order {order} used. Check a few stays in the preview."),
    "imp_csv_mapping": ("Choisissez au moins la colonne d'arrivée, et celle du départ ou du nombre de nuits.", "Choose at least the arrival column, and the departure or nights column."),
    "imp_no_code": ("code de confirmation vide", "empty confirmation code"),
    "imp_bad_dates": ("date d'arrivée ou de départ illisible", "unreadable arrival or departure date"),
    "imp_dates_order": ("le départ n'est pas après l'arrivée", "the departure is not after the arrival"),
    "imp_nights_mismatch": ("{file} nuits indiquées, {dates} d'après les dates", "{file} nights stated, {dates} from the dates"),
    "imp_no_listing": ("logement vide", "empty listing"),
    "imp_bad_amount": ("montant illisible dans « {column} »", "unreadable amount in \"{column}\""),
    "imp_negative": ("montant négatif : ce n'est pas une réservation (remboursement ou ajustement ?)", "negative amount: this is not a booking (refund or adjustment?)"),
    "imp_code_conflict": ("le code {code} revient ligne {line} avec d'autres dates ou un autre logement", "code {code} comes back on line {line} with other dates or another listing"),
    "imp_ref_twice": ("la référence {ref} figure déjà ligne {line}", "reference {ref} is already on line {line}"),
    "imp_amounts_differ": ("brut − frais de service ≠ montant versé : vérifiez ce séjour", "gross − service fee ≠ amount paid: check this stay"),
    "imp_overlap": ("chevauche « {label} » ({start} → {end})", "overlaps \"{label}\" ({start} → {end})"),
    "imp_before_activity": ("arrivée avant le début d'activité du bien ({date})", "arrival before the property's activity start ({date})"),
    "imp_cancelled_kept": ("ce séjour est annulé dans Rental Cockpit : il n'est pas modifié", "this stay is cancelled in Rental Cockpit: it is not changed"),
    "imp_payout_exists": ("versement déjà enregistré", "payout already recorded"),
    "imp_payout_too_high": ("versement non enregistré : il dépasserait le montant attendu", "payout not recorded: it would exceed the expected amount"),
    "imp_file_known": ("Ce fichier a déjà été importé le {date}.", "This file was already imported on {date}."),
    "imp_ignored_transfers": ("{n} ligne(s) « Payout » ignorée(s) : ce sont des virements de montants déjà comptés.", "{n} \"Payout\" line(s) ignored: they are transfers of amounts already counted."),
    "imp_ignored_other": ("{n} ligne(s) d'un autre type ignorée(s) ({types}) : elles ne sont pas des réservations.", "{n} line(s) of another type ignored ({types}): they are not bookings."),
}

FIELD_LABELS = {
    "start": ("arrivée", "arrival"), "end": ("départ", "departure"), "guests": ("voyageurs", "guests"),
    "gross": ("montant brut", "gross amount"), "commission": ("commission", "commission"), "payout": ("versement net", "net payout"),
    "taxes_collected": ("taxe de séjour", "tourist tax"), "external_ref": ("référence", "reference"),
}


def render(item: dict[str, Any], lang: str) -> str:
    fr, en = MESSAGES.get(item["code"], (item["code"], item["code"]))
    text = fr if lang == "fr" else en
    try:
        return text.format(**item.get("params", {}))
    except (KeyError, IndexError):  # pragma: no cover - defensive
        return text


def fingerprint(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _stays_of(data: dict[str, Any], pid: str) -> list[dict[str, Any]]:
    return [s for s in data.get("stays", {}).values() if s["property_id"] == pid]


def _property_for(row: dict[str, Any], options: dict[str, Any], properties: dict[str, Any]) -> str | None:
    mapping = options.get("property_map") or {}
    listing = row.get("listing") or ""
    pid = mapping.get(listing) if listing else options.get("property_id")
    if not pid and listing and options.get("property_id") and not mapping:
        pid = options.get("property_id")
    if pid and pid in properties and not properties[pid].get("archived"):
        return pid
    return None


def _changes(stay: dict[str, Any], row: dict[str, Any]) -> list[dict[str, Any]]:
    """Fields the file would change on a stay already imported (only where the file has a value)."""
    changes = []
    for field in ("start", "end"):
        if row[field] != stay[field]:
            changes.append({"field": field, "before": stay[field], "after": row[field]})
    if row.get("guests") and row["guests"] != stay.get("guests"):
        changes.append({"field": "guests", "before": stay.get("guests"), "after": row["guests"]})
    current = stay.get("amounts") or {}
    for field, value in (row.get("amounts") or {}).items():
        if value is not None and value != current.get(field):
            changes.append({"field": field, "before": current.get(field), "after": value})
    return changes


def build(data: dict[str, Any], parsed: dict[str, Any], options: dict[str, Any], today: date, content_hash: str) -> dict[str, Any]:
    """The preview: one entry per line of the file, with what would happen and why. Writes nothing."""
    properties = data.get("properties", {})
    decisions = options.get("decisions") or {}
    keep_names = bool(options.get("keep_names"))
    with_payouts = options.get("create_payouts", True) is not False
    rows = []
    for row in parsed["rows"]:
        item: dict[str, Any] = {"key": row["key"], "lines": row["lines"], "external_ref": row.get("external_ref", ""),
                                "listing": row.get("listing", ""), "errors": list(row.get("errors", [])),
                                "warnings": list(row.get("warnings", [])), "changes": [], "payout": None}
        if item["errors"]:
            item.update(status="error", decision="skip")
            rows.append(item)
            continue
        item.update({key: row.get(key) for key in ("start", "end", "nights", "guests", "amounts", "paid_on", "paid_amount")})
        if any(v is not None and v < 0 for v in (item["amounts"] or {}).values()):
            item["errors"].append({"code": "imp_negative", "params": {}})
            item.update(status="error", decision="skip")
            rows.append(item)
            continue
        item["guest_label"] = row.get("guest_name", "") if keep_names else ""
        pid = _property_for(row, options, properties)
        item["property_id"] = pid
        if not pid:
            item.update(status="unmapped", decision="skip")
            rows.append(item)
            continue
        prop = properties[pid]
        same_ref = [s for s in _stays_of(data, pid) if item["external_ref"] and s.get("external_ref") == item["external_ref"]]
        target = None
        if same_ref:
            target = same_ref[0]
            if target["status"] == "cancelled":
                item["warnings"].append({"code": "imp_cancelled_kept", "params": {}})
                item.update(status="same", decision="skip", stay_id=target["id"], locked=True)
            else:
                item["changes"] = _changes(target, item)
                item.update(status="update" if item["changes"] else "same", stay_id=target["id"])
                item["decision"] = "import" if item["changes"] else "skip"
        else:
            twin = next((s for s in _stays_of(data, pid) if s["status"] != "cancelled" and s["start"] == item["start"]
                         and s["end"] == item["end"]), None)
            if twin:
                target = twin
                item.update(status="duplicate", stay_id=twin["id"], decision="complete",
                            twin_label=twin.get("guest_label") or twin.get("external_ref") or "")
            else:
                item.update(status="new", decision="import")
                for other in _stays_of(data, pid):
                    if other["status"] != "cancelled" and other["start"] < item["end"] and item["start"] < other["end"]:
                        item["warnings"].append({"code": "imp_overlap", "params": {
                            "label": other.get("guest_label") or other.get("external_ref") or "—", "start": other["start"], "end": other["end"]}})
            start_limit = prop.get("activity_start")
            if start_limit and item["start"] < start_limit:
                item["warnings"].append({"code": "imp_before_activity", "params": {"date": start_limit}})
                item["decision"] = "skip"
        if item["key"] in decisions and decisions[item["key"]] in DECISIONS:
            allowed = {"new": ("import", "skip"), "update": ("import", "skip"), "duplicate": ("complete", "import", "skip")}
            if decisions[item["key"]] in allowed.get(item["status"], ()):
                item["decision"] = decisions[item["key"]]
        # Payout from the file (date of the transaction): recorded once, never above what is expected.
        if with_payouts and item.get("paid_on") and item.get("paid_amount") and item["paid_on"] <= today.isoformat():
            if target is not None:
                already = [link for p in data.get("payments", {}).values() for link in p["links"]
                           if link["type"] == "stay" and link["id"] == target["id"]]
                if any(p["date"] == item["paid_on"] and link["amount"] == item["paid_amount"]
                       for p in data.get("payments", {}).values() for link in p["links"]
                       if link["type"] == "stay" and link["id"] == target["id"]):
                    item["warnings"].append({"code": "imp_payout_exists", "params": {}})
                else:
                    received = sum(link["amount"] for link in already)
                    expected = expected_payout({**target, "amounts": {**(target.get("amounts") or {}),
                                                                       **{k: v for k, v in (item["amounts"] or {}).items() if v is not None}}})
                    if expected is not None and received + item["paid_amount"] > expected:
                        item["warnings"].append({"code": "imp_payout_too_high", "params": {}})
                    else:
                        item["payout"] = {"date": item["paid_on"], "amount": item["paid_amount"]}
            else:
                item["payout"] = {"date": item["paid_on"], "amount": item["paid_amount"]}
        if item["status"] == "same" and not item.get("locked"):
            # Nothing to change on the stay; the line still matters when it brings a payout.
            item["decision"] = "import" if item["payout"] else "skip"
        rows.append(item)

    known = [i for i in data.get("imports", {}).values() if i.get("sha256") == content_hash and not i.get("undone_at")]
    notices = list(parsed.get("warnings", []))
    if parsed["ignored"]["transfers"]:
        notices.append({"code": "imp_ignored_transfers", "params": {"n": parsed["ignored"]["transfers"]}})
    if parsed["ignored"]["other"]:
        notices.append({"code": "imp_ignored_other", "params": {"n": sum(parsed["ignored"]["other"].values()),
                                                               "types": ", ".join(sorted(parsed["ignored"]["other"]))}})
    if known:
        notices.append({"code": "imp_file_known", "params": {"date": known[-1]["at"][:10]}})
    counts = {status: sum(1 for r in rows if r["status"] == status) for status in STATUSES}
    counts["to_write"] = sum(1 for r in rows if r["decision"] != "skip" and r["status"] in ("new", "update", "duplicate"))
    counts["payouts"] = sum(1 for r in rows if r["payout"] and r["decision"] != "skip")
    return {"rows": rows, "counts": counts, "errors": parsed["errors"], "notices": notices,
            "can_apply": not parsed["errors"] and counts["to_write"] + counts["payouts"] > 0}


def apply(ledger: Ledger, plan: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    """Write the plan in the working copy held by ``ledger`` (one transaction for the caller)."""
    if plan["errors"] or not plan["can_apply"]:
        raise RCError("import_nothing")
    import_id = new_id("imp")
    source = "airbnb" if meta["kind"] == "airbnb" else "csv"
    record = {"id": import_id, "at": ledger.clock(), "by": ledger.actor, "kind": meta["kind"], "reader": meta["reader"],
              "file_name": meta.get("file_name", "")[:120], "sha256": meta["sha256"], "created": [], "updated": [],
              "payments": [], "counts": {}, "undone_at": None}
    created = updated = completed = payouts = 0
    for row in plan["rows"]:
        if row["decision"] == "skip" or row["status"] in ("error", "unmapped"):
            continue
        stay_id = row.get("stay_id")
        if row["status"] == "new" or (row["status"] == "duplicate" and row["decision"] == "import"):
            payload = {"property_id": row["property_id"], "start": row["start"], "end": row["end"], "guests": row.get("guests"),
                       "guest_label": row.get("guest_label", ""), "external_ref": row.get("external_ref", ""),
                       "channel": "airbnb" if source == "airbnb" else meta.get("channel", "other"),
                       "amounts": {f"{k}_cents": v for k, v in (row.get("amounts") or {}).items() if v is not None}}
            stay = ledger.create_stay(payload, source=source, origin_import=import_id)["stay"]
            stay_id = stay["id"]
            record["created"].append({"id": stay_id, "revision": stay["revision"]})
            created += 1
        elif row["status"] in ("update", "duplicate"):
            stay = ledger.data["stays"][stay_id]
            before = deepcopy({k: stay.get(k) for k in ("start", "end", "guests", "amounts", "external_ref", "guest_label")})
            fields: dict[str, Any] = {}
            if row["status"] == "update":
                for change in row["changes"]:
                    if change["field"] in ("start", "end", "guests"):
                        fields[change["field"]] = change["after"]
                amounts = {f"{c['field']}_cents": c["after"] for c in row["changes"]
                           if c["field"] in ("gross", "commission", "payout", "taxes_collected")}
            else:  # complete a stay entered by hand: only what it does not know yet, plus the reference
                current = stay.get("amounts") or {}
                amounts = {f"{k}_cents": v for k, v in (row.get("amounts") or {}).items() if v is not None and current.get(k) is None}
                if row.get("external_ref") and not stay.get("external_ref"):
                    fields["external_ref"] = row["external_ref"]
                if row.get("guests") and not stay.get("guests"):
                    fields["guests"] = row["guests"]
            if amounts:
                fields["amounts"] = amounts
            if fields:
                result = ledger.update_stay(stay_id, fields)["stay"]
                record["updated"].append({"id": stay_id, "before": before, "revision": result["revision"]})
                updated += row["status"] == "update"
                completed += row["status"] == "duplicate"
        if row.get("payout") and stay_id:
            payment = ledger.create_payment({
                "property_id": row["property_id"], "direction": "in", "date": row["payout"]["date"],
                "amount_cents": row["payout"]["amount"],
                "links": [{"type": "stay", "id": stay_id, "amount_cents": row["payout"]["amount"]}],
                "method": "Import Airbnb" if source == "airbnb" else "Import CSV", "origin": {"type": "import", "id": import_id},
            })["payment"]
            record["payments"].append(payment["id"])
            payouts += 1
    # Recording a payment changes nothing to a stay's revision: the undo check below still holds.
    record["counts"] = {"created": created, "updated": updated, "completed": completed, "payouts": payouts}
    ledger.data.setdefault("imports", {})[import_id] = record
    ledger.audit("import.apply", import_id, detail=f"{meta['kind']}:{created}+{updated}+{completed}+{payouts}")
    return {"import": deepcopy(record)}


def last_import(data: dict[str, Any]) -> dict[str, Any] | None:
    live = [i for i in data.get("imports", {}).values() if not i.get("undone_at")]
    return max(live, key=lambda i: i["at"]) if live else None


def undo_blockers(data: dict[str, Any], record: dict[str, Any]) -> list[str]:
    """Stays of the import changed since: undoing would erase someone's work, so it is refused."""
    blockers = []
    own = set(record["payments"])
    for item in record["created"] + record["updated"]:
        stay = data["stays"].get(item["id"])
        if stay is None:
            continue
        if int(stay.get("revision") or 0) != item["revision"]:
            blockers.append(stay.get("guest_label") or stay.get("external_ref") or stay["start"])
            continue
        foreign = [p for p in data.get("payments", {}).values() if p["id"] not in own
                   and any(link["type"] == "stay" and link["id"] == stay["id"] for link in p["links"])]
        linked = [e for e in data.get("entries", {}).values()
                  if e.get("stay_id") == stay["id"] or any(a.get("stay_id") == stay["id"] for a in e.get("allocations", []))]
        if (foreign or linked) and item in record["created"]:
            blockers.append(stay.get("guest_label") or stay.get("external_ref") or stay["start"])
    return blockers


def undo(ledger: Ledger, import_id: str) -> dict[str, Any]:
    data = ledger.data
    record = data.get("imports", {}).get(import_id)
    if record is None:
        raise RCError("not_found")
    latest = last_import(data)
    if record.get("undone_at") or latest is None or latest["id"] != import_id:
        raise RCError("import_not_last")
    blockers = undo_blockers(data, record)
    if blockers:
        raise RCError("import_changed_since", stays=", ".join(blockers[:5]))
    for payment_id in record["payments"]:
        data["payments"].pop(payment_id, None)
    for item in record["created"]:
        data["stays"].pop(item["id"], None)
    for item in record["updated"]:
        stay = data["stays"].get(item["id"])
        if stay is None:
            continue
        before = deepcopy(stay)
        stay.update(deepcopy(item["before"]))
        ledger._history(stay, before, ("start", "end", "guests", "amounts", "external_ref", "guest_label"))
    record["undone_at"] = ledger.clock()
    record["undone_by"] = ledger.actor
    ledger.audit("import.undo", import_id)
    return {"import": deepcopy(record)}

