import json
import os

DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")

DEFAULT_SETTINGS = {
    "crf": 23,
    "preset": "medium",
    "tune": "none",
    "aspect": "none",
    "videocodec": "libx264",
    "fps": "sameassource",
    "audiocodec": "aac",
    "bitrate": "128k",
}

os.makedirs(DATA_DIR, exist_ok=True)


def _read(path, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        return json.load(f)


def _write(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_settings():
    data = _read(SETTINGS_FILE, {})
    merged = {**DEFAULT_SETTINGS, **data}
    return merged


def update_setting(key, value):
    data = _read(SETTINGS_FILE, {})
    data[key] = value
    _write(SETTINGS_FILE, data)


def get_approved_groups():
    return set(_read(GROUPS_FILE, []))


def approve_group(chat_id):
    groups = get_approved_groups()
    groups.add(chat_id)
    _write(GROUPS_FILE, list(groups))


def revoke_group(chat_id):
    groups = get_approved_groups()
    groups.discard(chat_id)
    _write(GROUPS_FILE, list(groups))
