import asyncio
import threading

from pyrogram import Client
from config import BOT_TOKEN, API_ID, API_HASH

_client: Client = None
_loop: asyncio.AbstractEventLoop = None
_ready = threading.Event()


def _run_loop(loop, client):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_start(client))


async def _start(client):
    await client.start()
    _ready.set()
    await asyncio.Event().wait()


def start_pyrogram():
    global _client, _loop
    _loop = asyncio.new_event_loop()
    _client = Client(
        "encoder_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        in_memory=True,
    )
    t = threading.Thread(target=_run_loop, args=(_loop, _client), daemon=True)
    t.start()
    _ready.wait()


def get_client() -> Client:
    return _client


def get_loop() -> asyncio.AbstractEventLoop:
    return _loop
