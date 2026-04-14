import os
import sys
from pyrogram import Client, filters
from utils.db import get_settings
from config import OWNER_ID

@Client.on_message(filters.command("start"))
async def cmd_start(client, message):
    await message.reply_text("<b>ᴇɴᴄᴏᴅᴇʀ ʙᴏᴛ ᴏɴʟɪɴᴇ.</b>")

@Client.on_message(filters.command("ping"))
async def cmd_ping(client, message):
    await message.reply_text("<b>ᴘᴏɴɢ.</b>")

@Client.on_message(filters.command("settings"))
async def cmd_settings(client, message):
    s = get_settings()
    t = "<b>ᴄᴜʀʀᴇɴᴛ sᴇᴛᴛɪɴɢs:</b>\n"
    for k, v in s.items():
        t += f"<b>{k}:</b> <code>{v}</code>\n"
    await message.reply_text(t)

@Client.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def cmd_restart(client, message):
    await message.reply_text("<b>ʀᴇsᴛᴀʀᴛɪɴɢ...</b>")
    os.execl(sys.executable, sys.executable, *sys.argv)
