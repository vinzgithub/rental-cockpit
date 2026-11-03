# Copyright © 2026 Vincent Fournet
"""Delivery L2 in a real browser: the fictional Airbnb export, from the file to the undo."""
from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def open_import(page):
    page.locator('.pagehead [data-action="import"]').click()
    page.locator("dialog[open] .imp-kinds").wait_for()


def check(page, path):
    page.locator('dialog[open] [data-k="file"]').set_input_files(str(path))
    page.locator('dialog[open] [data-k="check"]').click()
    page.locator("dialog[open] .imp-file").wait_for()


def wait_preview(page):
    page.wait_for_timeout(150)
    page.locator('dialog[open] [data-k="apply"]:has-text("…")').wait_for(state="detached")


def test_airbnb_file_preview_import_and_undo(desktop, base_url, tmp_path):
    page = desktop
    page.goto(base_url + "/")
    page.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    for name in ("Gîte d'essai", "Studio d'essai"):
        page.locator('[data-action="add-property"]').first.click()
        page.locator("#rc-p-name").fill(name)
        page.locator("dialog[open] [data-save]").click()
        page.locator("dialog[open]").wait_for(state="detached")
    page.locator('.sidebar [data-value="sejours"]').click()

    open_import(page)
    check(page, FIXTURES / "airbnb_fr.csv")
    # Two properties: nothing is attached to a listing until the person chooses.
    assert page.locator('dialog[open] [data-k="apply"]').is_disabled()
    assert "1 versement(s) Airbnb" in page.locator("dialog[open] .tip").first.text_content()
    page.locator('dialog[open] [data-k="listing-0"]').select_option(label="Gîte d'essai")
    wait_preview(page)
    page.locator('dialog[open] [data-k="listing-1"]').select_option(label="Studio d'essai")
    wait_preview(page)
    error = page.locator("dialog[open] .imp-row.error")
    assert "2 nuits indiquées, 3 d'après les dates" in error.text_content()
    first = page.locator("dialog[open] .imp-row:not(.op)", has_text="HMTEST0001")
    assert "Versement de 510,00 € envoyé le 5 oct. 2026" in first.text_content().replace(" ", " ").replace("\xa0", " ")
    apply = page.locator('dialog[open] [data-k="apply"]')
    assert apply.text_content().strip() == "Importer 3 séjours, 1 recette ou dépense et 2 versements"

    # A line can be left out before confirming.
    second = page.locator("dialog[open] .imp-row", has_text="HMTEST0002")
    second.locator("select").select_option("skip")
    wait_preview(page)
    assert apply.text_content().strip() == "Importer 2 séjours, 1 recette ou dépense et 2 versements"
    page.locator("dialog[open] .imp-row", has_text="HMTEST0002").locator("select").select_option("import")
    wait_preview(page)
    apply.click()
    page.locator("dialog[open] .imp-done").wait_for()
    assert [v.strip() for v in page.locator("dialog[open] .facts-list dd").all_text_contents()] == ["3", "0", "0", "2", "1"]
    page.locator('dialog[open] [data-k="see"]').click()
    page.locator(".stays-list tbody tr").nth(2).wait_for()
    assert page.locator(".stays-list tbody tr").count() == 3

    # The same file again: the listings are remembered and nothing is new.
    open_import(page)
    check(page, FIXTURES / "airbnb_fr.csv")
    assert page.locator('dialog[open] [data-k="apply"]').text_content().strip() == "Rien à importer"
    assert "déjà été importé" in page.locator("dialog[open] .tip").first.text_content()
    page.locator('dialog[open] [data-k="back"]').click()
    page.locator('dialog[open] [data-k="history"]').click()
    history = page.locator("dialog[open]").last
    history.locator(".imp-hist").first.wait_for()
    history.locator("[data-undo]").click()
    page.locator("dialog[open] [data-confirm]").click()
    page.locator(".toast", has_text="Import annulé").wait_for()
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")
    page.locator(".stays-card .empty").wait_for()


def test_csv_columns_and_commission_rate(desktop, base_url, tmp_path):
    page = desktop
    page.goto(base_url + "/")
    page.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    page.locator(".kpi").first.wait_for()
    page.locator('.sidebar [data-value="sejours"]').click()
    csv = tmp_path / "plateforme.csv"
    csv.write_text("Arrivée;Départ;Montant;Dossier\n02/03/2027;05/03/2027;300,00;D-1\n", encoding="utf-8")
    open_import(page)
    page.locator('dialog[open] .imp-kind:has([data-k="kind-csv"])').click()
    check(page, csv)
    assert page.locator('dialog[open] [data-k="map-start"]').input_value() == "Arrivée"
    assert "Exemple : 02/03/2027" in page.locator("dialog[open] .imp-map").first.text_content()
    page.locator('dialog[open] [data-k="map-external_ref"]').select_option("Dossier")
    wait_preview(page)
    page.locator('dialog[open] [data-k="property"]').select_option(label="Gîte d'essai")
    wait_preview(page)
    page.locator('dialog[open] [data-k="rate"]').fill("15")
    page.locator('dialog[open] [data-k="rate"]').press("Enter")
    wait_preview(page)
    row = page.locator("dialog[open] .imp-row").first
    text = row.text_content().replace(" ", " ").replace("\xa0", " ")
    assert "D-1" in text and "Commission 45,00 €" in text and "15 % du montant brut" in text
    page.locator('dialog[open] [data-k="channel"]').select_option("booking")
    wait_preview(page)
    page.locator('dialog[open] [data-k="apply"]').click()
    page.locator("dialog[open] .imp-done").wait_for()
    page.locator('dialog[open] [data-k="see"]').click()
    row = page.locator(".stays-list tbody tr", has_text="D-1")
    row.wait_for()
    assert "Booking.com" in row.text_content()


def test_import_fits_a_phone(phone, base_url):
    phone.goto(base_url + "/")
    phone.locator('.bottomnav [data-value="sejours"]').click()
    open_import(phone)
    check(phone, FIXTURES / "airbnb_fr.csv")
    phone.locator("dialog[open] .imp-row").first.wait_for()
    widths = phone.evaluate("() => { const b = document.querySelector('dialog[open] .dbody'); return [b.scrollWidth, b.clientWidth]; }")
    assert widths[0] <= widths[1], widths
    footer = phone.locator("dialog[open] .dfoot").bounding_box()
    assert footer["y"] + footer["height"] <= 844


def test_airbnb_operations_and_cancelled_booking(desktop, base_url):
    """Acceptance ANO-001 and ANO-002: every payout explained, a late cancellation paid but without nights."""
    page = desktop
    page.goto(base_url + "/")
    page.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    page.locator('[data-action="add-property"]').first.click()
    page.locator("#rc-p-name").fill("Gîte d'essai")
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open]").wait_for(state="detached")
    page.locator('.sidebar [data-value="sejours"]').click()
    open_import(page)
    check(page, FIXTURES / "airbnb_operations_fr.csv")
    rec = page.locator("dialog[open] .imp-rec")
    text = rec.inner_text().replace(" ", " ").replace("\xa0", " ")
    assert "11 versement(s) envoyé(s) par Airbnb" in text and "dont indemnisations (dommages, résolution)" in text
    assert "7,50 € versés par Airbnb ne seront pas enregistrés" in text
    aircover = page.locator("dialog[open] .imp-row.op", has_text="Versement de résolution")
    assert "Indemnisation" in aircover.inner_text() and "+ 95,00 €" in aircover.inner_text().replace("\xa0", " ").replace(" ", " ")
    # The cancelled booking is the one of five nights: the money is kept, the nights are not.
    cancelled = page.locator("dialog[open] .imp-row:not(.op)", has_text="HMFICT0101")
    assert "Annulé, montant encaissé conservé" in cancelled.locator("select").inner_text()
    cancelled.locator("select").select_option("cancelled")
    wait_preview(page)
    assert "ses nuits ne comptent pas" in page.locator("dialog[open] .imp-row:not(.op)", has_text="HMFICT0101").inner_text()
    unknown = page.locator("dialog[open] .imp-row.op", has_text="Remboursement de frais")
    unknown.locator("select").select_option("import")
    wait_preview(page)
    assert "Chaque somme versée par Airbnb" in page.locator("dialog[open] .imp-rec").inner_text()
    page.locator('dialog[open] [data-k="apply"]').click()
    page.locator("dialog[open] .imp-done").wait_for()
    page.locator('dialog[open] [data-k="see"]').click()
    page.locator('.sidebar [data-value="depenses"]').click()
    page.locator(".entries-list, .entry-card, .empty").first.wait_for()
    body = page.locator("main").inner_text()
    assert "Indemnisation Airbnb" in body and "Remboursement à un voyageur" in body
