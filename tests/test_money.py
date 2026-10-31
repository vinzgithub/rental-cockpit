# Copyright © 2026 Vincent Fournet
import pytest
from engine.money import allocate, format_cents, parse_amount, parse_amount_text


@pytest.mark.parametrize("text,cents", [("12.50", 1250), ("12,5", 1250), ("1000", 100000), ("0,01", 1), (" 80 € ", 8000), (150, 15000)])
def test_parse_amount_accepts_decimal_notation(text, cents):
    assert parse_amount(text) == cents


@pytest.mark.parametrize("text", ["1.250,00", "12.345", "abc", "", "1e3", "12.505", "-5"])
def test_parse_amount_refuses_ambiguous_or_invalid(text):
    with pytest.raises(ValueError):
        parse_amount(text)


def test_parse_amount_text_for_imports():
    assert parse_amount_text("1 234,56 €") == 123456
    assert parse_amount_text("1,234.56") == 123456
    assert parse_amount_text("(12,50)") == -1250
    assert parse_amount_text("") is None
    with pytest.raises(ValueError):
        parse_amount_text("1.250")  # could be 1.25 or 1 250: refused, never guessed


@pytest.mark.parametrize("total,weights", [(1000, [1, 1, 1]), (35000, [1] * 3), (-1001, [2, 1]), (1, [1, 1, 1]), (15000, [100, 40, 10])])
def test_allocate_never_loses_a_cent(total, weights):
    shares = allocate(total, weights)
    assert sum(shares) == total
    assert max(shares) - min(shares) <= max(1, abs(total))


def test_format_cents():
    assert format_cents(100000, "fr") == "1 000,00 €"
    assert format_cents(-1250, "en") == "-€12.50"
