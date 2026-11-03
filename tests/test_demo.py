# Copyright © 2026 Vincent Fournet
"""The demo is fictional and reproduces the documented example (UX 02, T02, T03)."""
import json
from datetime import date

import pytest
from engine.demo import build_demo, example_month
from engine.indicators import compute


@pytest.mark.parametrize("today", [date(2026, 10, 31), date(2026, 11, 3), date(2027, 3, 21), date(2027, 1, 2)])
def test_example_month_shows_documented_figures(today):
    data = build_demo(today)
    start, end = example_month(today)
    pids = list(data["properties"])
    activity = compute(data, property_ids=pids, start=start, end=end, mode="activity", today=today)["indicators"]
    cash = compute(data, property_ids=pids, start=start, end=end, mode="cash", today=today)["indicators"]
    assert (activity["revenue"]["value"], activity["operating_expenses"]["value"], activity["operating_balance"]["value"]) == (100000, 20000, 80000)
    assert cash["balance_after_financing"]["value"] == 60000


def test_demo_contains_no_real_looking_personal_data():
    text = json.dumps(build_demo(date(2026, 10, 31)), ensure_ascii=False).lower()
    for forbidden in ("@", "http", "iban", "rue ", "avenue", "boulevard", "chemin "):
        assert forbidden not in text


def test_upcoming_stays_are_in_the_future():
    today = date(2026, 10, 31)
    data = build_demo(today)
    result = compute(data, property_ids=list(data["properties"]), start=date(2026, 10, 1), end=date(2026, 11, 1), today=today)
    assert result["upcoming_stays"] and all(stay["end"] > today.isoformat() for stay in result["upcoming_stays"])


def test_month_to_month_change_comes_from_the_data():
    """The previous month is ordinary fictional activity: the change shown is computed from it."""
    today = date(2026, 10, 31)
    data = build_demo(today)
    start, end = example_month(today)
    pids = list(data["properties"])
    result = compute(data, property_ids=pids, start=start, end=end, today=today)
    previous = compute(data, property_ids=pids, start=date(2026, 9, 1), end=date(2026, 10, 1), today=today, compare=False)
    for key in ("revenue", "operating_expenses", "operating_balance"):
        assert result["previous"]["values"][key] == previous["indicators"][key]["value"]
    assert previous["indicators"]["revenue"]["value"] > 0 and previous["indicators"]["nights"]["value"] > 0


def test_demo_stays_never_overlap_and_one_spans_two_months():
    from datetime import date, timedelta

    from rental_cockpit.engine.demo import build_demo

    for today in (date(2026, 1, 10), date(2026, 10, 31), date(2027, 3, 2)):
        data = build_demo(today)
        for pid in data["properties"]:
            stays = sorted((s for s in data["stays"].values() if s["property_id"] == pid and s["status"] != "cancelled"),
                           key=lambda s: s["start"])
            assert all(nxt["start"] >= cur["end"] for cur, nxt in zip(stays, stays[1:], strict=False))
        spanning = [s for s in data["stays"].values()
                    if s["start"][:7] != (date.fromisoformat(s["end"]) - timedelta(days=1)).isoformat()[:7]]
        assert len(spanning) == 1
