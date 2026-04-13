import json
import os

DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
PRESETS_FILE = os.path.join(DATA_DIR, "presets.json")

DEFAULT_SETTINGS = {
    "crf": "23",
    "preset": "veryfast",
    "tune": "none",
    "aspect": "none",
    "videocodec": "libx264",
    "fps": "sameassource",
    "audiocodec": "aac",
    "bitrate": "128k",
}

os.makedirs(DATA_DIR, exist_ok=True)


def _load(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def _save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_settings():
    data = _load(SETTINGS_FILE, {})
    merged = {**DEFAULT_SETTINGS, **data}
    return merged


def save_settings(settings):
    _save(SETTINGS_FILE, settings)


def get_groups():
    return _load(GROUPS_FILE, [])


def save_groups(groups):
    _save(GROUPS_FILE, groups)


def get_presets():
    return _load(PRESETS_FILE, {})


def save_presets(presets):
    _save(PRESETS_FILE, presets)
