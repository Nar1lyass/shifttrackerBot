"""Настройки приложения. Секреты читаются из окружения или файла .env, а не из кода."""
import os
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "shifts.db"))
DEFAULT_TAX_PERCENT = Decimal(os.getenv("DEFAULT_TAX_PERCENT", "40"))
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "cs")

# Ограничения ввода
MAX_HOURS_PER_DAY = Decimal("24")
MAX_HOURS_PER_MONTH = Decimal("744")  # 31 день * 24 часа
MAX_AMOUNT = Decimal("100000000")
MAX_STAFF_LINES = 50
MAX_NAME_LENGTH = 64
MAX_TEAM_NAME_LENGTH = 64
