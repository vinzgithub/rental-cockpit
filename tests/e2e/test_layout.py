# Copyright © 2026 Vincent Fournet
"""No screen is wider than the window, from a 360-pixel phone to a wide computer (UX 07)."""
from __future__ import annotations

SCREENS = ("synthese", "sejours", "depenses", "prestataires", "justificatifs", "reglages")
WIDTHS = (360, 414, 600, 768, 900, 1024, 1100, 1280, 1440)


def test_no_horizontal_scrolling_at_any_width(desktop, base_url):
    page = desktop
    page.goto(base_url + "/")
    page.locator(".kpi").first.wait_for()
    problems = []
    for width in WIDTHS:
        page.set_viewport_size({"width": width, "height": 900})
        for screen in SCREENS:
            page.evaluate(f"() => document.querySelector('[data-action=nav][data-value={screen}]').click()")
            page.wait_for_timeout(350)
            over = page.evaluate("""() => { const main = document.querySelector('.main');
                return Math.max(document.documentElement.scrollWidth - window.innerWidth, main.scrollWidth - main.clientWidth); }""")
            if over > 0:
                problems.append(f"{screen} at {width}px: {over}px too wide")
    assert problems == []
