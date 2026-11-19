"""Holdfast's saved games and best-wave records, in SQLite (`data/holdfast.db`).

A game is saved at the start of every build phase, so a deploy or a crash only loses the wave in
progress. A save belongs to every browser that played in it (their tokens); each browser keeps at
most `KEEP`. A game that ends deletes its save. Saves carry `VERSION`; a save from another version
is deleted when its owner next lists their saves (there are no migrations yet).

Records: the furthest wave reached on each map and difficulty, by number of players, with who did it.
"""

import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("HOLDFAST_DB", "data/holdfast.db"))
VERSION = 2  # 2: crosspathing (towers save tiers on both paths) and boss events
KEEP = 5
TOP = 5  # records listed per map and difficulty
_lock = threading.Lock()


@contextmanager
def _db():
    with _lock:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(DB_PATH)
        try:
            con.execute("CREATE TABLE IF NOT EXISTS games (id TEXT PRIMARY KEY, tokens TEXT, updated REAL, "
                        "summary TEXT, state TEXT)")
            con.execute("CREATE TABLE IF NOT EXISTS records (map TEXT, diff TEXT, players INTEGER, wave INTEGER, "
                        "names TEXT, won INTEGER, at REAL)")
            yield con
            con.commit()
        finally:
            con.close()


def save(game_id, tokens, state, summary):
    state = {**state, "v": VERSION}
    with _db() as con:
        con.execute("REPLACE INTO games VALUES (?, ?, ?, ?, ?)",
                    (game_id, json.dumps(sorted(tokens)), time.time(), summary, json.dumps(state)))
        for tok in tokens:  # each browser keeps its newest few
            rows = [r for r in con.execute("SELECT id, tokens FROM games ORDER BY updated DESC") if tok in json.loads(r[1])]
            for gid, _ in rows[KEEP:]:
                con.execute("DELETE FROM games WHERE id = ?", (gid,))


def list_for(token):
    if not token:
        return []
    with _db() as con:
        for gid, state in con.execute("SELECT id, state FROM games").fetchall():
            if json.loads(state).get("v") != VERSION:
                con.execute("DELETE FROM games WHERE id = ?", (gid,))
        rows = con.execute("SELECT id, tokens, updated, summary FROM games ORDER BY updated DESC").fetchall()
    return [{"id": r[0], "when": r[2], "summary": r[3]} for r in rows if token in json.loads(r[1])][:KEEP]


def load(game_id, token):
    """The saved state, or None (not found, not theirs, or from another version)."""
    with _db() as con:
        r = con.execute("SELECT tokens, state FROM games WHERE id = ?", (game_id,)).fetchone()
    if not r or token not in json.loads(r[0]):
        return None
    state = json.loads(r[1])
    return state if state.get("v") == VERSION else None


def forget(game_id, token):
    """A player deletes one of their own saves."""
    with _db() as con:
        r = con.execute("SELECT tokens FROM games WHERE id = ?", (game_id,)).fetchone()
        if r and token in json.loads(r[0]):
            con.execute("DELETE FROM games WHERE id = ?", (game_id,))


def delete(game_id):
    with _db() as con:
        con.execute("DELETE FROM games WHERE id = ?", (game_id,))


def record(map_id, diff, players, wave, names, won):
    """Note how far a game got. True if it's the best yet for that map, difficulty and party size."""
    with _db() as con:
        best = con.execute("SELECT MAX(wave) FROM records WHERE map = ? AND diff = ? AND players = ?",
                           (map_id, diff, players)).fetchone()[0]
        con.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (map_id, diff, players, wave, json.dumps(names), int(won), time.time()))
    return best is None or wave > best


def records(map_id, diff):
    """The best games on a map and difficulty: [{wave, players, names, won, at}]."""
    with _db() as con:
        rows = con.execute("SELECT wave, players, names, won, at FROM records WHERE map = ? AND diff = ? "
                           "ORDER BY wave DESC, at ASC LIMIT ?", (map_id, diff, TOP)).fetchall()
    return [{"wave": r[0], "players": r[1], "names": json.loads(r[2]), "won": bool(r[3]), "at": r[4]} for r in rows]
