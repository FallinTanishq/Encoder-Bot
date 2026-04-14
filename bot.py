import asyncio
import os
import time
from pyrogram import Client, idle
from pyrogram import enums
import config
from utils.db import get_settings
import utils.state
from utils.ffmpeg_utils import run_ffmpeg
from utils.progress import update_progress

app = Client("encoder", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN, plugins=dict(root="handlers"), parse_mode=enums.ParseMode.HTML)

async def worker():
    while True:
        task_id = await utils.state.queue.get()
        if utils.state.cancel_flags.get(task_id):
            utils.state.queue.task_done()
            continue
            
        utils.state.current_task_id = task_id
        data = utils.state.active_tasks.get(task_id)
        
        if not data:
            utils.state.queue.task_done()
            continue
            
        try:
            msg = data["msg"]
            file_path = data["file_path"]
            ext = os.path.splitext(file_path)[1]
            out_path = f"{file_path}_out{ext}"
            settings = get_settings()
            
            success = await run_ffmpeg(file_path, out_path, data["selected"], settings, msg, task_id, data["duration"])
            
            if utils.state.cancel_flags.get(task_id):
                raise Exception("Cancelled")
                
            if success and os.path.exists(out_path):
                start_time = time.time()
                await app.send_document(
                    chat_id=data["message"].chat.id,
                    document=out_path,
                    reply_to_message_id=data["message"].id,
                    progress=update_progress,
                    progress_args=(msg, start_time, "ᴜᴘʟᴏᴀᴅɪɴɢ", task_id)
                )
                await msg.edit_text("<b>ᴄᴏᴍᴘʟᴇᴛᴇᴅ.</b>")
            else:
                await msg.edit_text("<b>ᴇɴᴄᴏᴅɪɴɢ ғᴀɪʟᴇᴅ.</b>")
                
        except Exception as e:
            if str(e) != "Cancelled":
                try:
                    await data["msg"].edit_text("<b>ᴇʀʀᴏʀ.</b>")
                except Exception:
                    pass
        finally:
            for p in [data.get("file_path"), f"{data.get('file_path')}_out{ext}"]:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            utils.state.queue.task_done()

async def main():
    await app.start()
    asyncio.create_task(worker())
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
