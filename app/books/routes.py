import json
import re
import shutil
import time
import zipfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse

from .. import auth
from ..serials import page as serials_page
from . import epub, pages, store

MAX_UPLOAD = 200 * 1024 * 1024
# Chapter text, images and audio never change for a given book id, so browsers may keep them.
IMMUTABLE = {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "private, max-age=604800"}

router = APIRouter(prefix="/books", include_in_schema=False)
api = APIRouter(prefix="/api", dependencies=[Depends(auth.require)], include_in_schema=False)


def _login(path: str) -> HTMLResponse:
    return HTMLResponse(
        serials_page.render_login(title="Library", next_path=path), status_code=401, headers=auth.PRIVATE_HEADERS
    )


@router.get("")
def library(request: Request):
    if not auth.authorized(request):
        return _login("/books")
    return HTMLResponse(pages.library(), headers=auth.PRIVATE_HEADERS)


@router.get("/read/{book_id}")
def reader(request: Request, book_id: str):
    if not auth.authorized(request):
        return _login(f"/books/read/{book_id}")
    book = store.load_book(book_id)
    if not book:
        raise HTTPException(404)
    return HTMLResponse(pages.reader(book, request.cookies.get("reader_theme", "")), headers=auth.PRIVATE_HEADERS)


def _book(book_id: str) -> tuple[dict, Path]:
    folder = store.book_dir(book_id)
    if not folder:
        raise HTTPException(404, "No such book")
    return store.read_json(folder / "book.json"), folder


def _audio_status(book: dict) -> dict:
    working = store.read_json(store.WORKER) or {}
    if working.get("book") != book["id"] or time.time() - working.get("updated", 0) > 120:
        working = None
    return {"ready": sorted(store.audio_done(book["id"])), "total": len(book["chapters"]), "working": working}


def _filename(title: str, ext: str) -> str:
    ascii_name = re.sub(r"[^A-Za-z0-9 ._-]+", "", title).strip()[:80] or "book"
    return f"attachment; filename=\"{ascii_name}.{ext}\"; filename*=UTF-8''{quote(title[:80])}.{ext}"


@api.get("/library")
def library_data():
    books = []
    for book in store.list_books():
        progress = store.read_json(store.BOOKS_DIR / book["id"] / "progress.json", {})
        books.append({
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "cover": book["cover"] and f"/books/api/{book['id']}/res/{quote(book['cover'])}",
            "percent": progress.get("percent", 0),
            "opened": progress.get("updated", 0),
            "added": book["added"],
            "audio": _audio_status(book),
        })
    return JSONResponse(books, headers=auth.PRIVATE_HEADERS)


@api.post("/upload")
async def upload(request: Request):
    data = await request.body()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "That file is too large.")
    try:
        book_id = await run_in_threadpool(epub.save, data)
    except epub.EpubError as e:
        raise HTTPException(400, str(e))
    return {"id": book_id}


@api.get("/{book_id}")
def book_data(book_id: str):
    book, folder = _book(book_id)
    book = {k: v for k, v in book.items() if k != "images"}
    book["cover"] = book["cover"] and f"/books/api/{book_id}/res/{quote(book['cover'])}"
    book["progress"] = store.read_json(folder / "progress.json")
    book["audio"] = _audio_status(book)
    return JSONResponse(book, headers=auth.PRIVATE_HEADERS)


@api.delete("/{book_id}")
def delete(book_id: str):
    _, folder = _book(book_id)
    shutil.rmtree(folder)
    return {"ok": True}


@api.get("/{book_id}/chapter/{n}")
def chapter(book_id: str, n: int):
    _, folder = _book(book_id)
    path = folder / "chapters" / f"{n}.html"
    if not path.exists():
        raise HTTPException(404)
    return HTMLResponse(path.read_text(), headers=IMMUTABLE)


@api.get("/{book_id}/res/{path:path}")
def resource(book_id: str, path: str):
    book, folder = _book(book_id)
    media_type = book["images"].get(path)
    if not media_type:
        raise HTTPException(404)
    with zipfile.ZipFile(folder / "book.epub") as z:
        return Response(z.read(path), media_type=media_type, headers=IMMUTABLE)


@api.get("/{book_id}/audio/{n}.json")
def audio_timing(book_id: str, n: int):
    _, folder = _book(book_id)
    timing = store.read_json(folder / "audio" / f"{n}.json")
    if timing is not None:
        return JSONResponse(timing, headers=IMMUTABLE)
    partial = store.read_json(store.partial_paths(folder, n)[1])
    if not partial or not partial["starts"]:
        raise HTTPException(404, "Not generated yet")
    return JSONResponse({**partial, "complete": False}, headers=auth.PRIVATE_HEADERS)


@api.get("/{book_id}/audio/{n}.mp3")
def audio(book_id: str, n: int, request: Request):
    _, folder = _book(book_id)
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
def audio_status(book_id: str):
    book, _ = _book(book_id)
    return JSONResponse(_audio_status(book), headers=auth.PRIVATE_HEADERS)


@api.post("/{book_id}/listen")
async def listen(book_id: str, request: Request):
    """Ask the worker to narrate this chapter next."""
    _book(book_id)
    chapter = int((await request.json()).get("chapter", 0))
    store.write_json(store.PRIORITY, {"book": book_id, "chapter": chapter})
    return {"ok": True}


@api.post("/{book_id}/progress")
async def progress(book_id: str, request: Request):
    _, folder = _book(book_id)
    body = json.loads(await request.body() or b"{}")
    store.write_json(folder / "progress.json", {
        "chapter": int(body.get("chapter", 0)),
        "segment": int(body.get("segment", 0)),
        "percent": max(0.0, min(100.0, float(body.get("percent", 0)))),
        "updated": time.time(),
    })
    return {"ok": True}


@api.get("/{book_id}/search")
def search(book_id: str, q: str):
    book, folder = _book(book_id)
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
def download_epub(book_id: str):
    book, folder = _book(book_id)
    return FileResponse(
        folder / "book.epub", media_type="application/epub+zip",
        headers={"Content-Disposition": _filename(book["title"], "epub"), **auth.PRIVATE_HEADERS},
    )


@api.get("/{book_id}/download.mp3")
def download_mp3(book_id: str, chapter: int | None = None):
    """The whole audiobook (every chapter narrated so far, in order) or a single chapter."""
    book, folder = _book(book_id)
    done = store.audio_done(book_id)
    numbers = [chapter] if chapter is not None else range(len(book["chapters"]))
    files = [folder / "audio" / f"{n}.mp3" for n in numbers if n in done]
    files = [f for f in files if f.exists()]
    if not files:
        raise HTTPException(404, "No audio yet")
    name = book["title"] if chapter is None else f"{book['title']} - {book['chapters'][chapter]['title']}"

    def stream():
        # Constant-bitrate MP3s with the same settings play back fine when simply joined.
        for f in files:
            with f.open("rb") as fh:
                while chunk := fh.read(1 << 20):
                    yield chunk

    return StreamingResponse(stream(), media_type="audio/mpeg", headers={
        "Content-Disposition": _filename(name, "mp3"),
        "Content-Length": str(sum(f.stat().st_size for f in files)),
        **auth.PRIVATE_HEADERS,
    })


router.include_router(api)
