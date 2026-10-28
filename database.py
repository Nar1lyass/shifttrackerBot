"""Работа с SQLite.

Все командные данные (дневные записи, часы, отчёты) привязаны к команде,
поэтому пользователь видит и меняет только данные своей команды.
Деньги хранятся в геллерах (целое число), чтобы не накапливать ошибки float.
"""
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import config

SCHEMA_VERSION = 1
_db_path: str = config.DB_PATH

_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # без похожих 0/O и 1/I


class AlreadyInTeamError(Exception):
    def __init__(self, team_name: str):
        super().__init__(team_name)
        self.team_name = team_name


class DuplicateDayError(Exception):
    pass


@dataclass(frozen=True)
class Membership:
    team_id: int
    team_name: str
    role: str
    invite_code: str
    tax_percent: Decimal

    @property
    def is_manager(self) -> bool:
        return self.role == "manager"


@contextmanager
def connect():
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _to_cents(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).to_integral_value())


def _from_cents(cents: int | None) -> Decimal:
    return Decimal(cents or 0) / 100


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def init_db(path: str | None = None) -> None:
    """Создаёт таблицы и мигрирует базу старой версии (без команд)."""
    global _db_path
    if path is not None:
        _db_path = path

    with connect() as conn:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version < 1:
            # Старые таблицы не знали о командах, их данные нельзя безопасно
            # приписать какой-то команде. Не удаляем, а переименовываем.
            for old in ("team_shifts", "daily_tips"):
                if _table_exists(conn, old) and not _table_exists(conn, f"legacy_{old}"):
                    conn.execute(f"ALTER TABLE {old} RENAME TO legacy_{old}")

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id  INTEGER PRIMARY KEY,
                language TEXT NOT NULL DEFAULT 'cs'
            );

            CREATE TABLE IF NOT EXISTS shifts (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                hours   REAL,
                tips    REAL,
                date    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS teams (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                invite_code TEXT NOT NULL UNIQUE,
                tax_percent TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS team_members (
                user_id   INTEGER PRIMARY KEY,
                team_id   INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                role      TEXT NOT NULL CHECK (role IN ('manager', 'member')),
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS day_entries (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id    INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                shift_date DATE NOT NULL,
                month_year TEXT NOT NULL,
                tips_cents INTEGER NOT NULL CHECK (tips_cents >= 0),
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (team_id, shift_date)
            );
            CREATE INDEX IF NOT EXISTS idx_day_entries_month ON day_entries(team_id, month_year);

            CREATE TABLE IF NOT EXISTS day_entry_hours (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id   INTEGER NOT NULL REFERENCES day_entries(id) ON DELETE CASCADE,
                staff_name TEXT NOT NULL,
                hours      TEXT NOT NULL
            );
            """
        )
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")


# --- ЯЗЫК ---

def set_user_language(user_id: int, lang: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO users (user_id, language) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET language = excluded.language",
            (user_id, lang),
        )


def get_user_language(user_id: int) -> str | None:
    """Сохранённый язык пользователя или None, если он его ещё не выбирал."""
    with connect() as conn:
        row = conn.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return row["language"] if row else None


# --- КОМАНДЫ (заведения) ---

def get_membership(user_id: int) -> Membership | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT t.id, t.name, t.invite_code, t.tax_percent, m.role
            FROM team_members m JOIN teams t ON t.id = m.team_id
            WHERE m.user_id = ?
            """,
            (user_id,),
        ).fetchone()
    if not row:
        return None
    return Membership(row["id"], row["name"], row["role"], row["invite_code"], Decimal(row["tax_percent"]))


def _generate_invite_code(conn: sqlite3.Connection) -> str:
    while True:
        code = "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(8))
        if not conn.execute("SELECT 1 FROM teams WHERE invite_code = ?", (code,)).fetchone():
            return code


def create_team(user_id: int, name: str, tax_percent: Decimal | None = None) -> Membership:
    existing = get_membership(user_id)
    if existing:
        raise AlreadyInTeamError(existing.team_name)
    tax = config.DEFAULT_TAX_PERCENT if tax_percent is None else tax_percent
    with connect() as conn:
        code = _generate_invite_code(conn)
        cur = conn.execute(
            "INSERT INTO teams (name, invite_code, tax_percent) VALUES (?, ?, ?)",
            (name, code, str(tax)),
        )
        conn.execute(
            "INSERT INTO team_members (user_id, team_id, role) VALUES (?, ?, 'manager')",
            (user_id, cur.lastrowid),
        )
    return get_membership(user_id)


def join_team(user_id: int, invite_code: str) -> Membership | None:
    """Вступление по коду. None, если код неверный."""
    existing = get_membership(user_id)
    if existing:
        raise AlreadyInTeamError(existing.team_name)
    with connect() as conn:
        team = conn.execute(
            "SELECT id FROM teams WHERE invite_code = ?", (invite_code.strip().upper(),)
        ).fetchone()
        if not team:
            return None
        conn.execute(
            "INSERT INTO team_members (user_id, team_id, role) VALUES (?, ?, 'member')",
            (user_id, team["id"]),
        )
    return get_membership(user_id)


def leave_team(user_id: int) -> str:
    """Возвращает 'not_in_team', 'last_manager', 'team_deleted' или 'left'."""
    membership = get_membership(user_id)
    if not membership:
        return "not_in_team"
    with connect() as conn:
        counts = conn.execute(
            "SELECT COUNT(*) AS total, SUM(role = 'manager') AS managers FROM team_members WHERE team_id = ?",
            (membership.team_id,),
        ).fetchone()
        if counts["total"] == 1:
            conn.execute("DELETE FROM teams WHERE id = ?", (membership.team_id,))
            return "team_deleted"
        if membership.is_manager and counts["managers"] == 1:
            return "last_manager"
        conn.execute("DELETE FROM team_members WHERE user_id = ?", (user_id,))
    return "left"


def count_team_members(team_id: int) -> tuple[int, int]:
    """(менеджеров, сотрудников)"""
    with connect() as conn:
        row = conn.execute(
            "SELECT SUM(role = 'manager') AS managers, SUM(role = 'member') AS members "
            "FROM team_members WHERE team_id = ?",
            (team_id,),
        ).fetchone()
    return row["managers"] or 0, row["members"] or 0


def set_team_tax(team_id: int, tax_percent: Decimal) -> None:
    with connect() as conn:
        conn.execute("UPDATE teams SET tax_percent = ? WHERE id = ?", (str(tax_percent), team_id))


# --- ДНЕВНЫЕ ЗАПИСИ КОМАНДЫ ---

def save_day_entry(
    team_id: int, created_by: int, shift_date: date, tips: Decimal, staff_hours: dict[str, Decimal]
) -> None:
    """Сохраняет чаевые и часы за день. Повторная запись за ту же дату запрещена."""
    with connect() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO day_entries (team_id, shift_date, month_year, tips_cents, created_by) "
                "VALUES (?, ?, ?, ?, ?)",
                (team_id, shift_date.isoformat(), shift_date.strftime("%Y-%m"), _to_cents(tips), created_by),
            )
        except sqlite3.IntegrityError:
            raise DuplicateDayError() from None
        conn.executemany(
            "INSERT INTO day_entry_hours (entry_id, staff_name, hours) VALUES (?, ?, ?)",
            [(cur.lastrowid, name, str(hours)) for name, hours in staff_hours.items()],
        )


def delete_last_entry(team_id: int) -> tuple[date, Decimal] | None:
    """Удаляет последнюю внесённую запись команды. Возвращает её дату и сумму."""
    with connect() as conn:
        row = conn.execute(
            "SELECT id, shift_date, tips_cents FROM day_entries WHERE team_id = ? ORDER BY id DESC LIMIT 1",
            (team_id,),
        ).fetchone()
        if not row:
            return None
        conn.execute("DELETE FROM day_entries WHERE id = ?", (row["id"],))
    return date.fromisoformat(row["shift_date"]), _from_cents(row["tips_cents"])


def delete_day_entry(team_id: int, shift_date: date) -> bool:
    with connect() as conn:
        cur = conn.execute(
            "DELETE FROM day_entries WHERE team_id = ? AND shift_date = ?",
            (team_id, shift_date.isoformat()),
        )
    return cur.rowcount > 0


def get_month_data(team_id: int, month_year: str) -> tuple[Decimal, dict[str, Decimal]]:
    """Сумма чаевых за месяц и часы по сотрудникам.

    Имена объединяются без учёта регистра («alex» и «Alex» — один человек),
    отображается первое встреченное написание.
    """
    with connect() as conn:
        total = conn.execute(
            "SELECT SUM(tips_cents) FROM day_entries WHERE team_id = ? AND month_year = ?",
            (team_id, month_year),
        ).fetchone()[0]
        rows = conn.execute(
            """
            SELECT h.staff_name, h.hours
            FROM day_entry_hours h JOIN day_entries e ON e.id = h.entry_id
            WHERE e.team_id = ? AND e.month_year = ?
            ORDER BY e.shift_date, h.id
            """,
            (team_id, month_year),
        ).fetchall()

    hours: dict[str, Decimal] = {}
    display: dict[str, str] = {}
    for row in rows:
        key = row["staff_name"].casefold()
        display.setdefault(key, row["staff_name"])
        hours[key] = hours.get(key, Decimal(0)) + Decimal(row["hours"])
    return _from_cents(total), {display[k]: v for k, v in hours.items()}


# --- ЛИЧНЫЙ УЧЁТ СМЕН ---

def add_shift(user_id: int, hours: Decimal, tips: Decimal) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO shifts (user_id, hours, tips) VALUES (?, ?, ?)",
            (user_id, float(hours), float(tips)),
        )


def get_user_stats(user_id: int) -> tuple[int, Decimal, Decimal]:
    """(кол-во смен, часы, чаевые)"""
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(id), SUM(hours), SUM(tips) FROM shifts WHERE user_id = ?", (user_id,)
        ).fetchone()
    count, hours, tips = row[0] or 0, row[1] or 0, row[2] or 0
    return count, Decimal(str(hours)).quantize(Decimal("0.01")), Decimal(str(tips)).quantize(Decimal("0.01"))
