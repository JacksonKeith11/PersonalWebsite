"""Fights: dice, actions, enemy intents, statuses, summons and the end of a fight. Mixed into `Game`.

A round: every hero in the fight rolls their dice and every enemy shows its intent. The party
places dice on actions together (each placement is a plan entry, resolved in the order placed;
"instant" actions such as Inspire or Loaded Dice take effect as soon as they're placed) and readies
up. Then the heroes' actions resolve, then summons and pets act, then enemies act in speed order,
then end-of-round effects (Burn, Doom, Lifeline, statuses running out, Armor clearing).

Heroes are "h0".."h2", enemies "f<id>" and summons "s<id>" wherever the browser names a target.
"""

from . import classes as C
from .content import archipelago as A
from .content import items as I

ROWS = ("front", "back")
SHIELD_BLOCK = 3
DEBUFFS = ("burn", "poison", "weak", "vuln", "mark", "root")
TICKING = ("weak", "vuln", "mark", "root")
ROUND_ONLY = ("riposte", "thorns")  # hero statuses that clear at the end of the round
ONE_SHOT = ("stun", "freeze", "shock")
UNSTOPPABLE = ("cleave", "earthshaker")
ENRAGE_FROM = 10


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


class Combat:
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
            "by": spec.get("by"), "round": 0, "foes": [], "hs": {}, "plan": [], "guard": {}, "taunt": None,
            "sanct": 0, "aegis": 0, "xp": 0, "gold": 0, "dmul": diff["foe_dmg"] * (1 + 0.1 * tier),
            "spirit": {}, "nextfoe": 1, "phase": 1, "allies": [], "nextsum": 1, "acts": {}, "pain": {},
        }
        s["fid"] += 1
        s["fight"] = f
        s["phase"] = "fight"
        grow = max(0, s["rises"] - 10) * 0.1 if spec["kind"] == "boss" else 0
        for k in spec["foes"]:
            key, hp = (k["k"], k.get("hp")) if isinstance(k, dict) else (k, None)
            self.add_foe(key, hp, grow)
        for h in f["heroes"]:
            hero = self.hero(h)
            m = self.mods(h)
            row = C.CLASSES[hero["cls"]]["row"]
            x = {"row": "front" if row == "either" else row, "st": {}, "down": False, "fled": False,
                 "dice": [], "rr": max(0, 1 + m.get("reroll", 0)), "once": [], "round_once": [], "cds": {}, "echo": False,
                 "unbreak": False, "ward": m.get("stun_ward", 0), "ready": False}
            f["hs"][str(h)] = x
            if m.get("start_armor"):
                x["st"]["armor"] = m["start_armor"]
            if m.get("evasive"):
                x["st"]["dodge"] = 1
            if m.get("bark"):
                self.summon(h, "sapling", 6)
        f["ambush"] = spec.get("by") in f["heroes"] and \
            C.CLASSES[self.hero(spec["by"])["cls"]]["map"]["key"] == "ambush"
        names = ", ".join(fo["name"] for fo in f["foes"])
        self.say(f"Fight! {names}.")
        self.fx("fight", fk=f["kind"], tile=f["tile"])
        self.new_round()

    def add_foe(self, key, hp=None, grow=0.0):
        f = self.s["fight"]
        d = A.FOES[key]
        mult = self.diff()["foe_hp"] * (1 + 0.15 * self.tier()) * (1 + grow)
        mx = max(1, round(d["hp"] * mult))
        fo = {"id": f["nextfoe"], "k": key, "name": d["name"], "hp": min(hp or mx, mx), "max": mx, "row": d["row"],
              "st": {}, "intent": None, "seq": 0, "might": 0}
        f["nextfoe"] += 1
        f["foes"].append(fo)
        return fo

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

    def unit_row(self, uid):
        if uid.startswith("h"):
            return self.hs(int(uid[1:]))["row"]
        a = self.ally(int(uid[1:]))
        return a["row"] if a else "front"

    def unit_alive(self, uid):
        if not uid:
            return False
        if uid.startswith("h"):
            return self.active(int(uid[1:]))
        a = self.ally(int(uid[1:]))
        return bool(a) and a["hp"] > 0

    def party_units(self):
        """Everything enemies can hit: standing heroes and summons."""
        return [f"h{h}" for h in self.actives()] + [f"s{a['id']}" for a in self.allies()]

    def herald_aura(self):
        return sum(self.mods(h).get("hymn_aura", 0) for h in self.actives())

    # ------------------------------------------------------------------ rounds

    def new_round(self):
        f = self.s["fight"]
        f["round"] += 1
        f["plan"] = []
        f["guard"] = {}
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
        thorns = sum(self.mods(h).get("crown_thorns", 0) for h in self.actives())
        for fo in self.foes():
            if thorns:
                self.hurt_foe(fo, thorns, None, pure=True)
            if fo["hp"] > 0 and fo["st"].get("poison"):
                self.hurt_foe(fo, fo["st"]["poison"], None, pure=True)
        aura = sum(self.mods(h).get("aura", 0) for h in self.actives())
        for h in self.actives():
            st = self.hs(h)["st"]
            if st.get("poison"):
                self.hurt_hero(h, st["poison"], None, pure=True)
            if not self.active(h):
                continue
            m = self.mods(h)
            if aura + m.get("regen", 0):
                self.fight_heal(h, aura + m.get("regen", 0), None)
            if m.get("last_stand") and self.hero(h)["hp"] <= self.maxhp(h) // 4:
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
            x["dice"] = []
            x["round_once"] = []
            x["cds"] = {k: n - 1 for k, n in x.get("cds", {}).items() if n > 1}
            x["links"] = {}
            x["inspire"] = 0
            x["pain_bonus"] = pain.get(str(h), 0)
            if not self.active(h):
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
                dice.append({"faces": list(range(1, 9 if m.get("pet_strike") else 5)), "dk": [], "src": "pet"})
            if any(y != h for y in anthem):
                dice.append({"faces": [1, 2, 3, 4], "dk": [], "src": "anthem"})
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
            if x["st"].pop("freeze", 0) and not m.get("freeze_immune") and x["dice"]:
                x["dice"].remove(min(x["dice"], key=_num))
        # Spirit dice for heroes who are dead
        f["spirit"] = {str(h): {"v": self.rng.randint(1, 6), "used": False}
                       for h in range(3) if not self.hero(h)["alive"]}
        # Intents
        for fo in self.foes():
            self.choose_intent(fo)
        self.fx("round", n=f["round"])

    def choose_intent(self, fo):
        f = self.s["fight"]
        d = A.FOES[fo["k"]]
        if f["ambush"] and f["round"] == 1:
            fo["intent"] = {"k": "dazed"}
            return
        if d.get("seq"):
            it = dict(d["seq"][fo["seq"] % len(d["seq"])])
            fo["seq"] += 1
        else:
            it = dict(self.rng.weighted([(i, i.get("w", 1)) for i in d["ints"]]))
        if it["k"] == "summon" and len(self.foes()) >= 5:
            it = {"k": "attack", "v": 5}
        if "v" in it and it["k"] in ("attack", "row", "all"):
            it["v"] = max(1, round(it["v"] * f["dmul"])) + fo["might"]
            if f["round"] == 1:
                heckle = max([self.mods(h).get("heckler", 0) for h in self.actives()] or [0])
                it["v"] = max(0, it["v"] - heckle)
        if it["k"] == "attack" or it["k"] == "debuff":
            it["tgt"] = self.foe_target(it, heroes_only=it["k"] == "debuff")
        elif it["k"] == "row":
            it["row"] = it.get("reach") == "back" and "back" or "front"
        it.pop("w", None)
        fo["intent"] = it

    def foe_target(self, it, heroes_only=False, exclude=None):
        units = [f"h{h}" for h in self.actives()] if heroes_only else self.party_units()
        units = [u for u in units if u != exclude]
        if not units:
            return None
        f = self.s["fight"]
        if f["taunt"] is not None and self.active(f["taunt"]) and f"h{f['taunt']}" != exclude:
            return f"h{f['taunt']}"
        seen = [u for u in units if not (u.startswith("h") and self.mods(int(u[1:])).get("camouflage"))]
        units = seen or units
        if it.get("weakest"):
            return min(units, key=lambda u: self.hero(int(u[1:]))["hp"] if u.startswith("h") else self.ally(int(u[1:]))["hp"])
        if it.get("melee"):
            units = [u for u in units if self.unit_row(u) == "front"] or units
        elif it.get("reach") == "back":
            units = [u for u in units if self.unit_row(u) == "back"] or units
        return self.rng.choice(units)

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
        if m.get("keen_edge") and v == 6:
            v = 7
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

    def outcomes(self, h, d):
        """What a die might come up as, for planning: [(value, tag, chance)]. No randomness used."""
        x = self.hs(h)
        add = d.get("bonus", 0) + self.s["fight"].get("hymn", 0)
        if d.get("rolled"):
            return [(d["v"], d.get("tag"), 1.0)]
        if d.get("v") is not None:
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
        out = []
        for v, t, p in base:
            if t not in ("S", "X"):
                v += add + (1 if d.get("link") and self.mods(h).get("sleight") else 0)
            out.append((v, t, p))
        del x
        return out

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
        if a.get("melee") and x["row"] != "front":
            raise Invalid("You need to be in the front row.")
        return None

    def do_place(self, h, msg):
        if not self.in_fight(h) or not self.active(h):
            raise Invalid("You're not fighting.")
        x = self.hs(h)
        if x["ready"]:
            raise Invalid("You've readied up; unready to change your plan.")
        key = msg.get("a")
        acts = self.actions_of(h)
        match = next((k for k in acts if k.rstrip("+") == key), None)
        if match is None:
            raise Invalid("You don't know that action.")
        a = self.action_def(h, match)
        f = self.s["fight"]
        if a.get("once") and (a["key"] in x["once"] or any(p["h"] == h and p["a"] == a["key"] for p in f["plan"])):
            raise Invalid("Once per fight.")
        if a.get("cd") and (x["cds"].get(a["key"]) or any(p["h"] == h and p["a"] == a["key"] for p in f["plan"])):
            left = x["cds"].get(a["key"], 0)
            raise Invalid(f"{a['name']} is cooling down: ready again {'in ' + str(left) + ' rounds' if left > 1 else 'next round'}."
                          if left else f"{a['name']} can only be used once a round.")
        if a.get("per_round") and a["key"] in x["round_once"]:
            raise Invalid("Once a round.")
        if a["key"] == "flee" and f["kind"] in ("dungeon", "boss"):
            raise Invalid("There's no running from this one.")
        if a["key"] in ("flee", "shift") and x["st"].get("root"):
            raise Invalid("You're Rooted.")
        ids = msg.get("dice") or []
        if not isinstance(ids, list) or len(set(ids)) != len(ids):
            raise Invalid("Pick dice.")
        dice = [next((d for d in x["dice"] if d["id"] == i and not d["used"]), None) for i in ids]
        if None in dice:
            raise Invalid("Those dice are already used.")
        if not a["def"] and any("guard" in (d.get("dk") or []) for d in dice):
            raise Invalid("Guard dice only go on defensive actions: Block, Armor, healing and the like.")
        if not self.count_ok(a["req"], dice):
            n = a["req"].get("n", 1)
            raise Invalid(f"That takes {'up to ' if a['req'].get('upto') else ''}{n} {'die' if n == 1 else 'dice'}.")
        if a.get("melee") and x["row"] != "front":
            raise Invalid("You need to be in the front row.")
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
        for d in dice:
            d["used"] = True
        entry = {"h": h, "a": a["key"], "plus": a["plus"], "dice": ids, "tgt": tgt}
        entry["est"] = self.estimate(h, a, dice, tgt)
        f["plan"].append(entry)

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
            elif k == "bottle":
                v = self.roll(h, dice[0])
                key = "big_potion" if v >= 5 else "potion"
                for _ in range(2 if m.get("philosopher") else 1):
                    self.gain_item(h, key)
        for d in dice:
            if d["id"] not in keep and d in x["dice"]:
                d["used"] = True
        self.fx("act", h=h, a=a["key"], tgt=tgt, instant=True)

    def do_unplace(self, h, msg):
        if not self.in_fight(h):
            raise Invalid("You're not fighting.")
        f = self.s["fight"]
        x = self.hs(h)
        if x["ready"]:
            raise Invalid("Unready first.")
        i = msg.get("i")
        mine = [p for p in f["plan"] if p["h"] == h]
        if not isinstance(i, int) or not 0 <= i < len(f["plan"]) or f["plan"][i]["h"] != h:
            if mine and i is None:
                i = f["plan"].index(mine[-1])
            else:
                raise Invalid("Undo what?")
        p = f["plan"].pop(i)
        for d in x["dice"]:
            if d["id"] in p["dice"]:
                d["used"] = False
        if p["a"] in x["round_once"]:
            x["round_once"].remove(p["a"])

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
        self.check_end()

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
             "pair": int(is_pair(vals, tags)), "straight": int(is_straight(vals, tags))}
        if isinstance(target, dict):
            st = target["st"]
            it = target.get("intent") or {}
            e.update(undead=int(bool(A.FOES[target["k"]].get("undead"))), rooted=int(bool(st.get("root"))),
                     stunned=int(bool(st.get("stun"))), poisoned=int(bool(st.get("poison"))), marked=int(bool(st.get("mark"))),
                     aimed=int(it.get("tgt") == f"h{h}"), matched=int(bool(vals) and it.get("v") is not None and vals[0] == it["v"]))
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
        if isinstance(target, dict):
            if target["st"].get("stun") or target["st"].get("root"):
                n += m.get("opportunist", 0)
            it = target.get("intent") or {}
            if it.get("tgt") and it.get("tgt") != f"h{h}":
                n += m.get("backstab", 0)
        return n

    def estimate(self, h, a, dice, tgt):
        """What a planned action will probably do: its chance to hit, and the expected number
        (with the lowest and highest it could be) for its first damage, heal or Armor effect."""
        from itertools import product
        target = self.foe(int(tgt[1:])) if isinstance(tgt, str) and tgt.startswith("f") else None
        per = [self.outcomes(h, d) for d in dice] or [[]]
        combos = list(product(*per)) if dice else [()]
        if len(combos) > 4000:
            combos = combos[:: len(combos) // 4000 + 1]
            norm = sum(_p(c) for c in combos)
        else:
            norm = 1.0
        p_hit, ev, lo, hi, kind = 0.0, 0.0, None, None, None
        for c in combos:
            vals = [o[0] for o in c]
            tags = [o[1] for o in c]
            pr = _p(c) / norm
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
        return max(0, n)

    def resolve_round(self):
        f = self.s["fight"]
        # Hero actions in the order they were placed; each one's dice roll as it happens.
        for p in list(f["plan"]):
            if self.s["fight"] is not f or not self.foes():
                break
            h = p["h"]
            if not self.active(h):
                continue
            x = self.hs(h)
            dice = [d for d in x["dice"] if d["id"] in p["dice"]]
            a = self.action_def(h, p["a"] + ("+" if p["plus"] else ""))
            if a.get("once"):
                x["once"].append(a["key"])
            if a.get("cd"):
                x["cds"][a["key"]] = a["cd"]
            hit = self.roll_for(h, a, dice)
            self.fx("act", h=h, a=a["key"], tgt=p["tgt"], hit=hit)
            ops = a["ops"] if hit else a.get("miss", [])
            self.run_ops(h, a, dice, p["tgt"], ops=ops)
            self.elements(h, a, dice, p["tgt"])
            if a.get("spell") and self.mods(h).get("spell_echo") and not x["echo"] and self.s["fight"] is f:
                x["echo"] = True
                self.fx("act", h=h, a=a["key"], tgt=p["tgt"], echo=True)
                self.run_ops(h, a, dice, p["tgt"], half=True, ops=ops)
            f["acts"][str(h)] = f["acts"].get(str(h), 0) + 1
            if self.s["fight"] is not f:
                return
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

    def targets_for(self, h, a, tgt):
        kind = a["tgt"]
        if kind == "foe":
            fo = self.foe(int(tgt[1:]))
            if not fo or fo["hp"] <= 0:
                # it died before this resolved: hit another in reach
                pool = self.front_foes() if a.get("melee") else self.foes()
                fo = pool[0] if pool else None
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
        if to == "front":
            return [("h", y) for y in self.actives() if self.hs(y)["row"] == "front"]
        if to == "myrow":
            return [("h", y) for y in self.actives() if self.hs(y)["row"] == x["row"]]
        return base

    def run_ops(self, h, a, dice, tgt, half=False, ops=None):
        m = self.mods(h)
        plus = 2 if a["plus"] else 0
        base = self.targets_for(h, a, tgt)
        x = self.hs(h)
        pierce_all = bool(m.get("unstoppable")) and a["key"] in UNSTOPPABLE
        crescendo = x["st"].get("crescendo")
        dealt_any = False

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
                        env = self.env(h, a, dice, t)
                        if d is not None:
                            env["d"] = _num(d)
                        n = scale(_amt(op["amt"], env) + plus) + self.dmg_bonus(h, a, t)
                        if crescendo:
                            n = n * 3 // 2
                        if m.get("eagle_eye"):
                            src = [d] if d is not None else dice
                            if any(_num(dd) and _num(dd) >= top_face(dd["faces"]) for dd in src):
                                n *= 2
                        done = self.hurt_foe(t, n, h, pierce=pierce_all or op.get("pierce"), bomb=a.get("bomb"))
                        dealt_any = True
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
                            self.fight_heal(h, done // 2, h)
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
            elif k == "shift":
                if x["st"].get("root") and not a.get("free_shift"):
                    continue
                x["row"] = "back" if x["row"] == "front" else "front"
                self.fx("shift", h=h, row=x["row"])
            elif k == "flee":
                x["fled"] = True
                hero = self.hero(h)
                hero["tile"], hero["afloat"] = hero["prev"], False
                self.fx("flee", h=h)
                self.say(f"{hero['name']} flees.")
            elif k == "guard":
                for t in targets:
                    if isinstance(t, tuple):
                        self.s["fight"]["guard"][str(t[1])] = h
                        self.fx("st", to=f"h{t[1]}", s="guarded")
            elif k == "taunt":
                f = self.s["fight"]
                f["taunt"] = h
                for fo in self.foes():
                    it = fo["intent"] or {}
                    if it.get("k") in ("attack", "debuff"):
                        it["tgt"] = f"h{h}"
                self.fx("st", to=f"h{h}", s="taunt")
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
                if m.get("aegis"):
                    f["aegis"] = max(f["aegis"], m["aegis"])
                self.fx("st", to="party", s="sanct")
            elif k == "weaken":
                n = scale(_amt(op["amt"], self.env(h, a, dice)) + plus)
                for t in targets:
                    it = t.get("intent") if isinstance(t, dict) else None
                    if it and it.get("v") is not None:
                        it["v"] = max(0, it["v"] - n)
                        self.fx("st", to=f"f{t['id']}", s="weakened")
            elif k == "retarget":
                for t in targets:
                    it = t.get("intent") if isinstance(t, dict) else None
                    if it and it.get("tgt"):
                        new = self.foe_target(it, exclude=it["tgt"])
                        if new is None:
                            t["intent"] = {"k": "dazed"}
                        else:
                            it["tgt"] = new
                        self.fx("st", to=f"f{t['id']}", s="distracted")
            elif k == "cancel":
                for t in targets:
                    if isinstance(t, dict) and t["hp"] > 0:
                        t["intent"] = {"k": "dazed"}
                        self.fx("st", to=f"f{t['id']}", s="dazed")
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
        arm = 0 if pierce else fo["st"].get("armor", 0)
        blocked = min(arm, n)
        if blocked:
            fo["st"]["armor"] = arm - blocked
        n -= blocked
        fo["hp"] -= n
        if h is not None:
            self.s["stats"][h]["dmg"] += n
        self.fx("dmg", to=f"f{fo['id']}", n=n, block=blocked)
        if not pure and fo["st"].pop("shock", 0) and n > 0:
            others = [o for o in self.foes() if o is not fo]
            if others:
                near = [o for o in others if o["row"] == fo["row"]] or others
                self.hurt_foe(near[0], n // 2, h, pure=True)
        if fo["hp"] <= 0:
            self.foe_dies(fo, h, bomb)
        return n

    def foe_dies(self, fo, h, bomb=False):
        f = self.s["fight"]
        fo["hp"] = 0
        d = A.FOES[fo["k"]]
        f["xp"] += d["xp"]
        f["gold"] += d["gold"]
        self.fx("die", to=f"f{fo['id']}")
        if h is not None and self.hero(h)["alive"]:
            self.s["stats"][h]["kills"] += 1
            m = self.mods(h)
            if m.get("kill_heal") and self.active(h):
                self.fight_heal(h, m["kill_heal"], h)
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
        if d.get("boss") and not d.get("final"):
            self.say(f"{d['name']} falls!")

    def fight_heal(self, h, n, by):
        hero = self.hero(h)
        mx = self.maxhp(h)
        got = min(max(0, n), mx - hero["hp"])
        hero["hp"] += got
        if by is not None:
            self.s["stats"][by]["heal"] += got
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
            n -= f["sanct"] + f["aegis"]
            if melee and x["row"] == "back":
                n -= 2
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
                f["plan"] = [p for p in f["plan"] if p["h"] != h]
                fury = self.mods(h).get("undying", 0)
                if fury and fo is not None and fo["hp"] > 0:
                    self.hurt_foe(fo, fury, h, pure=True)
        return n

    def foe_act(self, fo):
        f = self.s["fight"]
        it = fo["intent"] or {}
        if fo["st"].pop("stun", 0):
            self.fx("st", to=f"f{fo['id']}", s="stunned")
            return
        frozen = fo["st"].pop("freeze", 0)
        k = it.get("k")
        v = it.get("v", 0)
        if frozen:
            v //= 2
        if fo["st"].get("weak"):
            v = int(v * 0.75)
        self.fx("fact", f=fo["id"], ik=k)
        if k == "attack" or k == "debuff":
            t = it.get("tgt")
            if not self.unit_alive(t) or (k == "debuff" and t and t.startswith("s")):
                t = self.foe_target(it, heroes_only=k == "debuff")
            if t is None:
                return
            if f["taunt"] is not None and self.active(f["taunt"]):
                t = f"h{f['taunt']}"
            if k == "attack":
                self.hurt_unit(t, v, fo, melee=bool(it.get("melee")))
            if it.get("st") and t.startswith("h") and self.active(int(t[1:])):
                self.hero_status(int(t[1:]), it["st"], it.get("sn", 1))
        elif k in ("row", "all"):
            units = self.party_units()
            if k == "row":
                want = it.get("row", "front")
                units = [u for u in units if self.unit_row(u) == want] or units
            for u in units:
                self.hurt_unit(u, v, fo)
                if it.get("st") and u.startswith("h") and self.active(int(u[1:])) and self.rng.random() < it.get("chance", 1):
                    self.hero_status(int(u[1:]), it["st"], it.get("sn", 1))
        elif k == "block":
            fo["st"]["armor"] = fo["st"].get("armor", 0) + v
            self.fx("armor", to=f"f{fo['id']}", n=v)
        elif k == "guard":
            ally = min(self.foes(), key=lambda o: o["hp"] / o["max"])
            ally["st"]["armor"] = ally["st"].get("armor", 0) + v
            self.fx("armor", to=f"f{ally['id']}", n=v)
        elif k == "heal":
            ally = min(self.foes(), key=lambda o: o["hp"] / o["max"])
            got = min(v, ally["max"] - ally["hp"])
            ally["hp"] += got
            self.fx("heal", to=f"f{ally['id']}", n=got)
        elif k == "buff":
            for o in self.foes():
                o["might"] += v
            self.fx("st", to="foes", s="might")
        elif k == "summon":
            if len(self.foes()) < 5:
                new = self.add_foe(it["f"])
                new["intent"] = {"k": "dazed"}
                self.fx("summon", f=new["id"])

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
        f = self.s["fight"]
        crown = next((fo for fo in self.foes() if A.FOES[fo["k"]].get("final")), None)
        if not crown:
            return
        frac = crown["hp"] / crown["max"]
        if f["phase"] == 1 and frac <= 0.66:
            f["phase"] = 2
            self.say("The sea pours over the peak: the back row is flooding!")
            self.fx("phase", n=2)
        elif f["phase"] == 2 and frac <= 0.33:
            f["phase"] = 3
            for fo in self.foes():
                if fo is not crown:
                    fo["hp"] = 0
                    self.fx("die", to=f"f{fo['id']}")
            self.say("The Drowned Crown stands alone, and furious.")
            self.fx("phase", n=3)
        if f["phase"] >= 2:
            for h in self.actives():
                if self.hs(h)["row"] == "back":
                    self.hurt_hero(h, 3, None, pure=True)

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
            for h in winners:
                if f["kind"] in ("lair", "dungeon"):
                    bonus = 2 if f["kind"] == "dungeon" and f["step"] == len(A.DUNGEONS[f["region"]]["fights"]) - 1 else 1
                    self.offer_loot(h, 3 if bonus == 2 else 2, tier_bonus=bonus)
                elif self.rng.chance(0.35):
                    self.offer_loot(h, 2)
            if f["kind"] == "dungeon":
                reg = f["region"]
                step = f["step"] + 1
                s["dungeon"][reg] = step
                fights = A.DUNGEONS[reg]["fights"]
                if step >= len(fights):
                    s["cleared"].append(reg)
                    self.say(f"{A.DUNGEONS[reg]['name']} is cleared! ({len(s['cleared'])} of 3)")
                    self.fx("cleared", region=reg)
                    if len(s["cleared"]) == 3:
                        self.say("All three are cleared. The way to the peak is open.")
                else:
                    still = [h for h in party if self.hero(h)["alive"] and not self.hs_from(f, h)["fled"]]
                    if still:
                        s["fights"].insert(0, {"kind": "dungeon", "tile": f["tile"], "heroes": still, "region": reg,
                                               "step": step, "foes": list(fights[step]), "by": None})
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
                    g["foes"] = [{"k": fo["k"], "hp": fo["hp"]} for fo in alive.values()][:5]
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
        out = {k: f[k] for k in ("id", "kind", "tile", "heroes", "round", "foes", "plan", "guard", "taunt",
                                 "sanct", "aegis", "spirit", "region", "step", "phase", "ambush", "allies")}
        out["hymn"] = f.get("hymn", 0)
        out["hs"] = {k: dict(x, dice=[{kk: vv for kk, vv in d.items() if kk not in ("sv", "stag")} for d in x["dice"]])
                     for k, x in f["hs"].items()}
        return out
