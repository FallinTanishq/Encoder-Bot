from pyrogram import Client, filters
from config import OWNER_ID
from utils.db import get_groups, save_groups, get_presets, save_presets, get_settings, save_settings

@Client.on_message(filters.command("approve") & filters.user(OWNER_ID))
async def cmd_approve(client, message):
    g = get_groups()
    if message.chat.id not in g:
        g.append(message.chat.id)
        save_groups(g)
    await message.reply_text("<b>ᴀᴘᴘʀᴏᴠᴇᴅ.</b>")

@Client.on_message(filters.command("revoke") & filters.user(OWNER_ID))
async def cmd_revoke(client, message):
    g = get_groups()
    if message.chat.id in g:
        g.remove(message.chat.id)
        save_groups(g)
    await message.reply_text("<b>ʀᴇᴠᴏᴋᴇᴅ.</b>")

@Client.on_message(filters.command("savepreset") & filters.user(OWNER_ID))
async def cmd_savepreset(client, message):
    if len(message.command) < 2:
        return
    name = message.command[1].lower()
    p = get_presets()
    p[name] = get_settings()
    save_presets(p)
    await message.reply_text(f"<b>ᴘʀᴇsᴇᴛ sᴀᴠᴇᴅ:</b> <code>{name}</code>")

@Client.on_message(filters.command("p") & filters.user(OWNER_ID))
async def cmd_loadpreset(client, message):
    if len(message.command) < 2:
        return
    name = message.command[1].lower()
    p = get_presets()
    if name not in p:
        await message.reply_text("<b>ɴᴏᴛ ғᴏᴜɴᴅ.</b>")
        return
    save_settings(p[name])
    s = p[name]
    text = f"<b>ᴘʀᴇsᴇᴛ {name} ʟᴏᴀᴅᴇᴅ.</b>\n"
    for k, v in s.items():
        text += f"<b>{k}:</b> <code>{v}</code>\n"
    await message.reply_text(text)

def validate_setting(k, v):
    v = v.lower()
    if k == "preset" and v not in ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]:
        return False
    if k == "tune" and v not in ["film", "animation", "grain", "stillimage", "fastdecode", "zerolatency", "none"]:
        return False
    if k == "fps" and v != "sameassource" and not v.isdigit():
        return False
    if k == "aspect" and v != "none" and "x" not in v:
        return False
    return True

@Client.on_message(filters.command(["crf", "preset", "tune", "aspect", "videocodec", "fps", "audiocodec", "bitrate"]) & filters.user(OWNER_ID))
async def cmd_settings_set(client, message):
    cmd = message.command[0].lower()
    if len(message.command) < 2:
        return
    val = message.text.split(None, 1)[1]
    if not validate_setting(cmd, val):
        await message.reply_text("<b>ɪɴᴠᴀʟɪᴅ.</b>")
        return
    s = get_settings()
    s[cmd] = val
    save_settings(s)
    await message.reply_text(f"<b>{cmd} sᴇᴛ ᴛᴏ:</b> <code>{val}</code>")
