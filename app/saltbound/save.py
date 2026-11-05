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
from contextlib import contextmanager
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
    for reg in ("coral", "keys", "storm"):  # saves this old only ever had the original three
        D = A.DUNGEONS[reg]
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


def _v4(state):
    """v5: the rising tide no longer floods (land already flooded stays so), loot after a fight is
    one shared pool (`pools`), and two commons no better than starting gear are gone: the Fishing
    Spear (the Rapier exactly) and the Sailcloth Wrap (a Wool Robe with a worse face)."""
    text = json.dumps(state).replace('"fishing_spear"', '"rapier"').replace('"sailcloth_wrap"', '"wool_robe"')
    state = json.loads(text)
    state.setdefault("pools", {})
    state.setdefault("poolid", 0)
    state["v"] = 5
    return state


def _v5(state):
    """v6 heroes have a second trinket slot."""
    for hero in state.get("heroes", []):
        hero.setdefault("equip", {}).setdefault("trinket2", None)
    state["v"] = 6
    return state


def _v6(state):
    """v7 takes the second trinket slot out again: whatever was in it goes into the bag."""
    for hero in state.get("heroes", []):
        extra = hero.get("equip", {}).pop("trinket2", None)
        if extra:
            hero.setdefault("bag", []).append(extra)
    state["v"] = 7
    return state


def _v7(state):
    """v8 adds the overworld's choices: what places show before you reach them, town trades,
    opportunities, garrisons and event chains. Places get theirs from a generator of their own (so the
    run's main one is untouched); old saves get no guarded wrecks or lair prizes."""
    from .game import Game
    from .rng import Rng
    state.update({k: state.get(k, v) for k, v in
                  {"opps": [], "oppid": 0, "garrison": {}, "crown_cut": 0, "chains": []}.items()})
    for p in state["world"]["places"].values():
        if p["kind"] == "event" and p.get("done"):
            p.setdefault("ev", None)
    Game(state).setup_places(Rng(state["seed"] * 31 + 7), guards=False)
    state["v"] = 8
    return state


def _v8(state):
    """v9 makes jobs two to a board, with deadlines and rewards. A board's old single offer is dropped
    (a new board is made the next time someone stands in the town); jobs already taken keep the old
    reward and get a generous deadline."""
    places = state["world"]["places"]
    by_name = {p.get("name"): int(t) for t, p in places.items() if p["kind"] == "town"}
    for p in places.values():
        p.pop("quest", None)
    for i, q in enumerate(state.get("quests", []), 1):
        q.setdefault("id", i)
        q.setdefault("failed", False)
        q.setdefault("until", state["turn"] + 20)
        q.setdefault("reward", {"gold": 25, "type": "loot"})
        q.setdefault("src_tile", by_name.get(q.get("src"), state["world"]["start"]))
        if q["kind"] == "deliver":
            q.setdefault("tile", q["to"])
    state["jobid"] = len(state.get("quests", []))
    state["v"] = 9
    return state


def _v9(state):
    """v10 fills the sea and the land's secrets: currents, reefs, whirlpools, places at sea, lookouts
    and hidden grottos (`world.add_features`, from the run's seed, as a new run of it would have them),
    sea beasts, squalls and raids. The extras come from generators of their own, so the run's main one
    is untouched."""
    from .game import Game
    from .content import archipelago as A
    from . import world as Wd
    from .rng import Rng
    Wd.add_features(state["world"], Rng(state["seed"] ^ 0x5EA5))
    for p in state["world"]["places"].values():
        if p["kind"] == "shrine" and p.get("sea"):
            p.setdefault("buff", A.SEA_SHRINE_BUFF)
    state.update({k: state.get(k, v) for k, v in {"squalls": [], "sqid": 0, "garrison_skip": {}}.items()})
    g = Game(state)
    g.rng = Rng(state["seed"] * 13 + 5)
    for _ in range(A.SEA_MAX):
        g.spawn_sea(far=4)
    state["v"] = 10
    return state


def _v10(state):
    """v11 gives the Vanguard Impact: Payback takes Retaliate's place in its kit (an upgraded
    Retaliate becomes an upgraded Payback), and the Avalanche capstone (Retaliate on the front row)
    becomes Shockwave."""
    swap = {"retaliate": "payback", "retaliate+": "payback+", "avalanche": "shockwave"}
    for hero in state.get("heroes", []):
        if hero.get("cls") == "vanguard":
            sk = [swap.get(k, k) for k in hero.get("skills", [])]
            if "payback" not in sk and "payback+" not in sk:
                sk.append("payback")
            hero["skills"] = list(dict.fromkeys(sk))
    state["v"] = 11
    return state


# version -> function(state) -> state at version + 1
MIGRATIONS = {1: _v1, 2: _v2, 3: _v3, 4: _v4, 5: _v5, 6: _v6, 7: _v7, 8: _v8, 9: _v9, 10: _v10}


class TooOld(Exception):
    pass


_con = None


@contextmanager
def _db():
    """The database, one connection for the process (made on first use), held under the lock:
    the event loop and the threadpool's `saves` route both use it."""
    global _con
    with _lock:
        if _con is None:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            _con = sqlite3.connect(DB_PATH, check_same_thread=False)
            _con.execute("""CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, created REAL, updated REAL, version INTEGER, title TEXT,
                tokens TEXT, state TEXT)""")
        yield _con


def save(run_id, tokens, g, title):
    state = json.dumps(g.s, separators=(",", ":"))
    now = time.time()
    with _db() as con, con:
        old = con.execute("SELECT tokens FROM runs WHERE id = ?", (run_id,)).fetchone()
        if old:
            tokens = sorted(set(json.loads(old[0])) | set(tokens))
            con.execute("UPDATE runs SET updated = ?, version = ?, title = ?, tokens = ?, state = ? WHERE id = ?",
                        (now, g.s["v"], title, json.dumps(tokens), state, run_id))
        else:
            con.execute("INSERT INTO runs VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (run_id, now, now, g.s["v"], title, json.dumps(sorted(tokens)), state))
            _prune(con, tokens, run_id)


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
    with _db() as con:
        rows = con.execute("SELECT id, updated, title, tokens, version FROM runs ORDER BY updated DESC").fetchall()
    return [{"id": r[0], "updated": r[1], "title": r[2], "ok": r[4] <= G.VERSION}
            for r in rows if token in json.loads(r[3])][:KEEP]


def load(run_id, token):
    with _db() as con:
        row = con.execute("SELECT tokens, state FROM runs WHERE id = ?", (run_id,)).fetchone()
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
    with _db() as con, con:
        row = con.execute("SELECT tokens FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row and token in json.loads(row[0]):
            con.execute("DELETE FROM runs WHERE id = ?", (run_id,))
