"""Build an EPUB from a story URL on Royal Road, SpaceBattles, Sufficient Velocity or
Questionable Questing, then add it to a reader's library like an upload.

Imports run one at a time on a background thread, a second apart per request, and only when a
reader asks for one. Nothing here retries past a Cloudflare challenge: a blocked request fails
the import with a message saying so. Royal Road and SpaceBattles block this server, so stories can
instead come through the "Import to Library" bookmarklet: the same parsers run here on pages the
reader's browser fetched, asking it for more until they have every page they need (see gather).
Jobs live in memory, so a restart drops unfinished ones.

Importing a story that's already in the reader's library updates that book instead: chapters it
already has are copied from its EPUB (each chapter records the link it came from), so only new
ones are downloaded.
"""

import hashlib
import io
import json
import logging
import math
import os
import queue
import re
import threading
import time
import uuid
import zipfile
from html import escape, unescape
from urllib.parse import unquote, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import Comment

from ..serials import http
from ..serials.sources import xenforo
from . import epub, store

log = logging.getLogger(__name__)

DELAY = 1.0  # seconds between requests to the story's site
MAX_IMAGES = 300
MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/webp": "webp", "image/svg+xml": "svg"}

FORUM_HOSTS = {
    "forums.spacebattles.com": "spacebattles",
    "forums.sufficientvelocity.com": "sufficientvelocity",
    "forum.questionablequesting.com": "questionablequesting",
    "questionablequesting.com": "questionablequesting",
}
RR_FICTION_RE = re.compile(r"^/fiction/(\d+)")
THREAD_RE = re.compile(r"/threads/(?:[^/]*\.)?(\d+)(?:/|$)")
POST_RE = re.compile(r"(?:/posts/|#post-|post-)(\d+)")
READER_POSTS_PER_PAGE = 10
BOOKMARKLET_SITES = {"Royal Road", "SpaceBattles", "Sufficient Velocity", "Questionable Questing"}
BOT_CHECK_RE = re.compile(r"<title>\s*(Just a moment|Making sure you(?:'|&#39;|’)re not a bot)", re.I)
# Sites that turn this server away, so updates go through the bookmarklet.
SERVER_BLOCKED = {"royalroad", "spacebattles"}


class ImportFailed(Exception):
    pass


# --- sites ---------------------------------------------------------------------------------

class _Fetcher:
    """Spaces requests out and turns blocks and missing pages into readable errors."""

    def __init__(self, site: str, client: httpx.Client):
        self.site = site
        self.client = client
        self.last = 0.0

    def blocked(self) -> ImportFailed:
        if self.site in BOOKMARKLET_SITES:
            return ImportFailed(
                f"{self.site} blocks downloads from this server. Open the story on {self.site} and use the "
                "Import to Library bookmark instead (see Add from link)."
            )
        return ImportFailed(
            f"{self.site} blocks automated downloads of that page. Save it with WebToEpub in your "
            "browser and add the EPUB with Add book instead."
        )

    def get(self, url: str, **kwargs) -> httpx.Response:
        time.sleep(max(0.0, self.last + DELAY - time.monotonic()))
        try:
            r = http.get(self.client, url, **kwargs)
            # Royal Road serves its bot check with a 200.
            if BOT_CHECK_RE.search(r.text[:2000]):
                raise self.blocked()
            return r
        except httpx.HTTPStatusError as e:
            r = e.response
            if r.headers.get("cf-mitigated") == "challenge" or BOT_CHECK_RE.search(r.text[:2000]):
                raise self.blocked() from e
            if r.status_code == 404:
                raise ImportFailed(f"{self.site} says that page doesn't exist.") from e
            if r.status_code == 403:
                raise ImportFailed(f"{self.site} refused the request (403).") from e
            raise ImportFailed(f"{self.site} returned an error ({r.status_code}).") from e
        except httpx.TransportError as e:
            raise ImportFailed(f"Couldn't reach {self.site}.") from e
        finally:
            self.last = time.monotonic()

    def soup(self, url: str, **kwargs) -> BeautifulSoup:
        return BeautifulSoup(self.get(url, **kwargs).text, "html.parser")

    def prefetch(self, urls: list[str]) -> None:
        """Pages about to be read; only matters to _Delivered, which asks for them in one go."""


def _page_key(url: str) -> str:
    u = httpx.URL(url)
    query = "&".join(sorted(f"{k}={v}" for k, v in u.params.multi_items()))
    return unquote(u.path).rstrip("/") + (f"?{query}" if query else "")


class _Need(Exception):
    def __init__(self, urls: list[str]):
        self.urls = urls


class _Delivered(_Fetcher):
    """Pages a reader's browser fetched, handed to the site parsers in place of requests. With
    `collect`, a missing page raises _Need so the browser can be asked for it."""

    def __init__(self, site: str, client: httpx.Client | None, pages: dict[str, str], collect: bool = False):
        super().__init__(site, client)
        self.pages = pages
        self.collect = collect

    def get(self, url: str, params: dict | None = None, **kwargs) -> httpx.Response:
        url = str(httpx.URL(url, params=params) if params else httpx.URL(url))
        text = self.pages.get(_page_key(url))
        if text is None:
            if self.collect:
                raise _Need([url])
            raise ImportFailed(f"The browser didn't send {_page_key(url)}. Try the bookmark again.")
        if BOT_CHECK_RE.search(text[:2000]):
            raise ImportFailed(f"{self.site} showed your browser a bot check. Reload the story there and try again.")
        return httpx.Response(200, text=text, request=httpx.Request("GET", url))

    def prefetch(self, urls: list[str]) -> None:
        missing = list(dict.fromkeys(u for u in urls if _page_key(u) not in self.pages))
        if missing and self.collect:
            raise _Need(missing)


def identify(url: str) -> tuple[str, str]:
    """(site key, canonical story URL) for a supported link, or ImportFailed."""
    url = url.strip()
    if not re.match(r"^https?://", url):
        url = "https://" + url
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if host in ("royalroad.com", "www.royalroad.com"):
        m = RR_FICTION_RE.match(parts.path)
        if not m:
            raise ImportFailed("Paste a link to a Royal Road fiction or one of its chapters.")
        return "royalroad", f"https://www.royalroad.com/fiction/{m.group(1)}"
    if host in FORUM_HOSTS:
        key = FORUM_HOSTS[host]
        base = xenforo.FORUMS[key][1]
        m = THREAD_RE.search(parts.path)
        if m:
            return key, f"{base}/threads/{m.group(1)}/"
        if POST_RE.search(parts.path + "#" + parts.fragment):
            return key, f"{base}{parts.path}"  # resolved to its thread when fetched
        raise ImportFailed("Paste a link to a forum thread.")
    raise ImportFailed("Only Royal Road, SpaceBattles, Sufficient Velocity and Questionable Questing links work.")


class _Previous:
    """The chapters of a book the importer built earlier, read back from its EPUB."""

    def __init__(self, path):
        self.zip = zipfile.ZipFile(path)
        names = set(self.zip.namelist())
        opf = self.zip.read("OEBPS/content.opf").decode()
        self.types = dict(re.findall(r'href="(images/[^"]+)" media-type="([^"]+)"', opf))
        cover = re.search(r'href="(images/[^"]+)" media-type="[^"]+" properties="cover-image"', opf)
        self.cover = cover and cover.group(1)
        self.chapters: list[tuple[str | None, str, str]] = []  # (link, title, XHTML body)
        while (name := f"OEBPS/text/{len(self.chapters)}.xhtml") in names:
            page = self.zip.read(name).decode()
            title = re.search(r"<title>(.*?)</title>", page, re.S)
            link = re.search(r'<meta name="source" content="([^"]*)"', page)
            body = page.split("<body>\n", 1)[-1].rsplit("\n</body>", 1)[0]
            body = re.sub(r"^<h2>.*?</h2>\n", "", body, count=1, flags=re.S)
            self.chapters.append((link and unescape(link.group(1)), unescape(title.group(1)) if title else "", body))
        self.by_link = {link: i for i, (link, _, _) in enumerate(self.chapters) if link}

    def find(self, i: int, link: str, title: str) -> int | None:
        """Which earlier chapter is the story's chapter i. Books imported before chapters recorded
        their links go by position and title."""
        if self.by_link:
            return self.by_link.get(link)
        return i if i < len(self.chapters) and self.chapters[i][1] == title else None

    def close(self) -> None:
        self.zip.close()


def _previous(book_id: str | None) -> _Previous | None:
    folder = book_id and store.book_dir(book_id)
    if not folder:
        return None
    try:
        return _Previous(folder / "book.epub")
    except (OSError, KeyError, zipfile.BadZipFile):
        return None


class Story:
    def __init__(self, client: httpx.Client | None, base: str, url: str, previous: _Previous | None = None):
        self.url = url  # canonical story link
        self.title = ""
        self.author = ""
        self.cover: str | None = None  # zip path of the cover image
        self.chapters: list[tuple[str, str, str]] = []  # (title, XHTML body, link)
        self.images = _Images(client, base)
        self.previous = previous
        self.reused = 0

    def convert(self, content: Tag) -> str:
        # Converted right away so a long story doesn't keep every parsed page in memory.
        return "".join(_xhtml(c, self.images) for c in content.children)

    def add(self, title: str, content: Tag, link: str) -> None:
        self.chapters.append((title, self.convert(content), link))

    def reuse(self, index: int, title: str, link: str) -> None:
        """Copy chapter `index` of the earlier book, with its images."""
        def image(m: re.Match) -> str:
            path = self.images.adopt(self.previous, m.group(1))
            return f'<img src="../{path}"{m.group(2)}/>' if path else ""

        body = re.sub(r'<img src="\.\./(images/[^"]+)"([^>]*?)/>', image, self.previous.chapters[index][2])
        self.chapters.append((title, body, link))
        self.reused += 1

    def unchanged(self) -> bool:
        """An update that found nothing new."""
        p = self.previous
        return bool(p) and self.reused == len(self.chapters) == len(p.chapters) and all(
            title == old[1] for (title, _, _), old in zip(self.chapters, p.chapters)
        )

    @property
    def new(self) -> int:
        return len(self.chapters) - self.reused


def _royalroad(f: _Fetcher, url: str, job: dict, previous: _Previous | None = None) -> Story:
    r = f.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    story = Story(f.client, str(r.url), url, previous)
    meta = {}
    if tag := soup.select_one('script[type="application/ld+json"]'):
        try:
            meta = json.loads(tag.string or "{}")
        except ValueError:
            pass
    meta = meta if isinstance(meta, dict) else {}

    def og(prop: str) -> str:
        tag = soup.find("meta", attrs={"property": prop})
        return tag.get("content", "") if tag else ""

    heading = soup.select_one(".fic-header h1") or soup.find("h1")
    story.title = meta.get("name") or (heading and heading.get_text(strip=True)) or og("og:title")
    story.author = (meta.get("author") or {}).get("name") or og("books:author")
    if previous and previous.cover:
        story.cover = story.images.adopt(previous, previous.cover)
    elif cover := meta.get("image") or og("og:image"):
        story.cover = story.images.add(cover)

    found = re.search(r"^\s*window\.chapters\s*=\s*(.*?)\s*;\s*$", r.text, flags=re.MULTILINE)
    try:
        listing = json.loads(found.group(1)) if found else []
    except ValueError:
        listing = []
    if not listing:
        raise ImportFailed("Couldn't find any chapters on that Royal Road page.")
    # isUnlocked reads false for every chapter when logged out; only chapters tied to a paid
    # subscription tier are actually locked.
    listing = [c for c in listing if not c.get("subscriptionTiers") and c.get("url")]
    if not listing:
        raise ImportFailed("Every chapter of that story is locked behind a paid subscription.")
    links = [urljoin(str(r.url), c["url"]) for c in listing]
    titles = [c.get("title") or f"Chapter {i + 1}" for i, c in enumerate(listing)]
    have = [previous.find(i, link, t) if previous else None for i, (link, t) in enumerate(zip(links, titles))]
    job["title"], job["total"] = story.title, have.count(None)

    f.prefetch([link for link, old in zip(links, have) if old is None])
    for c, link, title, old in zip(listing, links, titles, have):
        if old is not None:
            story.reuse(old, title, link)
            continue
        page = f.soup(link)
        content = page.select_one("div.chapter-inner.chapter-content") or page.select_one("div.chapter-content")
        if content is None:
            raise ImportFailed(f"Couldn't read the chapter “{c.get('title', '')}”.")
        # Royal Road hides decoy paragraphs with per-page classes set to display: none.
        hidden = set()
        for style in page.find_all("style"):
            hidden.update(re.findall(r"\.([\w-]+)\s*\{[^}]*display\s*:\s*none", style.get_text(), flags=re.I))
        for el in content.find_all(class_=lambda cls: cls in hidden):
            el.decompose()
        story.add(title, content, link)
        job["done"] = story.new
    return story


_forum_clients: dict[str, httpx.Client] = {}


def _xenforo(f: _Fetcher, key: str, url: str, job: dict, previous: _Previous | None = None) -> Story:
    name, base = xenforo.FORUMS[key]
    c = f.client
    r = f.get(url)
    soup = BeautifulSoup(r.text, "html.parser")
    if not soup.select("article.message--post") and 'data-logged-in="true"' not in r.text:
        # Some boards (QQ's especially) only show threads to members.
        if isinstance(f, _Delivered):
            raise ImportFailed(f"{name} only shows that thread to members. Log in there in this browser and try again.")
        username = os.environ.get(f"{key.upper()}_USERNAME")
        password = os.environ.get(f"{key.upper()}_PASSWORD")
        if not (username and password):
            raise ImportFailed(f"{name} wants you logged in to see that thread, and no account is set up for it.")
        try:
            xenforo.login(c, base, username, password)
        except (xenforo.LoginRejected, RuntimeError) as e:
            raise ImportFailed(f"Couldn't log in to {name}: {e}") from e
        r = f.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
    m = THREAD_RE.search(urlsplit(str(r.url)).path)
    if not m:
        raise ImportFailed(f"That doesn't look like a {name} thread.")
    thread = f"{base}/threads/{m.group(1)}"

    story = Story(c, str(r.url), f"{thread}/", previous)
    title = soup.select_one("h1.p-title-value")
    if title:
        for label in title.select(".label, .label-append"):
            label.decompose()
        story.title = title.get_text(" ", strip=True)
    starter = soup.select_one(".p-description a.username") or soup.select_one("article.message--post[data-author]")
    if starter:
        story.author = starter.get("data-author") or starter.get_text(strip=True)

    marks = _threadmarks(f, f"{thread}/threadmarks", {"threadmark_category": 1, "per_page": 200})
    if not marks:
        raise ImportFailed("That thread has no threadmarks, so there's no story to collect.")
    links = [f"{base}/posts/{post_id}/" for _, post_id in marks]
    have = [previous.find(i, link, t) if previous else None for i, (link, (t, _)) in enumerate(zip(links, marks))]
    wanted = {post_id for (_, post_id), old in zip(marks, have) if old is None}
    job["title"], job["total"] = story.title, len(wanted)

    # Reader mode lists threadmarked posts in order, ten to a page. Read the pages the missing
    # posts should be on first, then any others until they've all turned up.
    reader_pages = [
        str(httpx.URL(f"{thread}/reader/page-{page}", params={"threadmark_category": 1}))
        for page in range(1, math.ceil(len(marks) / READER_POSTS_PER_PAGE) + 1)
    ]
    likely = sorted({i // READER_POSTS_PER_PAGE for i, old in enumerate(have) if old is None})
    order = [reader_pages[i] for i in likely] + [p for i, p in enumerate(reader_pages) if i not in likely]
    bodies = {}
    f.prefetch(order[:len(likely)])
    for page in order:
        if not wanted:
            break
        reader = f.soup(page)
        for post in reader.select("article.message--post"):
            post_id = POST_RE.search(post.get("data-content", "") or post.get("id", ""))
            body = post.select_one("article.message-body .bbWrapper") or post.select_one(".bbWrapper")
            if post_id and body and post_id.group(1) in wanted:
                wanted.discard(post_id.group(1))
                bodies[post_id.group(1)] = story.convert(body)
        job["done"] = len(bodies)
    for (mark_title, post_id), link, old in zip(marks, links, have):
        if old is not None:
            story.reuse(old, mark_title, link)
        elif post_id in bodies:
            story.chapters.append((mark_title, bodies[post_id], link))
    if not story.new and not story.reused:
        raise ImportFailed(f"Couldn't read the threadmarked posts on {name}.")
    return story


def _threadmarks(f: _Fetcher, url: str, params: dict | None = None, seen: set | None = None) -> list[tuple[str, str]]:
    """(title, post id) for each main-story threadmark, following pages and the "…" ranges
    that long listings collapse."""
    seen = seen if seen is not None else set()
    key = url + json.dumps(params, sort_keys=True)
    if key in seen:
        return []
    seen.add(key)
    soup = f.soup(url, params=params)
    marks = []
    items = soup.select("div.structItem--threadmark")
    later = []
    if params is not None:  # only the first page links to the rest
        pages = soup.select("ul.pageNav-main li.pageNav-page a")
        last = re.match(r"^(?P<prefix>.*[?&]page=)(?P<last>\d+)", pages[-1].get("href", "")) if pages else None
        if last:
            later = [urljoin(url, last["prefix"] + str(n)) for n in range(2, int(last["last"]) + 1)]
    f.prefetch([
        urljoin(url, fetcher["data-fetchurl"])
        for item in items if (fetcher := item.find(attrs={"data-xf-click": "threadmark-fetcher"}))
    ] + later)
    for item in items:
        link = item.find("a", attrs={"data-tp-primary": "on"})
        if link and (post := POST_RE.search(link.get("href", ""))):
            marks.append((link.get_text(" ", strip=True), post.group(1)))
        elif fetcher := item.find(attrs={"data-xf-click": "threadmark-fetcher"}):
            marks += _threadmarks(f, urljoin(url, fetcher["data-fetchurl"]), None, seen)
    for page in later:
        marks += _threadmarks(f, page, None, seen)
    deduped, ids = [], set()
    for mark in marks:
        if mark[1] not in ids:
            ids.add(mark[1])
            deduped.append(mark)
    return deduped


def _site_name(site: str) -> str:
    return "Royal Road" if site == "royalroad" else xenforo.FORUMS[site][0]


def _parse(site: str, url: str, f: _Fetcher, job: dict, previous: _Previous | None = None) -> Story:
    return _royalroad(f, url, job, previous) if site == "royalroad" else _xenforo(f, site, url, job, previous)


# --- EPUB ----------------------------------------------------------------------------------

KEEP = {
    "p", "br", "hr", "em", "strong", "u", "s", "sup", "sub", "small", "code", "pre", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "table", "thead", "tbody", "tfoot", "tr",
    "td", "th", "div", "img",
}
RENAME = {"i": "em", "cite": "em", "b": "strong", "strike": "s", "del": "s", "tt": "code", "section": "div", "article": "div"}
DROP = {"script", "style", "noscript", "iframe", "object", "video", "audio", "form", "button", "svg", "head", "title"}
VOID = {"br", "hr", "img"}
# XenForo chrome inside post bodies: "Click to expand…" on quotes and the like.
DROP_CLASSES = {"bbCodeBlock-expandLink", "bbCodeBlock-shrinkLink", "bbCodeBlock-expandContent--hide"}


class _Images:
    def __init__(self, client: httpx.Client | None, base: str):
        self.client = client
        self.base = base
        self.files: dict[str, tuple[str, bytes, str]] = {}  # url -> (zip path, data, media type)
        self.failed: set[str] = set()

    def add(self, src: str) -> str | None:
        if self.client is None:  # gathering pages from the browser; images come at build time
            return None
        url = urljoin(self.base, src)
        if not url.startswith(("http://", "https://")) or url in self.failed:
            return None
        if url in self.files:
            return self.files[url][0]
        if len(self.files) >= MAX_IMAGES:
            return None
        try:
            r = self.client.get(url)
            r.raise_for_status()
        except httpx.HTTPError:
            self.failed.add(url)
            return None
        media_type = r.headers.get("content-type", "").split(";")[0].strip().lower()
        if media_type not in IMAGE_TYPES or len(r.content) > MAX_IMAGE_BYTES:
            self.failed.add(url)
            return None
        path = f"images/{len(self.files)}.{IMAGE_TYPES[media_type]}"
        self.files[url] = (path, r.content, media_type)
        return path

    def adopt(self, previous: "_Previous", old_path: str) -> str | None:
        """An image of the earlier book, copied in without downloading it again."""
        key = f"previous:{old_path}"
        if key in self.files:
            return self.files[key][0]
        media_type = previous.types.get(old_path)
        if media_type not in IMAGE_TYPES or len(self.files) >= MAX_IMAGES:
            return None
        try:
            data = previous.zip.read(f"OEBPS/{old_path}")
        except KeyError:
            return None
        path = f"images/{len(self.files)}.{IMAGE_TYPES[media_type]}"
        self.files[key] = (path, data, media_type)
        return path


def _xhtml(node, images: _Images) -> str:
    """Well-formed XHTML from a page fragment, keeping only plain formatting tags."""
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return escape(str(node), quote=False)
    if not isinstance(node, Tag) or node.name in DROP or DROP_CLASSES & set(node.get("class") or []):
        return ""
    if node.name == "img":
        if "smilie" in (node.get("class") or []):  # forum emoji
            return escape(node.get("alt", ""), quote=False)
        src = node.get("data-src") or node.get("data-url") or node.get("src") or ""
        path = images.add(src) if src and not src.startswith("data:") else None
        alt = escape(node.get("alt", ""))
        # How the site sized or floated it, for the reader (see epub._Styles).
        size = "".join(f' {a}="{v}"' for a in ("width", "height") if (v := node.get(a, "")).isdigit())
        style = ";".join(f"{k}:{v}" for k, v in epub._declarations(node.get("style") or "").items() if epub._length(v) or k == "float")
        size += f' style="{escape(style)}"' if style else ""
        return f'<img src="../{path}" alt="{alt}"{size}/>' if path else ""
    inner = "".join(_xhtml(c, images) for c in node.children)
    name = RENAME.get(node.name, node.name)
    if name in VOID:
        return f"<{name}/>"
    if name not in KEEP:
        return inner
    return f"<{name}>{inner}</{name}>"


def _page(title: str, body: str, link: str = "") -> str:
    # The link a chapter came from lets an update tell which chapters it already has.
    meta = f'<meta name="source" content="{escape(link)}"/>' if link else ""
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
        f"<head><title>{escape(title)}</title>{meta}</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def build_epub(story: Story) -> bytes:
    images, cover, source = story.images, story.cover, story.url
    chapters = []
    for n, (title, body, link) in enumerate(story.chapters):
        chapters.append((f"text/{n}.xhtml", title, _page(title, f"<h2>{escape(title)}</h2>\n{body}", link)))

    book_id = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, source))
    nav = _page("Contents", '<nav epub:type="toc" id="toc"><h1>Contents</h1><ol>' + "".join(
        f'<li><a href="{path}">{escape(title)}</a></li>' for path, title, _ in chapters
    ) + "</ol></nav>")
    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>']
    manifest += [f'<item id="c{n}" href="{path}" media-type="application/xhtml+xml"/>' for n, (path, _, _) in enumerate(chapters)]
    for n, (path, _, media_type) in enumerate(images.files.values()):
        props = ' properties="cover-image"' if path == cover else ""
        manifest.append(f'<item id="i{n}" href="{path}" media-type="{media_type}"{props}/>')
    spine = "".join(f'<itemref idref="c{n}"/>' for n in range(len(chapters)))
    # A fixed timestamp keeps the file identical when nothing changed, so re-importing an
    # unchanged story doesn't add a second copy (books are identified by a hash of the file).
    modified = "2000-01-01T00:00:00Z"
    opf = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="id">{escape(book_id)}</dc:identifier>
    <dc:title>{escape(story.title or "Untitled")}</dc:title>
    {f"<dc:creator>{escape(story.author)}</dc:creator>" if story.author else ""}
    <dc:language>en</dc:language>
    <dc:source>{escape(source)}</dc:source>
    <meta property="dcterms:modified">{modified}</meta>
  </metadata>
  <manifest>
    {chr(10).join(manifest)}
  </manifest>
  <spine>{spine}</spine>
</package>
"""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        def put(name: str, data: str | bytes, compress=zipfile.ZIP_DEFLATED):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = compress
            z.writestr(info, data)

        put("mimetype", "application/epub+zip", zipfile.ZIP_STORED)
        put("META-INF/container.xml", (
            '<?xml version="1.0"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'
        ))
        put("OEBPS/content.opf", opf)
        put("OEBPS/nav.xhtml", nav)
        for path, _, page in chapters:
            put(f"OEBPS/{path}", page)
        for path, data, _ in images.files.values():
            put(f"OEBPS/{path}", data, zipfile.ZIP_STORED)
    return out.getvalue()


# --- jobs ----------------------------------------------------------------------------------

_jobs: dict[str, dict] = {}
_queue: queue.Queue = queue.Queue()
_lock = threading.Lock()
_thread: threading.Thread | None = None
FINISHED_KEEP = 600  # seconds a finished or failed import stays listed


_pages: dict[str, dict[str, str]] = {}  # job id -> pages from the bookmarklet, until it runs
_sessions: dict[str, dict] = {}  # bookmarklet imports still gathering pages
SESSION_KEEP = 1800
MAX_PAGES = 5000
MAX_GATHER_BYTES = 300 * 1024 * 1024


def start(url: str, owner: str) -> dict:
    return _enqueue(*identify(url), owner)


def update(book: dict) -> dict:
    """Check an imported book's story for new chapters."""
    return _enqueue(*identify(epub.source_of(book)), book["owner"], target=book["id"])


def update_route(source: str) -> str | None:
    """How an imported book gets its new chapters: "server" fetches them here, "browser" means
    through the bookmarklet on the story's page. None for a book that wasn't imported."""
    try:
        site, _ = identify(source) if source else (None, None)
    except ImportFailed:
        return None
    return site and ("browser" if site in SERVER_BLOCKED else "server")


def _existing(owner: str, canonical: str) -> str | None:
    """The reader's book of this story, if they've imported it before."""
    return next((b["id"] for b in store.list_books(owner) if epub.source_of(b) == canonical), None)


def gather(owner: str, url: str | None = None, session: str | None = None, pages=None) -> dict:
    """One round of a bookmarklet import. The site parser runs on the pages the reader's browser
    has sent so far; returns {"session", "need": [urls]} while it wants more, then queues the
    import and returns {"id"} of the job."""
    if pages is None:
        pages = {}
    if not isinstance(pages, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in pages.items()):
        raise ImportFailed("The bookmark sent something unexpected. Try it again.")
    now = time.time()
    with _lock:
        for sid in [k for k, v in _sessions.items() if now - v["updated"] > SESSION_KEEP]:
            del _sessions[sid]
        if session:
            s = _sessions.get(str(session))
            if not s or s["owner"] != owner:
                raise ImportFailed("That import timed out. Start it again from the bookmark.")
        else:
            site, canonical = identify(str(url or ""))
            session = uuid.uuid4().hex
            s = _sessions[session] = {
                "owner": owner, "site": site, "url": canonical, "pages": {}, "size": 0,
                "target": _existing(owner, canonical),
            }
        s["updated"] = now
        for k, v in pages.items():
            s["pages"][_page_key(k)] = v
            s["size"] += len(v)
        if len(s["pages"]) > MAX_PAGES or s["size"] > MAX_GATHER_BYTES:
            del _sessions[session]
            raise ImportFailed("That story is too long to import this way.")
    previous = _previous(s["target"])
    try:
        _parse(s["site"], s["url"], _Delivered(_site_name(s["site"]), None, s["pages"], collect=True), {}, previous)
    except _Need as e:
        return {"session": session, "need": e.urls}
    except ImportFailed:
        with _lock:
            _sessions.pop(session, None)
        raise
    finally:
        if previous:
            previous.close()
    with _lock:
        _sessions.pop(session, None)
    return {"id": _enqueue(s["site"], s["url"], owner, s["pages"], s["target"])["id"]}


def _enqueue(site: str, canonical: str, owner: str, pages: dict[str, str] | None = None, target: str | None = None) -> dict:
    global _thread
    if target is None and pages is None:
        target = _existing(owner, canonical)
    with _lock:
        for job in _jobs.values():
            if job["owner"] == owner and job["url"] == canonical and job["status"] in ("queued", "running"):
                return job
        job = {
            "id": hashlib.sha256(f"{owner}\0{canonical}\0{time.time()}".encode()).hexdigest()[:12],
            "owner": owner, "site": site, "url": canonical, "title": "", "status": "queued",
            "done": 0, "total": 0, "error": "", "book": None, "updated": time.time(),
            "target": target, "update": bool(target), "new": 0,
        }
        _jobs[job["id"]] = job
        if pages is not None:
            _pages[job["id"]] = pages
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_run, name="book-import", daemon=True)
            _thread.start()
    _queue.put(job["id"])
    return job


def jobs_for(owner: str) -> list[dict]:
    now = time.time()
    with _lock:
        for job_id in [j["id"] for j in _jobs.values() if j["status"] in ("done", "error") and now - j["updated"] > FINISHED_KEEP]:
            del _jobs[job_id]
        return [dict(j) for j in _jobs.values() if j["owner"] == owner]


def dismiss(job_id: str, owner: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job and job["owner"] == owner and job["status"] in ("done", "error"):
            del _jobs[job_id]


def _run() -> None:
    while True:
        job = _jobs.get(_queue.get())
        if not job:
            continue
        job["status"], job["updated"] = "running", time.time()
        pages = _pages.pop(job["id"], None)
        previous = _previous(job["target"])
        own_client = None
        try:
            if pages is not None:
                f = own_client = _Delivered(_site_name(job["site"]), http.client(), pages)
            elif job["site"] == "royalroad":
                f = own_client = _Fetcher("Royal Road", http.client())
            else:
                # Kept between imports so a forum login lasts; images may be members-only attachments.
                client = _forum_clients.get(job["site"]) or _forum_clients.setdefault(job["site"], http.client())
                f = _Fetcher(xenforo.FORUMS[job["site"]][0], client)
            story = _parse(job["site"], job["url"], f, job, previous)
            job["title"], job["new"] = story.title, story.new
            if story.unchanged():
                job["book"] = job["target"]
            else:
                data = build_epub(story)
                job["book"] = (job["target"] and epub.update(job["target"], data)) or epub.save(data, job["owner"], story.url)
            job["status"] = "done"
        except ImportFailed as e:
            job["status"], job["error"] = "error", str(e)
        except epub.EpubError as e:
            job["status"], job["error"] = "error", str(e)
        except Exception:
            log.exception("import of %s failed", job["url"])
            job["status"], job["error"] = "error", "Something went wrong building the book."
        finally:
            if own_client:
                own_client.client.close()
            if previous:
                previous.close()
        job["updated"] = time.time()
