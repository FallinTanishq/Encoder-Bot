import asyncio
import os
import time
from pyrogram import Client, idle, enums
import config
# Imported set_thumb to update expired references
from utils.db import get_settings, init_db, get_thumb, set_thumb
import utils.state
from utils.ffmpeg_utils import run_ffmpeg, take_screenshot, probe, rename_encoded_file
from utils.progress import update_progress

app = Client(
    "encoder",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    plugins=dict(root="handlers"),
    parse_mode=enums.ParseMode.HTML
)

def cleanup_downloads():
    """Cleans up the downloads folder on startup."""
    folder = 'downloads'
    os.makedirs(folder, exist_ok=True)
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception:
            pass

async def worker():
    """Background worker that processes the video queue."""
    while True:
        task_id = await utils.state.queue.get()
        utils.state.current_task_id = task_id
        data = utils.state.active_tasks.get(task_id)
        
        ext = ""
        final_thumb = None

        if not data or utils.state.cancel_flags.get(task_id):
            utils.state.active_tasks.pop(task_id, None)
            utils.state.queue.task_done()
            continue

        try:
            msg = data["msg"]
            user_id = data["user_id"]
            file_path = data["file_path"]
            ext = os.path.splitext(file_path)[1]
            out_path = f"{file_path}_out{ext}"
            
            await msg.edit_text("<b>ᴘʀᴇᴘᴀʀɪɴɢ ᴇɴᴄᴏᴅᴇ...</b>")
            settings = await get_settings() 
            
            # Start FFmpeg Process
            success = await run_ffmpeg(
                file_path, out_path, data["selected"], 
                settings, msg, task_id, data["duration"]
            )
            
            if utils.state.cancel_flags.get(task_id):
                raise Exception("Cancelled")

            if success and os.path.exists(out_path):
                # --- AUTO-RENAME LOGIC ---
                try:
                    probe_data = await probe(out_path)
                    w, h = 0, 0
                    if "streams" in probe_data:
                        for s in probe_data["streams"]:
                            if s.get("codec_type") == "video":
                                w = int(s.get("width", 0))
                                h = int(s.get("height", 0))
                                break
                    
                    new_file_name = rename_encoded_file(os.path.basename(file_path), w, h)
                    new_out_path = os.path.join(os.path.dirname(out_path), new_file_name)
                    
                    if os.path.exists(new_out_path) and new_out_path != out_path:
                        os.remove(new_out_path)
                        
                    os.rename(out_path, new_out_path)
                    out_path = new_out_path # Safely reassign for the upload block
                except Exception as e:
                    print(f"Renaming failed: {e}")
                # -------------------------

                # --- THUMBNAIL LOGIC ---
                thumb_doc = await get_thumb(user_id)
                final_thumb = None
                
                if thumb_doc and thumb_doc.get("thumb"):
                    custom_thumb_id = thumb_doc.get("thumb")
                    thumb_dl_path = f"downloads/custom_{task_id}.jpg"
                    
                    try:
                        # Attempt to download the saved thumbnail
                        final_thumb = await app.download_media(custom_thumb_id, file_name=thumb_dl_path)
                    except Exception as e:
                        print(f"Thumb error: {e}")
                        # If file reference is expired, try to fetch a fresh one
                        if "FILE_REFERENCE_EXPIRED" in str(e):
                            chat_id = thumb_doc.get("thumb_chat_id")
                            msg_id = thumb_doc.get("thumb_msg_id")
                            
                            if chat_id and msg_id:
                                try:
                                    fresh_msg = await app.get_messages(chat_id, msg_id)
                                    if fresh_msg and fresh_msg.photo:
                                        fresh_file_id = fresh_msg.photo.file_id
                                        # Update DB with new file reference
                                        await set_thumb(user_id, fresh_file_id, chat_id, msg_id)
                                        # Try download again
                                        final_thumb = await app.download_media(fresh_file_id, file_name=thumb_dl_path)
                                except Exception as inner_e:
                                    print(f"Failed to refresh expired thumb: {inner_e}")
                
                # Safe Fallback if download failed or no custom thumb
                if not final_thumb:
                    gen_path = f"downloads/thumb_{task_id}.jpg"
                    final_thumb = take_screenshot(out_path, gen_path)
                # -------------------------
                
                # Upload the final file
                start_time = time.time()
                await app.send_document(
                    chat_id=data["message"].chat.id,
                    document=out_path,
                    thumb=final_thumb,
                    caption="<b>✅ ᴇɴᴄᴏᴅᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ</b>",
                    reply_to_message_id=data["message"].id,
                    progress=update_progress,
                    progress_args=(msg, start_time, "ᴜᴘʟᴏᴀᴅɪɴɢ", task_id)
                )
                await msg.delete()
            else:
                await msg.edit_text("<b>ᴇɴᴄᴏᴅɪɴɢ ғᴀɪʟᴇᴅ.</b>")
                
        except Exception as e:
            if str(e) != "Cancelled":
                try:
                    await data["msg"].edit_text(f"<b>ᴘʀᴏᴄᴇss sᴛᴏᴘᴘᴇᴅ:</b> <code>{str(e)}</code>")
                except:
                    pass
        finally:
            # Cleanup all temporary files for this task
            paths_to_delete = [final_thumb]
            
            # Cleanly handles dynamically assigned output paths
            if 'out_path' in locals() and out_path:
                paths_to_delete.append(out_path)
                
            if data and "file_path" in data:
                paths_to_delete.append(data["file_path"])
                paths_to_delete.append(f"{data['file_path']}_out{ext}")
                
            for p in paths_to_delete:
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except:
                        pass
            
            utils.state.current_task_id = None
            utils.state.active_tasks.pop(task_id, None)
            utils.state.queue.task_done()

async def main():
    """Main entry point."""
    cleanup_downloads()
    await init_db() # Connect to MongoDB
    await app.start()
    asyncio.create_task(worker())
    print("Bot is running...")
    await idle()
    await app.stop()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
