"""Saved runs, in SQLite (`data/saltbound.db`).

A run is saved after every resolved map turn and every combat round, overwriting its own row. A
save belongs to every browser that played in it (their tokens), and each browser keeps at most
`KEEP` runs: starting a sixth deletes its oldest. Saves carry the game's `VERSION`; `MIGRATIONS[n]`
turns a version-n state into version n+1, and a save that can't be brought up to date is refused
rather than loaded half-broken.
"""

import json
import os
import sqlite3
import threading
import time
from pathlib import Path

from . import game as G

DB_PATH = Path(os.environ.get("SALTBOUND_DB", "data/saltbound.db"))
KEEP = 5
_lock = threading.Lock()

# version -> function(state) -> state at version + 1
MIGRATIONS = {}


class TooOld(Exception):
    pass


def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS runs (
        id TEXT PRIMARY KEY, created REAL, updated REAL, version INTEGER, title TEXT,
        tokens TEXT, state TEXT)""")
    return con


def save(run_id, tokens, g, title):
    state = json.dumps(g.s, separators=(",", ":"))
    now = time.time()
    with _lock:
        con = _db()
        try:
            with con:
                old = con.execute("SELECT tokens FROM runs WHERE id = ?", (run_id,)).fetchone()
                if old:
                    tokens = sorted(set(json.loads(old[0])) | set(tokens))
                    con.execute("UPDATE runs SET updated = ?, version = ?, title = ?, tokens = ?, state = ? WHERE id = ?",
                                (now, g.s["v"], title, json.dumps(tokens), state, run_id))
                else:
                    con.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (run_id, now, now, g.s["v"], title, json.dumps(sorted(tokens)), state))
                    _prune(con, tokens, run_id)
        finally:
            con.close()


def _prune(con, tokens, keep_id):
    for tok in tokens:
        rows = con.execute("SELECT id, tokens FROM runs ORDER BY updated DESC").fetchall()
        mine = [r[0] for r in rows if tok in json.loads(r[1])]
        for rid in mine[KEEP:]:
            if rid != keep_id:
                con.execute("DELETE FROM runs WHERE id = ?", (rid,))


def list_for(token):
    if not token:
        return []
    with _lock:
        con = _db()
        try:
            rows = con.execute("SELECT id, updated, title, tokens, version FROM runs ORDER BY updated DESC").fetchall()
        finally:
            con.close()
    return [{"id": r[0], "updated": r[1], "title": r[2], "ok": r[4] <= G.VERSION}
            for r in rows if token in json.loads(r[3])][:KEEP]


def load(run_id, token):
    with _lock:
        con = _db()
        try:
            row = con.execute("SELECT tokens, state FROM runs WHERE id = ?", (run_id,)).fetchone()
        finally:
            con.close()
    if not row or token not in json.loads(row[0]):
        return None
    state = json.loads(row[1])
    return migrate(state)


def migrate(state):
    while state.get("v", 0) < G.VERSION:
        step = MIGRATIONS.get(state.get("v", 0))
        if step is None:
            raise TooOld(f"This save is from an older version (v{state.get('v')}) that can't be brought up to date.")
        state = step(state)
    if state.get("v") != G.VERSION:
        raise TooOld("This save is from a newer version of the game.")
    return state


def delete(run_id, token):
    with _lock:
        con = _db()
        try:
            with con:
                row = con.execute("SELECT tokens FROM runs WHERE id = ?", (run_id,)).fetchone()
                if row and token in json.loads(row[0]):
                    con.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        finally:
            con.close()
