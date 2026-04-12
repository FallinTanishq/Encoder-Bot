import asyncio
from utils.db import get_settings


def build_ffmpeg_cmd(input_path, output_path, audio_indices, keep_all_subs=True):
    s = get_settings()

    cmd = ["ffmpeg", "-y", "-i", input_path]

    cmd += ["-map", "0:v:0"]

    for idx in audio_indices:
        cmd += ["-map", f"0:{idx}"]

    if keep_all_subs:
        cmd += ["-map", "0:s?"]

    cmd += ["-c:v", s["videocodec"]]
    cmd += ["-crf", str(s["crf"])]
    cmd += ["-preset", s["preset"]]

    if s.get("tune"):
        cmd += ["-tune", s["tune"]]

    if s.get("aspect"):
        cmd += ["-vf", f"scale={s['aspect'].replace('x', ':')}"]

    if s.get("fps") and s["fps"] != "sameassource":
        cmd += ["-r", s["fps"]]

    cmd += ["-c:a", s["audiocodec"]]
    cmd += ["-b:a", s["bitrate"]]

    if keep_all_subs:
        cmd += ["-c:s", "copy"]

    cmd += ["-progress", "pipe:1", "-nostats"]
    cmd.append(output_path)

    return cmd


async def run_ffmpeg(cmd, duration, progress_callback):
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    data = {}
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        line = line.decode().strip()
        if "=" in line:
            key, _, val = line.partition("=")
            data[key.strip()] = val.strip()

        if "out_time_ms" in data:
            try:
                elapsed_ms = int(data["out_time_ms"])
                elapsed_sec = elapsed_ms / 1_000_000
                speed_str = data.get("speed", "N/A").replace("x", "")
                fps_str = data.get("fps", "0")
                pct = min(elapsed_sec / duration * 100, 100) if duration else 0
                await progress_callback(elapsed_sec, speed_str, fps_str, pct)
            except (ValueError, ZeroDivisionError):
                pass

    await proc.wait()
    return proc.returncode
