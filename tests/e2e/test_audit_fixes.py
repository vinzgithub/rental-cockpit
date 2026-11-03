# Copyright © 2026 Vincent Fournet
"""Fixes from the 0.1.0 audit, checked in a real browser (0.1.1)."""
from __future__ import annotations


def test_menu_only_lists_working_screens(desktop, base_url):
    desktop.goto(base_url + "/")
    desktop.locator(".kpi").first.wait_for()
    labels = [text.strip() for text in desktop.locator(".sidebar .navbtn").all_text_contents()]
    assert labels == ["Synthèse", "Réglages"]


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
    # No item leads to a screen that does not exist yet.
    assert dialog.locator('[data-action="go"]').count() == 0


def test_copy_works_on_plain_http(desktop, base_url):
    desktop.goto(base_url + "/")
    desktop.locator('.sidebar [data-value="reglages"]').click()
    desktop.locator('[data-action="copy"]').click()
    toast = desktop.locator(".toast").last
    toast.wait_for()
    assert "Copié" in toast.text_content() or "Ctrl+C" in toast.text_content()
