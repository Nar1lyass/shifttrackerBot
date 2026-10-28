from decimal import Decimal as D

import pytest

from calculator import CalculationError, calculate_tip_distribution


def test_basic_split_by_hours():
    report = calculate_tip_distribution(D("1000"), D("40"), {"Alex": D("8"), "Martin": D("2")})
    assert report.tax_amount == D("400.00")
    assert report.net_tips == D("600.00")
    assert report.total_hours == D("10")
    assert report.rate_per_hour == D("60.00")
    assert report.payouts == {"Alex": D("480.00"), "Martin": D("120.00")}


@pytest.mark.parametrize(
    "total,tax,hours",
    [
        ("100", "0", ["1", "1", "1"]),
        ("1000.01", "40", ["7", "3", "5.5"]),
        ("99999.99", "33.33", ["160", "120.5", "88.25", "12"]),
        ("0.05", "0", ["1", "1", "1", "1", "1", "1", "1"]),
    ],
)
def test_payouts_always_sum_to_net_pool(total, tax, hours):
    staff = {f"P{i}": D(h) for i, h in enumerate(hours)}
    report = calculate_tip_distribution(D(total), D(tax), staff)
    assert sum(report.payouts.values()) == report.net_tips
    assert report.tax_amount + report.net_tips == report.total_tips


def test_leftover_cent_goes_deterministically():
    report = calculate_tip_distribution(D("100"), D("0"), {"B": D("1"), "A": D("1"), "C": D("1")})
    assert report.payouts == {"A": D("33.34"), "B": D("33.33"), "C": D("33.33")}


def test_zero_tips_is_valid():
    report = calculate_tip_distribution(D("0"), D("40"), {"Alex": D("8")})
    assert report.payouts == {"Alex": D("0")}


@pytest.mark.parametrize(
    "total,tax,staff",
    [
        ("-1", "40", {"A": D("1")}),
        ("100", "100", {"A": D("1")}),
        ("100", "-5", {"A": D("1")}),
        ("100", "40", {}),
        ("100", "40", {"A": D("0")}),
        ("100", "40", {"A": D("-3")}),
    ],
)
def test_invalid_input_rejected(total, tax, staff):
    with pytest.raises(CalculationError):
        calculate_tip_distribution(D(total), D(tax), staff)
