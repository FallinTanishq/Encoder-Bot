from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from utils.db import get_settings

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    s = get_settings()

    fps_display = s.get("fps") or "sameassource"
    tune_display = f"<code>{s['tune']}</code>" if s.get("tune") else "<i>none</i>"
    aspect_display = f"<code>{s['aspect']}</code>" if s.get("aspect") else "<i>sameassource</i>"

    text = (
        "<b>Current Encoder Settings</b>\n\n"
        f"<b>Video Codec</b>    <code>{s['videocodec']}</code>\n"
        f"<b>CRF</b>           <code>{s['crf']}</code>\n"
        f"<b>Preset</b>        <code>{s['preset']}</code>\n"
        f"<b>Tune</b>          {tune_display}\n"
        f"<b>Aspect</b>        {aspect_display}\n"
        f"<b>FPS</b>           <code>{fps_display}</code>\n\n"
        f"<b>Audio Codec</b>   <code>{s['audiocodec']}</code>\n"
        f"<b>Audio Bitrate</b> <code>{s['bitrate']}</code>"
    )

    await message.reply(text, parse_mode="HTML")
