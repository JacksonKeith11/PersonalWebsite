"""Frag Arena's match: one shared room for everyone connected, simulated at 30 Hz.

Players move themselves in the browser and report where they are; everything that hurts
(hitscan, projectiles, splash, black holes, pickups, frags) is decided here, as are the round's
rules (the mode and mutators anyone can pick from the menu). Bots are simulated here too.
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
AWAY_KEEP = 20 * 60  # how long someone who left keeps their place (score, colour) for a rejoin
POWER_FIRST = 15.0  # seconds into a match before the first power weapon
POWER_GAP = (30.0, 50.0)  # seconds between one being taken and the next appearing
POWER_WAIT = 45.0  # one nobody takes vanishes after this, and turns up elsewhere soon after
FRENZY = {"first": 3.0, "gap": (4.0, 8.0), "wait": 20.0}  # the power frenzy mutator's timings
INFECT_START = 10.0  # seconds into an Infection round before the first zombie is picked
INFECT_TIME = 180.0  # survive this long after that and the humans win
ZOMBIE_FAST = 1.25  # zombies' run speed, times everyone else's
JUGG_HP, JUGG_ARMOR = 300, 100
JUGG_RECHARGE = 5.0  # the Juggernaut's power weapon gets a charge back this often
LOW_GRAV = 0.45  # gravity under the low gravity mutator, times normal
INSTA_DMG = 300  # a rail under instagib: kills anyone but a Juggernaut
EYE = PHYS["eye"]

# The first three are what everyone carries. The rest are power weapons: one at a time appears at
# a power spot, holding a few charges; holding one replaces any other, and it's lost on death.
# `kind` says how it fires; the browser draws and predicts by `key`.
WEAPONS = [
    {"key": "mg", "name": "Machine gun", "short": "MG", "kind": "hitscan", "cool": 0.09, "dmg": 11,
     "spread": 0.018, "start": 150, "max": 250, "add": 60},
    {"key": "sg", "name": "Shotgun", "short": "SG", "kind": "hitscan", "cool": 1.0, "dmg": 8, "pellets": 11,
     "spread": 0.085, "start": 10, "max": 25, "add": 5},
    {"key": "rl", "name": "Rocket launcher", "short": "RL", "kind": "rocket", "cool": 0.8, "dmg": 100,
     "splash": 100, "radius": 3.75, "speed": 28.0, "start": 10, "max": 25, "add": 5},
    {"key": "rg", "name": "Railgun", "short": "RAIL", "kind": "hitscan", "power": True, "pierce": True,
     "cool": 1.5, "dmg": 100, "charge": 6, "blurb": "One-shots anyone not armored, through a whole line of them"},
    {"key": "vx", "name": "Vortex", "short": "VORTEX", "kind": "vortex", "power": True, "cool": 1.4, "dmg": 30,
     "speed": 20.0, "pull": 26.0, "reach": 9.0, "time": 2.6, "core_dmg": 6, "splash": 90, "radius": 4.5,
     "charge": 3, "blurb": "Fires a black hole that drags everyone in, then bursts"},
    {"key": "io", "name": "Ion orb", "short": "ION", "kind": "orb", "power": True, "cool": 1.6, "speed": 8.0,
     "zap": 12, "zap_every": 0.25, "zap_reach": 9.0, "life": 6.0, "dmg": 110, "splash": 110, "radius": 5.0,
     "charge": 2, "blurb": "A slow orb that zaps everyone near it, then blows up"},
    {"key": "sw", "name": "Swapper", "short": "SWAP", "kind": "hitscan", "power": True, "swap": True,
     "cool": 0.9, "dmg": 15, "grow": 0.2, "charge": 5, "blurb": "Trade places with whoever you hit"},
    {"key": "yt", "name": "Yeet cannon", "short": "YEET", "kind": "hitscan", "power": True, "yeet": True,
     "cool": 0.8, "dmg": 20, "grow": 0.35, "push": 26.0, "lift": 9.0, "recoil": 9.0, "charge": 6,
     "blurb": "Blasts whoever it hits across the map, and you backwards"},
    # Only in some modes: Gun Game's last rung (and always to hand there), and zombies' only weapon.
    {"key": "kn", "name": "Knife", "short": "KNIFE", "kind": "hitscan", "melee": True, "cool": 0.45, "dmg": 200,
     "range": 2.4, "grow": 0.3, "start": 0, "max": 0, "add": 0},
]
for _w in WEAPONS:
    if _w.get("power"):
        _w.update(start=0, max=_w["charge"], add=0)
MG, SG, RL, RG, VX, IO, SW, YT, KN = range(len(WEAPONS))
POWER = [i for i, w in enumerate(WEAPONS) if w.get("power")]

# The round's mode, picked from the menu by anyone; changing it starts a new round.
GUN_LADDER = [MG, SG, RL, IO, VX, RG, KN]  # Gun Game: two kills on each, then a knife kill wins
GUN_KILLS = 2
MODES = {
    "dm": {"name": "Deathmatch", "limit": FRAG_LIMIT},
    "gun": {"name": "Gun Game", "limit": GUN_KILLS * (len(GUN_LADDER) - 1) + 1},
    "infect": {"name": "Infection", "limit": 0},
    "jugg": {"name": "Juggernaut", "limit": 10},
}
# Mutators, any mix of them, on top of the mode.
MUTATORS = {"lowgrav": "low gravity", "insta": "instagib", "rockets": "rockets only", "bigheads": "big heads",
            "frenzy": "power frenzy"}

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


def _rv(v):
    return [round(c, 3) for c in v]


def _clean(text, n):
    if not isinstance(text, str):
        return ""
    return "".join(ch for ch in text if ch.isprintable()).strip()[:n]


class Player:
    def __init__(self, pid, name, color, bot=False, queue=None, token=None, tab=None):
        self.id = pid
        self.name = name
        self.color = color
        self.bot = bot
        self.queue = queue
        self.token = token  # the browser's id, so leaving and coming back keeps your place
        self.tab = tab  # which tab of that browser holds the connection
        self.left_at = 0.0
        self.playing = False  # has pressed Play since connecting (else watching from the menu)
        self.body = world.Body()
        self.yaw = 0.0
        self.pitch = 0.0
        self.weapon = MG
        self.hp = 0
        self.armor = 0
        self.ammo = [w["start"] for w in WEAPONS]
        self.alive = False
        self.life = 0  # counts spawns, so stale position reports from a past life are ignored
        self.warp = 0  # counts teleports (the Swapper), for the same reason
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
        self.role = ""  # "zombie" (Infection) or "jugg" (the Juggernaut)
        self.jugg_w = None  # the Juggernaut's power weapon, which recharges
        self.recharge_at = 0.0
        self.kit_sent = None  # the last kit this player's browser was told about

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

    def centre(self):
        return [self.pos[0], self.pos[1] + PHYS["height"] / 2, self.pos[2]]

    def power(self):
        """The power weapon held, or None."""
        return next((w for w in POWER if self.ammo[w] > 0), None)


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
        self.rush = False  # heading for a power weapon, fight or no fight


class Game:
    def __init__(self):
        self.players: dict[int, Player] = {}
        self.away: dict[str, Player] = {}  # players who left, by browser token, for rejoining
        self.next_id = 1
        self.shots = []  # projectiles in flight: rockets, vortex shells, ion orbs
        self.next_shot = 1
        self.vortices = []
        self.pickups = [dict(p, up_at=0.0) for p in world.PICKUPS]
        self.power = None  # {"w", "spot"} while a power weapon waits to be picked up
        self.power_at = 0.0
        self.last_spot = None
        self.events = []
        self.task = None
        self.start = time.monotonic()
        self.inter_until = 0.0
        self.roster_dirty = True
        self.roster_at = 0.0
        self.decay_at = 0.0
        self.mode = "dm"
        self.muts = set()
        self.rotate = False  # move to the next map after each round
        self.knock = KNOCK
        self.infect_on = False  # Infection: the first zombie has been picked
        self.alpha_at = 0.0
        self.round_end = 0.0  # Infection: when the survivors win
        self.last_human = None
        self.rules_at = -9.0

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
            log.info("arena: dropping %s, send queue full", p.name)
            self.hang_up(p.queue)
            p.closing = True

    @staticmethod
    def hang_up(queue):
        while not queue.empty():
            queue.get_nowait()
        queue.put_nowait(None)  # tells the connection's writer to close the socket

    def broadcast_msg(self, text):
        self.events.append({"k": "msg", "text": text})

    def humans(self):
        return [p for p in self.players.values() if not p.bot]

    # ------------------------------------------------------------ joining and leaving

    def join(self, queue, name, token="", tab=""):
        """Seat a new connection: the same player again if this browser was here before."""
        now = self.now()
        for k in [k for k, p in self.away.items() if now - p.left_at > AWAY_KEEP]:
            del self.away[k]
        token, tab, name = _clean(token, 40), _clean(tab, 40), _clean(name, 16)
        live = next((p for p in self.humans() if token and p.token == token), None)
        if live is not None and live.tab != tab:
            token = ""  # a second tab of the same browser: a separate player, not remembered
            live = None
        if live is not None:
            # A reload or reconnect of the same tab: hand the player over to the new socket.
            old = live.queue
            live.queue = queue
            live.closing = False
            live.events = []
            live.playing = live.alive
            self.hang_up(old)
            p = live
        elif token and token in self.away:
            if len(self.humans()) >= MAX_PLAYERS:
                return None
            p = self.away.pop(token)
            p.queue, p.tab, p.closing, p.events, p.playing = queue, tab, False, [], False
            if any(q.color == p.color for q in self.players.values()):
                p.color = self.free_color()
            if len(self.players) >= MAX_PLAYERS:
                self.remove_bot()
            p.name = self.unique_name(name or p.name)
            self.players[p.id] = p
            self.broadcast_msg(f"{p.name} is back")
        else:
            if len(self.humans()) >= MAX_PLAYERS:
                return None
            if len(self.players) >= MAX_PLAYERS:
                self.remove_bot()
            name = self.unique_name(name or "Player")
            p = Player(self.next_id, name, self.free_color(), queue=queue, token=token or None, tab=tab)
            self.next_id += 1
            self.players[p.id] = p
            self.broadcast_msg(f"{name} joined")
        self.roster_dirty = True
        self.send(p, {
            "t": "welcome", "id": p.id, "ts": now, "map": world.map_payload(), "phys": PHYS,
            "weapons": WEAPONS, "knock": self.knock, "interp": INTERP, "limit": self.limit(), "tick": TICK,
            "modes": {k: m["name"] for k, m in MODES.items()}, "mutators": MUTATORS,
            "maps": {k: [m[0], m[2]] for k, m in world.MAPS.items()},
        })
        self.send(p, self.rules())
        p.kit_sent = None
        if p.alive:
            # Carry on where they were.
            p.events.append({"k": "spawn", "p": _rv(p.pos), "yaw": _r(p.yaw), "life": p.life, "warp": p.warp,
                             "w": p.weapon})
        if self.task is None:
            self.task = asyncio.get_running_loop().create_task(self.run())
        return p

    def leave(self, p, queue=None):
        """A connection closed. `queue` is that connection's; if someone took over since, ignore it."""
        if queue is not None and p.queue is not queue:
            return
        if self.players.pop(p.id, None) is None:
            return
        self.roster_dirty = True
        for q in self.players.values():
            if q.brain and q.brain.target == p.id:
                q.brain.target = None
        if p.role == "jugg":
            self.broadcast_msg("The Juggernaut left")
        self.set_role(p, "")
        if p.bot:
            return
        self.broadcast_msg(f"{p.name} left")
        if p.token:
            p.alive = False
            p.left_at = self.now()
            for w in POWER:
                p.ammo[w] = 0
            self.away[p.token] = p

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
        p.playing = True
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
                if not p.playing:
                    p.playing = True
                    self.roster_dirty = True
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
            elif t == "rules":
                mode, muts = msg.get("mode"), msg.get("muts")
                key, rotate = msg.get("map", world.MAP["key"]), bool(msg.get("rotate", self.rotate))
                if mode not in MODES or not isinstance(muts, list) or key not in world.MAPS \
                        or now - self.rules_at < 1.0:
                    return
                muts = {m for m in muts if m in MUTATORS}
                if rotate != self.rotate:
                    self.rotate = rotate
                    self.broadcast_msg(f"{p.name} turned map rotation {'on' if rotate else 'off'}")
                    self.send_rules()
                if mode != self.mode or muts != self.muts or key != world.MAP["key"]:
                    self.rules_at = now
                    self.mode, self.muts = mode, muts
                    if key != world.MAP["key"]:
                        self.set_map(key)
                    self.new_round()
                    self.broadcast_msg(f"{p.name} switched to {self.describe()}")
            elif t == "name":
                name = _clean(msg.get("name"), 16)
                if name and name != p.name:
                    new = self.unique_name(name, skip=p)
                    self.broadcast_msg(f"{p.name} is now {new}")
                    p.name = new
                    self.roster_dirty = True
        except ValueError:
            pass

    def on_state(self, p, msg):
        if not p.alive or msg.get("life") != p.life or msg.get("warp", 0) != p.warp:
            return
        pos = _vec(msg.get("p"), 100.0)
        p.yaw = _num(msg.get("yaw", 0), -1e4, 1e4) % (2 * math.pi)
        p.pitch = _num(msg.get("pitch", 0), -1.6, 1.6)
        w = msg.get("w")
        if w in self.kit(p)[0] and p.ammo[w] > 0:
            p.weapon = w
        if abs(pos[0]) > world.HALF[0] + 1 or abs(pos[2]) > world.HALF[1] + 1 or not -5 < pos[1] < 60 \
                or world.inside_solid(*pos):
            return
        p.body.pos = pos
        if isinstance(msg.get("v"), list):
            p.body.vel = _vec(msg["v"], 200.0)

    def on_fire(self, p, msg, now):
        if not p.alive or now < self.inter_until:
            return
        w = msg.get("w")
        if w not in self.kit(p)[0] or p.ammo[w] <= 0 or now < p.next_fire - FIRE_SLACK:
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
        if w not in self.kit(p)[1]:
            p.ammo[w] -= 1
        p.next_fire = max(p.next_fire, now - FIRE_SLACK) + spec["cool"]
        p.weapon = w
        if spec.get("power") and p.ammo[w] <= 0:
            p.weapon = MG
        if spec["kind"] in ("rocket", "vortex", "orb"):
            d = dirs[0]
            s = {"id": self.next_shot, "w": w, "by": p.id, "lid": lid, "p": origin[:],
                 "v": [c * spec["speed"] for c in d], "born": now, "zap_at": now + spec.get("zap_every", 0)}
            self.next_shot += 1
            self.shots.append(s)
            self.events.append({"k": "proj", "id": s["id"], "w": w, "by": p.id, "p": _rv(origin), "v": _rv(s["v"])})
            return
        if spec.get("yeet") and p.bot:
            p.body.knock(*[-c * spec["recoil"] for c in dirs[0]])  # a person's browser applies its own
        ends = [self.hitscan(p, w, origin, d, at) for d in dirs]
        self.events.append({"k": "shot", "w": w, "by": p.id, "o": _rv(origin), "e": ends})

    def hitscan(self, p, w, o, d, at):
        spec = WEAPONS[w]
        far = world.ray_world(o, d, spec.get("range", 300.0))
        hits = []
        for q in self.players.values():
            if q is p or not q.alive:
                continue
            x, y, z = q.pos_at(at)
            t = world.ray_box(*o, *d, world.player_box(x, y, z, grow=spec.get("grow", 0.08)), far)
            if t is not None:
                hits.append((t, q))
        hits.sort(key=lambda h: h[0])
        if not spec.get("pierce"):
            hits = hits[:1]
        for _, q in hits:
            if spec.get("swap"):
                self.swap(p, q)
                self.damage(q, spec["dmg"], p, w, None)
            elif spec.get("yeet"):
                fling = [d[0] * spec["push"], d[1] * spec["push"] + spec["lift"], d[2] * spec["push"]]
                self.push(q, fling)
                self.damage(q, spec["dmg"], p, w, None)
            else:
                self.damage(q, spec["dmg"], p, w, d)
        end = far if spec.get("pierce") or not hits else hits[0][0]
        return [_r(o[i] + d[i] * end) for i in range(3)]

    def push(self, q, v):
        """Change q's velocity: directly for a bot, through their browser for a person."""
        if q.bot:
            q.body.knock(*v)
        else:
            q.events.append({"k": "knock", "v": _rv(v)})

    def teleport(self, q, pos):
        q.body.pos = pos[:]
        q.body.vel = [0.0, 0.0, 0.0]
        q.body.ground = False
        q.history.clear()
        q.warp += 1
        if not q.bot:
            q.events.append({"k": "tp", "p": _rv(pos), "warp": q.warp})

    def swap(self, a, b):
        pa, pb = a.pos[:], b.pos[:]
        self.teleport(a, pb)
        self.teleport(b, pa)
        self.events.append({"k": "swap", "a": _rv(pa), "b": _rv(pb), "by": a.id})

    def step_shots(self, now):
        keep = []
        for s in self.shots:
            spec = WEAPONS[s["w"]]
            if s["w"] == IO and now >= s["zap_at"]:
                s["zap_at"] = now + spec["zap_every"]
                self.zap(s, spec)
            d = [c / spec["speed"] for c in s["v"]]
            seg = spec["speed"] * TICK
            o = s["p"]
            t_world = world.ray_world(o, d, seg)
            hit_t, hit_q = t_world, None
            for q in self.players.values():
                if not q.alive or (q.id == s["by"] and now - s["born"] < 0.25):
                    continue
                t = world.ray_box(*o, *d, world.player_box(*q.pos, grow=0.1), hit_t)
                if t is not None and t < hit_t:
                    hit_t, hit_q = t, q
            expired = now - s["born"] > spec.get("life", 10.0)
            if hit_q is None and t_world >= seg and not expired:
                s["p"] = [o[i] + d[i] * seg for i in range(3)]
                keep.append(s)
                continue
            point = [o[i] + d[i] * max(min(hit_t, seg) - 0.05, 0) for i in range(3)]
            by = self.players.get(s["by"])
            self.events.append({"k": "boom", "id": s["id"], "w": s["w"], "by": s["by"], "lid": s["lid"],
                                "p": _rv(point)})
            if by is None:
                continue  # its owner left; don't let it count as anyone's suicide
            if s["w"] == VX:
                if hit_q is not None:
                    self.damage(hit_q, spec["dmg"], by, VX, d)
                core = [point[0] - d[0] * 0.4, point[1] + 1.0, point[2] - d[2] * 0.4]
                if world.inside_solid(core[0], core[1] - 0.9, core[2]):
                    core = point
                self.vortices.append({"id": s["id"], "by": s["by"], "p": core, "until": now + spec["time"]})
                self.events.append({"k": "vortex", "id": s["id"], "p": _rv(core), "t": spec["time"]})
            else:
                self.explode(point, by, s["w"], hit_q, d)
        self.shots = keep

    def zap(self, s, spec):
        by = self.players.get(s["by"])
        if by is None:
            return
        for q in list(self.players.values()):
            if q is by or not q.alive:
                continue
            c = q.centre()
            if math.dist(c, s["p"]) > spec["zap_reach"] or not world.clear_line(s["p"], c):
                continue
            self.events.append({"k": "zap", "a": _rv(s["p"]), "b": _rv(c)})
            self.damage(q, spec["zap"], by, IO, None)

    def step_vortices(self, now):
        spec = WEAPONS[VX]
        keep = []
        for v in self.vortices:
            by = self.players.get(v["by"])
            if now >= v["until"] or by is None:
                if by is not None:
                    self.explode(v["p"], by, VX, None, None, outward=True)
                self.events.append({"k": "vend", "id": v["id"], "p": _rv(v["p"])})
                continue
            keep.append(v)
            core = v["p"]
            hurt = int(now / 0.25) != int((now - TICK) / 0.25)  # four times a second
            for q in list(self.players.values()):
                if not q.alive:
                    continue
                c = q.centre()
                dist = math.dist(c, core)
                if dist > spec["reach"] or dist < 0.05 or not world.clear_line(core, c):
                    continue
                # Pull toward the core, harder up close; owners feel half of it.
                f = spec["pull"] * TICK * (1.2 - 0.6 * dist / spec["reach"]) * (0.5 if q is by else 1.0)
                pull = [(core[i] - c[i]) / dist * f for i in range(3)]
                pull[1] += PHYS["gravity"] * TICK * 0.6  # half-cancel gravity, so you float in
                # damp motion across the pull, so people spiral in rather than orbit forever
                vel = q.body.vel
                pull = [pull[i] - vel[i] * 0.06 for i in range(3)]
                self.push(q, pull)
                if hurt and dist < 2.5 and q is not by:
                    self.damage(q, spec["core_dmg"], by, VX, None)
        self.vortices = keep

    def explode(self, point, by, w, direct, d, outward=False):
        spec = WEAPONS[w]
        if direct is not None:
            self.damage(direct, spec["dmg"], by, w, d)
        for q in list(self.players.values()):
            if not q.alive or q is direct:
                continue
            b = world.player_box(*q.pos)
            near = [min(max(point[i], b[i]), b[i + 3]) for i in range(3)]
            dist = math.dist(point, near)
            if dist >= spec["radius"]:
                continue
            centre = q.centre()
            if not world.clear_line(point, centre) and not world.clear_line(point, near):
                continue
            push = [centre[i] - point[i] for i in range(3)]
            push[1] += 0.25  # a little lift, so blasts on the floor pop you up
            n = math.sqrt(sum(c * c for c in push)) or 1.0
            mine = q is by and not q.bot and w == RL and not outward
            self.damage(q, spec["splash"] * (1 - dist / spec["radius"]), by, w, [c / n for c in push], predicted=mine)

    def damage(self, t, amount, by, w, kdir, predicted=False):
        """Hurt t. `predicted` means t's own browser already applied the knockback (its own rocket)."""
        if not t.alive or self.now() < self.inter_until or self.friendly(by, t):
            return
        if w == RG and "insta" in self.muts:
            amount = INSTA_DMG
        if kdir is not None and not predicted:
            k = min(amount, 200) * self.knock
            self.push(t, [kdir[0] * k, kdir[1] * k, kdir[2] * k])
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
        for pw in POWER:
            t.ammo[pw] = 0
        self.events.append({"k": "kill", "by": by.id if by else 0, "to": t.id, "w": w})
        self.roster_dirty = True
        killer = by if by is not None and by is not t else None
        if self.mode == "dm":
            if killer is None:
                t.score -= 1
            else:
                killer.score += 1
        elif self.mode == "gun":
            # Any kill moves you up; dying by your own hand or a knife moves you back one.
            if killer is not None:
                killer.score += 1
            if killer is None or w == KN:
                t.score = max(0, t.score - 1)
        elif self.mode == "infect":
            if t.role != "zombie" and self.infect_on:
                if killer is not None:
                    killer.score += 1
                self.set_role(t, "zombie")
                self.broadcast_msg(f"{t.name} was infected")
            elif t.role == "zombie" and killer is not None:
                killer.score += 1
        elif self.mode == "jugg":
            jugg = self.juggernaut()
            if t is jugg or jugg is None:
                self.set_role(t, "")
                if killer is not None:
                    killer.score += 1
                    self.set_role(killer, "jugg")
                    self.broadcast_msg(f"{killer.name} is the Juggernaut")
                elif t is jugg:
                    self.broadcast_msg("The Juggernaut fell; the next kill takes the mantle")
            elif killer is jugg:
                killer.score += 1
        limit = self.limit()
        if limit and killer is not None and killer.score >= limit:
            self.end_round(killer)

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
        if self.mode == "infect" and self.infect_on:
            p.role = "zombie"  # the dead come back as zombies, and so does anyone joining late
        if p.role == "jugg":  # made Juggernaut by a rocket that landed after they died
            p.hp, p.armor = JUGG_HP, JUGG_ARMOR
            if p.jugg_w is not None:
                p.ammo[p.jugg_w] = WEAPONS[p.jugg_w]["charge"]
        p.body.fast = ZOMBIE_FAST if p.role == "zombie" else 1.0
        self.sync_kit(p)
        p.alive = True
        p.life += 1
        p.next_fire = 0.0
        p.history.clear()
        p.events.append({"k": "spawn", "p": [x, y, z], "yaw": _r(yaw), "life": p.life, "warp": p.warp,
                         "w": p.weapon})
        self.events.append({"k": "respawn", "id": p.id, "p": [x, y, z]})
        self.roster_dirty = True
        if p.brain:
            p.brain.__init__()

    def clear_shots(self):
        """Drop every projectile and black hole, telling browsers so they stop drawing them."""
        if self.shots:
            self.events.append({"k": "gone", "ids": [sh["id"] for sh in self.shots]})
        for v in self.vortices:
            self.events.append({"k": "vend", "id": v["id"], "p": _rv(v["p"])})
        self.shots = []
        self.vortices = []

    def end_round(self, winner, text=None):
        self.inter_until = self.now() + INTERMISSION
        self.clear_shots()
        self.events.append({"k": "win", "id": winner.id if winner else 0, "until": INTERMISSION, "text": text})

    def new_round(self):
        """Scores reset and everyone playing respawns; also how a change of mode or mutators starts."""
        now = self.now()
        self.inter_until = 0.0
        self.clear_shots()
        PHYS.update(world.BASE_PHYS)
        self.knock = KNOCK
        if "lowgrav" in self.muts:
            # Jumps go higher. Pads and rocket blasts are scaled so they carry you just as high.
            PHYS["gravity"] *= LOW_GRAV
            PHYS["pad_mul"] = math.sqrt(LOW_GRAV)
            self.knock = KNOCK * math.sqrt(LOW_GRAV)
        self.infect_on = False
        self.alpha_at = now + INFECT_START
        self.round_end = 0.0
        self.last_human = None
        if self.power:
            self.events.append({"k": "power", "w": None, "spot": self.power["spot"]})
        self.power = None
        self.power_at = 0.0
        for p in [*self.players.values(), *self.away.values()]:
            p.score = p.deaths = 0
            self.set_role(p, "")
            for w in POWER:
                p.ammo[w] = 0
        for p in self.players.values():
            if p.bot or p.playing:  # not those still watching from the menu
                self.respawn(p)
        for pk in self.pickups:
            pk["up_at"] = 0.0
        self.roster_dirty = True
        self.send_rules()

    # ------------------------------------------------------------ modes and mutators

    def limit(self):
        return MODES[self.mode]["limit"]

    def describe(self):
        muts = [MUTATORS[m] for m in MUTATORS if m in self.muts]
        return f"{MODES[self.mode]['name']} on {world.MAP['name']}" + (f" with {', '.join(muts)}" if muts else "")

    def set_map(self, key):
        """Swap the map; the caller starts a new round, which respawns everyone on it."""
        world.load_map(key)
        if any(p.bot for p in self.players.values()):
            world.build_graph()
        self.pickups = [dict(pk, up_at=0.0) for pk in world.PICKUPS]
        self.power = None
        self.last_spot = None
        self.clear_shots()
        msg = json.dumps({"t": "map", "map": world.map_payload()}, separators=(",", ":"))
        for p in self.humans():
            self.send(p, msg)

    def rules(self):
        return {"t": "rules", "mode": self.mode, "muts": sorted(self.muts), "limit": self.limit(), "phys": PHYS,
                "knock": self.knock, "ends": _r(self.round_end) if self.infect_on else None,
                "alpha": _r(self.alpha_at) if self.mode == "infect" and not self.infect_on else None,
                "ladder": GUN_LADDER, "per": GUN_KILLS, "map": world.MAP["key"], "rotate": self.rotate}

    def send_rules(self):
        rules = self.rules()
        for p in self.humans():
            self.send(p, rules)

    def participants(self):
        return [p for p in self.players.values() if p.bot or p.playing]

    def juggernaut(self):
        return next((p for p in self.players.values() if p.role == "jugg"), None)

    def friendly(self, a, b):
        """Whether a can't hurt b: teammates in Infection, and everyone but the Juggernaut and those after them."""
        if a is None or b is None or a is b:
            return False
        if self.mode == "infect":
            return not self.infect_on or (a.role == "zombie") == (b.role == "zombie")
        if self.mode == "jugg":
            return "jugg" not in (a.role, b.role) and self.juggernaut() is not None
        return False

    def powers_on(self):
        return self.mode != "gun" and not self.muts & {"insta", "rockets"}

    def pickup_on(self, kind):
        if "insta" in self.muts:
            return False  # everyone dies to one rail anyway
        return kind != "ammo" or not (self.mode == "gun" or "rockets" in self.muts)

    def kit(self, p):
        """The weapons p may use, in slot order, and which of them never run out."""
        if self.mode == "gun":
            w = GUN_LADDER[min(p.score // GUN_KILLS, len(GUN_LADDER) - 1)]
            ws = [w] if w == KN else [w, KN]
            return ws, set(ws)
        if p.role == "zombie":
            return [KN], {KN}
        only = [w for m, w in (("insta", RG), ("rockets", RL)) if m in self.muts]
        if only:
            return only, set(only)
        pw = p.power()
        return ([MG, SG, RL, pw] if pw is not None else [MG, SG, RL]), set()

    def sync_kit(self, p):
        """Keep p holding what their kit allows, and tell their browser when the kit changes."""
        ws, inf = self.kit(p)
        for w in inf:
            p.ammo[w] = max(p.ammo[w], 1)
        if p.weapon not in ws or p.ammo[p.weapon] <= 0:
            p.weapon = next((w for w in ws if p.ammo[w] > 0), ws[0])
        sent = (tuple(ws), tuple(sorted(inf)), p.body.fast)
        if sent != p.kit_sent:
            p.kit_sent = sent
            p.events.append({"k": "kit", "a": ws, "inf": sorted(inf), "fast": p.body.fast})

    def set_role(self, p, role):
        if p.role == role:
            return
        p.role = role
        p.body.fast = ZOMBIE_FAST if role == "zombie" else 1.0
        self.roster_dirty = True
        if role == "jugg":
            p.hp = max(p.hp, JUGG_HP)
            p.armor = max(p.armor, JUGG_ARMOR)
            p.jugg_w = random.choice([RG, VX, IO, YT]) if self.powers_on() else None
            if p.jugg_w is not None:
                for w in POWER:
                    p.ammo[w] = 0
                p.ammo[p.jugg_w] = WEAPONS[p.jugg_w]["charge"]
                p.weapon = p.jugg_w
            p.recharge_at = self.now() + JUGG_RECHARGE
        elif role == "zombie":
            for w in POWER:
                p.ammo[w] = 0

    def step_mode(self, now):
        if now < self.inter_until:
            return
        if self.mode == "jugg":
            jugg = self.juggernaut()
            if jugg and jugg.alive and jugg.jugg_w is not None and now >= jugg.recharge_at:
                jugg.recharge_at = now + JUGG_RECHARGE
                w = jugg.jugg_w
                if jugg.power() in (None, w):
                    jugg.ammo[w] = min(WEAPONS[w]["charge"], jugg.ammo[w] + 1)
            return
        if self.mode != "infect":
            return
        if not self.alpha_at:
            self.alpha_at = now + INFECT_START
            self.send_rules()
        everyone = self.participants()
        zombies = [p for p in everyone if p.role == "zombie"]
        humans = [p for p in everyone if p.role != "zombie"]
        if not self.infect_on:
            if now < self.alpha_at:
                return
            if len(everyone) < 2:
                self.alpha_at = now + 1.0  # wait for someone to infect
                return
            alpha = random.choice(everyone)
            self.set_role(alpha, "zombie")
            self.infect_on = True
            if not self.round_end:
                self.round_end = now + INFECT_TIME
            self.broadcast_msg(f"{alpha.name} is the first zombie! Survive {round(self.round_end - now)} s")
            self.send_rules()
            return
        if not humans:
            best = max(zombies, key=lambda q: q.score, default=None)
            self.end_round(best, "The zombies win!")
        elif not zombies:
            # The zombies all left: pick another soon.
            self.infect_on = False
            self.alpha_at = now + 5.0
            self.send_rules()
        elif now >= self.round_end:
            best = max(humans, key=lambda q: q.score)
            self.end_round(best, f"Survivors win! {', '.join(q.name for q in humans[:4])} made it")
        elif len(humans) == 1 and self.last_human != humans[0].id:
            last = humans[0]
            self.last_human = last.id
            self.broadcast_msg(f"{last.name} is the last survivor")
            if last.alive:
                last.hp = max(last.hp, 200)
                last.armor = max(last.armor, 100)

    # ------------------------------------------------------------ pickups

    def step_pickups(self, now):
        for i, pk in enumerate(self.pickups):
            if pk["up_at"] > now or not self.pickup_on(pk["kind"]):
                continue
            for p in self.players.values():
                if not p.alive or p.role == "zombie" or abs(p.pos[1] - pk["y"]) > 1.5 or math.hypot(p.pos[0] - pk["x"], p.pos[2] - pk["z"]) > 1.1:
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
            if all(a >= w["max"] for a, w in zip(p.ammo, WEAPONS) if not w.get("power")):
                return False
            p.ammo = [a if w.get("power") else min(w["max"], a + w["add"]) for a, w in zip(p.ammo, WEAPONS)]
        return True

    def step_power(self, now):
        """One power weapon at a time, appearing at a random spot a while after the last was taken."""
        if not self.powers_on():
            return
        frenzy = "frenzy" in self.muts
        if self.power is None:
            if not self.power_at:
                self.power_at = now + (FRENZY["first"] if frenzy else POWER_FIRST)
            if now < self.power_at or now < self.inter_until:
                return
            spots = [i for i in range(len(world.POWER_SPOTS)) if i != self.last_spot]
            spot = random.choice(spots)
            w = random.choice(POWER)
            self.power = {"w": w, "spot": spot, "until": now + (FRENZY["wait"] if frenzy else POWER_WAIT)}
            self.last_spot = spot
            self.events.append({"k": "power", "w": w, "spot": spot})
            name = WEAPONS[w]["name"]
            self.broadcast_msg(f"{'An' if name[0] in 'AEIOU' else 'A'} {name} appeared {world.POWER_SPOTS[spot]['where']}")
            return
        s = world.POWER_SPOTS[self.power["spot"]]
        if now >= self.power["until"]:
            self.events.append({"k": "power", "w": None, "spot": self.power["spot"]})
            self.broadcast_msg(f"The {WEAPONS[self.power['w']]['name']} vanished")
            self.power = None
            self.power_at = now + random.uniform(*FRENZY["gap"] if frenzy else (5.0, 10.0))
            return
        for p in self.players.values():
            if p.alive and not p.role and abs(p.pos[1] - s["y"]) < 1.5 and math.hypot(p.pos[0] - s["x"], p.pos[2] - s["z"]) < 1.2:
                w = self.power["w"]
                for pw in POWER:
                    p.ammo[pw] = 0
                p.ammo[w] = WEAPONS[w]["charge"]
                p.weapon = w
                p.events.append({"k": "got", "kind": "power", "w": w})
                self.events.append({"k": "power", "w": None, "spot": self.power["spot"], "by": p.id})
                self.broadcast_msg(f"{p.name} grabbed the {WEAPONS[w]['name']}")
                self.power = None
                self.power_at = now + random.uniform(*FRENZY["gap"] if frenzy else POWER_GAP)
                return

    # ------------------------------------------------------------ bots

    def bot_think(self, p, now):
        b = p.brain
        was = b.rush
        b.rush = False
        if self.power and p.power() is None and not p.role:
            s = world.POWER_SPOTS[self.power["spot"]]
            if s["bots"] and math.dist(p.pos, (s["x"], s["y"], s["z"])) < 25:
                b.rush = True
                if not was or not b.path:
                    b.path = world.path(world.nearest_node(*p.pos), world.nearest_node(s["x"], s["y"], s["z"]))
                    b.best_dist, b.progress_at = 1e9, now
        eye = p.eye()
        fwd = _dir(p.yaw, 0)
        best, best_score = None, 1e9
        for q in self.players.values():
            if q is p or not q.alive or self.friendly(p, q):
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
            if not b.rush:
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
            if not b.rush and (not b.path or now > b.repath_at):
                self.bot_goal(p, now)

    def bot_weapon(self, p, d, q):
        ws = self.kit(p)[0]
        if len(ws) == 1:
            return ws[0]
        a = p.ammo
        if KN in ws:  # Gun Game: knife them if they're close enough
            return KN if d < 2.5 else ws[0]
        pw = p.power()
        if pw is not None and pw in ws:
            fits = {RG: d > 8, VX: 6 < d < 30, IO: d < 25, SW: 6 < d < 30 and random.random() < 0.3, YT: d < 18}
            if fits[pw]:
                return pw
        if d < 7 and a[SG] > 0:
            return SG
        if d < 22 and a[RL] > 0 and q.pos[1] < p.pos[1] + 2.5:
            return RL
        if a[MG] > 0:
            return MG
        return next((i for i in (RL, SG) if a[i] > 0), MG)

    def bot_goal(self, p, now):
        b = p.brain
        up = [pk for pk in self.pickups if pk["up_at"] <= now and self.pickup_on(pk["kind"]) and p.role != "zombie"]
        # Zombies know where the living are, and everyone knows where the Juggernaut is.
        prey = [q for q in self.players.values() if q.alive and q is not p and not self.friendly(p, q)
                and (p.role == "zombie" or q.role == "jugg")]
        goal = None
        wanted = []
        if p.hp < 70:
            wanted = [pk for pk in up if pk["kind"] in ("health", "mega")]
        elif p.armor < 50 and random.random() < 0.5:
            wanted = [pk for pk in up if pk["kind"] in ("armor", "mega")]
        elif p.ammo[SG] + p.ammo[RL] < 8:
            wanted = [pk for pk in up if pk["kind"] == "ammo"]
        if self.power and world.POWER_SPOTS[self.power["spot"]]["bots"] and p.power() is None and not p.role \
                and random.random() < 0.6:
            s = world.POWER_SPOTS[self.power["spot"]]
            wanted = [{"x": s["x"], "y": s["y"], "z": s["z"]}]
        hunting = bool(prey) and random.random() < 0.8
        if hunting:
            q = min(prey, key=lambda q: math.dist(p.pos, q.pos))
            goal = world.nearest_node(*q.pos)
        elif wanted:
            pk = min(wanted, key=lambda k: math.dist(p.pos, (k["x"], k["y"], k["z"])))
            goal = world.nearest_node(pk["x"], pk["y"], pk["z"])
        elif b.last_seen and now - b.last_seen_at < 6 and random.random() < 0.7:
            goal = world.nearest_node(*b.last_seen)
        else:
            goal = random.randrange(len(world.NODES))
        start = world.nearest_node(*p.pos)
        b.path = world.path(start, goal)
        b.repath_at = now + (3 if hunting else 8)  # the hunted move, so look again sooner
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
            if "speed" in spec:
                fly = math.dist(eye, aim) / spec["speed"]
                v = q.velocity()
                feet = 0.3 if p.weapon == RL else 1.0
                aim = [q.pos[0] + v[0] * fly * 0.8, q.pos[1] + feet, q.pos[2] + v[2] * fly * 0.8]
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
            limit = {MG: 0.12, SG: 0.18, RG: 0.05, SW: 0.06, KN: 0.4}.get(p.weapon, 0.1)
            if spec.get("melee") and math.dist(eye, aim) > spec["range"] + 0.4:
                limit = -1.0  # not in reach yet
            if now >= b.react_at and now >= p.next_fire and b.aim_err < limit and p.ammo[p.weapon] > 0 \
                    and now >= self.inter_until:
                self.bot_fire(p, now)

        if q is not None and q.alive and not (b.rush and b.path):
            # Fight: strafe, and close or open the distance toward what suits the weapon.
            d = math.hypot(q.pos[0] - p.pos[0], q.pos[2] - p.pos[2]) or 1.0
            fx, fz = (q.pos[0] - p.pos[0]) / d, (q.pos[2] - p.pos[2]) / d
            want = {MG: 12, SG: 4, RL: 9, RG: 25, VX: 14, IO: 12, SW: 15, YT: 8, KN: -9}[p.weapon]  # knives charge
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
                if q is None or not q.alive:
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
        if "spread" in spec:
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
            self.shots = []
            self.vortices = []
            self.inter_until = 0.0
            self.infect_on = False  # the next Infection round starts when someone's back
            self.alpha_at = self.round_end = 0.0
            for p in self.away.values():
                self.set_role(p, "")
            log.info("arena: match empty, stopped")

    def tick(self):
        now = self.now()
        if self.inter_until and now >= self.inter_until:
            if self.rotate:
                keys = list(world.MAPS)
                self.set_map(keys[(keys.index(world.MAP["key"]) + 1) % len(keys)])
                self.broadcast_msg(f"Next map: {world.MAP['name']}")
            self.new_round()
        for p in list(self.players.values()):
            if p.bot:
                if p.alive:
                    self.bot_tick(p, now, TICK)
                elif now - p.died_at >= BOT_RESPAWN and now >= self.inter_until:
                    self.respawn(p)
            elif not p.alive and p.playing and p.life > 0 and now - p.died_at >= RESPAWN_AUTO \
                    and now >= self.inter_until:
                self.respawn(p)
        self.step_shots(now)
        self.step_vortices(now)
        self.step_pickups(now)
        self.step_power(now)
        self.step_mode(now)
        for p in self.players.values():
            self.sync_kit(p)
        if now >= self.decay_at:
            self.decay_at = now + 1.0
            for p in self.players.values():
                if p.role == "jugg":
                    continue
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
                [p.id, p.name, p.color, p.score, p.deaths, int(p.bot), p.ping, int(p.playing), p.role]
                for p in self.players.values()
            ]}
            for p in self.humans():
                self.send(p, roster)
        common = {
            "t": "s", "ts": round(now, 4),
            "p": [[p.id, _r(p.pos[0]), _r(p.pos[1]), _r(p.pos[2]), _r(p.yaw), _r(p.pitch), p.weapon, int(p.alive)]
                  for p in self.players.values()],
            "pk": "".join("1" if pk["up_at"] <= now and self.pickup_on(pk["kind"]) else "0" for pk in self.pickups),
            "pw": [self.power["w"], self.power["spot"]] if self.power else None,
            "ev": self.events,
        }
        head = json.dumps(common, separators=(",", ":"))[:-1]
        self.events = []
        for p in self.humans():
            me = [p.hp, p.armor, *p.ammo, int(p.alive), p.life, p.warp]
            self.send(p, f'{head},"me":{json.dumps(me)},"pv":{json.dumps(p.events, separators=(",", ":"))}}}')
            p.events = []
        for p in self.players.values():
            if p.bot:
                p.events = []  # nobody reads a bot's


GAME = Game()
