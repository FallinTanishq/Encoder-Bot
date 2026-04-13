import asyncio

from pyrogram import Client, idle

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

    await app.start()
    asyncio.create_task(compress.run_encode_worker(app))
    await idle()
    await app.stop()


if __name__ == "__main__":
    asyncio.run(main())
