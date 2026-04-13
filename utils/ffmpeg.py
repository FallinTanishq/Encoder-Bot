import asyncio
import json
import os
import re
import subprocess


async def probe_file(path):
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", path
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, _ = await proc.communicate()
    return json.loads(stdout)


def get_audio_tracks(probe_data):
    tracks = []
    for stream in probe_data.get("streams", []):
        if stream.get("codec_type") == "audio":
            idx = stream.get("index")
            codec = stream.get("codec_name", "unknown")
            lang = stream.get("tags", {}).get("language", "und")
            title = stream.get("tags", {}).get("title", "")
            channels = stream.get("channels", 0)
            tracks.append({
                "index": idx,
                "codec": codec,
                "language": lang,
                "title": title,
                "channels": channels,
            })
    return tracks


def get_duration(probe_data):
    for stream in probe_data.get("streams", []):
        if "duration" in stream:
            return float(stream["duration"])
    return 0.0


def build_ffmpeg_cmd(input_path, output_path, settings, selected_audio_indices):
    cmd = ["ffmpeg", "-y", "-i", input_path]

    video_map = []
    audio_map = []
    subtitle_map = []

    for stream in []:
        pass

    cmd += ["-map", "0:v:0"]

    for idx in selected_audio_indices:
        cmd += ["-map", f"0:{idx}"]

    cmd += ["-map", "0:s?"]

    vcodec = settings.get("videocodec", "libx264")
    crf = settings.get("crf", "23")
    preset = settings.get("preset", "veryfast")
    tune = settings.get("tune", "none")
    aspect = settings.get("aspect", "none")
    fps = settings.get("fps", "sameassource")
    acodec = settings.get("audiocodec", "aac")
    bitrate = settings.get("bitrate", "128k")

    cmd += ["-c:v", vcodec, "-crf", crf, "-preset", preset]

    if tune and tune != "none":
        cmd += ["-tune", tune]

    if aspect and aspect != "none":
        cmd += ["-vf", f"scale={aspect}"]

    if fps and fps != "sameassource":
        cmd += ["-r", fps]

    cmd += ["-c:a", acodec, "-b:a", bitrate]
    cmd += ["-c:s", "copy"]
    cmd += ["-progress", "pipe:1", "-nostats"]
    cmd.append(output_path)

    return cmd


def parse_progress(line, duration):
    data = {}
    for part in line.strip().split("\n"):
        if "=" in part:
            k, v = part.split("=", 1)
            data[k.strip()] = v.strip()

    out_time_us = data.get("out_time_us") or data.get("out_time_ms")
    speed = data.get("speed", "0x").replace("x", "")
    fps = data.get("fps", "0")

    current = 0.0
    if out_time_us:
        try:
            current = float(out_time_us) / 1_000_000
        except Exception:
            pass

    percent = (current / duration * 100) if duration > 0 else 0

    try:
        speed_val = float(speed)
    except Exception:
        speed_val = 0.0

    try:
        fps_val = float(fps)
    except Exception:
        fps_val = 0.0

    return {
        "percent": min(percent, 100.0),
        "speed": speed_val,
        "fps": fps_val,
        "current": current,
        "duration": duration,
    }


def format_progress_bar(percent, width=10):
    filled = int(width * percent / 100)
    bar = "▰" * filled + "▱" * (width - filled)
    return f"[{bar}]"


def format_time(seconds):
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h, {m}m, {s}s"
    elif m:
        return f"{m}m, {s}s"
    return f"{s}s"
