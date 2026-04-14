import asyncio
import os
import re
import json
import subprocess
import utils.state

async def probe(file_path):
    """Fetches metadata using ffprobe."""
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
    """Generates a thumbnail at the 5-second mark."""
    cmd = [
        'ffmpeg', '-ss', '00:00:05', '-i', video_file,
        '-vframes', '1', '-q:v', '2', output_path, '-y'
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    except:
        return None

async def run_ffmpeg(input_file, output_file, selected_audio, settings, msg, task_id, duration):
    """The main encoding engine."""
    
    # 1. Base Command
    cmd = ['ffmpeg', '-i', input_file]

    # 2. Video Settings
    v_codec = settings.get("videocodec", "libx264")
    cmd.extend(['-c:v', v_codec])

    # Preset & Tune
    preset = settings.get("preset", "none")
    if preset != "none":
        cmd.extend(['-preset', preset])
        
    tune = settings.get("tune", "none")
    if tune != "none":
        cmd.extend(['-tune', tune])

    # CRF (Quality)
    crf = settings.get("crf", "none")
    if crf != "none":
        cmd.extend(['-crf', str(crf)])

    # Aspect Ratio / Scaling
    aspect = settings.get("aspect", "none")
    if aspect != "none":
        # Example: 1280x720
        cmd.extend(['-vf', f'scale={aspect.replace("x", ":")}'])

    # FPS
    fps = settings.get("fps", "sameassource")
    if fps != "sameassource":
        cmd.extend(['-r', str(fps)])

    # 3. Audio Mapping Logic
    # We map the video stream (0:v:0)
    cmd.extend(['-map', '0:v:0'])
    
    # Map selected audio streams
    if selected_audio:
        for idx in selected_audio:
            cmd.extend(['-map', f'0:{idx}'])
    else:
        # Default to all audio if none selected
        cmd.extend(['-map', '0:a?'])

    # Audio Codec
    a_codec = settings.get("audiocodec", "aac")
    cmd.extend(['-c:a', a_codec])

    # 4. Output Configuration
    cmd.extend(['-y', output_file])

    # Start Process
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    utils.state.active_process = process

    # 5. Progress Tracking
    # FFmpeg outputs progress to stderr
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        
        data = line.decode('utf-8')
        if "time=" in data:
            # Extract time=00:00:00.00
            match = re.search(r'time=(\d+:\d+:\d+\.\d+)', data)
            if match:
                elapsed_time = match.group(1)
                # Convert HH:MM:SS to seconds
                h, m, s = map(float, elapsed_time.split(':'))
                done_seconds = h * 3600 + m * 60 + s
                
                # Update progress roughly every 5 seconds to avoid flooding Telegram
                # This logic is usually handled inside your update_progress utility
                pass 

    await process.wait()
    utils.state.active_process = None
    
    return process.returncode == 0
