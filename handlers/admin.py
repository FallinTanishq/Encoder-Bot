from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from config import OWNER_ID
from utils.db import approve_group, remove_group, update_setting

router = Router()

VALID_PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"}
VALID_TUNES = {"film", "animation", "grain", "stillimage", "fastdecode", "zerolatency", "none"}


async def _check_owner(message: Message) -> bool:
    if message.from_user.id != OWNER_ID:
        await message.reply(
            "<b>Permission denied.</b>\n"
            "Only the bot owner can use this command.",
            parse_mode="HTML"
        )
        return False
    return True


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply(
        "<b>Encoder Bot</b>\n\n"
        "Reply to any file in an approved group with /compress to encode it.\n"
        "Use /settings to view current encoder configuration.",
        parse_mode="HTML"
    )


@router.message(Command("ping"))
async def cmd_ping(message: Message):
    import time
    start = time.time()
    sent = await message.reply("<b>Pong!</b>", parse_mode="HTML")
    elapsed = (time.time() - start) * 1000
    await sent.edit_text(f"<b>Pong!</b>  <code>{elapsed:.0f}ms</code>", parse_mode="HTML")
    

@router.message(Command("restart"))
async def cmd_restart(message: Message):
    if not await _check_owner(message):
        return
    await message.reply("<b>Restarting...</b>", parse_mode="HTML")
    import os, sys
    os.execv(sys.executable, [sys.executable] + sys.argv)


@router.message(Command("approve"))
async def cmd_approve(message: Message):
    if not await _check_owner(message):
        return
    if message.chat.type == "private":
        await message.reply("<b>This command must be used inside a group.</b>", parse_mode="HTML")
        return
    approve_group(message.chat.id)
    await message.reply(
        f"<b>Group approved.</b>\n"
        f"<code>{message.chat.title}</code> is now authorized to use this bot.",
        parse_mode="HTML"
    )


@router.message(Command("revoke"))
async def cmd_revoke(message: Message):
    if not await _check_owner(message):
        return
    if message.chat.type == "private":
        await message.reply("<b>This command must be used inside a group.</b>", parse_mode="HTML")
        return
    remove_group(message.chat.id)
    await message.reply(
        f"<b>Group revoked.</b>\n"
        f"<code>{message.chat.title}</code> has been removed from the authorized list.",
        parse_mode="HTML"
    )


async def _set_command(message: Message, key: str):
    if not await _check_owner(message):
        return
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(f"<b>Usage:</b> <code>/{key} &lt;value&gt;</code>", parse_mode="HTML")
        return

    value = parts[1].strip().lower()

    if key == "preset":
        if value not in VALID_PRESETS:
            opts = " · ".join(sorted(VALID_PRESETS, key=list(VALID_PRESETS).index if hasattr(VALID_PRESETS, 'index') else str))
            await message.reply(
                f"<b>Invalid preset.</b> Choose from:\n\n"
                f"<code>ultrafast · superfast · veryfast · faster · fast · medium · slow · slower · veryslow</code>",
                parse_mode="HTML"
            )
            return

    if key == "tune":
        if value not in VALID_TUNES:
            await message.reply(
                f"<b>Invalid tune.</b> Choose from:\n\n"
                f"<code>film · animation · grain · stillimage · fastdecode · zerolatency · none</code>",
                parse_mode="HTML"
            )
            return
        if value == "none":
            value = None

    if key == "fps" and value in ("source", "sameassource", "same"):
        value = "sameassource"

    if key == "aspect" and value in ("none", "off", "source"):
        value = None

    update_setting(key, value)
    display = f"<code>{value}</code>" if value else "<i>disabled</i>"
    await message.reply(f"<b>{key}</b> updated to {display}.", parse_mode="HTML")


@router.message(Command("crf"))
async def cmd_crf(message: Message):
    await _set_command(message, "crf")

@router.message(Command("preset"))
async def cmd_preset(message: Message):
    await _set_command(message, "preset")

@router.message(Command("tune"))
async def cmd_tune(message: Message):
    await _set_command(message, "tune")

@router.message(Command("aspect"))
async def cmd_aspect(message: Message):
    await _set_command(message, "aspect")

@router.message(Command("videocodec"))
async def cmd_videocodec(message: Message):
    await _set_command(message, "videocodec")

@router.message(Command("fps"))
async def cmd_fps(message: Message):
    await _set_command(message, "fps")

@router.message(Command("audiocodec"))
async def cmd_audiocodec(message: Message):
    await _set_command(message, "audiocodec")

@router.message(Command("bitrate"))
async def cmd_bitrate(message: Message):
    await _set_command(message, "bitrate")
