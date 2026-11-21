"""Overlords' fight: two boards on one hex battlefield, simulated to the end in one go.

The server runs a whole fight the moment the fight phase starts (a few milliseconds) and sends the
browsers its timeline of events, which they play back in step with the server's clock. So fights
are deterministic for a seed, anyone can watch any fight, and the balance tools can run thousands.

The battlefield is COLS x ROWS pointy-top hexes in "odd-r" offset coordinates (odd rows sit half a
hex to the right). Each player's own board is COLS x 4 with row 3 at the front; the home board
keeps its coordinates and the away board is turned round (`to_grid`), so the two front rows meet in
the middle.

Each tick (DT) every living unit, in a fixed shuffled order, casts if its mana is full, attacks its
target if it's in range and its attack is ready, or else steps one hex along the shortest free path
towards a hex in range. A unit that has just moved or cast is `busy` until it's done, and gains no mana for MANA_LOCK
after a cast. From OVERTIME every hit grows, so fights end before TIME_CAP.

Events, each a list starting [kind, time]:
    m  [m, t, id, col, row]                     moved one hex (arrives MOVE_TIME later)
    j  [j, t, id, col, row]                     jumped (dash, leap)
    a  [a, t, id, target id]                    attacked
    x  [x, t, id]                               dodged an attack
    d  [d, t, source id, id, amount, type, crit, hp left]
                                                took damage (type 0 phys, 1 magic, 2 true, 3 burn);
                                                shields soak it before hp, so hp left may not drop;
                                                burning is told in lumps (BURN_LUMP), not every tick
    c  [c, t, id, target id or 0]               cast its ability
    h  [h, t, id, amount, healer id]            healed
    s  [s, t, id, amount, secs, caster id]      shielded
    st [st, t, id, secs]                        stunned
    sp [sp, t, unit row]                        summoned (a unit row like the start's)
    r  [r, t, id, hp]                           rose again (Gravebound)
    k  [k, t, id]                               died
    v  [v, t, [[id, hp, mana, shield]...]]      every unit's numbers, every SNAP seconds
"""

import random

from . import data as D

COLS, ROWS = 7, 8
DT = 0.05
TIME_CAP = 30.0
MOVE_TIME = 0.45
CAST_LOCK = 0.4
SNAP = 0.5
MANA_PER_ATTACK = 10
MANA_FROM_HURT = 0.04  # of damage taken after armor
MANA_HURT_MAX = 8
MANA_LOCK = 1.0  # seconds after a cast in which a unit gains no mana
OVERTIME = 18.0  # from here every hit does OVERTIME_RAMP more for each second past it
OVERTIME_RAMP = 0.25
BURN_SECS = 3.0
SLOW_SECS = 3.0
CHILL_SECS = 2.0
TRAIT_SHIELD_SECS = 10.0
MAX_ASPD = 3.0
DUEL_STACKS = 8
FRENZY_STACKS = 10
SHRED_SECS = 3.0
BURN_LUMP = 20  # burn damage is told in events of about this much
TYPES = {"phys": 0, "magic": 1, "true": 2, "burn": 3}

DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def axial(h):
    c, r = h
    return c - (r - (r & 1)) // 2, r


def offset(q, r):
    return q + (r - (r & 1)) // 2, r


def dist(a, b):
    aq, ar = axial(a)
    bq, br = axial(b)
    dq, dr = aq - bq, ar - br
    return max(abs(dq), abs(dr), abs(dq + dr))


def on_board(h):
    return 0 <= h[0] < COLS and 0 <= h[1] < ROWS


def neighbours(h):
    q, r = axial(h)
    for dq, dr in DIRS:
        n = offset(q + dq, r + dr)
        if on_board(n):
            yield n


def to_grid(side, col, row):
    return (col, row) if side == 0 else (COLS - 1 - col, ROWS - 1 - row)


def line_hexes(a, b, length):
    """`length` hexes from a (not included) in the direction of b."""
    aq, ar = axial(a)
    bq, br = axial(b)
    dq, dr = bq - aq, br - ar
    n = max(abs(dq), abs(dr), abs(dq + dr)) or 1
    out = []
    for i in range(1, length + 1):
        fq, fr = aq + dq * i / n, ar + dr * i / n
        fs = -fq - fr
        q, r, s = round(fq), round(fr), round(fs)
        if abs(q - fq) > abs(r - fr) and abs(q - fq) > abs(s - fs):
            q = -r - s
        elif abs(r - fr) > abs(s - fs):
            r = -q - s
        h = offset(q, r)
        if on_board(h):
            out.append(h)
    return out


def at_star(v, star):
    return v[star - 1] if isinstance(v, list) else v


class Unit:
    def __init__(self, uid, side, key, star, hex_):
        u = D.UNITS[key]
        m = D.STAR_MULT[star - 1]
        self.id, self.side, self.key, self.star, self.hex = uid, side, key, star, hex_
        self.max = u["hp"] * m
        self.hp = self.max
        self.ad = u["ad"] * m
        self.base_as = u["as"]
        self.range = u["range"]
        self.armor = u["armor"]
        self.mr = u["mr"]
        self.maxmana = u["mana"]
        self.mana = u["start"]
        self.ability = u["ability"]
        self.traits = u["traits"]
        self.summon = bool(u.get("summon"))
        self.static = bool(u.get("static"))  # never moves (turrets)
        self.ap = 100.0
        self.crit = 0.25
        self.critdmg = 1.4
        self.dodge = 0.0
        self.aspd_pct = 0.0
        self.shields = []  # [amount, until]
        self.stun = 0.0
        self.busy = 0.0
        self.next_atk = 0.0
        self.target = None
        self.alive = True
        self.burn = (0.0, 0.0, None)  # (damage per second, until, source)
        self.slow = (0.0, 0.0)  # (fraction of attack speed lost, until)
        self.buffs = []  # [stat, amount, until]
        self.revive = 0.0
        self.regen = 0.0
        self.mana_regen = 0.0
        self.burns = 0.0  # Emberforged: attacks set burning
        self.chills = 0.0  # Mirefolk: attackers are chilled
        self.duel = 0.0
        self.stacks = 0
        self.double = 0.0
        self.leap = False
        self.summon_boost = 0.0
        self.dmg_done = 0.0
        self.mana_lock = 0.0
        self.items = []
        self.own_row = 0  # the row on its owner's board (3 = the front)
        # items
        self.frenzy = 0.0  # attack speed per attack, up to FRENZY_STACKS
        self.fstacks = 0
        self.ability_crit = False
        self.mana_on_hit = 0.0
        self.shred = 0.0  # armor its attacks strip, and (as a target) what's been stripped from it
        self.shred_amt = 0.0
        self.shred_until = 0.0
        self.omnivamp = 0.0
        self.splash = 0.0
        self.on_hit_magic = 0.0
        self.chill_on_hit = 0.0
        self.pct_hit = 0.0
        self.cast_mana = 0.0
        self.aura = 0.0
        self.cast_heal = 0.0
        self.team_mana = 0.0
        self.low_heal = 0.0
        self.low_used = False
        self.dr = 0.0
        self.thorns = 0.0
        self.cc_immune = False
        self.burn_told = {}  # source id -> burn damage not yet in an event

    def row(self):
        """What the browsers are told about a unit at the start or when it's summoned."""
        return [self.id, self.side, self.key, self.star, self.hex[0], self.hex[1], round(self.max),
                self.maxmana, round(self.mana), self.items]

    def shield(self, now):
        return sum(a for a, until in self.shields if until > now)

    def stat(self, name, now):
        v = getattr(self, name) + sum(a for s, a, until in self.buffs if s == name and until > now)
        if name == "armor" and self.shred_until > now:
            v -= self.shred_amt
        return v

    def attack_speed(self, now):
        pct = self.stat("aspd_pct", now) + self.duel * self.stacks + self.frenzy * self.fstacks
        slow = self.slow[0] if self.slow[1] > now else 0.0
        return min(MAX_ASPD, self.base_as * (1 + pct) * (1 - slow))


class Fight:
    def __init__(self, home, away, seed=0, extras=None):
        """home and away: lists of {"unit", "star", "col", "row", "items"} in each player's own
        coordinates. `extras`, one dict a side, is what commanders and augments add: `bonus` ({trait:
        n} on top of the board's counts), `team` (fx for every unit), `front` (fx for the front row),
        `revive_first` (the first unit to die rises with that share of HP), `summon` ([key, star], a
        unit that starts on the side's half), `rally` ([attack speed, seconds] for everyone at the
        start)."""
        self.rng = random.Random(seed)
        self.t = 0.0
        self.units: list[Unit] = []
        self.occ = {}
        self.events = []
        self.next_id = 1
        extras = extras or ({}, {})
        for side, board in ((0, home), (1, away)):
            for b in board:
                h = to_grid(side, b["col"], b["row"])
                if h in self.occ or b["unit"] not in D.UNITS:
                    continue
                u = self.add(side, b["unit"], b.get("star", 1), h)
                u.items = [i for i in b.get("items", ()) if i in D.ITEMS][:D.MAX_ITEMS]
                u.traits = D.unit_traits(u.key, u.items)
                u.own_row = b["row"]
        self.traits = [D.trait_counts([(u.key, u.items) for u in self.units if u.side == s and not u.summon],
                                      extras[s].get("bonus")) for s in (0, 1)]
        for side in (0, 1):
            self.apply_traits(side)
        for u in self.units:
            for i in u.items:
                self.give(u, D.ITEMS[i]["fx"])
        self.first_revive = [0.0, 0.0]
        for side in (0, 1):
            ex = extras[side]
            for u in [u for u in self.units if u.side == side]:
                if ex.get("team"):
                    self.give(u, ex["team"])
                if ex.get("front") and u.own_row == 3:
                    self.give(u, ex["front"])
                if ex.get("rally"):
                    u.buffs.append(["aspd_pct", ex["rally"][0], ex["rally"][1]])
            self.first_revive[side] = ex.get("revive_first", 0.0)
            if ex.get("summon"):
                key, star = ex["summon"]
                spots = [to_grid(side, c, r) for r in (3, 2, 1, 0) for c in (3, 2, 4, 1, 5, 0, 6)]
                spot = next((h for h in spots if h not in self.occ), None)
                if spot and key in D.UNITS:
                    s = self.add(side, key, star, spot)
                    if ex.get("team", {}).get("summon_boost"):
                        s.max *= 1 + ex["team"]["summon_boost"]
                        s.hp = s.max
                        s.ad *= 1 + ex["team"]["summon_boost"]
        for u in self.units:
            if u.team_mana:
                for f in self.units:
                    if f.side == u.side and f is not u and f.ability and dist(f.hex, u.hex) <= 1:
                        f.mana = min(f.maxmana, f.mana + u.team_mana)
        self.rng.shuffle(self.units)
        for u in self.units:
            u.next_atk = 0.2 + 0.3 * self.rng.random()
        self.start = [u.row() for u in sorted(self.units, key=lambda u: u.id)]  # [id, side, key, star, col, row, max hp, max mana, mana, items]
        for u in list(self.units):
            if u.leap:
                self.do_leap(u)
        self.since_snap = SNAP

    # ------------------------------------------------------------ setting up

    def add(self, side, key, star, h):
        u = Unit(self.next_id, side, key, star, h)
        self.next_id += 1
        self.units.append(u)
        self.occ[h] = u
        return u

    def apply_traits(self, side):
        for trait, count in self.traits[side].items():
            level = D.trait_level(trait, count)
            if level < 0:
                continue
            fx = D.TRAITS[trait]["fx"][level]
            team = fx.get("who") == "team"
            for u in self.units:
                if u.side == side and (team or trait in u.traits):
                    self.give(u, fx)

    def give(self, u, fx):
        for k, v in fx.items():
            if k == "who":
                continue
            if k == "hp_pct":
                u.max *= 1 + v
                u.hp = u.max
            elif k == "ad_pct":
                u.ad *= 1 + v
            elif k == "mana_cut":
                u.maxmana = round(u.maxmana * (1 - v))
            elif k in ("armor", "mr", "ap", "dodge", "crit", "critdmg", "aspd_pct", "mana_on_hit", "omnivamp",
                       "splash", "on_hit_magic", "pct_hit", "aura", "cast_heal", "team_mana", "low_heal", "thorns"):
                setattr(u, k, getattr(u, k) + v)
            elif k == "ad":
                u.ad += v
            elif k == "hp":
                u.max += v
                u.hp = u.max
            elif k == "mana":
                if u.ability:
                    u.mana = min(u.maxmana, u.mana + v)
            elif k in ("frenzy", "shred", "chill_on_hit", "cast_mana"):
                setattr(u, k, max(getattr(u, k), v))
            elif k == "dr":
                u.dr = 1 - (1 - u.dr) * (1 - v)
            elif k == "ability_crit":
                u.ability_crit = True
            elif k == "cc_immune":
                u.cc_immune = True
            elif k == "burn":
                u.burns = max(u.burns, v)
            elif k == "regen":
                u.regen += v
            elif k == "mana_regen":
                u.mana_regen += v
            elif k == "revive":
                u.revive = max(u.revive, v)
            elif k == "chill":
                u.chills = max(u.chills, v)
            elif k == "shield":
                u.shields.append([v, TRAIT_SHIELD_SECS])
            elif k == "duel":
                u.duel = max(u.duel, v)
            elif k == "double":
                u.double = max(u.double, v)
            elif k == "leap":
                u.leap = True
            elif k == "summon_boost":
                u.summon_boost += v

    def do_leap(self, u):
        foes = [f for f in self.units if f.alive and f.side != u.side]
        if not foes:
            return
        far = max(foes, key=lambda f: (dist(u.hex, f.hex), -f.id))
        spot = self.free_near(far.hex)
        if spot:
            self.jump(u, spot)
            u.target = far

    # ------------------------------------------------------------ helpers

    def ev(self, *e):
        self.events.append([e[0], round(self.t, 2), *e[1:]])

    def alive(self, side):
        return [u for u in self.units if u.alive and u.side == side]

    def foes(self, u):
        return [f for f in self.units if f.alive and f.side != u.side]

    def friends(self, u):
        return [f for f in self.units if f.alive and f.side == u.side]

    def nearest(self, u, among):
        return min(among, key=lambda f: (dist(u.hex, f.hex), f.id), default=None)

    def free_near(self, h):
        """A free hex next to h, else the nearest free hex."""
        free = [n for n in neighbours(h) if n not in self.occ]
        if free:
            return self.rng.choice(sorted(free))
        rest = [(c, r) for c in range(COLS) for r in range(ROWS) if (c, r) not in self.occ]
        return min(rest, key=lambda n: (dist(n, h), n), default=None)

    def jump(self, u, h):
        del self.occ[u.hex]
        u.hex = h
        self.occ[h] = u
        self.ev("j", u.id, h[0], h[1])

    def path_step(self, u, target):
        """The first hex of the shortest free path to a hex within range of target, or None."""
        start = u.hex
        if dist(start, target.hex) <= u.range:
            return None
        prev = {start: None}
        frontier = [start]
        while frontier:
            nxt = []
            for h in frontier:
                for n in neighbours(h):
                    if n in prev or n in self.occ:
                        continue
                    prev[n] = h
                    if dist(n, target.hex) <= u.range:
                        while prev[n] != start:
                            n = prev[n]
                        return n
                    nxt.append(n)
            frontier = nxt
        return None

    # ------------------------------------------------------------ the fight

    def run(self):
        while self.t < TIME_CAP and self.alive(0) and self.alive(1):
            self.tick()
            self.t += DT
        self.snap()
        left = [self.alive(0), self.alive(1)]
        winner = 0 if left[0] and not left[1] else 1 if left[1] and not left[0] else None
        return {
            "winner": winner,
            "time": round(self.t, 2),
            "start": self.start,
            "events": self.events,
            "traits": self.traits,
            "survivors": [[[u.key, u.star] for u in side if not u.summon] for side in left],
            "dmg": {u.id: round(u.dmg_done) for u in self.units},
        }

    def tick(self):
        now = self.t
        self.since_snap += DT
        if self.since_snap >= SNAP:
            self.since_snap = 0.0
            self.snap()
        for u in list(self.units):
            if not u.alive:
                continue
            dps, until, src = u.burn
            if until > now and dps:
                self.deal(src, u, dps * DT, "burn")
                if not u.alive:
                    continue
            if u.aura:
                for f in self.foes(u):
                    if dist(f.hex, u.hex) <= 1:
                        self.deal(u, f, f.max * u.aura * DT, "burn")
            if u.regen and u.hp < u.max:
                u.hp = min(u.max, u.hp + u.max * u.regen * DT)
            if u.mana_regen and u.ability and now >= u.mana_lock:
                u.mana += u.mana_regen * DT
            if now < u.stun or now < u.busy:
                continue
            if u.ability and u.mana >= u.maxmana:
                self.cast(u)
                continue
            foes = self.foes(u)
            if not foes:
                return
            t = u.target
            if t is None or not t.alive or dist(u.hex, t.hex) > u.range:
                t = u.target = self.nearest(u, foes)
            if dist(u.hex, t.hex) <= u.range:
                if now >= u.next_atk:
                    self.attack(u, t)
                    u.next_atk = now + 1 / u.attack_speed(now)
                continue
            if u.static:
                continue
            step = None
            for f in sorted(foes, key=lambda f: (dist(u.hex, f.hex), f.id)):
                step = self.path_step(u, f)
                if step:
                    u.target = f
                    break
            if step:
                del self.occ[u.hex]
                u.hex = step
                self.occ[step] = u
                u.busy = now + MOVE_TIME
                u.next_atk = max(u.next_atk, u.busy)
                self.ev("m", u.id, step[0], step[1])

    def snap(self):
        now = self.t
        self.ev("v", [[u.id, round(u.hp), round(u.mana), round(u.shield(now))] for u in self.units if u.alive])

    def attack(self, u, t):
        self.ev("a", u.id, t.id)
        if u.ability and self.t >= u.mana_lock:
            u.mana = min(u.maxmana, u.mana + MANA_PER_ATTACK + u.mana_on_hit)
        if u.duel:
            u.stacks = min(DUEL_STACKS, u.stacks + 1)
        if u.frenzy:
            u.fstacks = min(FRENZY_STACKS, u.fstacks + 1)
        hits = 2 if u.double and self.rng.random() < u.double else 1
        for _ in range(hits):
            if not t.alive:
                break
            dodge = t.stat("dodge", self.t)
            if dodge and self.rng.random() < dodge:
                self.ev("x", t.id)
                continue
            crit = self.rng.random() < u.crit
            dmg = u.stat("ad", self.t) * (u.critdmg if crit else 1)
            dealt = self.deal(u, t, dmg, "phys", crit)
            if u.splash:
                for f in self.foes(u):
                    if f is not t and dist(f.hex, t.hex) <= 1:
                        self.deal(u, f, dmg * u.splash, "phys")
            if t.alive and u.pct_hit:
                self.deal(u, t, t.max * u.pct_hit, "phys")
            if t.alive and u.on_hit_magic:
                self.deal(u, t, u.on_hit_magic, "magic")
            if t.alive and u.shred:
                t.shred_amt = max(u.shred, t.shred_amt if t.shred_until > self.t else 0)
                t.shred_until = self.t + SHRED_SECS
            if t.alive and u.chill_on_hit:
                t.slow = (max(u.chill_on_hit, t.slow[0] if t.slow[1] > self.t else 0), self.t + CHILL_SECS)
            if t.thorns and dealt and u.alive:
                self.deal(t, u, dealt * t.thorns, "magic")
            if u.burns and t.alive:
                t.burn = (t.max * u.burns, self.t + BURN_SECS, u)
        if t.chills:
            u.slow = (max(t.chills, u.slow[0] if u.slow[1] > self.t else 0), self.t + CHILL_SECS)

    def deal(self, src, dst, amount, kind, crit=False):
        if not dst.alive or amount <= 0:
            return 0
        now = self.t
        if dst.dr:
            amount *= 1 - dst.dr
        if kind == "phys":
            amount *= 100 / (100 + max(0, dst.stat("armor", now)))
        elif kind == "magic":
            amount *= 100 / (100 + max(0, dst.stat("mr", now)))
        if now > OVERTIME:
            amount *= 1 + OVERTIME_RAMP * (now - OVERTIME)
        rest = amount
        for sh in dst.shields:
            if sh[1] > now and rest > 0:
                take = min(sh[0], rest)
                sh[0] -= take
                rest -= take
        dst.shields = [sh for sh in dst.shields if sh[0] > 0 and sh[1] > now]
        dst.hp -= rest
        if kind == "burn":  # burning ticks every DT: told in lumps of BURN_LUMP per source, or when it dies
            key = src.id if src else 0
            dst.burn_told[key] = dst.burn_told.get(key, 0.0) + amount
            if dst.burn_told[key] >= BURN_LUMP or dst.hp <= 0:
                self.ev("d", key, dst.id, round(dst.burn_told.pop(key)), 3, 0, max(0, round(dst.hp)))
        else:
            self.ev("d", src.id if src else 0, dst.id, round(amount), TYPES[kind], int(crit), max(0, round(dst.hp)))
        if dst.ability and kind != "burn" and now >= dst.mana_lock:
            dst.mana = min(dst.maxmana, dst.mana + min(MANA_HURT_MAX, amount * MANA_FROM_HURT))
        if src is not None:
            src.dmg_done += amount
            if src.omnivamp and src.alive:
                src.hp = min(src.max, src.hp + amount * src.omnivamp)
        if dst.hp <= 0:
            self.die(dst)
        elif dst.low_heal and not dst.low_used and dst.hp < dst.max / 2:
            dst.low_used = True
            for f in self.friends(dst):
                if dist(f.hex, dst.hex) <= 2:
                    gain = min(dst.low_heal, f.max - f.hp)
                    f.hp += gain
                    self.ev("h", f.id, round(gain), dst.id)
        return amount

    def die(self, u):
        if not u.revive and not u.summon and self.first_revive[u.side]:
            u.revive = self.first_revive[u.side]
            self.first_revive[u.side] = 0.0
        if u.revive:
            u.hp = u.max * u.revive
            u.revive = 0.0
            u.burn = (0.0, 0.0, None)
            u.stun = self.t + 1.0
            self.ev("r", u.id, round(u.hp))
            return
        u.alive = False
        u.hp = 0
        del self.occ[u.hex]
        self.ev("k", u.id)

    # ------------------------------------------------------------ abilities

    def cast(self, u):
        foes = self.foes(u)
        t = u.target if u.target is not None and u.target.alive else self.nearest(u, foes)
        u.target = t
        u.mana = 0.0
        self.ev("c", u.id, t.id if t else 0)
        u.cast_crit = u.critdmg if u.ability_crit and self.rng.random() < u.crit else 1.0
        for step in u.ability["steps"]:
            getattr(self, "step_" + step["do"])(u, step)
        if u.cast_heal:
            f = min(self.friends(u), key=lambda f: (f.hp / f.max, f.id))
            gain = min(u.cast_heal * u.ap / 100, f.max - f.hp)
            f.hp += gain
            self.ev("h", f.id, round(gain), u.id)
        u.busy = self.t + CAST_LOCK
        u.mana_lock = self.t + MANA_LOCK
        if u.cast_mana:
            u.mana = u.cast_mana
        u.next_atk = max(u.next_atk, u.busy)

    def select(self, u, sel):
        name, _, n = sel.partition(":")
        n = int(n) if n else 0
        t = u.target if u.target is not None and u.target.alive else None
        foes = self.foes(u)
        if name == "target":
            return [t] if t else []
        if name == "self":
            return [u]
        if name == "around_target":
            return [f for f in foes if dist(f.hex, t.hex) <= n] if t else []
        if name == "around_self":
            return [f for f in foes if dist(f.hex, u.hex) <= n]
        if name == "line":
            if not t:
                return []
            hexes = set(line_hexes(u.hex, t.hex, n))
            return [f for f in foes if f.hex in hexes]
        if name == "nearest":
            return sorted(foes, key=lambda f: (dist(u.hex, f.hex), f.id))[:n]
        if name == "farthest":
            return [max(foes, key=lambda f: (dist(u.hex, f.hex), -f.id))] if foes else []
        if name == "random":
            return self.rng.sample(foes, min(n, len(foes)))
        if name == "chain":
            if not t:
                return []
            hit = [t]
            while len(hit) < n:
                left = [f for f in foes if f not in hit and dist(f.hex, hit[-1].hex) <= 3]
                if not left:
                    break
                hit.append(min(left, key=lambda f: (dist(f.hex, hit[-1].hex), f.id)))
            return hit
        if name == "lowest_enemy":
            return [min(foes, key=lambda f: (f.hp / f.max, f.id))] if foes else []
        friends = self.friends(u)
        if name == "lowest_ally":
            return [min(friends, key=lambda f: (f.hp / f.max, f.id))]
        if name == "allies_near":
            return [f for f in friends if dist(f.hex, u.hex) <= n]
        if name == "allies":
            return friends
        if name == "enemies":
            return foes
        raise ValueError(sel)

    def step_hit(self, u, st):
        kind = st.get("type", "magic")
        amount = at_star(st["dmg"], u.star) * u.ap / 100 * getattr(u, "cast_crit", 1.0)
        drained = 0.0
        for f in self.select(u, st["to"]):
            drained += self.deal(u, f, amount, kind)
            if not f.alive:
                continue
            if "stun" in st and not f.cc_immune:
                secs = at_star(st["stun"], u.star)
                f.stun = max(f.stun, self.t + secs)
                self.ev("st", f.id, secs)
            if "slow" in st:
                f.slow = (at_star(st["slow"], u.star), self.t + SLOW_SECS)
            if "burn" in st:
                f.burn = (f.max * at_star(st["burn"], u.star), self.t + BURN_SECS, u)
        if "heal_frac" in st and drained and u.alive:
            gain = min(drained * at_star(st["heal_frac"], u.star), u.max - u.hp)
            u.hp += gain
            self.ev("h", u.id, round(gain), u.id)

    def step_heal(self, u, st):
        amount = at_star(st["amt"], u.star) * u.ap / 100
        for f in self.select(u, st["to"]):
            gain = min(amount, f.max - f.hp)
            f.hp += gain
            self.ev("h", f.id, round(gain), u.id)

    def step_shield(self, u, st):
        amount = at_star(st["amt"], u.star) * u.ap / 100
        secs = at_star(st["secs"], u.star)
        for f in self.select(u, st["to"]):
            f.shields.append([amount, self.t + secs])
            self.ev("s", f.id, round(amount), secs, u.id)

    def step_buff(self, u, st):
        amount = at_star(st["amt"], u.star)
        for f in self.select(u, st["to"]):
            f.buffs.append([st["stat"], amount, self.t + at_star(st["secs"], u.star)])

    def step_summon(self, u, st):
        for _ in range(at_star(st.get("count", 1), u.star)):
            h = self.free_near(u.hex)
            if h is None:
                return
            s = self.add(u.side, st["unit"], u.star, h)
            if u.summon_boost:
                s.max *= 1 + u.summon_boost
                s.hp = s.max
                s.ad *= 1 + u.summon_boost
            s.next_atk = self.t + 0.5
            self.ev("sp", s.row())

    def step_mana(self, u, st):
        amount = at_star(st["amt"], u.star)
        for f in self.select(u, st["to"]):
            if f is not u and f.ability:
                f.mana = min(f.maxmana, f.mana + amount)

    def step_dash(self, u, st):
        picked = self.select(u, st["to"])
        if not picked:
            return
        spot = self.free_near(picked[0].hex)
        if spot:
            self.jump(u, spot)
        u.target = picked[0]


def fight(home, away, seed=0):
    return Fight(home, away, seed).run()
