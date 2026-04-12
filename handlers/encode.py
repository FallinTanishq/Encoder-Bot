import asyncio
import os
import time
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
from utils.db import is_approved
from utils.ffprobe import probe, get_streams_by_type, stream_label, get_duration, get_extension
from utils.ffmpeg import build_ffmpeg_cmd, run_ffmpeg
from utils.progress import (
    encode_progress_text, download_progress_text, upload_progress_text
)

router = Router()

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

encode_queue = asyncio.Queue()
queue_running = False


class EncodeFlow(StatesGroup):
    selecting_audio = State()
    confirming = State()
    encoding = State()


def audio_keyboard(streams, selected):
    buttons = []
    for s in streams:
        idx = s.get("index")
        codec = s.get("codec_name", "unknown")
        lang = s.get("tags", {}).get("language", "und")
        title = s.get("tags", {}).get("title", "")
        channels = s.get("channels", "")

        label_parts = [f"[{lang.upper()}]", codec.upper()]
        if title:
            label_parts.append(title)
        if channels:
            ch = "Stereo" if channels == 2 else "Mono" if channels == 1 else f"{channels}ch"
            label_parts.append(ch)

        label = " · ".join(label_parts)
        tick = "✓ " if idx in selected else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{tick}{label}",
                callback_data=f"aud:{idx}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="Confirm Selection", callback_data="aud_done")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def process_queue():
    global queue_running
    queue_running = True
    while not encode_queue.empty():
        task = await encode_queue.get()
        try:
            await run_encode_task(task)
        except Exception as e:
            try:
                await task["status_msg"].edit_text(
                    f"<b>Encoding failed.</b>\n<code>{e}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        encode_queue.task_done()
    queue_running = False


async def run_encode_task(task):
    input_path = task["input_path"]
    file_name = task["file_name"]
    audio_indices = task["audio_selected"]
    status_msg = task["status_msg"]
    bot: Bot = task["bot"]
    chat_id = task["chat_id"]

    ext = get_extension(file_name)
    output_name = file_name.rsplit(".", 1)[0] + "_encoded" + ext
    output_path = os.path.join(TEMP_DIR, output_name)

    duration = await get_duration(input_path)
    cmd = build_ffmpeg_cmd(input_path, output_path, audio_indices, keep_all_subs=True)

    await status_msg.edit_text(
        "<b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b>\n\n"
        "<b>ᴘʀᴏɢʀᴇss:</b> <code>0.0%</code>\n"
        "<code>[▱▱▱▱▱▱▱▱▱▱]</code>",
        parse_mode="HTML"
    )

    last_edit = [0]

    async def on_progress(elapsed, speed, fps, pct):
        now = time.time()
        if now - last_edit[0] < 4:
            return
        last_edit[0] = now
        try:
            await status_msg.edit_text(
                encode_progress_text(elapsed, speed, fps, pct, duration),
                parse_mode="HTML"
            )
        except Exception:
            pass

    returncode = await run_ffmpeg(cmd, duration, on_progress)

    if os.path.exists(input_path):
        os.remove(input_path)

    if returncode != 0 or not os.path.exists(output_path):
        await status_msg.edit_text(
            "<b>Encoding failed.</b>\n"
            "Check your ffmpeg settings and try again.",
            parse_mode="HTML"
        )
        return

    await status_msg.edit_text(
        "<b>ᴜᴘʟᴏᴀᴅɪɴɢ</b>\n\n"
        "<b>ᴘʀᴏɢʀᴇss:</b> <code>0.0%</code>\n"
        "<code>[▱▱▱▱▱▱▱▱▱▱]</code>",
        parse_mode="HTML"
    )

    with open(output_path, "rb") as f:
        await bot.send_document(
            chat_id=chat_id,
            document=f,
            filename=output_name,
        )

    if os.path.exists(output_path):
        os.remove(output_path)

    await status_msg.edit_text(
        "<b>Done.</b>\n"
        f"<code>{output_name}</code> has been uploaded.",
        parse_mode="HTML"
    )


@router.message(Command("compress"))
async def cmd_compress(message: Message, state: FSMContext):
    if message.chat.type == "private":
        return
    if not is_approved(message.chat.id):
        return

    replied = message.reply_to_message
    if not replied or not (replied.document or replied.video):
        await message.reply(
            "<b>Reply to a video or document file with /compress to encode it.</b>",
            parse_mode="HTML"
        )
        return

    doc = replied.document or replied.video
    file_name = getattr(doc, "file_name", None) or f"input_{doc.file_id}"
    file_id = doc.file_id

    status_msg = await message.reply(
        "<b>Downloading file...</b>",
        parse_mode="HTML"
    )

    bot: Bot = message.bot
    file = await bot.get_file(file_id)
    input_path = os.path.join(TEMP_DIR, file_name)

    await bot.download_file(file.file_path, destination=input_path, chunk_size=1024 * 512)

    info = await probe(input_path)
    audio_streams = get_streams_by_type(info, "audio")

    await state.update_data(
        input_path=input_path,
        file_name=file_name,
        audio_streams=audio_streams,
        audio_selected=[],
        chat_id=message.chat.id,
        status_msg_id=status_msg.message_id,
    )

    if not audio_streams:
        await state.update_data(audio_selected=[])
        await _queue_encode(message, state, status_msg, bot)
        return

    await state.set_state(EncodeFlow.selecting_audio)

    kb = audio_keyboard(audio_streams, [])
    await status_msg.edit_text(
        "<b>Select audio tracks to keep.</b>\n\n"
        "Tap a track to toggle it. You can select multiple.\n"
        "Press <b>Confirm Selection</b> when done.",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("aud:"), EncodeFlow.selecting_audio)
async def cb_toggle_audio(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("audio_selected", [])
    selected = [i for i in selected if i != idx] if idx in selected else selected + [idx]
    await state.update_data(audio_selected=selected)
    kb = audio_keyboard(data["audio_streams"], selected)
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "aud_done", EncodeFlow.selecting_audio)
async def cb_audio_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    audio_selected = data.get("audio_selected", [])
    audio_streams = data.get("audio_streams", [])

    if not audio_selected:
        await cb.answer("Select at least one audio track.", show_alert=True)
        return

    await cb.answer()

    def fmt_audio(streams, indices):
        chosen = [s for s in streams if s.get("index") in indices]
        lines = []
        for s in chosen:
            lang = s.get("tags", {}).get("language", "und")
            title = s.get("tags", {}).get("title", "")
            codec = s.get("codec_name", "unknown")
            line = f"  <code>[{lang.upper()}] {codec.upper()}"
            if title:
                line += f" · {title}"
            line += "</code>"
            lines.append(line)
        return "\n".join(lines)

    position = encode_queue.qsize() + (1 if queue_running else 0)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="start encoding", callback_data="start_encode"),
        InlineKeyboardButton(text="cancel", callback_data="cancel_encode"),
    ]])

    await cb.message.edit_text(
        f"<b>Ready to encode.</b>\n\n"
        f"<b>Audio tracks:</b>\n{fmt_audio(audio_streams, audio_selected)}\n\n"
        f"<b>Subtitles:</b> <i>all kept</i>\n\n"
        f"<b>Queue position:</b> <code>{position + 1}</code>",
        reply_markup=kb,
        parse_mode="HTML"
    )

    await state.set_state(EncodeFlow.confirming)


@router.callback_query(F.data == "cancel_encode", EncodeFlow.confirming)
async def cb_cancel(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    input_path = data.get("input_path")
    if input_path and os.path.exists(input_path):
        os.remove(input_path)
    await state.clear()
    await cb.message.edit_text(
        "<b>Encoding cancelled.</b>",
        parse_mode="HTML"
    )
    await cb.answer()


@router.callback_query(F.data == "start_encode", EncodeFlow.confirming)
async def cb_start_encode(cb: CallbackQuery, state: FSMContext):
    global queue_running
    await cb.answer()

    data = await state.get_data()

    task = {
        "input_path": data["input_path"],
        "file_name": data["file_name"],
        "audio_selected": data.get("audio_selected", []),
        "status_msg": cb.message,
        "bot": cb.message.bot,
        "chat_id": data["chat_id"],
    }

    position = encode_queue.qsize()

    await encode_queue.put(task)
    await state.clear()

    if not queue_running:
        asyncio.create_task(process_queue())
    else:
        await cb.message.edit_text(
            f"<b>Added to queue.</b>\n"
            f"<b>Position:</b> <code>{position + 1}</code>\n\n"
            "Your file will be encoded once the current job finishes.",
            parse_mode="HTML"
        )


async def _queue_encode(message, state, status_msg, bot):
    global queue_running
    data = await state.get_data()

    task = {
        "input_path": data["input_path"],
        "file_name": data["file_name"],
        "audio_selected": [],
        "status_msg": status_msg,
        "bot": bot,
        "chat_id": data["chat_id"],
    }

    await encode_queue.put(task)
    await state.clear()

    if not queue_running:
        asyncio.create_task(process_queue())
