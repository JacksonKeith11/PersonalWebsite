"""Reads notification emails from a Gmail label over IMAP.

Every update comes straight from the email; AO3, Royal Road, and fiction.live are never contacted.
"""

import email
import imaplib
import os
import re
import time
from email import policy
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .. import db

AO3_WORK_RE = re.compile(r"^https?://archiveofourown\.org/works/(\d+)/?$")
AO3_CHAPTER_RE = re.compile(r"^https?://archiveofourown\.org/works/(\d+)/chapters/(\d+)")
AO3_SUBJECT_RE = re.compile(r"posted (?:.* of )?(.+)$")
AO3_AUTHOR_RE = re.compile(r"^https?://archiveofourown\.org/users/[^/]+/pseuds/[^/?#]+")
AO3_SUBJECT_AUTHOR_RE = re.compile(r"^\[AO3\] (.+?) posted ")
ROYALROAD_FICTION_RE = re.compile(r"^https?://(?:www\.)?royalroad\.com/fiction/(\d+)(?:/[\w-]+)?/?(?:[?#].*)?$")
ROYALROAD_CHAPTER_RE = re.compile(r"^https?://(?:www\.)?royalroad\.com/fiction/(\d+)(?:/[\w-]+)?/chapter/(\d+)(?:/[\w-]+)?")
# Royal Road emails only link through a click tracker, so the details come from the text:
# "<author> has just posted a new chapter of <fiction> titled <chapter>.\nYou can read it at <url>"
ROYALROAD_SUBJECT_RE = re.compile(r"^New Chapter of (.+)$", re.IGNORECASE)
ROYALROAD_TITLED_RE = re.compile(r"new chapter of (.+?) titled (.+?)\.?\s*$", re.IGNORECASE | re.MULTILINE)
ROYALROAD_READ_RE = re.compile(r"read it at (https?://\S+)", re.IGNORECASE)
FICTIONLIVE_STORY_RE = re.compile(r"^https?://fiction\.live/stories/([^/?#'\"]+)/([A-Za-z0-9]{17})/?(?:[?#].*)?$")
FICTIONLIVE_CHAPTER_RE = re.compile(r"^https?://fiction\.live/stories/([^/?#'\"]+)/([A-Za-z0-9]{17})/[^/?#'\"]+/([A-Za-z0-9]{17})")
GONE_LIVE_RE = re.compile(r"^(.*) has gone live\s*$", re.IGNORECASE)
FICTIONLIVE_USER_RE = re.compile(r"^https?://fiction\.live/user/([^/?#'\"]+)")
URL_RE = re.compile(r"https?://[^\s'\"<>()]+")
# Link text that says nothing about the chapter, e.g. a "Read now" button.
GENERIC_LINK_TEXT = {"", "read", "read now", "read it here", "read chapter", "read the chapter", "click here", "here", "view"}
PLACEHOLDER_TITLES = {"New chapter", "New work", "Update"}


def _links(msg: email.message.EmailMessage) -> list[tuple[str, str]]:
    """(href, link text) for every link, from the HTML part if there is one, else bare URLs in the text."""
    html = next((p.get_content() for p in msg.walk() if p.get_content_type() == "text/html"), "")
    if html:
        return [(a["href"].strip(), a.get_text(" ", strip=True)) for a in BeautifulSoup(html, "html.parser").find_all("a", href=True)]
    text = next((p.get_content() for p in msg.walk() if p.get_content_type() == "text/plain"), "")
    return [(url, "") for url in URL_RE.findall(text)]


def _label(text: str, default: str) -> str:
    return default if text.strip().lower() in GENERIC_LINK_TEXT else text


def _ao3_updates(links: list[tuple[str, str]], subject: str, sent: float) -> list[db.Update]:
    work_titles: dict[str, str] = {}
    for href, text in links:
        m = AO3_WORK_RE.match(href)
        if m and text:
            work_titles.setdefault(m.group(1), text)
    fallback = AO3_SUBJECT_RE.search(subject)
    authors = list(dict.fromkeys(text for href, text in links if AO3_AUTHOR_RE.match(href) and text))
    subject_author = AO3_SUBJECT_AUTHOR_RE.match(subject)
    author = ", ".join(authors) or (subject_author.group(1) if subject_author else "")

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
                    title=_label(text, "New chapter"),
                    url=url,
                    published=sent,
                    author=author,
                )
            )
    if not updates and "posted" in subject:
        # A new work from a subscribed author links only to the work itself.
        for work_id in work_titles:
            url = f"https://archiveofourown.org/works/{work_id}"
            updates.append(
                db.Update(
                    key=url,
                    site="AO3",
                    story_title=work_title(work_id),
                    story_url=url,
                    title="New work",
                    url=url,
                    published=sent,
                    author=author,
                )
            )
    return updates


def _plain_text(msg: email.message.EmailMessage) -> str:
    return next((p.get_content() for p in msg.walk() if p.get_content_type() == "text/plain"), "")


def _royalroad_tracked_update(msg: email.message.EmailMessage, links: list[tuple[str, str]], subject: str, sent: float) -> list[db.Update]:
    """Chapter notification whose only links go through Royal Road's click tracker."""
    text = _plain_text(msg)
    read = ROYALROAD_READ_RE.search(text)
    url = read.group(1) if read else next((href for href, label in links if label.strip().lower() == "read now"), None)
    subject_match = ROYALROAD_SUBJECT_RE.match(subject)
    if not (url and subject_match):
        return []
    fiction = subject_match.group(1).strip()
    chapter = "New chapter"
    # Prefer splitting on the exact fiction title, since chapter titles can contain " titled ".
    marker = f"{fiction} titled "
    for line in text.splitlines():
        if marker in line:
            chapter = line.split(marker, 1)[1].strip().rstrip(".") or chapter
            break
    else:
        titled = ROYALROAD_TITLED_RE.search(text)
        if titled:
            chapter = titled.group(2).strip()
    return [
        db.Update(
            key=f"royalroad:{msg.get('Message-ID') or url}",
            site="Royal Road",
            story_title=fiction,
            story_url=f"https://www.royalroad.com/fictions/search?{urlencode({'title': fiction})}",
            title=chapter,
            url=url,
            published=sent,
        )
    ]


def _royalroad_updates(msg: email.message.EmailMessage, links: list[tuple[str, str]], subject: str, sent: float) -> list[db.Update]:
    fiction_titles: dict[str, str] = {}
    for href, text in links:
        m = ROYALROAD_FICTION_RE.match(href)
        if m and _label(text, ""):
            fiction_titles.setdefault(m.group(1), text)

    updates = []
    for href, text in links:
        m = ROYALROAD_CHAPTER_RE.match(href)
        if m:
            url = "https://www.royalroad.com" + href.split("royalroad.com", 1)[1].split("?")[0].split("#")[0]
            updates.append(
                db.Update(
                    key=f"royalroad:chapter:{m.group(2)}",
                    site="Royal Road",
                    story_title=fiction_titles.get(m.group(1)) or subject,
                    story_url=f"https://www.royalroad.com/fiction/{m.group(1)}",
                    title=_label(text, "New chapter"),
                    url=url,
                    published=sent,
                )
            )
    return updates or _royalroad_tracked_update(msg, links, subject, sent)


def _fictionlive_updates(msg: email.message.EmailMessage, links: list[tuple[str, str]], subject: str, sent: float) -> list[db.Update]:
    story_titles: dict[str, tuple[str, str]] = {}  # story_id -> (title, url)
    for href, text in links:
        m = FICTIONLIVE_STORY_RE.match(href)
        if m:
            url = f"https://fiction.live/stories/{m.group(1)}/{m.group(2)}"
            if m.group(2) not in story_titles or not story_titles[m.group(2)][0]:
                story_titles[m.group(2)] = (_label(text, ""), url)
    live = GONE_LIVE_RE.match(subject)
    author = next((m.group(1) for m in (FICTIONLIVE_USER_RE.match(href) for href, _ in links) if m), "")

    def story(story_id: str, slug: str) -> tuple[str, str]:
        title, url = story_titles.get(story_id, ("", f"https://fiction.live/stories/{slug}/{story_id}"))
        return title or (live.group(1).strip() if live else subject), url

    updates = []
    for href, text in links:
        m = FICTIONLIVE_CHAPTER_RE.match(href)
        if m:
            title, story_url = story(m.group(2), m.group(1))
            url = "https://" + href.split("://", 1)[1].split("?")[0].split("#")[0]
            updates.append(
                db.Update(
                    key=f"fictionlive:{m.group(2)}:{m.group(3)}",
                    site="fiction.live",
                    story_title=title,
                    story_url=story_url,
                    title=_label(text, "New chapter"),
                    url=url,
                    published=sent,
                    author=author,
                )
            )
    if not updates and story_titles:
        # e.g. "<story> has gone live": the email only links to the story.
        story_id = next(iter(story_titles))
        title, url = story(story_id, "")
        updates.append(
            db.Update(
                key=f"fictionlive-live:{msg.get('Message-ID') or f'{story_id}:{sent}'}",
                site="fiction.live",
                story_title=title,
                story_url=url,
                title="Went live" if live else "Update",
                url=url,
                published=sent,
                author=author,
            )
        )
    return updates


def _process(msg: email.message.EmailMessage) -> None:
    subject = str(msg.get("Subject", ""))
    sender = str(msg.get("From", "")).lower()
    sent = parsedate_to_datetime(msg["Date"]).timestamp() if msg["Date"] else time.time()
    links = _links(msg)

    if "archiveofourown.org" in sender:
        updates = _ao3_updates(links, subject, sent)
    elif "royalroad.com" in sender:
        updates = _royalroad_updates(msg, links, subject, sent)
    elif "fiction.live" in sender:
        updates = _fictionlive_updates(msg, links, subject, sent)
    else:
        return
    # The same chapter is often linked twice (title, then a "Read" button); keep the real title.
    merged: dict[str, db.Update] = {}
    for u in updates:
        if u.key not in merged or merged[u.key].title in PLACEHOLDER_TITLES:
            merged[u.key] = u
    db.save_updates(list(merged.values()))


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

        # No historical backfill: only emails sent after the first successful sync count,
        # even if older ones get the label later.
        since = float(db.get_state("email_since") or 0)
        if not since:
            since = time.time()
            db.set_state("email_since", str(since))
        since_day = time.strftime("%d-%b-%Y", time.gmtime(since - 86400))

        _, data = imap.uid("search", None, f"UID {last_uid + 1}:* SINCE {since_day}")
        # "N:*" always matches the newest message, even when it is older than N.
        uids = [int(u) for u in data[0].split() if int(u) > last_uid]
        for uid in sorted(uids):
            _, msg_data = imap.uid("fetch", str(uid), "(RFC822)")
            raw = next(part[1] for part in msg_data if isinstance(part, tuple))
            msg = email.message_from_bytes(raw, policy=policy.default)
            if msg["Date"] and parsedate_to_datetime(msg["Date"]).timestamp() >= since:
                _process(msg)
            db.set_state("imap_last_uid", str(uid))
    finally:
        try:
            imap.logout()
        except Exception:
            pass
