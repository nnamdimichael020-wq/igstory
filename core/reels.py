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

    cl.media_like(reel.pk)
    LOVED[str(reel.pk)] = time.time()
    save_history(LOVED_FILE, LOVED)
    log_message(f"LOVED a reel from @{target}")
    return 1
