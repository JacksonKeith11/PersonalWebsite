"""A Kingfall room: the browsers in it (each can bring up to four couch heroes), the lobby, and the
run (fights, then the Bonfire between them). Rooms by four-letter code (app/rooms.py)."""

import asyncio
import random
import logging
import time

from ..rooms import Codes, clean, push
from . import content as C
from .build import ATTRS, Build
from .content.upgrades import UPGRADES, offer as draw_offer
from .fight import TICK, Fight

log = logging.getLogger("kingfall")
ROOMS = Codes(keep=30 * 60)
MAX_HEROES = 4
LOOKS = ("knight", "pilgrim", "hunter", "sellsword")
# A run: two bosses from each tier, then a final. Only bosses that exist (content.BOSSES) are drawn,
# so tiers with none yet are skipped.
POOLS = {1: ["corvin", "mire", "bellwarden"], 2: ["headsmen", "wolf", "alchemist", "wyrm"], 3: ["mirror", "bastion", "moth"],
         4: ["king", "drake"]}
TIERS = [1, 1, 2, 2, 3, 3, 4]
SHOP = {"reroll": 30, "flask": 120, "ember": 150}
SWAP_AFTER = (2, 4)  # the weapon shrine is lit at the Bonfires after these fights


class Hero:
    """A hero for the whole run: who plays them and their build."""

    def __init__(self, hid, conn, slot, name, look, weapon, colour):
        self.id, self.conn, self.slot = hid, conn, slot
        self.name, self.look, self.weapon, self.colour = name, look, weapon, colour
        self.level = 1
        self.attrs = {"vig": 0, "end": 0, "mig": 0, "fin": 0, "arc": 0}
        self.ups = []           # [(upgrade id, rarity)]
        self.points = 0         # attribute points to spend
        self.offer = []         # upgrade cards on offer at the Bonfire
        self.picks = 0          # upgrades still to choose
        self.ready = False
        self.swap = False       # may change weapon at this Bonfire
        self._build = None
        self.flasks = self.build().stats["flasks"]
        self.hp = self.mhp()
        self.second_wind = True

    def build(self):
        if self._build is None: self._build = Build(self.attrs, self.ups)
        return self._build

    def changed(self):
        self._build = None

    def mhp(self):
        return max(20, round(self.build().stats["mhp"]))

    def max_flasks(self):
        return self.build().stats["flasks"]

    def wire(self):
        return {"id": self.id, "conn": self.conn.id, "slot": self.slot, "name": self.name, "look": self.look,
                "weapon": self.weapon, "colour": self.colour, "level": self.level, "attrs": self.attrs,
                "hp": self.hp, "mhp": self.mhp(), "flasks": self.flasks, "maxflasks": self.max_flasks(), "ups": self.ups,
                "points": self.points, "offer": self.offer, "picks": self.picks, "ready": self.ready, "swap": self.swap,
                "stats": self.build().client()}


class Conn:
    """One browser."""

    def __init__(self, cid, queue, token, tab):
        self.id, self.queue, self.token, self.tab = cid, queue, token, tab
        self.connected = True
        self.closing = False
        self.left_at = 0.0


class Room:
    def __init__(self, code, debug=False):
        self.code = code
        self.debug = debug
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
        self.run = []
        self.coins = 0
        self.bought = {}
        self.rng = random.Random()

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
            for b in self.fight.bodies:
                if b.move: self.send(c, b.move.wire({"art": b.art}))
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
        return {"t": "lobby", "state": self.state, "host": self.host, "stage": self.stage, "of": len(self.run), "run": self.run,
                "coins": self.coins, "prices": self.prices(),
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
        elif self.state == "bonfire" and h:
            self.bonfire(h, t, msg)
        elif t == "debugwin" and self.debug and self.fight:
            self.fight.die(now)
        elif self.fight and h:
            f = self.fight
            if t == "st": f.report(h.id, msg)
            elif t == "hit": f.hit_boss(h.id, msg, now)
            elif t == "hurt": f.hurt(h.id, msg, now)
            elif t == "drink": f.drink(h.id, now)
            elif t == "revive": f.revive(h.id, msg.get("who"), now)
            elif t == "dodge": f.dodged(h.id, msg, now)
            elif t == "perfect": f.perfect(h.id, now)
            elif t == "hitadd": f.hit_add(h.id, msg, now)

    # ------------------------------------------------------------------ the Bonfire
    def prices(self):
        return {k: v + (60 * self.bought.get(k, 0) if k != "reroll" else 0) for k, v in SHOP.items()}

    def bonfire(self, h, t, msg):
        if t == "attr" and h.points > 0 and msg.get("a") in ATTRS:
            h.attrs[msg["a"]] += 1; h.points -= 1; h.changed()
            h.hp = h.mhp()
        elif t == "pick" and h.offer and isinstance(msg.get("i"), int) and 0 <= msg["i"] < len(h.offer):
            uid, rarity = h.offer[msg["i"]]
            slot = UPGRADES[uid]["slot"]
            if slot: h.ups = [(u, r) for u, r in h.ups if UPGRADES[u]["slot"] != slot]
            h.ups.append((uid, rarity))
            h.picks -= 1
            h.offer = draw_offer(h, len(self.heroes), self.rng, self.stage) if h.picks > 0 else []
            h.changed(); h.hp = h.mhp(); h.flasks = h.max_flasks()
        elif t == "buy" and msg.get("item") in SHOP:
            item, price = msg["item"], self.prices()[msg["item"]]
            if self.coins < price: return
            if item == "reroll":
                if not h.offer: return
                h.offer = draw_offer(h, len(self.heroes), self.rng, self.stage)
            elif item == "flask":
                h.ups.append(("any_flask", "common")); h.changed(); h.flasks = h.max_flasks()
            elif item == "ember":
                h.picks += 1
                if not h.offer: h.offer = draw_offer(h, len(self.heroes), self.rng, self.stage)
            self.coins -= price
            if item != "reroll": self.bought[item] = self.bought.get(item, 0) + 1
        elif t == "weapon" and h.swap and msg.get("weapon") in C.WEAPONS and msg["weapon"] != h.weapon:
            h.weapon = msg["weapon"]
            h.ups = [(u, r) for u, r in h.ups if not UPGRADES[u]["weapon"]]  # the old weapon's Arts go with it
            h.changed(); h.swap = False
        elif t == "ready":
            h.ready = bool(msg.get("on", True))
        else:
            return
        if all(x.ready for x in self.heroes.values()):
            self.start_fight()
            return
        self.broadcast(self.lobby_wire())

    # ------------------------------------------------------------------ the run
    def start_run(self):
        self.stage = 0
        self.result = None
        self.coins = 0
        self.bought = {}
        used = set()
        self.run = []
        for tier in TIERS:
            pool = [b for b in POOLS[tier] if b in C.BOSSES and b not in used]
            if pool:
                b = self.rng.choice(pool)
                used.add(b); self.run.append(b)
        for h in self.heroes.values():
            h.level, h.points, h.picks, h.offer, h.ups, h.ready = 1, 0, 0, [], [], False
            h.attrs = {a: 0 for a in ATTRS}
            h.changed()
            h.flasks = h.max_flasks()
            h.hp = h.mhp()
            h.second_wind = True
        self.start_fight()

    def start_fight(self):
        self.state = "fight"
        for h in self.heroes.values(): h.ready = False
        self.fight = Fight(self, self.run[self.stage], list(self.heroes.values()), self.now())
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
                if n % 2 == 0 or any(b.move for b in f.bodies):
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
        tier = C.BOSSES[self.run[self.stage]]["tier"]
        self.fight = None
        if won and self.stage + 1 < len(self.run):
            self.stage += 1
            self.state = "bonfire"
            self.coins += 60 + 40 * tier
            for h in self.heroes.values():
                h.level += 1
                h.points += 1
                h.picks += 1
                h.offer = draw_offer(h, len(self.heroes), self.rng, self.stage)
                h.swap = self.stage in SWAP_AFTER
                h.ready = False
        else:
            self.state = "over"
            self.result = "won" if won else "lost"
        for h in self.heroes.values():
            h.hp = h.mhp()
            h.flasks = h.max_flasks()
        self.broadcast(self.lobby_wire())
