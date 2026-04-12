def progress_bar(pct, length=10):
    filled = int(pct / 100 * length)
    bar = "▰" * filled + "▱" * (length - filled)
    return f"[{bar}]"


def fmt_time(seconds):
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h, {m}m, {s}s"
    if m:
        return f"{m}m, {s}s"
    return f"{s}s"


def encode_progress_text(elapsed, speed, fps, pct, duration):
    remaining = ((duration - elapsed) / float(speed)) if speed and float(speed) > 0 else 0
    bar = progress_bar(pct)
    return (
        f"<b>ᴇɴᴄᴏᴅɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss</b>\n\n"
        f"<b>sᴘᴇᴇᴅ:</b> <code>{speed}x</code>\n"
        f"<b>fps:</b> <code>{fps}</code>\n"
        f"<b>ᴇʟᴀᴘsᴇᴅ:</b> <code>{fmt_time(elapsed)}</code>\n"
        f"<b>ᴛɪᴍᴇ ʟᴇғᴛ:</b> <code>{fmt_time(remaining)}</code>\n"
        f"<b>ᴘʀᴏɢʀᴇss:</b> <code>{pct:.1f}%</code>\n"
        f"<code>{bar}</code>"
    )


def download_progress_text(downloaded, total):
    pct = (downloaded / total * 100) if total else 0
    bar = progress_bar(pct)
    done_mb = downloaded / 1024 / 1024
    total_mb = total / 1024 / 1024
    return (
        f"<b>ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ</b>\n\n"
        f"<b>ᴘʀᴏɢʀᴇss:</b> <code>{pct:.1f}%</code>\n"
        f"<b>sɪᴢᴇ:</b> <code>{done_mb:.1f} / {total_mb:.1f} MB</code>\n"
        f"<code>{bar}</code>"
    )


def upload_progress_text(uploaded, total):
    pct = (uploaded / total * 100) if total else 0
    bar = progress_bar(pct)
    done_mb = uploaded / 1024 / 1024
    total_mb = total / 1024 / 1024
    return (
        f"<b>ᴜᴘʟᴏᴀᴅɪɴɢ</b>\n\n"
        f"<b>ᴘʀᴏɢʀᴇss:</b> <code>{pct:.1f}%</code>\n"
        f"<b>sɪᴢᴇ:</b> <code>{done_mb:.1f} / {total_mb:.1f} MB</code>\n"
        f"<code>{bar}</code>"
    )
