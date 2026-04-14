import asyncio

from pyrogram import Client, idle

from config import API_HASH, API_ID, BOT_TOKEN

app = Client(
    "encoder_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

import handlers.basic as basic_handlers
import handlers.owner as owner_handlers
import handlers.compress as compress_handlers

basic_handlers.register(app)
owner_handlers.register(app)
compress_handlers.register(app)


async def main():
    await app.start()
    asyncio.create_task(compress_handlers.run_encode_worker(app))
    await idle()
    await app.stop()


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
