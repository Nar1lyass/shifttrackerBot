# ShiftTracker Bot

A Telegram bot that tracks shifts and fairly splits card tips among restaurant and hotel staff, based on hours worked and after tax.

I built it to solve a real problem at work. At the end of each month someone had to divide the card-tip pool by hand in a spreadsheet, and the results were often disputed. The bot keeps a daily log per team and produces a transparent monthly payout report.

**Languages:** Čeština · English · Русский (picked automatically from the Telegram app language, changeable with `/language`).

## Features

- **Teams with roles.** A manager creates a team and invites colleagues with a code or link. Each team sees only its own data. Only managers can enter data and view reports.
- **Daily log.** Card tips and each person's hours for a day (today or any past date). One entry per date, with `/undo` and `/delete_day` to fix mistakes.
- **Monthly report.** Tips minus the team tax, split proportionally to hours.
- **Exact money math.** Uses `Decimal` and integer haléře with the largest-remainder method, so payouts always add up exactly to the net pool.
- **One-off calculator** (`/monthly_bulk`). Split a month's tips without saving anything. Available to everyone.
- **Personal log.** Track your own shifts and tips with `/add_shift` and `/stats`.
- **Forgiving input.** Accepts `6,5` or `6.5`, `1 200`, multi-word names, and `DD.MM.YYYY` dates. Errors point to the exact line.

### Example

```
/add_daily_team 27.10.2026
> 4500
> Alex 8
  Martin Novák 6,5

/monthly_report 2026-10
🏆 REPORT FROM DAILY ENTRIES (2026-10)
💳 Total card tips: 4 500.50 CZK
🏛️ Tax (21 %): −945.11 CZK
💰 Net pool to split: 3 555.39 CZK
• Alex (8 h) ➔ 1 835.04 CZK
• Martin Novák (6.5 h) ➔ 1 490.97 CZK
...
```

## Commands

| Command | Who | What it does |
|---|---|---|
| `/create_team Name` | anyone | Create a team and become its manager |
| `/join CODE` | anyone | Join a team (or open the invite link) |
| `/team`, `/leave_team` | member | Team info / leave the team |
| `/add_daily_team [date]` | manager | Enter tips and hours for a day |
| `/undo`, `/delete_day date` | manager | Remove the last entry or the entry for a date |
| `/monthly_report [YYYY-MM]` | manager | Monthly payout report |
| `/set_tax 40` | manager | Team tax in % |
| `/monthly_bulk` | anyone | One-off calculation without saving |
| `/add_shift`, `/stats` | anyone | Personal shifts and statistics |
| `/language`, `/cancel`, `/help` | anyone | Language, cancel the current dialog, help |

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then put your BotFather token into .env
python main.py
```

Requires Python 3.10+.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover the tip calculation (including exact rounding), input parsing, database rules (team isolation, duplicate days, undo, leaving a team, migration from the old schema) and the consistency of all three translations.

## Project structure

```
main.py         entry point: bot setup, command menu, polling
handlers.py     Telegram handlers and dialog states (aiogram 3 FSM)
calculator.py   tip distribution (the single source of truth for the math)
parsing.py      user input validation with localized error keys
database.py     SQLite schema, migrations and queries
locales.py      all texts (cs/en/ru), HTML escaping, number formatting
config.py       settings read from environment / .env
tests/          pytest suite
```

## Tech notes and limits

- aiogram 3, SQLite, no ORM. The database is upgraded automatically on startup. Tables from the old version without teams are kept as `legacy_*`.
- Dialog state uses in-memory FSM storage. An unfinished dialog is lost when the bot restarts; for production, switch to `RedisStorage`.
- Database calls are synchronous. That is fine at the scale of a single venue; for heavy load, move to `aiosqlite` or PostgreSQL.
- Staff in the daily log are identified by name, not by Telegram account. "alex" and "Alex" count as the same person; a typo creates a new one.
