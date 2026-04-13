import time
import asyncio


def _bar(fraction, width=10):
    filled = int(fraction * width)
    return "▰" * filled + "▱" * (width - filled)


def _fmt_time(seconds):
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    if m:
        return f"{m}m, {s}s"
    return f"{s}s"


def make_download_text(done, total, elapsed):
    pct = done / total if total else 0
    done_mb = done / 1024 / 1024
    total_mb = total / 1024 / 1024
    speed = done / elapsed if elapsed else 0
    eta = (total - done) / speed if speed else 0
    return (
        "<b>ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ</b>\n\n"
        f"<b>sɪᴢᴇ:</b> <code>{done_mb:.1f} MB / {total_mb:.1f} MB</code>\n"
        f"<b>ᴘʀᴏɢʀᴇss:</b> <code>{pct*100:.1f}%</code>\n"
        f"<b>ᴇʟᴀᴘsᴇᴅ:</b> <code>{_fmt_time(elapsed)}</code>\n"
        f"<b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> <code>{_fmt_time(eta)}</code>\n"
        f"<code>[{_bar(pct)}]</code>"
    )


def make_upload_text(done, total, elapsed):
    pct = done / total if total else 0
    done_mb = done / 1024 / 1024
    total_mb = total / 1024 / 1024
    speed = done / elapsed if elapsed else 0
    eta = (total - done) / speed if speed else 0
    return (
        "<b>ᴜᴘʟᴏᴀᴅɪɴɢ</b>\n\n"
        f"<b>sɪᴢᴇ:</b> <code>{done_mb:.1f} MB / {total_mb:.1f} MB</code>\n"
        f"<b>ᴘʀᴏɢʀᴇss:</b> <code>{pct*100:.1f}%</code>\n"
        f"<b>ᴇʟᴀᴘsᴇᴅ:</b> <code>{_fmt_time(elapsed)}</code>\n"
        f"<b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> <code>{_fmt_time(eta)}</code>\n"
        f"<code>[{_bar(pct)}]</code>"
    )


def make_encode_text(speed, fps, elapsed, eta, pct):
    return (
        "<b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b>\n\n"
        f"<b>sᴘᴇᴇᴅ:</b> <code>{speed:.2f}x</code>\n"
        f"<b>fps:</b> <code>{fps}</code>\n"
        f"<b>ᴇʟᴀᴘsᴇᴅ:</b> <code>{_fmt_time(elapsed)}</code>\n"
        f"<b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> <code>{_fmt_time(eta)}</code>\n"
        f"<b>ᴘʀᴏɢʀᴇss:</b> <code>{pct*100:.1f}%</code>\n"
        f"<code>[{_bar(pct)}]</code>"
    )
