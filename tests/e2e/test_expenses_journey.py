# Copyright © 2026 Vincent Fournet
"""Delivery L3 in a real browser: fictional expenses, a partial payment, a loan, the export and the categories.

Every date is in the past whatever day the tests run, so the figures do not
depend on the calendar.
"""
from __future__ import annotations

from .helpers import pick_period, show_view


def clean(text: str) -> str:
    return text.replace(" ", " ").replace("\xa0", " ")


def kpis(page) -> list[str]:
    page.wait_for_timeout(400)
    return [clean(text) for text in page.locator(".kpi .value").all_text_contents()]


def add_entry(page, *, category, label, amount, date, payment="unknown", kind="expense", split=None, months=None):
    page.locator(f'.pagehead [data-action="entry-new"][data-value="{kind}"]').click()
    page.locator("#rc-e-cat").select_option(category)
    page.locator("#rc-e-label").fill(label)
    page.locator("#rc-e-amount").fill(amount)
    page.locator("#rc-e-date").fill(date)
    page.locator(f'dialog[open] .pay-option:has(input[value="{payment}"])').click()
    for name, value in (split or {}).items():
        page.locator(f"#rc-e-{name}").fill(value)
    if months:
        page.locator('dialog[open] .check-line:has(input[name="repeat"])').click()
        page.locator("#rc-e-months").fill(str(months))
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open] .pill-row").wait_for()


def test_expenses_from_the_form_to_the_three_readings(desktop, base_url):
    page = desktop
    page.goto(base_url + "/")
    page.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    page.locator('[data-action="add-property"]').first.click()
    page.locator("#rc-p-name").fill("Gîte d'essai")
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open]").wait_for(state="detached")
    page.locator('.sidebar [data-value="depenses"]').click()

    add_entry(page, category="maintenance", label="Réparation chauffe-eau", amount="300", date="2026-10-10", payment="unpaid")
    assert "À payer" in page.locator("dialog[open] .pill-row").text_content()
    page.locator("dialog[open] [data-pay]").click()
    page.locator("#rc-ep-date").fill("2026-10-12")
    page.locator("#rc-ep-amount").fill("100")
    page.locator("dialog[open] [data-save]").last.click()
    page.locator("dialog[open] .pill-row .pill.amber").wait_for()
    facts = clean(page.locator("dialog[open] .money-facts").text_content())
    assert "Reste à payer200,00 €" in facts.replace("\n", "").replace("  ", "")
    # More than what is left is refused, with the amount in the message.
    page.locator("dialog[open] [data-pay]").click()
    page.locator("#rc-ep-amount").fill("250")
    page.locator("dialog[open] [data-save]").last.click()
    assert "200,00" in clean(page.locator("dialog[open] .error-box").last.text_content())
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")

    add_entry(page, category="loan", label="Mensualité de prêt", amount="500", date="2026-08-05", payment="unpaid",
              split={"principal": "350", "interest": "120", "insurance": "30"}, months=3)
    assert "Échéance 1 sur 3" in page.locator("dialog[open] .pill-row").text_content()
    page.keyboard.press("Escape")
    page.locator(".entries-list tbody tr", has_text="Échéance 3 sur 3").wait_for()
    page.locator('[data-action="entries-view"][data-value="to_pay"]').click()
    page.locator(".entries-list tbody tr").nth(3).wait_for()
    assert page.locator(".entries-list tbody tr").count() == 4  # the repair and three instalments

    # The export has the same filters as the screen, and opens in a spreadsheet.
    with page.expect_download() as download:
        page.locator('.pagehead a[download]').click()
    content = open(download.value.path(), encoding="utf-8-sig").read()
    assert content.splitlines()[0].startswith("Date;Bien;Type;Catégorie") and content.count("Mensualité de prêt") == 3

    page.locator('.sidebar [data-value="synthese"]').click()
    show_view(page, "analysis", "activity")
    pick_period(page, "m:2026-10")
    assert kpis(page) == ["-300 €", "0 €", "300 €"]
    beyond = clean(page.locator('section[aria-labelledby="rc-beyond"]').text_content())
    assert "Remboursements d'emprunt" in beyond and "500,00 €" in beyond and "capital 350,00 €" in beyond
    settle = clean(page.locator('section[aria-labelledby="rc-settle"]').text_content())
    assert "1 700,00 €" in settle  # 200 € of the repair + three instalments of 500 €
    page.locator('[data-action="mode"][data-value="cash"]').click()
    assert kpis(page) == ["-100 €", "0 €", "100 €"]


def test_categories_in_settings(desktop, base_url):
    page = desktop
    page.goto(base_url + "/")
    page.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    page.locator('.sidebar [data-value="reglages"]').click()
    page.locator('[data-action="category-new"]').click()
    page.locator("#rc-c-label").fill("Conciergerie")
    page.locator("dialog[open] [data-save]").click()
    row = page.locator(".cat-row", has_text="Conciergerie")
    row.wait_for()
    assert "Dépense d'exploitation" in row.text_content()
    page.locator('[data-action="category-edit"][data-value="energy"]').click()
    page.locator("#rc-c-label").fill("Électricité et eau")
    page.locator("dialog[open] [data-save]").click()
    page.locator(".cat-row", has_text="Électricité et eau").wait_for()
    assert "d'origine : Énergie" in page.locator(".cat-row", has_text="Électricité et eau").text_content()


def test_expenses_fit_a_phone(phone, base_url):
    phone.goto(base_url + "/")
    phone.locator('.bottomnav [data-value="depenses"]').click()
    phone.locator(".entries-list-cards .entry-card").first.wait_for()
    assert phone.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    phone.locator(".entries-list-cards .entry-card").first.click()
    phone.locator("dialog[open] .pill-row").wait_for()
    widths = phone.evaluate("() => { const b = document.querySelector('dialog[open] .dbody'); return [b.scrollWidth, b.clientWidth]; }")
    assert widths[0] <= widths[1], widths
