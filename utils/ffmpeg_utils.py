import asyncio
import os
import re
import json
import subprocess
import utils.state

async def probe(file_path):
    """
    Uses ffprobe to get video metadata (duration, streams, etc.)
    Returns a dictionary of the JSON output.
    """
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_format', '-show_streams', file_path
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return json.loads(stdout)

def take_screenshot(video_file, output_path):
    """
    Generates a single frame screenshot for use as a thumbnail.
    """
    cmd = [
        'ffmpeg', '-ss', '00:00:05', '-i', video_file,
        '-vframes', '1', '-q:v', '2', output_path, '-y'
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    except Exception:
        return None

async def run_ffmpeg(input_file, output_file, selected_audio, settings, msg, task_id, duration):
    """
    The core encoding engine.
    Dynamically builds the command based on database settings.
    """
    
    # 1. Input
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', input_file]

    # 2. Global Video Settings
    v_codec = settings.get("videocodec", "libx264")
    cmd.extend(['-c:v', v_codec])

    # CRF (Quality) - Only applied if not using specific video bitrate logic
    crf = settings.get("crf", "none")
    if crf != "none":
        cmd.extend(['-crf', str(crf)])

    # Preset (Speed/Efficiency)
    preset = settings.get("preset", "none")
    if preset != "none":
        cmd.extend(['-preset', preset])
        
    # Tune (Content Optimization)
    tune = settings.get("tune", "none")
    if tune != "none":
        cmd.extend(['-tune', tune])

    # Aspect Ratio / Scaling (Filters)
    aspect = settings.get("aspect", "none")
    if aspect != "none":
        # Formats '1280x720' into 'scale=1280:720'
        scale_val = aspect.replace("x", ":")
        cmd.extend(['-vf', f'scale={scale_val}'])

    # FPS
    fps = settings.get("fps", "sameassource")
    if fps != "sameassource":
        cmd.extend(['-r', str(fps)])

    # 3. Stream Mapping
    # Always map the first video stream
    cmd.extend(['-map', '0:v:0'])
    
    # Map selected audio streams or all if none specified
    if selected_audio:
        for idx in selected_audio:
            cmd.extend(['-map', f'0:{idx}'])
    else:
        cmd.extend(['-map', '0:a?'])

    # 4. Audio Settings
    a_codec = settings.get("audiocodec", "aac")
    cmd.extend(['-c:a', a_codec])

    # Audio Bitrate (The /bitrate command logic)
    a_bitrate = settings.get("bitrate", "none")
    if a_bitrate != "none":
        cmd.extend(['-b:a', str(a_bitrate)])

    # 5. Output
    cmd.extend(['-y', output_file])

    # Execute
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    utils.state.active_process = process

    # Monitor Progress (Stderr is where FFmpeg sends log output)
    try:
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            
            # Optional: You can parse 'time=' here for live progress bars
            # but usually, we rely on the helper in utils/progress.py
            pass

        await process.wait()
    except Exception as e:
        print(f"FFmpeg Process Error: {e}")
    finally:
        utils.state.active_process = None
    
    return process.returncode == 0
