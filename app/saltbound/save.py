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



def _v1(state):
    """v1 planned actions and resolved them together; v2 resolves each as it's placed. A fight saved
    mid-plan gets its planned dice back to play again."""
    f = state.get("fight")
    if f:
        for p in f.pop("plan", []):
            x = f["hs"].get(str(p["h"]))
            for d in (x or {}).get("dice", []):
                if d["id"] in p["dice"]:
                    d["used"] = False
        f["done"] = []
    state["v"] = 2
    return state


def _v2(state):
    """v3 enemies roll dice and heroes have no rows. A fight saved mid-round: the enemies' old
    intents can't be rolled, so they spend that round regrouping."""
    f = state.get("fight")
    if f:
        for fo in f["foes"]:
            fo["intent"] = {"k": "dazed", "name": "Regrouping"}
        for x in f["hs"].values():
            x.pop("row", None)
    # skills that were replaced: Quiver by Spotter, Riposte+ by Read the Blade, Pinning Arrow by Covering Fire
    swap = {"quiver": "spotter", "riposte_plus": "read_blade", "pinning_arrow": "covering_fire"}
    for hero in state.get("heroes", []):
        hero["skills"] = [swap.get(k, k) for k in hero.get("skills", [])]
    state["v"] = 3
    return state


def _v3(state):
    """v4 dungeons have lineup pools and forks. A dungeon part-way through goes on with the first
    lineup of its next step (no fork for a step already reached)."""
    from .content import archipelago as A
    state.setdefault("fork", None)
    nxt = state.setdefault("dnext", {})
    for reg, D in A.DUNGEONS.items():
        if reg in nxt:
            continue
        step = state.get("dungeon", {}).get(reg, 0)
        if step == 0:
            nxt[reg] = {"path": "open", "foes": list(D["open"][0])}
        elif step == 1:
            nxt[reg] = {"path": "passage", "foes": list(D["mid"][0])}
        else:
            nxt[reg] = {"path": "gate", "foes": D["escort"][0][:1] + [D["boss"]] + D["escort"][0][1:]}
    state["v"] = 4
    return state


# version -> function(state) -> state at version + 1
MIGRATIONS = {1: _v1, 2: _v2, 3: _v3}


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
