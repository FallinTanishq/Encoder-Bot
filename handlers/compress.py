import os
import uuid

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from config import OWNER_ID
from utils.data import get_settings, get_approved_groups
from utils.ffmpeg import probe_tracks
from utils import queue as encode_queue

router = Router()

_sessions = {}


def _is_approved(chat_id):
    return chat_id in get_approved_groups() or chat_id == OWNER_ID


def _audio_button_text(track, selected):
    mark = "+" if selected else "-"
    title = f" ({track['title']})" if track["title"] else ""
    return f"[{mark}] {track['codec']} | {track['language']}{title} | {track['channels']}ch"


def _build_audio_keyboard(session_id, audio_tracks, selected):
    buttons = []
    for i, track in enumerate(audio_tracks):
        is_sel = i in selected
        buttons.append([InlineKeyboardButton(
            text=_audio_button_text(track, is_sel),
            callback_data=f"audio_toggle:{session_id}:{i}",
        )])
    buttons.append([
        InlineKeyboardButton(text="confirm", callback_data=f"audio_confirm:{session_id}"),
        InlineKeyboardButton(text="cancel", callback_data=f"audio_cancel:{session_id}"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("compress"))
async def cmd_compress(msg: Message):
    if not _is_approved(msg.chat.id):
        return

    replied = msg.reply_to_message
    if not replied:
        await msg.answer("<b>reply to a file with /compress</b>", parse_mode="HTML")
        return

    doc = replied.document or replied.video or replied.audio
    if not doc:
        await msg.answer("<b>replied message has no supported file.</b>", parse_mode="HTML")
        return

    file_name = getattr(doc, "file_name", None) or "file"
    ext = os.path.splitext(file_name)[1] or ".mkv"

    session_id = str(uuid.uuid4())[:8]
    tmp_in = f"downloads/{session_id}_in{ext}"
    tmp_out = f"downloads/{session_id}_out{ext}"
    os.makedirs("downloads", exist_ok=True)

    probe_msg = await msg.answer("<b>reading file info...</b>", parse_mode="HTML")

    try:
        pyro_client = __import__("utils.pyrogram_client", fromlist=["get_client"]).get_client()
        pyro_loop = __import__("utils.pyrogram_client", fromlist=["get_loop"]).get_loop()

        import asyncio
        done_evt = asyncio.Event()
        result = [None]

        async def fetch_and_probe():
            path = await pyro_client.download_media(replied, file_name=tmp_in)
            audio_tracks, subtitle_tracks = probe_tracks(path)
            result[0] = (audio_tracks, subtitle_tracks, path)
            done_evt.set()

        import threading

        def run_in_pyro():
            future = asyncio.run_coroutine_threadsafe(fetch_and_probe(), pyro_loop)
            future.result()

        t = threading.Thread(target=run_in_pyro, daemon=True)
        t.start()

        await asyncio.get_event_loop().run_in_executor(None, t.join)

        if result[0] is None:
            raise RuntimeError("could not probe file")

        audio_tracks, subtitle_tracks, actual_path = result[0]
        subtitle_indices = [s["index"] for s in subtitle_tracks]

    except Exception as e:
        await probe_msg.edit_text(f"<b>error reading file:</b> <code>{e}</code>", parse_mode="HTML")
        return

    if not audio_tracks:
        selected = set()
    else:
        selected = set(range(len(audio_tracks)))

    _sessions[session_id] = {
        "audio_tracks": audio_tracks,
        "subtitle_indices": subtitle_indices,
        "selected_audio": selected,
        "input_path": actual_path,
        "output_path": tmp_out,
        "ext": ext,
        "source_message": replied,
        "chat_id": msg.chat.id,
        "user_id": msg.from_user.id,
    }

    if not audio_tracks:
        await probe_msg.edit_text(
            "<b>no audio tracks found.</b> proceed with video only?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="start encoding", callback_data=f"audio_confirm:{session_id}"),
                InlineKeyboardButton(text="cancel", callback_data=f"audio_cancel:{session_id}"),
            ]]),
        )
        return

    await probe_msg.edit_text(
        "<b>select audio tracks to keep:</b>",
        parse_mode="HTML",
        reply_markup=_build_audio_keyboard(session_id, audio_tracks, selected),
    )


@router.callback_query(F.data.startswith("audio_toggle:"))
async def cb_audio_toggle(cb: CallbackQuery):
    _, session_id, idx_str = cb.data.split(":", 2)
    idx = int(idx_str)
    session = _sessions.get(session_id)
    if not session:
        await cb.answer("session expired")
        return
    sel = session["selected_audio"]
    if idx in sel:
        sel.discard(idx)
    else:
        sel.add(idx)
    await cb.message.edit_reply_markup(
        reply_markup=_build_audio_keyboard(session_id, session["audio_tracks"], sel)
    )
    await cb.answer()


@router.callback_query(F.data.startswith("audio_confirm:"))
async def cb_audio_confirm(cb: CallbackQuery):
    _, session_id = cb.data.split(":", 1)
    session = _sessions.pop(session_id, None)
    if not session:
        await cb.answer("session expired")
        return

    audio_tracks = session["audio_tracks"]
    selected = sorted(session["selected_audio"])
    selected_indices = [audio_tracks[i]["index"] for i in selected]
    selected_labels = [
        f"{audio_tracks[i]['codec']} | {audio_tracks[i]['language']} | {audio_tracks[i]['channels']}ch"
        for i in selected
    ] or ["none"]

    q_pos = encode_queue.queue_size() + 1
    summary = "\n".join(f"  - <code>{l}</code>" for l in selected_labels)

    await cb.message.edit_text(
        f"<b>queue position:</b> <code>{q_pos}</code>\n\n"
        f"<b>selected audio:</b>\n{summary}\n\n"
        f"<b>subtitles:</b> <code>all kept</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="start encoding", callback_data=f"encode_start:{session_id}"),
            InlineKeyboardButton(text="cancel", callback_data=f"encode_cancel:{session_id}"),
        ]]),
    )

    _sessions[session_id] = {
        **session,
        "selected_audio": selected_indices,
        "confirmed": True,
    }
    await cb.answer()


@router.callback_query(F.data.startswith("encode_start:"))
async def cb_encode_start(cb: CallbackQuery):
    _, session_id = cb.data.split(":", 1)
    session = _sessions.pop(session_id, None)
    if not session:
        await cb.answer("session expired")
        return

    await cb.message.edit_text("<b>queued.</b>", parse_mode="HTML")

    job = {
        "input_path": session["input_path"],
        "output_path": session["output_path"],
        "settings": get_settings(),
        "selected_audio": session["selected_audio"],
        "subtitle_indices": session["subtitle_indices"],
        "source_message": session["source_message"],
    }

    status_msg = await cb.message.answer("<b>starting...</b>", parse_mode="HTML")
    await encode_queue.enqueue(job, cb.bot, status_msg)
    await cb.answer()


@router.callback_query(F.data.startswith(("audio_cancel:", "encode_cancel:")))
async def cb_cancel(cb: CallbackQuery):
    parts = cb.data.split(":", 1)
    session_id = parts[1]
    _sessions.pop(session_id, None)
    await cb.message.edit_text("<b>cancelled.</b>", parse_mode="HTML")
    await cb.answer()
