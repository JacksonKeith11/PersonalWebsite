"""A Kingfall room: the browsers in it (each can bring up to four couch heroes), the lobby, and the
run (fights, then the Bonfire between them). Rooms by four-letter code (app/rooms.py)."""

import asyncio
import logging
import time

from ..rooms import Codes, clean, push
from . import content as C
from .fight import TICK, Fight

log = logging.getLogger("kingfall")
ROOMS = Codes(keep=30 * 60)
MAX_HEROES = 4
LOOKS = ("knight", "pilgrim", "hunter", "sellsword")
RUN = ["corvin"]  # the bosses a run fights, in order (the full game draws them by tier)


class Hero:
    """A hero for the whole run: who plays them and their build."""

    def __init__(self, hid, conn, slot, name, look, weapon, colour):
        self.id, self.conn, self.slot = hid, conn, slot
        self.name, self.look, self.weapon, self.colour = name, look, weapon, colour
        self.level = 1
        self.attrs = {"vig": 0, "end": 0, "mig": 0, "fin": 0, "arc": 0}
        self.ups = []
        self.flasks = C.HERO["flask"]["charges"]
        self.hp = self.mhp()
        self.second_wind = True

    def mhp(self):
        return C.HERO["hp"] + 12 * self.attrs["vig"]

    def might(self):
        return 1.0 + 0.06 * self.attrs["mig"]

    def guard_mult(self):
        return 1.0

    def wire(self):
        return {"id": self.id, "conn": self.conn.id, "slot": self.slot, "name": self.name, "look": self.look,
                "weapon": self.weapon, "colour": self.colour, "level": self.level, "attrs": self.attrs,
                "hp": self.hp, "mhp": self.mhp(), "flasks": self.flasks}


class Conn:
    """One browser."""

    def __init__(self, cid, queue, token, tab):
        self.id, self.queue, self.token, self.tab = cid, queue, token, tab
        self.connected = True
        self.closing = False
        self.left_at = 0.0


class Room:
    def __init__(self, code):
        self.code = code
        self.epoch = time.monotonic()
        self.conns = {}
        self.heroes = {}
        self.host = None
        self.next_id = 1
        self.state = "lobby"
        self.stage = 0
        self.fight = None
        self.task = None
        self.empty_since = None
        self.result = None

    def now(self):
        return time.monotonic() - self.epoch

    # ------------------------------------------------------------------ connections
    def join(self, queue, token, tab):
        token, tab = clean(token, 40), clean(tab, 40)
        c = next((q for q in self.conns.values() if token and q.token == token), None)
        if c is not None and c.connected and c.tab != tab:
            c, token = None, token + ":" + tab  # a second tab of one browser is someone else
            c = next((q for q in self.conns.values() if q.token == token), None)
        if c is not None:
            if c.connected and c.queue is not queue:
                push(c.queue, {"t": "replaced"}, game="kingfall")
            c.queue, c.tab, c.connected, c.closing = queue, tab, True, False
        else:
            c = Conn(self.next_id, queue, token, tab)
            self.next_id += 1
            self.conns[c.id] = c
        if self.host is None or self.host not in self.conns or not self.conns[self.host].connected:
            self.host = c.id
        self.empty_since = None
        self.send(c, {"t": "welcome", "you": c.id, "code": self.code, "data": C.client(), "st": round(self.now(), 3)})
        self.send(c, self.lobby_wire())
        if self.fight:
            self.send(c, self.fight.start_wire())
            if self.fight.move: self.send(c, self.fight.move.wire())
        return c

    def leave(self, c, queue):
        if c.queue is not queue: return
        c.connected = False
        c.left_at = time.monotonic()
        if self.state == "lobby":
            for h in [h for h in self.heroes.values() if h.conn is c]:
                del self.heroes[h.id]
        if self.host == c.id:
            alive = [q for q in self.conns.values() if q.connected]
            self.host = alive[0].id if alive else None
        if not any(q.connected for q in self.conns.values()):
            self.empty_since = time.monotonic()
            if self.task: self.task.cancel(); self.task = None
            self.state, self.fight = "lobby", None
            self.heroes = {k: h for k, h in self.heroes.items() if h.conn.connected}
        self.broadcast(self.lobby_wire())

    def send(self, c, msg):
        if c.connected and not c.closing:
            if not push(c.queue, msg, who=str(c.id), game="kingfall"):
                c.closing = True

    def broadcast(self, msg):
        for c in self.conns.values():
            self.send(c, msg)

    def lobby_wire(self):
        return {"t": "lobby", "state": self.state, "host": self.host, "stage": self.stage, "of": len(RUN),
                "heroes": [h.wire() for h in sorted(self.heroes.values(), key=lambda h: h.id)],
                "conns": [c.id for c in self.conns.values() if c.connected], "result": self.result}

    # ------------------------------------------------------------------ messages
    def handle(self, c, msg):
        t = msg.get("t")
        now = self.now()
        if t == "ping":
            self.send(c, {"t": "pong", "c": msg.get("c"), "s": round(now, 4)})
            return
        h = self.heroes.get(msg.get("h")) if "h" in msg else None
        if h is not None and h.conn is not c: return
        if t == "add" and self.state == "lobby":
            if len(self.heroes) >= MAX_HEROES: return
            slot = msg.get("slot") if isinstance(msg.get("slot"), int) else 0
            if any(x.conn is c and x.slot == slot for x in self.heroes.values()): return
            used = {x.colour for x in self.heroes.values()}
            colour = next(i for i in range(4) if i not in used)
            look = msg.get("look") if msg.get("look") in LOOKS else LOOKS[colour]
            weapon = msg.get("weapon") if msg.get("weapon") in C.WEAPONS else "sword"
            hero = Hero(self.next_id, c, slot, clean(msg.get("name"), 16) or f"Hero {colour + 1}", look, weapon, colour)
            self.next_id += 1
            self.heroes[hero.id] = hero
            self.broadcast(self.lobby_wire())
        elif t == "set" and h and self.state == "lobby":
            if msg.get("look") in LOOKS: h.look = msg["look"]
            if msg.get("weapon") in C.WEAPONS: h.weapon = msg["weapon"]
            if msg.get("name") is not None: h.name = clean(msg.get("name"), 16) or h.name
            self.broadcast(self.lobby_wire())
        elif t == "drop" and h and self.state == "lobby":
            del self.heroes[h.id]
            self.broadcast(self.lobby_wire())
        elif t == "start" and c.id == self.host and self.state in ("lobby", "over") and self.heroes:
            self.start_run()
        elif self.fight and h:
            f = self.fight
            if t == "st": f.report(h.id, msg)
            elif t == "hit": f.hit_boss(h.id, msg, now)
            elif t == "hurt": f.hurt(h.id, msg, now)
            elif t == "drink": f.drink(h.id, now)
            elif t == "revive": f.revive(h.id, msg.get("who"), now)

    # ------------------------------------------------------------------ the run
    def start_run(self):
        self.stage = 0
        self.result = None
        for h in self.heroes.values():
            h.flasks = C.HERO["flask"]["charges"]
            h.hp = h.mhp()
            h.second_wind = True
        self.start_fight()

    def start_fight(self):
        self.state = "fight"
        self.fight = Fight(self, RUN[self.stage], list(self.heroes.values()), self.now())
        self.broadcast(self.lobby_wire())
        self.broadcast(self.fight.start_wire())
        if not self.task:
            self.task = asyncio.get_event_loop().create_task(self.loop())

    async def loop(self):
        try:
            n = 0
            while self.fight:
                now = self.now()
                f = self.fight
                f.tick(now)
                n += 1
                if n % 2 == 0 or f.move:
                    self.broadcast(f.snapshot(now))
                if f.over == "won" and now >= f.until:
                    self.end_fight(True)
                elif f.over == "lost":
                    await asyncio.sleep(3.0)
                    self.end_fight(False)
                await asyncio.sleep(TICK)
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception("kingfall loop")
        finally:
            self.task = None

    def end_fight(self, won):
        self.fight = None
        if won and self.stage + 1 < len(RUN):
            self.stage += 1
            self.state = "bonfire"
        else:
            self.state = "over"
            self.result = "won" if won else "lost"
        for h in self.heroes.values():
            h.hp = h.mhp()
            h.flasks = C.HERO["flask"]["charges"]
        self.broadcast(self.lobby_wire())
