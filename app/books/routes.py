import json
import re
import shutil
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse

from .. import auth
from . import epub, importer, pages, store

MAX_UPLOAD = 200 * 1024 * 1024
# Chapter text, images and audio never change for a given book id and rev (the pages ask with
# ?v=<rev>; an update bumps it), so browsers may keep them.
IMMUTABLE = {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "private, max-age=604800"}

# Each reader picks a username, with no password, and sees only the books uploaded under it.
# Anyone can type any name, so signing the cookie would add nothing.
USER_COOKIE = "books_user"
USERNAME_RE = re.compile(r"^[a-z0-9_-]{1,32}$")

router = APIRouter(prefix="/books", include_in_schema=False)


def current_user(request: Request) -> str | None:
    name = request.cookies.get(USER_COOKIE, "")
    return name if USERNAME_RE.match(name) else None


def require_user(request: Request) -> str:
    """Dependency for the API routes."""
    user = current_user(request)
    if not user:
        raise HTTPException(401, "Not signed in")
    return user


api = APIRouter(prefix="/api", dependencies=[Depends(require_user)], include_in_schema=False)


def _login(path: str, failed: bool = False) -> HTMLResponse:
    return HTMLResponse(pages.login(path, failed), status_code=401, headers=auth.PRIVATE_HEADERS)


def _safe_next(path: str) -> str:
    return path if path.startswith("/books") and not path.startswith("//") else "/books"


@router.post("/login")
async def login(request: Request):
    form = parse_qs((await request.body()).decode())
    name = form.get("username", [""])[0].strip().lower()
    next_path = _safe_next(form.get("next", ["/books"])[0])
    if not USERNAME_RE.match(name):
        return _login(next_path, failed=True)
    response = RedirectResponse(next_path, status_code=303)
    response.set_cookie(
        USER_COOKIE, name, max_age=auth.MAX_AGE, path="/books", secure=True, httponly=True, samesite="lax"
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/books", status_code=303)
    response.delete_cookie(USER_COOKIE, path="/books", secure=True, httponly=True, samesite="lax")
    return response


@router.get("")
def library(request: Request):
    user = current_user(request)
    if not user:
        return _login("/books")
    return HTMLResponse(pages.library(user), headers=auth.PRIVATE_HEADERS)


@router.get("/receive")
def receive(request: Request):
    """Opened by the bookmarklet on a Royal Road page; takes the pages it fetched."""
    user = current_user(request)
    if not user:
        return _login("/books/receive")
    return HTMLResponse(pages.receive(user), headers=auth.PRIVATE_HEADERS)


SW_SOURCE = (Path(__file__).parent.parent / "static" / "books" / "sw.js").read_text()


@router.get("/sw.js")
def service_worker():
    """Offline reading. Served here rather than under /static so it can look after /books."""
    script = SW_SOURCE.replace("__VERSION__", str(pages.ASSET_VERSION)).replace("__SHELL__", json.dumps(pages.SHELL))
    return Response(script, media_type="text/javascript", headers={"Service-Worker-Allowed": "/books", **auth.PRIVATE_HEADERS})


@router.get("/read/{book_id}")
def reader(request: Request, book_id: str):
    user = current_user(request)
    if not user:
        return _login(f"/books/read/{book_id}")
    book, _ = _book(book_id, user)
    return HTMLResponse(pages.reader(book, request.cookies.get("reader_theme", "")), headers=auth.PRIVATE_HEADERS)


def _book(book_id: str, user: str) -> tuple[dict, Path]:
    """A book belonging to `user`; anyone else's is reported as missing."""
    folder = store.book_dir(book_id)
    book = folder and store.read_json(folder / "book.json")
    if not book or book.get("owner") != user:
        raise HTTPException(404, "No such book")
    return book, folder


def _audio_status(book: dict) -> dict:
    working = store.read_json(store.WORKER) or {}
    if working.get("book") != book["id"] or time.time() - working.get("updated", 0) > 120:
        working = None
    done = store.audio_done(book["id"])
    # Progress by amount of text, since sections range from a title page to a whole novella.
    folder = store.BOOKS_DIR / book["id"]
    narrated = 0.0
    for n, chapter in enumerate(book["chapters"]):
        if n in done:
            narrated += chapter["chars"]
        elif partial := store.read_json(store.partial_paths(folder, n)[1]):
            narrated += chapter["chars"] * len(partial["starts"]) / max(1, chapter["segments"])
    total = sum(c["chars"] for c in book["chapters"]) or 1
    return {
        "ready": sorted(done),
        "total": len(book["chapters"]),
        "percent": 100 if len(done) == len(book["chapters"]) else min(99, int(narrated / total * 100)),
        "working": working,
        "requested": store.narration_requested(book["id"]),
    }


def _res_url(book: dict, path: str) -> str:
    return f"/books/api/{book['id']}/res/{quote(path)}?v={book.get('rev', 0)}"


def _filename(title: str, ext: str) -> str:
    ascii_name = re.sub(r"[^A-Za-z0-9 ._-]+", "", title).strip()[:80] or "book"
    return f"attachment; filename=\"{ascii_name}.{ext}\"; filename*=UTF-8''{quote(title[:80])}.{ext}"


@api.get("/library")
def library_data(user: str = Depends(require_user)):
    books = []
    for book in store.list_books(user):
        progress = store.read_json(store.BOOKS_DIR / book["id"] / "progress.json", {})
        source = epub.source_of(book)
        books.append({
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "cover": book["cover"] and _res_url(book, book["cover"]),
            "rev": book.get("rev", 0),
            "source": source,
            "update": importer.update_route(source),
            "percent": progress.get("percent", 0),
            "opened": progress.get("updated", 0),
            "added": book["added"],
            "audio": _audio_status(book),
        })
    return JSONResponse(books, headers=auth.PRIVATE_HEADERS)


@api.post("/upload")
async def upload(request: Request, user: str = Depends(require_user)):
    data = await request.body()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "That file is too large.")
    try:
        book_id = await run_in_threadpool(epub.save, data, user)
    except epub.EpubError as e:
        raise HTTPException(400, str(e))
    return {"id": book_id}


@api.post("/import")
async def import_url(request: Request, user: str = Depends(require_user)):
    """Start building a book from a Royal Road or forum story link."""
    url = str((await request.json()).get("url", ""))
    try:
        job = importer.start(url, user)
    except importer.ImportFailed as e:
        raise HTTPException(400, str(e))
    return {"id": job["id"]}


@api.post("/import-pages")
async def import_pages(request: Request, user: str = Depends(require_user)):
    """One round of a bookmarklet import: story pages the reader's browser fetched go in, and either
    the pages still needed or the queued job's id come back."""
    body = await request.body()
    if len(body) > MAX_UPLOAD:
        raise HTTPException(413, "That story is too large.")
    try:
        data = json.loads(body)
        return await run_in_threadpool(importer.gather, user, data.get("url"), data.get("session"), data.get("pages"))
    except (ValueError, AttributeError):
        raise HTTPException(400, "The bookmark sent something unexpected. Try it again.")
    except importer.ImportFailed as e:
        raise HTTPException(400, str(e))


@api.get("/imports")
def imports(user: str = Depends(require_user)):
    return JSONResponse(importer.jobs_for(user), headers=auth.PRIVATE_HEADERS)


@api.delete("/imports/{job_id}")
def dismiss_import(job_id: str, user: str = Depends(require_user)):
    importer.dismiss(job_id, user)
    return {"ok": True}


@api.get("/{book_id}")
def book_data(book_id: str, user: str = Depends(require_user)):
    book, folder = _book(book_id, user)
    book = {k: v for k, v in book.items() if k != "images"}
    book["cover"] = book["cover"] and _res_url(book, book["cover"])
    book["rev"] = book.get("rev", 0)
    book["progress"] = store.read_json(folder / "progress.json")
    book["audio"] = _audio_status(book)
    return JSONResponse(book, headers=auth.PRIVATE_HEADERS)


@api.delete("/{book_id}")
def delete(book_id: str, user: str = Depends(require_user)):
    _, folder = _book(book_id, user)
    shutil.rmtree(folder)
    return {"ok": True}


@api.post("/{book_id}/update")
def update(book_id: str, user: str = Depends(require_user)):
    """Check an imported book's story for new chapters, on sites that let this server in."""
    book, _ = _book(book_id, user)
    route = importer.update_route(epub.source_of(book))
    if route is None:
        raise HTTPException(400, "Only books imported from a story link can be updated.")
    if route == "browser":
        raise HTTPException(400, "Use the Import to Library bookmark on the story's page to update this book.")
    try:
        job = importer.update(book)
    except importer.ImportFailed as e:
        raise HTTPException(400, str(e))
    return {"id": job["id"]}


@api.get("/{book_id}/chapter/{n}")
def chapter(book_id: str, n: int, user: str = Depends(require_user)):
    _, folder = _book(book_id, user)
    path = folder / "chapters" / f"{n}.html"
    if not path.exists():
        raise HTTPException(404)
    return HTMLResponse(path.read_text(), headers=IMMUTABLE)


@api.get("/{book_id}/res/{path:path}")
def resource(book_id: str, path: str, user: str = Depends(require_user)):
    book, folder = _book(book_id, user)
    media_type = book["images"].get(path)
    if not media_type:
        raise HTTPException(404)
    with zipfile.ZipFile(folder / "book.epub") as z:
        return Response(z.read(path), media_type=media_type, headers=IMMUTABLE)


@api.get("/{book_id}/audio/{n}.json")
def audio_timing(book_id: str, n: int, user: str = Depends(require_user)):
    _, folder = _book(book_id, user)
    timing = store.read_json(folder / "audio" / f"{n}.json")
    if timing is not None:
        return JSONResponse(timing, headers=IMMUTABLE)
    partial = store.read_json(store.partial_paths(folder, n)[1])
    if not partial or not partial["starts"]:
        raise HTTPException(404, "Not generated yet")
    return JSONResponse({**partial, "complete": False}, headers=auth.PRIVATE_HEADERS)


@api.get("/{book_id}/audio/{n}.mp3")
def audio(book_id: str, n: int, request: Request, user: str = Depends(require_user)):
    _, folder = _book(book_id, user)
    path = folder / "audio" / f"{n}.mp3"
    if (folder / "audio" / f"{n}.json").exists() and path.exists():
        return FileResponse(path, media_type="audio/mpeg", headers=IMMUTABLE)
    tmp, partial = store.partial_paths(folder, n)
    length = (store.read_json(partial) or {}).get("bytes", 0)
    try:
        return _byte_range(tmp, length, request.headers.get("range"))
    except FileNotFoundError:  # finished between the checks above; serve the final file
        if not path.exists():
            raise HTTPException(404)
        return FileResponse(path, media_type="audio/mpeg", headers=IMMUTABLE)


def _byte_range(path: Path, length: int, header: str | None) -> Response:
    """Serve the first `length` bytes of a file that's still being written, honoring Range
    requests (Safari won't play audio without them)."""
    if length <= 0:
        raise HTTPException(404)
    start, end, status = 0, length - 1, 200
    if header and header.startswith("bytes="):
        first, _, last = header[6:].split(",")[0].strip().partition("-")
        if first:
            start, end = int(first), min(int(last) if last else length - 1, length - 1)
        else:
            start = max(0, length - int(last))
        if start > end:
            return Response(status_code=416, headers={"Content-Range": f"bytes */{length}"})
        status = 206
    with path.open("rb") as f:
        f.seek(start)
        data = f.read(end - start + 1)
    headers = {"Accept-Ranges": "bytes", **auth.PRIVATE_HEADERS}
    if status == 206:
        headers["Content-Range"] = f"bytes {start}-{end}/{length}"
    return Response(data, status_code=status, media_type="audio/mpeg", headers=headers)


@api.get("/{book_id}/audio-status")
def audio_status(book_id: str, user: str = Depends(require_user)):
    book, _ = _book(book_id, user)
    return JSONResponse(_audio_status(book), headers=auth.PRIVATE_HEADERS)


@api.post("/{book_id}/listen")
async def listen(book_id: str, request: Request, user: str = Depends(require_user)):
    """Ask the worker to narrate this chapter next (and so the book: pressing listen asks for it)."""
    _, folder = _book(book_id, user)
    chapter = int((await request.json()).get("chapter", 0))
    (folder / store.NARRATE).touch()
    store.write_json(store.PRIORITY, {"book": book_id, "chapter": chapter})
    return {"ok": True}


@api.post("/{book_id}/narrate")
async def narrate(book_id: str, request: Request, user: str = Depends(require_user)):
    """Start or stop making the audiobook; stopping keeps what's been narrated."""
    book, folder = _book(book_id, user)
    if (await request.json()).get("on", True):
        (folder / store.NARRATE).touch()
    else:
        (folder / store.NARRATE).unlink(missing_ok=True)
    return JSONResponse(_audio_status(book), headers=auth.PRIVATE_HEADERS)


@api.post("/{book_id}/progress")
async def progress(book_id: str, request: Request, user: str = Depends(require_user)):
    _, folder = _book(book_id, user)
    body = json.loads(await request.body() or b"{}")
    # A place saved while offline is sent later with when it was saved ("at"), and doesn't
    # replace one saved since on another device.
    updated = time.time()
    if body.get("at"):
        updated = min(updated, float(body["at"]))
        if updated < store.read_json(folder / "progress.json", {}).get("updated", 0):
            return {"ok": True, "kept": "newer"}
    store.write_json(folder / "progress.json", {
        "chapter": int(body.get("chapter", 0)),
        "segment": int(body.get("segment", 0)),
        "percent": max(0.0, min(100.0, float(body.get("percent", 0)))),
        "updated": updated,
    })
    return {"ok": True}


@api.get("/{book_id}/search")
def search(book_id: str, q: str, user: str = Depends(require_user)):
    book, folder = _book(book_id, user)
    needle = q.strip().lower()
    results = []
    if len(needle) >= 2:
        for n in range(len(book["chapters"])):
            for s, text in enumerate(store.read_json(folder / "chapters" / f"{n}.json", [])):
                at = text.lower().find(needle)
                if at < 0:
                    continue
                start = max(0, at - 60)
                results.append({
                    "chapter": n,
                    "segment": s,
                    "title": book["chapters"][n]["title"],
                    "before": ("…" if start else "") + text[start:at],
                    "match": text[at:at + len(needle)],
                    "after": text[at + len(needle):at + len(needle) + 80] + ("…" if at + len(needle) + 80 < len(text) else ""),
                })
                if len(results) >= 200:
                    return JSONResponse(results, headers=auth.PRIVATE_HEADERS)
    return JSONResponse(results, headers=auth.PRIVATE_HEADERS)


@api.get("/{book_id}/download.epub")
def download_epub(book_id: str, user: str = Depends(require_user)):
    book, folder = _book(book_id, user)
    return FileResponse(
        folder / "book.epub", media_type="application/epub+zip",
        headers={"Content-Disposition": _filename(book["title"], "epub"), **auth.PRIVATE_HEADERS},
    )


def _audio_parts(book_id: str, folder: Path, numbers) -> list[tuple[int, object, int]]:
    """(chapter, open file, length) for each chapter with any narration, including whatever of an
    unfinished chapter is narrated so far. Everything is opened now: an unfinished chapter's file
    gets renamed when it completes."""
    done = store.audio_done(book_id)
    parts = []
    for n in numbers:
        try:
            if n in done:
                path = folder / "audio" / f"{n}.mp3"
                parts.append((n, path.open("rb"), path.stat().st_size))
            else:
                tmp, partial = store.partial_paths(folder, n)
                length = (store.read_json(partial) or {}).get("bytes", 0)
                if length:
                    parts.append((n, tmp.open("rb"), length))
        except FileNotFoundError:
            continue
    if not parts:
        raise HTTPException(404, "No audio yet")
    return parts


def _copy(fh, length: int):
    with fh:
        while length > 0 and (chunk := fh.read(min(1 << 20, length))):
            length -= len(chunk)
            yield chunk


@api.get("/{book_id}/download.mp3")
def download_mp3(book_id: str, chapter: int | None = None, user: str = Depends(require_user)):
    """The whole audiobook as one file, or a single chapter."""
    book, folder = _book(book_id, user)
    numbers = [chapter] if chapter is not None else range(len(book["chapters"]))
    parts = _audio_parts(book_id, folder, numbers)
    name = book["title"] if chapter is None else f"{book['title']} - {book['chapters'][chapter]['title']}"

    def stream():
        # Constant-bitrate MP3s with the same settings play back fine when simply joined.
        for _, fh, length in parts:
            yield from _copy(fh, length)

    return StreamingResponse(stream(), media_type="audio/mpeg", headers={
        "Content-Disposition": _filename(name, "mp3"),
        "Content-Length": str(sum(length for _, _, length in parts)),
        **auth.PRIVATE_HEADERS,
    })


class _ZipSink:
    """A write-only file for ZipFile that hands back what's been written, so the zip streams."""

    def __init__(self):
        self.chunks = []

    def write(self, data) -> int:
        self.chunks.append(bytes(data))
        return len(data)

    def flush(self):
        pass

    def take(self) -> bytes:
        data, self.chunks = b"".join(self.chunks), []
        return data


@api.get("/{book_id}/download-chapters.zip")
def download_chapters(book_id: str, user: str = Depends(require_user)):
    """The audiobook as a zip of one MP3 per chapter, numbered so they sort in order."""
    book, folder = _book(book_id, user)
    chapters = book["chapters"]
    parts = _audio_parts(book_id, folder, range(len(chapters)))
    width = max(2, len(str(len(chapters))))

    def stream():
        sink = _ZipSink()
        # MP3s don't compress, so store them. The sink can't seek, so ZipFile writes each
        # entry's sizes after its data.
        with zipfile.ZipFile(sink, "w", zipfile.ZIP_STORED) as z:
            for n, fh, length in parts:
                title = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "", chapters[n]["title"]).strip()[:80]
                with z.open(f"{n + 1:0{width}d} {title}.mp3".replace(" .mp3", ".mp3"), "w") as entry:
                    for chunk in _copy(fh, length):
                        entry.write(chunk)
                        yield sink.take()
        yield sink.take()

    return StreamingResponse(stream(), media_type="application/zip", headers={
        "Content-Disposition": _filename(f"{book['title']} (chapters)", "zip"),
        **auth.PRIVATE_HEADERS,
    })


router.include_router(api)
