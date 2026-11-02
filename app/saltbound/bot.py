"""Bots, for solo testing and the simulator only (real games wait for their players).

`decide(game, h)` returns the next message a bot playing hero h would send, or None if it has
nothing to do. The party heads for one shared goal each turn so the bots stay together.
"""

import heapq
import zlib
from itertools import combinations

from . import classes as C
from . import world as Wd
from .combat import Invalid
from .dice import amt, check_hit, top_face
from .dice import face as face_of
from .tuning import ROLL_MODS
from .content import archipelago as A
from .content import items as I

RANK = {r: i for i, r in enumerate(I.RARITIES)}


def support(g, h):
    """A fallen hero gives their spirit die to the ally still to play who holds the fewest unused
    dice (so it adds a play rather than sitting spare)."""
    s = g.s
    f = s["fight"]
    if not f or s["phase"] != "fight":
        return None
    sp = f["spirit"].get(str(h))
    if not sp or sp["used"]:
        return None
    to = [y for y in g.actives() if not g.hs(y)["ready"]] or g.actives()
    if not to:
        return None
    best = min(to, key=lambda y: (sum(1 for d in g.hs(y)["dice"] if not d["used"]), y))
    return {"t": "spirit", "to": best}


def decide(g, h):
    s = g.s
    hero = g.hero(h)
    if s["phase"] == "end":
        return None
    q = s["pending"][str(h)]
    if q:
        return choose(g, h, q[0])
    if not hero["alive"]:
        return support(g, h)
    if s["phase"] == "fork" and s.get("fork") and str(h) not in s["fork"]["votes"]:
        return {"t": "fork", "n": fork_pick(g, s["fork"])}
    if s["phase"] == "fight" and g.in_fight(h):
        return fight_move(g, h)
    if s["phase"] == "plan":
        return plan_move(g, h)
    return None


FORK_PREF = {"champion": 3, "vault": 2, "passage": 1, "shrine": 0, "gate": 2, "sneak": 3, "rest": 1}


def fork_pick(g, fk):
    """A path: rest when the party is hurt, otherwise the better loot."""
    heroes = [y for y in fk["heroes"] if g.hero(y)["alive"]]
    hp = sum(g.hero(y)["hp"] for y in heroes) / max(1, sum(g.maxhp(y) for y in heroes))
    def score(i):
        p = fk["opts"][i]["path"]
        if p in ("shrine", "rest"):
            return 5 if hp < 0.55 else 0
        return FORK_PREF.get(p, 1)
    return max(range(len(fk["opts"])), key=score)


SETUP_OPS = {"inspire", "hymn", "give", "reroll_ally", "strip", "guard", "taunt"}
SETUP_STATUS = {"crescendo", "vuln", "mark", "weak"}


def order(g, heroes):
    """Who plans first in a fight: heroes holding a usable set-up (a buff, Mark, Vulnerable,
    Crescendo...), so it resolves before the attacks it's meant to help. Actions happen in the
    order they're placed."""
    if g.s["phase"] != "fight" or not g.s["fight"]:
        return list(heroes)

    def setup(y):
        if not g.in_fight(y) or not g.active(y):
            return 1
        x = g.hs(y)
        for k in g.actions_of(y):
            a = g.action_def(y, k)
            if (a.get("cd") and g.cooling(y, a["key"])) or (a.get("once") and a["key"] in x["once"]):
                continue
            if any(o["op"] in SETUP_OPS or (o["op"] == "status" and o["s"] in SETUP_STATUS) for o in a["ops"]):
                return 0
        return 1
    return sorted(heroes, key=setup)


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
        # the pick that most improves on what's worn in its slot (consumables by rarity)
        opts = d["opts"]
        return {"t": "choose", "n": max(range(len(opts)), key=lambda i: loot_gain(g, h, opts[i]))}
    if d["type"] == "pool":
        # claim the unclaimed item that most improves on what's worn (consumables by rarity)
        pool = g.s["pools"][str(d["id"])]
        free = [i for i in range(len(pool["items"])) if str(i) not in pool["taken"]]
        if not free:
            return {"t": "choose", "n": -1}
        return {"t": "choose", "n": max(free, key=lambda i: loot_gain(g, h, pool["items"][i]))}
    if d["type"] == "level":
        opts = d["opts"]
        return {"t": "choose", "n": max(range(len(opts)), key=lambda i: level_score(g, h, d["lvl"], opts[i]))}
    return None


def loot_gain(g, h, k):
    """How much an item improves on what's worn in its slot (consumables by rarity)."""
    it = I.ITEMS[k]
    if it["slot"] == "use":
        return RANK[it["rarity"]] * 1.5
    cur = replaced(g, h, k)[1]
    return item_score(g, h, k) - (item_score(g, h, cur) if cur else 0)


def replaced(g, h, key):
    """(slot, item) that wearing this would replace: an empty slot first, else the weakest worn one
    of its kind (two trinket slots)."""
    equip = g.hero(h)["equip"]
    slots = I.slots_for(I.ITEMS[key]["slot"])
    empty = [s for s in slots if not equip.get(s)]
    if empty:
        return empty[0], None
    s = min(slots, key=lambda s: item_score(g, h, equip[s]))
    return s, equip[s]


# Item passives that only do something with the right actions: (mods, what the hero needs)
NEEDS = [
    ({"bomb_bonus", "splash_bonus", "chain_reaction"}, lambda a: a.get("bomb")),
    ({"spell_burn", "spell_chain", "spell_echo"}, lambda a: a.get("spell")),
    ({"heal_bonus", "heal_armor", "overflow"}, lambda a: any(o["op"] == "heal" for o in a["ops"])),
    ({"summon_cap", "summon_hp", "summon_regen"}, lambda a: any(o["op"] == "summon" for o in a["ops"])),
    ({"poison_bonus", "plague"}, lambda a: any(o["op"] == "status" and o["s"] == "poison" for o in a["ops"])),
    ({"burn_bonus"}, lambda a: any(o["op"] == "status" and o["s"] == "burn" for o in a["ops"])),
    ({"mark_ext"}, lambda a: any(o["op"] == "status" and o["s"] == "mark" for o in a["ops"])),
    ({"root_ext"}, lambda a: any(o["op"] == "status" and o["s"] == "root" for o in a["ops"])),
]
# ...and ones that work against what the hero is for: Camouflage on someone who pulls hits
AVOIDS = [({"camouflage"}, lambda a: any(o["op"] in ("guard", "taunt") for o in a["ops"]))]


def item_score(g, h, key):
    """Roughly what a piece of gear is worth to this hero: its rarity, its die, and its passive
    unless the passive needs actions the hero doesn't have (bomb bonuses on someone with no bombs)."""
    it = I.ITEMS[key]
    acts = [g.action_def(h, k) for k in g.actions_of(h)] + \
        [g.action_def(h, k) for k in it.get("acts", []) if k in I.WEAPON_ACTIONS or k in C.ACTIONS]
    score = RANK[it["rarity"]] * 2.5
    die = it.get("die")
    if die:
        score += sum(v if v is not None else 0 for v, _ in map(face_of, die)) / len(die) * 0.5
    mods = set(it.get("mods", {})) - {"max_hp", "move"}
    for keys, need in NEEDS:
        if mods & keys and not any(need(a) for a in acts):
            score -= 3
    for keys, clash in AVOIDS:
        if mods & keys and any(clash(a) for a in acts):
            score -= 4
    return score + it.get("mods", {}).get("max_hp", 0) * 0.3


def better(g, h, key):
    """Would wearing this beat what's in its slot?"""
    cur = replaced(g, h, key)[1]
    return cur is None or item_score(g, h, key) > item_score(g, h, cur) + 0.5


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
        if it["slot"] != "use" and better(g, h, key):
            return {"t": "equip", "bag": i, "into": replaced(g, h, key)[0]}
    if place and place["kind"] == "town":
        if hero["hp"] < mx * 0.7 and hero["gold"] >= g.inn_cost():
            return {"t": "inn"}
        if not hero["skiff"] and g.docks(hero["tile"]) and hero["gold"] >= 10:
            return {"t": "skiff"}
        town = g.place(hero["tile"])
        jobs = town.get("jobs") or []
        active = [q for q in s["quests"] if not q["done"] and not q.get("failed")]
        if jobs and not town.get("quest_taken") and len(active) < 2:
            # the best-paying job the party could manage (lairs and bounties once it's strong enough)
            ok = [i for i, j in enumerate(jobs) if j["kind"] in ("deliver", "salvage") or s["level"] >= 3]
            if ok:
                return {"t": "quest", "n": max(ok, key=lambda i: job_value(jobs[i]))}
        if town.get("spec") == "temple":
            if any(A.BUFFS.get(b, {}).get("curse") for b in hero["buffs"]):
                return {"t": "temple", "what": "cleanse"}
            if not town.get("revive_sold") and s["revives"] < 2 and hero["gold"] >= A.TEMPLE_REVIVE + 10:
                return {"t": "temple", "what": "revive"}
        if town.get("spec") == "smith":
            ups = [(g.reforge_cost(k), sl) for sl, k in hero["equip"].items() if k and g.reforge_cost(k)]
            ups = [(c, sl) for c, sl in ups if hero["gold"] >= c + 15]
            if ups:
                return {"t": "reforge", "slot": min(ups)[1]}
        stock = list(g.shop(hero["tile"]))
        ship = g.opp_at(hero["tile"])
        if ship and ship["kind"] == "ship":
            stock = ship["stock"] + stock
        for key in stock:
            it = I.ITEMS[key]
            if it["slot"] == "use":
                continue
            if better(g, h, key) and hero["gold"] >= g.price_for(h, key):
                return {"t": "buy", "item": key}
        if hero["gold"] >= 30 and hero["bag"].count("potion") < 2:
            return {"t": "buy", "item": "potion"}
    if hero["hp"] < mx * 0.45 and "potion" in hero["bag"]:
        return {"t": "use", "bag": hero["bag"].index("potion")}
    if hero["hp"] < mx * 0.35 and not (place and place["kind"] == "town"):
        if not p["rest"]:
            return {"t": "rest"}
        return {"t": "ready"}
    goal = party_goal(g)
    if goal is not None and not p["path"]:
        goal, fight = keep_together(g, h, goal)
        path = route(g, h, goal)
        if path and fight and goal in path:
            # wait beside the fight until the whole party is close enough to be pulled in with you
            path = path[:path.index(goal)]
        if path:
            try:
                g.path_cost(h, path)
                return {"t": "path", "path": path}
            except Invalid:
                pass
    # nowhere to go (already at the goal, say a town whose inn is too dear): rest while hurt
    if hero["hp"] < mx and not p["path"] and not p["rest"]:
        return {"t": "rest"}
    return {"t": "ready"}


def keep_together(g, h, goal):
    """Players keep their party together; so do the bots. A hero who is more than 2 hexes ahead of an
    ally waits for them (walking back made heroes cross and swap places). Returns (where to go, and whether walking
    into it starts a fight that someone would miss: everyone else must be within a hex of it first,
    since that's who a fight pulls in)."""
    at = g.hero(h)["tile"]
    others = [g.hero(y)["tile"] for y in g.living() if y != h]
    behind = [t for t in others if Wd.dist(t, at) > 2 and Wd.dist(t, goal) > Wd.dist(at, goal)]
    if behind:
        return at, False
    fight = g.is_dungeon(goal) or g.group_at(goal) is not None
    return goal, fight and any(Wd.dist(t, goal) > 1 for t in others)


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
    # a chance that won't wait, if the party can get there in time
    for o in sorted(s.get("opps", []), key=lambda o: Wd.dist(o["tile"], at)):
        if Wd.dist(o["tile"], at) > (o["until"] - s["turn"] + 1) * 3:
            continue
        if o["kind"] == "drift" or (o["kind"] == "healer" and weakest < 0.75 and len(o["used"]) < len(alive)) \
                or (o["kind"] == "ship" and lead["gold"] >= 40):
            return o["tile"]
    # a job, while there's time to finish it, unless it's time for a dungeon
    ready_for = 2 + 2 * len(s["cleared"])
    due = s["level"] >= ready_for or s["rises"] >= 8
    jobs = [q for q in s["quests"] if not q["done"] and not q.get("failed") and not due]
    for q in sorted(jobs, key=lambda q: q["until"]):
        goal = g.job_goal(q)
        trip = Wd.dist(goal, at) + (Wd.dist(goal, q["src_tile"]) if q["kind"] == "salvage" and q.get("stage") == "fetch" else 0)
        if goal is not None and trip <= (q["until"] - s["turn"] + 1) * 3 and (q["kind"] not in ("lair", "bounty") or s["level"] >= 3):
            return goal
    ready_for = 2 + 2 * len(s["cleared"])
    if s["level"] >= ready_for or s["rises"] >= 8:
        dungeons = [int(t) for t, p in places.items() if p["kind"] == "dungeon" and p["region"] not in s["cleared"]]
        if dungeons:
            return min(dungeons, key=lambda t: Wd.dist(t, at))
    targets = [gr["tile"] for gr in s["groups"] if s["seen"][gr["tile"]] and (not gr["lair"] or s["level"] >= 3)]
    targets += [int(t) for t, p in places.items() if s["seen"][int(t)] and p["kind"] in ("event", "wreck", "shrine", "cache")
                and not p.get("done") and not (p["kind"] == "shrine" and int(t) in lead["shrines"])]
    if targets:
        return min(targets, key=lambda t: Wd.dist(t, at))
    unseen = [t for t in range(Wd.W * Wd.H) if not s["seen"][t] and g.terrain(t) in Wd.COST]
    if unseen:
        return min(unseen, key=lambda t: Wd.dist(t, at))
    return None


JOB_EXTRA = {"loot": 25, "item": 40, "revive": 45, "trade": 30, "restock": 20}


def job_value(j):
    """What a job is worth to the bots, per turn it takes."""
    return (3 * j["reward"]["gold"] + JOB_EXTRA[j["reward"]["type"]]) / j["turns"]


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
    # a party travelling together moves at its slowest member's pace, so a quick hero (a Tracker,
    # Wayfinder) doesn't arrive first and fight alone
    mates = [y for y in g.living() if Wd.dist(g.hero(y)["tile"], hero["tile"]) <= 3]
    pace = min(g.moves(y) for y in mates) if len(mates) == len(g.living()) else g.moves(h)
    for t, _ in steps:
        st = g.step_cost(h, at, t, af)
        if st is None or spent + st[0] > pace:
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
        global _SIGS
        _SIGS = {}

    def __exit__(self, *exc):
        global _SIGS
        _SIGS = None
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

def hits_of(it):
    """How many hits an intent lands (separate dice, or a sweep)."""
    if it.get("each"):
        return len(it.get("dice") or []) or 1
    if it.get("sweep"):
        return it["sweep"]
    return 1


def foe_value(it):
    """How much an intent matters, in rough HP-to-the-party terms."""
    k, v = it.get("k"), it.get("v", 0)
    return {"attack": v * hits_of(it), "all": v * 2.5, "heal": v * 0.7, "buff": v * 3, "summon": 5, "charge": 4,
            "block": v * 0.3, "guard": v * 0.4, "debuff": 4}.get(k, 0) + (2 if it.get("st") else 0)


_BASE = {}


def base_threat(g, fo):
    """What this kind of enemy is worth stopping on an average round."""
    from .foes import die_mean
    key = fo["k"]
    if key not in _BASE:
        d = A.FOES[key]
        moves = d["moves"]
        keys = d.get("seq") or list(moves)
        tot = wt = 0
        for k in keys:
            mv = moves[k]
            idx = mv.get("use") or list(range(mv.get("n", 0)))
            dice = [d["dice"][i] for i in idx]
            v = sum(die_mean(x["faces"], x.get("dk", [])) for x in dice)
            if mv.get("each") and dice:
                v /= len(dice)
            w = 1 if d.get("seq") else mv.get("w", 1)
            tot += foe_value(dict(mv, v=v if mv["k"] != "buff" else mv.get("v", 2), dice=dice)) * w
            wt += w
        _BASE[key] = tot / max(1, wt)
    f = g.s["fight"]
    return _BASE[key] * f["dmul"] + fo["might"] * 1.5


class Board:
    """The round as a player sees it: the enemies' intents, and set-ups the bot is weighing in its plan."""

    def __init__(self, g, empty=False):
        self.dmg, self.stop, self.cut, self.armor, self.heal, self.summons = {}, {}, {}, {}, {}, {}
        # set-ups already planned: chance a foe will be Vulnerable or Marked before later hits land,
        # and chance a hero's next damaging action gets Crescendo
        self.vuln, self.mark, self.cresc = {}, {}, {}
        if empty:
            return
        f = g.s["fight"]
        self.sanct = f["sanct"] + f["aegis"]
        self.taunt = f["taunt"]
        # Actions happen as they're placed, so what the party has already done is in the state.

    def copy(self):
        b = Board(None, empty=True)
        for k in ("dmg", "stop", "cut", "armor", "heal", "summons", "vuln", "mark", "cresc"):
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
        for name in ("vuln", "mark", "cresc"):
            tgt = getattr(self, name)
            for k, v in eff[name].items():
                tgt[k] = 1 - (1 - tgt.get(k, 0)) * (1 - min(1, v))
        for k, v in eff["cused"].items():
            self.cresc[k] = self.cresc.get(k, 0) * (1 - min(1, v))
        self.sanct += eff["sanct"]
        if eff["taunt"] is not None:
            self.taunt = eff["taunt"]


def foe_hits(g, b, fo):
    """[(unit, damage)] this enemy's intent will do this round, as things stand."""
    it = fo.get("intent") or {}
    k = it.get("k")
    if k not in ("attack", "all", "debuff") or fo["st"].get("stun"):
        return []
    live = 1 - b.stop.get(fo["id"], 0)
    v = max(0, it.get("v", 0) - b.cut.get(fo["id"], 0))
    if fo["st"].get("freeze"):
        v //= 2
    if fo["st"].get("weak"):
        v = int(v * 0.75)
    v = (0 if k == "debuff" else v) + (2 if it.get("st") else 0) + (4 if k == "debuff" else 0)
    units = g.party_units()
    if k == "all":
        hit = units
    else:
        hit = list(it.get("tgts") or ([it["tgt"]] if it.get("tgt") else []))
        if b.taunt is not None and g.active(b.taunt):
            hit = [f"h{b.taunt}"] * len(hit)
        hit = [t for t in hit if t in units]
    out = [(u, max(0, v - (b.sanct if u.startswith("h") else 0)) * live) for u in hit]
    if it.get("chain") and out:
        others = [u for u in units if u not in hit]
        out += [(u, out[0][1] / 2 / len(others)) for u in others]
    return out


def threat_now(g, b, fo):
    """What this enemy will do to the party this round if nothing stops it."""
    it = fo.get("intent") or {}
    if fo["st"].get("stun"):
        return 0
    live = 1 - b.stop.get(fo["id"], 0)
    if it.get("k") in ("attack", "all", "debuff"):
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
    for y in inc:
        # the Drowned Crown's Undertow lands at the end of the round (Armor stops it)
        n = g.hs(y)["st"].get("undertow", 0)
        if n:
            inc[y] += n
            big[y] = max(big[y], n)
            hits[y] += 1
    return inc, big, hits


# ---- scoring one placement

_COMBOS = {}


def dice_combos(g, h, dice):
    """Every way these dice could come up, [(values, tags, chance, dice variables)], cached: the
    same dice are scored on many actions and targets."""
    x = g.hs(h)
    m = g.mods(h)
    key = (h, g.s["fight"].get("hymn", 0), tuple(m.get(k, 0) for k in ROLL_MODS), x["st"].get("armor", 0), g.maxhp(h) - g.hero(h)["hp"],
           tuple(die_sig(d) + (d.get("rolled"), d.get("tag"), str(x.get("links", {}).get(d.get("link")))) for d in dice))
    got = _COMBOS.get(key)
    if got is None:
        if len(_COMBOS) > 4096:
            _COMBOS.clear()
        got = _COMBOS[key] = [(vals, tags, pr, g.dice_env(h, vals, tags))
                              for vals, tags, pr in g.joint_outcomes(h, dice, cap=COMBO_CAP)]
    return got


def new_eff():
    return {"dmg": {}, "stop": {}, "cut": {}, "armor": {}, "heal": {}, "summons": {}, "sanct": 0.0, "taunt": None,
            "vuln": {}, "mark": {}, "cresc": {}, "cused": {}}


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
    bonus = {}  # the hero's flat damage bonus on each target: the same for every outcome

    def dmg_bonus(t):
        if t["id"] not in bonus:
            bonus[t["id"]] = g.dmg_bonus(h, a, t)
        return bonus[t["id"]]
    # hits a Taunt or Guard in this action pulls onto the hero, for the Armor op after it
    pulled = 0.0
    for o in a["ops"]:
        if o["op"] == "taunt":
            pulled = sum(n for y, n in inc.items() if y != h)
        elif o["op"] == "guard" and base and isinstance(base[0], tuple) and base[0][1] != h:
            pulled = big.get(base[0][1], 0)
    # What doesn't change from one way the dice could roll to the next is worked out once here: each
    # op's targets, and for a damage op what it needs to know about each target. The sums below are
    # in the same order as ever, so this only saves time (the run fingerprints must not change).
    cres = 1.0 if g.hs(h)["st"].get("crescendo") else b.cresc.get(h, 0)
    spell_burn = bool(a.get("spell") and m.get("spell_burn"))
    red_mist = bool(m.get("red_mist") and g.hero(h)["hp"] < g.maxhp(h) / 2)
    melee = a.get("melee")

    def prep(ops):
        out = []
        for op in ops:
            k = op["op"]
            tg = op_targets(g, h, op, base)
            info = None
            if k == "dmg":
                per = []
                for t, share in tg:
                    if not isinstance(t, dict) or (t.get("air") and melee):
                        continue
                    tid = t["id"]
                    st = t["st"]
                    per.append((t, share, g.target_part(h, t), dmg_bonus(t), g.combo_parts(h, t),
                                None if st.get("vuln") else 1 + 0.25 * b.vuln.get(tid, 0),
                                None if st.get("mark") else 3 * b.mark.get(tid, 0),
                                t["hp"] - b.dmg.get(tid, 0), 0.75 + 0.5 * tb[tid] / top, now[tid] + 2 + 0.5 * tb[tid]))
                info = (per, op.get("each"), g.hit_pierces(h, a, op), "if" in op, bool(op.get("leech") or op.get("onkill")))
            out.append((op, k, tg, info))
        return out
    hit_ops, miss_ops = prep(a["ops"]), prep(a.get("miss", []))
    for vals, tags, pr, de in dice_combos(g, h, dice):
        hit = check_hit(a["req"], vals, tags)
        val = 0.0
        dealt = {}
        hit_any = False
        for op, k, tg, info in (hit_ops if hit else miss_ops):
            if k == "dmg":
                # worked out with the fight's own sums (Combat.hit_base, hit_finish, foe_soak, hit_spill)
                per, each_op, pierce, cond, leech = info
                each = range(len(vals)) if each_op else [None]
                for t, share, part_env, bonus_t, combo, vfac, madd, left0, w, stopv in per:
                    env = g.target_env_from(de, part_env, t, vals)
                    if cond and not amt(op["if"], env):
                        continue
                    n = 0
                    spill = 0.0
                    for j, i in enumerate(each):
                        raw, _ = g.hit_base(h, a, op, t, dice, vals, tags, i, env=env, bonus=bonus_t)
                        if j == 0:
                            raw += g.combo_sum(combo, vals)  # Pincer, Covered, Shatter, the bell (as combo_peek)
                        raw = g.hit_finish(h, raw, dice, vals, i, cres)
                        got = g.foe_damage_after(t, int(raw), h)
                        # Vulnerable and Mark that earlier placements will have put on it
                        if vfac is not None:
                            got *= vfac
                        if madd is not None:
                            got += madd
                        n += g.foe_soak(t, got, h, pierce=pierce)[0]
                        for kind, kn in g.hit_spill(h, a, op, int(raw)):
                            hit_by = g.spill_targets(kind, t)
                            part = 1 / len(hit_by) if kind == "chain" and hit_by else 1
                            spill += sum(min(kn, o["hp"]) * 0.8 * part for o in hit_by)
                    hit_any = True
                    val += share * spill
                    tid = t["id"]
                    left = left0 - dealt.get(tid, 0)
                    if left <= 0:
                        val += share * 0.05 * n
                        continue
                    val += share * min(n, left) * w
                    if n >= left:
                        val += share * stopv
                        bump(eff["stop"], tid, pr * share)
                    elif n > 0 and spell_burn:
                        val += share * foe_status(g, b, "burn", 1, t, now, tb, top, eff, pr * share)
                    if leech:
                        val += share * min(n, left) * 0.3
                    if red_mist:
                        val += share * heal_value(g, b, h, min(n, left) // 3, inc)
                    dealt[tid] = dealt.get(tid, 0) + n * share
                    bump(eff["dmg"], tid, pr * share * min(n, left))
            elif k == "status":
                for t, share in tg:
                    env = g.target_env(de, h, t, vals) if isinstance(t, dict) else de
                    if "if" in op and not amt(op["if"], env):
                        continue
                    n = g.status_amount(h, a, op["s"], amt(op["n"], env))
                    if isinstance(t, dict):
                        val += share * foe_status(g, b, op["s"], n, t, now, tb, top, eff, pr * share)
                    else:
                        val += share * hero_status(g, b, h, op["s"], n, t[1], inc, big, hits, eff, pr * share)
            elif k == "armor":
                n = amt(op["amt"], de) + plus
                for t, share in tg:
                    if isinstance(t, tuple):
                        y = t[1]
                        need = max(0, inc.get(y, 0) + (pulled if y == h else 0) - g.hs(y)["st"].get("armor", 0) - b.armor.get(y, 0))
                        val += share * (min(n, need) + n * (0.33 if m.get("overguard") else 0.15))
                        bump(eff["armor"], y, pr * share * n)
            elif k == "heal":
                n = amt(op["amt"], de) + plus + m.get("heal_bonus", 0)
                for t, share in tg:
                    if isinstance(t, tuple):
                        val += share * heal_value(g, b, t[1], n, inc, overflow=bool(m.get("overflow")))
                        bump(eff["heal"], t[1], pr * share * n)
            elif k == "lift":
                for t, share in tg:
                    if isinstance(t, tuple) and g.hs(t[1])["down"]:
                        val += share * 30
            elif k == "heal_summons":
                n = amt(op["amt"], de) + plus
                val += sum(min(n, al["max"] - al["hp"]) * 0.4 for al in g.allies())
            elif k == "selfdmg":
                n = amt(op["amt"], {})
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
                val += n * sum(hits.values()) + (m.get("aegis", 0) * 3 if hit else 0)
                eff["sanct"] += pr * n
            elif k == "cleanse":
                for t, share in tg:
                    if isinstance(t, tuple):
                        st = g.hs(t[1])["st"]
                        val += share * (st.get("burn", 0) + 2 * st.get("poison", 0) + 2 * sum(1 for s in ("weak", "vuln", "mark", "root") if st.get(s)))
            elif k == "weaken":
                n = amt(op["amt"], de) + plus
                for t, share in tg:
                    if isinstance(t, dict) and (t.get("intent") or {}).get("v") is not None:
                        v = t["intent"]["v"]
                        val += share * min(n, v) / max(1, v) * now[t["id"]]
                        bump(eff["cut"], t["id"], pr * share * n)
            elif k == "cancel":
                for t, share in tg:
                    if isinstance(t, dict) and not g.steeled(t):
                        val += share * now[t["id"]]
                        bump(eff["stop"], t["id"], pr * share)
            elif k == "retarget":
                for t, share in tg:
                    if isinstance(t, dict):
                        val += share * now[t["id"]] * 0.4
            elif k == "foresee":
                for t, share in tg:
                    it = t.get("intent") if isinstance(t, dict) else None
                    if it and any(d.get("v") is None for d in it.get("dice") or []):
                        val += share * 0.8
            elif k == "steal":
                for t, share in tg:
                    it = t.get("intent") if isinstance(t, dict) else None
                    if it and it.get("dice") and it.get("k") in ("attack", "all"):
                        frac = 1 / len(it["dice"]) if len(it["dice"]) > 1 else 1
                        val += share * now[t["id"]] * min(1, frac * 1.3)
                        bump(eff["cut"], t["id"], pr * share * it.get("v", 0) * frac)
            elif k == "strip":
                n = amt(op["amt"], de) + plus
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
        if hit_any:
            bump(eff["cused"], h, pr)  # this hit spends the hero's Crescendo
        total += pr * val
    return total, eff


def foe_status(g, b, s, n, t, now, tb, top, eff, pr):
    left = max(0, t["hp"] - b.dmg.get(t["id"], 0))
    if left <= 0 or n <= 0:
        return 0
    w = 0.75 + 0.5 * tb[t["id"]] / top
    if s == "stun":
        if t["st"].get("stun") or g.steeled(t):
            return 0
        bump(eff["stop"], t["id"], pr)
        return now[t["id"]] + 1
    if s == "freeze":
        bump(eff["cut"], t["id"], pr * (t.get("intent") or {}).get("v", 0) / 2)
        return now[t["id"]] * 0.5
    if s == "weak":
        return 0.25 * now[t["id"]] + 0.25 * tb[t["id"]] * n
    if s in ("vuln", "mark"):
        # worth more the more of the party's damage is still to come; later placements see it too
        if t["st"].get(s):
            return 0
        fresh = 1 - getattr(b, s).get(t["id"], 0)
        bump(eff[s], t["id"], pr)
        return fresh * (2.0 * n if s == "vuln" else min(3.0 * n, left))
    if s == "burn":
        return min(n * (n + 1) / 2, left) * w * 0.9
    if s == "poison":
        return min(n * 3, left) * w * 0.9
    if s == "doom":
        return min(n, left) * w * 0.8
    if s == "shock":
        return 1.5
    return 0.5


def hero_status(g, b, h, s, n, y, inc, big, hits, eff, pr):
    if not g.active(y):
        return 0
    if s == "dodge":
        return big.get(y, 0) * 0.9 or 0.5
    if s in ("riposte", "thorns"):
        return n * hits.get(y, 0) * 0.8
    if s == "crescendo":
        # half again on this hero's next damaging action (about 6), if it hasn't already got one
        if g.hs(y)["st"].get("crescendo"):
            return 0
        fresh = 1 - b.cresc.get(y, 0)
        bump(eff["cresc"], y, pr)
        return 3.0 * fresh
    if s == "lifeline":
        # half their max HP at the end of the round, but only if they're still standing then (a knocked
        # down hero loses their statuses): worth what they'll be missing after this round's hits
        if g.hs(y)["st"].get("lifeline"):
            return 0
        left = g.hero(y)["hp"] + g.hs(y)["st"].get("armor", 0) - inc.get(y, 0)
        if left <= 0:
            return 0
        return min(g.maxhp(y) // 2, g.maxhp(y) - left) * 0.6
    return 1


def heal_value(g, b, y, n, inc, overflow=False):
    """A point healed is worth at least a point of Armor that stops a hit: HP lost stays lost after the
    fight (an inn or a rest to get back). More on the badly hurt, much more on someone about to drop.
    With Overflow, healing past full is Armor, valued as Armor is."""
    if not g.active(y):
        return 0
    hero = g.hero(y)
    mx = g.maxhp(y)
    missing = mx - hero["hp"] - b.heal.get(y, 0)
    useful = max(0, min(n, missing))
    extra = 0.0
    if overflow and n > useful:
        spare = n - useful
        need = max(0, inc.get(y, 0) - g.hs(y)["st"].get("armor", 0) - b.armor.get(y, 0) - useful)
        extra = min(spare, need) + spare * 0.15
    left = hero["hp"] + b.heal.get(y, 0) + g.hs(y)["st"].get("armor", 0) + b.armor.get(y, 0) - inc.get(y, 0)
    if left <= 0 and useful > 0:
        return useful * 2 + (10 if useful > -left else 0) + extra
    return useful * (1.0 + (1 - hero["hp"] / mx)) + extra


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
    if to == "another":
        first = next((t for t in base if isinstance(t, dict)), None)
        others = [fo for fo in g.foes() if fo is not first]
        return [(fo, 1 / len(others)) for fo in others]
    if to == "party":
        return [(("h", y), 1) for y in g.actives()]
    if to == "lowest":
        others = [y for y in g.actives() if y != h]
        return [(("h", min(others, key=lambda y: g.hero(y)["hp"])), 1)] if others else []
    return [(t, 1) for t in base]


# ---- planning the hand

_SIGS = None  # die signatures while a bot thinks (`frozen`): id -> (the die, its signature)


def die_sig(d):
    # every part sortable (None and numbers don't compare): dice are sorted by this signature
    if _SIGS is not None:
        got = _SIGS.get(id(d))
        if got is not None and got[0] is d:
            return got[1]
        sig = _die_sig(d)
        _SIGS[id(d)] = (d, sig)  # holding the die keeps its id from being reused meanwhile
        return sig
    return _die_sig(d)


def _die_sig(d):
    return (tuple(map(str, d["faces"])), tuple(d.get("dk") or ()), str(d.get("v")), str(d.get("fc") or ()), str(d.get("hint")),
            d.get("bonus", 0), str(d.get("link")), bool(d.get("top")))


def candidates(g, h, b, free):
    x = g.hs(h)
    foes = g.foes()
    out = []
    for key in g.actions_of(h):
        a = g.action_def(h, key)
        if a["key"] == "flee" or (a.get("once") and a["key"] in x["once"]):
            continue
        if a.get("per_rest") and a["key"] in g.hero(h).get("spent", []):
            continue
        if a.get("cd") and g.cooling(h, a["key"]):
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
                if not a["def"] and not g.mods(h).get("guard_free") and any("guard" in (d.get("dk") or []) for d in dice):
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


RISKY_REQ = ("min", "max", "exact", "odd", "even", "sum_min", "pair", "or_face")


def die_mean(g, h, d):
    return sum(v * p for v, _, p in g.outcomes(h, d))


def unrolled(g, y):
    """Dice of a hero that will still roll this round (placed or not)."""
    return [d for d in g.hs(y)["dice"] if not d.get("rolled")]


def has_risky(g, y):
    return any(any(k in g.action_def(y, k2).get("req", {}) for k in RISKY_REQ) for k2 in g.actions_of(y))


def instant_value(g, h, a, dice):
    """Instant tricks, valued by what they add to the party's rolls this round."""
    key = a["key"]
    m = g.mods(h)
    extra = (1 if m.get("second_verse") else 0) + (2 if a["plus"] else 0)
    others = [y for y in g.actives() if y != h]
    if key == "inspire":
        # half the die (at least 2) on an ally's next roll: best on the ally with the most still to roll
        cand = [y for y in others if unrolled(g, y)]
        if not cand or not dice:
            return []
        y = max(cand, key=lambda z: (len(unrolled(g, z)), has_risky(g, z)))
        bonus = max(2, die_mean(g, h, dice[0]) // 2) + extra
        return [(f"h{y}", bonus * (1.3 if has_risky(g, y) else 1.1) * (0.8 if g.hs(y).get("inspire") else 1))]
    if key == "hymn_of_valor":
        # +1 (+2 on a match) to every die the party still rolls this round
        if len(dice) < 2:
            return []
        count = sum(len(unrolled(g, y)) for y in g.actives()) - len(dice)
        a0, b0 = dice[0], dice[1]
        if a0.get("v") is not None and b0.get("v") is not None:
            match = 1.0 if a0["v"] == b0["v"] else 0.0
        else:
            match = 1 / max(len(a0["faces"]), len(b0["faces"]))
        return [(None, (1 + match + extra) * count * 0.9)]
    if key == "lend_a_hand":
        cand = [y for y in others if not g.hs(y)["ready"]]
        if not cand or not dice:
            return []
        seer = dice[0].get("v") is not None
        y = max(cand, key=lambda z: (has_risky(g, z) and seer, -len(unrolled(g, z))))
        bonus = C.ACTIONS["lend_a_hand"]["ops"][0].get("bonus", 0)
        return [(f"h{y}", die_mean(g, h, dice[0]) + bonus + extra + (2 if seer and has_risky(g, y) else 0) - 0.5)]
    if key == "perfect_form":
        d = dice[0] if dice else None
        if not d or d.get("top"):
            return []
        return [(None, (top_face(d["faces"]) - die_mean(g, h, d)) * 1.2)]
    if key == "bloodprice":
        # the +3 lands on a die the plan then uses (the search can't see that), so count it here
        low = g.hero(h)["hp"] < g.maxhp(h) * 0.4
        return [(None, 2 * 1.6 - 3 * (1.5 if low else 0.4))]
    if key == "loaded_dice":
        pairs = any("pair" in g.action_def(h, k).get("req", {}) or "pair" in str(g.action_def(h, k).get("ops"))
                    for k in g.actions_of(h) if not g.cooling(h, k.rstrip("+")))
        return [(None, 3 if pairs else 0.3)]
    if key == "quicksilver":
        cand = others or [h]
        y = max(cand, key=lambda z: has_risky(g, z))
        # the next die rolls 3 higher, and two rerolls for a hero with risky actions
        return [(f"h{y}", 4.5 if has_risky(g, y) else 3)]
    if key == "bottle_it":
        # a potion kept for later: a Tonic (heals 10), or a Rum Ration (22) on a 5+; a stored heal is
        # worth about a third of what it heals (the bots drink potions only when someone would drop)
        if not dice:
            return []
        out = g.outcomes(h, dice[0])
        big = sum(p for v, _, p in out if v >= 5)
        heal = big * I.ITEMS["big_potion"]["use"]["heal"] + (1 - big) * I.ITEMS["potion"]["use"]["heal"]
        return [(None, heal * 0.35 * (2 if g.mods(h).get("philosopher") else 1))]
    if key == "encore":
        # Counterpoint: a low roll turns high; worth about a quarter of the die's size
        d = dice[0] if dice else None
        if not d or d.get("v") is not None and d["v"] > top_face(d["faces"]) / 2:
            return []
        return [(None, top_face(d["faces"]) * 0.3 + (1 if has_risky(g, h) else 0))]
    if key == "potency":
        # Splitting Flask: one more action to spend (the Alchemist's Toss)
        d = dice[0] if dice else None
        return [(None, 2.0)] if d and top_face(d["faces"]) >= 6 else []
    if key == "bramble_skin":
        # Grafting: worth it when a big roll is needed (Call Bear 9+, Strangle on a Rooted foe)
        needs = any(g.action_def(h, k)["req"].get("sum_min", 0) >= 9 for k in g.actions_of(h) if not g.cooling(h, k.rstrip("+")))
        return [(None, 2.5)] if needs and len(dice) == 2 else []
    if key == "aura":
        cand = [y for y in others if unrolled(g, y)]
        if not cand:
            return []
        y = max(cand, key=lambda z: (has_risky(g, z), len(unrolled(g, z))))
        return [(f"h{y}", 2.5 + (1.5 if has_risky(g, y) else 0))]
    if key == "transfusion":
        cand = others or [h]
        y = max(cand, key=lambda z: g.maxhp(z) - g.hero(z)["hp"])
        miss = g.maxhp(y) - g.hero(y)["hp"]
        return [(f"h{y}", min(miss, die_mean(g, h, dice[0]) if dice else 0) * 0.8 + 2)]
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
