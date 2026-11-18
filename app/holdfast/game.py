"""Holdfast: co-op tower defence for 1-4 players.

Everyone builds on one map, each from their own purse; bounties are shared out equally between
whoever is connected, and gold can be handed to another player. Thirty waves; twenty lives between
everyone. The server runs the whole fight (`Room.advance`), fifteen steps a second, and sends
snapshots of the enemies ten times a second; the browser only draws and asks to build.

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
MAX_SHOTS = 80  # shots drawn a snapshot, at most (a Storm of Arrows looses forty a second)
MAX_PLAYERS = 4
MAX_IN_ROOM = 10
COLORS = ["#e8552f", "#3f8fe8", "#e8b923", "#4fb85f"]
ROOM_KEEP = 30 * 60
SPEEDS = (1, 2, 3)
GIFT = 25
TARGETS = ("first", "last", "strong", "close")  # which enemy in reach a tower aims at
UNDO = 5  # real seconds in which a build or upgrade can be taken back for a full refund


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


class Tower:
    def __init__(self, tid, kind, x, y, owner):
        self.id, self.kind, self.x, self.y, self.owner = tid, kind, x, y, owner
        self.path = None  # the upgrade path, once one's bought
        self.tier = 0
        self.spent = D.TOWERS[kind]["cost"]
        self.cool = 0.3
        self.boost = self.reach = self.power = 0.0  # from beacons nearby
        self.kills = 0
        self.dmg = 0.0
        self.stats = D.stats(kind)
        self.target = "first"
        self.sees = False  # can it target Ghosts?
        self.cd = 0.0  # seconds of fighting before its ability is ready again
        self.overdrive = (0.0, 1.0)  # (fight time it lasts until, how much faster)
        self.undo = None  # (monotonic time it expires, who paid, "build" or "up", cost)

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
        return {"id": self.id, "k": self.kind, "p": self.path, "n": self.tier, "x": self.x, "y": self.y,
                "o": self.owner, "s": self.spent, "kills": self.kills, "dmg": round(self.dmg),
                "tg": self.target, "un": undo}


class Enemy:
    def __init__(self, eid, kind, wave, mult, route, length):
        e = D.ENEMIES[kind]
        self.id, self.kind = eid, kind
        self.max = self.hp = e["hp"] * D.health(wave) * mult
        self.speed = e["speed"]
        self.armor = e.get("armor", 0) * (1 + wave / 15)
        self.air = e.get("air", False)
        self.bounty = e["bounty"] * D.bounty(wave)
        self.lives = e.get("lives", 1)
        self.route, self.length = route, length
        self.d = 0.0  # how far along the route
        self.x, self.y = route[0][0]
        self.slow, self.slow_for, self.brittle = 0.0, 0.0, 0.0
        self.stun = 0.0  # seconds left stopped dead
        self.burn, self.burn_for, self.burner = 0.0, 0.0, None  # damage a second, for how long, from which tower
        self.boss = kind == "boss"
        self.camo = e.get("camo", False)
        self.heal = e.get("heal", 0.0)
        self.split = e.get("split", 0)
        self.summon, self.every = e.get("summon", 0), e.get("every", 0)
        self.summon_t = self.every
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
        self.shots = []
        self.kills = []  # towers that have killed something since the last snapshot
        self.next_tower = self.next_enemy = 1
        self.blocked = set()
        self.routes = []
        self.since_snap = 0.0
        self.dirty = False
        self.buildable = set()
        self.fight_t = 0.0  # seconds spent fighting, all game (ability cooldowns and effects run on it)
        self.rally = (0.0, 1.0)  # (fight time until, how much faster every tower fires)
        self.mark = (0.0, 0.0)  # (until, extra damage every enemy takes)
        self.bounty_up = (0.0, 0.0)  # (until, extra a kill pays)
        self.born = []  # enemies born mid-step (split, summoned), joined at the end of it
        self.effects = []  # abilities used since the last snapshot: [tower id, what it did]
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
        t.undo = (time.monotonic() + UNDO, p.id, "build", cost)
        self.boosts()
        return t

    def evolved(self, kind, path):
        """The tower that already has this final evolution, if any: only one may stand at a time."""
        return next((t for t in self.towers.values()
                     if t.kind == kind and t.path == path and t.tier >= D.EVOLUTION), None)

    def upgrade(self, p, t, path):
        """Buy the next tier on `path` (the first buy picks the path for good). Anyone may pay."""
        if t is None or path not in (0, 1) or (t.path is not None and t.path != path) or t.tier >= D.EVOLUTION:
            return False
        if t.tier + 1 == D.EVOLUTION and self.evolved(t.kind, path):
            return False
        cost = D.TOWERS[t.kind]["paths"][path]["tiers"][t.tier]["cost"]
        if p.gold < cost:
            return False
        p.gold -= cost
        p.spent += cost
        t.spent += cost
        t.path = path
        t.tier += 1
        t.stats = D.stats(t.kind, path, t.tier)
        t.undo = (time.monotonic() + UNDO, p.id, "up", cost)
        self.boosts()
        return True

    def undo(self, p, t):
        """Take back a build or an upgrade made in the last few seconds, for a full refund to whoever
        paid. Only the latest one on a tower, and only by the player who paid."""
        if t is None or not t.undo or t.undo[0] < time.monotonic() or t.undo[1] != p.id:
            return
        _, _, what, cost = t.undo
        p.gold += cost
        p.spent -= cost
        t.undo = None
        if what == "build":
            del self.towers[t.id]
            del self.at[(t.x, t.y)]
        else:
            t.spent -= cost
            t.tier -= 1
            if t.tier == 0:
                t.path = None
            t.stats = D.stats(t.kind, t.path, t.tier)
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
        """Work out what the beacons beside each tower do for it: the best of each kind counts."""
        beacons = [t for t in self.towers.values() if t.kind == "beacon"]
        for t in self.towers.values():
            near = [b.stats for b in beacons
                    if b is not t and math.hypot(b.x - t.x, b.y - t.y) <= b.stats["range"]]
            t.boost, t.reach, t.power = (max((b.get(k, 0.0) for b in near), default=0.0)
                                         for k in ("boost", "reach", "power"))
            t.sees = bool(t.stats.get("detect") or t.stats["mode"] == "aura" or any(b.get("reveal") for b in near))

    def start_wave(self):
        self.wave += 1
        self.wave_t = 0.0
        self.fighting = True
        for p in self.players.values():
            p.ready = False
        spawns = []
        for g, (kind, count, gap, delay) in enumerate(D.wave(self.wave)):
            for i in range(count):
                spawns.append((delay + i * gap, kind, (g + i) % len(self.routes)))
        self.spawns = sorted(spawns, reverse=True)
        self.dirty = True

    def spawn(self, kind, r):
        route, length = (self.flights if D.ENEMIES[kind].get("air") else self.routes)[r]
        # no tougher for more players: they share one income, so they're no richer
        self.enemies.append(Enemy(self.next_enemy, kind, self.wave, D.DIFFICULTY[self.diff], route, length))
        self.next_enemy += 1

    def hurt(self, e, dmg, tower, pierce=False):
        """Damage an enemy on behalf of a tower, with everything that changes it."""
        if e.hp <= 0:
            return
        st = tower.stats
        dmg *= 1 + tower.power
        if self.fight_t < self.mark[0]:
            dmg *= 1 + self.mark[1]
        if e.boss:
            dmg *= st.get("boss", 1)
        if e.slow > 0:
            dmg *= 1 + e.brittle
        dmg = dmg if pierce or st.get("pierce") else max(dmg * 0.15, dmg - e.armor)
        self.damage(e, dmg, tower)
        if st.get("shred"):
            e.armor = max(0.0, e.armor - st["shred"])
        if st.get("stun"):
            e.stun = max(e.stun, st["stun"] / (3 if e.boss else 1))
        if st.get("burn") and (st["burn"] >= e.burn or e.burn_for <= 0):
            e.burn, e.burn_for, e.burner = st["burn"], st.get("burn_for", 2.0), tower
        if st.get("slow"):
            e.slow, e.slow_for = max(e.slow, st["slow"]), st.get("hold", 1.5)
            e.brittle = max(e.brittle, st.get("brittle", 0.0))

    def damage(self, e, dmg, tower):
        """Take health off, credit the tower and its builder, and pay out for a kill."""
        if e.hp <= 0:
            return
        dealt = min(e.hp, dmg)
        e.hp -= dmg
        e.taken += dealt
        if tower is None:  # an ability's strike
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
        """Pay out for a kill, and let a Splitter split."""
        extra = max((m.stats.get("bounty", 0.0) for m in self.towers.values() if m.kind == "mint"
                     and (m.x - e.x) ** 2 + (m.y - e.y) ** 2 <= m.range ** 2), default=0.0)
        if self.fight_t < self.bounty_up[0]:
            extra += self.bounty_up[1]
        crew = self.crew() or [p for p in self.players.values() if p.seated]
        for p in crew:
            p.gold += e.bounty * (1 + extra) / len(crew)
        for i in range(e.split):
            child = Enemy(self.next_enemy, "swarm", e.wave, D.DIFFICULTY[self.diff], e.route, e.length)
            self.next_enemy += 1
            child.d = max(0.0, e.d - 0.25 * i)
            child.x, child.y = e.x, e.y
            self.born.append(child)

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

    def fire(self, t):
        """One tower's turn: shoot if something's in reach. True if it did."""
        s = t.stats
        mode = s["mode"]
        if mode in ("support", "income"):
            return False
        air, r = s.get("air", False), t.range
        near = [e for e in self.enemies if e.hp > 0 and (air or not e.air) and (t.sees or not e.camo)
                and (e.x - t.x) ** 2 + (e.y - t.y) ** 2 <= r * r]
        if not near:
            return False
        self.order(t, near)
        if mode == "aura":
            for e in near:
                self.hurt(e, s["dmg"], t)
            self.shots.append([t.id, t.x, t.y])
        elif mode == "splash":
            for target in near[:s.get("shots", 1)]:
                blasts = [(target.x, target.y, s["splash"], s["dmg"])]
                for i in range(s.get("cluster", 0)):
                    a = 2 * math.pi * i / s["cluster"] + self.rng.random()
                    blasts.append((target.x + math.cos(a) * 0.8, target.y + math.sin(a) * 0.8, s["splash"] * 0.6,
                                   s["dmg"] * 0.4))
                for x, y, radius, dmg in blasts:
                    for e in self.enemies:
                        if not e.air and (e.x - x) ** 2 + (e.y - y) ** 2 <= radius * radius:
                            self.hurt(e, dmg, t)
                self.shots.append([t.id, *[round(v, 2) for x, y, _, _ in blasts for v in (x, y)]])
        elif mode == "chain":
            hit, e = [], near[0]
            while e is not None and len(hit) < s["chain"]:
                hit.append(e)
                self.hurt(e, s["dmg"], t)
                e = min((o for o in self.enemies if o.hp > 0 and o not in hit and (air or not o.air)
                         and (o.x - e.x) ** 2 + (o.y - e.y) ** 2 <= 1.7 ** 2),
                        key=lambda o: (o.x - e.x) ** 2 + (o.y - e.y) ** 2, default=None)
            self.shots.append([t.id, *[v for e in hit for v in (round(e.x, 2), round(e.y, 2))]])
        else:
            for target in near[:s.get("shots", 1)]:
                self.hurt(target, s["dmg"], t)
                self.shots.append([t.id, round(target.x, 2), round(target.y, 2)])
        return True

    def advance(self, dt):
        """One step of the fight."""
        if not self.fighting:
            self.next_in -= dt
            if self.next_in <= 0:
                self.start_wave()
            return
        self.wave_t += dt
        self.fight_t += dt
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
                        g = Enemy(self.next_enemy, "grunt", e.wave, D.DIFFICULTY[self.diff], e.route, e.length)
                        self.next_enemy += 1
                        g.d = max(0.0, e.d - 0.3 * (i + 1))
                        g.x, g.y = e.x, e.y
                        self.born.append(g)
            if e.stun > 0:
                e.stun -= dt
                continue
            e.d += e.speed * (1 - e.slow) * dt
            if e.d >= e.length:
                e.hp = 0
                self.lives -= e.lives
                self.leaks[self.wave] = self.leaks.get(self.wave, 0) + e.lives
                self.dirty = True
                continue
            i = next(i for i, (_, d) in enumerate(e.route) if d > e.d)
            (x0, y0), d0 = e.route[i - 1]
            (x1, y1), d1 = e.route[i]
            u = (e.d - d0) / (d1 - d0)
            e.x, e.y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        rally = self.rally[1] if self.fight_t < self.rally[0] else 1.0
        for t in self.towers.values():
            t.cool -= dt
            t.cd = max(0.0, t.cd - dt)
            if t.cool <= 0 and self.fire(t):
                fast = t.overdrive[1] if self.fight_t < t.overdrive[0] else 1.0
                t.cool = t.stats["rate"] / (1 + t.boost) / fast / rally
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
            crew = self.crew() or [p for p in self.players.values() if p.seated]
            for p in crew:  # a little for seeing the wave off
                p.gold += (20 + 4 * self.wave) / len(crew)
            for m in self.towers.values():  # mints pay their builders
                if m.kind == "mint" and m.owner in self.players:
                    self.players[m.owner].gold += m.stats.get("income", 0)
            if self.wave == D.WAVES and not self.endless:
                self.phase = "won"
                self.end_game(True)
            else:
                self.next_in = D.BUILD_TIME[1]
                self.save_game()

    # ------------------------------------------------------------ abilities

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
            else:
                hit = sorted(foes, key=lambda e: e.hp, reverse=True)[:a["pick"]]
            if not hit:
                return False
            for e in hit:
                dmg = e.max * a["boss_frac"] if e.boss and "boss_frac" in a else a["dmg"]
                self.damage(e, dmg, t)
            self.effects.append([t.id, do, *[v for e in hit[:24] for v in (round(e.x, 2), round(e.y, 2))]])
        else:
            if do == "stun":
                for e in foes:
                    e.stun = max(e.stun, a["secs"] / (3 if e.boss else 1))
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
            elif do == "gold":
                for p in self.players.values():
                    if p.seated:
                        p.gold += a["gold"]
            elif do == "bounty":
                self.bounty_up = (now + a["secs"], a["more"])
            self.effects.append([t.id, do])
        t.cd = a["cd"]
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
            "map": self.map, "diff": self.diff, "wave": self.wave, "lives": self.lives, "endless": self.endless,
            "leaks": sorted([w, n] for w, n in self.leaks.items()),
            "players": [{"token": p.token, "name": p.name, "color": p.color, "gold": p.gold, "kills": p.kills,
                         "dmg": p.dmg, "spent": p.spent} for p in seated],
            "towers": [{"k": t.kind, "p": t.path, "n": t.tier, "x": t.x, "y": t.y, "s": t.spent, "kills": t.kills,
                        "dmg": t.dmg, "tg": t.target, "cd": t.cd,
                        "o": self.players[t.owner].token if t.owner in self.players else None}
                       for t in self.towers.values()],
        }
        names = ", ".join(p.name for p in seated)
        summary = (f"{D.MAPS[self.map]['name']}, {self.diff}: wave {self.wave + 1} next, "
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
            t.path, t.tier = saved["p"], saved["n"]
            t.stats = D.stats(t.kind, t.path, t.tier)
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
            self.everyone({
                "t": "s",
                "e": [[e.id, D.KINDS.index(e.kind), round(e.x, 2), round(e.y, 2), round(100 * e.hp / e.max),
                       int(e.slow > 0) | 2 * (e.burn_for > 0) | 4 * (e.stun > 0) | 8 * e.camo, round(e.taken)]
                      for e in self.enemies],
                "a": {t.id: round(t.cd, 1) for t in self.towers.values() if t.tier >= D.EVOLUTION},
                "x": self.effects,
                "gl": [round(max(0.0, until - self.fight_t), 1) for until, _ in (self.rally, self.mark, self.bounty_up)],
                "f": self.shots[-MAX_SHOTS:],
                "k": {t.id: t.kills for t in set(self.kills)},
                "g": {p.id: int(p.gold) for p in self.players.values() if p.seated},
                "n": None if self.fighting else round(max(0.0, self.next_in), 1),
            })
            self.shots = []
            self.kills = []
            self.effects = []
            for e in self.enemies:
                e.taken = 0.0

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
            "players": [{"id": p.id, "name": p.name, "color": p.color, "on": p.connected, "seated": p.seated,
                         "gold": int(p.gold), "kills": p.kills, "dmg": round(p.dmg), "spent": p.spent,
                         "ready": p.ready} for p in self.players.values()],
        }
        if self.phase != "lobby":
            nxt = self.wave + 1
            st.update(
                wave=self.wave, lives=self.lives, fighting=self.fighting, speed=self.speed,
                towers=[t.view() for t in self.towers.values()], endless=self.endless,
                coming=[[kind, count] for kind, count, _, _ in D.wave(nxt)] if nxt <= D.WAVES or self.endless else [])
        if self.phase in ("won", "lost"):
            st.update(summary=self.summary, record_new=self.record_new)
        if self.phase in ("lobby", "won", "lost") and self.saving:
            st["records"] = SAVE.records(self.map, self.diff)
        self.everyone(st)


ROOMS = Codes(ROOM_KEEP)
