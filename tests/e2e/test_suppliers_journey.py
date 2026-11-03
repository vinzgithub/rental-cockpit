# Copyright © 2026 Vincent Fournet
"""Delivery L4 in a real browser: a supplier with indicative rates, a detailed
invoice of 150 € split between two stays, then reconciled with the cleanings
typed by hand after each departure — and counted once, never twice.

Every date is in the past whatever day the tests run (fictional data only).
"""
from __future__ import annotations


def clean(text: str) -> str:
    return " ".join(text.replace(" ", " ").replace("\xa0", " ").split())


def add_stay(page, *, start, end, label, gross, commission):
    page.locator('.pagehead [data-action="stay-new"]').click()
    page.locator("#rc-s-start").fill(start)
    page.locator("#rc-s-end").fill(end)
    page.locator("#rc-s-label").fill(label)
    page.locator("#rc-s-gross").fill(gross)
    page.locator("#rc-s-commission").fill(commission)
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open] .pill-row").wait_for()
    page.keyboard.press("Escape")
    page.locator("dialog[open]").wait_for(state="detached")


def add_cleaning(page, *, amount, date):
    page.locator('.pagehead [data-action="entry-new"][data-value="expense"]').click()
    page.locator("#rc-e-cat").select_option("cleaning")
    page.locator("#rc-e-label").fill("Ménage de départ")
    page.locator("#rc-e-amount").fill(amount)
    page.locator("#rc-e-date").fill(date)
    page.locator('dialog[open] .pay-option:has(input[value="paid"])').click()
    page.locator("#rc-e-paydate").fill(date)
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open] .pill-row").wait_for()
    page.keyboard.press("Escape")
    page.locator("dialog[open]").wait_for(state="detached")


def fill_line(row, *, kind, date, quantity="", unit="", amount=""):
    row.locator("[data-l=kind]").select_option(kind)
    if quantity:
        row.locator("[data-l=quantity]").fill(quantity)
    if unit:
        row.locator("[data-l=unit]").select_option(unit)
    if amount:
        row.locator("[data-l=amount]").fill(amount)
    row.locator("[data-l=intervention_date]").fill(date)


def expenses_total(page, base_url) -> int:
    """What the Dépenses screen totals, asked from the page itself (same session, same data)."""
    return page.evaluate("async () => (await (await fetch('/api/entries?view=all')).json()).totals.expenses")


def test_supplier_invoice_split_and_reconciled(desktop, base_url):
    page = desktop
    page.goto(base_url + "/")
    page.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    page.locator('[data-action="add-property"]').first.click()
    page.locator("#rc-p-name").fill("Gîte d'essai")
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open]").wait_for(state="detached")

    page.locator('.sidebar [data-value="sejours"]').click()
    add_stay(page, start="2026-09-28", end="2026-10-04", label="Séjour A", gross="600", commission="90")
    add_stay(page, start="2026-10-10", end="2026-10-13", label="Séjour B", gross="300", commission="45")
    page.locator('.sidebar [data-value="depenses"]').click()
    add_cleaning(page, amount="45", date="2026-10-04")
    add_cleaning(page, amount="35", date="2026-10-13")
    assert expenses_total(page, base_url) == 8000

    # A supplier with two indicative rates.
    page.locator('.sidebar [data-value="prestataires"]').click()
    page.locator(".empty", has_text="Aucun prestataire").wait_for()
    page.locator('.pagehead [data-action="supplier-new"]').click()
    page.locator("#rc-sp-name").fill("Ménage Essai")
    page.locator("#rc-sp-role").fill("Ménage et linge")
    page.locator('dialog[open] .check-line:has(input[value="cleaning"])').click()
    page.locator('dialog[open] .check-line:has(input[value="linen"])').click()
    for kind, unit, price in (("cleaning", "hour", "25"), ("linen", "set", "10")):
        page.locator("dialog[open] [data-rate-add]").click()
        rate = page.locator("dialog[open] [data-rate]").last
        rate.locator("[data-r=kind]").select_option(kind)
        rate.locator("[data-r=unit]").select_option(unit)
        rate.locator("[data-r=unit_price]").fill(price)
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open] [data-invoice]").wait_for()
    assert "25,00 €" in clean(page.locator("dialog[open] .dbody").text_content())

    # A detailed invoice: 4 h of cleaning, 4 sets of linen and a trip. The rates pre-fill the prices.
    page.locator("dialog[open] [data-invoice]").click()
    page.locator("dialog[open] h2", has_text="Nouvelle facture").wait_for()
    page.locator("#rc-e-label").fill("Facture Ménage Essai F-018")
    page.locator("#rc-e-amount").fill("150")
    page.locator("#rc-e-date").fill("2026-10-20")
    page.locator("#rc-e-inv").fill("F-018")
    page.locator('dialog[open] .pay-option:has(input[value="unpaid"])').click()
    assert page.locator("#rc-e-cat").input_value() == "cleaning"  # the supplier's usual category
    rows = page.locator("dialog[open] .svc-line")
    fill_line(rows.nth(0), kind="cleaning", quantity="4", unit="hour", date="2026-10-04")
    assert rows.nth(0).locator("[data-l=unit_price]").input_value() == "25"
    page.locator("dialog[open] [data-line-add]").click()
    fill_line(rows.nth(1), kind="linen", quantity="4", unit="set", date="2026-10-13")
    assert rows.nth(1).locator("[data-l=unit_price]").input_value() == "10"
    page.locator("dialog[open] [data-line-add]").click()
    fill_line(rows.nth(2), kind="travel", amount="10", date="2026-10-13")
    assert "le détail correspond à la facture" in page.locator("[data-lines-total]").text_content()
    # The reason field only appears for an adjustment.
    assert rows.nth(2).locator("[data-note-field]").is_hidden()
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open] [data-split]").wait_for()
    assert expenses_total(page, base_url) == 23000  # nothing reconciled yet: 45 + 35 + 150

    # Split: each service goes to the stay whose departure is the day of the intervention.
    page.locator("dialog[open] [data-split]").click()
    page.locator("dialog[open] [data-alloc]").first.wait_for()
    selected = [clean(s.evaluate("e => e.selectedOptions[0].textContent")) for s in page.locator("dialog[open] [data-a=stay]").all()]
    assert [s.split(" · ")[0] for s in selected] == ["Séjour A", "Séjour B", "Séjour B"]
    assert clean(page.locator("dialog[open] [data-total]").last.text_content()) == "150,00 € répartis sur 150,00 €"
    page.locator("dialog[open] [data-save]").last.click()
    page.locator("dialog[open] .split-row small.done").nth(2).wait_for()
    assert expenses_total(page, base_url) == 23000  # a split never adds a charge

    # Reconcile with the two cleanings typed by hand: their payments move to the invoice.
    page.locator("dialog[open] [data-reconcile]").click()
    page.locator("dialog[open] .keyrow.pick").nth(1).wait_for()
    assert page.locator("dialog[open] .keyrow.pick").count() == 2
    for box in page.locator("dialog[open] .keyrow.pick").all():
        box.click()
    assert clean(page.locator("dialog[open] [data-total]").last.text_content()) == \
        "80,00 € rapprochés sur 150,00 € · 70,00 € restent propres à la facture"
    page.locator("dialog[open] [data-save]").last.click()
    page.locator("dialog[open] [data-unreconcile]").nth(1).wait_for()
    facts = clean(page.locator("dialog[open] .money-facts").first.inner_text())
    assert "Déjà payé 80,00 €" in facts and "Reste à payer 70,00 €" in facts
    assert expenses_total(page, base_url) == 15000  # counted once
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")

    # The stay shows the costs it was given and its margin.
    page.locator('.sidebar [data-value="sejours"]').click()
    page.locator('[data-action="stays-view"][data-value="all"]').click()
    page.locator(".stays-list tbody tr", has_text="Séjour A").click()
    page.locator("dialog[open] .pill-row").wait_for()
    body = clean(page.locator("dialog[open] .dbody").inner_text())
    assert "Coûts affectés à ce séjour" in body and "Facture Ménage Essai F-018" in body
    assert "Coûts affectés − 100,00 €" in body and "Marge après coûts 410,00 €" in body
    page.keyboard.press("Escape")

    # Undo one reconciliation: the cleaning of 4 October comes back with its payment.
    page.locator('.sidebar [data-value="prestataires"]').click()
    page.locator(".supplier-card").first.click()
    page.locator("dialog[open] .keyrow.clickable", has_text="F-018").click()
    page.locator("dialog[open] [data-unreconcile]").first.click()
    page.locator("dialog[open] [data-confirm]", has_text="Rétablir la saisie").click()
    page.wait_for_function("() => document.querySelectorAll('dialog[open] [data-unreconcile]').length === 1")
    assert expenses_total(page, base_url) == 19500
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
    page.locator(".supplier-card", has_text="115,00 € à payer").wait_for()

    # From the supplier's page to its expenses.
    page.locator(".supplier-card").first.click()
    page.locator("dialog[open] .linkbtn", has_text="Les retrouver dans Dépenses").click()
    page.locator("dialog[open]").wait_for(state="detached")
    page.locator(".entries-list tbody tr", has_text="F-018").wait_for()
    assert page.locator('[data-input="entries-q"]').input_value() == "Ménage Essai"


def test_suppliers_fit_a_phone(phone, base_url):
    """The demo's detailed invoice (150 € split between two stays), from the supplier to the split, on a phone."""
    phone.goto(base_url + "/")
    phone.locator(".banner").wait_for()  # this browser still shows the demo
    phone.locator('.bottomnav [data-value="prestataires"]').click()
    phone.locator(".supplier-card").first.wait_for()
    assert phone.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    phone.locator(".supplier-card", has_text="Prestataire Démo").click()
    phone.locator("dialog[open] [data-invoice]").wait_for()
    for step in ("supplier", "invoice", "split"):
        widths = phone.evaluate("() => { const b = [...document.querySelectorAll('dialog[open] .dbody')].at(-1); return [b.scrollWidth, b.clientWidth]; }")
        assert widths[0] <= widths[1], (step, widths)
        if step == "supplier":
            phone.locator("dialog[open] .keyrow.clickable", has_text="F-DEMO-018").click()
            phone.locator("dialog[open] [data-split]").wait_for()
        elif step == "invoice":
            assert phone.locator("dialog[open] .split-row small.done").count() == 3
            phone.locator("dialog[open] [data-split]").click()
            phone.locator("dialog[open] [data-alloc]").first.wait_for()
            assert phone.locator("dialog[open] [data-alloc]").count() == 6
    phone.keyboard.press("Escape")
    # The invoice form, with its service lines, on a phone.
    phone.locator("dialog[open]").last.locator("[data-edit]").click()
    phone.locator("dialog[open] .svc-line").first.wait_for()
    widths = phone.evaluate("() => { const b = [...document.querySelectorAll('dialog[open] .dbody')].at(-1); return [b.scrollWidth, b.clientWidth]; }")
    assert widths[0] <= widths[1], widths
