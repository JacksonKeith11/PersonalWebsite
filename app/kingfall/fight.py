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
STRING_REST = 1.7    # after a string of moves a boss stands winded this long: the opening
BREAK_STAGGER = 3.5  # a boss whose break bar is emptied reels this long


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
        self.c = {}            # what this cast rolled: "v" its variant, "spots" [[x, y, r, tag, on]] (safe ground, cover)
        self.gone = set()      # hits struck back at the boss (a projectile with `ret`)
        self.brk = self.brk0 = 0.0   # its break bar: damage dealt in the move's `brk` window empties it
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
        if self.c: m["c"] = self.c
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
        self.unbowed = False        # the Unbowed blessing has saved them this fight
        self.skill_used = {}        # skill id -> when its cooldown began (cooldowns start afresh each fight; refunds move it back)
        self.skill_cast = {}        # skill id -> when it was really last cast (its hits count for a while after)
        self.held = 0.0             # caught (a tongue, a chain): can't move until then
        self.trance_until, self.trance_taken = 0.0, 1.0   # Battle Trance: hits taken hurt more until then
        self.guard_until = 0.0      # Stone Ward: the next hit before then is soaked whole
        self.seeded = -9.0          # when a dodge last seeded the boss with a status (Spore Cloud)
        self.zoned = {}             # skill id -> the cast whose area has been placed
        self.paid = set()           # swings that have already paid their price in health (Blood blessings)


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
        self.sigils, self.sigil_until = 0, 0.0   # the catalyst's marks on this body (content/weapons.py, `sigil`)
        self.enraged = False
        self.art = d["art"]
        self.chain = 0           # moves into the string it's playing
        self.tired_until = 0.0   # winded after a string: stands still, the opening
        self.reap = {}           # hero id -> [until, uses left]: the scythe's mark (content/weapons.py, `reap`)
        self.growth = None       # a canker planted by a special (the Rot blessing): {until, acc, frac, amt, by}
        self.queue = []          # signature moves owed (its health passed one of its `marks`)
        self.marks_done = set()

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
        self.zones = []           # circles heroes' skills leave on the ground: {x, y, r, until, sk, by, next}
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
        w = self.W(fh)
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
            if not s or s["id"] not in fh.hero.skills: return None
            if now - fh.skill_cast.get(s["id"], -99.0) > s.get("live", SKILL_LIVE): return None
            part = s.get("sub", {}).get(msg.get("sub")) if msg.get("sub") else s   # a further hit of the skill, priced on its own
            if not part or "mult" not in part: return None
            return part["mult"] * SKILL_BASE / w["base"], part["poise"], "special"
        if kind == "proc":   # an upgrade's extra attack: priced like a skill, whatever the weapon
            f = next((x for x in fh.hero.build().get("proc") if x["uid"] == msg.get("p")), None)
            if not f: return None
            return f["pow"] * SKILL_BASE / w["base"], f.get("poise", 4), "proc"
        if kind == "move":   # a weapon's named attack (a dash-strike, the riposte, the whirlwind...): priced as its slot
            atk = w.get("moves", {}).get(msg.get("m"))
            if not atk: return None
            return atk["mult"], atk["poise"], atk.get("slot", "light")
        if kind == "guard" and "mult" in w["guard"]:  # the halberd's counter, the bow's roll-shot
            return w["guard"]["mult"], w["guard"].get("poise", 8), kind
        return None

    def W(self, fh):
        """A hero's weapon table, with what their blessings change in it."""
        return fh.hero.build().weapon(fh.hero.weapon)

    def open(self, b, now):
        """Is this body open to a counter-hit: mid-attack (a move under way) or winded after a string?"""
        return b.move is not None or (b.state == "idle" and now < b.tired_until)

    def gain(self, fh, **kw):
        """Tell a hero's browser what a blessing just gave them: Focus, seconds off their skills' cooldowns,
        dashes (the browser keeps all three). The server's own cooldown clocks move with it."""
        if kw.get("cd"):   # `sk`: only that skill's
            for k in fh.skill_used:
                if kw.get("sk") in (None, k): fh.skill_used[k] -= kw["cd"]
        self.room.broadcast({"t": "fx", "k": "gain", "h": fh.hero.id, **{k: round(v, 2) if isinstance(v, (int, float)) else v for k, v in kw.items()}})

    def pay(self, fh, cost, key=None):
        """Health spent on a Blood blessing (once per `key`); never the last point."""
        if key is not None:
            if key in fh.paid: return
            fh.paid.add(key)
            if len(fh.paid) > 200: fh.paid = set(list(fh.paid)[-100:])
        fh.hero.hp = max(1, fh.hero.hp - round(cost))

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
        atk, sw = msg.get("atk"), msg.get("sw")
        skill = SKILLS.get(msg.get("sk")) if atk == "skill" else None
        W = self.W(fh)
        # a counter-hit: on a boss that is mid-attack or winded, some skills and blessings strike harder
        counter = None
        if self.open(b, now):
            cs = [skill["counter"]] if skill and skill.get("counter") and not msg.get("sub") else []
            if atk == "special" and W["special"].get("counter"): cs.append(W["special"]["counter"])   # the scythe's Harvest
            cs += [{"dmg": x["mult"], "poise": x["poise"]} for x in build.get("counterhit")
                   if (x["slot"] == "skill" and atk == "skill") or (x["slot"] == "special" and slot == "special" and atk != "skill")]
            for c in cs:
                mult *= c.get("dmg", 1.0); poise *= c.get("poise", 1.0); counter = "counter"
                if c.get("refund") and (sw, "refund") not in fh.swings:   # Storm Bolt: part of its cooldown comes straight back
                    fh.swings.add((sw, "refund"))
                    self.gain(fh, cd=skill["cd"] * build.stats["skill_cd"] * c["refund"], sk=skill["id"])
        ex = skill.get("execute") if skill and not msg.get("sub") else None
        if ex and b.hp < b.mhp * ex["below"]: mult *= ex["dmg"]; counter = "execute"   # Deathblow: double on a boss near its end
        # Blood: the combo's last light and an overcharged heavy cost health and hit harder; Storm's echo is half a special
        if atk == "light" and msg.get("i") == len(self.W(fh)["light"]) - 1:
            for x in build.get("bloodfin"): mult *= x["mult"]; self.pay(fh, x["cost"], ("fin", sw))
        if atk == "heavy" and msg.get("oc"):
            for x in build.get("overcharge"): mult *= x["mult"]; self.pay(fh, x["cost"], ("oc", sw))
        if atk == "special" and msg.get("eh"):
            for x in build.get("echo"): mult *= x["frac"]
        if atk == "move":
            for x in build.get("movedmg"):
                if x["move"] == msg.get("m"): mult *= x["mult"]
        # what only this weapon does: the daggers bite deeper from behind, the halberd at its tip, the bow on a
        # Power Shot (the browser says which hits were), and the catalyst's heavy and special spend its sigils
        bonus = counter
        # the second six: a streak spent (gauntlets), a caught disc or a primed shot (chakrams, cannon), a mark reaped (scythe)
        st = W.get("streak")
        if st and atk == "heavy" and W["heavy"].get("spend") and isinstance(msg.get("sk"), int) and msg["sk"] > 0:
            mult *= 1 + st["per"] * min(st["max"], msg["sk"]); bonus = "streak"
        if W.get("ammo") and msg.get("ch") and atk in ("light", "heavy"):
            mult *= W["ammo"]["caught"]; bonus = "catch"
        rp = W.get("reap")
        if rp and core is None:
            mark = b.reap.get(hid)
            if atk == "light" and msg.get("i") == len(W["light"]) - 1:
                b.reap[hid] = [now + rp["live"], rp["uses"]]
            elif atk == "heavy" and mark and now < mark[0] and (sw, "reap") not in fh.swings:
                fh.swings.add((sw, "reap"))
                mult *= rp["mult"]; bonus = "reap"; self.heal(fh, rp["heal"])
                mark[1] -= 1
                if mark[1] <= 0: del b.reap[hid]
        if msg.get("atk") in ("light", "heavy", "special", "move"):
            if msg.get("bk") and W.get("backstab"): mult *= W["backstab"]; bonus = "back"
            if msg.get("tip") and W.get("tip"): mult *= W["tip"]; bonus = "tip"
            if msg.get("pw") and slot == "heavy" and W["heavy"].get("power"): mult *= W["heavy"]["power"]["mult"]; bonus = "power"
            sg = W.get("sigil")
            if sg and core is None:
                if now > b.sigil_until: b.sigils = 0
                if slot == "light":
                    b.sigils = min(sg["max"], b.sigils + 1); b.sigil_until = now + sg["live"]
                elif b.sigils and msg.get("atk") in ("heavy", "special"):
                    mult *= 1 + sg["per"] * b.sigils; bonus = "sigil"; b.sigils = 0
        if slot == "light" and isinstance(msg.get("i"), int):   # Momentum: each hit of the combo more than the last
            for x in build.get("ramp"): mult *= x["mult"] ** max(0, min(6, msg["i"]))
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
        # circles on the ground: a banner the hero stands in, a cloud the boss stands in
        rally = [z["rally"] for z in self.zones if z.get("rally") and math.hypot(z["x"] - fh.x, z["y"] - fh.y) <= z["r"]]
        if rally and not now < fh.vengeance[1]: mult *= max(rally)
        for z in self.zones:
            if z.get("vuln") and math.hypot(z["x"] - b.x, z["y"] - b.y) <= z["r"] + b.d["radius"]: mult *= z["vuln"]; break
        if crit:
            mult *= 3.0
            for x in build.get("crit"): mult *= x["mult"]
            for x in build.get("critextend"): b.until += x["secs"]
        dmg = round(W["base"] * mult)
        if m and m.brk > 0 and m.window("brk_win", now):   # a break bar: emptied, the move is broken off and the boss reels
            m.brk -= dmg * (skill.get("brk", 1.0) if skill else 1.0)
            if m.brk <= 0:
                self.room.broadcast({"t": "fx", "k": "broken", "e": e, "h": hid, "x": round(b.x), "y": round(b.y)})
                self.stagger(b, now, m.data["brk"].get("stagger", BREAK_STAGGER), "break")
                for f in self.heroes.values(): f.held = 0.0
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
        if slot == "special" and atk != "skill":
            for x in build.get("specialheal"): self.heal(fh, x["amt"])
            for x in build.get("growth"):   # a canker: it bursts later for a share of what the body takes meanwhile
                if not b.growth: b.growth = {"until": now + x["secs"], "acc": 0.0, "frac": x["frac"], "amt": x["amt"], "by": fh}
        if skill and skill.get("brand") and not msg.get("sub") and not b.growth:   # Storm Brand: struck later for a share of what it takes meanwhile
            b.growth = {"until": now + skill["brand"]["secs"], "acc": 0.0, "frac": skill["brand"]["frac"], "amt": 0, "by": fh, "word": "BRAND", "kind": "bolt"}
        if skill and skill.get("cdhit") and (sw, "cd") not in fh.swings:   # each strike that lands brings it back sooner
            fh.swings.add((sw, "cd")); fh.skill_used[skill["id"]] = fh.skill_used.get(skill["id"], now) - skill["cdhit"]
        if b.growth: b.growth["acc"] += dmg + extra
        fh.hero.tally["dmg"] += min(b.hp, dmg + extra)
        b.hp = max(0, b.hp - dmg - extra)
        fh.threat += dmg
        for x in build.get("steal"):
            if x["slot"] in (slot, "all"): self.heal(fh, dmg * x["frac"])
        if crit:
            for x in build.get("critstatus"):
                self.build_status(b, "burn", x["amt"], now, fh); self.build_status(b, "rot", x["amt"], now, fh)
        elif b.state != "stagger":
            self.damage_poise(b, poise, now)
        fx = {"t": "fx", "k": "crit" if crit else "hit", "e": e, "h": hid, "dmg": dmg + extra, "x": round(b.x), "y": round(b.y)}
        if bonus: fx["bonus"] = bonus
        if W.get("sigil"): fx["sg"] = b.sigils
        if rp: fx["mk"] = round(max(0.0, b.reap[hid][0] - now), 1) if hid in b.reap else 0
        self.room.broadcast(fx)
        if atk == "skill":  # a skill builds its own status, not the special's
            st = (skill["sub"][msg["sub"]] if msg.get("sub") else skill).get("status")
            if st: self.build_status(b, st[0], st[1] * build.buildup, now, fh)
        elif msg.get("atk") == "proc":  # and so does an upgrade's extra attack
            f = next((x for x in build.get("proc") if x["uid"] == msg.get("p")), None)
            if f and f.get("kind"): self.build_status(b, f["kind"], f["amt"] * build.buildup, now, fh)
            if f and f.get("heal"): self.heal(fh, f["heal"])
        else:
            own = W.get("status", {}).get(slot)   # the weapon's own (the daggers' Bleed)
            for s in ([own] if own else []) + build.status[slot]: self.build_status(b, s[0], s[1] * build.buildup, now, fh)
        self.check_hp(b, now)

    def check_hp(self, b, now):
        if b.hp <= 0 and b.alive:
            self.body_down(b, now)
            return
        for i, (th, mid) in enumerate(b.d.get("marks", [])):   # its signature moves come at set points of the fight
            if i not in b.marks_done and b.hp <= b.mhp * th:
                b.marks_done.add(i)
                b.queue.append(mid)
        if b.state == "stagger": return   # a stagger runs its full length: the next phase waits for it to end
        for i, th in enumerate(b.d.get("phases", [])):
            ph = i + 2
            if b.phase < ph and b.hp <= b.mhp * th:
                b.phase = ph
                b.chain = 0
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
        dmg = round(self.W(fh)["base"] * mult * fh.hero.build().dmg_mult(slot))
        a["hp"] -= dmg
        self.room.broadcast({"t": "fx", "k": "addhit", "a": a["id"], "dmg": dmg, "x": round(a["x"]), "y": round(a["y"])})
        if a["hp"] <= 0:
            del self.adds[a["id"]]
            if a.get("spot"):   # a candle lit: its light is safe ground for the cast that set it out
                seq, i = a["spot"]
                for m in self.moves():
                    if m.seq == seq:
                        m.c["spots"][i][4] = 1
                        self.room.broadcast({"t": "spot", "seq": seq, "i": i})
            self.room.broadcast({"t": "fx", "k": "adddie", "a": a["id"], "kind": a["kind"], "x": round(a["x"]), "y": round(a["y"])})

    def use_skill(self, hid, msg, now):
        """A hero used a skill (their browser plays it and reports its hits). Starts its cooldown and
        applies what acts at once: empower, rally, heal, ward."""
        fh = self.heroes.get(hid)
        s = SKILLS.get(msg.get("sk"))
        if not fh or not s or fh.down or fh.dead or self.over or s["id"] not in fh.hero.skills: return
        build = fh.hero.build()
        if now - fh.skill_used.get(s["id"], -99.0) < s["cd"] * build.stats["skill_cd"] - SKILL_SLACK: return
        fh.skill_used[s["id"]] = fh.skill_cast[s["id"]] = now
        if msg.get("ff") and build.get("meditate"):   # Meditation: used at full Focus, it comes back in half the time
            fh.skill_used[s["id"]] = now - s["cd"] * build.stats["skill_cd"] * 0.5
        for x in build.get("skillheal"): self.heal(fh, x["amt"])
        for x in build.get("skillward"): fh.shield = max(fh.shield, round(x["amt"]))
        near = [o for o in self.alive_heroes() if o is fh or math.hypot(o.x - fh.x, o.y - fh.y) <= s.get("radius", 0)]
        if "empower" in s: fh.empowered = (s["empower"], now + 5.0)
        if "guard" in s: fh.guard_until = now + s["guard"]
        if "cost" in s:   # Blood Pact: paid in health
            self.pay(fh, s["cost"])
            self.room.broadcast({"t": "fx", "k": "paid", "h": hid, "dmg": round(s["cost"]), "x": round(fh.x), "y": round(fh.y)})
        if "trance" in s:
            T = s["trance"]
            fh.trance_until, fh.trance_taken = now + T["secs"], T["taken"]
            fh.vengeance = (max(T["dmg"], fh.vengeance[0] if now < fh.vengeance[1] else 1.0), now + T["secs"])
        self.room.broadcast({"t": "fx", "k": "skill", "h": hid, "sk": s["id"], "x": round(fh.x), "y": round(fh.y)})
        if s.get("zone") and s["zone"].get("at") != "aoe": self.add_zone(fh, s, fh.x, fh.y, now)

    def add_zone(self, fh, s, x, y, now):
        """A skill's circle on the ground (a banner, hallowed ground, a censer's cloud)."""
        z = s["zone"]
        self.zones.append({**z, "x": x, "y": y, "until": now + z["secs"], "sk": s["id"], "by": fh, "next": now + z.get("every", 1.0)})
        self.room.broadcast({"t": "fx", "k": "zone", "h": fh.hero.id, "sk": s["id"], "x": round(x), "y": round(y), "r": z["r"], "dur": z["secs"]})

    def zone_at(self, hid, msg, now):
        """A browser says where its skill's area landed (the censer's cloud)."""
        fh, s = self.heroes.get(hid), SKILLS.get(msg.get("sk"))
        if not fh or not s or not s.get("zone") or s["zone"].get("at") != "aoe" or fh.zoned.get(s["id"]) == fh.skill_cast.get(s["id"]): return
        if now - fh.skill_cast.get(s["id"], -99.0) > 2.0: return
        try:
            x, y = float(msg.get("x")), float(msg.get("y"))
        except (TypeError, ValueError):
            return
        if math.hypot(x - fh.x, y - fh.y) > s["aoe"].get("range", 0) + 60: return
        fh.zoned[s["id"]] = fh.skill_cast[s["id"]]
        self.add_zone(fh, s, x, y, now)

    def plant(self, hid, msg, now):
        """The war banner's standard, planted (its bearer's browser says where) or called back (`up`)."""
        fh = self.heroes.get(hid)
        if not fh: return
        st = self.W(fh).get("stand")
        had = any(z["sk"] == "standard" and z["by"] is fh for z in self.zones)
        self.zones = [z for z in self.zones if not (z["sk"] == "standard" and z["by"] is fh)]
        if had: self.room.broadcast({"t": "fx", "k": "unzone", "h": hid})
        if not st or msg.get("up") or fh.down or fh.dead: return
        try:
            x, y = float(msg.get("x")), float(msg.get("y"))
        except (TypeError, ValueError):
            return
        if math.hypot(x - fh.x, y - fh.y) > 80: return
        self.zones.append({"x": x, "y": y, "r": st["r"], "until": float("inf"), "sk": "standard", "by": fh, "rally": st["rally"],
                           "hps": st.get("hps", 0), "every": 1.0, "next": now + 1.0})
        self.room.broadcast({"t": "fx", "k": "zone", "h": hid, "sk": "standard", "x": round(x), "y": round(y), "r": st["r"], "dur": 0})

    def pay_special(self, hid, now):
        """Bloodletting: a special used without the Focus for it costs health."""
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead: return
        for x in fh.hero.build().get("bloodspecial"):
            self.pay(fh, x["cost"])
            self.room.broadcast({"t": "fx", "k": "paid", "h": hid, "dmg": round(x["cost"]), "x": round(fh.x), "y": round(fh.y)})

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
        for x in build.get("burstheal"):
            if x["kind"] == kind: self.heal(fh, x["amt"])
        for x in build.get("burstgain"):
            if x["kind"] == kind: self.gain(fh, **{k: x[k] for k in ("cd", "focus") if k in x})
        for x in build.get("procbuild"):
            if x["on"] == kind: self.build_status(b, x["kind"], x["amt"], now, fh)
        if dmg:
            fh.hero.tally["dmg"] += min(b.hp, dmg)
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
        fh.hero.tally["dodges"] += 1
        build = fh.hero.build()
        for x in build.get("perfect"):
            fh.empowered = (x["dmg"], now + 2.0)
            if x.get("heal"): self.heal(fh, x["heal"])
        if fh.down or fh.dead: return
        for x in build.get("perfectstatus"):   # at most once a second: a fan of shots is one dodge
            if now - fh.seeded >= 1.0:
                fh.seeded = now
                self.build_status(self.nearest_body(fh.x, fh.y), x["kind"], x["amt"] * build.buildup, now, fh)

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
        hit = mv = None
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
        if msg.get("ward") and now <= fh.guard_until + 0.3 and not (hit and hit.get("room")):   # Stone Ward soaked it whole
            fh.guard_until = 0.0
            ws = SKILLS["ward"]
            fh.skill_used["ward"] = fh.skill_used.get("ward", now) - ws["cd"] * build.stats["skill_cd"] * ws["refund"]
            self.room.broadcast({"t": "fx", "k": "warded", "h": hid, "x": round(fh.x), "y": round(fh.y), "burst": 1})
            return
        if msg.get("counter") and hit and hit.get("v") and b.alive:   # Answering Blade: a countered shot goes back
            for x in build.get("countershot"):
                b.hp = max(1, b.hp - round(x["dmg"]))
                self.room.broadcast({"t": "fx", "k": "reflect", "seq": mv.seq, "i": -1, "e": mv.e, "h": hid, "x": round(fh.x), "y": round(fh.y)})
        if msg.get("parry") or msg.get("block"):
            for x in build.get("guard_status"): self.build_status(b, x["kind"], x["amt"] * build.buildup, now, fh)
        if msg.get("parry") and hit and hit.get("ret"):   # a parried projectile that can be struck back goes back
            i = int(key.split(":")[1])
            if i not in mv.gone:
                mv.gone.add(i)
                self.room.broadcast({"t": "fx", "k": "reflect", "seq": mv.seq, "i": i, "e": mv.e, "h": hid, "x": round(fh.x), "y": round(fh.y)})
        if msg.get("parry"):
            fh.hero.tally["parries"] += 1
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
        chip = self.W(fh)["guard"].get("chip", 0)
        if msg.get("block"):
            if not msg.get("counter"):
                self.room.broadcast({"t": "fx", "k": "block", "h": hid, "x": round(fh.x), "y": round(fh.y)})
            if not chip or msg.get("counter"): return
            dmg = dmg * chip  # a heavy weapon's block lets some through
        dmg = dmg * self.dmg_scale * (fh.trance_taken if now < fh.trance_until else 1.0)
        if fh.shield:
            soak = min(fh.shield, dmg); fh.shield -= soak; dmg -= soak
            if round(dmg) <= 0:  # the ward took all of it: no flinch from the drink, no damage number
                self.room.broadcast({"t": "fx", "k": "warded", "h": hid, "x": round(fh.x), "y": round(fh.y)})
                return
        fh.heal_at = None  # a hit spills the drink
        h = fh.hero
        h.tally["taken"] += min(h.hp, round(dmg))
        h.hp = max(0, h.hp - round(dmg))
        self.room.broadcast({"t": "fx", "k": "hurt", "h": hid, "dmg": round(dmg), "x": round(fh.x), "y": round(fh.y)})
        if hit and hit.get("hold") and h.hp > 0:   # caught: held where they stand, and the other twin may come for them
            fh.held = now + hit["hold"]
            self.room.broadcast({"t": "fx", "k": "held", "h": hid, "e": mv.e, "seq": mv.seq, "dur": hit["hold"]})
            call = mv.data.get("call")
            for o in self.bodies:
                if call and o is not src and o.alive and o.state not in ("stagger", "intro") and call in o.d["moves"] \
                        and not (o.move and o.move.data.get("invuln")):
                    self.start_move(o, call, o.d["moves"][call], now, cancel=True, target=fh)
                    break
        if h.hp <= 0:
            saved = None if fh.unbowed else next(iter(fh.hero.build().get("unbowed")), None)
            if saved:   # Unbowed: once a fight, left standing
                fh.unbowed = True
                h.hp = min(h.mhp(), max(1, round(saved["amt"])))
                self.room.broadcast({"t": "fx", "k": "unbowed", "h": hid, "x": round(fh.x), "y": round(fh.y)})
            else:
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

    def reflect(self, hid, msg, now):
        """A hero struck one of the boss's projectiles back at it (their browser says): it's gone for
        everyone, and it costs the boss poise like a parry."""
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead or self.over: return
        hit, start, mv = self.find_hit(f"{msg.get('seq')}:{msg.get('i')}")
        i = msg.get("i")
        if hit is None or not hit.get("ret") or i in mv.gone: return
        if not (hit["t0"] - 0.3 <= now - start <= hit["t1"] + 0.5): return
        mv.gone.add(i)
        b = self.bodies[mv.e]
        self.room.broadcast({"t": "fx", "k": "reflect", "seq": mv.seq, "i": i, "e": mv.e, "h": hid, "x": round(fh.x), "y": round(fh.y)})
        if b.alive and b.state not in ("intro", "dead"):
            self.damage_poise(b, hit["ret"] * (b.mpoise / b.base_poise) ** 0.5, now)

    def clear(self, hid, msg, now):
        """A hero's burst of frost shattered one of the boss's projectiles (their browser says): gone for everyone."""
        fh = self.heroes.get(hid)
        if not fh or fh.down or fh.dead or self.over: return
        if not any(SKILLS[k].get("clear") or SKILLS[k].get("aoe", {}).get("clear") for k in fh.hero.skills if k in SKILLS) \
                and not any(x.get("aoe", {}).get("clear") for x in fh.hero.build().get("proc")) and not self.W(fh)["special"].get("clear"): return
        hit, start, mv = self.find_hit(f"{msg.get('seq')}:{msg.get('i')}")
        i = msg.get("i")
        if hit is None or hit.get("k") != "proj" or i in mv.gone: return
        mv.gone.add(i)
        x, y = msg.get("x"), msg.get("y")
        self.room.broadcast({"t": "fx", "k": "cleared", "seq": mv.seq, "i": i, "h": hid,
                             "x": x if isinstance(x, (int, float)) else round(fh.x), "y": y if isinstance(y, (int, float)) else round(fh.y)})

    def knock_down(self, fh, now):
        fh.down = True
        fh.hero.tally["downs"] += 1
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
        for x in fh.hero.build().get("flaskrally"): fh.vengeance = (x["mult"], now + x["dur"])

    def revive(self, hid, who, now):
        fh, other = self.heroes.get(hid), self.heroes.get(who)
        if not fh or not other or fh is other or fh.down or fh.dead or not other.down or other.dead: return
        if math.hypot(fh.x - other.x, fh.y - other.y) > 40: return
        d = C.HERO["down"]
        pacts = fh.hero.build().get("revive")
        if not any(x.get("free") for x in pacts):
            fh.hero.hp = max(1, fh.hero.hp - round(fh.hero.mhp() * d["cost"]))
        other.down = False
        fh.hero.tally["revives"] += 1
        other.hero.hp = max(1, round(other.hero.mhp() * d["rise"]))
        other.shield = round(sum(x.get("shield", 0) for x in pacts))
        if fh.hero.build().get("revivegain"):
            self.gain(fh, dash=9); self.gain(other, dash=9)
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

    def start_move(self, b, mid, data, now, cancel=False, target=None):
        if cancel: self.cancel(b, now)
        t = target or (b.target if b.target in self.alive_heroes() else self.pick_target(b, now))
        self.seq += 1
        cast = {}
        if data.get("variants"): cast["v"] = random.randrange(data["variants"])
        if data.get("spots"):
            cast["spots"] = [[round(x), round(y), r, tag, on] for x, y, r, tag, on in SPOTS[data["spots"]](self, b, t, data, now)]
            if data.get("blink"): b.x, b.y = cast["spots"][0][:2]   # it reappears on the first spot
        aim = math.atan2(t.y - b.y, t.x - b.x) if t else b.face
        dist = math.hypot(t.x - b.x, t.y - b.y) if t else 80
        dists = resolve(data, 0.0, dist, [0.0] * n_dists(data))
        b.move = Move(self.seq, b.e, mid, data, now + LEAD, (b.x, b.y), aim, dists, t.hero.id if t else None)
        b.move.c = cast
        if data.get("brk"):
            b.move.brk = b.move.brk0 = data["brk"]["hp"] * C.SCALE_HP[len(self.heroes) - 1] * self.diff["hp"]
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
            if m.get("sig") or (m.get("enraged") and not b.enraged): continue
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

    def spawn_at(self, b, kind_id, x, y, now, life, spot=None):
        """An add that stands where it's put (a candle): for a signature move's cast."""
        kind = self.boss["adds"][kind_id]
        self.add_seq += 1
        hp = kind["hp"] * (1 + 0.3 * (len(self.heroes) - 1))
        self.adds[self.add_seq] = {"id": self.add_seq, "kind": kind_id, "x": x, "y": y, "hp": hp, "mhp": hp, "r": kind["radius"],
                                   "dmg": kind["dmg"], "speed": kind["speed"], "born": now, "life": life, "e": b.e, "spot": spot}

    def spread(self, n, r, gap, near=None, lo=0.0, hi=0.0):
        """n points inside the walls, r from them and `gap` apart; with `near`, each lo..hi from it."""
        l, t, rt, bt = self.arena["pad"]
        x0, x1, y0, y1 = l + r + 6, self.arena["w"] - rt - r - 6, t + r + 6, self.arena["h"] - bt - r - 6
        pts = []
        for _ in range(400):
            if len(pts) == n: break
            if near:
                a, d = random.uniform(0, 2 * math.pi), random.uniform(lo, hi)
                x, y = near[0] + math.cos(a) * d, near[1] + math.sin(a) * d
                if not (x0 <= x <= x1 and y0 <= y <= y1): continue
            else:
                x, y = random.uniform(x0, x1), random.uniform(y0, y1)
            if all(math.hypot(x - px, y - py) >= gap for px, py in pts): pts.append((x, y))
        while len(pts) < n: pts.append((random.uniform(x0, x1), random.uniform(y0, y1)))
        return pts

    def step_adds(self, now):
        live = self.alive_heroes()
        for a in list(self.adds.values()):
            if now - a["born"] > a["life"]:
                del self.adds[a["id"]]
                self.room.broadcast({"t": "fx", "k": "adddie", "a": a["id"], "kind": a["kind"], "x": round(a["x"]), "y": round(a["y"])})
                continue
            if now - a["born"] < 0.6 or not live or not a["speed"]: continue
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
        for z in self.zones:   # hallowed ground heals whoever stands in it
            if z.get("hps") and now >= z["next"]:   # a standard that mends (a Weapon Art): a little, every second
                z["next"] += z["every"]
                for o in self.alive_heroes():
                    if math.hypot(o.x - z["x"], o.y - z["y"]) <= z["r"] and o.hero.hp < o.hero.mhp(): self.heal(o, z["hps"])
            elif z.get("heal") and now >= z["next"]:
                z["next"] += z["every"]
                for o in self.alive_heroes():
                    if math.hypot(o.x - z["x"], o.y - z["y"]) <= z["r"] and o.hero.hp < o.hero.mhp():
                        self.heal(o, z["by"].hero.mhp() * z["heal"] * z["every"] / z["secs"])
                        self.room.broadcast({"t": "fx", "k": "mend", "h": o.hero.id, "x": round(o.x), "y": round(o.y)})
        self.zones = [z for z in self.zones if now < z["until"]]
        for b in self.bodies:   # a canker bursts
            g = b.growth
            if g and now >= g["until"]:
                b.growth = None
                if not b.alive: continue
                dmg = round(g["acc"] * g["frac"])
                if dmg:
                    g["by"].hero.tally["dmg"] += min(b.hp, dmg)
                    b.hp = max(0, b.hp - dmg)
                    self.room.broadcast({"t": "fx", "k": "status", "e": b.e, "kind": g.get("kind", "rot"), "word": g.get("word", "CANKER"), "dmg": dmg, "x": round(b.x), "y": round(b.y)})
                if g["amt"]: self.build_status(b, "rot", g["amt"] * g["by"].hero.build().buildup, now, g["by"])
                self.check_hp(b, now)
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
                was = b.state
                b.state, b.until = "idle", now + 0.3
                if was == "stagger": self.check_hp(b, now)   # a phase it was beaten into while reeling begins now
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
                # a string: some moves are always followed by another, at the same hero, with no rest between
                nxt = m.data.get("then")
                nxt = random.choice(nxt) if isinstance(nxt, list) else nxt
                tg = self.heroes.get(m.target)
                nd = b.d["moves"].get(nxt)
                if (nd and b.chain < 2 and not b.queue and not self.calm and tg in self.alive_heroes() and b.phase in nd["phase"]
                        and nd["range"][0] * 0.8 <= math.hypot(tg.x - b.x, tg.y - b.y) <= nd["range"][1] * 1.25):
                    b.chain += 1
                    b.target = tg
                    self.start_move(b, nxt, nd, now, target=tg)
                    return
                tired = m.data.get("tired") or (STRING_REST if b.chain else 0)
                b.chain = 0
                b.target = self.pick_target(b, now)  # a new look round after every attack
                rest = (random.uniform(0.6, 1.2) if self.solo else random.uniform(0.25, 0.7)) * ((2.2 if self.solo else 1.9) if len(self.bodies) > 1 else 1)
                if tired:   # winded: it stands and pants, open to whatever you have
                    rest = tired + (0.3 if self.solo else 0)
                    b.tired_until = now + rest / self.diff["speed"]
                b.state, b.until = "idle", now + rest / self.diff["speed"]
            return
        if now < b.tired_until:
            b.vx = b.vy = 0
            return
        if not b.target or b.target not in self.alive_heroes() or random.random() < 0.01:
            b.target = self.pick_target(b, now)
        t = b.target
        if not t:
            b.vx = b.vy = 0
            return
        if now >= b.until and b.queue:   # a signature move it owes comes before anything else
            mid = b.queue.pop(0)
            if mid in b.d["moves"]:
                self.start_move(b, mid, b.d["moves"][mid], now)
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
                       round(b.poise), b.mpoise, b.phase, "tired" if b.state == "idle" and now < b.tired_until else b.state, [round(c) for c in b.cores],
                       # each status: how full its meter is (%), and whether it's in force (burst lately; rot still eating)
                       [min(100, round(100 * b.meter[k] / (100 * 1.4 ** b.procs[k]))) for k in STATUSES],
                       [1 if now - b.marked[k] < STATUS_LIVE or (k == "rot" and b.rot_until > now) else 0 for k in STATUSES],
                       # its break bar, percent left, while the move's window for it is open
                       max(1, round(100 * b.move.brk / b.move.brk0)) if b.move and b.move.brk > 0 and b.move.window("brk_win", now) else 0]
                      for b in self.bodies],
                "a": [[a["id"], a["kind"], round(a["x"], 1), round(a["y"], 1), round(a["hp"]), round(a["mhp"])] for a in self.adds.values()],
                "h": [[f.hero.id, round(f.x, 1), round(f.y, 1), round(f.face, 2), f.anim, round(f.at, 2), f.hero.hp, f.hero.mhp(),
                       f.hero.flasks, 1 if f.down else (2 if f.dead else 0),
                       round(max(0, f.bleed - now), 1) if f.down and f.bleed else 0, 1 if f.heal_at else 0,
                       # what's on them: ward left, seconds of extra damage left, a charged next hit
                       -1 if now < f.guard_until else round(f.shield),
                       round(max([f.vengeance[1] - now if f.vengeance[0] > 1 else 0.0]
                                 + [min(99.0, z["until"] - now) for z in self.zones if z.get("rally") and math.hypot(z["x"] - f.x, z["y"] - f.y) <= z["r"]] + [0.0]), 1),
                       1 if f.empowered and now < f.empowered[1] else 0]
                      for f in self.heroes.values()]}

    def start_wire(self):
        return {"t": "fight", "boss": self.boss["id"], "arena": self.boss["arena"], "size": [self.arena["w"], self.arena["h"]],
                "pad": self.arena["pad"], "intro": INTRO, "started": round(self.started, 3),
                "bodies": [{"mhp": b.mhp, "mpoise": b.mpoise, "x": round(b.x), "y": round(b.y), "art": b.art} for b in self.bodies],
                "heroes": {f.hero.id: [round(f.x), round(f.y)] for f in self.heroes.values()}}


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


# ---------------------------------------------------------------------- where a signature cast puts its spots
# Each returns [(x, y, r, tag, on)]: the safe ground or cover of that cast (a move's "spots" names one).

def _stones(f, b, t, data, now):
    return [(x, y, 32, 0, 1) for x, y in f.spread(3, 32, 150)]


def _bells(f, b, t, data, now):
    return [(x, y, 15, 0, 1) for x, y in f.spread(2 if b.phase < 2 else 1, 30, 90, (b.x, b.y), 95, 150)]


def _flasks(f, b, t, data, now):
    return [(x, y, 36, i, 1) for i, (x, y) in enumerate(f.spread(3, 36, 110, (t.x, t.y) if t else None, 40, 200))]


def _candles(f, b, t, data, now):
    pts = f.spread(3, 44, 170)
    for i, (x, y) in enumerate(pts): f.spawn_at(b, "candle", x, y, now, data["dur"], (f.seq, i))
    return [(x, y, 46, 0, 0) for x, y in pts]


def _rubble(f, b, t, data, now):
    return [(x, y, 17, 0, 1) for x, y in f.spread(3, 30, 100, (b.x, b.y), 100, 180)]


def _lights(f, b, t, data, now):
    out, at = [], (t.x, t.y) if t else (b.x, b.y)
    for i in range(3):
        at = f.spread(1, 60, 0, at, 30 if i == 0 else 90, 110 if i == 0 else 150)[0]
        out.append((at[0], at[1], 60, i, 1))
    return out


def _trinity(f, b, t, data, now):
    a, cx, cy = random.uniform(0, 2 * math.pi), f.arena["w"] / 2, f.arena["h"] / 2 + 15
    return [(cx + math.cos(a + k * 2.094) * 150, cy + math.sin(a + k * 2.094) * 110, 20, 0 if k == 0 else 1, 1) for k in range(3)]


def _fist(f, b, t, data, now):
    a = math.atan2(t.y - b.y, t.x - b.x) if t else b.face
    x, y = f.clamp(b.x + math.cos(a) * 120, b.y + math.sin(a) * 120)
    return [(x, y, 18, 0, 1)]


SPOTS = {"stones": _stones, "bells": _bells, "flasks": _flasks, "candles": _candles, "rubble": _rubble, "lights": _lights,
         "trinity": _trinity, "fist": _fist}
