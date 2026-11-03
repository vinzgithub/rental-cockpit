# Copyright © 2026 Vincent Fournet
"""T10: storage failure, full disk, interruption and expired tokens leave a consistent state
and an explained message. Fictional data only."""
from __future__ import annotations

import errno
import sqlite3
from datetime import date

import pytest
from fastapi.testclient import TestClient

from rental_cockpit.app import create_app
from rental_cockpit.config import Config
from rental_cockpit.engine import documents
from rental_cockpit.storage import BlobStore

PASSWORD = "un-mot-de-passe-long"
INVOICE = documents.sample_pdf(["Ménage Essai — document fictif", "Facture n° F-018", "Total TTC 150,00 €"])


@pytest.fixture
def client(tmp_path):
    client = TestClient(create_app(Config(data_dir=tmp_path)))
    client.app.state.services.today = lambda: date(2026, 11, 1)
    token = client.get("/api/session").json()["csrf"]
    response = client.post("/api/auth/setup", json={"username": "admin", "password": PASSWORD, "confirm": PASSWORD},
                           headers={"X-CSRF-Token": token})
    client.headers["X-CSRF-Token"] = response.json()["csrf"]
    client.post("/api/start", json={"choice": "own_data"})
    return client


def create_property(client):
    return client.post("/api/properties", json={"name": "Gîte d'essai", "op_id": "op-p"}, params={"lang": "fr"}).json()["property"]["id"]


def expense(pid, op):
    return {"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Ménage", "amount": "45", "date": "2026-10-04", "op_id": op}


def test_full_disk_when_saving_keeps_the_previous_state(client, monkeypatch):
    pid = create_property(client)
    before = client.get("/api/entries").json()["counts"]["all"]
    real_connect = sqlite3.connect

    class FullDisk:
        def __init__(self, conn):
            object.__setattr__(self, "conn", conn)

        def __setattr__(self, name, value):
            setattr(self.conn, name, value)

        def execute(self, sql, *args):
            if sql.startswith("INSERT INTO registries"):
                raise sqlite3.OperationalError("database or disk is full")
            return self.conn.execute(sql, *args)

        def __getattr__(self, name):
            return getattr(self.conn, name)

    monkeypatch.setattr(sqlite3, "connect", lambda *a, **k: FullDisk(real_connect(*a, **k)))
    refused = client.post("/api/entries", json=expense(pid, "op-1"), params={"lang": "fr"})
    assert refused.status_code == 400 and refused.json()["code"] == "storage_full"
    assert "rien n'a été enregistré" in refused.json()["message"]
    monkeypatch.setattr(sqlite3, "connect", real_connect)
    assert client.get("/api/entries").json()["counts"]["all"] == before  # neither in memory nor on disk
    retried = client.post("/api/entries", json=expense(pid, "op-1"), params={"lang": "fr"})
    assert retried.status_code == 200 and client.get("/api/entries").json()["counts"]["all"] == before + 1


def test_full_disk_for_a_pdf_records_nothing(client, monkeypatch, tmp_path):
    pid = create_property(client)
    checked = client.post("/api/documents/preview", content=INVOICE, params={"filename": "f.pdf"}).json()
    body = {"token": checked["token"], "mode": "create", "op_id": "op-c",
            "entry": {"property_id": pid, "category_id": "cleaning", "label": "Facture", "amount": "150", "date": "2026-10-20"}}

    def no_space(self, sha, raw):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(BlobStore, "write", no_space)
    refused = client.post("/api/documents", json=body, params={"lang": "fr"})
    assert refused.json()["code"] == "storage_full"
    assert client.get("/api/entries").json()["counts"]["all"] == 0 and client.get("/api/documents").json()["documents"] == []
    monkeypatch.undo()
    client.app.state.services.today = lambda: date(2026, 11, 1)
    # The same check is still valid: once space is freed, the confirmation goes through.
    assert client.post("/api/documents", json=body, params={"lang": "fr"}).status_code == 200


def test_interrupted_save_leaves_no_charge_and_no_orphan_file(client, monkeypatch, tmp_path):
    pid = create_property(client)
    checked = client.post("/api/documents/preview", content=INVOICE, params={"filename": "f.pdf"}).json()
    registry = client.app.state.services.registries["real"]
    real_mutate = registry.mutate

    def interrupted(operation, now):
        raise sqlite3.OperationalError("disk I/O error")

    monkeypatch.setattr(registry, "mutate", interrupted)
    browser = TestClient(client.app, raise_server_exceptions=False, cookies=client.cookies, headers=client.headers)
    failed = browser.post("/api/documents", params={"lang": "fr"}, json={"token": checked["token"], "mode": "create", "op_id": "op-c", "entry": {
        "property_id": pid, "category_id": "cleaning", "label": "Facture", "amount": "150", "date": "2026-10-20"}})
    assert failed.status_code == 500 and failed.json()["code"] == "unknown" and "rien n'a été enregistré" in failed.json()["message"]
    monkeypatch.setattr(registry, "mutate", real_mutate)
    assert client.get("/api/entries").json()["counts"]["all"] == 0
    assert not list((tmp_path / "documents").glob("*.pdf"))  # the file written first was removed


def test_expired_tokens_are_explained(client):
    pid = create_property(client)
    gone = client.post("/api/documents", json={"token": "expire", "mode": "create", "op_id": "op-x",
                                                "entry": {"property_id": pid}}, params={"lang": "fr"})
    assert gone.json()["code"] == "pdf_preview_expired" and "rien n'a été enregistré" in gone.json()["message"]
    restore = client.post("/api/restore/apply", json={"token": "expire", "confirm": "REMPLACER"}, params={"lang": "fr"})
    assert restore.json()["code"] == "restore_expired" and "rien n'a été restauré" in restore.json()["message"]
    stale = client.post("/api/properties", json={"name": "x", "op_id": "op-y"}, params={"lang": "fr"},
                        headers={"X-CSRF-Token": "ancien-jeton"})
    assert stale.status_code == 403 and stale.json()["code"] == "csrf_failed"
    signed_out = TestClient(client.app)
    assert signed_out.get("/api/entries").status_code == 401
