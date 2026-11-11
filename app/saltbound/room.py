"""Saltbound's rooms: who's connected, the lobby (claiming heroes, difficulty, saved runs), and
passing players' actions to their run.

A run always has three heroes. Each lobby slot holds a class and who plays it; the host picks
classes for empty slots, and on Start any slot nobody claimed goes to the host. In a run each
hero has a controller; if they disconnect the game simply waits (there are no timers), and the
host can hand the hero to someone else. Bots exist only for testing: a room made from a page with
`?bots` lets the host give slots to the bot.

The game is turn-based with no clock, so a room has no tick loop: it changes when a message comes
in, broadcasts the new state, and autosaves when a map turn or combat round has passed.
"""

import asyncio
import json
import logging
import secrets
import time

from ..rooms import Codes, clean, dumps, push
from . import world as Wd
from . import bot
from . import game as G
from . import save as S
from .classes import CLASSES
from .combat import Invalid

log = logging.getLogger("saltbound")

ROOM_KEEP = 60 * 60
MAX_PEOPLE = 8
BOT = "bot"
BOT_DELAY = 0.35
BOT_FIGHT_DELAY = 1.2  # each action plays out the moment it's placed; give it time to be seen
PING_GAP = 0.6  # seconds between one person's map pings
PING_KINDS = ("look", "go", "danger")


class Person:
    def __init__(self, pid, name, queue, token, tab):
        self.id = pid
        self.name = name
        self.queue = queue
        self.token = token
        self.tab = tab
        self.connected = True
        self.closing = False
        self.pinged = 0.0


class Room:
    def __init__(self, code, debug=False):
        self.code = code
        self.debug = debug
        self.people: dict[int, Person] = {}
        self.next_id = 1
        self.host = None
        self.slots = [{"cls": None, "pid": None} for _ in range(3)]
        self.diff = "normal"
        self.custom = None  # the host's custom sliders (G.CUSTOM), or None for the preset as it is
        self.game: G.Game | None = None
        self.run_id = None
        self.resume = None  # a loaded save waiting in the lobby: its state
        self.ctl = [None, None, None]  # hero -> person id (or BOT) during a run
        self.saved_key = None
        self.empty_since = None
        self.bot_task = None

    # ---------------------------------------------------------------- plumbing

    def send(self, p, data):
        if not p.connected or p.closing or p.queue is None:
            return
        if not push(p.queue, data, p.name, "saltbound"):
            p.closing = True

    def everyone(self, data):
        text = dumps(data)
        for p in self.people.values():
            self.send(p, text)

    def room_view(self):
        return {
            "code": self.code, "host": self.host, "debug": self.debug, "diff": self.diff, "custom": self.custom,
            # each slider's range and its default under the preset chosen (the lobby's Custom panel)
            "sliders": {k: [lo, hi, d if d is not None else {"rise": G.DIFFICULTY[self.diff]["rise"], "gold": G.START_GOLD,
                                                              "revives": G.DIFFICULTY[self.diff]["revives"]}[k]]
                        for k, (lo, hi, d) in G.CUSTOM.items()},
            "people": [{"id": p.id, "name": p.name, "on": p.connected} for p in self.people.values()],
            "slots": self.slots, "ctl": self.ctl, "playing": self.game is not None,
            "resume": self.resume_view(),
        }

    def resume_view(self):
        if not self.resume:
            return None
        st = self.resume
        return {"turn": st["turn"], "diff": st["diff"], "custom": st.get("custom"), "level": st["level"], "cleared": st["cleared"],
                "classes": [h["cls"] for h in st["heroes"]]}

    def broadcast(self):
        data = {"t": "state", "room": self.room_view(), "game": self.game.view() if self.game else None}
        self.everyone(data)

    def world_msg(self):
        w = self.game.s["world"]
        marks = sorted((int(t), p.get("region") or "peak") for t, p in w["places"].items() if p["kind"] in ("dungeon", "peak"))
        return {"t": "world", "w": w["w"], "h": w["h"], "elev": w["elev"], "bio": w["bio"], "reg": w["reg"],
                "peak": w["peak"], "start": w["start"], "seed": self.game.s["seed"],
                "cur": w.get("cur", {}), "reef": w.get("reef", []), "pool": w.get("pool", []),
                "landmarks": [{"tile": t, "region": r} for t, r in marks], "regions": Wd.regions(w),
                "sink": w.get("sink", []), "ice": w.get("ice", [])}

    # ---------------------------------------------------------------- joining and leaving

    def join(self, queue, name, token, tab):
        token, tab, name = clean(token, 40), clean(tab, 40), clean(name, 16) or "Sailor"
        p = next((q for q in self.people.values() if token and q.token == token), None)
        if p is not None and p.connected and p.tab != tab:
            p, token = None, token + ":" + tab  # a second tab of one browser is someone else
        if p is not None:
            if p.connected and p.queue is not None:
                p.queue.put_nowait(None)
            p.queue, p.tab, p.connected, p.closing, p.name = queue, tab, True, False, name
        else:
            if len(self.people) >= MAX_PEOPLE:
                raise Invalid("This room is full.")
            p = Person(self.next_id, name, queue, token, tab)
            self.next_id += 1
            self.people[p.id] = p
        if self.host is None or self.host not in self.people or not self.people[self.host].connected:
            self.host = p.id
        self.empty_since = None
        self.send(p, {"t": "welcome", "you": p.id, "code": self.code, "static": STATIC})
        self.send(p, {"t": "saves", "list": S.list_for(p.token.split(":")[0])})
        if self.game:
            self.send(p, self.world_msg())
        self.broadcast()
        return p

    def leave(self, p, queue):
        if p.queue is not queue:
            return
        p.connected = False
        p.queue = None
        if not self.game and not any(s["pid"] == p.id for s in self.slots):
            self.people.pop(p.id, None)
        if self.host == p.id:
            nxt = next((q for q in self.people.values() if q.connected), None)
            self.host = nxt.id if nxt else None
        if not any(q.connected for q in self.people.values()):
            self.empty_since = time.monotonic()
        self.broadcast()

    # ---------------------------------------------------------------- messages

    def handle(self, p, msg):
        t = msg.get("t")
        try:
            if t == "name":
                p.name = clean(msg.get("name"), 16) or p.name
            elif t == "saves":
                self.send(p, {"t": "saves", "list": S.list_for(p.token.split(":")[0])})
                return
            elif t == "delsave":
                S.delete(clean(msg.get("id"), 40), p.token.split(":")[0])
                self.send(p, {"t": "saves", "list": S.list_for(p.token.split(":")[0])})
                return
            elif t == "ping":
                self.ping(p, msg)
                return
            elif self.game is None:
                self.lobby(p, t, msg)
            else:
                self.guarded(lambda: self.play(p, t, msg), f"{t} from {p.name}")
        except Invalid as e:
            self.send(p, {"t": "err", "msg": str(e)})
            return
        except Exception:
            # outside a game move (the lobby, saves): log it rather than let the socket drop the player
            log.exception("saltbound: %s from %s failed", t, p.name)
            self.send(p, {"t": "err", "msg": "Something went wrong. Try again."})
            return
        self.after()

    def ping(self, p, msg):
        """A mark on the map for everyone ("look here", "let's go here", "careful"). Nothing in the game
        changes and nothing is saved: it's passed straight on, at most one per person every `PING_GAP`."""
        tile, kind = msg.get("tile"), msg.get("kind")
        if self.game is None or not isinstance(tile, int) or not 0 <= tile < Wd.W * Wd.H or kind not in PING_KINDS:
            return
        now = time.monotonic()
        if now - p.pinged < PING_GAP:
            return
        p.pinged = now
        heroes = [h for h, c in enumerate(self.ctl) if c == p.id]
        self.everyone({"t": "ping", "tile": tile, "kind": kind, "from": p.id, "name": p.name,
                       "h": heroes[0] if heroes else None})

    def guarded(self, fn, what):
        """Run a change to the game; if it fails unexpectedly (a bug, not a rule), log it, put the game
        back as it was before the change (a half-applied move would corrupt the run) and say so."""
        g = self.game
        snap = json.dumps(g.s)
        try:
            return fn()
        except Invalid:
            raise
        except Exception:
            log.exception("saltbound: %s failed in run %s; rolled back", what, self.run_id)
            self.game = G.Game(json.loads(snap))
            raise Invalid("Something went wrong with that move, so it was undone. Try something else.")

    def host_only(self, p):
        if p.id != self.host:
            raise Invalid("Only the host can do that.")

    def lobby(self, p, t, msg):
        i = msg.get("slot")
        slot = self.slots[i] if isinstance(i, int) and 0 <= i < 3 else None
        if t == "claim":
            if slot is None:
                raise Invalid("Pick a hero.")
            if slot["pid"] not in (None, p.id):
                raise Invalid("Someone's already playing that hero.")
            cls = msg.get("cls")
            if self.resume:
                cls = slot["cls"]
            elif cls not in CLASSES or any(s["cls"] == cls and s is not slot for s in self.slots):
                raise Invalid("Pick a class nobody else has.")
            slot["cls"], slot["pid"] = cls, p.id
        elif t == "unclaim":
            if slot is None or slot["pid"] != p.id:
                raise Invalid("That isn't yours.")
            slot["pid"] = None
        elif t == "setcls":
            if slot is None or self.resume:
                raise Invalid("Pick a hero.")
            if slot["pid"] not in (None, p.id, BOT) and p.id != self.host:
                raise Invalid("That hero is someone else's.")
            cls = msg.get("cls")
            if cls is not None and (cls not in CLASSES or any(s["cls"] == cls and s is not slot for s in self.slots)):
                raise Invalid("Pick a class nobody else has.")
            slot["cls"] = cls
        elif t == "assign":
            self.host_only(p)
            who = msg.get("pid")
            if slot is None:
                raise Invalid("Pick a hero.")
            if who == BOT and not self.debug:
                raise Invalid("Bots are only for testing.")
            if who not in (None, BOT) and who not in self.people:
                raise Invalid("Nobody by that name is here.")
            slot["pid"] = who
        elif t == "diff":
            self.host_only(p)
            if msg.get("d") not in G.DIFFICULTY or self.resume:
                raise Invalid("Pick a difficulty.")
            self.diff = msg["d"]
        elif t == "custom":
            # the custom sliders on top of the preset: {} or None turns them off
            self.host_only(p)
            if self.resume:
                raise Invalid("A saved voyage keeps its own difficulty.")
            c = msg.get("c")
            self.custom = G.clean_custom(c) if isinstance(c, dict) and c else None
        elif t == "resume":
            self.host_only(p)
            rid = clean(msg.get("id"), 40)
            try:
                st = S.load(rid, p.token.split(":")[0])
            except S.TooOld as e:
                raise Invalid(str(e))
            if st is None:
                raise Invalid("That save is gone.")
            self.resume, self.run_id = st, rid
            self.diff = st["diff"]
            self.slots = [{"cls": h["cls"], "pid": None} for h in st["heroes"]]
        elif t == "fresh":
            self.host_only(p)
            self.resume = self.run_id = None
            self.slots = [{"cls": None, "pid": None} for _ in range(3)]
        elif t == "start":
            self.host_only(p)
            self.start()
        else:
            raise Invalid("Not now.")

    def start(self):
        classes = [s["cls"] for s in self.slots]
        if None in classes:
            raise Invalid("Every hero needs a class.")
        if len(set(classes)) != 3:
            raise Invalid("Each hero needs a different class.")
        self.ctl = [s["pid"] if s["pid"] in self.people or s["pid"] == BOT else self.host for s in self.slots]
        if self.resume:
            self.game = G.Game(self.resume)
            self.resume = None
        else:
            seed = secrets.randbits(32)
            names = [self.people[c].name if c in self.people and self.ctl.count(c) == 1 else None for c in self.ctl]
            self.game = G.Game.new(seed, classes, self.diff, names, custom=self.custom)
            self.run_id = secrets.token_hex(8)
        self.saved_key = None
        self.everyone(self.world_msg())

    def play(self, p, t, msg):
        g = self.game
        if t == "assign":
            self.host_only(p)
            h, who = msg.get("h"), msg.get("pid")
            if not isinstance(h, int) or not 0 <= h < 3:
                raise Invalid("Pick a hero.")
            if who == BOT and not self.debug:
                raise Invalid("Bots are only for testing.")
            if who != BOT and who not in self.people:
                raise Invalid("Pick someone who's here.")
            self.ctl[h] = who
            return
        if t == "quit":
            self.host_only(p)
            self.autosave(force=True)
            self.game = None
            self.resume = None
            self.slots = [{"cls": None, "pid": None} for _ in range(3)]
            self.ctl = [None, None, None]
            return
        h = msg.get("h")
        if not isinstance(h, int) or not 0 <= h < 3:
            raise Invalid("Which hero?")
        if self.ctl[h] != p.id:
            raise Invalid("That's not your hero.")
        g.act(h, msg)

    # ---------------------------------------------------------------- after every change

    def after(self):
        self.autosave()
        self.broadcast()
        self.kick_bots()

    def autosave(self, force=False):
        g = self.game
        if not g:
            return
        if g.s["phase"] == "end":
            if self.run_id:
                tokens = self.tokens()
                for tok in tokens:
                    S.delete(self.run_id, tok)
                self.run_id = None
            return
        f = g.s["fight"]
        key = (g.s["turn"], g.s["phase"], f["id"] if f else None, f["round"] if f else None)
        if key == self.saved_key and not force:
            return
        self.saved_key = key
        try:
            st = g.s
            classes = ", ".join(CLASSES[h["cls"]]["name"] for h in st["heroes"])
            where = " · mid-fight" if f else ""
            S.save(self.run_id, self.tokens(), g, f"{classes} · {st['diff'].title()}{' (custom)' if st.get('custom') else ''} · turn {st['turn']}, level {st['level']}, "
                                                    f"{len(st['cleared'])} of 3 cleared{where}")
        except Exception:
            log.exception("saltbound: saving run %s failed", self.run_id)

    def tokens(self):
        out = set()
        for c in self.ctl:
            if c in self.people and self.people[c].token:
                out.add(self.people[c].token.split(":")[0])
        return sorted(out)

    def kick_bots(self):
        if not self.game or self.bot_task is not None:
            return
        if not any(self.ctl[h] == BOT for h in self.game.waiting()) and not self.spirit_bots():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        delay = BOT_FIGHT_DELAY if self.game.s["phase"] == "fight" else BOT_DELAY
        self.bot_task = loop.call_later(delay, self.bot_step)

    def spirit_bots(self):
        g = self.game
        f = g.s["fight"]
        return bool(f) and any(self.ctl[int(h)] == BOT and not sp["used"] for h, sp in f["spirit"].items())

    def bot_step(self):
        self.bot_task = None
        if not self.game:
            return
        try:
            acted = self._bot_step()
        except Exception:
            # never leave the bots stalled: log it, and the next kick tries again (the failing bot readies)
            log.exception("saltbound: a bot step failed in run %s", self.run_id)
            acted = self._bot_fallback()
        if acted:
            self.after()

    def _bot_fallback(self):
        g = self.game
        for h in [h for h in g.waiting() if self.ctl[h] == BOT]:
            try:
                self.guarded(lambda: g.act(h, {"t": "fready"} if g.s["phase"] == "fight" else {"t": "ready"}), f"bot {h} readying")
                return True
            except Invalid:
                continue
        return False

    def _bot_step(self):
        g = self.game
        hs = [h for h in g.waiting() if self.ctl[h] == BOT]
        # spirit dice go first, while the heroes fighting can still use them
        give = [int(h) for h, sp in g.s["fight"]["spirit"].items() if self.ctl[int(h)] == BOT and not sp["used"]] \
            if self.spirit_bots() else []
        acted = False
        for h in give + bot.order(g, hs):
            msg = bot.decide(g, h)
            if msg is None:
                continue
            try:
                self.guarded(lambda: g.act(h, msg), f"bot {h} {msg.get('t')}")
            except Invalid:
                g = self.game  # rolled back, perhaps
                try:
                    self.guarded(lambda: g.act(h, {"t": "fready"} if g.s["phase"] == "fight" else {"t": "ready"}), f"bot {h} readying")
                except Invalid:
                    continue
            acted = True
            break
        return acted


STATIC = G.static()

ROOMS = Codes(ROOM_KEEP)
