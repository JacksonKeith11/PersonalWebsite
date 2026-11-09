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
STATUSES = ("burn", "frost", "bleed", "rot")
STATUS_LIVE = 4.0    # a burst marks the boss as burning/frozen/... for this long
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
        self.lights = 0
        self.empowered = None       # (damage mult, until) for the next hit
        self.vengeance = (1.0, 0.0)
        self.shield = 0


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
        self.meter = {k: 0.0 for k in STATUSES}   # status buildup on the boss
        self.procs = {k: 0 for k in STATUSES}
        self.marked = {k: -99.0 for k in STATUSES}  # when each status last burst
        self.rot_until = 0.0
        self.rot_dps = 0.0
        self.slow_until = 0.0
        self.tier = self.boss.get("tier", 1)
        self.rot_blocks_poise = False
        self.dmg_scale = 1.0     # the difficulty's boss damage
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
        b = fh.hero.build()
        slot = kind
        crit = self.state == "stagger" and kind in ("heavy", "special")
        mult *= b.dmg_mult(slot)
        poise *= b.poise_mult(slot)
        h = fh.hero
        if h.hp < h.mhp() * 0.5:
            for e in b.get("lowhp"): mult *= e["mult"]
        for e in b.get("vsstatus"):
            if now - self.marked[e["kind"]] < STATUS_LIVE: mult *= e["mult"]
        if fh.empowered and now < fh.empowered[1]:
            mult *= fh.empowered[0]; fh.empowered = None
        if now < fh.vengeance[1]: mult *= fh.vengeance[0]
        if any(math.hypot(o.x - fh.x, o.y - fh.y) < 90 for o in self.alive_heroes() if o is not fh):
            for e in b.get("near"): mult *= e["mult"]
        if crit:
            mult *= 3.0
            for e in b.get("crit"): mult *= e["mult"]
        dmg = round(w["base"] * mult * C.HERO.get("dmg_scale", 1.0))
        extra = 0
        if kind == "light":
            fh.lights += 1
            for e in b.get("chain"):
                if fh.lights % e["every"] == 0:
                    extra += round(e["dmg"])
                    for s in b.get("chainstatus"): self.build_status(s["kind"], s["amt"] * b.buildup, now, fh)
                    for s in b.get("chainheal"): self.heal(fh, s["amt"])
                    self.room.broadcast({"t": "fx", "k": "chain", "x": round(self.x), "y": round(self.y)})
        if kind == "special":
            for e in b.get("specialheal"): self.heal(fh, e["amt"])
        self.hp = max(0, self.hp - dmg - extra)
        fh.threat += dmg
        for e in b.get("steal"):
            if e["slot"] in (slot, "all"): self.heal(fh, dmg * e["frac"])
        if crit:
            self.state, self.until = "idle", now + 0.6  # the critical ends the stagger
            self.poise = self.mpoise
            for e in b.get("critstatus"):
                self.build_status("burn", e["amt"], now, fh); self.build_status("rot", e["amt"], now, fh)
        elif self.state != "stagger":
            self.damage_poise(poise, now)
        self.room.broadcast({"t": "fx", "k": "crit" if crit else "hit", "h": hid, "dmg": dmg + extra, "x": round(self.x), "y": round(self.y)})
        for s in b.status[slot]: self.build_status(s[0], s[1] * b.buildup, now, fh)
        if self.hp <= 0:
            self.die(now)
        elif self.phase == 1 and self.hp <= self.mhp * self.boss["phase2"]:
            self.phase = 2
            self.start_move("phase2", self.boss["phase2_move"], now, cancel=True)

    def heal(self, fh, amt):
        h = fh.hero
        if fh.down or fh.dead or amt <= 0: return
        h.hp = min(h.mhp(), h.hp + max(1, round(amt)))

    def build_status(self, kind, amt, now, fh):
        """Add buildup; a full meter bursts (and the next takes longer to fill)."""
        if self.state == "dead" or amt <= 0: return
        self.meter[kind] += amt
        need = 100 * 1.4 ** self.procs[kind]
        if self.meter[kind] < need:
            return
        self.meter[kind] = 0
        self.procs[kind] += 1
        self.marked[kind] = now
        b = fh.hero.build()
        mult = 1.0
        for e in b.get("statusmult"):
            if e["kind"] == kind: mult *= e["mult"]
        for e in b.get("combo"):
            if e["a"] == kind and now - self.marked[e["b"]] < STATUS_LIVE: mult *= e["mult"]
        scale = 1 + 0.25 * (self.tier - 1)
        dmg = 0
        if kind == "burn":
            dmg = round(70 * scale * mult)
        elif kind == "bleed":
            dmg = round(95 * scale * mult)
        elif kind == "frost":
            self.slow_until = now + STATUS_LIVE
            if any(True for _ in b.get("frostbreak")) and self.hp < self.mhp * 0.5:
                self.damage_poise(self.poise + 1, now)
            else:
                self.damage_poise(50 * mult * (self.mpoise / self.boss["poise"]) ** 0.5, now)
            dmg = round(20 * scale)
        elif kind == "rot":
            self.rot_until = now + 5.0
            self.rot_dps = 26 * scale * mult
            self.rot_blocks_poise = any(True for _ in b.get("vsstatus_poise"))
        for e in b.get("procbuild"):
            if e["on"] == kind: self.build_status(e["kind"], e["amt"], now, fh)
        if dmg:
            self.hp = max(1 if self.hp > 0 else 0, self.hp - dmg)
        self.room.broadcast({"t": "fx", "k": "status", "kind": kind, "dmg": dmg, "x": round(self.x), "y": round(self.y)})

    def dodged(self, hid, msg, now):
        """A hero rolled; if they rolled past the boss, their dodge upgrades build statuses."""
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead: return
        try:
            x0, y0, x1, y1 = (float(msg.get(k)) for k in ("x0", "y0", "x1", "y1"))
        except (TypeError, ValueError):
            return
        dx, dy = x1 - x0, y1 - y0
        L = max(1e-6, dx * dx + dy * dy)
        u = max(0.0, min(1.0, ((self.x - x0) * dx + (self.y - y0) * dy) / L))
        if math.hypot(x0 + dx * u - self.x, y0 + dy * u - self.y) > 50 + self.boss["radius"]: return
        b = fh.hero.build()
        for e in b.get("dodge"): self.build_status(e["kind"], e["amt"] * b.buildup, now, fh)

    def perfect(self, hid, now):
        """A hero's roll carried them through a hit (their browser says)."""
        fh = self.heroes.get(hid)
        if not fh: return
        for e in fh.hero.build().get("perfect"):
            fh.empowered = (e["dmg"], now + 2.0)
            if e.get("heal"): self.heal(fh, e["heal"])

    def damage_poise(self, amount, now):
        if self.rot_until > now and self.rot_blocks_poise: amount *= 1.25
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
        b = fh.hero.build()
        if msg.get("parry") or msg.get("block"):
            for e in b.get("guard_status"): self.build_status(e["kind"], e["amt"] * b.buildup, now, fh)
        if msg.get("parry"):
            self.damage_poise(60 * (self.mpoise / self.boss["poise"]) ** 0.5, now)
            for e in b.get("parry"): fh.empowered = (e["mult"], now + 3.0)
            for e in b.get("parryheal"): self.heal(fh, e["amt"])
            for e in b.get("parrybolt"):
                self.hp = max(1, self.hp - round(e["dmg"]))
                self.room.broadcast({"t": "fx", "k": "chain", "x": round(self.x), "y": round(self.y)})
            for o in self.heroes.values():
                for e in o.hero.build().get("allyparry"): o.empowered = (e["mult"], now + 3.0)
            self.room.broadcast({"t": "fx", "k": "parry", "h": hid, "x": round(fh.x), "y": round(fh.y)})
            return
        if msg.get("block"):
            self.room.broadcast({"t": "fx", "k": "block", "h": hid, "x": round(fh.x), "y": round(fh.y)})
            return
        dmg = hit["dmg"] * self.dmg_scale
        if fh.shield:
            soak = min(fh.shield, dmg); fh.shield -= soak; dmg -= soak
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
        for o in self.heroes.values():
            if o is not fh:
                for e in o.hero.build().get("ondown"): o.vengeance = (e["mult"], now + e["dur"])
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
        pacts = fh.hero.build().get("revive")
        if not any(e.get("free") for e in pacts):
            fh.hero.hp = max(1, fh.hero.hp - round(fh.hero.mhp() * d["cost"]))
        other.down = False
        other.hero.hp = max(1, round(other.hero.mhp() * d["rise"]))
        other.shield = round(sum(e.get("shield", 0) for e in pacts))
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
                amt = h.mhp() * h.build().stats["heal"]
                h.hp = min(h.mhp(), h.hp + round(amt))
                self.room.broadcast({"t": "fx", "k": "heal", "h": h.id, "x": round(f.x), "y": round(f.y)})
                for e in h.build().get("flaskall"):
                    for o in self.alive_heroes():
                        if o is not f and math.hypot(o.x - f.x, o.y - f.y) < 70:
                            self.heal(o, amt * e["frac"])
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
        if self.rot_until > now and self.state != "dead":
            self.rot_acc = getattr(self, "rot_acc", 0.0) + self.rot_dps * TICK
            if self.rot_acc >= 10:
                n = int(self.rot_acc); self.rot_acc -= n
                self.hp = max(1, self.hp - n)
                self.room.broadcast({"t": "fx", "k": "dot", "kind": "rot", "dmg": n, "x": round(self.x), "y": round(self.y)})
        if self.state != "stagger" and now - self.poise_hit > POISE_REGEN[0] and not (self.rot_until > now and self.rot_blocks_poise):
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
            sp = self.boss["speed"] * (1.15 if self.phase == 2 else 1.0) * (0.55 if now < self.slow_until else 1.0)
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
