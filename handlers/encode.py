import os
import time
import uuid
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID
from utils.db import get_groups, set_thumb, del_thumb
import utils.state
from utils.ffmpeg_utils import probe
from utils.progress import update_progress

@Client.on_message(filters.command("t"))
async def set_thumbnail_cmd(client, message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply_text("<b>ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴘʜᴏᴛᴏ ᴡɪᴛʜ /t ᴛᴏ sᴇᴛ ɪᴛ ᴀs ʏᴏᴜʀ ᴛʜᴜᴍʙɴᴀɪʟ.</b>")
        return
    file_id = message.reply_to_message.photo.file_id
    await set_thumb(message.from_user.id, file_id, message.chat.id, message.reply_to_message.id)
    await message.reply_text("✅ <b>Custom thumbnail saved!</b>")

@Client.on_message(filters.command("delt"))
async def del_thumbnail_cmd(client, message):
    await del_thumb(message.from_user.id)
    await message.reply_text("🗑 <b>Custom thumbnail removed.</b>")

@Client.on_message(filters.command("compress"))
async def compress_cmd(client, message):
    auth_groups = await get_groups()
    if message.chat.id not in auth_groups and message.chat.id != OWNER_ID:
        return
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply_text("<b>ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇᴅɪᴀ ᴍᴇssᴀɢᴇ.</b>")
        return
    
    task_id = str(uuid.uuid4())
    msg = await message.reply_text("<b>ɢᴇᴛᴛɪɴɢ ᴍᴇᴛᴀᴅᴀᴛᴀ... ⚡</b>")
    
    # --- REFRESH FILE REFERENCE ---
    # Fetch a fresh copy of the message to ensure the file reference hasn't expired
    try:
        target_msg = await client.get_messages(message.chat.id, message.reply_to_message.id)
        if target_msg.empty: target_msg = message.reply_to_message
    except Exception:
        target_msg = message.reply_to_message
    # ------------------------------
        
    utils.state.pending_selections[task_id] = {
        "client": client, "message": message, "media_msg": target_msg,
        "msg": msg, "user_id": message.from_user.id, "selected": []
    }
    
    try:
        os.makedirs("downloads", exist_ok=True)
        temp_header = f"downloads/header_{task_id}.mkv"
        
        # Streams the first 5MB using the refreshed message
        async for chunk in client.stream_media(target_msg, limit=5):
            with open(temp_header, "ab") as f: f.write(chunk)
            if os.path.getsize(temp_header) > 5 * 1024 * 1024: break
        
        probe_data = await probe(temp_header)
        if os.path.exists(temp_header): os.remove(temp_header) 
            
        streams = probe_data.get("streams", [])
        utils.state.pending_selections[task_id]["duration"] = float(probe_data.get("format", {}).get("duration", 0))
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        utils.state.pending_selections[task_id]["audio_streams"] = audio_streams
        
        if not audio_streams:
            asyncio.create_task(trigger_full_download(task_id, client))
            return
            
        kb = []
        for s in audio_streams:
            idx = s.get("index")
            lang = s.get("tags", {}).get("language", "und")
            btn_text = f"[ ] {lang} | {s.get('codec_name')}"
            kb.append([InlineKeyboardButton(btn_text, callback_data=f"aud_{task_id}_{idx}")])
        
        kb.append([
            InlineKeyboardButton("Select All", callback_data=f"all_{task_id}"),
            InlineKeyboardButton("Done", callback_data=f"done_{task_id}")
        ])
        await msg.edit_text("<b>sᴇʟᴇᴄᴛ ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋs:</b>", reply_markup=InlineKeyboardMarkup(kb))
    except Exception as e:
        await msg.edit_text(f"<b>ᴇʀʀᴏʀ:</b> <code>{e}</code>")

@Client.on_callback_query(filters.regex(r"^aud_(.*)_(.*)"))
async def toggle_audio(client, query):
    task_id, idx = query.matches[0].group(1), int(query.matches[0].group(2))
    if task_id not in utils.state.pending_selections: return
    
    sel = utils.state.pending_selections[task_id]["selected"]
    if idx in sel: sel.remove(idx)
    else: sel.append(idx)
        
    audio_streams = utils.state.pending_selections[task_id]["audio_streams"]
    kb = [[InlineKeyboardButton(f"{'[X]' if s.get('index') in sel else '[ ]'} {s.get('tags',{}).get('language','und')} | {s.get('codec_name')}", 
           callback_data=f"aud_{task_id}_{s.get('index')}")] for s in audio_streams]
    kb.append([InlineKeyboardButton("Select All", callback_data=f"all_{task_id}"), InlineKeyboardButton("Done", callback_data=f"done_{task_id}")])
    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(kb))

@Client.on_callback_query(filters.regex(r"^all_(.*)"))
async def select_all_audio(client, query):
    task_id = query.matches[0].group(1)
    if task_id not in utils.state.pending_selections: return
    
    audio_streams = utils.state.pending_selections[task_id]["audio_streams"]
    utils.state.pending_selections[task_id]["selected"] = [s.get("index") for s in audio_streams]
    
    kb = [[InlineKeyboardButton(f"[X] {s.get('tags',{}).get('language','und')} | {s.get('codec_name')}", 
           callback_data=f"aud_{task_id}_{s.get('index')}")] for s in audio_streams]
    kb.append([InlineKeyboardButton("Select All", callback_data=f"all_{task_id}"), InlineKeyboardButton("Done", callback_data=f"done_{task_id}")])
    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    await query.answer("All selected!")

@Client.on_callback_query(filters.regex(r"^done_(.*)"))
async def finish_selection(client, query):
    task_id = query.matches[0].group(1)
    if task_id not in utils.state.pending_selections: return
    await query.answer()
    asyncio.create_task(trigger_full_download(task_id, client))

async def trigger_full_download(task_id, client):
    data = utils.state.pending_selections[task_id]
    try:
        # --- REFRESH FILE REFERENCE AGAIN ---
        # If the user took a long time picking audio tracks, the reference might have expired.
        try:
            fresh_msg = await client.get_messages(data["message"].chat.id, data["media_msg"].id)
            if not fresh_msg.empty: data["media_msg"] = fresh_msg
        except Exception:
            pass
        # ------------------------------------

        file_path = await client.download_media(data["media_msg"], progress=update_progress, progress_args=(data["msg"], time.time(), "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ", task_id))
        data["file_path"] = file_path
        data = utils.state.pending_selections.pop(task_id)
        utils.state.active_tasks[task_id] = data
        await utils.state.queue.put(task_id)
        await data["msg"].edit_text("<b>ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ...</b>")
    except Exception as e:
        await data["msg"].edit_text(f"Download Error: {e}")
