"""Holdfast: co-op tower defence for 1-4 players.

Everyone builds on one map, each from their own purse; bounties are shared out equally between
whoever is connected, and gold can be handed to another player. Thirty waves; twenty lives between
everyone. The server runs the whole fight (`Room.advance`), fifteen steps a second, and sends
snapshots ten times a second; the browser only draws and asks to build.

Arrows, bolts and shells are real projectiles (`Shot`): they fly, aimed where their target will be,
can miss, and go through `pierce` enemies. Trappers lay piles on the road (`Trap`), Workshops build
little turrets (`Sentry`), and players can buy one-use items. Enemies can be immune to damage types
and burst into smaller ones; every tenth wave brings a boss, or a boss event's boss.

After wave 30 the host may carry on into endless waves. The game is saved at the start of every
build phase (save.py), can be resumed from the lobby, and how far it got goes into the records.
"""

import asyncio
import logging
import math
import random
import secrets
import time

from ..rooms import Codes, Refused, clean, dumps, hang_up, push
from . import data as D
from . import save as SAVE

log = logging.getLogger("holdfast")

STEP = 1 / 15  # one step of the fight
SNAP_EVERY = 0.1
MAX_SHOTS = 80  # instant shots (auras, lightning) drawn a snapshot, at most
MAX_FLYING = 160  # new projectiles drawn a snapshot, at most (the rest still fly, unseen)
MAX_PLAYERS = 4
MAX_IN_ROOM = 10
COLORS = ["#e8552f", "#3f8fe8", "#e8b923", "#4fb85f"]
ROOM_KEEP = 30 * 60
SPEEDS = (1, 2, 3)
GIFT = 25
TARGETS = ("first", "last", "strong", "close")  # which enemy in reach a tower aims at
UNDO = 5  # real seconds in which a build or upgrade can be taken back for a full refund
LOB_TIME = 0.9  # seconds a lobbed shell is in the air
SUBSTEP = 0.25  # projectiles move at most this far between looks for something to hit
HIT_PAD = 0.12  # a projectile hits an enemy within its size plus this
TRAP_REACH = 0.4  # an enemy this near a spike or mine pile sets it off
EVENT_BOSSES = ("gravewarden", "stormhulk", "ironmaw")
TRAP_CODES = {"spike": 0, "mine": 1, "tar": 2}


def where(route, d):
    """The point `d` along a route, and the direction it heads there."""
    for i in range(1, len(route)):
        if route[i][1] > d:
            break
    (x0, y0), d0 = route[i - 1]
    (x1, y1), d1 = route[i]
    seg = d1 - d0 or 1.0
    u = min(1.0, max(0.0, (d - d0) / seg))
    return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, (x1 - x0) / seg, (y1 - y0) / seg


class Player:
    def __init__(self, pid, name, color, queue, token, tab):
        self.id, self.name, self.color = pid, name, color
        self.queue, self.token, self.tab = queue, token, tab
        self.connected = True
        self.closing = False
        self.seated = True
        self.reset()

    def reset(self):
        self.gold = 0.0
        self.kills = 0
        self.dmg = 0.0
        self.spent = 0
        self.ready = False
        self.items = {}  # item -> fight time it can be used again


class Tower:
    def __init__(self, tid, kind, x, y, owner):
        self.id, self.kind, self.x, self.y, self.owner = tid, kind, x, y, owner
        self.tiers = [0, 0]  # tiers bought on each path
        self.first = None  # the path bought first (it's the main one on a tie)
        self.spent = D.TOWERS[kind]["cost"]
        self.cool = 0.3
        self.boost = self.reach = self.power = 0.0  # from support towers nearby
        self.unlock = False  # hurts every type, thanks to a support tower nearby
        self.kills = 0
        self.dmg = 0.0
        self.stats = D.stats(kind)
        self.target = "first"
        self.sees = False  # can it target Ghosts?
        self.cd = 0.0  # seconds of fighting before its ability is ready again
        self.overdrive = (0.0, 1.0)  # (fight time it lasts until, how much faster)
        self.dazed = 0.0  # fight time until which a boss has knocked it out
        self.undo = None  # (monotonic time it expires, who paid, "build" or "up", cost, path)
        self.spots = (None, [])  # (reach, road points in reach): where a trapper lays piles

    @property
    def credit(self):
        return self

    @property
    def draw_id(self):
        return self.id

    @property
    def path(self):
        """The main path, or None before any upgrade."""
        return D.main_path(self.tiers, self.first)

    @property
    def tier(self):
        """Tiers on the main path."""
        main = self.path
        return 0 if main is None else self.tiers[main]

    def restat(self):
        self.stats = D.stats(self.kind, self.tiers, self.first)

    @property
    def range(self):
        return self.stats["range"] * (1 + self.reach)

    @property
    def ability(self):
        if self.tier >= D.EVOLUTION:
            return D.TOWERS[self.kind]["paths"][self.path]["tiers"][D.EVOLUTION - 1].get("ability")
        return None

    def view(self):
        undo = None
        if self.undo and self.undo[0] > time.monotonic():
            undo = [self.undo[1], round(self.undo[0] - time.monotonic(), 1)]
        return {"id": self.id, "k": self.kind, "p": self.path, "n": self.tier, "c": list(self.tiers),
                "f": self.first, "x": self.x, "y": self.y, "o": self.owner, "s": self.spent, "kills": self.kills,
                "dmg": round(self.dmg), "tg": self.target, "un": undo, "cs": self.sees, "ul": self.unlock}


class Sentry:
    """A little turret a Workshop builds (or a Hired Bow): it fights for a while, then falls apart.
    What it does is credited to its workshop."""

    kind = "workshop"
    target = "first"
    boost = 0.0
    dazed = 0.0

    def __init__(self, sid, x, y, stats, parent, until):
        self.id, self.x, self.y, self.stats, self.parent, self.until = sid, x, y, stats, parent, until
        self.cool = 0.4

    @property
    def credit(self):
        return self.parent

    @property
    def draw_id(self):
        return self.parent.id if self.parent else 0

    @property
    def range(self):
        return self.stats["range"]

    @property
    def sees(self):
        return bool(self.stats.get("detect") or self.stats["mode"] == "aura")

    @property
    def power(self):
        return self.parent.power if self.parent else 0.0

    @property
    def unlock(self):
        return self.parent.unlock if self.parent else False


class Shot:
    """A projectile in flight."""

    __slots__ = ("id", "x", "y", "vx", "vy", "left", "pierce", "hit", "st", "src", "splash", "lob", "tx", "ty")

    def __init__(self, sid, x, y, vx, vy, left, st, src):
        self.id, self.x, self.y, self.vx, self.vy, self.left, self.st, self.src = sid, x, y, vx, vy, left, st, src
        self.pierce = st.get("pierce", 1)
        self.hit = set()
        self.splash = st["mode"] == "splash"
        self.lob = False
        self.tx = self.ty = 0.0


class Trap:
    """A pile on the road: spikes (hurt `hits` enemies), a mine (bursts on the first) or tar (slows)."""

    def __init__(self, tid, kind, x, y, st, src, until):
        self.id, self.kind, self.x, self.y, self.st, self.src, self.until = tid, kind, x, y, st, src, until
        self.hits = st.get("hits", 1)
        self.hit = set()


class Enemy:
    def __init__(self, eid, kind, wave, mult, route, length, tier=1):
        e = D.ENEMIES[kind]
        self.id, self.kind = eid, kind
        self.event = e.get("event", False)
        self.tier = tier
        grow = 1 + D.BOSS_TIER_HP * (tier - 1) if self.event else 1
        self.max = self.hp = e["hp"] * D.health(wave) * mult * grow
        self.speed = e["speed"]
        self.size = e.get("size", 0.3)
        self.armor = e.get("armor", 0) * (1 + wave / 15)
        self.air = e.get("air", False)
        self.bounty = e["bounty"] * D.bounty(wave) * (tier if self.event else 1)
        self.lives = e.get("lives", 1)
        self.route, self.length = route, length
        self.d = 0.0  # how far along the route
        self.x, self.y = route[0][0]
        self.slow, self.slow_for, self.brittle = 0.0, 0.0, 0.0
        self.stun = 0.0  # seconds left stopped dead
        self.burn, self.burn_for, self.burner = 0.0, 0.0, None  # damage a second, for how long, from which tower
        self.boss = e.get("boss", False)
        self.big = self.boss or e.get("blimp", False)
        self.camo = e.get("camo", False)
        self.immune = set(e.get("immune", ()))
        self.heal = e.get("heal", 0.0)
        self.children = e.get("children", [])
        self.summon, self.every = e.get("summon", 0), e.get("every", 0)
        self.summon_t = self.every
        self.zap_t = e.get("zap", 0)
        self.skulls = list(e.get("skulls", []))
        self.move = e.get("move")
        self.shield = 0.0  # fight time until which nothing can hurt it
        self.shell = 0.0  # damage soaked up before its health
        self.charge = 0.0  # fight time until which it charges
        self.wave = wave
        self.taken = 0.0  # damage since the last snapshot (the browser floats it up)


def make_route(points):
    """A path as [((x, y), distance so far)] for walking along."""
    out, d = [(tuple(map(float, points[0])), 0.0)], 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        d += math.hypot(x1 - x0, y1 - y0)
        out.append(((float(x1), float(y1)), d))
    return out, d


class Room:
    def __init__(self, code):
        self.code = code
        self.players: dict[int, Player] = {}
        self.next_id = 1
        self.host = None
        self.map = "meadow"
        self.diff = "normal"
        self.bosses = "warlord"
        self.phase = "lobby"  # lobby, play, won, lost
        self.speed = 1
        self.saving = True  # the simulator turns saving and records off
        self.task = None
        self.empty_since = None
        self.rng = random.Random()
        self.clear()

    def clear(self):
        self.towers: dict[int, Tower] = {}
        self.at = {}  # (x, y) -> tower
        self.enemies: list[Enemy] = []
        self.spawns = []  # (time, kind, route index), soonest last
        self.wave = 0
        self.wave_t = 0.0  # seconds into the wave
        self.fighting = False
        self.next_in = 0.0  # seconds until the next wave starts, between waves
        self.lives = D.LIVES
        self.shots = []  # instant shots (auras, lightning) since the last snapshot: [tower id, from x, from y, points...]
        self.flying: list[Shot] = []
        self.launched = []  # projectiles fired since the last snapshot: [id, tower id, style, x, y, vx, vy, seconds]
        self.landed = []  # ids of drawn projectiles that stopped since the last snapshot
        self.drawn = set()  # ids of projectiles the browsers were told about
        self.booms = []  # blasts since the last snapshot: [x, y, radius, style]
        self.traps: list[Trap] = []
        self.sentries: list[Sentry] = []
        self.kills = []  # towers that have killed something since the last snapshot
        self.next_tower = self.next_enemy = self.next_shot = self.next_trap = self.next_sentry = 1
        self.routes = []
        self.flights = []
        self.since_snap = 0.0
        self.dirty = False
        self.buildable = set()
        self.road_tiles = set()
        self.road_pts = []  # points every quarter tile along the roads, on the board
        self.roadside = []  # off-road tiles beside the road (where sentries go)
        self.fight_t = 0.0  # seconds spent fighting, all game (ability cooldowns and effects run on it)
        self.rally = (0.0, 1.0)  # (fight time until, how much faster every tower fires)
        self.mark = (0.0, 0.0)  # (until, extra damage every enemy takes)
        self.bounty_up = (0.0, 0.0)  # (until, extra a kill pays)
        self.unmake = 0.0  # fight time until which enemies have no immunities or armour
        self.born = []  # enemies born mid-step (split, summoned), joined at the end of it
        self.effects = []  # abilities, items and boss moves since the last snapshot: [tower id, what, points...]
        self.leaks = {}  # wave -> lives lost in it
        self.retired = []  # towers sold this game, for the end summary: (name, owner, kills, dmg)
        self.endless = False
        self.game_id = None
        self.summary = None  # the end-of-game summary
        self.record_new = False

    # ------------------------------------------------------------ plumbing

    def send(self, p, data):
        if not p.connected or p.closing or p.queue is None:
            return
        if not push(p.queue, data, p.name, "holdfast"):
            p.closing = True

    def everyone(self, data):
        text = dumps(data)
        for p in self.players.values():
            self.send(p, text)

    def humans(self):
        return [p for p in self.players.values() if p.connected]

    def crew(self):
        """Who's playing and here: they share the bounties."""
        return [p for p in self.players.values() if p.seated and p.connected]

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
            color = next((c for c in COLORS if c not in used), "#8a8580")
            p = Player(self.next_id, self.unique_name(name), color, queue, token or None, tab)
            p.seated = sum(q.seated for q in self.players.values()) < MAX_PLAYERS
            self.next_id += 1
            self.players[p.id] = p
        if self.host not in self.players or not self.players[self.host].connected:
            self.host = p.id
        self.empty_since = None
        self.send(p, {"t": "welcome", "you": p.id, "code": self.code, "towers": D.TOWERS, "enemies": D.ENEMIES,
                      "kinds": D.KINDS, "cols": D.COLS, "rows": D.ROWS, "waves": D.WAVES, "gift": GIFT,
                      "sell": D.SELL_BACK, "max": MAX_PLAYERS, "targets": TARGETS, "undo": UNDO,
                      "items": D.ITEMS, "bosses": D.BOSSES, "evolution": D.EVOLUTION, "cross_max": D.CROSS_MAX,
                      "cross_mul": sorted(D.CROSS_MUL), "cross_add": sorted(D.CROSS_ADD),
                      "maps": {k: {"name": m["name"], "blurb": m["blurb"]} for k, m in D.MAPS.items()}})
        if self.phase != "lobby":
            self.send_map(p)
        self.send_saves(p)
        self.send_state()
        if self.task is None:
            self.task = asyncio.get_running_loop().create_task(self.run())
        return p

    def leave(self, p, queue):
        if p.queue is not queue or not p.connected:
            return
        p.connected = False
        p.queue = None
        if self.phase == "lobby" or not p.seated:
            self.players.pop(p.id, None)
        if self.host == p.id:
            nxt = next(iter(self.humans()), None)
            self.host = nxt.id if nxt else self.host
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
        if self.phase == "lobby":
            if t == "set" and host:
                if msg.get("map") in D.MAPS:
                    self.map = msg["map"]
                if msg.get("diff") in D.DIFFICULTY:
                    self.diff = msg["diff"]
                if msg.get("bosses") in D.BOSSES:
                    self.bosses = msg["bosses"]
            elif t == "start" and host:
                self.start()
            elif t == "resume" and host:
                if not self.resume(p, clean(msg.get("id"), 40)):
                    self.send(p, {"t": "note", "msg": "That saved game can't be loaded any more."})
                    self.send_saves(p)
                    return
            elif t == "forget":
                SAVE.forget(clean(msg.get("id"), 40), p.token)
                self.send_saves(p)
                return
            else:
                return
        elif self.phase == "play" and p.seated:
            if t == "build":
                self.build(p, msg.get("k"), msg.get("x"), msg.get("y"))
            elif t == "up":
                self.upgrade(p, self.towers.get(msg.get("id")), msg.get("path"))
            elif t == "sell":
                self.sell(p, self.towers.get(msg.get("id")))
            elif t == "give":
                to = self.players.get(msg.get("to"))
                if to and to is not p and to.seated and p.gold >= GIFT:
                    p.gold -= GIFT
                    to.gold += GIFT
            elif t == "ready" and not self.fighting:
                p.ready = True
                if all(q.ready for q in self.crew()):
                    self.next_in = min(self.next_in, 0.5)
            elif t == "speed" and host and msg.get("v") in SPEEDS:
                self.speed = msg["v"]
            elif t == "target" and msg.get("v") in TARGETS and msg.get("id") in self.towers:
                self.towers[msg["id"]].target = msg["v"]
            elif t == "ability":
                if not self.use_ability(self.towers.get(msg.get("id"))):
                    return
            elif t == "item":
                if not self.use_item(p, msg.get("k"), msg.get("x"), msg.get("y")):
                    return
            elif t == "undo":
                self.undo(p, self.towers.get(msg.get("id")))
            else:
                return
        elif t == "endless" and host and self.phase == "won" and not self.endless:
            self.endless = True
            self.phase = "play"
            self.summary = None
            self.next_in = D.BUILD_TIME[1]
        elif t == "again" and host and self.phase in ("won", "lost"):
            self.phase = "lobby"
            self.summary = None
            for q in [q for q in self.players.values() if not q.connected]:
                del self.players[q.id]
            for i, q in enumerate(self.players.values()):
                q.seated = i < MAX_PLAYERS
        else:
            return
        self.send_state()

    # ------------------------------------------------------------ a game

    def setup_map(self):
        self.clear()
        m = D.MAPS[self.map]
        self.routes = [make_route(path) for path in m["paths"]]
        # flyers cut straight from where a road starts to the keep
        self.flights = [make_route([path[0], path[-1]]) for path in m["paths"]]
        self.buildable = D.buildable(m)
        self.road_tiles = D.path_tiles(m)
        pts = set()
        for route, length in self.routes:
            d = 0.0
            while d <= length:
                x, y, _, _ = where(route, d)
                if -0.5 <= x <= D.COLS - 0.5 and -0.5 <= y <= D.ROWS - 0.5:
                    pts.add((round(x, 2), round(y, 2)))
                d += 0.25
        self.road_pts = sorted(pts)
        self.roadside = sorted((x, y) for x in range(D.COLS) for y in range(D.ROWS) if (x, y) not in self.road_tiles
                               and any((x + dx, y + dy) in self.road_tiles for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
        self.phase = "play"
        self.speed = 1
        self.game_id = secrets.token_hex(8)

    def start(self):
        self.setup_map()
        self.next_in = D.BUILD_TIME[0]
        crew = self.crew()
        for p in self.players.values():
            p.reset()
            p.gold = D.START_GOLD[0] / len(crew) + D.START_GOLD[1] if p in crew else 0
        for p in self.players.values():
            self.send_map(p)
            self.send_saves(p)

    def send_map(self, p):
        m = D.MAPS[self.map]
        self.send(p, {"t": "map", "name": m["name"], "paths": m["paths"], "rocks": m["rocks"],
                      "build": m.get("build")})

    def free(self, x, y):
        return type(x) is int and type(y) is int and (x, y) in self.buildable and (x, y) not in self.at

    def build(self, p, kind, x, y):
        if kind not in D.TOWERS or not self.free(x, y) or p.gold < D.TOWERS[kind]["cost"]:
            return None
        cost = D.TOWERS[kind]["cost"]
        p.gold -= cost
        p.spent += cost
        t = Tower(self.next_tower, kind, x, y, p.id)
        self.next_tower += 1
        self.towers[t.id] = self.at[(x, y)] = t
        t.undo = (time.monotonic() + UNDO, p.id, "build", cost, None)
        self.boosts()
        return t

    def evolved(self, kind, path):
        """The tower that already has this final evolution, if any: only one may stand at a time."""
        return next((t for t in self.towers.values()
                     if t.kind == kind and t.path == path and t.tier >= D.EVOLUTION), None)

    def upgrade(self, p, t, path):
        """Buy the next tier on `path`. Both paths can be bought, but only one past tier 2 (a tower
        is at most 4-2); a final evolution only if there isn't one already. Anyone may pay."""
        if t is None or path not in (0, 1) or not D.can_buy(t.tiers, path):
            return False
        nxt = t.tiers[path] + 1
        if nxt == D.EVOLUTION and self.evolved(t.kind, path):
            return False
        cost = D.TOWERS[t.kind]["paths"][path]["tiers"][nxt - 1]["cost"]
        if p.gold < cost:
            return False
        p.gold -= cost
        p.spent += cost
        t.spent += cost
        if t.first is None:
            t.first = path
        t.tiers[path] = nxt
        t.restat()
        t.undo = (time.monotonic() + UNDO, p.id, "up", cost, path)
        self.boosts()
        return True

    def undo(self, p, t):
        """Take back a build or an upgrade made in the last few seconds, for a full refund to whoever
        paid. Only the latest one on a tower, and only by the player who paid."""
        if t is None or not t.undo or t.undo[0] < time.monotonic() or t.undo[1] != p.id:
            return
        _, _, what, cost, path = t.undo
        p.gold += cost
        p.spent -= cost
        t.undo = None
        if what == "build":
            del self.towers[t.id]
            del self.at[(t.x, t.y)]
        else:
            t.spent -= cost
            t.tiers[path] -= 1
            if not t.tiers[t.first]:
                t.first = 1 - t.first if t.tiers[1 - t.first] else None
            t.restat()
        self.boosts()

    def sell(self, p, t):
        if t is None or t.owner != p.id:
            return
        if t.kills:
            self.retired.append((self.tower_name(t), t.owner, t.kills, t.dmg))
        p.gold += round(t.spent * D.SELL_BACK)
        del self.towers[t.id]
        del self.at[(t.x, t.y)]
        self.boosts()

    def boosts(self):
        """Work out what the support towers in reach do for each tower: the best of each kind counts."""
        helpers = [t for t in self.towers.values()
                   if any(t.stats.get(k) for k in ("boost", "reach", "power", "reveal", "unlock"))]
        for t in self.towers.values():
            near = [b.stats for b in helpers
                    if b is not t and math.hypot(b.x - t.x, b.y - t.y) <= b.stats["range"]]
            t.boost, t.reach, t.power = (max((b.get(k, 0.0) for b in near), default=0.0)
                                         for k in ("boost", "reach", "power"))
            t.unlock = any(b.get("unlock") for b in near)
            t.sees = bool(t.stats.get("detect") or t.stats["mode"] == "aura" or any(b.get("reveal") for b in near))

    def boss_kind(self, w):
        """Who the boss event sends on wave `w`: "boss" (Warlords) or a named boss."""
        if self.bosses == "random":
            return random.Random(f"{self.game_id}:{w}").choice(EVENT_BOSSES)
        return "boss" if self.bosses == "warlord" else self.bosses

    def groups(self, w):
        """Wave `w` as the room will send it (the boss event's boss in place of "boss")."""
        out = []
        for kind, count, gap, delay in D.wave(w):
            if kind == "boss" and self.boss_kind(w) != "boss":
                kind, count = self.boss_kind(w), 1
            out.append((kind, count, gap, delay))
        return out

    def start_wave(self):
        self.wave += 1
        self.wave_t = 0.0
        self.fighting = True
        for p in self.players.values():
            p.ready = False
        spawns = []
        for g, (kind, count, gap, delay) in enumerate(self.groups(self.wave)):
            for i in range(count):
                spawns.append((delay + i * gap, kind, (g + i) % len(self.routes)))
        self.spawns = sorted(spawns, reverse=True)
        self.dirty = True

    def spawn(self, kind, r):
        route, length = (self.flights if D.ENEMIES[kind].get("air") else self.routes)[r]
        # no tougher for more players: they share one income, so they're no richer
        e = Enemy(self.next_enemy, kind, self.wave, D.DIFFICULTY[self.diff], route, length, max(1, self.wave // 10))
        self.enemies.append(e)
        self.next_enemy += 1
        return e

    def child(self, kind, parent, d):
        """An enemy born mid-step (burst out of another, summoned, raised) at `d` along its route."""
        e = Enemy(self.next_enemy, kind, parent.wave, D.DIFFICULTY[self.diff], parent.route, parent.length)
        self.next_enemy += 1
        e.d = min(max(0.0, d), parent.length - 0.3)
        e.x, e.y, _, _ = where(e.route, e.d)
        e.camo = e.camo or parent.camo
        self.born.append(e)
        return e

    # ------------------------------------------------------------ hurting

    def hurt(self, e, dmg, src, st):
        """Damage an enemy with a hit carrying `st` (a tower's or a sentry's numbers) on behalf of
        `src` (a tower, a sentry or nothing), with everything that changes it."""
        if e.hp <= 0 or e.shield > self.fight_t:
            return
        unmade = self.fight_t < self.unmake
        if st.get("dtype", "normal") in e.immune and not unmade and not (src and src.unlock):
            return  # immune: no damage, and no slow, stun or burn either
        dmg *= 1 + (src.power if src else 0.0)
        if self.fight_t < self.mark[0]:
            dmg *= 1 + self.mark[1]
        if e.big:
            dmg *= st.get("boss", 1)
        if e.slow > 0:
            dmg *= 1 + e.brittle
        dmg = dmg if st.get("ap") or unmade else max(dmg * 0.15, dmg - e.armor)
        credit = src.credit if src else None
        self.damage(e, dmg, credit)
        if st.get("shred"):
            e.armor = max(0.0, e.armor - st["shred"])
        if st.get("stun"):
            e.stun = max(e.stun, st["stun"] / (3 if e.big else 1))
        if st.get("burn") and (st["burn"] >= e.burn or e.burn_for <= 0):
            e.burn, e.burn_for, e.burner = st["burn"], st.get("burn_for", 2.0), credit
        if st.get("slow"):
            e.slow, e.slow_for = max(e.slow, st["slow"]), st.get("hold", 1.5)
            e.brittle = max(e.brittle, st.get("brittle", 0.0))

    def damage(self, e, dmg, tower):
        """Take health off (a shell soaks it up first), credit the tower and its builder, pay out for a
        kill, and set off a boss's skull."""
        if e.hp <= 0 or e.shield > self.fight_t:
            return
        if e.shell > 0:
            soak = min(e.shell, dmg)
            e.shell -= soak
            dmg -= soak
            if dmg <= 0:
                return
        dealt = min(e.hp, dmg)
        e.hp -= dmg
        e.taken += dealt
        if e.skulls and e.hp > 0 and e.hp <= e.max * e.skulls[0]:
            self.skull(e)
        if tower is None:  # an ability's strike, an item, a sentry nobody built
            if e.hp <= 0:
                self.killed(e, None)
            return
        tower.dmg += dealt
        owner = self.players.get(tower.owner)
        if owner:
            owner.dmg += dealt
        if e.hp <= 0:
            tower.kills += 1
            self.kills.append(tower)
            if owner:
                owner.kills += 1
            self.killed(e, tower)

    def killed(self, e, tower):
        """Pay out for a kill, and let it burst into its children."""
        extra = max((m.stats.get("bounty", 0.0) for m in self.towers.values() if m.stats.get("bounty")
                     and (m.x - e.x) ** 2 + (m.y - e.y) ** 2 <= m.range ** 2), default=0.0)
        if self.fight_t < self.bounty_up[0]:
            extra += self.bounty_up[1]
        crew = self.crew() or [p for p in self.players.values() if p.seated]
        for p in crew:
            p.gold += e.bounty * (1 + extra) / len(crew)
        i = 0
        for kind, n in e.children:
            for _ in range(n):
                self.child(kind, e, e.d - 0.22 * i)
                i += 1

    def skull(self, e):
        """A boss event's boss has fallen past a skull: it does its move."""
        now = self.fight_t
        while e.skulls and e.hp <= e.max * e.skulls[0]:
            e.skulls.pop(0)
            self.effects.append([0, "skull", round(e.x, 2), round(e.y, 2)])
            if e.move == "raise":
                e.shield = now + D.SHIELD_FOR
                n = D.RAISE[0] + D.RAISE[1] * e.tier
                for i in range(n):
                    self.child("ghost", e, e.d + (i - n / 2) * 0.35)
            elif e.move == "storm":
                e.shield = now + 1.5
                for t in self.towers.values():
                    if (t.x - e.x) ** 2 + (t.y - e.y) ** 2 <= D.STORM_RANGE ** 2:
                        t.dazed = max(t.dazed, now + D.ZAP_FOR)
                        self.effects.append([t.id, "zap", round(e.x, 2), round(e.y, 2)])
            elif e.move == "charge":
                e.shell = e.max * D.CHARGE[0]
                e.charge = now + D.CHARGE[2]

    def pace(self, e):
        """How fast an enemy is moving now, tiles a second."""
        if e.stun > 0:
            return 0.0
        return e.speed * (1 - e.slow) * (D.CHARGE[1] if e.charge > self.fight_t else 1)

    # ------------------------------------------------------------ towers firing

    def order(self, t, near):
        """Enemies in reach, the one this tower wants first."""
        if t.target == "last":
            near.sort(key=lambda e: e.length - e.d, reverse=True)
        elif t.target == "strong":
            near.sort(key=lambda e: e.hp, reverse=True)
        elif t.target == "close":
            near.sort(key=lambda e: (e.x - t.x) ** 2 + (e.y - t.y) ** 2)
        else:  # first: the one nearest the keep
            near.sort(key=lambda e: e.length - e.d)
        return near

    @staticmethod
    def reaches(st, e):
        """Can a hit with these numbers touch this enemy, flying or not?"""
        return st.get("air", False) if e.air else st.get("ground", True)

    def in_reach(self, t, st):
        r2, x, y = t.range ** 2, t.x, t.y
        air, ground, sees = st.get("air", False), st.get("ground", True), t.sees
        return [e for e in self.enemies if (e.x - x) ** 2 + (e.y - y) ** 2 <= r2 and e.hp > 0
                and (air if e.air else ground) and (sees or not e.camo)]

    def fire(self, t):
        """One tower's (or sentry's) turn: shoot if something's in reach. True if it did."""
        s = t.stats
        mode = s["mode"]
        if mode in ("support", "income"):
            return False
        if mode == "trap":
            return self.lay(t)
        if mode == "sentry":
            return self.assemble(t)
        near = self.in_reach(t, s)
        if not near:
            return False
        self.order(t, near)
        if mode == "aura":
            for e in near:
                self.hurt(e, s["dmg"], t, s)
            self.shots.append([t.draw_id, t.x, t.y])
        elif mode == "chain":
            hit, e = [], near[0]
            while e is not None and len(hit) < s["chain"]:
                hit.append(e)
                self.hurt(e, s["dmg"], t, s)
                e = min((o for o in self.enemies if o.hp > 0 and o not in hit and self.reaches(s, o)
                         and (o.x - e.x) ** 2 + (o.y - e.y) ** 2 <= 1.7 ** 2),
                        key=lambda o: (o.x - e.x) ** 2 + (o.y - e.y) ** 2, default=None)
            self.shots.append([t.draw_id, round(t.x, 2), round(t.y, 2),
                               *[v for e in hit for v in (round(e.x, 2), round(e.y, 2))]])
        elif mode == "radial":  # blades all round
            n = s.get("shots", 8)
            a0 = self.rng.random() * math.tau
            for i in range(n):
                a = a0 + math.tau * i / n
                self.launch(t, s, math.cos(a), math.sin(a), None)
        else:  # shoot and splash: a projectile at each of the first `shots` in line, the rest fanned out
            n = s.get("shots", 1)
            speed = s.get("speed", 12)
            first = None
            for i in range(n):
                if i < len(near):
                    tx, ty = self.lead(t.x, t.y, near[i], None if s.get("lob") else speed)
                    if first is None:
                        first = (tx, ty)
                else:
                    a = math.atan2(first[1] - t.y, first[0] - t.x) + 0.18 * ((i - len(near)) // 2 + 1) * (1 if i % 2 else -1)
                    dist = math.hypot(first[0] - t.x, first[1] - t.y)
                    tx, ty = t.x + math.cos(a) * dist, t.y + math.sin(a) * dist
                if s.get("lob"):
                    self.lob(t, s, tx, ty)
                else:
                    dist = math.hypot(tx - t.x, ty - t.y) or 0.01
                    self.launch(t, s, (tx - t.x) / dist, (ty - t.y) / dist, dist)
        return True

    def lead(self, x, y, e, speed):
        """Where to aim at an enemy so the projectile meets it (or, lobbed, lands on it)."""
        tx, ty = e.x, e.y
        v = self.pace(e)
        if not v:
            return tx, ty
        for _ in range(2):
            secs = LOB_TIME if speed is None else math.hypot(tx - x, ty - y) / speed
            tx, ty, _, _ = where(e.route, min(e.d + v * secs, e.length))
        return tx, ty

    def style(self, src, st):
        """How the browsers draw a projectile."""
        if st.get("lob"):
            return "l"
        if src.kind == "workshop":
            return "s" if st["mode"] == "splash" else "c"
        if src.kind == "skyhook" and st["mode"] == "splash":
            return "s"
        return {"archer": "a", "ballista": "b", "cannon": "s", "bladewheel": "w", "arcanist": "o",
                "skyhook": "h", "alchemist": "f"}.get(src.kind, "a")

    def launch(self, src, st, dx, dy, aim):
        """A projectile from `src` heading (dx, dy): a shell flies to where it was aimed (`aim`
        tiles) and bursts there if it meets nothing first; anything else flies a little past its reach."""
        speed = st.get("speed", 12)
        if st["mode"] == "splash":
            left = max(0.3, aim)
        else:
            left = src.range * 1.25
        sh = Shot(self.next_shot, float(src.x), float(src.y), dx * speed, dy * speed, left, st, src)
        self.next_shot += 1
        self.flying.append(sh)
        self.draw(sh, src, st, left / speed)

    def lob(self, src, st, tx, ty):
        sh = Shot(self.next_shot, float(src.x), float(src.y), (tx - src.x) / LOB_TIME, (ty - src.y) / LOB_TIME,
                  LOB_TIME, st, src)
        sh.lob, sh.tx, sh.ty = True, tx, ty
        self.next_shot += 1
        self.flying.append(sh)
        self.draw(sh, src, st, LOB_TIME)

    def draw(self, sh, src, st, secs):
        if len(self.launched) < MAX_FLYING:
            self.launched.append([sh.id, src.draw_id, self.style(src, st), round(sh.x, 2), round(sh.y, 2),
                                  round(sh.vx, 2), round(sh.vy, 2), round(secs, 2)])
            self.drawn.add(sh.id)

    def fly(self, dt):
        """Move every projectile; each hits what it meets, up to its pierce."""
        keep = []
        enemies = [e for e in self.enemies if e.hp > 0]
        for sh in self.flying:
            done = False
            if sh.lob:
                sh.left -= dt
                sh.x += sh.vx * dt
                sh.y += sh.vy * dt
                if sh.left <= 0:
                    self.blast(sh.tx, sh.ty, sh.src, sh.st)
                    done = True
            else:
                speed = math.hypot(sh.vx, sh.vy)
                step = speed * dt
                n = max(1, math.ceil(step / SUBSTEP))
                ddx, ddy, dd = sh.vx * dt / n, sh.vy * dt / n, step / n
                st, air, ground = sh.st, sh.st.get("air", False), sh.st.get("ground", True)
                for _ in range(n):
                    sh.x += ddx
                    sh.y += ddy
                    sh.left -= dd
                    for e in enemies:
                        if e.hp <= 0 or e.id in sh.hit or not (air if e.air else ground):
                            continue
                        r = e.size + HIT_PAD
                        if (e.x - sh.x) ** 2 + (e.y - sh.y) ** 2 > r * r:
                            continue
                        if sh.splash:
                            self.blast(e.x, e.y, sh.src, st)
                            done = True
                            break
                        sh.hit.add(e.id)
                        self.hurt(e, st["dmg"], sh.src, st)
                        sh.pierce -= 1
                        if sh.pierce <= 0:
                            done = True
                            break
                    if done:
                        break
                    if sh.left <= 0:
                        if sh.splash:
                            self.blast(sh.x, sh.y, sh.src, st)
                        done = True
                        break
                    if not (-1.5 < sh.x < D.COLS + 0.5 and -1.5 < sh.y < D.ROWS + 0.5):
                        done = True
                        break
            if done:
                if sh.id in self.drawn:
                    self.drawn.discard(sh.id)
                    self.landed.append(sh.id)
            else:
                keep.append(sh)
        self.flying = keep

    def blast(self, x, y, src, st):
        """A burst (with any cluster of small ones around it) that hurts what it can reach."""
        blasts = [(x, y, st["splash"], st["dmg"])]
        for i in range(st.get("cluster", 0)):
            a = math.tau * i / st["cluster"] + self.rng.random()
            blasts.append((x + math.cos(a) * 0.8, y + math.sin(a) * 0.8, st["splash"] * 0.6, st["dmg"] * 0.4))
        look = "acid" if src is not None and src.kind == "alchemist" else \
            "fire" if st.get("burn") or st.get("dtype") == "fire" else "blast"
        for bx, by, radius, dmg in blasts:
            for e in self.enemies:
                if e.hp > 0 and self.reaches(st, e) and (e.x - bx) ** 2 + (e.y - by) ** 2 <= radius * radius:
                    self.hurt(e, dmg, src, st)
            if len(self.booms) < MAX_SHOTS:
                self.booms.append([round(bx, 2), round(by, 2), round(radius, 2), look])

    def lay(self, t):
        """A trapper lays a pile somewhere on the road in its reach, if it has fewer than its limit."""
        s = t.stats
        if sum(tr.src is t for tr in self.traps) >= s["max"]:
            return False
        if t.spots[0] != t.range:
            r2 = t.range ** 2
            t.spots = (t.range, [(x, y) for x, y in self.road_pts if (x - t.x) ** 2 + (y - t.y) ** 2 <= r2])
        if not t.spots[1]:
            return False
        x, y = self.rng.choice(t.spots[1])
        self.put_trap(s["trap"], x, y, s, t, s["life"])
        return True

    def put_trap(self, kind, x, y, st, src, life):
        tr = Trap(self.next_trap, kind, x, y, st, src, self.fight_t + life)
        self.next_trap += 1
        self.traps.append(tr)
        return tr

    def assemble(self, t):
        """A workshop builds a sentry beside the road in its reach, while there's a fight on."""
        s = t.stats
        if not self.enemies or sum(sn.parent is t for sn in self.sentries) >= s["max"]:
            return False
        self.put_sentry(t, s["sentry"], s["life"])
        return True

    def put_sentry(self, t, st, life, x=None, y=None):
        if x is None:
            taken = {(round(sn.x), round(sn.y)) for sn in self.sentries}
            r2 = t.range ** 2
            spots = [xy for xy in self.roadside if xy not in self.at and xy not in taken
                     and (xy[0] - t.x) ** 2 + (xy[1] - t.y) ** 2 <= r2]
            # somewhere it can reach an enemy near the workshop, if there is one
            foe = min((e for e in self.enemies if e.hp > 0), default=None,
                      key=lambda e: (e.x - t.x) ** 2 + (e.y - t.y) ** 2)
            if foe is not None:
                r = st["range"] * 0.8
                near = [xy for xy in spots if (xy[0] - foe.x) ** 2 + (xy[1] - foe.y) ** 2 <= r * r]
                spots = near or spots
            x, y = self.rng.choice(spots) if spots else (t.x, t.y)
            x, y = x + self.rng.uniform(-0.15, 0.15), y + self.rng.uniform(-0.15, 0.15)
        sn = Sentry(self.next_sentry, x, y, st, t, self.fight_t + life)
        self.next_sentry += 1
        self.sentries.append(sn)
        return sn

    def spring(self):
        """Enemies walking over piles on the road set them off; tar slows whatever's in it."""
        keep = []
        for tr in self.traps:
            if tr.until <= self.fight_t or tr.hits <= 0:
                continue
            reach = tr.st.get("radius", TRAP_REACH)
            for e in self.enemies:
                if e.hp <= 0 or e.air or (e.x - tr.x) ** 2 + (e.y - tr.y) ** 2 > (reach + e.size * 0.5) ** 2:
                    continue
                if tr.kind == "tar":
                    e.slow = max(e.slow, tr.st["slow"])
                    e.slow_for = max(e.slow_for, 0.3)
                elif tr.kind == "mine":
                    self.blast(tr.x, tr.y, tr.src, tr.st)
                    tr.hits = 0
                    break
                elif e.id not in tr.hit:
                    tr.hit.add(e.id)
                    self.hurt(e, tr.st["dmg"], tr.src, tr.st)
                    tr.hits -= 1
                    if tr.hits <= 0:
                        break
            if tr.hits > 0:
                keep.append(tr)
        self.traps = keep

    def advance(self, dt):
        """One step of the fight."""
        if not self.fighting:
            self.next_in -= dt
            if self.next_in <= 0:
                self.start_wave()
            return
        self.wave_t += dt
        self.fight_t += dt
        now = self.fight_t
        while self.spawns and self.spawns[-1][0] <= self.wave_t:
            _, kind, r = self.spawns.pop()
            self.spawn(kind, r)
        menders = [e for e in self.enemies if e.heal and e.hp > 0]
        if menders:  # Menders patch up whoever's near them, themselves included (the best one counts)
            for e in self.enemies:
                heal = max((m.heal for m in menders if (e.x - m.x) ** 2 + (e.y - m.y) ** 2 <= 1.5 ** 2), default=0)
                if heal and e.hp > 0:
                    e.hp = min(e.max, e.hp + e.max * heal * dt)
        for e in self.enemies:
            if e.slow_for > 0:
                e.slow_for -= dt
                if e.slow_for <= 0:
                    e.slow = e.brittle = 0.0
            if e.burn_for > 0:
                e.burn_for -= dt
                self.damage(e, e.burn * dt, e.burner)
                if e.hp <= 0:
                    continue
            if e.summon:  # a Warlord calls up Grunts behind it
                e.summon_t -= dt
                if e.summon_t <= 0:
                    e.summon_t = e.every
                    for i in range(e.summon):
                        self.child("grunt", e, e.d - 0.3 * (i + 1))
            if e.zap_t:  # the Stormhulk knocks out the best tower near it
                e.zap_t -= dt
                if e.zap_t <= 0:
                    e.zap_t = D.ENEMIES[e.kind]["zap"]
                    near = [t for t in self.towers.values() if t.dazed <= now
                            and (t.x - e.x) ** 2 + (t.y - e.y) ** 2 <= D.ZAP_RANGE ** 2]
                    if near:
                        t = max(near, key=lambda t: t.spent)
                        t.dazed = now + D.ZAP_FOR
                        self.effects.append([t.id, "zap", round(e.x, 2), round(e.y, 2)])
            if e.stun > 0:
                e.stun -= dt
                continue
            e.d += self.pace(e) * dt
            if e.d >= e.length:
                e.hp = 0
                self.lives -= e.lives
                self.leaks[self.wave] = self.leaks.get(self.wave, 0) + e.lives
                self.dirty = True
                continue
            e.x, e.y, _, _ = where(e.route, e.d)
        self.spring()
        self.fly(dt)
        rally = self.rally[1] if now < self.rally[0] else 1.0
        for t in self.towers.values():
            t.cool -= dt
            t.cd = max(0.0, t.cd - dt)
            if t.cool <= 0 and t.dazed <= now and self.fire(t):
                fast = t.overdrive[1] if now < t.overdrive[0] else 1.0
                t.cool = t.stats["rate"] / (1 + t.boost) / fast / rally
        live = []
        for sn in self.sentries:
            if sn.until <= now:
                continue
            live.append(sn)
            sn.cool -= dt
            if sn.cool <= 0 and self.fire(sn):
                p = sn.parent
                fast = p.overdrive[1] if p and now < p.overdrive[0] else 1.0
                sn.cool = sn.stats["rate"] / fast / rally
        self.sentries = live
        self.enemies = [e for e in self.enemies if e.hp > 0] + self.born
        self.born = []
        if self.lives <= 0:
            self.lives = 0
            self.phase = "lost"
            self.end_game(False)
            self.dirty = True
        elif not self.spawns and not self.enemies:
            self.fighting = False
            self.dirty = True
            self.sentries = []  # sentries pack up between waves; piles on the road stay
            for sh in self.flying:
                if sh.id in self.drawn:
                    self.landed.append(sh.id)
            self.flying, self.drawn = [], set()
            crew = self.crew() or [p for p in self.players.values() if p.seated]
            for p in crew:  # a little for seeing the wave off
                p.gold += (20 + 4 * self.wave) / len(crew)
            for m in self.towers.values():  # mints (and other towers with income) pay their builders
                if m.stats.get("income") and m.owner in self.players:
                    self.players[m.owner].gold += m.stats["income"]
            if self.wave == D.WAVES and not self.endless:
                self.phase = "won"
                self.end_game(True)
            else:
                self.next_in = D.BUILD_TIME[1]
                self.save_game()

    # ------------------------------------------------------------ abilities and items

    def use_ability(self, t):
        """Set off a final evolution's ability, if it's ready and there's a fight on."""
        a = t.ability if t else None
        if a is None or t.cd > 0 or not self.fighting:
            return False
        now = self.fight_t
        ground = a.get("ground", False)
        foes = [e for e in self.enemies if e.hp > 0 and not (ground and e.air)]
        do = a["do"]
        if do == "strike":
            if a["pick"] == "all":
                hit = foes
            elif a["pick"] == "lead":
                lead = min(foes, key=lambda e: e.length - e.d, default=None)
                hit = [e for e in foes if lead and (e.x - lead.x) ** 2 + (e.y - lead.y) ** 2 <= a["radius"] ** 2]
            elif a["pick"] == "near":
                hit = [e for e in foes if (e.x - t.x) ** 2 + (e.y - t.y) ** 2 <= a["radius"] ** 2]
            else:
                hit = sorted(foes, key=lambda e: e.hp, reverse=True)[:a["pick"]]
            if not hit:
                return False
            for e in hit:
                dmg = e.max * a["boss_frac"] if e.boss and "boss_frac" in a else a["dmg"]
                self.damage(e, dmg, t)
            self.effects.append([t.id, do, *[v for e in hit[:24] for v in (round(e.x, 2), round(e.y, 2))]])
        elif do == "transmute":
            hit = sorted((e for e in foes if not e.boss), key=lambda e: e.hp, reverse=True)[:a["pick"]]
            if not hit:
                return False
            for e in hit:
                e.bounty *= a["mult"]
                e.shell = 0
                self.damage(e, e.hp + 1, t)
            self.effects.append([t.id, "gold", *[v for e in hit for v in (round(e.x, 2), round(e.y, 2))]])
        elif do == "carpet":
            pts = self.road_pts[::max(1, len(self.road_pts) // a["piles"])][:a["piles"]]
            st = dict(t.stats, dmg=t.stats["dmg"] * a["mult"], hits=max(20, t.stats.get("hits", 1)))
            for x, y in pts:
                self.put_trap("spike", x, y, st, t, 25)
            self.effects.append([t.id, "strike", *[v for x, y in pts for v in (x, y)]])
        elif do == "detonate":
            mine = [tr for tr in self.traps if tr.src is t]
            if not mine:
                return False
            for tr in mine:
                self.blast(tr.x, tr.y, t, dict(tr.st, dmg=tr.st["dmg"] * a["mult"], splash=tr.st.get("splash", 1.0)))
                tr.hits = 0
            self.effects.append([t.id, "strike", *[v for tr in mine[:24] for v in (round(tr.x, 2), round(tr.y, 2))]])
        elif do == "deploy":
            s = t.stats
            have = sum(sn.parent is t for sn in self.sentries)
            for _ in range(max(0, 2 * s["max"] - have)):
                self.put_sentry(t, s["sentry"], s["life"])
            self.effects.append([t.id, "rally"])
        else:
            if do == "stun":
                for e in foes:
                    e.stun = max(e.stun, a["secs"] / (3 if e.big else 1))
            elif do == "slow":
                for e in foes:
                    e.slow, e.slow_for = max(e.slow, a["slow"]), a["secs"]
            elif do == "burn":
                for e in foes:
                    e.burn, e.burn_for, e.burner = a["dps"], a["secs"], t
            elif do == "overdrive":
                t.overdrive = (now + a["secs"], a["rate"])
            elif do == "rally":
                self.rally = (now + a["secs"], a["rate"])
            elif do == "mark":
                self.mark = (now + a["secs"], a["more"])
            elif do == "unmake":
                self.unmake = now + a["secs"]
            elif do == "gold":
                for p in self.players.values():
                    if p.seated:
                        p.gold += a["gold"]
            elif do == "bounty":
                self.bounty_up = (now + a["secs"], a["more"])
            self.effects.append([t.id, do])
        t.cd = a["cd"]
        return True

    def use_item(self, p, kind, x=None, y=None):
        """Buy a one-use item from your own purse and use it at once, where it's aimed."""
        it = D.ITEMS.get(kind) if type(kind) is str else None
        if it is None or (it.get("fight") and not self.fighting) or p.items.get(kind, 0.0) > self.fight_t:
            return False
        wave = max(1, self.wave if self.fighting else self.wave + 1)
        cost = D.item_cost(kind, wave)
        place = it["place"]
        on_board = type(x) is int and type(y) is int and 0 <= x < D.COLS and 0 <= y < D.ROWS
        if place != "none" and not on_board:
            return False
        if place == "road" and (x, y) not in self.road_tiles:
            return False
        if place == "free" and (not self.free(x, y) or any(round(sn.x) == x and round(sn.y) == y for sn in self.sentries)):
            return False
        if p.gold < cost:
            return False
        p.gold -= cost
        p.spent += cost
        p.items[kind] = self.fight_t + it["cd"]
        power = D.item_power(wave)
        now = self.fight_t
        if kind == "caltrops":
            self.put_trap("spike", x, y, {"dtype": "normal", "dmg": it["dmg"] * power, "hits": it["hits"]}, None, it["life"])
        elif kind == "tar":
            self.put_trap("tar", x, y, {"slow": it["slow"], "radius": it["radius"], "hits": 1}, None, it["life"])
        elif kind == "keg":
            self.blast(x, y, None, {"mode": "splash", "dtype": "normal", "dmg": it["dmg"] * power, "splash": it["splash"],
                                    "air": True})
        elif kind == "hired":
            st = dict(it["sentry"], dmg=it["sentry"]["dmg"] * power)
            self.put_sentry(None, st, it["life"], x, y)
        elif kind == "horn":
            if now >= self.rally[0] or self.rally[1] < it["rate"]:
                self.rally = (now + it["secs"], it["rate"])
        elif kind == "flask":
            for e in self.enemies:
                if e.hp > 0:
                    e.stun = max(e.stun, it["secs"] / (3 if e.big else 1))
        self.effects.append([0, f"item:{kind}", *([x, y] if place != "none" else [])])
        return True

    # ------------------------------------------------------------ the end, saves and records

    @staticmethod
    def tower_name(t):
        """A tower's final evolution's name, or its kind's."""
        if t.tier >= D.EVOLUTION:
            return D.TOWERS[t.kind]["paths"][t.path]["tiers"][D.EVOLUTION - 1]["name"]
        return D.TOWERS[t.kind]["name"]

    def end_game(self, won):
        """Sum the game up (sold towers count too), put it in the records and drop its save."""
        seated = [p for p in self.players.values() if p.seated]
        towers = [(self.tower_name(t), t.owner, t.kills, t.dmg) for t in self.towers.values()] + self.retired
        towers = sorted((t for t in towers if t[2]), key=lambda t: (t[2], t[3]), reverse=True)
        best = {}
        for t in towers:
            best.setdefault(t[1], t)
        reached = self.wave if not won else D.WAVES
        self.summary = {
            "won": won, "wave": reached, "endless": self.endless,
            "mvp": towers and {"name": towers[0][0], "owner": towers[0][1], "kills": towers[0][2],
                               "dmg": round(towers[0][3])} or None,
            "best": {pid: {"name": n, "kills": k, "dmg": round(d)} for pid, (n, _, k, d) in best.items()},
            "leaks": sorted([w, n] for w, n in self.leaks.items()),
        }
        self.record_new = False
        if self.saving:
            self.record_new = SAVE.record(self.map, self.diff, len(seated), reached,
                                          [p.name for p in seated], won and not self.endless)
            if self.game_id:
                SAVE.delete(self.game_id)
            for p in self.players.values():
                self.send_saves(p)

    def send_saves(self, p):
        if self.saving and p.token:
            self.send(p, {"t": "saves", "list": SAVE.list_for(p.token)})

    def save_game(self):
        """Save the game at the start of a build phase."""
        if not self.saving or not self.game_id:
            return
        seated = [p for p in self.players.values() if p.seated and p.token]
        if not seated:
            return
        state = {
            "map": self.map, "diff": self.diff, "bosses": self.bosses, "wave": self.wave, "lives": self.lives,
            "endless": self.endless, "leaks": sorted([w, n] for w, n in self.leaks.items()),
            "players": [{"token": p.token, "name": p.name, "color": p.color, "gold": p.gold, "kills": p.kills,
                         "dmg": p.dmg, "spent": p.spent} for p in seated],
            "towers": [{"k": t.kind, "c": t.tiers, "f": t.first, "x": t.x, "y": t.y, "s": t.spent, "kills": t.kills,
                        "dmg": t.dmg, "tg": t.target, "cd": t.cd,
                        "o": self.players[t.owner].token if t.owner in self.players else None}
                       for t in self.towers.values()],
        }
        names = ", ".join(p.name for p in seated)
        boss = "" if self.bosses == "warlord" else f", {D.BOSSES[self.bosses]}"
        summary = (f"{D.MAPS[self.map]['name']}, {self.diff}{boss}: wave {self.wave + 1} next, "
                   f"{self.lives} lives. {names}")
        SAVE.save(self.game_id, [p.token for p in seated], state, summary)
        for p in self.players.values():
            self.send_saves(p)

    def resume(self, p, game_id):
        """Pick up a saved game. Players in the room whose browsers were in it get their purses
        back; anyone missing keeps a seat (and their towers) to come back to."""
        state = SAVE.load(game_id, p.token)
        if not state or state.get("map") not in D.MAPS or state.get("diff") not in D.DIFFICULTY:
            return False
        self.map, self.diff = state["map"], state["diff"]
        self.bosses = state.get("bosses") if state.get("bosses") in D.BOSSES else "warlord"
        self.setup_map()
        self.game_id = game_id
        self.wave, self.lives, self.endless = state["wave"], state["lives"], state["endless"]
        self.leaks = {w: n for w, n in state.get("leaks", [])}
        self.next_in = D.BUILD_TIME[1]
        by_token = {}
        here = {q.token: q for q in self.players.values() if q.token}
        for q in self.players.values():
            q.reset()
            q.seated = False
        for saved in state["players"]:
            q = here.get(saved["token"])
            if q is None:  # not here yet: a seat to come back to
                q = Player(self.next_id, self.unique_name(saved["name"]), saved["color"], None, saved["token"], None)
                q.connected = False
                self.next_id += 1
                self.players[q.id] = q
            q.seated = True
            q.gold, q.kills, q.dmg, q.spent = saved["gold"], saved["kills"], saved["dmg"], saved["spent"]
            by_token[saved["token"]] = q
        for q in self.players.values():  # newcomers take any seats left, with a little gold
            if not q.seated and sum(o.seated for o in self.players.values()) < MAX_PLAYERS:
                q.seated = True
                q.gold = D.START_GOLD[1]
        for saved in state["towers"]:
            if saved["k"] not in D.TOWERS or not self.free(saved["x"], saved["y"]):
                continue
            owner = by_token.get(saved["o"])
            t = Tower(self.next_tower, saved["k"], saved["x"], saved["y"], owner.id if owner else None)
            self.next_tower += 1
            t.tiers, t.first = list(saved["c"]), saved["f"]
            t.restat()
            t.spent, t.kills, t.dmg, t.cd = saved["s"], saved["kills"], saved["dmg"], saved.get("cd", 0.0)
            t.target = saved.get("tg", "first") if saved.get("tg") in TARGETS else "first"
            self.towers[t.id] = self.at[(t.x, t.y)] = t
        self.boosts()
        for q in self.players.values():
            self.send_map(q)
        return True

    def tick(self):
        if self.phase != "play":
            return
        for _ in range(self.speed):
            if self.phase == "play":
                self.advance(STEP)
        self.since_snap += STEP
        if self.dirty:
            self.dirty = False
            self.send_state()
        if self.since_snap >= SNAP_EVERY:
            self.since_snap = 0.0
            self.everyone(self.snapshot())
            self.shots, self.launched, self.landed, self.booms = [], [], [], []
            self.kills = []
            self.effects = []
            for e in self.enemies:
                e.taken = 0.0

    def snapshot(self):
        now = self.fight_t
        kinds = {k: i for i, k in enumerate(D.KINDS)}
        return {
            "t": "s",
            "e": [[e.id, kinds[e.kind], round(e.x, 2), round(e.y, 2), round(100 * e.hp / e.max),
                   int(e.slow > 0) | 2 * (e.burn_for > 0) | 4 * (e.stun > 0) | 8 * e.camo
                   | 16 * (e.shield > now) | 32 * (e.shell > 0) | 64 * (e.charge > now), round(e.taken)]
                  for e in self.enemies],
            "bo": [[e.id, kinds[e.kind], round(100 * e.hp / e.max), e.tier, round(100 * e.shell / e.max)]
                   for e in self.enemies if e.event],
            "a": {t.id: round(t.cd, 1) for t in self.towers.values() if t.tier >= D.EVOLUTION},
            "dz": {t.id: round(t.dazed - now, 1) for t in self.towers.values() if t.dazed > now},
            "x": self.effects,
            "gl": [round(max(0.0, until - now), 1) for until in (self.rally[0], self.mark[0], self.bounty_up[0], self.unmake)],
            "f": self.shots[-MAX_SHOTS:],
            "p": self.launched,
            "pe": self.landed,
            "bx": self.booms,
            "tr": [[tr.id, TRAP_CODES[tr.kind], tr.x, tr.y] for tr in self.traps],
            "se": [[sn.id, round(sn.x, 2), round(sn.y, 2), sn.draw_id] for sn in self.sentries],
            "k": {t.id: t.kills for t in set(self.kills)},
            "g": {p.id: int(p.gold) for p in self.players.values() if p.seated},
            "ic": {p.id: {k: round(v - now, 1) for k, v in p.items.items() if v > now}
                   for p in self.players.values() if p.seated},
            "n": None if self.fighting else round(max(0.0, self.next_in), 1),
        }

    async def run(self):
        next_t = time.monotonic()
        try:
            while self.humans():
                try:
                    self.tick()
                except Exception:
                    log.exception("holdfast: tick failed in room %s", self.code)
                next_t += STEP
                delay = next_t - time.monotonic()
                if delay < -0.5:
                    next_t = time.monotonic()
                await asyncio.sleep(max(0.0, delay))
        finally:
            self.task = None
            self.empty_since = time.monotonic()

    # ------------------------------------------------------------ what the browsers see

    def send_state(self):
        st = {
            "t": "state", "phase": self.phase, "host": self.host, "map": self.map, "diff": self.diff,
            "bosses": self.bosses,
            "players": [{"id": p.id, "name": p.name, "color": p.color, "on": p.connected, "seated": p.seated,
                         "gold": int(p.gold), "kills": p.kills, "dmg": round(p.dmg), "spent": p.spent,
                         "ready": p.ready} for p in self.players.values()],
        }
        if self.phase != "lobby":
            nxt = self.wave + 1
            st.update(
                wave=self.wave, lives=self.lives, fighting=self.fighting, speed=self.speed,
                towers=[t.view() for t in self.towers.values()], endless=self.endless,
                item_wave=max(1, self.wave if self.fighting else nxt),
                coming=[[kind, count] for kind, count, _, _ in self.groups(nxt)] if nxt <= D.WAVES or self.endless else [])
        if self.phase in ("won", "lost"):
            st.update(summary=self.summary, record_new=self.record_new)
        if self.phase in ("lobby", "won", "lost") and self.saving:
            st["records"] = SAVE.records(self.map, self.diff)
        self.everyone(st)


ROOMS = Codes(ROOM_KEEP)
