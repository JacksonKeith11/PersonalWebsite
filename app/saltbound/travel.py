"""Beacon towers and travelling merchants, mixed into `Game`.

- **Beacons** (place kind `beacon`, `BEACONS` of them on high ground, spread out): the first hero to end a
  turn on one lights it for the party (`lit`), and the land `BEACON_SIGHT` hexes round it is revealed. A hero
  standing on a lit beacon can spend their move travelling to any other lit one (`do_beacon` sets the plan's
  `warp`; `resolve_turn` carries them there before anyone walks), so a party that has split up can regroup.
- **Merchants** (`s["merchants"]`, `MERCHANTS` of them): caravans that go from town to town over land and,
  between islands, by boat (`merchant_road`), `MERCHANT_STEP` hexes a turn, and wait `MERCHANT_WAIT` turns in each town. Each
  sells `MERCHANT_STOCK` rare and legendary pieces of this run's gear at `MERCHANT_MARKUP` times their
  price, restocking in every town. A hero on its hex can buy (`do_mbuy`); a caravan with a hero on it
  waits for them (up to `MERCHANT_HOLD` turns).
Old saves get both the first turn they're played (`ensure_travel`).
"""

from . import world as Wd
from .combat import Invalid
from .content import archipelago as A

MERCHANT_NAMES = ["Mother Ostra's caravan", "the Brass Peddler", "Old Fenwick's wagons", "the Saffron Caravan",
                  "Madame Quill's curiosities", "the Lantern Traders"]


class Travel:
    def ensure_travel(self, rng):
        s = self.s
        if not s.get("beacons_placed"):
            s["beacons_placed"] = True
            self.place_beacons(rng)
        if "merchants" not in s:
            s["merchants"] = []
            for _ in range(A.MERCHANTS):
                self.spawn_merchant(rng)

    # ------------------------------------------------------------------ beacons

    def place_beacons(self, rng):
        """`BEACONS` beacons on the highest open hills and peaks, `BEACON_GAP` hexes apart at least."""
        w = self.s["world"]
        places = w["places"]
        cands = [t for t in range(Wd.W * Wd.H) if w["bio"][t] in ("hills", "peak") and self.terrain(t) in Wd.COST
                 and self.terrain(t) != "town" and not self.place(t) and t != w["peak"]
                 and all(not self.place(n) for n in Wd.neighbors(t))]
        cands.sort(key=lambda t: -(w["elev"][t] + rng.random() * 2))
        chosen = []
        for t in cands:
            if all(Wd.dist(t, c) >= A.BEACON_GAP for c in chosen):
                chosen.append(t)
            if len(chosen) >= A.BEACONS:
                break
        for t in chosen:
            places[str(t)] = {"kind": "beacon"}

    def lit_beacons(self):
        return [int(t) for t, p in self.s["world"]["places"].items() if p["kind"] == "beacon" and p.get("lit")]

    def beacon_land(self, h, t, p):
        if p.get("lit"):
            return
        p["lit"] = True
        self.reveal(t, A.BEACON_SIGHT)
        self.say(f"{self.hero(h)['name']} lights a beacon: the land round it is on your map, and the party can "
                 f"travel between lit beacons ({len(self.lit_beacons())} lit).")
        self.fx("beacon", h=h, tile=t)

    def do_beacon(self, h, msg):
        """Plan to travel from the lit beacon you're on to another (`to`), or take it back (`to` None)."""
        if not self.can_plan(h):
            raise Invalid("Not now.")
        p = self.plan(h)
        to = msg.get("to")
        if to is None:
            p["warp"] = None
            return
        hero = self.hero(h)
        here = self.place(hero["tile"])
        if not (here and here["kind"] == "beacon" and here.get("lit")) or hero["afloat"]:
            raise Invalid("You need to be standing on a lit beacon.")
        if to not in self.lit_beacons() or to == hero["tile"]:
            raise Invalid("Travel to another lit beacon.")
        p.update(warp=to, path=[], rest=False, ready=False, rally=None)

    def warp(self, h, to, encounters):
        """A planned beacon journey: there in one go, before anyone walks."""
        hero = self.hero(h)
        frm = hero["tile"]
        hero["prev"], hero["tile"], hero["afloat"] = frm, to, False
        self.reveal(to, self.vision(h))
        self.fx("gate", h=h, frm=frm, to=to, how="beacon")
        self.say(f"{hero['name']} follows the beacons' light across the islands.")
        if self.group_at(to):
            encounters.append((to, h))

    # ------------------------------------------------------------------ merchants

    def towns(self):
        return [int(t) for t, p in self.s["world"]["places"].items() if p["kind"] == "town"]

    def spawn_merchant(self, rng):
        s = self.s
        used = {mer["tile"] for mer in s["merchants"]}
        towns = [t for t in self.towns() if t not in used and t != s["world"]["start"]] or self.towns()
        if not towns:
            return
        t = rng.choice(towns)
        names = [n for n in MERCHANT_NAMES if n not in {mer["name"] for mer in s["merchants"]}] or MERCHANT_NAMES
        s["mid"] = s.get("mid", 0) + 1
        mer = {"id": s["mid"], "name": rng.choice(names), "tile": t, "to": None, "road": [], "wait": A.MERCHANT_WAIT, "held": 0}
        mer["stock"] = self.merchant_stock(rng)
        s["merchants"].append(mer)

    def merchant_stock(self, rng):
        gear = self.gear()
        rare = [k for k in gear if self.item(k)["rarity"] == "rare"]
        legend = [k for k in gear if self.item(k)["rarity"] == "legendary"]
        stock = rng.sample(legend, min(len(legend), A.MERCHANT_LEGENDS))
        stock += rng.sample([k for k in rare if k not in stock], min(len(rare), A.MERCHANT_STOCK - len(stock)))
        return stock

    def merchant_at(self, t):
        return next((mer for mer in self.s.get("merchants", []) if mer["tile"] == t), None)

    def merchant_price(self, h, key):
        """A caravan's price: the item's price marked up, less the Herald's 20% like any shop's."""
        p = int(self.price(key) * A.MERCHANT_MARKUP)
        return p * 8 // 10 if self.has_class("herald") else p

    def tick_merchants(self):
        """A new turn: each caravan waits in town, or rolls on along its road (holding for a customer)."""
        for mer in self.s.get("merchants", []):
            if any(self.hero(x)["tile"] == mer["tile"] for x in self.living()) and mer["held"] < A.MERCHANT_HOLD:
                mer["held"] += 1
                continue
            mer["held"] = 0
            if mer["wait"] > 0:
                mer["wait"] -= 1
                continue
            if not mer["road"]:
                self.merchant_route(mer)
                if not mer["road"]:
                    mer["wait"] = A.MERCHANT_WAIT
                    continue
            for _ in range(A.MERCHANT_STEP):
                if not mer["road"] or self.group_at(mer["road"][0]):
                    break
                mer["tile"] = mer["road"].pop(0)
            if not mer["road"] and mer["tile"] == mer["to"]:
                mer["wait"], mer["stock"] = A.MERCHANT_WAIT, self.merchant_stock(self.rng)
                town = self.place(mer["tile"])
                if town and any(self.s["seen"][n] for n in [mer["tile"]] + Wd.neighbors(mer["tile"])):
                    self.say(f"{mer['name']} rolls into {town['name']} with new wares.")

    def merchant_route(self, mer):
        """The next town for a caravan: one it can reach by road, a fair way off, not the one it's in."""
        here = mer["tile"]
        opts = []
        for t in self.towns():
            if t == here:
                continue
            road = self.merchant_road(here, t)
            if road:
                opts.append((abs(len(road) - 10), self.rng.random(), t, road))
        if opts:
            _, _, mer["to"], mer["road"] = min(opts)

    def merchant_road(self, at, to):
        """A caravan's way to a town: over land and, between islands, by boat. It keeps off places and
        other towns (and the peak); the hexes after `at`, or None."""
        if at == to:
            return []
        w = self.s["world"]
        prev, edge = {at: None}, [at]
        while edge and to not in prev:
            nxt = []
            for t in edge:
                for n in Wd.neighbors(t):
                    if n in prev:
                        continue
                    if n != to and (self.place(n) or n == w["peak"] or self.terrain(n) == "town"):
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

    def do_mbuy(self, h, msg):
        if self.in_fight(h):
            raise Invalid("Not in the middle of a fight.")
        hero = self.hero(h)
        mer = self.merchant_at(hero["tile"])
        key = msg.get("item")
        if not mer or key not in mer["stock"]:
            raise Invalid("That's not for sale here.")
        cost = self.merchant_price(h, key)
        if hero["gold"] < cost:
            raise Invalid("You can't afford that.")
        hero["gold"] -= cost
        mer["stock"].remove(key)
        self.gain_item(h, key)
        self.fx("coins", h=h, n=-cost)
        self.say(f"{hero['name']} buys the {self.item(key)['name']} from {mer['name']} ({cost} gold).")

    def merchants_view(self):
        s = self.s
        return [{"id": mer["id"], "name": mer["name"], "tile": mer["tile"], "to": mer["to"], "wait": mer["wait"], "stock": mer["stock"],
                 "prices": {k: int(self.price(k) * A.MERCHANT_MARKUP) for k in mer["stock"]}}
                for mer in s.get("merchants", []) if s["seen"][mer["tile"]]]
