import asyncio
import logging
import threading
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

pyro_loop = asyncio.new_event_loop()


def run_pyro_loop():
    asyncio.set_event_loop(pyro_loop)
    pyro_loop.run_forever()


async def pyro_start():
    await pyro.start()


async def main():
    pyro_thread = threading.Thread(target=run_pyro_loop, daemon=True)
    pyro_thread.start()

    future = asyncio.run_coroutine_threadsafe(pyro_start(), pyro_loop)
    future.result(timeout=30)

    encode.pyro_client = pyro
    encode.pyro_loop = pyro_loop

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
