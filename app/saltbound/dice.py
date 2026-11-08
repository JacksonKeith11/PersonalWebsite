"""Dice: faces, rolling, and the odds of an action's dice (for planning and the bots).

Pure helpers at the top (a face's value and tag, condition checks, amount expressions); the `Dice`
mixin rolls a hero's dice during a fight. Mixed into `Game` through `Combat`.
"""

from itertools import product

from .tuning import SHIELD_BLOCK

_CODE = {}
_GLOBALS = {"__builtins__": {}, "max": max, "min": min}


def amt(expr, env):
    if isinstance(expr, (int, float)):
        return int(expr)
    code = _CODE.get(expr)
    if code is None:
        code = _CODE[expr] = compile(expr, "<amt>", "eval")
    return int(eval(code, _GLOBALS, env))  # expressions come only from our own data


TAGS = {"F": "burn", "I": "freeze", "P": "poison"}


def face(f):
    """(value, tag) for a die face: numbers, "S" shield, "X" skull, "W" wild, "R" resonance, "F3"/"I3"/"P3"."""
    if isinstance(f, int):
        return f, None
    if f in ("S", "X"):
        return 0, f
    if f == "W":
        return None, "W"
    if f == "R":
        return 3, "R"  # Resonance: a 3 while planning; it takes an ally's number when it rolls (Dice.roll)
    return int(f[1:]), TAGS[f[0]]


def top_face(faces):
    return max([face(f)[0] for f in faces if face(f)[0] is not None] or [0])


def mean_face(faces):
    vals = [face(f)[0] if face(f)[1] != "W" else top_face(faces) for f in faces]
    return sum(vals) / len(vals)


def fate_faces(d):
    """A Fate die's two faces, as (value, tag) pairs (saves from before Nov 2026 kept bare numbers)."""
    return [tuple(x) if isinstance(x, (list, tuple)) else (x, None) for x in d["fc"]]


def num(d):
    """A die's value: rolled or shown, else (while planning) what it rolls on average."""
    if isinstance(d.get("v"), int):
        return d["v"]
    if d.get("v") is None and "faces" in d:
        return round(mean_face(d["faces"]))
    return 0



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


class Dice:
    def new_die(self, h, faces, src, dk=None):
        """A die that joins a hero's hand mid-round (split, grafted, stolen tempo...)."""
        x = self.hs(h)
        x["nid"] = x.get("nid", 0) + 1
        return {"id": f"{h}.{self.s['fight']['round']}.n{x['nid']}", "faces": faces, "dk": list(dk or []), "src": src,
                "used": False, "v": None, "bonus": 0, "top": False}

    def resonant(self, h):
        """What a Resonance face rolls for hero h: the biggest number the last other hero to play a die
        this round played (so it lines up a Chord), or 3 if nobody else has."""
        for y, v in reversed(self.s["fight"].get("plays", [])):
            if y != h:
                return v
        return 3

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
            v, t = self.rng.choice(fate_faces(d))
        else:
            v, t = self.raw_roll(h, d)
        if t == "R":
            v = self.resonant(h)
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
        v = self.face_rules(h, d, v, t)
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

    def face_rules(self, h, d, v, t):
        """What a hero's passives make of a face before bonuses: Bulwark Faces (a shield still
        blocks, and is worth the top face), Heedless (a skull is the top face, and still hurts),
        Weighted Coin (a 1 is the top face), Keen Edge (6 is 7). Rolling and planning (`outcomes`)
        both use this."""
        m = self.mods(h)
        if m.get("shield_top") and t == "S":
            v = top_face(d["faces"])
        if m.get("skull_top") and t == "X":
            v = top_face(d["faces"])
        if m.get("one_is_top") and v == 1 and t is None:
            v = top_face(d["faces"])
        if m.get("keen_edge") and v == 6:
            v = 7
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
            base = [(v, t, 0.5) for v, t in fate_faces(d)]
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
                elif t == "R":
                    v = self.resonant(h)  # what it would copy if it rolled now
                if "exploding" in d["dk"] and v == top and t != "W":
                    v += round(mean_face(d["faces"]))
                base.append((v, t, 1 / len(faces)))
        base = [(self.face_rules(h, d, v, t), t, p) for v, t, p in base]
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
