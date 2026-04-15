import motor.motor_asyncio
import config

# Initialize MongoDB Client
client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)
db = client["EncoderBotDB3"]
settings_col = db["settings"]
groups_col = db["groups"]
users_col = db["users"] 

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
    """Initializes default settings if database is empty."""
    doc = await settings_col.find_one({"_id": "default"})
    if not doc:
        await settings_col.insert_one(DEFAULT_SETTINGS)

async def get_settings():
    """Fetches global FFmpeg settings."""
    doc = await settings_col.find_one({"_id": "default"})
    return doc if doc else DEFAULT_SETTINGS

async def update_setting(key, value):
    """Updates a specific global setting."""
    await settings_col.update_one({"_id": "default"}, {"$set": {key: value}}, upsert=True)

async def get_groups():
    """Returns list of authorized chat IDs."""
    cursor = groups_col.find({})
    groups = []
    async for doc in cursor:
        groups.append(doc["chat_id"])
    return groups

async def add_group(chat_id):
    await groups_col.update_one({"chat_id": chat_id}, {"$set": {"chat_id": chat_id}}, upsert=True)

async def remove_group(chat_id):
    await groups_col.delete_one({"chat_id": chat_id})

# --- USER THUMBNAIL FUNCTIONS ---

async def set_thumb(user_id, file_id):
    """Saves a user's custom thumbnail file_id."""
    await users_col.update_one({"user_id": user_id}, {"$set": {"thumb": file_id}}, upsert=True)

async def get_thumb(user_id):
    """Retrieves a user's custom thumbnail file_id."""
    doc = await users_col.find_one({"user_id": user_id})
    return doc.get("thumb") if doc else None

async def del_thumb(user_id):
    """Deletes a user's custom thumbnail."""
    await users_col.update_one({"user_id": user_id}, {"$unset": {"thumb": ""}})
