# encoder_bot

ffmpeg-based Telegram encoder bot built with aiogram 3.

## Setup

1. Edit `config.py` — set your `BOT_TOKEN` and `OWNER_ID`.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Make sure `ffmpeg` and `ffprobe` are installed and available in PATH.

## Running

```bash
python3 bot.py
```

Or with PM2:

```bash
pm2 start ecosystem.config.js
```

## Commands

| Command | Who | Description |
|---|---|---|
| `/approve` | Owner (in group) | Authorize the current group |
| `/revoke` | Owner (in group) | Remove group authorization |
| `/settings` | Anyone | View current encoder settings |
| `/crf <value>` | Owner | Set CRF (e.g. 23) |
| `/preset <value>` | Owner | Set preset (e.g. veryfast, medium) |
| `/tune <value>` | Owner | Set tune (e.g. animation, film, none) |
| `/aspect <value>` | Owner | Set output resolution (e.g. 1920x1080, none) |
| `/videocodec <value>` | Owner | Set video codec (e.g. libx264, libx265) |
| `/fps <value>` | Owner | Set fps (e.g. 24, sameassource) |
| `/audiocodec <value>` | Owner | Set audio codec (e.g. aac, libopus) |
| `/bitrate <value>` | Owner | Set audio bitrate (e.g. 128k, 192k) |

## Usage

Send a video or document file to an approved group. The bot will:

1. Download the file with a progress bar.
2. Ask which audio tracks to keep (multi-select).
3. Ask which subtitle tracks to keep (multi-select).
4. Show a confirmation with your selections.
5. Encode with a live progress bar showing speed, fps, elapsed, time left, and percentage.
6. Upload the output file with a progress bar.

Output file keeps the same extension as the source.

## Project Structure

```
encoder_bot/
├── bot.py
├── config.py
├── requirements.txt
├── ecosystem.config.js
├── data/               # auto-created, stores settings.json and groups.json
├── temp/               # auto-created, stores in-progress files
├── handlers/
│   ├── admin.py        # /approve, /revoke, all setting commands
│   ├── settings.py     # /settings
│   └── encode.py       # file handling, stream selection, encode flow
└── utils/
    ├── db.py           # JSON-based persistence
    ├── ffmpeg.py       # command builder and async runner
    ├── ffprobe.py      # stream info extraction
    └── progress.py     # progress bar and text formatters
```
