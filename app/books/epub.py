"""Turn an EPUB into the files described in store.py.

Chapter markup is rebuilt from scratch with a small whitelist of tags, so nothing from the
EPUB's own HTML (scripts, styles, attributes) reaches the reader page.
"""

import hashlib
import io
import os
import posixpath
import shutil
import time
import uuid
import zipfile
from html import escape
from urllib.parse import quote, unquote
from xml.etree import ElementTree

from bs4 import BeautifulSoup, NavigableString, Tag
from bs4.element import CData, Comment, Declaration, Doctype, ProcessingInstruction

from . import store

BLOCK = {
    "address", "article", "aside", "blockquote", "body", "center", "dd", "div", "dl", "dt", "figcaption",
    "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p",
    "pre", "section", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "ul",
}
SKIP = {"script", "style", "head", "title", "meta", "link", "noscript", "iframe", "object", "video", "audio", "form"}
INLINE = {
    "em": "em", "i": "em", "cite": "em", "dfn": "em", "var": "em", "strong": "strong", "b": "strong",
    "u": "u", "sup": "sup", "sub": "sub", "small": "small", "s": "s", "strike": "s", "del": "s",
    "code": "code", "tt": "code", "kbd": "code",
}
LEAF_TAG = {"h1": "h1", "h2": "h2", "h3": "h3", "h4": "h4", "h5": "h5", "h6": "h6", "blockquote": "blockquote", "pre": "pre"}
NOT_TEXT = (Comment, Declaration, Doctype, ProcessingInstruction, CData)


class EpubError(Exception):
    pass


def _xml(data: bytes) -> ElementTree.Element:
    """Parse XML and drop namespaces, which EPUBs use inconsistently."""
    root = ElementTree.fromstring(data)
    for el in root.iter():
        if isinstance(el.tag, str):
            el.tag = el.tag.rsplit("}", 1)[-1]
        el.attrib = {k.rsplit("}", 1)[-1]: v for k, v in el.attrib.items()}
    return root


def _resolve(base: str, href: str) -> tuple[str, str]:
    """Resolve an href relative to the file it appears in; returns (zip path, fragment)."""
    path, _, frag = href.partition("#")
    path = unquote(path)
    if not path:
        return base, frag
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), path)), frag


class _Chapter:
    def __init__(self, path: str, res_url):
        self.path = path
        self.res_url = res_url
        self.blocks: list[tuple[int | None, str]] = []  # (segment or None, markup with a {s} slot)
        self.texts: list[str] = []
        self.anchors: dict[str, int] = {}
        self.pending: list[str] = []  # ids seen since the last spoken block; they point at the next one

    def walk(self, el: Tag) -> None:
        self._note_ids(el)
        run: list = []
        for child in el.children:
            if isinstance(child, Tag) and child.name in SKIP:
                continue
            if isinstance(child, Tag) and child.name in BLOCK:
                self._emit("p", run)
                run = []
                if child.name == "hr":
                    self.blocks.append((None, "<hr>"))
                elif any(d.name in BLOCK for d in child.find_all(True)):
                    self.walk(child)
                else:
                    self._note_ids(child)
                    self._emit(LEAF_TAG.get(child.name, "p"), list(child.children))
            else:
                run.append(child)
        self._emit("p", run)

    def _note_ids(self, el: Tag) -> None:
        for attr in ("id", "name"):
            value = el.get(attr)
            if isinstance(value, str) and value:
                self.pending.append(value)

    def _emit(self, tag: str, nodes: list) -> None:
        parts = [self._inline(n) for n in nodes]
        html = "".join(p[0] for p in parts).strip()
        text = " ".join("".join(p[1] for p in parts).split())
        if text:
            index = len(self.texts)
            self.texts.append(text)
            for anchor in self.pending:
                self.anchors.setdefault(anchor, index)
            self.pending = []
            self.blocks.append((index, f'<{tag} data-s="{{s}}">{html.replace("{", "{{").replace("}", "}}")}</{tag}>'))
        elif any(p[2] for p in parts):
            self.blocks.append((None, f'<div class="fig">{html.replace("{", "{{").replace("}", "}}")}</div>'))

    def _inline(self, node) -> tuple[str, str, bool]:
        """Returns (markup, spoken text, has image)."""
        if isinstance(node, NavigableString):
            if isinstance(node, NOT_TEXT):
                return "", "", False
            return escape(str(node), quote=False), str(node), False
        if not isinstance(node, Tag) or node.name in SKIP:
            return "", "", False
        self._note_ids(node)
        if node.name == "br":
            return "<br>", " ", False
        if node.name in ("img", "image"):
            src = node.get("src") or node.get("xlink:href") or node.get("href")
            if not src:
                return "", "", False
            url = self.res_url(_resolve(self.path, src)[0])
            alt = node.get("alt", "")
            # A one- or two-letter alt is a drop cap drawn as an image; it's part of the first word.
            spoken = alt if 0 < len(alt.strip()) <= 2 else ""
            return f'<img src="{escape(url)}" alt="{escape(alt)}">', spoken, True
        parts = [self._inline(c) for c in node.children]
        html = "".join(p[0] for p in parts)
        tag = INLINE.get(node.name)
        if tag and html.strip():
            html = f"<{tag}>{html}</{tag}>"
        return html, "".join(p[1] for p in parts), any(p[2] for p in parts)


def _nav_toc(z: zipfile.ZipFile, path: str) -> list[dict]:
    soup = BeautifulSoup(z.read(path), "html.parser")
    nav = soup.find("nav", attrs={"epub:type": "toc"}) or soup.find("nav")
    entries = []

    def walk(ol: Tag, depth: int) -> None:
        for li in ol.find_all("li", recursive=False):
            link = li.find(["a", "span"], recursive=False)
            if link and link.get("href"):
                entries.append({"title": " ".join(link.get_text().split()), "target": _resolve(path, link["href"]), "depth": depth})
            child = li.find("ol", recursive=False)
            if child:
                walk(child, depth + 1)

    if nav and nav.find("ol"):
        walk(nav.find("ol"), 0)
    return entries


def _ncx_toc(z: zipfile.ZipFile, path: str) -> list[dict]:
    root = _xml(z.read(path))
    entries = []

    def walk(el: ElementTree.Element, depth: int) -> None:
        for point in el.findall("navPoint"):
            label = point.find("navLabel/text")
            content = point.find("content")
            if content is not None and content.get("src"):
                title = " ".join((label.text or "").split()) if label is not None else ""
                entries.append({"title": title, "target": _resolve(path, content.get("src")), "depth": depth})
            walk(point, depth + 1)

    nav_map = root.find("navMap")
    if nav_map is not None:
        walk(nav_map, 0)
    return entries


def _read(data: bytes, book_id: str, rev: int) -> tuple[dict, list[dict]]:
    """The book.json fields describing an EPUB's contents, and its sections' markup and text.
    Image links carry `rev`, so a book rebuilt by an update doesn't show cached images."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        container = _xml(z.read("META-INF/container.xml"))
        rootfile = container.find(".//rootfile")
        opf_path = rootfile.get("full-path")
        opf = _xml(z.read(opf_path))
    except (zipfile.BadZipFile, KeyError, AttributeError, ElementTree.ParseError) as e:
        raise EpubError("That doesn't look like a valid EPUB file.") from e

    metadata = opf.find("metadata")
    title = (metadata.findtext("title") or "").strip() if metadata is not None else ""
    authors = [c.text.strip() for c in metadata.findall("creator") if c.text] if metadata is not None else []

    manifest = {}
    for item in opf.iterfind("manifest/item"):
        manifest[item.get("id")] = {
            "path": _resolve(opf_path, item.get("href", ""))[0],
            "type": item.get("media-type", ""),
            "props": item.get("properties", "").split(),
        }
    spine = opf.find("spine")
    if spine is None:
        raise EpubError("The EPUB has no reading order (spine).")

    cover = next((m["path"] for m in manifest.values() if "cover-image" in m["props"]), None)
    if not cover and metadata is not None:
        cover_meta = next((m for m in metadata.iter("meta") if m.get("name") == "cover"), None)
        if cover_meta is not None and cover_meta.get("content") in manifest:
            cover = manifest[cover_meta.get("content")]["path"]
    images = {m["path"]: m["type"] for m in manifest.values() if m["type"].startswith("image/")}

    def res_url(path: str) -> str:
        return f"/books/api/{book_id}/res/{quote(path)}?v={rev}"

    chapters, chapter_of, anchors = [], {}, []
    for ref in spine.iterfind("itemref"):
        item = manifest.get(ref.get("idref"))
        if not item or "html" not in item["type"] or ref.get("linear") == "no":
            continue
        try:
            soup = BeautifulSoup(z.read(item["path"]), "html.parser")
        except KeyError:
            continue
        chapter = _Chapter(item["path"], res_url)
        chapter.walk(soup.body or soup)
        chapter_of[item["path"]] = len(chapters)  # sections with nothing in them point at the next chapter
        if not chapter.blocks:
            continue
        chapters.append(chapter)
        anchors.append(chapter.anchors)
    if not chapters:
        raise EpubError("Couldn't find any text in that EPUB.")

    nav = next((m["path"] for m in manifest.values() if "nav" in m["props"]), None)
    ncx = manifest.get(spine.get("toc") or "", {}).get("path")
    try:
        raw_toc = (_nav_toc(z, nav) if nav else []) or (_ncx_toc(z, ncx) if ncx else [])
    except (KeyError, ElementTree.ParseError):
        raw_toc = []
    toc = []
    for entry in raw_toc:
        path, frag = entry["target"]
        index = chapter_of.get(path)
        if index is None or index >= len(chapters):
            continue
        toc.append({
            "title": entry["title"] or f"Section {index + 1}",
            "chapter": index,
            "segment": anchors[index].get(frag, 0) if frag else 0,
            "depth": entry["depth"],
        })
    if not toc:
        toc = [{"title": f"Section {i + 1}", "chapter": i, "segment": 0, "depth": 0} for i in range(len(chapters))]

    # Many EPUBs put several chapters in one file. Split files at table-of-contents entries so
    # each section is a real chapter: narration, downloads and listening start per section.
    sections, starts_of = [], []
    for i, c in enumerate(chapters):
        starts = sorted({0} | {t["segment"] for t in toc if t["chapter"] == i and 0 < t["segment"] < len(c.texts)})
        starts_of.append([(start, len(sections) + k) for k, start in enumerate(starts)])
        parts = [{"blocks": [], "texts": c.texts[a:b], "start": a} for a, b in zip(starts, [*starts[1:], len(c.texts)])]
        waiting = []  # images and rules go with the next spoken block
        for seg, markup in c.blocks:
            if seg is None:
                waiting.append(markup)
                continue
            k = max(k for k, start in enumerate(starts) if start <= seg)
            part = parts[k]
            part["blocks"] += [m.format() for m in waiting] + [markup.format(s=seg - part["start"])]
            waiting = []
        parts[-1]["blocks"] += [m.format() for m in waiting]
        sections += parts
    for t in toc:
        start, index = max((p for p in starts_of[t["chapter"]] if p[0] <= t["segment"]), key=lambda p: p[0])
        t["chapter"], t["segment"] = index, t["segment"] - start

    def chapter_title(index: int) -> str:
        titles = [t["title"] for t in toc if t["chapter"] <= index]
        return titles[-1] if titles else title

    book = {
        "id": book_id,
        "title": title or "Untitled",
        "author": ", ".join(authors),
        "cover": cover if cover in images else None,
        "rev": rev,
        "chapters": [
            {"title": chapter_title(i), "segments": len(c["texts"]), "chars": sum(map(len, c["texts"]))}
            for i, c in enumerate(sections)
        ],
        "toc": toc,
        "images": images,
    }
    return book, sections


def save(data: bytes, owner: str, source: str = "") -> str:
    """Store an uploaded EPUB for `owner`; returns the book id. Uploading the same file twice is a no-op,
    and two people uploading the same file each get their own copy. `source` is the story link of a
    book the importer built, which lets it be updated later."""
    book_id = hashlib.sha256(owner.encode() + b"\0" + data).hexdigest()[:12]
    if store.book_dir(book_id):
        return book_id
    book, sections = _read(data, book_id, 0)
    book.update(owner=owner, added=time.time(), source=source)

    # Build in a hidden folder and rename, so the worker never sees a half-written book.
    store.BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = store.BOOKS_DIR / f".{book_id}"
    shutil.rmtree(tmp, ignore_errors=True)
    (tmp / "chapters").mkdir(parents=True)
    (tmp / "audio").mkdir()
    (tmp / "book.epub").write_bytes(data)
    for i, c in enumerate(sections):
        (tmp / "chapters" / f"{i}.html").write_text("\n".join(c["blocks"]))
        store.write_json(tmp / "chapters" / f"{i}.json", c["texts"])
    store.write_json(tmp / "book.json", book)
    tmp.rename(store.BOOKS_DIR / book_id)
    return book_id


def update(book_id: str, data: bytes) -> str | None:
    """Replace a book's contents with a newer EPUB of the same story, keeping its id, reading
    position and the narration of every section whose text didn't change (an update usually just
    adds chapters at the end). Returns None if the book is gone."""
    folder = store.book_dir(book_id)
    old = folder and store.read_json(folder / "book.json")
    if not old:
        return None
    book, sections = _read(data, book_id, old.get("rev", 0) + 1)
    book.update(owner=old["owner"], added=old["added"], source=old.get("source", ""), updated=time.time())

    # Sections are rewritten one file at a time; the worker notices the new rev in book.json and
    # drops narration it started on text that changed.
    chapters, audio = folder / "chapters", folder / "audio"

    def drop_audio(n: int) -> None:
        for path in (audio / f"{n}.json", audio / f"{n}.mp3", *store.partial_paths(folder, n)):
            path.unlink(missing_ok=True)

    for i, c in enumerate(sections):
        if store.read_json(chapters / f"{i}.json") != c["texts"]:
            drop_audio(i)
        store.write_text(chapters / f"{i}.html", "\n".join(c["blocks"]))
        store.write_json(chapters / f"{i}.json", c["texts"])
    for path in chapters.glob("*.json"):
        if path.stem.isdigit() and int(path.stem) >= len(sections):
            drop_audio(int(path.stem))
            path.unlink(missing_ok=True)
            path.with_suffix(".html").unlink(missing_ok=True)
    tmp = folder / ".book.epub.tmp"
    tmp.write_bytes(data)
    os.replace(tmp, folder / "book.epub")
    store.write_json(folder / "book.json", book)

    progress = store.read_json(folder / "progress.json")
    if progress and progress.get("chapter", 0) >= len(sections):
        store.write_json(folder / "progress.json", {**progress, "chapter": len(sections) - 1, "segment": 0})
    return book_id


def source_of(book: dict) -> str:
    """The story link of a book the importer built, or "" for an upload. Books imported before
    book.json recorded it get it from the EPUB, whose identifier the importer derives from the link."""
    if "source" in book:
        return book["source"]
    source = ""
    try:
        with zipfile.ZipFile(store.BOOKS_DIR / book["id"] / "book.epub") as z:
            opf = _xml(z.read("OEBPS/content.opf"))
        link = (opf.findtext("metadata/source") or "").strip()
        if link and opf.findtext("metadata/identifier") == f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, link)}":
            source = link
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError):
        pass
    path = store.BOOKS_DIR / book["id"] / "book.json"
    fresh = store.read_json(path)
    if fresh and "source" not in fresh:
        store.write_json(path, {**fresh, "source": source})
    book["source"] = source
    return source
