# Copyright © 2026 Vincent Fournet
"""CSV exports of the expenses and the stays, for a spreadsheet or an accountant.

The files open directly in a spreadsheet: UTF-8 with a byte order mark,
semicolons and decimal commas in French, commas and decimal points in
English. A text that a spreadsheet would run as a formula (starting with
``=``, ``+``, ``-``, ``@``, a tab or a carriage return) is written with a
leading apostrophe: an imported label can never become a formula on the
accountant's computer (SEC 06). Amounts are produced here, never from free
text, and are written as plain numbers.
"""
from __future__ import annotations

import csv
import io
from typing import Any, Iterable

from .schema import label

FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def safe_text(value: Any) -> str:
    text = str(value or "").replace("\r\n", " ").replace("\n", " ")
    return "'" + text if text.startswith(FORMULA_STARTS) else text


def _amount(cents: int | None, lang: str) -> str:
    if cents is None:
        return ""
    sign = "-" if cents < 0 else ""
    units, rest = divmod(abs(cents), 100)
    return f"{sign}{units}{',' if lang == 'fr' else '.'}{rest:02d}"


def _write(header: list[str], rows: Iterable[list[str]], lang: str) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";" if lang == "fr" else ",", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    writer.writerows(rows)
    return ("﻿" + buffer.getvalue()).encode("utf-8")


ENTRY_HEADER = {
    "fr": ["Date", "Bien", "Type", "Catégorie", "Traitement", "Libellé", "Fournisseur", "N° de facture", "Montant", "Réglé", "Reste",
           "État du paiement", "Début de période", "Fin de période", "Capital", "Intérêts", "Assurance", "Séjour", "Archivée", "Note"],
    "en": ["Date", "Property", "Type", "Category", "Treatment", "Label", "Supplier", "Invoice number", "Amount", "Settled", "Remaining",
           "Payment status", "Period start", "Period end", "Principal", "Interest", "Insurance", "Stay", "Archived", "Note"],
}


def entries_csv(data: dict[str, Any], items: list[dict[str, Any]], lang: str) -> bytes:
    yes, no = ("oui", "non") if lang == "fr" else ("yes", "no")
    rows = []
    for item in items:
        split = item.get("loan_split") or {}
        rows.append([
            item["date"], safe_text(item["property"]), item["kind_label"], safe_text(item["category"]), item["treatment_label"],
            safe_text(item["label"]), safe_text(item["supplier"]), safe_text(item["invoice_number"]),
            _amount(item["amount"], lang), _amount(item["paid"], lang), _amount(item["remaining"], lang), item["state_label"],
            item["period_start"], item["period_end"],
            _amount(split.get("principal"), lang), _amount(split.get("interest"), lang), _amount(split.get("insurance"), lang),
            safe_text(item["stay_label"]), yes if item["archived"] else no,
            safe_text(data["entries"].get(item["id"], {}).get("note", "")),
        ])
    return _write(ENTRY_HEADER["fr" if lang == "fr" else "en"], rows, lang)


STAY_HEADER = {
    "fr": ["Arrivée", "Départ", "Nuits", "Bien", "Canal", "Référence", "Libellé", "Voyageurs", "Statut", "Montant brut", "Commission",
           "Versement net attendu", "Reçu", "Taxe de séjour", "Caution", "État du versement"],
    "en": ["Arrival", "Departure", "Nights", "Property", "Channel", "Reference", "Label", "Guests", "Status", "Gross amount", "Commission",
           "Expected net payout", "Received", "Tourist tax", "Security deposit", "Payout status"],
}


def stays_csv(items: list[dict[str, Any]], lang: str) -> bytes:
    rows = []
    for item in items:
        amounts = item["amounts"]
        rows.append([
            item["start"], item["end"], str(item["nights"]), safe_text(item["property"]), item["channel_label"],
            safe_text(item["external_ref"]), safe_text(item["guest_label"]), str(item["guests"] or ""),
            label("stay_status", item["status"], lang),
            _amount(amounts.get("gross"), lang), _amount(amounts.get("commission"), lang), _amount(item["expected_payout"], lang),
            _amount(item["received"], lang), _amount(amounts.get("taxes_collected"), lang), _amount(amounts.get("deposit"), lang),
            item["payout_label"],
        ])
    return _write(STAY_HEADER["fr" if lang == "fr" else "en"], rows, lang)

