"""A Saltbound run: the whole game state and its rules, outside of fights (see combat.py).

The state is one JSON-able dict (`Game.s`), so saving is `json.dumps(game.s)`. The game never
waits on a clock: it changes only when a hero acts (`Game.act`), and `Game.waiting()` says who it
is waiting on. Every hero sees the same state (vision is shared), so `Game.view()` is one dict
for everyone.

A map turn: every living hero plans a path (or rests) and readies up; then everyone moves at
once, enemies close in, fights start where heroes and enemies meet (every hero within a hex
joins), and landing on a place (an event, a wreck, a shrine) queues a dialog for that hero. Then
the next turn begins: the tide may turn, and every few turns it rises and enemies grow stronger.

Phases: `plan` (map turns), `fight`, `reward` (after a fight, until everyone's picks are made),
`end`.
"""

from . import classes as C
from . import mods as M
from . import world as Wd
from .combat import Combat, Invalid
from .content import archipelago as A
from .content import items as I
from .rng import Rng
from .tuning import SURGE

VERSION = 5
DIFFICULTY = {
    "story": {"rise": 4, "revives": 4, "foe_hp": 1.0, "foe_dmg": 0.95},
    "normal": {"rise": 3, "revives": 3, "foe_hp": 1.9, "foe_dmg": 1.75},
    "hard": {"rise": 3, "revives": 2, "foe_hp": 2.35, "foe_dmg": 2.3},
}
MOVES = 4
VISION = 5  # land seen around a hero: more than a turn's walk, so a move's result is in view
GROW_FROM = 10  # after this many rises more enemies come ashore
TIDE_EVERY = 4
SPAWN_EVERY = 4
MAX_GROUPS = 12
INN_COST = 8
SKIFF_COST = 10
START_GOLD = 20
POOL_EXTRA = 2  # a fight's loot pool holds this many more items than the winners' picks
LOG_KEEP = 40
FX_KEEP = 200


M.check_content([(f"passive {k}", p["mods"]) for k, p in C.PASSIVES.items()]
                + [(f"item {k}", {**it.get("mods", {}), **it.get("cursed_mods", {})}) for k, it in I.ITEMS.items()]
                + [(f"blessing {k}", b["mods"]) for k, b in A.BUFFS.items()])


class Game(Combat):
    def __init__(self, s):
        self.s = s
        self.rng = Rng(s["rng"])

    # ------------------------------------------------------------------ making a run

    @classmethod
    def new(cls, seed, classes, difficulty="normal", names=None):
        assert len(classes) == 3 and len(set(classes)) == 3
        w = Wd.generate(seed)
        diff = DIFFICULTY[difficulty]
        heroes = []
        for i, k in enumerate(classes):
            c = C.CLASSES[k]
            heroes.append({
                "cls": k, "name": (names or [None] * 3)[i] or c["name"], "hp": 0, "gold": START_GOLD,
                "skills": list(c["start"]), "equip": {"weapon": c["weapon"], "armor": c["armor"], "trinket": None},
                "bag": ["potion"], "tile": w["start"], "prev": w["start"], "afloat": False, "skiff": False,
                "alive": True, "buffs": {}, "shrines": [], "dieup": 0, "tags": {},
            })
        s = {
            "v": VERSION, "seed": seed, "rng": seed * 7919 + 17, "diff": difficulty, "turn": 1, "sea": Wd.SEA0,
            "rises": 0, "phase": "plan", "result": None, "world": w, "seen": [0] * (Wd.W * Wd.H), "cleared": [],
            "dungeon": {}, "heroes": heroes, "xp": 0, "level": 1, "revives": diff["revives"], "miracle": False,
            "groups": [], "gid": 1, "plans": {}, "pending": {"0": [], "1": [], "2": []}, "pools": {}, "poolid": 0, "fights": [],
            "fight": None, "after": "turn", "quests": [], "shops": {}, "fx": [], "fxid": 0, "log": [],
            "stats": [{"dmg": 0, "heal": 0, "kills": 0, "taken": 0} for _ in range(3)], "fid": 1,
            "dnext": {}, "fork": None,
        }
        g = cls(s)
        for reg in A.DUNGEONS:
            s["dnext"][reg] = {"path": "open", "foes": g.dungeon_lineup(reg, "open")}
        for h in range(3):
            g.hero(h)["hp"] = g.maxhp(h)
        g.reveal_all()
        for _ in range(9):
            g.spawn(far=4)
        for t, p in w["places"].items():
            if p["kind"] == "lair":
                g.add_group(int(t), list(g.rng.choice(A.LAIRS[w["reg"][int(t)] if w["reg"][int(t)] in A.LAIRS else "coral"])), lair=True)
        g.reset_plans()
        g.say("The party sets out from " + w["places"][str(w["start"])]["name"] + ".")
        g.sync()
        return g

    # ------------------------------------------------------------------ small helpers

    def sync(self):
        self.s["rng"] = self.rng.state

    def hero(self, h):
        return self.s["heroes"][h]

    def say(self, text):
        self.s["log"].append({"t": self.s["turn"], "m": text})
        del self.s["log"][:-LOG_KEEP]

    def fx(self, kind_, **kw):
        self.s["fxid"] += 1
        self.s["fx"].append({"id": self.s["fxid"], "k": kind_, **kw})
        del self.s["fx"][:-FX_KEEP]

    def diff(self):
        return DIFFICULTY[self.s["diff"]]

    def place(self, tile):
        return self.s["world"]["places"].get(str(tile))

    def living(self):
        return [h for h in range(3) if self.hero(h)["alive"]]

    def mods(self, h):
        """Everything that changes a hero's numbers: passives, gear and blessings, summed."""
        hero = self.hero(h)
        out = {"override": {}, "grant": []}

        def add(m):
            for k, v in m.items():
                if k == "override":
                    for a, o in v.items():
                        out["override"].setdefault(a, {}).update(o)
                elif k == "grant":
                    out["grant"].append(v)
                else:
                    out[k] = out.get(k, 0) + v
        for sk in hero["skills"]:
            p = C.PASSIVES.get(sk.rstrip("+"))
            if p:
                add(p["mods"])
        for slot in ("weapon", "armor", "trinket"):
            it = hero["equip"].get(slot)
            if it:
                add(I.ITEMS[it].get("mods", {}))
                if I.ITEMS[it].get("cursed_mods"):
                    add(I.ITEMS[it]["cursed_mods"])
        for b in hero["buffs"]:
            add(A.BUFFS[b]["mods"])
        return out

    def maxhp(self, h):
        hero = self.hero(h)
        c = C.CLASSES[hero["cls"]]
        return max(1, c["hp"] + (self.s["level"] - 1) * c["hp_lvl"] + self.mods(h).get("max_hp", 0))

    def heal(self, h, n):
        hero = self.hero(h)
        before = hero["hp"]
        hero["hp"] = min(self.maxhp(h), hero["hp"] + max(0, n))
        return hero["hp"] - before

    def base_dice(self, h):
        """The class's dice, grown at levels 3 and 6: a 1..N die steps up a size, any other die gets
        +1 on every number. Heirloom dice also raise their lowest face once per party level."""
        hero = self.hero(h)
        dice = [dict(d, faces=list(d["faces"]), dk=list(d["dk"])) for d in C.CLASSES[hero["cls"]]["dice"]]
        for _ in range(hero["dieup"]):
            grow = [d for d in dice if any(isinstance(f, int) for f in d["faces"])]
            if not grow:
                break
            d = min(grow, key=lambda d: max(f for f in d["faces"] if isinstance(f, int)))
            if d["faces"] == list(range(1, len(d["faces"]) + 1)):
                top = len(d["faces"])
                nxt = next((n for n in C.DIE_LADDER if n > top), top + 2)
                d["faces"] = list(range(1, nxt + 1))
            else:
                d["faces"] = [f + 1 if isinstance(f, int) else f for f in d["faces"]]
        return dice

    def dice_of(self, h):
        """Every die a hero rolls: {faces, dk (kinds), src}."""
        hero = self.hero(h)
        out = [dict(d, src="base") for d in self.base_dice(h)]
        for slot in ("weapon", "armor", "trinket"):
            it = hero["equip"].get(slot)
            if it:
                out.append({"faces": list(I.ITEMS[it]["die"]), "dk": list(I.ITEMS[it].get("dk", [])), "src": slot})
        for d in out:
            if "heirloom" in d["dk"]:
                for _ in range(self.s["level"] - 1):
                    nums = [i for i, f in enumerate(d["faces"]) if isinstance(f, int)]
                    low = min(nums, key=lambda i: d["faces"][i])
                    d["faces"][low] += 1
        return out

    def actions_of(self, h):
        """The keys of the actions a hero can use (with '+' for upgraded ones)."""
        hero = self.hero(h)
        out = [k for k in hero["skills"] if k.rstrip("+") in C.ACTIONS]
        for slot in ("weapon", "trinket"):
            w = hero["equip"].get(slot)
            if w:
                out += [a for a in I.ITEMS[w].get("acts", []) if a not in out]
        out += [g for g in self.mods(h)["grant"] if g not in out]
        out += C.GENERIC
        return out

    def action_def(self, h, key):
        base = key.rstrip("+")
        a = dict(C.ACTIONS.get(base) or I.WEAPON_ACTIONS[base])
        a.update(self.mods(h)["override"].get(base, {}))
        a["key"] = base
        a["plus"] = key.endswith("+")
        a["def"] = C.is_defensive(a)
        return a

    def moves(self, h):
        hero = self.hero(h)
        tracker = C.CLASSES[hero["cls"]]["map"]["key"] == "tracker" and not hero["afloat"]
        return max(1, MOVES + self.mods(h).get("move", 0) + (1 if tracker else 0))


    # ------------------------------------------------------------------ terrain

    def terrain(self, t):
        """'deep', 'shoal' (passable on foot at low tide) or a land biome."""
        e = self.s["world"]["elev"][t]
        sea = self.s["sea"]
        if e <= sea:
            return "deep"
        if e == sea + 1:
            return "deep" if self.tide() == "high" else "shoal"
        return self.s["world"]["bio"][t]

    def tide(self):
        return "low" if ((self.s["turn"] - 1) // TIDE_EVERY) % 2 == 0 else "high"

    def step_cost(self, h, a, b, afloat):
        """(cost, afloat after) for a hero stepping from a to b, or None if they can't."""
        hero = self.hero(h)
        if b not in Wd.neighbors(a):
            return None
        if b == self.s["world"]["peak"] and len(self.s["cleared"]) < 3:
            return None
        t = self.terrain(b)
        if t == "deep":
            if not hero["skiff"]:
                return None
            return (1 if afloat else 2), True
        if t == "shoal":
            return (1, True) if afloat else (2, False)
        cost = Wd.COST.get(t, 1)
        if t in Wd.FAST.get(C.CLASSES[hero["cls"]]["map"]["key"], ()):
            cost = 1
        return cost + (1 if afloat else 0), False

    def path_cost(self, h, path):
        hero = self.hero(h)
        at, afloat, total = hero["tile"], hero["afloat"], 0
        vis = self.visible_tiles()
        for i, b in enumerate(path):
            step = self.step_cost(h, at, b, afloat)
            if step is None:
                return None
            if ((self.group_at(b) and b in vis) or self.is_dungeon(b)) and i != len(path) - 1:
                return None  # a fight you can see, or a dungeon, stops you (hidden ones ambush you)
            total += step[0]
            at, afloat = b, step[1]
        return total

    def is_dungeon(self, t):
        p = self.place(t)
        return bool(p) and (p["kind"] == "dungeon" and p["region"] not in self.s["cleared"] or p["kind"] == "peak")

    def reveal(self, t, r):
        for u in Wd.within(t, r):
            self.s["seen"][u] = 1

    def vision(self, h):
        key = C.CLASSES[self.hero(h)["cls"]]["map"]["key"]
        return VISION + (1 if key == "farsight" else 0) + (1 if self.mods(h).get("wayfinder") else 0)

    def enemy_sight(self, h):
        """How far a hero can see enemies (Trackers see them further off)."""
        return self.vision(h) + (2 if C.CLASSES[self.hero(h)["cls"]]["map"]["key"] == "tracker" else 0)

    def reveal_all(self):
        for h in self.living():
            self.reveal(self.hero(h)["tile"], self.vision(h))

    def visible_tiles(self):
        out = set()
        for h in self.living():
            out |= Wd.within(self.hero(h)["tile"], self.enemy_sight(h))
        return out

    # ------------------------------------------------------------------ enemies on the map

    def group_at(self, t):
        return next((g for g in self.s["groups"] if g["tile"] == t), None)

    def tier(self):
        return len(self.s["cleared"])

    def add_group(self, t, foes, lair=False):
        g = {"id": self.s["gid"], "tile": t, "foes": [dict(k) if isinstance(k, dict) else {"k": k} for k in foes], "lair": lair,
             "reg": self.s["world"]["reg"][t]}
        self.s["gid"] += 1
        self.s["groups"].append(g)
        return g

    def spawn(self, far=5):
        w = self.s["world"]
        heroes = [self.hero(h)["tile"] for h in self.living()]
        cands = [t for t in range(Wd.W * Wd.H) if self.terrain(t) in Wd.COST and self.terrain(t) != "town"
                 and not self.place(t) and not self.group_at(t) and all(Wd.dist(t, x) >= far for x in heroes)]
        if not cands:
            return
        t = self.rng.choice(cands)
        reg = w["reg"][t] or "peak"
        pool = A.GROUPS[reg]
        hi = min(len(pool), 3 + self.tier() * 2 + (2 if self.s["rises"] > GROW_FROM else 0))
        lo = max(0, hi - 4)
        foes = list(self.rng.choice(pool[lo:hi]))
        tier = self.tier()
        if tier >= 2 and self.rng.chance(0.15):
            # a big single threat, alone
            foes = [A.BIG.get(reg) or self.rng.choice(list(A.BIG.values()))]
        elif tier >= 1 and self.rng.chance(0.25):
            # an elite leads the group
            i = max(range(len(foes)), key=lambda j: A.FOES[foes[j]]["hp"])
            foes[i] = {"k": foes[i], "aff": self.rng.choice(A.ROAM_ELITES)}
        self.add_group(t, foes)

    def move_groups(self):
        """Enemies near a hero on land take a step toward them. Returns tiles where they caught someone."""
        caught = []
        heroes = [h for h in self.living() if not self.hero(h)["afloat"]]
        pos = {h: (self.hero(h)["tile"], self.hero(h)["afloat"]) for h in self.living()}
        for g in self.s["groups"]:
            tile_of = {x["id"]: x["tile"] for x in self.s["groups"]}
            best = self.group_step(g, pos, set(tile_of.values()), tile_of)
            if best is not None:
                self.fx("gmove", g=g["id"], path=[g["tile"], best])
                g["tile"] = best
                if any(self.hero(x)["tile"] == best for x in heroes):
                    caught.append(best)
        return caught

    def group_step(self, g, heroes, occupied, tile_of):
        """Where a roaming group steps this turn, toward the nearest hero on land within 3 (None if
        it stays). `heroes` maps hero to (tile, afloat); `occupied` is every group's tile."""
        if g["lair"]:
            return None
        beasts = all(A.FOES[f["k"]].get("beast") for f in g["foes"])
        at = tile_of[g["id"]]
        near = [h for h, (t, af) in heroes.items() if not af and Wd.dist(at, t) <= 3 and
                not (beasts and C.CLASSES[self.hero(h)["cls"]]["map"]["key"] == "wildspeak")]
        if not near:
            return None
        h = min(near, key=lambda h: Wd.dist(at, heroes[h][0]))
        goal = heroes[h][0]
        best = None
        for n in Wd.neighbors(at):
            ter = self.terrain(n)
            if ter not in Wd.COST or ter == "town" or n in occupied or (self.place(n) and n != goal):
                continue
            if Wd.dist(n, goal) < Wd.dist(at, goal) and (best is None or Wd.dist(n, goal) < Wd.dist(best, goal)):
                best = n
        return best

    def forecast(self):
        """What the planned turn will do, worked out from what the party can see: where each hero
        ends up, where the visible enemy groups will step, which fights start and who joins them,
        and what each hero lands on. Hidden enemies can still spring an ambush."""
        s = self.s
        if s["phase"] != "plan":
            return None
        vis = self.visible_tiles()
        pos = {h: (self.hero(h)["tile"], self.hero(h)["afloat"]) for h in self.living()}
        plans = {int(h): p for h, p in s["plans"].items() if int(h) in pos}
        active = {h: list(p["path"]) for h, p in plans.items() if p["path"]}
        encounters = []
        for _ in range(max((len(v) for v in active.values()), default=0)):
            for h in list(active):
                b = active[h].pop(0)
                t, af = pos[h]
                st = self.step_cost(h, t, b, af)
                if st is None:
                    active.pop(h)
                    continue
                pos[h] = (b, st[1])
                g = self.group_at(b)
                if (g and b in vis) or self.is_dungeon(b):
                    encounters.append((b, h))
                    active.pop(h)
                elif not active[h]:
                    active.pop(h)
        tile_of = {g["id"]: g["tile"] for g in s["groups"]}
        steps = []
        for g in s["groups"]:
            occupied = set(tile_of.values())
            best = self.group_step(g, pos, occupied, tile_of)
            if best is None:
                continue
            seen = g["tile"] in vis
            tile_of[g["id"]] = best
            if seen:
                steps.append({"g": g["id"], "from": g["tile"], "to": best})
                if any(t == best and not af for t, af in pos.values()) and best not in [e[0] for e in encounters]:
                    encounters.append((best, None))
        fights, engaged = [], set()
        for tile, by in encounters:
            heroes = [h for h in pos if h not in engaged and Wd.dist(pos[h][0], tile) <= 1]
            if not heroes:
                continue
            engaged.update(heroes)
            p = self.place(tile)
            fight = {"tile": tile, "heroes": heroes, "by": by}
            if p and p["kind"] == "peak":
                fight.update(kind="boss", foes=list(A.FINAL))
            elif p and p["kind"] == "dungeon" and p["region"] not in s["cleared"]:
                fight.update(self.dungeon_spec(p["region"]))
            else:
                main = next((g for g in s["groups"] if tile_of[g["id"]] == tile), None)
                if main is None:
                    continue
                near = [g for g in s["groups"] if g is not main and not g["lair"] and tile_of[g["id"]] in vis
                        and Wd.dist(tile_of[g["id"]], tile) <= 1]
                foes = list(main["foes"])
                for g in near:
                    if len(foes) + len(g["foes"]) <= 5:
                        foes += g["foes"]
                fight.update(kind="lair" if main["lair"] else "roam", foes=foes[:5])
            # the view wants keys, with any elite affixes alongside
            fight["aff"] = [k.get("aff") if isinstance(k, dict) else None for k in fight["foes"]]
            fight["foes"] = [k["k"] if isinstance(k, dict) else k for k in fight["foes"]]
            fights.append(fight)
        lands = {}
        for h, (t, af) in pos.items():
            p = self.place(t)
            if h in engaged or not p or t == self.hero(h)["tile"]:
                continue
            if p["kind"] in ("event", "wreck") and p.get("done"):
                continue
            if p["kind"] == "shrine" and t in self.hero(h)["shrines"]:
                continue
            lands[str(h)] = p["kind"]
        return {"ends": {str(h): t for h, (t, af) in pos.items()}, "steps": steps, "fights": fights, "lands": lands}

    # ------------------------------------------------------------------ planning

    def reset_plans(self):
        self.s["plans"] = {str(h): {"path": [], "ready": False, "rest": False} for h in self.living()}

    def waiting(self):
        """Heroes the game is waiting on right now."""
        s = self.s
        if s["phase"] == "end":
            return []
        out = set(int(h) for h, q in s["pending"].items() if q)
        if s["phase"] == "plan":
            out |= {int(h) for h, p in s["plans"].items() if not p["ready"] and self.hero(int(h))["alive"]}
        elif s["phase"] == "fight" and s["fight"]:
            out |= set(self.fight_waiting())
        elif s["phase"] == "fork" and s.get("fork"):
            out |= {y for y in s["fork"]["heroes"] if str(y) not in s["fork"]["votes"] and self.hero(y)["alive"]}
        return sorted(out)

    def act(self, h, msg):
        """A hero does something. Raises Invalid if they can't."""
        t = msg.get("t")
        if self.s["phase"] == "end":
            raise Invalid("The run is over.")
        if not (0 <= h < 3):
            raise Invalid("No such hero.")
        handler = {
            "path": self.do_path, "ready": self.do_ready, "rest": self.do_rest, "choose": self.do_choose,
            "buy": self.do_buy, "sell": self.do_sell, "inn": self.do_inn, "skiff": self.do_skiff,
            "quest": self.do_quest, "equip": self.do_equip, "unequip": self.do_unequip, "use": self.do_use,
            "give": self.do_give, "drop": self.do_drop,
            "place": self.do_place, "reroll": self.do_reroll,
            "fready": self.do_fready, "spirit": self.do_spirit, "fork": self.do_fork,
        }.get(t)
        if handler is None:
            raise Invalid("Unknown action.")
        handler(h, msg)
        self.sync()

    def plan(self, h):
        p = self.s["plans"].get(str(h))
        if p is None:
            raise Invalid("That hero has no turn to plan.")
        return p

    def can_plan(self, h):
        """Map planning is open in the plan phase, and during fights for heroes outside them."""
        if self.s["phase"] == "plan":
            return True
        f = self.s["fight"]
        if self.s["phase"] == "fork":
            return h not in self.s["fork"]["heroes"]
        return self.s["phase"] in ("fight", "reward") and (not f or h not in f["heroes"])

    def do_path(self, h, msg):
        if not self.can_plan(h):
            raise Invalid("Not now.")
        p = self.plan(h)
        path = [int(t) for t in msg.get("path") or [] if isinstance(t, int) and 0 <= t < Wd.W * Wd.H][:12]
        if path:
            cost = self.path_cost(h, path)
            if cost is None:
                raise Invalid("You can't go that way.")
            if cost > self.moves(h):
                raise Invalid("That's too far for one turn.")
        p["path"], p["rest"], p["ready"] = path, False, False

    def do_rest(self, h, msg):
        if not self.can_plan(h):
            raise Invalid("Not now.")
        p = self.plan(h)
        p["rest"], p["path"], p["ready"] = bool(msg.get("on", True)), [], False

    def do_ready(self, h, msg):
        if self.s["phase"] != "plan":
            raise Invalid("Not now.")
        p = self.plan(h)
        if self.s["pending"][str(h)]:
            raise Invalid("Answer what's in front of you first.")
        p["ready"] = bool(msg.get("on", True))
        if self.all_ready():
            self.resolve_turn()

    def all_ready(self):
        live = {str(h) for h in self.living()}
        self.s["plans"] = {h: p for h, p in self.s["plans"].items() if h in live}
        return all(q["ready"] for q in self.s["plans"].values()) and not any(self.s["pending"].values())

    # ------------------------------------------------------------------ resolving a turn

    def resolve_turn(self):
        s = self.s
        plans = {int(h): p for h, p in s["plans"].items()}
        # Resting
        for h, p in plans.items():
            if p["rest"]:
                self.rest(h)
        # Everyone moves at once, a step at a time; walking into enemies or a dungeon stops you.
        encounters = []  # (tile, who triggered it)
        moved = {h: [self.hero(h)["tile"]] for h in plans}
        steps = max((len(p["path"]) for p in plans.values()), default=0)
        active = {h: list(p["path"]) for h, p in plans.items() if p["path"]}
        for _ in range(steps):
            for h in list(active):
                hero = self.hero(h)
                b = active[h].pop(0)
                st = self.step_cost(h, hero["tile"], b, hero["afloat"])
                if st is None:
                    active.pop(h)
                    continue
                hero["prev"] = hero["tile"]
                hero["tile"], hero["afloat"] = b, st[1]
                moved[h].append(b)
                self.reveal(b, self.vision(h))
                if self.group_at(b) or self.is_dungeon(b):
                    encounters.append((b, h))
                    active.pop(h)
                elif not active[h]:
                    active.pop(h)
        for h, path in moved.items():
            if len(path) > 1:
                self.fx("move", h=h, path=path)
        # Enemies close in.
        for t in self.move_groups():
            if t not in [e[0] for e in encounters]:
                encounters.append((t, None))
        self.reset_plans()
        s["after"] = "turn"
        engaged = set()
        for tile, by in encounters:
            spec = self.encounter(tile, by, engaged)
            if spec:
                s["fights"].append(spec)
        # Landing on places, for heroes not about to fight.
        for h in self.living():
            if h not in engaged:
                self.land(h)
        self.next_step()

    def encounter(self, tile, by, engaged):
        """A fight spec for an encounter at tile: heroes and enemies within a hex join."""
        heroes = [h for h in self.living() if h not in engaged and Wd.dist(self.hero(h)["tile"], tile) <= 1]
        if not heroes:
            return None
        engaged.update(heroes)
        p = self.place(tile)
        if p and p["kind"] == "peak" and len(self.s["cleared"]) >= 3:
            return {"kind": "boss", "tile": tile, "heroes": heroes, "foes": list(A.FINAL), "by": by}
        if p and p["kind"] == "dungeon" and p["region"] not in self.s["cleared"]:
            return dict(self.dungeon_spec(p["region"]), tile=tile, heroes=heroes, by=by)
        groups = [g for g in self.s["groups"] if Wd.dist(g["tile"], tile) <= 1 and not g.get("busy")]
        main = self.group_at(tile)
        if main is None:
            return None
        groups = [main] + [g for g in groups if g is not main and not g["lair"]]
        foes, gids = [], []
        for g in groups:
            if len(foes) + len(g["foes"]) > 5 and foes:
                continue
            g["busy"] = True
            gids.append(g["id"])
            foes += g["foes"]
        return {"kind": "lair" if main["lair"] else "roam", "tile": tile, "heroes": heroes, "groups": gids,
                "foes": foes[:5], "by": by}

    # ------------------------------------------------------------------ dungeons: lineups and forks

    def dungeon_lineup(self, reg, path):
        """Roll the enemies down a dungeon path."""
        D = A.DUNGEONS[reg]
        if path == "open":
            return list(self.rng.choice(D["open"]))
        if path == "passage":
            return list(self.rng.choice(D["mid"]))
        if path == "champion":
            return list(self.rng.choice(D["champ"]))
        if path == "vault":
            foes = list(self.rng.choice(D["mid"]))
            i = self.rng.randint(0, len(foes) - 1)
            foes[i] = {"k": foes[i], "aff": self.rng.choice(A.ROAM_ELITES)}
            return foes
        if path == "shrine":
            return []
        esc = list(self.rng.choice(D["escort"]))
        foes = esc[:1] + [D["boss"]] + esc[1:]
        if path == "rest":
            foes.append(self.rng.choice([k for e in D["escort"] for k in e]))
        return foes

    def dungeon_spec(self, reg):
        """The next fight in a dungeon, as the party will meet it."""
        nxt = self.s["dnext"][reg]
        return {"kind": "dungeon", "region": reg, "step": self.s["dungeon"].get(reg, 0), "foes": list(nxt["foes"]),
                "path": nxt["path"], "ambush_foes": nxt["path"] == "sneak"}

    def make_fork(self, reg, step, tile, heroes):
        """After a dungeon fight: the party picks one of two ways on."""
        paths = self.rng.sample(A.MID_PATHS if step == 1 else A.BOSS_PATHS, 2)
        self.s["fork"] = {"region": reg, "step": step, "tile": tile, "heroes": list(heroes), "votes": {},
                          "opts": [{"path": p, "foes": self.dungeon_lineup(reg, p)} for p in paths]}
        self.say("The way forks. Pick a path.")

    def do_fork(self, h, msg):
        fk = self.s["fork"]
        if self.s["phase"] != "fork" or not fk or h not in fk["heroes"]:
            raise Invalid("There's no fork to choose at.")
        n = msg.get("n")
        if not isinstance(n, int) or not 0 <= n < len(fk["opts"]):
            raise Invalid("Pick one of the paths.")
        fk["votes"][str(h)] = n
        alive = [y for y in fk["heroes"] if self.hero(y)["alive"]]
        if any(str(y) not in fk["votes"] for y in alive):
            return
        tally = {}
        for y in alive:
            tally[fk["votes"][str(y)]] = tally.get(fk["votes"][str(y)], 0) + 1
        top = max(tally.values())
        pick = self.rng.choice(sorted(i for i, c in tally.items() if c == top))
        self.take_path(fk, fk["opts"][pick])
        self.next_step()

    def take_path(self, fk, opt):
        s = self.s
        reg, path = fk["region"], opt["path"]
        s["fork"] = None
        info = A.PATHS[path]
        self.say(f"The party takes {info['name']}.")
        heal = {"shrine": 0.35, "rest": 0.3}.get(path, 0)
        for y in fk["heroes"]:
            hero = self.hero(y)
            if not hero["alive"]:
                continue
            if heal:
                got = min(self.maxhp(y) - hero["hp"], round(self.maxhp(y) * heal))
                hero["hp"] += got
                if got:
                    self.fx("heal", to=f"h{y}", n=got)
            if path == "shrine":
                for b in [b for b in hero["buffs"] if A.BUFFS.get(b, {}).get("curse")]:
                    del hero["buffs"][b]
        s["dungeon"][reg] = fk["step"]
        if path == "shrine":
            self.make_fork(reg, fk["step"] + 1, fk["tile"], fk["heroes"])
            return
        s["dnext"][reg] = {"path": path, "foes": opt["foes"]}
        heroes = [y for y in fk["heroes"] if self.hero(y)["alive"]]
        if heroes:
            s["fights"].insert(0, dict(self.dungeon_spec(reg), tile=fk["tile"], heroes=heroes, by=None))

    def next_step(self):
        """After a turn, a fight or a reward: start the next fight, wait for picks, or go on."""
        s = self.s
        if s["phase"] == "end":
            return
        if any(s["pending"][str(h)] for h in range(3) if self.waiting_reward(h)):
            s["phase"] = "reward"
            return
        if s.get("fork"):
            s["phase"] = "fork"
            return
        if s["fights"]:
            self.start_fight(s["fights"].pop(0))
            return
        for g in s["groups"]:
            g.pop("busy", None)
        if s["after"] == "turn":
            self.begin_turn()
        s["phase"] = "plan"
        s["plans"] = {h: p for h, p in s["plans"].items() if self.hero(int(h))["alive"]}
        for h in self.living():
            if str(h) not in s["plans"]:
                s["plans"][str(h)] = {"path": [], "ready": False, "rest": False}
        # a fight from an event can start mid-plan and take out the only hero not yet ready: then
        # everyone left is ready, so the turn goes on
        if s["after"] == "plan" and s["plans"] and self.all_ready():
            self.resolve_turn()

    def waiting_reward(self, h):
        return any(d["type"] in ("loot", "pool", "level") for d in self.s["pending"][str(h)])

    def begin_turn(self):
        s = self.s
        s["turn"] += 1
        before = self.tide_at(s["turn"] - 1)
        if self.tide() != before:
            self.say("The tide turns: it's " + self.tide() + " tide.")
            self.fx("tide", tide=self.tide())
        if (s["turn"] - 1) % self.diff()["rise"] == 0:
            self.rise()
        if s["phase"] == "end":
            return
        if (s["turn"] - 1) % SPAWN_EVERY == 0 and len(s["groups"]) < MAX_GROUPS:
            self.spawn()
            if s["rises"] > GROW_FROM:
                self.spawn()
        for h in range(3):
            hero = self.hero(h)
            for b in list(hero["buffs"]):
                hero["buffs"][b] -= 1
                if hero["buffs"][b] <= 0:
                    del hero["buffs"][b]
            hero["hp"] = min(hero["hp"], self.maxhp(h))
        # A dead hero comes back if there's a revive to spend.
        alive = self.living()
        for h in range(3):
            if not self.hero(h)["alive"] and s["revives"] > 0 and alive:
                s["revives"] -= 1
                hero = self.hero(h)
                hero["alive"] = True
                hero["tile"] = hero["prev"] = self.hero(alive[0])["tile"]
                hero["afloat"] = self.hero(alive[0])["afloat"]
                hero["hp"] = max(1, self.maxhp(h) // 4)
                self.say(f"{hero['name']} is back on their feet.")
        self.keep_plans()

    def keep_plans(self):
        """A new turn: keep paths pre-planned during fights if they still work, unready everyone."""
        old = self.s["plans"]
        self.s["plans"] = {}
        for h in self.living():
            p = old.get(str(h)) or {"path": [], "ready": False, "rest": False}
            if p["path"]:
                cost = self.path_cost(h, p["path"])
                if cost is None or cost > self.moves(h):
                    p["path"] = []
            p["ready"] = False
            self.s["plans"][str(h)] = p

    def tide_at(self, turn):
        return "low" if ((turn - 1) // TIDE_EVERY) % 2 == 0 else "high"

    def rise(self):
        """The tide rises: every enemy met from now on is a little stronger (`surge`). The land
        stays as it is: the sea never floods hexes or sinks places."""
        s = self.s
        s["rises"] += 1
        self.fx("rise", rises=s["rises"])
        self.say(f"The tide rises. Enemies are now {round(SURGE * s['rises'] * 100)}% stronger.")
        if s["rises"] == GROW_FROM + 1:
            self.say("More enemies come ashore with every rise now.")

    def surge(self):
        """How much stronger enemies are for the tide having risen: HP and damage both."""
        return 1 + SURGE * self.s["rises"]

    def rest(self, h):
        hero = self.hero(h)
        hero["spent"] = []  # once-per-rest actions (Lift) come back
        p = self.place(hero["tile"])
        medic = any(C.CLASSES[self.hero(x)["cls"]]["map"]["key"] == "field_medic" and self.hero(x)["tile"] == hero["tile"]
                    for x in self.living())
        key = C.CLASSES[hero["cls"]]["map"]["key"]
        frac = 0.5 if p and p["kind"] == "camp" else 0.2
        if key == "forage" and p and p["kind"] == "camp":
            frac = 1
        if medic:
            frac = min(1, frac + 0.1)
        frac = min(1, frac + self.mods(h).get("rest_bonus", 0))
        n = self.heal(h, int(self.maxhp(h) * frac + 0.5))
        self.fx("heal", to=f"h{h}", n=n)
        self.say(f"{hero['name']} rests (+{n} HP).")
        if key == "brewer":
            for _ in range(2 if self.mods(h).get("distiller") else 1):
                hero["bag"].append("potion")

    # ------------------------------------------------------------------ places

    def land(self, h):
        hero = self.hero(h)
        t = hero["tile"]
        p = self.place(t)
        if not p:
            return
        k = p["kind"]
        if k == "event" and not p.get("done"):
            ev = self.pick_event(h)
            p["done"] = True
            self.push(h, {"type": "event", "key": ev["key"]})
        elif k == "wreck" and not p.get("done"):
            p["done"] = True
            n = 2 + (1 if C.CLASSES[hero["cls"]]["map"]["key"] == "light_fingers" else 0)
            self.offer_loot(h, n, tier_bonus=0)
            self.say(f"{hero['name']} picks through a wreck.")
        elif k == "shrine" and t not in hero["shrines"]:
            if "buff" not in p:
                p["buff"] = self.rng.choice(A.SHRINE_BUFFS)
            hero["shrines"].append(t)
            self.buff(h, p["buff"])
        elif k == "town":
            for q in self.s["quests"]:
                if q["kind"] == "deliver" and q["to"] == t and not q["done"]:
                    self.complete_quest(q, h)

    def buff(self, h, key):
        b = A.BUFFS[key]
        self.hero(h)["buffs"][key] = b["turns"]
        self.say(f"{self.hero(h)['name']}: {b['name']} ({b['text']})")
        self.fx("buff", h=h, b=key)

    def push(self, h, dialog):
        self.s["pending"][str(h)].append(dialog)

    def pick_event(self, h):
        done = {d.get("key") for d in self.s.get("events_seen", [])}
        fresh = [e for e in A.EVENTS if e["key"] not in done] or A.EVENTS
        e = self.rng.choice(fresh)
        self.s.setdefault("events_seen", []).append({"key": e["key"]})
        return e

    def do_choose(self, h, msg):
        q = self.s["pending"][str(h)]
        if not q:
            raise Invalid("Nothing to choose.")
        d = q[0]
        n = msg.get("n")
        if d["type"] == "event":
            ev = next(e for e in A.EVENTS if e["key"] == d["key"])
            if not isinstance(n, int) or not 0 <= n < len(ev["choices"]):
                raise Invalid("Pick one of the choices.")
            ch = ev["choices"][n]
            hero = self.hero(h)
            if ch.get("need") and not self.has_class(ch["need"]):
                raise Invalid("Nobody in the party can do that.")
            if ch.get("cost", 0) > hero["gold"]:
                raise Invalid("You can't afford that.")
            hero["gold"] -= ch.get("cost", 0)
            q.pop(0)
            out = ch["ok"]
            roll = None
            if ch.get("check"):
                roll = self.event_roll(h, ch["check"])
                if not roll["ok"]:
                    out = ch["bad"]
                elif ch.get("great") and roll.get("great"):
                    out = ch["great"]
            self.outcome(h, out, ev, roll)
        elif d["type"] == "loot":
            if n is None or n == -1:
                q.pop(0)
            elif isinstance(n, int) and 0 <= n < len(d["opts"]):
                to = self.loot_to(h, d["opts"][n], msg)
                q.pop(0)
                self.take_loot(h, d["opts"][n], to, msg.get("equip"))
            else:
                raise Invalid("Pick an item, or skip.")
        elif d["type"] == "pool":
            pool = self.s["pools"][str(d["id"])]
            if n is None or n == -1:
                q.pop(0)
            elif isinstance(n, int) and 0 <= n < len(pool["items"]):
                if str(n) in pool["taken"]:
                    raise Invalid("Someone has already claimed that.")
                to = self.loot_to(h, pool["items"][n], msg)
                q.pop(0)
                pool["taken"][str(n)] = {"by": h, "to": to}
                self.take_loot(h, pool["items"][n], to, msg.get("equip"))
            else:
                raise Invalid("Claim an item, or pass.")
            self.close_pool(d["id"])
        elif d["type"] == "level":
            if not isinstance(n, int) or not 0 <= n < len(d["opts"]):
                raise Invalid("Pick one.")
            self.learn(h, d["opts"][n])
            q.pop(0)
        if self.s["phase"] == "reward" and not any(self.waiting_reward(x) for x in range(3)):
            self.next_step()
        elif self.s["phase"] == "plan" and self.all_ready():
            self.resolve_turn()

    def event_die(self, h, which):
        """The die an event check rolls: a slot's item die (a bare d4 with nothing there), or the
        hero's best die."""
        from .dice import top_face
        dice = self.dice_of(h)
        if which in ("weapon", "armor", "trinket"):
            d = next((d for d in dice if d["src"] == which), None)
            return d["faces"] if d else [1, 2, 3, 4]
        return max((d["faces"] for d in dice), key=top_face)

    def event_roll(self, h, spec):
        """Roll an event check. `spec` is a number (best die, that much or more) or {die: weapon,
        armor, trinket, best or party (the best die of anyone on your hex), n: the target, vs: an
        opponent's die size to beat instead, great: a roll for the best outcome}."""
        from .dice import face, top_face
        if isinstance(spec, int):
            spec = {"n": spec}
        which = spec.get("die", "best")
        roller = h
        if which == "party":
            here = [x for x in self.living() if self.hero(x)["tile"] == self.hero(h)["tile"]]
            roller = max(here, key=lambda x: top_face(self.event_die(x, "best")))
            which = "best"
        faces = self.event_die(roller, which)
        v, t = face(self.roll_face(faces))
        v = (top_face(faces) if t == "W" else v) + self.mods(roller).get("silver_voice", 0)
        out = {"v": v, "die": which, "faces": faces, "by": roller}
        if spec.get("vs"):
            opp = self.rng.randint(1, spec["vs"])
            out.update(opp=opp, vs=spec["vs"], ok=v > opp)
        else:
            out.update(need=spec.get("n", 4), ok=v >= spec.get("n", 4))
        if spec.get("great"):
            out["great"] = v >= spec["great"]
            out["great_at"] = spec["great"]
        return out

    def has_class(self, k):
        return any(self.hero(h)["cls"] == k for h in self.living())

    def roll_face(self, faces):
        return faces[self.rng.next() % len(faces)]

    def outcome(self, h, out, ev, roll):
        hero = self.hero(h)
        bits = []
        if out.get("all"):
            # good fortune shared with everyone standing on this hex
            for x in self.living():
                if x != h and self.hero(x)["tile"] == hero["tile"]:
                    if out.get("hp", 0) > 0:
                        self.heal(x, out["hp"])
                    if out.get("buff"):
                        self.buff(x, out["buff"])
                    bits.append(f"{self.hero(x)['name']} too")
        if out.get("skiff") and not hero["skiff"]:
            hero["skiff"] = True
            bits.append("a skiff")
        if out.get("gold"):
            hero["gold"] = max(0, hero["gold"] + out["gold"])
            bits.append(f"{out['gold']:+d} gold")
        if out.get("hp"):
            if out["hp"] > 0:
                n = self.heal(h, out["hp"])
                bits.append(f"+{n} HP")
            else:
                hero["hp"] = max(1, hero["hp"] + out["hp"])
                bits.append(f"{out['hp']} HP")
        if out.get("potion"):
            for _ in range(out["potion"]):
                self.gain_item(h, "potion")
        if out.get("buff"):
            self.buff(h, out["buff"])
        if out.get("revive"):
            self.s["revives"] += out["revive"]
            bits.append("+1 revive")
        if out.get("xp"):
            self.gain_xp(out["xp"])
            bits.append(f"+{out['xp']} XP")
        if out.get("item"):
            self.offer_loot(h, 2, rarity=out["item"])
        self.fx("event", h=h, key=ev["key"], text=out.get("text", ""), roll=roll, bits=bits)
        self.say(f"{hero['name']} — {ev['title']}: {out.get('text', '')}" + (f" ({', '.join(bits)})" if bits else ""))
        if out.get("fight"):
            # anyone on or next to the hex (and not already in a fight) joins in
            busy = {y for fs in self.s["fights"] for y in fs["heroes"]} | set((self.s["fight"] or {}).get("heroes", []))
            heroes = [h] + [y for y in self.living() if y != h and y not in busy
                            and Wd.dist(self.hero(y)["tile"], hero["tile"]) <= 1]
            self.s["fights"].append({"kind": "event", "tile": hero["tile"], "heroes": heroes, "foes": list(out["fight"]), "by": h})
            if self.s["phase"] == "plan":
                self.s["after"] = "plan"
                self.next_step()

    # ------------------------------------------------------------------ loot, xp and levels

    def rarity_for(self, bonus=0):
        tier = self.tier() + bonus
        weights = [("common", max(1, 6 - tier * 2)), ("uncommon", 3 + tier), ("rare", max(0, tier * 2 - 1)),
                   ("legendary", max(0, tier - 2))]
        return self.rng.weighted(weights)

    def loot_to(self, h, key, msg):
        """Who loot goes to: the hero, or an ally within a hex (anyone who could have joined the
        fight) whose bag has room. Raises Invalid if they can't take it."""
        to = msg.get("to", h)
        if to == h:
            return h
        if not isinstance(to, int) or not 0 <= to < 3 or not self.hero(to)["alive"]:
            raise Invalid("Give it to whom?")
        if Wd.dist(self.hero(to)["tile"], self.hero(h)["tile"]) > 1:
            raise Invalid("They're too far away.")
        return to

    def take_loot(self, h, key, to, equip):
        if to != h:
            self.say(f"{self.hero(h)['name']} hands the {I.ITEMS[key]['name']} to {self.hero(to)['name']}.")
        if equip and I.ITEMS[key]["slot"] != "use":
            self.wear(to, key)
        else:
            self.gain_item(to, key)

    def offer_pool(self, counts, tier_bonus=0):
        """After a fight: one pool of loot for everyone who won it, bigger than the picks they'd
        have had alone (`counts`: {hero: how many picks}). Each claims one item (or passes), first
        come first served; what nobody claims is left behind."""
        heroes = list(counts)
        if not heroes:
            return
        s = self.s
        pid = s["poolid"] = s.get("poolid", 0) + 1
        items = self.make_loot(sum(counts.values()) + POOL_EXTRA, tier_bonus)
        s.setdefault("pools", {})[str(pid)] = {"items": items, "taken": {}, "heroes": heroes}
        for h in heroes:
            self.push(h, {"type": "pool", "id": pid})

    def close_pool(self, pid):
        """Forget a pool once nobody has its dialog left to answer."""
        if not any(d["type"] == "pool" and d["id"] == pid for q in self.s["pending"].values() for d in q):
            pool = self.s["pools"].pop(str(pid))
            left = len(pool["items"]) - len(pool["taken"])
            if left:
                self.say(f"{left} unclaimed item{'s' if left > 1 else ''} left behind.")

    def offer_loot(self, h, n, tier_bonus=0, rarity=None):
        self.push(h, {"type": "loot", "opts": self.make_loot(n, tier_bonus, rarity)})

    def make_loot(self, n, tier_bonus=0, rarity=None):
        opts = []
        for _ in range(n * 3):
            if len(opts) >= n:
                break
            r = rarity or self.rarity_for(tier_bonus)
            pool = [k for k in I.GEAR if I.ITEMS[k]["rarity"] == r and k not in opts] or \
                [k for k in I.GEAR if k not in opts]
            if self.rng.chance(0.2):
                pool = [k for k in I.CONSUMABLES if k not in opts] or pool
            opts.append(self.rng.choice(pool))
        return opts

    def gain_item(self, h, key):
        hero = self.hero(h)
        it = I.ITEMS[key]
        slot = it["slot"]
        if slot != "use" and hero["equip"].get(slot) is None:
            hero["equip"][slot] = key
        else:
            hero["bag"].append(key)
        self.say(f"{hero['name']} gets {it['name']}.")
        if slot != "use" and slot in hero["equip"] and hero["equip"][slot] != key:
            pass

    def gain_xp(self, n):
        s = self.s
        old = s["level"]
        s["xp"] += n
        new = min(C.level_for(s["xp"]), C.MAX_LEVEL)
        if new > old:
            for lvl in range(old + 1, new + 1):
                s["level"] = lvl
                for h in range(3):
                    hero = self.hero(h)
                    hero["hp"] = min(self.maxhp(h), hero["hp"] + C.CLASSES[hero["cls"]]["hp_lvl"])
                    if lvl in C.DIE_UP_LEVELS:
                        hero["dieup"] += 1
                    self.push(h, {"type": "level", "lvl": lvl, "opts": self.level_offer(h, lvl)})
            self.say(f"The party reaches level {new}!")
            self.fx("level", lvl=new)

    def level_offer(self, h, lvl):
        hero = self.hero(h)
        c = C.CLASSES[hero["cls"]]
        owned = {k.rstrip("+") for k in hero["skills"]}
        pending = set()
        for d in self.s["pending"][str(h)]:
            if d["type"] == "level":
                pending |= {o.rstrip("+") for o in d["opts"]}
        cands = []
        for k in c["pool"]:
            sk = C.skill_def(k)
            if k in owned or (sk.get("cap") and lvl < 6):
                continue
            w = 1 + sum(hero["tags"].get(t, 0) for t in sk.get("tags", []))
            if sk.get("cap"):
                w += 1
            cands.append((k, w))
        for k in hero["skills"]:
            if k in C.ACTIONS and k not in C.GENERIC:
                cands.append((k + "+", 0.6))
        cands = [(k, w) for k, w in cands if k.rstrip("+") not in pending or k.endswith("+")]
        out = []
        while cands and len(out) < 3:
            k = self.rng.weighted(cands)
            out.append(k)
            cands = [(x, w) for x, w in cands if x != k]
        return out

    def learn(self, h, key):
        hero = self.hero(h)
        base = key.rstrip("+")
        if key.endswith("+"):
            hero["skills"] = [k + "+" if k == base else k for k in hero["skills"]]
        else:
            hero["skills"].append(base)
        for t in C.skill_def(base).get("tags", []):
            hero["tags"][t] = hero["tags"].get(t, 0) + 1
        hero["hp"] = min(hero["hp"] + max(0, C.skill_def(base)["mods"].get("max_hp", 0)) if base in C.PASSIVES else hero["hp"],
                         self.maxhp(h))
        self.say(f"{hero['name']} learns {C.skill_def(base)['name']}{'+' if key.endswith('+') else ''}.")

    # ------------------------------------------------------------------ towns, items and trading

    def town(self, h):
        p = self.place(self.hero(h)["tile"])
        if not p or p["kind"] != "town":
            raise Invalid("You're not in a town.")
        if not self.can_plan(h):
            raise Invalid("Not now.")
        return p

    def shop(self, t):
        key = str(t)
        if key not in self.s["shops"]:
            stock = []
            for _ in range(5):
                r = self.rarity_for(1)
                pool = [k for k in I.GEAR if I.ITEMS[k]["rarity"] == r and k not in stock] or I.GEAR
                stock.append(self.rng.choice(pool))
            self.s["shops"][key] = stock + ["potion", "big_potion", "bomb", "ward_scroll", "smelling_salts"]
        return self.s["shops"][key]

    def price_for(self, h, key):
        p = I.price(key)
        if self.has_class("herald"):
            p = p * 8 // 10
        return p

    def do_buy(self, h, msg):
        self.town(h)  # checks the hero can shop
        t = self.hero(h)["tile"]
        stock = self.shop(t)
        key = msg.get("item")
        if key not in stock:
            raise Invalid("That's not for sale here.")
        hero = self.hero(h)
        cost = self.price_for(h, key)
        if hero["gold"] < cost:
            raise Invalid("You can't afford that.")
        hero["gold"] -= cost
        if key not in I.CONSUMABLES:
            stock.remove(key)
        self.gain_item(h, key)
        self.fx("coins", h=h, n=-cost)

    def sell_price(self, h, key):
        """What an item sells for: 40% of its price, 60% with Haggler."""
        return I.price(key) * self.sell_rate(h) // 100

    def sell_rate(self, h):
        return 60 if self.mods(h).get("haggler") else 40

    def do_sell(self, h, msg):
        self.town(h)
        hero = self.hero(h)
        i = msg.get("bag")
        if not isinstance(i, int) or not 0 <= i < len(hero["bag"]):
            raise Invalid("Sell what?")
        key = hero["bag"].pop(i)
        n = self.sell_price(h, key)
        hero["gold"] += n
        self.say(f"{hero['name']} sells {I.ITEMS[key]['name']} for {n} gold.")

    def do_inn(self, h, msg):
        self.town(h)
        hero = self.hero(h)
        cost = self.inn_cost()
        if hero["hp"] >= self.maxhp(h):
            raise Invalid("You're already rested.")
        if hero["gold"] < cost:
            raise Invalid("You can't afford a room.")
        hero["gold"] -= cost
        hero["spent"] = []
        n = self.heal(h, self.maxhp(h))
        self.fx("heal", to=f"h{h}", n=n)
        self.say(f"{hero['name']} takes a room at the inn (+{n} HP).")

    def inn_cost(self):
        return INN_COST * 8 // 10 if self.has_class("herald") else INN_COST

    def docks(self, t):
        return any(self.terrain(n) in ("deep", "shoal") for n in Wd.neighbors(t))

    def do_skiff(self, h, msg):
        self.town(h)
        hero = self.hero(h)
        if hero["skiff"]:
            raise Invalid("You already have a skiff.")
        if not self.docks(hero["tile"]):
            raise Invalid("There are no docks here.")
        if hero["gold"] < SKIFF_COST:
            raise Invalid("You can't afford a skiff.")
        hero["gold"] -= SKIFF_COST
        hero["skiff"] = True
        self.say(f"{hero['name']} buys a skiff.")

    def town_quest(self, t):
        """The quest a town offers, made on first asking."""
        p = self.place(t)
        if "quest" not in p:
            lairs = [g for g in self.s["groups"] if g["lair"]]
            towns = [int(k) for k, q in self.s["world"]["places"].items() if q["kind"] == "town" and int(k) != t]
            if lairs and self.rng.chance(0.6):
                g = min(lairs, key=lambda g: Wd.dist(g["tile"], t))
                p["quest"] = {"kind": "lair", "group": g["id"], "tile": g["tile"]}
            elif towns:
                to = self.rng.choice(towns)
                p["quest"] = {"kind": "deliver", "to": to, "name": self.place(to)["name"]}
            else:
                p["quest"] = None
        return p["quest"]

    def do_quest(self, h, msg):
        p = self.town(h)
        q = self.town_quest(self.hero(h)["tile"])
        if not q or p.get("quest_taken"):
            raise Invalid("There's no work going here.")
        p["quest_taken"] = True
        quest = dict(q, done=False, src=p["name"])
        self.s["quests"].append(quest)
        self.say(f"{self.hero(h)['name']} takes a job in {p['name']}.")

    def complete_quest(self, q, h):
        q["done"] = True
        for x in self.living():
            self.hero(x)["gold"] += A.QUEST_REWARD
        self.offer_loot(h, 2, tier_bonus=1)
        self.say(f"Job done for {q['src']}: +{A.QUEST_REWARD} gold each.")

    def wear(self, h, key):
        """Put new gear straight on; what it replaces goes in the bag."""
        hero = self.hero(h)
        slot = I.ITEMS[key]["slot"]
        old = hero["equip"].get(slot)
        hero["equip"][slot] = key
        if old:
            hero["bag"].append(old)
        hero["hp"] = min(hero["hp"], self.maxhp(h))
        self.say(f"{hero['name']} puts on the {I.ITEMS[key]['name']}.")

    def do_equip(self, h, msg):
        if self.in_fight(h):
            raise Invalid("Not in the middle of a fight.")
        hero = self.hero(h)
        i = msg.get("bag")
        if not isinstance(i, int) or not 0 <= i < len(hero["bag"]):
            raise Invalid("Equip what?")
        key = hero["bag"][i]
        slot = I.ITEMS[key]["slot"]
        if slot == "use":
            raise Invalid("That's not something you wear.")
        old = hero["equip"].get(slot)
        hero["bag"][i:i + 1] = [old] if old else []
        hero["equip"][slot] = key
        hero["hp"] = min(hero["hp"], self.maxhp(h))

    def do_unequip(self, h, msg):
        if self.in_fight(h):
            raise Invalid("Not in the middle of a fight.")
        hero = self.hero(h)
        slot = msg.get("slot")
        if slot not in ("armor", "trinket") or not hero["equip"].get(slot):
            raise Invalid("You can't take that off.")
        hero["bag"].append(hero["equip"][slot])
        hero["equip"][slot] = None
        hero["hp"] = min(hero["hp"], self.maxhp(h))

    def do_drop(self, h, msg):
        hero = self.hero(h)
        i = msg.get("bag")
        if not isinstance(i, int) or not 0 <= i < len(hero["bag"]):
            raise Invalid("Drop what?")
        hero["bag"].pop(i)

    def do_give(self, h, msg):
        if self.in_fight(h):
            raise Invalid("Not in the middle of a fight.")
        hero = self.hero(h)
        to = msg.get("to")
        if not isinstance(to, int) or to == h or not 0 <= to < 3 or not self.hero(to)["alive"]:
            raise Invalid("Give it to whom?")
        other = self.hero(to)
        if other["tile"] != hero["tile"]:
            raise Invalid("You need to be on the same hex to trade.")
        if "gold" in msg:
            n = msg["gold"]
            if not isinstance(n, int) or not 0 < n <= hero["gold"]:
                raise Invalid("How much?")
            hero["gold"] -= n
            other["gold"] += n
            return
        i = msg.get("bag")
        if not isinstance(i, int) or not 0 <= i < len(hero["bag"]):
            raise Invalid("Give what?")
        other["bag"].append(hero["bag"].pop(i))

    def do_use(self, h, msg):
        hero = self.hero(h)
        i = msg.get("bag")
        if not isinstance(i, int) or not 0 <= i < len(hero["bag"]):
            raise Invalid("Use what?")
        key = hero["bag"][i]
        it = I.ITEMS[key]
        if it["slot"] != "use":
            raise Invalid("You can't use that.")
        if self.in_fight(h):
            self.fight_use(h, i, msg.get("tgt"))
            return
        if it.get("fight"):
            raise Invalid("That's for fights.")
        to = msg.get("to", h)
        if not isinstance(to, int) or not 0 <= to < 3 or not self.hero(to)["alive"] or self.hero(to)["tile"] != hero["tile"]:
            raise Invalid("Use it on whom?")
        hero["bag"].pop(i)
        n = self.heal(to, int(it["use"]["heal"]))
        self.fx("heal", to=f"h{to}", n=n)

    # ------------------------------------------------------------------ the end

    def end(self, result):
        self.s["phase"] = "end"
        self.s["result"] = result
        self.s["fight"] = None
        self.fx("end", result=result)

    # ------------------------------------------------------------------ what players see

    def view(self):
        s = self.s
        vis = self.visible_tiles()
        groups = [{"id": g["id"], "tile": g["tile"], "lair": g["lair"], "foes": [f["k"] for f in g["foes"]],
                   "aff": [f.get("aff") for f in g["foes"]]}
                  for g in s["groups"] if g["tile"] in vis or (g["lair"] and s["seen"][g["tile"]])]
        heroes = []
        for h in range(3):
            hero = s["heroes"][h]
            heroes.append({**{k: v for k, v in hero.items() if k not in ("tags",)}, "maxhp": self.maxhp(h),
                           "moves": self.moves(h), "sight": self.enemy_sight(h), "dice": [{"faces": d["faces"], "dk": d["dk"], "src": d["src"]} for d in self.dice_of(h)], "sellrate": self.sell_rate(h),
                           "actions": self.actions_of(h)})
        places = {}
        for t, p in s["world"]["places"].items():
            if s["seen"][int(t)]:
                q = {k: v for k, v in p.items() if k not in ("quest",)}
                if p["kind"] == "town":
                    q["docks"] = self.docks(int(t))
                    if any(self.hero(x)["tile"] == int(t) for x in self.living()):
                        q["shop"] = self.shop(int(t))
                        q["quest"] = None if p.get("quest_taken") else self.town_quest(int(t))
                places[t] = q
        return {
            "turn": s["turn"], "sea": s["sea"], "rises": s["rises"], "tide": self.tide(), "phase": s["phase"],
            "result": s["result"], "diff": s["diff"], "rise_every": self.diff()["rise"],
            "grow_from": GROW_FROM, "surge": round(SURGE * s["rises"] * 100), "next_tide": TIDE_EVERY - (s["turn"] - 1) % TIDE_EVERY,
            "next_rise": self.diff()["rise"] - (s["turn"] - 1) % self.diff()["rise"],
            "seen": "".join(map(str, s["seen"])), "places": places, "groups": groups, "heroes": heroes,
            "xp": s["xp"], "level": s["level"], "xp_next": C.XP_FOR[s["level"]] if s["level"] < C.MAX_LEVEL else None,
            "xp_this": C.XP_FOR[s["level"] - 1], "revives": s["revives"], "cleared": s["cleared"],
            "dungeon": s["dungeon"], "fork": s.get("fork"), "dnext": s.get("dnext", {}), "plans": s["plans"], "pending": s["pending"], "pools": s.get("pools", {}), "fight": self.fight_view(),
            "forecast": self.forecast(),
            "quests": s["quests"], "log": s["log"][-12:], "fx": s["fx"][-60:],
            "stats": s["stats"], "waiting": self.waiting(), "inn": self.inn_cost(),
            "skiff_cost": SKIFF_COST, "herald": self.has_class("herald"),
        }


def static():
    """Content the browser needs once: classes, actions, items, foes, events, buffs."""
    acts = {k: {**v, "def": C.is_defensive(v), "short": C.SHORT.get(k)} for k, v in {**I.WEAPON_ACTIONS, **C.ACTIONS}.items()}
    return {
        "classes": C.CLASSES, "actions": acts, "passives": C.PASSIVES, "items": I.ITEMS, "foes": A.FOES,
        "events": {e["key"]: e for e in A.EVENTS}, "buffs": A.BUFFS, "regions": A.REGION_NAMES,
        "dungeons": {k: v["name"] for k, v in A.DUNGEONS.items()}, "paths": A.PATHS, "elites": A.ELITES, "combos": C.COMBOS, "xp_for": C.XP_FOR,
        "prices": {k: I.price(k) for k in I.ITEMS},
        "map": {"w": Wd.W, "h": Wd.H, "cost": Wd.COST, "fast": Wd.FAST},
    }
