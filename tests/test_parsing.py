from datetime import date
from decimal import Decimal as D

import pytest

from parsing import (
    ParseError,
    parse_amount,
    parse_date,
    parse_hours,
    parse_month,
    parse_staff_lines,
    parse_tax,
    parse_team_name,
)

DAY = D("24")


@pytest.mark.parametrize("text,expected", [("4500", D("4500")), ("4500,5", D("4500.5")), ("1 200.50", D("1200.50")), ("0", D("0"))])
def test_parse_amount_ok(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", ["", None, "abc", "-1", "1.234", "NaN", "Infinity", "1e999"])
def test_parse_amount_rejects(text):
    with pytest.raises(ParseError) as exc:
        parse_amount(text)
    assert exc.value.key == "invalid_amount"


@pytest.mark.parametrize("text", ["100", "150", "-1", "x"])
def test_parse_tax_rejects(text):
    with pytest.raises(ParseError):
        parse_tax(text)


def test_parse_tax_ok():
    assert parse_tax("40") == D("40")
    assert parse_tax("0") == D("0")
    assert parse_tax("99,99") == D("99.99")


@pytest.mark.parametrize("text", ["0", "-2", "25", "8.123"])
def test_parse_hours_rejects(text):
    with pytest.raises(ParseError):
        parse_hours(text, DAY)


def test_staff_multiword_names_and_comma():
    result = parse_staff_lines("Alex 8\n\n  Martin   Novák  6,5 \nАнна-Мария 4", DAY)
    assert result == {"Alex": D("8"), "Martin Novák": D("6.5"), "Анна-Мария": D("4")}


def test_staff_duplicate_name_is_error_case_insensitive():
    with pytest.raises(ParseError) as exc:
        parse_staff_lines("Alex 8\nalex 2", DAY)
    assert exc.value.key == "duplicate_name"
    assert exc.value.params["name"] == "Alex"


def test_staff_missing_hours_reports_line():
    with pytest.raises(ParseError) as exc:
        parse_staff_lines("Alex 8\nMartin", DAY)
    assert exc.value.key == "invalid_staff_line"
    assert exc.value.params["line_no"] == 2


def test_staff_bad_hours_reports_line():
    with pytest.raises(ParseError) as exc:
        parse_staff_lines("Alex 30", DAY)
    assert exc.value.key == "invalid_staff_hours"


def test_staff_empty():
    with pytest.raises(ParseError) as exc:
        parse_staff_lines("  \n ", DAY)
    assert exc.value.key == "empty_staff"


def test_staff_too_many_lines():
    with pytest.raises(ParseError) as exc:
        parse_staff_lines("\n".join(f"P{i} 1" for i in range(51)), DAY)
    assert exc.value.key == "too_many_lines"


def test_parse_month():
    today = date(2026, 10, 28)
    assert parse_month("1", today) == "2026-10"
    assert parse_month("2026-09", today) == "2026-09"
    assert parse_month("9.2026", today) == "2026-09"
    assert parse_month("09/2026", today) == "2026-09"
    for bad in ("2026-13", "октябрь", "", "2026-1-1"):
        with pytest.raises(ParseError):
            parse_month(bad, today)


def test_parse_date():
    today = date(2026, 10, 28)
    assert parse_date("27.10.2026", today) == date(2026, 10, 27)
    assert parse_date("2026-10-28", today) == today
    with pytest.raises(ParseError) as exc:
        parse_date("29.10.2026", today)
    assert exc.value.key == "future_date"
    with pytest.raises(ParseError):
        parse_date("31.02.2026", today)


def test_parse_team_name():
    assert parse_team_name("  Kavárna   U Mostu ") == "Kavárna U Mostu"
    with pytest.raises(ParseError):
        parse_team_name(None)
    with pytest.raises(ParseError):
        parse_team_name("x" * 65)
