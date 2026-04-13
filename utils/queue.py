import asyncio
import os
import time
import threading
import subprocess
from collections import deque

from utils.ffmpeg import build_ffmpeg_cmd, get_duration, parse_progress_line
from utils.progress import make_encode_text, make_download_text, make_upload_text
import utils.pyrogram_client as pyro_mgr

_queue = deque()
_lock = asyncio.Lock()
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


async def _run_job(job, bot, status_msg):
    chat_id = status_msg.chat.id
    msg_id = status_msg.message_id
    pyro_client = pyro_mgr.get_client()
    pyro_loop = pyro_mgr.get_loop()

    input_path = job["input_path"]
    output_path = job["output_path"]
    settings = job["settings"]
    selected_audio = job["selected_audio"]
    subtitle_indices = job["subtitle_indices"]
    source_message = job["source_message"]

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

    await edit("<b>ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ</b>\n\n<code>starting...</code>")

    download_done = threading.Event()
    download_error = [None]
    last_edit = [0]

    def progress_dl(current, total):
        now = time.time()
        if now - last_edit[0] < 3.5:
            return
        last_edit[0] = now
        elapsed = now - start_dl[0]
        text = make_download_text(current, total, elapsed)
        asyncio.run_coroutine_threadsafe(edit(text), _aiogram_loop)

    start_dl = [time.time()]

    async def do_download():
        try:
            await pyro_client.download_media(
                source_message,
                file_name=input_path,
                progress=progress_dl,
            )
        except Exception as e:
            download_error[0] = e
        finally:
            download_done.set()

    asyncio.run_coroutine_threadsafe(do_download(), pyro_loop)
    download_done.wait()

    if download_error[0]:
        raise download_error[0]

    await edit("<b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b>\n\n<code>starting...</code>")

    duration = get_duration(input_path)
    cmd = build_ffmpeg_cmd(input_path, output_path, settings, selected_audio, subtitle_indices)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    start_enc = time.time()
    last_edit[0] = 0
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
                    out_time_us = int(data.get("out_time_us", 0))
                    current_sec = out_time_us / 1_000_000
                    fps = data.get("fps", "0").strip()
                    speed_str = data.get("speed", "0x").replace("x", "").strip()
                    speed = float(speed_str) if speed_str else 0.0
                    pct = current_sec / duration if duration else 0
                    pct = min(pct, 1.0)
                    eta = (duration - current_sec) / speed if speed else 0
                    text = make_encode_text(speed, fps, elapsed, eta, pct)
                    await edit(text)
                except Exception:
                    pass

    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError("ffmpeg encoding failed")

    try:
        os.remove(input_path)
    except Exception:
        pass

    await edit("<b>ᴜᴘʟᴏᴀᴅɪɴɢ</b>\n\n<code>starting...</code>")

    upload_done = threading.Event()
    upload_error = [None]
    start_up = [time.time()]
    last_edit[0] = 0

    def progress_ul(current, total):
        now = time.time()
        if now - last_edit[0] < 3.5:
            return
        last_edit[0] = now
        elapsed = now - start_up[0]
        text = make_upload_text(current, total, elapsed)
        asyncio.run_coroutine_threadsafe(edit(text), _aiogram_loop)

    async def do_upload():
        try:
            await pyro_client.send_document(
                chat_id=chat_id,
                document=output_path,
                progress=progress_ul,
                reply_to_message_id=source_message.id,
            )
        except Exception as e:
            upload_error[0] = e
        finally:
            upload_done.set()

    asyncio.run_coroutine_threadsafe(do_upload(), pyro_loop)
    upload_done.wait()

    try:
        os.remove(output_path)
    except Exception:
        pass

    if upload_error[0]:
        raise upload_error[0]

    await edit("<b>done.</b>")
