"""Saved runs, in SQLite (`data/kingfall.db`): a checkpoint at every Bonfire, so a deploy or a crash
only loses the fight in progress.

A save belongs to every browser that played in it (their tokens); each browser keeps at most `KEEP`.
A run that ends (won or lost) deletes its save. Saves carry `VERSION`; `MIGRATIONS[n]` turns a
version-n state into version n+1, and a save that can't be brought up to date is deleted when its
owner next lists their saves (so bumping `VERSION` without a migration clears every old run).
"""

import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("KINGFALL_DB", "data/kingfall.db"))
VERSION = 2   # 2 (Nov 2026): the owner asked for old runs to be cleared (one was stuck), and the blessings had changed under them
MIGRATIONS = {}
KEEP = 5
_lock = threading.Lock()


@contextmanager
def _db():
    with _lock:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(DB_PATH)
        try:
            con.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, tokens TEXT, updated REAL, summary TEXT, state TEXT)")
            yield con
            con.commit()
        finally:
            con.close()


def save(run_id, tokens, state, summary):
    state = {**state, "v": VERSION}
    with _db() as con:
        con.execute("REPLACE INTO runs VALUES (?, ?, ?, ?, ?)", (run_id, json.dumps(sorted(tokens)), time.time(), summary, json.dumps(state)))
        for tok in tokens:  # each browser keeps its newest few
            rows = [r for r in con.execute("SELECT id, tokens FROM runs ORDER BY updated DESC") if tok in json.loads(r[1])]
            for rid, _ in rows[KEEP:]:
                con.execute("DELETE FROM runs WHERE id = ?", (rid,))


def list_for(token):
    if not token: return []
    with _db() as con:
        for rid, state in con.execute("SELECT id, state FROM runs").fetchall():   # drop what can no longer be loaded
            v = json.loads(state).get("v", 0)
            while v < VERSION and v in MIGRATIONS: v += 1
            if v < VERSION: con.execute("DELETE FROM runs WHERE id = ?", (rid,))
        rows = con.execute("SELECT id, tokens, updated, summary FROM runs ORDER BY updated DESC").fetchall()
    return [{"id": r[0], "when": r[2], "summary": r[3]} for r in rows if token in json.loads(r[1])][:KEEP]


def load(run_id, token):
    """The saved state, brought up to date, or None (not found, not theirs, or too old to load)."""
    with _db() as con:
        r = con.execute("SELECT tokens, state FROM runs WHERE id = ?", (run_id,)).fetchone()
    if not r or token not in json.loads(r[0]): return None
    state = json.loads(r[1])
    while state.get("v", 0) < VERSION:
        step = MIGRATIONS.get(state.get("v", 0))
        if not step: return None
        state = step(state)
    return state


def forget(run_id, token):
    """A player deletes one of their own saves."""
    with _db() as con:
        r = con.execute("SELECT tokens FROM runs WHERE id = ?", (run_id,)).fetchone()
        if r and token in json.loads(r[0]): con.execute("DELETE FROM runs WHERE id = ?", (run_id,))


def delete(run_id):
    with _db() as con:
        con.execute("DELETE FROM runs WHERE id = ?", (run_id,))
