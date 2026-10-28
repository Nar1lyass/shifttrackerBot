import re
import string
from decimal import Decimal as D

from locales import MENU_COMMANDS, SUPPORTED_LANGUAGES, TEXTS, fmt_money, fmt_number, get_text, resolve_language


def placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_all_languages_have_same_keys_and_placeholders():
    base = TEXTS["en"]
    for lang in SUPPORTED_LANGUAGES:
        assert set(TEXTS[lang]) == set(base), lang
        for key, template in TEXTS[lang].items():
            assert placeholders(template) == placeholders(base[key]), (lang, key)


def test_menu_commands_valid_for_telegram():
    for cmd in MENU_COMMANDS:
        assert re.fullmatch(r"[a-z0-9_]{1,32}", cmd)
        for lang in SUPPORTED_LANGUAGES:
            assert 1 <= len(get_text(lang, f"cmd_{cmd}")) <= 256


def test_values_are_html_escaped():
    text = get_text("en", "report_line", name="<b>Al & *_x_*</b>", hours="8", amount="1")
    assert "&lt;b&gt;Al &amp; *_x_*&lt;/b&gt;" in text


def test_resolve_language():
    assert resolve_language("ru", "en") == "ru"
    assert resolve_language(None, "en-GB") == "en"
    assert resolve_language(None, "de") == "cs"
    assert resolve_language("xx", None) == "cs"


def test_formatting():
    assert fmt_money(D("1234.5")) == "1 234.50"
    assert fmt_number(D("8.50")) == "8.5"
    assert fmt_number(D("40")) == "40"
