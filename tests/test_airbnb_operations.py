# Copyright © 2026 Vincent Fournet
"""Airbnb lines that are not bookings, and bookings cancelled but paid (acceptance ANO-001, ANO-002).

The export used here is fictional (``fixtures/airbnb_operations_fr.csv``), built like a real
« Historique des transactions »: each « Payout » line is followed by the lines it pays.

* October 2026: six payouts, 1 355,00 € in all — five bookings (1 260,00 €) and an AirCover
  damage refund (95,00 €) for booking HMFICT0001;
* September: a platform credit (15,00 €), a payout of 350,00 € = a booking of 400,00 € minus a
  resolution adjustment of 50,00 € refunded to a guest, and a line of a type the reader does not
  know (7,50 €);
* May: HMFICT0101, five nights from 18 May, cancelled late and paid 211,80 € net, overlapping
  HMFICT0102, the night of 22 May, really spent.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from rental_cockpit.engine.imports import airbnb, plan
from rental_cockpit.engine.indicators import compute, month_period
from rental_cockpit.engine.ledger import Ledger
from rental_cockpit.engine.schema import empty_registry

EXPORT = (Path(__file__).parent / "fixtures" / "airbnb_operations_fr.csv").read_bytes()
TODAY = date(2026, 11, 2)
LISTING = "Gîte d'essai (annonce)"


@pytest.fixture
def gite():
    data = empty_registry()
    ledger = Ledger(data, "1")
    pid = ledger.create_property({"name": "Gîte d'essai"})["property"]["id"]
    return data, ledger, pid


def preview(data, pid, **options):
    parsed = airbnb.parse(EXPORT)
    return plan.build(data, parsed, {"property_map": {LISTING: pid}, **options}, TODAY, plan.fingerprint(EXPORT))


def run(ledger, pid, **options):
    built = preview(ledger.data, pid, **options)
    meta = {"kind": "airbnb", "reader": airbnb.READER_VERSION, "sha256": plan.fingerprint(EXPORT), "file_name": "export.csv", "lang": "fr"}
    summary = plan.apply(ledger, built, meta)["import"]
    return built, ledger.data["imports"][summary["id"]]


def ops(built):
    return {r["family"]: r for r in built["rows"] if r.get("kind") == "operation"}


def stays(built):
    return {r["external_ref"]: r for r in built["rows"] if r.get("kind") != "operation"}


def figures(data, pid, year, month, mode):
    start, end = month_period(year, month)
    result = compute(data, property_ids={pid}, start=start, end=end, mode=mode, lang="fr", today=TODAY, compare=False)
    return result["indicators"]


def test_every_payout_is_checked_against_the_lines_it_pays():
    parsed = airbnb.parse(EXPORT)
    assert parsed["errors"] == [] and len(parsed["payouts"]) == 11
    assert all(p["explained"] == p["amount"] for p in parsed["payouts"])
    october = [p for p in parsed["payouts"] if p["date"].startswith("2026-10")]
    assert sum(p["amount"] for p in october) == 135500
    aircover = next(p for p in october if p["amount"] == 9500)
    assert (aircover["date"], aircover["bank_by"], [part["kind"] for part in aircover["parts"]]) == ("2026-10-20", "2026-10-28", ["compensation"])


def test_a_aircover_refund_is_one_income_without_nights(gite):
    """TEST-A: the payout and the resolution line are one sum of 95 €, an income outside stays."""
    data, ledger, pid = gite
    built = preview(data, pid)
    refund = ops(built)["compensation"]
    assert (refund["status"], refund["decision"], refund["category_id"], refund["amount"]) == ("new", "import", "platform_compensation", 9500)
    assert refund["payout"] == {"date": "2026-10-20", "amount": 9500, "bank_by": "2026-10-28"}
    nights_before = figures(data, pid, 2026, 10, "activity")["nights"]["value"]
    _, record = run(ledger, pid)
    entries = [e for e in data["entries"].values() if e["category_id"] == "platform_compensation"]
    assert len(entries) == 1
    entry = entries[0]
    assert (entry["kind"], entry["amount"], entry["date"], entry["origin"]["source"]) == ("income", 9500, "2026-10-20", "airbnb")
    assert entry["label"].startswith("Indemnisation Airbnb — Remboursement des dommages AirCover")
    assert entry["stay_id"] == next(s["id"] for s in data["stays"].values() if s["external_ref"] == "HMFICT0001")
    [payment] = [p for p in data["payments"].values() if p["links"][0]["id"] == entry["id"]]
    assert (payment["date"], payment["expected_on"], payment["amount"], payment["direction"]) == ("2026-10-20", "2026-10-28", 9500, "in")
    # No booking was created for it and no night is added.
    assert not any(s["start"] == "2026-10-16" and s["external_ref"] != "HMFICT0001" for s in data["stays"].values())
    assert figures(data, pid, 2026, 10, "activity")["nights"]["value"] == nights_before + 12  # the five October bookings only
    # Re-importing the same file adds nothing.
    again = preview(data, pid)
    assert ops(again)["compensation"]["status"] == "same" and again["counts"]["entries"] == 0
    assert again["reconciliation"]["states"]["left"] == 750  # only the line of unknown type, still not recorded
    assert record["counts"]["entries"] == 3


def test_c_october_payouts_add_up_with_the_refund_apart(gite):
    """TEST-C: the six October payouts are found again, 1 355 €, the damage refund apart from stays."""
    data, ledger, pid = gite
    built = preview(data, pid)
    october = next(m for m in built["reconciliation"]["months"] if m["month"] == "2026-10")
    assert october == {"month": "2026-10", "total": 135500, "stay": 126000, "other": 9500, "left": 0}
    run(ledger, pid)
    cash = figures(data, pid, 2026, 10, "cash")
    assert cash["revenue"]["value"] == 135500
    by_category = {line["category_id"]: line["share"] for line in
                   compute(data, property_ids={pid}, start=date(2026, 10, 1), end=date(2026, 11, 1), mode="cash",
                           lang="fr", today=TODAY, compare=False, with_lines=True)["indicators"]["revenue"]["lines"]
                   if line["category_id"] == "platform_compensation"}
    assert by_category == {"platform_compensation": 9500}


def test_adjustment_withheld_from_a_payout_and_platform_credit(gite):
    """September: received 400 + 15, 50 withheld for a guest: the bank sees 350 + 15."""
    data, ledger, pid = gite
    built, _ = run(ledger, pid)
    assert ops(built)["adjustment"]["category_id"] == "guest_refund" and ops(built)["credit"]["category_id"] == "platform_credit"
    cash = figures(data, pid, 2026, 9, "cash")
    assert cash["revenue"]["value"] == 41500
    assert cash["operating_expenses"]["value"] == 5000
    assert cash["operating_balance"]["value"] == 36500  # = the two payouts of the month that were recorded
    refund = next(e for e in data["entries"].values() if e["category_id"] == "guest_refund")
    assert (refund["kind"], refund["amount"], refund["payment_declared"]) == ("expense", 5000, "unpaid")
    assert ledger.entry_paid(refund["id"]) == 5000


def test_unknown_type_is_shown_with_its_amount_and_needs_a_choice(gite):
    data, ledger, pid = gite
    built = preview(data, pid)
    unknown = ops(built)["unknown"]
    assert (unknown["status"], unknown["decision"], unknown["choices"]) == ("new", "skip", ["import", "skip"])
    assert [w["code"] for w in unknown["warnings"]][0] == "imp_op_unknown"
    left = built["reconciliation"]["left"]
    assert [(item["amount"], item["kind"]) for item in left] == [(750, "unknown")]
    assert built["reconciliation"]["states"]["left"] == 750
    chosen = preview(data, pid, decisions={unknown["key"]: "import"})
    assert chosen["reconciliation"]["states"]["left"] == 0
    assert ops(chosen)["unknown"]["category_id"] == "other_income"


def test_operation_without_listing_needs_the_property_of_the_file(gite):
    data, ledger, pid = gite
    other = ledger.create_property({"name": "Studio d'essai"})["property"]["id"]
    parsed = airbnb.parse(EXPORT)
    built = plan.build(data, parsed, {"property_map": {LISTING: pid}}, TODAY, "x")
    assert ops(built)["credit"]["property_id"] == pid  # every listing goes to one property: the credit goes there too
    ambiguous = plan.build(data, parsed, {"property_map": {LISTING: pid}, "property_id": other}, TODAY, "x")
    assert ops(ambiguous)["credit"]["property_id"] == other  # the property chosen for the file wins


def test_b_cancelled_but_paid_booking_keeps_the_money_not_the_nights(gite):
    """TEST-B: a late cancellation paid 211,80 €, then a one-night booking on the same dates."""
    data, ledger, pid = gite
    built = preview(data, pid)
    cancelled, real = stays(built)["HMFICT0101"], stays(built)["HMFICT0102"]
    assert "cancelled" in cancelled["choices"]
    for line in (cancelled, real):
        assert [w["code"] for w in line["warnings"]] == ["imp_overlap_file", "imp_overlap_cancelled"]
    decided = preview(data, pid, decisions={cancelled["key"]: "cancelled"})
    assert stays(decided)["HMFICT0102"]["warnings"] == []  # no overlap left once the cancellation is known
    assert decided["counts"]["cancelled"] == 1
    _, record = run(ledger, pid, decisions={cancelled["key"]: "cancelled"})
    stay = next(s for s in data["stays"].values() if s["external_ref"] == "HMFICT0101")
    assert stay["status"] == "cancelled"
    assert stay["amounts"]["gross"] == 22000 and stay["amounts"]["payout"] == 21180
    assert ledger.data["payments"] and any(link["id"] == stay["id"] for p in data["payments"].values() for link in p["links"])
    may = figures(data, pid, 2026, 5, "activity")
    assert may["nights"]["value"] == 1  # only the night really spent
    assert may["revenue"]["value"] == 22000 + 12500  # the retained amount counts once, with the night of 22 May
    assert figures(data, pid, 2026, 5, "cash")["revenue"]["value"] == 21180 + 12050
    again = preview(data, pid)
    assert stays(again)["HMFICT0101"]["status"] == "same" and again["counts"]["to_write"] == 0
    assert record["counts"]["created"] == 8


def test_undo_removes_the_operations_of_the_import(gite):
    data, ledger, pid = gite
    _, record = run(ledger, pid)
    assert plan.undo_blockers(data, record) == []
    plan.undo(ledger, record["id"])
    assert data["entries"] == {} and data["payments"] == {} and data["stays"] == {}


def test_undo_is_refused_once_an_operation_was_changed(gite):
    data, ledger, pid = gite
    _, record = run(ledger, pid)
    entry_id = record["entries"][0]
    ledger.update_entry(entry_id, {"label": "Indemnisation vérifiée"})
    assert plan.undo_blockers(data, record) == ["Indemnisation vérifiée"]
