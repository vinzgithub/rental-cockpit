# Copyright © 2026 Vincent Fournet
"""QUA 02: the Overview and the lists stay fast with many fictional records.

The reference measurements (10 000 entries, 2 000 stays) are in the acceptance
documentation; this test keeps a smaller data set and wide margins, so it
catches a computation that grows with the square of the data, not a slow machine.
"""
from __future__ import annotations

import random
import time
from datetime import date, timedelta

from rental_cockpit.engine import stays as stay_views
from rental_cockpit.engine.indicators import compute
from rental_cockpit.engine.ledger import Ledger
from rental_cockpit.engine.schema import empty_registry


def test_overview_and_stays_list_grow_linearly():
    rng = random.Random(7)
    data = empty_registry()
    ledger = Ledger(data, "perf")
    props = [ledger.create_property({"name": f"Bien {i}"})["property"]["id"] for i in range(3)]
    first = date(2023, 1, 1)
    for i in range(900):
        start = first + timedelta(days=(i // 3) * 4)
        ledger.create_stay({"property_id": props[i % 3], "start": start.isoformat(), "end": (start + timedelta(days=3)).isoformat(),
                            "amounts": {"gross": str(rng.randint(200, 900)), "commission": "30"}})
    for i in range(6000):
        day = first + timedelta(days=rng.randint(0, 1000))
        ledger.create_entry({"property_id": props[i % 3], "kind": "expense", "category_id": "cleaning", "label": f"Dépense {i}",
                             "amount": str(rng.randint(10, 300)), "date": day.isoformat(), "paid": i % 2 == 0, "paid_date": day.isoformat()})
    started = time.perf_counter()
    result = compute(data, property_ids=set(props), start=date(2024, 1, 1), end=date(2025, 1, 1), lang="fr", today=date(2026, 11, 1))
    assert result["indicators"]["operating_expenses"]["value"] > 0
    received = stay_views.received_by_stay(data)
    rows = [stay_views.summary(data, s, date(2026, 11, 1), "fr", received) for s in data["stays"].values()]
    assert len(rows) == 900
    assert time.perf_counter() - started < 3
