import asyncio

from pyrogram import Client

from config import API_HASH, API_ID, BOT_TOKEN
from handlers import basic, compress, owner


app = Client(
    "encoder_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)


async def main():
    basic.register(app)
    owner.register(app)
    compress.register(app)

    async with app:
        worker = asyncio.create_task(compress.run_encode_worker(app))
        await asyncio.Event().wait()
        worker.cancel()


if __name__ == "__main__":
    asyncio.run(main())
