"""Bots, for solo testing and the simulator only (real games wait for their players).

`decide(game, h)` returns the next message a bot playing hero h would send, or None if it has
nothing to do. The party heads for one shared goal each turn so the bots stay together.
"""

import heapq
from itertools import combinations

from . import classes as C
from . import world as Wd
from .combat import Invalid
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
        best = 0
        for i, ch in enumerate(ev["choices"]):
            if ch.get("need") and g.has_class(ch["need"]):
                best = i
                break
            if ch.get("cost", 0) > hero["gold"]:
                continue
            if "fight" in ch["ok"] and hero["hp"] < g.maxhp(h) * 0.6:
                continue
        return {"t": "choose", "n": best}
    if d["type"] == "loot":
        opts = d["opts"]
        best = max(range(len(opts)), key=lambda i: RANK[I.ITEMS[opts[i]]["rarity"]])
        return {"t": "choose", "n": best}
    if d["type"] == "level":
        return {"t": "choose", "n": 0}
    return None


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

def fight_move(g, h):
    x = g.hs(h)
    if x["ready"]:
        return None
    free = [d for d in x["dice"] if not d["used"]]
    best = None
    if free:
        best = best_placement(g, h, free)
    if best:
        return best
    return {"t": "fready"}


def best_placement(g, h, free):
    f = g.s["fight"]
    hurt = [y for y in g.actives() if g.hero(y)["hp"] < g.maxhp(y) * 0.45]
    downed = [y for y in f["heroes"] if g.hs(y)["down"]]
    foes = g.foes()
    if not foes:
        return None
    best, score = None, 0.0
    for key in g.actions_of(h):
        a = g.action_def(h, key)
        if a["key"] in ("flee",):
            continue
        if a.get("once") and a["key"] in g.hs(h)["once"]:
            continue
        n = a["req"].get("n", 1)
        combos = [()] if n == 0 else combinations(free, n) if n <= 3 else []
        for dice in combos:
            if not g.check_req(a["req"], list(dice)):
                continue
            for tgt, val in targets(g, h, a, list(dice), hurt, downed, foes):
                if val > score:
                    best, score = {"t": "place", "a": a["key"], "dice": [d["id"] for d in dice], "tgt": tgt}, val
    if best and best["a"] == "shift":
        return best if score > 0 else None
    return best


def planned_damage(g):
    """Damage the party has already planned on each enemy this round."""
    out = {}
    for p in g.s["fight"]["plan"]:
        est = p.get("est")
        if est and est["k"] == "dmg" and p["tgt"]:
            out[p["tgt"]] = out.get(p["tgt"], 0) + est["n"]
    return out


def targets(g, h, a, dice, hurt, downed, foes):
    kind = a["tgt"]
    x = g.hs(h)
    if a.get("melee") and x["row"] != "front":
        return []
    ops = [o["op"] for o in a["ops"]]
    env = g.env(h, a, dice)
    v = env["sum"] if env["n"] > 1 else env["v"]
    if kind == "foe":
        planned = planned_damage(g)
        pool = g.front_foes() if a.get("melee") else foes
        pool = [o for o in pool if planned.get(f"f{o['id']}", 0) < o["hp"]]
        if not pool:
            return []
        fo = min(pool, key=lambda o: o["hp"] - planned.get(f"f{o['id']}", 0))
        est = g.estimate(h, a, dice, f"f{fo['id']}")
        val = (est["n"] if est else 2) + (3 if est and est["n"] >= fo["hp"] else 0)
        if "status" in ops:
            val += 2
        return [(f"f{fo['id']}", val)]
    if kind in ("foes", "front"):
        est = g.estimate(h, a, dice, None)
        n = len(foes if kind == "foes" else g.front_foes())
        return [(None, (est["n"] if est else 2) * n + 1)]
    if kind == "downed":
        return [(f"h{y}", 30) for y in downed[:1]]
    if kind in ("ally", "other"):
        if "heal" in ops and hurt:
            y = min(hurt, key=lambda y: g.hero(y)["hp"])
            return [(f"h{y}", 12 + v)]
        if "armor" in ops or "guard" in ops:
            cand = [y for y in g.actives() if y != h or kind == "ally"]
            if cand:
                y = min(cand, key=lambda y: g.hero(y)["hp"])
                return [(f"h{y}", v * 0.8)]
        if "status" in ops and a["key"] == "lifeline" and hurt:
            return [(f"h{hurt[0]}", 20)]
        if "cleanse" in ops:
            return []
        return []
    if kind == "party":
        if "heal" in ops:
            return [(None, 6 * len(hurt) + (1 if hurt else -1))]
        return [(None, 6)]
    if kind == "self":
        if "armor" in ops:
            # only worth it against what's actually coming this round, less what's already planned
            incoming = sum(fo["intent"].get("v", 0) for fo in foes
                           if fo.get("intent") and fo["intent"].get("tgt") == f"h{h}")
            have = x["st"].get("armor", 0) + sum(p["est"]["n"] for p in g.s["fight"]["plan"]
                                                 if p["h"] == h and p.get("est") and p["est"]["k"] == "armor")
            gain = min(v * (2 if a["key"] == "brace" else 1), max(0, incoming - have))
            return [(None, gain * 0.9)]
        if "taunt" in ops:
            return [(None, 4 if g.hero(h)["hp"] > g.maxhp(h) * 0.6 else 0)]
        if "shift" in ops:
            melee_only = all(g.action_def(h, k).get("melee") for k in g.actions_of(h) if k not in C.GENERIC)
            if x["row"] == "back" and melee_only:
                return [(None, 5)]
            return []
    return []
