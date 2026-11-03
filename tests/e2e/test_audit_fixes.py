# Copyright © 2026 Vincent Fournet
"""Fixes from the 0.1.0 audit, checked in a real browser (0.1.1)."""
from __future__ import annotations

from .helpers import show_view


def test_menu_only_lists_working_screens(desktop, base_url):
    desktop.goto(base_url + "/")
    desktop.locator(".kpi").first.wait_for()
    labels = [text.strip() for text in desktop.locator(".sidebar .navbtn").all_text_contents()]
    assert labels == ["Synthèse", "Séjours", "Dépenses", "Prestataires", "Justificatifs", "Réglages"]


def test_demo_and_own_data_are_one_click_apart(desktop, base_url):
    desktop.goto(base_url + "/")
    desktop.locator(".banner").wait_for()  # the demo is shown
    desktop.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    desktop.locator(".banner").wait_for(state="detached")
    desktop.locator('.sidebar [data-action="dataset"][data-value="demo"]').click()
    desktop.locator(".banner").wait_for()
    assert desktop.locator('.sidebar [data-value="demo"]').get_attribute("aria-pressed") == "true"


def test_explanation_fits_a_phone(phone, base_url):
    phone.goto(base_url + "/")
    phone.locator(".kpi").first.wait_for()
    show_view(phone, "analysis", "activity")
    phone.locator('[data-action="explain"][data-value="operating_balance"]').click()
    phone.locator("dialog[open] .lines").wait_for()
    overflow = phone.evaluate("""() => {
        const body = document.querySelector('dialog[open] .dbody');
        const lines = document.querySelector('dialog[open] .lines-wrap');
        return [body.scrollWidth - body.clientWidth, lines.scrollWidth - lines.clientWidth];
    }""")
    assert overflow == [0, 0]


def test_bell_opens_the_things_to_check(phone, base_url):
    phone.goto(base_url + "/")
    phone.locator(".kpi").first.wait_for()
    phone.locator('[data-action="alerts"]').click()
    dialog = phone.locator("dialog[open]")
    dialog.wait_for()
    assert "À vérifier" in dialog.text_content()
    # Every item that leads somewhere leads to a screen of the menu.
    targets = {link.get_attribute("data-value") for link in dialog.locator('[data-action="go"]').all()}
    assert targets <= {"synthese", "sejours", "depenses", "reglages"}
    # « Paiements à confirmer » opens the expenses whose payment is unknown.
    dialog.locator('[data-action="go"][data-value="depenses"]').click()
    phone.locator('[data-action="entries-view"][data-value="to_confirm"][aria-selected="true"]').wait_for()
    phone.locator(".entries-list-cards .entry-card").first.wait_for()


def test_copy_works_on_plain_http(desktop, base_url):
    desktop.goto(base_url + "/")
    desktop.locator('.sidebar [data-value="reglages"]').click()
    desktop.locator('[data-action="copy"]').click()
    toast = desktop.locator(".toast").last
    toast.wait_for()
    assert "Copié" in toast.text_content() or "Ctrl+C" in toast.text_content()


def test_copy_by_hand_is_offered_on_plain_http(desktop, base_url):
    """Acceptance ERGO-005: on http://, the manual copy is said next to the secret, before trying."""
    page = desktop
    page.goto(base_url + "/")
    assert page.evaluate("() => window.isSecureContext") is False  # the test server is reached by name, over http
    page.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    page.locator('.sidebar [data-value="reglages"]').click()
    page.locator('[data-action="user-new"]').click()
    note = page.locator("dialog[open] .copy-manual")
    note.wait_for()
    assert "HTTPS" in note.inner_text()
    page.locator("dialog[open] [data-copy]").click()
    toast = page.locator(".toast").last
    toast.wait_for()
    assert "Copié" in toast.text_content() or "Ctrl+C" in toast.text_content()
    page.keyboard.press("Escape")
    page.locator('[data-action="key-new"]').click()
    page.locator("dialog[open] [data-submit]").click()
    page.locator("dialog[open] .codebox code").wait_for()
    assert page.locator("dialog[open] .copy-manual").is_visible()
    assert page.locator("dialog[open] .codebox code").evaluate("el => getComputedStyle(el).userSelect") == "all"


SCREENS = {"synthese", "sejours", "depenses", "prestataires", "justificatifs", "reglages"}


def test_every_link_and_alert_leads_somewhere(desktop, base_url):
    """Acceptance ERGO-006: no button promises a screen that does not exist; each alert opens its list."""
    page = desktop
    page.goto(base_url + "/")
    page.locator(".kpi").first.wait_for()
    for screen in sorted(SCREENS):
        page.evaluate(f"() => document.querySelector('[data-action=nav][data-value={screen}]').click()")
        page.wait_for_timeout(500)
        targets = set(page.evaluate("() => [...document.querySelectorAll('[data-action=go], [data-action=nav]')].map(b => b.dataset.value)"))
        assert targets <= SCREENS, (screen, targets - SCREENS)
        text = page.locator("body").inner_text().casefold()
        assert "bientôt" not in text and "coming soon" not in text, screen
    page.evaluate("() => document.querySelector('[data-action=nav][data-value=synthese]').click()")
    page.locator(".kpi").first.wait_for()
    count = page.locator('section[aria-labelledby="rc-check"] .check').count()
    for index in range(count):
        item = page.locator('section[aria-labelledby="rc-check"] .check').nth(index)
        target, view = item.get_attribute("data-value"), item.get_attribute("data-view")
        item.click()
        page.locator(f'.sidebar [data-value="{target}"][aria-current="page"]').wait_for()
        if view:
            page.locator(f'[data-view="{view}"][aria-selected="true"], [data-value="{view}"][aria-selected="true"]').first.wait_for()
        page.evaluate("() => document.querySelector('[data-action=nav][data-value=synthese]').click()")
        page.locator(".kpi").first.wait_for()
