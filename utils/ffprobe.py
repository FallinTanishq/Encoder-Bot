import asyncio
import json


async def probe(filepath):
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", filepath,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return json.loads(stdout)


async def get_duration(filepath):
    info = await probe(filepath)
    return float(info.get("format", {}).get("duration", 0))


def get_streams_by_type(info, codec_type):
    return [s for s in info.get("streams", []) if s.get("codec_type") == codec_type]


def stream_label(stream):
    idx = stream.get("index", "?")
    codec = stream.get("codec_name", "unknown")
    lang = stream.get("tags", {}).get("language", "und")
    title = stream.get("tags", {}).get("title", "")
    label = f"[{idx}] {codec} | {lang}"
    if title:
        label += f" | {title}"
    return label


def get_extension(filepath):
    return "." + filepath.rsplit(".", 1)[-1] if "." in filepath else ".mkv"
