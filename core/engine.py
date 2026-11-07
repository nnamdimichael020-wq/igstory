"""
Server-side bot engine: a job queue processed by a pool of worker threads.

Each worker owns its own instagrapi Client (thread-local login), so multiple
jobs can run concurrently. Run history and stats persist to data/stats.json.

Live-state features: per-job progress, pause/resume, mute (suppresses Telegram
notifications), and a heartbeat thread that self-syncs every 60 seconds.
"""
import json
import queue
import random
import threading
import time
import traceback
from pathlib import Path

from utils.logger import log_message
from utils.config import load_config
from core.auth import handle_login
from core.viewer import viewer_task
from core.lover import lover_task
from core.follower_viewer import follower_viewer_task
from core.reels import view_reels_task, love_first_reel_task, watch_reel_task, resolve_target

DATA_DIR = Path("data")
STATS_FILE = DATA_DIR / "stats.json"
BLACKLIST_FILE = Path("blacklist.txt")

MODES = {
    "view_stories": ("View Stories (Following)", viewer_task),
    "love_stories": ("Love Stories (Followers of Target)", lover_task),
    "view_reels":   ("View Reels (Target link)", view_reels_task),
    "love_reels":   ("Love Latest Reel (Target link)", love_first_reel_task),
    "watch_reel":   ("Watch Reel N Times (reel link)", watch_reel_task),
    "follower_viewer": ("View Stories of Followers (Target link)", follower_viewer_task),
}
TARGET_MODES = ("love_stories", "view_reels", "love_reels", "watch_reel", "follower_viewer")


class BotEngine:
    def __init__(self, max_workers: int = 2):
        self.max_workers = max_workers
        self.job_queue: "queue.Queue[int]" = queue.Queue()
        self.jobs: dict[int, dict] = {}
        self.history: list[dict] = []
        self.lock = threading.Lock()
        self._stop_events: dict[int, threading.Event] = {}
        self._pause_events: dict[int, threading.Event] = {}
        self._tls = threading.local()
        self.stats = self._load_stats()
        # Heartbeat: engine self-syncs every 60s (liveness stamp + stats flush)
        self.heartbeat = {"last": None, "count": 0, "interval": 60}
        self._workers = [
            threading.Thread(target=self._worker_loop, args=(i,), daemon=True, name=f"bot-worker-{i}")
            for i in range(max_workers)
        ]
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name="bot-heartbeat")
        for w in self._workers:
            w.start()
        self._heartbeat_thread.start()

    # ---------- persistence ----------
    def _load_stats(self) -> dict:
        if STATS_FILE.exists():
            try:
                return json.loads(STATS_FILE.read_text())
            except Exception:
                pass
        return {"total_actions": 0, "total_jobs": 0, "started": time.strftime("%Y-%m-%d %H:%M:%S")}

    def _save_stats(self):
        DATA_DIR.mkdir(exist_ok=True)
        with self.lock:
            STATS_FILE.write_text(json.dumps(self.stats, indent=2))

    # ---------- session per worker thread ----------
    def _client(self, config):
        cl = getattr(self._tls, "client", None)
        if cl is not None:
            return cl
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
        self._tls.client = cl
        return cl

    # ---------- public API ----------
    def submit(self, modes, link="", views=1, interval_min=0) -> int:
        job_id = int(time.time() * 1000) % 10**10
        ev = threading.Event()
        with self.lock:
            self.jobs[job_id] = {
                "id": job_id, "modes": list(modes), "link": link, "views": views,
                "interval": interval_min, "status": "queued", "logs": [],
                "result": None, "error": None, "queued_at": time.strftime("%H:%M:%S"),
                "paused": False, "muted": False,
                "progress": {"cycle": 0, "actions": 0},
            }
            self._stop_events[job_id] = ev
            self._pause_events[job_id] = threading.Event()
            self.stats["total_jobs"] += 1
        self.job_queue.put(job_id)
        return job_id

    def stop(self, job_id=None):
        with self.lock:
            targets = [job_id] if job_id else list(self._stop_events)
            for jid in targets:
                if jid in self._stop_events:
                    self._stop_events[jid].set()
                if jid in self.jobs and self.jobs[jid]["status"] in ("queued", "running", "paused"):
                    self.jobs[jid]["status"] = "stopped"

    def pause(self, job_id=None):
        with self.lock:
            targets = [job_id] if job_id else list(self.jobs)
            for jid in targets:
                if jid in self.jobs and self.jobs[jid]["status"] == "running":
                    self.jobs[jid]["paused"] = True
                    self.jobs[jid]["status"] = "paused"
                    self._pause_events[jid].set()

    def resume(self, job_id=None):
        with self.lock:
            targets = [job_id] if job_id else list(self.jobs)
            for jid in targets:
                if jid in self.jobs and self.jobs[jid]["status"] == "paused":
                    self.jobs[jid]["paused"] = False
                    self.jobs[jid]["status"] = "running"
                    self._pause_events[jid].clear()

    def set_mute(self, job_id=None, muted: bool = True):
        with self.lock:
            targets = [job_id] if job_id else list(self.jobs)
            for jid in targets:
                if jid in self.jobs:
                    self.jobs[jid]["muted"] = bool(muted)

    def clear(self):
        with self.lock:
            for j in self.jobs.values():
                j["logs"] = []
            self.history = []

    def status(self) -> dict:
        with self.lock:
            return {
                "workers": self.max_workers,
                "queue": self.job_queue.qsize(),
                "jobs": [dict(j) for j in self.jobs.values()],
                "history": list(self.history[-50:]),
                "stats": dict(self.stats),
                "heartbeat": dict(self.heartbeat),
                "now": time.strftime("%H:%M:%S"),
            }

    def blacklist(self):
        if BLACKLIST_FILE.exists():
            return [l.strip() for l in BLACKLIST_FILE.read_text().splitlines() if l.strip()]
        return []

    def set_blacklist(self, users: list[str]):
        BLACKLIST_FILE.write_text("\n".join(u.strip().lstrip("@") for u in users if u.strip()) + "\n")

    # ---------- internals ----------
    def _log(self, job_id, line):
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]["logs"].append(f"[{time.strftime('%H:%M:%S')}] {line}")
                if len(self.jobs[job_id]["logs"]) > 300:
                    self.jobs[job_id]["logs"] = self.jobs[job_id]["logs"][-300:]

    def _heartbeat_loop(self):
        """Self-sync every minute: stamp liveness and flush stats to disk."""
        while True:
            time.sleep(self.heartbeat["interval"])
            with self.lock:
                self.heartbeat["last"] = time.strftime("%H:%M:%S")
                self.heartbeat["count"] += 1
            self._save_stats()
            log_message(f"♥ heartbeat #{self.heartbeat['count']} — engine alive, stats synced")

    def _wait_if_paused(self, job_id):
        ev = self._pause_events.get(job_id)
        while ev and ev.is_set():
            time.sleep(1)
            if self._stop_events.get(job_id) and self._stop_events[job_id].is_set():
                return

    def _worker_loop(self, worker_idx):
        while True:
            job_id = self.job_queue.get()
            try:
                self._run_job(job_id)
            except Exception:
                traceback.print_exc()
            finally:
                self.job_queue.task_done()

    def _run_job(self, job_id):
        ev = self._stop_events.get(job_id)
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job["status"] == "stopped":
                return
            job["status"] = "running"
            job["logs"] = []
        modes, link, views, interval = job["modes"], job["link"], job["views"], job["interval"]
        self._log(job_id, f"Starting mode(s): {', '.join(MODES[m][0] for m in modes)}" + (f" for '{link}'" if link else ""))
        if interval > 0:
            self._log(job_id, f"Auto-repeat every {interval} min until stopped.")
        try:
            config = load_config()
            config["MAX_REELS"] = 30
            config["VIEWS"] = max(1, int(views or 1))
            with self.lock:
                if self.jobs[job_id]["muted"]:
                    config["TELEGRAM_TOKEN"] = None  # muted: no notifications
            cl = self._client(config)

            cycle = 0
            while not ev.is_set():
                self._wait_if_paused(job_id)
                if ev.is_set():
                    break
                cycle += 1
                total = 0
                for mode in modes:
                    if ev.is_set():
                        break
                    self._wait_if_paused(job_id)
                    if ev.is_set():
                        break
                    if mode in TARGET_MODES:
                        if not link:
                            raise ValueError("Please provide an Instagram profile/reel link for this mode.")
                        target = resolve_target(cl, link)
                        config["TARGET"] = target
                        config["TARGETS"] = [target]
                        self._log(job_id, f"[{MODES[mode][0]}] resolved target: {link if target.startswith('__media__') else '@' + target}")
                    self._log(job_id, f"▶ Cycle {cycle} — running: {MODES[mode][0]}")
                    count = MODES[mode][1](cl, config) or 0
                    total += count
                    with self.lock:
                        self.jobs[job_id]["progress"] = {"cycle": cycle, "actions": total}
                    self._log(job_id, f"✔ {MODES[mode][0]} done: {count} action(s).")

                with self.lock:
                    job["result"] = total
                    self.stats["total_actions"] += total
                    self.history.append({"id": job_id, "cycle": cycle, "modes": list(modes),
                                         "status": "stopped" if ev.is_set() else "done",
                                         "result": total, "time": time.strftime("%H:%M:%S")})
                    if len(self.history) > 50:
                        del self.history[:-50]
                self._save_stats()
                self._log(job_id, f"Cycle {cycle} finished: {total} action(s).")

                if interval <= 0 or ev.is_set():
                    break
                wait_until = time.time() + interval * 60
                while time.time() < wait_until and not ev.is_set():
                    time.sleep(1)

            with self.lock:
                job["status"] = "stopped" if ev.is_set() else "done"
            self._log(job_id, "Job finished.")
        except Exception as e:
            traceback.print_exc()
            with self.lock:
                job["status"] = "error"
                job["error"] = str(e)
                self.history.append({"id": job_id, "cycle": 0, "modes": list(modes),
                                     "status": "error", "result": None, "error": str(e),
                                     "time": time.strftime("%H:%M:%S")})
            self._log(job_id, f"ERROR: {e}")


engine = BotEngine(max_workers=2)
