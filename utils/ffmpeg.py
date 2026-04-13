import json
import subprocess
import re


def probe_tracks(path):
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    streams = data.get("streams", [])

    audio = []
    subtitles = []
    for s in streams:
        codec_type = s.get("codec_type")
        if codec_type == "audio":
            audio.append({
                "index": s.get("index"),
                "codec": s.get("codec_name", "unknown"),
                "language": s.get("tags", {}).get("language", "und"),
                "title": s.get("tags", {}).get("title", ""),
                "channels": s.get("channels", 0),
            })
        elif codec_type == "subtitle":
            subtitles.append({"index": s.get("index")})

    return audio, subtitles


def get_duration(path):
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    try:
        return float(data["format"]["duration"])
    except Exception:
        return 0.0


def build_ffmpeg_cmd(input_path, output_path, settings, selected_audio_indices, subtitle_indices):
    cmd = ["ffmpeg", "-y", "-i", input_path]

    cmd += ["-map", "0:v"]

    for idx in selected_audio_indices:
        cmd += ["-map", f"0:{idx}"]

    for idx in subtitle_indices:
        cmd += ["-map", f"0:{idx}"]

    cmd += ["-c:v", settings["videocodec"]]
    cmd += ["-crf", str(settings["crf"])]
    cmd += ["-preset", settings["preset"]]

    if settings["tune"] != "none":
        cmd += ["-tune", settings["tune"]]

    if settings["aspect"] != "none":
        cmd += ["-vf", f"scale={settings['aspect'].replace('x', ':')}"]

    if settings["fps"] != "sameassource":
        cmd += ["-r", str(settings["fps"])]

    cmd += ["-c:a", settings["audiocodec"]]
    cmd += ["-b:a", settings["bitrate"]]

    cmd += ["-c:s", "copy"]

    cmd += ["-progress", "pipe:1", "-nostats"]
    cmd += [output_path]
    return cmd


def parse_progress_line(line):
    data = {}
    for part in line.strip().split("\n"):
        if "=" in part:
            k, v = part.split("=", 1)
            data[k.strip()] = v.strip()
    return data
