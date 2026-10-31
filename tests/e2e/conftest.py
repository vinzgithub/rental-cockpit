# Copyright © 2026 Vincent Fournet
"""Browser tests: a real server, a real Chromium, fictional data only.

They run in their own CI job (``pytest tests/e2e``) and are skipped when
Playwright is not installed. The server is reached through a made-up host
name on plain HTTP, like an installation on a home network: the browser then
treats the page as *not* secure, which is what the copy buttons must survive.
"""
from __future__ import annotations

import socket
import threading
import time

import pytest

sync_api = pytest.importorskip("playwright.sync_api")
uvicorn = pytest.importorskip("uvicorn")

from rental_cockpit.app import create_app  # noqa: E402
from rental_cockpit.config import Config  # noqa: E402

HOST = "rental-cockpit.test"
PASSWORD = "motdepasse-recette"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    app = create_app(Config(data_dir=tmp_path_factory.mktemp("data")))
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(200):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://{HOST}:{port}"
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=[f"--host-resolver-rules=MAP {HOST} 127.0.0.1"])
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def admin_state(browser, base_url, tmp_path_factory):
    """Creates the administrator once per module and keeps the signed-in session."""
    context = browser.new_context(locale="fr-FR", viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(base_url + "/")
    page.locator("#rc-u").fill("camille")
    page.locator("#rc-d").fill("Camille")
    page.locator("#rc-p").fill(PASSWORD)
    page.locator("#rc-c").fill(PASSWORD)
    page.locator("form [type=submit]").click()
    page.locator('[data-action="start"][data-value="demo"]').click()
    page.locator(".kpi").first.wait_for()
    path = tmp_path_factory.mktemp("state") / "state.json"
    context.storage_state(path=str(path))
    context.close()
    return str(path)


@pytest.fixture
def desktop(browser, admin_state):
    context = browser.new_context(locale="fr-FR", viewport={"width": 1440, "height": 900}, storage_state=admin_state)
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    yield page
    context.close()
    assert not errors, errors


@pytest.fixture
def phone(browser, admin_state):
    context = browser.new_context(locale="fr-FR", viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
                                  storage_state=admin_state)
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    yield page
    context.close()
    assert not errors, errors
