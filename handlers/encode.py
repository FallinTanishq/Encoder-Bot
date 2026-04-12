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


class EncodeFlow(StatesGroup):
    selecting_audio = State()
    selecting_subtitle = State()
    confirming = State()
    encoding = State()


def group_guard(handler):
    async def wrapper(message: Message, state: FSMContext, *args, **kwargs):
        if message.chat.type == "private":
            return
        if not is_approved(message.chat.id):
            return
        return await handler(message, state, *args, **kwargs)
    wrapper.__name__ = handler.__name__
    return wrapper


def stream_keyboard(streams, selected, action_prefix, done_prefix):
    buttons = []
    for s in streams:
        idx = s.get("index")
        label = stream_label(s)
        tick = ">" if idx in selected else " "
        buttons.append([
            InlineKeyboardButton(
                text=f"{tick} {label}",
                callback_data=f"{action_prefix}:{idx}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="confirm", callback_data=done_prefix)
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(F.document | F.video)
@group_guard
async def handle_file(message: Message, state: FSMContext):
    doc = message.document or message.video
    file_name = getattr(doc, "file_name", None) or f"input_{doc.file_id}"
    file_id = doc.file_id

    await state.set_state(EncodeFlow.selecting_audio)
    await state.update_data(
        file_id=file_id,
        file_name=file_name,
        audio_selected=[],
        subtitle_selected=[],
        chat_id=message.chat.id,
        message_id=message.message_id,
    )

    status_msg = await message.reply(
        "<b>Downloading file...</b>",
        parse_mode="HTML"
    )

    bot: Bot = message.bot
    file = await bot.get_file(file_id)
    input_path = os.path.join(TEMP_DIR, file_name)

    total = doc.file_size or 0
    last_update = [0]

    async def dl_progress(downloaded, total_):
        now = time.time()
        if now - last_update[0] < 2:
            return
        last_update[0] = now
        try:
            await status_msg.edit_text(
                download_progress_text(downloaded, total_),
                parse_mode="HTML"
            )
        except Exception:
            pass

    await bot.download_file(file.file_path, destination=input_path, chunk_size=1024 * 512)

    info = await probe(input_path)
    audio_streams = get_streams_by_type(info, "audio")
    sub_streams = get_streams_by_type(info, "subtitle")

    await state.update_data(
        input_path=input_path,
        audio_streams=audio_streams,
        sub_streams=sub_streams,
    )

    if not audio_streams:
        await state.update_data(audio_selected=[])
        await _ask_subtitles(status_msg, state, sub_streams)
        return

    kb = stream_keyboard(audio_streams, [], "aud", "aud_done")
    await status_msg.edit_text(
        "<b>Select audio tracks to keep.</b>\n"
        "Tap to toggle, then confirm when ready.",
        reply_markup=kb,
        parse_mode="HTML"
    )


async def _ask_subtitles(msg: Message, state: FSMContext, sub_streams):
    await state.set_state(EncodeFlow.selecting_subtitle)
    if not sub_streams:
        await state.update_data(subtitle_selected=[])
        await _ask_confirm(msg, state)
        return
    data = await state.get_data()
    kb = stream_keyboard(sub_streams, data.get("subtitle_selected", []), "sub", "sub_done")
    await msg.edit_text(
        "<b>Select subtitle tracks to keep.</b>\n"
        "Tap to toggle, then confirm when ready.",
        reply_markup=kb,
        parse_mode="HTML"
    )


async def _ask_confirm(msg: Message, state: FSMContext):
    await state.set_state(EncodeFlow.confirming)
    data = await state.get_data()
    s = data
    audio_indices = s.get("audio_selected", [])
    sub_indices = s.get("subtitle_selected", [])
    audio_streams = s.get("audio_streams", [])
    sub_streams = s.get("sub_streams", [])

    def fmt_streams(streams, indices):
        chosen = [st for st in streams if st.get("index") in indices]
        if not chosen:
            return "<i>none</i>"
        return "\n".join(f"  <code>{stream_label(st)}</code>" for st in chosen)

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="start encoding", callback_data="start_encode"),
        InlineKeyboardButton(text="cancel", callback_data="cancel_encode"),
    ]])

    await msg.edit_text(
        f"<b>Ready to encode.</b>\n\n"
        f"<b>Audio tracks:</b>\n{fmt_streams(audio_streams, audio_indices)}\n\n"
        f"<b>Subtitle tracks:</b>\n{fmt_streams(sub_streams, sub_indices)}",
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
    kb = stream_keyboard(data["audio_streams"], selected, "aud", "aud_done")
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "aud_done", EncodeFlow.selecting_audio)
async def cb_audio_done(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await _ask_subtitles(cb.message, state, data.get("sub_streams", []))
    await cb.answer()


@router.callback_query(F.data.startswith("sub:"), EncodeFlow.selecting_subtitle)
async def cb_toggle_sub(cb: CallbackQuery, state: FSMContext):
    idx = int(cb.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("subtitle_selected", [])
    selected = [i for i in selected if i != idx] if idx in selected else selected + [idx]
    await state.update_data(subtitle_selected=selected)
    kb = stream_keyboard(data["sub_streams"], selected, "sub", "sub_done")
    await cb.message.edit_reply_markup(reply_markup=kb)
    await cb.answer()


@router.callback_query(F.data == "sub_done", EncodeFlow.selecting_subtitle)
async def cb_sub_done(cb: CallbackQuery, state: FSMContext):
    await _ask_confirm(cb.message, state)
    await cb.answer()


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
    await state.set_state(EncodeFlow.encoding)
    await cb.answer()

    data = await state.get_data()
    input_path = data["input_path"]
    file_name = data["file_name"]
    audio_indices = data.get("audio_selected", [])
    sub_indices = data.get("subtitle_selected", [])

    ext = get_extension(file_name)
    output_name = file_name.rsplit(".", 1)[0] + "_encoded" + ext
    output_path = os.path.join(TEMP_DIR, output_name)

    duration = await get_duration(input_path)
    cmd = build_ffmpeg_cmd(input_path, output_path, audio_indices, sub_indices)

    status_msg = cb.message
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

    if returncode != 0 or not os.path.exists(output_path):
        await status_msg.edit_text(
            "<b>Encoding failed.</b>\n"
            "Check your ffmpeg settings and try again.",
            parse_mode="HTML"
        )
        if os.path.exists(input_path):
            os.remove(input_path)
        await state.clear()
        return

    if os.path.exists(input_path):
        os.remove(input_path)

    file_size = os.path.getsize(output_path)
    await status_msg.edit_text(
        "<b>ᴜᴘʟᴏᴀᴅɪɴɢ</b>\n\n"
        "<b>ᴘʀᴏɢʀᴇss:</b> <code>0.0%</code>\n"
        "<code>[▱▱▱▱▱▱▱▱▱▱]</code>",
        parse_mode="HTML"
    )

    last_ul = [0]

    async def ul_callback(uploaded, total):
        now = time.time()
        if now - last_ul[0] < 3:
            return
        last_ul[0] = now
        try:
            await status_msg.edit_text(
                upload_progress_text(uploaded, total),
                parse_mode="HTML"
            )
        except Exception:
            pass

    bot: Bot = cb.message.bot
    with open(output_path, "rb") as f:
        await bot.send_document(
            chat_id=cb.message.chat.id,
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

    await state.clear()
