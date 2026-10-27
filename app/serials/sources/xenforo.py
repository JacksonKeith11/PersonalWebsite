"""SpaceBattles, Sufficient Velocity, and Questionable Questing (all XenForo 2).

Reads the forum's "What's new → Threadmarks" listing, filtered to watched threads and
main-story threadmarks, so each sync is a single request instead of one per thread.
"""

import os
import re
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .. import db, http

FORUMS = {
    "spacebattles": ("SpaceBattles", "https://forums.spacebattles.com"),
    "sufficientvelocity": ("Sufficient Velocity", "https://forums.sufficientvelocity.com"),
    "questionablequesting": ("Questionable Questing", "https://forum.questionablequesting.com"),
}

THREAD_RE = re.compile(r"/threads/(?:([^/]*)\.)?(\d+)/")
POST_RE = re.compile(r"post-(\d+)")
MAX_PAGES = 5
# Category 1 is the main story; this skips sidebars, omakes, and informational posts.
LISTING_PARAMS = {"skip": 1, "watched_threads": 1, "threadmark_category_ids[]": 1}

# One client per forum, kept between syncs so we only log in when the session expires.
_clients: dict[str, httpx.Client] = {}


class LoginRejected(RuntimeError):
    pass


def update_key(site: str, post_id: str) -> str:
    return f"{site}#post-{post_id}"


def login(c, base: str, username: str, password: str) -> None:
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


def _parse(site: str, base: str, soup: BeautifulSoup) -> list[db.Update]:
    updates = []
    for item in soup.select(".structItem"):
        links = item.select(".structItem-title a")
        posted = item.select_one("time[datetime]")
        if len(links) < 2 or not posted:
            continue
        thread_link, mark_link = links[0], links[-1]
        url = urljoin(base, mark_link["href"])
        thread = THREAD_RE.search(thread_link.get("href", ""))
        post = POST_RE.search(url)
        if not (thread and post):
            continue
        slug = f"{thread.group(1)}." if thread.group(1) else ""
        updates.append(
            db.Update(
                key=update_key(site, post.group(1)),
                site=site,
                story_title=thread_link.get_text(strip=True),
                story_url=f"{base}/threads/{slug}{thread.group(2)}/",
                title=mark_link.get_text(strip=True) or "New threadmark",
                url=url,
                published=datetime.strptime(posted["datetime"], "%Y-%m-%dT%H:%M:%S%z").timestamp(),
            )
        )
    return updates


def fetch(key: str) -> None:
    site, base = FORUMS[key]
    username = os.environ.get(f"{key.upper()}_USERNAME")
    password = os.environ.get(f"{key.upper()}_PASSWORD")
    if not (username and password):
        raise RuntimeError("credentials not set")

    if db.creds_rejected(key, username, password):
        raise RuntimeError("password was rejected; not retrying until it changes in .env")

    c = _clients.get(key) or _clients.setdefault(key, http.client())
    r = http.get(c, f"{base}/whats-new/threadmarks/", params=LISTING_PARAMS)
    if 'data-logged-in="true"' not in r.text:
        try:
            login(c, base, username, password)
        except LoginRejected:
            db.mark_creds_rejected(key, username, password)
            raise
        r = http.get(c, f"{base}/whats-new/threadmarks/", params=LISTING_PARAMS)

    for _ in range(MAX_PAGES):
        soup = BeautifulSoup(r.text, "html.parser")
        db.save_updates(_parse(site, base, soup))
        next_page = soup.select_one("a.pageNav-jump--next")
        if not next_page:
            break
        r = http.get(c, urljoin(base, next_page["href"]))
