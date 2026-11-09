"""One boss fight: the bosses' AI and moves, health, poise, statuses, adds, downed heroes. Runs at 30 Hz.

The netcode (docs/kingfall.md, "Netcode"): each browser moves its own heroes and reports where they
are; the server picks the boss's moves and announces each one `LEAD` seconds before it starts, with
its origin, aim and step lengths, so every browser draws it, and checks it against its own heroes,
at the same server time. A browser reports its heroes' hits on the boss and the hits they took;
the server applies the damage.

A boss is one or more bodies (the Twin Headsmen are two), each with its own moves, health, poise and
statuses. Bosses can also call adds (small enemies the server moves), leave lingering ground hazards
('zone' hits, which hurt every `tick` seconds), leap or fly ('air' windows: no one can hit them),
burrow ('under') and have weak points ('cores') that must be broken before the body takes full damage.
"""

import math
import random

from . import content as C
from .content.moves import aim_at, n_dists, offset, resolve
from .content.skills import BASE as SKILL_BASE, SKILLS

LEAD = 0.14          # a move is announced this long before it starts
TICK = 1 / 30
STAGGER = 5.0        # seconds a broken-poise boss reels
POISE_K = 2.6        # every boss's written poise, multiplied: staggers are rare and worth it
POISE_GROW = 0.25    # each stagger makes the next need this much more
TOPPLE = 7.0         # seconds a boss reels when its last core breaks
POISE_REGEN = (3.0, 0.12)  # after this long without poise damage, it refills by this share a second
INTRO = 2.2
STATUSES = ("burn", "frost", "bleed", "rot")
STATUS_LIVE = 4.0    # a burst marks the boss as burning/frozen/... for this long
ARENA = {"w": 800, "h": 480, "pad": (48, 70, 48, 40)}  # left, top, right, bottom walls
SKILL_SLACK = 0.3   # a browser's cooldown may run this far ahead of the server's
SKILL_LIVE = 4.0    # a skill's hits count for this long after it's used (a lance in flight, a pillar falling)
RECENT = 12          # finished moves kept for late hit reports and lingering hazards


def bodies_of(boss):
    """A boss's bodies: its 'bodies' list, or the boss itself as its only body."""
    return boss.get("bodies") or [boss]


class Move:
    def __init__(self, seq, e, mid, data, start, origin, aim, dists, target=None):
        self.seq, self.e, self.id, self.data, self.start = seq, e, mid, data, start
        self.target = target   # the hero id it was aimed at (browsers mark them)
        self.origin = origin
        self.aims = [(0.0, aim)]
        self.dists = dists
        self.locked = {0.0}
        self.spawned = set()
        self.last = start + max([data["dur"]] + [h["t1"] for h in data["hits"]])  # when its last hazard ends

    def pos(self, now):
        dx, dy = offset(self.data, self.aims, self.dists, now - self.start)
        return self.origin[0] + dx, self.origin[1] + dy

    def end(self):
        return self.start + self.data["dur"]

    def window(self, key, now):
        w = self.data.get(key)
        return bool(w) and self.start + w[0] <= now <= self.start + w[1]

    def wire(self, extra=None):
        m = {"t": "mv", "seq": self.seq, "e": self.e, "id": self.id, "at": round(self.start, 3), "x": round(self.origin[0], 1),
             "y": round(self.origin[1], 1), "a": round(self.aims[0][1], 4), "d": [round(d, 1) for d in self.dists]}
        if self.target is not None: m["tg"] = self.target
        if extra: m.update(extra)
        return m


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
        self.far = 0.0         # seconds spent keeping away from the boss (archers, casters): it comes for them
        self.second_wind = None
        self.lights = 0
        self.empowered = None       # (damage mult, until) for the next hit
        self.vengeance = (1.0, 0.0)
        self.shield = 0
        self.skill_used = {}        # skill id -> when it was last used (cooldowns start afresh each fight)


class Body:
    """One of a boss's bodies."""

    def __init__(self, fight, e, d, n, now, x, y):
        self.f, self.e, self.d = fight, e, d
        self.mhp = round(d["hp"] * C.SCALE_HP[n - 1])
        self.hp = self.mhp
        self.base_poise = d["poise"]
        self.mpoise = round(d["poise"] * POISE_K * C.SCALE_POISE[n - 1])
        self.poise0 = self.mpoise
        self.staggers = 0
        self.crit_by = set()   # heroes who have landed their critical on this stagger
        self.poise = self.mpoise
        self.poise_hit = 0.0
        self.phase = 1
        self.x, self.y = x, y
        self.face = math.pi / 2
        self.state, self.until = "intro", now + INTRO
        self.move = None
        self.cool = {}
        self.last_move = None
        self.target = None
        self.vx = self.vy = 0.0
        self.meter = {k: 0.0 for k in STATUSES}
        self.procs = {k: 0 for k in STATUSES}
        self.marked = {k: -99.0 for k in STATUSES}
        self.rot_until = self.rot_dps = self.rot_acc = 0.0
        self.rot_blocks_poise = False
        self.slow_until = 0.0
        self.cores = [c["hp"] * C.SCALE_HP[n - 1] for c in d.get("cores", [])]
        self.enraged = False
        self.art = d["art"]

    @property
    def alive(self):
        return self.state != "dead"

    def untouchable(self, now):
        m = self.move
        return bool(m) and now >= m.start and (m.data.get("invuln") or m.window("air", now) or m.window("under", now))

    def core_pos(self, i):
        c = self.d["cores"][i]
        side = -1 if math.cos(self.face) < -0.05 else 1
        return self.x + c["dx"] * side, self.y + c["dy"]

    def armored(self):
        return any(hp > 0 for hp in self.cores) and self.state != "stagger"


class Fight:
    def __init__(self, room, boss_id, heroes, now, diff=None):
        self.room = room
        self.boss = C.BOSSES[boss_id]
        self.arena = ARENA
        self.diff = diff or {"hp": 1.0, "dmg": 1.0, "speed": 1.0, "wind": True}
        n = max(1, min(4, len(heroes)))
        defs = bodies_of(self.boss)
        self.bodies = []
        for e, d in enumerate(defs):
            x = self.arena["w"] * (0.5 + (e - (len(defs) - 1) / 2) * 0.22)
            b = Body(self, e, d, n, now, x, self.arena["h"] * 0.36)
            b.mhp = b.hp = round(b.mhp * self.diff["hp"])
            self.bodies.append(b)
        self.recent = []
        self.seq = 0
        self.started = now
        self.over = None          # "won" / "lost"
        self.until = 0.0
        self.solo = len(heroes) == 1
        self.tier = self.boss.get("tier", 1)
        self.dmg_scale = self.diff["dmg"]
        self.calm = False         # debug rooms: the boss only walks about, never attacks (browser tests)
        self.adds = {}
        self.add_seq = 0
        self.heroes = {}
        for i, h in enumerate(heroes):
            x = self.arena["w"] * (0.5 + (i - (len(heroes) - 1) / 2) * 0.08)
            fh = FHero(h, x, self.arena["h"] * 0.78)
            fh.face = -math.pi / 2
            self.heroes[h.id] = fh

    # compatibility for single-body code (tools, the sim): the first body
    @property
    def x(self): return self.bodies[0].x

    @property
    def y(self): return self.bodies[0].y

    @property
    def hp(self): return sum(b.hp for b in self.bodies)

    @property
    def mhp(self): return sum(b.mhp for b in self.bodies)

    @property
    def phase(self): return max(b.phase for b in self.bodies)

    def moves(self):
        """Every move still live or lingering."""
        return [b.move for b in self.bodies if b.move] + self.recent

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

    def attack(self, fh, msg, now):
        """(mult, poise, slot) of a hero's attack from its message, or None."""
        w = C.WEAPONS.get(fh.hero.weapon)
        kind = msg.get("atk")
        if kind == "light":
            i = msg.get("i") if isinstance(msg.get("i"), int) else 0
            atk = w["light"][max(0, min(len(w["light"]) - 1, i))]
            return atk["mult"], atk["poise"], kind
        if kind == "heavy":
            c = max(0.0, min(1.0, float(msg.get("c") or 0)))
            atk = w["heavy"]
            return atk["mult"][0] + (atk["mult"][1] - atk["mult"][0]) * c, atk["poise"][0] + (atk["poise"][1] - atk["poise"][0]) * c, kind
        if kind == "special":
            atk = w["special"]
            return atk["mult"], atk["poise"], kind
        if kind == "skill":  # damage from the skill alone, whatever the weapon (hit_boss multiplies by the weapon's base)
            s = SKILLS.get(msg.get("sk"))
            if not s or "mult" not in s or s["id"] not in fh.hero.skills: return None
            if now - fh.skill_used.get(s["id"], -99.0) > SKILL_LIVE: return None
            return s["mult"] * SKILL_BASE / w["base"], s["poise"], "special"
        if kind == "guard" and "mult" in w["guard"]:  # the halberd's counter, the bow's roll-shot
            return w["guard"]["mult"], w["guard"].get("poise", 8), kind
        return None

    def new_swing(self, fh, msg):
        sw = msg.get("sw")
        key = (sw, msg.get("a"), msg.get("e"), msg.get("core"))
        if not isinstance(sw, int) or key in fh.swings: return False
        fh.swings.add(key)
        if len(fh.swings) > 300: fh.swings = set(list(fh.swings)[-150:])
        return True

    def hit_boss(self, hid, msg, now):
        """A hero's attack landed on a boss body, or one of its cores (the browser says so)."""
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead or self.over: return
        e = msg.get("e") if isinstance(msg.get("e"), int) else 0
        if not 0 <= e < len(self.bodies): return
        b = self.bodies[e]
        if b.state in ("intro", "dead") or not self.new_swing(fh, msg): return
        a = self.attack(fh, msg, now)
        if not a: return
        mult, poise, slot = a
        if b.untouchable(now):
            self.room.broadcast({"t": "fx", "k": "immune", "e": e, "x": round(b.x), "y": round(b.y)})
            return
        m = b.move
        if m and m.window("guard", now):
            ang = math.atan2(fh.y - b.y, fh.x - b.x)
            if abs(_wrap(ang - aim_at(m.aims, now - m.start))) < math.radians(75):
                self.room.broadcast({"t": "fx", "k": "guarded", "e": e, "x": round(b.x), "y": round(b.y), "h": hid})
                return
        core = msg.get("core")
        build = fh.hero.build()
        crit = b.state == "stagger" and slot in ("heavy", "special") and hid not in b.crit_by
        if crit: b.crit_by.add(hid)  # one critical each per stagger; the stagger runs its full length
        mult *= build.dmg_mult(slot)
        if msg.get("atk") == "skill": mult *= build.dmg["skill"]
        poise *= build.poise_mult(slot)
        h = fh.hero
        if h.hp < h.mhp() * 0.5:
            for x in build.get("lowhp"): mult *= x["mult"]
        for x in build.get("vsstatus"):
            if now - b.marked[x["kind"]] < STATUS_LIVE: mult *= x["mult"]
        if fh.empowered and now < fh.empowered[1]:
            mult *= fh.empowered[0]; fh.empowered = None
        if now < fh.vengeance[1]: mult *= fh.vengeance[0]
        if any(math.hypot(o.x - fh.x, o.y - fh.y) < 90 for o in self.alive_heroes() if o is not fh):
            for x in build.get("near"): mult *= x["mult"]
        if crit:
            mult *= 3.0
            for x in build.get("crit"): mult *= x["mult"]
        dmg = round(C.WEAPONS[h.weapon]["base"] * mult)
        if isinstance(core, int) and 0 <= core < len(b.cores) and b.cores[core] > 0:
            b.cores[core] = max(0, b.cores[core] - dmg)
            cx, cy = b.core_pos(core)
            self.room.broadcast({"t": "fx", "k": "core", "e": e, "i": core, "dmg": dmg, "left": round(b.cores[core]), "h": hid,
                                 "x": round(cx), "y": round(cy)})
            if all(c <= 0 for c in b.cores):
                self.stagger(b, now, TOPPLE, "topple")
            return
        if b.armored():
            dmg = max(1, round(dmg * b.d.get("armor", 0.35)))
        extra = 0
        if slot == "light":
            fh.lights += 1
            for x in build.get("chain"):
                if fh.lights % x["every"] == 0:
                    extra += round(x["dmg"])
                    for s in build.get("chainstatus"): self.build_status(b, s["kind"], s["amt"] * build.buildup, now, fh)
                    for s in build.get("chainheal"): self.heal(fh, s["amt"])
                    self.room.broadcast({"t": "fx", "k": "chain", "e": e, "x": round(b.x), "y": round(b.y)})
        if slot == "special" and msg.get("atk") != "skill":
            for x in build.get("specialheal"): self.heal(fh, x["amt"])
        b.hp = max(0, b.hp - dmg - extra)
        fh.threat += dmg
        for x in build.get("steal"):
            if x["slot"] in (slot, "all"): self.heal(fh, dmg * x["frac"])
        if crit:
            for x in build.get("critstatus"):
                self.build_status(b, "burn", x["amt"], now, fh); self.build_status(b, "rot", x["amt"], now, fh)
        elif b.state != "stagger":
            self.damage_poise(b, poise, now)
        self.room.broadcast({"t": "fx", "k": "crit" if crit else "hit", "e": e, "h": hid, "dmg": dmg + extra, "x": round(b.x), "y": round(b.y)})
        if msg.get("atk") == "skill":  # a skill builds its own status, not the special's
            st = SKILLS[msg["sk"]].get("status")
            if st: self.build_status(b, st[0], st[1] * build.buildup, now, fh)
        else:
            own = C.WEAPONS[h.weapon].get("status", {}).get(slot)   # the weapon's own (the daggers' Bleed)
            for s in ([own] if own else []) + build.status[slot]: self.build_status(b, s[0], s[1] * build.buildup, now, fh)
        self.check_hp(b, now)

    def check_hp(self, b, now):
        if b.hp <= 0 and b.alive:
            self.body_down(b, now)
            return
        for i, th in enumerate(b.d.get("phases", [])):
            ph = i + 2
            if b.phase < ph and b.hp <= b.mhp * th:
                b.phase = ph
                mv = b.d.get("phase_moves", {}).get(ph)
                art = b.d.get("phase_art", {}).get(ph)
                if art: b.art = art
                if mv: self.start_move(b, f"phase{ph}", mv, now, cancel=True)
                break

    def hit_add(self, hid, msg, now):
        fh = self.heroes.get(hid)
        a = self.adds.get(msg.get("a"))
        if not fh or not a or fh.down or fh.dead or not self.new_swing(fh, msg): return
        if math.hypot(a["x"] - fh.x, a["y"] - fh.y) > 140: return
        at = self.attack(fh, msg, now)
        if not at: return
        mult, _, slot = at
        dmg = round(C.WEAPONS[fh.hero.weapon]["base"] * mult * fh.hero.build().dmg_mult(slot))
        a["hp"] -= dmg
        self.room.broadcast({"t": "fx", "k": "addhit", "a": a["id"], "dmg": dmg, "x": round(a["x"]), "y": round(a["y"])})
        if a["hp"] <= 0:
            del self.adds[a["id"]]
            self.room.broadcast({"t": "fx", "k": "adddie", "a": a["id"], "kind": a["kind"], "x": round(a["x"]), "y": round(a["y"])})

    def use_skill(self, hid, msg, now):
        """A hero used a skill (their browser plays it and reports its hits). Starts its cooldown and
        applies what acts at once: empower, rally, heal, ward."""
        fh = self.heroes.get(hid)
        s = SKILLS.get(msg.get("sk"))
        if not fh or not s or fh.down or fh.dead or self.over or s["id"] not in fh.hero.skills: return
        build = fh.hero.build()
        if now - fh.skill_used.get(s["id"], -99.0) < s["cd"] * build.stats["skill_cd"] - SKILL_SLACK: return
        fh.skill_used[s["id"]] = now
        for x in build.get("skillheal"): self.heal(fh, x["amt"])
        for x in build.get("skillward"): fh.shield = max(fh.shield, round(x["amt"]))
        near = [o for o in self.alive_heroes() if o is fh or math.hypot(o.x - fh.x, o.y - fh.y) <= s.get("radius", 0)]
        if "empower" in s: fh.empowered = (s["empower"], now + 5.0)
        if "rally" in s:
            for o in near: o.vengeance = (max(s["rally"], o.vengeance[0] if now < o.vengeance[1] else 1.0), now + s["secs"])
        if "heal" in s:
            for o in near:
                self.heal(o, fh.hero.mhp() * s["heal"])
                self.room.broadcast({"t": "fx", "k": "heal", "h": o.hero.id, "x": round(o.x), "y": round(o.y)})
        if "ward" in s: fh.shield = max(fh.shield, s["ward"])
        self.room.broadcast({"t": "fx", "k": "skill", "h": hid, "sk": s["id"], "x": round(fh.x), "y": round(fh.y)})

    def heal(self, fh, amt):
        h = fh.hero
        if fh.down or fh.dead or amt <= 0: return
        h.hp = min(h.mhp(), h.hp + max(1, round(amt)))

    def build_status(self, b, kind, amt, now, fh):
        """Add buildup on body b; a full meter bursts (and the next takes longer to fill)."""
        if not b.alive or amt <= 0: return
        b.meter[kind] += amt
        if b.meter[kind] < 100 * 1.4 ** b.procs[kind]:
            return
        b.meter[kind] = 0
        b.procs[kind] += 1
        b.marked[kind] = now
        build = fh.hero.build()
        mult = 1.0
        for x in build.get("statusmult"):
            if x["kind"] == kind: mult *= x["mult"]
        for x in build.get("combo"):
            if x["a"] == kind and now - b.marked[x["b"]] < STATUS_LIVE: mult *= x["mult"]
        scale = 1 + 0.25 * (self.tier - 1)
        dmg = 0
        if kind == "burn":
            dmg = round(70 * scale * mult)
        elif kind == "bleed":
            dmg = round(95 * scale * mult)
        elif kind == "frost":
            b.slow_until = now + STATUS_LIVE
            if build.get("frostbreak") and b.hp < b.mhp * 0.5:
                self.damage_poise(b, b.poise + 1, now)
            else:
                self.damage_poise(b, 50 * mult * (b.mpoise / b.base_poise) ** 0.5, now)
            dmg = round(20 * scale)
        elif kind == "rot":
            b.rot_until = now + 5.0
            b.rot_dps = 26 * scale * mult
            b.rot_blocks_poise = bool(build.get("vsstatus_poise"))
        for x in build.get("procbuild"):
            if x["on"] == kind: self.build_status(b, x["kind"], x["amt"], now, fh)
        if dmg:
            b.hp = max(0, b.hp - dmg)
        self.room.broadcast({"t": "fx", "k": "status", "e": b.e, "kind": kind, "dmg": dmg, "x": round(b.x), "y": round(b.y)})
        self.check_hp(b, now)

    def nearest_body(self, x, y):
        live = [b for b in self.bodies if b.alive] or self.bodies
        return min(live, key=lambda b: math.hypot(b.x - x, b.y - y))

    def dodged(self, hid, msg, now):
        """A hero rolled; if they rolled past a boss, their dodge upgrades build statuses."""
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead: return
        try:
            x0, y0, x1, y1 = (float(msg.get(k)) for k in ("x0", "y0", "x1", "y1"))
        except (TypeError, ValueError):
            return
        dx, dy = x1 - x0, y1 - y0
        L = max(1e-6, dx * dx + dy * dy)
        for b in self.bodies:
            if not b.alive: continue
            u = max(0.0, min(1.0, ((b.x - x0) * dx + (b.y - y0) * dy) / L))
            if math.hypot(x0 + dx * u - b.x, y0 + dy * u - b.y) > 50 + b.d["radius"]: continue
            build = fh.hero.build()
            for x in build.get("dodge"): self.build_status(b, x["kind"], x["amt"] * build.buildup, now, fh)

    def perfect(self, hid, now):
        """A hero's roll carried them through a hit (their browser says)."""
        fh = self.heroes.get(hid)
        if not fh: return
        for x in fh.hero.build().get("perfect"):
            fh.empowered = (x["dmg"], now + 2.0)
            if x.get("heal"): self.heal(fh, x["heal"])

    def damage_poise(self, b, amount, now):
        if b.state == "stagger": return  # it's already reeling; poise is whole again when it recovers
        if b.rot_until > now and b.rot_blocks_poise: amount *= 1.25
        b.poise -= amount
        b.poise_hit = now
        if b.poise <= 0 and b.state != "stagger" and not (b.move and b.move.data.get("invuln")):
            self.stagger(b, now, STAGGER, "stagger")

    def stagger(self, b, now, dur, kind):
        """The boss reels for `dur` seconds, open to one critical from each hero. Each stagger makes
        the next one harder to earn."""
        self.cancel(b, now)
        b.state, b.until = "stagger", now + dur
        b.crit_by = set()
        if kind == "stagger":
            b.staggers += 1
            b.mpoise = round(b.poise0 * (1 + POISE_GROW * b.staggers))
        b.poise = b.mpoise
        self.room.broadcast({"t": "fx", "k": kind, "e": b.e, "x": round(b.x), "y": round(b.y), "dur": dur})

    def hurt(self, hid, msg, now):
        """A hero took a hit (their browser decided). Applies the damage."""
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead or self.over: return
        key = str(msg.get("id"))[:24]
        if key in fh.hits_taken: return
        if key.startswith("a"):
            dmg, src = self.add_hit(fh, key)
            if dmg is None: return
        else:
            hit, start, mv = self.find_hit(key)
            if hit is None: return
            t = now - start
            if not (hit["t0"] - 0.6 <= t <= hit["t1"] + 0.8): return
            dmg, src = hit["dmg"], self.bodies[mv.e]
        fh.hits_taken.add(key)
        if len(fh.hits_taken) > 400: fh.hits_taken = set(list(fh.hits_taken)[-200:])
        b = src or self.nearest_body(fh.x, fh.y)
        build = fh.hero.build()
        if msg.get("parry") or msg.get("block"):
            for x in build.get("guard_status"): self.build_status(b, x["kind"], x["amt"] * build.buildup, now, fh)
        if msg.get("parry"):
            self.damage_poise(b, 60 * (b.mpoise / b.base_poise) ** 0.5, now)
            for x in build.get("parry"): fh.empowered = (x["mult"], now + 3.0)
            for x in build.get("parryheal"): self.heal(fh, x["amt"])
            for x in build.get("parrybolt"):
                b.hp = max(1, b.hp - round(x["dmg"]))
                self.room.broadcast({"t": "fx", "k": "chain", "e": b.e, "x": round(b.x), "y": round(b.y)})
            for o in self.heroes.values():
                for x in o.hero.build().get("allyparry"): o.empowered = (x["mult"], now + 3.0)
            self.room.broadcast({"t": "fx", "k": "parry", "h": hid, "x": round(fh.x), "y": round(fh.y)})
            return
        chip = C.WEAPONS[fh.hero.weapon]["guard"].get("chip", 0)
        if msg.get("block"):
            if not msg.get("counter"):
                self.room.broadcast({"t": "fx", "k": "block", "h": hid, "x": round(fh.x), "y": round(fh.y)})
            if not chip or msg.get("counter"): return
            dmg = dmg * chip  # a heavy weapon's block lets some through
        dmg = dmg * self.dmg_scale
        if fh.shield:
            soak = min(fh.shield, dmg); fh.shield -= soak; dmg -= soak
            if round(dmg) <= 0:  # the ward took all of it: no flinch from the drink, no damage number
                self.room.broadcast({"t": "fx", "k": "warded", "h": hid, "x": round(fh.x), "y": round(fh.y)})
                return
        fh.heal_at = None  # a hit spills the drink
        h = fh.hero
        h.hp = max(0, h.hp - round(dmg))
        self.room.broadcast({"t": "fx", "k": "hurt", "h": hid, "dmg": round(dmg), "x": round(fh.x), "y": round(fh.y)})
        if h.hp <= 0:
            self.knock_down(fh, now)

    def add_hit(self, fh, key):
        """An add touched a hero: 'a<id>:<n>' (n counts seconds of contact)."""
        try:
            aid = int(key[1:].split(":")[0])
        except ValueError:
            return None, None
        a = self.adds.get(aid)
        if not a or math.hypot(a["x"] - fh.x, a["y"] - fh.y) > a["r"] + 40: return None, None
        return a["dmg"], None

    def find_hit(self, key):
        """'seq:i' or 'seq:i:n' (n for repeating hits) -> (hit, the move's start time, the move)."""
        parts = key.split(":")
        try:
            seq, i = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return None, 0, None
        for m in self.moves():
            if m.seq == seq and 0 <= i < len(m.data["hits"]) and m.data["hits"][i]["k"] != "spawn":
                return m.data["hits"][i], m.start, m
        return None, 0, None

    def knock_down(self, fh, now):
        fh.down = True
        fh.heal_at = None
        for o in self.heroes.values():
            if o is not fh:
                for x in o.hero.build().get("ondown"): o.vengeance = (x["mult"], now + x["dur"])
        if self.solo and fh.hero.second_wind and self.diff.get("wind", True):
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
        if not any(x.get("free") for x in pacts):
            fh.hero.hp = max(1, fh.hero.hp - round(fh.hero.mhp() * d["cost"]))
        other.down = False
        other.hero.hp = max(1, round(other.hero.mhp() * d["rise"]))
        other.shield = round(sum(x.get("shield", 0) for x in pacts))
        self.room.broadcast({"t": "fx", "k": "revive", "h": who, "by": hid, "x": round(other.x), "y": round(other.y)})

    # ------------------------------------------------------------------ the boss
    def cancel(self, b, now):
        if b.move:
            self.room.broadcast({"t": "cancel", "seq": b.move.seq, "at": round(now, 3)})
            b.x, b.y = self.clamp(*b.move.pos(min(now, b.move.end())))
            b.move.last = min(b.move.last, now)
            self.recent = ([b.move] + self.recent)[:RECENT]
            b.move = None

    def body_down(self, b, now):
        self.cancel(b, now)
        b.state = "dead"
        b.hp = 0
        self.room.broadcast({"t": "fx", "k": "bodydown", "e": b.e, "x": round(b.x), "y": round(b.y)})
        rest = [o for o in self.bodies if o.alive]
        if not rest:
            self.over = "won"
            self.until = now + 3.5
            self.adds.clear()
            self.room.broadcast({"t": "fx", "k": "bossdown", "x": round(b.x), "y": round(b.y)})
            return
        for o in rest:  # the survivor takes up the fallen one's power (the Headsmen)
            if o.d.get("avenge") and not o.enraged:
                o.enraged = True
                o.phase = max(o.phase, 3)
                o.hp = min(o.mhp, o.hp + round(o.mhp * 0.25))
                mv = o.d.get("phase_moves", {}).get(3)
                if mv: self.start_move(o, "phase3", mv, now, cancel=True)

    def die(self, now):
        for b in self.bodies:
            if b.alive: self.body_down(b, now)

    def alive_heroes(self):
        return [f for f in self.heroes.values() if not f.down and not f.dead]

    def pick_target(self, b, now):
        """Who a body walks toward between attacks: whoever is near, has hurt it lately, hasn't been
        chased for a while, or has been keeping their distance (so archers and casters get hunted)."""
        best, score = None, -1e9
        for f in self.alive_heroes():
            d = math.hypot(f.x - b.x, f.y - b.y)
            s = (-d / 160 + f.threat * 0.01 + min(8.0, now - f.last_targeted) * 0.3 + min(4.0, f.far) * 0.35
                 + random.random() * 0.6)
            if len(self.bodies) > 1 and any(o.target is f for o in self.bodies if o is not b): s -= 1.0  # the two split up
            if s > score: best, score = f, s
        return best

    def target_weight(self, b, f, m, now):
        """How much a body wants to spend move m on hero f. Its walking target is favoured; anyone it
        hasn't attacked for a while, or who has kept their distance, draws its ranged moves."""
        w = 1.0 if f is b.target else 0.45
        w *= 1 + min(6.0, now - f.last_targeted) / 6
        if m["range"][0] >= 60: w *= 1 + min(4.0, f.far) * 0.3
        if any(o is not b and o.move and o.move.target == f.hero.id for o in self.bodies): w *= 0.4  # the two split up
        return w

    def start_move(self, b, mid, data, now, cancel=False):
        if cancel: self.cancel(b, now)
        t = b.target if b.target in self.alive_heroes() else self.pick_target(b, now)
        aim = math.atan2(t.y - b.y, t.x - b.x) if t else b.face
        dist = math.hypot(t.x - b.x, t.y - b.y) if t else 80
        dists = resolve(data, 0.0, dist, [0.0] * n_dists(data))
        self.seq += 1
        b.move = Move(self.seq, b.e, mid, data, now + LEAD, (b.x, b.y), aim, dists, t.hero.id if t else None)
        self.fit(b.move)
        b.face = aim
        b.state = "move"
        b.vx = b.vy = 0
        b.cool[mid] = now + LEAD + data["dur"] + data.get("cd", 0)
        b.last_move = mid
        extra = {"art": b.art} if mid.startswith("phase") else None
        self.room.broadcast(b.move.wire(extra))

    def choose(self, b, now):
        """A move and who it's for: any hero in that move's range, so a boss fighting the swords up
        close will turn its ranged moves on the archer at the back."""
        if not b.target: return None
        opts = []
        for mid, m in b.d["moves"].items():
            if b.phase not in m["phase"] or b.cool.get(mid, 0) > now: continue
            if m.get("enraged") and not b.enraged: continue
            if m.get("adds") and sum(1 for a in self.adds.values() if a["kind"] == m["adds"]) >= m.get("max_adds", 4): continue
            lo, hi = m["range"]
            for f in self.alive_heroes():
                if lo <= math.hypot(f.x - b.x, f.y - b.y) <= hi:
                    opts.append((mid, f, m["weight"] * (0.35 if mid == b.last_move else 1.0) * self.target_weight(b, f, m, now)))
        if not opts: return None
        r = random.random() * sum(w for _, _, w in opts)
        for mid, f, w in opts:
            r -= w
            if r <= 0: return mid, f
        return opts[-1][:2]

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

    # ------------------------------------------------------------------ adds
    def spawn(self, b, h, now):
        kind = self.boss["adds"][h["kind"]]
        a = b.move.aims[-1][1] if b.move else b.face
        n = h.get("n", 1)
        for i in range(n):
            if len(self.adds) >= 12: return
            ang = a + math.radians(h.get("spread", 0) * (i - (n - 1) / 2))
            x, y = self.clamp(b.x + math.cos(ang) * h.get("x", 30), b.y + math.sin(ang) * h.get("x", 30))
            self.add_seq += 1
            hp = kind["hp"] * (1 + 0.3 * (len(self.heroes) - 1))
            self.adds[self.add_seq] = {"id": self.add_seq, "kind": h["kind"], "x": x, "y": y, "hp": hp, "mhp": hp, "r": kind["radius"],
                                       "dmg": kind["dmg"], "speed": kind["speed"], "born": now, "life": kind.get("life", 30), "e": b.e}

    def step_adds(self, now):
        live = self.alive_heroes()
        for a in list(self.adds.values()):
            if now - a["born"] > a["life"]:
                del self.adds[a["id"]]
                self.room.broadcast({"t": "fx", "k": "adddie", "a": a["id"], "kind": a["kind"], "x": round(a["x"]), "y": round(a["y"])})
                continue
            if now - a["born"] < 0.6 or not live: continue
            t = min(live, key=lambda f: math.hypot(f.x - a["x"], f.y - a["y"]))
            dx, dy = t.x - a["x"], t.y - a["y"]
            d = math.hypot(dx, dy)
            if d > 4:
                a["x"], a["y"] = self.clamp(a["x"] + dx / d * a["speed"] * TICK, a["y"] + dy / d * a["speed"] * TICK)

    # ------------------------------------------------------------------ the tick
    def tick(self, now):
        if self.over == "lost": return
        for f in self.heroes.values():
            if f.heal_at and now >= f.heal_at:
                f.heal_at = None
                h = f.hero
                amt = h.mhp() * h.build().stats["heal"]
                h.hp = min(h.mhp(), h.hp + round(amt))
                self.room.broadcast({"t": "fx", "k": "heal", "h": h.id, "x": round(f.x), "y": round(f.y)})
                for x in h.build().get("flaskall"):
                    for o in self.alive_heroes():
                        if o is not f and math.hypot(o.x - f.x, o.y - f.y) < 70:
                            self.heal(o, amt * x["frac"])
            if f.down and f.second_wind and now >= f.second_wind:
                f.second_wind, f.down = None, False
                f.hero.hp = round(f.hero.mhp() * 0.5)
                self.room.broadcast({"t": "fx", "k": "revive", "h": f.hero.id, "x": round(f.x), "y": round(f.y)})
            elif f.down and not f.second_wind and f.bleed and now >= f.bleed:
                f.dead = True
                self.room.broadcast({"t": "fx", "k": "dead", "h": f.hero.id})
            f.threat *= 0.995
            near = min((math.hypot(f.x - b.x, f.y - b.y) for b in self.bodies if b.alive), default=0)
            f.far = f.far + TICK if near > 120 else max(0.0, f.far - 2 * TICK)
        if not self.alive_heroes() and not any(f.second_wind for f in self.heroes.values()) and self.over != "won":
            self.over = "lost"
            for b in self.bodies: self.cancel(b, now)
            self.room.broadcast({"t": "fx", "k": "wipe"})
            return
        if self.over == "won": return
        self.recent = [m for m in self.recent if m.last > now - 1.0]
        self.step_adds(now)
        for b in self.bodies:
            if b.alive: self.tick_body(b, now)

    def tick_body(self, b, now):
        if b.rot_until > now:
            b.rot_acc += b.rot_dps * TICK
            if b.rot_acc >= 10:
                n = int(b.rot_acc); b.rot_acc -= n
                b.hp = max(0, b.hp - n)
                self.room.broadcast({"t": "fx", "k": "dot", "e": b.e, "kind": "rot", "dmg": n, "x": round(b.x), "y": round(b.y)})
                self.check_hp(b, now)
                if not b.alive: return
        if b.state != "stagger" and now - b.poise_hit > POISE_REGEN[0] and not (b.rot_until > now and b.rot_blocks_poise):
            b.poise = min(b.mpoise, b.poise + b.mpoise * POISE_REGEN[1] * TICK)
        if b.state in ("intro", "stagger"):
            if now >= b.until:
                if b.state == "stagger" and b.cores:
                    b.cores = [c["hp"] * C.SCALE_HP[len(self.heroes) - 1] for c in b.d["cores"]]  # the cores glow again
                b.state, b.until = "idle", now + 0.3
            return
        if b.move:
            m = b.move
            t = now - m.start
            for lt in m.data.get("locks", []):
                if lt not in m.locked and t >= lt:
                    m.locked.add(lt)
                    tg = b.target if b.target in self.alive_heroes() else self.pick_target(b, now)
                    if tg:
                        bx, by = m.pos(now)
                        a = math.atan2(tg.y - by, tg.x - bx)
                        m.aims.append((lt, a))
                        m.dists = resolve(m.data, lt, math.hypot(tg.x - bx, tg.y - by), m.dists)
                        self.fit(m, lt)
                        b.face = a
                        self.room.broadcast({"t": "aim", "seq": m.seq, "lt": lt, "a": round(a, 4), "d": [round(d, 1) for d in m.dists]})
            for i, h in enumerate(m.data["hits"]):
                if h["k"] == "spawn" and i not in m.spawned and t >= h["t0"]:
                    m.spawned.add(i)
                    self.spawn(b, h, now)
            b.x, b.y = self.clamp(*m.pos(now))
            if now >= m.end():
                self.recent = ([m] + self.recent)[:RECENT]
                b.move = None
                b.target = self.pick_target(b, now)  # a new look round after every attack
                rest = (random.uniform(0.6, 1.2) if self.solo else random.uniform(0.25, 0.7)) * ((2.2 if self.solo else 1.9) if len(self.bodies) > 1 else 1)
                b.state, b.until = "idle", now + rest / self.diff["speed"]
            return
        if not b.target or b.target not in self.alive_heroes() or random.random() < 0.01:
            b.target = self.pick_target(b, now)
        t = b.target
        if not t:
            b.vx = b.vy = 0
            return
        if now >= b.until and not self.calm:
            pick = self.choose(b, now)
            if pick:
                mid, b.target = pick
                b.target.last_targeted = now
                self.start_move(b, mid, b.d["moves"][mid], now)
                return
        dx, dy = t.x - b.x, t.y - b.y
        d = math.hypot(dx, dy)
        b.face = math.atan2(dy, dx)
        keep = b.d.get("keep", 46)  # ranged bosses keep their distance
        if d > 0.5 and (d > keep + 6 or (b.d.get("keep") and d < keep * 0.5)):
            sp = b.d["speed"] * (1.15 if b.phase >= 2 else 1.0) * (0.55 if now < b.slow_until else 1.0) * self.diff["speed"]
            sgn = 1 if d > keep else -1
            b.vx, b.vy = dx / d * sp * sgn, dy / d * sp * sgn
            b.x, b.y = self.clamp(b.x + b.vx * TICK, b.y + b.vy * TICK)
        else:
            b.vx = b.vy = 0

    def snapshot(self, now):
        return {"t": "s", "st": round(now, 3),
                "b": [[round(b.x, 1), round(b.y, 1), round(b.vx, 1), round(b.vy, 1), round(b.face, 3), b.hp, b.mhp,
                       round(b.poise), b.mpoise, b.phase, b.state, [round(c) for c in b.cores],
                       # each status: how full its meter is (%), and whether it's in force (burst lately; rot still eating)
                       [min(100, round(100 * b.meter[k] / (100 * 1.4 ** b.procs[k]))) for k in STATUSES],
                       [1 if now - b.marked[k] < STATUS_LIVE or (k == "rot" and b.rot_until > now) else 0 for k in STATUSES]]
                      for b in self.bodies],
                "a": [[a["id"], a["kind"], round(a["x"], 1), round(a["y"], 1), round(a["hp"]), round(a["mhp"])] for a in self.adds.values()],
                "h": [[f.hero.id, round(f.x, 1), round(f.y, 1), round(f.face, 2), f.anim, round(f.at, 2), f.hero.hp, f.hero.mhp(),
                       f.hero.flasks, 1 if f.down else (2 if f.dead else 0),
                       round(max(0, f.bleed - now), 1) if f.down and f.bleed else 0, 1 if f.heal_at else 0,
                       # what's on them: ward left, seconds of extra damage left, a charged next hit
                       round(f.shield), round(max(0.0, f.vengeance[1] - now), 1) if f.vengeance[0] > 1 else 0,
                       1 if f.empowered and now < f.empowered[1] else 0]
                      for f in self.heroes.values()]}

    def start_wire(self):
        return {"t": "fight", "boss": self.boss["id"], "arena": self.boss["arena"], "size": [self.arena["w"], self.arena["h"]],
                "pad": self.arena["pad"], "intro": INTRO, "started": round(self.started, 3),
                "bodies": [{"mhp": b.mhp, "mpoise": b.mpoise, "x": round(b.x), "y": round(b.y), "art": b.art} for b in self.bodies],
                "heroes": {f.hero.id: [round(f.x), round(f.y)] for f in self.heroes.values()}}


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi
