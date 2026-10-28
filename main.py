import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

import config
import database as db
from handlers import router
from locales import MENU_COMMANDS, SUPPORTED_LANGUAGES, get_text


async def setup_bot_commands(bot: Bot) -> None:
    """Меню команд на языке интерфейса Telegram пользователя (cs/en/ru) и по умолчанию."""
    for lang in SUPPORTED_LANGUAGES:
        commands = [BotCommand(command=c, description=get_text(lang, f"cmd_{c}")) for c in MENU_COMMANDS]
        await bot.set_my_commands(commands, language_code=lang)
    default = [BotCommand(command=c, description=get_text(config.DEFAULT_LANGUAGE, f"cmd_{c}")) for c in MENU_COMMANDS]
    await bot.set_my_commands(default)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if not config.BOT_TOKEN:
        sys.exit("BOT_TOKEN не задан. Скопируйте .env.example в .env и впишите токен от @BotFather.")

    db.init_db()

    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    await setup_bot_commands(bot)
    logging.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
