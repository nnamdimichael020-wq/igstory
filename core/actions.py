from instagrapi import Client
from . import humanize

def like_first_story(cl: Client, user, stories: list, config: dict = None) -> tuple[int, str]:
    """Action: Likes the first story — gated by a statistically normal like ratio."""
    if not stories:
        return 0, ""
    if humanize.messy_skip():
        return 0, ""
    ratio = (config or {}).get("LIKE_RATIO", humanize.DEFAULT_LIKE_RATIO)
    if not humanize.action_chance(ratio):
        return 0, ""

    first_story = stories[0]
    cl.story_like(first_story.pk)
    log_line = f"LOVED a story from @{user.username}"
    return 1, log_line

def view_all_stories(cl: Client, user, stories: list) -> tuple[int, str]:
    """Action: Views all available stories."""
    if not stories:
        return 0, ""
        
    story_pks_to_view = [s.pk for s in stories]
    cl.story_seen(story_pks_to_view)
    log_line = f"Viewed {len(story_pks_to_view)} stories from follower @{user.username}"
    return len(story_pks_to_view), log_line