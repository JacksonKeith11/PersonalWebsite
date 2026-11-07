"""What heroes do together: Chord (the same number, back to back, on one enemy), the elemental
reactions (one hero's status meets another's), Break (enough damage to stop a boss's big move), the
Bell-Warden's crack, and Spiteful elites. The numbers are in tuning.py, the words in COMBOS in
classes.py. Mixed into `Game` through `Combat`."""

from .dice import num
from .tuning import (BELL_CRACK, CHORD_CAP, FROSTLOCK_BOSS, REACT_BLIGHT, REACT_FRACTURE, REACT_FRACTURE_EACH,
                     REACT_KINDLE, REACT_KINDLE_CAP, REACT_OVERLOAD, REACT_OVERLOAD_EACH, REACT_THERMAL,
                     REACT_THERMAL_EACH)

# Two statuses from two different heroes on one enemy react, and both are used up.
ELEMENTS = ("burn", "freeze", "shock", "poison", "root")
REACTIONS = {
    frozenset(("burn", "shock")): "overload",
    frozenset(("burn", "freeze")): "thermal",
    frozenset(("burn", "poison")): "blightfire",
    frozenset(("freeze", "shock")): "fracture",
    frozenset(("poison", "shock")): "conduction",
    frozenset(("root", "freeze")): "frostlock",
    frozenset(("root", "burn")): "kindling",
}


class Combos:
    # ---------------------------------------------------------------- Chord
    # A hero hits an enemy; the very next action the party plays is another hero's, on the same enemy,
    # with a die showing a number the first one showed: it copies the first hit. A third hero right
    # after, with that number again, copies it twice. Any other action in between ends it.
    def chord_open(self, h, a, dice, tgt):
        """Before an action resolves: the Chord bonus its first hit on `tgt` would get (0 for none);
        it becomes the next action in the round's order."""
        f = self.s["fight"]
        bonus, shared = self.chord_for(h, tgt, [num(d) for d in dice])
        f["seq"] = f.get("seq", 0) + 1
        f["cur"] = {"h": h, "t": tgt, "n": None, "bonus": bonus, "vals": shared}

    def chord_for(self, h, tgt, vals):
        """The Chord bonus hero h's next action would get on `tgt` with these numbers, and the
        numbers it shares with the chord (the bots use this too)."""
        f = self.s["fight"]
        ch = f.get("chord")
        if not ch or ch["seq"] != f.get("seq", 0) or h in ch["hs"] or tgt != ch["t"]:
            return 0, []
        shared = sorted({v for v in vals if v in ch["vals"]})
        if not shared:
            return 0, []
        return min(ch["base"], CHORD_CAP) * len(ch["hs"]) + self.mods(h).get("combo_up", 0), shared

    def chord_hit(self, h, t, n):
        """The first hit of the action now resolving on its target: add the Chord, and remember it."""
        cur = self.s["fight"].get("cur")
        if not cur or cur["h"] != h or cur["n"] is not None or cur["t"] != f"f{t['id']}":
            return n
        if cur["bonus"]:
            n += cur["bonus"]
            self.fx("combo", to=f"f{t['id']}", c="chord", n=cur["bonus"], lvl=len(self.s["fight"]["chord"]["hs"]) + 1)
        cur["n"] = n
        return n

    def chord_close(self, h, dice):
        """After an action: it carries the Chord on, starts a new one, or (no hit on one enemy) ends it."""
        f = self.s["fight"]
        cur = f.pop("cur", None)
        if not cur:
            return
        ch = f.get("chord")
        if cur["n"] is None:
            f["chord"] = None
        elif cur["bonus"] and ch:
            ch.update(hs=ch["hs"] + [h], vals=cur["vals"], seq=f["seq"])
            if len(ch["hs"]) >= 3:
                f["chord"] = None  # three heroes is the whole chord
        else:
            vals = sorted({num(d) for d in dice if num(d)})
            f["chord"] = {"t": cur["t"], "hs": [h], "vals": vals, "base": cur["n"], "seq": f["seq"]} if vals else None

    # ---------------------------------------------------------------- elemental reactions
    def foe_status_by(self, fo, s, h):
        """Who put a status on an enemy; a status meeting a different hero's other element reacts."""
        if fo["hp"] <= 0 or h is None:
            return
        if s == "poison" and not fo.get("qf") and str(h) in self.s["fight"]["hs"] and "trinkets" in self.hs(h) \
                and self.mods(h).get("quick_fingers"):
            fo["qf"] = True
            self.pilfer(h)  # Quick Fingers: the first Poison on each enemy lifts a trinket
        by = fo.setdefault("st_by", {})
        by[s] = h
        kind, other = self.reaction_on(fo, s, h)
        if kind:
            self.react_elements(fo, kind, h)

    def reaction_on(self, fo, s, h):
        """The reaction status `s` from hero h would set off on this enemy, and the status it meets."""
        if s not in ELEMENTS or not fo["st"].get(s) or fo.get("reacted") == self.s["fight"]["round"]:
            return None, None
        by = fo.get("st_by", {})
        for other in ELEMENTS:
            kind = REACTIONS.get(frozenset((s, other)))
            if kind and other != s and fo["st"].get(other) and by.get(other) not in (None, h):
                return kind, other
        return None, None

    def react_elements(self, fo, kind, h):
        """An elemental reaction on this enemy, set off by hero h. Once per enemy a round."""
        f = self.s["fight"]
        fo["reacted"] = f["round"]
        st = fo["st"]
        up = self.mods(h).get("combo_up", 0)
        burn, poison, shock = st.get("burn", 0), st.get("poison", 0), st.get("shock", 0)
        others = [o for o in self.foes() if o is not fo]
        for s in next(k for k, v in REACTIONS.items() if v == kind):
            st.pop(s, None)  # both statuses are used up
        n = 0
        if kind == "overload":
            n = REACT_OVERLOAD + REACT_OVERLOAD_EACH * (burn + shock) + up
        elif kind == "thermal":
            n = REACT_THERMAL + REACT_THERMAL_EACH * burn + up
            st.pop("armor", None)
            st["vuln"] = max(st.get("vuln", 0), 2)
        elif kind == "blightfire":
            n = REACT_BLIGHT * (burn + poison) + up
        elif kind == "fracture":
            n = REACT_FRACTURE + REACT_FRACTURE_EACH * shock + up
            st["weak"] = max(st.get("weak", 0), 2)
        elif kind == "conduction":
            st["poison"] = 2 * poison + up
        elif kind == "frostlock":
            if self.boss_like(fo) or fo.get("locked"):
                n = FROSTLOCK_BOSS + up  # a boss (or one locked before) takes the cold instead
            elif not self.resist(fo):
                fo["locked"] = True
                st["stun"] = 1
        elif kind == "kindling":
            st["burn"] = min(REACT_KINDLE_CAP, burn * REACT_KINDLE) + up
        self.fx("combo", to=f"f{fo['id']}", c=kind, n=n)
        self.say(f"{self.static_combo(kind)} on {fo['name']}!")
        if n:
            self.hurt_foe(fo, n, h, pure=True, pierce=kind in ("thermal", "fracture"))
        for o in others:
            if o["hp"] <= 0:
                continue
            if kind == "overload" and n:
                self.hurt_foe(o, n // 2, h, pure=True)
            elif kind == "blightfire" and poison // 2:
                o["st"]["poison"] = max(o["st"].get("poison", 0), poison // 2)
                self.fx("st", to=f"f{o['id']}", s="poison")
            elif kind == "conduction" and poison // 2:
                o["st"]["poison"] = o["st"].get("poison", 0) + poison // 2
                self.fx("st", to=f"f{o['id']}", s="poison")

    @staticmethod
    def static_combo(kind):
        from .classes import COMBOS
        return COMBOS[kind]["name"]

    def reaction_worth(self, fo, s, h):
        """About what a reaction status `s` from hero h would set off is worth (for the bots)."""
        kind, _ = self.reaction_on(fo, s, h)
        if not kind:
            return 0
        st = fo["st"]
        burn, poison, shock = st.get("burn", 0), st.get("poison", 0), st.get("shock", 0)
        others = len([o for o in self.foes() if o is not fo])
        return {"overload": (REACT_OVERLOAD + REACT_OVERLOAD_EACH * (burn + shock)) * (1 + others / 2),
                "thermal": REACT_THERMAL + REACT_THERMAL_EACH * burn + 6,
                "blightfire": REACT_BLIGHT * (burn + poison) + poison * others,
                "fracture": REACT_FRACTURE + REACT_FRACTURE_EACH * shock + 4,
                "conduction": poison * (2 + others),
                "frostlock": FROSTLOCK_BOSS if self.boss_like(fo) or fo.get("locked") else 14,
                "kindling": 2 * burn * (REACT_KINDLE - 1)}[kind]

    # ---------------------------------------------------------------- Break
    # A boss's big move (`brk` on the move: the share of its health) shows a Break bar. Enough damage
    # from at least two heroes before it acts stops the move.
    def break_left(self, fo, h=None):
        """The damage still needed to break this enemy's move (None if it can't be broken now). With h,
        None too if hero h's hit couldn't be the one that breaks it (it'd still be one hero)."""
        it = fo.get("intent") or {}
        if not it.get("brk") or it.get("broken") or self.steeled(fo):
            return None
        if h is not None and not [y for y in fo.get("brk_by", []) if y != h]:
            return None
        return max(0, it["brk"] - fo.get("brk_d", 0))

    def break_hit(self, fo, n, h):
        """A hero's hit on an enemy with a breakable move: count it, and break the move if it's enough."""
        it = fo.get("intent") or {}
        if not it.get("brk") or it.get("broken") or h is None or n <= 0 or self.steeled(fo):
            return
        fo["brk_d"] = fo.get("brk_d", 0) + n
        if h not in fo.setdefault("brk_by", []):
            fo["brk_by"].append(h)
        if fo["brk_d"] >= it["brk"] and len(fo["brk_by"]) >= 2:
            fo["intent"] = {"k": "dazed", "name": f"Broken: no {it['name']}", "broken": True}
            fo.pop("next", None)
            self.lost_action(fo)
            self.fx("combo", to=f"f{fo['id']}", c="break", n=0)
            self.say(f"{fo['name']}'s {it['name']} is broken!")

    # ---------------------------------------------------------------- the Bell-Warden's bell
    def bell_parts(self, h, t):
        """For the bots: the bell number a hit on t could crack (or None), and the Chord on t: (the
        numbers it needs, its bonus) or None."""
        bell = t["bell"] if t.get("bell") and not t.get("cracked") else None
        bonus, _ = self.chord_for(h, f"f{t['id']}", list(range(1, 21)))
        chord = (set(self.s["fight"]["chord"]["vals"]), bonus) if bonus else None
        return chord, bell

    @staticmethod
    def bell_sum(parts, vals):
        chord, bell = parts
        n = 0
        if chord is not None and any(v in chord[0] for v in vals):
            n += chord[1]
        if bell is not None and bell in vals:
            n += BELL_CRACK
        return n

    def bell_crack(self, h, dice, t, used):
        """The Bell-Warden: a hit with a die showing its bell number cracks it."""
        if "bell" in used or not t.get("bell") or t.get("cracked") or t["bell"] not in [num(d) for d in dice]:
            return 0
        used.add("bell")
        t["cracked"] = True
        t["st"]["weak"] = max(t["st"].get("weak", 0), 1)
        self.say("The bell cracks! The Bell-Warden reels: its next attack is Weak.")
        self.fx("combo", to=f"f{t['id']}", c="bell", n=BELL_CRACK)
        return BELL_CRACK

    def spite(self, a):
        """Spiteful elites gain might when a hero buffs, heals or shields."""
        if a.get("def") or a.get("instant") or a["tgt"] in ("ally", "other", "party"):
            for fo in self.foes():
                if fo.get("aff") == "spiteful":
                    fo["might"] += 1
                    self.fx("st", to=f"f{fo['id']}", s="spite")
