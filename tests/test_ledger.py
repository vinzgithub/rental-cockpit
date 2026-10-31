# Copyright © 2026 Vincent Fournet
import pytest
from engine.errors import RCError
from engine.ledger import Ledger, allocation_remaining, entry_payment_status
from engine.schema import empty_registry


@pytest.fixture
def led():
    data = empty_registry()
    ledger = Ledger(data, "admin")
    ledger.pid = ledger.create_property({"name": "Bien"})["property"]["id"]
    return ledger


def test_same_operation_twice_is_applied_once(led):
    """DUP 03: a double click sends the same op_id; nothing is created twice."""
    payload = {"property_id": led.pid, "category_id": "cleaning", "label": "Ménage", "date": "2026-06-01", "amount": "80"}
    first = led.once("op-1", lambda: led.create_entry(payload))
    second = led.once("op-1", lambda: led.create_entry(payload))
    assert second["replayed"] is True and second["entry"]["id"] == first["entry"]["id"]
    assert len(led.data["entries"]) == 1


def test_service_lines_must_match_total_with_clear_message(led):
    with pytest.raises(RCError) as err:
        led.create_entry({"property_id": led.pid, "category_id": "cleaning", "label": "Facture", "date": "2026-06-01", "amount": "150",
                          "lines": [{"kind": "cleaning", "amount": "100"}, {"kind": "linen", "amount": "40"}]})
    assert err.value.code == "lines_total_mismatch"
    assert "140,00" in err.value.message("fr") and "150,00" in err.value.message("fr")
    assert led.data["entries"] == {}


def test_remaining_to_allocate_per_service(led):
    stay = led.create_stay({"property_id": led.pid, "start": "2026-06-01", "end": "2026-06-03"})["stay"]["id"]
    entry = led.create_entry({"property_id": led.pid, "category_id": "cleaning", "label": "Facture", "date": "2026-06-05", "amount": "150",
                              "lines": [{"id": "m", "kind": "cleaning", "amount": "100"}, {"id": "l", "kind": "linen", "amount": "40"}, {"id": "d", "kind": "travel", "amount": "10"}],
                              "allocations": [{"line_id": "m", "stay_id": stay, "amount": "100"}, {"line_id": "l", "stay_id": stay, "amount": "40"}]})["entry"]
    remaining = {row["kind"]: row["remaining"] for row in allocation_remaining(entry)}
    assert remaining == {"cleaning": 0, "linen": 0, "travel": 1000}   # « 10 € de déplacement restent à affecter »
    with pytest.raises(RCError) as err:
        led.set_allocations(entry["id"], {"allocations": [{"line_id": "d", "stay_id": stay, "amount": "11"}]})
    assert err.value.code == "allocation_exceeds"


def test_status_never_replaces_a_known_payment(led):
    entry = led.create_entry({"property_id": led.pid, "category_id": "maintenance", "label": "Réparation", "date": "2026-06-01", "amount": "100"})["entry"]
    assert entry_payment_status(led.data, entry) == ("unknown", 0)
    led.create_payment({"property_id": led.pid, "direction": "out", "date": "2026-06-02", "amount": "40", "links": [{"type": "entry", "id": entry["id"], "amount": "40"}]})
    assert entry_payment_status(led.data, entry) == ("partial", 4000)
    with pytest.raises(RCError) as err:
        led.create_payment({"property_id": led.pid, "direction": "out", "date": "2026-06-03", "amount": "70", "links": [{"type": "entry", "id": entry["id"], "amount": "70"}]})
    assert err.value.code == "payment_exceeds"


def test_corrections_keep_previous_value_and_author(led):
    entry = led.create_entry({"property_id": led.pid, "category_id": "maintenance", "label": "Réparation", "date": "2026-06-01", "amount": "100"})["entry"]
    led.update_entry(entry["id"], {"amount": "120"})
    history = led.data["entries"][entry["id"]]["history"]
    assert history[-1]["by"] == "admin" and history[-1]["changes"]["amount"] == [10000, 12000]


def test_other_currency_is_refused(led):
    with pytest.raises(RCError) as err:
        led.create_property({"name": "Abroad", "currency": "USD"})
    assert err.value.code == "currency_unsupported"


def test_text_is_never_html_and_control_chars_refused(led):
    prop = led.create_property({"name": "<b>Gîte</b>"})["property"]
    assert prop["name"] == "<b>Gîte</b>"      # stored as text, escaped by the interface
    with pytest.raises(RCError):
        led.create_property({"name": "bad\x00name"})


def test_loan_split_must_equal_instalment(led):
    with pytest.raises(RCError) as err:
        led.create_entry({"property_id": led.pid, "category_id": "loan", "label": "Prêt", "date": "2026-06-05", "amount": "200",
                          "loan_split": {"principal": "150", "interest": "40", "insurance": "20"}})
    assert err.value.code == "loan_split_mismatch"


def test_archived_property_refuses_new_data_but_keeps_history(led):
    led.create_stay({"property_id": led.pid, "start": "2026-06-01", "end": "2026-06-03"})
    led.set_property_archived(led.pid, True)
    with pytest.raises(RCError) as err:
        led.create_stay({"property_id": led.pid, "start": "2026-07-01", "end": "2026-07-03"})
    assert err.value.code == "property_archived"
    assert len(led.data["stays"]) == 1
