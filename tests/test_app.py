# Copyright © 2026 Vincent Fournet
"""The web application: accounts, CSRF, rights, demo separation and security headers (SEC 01–07, T07)."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from rental_cockpit.app import create_app
from rental_cockpit.config import Config
from rental_cockpit.engine.demo import example_month

PASSWORD = "un-mot-de-passe-long"


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(Config(data_dir=tmp_path)))


def csrf(client):
    return client.get("/api/session").json()["csrf"]


def setup_admin(client):
    token = csrf(client)
    response = client.post("/api/auth/setup", json={"username": "admin", "password": PASSWORD, "confirm": PASSWORD},
                           headers={"X-CSRF-Token": token})
    assert response.status_code == 200, response.text
    return response.json()["csrf"]


def test_first_visit_requires_creating_the_administrator(client):
    session = client.get("/api/session").json()
    assert session["setup_required"] is True and session["authenticated"] is False
    token = setup_admin(client)
    assert client.get("/api/session").json()["user"]["is_admin"] is True
    # A second administrator cannot be created through the setup page.
    response = client.post("/api/auth/setup", json={"username": "other", "password": PASSWORD, "confirm": PASSWORD},
                           headers={"X-CSRF-Token": token})
    assert response.json()["code"] == "setup_done"


def test_changes_without_csrf_token_are_refused(client):
    setup_admin(client)
    response = client.post("/api/properties", json={"name": "Bien"})
    assert response.status_code == 403 and response.json()["code"] == "csrf_failed"


def test_nothing_is_readable_without_signing_in(client):
    setup_admin(client)
    anonymous = TestClient(client.app)
    for url in ("/api/overview?start=2026-10-01&end=2026-11-01", "/api/indicator?start=2026-10-01&end=2026-11-01&indicator=revenue"):
        response = anonymous.get(url)
        assert response.status_code == 401 and response.json()["code"] == "login_required"


def test_login_throttle_and_generic_message(client):
    setup_admin(client)
    other = TestClient(client.app)
    token = csrf(other)
    codes = [other.post("/api/auth/login", json={"username": "admin", "password": "wrong-password"}, headers={"X-CSRF-Token": token}).json()["code"]
             for _ in range(6)]
    assert codes[:5] == ["login_failed"] * 5 and codes[5] == "login_locked"
    unknown = TestClient(client.app)
    response = unknown.post("/api/auth/login", json={"username": "nobody", "password": "x"}, headers={"X-CSRF-Token": csrf(unknown)})
    assert response.json()["code"] in {"login_failed", "login_locked"}


def test_property_creation_double_click_creates_one(client):
    token = setup_admin(client)
    body = {"name": "Mon <gîte>", "capacity": 4, "op_id": "op-double"}
    first = client.post("/api/properties", json=body, headers={"X-CSRF-Token": token}).json()
    second = client.post("/api/properties", json=body, headers={"X-CSRF-Token": token}).json()
    assert second["property"]["id"] == first["property"]["id"] and second.get("replayed")
    overview = client.get("/api/overview", params={"start": "2026-10-01", "end": "2026-11-01"}).json()
    assert [p["name"] for p in overview["properties"]] == ["Mon <gîte>"]


def test_demo_is_separate_from_real_data(client):
    token = setup_admin(client)
    response = client.post("/api/start", json={"choice": "demo"}, headers={"X-CSRF-Token": token})
    assert response.json()["demo"]["exists"] is True
    real = client.get("/api/overview", params={"start": "2026-10-01", "end": "2026-11-01", "dataset": "real"}).json()
    assert real["properties"] == []
    start, end = example_month(date.today())
    demo = client.get("/api/overview", params={"start": start.isoformat(), "end": end.isoformat(), "dataset": "demo"}).json()
    assert demo["indicators"]["operating_balance"]["value"] == 80000
    assert {p["name"] for p in demo["properties"]} == {"Appartement A", "Studio B"}


def test_unknown_property_is_refused_not_leaked(client):
    setup_admin(client)
    response = client.get("/api/overview", params={"start": "2026-10-01", "end": "2026-11-01", "property_id": "prop-guessed"})
    assert response.status_code == 403 and response.json()["code"] == "forbidden_property"


def test_security_headers_and_no_store(client):
    response = client.get("/")
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-frame-options"] == "DENY"
    assert client.get("/api/session").headers["cache-control"] == "no-store"


def test_errors_are_translated(client):
    token = csrf(client)
    response = client.post("/api/auth/setup", json={"username": "a", "password": PASSWORD, "confirm": PASSWORD, "lang": "en"},
                           headers={"X-CSRF-Token": token})
    assert response.json()["message"].startswith("User name")


def test_interface_calls_only_existing_routes(client):
    """QUA 01: every API path used by the interface is served by the application."""
    import re
    from pathlib import Path

    static = Path(__file__).resolve().parents[1] / "src" / "rental_cockpit" / "static" / "js"
    used = set()
    for path in static.rglob("*.js"):
        used |= set(re.findall(r'"(/api/[a-z_/]+)"', path.read_text(encoding="utf-8")))
    served = {route.path for route in client.app.routes}
    assert used and used <= served, used - served
