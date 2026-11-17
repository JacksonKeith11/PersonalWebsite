"""Plays Sketch Relay headlessly, with pretend browsers, and checks it holds together.

    python3 tools/relay-check.py

Games of 3 to 8 players are played through to the album: every book must get one page from every
player, alternating words and drawings, and each player must be handed the page the one before
them made. Then the awkward cases: drawings that aren't drawings, a player who runs out of time,
one who leaves mid-game and comes back, someone joining a game under way, and playing again.
"""

import asyncio
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.relay import game  # noqa: E402
from app.rooms import Refused  # noqa: E402


class Browser:
    """A pretend player: joins a room and remembers the latest of each kind of message."""

    def __init__(self, room, name):
        self.queue = asyncio.Queue(maxsize=200)
        self.name = name
        self.token = f"token-{name}-{random.random()}"
        self.last = {}
        self.join(room)

    def join(self, room):
        self.room = room
        self.p = room.join(self.queue, self.name, self.token, "tab")
        self.read()

    def read(self):
        while not self.queue.empty():
            text = self.queue.get_nowait()
            if text is not None:
                m = json.loads(text)
                self.last[m["t"]] = m
        return self.last

    def do(self, **msg):
        self.room.handle(self.p, msg)

    def drop(self):
        self.room.leave(self.p, self.queue)

    def play(self):
        """Hand in this step's page, if there's one to do. Returns what was sent."""
        task = self.read().get("task")
        st = self.last["state"]
        if st["phase"] != "play" or not task or task["step"] != st["step"] or task["done"]:
            return None
        task["done"] = True
        if task["kind"] == "draw":
            sent = [{"c": random.randrange(game.N_COLORS), "w": random.randrange(game.N_WIDTHS),
                     "p": [random.randrange(game.W), random.randrange(game.H), 5, 5]}]
            self.do(t="submit", step=task["step"], strokes=sent)
        else:
            sent = f"{self.name} at step {task['step']}"
            self.do(t="submit", step=task["step"], text=sent)
        return sent


def everyone(browsers):
    for b in browsers:
        b.read()


def play_out(room, browsers):
    """Play from the lobby to the album, checking each page is passed on to the right player."""
    host = browsers[0]
    host.do(t="start")
    everyone(browsers)
    n = len(room.order)
    assert room.phase == "play" and n == len(browsers), (room.phase, n)
    seat = {b.p.id: b for b in browsers}
    for step in range(n):
        assert room.step == step
        sent = {}
        for i, pid in enumerate(room.order):
            b = seat[pid]
            task = b.read()["task"]
            assert task["step"] == step and task["kind"] == room.kind(), task
            if step:
                # the page handed to this seat is the one the seat before it made last step
                before = room.order[(i - 1) % n]
                page = task["page"]
                assert page.get("text", page.get("strokes")) == made[before], (step, i)
            sent[pid] = b.play()
        made = sent
        everyone(browsers)
    assert room.phase == "reveal", room.phase
    for book in room.books:
        assert len(book) == n and len({page["by"] for page in book}) == n
        assert [page["k"] for page in book] == ["draw" if i % 2 else "text" for i in range(n)]
    for b in browsers:
        assert b.read()["books"]["books"] == room.books
    turns = 0
    while room.phase == "reveal":
        browsers[1].do(t="next")  # not the host: ignored
        host.do(t="next")
        turns += 1
        assert turns <= n * n, "the reveal never ends"
    assert turns == n * n and room.phase == "album", (turns, room.phase)


def check_drawings():
    c = game.clean_drawing
    assert c(None) == [] and c("scribble") == [] and c([1, "x", None, {}]) == []
    assert c([{"c": 0, "w": 0, "p": [1]}]) == [] and c([{"c": 99, "w": 0, "p": [1, 2]}]) == []
    assert c([{"c": True, "w": 0, "p": [1, 2]}]) == [] and c([{"c": 0, "w": 0, "p": [1.5, 2]}]) == []
    assert c([{"c": 1, "w": 2, "p": [-5, 9999, 10, 20, 7], "x": "junk"}]) == [{"c": 1, "w": 2, "p": [0, game.H, 10, 20]}]
    big = c([{"c": 0, "w": 0, "p": [1, 2] * 5000}, {"c": 0, "w": 0, "p": [1, 2] * 5000}])
    assert sum(len(s["p"]) // 2 for s in big) == game.MAX_POINTS
    assert len(c([{"c": 0, "w": 0, "p": [1, 2]}] * 5000)) == game.MAX_STROKES


async def main():
    check_drawings()

    for n in range(game.MIN_PLAYERS, game.MAX_PLAYERS + 1):
        room = game.Room("TEST")
        browsers = [Browser(room, f"P{i}") for i in range(n)]
        play_out(room, browsers)
        # and again, in the same room
        browsers[0].do(t="again")
        assert room.phase == "lobby" and len(room.players) == n
        play_out(room, browsers)

    # Too few players: no game.
    room = game.Room("TEST")
    a, b = Browser(room, "A"), Browser(room, "B")
    a.do(t="start")
    assert room.phase == "lobby"
    # The same name twice, and only the host may start.
    c = Browser(room, "A")
    assert c.p.name == "A 2"
    b.do(t="start")
    assert room.phase == "lobby"
    b.do(t="timer", v="off")
    assert room.timer == "normal"
    a.do(t="timer", v="relaxed")
    assert room.timer == "relaxed" and a.read()["state"]["timer"] == "relaxed"
    a.do(t="start")
    assert room.phase == "play" and a.read()["state"]["left"] > 100

    # Someone arriving mid-game watches; an empty or stale page is ignored.
    d = Browser(room, "D")
    assert not room.playing(d.p) and "task" not in d.last
    a.do(t="submit", step=0, text="   ")
    a.do(t="submit", step=3, text="too early")
    d.do(t="submit", step=0, text="not playing")
    assert not room.done
    # A leaves and comes back to the same seat and job; the watcher leaving is forgotten.
    a.drop()
    d.drop()
    assert room.playing(a.p) and not a.p.connected and d.p.id not in room.players and room.host != a.p.id
    a.last.clear()
    a.join(room)
    assert a.last["task"]["step"] == 0 and not a.last["task"]["done"] and room.phase == "play"
    # The clock runs out on B: a stock prompt stands in.
    a.play(), c.play()
    assert room.step == 0
    room.times_up()
    assert room.step == 1
    mine = room.books[room.book_of(b.p.id, 0)][0]
    assert mine["auto"] and mine["text"] in game.IDEAS
    # C leaves for good: the step ends once the others are in, with a blank sheet for C.
    c.drop()
    a.play()
    assert room.step == 1
    b.play()
    assert room.step == 2 and room.books[room.book_of(c.p.id, 1)][1] == {"k": "draw", "strokes": [], "by": c.p.id, "auto": True}
    # The host hurries the last step along; whoever hadn't finished gets a shrug.
    host = next(x for x in (a, b) if x.p.id == room.host)
    host.do(t="hurry")
    assert room.phase == "reveal" and all(book[2]["text"] == "(no idea)" for book in room.books)
    # A watcher who arrives now gets the books; back in the lobby, C (gone) is dropped.
    e = Browser(room, "E")
    assert e.last["books"]["books"] == room.books
    while room.phase == "reveal":
        host.do(t="next")
    host.do(t="again")
    assert room.phase == "lobby" and sorted(p.name for p in room.players.values()) == ["A", "B", "E"]

    # With the timer off there's no clock, and a full room turns people away.
    host.do(t="timer", v="off")
    host.do(t="start")
    assert room.phase == "play" and host.read()["state"]["left"] is None and room.alarm is None
    for i in range(game.MAX_IN_ROOM - len(room.players)):
        Browser(room, f"W{i}")
    try:
        Browser(room, "one too many")
        raise AssertionError("a full room let someone in")
    except Refused:
        pass
    # Everyone leaves mid-game: the room waits, and is marked empty for sweeping.
    for p in list(room.players.values()):
        room.leave(p, p.queue)
    assert room.phase == "play" and room.empty_since
    print("Sketch Relay: games of 3 to 8 played out; timeouts, leaving, rejoining and watching hold up")


asyncio.run(main())
