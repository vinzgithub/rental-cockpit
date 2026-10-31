# Copyright © 2026 Vincent Fournet
"""Calculation rules of the specification (FIN 01–FIN 06, DON 06, T03)."""
from datetime import date

import pytest
from engine.indicators import compute, indicator_detail, previous_period
from engine.ledger import Ledger
from engine.schema import empty_registry

JUNE = (date(2026, 6, 1), date(2026, 7, 1))


@pytest.fixture
def book():
    data = empty_registry()
    led = Ledger(data, "tester")
    pid = led.create_property({"name": "Bien fictif"})["property"]["id"]
    return data, led, pid


def values(data, pid, mode="activity", period=JUNE):
    result = compute(data, property_ids=[pid], start=period[0], end=period[1], mode=mode, today=date(2026, 7, 15))
    return {key: item["value"] for key, item in result["indicators"].items()}, result


def test_documented_example_T03(book):
    """1 000 € revenue − 30 commission − 80 cleaning − 20 linen − 10 travel − 60 repair = 800 €;
    with a 200 € instalment and everything paid in the month, cash after financing is 600 €."""
    data, led, pid = book
    stay = led.create_stay({"property_id": pid, "start": "2026-06-10", "end": "2026-06-14",
                            "amounts": {"gross": "1000", "commission": "30", "payout": "970"}})["stay"]
    led.create_payment({"property_id": pid, "direction": "in", "date": "2026-06-11", "amount": "970",
                        "links": [{"type": "stay", "id": stay["id"], "amount": "970"}]})
    for category, amount in (("cleaning", "80"), ("linen", "20"), ("travel", "10"), ("maintenance", "60")):
        led.create_entry({"property_id": pid, "category_id": category, "label": category, "date": "2026-06-14", "amount": amount, "paid": True})
    led.create_entry({"property_id": pid, "category_id": "loan", "label": "Mensualité", "date": "2026-06-05", "amount": "200", "paid": True,
                      "loan_split": {"principal": "150", "interest": "40", "insurance": "10"}})

    activity, result = values(data, pid)
    assert activity["revenue"] == 100000
    assert activity["operating_expenses"] == 20000
    assert activity["operating_balance"] == 80000
    assert activity["financing"] == 20000
    assert result["indicators"]["financing"]["split"] == {"principal": 15000, "interest": 4000, "insurance": 1000, "unknown": 0}

    cash, _ = values(data, pid, "cash")
    assert cash["revenue"] == 97000            # net payout received, commission withheld at source
    assert cash["operating_balance"] == 80000
    assert cash["balance_after_financing"] == 60000


def test_stay_across_two_months_is_split_per_night(book):
    """Two nights in June, one in July: 300 € → 200 € + 100 €, never 300 € twice (FIN 03)."""
    data, led, pid = book
    led.create_stay({"property_id": pid, "start": "2026-06-29", "end": "2026-07-02", "amounts": {"gross": "300", "commission": "10"}})
    june, _ = values(data, pid)
    july, _ = values(data, pid, period=(date(2026, 7, 1), date(2026, 8, 1)))
    assert (june["revenue"], july["revenue"]) == (20000, 10000)
    assert june["operating_expenses"] + july["operating_expenses"] == 1000
    assert june["nights"] == 2 and july["nights"] == 1


def test_rounding_stays_exact_to_the_cent(book):
    data, led, pid = book
    led.create_stay({"property_id": pid, "start": "2026-06-30", "end": "2026-07-03", "amounts": {"gross": "100"}})
    june, _ = values(data, pid)
    july, _ = values(data, pid, period=(date(2026, 7, 1), date(2026, 8, 1)))
    assert june["revenue"] + july["revenue"] == 10000


def test_departure_day_is_not_a_night(book):
    data, led, pid = book
    led.create_stay({"property_id": pid, "start": "2026-06-10", "end": "2026-06-12", "amounts": {"gross": "180"}})
    june, _ = values(data, pid)
    assert june["nights"] == 2


def test_unknown_amount_is_not_zero(book):
    """FIN 05: a stay without amount makes the result incomplete instead of counting 0 silently."""
    data, led, pid = book
    led.create_stay({"property_id": pid, "start": "2026-06-10", "end": "2026-06-12"})
    _, result = values(data, pid)
    assert result["indicators"]["revenue"]["complete"] is False
    assert any(item["kind"] == "stays_without_amount" for item in result["to_check"])


def test_unpaid_expense_stays_out_of_cash(book):
    """FIN 05/FIN 06: no payment recorded means nothing left the account."""
    data, led, pid = book
    led.create_entry({"property_id": pid, "category_id": "maintenance", "label": "Réparation", "date": "2026-06-03", "amount": "60"})
    cash, result = values(data, pid, "cash")
    activity, _ = values(data, pid)
    assert activity["operating_expenses"] == 6000
    assert cash["operating_expenses"] == 0
    assert result["indicators"]["to_pay"]["value"] == 6000


def test_equipment_and_taxes_are_not_operating(book):
    data, led, pid = book
    led.create_entry({"property_id": pid, "category_id": "equipment", "label": "Lave-linge", "date": "2026-06-03", "amount": "450", "paid": True})
    led.create_entry({"property_id": pid, "category_id": "taxes", "label": "Taxe", "date": "2026-06-03", "amount": "100", "paid": True})
    activity, _ = values(data, pid)
    cash, _ = values(data, pid, "cash")
    assert activity["operating_expenses"] == 0 and activity["investment"] == 45000 and activity["taxes"] == 10000
    assert cash["balance_after_financing"] == -55000


def test_coverage_period_spreads_day_by_day(book):
    data, led, pid = book
    led.create_entry({"property_id": pid, "category_id": "insurance", "label": "Assurance", "date": "2026-01-01", "amount": "365",
                      "period_start": "2026-01-01", "period_end": "2027-01-01"})
    june, _ = values(data, pid)
    invoice, _ = values(data, pid, "invoice")
    assert june["operating_expenses"] == 3000       # 30 days × 1 €
    assert invoice["operating_expenses"] == 0       # invoice dated in January


def test_cancelled_stay_keeps_retained_amount_on_arrival_date(book):
    data, led, pid = book
    led.create_stay({"property_id": pid, "start": "2026-06-20", "end": "2026-06-25", "status": "cancelled", "amounts": {"gross": "120"}})
    june, _ = values(data, pid)
    assert june["revenue"] == 12000 and june["nights"] == 0


def test_service_invoice_is_counted_once_with_category_breakdown(book):
    """PRE 04 example: 150 € = 100 + 40 + 10, split 90/60 between two stays → one 150 € expense."""
    data, led, pid = book
    a = led.create_stay({"property_id": pid, "start": "2026-06-02", "end": "2026-06-05", "amounts": {"gross": "300"}})["stay"]["id"]
    b = led.create_stay({"property_id": pid, "start": "2026-06-08", "end": "2026-06-10", "amounts": {"gross": "200"}})["stay"]["id"]
    led.create_entry({"property_id": pid, "category_id": "cleaning", "label": "Facture", "date": "2026-06-20", "amount": "150",
                      "lines": [{"id": "m", "kind": "cleaning", "amount": "100"}, {"id": "l", "kind": "linen", "amount": "40"}, {"id": "d", "kind": "travel", "amount": "10"}],
                      "allocations": [{"line_id": "m", "stay_id": a, "amount": "60"}, {"line_id": "l", "stay_id": a, "amount": "24"}, {"line_id": "d", "stay_id": a, "amount": "6"},
                                      {"line_id": "m", "stay_id": b, "amount": "40"}, {"line_id": "l", "stay_id": b, "amount": "16"}, {"line_id": "d", "stay_id": b, "amount": "4"}]})
    june, result = values(data, pid)
    assert june["operating_expenses"] == 15000
    breakdown = {row["category_id"]: row["amount"] for row in result["by_category"]}
    assert breakdown == {"cleaning": 10000, "linen": 4000, "travel": 1000}


def test_detail_lines_add_up_to_the_indicator(book):
    data, led, pid = book
    led.create_stay({"property_id": pid, "start": "2026-06-29", "end": "2026-07-02", "amounts": {"gross": "300", "commission": "9"}})
    led.create_entry({"property_id": pid, "category_id": "cleaning", "label": "Ménage", "date": "2026-06-30", "amount": "40"})
    detail = indicator_detail(data, "operating_balance", property_ids=[pid], start=JUNE[0], end=JUNE[1], mode="activity", today=date(2026, 7, 15))
    lines = detail["indicator"]["lines"]
    assert sum(line["sign"] * line["share"] for line in lines) == detail["indicator"]["value"]
    assert all(line["rule"] for line in lines)


def test_hidden_property_never_leaks_into_totals(book):
    """SEC 02: totals only use the properties asked for."""
    data, led, pid = book
    other = led.create_property({"name": "Autre bien"})["property"]["id"]
    led.create_stay({"property_id": other, "start": "2026-06-10", "end": "2026-06-12", "amounts": {"gross": "500"}})
    june, result = values(data, pid)
    assert june["revenue"] == 0
    assert set(result["by_property"]) == {pid}


def test_previous_period():
    assert previous_period(date(2026, 1, 1), date(2026, 2, 1)) == (date(2025, 12, 1), date(2026, 1, 1))
    assert previous_period(date(2026, 1, 1), date(2027, 1, 1)) == (date(2025, 1, 1), date(2026, 1, 1))
