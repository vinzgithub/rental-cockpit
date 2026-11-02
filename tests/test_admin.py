# Copyright © 2026 Vincent Fournet
"""Version 1.0: reader accounts, backups and restore (SAU 01, SAU 02, T11). Fictional data only."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient

from rental_cockpit import cli
from rental_cockpit.app import create_app
from rental_cockpit.config import Config
from rental_cockpit.engine import documents

TODAY = date(2026, 11, 1)
PASSWORD = "un-mot-de-passe-long"
INVOICE = documents.sample_pdf(["Ménage Essai — document fictif", "Facture n° F-018", "Total TTC 150,00 €"])


def admin_client(data_dir):
    client = TestClient(create_app(Config(data_dir=data_dir)))
    client.app.state.services.today = lambda: TODAY
    token = client.get("/api/session").json()["csrf"]
    response = client.post("/api/auth/setup", json={"username": "admin", "password": PASSWORD, "confirm": PASSWORD},
                           headers={"X-CSRF-Token": token})
    client.headers["X-CSRF-Token"] = response.json()["csrf"]
    client.post("/api/start", json={"choice": "own_data"})
    return client


def sign_in(app, username, password):
    client = TestClient(app)
    token = client.get("/api/session").json()["csrf"]
    response = client.post("/api/auth/login", json={"username": username, "password": password}, headers={"X-CSRF-Token": token})
    client.headers["X-CSRF-Token"] = response.json().get("csrf", token)
    return client, response


def post(client, path, body, op=None):
    response = client.post(path, json={**body, **({"op_id": op} if op else {})}, params={"lang": "fr"})
    assert response.status_code == 200, response.text
    return response.json()


def fill(client):
    """A property, a stay, an expense paid in part and its PDF."""
    pid = post(client, "/api/properties", {"name": "Gîte d'essai"}, "op-p")["property"]["id"]
    other = post(client, "/api/properties", {"name": "Autre bien"}, "op-p2")["property"]["id"]
    post(client, "/api/stays", {"property_id": pid, "start": "2026-10-10", "end": "2026-10-13", "guest_label": "Séjour B",
                                "amounts": {"gross": "300", "commission": "45"}}, "op-s")
    entry = post(client, "/api/entries", {"property_id": pid, "kind": "expense", "category_id": "cleaning", "label": "Ménage",
                                          "amount": "150", "date": "2026-10-20", "payment_declared": "unpaid"}, "op-e")["detail"]
    post(client, f"/api/entries/{entry['id']}/payments", {"date": "2026-10-25", "amount": "50"}, "op-pay")
    checked = client.post("/api/documents/preview", content=INVOICE, params={"filename": "facture.pdf", "entry_id": entry["id"]}).json()
    post(client, "/api/documents", {"token": checked["token"], "mode": "attach", "entry_id": entry["id"]}, "op-d")
    return pid, other, entry


# --------------------------------------------------------------------------- reader accounts


def test_reader_account_from_creation_to_deletion(tmp_path):
    client = admin_client(tmp_path)
    pid, other, entry = fill(client)
    created = post(client, "/api/users", {"username": "lecteur", "display_name": "Comptable", "password": "temporaire-123",
                                          "grants": [{"property_id": pid, "documents": False}, {"property_id": "inconnu"}]})
    reader = next(u for u in created["users"] if u["username"] == "lecteur")
    assert (reader["role"], reader["must_change_password"], reader["grants"]) == ("reader", True, {pid: False})
    duplicate = client.post("/api/users", json={"username": "LECTEUR", "password": "temporaire-123"})
    assert duplicate.json()["code"] == "username_taken"
    assert client.post("/api/users", json={"username": "a b", "password": "temporaire-123"}).json()["code"] == "username_invalid"
    assert client.post("/api/users", json={"username": "court", "password": "x"}).json()["code"] == "password_too_short"
    # First sign-in: nothing opens before the reader chooses a password.
    browser, _ = sign_in(client.app, "lecteur", "temporaire-123")
    session = browser.get("/api/session").json()
    assert session["must_change_password"] is True
    assert browser.get("/api/overview", params={"start": "2026-10-01", "end": "2026-11-01"}).json()["code"] == "password_change_required"
    changed = browser.post("/api/account/password", json={"current": "temporaire-123", "new": "mon-mot-de-passe", "confirm": "mon-mot-de-passe"})
    assert changed.status_code == 200
    assert "must_change_password" not in browser.get("/api/session").json()
    # Property only: entries yes, PDFs no, the other property never.
    assert browser.get(f"/api/entries/{entry['id']}").json()["documents_access"] is False
    assert browser.get("/api/entries", params={"property_id": other}).status_code == 403
    # PDFs granted: the change applies at the next request.
    assert client.patch(f"/api/users/{reader['id']}", json={"grants": [{"property_id": pid, "documents": True}]}).status_code == 200
    assert browser.get(f"/api/entries/{entry['id']}").json()["documents_access"] is True
    # A reader cannot manage accounts or backups.
    assert browser.get("/api/users").status_code == 403
    assert browser.post("/api/backups").status_code == 403
    # Reset: every session of the reader ends, a new password is asked again.
    post(client, f"/api/users/{reader['id']}/password", {"password": "nouveau-temporaire"})
    assert browser.get("/api/session").json()["authenticated"] is False
    again, _ = sign_in(client.app, "lecteur", "nouveau-temporaire")
    assert again.get("/api/session").json()["must_change_password"] is True
    # The administrator account cannot be changed or deleted from here.
    admin_id = next(u["id"] for u in client.get("/api/users").json()["users"] if u["role"] == "admin")
    assert client.request("DELETE", f"/api/users/{admin_id}").status_code == 404
    deleted = client.request("DELETE", f"/api/users/{reader['id']}").json()
    assert [u["username"] for u in deleted["users"]] == ["admin"]
    assert sign_in(client.app, "lecteur", "nouveau-temporaire")[1].status_code != 200


# --------------------------------------------------------------------------- backups


def backup_bytes(client) -> tuple[str, bytes]:
    made = post(client, "/api/backups", {})["backup"]
    file = client.get(f"/api/backups/{made['name']}/file")
    assert file.status_code == 200 and file.headers["content-type"] == "application/zip"
    return made["name"], file.content


def test_backup_restored_on_another_installation(tmp_path):
    source = admin_client(tmp_path / "source")
    pid, _, entry = fill(source)
    post(source, "/api/users", {"username": "lecteur", "password": "temporaire-123", "grants": [{"property_id": pid, "documents": True}]})
    name, raw = backup_bytes(source)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        names = sorted(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
        accounts = archive.read("accounts.json").decode()
    assert names == ["accounts.json", f"documents/{documents.sha256(INVOICE)}.pdf", "manifest.json", "registry.json"]
    assert manifest["totals"] == {"expenses": 15000, "income": 0, "payments": 5000, "stays_gross": 30000}
    assert "password" not in accounts and "totp" not in accounts and "pbkdf2" not in accounts and "scrypt" not in accounts
    if (tmp_path / "source" / "backups").exists():
        assert ((tmp_path / "source" / "backups" / name).stat().st_mode & 0o777) == 0o600

    # Another installation, with its own reader of the same name.
    target = admin_client(tmp_path / "target")
    post(target, "/api/properties", {"name": "Bien à remplacer"}, "op-x")
    target.post("/api/users", json={"username": "lecteur", "password": "temporaire-123"})
    checked = target.post("/api/restore/check", content=raw, headers={"Content-Type": "application/zip"})
    assert checked.status_code == 200, checked.text
    summary = checked.json()
    assert summary["backup"]["properties"] == ["Autre bien", "Gîte d'essai"] and summary["backup"]["documents"] == 1
    assert summary["current"]["counts"]["properties"] == 1
    # Nothing changed yet; the confirmation word is required.
    assert [p["name"] for p in target.get("/api/users").json()["properties"]] == ["Bien à remplacer"]
    refused = target.post("/api/restore/apply", json={"token": summary["token"], "confirm": "oui"})
    assert refused.json()["code"] == "restore_confirm"
    restored = post(target, "/api/restore/apply", {"token": summary["token"], "confirm": "REMPLACER"})
    assert restored["same_totals"] is True and restored["safety_backup"].startswith("avant-restauration")
    assert restored["grants"] == {"applied": ["lecteur"], "unknown": []}
    # Same figures, same PDF bytes, rights back by name.
    entries = target.get("/api/entries").json()
    assert entries["totals"]["expenses"] == 15000 and entries["counts"]["all"] == 1
    doc = target.get(f"/api/entries/{entry['id']}").json()["document_list"][0]
    assert target.get(f"/api/documents/{doc['id']}/file").content == INVOICE
    reader = next(u for u in target.get("/api/users").json()["users"] if u["username"] == "lecteur")
    assert reader["grants"] == {pid: True}
    # The replaced data were saved first, and that backup can itself be restored.
    assert any(b["kind"] == "before_restore" for b in target.get("/api/backups").json()["backups"])
    # A token is used once.
    assert target.post("/api/restore/apply", json={"token": summary["token"], "confirm": "REMPLACER"}).json()["code"] == "restore_expired"


def tampered(raw: bytes, change) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(raw))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        files = {info.filename: source.read(info.filename) for info in source.infolist()}
        for name, content in change(files).items():
            archive.writestr(name, content)
    return out.getvalue()


@pytest.mark.parametrize(("case", "change", "code"), [
    ("changed amount", lambda f: {**f, "registry.json": f["registry.json"].replace(b'"amount":15000', b'"amount":95000')}, "backup_invalid"),
    ("changed PDF", lambda f: {**f, **{k: v.replace(b"150,00", b"990,00") for k, v in f.items() if k.startswith("documents/")}}, "backup_invalid"),
    ("missing PDF", lambda f: {k: v for k, v in f.items() if not k.startswith("documents/")}, "backup_invalid"),
    ("path traversal", lambda f: {**f, "../../evil.txt": b"x"}, "backup_invalid"),
    ("newer schema", None, "backup_schema_newer"),
])
def test_damaged_or_foreign_backups_are_refused(tmp_path, case, change, code):
    client = admin_client(tmp_path)
    fill(client)
    _, raw = backup_bytes(client)
    if case == "newer schema":
        def change(files):
            registry = json.loads(files["registry.json"])
            registry["schema"] = 99
            body = json.dumps(registry).encode()
            manifest = json.loads(files["manifest.json"])
            manifest["files"]["registry.json"] = {"sha256": documents.sha256(body), "size": len(body)}
            return {**files, "registry.json": body, "manifest.json": json.dumps(manifest).encode()}
    before = client.get("/api/entries").json()["totals"]
    response = client.post("/api/restore/check", content=tampered(raw, change), headers={"Content-Type": "application/zip"})
    assert response.status_code == 400 and response.json()["code"] == code, (case, response.text)
    assert client.get("/api/entries").json()["totals"] == before
    assert not (tmp_path / "evil.txt").exists() and not list((tmp_path / "restore-staging").glob("*"))
    garbage = client.post("/api/restore/check", content=b"not a zip", headers={"Content-Type": "application/zip"})
    assert garbage.json()["code"] == "backup_invalid"


def test_command_line_backup_and_restore_after_a_failed_update(tmp_path, monkeypatch, capsys):
    """SAU 03: an update that broke the data, then the documented restore, run for real."""
    client = admin_client(tmp_path)
    fill(client)
    expected = client.get("/api/entries").json()["totals"]
    monkeypatch.setenv("RENTAL_COCKPIT_DATA_DIR", str(tmp_path))
    assert cli.main(["backup"]) == 0
    written = capsys.readouterr().out
    archive = next((tmp_path / "backups").glob("rental-cockpit-sauvegarde-*.zip"))
    assert str(archive) in written
    # « The update went wrong »: the registry is emptied and a PDF is lost.
    services = client.app.state.services
    services.registries["real"].mutate(lambda data: data["entries"].clear(), "2026-11-01T00:00:00+00:00")
    for pdf in (tmp_path / "documents").glob("*.pdf"):
        pdf.unlink()
    # A file the container cannot read: refused with the standard-input procedure as the way out.
    assert cli.main(["restore", str(tmp_path / "absent.zip"), "--yes"]) == 1
    assert "Cannot read" in capsys.readouterr().err
    # Typing anything but the confirmation word restores nothing.
    monkeypatch.setattr("builtins.input", lambda prompt: "non")
    assert cli.main(["restore", str(archive)]) == 1
    assert "Nothing was restored." in capsys.readouterr().out
    assert client.get("/api/entries").json()["entries"] == []
    # The documented Docker procedure: the backup on standard input, checked first, then restored with --yes.
    def stdin():
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(archive.read_bytes())))
    stdin()
    assert cli.main(["restore", "-"]) == 1
    out = capsys.readouterr().out
    assert "checked" in out and "run the same command again with --yes" in out
    assert client.get("/api/entries").json()["entries"] == []
    stdin()
    assert cli.main(["restore", "-", "--yes"]) == 0
    out = capsys.readouterr().out
    assert "Same totals as the backup." in out and "avant-restauration" in out
    assert not (tmp_path / "restore-staging" / "cli").exists()
    restarted = TestClient(create_app(Config(data_dir=tmp_path)))
    token = restarted.get("/api/session").json()["csrf"]
    restarted.post("/api/auth/login", json={"username": "admin", "password": PASSWORD}, headers={"X-CSRF-Token": token})
    assert restarted.get("/api/entries").json()["totals"] == expected
    doc = restarted.get("/api/documents").json()["documents"][0]
    assert restarted.get(f"/api/documents/{doc['id']}/file").content == INVOICE
