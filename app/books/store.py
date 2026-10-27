"""On-disk layout shared by the web app and the TTS worker (stdlib only, so the worker image stays small).

data/books/
  priority.json          chapter the reader asked to listen to; the worker does it first
  worker.json            what the worker is generating right now
  <id>/book.json         metadata (including the uploader's username, "owner"), chapter list, table of contents;
                         "source" is the story link of an imported book, and "rev" counts its updates
  <id>/book.epub         the original upload
  <id>/progress.json     reading position
  <id>/narrate           present once someone asks for the audiobook; the worker narrates only these
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
NARRATE = "narrate"
ID_RE = re.compile(r"^[0-9a-f]{12}$")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def write_text(path: Path, text: str) -> None:
    """Replace a file in one step, so a reader never sees half of it."""
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data))


def book_dir(book_id: str) -> Path | None:
    if not ID_RE.match(book_id):
        return None
    path = BOOKS_DIR / book_id
    return path if (path / "book.json").exists() else None


def load_book(book_id: str) -> dict | None:
    path = book_dir(book_id)
    return read_json(path / "book.json") if path else None


def list_books(owner: str | None = None) -> list[dict]:
    """All books, or one user's, newest upload first."""
    if not BOOKS_DIR.exists():
        return []
    books = [read_json(p / "book.json") for p in BOOKS_DIR.iterdir() if ID_RE.match(p.name)]
    books = [b for b in books if b and (owner is None or b.get("owner") == owner)]
    return sorted(books, key=lambda b: b["added"], reverse=True)


def narration_requested(book_id: str) -> bool:
    return (BOOKS_DIR / book_id / NARRATE).exists()


def partial_paths(folder: Path, n: int) -> tuple[Path, Path]:
    """The MP3 of a chapter still being narrated, and the record of how much of it is written."""
    return folder / "audio" / f".{n}.mp3.tmp", folder / "audio" / f"{n}.partial.json"


def audio_done(book_id: str) -> set[int]:
    audio = BOOKS_DIR / book_id / "audio"
    if not audio.exists():
        return set()
    return {int(p.stem) for p in audio.glob("*.json") if p.stem.isdigit()}
