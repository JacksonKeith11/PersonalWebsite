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
from .dice import Dice, face, num, top_face
from .foes import Foes
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
            "path": spec.get("path"),
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
        if self.check_end():
            return
        f["hymn"] = 0
        anthem = [h for h in self.actives() if self.mods(h).get("anthem")]
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
        self.crown_round()
        self.foe_round()
        for fo in self.foes():
            self.choose_intent(fo)
        self.fx("round", n=f["round"])

    def round_reset(self):
        """Clear last round's bookkeeping; returns the Pain Engine bonuses it earned."""
        f = self.s["fight"]
        f["round"] += 1
        f["done"] = []
        f["rec"] = None
        f["guard"] = {}
        f["lastdie"] = {}
        f["pincered"] = []
        f["cloaked"] = []
        f["covered"] = []
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
        x["dice"] = []
        x["round_once"] = []
        x["cds"] = {k: n - 1 for k, n in x.get("cds", {}).items() if n > 1}
        x["links"] = {}
        x["tempo"] = False
        x["kdie"] = False
        x["inspire"] = x.pop("carry", 0)  # Clean Bill's bonus, earned after their dice were spent
        x.pop("spells", None)
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
        self.dice_attacks(h, x, m)

    def round_dice(self, h, x, m, anthem):
        """The dice a hero rolls this round: gear and class dice, then pets, Anthem, Slack Water."""
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
        return dice

    def dice_attacks(self, h, x, m):
        """What enemies did to a hero's dice: Hex swaps the biggest for a cursed one, Freeze takes
        the smallest, thieves take the biggest, Barnacle Crust locks it, static shocks low rolls.
        Then Diagnosis shows the smallest."""
        if x["st"].pop("hex", 0) and x["dice"]:
            big = max(x["dice"], key=lambda d: top_face(d["faces"]))
            big.update(faces=list(CURSED_DIE), dk=[], src="hex", v=None, top=False)
            for k2 in ("link", "sv", "stag", "hint", "fc", "tag"):
                big.pop(k2, None)
            self.fx("st", to=f"h{h}", s="hexed")
        if x["st"].pop("freeze", 0) and not m.get("freeze_immune") and x["dice"]:
            x["dice"].remove(min(x["dice"], key=num))
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
        u = I.ITEMS[key]["use"]
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
        self.say(f"{hero['name']} uses {I.ITEMS[key]['name']}.")
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
        hit = self.roll_for(h, a, dice)
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
        if m.get("frozen_bonus") and isinstance(tgt, str) and tgt.startswith("f") and any(d.get("tag") == "freeze" for d in dice):
            # a freeze face freezes before its own hit lands, so Frostbite counts on that hit too
            fo = self.foe(int(tgt[1:]))
            if fo and fo["hp"] > 0:
                fo["st"]["freeze"] = 1
        self.run_ops(h, a, dice, tgt, ops=ops, hit=hit)
        x.pop("acting", None)
        if self.s["fight"] is f:
            self.after_action(h, a, tgt)
        self.elements(h, a, dice, tgt)
        if self.s["fight"] is f and a["tgt"] == "foe" and dice and isinstance(tgt, str) and tgt.startswith("f"):
            f.setdefault("lastdie", {})[tgt[1:]] = [h, [num(d) for d in dice]]
            fo = self.foe(int(tgt[1:]))
            known = [d["v"] for d in ((fo or {}).get("intent") or {}).get("dice") or [] if d.get("v") is not None]
            if self.mods(h).get("tempo") and known and not x.get("tempo") and max(num(d) for d in dice) > max(known):
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
        done["vals"] = [num(d) for d in dice]
        done["out"] = self.act_outcome(since)
        if self.s["fight"] is f:
            self.check_end()

    def after_action(self, h, a, tgt):
        """Bookkeeping for the passives that care what was done: Spellweave, Reagents, Quarry,
        Call and Response (instants call it too)."""
        f = self.s["fight"]
        x = self.hs(h)
        if a.get("spell"):
            x.setdefault("spells", []).append(a["key"])
        if a.get("bomb"):
            x["bombs"] = x.get("bombs", 0) + 1
        if self.mods(h).get("quarry") and a["tgt"] == "foe" and isinstance(tgt, str) and tgt.startswith("f"):
            fid, r, q = int(tgt[1:]), f["round"], x.get("quarry")
            if q and q["id"] == fid and q["r"] == r - 1:
                x["quarry"] = {"id": fid, "r": r, "n": q["n"] + 1}
            elif not (q and q["id"] == fid and q["r"] == r):
                x["quarry"] = {"id": fid, "r": r, "n": 1}
        if x.get("cued") and any(o["op"] == "dmg" for o in a["ops"]):
            x.pop("cued")
        cue = self.mods(h).get("cue")
        if cue:
            for y in self.actives():
                if y != h:
                    self.hs(y)["cued"] = cue

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
        for h in self.actives():
            if self.mods(h).get("pet_strike") and self.foes():
                fo = min(self.foes(), key=lambda o: o["hp"])
                self.fx("act", h=h, a="sic_em", tgt=f"f{fo['id']}")
                self.hurt_foe(fo, 3, h)
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
            if not pure and h is not None and fo["st"].get("poison"):
                fester = max(self.mods(y).get("fester", 0) for y in self.actives()) if self.actives() else 0
                if fester:
                    fo["st"]["poison"] += fester
                    self.fx("st", to=f"f{fo['id']}", s="poison")
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
            x = f["hs"].get(str(h))
            if m.get("kill_die") and self.active(h) and x and not x.get("kdie") and self.foes():
                # Bloodlust: the first kill each round hands you a fresh die to keep swinging
                x["kdie"] = True
                x["dice"].append(self.new_die(h, list(range(1, m["kill_die"] + 1)), "bloodlust"))
                self.fx("st", to=f"h{h}", s="bloodlust")
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
            for s in ROUND_ONLY:
                st.pop(s, None)
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
            self.offer_pool(winners, rarity=p["rarity"], extra=prizes)
        elif n or prizes:
            self.offer_pool(winners, tier_bonus=bonus + (1 if n >= 3 else 0), extra=prizes[:1])
        if path == "vault" and winners:
            self.say("The vault gives up its gold: +12 each.")
        if f["kind"] == "dungeon":
            self.dungeon_advance(f)
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
        out["covered"] = f.get("covered", [])
        out["lastdie"] = f.get("lastdie", {})
        out["pincered"] = f.get("pincered", [])
        out["path"] = f.get("path")
        out["hymn"] = f.get("hymn", 0)
        out["last"] = f.get("last", [])
        out["hs"] = {k: dict(x, dice=[{kk: vv for kk, vv in d.items() if kk not in ("sv", "stag")} for d in x["dice"]],
                             rollmods={m: v for m, v in self.mods(int(k)).items() if m in ROLL_MODS and v})
                     for k, x in f["hs"].items()}
        return out
