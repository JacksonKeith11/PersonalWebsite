"""On-disk layout shared by the web app and the TTS worker (stdlib only, so the worker image stays small).

data/books/
  priority.json          chapter the reader asked to listen to; the worker does it first
  worker.json            what the worker is generating right now
  <id>/book.json         metadata, chapter list, table of contents
  <id>/book.epub         the original upload
  <id>/progress.json     reading position
  <id>/chapters/<n>.html reader markup; every spoken block carries data-s="<segment>"
  <id>/chapters/<n>.json the text of each segment, in order
  <id>/audio/<n>.mp3     narration for chapter n
  <id>/audio/<n>.json    {"starts": [segment start seconds], "duration": seconds}; written last, marks n done
  <id>/audio/.<n>.mp3.tmp, <n>.partial.json   chapter n while it's being narrated (playable as it grows)
"""

import json
import os
import re
from pathlib import Path

BOOKS_DIR = Path(os.environ.get("BOOKS_DIR", "/app/data/books"))
PRIORITY = BOOKS_DIR / "priority.json"
WORKER = BOOKS_DIR / "worker.json"
ID_RE = re.compile(r"^[0-9a-f]{12}$")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def write_json(path: Path, data) -> None:
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, path)


def book_dir(book_id: str) -> Path | None:
    if not ID_RE.match(book_id):
        return None
    path = BOOKS_DIR / book_id
    return path if (path / "book.json").exists() else None


def load_book(book_id: str) -> dict | None:
    path = book_dir(book_id)
    return read_json(path / "book.json") if path else None


def list_books() -> list[dict]:
    """All books, newest upload first."""
    if not BOOKS_DIR.exists():
        return []
    books = [read_json(p / "book.json") for p in BOOKS_DIR.iterdir() if ID_RE.match(p.name)]
    return sorted((b for b in books if b), key=lambda b: b["added"], reverse=True)


def partial_paths(folder: Path, n: int) -> tuple[Path, Path]:
    """The MP3 of a chapter still being narrated, and the record of how much of it is written."""
    return folder / "audio" / f".{n}.mp3.tmp", folder / "audio" / f"{n}.partial.json"


def audio_done(book_id: str) -> set[int]:
    audio = BOOKS_DIR / book_id / "audio"
    if not audio.exists():
        return set()
    return {int(p.stem) for p in audio.glob("*.json") if p.stem.isdigit()}
