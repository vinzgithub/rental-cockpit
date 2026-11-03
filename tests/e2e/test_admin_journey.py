# Copyright © 2026 Vincent Fournet
"""Version 1.0 in a real browser: a reader account with a temporary password, then a backup
downloaded and restored with the confirmation word. Fictional data only."""
from __future__ import annotations

from pathlib import Path


def test_reader_backup_and_restore(desktop, browser, base_url, tmp_path):
    page = desktop
    page.goto(base_url + "/")
    page.locator('.sidebar [data-action="dataset"][data-value="real"]').click()
    page.locator('[data-action="add-property"]').first.click()
    page.locator("#rc-p-name").fill("Gîte d'essai")
    page.locator("dialog[open] [data-save]").click()
    page.locator("dialog[open]").wait_for(state="detached")
    page.locator('.sidebar [data-value="reglages"]').click()
    page.locator("#rc-set-users").wait_for()

    # A reader with a temporary password, the property open, its PDFs too.
    page.locator('[data-action="user-new"]').click()
    page.locator("#rc-us-name").fill("comptable")
    page.locator("#rc-us-display").fill("Cabinet comptable")
    temporary = page.locator("#rc-us-pwd").input_value()
    assert len(temporary) >= 14
    row = page.locator("dialog[open] [data-property]", has_text="Gîte d'essai")
    assert row.locator("[data-g=pdf]").is_disabled()
    row.locator("[data-g=see]").check()
    row.locator("[data-g=pdf]").check()
    page.locator("dialog[open] [data-save]").click()
    page.locator(".user-row", has_text="Cabinet comptable").wait_for()
    assert "Mot de passe à choisir" in page.locator(".user-row", has_text="Cabinet comptable").inner_text()

    # Backup: created, checked and downloaded.
    with page.expect_download() as download:
        page.locator('[data-action="backup-create"]').click()
    archive = tmp_path / download.value.suggested_filename
    archive.write_bytes(Path(download.value.path()).read_bytes())
    page.locator(".backup-row").first.wait_for()

    # Restore: checked first, applied only with the word.
    page.locator('[data-action="backup-restore"]').click()
    page.locator("dialog[open] [data-zip]").set_input_files(str(archive))
    page.locator("dialog[open] [data-word]").wait_for()
    assert "Sauvegarde vérifiée" in page.locator("dialog[open] .tip.ok").inner_text()
    save = page.locator("dialog[open] [data-save]")
    page.locator("dialog[open] [data-word]").fill("remplacer")
    assert save.is_disabled()
    page.locator("dialog[open] [data-word]").fill("REMPLACER")
    save.click()
    done = page.locator("dialog[open] .tip.ok", has_text="Restauration terminée")
    done.wait_for()
    assert "totaux sont identiques" in done.inner_text() and "avant-restauration" in done.inner_text()
    page.keyboard.press("Escape")
    page.locator(".backup-row", has_text="avant-restauration").wait_for()

    # The reader's first sign-in asks for their own password, then opens the property.
    context = browser.new_context(locale="fr-FR", viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    reader = context.new_page()
    reader.goto(base_url + "/")
    reader.locator("#rc-u").fill("comptable")
    reader.locator("#rc-p").fill(temporary)
    reader.locator("form [type=submit]").click()
    reader.locator("#rc-n").wait_for()
    reader.locator("#rc-p").fill(temporary)
    reader.locator("#rc-n").fill("mot-de-passe-lecteur")
    reader.locator("#rc-c").fill("mot-de-passe-lecteur")
    reader.locator("form [type=submit]").click()
    reader.locator(".kpi").first.wait_for()
    assert reader.evaluate("() => document.documentElement.scrollWidth <= window.innerWidth")
    context.close()
