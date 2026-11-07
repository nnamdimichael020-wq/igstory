import re
import time
import random
from pathlib import Path
from instagrapi import Client
from utils.logger import log_message
from .history import load_history, save_history

SEEN_REELS_FILE = Path("data/seen_reels.json")


def extract_username(link: str) -> str:
    """Extract an Instagram username from a profile/reel/post link or bare username."""
    link = (link or "").strip()
    if not link:
        return ""
    if "/" not in link:
        return link.lstrip("@")
    match = re.search(r"instagram\.com/(?:reel|reels|p|tv)/", link)
    if match:
        # Media link (reel/post) — username must be resolved via API; return the code marker
        code = re.search(r"instagram\.com/(?:reel|reels|p|tv)/([\w-]+)", link)
        return f"__media__:{code.group(1)}" if code else ""
    match = re.search(r"instagram\.com/([\w.]+)/?", link)
    return match.group(1) if match else link.lstrip("@")


def resolve_target(cl: Client, link: str) -> str:
    """Resolve a link/username to a plain username, using the API for media links."""
    target = extract_username(link)
    if target.startswith("__media__:"):
        code = target.split(":", 1)[1]
        media = cl.media_info(code)
        return media.user.username
    return target


def view_reels_task(cl: Client, config: dict):
    """Mark all reels of the target account as 'viewed' (reels have no official seen API)."""
    target = config["TARGET"]
    SEEN = load_history(SEEN_REELS_FILE)
    try:
        target_id = cl.user_id_from_username(target)
        reels = cl.user_reels(target_id, amount=config.get("MAX_REELS", 30))
    except Exception as e:
        log_message(f"Reels: could not fetch reels for @{target}: {e}")
        return 0

    viewed = 0
    for reel in reels:
        if str(reel.pk) not in SEEN:
            SEEN[str(reel.pk)] = time.time()
            log_message(f"Viewed reel {reel.code} from @{target}")
            viewed += 1
        time.sleep(random.uniform(2, 5))
    save_history(SEEN_REELS_FILE, SEEN)
    log_message(f"Reels viewer: {viewed} new reels viewed from @{target}.")
    return viewed


def watch_reel_task(cl: Client, config: dict):
    """'Watch' a specific reel link VIEWS times (best-effort play registration).

    Instagram has no official 'seen' API for reels, so each watch fetches the
    reel's info (which is what a real client play does) with human-like delays.
    """
    target = config["TARGET"]
    views = int(config.get("VIEWS", 1))
    try:
        code = target.split(":", 1)[1] if target.startswith("__media__:") else None
        if not code:
            # profile link — use the latest reel
            target_id = cl.user_id_from_username(target)
            reels = cl.user_reels(target_id, amount=1)
            if not reels:
                log_message(f"Reel watcher: @{target} has no reels.")
                return 0
            code = reels[0].code
        for i in range(views):
            cl.media_info(code)
            log_message(f"Watched reel https://instagram.com/reel/{code}/ (view {i + 1}/{views})")
            time.sleep(random.uniform(3, 7))
        log_message(f"Reel watcher: {views} views registered on reel /{code}/.")
        return views
    except Exception as e:
        log_message(f"Reel watcher failed: {e}")
        return 0


def love_first_reel_task(cl: Client, config: dict):
    """Like the latest (first) reel of the target account."""
    target = config["TARGET"]
    LOVED_FILE = Path("data/loved_reels.json")
    LOVED = load_history(LOVED_FILE)
    try:
        target_id = cl.user_id_from_username(target)
        reels = cl.user_reels(target_id, amount=1)
    except Exception as e:
        log_message(f"Reels lover: could not fetch reels for @{target}: {e}")
        return 0

    if not reels:
        log_message(f"Reels lover: @{target} has no reels.")
        return 0

    reel = reels[0]
    if str(reel.pk) in LOVED:
        log_message(f"Reels lover: latest reel of @{target} already loved.")
        return 0

    from . import humanize
    acted = 0
    like_ratio = config.get("LIKE_RATIO", humanize.DEFAULT_LIKE_RATIO)
    comment_ratio = config.get("COMMENT_RATIO", humanize.DEFAULT_COMMENT_RATIO)
    if not humanize.messy_skip() and humanize.action_chance(like_ratio):
        cl.media_like(reel.pk)
        LOVED[str(reel.pk)] = time.time()
        acted += 1
        log_message(f"LOVED a reel from @{target}")
    if humanize.action_chance(comment_ratio):
        try:
            cl.media_comment(reel.pk, random.choice(humanize.SAFE_COMMENTS))
            log_message(f"Commented on reel from @{target}")
            acted += 1
        except Exception as e:
            log_message(f"Comment skipped: {e}")
    if acted:
        save_history(LOVED_FILE, LOVED)
    return acted
