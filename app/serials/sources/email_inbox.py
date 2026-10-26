"""Reads notification emails from a Gmail label over IMAP.

- AO3 subscription emails become updates directly (AO3 itself is never contacted).
- fiction.live "has gone live" emails become updates, and register the story for chapter polling.
- Any Royal Road fiction linked in an email is registered for RSS polling.
"""

import email
import imaplib
import os
import re
import time
from email import policy
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from .. import db
from . import fictionlive

ROYALROAD_RE = re.compile(r"https?://(?:www\.)?royalroad\.com/fiction/(\d+)(?:/([\w-]+))?")
FICTIONLIVE_RE = re.compile(r"https?://fiction\.live/stories/([^/\s'\"<>]+)/([A-Za-z0-9]{17})")
GONE_LIVE_RE = re.compile(r"^(.*) has gone live\s*$", re.IGNORECASE)
AO3_WORK_RE = re.compile(r"^https?://archiveofourown\.org/works/(\d+)/?$")
AO3_CHAPTER_RE = re.compile(r"^https?://archiveofourown\.org/works/(\d+)/chapters/(\d+)")
AO3_SUBJECT_RE = re.compile(r"posted (?:.* of )?(.+)$")


def _body(msg: email.message.EmailMessage) -> str:
    parts = [p for p in msg.walk() if p.get_content_type() in ("text/html", "text/plain")]
    return "\n".join(p.get_content() for p in parts)


def _ao3_updates(msg: email.message.EmailMessage, subject: str, sent: float) -> list[db.Update]:
    html = next((p.get_content() for p in msg.walk() if p.get_content_type() == "text/html"), "")
    links = [(a["href"], a.get_text(" ", strip=True)) for a in BeautifulSoup(html, "html.parser").find_all("a", href=True)]

    work_titles: dict[str, str] = {}
    for href, text in links:
        m = AO3_WORK_RE.match(href)
        if m and text:
            work_titles.setdefault(m.group(1), text)
    fallback = AO3_SUBJECT_RE.search(subject)

    def work_title(work_id: str) -> str:
        return work_titles.get(work_id) or (fallback.group(1) if fallback else f"Work {work_id}")

    updates = []
    for href, text in links:
        m = AO3_CHAPTER_RE.match(href)
        if m:
            url = f"https://archiveofourown.org/works/{m.group(1)}/chapters/{m.group(2)}"
            updates.append(
                db.Update(
                    key=url,
                    site="AO3",
                    story_title=work_title(m.group(1)),
                    story_url=f"https://archiveofourown.org/works/{m.group(1)}",
                    title=text or "New chapter",
                    url=url,
                    published=sent,
                )
            )
    if not updates and "posted" in subject:
        # A new work from a subscribed author links only to the work itself.
        for work_id in work_titles:
            url = f"https://archiveofourown.org/works/{work_id}"
            updates.append(
                db.Update(key=url, site="AO3", story_title=work_title(work_id), story_url=url, title="New work", url=url, published=sent)
            )
    return list({u.key: u for u in updates}.values())


def _process(msg: email.message.EmailMessage) -> None:
    body = _body(msg)
    subject = str(msg.get("Subject", ""))
    sent = parsedate_to_datetime(msg["Date"]).timestamp() if msg["Date"] else time.time()

    if "archiveofourown.org" in str(msg.get("From", "")):
        db.save_updates(_ao3_updates(msg, subject, sent))
        return

    for fiction_id, slug in set(ROYALROAD_RE.findall(body)):
        url = f"https://www.royalroad.com/fiction/{fiction_id}" + (f"/{slug}" if slug else "")
        db.track("royalroad", fiction_id, url)

    stories = set(FICTIONLIVE_RE.findall(body))
    for slug, story_id in stories:
        db.track("fictionlive", story_id, fictionlive.story_url(slug, story_id))

    live = GONE_LIVE_RE.match(subject)
    if live and stories:
        slug, story_id = next(iter(stories))
        db.save_updates(
            [
                db.Update(
                    key=f"fictionlive-live:{msg.get('Message-ID') or f'{story_id}:{sent}'}",
                    site=fictionlive.SITE,
                    story_title=live.group(1).strip(),
                    story_url=fictionlive.story_url(slug, story_id),
                    title="Went live",
                    url=fictionlive.story_url(slug, story_id),
                    published=sent,
                )
            ]
        )


def fetch() -> None:
    address = os.environ.get("GMAIL_ADDRESS")
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    label = os.environ.get("GMAIL_LABEL", "serials")
    if not (address and password):
        raise RuntimeError("credentials not set")

    if db.creds_rejected("gmail", address, password):
        raise RuntimeError("app password was rejected; not retrying until it changes in .env")

    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        try:
            imap.login(address, password)
        except imaplib.IMAP4.error as e:
            if "AUTHENTICATIONFAILED" in str(e):
                db.mark_creds_rejected("gmail", address, password)
            raise
        typ, _ = imap.select(f'"{label}"', readonly=True)
        if typ != "OK":
            raise RuntimeError(f"label '{label}' not found")

        # UIDs are only stable within one UIDVALIDITY; start over if it changes.
        validity = imap.response("UIDVALIDITY")[1][0].decode()
        if db.get_state("imap_uidvalidity") != validity:
            db.set_state("imap_uidvalidity", validity)
            db.set_state("imap_last_uid", "0")
        last_uid = int(db.get_state("imap_last_uid", "0"))

        _, data = imap.uid("search", None, f"UID {last_uid + 1}:*")
        # "N:*" always matches the newest message, even when it is older than N.
        uids = [int(u) for u in data[0].split() if int(u) > last_uid]
        for uid in sorted(uids):
            _, msg_data = imap.uid("fetch", str(uid), "(RFC822)")
            raw = next(part[1] for part in msg_data if isinstance(part, tuple))
            _process(email.message_from_bytes(raw, policy=policy.default))
            db.set_state("imap_last_uid", str(uid))
    finally:
        try:
            imap.logout()
        except Exception:
            pass
