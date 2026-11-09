"""One boss fight: the boss's AI and moves, health, poise, downed heroes. Runs at 30 Hz on the server.

The netcode (docs/kingfall.md, "Netcode"): each browser moves its own heroes and reports where they
are; the server picks the boss's moves and announces each one `LEAD` seconds before it starts, with
its origin, aim and step lengths, so every browser draws it, and checks it against its own heroes,
at the same server time. A browser reports its heroes' hits on the boss and the hits they took;
the server applies the damage.
"""

import math
import random

from . import content as C
from .content.moves import aim_at, offset, resolve

LEAD = 0.14          # a move is announced this long before it starts
TICK = 1 / 30
STAGGER = 2.6        # seconds a broken-poise boss reels
POISE_REGEN = (3.0, 25.0)  # after this long without poise damage, it refills at this rate
INTRO = 2.2
ARENAS = {"chapel": {"w": 800, "h": 480, "pad": (48, 70, 48, 40)}}  # left, top, right, bottom walls


class Move:
    def __init__(self, seq, mid, data, start, origin, aim, dists):
        self.seq, self.id, self.data, self.start = seq, mid, data, start
        self.origin = origin
        self.aims = [(0.0, aim)]
        self.dists = dists
        self.locked = {0.0}

    def pos(self, now):
        dx, dy = offset(self.data, self.aims, self.dists, now - self.start)
        return self.origin[0] + dx, self.origin[1] + dy

    def end(self):
        return self.start + self.data["dur"]

    def wire(self):
        return {"t": "mv", "seq": self.seq, "id": self.id, "at": round(self.start, 3), "x": round(self.origin[0], 1),
                "y": round(self.origin[1], 1), "a": round(self.aims[0][1], 4), "d": [round(d, 1) for d in self.dists]}


class FHero:
    """A hero's state during a fight (the run's Hero keeps what lasts between fights)."""

    def __init__(self, hero, x, y):
        self.hero = hero
        self.x, self.y = x, y
        self.face = 0.0
        self.anim, self.at = "idle", 0.0
        self.down = False
        self.dead = False
        self.bleed = 0.0       # when a downed hero dies
        self.heal_at = None    # a drink finishes then
        self.hits_taken = set()
        self.swings = set()
        self.threat = 0.0      # recent damage dealt, for the boss's choice of target
        self.last_targeted = 0.0
        self.second_wind = None


class Fight:
    def __init__(self, room, boss_id, heroes, now):
        self.room = room
        self.boss = C.BOSSES[boss_id]
        self.arena = ARENAS[self.boss["arena"]]
        n = max(1, min(4, len(heroes)))
        self.mhp = round(self.boss["hp"] * C.SCALE_HP[n - 1])
        self.hp = self.mhp
        self.mpoise = round(self.boss["poise"] * C.SCALE_POISE[n - 1])
        self.poise = self.mpoise
        self.poise_hit = 0.0
        self.phase = 1
        self.x, self.y = self.arena["w"] * 0.5, self.arena["h"] * 0.36
        self.face = math.pi / 2
        self.state, self.until = "intro", now + INTRO
        self.move = None
        self.recent = []          # recent moves, for late hit reports
        self.seq = 0
        self.cool = {}
        self.last_move = None
        self.target = None
        self.vx = self.vy = 0.0
        self.started = now
        self.over = None          # "won" / "lost"
        self.solo = len(heroes) == 1
        self.heroes = {}
        for i, h in enumerate(heroes):
            x = self.arena["w"] * (0.5 + (i - (len(heroes) - 1) / 2) * 0.08)
            fh = FHero(h, x, self.arena["h"] * 0.78)
            fh.face = -math.pi / 2
            self.heroes[h.id] = fh

    # ------------------------------------------------------------------ messages from browsers
    def report(self, hid, msg):
        fh = self.heroes.get(hid)
        if not fh or fh.dead: return
        try:
            x, y = float(msg.get("x")), float(msg.get("y"))
        except (TypeError, ValueError):
            return
        if not (0 <= x <= self.arena["w"] and 0 <= y <= self.arena["h"]): return
        if not fh.down:
            fh.x, fh.y = x, y
        fh.face = float(msg.get("f") or 0)
        fh.anim = str(msg.get("an") or "idle")[:12]
        fh.at = float(msg.get("at") or 0)

    def hit_boss(self, hid, msg, now):
        """A hero's attack landed on the boss (the browser says so)."""
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead or self.state in ("intro", "dead") or self.over: return
        sw = msg.get("sw")
        if not isinstance(sw, int) or sw in fh.swings: return
        fh.swings.add(sw)
        if len(fh.swings) > 200: fh.swings = set(sorted(fh.swings)[-100:])
        w = C.WEAPONS.get(fh.hero.weapon)
        kind = msg.get("atk")
        if kind == "light":
            i = msg.get("i") if isinstance(msg.get("i"), int) else 0
            atk = w["light"][max(0, min(len(w["light"]) - 1, i))]
            mult, poise = atk["mult"], atk["poise"]
        elif kind == "heavy":
            c = max(0.0, min(1.0, float(msg.get("c") or 0)))
            atk = w["heavy"]
            mult = atk["mult"][0] + (atk["mult"][1] - atk["mult"][0]) * c
            poise = atk["poise"][0] + (atk["poise"][1] - atk["poise"][0]) * c
        elif kind == "special":
            atk = w["special"]
            mult, poise = atk["mult"], atk["poise"]
        else:
            return
        if self.move and self.move.data.get("invuln") and now >= self.move.start:
            self.room.broadcast({"t": "fx", "k": "immune", "x": round(self.x), "y": round(self.y)})
            return
        g = self.move and self.move.data.get("guard")
        if g and self.move.start + g[0] <= now <= self.move.start + g[1]:
            ang = math.atan2(fh.y - self.y, fh.x - self.x)
            if abs(_wrap(ang - aim_at(self.move.aims, now - self.move.start))) < math.radians(75):
                self.room.broadcast({"t": "fx", "k": "guarded", "x": round(self.x), "y": round(self.y), "h": hid})
                return
        crit = self.state == "stagger" and kind in ("heavy", "special")
        dmg = w["base"] * mult * fh.hero.might() * (3.0 if crit else 1.0)
        dmg = round(dmg)
        self.hp = max(0, self.hp - dmg)
        fh.threat += dmg
        if crit:
            self.state, self.until = "idle", now + 0.6  # the critical ends the stagger
            self.poise = self.mpoise
        elif self.state != "stagger":
            self.damage_poise(poise, now)
        self.room.broadcast({"t": "fx", "k": "crit" if crit else "hit", "h": hid, "dmg": dmg, "x": round(self.x), "y": round(self.y)})
        if self.hp <= 0:
            self.die(now)
        elif self.phase == 1 and self.hp <= self.mhp * self.boss["phase2"]:
            self.phase = 2
            self.start_move("phase2", self.boss["phase2_move"], now, cancel=True)

    def damage_poise(self, amount, now):
        self.poise -= amount
        self.poise_hit = now
        if self.poise <= 0 and self.state != "stagger" and not (self.move and self.move.data.get("invuln")):
            self.cancel(now)
            self.state, self.until = "stagger", now + STAGGER
            self.poise = self.mpoise
            self.room.broadcast({"t": "fx", "k": "stagger", "x": round(self.x), "y": round(self.y)})

    def hurt(self, hid, msg, now):
        """A hero took a hit (their browser decided). Applies the damage."""
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead or self.over: return
        key = str(msg.get("id"))[:24]
        if key in fh.hits_taken: return
        hit, start = self.find_hit(key)
        if hit is None: return
        t = now - start
        if not (hit["t0"] - 0.6 <= t <= hit["t1"] + 0.8): return
        fh.hits_taken.add(key)
        if len(fh.hits_taken) > 300: fh.hits_taken = set(list(fh.hits_taken)[-150:])
        if msg.get("parry"):
            self.damage_poise(60 * (self.mpoise / self.boss["poise"]) ** 0.5, now)
            self.room.broadcast({"t": "fx", "k": "parry", "h": hid, "x": round(fh.x), "y": round(fh.y)})
            return
        dmg = hit["dmg"] * fh.hero.guard_mult()
        if msg.get("block"):
            self.room.broadcast({"t": "fx", "k": "block", "h": hid, "x": round(fh.x), "y": round(fh.y)})
            return
        fh.heal_at = None  # a hit spills the drink
        h = fh.hero
        h.hp = max(0, h.hp - round(dmg))
        self.room.broadcast({"t": "fx", "k": "hurt", "h": hid, "dmg": round(dmg), "x": round(fh.x), "y": round(fh.y)})
        if h.hp <= 0:
            self.knock_down(fh, now)

    def find_hit(self, key):
        """'seq:i' or 'seq:i:n' (n for repeating hits) -> (hit, the move's start time)."""
        parts = key.split(":")
        try:
            seq, i = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return None, 0
        for m in ([self.move] if self.move else []) + self.recent:
            if m.seq == seq and 0 <= i < len(m.data["hits"]):
                return m.data["hits"][i], m.start
        return None, 0

    def knock_down(self, fh, now):
        fh.down = True
        fh.heal_at = None
        if self.solo and fh.hero.second_wind:
            fh.hero.second_wind = False
            fh.second_wind = now + 2.0
            self.room.broadcast({"t": "fx", "k": "secondwind", "h": fh.hero.id})
        else:
            fh.bleed = now + C.HERO["down"]["bleed"]
        self.room.broadcast({"t": "fx", "k": "down", "h": fh.hero.id, "x": round(fh.x), "y": round(fh.y)})

    def drink(self, hid, now):
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead or fh.hero.flasks <= 0 or fh.heal_at: return
        fh.hero.flasks -= 1
        fh.heal_at = now + C.HERO["flask"]["at"]

    def revive(self, hid, who, now):
        fh, other = self.heroes.get(hid), self.heroes.get(who)
        if not fh or not other or fh is other or fh.down or fh.dead or not other.down or other.dead: return
        if math.hypot(fh.x - other.x, fh.y - other.y) > 40: return
        d = C.HERO["down"]
        fh.hero.hp = max(1, fh.hero.hp - round(fh.hero.mhp() * d["cost"]))
        other.down = False
        other.hero.hp = max(1, round(other.hero.mhp() * d["rise"]))
        self.room.broadcast({"t": "fx", "k": "revive", "h": who, "by": hid, "x": round(other.x), "y": round(other.y)})

    # ------------------------------------------------------------------ the boss
    def cancel(self, now):
        if self.move:
            self.room.broadcast({"t": "cancel", "seq": self.move.seq, "at": round(now, 3)})
            self.x, self.y = self.clamp(*self.move.pos(min(now, self.move.end())))
            self.recent = ([self.move] + self.recent)[:4]
            self.move = None

    def die(self, now):
        self.cancel(now)
        self.state = "dead"
        self.over = "won"
        self.until = now + 3.5
        self.room.broadcast({"t": "fx", "k": "bossdown", "x": round(self.x), "y": round(self.y)})

    def alive_heroes(self):
        return [f for f in self.heroes.values() if not f.down and not f.dead]

    def pick_target(self, now):
        best, score = None, -1e9
        for f in self.alive_heroes():
            d = math.hypot(f.x - self.x, f.y - self.y)
            s = -d / 90 + f.threat * 0.01 + min(6.0, now - f.last_targeted) * 0.35 + random.random() * 0.6
            if s > score: best, score = f, s
        return best

    def start_move(self, mid, data, now, cancel=False):
        if cancel: self.cancel(now)
        t = self.target
        aim = math.atan2(t.y - self.y, t.x - self.x) if t else self.face
        dist = math.hypot(t.x - self.x, t.y - self.y) if t else 80
        dists = resolve(data, 0.0, dist, [0.0] * len(data["motion"]))
        self.seq += 1
        self.move = Move(self.seq, mid, data, now + LEAD, (self.x, self.y), aim, dists)
        self.fit(self.move)
        self.face = aim
        self.state = "move"
        self.vx = self.vy = 0
        self.cool[mid] = now + LEAD + data["dur"] + data.get("cd", 0)
        self.last_move = mid
        self.room.broadcast(self.move.wire())

    def choose(self, now):
        t = self.target
        if not t: return None
        d = math.hypot(t.x - self.x, t.y - self.y)
        opts = []
        for mid, m in self.boss["moves"].items():
            if self.phase not in m["phase"] or self.cool.get(mid, 0) > now: continue
            lo, hi = m["range"]
            if lo <= d <= hi:
                opts.append((mid, m["weight"] * (0.35 if mid == self.last_move else 1.0)))
        if not opts: return None
        r = random.random() * sum(w for _, w in opts)
        for mid, w in opts:
            r -= w
            if r <= 0: return mid
        return opts[-1][0]

    def fit(self, move, after=0.0):
        """Shorten a move's steps so it never carries the boss through a wall (browsers draw the
        motion as sent, so the server can't clamp it afterwards)."""
        for _ in range(12):
            x, y = move.pos(move.end())
            if (x, y) == self.clamp(x, y): return
            move.dists = [d * 0.8 if seg[0] >= after else d for d, seg in zip(move.dists, move.data["motion"])]

    def clamp(self, x, y):
        l, t, r, b = self.arena["pad"]
        return max(l, min(self.arena["w"] - r, x)), max(t, min(self.arena["h"] - b, y))

    def tick(self, now):
        if self.over == "lost": return
        # heroes: drinks, bleeding out, second wind
        for f in self.heroes.values():
            if f.heal_at and now >= f.heal_at:
                f.heal_at = None
                h = f.hero
                h.hp = min(h.mhp(), h.hp + round(h.mhp() * C.HERO["flask"]["heal"]))
                self.room.broadcast({"t": "fx", "k": "heal", "h": h.id, "x": round(f.x), "y": round(f.y)})
            if f.down and f.second_wind and now >= f.second_wind:
                f.second_wind, f.down = None, False
                f.hero.hp = round(f.hero.mhp() * 0.5)
                self.room.broadcast({"t": "fx", "k": "revive", "h": f.hero.id, "x": round(f.x), "y": round(f.y)})
            elif f.down and not f.second_wind and f.bleed and now >= f.bleed:
                f.dead = True
                self.room.broadcast({"t": "fx", "k": "dead", "h": f.hero.id})
            f.threat *= 0.995
        if not self.alive_heroes() and not any(f.second_wind for f in self.heroes.values()) and self.over != "won":
            self.over = "lost"
            self.cancel(now)
            self.room.broadcast({"t": "fx", "k": "wipe"})
            return
        if self.state == "dead": return
        if self.state != "stagger" and now - self.poise_hit > POISE_REGEN[0]:
            self.poise = min(self.mpoise, self.poise + POISE_REGEN[1] * TICK)
        if self.state in ("intro", "stagger"):
            if now >= self.until:
                self.state, self.until = "idle", now + 0.3
            return
        if self.move:
            m = self.move
            t = now - m.start
            for lt in m.data.get("locks", []):
                if lt not in m.locked and t >= lt:
                    m.locked.add(lt)
                    tg = self.target if self.target in self.alive_heroes() else self.pick_target(now)
                    if tg:
                        bx, by = m.pos(now)
                        a = math.atan2(tg.y - by, tg.x - bx)
                        m.aims.append((lt, a))
                        m.dists = resolve(m.data, lt, math.hypot(tg.x - bx, tg.y - by), m.dists)
                        self.fit(m, lt)
                        self.face = a
                        self.room.broadcast({"t": "aim", "seq": m.seq, "lt": lt, "a": round(a, 4), "d": [round(d, 1) for d in m.dists]})
            self.x, self.y = self.clamp(*m.pos(now))
            if now >= m.end():
                self.recent = ([m] + self.recent)[:4]
                self.move = None
                self.state, self.until = "idle", now + (random.uniform(0.6, 1.2) if self.solo else random.uniform(0.25, 0.7))
            return
        # idle: pick a target, then a move in range, else walk closer
        if not self.target or self.target not in self.alive_heroes() or random.random() < 0.01:
            self.target = self.pick_target(now)
        t = self.target
        if not t:
            self.vx = self.vy = 0
            return
        if now >= self.until:
            mid = self.choose(now)
            if mid:
                t.last_targeted = now
                self.start_move(mid, self.boss["moves"][mid], now)
                return
        dx, dy = t.x - self.x, t.y - self.y
        d = math.hypot(dx, dy)
        self.face = math.atan2(dy, dx)
        if d > 46:
            sp = self.boss["speed"] * (1.15 if self.phase == 2 else 1.0)
            self.vx, self.vy = dx / d * sp, dy / d * sp
            self.x, self.y = self.clamp(self.x + self.vx * TICK, self.y + self.vy * TICK)
        else:
            self.vx = self.vy = 0

    def snapshot(self, now):
        return {"t": "s", "st": round(now, 3),
                "b": [round(self.x, 1), round(self.y, 1), round(self.vx, 1), round(self.vy, 1), round(self.face, 3), self.hp, self.mhp,
                      round(self.poise), self.mpoise, self.phase, self.state],
                "h": [[f.hero.id, round(f.x, 1), round(f.y, 1), round(f.face, 2), f.anim, round(f.at, 2), f.hero.hp, f.hero.mhp(),
                       f.hero.flasks, 1 if f.down else (2 if f.dead else 0),
                       round(max(0, f.bleed - now), 1) if f.down and f.bleed else 0, 1 if f.heal_at else 0]
                      for f in self.heroes.values()]}

    def start_wire(self):
        return {"t": "fight", "boss": self.boss["id"], "arena": self.boss["arena"], "size": [self.arena["w"], self.arena["h"]],
                "pad": self.arena["pad"], "mhp": self.mhp, "mpoise": self.mpoise, "intro": INTRO, "started": round(self.started, 3),
                "heroes": {f.hero.id: [round(f.x), round(f.y)] for f in self.heroes.values()}}


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi
