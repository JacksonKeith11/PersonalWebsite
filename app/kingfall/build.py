"""A hero's build: their attributes and upgrades folded into the numbers the fight uses.

Attributes (one point a level): Vigor +12 health, Endurance +10 stamina and 6% quicker stamina, Might
+7% heavy and special damage and +8% poise damage, Finesse +6% light damage, Arcane +12% status
buildup and +8% special damage. Upgrades: see content/upgrades.py.
"""

from collections import defaultdict

from . import content as C
from .content.upgrades import UPGRADES, scaled

ATTRS = ("vig", "end", "mig", "fin", "arc")
ATTR_NAMES = {"vig": "Vigor", "end": "Endurance", "mig": "Might", "fin": "Finesse", "arc": "Arcane"}
ATTR_TEXT = {"vig": "+12 health", "end": "+10 stamina, quicker recovery", "mig": "+7% heavy and special damage, +8% poise damage",
             "fin": "+6% light damage", "arc": "+12% status buildup, +8% special damage"}


class Build:
    def __init__(self, attrs, ups):
        H = C.HERO
        a = attrs
        self.stats = {"mhp": H["hp"] + 12 * a["vig"], "stamina": H["stamina"] + 10 * a["end"], "st_regen": 1 + 0.06 * a["end"],
                      "speed": 1.0, "roll_st": 1.0, "focus_gain": 1.0, "special_cost": 1.0, "reach": 1.0, "flasks": H["flask"]["charges"],
                      "heal": H["flask"]["heal"], "block_st": 1.0, "iframes": 0.0, "revive_time": 1.0, "guard_arc": 1.0}
        self.dmg = defaultdict(lambda: 1.0)
        self.dmg["light"] *= 1 + 0.06 * a["fin"]
        self.dmg["heavy"] *= 1 + 0.07 * a["mig"]
        self.dmg["special"] *= (1 + 0.07 * a["mig"]) * (1 + 0.08 * a["arc"])
        self.poise = defaultdict(lambda: 1.0)
        for s in ("light", "heavy", "special"): self.poise[s] *= 1 + 0.08 * a["mig"]
        self.status = defaultdict(list)        # slot -> [(kind, amt)]
        self.buildup = 1 + 0.12 * a["arc"]
        self.fx = defaultdict(list)            # effect type -> [effect]
        self.slots = {}
        for uid, rarity in ups:
            u = UPGRADES.get(uid)
            if not u: continue
            if u["slot"]: self.slots[u["slot"]] = uid
            for f in scaled(uid, rarity):
                t = f["t"]
                if t == "dmg": self.dmg[f["slot"]] *= f["mult"]
                elif t == "poise": self.poise[f["slot"]] *= f["mult"]
                elif t == "status": self.status[f["slot"]].append((f["kind"], f["amt"]))
                elif t == "stat":
                    if "add" in f: self.stats[f["key"]] += f["add"]
                    else: self.stats[f["key"]] *= f["mult"]
                else: self.fx[t].append(f)
        self.stats["flasks"] = int(round(self.stats["flasks"]))

    def dmg_mult(self, slot):
        return self.dmg[slot] * self.dmg["all"]

    def poise_mult(self, slot):
        return self.poise[slot] * self.poise["all"]

    def has(self, t):
        return bool(self.fx.get(t))

    def get(self, t):
        return self.fx.get(t, [])

    def client(self):
        """What the browser needs to move and fight: stamina, speed and so on."""
        s = self.stats
        perfect = self.get("perfect")
        return {"stamina": round(s["stamina"]), "st_regen": round(s["st_regen"], 3), "speed": round(s["speed"], 3), "roll_st": round(s["roll_st"], 3),
                "focus_gain": round(s["focus_gain"], 3), "special_cost": round(s["special_cost"], 3), "reach": round(s["reach"], 3),
                "block_st": round(s["block_st"], 3), "iframes": round(s["iframes"], 3), "revive_time": round(s["revive_time"], 3),
                "guard_arc": round(s["guard_arc"], 3), "perfect_st": round(sum(f["st"] for f in perfect)),
                "focusback": round(sum(f["amt"] for f in self.get("focusback"))), "dodge": bool(self.get("dodge"))}
