"""Разбор и проверка пользовательского ввода.

Все ошибки поднимаются как ParseError с ключом текста из locales.py, чтобы
обработчик мог показать пользователю понятное сообщение на его языке.
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import config


class ParseError(ValueError):
    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params


_SPACES = re.compile(r"[\s  ]+")


def parse_decimal(text: str | None, error_key: str = "invalid_number") -> Decimal:
    if not text:
        raise ParseError(error_key)
    cleaned = _SPACES.sub("", text).replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ParseError(error_key) from None
    if not value.is_finite():
        raise ParseError(error_key)
    return value


def _max_two_decimals(value: Decimal) -> bool:
    return value == value.quantize(Decimal("0.01"))


def parse_amount(text: str | None) -> Decimal:
    """Сумма в CZK: от 0, не больше двух знаков после запятой."""
    value = parse_decimal(text, "invalid_amount")
    if value < 0 or value > config.MAX_AMOUNT or not _max_two_decimals(value):
        raise ParseError("invalid_amount")
    return value


def parse_tax(text: str | None) -> Decimal:
    """Процент налога: от 0 включительно до 100 не включительно."""
    value = parse_decimal(text, "invalid_tax")
    if not (0 <= value < 100):
        raise ParseError("invalid_tax")
    return value


def parse_hours(text: str | None, max_hours: Decimal) -> Decimal:
    value = parse_decimal(text, "invalid_hours")
    if value <= 0 or value > max_hours or not _max_two_decimals(value):
        raise ParseError("invalid_hours", max_hours=max_hours)
    return value


def parse_staff_lines(text: str | None, max_hours: Decimal) -> dict[str, Decimal]:
    """Разбирает строки вида «Имя Фамилия 8,5».

    Часы берутся из последнего слова, поэтому имя может состоять из нескольких слов.
    Повтор имени (без учёта регистра) считается ошибкой, а не перезаписывается молча.
    """
    lines = [line.strip() for line in (text or "").splitlines()]
    lines = [(no, line) for no, line in enumerate(lines, start=1) if line]
    if not lines:
        raise ParseError("empty_staff")
    if len(lines) > config.MAX_STAFF_LINES:
        raise ParseError("too_many_lines", max_lines=config.MAX_STAFF_LINES)

    result: dict[str, Decimal] = {}
    seen: dict[str, str] = {}
    for line_no, line in lines:
        parts = line.rsplit(maxsplit=1)
        if len(parts) != 2:
            raise ParseError("invalid_staff_line", line_no=line_no, line=line)
        name = " ".join(parts[0].split())
        if len(name) > config.MAX_NAME_LENGTH:
            raise ParseError("name_too_long", line_no=line_no, max_len=config.MAX_NAME_LENGTH)
        try:
            hours = parse_hours(parts[1], max_hours)
        except ParseError:
            raise ParseError(
                "invalid_staff_hours", line_no=line_no, line=line, max_hours=max_hours
            ) from None
        key = name.casefold()
        if key in seen:
            raise ParseError("duplicate_name", name=seen[key])
        seen[key] = name
        result[name] = hours
    return result


_MONTH_FORMATS = ("%Y-%m", "%m.%Y", "%m/%Y")
_DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y")


def parse_month(text: str | None, today: date | None = None) -> str:
    """Возвращает месяц в виде «ГГГГ-ММ». «1» означает текущий месяц."""
    value = (text or "").strip()
    today = today or date.today()
    if value == "1":
        return today.strftime("%Y-%m")
    for fmt in _MONTH_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    raise ParseError("invalid_month")


def parse_date(text: str | None, today: date | None = None) -> date:
    """Дата смены: ГГГГ-ММ-ДД или ДД.ММ.ГГГГ, не позже сегодняшней."""
    value = (text or "").strip()
    today = today or date.today()
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt).date()
        except ValueError:
            continue
        if parsed > today:
            raise ParseError("future_date")
        return parsed
    raise ParseError("invalid_date")


def parse_team_name(text: str | None) -> str:
    name = " ".join((text or "").split())
    if not name:
        raise ParseError("create_team_usage")
    if len(name) > config.MAX_TEAM_NAME_LENGTH:
        raise ParseError("team_name_too_long", max_len=config.MAX_TEAM_NAME_LENGTH)
    return name
