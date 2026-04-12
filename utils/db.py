import json
import os

SETTINGS_FILE = "data/settings.json"
GROUPS_FILE = "data/groups.json"

DEFAULT_SETTINGS = {
    "crf": "23",
    "preset": "medium",
    "tune": None,
    "aspect": None,
    "videocodec": "libx264",
    "fps": "sameassource",
    "audiocodec": "aac",
    "bitrate": "128k",
}


def _load(path, default):
    if not os.path.exists(path):
        return json.loads(json.dumps(default))
    with open(path) as f:
        return json.load(f)


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_settings():
    data = _load(SETTINGS_FILE, DEFAULT_SETTINGS)
    for key, val in DEFAULT_SETTINGS.items():
        data.setdefault(key, val)
    return data


def update_setting(key, value):
    data = get_settings()
    data[key] = value
    _save(SETTINGS_FILE, data)


def get_approved_groups():
    data = _load(GROUPS_FILE, {"groups": []})
    return data.get("groups", [])


def approve_group(chat_id):
    data = _load(GROUPS_FILE, {"groups": []})
    if chat_id not in data["groups"]:
        data["groups"].append(chat_id)
    _save(GROUPS_FILE, data)


def remove_group(chat_id):
    data = _load(GROUPS_FILE, {"groups": []})
    data["groups"] = [g for g in data["groups"] if g != chat_id]
    _save(GROUPS_FILE, data)


def is_approved(chat_id):
    return chat_id in get_approved_groups()
