# Copyright © 2026 Vincent Fournet
"""Stays (delivery L1, 0.2.0): engine rules, schema 2 migration and the « Séjours » API.

Fictional data only. The scenario figures are the ones given to the
independent testers in the pull request.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rental_cockpit.app import create_app
from rental_cockpit.config import Config
from rental_cockpit.database import Database, Registry
from rental_cockpit.engine import stays as stay_views
from rental_cockpit.engine.errors import RCError
from rental_cockpit.engine.indicators import compute, month_period
from rental_cockpit.engine.ledger import Ledger
from rental_cockpit.engine.migrations import migrate
from rental_cockpit.engine.schema import SCHEMA_VERSION, empty_registry
from rental_cockpit.security import hash_password

FIXTURE = Path(__file__).parent / "fixtures" / "registry_v1.json"
TODAY = date(2026, 10, 31)
PASSWORD = "un-mot-de-passe-long"


def figures(data, pid, year, month, mode):
    start, end = month_period(year, month)
    ind = compute(data, property_ids={pid}, start=start, end=end, mode=mode, lang="fr", today=TODAY)["indicators"]
    return ind["revenue"]["value"], ind["operating_expenses"]["value"], ind["operating_balance"]["value"]


@pytest.fixture
def house():
    data = empty_registry()
    ledger = Ledger(data, "1")
    pid = ledger.create_property({"name": "Gîte d'essai"})["property"]["id"]
    return data, ledger, pid


# --------------------------------------------------------------------------- engine


def test_validation_scenario_three_readings(house):
    """The scenario of the pull request: 6 nights across two months, then the payout."""
    data, ledger, pid = house
    stay = ledger.create_stay({"property_id": pid, "start": "2026-09-28", "end": "2026-10-04", "guests": 2,
                               "amounts": {"gross": "600", "commission": "90"}})["stay"]
    assert stay["channel"] == "direct"
    assert figures(data, pid, 2026, 9, "activity") == (30000, 4500, 25500)
    assert figures(data, pid, 2026, 10, "activity") == (30000, 4500, 25500)
    assert figures(data, pid, 2026, 9, "invoice") == (60000, 9000, 51000)
    assert figures(data, pid, 2026, 10, "invoice") == (0, 0, 0)
    assert figures(data, pid, 2026, 10, "cash") == (0, 0, 0)
    summary = stay_views.summary(data, stay, TODAY, "fr")
    assert (summary["nights"], summary["expected_payout"], summary["payout_state"]) == (6, 51000, "to_confirm")

    ledger.create_payment({"property_id": pid, "direction": "in", "date": "2026-10-05", "amount": "510",
                           "links": [{"type": "stay", "id": stay["id"], "amount": "510"}]})
    assert figures(data, pid, 2026, 10, "cash") == (51000, 0, 51000)
    assert stay_views.summary(data, stay, TODAY, "fr")["payout_state"] == "received"


def test_month_split_adds_up_to_the_cent(house):
    data, ledger, pid = house
    stay = ledger.create_stay({"property_id": pid, "start": "2026-01-30", "end": "2026-02-02",
                               "amounts": {"gross": "100", "commission": "10"}})["stay"]
    rows = stay_views.breakdown(stay)
    assert [r["nights"] for r in rows] == [2, 1]
    assert sum(r["revenue"] for r in rows) == 10000 and sum(r["commission"] for r in rows) == 1000
    # Same figures as the Overview, month by month.
    assert rows[0]["revenue"] == figures(data, pid, 2026, 1, "activity")[0]
    assert rows[1]["revenue"] == figures(data, pid, 2026, 2, "activity")[0]


def test_cancellation_keeps_the_retained_amount_on_the_arrival_date(house):
    data, ledger, pid = house
    stay = ledger.create_stay({"property_id": pid, "start": "2026-10-30", "end": "2026-11-02",
                               "amounts": {"gross": "300", "commission": "45"}})["stay"]
    with pytest.raises(RCError) as err:
        ledger.update_stay(stay["id"], {"status": "cancelled"})
    assert err.value.code == "stay_cancel_route"
    cancelled = ledger.cancel_stay(stay["id"], {"retained": "60", "updated_at": stay["updated_at"]})["stay"]
    assert cancelled["status"] == "cancelled" and cancelled["amounts_before_cancel"]["gross"] == 30000
    # 60 € kept, counted once in October (arrival), nothing in November; no night is counted.
    assert figures(data, pid, 2026, 10, "activity") == (6000, 0, 6000)
    assert figures(data, pid, 2026, 11, "activity") == (0, 0, 0)
    assert stay_views.breakdown(cancelled)[0]["revenue"] == 6000
    restored = ledger.restore_stay(stay["id"], {})["stay"]
    assert restored["status"] == "confirmed" and restored["amounts"]["gross"] == 30000
    assert "amounts_before_cancel" not in restored
    assert figures(data, pid, 2026, 11, "activity")[0] == 10000  # 1 night of 3 in November


def test_cancellation_cannot_go_below_what_was_received(house):
    data, ledger, pid = house
    stay = ledger.create_stay({"property_id": pid, "start": "2026-10-01", "end": "2026-10-03",
                               "amounts": {"gross": "200", "commission": "30"}})["stay"]
    ledger.create_payment({"property_id": pid, "direction": "in", "date": "2026-10-04", "amount": "170",
                           "links": [{"type": "stay", "id": stay["id"], "amount": "170"}]})
    with pytest.raises(RCError) as err:
        ledger.cancel_stay(stay["id"], {"retained": "50"})
    assert err.value.code == "cancel_received_too_high"
    with pytest.raises(RCError) as err:
        ledger.cancel_stay(stay["id"], {"retained": "50", "retained_commission": "60"})
    assert err.value.code == "cancel_commission_too_high"


def test_payout_states_and_overpayment(house):
    data, ledger, pid = house
    later = ledger.create_stay({"property_id": pid, "start": "2026-12-01", "end": "2026-12-03",
                                "amounts": {"gross": "200", "commission": "30"}})["stay"]
    assert stay_views.summary(data, later, TODAY, "fr")["payout_state"] == "expected"
    unknown = ledger.create_stay({"property_id": pid, "start": "2026-10-10", "end": "2026-10-12"})["stay"]
    assert stay_views.summary(data, unknown, TODAY, "fr")["payout_state"] == "unknown"
    ledger.create_payment({"property_id": pid, "direction": "in", "date": "2026-11-02", "amount": "100",
                           "links": [{"type": "stay", "id": later["id"], "amount": "100"}]})
    assert stay_views.summary(data, later, TODAY, "fr")["payout_state"] == "partial"
    with pytest.raises(RCError) as err:
        ledger.create_payment({"property_id": pid, "direction": "in", "date": "2026-11-03", "amount": "80",
                               "links": [{"type": "stay", "id": later["id"], "amount": "80"}]})
    assert err.value.code == "payout_exceeds"
    ledger.create_payment({"property_id": pid, "direction": "in", "date": "2026-11-03", "amount": "70",
                           "links": [{"type": "stay", "id": later["id"], "amount": "70"}]})
    assert stay_views.summary(data, later, TODAY, "fr")["payout_state"] == "received"


def test_cancelled_stay_without_retained_amount_has_nothing_to_receive(house):
    data, ledger, pid = house
    stay = ledger.create_stay({"property_id": pid, "start": "2026-10-01", "end": "2026-10-03",
                               "amounts": {"gross": "200", "commission": "30"}})["stay"]
    cancelled = ledger.cancel_stay(stay["id"], {})["stay"]
    assert stay_views.summary(data, cancelled, TODAY, "fr")["payout_state"] == "none"
    assert figures(data, pid, 2026, 10, "activity") == (0, 0, 0)


# --------------------------------------------------------------------------- migration


def test_schema_1_registry_migrates_without_losing_anything():
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert raw["schema"] == 1 and SCHEMA_VERSION == 2
    migrated, changed = migrate(raw)
    assert changed and migrated["schema"] == 2
    for key in ("properties", "stays", "entries", "payments"):
        assert set(migrated[key]) == set(raw[key])
    channels = {s["source"]: s["channel"] for s in migrated["stays"].values()}
    assert channels == {"manual": "other", "airbnb": "airbnb", "csv": "other"}
    pid = next(iter(raw["properties"]))
    for mode in ("activity", "invoice", "cash"):
        assert figures(migrated, pid, 2026, 10, mode) == figures(raw, pid, 2026, 10, mode)
    assert migrate(migrated) == (migrated, False)


def test_database_is_copied_before_a_migration(tmp_path):
    db = Database(tmp_path / "rental_cockpit.db")
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    db.save_registry("real", raw, 0, "2026-10-01T08:00:00+00:00")
    registry = Registry(db, "real")
    registry.load(create=False, now="2026-11-01T09:30:00+00:00")
    assert registry.data["schema"] == 2
    copies = list((tmp_path / "backups").glob("pre-migration-v1-to-v2-*.db"))
    assert len(copies) == 1
    with sqlite3.connect(copies[0]) as old:
        body = json.loads(old.execute("SELECT body FROM registries WHERE dataset = 'real'").fetchone()[0])
    assert body["schema"] == 1 and set(body["stays"]) == set(raw["stays"])
    # A second start does not copy again: there is nothing left to migrate.
    Registry(Database(tmp_path / "rental_cockpit.db"), "real").load(create=False, now="2026-11-02T09:30:00+00:00")
    assert len(list((tmp_path / "backups").glob("*.db"))) == 1


# --------------------------------------------------------------------------- API


@pytest.fixture
def client(tmp_path):
    client = TestClient(create_app(Config(data_dir=tmp_path)))
    token = client.get("/api/session").json()["csrf"]
    response = client.post("/api/auth/setup", json={"username": "admin", "password": PASSWORD, "confirm": PASSWORD},
                           headers={"X-CSRF-Token": token})
    client.headers["X-CSRF-Token"] = response.json()["csrf"]
    client.post("/api/start", json={"choice": "own_data"})
    return client


def new_property(client) -> str:
    return client.post("/api/properties", json={"name": "Gîte d'essai", "op_id": "op-prop"}).json()["property"]["id"]


def test_api_create_list_read_and_overview(client):
    pid = new_property(client)
    created = client.post("/api/stays", json={"property_id": pid, "start": "2026-09-28", "end": "2026-10-04", "guests": 2,
                                              "channel": "airbnb", "amounts": {"gross": "600", "commission": "90"}, "op_id": "op-1"})
    assert created.status_code == 200, created.text
    detail = created.json()["detail"]
    assert detail["nights"] == 6 and detail["expected_payout"] == 51000 and detail["channel_label"] == "Airbnb"
    assert [(r["nights"], r["revenue"]) for r in detail["breakdown"]] == [(3, 30000), (3, 30000)]
    stays = client.get("/api/stays", params={"view": "all"}).json()
    assert [s["id"] for s in stays["stays"]] == [detail["id"]]
    assert stays["counts"]["attention"] == 1  # payout to confirm (the stay has ended)
    overview = client.get("/api/overview", params={"start": "2026-09-01", "end": "2026-10-01"}).json()
    assert overview["indicators"]["revenue"]["value"] == 30000
    received = client.post(f"/api/stays/{detail['id']}/payouts", json={"date": "2026-10-05", "amount": "510", "op_id": "op-2"})
    assert received.status_code == 200, received.text
    assert received.json()["detail"]["payout_state"] == "received"
    cash = client.get("/api/overview", params={"start": "2026-10-01", "end": "2026-11-01", "mode": "cash"}).json()
    assert cash["indicators"]["revenue"]["value"] == 51000
    payment_id = received.json()["detail"]["payments"][0]["id"]
    undone = client.request("DELETE", f"/api/payments/{payment_id}", json={"op_id": "op-3"})
    assert undone.json()["detail"]["payout_state"] == "to_confirm"


def test_api_double_click_creates_one_stay(client):
    pid = new_property(client)
    body = {"property_id": pid, "start": "2026-11-10", "end": "2026-11-12", "op_id": "op-same"}
    first = client.post("/api/stays", json=body).json()
    again = client.post("/api/stays", json=body).json()
    assert again["replayed"] is True and again["stay"]["id"] == first["stay"]["id"]
    assert len(client.get("/api/stays", params={"view": "all"}).json()["stays"]) == 1


def test_api_refuses_a_change_made_on_an_outdated_copy(client):
    pid = new_property(client)
    stay = client.post("/api/stays", json={"property_id": pid, "start": "2026-11-10", "end": "2026-11-12", "op_id": "op-a"}).json()["stay"]
    ok = client.patch(f"/api/stays/{stay['id']}", json={"guests": 3, "revision": stay["revision"], "op_id": "op-b"})
    assert ok.status_code == 200 and ok.json()["stay"]["revision"] == stay["revision"] + 1
    # Same second, older copy: the revision number still tells them apart.
    stale = client.patch(f"/api/stays/{stay['id']}", json={"guests": 4, "revision": stay["revision"], "op_id": "op-c"})
    assert stale.status_code == 409 and stale.json()["code"] == "stale_revision"


def test_api_cancel_restore_and_delete(client):
    pid = new_property(client)
    stay = client.post("/api/stays", json={"property_id": pid, "start": "2026-11-10", "end": "2026-11-12",
                                           "amounts": {"gross": "200", "commission": "30"}, "op_id": "op-a"}).json()["detail"]
    cancelled = client.post(f"/api/stays/{stay['id']}/cancel", json={"retained": "50", "op_id": "op-b"}).json()["detail"]
    assert cancelled["state"] == "cancelled" and cancelled["amounts"]["gross"] == 5000
    assert client.get("/api/stays", params={"view": "cancelled"}).json()["counts"]["cancelled"] == 1
    restored = client.post(f"/api/stays/{stay['id']}/restore", json={"op_id": "op-c"}).json()["detail"]
    assert restored["status"] == "confirmed" and restored["amounts"]["gross"] == 20000
    deleted = client.request("DELETE", f"/api/stays/{stay['id']}", json={"op_id": "op-d"})
    assert deleted.json()["deleted"] == stay["id"]
    assert client.get(f"/api/stays/{stay['id']}").status_code == 404


def test_api_validation_messages(client):
    pid = new_property(client)
    wrong = client.post("/api/stays", json={"property_id": pid, "start": "2026-11-12", "end": "2026-11-12", "op_id": "op-a"},
                        params={"lang": "fr"})
    assert wrong.status_code == 400 and "départ" in wrong.json()["message"]


def test_api_reader_sees_only_granted_stays_and_cannot_write(client):
    pid = new_property(client)
    other = client.post("/api/properties", json={"name": "Autre bien", "op_id": "op-prop-2"}).json()["property"]["id"]
    mine = client.post("/api/stays", json={"property_id": pid, "start": "2026-11-10", "end": "2026-11-12", "op_id": "op-a"}).json()["stay"]
    hidden = client.post("/api/stays", json={"property_id": other, "start": "2026-11-10", "end": "2026-11-12", "op_id": "op-b"}).json()["stay"]
    db = client.app.state.services.db
    with db.transaction() as conn:
        conn.execute("INSERT INTO users(username, display_name, password_hash, role, created_at, updated_at) VALUES ('lecteur', '', ?, 'reader', '2026-10-31', '2026-10-31')",
                     (hash_password(PASSWORD),))
        uid = conn.execute("SELECT id FROM users WHERE username = 'lecteur'").fetchone()[0]
        conn.execute("INSERT INTO grants(user_id, property_id, documents) VALUES (?, ?, 0)", (uid, pid))
    reader = TestClient(client.app)
    token = reader.get("/api/session").json()["csrf"]
    token = reader.post("/api/auth/login", json={"username": "lecteur", "password": PASSWORD}, headers={"X-CSRF-Token": token}).json()["csrf"]
    reader.headers["X-CSRF-Token"] = token
    listed = reader.get("/api/stays", params={"view": "all"}).json()["stays"]
    assert [s["id"] for s in listed] == [mine["id"]]
    assert reader.get(f"/api/stays/{hidden['id']}").json()["code"] == "forbidden_property"
    refused = reader.post("/api/stays", json={"property_id": pid, "start": "2026-12-01", "end": "2026-12-02", "op_id": "op-r"})
    assert refused.status_code == 403
    assert reader.patch(f"/api/stays/{mine['id']}", json={"guests": 9}).status_code == 403


def test_api_demo_stays_stay_in_the_demo(client):
    client.post("/api/start", json={"choice": "demo"})
    demo = client.get("/api/stays", params={"dataset": "demo", "view": "all"}).json()["stays"]
    real = client.get("/api/stays", params={"view": "all"}).json()["stays"]
    assert demo and not real
    assert {s["channel"] for s in demo} <= {"airbnb", "abritel"}


def test_api_changes_need_the_csrf_token(client):
    pid = new_property(client)
    del client.headers["X-CSRF-Token"]
    refused = client.post("/api/stays", json={"property_id": pid, "start": "2026-11-10", "end": "2026-11-12"})
    assert refused.status_code == 403 and refused.json()["code"] == "csrf_failed"
