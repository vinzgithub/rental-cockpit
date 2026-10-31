# Copyright © 2026 Vincent Fournet
"""Delivery L1 in a real browser: a fictional stay, from the form to the three readings."""
from __future__ import annotations


def kpis(page) -> list[str]:
    page.wait_for_timeout(400)
    return [text.replace(" ", " ").replace("\xa0", " ") for text in page.locator(".kpi .value").all_text_contents()]


def test_stay_from_the_form_to_the_three_readings(desktop, base_url):
    page = desktop
    page.goto(base_url + "/")
    page.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    page.locator('[data-action="add-property"]').first.click()
    page.locator("#rc-p-name").fill("Gîte d'essai")
    page.locator("[data-save]").click()
    page.locator(".kpi").first.wait_for()

    page.locator('.sidebar [data-value="sejours"]').click()
    page.locator('.pagehead [data-action="stay-new"]').click()
    page.locator("#rc-s-start").fill("2026-09-28")
    page.locator("#rc-s-end").fill("2026-10-04")
    assert "3 nuits en septembre 2026" in page.locator("[data-nights]").text_content()
    page.locator("#rc-s-gross").fill("600")
    page.locator("#rc-s-commission").fill("90")
    page.locator("dialog [data-save]").click()
    rows = page.locator("dialog[open] table.breakdown tbody tr")
    rows.first.wait_for()
    assert rows.count() == 2
    page.keyboard.press("Escape")

    # Balance / revenue / expenses, as in the pull request.
    page.locator('.sidebar [data-value="synthese"]').click()
    page.locator('[data-change="period"]').select_option("m:2026-09")
    assert kpis(page) == ["255 €", "300 €", "45 €"]
    page.locator('[data-action="mode"][data-value="invoice"]').click()
    assert kpis(page) == ["510 €", "600 €", "90 €"]
    page.locator('[data-change="period"]').select_option("m:2026-10")
    page.locator('[data-action="mode"][data-value="cash"]').click()
    assert kpis(page) == ["0 €", "0 €", "0 €"]

    # « 1 versement à confirmer » leads to the stay, the payout fills the Cash reading.
    page.locator('.grid-2 .check[data-view="attention"]').first.click()
    page.locator(".stays-list tbody tr").first.click()
    page.locator("dialog[open] [data-payout]").click()
    page.locator("#rc-p-date").fill("2026-10-05")
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open] .pill-row .pill.teal").last.wait_for()
    page.keyboard.press("Escape")
    page.locator('.sidebar [data-value="synthese"]').click()
    assert kpis(page) == ["510 €", "510 €", "0 €"]


def test_stays_fit_a_phone(phone, base_url):
    phone.goto(base_url + "/")
    phone.locator('.bottomnav [data-value="sejours"]').click()
    card = phone.locator(".stays-list-cards .stay-card").first
    card.wait_for()
    card.click()
    phone.locator("dialog[open] .money-facts").wait_for()
    overflow = phone.evaluate("() => { const d = document.querySelector('dialog[open] .dbody'); return d.scrollWidth - d.clientWidth; }")
    assert overflow == 0
    assert phone.locator("dialog[open] [data-stay-edit]").is_visible()
