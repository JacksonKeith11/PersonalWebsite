import hashlib
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path

DB_PATH = Path(os.environ.get("SERIALS_DB", "data/serials.db"))

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


@dataclass
class Update:
    key: str  # unique per update; usually the chapter URL
    site: str
    story_title: str
    story_url: str
    title: str
    url: str
    published: float  # unix seconds


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS updates (
                key TEXT PRIMARY KEY,
                site TEXT NOT NULL,
                story_title TEXT NOT NULL,
                story_url TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS updates_published ON updates (published DESC);
            CREATE TABLE IF NOT EXISTS tracked (
                site TEXT NOT NULL,
                story_id TEXT NOT NULL,
                story_url TEXT NOT NULL,
                PRIMARY KEY (site, story_id)
            );
            CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT);
            CREATE TABLE IF NOT EXISTS status (
                source TEXT PRIMARY KEY,
                last_run REAL,
                last_ok REAL,
                error TEXT
            );
            """
        )
    return _conn


def save_updates(updates: list[Update]) -> None:
    with _lock:
        db = _db()
        db.executemany(
            """
            INSERT INTO updates (key, site, story_title, story_url, title, url, published)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (key) DO UPDATE SET
                story_title = excluded.story_title,
                story_url = excluded.story_url,
                title = excluded.title,
                url = excluded.url,
                published = excluded.published
            """,
            [(u.key, u.site, u.story_title, u.story_url, u.title, u.url, u.published) for u in updates],
        )
        db.commit()


def recent_updates(limit: int = 300, offset: int = 0) -> list[sqlite3.Row]:
    with _lock:
        return _db().execute(
            "SELECT * FROM updates ORDER BY published DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()


def count_updates() -> int:
    with _lock:
        return _db().execute("SELECT COUNT(*) FROM updates").fetchone()[0]


def track(site: str, story_id: str, story_url: str) -> None:
    with _lock:
        db = _db()
        db.execute(
            "INSERT INTO tracked (site, story_id, story_url) VALUES (?, ?, ?) "
            "ON CONFLICT (site, story_id) DO UPDATE SET story_url = excluded.story_url",
            (site, story_id, story_url),
        )
        db.commit()


def tracked(site: str) -> list[sqlite3.Row]:
    with _lock:
        return _db().execute("SELECT * FROM tracked WHERE site = ?", (site,)).fetchall()


def get_state(k: str, default: str | None = None) -> str | None:
    with _lock:
        row = _db().execute("SELECT v FROM state WHERE k = ?", (k,)).fetchone()
    return row["v"] if row else default


def set_state(k: str, v: str) -> None:
    with _lock:
        db = _db()
        db.execute("INSERT INTO state (k, v) VALUES (?, ?) ON CONFLICT (k) DO UPDATE SET v = excluded.v", (k, v))
        db.commit()


def record_status(source: str, error: str | None) -> None:
    now = time.time()
    with _lock:
        db = _db()
        if error is None:
            db.execute(
                "INSERT INTO status (source, last_run, last_ok, error) VALUES (?, ?, ?, NULL) "
                "ON CONFLICT (source) DO UPDATE SET last_run = ?, last_ok = ?, error = NULL",
                (source, now, now, now, now),
            )
        else:
            db.execute(
                "INSERT INTO status (source, last_run, error) VALUES (?, ?, ?) "
                "ON CONFLICT (source) DO UPDATE SET last_run = ?, error = ?",
                (source, now, error, now, error),
            )
        db.commit()


def statuses() -> list[sqlite3.Row]:
    with _lock:
        return _db().execute("SELECT * FROM status ORDER BY source").fetchall()


def _fingerprint(*creds: str) -> str:
    return hashlib.sha256("\0".join(creds).encode()).hexdigest()


def creds_rejected(source: str, *creds: str) -> bool:
    """True if these exact credentials were already rejected, so we don't keep retrying them."""
    return get_state(f"rejected:{source}") == _fingerprint(*creds)


def mark_creds_rejected(source: str, *creds: str) -> None:
    set_state(f"rejected:{source}", _fingerprint(*creds))
