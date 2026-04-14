from pyrogram import Client, filters
from pyrogram.types import Message

from config import OWNER_ID
from utils.data import get_settings, save_settings, get_groups, save_groups, get_presets, save_presets

VALID_PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"}
VALID_TUNES = {"film", "animation", "grain", "stillimage", "fastdecode", "zerolatency", "none"}


def register(app: Client):

    @app.on_message(filters.command("crf") & filters.user(OWNER_ID))
    async def crf_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text("<b>Usage:</b> <code>/crf 23</code>", parse_mode="html")
            return
        val = parts[1].strip()
        s = get_settings()
        s["crf"] = val
        save_settings(s)
        await message.reply_text(f"<b>CRF</b> set to <code>{val}</code>", parse_mode="html")

    @app.on_message(filters.command("preset") & filters.user(OWNER_ID))
    async def preset_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text(
                f"<b>Usage:</b> <code>/preset veryfast</code>\n<b>Valid:</b> <code>{', '.join(sorted(VALID_PRESETS))}</code>",
                parse_mode="html"
            )
            return
        val = parts[1].strip().lower()
        if val not in VALID_PRESETS:
            await message.reply_text(
                f"<b>Invalid preset.</b> Valid values: <code>{', '.join(sorted(VALID_PRESETS))}</code>",
                parse_mode="html"
            )
            return
        s = get_settings()
        s["preset"] = val
        save_settings(s)
        await message.reply_text(f"<b>Preset</b> set to <code>{val}</code>", parse_mode="html")

    @app.on_message(filters.command("tune") & filters.user(OWNER_ID))
    async def tune_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text(
                f"<b>Usage:</b> <code>/tune animation</code>\n<b>Valid:</b> <code>{', '.join(sorted(VALID_TUNES))}</code>",
                parse_mode="html"
            )
            return
        val = parts[1].strip().lower()
        if val not in VALID_TUNES:
            await message.reply_text(
                f"<b>Invalid tune.</b> Valid values: <code>{', '.join(sorted(VALID_TUNES))}</code>",
                parse_mode="html"
            )
            return
        s = get_settings()
        s["tune"] = val
        save_settings(s)
        await message.reply_text(f"<b>Tune</b> set to <code>{val}</code>", parse_mode="html")

    @app.on_message(filters.command("aspect") & filters.user(OWNER_ID))
    async def aspect_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text("<b>Usage:</b> <code>/aspect 1920x1080</code> or <code>/aspect none</code>", parse_mode="html")
            return
        val = parts[1].strip()
        s = get_settings()
        s["aspect"] = val
        save_settings(s)
        await message.reply_text(f"<b>Aspect</b> set to <code>{val}</code>", parse_mode="html")

    @app.on_message(filters.command("videocodec") & filters.user(OWNER_ID))
    async def videocodec_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text("<b>Usage:</b> <code>/videocodec libx264</code>", parse_mode="html")
            return
        val = parts[1].strip()
        s = get_settings()
        s["videocodec"] = val
        save_settings(s)
        await message.reply_text(f"<b>Video Codec</b> set to <code>{val}</code>", parse_mode="html")

    @app.on_message(filters.command("fps") & filters.user(OWNER_ID))
    async def fps_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text("<b>Usage:</b> <code>/fps 24</code> or <code>/fps sameassource</code>", parse_mode="html")
            return
        val = parts[1].strip()
        s = get_settings()
        s["fps"] = val
        save_settings(s)
        await message.reply_text(f"<b>FPS</b> set to <code>{val}</code>", parse_mode="html")

    @app.on_message(filters.command("audiocodec") & filters.user(OWNER_ID))
    async def audiocodec_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text("<b>Usage:</b> <code>/audiocodec aac</code>", parse_mode="html")
            return
        val = parts[1].strip()
        s = get_settings()
        s["audiocodec"] = val
        save_settings(s)
        await message.reply_text(f"<b>Audio Codec</b> set to <code>{val}</code>", parse_mode="html")

    @app.on_message(filters.command("bitrate") & filters.user(OWNER_ID))
    async def bitrate_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text("<b>Usage:</b> <code>/bitrate 128k</code>", parse_mode="html")
            return
        val = parts[1].strip()
        s = get_settings()
        s["bitrate"] = val
        save_settings(s)
        await message.reply_text(f"<b>Bitrate</b> set to <code>{val}</code>", parse_mode="html")

    @app.on_message(filters.command("approve") & filters.user(OWNER_ID))
    async def approve_cmd(client, message: Message):
        if message.chat.type.name in ("PRIVATE",):
            await message.reply_text("<b>Use this command in a group.</b>", parse_mode="html")
            return
        groups = get_groups()
        chat_id = message.chat.id
        if chat_id not in groups:
            groups.append(chat_id)
            save_groups(groups)
        await message.reply_text(f"<b>Group approved:</b> <code>{chat_id}</code>", parse_mode="html")

    @app.on_message(filters.command("revoke") & filters.user(OWNER_ID))
    async def revoke_cmd(client, message: Message):
        if message.chat.type.name in ("PRIVATE",):
            await message.reply_text("<b>Use this command in a group.</b>", parse_mode="html")
            return
        groups = get_groups()
        chat_id = message.chat.id
        if chat_id in groups:
            groups.remove(chat_id)
            save_groups(groups)
        await message.reply_text(f"<b>Group revoked:</b> <code>{chat_id}</code>", parse_mode="html")

    @app.on_message(filters.command("approve"))
    async def approve_denied(client, message: Message):
        pass

    @app.on_message(filters.command("revoke"))
    async def revoke_denied(client, message: Message):
        pass

    @app.on_message(filters.command("savepreset") & filters.user(OWNER_ID))
    async def savepreset_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text("<b>Usage:</b> <code>/savepreset name</code>", parse_mode="html")
            return
        name = parts[1].strip().lower()
        s = get_settings()
        presets = get_presets()
        presets[name] = dict(s)
        save_presets(presets)
        await message.reply_text(f"<b>Preset saved:</b> <code>{name}</code>", parse_mode="html")

    @app.on_message(filters.command("p") & filters.user(OWNER_ID))
    async def load_preset_cmd(client, message: Message):
        parts = message.text.split(None, 1)
        if len(parts) < 2:
            await message.reply_text("<b>Usage:</b> <code>/p name</code>", parse_mode="html")
            return
        name = parts[1].strip().lower()
        presets = get_presets()
        if name not in presets:
            await message.reply_text(f"<b>Preset not found:</b> <code>{name}</code>", parse_mode="html")
            return
        loaded = presets[name]
        save_settings(loaded)
        text = (
            f"<b>Preset loaded:</b> <code>{name}</code>\n\n"
            f"<b>CRF:</b> <code>{loaded.get('crf')}</code>\n"
            f"<b>Preset:</b> <code>{loaded.get('preset')}</code>\n"
            f"<b>Tune:</b> <code>{loaded.get('tune')}</code>\n"
            f"<b>Aspect:</b> <code>{loaded.get('aspect')}</code>\n"
            f"<b>Video Codec:</b> <code>{loaded.get('videocodec')}</code>\n"
            f"<b>FPS:</b> <code>{loaded.get('fps')}</code>\n"
            f"<b>Audio Codec:</b> <code>{loaded.get('audiocodec')}</code>\n"
            f"<b>Bitrate:</b> <code>{loaded.get('bitrate')}</code>"
        )
        await message.reply_text(text, parse_mode="html")

    @app.on_message(filters.command("savepreset"))
    async def savepreset_denied(client, message: Message):
        await message.reply_text("<b>Access denied.</b>", parse_mode="html")

    @app.on_message(filters.command("p"))
    async def load_preset_denied(client, message: Message):
        await message.reply_text("<b>Access denied.</b>", parse_mode="html")
