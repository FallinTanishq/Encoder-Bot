import time
from pyrogram import StopTransmission
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import utils.state

def format_time(seconds):
    if seconds < 0:
        seconds = 0
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h, {m}m, {s}s"
    return f"{m}m, {s}s"

def format_size(bytes_val):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.2f}{unit}"
        bytes_val /= 1024.0

def make_bar(percent):
    f = int(percent / 10)
    return "▰" * f + "▱" * (10 - f)

async def update_progress(current, total, msg, start_time, action, task_id):
    if utils.state.cancel_flags.get(task_id):
        raise StopTransmission
    now = time.time()
    if not hasattr(update_progress, "last_update"):
        update_progress.last_update = {}
    if now - update_progress.last_update.get(task_id, 0) < 3.5 and current != total:
        return
    update_progress.last_update[task_id] = now
    percent = (current / total) * 100 if total > 0 else 0
    elapsed = now - start_time
    speed = current / elapsed if elapsed > 0 else 0
    left = (total - current) / speed if speed > 0 else 0
    text = (f"<b>{action}</b>\n"
            f"<b>sɪᴢᴇ:</b> <code>{format_size(current)} / {format_size(total)}</code>\n"
            f"<b>ᴇʟᴀᴘsᴇᴅ:</b> <code>{format_time(elapsed)}</code>\n"
            f"<b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> <code>{format_time(left)}</code>\n"
            f"<b>ᴘʀᴏɢʀᴇss:</b> <code>{percent:.1f}%</code>\n"
            f"<code>[{make_bar(percent)}]</code>")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"cancel_{task_id}")]])
    try:
        await msg.edit_text(text, reply_markup=kb)
    except Exception:
        pass

async def encode_progress(msg, speed, fps, eta, percent, task_id):
    now = time.time()
    if not hasattr(encode_progress, "last_update"):
        encode_progress.last_update = {}
    if now - encode_progress.last_update.get(task_id, 0) < 3.5 and percent < 100:
        return
    encode_progress.last_update[task_id] = now
    
    text = (f"<b>🎥 ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss...</b>\n\n"
            f"<b>ᴇɴᴄᴏᴅᴇᴅ:</b> <code>{percent}%</code>\n"
            f"<b>sᴘᴇᴇᴅ:</b> <code>{speed}</code>\n"
            f"<b>fps:</b> <code>{fps} fps</code>\n"
            f"<b>ᴇᴛᴀ:</b> <code>{format_time(eta)}</code>\n"
            f"<code>[{make_bar(float(percent))}]</code>")
    
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Cancel", callback_data=f"cancel_{task_id}")]])
    try:
        await msg.edit_text(text, reply_markup=kb)
    except Exception:
        pass
