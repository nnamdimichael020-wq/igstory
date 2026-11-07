"""
Anti-detection humanization primitives.

Goal: messy, incomplete, multi-signal behavior instead of machine-perfect
timing. All delays are jittered with occasional long pauses; watch times vary
naturally; like/comment decisions follow configurable but statistically normal
ratios (e.g. like ~10% of views, comment ~1%).
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


def watch_time(min_s: float = 2.0, max_s: float = 9.0) -> float:
    """Natural variation in how long an item is watched."""
    # skew: most watches short, a few long
    return min_s + (max_s - min_s) * (random.random() ** 2)


def messy_skip(chance: float = 0.05) -> bool:
    """Occasionally skip an action entirely (incomplete data signal)."""
    return random.random() < chance


def action_chance(ratio: float) -> bool:
    """Decide whether to like/comment given a view, per the ratio."""
    return random.random() < max(0.0, min(1.0, ratio))


def sleep_human(min_s: float = 4.0, max_s: float = 12.0):
    time.sleep(human_delay(min_s, max_s))
