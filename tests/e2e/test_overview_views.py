# Copyright © 2026 Vincent Fournet
"""Acceptance ERGO-001 to ERGO-004 in a real browser, on the demo (fictional data).

* the Overview opens on « Mon argent », with « Performance locative » and « Analyse comptable »
  one click away, and its figures add up as their labels say (TEST-E);
* the period picker works with the mouse, the keyboard and on a phone (TEST-D);
* every « Comment est calculé ce montant ? » fits a 360 and a 390-pixel phone, held upright or
  sideways, with one scroll only (TEST-F).
"""
from __future__ import annotations

import pytest

from .helpers import pick_period, show_view

FITS = """() => { const d = document.querySelector('dialog[open]'); const body = d.querySelector('.dbody');
  const wide = [...d.querySelectorAll('*')].filter(el => el.getBoundingClientRect().right > d.getBoundingClientRect().right + 1).length;
  const scrollers = [...d.querySelectorAll('.dbody *')].filter(el => { const s = getComputedStyle(el);
      return /(auto|scroll)/.test(s.overflowY) && el.scrollHeight > el.clientHeight + 1; }).length;
  return { sideways: body.scrollWidth - body.clientWidth, wide, scrollers }; }"""


def values(page, mode: str) -> dict[str, int]:
    """The figures of the demo's month shown, in cents, as the server computes them for a reading."""
    return page.evaluate("""async (mode) => {
        const session = await (await fetch('/api/session')).json();
        const start = session.demo.focus.start.slice(0, 7) + '-01';
        const [y, m] = start.split('-').map(Number);
        const end = m === 12 ? `${y + 1}-01-01` : `${y}-${String(m + 1).padStart(2, '0')}-01`;
        const params = new URLSearchParams({ dataset: 'demo', property_id: 'all', mode, start, end });
        const data = await (await fetch('/api/overview?' + params)).json();
        return Object.fromEntries(Object.entries(data.indicators).map(([k, v]) => [k, v.value])); }""", mode)


def open_demo(page, base_url):
    page.goto(base_url + "/")
    page.locator(".kpi").first.wait_for()
    if not page.locator(".banner").count():  # the demo is the dataset these tests read
        page.evaluate("() => document.querySelector('[data-action=dataset][data-value=demo]').click()")
        page.locator(".banner").wait_for()
        page.locator(".kpi").first.wait_for()


def test_views_say_what_they_add_up(desktop, base_url):
    page = desktop
    open_demo(page, base_url)
    # « Mon argent » first: money in, money out, balance; what is left to receive or pay is always shown.
    assert page.locator('[data-action="view"][aria-pressed="true"]').get_attribute("data-value") == "money"
    assert page.locator(".kpi .label").all_inner_texts() == ["Solde de la période", "Encaissé", "Payé"]
    assert page.locator('section[aria-labelledby="rc-settle"]').is_visible()
    money = values(page, "cash")
    assert money["cash_balance"] == money["cash_in"] - money["cash_out"]
    assert money["cash_out"] == money["operating_expenses"] + money["financing"] + money["taxes"] + money["investment"]
    # « Performance locative »: result = nights + other income − commissions − other expenses.
    show_view(page, "performance")
    assert page.locator(".kpi .label").all_inner_texts() == ["Résultat locatif", "Recettes des nuitées", "Commissions"]
    perf = values(page, "activity")
    assert perf["operating_balance"] == perf["stay_revenue"] + perf["other_income"] - perf["commissions"] - perf["other_expenses"]
    page.locator(".series-row").nth(11).wait_for()
    assert page.locator(".series-row").count() == 12
    assert "nuits" in page.locator('section[aria-labelledby="rc-occupancy"]').inner_text()
    # A month of the evolution opens that month.
    page.locator(".series-row").nth(2).click()
    page.locator('[data-period="overview"] .period-open', has_text="Mars").wait_for()
    # « Analyse comptable » keeps the three readings, with plain names.
    show_view(page, "analysis")
    assert page.locator('[data-action="mode"]').all_inner_texts() == ["Par nuit occupée", "Par date de séjour ou de facture", "Par date de paiement"]
    # The view chosen is remembered.
    page.reload()
    page.locator(".kpi").first.wait_for()
    assert page.locator('[data-action="view"][aria-pressed="true"]').get_attribute("data-value") == "analysis"


def test_period_picker_with_the_mouse_and_the_keyboard(desktop, base_url):
    page = desktop
    open_demo(page, base_url)
    trigger = page.locator('[data-period="overview"] .period-open')
    start = trigger.inner_text().strip()
    # Arrows: one month back and forth.
    page.locator('[data-period="overview"] [data-action="period-step"][data-value="-1"]').click()
    page.wait_for_timeout(300)
    assert trigger.inner_text().strip() != start
    page.locator('[data-period="overview"] [data-action="period-step"][data-value="1"]').click()
    page.wait_for_timeout(300)
    assert trigger.inner_text().strip() == start
    # Keyboard: Enter opens the panel on the month shown, Escape closes it and gives the focus back.
    trigger.focus()
    page.keyboard.press("Enter")
    page.locator(".period-panel").wait_for()
    assert page.evaluate("() => document.activeElement.getAttribute('aria-pressed')") == "true"
    page.keyboard.press("Escape")
    page.locator(".period-panel").wait_for(state="detached")
    assert page.evaluate("() => document.activeElement.classList.contains('period-open')")
    # Year arrows, a whole year, the current month, a free period.
    pick_period(page, "y:2025")
    assert trigger.inner_text().strip() == "Année 2025"
    trigger.click()
    page.locator('.period-panel [data-action="period-pick"]', has_text="Mois actuel").click()
    page.wait_for_timeout(300)
    trigger.click()
    page.locator('.period-panel input[name="from"]').fill("2026-09-10")
    page.locator('.period-panel input[name="to"]').fill("2026-10-09")
    page.locator('.period-panel [type="submit"]').click()
    page.wait_for_timeout(400)
    assert trigger.inner_text().strip() == "10 sept. 2026 → 9 oct. 2026"
    # A click elsewhere closes the panel.
    trigger.click()
    page.locator(".period-panel").wait_for()
    page.locator("h1").click()
    page.locator(".period-panel").wait_for(state="detached")


def test_expenses_use_the_same_picker(desktop, base_url):
    page = desktop
    open_demo(page, base_url)
    page.locator('.sidebar [data-value="depenses"]').click()
    control = page.locator('[data-period="entries"] .period-open')
    control.wait_for()
    assert control.inner_text().strip() == "Toutes les dates"
    assert page.locator('[data-period="entries"] [data-action="period-step"]').first.is_disabled()
    all_rows = page.locator(".entries-list tbody tr").count()
    pick_period(page, "y:2026", target="entries")
    assert control.inner_text().strip() == "Année 2026"
    pick_period(page, "m:2026-10", target="entries")
    page.wait_for_timeout(300)
    october = page.locator(".entries-list tbody tr").count()
    assert 0 < october <= all_rows
    pick_period(page, "all", target="entries")
    page.wait_for_timeout(300)
    assert page.locator(".entries-list tbody tr").count() == all_rows


def test_period_picker_on_a_phone(phone, base_url):
    open_demo(phone, base_url)
    phone.locator('[data-period="overview"] .period-open').click()
    panel = phone.locator(".period-panel")
    panel.wait_for()
    box, width = panel.bounding_box(), phone.viewport_size["width"]
    assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert all(b["height"] >= 44 for b in (m.bounding_box() for m in panel.locator(".pp-month").all()))
    assert phone.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    phone.locator('.period-panel [data-action="period-pick"]').nth(0).click()
    panel.wait_for(state="detached")


@pytest.mark.parametrize("size", [(360, 760), (390, 844), (760, 360)])
def test_every_explanation_fits_a_phone(browser, admin_state, base_url, size):
    width, height = size
    context = browser.new_context(locale="fr-FR", viewport={"width": width, "height": height}, is_mobile=True, has_touch=True,
                                  storage_state=admin_state)
    page = context.new_page()
    open_demo(page, base_url)
    problems = []
    for view, mode in (("money", None), ("performance", None), ("analysis", "activity"), ("analysis", "invoice"), ("analysis", "cash")):
        show_view(page, view, mode)
        ids = page.evaluate("() => [...new Set([...document.querySelectorAll('[data-action=explain]')].filter(b => b.offsetParent).map(b => b.dataset.value))]")
        assert len(ids) >= 3, (view, mode, ids)
        for indicator in ids:
            page.locator(f'[data-action="explain"][data-value="{indicator}"]').locator("visible=true").first.click()
            page.locator("dialog[open] .facts-list").wait_for()
            found = page.evaluate(FITS)
            if found != {"sideways": 0, "wide": 0, "scrollers": 0}:
                problems.append(f"{view}/{mode}/{indicator} at {width}×{height}: {found}")
            page.keyboard.press("Escape")
            page.locator("dialog[open]").wait_for(state="detached")
    context.close()
    assert problems == []
