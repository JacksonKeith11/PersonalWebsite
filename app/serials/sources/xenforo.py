"""SpaceBattles, Sufficient Velocity, and Questionable Questing (all XenForo 2).

Logs in, reads the Watched Threads list, and pulls each thread's threadmarks RSS feed.
"""

import os
import re
import time

import feedparser
from bs4 import BeautifulSoup

from .. import db, http

FORUMS = {
    "spacebattles": ("SpaceBattles", "https://forums.spacebattles.com"),
    "sufficientvelocity": ("Sufficient Velocity", "https://forums.sufficientvelocity.com"),
    "questionablequesting": ("Questionable Questing", "https://forum.questionablequesting.com"),
}

THREAD_RE = re.compile(r"/threads/(?:([^/]*)\.)?(\d+)/")
MAX_WATCHED_PAGES = 20


class LoginRejected(RuntimeError):
    pass


def _login(c, base: str, username: str, password: str) -> None:
    page = http.get(c, f"{base}/login/")
    token = BeautifulSoup(page.text, "html.parser").find("input", {"name": "_xfToken"})
    if not token:
        raise RuntimeError("login form not found")
    r = c.post(
        f"{base}/login/login",
        data={
            "login": username,
            "password": password,
            "remember": "1",
            "_xfToken": token["value"],
            "_xfRedirect": f"{base}/",
        },
    )
    if 'data-logged-in="true"' not in r.text:
        error = BeautifulSoup(r.text, "html.parser").select_one(".blockMessage--error")
        raise LoginRejected("login failed" + (f": {error.get_text(' ', strip=True)}" if error else ""))


def _watched_threads(c, base: str) -> dict[str, tuple[str, str]]:
    """Returns {thread_id: (title, url)}."""
    threads: dict[str, tuple[str, str]] = {}
    for page in range(1, MAX_WATCHED_PAGES + 1):
        soup = BeautifulSoup(http.get(c, f"{base}/watched/threads", params={"page": page}).text, "html.parser")
        for item in soup.select(".structItem--thread"):
            link = item.select_one(".structItem-title a[data-tp-primary]") or item.select(".structItem-title a")[-1]
            m = THREAD_RE.search(link.get("href", ""))
            if m:
                slug = f"{m.group(1)}." if m.group(1) else ""
                threads[m.group(2)] = (link.get_text(strip=True), f"{base}/threads/{slug}{m.group(2)}/")
        if not soup.select_one(".pageNav-jump--next"):
            break
        time.sleep(1)
    return threads


def fetch(key: str) -> None:
    site, base = FORUMS[key]
    username = os.environ.get(f"{key.upper()}_USERNAME")
    password = os.environ.get(f"{key.upper()}_PASSWORD")
    if not (username and password):
        raise RuntimeError("credentials not set")

    if db.creds_rejected(key, username, password):
        raise RuntimeError("password was rejected; not retrying until it changes in .env")

    with http.client() as c:
        try:
            _login(c, base, username, password)
        except LoginRejected:
            db.mark_creds_rejected(key, username, password)
            raise
        threads = _watched_threads(c, base)
        errors = []
        for thread_id, (title, url) in threads.items():
            time.sleep(1)
            try:
                rss = http.get(c, f"{base}/threads/{thread_id}/threadmarks.rss", params={"threadmark_category": 1})
            except Exception as e:
                errors.append(f"{title}: {e}")
                continue
            updates = []
            for entry in feedparser.parse(rss.content).entries:
                published = http.struct_to_epoch(entry.get("published_parsed") or entry.get("updated_parsed"))
                if not (published and entry.get("link")):
                    continue
                updates.append(
                    db.Update(
                        key=entry.link,
                        site=site,
                        story_title=title,
                        story_url=url,
                        title=entry.get("title", "New threadmark"),
                        url=entry.link,
                        published=published,
                    )
                )
            db.save_updates(updates)
        if errors:
            raise RuntimeError(f"{len(threads)} threads, {len(errors)} failed: " + "; ".join(errors[:3]))
