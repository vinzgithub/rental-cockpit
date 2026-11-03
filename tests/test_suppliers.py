# Copyright © 2026 Vincent Fournet
"""Suppliers (delivery L4, 0.5.0): detailed invoices, split between stays, reconciliation and the « Prestataires » API.

Fictional data only. The invoice of 150 € = 100 cleaning + 4 × 10 linen + 10
travel is the documented example: one expense of 150 €, never 300 €.
"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from rental_cockpit.app import create_app
from rental_cockpit.config import Config
from rental_cockpit.engine import entries as entry_views
from rental_cockpit.engine import stays as stay_views
from rental_cockpit.engine import suppliers as supplier_views
from rental_cockpit.engine.errors import RCError
from rental_cockpit.engine.indicators import compute, month_period
from rental_cockpit.engine.ledger import Ledger
from rental_cockpit.engine.schema import empty_registry
from rental_cockpit.security import hash_password

TODAY = date(2026, 11, 1)
PASSWORD = "un-mot-de-passe-long"
LINES = [{"id": "l1", "kind": "cleaning", "label": "Ménage", "amount": "100", "intervention_date": "2026-10-04"},
         {"id": "l2", "kind": "linen", "label": "Linge", "quantity": "4", "unit": "set", "unit_price": "10", "intervention_date": "2026-10-04"},
         {"id": "l3", "kind": "travel", "label": "Déplacement", "amount": "10", "intervention_date": "2026-10-04"}]


def expenses(data, pid, mode="activity"):
    start, end = month_period(2026, 10)
    return compute(data, property_ids={pid}, start=start, end=end, mode=mode, lang="fr", today=TODAY)["indicators"]["operating_expenses"]["value"]


@pytest.fixture
def setup():
    data = empty_registry()
    ledger = Ledger(data, "1")
    pid = ledger.create_property({"name": "Gîte d'essai"})["property"]["id"]
    sup = ledger.create_supplier({"name": "Ménage Essai", "role": "Ménage et linge", "categories": ["cleaning", "linen"],
                                  "rates": [{"kind": "cleaning", "unit": "hour", "unit_price": "25", "label": "Ménage à l'heure"},
                                            {"kind": "linen", "unit": "set", "unit_price": "10"}]})["supplier"]["id"]
    a = ledger.create_stay({"property_id": pid, "start": "2026-09-28", "end": "2026-10-04", "guest_label": "Séjour A",
                            "amounts": {"gross": "600", "commission": "90"}})["stay"]["id"]
    b = ledger.create_stay({"property_id": pid, "start": "2026-10-10", "end": "2026-10-13", "guest_label": "Séjour B",
                            "amounts": {"gross": "300", "commission": "45"}})["stay"]["id"]
    return data, ledger, pid, sup, a, b


def invoice(ledger, pid, sup, **extra):
    return ledger.create_entry({"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Facture Ménage Essai F-018",
                                "invoice_number": "F-018", "amount": "150", "date": "2026-10-20", "supplier_id": sup,
                                "lines": LINES, "payment_declared": "unpaid", **extra})["entry"]


# --------------------------------------------------------------------------- engine


def test_detailed_invoice_is_one_expense(setup):
    data, ledger, pid, sup, *_ = setup
    entry = invoice(ledger, pid, sup)
    assert [line["amount"] for line in entry["lines"]] == [10000, 4000, 1000]
    assert expenses(data, pid) == 15000 + 4500 + 4500  # the invoice once, plus the October share of each commission
    # Editing the invoice keeps its lines (stored in cents) and their identifiers.
    kept = ledger.update_entry(entry["id"], {"label": "Facture F-018 (corrigée)", "amount": "150"})["entry"]
    assert [(line["id"], line["amount"]) for line in kept["lines"]] == [("l1", 10000), ("l2", 4000), ("l3", 1000)]
    with pytest.raises(RCError) as wrong:
        ledger.create_entry({"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "x", "amount": "160",
                             "date": "2026-10-20", "lines": LINES})
    assert wrong.value.code == "lines_total_mismatch"


def test_split_between_stays_adds_no_charge(setup):
    data, ledger, pid, sup, a, b = setup
    entry = invoice(ledger, pid, sup)
    before = expenses(data, pid)
    ledger.set_allocations(entry["id"], {"allocations": [
        {"line_id": "l1", "stay_id": a, "amount": "60"}, {"line_id": "l2", "stay_id": a, "amount": "24"}, {"line_id": "l3", "stay_id": a, "amount": "6"},
        {"line_id": "l1", "stay_id": b, "amount": "40"}, {"line_id": "l2", "stay_id": b, "amount": "16"}, {"line_id": "l3", "stay_id": b, "amount": "4"}]})
    assert expenses(data, pid) == before
    rows = supplier_views.split_rows(data, data["entries"][entry["id"]], "fr")
    assert [(r["kind_label"], r["allocated"], r["remaining"]) for r in rows] == [("Ménage", 10000, 0), ("Linge", 4000, 0), ("Déplacement", 1000, 0)]
    stay_a = stay_views.detail(data, data["stays"][a], TODAY, "fr")
    assert (stay_a["costs_total"], stay_a["margin"]) == (9000, 51000 - 9000)
    assert [c["detail"] for c in stay_a["costs"]] == ["Ménage", "Linge", "Déplacement"]
    assert stay_views.detail(data, data["stays"][b], TODAY, "fr")["costs_total"] == 6000
    with pytest.raises(RCError) as over:
        ledger.set_allocations(entry["id"], {"allocations": [{"line_id": "l3", "stay_id": a, "amount": "11"}]})
    assert over.value.code == "allocation_exceeds"
    # A service already split cannot leave the invoice behind the person's back.
    kept = [line for line in LINES if line["id"] != "l3"]
    with pytest.raises(RCError) as removed:
        ledger.update_entry(entry["id"], {"amount": "140", "lines": kept})
    assert removed.value.code == "allocation_line_removed" and removed.value.params["what"] == "Déplacement"
    # A line without a label is named by its kind, in the reader's language.
    bare = invoice(ledger, pid, sup, lines=[{**line, "label": ""} for line in LINES])
    ledger.set_allocations(bare["id"], {"allocations": [{"line_id": "l3", "stay_id": a, "amount": "10"}]})
    with pytest.raises(RCError) as unnamed:
        ledger.update_entry(bare["id"], {"amount": "140", "lines": [{**line, "label": ""} for line in kept]})
    assert "« Déplacement »" in unnamed.value.message("fr") and '"Travel"' in unnamed.value.message("en")


def test_part_left_to_split_is_listed_to_check(setup):
    data, ledger, pid, sup, a, _ = setup
    entry = invoice(ledger, pid, sup)
    ledger.set_allocations(entry["id"], {"allocations": [{"line_id": "l1", "stay_id": a, "amount": "100"},
                                                         {"line_id": "l2", "stay_id": a, "amount": "40"}]})
    start, end = month_period(2026, 10)
    checks = compute(data, property_ids={pid}, start=start, end=end, lang="fr", today=TODAY)["to_check"]
    item = next(c for c in checks if c["kind"] == "allocations_incomplete")
    assert item["amount"] == 1000 and "10,00" in item["title"]


def test_suggested_stay_for_an_intervention(setup):
    data, _, pid, _, a, b = setup
    assert supplier_views.suggested_stay(data, pid, "2026-10-04") == a  # departure cleaning
    assert supplier_views.suggested_stay(data, pid, "2026-10-11") == b  # during the stay
    assert supplier_views.suggested_stay(data, pid, "2026-10-08") == ""


def test_reconciliation_replaces_entries_typed_by_hand(setup):
    data, ledger, pid, sup, a, b = setup
    first = ledger.create_entry({"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Ménage de départ",
                                 "amount": "45", "date": "2026-10-04", "stay_id": a, "paid": True, "paid_date": "2026-10-05"})["entry"]
    second = ledger.create_entry({"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Ménage de départ",
                                  "amount": "35", "date": "2026-10-13", "stay_id": b})["entry"]
    other = ledger.create_entry({"property_id": pid, "kind": "expense", "category_id": "energy", "label": "Électricité",
                                 "amount": "48", "date": "2026-10-14"})["entry"]
    entry = invoice(ledger, pid, sup)
    assert expenses(data, pid) == 4500 + 3500 + 4800 + 15000 + 9000
    found = [c["id"] for c in supplier_views.candidates(data, data["entries"][entry["id"]], "fr")]
    assert set(found) == {first["id"], second["id"]} and other["id"] not in found
    ledger.reconcile(entry["id"], {"entry_ids": [first["id"], second["id"]]})
    # The invoice is the only expense now; the payment typed by hand follows it.
    assert expenses(data, pid) == 4800 + 15000 + 9000
    assert expenses(data, pid, "cash") == 4500
    detail = entry_views.detail(data, data["entries"][entry["id"]], "fr", TODAY)
    assert (detail["paid"], detail["state"], [r["amount"] for r in detail["replaces"]]) == (4500, "partial", [4500, 3500])
    assert data["entries"][first["id"]]["superseded_by"] == entry["id"]
    with pytest.raises(RCError) as refused:
        ledger.set_entry_archived(entry["id"], True)
    assert refused.value.code == "entry_reconciled"
    with pytest.raises(RCError):
        ledger.update_entry(entry["id"], {"amount": "70", "lines": [{"kind": "cleaning", "amount": "70"}]})
    ledger.unreconcile(entry["id"], {"entry_id": first["id"]})
    assert data["entries"][first["id"]]["superseded_by"] == "" and ledger.entry_paid(first["id"]) == 4500
    assert ledger.entry_paid(entry["id"]) == 0


def test_reconciliation_cannot_replace_more_than_the_invoice(setup):
    data, ledger, pid, sup, *_ = setup
    big = ledger.create_entry({"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Ménage",
                               "amount": "160", "date": "2026-10-04"})["entry"]
    entry = invoice(ledger, pid, sup)
    with pytest.raises(RCError) as refused:
        ledger.reconcile(entry["id"], {"entry_ids": [big["id"]]})
    assert refused.value.code == "reconcile_exceeds"
    assert data["entries"][big["id"]]["superseded_by"] == ""
    with pytest.raises(RCError):
        ledger.reconcile(entry["id"], {"entry_ids": [entry["id"]]})


def test_supplier_summary(setup):
    data, ledger, pid, sup, *_ = setup
    invoice(ledger, pid, sup)
    ledger.create_entry({"property_id": pid, "kind": "expense", "category_id": "linen", "label": "Linge", "amount": "20",
                         "date": "2026-10-25", "supplier_id": sup})
    item = supplier_views.summary(data, data["suppliers"][sup], "fr", TODAY)
    assert (item["entries"], item["year_total"], item["to_pay"], item["to_confirm"]) == (2, 17000, 17000, 1)
    assert [r["kind_label"] + "/" + r["unit_label"] for r in item["rates"]] == ["Ménage/heure", "Linge/lot"]
    assert [c["label"] for c in item["categories"]] == ["Ménage", "Linge"]


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


def post(client, path, body, op):
    response = client.post(path, json={**body, "op_id": op}, params={"lang": "fr"})
    assert response.status_code == 200, response.text
    return response.json()


def test_api_supplier_invoice_split_and_reconcile(client):
    pid = post(client, "/api/properties", {"name": "Gîte d'essai"}, "op-p")["property"]["id"]
    sup = post(client, "/api/suppliers", {"name": "Ménage Essai", "categories": ["cleaning", "linen"],
                                          "rates": [{"kind": "linen", "unit": "set", "unit_price": "10"}]}, "op-s")["detail"]
    assert sup["rates"][0]["unit_label"] == "lot"
    stay = post(client, "/api/stays", {"property_id": pid, "start": "2026-09-28", "end": "2026-10-04",
                                       "amounts": {"gross": "600", "commission": "90"}}, "op-st")["stay"]
    manual = post(client, "/api/entries", {"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Ménage de départ",
                                           "amount": "45", "date": "2026-10-04", "paid": True}, "op-m")["entry"]
    created = post(client, "/api/entries", {"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Facture F-018",
                                            "amount": "150", "date": "2026-10-20", "supplier_id": sup["id"], "lines": LINES}, "op-i")
    detail = created["detail"]
    assert [r["kind_label"] for r in detail["split"]] == ["Ménage", "Linge", "Déplacement"]
    split = post(client, f"/api/entries/{detail['id']}/allocations", {"revision": detail["revision"], "allocations": [
        {"line_id": "l1", "stay_id": stay["id"], "amount": "100"}, {"line_id": "l2", "stay_id": stay["id"], "amount": "40"},
        {"line_id": "l3", "stay_id": stay["id"], "amount": "10"}]}, "op-a")["detail"]
    assert sum(r["remaining"] for r in split["split"]) == 0
    # Removing a service already split is refused, and nothing changes.
    refused = client.patch(f"/api/entries/{detail['id']}", params={"lang": "fr"},
                           json={"amount": "140", "lines": LINES[:2], "revision": split["revision"], "op_id": "op-x"})
    assert refused.status_code == 400 and refused.json()["code"] == "allocation_line_removed" and "Déplacement" in refused.json()["message"]
    assert [line["id"] for line in client.get(f"/api/entries/{detail['id']}").json()["service_lines"]] == ["l1", "l2", "l3"]
    stay_detail = client.get(f"/api/stays/{stay['id']}").json()
    assert (stay_detail["costs_total"], stay_detail["margin"]) == (15000, 36000)
    candidates = client.get(f"/api/entries/{detail['id']}/candidates").json()["candidates"]
    assert [c["id"] for c in candidates] == [manual["id"]] and candidates[0]["paid"] == 4500
    reconciled = post(client, f"/api/entries/{detail['id']}/reconcile", {"entry_ids": [manual["id"]], "revision": split["revision"]}, "op-r")["detail"]
    assert reconciled["replaces"][0]["label"] == "Ménage de départ" and reconciled["paid"] == 4500 and not reconciled["deletable"]
    listing = client.get("/api/entries").json()
    assert listing["counts"]["all"] == 1 and listing["counts"]["archived"] == 1
    replaced = client.get(f"/api/entries/{manual['id']}").json()
    assert replaced["superseded_by"]["id"] == detail["id"]
    undone = post(client, f"/api/entries/{detail['id']}/unreconcile", {"entry_id": manual["id"], "revision": reconciled["revision"]}, "op-u")
    assert undone["detail"]["replaces"] == [] and undone["detail"]["paid"] == 0
    suppliers = client.get("/api/suppliers").json()
    assert suppliers["suppliers"][0]["entries"] == 1 and suppliers["counts"] == {"active": 1, "archived": 0}
    assert [e["label"] for e in client.get("/api/entries", params={"supplier_id": sup["id"]}).json()["entries"]] == ["Facture F-018"]


def test_api_supplier_edit_archive_and_rights(client):
    pid = post(client, "/api/properties", {"name": "Gîte d'essai"}, "op-p")["property"]["id"]
    other = post(client, "/api/properties", {"name": "Autre bien"}, "op-p2")["property"]["id"]
    sup = post(client, "/api/suppliers", {"name": "Atelier Essai"}, "op-s")["detail"]
    stale = client.patch(f"/api/suppliers/{sup['id']}", json={"role": "x", "revision": sup["revision"] + 5, "op_id": "op-1"})
    assert stale.status_code == 409
    edited = client.patch(f"/api/suppliers/{sup['id']}", json={"role": "Réparations", "revision": sup["revision"], "op_id": "op-2"})
    assert edited.json()["detail"]["role"] == "Réparations"
    for prop, amount, op in ((pid, "100", "op-3"), (other, "900", "op-4")):
        post(client, "/api/entries", {"property_id": prop, "kind": "expense", "category_id": "maintenance", "label": "Réparation",
                                      "amount": amount, "date": "2026-10-10", "supplier_id": sup["id"]}, op)
    assert client.get(f"/api/suppliers/{sup['id']}").json()["year_total"] == 100000
    db = client.app.state.services.db
    with db.transaction() as conn:
        conn.execute("INSERT INTO users(username, display_name, password_hash, role, created_at, updated_at) VALUES ('lecteur', '', ?, 'reader', '2026-10-31', '2026-10-31')",
                     (hash_password(PASSWORD),))
        uid = conn.execute("SELECT id FROM users WHERE username = 'lecteur'").fetchone()[0]
        conn.execute("INSERT INTO grants(user_id, property_id, documents) VALUES (?, ?, 0)", (uid, pid))
    reader = TestClient(client.app)
    token = reader.get("/api/session").json()["csrf"]
    reader.headers["X-CSRF-Token"] = reader.post("/api/auth/login", json={"username": "lecteur", "password": PASSWORD},
                                                 headers={"X-CSRF-Token": token}).json()["csrf"]
    assert reader.get(f"/api/suppliers/{sup['id']}").json()["year_total"] == 10000  # only the granted property
    assert reader.post("/api/suppliers", json={"name": "x"}).status_code == 403
    archived = post(client, f"/api/suppliers/{sup['id']}/archive", {}, "op-5")["detail"]
    assert archived["archived"] is True
    assert client.get("/api/suppliers", params={"view": "archived"}).json()["suppliers"][0]["id"] == sup["id"]
    del client.headers["X-CSRF-Token"]
    assert client.post("/api/suppliers", json={"name": "y"}).status_code == 403
