"""
Anti-detection humanization primitives.

Goal: messy, incomplete, multi-signal behavior instead of machine-perfect
timing. Delays are jittered with occasional long pauses; watch times follow a
natural drop-off curve; like/comment decisions follow statistically normal
ratios; sessions vary in length and time of day.
"""
import random
import time

# Statistically normal defaults (fractions of viewed items)
DEFAULT_LIKE_RATIO = 0.10     # ~1 like per 10 views
DEFAULT_COMMENT_RATIO = 0.01  # ~1 comment per 100 views

SAFE_COMMENTS = [
    "Nice! 🔥", "Love this 😍", "Great post!", "This is awesome 👏",
    "So good!", "🔥🔥", "Amazing!", "Wow 😮",
]


def human_delay(min_s: float = 4.0, max_s: float = 12.0) -> float:
    """Jittered delay with occasional long 'human' pauses (~5% of the time)."""
    d = random.uniform(min_s, max_s)
    if random.random() < 0.05:
        d += random.uniform(15, 45)  # got distracted
    return d


def watch_time(min_s: float = 2.0, max_s: float = 9.0, full_s: float = 30.0) -> float:
    """Watch time with a natural drop-off curve: most views short, some medium,
    some full-length, some abandoned mid-video, occasional rewatches."""
    r = random.random()
    if r < 0.55:      # drop-off: short view
        return random.uniform(min_s, min_s + 2)
    if r < 0.80:      # medium dwell
        return random.uniform(min_s + 2, max_s)
    if r < 0.92:      # full watch
        return random.uniform(max_s, full_s)
    if r < 0.97:      # abandon mid-video
        return random.uniform(0.5, min_s)
    return random.uniform(min_s, max_s) + random.uniform(min_s, max_s)  # rewatch


def session_length() -> float:
    """Session length in minutes, varied by time of day (local hour) plus noise."""
    hour = time.localtime().tm_hour
    if 0 <= hour < 6:
        base = random.uniform(3, 12)      # late night: quick check
    elif 6 <= hour < 12:
        base = random.uniform(8, 25)      # morning
    elif 12 <= hour < 17:
        base = random.uniform(10, 30)     # afternoon
    else:
        base = random.uniform(15, 45)     # evening: longest
    return base * random.uniform(0.5, 1.5)  # messy multiplier


def time_of_day_gap() -> float:
    """Irregular gap between sessions (minutes), incl. occasional long breaks."""
    r = random.random()
    if r < 0.70:
        return random.uniform(5, 60)
    if r < 0.95:
        return random.uniform(60, 240)
    return random.uniform(240, 720)  # hours offline


def messy_skip(chance: float = 0.05) -> bool:
    """Occasionally skip an action entirely (incomplete data signal)."""
    return random.random() < chance


def action_chance(ratio: float) -> bool:
    """Decide whether to like/comment given a view, per the ratio."""
    return random.random() < max(0.0, min(1.0, ratio))


def sleep_human(min_s: float = 4.0, max_s: float = 12.0):
    time.sleep(human_delay(min_s, max_s))


def multi_action_sequence() -> list:
    """A realistic burst: view -> (like) -> (comment) -> scroll -> leave.
    Not every element fires every time (messy)."""
    seq = ["view", "scroll"]
    if random.random() < 0.35:
        seq.insert(1, "like")
    if random.random() < 0.05:
        seq.insert(-1, "comment")
    if random.random() < 0.15:
        seq.insert(1, "rewatch")
    seq.append("leave")
    return seq
