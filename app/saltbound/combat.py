"""Fights: dice, actions, enemy intents, statuses, summons and the end of a fight. Mixed into `Game`.

A round: every hero in the fight rolls their dice and every enemy shows its intent. The party
places dice on actions together, and each action happens the moment it's placed: its dice roll and
its effects land before anyone places another, so the party's actions go in the order they were
played (`f["done"]` lists them for the round). When everyone is ready, summons and pets act, then
enemies act in speed order, then end-of-round effects (Burn, Doom, Lifeline, statuses running out,
Armor clearing).

Heroes are "h0".."h2", enemies "f<id>" and summons "s<id>" wherever the browser names a target.
"""

from itertools import product

from . import classes as C
from .content import archipelago as A
from .foes import Foes, die_range
from .content import items as I

ROWS = ("front", "back")
SHIELD_BLOCK = 3
DEBUFFS = ("burn", "poison", "weak", "vuln", "mark", "root", "hex")
TICKING = ("weak", "vuln", "mark", "root")
ROUND_ONLY = ("riposte", "thorns")  # hero statuses that clear at the end of the round
ONE_SHOT = ("stun", "freeze", "shock", "hex", "lock", "steal", "static")
UNSTOPPABLE = ("cleave", "earthshaker")
ENRAGE_FROM = 10
# Enemies met on the map (roaming groups and lairs) last longer but hit softer, so those fights
# take a few rounds without being deadlier. Elites and big threats are meant to be dangerous: no change.
ROAM_HP = 2.2
ROAM_DMG = 0.65
# Event fights: whoever is on or next to the hex joins; a hero alone meets weaker enemies.
EVENT_DMG = 0.7
EVENT_HP = {1: 0.9, 2: 1.4, 3: 1.9}
# The Drowned Crown: warded while a Tide Guard stands (phase 1), drags one hero under each round
# (the Undertow, phases 2 and 3: Armor or a Guard stops it), and alone it's exposed and furious.
CROWN_WARD = 0.5
CROWN_EXPOSED = 1.5
UNDERTOW = 3    # times the fight's damage multiplier
BELL_CRACK = 6  # hitting the Bell-Warden with a die showing its bell number
LAMP_DOUSE = 3  # different heroes hitting the Lamp Keeper in one round put its lamp out
SWALLOW_GUT = 0.15  # the Reef Maw spits a hero out after taking this share of its health
CURSED_DIE = ["X", 1, 2, 3]

# Cross-hero combos: what two heroes do together (see COMBOS in classes.py for the words).
PINCER = 2      # the first hit on an enemy after an ally hit it this round...
PINCER_MATCH = 3  # ...and this much more if one of your dice shows a number one of theirs showed
COVERED = 3     # your first hit after an ally Guarded or Taunted for you this round
SHATTER = 4     # hitting an enemy an ally Froze breaks the ice
WILDFIRE = 1    # Burn meets an ally's Poison (or the reverse): it erupts for (Burn + Poison) x this


class Invalid(Exception):
    """An action that isn't allowed; the message is shown to the player."""


_CODE = {}
_GLOBALS = {"__builtins__": {}, "max": max, "min": min}


def _amt(expr, env):
    if isinstance(expr, (int, float)):
        return int(expr)
    code = _CODE.get(expr)
    if code is None:
        code = _CODE[expr] = compile(expr, "<amt>", "eval")
    return int(eval(code, _GLOBALS, env))  # expressions come only from our own data


TAGS = {"F": "burn", "I": "freeze", "P": "poison"}


def face(f):
    """(value, tag) for a die face: numbers, "S" shield, "X" skull, "W" wild, "F3"/"I3"/"P3"."""
    if isinstance(f, int):
        return f, None
    if f in ("S", "X"):
        return 0, f
    if f == "W":
        return None, "W"
    return int(f[1:]), TAGS[f[0]]


def top_face(faces):
    return max([face(f)[0] for f in faces if face(f)[0] is not None] or [0])


def mean_face(faces):
    vals = [face(f)[0] if face(f)[1] != "W" else top_face(faces) for f in faces]
    return sum(vals) / len(vals)


def _num(d):
    """A die's value: rolled or shown, else (while planning) what it rolls on average."""
    if isinstance(d.get("v"), int):
        return d["v"]
    if d.get("v") is None and "faces" in d:
        return round(mean_face(d["faces"]))
    return 0


def _p(combo):
    out = 1.0
    for o in combo:
        out *= o[2]
    return out


def check_hit(req, vals, tags):
    """Did these rolled values meet an action's conditions? Wild faces pass any condition."""
    for v, t in zip(vals, tags):
        if t == "W":
            continue
        ok = True
        if "min" in req and v < req["min"]:
            ok = False
        if "max" in req and v > req["max"]:
            ok = False
        if "exact" in req and v != req["exact"]:
            ok = False
        if req.get("odd") and v % 2 == 0:
            ok = False
        if req.get("even") and (v % 2 or v == 0):
            ok = False
        if not ok and not (req.get("or_face") and t == req["or_face"]):
            return False
    if req.get("pair") and not is_pair(vals, tags):
        return False
    if "sum_min" in req and sum(vals) < req["sum_min"]:
        return False
    return True


def is_pair(vals, tags):
    real = [v for v, t in zip(vals, tags) if t != "W"]
    return len(vals) >= 2 and len(set(real)) <= 1


def is_straight(vals, tags):
    real = sorted(v for v, t in zip(vals, tags) if t != "W")
    return len(vals) >= 3 and all(b - a == 1 for a, b in zip(real, real[1:])) and len(set(real)) == len(real)


class Combat(Foes):
    # ------------------------------------------------------------------ starting

    def in_fight(self, h):
        f = self.s["fight"]
        return bool(f) and self.s["phase"] == "fight" and h in f["heroes"]

    def start_fight(self, spec):
        s = self.s
        tier = self.tier()
        diff = self.diff()
        f = {
            "id": s["fid"], "kind": spec["kind"], "tile": spec["tile"], "heroes": spec["heroes"],
            "groups": spec.get("groups", []), "region": spec.get("region"), "step": spec.get("step", 0),
            "path": spec.get("path"),
            "by": spec.get("by"), "round": 0, "foes": [], "hs": {}, "done": [], "guard": {}, "taunt": None,
            "sanct": 0, "aegis": 0, "xp": 0, "gold": 0, "dmul": diff["foe_dmg"] * (1 + 0.1 * tier),
            "spirit": {}, "nextfoe": 1, "phase": 1, "allies": [], "nextsum": 1, "acts": {}, "pain": {},
        }
        s["fid"] += 1
        s["fight"] = f
        s["phase"] = "fight"
        grow = max(0, s["rises"] - 10) * 0.1 if spec["kind"] == "boss" else 0
        roam = spec["kind"] in ("roam", "lair")
        if roam:
            f["dmul"] *= ROAM_DMG
        if spec["kind"] == "event":
            f["dmul"] *= EVENT_DMG
            grow = EVENT_HP.get(len(spec["heroes"]), 1.0) - 1
        for k in spec["foes"]:
            key, hp, aff = (k["k"], k.get("hp"), k.get("aff")) if isinstance(k, dict) else (k, None, None)
            if roam and not aff and not A.FOES[key].get("big"):
                grow = ROAM_HP - 1
            elif roam:
                grow = 0
            self.add_foe(key, hp, grow, aff)
        for h in f["heroes"]:
            hero = self.hero(h)
            m = self.mods(h)
            x = {"st": {}, "down": False, "fled": False,
                 "dice": [], "rr": max(0, 1 + m.get("reroll", 0)), "once": [], "round_once": [], "cds": {}, "echo": False,
                 "unbreak": False, "ward": m.get("stun_ward", 0), "ready": False}
            f["hs"][str(h)] = x
            if m.get("start_armor"):
                x["st"]["armor"] = m["start_armor"]
            if m.get("evasive"):
                x["st"]["dodge"] = 1
            if m.get("bark"):
                self.summon(h, "sapling", 10)
        if any(self.mods(h).get("open_weak") for h in f["heroes"]):
            for fo in f["foes"]:
                fo["st"]["weak"] = max(fo["st"].get("weak", 0), 1)
        f["ambush"] = bool(spec.get("ambush_foes")) or (spec.get("by") in f["heroes"] and
                                                        C.CLASSES[self.hero(spec["by"])["cls"]]["map"]["key"] == "ambush")
        names = ", ".join(fo["name"] for fo in f["foes"])
        self.say(f"Fight! {names}.")
        self.fx("fight", fk=f["kind"], tile=f["tile"])
        self.new_round()

    def add_foe(self, key, hp=None, grow=0.0, aff=None):
        f = self.s["fight"]
        d = A.FOES[key]
        mult = self.diff()["foe_hp"] * (1 + 0.15 * self.tier()) * (1 + grow)
        mx = max(1, round(d["hp"] * mult))
        fo = {"id": f["nextfoe"], "k": key, "name": d["name"], "hp": mx, "max": mx, "row": d["row"],
              "st": {}, "intent": None, "seq": 0, "might": 0}
        self.foe_setup(fo, aff)
        if hp:
            fo["hp"] = min(hp, fo["max"])
        f["nextfoe"] += 1
        f["foes"].append(fo)
        return fo

    def new_die(self, h, faces, src, dk=None):
        """A die that joins a hero's hand mid-round (split, grafted, stolen tempo...)."""
        x = self.hs(h)
        x["nid"] = x.get("nid", 0) + 1
        return {"id": f"{h}.{self.s['fight']['round']}.n{x['nid']}", "faces": faces, "dk": list(dk or []), "src": src,
                "used": False, "v": None, "bonus": 0, "top": False}

    def summon(self, h, kind, hp=None):
        f = self.s["fight"]
        d = C.SUMMONS[kind]
        m = self.mods(h)
        cap = C.SUMMON_CAP + m.get("summon_cap", 0)
        mine = [a for a in self.allies() if a["owner"] == h]
        while len(mine) >= cap:
            old = mine.pop(0)
            old["hp"] = 0
            self.fx("die", to=f"s{old['id']}")
        mx = max(1, round((hp or d["hp"]) * (1 + m.get("summon_hp", 0))))
        a = {"id": f["nextsum"], "k": kind, "name": d["name"], "hp": mx, "max": mx, "row": d["row"], "atk": d["atk"],
             "all": d.get("all", False), "owner": h, "st": {}}
        f["nextsum"] += 1
        f["allies"].append(a)
        self.fx("summon", s=a["id"])
        return a

    # ------------------------------------------------------------------ lookups

    def passive_mod(self, h, key):
        return sum(C.PASSIVES[k.rstrip("+")]["mods"].get(key, 0) for k in self.hero(h)["skills"]
                   if k.rstrip("+") in C.PASSIVES)

    def hs(self, h):
        return self.s["fight"]["hs"][str(h)]

    def active(self, h):
        f = self.s["fight"]
        return h in f["heroes"] and not self.hs(h)["down"] and not self.hs(h)["fled"]

    def actives(self):
        return [h for h in self.s["fight"]["heroes"] if self.active(h)]

    def allies(self):
        return [a for a in self.s["fight"]["allies"] if a["hp"] > 0]

    def ally(self, sid):
        return next((a for a in self.s["fight"]["allies"] if a["id"] == sid), None)

    def foe(self, fid):
        return next((fo for fo in self.s["fight"]["foes"] if fo["id"] == fid), None)

    def foes(self):
        return [fo for fo in self.s["fight"]["foes"] if fo["hp"] > 0]

    def front_foes(self):
        fr = [fo for fo in self.foes() if fo["row"] == "front"]
        return fr or self.foes()

    def fight_waiting(self):
        f = self.s["fight"]
        return [h for h in f["heroes"] if self.active(h) and not self.hs(h)["ready"]]

    def unit_alive(self, uid):
        if not uid:
            return False
        if uid.startswith("h"):
            return self.active(int(uid[1:]))
        a = self.ally(int(uid[1:]))
        return bool(a) and a["hp"] > 0

    def party_units(self):
        """Everything enemies can hit: standing heroes and summons."""
        return [f"h{h}" for h in self.actives() if not self.hs(h).get("swallowed")] + [f"s{a['id']}" for a in self.allies()]

    def herald_aura(self):
        return sum(self.mods(h).get("hymn_aura", 0) for h in self.actives())

    # ------------------------------------------------------------------ rounds

    def new_round(self):
        f = self.s["fight"]
        f["round"] += 1
        f["done"] = []
        f["guard"] = {}
        f["lastdie"] = {}
        f["pincered"] = []
        f["covered"] = []
        f["taunt"] = None
        f["sanct"] = 0
        f["acts"] = {}
        pain, f["pain"] = f["pain"], {}
        # No endless stalemates: from round 11 the enemies grow stronger every round.
        if f["round"] > ENRAGE_FROM:
            for fo in self.foes():
                fo["might"] += 2
            if f["round"] == ENRAGE_FROM + 1:
                self.say("The enemies grow desperate: they hit harder every round now.")
        # Crown of Thorns, Poison, regeneration, Last Stand
        for fo in self.foes():
            if fo.get("aff") == "ironclad":
                fo["st"]["armor"] = fo["st"].get("armor", 0) + 4
                self.fx("armor", to=f"f{fo['id']}", n=4)
            if fo.get("aff") == "warlord" and f["round"] > 1:
                for o in self.foes():
                    if o is not fo:
                        o["might"] += 1
                self.fx("st", to=f"f{fo['id']}", s="rallies")
        thorns = sum(self.mods(h).get("crown_thorns", 0) for h in self.actives())
        for fo in self.foes():
            if thorns:
                self.hurt_foe(fo, thorns, None, pure=True)
            if fo["hp"] > 0 and fo["st"].get("poison"):
                self.hurt_foe(fo, fo["st"]["poison"], None, pure=True)
        # Aura: the most wounded hero (lowest HP, below full) heals
        aura = sum(self.mods(h).get("aura", 0) for h in self.actives())
        hurt = [h for h in self.actives() if self.hero(h)["hp"] < self.maxhp(h)]
        aura_to = min(hurt, key=lambda h: self.hero(h)["hp"]) if aura and hurt else None
        for h in self.actives():
            st = self.hs(h)["st"]
            if st.get("poison"):
                self.hurt_hero(h, st["poison"], None, pure=True)
            if not self.active(h):
                continue
            m = self.mods(h)
            got = (aura if h == aura_to else 0) + m.get("regen", 0)
            if got:
                self.fight_heal(h, got, None)
            if m.get("last_stand") and self.hero(h)["hp"] <= self.maxhp(h) // 2:
                st["armor"] = st.get("armor", 0) + m["last_stand"]
        sregen = sum(self.mods(h).get("summon_regen", 0) for h in self.actives())
        if sregen:
            for a in self.allies():
                got = min(sregen, a["max"] - a["hp"])
                a["hp"] += got
                if got:
                    self.fx("heal", to=f"s{a['id']}", n=got)
        if self.check_end():
            return
        # Dice: most stay hidden until their action resolves; Seer dice are rolled now and shown,
        # Augur dice are rolled now and show only high or low, Fate dice show two faces.
        f["hymn"] = 0
        anthem = [h for h in self.actives() if self.mods(h).get("anthem")]
        for h in f["heroes"]:
            x = self.hs(h)
            x["ready"] = False
            if self.mods(h).get("hoard") and x["dice"]:
                # Slack Water: the biggest die left unused carries over
                left = [d for d in x["dice"] if not d["used"] and d["src"] not in ("hoard", "gift", "hex")]
                if left:
                    big = max(left, key=lambda d: top_face(d["faces"]))
                    x["hoard"] = {"faces": big["faces"], "src": "hoard",
                                  "dk": [k for k in big["dk"] if k not in ("seer", "augur", "fate", "top") and not k.startswith("link:")]}
            x["dice"] = []
            x["round_once"] = []
            x["cds"] = {k: n - 1 for k, n in x.get("cds", {}).items() if n > 1}
            x["links"] = {}
            x["tempo"] = False
            x["inspire"] = 0
            x["pain_bonus"] = pain.get(str(h), 0)
            x["soaked"] = False
            if not self.active(h):
                continue
            if x.get("swallowed"):
                self.fx("st", to=f"h{h}", s="swallowed")
                self.hurt_hero(h, max(2, round(f["dmul"] * 1.5)), None, pure=True)
                continue
            if x["st"].pop("stun", 0):
                if x["ward"] > 0:
                    x["ward"] -= 1
                else:
                    self.fx("st", to=f"h{h}", s="stunned")
                    continue
            m = self.mods(h)
            dice = self.dice_of(h)
            if m.get("pet"):
                dice.append({"faces": list(range(1, (8 if m.get("pet_strike") else min(8, m["pet"])) + 1)), "dk": [], "src": "pet"})
            if any(y != h for y in anthem):
                dice.append({"faces": [1, 2, 3, 4], "dk": [], "src": "anthem"})
            if x.get("hoard"):
                dice.append(x.pop("hoard"))
            if m.get("all_explode"):
                dice = [dict(d, dk=list(d["dk"]) + (["exploding"] if "exploding" not in d["dk"] else [])) for d in dice]
            if m.get("deadeye") and dice:
                big = max(dice, key=lambda d: top_face(d["faces"]))
                big["dk"] = list(big["dk"]) + ["seer", "top"]
            for i, d in enumerate(dice):
                inst = {"id": f"{h}.{f['round']}.{i}", "faces": d["faces"], "dk": d["dk"], "src": d["src"], "used": False,
                        "v": None, "bonus": 0, "top": "top" in d["dk"]}
                for k in d["dk"]:
                    if k.startswith("link:"):
                        inst["link"] = k[5:]
                if "seer" in d["dk"]:
                    inst["v"], inst["tag"] = self.raw_roll(h, inst)
                elif "augur" in d["dk"]:
                    inst["sv"], inst["stag"] = self.raw_roll(h, inst)
                    lo, hi = min(face(f2)[0] or 0 for f2 in d["faces"]), top_face(d["faces"])
                    inst["hint"] = "high" if inst["sv"] > (lo + hi) / 2 else "low"
                elif "fate" in d["dk"]:
                    inst["fc"] = [self.raw_roll(h, inst)[0], self.raw_roll(h, inst)[0]]
                x["dice"].append(inst)
            if x["st"].pop("hex", 0) and x["dice"]:
                # hexed: the biggest die is swapped for a cursed one
                big = max(x["dice"], key=lambda d: top_face(d["faces"]))
                big.update(faces=list(CURSED_DIE), dk=[], src="hex", v=None, top=False)
                for k2 in ("link", "sv", "stag", "hint", "fc", "tag"):
                    big.pop(k2, None)
                self.fx("st", to=f"h{h}", s="hexed")
            if x["st"].pop("freeze", 0) and not m.get("freeze_immune") and x["dice"]:
                x["dice"].remove(min(x["dice"], key=_num))
            # enemies that attack your dice: Barnacles lock one, thieves steal one, static shocks low rolls
            if x["st"].pop("steal", 0) and x["dice"]:
                x["dice"].remove(max(x["dice"], key=lambda d: top_face(d["faces"])))
                self.fx("st", to=f"h{h}", s="robbed")
            if x["st"].pop("lock", 0) and x["dice"]:
                big = max(x["dice"], key=lambda d: top_face(d["faces"]))
                big["used"], big["locked"] = True, True
                self.fx("st", to=f"h{h}", s="locked")
            x["static"] = bool(x["st"].pop("static", 0))
            if m.get("seer_small"):
                hid = [d for d in x["dice"] if not d["used"] and d.get("v") is None and not d.get("fc")]
                if hid:
                    d = min(hid, key=lambda d: top_face(d["faces"]))
                    d["v"], d["tag"] = self.raw_roll(h, d)
                    for k2 in ("sv", "stag", "hint"):
                        d.pop(k2, None)
        # the swallow can knock the last hero down; and with nobody else left to fight, the Maw spits its prey out
        if self.check_end():
            return
        if all(self.hs(y).get("swallowed") for y in self.actives()):
            for fo in self.foes():
                if fo.get("gut") is not None:
                    self.release_swallowed(fo)
        # Spirit dice for heroes who are dead
        f["spirit"] = {str(h): {"v": self.rng.randint(1, 6), "used": False}
                       for h in range(3) if not self.hero(h)["alive"]}
        self.crown_round()
        self.foe_round()
        # Intents
        for fo in self.foes():
            self.choose_intent(fo)
        self.fx("round", n=f["round"])

    # ------------------------------------------------------------------ placing dice

    def cooling(self, h, key):
        """Rounds until an action can be used again (0: ready)."""
        return self.hs(h)["cds"].get(key, 0)

    def count_ok(self, req, dice):
        n = req.get("n", 1)
        return 1 <= len(dice) <= n if req.get("upto") else len(dice) == n

    # ------------------------------------------------------------------ rolling

    def raw_roll(self, h, d):
        """Roll a die's face (no bonuses): (value, tag). Explodes, and links to its group."""
        x = self.hs(h)
        g = d.get("link")
        if g and g in x["links"]:
            return tuple(x["links"][g])
        faces = d["faces"]
        if d.get("top"):
            v, t = top_face(faces), None
        else:
            v, t = face(self.roll_face(faces))
        top = top_face(faces)
        if t == "W":
            v = top
        if "exploding" in d["dk"] and v == top and t != "W":
            for _ in range(3):
                extra, et = face(self.roll_face(faces))
                v += (extra if et != "W" else top) + self.mods(h).get("overcharge", 0)
                if extra != top:
                    break
        if g:
            x["links"][g] = [v, t]
        return v, t

    def roll(self, h, d):
        """A die's final value when its action resolves (or when an instant uses it)."""
        x = self.hs(h)
        m = self.mods(h)
        if d.get("rolled"):
            return d["v"]
        if d.get("v") is not None:  # rolled and shown while planning (Seer)
            v, t = d["v"], d.get("tag")
        elif "sv" in d:
            v, t = d.pop("sv"), d.pop("stag", None)
        elif d.get("fc"):
            v, t = self.rng.choice(d["fc"]), None
        else:
            v, t = self.raw_roll(h, d)
        if t == "X":
            hero = self.hero(h)
            n = min(3, hero["hp"] - 1)
            if n > 0:
                hero["hp"] -= n
                self.fx("dmg", to=f"h{h}", n=n, block=0)
            if m.get("skull_boost"):
                x["inspire"] = x.get("inspire", 0) + m["skull_boost"]
                self.fx("st", to=f"h{h}", s="inspired")
        if t == "W" and m.get("wild_heal") and self.active(h):
            self.fight_heal(h, m["wild_heal"], h)
        if m.get("shield_top") and t == "S":
            v = top_face(d["faces"])  # Bulwark Faces: still a shield (it blocks), and worth the top face
        if m.get("one_is_top") and v == 1 and t is None:
            v = top_face(d["faces"])
        if m.get("keen_edge") and v == 6:
            v = 7
        if x.get("static") and t not in ("S", "X", "W") and v is not None and v <= 2 and self.active(h):
            self.fx("st", to=f"h{h}", s="static")
            self.hurt_hero(h, 3, None, pure=True)
        if t not in ("S", "X"):
            v += d.get("bonus", 0) + self.s["fight"].get("hymn", 0)
            if d.get("link") and m.get("sleight"):
                v += 1
            if x.get("inspire"):
                v += x["inspire"]
                x["inspire"] = 0
            if x.get("pain_bonus"):
                v += x["pain_bonus"]
                x["pain_bonus"] = 0
        d["v"], d["tag"], d["rolled"] = v, t, True
        d["shown"] = True
        return v

    def die_add(self, h, d):
        """What gets added to a die's face when it rolls (not to shield or skull faces)."""
        return d.get("bonus", 0) + self.s["fight"].get("hymn", 0) + (1 if d.get("link") and self.mods(h).get("sleight") else 0)

    def outcomes(self, h, d, raw=False):
        """What a die might come up as, for planning: [(value, tag, chance)]. No randomness used.
        `raw` leaves out the die's bonuses (for linked dice, which share one face)."""
        x = self.hs(h)
        if d.get("rolled"):
            return [(d["v"], d.get("tag"), 1.0)]
        g = d.get("link")
        if g and g in x.get("links", {}) and d.get("v") is None:
            base = [(x["links"][g][0], x["links"][g][1], 1.0)]  # its group already rolled (a linked Seer die)
        elif d.get("v") is not None:
            base = [(d["v"], d.get("tag"), 1.0)]
        elif d.get("fc"):
            base = [(d["fc"][0], None, 0.5), (d["fc"][1], None, 0.5)]
        elif d.get("top"):
            base = [(top_face(d["faces"]), None, 1.0)]
        else:
            faces = d["faces"]
            if d.get("hint"):
                lo, hi = min(face(f2)[0] or 0 for f2 in faces), top_face(faces)
                mid = (lo + hi) / 2
                faces = [f2 for f2 in faces if (face(f2)[0] if face(f2)[1] != "W" else hi) > mid] if d["hint"] == "high" else \
                    [f2 for f2 in faces if (face(f2)[0] if face(f2)[1] != "W" else hi) <= mid]
                faces = faces or d["faces"]
            top = top_face(d["faces"])
            base = []
            for f2 in faces:
                v, t = face(f2)
                if t == "W":
                    v = top
                if "exploding" in d["dk"] and v == top and t != "W":
                    v += round(mean_face(d["faces"]))
                base.append((v, t, 1 / len(faces)))
        if raw:
            return base
        add = self.die_add(h, d)
        return [(v + (add if t not in ("S", "X") else 0), t, p) for v, t, p in base]

    def joint_outcomes(self, h, dice, cap=4000):
        """Every way these dice could come up together: [(values, tags, chance)]. Linked dice that
        haven't rolled share one roll, so they always match. Big sets are thinned to about `cap`."""
        groups, where = [], {}
        for i, d in enumerate(dice):
            g = d.get("link") if d.get("v") is None and not d.get("rolled") else None
            if g and g in where:
                groups[where[g]].append(i)
                continue
            if g:
                where[g] = len(groups)
            groups.append([i])
        per = [self.outcomes(h, dice[grp[0]], raw=len(grp) > 1) for grp in groups]
        combos = list(product(*per)) if dice else [()]
        if cap and len(combos) > cap:
            combos = combos[:: len(combos) // cap + 1]
        out = []
        for c in combos:
            vals, tags, pr = [0] * len(dice), [None] * len(dice), 1.0
            for grp, (v, t, p) in zip(groups, c):
                pr *= p
                for i in grp:
                    vals[i] = v + (self.die_add(h, dice[i]) if len(grp) > 1 and t not in ("S", "X") else 0)
                    tags[i] = t
            out.append((vals, tags, pr))
        norm = sum(o[2] for o in out) or 1.0
        return [(v, t, p / norm) for v, t, p in out]

    def resolve_target(self, h, a, tgt):
        """Check a target for an action; returns the target id (or None for untargeted)."""
        kind = a["tgt"]
        x = self.hs(h)
        if kind == "foe":
            fo = self.foe(int(tgt[1:])) if isinstance(tgt, str) and tgt.startswith("f") and tgt[1:].isdigit() else None
            if not fo or fo["hp"] <= 0:
                raise Invalid("Pick an enemy.")
            if a.get("melee") and fo not in self.front_foes():
                raise Invalid("Melee can only reach the front row.")
            return tgt
        if kind in ("ally", "other", "downed"):
            hid = int(tgt[1:]) if isinstance(tgt, str) and tgt.startswith("h") and tgt[1:].isdigit() else None
            f = self.s["fight"]
            if hid is None or hid not in f["heroes"]:
                raise Invalid("Pick an ally.")
            if kind == "downed":
                if not self.hs(hid)["down"]:
                    raise Invalid("Pick a knocked-down ally.")
            elif not self.active(hid):
                raise Invalid("Pick an ally who's standing.")
            if kind == "other" and hid == h:
                raise Invalid("Pick someone else.")
            return tgt
        return None

    def do_place(self, h, msg):
        if not self.in_fight(h) or not self.active(h):
            raise Invalid("You're not fighting.")
        x = self.hs(h)
        if x["ready"]:
            raise Invalid("You've readied up; unready to act again.")
        key = msg.get("a")
        acts = self.actions_of(h)
        match = next((k for k in acts if k.rstrip("+") == key), None)
        if match is None:
            raise Invalid("You don't know that action.")
        a = self.action_def(h, match)
        f = self.s["fight"]
        if a.get("once") and a["key"] in x["once"]:
            raise Invalid("Once per fight.")
        if a.get("per_rest") and a["key"] in self.hero(h).get("spent", []):
            raise Invalid(f"{a['name']} is spent until you rest.")
        if a.get("cd") and x["cds"].get(a["key"]):
            left = x["cds"][a["key"]]
            raise Invalid(f"{a['name']} is cooling down: ready again {'in ' + str(left) + ' rounds' if left > 1 else 'next round'}.")
        if a.get("per_round") and a["key"] in x["round_once"]:
            raise Invalid("Once a round.")
        if a["key"] == "flee" and f["kind"] in ("dungeon", "boss"):
            raise Invalid("There's no running from this one.")
        if a["key"] == "flee" and x["st"].get("root"):
            raise Invalid("You're Rooted.")
        ids = msg.get("dice") or []
        if not isinstance(ids, list) or len(set(ids)) != len(ids):
            raise Invalid("Pick dice.")
        dice = [next((d for d in x["dice"] if d["id"] == i and not d["used"]), None) for i in ids]
        if None in dice:
            raise Invalid("Those dice are already used.")
        if not a["def"] and not self.mods(h).get("guard_free") and any("guard" in (d.get("dk") or []) for d in dice):
            raise Invalid("Guard dice only go on defensive actions: Block, Armor, healing and the like.")
        if not self.count_ok(a["req"], dice):
            n = a["req"].get("n", 1)
            raise Invalid(f"That takes {'up to ' if a['req'].get('upto') else ''}{n} {'die' if n == 1 else 'dice'}.")
        tgt = self.resolve_target(h, a, msg.get("tgt"))
        if a["req"].get("marked") and not self.foe(int(tgt[1:]))["st"].get("mark"):
            raise Invalid("That enemy needs to be Marked.")
        if a.get("once") and a.get("instant"):
            x["once"].append(a["key"])
        if a.get("cd") and a.get("instant"):
            x["cds"][a["key"]] = a["cd"]
        if a.get("per_round"):
            x["round_once"].append(a["key"])
        if a.get("instant"):
            self.instant(h, a, dice, tgt)
            return
        # Everything else happens now, in the order the party plays it: the dice roll and the action
        # lands before anyone places another.
        for d in dice:
            d["used"] = True
        self.resolve_action(h, a, dice, tgt)
        self.maybe_resolve()

    def maybe_resolve(self):
        """Thorns or a bursting enemy can knock down the last hero still acting: then the round
        goes on without them."""
        if self.s["phase"] == "fight" and self.s["fight"] and not self.check_end() and not self.fight_waiting():
            self.resolve_round()

    def instant(self, h, a, dice, tgt):
        """Actions that set up dice take effect the moment they're placed."""
        x = self.hs(h)
        m = self.mods(h)
        keep = set()
        extra = 1 if m.get("second_verse") else 0
        plus = 2 if a["plus"] else 0
        other = int(tgt[1:]) if isinstance(tgt, str) and tgt.startswith("h") else None
        for op in a["ops"]:
            k = op["op"]
            if k == "setdie":
                d = dice[0]
                d["top"] = True
                if d.get("v") is not None and not d.get("rolled"):
                    d["v"], d["tag"] = top_face(d["faces"]), None
                keep.add(d["id"])
            elif k == "bump":
                d = dice[0]
                d["bonus"] = d.get("bonus", 0) + _amt(op["amt"], {}) + plus
                keep.add(d["id"])
            elif k == "selfdmg":
                hero = self.hero(h)
                n = min(_amt(op["amt"], {}), hero["hp"] - 1)
                hero["hp"] -= n
                self.fx("dmg", to=f"h{h}", n=n, block=0)
            elif k == "loaded":
                g = "L" + dice[0]["id"]
                for d in dice:
                    d["link"] = g
                    keep.add(d["id"])
            elif k == "inspire":
                v = self.roll(h, dice[0])
                self.hs(other)["inspire"] = self.hs(other).get("inspire", 0) + max(2, v // 2) + extra + plus
                self.fx("st", to=f"h{other}", s="inspired")
            elif k == "hymn":
                vals = [self.roll(h, d) for d in dice]
                f = self.s["fight"]
                f["hymn"] = f.get("hymn", 0) + 1 + (1 if len(set(vals)) == 1 else 0) + extra
                self.fx("st", to="party", s="hymn")
            elif k == "give":
                d = dice[0]
                x["dice"].remove(d)
                self.hs(other)["dice"].append(dict(d, id=f"g{d['id']}", src="gift", used=False,
                                                    bonus=d.get("bonus", 0) + extra))
                keep.add(d["id"])
            elif k == "reroll_ally":
                self.hs(other)["rr"] += 2 + (1 if a["plus"] else 0)
                self.fx("st", to=f"h{other}", s="rerolls")
            elif k == "flip":
                # Counterpoint: roll it in the open; a low roll turns to its opposite face
                d = dice[0]
                v, t = (d["v"], d.get("tag")) if d.get("v") is not None else self.raw_roll(h, d)
                nums = [face(f2)[0] for f2 in d["faces"] if face(f2)[0] is not None]
                lo, hi = min(nums), max(nums)
                if t not in ("S", "X", "W") and v is not None and v <= (lo + hi) / 2:
                    v = lo + hi - v
                    self.fx("st", to=f"h{h}", s="flipped")
                d["v"], d["tag"] = v, (t if t in ("S", "X", "W") else None)
                for k2 in ("sv", "stag", "hint", "fc"):
                    d.pop(k2, None)
                keep.add(d["id"])
            elif k == "split":
                d = dice[0]
                x["dice"].remove(d)
                half = max(2, top_face(d["faces"]) // 2)
                for _ in range(2):
                    x["dice"].append(self.new_die(h, list(range(1, half + 1)), "split"))
                keep.add(d["id"])
                self.fx("st", to=f"h{h}", s="split")
            elif k == "merge":
                size = min(20, sum(top_face(d["faces"]) for d in dice))
                for d in dice:
                    x["dice"].remove(d)
                    keep.add(d["id"])
                x["dice"].append(self.new_die(h, list(range(1, size + 1)), "graft"))
                self.fx("st", to=f"h{h}", s="grafted")
            elif k == "second_opinion":
                hid = [d for d in self.hs(other)["dice"] if not d["used"] and d.get("v") is None and not d.get("fc")]
                if hid:
                    d = max(hid, key=lambda d: top_face(d["faces"]))
                    rolls = [self.raw_roll(other, d) for _ in range(2)]
                    v, t = max(rolls, key=lambda r: (r[1] not in ("X", "S"), r[0] or 0))
                    d["v"], d["tag"] = v, t
                    for k2 in ("sv", "stag", "hint"):
                        d.pop(k2, None)
                    self.fx("st", to=f"h{other}", s="second_opinion")
            elif k == "transfusion":
                v = self.roll(h, dice[0])
                self.fight_heal(other, v + m.get("heal_bonus", 0) + plus, h)
                self.hs(other)["inspire"] = self.hs(other).get("inspire", 0) + 1 + extra
                self.fx("st", to=f"h{other}", s="inspired")
            elif k == "bottle":
                v = self.roll(h, dice[0])
                key = "big_potion" if v >= 5 else "potion"
                for _ in range(2 if m.get("philosopher") else 1):
                    self.gain_item(h, key)
        for d in dice:
            if d["id"] not in keep and d in x["dice"]:
                d["used"] = True
        self.s["fight"]["done"].append({"h": h, "a": a["key"], "plus": a["plus"], "tgt": tgt, "hit": None})
        self.fx("act", h=h, a=a["key"], tgt=tgt, instant=True)
        self.spite(a)

    def do_reroll(self, h, msg):
        if not self.in_fight(h) or not self.active(h):
            raise Invalid("You're not fighting.")
        x = self.hs(h)
        if x["rr"] <= 0:
            raise Invalid("No rerolls left this fight.")
        d = next((d for d in x["dice"] if d["id"] == msg.get("die") and not d["used"]), None)
        if not d:
            raise Invalid("Pick an unused die.")
        x["rr"] -= 1
        d["v"] = self.roll_face(d["faces"])
        self.fx("reroll", h=h, die=d["id"], v=d["v"])

    def do_spirit(self, h, msg):
        f = self.s["fight"]
        if not f or self.s["phase"] != "fight":
            raise Invalid("No fight.")
        sp = f["spirit"].get(str(h))
        if not sp or sp["used"]:
            raise Invalid("You have no spirit die to give.")
        to = msg.get("to")
        if not isinstance(to, int) or not self.active(to):
            raise Invalid("Give it to whom?")
        sp["used"] = True
        x = self.hs(to)
        x["dice"].append({"id": f"s{h}.{f['round']}", "faces": [1, 2, 3, 4, 5, 6], "v": sp["v"], "src": "spirit", "used": False})
        self.fx("spirit", h=h, to=to, v=sp["v"])

    def do_fready(self, h, msg):
        if not self.in_fight(h) or not self.active(h):
            raise Invalid("You're not fighting.")
        self.hs(h)["ready"] = bool(msg.get("on", True))
        if not self.fight_waiting():
            self.resolve_round()

    def fight_use(self, h, i, tgt):
        """A consumable in a fight: takes effect at once, no die needed."""
        if not self.active(h):
            raise Invalid("You can't do that now.")
        hero = self.hero(h)
        key = hero["bag"][i]
        u = I.ITEMS[key]["use"]
        bonus = 1 + self.mods(h).get("potion_bonus", 0)
        if "heal" in u:
            hid = int(tgt[1:]) if isinstance(tgt, str) and tgt.startswith("h") and tgt[1:].isdigit() else h
            if not self.active(hid):
                raise Invalid("Use it on whom?")
            hero["bag"].pop(i)
            self.fight_heal(hid, int(u["heal"] * bonus), h)
        elif "bomb" in u:
            fo = self.foe(int(tgt[1:])) if isinstance(tgt, str) and tgt.startswith("f") and tgt[1:].isdigit() else None
            if not fo or fo["hp"] <= 0:
                raise Invalid("Throw it at whom?")
            hero["bag"].pop(i)
            self.hurt_foe(fo, u["bomb"] + self.mods(h).get("bomb_bonus", 0), h, bomb=True)
        elif "party_armor" in u:
            hero["bag"].pop(i)
            for x in self.actives():
                self.hs(x)["st"]["armor"] = self.hs(x)["st"].get("armor", 0) + u["party_armor"]
                self.fx("armor", to=f"h{x}", n=u["party_armor"])
        elif "lift" in u:
            hid = int(tgt[1:]) if isinstance(tgt, str) and tgt.startswith("h") and tgt[1:].isdigit() else None
            if hid is None or hid not in self.s["fight"]["heroes"] or not self.hs(hid)["down"]:
                raise Invalid("Use it on a knocked-down ally.")
            hero["bag"].pop(i)
            self.lift(hid, u["lift"])
        self.say(f"{hero['name']} uses {I.ITEMS[key]['name']}.")
        self.maybe_resolve()

    # ------------------------------------------------------------------ resolving

    def env(self, h, a, dice, target=None, vals=None, tags=None):
        """Variables for an action's amounts. `vals`/`tags` are the rolled values (or, while
        estimating, one possible outcome); without them, dice count at what they're showing or
        what they roll on average."""
        if vals is None:
            vals = [_num(d) for d in dice]
            tags = [d.get("tag") for d in dice]
        x = self.hs(h)
        hero = self.hero(h)
        e = {"v": vals[0] if vals else 0, "sum": sum(vals), "n": len(vals), "armor": x["st"].get("armor", 0),
             "missing": self.maxhp(h) - hero["hp"], "undead": 0, "rooted": 0, "stunned": 0, "poisoned": 0,
             "marked": 0, "aimed": 0, "d": vals[0] if vals else 0, "matched": 0,
             "pair": int(is_pair(vals, tags)), "straight": int(is_straight(vals, tags)), "outroll": 0}
        if isinstance(target, dict):
            st = target["st"]
            it = target.get("intent") or {}
            known = [d["v"] for d in it.get("dice") or [] if d.get("v") is not None]
            e["outroll"] = int(bool(vals) and bool(known) and len(known) == len(it.get("dice") or []) and vals[0] > max(known))
            e.update(undead=int(bool(A.FOES[target["k"]].get("undead"))), rooted=int(bool(st.get("root"))),
                     stunned=int(bool(st.get("stun"))), poisoned=int(bool(st.get("poison"))), marked=int(bool(st.get("mark"))),
                     aimed=int(f"h{h}" in self.intent_aims(it)), matched=0)
        return e

    def dmg_bonus(self, h, a, target):
        """Flat damage a hero adds to every hit of this action on this target."""
        m = self.mods(h)
        f = self.s["fight"]
        n = m.get("might", 0) + self.herald_aura()
        n += m.get("momentum", 0) * f["acts"].get(str(h), 0)
        n += m.get("rage", 0) * ((self.maxhp(h) - self.hero(h)["hp"]) // 5)
        if a.get("bomb"):
            n += m.get("bomb_bonus", 0)
        if m.get("first_strike") and not self.hs(h).get("struck"):
            n += m["first_strike"]
        if isinstance(target, dict):
            if target["st"].get("stun") or target["st"].get("root"):
                n += m.get("opportunist", 0)
            if target["st"].get("burn"):
                n += m.get("burn_bonus_hit", 0)
            if target["hp"] * 2 < target["max"]:
                n += m.get("execute_bonus", 0)
            aims = self.intent_aims(target.get("intent") or {})
            if aims and f"h{h}" not in aims:
                n += m.get("backstab", 0)
        return n

    def estimate(self, h, a, dice, tgt):
        """What a planned action will probably do: its chance to hit, and the expected number
        (with the lowest and highest it could be) for its first damage, heal or Armor effect."""
        target = self.foe(int(tgt[1:])) if isinstance(tgt, str) and tgt.startswith("f") else None
        p_hit, ev, lo, hi, kind = 0.0, 0.0, None, None, None
        for vals, tags, pr in self.joint_outcomes(h, dice):
            hit = check_hit(a["req"], vals, tags)
            p_hit += pr if hit else 0
            ops = a["ops"] if hit else a.get("miss", [])
            n = 0
            for op in ops:
                if op["op"] in ("dmg", "heal", "armor", "lift"):
                    kind = kind or op["op"]
                    if op["op"] != kind:
                        continue
                    env = self.env(h, a, dice, target, vals, tags)
                    if op.get("each"):
                        n = sum(_amt(op["amt"], {**env, "d": v}) for v in vals)
                    else:
                        n = _amt(op["amt"], env)
                    n += 2 if a["plus"] else 0
                    if kind == "dmg":
                        n += self.dmg_bonus(h, a, target)
                        if target:
                            n += sum(b for _, b in self.combo_peek(h, target, vals))
                            n = self.foe_damage_after(target, n, h)
                    elif kind == "heal":
                        n += self.mods(h).get("heal_bonus", 0)
                    n = max(0, n)
                    break
            ev += pr * n
            lo = n if lo is None else min(lo, n)
            hi = n if hi is None else max(hi, n)
        risky = any(k in a["req"] for k in ("min", "max", "exact", "odd", "even", "sum_min", "pair", "or_face"))
        return {"k": kind, "n": round(ev), "lo": lo or 0, "hi": hi or 0, "p": round(p_hit, 3) if risky else None}

    def foe_damage_after(self, fo, n, h):
        st = fo["st"]
        if h is not None and self.hs(h)["st"].get("weak"):
            n = int(n * 0.75)
        if st.get("freeze") and h is not None:
            n += self.mods(h).get("frozen_bonus", 0)
        if st.get("vuln"):
            n = int(n * 1.25 + 0.5)
        if st.get("mark"):
            n += 3
        if fo["k"] == "lamp_keeper" and fo.get("lit", True):
            n = int(n * 0.5)
        if A.FOES[fo["k"]].get("final"):
            if self.crown_warded(fo):
                n = int(n * CROWN_WARD)
            elif self.s["fight"].get("phase", 1) >= 3:
                n = int(n * CROWN_EXPOSED + 0.5)
        return max(0, n)

    def crown_warded(self, fo):
        return any(o is not fo and o["k"] == "tide_guard" for o in self.foes())

    def spite(self, a):
        """Spiteful elites gain might when a hero buffs, heals or shields."""
        if a.get("def") or a.get("instant") or a["tgt"] in ("ally", "other", "party"):
            for fo in self.foes():
                if fo.get("aff") == "spiteful":
                    fo["might"] += 1
                    self.fx("st", to=f"f{fo['id']}", s="spite")

    def resolve_action(self, h, a, dice, tgt):
        """A placed action happens: its dice roll, it hits or misses, its effects land."""
        f = self.s["fight"]
        x = self.hs(h)
        self.spite(a)
        if a.get("once"):
            x["once"].append(a["key"])
        if a.get("cd"):
            x["cds"][a["key"]] = a["cd"]
        if a.get("per_rest"):
            self.hero(h).setdefault("spent", []).append(a["key"])
        hit = self.roll_for(h, a, dice)
        f["done"].append({"h": h, "a": a["key"], "plus": a["plus"], "tgt": tgt, "hit": hit})
        self.fx("act", h=h, a=a["key"], tgt=tgt, hit=hit)
        ops = a["ops"] if hit else a.get("miss", [])
        self.run_ops(h, a, dice, tgt, ops=ops, hit=hit)
        self.elements(h, a, dice, tgt)
        if self.s["fight"] is f and a["tgt"] == "foe" and dice and isinstance(tgt, str) and tgt.startswith("f"):
            f.setdefault("lastdie", {})[tgt[1:]] = [h, [_num(d) for d in dice]]
            fo = self.foe(int(tgt[1:]))
            known = [d["v"] for d in ((fo or {}).get("intent") or {}).get("dice") or [] if d.get("v") is not None]
            if self.mods(h).get("tempo") and known and not x.get("tempo") and max(_num(d) for d in dice) > max(known):
                x["tempo"] = True
                x["dice"].append(self.new_die(h, list(range(1, 7)), "tempo"))
                self.fx("st", to=f"h{h}", s="tempo")
        if a["key"] == "block" and self.mods(h).get("block_heal") and self.s["fight"] is f:
            self.fight_heal(h, self.mods(h)["block_heal"], h)
        echo = (a.get("spell") and self.mods(h).get("spell_echo")) or (self.mods(h).get("echo_any") and a["key"] not in C.GENERIC)
        if echo and not x["echo"] and self.s["fight"] is f:
            x["echo"] = True
            self.fx("act", h=h, a=a["key"], tgt=tgt, echo=True)
            self.run_ops(h, a, dice, tgt, half=True, ops=ops, hit=hit)
        f["acts"][str(h)] = f["acts"].get(str(h), 0) + 1
        if self.s["fight"] is f:
            self.check_end()

    def resolve_round(self):
        """Everyone is ready: summons and pets act, then the enemies, fastest first."""
        if self.check_end():
            return
        # Summons and pets
        for a in self.allies():
            if not a["atk"] or not self.foes():
                continue
            self.fx("sact", s=a["id"])
            if a["all"]:
                for fo in self.foes():
                    self.hurt_foe(fo, a["atk"], a["owner"], pure=True)
            else:
                fo = min(self.front_foes(), key=lambda o: o["hp"])
                self.hurt_foe(fo, a["atk"], a["owner"])
        for h in self.actives():
            if self.mods(h).get("pet_strike") and self.foes():
                fo = min(self.foes(), key=lambda o: o["hp"])
                self.fx("act", h=h, a="sic_em", tgt=f"f{fo['id']}")
                self.hurt_foe(fo, 3, h)
        if self.check_end():
            return
        # Enemies act, fastest first.
        for fo in sorted(self.foes(), key=lambda fo: -A.FOES[fo["k"]]["speed"]):
            if fo["hp"] <= 0:
                continue
            self.foe_act(fo)
            if self.check_end():
                return
        self.end_round()

    def roll_for(self, h, a, dice):
        """Roll an action's dice; a miss gets Steady dice and then an automatic reroll (if the hero
        has one left) to try again. Shield faces block as they land. Returns whether it hit."""
        x = self.hs(h)
        for d in dice:
            self.roll(h, d)

        def hit():
            return check_hit(a["req"], [d["v"] for d in dice], [d.get("tag") for d in dice])
        self.fx("roll", h=h, dice=[{"id": d["id"], "v": d["v"], "tag": d.get("tag")} for d in dice])
        ok = hit()
        if not ok:
            for d in dice:
                if "steady" in d["dk"] and not ok:
                    d["rolled"] = False
                    d.pop("v", None)
                    d["v"] = None
                    self.roll(h, d)
                    self.fx("reroll", h=h, die=d["id"], v=d["v"], why="steady")
                    ok = hit()
        if not ok and x["rr"] > 0 and dice:
            d = min((d for d in dice if d.get("tag") != "W"), key=lambda d: d["v"], default=None)
            if d is not None:
                x["rr"] -= 1
                d["rolled"] = False
                d["v"] = None
                self.roll(h, d)
                self.fx("reroll", h=h, die=d["id"], v=d["v"], why="reroll")
                ok = hit()
        cost = self.mods(h).get("blood_reroll", 0)
        if not ok and cost and x["rr"] <= 0 and dice and self.hero(h)["hp"] > cost + 1:
            d = min((d for d in dice if d.get("tag") != "W"), key=lambda d: d["v"], default=None)
            if d is not None:
                self.hero(h)["hp"] -= cost
                self.fx("dmg", to=f"h{h}", n=cost, block=0)
                d["rolled"] = False
                d["v"] = None
                self.roll(h, d)
                self.fx("reroll", h=h, die=d["id"], v=d["v"], why="blood")
                ok = hit()
        shields = sum(1 for d in dice if d.get("tag") == "S")
        if shields:
            n = shields * (SHIELD_BLOCK + self.mods(h).get("shield_block", 0))
            x["st"]["armor"] = x["st"].get("armor", 0) + n
            self.fx("armor", to=f"h{h}", n=n)
        return ok

    def elements(self, h, a, dice, tgt):
        """Elemental faces add their status to the action's enemy target."""
        fo = self.foe(int(tgt[1:])) if isinstance(tgt, str) and tgt.startswith("f") else None
        if not fo or fo["hp"] <= 0:
            return
        for d in dice:
            t = d.get("tag")
            if t in ("burn", "freeze", "poison"):
                if t == "freeze":
                    fo["st"]["freeze"] = 1
                else:
                    fo["st"][t] = fo["st"].get(t, 0) + 1
                self.fx("st", to=f"f{fo['id']}", s=t)
                self.foe_status_by(fo, t, h)
                if fo["hp"] <= 0:
                    return

    # ------------------------------------------------------------------ cross-hero combos

    def cover(self, y):
        f = self.s["fight"]
        if y not in f.setdefault("covered", []):
            f["covered"].append(y)

    def combo_peek(self, h, t, vals, used=()):
        """The combos a hit by hero h on enemy t would score with these die values, without
        scoring them: [(name, bonus)]."""
        f = self.s["fight"]
        up = self.mods(h).get("combo_up", 0)
        out = []
        if "covered" not in used and h in f.get("covered", []):
            out.append(("covered", COVERED + up))
        last = f.get("lastdie", {}).get(str(t["id"]))
        if "pincer" not in used and last and last[0] != h and t["id"] not in f.get("pincered", []):
            match = any(v and v in last[1] for v in vals)
            out.append(("pincer", PINCER + (PINCER_MATCH if match else 0) + up))
        if "shatter" not in used and t["st"].get("freeze") and t.get("st_by", {}).get("freeze") not in (None, h):
            out.append(("shatter", SHATTER + up))
        if "bell" not in used and t.get("bell") and not t.get("cracked") and t["bell"] in vals:
            out.append(("bell", BELL_CRACK))
        return out

    def combo_bonus(self, h, a, dice, t, used):
        """Extra damage a hit gets from what an ally did first (Covered, Pincer, Shatter), scored."""
        f = self.s["fight"]
        n = 0
        for name, bonus in self.combo_peek(h, t, [_num(d) for d in dice], used):
            used.add(name)
            n += bonus
            if name == "covered":
                f["covered"].remove(h)
            elif name == "pincer":
                f.setdefault("pincered", []).append(t["id"])
            elif name == "shatter":
                t["st"].pop("freeze", None)
            elif name == "bell":
                t["cracked"] = True
                t["st"]["stun"] = 1
                self.say("The bell cracks! The Bell-Warden loses its next action.")
            self.fx("combo", to=f"f{t['id']}", c=name, n=bonus)
        return n

    def foe_status_by(self, fo, s, h):
        """Who put a status on an enemy, and Wildfire when Burn meets an ally's Poison."""
        if fo["hp"] <= 0 or h is None:
            return
        by = fo.setdefault("st_by", {})
        other = {"burn": "poison", "poison": "burn"}.get(s)
        if other and fo["st"].get(other) and by.get(other) not in (None, h) and not fo.get("wildfire"):
            fo["wildfire"] = True
            n = (fo["st"].get("burn", 0) + fo["st"].get("poison", 0)) * WILDFIRE + self.mods(h).get("combo_up", 0)
            self.fx("combo", to=f"f{fo['id']}", c="wildfire", n=n)
            self.hurt_foe(fo, n, h, pure=True)
            for o in self.foes():
                if o is not fo:
                    self.hurt_foe(o, n // 2, h, pure=True)
        by[s] = h

    def targets_for(self, h, a, tgt):
        kind = a["tgt"]
        if kind == "foe":
            fo = self.foe(int(tgt[1:]))
            if not fo or fo["hp"] <= 0:
                # it died before this resolved: the weakest enemy in reach takes it instead
                pool = self.front_foes() if a.get("melee") else self.foes()
                fo = min(pool, key=lambda o: o["hp"]) if pool else None
            return [fo] if fo else []
        if kind == "foes":
            return self.foes()
        if kind == "front":
            if a["key"] == "cleave" and self.mods(h).get("unstoppable"):
                return self.foes()
            return list(self.front_foes())
        if kind in ("ally", "other", "downed"):
            hid = int(tgt[1:])
            if kind != "downed" and not self.active(hid):
                return []
            return [("h", hid)]
        if kind == "party":
            return [("h", x) for x in self.actives()]
        return [("h", h)]

    def op_targets(self, h, op, base):
        """Who an op hits: the action's targets, unless the op says otherwise."""
        to = op.get("to")
        x = self.hs(h)
        if to == "self":
            return [("h", h)]
        if to == "one":
            return base[:1]
        if to == "random":
            foes = self.foes()
            return [self.rng.choice(foes)] if foes else []
        if to == "row":
            first = next((t for t in base if isinstance(t, dict)), None)
            return [fo for fo in self.foes() if first and fo["row"] == first["row"]]
        if to == "party":
            return [("h", y) for y in self.actives()]
        if to == "lowest":
            others = [y for y in self.actives() if y != h]
            return [("h", min(others, key=lambda y: self.hero(y)["hp"]))] if others else []
        return base

    def run_ops(self, h, a, dice, tgt, half=False, ops=None, hit=True):
        m = self.mods(h)
        plus = 2 if a["plus"] else 0
        base = self.targets_for(h, a, tgt)
        x = self.hs(h)
        pierce_all = bool(m.get("unstoppable")) and a["key"] in UNSTOPPABLE
        crescendo = x["st"].get("crescendo")
        dealt_any = False
        combo_used = set()

        def scale(n):
            return n // 2 if half else n

        def gate(op, target=None):
            return "if" not in op or bool(_amt(op["if"], self.env(h, a, dice, target)))

        for op in (a["ops"] if ops is None else ops):
            k = op["op"]
            targets = self.op_targets(h, op, base)
            if k == "dmg":
                each = dice if op.get("each") else [None]
                for d in each:
                    for t in (targets if not op.get("random") else [None]):
                        if op.get("random"):
                            foes = self.foes()
                            if not foes:
                                break
                            t = self.rng.choice(foes)
                        if isinstance(t, tuple) or t["hp"] <= 0 or not gate(op, t):
                            continue
                        if t.get("air") and a.get("melee"):
                            self.fx("st", to=f"f{t['id']}", s="out of reach")
                            continue
                        env = self.env(h, a, dice, t)
                        if d is not None:
                            env["d"] = _num(d)
                        n = scale(_amt(op["amt"], env) + plus) + self.dmg_bonus(h, a, t)
                        n += self.combo_bonus(h, a, dice, t, combo_used)
                        if crescendo:
                            n = n * 3 // 2
                        if m.get("eagle_eye"):
                            src = [d] if d is not None else dice
                            if any(_num(dd) and _num(dd) >= top_face(dd["faces"]) for dd in src):
                                n *= 2
                        done = self.hurt_foe(t, n, h, pierce=pierce_all or op.get("pierce") or m.get("pierce_all"), bomb=a.get("bomb"))
                        dealt_any = True
                        if a.get("spell") and m.get("spell_burn") and done and t["hp"] > 0:
                            t["st"]["burn"] = t["st"].get("burn", 0) + 1
                            self.fx("st", to=f"f{t['id']}", s="burn")
                            self.foe_status_by(t, "burn", h)
                        if a.get("spell") and m.get("spell_chain") and a["tgt"] == "foe" and "chain" not in combo_used:
                            combo_used.add("chain")
                            others = [o for o in self.foes() if o is not t]
                            if others:
                                o = self.rng.choice(others)
                                self.fx("st", to=f"f{o['id']}", s="arced")
                                self.hurt_foe(o, n // 2, h)
                        if op.get("splash"):
                            for o in self.foes():
                                if o is not t and o["row"] == t["row"]:
                                    self.hurt_foe(o, op["splash"] + m.get("splash_bonus", 0), h, pure=True, bomb=a.get("bomb"))
                        if a["key"] == "cleave" and m.get("wide_arcs") and not pierce_all:
                            for o in self.foes():
                                if o["row"] == "back":
                                    self.hurt_foe(o, n // 2, h)
                        if op.get("leech") and done:
                            self.fight_heal(h, int(done * op["leech"]), h)
                        if m.get("red_mist") and done and self.hero(h)["hp"] < self.maxhp(h) / 2:
                            self.fight_heal(h, done // 3, h)
                        if op.get("onkill") and t["hp"] <= 0:
                            self.fight_heal(h, _amt(op["onkill"], env), h)
            elif k == "selfdmg":
                hero = self.hero(h)
                n = min(_amt(op["amt"], {}), hero["hp"] - 1)
                if n > 0:
                    hero["hp"] -= n
                    self.fx("dmg", to=f"h{h}", n=n, block=0)
            elif k == "armor":
                n = scale(_amt(op["amt"], self.env(h, a, dice)) + plus)
                for t in targets:
                    if isinstance(t, tuple):
                        st = self.hs(t[1])["st"]
                        st["armor"] = st.get("armor", 0) + n
                        self.fx("armor", to=f"h{t[1]}", n=n)
            elif k == "heal":
                amount = scale(_amt(op["amt"], self.env(h, a, dice)) + plus) + m.get("heal_bonus", 0)
                for t in targets:
                    if isinstance(t, tuple):
                        self.fight_heal(t[1], amount, h)
            elif k == "heal_summons":
                amount = scale(_amt(op["amt"], self.env(h, a, dice)) + plus)
                for al in self.allies():
                    got = min(amount, al["max"] - al["hp"])
                    al["hp"] += got
                    if got:
                        self.fx("heal", to=f"s{al['id']}", n=got)
            elif k == "status":
                s = op["s"]
                for t in targets:
                    if not gate(op, t if isinstance(t, dict) else None):
                        continue
                    n = _amt(op["n"], self.env(h, a, dice, t if isinstance(t, dict) else None))
                    if s in ("burn", "poison"):
                        n += 1 if a["plus"] else 0
                    if s == "burn":
                        n += m.get("burn_bonus", 0)
                    if s == "poison":
                        n += m.get("poison_bonus", 0)
                    if s in ("weak", "vuln", "mark"):
                        n += m.get("debuff_ext", 0)
                    if s == "mark":
                        n += m.get("mark_ext", 0)
                    if s == "root":
                        n += m.get("root_ext", 0)
                    if s in ("riposte",):
                        n += m.get("riposte_up", 0)
                    if isinstance(t, tuple):
                        st = self.hs(t[1])["st"]
                        st[s] = max(st.get(s, 0), n) if s in ("riposte", "thorns", "dodge", "crescendo") else st.get(s, 0) + n
                        self.fx("st", to=f"h{t[1]}", s=s)
                    elif t["hp"] > 0:
                        if s == "doom":
                            t["st"]["doom"] = max(t["st"].get("doom", 0), n + plus)
                            t["st"]["doomt"] = 2
                        elif s in ONE_SHOT:
                            t["st"][s] = 1
                        else:
                            t["st"][s] = t["st"].get(s, 0) + n
                        self.fx("st", to=f"f{t['id']}", s=s)
                        self.foe_status_by(t, s, h)
            elif k == "flee":
                x["fled"] = True
                hero = self.hero(h)
                hero["tile"], hero["afloat"] = hero["prev"], False
                self.fx("flee", h=h)
                self.say(f"{hero['name']} flees.")
            elif k == "guard":
                for t in targets:
                    if isinstance(t, tuple):
                        # the first attack aimed at them swings to you, in plain sight; with none,
                        # you take the next hit that lands on them
                        if not self.retarget_intents(f"h{h}", frm=f"h{t[1]}", first_only=True):
                            self.s["fight"]["guard"][str(t[1])] = h
                        self.fx("st", to=f"h{t[1]}", s="guarded")
                        if t[1] != h:
                            self.cover(t[1])
                            if m.get("guard_share"):
                                st = self.hs(t[1])["st"]
                                st["armor"] = st.get("armor", 0) + m["guard_share"]
                                self.fx("armor", to=f"h{t[1]}", n=m["guard_share"])
            elif k == "taunt":
                f = self.s["fight"]
                f["taunt"] = h
                self.retarget_intents(f"h{h}")
                self.fx("st", to=f"h{h}", s="taunt")
                for y in self.actives():
                    if y != h:
                        self.cover(y)
                        if m.get("guard_share"):
                            st = self.hs(y)["st"]
                            st["armor"] = st.get("armor", 0) + 2
                            self.fx("armor", to=f"h{y}", n=2)
            elif k == "drag":
                for t in targets:
                    if not isinstance(t, tuple) and t["hp"] > 0 and not t["st"].get("root"):
                        t["row"] = "front"
                        self.fx("drag", to=f"f{t['id']}")
            elif k == "lift":
                n = scale(_amt(op["amt"], self.env(h, a, dice)) + plus)
                for t in targets:
                    if isinstance(t, tuple):
                        self.lift(t[1], n)
            elif k == "cleanse":
                for t in targets:
                    if isinstance(t, tuple):
                        st = self.hs(t[1])["st"]
                        for d in DEBUFFS:
                            st.pop(d, None)
                        self.fx("st", to=f"h{t[1]}", s="cleansed")
            elif k == "sanct":
                f = self.s["fight"]
                f["sanct"] += op["n"] + (1 if a["plus"] else 0)
                if m.get("aegis") and hit:
                    f["aegis"] = max(f["aegis"], m["aegis"])
                self.fx("st", to="party", s="sanct")
            elif k == "weaken":
                n = scale(_amt(op["amt"], self.env(h, a, dice)) + plus)
                for t in targets:
                    it = t.get("intent") if isinstance(t, dict) else None
                    if it and it.get("dice") and it["k"] in ("attack", "all", "block", "guard", "heal"):
                        it["bonus"] = it.get("bonus", 0) - n
                        self.intent_numbers(it)
                        self.fx("st", to=f"f{t['id']}", s="weakened")
            elif k == "retarget":
                for t in targets:
                    it = t.get("intent") if isinstance(t, dict) else None
                    if it and (it.get("tgt") or it.get("tgts")):
                        old = it.get("tgt") or it["tgts"][0]
                        new = self.foe_target(dict(it, tgt_kind="random"), exclude=old)
                        if new is None:
                            t["intent"] = {"k": "dazed", "name": "Distracted"}
                        elif it.get("tgt"):
                            it["tgt"] = new
                        else:
                            it["tgts"] = [new if u == old else u for u in it["tgts"]]
                        self.fx("retarget", f=t["id"], to=new)
                        self.fx("st", to=f"f{t['id']}", s="distracted")
            elif k == "cancel":
                for t in targets:
                    if isinstance(t, dict) and t["hp"] > 0:
                        t["intent"] = {"k": "dazed", "name": "Lost its turn"}
                        self.fx("st", to=f"f{t['id']}", s="dazed")
            elif k == "foresee":
                # the enemy's dice roll now, in the open: its intent shows exactly what it will do
                for t in targets:
                    it = t.get("intent") if isinstance(t, dict) else None
                    if not it or not it.get("dice"):
                        continue
                    for d in it["dice"]:
                        if d.get("v") is None:
                            d.pop("fc", None)
                            d["v"], d["tag"] = self.foe_roll_face(d["faces"])
                    self.intent_numbers(it)
                    self.fx("st", to=f"f{t['id']}", s="foreseen")
            elif k == "steal":
                for t in targets:
                    it = t.get("intent") if isinstance(t, dict) else None
                    if not it or not it.get("dice"):
                        continue
                    i = max(range(len(it["dice"])), key=lambda j: die_range(it["dice"][j]["faces"])[1])
                    it["dice"].pop(i)
                    if it.get("tgts") and it.get("each") and i < len(it["tgts"]):
                        it["tgts"].pop(i)
                    if not it["dice"]:
                        t["intent"] = {"k": "dazed", "name": "Robbed blind"}
                    else:
                        self.intent_numbers(it)
                    self.fx("st", to=f"f{t['id']}", s="robbed")
            elif k == "gold":
                n = _amt(op["amt"], {})
                self.hero(h)["gold"] += n
                self.fx("coins", h=h, n=n)
            elif k == "strip":
                n = scale(_amt(op["amt"], self.env(h, a, dice)) + plus)
                for t in targets:
                    if isinstance(t, dict):
                        t["st"]["armor"] = max(0, t["st"].get("armor", 0) - n)
            elif k == "summon":
                hp = _amt(op["hp"], self.env(h, a, dice)) + plus if op.get("hp") else None
                self.summon(h, op["k"], hp)
        if crescendo and dealt_any:
            x["st"].pop("crescendo", None)

    def lift(self, h, n):
        x = self.hs(h)
        if not x["down"]:
            return
        x["down"] = False
        self.hero(h)["hp"] = max(1, min(self.maxhp(h), n))
        self.fx("lift", to=f"h{h}", n=self.hero(h)["hp"])
        self.say(f"{self.hero(h)['name']} is back up.")

    def hurt_foe(self, fo, n, h, pure=False, pierce=False, bomb=False):
        """Damage an enemy; returns the damage that got past Armor."""
        if fo["hp"] <= 0:
            return 0
        if not pure:
            n = self.foe_damage_after(fo, n, h)
        if not pure and h is not None and A.FOES[fo["k"]].get("shell_min") and 0 < n < A.FOES[fo["k"]]["shell_min"]:
            self.fx("st", to=f"f{fo['id']}", s="shrugs")  # the Brine Golem's crust: small hits don't get through
            n = 0
        arm = 0 if pierce else fo["st"].get("armor", 0)
        blocked = min(arm, n)
        if blocked:
            fo["st"]["armor"] = arm - blocked
        n -= blocked
        fo["hp"] -= n
        if h is not None:
            self.s["stats"][h]["dmg"] += n
            fo.setdefault("hurt_by", {})[str(h)] = fo.get("hurt_by", {}).get(str(h), 0) + n
            if n > 0 and str(h) in self.s["fight"]["hs"]:
                self.hs(h)["struck"] = True
        self.fx("dmg", to=f"f{fo['id']}", n=n, block=blocked)
        if not pure and fo["st"].pop("shock", 0) and n > 0:
            others = [o for o in self.foes() if o is not fo]
            if others:
                near = [o for o in others if o["row"] == fo["row"]] or others
                self.hurt_foe(near[0], n // 2, h, pure=True)
        thorns = A.FOES[fo["k"]].get("thorns")
        if thorns and h is not None and not pure and not bomb and n > 0 and self.active(h):
            self.fx("st", to=f"f{fo['id']}", s="thorns")
            self.hurt_hero(h, thorns, None, pure=True)
        if fo["hp"] <= 0:
            self.foe_dies(fo, h, bomb)
        else:
            self.foe_hit_hooks(fo, n, h, pure)
            self.foe_bloodied(fo)
        return n

    def foe_dies(self, fo, h, bomb=False):
        f = self.s["fight"]
        fo["hp"] = 0
        d = A.FOES[fo["k"]]
        if fo.get("loot") and h is not None and self.hero(h)["alive"]:
            self.gain_item(h, fo.pop("loot"))
            self.fx("st", to=f"h{h}", s="recovered")
        if fo.get("gut") is not None or any(x.get("swallowed") == fo["id"] for x in f["hs"].values()):
            self.release_swallowed(fo)
        f["xp"] += d["xp"] * (2 if fo.get("aff") else 1)
        f["gold"] += d["gold"] * (2 if fo.get("aff") else 1)
        self.fx("die", to=f"f{fo['id']}")
        if h is not None and self.hero(h)["alive"]:
            self.s["stats"][h]["kills"] += 1
            m = self.mods(h)
            if m.get("kill_heal") and self.active(h):
                self.fight_heal(h, m["kill_heal"], h)
            if m.get("kill_armor") and self.active(h):
                st = self.hs(h)["st"]
                st["armor"] = st.get("armor", 0) + m["kill_armor"]
                self.fx("armor", to=f"h{h}", n=m["kill_armor"])
            if m.get("kill_gold"):
                self.hero(h)["gold"] += m["kill_gold"]
                self.fx("coins", h=h, n=m["kill_gold"])
        poisoned = fo["st"].get("poison")
        if poisoned and any(self.mods(y).get("plague") for y in self.actives()):
            others = self.foes()
            if others:
                o = self.rng.choice(others)
                o["st"]["poison"] = o["st"].get("poison", 0) + poisoned
                self.fx("st", to=f"f{o['id']}", s="poison")
        if bomb and h is not None and self.mods(h).get("chain_reaction"):
            for o in self.foes():
                self.hurt_foe(o, fo["max"] // 2, h, pure=True)
        for o in self.foes():
            if A.FOES[o["k"]].get("pack"):
                o["might"] += A.FOES[o["k"]]["pack"]
                self.fx("st", to=f"f{o['id']}", s="enraged")
        if d.get("volatile"):
            self.fx("st", to=f"f{fo['id']}", s="explodes")
            for y in self.actives():
                self.hurt_hero(y, d["volatile"], None, pure=True)
        if d.get("boss") and not d.get("final"):
            self.say(f"{d['name']} falls!")
        if fo["k"] == "tide_guard":
            crown = next((o for o in self.foes() if A.FOES[o["k"]].get("final")), None)
            if crown and not self.crown_warded(crown) and crown["st"].pop("warded", None):
                self.fx("st", to=f"f{crown['id']}", s="unwarded")

    def fight_heal(self, h, n, by):
        hero = self.hero(h)
        mx = self.maxhp(h)
        got = min(max(0, n), mx - hero["hp"])
        hero["hp"] += got
        if by is not None:
            self.s["stats"][by]["heal"] += got
            ha = self.mods(by).get("heal_armor", 0)
            if ha and got > 0 and self.active(h):
                self.hs(h)["st"]["armor"] = self.hs(h)["st"].get("armor", 0) + ha
            over = n - got
            if over > 0 and self.mods(by).get("overflow"):
                self.hs(h)["st"]["armor"] = self.hs(h)["st"].get("armor", 0) + over
        self.fx("heal", to=f"h{h}", n=got)
        return got

    def hurt_unit(self, uid, n, fo, melee=False):
        if uid.startswith("h"):
            return self.hurt_hero(int(uid[1:]), n, fo, melee=melee)
        a = self.ally(int(uid[1:]))
        if not a or a["hp"] <= 0:
            return 0
        n = max(0, n - self.s["fight"]["sanct"] - self.s["fight"]["aegis"])
        a["hp"] -= n
        self.fx("dmg", to=f"s{a['id']}", n=n, block=0)
        if a["hp"] <= 0:
            a["hp"] = 0
            self.fx("die", to=f"s{a['id']}")
        return n

    def hurt_hero(self, h, n, fo, melee=False, pure=False):
        f = self.s["fight"]
        if not self.active(h):
            return 0
        if not pure:
            g = f["guard"].pop(str(h), None)
            if g is not None and g != h and self.active(g):
                h = g
            x = self.hs(h)
            if x["st"].pop("dodge", 0):
                self.fx("st", to=f"h{h}", s="dodged")
                return 0
            soak = self.mods(h).get("first_hit_soak", 0)
            if soak and not x.get("soaked"):
                x["soaked"] = True
                n -= soak
            n -= f["sanct"] + f["aegis"]
            if fo is not None and fo["row"] == "back":
                n -= self.mods(h).get("footwork", 0)
            if x["st"].get("vuln"):
                n = int(n * 1.25 + 0.5)
            if x["st"].get("mark"):
                n += 3
        x = self.hs(h)
        n = max(0, n)
        arm = x["st"].get("armor", 0)
        blocked = min(arm, n)
        if blocked:
            x["st"]["armor"] = arm - blocked
        n -= blocked
        hero = self.hero(h)
        hero["hp"] -= n
        self.s["stats"][h]["taken"] += n
        self.fx("dmg", to=f"h{h}", n=n, block=blocked)
        if n > 0 and not pure and self.mods(h).get("pain_engine"):
            f["pain"][str(h)] = f["pain"].get(str(h), 0) + 1
        if fo is not None and not pure and fo["hp"] > 0:
            if blocked and not n and x["st"].get("riposte"):
                self.hurt_foe(fo, x["st"]["riposte"], h, pure=True)
            th = self.mods(h).get("thorns", 0) + x["st"].get("thorns", 0)
            if th and fo["hp"] > 0:
                self.hurt_foe(fo, th, h, pure=True)
            if self.mods(h).get("mark_attacker") and fo["hp"] > 0 and not fo["st"].get("mark"):
                fo["st"]["mark"] = 1
                self.fx("st", to=f"f{fo['id']}", s="mark")
            if x["st"].pop("shock", 0) and n > 0:
                others = [y for y in self.actives() if y != h]
                if others:
                    self.hurt_hero(others[0], n // 2, None, pure=True)
        if hero["hp"] <= 0:
            if self.mods(h).get("unbreakable") and not x["unbreak"]:
                x["unbreak"] = True
                hero["hp"] = 1
                self.fx("st", to=f"h{h}", s="unbreakable")
            else:
                hero["hp"] = 0
                x["down"] = True
                x["st"] = {}
                self.fx("down", to=f"h{h}")
                self.say(f"{hero['name']} is knocked down!")
                fury = self.mods(h).get("undying", 0)
                if fury and fo is not None and fo["hp"] > 0:
                    self.hurt_foe(fo, fury, h, pure=True)
        return n

    def hero_status(self, h, s, n):
        x = self.hs(h)
        m = self.mods(h)
        if s == "stun" and x["ward"] > 0:
            x["ward"] -= 1
            return
        if (s == "weak" and m.get("weak_immune")) or (s == "burn" and m.get("burn_immune")):
            return
        if s in TICKING:
            n += 1  # applied during the enemies' turn: it has to last through the heroes' next one
        x["st"][s] = x["st"].get(s, 0) + n if s not in ONE_SHOT else 1
        self.fx("st", to=f"h{h}", s=s)

    def end_round(self):
        self.undertow()
        for h in self.actives():
            if not self.mods(h).get("triage"):
                continue
            left = [d for d in self.hs(h)["dice"] if not d["used"]]
            hurt = [y for y in self.actives() if self.hero(y)["hp"] < self.maxhp(y)]
            if left and hurt:
                d = max(left, key=lambda d: top_face(d["faces"]))
                v = self.roll(h, d)
                d["used"] = True
                y = min(hurt, key=lambda y: self.hero(y)["hp"] / self.maxhp(y))
                self.fx("st", to=f"h{h}", s="triage")
                self.fight_heal(y, (v + 1) // 2, h)
        for fo in self.foes():
            st = fo["st"]
            if st.get("burn"):
                self.hurt_foe(fo, st["burn"], None, pure=True)
                st["burn"] -= 1
            if st.get("doomt"):
                st["doomt"] -= 1
                if st["doomt"] <= 0:
                    self.hurt_foe(fo, st.pop("doom", 0), None, pure=True)
                    st.pop("doomt", None)
            for s in TICKING:
                if st.get(s):
                    st[s] -= 1
            st["armor"] = 0
            for s in [s for s, v in st.items() if not v]:
                del st[s]
        for h in self.actives():
            x = self.hs(h)
            st = x["st"]
            if st.get("burn"):
                self.hurt_hero(h, st["burn"], None, pure=True)
                st["burn"] -= 1
            if st.pop("lifeline", 0) and self.active(h):
                self.fight_heal(h, self.maxhp(h), None)
            for s in TICKING:
                if st.get(s):
                    st[s] -= 1
            for s in ROUND_ONLY:
                st.pop(s, None)
            st["armor"] = st.get("armor", 0) // 2 if self.mods(h).get("overguard") else 0
            for s in [s for s, v in st.items() if not v]:
                del st[s]
        self.boss_phase()
        if not self.check_end():
            self.new_round()

    def boss_phase(self):
        """The Drowned Crown's phases. 1: warded while a Tide Guard stands. 2 (two thirds health):
        the Undertow drags one hero under each round. 3 (a third): its guards drown, and it fights
        alone, exposed (takes 50% more) and furious (every attack rolls an extra die)."""
        f = self.s["fight"]
        crown = next((fo for fo in self.foes() if A.FOES[fo["k"]].get("final")), None)
        if not crown:
            return
        frac = crown["hp"] / crown["max"]
        if f["phase"] == 1 and frac <= 0.66:
            f["phase"] = 2
            self.say("The sea pours over the peak: each round the Undertow drags someone under. Armor or a Guard stops it.")
            self.fx("phase", n=2)
        elif f["phase"] == 2 and frac <= 0.33:
            f["phase"] = 3
            for fo in self.foes():
                if fo is not crown:
                    fo["hp"] = 0
                    self.fx("die", to=f"f{fo['id']}")
            crown["fury"] = True
            self.say("The Drowned Crown stands alone: exposed, and furious.")
            self.fx("phase", n=3)

    def foe_round(self):
        """Start-of-round enemy upkeep: the Bell-Warden's bell number, the Lamp Keeper's lamp, the Iron
        Bosun's crew, Harpies running off with loot, Splitting elites."""
        f = self.s["fight"]
        for fo in list(self.foes()):
            fo["hitr"] = []
            if fo["k"] == "bell_warden":
                fo["bell"] = self.rng.randint(1, 6)
                fo["cracked"] = False
            if fo["k"] == "lamp_keeper":
                fo["lit"] = f["round"] > fo.get("dark_until", 0)
            if fo.get("bl") and A.FOES[fo["k"]].get("bloodied", {}).get("rule") == "allhands" and len(self.foes()) < 5:
                new = self.add_foe("deckhound")
                new["intent"] = {"k": "dazed", "name": "Just arrived"}
                self.fx("summon", f=new["id"])
            if fo.get("loot"):
                fo["flee_in"] = fo.get("flee_in", 2) - 1
                if fo["flee_in"] <= 0:
                    fo["hp"] = 0
                    self.fx("st", to=f"f{fo['id']}", s="flees")
                    self.fx("die", to=f"f{fo['id']}")
                    self.say(f"{fo['name']} flies off with the loot.")

    def foe_hit_hooks(self, fo, n, h, pure):
        """After a hero's hit lands on an enemy (and it lived): Splitting elites, Jellyfloats, the Lamp
        Keeper's lamp, the Reef Maw's gut."""
        f = self.s["fight"]
        d = A.FOES[fo["k"]]
        if h is not None and n > 0:
            fo.setdefault("hitr", [])
            if h not in fo["hitr"]:
                fo["hitr"].append(h)
        if fo["k"] == "lamp_keeper" and fo.get("lit", True) and len(fo.get("hitr", [])) >= min(LAMP_DOUSE, len(self.actives())):
            fo["lit"] = False
            fo["dark_until"] = f["round"] + 1
            fo["st"]["stun"] = 1
            self.fx("st", to=f"f{fo['id']}", s="doused")
            self.say("The lamp goes out! The Lamp Keeper reels in the dark.")
        splits = (d.get("splits") and n > 0) or (fo.get("aff") == "splitting" and len(fo.get("hitr", [])) >= 2)
        if splits and not fo.get("split") and fo["hp"] >= 4 and len(self.foes()) < 5:
            fo["split"] = True
            half = fo["hp"] // 2
            fo["hp"] -= half
            new = self.add_foe(fo["k"], half)
            new["split"] = True
            new["intent"] = {"k": "dazed", "name": "Just split off"}
            self.fx("summon", f=new["id"])
            self.fx("st", to=f"f{fo['id']}", s="splits")
        if fo.get("gut") and n > 0:
            fo["gut"] -= n
            if fo["gut"] <= 0:
                self.release_swallowed(fo)

    def release_swallowed(self, fo):
        fo.pop("gut", None)
        for k, x in self.s["fight"]["hs"].items():
            if x.get("swallowed") == fo["id"]:
                x.pop("swallowed")
                self.fx("st", to=f"h{k}", s="spat out")
                self.say(f"{self.hero(int(k))['name']} is spat out!")

    def crown_round(self):
        """At the start of a round: show the Crown's ward, and pick who the Undertow drags."""
        f = self.s["fight"]
        crown = next((fo for fo in self.foes() if A.FOES[fo["k"]].get("final")), None)
        if not crown:
            return
        crown["st"].pop("warded", None)
        crown["st"].pop("exposed", None)
        if self.crown_warded(crown):
            crown["st"]["warded"] = 1
        elif f["phase"] >= 3:
            crown["st"]["exposed"] = 1
        if f["phase"] >= 2 and self.actives():
            y = self.rng.choice(self.actives())
            n = max(1, round(UNDERTOW * f["dmul"]))
            self.hs(y)["st"]["undertow"] = n
            self.fx("st", to=f"h{y}", s="undertow")

    def undertow(self):
        """At the end of a round: the Undertow lands (Armor blocks it; a Guard takes it)."""
        for h in self.actives():
            n = self.hs(h)["st"].pop("undertow", 0)
            if n:
                self.fx("st", to=f"h{h}", s="dragged")
                self.hurt_hero(h, n, None)

    # ------------------------------------------------------------------ the end of a fight

    def check_end(self):
        f = self.s["fight"]
        if not f or self.s["phase"] != "fight":
            return True
        if not self.foes():
            self.finish_fight("won")
            return True
        if not self.actives():
            self.finish_fight("lost")
            return True
        return False

    def finish_fight(self, result):
        s = self.s
        f = s["fight"]
        party = f["heroes"]
        # Knocked-down heroes: a revive, or they're gone.
        for h in party:
            if self.hs(h)["down"]:
                hero = self.hero(h)
                free = not s["miracle"] and any(self.mods(x).get("miracle") for x in self.living())
                if free:
                    s["miracle"] = True
                    hero["hp"] = max(1, self.maxhp(h) // 4)
                    self.say(f"A miracle: {hero['name']} gets up without costing a revive.")
                elif s["revives"] > 0:
                    s["revives"] -= 1
                    hero["hp"] = max(1, self.maxhp(h) // 4)
                    self.say(f"{hero['name']} is revived ({s['revives']} revive{'s' if s['revives'] != 1 else ''} left).")
                    self.fx("revive", h=h)
                else:
                    hero["alive"] = False
                    hero["hp"] = 0
                    self.say(f"{hero['name']} has fallen, with no revives left.")
                    self.fx("dead", h=h)
        s["fight"] = None
        self.fx("fightend", result=result)
        if not self.living():
            self.say("The whole party has fallen.")
            self.end("lost")
            return
        for g in s["groups"]:
            g.pop("busy", None)
        if result == "won":
            if f["kind"] == "boss":
                self.say("The Drowned Crown sinks into the sea it raised. The isles are saved!")
                self.end("won")
                return
            winners = [h for h in party if not self.hs_from(f, h)["fled"] and self.hero(h)["alive"]]
            gold = f["gold"]
            for h in winners:
                self.hero(h)["gold"] += gold + self.mods(h).get("sticky", 0)
            self.say(f"Victory! +{f['xp']} XP" + (f", +{gold} gold each." if gold else "."))
            s["groups"] = [g for g in s["groups"] if g["id"] not in f["groups"]]
            p = self.place(f["tile"])
            if f["kind"] == "lair" and p and p["kind"] == "lair":
                p["done"] = True
                for q in s["quests"]:
                    if q["kind"] == "lair" and q["group"] in f["groups"] and not q["done"]:
                        self.complete_quest(q, winners[0] if winners else party[0])
            final = f["kind"] == "dungeon" and f["step"] >= A.DUNGEON_STEPS - 1
            path = f.get("path")
            for h in winners:
                if f["kind"] == "dungeon":
                    if final:
                        self.offer_loot(h, 2 if path == "sneak" else 3, tier_bonus=2)
                    elif path == "champion":
                        self.offer_loot(h, 3, tier_bonus=2)
                    else:
                        self.offer_loot(h, 2, tier_bonus=1)
                    if path == "vault":
                        self.hero(h)["gold"] += 12
                elif f["kind"] == "lair" or any(fo.get("aff") or A.FOES[fo["k"]].get("big") for fo in f["foes"]):
                    self.offer_loot(h, 2, tier_bonus=1)
                elif self.rng.chance(0.35):
                    self.offer_loot(h, 2)
            if path == "vault" and winners:
                self.say("The vault gives up its gold: +12 each.")
            if f["kind"] == "dungeon":
                reg = f["region"]
                step = f["step"] + 1
                s["dungeon"][reg] = step
                if step >= A.DUNGEON_STEPS:
                    s["cleared"].append(reg)
                    self.say(f"{A.DUNGEONS[reg]['name']} is cleared! ({len(s['cleared'])} of 3)")
                    self.fx("cleared", region=reg)
                    if len(s["cleared"]) == 3:
                        self.say("All three are cleared. The way to the peak is open.")
                else:
                    still = [h for h in party if self.hero(h)["alive"] and not self.hs_from(f, h)["fled"]]
                    if still:
                        self.make_fork(reg, step, f["tile"], still)
                    else:
                        s["dnext"][reg] = {"path": "passage" if step == 1 else "gate",
                                           "foes": self.dungeon_lineup(reg, "passage" if step == 1 else "gate")}
            self.gain_xp(f["xp"])
        else:
            # Lost: anyone still standing (or revived) falls back; the enemies keep their wounds.
            for h in party:
                hero = self.hero(h)
                if hero["alive"] and not self.hs_from(f, h)["fled"]:
                    hero["tile"], hero["afloat"] = hero["prev"], False
            alive = {fo["id"]: fo for fo in f["foes"] if fo["hp"] > 0}
            for g in s["groups"]:
                if g["id"] in f["groups"]:
                    g["foes"] = [dict({"k": fo["k"], "hp": fo["hp"]}, **({"aff": fo["aff"]} if fo.get("aff") else {}))
                                  for fo in alive.values()][:5]
                    alive = {}
            s["groups"] = [g for g in s["groups"] if g["foes"]]
            self.say("The party falls back." if f["kind"] != "event" else "You get away, battered.")
        self.next_step()

    def hs_from(self, f, h):
        return f["hs"][str(h)]

    # ------------------------------------------------------------------ the view

    def fight_view(self):
        f = self.s["fight"]
        if not f:
            return None
        out = {k: f[k] for k in ("id", "kind", "tile", "heroes", "round", "foes", "done", "guard", "taunt",
                                 "sanct", "aegis", "spirit", "region", "step", "phase", "ambush", "allies")}
        out["covered"] = f.get("covered", [])
        out["lastdie"] = f.get("lastdie", {})
        out["pincered"] = f.get("pincered", [])
        out["path"] = f.get("path")
        out["hymn"] = f.get("hymn", 0)
        out["hs"] = {k: dict(x, dice=[{kk: vv for kk, vv in d.items() if kk not in ("sv", "stag")} for d in x["dice"]])
                     for k, x in f["hs"].items()}
        return out
