import asyncio
import os
import json
import subprocess
import utils.state
from utils.progress import encode_progress

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
    
    # 1. Input - Added -progress pipe:1 to output live stats
    cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-progress', 'pipe:1', '-i', input_file]

    # 2. Global Video Settings
    v_codec = settings.get("videocodec", "libx264")
    cmd.extend(['-c:v', v_codec])

    # CRF (Quality)
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
        scale_val = aspect.replace("x", ":")
        cmd.extend(['-vf', f'scale={scale_val}'])

    # FPS
    fps_setting = settings.get("fps", "sameassource")
    if fps_setting != "sameassource":
        cmd.extend(['-r', str(fps_setting)])

    # 3. Stream Mapping
    cmd.extend(['-map', '0:v:0']) # Map Video
    
    # Map selected audio tracks
    if selected_audio:
        for idx in selected_audio:
            cmd.extend(['-map', f'0:{idx}'])
    else:
        cmd.extend(['-map', '0:a?'])

    # --- THE SUBTITLE FIX ---
    # Map all subtitle streams and copy them untouched
    cmd.extend(['-map', '0:s?'])
    cmd.extend(['-c:s', 'copy'])

    # 4. Audio Settings
    a_codec = settings.get("audiocodec", "aac")
    cmd.extend(['-c:a', a_codec])

    # Audio Bitrate
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
    
    # Progress Trackers
    current_fps = "0"
    current_speed = "0x"
    out_time_us = 0

    try:
        # Read standard output to parse live FFmpeg progress line-by-line
        while True:
            line = await process.stdout.readline()
            if not line:
                break
                
            line = line.decode('utf-8').strip()
            
            # Check for cancellation
            if utils.state.cancel_flags.get(task_id):
                process.kill()
                raise Exception("Cancelled")
            
            # Parse FFmpeg key=value pairs
            if line.startswith("fps="):
                current_fps = line.split("=")[1].strip()
            elif line.startswith("speed="):
                current_speed = line.split("=")[1].strip()
            elif line.startswith("out_time_us="):
                try:
                    out_time_us = int(line.split("=")[1])
                except ValueError:
                    pass
            elif line.startswith("progress="):
                # When block ends, push the progress update to the user
                if duration > 0 and out_time_us > 0:
                    encoded_seconds = out_time_us / 1_000_000
                    percent = min(100.0, round((encoded_seconds / duration) * 100, 1))
                    
                    try:
                        sp_val = float(current_speed.replace("x", "").strip())
                        eta_seconds = (duration - encoded_seconds) / sp_val if sp_val > 0 else 0
                    except Exception:
                        eta_seconds = 0
                        
                    await encode_progress(msg, current_speed, current_fps, eta_seconds, percent, task_id)

        await process.wait()
    except Exception as e:
        print(f"FFmpeg Process Error: {e}")
        if str(e) != "Cancelled" and process.returncode is None:
            try:
                process.kill()
            except Exception:
                pass
        raise e
    finally:
        utils.state.active_process = None
    
    return process.returncode == 0
