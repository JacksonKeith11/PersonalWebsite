"""A Saltbound run: the whole game state and its rules, outside of fights (see combat.py).

The state is one JSON-able dict (`Game.s`), so saving is `json.dumps(game.s)`. The game never
waits on a clock: it changes only when a hero acts (`Game.act`), and `Game.waiting()` says who it
is waiting on. Every hero sees the same state (vision is shared), so `Game.view()` is one dict
for everyone.

A map turn: every living hero plans a path (or rests) and readies up; then everyone moves at
once, enemies close in, fights start where heroes and enemies meet (every hero within a hex
joins), and landing on a place (an event, a wreck, a shrine) queues a dialog for that hero. Then
the next turn begins: the tide may turn and the sea may rise.

Phases: `plan` (map turns), `fight`, `reward` (after a fight, until everyone's picks are made),
`end`.
"""

from . import classes as C
from . import world as Wd
from .combat import Combat, Invalid
from .content import archipelago as A
from .content import items as I
from .rng import Rng

VERSION = 1
DIFFICULTY = {
    "story": {"rise": 4, "revives": 4, "foe_hp": 1.0, "foe_dmg": 0.95},
    "normal": {"rise": 3, "revives": 3, "foe_hp": 1.9, "foe_dmg": 1.75},
    "hard": {"rise": 3, "revives": 2, "foe_hp": 2.2, "foe_dmg": 2.1},
}
MOVES = 4
VISION = 2
GROW_FROM = 10  # after this many rises the Drowned Crown grows and more enemies come
LOSS_RISE = 15  # the peak floods: the run is lost
TIDE_EVERY = 4
SPAWN_EVERY = 4
MAX_GROUPS = 12
INN_COST = 8
SKIFF_COST = 10
START_GOLD = 20
BAG = 4
FLOOD_DAMAGE = 4
LOG_KEEP = 40
FX_KEEP = 200


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
            "groups": [], "gid": 1, "plans": {}, "pending": {"0": [], "1": [], "2": []}, "fights": [],
            "fight": None, "after": "turn", "quests": [], "shops": {}, "fx": [], "fxid": 0, "log": [],
            "stats": [{"dmg": 0, "heal": 0, "kills": 0, "taken": 0} for _ in range(3)], "fid": 1,
        }
        g = cls(s)
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
        w = hero["equip"].get("weapon")
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

    def bag_size(self, h):
        return BAG + self.mods(h).get("bag", 0)

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
        key = C.CLASSES[hero["cls"]]["map"]["key"]
        if key == "trailbreaker" and t in ("forest", "hills", "peak"):
            cost = 1
        if key == "wildspeak" and t == "forest":
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
        return self.vision(h) + 1 + (2 if C.CLASSES[self.hero(h)["cls"]]["map"]["key"] == "tracker" else 0)

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
        g = {"id": self.s["gid"], "tile": t, "foes": [{"k": k} for k in foes], "lair": lair,
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
        self.add_group(t, list(self.rng.choice(pool[lo:hi])))

    def move_groups(self):
        """Enemies near a hero on land take a step toward them. Returns tiles where they caught someone."""
        caught = []
        heroes = [h for h in self.living() if not self.hero(h)["afloat"]]
        for g in self.s["groups"]:
            if g["lair"]:
                continue
            beasts = all(A.FOES[f["k"]].get("beast") for f in g["foes"])
            near = [h for h in heroes if Wd.dist(g["tile"], self.hero(h)["tile"]) <= 3 and
                    not (beasts and C.CLASSES[self.hero(h)["cls"]]["map"]["key"] == "wildspeak")]
            if not near:
                continue
            h = min(near, key=lambda h: Wd.dist(g["tile"], self.hero(h)["tile"]))
            goal = self.hero(h)["tile"]
            best = None
            for n in Wd.neighbors(g["tile"]):
                ter = self.terrain(n)
                if ter not in Wd.COST or ter == "town" or self.group_at(n) or (self.place(n) and n != goal):
                    continue
                if Wd.dist(n, goal) < Wd.dist(g["tile"], goal) and (best is None or Wd.dist(n, goal) < Wd.dist(best, goal)):
                    best = n
            if best is not None:
                self.fx("gmove", g=g["id"], path=[g["tile"], best])
                g["tile"] = best
                if any(self.hero(x)["tile"] == best for x in heroes):
                    caught.append(best)
        return caught

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
            "place": self.do_place, "unplace": self.do_unplace, "reroll": self.do_reroll,
            "fready": self.do_fready, "spirit": self.do_spirit,
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
            step = self.s["dungeon"].get(p["region"], 0)
            return {"kind": "dungeon", "tile": tile, "heroes": heroes, "region": p["region"], "step": step,
                    "foes": list(A.DUNGEONS[p["region"]]["fights"][step]), "by": by}
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

    def next_step(self):
        """After a turn, a fight or a reward: start the next fight, wait for picks, or go on."""
        s = self.s
        if s["phase"] == "end":
            return
        if any(s["pending"][str(h)] for h in range(3) if self.waiting_reward(h)):
            s["phase"] = "reward"
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

    def waiting_reward(self, h):
        return any(d["type"] in ("loot", "level") for d in self.s["pending"][str(h)])

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
        s = self.s
        s["rises"] += 1
        s["sea"] += 1
        if s["rises"] >= LOSS_RISE:
            self.say("The sea closes over the peak. The Drowned Crown has won.")
            self.end("lost")
            return
        w = s["world"]
        flooded = [t for t in range(Wd.W * Wd.H) if w["elev"][t] == s["sea"] + 1 or w["elev"][t] == s["sea"]]
        self.fx("rise", sea=s["sea"])
        for t in flooded:
            p = self.place(t)
            if p and w["elev"][t] <= s["sea"] + 1 and p["kind"] != "peak" and p["kind"] != "dungeon":
                if p["kind"] == "town":
                    self.say(f"{p['name']} sinks beneath the waves.")
                del w["places"][str(t)]
        for g in list(s["groups"]):
            if self.terrain(g["tile"]) in ("deep", "shoal"):
                s["groups"].remove(g)
        for h in self.living():
            hero = self.hero(h)
            if self.terrain(hero["tile"]) == "deep" and not hero["afloat"]:
                if hero["skiff"]:
                    hero["afloat"] = True
                else:
                    dry = min((t for t in Wd.within(hero["tile"], 6) if self.terrain(t) in Wd.COST),
                              key=lambda t: Wd.dist(t, hero["tile"]), default=None)
                    if dry is not None:
                        self.fx("move", h=h, path=[hero["tile"], dry])
                        hero["tile"] = hero["prev"] = dry
                    hero["hp"] = max(1, hero["hp"] - FLOOD_DAMAGE)
                    self.say(f"{hero['name']} is swept ashore by the flood (−{FLOOD_DAMAGE} HP).")
        if s["rises"] == GROW_FROM + 1:
            self.say("The Drowned Crown grows stronger with every rise now.")
        else:
            self.say(f"The sea rises. {LOSS_RISE - s['rises']} rises until the peak goes under.")

    def floods_next(self):
        """Tiles that become impassable shallows at the next rise, if it's next turn."""
        s = self.s
        if s["turn"] % self.diff()["rise"] != 0:
            return []
        return [t for t in range(Wd.W * Wd.H) if s["world"]["elev"][t] == s["sea"] + 2]

    def rest(self, h):
        hero = self.hero(h)
        p = self.place(hero["tile"])
        medic = any(C.CLASSES[self.hero(x)["cls"]]["map"]["key"] == "field_medic" and self.hero(x)["tile"] == hero["tile"]
                    for x in self.living())
        key = C.CLASSES[hero["cls"]]["map"]["key"]
        frac = 0.5 if (p and p["kind"] == "camp") or medic else 0.2
        if key == "forage" and p and p["kind"] == "camp":
            frac = 1
        n = self.heal(h, int(self.maxhp(h) * frac + 0.5))
        self.fx("heal", to=f"h{h}", n=n)
        self.say(f"{hero['name']} rests (+{n} HP).")
        if key == "brewer":
            for _ in range(2 if self.mods(h).get("distiller") else 1):
                if len(hero["bag"]) < self.bag_size(h):
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
                from .combat import face, top_face
                faces = max((d2["faces"] for d2 in self.dice_of(h)), key=top_face)
                v, t = face(self.roll_face(faces))
                roll = (top_face(faces) if t == "W" else v) + self.mods(h).get("silver_voice", 0)
                if roll < ch["check"]:
                    out = ch["bad"]
            self.outcome(h, out, ev, roll)
        elif d["type"] == "loot":
            if n is None or n == -1:
                q.pop(0)
            elif isinstance(n, int) and 0 <= n < len(d["opts"]):
                key = d["opts"][n]
                q.pop(0)
                self.gain_item(h, key)
            else:
                raise Invalid("Pick an item, or skip.")
        elif d["type"] == "level":
            if not isinstance(n, int) or not 0 <= n < len(d["opts"]):
                raise Invalid("Pick one.")
            self.learn(h, d["opts"][n])
            q.pop(0)
        if self.s["phase"] == "reward" and not any(self.waiting_reward(x) for x in range(3)):
            self.next_step()
        elif self.s["phase"] == "plan" and self.all_ready():
            self.resolve_turn()

    def has_class(self, k):
        return any(self.hero(h)["cls"] == k for h in self.living())

    def roll_face(self, faces):
        return faces[self.rng.next() % len(faces)]

    def outcome(self, h, out, ev, roll):
        hero = self.hero(h)
        bits = []
        if out.get("gold"):
            hero["gold"] += out["gold"]
            bits.append(f"+{out['gold']} gold")
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
            self.s["fights"].append({"kind": "event", "tile": hero["tile"], "heroes": [h], "foes": list(out["fight"]), "by": h})
            if self.s["phase"] == "plan":
                self.s["after"] = "plan"
                self.next_step()

    # ------------------------------------------------------------------ loot, xp and levels

    def rarity_for(self, bonus=0):
        tier = self.tier() + bonus
        weights = [("common", max(1, 6 - tier * 2)), ("uncommon", 3 + tier), ("rare", max(0, tier * 2 - 1)),
                   ("legendary", max(0, tier - 2))]
        return self.rng.weighted(weights)

    def offer_loot(self, h, n, tier_bonus=0, rarity=None):
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
        self.push(h, {"type": "loot", "opts": opts})

    def gain_item(self, h, key):
        hero = self.hero(h)
        it = I.ITEMS[key]
        slot = it["slot"]
        if slot != "use" and hero["equip"].get(slot) is None:
            hero["equip"][slot] = key
        elif len(hero["bag"]) < self.bag_size(h):
            hero["bag"].append(key)
        else:
            hero["gold"] += I.price(key) * 4 // 10
            self.say(f"{hero['name']}'s bag is full, so they sell the {it['name']}.")
            return
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
        p = self.town(h)
        t = self.hero(h)["tile"]
        stock = self.shop(t)
        key = msg.get("item")
        if key not in stock:
            raise Invalid("That's not for sale here.")
        hero = self.hero(h)
        cost = self.price_for(h, key)
        if hero["gold"] < cost:
            raise Invalid("You can't afford that.")
        slot = I.ITEMS[key]["slot"]
        if len(hero["bag"]) >= self.bag_size(h) and not (slot != "use" and hero["equip"].get(slot) is None):
            raise Invalid("Your bag is full.")
        hero["gold"] -= cost
        if key not in I.CONSUMABLES:
            stock.remove(key)
        self.gain_item(h, key)
        self.fx("coins", h=h, n=-cost)

    def do_sell(self, h, msg):
        self.town(h)
        hero = self.hero(h)
        i = msg.get("bag")
        if not isinstance(i, int) or not 0 <= i < len(hero["bag"]):
            raise Invalid("Sell what?")
        key = hero["bag"].pop(i)
        n = I.price(key) * (6 if self.mods(h).get("haggler") else 4) // 10
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
        if len(hero["bag"]) >= self.bag_size(h):
            raise Invalid("Your bag is full.")
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
        if len(other["bag"]) >= self.bag_size(to):
            raise Invalid("Their bag is full.")
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
        bonus = 1 + self.mods(h).get("potion_bonus", 0)
        n = self.heal(to, int(it["use"]["heal"] * bonus))
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
        groups = [{"id": g["id"], "tile": g["tile"], "lair": g["lair"], "foes": [f["k"] for f in g["foes"]]}
                  for g in s["groups"] if g["tile"] in vis or (g["lair"] and s["seen"][g["tile"]])]
        heroes = []
        for h in range(3):
            hero = s["heroes"][h]
            heroes.append({**{k: v for k, v in hero.items() if k not in ("tags",)}, "maxhp": self.maxhp(h),
                           "moves": self.moves(h), "dice": [{"faces": d["faces"], "dk": d["dk"]} for d in self.dice_of(h)], "bagsize": self.bag_size(h),
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
            "result": s["result"], "diff": s["diff"], "rise_every": self.diff()["rise"], "loss_rise": LOSS_RISE,
            "grow_from": GROW_FROM, "next_tide": TIDE_EVERY - (s["turn"] - 1) % TIDE_EVERY,
            "next_rise": self.diff()["rise"] - (s["turn"] - 1) % self.diff()["rise"],
            "seen": "".join(map(str, s["seen"])), "places": places, "groups": groups, "heroes": heroes,
            "xp": s["xp"], "level": s["level"], "xp_next": C.XP_FOR[s["level"]] if s["level"] < C.MAX_LEVEL else None,
            "xp_this": C.XP_FOR[s["level"] - 1], "revives": s["revives"], "cleared": s["cleared"],
            "dungeon": s["dungeon"], "plans": s["plans"], "pending": s["pending"], "fight": self.fight_view(),
            "quests": s["quests"], "floods": self.floods_next(), "log": s["log"][-12:], "fx": s["fx"][-60:],
            "stats": s["stats"], "waiting": self.waiting(), "inn": self.inn_cost(),
            "skiff_cost": SKIFF_COST, "herald": self.has_class("herald"),
        }


def static():
    """Content the browser needs once: classes, actions, items, foes, events, buffs."""
    acts = {k: {**v, "def": C.is_defensive(v)} for k, v in {**C.ACTIONS, **I.WEAPON_ACTIONS}.items()}
    return {
        "classes": C.CLASSES, "actions": acts, "passives": C.PASSIVES, "items": I.ITEMS, "foes": A.FOES,
        "events": {e["key"]: e for e in A.EVENTS}, "buffs": A.BUFFS, "regions": A.REGION_NAMES,
        "dungeons": {k: v["name"] for k, v in A.DUNGEONS.items()}, "xp_for": C.XP_FOR,
        "prices": {k: I.price(k) for k in I.ITEMS},
    }
