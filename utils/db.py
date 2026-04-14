import motor.motor_asyncio
import config

# Initialize MongoDB Client
client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)
db = client["EncoderBotDB"]
settings_col = db["settings"]
groups_col = db["groups"]

DEFAULT_SETTINGS = {
    "_id": "default",
    "videocodec": "libx264",
    "crf": "none",
    "preset": "none",
    "tune": "none",
    "aspect": "none",
    "fps": "sameassource",
    "audiocodec": "aac",
    "bitrate": "none"
}

async def init_db():
    """Run this on startup to ensure default settings exist."""
    doc = await settings_col.find_one({"_id": "default"})
    if not doc:
        await settings_col.insert_one(DEFAULT_SETTINGS)

async def get_settings():
    """Fetches the current FFmpeg settings from MongoDB."""
    doc = await settings_col.find_one({"_id": "default"})
    return doc if doc else DEFAULT_SETTINGS

async def update_setting(key, value):
    """Updates a specific setting in MongoDB."""
    await settings_col.update_one(
        {"_id": "default"},
        {"$set": {key: value}},
        upsert=True
    )

async def get_groups():
    """Returns a list of authorized group IDs."""
    cursor = groups_col.find({})
    groups = []
    async for doc in cursor:
        groups.append(doc["chat_id"])
    return groups

async def add_group(chat_id):
    """Authorizes a new group."""
    await groups_col.update_one(
        {"chat_id": chat_id}, 
        {"$set": {"chat_id": chat_id}}, 
        upsert=True
    )

async def remove_group(chat_id):
    """Removes authorization from a group."""
    await groups_col.delete_one({"chat_id": chat_id})
