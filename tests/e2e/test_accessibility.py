# Copyright © 2026 Vincent Fournet
"""Accessibility (UX 07, T12): every screen and the main dialogs checked with axe-core, on a computer
and at 360 pixels wide, plus the absence of horizontal scrolling.

axe-core is not part of the application: the test uses it when ``AXE_PATH`` points to
``axe.min.js`` (the CI installs it) and is skipped otherwise.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

AXE = Path(os.environ.get("AXE_PATH", "node_modules/axe-core/axe.min.js"))
pytestmark = pytest.mark.skipif(not AXE.is_file(), reason="axe-core not installed (set AXE_PATH)")
SCREENS = ("synthese", "sejours", "depenses", "prestataires", "justificatifs", "reglages")


def violations(page) -> list[str]:
    if not page.evaluate("() => Boolean(window.axe)"):
        page.evaluate(AXE.read_text())
    found = page.evaluate("""async () => (await axe.run(document, { resultTypes: ['violations'] })).violations
        .map(v => `${v.id} (${v.impact}): ${v.nodes.slice(0, 2).map(n => n.target.join(' ')).join(' | ')}`)""")
    return found


def test_screens_and_dialogs_on_a_computer(desktop, base_url):
    page = desktop
    page.goto(base_url + "/")
    page.locator(".kpi").first.wait_for()
    # The first Tab reaches « Aller au contenu », which leads straight to the content.
    page.keyboard.press("Tab")
    assert page.evaluate("() => document.activeElement.className") == "skip-link"
    page.keyboard.press("Enter")
    assert page.evaluate("() => document.activeElement.id") == "rc-main"
    problems = []
    for screen in SCREENS:
        page.locator(f'.sidebar [data-value="{screen}"]').click()
        page.wait_for_timeout(700)
        problems += [f"{screen}: {v}" for v in violations(page)]
    page.locator('.sidebar [data-value="depenses"]').click()
    page.locator(".entries-list tbody tr").first.click()
    page.locator("dialog[open] .pill-row").wait_for()
    problems += [f"expense page: {v}" for v in violations(page)]
    page.keyboard.press("Escape")
    page.locator('.sidebar [data-value="justificatifs"]').click()
    page.locator('.pagehead [data-action="invoice-import"]').click()
    page.locator("dialog[open] [data-pdf]").wait_for(state="attached")
    problems += [f"invoice import: {v}" for v in violations(page)]
    page.keyboard.press("Escape")
    page.locator('.sidebar [data-value="reglages"]').click()
    page.locator('[data-action="user-new"]').click()
    page.locator("dialog[open] #rc-us-name").wait_for()
    problems += [f"reader form: {v}" for v in violations(page)]
    assert problems == []


def test_screens_at_360_pixels(browser, admin_state, base_url):
    context = browser.new_context(locale="fr-FR", viewport={"width": 360, "height": 780}, is_mobile=True, has_touch=True,
                                  storage_state=admin_state)
    page = context.new_page()
    page.goto(base_url + "/")
    page.locator(".kpi").first.wait_for()
    problems = []
    for screen in SCREENS:
        page.locator(f'.bottomnav [data-value="{screen}"]').click()
        page.wait_for_timeout(700)
        if page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth"):
            problems.append(f"{screen}: horizontal scrolling")
        problems += [f"{screen}: {v}" for v in violations(page)]
    context.close()
    assert problems == []
