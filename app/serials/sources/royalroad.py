"""Royal Road: polls the public RSS feed of each fiction discovered from notification emails."""

import os
import re
import time

import feedparser

from .. import db, http

SITE = "Royal Road"
FICTION_RE = re.compile(r"(?:royalroad\.com/fiction/)?(\d+)")


def _seed_from_env() -> None:
    """ROYALROAD_FICTIONS: optional comma-separated fiction URLs or IDs to track before any email arrives."""
    for item in os.environ.get("ROYALROAD_FICTIONS", "").split(","):
        m = FICTION_RE.search(item.strip())
        if m:
            db.track("royalroad", m.group(1), f"https://www.royalroad.com/fiction/{m.group(1)}")


def fetch() -> None:
    _seed_from_env()
    errors = []
    stories = db.tracked("royalroad")
    with http.client() as c:
        for story in stories:
            try:
                r = http.get(c, f"https://www.royalroad.com/fiction/syndication/{story['story_id']}")
            except Exception as e:
                errors.append(f"{story['story_id']}: {e}")
                continue
            feed = feedparser.parse(r.content)
            story_title = feed.feed.get("title", f"Fiction {story['story_id']}")
            updates = []
            for entry in feed.entries:
                published = http.struct_to_epoch(entry.get("published_parsed"))
                if not (published and entry.get("link")):
                    continue
                title = entry.get("title", "New chapter")
                # Item titles are usually "<Fiction> - <Chapter>".
                if title.startswith(f"{story_title} - "):
                    title = title[len(story_title) + 3 :]
                updates.append(
                    db.Update(
                        key=entry.link,
                        site=SITE,
                        story_title=story_title,
                        story_url=story["story_url"],
                        title=title,
                        url=entry.link,
                        published=published,
                    )
                )
            db.save_updates(updates)
            time.sleep(1)
    if errors:
        raise RuntimeError(f"{len(stories)} fictions, {len(errors)} failed: " + "; ".join(errors[:3]))
