# Copyright © 2026 Vincent Fournet
"""From a read file to stays and the platform's other operations: preview, apply, undo.

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
from bisect import bisect_left
from copy import deepcopy
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from ..errors import RCError
from ..indicators import expected_payout
from ..ledger import Ledger, new_id
from ..money import format_cents

STATUSES = ("new", "update", "same", "duplicate", "unmapped", "error")
DECISIONS = ("import", "complete", "cancelled", "skip")
# What a line of the platform that is not a booking becomes (see airbnb.OPERATION_TYPES).
OPERATION_CATEGORIES = {"compensation": "platform_compensation", "credit": "platform_credit"}
OPERATION_LABELS = {
    "compensation": ("Indemnisation Airbnb", "Airbnb compensation"),
    "credit": ("Crédit Airbnb", "Airbnb credit"),
    "adjustment": ("Remboursement à un voyageur (retenu par Airbnb)", "Refund to a guest (withheld by Airbnb)"),
    "unknown": ("Opération Airbnb", "Airbnb operation"),
}

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
    "imp_bad_dates": ("date d'arrivée ou de départ illisible, ou hors des années 2000 à 2100", "arrival or departure date unreadable, or outside the years 2000 to 2100"),
    "imp_dates_order": ("le départ n'est pas après l'arrivée", "the departure is not after the arrival"),
    "imp_nights_mismatch": ("{file} nuits indiquées, {dates} d'après les dates", "{file} nights stated, {dates} from the dates"),
    "imp_no_listing": ("logement vide", "empty listing"),
    "imp_bad_amount": ("montant illisible dans « {column} »", "unreadable amount in \"{column}\""),
    "imp_negative": ("montant négatif : ce n'est pas une réservation (remboursement ou ajustement ?)", "negative amount: this is not a booking (refund or adjustment?)"),
    "imp_code_conflict": ("le code {code} revient ligne {line} avec d'autres dates ou un autre logement", "code {code} comes back on line {line} with other dates or another listing"),
    "imp_ref_twice": ("la référence {ref} figure déjà ligne {line}", "reference {ref} is already on line {line}"),
    "imp_amounts_differ": ("brut − frais de service ≠ montant versé : vérifiez ce séjour", "gross − service fee ≠ amount paid: check this stay"),
    "imp_overlap": ("chevauche « {label} » ({start} → {end})", "overlaps \"{label}\" ({start} → {end})"),
    "imp_unavailable": ("dates marquées indisponibles sur ce bien ({start} → {end})", "dates marked unavailable on this property ({start} → {end})"),
    "imp_before_activity": ("arrivée avant le début d'activité du bien ({date})", "arrival before the property's activity start ({date})"),
    "imp_overlap_file": ("chevauche la ligne {line} du même fichier ({start} → {end})", "overlaps line {line} of the same file ({start} → {end})"),
    "imp_received_above": ("déjà reçu {received}, plus que le nouveau montant attendu ({expected}) : vérifiez les versements", "already received {received}, more than the new expected amount ({expected}): check the payouts"),
    "imp_twin_differs": ("montants différents de ceux du séjour saisi ({fields}) : ceux du séjour sont conservés", "amounts differ from the stay entered ({fields}): the stay's are kept"),
    "imp_not_text": ("Ce n'est pas un fichier CSV : un classeur (.xlsx, .ods) ou un PDF doit d'abord être enregistré au format CSV.", "This is not a CSV file: a workbook (.xlsx, .ods) or a PDF must first be saved as CSV."),
    "imp_cancelled_kept": ("ce séjour est annulé dans Rental Cockpit : il n'est pas modifié", "this stay is cancelled in Rental Cockpit: it is not changed"),
    "imp_ref_elsewhere": ("la référence {ref} existe déjà sur le bien « {property} » : vérifiez le bien choisi pour ce logement", "reference {ref} already exists on property \"{property}\": check the property chosen for this listing"),
    "imp_commission_rate": ("commission calculée : {rate} % du montant brut", "commission computed: {rate}% of the gross amount"),
    "imp_payout_exists": ("versement déjà enregistré", "payout already recorded"),
    "imp_payout_too_high": ("versement non enregistré : il dépasserait le montant attendu", "payout not recorded: it would exceed the expected amount"),
    "imp_file_known": ("Ce fichier a déjà été importé le {date}.", "This file was already imported on {date}."),
    "imp_ignored_transfers": ("{n} ligne(s) « Payout » ignorée(s) : ce sont des virements de montants déjà comptés.", "{n} \"Payout\" line(s) ignored: they are transfers of amounts already counted."),
    "imp_ignored_other": ("{n} ligne(s) sans montant ignorée(s) ({types}).", "{n} line(s) without an amount ignored ({types})."),
    "imp_payouts_checked": ("{n} versement(s) Airbnb, {total} au total : chacun correspond au centime aux lignes qu'il paie.", "{n} Airbnb payout(s), {total} in all: each matches the lines it pays to the cent."),
    "imp_payout_mismatch": ("Le versement de la ligne {line} ({amount}) ne correspond pas aux lignes qui le suivent ({explained}) : vérifiez-le dans l'export.", "The payout on line {line} ({amount}) does not match the lines after it ({explained}): check it in the export."),
    "imp_op_no_date": ("date de l'opération illisible", "unreadable date of the operation"),
    "imp_op_unknown": ("type d'opération « {type} » inconnu de Rental Cockpit : vérifiez sa nature avant de l'enregistrer", "operation type \"{type}\" unknown to Rental Cockpit: check what it is before recording it"),
    "imp_op_no_property": ("cette opération ne nomme pas de logement : choisissez le bien du fichier ci-dessus", "this operation names no listing: choose the property of the file above"),
    "imp_op_known": ("déjà enregistrée par un import précédent", "already recorded by an earlier import"),
    "imp_op_payout": ("versée par Airbnb le {date} (arrivée sur le compte au plus tard le {bank})", "sent by Airbnb on {date} (on the account by {bank} at the latest)"),
    "imp_op_withheld": ("retenue par Airbnb sur le versement du {date}", "withheld by Airbnb from the payout of {date}"),
    "imp_op_stay": ("concerne la réservation {ref}", "concerns booking {ref}"),
    "imp_overlap_cancelled": ("si l'une de ces réservations a été annulée et qu'Airbnb a versé un dédommagement, choisissez « Annulé, montant encaissé conservé » pour celle-là : le montant compte, ses nuits non", "if one of these bookings was cancelled and Airbnb paid a compensation, choose \"Cancelled, amount received kept\" for that one: the amount counts, its nights do not"),
}

AMOUNT_FIELDS = ("gross", "commission", "payout", "taxes_collected")
AMOUNT_PARAMS = ("received", "expected", "total", "amount", "explained")  # amounts in cents, written in the reader's language
DATE_PARAMS = ("date", "start", "end", "bank")  # ISO days, written « 5 oct. 2026 » or « 5 Oct 2026 »
MONTHS = {"fr": ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."),
          "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")}


def _day(value: Any, lang: str) -> str:
    try:
        day = date.fromisoformat(str(value)[:10])
    except ValueError:
        return str(value)
    return f"{day.day} {MONTHS['fr' if lang == 'fr' else 'en'][day.month - 1]} {day.year}"

FIELD_LABELS = {
    "start": ("arrivée", "arrival"), "end": ("départ", "departure"), "guests": ("voyageurs", "guests"),
    "gross": ("montant brut", "gross amount"), "commission": ("commission", "commission"), "payout": ("versement net", "net payout"),
    "taxes_collected": ("taxe de séjour", "tourist tax"), "external_ref": ("référence", "reference"),
}


def render(item: dict[str, Any], lang: str) -> str:
    fr, en = MESSAGES.get(item["code"], (item["code"], item["code"]))
    text = fr if lang == "fr" else en
    params = {}
    for key, value in item.get("params", {}).items():
        if key in AMOUNT_PARAMS:
            value = format_cents(value, lang)
        elif key in DATE_PARAMS:
            value = _day(value, lang)
        elif key == "fields":
            value = ", ".join(FIELD_LABELS.get(f, (f, f))[0 if lang == "fr" else 1] for f in value)
        params[key] = value
    try:
        return text.format(**params)
    except (KeyError, IndexError):  # pragma: no cover - defensive
        return text


def fingerprint(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class _Index:
    """Stays and payouts of the registry, looked up once: a 20,000-line file stays quick to check."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.by_ref: dict[str, list[dict[str, Any]]] = {}
        self.by_dates: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        live: dict[str, list[dict[str, Any]]] = {}
        for stay in data.get("stays", {}).values():
            if stay.get("external_ref"):
                self.by_ref.setdefault(stay["external_ref"], []).append(stay)
            if stay["status"] != "cancelled":
                self.by_dates.setdefault((stay["property_id"], stay["start"], stay["end"]), []).append(stay)
                live.setdefault(stay["property_id"], []).append(stay)
        # Per property, stays sorted by arrival with the latest departure so far: overlaps by bisection.
        self.sorted: dict[str, tuple[list[str], list[dict[str, Any]], list[str]]] = {}
        for pid, stays in live.items():
            stays.sort(key=lambda s: (s["start"], s["end"]))
            reach, latest = [], ""
            for stay in stays:
                latest = max(latest, stay["end"])
                reach.append(latest)
            self.sorted[pid] = ([s["start"] for s in stays], stays, reach)
        self.payouts: dict[str, list[tuple[str, int]]] = {}
        self.entry_paid: dict[str, int] = {}
        for payment in data.get("payments", {}).values():
            for link in payment["links"]:
                if link["type"] == "stay":
                    self.payouts.setdefault(link["id"], []).append((payment["date"], link["amount"]))
                else:
                    self.entry_paid[link["id"]] = self.entry_paid.get(link["id"], 0) + link["amount"]
        # Platform operations already recorded by an import, by the key the reader gives them.
        self.operations: dict[str, dict[str, Any]] = {}
        for entry in data.get("entries", {}).values():
            key = (entry.get("origin") or {}).get("key")
            if key:
                self.operations[key] = entry

    def overlapping(self, pid: str, start: str, end: str) -> list[dict[str, Any]]:
        starts, stays, reach = self.sorted.get(pid, ([], [], []))
        found = []
        index = bisect_left(starts, end) - 1  # stays arriving before this departure
        while index >= 0 and reach[index] > start:
            if stays[index]["end"] > start:
                found.append(stays[index])
            index -= 1
        return sorted(found, key=lambda s: s["start"])

    def received(self, stay_id: str) -> int:
        return sum(amount for _, amount in self.payouts.get(stay_id, []))


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


def _fills(stay: dict[str, Any], item: dict[str, Any]) -> list[dict[str, Any]]:
    """Completing a stay entered by hand: only what it does not know yet; what it knows is kept.

    When the file disagrees with an amount typed by hand, the net payout of
    the file is not added either: it would contradict the gross amount and
    commission kept on the stay.
    """
    current = stay.get("amounts") or {}
    found = {k: v for k, v in (item.get("amounts") or {}).items() if v is not None}
    differ = [k for k, v in found.items() if current.get(k) is not None and current[k] != v]
    if differ:
        item["warnings"].append({"code": "imp_twin_differs", "params": {"fields": differ}})
    fills = [{"field": k, "before": None, "after": v} for k, v in found.items()
             if current.get(k) is None and not (differ and k == "payout")]
    if item.get("external_ref") and not stay.get("external_ref"):
        fills.append({"field": "external_ref", "before": "", "after": item["external_ref"]})
    if item.get("guests") and not stay.get("guests"):
        fills.append({"field": "guests", "before": None, "after": item["guests"]})
    return fills


def commission_rate(value: Any) -> Decimal | None:
    """Commission rate typed by the person (« 15 », « 3,5 »), between 0 and 100 %, or ``None``."""
    text = str(value or "").strip().replace(",", ".").rstrip("%").strip()
    if not text:
        return None
    try:
        rate = Decimal(text)
    except InvalidOperation:
        return None
    return rate if rate.is_finite() and 0 <= rate <= 100 else None


def _match(index: _Index, item: dict[str, Any], pid: str, properties: dict[str, Any]) -> dict[str, Any] | None:
    """Status of a line against the registry; returns the stay it would change, if any."""
    ref = item["external_ref"]
    with_ref = index.by_ref.get(ref, []) if ref else []
    same_ref = next((s for s in with_ref if s["property_id"] == pid), None)
    if same_ref is not None:
        if same_ref["status"] == "cancelled":
            item["warnings"].append({"code": "imp_cancelled_kept", "params": {}})
            item.update(status="same", decision="skip", stay_id=same_ref["id"], locked=True)
            return None
        item["changes"] = _changes(same_ref, item)
        merged = {**(same_ref.get("amounts") or {}), **{k: v for k, v in (item["amounts"] or {}).items() if v is not None}}
        expected = expected_payout({**same_ref, "amounts": merged})
        received = index.received(same_ref["id"])
        if item["changes"] and expected is not None and received > expected:
            item["warnings"].append({"code": "imp_received_above", "params": {
                "received": received, "expected": expected}})
        item.update(status="update" if item["changes"] else "same", stay_id=same_ref["id"],
                    decision="import" if item["changes"] else "skip")
        return same_ref
    elsewhere = next((s for s in with_ref if s["property_id"] != pid), None)
    if elsewhere is not None:
        # The listing is probably attached to the wrong property: nothing is written unless the person insists.
        item["warnings"].append({"code": "imp_ref_elsewhere", "params": {
            "ref": ref, "property": properties.get(elsewhere["property_id"], {}).get("name", "—")}})
        item.update(status="duplicate", stay_id=None, decision="skip", twin_label=ref)
        return None
    twin = next(iter(index.by_dates.get((pid, item["start"], item["end"]), [])), None)
    if twin is not None:
        item.update(status="duplicate", stay_id=twin["id"], decision="complete",
                    twin_label=twin.get("guest_label") or twin.get("external_ref") or twin["start"])
        item["changes"] = _fills(twin, item)
        return twin
    item.update(status="new", decision="import")
    for other in index.overlapping(pid, item["start"], item["end"])[:3]:
        item["warnings"].append({"code": "imp_overlap", "params": {
            "label": other.get("guest_label") or other.get("external_ref") or "—", "start": other["start"], "end": other["end"]}})
    for block in properties[pid].get("unavailable", []):
        if block["start"] < item["end"] and item["start"] < block["end"]:
            item["warnings"].append({"code": "imp_unavailable", "params": {"start": block["start"], "end": block["end"]}})
    return None


def _allowed(item: dict[str, Any]) -> tuple[str, ...]:
    """Decisions the person can take on a line of the preview."""
    if item.get("locked") or item["status"] in ("error", "unmapped"):
        return ()
    if item.get("kind") == "operation":
        if item["status"] == "same":
            return ("import", "skip") if item.get("payout") else ()
        return ("import", "skip")
    if item["status"] == "new":
        # A booking cancelled late can still be paid: the amount counts, the nights do not (ANO-002).
        return ("import", "cancelled", "skip")
    if item["status"] == "duplicate":
        # Completing is only offered when it brings something: a missing amount, the reference, a payout.
        useful = item.get("stay_id") and (item["changes"] or item.get("payout"))
        return ("complete", "import", "skip") if useful else ("import", "skip")
    if item["status"] == "same":
        return ("import", "skip") if item.get("payout") else ()
    return ("import", "skip")


def _payout(index: _Index, item: dict[str, Any], target: dict[str, Any] | None, today: date) -> None:
    """Payout from the file (date of the transaction): recorded once, never above what is expected."""
    if not (item.get("paid_on") and item.get("paid_amount")) or item["paid_on"] > today.isoformat():
        return
    if target is None:
        item["payout"] = {"date": item["paid_on"], "amount": item["paid_amount"], "bank_by": item.get("bank_by", "")}
        return
    if (item["paid_on"], item["paid_amount"]) in index.payouts.get(target["id"], []):
        item["warnings"].append({"code": "imp_payout_exists", "params": {}})
        return
    if item["status"] == "duplicate":  # completing only fills what the stay does not know
        known = {c["field"]: c["after"] for c in item["changes"] if c["field"] in AMOUNT_FIELDS}
    else:
        known = {k: v for k, v in (item["amounts"] or {}).items() if v is not None}
    expected = expected_payout({**target, "amounts": {**(target.get("amounts") or {}), **known}})
    if expected is not None and index.received(target["id"]) + item["paid_amount"] > expected:
        item["warnings"].append({"code": "imp_payout_too_high", "params": {}})
        return
    item["payout"] = {"date": item["paid_on"], "amount": item["paid_amount"], "bank_by": item.get("bank_by", "")}


def build(data: dict[str, Any], parsed: dict[str, Any], options: dict[str, Any], today: date, content_hash: str) -> dict[str, Any]:
    """The preview: one entry per line of the file, with what would happen and why. Writes nothing."""
    properties = data.get("properties", {})
    rate = commission_rate(options.get("commission_rate")) if parsed["kind"] == "csv" else None
    decisions = options.get("decisions") or {}
    keep_names = bool(options.get("keep_names"))
    with_payouts = options.get("create_payouts", True) is not False
    index = _Index(data)
    rows = []
    planned: dict[str, list[dict[str, Any]]] = {}
    for row in parsed["rows"]:
        item: dict[str, Any] = {"key": row["key"], "lines": row["lines"], "external_ref": row.get("external_ref", ""),
                                "listing": row.get("listing", ""), "errors": list(row.get("errors", [])),
                                "warnings": list(row.get("warnings", [])), "changes": [], "payout": None}
        if item["errors"]:
            item.update(status="error", decision="skip")
            rows.append(item)
            continue
        item.update({key: row.get(key) for key in ("start", "end", "nights", "guests", "amounts", "paid_on", "paid_amount", "bank_by", "payout_ref")})
        if any(v is not None and v < 0 for v in (item["amounts"] or {}).values()):
            item["errors"].append({"code": "imp_negative", "params": {}})
            item.update(status="error", decision="skip")
            rows.append(item)
            continue
        if rate is not None and item["amounts"].get("gross") is not None and item["amounts"].get("commission") is None:
            # A CSV without the platform's fee: the rate the person typed gives it, to the cent (half up).
            fee = int((Decimal(item["amounts"]["gross"]) * rate / 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            item["amounts"] = {**item["amounts"], "commission": fee}
            item["warnings"].append({"code": "imp_commission_rate", "params": {"rate": format(rate.normalize(), "f")}})
        item["guest_label"] = row.get("guest_name", "") if keep_names else ""
        pid = _property_for(row, options, properties)
        item["property_id"] = pid
        if not pid:
            item.update(status="unmapped", decision="skip")
            rows.append(item)
            continue
        prop = properties[pid]
        target = _match(index, item, pid, properties)
        start_limit = prop.get("activity_start")
        if start_limit and item["start"] < start_limit and item["status"] in ("new", "duplicate"):
            item["warnings"].append({"code": "imp_before_activity", "params": {"date": start_limit}})
            item["decision"] = "skip"
        choice = decisions.get(item["key"])
        if choice in _allowed(item) and item["status"] != "same":
            item["decision"] = choice
        if item["status"] == "duplicate" and item["decision"] == "import":
            target = None  # a new stay next to the one entered by hand: the payout goes to the new one
        if with_payouts:
            _payout(index, item, target, today)
        if item["decision"] == "complete" and not item["changes"] and not item["payout"]:
            item["decision"] = "skip"  # the stay entered by hand already knows everything the line says
        if item["status"] == "same" and not item.get("locked"):
            # Nothing to change on the stay; the line still matters when it brings a payout.
            item["decision"] = "import" if item["payout"] else "skip"
            if item["payout"] and choice in ("import", "skip"):
                item["decision"] = choice
        if item["decision"] not in ("skip", "cancelled") and item["status"] in ("new", "duplicate") and target is None:
            planned.setdefault(pid, []).append(item)
        if item["status"] == "new" and any(w["code"] == "imp_overlap" for w in item["warnings"]):
            item["warnings"].append({"code": "imp_overlap_cancelled", "params": {}})
        rows.append(item)

    # Two new stays of the same file on the same nights: both lines say so before anything is written.
    for items in planned.values():
        active: list[dict[str, Any]] = []
        for item in sorted(items, key=lambda i: (i["start"], i["lines"][0])):
            active = [other for other in active if other["end"] > item["start"]]
            for other in active[:3]:
                for here, there in ((item, other), (other, item)):
                    here["warnings"].append({"code": "imp_overlap_file", "params": {
                        "line": there["lines"][0], "start": there["start"], "end": there["end"]}})
                    if not any(w["code"] == "imp_overlap_cancelled" for w in here["warnings"]):
                        here["warnings"].append({"code": "imp_overlap_cancelled", "params": {}})
            active.append(item)

    rows += _operations(parsed, options, data, index, decisions, today, with_payouts, rows)
    for item in rows:
        item["choices"] = list(_allowed(item))
    known = [i for i in data.get("imports", {}).values() if i.get("sha256") == content_hash and not i.get("undone_at")]
    notices = list(parsed.get("warnings", []))
    payouts = parsed.get("payouts") or []
    mismatched = [p for p in payouts if p["explained"] != p["amount"]]
    if payouts and not mismatched:
        notices.append({"code": "imp_payouts_checked", "params": {"n": len(payouts), "total": sum(p["amount"] for p in payouts)}})
    for payout in mismatched[:5]:
        notices.append({"code": "imp_payout_mismatch", "params": {"line": payout["line"], "amount": payout["amount"], "explained": payout["explained"]}})
    if not payouts and parsed["ignored"]["transfers"]:
        notices.append({"code": "imp_ignored_transfers", "params": {"n": parsed["ignored"]["transfers"]}})
    if parsed["ignored"]["other"]:
        notices.append({"code": "imp_ignored_other", "params": {"n": sum(parsed["ignored"]["other"].values()),
                                                               "types": ", ".join(sorted(parsed["ignored"]["other"]))}})
    if known:
        notices.append({"code": "imp_file_known", "params": {"date": known[-1]["at"][:10]}})
    stays_rows = [r for r in rows if r.get("kind") != "operation"]
    counts = {status: sum(1 for r in stays_rows if r["status"] == status) for status in STATUSES}
    counts["to_write"] = sum(1 for r in stays_rows if r["decision"] != "skip" and (
        r["status"] in ("new", "update") or (r["status"] == "duplicate" and (r["decision"] == "import" or r["changes"]))))
    counts["payouts"] = sum(1 for r in rows if r["payout"] and r["decision"] != "skip")
    counts["operations"] = sum(1 for r in rows if r.get("kind") == "operation")
    counts["entries"] = sum(1 for r in rows if r.get("kind") == "operation" and r["status"] == "new" and r["decision"] == "import")
    counts["cancelled"] = sum(1 for r in stays_rows if r["decision"] == "cancelled")
    return {"rows": rows, "counts": counts, "errors": parsed["errors"], "notices": notices,
            "reconciliation": _reconcile(parsed, rows, index),
            "can_apply": not parsed["errors"] and counts["to_write"] + counts["payouts"] + counts["entries"] > 0}


def _single_property(options: dict[str, Any], properties: dict[str, Any]) -> str | None:
    """The property of a line that names no listing: the one chosen for the file, or the only one used."""
    pid = options.get("property_id")
    if pid in properties and not properties[pid].get("archived"):
        return pid
    used = {v for v in (options.get("property_map") or {}).values() if v in properties and not properties[v].get("archived")}
    return next(iter(used)) if len(used) == 1 else None


def _operations(parsed: dict[str, Any], options: dict[str, Any], data: dict[str, Any], index: _Index,
                decisions: dict[str, Any], today: date, with_payouts: bool, stay_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lines of the platform that are not bookings: what each becomes, as income or expense of a property."""
    properties, categories = data.get("properties", {}), data.get("categories", {})
    planned_refs = {(r.get("property_id"), r["external_ref"]) for r in stay_rows
                    if r.get("external_ref") and r["decision"] != "skip" and r["status"] in ("new", "duplicate")}
    items = []
    for op in parsed.get("operations") or []:
        amount = op["amount"]
        family = op["family"]
        item: dict[str, Any] = {
            "key": op["key"], "kind": "operation", "lines": op["lines"], "family": family, "type_label": op["type_label"],
            "external_ref": op["external_ref"], "listing": op["listing"], "details": op["details"], "op_key": op["op_key"],
            "date": op["date"], "start": op["start"], "end": op["end"], "errors": list(op["errors"]), "warnings": [], "facts": [],
            "changes": [], "payout": None, "amounts": None, "nights": None, "paid_on": op["paid_on"], "bank_by": op["bank_by"],
            "payout_ref": op["payout_ref"], "amount": abs(amount) if amount is not None else None,
            "direction": "out" if (amount or 0) < 0 else "in",
        }
        items.append(item)
        if item["errors"]:
            item.update(status="error", decision="skip")
            continue
        income = item["direction"] == "in"
        category_id = OPERATION_CATEGORIES.get(family) if income else ("guest_refund" if family == "adjustment" else None)
        if family == "adjustment" and income:
            category_id = "platform_compensation"
        fallback = "other_income" if income else "other_expense"
        usable = categories.get(category_id or "") or {}
        item["category_id"] = category_id if usable and not usable.get("archived") else fallback
        name = OPERATION_LABELS[family]
        item["label_pair"] = name if family != "unknown" else (op["type_label"], op["type_label"])
        item["warnings"] += [{"code": "imp_op_unknown", "params": {"type": op["type_label"]}}] if family == "unknown" else []
        if op["external_ref"]:
            item["facts"].append({"code": "imp_op_stay", "params": {"ref": op["external_ref"]}})
        pid = _property_for(op, options, properties) if op["listing"] else _single_property(options, properties)
        item["property_id"] = pid
        if not pid:
            if not op["listing"]:
                item["warnings"].append({"code": "imp_op_no_property", "params": {}})
            item.update(status="unmapped", decision="skip")
            continue
        stay = next((s for s in index.by_ref.get(op["external_ref"], []) if s["property_id"] == pid), None) if op["external_ref"] else None
        item["stay_id"] = stay["id"] if stay else ""
        item["stay_ref"] = op["external_ref"] if not stay and (pid, op["external_ref"]) in planned_refs else ""
        paid = bool(with_payouts and op["paid_on"] and op["paid_on"] <= today.isoformat())
        existing = index.operations.get(op["op_key"])
        if existing is not None:
            item.update(status="same", decision="skip", entry_id=existing["id"], known=True)
            remaining = existing["amount"] - index.entry_paid.get(existing["id"], 0)
            if paid and remaining > 0:
                item["payout"] = {"date": op["paid_on"], "amount": remaining, "bank_by": op["bank_by"]}
                item["decision"] = "import"
            else:
                item["facts"].append({"code": "imp_op_known", "params": {}})
        else:
            item.update(status="new", decision="import" if family != "unknown" else "skip")
            if paid:
                item["payout"] = {"date": op["paid_on"], "amount": item["amount"], "bank_by": op["bank_by"]}
        if item["payout"]:
            item["facts"].append({"code": "imp_op_payout" if income else "imp_op_withheld",
                                     "params": {"date": op["paid_on"], "bank": op["bank_by"] or op["paid_on"]}})
        choice = decisions.get(item["key"])
        if choice in _allowed(item):
            item["decision"] = choice
    return items


def _money_state(item: dict[str, Any] | None, index: _Index) -> str:
    """For one line paid by a payout: ``new`` (recorded now), ``known`` (already recorded) or ``left``."""
    if item is None:
        return "left"
    if item["decision"] != "skip" and item.get("payout"):
        return "new"
    if item.get("kind") == "operation":
        return "known" if item.get("known") and not item.get("payout") else "left"
    stay_id = item.get("stay_id")
    if stay_id and any(amount == item.get("paid_amount") for _, amount in index.payouts.get(stay_id, [])):
        return "known"
    return "left"


def _reconcile(parsed: dict[str, Any], rows: list[dict[str, Any]], index: _Index) -> dict[str, Any] | None:
    """« Bilan des versements » : every payout of the file, what it pays, and what would stay unrecorded."""
    payouts = parsed.get("payouts") or []
    if not payouts:
        return None
    by_key = {r["key"]: r for r in rows if r.get("kind") == "operation"}
    stays = {r["external_ref"]: r for r in rows if r.get("kind") != "operation" and r.get("external_ref")}
    kinds = {"stay": 0, "compensation": 0, "credit": 0, "adjustment": 0, "unknown": 0}
    states = {"new": 0, "known": 0, "left": 0}
    months: dict[str, dict[str, int]] = {}
    left: list[dict[str, Any]] = []
    for payout in payouts:
        month = months.setdefault(payout["date"][:7], {"total": 0, "stay": 0, "other": 0, "left": 0})
        month["total"] += payout["amount"]
        for part in payout["parts"]:
            item = stays.get(part["ref"]) if part["kind"] == "stay" else by_key.get(part.get("key", ""))
            state = _money_state(item, index)
            kinds[part["kind"]] += part["amount"]
            states[state] += part["amount"]
            month["stay" if part["kind"] == "stay" else "other"] += part["amount"]
            if state == "left":
                month["left"] += part["amount"]
                left.append({"line": part["line"], "ref": part["ref"], "amount": part["amount"], "date": payout["date"],
                             "kind": part["kind"], "key": item["key"] if item else ""})
    return {"count": len(payouts), "total": sum(p["amount"] for p in payouts), "kinds": kinds, "states": states,
            "left": left[:50], "left_count": len(left),
            "mismatched": [{"line": p["line"], "amount": p["amount"], "explained": p["explained"]} for p in payouts if p["explained"] != p["amount"]],
            "months": [{"month": m, **v} for m, v in sorted(months.items(), reverse=True)]}


def apply(ledger: Ledger, plan: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    """Write the plan in the working copy held by ``ledger`` (one transaction for the caller)."""
    if plan["errors"] or not plan["can_apply"]:
        raise RCError("import_nothing")
    import_id = new_id("imp")
    source = "airbnb" if meta["kind"] == "airbnb" else "csv"
    record = {"id": import_id, "seq": len(ledger.data.get("imports", {})) + 1, "at": ledger.clock(), "by": ledger.actor, "kind": meta["kind"], "reader": meta["reader"],
              "file_name": meta.get("file_name", "")[:120], "sha256": meta["sha256"], "created": [], "updated": [],
              "payments": [], "entries": [], "counts": {}, "undone_at": None}
    ledger.bulk = True
    try:
        counts = _write(ledger, plan, record, import_id, source, meta)
    finally:
        ledger.bulk = False
    # Recording a payment changes nothing to a stay's revision: the undo check below still holds.
    record["counts"] = counts
    ledger.data.setdefault("imports", {})[import_id] = record
    ledger.audit("import.apply", import_id, detail="{}:{created}+{updated}+{completed}+{payouts}+{entries}".format(meta["kind"], **counts))
    return {"import": summary(record)}


def _write(ledger: Ledger, plan: dict[str, Any], record: dict[str, Any], import_id: str, source: str,
           meta: dict[str, Any]) -> dict[str, int]:
    created = updated = completed = payouts = entries = 0
    created_refs: dict[tuple[str, str], str] = {}
    for row in plan["rows"]:
        if row["decision"] == "skip" or row["status"] in ("error", "unmapped"):
            continue
        if row.get("kind") == "operation":
            continue  # after the stays: an operation can concern a stay created by this import
        stay_id = row.get("stay_id")
        if row["status"] == "new" or (row["status"] == "duplicate" and row["decision"] == "import"):
            payload = {"property_id": row["property_id"], "start": row["start"], "end": row["end"], "guests": row.get("guests"),
                       "guest_label": row.get("guest_label", ""), "external_ref": row.get("external_ref", ""),
                       "channel": "airbnb" if source == "airbnb" else meta.get("channel") or "other",
                       "status": "cancelled" if row["decision"] == "cancelled" else "confirmed",
                       "amounts": {f"{k}_cents": v for k, v in (row.get("amounts") or {}).items() if v is not None}}
            stay = ledger.create_stay(payload, source=source, origin_import=import_id)["stay"]
            stay_id = stay["id"]
            record["created"].append({"id": stay_id, "revision": stay["revision"]})
            created += 1
            if stay["external_ref"]:
                created_refs[(stay["property_id"], stay["external_ref"])] = stay_id
        elif row["status"] in ("update", "duplicate"):
            stay = ledger.data["stays"][stay_id]
            before = deepcopy({k: stay.get(k) for k in ("start", "end", "guests", "amounts", "external_ref", "guest_label")})
            revision_before = int(stay.get("revision") or 0)
            fields: dict[str, Any] = {}
            if row["status"] == "update":
                for change in row["changes"]:
                    if change["field"] in ("start", "end", "guests"):
                        fields[change["field"]] = change["after"]
                amounts = {f"{c['field']}_cents": c["after"] for c in row["changes"] if c["field"] in AMOUNT_FIELDS}
            else:  # complete a stay entered by hand: what the preview listed, nothing else
                amounts = {f"{c['field']}_cents": c["after"] for c in row["changes"] if c["field"] in AMOUNT_FIELDS}
                fields.update({c["field"]: c["after"] for c in row["changes"] if c["field"] in ("external_ref", "guests")})
            if amounts:
                fields["amounts"] = amounts
            if fields:
                result = ledger.update_stay(stay_id, fields)["stay"]
                record["updated"].append({"id": stay_id, "before": before, "revision_before": revision_before,
                                          "revision": result["revision"]})
                updated += row["status"] == "update"
                completed += row["status"] == "duplicate"
        if row.get("payout") and stay_id:
            payment = ledger.create_payment({
                "property_id": row["property_id"], "direction": "in", "date": row["payout"]["date"],
                "expected_on": row["payout"].get("bank_by") or "",
                "amount_cents": row["payout"]["amount"],
                "links": [{"type": "stay", "id": stay_id, "amount_cents": row["payout"]["amount"]}],
                "method": "Import Airbnb" if source == "airbnb" else "Import CSV",
                "origin": {"type": "import", "id": import_id, "payout_ref": row.get("payout_ref") or ""},
            })["payment"]
            record["payments"].append(payment["id"])
            payouts += 1
    for row in plan["rows"]:
        if row.get("kind") != "operation" or row["decision"] == "skip" or row["status"] in ("error", "unmapped"):
            continue
        entry_id = row.get("entry_id") or ""
        if row["status"] == "new":
            entry_id = _create_operation(ledger, row, import_id, created_refs, meta.get("lang", "fr"))
            record["entries"].append(entry_id)
            entries += 1
        if row.get("payout") and entry_id:
            payment = ledger.create_payment({
                "property_id": row["property_id"], "direction": row["direction"], "date": row["payout"]["date"],
                "expected_on": row["payout"].get("bank_by") or "", "amount_cents": row["payout"]["amount"],
                "links": [{"type": "entry", "id": entry_id, "amount_cents": row["payout"]["amount"]}],
                "method": ("Import Airbnb" if row["direction"] == "in" else "Retenue Airbnb"),
                "origin": {"type": "import", "id": import_id, "payout_ref": row.get("payout_ref") or ""},
            })["payment"]
            record["payments"].append(payment["id"])
            payouts += 1
    return {"created": created, "updated": updated, "completed": completed, "payouts": payouts, "entries": entries}


def _create_operation(ledger: Ledger, row: dict[str, Any], import_id: str, created_refs: dict[tuple[str, str], str], lang: str) -> str:
    """An income or expense of the property for a platform operation, traced back to its line and import."""
    fr = lang == "fr"
    name = row["label_pair"][0 if fr else 1]
    label = f"{name} — {row['details']}" if row.get("details") else name
    stay_id = row.get("stay_id") or created_refs.get((row["property_id"], row.get("stay_ref") or ""), "")
    note_bits = []
    if row.get("external_ref"):
        note_bits.append(("Réservation " if fr else "Booking ") + row["external_ref"])
    if row.get("start") and row.get("end"):
        note_bits.append(f"{row['start']} → {row['end']}")
    note_bits.append(("Ligne {n} de l'export Airbnb" if fr else "Line {n} of the Airbnb export").format(n=row["lines"][0]))
    result = ledger.create_entry({
        "property_id": row["property_id"], "kind": "income" if row["direction"] == "in" else "expense",
        "category_id": row["category_id"], "label": label[:140], "amount_cents": row["amount"], "date": row["date"],
        "stay_id": stay_id, "payment_declared": "unpaid" if row["direction"] == "out" else "unknown",
        "note": " · ".join(note_bits)[:600],
    }, origin={"type": "import", "id": import_id, "key": row["op_key"], "source": "airbnb", "line": row["lines"][0]})
    return result["entry"]["id"]


def summary(record: dict[str, Any]) -> dict[str, Any]:
    """What the interface shows of an import (the full record, with every stay, stays in the registry)."""
    return {k: record.get(k) for k in ("id", "at", "kind", "reader", "file_name", "counts", "undone_at")}


def last_import(data: dict[str, Any]) -> dict[str, Any] | None:
    live = [i for i in data.get("imports", {}).values() if not i.get("undone_at")]
    return max(live, key=lambda i: (i["at"], i.get("seq", 0))) if live else None


def undo_blockers(data: dict[str, Any], record: dict[str, Any]) -> list[str]:
    """Stays of the import changed since: undoing would erase someone's work, so it is refused."""
    blockers = []
    own = set(record["payments"])
    own_entries = set(record.get("entries", []))
    for entry_id in own_entries:
        entry = data.get("entries", {}).get(entry_id)
        if entry is None:
            continue
        foreign = [p for p in data.get("payments", {}).values() if p["id"] not in own
                   and any(link["type"] == "entry" and link["id"] == entry_id for link in p["links"])]
        documents = [d for d in data.get("documents", {}).values() if entry_id in (d.get("entry_ids") or [])]
        if int(entry.get("revision") or 0) != 1 or foreign or documents or entry.get("archived"):
            blockers.append(entry["label"][:60])
    for item in record["created"] + record["updated"]:
        stay = data["stays"].get(item["id"])
        if stay is None:
            continue
        if int(stay.get("revision") or 0) != item["revision"]:
            blockers.append(stay.get("guest_label") or stay.get("external_ref") or stay["start"])
            continue
        foreign = [p for p in data.get("payments", {}).values() if p["id"] not in own
                   and any(link["type"] == "stay" and link["id"] == stay["id"] for link in p["links"])]
        linked = [e for e in data.get("entries", {}).values() if e["id"] not in own_entries and (
                  e.get("stay_id") == stay["id"] or any(a.get("stay_id") == stay["id"] for a in e.get("allocations", [])))]
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
    for entry_id in record.get("entries", []):
        data["entries"].pop(entry_id, None)
    for item in record["created"]:
        data["stays"].pop(item["id"], None)
    restored = {}
    for item in record["updated"]:
        stay = data["stays"].get(item["id"])
        if stay is None:
            continue
        before = deepcopy(stay)
        stay.update(deepcopy(item["before"]))
        ledger._history(stay, before, ("start", "end", "guests", "amounts", "external_ref", "guest_label"))
        restored[item["id"]] = (item.get("revision_before"), int(stay.get("revision") or 0))
    record["undone_at"] = ledger.clock()
    record["undone_by"] = ledger.actor
    # The stays are back where the previous import left them: that import can be undone in turn.
    previous = last_import(data)
    for entry in (previous["created"] + previous["updated"]) if previous else []:
        if entry["id"] in restored and entry["revision"] == restored[entry["id"]][0]:
            entry["revision"] = restored[entry["id"]][1]
    ledger.audit("import.undo", import_id, detail=f"{len(record['created'])}+{len(record['updated'])}+{len(record['payments'])}+{len(record.get('entries', []))}")
    return {"import": summary(record)}

