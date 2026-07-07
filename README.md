# Video Thumbnail Generator Telegram Bot

A complete Telegram Bot + Mini App Dashboard that processes videos from Google Drive — downloads them via rclone, generates 3 evenly-spaced thumbnails with ffmpeg, and uploads everything back to Telegram (bypassing the 50MB limit via a Local Bot API Server).

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Compose Stack                   │
│                                                          │
│  ┌──────────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  Telegram Bot API │  │  Python Bot  │  │  Next.js  │  │
│  │  (Local, :8081)   │◄─┤  + FastAPI   ├─►│ Dashboard │  │
│  └──────────────────┘  │  WS (:8765)  │  │  (:3000)  │  │
│                         └──────┬───────┘  └───────────┘  │
│                                │                          │
│                    ┌───────────┴───────────┐              │
│                    │    rclone  │  ffmpeg   │              │
│                    └───────────────────────┘              │
└─────────────────────────────────────────────────────────┘
                             │
                     ┌───────┴───────┐
                     │ Google Drive  │
                     └───────────────┘
```

## Features

- **Google Drive Integration** — select rclone remote and drive folder path
- **Sequential Processing** — strict one-at-a-time pipeline prevents memory spikes
- **3 Thumbnails Per Video** — evenly spaced at 25%, 50%, 75% of duration
- **Large File Support** — uploads via Local Bot API Server (no 50MB limit)
- **Real-time Dashboard** — Telegram Mini App with WebSocket-powered live updates
- **RAM Monitoring** — auto-pauses when memory is low, emergency cleanup on critical
- **Robust Paths** — all file operations use `pathlib.Path` with absolute resolution

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Telegram API credentials (from [my.telegram.org](https://my.telegram.org/apps))
- rclone configured with Google Drive

### 1. Clone & Configure

```bash
git clone <your-repo-url>
cd VideoThumbnailGenTGBot

# Copy and edit the environment file
cp .env.example .env
nano .env
```

### 2. Configure rclone

If rclone is not yet configured:

```bash
rclone config
# Follow the interactive setup to add a Google Drive remote
# The remote name should match RCLONE_REMOTE in your .env
```

### 3. Start the Stack

```bash
docker-compose up -d --build
```

This starts three containers:
- **telegram-bot-api** — Local Bot API Server on port 8081
- **bot** — Python bot + WebSocket server on port 8765
- **dashboard** — Next.js app on port 3000

### 4. Configure the Bot in Telegram

1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/mybots` → select your bot → **Bot Settings** → **Menu Button**
3. Set the URL to your dashboard (e.g., `https://your-domain.com:3000`)

### 5. Use the Bot

```
/start                    — Start the bot
/set_remote gdrive        — Set rclone remote name
/set_path /Movies/2024    — Set Google Drive folder
/process                  — Start processing all videos
/status                   — Check current progress
/cancel                   — Stop processing
/ram                      — Check memory usage
```

## Processing Pipeline

Each video goes through this sequence (strictly one at a time):

```
📥 Download (rclone copy from Google Drive)
    ↓
📸 Generate 3 Thumbnails (ffmpeg at 25%, 50%, 75% of duration)
    ↓
📤 Upload to Telegram (video + thumbnails as media group reply)
    ↓
🗑️ Cleanup (delete local video + thumbnail files)
    ↓
➡️ Next video in queue
```

## Project Structure

```
VideoThumbnailGenTGBot/
├── bot/                          # Python backend
│   ├── __init__.py
│   ├── config.py                 # Environment config
│   ├── client.py                 # Pyrogram client factory
│   ├── queue_manager.py          # Async queue + state tracking
│   ├── processor.py              # Download/thumbnail/upload pipeline
│   ├── ram_monitor.py            # psutil RAM monitoring
│   ├── ws_server.py              # FastAPI WebSocket server
│   ├── main.py                   # Entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   └── plugins/
│       ├── __init__.py
│       ├── start.py              # /start, /help commands
│       └── drive.py              # /set_remote, /set_path, /process, etc.
│
├── dashboard/                    # Next.js frontend
│   ├── package.json
│   ├── next.config.js
│   ├── jsconfig.json
│   ├── Dockerfile
│   ├── public/
│   └── src/
│       ├── app/
│       │   ├── globals.css       # Dark theme + glassmorphism
│       │   ├── layout.js         # Root layout + TG SDK
│       │   └── page.js           # Main dashboard page
│       ├── components/
│       │   ├── StatusCard.js     # Current video status
│       │   ├── QueueList.js      # Pending/completed list
│       │   ├── ProgressBar.js    # Overall progress
│       │   └── RamMonitor.js     # RAM usage display
│       └── hooks/
│           └── useWebSocket.js   # WebSocket connection hook
│
├── docker-compose.yml            # Full stack orchestration
├── .env.example                  # Environment template
└── README.md
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Bot Backend | Python 3.11, Pyrogram, FastAPI |
| File Transfer | rclone (Google Drive) |
| Video Processing | ffmpeg / ffprobe |
| Real-time Comms | FastAPI WebSockets |
| Dashboard | Next.js 14, React 18 |
| Large Files | Local Telegram Bot API Server |
| Containerization | Docker, Docker Compose |
| RAM Monitoring | psutil |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_ID` | Telegram API ID | (required) |
| `API_HASH` | Telegram API Hash | (required) |
| `BOT_TOKEN` | Bot token from BotFather | (required) |
| `RCLONE_REMOTE` | rclone remote name | `gdrive` |
| `RCLONE_PATH` | Google Drive folder path | `/` |
| `RCLONE_CONFIG_PATH` | Host path to rclone config | `~/.config/rclone` |
| `WEBAPP_URL` | Dashboard URL for TG button | — |
| `RAM_THRESHOLD_PERCENT` | Pause threshold | `85` |
| `RAM_CRITICAL_PERCENT` | Emergency threshold | `95` |
| `AUTH_USERS` | Authorized user IDs (space-separated) | `0` (all) |

## License

MIT
