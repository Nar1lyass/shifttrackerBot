"""Все тексты бота на трёх языках. Разметка HTML.

Значения, подставляемые в шаблон (имена, названия), экранируются в get_text(),
поэтому символы <, >, & в имени сотрудника не ломают сообщение.
"""
import html
from decimal import Decimal

import config

SUPPORTED_LANGUAGES = ("cs", "en", "ru")

LANGUAGE_NAMES = {
    "cs": "🇨🇿 Čeština",
    "en": "🇬🇧 English",
    "ru": "🇷🇺 Русский",
}

# Команды, которые показываются в меню Telegram (порядок важен)
MENU_COMMANDS = (
    "start", "help", "monthly_bulk", "add_daily_team", "monthly_report", "undo",
    "delete_day", "team", "create_team", "join", "set_tax", "leave_team",
    "add_shift", "stats", "language", "cancel",
)

TEXTS: dict[str, dict[str, str]] = {
    "cs": {
        # Menu
        "cmd_start": "Start",
        "cmd_help": "Nápověda",
        "cmd_monthly_bulk": "⚡ Jednorázový výpočet za měsíc",
        "cmd_add_daily_team": "📥 Zadat dýška a hodiny za den",
        "cmd_monthly_report": "📊 Měsíční výkaz týmu",
        "cmd_undo": "↩️ Smazat poslední denní záznam",
        "cmd_delete_day": "🗑 Smazat záznam za datum",
        "cmd_team": "👥 Můj tým",
        "cmd_create_team": "➕ Vytvořit tým",
        "cmd_join": "🔑 Připojit se k týmu kódem",
        "cmd_set_tax": "🏛️ Nastavit daň týmu",
        "cmd_leave_team": "🚪 Opustit tým",
        "cmd_add_shift": "👤 Osobní směna",
        "cmd_stats": "📈 Moje statistika",
        "cmd_language": "🌐 Jazyk",
        "cmd_cancel": "✖️ Zrušit aktuální akci",
        # Start / help
        "welcome": "Ahoj, {name}! 👋\nJsem bot pro evidenci směn a rozdělování dýšek v restauraci a hotelu.",
        "help_body": (
            "<b>Rychlý výpočet</b>\n"
            "/monthly_bulk — rozdělit dýška za měsíc bez ukládání\n\n"
            "<b>Tým</b>\n"
            "/create_team Název — vytvořit tým (stanete se manažerem)\n"
            "/join KÓD — připojit se k týmu\n"
            "/team — informace o týmu\n"
            "/leave_team — opustit tým\n\n"
            "<b>Pro manažera</b>\n"
            "/add_daily_team — zadat dýška a hodiny za dnešek\n"
            "/add_daily_team 27.10.2026 — za jiné datum\n"
            "/monthly_report — měsíční výkaz\n"
            "/undo — smazat poslední záznam\n"
            "/delete_day 27.10.2026 — smazat záznam za datum\n"
            "/set_tax 40 — nastavit daň v %\n\n"
            "<b>Osobní</b>\n"
            "/add_shift — osobní směna\n"
            "/stats — moje statistika\n\n"
            "/language — jazyk · /cancel — zrušit akci"
        ),
        "choose_lang": "Vyberte jazyk / Choose language / Выберите язык:",
        "lang_changed": "✅ Jazyk byl změněn na češtinu.",
        "cancelled": "✖️ Akce zrušena.",
        "nothing_to_cancel": "Není co rušit.",
        "internal_error": "⚠️ Něco se pokazilo. Zkuste to prosím znovu.",
        "unknown_message": "Nerozumím. Seznam příkazů: /help",
        "expect_text": "Pošlete prosím odpověď textem, nebo /cancel pro zrušení.",
        # Validation
        "invalid_number": "❌ Zadejte prosím platné číslo.",
        "invalid_amount": "❌ Zadejte částku od 0, maximálně se dvěma desetinnými místy (např. 4500 nebo 4500,50).",
        "invalid_tax": "❌ Daň musí být číslo od 0 do 99,99 (např. 40).",
        "invalid_hours": "❌ Hodiny musí být číslo větší než 0 a nejvýše {max_hours}.",
        "empty_staff": "❌ Seznam je prázdný. Zadejte alespoň jeden řádek: Jméno Hodiny",
        "too_many_lines": "❌ Příliš mnoho řádků (max. {max_lines}).",
        "invalid_staff_line": "❌ Řádek {line_no}: «{line}» — chybí hodiny. Formát: Jméno Hodiny",
        "invalid_staff_hours": "❌ Řádek {line_no}: «{line}» — hodiny musí být od 0 do {max_hours}, max. 2 desetinná místa.",
        "name_too_long": "❌ Řádek {line_no}: jméno je delší než {max_len} znaků.",
        "duplicate_name": "❌ Jméno «{name}» je v seznamu dvakrát. Sečtěte hodiny do jednoho řádku.",
        "invalid_month": "❌ Neplatný měsíc. Použijte RRRR-MM (např. 2026-10) nebo MM.RRRR.",
        "invalid_date": "❌ Neplatné datum. Použijte DD.MM.RRRR nebo RRRR-MM-DD.",
        "future_date": "❌ Datum nemůže být v budoucnosti.",
        # Bulk calculation
        "enter_total_bulk": "💳 Zadejte CELKOVOU částku dýšek na kartu za CELÝ MĚSÍC (např. 120000):",
        "enter_tax": "🏛️ Zadejte procento daně (např. 40):",
        "enter_staff_bulk": (
            "👥 Zadejte zaměstnance a JEJICH HODINY ZA MĚSÍC, každého na nový řádek:\n"
            "<code>Jméno Hodiny</code>\n\nPříklad:\n<code>Alex 160\nMartin Novák 120,5</code>"
        ),
        # Daily entry
        "enter_total_daily": "💳 Zadejte CELKOVOU částku dýšek na kartu za {date} (např. 4500):",
        "enter_staff_daily": (
            "👥 Zadejte zaměstnance a hodiny za {date}, každého na nový řádek:\n"
            "<code>Jméno Hodiny</code>\n\nPříklad:\n<code>Alex 8\nMartin Novák 6,5</code>"
        ),
        "daily_saved": "✅ Uloženo za {date}: dýška {tips} CZK, zaměstnanců: {people}.\nOmyl? /undo",
        "daily_duplicate": "⚠️ Záznam za {date} už existuje. Nejprve ho smažte: /delete_day {date}",
        # Reports
        "report_title_bulk": "🏆 <b>MĚSÍČNÍ VÝKAZ VÝPLAT</b>",
        "report_title_month": "🏆 <b>VÝKAZ Z DENNÍCH ZÁZNAMŮ ({month})</b>\n{team}",
        "report_total_tips": "💳 Dýška na kartu celkem: {value} CZK",
        "report_tax": "🏛️ Daň ({percent} %): −{value} CZK",
        "report_net_tips": "💰 Čistý fond k rozdělení: <b>{value} CZK</b>",
        "report_total_hours": "⏱️ Hodin celkem: {value} h",
        "report_rate": "📈 Sazba: <b>{value} CZK/h</b>",
        "report_payouts": "📋 <b>VÝPLATY:</b>",
        "report_line": "• <b>{name}</b> ({hours} h) ➔ <b>{amount} CZK</b>",
        "enter_month": "🗓 Zadejte měsíc ve formátu <b>RRRR-MM</b> (nebo <code>1</code> pro aktuální měsíc {current}):",
        "no_data_month": "❌ Za měsíc {month} nejsou žádné záznamy.",
        # Undo / delete
        "undo_done": "↩️ Smazán záznam za {date} (dýška {tips} CZK).",
        "undo_nothing": "Žádné záznamy ke smazání.",
        "delete_day_usage": "Použití: /delete_day DD.MM.RRRR",
        "day_deleted": "🗑 Záznam za {date} smazán.",
        "day_not_found": "❌ Záznam za {date} neexistuje.",
        # Teams
        "no_team": "Nejste v žádném týmu. Vytvořte ho (/create_team Název) nebo se připojte (/join KÓD).",
        "manager_only": "⛔ Tuto akci může provést pouze manažer týmu.",
        "already_in_team": "Už jste v týmu «{team}». Nejprve ho opusťte: /leave_team",
        "create_team_usage": "Použití: /create_team Název podniku",
        "team_name_too_long": "❌ Název je delší než {max_len} znaků.",
        "team_created": (
            "✅ Tým «{team}» vytvořen, jste manažer.\n\n"
            "Kód pro kolegy: <code>{code}</code>\nNebo odkaz: {link}\n\n"
            "Daň je nastavena na {tax} % (změna: /set_tax)."
        ),
        "join_usage": "Použití: /join KÓD",
        "invalid_code": "❌ Tým s tímto kódem neexistuje.",
        "joined": "✅ Připojili jste se k týmu «{team}».",
        "left_team": "🚪 Opustili jste tým «{team}».",
        "team_deleted": "🗑 Byli jste poslední člen, tým «{team}» byl smazán i se záznamy.",
        "last_manager": "⛔ Jste jediný manažer a v týmu jsou další lidé. Tým nelze opustit.",
        "team_info": "👥 <b>{team}</b>\nVaše role: {role}\nManažerů: {managers}, zaměstnanců: {members}\nDaň: {tax} %",
        "team_info_code": "\nKód pro pozvání: <code>{code}</code>\nOdkaz: {link}",
        "role_manager": "manažer",
        "role_member": "zaměstnanec",
        "set_tax_usage": "Aktuální daň: {tax} %. Změna: /set_tax 40",
        "tax_updated": "✅ Daň týmu nastavena na {tax} %.",
        # Personal
        "enter_personal_hours": "Kolik hodin jste odpracovali?",
        "enter_personal_tips": "Kolik osobních dýšek jste dostali (CZK)?",
        "personal_saved": "✅ Osobní směna uložena: {hours} h, {tips} CZK.",
        "stats_msg": "📊 <b>Vaše statistika:</b>\nSměny: {shifts}\nHodiny: {hours} h\nDýška: {tips} CZK",
    },
    "en": {
        "cmd_start": "Start",
        "cmd_help": "Help",
        "cmd_monthly_bulk": "⚡ One-off monthly calculation",
        "cmd_add_daily_team": "📥 Enter tips and hours for a day",
        "cmd_monthly_report": "📊 Team monthly report",
        "cmd_undo": "↩️ Delete the last daily entry",
        "cmd_delete_day": "🗑 Delete the entry for a date",
        "cmd_team": "👥 My team",
        "cmd_create_team": "➕ Create a team",
        "cmd_join": "🔑 Join a team with a code",
        "cmd_set_tax": "🏛️ Set team tax",
        "cmd_leave_team": "🚪 Leave the team",
        "cmd_add_shift": "👤 Personal shift",
        "cmd_stats": "📈 My statistics",
        "cmd_language": "🌐 Language",
        "cmd_cancel": "✖️ Cancel current action",
        "welcome": "Hello, {name}! 👋\nI track shifts and split tips in restaurants and hotels.",
        "help_body": (
            "<b>Quick calculation</b>\n"
            "/monthly_bulk — split a month's tips without saving\n\n"
            "<b>Team</b>\n"
            "/create_team Name — create a team (you become the manager)\n"
            "/join CODE — join a team\n"
            "/team — team info\n"
            "/leave_team — leave the team\n\n"
            "<b>For managers</b>\n"
            "/add_daily_team — enter today's tips and hours\n"
            "/add_daily_team 27.10.2026 — for another date\n"
            "/monthly_report — monthly report\n"
            "/undo — delete the last entry\n"
            "/delete_day 27.10.2026 — delete the entry for a date\n"
            "/set_tax 40 — set tax in %\n\n"
            "<b>Personal</b>\n"
            "/add_shift — personal shift\n"
            "/stats — my statistics\n\n"
            "/language — language · /cancel — cancel action"
        ),
        "choose_lang": "Choose language / Vyberte jazyk / Выберите язык:",
        "lang_changed": "✅ Language changed to English.",
        "cancelled": "✖️ Action cancelled.",
        "nothing_to_cancel": "Nothing to cancel.",
        "internal_error": "⚠️ Something went wrong. Please try again.",
        "unknown_message": "I didn't get that. Commands: /help",
        "expect_text": "Please reply with text, or /cancel to cancel.",
        "invalid_number": "❌ Please enter a valid number.",
        "invalid_amount": "❌ Enter an amount of 0 or more with at most two decimals (e.g. 4500 or 4500.50).",
        "invalid_tax": "❌ Tax must be a number from 0 to 99.99 (e.g. 40).",
        "invalid_hours": "❌ Hours must be greater than 0 and at most {max_hours}.",
        "empty_staff": "❌ The list is empty. Enter at least one line: Name Hours",
        "too_many_lines": "❌ Too many lines (max {max_lines}).",
        "invalid_staff_line": "❌ Line {line_no}: «{line}» — hours are missing. Format: Name Hours",
        "invalid_staff_hours": "❌ Line {line_no}: «{line}» — hours must be between 0 and {max_hours}, max 2 decimals.",
        "name_too_long": "❌ Line {line_no}: name is longer than {max_len} characters.",
        "duplicate_name": "❌ «{name}» appears twice. Put their hours on one line.",
        "invalid_month": "❌ Invalid month. Use YYYY-MM (e.g. 2026-10) or MM.YYYY.",
        "invalid_date": "❌ Invalid date. Use DD.MM.YYYY or YYYY-MM-DD.",
        "future_date": "❌ The date can't be in the future.",
        "enter_total_bulk": "💳 Enter the TOTAL card tips for the WHOLE MONTH (e.g. 120000):",
        "enter_tax": "🏛️ Enter the tax percentage (e.g. 40):",
        "enter_staff_bulk": (
            "👥 Enter staff and THEIR MONTHLY HOURS, one per line:\n"
            "<code>Name Hours</code>\n\nExample:\n<code>Alex 160\nMartin Novak 120.5</code>"
        ),
        "enter_total_daily": "💳 Enter the TOTAL card tips for {date} (e.g. 4500):",
        "enter_staff_daily": (
            "👥 Enter staff and hours for {date}, one per line:\n"
            "<code>Name Hours</code>\n\nExample:\n<code>Alex 8\nMartin Novak 6.5</code>"
        ),
        "daily_saved": "✅ Saved for {date}: tips {tips} CZK, staff: {people}.\nMistake? /undo",
        "daily_duplicate": "⚠️ An entry for {date} already exists. Delete it first: /delete_day {date}",
        "report_title_bulk": "🏆 <b>MONTHLY PAYOUT REPORT</b>",
        "report_title_month": "🏆 <b>REPORT FROM DAILY ENTRIES ({month})</b>\n{team}",
        "report_total_tips": "💳 Total card tips: {value} CZK",
        "report_tax": "🏛️ Tax ({percent} %): −{value} CZK",
        "report_net_tips": "💰 Net pool to split: <b>{value} CZK</b>",
        "report_total_hours": "⏱️ Total hours: {value} h",
        "report_rate": "📈 Rate: <b>{value} CZK/h</b>",
        "report_payouts": "📋 <b>PAYOUTS:</b>",
        "report_line": "• <b>{name}</b> ({hours} h) ➔ <b>{amount} CZK</b>",
        "enter_month": "🗓 Enter the month as <b>YYYY-MM</b> (or <code>1</code> for the current month {current}):",
        "no_data_month": "❌ No entries for {month}.",
        "undo_done": "↩️ Deleted the entry for {date} (tips {tips} CZK).",
        "undo_nothing": "No entries to delete.",
        "delete_day_usage": "Usage: /delete_day DD.MM.YYYY",
        "day_deleted": "🗑 Entry for {date} deleted.",
        "day_not_found": "❌ There is no entry for {date}.",
        "no_team": "You're not in a team. Create one (/create_team Name) or join one (/join CODE).",
        "manager_only": "⛔ Only the team manager can do this.",
        "already_in_team": "You're already in the team «{team}». Leave it first: /leave_team",
        "create_team_usage": "Usage: /create_team Venue name",
        "team_name_too_long": "❌ The name is longer than {max_len} characters.",
        "team_created": (
            "✅ Team «{team}» created, you are the manager.\n\n"
            "Code for colleagues: <code>{code}</code>\nOr link: {link}\n\n"
            "Tax is set to {tax} % (change: /set_tax)."
        ),
        "join_usage": "Usage: /join CODE",
        "invalid_code": "❌ No team with this code.",
        "joined": "✅ You joined the team «{team}».",
        "left_team": "🚪 You left the team «{team}».",
        "team_deleted": "🗑 You were the last member, team «{team}» and its entries were deleted.",
        "last_manager": "⛔ You're the only manager and the team has other people. You can't leave.",
        "team_info": "👥 <b>{team}</b>\nYour role: {role}\nManagers: {managers}, staff: {members}\nTax: {tax} %",
        "team_info_code": "\nInvite code: <code>{code}</code>\nLink: {link}",
        "role_manager": "manager",
        "role_member": "staff",
        "set_tax_usage": "Current tax: {tax} %. Change: /set_tax 40",
        "tax_updated": "✅ Team tax set to {tax} %.",
        "enter_personal_hours": "How many hours did you work?",
        "enter_personal_tips": "How much in personal tips did you get (CZK)?",
        "personal_saved": "✅ Personal shift saved: {hours} h, {tips} CZK.",
        "stats_msg": "📊 <b>Your statistics:</b>\nShifts: {shifts}\nHours: {hours} h\nTips: {tips} CZK",
    },
    "ru": {
        "cmd_start": "Старт",
        "cmd_help": "Справка",
        "cmd_monthly_bulk": "⚡ Разовый расчёт за месяц",
        "cmd_add_daily_team": "📥 Внести чаевые и часы за день",
        "cmd_monthly_report": "📊 Месячный отчёт команды",
        "cmd_undo": "↩️ Удалить последнюю дневную запись",
        "cmd_delete_day": "🗑 Удалить запись за дату",
        "cmd_team": "👥 Моя команда",
        "cmd_create_team": "➕ Создать команду",
        "cmd_join": "🔑 Вступить в команду по коду",
        "cmd_set_tax": "🏛️ Налог команды",
        "cmd_leave_team": "🚪 Выйти из команды",
        "cmd_add_shift": "👤 Личная смена",
        "cmd_stats": "📈 Моя статистика",
        "cmd_language": "🌐 Язык",
        "cmd_cancel": "✖️ Отменить текущее действие",
        "welcome": "Привет, {name}! 👋\nЯ бот для учёта смен и распределения чаевых в ресторане и отеле.",
        "help_body": (
            "<b>Быстрый расчёт</b>\n"
            "/monthly_bulk — разделить чаевые за месяц без сохранения\n\n"
            "<b>Команда</b>\n"
            "/create_team Название — создать команду (вы станете менеджером)\n"
            "/join КОД — вступить в команду\n"
            "/team — информация о команде\n"
            "/leave_team — выйти из команды\n\n"
            "<b>Для менеджера</b>\n"
            "/add_daily_team — внести чаевые и часы за сегодня\n"
            "/add_daily_team 27.10.2026 — за другую дату\n"
            "/monthly_report — месячный отчёт\n"
            "/undo — удалить последнюю запись\n"
            "/delete_day 27.10.2026 — удалить запись за дату\n"
            "/set_tax 40 — налог в %\n\n"
            "<b>Личное</b>\n"
            "/add_shift — личная смена\n"
            "/stats — моя статистика\n\n"
            "/language — язык · /cancel — отменить действие"
        ),
        "choose_lang": "Выберите язык / Choose language / Vyberte jazyk:",
        "lang_changed": "✅ Язык изменён на русский.",
        "cancelled": "✖️ Действие отменено.",
        "nothing_to_cancel": "Нечего отменять.",
        "internal_error": "⚠️ Что-то пошло не так. Попробуйте ещё раз.",
        "unknown_message": "Не понял. Список команд: /help",
        "expect_text": "Пожалуйста, ответьте текстом или нажмите /cancel для отмены.",
        "invalid_number": "❌ Пожалуйста, введите корректное число.",
        "invalid_amount": "❌ Введите сумму от 0, не больше двух знаков после запятой (например, 4500 или 4500,50).",
        "invalid_tax": "❌ Налог — число от 0 до 99,99 (например, 40).",
        "invalid_hours": "❌ Часы должны быть больше 0 и не больше {max_hours}.",
        "empty_staff": "❌ Список пуст. Введите хотя бы одну строку: Имя Часы",
        "too_many_lines": "❌ Слишком много строк (максимум {max_lines}).",
        "invalid_staff_line": "❌ Строка {line_no}: «{line}» — не указаны часы. Формат: Имя Часы",
        "invalid_staff_hours": "❌ Строка {line_no}: «{line}» — часы должны быть от 0 до {max_hours}, не больше 2 знаков после запятой.",
        "name_too_long": "❌ Строка {line_no}: имя длиннее {max_len} символов.",
        "duplicate_name": "❌ «{name}» указан дважды. Сложите часы в одну строку.",
        "invalid_month": "❌ Неверный месяц. Используйте ГГГГ-ММ (например, 2026-10) или ММ.ГГГГ.",
        "invalid_date": "❌ Неверная дата. Используйте ДД.ММ.ГГГГ или ГГГГ-ММ-ДД.",
        "future_date": "❌ Дата не может быть в будущем.",
        "enter_total_bulk": "💳 Введите ОБЩУЮ сумму безналичных чаевых за ВЕСЬ МЕСЯЦ (например, 120000):",
        "enter_tax": "🏛️ Введите процент налога (например, 40):",
        "enter_staff_bulk": (
            "👥 Введите сотрудников и ИХ ЧАСЫ ЗА МЕСЯЦ, каждого с новой строки:\n"
            "<code>Имя Часы</code>\n\nПример:\n<code>Алекс 160\nМартин Новак 120,5</code>"
        ),
        "enter_total_daily": "💳 Введите ОБЩУЮ сумму безналичных чаевых за {date} (например, 4500):",
        "enter_staff_daily": (
            "👥 Введите сотрудников и часы за {date}, каждого с новой строки:\n"
            "<code>Имя Часы</code>\n\nПример:\n<code>Алекс 8\nМартин Новак 6,5</code>"
        ),
        "daily_saved": "✅ Сохранено за {date}: чаевые {tips} CZK, сотрудников: {people}.\nОшиблись? /undo",
        "daily_duplicate": "⚠️ Запись за {date} уже есть. Сначала удалите её: /delete_day {date}",
        "report_title_bulk": "🏆 <b>МЕСЯЧНАЯ ВЕДОМОСТЬ ВЫПЛАТ</b>",
        "report_title_month": "🏆 <b>ОТЧЁТ ИЗ ДНЕВНЫХ ЗАПИСЕЙ ({month})</b>\n{team}",
        "report_total_tips": "💳 Всего чаевых на карту: {value} CZK",
        "report_tax": "🏛️ Налог ({percent} %): −{value} CZK",
        "report_net_tips": "💰 Чистый фонд к распределению: <b>{value} CZK</b>",
        "report_total_hours": "⏱️ Всего часов: {value} ч",
        "report_rate": "📈 Ставка: <b>{value} CZK/ч</b>",
        "report_payouts": "📋 <b>ВЫПЛАТЫ:</b>",
        "report_line": "• <b>{name}</b> ({hours} ч) ➔ <b>{amount} CZK</b>",
        "enter_month": "🗓 Введите месяц в формате <b>ГГГГ-ММ</b> (или <code>1</code> для текущего месяца {current}):",
        "no_data_month": "❌ За {month} нет записей.",
        "undo_done": "↩️ Удалена запись за {date} (чаевые {tips} CZK).",
        "undo_nothing": "Нет записей для удаления.",
        "delete_day_usage": "Использование: /delete_day ДД.ММ.ГГГГ",
        "day_deleted": "🗑 Запись за {date} удалена.",
        "day_not_found": "❌ Записи за {date} нет.",
        "no_team": "Вы не состоите в команде. Создайте её (/create_team Название) или вступите (/join КОД).",
        "manager_only": "⛔ Это действие доступно только менеджеру команды.",
        "already_in_team": "Вы уже в команде «{team}». Сначала выйдите: /leave_team",
        "create_team_usage": "Использование: /create_team Название заведения",
        "team_name_too_long": "❌ Название длиннее {max_len} символов.",
        "team_created": (
            "✅ Команда «{team}» создана, вы менеджер.\n\n"
            "Код для коллег: <code>{code}</code>\nИли ссылка: {link}\n\n"
            "Налог установлен {tax} % (изменить: /set_tax)."
        ),
        "join_usage": "Использование: /join КОД",
        "invalid_code": "❌ Команды с таким кодом нет.",
        "joined": "✅ Вы вступили в команду «{team}».",
        "left_team": "🚪 Вы вышли из команды «{team}».",
        "team_deleted": "🗑 Вы были последним участником, команда «{team}» удалена вместе с записями.",
        "last_manager": "⛔ Вы единственный менеджер, а в команде есть другие люди. Выйти нельзя.",
        "team_info": "👥 <b>{team}</b>\nВаша роль: {role}\nМенеджеров: {managers}, сотрудников: {members}\nНалог: {tax} %",
        "team_info_code": "\nКод приглашения: <code>{code}</code>\nСсылка: {link}",
        "role_manager": "менеджер",
        "role_member": "сотрудник",
        "set_tax_usage": "Текущий налог: {tax} %. Изменить: /set_tax 40",
        "tax_updated": "✅ Налог команды: {tax} %.",
        "enter_personal_hours": "Сколько часов вы отработали?",
        "enter_personal_tips": "Сколько личных чаевых вы получили (CZK)?",
        "personal_saved": "✅ Личная смена сохранена: {hours} ч, {tips} CZK.",
        "stats_msg": "📊 <b>Ваша статистика:</b>\nСмен: {shifts}\nЧасов: {hours} ч\nЧаевых: {tips} CZK",
    },
}


def resolve_language(saved: str | None, telegram_code: str | None) -> str:
    """Сохранённый выбор > язык Telegram > язык по умолчанию."""
    if saved in SUPPORTED_LANGUAGES:
        return saved
    short = (telegram_code or "").split("-")[0].lower()
    if short in SUPPORTED_LANGUAGES:
        return short
    return config.DEFAULT_LANGUAGE


def get_text(lang: str, key: str, **params) -> str:
    texts = TEXTS.get(lang, TEXTS[config.DEFAULT_LANGUAGE])
    template = texts.get(key) or TEXTS["en"].get(key) or key
    if not params:
        return template
    safe = {k: html.escape(v) if isinstance(v, str) else v for k, v in params.items()}
    return template.format(**safe)


def fmt_money(value: Decimal) -> str:
    """1234.5 -> «1 234.50» (неразрывный пробел между тысячами)."""
    return f"{Decimal(value):,.2f}".replace(",", " ")


def fmt_number(value: Decimal) -> str:
    """Часы и проценты без лишних нулей: 8.50 -> «8.5», 40.00 -> «40»."""
    text = f"{Decimal(value):.2f}"
    return text.rstrip("0").rstrip(".") if "." in text else text
