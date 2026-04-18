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
    await set_thumb(message.from_user.id, file_id)
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
    
    # Check if replied message has media
    media_msg = message.reply_to_message
    if not media_msg or not (media_msg.video or media_msg.document):
        await message.reply_text("<b>ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴠɪᴅᴇᴏ ᴏʀ ᴅᴏᴄᴜᴍᴇɴᴛ.</b>")
        return
    
    task_id = str(uuid.uuid4())
    msg = await message.reply_text("<b>ɢᴇᴛᴛɪɴɢ ᴍᴇᴛᴀᴅᴀᴛᴀ... ⚡</b>")
    
    utils.state.pending_selections[task_id] = {
        "client": client, 
        "message": message, 
        "media_msg": media_msg,
        "msg": msg, 
        "user_id": message.from_user.id, 
        "selected": []
    }
    
    try:
        os.makedirs("downloads", exist_ok=True)
        temp_header = f"downloads/header_{task_id}.mkv"
        
        # Stream first 5MB to get streams/duration
        async for chunk in client.stream_media(media_msg, limit=5):
            with open(temp_header, "ab") as f: 
                f.write(chunk)
            if os.path.getsize(temp_header) > 5 * 1024 * 1024: 
                break
        
        probe_data = await probe(temp_header)
        if os.path.exists(temp_header): 
            os.remove(temp_header) 
            
        streams = probe_data.get("streams", [])
        
        # --- THE PROGRESS BAR KEY ---
        # Ensure duration is captured as a float for the ETA math
        raw_duration = probe_data.get("format", {}).get("duration", 0)
        utils.state.pending_selections[task_id]["duration"] = float(raw_duration)
        
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        utils.state.pending_selections[task_id]["audio_streams"] = audio_streams
        
        if not audio_streams:
            # If no audio, skip selection and go straight to download
            asyncio.create_task(trigger_full_download(task_id, client))
            return
            
        kb = []
        for s in audio_streams:
            idx = s.get("index")
            # Get language or default to "Track"
            lang = s.get("tags", {}).get("language", f"Track {idx}")
            codec = s.get('codec_name', 'unknown')
            btn_text = f"✘ {lang.upper()} [{codec}]"
            kb.append([InlineKeyboardButton(btn_text, callback_data=f"aud_{task_id}_{idx}")])
        
        kb.append([
            InlineKeyboardButton("Select All", callback_data=f"all_{task_id}"),
            InlineKeyboardButton("Done ✅", callback_data=f"done_{task_id}")
        ])
        
        await msg.edit_text(
            "<b>sᴇʟᴇᴄᴛ ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋs:</b>\n<i>The selected tracks will be kept.</i>", 
            reply_markup=InlineKeyboardMarkup(kb)
        )

    except Exception as e:
        # Cleanup if probe fails
        if os.path.exists(temp_header): os.remove(temp_header)
        await msg.edit_text(f"<b>ᴇʀʀᴏʀ ɢᴇᴛᴛɪɴɢ ᴍᴇᴛᴀᴅᴀᴛᴀ:</b> <code>{e}</code>")

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
        file_path = await client.download_media(data["media_msg"], progress=update_progress, progress_args=(data["msg"], time.time(), "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ", task_id))
        data["file_path"] = file_path
        data = utils.state.pending_selections.pop(task_id)
        utils.state.active_tasks[task_id] = data
        await utils.state.queue.put(task_id)
        await data["msg"].edit_text("<b>ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ...</b>")
    except Exception as e:
        await data["msg"].edit_text(f"Download Error: {e}")
