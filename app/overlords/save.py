"""Overlords' records, in SQLite (`data/overlords.db`; OVERLORDS_DB overrides it for the checks).

Only records, no unlocks (the owner's choice): every finished match with at least one person in it
is kept, with each player's place, commander, augments, final traits and final board. A person is
known by their browser's token, stored hashed (a token is what lets a browser rejoin as its player,
so the raw one stays out of the database). From that: a player's games, wins, top-two finishes,
average place, favourite commander and trait, their recent matches, and the Hall of Overlords (the
most wins, under each browser's latest name).
"""

import hashlib
import json
import os
import sqlite3
import threading
import time
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("OVERLORDS_DB", "data/overlords.db"))
RECENT = 5
LEADERS = 5
_lock = threading.Lock()


def who(token):
    """The stored form of a browser's token, or None for bots and token-less browsers."""
    return hashlib.sha256(token.encode()).hexdigest()[:24] if token else None


@contextmanager
def _db():
    with _lock:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(DB_PATH)
        try:
            con.execute("CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY, at REAL, rounds INTEGER, "
                        "players TEXT)")
            con.execute("CREATE TABLE IF NOT EXISTS results (match INTEGER, who TEXT, name TEXT, bot TEXT, "
                        "place INTEGER, commander TEXT, augments TEXT, traits TEXT, units TEXT)")
            con.execute("CREATE INDEX IF NOT EXISTS results_who ON results (who)")
            yield con
            con.commit()
        finally:
            con.close()


def record(rounds, entries):
    """Saves a finished match. entries: [{token, name, bot, place, commander, augments, traits
    ({trait: count} active at the end), units ([[key, star]])}]."""
    with _db() as con:
        cur = con.execute("INSERT INTO matches (at, rounds, players) VALUES (?, ?, ?)",
                          (time.time(), rounds, len(entries)))
        mid = cur.lastrowid
        for e in entries:
            con.execute("INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (mid, who(e.get("token")), e["name"], e.get("bot"), e["place"], e.get("commander"),
                         json.dumps(e.get("augments", [])), json.dumps(e.get("traits", {})),
                         json.dumps(e.get("units", []))))
    return mid


def stats(token):
    """A browser's record: games, wins, top-two finishes, average place, favourite commander and
    trait (or None if it has no games), and its recent matches, newest first."""
    w = who(token)
    if not w:
        return None
    with _db() as con:
        rows = con.execute("SELECT r.match, r.place, r.commander, r.traits, m.at, m.rounds, m.players "
                           "FROM results r JOIN matches m ON m.id = r.match WHERE r.who = ? ORDER BY m.at DESC",
                           (w,)).fetchall()
    if not rows:
        return None
    places = [r[1] for r in rows]
    commanders = Counter(r[2] for r in rows if r[2])
    traits = Counter(t for r in rows for t in json.loads(r[3]))
    return {
        "games": len(rows), "wins": places.count(1), "top2": sum(p <= 2 for p in places),
        "avg": round(sum(places) / len(places), 2),
        "commander": commanders.most_common(1)[0][0] if commanders else None,
        "trait": traits.most_common(1)[0][0] if traits else None,
        "recent": [{"at": r[4], "place": r[1], "of": r[6], "rounds": r[5], "commander": r[2],
                    "traits": json.loads(r[3])} for r in rows[:RECENT]],
    }


def leaders():
    """The Hall of Overlords: the browsers with the most wins (then the best average place)."""
    with _db() as con:
        rows = con.execute("SELECT r.who, r.name, r.place, m.at FROM results r JOIN matches m ON m.id = r.match "
                           "WHERE r.who IS NOT NULL ORDER BY m.at").fetchall()
    people = {}
    for w, name, place, _ in rows:
        p = people.setdefault(w, {"name": name, "wins": 0, "games": 0, "places": 0})
        p["name"] = name  # the latest name it played under
        p["games"] += 1
        p["wins"] += place == 1
        p["places"] += place
    ranked = sorted(people.values(), key=lambda p: (-p["wins"], p["places"] / p["games"]))
    return [{"name": p["name"], "wins": p["wins"], "games": p["games"], "avg": round(p["places"] / p["games"], 2)}
            for p in ranked if p["wins"]][:LEADERS]
