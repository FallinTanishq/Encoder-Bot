import asyncio
import json
import re
import time
import utils.state
from utils.progress import format_time, encode_progress

async def probe(file_path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, _ = await proc.communicate()
    return json.loads(stdout)

async def run_ffmpeg(input_file, output_file, audio_tracks, settings, msg, task_id, total_duration):
    cmd = ["ffmpeg", "-y", "-i", input_file]
    cmd.extend(["-map", "0:v:0"])
    for a in audio_tracks:
        cmd.extend(["-map", f"0:{a}"])
    cmd.extend(["-map", "0:s?"])
    cmd.extend(["-c:v", settings["videocodec"]])
    if settings["crf"] != "none":
        cmd.extend(["-crf", settings["crf"]])
    if settings["preset"] != "none":
        cmd.extend(["-preset", settings["preset"]])
    if settings["tune"] != "none":
        cmd.extend(["-tune", settings["tune"]])
    if settings["aspect"] != "none":
        cmd.extend(["-s", settings["aspect"]])
    if settings["fps"] != "sameassource":
        cmd.extend(["-r", settings["fps"]])
    cmd.extend(["-c:a", settings["audiocodec"]])
    if settings["bitrate"] != "none":
        cmd.extend(["-b:a", settings["bitrate"]])
    cmd.extend(["-c:s", "copy"])
    cmd.append(output_file)

    utils.state.active_process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
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

        line = await utils.state.active_process.stderr.readline()
        if not line:
            break
        line = line.decode("utf-8").strip()

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
