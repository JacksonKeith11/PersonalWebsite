"""A hero's build: their attributes and upgrades folded into the numbers the fight uses.

Attributes (one point a level): Vigor +12 health, Endurance dashes back 8% faster, Might
+7% heavy and special damage and +8% poise damage, Finesse +6% light damage, Arcane +12% status
buildup and +8% special damage. Upgrades: see content/upgrades.py.
"""

import copy
from collections import defaultdict

from . import content as C
from .content.upgrades import UPGRADES, scaled

ATTRS = ("vig", "end", "mig", "fin", "arc")
ATTR_NAMES = {"vig": "Vigor", "end": "Endurance", "mig": "Might", "fin": "Finesse", "arc": "Arcane"}
ATTR_TEXT = {"vig": "+12 health", "end": "Dashes come back 8% faster", "mig": "+7% heavy and special damage, +8% poise damage",
             "fin": "+6% light damage", "arc": "+12% status buildup, +8% special damage"}


class Build:
    def __init__(self, attrs, ups):
        H = C.HERO
        a = attrs
        self.stats = {"mhp": H["hp"] + 12 * a["vig"], "dash_regen": 1 + 0.08 * a["end"],
                      "speed": 1.0, "dash_time": 1.0, "focus_gain": 1.0, "special_cost": 1.0, "reach": 1.0, "flasks": H["flask"]["charges"],
                      "heal": H["flask"]["heal"], "block_cost": 1.0, "iframes": 0.0, "revive_time": 1.0, "guard_arc": 1.0, "dash_charges": 0, "skill_cd": 1.0, "skill_focus": 0,
                      "light_speed": 1.0, "roll_haste": 1.0, "light_pierce": 0, "light_shots": 0,
                      "patience": 0, "haste_light": 1.0, "drink_speed": 0, "dash_refund": 0, "overcharge": 0, "bloodspecial": 0, "echo": 0, "meditate": 0}
        self.mods = []                         # [(path, value)]: what blessings change in the weapon itself
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
                elif t == "mod": self.mods.extend(f["set"].items())
                elif t == "stat":
                    if "add" in f: self.stats[f["key"]] += f["add"]
                    else: self.stats[f["key"]] *= f["mult"]
                else:
                    f["uid"] = uid
                    self.fx[t].append(f)
        self.stats["flasks"] = int(round(self.stats["flasks"]))
        self._weapons = {}

    def weapon(self, wid):
        """This hero's own weapon table: the weapon with what their blessings change in it (`mod` effects)."""
        if not self.mods: return C.WEAPONS[wid]
        if wid not in self._weapons:
            w = copy.deepcopy(C.WEAPONS[wid])
            for path, value in self.mods:
                at, keys = w, path.split(".")
                for k in keys[:-1]:
                    k = int(k) if isinstance(at, list) else k
                    if isinstance(at, dict) and k not in at: at[k] = {}
                    at = at[k]
                k = int(keys[-1]) if isinstance(at, list) else keys[-1]
                at[k] = copy.deepcopy(value)
            self._weapons[wid] = w
        return self._weapons[wid]

    def dmg_mult(self, slot):
        return self.dmg[slot] * self.dmg["all"]

    def poise_mult(self, slot):
        return self.poise[slot] * self.poise["all"]

    def has(self, t):
        return bool(self.fx.get(t))

    def get(self, t):
        return self.fx.get(t, [])

    def client(self):
        """What the browser needs to move and fight: speed, how its dashes come back and so on."""
        s = self.stats
        perfect = self.get("perfect")
        return {"dash_regen": round(s["dash_regen"], 3), "speed": round(s["speed"], 3), "dash_time": round(s["dash_time"], 3),
                "focus_gain": round(s["focus_gain"], 3), "special_cost": round(s["special_cost"], 3), "reach": round(s["reach"], 3),
                "block_cost": round(s["block_cost"], 3), "iframes": round(s["iframes"], 3), "revive_time": round(s["revive_time"], 3),
                "guard_arc": round(s["guard_arc"], 3), "perfect_dash": round(sum(f["dash"] for f in perfect), 3),
                "focusback": round(sum(f["amt"] for f in self.get("focusback"))), "dodge": bool(self.get("dodge")),
                "dash_charges": round(s["dash_charges"]), "skill_cd": round(s["skill_cd"], 3), "skill_focus": round(s["skill_focus"]),
                "light_speed": round(s["light_speed"], 3), "roll_haste": round(s["roll_haste"], 3), "light_pierce": round(s["light_pierce"]),
                "light_shots": round(s["light_shots"]),
                "patience": round(s["patience"]), "haste_light": round(s["haste_light"], 3), "drink_speed": round(s["drink_speed"]),
                "dash_refund": round(s["dash_refund"]), "overcharge": round(s["overcharge"]), "bloodspecial": round(s["bloodspecial"]),
                "echo": round(s["echo"]), "meditate": round(s["meditate"]),
                "perfect_focus": round(sum(f["focus"] for f in self.get("perfectgain"))),
                # what blessings change in the weapon itself: [[path, value]] (hero.js, weaponOf)
                "mods": [[p, v] for p, v in self.mods],
                # the extra attacks upgrades add (content/upgrades.py, `proc`): the browser looses them, the server prices them
                "procs": [{"id": f["uid"], "when": f["when"], "cd": f.get("cd", 0), "proj": f.get("proj"), "aoe": f.get("aoe"), "pass": f.get("pass"), "col": f.get("col")} for f in self.get("proc")]}
