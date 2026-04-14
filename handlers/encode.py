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

# --- NEW CUSTOM THUMBNAIL COMMANDS ---
@Client.on_message(filters.command("t"))
async def set_thumbnail_cmd(client, message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        await message.reply_text("<b>ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴘʜᴏᴛᴏ ᴡɪᴛʜ /t ᴛᴏ sᴇᴛ ɪᴛ ᴀs ʏᴏᴜʀ ᴛʜᴜᴍʙɴᴀɪʟ.</b>")
        return
    
    # Grab the highest resolution file_id of the photo
    file_id = message.reply_to_message.photo.file_id
    await set_thumb(message.from_user.id, file_id)
    await message.reply_text("✅ <b>Custom thumbnail saved successfully!</b>\n<i>Use /delt to remove it.</i>")

@Client.on_message(filters.command("delt"))
async def del_thumbnail_cmd(client, message):
    await del_thumb(message.from_user.id)
    await message.reply_text("🗑 <b>Custom thumbnail removed. Bot will use auto-generated ones.</b>")

# --- ENCODE HANDLERS ---
@Client.on_message(filters.command("compress"))
async def compress_cmd(client, message):
    auth_groups = await get_groups()
    if message.chat.id not in auth_groups and message.chat.id != OWNER_ID:
        return
        
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply_text("<b>ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇᴅɪᴀ ᴍᴇssᴀɢᴇ.</b>")
        return
    
    media = getattr(message.reply_to_message, message.reply_to_message.media.value)
    if not hasattr(media, "file_id"):
        return

    task_id = str(uuid.uuid4())
    msg = await message.reply_text("<b>ɢᴇᴛᴛɪɴɢ ᴍᴇᴛᴀᴅᴀᴛᴀ... ⚡</b>")
    
    utils.state.pending_selections[task_id] = {
        "client": client,
        "message": message,
        "media_msg": message.reply_to_message,
        "msg": msg,
        "user_id": message.from_user.id,
        "selected": []
    }
    
    try:
        utils.state.cancel_flags[task_id] = False
        os.makedirs("downloads", exist_ok=True)
        temp_header = f"downloads/header_{task_id}.mkv"
        
        async for chunk in client.stream_media(message.reply_to_message, limit=5):
            with open(temp_header, "ab") as f:
                f.write(chunk)
            if os.path.getsize(temp_header) > 5 * 1024 * 1024: 
                break
        
        probe_data = await probe(temp_header)
        if os.path.exists(temp_header):
            os.remove(temp_header) 
            
        streams = probe_data.get("streams", [])
        duration = float(probe_data.get("format", {}).get("duration", 0))
        utils.state.pending_selections[task_id]["duration"] = duration
        
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        utils.state.pending_selections[task_id]["audio_streams"] = audio_streams
        
        if not audio_streams:
            await trigger_full_download(task_id, client)
            return
            
        kb = []
        for s in audio_streams:
            idx = s.get("index")
            lang = s.get("tags", {}).get("language", "und")
            codec = s.get("codec_name", "unknown")
            title = s.get("tags", {}).get("title", f"Track {idx}")
            btn_text = f"[ ] {lang} | {codec} | {title}"
            kb.append([InlineKeyboardButton(btn_text, callback_data=f"aud_{task_id}_{idx}")])
        
        # Added Select All and Done to the same row
        kb.append([
            InlineKeyboardButton("Select All", callback_data=f"all_{task_id}"),
            InlineKeyboardButton("Done", callback_data=f"done_{task_id}")
        ])
        
        await msg.edit_text("<b>sᴇʟᴇᴄᴛ ᴀᴜᴅɪᴏ ᴛʀᴀᴄᴋs:</b>", reply_markup=InlineKeyboardMarkup(kb))
        
    except Exception as e:
        await msg.edit_text(f"<b>ᴇʀʀᴏʀ:</b> <code>{str(e)}</code>")

@Client.on_callback_query(filters.regex(r"^aud_(.*)_(.*)"))
async def toggle_audio(client, query):
    task_id = query.matches[0].group(1)
    idx = int(query.matches[0].group(2))
    
    if task_id not in utils.state.pending_selections:
        await query.answer("Expired.", show_alert=True)
        return
    if query.from_user.id != utils.state.pending_selections[task_id]["user_id"] and query.from_user.id != OWNER_ID:
        await query.answer("Not yours.", show_alert=True)
        return
        
    sel = utils.state.pending_selections[task_id]["selected"]
    if idx in sel:
        sel.remove(idx)
    else:
        sel.append(idx)
        
    audio_streams = utils.state.pending_selections[task_id]["audio_streams"]
    kb = []
    for s in audio_streams:
        s_idx = s.get("index")
        lang = s.get("tags", {}).get("language", "und")
        codec = s.get("codec_name", "unknown")
        title = s.get("tags", {}).get("title", f"Track {s_idx}")
        mark = "[X]" if s_idx in sel else "[ ]"
        btn_text = f"{mark} {lang} | {codec} | {title}"
        kb.append([InlineKeyboardButton(btn_text, callback_data=f"aud_{task_id}_{s_idx}")])
    
    kb.append([
        InlineKeyboardButton("Select All", callback_data=f"all_{task_id}"),
        InlineKeyboardButton("Done", callback_data=f"done_{task_id}")
    ])
    
    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    await query.answer()

# --- NEW SELECT ALL LOGIC ---
@Client.on_callback_query(filters.regex(r"^all_(.*)"))
async def select_all_audio(client, query):
    task_id = query.matches[0].group(1)
    
    if task_id not in utils.state.pending_selections:
        await query.answer("Expired.", show_alert=True)
        return
    if query.from_user.id != utils.state.pending_selections[task_id]["user_id"] and query.from_user.id != OWNER_ID:
        await query.answer("Not yours.", show_alert=True)
        return

    audio_streams = utils.state.pending_selections[task_id]["audio_streams"]
    # Add all audio indices to the selected list
    utils.state.pending_selections[task_id]["selected"] = [s.get("index") for s in audio_streams]
    
    kb = []
    for s in audio_streams:
        s_idx = s.get("index")
        lang = s.get("tags", {}).get("language", "und")
        codec = s.get("codec_name", "unknown")
        title = s.get("tags", {}).get("title", f"Track {s_idx}")
        btn_text = f"[X] {lang} | {codec} | {title}"
        kb.append([InlineKeyboardButton(btn_text, callback_data=f"aud_{task_id}_{s_idx}")])
        
    kb.append([
        InlineKeyboardButton("Select All", callback_data=f"all_{task_id}"),
        InlineKeyboardButton("Done", callback_data=f"done_{task_id}")
    ])
    
    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    await query.answer("All audio tracks selected!")

@Client.on_callback_query(filters.regex(r"^done_(.*)"))
async def finish_selection(client, query):
    task_id = query.matches[0].group(1)
    if task_id not in utils.state.pending_selections:
        await query.answer("Expired.", show_alert=True)
        return
    if query.from_user.id != utils.state.pending_selections[task_id]["user_id"] and query.from_user.id != OWNER_ID:
        await query.answer("Not yours.", show_alert=True)
        return
    await query.answer()
    asyncio.create_task(trigger_full_download(task_id, client))

async def trigger_full_download(task_id, client):
    if task_id not in utils.state.pending_selections:
        return
    data = utils.state.pending_selections[task_id]
    msg = data["msg"]
    media_msg = data["media_msg"]
    
    try:
        start_time = time.time()
        file_path = await client.download_media(
            media_msg,
            progress=update_progress,
            progress_args=(msg, start_time, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ", task_id)
        )
        if utils.state.cancel_flags.get(task_id):
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            await msg.edit_text("<b>ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
            utils.state.pending_selections.pop(task_id, None)
            return
            
        data["file_path"] = file_path
        await start_queue_task(task_id)
    except Exception as e:
        await msg.edit_text(f"<b>Download Error:</b> <code>{str(e)}</code>")
        utils.state.pending_selections.pop(task_id, None)

@Client.on_callback_query(filters.regex(r"^cancel_(.*)"))
async def cancel_task(client, query):
    task_id = query.matches[0].group(1)
    allowed = [OWNER_ID]
    if task_id in utils.state.pending_selections:
        allowed.append(utils.state.pending_selections[task_id]["user_id"])
    elif task_id in utils.state.active_tasks:
        allowed.append(utils.state.active_tasks[task_id]["user_id"])
    if query.from_user.id not in allowed:
        await query.answer("Not allowed.", show_alert=True)
        return
    
    utils.state.cancel_flags[task_id] = True
    if utils.state.active_process and getattr(utils.state, "current_task_id", None) == task_id:
        try:
            utils.state.active_process.terminate()
        except:
            pass
    await query.answer("Cancelled.")
    await query.message.edit_text("<b>ᴄᴀɴᴄᴇʟʟᴇᴅ ʙʏ ᴜsᴇʀ.</b>")

async def start_queue_task(task_id):
    if task_id not in utils.state.pending_selections:
        return
    data = utils.state.pending_selections.pop(task_id)
    msg = data["msg"]
    q_pos = utils.state.queue.qsize() + 1
    utils.state.active_tasks[task_id] = data
    await utils.state.queue.put(task_id)
    await msg.edit_text(
        f"<b>ᴀᴅᴅᴇᴅ ᴛᴏ ǫᴜᴇᴜᴇ</b>\n<b>ᴘᴏsɪᴛɪᴏɴ:</b> <code>{q_pos}</code>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"cancel_{task_id}")]])
    )
