# encoder-bot

A Telegram bot that encodes video and audio files using ffmpeg. Built with aiogram 3 and Pyrogram.

---

## Features

- Reply to any video/audio file with `/compress` to encode it
- Interactive audio track selection before encoding
- All subtitle tracks are kept automatically
- One file encodes at a time with a queue system
- Live progress bars for download, encode, and upload stages
- Pyrogram handles file transfers, bypassing the 20MB bot API limit (supports up to 4GB)
- Configurable ffmpeg settings per owner commands
- Group allowlist — bot only responds in approved groups

---

## Environment Variables

Set these in your Heroku app settings under **Config Vars**:

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Your bot token from @BotFather |
| `OWNER_ID` | Your Telegram user ID (integer) |
| `API_ID` | From my.telegram.org |
| `API_HASH` | From my.telegram.org |

---

## Deploying to Heroku

### 1. Add buildpacks

ffmpeg must be installed before the Python buildpack runs:

```
heroku buildpacks:add --index 1 https://github.com/jonathanong/heroku-buildpack-ffmpeg-latest.git
heroku buildpacks:add --index 2 heroku/python
```

### 2. Set config vars

```
heroku config:set BOT_TOKEN=your_token
heroku config:set OWNER_ID=123456789
heroku config:set API_ID=12345
heroku config:set API_HASH=your_api_hash
```

### 3. Deploy

Push to your connected GitHub repo or deploy directly:

```
git push heroku main
```

### 4. Scale the worker dyno

The bot runs as a worker, not a web process:

```
heroku ps:scale worker=1 web=0
```

---

## Commands

### Anyone (in approved groups)

| Command | Description |
|---------|-------------|
| `/start` | Basic info message |
| `/ping` | Response time in ms |
| `/settings` | Show current encoder settings |
| `/compress` | Reply to a file to encode it |

### Owner only

| Command | Description |
|---------|-------------|
| `/approve` | Approve current group |
| `/revoke` | Revoke current group |
| `/crf <0-51>` | Set CRF value |
| `/preset <value>` | Set encoding preset |
| `/tune <value>` | Set tune flag |
| `/aspect <WxH or none>` | Set output resolution |
| `/videocodec <codec>` | Set video codec |
| `/fps <value or sameassource>` | Set frame rate |
| `/audiocodec <codec>` | Set audio codec |
| `/bitrate <value>` | Set audio bitrate |
| `/restart` | Restart the bot process |

Valid presets: `ultrafast superfast veryfast faster fast medium slow slower veryslow`

Valid tunes: `film animation grain stillimage fastdecode zerolatency none`

---

## Project Structure

```
encoder-bot/
├── bot.py                  main entry point
├── config.py               reads env vars
├── Procfile                worker: python3 bot.py
├── runtime.txt             python-3.12.3
├── requirements.txt
├── ecosystem.config.js     PM2 config (for non-Heroku deployments)
├── handlers/
│   ├── common.py           /start /ping /settings /restart
│   ├── admin.py            group management + ffmpeg settings
│   └── compress.py         /compress flow, audio UI, queue entry
└── utils/
    ├── data.py             JSON persistence for settings and groups
    ├── ffmpeg.py           probe tracks, build command, parse progress
    ├── progress.py         progress bar text formatters
    ├── pyrogram_client.py  Pyrogram running on separate thread and loop
    └── queue.py            download → encode → upload pipeline
```

---

## Running Locally / on VPS with PM2

```
pip install -r requirements.txt
cp .env.example .env  # fill in your values
pm2 start ecosystem.config.js
pm2 save
```

---

## Notes

- The `data/` folder is created automatically and stores settings and approved groups as JSON files. On Heroku, this folder is ephemeral — settings reset on dyno restart. For persistence on Heroku, replace JSON storage with a database add-on (e.g. Heroku Postgres).
- The `downloads/` folder is used as a scratch space during encoding and is cleaned up after each job.
- Pyrogram runs on a separate thread with its own event loop to avoid blocking aiogram's polling loop. Progress updates are sent back to the main loop using `asyncio.run_coroutine_threadsafe`.
