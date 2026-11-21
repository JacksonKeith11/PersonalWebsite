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
    b  [b, t, id, kind, secs]                   a status: vanish (untargetable), taunt (by id, at
                                                the start: [b, t, taunter, 'taunt', secs]),
                                                mark (takes more damage), wound (heals less),
                                                devour (swallowed: hidden), grow, cleanse, parry,
                                                zap (an item's lightning: damage follows at once),
                                                burst (bursting on death: likewise)
    z  [z, t, side, col, row, r, secs, kind, caster id]
                                                an area on the ground: kind 'zone' (an ability's
                                                lingering area, of `side`'s caster) or 'warn'
                                                (where a delayed blow will land)
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
MARK_SECS = 3.0  # mark_on_hit (an extra ability)
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
        self.raw = (self.max, u["armor"], u["mr"])  # its own numbers, for conversions (Fight.convert)
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
        # statuses from the roster review
        self.hidden_until = 0.0  # untargetable (vanished, or swallowed)
        self.taunt = (None, 0.0)  # (unit it must attack, until)
        self.amp = (0.0, 0.0)  # (more damage taken, until)
        self.wound_until = 0.0  # heals half as much until
        self.mana_slow = (0.0, 0.0)  # (share of mana gain lost, until)
        # passives (units' own, items and artifacts)
        self.multishot = 0.0
        self.death_burst = 0.0
        self.guard_aura = 0.0
        self.taunt_start = 0.0
        self.every3 = 0.0
        self.attacks = 0
        self.on_kill = None  # [attack speed, heal share]
        self.kill_aspd = 0.0
        self.execute = 0.0
        self.wound_on_hit = 0.0
        self.grow_hp = None  # [share of max hp a second, cap]
        self.grown = 0.0
        self.base_max = 0.0
        self.echo = 0.0
        self.spell_dr = 0.0
        self.last_stand = None  # [below this share, seconds hidden, heal share]
        self.summon_every = None  # [unit, seconds]
        self.next_summon = 0.0
        self.low_bonus = 0.0
        self.cast_grow_ap = 0.0
        self.cast_share = 0.0
        self.horn = None  # [attack speed, seconds, radius]
        self.echo_first = 0.0  # the Archmage: the first cast echoes at this strength
        # extra abilities (picked at 2 and 3 stars)
        self.talents = []
        self.cast_power = 0.0  # its ability is this much stronger
        self.cast_burn = 0.0  # its ability burns what it hits (share of max hp a second)
        self.mark_on_hit = 0.0  # its attacks make the target take this much more damage for MARK_SECS

    def row(self):
        """What the browsers are told about a unit at the start or when it's summoned."""
        return [self.id, self.side, self.key, self.star, self.hex[0], self.hex[1], round(self.max),
                self.maxmana, round(self.mana), self.items, self.talents, self.stats()]

    def stats(self):
        """Its numbers as a fight starts, with traits, items, extra abilities and commanders counted, for
        the browsers' unit cards (buffs that run out are left out)."""
        return {"hp": round(self.max), "ad": round(self.ad), "as": round(min(MAX_ASPD, self.base_as * (1 + self.aspd_pct)), 2),
                "range": self.range, "armor": round(self.armor), "mr": round(self.mr), "mana": round(self.mana),
                "maxmana": self.maxmana, "ap": round(self.ap), "crit": round(self.crit, 2),
                "critdmg": round(self.critdmg, 2), "dodge": round(self.dodge, 2), "dr": round(self.dr, 2),
                "spell_dr": round(self.spell_dr, 2), "power": round(self.cast_power, 2), "regen": round(self.regen, 3)}

    def shield(self, now):
        return sum(a for a, until in self.shields if until > now)

    def stat(self, name, now):
        v = getattr(self, name) + sum(a for s, a, until in self.buffs if s == name and until > now)
        if name == "armor" and self.shred_until > now:
            v -= self.shred_amt
        return v

    def hidden(self, now):
        return self.hidden_until > now

    def attack_speed(self, now):
        pct = self.stat("aspd_pct", now) + self.duel * self.stacks + self.frenzy * self.fstacks + self.kill_aspd
        slow = self.slow[0] if self.slow[1] > now else 0.0
        return min(MAX_ASPD, self.base_as * (1 + pct) * (1 - slow))


class Fight:
    def __init__(self, home, away, seed=0, extras=None):
        """home and away: lists of {"unit", "star", "col", "row", "items"} in each player's own
        coordinates. `extras`, one dict a side, is what commanders and augments add: `bonus` ({trait:
        n} on top of the board's counts), `team` (fx for every unit), `front` (fx for the front row),
        `stars` ([[least star, fx]]: fx for units of at least that star), `convert` (see `convert`),
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
                u.talents = [t for t in b.get("talents", ()) if t in D.TALENTS][:len(D.TALENT_STARS)]
                u.own_row = b["row"]
        for u in self.units:
            passive = D.UNITS[u.key].get("passive")
            if passive:
                self.give(u, passive)
        self.traits = [D.trait_counts([(u.key, u.items) for u in self.units if u.side == s and not u.summon],
                                      extras[s].get("bonus")) for s in (0, 1)]
        for side in (0, 1):
            self.apply_traits(side)
        for u in self.units:
            for i in u.items:
                self.give(u, D.ITEMS[i]["fx"])
            for t in u.talents:
                self.give(u, D.TALENTS[t]["fx"])
        self.first_revive = [0.0, 0.0]
        self.fallen_rally = [extras[s].get("fallen_rally", 0.0) for s in (0, 1)]  # the Warlord
        for side in (0, 1):
            ex = extras[side]
            for u in [u for u in self.units if u.side == side]:
                if ex.get("team"):
                    self.give(u, ex["team"])
                if ex.get("front") and u.own_row == 3:
                    self.give(u, ex["front"])
                for least, fx in ex.get("stars", ()):
                    if u.star >= least:
                        self.give(u, fx)
                if ex.get("rally"):
                    u.buffs.append(["aspd_pct", ex["rally"][0], ex["rally"][1]])
            self.first_revive[side] = ex.get("revive_first", 0.0)
            foes = [u for u in self.units if u.side != side]
            if ex.get("hex_strongest") and foes:  # the Hexer: the enemy's best unit takes more all fight
                best = max(foes, key=lambda u: (u.star, D.UNITS[u.key]["cost"], len(u.items), -u.id))
                best.amp = (ex["hex_strongest"], TIME_CAP + 1)
            if ex.get("hex_all"):
                amt, secs = ex["hex_all"]
                for f in foes:
                    f.amp = (max(f.amp[0], amt), secs)
            if ex.get("drain"):  # the Chronomancer: the enemy starts dry and fills slowly
                share, secs = ex["drain"]
                for f in foes:
                    f.mana = 0.0
                    f.mana_slow = (share, secs)
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
        for side in (0, 1):
            if extras[side].get("convert"):
                for u in [u for u in self.units if u.side == side]:
                    self.convert(u, extras[side]["convert"])
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
        self.zones = []  # [side, centre, r, until, dmg a second, heal a second, slow, caster]
        self.later = []  # [time, caster, step]: delayed blows
        self.corpses = []  # hexes where units fell, for raising
        for u in sorted(self.units, key=lambda u: u.id):
            u.base_max = u.max
            if u.summon_every:
                u.next_summon = u.summon_every[1]
            if u.taunt_start:
                for f in self.units:
                    if f.side != u.side and dist(f.hex, u.hex) <= 3:
                        f.taunt = (u, u.taunt_start)
                self.ev("b", u.id, "taunt", u.taunt_start)
            if u.horn:
                amt, secs, r = u.horn
                for f in self.units:
                    if f.side == u.side and dist(f.hex, u.hex) <= r:
                        f.buffs.append(["aspd_pct", amt, secs])
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
            elif k in ("multishot", "death_burst", "guard_aura", "taunt_start", "every3", "execute", "wound_on_hit",
                       "echo", "low_bonus", "cast_share", "cast_burn", "mark_on_hit"):
                setattr(u, k, max(getattr(u, k), v))
            elif k == "echo_first":
                u.echo_first = max(u.echo_first, v)
            elif k in ("spell_dr", "cast_grow_ap", "cast_power"):
                setattr(u, k, getattr(u, k) + v)
            elif k in ("on_kill", "grow_hp", "last_stand", "summon_every", "horn"):
                setattr(u, k, list(v))

    def convert(self, u, conv):
        """Build-around augments that turn one stat into another, once everything else is counted:
        `hp_to_ad` [per, attack]: attack for every `per` max HP beyond the unit's own; `res_to_ap` share:
        ability power for armor and resist beyond its own; `aspd_to_mana` n: mana a second per 100% attack
        speed beyond its own."""
        raw_max, raw_armor, raw_mr = u.raw
        if "hp_to_ad" in conv:
            per, amt = conv["hp_to_ad"]
            u.ad += amt * (max(0.0, u.max - raw_max) // per)
        if "res_to_ap" in conv:
            u.ap += conv["res_to_ap"] * max(0.0, (u.armor - raw_armor) + (u.mr - raw_mr))
        if "aspd_to_mana" in conv and u.ability:
            u.mana_regen += conv["aspd_to_mana"] * max(0.0, u.aspd_pct)

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
        """The enemies u can target or hit: not vanished or swallowed."""
        return [f for f in self.units if f.alive and f.side != u.side and f.hidden_until <= self.t]

    def heal(self, f, amount, src):
        """Heals f (halved while wounded), tells it, and returns what it gained."""
        if not f.alive:
            return 0.0
        if f.wound_until > self.t:
            amount *= 0.5
        gain = max(0.0, min(amount, f.max - f.hp))
        f.hp += gain
        self.ev("h", f.id, round(gain), src.id if src else f.id)
        return gain

    def gain_mana(self, u, n):
        if not u.ability or self.t < u.mana_lock:
            return
        if u.mana_slow[1] > self.t:
            n *= 1 - u.mana_slow[0]
        u.mana = min(u.maxmana, u.mana + n)

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
            "fallen": [sum(1 for u in self.units if u.side == s and not u.summon and not u.alive) for s in (0, 1)],
            "dmg": {u.id: round(u.dmg_done) for u in self.units},
        }

    def tick(self):
        now = self.t
        self.since_snap += DT
        if self.since_snap >= SNAP:
            self.since_snap = 0.0
            self.snap()
        for blow in [b for b in self.later if b[0] <= now]:
            self.later.remove(blow)
            getattr(self, "step_" + blow[2]["do"])(blow[1], blow[2], blow[3])
        self.zones = [z for z in self.zones if z[3] > now]
        for side, centre, r, until, dmg, heal, slow, caster in self.zones:
            for f in [f for f in self.units if f.alive and dist(f.hex, centre) <= r]:
                if f.side != side and dmg:
                    self.deal(caster, f, dmg * caster.ap / 100 * DT, "burn", spell=True)
                    if slow and f.alive:
                        f.slow = (max(slow, f.slow[0] if f.slow[1] > now else 0), now + 0.5)
                elif f.side == side and heal and f.hp < f.max:
                    f.hp = min(f.max, f.hp + heal * caster.ap / 100 * DT * (0.5 if f.wound_until > now else 1))
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
                if not u.alive:  # a foe its aura burned down took it with them (a death burst)
                    continue
            regen = u.stat("regen", now)
            if regen and u.hp < u.max:
                u.hp = min(u.max, u.hp + u.max * regen * DT * (0.5 if u.wound_until > now else 1))
            if u.mana_regen:
                self.gain_mana(u, u.mana_regen * DT)
            if u.grow_hp and u.grown < u.grow_hp[1]:
                step = min(u.grow_hp[0] * DT, u.grow_hp[1] - u.grown)
                u.grown += step
                u.max += u.base_max * step
                u.hp += u.base_max * step
            if u.summon_every and now >= u.next_summon:
                u.next_summon = now + u.summon_every[1]
                self.step_summon(u, {"unit": u.summon_every[0]})
            if now < u.stun or now < u.busy:
                continue
            if u.ability and u.mana >= u.maxmana:
                self.cast(u)
                continue
            foes = self.foes(u)
            if not foes:
                continue
            t = u.target
            taunter, until = u.taunt
            if taunter is not None and until > now and taunter.alive and not taunter.hidden(now):
                t = u.target = taunter
            elif t is None or not t.alive or t.hidden(now) or dist(u.hex, t.hex) > u.range:
                t = u.target = self.nearest(u, foes)
            if dist(u.hex, t.hex) <= u.range:
                if now >= u.next_atk:
                    self.attack(u, t)
                    u.next_atk = now + 1 / u.attack_speed(now)
                continue
            if u.static:
                continue
            step = None
            for f in ([t] if t is u.taunt[0] else []) + sorted(foes, key=lambda f: (dist(u.hex, f.hex), f.id)):
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
        self.gain_mana(u, MANA_PER_ATTACK + u.mana_on_hit)
        u.attacks += 1
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
            if u.multishot:  # a second enemy near the target is struck too
                near = [f for f in self.foes(u) if f is not t and dist(f.hex, t.hex) <= 2]
                if near:
                    other = min(near, key=lambda f: (dist(f.hex, t.hex), f.id))
                    self.ev("a", u.id, other.id)
                    self.deal(u, other, dmg * u.multishot, "phys")
            if t.alive and u.execute and t.hp < t.max * u.execute:
                self.deal(u, t, t.hp + t.shield(self.t) + 1, "true")
            if t.alive and u.mark_on_hit:
                self.mark(t, u.mark_on_hit, MARK_SECS)
            if t.alive and u.wound_on_hit:
                t.wound_until = self.t + u.wound_on_hit
            if t.alive and u.pct_hit:
                self.deal(u, t, t.max * u.pct_hit, "phys")
            if t.alive and u.on_hit_magic:
                self.deal(u, t, u.on_hit_magic, "magic")
            if t.alive and u.shred:
                t.shred_amt = max(u.shred, t.shred_amt if t.shred_until > self.t else 0)
                t.shred_until = self.t + SHRED_SECS
            if t.alive and u.chill_on_hit:
                t.slow = (max(u.chill_on_hit, t.slow[0] if t.slow[1] > self.t else 0), self.t + CHILL_SECS)
            thorns = t.stat("thorns", self.t)
            if thorns and dealt and u.alive:
                self.deal(t, u, dealt * thorns, "magic")
            burns = u.stat("burns", self.t)
            if burns and t.alive:
                t.burn = (t.max * burns, self.t + BURN_SECS, u)
        if u.every3 and u.attacks % 3 == 0 and u.alive:  # every third attack: lightning through three
            self.ev("b", u.id, "zap", 0.3)
            hit = [t] if t.alive else []
            for f in sorted(self.foes(u), key=lambda f: (dist(f.hex, t.hex), f.id)):
                if len(hit) >= 3:
                    break
                if f not in hit:
                    hit.append(f)
            for f in hit:
                self.deal(u, f, u.every3, "magic")
        if t.chills:
            u.slow = (max(t.chills, u.slow[0] if u.slow[1] > self.t else 0), self.t + CHILL_SECS)

    def mark(self, f, amp, secs):
        """f takes `amp` more damage for `secs`, unless a stronger mark (or the Hexer's hex) is still on."""
        if f.amp[1] > self.t and f.amp[0] >= amp:
            return
        f.amp = (amp, max(f.amp[1], self.t + secs))

    def deal(self, src, dst, amount, kind, crit=False, spell=False):
        if not dst.alive or amount <= 0:
            return 0
        now = self.t
        if dst.dr:
            amount *= 1 - dst.dr
        if dst.amp[1] > now:
            amount *= 1 + dst.amp[0]
        if src is not None and src.low_bonus and dst.hp < dst.max / 2:
            amount *= 1 + src.low_bonus
        if spell and dst.spell_dr:
            amount *= max(0.2, 1 - dst.spell_dr)
        guard = max((g.guard_aura for g in self.units if g.guard_aura and g.alive and g is not dst
                     and g.side == dst.side and dist(g.hex, dst.hex) <= 1), default=0.0)
        if guard:
            amount *= 1 - guard
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
        if kind != "burn":
            self.gain_mana(dst, min(MANA_HURT_MAX, amount * MANA_FROM_HURT))
        if src is not None:
            src.dmg_done += amount
            if src.omnivamp and src.alive:
                src.hp = min(src.max, src.hp + amount * src.omnivamp * (0.5 if src.wound_until > now else 1))
        if dst.hp > 0 and dst.last_stand and dst.hp < dst.max * dst.last_stand[0]:
            below, secs, share = dst.last_stand  # once: out of reach for a moment, and some HP back
            dst.last_stand = None
            dst.hidden_until = now + secs
            self.ev("b", dst.id, "vanish", secs)
            self.heal(dst, dst.max * share, dst)
        if dst.hp <= 0:
            self.die(dst)
            if not dst.alive and src is not None and src.alive and src.on_kill:
                src.kill_aspd += src.on_kill[0]
                self.heal(src, src.max * src.on_kill[1], src)
        elif dst.low_heal and not dst.low_used and dst.hp < dst.max / 2:
            dst.low_used = True
            for f in self.friends(dst):
                if dist(f.hex, dst.hex) <= 2:
                    self.heal(f, dst.low_heal, dst)
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
        if not u.summon:
            self.corpses.append(u.hex)
        if self.fallen_rally[u.side] and u.own_row == 3 and not u.summon:  # a front-liner falls: the rest rally
            for f in self.friends(u):
                f.kill_aspd += self.fallen_rally[u.side]
        if u.death_burst:
            self.ev("b", u.id, "burst", 0.5)
            for f in [f for f in self.units if f.alive and f.side != u.side and dist(f.hex, u.hex) <= 1]:
                self.deal(u, f, u.death_burst, "magic", spell=True)

    # ------------------------------------------------------------ abilities

    def cast(self, u):
        foes = self.foes(u)
        t = u.target if u.target is not None and u.target.alive else self.nearest(u, foes)
        u.target = t
        u.mana = 0.0
        self.ev("c", u.id, t.id if t else 0)
        u.cast_crit = u.critdmg if u.ability_crit and self.rng.random() < u.crit else 1.0
        u.refund = False
        power = 1.0 + u.cast_power
        for step in u.ability["steps"]:
            self.run_step(u, step, power)
        echo = max(u.echo, u.echo_first)
        u.echo_first = 0.0
        if echo:  # the Echoing Tome, or the Archmage's first cast: the whole ability again, weaker
            for step in u.ability["steps"]:
                if step["do"] not in ("summon", "raise", "dash", "pull", "vanish", "devour"):
                    self.run_step(u, step, echo * power)
        if u.cast_heal and self.friends(u):
            f = min(self.friends(u), key=lambda f: (f.hp / f.max, f.id))
            self.heal(f, u.cast_heal * u.ap / 100, u)
        if u.cast_grow_ap:
            u.ap += u.cast_grow_ap
        if u.cast_share:
            for f in sorted([f for f in self.friends(u) if f is not u and f.ability],
                            key=lambda f: (dist(f.hex, u.hex), f.id))[:2]:
                f.mana = min(f.maxmana, f.mana + u.cast_share)
        u.busy = self.t + CAST_LOCK
        u.mana_lock = self.t + MANA_LOCK
        if u.cast_mana:
            u.mana = u.cast_mana
        if u.refund:  # a kill that refills it (Ghoul Reaver): ready to cast again once the lock is over
            u.mana = u.maxmana
        u.next_atk = max(u.next_atk, u.busy)

    def run_step(self, u, step, power):
        if step.get("delay"):  # it lands later: marked on the ground now
            t = u.target if u.target is not None and u.target.alive else None
            spot = self.cluster_centre(u, 1) if step["to"].startswith("cluster") else t.hex if t else None
            if spot:
                r = int(step["to"].partition(":")[2] or 0) if step["to"].startswith(("cluster", "around")) else 0
                self.ev("z", u.side, spot[0], spot[1], r, step["delay"], "warn", u.id)
            self.later.append([self.t + step["delay"], u, dict(step, delay=0, at=spot), power])
            return
        getattr(self, "step_" + step["do"])(u, step, power)

    def cluster_centre(self, u, r):
        """The enemy with the most enemies within r of it (ties: the nearest to u)."""
        foes = self.foes(u)
        if not foes:
            return None
        best = max(foes, key=lambda f: (sum(dist(g.hex, f.hex) <= r for g in foes), -dist(u.hex, f.hex), -f.id))
        return best.hex

    def select(self, u, sel, at=None):
        name, _, n = sel.partition(":")
        n = int(n) if n else 0
        t = u.target if u.target is not None and u.target.alive else None
        foes = self.foes(u)
        if name == "target":
            return [t] if t else []
        if name == "self":
            return [u]
        if name == "around_target":
            centre = at or (t.hex if t else None)
            return [f for f in foes if dist(f.hex, centre) <= n] if centre else []
        if name == "cluster":
            centre = at or self.cluster_centre(u, n)
            return [f for f in foes if dist(f.hex, centre) <= n] if centre else []
        if name == "highest_hp":
            return [max(foes, key=lambda f: (f.hp, -f.id))] if foes else []
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
            return [min(friends, key=lambda f: (f.hp / f.max, f.id))] if friends else []
        if name == "allies_near":
            return [f for f in friends if dist(f.hex, u.hex) <= n]
        if name == "nearest_allies":
            return sorted([f for f in friends if f is not u], key=lambda f: (dist(f.hex, u.hex), f.id))[:n]
        if name == "allies":
            return friends
        if name == "enemies":
            return foes
        raise ValueError(sel)

    def step_hit(self, u, st, power=1.0):
        kind = st.get("type", "magic")
        amount = at_star(st["dmg"], u.star) * u.ap / 100 * getattr(u, "cast_crit", 1.0) * power
        drained = 0.0
        for f in self.select(u, st["to"], st.get("at")):
            if not f.alive:
                continue
            dmg = amount * (1 + st.get("missing", 0) * (1 - f.hp / f.max))
            drained += self.deal(u, f, dmg, kind, spell=True)
            if not f.alive:
                if st.get("refund"):
                    u.refund = True
                continue
            if st.get("execute") and f.hp < f.max * at_star(st["execute"], u.star):
                self.deal(u, f, f.hp + f.shield(self.t) + 1, "true", spell=True)
                if st.get("refund"):
                    u.refund = True
                continue
            if "amp" in st:
                self.mark(f, at_star(st["amp"], u.star), st.get("amp_secs", 4))
                self.ev("b", f.id, "mark", st.get("amp_secs", 4))
            if "wound" in st:
                f.wound_until = self.t + st["wound"]
                self.ev("b", f.id, "wound", st["wound"])
            if "mana_burn" in st and f.ability:
                f.mana = max(0.0, f.mana - at_star(st["mana_burn"], u.star))
            if "knock" in st and u.alive:
                self.knock(u, f, st["knock"])
            if "stun" in st and not f.cc_immune:
                secs = at_star(st["stun"], u.star)
                f.stun = max(f.stun, self.t + secs)
                self.ev("st", f.id, secs)
            if "slow" in st:
                f.slow = (at_star(st["slow"], u.star), self.t + SLOW_SECS)
            if "burn" in st or u.cast_burn:  # Kindling and Inferno Heart burn whatever the ability hits
                f.burn = (f.max * max(at_star(st.get("burn", 0), u.star), u.cast_burn), self.t + BURN_SECS, u)
        if "heal_frac" in st and drained and u.alive:
            self.heal(u, drained * at_star(st["heal_frac"], u.star), u)

    def step_heal(self, u, st, power=1.0):
        amount = at_star(st["amt"], u.star) * u.ap / 100 * power
        for f in self.select(u, st["to"]):
            self.heal(f, amount, u)

    def step_shield(self, u, st, power=1.0):
        amount = at_star(st["amt"], u.star) * u.ap / 100 * power
        secs = at_star(st["secs"], u.star)
        for f in self.select(u, st["to"]):
            f.shields.append([amount, self.t + secs])
            self.ev("s", f.id, round(amount), secs, u.id)

    def step_buff(self, u, st, power=1.0):
        amount = at_star(st["amt"], u.star) * power
        secs = at_star(st["secs"], u.star)
        for f in self.select(u, st["to"]):
            f.buffs.append([st["stat"], amount, self.t + secs])
            if st["stat"] == "dodge" and amount >= 1:
                self.ev("b", f.id, "parry", secs)

    def step_grow(self, u, st, power=1.0):
        """Grows for good: `stat` (ad, ap, armor, mr, aspd_pct, hp) up by `amt` each cast."""
        amount = at_star(st["amt"], u.star) * power
        for f in self.select(u, st.get("to", "self")):
            if st["stat"] == "hp":
                f.max += amount
                f.hp += amount
            else:
                setattr(f, st["stat"], getattr(f, st["stat"]) + amount)
            self.ev("b", f.id, "grow", 1)

    def step_taunt(self, u, st, power=1.0):
        secs = at_star(st["secs"], u.star)
        for f in self.select(u, st["to"]):
            f.taunt = (u, self.t + secs)
        self.ev("b", u.id, "taunt", secs)

    def step_vanish(self, u, st, power=1.0):
        secs = at_star(st["secs"], u.star)
        u.hidden_until = self.t + secs
        self.ev("b", u.id, "vanish", secs)

    def step_cleanse(self, u, st, power=1.0):
        for f in self.select(u, st["to"]):
            f.stun = min(f.stun, self.t)
            f.slow = (0.0, 0.0)
            f.burn = (0.0, 0.0, None)
            f.wound_until = 0.0
            f.amp = (0.0, 0.0)
            self.ev("b", f.id, "cleanse", 0.5)

    def step_pull(self, u, st, power=1.0):
        """Drags the unit `to` picks to a free hex beside the caster, and makes it the target."""
        picked = [f for f in self.select(u, st["to"]) if not f.static]
        if not picked:
            return
        f = picked[0]
        free = sorted((n for n in neighbours(u.hex) if n not in self.occ), key=lambda n: (dist(n, f.hex), n))
        if free and dist(f.hex, u.hex) > 1:
            self.jump(f, free[0])
            f.busy = max(f.busy, self.t + 0.3)
        u.target = f

    def knock(self, u, f, n):
        """Shoves f up to n hexes straight away from u (stopping at the edge or another unit)."""
        if f.static or not f.alive:
            return
        spot = None
        for h in line_hexes(u.hex, f.hex, dist(u.hex, f.hex) + n)[dist(u.hex, f.hex):]:
            if h in self.occ:
                break
            spot = h
        if spot:
            self.jump(f, spot)
            f.busy = max(f.busy, self.t + 0.3)

    def step_zone(self, u, st, power=1.0):
        """A lingering area for `secs`: hurts (dmg a second, magic as burn) and slows enemies in it, or
        heals allies in it (heal a second). At the target, the caster or the densest cluster."""
        r = st.get("r", 1)
        t = u.target if u.target is not None and u.target.alive else self.nearest(u, self.foes(u))
        where = st.get("at") or (self.cluster_centre(u, r) if st["to"] == "cluster" else u.hex if st["to"] == "self"
                                 else t.hex if t else None)
        if not where:
            return
        secs = at_star(st["secs"], u.star)
        self.zones.append([u.side, where, r, self.t + secs, at_star(st.get("dmg", 0), u.star) * power,
                           at_star(st.get("heal", 0), u.star) * power, st.get("slow", 0), u])
        self.ev("z", u.side, where[0], where[1], r, secs, "zone", u.id)

    def step_raise(self, u, st, power=1.0):
        """Raises `unit` where units have fallen (the latest first), up to `count`; any left over rise
        beside the caster."""
        n = at_star(st.get("count", 1), u.star)
        for _ in range(n):
            spot = next((h for h in reversed(self.corpses) if h not in self.occ), None) or self.free_near(u.hex)
            if spot is None:
                return
            self.corpses = [h for h in self.corpses if h != spot]
            s = self.add(u.side, st["unit"], u.star, spot)
            self.boost_summon(u, s, power)
            s.base_max = s.max
            s.next_atk = self.t + 0.5
            self.ev("sp", s.row())

    def step_devour(self, u, st, power=1.0):
        """Swallows the unit `to` picks: it can't act or be reached for `secs`, and takes dmg now."""
        picked = self.select(u, st["to"])
        if not picked:
            return
        f = picked[0]
        secs = at_star(st["secs"], u.star)
        self.deal(u, f, at_star(st["dmg"], u.star) * u.ap / 100 * power, "magic", spell=True)
        if f.alive and not f.cc_immune:
            f.stun = max(f.stun, self.t + secs)
            f.hidden_until = self.t + secs
            self.ev("b", f.id, "devour", secs)

    def boost_summon(self, u, s, power=1.0):
        """Summoner boosts, and an Empowered ability (power above 1), make what u calls up stronger."""
        m = (1 + u.summon_boost) * max(1.0, power)
        if m != 1:
            s.max *= m
            s.hp = s.max
            s.ad *= m

    def step_summon(self, u, st, power=1.0):
        for _ in range(at_star(st.get("count", 1), u.star)):
            h = self.free_near(u.hex)
            if h is None:
                return
            s = self.add(u.side, st["unit"], u.star, h)
            self.boost_summon(u, s, power)
            s.base_max = s.max
            s.next_atk = self.t + 0.5
            self.ev("sp", s.row())

    def step_mana(self, u, st, power=1.0):
        amount = at_star(st["amt"], u.star)
        for f in self.select(u, st["to"]):
            if f is not u and f.ability:
                f.mana = min(f.maxmana, f.mana + amount)

    def step_dash(self, u, st, power=1.0):
        picked = self.select(u, st["to"])
        if not picked:
            return
        spot = self.free_near(picked[0].hex)
        if spot:
            self.jump(u, spot)
        u.target = picked[0]


def fight(home, away, seed=0):
    return Fight(home, away, seed).run()
