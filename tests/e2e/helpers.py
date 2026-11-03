# Copyright © 2026 Vincent Fournet
"""Steps shared by the browser journeys: choosing a period, a view of the Overview, a reading."""
from __future__ import annotations


def pick_period(page, key: str, target: str = "overview") -> None:
    """Choose a period with the picker, as a person would: « m:2026-10 », « y:2026 » or « all »."""
    control = page.locator(f'[data-period="{target}"]').locator("visible=true").first
    control.locator(".period-open").click()
    panel = control.locator(".period-panel")
    panel.wait_for()
    if key != "all":
        year = int(key[2:6])
        while (shown := int(panel.locator(".pp-year b").inner_text())) != year:
            panel.locator(f'[data-action="period-year"][data-value="{1 if shown < year else -1}"]').click()
    panel.locator(f'[data-action="period-pick"][data-value="{key}"]').click()
    panel.wait_for(state="detached")
    page.wait_for_timeout(300)


def show_view(page, view: str, mode: str | None = None) -> None:
    """« Mon argent » (money), « Performance locative » (performance) or « Analyse comptable » (analysis)."""
    page.locator(f'[data-action="view"][data-value="{view}"]').click()
    page.locator(f'[data-action="view"][data-value="{view}"][aria-pressed="true"]').wait_for()
    if mode:
        page.locator(f'[data-action="mode"][data-value="{mode}"]').click()
        page.locator(f'[data-action="mode"][data-value="{mode}"][aria-pressed="true"]').wait_for()
    page.wait_for_timeout(300)
