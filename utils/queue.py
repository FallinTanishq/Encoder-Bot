import asyncio
import os
import time
import threading
from collections import deque

from utils.ffmpeg import build_ffmpeg_cmd, get_duration, parse_progress_line
from utils.progress import make_encode_text, make_download_text, make_upload_text
import utils.pyrogram_client as pyro_mgr

_queue = deque()
_processing = False
_aiogram_loop: asyncio.AbstractEventLoop = None


def set_aiogram_loop(loop):
    global _aiogram_loop
    _aiogram_loop = loop


def queue_size():
    return len(_queue)


async def enqueue(job: dict, bot, status_msg):
    _queue.append((job, bot, status_msg))
    global _processing
    if not _processing:
        asyncio.create_task(_process_next())


async def _process_next():
    global _processing
    _processing = True
    while _queue:
        job, bot, status_msg = _queue.popleft()
        try:
            await _run_job(job, bot, status_msg)
        except Exception as e:
            try:
                await bot.edit_message_text(
                    chat_id=status_msg.chat.id,
                    message_id=status_msg.message_id,
                    text=f"<b>error:</b> <code>{e}</code>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
    _processing = False


def _run_on_pyro_loop_blocking(coro):
    """
    Schedule a coroutine on Pyrogram's loop and block until it completes.
    Must be called from a plain thread (not from inside an async context).
    Propagates any exception raised inside the coroutine.
    """
    future = asyncio.run_coroutine_threadsafe(coro, pyro_mgr.get_loop())
    return future.result()


async def _run_job(job, bot, status_msg):
    chat_id = status_msg.chat.id
    msg_id = status_msg.message_id

    input_path = job["input_path"]
    output_path = job["output_path"]
    settings = job["settings"]
    selected_audio = job["selected_audio"]
    subtitle_indices = job["subtitle_indices"]
    file_id = job["file_id"]
    source_msg_id = job["source_msg_id"]

    # ── helpers ──────────────────────────────────────────────────────────
    async def edit(text):
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                parse_mode="HTML",
            )
        except Exception:
            pass

    def edit_sync(text):
        """Send an edit from a non-aiogram thread."""
        asyncio.run_coroutine_threadsafe(edit(text), _aiogram_loop)

    # ── DOWNLOAD (must run on pyro_loop) ─────────────────────────────────
    await edit("<b>ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ</b>\n\n<code>starting...</code>")

    last_edit = [0.0]
    start_dl = [time.time()]

    def progress_dl(current, total):
        now = time.time()
        if now - last_edit[0] < 3.5:
            return
        last_edit[0] = now
        edit_sync(make_download_text(current, total, now - start_dl[0]))

    async def do_download():
        pyro_client = pyro_mgr.get_client()
        await pyro_client.download_media(
            file_id,
            file_name=input_path,
            progress=progress_dl,
        )

    dl_error = [None]
    dl_done = threading.Event()

    def dl_thread():
        try:
            _run_on_pyro_loop_blocking(do_download())
        except Exception as e:
            dl_error[0] = e
        finally:
            dl_done.set()

    threading.Thread(target=dl_thread, daemon=True).start()
    await asyncio.get_event_loop().run_in_executor(None, dl_done.wait)

    if dl_error[0]:
        raise dl_error[0]

    # ── ENCODE (asyncio subprocess on aiogram loop — fine) ───────────────
    await edit("<b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b>\n\n<code>starting...</code>")

    duration = get_duration(input_path)
    cmd = build_ffmpeg_cmd(input_path, output_path, settings, selected_audio, subtitle_indices)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    start_enc = time.time()
    last_edit[0] = 0.0
    buf = ""

    while True:
        chunk = await proc.stdout.read(512)
        if not chunk:
            break
        buf += chunk.decode(errors="ignore")
        if "progress=" in buf:
            now = time.time()
            if now - last_edit[0] >= 3.5:
                last_edit[0] = now
                elapsed = now - start_enc
                data = parse_progress_line(buf)
                buf = ""
                try:
                    current_sec = int(data.get("out_time_us", 0)) / 1_000_000
                    fps = data.get("fps", "0").strip()
                    speed = float(data.get("speed", "0x").replace("x", "").strip() or 0)
                    pct = min(current_sec / duration if duration else 0, 1.0)
                    eta = (duration - current_sec) / speed if speed else 0
                    await edit(make_encode_text(speed, fps, elapsed, eta, pct))
                except Exception:
                    pass

    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg encoding failed")

    try:
        os.remove(input_path)
    except Exception:
        pass

    # ── UPLOAD (must run on pyro_loop) ────────────────────────────────────
    await edit("<b>ᴜᴘʟᴏᴀᴅɪɴɢ</b>\n\n<code>starting...</code>")

    start_up = [time.time()]
    last_edit[0] = 0.0

    def progress_ul(current, total):
        now = time.time()
        if now - last_edit[0] < 3.5:
            return
        last_edit[0] = now
        edit_sync(make_upload_text(current, total, now - start_up[0]))

    async def do_upload():
        pyro_client = pyro_mgr.get_client()
        await pyro_client.send_document(
            chat_id=chat_id,
            document=output_path,
            progress=progress_ul,
            reply_to_message_id=source_msg_id,
        )

    ul_error = [None]
    ul_done = threading.Event()

    def ul_thread():
        try:
            _run_on_pyro_loop_blocking(do_upload())
        except Exception as e:
            ul_error[0] = e
        finally:
            ul_done.set()

    threading.Thread(target=ul_thread, daemon=True).start()
    await asyncio.get_event_loop().run_in_executor(None, ul_done.wait)

    try:
        os.remove(output_path)
    except Exception:
        pass

    if ul_error[0]:
        raise ul_error[0]

    await edit("<b>done.</b>")
