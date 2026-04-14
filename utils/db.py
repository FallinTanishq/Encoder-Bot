import json
import os

os.makedirs("data", exist_ok=True)

def _read(filepath, default):
    if not os.path.exists(filepath):
        return default
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def _write(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def get_settings():
    return _read("data/settings.json", {
        "crf": "27",
        "preset": "veryfast",
        "tune": "none",
        "aspect": "none",
        "videocodec": "libx264",
        "fps": "sameassource",
        "audiocodec": "libopus",
        "bitrate": "64k"
    })

def save_settings(data):
    _write("data/settings.json", data)

def get_groups():
    return _read("data/groups.json", [])

def save_groups(data):
    _write("data/groups.json", data)

def get_presets():
    return _read("data/presets.json", {})

def save_presets(data):
    _write("data/presets.json", data)
