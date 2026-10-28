"""Единственная функция расчёта распределения чаевых.

Используется и в разовом расчёте (/monthly_bulk), и в отчёте из дневных записей
(/monthly_report), поэтому правила расчёта одинаковы везде.
"""
from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


class CalculationError(ValueError):
    """Невозможно посчитать распределение с такими входными данными."""


@dataclass(frozen=True)
class TipReport:
    total_tips: Decimal
    tax_percent: Decimal
    tax_amount: Decimal
    net_tips: Decimal
    total_hours: Decimal
    rate_per_hour: Decimal
    hours_by_staff: dict[str, Decimal]
    payouts: dict[str, Decimal]


def to_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_tip_distribution(
    total_tips: Decimal, tax_percent: Decimal, staff_hours: dict[str, Decimal]
) -> TipReport:
    """Делит фонд чаевых после налога пропорционально отработанным часам.

    Суммы считаются в геллерах методом наибольшего остатка, поэтому сумма выплат
    всегда в точности равна чистому фонду: ни геллер не теряется и не появляется.
    """
    total_tips = to_money(Decimal(total_tips))
    tax_percent = Decimal(tax_percent)

    if total_tips < 0:
        raise CalculationError("total_tips must be >= 0")
    if not (0 <= tax_percent < 100):
        raise CalculationError("tax_percent must be in [0, 100)")
    if not staff_hours:
        raise CalculationError("staff_hours is empty")
    if any(Decimal(h) <= 0 for h in staff_hours.values()):
        raise CalculationError("hours must be > 0")

    hours = {name: Decimal(h) for name, h in staff_hours.items()}
    total_hours = sum(hours.values(), Decimal(0))

    tax_amount = to_money(total_tips * tax_percent / 100)
    net_tips = total_tips - tax_amount
    net_cents = int(net_tips * 100)

    exact = {name: net_cents * h / total_hours for name, h in hours.items()}
    cents = {name: int(value.to_integral_value(rounding=ROUND_FLOOR)) for name, value in exact.items()}
    leftover = net_cents - sum(cents.values())
    # Остаток раздаём тем, у кого самая большая дробная часть (при равенстве по имени,
    # чтобы результат был детерминированным).
    order = sorted(hours, key=lambda n: (-(exact[n] - cents[n]), n))
    for name in order[:leftover]:
        cents[name] += 1

    payouts = {name: Decimal(c) / 100 for name, c in cents.items()}
    return TipReport(
        total_tips=total_tips,
        tax_percent=tax_percent,
        tax_amount=tax_amount,
        net_tips=net_tips,
        total_hours=total_hours,
        rate_per_hour=to_money(net_tips / total_hours),
        hours_by_staff=hours,
        payouts=payouts,
    )
