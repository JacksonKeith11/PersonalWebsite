"""Frag Arena's match: one shared room for everyone connected, simulated at 30 Hz.

Players move themselves in the browser and report where they are; everything that hurts
(hitscan, rockets, splash, pickups, frags) is decided here. Bots are simulated here too.
"""

import asyncio
import json
import logging
import math
import random
import time
from collections import deque

from . import world
from .world import PHYS

log = logging.getLogger("arena")

TICK = 1 / 30
BOT_SUBSTEPS = 2
MAX_PLAYERS = 12
FRAG_LIMIT = 20
INTERMISSION = 8.0
INTERP = 0.1  # how far behind the server clients draw other players
REWIND_MAX = 0.35  # the most lag compensation a hitscan shot gets
KNOCK = 0.15  # metres per second of knockback per point of damage (Q3's 5 units per point)
FIRE_SLACK = 0.12  # how early a shot may arrive, since network jitter bunches them up
RESPAWN_MIN = 1.0
RESPAWN_AUTO = 5.0
BOT_RESPAWN = 1.5
EYE = PHYS["eye"]

WEAPONS = [
    {"key": "mg", "name": "Machine gun", "cool": 0.1, "dmg": 7, "spread": 0.025, "start": 100, "max": 200, "add": 50},
    {"key": "sg", "name": "Shotgun", "cool": 1.0, "dmg": 8, "pellets": 11, "spread": 0.085,
     "start": 10, "max": 25, "add": 5},
    {"key": "rl", "name": "Rocket launcher", "cool": 0.8, "dmg": 100, "splash": 100, "radius": 3.75, "speed": 28.0,
     "start": 10, "max": 25, "add": 5},
    {"key": "rg", "name": "Railgun", "cool": 1.5, "dmg": 100, "start": 5, "max": 15, "add": 5},
]
MG, SG, RL, RG = range(4)

PICKUP_RESPAWN = {"health": 20.0, "mega": 35.0, "armor": 25.0, "ammo": 20.0}

COLORS = ["#e8553f", "#3f8de8", "#5fc95a", "#e8c43f", "#b45fe8", "#3fd6d0",
          "#e8883f", "#e85fa8", "#8f9aa6", "#a3d65a", "#5f6ee8", "#d6a36e"]
BOT_NAMES = ["Brick", "Vex", "Nyx", "Rook", "Bolt", "Kite", "Mako", "Jinx", "Ozzy", "Pike", "Sable", "Fen"]


def _num(v, lo, hi):
    if not isinstance(v, (int, float)) or math.isnan(v) or not lo <= v <= hi:
        raise ValueError
    return float(v)


def _vec(v, lim=1000.0):
    if not isinstance(v, list) or len(v) != 3:
        raise ValueError
    return [_num(c, -lim, lim) for c in v]


def _unit(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    if n < 1e-6:
        raise ValueError
    return [v[0] / n, v[1] / n, v[2] / n]


def _dir(yaw, pitch):
    c = math.cos(pitch)
    return [-math.sin(yaw) * c, math.sin(pitch), -math.cos(yaw) * c]


def _r(x):
    return round(x, 3)


def _clean_name(name):
    if not isinstance(name, str):
        return ""
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:16]


class Player:
    def __init__(self, pid, name, color, bot=False, queue=None):
        self.id = pid
        self.name = name
        self.color = color
        self.bot = bot
        self.queue = queue
        self.body = world.Body()
        self.yaw = 0.0
        self.pitch = 0.0
        self.weapon = MG
        self.hp = 0
        self.armor = 0
        self.ammo = [w["start"] for w in WEAPONS]
        self.alive = False
        self.life = 0  # counts spawns, so stale position reports from a past life are ignored
        self.died_at = 0.0
        self.score = 0
        self.deaths = 0
        self.next_fire = 0.0
        self.history = deque()  # (time, x, y, z) for rewinding hitscan
        self.events = []  # private events for this player's next snapshot
        self.ping = 0
        self.closing = False
        self.msg_window = 0.0
        self.msg_count = 0
        self.brain = Brain() if bot else None

    @property
    def pos(self):
        return self.body.pos

    def pos_at(self, t):
        """Where other players saw this player at server time t."""
        h = self.history
        if not h or t >= h[-1][0]:
            return self.pos
        for i in range(len(h) - 1, 0, -1):
            t0, t1 = h[i - 1][0], h[i][0]
            if t0 <= t:
                f = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
                a, b = h[i - 1], h[i]
                return [a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, a[3] + (b[3] - a[3]) * f]
        return list(h[0][1:])

    def velocity(self):
        h = self.history
        if len(h) < 4:
            return self.body.vel
        a, b = h[-4], h[-1]
        dt = b[0] - a[0]
        if dt <= 0:
            return [0.0, 0.0, 0.0]
        return [(b[1] - a[1]) / dt, (b[2] - a[2]) / dt, (b[3] - a[3]) / dt]

    def eye(self):
        return [self.pos[0], self.pos[1] + EYE, self.pos[2]]


class Brain:
    """A bot's memory between thoughts."""

    def __init__(self):
        self.path = []
        self.repath_at = 0.0
        self.target = None
        self.visible = False
        self.react_at = 0.0
        self.last_seen = None
        self.last_seen_at = -99.0
        self.attacker = None
        self.strafe = 1
        self.strafe_until = 0.0
        self.best_dist = 1e9
        self.progress_at = 0.0
        self.think_at = 0.0
        self.noise = (0.0, 0.0)
        self.aim_err = 1.0


class Game:
    def __init__(self):
        self.players: dict[int, Player] = {}
        self.next_id = 1
        self.rockets = []
        self.next_rocket = 1
        self.pickups = [dict(p, up_at=0.0) for p in world.PICKUPS]
        self.events = []
        self.task = None
        self.start = time.monotonic()
        self.inter_until = 0.0
        self.roster_dirty = True
        self.roster_at = 0.0
        self.decay_at = 0.0

    # ------------------------------------------------------------ clock and sending

    def now(self):
        return time.monotonic() - self.start

    def send(self, p, data):
        if p.bot or p.closing:
            return
        text = data if isinstance(data, str) else json.dumps(data, separators=(",", ":"))
        try:
            p.queue.put_nowait(text)
        except asyncio.QueueFull:
            # Too far behind to catch up: drop them and let the client reconnect.
            p.closing = True
            while not p.queue.empty():
                p.queue.get_nowait()
            p.queue.put_nowait(None)  # tells the connection's writer to hang up
            log.info("arena: dropping %s, send queue full", p.name)

    def broadcast_msg(self, text):
        self.events.append({"k": "msg", "text": text})

    def humans(self):
        return [p for p in self.players.values() if not p.bot]

    # ------------------------------------------------------------ joining and leaving

    def join(self, queue, name):
        if len(self.humans()) >= MAX_PLAYERS:
            return None
        if len(self.players) >= MAX_PLAYERS:
            self.remove_bot()
        name = self.unique_name(_clean_name(name) or "Player")
        p = Player(self.next_id, name, self.free_color(), queue=queue)
        self.next_id += 1
        self.players[p.id] = p
        self.roster_dirty = True
        self.broadcast_msg(f"{name} joined")
        self.send(p, {
            "t": "welcome", "id": p.id, "ts": self.now(), "map": world.map_payload(), "phys": PHYS,
            "weapons": WEAPONS, "knock": KNOCK, "interp": INTERP, "limit": FRAG_LIMIT, "tick": TICK,
        })
        if self.task is None:
            self.task = asyncio.get_running_loop().create_task(self.run())
        return p

    def leave(self, p):
        if self.players.pop(p.id, None) is None:
            return
        self.roster_dirty = True
        if not p.bot:
            self.broadcast_msg(f"{p.name} left")
        for q in self.players.values():
            if q.brain and q.brain.target == p.id:
                q.brain.target = None

    def unique_name(self, name, skip=None):
        taken = {q.name for q in self.players.values() if q is not skip}
        if name not in taken:
            return name
        n = 2
        while f"{name[:13]} {n}" in taken:
            n += 1
        return f"{name[:13]} {n}"

    def free_color(self):
        used = {q.color for q in self.players.values()}
        return next((c for c in COLORS if c not in used), random.choice(COLORS))

    def add_bot(self):
        if len(self.players) >= MAX_PLAYERS:
            return False
        world.build_graph()
        used = {q.name for q in self.players.values()}
        name = next((n for n in BOT_NAMES if n not in used), self.unique_name("Bot"))
        p = Player(self.next_id, name, self.free_color(), bot=True)
        self.next_id += 1
        self.players[p.id] = p
        self.roster_dirty = True
        self.respawn(p)
        return True

    def remove_bot(self):
        bots = [p for p in self.players.values() if p.bot]
        if not bots:
            return False
        self.leave(bots[-1])
        return True

    # ------------------------------------------------------------ messages from clients

    def handle(self, p, msg):
        now = self.now()
        if now - p.msg_window > 1.0:
            p.msg_window, p.msg_count = now, 0
        p.msg_count += 1
        if p.msg_count > 150 or not isinstance(msg, dict):
            return
        t = msg.get("t")
        try:
            if t == "st":
                self.on_state(p, msg)
            elif t == "fire":
                self.on_fire(p, msg, now)
            elif t == "ping":
                p.ping = int(_num(msg.get("rtt", 0), 0, 9999))
                self.send(p, {"t": "pong", "c": msg.get("c"), "s": now})
            elif t == "spawn":
                if not p.alive and (p.life == 0 or now - p.died_at >= RESPAWN_MIN) and now >= self.inter_until:
                    self.respawn(p)
            elif t == "bot":
                op = msg.get("op")
                if op == "add" and self.add_bot():
                    self.broadcast_msg(f"{p.name} added a bot")
                elif op == "remove" and self.remove_bot():
                    self.broadcast_msg(f"{p.name} removed a bot")
                elif op == "clear":
                    n = 0
                    while self.remove_bot():
                        n += 1
                    if n:
                        self.broadcast_msg(f"{p.name} removed the bots")
            elif t == "name":
                name = _clean_name(msg.get("name"))
                if name and name != p.name:
                    new = self.unique_name(name, skip=p)
                    self.broadcast_msg(f"{p.name} is now {new}")
                    p.name = new
                    self.roster_dirty = True
        except ValueError:
            pass

    def on_state(self, p, msg):
        if not p.alive or msg.get("life") != p.life:
            return
        pos = _vec(msg.get("p"), 100.0)
        p.yaw = _num(msg.get("yaw", 0), -1e4, 1e4) % (2 * math.pi)
        p.pitch = _num(msg.get("pitch", 0), -1.6, 1.6)
        w = msg.get("w")
        if w in range(len(WEAPONS)):
            p.weapon = w
        if abs(pos[0]) > 31 or abs(pos[2]) > 31 or not -5 < pos[1] < 40 or world.inside_solid(*pos):
            return
        p.body.pos = pos
        if isinstance(msg.get("v"), list):
            p.body.vel = _vec(msg["v"], 200.0)

    def on_fire(self, p, msg, now):
        if not p.alive or now < self.inter_until:
            return
        w = msg.get("w")
        if w not in range(len(WEAPONS)) or p.ammo[w] <= 0 or now < p.next_fire - FIRE_SLACK:
            return
        origin = _vec(msg.get("o"), 100.0)
        eye = p.eye()
        if math.dist(origin, eye) > 2.5:
            origin = eye
        dirs = msg.get("d")
        if not isinstance(dirs, list) or not dirs:
            return
        dirs = [_unit(_vec(d)) for d in dirs[: WEAPONS[w].get("pellets", 1)]]
        at = _num(msg.get("at", now), -1e9, 1e9)
        lid = msg.get("lid")
        self.fire(p, w, origin, dirs, max(now - REWIND_MAX, min(at, now)), now, lid if isinstance(lid, int) else 0)

    # ------------------------------------------------------------ combat

    def fire(self, p, w, origin, dirs, at, now, lid=0):
        """`lid` is the shooter's own number for a rocket, so their browser can match it to the one it drew."""
        spec = WEAPONS[w]
        p.ammo[w] -= 1
        p.next_fire = max(p.next_fire, now - FIRE_SLACK) + spec["cool"]
        p.weapon = w
        if w == RL:
            d = dirs[0]
            r = {"id": self.next_rocket, "by": p.id, "lid": lid, "p": origin[:], "v": [c * spec["speed"] for c in d],
                 "born": now}
            self.next_rocket += 1
            self.rockets.append(r)
            self.events.append({"k": "rocket", "id": r["id"], "by": p.id, "p": [_r(c) for c in origin],
                                "v": [_r(c) for c in r["v"]]})
            return
        ends = [self.hitscan(p, w, origin, d, at) for d in dirs]
        self.events.append({"k": "shot", "w": w, "by": p.id, "o": [_r(c) for c in origin], "e": ends})

    def hitscan(self, p, w, o, d, at):
        spec = WEAPONS[w]
        far = world.ray_world(o, d, 300.0)
        hits = []
        for q in self.players.values():
            if q is p or not q.alive:
                continue
            x, y, z = q.pos_at(at)
            t = world.ray_box(*o, *d, world.player_box(x, y, z, grow=0.08), far)
            if t is not None:
                hits.append((t, q))
        hits.sort(key=lambda h: h[0])
        if w != RG:
            hits = hits[:1]
        for t, q in hits:
            self.damage(q, spec["dmg"], p, w, d)
        end = far if w == RG or not hits else hits[0][0]
        return [_r(o[i] + d[i] * end) for i in range(3)]

    def step_rockets(self, now):
        spec = WEAPONS[RL]
        keep = []
        for r in self.rockets:
            v = r["v"]
            d = [c / spec["speed"] for c in v]
            seg = spec["speed"] * TICK
            o = r["p"]
            t_world = world.ray_world(o, d, seg)
            hit_t, hit_q = t_world, None
            for q in self.players.values():
                if not q.alive or (q.id == r["by"] and now - r["born"] < 0.25):
                    continue
                t = world.ray_box(*o, *d, world.player_box(*q.pos, grow=0.1), hit_t)
                if t is not None and t < hit_t:
                    hit_t, hit_q = t, q
            if hit_q is None and t_world >= seg:
                r["p"] = [o[i] + d[i] * seg for i in range(3)]
                if now - r["born"] < 10:
                    keep.append(r)
                continue
            point = [o[i] + d[i] * max(hit_t - 0.05, 0) for i in range(3)]
            self.explode(r, point, hit_q, d)
        self.rockets = keep

    def explode(self, r, point, direct, d):
        spec = WEAPONS[RL]
        by = self.players.get(r["by"])
        self.events.append({"k": "boom", "id": r["id"], "by": r["by"], "lid": r["lid"], "p": [_r(c) for c in point]})
        if by is None:
            return  # its owner left; don't let it count as anyone's suicide
        if direct is not None:
            self.damage(direct, spec["dmg"], by, RL, d)
        for q in list(self.players.values()):
            if not q.alive or q is direct:
                continue
            b = world.player_box(*q.pos)
            near = [min(max(point[i], b[i]), b[i + 3]) for i in range(3)]
            dist = math.dist(point, near)
            if dist >= spec["radius"]:
                continue
            centre = [q.pos[0], q.pos[1] + PHYS["height"] / 2, q.pos[2]]
            if not world.clear_line(point, centre) and not world.clear_line(point, near):
                continue
            push = [centre[i] - point[i] for i in range(3)]
            push[1] += 0.25  # a little lift, so blasts on the floor pop you up
            n = math.sqrt(sum(c * c for c in push)) or 1.0
            self.damage(q, spec["splash"] * (1 - dist / spec["radius"]), by, RL,
                        [c / n for c in push], predicted=(q is by and not q.bot))

    def damage(self, t, amount, by, w, kdir, predicted=False):
        """Hurt t. `predicted` means t's own browser already applied the knockback (its own rocket)."""
        if not t.alive or self.now() < self.inter_until:
            return
        if kdir is not None and not predicted:
            k = min(amount, 200) * KNOCK
            kv = [kdir[0] * k, kdir[1] * k, kdir[2] * k]
            if t.bot:
                t.body.knock(*kv)
            else:
                t.events.append({"k": "knock", "v": [_r(c) for c in kv]})
        if by is t:
            amount *= 0.5
        amount = max(1, round(amount))
        save = min(t.armor, math.ceil(amount * 0.66))
        t.armor -= save
        t.hp -= amount - save
        src = by.pos if by else t.pos
        t.events.append({"k": "hurt", "d": amount, "from": [_r(src[0]), _r(src[2])]})
        if by is not None and by is not t:
            by.events.append({"k": "hit", "d": amount, "w": w})
            if t.brain:
                t.brain.attacker = by.id
        if t.hp <= 0:
            self.kill(t, by, w)

    def kill(self, t, by, w):
        now = self.now()
        t.alive = False
        t.died_at = now
        t.deaths += 1
        t.hp = min(t.hp, 0)
        if by is None or by is t:
            t.score -= 1
        else:
            by.score += 1
        self.events.append({"k": "kill", "by": by.id if by else 0, "to": t.id, "w": w})
        self.roster_dirty = True
        if by is not None and by is not t and by.score >= FRAG_LIMIT:
            self.inter_until = now + INTERMISSION
            self.rockets = []
            self.events.append({"k": "win", "id": by.id, "until": INTERMISSION})

    def respawn(self, p):
        others = [q.pos for q in self.players.values() if q.alive and q is not p]

        def safety(s):
            return min((math.dist(s[:3], o) for o in others), default=100.0) + random.random() * 4

        x, y, z, yaw = max(world.SPAWNS, key=safety)
        p.body = world.Body(x, y, z)
        p.yaw, p.pitch = yaw, 0.0
        p.hp, p.armor = 100, 0
        p.ammo = [w["start"] for w in WEAPONS]
        p.weapon = RL if p.bot and random.random() < 0.5 else MG
        p.alive = True
        p.life += 1
        p.next_fire = 0.0
        p.history.clear()
        p.events.append({"k": "spawn", "p": [x, y, z], "yaw": _r(yaw), "life": p.life})
        self.events.append({"k": "respawn", "id": p.id, "p": [x, y, z]})
        self.roster_dirty = True
        if p.brain:
            p.brain.__init__()

    def end_intermission(self):
        self.inter_until = 0.0
        for p in self.players.values():
            p.score = p.deaths = 0
            if p.bot or p.life > 0:  # not those still watching from the menu
                self.respawn(p)
        for pk in self.pickups:
            pk["up_at"] = 0.0
        self.roster_dirty = True

    # ------------------------------------------------------------ pickups

    def step_pickups(self, now):
        for i, pk in enumerate(self.pickups):
            if pk["up_at"] > now:
                continue
            for p in self.players.values():
                if not p.alive or abs(p.pos[1] - pk["y"]) > 1.5 or math.hypot(p.pos[0] - pk["x"], p.pos[2] - pk["z"]) > 1.1:
                    continue
                if self.take(p, pk["kind"]):
                    pk["up_at"] = now + PICKUP_RESPAWN[pk["kind"]]
                    self.events.append({"k": "pickup", "i": i, "by": p.id})
                    p.events.append({"k": "got", "kind": pk["kind"]})
                    break

    def take(self, p, kind):
        if kind == "health":
            if p.hp >= 100:
                return False
            p.hp = min(100, p.hp + 25)
        elif kind == "mega":
            if p.hp >= 200:
                return False
            p.hp = min(200, p.hp + 100)
        elif kind == "armor":
            if p.armor >= 200:
                return False
            p.armor = min(200, p.armor + 50)
        elif kind == "ammo":
            if all(a >= w["max"] for a, w in zip(p.ammo, WEAPONS)):
                return False
            p.ammo = [min(w["max"], a + w["add"]) for a, w in zip(p.ammo, WEAPONS)]
        return True

    # ------------------------------------------------------------ bots

    def bot_think(self, p, now):
        b = p.brain
        eye = p.eye()
        fwd = _dir(p.yaw, 0)
        best, best_score = None, 1e9
        for q in self.players.values():
            if q is p or not q.alive:
                continue
            centre = [q.pos[0], q.pos[1] + 1.0, q.pos[2]]
            d = math.dist(eye, centre)
            if d > 70:
                continue
            known = q.id in (b.target, b.attacker)
            if not known and d > 3:
                cos = ((centre[0] - eye[0]) * fwd[0] + (centre[2] - eye[2]) * fwd[2]) / max(
                    math.hypot(centre[0] - eye[0], centre[2] - eye[2]), 1e-6)
                if cos < 0.3:  # outside a ~145 degree view
                    continue
            if not world.clear_line(eye, centre) and not world.clear_line(eye, [q.pos[0], q.pos[1] + EYE, q.pos[2]]):
                continue
            score = d * (0.6 if known else 1.0)
            if score < best_score:
                best, best_score = q, score
        if best is not None:
            if best.id != b.target:
                b.react_at = now + 0.3 + random.random() * 0.3
            b.target = best.id
            b.visible = True
            b.last_seen = best.pos[:]
            b.last_seen_at = now
            b.path = []
            d = math.dist(p.pos, best.pos)
            p.weapon = self.bot_weapon(p, d, best)
            wobble = 2.2 if p.weapon == RG else 1.0  # bots one-shotting everyone with the rail isn't fun
            b.noise = (random.gauss(0, 0.03 * wobble), random.gauss(0, 0.02 * wobble))
        else:
            b.visible = False
            if b.target is not None and now - b.last_seen_at > 3:
                b.target = None
            b.attacker = None
            if not b.path or now > b.repath_at:
                self.bot_goal(p, now)

    def bot_weapon(self, p, d, q):
        a = p.ammo
        if d < 7 and a[SG] > 0:
            return SG
        if d < 22 and a[RL] > 0 and q.pos[1] < p.pos[1] + 2.5:
            return RL
        if d > 18 and a[RG] > 0:
            return RG
        if a[MG] > 0:
            return MG
        return next((i for i in (RL, RG, SG) if a[i] > 0), MG)

    def bot_goal(self, p, now):
        b = p.brain
        up = [pk for pk in self.pickups if pk["up_at"] <= now]
        goal = None
        wanted = []
        if p.hp < 70:
            wanted = [pk for pk in up if pk["kind"] in ("health", "mega")]
        elif p.armor < 50 and random.random() < 0.5:
            wanted = [pk for pk in up if pk["kind"] in ("armor", "mega")]
        elif sum(p.ammo[1:]) < 8:
            wanted = [pk for pk in up if pk["kind"] == "ammo"]
        if wanted:
            pk = min(wanted, key=lambda k: math.dist(p.pos, (k["x"], k["y"], k["z"])))
            goal = world.nearest_node(pk["x"], pk["y"], pk["z"])
        elif b.last_seen and now - b.last_seen_at < 6 and random.random() < 0.7:
            goal = world.nearest_node(*b.last_seen)
        else:
            goal = random.randrange(len(world.NODES))
        start = world.nearest_node(*p.pos)
        b.path = world.path(start, goal)
        b.repath_at = now + 8
        b.best_dist = 1e9
        b.progress_at = now

    def bot_tick(self, p, now, dt):
        b = p.brain
        if now >= b.think_at:
            b.think_at = now + 0.1 + random.random() * 0.05
            self.bot_think(p, now)
        wx = wz = 0.0
        jump = False
        q = self.players.get(b.target) if b.visible else None
        if q is not None and q.alive:
            spec = WEAPONS[p.weapon]
            eye = p.eye()
            aim = [q.pos[0], q.pos[1] + 1.1, q.pos[2]]
            if p.weapon == RL:
                fly = math.dist(eye, aim) / spec["speed"]
                v = q.velocity()
                aim = [q.pos[0] + v[0] * fly * 0.8, q.pos[1] + 0.3, q.pos[2] + v[2] * fly * 0.8]
                if not world.clear_line(eye, aim):
                    aim = [q.pos[0], q.pos[1] + 1.0, q.pos[2]]
            dx, dy, dz = aim[0] - eye[0], aim[1] - eye[1], aim[2] - eye[2]
            want_yaw = math.atan2(-dx, -dz) + b.noise[0]
            want_pitch = math.atan2(dy, math.hypot(dx, dz)) + b.noise[1]
            dyaw = (want_yaw - p.yaw + math.pi) % (2 * math.pi) - math.pi
            turn = 7.0 * dt
            p.yaw = (p.yaw + max(-turn, min(turn, dyaw))) % (2 * math.pi)
            dp = want_pitch - p.pitch
            p.pitch = max(-1.5, min(1.5, p.pitch + max(-turn, min(turn, dp))))
            b.aim_err = abs(dyaw) + abs(dp)
            limit = {MG: 0.12, SG: 0.18, RL: 0.1, RG: 0.05}[p.weapon]
            if now >= b.react_at and now >= p.next_fire and b.aim_err < limit and p.ammo[p.weapon] > 0 \
                    and now >= self.inter_until:
                self.bot_fire(p, now)

            # Fight: strafe, and close or open the distance toward what suits the weapon.
            d = math.hypot(q.pos[0] - p.pos[0], q.pos[2] - p.pos[2]) or 1.0
            fx, fz = (q.pos[0] - p.pos[0]) / d, (q.pos[2] - p.pos[2]) / d
            want = {MG: 12, SG: 4, RL: 9, RG: 25}[p.weapon]
            radial = 1.0 if d > want + 3 else -0.7 if d < want - 3 else 0.0
            if now > b.strafe_until:
                b.strafe = -b.strafe if random.random() < 0.7 else b.strafe
                b.strafe_until = now + 0.4 + random.random() * 0.9
            wx = fx * radial - fz * b.strafe
            wz = fz * radial + fx * b.strafe
            jump = random.random() < 0.015
        elif b.path:
            nx, ny, nz = world.NODES[b.path[0]]
            dx, dz = nx - p.pos[0], nz - p.pos[2]
            dist = math.hypot(dx, dz)
            if dist < 0.8 and abs(ny - p.pos[1]) < 1.2:
                b.path.pop(0)
                b.best_dist = 1e9
                b.progress_at = now
            else:
                wx, wz = dx / dist, dz / dist
                if dist < b.best_dist - 0.3:
                    b.best_dist = dist
                    b.progress_at = now
                stuck = now - b.progress_at
                if stuck > 1.0 and p.body.ground:
                    jump = True
                if stuck > 2.5:
                    b.path = []
                want_yaw = math.atan2(-dx, -dz)
                dyaw = (want_yaw - p.yaw + math.pi) % (2 * math.pi) - math.pi
                p.yaw = (p.yaw + max(-4 * dt, min(4 * dt, dyaw))) % (2 * math.pi)
                p.pitch *= 0.9
        sub = dt / BOT_SUBSTEPS
        for _ in range(BOT_SUBSTEPS):
            world.move(p.body, wx, wz, jump, sub)
            jump = False
        if p.pos[1] < -20:
            self.damage(p, 999, None, MG, None)

    def bot_fire(self, p, now):
        spec = WEAPONS[p.weapon]
        o = p.eye()
        base = _dir(p.yaw, p.pitch)
        dirs = [base]
        if p.weapon in (MG, SG):
            n = spec.get("pellets", 1)
            dirs = [_unit([c + random.gauss(0, spec["spread"] * 0.6) for c in base]) for _ in range(n)]
        self.fire(p, p.weapon, o, dirs, now, now)

    # ------------------------------------------------------------ the loop

    async def run(self):
        log.info("arena: match started")
        next_t = time.monotonic()
        try:
            while self.humans():
                try:
                    self.tick()
                except Exception:
                    log.exception("arena: tick failed")
                next_t += TICK
                delay = next_t - time.monotonic()
                if delay < -0.5:
                    next_t = time.monotonic()
                await asyncio.sleep(max(0.0, delay))
        finally:
            self.task = None
            for p in [p for p in self.players.values() if p.bot]:
                self.players.pop(p.id)
            self.rockets = []
            self.inter_until = 0.0
            log.info("arena: match empty, stopped")

    def tick(self):
        now = self.now()
        if self.inter_until and now >= self.inter_until:
            self.end_intermission()
        for p in list(self.players.values()):
            if p.bot:
                if p.alive:
                    self.bot_tick(p, now, TICK)
                elif now - p.died_at >= BOT_RESPAWN and now >= self.inter_until:
                    self.respawn(p)
            elif not p.alive and p.life > 0 and now - p.died_at >= RESPAWN_AUTO and now >= self.inter_until:
                self.respawn(p)
        self.step_rockets(now)
        self.step_pickups(now)
        if now >= self.decay_at:
            self.decay_at = now + 1.0
            for p in self.players.values():
                if p.hp > 100:
                    p.hp -= 1
                if p.armor > 100:
                    p.armor -= 1
        for p in self.players.values():
            if p.alive:
                p.history.append((now, *p.pos))
                while p.history and p.history[0][0] < now - 1.0:
                    p.history.popleft()
        self.broadcast(now)

    def broadcast(self, now):
        if self.roster_dirty or now - self.roster_at > 2:
            self.roster_dirty = False
            self.roster_at = now
            roster = {"t": "roster", "list": [
                [p.id, p.name, p.color, p.score, p.deaths, int(p.bot), p.ping, int(p.bot or p.life > 0)]
                for p in self.players.values()
            ]}
            for p in self.humans():
                self.send(p, roster)
        common = {
            "t": "s", "ts": round(now, 4),
            "p": [[p.id, _r(p.pos[0]), _r(p.pos[1]), _r(p.pos[2]), _r(p.yaw), _r(p.pitch), p.weapon, int(p.alive)]
                  for p in self.players.values()],
            "pk": "".join("1" if pk["up_at"] <= now else "0" for pk in self.pickups),
            "ev": self.events,
        }
        head = json.dumps(common, separators=(",", ":"))[:-1]
        self.events = []
        for p in self.humans():
            me = [p.hp, p.armor, *p.ammo, int(p.alive), p.life]
            self.send(p, f'{head},"me":{json.dumps(me)},"pv":{json.dumps(p.events, separators=(",", ":"))}}}')
            p.events = []


GAME = Game()
