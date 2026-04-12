import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from pyrogram import Client
from config import BOT_TOKEN, API_ID, API_HASH
from handlers import admin, settings, encode

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(admin.router)
dp.include_router(settings.router)
dp.include_router(encode.router)

pyro = Client(
    "encoder_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)


async def main():
    await pyro.start()
    encode.pyro_client = pyro
    await dp.start_polling(bot)
    await pyro.stop()


if __name__ == "__main__":
    asyncio.run(main())
