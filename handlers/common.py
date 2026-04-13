import time
import os
import sys

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import OWNER_ID
from utils.data import get_settings, get_approved_groups

router = Router()


def _is_approved(chat_id):
    return chat_id in get_approved_groups() or chat_id == OWNER_ID


@router.message(Command("start"))
async def cmd_start(msg: Message):
    if not _is_approved(msg.chat.id):
        return
    await msg.answer(
        "<b>encoder bot</b>\n\n"
        "reply to a video or audio file with <code>/compress</code> to encode it.",
        parse_mode="HTML",
    )


@router.message(Command("ping"))
async def cmd_ping(msg: Message):
    if not _is_approved(msg.chat.id):
        return
    t = time.time()
    m = await msg.answer("pinging...")
    elapsed = (time.time() - t) * 1000
    await m.edit_text(f"<b>pong:</b> <code>{elapsed:.1f} ms</code>", parse_mode="HTML")


@router.message(Command("settings"))
async def cmd_settings(msg: Message):
    if not _is_approved(msg.chat.id):
        return
    s = get_settings()
    lines = "\n".join(
        f"<b>{k}:</b> <code>{v}</code>" for k, v in s.items()
    )
    await msg.answer(f"<b>current settings</b>\n\n{lines}", parse_mode="HTML")


@router.message(Command("restart"))
async def cmd_restart(msg: Message):
    if msg.from_user.id != OWNER_ID:
        return
    await msg.answer("<b>restarting...</b>", parse_mode="HTML")
    os.execv(sys.executable, [sys.executable] + sys.argv)
