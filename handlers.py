"""Обработчики сообщений Telegram."""
import logging
from datetime import date
from decimal import Decimal
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)

import config
import database as db
from calculator import TipReport, calculate_tip_distribution
from locales import LANGUAGE_NAMES, SUPPORTED_LANGUAGES, fmt_money, fmt_number, get_text, resolve_language
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

logger = logging.getLogger(__name__)
router = Router()

TELEGRAM_LIMIT = 4000  # реальный лимит 4096, оставляем запас


# --- ЯЗЫК ПОЛЬЗОВАТЕЛЯ ДЛЯ КАЖДОГО ОБРАБОТЧИКА ---

class LanguageMiddleware(BaseMiddleware):
    """Кладёт язык пользователя в data['lang'], чтобы не запрашивать его в каждом хендлере."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        saved = db.get_user_language(user.id) if user else None
        data["lang"] = resolve_language(saved, user.language_code if user else None)
        return await handler(event, data)


router.message.middleware(LanguageMiddleware())
router.callback_query.middleware(LanguageMiddleware())


# --- СОСТОЯНИЯ ---

class BulkMonthlyState(StatesGroup):
    waiting_for_total = State()
    waiting_for_tax = State()
    waiting_for_staff = State()


class DailyTeamState(StatesGroup):
    waiting_for_total = State()
    waiting_for_staff = State()


class MonthlyReportState(StatesGroup):
    waiting_for_month = State()


class ShiftState(StatesGroup):
    waiting_for_hours = State()
    waiting_for_tips = State()


# Ответ внутри диалога: только текст и не команда
TEXT_ANSWER = F.text & ~F.text.startswith("/")


# --- ВСПОМОГАТЕЛЬНОЕ ---

def fmt_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


async def answer_long(message: Message, text: str) -> None:
    """Делит длинный текст по строкам, чтобы не упереться в лимит Telegram."""
    chunk = ""
    for line in text.split("\n"):
        if chunk and len(chunk) + len(line) + 1 > TELEGRAM_LIMIT:
            await message.answer(chunk)
            chunk = ""
        chunk = f"{chunk}\n{line}" if chunk else line
    if chunk:
        await message.answer(chunk)


async def answer_parse_error(message: Message, lang: str, error: ParseError) -> None:
    params = {k: fmt_number(v) if not isinstance(v, (str, int)) else v for k, v in error.params.items()}
    await message.answer(get_text(lang, error.key, **params))


def format_report(lang: str, title: str, report: TipReport) -> str:
    lines = [
        title,
        "",
        get_text(lang, "report_total_tips", value=fmt_money(report.total_tips)),
        get_text(lang, "report_tax", percent=fmt_number(report.tax_percent), value=fmt_money(report.tax_amount)),
        get_text(lang, "report_net_tips", value=fmt_money(report.net_tips)),
        get_text(lang, "report_total_hours", value=fmt_number(report.total_hours)),
        get_text(lang, "report_rate", value=fmt_money(report.rate_per_hour)),
        "",
        get_text(lang, "report_payouts"),
    ]
    for name, amount in sorted(report.payouts.items(), key=lambda item: (-item[1], item[0].casefold())):
        lines.append(
            get_text(
                lang, "report_line",
                name=name, hours=fmt_number(report.hours_by_staff[name]), amount=fmt_money(amount),
            )
        )
    return "\n".join(lines)


async def invite_link(bot: Bot, code: str) -> str:
    me = await bot.me()
    return f"https://t.me/{me.username}?start={code}"


async def get_manager(message: Message, lang: str) -> db.Membership | None:
    """Членство пользователя, если он менеджер; иначе отвечает и возвращает None."""
    membership = db.get_membership(message.from_user.id)
    if not membership:
        await message.answer(get_text(lang, "no_team"))
        return None
    if not membership.is_manager:
        await message.answer(get_text(lang, "manager_only"))
        return None
    return membership


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=LANGUAGE_NAMES[code], callback_data=f"lang_{code}")]
            for code in SUPPORTED_LANGUAGES
        ]
    )


# --- СТАРТ, СПРАВКА, ОТМЕНА, ЯЗЫК ---

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, lang: str, bot: Bot):
    await state.clear()
    # Ссылка-приглашение вида t.me/<bot>?start=<КОД>
    if command.args:
        await join_by_code(message, command.args, lang)
        return
    welcome = get_text(lang, "welcome", name=message.from_user.first_name or "")
    await message.answer(f"{welcome}\n\n{get_text(lang, 'help_body')}")


@router.message(Command("help"))
async def cmd_help(message: Message, lang: str):
    await message.answer(get_text(lang, "help_body"))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, lang: str):
    if await state.get_state() is None:
        await message.answer(get_text(lang, "nothing_to_cancel"))
        return
    await state.clear()
    await message.answer(get_text(lang, "cancelled"))


@router.message(Command("language"))
async def cmd_language(message: Message, lang: str):
    await message.answer(get_text(lang, "choose_lang"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang_"))
async def process_language_choice(callback: CallbackQuery):
    lang_code = callback.data.removeprefix("lang_")
    if lang_code not in SUPPORTED_LANGUAGES:
        await callback.answer()
        return
    db.set_user_language(callback.from_user.id, lang_code)
    await callback.answer()
    await callback.message.edit_text(get_text(lang_code, "lang_changed"))


# --- КОМАНДА (ЗАВЕДЕНИЕ) ---

@router.message(Command("create_team"))
async def cmd_create_team(message: Message, command: CommandObject, lang: str, bot: Bot):
    try:
        name = parse_team_name(command.args)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    try:
        membership = db.create_team(message.from_user.id, name)
    except db.AlreadyInTeamError as error:
        await message.answer(get_text(lang, "already_in_team", team=error.team_name))
        return
    await message.answer(
        get_text(
            lang, "team_created",
            team=membership.team_name,
            code=membership.invite_code,
            link=await invite_link(bot, membership.invite_code),
            tax=fmt_number(membership.tax_percent),
        )
    )


async def join_by_code(message: Message, code: str, lang: str) -> None:
    try:
        membership = db.join_team(message.from_user.id, code)
    except db.AlreadyInTeamError as error:
        await message.answer(get_text(lang, "already_in_team", team=error.team_name))
        return
    if not membership:
        await message.answer(get_text(lang, "invalid_code"))
        return
    await message.answer(get_text(lang, "joined", team=membership.team_name))


@router.message(Command("join"))
async def cmd_join(message: Message, command: CommandObject, lang: str):
    if not command.args:
        await message.answer(get_text(lang, "join_usage"))
        return
    await join_by_code(message, command.args, lang)


@router.message(Command("team"))
async def cmd_team(message: Message, lang: str, bot: Bot):
    membership = db.get_membership(message.from_user.id)
    if not membership:
        await message.answer(get_text(lang, "no_team"))
        return
    managers, members = db.count_team_members(membership.team_id)
    text = get_text(
        lang, "team_info",
        team=membership.team_name,
        role=get_text(lang, f"role_{membership.role}"),
        managers=managers,
        members=members,
        tax=fmt_number(membership.tax_percent),
    )
    if membership.is_manager:
        text += get_text(
            lang, "team_info_code",
            code=membership.invite_code,
            link=await invite_link(bot, membership.invite_code),
        )
    await message.answer(text)


@router.message(Command("leave_team"))
async def cmd_leave_team(message: Message, lang: str):
    membership = db.get_membership(message.from_user.id)
    result = db.leave_team(message.from_user.id)
    if result == "not_in_team":
        await message.answer(get_text(lang, "no_team"))
    elif result == "last_manager":
        await message.answer(get_text(lang, "last_manager"))
    elif result == "team_deleted":
        await message.answer(get_text(lang, "team_deleted", team=membership.team_name))
    else:
        await message.answer(get_text(lang, "left_team", team=membership.team_name))


@router.message(Command("set_tax"))
async def cmd_set_tax(message: Message, command: CommandObject, lang: str):
    membership = await get_manager(message, lang)
    if not membership:
        return
    if not command.args:
        await message.answer(get_text(lang, "set_tax_usage", tax=fmt_number(membership.tax_percent)))
        return
    try:
        tax = parse_tax(command.args)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    db.set_team_tax(membership.team_id, tax)
    await message.answer(get_text(lang, "tax_updated", tax=fmt_number(tax)))


# --- 1. РАЗОВЫЙ МЕСЯЧНЫЙ РАСЧЁТ (/monthly_bulk) — без сохранения, доступен всем ---

@router.message(Command("monthly_bulk"))
async def start_monthly_bulk(message: Message, state: FSMContext, lang: str):
    await state.clear()
    await message.answer(get_text(lang, "enter_total_bulk"))
    await state.set_state(BulkMonthlyState.waiting_for_total)


@router.message(BulkMonthlyState.waiting_for_total, TEXT_ANSWER)
async def process_bulk_total(message: Message, state: FSMContext, lang: str):
    try:
        total = parse_amount(message.text)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    await state.update_data(total=str(total))
    await message.answer(get_text(lang, "enter_tax"))
    await state.set_state(BulkMonthlyState.waiting_for_tax)


@router.message(BulkMonthlyState.waiting_for_tax, TEXT_ANSWER)
async def process_bulk_tax(message: Message, state: FSMContext, lang: str):
    try:
        tax = parse_tax(message.text)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    await state.update_data(tax=str(tax))
    await message.answer(get_text(lang, "enter_staff_bulk"))
    await state.set_state(BulkMonthlyState.waiting_for_staff)


@router.message(BulkMonthlyState.waiting_for_staff, TEXT_ANSWER)
async def process_bulk_staff(message: Message, state: FSMContext, lang: str):
    try:
        staff_hours = parse_staff_lines(message.text, config.MAX_HOURS_PER_MONTH)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    data = await state.get_data()
    report = calculate_tip_distribution(Decimal(data["total"]), Decimal(data["tax"]), staff_hours)
    await answer_long(message, format_report(lang, get_text(lang, "report_title_bulk"), report))
    await state.clear()


# --- 2. ДНЕВНОЙ ВВОД КОМАНДЫ (/add_daily_team [дата]) — только менеджер ---

@router.message(Command("add_daily_team"))
async def start_daily_team(message: Message, command: CommandObject, state: FSMContext, lang: str):
    await state.clear()
    if not await get_manager(message, lang):
        return
    try:
        shift_date = parse_date(command.args) if command.args else date.today()
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    await state.update_data(shift_date=shift_date.isoformat())
    await message.answer(get_text(lang, "enter_total_daily", date=fmt_date(shift_date)))
    await state.set_state(DailyTeamState.waiting_for_total)


@router.message(DailyTeamState.waiting_for_total, TEXT_ANSWER)
async def process_daily_total(message: Message, state: FSMContext, lang: str):
    try:
        total = parse_amount(message.text)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    data = await state.update_data(total=str(total))
    shift_date = date.fromisoformat(data["shift_date"])
    await message.answer(get_text(lang, "enter_staff_daily", date=fmt_date(shift_date)))
    await state.set_state(DailyTeamState.waiting_for_staff)


@router.message(DailyTeamState.waiting_for_staff, TEXT_ANSWER)
async def process_daily_staff(message: Message, state: FSMContext, lang: str):
    try:
        staff_hours = parse_staff_lines(message.text, config.MAX_HOURS_PER_DAY)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return

    # Права проверяем ещё раз: за время диалога пользователя могли убрать из команды
    membership = await get_manager(message, lang)
    if not membership:
        await state.clear()
        return

    data = await state.get_data()
    shift_date = date.fromisoformat(data["shift_date"])
    total = Decimal(data["total"])
    try:
        db.save_day_entry(membership.team_id, message.from_user.id, shift_date, total, staff_hours)
    except db.DuplicateDayError:
        await message.answer(get_text(lang, "daily_duplicate", date=fmt_date(shift_date)))
        await state.clear()
        return
    await message.answer(
        get_text(lang, "daily_saved", date=fmt_date(shift_date), tips=fmt_money(total), people=len(staff_hours))
    )
    await state.clear()


@router.message(Command("undo"))
async def cmd_undo(message: Message, lang: str):
    membership = await get_manager(message, lang)
    if not membership:
        return
    deleted = db.delete_last_entry(membership.team_id)
    if not deleted:
        await message.answer(get_text(lang, "undo_nothing"))
        return
    shift_date, tips = deleted
    await message.answer(get_text(lang, "undo_done", date=fmt_date(shift_date), tips=fmt_money(tips)))


@router.message(Command("delete_day"))
async def cmd_delete_day(message: Message, command: CommandObject, lang: str):
    membership = await get_manager(message, lang)
    if not membership:
        return
    if not command.args:
        await message.answer(get_text(lang, "delete_day_usage"))
        return
    try:
        shift_date = parse_date(command.args)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    if db.delete_day_entry(membership.team_id, shift_date):
        await message.answer(get_text(lang, "day_deleted", date=fmt_date(shift_date)))
    else:
        await message.answer(get_text(lang, "day_not_found", date=fmt_date(shift_date)))


# --- 3. МЕСЯЧНЫЙ ОТЧЁТ (/monthly_report [месяц]) — только менеджер ---

async def send_monthly_report(message: Message, lang: str, membership: db.Membership, month: str) -> None:
    total, staff_hours = db.get_month_data(membership.team_id, month)
    if not staff_hours:
        await message.answer(get_text(lang, "no_data_month", month=month))
        return
    report = calculate_tip_distribution(total, membership.tax_percent, staff_hours)
    title = get_text(lang, "report_title_month", month=month, team=membership.team_name)
    await answer_long(message, format_report(lang, title, report))


@router.message(Command("monthly_report"))
async def start_monthly_report(message: Message, command: CommandObject, state: FSMContext, lang: str):
    await state.clear()
    membership = await get_manager(message, lang)
    if not membership:
        return
    if command.args:
        try:
            month = parse_month(command.args)
        except ParseError as error:
            await answer_parse_error(message, lang, error)
            return
        await send_monthly_report(message, lang, membership, month)
        return
    await message.answer(get_text(lang, "enter_month", current=date.today().strftime("%Y-%m")))
    await state.set_state(MonthlyReportState.waiting_for_month)


@router.message(MonthlyReportState.waiting_for_month, TEXT_ANSWER)
async def process_monthly_report(message: Message, state: FSMContext, lang: str):
    try:
        month = parse_month(message.text)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    await state.clear()
    membership = await get_manager(message, lang)
    if membership:
        await send_monthly_report(message, lang, membership, month)


# --- 4. ЛИЧНЫЕ СМЕНЫ И СТАТИСТИКА ---

@router.message(Command("add_shift"))
async def start_add_shift(message: Message, state: FSMContext, lang: str):
    await state.clear()
    await message.answer(get_text(lang, "enter_personal_hours"))
    await state.set_state(ShiftState.waiting_for_hours)


@router.message(ShiftState.waiting_for_hours, TEXT_ANSWER)
async def process_hours(message: Message, state: FSMContext, lang: str):
    try:
        hours = parse_hours(message.text, config.MAX_HOURS_PER_DAY)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    await state.update_data(hours=str(hours))
    await message.answer(get_text(lang, "enter_personal_tips"))
    await state.set_state(ShiftState.waiting_for_tips)


@router.message(ShiftState.waiting_for_tips, TEXT_ANSWER)
async def process_tips(message: Message, state: FSMContext, lang: str):
    try:
        tips = parse_amount(message.text)
    except ParseError as error:
        await answer_parse_error(message, lang, error)
        return
    data = await state.get_data()
    hours = Decimal(data["hours"])
    db.add_shift(message.from_user.id, hours, tips)
    await message.answer(get_text(lang, "personal_saved", hours=fmt_number(hours), tips=fmt_money(tips)))
    await state.clear()


@router.message(Command("stats"))
async def cmd_stats(message: Message, lang: str):
    shifts, hours, tips = db.get_user_stats(message.from_user.id)
    await message.answer(get_text(lang, "stats_msg", shifts=shifts, hours=fmt_number(hours), tips=fmt_money(tips)))


# --- ВСЁ ОСТАЛЬНОЕ ---

@router.message()
async def fallback(message: Message, state: FSMContext, lang: str):
    """Стикер/фото посреди диалога или неизвестный текст вне диалога."""
    if await state.get_state() is not None:
        await message.answer(get_text(lang, "expect_text"))
    else:
        await message.answer(get_text(lang, "unknown_message"))


@router.error()
async def on_error(event: ErrorEvent):
    """Неожиданные ошибки пишем в лог и вежливо сообщаем пользователю, а не молчим."""
    logger.exception("Unhandled error while processing update", exc_info=event.exception)
    message = event.update.message
    if message:
        user = message.from_user
        lang = resolve_language(db.get_user_language(user.id) if user else None, user.language_code if user else None)
        try:
            await message.answer(get_text(lang, "internal_error"))
        except Exception:
            logger.exception("Failed to send error message")
