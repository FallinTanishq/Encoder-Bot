from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from config import OWNER_ID
from utils.db import (
    approve_group, remove_group, is_approved,
    update_setting, get_settings
)

router = Router()

VALID_SETTINGS = {
    "crf", "preset", "tune", "aspect",
    "videocodec", "fps", "audiocodec", "bitrate"
}


def owner_only(handler):
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id != OWNER_ID:
            await message.reply(
                "<b>Permission denied.</b>\n"
                "Only the bot owner can use this command.",
                parse_mode="HTML"
            )
            return
        return await handler(message, *args, **kwargs)
    wrapper.__name__ = handler.__name__
    return wrapper


@router.message(Command("approve"))
@owner_only
async def cmd_approve(message: Message):
    if message.chat.type == "private":
        await message.reply(
            "<b>This command must be used inside a group.</b>",
            parse_mode="HTML"
        )
        return
    approve_group(message.chat.id)
    await message.reply(
        f"<b>Group approved.</b>\n"
        f"<code>{message.chat.title}</code> is now authorized to use this bot.",
        parse_mode="HTML"
    )


@router.message(Command("revoke"))
@owner_only
async def cmd_revoke(message: Message):
    if message.chat.type == "private":
        await message.reply(
            "<b>This command must be used inside a group.</b>",
            parse_mode="HTML"
        )
        return
    remove_group(message.chat.id)
    await message.reply(
        f"<b>Group revoked.</b>\n"
        f"<code>{message.chat.title}</code> has been removed from the authorized list.",
        parse_mode="HTML"
    )


async def _set_command(message: Message, key: str):
    if message.from_user.id != OWNER_ID:
        await message.reply(
            "<b>Permission denied.</b>\n"
            "Only the bot owner can change settings.",
            parse_mode="HTML"
        )
        return

    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await message.reply(
            f"<b>Usage:</b> <code>/{key} &lt;value&gt;</code>",
            parse_mode="HTML"
        )
        return

    value = parts[1].strip()

    if key == "fps" and value.lower() in ("source", "sameassource", "same"):
        value = "sameassource"

    if key == "tune" and value.lower() in ("none", "off", "disable"):
        value = None

    if key == "aspect" and value.lower() in ("none", "off", "source"):
        value = None

    update_setting(key, value)

    display = f"<code>{value}</code>" if value else "<i>disabled</i>"
    await message.reply(
        f"<b>{key}</b> updated to {display}.",
        parse_mode="HTML"
    )


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
