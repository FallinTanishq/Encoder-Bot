from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import OWNER_ID
from utils.data import (
    approve_group, revoke_group, update_setting, get_approved_groups
)

router = Router()

VALID_PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"}
VALID_TUNES = {"film", "animation", "grain", "stillimage", "fastdecode", "zerolatency", "none"}


def _owner_only(msg: Message):
    return msg.from_user.id == OWNER_ID


@router.message(Command("approve"))
async def cmd_approve(msg: Message):
    if not _owner_only(msg):
        return
    approve_group(msg.chat.id)
    await msg.answer(f"<b>approved:</b> <code>{msg.chat.id}</code>", parse_mode="HTML")


@router.message(Command("revoke"))
async def cmd_revoke(msg: Message):
    if not _owner_only(msg):
        return
    revoke_group(msg.chat.id)
    await msg.answer(f"<b>revoked:</b> <code>{msg.chat.id}</code>", parse_mode="HTML")


async def _set_cmd(msg: Message, key, value, validator=None, error_msg=None):
    if not _owner_only(msg):
        return
    if validator and not validator(value):
        await msg.answer(f"<b>invalid value.</b> {error_msg or ''}", parse_mode="HTML")
        return
    update_setting(key, value)
    await msg.answer(f"<b>{key}</b> set to <code>{value}</code>", parse_mode="HTML")


def _arg(msg: Message):
    parts = msg.text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


@router.message(Command("crf"))
async def cmd_crf(msg: Message):
    val = _arg(msg)
    if not _owner_only(msg):
        return
    try:
        n = int(val)
        assert 0 <= n <= 51
    except Exception:
        await msg.answer("<b>crf must be an integer 0-51.</b>", parse_mode="HTML")
        return
    update_setting("crf", n)
    await msg.answer(f"<b>crf</b> set to <code>{n}</code>", parse_mode="HTML")


@router.message(Command("preset"))
async def cmd_preset(msg: Message):
    val = _arg(msg)
    await _set_cmd(msg, "preset", val, lambda v: v in VALID_PRESETS,
                   f"valid: {', '.join(sorted(VALID_PRESETS))}")


@router.message(Command("tune"))
async def cmd_tune(msg: Message):
    val = _arg(msg)
    await _set_cmd(msg, "tune", val, lambda v: v in VALID_TUNES,
                   f"valid: {', '.join(sorted(VALID_TUNES))}")


@router.message(Command("aspect"))
async def cmd_aspect(msg: Message):
    val = _arg(msg)
    if not _owner_only(msg):
        return
    if val != "none" and "x" not in val:
        await msg.answer("<b>format:</b> <code>1920x1080</code> or <code>none</code>", parse_mode="HTML")
        return
    update_setting("aspect", val)
    await msg.answer(f"<b>aspect</b> set to <code>{val}</code>", parse_mode="HTML")


@router.message(Command("videocodec"))
async def cmd_videocodec(msg: Message):
    val = _arg(msg)
    await _set_cmd(msg, "videocodec", val)


@router.message(Command("fps"))
async def cmd_fps(msg: Message):
    val = _arg(msg)
    if not _owner_only(msg):
        return
    if val != "sameassource":
        try:
            float(val)
        except ValueError:
            await msg.answer("<b>fps must be a number or</b> <code>sameassource</code>", parse_mode="HTML")
            return
    update_setting("fps", val)
    await msg.answer(f"<b>fps</b> set to <code>{val}</code>", parse_mode="HTML")


@router.message(Command("audiocodec"))
async def cmd_audiocodec(msg: Message):
    val = _arg(msg)
    await _set_cmd(msg, "audiocodec", val)


@router.message(Command("bitrate"))
async def cmd_bitrate(msg: Message):
    val = _arg(msg)
    await _set_cmd(msg, "bitrate", val)
