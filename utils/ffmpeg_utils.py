import asyncio
import json
import os
import re
import subprocess
import time
import utils.state
from utils.progress import format_time, encode_progress

async def probe(file_path):
    """Probes a file fast. Works on partial files/headers too."""
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await proc.communicate()
    return json.loads(stdout)

def take_screenshot(file_path, output_path):
    """Takes a screenshot at the 10-second mark to use as a Telegram thumbnail."""
    try:
        cmd = [
            "ffmpeg", "-y", "-ss", "00:00:10", "-i", file_path, 
            "-vframes", "1", "-q:v", "2", output_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None

async def run_ffmpeg(input_file, output_file, audio_tracks, settings, msg, task_id, total_duration):
    """Executes FFmpeg with a raised buffer limit to prevent 1080p chunk exceed errors."""
    cmd = ["ffmpeg", "-y", "-i", input_file]
    
    # Map video and selected audio
    cmd.extend(["-map", "0:v:0"])
    for a in audio_tracks:
        cmd.extend(["-map", f"0:{a}"])
    cmd.extend(["-map", "0:s?"]) # Copy subtitles if any
    
    # Video settings
    cmd.extend(["-c:v", settings.get("videocodec", "libx264")])
    if settings.get("crf", "none") != "none":
        cmd.extend(["-crf", settings["crf"]])
    if settings.get("preset", "none") != "none":
        cmd.extend(["-preset", settings["preset"]])
    if settings.get("tune", "none") != "none":
        cmd.extend(["-tune", settings["tune"]])
    if settings.get("aspect", "none") != "none":
        cmd.extend(["-s", settings["aspect"]])
    if settings.get("fps", "sameassource") != "sameassource":
        cmd.extend(["-r", settings["fps"]])
        
    # Audio settings
    cmd.extend(["-c:a", settings.get("audiocodec", "aac")])
    if settings.get("bitrate", "none") != "none":
        cmd.extend(["-b:a", settings["bitrate"]])
    
    # Subtitles and output
    cmd.extend(["-c:s", "copy"])
    cmd.append(output_file)

    # limit=1024*128 prevents the Heroku buffer crash on heavy encodes
    utils.state.active_process = await asyncio.create_subprocess_exec(
        *cmd, 
        stdout=asyncio.subprocess.PIPE, 
        stderr=asyncio.subprocess.PIPE,
        limit=1024 * 128
    )
    
    start_time = time.time()
    time_regex = re.compile(r"time=\s*(\d+):(\d+):([\d\.]+)")
    speed_regex = re.compile(r"speed=\s*([\d\.]+)x")
    fps_regex = re.compile(r"fps=\s*([\d\.]+)")

    while True:
        if utils.state.cancel_flags.get(task_id):
            utils.state.active_process.terminate()
            await utils.state.active_process.wait()
            utils.state.active_process = None
            return False

        try:
            # Using \r because FFmpeg overwrites the line rather than printing new ones (\n)
            line_bytes = await utils.state.active_process.stderr.readuntil(b'\r')
            line = line_bytes.decode("utf-8").strip()
        except asyncio.IncompleteReadError as e:
            line = e.partial.decode("utf-8").strip()
            if not line: break
        except Exception:
            break

        time_match = time_regex.search(line)
        speed_match = speed_regex.search(line)
        fps_match = fps_regex.search(line)

        if time_match and speed_match and fps_match and total_duration > 0:
            h, m, s = map(float, time_match.groups())
            current_time = h * 3600 + m * 60 + s
            speed = speed_match.group(1) + "x"
            fps = fps_match.group(1)
            percent = min(round((current_time / total_duration) * 100, 1), 100.0)
            elapsed = time.time() - start_time
            sp = float(speed_match.group(1))
            left = (total_duration - current_time) / sp if sp > 0 else 0
            
            await encode_progress(msg, speed, fps, format_time(elapsed), format_time(left), percent, task_id)

    await utils.state.active_process.wait()
    success = utils.state.active_process.returncode == 0
    utils.state.active_process = None
    return success
