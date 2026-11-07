"""
IGStory Bot V2 — Web API + live page backend (server-side bot engine).

Run locally:
    pip install -r requirements.txt
    python webapp.py            # serves the page + API on http://0.0.0.0:5000
Production:
    gunicorn -w 2 -b 0.0.0.0:8080 webapp:app

The Cloudflare Worker serves the static page from public/; point the page's
"API URL" setting at the host where this app runs (PythonAnywhere, Render, ...).
The heavy lifting is done by core/engine.py: a worker-pool job queue where
each worker thread owns its own Instagram session.
"""
import os
from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from utils.logger import setup_logger
from core.engine import engine, MODES

setup_logger()

BASE_DIR = Path(__file__).parent
PUBLIC_DIR = BASE_DIR / "public"

app = Flask(__name__, static_folder=str(PUBLIC_DIR), static_url_path="")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Optional shared-secret guard: set API_KEY to require Bearer auth on /api/*
API_KEY = os.environ.get("API_KEY", "")

def require_key(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if API_KEY:
            provided = request.headers.get("Authorization", "").replace("Bearer ", "") \
                       or request.args.get("key", "")
            if provided != API_KEY:
                return jsonify({"error": "unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.route("/api/health")
def api_health():
    env_ok = (BASE_DIR / "configs" / "default.env").exists()
    return jsonify({"ok": True, "configured": env_ok, "workers": engine.max_workers})


@app.route("/api/modes")
@require_key
def modes():
    return jsonify({k: v[0] for k, v in MODES.items()})


@app.route("/api/run", methods=["POST"])
@require_key
def api_run():
    data = request.get_json(force=True)
    modes = data.get("modes") or ([data["mode"]] if data.get("mode") else [])
    if not modes or any(m not in MODES for m in modes):
        return jsonify({"error": "Unknown mode"}), 400
    job_id = engine.submit(
        modes,
        link=(data.get("link") or "").strip(),
        views=data.get("views", 1),
        interval_min=max(0, int(data.get("interval", 0) or 0)),
    )
    return jsonify({"job_id": job_id, "status": "queued"})


@app.route("/api/status")
@require_key
def api_status():
    return jsonify(engine.status())


@app.route("/api/stop", methods=["POST"])
@require_key
def api_stop():
    data = request.get_json(silent=True) or {}
    engine.stop(data.get("job_id"))
    return jsonify({"status": "stopped"})


@app.route("/api/clear", methods=["POST"])
@require_key
def api_clear():
    engine.clear()
    return jsonify({"ok": True})


@app.route("/api/blacklist", methods=["GET"])
@require_key
def api_blacklist_get():
    return jsonify({"blacklist": engine.blacklist()})


@app.route("/api/blacklist", methods=["POST"])
@require_key
def api_blacklist_post():
    data = request.get_json(force=True)
    engine.set_blacklist(data.get("users", []))
    return jsonify({"blacklist": engine.blacklist()})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), threaded=True)
