# Copyright © 2026 Vincent Fournet
"""Imports (delivery L2, 0.3.0): Airbnb and CSV readers, preview, apply, undo and the API.

Fictional data only: the two files of ``tests/fixtures`` are written by hand
with the columns of the real exports and invented codes, names and amounts.
"""
from __future__ import annotations

import base64
import time
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rental_cockpit.app import create_app
from rental_cockpit.config import Config
from rental_cockpit.engine.errors import RCError
from rental_cockpit.engine.imports import airbnb, generic, plan
from rental_cockpit.engine.indicators import compute, month_period
from rental_cockpit.engine.ledger import Ledger
from rental_cockpit.engine.schema import empty_registry
from rental_cockpit.security import hash_password

FIXTURES = Path(__file__).parent / "fixtures"
AIRBNB = (FIXTURES / "airbnb_fr.csv").read_bytes()
GENERIC = (FIXTURES / "generic_fr.csv").read_bytes()
TODAY = date(2026, 10, 31)
PASSWORD = "un-mot-de-passe-long"
GITE, STUDIO = "Gîte d'essai (annonce)", "Studio d'essai (annonce)"


def codes(items):
    return [i["code"] for i in items]


def by_ref(built):
    return {r["external_ref"]: r for r in built["rows"]}


def revenue(data, pid, year, month, mode):
    start, end = month_period(year, month)
    return compute(data, property_ids={pid}, start=start, end=end, mode=mode, lang="fr", today=TODAY)["indicators"]["revenue"]["value"]


@pytest.fixture
def two():
    data = empty_registry()
    ledger = Ledger(data, "1")
    gite = ledger.create_property({"name": "Gîte d'essai"})["property"]["id"]
    studio = ledger.create_property({"name": "Studio d'essai"})["property"]["id"]
    return data, ledger, gite, studio


def preview(data, content, options, today=TODAY, kind="airbnb", mapping=None, date_order="auto"):
    parsed = airbnb.parse(content) if kind == "airbnb" else generic.parse(content, mapping, date_order)
    return parsed, plan.build(data, parsed, options, today, plan.fingerprint(content))


def run(ledger, content, options, kind="airbnb", **kwargs):
    parsed, built = preview(ledger.data, content, options, kind=kind, **kwargs)
    meta = {"kind": parsed["kind"], "reader": parsed["reader"], "sha256": plan.fingerprint(content), "file_name": "essai.csv",
            "channel": options.get("channel")}
    summary = plan.apply(ledger, built, meta)["import"]
    assert set(summary) == {"id", "at", "kind", "reader", "file_name", "counts", "undone_at"}
    return built, ledger.data["imports"][summary["id"]]


def mapped(gite, studio, **extra):
    return {"property_map": {GITE: gite, STUDIO: studio}, **extra}


def airbnb_line(code, start, end, nights, amount, fee, gross, date_paid="", listing=GITE):
    return f'{date_paid},,Réservation,{code},08/25/2026,{start},{end},{nights},Voyageur,{listing},,,EUR,{amount},,{fee},,,{gross},,2026\n'


def edited(old: str, new: str) -> bytes:
    text = AIRBNB.decode("utf-8-sig")
    assert text.count(old) == 1
    return ("﻿" + text.replace(old, new)).encode()


# --------------------------------------------------------------------------- Airbnb reader


def test_airbnb_reader_takes_reservations_and_ignores_transfers():
    parsed = airbnb.parse(AIRBNB)
    assert parsed["errors"] == [] and parsed["date_order"] == "MDY"
    assert parsed["ignored"] == {"transfers": 1, "other": {"Ajustement de la résolution": 1}}
    assert parsed["listings"] == [GITE, STUDIO]
    rows = {r["external_ref"]: r for r in parsed["rows"]}
    first = rows["HMTEST0001"]
    assert (first["start"], first["end"], first["nights"]) == ("2026-09-28", "2026-10-04", 6)
    assert first["amounts"] == {"gross": 60000, "commission": 9000, "payout": 51000, "taxes_collected": None}
    assert (first["paid_on"], first["paid_amount"]) == ("2026-10-05", 51000)
    assert rows["HMTEST0002"]["paid_on"] == "" and rows["HMTEST0002"]["paid_amount"] is None
    assert codes(rows["HMTEST0004"]["errors"]) == ["imp_nights_mismatch"]


def test_airbnb_reader_refuses_another_export():
    english = b"Date,Type,Confirmation code,Start date,End date,Nights,Guest,Listing,Amount\n10/05/2026,Reservation,HM1,09/28/2026,10/04/2026,6,X,Y,510\n"
    parsed = airbnb.parse(english)
    assert codes(parsed["errors"]) == ["imp_airbnb_columns"] and parsed["rows"] == []
    assert "Code de confirmation" in plan.render(parsed["errors"][0], "fr")


def test_airbnb_reader_refuses_mixed_date_orders():
    header = AIRBNB.decode("utf-8-sig").splitlines()[0] + "\n"
    content = (header + airbnb_line("HMA", "09/28/2026", "10/04/2026", 6, "510", "90", "600")
               + airbnb_line("HMB", "13/10/2026", "15/10/2026", 2, "170", "30", "200")).encode()
    parsed = airbnb.parse(content)
    assert codes(parsed["errors"]) == ["imp_dates_mixed"] and parsed["rows"] == []


def test_airbnb_reader_merges_one_code_on_several_lines_and_refuses_conflicts():
    header = AIRBNB.decode("utf-8-sig").splitlines()[0] + "\n"
    content = (header + airbnb_line("HMA", "09/28/2026", "10/04/2026", 6, "400", "60", "460")
               + airbnb_line("HMA", "09/28/2026", "10/04/2026", 6, "110", "30", "140")
               + airbnb_line("HMB", "10/13/2026", "10/15/2026", 2, "170", "30", "200")
               + airbnb_line("HMB", "10/14/2026", "10/16/2026", 2, "170", "30", "200")).encode()
    rows = {r["external_ref"]: r for r in airbnb.parse(content)["rows"]}
    assert rows["HMA"]["lines"] == [2, 3] and rows["HMA"]["amounts"]["gross"] == 60000
    assert codes(rows["HMB"]["errors"]) == ["imp_code_conflict"]


# --------------------------------------------------------------------------- preview


def test_preview_says_what_would_happen_without_writing(two):
    data, _, gite, studio = two
    before = repr(data)
    _, built = preview(data, AIRBNB, mapped(gite, studio))
    assert repr(data) == before
    rows = by_ref(built)
    assert {ref: r["status"] for ref, r in rows.items()} == {
        "HMTEST0001": "new", "HMTEST0002": "new", "HMTEST0003": "new", "HMTEST0004": "error"}
    assert rows["HMTEST0001"]["payout"] == {"date": "2026-10-05", "amount": 51000}
    assert rows["HMTEST0002"]["payout"] is None
    assert rows["HMTEST0003"]["property_id"] == studio
    assert rows["HMTEST0001"]["guest_label"] == ""  # guests' names are only kept when asked
    assert rows["HMTEST0001"]["choices"] == ["import", "skip"] and rows["HMTEST0004"]["choices"] == []
    counts = built["counts"]
    assert (counts["new"], counts["error"], counts["to_write"], counts["payouts"]) == (3, 1, 3, 2)
    assert built["can_apply"] is True
    assert codes(built["notices"]) == ["imp_ignored_transfers", "imp_ignored_other"]


def test_preview_keeps_names_only_when_asked(two):
    data, _, gite, studio = two
    _, built = preview(data, AIRBNB, mapped(gite, studio, keep_names=True))
    assert by_ref(built)["HMTEST0001"]["guest_label"] == "Voyageur Test"


def test_listing_without_property_is_not_imported(two):
    data, _, gite, _ = two
    _, built = preview(data, AIRBNB, {"property_map": {GITE: gite, STUDIO: ""}})
    assert by_ref(built)["HMTEST0003"]["status"] == "unmapped"
    assert built["counts"]["to_write"] == 2


def test_future_payout_and_payouts_turned_off_are_not_recorded(two):
    data, _, gite, studio = two
    _, early = preview(data, AIRBNB, mapped(gite, studio), today=date(2026, 10, 10))
    assert by_ref(early)["HMTEST0003"]["payout"] is None  # paid on 16 October, not yet
    _, off = preview(data, AIRBNB, mapped(gite, studio, create_payouts=False))
    assert off["counts"]["payouts"] == 0


def test_arrival_before_activity_start_is_skipped_unless_chosen(two):
    data, ledger, gite, studio = two
    ledger.update_property(gite, {"activity_start": "2026-10-01"})
    _, built = preview(data, AIRBNB, mapped(gite, studio))
    first = by_ref(built)["HMTEST0001"]
    assert first["decision"] == "skip" and "imp_before_activity" in codes(first["warnings"])
    warning = next(w for w in first["warnings"] if w["code"] == "imp_before_activity")
    assert plan.render(warning, "fr") == "arrivée avant le début d'activité du bien (1 oct. 2026)"
    assert plan.render(warning, "en") == "arrival before the property's activity start (1 Oct 2026)"
    _, forced = preview(data, AIRBNB, mapped(gite, studio, decisions={first["key"]: "import"}))
    assert by_ref(forced)["HMTEST0001"]["decision"] == "import"


def test_overlaps_with_the_registry_and_inside_the_file(two):
    data, ledger, gite, studio = two
    ledger.create_stay({"property_id": gite, "start": "2026-10-01", "end": "2026-10-03", "guest_label": "Famille Test"})
    ledger.update_property(gite, {"unavailable": [{"start": "2026-09-27", "end": "2026-09-29", "label": "Travaux"}]})
    _, built = preview(data, AIRBNB, mapped(gite, studio))
    assert codes(by_ref(built)["HMTEST0001"]["warnings"]) == ["imp_overlap", "imp_unavailable"]
    content = "Arrivée;Départ;Montant brut\n01/11/2026;05/11/2026;400\n03/11/2026;06/11/2026;300\n".encode()
    _, inside = preview(data, content, {"property_id": gite}, kind="csv")
    second = inside["rows"][1]
    assert second["status"] == "new" and codes(second["warnings"]) == ["imp_overlap_file"]


def test_dates_outside_the_accepted_years_are_errors(two):
    data, _, gite, _ = two
    content = "Arrivée;Départ\n01/11/2150;05/11/2150\n01/11/1999;03/11/1999\n".encode()
    _, built = preview(data, content, {"property_id": gite}, kind="csv", date_order="DMY")
    assert [codes(r["errors"]) for r in built["rows"]] == [["imp_bad_dates"], ["imp_bad_dates"]]


def test_large_file_is_checked_and_written_quickly(two):
    data, ledger, gite, _ = two
    lines = ["Arrivée;Départ;Référence;Montant brut;Commission"]
    day = date(2020, 1, 1)
    for n in range(3000):
        start = day.toordinal() + 2 * n
        lines.append(f"{date.fromordinal(start):%d/%m/%Y};{date.fromordinal(start + 2):%d/%m/%Y};R{n:05d};300;45")
    content = ("\n".join(lines) + "\n").encode()
    begin = time.perf_counter()
    _, record = run(ledger, content, {"property_id": gite}, kind="csv")
    _, again = preview(data, content, {"property_id": gite}, kind="csv")
    assert record["counts"]["created"] == 3000 and again["counts"]["same"] == 3000
    assert time.perf_counter() - begin < 10


def test_negative_amount_is_an_error(two):
    data, _, gite, _ = two
    content = "Arrivée;Départ;Montant brut\n01/11/2026;05/11/2026;-50\n".encode()
    _, built = preview(data, content, {"property_id": gite}, kind="csv")
    assert built["rows"][0]["status"] == "error" and codes(built["rows"][0]["errors"]) == ["imp_negative"]
    assert built["can_apply"] is False


# --------------------------------------------------------------------------- apply, re-import, duplicates


def test_apply_creates_stays_and_payouts_that_feed_the_figures(two):
    data, ledger, gite, studio = two
    journal = len(data.get("audit", []))
    _, record = run(ledger, AIRBNB, mapped(gite, studio))
    # One line in the journal for the whole file, not one per stay or payout.
    assert [e["action"] for e in data["audit"][journal:]] == ["import.apply"]
    assert ledger.bulk is False
    assert record["counts"] == {"created": 3, "updated": 0, "completed": 0, "payouts": 2}
    stays = {s["external_ref"]: s for s in data["stays"].values()}
    assert set(stays) == {"HMTEST0001", "HMTEST0002", "HMTEST0003"}
    first = stays["HMTEST0001"]
    assert (first["source"], first["channel"], first["origin_import"]) == ("airbnb", "airbnb", record["id"])
    payments = list(data["payments"].values())
    assert {p["method"] for p in payments} == {"Import Airbnb"}
    assert {p["origin"]["id"] for p in payments} == {record["id"]}
    # Same figures as a stay entered by hand: 3 of the 6 nights in September, the payout in October.
    assert revenue(data, gite, 2026, 9, "activity") == 30000
    assert revenue(data, gite, 2026, 9, "invoice") == 60000
    assert revenue(data, gite, 2026, 10, "cash") == 51000


def test_same_file_again_changes_nothing(two):
    data, ledger, gite, studio = two
    run(ledger, AIRBNB, mapped(gite, studio))
    _, again = preview(data, AIRBNB, mapped(gite, studio))
    rows = by_ref(again)
    assert {r["status"] for ref, r in rows.items() if ref != "HMTEST0004"} == {"same"}
    assert "imp_payout_exists" in codes(rows["HMTEST0001"]["warnings"])
    assert again["can_apply"] is False
    assert "imp_file_known" in codes(again["notices"])
    with pytest.raises(RCError) as refused:
        plan.apply(ledger, again, {"kind": "airbnb", "reader": "airbnb-fr-1", "sha256": "x"})
    assert refused.value.code == "import_nothing"


def test_modified_file_updates_the_stay_it_imported(two):
    data, ledger, gite, studio = two
    run(ledger, AIRBNB, mapped(gite, studio))
    changed = edited("HMTEST0002,10/20/2026,12/20/2026,12/23/2026,3,Autre Voyageur,Gîte d'essai (annonce),,,EUR,255.00,,45.00,,40.00,300.00",
                     "HMTEST0002,10/20/2026,12/20/2026,12/23/2026,3,Autre Voyageur,Gîte d'essai (annonce),,,EUR,275.00,,45.00,,40.00,320.00")
    _, built = preview(data, changed, mapped(gite, studio))
    row = by_ref(built)["HMTEST0002"]
    assert row["status"] == "update"
    assert [(c["field"], c["before"], c["after"]) for c in row["changes"]] == [("gross", 30000, 32000), ("payout", 25500, 27500)]
    stay = data["stays"][row["stay_id"]]
    revision = stay["revision"]
    _, record = run(ledger, changed, mapped(gite, studio))
    assert record["counts"]["updated"] == 1 and record["counts"]["created"] == 0
    assert stay["amounts"]["gross"] == 32000 and stay["revision"] == revision + 1


def test_lower_amount_than_already_received_is_flagged(two):
    data, ledger, gite, studio = two
    run(ledger, AIRBNB, mapped(gite, studio))
    lower = edited("EUR,510.00,,90.00,,60.00,600.00", "EUR,500.00,,90.00,,60.00,590.00")
    _, built = preview(data, lower, mapped(gite, studio))
    row = by_ref(built)["HMTEST0001"]
    assert row["status"] == "update" and "imp_received_above" in codes(row["warnings"])
    assert "510,00" in plan.render(next(w for w in row["warnings"] if w["code"] == "imp_received_above"), "fr")


def test_stay_entered_by_hand_is_completed_not_doubled(two):
    data, ledger, gite, studio = two
    hand = ledger.create_stay({"property_id": gite, "start": "2026-09-28", "end": "2026-10-04", "guest_label": "Famille Test",
                               "amounts": {"gross": "600"}})["stay"]
    _, built = preview(data, AIRBNB, mapped(gite, studio))
    row = by_ref(built)["HMTEST0001"]
    assert (row["status"], row["decision"], row["stay_id"], row["twin_label"]) == ("duplicate", "complete", hand["id"], "Famille Test")
    assert row["choices"] == ["complete", "import", "skip"]
    _, record = run(ledger, AIRBNB, mapped(gite, studio))
    assert record["counts"]["completed"] == 1 and record["counts"]["created"] == 2
    stay = data["stays"][hand["id"]]
    assert stay["external_ref"] == "HMTEST0001" and stay["guest_label"] == "Famille Test"
    assert stay["amounts"]["gross"] == 60000 and stay["amounts"]["commission"] == 9000
    assert len([s for s in data["stays"].values() if s["start"] == "2026-09-28"]) == 1


def test_duplicate_that_brings_nothing_is_skipped(two):
    data, ledger, gite, studio = two
    ledger.create_stay({"property_id": gite, "start": "2026-12-20", "end": "2026-12-23", "external_ref": "MAIN-1",
                        "amounts": {"gross": "300", "commission": "45", "payout": "255"}})
    _, built = preview(data, AIRBNB, mapped(gite, studio))
    row = by_ref(built)["HMTEST0002"]
    assert (row["status"], row["decision"], row["changes"], row["choices"]) == ("duplicate", "skip", [], ["import", "skip"])
    assert built["counts"]["to_write"] == 2


def test_duplicate_can_be_imported_as_a_new_stay_or_skipped(two):
    data, ledger, gite, studio = two
    ledger.create_stay({"property_id": gite, "start": "2026-09-28", "end": "2026-10-04"})
    key = by_ref(preview(data, AIRBNB, mapped(gite, studio))[1])["HMTEST0001"]["key"]
    _, skipped = preview(data, AIRBNB, mapped(gite, studio, decisions={key: "skip"}))
    assert by_ref(skipped)["HMTEST0001"]["decision"] == "skip"
    run(ledger, AIRBNB, mapped(gite, studio, decisions={key: "import"}))
    assert len([s for s in data["stays"].values() if s["start"] == "2026-09-28"]) == 2


def test_completing_never_records_more_than_expected(two):
    data, ledger, gite, studio = two
    ledger.create_stay({"property_id": gite, "start": "2026-09-28", "end": "2026-10-04", "amounts": {"gross": "580", "commission": "90"}})
    _, built = preview(data, AIRBNB, mapped(gite, studio))
    row = by_ref(built)["HMTEST0001"]
    assert row["payout"] is None and codes(row["warnings"]) == ["imp_twin_differs", "imp_payout_too_high"]
    assert [c["field"] for c in row["changes"]] == ["external_ref"]  # the amounts typed by hand are kept
    assert "montant brut" in plan.render(row["warnings"][0], "fr")


def test_reference_on_another_property_is_not_imported_by_default(two):
    data, ledger, gite, studio = two
    run(ledger, AIRBNB, {"property_map": {GITE: studio, STUDIO: studio}})  # wrong property the first time
    _, built = preview(data, AIRBNB, mapped(gite, studio))
    row = by_ref(built)["HMTEST0001"]
    assert (row["status"], row["decision"], row["stay_id"]) == ("duplicate", "skip", None)
    assert "imp_ref_elsewhere" in codes(row["warnings"]) and row["choices"] == ["import", "skip"]


def test_cancelled_stay_is_left_alone(two):
    data, ledger, gite, studio = two
    run(ledger, AIRBNB, mapped(gite, studio))
    stay = next(s for s in data["stays"].values() if s["external_ref"] == "HMTEST0002")
    ledger.cancel_stay(stay["id"], {"retained": "0"})
    changed = edited("EUR,255.00,,45.00,,40.00,300.00", "EUR,275.00,,45.00,,40.00,320.00")
    _, built = preview(data, changed, mapped(gite, studio))
    row = by_ref(built)["HMTEST0002"]
    assert (row["status"], row["decision"], row["choices"]) == ("same", "skip", [])
    assert codes(row["warnings"]) == ["imp_cancelled_kept"]


# --------------------------------------------------------------------------- undo


def test_undo_removes_the_last_import(two):
    data, ledger, gite, studio = two
    _, record = run(ledger, AIRBNB, mapped(gite, studio))
    plan.undo(ledger, record["id"])
    assert data["stays"] == {} and data["payments"] == {}
    assert data["imports"][record["id"]]["undone_at"] and plan.last_import(data) is None
    with pytest.raises(RCError) as twice:
        plan.undo(ledger, record["id"])
    assert twice.value.code == "import_not_last"


def test_undo_puts_back_what_an_update_changed(two):
    data, ledger, gite, studio = two
    run(ledger, AIRBNB, mapped(gite, studio))
    changed = edited("EUR,255.00,,45.00,,40.00,300.00", "EUR,275.00,,45.00,,40.00,320.00")
    _, record = run(ledger, changed, mapped(gite, studio))
    stay = next(s for s in data["stays"].values() if s["external_ref"] == "HMTEST0002")
    assert stay["amounts"]["gross"] == 32000
    plan.undo(ledger, record["id"])
    assert stay["amounts"]["gross"] == 30000 and len(data["stays"]) == 3


def test_undoing_two_imports_in_a_row(two):
    data, ledger, gite, studio = two
    ledger.create_stay({"property_id": gite, "start": "2026-12-20", "end": "2026-12-23", "amounts": {"gross": "300"}})
    _, first = run(ledger, AIRBNB, mapped(gite, studio))  # creates two stays, completes the one typed by hand
    changed = edited("EUR,255.00,,45.00,,40.00,300.00", "EUR,275.00,,45.00,,40.00,320.00")
    _, second = run(ledger, changed, mapped(gite, studio))
    plan.undo(ledger, second["id"])
    assert plan.undo_blockers(data, first) == []
    plan.undo(ledger, first["id"])
    hand = next(iter(data["stays"].values()))
    assert len(data["stays"]) == 1 and hand["external_ref"] == "" and hand["amounts"]["gross"] == 30000
    assert hand["amounts"]["commission"] is None and data["payments"] == {}


def test_undo_is_refused_once_a_stay_was_changed(two):
    data, ledger, gite, studio = two
    _, record = run(ledger, AIRBNB, mapped(gite, studio))
    stay = next(s for s in data["stays"].values() if s["external_ref"] == "HMTEST0002")
    ledger.update_stay(stay["id"], {"guests": 3})
    assert plan.undo_blockers(data, record) == ["HMTEST0002"]
    with pytest.raises(RCError) as refused:
        plan.undo(ledger, record["id"])
    assert refused.value.code == "import_changed_since"
    assert len(data["stays"]) == 3


def test_undo_is_refused_when_a_payment_was_added_by_hand(two):
    data, ledger, gite, studio = two
    _, record = run(ledger, AIRBNB, mapped(gite, studio))
    stay = next(s for s in data["stays"].values() if s["external_ref"] == "HMTEST0002")
    ledger.create_payment({"property_id": gite, "direction": "in", "date": "2026-10-30", "amount": "100",
                           "links": [{"type": "stay", "id": stay["id"], "amount": "100"}]})
    assert plan.undo_blockers(data, record) == ["HMTEST0002"]


# --------------------------------------------------------------------------- generic CSV


def test_generic_csv_suggests_columns_and_reads_french_numbers():
    parsed = generic.parse(GENERIC)
    assert parsed["encoding"] == "cp1252" and parsed["delimiter"] == ";"
    assert "imp_encoding_fallback" in codes(parsed["warnings"])
    assert parsed["mapping"] == {
        "start": "Arrivée", "end": "Départ", "external_ref": "Référence", "guest_label": "Client",
        "guests": "Nombre de voyageurs", "gross": "Montant brut", "commission": "Commission", "payout": "Montant net",
        "paid_on": "Date de paiement"}
    assert parsed["date_order"] == "DMY"
    rows = {r["external_ref"]: r for r in parsed["rows"]}
    assert rows["BK-001"]["amounts"] == {"gross": 60000, "commission": 9000, "payout": 51000, "taxes_collected": None}
    assert (rows["BK-001"]["start"], rows["BK-001"]["paid_on"], rows["BK-001"]["guests"]) == ("2026-09-28", "2026-10-05", 2)
    assert codes(rows["BK-003"]["errors"]) == ["imp_dates_order"]


def test_generic_csv_start_and_nights_with_a_chosen_date_order():
    content = b"Debut,Nuits,Montant\n05/11/2026,3,300\n"
    auto = generic.parse(content)
    assert auto["rows"][0]["end"] == "2026-11-08" and "imp_dates_ambiguous" in codes(auto["warnings"])
    american = generic.parse(content, date_order="MDY")
    assert (american["rows"][0]["start"], american["rows"][0]["end"]) == ("2026-05-11", "2026-05-14")


def test_generic_csv_needs_the_arrival_and_the_departure_or_nights():
    parsed = generic.parse(GENERIC, {"start": "Arrivée", "gross": "Montant brut"})
    assert codes(parsed["errors"]) == ["imp_csv_mapping"] and parsed["rows"] == []


def test_commission_rate_when_the_file_has_no_commission(two):
    data, ledger, gite, _ = two
    content = "Arrivée;Départ;Montant brut\n01/11/2026;04/11/2026;300\n10/11/2026;12/11/2026;333,33\n".encode()
    _, without = preview(data, content, {"property_id": gite}, kind="csv")
    assert without["rows"][0]["amounts"]["commission"] is None
    _, built = preview(data, content, {"property_id": gite, "commission_rate": "3,5"}, kind="csv")
    assert [r["amounts"]["commission"] for r in built["rows"]] == [1050, 1167]  # 11.67 € rounded half up from 11.666…
    assert "imp_commission_rate" in codes(built["rows"][0]["warnings"])
    assert [plan.commission_rate(v) for v in ("120", "abc", "NaN", "Infinity", "-1")] == [None] * 5
    _, record = run(ledger, content, {"property_id": gite, "commission_rate": "15", "channel": "booking"}, kind="csv")
    stay = data["stays"][record["created"][0]["id"]]
    assert (stay["source"], stay["channel"], stay["amounts"]["commission"]) == ("csv", "booking", 4500)


def test_generic_csv_reference_twice_is_an_error():
    content = b"Arrivee,Depart,Reference\n01/11/2026,04/11/2026,R1\n10/11/2026,12/11/2026,R1\n"
    rows = generic.parse(content)["rows"]
    assert rows[0]["errors"] == [] and codes(rows[1]["errors"]) == ["imp_ref_twice"]


# --------------------------------------------------------------------------- API


@pytest.fixture
def client(tmp_path):
    client = TestClient(create_app(Config(data_dir=tmp_path)))
    client.app.state.services.today = lambda: TODAY
    token = client.get("/api/session").json()["csrf"]
    response = client.post("/api/auth/setup", json={"username": "admin", "password": PASSWORD, "confirm": PASSWORD},
                           headers={"X-CSRF-Token": token})
    client.headers["X-CSRF-Token"] = response.json()["csrf"]
    client.post("/api/start", json={"choice": "own_data"})
    return client


def body(content: bytes, **extra):
    return {"content": base64.b64encode(content).decode(), "file_name": "essai.csv", **extra}


def properties(client):
    gite = client.post("/api/properties", json={"name": "Gîte d'essai", "op_id": "op-p1"}).json()["property"]["id"]
    studio = client.post("/api/properties", json={"name": "Studio d'essai", "op_id": "op-p2"}).json()["property"]["id"]
    return gite, studio


def test_api_preview_apply_remember_and_undo(client):
    gite, studio = properties(client)
    first = client.post("/api/imports/preview", json=body(AIRBNB, kind="airbnb"), params={"lang": "fr"}).json()
    assert first["property_map"] == {GITE: "", STUDIO: ""} and first["can_apply"] is False
    assert {r["status"] for r in first["rows"]} == {"unmapped", "error"}
    assert {p["id"] for p in first["properties"]} == {gite, studio}
    assert first["notices"][0].startswith("1 ligne(s) « Payout » ignorée(s)")
    options = {"property_map": {GITE: gite, STUDIO: studio}}
    ready = client.post("/api/imports/preview", json=body(AIRBNB, kind="airbnb", options=options), params={"lang": "fr"}).json()
    assert ready["can_apply"] is True and ready["counts"]["to_write"] == 3
    error = next(r for r in ready["rows"] if r["status"] == "error")
    assert error["errors"] == ["2 nuits indiquées, 3 d'après les dates"] and error["status_label"] == "Erreur"
    stale = client.post("/api/imports/apply", json=body(AIRBNB, kind="airbnb", options=options, op_id="op-old",
                                                        expect={"to_write": 2, "payouts": 2}))
    assert stale.status_code == 409 and stale.json()["code"] == "preview_stale"
    expect = {k: ready["counts"][k] for k in ("to_write", "payouts")}
    applied = client.post("/api/imports/apply", json=body(AIRBNB, kind="airbnb", options=options, op_id="op-imp", expect=expect))
    assert applied.status_code == 200, applied.text
    record = applied.json()["import"]
    assert record["counts"]["created"] == 3
    again = client.post("/api/imports/apply", json=body(AIRBNB, kind="airbnb", options=options, op_id="op-imp")).json()
    assert again["replayed"] is True
    stays = client.get("/api/stays", params={"view": "all"}).json()["stays"]
    assert len(stays) == 3
    detail = client.get(f"/api/stays/{stays[0]['id']}").json()
    assert detail["source"] == "airbnb" and detail["imported"]["file_name"] == "essai.csv"
    # The listings are remembered: the next preview needs no choice and finds everything up to date.
    later = client.post("/api/imports/preview", json=body(AIRBNB, kind="airbnb")).json()
    assert later["property_map"] == {GITE: gite, STUDIO: studio}
    assert later["can_apply"] is False and later["counts"]["same"] == 3
    history = client.get("/api/imports").json()
    assert history["last_id"] == record["id"] and history["blockers"] == []
    assert history["imports"][0]["file_name"] == "essai.csv"
    undone = client.post(f"/api/imports/{record['id']}/undo", json={"op_id": "op-undo"})
    assert undone.status_code == 200, undone.text
    assert client.get("/api/stays", params={"view": "all"}).json()["stays"] == []


def test_api_refuses_to_apply_a_file_with_nothing_new(client):
    gite, studio = properties(client)
    options = {"property_map": {GITE: gite, STUDIO: studio}}
    client.post("/api/imports/apply", json=body(AIRBNB, kind="airbnb", options=options, op_id="op-1"))
    refused = client.post("/api/imports/apply", json=body(AIRBNB, kind="airbnb", options=options, op_id="op-2"), params={"lang": "fr"})
    assert refused.status_code == 400 and refused.json()["code"] == "import_nothing"


def test_api_undo_refused_after_a_change(client):
    gite, studio = properties(client)
    options = {"property_map": {GITE: gite, STUDIO: studio}}
    record = client.post("/api/imports/apply", json=body(AIRBNB, kind="airbnb", options=options, op_id="op-1")).json()["import"]
    stay = next(s for s in client.get("/api/stays", params={"view": "all"}).json()["stays"] if s["external_ref"] == "HMTEST0002")
    client.patch(f"/api/stays/{stay['id']}", json={"guests": 3, "op_id": "op-2"})
    assert client.get("/api/imports").json()["blockers"] == ["HMTEST0002"]
    refused = client.post(f"/api/imports/{record['id']}/undo", json={"op_id": "op-3"}, params={"lang": "fr"})
    assert refused.status_code == 400 and "HMTEST0002" in refused.json()["message"]


def test_api_csv_mapping_rate_and_channel_are_remembered(client):
    gite, _ = properties(client)
    content = "Arrivée;Départ;Montant brut;Dossier\n01/11/2026;04/11/2026;300;X-1\n".encode()
    first = client.post("/api/imports/preview", json=body(content, kind="csv")).json()
    assert first["mapping"] == {"start": "Arrivée", "end": "Départ", "gross": "Montant brut"}  # « Dossier » is not guessed
    assert first["samples"] == {"Arrivée": "01/11/2026", "Départ": "04/11/2026", "Montant brut": "300", "Dossier": "X-1"}
    assert first["property_map"] == {} and first["property_id"] == ""
    options = {"property_id": gite, "mapping": {**first["mapping"], "external_ref": "Dossier"}, "commission_rate": "15", "channel": "booking"}
    applied = client.post("/api/imports/apply", json=body(content, kind="csv", options=options, op_id="op-1"))
    assert applied.status_code == 200, applied.text
    other = "Arrivée;Départ;Montant brut;Dossier\n10/11/2026;12/11/2026;200;X-2\n".encode()
    later = client.post("/api/imports/preview", json=body(other, kind="csv", options={"property_id": gite})).json()
    assert later["mapping"]["external_ref"] == "Dossier"
    assert (later["commission_rate"], later["channel"]) == ("15", "booking")
    assert later["rows"][0]["amounts"]["commission"] == 3000


def test_api_english_airbnb_file_is_explained_not_imported(client):
    properties(client)
    english = b"Date,Type,Confirmation code,Start date,End date,Nights,Guest,Listing,Amount\n"
    result = client.post("/api/imports/preview", json=body(english, kind="airbnb"), params={"lang": "fr"}).json()
    assert result["can_apply"] is False and "import CSV générique" in result["errors"][0]


def test_api_rejects_unreadable_and_oversized_files(client):
    properties(client)
    bad = client.post("/api/imports/preview", json={"content": "pas du base64 !", "kind": "airbnb"})
    assert bad.status_code == 400 and bad.json()["code"] == "import_file"
    empty = client.post("/api/imports/preview", json={"content": "", "kind": "airbnb"})
    assert empty.json()["code"] == "import_file"
    huge = client.post("/api/imports/preview", content=b"x" * (plan_max() + 1), headers={"Content-Type": "application/json"})
    assert huge.status_code == 413 and huge.json()["code"] == "upload_too_large"
    binary = client.post("/api/imports/preview", json=body(b"\x00\x01\x02PK\x03\x04", kind="csv"))
    assert binary.status_code == 400 and binary.json()["code"] == "import_file"


def test_api_ignores_malformed_choices(client):
    gite, _ = properties(client)
    content = "Arrivée;Départ;Montant brut\n01/11/2026;04/11/2026;300\n".encode()
    odd = {"property_id": gite, "decisions": ["skip"], "mapping": "Arrivée", "property_map": None, "commission_rate": "NaN"}
    result = client.post("/api/imports/preview", json=body(content, kind="csv", options=odd))
    assert result.status_code == 200, result.text
    assert result.json()["can_apply"] is True and result.json()["commission_rate"] == ""
    assert client.post("/api/imports/preview", json=body(content, kind="csv", options="x")).status_code == 200


def plan_max() -> int:
    from rental_cockpit.import_routes import MAX_BODY
    return MAX_BODY


def test_api_imports_need_an_administrator_and_the_csrf_token(client):
    gite, _ = properties(client)
    db = client.app.state.services.db
    with db.transaction() as conn:
        conn.execute("INSERT INTO users(username, display_name, password_hash, role, created_at, updated_at) VALUES ('lecteur', '', ?, 'reader', '2026-10-31', '2026-10-31')",
                     (hash_password(PASSWORD),))
        uid = conn.execute("SELECT id FROM users WHERE username = 'lecteur'").fetchone()[0]
        conn.execute("INSERT INTO grants(user_id, property_id, documents) VALUES (?, ?, 0)", (uid, gite))
    reader = TestClient(client.app)
    token = reader.get("/api/session").json()["csrf"]
    reader.headers["X-CSRF-Token"] = reader.post("/api/auth/login", json={"username": "lecteur", "password": PASSWORD},
                                                 headers={"X-CSRF-Token": token}).json()["csrf"]
    assert reader.post("/api/imports/preview", json=body(AIRBNB, kind="airbnb")).status_code == 403
    assert reader.get("/api/imports").status_code == 403
    del client.headers["X-CSRF-Token"]
    refused = client.post("/api/imports/preview", json=body(AIRBNB, kind="airbnb"))
    assert refused.status_code == 403 and refused.json()["code"] == "csrf_failed"


def test_api_import_into_the_demo_stays_in_the_demo(client):
    client.post("/api/start", json={"choice": "demo"})
    demo_props = client.get("/api/overview", params={"dataset": "demo", "start": "2026-10-01", "end": "2026-11-01"}).json()["properties"]
    target = demo_props[0]["id"]
    content = "Arrivée;Départ;Montant brut\n01/12/2027;04/12/2027;300\n".encode()
    applied = client.post("/api/imports/apply", json=body(content, kind="csv", dataset="demo", options={"property_id": target}, op_id="op-d"))
    assert applied.status_code == 200, applied.text
    assert client.get("/api/stays", params={"view": "all"}).json()["stays"] == []
    demo = client.get("/api/stays", params={"dataset": "demo", "view": "all"}).json()["stays"]
    assert any(s["start"] == "2027-12-01" for s in demo)
