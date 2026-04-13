import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from handlers import common, admin, compress
from utils import queue as encode_queue
from utils.pyrogram_client import start_pyrogram

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()

    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(compress.router)

    encode_queue.set_aiogram_loop(asyncio.get_event_loop())

    await dp.start_polling(bot)


if __name__ == "__main__":
    start_pyrogram()
    asyncio.run(main())
