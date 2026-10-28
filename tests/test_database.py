import sqlite3
from datetime import date
from decimal import Decimal as D

import pytest

import database as db

MANAGER, MEMBER, STRANGER = 1, 2, 3


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db.init_db(str(tmp_path / "test.db"))


def make_team(user_id=MANAGER, name="Bistro"):
    return db.create_team(user_id, name, D("40"))


def test_language_roundtrip():
    assert db.get_user_language(MANAGER) is None
    db.set_user_language(MANAGER, "en")
    db.set_user_language(MANAGER, "ru")
    assert db.get_user_language(MANAGER) == "ru"


def test_create_and_join_team():
    team = make_team()
    assert team.is_manager and len(team.invite_code) == 8
    joined = db.join_team(MEMBER, team.invite_code.lower())
    assert joined.team_id == team.team_id and not joined.is_manager
    assert db.count_team_members(team.team_id) == (1, 1)


def test_cannot_be_in_two_teams():
    make_team()
    with pytest.raises(db.AlreadyInTeamError):
        make_team()


def test_join_with_wrong_code():
    make_team()
    assert db.join_team(STRANGER, "WRONG123") is None


def test_teams_are_isolated():
    a = make_team(MANAGER, "A")
    b = make_team(STRANGER, "B")
    db.save_day_entry(a.team_id, MANAGER, date(2026, 10, 1), D("1000"), {"Alex": D("8")})
    assert db.get_month_data(b.team_id, "2026-10") == (D("0"), {})
    total, hours = db.get_month_data(a.team_id, "2026-10")
    assert total == D("1000") and hours == {"Alex": D("8")}


def test_duplicate_day_rejected_and_undo():
    team = make_team()
    db.save_day_entry(team.team_id, MANAGER, date(2026, 10, 1), D("1000"), {"Alex": D("8")})
    with pytest.raises(db.DuplicateDayError):
        db.save_day_entry(team.team_id, MANAGER, date(2026, 10, 1), D("50"), {"Alex": D("1")})
    db.save_day_entry(team.team_id, MANAGER, date(2026, 10, 2), D("500.55"), {"Alex": D("4")})
    assert db.delete_last_entry(team.team_id) == (date(2026, 10, 2), D("500.55"))
    total, hours = db.get_month_data(team.team_id, "2026-10")
    assert total == D("1000") and hours == {"Alex": D("8")}


def test_delete_day():
    team = make_team()
    db.save_day_entry(team.team_id, MANAGER, date(2026, 10, 1), D("1000"), {"Alex": D("8")})
    assert db.delete_day_entry(team.team_id, date(2026, 10, 1)) is True
    assert db.delete_day_entry(team.team_id, date(2026, 10, 1)) is False
    assert db.delete_last_entry(team.team_id) is None


def test_month_aggregation_merges_name_case():
    team = make_team()
    db.save_day_entry(team.team_id, MANAGER, date(2026, 10, 1), D("100.10"), {"Alex": D("8"), "Martin Novák": D("2.5")})
    db.save_day_entry(team.team_id, MANAGER, date(2026, 10, 2), D("200.20"), {"alex": D("4")})
    db.save_day_entry(team.team_id, MANAGER, date(2026, 11, 1), D("999"), {"Alex": D("1")})
    total, hours = db.get_month_data(team.team_id, "2026-10")
    assert total == D("300.30")
    assert hours == {"Alex": D("12"), "Martin Novák": D("2.5")}


def test_leave_team_rules():
    team = make_team()
    db.join_team(MEMBER, team.invite_code)
    assert db.leave_team(MANAGER) == "last_manager"
    assert db.leave_team(MEMBER) == "left"
    assert db.leave_team(MEMBER) == "not_in_team"
    db.save_day_entry(team.team_id, MANAGER, date(2026, 10, 1), D("1"), {"A": D("1")})
    assert db.leave_team(MANAGER) == "team_deleted"
    assert db.get_membership(MANAGER) is None
    with db.connect() as conn:  # записи удалены каскадом
        assert conn.execute("SELECT COUNT(*) FROM day_entries").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM day_entry_hours").fetchone()[0] == 0


def test_set_team_tax():
    team = make_team()
    db.set_team_tax(team.team_id, D("21.5"))
    assert db.get_membership(MANAGER).tax_percent == D("21.5")


def test_personal_shifts():
    db.add_shift(MANAGER, D("8"), D("350.5"))
    db.add_shift(MANAGER, D("6.5"), D("200"))
    assert db.get_user_stats(MANAGER) == (2, D("14.50"), D("550.50"))
    assert db.get_user_stats(STRANGER) == (0, D("0.00"), D("0.00"))


def test_migration_from_old_schema(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE shifts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, hours REAL, tips REAL,
                             date TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE team_shifts (id INTEGER PRIMARY KEY, staff_name TEXT, hours REAL, shift_date DATE, month_year TEXT);
        CREATE TABLE daily_tips (id INTEGER PRIMARY KEY, amount REAL, shift_date DATE, month_year TEXT);
        CREATE TABLE users (user_id INTEGER PRIMARY KEY, language TEXT DEFAULT 'cs');
        INSERT INTO shifts (user_id, hours, tips) VALUES (7, 8, 100);
        INSERT INTO daily_tips (amount, shift_date, month_year) VALUES (500, '2026-10-01', '2026-10');
        INSERT INTO users VALUES (7, 'ru');
        """
    )
    conn.commit()
    conn.close()

    db.init_db(str(path))
    db.init_db(str(path))  # повторный запуск не должен ломаться

    assert db.get_user_stats(7)[0] == 1
    assert db.get_user_language(7) == "ru"
    with db.connect() as c:
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"legacy_daily_tips", "legacy_team_shifts", "teams", "day_entries"} <= tables
        assert c.execute("SELECT COUNT(*) FROM legacy_daily_tips").fetchone()[0] == 1
