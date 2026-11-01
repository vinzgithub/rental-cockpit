# Copyright © 2026 Vincent Fournet
"""Two-factor sign-in, password change and read-only API keys (SEC 01, SEC 05)."""
import time

import pytest
from fastapi.testclient import TestClient

from rental_cockpit.app import create_app
from rental_cockpit.config import Config
from rental_cockpit.security import TOTP_PERIOD, totp_at

PASSWORD = "un-mot-de-passe-long"


@pytest.fixture
def app(tmp_path):
    return create_app(Config(data_dir=tmp_path, frame_ancestors="https://ha.example.org"))


def csrf(client):
    return client.get("/api/session").json()["csrf"]


def post(client, url, body=None):
    return client.post(url, json=body or {}, headers={"X-CSRF-Token": csrf(client)})


@pytest.fixture
def admin(app):
    client = TestClient(app)
    assert post(client, "/api/auth/setup", {"username": "admin", "password": PASSWORD, "confirm": PASSWORD}).status_code == 200
    return client


def login(app, code=None):
    client = TestClient(app)
    first = post(client, "/api/auth/login", {"username": "admin", "password": PASSWORD}).json()
    if code is not None:
        assert first["mfa_required"] is True
        return client, post(client, "/api/auth/mfa", {"code": code})
    return client, first


def step_now():
    return int(time.time() // TOTP_PERIOD)


def enable_mfa(admin):
    started = post(admin, "/api/account/mfa/start", {"password": PASSWORD}).json()
    assert started["qr"].startswith("data:image/svg+xml") and started["uri"].startswith("otpauth://totp/Rental%20Cockpit")
    secret = started["secret"].replace(" ", "")
    enabled = post(admin, "/api/account/mfa/enable", {"code": totp_at(secret, step_now())}).json()
    assert len(enabled["recovery_codes"]) == 10
    return secret, enabled["recovery_codes"]


def test_mfa_setup_requires_password_and_a_valid_first_code(admin):
    assert post(admin, "/api/account/mfa/start", {"password": "wrong-password"}).json()["code"] == "password_wrong"
    post(admin, "/api/account/mfa/start", {"password": PASSWORD})
    assert post(admin, "/api/account/mfa/enable", {"code": "000000"}).json()["code"] == "totp_invalid"
    assert admin.get("/api/account").json()["mfa"]["enabled"] is False


def test_sign_in_asks_for_a_code_and_each_code_works_once(app, admin, monkeypatch):
    # The clock is held in the middle of the next 30 s step (never in the past, the
    # session cookie would look signed in the future): crossing into another step
    # during the test would make the « already used » code a fresh one.
    frozen = (int(time.time() // TOTP_PERIOD) + 1.5) * TOTP_PERIOD
    monkeypatch.setattr(time, "time", lambda: frozen)
    secret, codes = enable_mfa(admin)
    assert admin.get("/api/account").json()["mfa"] == {"enabled": True, "recovery_left": 10}
    # The password alone does not open the session.
    client, first = login(app)
    assert first["mfa_required"] is True
    assert client.get("/api/overview", params={"start": "2026-10-01", "end": "2026-11-01"}).status_code == 401
    # The code already used during setup is refused; the next one works.
    _, refused = login(app, totp_at(secret, step_now()))
    assert refused.json()["code"] == "totp_invalid"
    client, accepted = login(app, totp_at(secret, step_now() + 1))
    assert accepted.status_code == 200 and client.get("/api/session").json()["authenticated"] is True


def test_recovery_code_is_single_use(app, admin):
    _, codes = enable_mfa(admin)
    _, first = login(app, codes[0].upper())
    assert first.status_code == 200
    _, second = login(app, codes[0])
    assert second.json()["code"] == "totp_invalid"
    assert admin.get("/api/account").json()["mfa"]["recovery_left"] == 9


def test_enabling_mfa_signs_out_other_browsers_only(app, admin):
    other, _ = login(app)
    assert other.get("/api/session").json()["authenticated"] is True
    enable_mfa(admin)
    assert other.get("/api/session").json()["authenticated"] is False
    assert admin.get("/api/session").json()["authenticated"] is True


def test_disabling_needs_password_and_code(app, admin):
    secret, codes = enable_mfa(admin)
    assert post(admin, "/api/account/mfa/disable", {"password": PASSWORD, "code": "123456"}).json()["code"] == "totp_invalid"
    assert post(admin, "/api/account/mfa/disable", {"password": PASSWORD, "code": codes[3]}).json()["ok"] is True
    _, plain = login(app)
    assert plain["ok"] is True


def test_new_recovery_codes_replace_the_old_ones(app, admin):
    _, old = enable_mfa(admin)
    fresh = post(admin, "/api/account/mfa/recovery", {"password": PASSWORD, "code": old[0]}).json()["recovery_codes"]
    _, refused = login(app, old[1])
    assert refused.json()["code"] == "totp_invalid"
    _, accepted = login(app, fresh[0])
    assert accepted.status_code == 200


def test_password_change_keeps_this_session_and_ends_the_others(app, admin):
    other, _ = login(app)
    assert post(admin, "/api/account/password", {"current": "wrong", "new": "x" * 12, "confirm": "x" * 12}).json()["code"] == "password_wrong"
    assert post(admin, "/api/account/password", {"current": PASSWORD, "new": "nouveau-mot-de-passe", "confirm": "nouveau-mot-de-passe"}).json()["ok"]
    assert admin.get("/api/session").json()["authenticated"] is True
    assert other.get("/api/session").json()["authenticated"] is False


def test_api_key_reads_summary_and_can_be_revoked(app, admin):
    post(admin, "/api/properties", {"name": "Bien fictif"})
    created = post(admin, "/api/account/keys", {"name": "Home Assistant"}).json()
    assert created["token"].startswith("rc_")
    reader = TestClient(app)
    assert reader.get("/api/v1/summary").status_code == 401
    response = reader.get("/api/v1/summary", headers={"Authorization": f"Bearer {created['token']}"})
    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "EUR" and body["properties"][0]["name"] == "Bien fictif"
    assert body["month"]["revenue"] == 0 and body["occupied_tonight"] == 0
    # The key is shown once: the list never contains it.
    listed = admin.get("/api/account").json()["keys"]
    assert listed[0]["name"] == "Home Assistant" and "token" not in listed[0] and listed[0]["last_used_at"]
    assert admin.delete(f"/api/account/keys/{created['id']}", headers={"X-CSRF-Token": csrf(admin)}).json()["ok"]
    assert reader.get("/api/v1/summary", headers={"Authorization": f"Bearer {created['token']}"}).status_code == 401


def test_api_key_cannot_change_anything(app, admin):
    token = post(admin, "/api/account/keys", {"name": "HA"}).json()["token"]
    stranger = TestClient(app)
    response = stranger.post("/api/properties", json={"name": "Intrus"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code in (401, 403)


def test_framing_allowed_only_for_configured_origin(admin):
    response = admin.get("/")
    assert "frame-ancestors 'self' https://ha.example.org" in response.headers["content-security-policy"]
    assert "x-frame-options" not in response.headers


def test_cli_disables_mfa_for_a_lost_phone(app, admin, tmp_path, monkeypatch):
    from rental_cockpit import cli

    enable_mfa(admin)
    monkeypatch.setenv("RENTAL_COCKPIT_DATA_DIR", str(tmp_path))
    assert cli.main(["disable-mfa", "admin"]) == 0
    _, plain = login(app)
    assert plain["ok"] is True
    assert admin.get("/api/session").json()["authenticated"] is False  # every browser signed out
