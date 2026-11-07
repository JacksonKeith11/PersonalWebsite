"""Fights: dice, actions, enemy intents, statuses, summons and the end of a fight. Mixed into `Game`.

A round: every hero in the fight rolls their dice and every enemy shows its intent. The party
places dice on actions together, and each action happens the moment it's placed: its dice roll and
its effects land before anyone places another, so the party's actions go in the order they were
played (`f["done"]` lists them for the round). When everyone is ready, summons and pets act, then
enemies act in speed order, then end-of-round effects (Burn, Doom, Lifeline, statuses running out,
the heroes' Armor clearing). Enemy Armor clears when the enemies' turn starts instead, so Armor they
gain on their turn lasts through the heroes' next round.

Heroes are "h0".."h2", enemies "f<id>" and summons "s<id>" wherever the browser names a target.
"""

from . import classes as C
from .actions import Actions
from .bosses import Bosses
from .combos import Combos
from .content import archipelago as A
from .content import items as I
from .dice import Dice, face, is_pair, num, top_face
from .foes import Foes
from .crits import is_crit
from .actions import element_of
from .tuning import SWELL, ECHO_FACES, AIM_CAP
from .tuning import DUNGEON_STEP_DMG, DUNGEON_STEP_HP, ROLL_MODS, CURSED_DIE, ENRAGE_FROM, EVENT_DMG, EVENT_HP, ONE_SHOT, ROAM_DMG, ROAM_HP, ROUND_ONLY, TICKING


class Invalid(Exception):
    """An action that isn't allowed; the message is shown to the player."""


class Combat(Dice, Actions, Combos, Bosses, Foes):
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
            "path": spec.get("path"), "raid": spec.get("raid"), "win": spec.get("win"), "ev": spec.get("ev"),
            "by": spec.get("by"), "round": 0, "foes": [], "hs": {}, "done": [], "guard": {}, "taunt": None,
            "sanct": 0, "aegis": 0, "xp": 0, "gold": 0, "dmul": diff["foe_dmg"] * (1 + 0.1 * tier) * self.surge(),
            "spirit": {}, "nextfoe": 1, "phase": 1, "allies": [], "nextsum": 1, "acts": {}, "pain": {},
        }
        s["fid"] += 1
        s["fight"] = f
        s["phase"] = "fight"
        grow = 0
        roam = spec["kind"] in ("roam", "lair")
        if roam:
            f["dmul"] *= ROAM_DMG
        if spec["kind"] == "dungeon":
            # the objectives still standing grow with every one the party clears
            step = min(tier, len(DUNGEON_STEP_HP) - 1)
            f["dmul"] *= DUNGEON_STEP_DMG[step]
            f["hpmul"] = DUNGEON_STEP_HP[step]
        if spec["kind"] == "event":
            f["dmul"] *= EVENT_DMG
            grow = EVENT_HP.get(len(spec["heroes"]), 1.0) - 1
        for k in spec["foes"]:
            key, hp, aff = (k["k"], k.get("hp"), k.get("aff")) if isinstance(k, dict) else (k, None, None)
            if roam and not aff and not A.FOES[key].get("big"):
                grow = ROAM_HP - 1
            elif roam:
                grow = 0
            boss = spec.get("boss_grow", 0) if A.FOES[key].get("boss") else 0
            self.add_foe(key, hp, grow + boss, aff)
        for h in f["heroes"]:
            m = self.mods(h)
            x = {"st": {}, "down": False, "fled": False,
                 "dice": [], "rr": max(0, 1 + m.get("reroll", 0)), "once": [], "round_once": [], "cds": {}, "echo": False,
                 "unbreak": False, "ward": m.get("stun_ward", 0), "ready": False}
            f["hs"][str(h)] = x
            if m.get("start_armor"):
                x["st"]["armor"] = m["start_armor"]
            if m.get("evasive"):
                x["st"]["halfhit"] = 1  # Evasive: the first hit deals half
            if C.map_key(self.hero(h)) == "light_fingers":
                x["trinkets"] = list(self.hero(h).pop("stash", []))[:1] if m.get("stash") else []
            if m.get("bark"):
                self.summon(h, "sapling", 10)
        for h in f["heroes"]:
            hero = self.hero(h)
            m = self.mods(h)
            if C.map_key(hero) == "farsight":
                f["hs"][str(h)].update(attune="fire", flux=0)  # the Arcanist starts each fight attuned to Fire
            if not m.get("blessed_rest"):
                hero["grace"] = 0  # Grace starts over each fight (Blessed Rest: it carries)
            f["hs"][str(h)]["grace"] = hero.get("grace", 0)
            if m.get("thick_scales") and hero.get("scales", 0) < m["thick_scales"]:
                self.grow_scales(h, 1)  # Thick Hide
            if C.map_key(hero) == "meditation":
                # the Samurai: every fight starts Sheathed (Meditation: with Resolve after a rest)
                f["hs"][str(h)].update(sheathed=True, resolve=C.MEDITATION if hero.pop("meditated", False) else 0,
                                       rcap=self.resolve_cap(h))
            if C.map_key(hero) == "quick_draw":
                f["hs"][str(h)].update(ammo=self.cylinder(h), cap=self.cylinder(h), lucky=bool(m.get("lucky_chamber")))  # the Gunslinger's cylinder, full
            if C.map_key(hero) == "tracker":
                f["hs"][str(h)]["hawk"] = f"h{h}"  # the Ranger's hawk starts each fight watching it
            if C.map_key(hero) == "trailbreaker":
                f["hs"][str(h)]["impact"] = 0  # the Vanguard's Impact (Stored Force: last fight's, as Armor)
                kept = hero.pop("stored", 0)
                if kept and m.get("stored_force"):
                    st_ = f["hs"][str(h)]["st"]
                    st_["armor"] = st_.get("armor", 0) + kept
            if C.map_key(hero) == "banked_coals":
                # Banked Coals: Heat from the road, twice the turns since the last fight (up to 10)
                f["hs"][str(h)]["heat"] = min(10, 2 * max(0, self.s["turn"] - hero.get("fought", self.s["turn"])))
                hero["fought"] = self.s["turn"]
            if C.map_key(hero) == "runewright":
                # Runewright: every enemy starts with a Sigil, two after a rest
                n = 2 if hero.get("runes") else 1
                hero["runes"] = max(0, hero.get("runes", 0) - 1)
                for fo in f["foes"]:
                    fo["st"]["sigil"] = max(fo["st"].get("sigil", 0), n)
        if any(C.map_key(self.hero(h)) == "silver_tongue" for h in f["heroes"]):
            ov = 1 if any(self.mods(h).get("overture") for h in f["heroes"]) else 0
            f["harm"] = {"valor": ov, "aegis": ov, "discord": 0}  # the Herald's Harmonies (Overture: 1 each)
        if any(self.mods(h).get("open_weak") for h in f["heroes"]):
            for fo in f["foes"]:
                fo["st"]["weak"] = max(fo["st"].get("weak", 0), 1)
        self.apply_ground(spec.get("ground"))
        f["ambush"] = bool(spec.get("ambush_foes")) or (spec.get("by") in f["heroes"] and
                                                        C.map_key(self.hero(spec["by"])) == "ambush")
        names = ", ".join(fo["name"] for fo in f["foes"])
        self.say(f"Fight! {names}.")
        self.fx("fight", fk=f["kind"], tile=f["tile"])
        self.new_round()
        if self.s["fight"] is f and any(C.map_key(self.hero(y)) == "precognition" for y in f["heroes"]):
            self._op_foresee(None, {}, self.foes())  # Precognition: the first attacks rolled in the open
        for y in f["heroes"]:
            if self.s["fight"] is f and C.map_key(self.hero(y)) == "quick_draw" and self.active(y):
                self.quick_draw(y)

    def apply_ground(self, gr):
        """A battleground's rule (`A.GROUNDS`, chosen by `Game.ground_of`) at the start of a fight."""
        f = self.s["fight"]
        f["ground"] = gr
        if not gr:
            return
        G = A.GROUNDS[gr["k"]]
        if gr["k"] not in ("high", "woods"):
            self.apply_region_ground(gr, G)
            return
        if gr["k"] == "high" and gr["side"] == "heroes":
            for h in f["heroes"]:
                st = self.hs(h)["st"]
                st["armor"] = st.get("armor", 0) + G["armor"]
        elif gr["k"] == "high":
            for fo in f["foes"]:
                fo["st"]["armor"] = fo["st"].get("armor", 0) + max(3, round(fo["max"] * G["foe_armor"]))
        elif gr["side"] == "heroes":
            for fo in f["foes"]:
                fo["st"]["weak"] = max(fo["st"].get("weak", 0), 1)
        else:
            for h in f["heroes"]:
                st = self.hs(h)["st"]
                st["weak"] = max(st.get("weak", 0), 1)
        who = {("high", "heroes"): "the party holds the slope", ("high", "foes"): "the enemies hold the slope",
               ("woods", "heroes"): "the enemies are caught in the trees", ("woods", "foes"): "the party is caught in the trees"}
        self.say(f"{G['name']}: {who[(gr['k'], gr['side'])]}.")

    def apply_region_ground(self, gr, G):
        """The other regions' battlegrounds (`A.GROUNDS`): what each does as the fight starts. `side` is
        who it helps; "both" for the ones that hit everyone alike (Hallowed ground heals each round, in
        `round_upkeep`; Resonance's +2 is in `dmg_bonus` and the enemies' might)."""
        f = self.s["fight"]
        k, side = gr["k"], gr["side"]
        heroes = [h for h in f["heroes"]]
        if k == "embers":
            for h in heroes:
                self.hero_status(h, "burn", G["burn"])
            for fo in f["foes"]:
                fo["st"]["burn"] = fo["st"].get("burn", 0) + G["burn"]
            text = "the ground smoulders under everyone"
        elif k == "statues":
            for fo in f["foes"]:
                if not A.FOES[fo["k"]].get("boss") and not A.FOES[fo["k"]].get("big"):
                    fo["asleep"] = True
                    fo["st"]["asleep"] = 1
            text = "the enemies stand half turned to stone, asleep"
        elif k == "resonance":
            for fo in f["foes"]:
                fo["might"] += G["might"]
            text = "the crystals ring: every hit deals 2 more"
        elif k == "hallowed":
            text = "grace lies on the meadow: everyone heals each round"
        else:
            # whoever walked in suffers it: the heroes when it helps the enemies, else the enemies
            hurt_heroes = side == "foes"
            if hurt_heroes:
                st = {"sinking": "root", "lulled": "hex", "snowdrift": "freeze"}[k]
                for h in heroes:
                    self.hero_status(h, st, 0 if st in TICKING else 1)
            else:
                st = {"sinking": "root", "lulled": "weak", "snowdrift": "root"}[k]
                for fo in f["foes"]:
                    fo["st"][st] = max(fo["st"].get(st, 0), 1)
            text = f"{'the party' if hurt_heroes else 'the enemies'} walked into it"
        self.say(f"{G['name']}: {text}.")

    def add_foe(self, key, hp=None, grow=0.0, aff=None):
        f = self.s["fight"]
        d = A.FOES[key]
        mult = self.diff()["foe_hp"] * (1 + 0.15 * self.tier()) * (1 + grow) * self.surge() * f.get("hpmul", 1)
        mx = max(1, round(d["hp"] * mult))
        fo = {"id": f["nextfoe"], "k": key, "name": d["name"], "hp": mx, "max": mx, "row": d["row"],
              "st": {}, "intent": None, "seq": 0, "might": 0}
        self.foe_setup(fo, aff)
        if hp:
            fo["hp"] = min(hp, fo["max"])
        f["nextfoe"] += 1
        f["foes"].append(fo)
        return fo

    def summon(self, h, kind, hp=None):
        f = self.s["fight"]
        d = C.SUMMONS[kind]
        m = self.mods(h)
        cap = C.SUMMON_CAP + m.get("summon_cap", 0)
        mine = [a for a in self.allies() if a["owner"] == h]
        replaced = []
        while len(mine) >= cap:
            old = mine.pop(0)
            old["hp"] = 0
            replaced.append(f"s{old['id']}")
            self.fx("die", to=f"s{old['id']}")
        mx = max(1, round((hp or d["hp"]) * (1 + m.get("summon_hp", 0))))
        a = {"id": f["nextsum"], "k": kind, "name": d["name"], "hp": mx, "max": mx, "row": d["row"], "atk": d["atk"],
             "all": d.get("all", False), "owner": h, "st": {}}
        f["nextsum"] += 1
        f["allies"].append(a)
        self.fx("summon", s=a["id"])
        me = f"s{a['id']}"
        # A summon that replaces an older one takes over the attacks aimed at it...
        for fo in self.foes():
            it = fo.get("intent") or {}
            if it.get("k") != "attack":
                continue
            if it.get("tgt") in replaced:
                it["tgt"] = me
                self.fx("retarget", f=fo["id"], to=me)
            elif any(t in replaced for t in it.get("tgts") or []):
                it["tgts"] = [me if t in replaced else t for t in it["tgts"]]
                self.fx("retarget", f=fo["id"], to=me)
        # ...and every new summon draws one attack this round, so it protects someone at once.
        pull = self.summon_pull(h)
        if pull:
            fo, i = pull
            it = fo["intent"]
            if i is None:
                it["tgt"] = me
            else:
                it["tgts"][i] = me
            self.fx("retarget", f=fo["id"], to=me)
        return a

    def summon_pull(self, h):
        """The attack a summon called by hero `h` now would draw onto itself: the first enemy (in the
        order they act) with a single-target attack aimed at a hero, one aimed at `h` first. Returns
        (enemy, index into `tgts`, or None for `tgt`), or None. The bots use it to value summoning."""
        f = self.s["fight"]
        if f["taunt"] is not None and self.active(f["taunt"]):
            return None  # a Taunt takes every attack whatever it was aimed at
        order = sorted(self.foes(), key=lambda fo: -A.FOES[fo["k"]]["speed"])
        best = None
        for fo in order:
            it = fo.get("intent") or {}
            if it.get("k") != "attack":
                continue
            aims = [(None, it["tgt"])] if it.get("tgt") else list(enumerate(it.get("tgts") or []))
            for i, t in aims:
                if not (t and t.startswith("h")):
                    continue
                if t == f"h{h}":
                    return fo, i
                best = best or (fo, i)
        return best

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

    def in_reach(self, fo):
        """Whether melee reaches this enemy: the front row, or the Ranger's hawk's (Pinned Prey)."""
        return fo in self.front_foes() or any(self.hawk_foe(y) is fo and self.mods(y).get("pinned_prey") for y in self.actives())

    def hawk_foe(self, h):
        """The enemy this hero's hawk is hunting, or None."""
        u = self.hs(h).get("hawk") if self.in_fight(h) else None
        fo = self.foe(int(u[1:])) if u and u[0] == "f" else None
        return fo if fo and fo["hp"] > 0 else None

    def send_hawk(self, h, uid):
        """The Ranger's hawk goes to `uid` ("f<id>" to hunt, "h<n>" to watch)."""
        x, m = self.hs(h), self.mods(h)
        x["hawk"] = uid
        self.fx("st", to=uid, s="hawk_hunt" if uid[0] == "f" else "hawk_watch")
        if uid[0] == "h" and int(uid[1:]) != h and m.get("mantle"):
            st = self.hs(int(uid[1:]))["st"]
            st["armor"] = st.get("armor", 0) + m["mantle"]  # Mantle
            self.fx("armor", to=uid, n=m["mantle"])
        if uid[0] == "f" and m.get("eyes_sky"):
            self.foresee_foe(self.foe(int(uid[1:])))  # Eyes in the Sky

    def foresee_foe(self, fo, always_fx=False):
        """Roll an enemy's intent dice now, in the open (Spotter, Read Intent, Eyes in the Sky)."""
        it = fo.get("intent") or {}
        if not it.get("dice") or (not always_fx and all(d.get("v") is not None for d in it["dice"])):
            return
        for d in it["dice"]:
            if d.get("v") is None:
                d.pop("fc", None)
                d["v"], d["tag"] = self.foe_roll_face(d["faces"])
        self.intent_numbers(it)
        self.fx("st", to=f"f{fo['id']}", s="foreseen")

    def do_hawk(self, h, msg):
        """Send the Ranger's hawk to an enemy or a hero: once a round, while planning, no die."""
        if not self.in_fight(h) or not self.active(h) or "hawk" not in self.hs(h):
            raise Invalid("You have no hawk here.")
        x, f = self.hs(h), self.s["fight"]
        if x["ready"]:
            raise Invalid("You've readied up; unready to act again.")
        if x.get("hawk_r") == f["round"]:
            raise Invalid("Your hawk has already moved this round.")
        tgt = msg.get("tgt")
        if not isinstance(tgt, str) or len(tgt) < 2 or not tgt[1:].isdigit() or tgt[0] not in "fh":
            raise Invalid("Send it to whom?")
        if tgt[0] == "f" and not (self.foe(int(tgt[1:])) or {}).get("hp", 0) > 0:
            raise Invalid("Pick an enemy.")
        if tgt[0] == "h" and (int(tgt[1:]) not in f["heroes"] or not self.active(int(tgt[1:]))):
            raise Invalid("Pick someone standing.")
        if tgt == x["hawk"]:
            raise Invalid("It's already there.")
        x["hawk_r"] = f["round"]
        self.send_hawk(h, tgt)
        self.maybe_resolve()

    def mummy_hold(self):
        """Mummify: an enemy wrapped up can't heal past what it had, nor keep any Armor."""
        for fo in self.foes():
            if fo["st"].get("mummy"):
                fo["hp"] = min(fo["hp"], fo.get("mcap", fo["hp"]))
                fo["mcap"] = fo["hp"]
                fo["st"].pop("armor", None)

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
        # Battle Hymn: only while its Herald is above half HP
        return sum(self.mods(h).get("hymn_aura", 0) for h in self.actives() if self.hero(h)["hp"] * 2 > self.maxhp(h))

    # ------------------------------------------------------------------ rounds

    def new_round(self):
        """A round starts: upkeep (enrage, elite affixes, Poison, regeneration), then everyone's dice,
        the fallen's spirit dice, boss and enemy upkeep, and the enemies' intents."""
        f = self.s["fight"]
        pain = self.round_reset()
        self.round_upkeep()
        self.mummy_hold()
        if self.check_end():
            return
        f["hymn"] = 0
        anthem = [h for h in self.actives() if self.mods(h).get("anthem")]
        hive = any(self.mods(y).get("hive_mind") for y in self.actives())
        for h in f["heroes"]:
            x = self.hs(h)
            psion = C.map_key(self.hero(h)) == "precognition"
            base = (C.FOCUS_BASE + sum(1 for lv in C.FOCUS_LEVELS if self.s["level"] >= lv)
                    if psion else (1 if hive else 0))
            if psion and self.mods(h).get("hive_mind"):
                base = max(0, base - (len(self.actives()) - 1))  # Hive Mind: each ally takes one of yours
            x["focus"], x["focus_free"] = base + self.mods(h).get("overclock", 0), base  # the Psion's Focus (Hive Mind's)
            if "sheathed" in x:
                x["countered"] = False  # the Samurai's iai counter: once a round
                if x["sheathed"] and self.active(h):
                    self.add_resolve(h, C.RESOLVE_ROUND + self.mods(h).get("patient_blade", 0))
        for h in f["heroes"]:
            self.deal_dice(h, anthem, pain)
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
        for h in self.actives():
            # the Dragonborn's Scales (and Scales given by Brood Bond, and Draconic Ascension): Armor each round
            x = self.hs(h)
            n = (self.hero(h).get("scales", 0) if C.map_key(self.hero(h)) == "dragons_rest" else 0) \
                + x.get("brood", 0) + (3 if x.get("ascend") else 0) + (f.get("harm") or {}).get("aegis", 0)
            if n:
                x["st"]["armor"] = x["st"].get("armor", 0) + n
                self.fx("armor", to=f"h{h}", n=n)
        self.crown_round()
        self.foe_round()
        for fo in self.foes():
            self.choose_intent(fo)
        for h in self.actives():
            fo = self.hawk_foe(h)
            if fo and self.mods(h).get("eyes_sky"):
                self.foresee_foe(fo)  # Eyes in the Sky
        self.fx("round", n=f["round"])

    def round_reset(self):
        """Clear last round's bookkeeping; returns the Pain Engine bonuses it earned."""
        f = self.s["fight"]
        f["round"] += 1
        f["done"] = []
        f["rec"] = None
        f["guard"] = {}
        f["chord"] = None
        f["cloaked"] = []
        f["taunt"] = None
        f["sanct"] = 0
        f["acts"] = {}
        pain, f["pain"] = f["pain"], {}
        return pain

    def round_upkeep(self):
        """Enrage, elite affixes, Crown of Thorns, Poison, regeneration, Last Stand."""
        f = self.s["fight"]
        # No endless stalemates: from round 11 the enemies grow stronger every round.
        if f["round"] > ENRAGE_FROM:
            for fo in self.foes():
                fo["might"] += 2
            if f["round"] == ENRAGE_FROM + 1:
                self.say("The enemies grow desperate: they hit harder every round now.")
        for fo in self.foes():
            if fo.get("aff") == "ironclad":
                fo["st"]["armor"] = fo["st"].get("armor", 0) + 4
                self.fx("armor", to=f"f{fo['id']}", n=4)
            d = A.FOES[fo["k"]]
            if d.get("armor_round"):
                fo["st"]["armor"] = fo["st"].get("armor", 0) + d["armor_round"]
                self.fx("armor", to=f"f{fo['id']}", n=d["armor_round"])
            heal = d.get("regen", 0) + (A.FOES[fo["k"]]["bloodied"].get("n", 0) if fo.get("bl") and d.get("bloodied", {}).get("rule") == "regen" else 0)
            if heal and fo["hp"] < fo["max"] and f["round"] > 1:
                got = min(heal, fo["max"] - fo["hp"])
                fo["hp"] += got
                self.fx("heal", to=f"f{fo['id']}", n=got)
            if d.get("aura_heal") and f["round"] > 1:
                for o in self.foes():
                    if o is not fo and o["hp"] < o["max"]:
                        got = min(d["aura_heal"], o["max"] - o["hp"])
                        o["hp"] += got
                        self.fx("heal", to=f"f{o['id']}", n=got)
            if fo.get("aff") == "warlord" and f["round"] > 1:
                for o in self.foes():
                    if o is not fo:
                        o["might"] += 1
                self.fx("st", to=f"f{fo['id']}", s="rallies")
        if (f.get("ground") or {}).get("k") == "hallowed" and f["round"] > 1:
            n = A.GROUNDS["hallowed"]["heal"]
            for h in self.actives():
                self.fight_heal(h, n, None)
            for fo in self.foes():
                got = min(n, fo["max"] - fo["hp"])
                if got > 0:
                    fo["hp"] += got
                    self.fx("heal", to=f"f{fo['id']}", n=got)
        thorns = sum(self.mods(h).get("crown_thorns", 0) for h in self.actives())
        for fo in self.foes():
            if thorns:
                self.hurt_foe(fo, thorns, None, pure=True)
            if fo["hp"] > 0 and fo["st"].get("poison"):
                self.hurt_foe(fo, fo["st"]["poison"], None, pure=True)
        for h in self.actives():
            st = self.hs(h)["st"]
            if st.get("poison"):
                self.hurt_hero(h, st["poison"], None, pure=True)
            if not self.active(h):
                continue
            m = self.mods(h)
            if m.get("regen"):
                self.fight_heal(h, m["regen"], None)
            if m.get("last_stand") and self.hero(h)["hp"] <= self.maxhp(h) // 2:
                st["armor"] = st.get("armor", 0) + m["last_stand"]
        sregen = sum(self.mods(h).get("summon_regen", 0) for h in self.actives())
        if sregen:
            for a in self.allies():
                got = min(sregen, a["max"] - a["hp"])
                a["hp"] += got
                if got:
                    self.fx("heal", to=f"s{a['id']}", n=got)

    def deal_dice(self, h, anthem, pain):
        """A hero's dice for the round. Most stay hidden until their action resolves; Seer dice are
        rolled now and shown, Augur dice show only high or low, Fate dice show two faces. Then
        whatever enemies did to their dice last round (Hex, Freeze, theft, Barnacle Crust, static)."""
        f = self.s["fight"]
        x = self.hs(h)
        x["ready"] = False
        if self.mods(h).get("hoard") and x["dice"]:
            # Slack Water: the biggest die left unused carries over
            left = [d for d in x["dice"] if not d["used"] and d["src"] not in ("hoard", "gift", "hex")]
            if left:
                big = max(left, key=lambda d: top_face(d["faces"]))
                x["hoard"] = {"faces": big["faces"], "src": "hoard",
                              "dk": [k for k in big["dk"] if k not in ("seer", "augur", "fate", "top") and not k.startswith("link:")]}
        if self.mods(h).get("swell_die"):
            old = next((d for d in x["dice"] if d.get("src") == "swell"), None)
            if old is not None:
                x["swell"] = 0 if old["used"] else min(x.get("swell", 0) + 1, len(SWELL) - 1)
        x["dice"] = []
        x["round_once"] = []
        if x.get("dealt") and "shoot" not in x.get("cds", {}) and "shoot" in self.actions_of(h):
            x["aim"] = min(AIM_CAP, x.get("aim", 0) + 1)  # Aim and Loose: a round waited ready and unused
        x["dealt"] = True
        if self.mods(h).get("echo_round"):
            x["echo"] = False  # the Abyssal Tome: the echo comes back every round
        x["cds"] = {k: n - 1 for k, n in x.get("cds", {}).items() if n > 1}
        x["links"] = {}
        x["tempo"] = False
        x["kdie"] = False
        x["inspire"] = x.pop("carry", 0)  # Clean Bill's bonus, earned after their dice were spent
        x.pop("spells", None)
        x.pop("spellcue", None)  # Kindle lasts the round
        x.pop("cued", None)
        x["pain_bonus"] = pain.get(str(h), 0)
        x["soaked"] = False
        if not self.active(h):
            return
        if x.get("swallowed"):
            self.fx("st", to=f"h{h}", s="swallowed")
            self.hurt_hero(h, max(2, round(f["dmul"] * 1.5)), None, pure=True)
            return
        if x["st"].pop("stun", 0):
            if x["ward"] > 0:
                x["ward"] -= 1
            else:
                self.fx("st", to=f"h{h}", s="stunned")
                return
        m = self.mods(h)
        for i, d in enumerate(self.round_dice(h, x, m, anthem)):
            inst = {"id": f"{h}.{f['round']}.{i}", "faces": d["faces"], "dk": d["dk"], "src": d["src"], "used": False,
                    "v": None, "bonus": d.get("bonus", 0), "top": "top" in d["dk"]}
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
        self.dice_attacks(h, x, m)

    def round_dice(self, h, x, m, anthem):
        """The dice a hero rolls this round: gear and class dice, then pets, Anthem, Slack Water."""
        dice = [dict(d, faces=list(d["faces"]), dk=list(d["dk"])) for d in self.dice_of(h)]
        self.dice_picks(dice, m)
        if m.get("swell_die"):
            size, bonus = SWELL[x.get("swell", 0)]
            dice.append({"faces": list(range(1, size + 1)), "dk": ["swell"], "src": "swell", "bonus": bonus})
        if m.get("echo_die"):
            dice.append({"faces": list(range(1, ECHO_FACES + 1)), "dk": ["echo"], "src": "echo"})
        if m.get("pet"):
            dice.append({"faces": list(range(1, min(8, m["pet"]) + 1)), "dk": [], "src": "pet"})
        if any(y != h for y in anthem):
            dice.append({"faces": [1, 2, 3, 4], "dk": [], "src": "anthem"})
        if x.get("hoard"):
            dice.append(x.pop("hoard"))
        if x.get("berserk"):  # berserk: every die explodes
            for d in dice:
                if "exploding" not in d["dk"]:
                    d["dk"] = list(d["dk"]) + ["exploding"]
        if m.get("bellows") and x.get("heat", 0) >= 10:  # Bellows: the weapon die explodes while hot
            for d in dice:
                if d.get("src") == "weapon" and "exploding" not in d["dk"]:
                    d["dk"] = list(d["dk"]) + ["exploding"]
        if m.get("all_explode"):
            dice = [dict(d, dk=list(d["dk"]) + (["exploding"] if "exploding" not in d["dk"] else [])) for d in dice]
        if C.map_key(self.hero(h)) == "precognition":
            for d in dice:  # the Psion sees all its dice
                if "seer" not in d["dk"]:
                    d["dk"] = list(d["dk"]) + ["seer"]
        elif dice and any(self.mods(y).get("shared_vision") for y in self.actives() if y != h):
            big = max(dice, key=lambda d: top_face(d["faces"]))  # Shared Vision
            if "seer" not in big["dk"]:
                big["dk"] = list(big["dk"]) + ["seer"]
        if m.get("deadeye") and dice:
            big = max(dice, key=lambda d: top_face(d["faces"]))
            big["dk"] = list(big["dk"]) + ["seer", "top"]
        return dice

    @staticmethod
    def dice_picks(dice, m):
        """Level-up picks that change a hero's dice for the fight (each a mod in mods.py)."""
        def lows(d, n=2):
            # the indices of a die's n lowest number faces
            return sorted((i for i, f in enumerate(d["faces"]) if isinstance(f, int)), key=lambda i: d["faces"][i])[:n]

        def by_src(src):
            return [d for d in dice if d["src"] == src]
        if m.get("shield_rim"):  # Shield Rim: the armor die's two lowest faces become shield faces
            for d in by_src("armor"):
                for i in lows(d):
                    d["faces"][i] = "S"
        if m.get("wild_low") and dice:  # Wild Surge: the biggest die's two lowest faces are wild
            d = max(dice, key=lambda d: top_face(d["faces"]))
            for i in lows(d):
                d["faces"][i] = "W"
        if m.get("steady_all"):  # Steady Hands: every die is Steady
            for d in dice:
                if "steady" not in d["dk"]:
                    d["dk"].append("steady")
        if m.get("fate_weapon"):  # Fated Blade: the weapon die is a Fate die
            for d in by_src("weapon"):
                if "fate" not in d["dk"]:
                    d["dk"].append("fate")
        if m.get("seer_augur"):  # Hawk's Eye: an Augur die is a Seer die
            for d in dice:
                if "augur" in d["dk"]:
                    d["dk"] = ["seer" if k == "augur" else k for k in d["dk"]]
        if m.get("wild_link"):  # Loaded Bones: linked dice's 1s and 2s are wild
            for d in dice:
                if any(k.startswith("link:") for k in d["dk"]):
                    d["faces"] = ["W" if f in (1, 2) else f for f in d["faces"]]
        if m.get("catalyst"):  # Catalyst: the weapon die's two lowest numbers burn and poison
            for d in by_src("weapon"):
                nums = sorted((i for i, f in enumerate(d["faces"]) if isinstance(f, int)), key=lambda i: d["faces"][i])
                for i, tag in zip(nums[:2], "FP"):
                    d["faces"][i] = f"{tag}{d['faces'][i]}"
        if m.get("rune_face"):  # Rune-Etched Blade: the weapon die's lowest face is a rune (wild, and it carves)
            for d in by_src("weapon"):
                for i in lows(d, 1):
                    d["faces"][i] = "W"
        if m.get("explosive_weapon"):  # Powder Edge: the weapon die explodes
            for d in by_src("weapon"):
                if "exploding" not in d["dk"]:
                    d["dk"].append("exploding")

    def echo_out(self, h, dice):
        """An ally's play sets every other hero's unused Echo die to its biggest number."""
        vals = [d["v"] for d in dice if isinstance(d.get("v"), int) and d.get("tag") not in ("S", "X")]
        if not vals or not self.s.get("fight"):
            return
        v = max(vals)
        for y in self.s["fight"]["heroes"]:
            if y == h or not self.active(y):
                continue
            for d in self.hs(y)["dice"]:
                if "echo" in d["dk"] and not d["used"]:
                    self.show_die(d, v, None)
                    self.fx("st", to=f"h{y}", s="echo")

    def dice_attacks(self, h, x, m):
        """What enemies did to a hero's dice: Hex swaps the biggest for a cursed one, Freeze takes
        the smallest, thieves take the biggest, Barnacle Crust locks it, static shocks low rolls.
        Then Diagnosis shows the smallest."""
        pool = [d for d in x["dice"] if d["src"] != "swell"]
        if x["st"].pop("hex", 0) and pool:
            big = max(pool, key=lambda d: top_face(d["faces"]))
            big.update(faces=list(CURSED_DIE), dk=[], src="hex", v=None, top=False)
            for k2 in ("link", "sv", "stag", "hint", "fc", "tag"):
                big.pop(k2, None)
            self.fx("st", to=f"h{h}", s="hexed")
        if x["st"].pop("freeze", 0) and not m.get("freeze_immune") and x["dice"]:
            x["dice"].remove(min(x["dice"], key=num))
        pool = [d for d in x["dice"] if d["src"] != "swell"]  # Freeze may have taken one of them
        if x["st"].pop("steal", 0) and pool:
            x["dice"].remove(max(pool, key=lambda d: top_face(d["faces"])))
            self.fx("st", to=f"h{h}", s="robbed")
        pool = [d for d in x["dice"] if d["src"] != "swell"]
        if x["st"].pop("lock", 0) and pool:
            big = max(pool, key=lambda d: top_face(d["faces"]))
            big["used"], big["locked"] = True, True
            self.fx("st", to=f"h{h}", s="locked")
        x["static"] = bool(x["st"].pop("static", 0))
        if m.get("seer_small"):
            hid = [d for d in x["dice"] if not d["used"] and d.get("v") is None and not d.get("fc")]
            if hid:
                d = min(hid, key=lambda d: top_face(d["faces"]))
                self.show_die(d, *self.raw_roll(h, d))


    def cooling(self, h, key):
        """Rounds until an action can be used again (0: ready)."""
        return self.hs(h)["cds"].get(key, 0)

    def count_ok(self, req, dice):
        n = req.get("n", 1)
        return 1 <= len(dice) <= n if req.get("upto") else len(dice) == n

    def resolve_target(self, h, a, tgt):
        """Check a target for an action; returns the target id (or None for untargeted)."""
        kind = a["tgt"]
        if kind == "foe":
            fo = self.foe(int(tgt[1:])) if isinstance(tgt, str) and tgt.startswith("f") and tgt[1:].isdigit() else None
            if not fo or fo["hp"] <= 0:
                raise Invalid("Pick an enemy.")
            if a.get("melee") and not self.in_reach(fo):
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
        if a.get("focus") and x.get("focus", 0) < a["focus"]:
            raise Invalid("Not enough Focus.")
        if a.get("shot") and x.get("ammo", 0) <= 0:
            raise Invalid("Your cylinder's empty: Reload, or Pistol Whip.")
        if a.get("stance") and "sheathed" in x and x["sheathed"] != (a["stance"] == "sheathed"):
            raise Invalid("Your blade is drawn: Cut, or Sheathe it first." if a["stance"] == "sheathed"
                          else "Your blade is sheathed: Draw it, or strike with the scabbard.")
        if x.get("berserk") and a["def"]:
            if not self.mods(h).get("cold_fury") or x.get("cold_used"):
                raise Invalid("You're berserk: no defending now.")
            x["cold_used"] = True  # Cold Fury: one a round
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
        if a["req"].get("sigils") and self.foe(int(tgt[1:]))["st"].get("sigil", 0) < a["req"]["sigils"]:
            raise Invalid(f"That enemy needs {a['req']['sigils']} Sigils on it.")
        if a.get("once") and a.get("instant"):
            x["once"].append(a["key"])
        if a.get("cd") and a.get("instant"):
            x["cds"][a["key"]] = a["cd"]
        if a.get("per_round"):
            x["round_once"].append(a["key"])
        if a.get("focus"):
            self.spend_focus(h, a["focus"])
        if a.get("instant"):
            self.instant(h, a, dice, tgt)
            self.echo_out(h, dice)
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

    def spend_focus(self, h, n):
        """Spend Focus; Overclock's extra Focus costs 1 HP each (never the last)."""
        x = self.hs(h)
        for _ in range(n):
            over = x["focus"] > x.get("focus_free", 0) and self.mods(h).get("overclock")
            x["focus"] -= 1
            hero = self.hero(h)
            if over and hero["hp"] > 1:  # it never knocks the Psion down (that would stall the round)
                hero["hp"] -= 1
                self.s["stats"][h]["taken"] += 1
                self.fx("dmg", to=f"h{h}", n=1, block=0)

    def do_nudge(self, h, msg):
        """The Psion's Focus: nudge a shown die up or down by 1 ("by"), or, by Mind Link, reveal an ally's
        hidden die ("of": the ally, "by": 0) and then nudge it. Perfect Foresight sets one ("set")."""
        if not self.in_fight(h) or not self.active(h):
            raise Invalid("You're not fighting.")
        x = self.hs(h)
        if x["ready"]:
            raise Invalid("You've readied up; unready to act again.")
        y = msg.get("of", h)
        if y != h and ("mind_link" not in self.hero(h)["skills"] or not isinstance(y, int) or not self.active(y)):
            raise Invalid("Only a Psion can reach an ally's dice.")
        d = next((d for d in self.hs(y)["dice"] if d["id"] == msg.get("die") and not d["used"]), None)
        if not d:
            raise Invalid("Pick an unused die.")
        nums = [face(f2)[0] for f2 in d["faces"] if face(f2)[0] is not None]
        lo, top = min(nums), top_face(d["faces"])
        if msg.get("set") is not None:
            v = msg["set"]
            if not self.mods(h).get("foresight") or x.get("foresaw") or y != h or d.get("v") is None:
                raise Invalid("You can't set that die.")
            if not isinstance(v, int) or v not in nums or d.get("tag") in ("S", "X", "W"):
                raise Invalid("Pick one of its numbers.")
            x["foresaw"] = True
            d["v"] = v
            self.fx("st", to=f"h{y}", s="foreseen_die")
            return
        by = msg.get("by", 0)
        if by not in (-1, 0, 1):
            raise Invalid("Nudge by one.")
        reveal = d.get("v") is None
        cost = (0 if reveal and y != h and self.mods(h).get("empathic") else int(reveal)) + abs(by)
        if not cost and not reveal:
            raise Invalid("Nudge it up or down.")
        if x.get("focus", 0) < cost:
            raise Invalid("Not enough Focus.")
        if by and not reveal and (d.get("tag") in ("S", "X", "W") or not lo <= d["v"] + by <= max(top, d["v"])):
            raise Invalid("That die can't go that way.")
        self.spend_focus(h, cost)
        if reveal:
            if "sv" in d:
                v, t = d.pop("sv"), d.pop("stag", None)
            elif d.get("fc"):
                v, t = self.rng.choice(d["fc"]), None
            else:
                v, t = self.raw_roll(y, d)
            self.show_die(d, v, t)
            d.pop("fc", None)
            self.fx("st", to=f"h{y}", s="revealed")
        if by and d.get("tag") not in ("S", "X", "W") and lo <= d["v"] + by <= max(top, d["v"]):
            d["v"] += by
            self.fx("st", to=f"h{y}", s="nudged")

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
        x["dice"].append({"id": f"s{h}.{f['round']}", "faces": [1, 2, 3, 4, 5, 6], "dk": [], "v": sp["v"], "src": "spirit", "used": False})
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
        u = self.item(key)["use"]
        if "heal" in u:
            hid = int(tgt[1:]) if isinstance(tgt, str) and tgt.startswith("h") and tgt[1:].isdigit() else h
            if not self.active(hid):
                raise Invalid("Use it on whom?")
            hero["bag"].pop(i)
            self.fight_heal(hid, int(u["heal"]), h)
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
        self.say(f"{hero['name']} uses {self.item(key)['name']}.")
        self.maybe_resolve()

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
        since = self.s["fxid"]
        self.chord_open(h, a, dice, tgt if isinstance(tgt, str) else None)
        hit = self.roll_for(h, a, dice)
        self.echo_out(h, dice)
        done = {"h": h, "a": a["key"], "plus": a["plus"], "tgt": tgt, "hit": hit}
        f["done"].append(done)
        self.fx("act", h=h, a=a["key"], tgt=tgt, hit=hit)
        ops = a["ops"] if hit else a.get("miss", [])
        m = self.mods(h)
        if not hit and a.get("spell") and m.get("miss_armor") and dice:
            # Backlash Ward: a spell that fizzles still throws up a shield
            n = sum(num(d) for d in dice)
            x["st"]["armor"] = x["st"].get("armor", 0) + n
            self.fx("armor", to=f"h{h}", n=n)
        x["acting"] = a["key"]
        if x.get("sheathed") and not a.get("stance") and a["tgt"] in ("foe", "foes", "front") \
                and any(o["op"] == "dmg" for o in ops):
            self.draw_blade(h)  # the Samurai swings something else (hit or miss): the blade comes out, the Resolve is lost
        # the Silver Round is settled before the shot lands: a crit's round back mustn't change it afterwards
        silver = bool(a.get("shot") == 1 and self.silver(h))
        if silver:
            self.fx("st", to=f"h{h}", s="silver_round")
        if m.get("frozen_bonus") and isinstance(tgt, str) and tgt.startswith("f") and any(d.get("tag") == "freeze" for d in dice):
            # a freeze face freezes before its own hit lands, so Frostbite counts on that hit too
            fo = self.foe(int(tgt[1:]))
            if fo and fo["hp"] > 0:
                fo["st"]["freeze"] = 1
        self.run_ops(h, a, dice, tgt, ops=ops, hit=hit)
        if hit and a.get("crit") and self.s["fight"] is f and any(is_crit(d) for d in dice):
            # a die on its top face: the action's crit lands too
            self.fx("st", to=f"h{h}", s="crit")
            self.run_ops(h, a, dice, tgt, ops=a["crit"], hit=hit)
            if "trinkets" in x and not x.get("crit_lift"):
                x["crit_lift"] = True  # the Scoundrel's Pickings: a crit lifts a trinket, once a round
                self.pilfer(h)
            if a["key"] == "claw" and m.get("wyrmfire") and isinstance(tgt, str) and tgt.startswith("f"):
                fo = self.foe(int(tgt[1:]))
                if fo:
                    self.foe_burn(fo, 2, h)  # Wyrmfire Claws: a crit Burns 3 in all
        x.pop("acting", None)
        if self.s["fight"] is f and hit and isinstance(tgt, str) and tgt.startswith("f"):
            fo = self.foe(int(tgt[1:]))
            if fo and a.get("bomb"):
                self.react(h, a, fo)  # the Alchemist's residues and reactions
            if fo and m.get("rune_face") and any(d.get("src") == "weapon" and d.get("tag") == "W" for d in dice):
                self.carve(fo, 1)  # Rune-Etched Blade: the rune face carves
            if a.get("spell") and m.get("spellstrike") and any(o["op"] == "dmg" for o in ops) and self.active(h):
                v = num(dice[0]) if dice else 0
                self.infuse(h, 1, m["spellstrike"], element_of(v))
        if self.s["fight"] is f and a.get("spell") and "attune" in x:
            self.attune_cast(h, a, tgt, dice, hit)  # the Arcanist's Attunement and Flux
        if self.s["fight"] is f and m.get("resonant_pair") and len(dice) >= 2 and is_pair([num(d) for d in dice], [d.get("tag") for d in dice]):
            x["focus"] = x.get("focus", 0) + m["resonant_pair"]  # Resonant Pair
            self.fx("st", to=f"h{h}", s="focus")
        if self.s["fight"] is f and "heat" in x and self.active(h):
            self.add_heat(h, self.dice_heat(h, a, dice))  # the Emberknight: every die stokes the fire
        if self.s["fight"] is f:
            self.after_action(h, a, tgt)
        self.elements(h, a, dice, tgt)
        if self.s["fight"] is f:
            self.chord_close(h, dice)
        if self.s["fight"] is f and a["tgt"] == "foe" and dice and isinstance(tgt, str) and tgt.startswith("f"):
            fo = self.foe(int(tgt[1:]))
            known = [d["v"] for d in ((fo or {}).get("intent") or {}).get("dice") or [] if d.get("v") is not None]
            if self.mods(h).get("tempo") and known and not x.get("tempo") and max(num(d) for d in dice) > max(known):
                x["tempo"] = True
                x["dice"].append(self.new_die(h, list(range(1, 7)), "tempo"))
                self.fx("st", to=f"h{h}", s="tempo")
        echo = (a.get("spell") and self.mods(h).get("spell_echo")) or (self.mods(h).get("echo_any") and a["key"] not in C.GENERIC)
        if echo and not x["echo"] and self.s["fight"] is f:
            x["echo"] = True
            self.fx("act", h=h, a=a["key"], tgt=tgt, echo=True)
            self.run_ops(h, a, dice, tgt, half=True, ops=ops, hit=hit)
        if a.get("shot") and self.s["fight"] is f:
            self.fire_rounds(h, a, tgt, dice, silver)
        if "sheathed" in x and self.s["fight"] is f and hit:
            self.blade_after(h, a, tgt)
        f["acts"][str(h)] = f["acts"].get(str(h), 0) + 1
        done["vals"] = [num(d) for d in dice]
        done["out"] = self.act_outcome(since)
        if self.s["fight"] is f:
            self.check_end()

    def blade_after(self, h, a, tgt):
        """The Samurai's picks that react to what just landed: Hilt and Sheath, Chiburi."""
        x = self.hs(h)
        m = self.mods(h)
        if a["key"] == "scabbard_strike" and m.get("hilt_sheath"):
            self.add_resolve(h, m["hilt_sheath"])  # Hilt and Sheath
        fo = self.target_foe(tgt)
        if a["key"] == "cut" and m.get("chiburi") and fo and fo["hp"] <= 0 and not x["sheathed"]:
            x["sheathed"] = True  # Chiburi: a Cut that kills sheathes the blade
            self.fx("st", to=f"h{h}", s="sheathed")

    def target_foe(self, tgt):
        """The enemy an action's target string names ("f3"), dead or alive, or None."""
        return self.foe(int(tgt[1:])) if isinstance(tgt, str) and tgt.startswith("f") and tgt[1:].isdigit() else None

    def draw_blade(self, h):
        x = self.hs(h)
        x["sheathed"], x["resolve"] = False, 0
        self.fx("st", to=f"h{h}", s="drawn")

    def iai_counter(self, h, fo):
        """The Samurai's iai counter: while Sheathed, the first enemy to hit it each round is cut for half its
        Resolve (Mirror Edge, Waiting Stance: all of it)."""
        x = self.hs(h)
        if not x.get("sheathed") or x.get("countered") or not x.get("resolve") or fo["hp"] <= 0 or self.hero(h)["hp"] <= 0:
            return  # a blow that knocks the Samurai down isn't countered (Final Breath is that cut)
        x["countered"] = True
        full = self.mods(h).get("mirror_edge") or x["st"].get("machi")
        self.fx("st", to=f"f{fo['id']}", s="iai")
        self.hurt_foe(fo, x["resolve"] if full else x["resolve"] // 2, h, pure=True)

    def quick_draw(self, h):
        """The Gunslinger's Quick Draw: when a fight starts, a free shot at the enemy with the biggest attack."""
        foes = self.foes()
        if not foes:
            return
        fo = max(foes, key=lambda o: ((o.get("intent") or {}).get("v", 0) if (o.get("intent") or {}).get("k") in ("attack", "all") else -1, o["hp"]))
        self.fx("st", to=f"f{fo['id']}", s="quick_draw")
        self.hurt_foe(fo, C.QUICK_DRAW, h)
        self.check_end()

    def fire_rounds(self, h, a, tgt, dice, silver):
        """A shot spends its rounds (after it lands, so `ammo` and `silver` in its amounts are the rounds
        before it), then the Silver Round's extras (Silver Bullets, Two Guns, Silver Lining) and Fresh
        Cartridge's round back on a kill. `silver`: whether it fired the Silver Round, settled before it
        landed (a crit's round back changes the count)."""
        x = self.hs(h)
        m = self.mods(h)
        have = x.get("ammo", 0)
        x["ammo"] = have - (have if a["shot"] == "all" else min(have, a["shot"]))
        x["st"].pop("cocked", None)
        fo = self.target_foe(tgt)
        if silver and fo and m.get("silver_bullets") and fo["hp"] > 0:
            fo["st"]["vuln"] = max(fo["st"].get("vuln", 0), 2)
            self.fx("st", to=f"f{fo['id']}", s="vuln")
        if silver and m.get("silver_twin"):
            others = [o for o in self.foes() if o is not fo]
            if others:  # Two Guns: the off-hand fires the Silver Round too
                self.hurt_foe(self.rng.choice(others), (num(dice[0]) if dice else 0) + m["silver_twin"], h)
        if silver and m.get("silver_lining"):
            y = min(self.actives(), key=lambda y: self.hero(y)["hp"] / self.maxhp(y))  # Silver Lining
            self.fight_heal(y, m["silver_lining"], h)
        if m.get("scavenge") and fo and fo["hp"] <= 0 and x["ammo"] < self.cylinder(h):
            x["ammo"] += 1  # Fresh Cartridge
            self.fx("st", to=f"h{h}", s="reloaded")

    def after_action(self, h, a, tgt):
        """Bookkeeping for the passives that care what was done: Spellweave, Reagents, Quarry,
        Call and Response (instants call it too)."""
        f = self.s["fight"]
        x = self.hs(h)
        if a.get("spell"):
            x.setdefault("spells", []).append(a["key"])
        if a.get("melee") or a.get("spell"):
            x["lastk"] = "melee" if a.get("melee") else "spell"  # for Bladesong
        if a.get("harmony") and f.get("harm") is not None:
            self.raise_harmony(h, a["harmony"], a.get("harmony_n", 1))
        if x.pop("combo_end", None):
            pass
        elif C.map_key(self.hero(h)) == "ambush" and isinstance(tgt, str) and tgt.startswith("f") \
                and any(o["op"] == "dmg" for o in a["ops"]):
            self.combo_hit(h, int(tgt[1:]))
        if a.get("bomb"):
            x["bombs"] = x.get("bombs", 0) + 1
        if a["key"] == "shoot":
            x["aim"] = 0  # Aim and Loose: loosed
        if a.get("spell") and a["key"] != "kindle" and any(o["op"] == "dmg" for o in a["ops"]):
            x.pop("spellcue", None)  # Kindle's bonus is spent on this spell
        if self.mods(h).get("quarry") and a["tgt"] == "foe" and isinstance(tgt, str) and tgt.startswith("f"):
            fid, r, q = int(tgt[1:]), f["round"], x.get("quarry")
            if q and q["id"] == fid and q["r"] == r - 1:
                x["quarry"] = {"id": fid, "r": r, "n": q["n"] + 1}
            elif not (q and q["id"] == fid and q["r"] == r):
                x["quarry"] = {"id": fid, "r": r, "n": 1}
        if x.get("apex_n") and any(o["op"] == "dmg" for o in a["ops"]):
            x.pop("apex_n")  # Apex Predator's +5 is spent on this hit
        if x.get("cued") and any(o["op"] == "dmg" for o in a["ops"]):
            x.pop("cued")
        cue = self.mods(h).get("cue")
        if cue:
            for y in self.actives():
                if y != h:
                    self.hs(y)["cued"] = cue

    def raise_harmony(self, h, which, n=1):
        """The Herald's songs raise a Harmony (Resonant Chord: the two lowest)."""
        f = self.s["fight"]
        harm = f["harm"]
        cap = C.HARMONY_CAP + (1 if any(self.mods(y).get("perfect_pitch") for y in f["heroes"]) else 0)
        keys = sorted(harm, key=lambda k: harm[k])[:2] if which == "chord" else [which]
        for k in keys:
            harm[k] = min(cap, harm[k] + n)
            self.fx("st", to="party", s="harm_" + k)
        self.hs(h)["lastharm"] = keys[-1]

    def pilfer(self, h, n=1):
        """The Scoundrel lifts trinkets from an enemy's pockets (up to its cap)."""
        x = self.hs(h)
        cap = C.TRINKET_CAP + self.mods(h).get("deep_sleeves", 0)
        for _ in range(n):
            if len(x["trinkets"]) >= cap:
                break
            k = self.rng.choice(sorted(C.TRINKETS))
            x["trinkets"].append({"k": k, "uses": 2 if self.mods(h).get("master_thief") else 1})
            self.fx("st", to=f"h{h}", s="lifted_" + k)

    def do_trinket(self, h, msg):
        """Use a trinket: no die, at any time while planning."""
        if not self.in_fight(h) or not self.active(h):
            raise Invalid("You're not fighting.")
        x = self.hs(h)
        if x["ready"]:
            raise Invalid("You've readied up; unready to act again.")
        i = msg.get("i")
        tr = x.get("trinkets") or []
        if not isinstance(i, int) or not 0 <= i < len(tr):
            raise Invalid("Use which trinket?")
        k = tr[i]["k"]
        want = C.TRINKETS[k][1]
        tgt = msg.get("tgt")
        m = self.mods(h)
        if want == "foe":
            fo = self.foe(int(tgt[1:])) if isinstance(tgt, str) and tgt.startswith("f") and tgt[1:].isdigit() else None
            if not fo or fo["hp"] <= 0:
                raise Invalid("Pick an enemy.")
        elif want == "hero":
            y = int(tgt[1:]) if isinstance(tgt, str) and tgt.startswith("h") and tgt[1:].isdigit() else h
            if not self.active(y):
                raise Invalid("Pick someone standing.")
        tr[i]["uses"] -= 1
        if tr[i]["uses"] <= 0:
            tr.pop(i)
        if k == "smoke":
            self.hs(y)["st"]["dodge"] = 1
            self.fx("st", to=f"h{y}", s="smoke")
            if y != h and m.get("pay_forward"):
                self.hs(y)["st"]["armor"] = self.hs(y)["st"].get("armor", 0) + 3
                self.fx("armor", to=f"h{y}", n=3)
        elif k == "caltrops":
            for fo in self.front_foes():
                it = fo.get("intent") or {}
                if it.get("dice") and it.get("k") in ("attack", "all"):
                    it["bonus"] = it.get("bonus", 0) - 2
                    self.intent_numbers(it)
                    self.fx("st", to=f"f{fo['id']}", s="weakened")
        elif k == "flash":
            fo["st"]["weak"] = max(fo["st"].get("weak", 0), 1)
            self.fx("st", to=f"f{fo['id']}", s="weak")
        elif k == "venom":
            fo["st"]["poison"] = fo["st"].get("poison", 0) + 3
            self.fx("st", to=f"f{fo['id']}", s="poison")
            self.foe_status_by(fo, "poison", h)
        elif k == "coin":
            left = [d for d in self.hs(y)["dice"] if not d["used"] and not d.get("rolled")]
            if left:
                d = max(left, key=lambda d: top_face(d["faces"]))
                d["bonus"] = d.get("bonus", 0) + (4 if y != h and m.get("pay_forward") else 2)
                self.fx("st", to=f"h{y}", s="inspired")
        elif k == "purse":
            self.hero(h)["gold"] += 6
            x["inspire"] = x.get("inspire", 0) + 2
            self.fx("coins", h=h, n=6)
        self.say(f"{self.hero(h)['name']} uses a {C.TRINKETS[k][0]}.")
        self.maybe_resolve()

    def combo_hit(self, h, fid):
        """A Duelist's hit: the combo on that enemy grows, or a new one starts (Feint Step carries it once a round)."""
        x = self.hs(h)
        c = x.get("combo")
        if c and c["id"] == fid:
            c["n"] += 1
        elif c and self.mods(h).get("feint_step") and not x.get("feinted"):
            x["feinted"] = True
            x["combo"] = {"id": fid, "n": c["n"] + 1}
        else:
            x["combo"] = {"id": fid, "n": 1}

    def act_outcome(self, since):
        """What an action did, from the effects it set off (fx after id `since`): damage dealt to
        enemies, HP lost by the party, healing, Armor, kills and statuses, for the round strip."""
        out = {"dmg": 0, "hurt": 0, "heal": 0, "armor": 0, "kills": 0, "st": []}
        for e in self.s["fx"]:
            if e["id"] <= since:
                continue
            k, to = e["k"], str(e.get("to", ""))
            if k == "dmg":
                out["dmg" if to.startswith("f") else "hurt"] += e.get("n", 0)
            elif k in ("heal", "armor"):
                out[k] += e.get("n", 0)
            elif k == "die" and to.startswith("f"):
                out["kills"] += 1
            elif k == "st" and e.get("s") and e["s"] not in out["st"]:
                out["st"].append(e["s"])
        return {k: v for k, v in out.items() if v}

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
                if fo["hp"] > 0 and self.mods(a["owner"]).get("strangler_fig"):
                    fo["st"]["root"] = max(fo["st"].get("root", 0), 2)  # Strangler Fig: into the next round too
                    self.fx("st", to=f"f{fo['id']}", s="root")
        for h in self.actives():
            fo = self.hawk_foe(h)
            if fo:
                self.fx("act", h=h, a="sic_em", tgt=f"f{fo['id']}")
                self.hurt_foe(fo, C.HAWK_PECK * self.mods(h).get("alpha_hawk", 1), h)  # the hawk pecks its prey
        if self.check_end():
            return
        # Enemies act, fastest first. Their Armor lasts from one enemy turn to the next, so what a
        # Block, a Guard or a shield face gives them protects them through the heroes' next round.
        for fo in self.foes():
            fo["st"].pop("armor", None)
        f = self.s["fight"]
        f["last"], f["rec"] = [], "foes"
        for fo in sorted(self.foes(), key=lambda fo: -A.FOES[fo["k"]]["speed"]):
            if fo["hp"] <= 0:
                continue
            self.foe_act(fo)
            self.mummy_hold()
            if self.check_end():
                return
        f["rec"] = "end"
        self.end_round()

    # What the enemies' turn did, kept for the next round's recap (`f["last"]`): one entry per enemy
    # action, holding what it did to whom, and one for the round's end (Undertow, Burn, Doom).
    RECAP = {"dmg", "heal", "armor", "down", "die", "st", "summon", "revive"}

    def recap(self, f, k, kw):
        last = f.setdefault("last", [])
        cur = last[-1] if last else None
        if f["rec"] == "foes" and (k in ("froll", "fact") or (k == "st" and kw.get("s") == "stunned" and kw["to"].startswith("f"))):
            fid = kw.get("f", None) if k != "st" else int(kw["to"][1:])
            if not cur or cur.get("f") != fid or k == "st":
                fo = next((o for o in f["foes"] if o["id"] == fid), None)
                cur = {"f": fid, "who": fo["name"] if fo else "?", "ik": kw.get("ik"),
                       "a": "Stunned" if k == "st" else kw.get("name") or ((fo or {}).get("intent") or {}).get("name"), "ev": []}
                last.append(cur)
            return
        if f["rec"] == "end" and (not cur or cur.get("f") is not None):
            cur = {"f": None, "who": "Round end", "a": None, "ev": []}
            last.append(cur)
        if cur is not None and k in self.RECAP:
            cur["ev"].append({x: kw[x] for x in ("to", "n", "block", "s") if kw.get(x) not in (None, 0)} | {"k": k})

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
        n, blocked, shrugs = self.foe_soak(fo, n, h, pure, pierce)
        if shrugs:
            self.fx("st", to=f"f{fo['id']}", s="shrugs")  # the Brine Golem's crust: small hits don't get through
        if blocked:
            fo["st"]["armor"] -= blocked
        fo["hp"] -= n
        if fo["st"].get("mummy"):
            fo["mcap"] = min(fo.get("mcap", fo["hp"]), fo["hp"])
        if fo["st"].get("sleep") and h is not None and n > 0:
            fo["st"].pop("sleep")  # Sleep Thread: a hit wakes it, and it attacks after all
            if fo.get("slept"):
                fo["intent"] = fo.pop("slept")
            self.fx("st", to=f"f{fo['id']}", s="wakes")
        if h is not None:
            self.s["stats"][h]["dmg"] += n
            fo.setdefault("hurt_by", {})[str(h)] = fo.get("hurt_by", {}).get(str(h), 0) + n
            if n > 0 and str(h) in self.s["fight"]["hs"]:
                self.hs(h)["struck"] = True
        self.fx("dmg", to=f"f{fo['id']}", n=n, block=blocked)
        if not pure and h is not None and n > 0 and fo["st"].get("root"):
            self.web_splash(fo, n, h)  # the Warden's Rootweb
        if not pure and fo["st"].pop("shock", 0) and n > 0:
            others = [o for o in self.foes() if o is not fo]
            if others:
                near = [o for o in others if o["row"] == fo["row"]] or others
                self.hurt_foe(near[0], n // 2, h, pure=True)
        thorns = A.FOES[fo["k"]].get("thorns", 0) + fo.get("thorns_x", 0)
        if thorns and h is not None and not pure and not bomb and n > 0 and self.active(h):
            self.fx("st", to=f"f{fo['id']}", s="thorns")
            self.hurt_hero(h, thorns, None, pure=True)
        if fo["hp"] <= 0:
            self.foe_dies(fo, h, bomb)
        else:
            if not pure and h is not None and fo["st"].get("poison"):
                fester = max(self.mods(y).get("fester", 0) for y in self.actives()) if self.actives() else 0
                if fester:
                    fo["st"]["poison"] += fester
                    self.fx("st", to=f"f{fo['id']}", s="poison")
            self.foe_hit_hooks(fo, n, h, pure)
            self.foe_bloodied(fo)
        return n

    def wardens(self):
        """The Wardens standing in this fight: while one is, every Rooted enemy is Entwined."""
        f = self.s["fight"]
        return [y for y in f["heroes"] if self.active(y) and C.map_key(self.hero(y)) == "wildspeak"]

    def web_splash(self, fo, n, h):
        """A hit on an Entwined enemy: every other Entwined enemy takes WEB_SPLASH (Thicket +1, Heart of
        the Wild a third of the hit if more); alone, it takes WEB_LONE more. Splashes don't splash."""
        ws = self.wardens()
        if not ws:
            return
        mods = [self.mods(y) for y in ws]
        base = C.WEB_SPLASH + (1 if any(m.get("thicket") for m in mods) else 0)
        amt = max(base, n // 3) if any(m.get("heart_wild") for m in mods) else base
        others = [o for o in self.foes() if o is not fo and o["st"].get("root")]
        if not others:
            if fo["hp"] > 0:
                self.hurt_foe(fo, C.WEB_LONE, h, pure=True)
            return
        for o in others:
            self.fx("st", to=f"f{o['id']}", s="web")
            self.hurt_foe(o, amt, h, pure=True)
        for y, m in zip(ws, mods):
            if m.get("sapping_vines"):
                hurt = [z for z in self.actives() if self.hero(z)["hp"] < self.maxhp(z)]
                if hurt:
                    self.fight_heal(min(hurt, key=lambda z: self.hero(z)["hp"] / self.maxhp(z)), 1, y)  # Sapping Vines

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
        for y in self.actives():
            if self.hs(y).get("hawk") == f"f{fo['id']}":
                left = [o for o in self.foes() if o["hp"] > 0]
                if self.mods(y).get("apex") and left:
                    self.send_hawk(y, f"f{min(left, key=lambda o: o['hp'])['id']}")  # Apex Predator
                    self.hs(y)["apex_n"] = self.mods(y)["apex"]
                else:
                    self.hs(y)["hawk"] = f"h{y}"  # its prey is down: the hawk comes back
        if h is not None and self.hero(h)["alive"]:
            self.s["stats"][h]["kills"] += 1
            m = self.mods(h)
            if m.get("kill_heal") and self.active(h):
                self.fight_heal(h, m["kill_heal"], h)
            x = f["hs"].get(str(h))
            if m.get("kill_die") and self.active(h) and x and not x.get("kdie") and self.foes():
                # Bloodlust: the first kill each round hands you a fresh die to keep swinging
                x["kdie"] = True
                x["dice"].append(self.new_die(h, list(range(1, m["kill_die"] + 1)), "bloodlust"))
                self.fx("st", to=f"h{h}", s="bloodlust")
            if x and "trinkets" in x and self.active(h):
                self.pilfer(h, 2 if m.get("fences_eye") else 1)  # Pickings: a killing blow lifts a trinket
            if f.get("harm") is not None and not f.get("echoed"):
                for y in self.actives():
                    if y != h and self.mods(y).get("harmonic_echo") and self.hs(y).get("lastharm"):
                        f["echoed"] = True  # Harmonic Echo, once a round
                        self.raise_harmony(y, self.hs(y)["lastharm"])
                        break
            if m.get("kill_resolve") and x and "resolve" in x and self.active(h):
                self.add_resolve(h, m["kill_resolve"])  # Bushido Code
            if m.get("fan_flames") and x and "heat" in x and self.active(h):
                self.add_heat(h, m["fan_flames"])  # Fan the Flames
            if m.get("kill_armor") and self.active(h):
                st = self.hs(h)["st"]
                st["armor"] = st.get("armor", 0) + m["kill_armor"]
                self.fx("armor", to=f"h{h}", n=m["kill_armor"])
            if m.get("kill_gold"):
                self.hero(h)["gold"] += m["kill_gold"]
                self.fx("coins", h=h, n=m["kill_gold"])
            if m.get("rampage") and x and x.get("acting") in x["cds"]:
                x["cds"][x["acting"]] = 1  # Rampage: ready again next round
                self.fx("st", to=f"h{h}", s="rampage")
            if m.get("dirty_trick"):
                aimed = [o for o in self.foes() if (o.get("intent") or {}).get("dice")]
                if aimed:
                    self._op_steal(None, {}, [max(aimed, key=lambda o: o["intent"].get("hi", 0))])
        if fo["st"].get("mark") and any(self.mods(y).get("mark_pass") for y in self.actives()):
            others = [o for o in self.foes() if not o["st"].get("mark")]
            if others:
                o = min(others, key=lambda o: o["hp"])
                o["st"]["mark"] = fo["st"]["mark"]
                self.fx("st", to=f"f{o['id']}", s="mark")
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
        if d.get("keg") and h is not None:
            self.keg_broken(fo, h)
        if d.get("volatile"):
            self.fx("st", to=f"f{fo['id']}", s="explodes")
            for y in self.actives():
                self.hurt_hero(y, d["volatile"], None, pure=True)
        if d.get("ember"):
            # it goes up in embers: every hero standing is Burned
            self.fx("st", to=f"f{fo['id']}", s="embers")
            for y in self.actives():
                self.hero_status(y, "burn", d["ember"])
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
            if str(by) in self.s["fight"]["hs"]:
                self.add_grace(by, got + (2 * max(0, over) if self.mods(by).get("overflowing_grace") else 0))
            if over > 1 and self.mods(by).get("overflow"):
                self.hs(h)["st"]["armor"] = self.hs(h)["st"].get("armor", 0) + over // 2  # Overflow: half (Nov 2026)
            bill = self.mods(by).get("clean_bill", 0)
            if bill and got > 0 and h != by and hero["hp"] >= mx and self.active(h):
                # Clean Bill: their next die this round, or next round's if they've nothing left to roll
                y = self.hs(h)
                key = "inspire" if any(not d["used"] and not d.get("rolled") for d in y["dice"]) else "carry"
                y[key] = y.get(key, 0) + bill
                self.fx("st", to=f"h{h}", s="inspired")
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
            if a.get("owner") is not None and self.mods(a["owner"]).get("bloom"):
                for y in self.actives():
                    self.fight_heal(y, a["max"] // 2, a["owner"])
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
            if fo is not None:
                if fo["st"].get("snare") and fo["hp"] > 0:
                    # Thorn Snare: sprung as it attacks
                    self.hurt_foe(fo, fo["st"].pop("snare"), fo.pop("snare_by", None), pure=True)
                    if fo["hp"] > 0:
                        fo["st"]["root"] = max(fo["st"].get("root", 0), 1)
                        self.fx("st", to=f"f{fo['id']}", s="root")
                if x["st"].get("counter") and fo["hp"] > 0:
                    self.hurt_foe(fo, x["st"].pop("counter"), h, pure=True)  # Set the Pike: it runs onto the point
                if fo["hp"] <= 0:
                    return 0  # it fell before its blow landed
                n += fo.pop("owed", 0)  # Sleep Dart: the put-off attack rides on this one
                tt = f.get("tether")
                if tt and h in tt:
                    # Tether: the first hit on either hero is split between them
                    f.pop("tether")
                    other = tt[1] if tt[0] == h else tt[0]
                    if self.active(other) and n > 1:
                        self.hurt_hero(other, n // 2, None, pure=True)
                        n -= n // 2
            if x["st"].pop("dodge", 0):
                self.fx("st", to=f"h{h}", s="dodged")
                return 0
            if fo is not None and not x.get("pevade") and any(self.mods(y).get("party_evasive") for y in self.actives()):
                x["pevade"] = True  # the Wings of the Arbiter: the first hit on each hero each fight misses
                self.fx("st", to=f"h{h}", s="dodged")
                return 0
            if x["st"].pop("halfhit", 0):
                n //= 2  # Evasive, Smoke Bomb: half
                self.fx("st", to=f"h{h}", s="glanced")
            soak = self.mods(h).get("first_hit_soak", 0) + max([self.mods(y).get("ward_party", 0) for y in self.actives()] or [0])
            if soak and not x.get("soaked"):
                x["soaked"] = True
                n -= soak
            n -= f["sanct"] + f["aegis"]
            if fo is not None:
                n -= (f.get("harm") or {}).get("discord", 0)  # the Herald's Dissonance
            if fo is not None and fo["row"] == "back":
                n -= self.mods(h).get("footwork", 0)
            if fo is not None:
                for y in self.actives():
                    hy = self.hs(y)
                    if hy.get("hawk") == f"h{h}" and not x.get("hawk_soak"):
                        x["hawk_soak"] = 1  # the Ranger's hawk watches this hero: the first hit each round
                        n -= C.HAWK_WATCH * self.mods(y).get("alpha_hawk", 1)
                        self.fx("st", to=f"h{h}", s="hawk_soak")
                    if hy.get("hawk") == f"f{fo['id']}":
                        n -= self.mods(y).get("harrier", 0)  # Harrier
                if fo["st"].get("root") and any(self.mods(y).get("snare_line") for y in self.wardens()):
                    n -= sum(1 for o in self.foes() if o is not fo and o["st"].get("root"))  # Snare Line
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
            if "impact" in x and not pure:
                self.add_impact(h, blocked, fo)  # the Vanguard's Armor stores what it soaks
        n -= blocked
        hero = self.hero(h)
        hero["hp"] -= n
        self.s["stats"][h]["taken"] += n
        if fo is not None:
            x["lasthit"] = fo["id"]
            if n > 0 and h not in fo.setdefault("hitters", []):
                fo["hitters"].append(h)  # Judgment counts the heroes it has hurt
        if n > 0:
            x["lost"] = x.get("lost", 0) + n
            m = self.mods(h)
            for y in self.actives():
                if self.mods(y).get("martyr"):
                    self.add_grace(y, n // 2)  # Martyr: the party's wounds fill the Mender's Grace
                if y != h and fo is not None and self.mods(y).get("honor_guard"):
                    self.add_resolve(y, self.mods(y)["honor_guard"])  # Honor Guard
            if not x.get("berserk") and C.map_key(hero) == "forage" and \
                    x["lost"] >= self.maxhp(h) * (0.25 if m.get("hair_trigger") else C.BERSERK_AT):
                x["berserk"] = True  # the Berserker goes berserk: the rest of its dice explode
                self.fx("st", to=f"h{h}", s="berserk")
                for d in x["dice"]:
                    if not d["used"] and "exploding" not in d["dk"]:
                        d["dk"] = list(d["dk"]) + ["exploding"]
        if fo is not None and not pure and C.map_key(hero) == "dragons_rest":
            self.grow_scales(h, 2 if x["st"].get("wingguard") else 1)  # every hit that lands grows a Scale
        m = self.mods(h)
        if 0 < hero["hp"] < self.maxhp(h) / 2:
            if m.get("ancient_blood") and not x.get("ablood"):
                x["ablood"] = True  # Ancient Blood
                self.fight_heal(h, m["ancient_blood"], h)
            if m.get("ascension") and not x.get("ascend"):
                x["ascend"] = True  # Draconic Ascension
                self.fx("st", to=f"h{h}", s="ascended")
        self.fx("dmg", to=f"h{h}", n=n, block=blocked)
        if n > 0 and not pure and self.mods(h).get("pain_engine"):
            f["pain"][str(h)] = f["pain"].get(str(h), 0) + 1
        if fo is not None and not pure and fo["hp"] > 0:
            if blocked and not n and x["st"].get("riposte"):
                chain = self.mods(h).get("riposte_chain")
                self.hurt_foe(fo, x["st"]["riposte"] + (self.combo_on(h, fo) * C.COMBO_STEP if chain else 0), h, pure=True)
                if chain:
                    self.combo_hit(h, fo["id"])  # Riposte Chain
            self.iai_counter(h, fo)
            if x["st"].get("glyphward"):
                self.carve(fo, x["st"]["glyphward"])  # Counter-Glyph: whoever hits you is carved
            if x["st"].get("emberward"):
                fo["st"]["burn"] = fo["st"].get("burn", 0) + x["st"]["emberward"]  # Ember Ward
                self.fx("st", to=f"f{fo['id']}", s="burn")
            if fo["st"].get("root"):
                tt = max([self.mods(y).get("thorned_tendrils", 0) for y in self.wardens()] or [0])
                if tt and fo["hp"] > 0:
                    self.hurt_foe(fo, tt, self.wardens()[0], pure=True)  # Thorned Tendrils
            th = self.mods(h).get("thorns", 0) + x["st"].get("thorns", 0)
            if th and fo["hp"] > 0:
                self.hurt_foe(fo, th, h, pure=True)
            if x["st"].pop("chill", 0) and fo["hp"] > 0:
                fo["st"]["freeze"] = 1  # Rime Guard: whoever hits you is Frozen
                self.fx("st", to=f"f{fo['id']}", s="freeze")
            if self.mods(h).get("mark_attacker") and fo["hp"] > 0 and not fo["st"].get("mark"):
                fo["st"]["mark"] = 1
                self.fx("st", to=f"f{fo['id']}", s="mark")
            if x["st"].pop("shock", 0) and n > 0:
                others = [y for y in self.actives() if y != h]
                if others:
                    self.hurt_hero(others[0], n // 2, None, pure=True)
        burden = next((y for y in self.actives() if y != h and self.mods(y).get("burden")
                       and str(y) not in f.get("burdened", [])), None) if hero["hp"] <= 0 else None
        if hero["hp"] <= 0:
            if self.mods(h).get("unbreakable") and not x["unbreak"]:
                x["unbreak"] = True
                hero["hp"] = 1
                self.fx("st", to=f"h{h}", s="unbreakable")
            elif burden is not None:
                # Shared Burden: the healer takes half the blow, and the ally none of it
                f.setdefault("burdened", []).append(str(burden))
                hero["hp"] += n
                self.s["stats"][h]["taken"] -= n
                self.fx("heal", to=f"h{h}", n=n)
                self.fx("st", to=f"h{h}", s="shielded")
                self.hurt_hero(burden, (n + 1) // 2, None, pure=True)
                return 0
            else:
                hero["hp"] = 0
                if self.mods(h).get("final_breath") and not x.get("fbreath") and fo is not None and fo["hp"] > 0 \
                        and "resolve" in x:
                    x["fbreath"] = True  # Final Breath: one last cut
                    self.fx("st", to=f"f{fo['id']}", s="iai")
                    self.hurt_foe(fo, x["resolve"] + self.mods(h)["final_breath"], h, pure=True)
                x["down"] = True
                x["st"] = {}
                for y in self.actives():
                    if y != h and self.mods(y).get("loyalty") and "sheathed" in self.hs(y):
                        self.hs(y)["sheathed"] = True  # Loyalty
                        self.add_resolve(y, self.mods(y)["loyalty"])
                if hero.get("scales"):
                    hero["scales"] //= 2  # knocked down: half the Scales go (rounded up)
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
        f = self.s["fight"]
        f.pop("tether", None)  # Tether lasts the round
        for fo in self.foes():
            if fo["st"].pop("sleep", 0):
                fo.pop("slept", None)  # Sleep Thread: it slept through the round
        if f.get("harm"):
            f.pop("echoed", None)
            hold = any(self.mods(y).get("symphony") for y in f["heroes"]) and all(v >= 2 for v in f["harm"].values())
            slow = any(self.mods(y).get("sustain") for y in f["heroes"]) and f["round"] % 2
            if not hold and not slow:
                f["harm"] = {k: max(0, v - 1) for k, v in f["harm"].items()}  # Harmonies fade
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
            for s in [s for s, v in st.items() if not v]:
                del st[s]
        for h in self.actives():
            x = self.hs(h)
            st = x["st"]
            if st.get("burn"):
                self.hurt_hero(h, st["burn"], None, pure=True)
                st["burn"] -= 1
            if st.pop("lifeline", 0) and self.active(h):
                self.fight_heal(h, self.maxhp(h) // 2, None)
            for s in TICKING:
                if st.get(s):
                    st[s] -= 1
            m = self.mods(h)
            if st.get("kshield") and m.get("kinetic_rebound") and st.get("armor") and x.get("lasthit") is not None:
                fo = self.foe(x["lasthit"])
                if fo and fo["hp"] > 0:
                    self.hurt_foe(fo, st["armor"], h, pure=True)  # Kinetic Rebound
            if m.get("calm_mind") and x.get("focus", 0) > 0 and self.active(h):
                self.fight_heal(h, m["calm_mind"] * x["focus"], h)  # Calm Mind
            for s in ROUND_ONLY:
                st.pop(s, None)
            if not self.mods(h).get("covenant"):
                st.pop("infuse", None)  # an infusion lasts the round (Covenant Edge: the fight)
                x.pop("inf", None)
            x.pop("white", None)
            x.pop("redline", None)
            x.pop("cold_used", None)
            x.pop("crit_lift", None)
            x.pop("imp2", None)  # Brace for Impact lasts the round
            x.pop("hawk_soak", None)
            x.pop("feinted", None)
            if not self.mods(h).get("relentless"):
                x.pop("combo", None)  # a combo lasts the round (Relentless: into the next)
            if "heat" in x:
                m = self.mods(h)
                if m.get("hearthfire") and x["heat"] >= 10:
                    hurt = [y for y in self.actives() if self.hero(y)["hp"] < self.maxhp(y)]
                    if hurt:
                        self.fight_heal(min(hurt, key=lambda y: self.hero(y)["hp"] / self.maxhp(y)), m["hearthfire"], h)
                x["heat"] -= x["heat"] // 4 if m.get("bank_coals") else x["heat"] // 2  # it cools
            st["armor"] = st.get("armor", 0) // 3 if self.mods(h).get("overguard") else 0
            for s in [s for s, v in st.items() if not v]:
                del st[s]
        self.boss_phase()
        if not self.check_end():
            self.new_round()

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
        """A fight is over: the knocked down get a revive (or fall for good), then the winners'
        rewards and the dungeon's next step, or the losers fall back."""
        s = self.s
        f = s["fight"]
        for h in f["heroes"]:
            if self.hs(h)["down"]:
                self.revive_or_fall(h)
            if self.mods(h).get("stored_force") and self.hs(h).get("impact"):
                self.hero(h)["stored"] = self.hs(h)["impact"]  # Stored Force: Armor at the next fight's start
            if self.mods(h).get("stash") and self.hs(h).get("trinkets"):
                self.hero(h)["stash"] = [self.hs(h)["trinkets"][0]]  # Stash: one trinket kept for the next fight
        s["fight"] = None
        self.fx("fightend", result=result, **({"xp": f["xp"], "gold": f["gold"]} if result == "won" and f["kind"] != "boss" else {}))
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
            self.fight_won(f)
        else:
            self.fight_lost(f)
        self.next_step()

    def revive_or_fall(self, h):
        s = self.s
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

    def fight_won(self, f):
        """Gold, loot, a lair or quest done, the dungeon's next step, XP."""
        s = self.s
        party = f["heroes"]
        winners = [h for h in party if not self.hs_from(f, h)["fled"] and self.hero(h)["alive"]]
        gold = f["gold"]
        for h in winners:
            self.hero(h)["gold"] += gold + self.mods(h).get("sticky", 0)
        self.say(f"Victory! +{f['xp']} XP" + (f", +{gold} gold each." if gold else "."))
        prizes = [g["prize"] for g in s["groups"] if g["id"] in f["groups"] and g.get("prize")]
        self.raids_beaten(f, winners)
        s["groups"] = [g for g in s["groups"] if g["id"] not in f["groups"]]
        p = self.place(f["tile"])
        wreck = f["kind"] == "lair" and p and p["kind"] == "wreck" and p.get("guard") and not p.get("done")
        if wreck:
            p["done"] = True
            self.say("The guards are beaten: the wreck is yours to pick through.")
        if f["kind"] == "lair" and p and p["kind"] == "lair":
            p["done"] = True
        for q in s["quests"]:  # a lair cleared or a wanted crew caught
            if q.get("group") in f["groups"] and not q["done"] and not q.get("failed"):
                self.complete_quest(q, winners[0] if winners else party[0])
        final = f["kind"] == "dungeon" and f["step"] >= A.DUNGEON_STEPS - 1
        path = f.get("path")
        # one shared pool of loot for the winners: its size and claims are fixed, the fight sets the rarity
        n, bonus = 0, 0
        if f["kind"] == "dungeon":
            n, bonus = (2 if path == "sneak" else 3, 2) if final else (3, 2) if path == "champion" else (2, 1)
            if path == "vault":
                for h in winners:
                    self.hero(h)["gold"] += 12
        elif f["kind"] == "lair" or any(fo.get("aff") or A.FOES[fo["k"]].get("big") for fo in f["foes"]):
            n, bonus = 2, 1
        elif self.rng.chance(0.35):
            n = 1
        if wreck:
            # a guarded wreck's pool holds an enchant material besides its rare gear
            self.offer_pool(winners, rarity=p["rarity"], extra=prizes + [self.rng.choice(I.MATERIALS)])
        elif n or prizes:
            # now and then a fight's pool holds an enchant material too
            mat = [self.rng.choice(I.MATERIALS)] if self.rng.chance(A.FIGHT_MAT_CHANCE) else []
            self.offer_pool(winners, tier_bonus=bonus + (1 if n >= 3 else 0), extra=prizes[:1] + mat)
        if path == "vault" and winners:
            self.say("The vault gives up its gold: +12 each.")
        if f["kind"] == "dungeon":
            self.dungeon_advance(f)
        if f.get("win") and winners:
            # an event fight's prize (a quest's next step, a relic): to whoever started it, if they're still up
            by = f["by"] if f.get("by") in winners else winners[0]
            self.outcome(by, f["win"], next(e for e in A.EVENTS if e["key"] == f["ev"]), None)
        self.gain_xp(f["xp"])

    def dungeon_advance(self, f):
        """A dungeon fight won: the dungeon is cleared, or the party picks its next path."""
        s = self.s
        reg = f["region"]
        step = f["step"] + 1
        s["dungeon"][reg] = step
        if step >= A.DUNGEON_STEPS:
            s["cleared"].append(reg)
            self.say(f"{A.DUNGEONS[reg]['name']} is cleared! ({len(s['cleared'])} of 3)")
            if not s.get("garrison", {}).get(reg):
                s["crown_cut"] = s.get("crown_cut", 0) + 1
                self.say("Cleared before its garrison grew: the Drowned Crown is weakened.")
            self.fx("cleared", region=reg)
            if len(s["cleared"]) == 3:
                self.say("All three are cleared. The way to the peak is open.")
            return
        still = [h for h in f["heroes"] if self.hero(h)["alive"] and not self.hs_from(f, h)["fled"]]
        if still:
            self.make_fork(reg, step, f["tile"], still)
        else:
            path = "passage" if step == 1 else "gate"
            s["dnext"][reg] = {"path": path, "foes": self.dungeon_lineup(reg, path)}

    def fight_lost(self, f):
        """Anyone still standing (or revived) falls back; the enemies keep their wounds."""
        s = self.s
        for h in f["heroes"]:
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


    def hs_from(self, f, h):
        return f["hs"][str(h)]

    # ------------------------------------------------------------------ the view

    def fight_view(self):
        f = self.s["fight"]
        if not f:
            return None
        out = {k: f[k] for k in ("id", "kind", "tile", "heroes", "round", "foes", "done", "guard", "taunt",
                                 "sanct", "aegis", "spirit", "region", "step", "phase", "ambush", "allies")}
        out["chord"] = f.get("chord")
        out["seq"] = f.get("seq", 0)
        out["path"] = f.get("path")
        out["hymn"] = f.get("hymn", 0)
        out["last"] = f.get("last", [])
        out["ground"] = f.get("ground")
        out["harm"] = f.get("harm")
        out["raid"] = f.get("raid")
        out["hs"] = {k: dict(x, dice=[{kk: vv for kk, vv in d.items() if kk not in ("sv", "stag")} for d in x["dice"]],
                             rollmods={m: v for m, v in self.mods(int(k)).items() if m in ROLL_MODS and v})
                     for k, x in f["hs"].items()}
        return out
