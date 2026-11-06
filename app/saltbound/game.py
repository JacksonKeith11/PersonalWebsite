"""A Saltbound run: the whole game state and its rules, outside of fights (see combat.py).

The state is one JSON-able dict (`Game.s`), so saving is `json.dumps(game.s)`. The game never
waits on a clock: it changes only when a hero acts (`Game.act`), and `Game.waiting()` says who it
is waiting on. Every hero sees the same state (vision is shared), so `Game.view()` is one dict
for everyone.

A map turn: every living hero plans a path (or rests) and readies up; then everyone moves at
once, enemies close in, fights start where heroes and enemies meet (every hero within a hex
joins), and landing on a place (an event, a wreck, a shrine) queues a dialog for that hero. Then
the next turn begins: the tide may turn, and every few turns the Great Tide rises: enemies grow
stronger, the sea brings arrivals and the garrisons grow.

Phases: `plan` (map turns), `fight`, `reward` (after a fight, until everyone's picks are made),
`end`.
"""

from . import classes as C
from . import mods as M
from . import world as Wd
from .biome import Biomes
from .quests import Quests
from .travel import Travel
from .combat import Combat, Invalid
from .content import archipelago as A
from .content import items as I
from .rng import Rng
from .tuning import DUNGEON_STEP_DMG, DUNGEON_STEP_HP, SURGE

VERSION = 13
DIFFICULTY = {
    # `rise`: turns between Great Tides (owner, Nov 2026: rarer and bigger, each one RISE_STEPS rises of
    # enemy strength at once, with the garrisons growing on the same turn)
    "story": {"rise": 12, "revives": 4, "foe_hp": 1.0, "foe_dmg": 0.95},
    "normal": {"rise": 9, "revives": 3, "foe_hp": 1.9, "foe_dmg": 2.6},
    # Hard: the tide's strength accelerates, so a few quests on the way are cheap but chasing every one is
    # dear (owner, Nov 2026: the middle road should be best, and whether a quest is worth it depends on the
    # path). Each rise adds `surge` (tuning.SURGE where unset), and past `surge_from` rises another
    # `surge2` times the square of how far past (Game.surge).
    "hard": {"rise": 9, "revives": 2, "foe_hp": 2.35, "foe_dmg": 2.95, "surge": 0.0065, "surge2": 0.0006, "surge_from": 20},
}
MOVES = 4
PATH_MAX = 20  # hexes in one turn's route at most (a current carries a skiff a long way)
VISION = 5  # land seen around a hero: more than a turn's walk, so a move's result is in view
GROW_FROM = 10  # after this many rises more enemies come ashore
RISE_STEPS = 3  # rises of enemy strength a Great Tide brings at once (`s["rises"]`; `s["tides"]` counts the tides)
TIDE_EVERY = 4
SPAWN_EVERY = 4
MAX_GROUPS = 12
INN_COST = 8
SKIFF_COST = 10
START_GOLD = 20
POOL_SIZE = 4  # a won fight's loot pool: this many items...
POOL_CLAIMS = 3  # ...of which at most this many can be claimed
SLOTS = I.SLOTS
slots_for = I.slots_for

LOG_KEEP = 40
FX_KEEP = 200


M.check_content([(f"passive {k}", p["mods"]) for k, p in C.PASSIVES.items()]
                + [(f"item {k}", {**it.get("mods", {}), **it.get("cursed_mods", {})}) for k, it in I.ITEMS.items()]
                + [(f"blessing {k}", b["mods"]) for k, b in A.BUFFS.items()])


class Game(Combat, Biomes, Quests, Travel):
    def __init__(self, s):
        self.s = s
        self.rng = Rng(s["rng"])

    # ------------------------------------------------------------------ making a run

    @classmethod
    def new(cls, seed, classes, difficulty="normal", names=None):
        assert len(classes) == 3 and len(set(classes)) == 3
        w = Wd.generate(seed, A.REGION_POOL)
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
            "rises": 0, "tides": 0, "phase": "plan", "result": None, "world": w, "seen": [0] * (Wd.W * Wd.H), "cleared": [],
            "dungeon": {}, "heroes": heroes, "xp": 0, "level": 1, "revives": diff["revives"], "miracle": False,
            "groups": [], "gid": 1, "plans": {}, "pending": {"0": [], "1": [], "2": []}, "pools": {}, "poolid": 0, "fights": [],
            "fight": None, "after": "turn", "quests": [], "shops": {}, "fx": [], "fxid": 0, "log": [],
            "stats": [{"dmg": 0, "heal": 0, "kills": 0, "taken": 0} for _ in range(3)], "fid": 1,
            "dnext": {}, "fork": None, "opps": [], "oppid": 0, "garrison": {}, "crown_cut": 0, "chains": [],
            "squalls": [], "sqid": 0, "garrison_skip": {},
        }
        g = cls(s)
        for reg in g.regions():
            s["dnext"][reg] = {"path": "open", "foes": g.dungeon_lineup(reg, "open")}
        for h in range(3):
            g.hero(h)["hp"] = g.maxhp(h)
        g.reveal_all()
        for _ in range(9):
            g.spawn(far=4)
        for _ in range(A.SEA_MAX):
            g.spawn_sea(far=4)
        for t, p in w["places"].items():
            if p["kind"] == "lair":
                gr = g.add_group(int(t), list(g.rng.choice(A.LAIRS[g.near_region(int(t))])), lair=True)
                gr["prize"] = g.rng.choice([k for k in g.gear() if g.item(k)["rarity"] == "rare"])
        g.setup_places(g.rng, guards=True)
        g.place_quests(g.rng)
        g.ensure_travel(g.rng)
        g.town_jobs(w["start"])
        g.reset_plans()
        names = [f"{A.DUNGEONS[r]['name']} in {A.REGION_NAMES[r]}" for r in g.regions()]
        g.say("The party sets out from " + w["places"][str(w["start"])]["name"] + ". This time the objectives are "
              + ", ".join(names[:-1]) + " and " + names[-1] + ".")
        g.sync()
        return g

    def setup_places(self, rng, guards=False):
        """What each place shows before anyone gets there, filled in where it's missing (new runs, and
        saves from before it existed): each event's story, each wreck's loot (a few guarded by camped
        enemies, with `guards`), each shrine's blessing (a few dark), each town's trade."""
        s = self.s
        w = s["world"]
        places = sorted(((int(t), p) for t, p in w["places"].items()), key=lambda x: x[0])
        evs = rng.shuffle([e["key"] for e in A.EVENTS if not e.get("hidden") and not e.get("region")])
        # a region's own events go to its event hexes first (only the regions this run drew)
        own = {r: rng.shuffle([e["key"] for e in A.EVENTS if e.get("region") == r]) for r in self.regions()}
        specs = rng.shuffle(list(A.TOWN_SPECS))
        wrecks = [t for t, p in places if p["kind"] == "wreck" and "rarity" not in p]
        shrines = [t for t, p in places if p["kind"] == "shrine" and "buff" not in p and not p.get("sea")]
        guarded = set(rng.sample(wrecks, A.GUARDED_WRECKS)) if guards else set()
        dark = set(rng.sample(shrines, A.DARK_SHRINES))
        k = j = 0
        for t, p in places:
            if p["kind"] == "event" and "ev" not in p:
                mine = own.get(w["reg"][t])
                if mine:
                    p["ev"] = mine.pop()
                else:
                    p["ev"] = evs[k % len(evs)]
                    k += 1
            elif p["kind"] == "wreck" and "rarity" not in p:
                if t in guarded:
                    p["rarity"], p["guard"] = "rare", True
                    reg = self.near_region(t)
                    foes = list(rng.choice(A.WRECK_GUARDS[reg]))
                    i = max(range(len(foes)), key=lambda n: A.FOES[foes[n]]["hp"])
                    foes[i] = {"k": foes[i], "aff": rng.choice(A.ROAM_ELITES)}
                    self.add_group(t, foes, lair=True)
                else:
                    p["rarity"] = rng.weighted(A.WRECK_RARITY)
            elif p["kind"] == "shrine" and "buff" not in p and p.get("sea"):
                p["buff"] = A.SEA_SHRINE_BUFF
            elif p["kind"] == "shrine" and "buff" not in p:
                p["buff"] = None if t in dark else rng.choice(A.SHRINE_BUFFS)
                if t in dark:
                    p["dark"] = True
            elif p["kind"] == "town" and "spec" not in p:
                p["spec"] = specs[j % len(specs)]
                j += 1

    # ------------------------------------------------------------------ small helpers

    def regions(self):
        """This run's three objective regions (drawn per world; older saves have the original three)."""
        return Wd.regions(self.s["world"])

    def near_region(self, t):
        """The objective region a hex belongs to, or for the peak and the small islands the one whose
        objective is nearest: whose enemies guard a wreck or a lair there."""
        w = self.s["world"]
        regs = self.regions()
        if w["reg"][t] in regs:
            return w["reg"][t]
        dung = {p["region"]: int(k) for k, p in w["places"].items() if p["kind"] == "dungeon"}
        return min(regs, key=lambda r: (Wd.dist(t, dung[r]) if r in dung else 99, regs.index(r)))

    def big_for(self, reg):
        """A big single threat for a hex's region: its own, or one of this run's regions'."""
        return A.BIG[reg] if reg in self.regions() else self.rng.choice([A.BIG[r] for r in self.regions()])

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
        f = self.s.get("fight")
        if f and f.get("rec"):
            self.recap(f, kind_, kw)

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
        for slot in SLOTS:
            it = hero["equip"].get(slot)
            if it:
                add(self.item(it).get("mods", {}))
                if self.item(it).get("cursed_mods"):
                    add(self.item(it)["cursed_mods"])
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
        for slot in SLOTS:
            it = hero["equip"].get(slot)
            if it:
                out.append({"faces": list(self.item(it)["die"]), "dk": list(self.item(it).get("dk", [])),
                            "src": self.item(it)["slot"]})
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
                out += [a for a in self.item(w).get("acts", []) if a not in out]
        out += [g for g in self.mods(h)["grant"] if g not in out]
        armor = hero["equip"].get("armor")
        guard = self.item(armor).get("guard") if armor else None
        out += [guard if g == "block" and guard else g for g in C.GENERIC]
        return out

    def equip_slot(self, h, key, into=None):
        """Where a piece of gear goes on: the slot asked for (`into`, for the two trinket slots), else
        an empty one, else the slot holding the lesser item (by rarity)."""
        slots = slots_for(self.item(key)["slot"])
        if into in slots:
            return into
        equip = self.hero(h)["equip"]
        empty = [s for s in slots if not equip.get(s)]
        if empty:
            return empty[0]
        return min(slots, key=lambda s: I.RARITIES.index(self.item(equip[s])["rarity"]))

    def action_def(self, h, key):
        base = key.rstrip("+")
        a = dict(C.ACTIONS.get(base) or I.WEAPON_ACTIONS[base])
        if key.endswith("+") and a.get("up"):
            a.update(a["up"])  # the upgrade's rider (classes.py `_upgrade`)
        a.update(self.mods(h)["override"].get(base, {}))
        a["key"] = base
        a["plus"] = key.endswith("+")
        a["def"] = C.is_defensive(a)
        return a

    def moves(self, h):
        hero = self.hero(h)
        tracker = C.map_key(hero) == "tracker" and not hero["afloat"]
        return max(1, MOVES + self.mods(h).get("move", 0) + (1 if tracker else 0))


    # ------------------------------------------------------------------ terrain

    def terrain(self, t):
        """'deep', 'shoal' (passable on foot at low tide) or a land biome."""
        e = self.s["world"]["elev"][t]
        sea = self.s["sea"]
        if e <= sea and self.iced(t):
            return "ice"  # the Frostpeaks' frozen sea
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
        if self.lava_at(b):
            return None  # Cinderreach's lava, until it cools
        t = self.terrain(b)
        if t == "deep":
            if not hero["skiff"]:
                return None
            cur, reef, pool, swirl = self.sea_map()
            if b in pool or (b in reef and self.tide() == "low"):
                return None
            if not afloat:
                cost = 2  # boarding
            elif cur.get(a) == b:
                cost = 0  # riding a current
            elif cur.get(b) == a:
                cost = 2  # against one
            else:
                cost = 1
            return cost + (1 if b in swirl else 0), True
        if t == "shoal":
            return (1, True) if afloat else (2, False)
        cost = self.land_cost(h, t, b, t in Wd.FAST.get(C.map_key(hero), ()))
        return cost + (1 if afloat else 0), False

    def sea_map(self):
        """The world's currents (hex -> the next hex downstream), reefs, whirlpools, and the hexes
        around the whirlpools (a skiff pays 1 more there)."""
        w = self.s["world"]
        c = getattr(self, "_sea", None)
        if c is None or c[0] is not w:
            cur = {int(k): v for k, v in w.get("cur", {}).items()}
            pool = set(w.get("pool", []))
            swirl = {n for t in pool for n in Wd.neighbors(t)} - pool
            self._sea = c = (w, cur, set(w.get("reef", [])), pool, swirl)
        return c[1:]

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
        storm = self.storm_sight(self.hero(h)["tile"])
        if storm is not None:
            return storm
        key = C.map_key(self.hero(h))
        return self.biome_sight(h, VISION + (1 if key == "farsight" else 0) + (1 if self.mods(h).get("wayfinder") else 0))

    def enemy_sight(self, h):
        """How far a hero can see enemies (Trackers see them further off; nobody sees far in a storm)."""
        storm = self.storm_sight(self.hero(h)["tile"])
        if storm is not None:
            return storm
        return self.vision(h) + (2 if C.map_key(self.hero(h)) == "tracker" else 0)

    def in_squall(self, t):
        return self.storm_sight(t) is not None

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

    def group_foes(self, reg):
        """A roaming group's enemies for a region, harder with objectives cleared and a high sea."""
        pool = A.GROUPS[reg]
        hi = min(len(pool), 3 + self.tier() * 2 + (2 if self.s["rises"] > GROW_FROM else 0))
        lo = max(0, hi - 4)
        return list(self.rng.choice(pool[lo:hi]))

    def spawn(self, far=5):
        w = self.s["world"]
        heroes = [self.hero(h)["tile"] for h in self.living()]
        cands = [t for t in range(Wd.W * Wd.H) if self.terrain(t) in Wd.COST and self.terrain(t) != "town"
                 and not self.place(t) and not self.group_at(t) and not self.lava_at(t) and all(Wd.dist(t, x) >= far for x in heroes)]
        if not cands:
            return
        t = self.rng.choice(cands)
        reg = w["reg"][t] or "peak"
        foes = self.group_foes(reg)
        tier = self.tier()
        if tier >= 2 and self.rng.chance(0.15):
            # a big single threat, alone
            foes = [self.big_for(reg)]
        elif tier >= 1 and self.rng.chance(0.25):
            # an elite leads the group
            i = max(range(len(foes)), key=lambda j: A.FOES[foes[j]]["hp"])
            foes[i] = {"k": foes[i], "aff": self.rng.choice(A.ROAM_ELITES)}
        self.add_group(t, foes)

    def land_groups(self):
        """The ordinary groups on land (what `MAX_GROUPS` counts): not sea beasts or raids."""
        return [g for g in self.s["groups"] if not g.get("sea") and not g.get("raid")]

    def spawn_sea(self, far=5):
        """A group of sea beasts, somewhere out on the water away from the heroes."""
        s = self.s
        heroes = [self.hero(h)["tile"] for h in self.living()]
        _, _, pool, _ = self.sea_map()
        elev = s["world"]["elev"]
        cands = [t for t in range(Wd.W * Wd.H) if elev[t] <= s["sea"] and not Wd.on_edge(t) and t not in pool
                 and not self.place(t) and not self.group_at(t) and all(Wd.dist(t, x) >= far for x in heroes)]
        if not cands:
            return None
        t = self.rng.choice(cands)
        if self.tier() >= 2 and self.rng.chance(A.SEA_BIG):
            foes = [A.BIG["coral"]]
        else:
            hi = min(len(A.SEA_GROUPS), 2 + self.tier() * 2)
            foes = list(self.rng.choice(A.SEA_GROUPS[max(0, hi - 3):hi]))
        g = self.add_group(t, foes)
        g["sea"] = True
        return g

    def move_groups(self):
        """Enemies take their step: roaming groups toward a hero near them on land, sea beasts toward a
        skiff at high tide, raids along their road. Returns tiles where they caught someone."""
        caught = []
        pos = {h: (self.hero(h)["tile"], self.hero(h)["afloat"]) for h in self.living()}
        for g in self.s["groups"]:
            tile_of = {x["id"]: x["tile"] for x in self.s["groups"]}
            best = self.group_step(g, pos, set(tile_of.values()), tile_of)
            if best is not None:
                self.fx("gmove", g=g["id"], path=[g["tile"], best])
                g["tile"] = best
                if any(self.hero(x)["tile"] == best and self.hero(x)["afloat"] == bool(g.get("sea")) for x in self.living()):
                    caught.append(best)
        for g in [g for g in self.s["groups"] if g.get("raid") and not g.get("occupy")]:
            if g["tile"] == g["raid"]["to"] and g["tile"] not in caught:
                self.occupy(g)
        return caught

    def group_step(self, g, heroes, occupied, tile_of):
        """Where a roaming group steps this turn, toward the nearest hero on land within 3 (None if
        it stays). `heroes` maps hero to (tile, afloat); `occupied` is every group's tile."""
        if g["lair"]:
            return None
        at = tile_of[g["id"]]
        if g.get("raid"):
            # a raid keeps to its road, whoever is about: onto a hero standing in it, or into its town
            road = self.raid_road(at, g["raid"]["to"])
            return road[0] if road and road[0] not in occupied else None
        sea = bool(g.get("sea"))
        if sea and self.tide() != "high":
            return None  # sea beasts lie still at low tide
        beasts = all(A.FOES[f["k"]].get("beast") for f in g["foes"])
        near = [h for h, (t, af) in heroes.items() if af == sea and Wd.dist(at, t) <= (A.SEA_HUNT if sea else self.hunt_range(g)) and
                not (beasts and C.map_key(self.hero(h)) == "wildspeak")]
        if not near:
            return None
        h = min(near, key=lambda h: Wd.dist(at, heroes[h][0]))
        goal = heroes[h][0]
        if g.get("bounty"):
            # a wanted crew runs: the step that takes it furthest from the heroes near it
            far = lambda n: min(Wd.dist(n, heroes[x][0]) for x in near)
            opts = [n for n in Wd.neighbors(at) if self.terrain(n) in Wd.COST and self.terrain(n) != "town"
                    and n not in occupied and not self.place(n) and not self.lava_at(n) and far(n) > far(at)]
            return max(opts, key=lambda n: (far(n), -n)) if opts else None
        best = None
        pool = self.sea_map()[2] if sea else ()
        for n in Wd.neighbors(at):
            ter = self.terrain(n)
            if sea:
                if ter != "deep" or n in pool or n in occupied or self.place(n):
                    continue
            elif ter not in Wd.COST or ter == "town" or n in occupied or (self.place(n) and n != goal) or self.lava_at(n):
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
            seen = g["tile"] in vis or bool(g.get("raid"))
            tile_of[g["id"]] = best
            if seen:
                steps.append({"g": g["id"], "from": g["tile"], "to": best})
                if any(t == best and af == bool(g.get("sea")) for t, af in pos.values()) and best not in [e[0] for e in encounters]:
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
                fight.update(kind="boss", foes=list(A.FINAL), boss_grow=-A.CROWN_CUT * s.get("crown_cut", 0))
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
                fight["ground"] = self.ground_of(tile, by, fight["kind"])
                if main.get("raid"):
                    fight["raid"] = "free" if main.get("occupy") else "stop"
                if any(q.get("group") == main["id"] and not q["done"] and not q.get("failed") for q in s["quests"]):
                    fight["job"] = True
            # the view wants keys, with any elite affixes alongside
            fight["aff"] = [k.get("aff") if isinstance(k, dict) else None for k in fight["foes"]]
            fight["foes"] = [k["k"] if isinstance(k, dict) else k for k in fight["foes"]]
            fights.append(fight)
        lands = {}
        for h, (t, af) in pos.items():
            p = self.place(t)
            o = self.opp_at(t)
            job = self.job_step(h, t)
            if h not in engaged and job and t != self.hero(h)["tile"]:
                lands[str(h)] = job
                continue
            if h not in engaged and o and (o["kind"] == "drift" or (o["kind"] == "healer" and h not in o["used"])):
                lands[str(h)] = o["kind"]
                continue
            if h in engaged or not p or t == self.hero(h)["tile"] or (p.get("hidden") and not p.get("found")):
                continue
            if p["kind"] in ("event", "wreck", "cache", "cove", "flotsam", "lookout", "grotto") and p.get("done"):
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
            "quest": self.do_quest, "equip": self.do_equip, "unequip": self.do_unequip, "use": self.do_use, "temper": self.do_temper, "beacon": self.do_beacon, "mbuy": self.do_mbuy,
            "give": self.do_give, "drop": self.do_drop,
            "reforge": self.do_reforge, "temple": self.do_temple, "chart": self.do_chart,
            "place": self.do_place, "reroll": self.do_reroll, "nudge": self.do_nudge, "trinket": self.do_trinket, "hawk": self.do_hawk,
            "fready": self.do_fready, "spirit": self.do_spirit, "fork": self.do_fork,
            "suggest": self.do_suggest, "ask": self.do_ask,
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
        path = [int(t) for t in msg.get("path") or [] if isinstance(t, int) and 0 <= t < Wd.W * Wd.H][:PATH_MAX]
        if path:
            cost = self.path_cost(h, path)
            if cost is None:
                raise Invalid("You can't go that way.")
            if cost > self.moves(h):
                raise Invalid("That's too far for one turn.")
        p["path"], p["rest"], p["ready"], p["warp"] = path, False, False, None

    def do_rest(self, h, msg):
        if not self.can_plan(h):
            raise Invalid("Not now.")
        p = self.plan(h)
        p["rest"], p["path"], p["ready"], p["warp"] = bool(msg.get("on", True)), [], False, None

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
        for h, p in plans.items():  # beacon journeys happen in one go, before anyone walks
            if p.get("warp") is not None and self.hero(h)["alive"]:
                self.warp(h, p["warp"], encounters)
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
                self.cut_trail(b)
                self.reveal(b, self.vision(h))
                self.spot_grottos(h)
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
            return {"kind": "boss", "tile": tile, "heroes": heroes, "foes": list(A.FINAL), "by": by,
                    "boss_grow": -A.CROWN_CUT * self.s.get("crown_cut", 0)}
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
        kind = "lair" if main["lair"] else "roam"
        return {"kind": kind, "tile": tile, "heroes": heroes, "groups": gids, "foes": foes[:5], "by": by,
                "ground": self.ground_of(tile, by, kind),
                "raid": ("free" if main.get("occupy") else "stop") if main.get("raid") else None}

    def ground_of(self, tile, by, kind):
        """The battleground rule a roaming or lair fight takes from its hex (`A.GROUNDS`), and the side
        it helps: on high ground whoever was already standing there, in the woods whoever came in.
        `by` is the hero who walked in, or None when enemies stepped onto the heroes."""
        if kind not in ("roam", "lair"):
            return None
        t = self.terrain(tile)
        reg = self.region_here(tile)
        came = by is not None  # the heroes walked in (else the enemies did)
        if t in ("hills", "peak"):
            return {"k": "high", "side": "foes" if came else "heroes"}
        # the other regions' own ground
        if reg == "ash" and t in ("grass", "beach"):
            return {"k": "embers", "side": "both"}
        if reg == "dunes" and t == "grass":
            return {"k": "sinking", "side": "foes" if came else "heroes"}
        if reg == "petrified" and t == "forest":
            return {"k": "statues", "side": "heroes"} if came else None
        if reg == "heaven" and t == "grass":
            return {"k": "hallowed", "side": "both"}
        if reg == "crystal" and t == "forest":
            return {"k": "resonance", "side": "both", "might": A.GROUNDS["resonance"]["might"]}
        if reg == "dream" and t == "grass":
            return {"k": "lulled", "side": "foes" if came else "heroes"}
        if reg == "frost" and t == "grass":
            return {"k": "snowdrift", "side": "foes" if came else "heroes"}
        if t == "forest":
            return {"k": "woods", "side": "heroes" if came else "foes"}
        return None

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
        """The next fight in a dungeon, as the party will meet it (the boss fight with its garrison)."""
        nxt = self.s["dnext"][reg]
        step = self.s["dungeon"].get(reg, 0)
        spec = {"kind": "dungeon", "region": reg, "step": step, "foes": list(nxt["foes"]),
                "path": nxt["path"], "ambush_foes": nxt["path"] == "sneak"}
        if step == A.DUNGEON_STEPS - 1:
            extra, grow = self.garrison_of(reg)
            spec["foes"] += extra
            spec["boss_grow"] = grow
        return spec

    def garrison_of(self, reg):
        """What an objective's garrison adds to its boss fight: (escorts, the boss's extra health)."""
        g = self.s.get("garrison", {}).get(reg, [])
        return list(g[:A.GARRISON_ESCORTS]), A.GARRISON_BOSS * max(0, len(g) - A.GARRISON_ESCORTS)

    def grow_garrisons(self):
        """Each objective not yet cleared grows its garrison (on each Great Tide). Returns
        [{"reg", "name", "tile", "n"}] for those that grew."""
        s = self.s
        grown = []
        for reg in self.regions():
            D = A.DUNGEONS[reg]
            g = s.setdefault("garrison", {}).setdefault(reg, [])
            if reg in s["cleared"] or len(g) >= A.GARRISON_MAX:
                continue
            skip = s.setdefault("garrison_skip", {})
            if skip.get(reg):
                skip[reg] -= 1
                self.say(f"{D['name']}'s garrison doesn't grow: its raiders never came back.")
                continue
            g.append(self.rng.choice([k for e in D["escort"] for k in e]))
            tile = next((int(t) for t, p in s["world"]["places"].items() if p["kind"] == "dungeon" and p.get("region") == reg), None)
            grown.append({"reg": reg, "name": D["name"], "tile": tile, "n": len(g)})
        if grown:
            self.say("The garrisons grow: " + ", ".join(x["name"] for x in grown) + ". Their bosses will be harder to reach.")
        return grown

    def make_fork(self, reg, step, tile, heroes):
        """After a dungeon fight: the party picks one of two ways on."""
        paths = self.rng.sample(A.MID_PATHS if step == 1 else A.BOSS_PATHS, 2)
        self.s["fork"] = {"region": reg, "step": step, "tile": tile, "heroes": list(heroes), "votes": {},
                          "opts": [{"path": p, "foes": self.dungeon_lineup(reg, p)} for p in paths]}
        if step == A.DUNGEON_STEPS - 1:
            extra, grow = self.garrison_of(reg)
            self.s["fork"]["garrison"] = {"foes": extra, "boss": round(grow * 100)}
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
            self.rise()  # the Great Tide: stronger enemies, arrivals, and the garrisons grow
        if s["phase"] == "end":
            return
        self.tick_tide()
        self.tick_opps()
        self.tick_chains()
        self.tick_jobs()
        self.tick_squalls()
        self.tick_biomes()
        self.ensure_travel(self.rng)
        self.tick_merchants()
        if s["turn"] >= A.RAID_FROM and (s["turn"] - A.RAID_FROM) % A.RAID_EVERY == 0:
            self.spawn_raid()
        if (s["turn"] - 1) % SPAWN_EVERY == 0:
            if len(self.land_groups()) < MAX_GROUPS:
                self.spawn()
                if s["rises"] > GROW_FROM:
                    self.spawn()
            if sum(1 for g in s["groups"] if g.get("sea")) < A.SEA_MAX:
                self.spawn_sea()
        for h in range(3):
            hero = self.hero(h)
            if hero["alive"] and self.timeless(h):
                continue  # the Stillwood: nothing runs down there
            for b in list(hero["buffs"]):
                if A.BUFFS[b].get("perm"):
                    continue  # a boon is for good
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

    # ------------------------------------------------------------------ opportunities and chains

    def tick_opps(self):
        """A new turn: opportunities run out, and every few turns a new one turns up."""
        s = self.s
        opps = s.setdefault("opps", [])
        for o in [o for o in opps if o["until"] < s["turn"]]:
            opps.remove(o)
            if o["kind"] == "ship":
                self.say(f"The merchant ship sails from {self.place(o['tile'])['name']}.")
            elif o["kind"] == "healer":
                self.say("The wandering healer moves on.")
            else:
                self.say("The drifting cargo washes back out to sea.")
        if s["turn"] % A.OPP_EVERY == 3 and len(opps) < A.OPP_MAX:
            self.spawn_opp()

    def opp_at(self, t):
        return next((o for o in self.s.get("opps", []) if o["tile"] == t), None)

    def spawn_opp(self):
        s = self.s
        heroes = [self.hero(h)["tile"] for h in self.living()]
        if not heroes:
            return
        taken = {o["tile"] for o in s["opps"]}
        places = s["world"]["places"]
        for kind in self.rng.shuffle(list(A.OPPS)):
            lo, hi = A.OPP_RANGE[kind]
            if kind == "ship":
                cands = [int(t) for t, p in places.items() if p["kind"] == "town" and self.docks(int(t)) and not p.get("occupied")]
            elif kind == "healer":
                cands = [int(t) for t, p in places.items() if p["kind"] == "camp"]
            else:
                cands = [t for t in range(Wd.W * Wd.H) if self.terrain(t) in ("beach", "grass") and not self.place(t)
                         and not self.group_at(t) and any(self.terrain(n) in ("deep", "shoal") for n in Wd.neighbors(t))]
            cands = [t for t in cands if t not in taken and lo <= min(Wd.dist(t, x) for x in heroes) <= hi]
            if not cands:
                continue
            t = self.rng.choice(cands)
            s["oppid"] = s.get("oppid", 0) + 1
            o = {"id": s["oppid"], "kind": kind, "tile": t, "until": s["turn"] + A.OPPS[kind]["turns"] - 1, "used": []}
            if kind == "ship":
                o["stock"] = []
                for _ in range(3):
                    r = self.rarity_for(2)
                    pool = [k for k in self.gear() if self.item(k)["rarity"] == r and k not in o["stock"]] or self.gear()
                    o["stock"].append(self.rng.choice(pool))
            s["opps"].append(o)
            self.reveal(t, 1)
            where = self.place(t)["name"] if kind == "ship" else A.REGION_NAMES.get(s["world"]["reg"][t] or "peak", "")
            self.say(f"{A.OPPS[kind]['name']} sighted ({where}), for {A.OPPS[kind]['turns']} turns.")
            self.fx("opp", kind=kind, tile=t)
            return

    def opp_land(self, h, o):
        """A hero on an opportunity's hex at the end of a turn."""
        hero = self.hero(h)
        if o["kind"] == "drift":
            self.s["opps"].remove(o)
            hero["gold"] += 10
            self.offer_loot(h, 3, tier_bonus=1)
            self.say(f"{hero['name']} hauls in the drifting cargo (+10 gold).")
            self.fx("coins", h=h, n=10)
        elif o["kind"] == "healer" and h not in o["used"]:
            o["used"].append(h)
            n = self.heal(h, self.maxhp(h))
            for b in [b for b in hero["buffs"] if A.BUFFS.get(b, {}).get("curse")]:
                del hero["buffs"][b]
            self.fx("heal", to=f"h{h}", n=n)
            self.say(f"The wandering healer sees to {hero['name']} (+{n} HP).")

    def start_chain(self, h, kind):
        s = self.s
        hero = self.hero(h)
        if kind == "cache":
            lo, hi = A.CACHE_RANGE
            cands = [t for t in range(Wd.W * Wd.H) if self.terrain(t) in ("beach", "grass", "forest", "hills")
                     and not self.place(t) and not self.group_at(t) and lo <= Wd.dist(t, hero["tile"]) <= hi]
            if cands:
                t = self.rng.choice(cands)
                s["world"]["places"][str(t)] = {"kind": "cache"}
                self.reveal(t, 1)
        elif kind == "loan":
            s.setdefault("chains", []).append({"kind": "loan", "h": h, "turn": s["turn"] + A.LOAN_DUE})
        elif kind == "castaway":
            s.setdefault("chains", []).append({"kind": "castaway", "turn": s["turn"] + A.CASTAWAY_AFTER})

    def tick_chains(self):
        """A new turn: a debt falls due."""
        s = self.s
        for c in [c for c in s.get("chains", []) if c["kind"] == "loan" and c["turn"] <= s["turn"]]:
            s["chains"].remove(c)
            who = c["h"] if self.hero(c["h"])["alive"] else (self.living() or [None])[0]
            if who is not None:
                self.push(who, {"type": "event", "key": "collector"})

    def tide_at(self, turn):
        return "low" if ((turn - 1) // TIDE_EVERY) % 2 == 0 else "high"

    def rise(self):
        """The Great Tide: every enemy met from now on is stronger (`surge`, RISE_STEPS rises at once),
        the sea brings arrivals, and the garrisons of the objectives still standing grow. The land
        stays as it is: the sea never floods hexes or sinks places."""
        s = self.s
        before = self.surge()
        was = s["rises"]
        s["rises"] += RISE_STEPS
        s["tides"] = s.get("tides", 0) + 1
        self.say(f"The Great Tide rises: enemies are stronger (+{round((self.surge() - before) * 100)}%).")
        news = self.tide_arrivals()
        grown = self.grow_garrisons()
        self.fx("rise", rises=s["rises"], tide=s["tides"], news=news, up=round((self.surge() - before) * 100),
                surge=round((self.surge() - 1) * 100), garrisons=grown)
        if was <= GROW_FROM < s["rises"]:
            self.say("More enemies come ashore with every rise now.")

    def tick_tide(self):
        """A new turn: enemies the tide landed that nobody fought go back to sea."""
        s = self.s
        for g in [g for g in s["groups"] if g.get("tide") and g.get("until", s["turn"]) < s["turn"]]:
            s["groups"].remove(g)
            self.say("The beached beast slides back into the sea." if g["lair"] else "A band that came ashore puts back out to sea.")

    def tide_arrivals(self):
        """What the rising tide brings (`A.TIDE_ARRIVALS`): gifts early, threats later, shown on the map
        at once. Returns what came, which is also kept as the news until the next rise."""
        s = self.s
        r = s["rises"]
        late = r >= A.TIDE_LATE
        n = 3 if r >= 2 * A.TIDE_TWO_FROM else 2  # a Great Tide brings two arrivals, three later on
        heroes = [self.hero(h)["tile"] for h in self.living()]
        news = []
        if not heroes:
            s["tidenews"] = news
            return news
        tried = set()
        while len(news) < n:
            pairs = [(k, a["w"][late]) for k, a in A.TIDE_ARRIVALS.items()
                     if a["from"] <= r and a["w"][late] > 0 and k not in tried]
            if not pairs:
                break
            k = self.rng.weighted(pairs)
            tried.add(k)
            got = self.tide_arrival(k, heroes, late)
            if got:
                news.append(got)
        s["tidenews"] = news
        return news

    def tide_arrival(self, k, heroes, late):
        s = self.s
        a = A.TIDE_ARRIVALS[k]
        if k == "boon":
            before = len(s.get("opps", []))
            if before >= A.OPP_MAX + 1:
                return None
            self.spawn_opp()
            if len(s.get("opps", [])) == before:
                return None
            o = s["opps"][-1]
            where = self.place(o["tile"])["name"] if o["kind"] == "ship" else A.REGION_NAMES.get(s["world"]["reg"][o["tile"]] or "peak", "")
            return {"k": k, "tile": o["tile"], "name": A.OPPS[o["kind"]]["name"] + " sighted", "text": A.OPPS[o["kind"]]["text"], "where": where}
        if k in ("landing", "warband", "leviathan") and sum(1 for x in s["groups"] if x.get("tide")) >= A.TIDE_GROUPS:
            return None
        if k == "wreckage" and sum(1 for p in s["world"]["places"].values() if p.get("tide") and not p.get("done")) >= A.TIDE_WRECKS:
            return None
        lo, hi = a["range"]
        cands = [t for t in range(Wd.W * Wd.H) if self.terrain(t) == "beach" and not self.place(t)
                 and not self.group_at(t) and lo <= min(Wd.dist(t, x) for x in heroes) <= hi]
        if not cands:
            return None
        t = self.rng.choice(cands)
        reg = s["world"]["reg"][t] or "peak"
        where = A.REGION_NAMES.get(reg, "")
        g = None
        if k == "wreckage":
            s["world"]["places"][str(t)] = {"kind": "wreck", "rarity": self.rng.weighted(A.TIDE_WRECK_RARITY[late]), "tide": True}
        elif k == "landing":
            g = self.add_group(t, self.group_foes(reg))
            g["sighted"] = s["turn"] + A.TIDE_SIGHTED - 1
        elif k == "warband":
            foes = self.group_foes(reg)
            i = max(range(len(foes)), key=lambda j: A.FOES[foes[j]]["hp"])
            foes[i] = {"k": foes[i], "aff": self.rng.choice(A.ROAM_ELITES)}
            g = self.add_group(t, foes)
            g["sighted"] = s["turn"] + A.TIDE_SIGHTED - 1
            g["prize"] = self.rng.choice([x for x in self.gear() if self.item(x)["rarity"] == "rare"])
        elif k == "leviathan":
            g = self.add_group(t, [self.big_for(reg)], lair=True)
            g["prize"] = self.rng.choice([x for x in self.gear() if self.item(x)["rarity"] == "rare"])
        if g:
            g["tide"] = True
            g["until"] = s["turn"] + A.TIDE_STAY * (2 if k == "leviathan" else 1) - 1
        self.reveal(t, 1)
        self.say(f"{a['name']} ({where}).")
        return {"k": k, "tile": t, "name": a["name"], "text": a["text"], "where": where, **({"g": g["id"]} if g else {})}

    # ------------------------------------------------------------------ raids

    def raid_road(self, at, to):
        """The road a raid takes from `at` to its town: the shortest walk over land that keeps off
        towns and places (but its own town). The hexes after `at`, or None if there's no way."""
        if at == to:
            return []
        prev, edge = {at: None}, [at]
        while edge and to not in prev:
            nxt = []
            for t in edge:
                for n in Wd.neighbors(t):
                    if n in prev:
                        continue
                    ter = self.terrain(n)
                    if n != to and (ter not in Wd.COST or ter == "town" or self.place(n)):
                        continue
                    prev[n] = t
                    nxt.append(n)
            edge = nxt
        if to not in prev:
            return None
        road = [to]
        while prev[road[-1]] != at:
            road.append(prev[road[-1]])
        return road[::-1]

    def spawn_raid(self):
        """An objective not yet cleared sends a band to take a town in reach (`A.RAID_*`)."""
        s = self.s
        places = s["world"]["places"]
        raids = [g for g in s["groups"] if g.get("raid")]
        if len(raids) >= A.RAID_MAX:
            return None
        busy = {g["raid"]["reg"] for g in raids}
        targeted = {g["raid"]["to"] for g in raids}
        heroes = {self.hero(h)["tile"] for h in self.living()}
        lo, hi = A.RAID_RANGE
        opts = []
        for t, p in sorted(places.items(), key=lambda x: int(x[0])):
            reg = p.get("region")
            if p["kind"] != "dungeon" or reg in s["cleared"] or reg in busy:
                continue
            d0 = int(t)
            starts = sorted(n for n in Wd.within(d0, 2) if self.terrain(n) in Wd.COST and self.terrain(n) != "town"
                            and not self.place(n) and not self.group_at(n) and n not in heroes)
            towns = sorted(int(x) for x, q in places.items() if q["kind"] == "town" and not q.get("occupied")
                           and int(x) not in targeted and int(x) not in heroes and Wd.dist(d0, int(x)) <= hi)
            for town in towns:
                st = min(starts, key=lambda n: (Wd.dist(n, town), n), default=None)
                road = self.raid_road(st, town) if st is not None else None
                if road and lo <= len(road) <= hi:
                    opts.append((reg, st, town, road))
        if not opts:
            return None
        reg, st, town, road = self.rng.choice(opts)
        foes = self.group_foes(reg)
        i = max(range(len(foes)), key=lambda j: A.FOES[foes[j]]["hp"])
        foes[i] = {"k": foes[i], "aff": self.rng.choice(A.ROAM_ELITES)}
        g = self.add_group(st, foes)
        g["raid"] = {"reg": reg, "to": town}
        self.reveal(st, 1)
        self.reveal(town, 1)
        name = self.place(town)["name"]
        self.say(f"Raiders march from {A.DUNGEONS[reg]['name']} on {name}: {len(road)} turns away. Stop them on the road!")
        self.fx("raid", g=g["id"], tile=st, to=town, reg=reg, eta=len(road))
        return g

    def occupy(self, g):
        """A raid reached its town with nobody there to stop it: the town is shut until it's freed,
        and the objective it came from grows its garrison at once."""
        s = self.s
        town = self.place(g["tile"])
        reg = g["raid"]["reg"]
        g["occupy"] = True
        g["lair"] = True
        town["occupied"] = g["id"]
        town.pop("jobs", None)
        gar = s.setdefault("garrison", {}).setdefault(reg, [])
        if reg not in s["cleared"] and len(gar) < A.GARRISON_MAX:
            gar.append(self.rng.choice([k for e in A.DUNGEONS[reg]["escort"] for k in e]))
        self.say(f"Raiders take {town['name']}! Its shop, inn, board and trade are shut until someone drives them out, "
                 f"and {A.DUNGEONS[reg]['name']}'s garrison grows.")
        self.fx("occupied", tile=g["tile"], reg=reg)

    def raids_beaten(self, f, winners):
        """After a won fight: any raid in it is broken (on the road) or driven out (from a town)."""
        s = self.s
        for g in [g for g in s["groups"] if g["id"] in f["groups"] and g.get("raid")]:
            reg = g["raid"]["reg"]
            if g.get("occupy"):
                town = self.place(g["tile"])
                town.pop("occupied", None)
                for h in winners:
                    self.hero(h)["gold"] += A.FREE_GOLD
                self.restock(g["tile"])
                self.say(f"{town['name']} is free! The townsfolk pay {A.FREE_GOLD} gold each and open a better-stocked shop.")
                self.fx("freed", tile=g["tile"], gold=A.FREE_GOLD)
            else:
                skip = s.setdefault("garrison_skip", {})
                if reg not in s["cleared"]:
                    skip[reg] = skip.get(reg, 0) + 1
                for h in winners:
                    self.hero(h)["gold"] += A.RAID_BOUNTY
                self.say(f"The raid is broken (+{A.RAID_BOUNTY} gold each): {A.DUNGEONS[reg]['name']}'s garrison won't grow next time.")
                self.fx("raidstop", tile=g["tile"], reg=reg, gold=A.RAID_BOUNTY)

    def restock(self, t):
        """A town's shop fills with better wares."""
        stock = []
        for _ in range(5):
            rr = self.rarity_for(2)
            pool = [k for k in self.gear() if self.item(k)["rarity"] == rr and k not in stock] or self.gear()
            stock.append(self.rng.choice(pool))
        self.s["shops"][str(t)] = stock + ["potion", "big_potion", "bomb", "ward_scroll", "smelling_salts"]

    # ------------------------------------------------------------------ the weather, grottos and lookouts

    def tick_squalls(self):
        """A new turn: squalls drift a hex (toward the middle of the map, roughly), blow out when their
        time is up or they leave the map, and every few turns a new one gathers: a squall over Stormcrag's
        waters, a sandstorm over the Shifting Sands, a blizzard over the Frostpeaks (`A.STORMS`)."""
        s = self.s
        qs = s.setdefault("squalls", [])
        for q in list(qs):
            nt = Wd.step_dir(q["tile"], q["dir"])
            if q["until"] < s["turn"] or nt is None or Wd.on_edge(nt):
                qs.remove(q)
                continue
            q["tile"] = nt
        if s["turn"] < A.SQUALL_FROM or s["turn"] % A.SQUALL_EVERY:
            return
        w = s["world"]
        for kind, K in A.STORMS.items():
            if K["region"] not in self.regions() or sum(1 for q in qs if q.get("kind", "squall") == kind) >= A.SQUALL_MAX:
                continue
            # squalls over Stormcrag's waters; sandstorms over the dunes; blizzards over the Frostpeaks
            cands = [t for t in range(Wd.W * Wd.H) if w["reg"][t] == K["region"] and not Wd.on_edge(t)
                     and (w["elev"][t] <= s["sea"]) == K["water"] and all(Wd.dist(t, q["tile"]) > 3 for q in qs)]
            if not cands:
                continue
            t = self.rng.choice(cands)
            toward = [d for d in range(6) if Wd.step_dir(t, d) is not None and Wd.dist(Wd.step_dir(t, d), w["peak"]) < Wd.dist(t, w["peak"])]
            s["sqid"] = s.get("sqid", 0) + 1
            qs.append({"id": s["sqid"], "tile": t, "dir": self.rng.choice(toward or list(range(6))), "until": s["turn"] + A.SQUALL_TURNS - 1,
                       "kind": kind})
            where = A.REGION_NAMES[K["region"]]
            self.say(f"A {K['name']} gathers over {where}. Inside it you'll see only {'a hex' if K['sight'] == 1 else 'a couple of hexes'}.")
            self.fx("squall", tile=t, kind=kind)

    def spot_grottos(self, h, r=None):
        """Hidden grottos near a hero are found (a hex off, or two for a Farsighted hero; `r` for a lookout)."""
        hero = self.hero(h)
        if r is None:
            r = A.GROTTO_SPOT + (1 if C.map_key(hero) == "farsight" else 0)
        for t, p in self.s["world"]["places"].items():
            if p["kind"] == "grotto" and p.get("hidden") and not p.get("found") and Wd.dist(int(t), hero["tile"]) <= r:
                p["found"] = True
                self.reveal(int(t), 1)
                where = A.REGION_NAMES.get(self.s["world"]["reg"][int(t)] or "peak", "")
                self.say(f"{hero['name']} finds a hidden grotto ({where}).")
                self.fx("found", h=h, tile=int(t))

    def surge(self):
        """How much stronger enemies are for the tide having risen: HP and damage both."""
        d, r = self.diff(), self.s["rises"]
        return 1 + d.get("surge", SURGE) * r + d.get("surge2", 0) * max(0, r - d.get("surge_from", 0)) ** 2

    def rest(self, h):
        hero = self.hero(h)
        hero["spent"] = []  # once-per-rest actions (Lift) come back
        p = self.place(hero["tile"])
        medic = any(C.map_key(self.hero(x)) == "field_medic" and self.hero(x)["tile"] == hero["tile"]
                    for x in self.living())
        key = C.map_key(hero)
        frac = 0.5 if p and p["kind"] == "camp" else 0.2
        if key == "forage" and p and p["kind"] == "camp":
            frac = 1
        if medic:
            frac = min(1, frac + 0.1)
        frac = self.biome_rest(h, frac)
        frac = min(1, frac + self.mods(h).get("rest_bonus", 0))
        n = self.heal(h, int(self.maxhp(h) * frac + 0.5))
        self.fx("heal", to=f"h{h}", n=n)
        self.say(f"{hero['name']} rests (+{n} HP).")
        if key == "brewer":
            for _ in range(2 if self.mods(h).get("distiller") else 1):
                hero["bag"].append("potion")
        if key == "dragons_rest":
            # Dragon's Rest: a Scale, two at a camp or in a town
            hero["scales"] = min(C.SCALE_CAP, hero.get("scales", 0) + (2 if p and p["kind"] in ("camp", "town") else 1))
        if key == "runewright":
            # Runewright: the next fight's enemies start with 2 Sigils (the next two after a town)
            hero["runes"] = max(hero.get("runes", 0), 2 if p and p["kind"] == "town" else 1)

    # ------------------------------------------------------------------ places

    def land(self, h):
        hero = self.hero(h)
        t = hero["tile"]
        self.spot_grottos(h)
        o = self.opp_at(t)
        if o:
            self.opp_land(h, o)
        self.job_land(h, t)
        p = self.place(t)
        if not p:
            return
        k = p["kind"]
        if self.biome_land(h, t, p):
            return
        if k == "quest":
            self.quest_land(h, t, p)
        elif k == "beacon":
            self.beacon_land(h, t, p)
        elif k == "event" and not p.get("done"):
            key = p.get("ev") or self.pick_event(h)["key"]
            self.s.setdefault("events_seen", []).append({"key": key})
            p["done"] = True
            self.push(h, {"type": "event", "key": key})
        elif k == "wreck" and not p.get("done"):
            p["done"] = True
            n = 2 + (1 if C.map_key(hero) == "light_fingers" else 0)
            self.offer_loot(h, n, tier_bonus=0, rarity=p.get("rarity"))
            self.say(f"{hero['name']} picks through a wreck.")
        elif k == "cove" and not p.get("done"):
            p["done"] = True
            hero["gold"] += A.COVE_GOLD
            self.offer_loot(h, 3, rarity=self.rng.weighted(A.COVE_RARITY))
            self.say(f"{hero['name']} finds a smugglers' stash in the cove (+{A.COVE_GOLD} gold).")
            self.fx("coins", h=h, n=A.COVE_GOLD)
        elif k == "flotsam" and not p.get("done"):
            p["done"] = True
            hero["gold"] += A.FLOTSAM_GOLD
            self.offer_loot(h, 2, rarity=self.rng.weighted(A.WRECK_RARITY))
            self.say(f"{hero['name']} hauls in the flotsam (+{A.FLOTSAM_GOLD} gold).")
            self.fx("coins", h=h, n=A.FLOTSAM_GOLD)
        elif k == "lookout" and not p.get("done"):
            p["done"] = True
            self.reveal(t, A.LOOKOUT_SIGHT)
            self.spot_grottos(h, A.LOOKOUT_SIGHT)
            self.say(f"{hero['name']} climbs the lookout: the land is laid out {A.LOOKOUT_SIGHT} hexes around.")
            self.fx("lookout", h=h, tile=t, r=A.LOOKOUT_SIGHT)
        elif k == "grotto" and not p.get("done"):
            p["done"] = p["found"] = True
            if p.get("grotto") == "spring":
                self.s["revives"] += 1
                n = self.heal(h, self.maxhp(h))
                self.fx("heal", to=f"h{h}", n=n)
                self.say(f"{hero['name']} drinks from the grotto's spring: full health, and the party gains a revive.")
            else:
                hero["gold"] += A.GROTTO_GOLD
                self.offer_loot(h, 3, rarity="rare")
                self.say(f"{hero['name']} finds an old hoard in the grotto (+{A.GROTTO_GOLD} gold).")
                self.gain_item(h, self.rng.choice(I.MATERIALS))
                self.fx("coins", h=h, n=A.GROTTO_GOLD)
        elif k == "cache" and not p.get("done"):
            p["done"] = True
            hero["gold"] += 15
            self.offer_loot(h, 3, tier_bonus=2)
            self.say(f"{hero['name']} digs up the cache from the torn chart (+15 gold).")
            self.fx("coins", h=h, n=15)
        elif k == "shrine" and p.get("dark") and t not in hero["shrines"]:
            hero["shrines"].append(t)
            self.push(h, {"type": "event", "key": "dark_shrine"})
        elif k == "shrine" and t not in hero["shrines"]:
            if "buff" not in p:
                p["buff"] = self.rng.choice(A.SHRINE_BUFFS)
            hero["shrines"].append(t)
            self.buff(h, p["buff"])
            self.bless_hex(h, t, p["buff"])
            if p.get("sea") and not p.get("mat_taken"):
                # the sea shrine's offering: an enchant material for the first to come
                p["mat_taken"] = True
                self.gain_item(h, self.rng.choice(I.MATERIALS))
        elif k == "town":
            self.town_jobs(t)
            for c in [c for c in self.s.get("chains", []) if c["kind"] == "castaway" and c["turn"] <= self.s["turn"]]:
                self.s["chains"].remove(c)
                hero["gold"] += 15
                self.offer_loot(h, 2, rarity="rare")
                text = "The castaway you helped made it here, and he hasn't forgotten: he presses a gift on you."
                self.fx("event", h=h, key="castaway", text=text, roll=None, bits=["+15 gold", "a rare find"])
                self.say(f"{hero['name']} — {text} (+15 gold)")

    def buff(self, h, key):
        b = A.BUFFS[key]
        self.hero(h)["buffs"][key] = b["turns"]
        self.say(f"{self.hero(h)['name']}: {b['name']} ({b['text']})")
        self.fx("buff", h=h, b=key)

    def push(self, h, dialog):
        self.s["pending"][str(h)].append(dialog)

    def pick_event(self, h):
        """An event for an event hex with none set (saves from before each hex had its own)."""
        done = {d.get("key") for d in self.s.get("events_seen", [])}
        placed = [e for e in A.EVENTS if not e.get("hidden") and not e.get("region")]
        fresh = [e for e in placed if e["key"] not in done] or placed
        return self.rng.choice(fresh)

    def do_choose(self, h, msg):
        q = self.s["pending"][str(h)]
        if not q:
            raise Invalid("Nothing to choose.")
        # the results screen shows every choice at once, so a pick can name which one (`i`); an event's
        # choice still comes first, since what it leads to can change the rest
        i = msg.get("i", 0)
        if not isinstance(i, int) or not 0 <= i < len(q) or (i and (q[i]["type"] == "event" or q[0]["type"] == "event")):
            raise Invalid("That choice isn't open.")
        d = q[i]
        n = msg.get("n")
        if d["type"] == "event" and d.get("huddle"):
            # a party check waiting on allies: roll now with whoever has chipped in, or take it back
            if msg.get("cancel"):
                self.end_huddle(h, d)
                d.pop("huddle")
            else:
                self.resolve_event(h, d, d["huddle"]["n"])
        elif d["type"] == "event":
            ev = next(e for e in A.EVENTS if e["key"] == d["key"])
            if not isinstance(n, int) or not 0 <= n < len(ev["choices"]):
                raise Invalid("Pick one of the choices.")
            ch = ev["choices"][n]
            hero = self.hero(h)
            if ch.get("need") and not self.has_class(ch["need"]):
                raise Invalid("Nobody in the party can do that.")
            if ch.get("cost", 0) > hero["gold"]:
                raise Invalid("You can't afford that.")
            helpers = self.helpers_for(h) if isinstance(ch.get("check"), dict) and ch["check"].get("die") == "party" else []
            if helpers:
                # a party check with allies on the hex: ask each of them to chip in first
                d["huddle"] = {"n": n, "helpers": helpers, "offers": {}}
                for y in helpers:
                    self.push(y, {"type": "help", "h": h, "key": d["key"], "n": n})
                self.fx("huddle", h=h, key=d["key"], n=n, helpers=helpers)
            else:
                self.resolve_event(h, d, n)
        elif d["type"] == "help":
            # an ally's party check: chip in (roll your best die too, and share a bad outcome) or not
            owner = d["h"]
            od = next((x for x in self.s["pending"][str(owner)] if x["type"] == "event" and x.get("huddle")), None)
            q.pop(i)
            if od:
                od["huddle"]["offers"][str(h)] = bool(n)
                self.say(f"{self.hero(h)['name']} {'chips in' if n else 'stays out of it'}.")
                if all(str(y) in od["huddle"]["offers"] for y in od["huddle"]["helpers"]):
                    self.resolve_event(owner, od, od["huddle"]["n"])
        elif d["type"] == "loot":
            if n is None or n == -1:
                q.pop(i)
            elif isinstance(n, int) and 0 <= n < len(d["opts"]):
                to = self.loot_to(h, d["opts"][n], msg)
                q.pop(i)
                self.take_loot(h, d["opts"][n], to, msg.get("equip"), msg.get("into"))
            else:
                raise Invalid("Pick an item, or skip.")
        elif d["type"] == "pool":
            pool = self.s["pools"][str(d["id"])]
            if (n is None or n == -1) and msg.get("all"):
                q[:] = [x for x in q if not (x["type"] == "pool" and x["id"] == d["id"])]
            elif n is None or n == -1:
                q.pop(i)
            elif isinstance(n, int) and 0 <= n < len(pool["items"]):
                if str(n) in pool["taken"]:
                    raise Invalid("Someone has already claimed that.")
                to = self.loot_to(h, pool["items"][n], msg)
                q.pop(i)
                pool["taken"][str(n)] = {"by": h, "to": to}
                self.take_loot(h, pool["items"][n], to, msg.get("equip"), msg.get("into"))
            else:
                raise Invalid("Claim an item, or pass.")
            self.close_pool(d["id"])
        elif d["type"] == "level":
            if not isinstance(n, int) or not 0 <= n < len(d["opts"]):
                raise Invalid("Pick one.")
            self.learn(h, d["opts"][n])
            q.pop(i)
        if self.s["phase"] == "reward" and not any(self.waiting_reward(x) for x in range(3)):
            self.next_step()
        elif self.s["phase"] == "plan" and self.all_ready():
            self.resolve_turn()

    def helpers_for(self, h):
        """Allies who could chip in on a hero's party check: everyone alive on the same hex."""
        return [y for y in self.living() if y != h and self.hero(y)["tile"] == self.hero(h)["tile"]]

    def end_huddle(self, h, d):
        """Take back the chip-in asks for a hero's party check."""
        for y in d["huddle"]["helpers"]:
            self.s["pending"][str(y)] = [x for x in self.s["pending"][str(y)] if not (x["type"] == "help" and x["h"] == h)]

    def resolve_event(self, h, d, n):
        """An event's choice happens: pay its cost, roll its check (with any allies who chipped in),
        and play the outcome. A failed party check's bad outcome reaches everyone who chipped in."""
        ev = next(e for e in A.EVENTS if e["key"] == d["key"])
        ch = ev["choices"][n]
        hero = self.hero(h)
        helpers = []
        if d.get("huddle"):
            helpers = [y for y in d["huddle"]["helpers"] if d["huddle"]["offers"].get(str(y)) and self.hero(y)["alive"]]
            self.end_huddle(h, d)
        q = self.s["pending"][str(h)]
        if d in q:
            q.remove(d)
        hero["gold"] -= min(hero["gold"], ch.get("cost", 0))
        out = ch["ok"]
        roll = None
        if ch.get("check"):
            roll = self.event_roll(h, ch["check"], helpers)
            if not roll["ok"]:
                out = ch["bad"]
            elif ch.get("great") and roll.get("great"):
                out = ch["great"]
        self.outcome(h, out, ev, roll)
        if roll and not roll["ok"] and helpers:
            self.share_bad(helpers, out, ev)

    def share_bad(self, helpers, out, ev):
        """Allies who chipped in on a failed party check take its harm too: lost HP, lost gold, curses."""
        for y in helpers:
            hy, bits = self.hero(y), []
            if out.get("hp", 0) < 0:
                hy["hp"] = max(1, hy["hp"] + out["hp"])
                bits.append(f"{out['hp']} HP")
            if out.get("gold", 0) < 0:
                hy["gold"] = max(0, hy["gold"] + out["gold"])
                bits.append(f"{out['gold']:+d} gold")
            for b in self.buffs_of(out):
                if A.BUFFS[b].get("curse"):
                    self.buff(y, b)
                    bits.append(A.BUFFS[b]["name"])
            if bits:
                self.fx("event", h=y, key=ev["key"], text="You chipped in, and you share the bad luck.", roll=None, bits=bits)
                self.say(f"{hy['name']} shares the bad luck ({', '.join(bits)}).")

    def do_suggest(self, h, msg):
        """A hero suggests one of an ally's event choices (or takes the suggestion back with n None)."""
        to, n = msg.get("to"), msg.get("n")
        if not isinstance(to, int) or not 0 <= to < 3 or to == h:
            raise Invalid("Suggest to whom?")
        q = self.s["pending"][str(to)]
        if not q or q[0]["type"] != "event":
            raise Invalid("They aren't choosing anything now.")
        ev = next(e for e in A.EVENTS if e["key"] == q[0]["key"])
        sugg = q[0].setdefault("sugg", {})
        if n is None:
            sugg.pop(str(h), None)
        elif isinstance(n, int) and 0 <= n < len(ev["choices"]):
            sugg[str(h)] = n
        else:
            raise Invalid("Suggest one of the choices.")

    def do_ask(self, h, msg):
        """A hero asks the party what to do about their event: everyone else's screen shows it."""
        q = self.s["pending"][str(h)]
        if not q or q[0]["type"] != "event":
            raise Invalid("Nothing to ask about.")
        q[0]["asked"] = True
        self.fx("ask", h=h, key=q[0]["key"])

    def event_die(self, h, which):
        """The die an event check rolls: a slot's item die (a bare d4 with nothing there), or the
        hero's best die."""
        from .dice import top_face
        dice = self.dice_of(h)
        if which in ("weapon", "armor", "trinket"):
            d = next((d for d in dice if d["src"] == which), None)
            return d["faces"] if d else [1, 2, 3, 4]
        return max((d["faces"] for d in dice), key=top_face)

    def event_roll(self, h, spec, helpers=()):
        """Roll an event check. `spec` is a number (best die, that much or more) or {die: weapon,
        armor, trinket, best or party (a party check: you and every ally on your hex who chips in each
        roll your best die, and the best roll counts), n: the target, vs: an opponent's die size to
        beat instead, great: a roll for the best outcome}."""
        from .dice import face, top_face
        if isinstance(spec, int):
            spec = {"n": spec}
        which = spec.get("die", "best")
        party = which == "party"
        if party:
            which = "best"
        rolls = []
        for roller in [h] + (list(helpers) if party else []):
            faces = self.event_die(roller, which)
            v, t = face(self.roll_face(faces))
            v = (top_face(faces) if t == "W" else v) + self.mods(roller).get("silver_voice", 0)
            rolls.append({"by": roller, "v": v, "faces": faces})
        best = max(rolls, key=lambda r: r["v"])
        v, faces, roller = best["v"], best["faces"], best["by"]
        out = {"v": v, "die": which, "faces": faces, "by": roller}
        if len(rolls) > 1:
            out["rolls"] = rolls
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
                    for b in self.buffs_of(out):
                        self.buff(x, b)
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
        for b in self.buffs_of(out):
            self.buff(h, b)
        if out.get("chain"):
            self.start_chain(h, out["chain"])
        if out.get("revive"):
            self.s["revives"] += out["revive"]
            bits.append("+1 revive")
        if out.get("xp"):
            self.gain_xp(out["xp"])
            bits.append(f"+{out['xp']} XP")
        if out.get("item"):
            self.offer_loot(h, 2, rarity=out["item"])
        if out.get("give"):
            # one particular piece, offered as a pick (so it can be handed to an ally, or left)
            self.push(h, {"type": "loot", "opts": [out["give"]]})
            bits.append(self.item(out["give"])["name"])
        if out.get("mat"):
            mat = self.rng.choice(I.MATERIALS) if out["mat"] == "random" else out["mat"]
            self.gain_item(h, mat)
            bits.append(self.item(mat)["name"])
        self.fx("event", h=h, key=ev["key"], text=out.get("text", ""), roll=roll, bits=bits)
        self.say(f"{hero['name']} — {ev['title']}: {out.get('text', '')}" + (f" ({', '.join(bits)})" if bits else ""))
        if out.get("quest"):
            self.quest_move(h, ev["key"], out["quest"])
        if out.get("fight"):
            # anyone on or next to the hex (and not already in a fight) joins in
            busy = {y for fs in self.s["fights"] for y in fs["heroes"]} | set((self.s["fight"] or {}).get("heroes", []))
            heroes = [h] + [y for y in self.living() if y != h and y not in busy
                            and Wd.dist(self.hero(y)["tile"], hero["tile"]) <= 1]
            self.s["fights"].append({"kind": "event", "tile": hero["tile"], "heroes": heroes, "foes": list(out["fight"]), "by": h,
                                     "win": out.get("win"), "ev": ev["key"]})
            if self.s["phase"] == "plan":
                self.s["after"] = "plan"
                self.next_step()

    @staticmethod
    def buffs_of(out):
        b = out.get("buff")
        return b if isinstance(b, list) else [b] if b else []

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

    def take_loot(self, h, key, to, equip, into=None):
        if to != h:
            self.say(f"{self.hero(h)['name']} hands the {self.item(key)['name']} to {self.hero(to)['name']}.")
        if equip and self.item(key)["slot"] != "use":
            self.wear(to, key, into if to == h else None)
        else:
            self.gain_item(to, key)

    def offer_pool(self, heroes, tier_bonus=0, rarity=None, extra=None):
        """After a fight: one pool of `POOL_SIZE` items for everyone who won it, of which
        `POOL_CLAIMS` can be claimed, first come first served. The claims go round the winners (a
        hero who won alone claims three times, two winners two and one); what's left is left behind."""
        heroes = list(heroes)
        if not heroes:
            return
        s = self.s
        pid = s["poolid"] = s.get("poolid", 0) + 1
        items = list(extra or [])
        items += self.make_loot(POOL_SIZE - len(items), tier_bonus, rarity)
        s.setdefault("pools", {})[str(pid)] = {"items": items, "taken": {}, "heroes": heroes}
        for i in range(POOL_CLAIMS):
            self.push(heroes[i % len(heroes)], {"type": "pool", "id": pid})

    def close_pool(self, pid):
        """Forget a pool once nobody has its dialog left to answer (or every claim is made)."""
        pool = self.s["pools"].get(str(pid))
        if pool and len(pool["taken"]) >= min(POOL_CLAIMS, len(pool["items"])):
            for q in self.s["pending"].values():
                q[:] = [d for d in q if not (d["type"] == "pool" and d["id"] == pid)]
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
            pool = [k for k in self.gear() if self.item(k)["rarity"] == r and k not in opts] or \
                [k for k in self.gear() if k not in opts]
            if self.rng.chance(0.2):
                pool = [k for k in I.CONSUMABLES if k not in opts] or pool
            opts.append(self.rng.choice(pool))
        return opts

    def gain_item(self, h, key):
        hero = self.hero(h)
        it = self.item(key)
        slot = it["slot"]
        free = [s for s in slots_for(slot) if not hero["equip"].get(s)] if slot != "use" else []
        if free:
            hero["equip"][free[0]] = key
        else:
            hero["bag"].append(key)
        self.say(f"{hero['name']} gets {it['name']}.")

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
                pool = [k for k in self.gear() if self.item(k)["rarity"] == r and k not in stock] or self.gear()
                stock.append(self.rng.choice(pool))
            self.s["shops"][key] = stock + ["potion", "big_potion", "bomb", "ward_scroll", "smelling_salts"]
        return self.s["shops"][key]

    def price_for(self, h, key):
        p = self.price(key)
        if self.has_class("herald"):
            p = p * 8 // 10
        return p

    def do_buy(self, h, msg):
        self.town(h)  # checks the hero can shop
        t = self.hero(h)["tile"]
        stock = self.shop(t)
        key = msg.get("item")
        ship = self.opp_at(t)
        if ship and ship["kind"] == "ship" and key in ship["stock"] and key not in stock:
            stock = ship["stock"]
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
        return self.price(key) * self.sell_rate(h) // 100

    def sell_rate(self, h):
        p = self.place(self.hero(h)["tile"])
        fence = A.FENCE_BONUS if p and p.get("spec") == "fence" else 0
        return (60 if self.mods(h).get("haggler") else 40) + fence

    # ------------------------------------------------------------------ town trades

    def town_spec(self, h, spec):
        p = self.town(h)
        if p.get("spec") != spec:
            raise Invalid(f"There's no {A.TOWN_SPECS[spec]['name'].lower()} here.")
        return p

    # ------------------------------------------------------------------ worked gear (tempered, enchanted)

    def item(self, key):
        """An item's data: the catalogue's, or for worked gear ("rapier@3") the catalogue's with the
        work's die, kinds and the list of works done (`work`)."""
        rec = self.s.get("forged", {}).get(key)
        if rec is None:
            return I.ITEMS[key]
        return {**I.ITEMS[rec["base"]], "die": rec["die"], "dk": rec["dk"], "work": rec["work"], "base": rec["base"]}

    def gear(self):
        """The loot this run can turn up: every piece in the catalogue, less the regional pieces of
        regions it didn't draw (the original three regions' gear has no region and is always in)."""
        regs = tuple(self.regions())
        c = getattr(self, "_gear", None)
        if c is None or c[0] != regs:
            self._gear = c = (regs, [k for k in I.GEAR if I.ITEMS[k].get("region") in (None,) + regs])
        return c[1]

    def price(self, key):
        return I.price(key) + A.WORK_RESALE * len(self.item(key).get("work", []))

    def works(self, key):
        """The work done on a piece of gear that counts against its limit (Starmetal and Wyrm's Ember don't)."""
        return sum(1 for w in self.item(key).get("work", []) if not w.startswith("star:"))

    def rework(self, key, die, dk, what):
        """Record one more work on a piece of gear; returns its key (a new one the first time)."""
        forged = self.s.setdefault("forged", {})
        rec = forged.get(key)
        if rec is None:
            n = self.s["forge_n"] = self.s.get("forge_n", 0) + 1
            rec = {"base": key, "work": []}
            key = f"{key}@{n}"
            forged[key] = rec
        rec.update(die=die, dk=dk)
        rec["work"].append(what)
        return key

    def unforge(self, key):
        """Forget a worked item's record once it's gone (sold, reforged)."""
        self.s.get("forged", {}).pop(key, None)

    def temper_face(self, it):
        """The special face Mark puts on a die: a shield on armor; else more of the die's own kind (a
        burn, freeze or poison face as strong as its strongest); else a wild face."""
        if it["slot"] == "armor":
            return "S"
        tagged = [f for f in it["die"] if isinstance(f, str) and f[0] in "FIP" and f[1:].isdigit()]
        if tagged:
            return max(tagged, key=lambda f: int(f[1:]))
        return "W"

    def temper_options(self, key, free=False):
        """What the smith can do to a piece of gear: {what: (new faces, cost)}, empty at the cap
        (`free`: what a forge material can do, whatever the cap, for nothing)."""
        it = self.item(key)
        die = it.get("die")
        n = self.works(key)
        if not die or (n >= A.WORK_CAP and not free):
            return {}
        cost = 0 if free else A.TEMPER_COST[it["rarity"]][n]
        nums = [i for i, f in enumerate(die) if isinstance(f, int)]
        out = {}
        if nums:
            top = max(die[i] for i in nums)
            low = min(nums, key=lambda i: die[i])
            if die[low] < top:
                hone = list(die)
                hone[low] = min(top, die[low] + A.HONE_UP)
                # numbers stay in order on the die; special faces keep their places
                for i, v in zip(nums, sorted(hone[i] for i in nums)):
                    hone[i] = v
                out["hone"] = (hone, cost)
            if len(nums) > 1:
                mark = list(die)
                mark[low] = self.temper_face(it)
                out["mark"] = (mark, cost)
        return out

    def do_temper(self, h, msg):
        p = self.town_spec(h, "smith")
        hero = self.hero(h)
        slot = msg.get("slot")
        key = hero["equip"].get(slot) if slot in SLOTS else None
        if not key:
            raise Invalid("Temper what?")
        opts = self.temper_options(key)
        what = msg.get("what")
        if what not in opts:
            raise Invalid("The smith can't do that to it." if self.works(key) < A.WORK_CAP else "It can't take any more work.")
        die, cost = opts[what]
        if hero["gold"] < cost:
            raise Invalid("You can't afford that.")
        hero["gold"] -= cost
        it = self.item(key)
        hero["equip"][slot] = new = self.rework(key, die, list(it.get("dk", [])), what)
        self.fx("coins", h=h, n=-cost)
        self.fx("temper", h=h, slot=slot, what=what)
        self.say(f"The smith {'hones' if what == 'hone' else 'marks'} {hero['name']}'s {it['name']} "
                 f"({self.works(new)} of {A.WORK_CAP} works).")

    def enchant(self, h, i, slot):
        """Rub the material at bag index `i` into the gear in `slot`: its die gains the material's kind."""
        hero = self.hero(h)
        mat = I.ITEMS[hero["bag"][i]]
        key = hero["equip"].get(slot) if slot in SLOTS else None
        if not key:
            raise Invalid("Enchant what? Pick a piece of gear you wear.")
        it = self.item(key)
        if mat.get("forge"):
            # Starmetal hones, Wyrm's Ember marks: like the smith, but free and past the work limit
            what = mat["forge"]
            opts = self.temper_options(key, free=True)
            if what not in opts:
                raise Invalid("Its die can't take that.")
            hero["bag"].pop(i)
            hero["equip"][slot] = self.rework(key, opts[what][0], list(it.get("dk", [])), "star:" + what)
            self.fx("temper", h=h, slot=slot, what=what)
            self.say(f"{hero['name']} works the {mat['name']} into the {it['name']}: its die "
                     f"{'is honed' if what == 'hone' else 'gains a special face'} (free of its work limit).")
            return
        kind = mat["enchant"]
        if kind in it.get("dk", []):
            raise Invalid(f"Its die is already {kind.capitalize()}.")
        if self.works(key) >= A.WORK_CAP:
            raise Invalid("It can't take any more work.")
        hero["bag"].pop(i)
        hero["equip"][slot] = new = self.rework(key, list(it["die"]), list(it.get("dk", [])) + [kind], kind)
        hero["hp"] = min(hero["hp"], self.maxhp(h))
        self.fx("temper", h=h, slot=slot, what=kind)
        self.say(f"{hero['name']} rubs the {mat['name']} into the {it['name']}: its die is {kind.capitalize()} now "
                 f"({self.works(new)} of {A.WORK_CAP} works).")

    def reforge_cost(self, key):
        """What the smith charges to reforge an item (None if it can't get better)."""
        r = self.item(key)["rarity"]
        i = I.RARITIES.index(r)
        return A.REFORGE_COST[I.RARITIES[i + 1]] if i + 1 < len(I.RARITIES) else None

    def do_reforge(self, h, msg):
        self.town_spec(h, "smith")
        hero = self.hero(h)
        slot = msg.get("slot")
        key = hero["equip"].get(slot) if slot in SLOTS else None
        if not key:
            raise Invalid("Reforge what?")
        cost = self.reforge_cost(key)
        if cost is None:
            raise Invalid("It can't get any better.")
        p = self.place(hero["tile"])
        if p.get("voucher"):
            cost = 0
        if hero["gold"] < cost:
            raise Invalid("You can't afford that.")
        up = I.RARITIES[I.RARITIES.index(self.item(key)["rarity"]) + 1]
        pool = [k for k in self.gear() if self.item(k)["slot"] == self.item(key)["slot"] and self.item(k)["rarity"] == up and k != I.base(key)]
        if not pool:
            raise Invalid("The smith has nothing better for that slot.")
        hero["gold"] -= cost
        if not cost:
            p["voucher"] -= 1
        new = self.rng.choice(pool)
        old = self.item(key)["name"]  # before unforge drops a worked piece's record
        self.unforge(key)
        hero["equip"][slot] = new
        hero["hp"] = min(hero["hp"], self.maxhp(h))
        self.fx("coins", h=h, n=-cost)
        self.say(f"The smith reforges {hero['name']}'s {old} into {self.item(new)['name']}.")

    def do_temple(self, h, msg):
        p = self.town_spec(h, "temple")
        hero = self.hero(h)
        if msg.get("what") == "revive":
            if p.get("revive_sold"):
                raise Invalid("The temple has no more to give.")
            cost = 0 if p.get("voucher") else A.TEMPLE_REVIVE
            if hero["gold"] < cost:
                raise Invalid("You can't afford that.")
            hero["gold"] -= cost
            if not cost:
                p["voucher"] -= 1
            p["revive_sold"] = True
            self.s["revives"] += 1
            if cost:
                self.fx("coins", h=h, n=-cost)
            self.say(f"{hero['name']} pays for the temple's blessing: +1 revive.")
        else:
            curses = [b for b in hero["buffs"] if A.BUFFS.get(b, {}).get("curse")]
            if not curses:
                raise Invalid("You aren't cursed.")
            for b in curses:
                del hero["buffs"][b]
            self.say(f"The temple lifts {hero['name']}'s curses.")

    def do_chart(self, h, msg):
        p = self.town_spec(h, "cartographer")
        hero = self.hero(h)
        reg = msg.get("region")
        if reg not in self.regions() + ["peak"]:
            raise Invalid("A chart of where?")
        cost = 0 if p.get("voucher") else A.CHART_COST
        if hero["gold"] < cost:
            raise Invalid("You can't afford that.")
        w = self.s["world"]
        tiles = [t for t in range(Wd.W * Wd.H) if (w["reg"][t] or "peak") == reg and self.terrain(t) in Wd.COST]
        if all(self.s["seen"][t] for t in tiles):
            raise Invalid("You've already seen all of it.")
        hero["gold"] -= cost
        if not cost:
            p["voucher"] -= 1
        for t in tiles:
            self.s["seen"][t] = 1
        if cost:
            self.fx("coins", h=h, n=-cost)
        self.say(f"{hero['name']} buys a chart of {A.REGION_NAMES[reg]}.")

    def do_sell(self, h, msg):
        self.town(h)
        hero = self.hero(h)
        i = msg.get("bag")
        if not isinstance(i, int) or not 0 <= i < len(hero["bag"]):
            raise Invalid("Sell what?")
        key = hero["bag"].pop(i)
        n = self.sell_price(h, key)
        hero["gold"] += n
        self.say(f"{hero['name']} sells {self.item(key)['name']} for {n} gold.")
        self.unforge(key)

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

    # ------------------------------------------------------------------ jobs

    def town_jobs(self, t):
        """A town's notice board: `JOBS_PER_BOARD` jobs of different kinds, made when a hero first
        stands in the town (not when it's looked at, so the view never changes the run)."""
        p = self.place(t)
        if "jobs" not in p:
            jobs = []
            for kind in self.rng.shuffle(list(A.JOB_KINDS)):
                j = self.make_job(t, kind)
                if j:
                    jobs.append(j)
                if len(jobs) >= A.JOBS_PER_BOARD:
                    break
            p["jobs"] = jobs
        return p["jobs"]

    def job_targets(self):
        return {q.get("tile") for q in self.s["quests"] if not q["done"] and not q.get("failed")}

    def make_job(self, t, kind):
        """One job offer from town t, or None if there's nothing of that kind to do."""
        s = self.s
        places = s["world"]["places"]
        busy = self.job_targets()
        job = {"kind": kind}
        if kind == "deliver":
            towns = [int(k) for k, q in places.items() if q["kind"] == "town" and int(k) != t]
            if not towns:
                return None
            to = self.rng.choice(towns)
            job.update(to=to, tile=to, name=self.place(to)["name"])
            trip = Wd.dist(t, to)
        elif kind == "lair":
            lairs = [g for g in s["groups"] if g["lair"] and (self.place(g["tile"]) or {}).get("kind") == "lair"
                     and g["tile"] not in busy]
            if not lairs:
                return None
            g = min(lairs, key=lambda g: Wd.dist(g["tile"], t))
            job.update(group=g["id"], tile=g["tile"])
            trip = Wd.dist(t, g["tile"])
        elif kind == "bounty":
            lo, hi = A.BOUNTY_RANGE
            cands = [x for x in range(Wd.W * Wd.H) if self.terrain(x) in Wd.COST and self.terrain(x) != "town"
                     and not self.place(x) and not self.group_at(x) and lo <= Wd.dist(x, t) <= hi]
            if not cands:
                return None
            used = {q.get("crew") for q in s["quests"]} | {j.get("crew") for q in places.values() for j in q.get("jobs", [])}
            names = [n for n in A.BOUNTY_NAMES if n not in used] or A.BOUNTY_NAMES
            job.update(tile=self.rng.choice(cands), crew=self.rng.choice(names))
            trip = Wd.dist(t, job["tile"]) + 2  # they run
        else:  # salvage
            wrecks = [int(k) for k, q in places.items() if q["kind"] == "wreck" and int(k) not in busy and 3 <= Wd.dist(int(k), t) <= 12]
            if not wrecks:
                return None
            w = self.rng.choice(wrecks)
            job.update(tile=w, guarded=bool(self.place(w).get("guard") and not self.place(w).get("done")))
            trip = 2 * Wd.dist(t, w)
        job["turns"] = -(-trip // A.JOB_PACE) + A.JOB_SLACK[kind]
        gold = A.JOB_GOLD + A.JOB_PER_HEX * trip + A.JOB_BONUS[kind]
        spec = self.place(t).get("spec")
        weights = [(k, w) for k, w in A.JOB_REWARDS.items() if k != "trade" or spec in ("smith", "cartographer", "temple")]
        kind_r = self.rng.weighted(weights)
        r = {"gold": round(gold * A.JOB_GOLD_CUT[kind_r]), "type": kind_r}
        if kind_r == "item":
            r["item"] = self.rng.choice([k for k in self.gear() if self.item(k)["rarity"] == "rare"])
        if kind_r == "trade":
            r["spec"] = spec
        job["reward"] = r
        return job

    def do_quest(self, h, msg):
        p = self.town(h)
        t = self.hero(h)["tile"]
        jobs = p.get("jobs") or []
        n = msg.get("n", 0)
        if p.get("quest_taken") or not isinstance(n, int) or not 0 <= n < len(jobs):
            raise Invalid("There's no work going here.")
        s = self.s
        p["quest_taken"] = True
        s["jobid"] = s.get("jobid", 0) + 1
        q = dict(jobs[n], id=s["jobid"], done=False, failed=False, src=p["name"], src_tile=t,
                 until=s["turn"] + jobs[n]["turns"] - 1)
        if q["kind"] == "bounty":
            spot = q["tile"]
            if self.group_at(spot) or self.place(spot):
                free = [x for x in Wd.within(spot, 2) if self.terrain(x) in Wd.COST and self.terrain(x) != "town"
                        and not self.place(x) and not self.group_at(x)]
                spot = free[0] if free else spot
            reg = self.near_region(spot)
            foes = list(self.rng.choice(A.GROUPS[reg][3:7]))
            i = max(range(len(foes)), key=lambda k: A.FOES[foes[k]]["hp"])
            foes[i] = {"k": foes[i], "aff": self.rng.choice(A.ROAM_ELITES)}
            g = self.add_group(spot, foes)
            g["bounty"], g["crew"] = q["id"], q["crew"]
            q["group"], q["tile"] = g["id"], spot
        if q["kind"] == "salvage":
            q["stage"] = "fetch"
        s["quests"].append(q)
        self.say(f"{self.hero(h)['name']} takes a job in {p['name']}: {self.job_line(q)} ({q['turns']} turns).")

    def job_line(self, q):
        if q["kind"] == "trail":
            return f"the quest {A.QUESTS[q['key']]['name']}"
        if q["kind"] == "deliver":
            return f"a parcel for {q['name']}"
        if q["kind"] == "lair":
            return "clear a lair"
        if q["kind"] == "bounty":
            return f"the bounty on {q['crew']}"
        return "salvage from a wreck"

    def tick_jobs(self):
        """A new turn: jobs past their deadline fail (a wanted crew gets away)."""
        s = self.s
        for q in s["quests"]:
            if q["done"] or q.get("failed"):
                continue
            lost = q["kind"] == "salvage" and q.get("stage") == "return" and not self.hero(q["carrier"])["alive"]
            if q.get("until", 1e9) < s["turn"] or lost:
                q["failed"] = True
                if q["kind"] == "bounty":
                    s["groups"] = [g for g in s["groups"] if g.get("bounty") != q["id"]]
                self.say(f"The job for {q['src']} has failed: {self.job_line(q)}" + (" (the crew got away)." if q["kind"] == "bounty" else "."))

    def job_land(self, h, t):
        """A hero standing on t at the end of a turn: a delivery made, salvage picked up or brought home."""
        for q in self.s["quests"]:
            if q["done"] or q.get("failed"):
                continue
            if q["kind"] == "trail":
                self.trail_land(h, q, t)
            elif q["kind"] == "deliver" and q["to"] == t:
                self.complete_quest(q, h)
            elif q["kind"] == "salvage" and q.get("stage") == "fetch" and q["tile"] == t and not self.group_at(t):
                q["stage"], q["carrier"] = "return", h
                self.say(f"{self.hero(h)['name']} hauls the cargo out of the wreck. Now back to {q['src']}.")
            elif q["kind"] == "salvage" and q.get("stage") == "return" and q["carrier"] == h and q["src_tile"] == t:
                self.complete_quest(q, h)

    def job_step(self, h, t):
        """What standing on t would do for a job: "job" (finish one), "cargo" (pick salvage up) or None."""
        for q in self.s["quests"]:
            if q["done"] or q.get("failed"):
                continue
            if q["kind"] == "trail" and q["tile"] == t and not self.group_at(t):
                return "quest"
            if (q["kind"] == "deliver" and q["to"] == t) or \
                    (q["kind"] == "salvage" and q.get("stage") == "return" and q["carrier"] == h and q["src_tile"] == t):
                return "job"
            if q["kind"] == "salvage" and q.get("stage") == "fetch" and q["tile"] == t and not self.group_at(t):
                return "cargo"
        return None

    def job_goal(self, q, h=None):
        """Where a job wants a hero to go next."""
        if q["kind"] == "bounty":
            g = next((g for g in self.s["groups"] if g.get("bounty") == q["id"]), None)
            return g["tile"] if g else None
        if q["kind"] == "salvage" and q.get("stage") == "return":
            return q["src_tile"]
        return q["tile"]

    def complete_quest(self, q, h):
        q["done"] = True
        r = q.get("reward") or {"gold": A.QUEST_REWARD, "type": "loot"}
        for x in self.living():
            self.hero(x)["gold"] += r["gold"]
        typ, extra = r["type"], ""
        if typ == "loot":
            self.offer_loot(h, 2, tier_bonus=1)
        elif typ == "item":
            self.push(h, {"type": "loot", "opts": [r["item"]]})
            extra = f", and {self.item(r['item'])['name']}"
        elif typ == "revive":
            self.s["revives"] += 1
            extra = ", and +1 revive"
        elif typ == "trade":
            src = self.place(q["src_tile"])
            src["voucher"] = src.get("voucher", 0) + 1
            extra = f", and a free go at {q['src']}'s {A.TOWN_SPECS[r['spec']]['name'].lower()}"
        elif typ == "restock":
            self.restock(q["src_tile"])
            extra = f", and {q['src']} restocks its shop with better wares"
        self.say(f"Job done for {q['src']}: +{r['gold']} gold each{extra}.")
        self.fx("job", h=h, src=q["src"], gold=r["gold"], extra=extra)

    def wear(self, h, key, into=None):
        """Put new gear straight on; what it replaces goes in the bag."""
        hero = self.hero(h)
        slot = self.equip_slot(h, key, into)
        old = hero["equip"].get(slot)
        hero["equip"][slot] = key
        if old:
            hero["bag"].append(old)
        hero["hp"] = min(hero["hp"], self.maxhp(h))
        self.say(f"{hero['name']} puts on the {self.item(key)['name']}.")

    def do_equip(self, h, msg):
        if self.in_fight(h):
            raise Invalid("Not in the middle of a fight.")
        hero = self.hero(h)
        i = msg.get("bag")
        if not isinstance(i, int) or not 0 <= i < len(hero["bag"]):
            raise Invalid("Equip what?")
        key = hero["bag"][i]
        if self.item(key)["slot"] == "use":
            raise Invalid("That's not something you wear.")
        slot = self.equip_slot(h, key, msg.get("into"))
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
        self.unforge(hero["bag"].pop(i))

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
        it = self.item(key)
        if it["slot"] != "use":
            raise Invalid("You can't use that.")
        if it.get("enchant") or it.get("forge"):
            if self.in_fight(h):
                raise Invalid("Not in the middle of a fight.")
            self.enchant(h, i, msg.get("slot"))
            return
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
                   "aff": [f.get("aff") for f in g["foes"]], "prize": g.get("prize"), "crew": g.get("crew"),
                   "sea": g.get("sea", False), "raid": g.get("raid"), "occupy": g.get("occupy", False)}
                  for g in s["groups"] if g["tile"] in vis or (g["lair"] and s["seen"][g["tile"]]) or g.get("bounty")
                  or g.get("raid") or g.get("sighted", 0) >= s["turn"]]
        raids = []
        for g in s["groups"]:
            if g.get("raid"):
                road = [] if g.get("occupy") else (self.raid_road(g["tile"], g["raid"]["to"]) or [])
                raids.append({"g": g["id"], "tile": g["tile"], "to": g["raid"]["to"], "reg": g["raid"]["reg"],
                              "occupy": g.get("occupy", False), "road": road})
        heroes = []
        for h in range(3):
            hero = s["heroes"][h]
            heroes.append({**{k: v for k, v in hero.items() if k not in ("tags",)}, "maxhp": self.maxhp(h),
                           "moves": self.moves(h), "sight": self.enemy_sight(h), "dice": [{"faces": d["faces"], "dk": d["dk"], "src": d["src"]} for d in self.dice_of(h)], "sellrate": self.sell_rate(h),
                           "actions": self.actions_of(h)})
        places = {}
        for t, p in s["world"]["places"].items():
            if s["seen"][int(t)] and not (p.get("hidden") and not p.get("found")):
                q = {k: v for k, v in p.items() if k not in ("quest", "jobs")}
                if p["kind"] == "event" and p.get("ev"):
                    ev = next(e for e in A.EVENTS if e["key"] == p["ev"])
                    q["title"], q["risk"] = ev["title"], A.event_risk(ev)
                    q["needs"] = sorted({ch["need"] for ch in ev["choices"] if ch.get("need")})
                if p["kind"] == "town":
                    q["docks"] = self.docks(int(t))
                    if any(self.hero(x)["tile"] == int(t) for x in self.living()):
                        q["shop"] = self.shop(int(t))
                        q["jobs"] = [] if p.get("quest_taken") else p.get("jobs", [])
                        ship = self.opp_at(int(t))
                        if ship and ship["kind"] == "ship":
                            q["ship"] = ship["stock"]
                places[t] = q
        return {
            "turn": s["turn"], "sea": s["sea"], "rises": s["rises"], "tide": self.tide(), "phase": s["phase"],
            "result": s["result"], "diff": s["diff"], "rise_every": self.diff()["rise"],
            "grow_from": GROW_FROM, "tidenews": s.get("tidenews", []), "next_tide": TIDE_EVERY - (s["turn"] - 1) % TIDE_EVERY,
            "next_rise": self.diff()["rise"] - (s["turn"] - 1) % self.diff()["rise"], "tides": s.get("tides", 0),
            "seen": "".join(map(str, s["seen"])), "places": places, "groups": groups, "heroes": heroes,
            "xp": s["xp"], "level": s["level"], "xp_next": C.XP_FOR[s["level"]] if s["level"] < C.MAX_LEVEL else None,
            "xp_this": C.XP_FOR[s["level"] - 1], "revives": s["revives"], "cleared": s["cleared"],
            "dungeon": s["dungeon"], "fork": s.get("fork"), "dnext": s.get("dnext", {}), "plans": s["plans"], "pending": s["pending"], "pools": s.get("pools", {}), "fight": self.fight_view(),
            "forecast": self.forecast(),
            "merchants": self.merchants_view(),
            "quests": [dict(q, left=q["until"] - s["turn"] + 1 if "until" in q else None, goal=self.job_goal(q))
                       for q in s["quests"]], "log": s["log"][-12:], "fx": s["fx"][-60:],
            "stats": s["stats"], "waiting": self.waiting(), "inn": self.inn_cost(),
            "skiff_cost": SKIFF_COST, "herald": self.has_class("herald"),
            "opps": [{"id": o["id"], "kind": o["kind"], "tile": o["tile"], "left": o["until"] - s["turn"] + 1,
                      "used": o["used"]} for o in s.get("opps", [])],
            "garrison": {reg: {"foes": self.garrison_of(reg)[0], "boss": round(self.garrison_of(reg)[1] * 100),
                               "n": len(s.get("garrison", {}).get(reg, []))} for reg in self.regions()},
            "dungeon_step": {"hp": round(100 * DUNGEON_STEP_HP[min(self.tier(), 2)] * (1 + 0.15 * self.tier())),
                             "dmg": round(100 * DUNGEON_STEP_DMG[min(self.tier(), 2)] * (1 + 0.1 * self.tier()))},
            "garrison_next": self.diff()["rise"] - (s["turn"] - 1) % self.diff()["rise"],  # with the Great Tide
            "crown_cut": round(A.CROWN_CUT * s.get("crown_cut", 0) * 100),
            "reforge": {k: self.reforge_cost(k) for h in self.living() for k in self.hero(h)["equip"].values() if k},
            "temper": {k: self.temper_options(k) for h in self.living() for k in self.hero(h)["equip"].values() if k},
            "forged": {k: {**self.item(k), "price": self.price(k)} for k in s.get("forged", {})},
            "loans": [{"h": c["h"], "left": c["turn"] - s["turn"]} for c in s.get("chains", []) if c["kind"] == "loan"],
            "raids": raids, "garrison_skip": s.get("garrison_skip", {}),
            "squalls": [{"id": q["id"], "tile": q["tile"], "next": Wd.step_dir(q["tile"], q["dir"]), "left": q["until"] - s["turn"] + 1,
                         "kind": q.get("kind", "squall")} for q in s.get("squalls", [])],
            "lava": {t: until - s["turn"] + 1 for t, until in s.get("lava", {}).items()},
            "trails": {t: until - s["turn"] + 1 for t, until in s.get("trails", {}).items()},
            "erupt": (s.get("erupt", A.ERUPT_FROM) - s["turn"]) if "ash" in self.regions() else None,
            "raid_next": (A.RAID_EVERY - (s["turn"] - A.RAID_FROM) % A.RAID_EVERY) if s["turn"] >= A.RAID_FROM else A.RAID_FROM - s["turn"],
        }


def static():
    """Content the browser needs once: classes, actions, items, foes, events, buffs."""
    acts = {k: {**v, "def": C.is_defensive(v), "short": C.SHORT.get(k)} for k, v in {**I.WEAPON_ACTIONS, **C.ACTIONS}.items()}
    return {
        "classes": C.CLASSES, "actions": acts, "passives": C.PASSIVES, "items": I.ITEMS, "foes": A.FOES,
        "events": {e["key"]: e for e in A.EVENTS}, "buffs": A.BUFFS, "regions": A.REGION_NAMES,
        "town_specs": A.TOWN_SPECS, "job_kinds": A.JOB_KINDS, "opps": A.OPPS, "temple_revive": A.TEMPLE_REVIVE, "chart_cost": A.CHART_COST, "garrison_every": A.GARRISON_EVERY,
        "dungeons": {k: v["name"] for k, v in A.DUNGEONS.items()}, "paths": A.PATHS, "elites": A.ELITES, "combos": C.COMBOS, "xp_for": C.XP_FOR,
        "prices": {k: I.price(k) for k in I.ITEMS},
        "map": {"w": Wd.W, "h": Wd.H, "cost": Wd.COST, "fast": Wd.FAST, "jungle": Wd.JUNGLE_COST, "sink": Wd.SINK_COST},
        "grounds": A.GROUNDS, "squall": {"r": A.SQUALL_R, "sight": A.SQUALL_SIGHT}, "lookout_sight": A.LOOKOUT_SIGHT,
        "work": {"cap": A.WORK_CAP, "hone": A.HONE_UP, "cost": A.TEMPER_COST},
        "quests": A.QUESTS,
        "travel": {"beacon_sight": A.BEACON_SIGHT, "markup": A.MERCHANT_MARKUP, "wait": A.MERCHANT_WAIT, "step": A.MERCHANT_STEP},
        "biome": {"skins": A._B.SKINS, "rules": A._B.RULES, "storms": A.STORMS, "trail_turns": A.TRAIL_TURNS, "lava_turns": A.LAVA_TURNS,
                  "erupt_every": A.ERUPT_EVERY, "jungle_sight": A.JUNGLE_SIGHT, "prism_sight": A.PRISM_SIGHT, "grace": round(A.GRACE_REST * 100),
                  "fossil_xp": A.FOSSIL_XP, "jungle": Wd.JUNGLE_COST, "sink": Wd.SINK_COST},
        "sea": {"cove_gold": A.COVE_GOLD, "flotsam_gold": A.FLOTSAM_GOLD, "hunt": A.SEA_HUNT, "grotto_gold": A.GROTTO_GOLD,
                "raid_bounty": A.RAID_BOUNTY, "free_gold": A.FREE_GOLD},
    }
