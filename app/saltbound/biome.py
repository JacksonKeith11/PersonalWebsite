"""The other regions' map rules, mixed into `Game`: what each region's land does as the party crosses it.

- Cinderreach (`ash`): the volcano erupts every `ERUPT_EVERY` turns (with a turn's warning): lava runs down
  from the crater and blocks the hexes it covers (`s["lava"]`, hex -> the turn it cools).
- The Shifting Sands (`dunes`): quicksand (`world["sink"]`) costs a whole turn's moves; sandstorms drift
  over the dunes; oases heal fully and lift curses (once per hero).
- The Stillwood (`petrified`): time stands still: blessings and curses don't run down for a hero standing
  there; fossil beds hold old treasure.
- The Verdant Deep (`jungle`): deep jungle costs `JUNGLE_COST`, but a hex someone has walked through is a
  trail (`s["trails"]`) for `TRAIL_TURNS` turns that costs 1 for everyone; inside it you see 2 hexes.
- Aetherhold (`heaven`): light-gates carry whoever ends a move on one to its twin; resting there heals
  more, and its shrines bless everyone on the hex.
- The Prism Wood (`crystal`): everyone sees further there, and its enemies notice you from further off;
  geodes hold enchant materials.
- The Drowsing Vale (`dream`): resting anywhere there heals like a camp, but brings a dream (an event).
- The Frostpeaks (`frost`): the sea round it is frozen (`world["ice"]`: walk it, no skiff); blizzards blow
  across; ending a turn on its glacier or summit, away from a town or camp, gives Frostbite.
Each only happens if the world drew that region. `rules.js` mirrors the step costs.
"""

from . import world as Wd
from .content import archipelago as A
from .content import items as I


class Biomes:
    # ------------------------------------------------------------------ where

    def region_here(self, t):
        """The objective region a hex belongs to, if it's one this run drew (else None)."""
        r = self.s["world"]["reg"][t]
        return r if r in self.regions() else None

    def deep_jungle(self, t):
        return self.region_here(t) == "jungle" and self.s["world"]["bio"][t] == "forest" and self.terrain(t) == "forest"

    # ------------------------------------------------------------------ moving

    def lava_at(self, t):
        return str(t) in self.s.get("lava", {})

    def boon_mods(self, h):
        """A hero's boons' mods (the quests' permanent buffs: some bend a map rule, sandwalk, junglewalk,
        frostborn). Cheaper than `mods` for route-finding, which asks for every step."""
        out = {}
        for b in self.hero(h)["buffs"]:
            if A.BUFFS[b].get("perm"):
                for k, v in A.BUFFS[b]["mods"].items():
                    out[k] = out.get(k, 0) + v
        return out

    def land_cost(self, h, t, b, fast):
        """The cost on foot of entering land hex b of terrain t (before the skiff's landing cost)."""
        cost = Wd.COST.get(t, 1)
        m = self.boon_mods(h)
        if t == "forest" and self.deep_jungle(b) and str(b) not in self.s.get("trails", {}) and not m.get("junglewalk"):
            cost = Wd.JUNGLE_COST
        if (fast and t != "ice") or (t == "ice" and m.get("frostborn")):
            cost = 1
        if b in self.sinks() and not m.get("sandwalk"):
            cost = Wd.SINK_COST
        return cost

    def sinks(self):
        w = self.s["world"]
        c = getattr(self, "_sinks", None)
        if c is None or c[0] is not w:
            self._sinks = c = (w, set(w.get("sink", [])), set(w.get("ice", [])))
        return c[1]

    def iced(self, t):
        self.sinks()
        return t in self._sinks[2]

    def cut_trail(self, b):
        """A hero walked through a deep-jungle hex: it's a trail for a while."""
        if self.deep_jungle(b):
            self.s.setdefault("trails", {})[str(b)] = self.s["turn"] + A.TRAIL_TURNS

    # ------------------------------------------------------------------ seeing

    def storm_sight(self, t):
        """How far a hero sees inside a storm (a squall, sandstorm or blizzard) at t, or None."""
        best = None
        for q in self.s.get("squalls", []):
            if Wd.dist(t, q["tile"]) <= A.SQUALL_R:
                sight = A.STORMS[q.get("kind", "squall")]["sight"]
                best = sight if best is None else min(best, sight)
        return best

    def biome_sight(self, h, base):
        t = self.hero(h)["tile"]
        if self.deep_jungle(t):
            base = min(base, A.JUNGLE_SIGHT)
        elif self.region_here(t) == "crystal":
            base += A.PRISM_SIGHT
        return base

    def hunt_range(self, g):
        """How far off a roaming group notices heroes (further in the Prism Wood)."""
        return A.PRISM_HUNT if self.region_here(g["tile"]) == "crystal" else 3

    # ------------------------------------------------------------------ each turn

    def tick_biomes(self):
        """A new turn: the volcano, lava cooling, trails growing back, Frostbite on the glacier."""
        s = self.s
        turn = s["turn"]
        for key in ("lava", "trails"):
            d = s.get(key)
            if d:
                for t in [t for t, until in d.items() if until < turn]:
                    del d[t]
        if "ash" in self.regions() and turn >= A.ERUPT_FROM - 1:
            nxt = s.setdefault("erupt", A.ERUPT_FROM)
            if turn == nxt - 1:
                self.say("The volcano on Cinderreach rumbles: it will erupt next turn. Keep off its slopes.")
                self.fx("rumble", tile=self.crater())
            elif turn >= nxt:
                self.erupt()
                s["erupt"] = turn + A.ERUPT_EVERY
        if "frost" in self.regions():
            w = s["world"]
            for h in self.living():
                hero = self.hero(h)
                t = hero["tile"]
                p = self.place(t)
                if self.region_here(t) == "frost" and w["bio"][t] in ("hills", "peak") and not hero["afloat"] \
                        and not (p and p["kind"] in ("town", "camp")) and not self.boon_mods(h).get("frostborn"):
                    if "frostbite" not in hero["buffs"]:
                        self.say(f"{hero['name']} spends the night on the ice: Frostbite (−5 max HP until it thaws).")
                    self.buff(h, "frostbite")
                elif "frostbite" in hero["buffs"] and p and p["kind"] in ("town", "camp"):
                    del hero["buffs"]["frostbite"]
                    self.say(f"{hero['name']} thaws out by the fire.")

    def timeless(self, h):
        """A hero in the Stillwood: their blessings and curses don't run down this turn."""
        return self.region_here(self.hero(h)["tile"]) == "petrified"

    def crater(self):
        return next((int(t) for t, p in self.s["world"]["places"].items() if p["kind"] == "dungeon" and p["region"] == "ash"), None)

    def erupt(self):
        """Lava runs down from the crater: `LAVA_FLOWS` flows, each taking the steepest way down (with a
        little chance) for up to `LAVA_LEN` hexes, stopping at the sea. It never covers a town, a place,
        a hero or an enemy group, and cools after `LAVA_TURNS` turns."""
        s = self.s
        w = s["world"]
        top = self.crater()
        if top is None:
            return
        lava = s.setdefault("lava", {})
        held = {self.hero(h)["tile"] for h in self.living()} | {g["tile"] for g in s["groups"]} | \
            {q["tile"] for q in s["quests"] if q["kind"] == "trail" and not q["done"]}
        new = []
        for _ in range(A.LAVA_FLOWS):
            at, seen = top, {top}
            for _ in range(A.LAVA_LEN):
                opts = [n for n in Wd.neighbors(at) if n not in seen and w["elev"][n] > s["sea"] + 1]
                if not opts:
                    break
                opts.sort(key=lambda n: (w["elev"][n] + self.rng.random() * 3))
                at = opts[0]
                seen.add(at)
                if at in held or self.place(at) or w["bio"][at] == "town":
                    continue
                lava[str(at)] = s["turn"] + A.LAVA_TURNS
                new.append(at)
        if new:
            self.say(f"The volcano erupts! Lava runs down its slopes: {len(new)} hexes are blocked for {A.LAVA_TURNS} turns.")
            self.fx("erupt", tile=top, tiles=new)

    # ------------------------------------------------------------------ resting and landing

    def biome_rest(self, h, frac):
        """Resting: more in Aetherhold; anywhere in the Drowsing Vale as at a camp, with a dream."""
        t = self.hero(h)["tile"]
        r = self.region_here(t)
        if r == "heaven":
            frac += A.GRACE_REST
        elif r == "dream" and not self.place(t):
            frac = max(frac, A.DREAM_REST)
            dreams = [e["key"] for e in A.EVENTS if e.get("dream")]
            if dreams:
                self.push(h, {"type": "event", "key": self.rng.choice(dreams)})
                self.say(f"{self.hero(h)['name']} drifts off to sleep, and dreams.")
        return frac

    def biome_land(self, h, t, p):
        """The other regions' places: True if this was one of them."""
        hero = self.hero(h)
        k = p["kind"]
        if k == "oasis":
            if t not in hero["shrines"]:
                hero["shrines"].append(t)
                n = self.heal(h, self.maxhp(h))
                for b in [b for b in hero["buffs"] if A.BUFFS.get(b, {}).get("curse")]:
                    del hero["buffs"][b]
                self.fx("heal", to=f"h{h}", n=n)
                self.say(f"{hero['name']} drinks deep at the oasis: full health, and every curse washed off.")
            return True
        if k == "fossil":
            if not p.get("done"):
                p["done"] = True
                self.offer_loot(h, 3, tier_bonus=1)
                self.gain_xp(A.FOSSIL_XP)
                self.say(f"{hero['name']} digs out a fossil bed: old bones, older treasure (+{A.FOSSIL_XP} XP).")
            return True
        if k == "geode":
            if not p.get("done"):
                p["done"] = True
                self.say(f"{hero['name']} cracks open a geode.")
                self.gain_item(h, self.rng.choice(I.MATERIALS))
                self.fx("found", h=h, tile=t)
            return True
        if k == "gate":
            to = p.get("to")
            if to is not None and not self.group_at(to):
                hero["prev"], hero["tile"], hero["afloat"] = t, to, False
                self.reveal(to, self.vision(h))
                self.fx("gate", h=h, frm=t, to=to)
                self.say(f"{hero['name']} steps into the light-gate and out across the sea.")
            return True
        return False

    def bless_hex(self, h, t, buff):
        """Aetherhold's shrines bless everyone standing on the hex, not just whoever touched it."""
        if self.region_here(t) != "heaven":
            return
        for y in self.living():
            other = self.hero(y)
            if y != h and other["tile"] == t and t not in other["shrines"]:
                other["shrines"].append(t)
                self.buff(y, buff)
