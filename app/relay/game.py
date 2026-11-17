"""Sketch Relay: a drawing-and-guessing relay for 3-8 friends, each on their own phone or computer.

Everyone writes a prompt. Each prompt is passed to the next player, who draws it; the drawing is
passed on to the next, who writes what they think it is; that guess is passed on and drawn; and so
on until every player has added one page to every chain (a "book"). Then the books are read out
page by page, and everyone sees how far each one drifted.

A room is one game table: `Room.handle` takes the browsers' messages, and the whole (small) state
is sent to everyone whenever it changes. A player's own job for the step (`task`) and the finished
books (`books`) carry drawings, so they're sent once rather than with every state.
"""

import asyncio
import random
import time

from ..rooms import Codes, Refused, clean, hang_up, push
from .ideas import IDEAS

MIN_PLAYERS = 3
MAX_PLAYERS = 8
COLORS = ["#d9482b", "#3f7fd9", "#d9a515", "#3fa55a", "#8a4fc9", "#d9558f", "#2aa5a5", "#8a6a3a"]
MAX_IN_ROOM = 24  # players and people watching
ROOM_KEEP = 30 * 60  # how long a room with nobody connected lingers, for rejoining

# A drawing is a list of strokes on a W x H sheet: {"c": colour, "w": width, "p": [x, y, x, y, ...]}.
# `c` and `w` index the browser's palette and brush sizes (js/pad.js: PALETTE, WIDTHS).
W, H = 800, 600
N_COLORS = 12
N_WIDTHS = 4
MAX_STROKES = 600
MAX_POINTS = 8000  # a whole drawing's "ink"; the browser shows it running out
TEXT_LEN = 80

# Seconds for each kind of step, by the room's timer setting; "off" waits for everyone.
TIMES = {"normal": {"write": 75, "draw": 100, "guess": 50},
         "relaxed": {"write": 150, "draw": 200, "guess": 100}}
TIMERS = ("normal", "relaxed", "off")
GRACE = 2.5  # after the clock runs out, for browsers to send in what they have


def clean_drawing(data):
    """A drawing from a browser, with anything out of range dropped or clamped ([] if it isn't one)."""
    if not isinstance(data, list):
        return []
    out, points = [], 0
    for s in data[:MAX_STROKES]:
        if not isinstance(s, dict):
            continue
        c, w, p = s.get("c"), s.get("w"), s.get("p")
        if type(c) is not int or type(w) is not int or not isinstance(p, list):
            continue
        if not (0 <= c < N_COLORS and 0 <= w < N_WIDTHS) or len(p) < 2:
            continue
        p = p[:len(p) // 2 * 2][:(MAX_POINTS - points) * 2]
        if not p or not all(type(v) is int for v in p):
            continue
        p = [min(max(v, 0), H if i % 2 else W) for i, v in enumerate(p)]
        points += len(p) // 2
        out.append({"c": c, "w": w, "p": p})
        if points >= MAX_POINTS:
            break
    return out


class Player:
    def __init__(self, pid, name, color, queue, token, tab):
        self.id = pid
        self.name = name
        self.color = color
        self.queue = queue
        self.token = token
        self.tab = tab
        self.connected = True
        self.closing = False


class Room:
    def __init__(self, code):
        self.code = code
        self.players: dict[int, Player] = {}
        self.next_id = 1
        self.host = None
        self.timer = "normal"
        self.phase = "lobby"  # lobby, play, reveal, album
        self.order = []  # the ids of who's playing, in passing order
        self.books = []  # books[b] is a list of pages; order[b] started it
        self.step = 0
        self.done = {}  # pid -> the page they've handed in this step
        self.deadline = None  # monotonic time the step's clock runs out, if there's a clock
        self.alarm = None
        self.reveal = [0, 1]  # the book being read out, and how many of its pages are showing
        self.empty_since = None

    # ------------------------------------------------------------ plumbing

    def send(self, p, data):
        if not p.connected or p.closing or p.queue is None:
            return
        if not push(p.queue, data, p.name, "relay"):
            p.closing = True

    def at(self, delay, fn):
        """Call `fn` in `delay` seconds, instead of whatever was waiting (None: nothing)."""
        if self.alarm is not None:
            self.alarm.cancel()
        self.alarm = asyncio.get_running_loop().call_later(delay, fn) if fn else None

    def playing(self, p):
        return p.id in self.order

    def kind(self, step=None):
        step = self.step if step is None else step
        return "write" if step == 0 else "draw" if step % 2 else "guess"

    def book_of(self, pid, step=None):
        """The index of the book `pid` works on in a step: each step, books move one seat along."""
        step = self.step if step is None else step
        return (self.order.index(pid) - step) % len(self.order)

    # ------------------------------------------------------------ joining and leaving

    def join(self, queue, name, token, tab):
        token, tab, name = clean(token, 40), clean(tab, 40), clean(name, 16) or "Player"
        p = next((q for q in self.players.values() if token and q.token == token), None)
        if p is not None and p.connected and p.tab != tab:
            p, token = None, ""  # a second tab of the same browser: someone new
        if p is not None:
            if p.connected and p.queue is not None:
                hang_up(p.queue)
            p.queue, p.tab, p.connected, p.closing = queue, tab, True, False
            if p.name != name:
                p.name = self.unique_name(name, skip=p)
        else:
            if len(self.players) >= MAX_IN_ROOM:
                raise Refused({"t": "error", "msg": "That room is full."})
            used = {q.color for q in self.players.values()}
            color = next((c for c in COLORS if c not in used), random.choice(COLORS))
            p = Player(self.next_id, self.unique_name(name), color, queue, token or None, tab)
            self.next_id += 1
            self.players[p.id] = p
        if self.host not in self.players or not self.players[self.host].connected:
            self.host = p.id
        self.empty_since = None
        self.send(p, {"t": "welcome", "you": p.id, "code": self.code, "min": MIN_PLAYERS, "max": MAX_PLAYERS,
                      "w": W, "h": H, "ink": MAX_POINTS, "len": TEXT_LEN})
        if self.phase == "play":
            step = self.step
            self.check_step()  # they may be the only one here, with their page already in
            if self.phase == "play" and self.step == step:
                self.send_task(p)
        if self.phase in ("reveal", "album"):
            self.send_books(p)
        self.send_state()
        return p

    def leave(self, p, queue):
        if p.queue is not queue or not p.connected:
            return
        p.connected = False
        p.queue = None
        if not self.playing(p):
            self.players.pop(p.id, None)
        if self.host == p.id:
            nxt = next((q for q in self.players.values() if q.connected), None)
            self.host = nxt.id if nxt else self.host
        if not any(q.connected for q in self.players.values()):
            self.empty_since = time.monotonic()
        if self.phase == "play":
            self.check_step()  # the step may have been waiting only on them
        self.send_state()

    def unique_name(self, name, skip=None):
        taken = {q.name for q in self.players.values() if q is not skip}
        if name not in taken:
            return name
        n = 2
        while f"{name[:13]} {n}" in taken:
            n += 1
        return f"{name[:13]} {n}"

    # ------------------------------------------------------------ messages

    def handle(self, p, msg):
        t = msg.get("t")
        host = p.id == self.host
        if t == "timer" and host and self.phase == "lobby" and msg.get("v") in TIMERS:
            self.timer = msg["v"]
        elif t == "start" and host and self.phase == "lobby":
            self.start()
        elif t == "submit" and self.phase == "play" and msg.get("step") == self.step:
            self.submit(p, msg)
        elif t == "hurry" and host and self.phase == "play":
            self.finish_step()
        elif t == "next" and host and self.phase == "reveal":
            self.next_page()
        elif t == "again" and host and self.phase == "album":
            self.to_lobby()
        else:
            return
        self.send_state()

    # ------------------------------------------------------------ a game

    def start(self):
        seats = [p.id for p in self.players.values() if p.connected][:MAX_PLAYERS]
        if len(seats) < MIN_PLAYERS:
            return
        random.shuffle(seats)
        self.order = seats
        self.books = [[] for _ in seats]
        self.phase = "play"
        self.begin_step(0)

    def begin_step(self, step):
        self.step = step
        self.done = {}
        if self.timer == "off":
            self.deadline = None
            self.at(0, None)
        else:
            secs = TIMES[self.timer][self.kind()]
            self.deadline = time.monotonic() + secs
            self.at(secs + GRACE, self.times_up)
        for pid in self.order:
            self.send_task(self.players[pid])
        self.check_step()  # nobody connected to wait for?

    def send_task(self, p):
        """Tell a player their job this step: the page they're answering, or that they're done."""
        if not self.playing(p):
            return
        kind = self.kind()
        task = {"t": "task", "step": self.step, "kind": kind, "done": p.id in self.done}
        if kind == "write":
            task["ideas"] = random.sample(IDEAS, 3)
        else:
            page = self.books[self.book_of(p.id)][-1]
            task["page"] = {k: page[k] for k in ("k", "text", "strokes") if k in page}
        self.send(p, task)

    def submit(self, p, msg):
        if not self.playing(p) or p.id in self.done:
            return
        if self.kind() == "draw":
            page = {"k": "draw", "strokes": clean_drawing(msg.get("strokes"))}
        else:
            text = clean(msg.get("text"), TEXT_LEN)
            if not text:
                return
            page = {"k": "text", "text": text}
        self.done[p.id] = {**page, "by": p.id}
        self.check_step()

    def check_step(self):
        """Move on once everyone who's connected has handed in their page."""
        if self.phase == "play" and all(pid in self.done or not self.players[pid].connected for pid in self.order):
            if any(self.players[pid].connected for pid in self.order):
                self.finish_step()

    def times_up(self):
        # With everyone gone, wait for someone to come back rather than play the game out alone.
        if any(self.players[pid].connected for pid in self.order):
            self.finish_step()
            self.send_state()

    def finish_step(self):
        """End the step, standing in for anyone who hasn't handed in: a stock prompt, a blank
        sheet or a shrug."""
        kind = self.kind()
        for pid in self.order:
            if pid in self.done:
                page = self.done[pid]
            elif kind == "write":
                page = {"k": "text", "text": random.choice(IDEAS), "by": pid, "auto": True}
            elif kind == "draw":
                page = {"k": "draw", "strokes": [], "by": pid, "auto": True}
            else:
                page = {"k": "text", "text": "(no idea)", "by": pid, "auto": True}
            self.books[self.book_of(pid)].append(page)
        if self.step + 1 < len(self.order):
            self.begin_step(self.step + 1)
        else:
            self.phase = "reveal"
            self.reveal = [0, 1]
            self.deadline = None
            self.at(0, None)
            for p in self.players.values():
                self.send_books(p)

    def send_books(self, p):
        self.send(p, {"t": "books", "books": self.books})

    def next_page(self):
        book, shown = self.reveal
        if shown < len(self.books[book]):
            self.reveal = [book, shown + 1]
        elif book + 1 < len(self.books):
            self.reveal = [book + 1, 1]
        else:
            self.phase = "album"

    def to_lobby(self):
        self.phase = "lobby"
        self.order = []
        self.books = []
        self.done = {}
        for p in [p for p in self.players.values() if not p.connected]:
            del self.players[p.id]

    # ------------------------------------------------------------ what the browsers see

    def send_state(self):
        st = {
            "t": "state", "phase": self.phase, "host": self.host, "timer": self.timer,
            "players": [{"id": p.id, "name": p.name, "color": p.color, "on": p.connected,
                         "playing": self.playing(p), "done": p.id in self.done}
                        for p in self.players.values()],
            "order": self.order,
        }
        if self.phase == "play":
            st.update(step=self.step, steps=len(self.order), kind=self.kind(),
                      left=None if self.deadline is None else max(0, round(self.deadline - time.monotonic(), 1)))
        elif self.phase == "reveal":
            st["reveal"] = self.reveal
        for p in self.players.values():
            self.send(p, st)


ROOMS = Codes(ROOM_KEEP)
