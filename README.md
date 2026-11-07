# IGStory Bot V2
```
   _         _____  ___         _____  __  __    __   __  _____  ___  __      
  /_\  /\ /\/__   \/___\ /\   /\\_   \/__\/ / /\ \ \ / _\/__   \/___\/__\/\_/\
 //_\\/ / \ \ / /\//  // \ \ / / / /\/_\  \ \/  \/ / \ \   / /\//  // \//\_ _/
/  _  \ \_/ // / / \_//   \ V /\/ /_//__   \  /\  /  _\ \ / / / \_// _  \ / \ 
\_/ \_/\___/ \/  \___/     \_/\____/\__/    \/  \/   \__/ \/  \___/\/ \_/ \_/ 
             AUTO VIEWER + LOVE FROM FOLLOWERS - V.2.4

```

An advanced Instagram bot for automatically viewing stories and interacting with users. Built with a robust, modular, and resilient architecture in Python.

## ✨ Features

- **Multiple Modes**:
  - **Viewer Mode**: Automatically views stories from all the accounts you follow, mimicking human behavior.
  - **Lover Mode**: A unique engagement strategy. It automatically likes the first story of each follower of *one or more specific target accounts*. If multiple targets are provided, the bot will randomly select one for each cycle.
  - **Follower Viewer Mode**: Automatically views all stories from the followers of *one or more specific target accounts*. If multiple targets are provided, the bot will randomly select one for each cycle.
  - **Parallel Hybrid Modes**: Run multiple tasks simultaneously, each in its own thread for maximum efficiency.
    - `Hybrid: View (Following) + Love (Followers)`
    - `Hybrid: View (Following) + View (Followers)`
- **Robust Login System**: Prioritizes `SESSION_ID` for stable sessions, falls back to username/password, and supports interactive handling for 2FA/Challenge codes.
- **Centralized Login & Session Sync**: Performs a single, central login for hybrid modes and automatically syncs the new `SESSION_ID` back to your configuration file after a successful login.
- **Comprehensive Telegram Monitoring**:
  - Get real-time bot status with the `/status` command, including server CPU/RAM usage.
  - Receive startup alerts, periodic "health pings", and critical failure notifications.
  - Get a summary notification after each operational cycle.
- **Smart Error Handling**: Intelligently handles common issues like session expiries and network connection errors to ensure maximum uptime.
- **Interactive Setup**: A user-friendly command-line interface guides you through the initial setup process.
- **Anti-Detection Measures**:
  - **Customizable Delays**: Fully configurable delays between actions for each mode to better mimic human behavior.
  - User-Agent rotation on each startup.
  - **Proxy Support**: Route traffic through a proxy for enhanced anonymity.
  - **Blacklist**: Easily exclude specific users from interactions.

## 📋 Requirements

- Python 3.7+
  - `instagrapi`
  - `python-dotenv`
  - `requests`
  - `psutil`

## 🚀 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/cenmurong/igstory
    cd igstory
    ```

2.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## ▶️ Usage

1.  **Run the bot (CLI):**
    ```bash
    python run.py
    ```

2.  **Run the bot from the live web page:**
    ```bash
    pip install -r requirements.txt
    python webapp.py     # serves the control panel + API on http://localhost:5000
    ```
    Open the page, paste an Instagram link/@username, switch between modes
    (View Stories · Love Stories · View Reels · Love Latest Reel) and press **Run**.

### 🚀 Deploying the backend (makes the live page fully functional)
The static page is served by Cloudflare (`wrangler.toml` → `public/`), but the
Python engine must run on a Python host. Pick **one** option:

**Option A — Free, no card: run on your own computer + Cloudflare quick tunnel**
```bash
cp configs.example.env configs/default.env   # fill in SESSION_ID
chmod +x run_local_tunnel.sh
./run_local_tunnel.sh
```
Install `cloudflared` once (no account/card needed). It prints a public
`https://....trycloudflare.com` URL — paste that into the page's **API URL**.
Downside: the backend sleeps when your computer sleeps.

**Option B — Free host with no card: PythonAnywhere**
Upload the repo, create a free "Web app" (Flask, `webapp:app`), set
`API_KEY` in its env, and use its always-on URL.

**Option C — Dockerfile on Render/Railway/Fly** (may ask for a card for
verification): uses the included `Dockerfile` / `render.yaml`.

Then, for any option:
- Set `API_KEY` on the host; the page has an **API key** field that sends it
  as `Authorization: Bearer …`.
- In the live page, set **API URL** to the backend's public URL.
- Check `GET /api/health` → should show `{"ok":true,"configured":true}`.

Run with gunicorn in production: `gunicorn -w 2 -b 0.0.0.0:8080 webapp:app`

⚠️ Never commit real keys. If a key (Render, Instagram session, Telegram)
is ever pasted somewhere public, revoke it immediately.

### 🎞 Reels Modes
- **View Reels (Target link)**: marks all reels of the target as viewed (tracked in `data/seen_reels.json`).
- **Love Latest Reel (Target link)**: likes the target's most recent reel (tracked in `data/loved_reels.json`).
- Accepts profile links, `@username`, or reel/post links (resolved via the API).

2.  **First-Time Setup:**
    On the first run for any mode, the bot will launch an interactive setup wizard. You will be prompted to enter your Instagram credentials, Telegram details, and other settings.

    - **`SESSION_ID`**: It's highly recommended to provide this for a more stable login. You can leave it blank to log in with a username/password, and the bot will automatically save the new `SESSION_ID` for future use.

3.  **Choose a Mode:**
    After setup, you will be presented with the main menu to choose an operational mode:
    - `1. Auto View Story (Following)`: Starts the viewer mode.
    - `2. Love First Story (Followers Target)`: Starts the lover mode. You can enter one or more comma-separated usernames as targets.
    - `3. Hybrid: View (Following) + Love (Followers)`: Runs viewer and lover tasks in parallel. You will be prompted for the lover task's target(s).
    - `4. Hybrid: View (Following) + View (Followers)`: Runs viewer and follower-viewer tasks in parallel.
    - `5. Reset Setup`: Allows you to re-run the setup for a specific mode or target.
    - `0. Exit`: Shuts down the bot.

## ⚙️ Configuration

All configuration files are stored as `.env` files inside the `configs/` directory.

- **`configs/default.env`**: Used for the **Viewer** mode.
- **`configs/lover.env`**: Used for the **Lover** mode (stores all targets inside).
- **`configs/follower_viewer.env`**: Used for the **Follower Viewer** mode (stores all targets inside).

### Key Variables

- `SESSION_ID`: Your Instagram session cookie. The most reliable way to log in.
- `INSTAGRAM_USERNAME` & `INSTAGRAM_PASSWORD`: Your credentials, used as a fallback if `SESSION_ID` is missing or invalid.
- `PROXY`: Optional proxy URL (e.g., `http://user:pass@host:port`).

## 🤖 Telegram Integration

The bot provides powerful monitoring capabilities through Telegram.

- **Critical Alerts**: Notifies you if the bot fails to log in after multiple attempts.

## 📂 Project Structure

```
igstory/
├── configs/              # Stores all .env configuration files
├── core/                 # Core application logic
│   ├── auth.py           # Handles login and session authentication
│   ├── actions.py        # Specific interaction functions (like, view)
│   ├── target_processor.py # Generic logic for processing a target's followers
│   ├── history.py        # Manages interaction history (seen/loved)
│   ├── hybrid.py         # Handles parallel task execution
│   ├── lover.py          # Wrapper for "Lover" mode
│   ├── follower_viewer.py# Wrapper for "Follower Viewer" mode
│   ├── viewer.py         # Task logic for "Viewer" mode
│   └── worker.py         # Generic worker for single-threaded modes
├── utils/                # Utility modules
│   ├── config.py         # Manages loading and creating configs
│   └── telegram.py       # Handles all Telegram communication
├── run.py                # Main entry point of the application
├── bot.log               # Log file for bot activities
└── README.md             # This file
```

---
## Connect With Me

<p>
  <a href="https://x.com/cenmurong"><img src="https://img.shields.io/badge/X-000000?style=for-the-badge&logo=x&logoColor=white" /></a>
  <a href="https://discord.com/users/451101979331002370"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" /></a>
  <a href="https://instagram.com/asaptrfr"><img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" /></a>
</p>

> **Disclaimer:** This bot is for educational purposes only. Automating Instagram activity may be against their terms of service. Use at your own risk.
