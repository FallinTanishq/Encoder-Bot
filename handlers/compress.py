import asyncio
import os
import time

from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import OWNER_ID
from utils.data import get_settings, get_groups
from utils.ffmpeg import (
    build_ffmpeg_cmd,
    format_progress_bar,
    format_time,
    get_audio_tracks,
    get_duration,
    parse_progress,
    probe_file,
)
import utils.queue as q

pending_jobs = {}
active_jobs = {}


def is_allowed(message: Message):
    if message.chat.type.name in ("PRIVATE",):
        return True
    return message.chat.id in get_groups()


def build_audio_keyboard(tracks, selected):
    buttons = []
    for t in tracks:
        idx = t["index"]
        label = f"{'[x] ' if idx in selected else '[ ] '}{t['codec']} | {t['language']} | {t['title'] or 'track'} | {t['channels']}ch"
        buttons.append([InlineKeyboardButton(label, callback_data=f"audio_toggle:{idx}")])
    buttons.append([
        InlineKeyboardButton("Confirm", callback_data="audio_confirm"),
        InlineKeyboardButton("Cancel", callback_data="audio_cancel"),
    ])
    return InlineKeyboardMarkup(buttons)


def register(app: Client):

    @app.on_message(filters.command("compress"))
    async def compress_cmd(client: Client, message: Message):
        if not is_allowed(message):
            return
        if not message.reply_to_message:
            await message.reply_text("<b>Reply to a file with /compress.</b>", parse_mode="html")
            return
        replied = message.reply_to_message
        media = replied.video or replied.audio or replied.document
        if not media:
            await message.reply_text("<b>Reply to a video or audio file.</b>", parse_mode="html")
            return

        job_key = f"{message.chat.id}:{message.from_user.id}"
        if job_key in pending_jobs:
            await message.reply_text("<b>You already have a pending job. Cancel it first.</b>", parse_mode="html")
            return

        status_msg = await message.reply_text("<b>Downloading file...</b>", parse_mode="html")

        cancel_event = asyncio.Event()

        async def download_with_progress():
            file_name = getattr(media, "file_name", None) or f"input_{media.file_id}"
            ext = os.path.splitext(file_name)[1] or ".mkv"
            input_path = f"downloads/{message.chat.id}_{message.id}{ext}"
            os.makedirs("downloads", exist_ok=True)

            last_update = [time.time()]
            total_size = getattr(media, "file_size", 0) or 0

            async def progress(current, total):
                if cancel_event.is_set():
                    raise asyncio.CancelledError()
                now = time.time()
                if now - last_update[0] < 3:
                    return
                last_update[0] = now
                pct = (current / total * 100) if total else 0
                cur_mb = current / 1024 / 1024
                tot_mb = total / 1024 / 1024
                bar = format_progress_bar(pct)
                cancel_kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Cancel", callback_data=f"cancel_process:{message.chat.id}:{message.id}:{message.from_user.id}")]
                ])
                try:
                    await status_msg.edit_text(
                        f"<b>Downloading</b>\n\n"
                        f"<b>Size:</b> <code>{cur_mb:.1f} MB / {tot_mb:.1f} MB</code>\n"
                        f"<b>Progress:</b> <code>{pct:.1f}%</code>\n"
                        f"<code>{bar}</code>",
                        parse_mode="html",
                        reply_markup=cancel_kb
                    )
                except Exception:
                    pass

            await client.download_media(replied, file_name=input_path, progress=progress)
            return input_path, ext

        active_jobs[job_key] = {"cancel_event": cancel_event, "user_id": message.from_user.id, "chat_id": message.chat.id}

        try:
            input_path, ext = await asyncio.wait_for(download_with_progress(), timeout=3600)
        except asyncio.CancelledError:
            await status_msg.edit_text("<b>Download cancelled.</b>", parse_mode="html")
            active_jobs.pop(job_key, None)
            return
        except Exception as e:
            await status_msg.edit_text(f"<b>Download failed:</b> <code>{e}</code>", parse_mode="html")
            active_jobs.pop(job_key, None)
            return

        if cancel_event.is_set():
            await status_msg.edit_text("<b>Download cancelled.</b>", parse_mode="html")
            active_jobs.pop(job_key, None)
            if os.path.exists(input_path):
                os.remove(input_path)
            return

        try:
            probe_data = await probe_file(input_path)
        except Exception as e:
            await status_msg.edit_text(f"<b>Failed to probe file:</b> <code>{e}</code>", parse_mode="html")
            active_jobs.pop(job_key, None)
            if os.path.exists(input_path):
                os.remove(input_path)
            return

        tracks = get_audio_tracks(probe_data)
        duration = get_duration(probe_data)
        selected_audio = set(t["index"] for t in tracks)

        pending_jobs[job_key] = {
            "input_path": input_path,
            "ext": ext,
            "tracks": tracks,
            "duration": duration,
            "selected_audio": selected_audio,
            "status_msg": status_msg,
            "user_id": message.from_user.id,
            "chat_id": message.chat.id,
            "message_id": message.id,
            "cancel_event": cancel_event,
        }

        if not tracks:
            await status_msg.edit_text(
                "<b>No audio tracks found. All subtitles will be kept.</b>\n\nPress <b>Start Encoding</b> to begin.",
                parse_mode="html",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Start Encoding", callback_data=f"encode_start:{job_key}"),
                        InlineKeyboardButton("Cancel", callback_data=f"encode_cancel:{job_key}"),
                    ]
                ])
            )
        else:
            kb = build_audio_keyboard(tracks, selected_audio)
            await status_msg.edit_text(
                "<b>Select audio tracks to keep:</b>",
                parse_mode="html",
                reply_markup=kb
            )

    @app.on_callback_query(filters.regex(r"^audio_toggle:(\d+)$"))
    async def audio_toggle(client: Client, cb: CallbackQuery):
        job_key = _find_job_key(cb)
        if not job_key:
            await cb.answer("Session expired.", show_alert=True)
            return
        job = pending_jobs[job_key]
        idx = int(cb.matches[0].group(1))
        if idx in job["selected_audio"]:
            job["selected_audio"].discard(idx)
        else:
            job["selected_audio"].add(idx)
        kb = build_audio_keyboard(job["tracks"], job["selected_audio"])
        await cb.edit_message_reply_markup(kb)
        await cb.answer()

    @app.on_callback_query(filters.regex(r"^audio_confirm$"))
    async def audio_confirm(client: Client, cb: CallbackQuery):
        job_key = _find_job_key(cb)
        if not job_key:
            await cb.answer("Session expired.", show_alert=True)
            return
        job = pending_jobs[job_key]
        selected = job["selected_audio"]
        tracks = job["tracks"]
        selected_names = [
            f"{t['codec']} | {t['language']} | {t['title'] or 'track'} | {t['channels']}ch"
            for t in tracks if t["index"] in selected
        ]
        track_text = "\n".join(f"- <code>{n}</code>" for n in selected_names) or "<code>none</code>"
        queue_pos = q.encode_queue.qsize() + (1 if q.active_task and not q.active_task.done() else 0)

        await cb.edit_message_text(
            f"<b>Selected Audio Tracks:</b>\n{track_text}\n\n"
            f"<b>Queue Position:</b> <code>{queue_pos + 1}</code>",
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Start Encoding", callback_data=f"encode_start:{job_key}"),
                    InlineKeyboardButton("Cancel", callback_data=f"encode_cancel:{job_key}"),
                ]
            ])
        )
        await cb.answer()

    @app.on_callback_query(filters.regex(r"^audio_cancel$"))
    async def audio_cancel(client: Client, cb: CallbackQuery):
        job_key = _find_job_key(cb)
        if job_key:
            job = pending_jobs.pop(job_key, None)
            if job and os.path.exists(job["input_path"]):
                os.remove(job["input_path"])
            active_jobs.pop(job_key, None)
        await cb.edit_message_text("<b>Cancelled.</b>", parse_mode="html")
        await cb.answer()

    @app.on_callback_query(filters.regex(r"^encode_cancel:(.+)$"))
    async def encode_cancel(client: Client, cb: CallbackQuery):
        job_key = cb.matches[0].group(1)
        job = pending_jobs.pop(job_key, None)
        if job:
            if os.path.exists(job["input_path"]):
                os.remove(job["input_path"])
            active_jobs.pop(job_key, None)
        await cb.edit_message_text("<b>Cancelled.</b>", parse_mode="html")
        await cb.answer()

    @app.on_callback_query(filters.regex(r"^encode_start:(.+)$"))
    async def encode_start(client: Client, cb: CallbackQuery):
        job_key = cb.matches[0].group(1)
        job = pending_jobs.get(job_key)
        if not job:
            await cb.answer("Session expired.", show_alert=True)
            return
        await cb.answer("Added to queue.")
        await cb.edit_message_text("<b>Added to encoding queue...</b>", parse_mode="html")
        await q.encode_queue.put((job_key, job, client))

    @app.on_callback_query(filters.regex(r"^cancel_process:(\d+):(\d+):(\d+)$"))
    async def cancel_process(client: Client, cb: CallbackQuery):
        chat_id = int(cb.matches[0].group(1))
        message_id = int(cb.matches[0].group(2))
        owner_id = int(cb.matches[0].group(3))

        if cb.from_user.id != owner_id and cb.from_user.id != OWNER_ID:
            await cb.answer("You cannot cancel this.", show_alert=True)
            return

        for jk, job in list(active_jobs.items()):
            if job["chat_id"] == chat_id and job["user_id"] == owner_id:
                job["cancel_event"].set()
                ffmpeg_proc = job.get("ffmpeg_proc")
                if ffmpeg_proc:
                    try:
                        ffmpeg_proc.terminate()
                    except Exception:
                        pass
                await cb.answer("Cancelling...", show_alert=False)
                return

        await cb.answer("Nothing to cancel.", show_alert=True)


def _find_job_key(cb: CallbackQuery):
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id
    key = f"{chat_id}:{user_id}"
    if key in pending_jobs:
        return key
    for k, job in pending_jobs.items():
        if job["chat_id"] == chat_id and job["user_id"] == user_id:
            return k
    return None


async def run_encode_worker(app: Client):
    while True:
        job_key, job, client = await q.encode_queue.get()

        q.active_task = asyncio.current_task()
        cancel_event = job["cancel_event"]

        input_path = job["input_path"]
        ext = job["ext"]
        selected_audio = list(job["selected_audio"])
        duration = job["duration"]
        status_msg = job["status_msg"]
        chat_id = job["chat_id"]
        user_id = job["user_id"]
        message_id = job["message_id"]

        output_path = input_path.replace("downloads/", "outputs/").replace(ext, f"_encoded{ext}")
        os.makedirs("outputs", exist_ok=True)

        settings = get_settings()
        cmd = build_ffmpeg_cmd(input_path, output_path, settings, selected_audio)

        cancel_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data=f"cancel_process:{chat_id}:{message_id}:{user_id}")]
        ])

        try:
            await status_msg.edit_text(
                "<b>Encoding in progress...</b>",
                parse_mode="html",
                reply_markup=cancel_kb
            )
        except Exception:
            pass

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            active_jobs[job_key]["ffmpeg_proc"] = proc

            start_time = time.time()
            last_update = time.time()
            progress_buf = []

            async def read_progress():
                nonlocal last_update
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="ignore").strip()
                    progress_buf.append(decoded)
                    if "progress=" in decoded:
                        chunk = "\n".join(progress_buf)
                        progress_buf.clear()
                        now = time.time()
                        if now - last_update >= 3:
                            last_update = now
                            elapsed = now - start_time
                            pdata = parse_progress(chunk, duration)
                            pct = pdata["percent"]
                            speed = pdata["speed"]
                            fps = pdata["fps"]
                            remaining = ((duration - pdata["current"]) / speed) if speed > 0 else 0
                            bar = format_progress_bar(pct)
                            try:
                                await status_msg.edit_text(
                                    f"<b>Encoding in Progress</b>\n\n"
                                    f"<b>Speed:</b> <code>{speed:.2f}x</code>\n"
                                    f"<b>FPS:</b> <code>{fps:.0f}</code>\n"
                                    f"<b>Elapsed:</b> <code>{format_time(elapsed)}</code>\n"
                                    f"<b>Time Left:</b> <code>{format_time(remaining)}</code>\n"
                                    f"<b>Progress:</b> <code>{pct:.1f}%</code>\n"
                                    f"<code>{bar}</code>",
                                    parse_mode="html",
                                    reply_markup=cancel_kb
                                )
                            except Exception:
                                pass

            read_task = asyncio.create_task(read_progress())

            async def check_cancel():
                while not cancel_event.is_set():
                    await asyncio.sleep(1)
                try:
                    proc.terminate()
                except Exception:
                    pass

            cancel_task = asyncio.create_task(check_cancel())

            await proc.wait()
            read_task.cancel()
            cancel_task.cancel()

        except Exception as e:
            await status_msg.edit_text(f"<b>Encoding failed:</b> <code>{e}</code>", parse_mode="html")
            pending_jobs.pop(job_key, None)
            active_jobs.pop(job_key, None)
            if os.path.exists(input_path):
                os.remove(input_path)
            q.encode_queue.task_done()
            continue

        if cancel_event.is_set() or proc.returncode != 0:
            await status_msg.edit_text("<b>Encoding cancelled or failed.</b>", parse_mode="html")
            pending_jobs.pop(job_key, None)
            active_jobs.pop(job_key, None)
            for p in [input_path, output_path]:
                if os.path.exists(p):
                    os.remove(p)
            q.encode_queue.task_done()
            continue

        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        last_update_upload = [time.time()]

        try:
            await status_msg.edit_text("<b>Uploading encoded file...</b>", parse_mode="html", reply_markup=cancel_kb)
        except Exception:
            pass

        upload_cancelled = False

        async def upload_progress(current, total):
            nonlocal upload_cancelled
            if cancel_event.is_set():
                upload_cancelled = True
                return
            now = time.time()
            if now - last_update_upload[0] < 3:
                return
            last_update_upload[0] = now
            pct = (current / total * 100) if total else 0
            cur_mb = current / 1024 / 1024
            tot_mb = total / 1024 / 1024
            bar = format_progress_bar(pct)
            try:
                await status_msg.edit_text(
                    f"<b>Uploading</b>\n\n"
                    f"<b>Size:</b> <code>{cur_mb:.1f} MB / {tot_mb:.1f} MB</code>\n"
                    f"<b>Progress:</b> <code>{pct:.1f}%</code>\n"
                    f"<code>{bar}</code>",
                    parse_mode="html",
                    reply_markup=cancel_kb
                )
            except Exception:
                pass

        try:
            await client.send_document(
                chat_id=chat_id,
                document=output_path,
                progress=upload_progress,
            )
            await status_msg.edit_text("<b>Done. File uploaded successfully.</b>", parse_mode="html")
        except Exception as e:
            await status_msg.edit_text(f"<b>Upload failed:</b> <code>{e}</code>", parse_mode="html")

        for p in [input_path, output_path]:
            if os.path.exists(p):
                os.remove(p)

        pending_jobs.pop(job_key, None)
        active_jobs.pop(job_key, None)
        q.encode_queue.task_done()
