"""
IGStory Bot V2 — Web API + live page backend.

Run locally:
    pip install -r requirements.txt
    python webapp.py            # serves the page + API on http://0.0.0.0:5000

The Cloudflare Worker serves the static page from public/; point the page's
"API URL" setting at the host where this Flask app runs (e.g. your Render /
Railway / VPS URL), since Cloudflare Workers cannot execute Python.
"""
import threading
import time
import traceback
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from utils.logger import setup_logger, log_message
from utils.config import load_config
from core.auth import handle_login
from core.viewer import viewer_task
from core.lover import lover_task
from core.reels import view_reels_task, love_first_reel_task, resolve_target

setup_logger()

BASE_DIR = Path(__file__).parent
PUBLIC_DIR = BASE_DIR / "public"

app = Flask(__name__, static_folder=str(PUBLIC_DIR), static_url_path="")

MODES = {
    "view_stories": ("View Stories (Following)", viewer_task),
    "love_stories": ("Love Stories (Followers of Target)", lover_task),
    "view_reels":   ("View Reels (Target link)", view_reels_task),
    "love_reels":   ("Love Latest Reel (Target link)", love_first_reel_task),
}

# Shared state
_state_lock = threading.Lock()
_client = None
_job = {"id": None, "mode": None, "status": "idle", "logs": [], "result": None, "error": None}


def get_client(config):
    """Log in once and reuse the client across runs."""
    global _client
    if _client is not None:
        return _client
    import random
    from instagrapi import Client
    from core.worker import USER_AGENTS
    cl = Client()
    cl.private_requests = True
    cl.user_agent = random.choice(USER_AGENTS)
    if config.get("PROXY"):
        cl.set_proxy(config["PROXY"])
    cl.delay_range = [8, 16]
    if not handle_login(cl, config):
        raise RuntimeError("Login failed — check SESSION_ID / credentials in configs/default.env")
    _client = cl
    return cl


def append_log(line):
    with _state_lock:
        _job["logs"].append(f"[{time.strftime('%H:%M:%S')}] {line}")
        if len(_job["logs"]) > 300:
            _job["logs"] = _job["logs"][-300:]


def run_job(job_id, mode, link):
    global _job
    try:
        with _state_lock:
            _job.update({"id": job_id, "mode": mode, "status": "running", "logs": [], "result": None, "error": None})
        append_log(f"Starting mode '{MODES[mode][0]}'" + (f" for '{link}'" if link else ""))

        config = load_config()
        config["MAX_REELS"] = 30
        cl = get_client(config)

        if mode in ("love_stories", "view_reels", "love_reels"):
            if not link:
                raise ValueError("Please provide an Instagram profile/reel link for this mode.")
            target = resolve_target(cl, link)
            config["TARGET"] = target
            config["TARGETS"] = [target]
            append_log(f"Resolved target: @{target}")

        task = MODES[mode][1]
        count = task(cl, config) or 0
        with _state_lock:
            _job["status"] = "done"
            _job["result"] = count
        append_log(f"Finished: {count} action(s).")
    except Exception as e:
        traceback.print_exc()
        with _state_lock:
            _job["status"] = "error"
            _job["error"] = str(e)
        append_log(f"ERROR: {e}")


@app.route("/")
def index():
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.route("/api/modes")
def modes():
    return jsonify({k: v[0] for k, v in MODES.items()})


@app.route("/api/run", methods=["POST"])
def api_run():
    data = request.get_json(force=True)
    mode = data.get("mode", "")
    link = (data.get("link") or "").strip()
    if mode not in MODES:
        return jsonify({"error": "Unknown mode"}), 400
    with _state_lock:
        if _job["status"] == "running":
            return jsonify({"error": "A job is already running"}), 409
        job_id = int(time.time())
    t = threading.Thread(target=run_job, args=(job_id, mode, link), daemon=True)
    t.start()
    return jsonify({"job_id": job_id, "status": "running"})


@app.route("/api/status")
def api_status():
    with _state_lock:
        return jsonify(dict(_job))


@app.route("/api/stop", methods=["POST"])
def api_stop():
    # Threads are daemonized; we just mark the job stopped.
    global _job
    with _state_lock:
        if _job["status"] == "running":
            _job["status"] = "stopped"
            append_log("Stop requested (finishes current action, then halts).")
    return jsonify({"status": "stopped"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
