import time

from pyrogram import Client, filters
from pyrogram.types import Message

from config import OWNER_ID
from utils.data import get_settings, get_groups


def is_approved(message: Message):
    if message.chat.type.name in ("PRIVATE",):
        return False
    return message.chat.id in get_groups()


def register(app: Client):

    @app.on_message(filters.command("start"))
    async def start_cmd(client, message: Message):
        is_owner = message.from_user and message.from_user.id == OWNER_ID
        if message.chat.type.name not in ("PRIVATE",) and message.chat.id not in get_groups() and not is_owner:
            return
        await message.reply_text(
            "<b>Encoder Bot</b>\n\n"
            "Reply to a video or audio file with <code>/compress</code> to encode it.\n\n"
            "<b>Commands:</b>\n"
            "<code>/settings</code> — view current encoder settings\n"
            "<code>/ping</code> — check response time",
            parse_mode="html"
        )

    @app.on_message(filters.command("ping"))
    async def ping_cmd(client, message: Message):
        is_owner = message.from_user and message.from_user.id == OWNER_ID
        if message.chat.type.name not in ("PRIVATE",) and message.chat.id not in get_groups() and not is_owner:
            return
        start = time.time()
        sent = await message.reply_text("<b>Pinging...</b>", parse_mode="html")
        ms = round((time.time() - start) * 1000, 2)
        await sent.edit_text(f"<b>Pong!</b> <code>{ms}ms</code>", parse_mode="html")

    @app.on_message(filters.command("settings"))
    async def settings_cmd(client, message: Message):
        if message.chat.type.name not in ("PRIVATE",) and message.chat.id not in get_groups():
            return
        s = get_settings()
        text = (
            "<b>Current Encoder Settings</b>\n\n"
            f"<b>CRF:</b> <code>{s['crf']}</code>\n"
            f"<b>Preset:</b> <code>{s['preset']}</code>\n"
            f"<b>Tune:</b> <code>{s['tune']}</code>\n"
            f"<b>Aspect:</b> <code>{s['aspect']}</code>\n"
            f"<b>Video Codec:</b> <code>{s['videocodec']}</code>\n"
            f"<b>FPS:</b> <code>{s['fps']}</code>\n"
            f"<b>Audio Codec:</b> <code>{s['audiocodec']}</code>\n"
            f"<b>Bitrate:</b> <code>{s['bitrate']}</code>"
        )
        await message.reply_text(text, parse_mode="html")

    @app.on_message(filters.command("restart") & filters.user(OWNER_ID))
    async def restart_cmd(client, message: Message):
        await message.reply_text("<b>Restarting...</b>", parse_mode="html")
        import os, sys
        os.execv(sys.executable, [sys.executable] + sys.argv)
