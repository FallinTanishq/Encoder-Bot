from pyrogram import Client, filters
from config import OWNER_ID
from utils.db import update_setting, get_settings, add_group, remove_group, get_groups

@Client.on_message(filters.command("videocodec") & filters.user(OWNER_ID))
async def set_videocodec(client, message):
    if len(message.command) < 2:
        await message.reply_text("<b>Usage:</b> `/videocodec [codec]` (e.g., libx264, libx265)")
        return
    codec = message.command[1]
    await update_setting("videocodec", codec)
    await message.reply_text(f"✅ <b>Video codec permanently set to:</b> <code>{codec}</code>")

@Client.on_message(filters.command("audiocodec") & filters.user(OWNER_ID))
async def set_audiocodec(client, message):
    if len(message.command) < 2:
        await message.reply_text("<b>Usage:</b> `/audiocodec [codec]` (e.g., aac, libopus)")
        return
    codec = message.command[1]
    await update_setting("audiocodec", codec)
    await message.reply_text(f"✅ <b>Audio codec permanently set to:</b> <code>{codec}</code>")

@Client.on_message(filters.command("preset") & filters.user(OWNER_ID))
async def set_preset(client, message):
    if len(message.command) < 2:
        await message.reply_text("<b>Usage:</b> `/preset [preset]` (e.g., fast, faster, ultrafast, none)")
        return
    preset = message.command[1]
    await update_setting("preset", preset)
    await message.reply_text(f"✅ <b>Preset permanently set to:</b> <code>{preset}</code>")

@Client.on_message(filters.command("crf") & filters.user(OWNER_ID))
async def set_crf(client, message):
    if len(message.command) < 2:
        await message.reply_text("<b>Usage:</b> `/crf [value]` (e.g., 28, 30, none)")
        return
    crf = message.command[1]
    await update_setting("crf", crf)
    await message.reply_text(f"✅ <b>CRF permanently set to:</b> <code>{crf}</code>")
    
@Client.on_message(filters.command("aspect") & filters.user(OWNER_ID))
async def set_aspect(client, message):
    if len(message.command) < 2:
        await message.reply_text("<b>Usage:</b> `/aspect [resolution]` (e.g., 1280x720, none)")
        return
    aspect = message.command[1]
    await update_setting("aspect", aspect)
    await message.reply_text(f"✅ <b>Aspect ratio permanently set to:</b> <code>{aspect}</code>")

@Client.on_message(filters.command("settings") & filters.user(OWNER_ID))
async def check_settings(client, message):
    settings = await get_settings()
    text = "<b>🎥 Current Global Settings:</b>\n\n"
    for key, val in settings.items():
        if key != "_id":
            text += f"• <b>{key}:</b> <code>{val}</code>\n"
    await message.reply_text(text)

@Client.on_message(filters.command("addgroup") & filters.user(OWNER_ID))
async def cmd_addgroup(client, message):
    if len(message.command) < 2:
        # If no ID is passed, add the current group
        chat_id = message.chat.id
    else:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            await message.reply_text("Invalid Chat ID.")
            return

    await add_group(chat_id)
    await message.reply_text(f"✅ <b>Group</b> <code>{chat_id}</code> <b>has been authorized.</b>")

@Client.on_message(filters.command("rmgroup") & filters.user(OWNER_ID))
async def cmd_rmgroup(client, message):
    if len(message.command) < 2:
        chat_id = message.chat.id
    else:
        try:
            chat_id = int(message.command[1])
        except ValueError:
            await message.reply_text("Invalid Chat ID.")
            return

    await remove_group(chat_id)
    await message.reply_text(f"❌ <b>Group</b> <code>{chat_id}</code> <b>authorization removed.</b>")

@Client.on_message(filters.command("groups") & filters.user(OWNER_ID))
async def list_groups(client, message):
    groups = await get_groups()
    if not groups:
        await message.reply_text("No groups authorized yet.")
        return
        
    text = "<b>🛡 Authorized Groups:</b>\n\n"
    for gid in groups:
        text += f"• <code>{gid}</code>\n"
    await message.reply_text(text)
