"""Bosses and enemies with rules of their own: the Drowned Crown's phases and Undertow, the
Bell-Warden's bell and Death Knell, the Lamp Keeper's lamp and Lighthouse Beam, the Gallows Admiral's
powder kegs, the Iron Bosun's crew, thieving Harpies, splitting enemies and the Reef Maw's swallow.
Mixed into `Game` through `Combat`."""

from .content import archipelago as A
from .tuning import KEG_BLAST, KNELL_EVERY, KNELL_REQUIEM, LAMP_DOUSE, TICKING, UNDERTOW


class Bosses:
    # ---- Steeled: no boss or big threat can be shut down two rounds running. One that loses an
    # action (Stunned, its turn cancelled, distracted at nobody, robbed of every die) is Steeled for
    # the next round: Stuns and cancels don't take, and it always acts.
    def boss_like(self, fo):
        d = A.FOES[fo["k"]]
        return bool(d.get("boss") or d.get("big") or d.get("final"))

    def steeled(self, fo):
        return self.boss_like(fo) and fo.get("steel", 0) >= self.s["fight"]["round"]

    def resist(self, fo):
        """A Steeled enemy shrugs off a Stun or a lost turn: True if it resisted."""
        if self.steeled(fo):
            self.fx("st", to=f"f{fo['id']}", s="steeled")
            return True
        return False

    def lost_action(self, fo):
        """A boss-like enemy just lost its action: Steel it for the next round."""
        if self.boss_like(fo):
            fo["steel"] = self.s["fight"]["round"] + 1
            fo["st"]["steeled"] = 1

    def crown_warded(self, fo):
        """The Drowned Crown behind its Tide Guards, or a bloodied boss with a `ward` rule behind its `by`."""
        d = A.FOES[fo["k"]]
        if d.get("final"):
            return any(o is not fo and o["k"] == "tide_guard" for o in self.foes())
        b = d.get("bloodied") or {}
        return bool(fo.get("bl")) and b.get("rule") == "ward" and any(o is not fo and o["k"] == b["by"] for o in self.foes())

    def bloodied_rule(self, fo):
        """The generic bloodied rules (see content/biomes.py), each round from the one after it's bloodied:
        a new enemy (`summon`), sharper thorns (`thorns` with `grow`), a status on heroes every few rounds
        (`curse`), a blow marked on a hero to land at the round's end (`fall`), the `ward`'s status."""
        b = A.FOES[fo["k"]].get("bloodied") or {}
        rule = b.get("rule")
        f = self.s["fight"]
        if rule == "summon" and len(self.foes()) < 5:
            new = self.add_foe(b["f"])
            new["intent"] = {"k": "dazed", "name": "Just arrived"}
            self.fx("summon", f=new["id"])
        elif rule == "thorns" and b.get("grow"):
            fo["thorns_x"] = min(fo.get("thorns_x", b["n"]) + b["grow"], b["n"] + 6)
            fo["st"]["thorns"] = fo["thorns_x"]
        elif rule == "curse" and (f["round"] - fo.get("bl_round", f["round"])) % b.get("every", 1) == 0:
            heroes = self.actives()
            if b.get("tgt") == "strongest" and heroes:
                heroes = [max(heroes, key=lambda y: self.hero(y)["hp"])]
            elif b.get("tgt") == "random" and heroes:
                heroes = [self.rng.choice(heroes)]
            for y in heroes:
                self.hero_status(y, b["st"], 0 if b["st"] in TICKING else 1)
        elif rule == "fall" and self.actives():
            y = self.rng.choice(self.actives())
            self.hs(y)["st"]["falling"] = max(1, round(b["n"] * f["dmul"]))
            self.hs(y)["fall_by"] = fo["k"]
            self.fx("st", to=f"h{y}", s="falling")
        elif rule == "ward":
            if self.crown_warded(fo):
                fo["st"]["warded"] = 1
            else:
                fo["st"].pop("warded", None)

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
            crown["force"] = "deluge"
            self.say("The sea pours over the peak: each round the Undertow drags someone under. Armor or a Guard stops it. "
                     "Next round the Deluge hits everyone.")
            self.fx("phase", n=2)
        elif f["phase"] == 2 and frac <= 0.33:
            f["phase"] = 3
            for fo in self.foes():
                if fo is not crown:
                    fo["hp"] = 0
                    self.fx("die", to=f"f{fo['id']}")
            crown["fury"] = True
            crown["force"] = "deluge"
            self.say("The Drowned Crown stands alone: exposed, and furious. Next round the Deluge hits everyone.")
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
                # the Death Knell counts down and tolls on the whole party (every other round, bloodied)
                every = KNELL_REQUIEM if fo.get("bl") else KNELL_EVERY
                fo["knell"] = min(fo.get("knell", every), every) - 1
                if fo["knell"] <= 0:
                    fo["force"] = "knell"
                    fo["knell"] = every
                    fo["st"].pop("knell", None)
                else:
                    fo["st"]["knell"] = fo["knell"]
            if fo["k"] == "lamp_keeper":
                fo["lit"] = f["round"] > fo.get("dark_until", 0)
            if not self.steeled(fo):
                fo["st"].pop("steeled", None)
            rule = A.FOES[fo["k"]].get("bloodied", {}).get("rule") if fo.get("bl") else None
            if rule:
                self.bloodied_rule(fo)
            if rule == "kegs" and len(self.foes()) < 5 and not any(A.FOES[o["k"]].get("keg") for o in self.foes()):
                new = self.add_foe("powder_keg")
                self.fx("summon", f=new["id"])
                self.say(f"{fo['name']} rolls out a powder keg. Break it before it blows, and it blows up among his crew.")
            if rule == "allhands" and len(self.foes()) < 5:
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
        if fo.get("asleep") and h is not None:
            fo.pop("asleep")
            fo["st"].pop("asleep", None)
            self.fx("st", to=f"f{fo['id']}", s="wakes")
            self.say(f"{fo['name']} wakes up!")
        if h is not None and n > 0:
            fo.setdefault("hitr", [])
            if h not in fo["hitr"]:
                fo["hitr"].append(h)
        if fo["k"] == "lamp_keeper" and fo.get("lit", True) and len(fo.get("hitr", [])) >= min(LAMP_DOUSE, len(self.actives())):
            fo["lit"] = False
            # blazing (bloodied), it relights the next round
            fo["dark_until"] = f["round"] + (0 if fo.get("bl") else 1)
            fo["st"]["weak"] = max(fo["st"].get("weak", 0), 1)
            self.fx("st", to=f"f{fo['id']}", s="doused")
            self.say("The lamp goes out! In the dark the Lamp Keeper takes full damage, and its next attack is Weak.")
            if (fo.get("intent") or {}).get("m") == "gather":
                # doused while it gathers, the light scatters: no Lighthouse Beam next round
                fo["intent"] = {"k": "dazed", "name": "The light scatters"}
                fo.pop("next", None)
                fo.pop("charged", None)
                self.fx("st", to=f"f{fo['id']}", s="scattered")
                self.say("The gathered light scatters: no Lighthouse Beam.")
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

    def keg_broken(self, fo, h):
        """A hero broke a Powder Keg before it blew: it goes up among the enemies instead."""
        n = round(KEG_BLAST * self.diff()["foe_hp"])
        self.fx("st", to=f"f{fo['id']}", s="explodes")
        self.say(f"The keg goes up among the crew (−{n} each)!")
        for o in self.foes():
            if o is not fo:
                self.hurt_foe(o, n, h, pure=True)

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
        """At the end of a round: the Undertow lands (Armor blocks it; a Guard takes it), and so does
        anything a `fall` rule marked (falling magma, an avalanche), with its status."""
        for h in self.actives():
            n = self.hs(h)["st"].pop("undertow", 0)
            if n:
                self.fx("st", to=f"h{h}", s="dragged")
                self.hurt_hero(h, n, None)
            n = self.hs(h)["st"].pop("falling", 0)
            if n and self.active(h):
                b = A.FOES.get(self.hs(h).pop("fall_by", ""), {}).get("bloodied", {})
                self.fx("st", to=f"h{h}", s="crushed")
                before = self.hero(h)["hp"]
                self.hurt_hero(h, n, None)
                if b.get("st") and self.active(h) and self.hero(h)["hp"] < before:
                    self.hero_status(h, b["st"], 2 if b["st"] == "burn" else 1)
