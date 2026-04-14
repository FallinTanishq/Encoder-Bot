import os
import time
import uuid
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID
from utils.db import get_groups
import utils.state
from utils.ffmpeg_utils import probe
from utils.progress import update_progress

@Client.on_message(filters.command("compress"))
async def compress_cmd(client, message):
    if message.chat.id not in get_groups() and message.chat.id != OWNER_ID:
        return
    if not message.reply_to_message or not message.reply_to_message.media:
        await message.reply_text("<b>ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴍᴇᴅɪᴀ ᴍᴇssᴀɢᴇ.</b>")
        return
    
    media = getattr(message.reply_to_message, message.reply_to_message.media.value)
    if not hasattr(media, "file_id"):
        return

    task_id = str(uuid.uuid4())
    msg = await message.reply_text("<b>ᴘʀᴏᴄᴇssɪɴɢ...</b>")
    
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
        start_time = time.time()
        file_path = await client.download_media(
            media,
            progress=update_progress,
            progress_args=(msg, start_time, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ", task_id)
        )
        
        if utils.state.cancel_flags.get(task_id):
            if os.path.exists(file_path):
                os.remove(file_path)
            await msg.edit_text("<b>ᴄᴀɴᴄᴇʟʟᴇᴅ.</b>")
            return
            
        utils.state.pending_selections[task_id]["file_path"] = file_path
        probe_data = await probe(file_path)
        streams = probe_data.get("streams", [])
        duration = float(probe_data.get("format", {}).get("duration", 0))
        utils.state.pending_selections[task_id]["duration"] = duration
        
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        utils.state.pending_selections[task_id]["audio_streams"] = audio_streams
        
        if not audio_streams:
            await start_queue_task(task_id)
            return
            
        kb = []
        for s in audio_streams:
            idx = s.get("index")
            lang = s.get("tags", {}).get("language", "und")
            codec = s.get("codec_name", "unknown")
            title = s.get("tags", {}).get("title", f"Track {idx}")
            btn_text = f"[ ] {lang} | {codec} | {title}"
            kb.append([InlineKeyboardButton(btn_text, callback_data=f"aud_{task_id}_{idx}")])
        kb.append([InlineKeyboardButton("Done", callback_data=f"done_{task_id}")])
        
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
    kb.append([InlineKeyboardButton("Done", callback_data=f"done_{task_id}")])
    
    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(kb))
    await query.answer()

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
    await start_queue_task(task_id)

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
