import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from handlers import common, admin, compress
from utils import queue as encode_queue
from utils.pyrogram_client import start_pyrogram

logging.basicConfig(level=logging.INFO)


async def main():
    # ✅ Correct for aiogram v3.7+
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()

    # Routers
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(compress.router)

    # ✅ Use running loop (Python 3.12 safe)
    encode_queue.set_aiogram_loop(asyncio.get_running_loop())

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    # ✅ Start Pyrogram once (important)
    start_pyrogram()

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
