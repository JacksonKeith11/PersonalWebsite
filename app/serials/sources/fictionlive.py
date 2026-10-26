"""fiction.live: polls the public API for each story discovered from notification emails."""

import re
import time

from .. import db, http

SITE = "fiction.live"


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "chapter"


def story_url(slug: str, story_id: str) -> str:
    return f"https://fiction.live/stories/{slug}/{story_id}"


def fetch() -> None:
    errors = []
    stories = db.tracked("fictionlive")
    with http.client() as c:
        for story in stories:
            story_id = story["story_id"]
            try:
                node = http.get(c, f"https://fiction.live/api/node/{story_id}").json()
            except Exception as e:
                errors.append(f"{story_id}: {e}")
                continue
            title = node.get("t") or story_id
            url = story_url(_slugify(title), story_id)
            db.track("fictionlive", story_id, url)
            updates = [
                db.Update(
                    key=f"fictionlive:{story_id}:{chapter['id']}",
                    site=SITE,
                    story_title=title,
                    story_url=url,
                    title=chapter.get("title") or "New chapter",
                    url=f"{url}/{_slugify(chapter.get('title') or '')}/{chapter['id']}",
                    published=chapter["ct"] / 1000,
                )
                for chapter in node.get("bm") or []
                if chapter.get("id") and chapter.get("ct")
            ]
            db.save_updates(updates)
            time.sleep(1)
    if errors:
        raise RuntimeError(f"{len(stories)} stories, {len(errors)} failed: " + "; ".join(errors[:3]))
