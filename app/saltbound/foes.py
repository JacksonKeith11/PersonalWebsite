"""Enemies: their dice, their moves, and what they do on their turn. Mixed into `Game` through `Combat`.

Enemies roll dice the way heroes do. Each enemy has a pool of dice (`dice` in `FOES`) and a set of
moves (`moves`); each round it picks a move, which names the dice it will roll (`use`, indices into
the pool, or the first `n`). The intent the party sees is that move: its name, the dice (with any
the party can already read), the flat bonus the enemy adds (difficulty, region and might), the
range, and who it's aimed at. When the enemy acts it rolls those dice in the open.

Dice faces: numbers, `X` skull (the die is 0 and the enemy takes 2), `S` shield (the die is 0 and
the enemy gains 3 Armor), `W` wild (its top face), `F4`/`I4`/`P4` (a 4 that also Burns, Freezes or
Poisons whoever it hits). Kinds (`dk`): exploding (a top face rolls again and adds), steady (a roll
in its bottom third rolls again), seer (rolled when the intent is chosen, and shown), fate (two
faces shown, one of them comes up), grow (the die gets 4 faces bigger with every Charge).

Move kinds: attack (one target; `each` makes every die its own hit on its own target, `sweep: N`
hits N different targets with the total, `chain` jumps to a second target for half), all (every
hero and summon), block (Armor for itself), guard (Armor for its most hurt ally), heal (its most
hurt ally), buff (`v` might for every enemy), debuff (a status), summon (`f`), charge (Rams: the
next attack rolls an extra die; growing dice: one size up).
Move pools: `pool` holds extra moves; each enemy draws one when it appears (bosses add theirs to
the end of their `seq`), so two Cutthroats can fight differently. Its moves are `fo["mv"]`.
Elites: an enemy can carry an affix (`fo["aff"]`, `ELITES` in the content): more health and a twist
(an extra die, exploding dice, Armor every round, Poison, rallying, leeching), and double the XP
and gold. `bloodied`: when a big enemy drops to half health it gains might and new moves, once.
Options: `self` on buff/heal (only itself), `all` on guard (every enemy).
Riders: `st`/`sn` a status on whoever is hit; `st_min` only if a die rolls at least that; `pair`
something extra on doubles (`st`/`sn`, or `again` to hit a second time). Targeting (`tgt`): random
(default), weakest, strongest, vengeful (whoever hurt it most last round).
"""

from .content import archipelago as A
from .tuning import SWALLOW_GUT

ELEMENT = {"F": "burn", "I": "freeze", "P": "poison"}
SKULL_SELF = 2
SHIELD_FACE = 3


def _face(f):
    """(value, tag) of a face."""
    if isinstance(f, int):
        return f, None
    if f in ("X", "S"):
        return 0, f
    if f == "W":
        return None, "W"
    return int(f[1:]), f[0]


def die_faces(d, grow=0):
    faces = list(d["faces"])
    if "grow" in d.get("dk", []) and grow:
        top = max(_face(x)[0] or 0 for x in faces)
        faces = list(range(1, top + 4 * grow + 1))
    return faces


def die_range(faces):
    nums = [_face(x)[0] for x in faces]
    top = max(n for n in nums if n is not None)
    return min(n if n is not None else top for n in nums), top


def die_mean(faces, dk=()):
    nums = [_face(x)[0] for x in faces]
    top = max(n for n in nums if n is not None)
    vals = [n if n is not None else top for n in nums]
    mean = sum(vals) / len(vals)
    if "exploding" in dk:
        mean += mean / len(vals)
    if "steady" in dk:
        cut = top / 3
        low = [v for v in vals if v <= cut]
        mean = mean + len(low) / len(vals) * (mean - sum(low) / max(1, len(low)))
    return mean


class Foes:
    # ------------------------------------------------------------------ choosing a move

    def foe_moves(self, fo):
        """This enemy's moves: its kind's, plus the pool move it drew, plus bloodied ones."""
        d = A.FOES[fo["k"]]
        allm = {**d["moves"], **d.get("pool", {}), **(d.get("bloodied", {}).get("moves", {}))}
        keys = fo.get("mv") or list(d["moves"])
        return {k: allm[k] for k in keys if k in allm}

    def foe_setup(self, fo, aff=None, rng=True):
        """A new enemy draws its pool move and takes its affix."""
        d = A.FOES[fo["k"]]
        fo["mv"] = list(d["moves"])
        pool = list(d.get("pool", {}))
        if pool and rng:
            extra = self.rng.choice(pool)
            if d.get("seq"):
                fo["sq"] = list(d["seq"]) + [extra]
            fo["mv"].append(extra)
        if aff and aff in A.ELITES:
            e = A.ELITES[aff]
            fo["aff"] = aff
            fo["name"] = e["name"] + " " + fo["name"]
            old = fo["max"]
            fo["max"] = max(1, round(old * e["hp"]))
            if fo["hp"] >= old:
                fo["hp"] = fo["max"]

    def foe_bloodied(self, fo):
        """A big enemy at half health: once, it gains might and its bloodied moves."""
        b = A.FOES[fo["k"]].get("bloodied")
        if not b or fo.get("bl") or fo["hp"] <= 0 or fo["hp"] * 2 > fo["max"]:
            return
        fo["bl"] = True
        fo["might"] += b.get("might", 0)
        fo["mv"] = list(fo.get("mv") or A.FOES[fo["k"]]["moves"]) + list(b.get("moves", {}))
        self.fx("st", to=f"f{fo['id']}", s="bloodied")
        self.say(f"{fo['name']} is bloodied: {b['text']}")
        rule = b.get("rule")
        if rule == "air":
            fo["air"] = True
        elif rule == "swallow":
            prey = [y for y in self.actives() if not self.hs(y).get("swallowed")]
            if prey:
                y = self.rng.choice(prey)
                self.hs(y)["swallowed"] = fo["id"]
                fo["gut"] = max(8, round(fo["max"] * SWALLOW_GUT))
                self.fx("st", to=f"h{y}", s="swallowed")
                self.say(f"{fo['name']} swallows {self.hero(y)['name']}!")

    def foe_leech(self, fo):
        return A.FOES[fo["k"]].get("leech") or fo.get("aff") == "vampiric"

    def choose_intent(self, fo):
        f = self.s["fight"]
        d = A.FOES[fo["k"]]
        if f["ambush"] and f["round"] == 1:
            fo["intent"] = {"k": "dazed", "name": "Caught off guard", "by_hero": True}
            return
        moves = self.foe_moves(fo)
        if fo.get("force") in moves:
            key = fo.pop("force")  # a boss's rule picked this one (the Bell-Warden's Death Knell)
        elif fo.get("next") in moves:
            key = fo.pop("next")  # a telegraphed follow-up (the Wyvern's breath after Draw Breath)
        elif d.get("seq"):
            seq = fo.get("sq") or d["seq"]
            key = seq[fo["seq"] % len(seq)]
            fo["seq"] += 1
            if fo.get("bl") and d.get("bloodied") and self.rng.chance(0.5):
                key = self.rng.choice(list(d["bloodied"]["moves"]))
        else:
            keys = list(moves)
            if fo.get("charged"):
                # a charged enemy spends it on its next attack
                keys = [k for k in keys if moves[k]["k"] in ("attack", "all")] or keys
            key = self.rng.weighted([(k, moves[k].get("w", 1)) for k in keys])
        mv = moves[key]
        if mv["k"] == "summon" and (len(self.foes()) >= 5 or (d.get("final") and f.get("phase", 1) >= 2)):
            key = next((k for k in moves if moves[k]["k"] == "attack"), key)
            mv = moves[key]
        thief_to = None
        if mv["k"] == "thief":
            from .content import items as I
            marks = [y for y in self.actives() if any(I.ITEMS[it]["slot"] == "use" for it in self.hero(y)["bag"])]
            thief_to = self.rng.choice(marks) if marks and not fo.get("loot") else None
        if (mv["k"] == "thief" and thief_to is None) or \
                (mv["k"] == "merge" and not any(o is not fo and o["k"] == fo["k"] for o in self.foes())):
            key = next((k for k in moves if moves[k]["k"] == "attack"), key)
            mv = moves[key]
        it = {"k": mv["k"], "m": key, "name": mv["name"]}
        for opt in ("each", "sweep", "chain", "st", "sn", "st_min", "pair", "v", "f", "self", "all", "next"):
            if opt in mv:
                it[opt] = mv[opt]
        it["tgt_kind"] = mv.get("tgt", "random")
        if thief_to is not None:
            it["tgt"] = f"h{thief_to}"
        if mv["k"] in ("attack", "all", "block", "guard", "heal", "debuff") and (mv.get("use") or mv.get("n")):
            idx = mv.get("use") or list(range(mv["n"]))
            dice = []
            for i in idx:
                src = d["dice"][i]
                src = src if isinstance(src, dict) else {"faces": src}
                die = {"faces": die_faces(src, fo.get("grow", 0)), "dk": list(src.get("dk", []))}
                if "seer" in die["dk"]:
                    die["v"], die["tag"] = self.foe_roll_face(die["faces"])
                elif "fate" in die["dk"]:
                    die["fc"] = [self.foe_roll_face(die["faces"]), self.foe_roll_face(die["faces"])]
                if fo.get("aff") == "frenzied" and "exploding" not in die["dk"]:
                    die["dk"].append("exploding")
                dice.append(die)
            more = (1 if fo.get("aff") == "hulking" or fo.get("fury") else 0) + fo.get("merged", 0)
            if more and mv["k"] in ("attack", "all") and dice:
                for _ in range(more):
                    extra = dict(dice[0], dk=[k for k in dice[0]["dk"] if k not in ("seer", "fate")])
                    extra.pop("v", None), extra.pop("fc", None), extra.pop("tag", None)
                    dice.append(extra)
            if fo.get("charged") and mv["k"] in ("attack", "all"):
                extra = dict(dice[0], dk=[k for k in dice[0]["dk"] if k not in ("seer", "fate")])
                extra.pop("v", None), extra.pop("fc", None), extra.pop("tag", None)
                dice.append(extra)
                it["charged"] = True
            it["dice"] = dice
            it["bonus"] = 0
            if mv["k"] in ("attack", "all"):
                it["bonus"] = self.foe_bonus(fo, it)
                if f["round"] == 1:
                    heckle = max([self.mods(h).get("heckler", 0) for h in self.actives()] or [0])
                    it["bonus"] -= heckle
            self.intent_numbers(it)
        if mv["k"] in ("attack", "debuff"):
            if mv.get("each"):
                it["tgts"] = [self.foe_target(it, heroes_only=False) for _ in it["dice"]]
                it["tgts"] = [t for t in it["tgts"] if t]
            elif mv.get("sweep"):
                it["tgts"] = self.foe_targets(it, mv["sweep"])
            else:
                it["tgt"] = self.foe_target(it, heroes_only=mv["k"] == "debuff")
                grudge = {k2: v2 for k2, v2 in fo.get("hurt_by", {}).items() if self.active(int(k2))}
                if it["tgt_kind"] == "vengeful" and grudge and f["taunt"] is None:
                    it["tgt"] = "h" + max(grudge, key=grudge.get)
        fo["hurt_by"] = {}
        fo["intent"] = it

    def foe_bonus(self, fo, it):
        """What an enemy adds to each hit: its dice's average times the difficulty and region
        multiplier above 1, plus its might."""
        f = self.s["fight"]
        dice = it["dice"]
        per = [die_mean(d["faces"], d["dk"]) for d in dice]
        base = sum(per) / len(per) if it.get("each") else sum(per)
        return round(base * (f["dmul"] - 1)) + fo["might"]

    def intent_numbers(self, it):
        """The lowest, highest and average of an intent's roll (per hit for `each`)."""
        dice = it.get("dice") or []
        if not dice:
            return
        rng, means = [], []
        for d in dice:
            if d.get("v") is not None:
                rng.append((d["v"], d["v"]))
                means.append(d["v"])
            elif d.get("fc"):
                vals = [x[0] if x[0] is not None else die_range(d["faces"])[1] for x in d["fc"]]
                rng.append((min(vals), max(vals)))
                means.append(sum(vals) / 2)
            else:
                lo, hi = die_range(d["faces"])
                if "exploding" in d["dk"]:
                    hi = hi * 2
                rng.append((lo, hi))
                means.append(die_mean(d["faces"], d["dk"]))
        b = it.get("bonus", 0)
        if it.get("each"):
            it["lo"] = max(0, min(r[0] for r in rng) + b)
            it["hi"] = max(0, max(r[1] for r in rng) + b)
            it["v"] = max(0, round(sum(means) / len(means) + b))
        else:
            it["lo"] = max(0, sum(r[0] for r in rng) + b)
            it["hi"] = max(0, sum(r[1] for r in rng) + b)
            it["v"] = max(0, round(sum(means) + b))

    def foe_roll_face(self, faces):
        v, tag = _face(self.rng.choice(faces))
        if tag == "W":
            v = die_range(faces)[1]
        return v, tag

    # ------------------------------------------------------------------ targets

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
        kind = it.get("tgt_kind", "random")
        hp = lambda u: self.hero(int(u[1:]))["hp"] if u.startswith("h") else self.ally(int(u[1:]))["hp"]
        if kind == "weakest":
            return min(units, key=hp)
        if kind == "strongest":
            return max(units, key=hp)
        return self.rng.choice(units)

    def foe_targets(self, it, n):
        units = self.party_units()
        f = self.s["fight"]
        if f["taunt"] is not None and self.active(f["taunt"]):
            return [f"h{f['taunt']}"]
        out = []
        pool = list(units)
        while pool and len(out) < n:
            u = self.rng.choice(pool)
            pool.remove(u)
            out.append(u)
        return out

    def intent_aims(self, it):
        """Every unit an intent will hit, as things stand."""
        if it.get("k") == "all":
            return self.party_units()
        if it.get("tgts"):
            return list(it["tgts"])
        return [it["tgt"]] if it.get("tgt") else []

    def retarget_intents(self, to, frm=None, first_only=False):
        """Swing enemy attacks at `to` (Taunt: all of them; Guard: the first one aimed at `frm`)."""
        order = sorted(self.foes(), key=lambda fo: -A.FOES[fo["k"]]["speed"])
        for fo in order:
            it = fo.get("intent") or {}
            if it.get("k") not in ("attack", "debuff"):
                continue
            changed = False
            if it.get("tgt") and it["tgt"] != to and (frm is None or it["tgt"] == frm):
                it["tgt"] = to
                changed = True
            elif it.get("tgts"):
                for i, t in enumerate(it["tgts"]):
                    if t != to and (frm is None or t == frm):
                        it["tgts"][i] = to
                        changed = True
                        if first_only:
                            break
            if changed:
                if frm is not None:
                    it["guarded"] = to
                self.fx("retarget", f=fo["id"], to=to)
                if first_only:
                    return True
        return False

    # ------------------------------------------------------------------ acting

    def foe_act(self, fo):
        it = fo["intent"] or {}
        if fo["st"].pop("stun", 0):
            self.fx("st", to=f"f{fo['id']}", s="stunned")
            self.lost_action(fo)
            return
        frozen = fo["st"].pop("freeze", 0)
        k = it.get("k")
        if k in (None, "dazed"):
            self.fx("fact", f=fo["id"], ik="dazed")
            if it.get("by_hero"):
                self.lost_action(fo)
            return
        if k == "charge":
            self.fx("fact", f=fo["id"], ik="charge")
            nxt = self.foe_moves(fo).get(it.get("m"), {}).get("next")
            if nxt:
                fo["next"] = nxt
            if any("grow" in (d.get("dk") if isinstance(d, dict) else []) for d in A.FOES[fo["k"]]["dice"]):
                fo["grow"] = fo.get("grow", 0) + 1
                self.fx("st", to=f"f{fo['id']}", s="grows")
            else:
                fo["charged"] = True
                self.fx("st", to=f"f{fo['id']}", s="charged")
            return
        if it.get("charged"):
            fo.pop("charged", None)
        if k in ("buff", "summon", "thief", "merge"):
            self.fx("fact", f=fo["id"], ik=k)
            self.foe_do(fo, it, k, [], [])
            return
        rolled = self.foe_roll(fo, it)
        vals = [r["v"] for r in rolled]
        tags = [r.get("tag") for r in rolled]
        pair = len(vals) >= 2 and len(set(vals)) < len(vals)
        top = max(vals) if vals else 0
        note = None
        if any(t == "X" for t in tags):
            note = "skull"
        if any(r.get("ex") for r in rolled):
            note = "explodes"
        if pair and it.get("pair"):
            note = "doubles"
        if it.get("st_min") and top >= it["st_min"]:
            note = note or "rider"
        self.fx("froll", f=fo["id"], name=it.get("name"), ik=k, dice=rolled, lo=it.get("lo"), hi=it.get("hi"),
                bonus=it.get("bonus", 0), note=note)
        for r in rolled:
            if r.get("tag") == "X":
                self.hurt_foe(fo, SKULL_SELF, None, pure=True)
            elif r.get("tag") == "S":
                fo["st"]["armor"] = fo["st"].get("armor", 0) + SHIELD_FACE
                self.fx("armor", to=f"f{fo['id']}", n=SHIELD_FACE)
        if fo["hp"] <= 0:
            return
        times = 2 if pair and (it.get("pair") or {}).get("again") else 1
        for _ in range(times):
            if fo["hp"] <= 0 or not self.actives():
                return
            self.fx("fact", f=fo["id"], ik=k)
            self.foe_do(fo, it, k, rolled, tags, frozen=frozen, pair=pair)
        if A.FOES[fo["k"]].get("keg") and fo["hp"] > 0:
            # a keg that blew is gone
            fo["hp"] = 0
            self.fx("die", to=f"f{fo['id']}")

    def foe_roll(self, fo, it):
        """Roll an intent's dice in the open: [{v, tag, re, ex}]."""
        out = []
        for d in it.get("dice") or []:
            r = {}
            if d.get("v") is not None:
                v, tag = d["v"], d.get("tag")
            elif d.get("fc"):
                v, tag = self.rng.choice(d["fc"])
                if tag == "W":
                    v = die_range(d["faces"])[1]
            else:
                v, tag = self.foe_roll_face(d["faces"])
                lo, hi = die_range(d["faces"])
                if "steady" in d["dk"] and tag is None and v <= hi / 3:
                    r["re"] = v
                    v, tag = self.foe_roll_face(d["faces"])
                if "exploding" in d["dk"] and v == hi and tag is None:
                    more, _ = self.foe_roll_face(d["faces"])
                    r["ex"] = more
                    v += more
            r["v"], r["tag"] = v or 0, tag
            out.append(r)
        return out

    def foe_do(self, fo, it, k, rolled, tags, frozen=False, pair=False):
        """An enemy's move landing, its dice already rolled."""
        f = self.s["fight"]
        vals = [r["v"] for r in rolled]
        bonus = it.get("bonus", 0)
        top = max(vals) if vals else 0
        riders = []
        if it.get("st") and (not it.get("st_min") or top >= it["st_min"]):
            riders.append((it["st"], it.get("sn", 1)))
        if pair and (it.get("pair") or {}).get("st"):
            riders.append((it["pair"]["st"], it["pair"].get("sn", 1)))

        def scale(n):
            if frozen:
                n //= 2
            if fo["st"].get("weak"):
                n = int(n * 0.75)
            return max(0, n)

        def landed(u, n, elems):
            if not u or not self.unit_alive(u):
                return
            if u.startswith("h") and self.active(int(u[1:])):
                y = int(u[1:])
                for s, sn in riders:
                    self.hero_status(y, s, sn)
                for e in elems:
                    self.hero_status(y, e, 2 if e != "freeze" else 1)
            if fo.get("aff") == "venomous" and n and u.startswith("h") and self.active(int(u[1:])):
                self.hero_status(int(u[1:]), "poison", 2)
            if self.foe_leech(fo) and n and fo["hp"] > 0:
                got = min((n + 1) // 2, fo["max"] - fo["hp"])
                if got:
                    fo["hp"] += got
                    self.fx("heal", to=f"f{fo['id']}", n=got)

        def live(u):
            # the target fell or fled before this landed: someone else takes it
            if u and self.unit_alive(u):
                return u
            return self.foe_target(it, heroes_only=k == "debuff")

        def taunted(u):
            if f["taunt"] is not None and self.active(f["taunt"]):
                return f"h{f['taunt']}"
            return u

        elems = [ELEMENT[t] for t in tags if t in ELEMENT]
        if k == "attack":
            if it.get("each"):
                tg = list(it.get("tgts") or [])
                for i, r in enumerate(rolled):
                    u = taunted(live(tg[i] if i < len(tg) else None))
                    if u is None or fo["hp"] <= 0:
                        continue
                    n = scale(r["v"] + bonus) if r.get("tag") not in ("X", "S") else 0
                    if n:
                        landed(u, self.hurt_unit(u, n, fo), [ELEMENT[r["tag"]]] if r.get("tag") in ELEMENT else [])
            else:
                n = scale(sum(vals) + bonus)
                aims = [taunted(live(u)) for u in (it.get("tgts") or [it.get("tgt")])]
                seen = []
                for u in aims:
                    if u is None or u in seen:
                        continue
                    seen.append(u)
                    landed(u, self.hurt_unit(u, n, fo), elems)
                if it.get("chain") and seen:
                    others = [u for u in self.party_units() if u not in seen]
                    if others:
                        u = self.rng.choice(others)
                        self.fx("st", to=u, s="arced")
                        landed(u, self.hurt_unit(u, n // 2, fo), [])
        elif k == "all":
            n = scale(sum(vals) + bonus)
            for u in self.party_units():
                landed(u, self.hurt_unit(u, n, fo), elems)
        elif k == "debuff":
            u = taunted(live(it.get("tgt")))
            if u and u.startswith("h") and self.active(int(u[1:])):
                if riders:
                    for s, sn in riders:
                        self.hero_status(int(u[1:]), s, sn)
                else:
                    self.fx("st", to=u, s="resisted")
        elif k == "block":
            n = sum(vals)
            fo["st"]["armor"] = fo["st"].get("armor", 0) + n
            self.fx("armor", to=f"f{fo['id']}", n=n)
        elif k == "guard" and it.get("all"):
            n = sum(vals)
            for o in self.foes():
                o["st"]["armor"] = o["st"].get("armor", 0) + n
                self.fx("armor", to=f"f{o['id']}", n=n)
        elif k == "guard":
            n = sum(vals)
            others = [o for o in self.foes() if o is not fo] or [fo]
            ally = min(others, key=lambda o: o["hp"] / o["max"])
            ally["st"]["armor"] = ally["st"].get("armor", 0) + n
            self.fx("armor", to=f"f{ally['id']}", n=n)
        elif k == "heal":
            n = sum(vals)
            ally = fo if it.get("self") else min(self.foes(), key=lambda o: o["hp"] / o["max"])
            got = min(n, ally["max"] - ally["hp"])
            ally["hp"] += got
            self.fx("heal", to=f"f{ally['id']}", n=got)
        elif k == "buff":
            for o in ([fo] if it.get("self") else self.foes()):
                o["might"] += it.get("v", 2)
            self.fx("st", to=f"f{fo['id']}" if it.get("self") else "foes", s="might")
        elif k == "thief":
            # the Harpy snatches a potion; kill it within two rounds to get it back
            from .content import items as I
            y = int(it["tgt"][1:]) if it.get("tgt") else None
            if y is not None and self.active(y):
                bag = self.hero(y)["bag"]
                got = next((i for i, x in enumerate(bag) if I.ITEMS[x]["slot"] == "use"), None)
                if got is not None:
                    fo["loot"] = bag.pop(got)
                    fo["flee_in"] = 2
                    self.fx("st", to=f"f{fo['id']}", s="snatched")
                    self.say(f"{fo['name']} snatches {self.hero(y)['name']}'s {I.ITEMS[fo['loot']]['name']}! Kill it within two rounds to get it back.")
        elif k == "merge":
            other = next((o for o in self.foes() if o is not fo and o["k"] == fo["k"]), None)
            if other:
                fo["hp"] += other["hp"]
                fo["max"] += other["max"]
                fo["merged"] = fo.get("merged", 0) + 1 + other.get("merged", 0)
                other["hp"] = 0
                self.fx("die", to=f"f{other['id']}")
                self.fx("st", to=f"f{fo['id']}", s="merged")
        elif k == "summon":
            if len(self.foes()) < 5:
                new = self.add_foe(it["f"])
                new["intent"] = {"k": "dazed", "name": "Just arrived"}
                self.fx("summon", f=new["id"])
