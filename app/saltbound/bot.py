"""Bots, for solo testing and the simulator only (real games wait for their players).

`decide(game, h)` returns the next message a bot playing hero h would send, or None if it has
nothing to do. The party heads for one shared goal each turn so the bots stay together.
"""

import heapq
import zlib
from itertools import combinations, product

from . import classes as C
from . import world as Wd
from .combat import Invalid, _amt, _p, check_hit
from .content import archipelago as A
from .content import items as I

RANK = {r: i for i, r in enumerate(I.RARITIES)}


def decide(g, h):
    s = g.s
    hero = g.hero(h)
    if s["phase"] == "end":
        return None
    q = s["pending"][str(h)]
    if q:
        return choose(g, h, q[0])
    if not hero["alive"]:
        f = s["fight"]
        if f and s["phase"] == "fight":
            sp = f["spirit"].get(str(h))
            if sp and not sp["used"] and g.actives():
                return {"t": "spirit", "to": g.actives()[0]}
        return None
    if s["phase"] == "fight" and g.in_fight(h):
        return fight_move(g, h)
    if s["phase"] == "plan":
        return plan_move(g, h)
    return None


# ---------------------------------------------------------------------- dialogs

def choose(g, h, d):
    hero = g.hero(h)
    if d["type"] == "event":
        ev = next(e for e in A.EVENTS if e["key"] == d["key"])
        ok = [i for i, ch in enumerate(ev["choices"])
              if (not ch.get("need") or g.has_class(ch["need"])) and ch.get("cost", 0) <= hero["gold"]]
        best = next((i for i in ok if ev["choices"][i].get("need")), None)
        if best is None:
            safe = [i for i in ok if not ("fight" in ev["choices"][i]["ok"] and hero["hp"] < g.maxhp(h) * 0.6)]
            best = (safe or ok or [0])[0]
        return {"t": "choose", "n": best}
    if d["type"] == "loot":
        opts = d["opts"]
        best = max(range(len(opts)), key=lambda i: RANK[I.ITEMS[opts[i]]["rarity"]])
        return {"t": "choose", "n": best}
    if d["type"] == "level":
        opts = d["opts"]
        return {"t": "choose", "n": max(range(len(opts)), key=lambda i: level_score(g, h, d["lvl"], opts[i]))}
    return None


def level_score(g, h, lvl, key):
    """Roughly how a sensible player ranks a level-up: new actions while the hand is small, capstones,
    passives, then upgrades. A little seeded noise spreads the picks, so the simulator sees them all."""
    hero = g.hero(h)
    base = key.rstrip("+")
    actions = [k for k in hero["skills"] if k.rstrip("+") in C.ACTIONS and k not in C.GENERIC]
    if key.endswith("+"):
        score = 2.0
    elif base in C.PASSIVES:
        score = 3.5 if C.PASSIVES[base].get("cap") else 2.5
    else:
        score = 3.0 if len(actions) < 5 else 1.6
        if C.ACTIONS.get(base, {}).get("cd"):
            score -= 0.3
    noise = zlib.crc32(f"{g.s['seed']}:{h}:{lvl}:{key}".encode()) % 1000 / 1000
    return score + noise * 1.5


# ---------------------------------------------------------------------- the map

def plan_move(g, h):
    s = g.s
    hero = g.hero(h)
    p = s["plans"][str(h)]
    if p["ready"]:
        return None
    place = g.place(hero["tile"])
    mx = g.maxhp(h)
    # gear from the bag
    for i, key in enumerate(hero["bag"]):
        it = I.ITEMS[key]
        if it["slot"] != "use":
            cur = hero["equip"].get(it["slot"])
            if cur is None or RANK[it["rarity"]] > RANK[I.ITEMS[cur]["rarity"]]:
                return {"t": "equip", "bag": i}
    if place and place["kind"] == "town":
        if hero["hp"] < mx * 0.7 and hero["gold"] >= g.inn_cost():
            return {"t": "inn"}
        if not hero["skiff"] and g.docks(hero["tile"]) and hero["gold"] >= 10:
            return {"t": "skiff"}
        stock = g.shop(hero["tile"])
        for key in stock:
            it = I.ITEMS[key]
            if it["slot"] == "use":
                continue
            cur = hero["equip"].get(it["slot"])
            if (cur is None or RANK[it["rarity"]] > RANK[I.ITEMS[cur]["rarity"]]) and hero["gold"] >= g.price_for(h, key) \
                    and len(hero["bag"]) < 4:
                return {"t": "buy", "item": key}
        if hero["gold"] >= 30 and hero["bag"].count("potion") < 2 and len(hero["bag"]) < 4:
            return {"t": "buy", "item": "potion"}
    if hero["hp"] < mx * 0.45 and "potion" in hero["bag"]:
        return {"t": "use", "bag": hero["bag"].index("potion")}
    if hero["hp"] < mx * 0.35 and not (place and place["kind"] == "town"):
        if not p["rest"]:
            return {"t": "rest"}
        return {"t": "ready"}
    goal = party_goal(g)
    if goal is not None and not p["path"]:
        path = route(g, h, goal)
        if path:
            try:
                g.path_cost(h, path)
                return {"t": "path", "path": path}
            except Invalid:
                pass
    return {"t": "ready"}


def party_goal(g):
    """Where the party is heading this turn: the same answer for every hero."""
    s = g.s
    alive = g.living()
    if not alive:
        return None
    lead = g.hero(alive[0])
    at = lead["tile"]
    places = s["world"]["places"]
    if len(s["cleared"]) == 3:
        return s["world"]["peak"]
    weakest = min(g.hero(h)["hp"] / g.maxhp(h) for h in alive)
    if weakest < 0.5:
        towns = [int(t) for t, p in places.items() if p["kind"] == "town"]
        if towns:
            return min(towns, key=lambda t: Wd.dist(t, at))
    ready_for = 2 + 2 * len(s["cleared"])
    if s["level"] >= ready_for or s["rises"] >= 8:
        dungeons = [int(t) for t, p in places.items() if p["kind"] == "dungeon" and p["region"] not in s["cleared"]]
        if dungeons:
            return min(dungeons, key=lambda t: Wd.dist(t, at))
    targets = [gr["tile"] for gr in s["groups"] if s["seen"][gr["tile"]] and (not gr["lair"] or s["level"] >= 3)]
    targets += [int(t) for t, p in places.items() if s["seen"][int(t)] and p["kind"] in ("event", "wreck", "shrine")
                and not p.get("done")]
    if targets:
        return min(targets, key=lambda t: Wd.dist(t, at))
    unseen = [t for t in range(Wd.W * Wd.H) if not s["seen"][t] and g.terrain(t) in Wd.COST]
    if unseen:
        return min(unseen, key=lambda t: Wd.dist(t, at))
    return None


def route(g, h, goal):
    """The first steps (within this turn's moves) of the cheapest way to goal."""
    hero = g.hero(h)
    start = (hero["tile"], hero["afloat"])
    dist = {start: 0}
    prev = {}
    pq = [(0, start)]
    end = None
    while pq:
        d, (t, af) = heapq.heappop(pq)
        if d > dist.get((t, af), 1e9):
            continue
        if t == goal:
            end = (t, af)
            break
        if d > 60:
            break
        for n in Wd.neighbors(t):
            st = g.step_cost(h, t, n, af)
            if st is None:
                continue
            if (g.group_at(n) or g.is_dungeon(n)) and n != goal:
                continue
            nd = d + st[0]
            key = (n, st[1])
            if nd < dist.get(key, 1e9):
                dist[key] = nd
                prev[key] = (t, af)
                heapq.heappush(pq, (nd, key))
    if end is None:
        return None
    steps = []
    k = end
    while k != start:
        steps.append(k)
        k = prev[k]
    steps.reverse()
    out, spent, af, at = [], 0, hero["afloat"], hero["tile"]
    for t, _ in steps:
        st = g.step_cost(h, at, t, af)
        if st is None or spent + st[0] > g.moves(h):
            break
        spent += st[0]
        out.append(t)
        at, af = t, st[1]
    return out


# ---------------------------------------------------------------------- fights
#
# The bots fight like a sensible player. They read every intent, then plan their whole hand at once
# (a short beam search over placements) and score each placement by what it's worth this round:
# damage weighted by how dangerous the target is, kills before an enemy acts (its intent never
# happens), stuns and weakens on the biggest hits, and Armor and heals where the damage will land.
# Every placement is scored across the ways its dice might roll, so a risky action's miss counts.

BEAM = 3
DEPTH = 3
COMBO_CAP = 96


def fight_move(g, h):
    x = g.hs(h)
    if x["ready"]:
        return None
    with frozen(g):
        return _fight_move(g, h, x)


class frozen:
    """Nothing changes while a bot thinks, so remember each hero's mods and max HP meanwhile."""

    def __init__(self, g):
        self.g = g

    def __enter__(self):
        g = self.g
        mods, maxhp, aura = {}, {}, []
        cm, cx, ca = type(g).mods, type(g).maxhp, type(g).herald_aura
        g.mods = lambda y: mods[y] if y in mods else mods.setdefault(y, cm(g, y))
        g.maxhp = lambda y: maxhp[y] if y in maxhp else maxhp.setdefault(y, cx(g, y))
        g.herald_aura = lambda: aura[0] if aura else (aura.append(ca(g)) or aura[0])

    def __exit__(self, *exc):
        for k in ("mods", "maxhp", "herald_aura"):
            self.g.__dict__.pop(k, None)


def _fight_move(g, h, x):
    b = Board(g)
    use = consumable(g, h, b)
    if use:
        return use
    free = [d for d in x["dice"] if not d["used"]]
    if free:
        val, msg = plan_hand(g, h, b, free, DEPTH)
        if msg and val > 0.3:
            return msg
    return {"t": "fready"}


# ---- what the enemies will do

def foe_value(it):
    """How much an intent matters, in rough HP-to-the-party terms."""
    k, v = it.get("k"), it.get("v", 0)
    return {"attack": v, "row": v * 2, "all": v * 2.5, "heal": v * 0.7, "buff": v * 3, "summon": 5,
            "block": v * 0.3, "guard": v * 0.4, "debuff": 3}.get(k, 0) + (2 if it.get("st") else 0)


_BASE = {}


def base_threat(g, fo):
    """What this kind of enemy is worth stopping on an average round."""
    key = fo["k"]
    if key not in _BASE:
        d = A.FOES[key]
        ints = d.get("seq") or d["ints"]
        w = [i.get("w", 1) for i in ints]
        _BASE[key] = sum(foe_value(i) * wi for i, wi in zip(ints, w)) / sum(w)
    f = g.s["fight"]
    return _BASE[key] * f["dmul"] + fo["might"] * 1.5


class Board:
    """The round as a player sees it: the enemies' intents, and what the party has already planned."""

    def __init__(self, g, empty=False):
        self.dmg, self.stop, self.cut, self.armor, self.heal, self.summons = {}, {}, {}, {}, {}, {}
        if empty:
            return
        f = g.s["fight"]
        self.sanct = f["sanct"] + f["aegis"]
        self.taunt = f["taunt"]
        for p in f["plan"]:
            y = p["h"]
            if not g.active(y):
                continue
            dice = [d for d in g.hs(y)["dice"] if d["id"] in p["dice"]]
            a = g.action_def(y, p["a"] + ("+" if p["plus"] else ""))
            _, eff = evaluate(g, self, y, a, dice, p["tgt"])
            self.apply(eff)

    def copy(self):
        b = Board(None, empty=True)
        for k in ("dmg", "stop", "cut", "armor", "heal", "summons"):
            setattr(b, k, dict(getattr(self, k)))
        b.sanct, b.taunt = self.sanct, self.taunt
        return b

    def view(self, g):
        """Incoming damage and each enemy's threat, worked out once per board."""
        if getattr(self, "_view", None) is None:
            foes = g.foes()
            tb = {fo["id"]: base_threat(g, fo) for fo in foes}
            self._view = (incoming(g, self), foes, tb, max(tb.values() or [1]) or 1,
                          {fo["id"]: threat_now(g, self, fo) for fo in foes})
        return self._view

    def apply(self, eff):
        self._view = None
        for k, v in eff["dmg"].items():
            self.dmg[k] = self.dmg.get(k, 0) + v
        for k, v in eff["stop"].items():
            self.stop[k] = 1 - (1 - self.stop.get(k, 0)) * (1 - min(1, v))
        for name in ("cut", "armor", "heal", "summons"):
            tgt = getattr(self, name)
            for k, v in eff[name].items():
                tgt[k] = tgt.get(k, 0) + v
        self.sanct += eff["sanct"]
        if eff["taunt"] is not None:
            self.taunt = eff["taunt"]


def foe_hits(g, b, fo):
    """[(unit, damage)] this enemy's intent will do this round, as things stand."""
    it = fo.get("intent") or {}
    k = it.get("k")
    if k not in ("attack", "row", "all", "debuff") or fo["st"].get("stun"):
        return []
    live = 1 - b.stop.get(fo["id"], 0)
    v = max(0, it.get("v", 0) - b.cut.get(fo["id"], 0))
    if fo["st"].get("freeze"):
        v //= 2
    if fo["st"].get("weak"):
        v = int(v * 0.75)
    v = (0 if k == "debuff" else v) + (2 if it.get("st") else 0)
    units = g.party_units()
    if k in ("attack", "debuff"):
        t = it.get("tgt")
        if b.taunt is not None and g.active(b.taunt):
            t = f"h{b.taunt}"
        hit = [t] if t in units else []
    elif k == "row":
        hit = [u for u in units if g.unit_row(u) == it.get("row", "front")] or units
    else:
        hit = units
    return [(u, max(0, v - (b.sanct if u.startswith("h") else 0)) * live) for u in hit]


def threat_now(g, b, fo):
    """What this enemy will do to the party this round if nothing stops it."""
    it = fo.get("intent") or {}
    if fo["st"].get("stun"):
        return 0
    live = 1 - b.stop.get(fo["id"], 0)
    if it.get("k") in ("attack", "row", "all", "debuff"):
        return sum(n if u.startswith("h") else n / 2 for u, n in foe_hits(g, b, fo))
    return foe_value(it) * live


def incoming(g, b):
    inc = {y: 0.0 for y in g.actives()}
    big = {y: 0.0 for y in g.actives()}
    hits = {y: 0 for y in g.actives()}
    for fo in g.foes():
        for u, n in foe_hits(g, b, fo):
            if u.startswith("h") and int(u[1:]) in inc:
                y = int(u[1:])
                inc[y] += n
                big[y] = max(big[y], n)
                hits[y] += 1
    return inc, big, hits


# ---- scoring one placement

_COMBOS = {}


def dice_combos(g, h, dice):
    key = (h, g.s["fight"].get("hymn", 0), g.mods(h).get("sleight", 0), tuple(die_sig(d) + (d.get("rolled"), d.get("tag")) for d in dice))
    got = _COMBOS.get(key)
    if got is None:
        if len(_COMBOS) > 4096:
            _COMBOS.clear()
        got = _COMBOS[key] = _dice_combos(g, h, dice)
    return got


def _dice_combos(g, h, dice):
    per = [g.outcomes(h, d) for d in dice]
    combos = list(product(*per)) if dice else [()]
    if len(combos) > COMBO_CAP:
        combos = combos[:: len(combos) // COMBO_CAP + 1]
    ps = [_p(c) for c in combos]
    norm = sum(ps) or 1
    return [([o[0] for o in c], [o[1] for o in c], pr / norm) for c, pr in zip(combos, ps)]


def new_eff():
    return {"dmg": {}, "stop": {}, "cut": {}, "armor": {}, "heal": {}, "summons": {}, "sanct": 0.0, "taunt": None}


def bump(d, k, v):
    d[k] = d.get(k, 0) + v


def evaluate(g, b, h, a, dice, tgt):
    """(value, expected effects) of an action with these dice on this target."""
    (inc, big, hits), foes, tb, top, now = b.view(g)
    base = bot_targets_for(g, h, a, tgt)
    m = g.mods(h)
    plus = 2 if a["plus"] else 0
    eff = new_eff()
    total = 0.0
    for vals, tags, pr in dice_combos(g, h, dice):
        hit = check_hit(a["req"], vals, tags)
        val = 0.0
        dealt = {}
        for op in (a["ops"] if hit else a.get("miss", [])):
            k = op["op"]
            tg = op_targets(g, h, op, base)
            if k == "dmg":
                each = vals if op.get("each") else [None]
                for t, share in tg:
                    if not isinstance(t, dict):
                        continue
                    env = g.env(h, a, dice, t, vals, tags)
                    n = 0
                    for v in each:
                        if v is not None:
                            env["d"] = v
                        n += _amt(op["amt"], env) + plus + g.dmg_bonus(h, a, t)
                    if g.hs(h)["st"].get("crescendo"):
                        n = n * 3 // 2
                    n = g.foe_damage_after(t, n, h)
                    if not op.get("pierce"):
                        n = max(0, n - t["st"].get("armor", 0))
                    if op.get("splash"):
                        val += share * sum(min(op["splash"], o["hp"]) * 0.8 for o in foes if o is not t and o["row"] == t["row"])
                    left = t["hp"] - b.dmg.get(t["id"], 0) - dealt.get(t["id"], 0)
                    if left <= 0:
                        val += share * 0.05 * n
                        continue
                    w = 0.75 + 0.5 * tb[t["id"]] / top
                    val += share * min(n, left) * w
                    if n >= left:
                        val += share * (now[t["id"]] + 2 + 0.5 * tb[t["id"]])
                        bump(eff["stop"], t["id"], pr * share)
                    if op.get("leech") or op.get("onkill"):
                        val += share * min(n, left) * 0.3
                    dealt[t["id"]] = dealt.get(t["id"], 0) + n * share
                    bump(eff["dmg"], t["id"], pr * share * min(n, left))
            elif k == "status":
                for t, share in tg:
                    env = g.env(h, a, dice, t if isinstance(t, dict) else None, vals, tags)
                    if "if" in op and not _amt(op["if"], env):
                        continue
                    n = _amt(op["n"], env)
                    if isinstance(t, dict):
                        val += share * foe_status(g, b, op["s"], n, t, now, tb, top, eff, pr * share)
                    else:
                        val += share * hero_status(g, h, op["s"], n, t[1], inc, big, hits)
            elif k == "armor":
                n = _amt(op["amt"], g.env(h, a, dice, None, vals, tags)) + plus
                for t, share in tg:
                    if isinstance(t, tuple):
                        y = t[1]
                        need = max(0, inc.get(y, 0) - g.hs(y)["st"].get("armor", 0) - b.armor.get(y, 0))
                        val += share * (min(n, need) + n * (0.5 if m.get("overguard") else 0.15))
                        bump(eff["armor"], y, pr * share * n)
            elif k == "heal":
                n = _amt(op["amt"], g.env(h, a, dice, None, vals, tags)) + plus + m.get("heal_bonus", 0)
                for t, share in tg:
                    if isinstance(t, tuple):
                        val += share * heal_value(g, b, t[1], n, inc)
                        bump(eff["heal"], t[1], pr * share * n)
            elif k == "lift":
                for t, share in tg:
                    if isinstance(t, tuple) and g.hs(t[1])["down"]:
                        val += share * 30
            elif k == "heal_summons":
                n = _amt(op["amt"], g.env(h, a, dice, None, vals, tags)) + plus
                val += sum(min(n, al["max"] - al["hp"]) * 0.4 for al in g.allies())
            elif k == "selfdmg":
                n = _amt(op["amt"], {})
                low = g.hero(h)["hp"] - inc.get(h, 0) < g.maxhp(h) * 0.35
                val -= n * (1.5 if low else 0.4)
            elif k == "guard":
                for t, share in tg:
                    if isinstance(t, tuple) and t[1] != h:
                        y = t[1]
                        frac = lambda z: g.hero(z)["hp"] / g.maxhp(z)
                        val += share * inc.get(y, 0) * (0.6 if frac(y) < frac(h) else 0.1)
            elif k == "taunt":
                others = sum(n for y, n in inc.items() if y != h)
                me = g.hero(h)["hp"] + g.hs(h)["st"].get("armor", 0) + b.armor.get(h, 0)
                sturdy = me > inc.get(h, 0) + others and g.hero(h)["hp"] >= g.maxhp(h) * 0.5
                val += 0.6 * others if sturdy else 0
                eff["taunt"] = h
            elif k == "sanct":
                n = op["n"] + (1 if a["plus"] else 0)
                val += n * sum(hits.values()) + (m.get("aegis", 0) * 3)
                eff["sanct"] += pr * n
            elif k == "cleanse":
                for t, share in tg:
                    if isinstance(t, tuple):
                        st = g.hs(t[1])["st"]
                        val += share * (st.get("burn", 0) + 2 * st.get("poison", 0) + 2 * sum(1 for s in ("weak", "vuln", "mark", "root") if st.get(s)))
            elif k == "weaken":
                n = _amt(op["amt"], g.env(h, a, dice, None, vals, tags)) + plus
                for t, share in tg:
                    if isinstance(t, dict) and (t.get("intent") or {}).get("v") is not None:
                        v = t["intent"]["v"]
                        val += share * min(n, v) / max(1, v) * now[t["id"]]
                        bump(eff["cut"], t["id"], pr * share * n)
            elif k == "cancel":
                for t, share in tg:
                    if isinstance(t, dict):
                        val += share * now[t["id"]]
                        bump(eff["stop"], t["id"], pr * share)
            elif k == "retarget":
                for t, share in tg:
                    if isinstance(t, dict):
                        val += share * now[t["id"]] * 0.4
            elif k == "strip":
                n = _amt(op["amt"], g.env(h, a, dice, None, vals, tags)) + plus
                for t, share in tg:
                    if isinstance(t, dict):
                        val += share * min(n, t["st"].get("armor", 0)) * 0.8
            elif k == "drag":
                for t, share in tg:
                    if isinstance(t, dict) and t["row"] == "back":
                        val += share * 1.0
            elif k == "summon":
                mine = sum(1 for al in g.allies() if al["owner"] == h) + b.summons.get(h, 0)
                if mine < C.SUMMON_CAP + m.get("summon_cap", 0):
                    val += 6 + min(6, sum(fo["hp"] for fo in foes) / 12)
                    bump(eff["summons"], h, pr)
            elif k == "gold":
                val += 3
            elif k == "shift":
                x = g.hs(h)
                melee_only = all(g.action_def(h, kk).get("melee") for kk in g.actions_of(h) if kk not in C.GENERIC)
                if x["row"] == "back" and melee_only:
                    val += 6
                elif x["row"] == "front" and not melee_only and g.hero(h)["hp"] < g.maxhp(h) * 0.4 and inc.get(h, 0) > 0:
                    val += min(inc[h], 2 * hits[h]) * 0.8
                if op is a["ops"][-1] and any(o["op"] == "status" and o["s"] == "dodge" for o in a["ops"]):
                    pass
        total += pr * val
    return total, eff


def foe_status(g, b, s, n, t, now, tb, top, eff, pr):
    left = max(0, t["hp"] - b.dmg.get(t["id"], 0))
    if left <= 0 or n <= 0:
        return 0
    w = 0.75 + 0.5 * tb[t["id"]] / top
    if s == "stun":
        if t["st"].get("stun"):
            return 0
        bump(eff["stop"], t["id"], pr)
        return now[t["id"]] + 1
    if s == "freeze":
        bump(eff["cut"], t["id"], pr * (t.get("intent") or {}).get("v", 0) / 2)
        return now[t["id"]] * 0.5
    if s == "weak":
        return 0.25 * now[t["id"]] + 0.25 * tb[t["id"]] * n
    if s == "vuln":
        return 2.0 * n
    if s == "mark":
        return min(3.0 * n, left)
    if s == "burn":
        return min(n * (n + 1) / 2, left) * w * 0.9
    if s == "poison":
        return min(n * 3, left) * w * 0.9
    if s == "doom":
        return min(n, left) * w * 0.8
    if s == "shock":
        return 1.5
    return 0.5


def hero_status(g, h, s, n, y, inc, big, hits):
    if not g.active(y):
        return 0
    if s == "dodge":
        return big.get(y, 0) * 0.9 or 0.5
    if s in ("riposte", "thorns"):
        return n * hits.get(y, 0) * 0.8
    if s == "crescendo":
        return 5
    if s == "lifeline":
        hero = g.hero(y)
        return g.maxhp(y) * 0.6 if hero["hp"] <= inc.get(y, 0) + 2 else 2
    return 1


def heal_value(g, b, y, n, inc):
    if not g.active(y):
        return 0
    hero = g.hero(y)
    mx = g.maxhp(y)
    missing = mx - hero["hp"] - b.heal.get(y, 0)
    useful = max(0, min(n, missing))
    left = hero["hp"] + b.heal.get(y, 0) + g.hs(y)["st"].get("armor", 0) + b.armor.get(y, 0) - inc.get(y, 0)
    if left <= 0 and useful > 0:
        return useful * 2 + (10 if useful > -left else 0)
    return useful * (0.6 + (1 - hero["hp"] / mx))


def bot_targets_for(g, h, a, tgt):
    kind = a["tgt"]
    if kind == "foe":
        fo = g.foe(int(tgt[1:]))
        return [fo] if fo and fo["hp"] > 0 else []
    if kind == "foes":
        return g.foes()
    if kind == "front":
        return list(g.foes() if a["key"] == "cleave" and g.mods(h).get("unstoppable") else g.front_foes())
    if kind in ("ally", "other", "downed"):
        return [("h", int(tgt[1:]))]
    if kind == "party":
        return [("h", y) for y in g.actives()]
    return [("h", h)]


def op_targets(g, h, op, base):
    """Like Combat.op_targets, without the dice: [(target, share)], a random enemy as a share of each."""
    to = op.get("to")
    if to == "self":
        return [(("h", h), 1)]
    if to == "one":
        return [(t, 1) for t in base[:1]]
    if to == "random" or op.get("random"):
        foes = g.foes()
        return [(fo, 1 / len(foes)) for fo in foes]
    if to == "row":
        first = next((t for t in base if isinstance(t, dict)), None)
        return [(fo, 1) for fo in g.foes() if first and fo["row"] == first["row"]]
    if to == "front":
        return [(("h", y), 1) for y in g.actives() if g.hs(y)["row"] == "front"]
    if to == "myrow":
        row = g.hs(h)["row"]
        return [(("h", y), 1) for y in g.actives() if g.hs(y)["row"] == row]
    return [(t, 1) for t in base]


# ---- planning the hand

def die_sig(d):
    return (tuple(map(str, d["faces"])), tuple(d.get("dk") or ()), d.get("v"), tuple(d.get("fc") or ()), d.get("hint"),
            d.get("bonus", 0), d.get("link"), d.get("top"))


def candidates(g, h, b, free):
    f = g.s["fight"]
    x = g.hs(h)
    foes = g.foes()
    out = []
    for key in g.actions_of(h):
        a = g.action_def(h, key)
        if a["key"] == "flee" or (a.get("once") and a["key"] in x["once"]):
            continue
        if a.get("per_rest") and (a["key"] in g.hero(h).get("spent", []) or any(p["h"] == h and p["a"] == a["key"] for p in f["plan"])):
            continue
        if a.get("cd") and (g.cooling(h, a["key"]) or any(p["h"] == h and p["a"] == a["key"] for p in f["plan"])):
            continue
        if a.get("melee") and x["row"] != "front":
            continue
        n = a["req"].get("n", 1)
        sizes = range(1, n + 1) if a["req"].get("upto") else [n]
        for size in sizes:
            if size > 3:
                continue
            seen = set()
            for dice in ([()] if size == 0 else combinations(free, size)):
                sig = tuple(sorted(die_sig(d) for d in dice))
                if sig in seen or not g.count_ok(a["req"], list(dice)):
                    continue
                if not a["def"] and any("guard" in (d.get("dk") or []) for d in dice):
                    continue
                seen.add(sig)
                dice = list(dice)
                msg = {"t": "place", "a": a["key"], "dice": [d["id"] for d in dice]}
                if a.get("instant"):
                    for tgt, val in instant_value(g, h, a, dice):
                        out.append((val, dict(msg, tgt=tgt), new_eff(), msg["dice"]))
                    continue
                for tgt in target_options(g, h, a, foes):
                    val, eff = evaluate(g, b, h, a, dice, tgt)
                    out.append((val, dict(msg, tgt=tgt), eff, msg["dice"]))
    return out


def target_options(g, h, a, foes):
    kind = a["tgt"]
    if kind == "foe":
        pool = g.front_foes() if a.get("melee") else foes
        if a["req"].get("marked"):
            pool = [o for o in pool if o["st"].get("mark")]
        return [f"f{o['id']}" for o in pool]
    if kind == "ally":
        return [f"h{y}" for y in g.actives()]
    if kind == "other":
        return [f"h{y}" for y in g.actives() if y != h]
    if kind == "downed":
        return [f"h{y}" for y in g.s["fight"]["heroes"] if g.hs(y)["down"]]
    return [None]


def plan_hand(g, h, b, free, depth):
    """(value, first placement) of the best way found to spend these dice."""
    cands = candidates(g, h, b, free)
    cands.sort(key=lambda c: -c[0])
    best = (0.0, None)
    for val, msg, eff, used in cands[:BEAM]:
        if val <= 0:
            break
        rest = [d for d in free if d["id"] not in used]
        sub = 0.0
        if rest and depth > 1:
            b2 = b.copy()
            b2.apply(eff)
            sub = plan_hand(g, h, b2, rest, depth - 1)[0]
        if val + sub > best[0]:
            best = (val + sub, msg)
    return best


def instant_value(g, h, a, dice):
    """Instant dice tricks: only the simple, clearly-good ones."""
    key = a["key"]
    if key == "inspire" or key == "lend_a_hand":
        others = [y for y in g.actives() if y != h and any(not d["used"] for d in g.hs(y)["dice"])]
        if others and dice and (key == "inspire" or dice[0].get("v") is not None):
            return [(f"h{others[0]}", 3)]
        return []
    if key == "bottle_it":
        return [(None, 2.5)] if len(g.hero(h)["bag"]) < g.bag_size(h) else []
    return []


def consumable(g, h, b):
    """Potions when someone would otherwise drop, salts for the downed, kegs for a kill that matters."""
    hero = g.hero(h)
    bag = hero["bag"]
    f = g.s["fight"]
    inc, _, _ = incoming(g, b)

    def find(*keys):
        return next((i for i, k in enumerate(bag) if k in keys), None)

    downed = [y for y in f["heroes"] if g.hs(y)["down"] and g.hero(y)["alive"]]
    i = find("smelling_salts")
    if downed and i is not None:
        return {"t": "use", "bag": i, "tgt": f"h{downed[0]}"}
    i = find("big_potion", "potion")
    if i is not None:
        for y in sorted(g.actives(), key=lambda z: g.hero(z)["hp"]):
            left = g.hero(y)["hp"] + g.hs(y)["st"].get("armor", 0) + b.armor.get(y, 0) + b.heal.get(y, 0) - inc.get(y, 0)
            if left <= 0 or g.hero(y)["hp"] < g.maxhp(y) * 0.25:
                return {"t": "use", "bag": i, "tgt": f"h{y}"}
    i = find("ward_scroll")
    if i is not None and sum(inc.values()) >= 14:
        return {"t": "use", "bag": i}
    i = find("bomb")
    if i is not None:
        dmg = I.ITEMS["bomb"]["use"]["bomb"] + g.mods(h).get("bomb_bonus", 0)
        for fo in sorted(g.foes(), key=lambda o: -threat_now(g, b, o)):
            left = fo["hp"] + fo["st"].get("armor", 0) - b.dmg.get(fo["id"], 0)
            if 0 < left <= dmg and threat_now(g, b, fo) >= 5 or A.FOES[fo["k"]].get("boss"):
                return {"t": "use", "bag": i, "tgt": f"f{fo['id']}"}
    return None
