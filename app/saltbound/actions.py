"""What actions do: the targets, the amounts, and each op's effect (`run_ops`), the instant actions
that set up dice (`instant`), and the shared sums both the fight and the bots use for a hit
(`hit_amount`, `foe_damage_after`, `foe_soak`, `hit_spill`). Mixed into `Game` through `Combat`.
"""

from . import classes as C
from .content import archipelago as A
from .dice import amt, face, is_pair, is_straight, num, top_face
from .foes import die_range
from .tuning import CROWN_EXPOSED, CROWN_WARD, DEBUFFS, ONE_SHOT, UNSTOPPABLE


class Cast:
    """One action taking effect: who, with what and on whom, and what it has done so far."""

    def __init__(self, **kw):
        self.half = False
        self.__dict__.update(kw)

    def scale(self, n):
        return n // 2 if self.half else n


class Actions:
    def env(self, h, a, dice, target=None, vals=None, tags=None):
        """Variables for an action's amounts. `vals`/`tags` are the rolled values (or, while
        estimating, one possible outcome); without them, dice count at what they're showing or
        what they roll on average."""
        if vals is None:
            vals = [num(d) for d in dice]
            tags = [d.get("tag") for d in dice]
        return self.target_env(self.dice_env(h, vals, tags), h, target, vals)

    def dice_env(self, h, vals, tags):
        """The variables that depend only on the hero and the dice (the bots work these out once per
        outcome and add each target's with `target_env`)."""
        x = self.hs(h)
        return {"v": vals[0] if vals else 0, "sum": sum(vals), "n": len(vals), "armor": x["st"].get("armor", 0),
                "missing": self.maxhp(h) - self.hero(h)["hp"], "undead": 0, "rooted": 0, "stunned": 0, "poisoned": 0,
                "marked": 0, "aimed": 0, "d": vals[0] if vals else 0, "matched": 0,
                "pair": int(is_pair(vals, tags)), "straight": int(is_straight(vals, tags)), "outroll": 0,
                "sig": 0, "sigv": 0, "allsig": sum(fo["st"].get("sigil", 0) for fo in self.foes()),
                "qg": int(bool(self.mods(h).get("quiet_glyph")) and bool(vals) and vals[0] <= 2)}

    def target_env(self, e, h, target, vals):
        """A copy of `dice_env`'s variables with the target enemy's added."""
        e = dict(e)
        if isinstance(target, dict):
            st = target["st"]
            it = target.get("intent") or {}
            known = [d["v"] for d in it.get("dice") or [] if d.get("v") is not None]
            e["outroll"] = int(bool(vals) and bool(known) and len(known) == len(it.get("dice") or []) and vals[0] > max(known))
            e.update(undead=int(bool(A.FOES[target["k"]].get("undead"))), rooted=int(bool(st.get("root"))),
                     stunned=int(bool(st.get("stun"))), poisoned=int(bool(st.get("poison"))), marked=int(bool(st.get("mark"))),
                     aimed=int(f"h{h}" in self.intent_aims(it)), matched=0, sig=st.get("sigil", 0))
            e["sigv"] = sigil_worth(e)
        return e

    def target_part(self, h, target):
        """What `target_env` adds for this target that doesn't depend on the dice (the bots work it out
        once per target and finish it per roll with `target_env_from`)."""
        if not isinstance(target, dict):
            return None
        st = target["st"]
        it = target.get("intent") or {}
        dice = it.get("dice") or []
        known = [d["v"] for d in dice if d.get("v") is not None]
        top = max(known) if known and len(known) == len(dice) else None
        return top, {"undead": int(bool(A.FOES[target["k"]].get("undead"))), "rooted": int(bool(st.get("root"))),
                     "stunned": int(bool(st.get("stun"))), "poisoned": int(bool(st.get("poison"))),
                     "marked": int(bool(st.get("mark"))), "aimed": int(f"h{h}" in self.intent_aims(it)), "matched": 0,
                     "sig": st.get("sigil", 0)}

    def target_env_from(self, e, part, target, vals):
        """`target_env`, from a `target_part` worked out earlier."""
        e = dict(e)
        if part is not None:
            top, add = part
            e["outroll"] = int(bool(vals) and top is not None and vals[0] > top)
            e.update(add)
            e["sigv"] = sigil_worth(e)
        return e

    def dmg_bonus(self, h, a, target):
        """Flat damage a hero adds to every hit of this action on this target."""
        m = self.mods(h)
        f = self.s["fight"]
        n = m.get("might", 0) + self.herald_aura()
        n += (f.get("ground") or {}).get("might", 0)  # the Prism Wood's Resonance
        n += m.get("momentum", 0) * f["acts"].get(str(h), 0)
        n += m.get("rage", 0) * ((self.maxhp(h) - self.hero(h)["hp"]) // 5)
        x = self.hs(h)
        if a.get("bomb"):
            n += m.get("bomb_bonus", 0) + m.get("reagents", 0) * min(5, x.get("bombs", 0))
        if a.get("spell") and m.get("spellweave") and any(k != a["key"] for k in x.get("spells", [])):
            n += m["spellweave"]
        n += x.get("cued", 0)
        if a.get("melee") and x["st"].get("infuse"):
            n += x.get("inf", {}).get("dmg", 0)  # an infused blade (Spellblade)
        kind = "melee" if a.get("melee") else "spell" if a.get("spell") else None
        if m.get("bladesong") and kind and x.get("lastk") and x["lastk"] != kind:
            n += m["bladesong"]
        if m.get("first_strike") and not x.get("struck"):
            n += m["first_strike"]
        if m.get("unseen") and not any(f"h{h}" in self.intent_aims(fo.get("intent") or {}) for fo in self.foes()):
            n += m["unseen"]
        if isinstance(target, dict):
            if m.get("engage") and target["hp"] >= target["max"]:
                n += m["engage"]
            if a.get("spell") and m.get("wither"):
                n += m["wither"] * sum(1 for s in DEBUFFS if target["st"].get(s))
            q = x.get("quarry")
            if m.get("quarry") and q and q["id"] == target["id"]:
                r = f["round"]
                n += m["quarry"] * min(3, q["n"] - 1 if q["r"] == r else q["n"] if q["r"] == r - 1 else 0)
            if target["st"].get("stun") or target["st"].get("root"):
                n += m.get("opportunist", 0)
            sig = target["st"].get("sigil", 0)
            if sig and a["key"] == "rune_cut":
                n += m.get("whetted", 0) * sig
            if sig and (a.get("spell") or a.get("bomb")):
                # Open Circuit: an ally Spellblade's Sigils feed this hero's spells and bombs
                n += sig * max([self.mods(y).get("open_circuit", 0) for y in self.actives() if y != h] or [0])
            if target["st"].get("burn"):
                n += m.get("burn_bonus_hit", 0)
            if target["hp"] * 2 < target["max"]:
                n += m.get("execute_bonus", 0)
            aims = self.intent_aims(target.get("intent") or {})
            if aims and f"h{h}" not in aims:
                n += m.get("backstab", 0)
        return n

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
        elif fo.get("bl") and self.crown_warded(fo):
            n = int(n * CROWN_WARD)  # a bloodied boss's ward (the Radiant Arbiter behind her Sentinels)
        return max(0, n)

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
        if to == "another":
            # a different enemy from the action's target, at random (a bolt arcing on)
            first = next((t for t in base if isinstance(t, dict)), None)
            others = [fo for fo in self.foes() if fo is not first]
            return [self.rng.choice(others)] if others else []
        if to == "lowest":
            others = [y for y in self.actives() if y != h]
            return [("h", min(others, key=lambda y: self.hero(y)["hp"]))] if others else []
        if to == "aiming":
            # every enemy whose coming attack is aimed at the hero
            return [fo for fo in self.foes() if f"h{h}" in self.intent_aims(fo.get("intent") or {})]
        if to == "sigiled":
            return [fo for fo in self.foes() if fo["st"].get("sigil")]
        return base

    # ------------------------------------------------------------------ one hit's numbers
    # The fight (`_op_dmg`) and the bots (bot.evaluate) both work a hit out with these, so a new
    # damage rule goes here once and both see it.

    def hit_base(self, h, a, op, t, dice, vals, tags, i=None, half=False, env=None, bonus=None):
        """A hit's amount before combos, and the amounts' variables: the op's amount (for die `i`
        alone if the op hits once per die), the Plus bonus, halved for an echo, plus the hero's flat
        damage bonuses. The bots pass `env` and `bonus` they've already worked out."""
        env = self.env(h, a, dice, t, vals, tags) if env is None else dict(env)
        if i is not None:
            env["d"] = vals[i]
        fuse = self.mods(h).get("short_fuse") if a.get("bomb") else 0
        if fuse and vals and 0 < vals[0] <= 2:
            env["v"] = env["d"] = fuse  # Short Fuse: a 1 or 2 burns down fast
        n = amt(op["amt"], env) + (2 if a["plus"] else 0)
        return (n // 2 if half else n) + (self.dmg_bonus(h, a, t) if bonus is None else bonus), env

    def hit_finish(self, h, n, dice, vals, i=None, cresc=0):
        """A hit's amount after combos: Crescendo (half again; the bots pass the chance they'll
        have it) and Eagle Eye (half again when a die shows its top face)."""
        if cresc >= 1:
            n = n * 3 // 2
        elif cresc > 0:
            n = n * (1 + 0.5 * cresc)
        if self.mods(h).get("eagle_eye"):
            src = [i] if i is not None else range(len(dice))
            if any(vals[j] and vals[j] >= top_face(dice[j]["faces"]) for j in src):
                n = n * 3 // 2
        return n

    def hit_pierces(self, h, a, op):
        m = self.mods(h)
        return bool((m.get("unstoppable") and a["key"] in UNSTOPPABLE) or op.get("pierce") or m.get("pierce_all"))

    def foe_soak(self, fo, n, h, pure=False, pierce=False):
        """What an enemy's crust and Armor take off a hit (no changes made):
        (damage that lands, Armor used, whether the crust shrugged it off)."""
        shell = A.FOES[fo["k"]].get("shell_min")
        shrugs = bool(not pure and h is not None and shell and 0 < n < shell)
        if shrugs:
            n = 0
        blocked = min(0 if pierce else fo["st"].get("armor", 0), n)
        return n - blocked, blocked, shrugs

    def hit_spill(self, h, a, op, n, used=()):
        """Damage a hit spills past its target, in the order it lands: [(kind, amount)].
        chain: one other enemy at random; splash: the target's row (pure); arc: the back row."""
        m = self.mods(h)
        out = []
        if a.get("spell") and m.get("spell_chain") and a["tgt"] == "foe" and "chain" not in used:
            out.append(("chain", n // 2))
        if op.get("splash"):
            out.append(("splash", op["splash"] + m.get("splash_bonus", 0)))
        if a["key"] == "cleave" and m.get("wide_arcs") and not (m.get("unstoppable") and a["key"] in UNSTOPPABLE):
            out.append(("arc", n // 2))
        return out

    def spill_targets(self, kind, t):
        if kind == "arc":
            return [o for o in self.foes() if o["row"] == "back"]
        if kind == "splash":
            return [o for o in self.foes() if o is not t and o["row"] == t["row"]]
        return [o for o in self.foes() if o is not t]

    # ------------------------------------------------------------------ an action's effects

    def run_ops(self, h, a, dice, tgt, half=False, ops=None, hit=True):
        """An action's effects, op by op: each op kind is an `_op_<kind>` method below."""
        x = self.hs(h)
        c = Cast(h=h, a=a, dice=dice, tgt=tgt, half=half, hit=hit, m=self.mods(h), plus=2 if a["plus"] else 0,
                 base=self.targets_for(h, a, tgt), x=x, crescendo=x["st"].get("crescendo"), dealt=False, used=set())
        for op in (a["ops"] if ops is None else ops):
            targets = self.op_targets(h, op, c.base)
            handler = getattr(self, "_op_" + op["op"], None)
            if handler:
                handler(c, op, targets)
        if c.crescendo and c.dealt:
            x["st"].pop("crescendo", None)

    def op_gate(self, c, op, target=None):
        """An op's `if` condition."""
        return "if" not in op or bool(amt(op["if"], self.env(c.h, c.a, c.dice, target)))

    def op_amount(self, c, op):
        """An op's amount with the Plus bonus, halved for an echo."""
        return c.scale(amt(op["amt"], self.env(c.h, c.a, c.dice)) + c.plus)

    def _op_dmg(self, c, op, targets):
        h, a, m = c.h, c.a, c.m
        vals = [num(d) for d in c.dice]
        tags = [d.get("tag") for d in c.dice]
        pierce = self.hit_pierces(h, a, op)
        for i in (range(len(c.dice)) if op.get("each") else [None]):
            for t in (targets if not op.get("random") else [None]):
                if op.get("random"):
                    foes = self.foes()
                    if not foes:
                        break
                    t = self.rng.choice(foes)
                if isinstance(t, tuple) or t["hp"] <= 0 or not self.op_gate(c, op, t):
                    continue
                if t.get("air") and a.get("melee"):
                    self.fx("st", to=f"f{t['id']}", s="out of reach")
                    continue
                n, env = self.hit_base(h, a, op, t, c.dice, vals, tags, i, c.half)
                n += self.combo_bonus(h, a, c.dice, t, c.used)
                n = self.hit_finish(h, n, c.dice, vals, i, 1 if c.crescendo else 0)
                done = self.hurt_foe(t, n, h, pierce=pierce, bomb=a.get("bomb"))
                c.dealt = True
                if a.get("melee") and c.x["st"].get("infuse"):
                    self.infuse_hit(h, t)
                if op.get("burst"):
                    self.burst(c, op, t, vals)
                if a.get("spell") and m.get("spell_burn") and done and t["hp"] > 0:
                    t["st"]["burn"] = t["st"].get("burn", 0) + 1
                    self.fx("st", to=f"f{t['id']}", s="burn")
                    self.foe_status_by(t, "burn", h)
                if a.get("bomb") and m.get("bomb_poison") and done and t["hp"] > 0:
                    t["st"]["poison"] = t["st"].get("poison", 0) + m["bomb_poison"]
                    self.fx("st", to=f"f{t['id']}", s="poison")
                    self.foe_status_by(t, "poison", h)
                for kind, k_n in self.hit_spill(h, a, op, n, c.used):
                    if kind == "chain":
                        c.used.add("chain")
                        others = self.spill_targets(kind, t)
                        if others:
                            o = self.rng.choice(others)
                            self.fx("st", to=f"f{o['id']}", s="arced")
                            self.hurt_foe(o, k_n, h)
                    elif kind == "splash":
                        for o in self.spill_targets(kind, t):
                            self.hurt_foe(o, k_n, h, pure=True, bomb=a.get("bomb"))
                    else:
                        for o in self.spill_targets(kind, t):
                            self.hurt_foe(o, k_n, h)
                if op.get("leech") and done:
                    self.fight_heal(h, int(done * op["leech"]), h)
                if m.get("red_mist") and done and self.hero(h)["hp"] < self.maxhp(h) / 2:
                    self.fight_heal(h, done // 3, h)
                if op.get("onkill") and t["hp"] <= 0:
                    self.fight_heal(h, amt(op["onkill"], env), h)

    def _op_carve(self, c, op, targets):
        for t in targets:
            if isinstance(t, dict) and t["hp"] > 0:
                self.carve(t, t["st"].get("sigil", 0) if op.get("double") else op["n"])

    def _op_infuse(self, c, op, targets):
        v = num(c.dice[0]) if c.dice else 0
        self.infuse(c.h, op["n"], self.op_amount(c, op), op.get("el") or element_of(v))

    def _op_selfdmg(self, c, op, targets):
        hero = self.hero(c.h)
        n = min(amt(op["amt"], {}), hero["hp"] - 1)
        if n > 0:
            hero["hp"] -= n
            self.fx("dmg", to=f"h{c.h}", n=n, block=0)

    def _op_armor(self, c, op, targets):
        n = self.op_amount(c, op)
        for t in targets:
            if isinstance(t, tuple):
                st = self.hs(t[1])["st"]
                st["armor"] = st.get("armor", 0) + n
                self.fx("armor", to=f"h{t[1]}", n=n)

    def _op_heal(self, c, op, targets):
        n = self.op_amount(c, op) + c.m.get("heal_bonus", 0)
        for t in targets:
            if isinstance(t, tuple):
                self.fight_heal(t[1], n, c.h)

    def _op_heal_summons(self, c, op, targets):
        n = self.op_amount(c, op)
        for al in self.allies():
            got = min(n, al["max"] - al["hp"])
            al["hp"] += got
            if got:
                self.fx("heal", to=f"s{al['id']}", n=got)

    def status_amount(self, h, a, s, n):
        """A status's stacks after the hero's bonuses (Plus, Kindling, Venom, longer debuffs...)."""
        m = self.mods(h)
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
        return n

    def _op_status(self, c, op, targets):
        s = op["s"]
        for t in targets:
            foe = t if isinstance(t, dict) else None
            if not self.op_gate(c, op, foe):
                continue
            n = self.status_amount(c.h, c.a, s, amt(op["n"], self.env(c.h, c.a, c.dice, foe)))
            if foe is None:
                st = self.hs(t[1])["st"]
                st[s] = max(st.get(s, 0), n) if s in ("riposte", "thorns", "dodge", "crescendo") else st.get(s, 0) + n
                self.fx("st", to=f"h{t[1]}", s=s)
            elif t["hp"] > 0:
                if s == "doom":
                    t["st"]["doom"] = max(t["st"].get("doom", 0), n + c.plus)
                    t["st"]["doomt"] = 2
                elif s == "stun" and self.resist(t):
                    continue
                elif s in ONE_SHOT:
                    t["st"][s] = 1
                else:
                    t["st"][s] = t["st"].get(s, 0) + n
                self.fx("st", to=f"f{t['id']}", s=s)
                self.foe_status_by(t, s, c.h)

    def _op_flee(self, c, op, targets):
        c.x["fled"] = True
        hero = self.hero(c.h)
        hero["tile"], hero["afloat"] = hero["prev"], False
        self.fx("flee", h=c.h)
        self.say(f"{hero['name']} flees.")

    def _op_guard(self, c, op, targets):
        h = c.h
        for t in targets:
            if isinstance(t, tuple):
                # the first attack aimed at them swings to you, in plain sight; with none,
                # you take the next hit that lands on them
                if not self.retarget_intents(f"h{h}", frm=f"h{t[1]}", first_only=True):
                    self.s["fight"]["guard"][str(t[1])] = h
                self.fx("st", to=f"h{t[1]}", s="guarded")
                if t[1] != h:
                    self.cover(t[1])
                    if c.m.get("guard_share"):
                        st = self.hs(t[1])["st"]
                        st["armor"] = st.get("armor", 0) + c.m["guard_share"]
                        self.fx("armor", to=f"h{t[1]}", n=c.m["guard_share"])

    def _op_taunt(self, c, op, targets):
        h = c.h
        self.s["fight"]["taunt"] = h
        self.retarget_intents(f"h{h}")
        self.fx("st", to=f"h{h}", s="taunt")
        for y in self.actives():
            if y != h:
                self.cover(y)
                if c.m.get("guard_share"):
                    st = self.hs(y)["st"]
                    st["armor"] = st.get("armor", 0) + 2
                    self.fx("armor", to=f"h{y}", n=2)

    def _op_drag(self, c, op, targets):
        for t in targets:
            if not isinstance(t, tuple) and t["hp"] > 0 and not t["st"].get("root"):
                t["row"] = "front"
                self.fx("drag", to=f"f{t['id']}")

    def _op_lift(self, c, op, targets):
        n = self.op_amount(c, op)
        for t in targets:
            if isinstance(t, tuple):
                self.lift(t[1], n)

    def _op_cleanse(self, c, op, targets):
        for t in targets:
            if isinstance(t, tuple):
                st = self.hs(t[1])["st"]
                for d in DEBUFFS:
                    st.pop(d, None)
                self.fx("st", to=f"h{t[1]}", s="cleansed")

    def _op_sanct(self, c, op, targets):
        f = self.s["fight"]
        f["sanct"] += op["n"] + (1 if c.a["plus"] else 0)
        if c.m.get("aegis") and c.hit:
            f["aegis"] = max(f["aegis"], c.m["aegis"])
        self.fx("st", to="party", s="sanct")

    def _op_weaken(self, c, op, targets):
        n = self.op_amount(c, op)
        for t in targets:
            it = t.get("intent") if isinstance(t, dict) else None
            if it and it.get("dice") and it["k"] in ("attack", "all", "block", "guard", "heal"):
                it["bonus"] = it.get("bonus", 0) - n
                self.intent_numbers(it)
                self.fx("st", to=f"f{t['id']}", s="weakened")

    def _op_retarget(self, c, op, targets):
        for t in targets:
            it = t.get("intent") if isinstance(t, dict) else None
            if it and (it.get("tgt") or it.get("tgts")):
                old = it.get("tgt") or it["tgts"][0]
                new = self.foe_target(dict(it, tgt_kind="random"), exclude=old)
                if new is None and self.steeled(t):
                    self.resist(t)
                    continue
                if new is None:
                    t["intent"] = {"k": "dazed", "name": "Distracted", "by_hero": True}
                elif it.get("tgt"):
                    it["tgt"] = new
                else:
                    it["tgts"] = [new if u == old else u for u in it["tgts"]]
                self.fx("retarget", f=t["id"], to=new)
                self.fx("st", to=f"f{t['id']}", s="distracted")

    def _op_cancel(self, c, op, targets):
        for t in targets:
            if isinstance(t, dict) and t["hp"] > 0 and not self.resist(t):
                t["intent"] = {"k": "dazed", "name": "Lost its turn", "by_hero": True}
                self.fx("st", to=f"f{t['id']}", s="dazed")

    def _op_foresee(self, c, op, targets):
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

    def _op_steal(self, c, op, targets):
        for t in targets:
            it = t.get("intent") if isinstance(t, dict) else None
            if not it or not it.get("dice"):
                continue
            if len(it["dice"]) == 1 and self.steeled(t):
                self.resist(t)  # a Steeled enemy keeps its last die
                continue
            i = max(range(len(it["dice"])), key=lambda j: die_range(it["dice"][j]["faces"])[1])
            it["dice"].pop(i)
            if it.get("tgts") and it.get("each") and i < len(it["tgts"]):
                it["tgts"].pop(i)
            if not it["dice"]:
                t["intent"] = {"k": "dazed", "name": "Robbed blind", "by_hero": True}
            else:
                self.intent_numbers(it)
            self.fx("st", to=f"f{t['id']}", s="robbed")

    def _op_gold(self, c, op, targets):
        n = amt(op["amt"], {})
        self.hero(c.h)["gold"] += n
        self.fx("coins", h=c.h, n=n)

    def _op_strip(self, c, op, targets):
        n = self.op_amount(c, op)
        for t in targets:
            if isinstance(t, dict):
                t["st"]["armor"] = max(0, t["st"].get("armor", 0) - n)

    def _op_summon(self, c, op, targets):
        hp = amt(op["hp"], self.env(c.h, c.a, c.dice)) + c.plus if op.get("hp") else None
        self.summon(c.h, op["k"], hp)

    # ------------------------------------------------------------------ instant actions

    # ------------------------------------------------------------------ the Spellblade's Sigils and infusions

    def carve(self, fo, n):
        """Carve Sigils into an enemy (up to SIGIL_CAP)."""
        if n <= 0 or fo["hp"] <= 0:
            return
        was = fo["st"].get("sigil", 0)
        fo["st"]["sigil"] = min(C.SIGIL_CAP, was + n)
        if fo["st"]["sigil"] > was:
            self.fx("st", to=f"f{fo['id']}", s="sigil")

    def infuse(self, h, n, dmg, el):
        """Infuse a hero's blade: their next `n` melee hits deal +`dmg` and carry `el` (frost, shock,
        burn). Infusions add up to INFUSE_CAP hits; the bonus is the bigger, the element the newest."""
        x = self.hs(h)
        st = x["st"]
        old = x.get("inf", {}).get("dmg", 0) if st.get("infuse") else 0
        st["infuse"] = min(C.INFUSE_CAP, st.get("infuse", 0) + n)
        x["inf"] = {"dmg": max(dmg, old), "el": el}
        self.fx("st", to=f"h{h}", s="infused_" + el)

    def infuse_hit(self, h, t):
        """An infused melee hit lands: its element, a Sigil with Infused Steel, one hit used up."""
        x = self.hs(h)
        m = self.mods(h)
        el = x.get("inf", {}).get("el")
        if t["hp"] > 0 and el:
            s, n = INFUSE_STATUS[el]
            if s == "shock":
                t["st"]["shock"] = 1
            else:
                t["st"][s] = t["st"].get(s, 0) + self.status_amount(h, {"plus": False}, s, n)
            self.fx("st", to=f"f{t['id']}", s=s)
            self.foe_status_by(t, s, h)
        if t["hp"] > 0 and m.get("infused_carve"):
            self.carve(t, 1)
        if not m.get("covenant"):
            x["st"]["infuse"] -= 1
            if x["st"]["infuse"] <= 0:
                x["st"].pop("infuse", None)
                x.pop("inf", None)

    def burst(self, c, op, t, vals):
        """A Burst spends the target's Sigils: Detonate spills them on the others, Feedback Loop
        infuses the blade."""
        spent = t["st"].pop("sigil", 0)
        if not spent:
            return
        self.fx("st", to=f"f{t['id']}", s="burst")
        if op.get("spill"):
            for o in self.foes():
                if o is not t:
                    self.hurt_foe(o, op["spill"] * spent, c.h)
        if spent >= 3 and c.m.get("feedback_loop") and self.active(c.h):
            v = vals[0] if vals else 0
            self.infuse(c.h, 2, max(2, v // 2), element_of(v))

    def instant(self, h, a, dice, tgt):
        """Actions that set up dice take effect the moment they're placed: each op kind is an
        `_inst_<kind>` method below. Dice they don't keep in play are used up."""
        since = self.s["fxid"]
        x = self.hs(h)
        m = self.mods(h)
        c = Cast(h=h, a=a, dice=dice, tgt=tgt, x=x, m=m, keep=set(), extra=1 if m.get("second_verse") else 0,
                 plus=2 if a["plus"] else 0, other=int(tgt[1:]) if isinstance(tgt, str) and tgt.startswith("h") else None)
        for op in a["ops"]:
            handler = getattr(self, "_inst_" + op["op"], None)
            if handler:
                handler(c, op)
        for d in dice:
            if d["id"] not in c.keep and d in x["dice"]:
                d["used"] = True
        self.s["fight"]["done"].append({"h": h, "a": a["key"], "plus": a["plus"], "tgt": tgt, "hit": None,
                                        "vals": [num(d) for d in dice], "out": self.act_outcome(since)})
        self.fx("act", h=h, a=a["key"], tgt=tgt, instant=True)
        self.spite(a)
        self.after_action(h, a, tgt)

    def show_die(self, d, v, t):
        """A die rolled in the open while planning: it shows this face from now on."""
        d["v"], d["tag"] = v, t
        for k in ("sv", "stag", "hint"):
            d.pop(k, None)

    def _inst_setdie(self, c, op):
        d = c.dice[0]
        d["top"] = True
        if d.get("v") is not None and not d.get("rolled"):
            d["v"], d["tag"] = top_face(d["faces"]), None
        c.keep.add(d["id"])

    def _inst_bump(self, c, op):
        d = c.dice[0]
        d["bonus"] = d.get("bonus", 0) + amt(op["amt"], {}) + c.plus
        c.keep.add(d["id"])

    def _inst_selfdmg(self, c, op):
        hero = self.hero(c.h)
        n = min(amt(op["amt"], {}), hero["hp"] - 1)
        hero["hp"] -= n
        self.fx("dmg", to=f"h{c.h}", n=n, block=0)

    def _inst_loaded(self, c, op):
        g = "L" + c.dice[0]["id"]
        for d in c.dice:
            d["link"] = g
            c.keep.add(d["id"])

    def _inst_inspire(self, c, op):
        v = self.roll(c.h, c.dice[0])
        y = self.hs(c.other)
        y["inspire"] = y.get("inspire", 0) + max(2, v // 2) + c.extra + c.plus
        self.fx("st", to=f"h{c.other}", s="inspired")
        self.bolster(c, c.other)

    def _inst_chorus(self, c, op):
        """Rousing Chorus: every ally's next die rolls higher by half the die (at least 2)."""
        v = self.roll(c.h, c.dice[0])
        for y in self.actives():
            if y != c.h:
                x = self.hs(y)
                x["inspire"] = x.get("inspire", 0) + max(2, v // 2) + c.extra + c.plus
                self.fx("st", to=f"h{y}", s="inspired")
                self.bolster(c, y)

    def bolster(self, c, y):
        """Bolster: the Herald's help comes with Armor."""
        n = c.m.get("bolster", 0)
        if n and self.active(y):
            st = self.hs(y)["st"]
            st["armor"] = st.get("armor", 0) + n
            self.fx("armor", to=f"h{y}", n=n)

    def _inst_hymn(self, c, op):
        vals = [self.roll(c.h, d) for d in c.dice]
        f = self.s["fight"]
        f["hymn"] = f.get("hymn", 0) + 2 + (1 if len(set(vals)) == 1 else 0) + c.extra
        self.fx("st", to="party", s="hymn")

    def _inst_give(self, c, op):
        d = c.dice[0]
        c.x["dice"].remove(d)
        self.hs(c.other)["dice"].append(dict(d, id=f"g{d['id']}", src="gift", used=False,
                                             bonus=d.get("bonus", 0) + c.extra + op.get("bonus", 0)))
        c.keep.add(d["id"])
        self.bolster(c, c.other)

    def _inst_reroll_ally(self, c, op):
        y = self.hs(c.other)
        y["rr"] += 2 + (1 if c.a["plus"] else 0)
        y["inspire"] = y.get("inspire", 0) + 3 + c.extra
        self.fx("st", to=f"h{c.other}", s="rerolls")

    def _inst_flip(self, c, op):
        # Counterpoint: roll it in the open; a low roll turns to its opposite face
        d = c.dice[0]
        v, t = (d["v"], d.get("tag")) if d.get("v") is not None else self.raw_roll(c.h, d)
        nums = [face(f2)[0] for f2 in d["faces"] if face(f2)[0] is not None]
        lo, hi = min(nums), max(nums)
        if t not in ("S", "X", "W") and v is not None and v <= (lo + hi) / 2:
            v = lo + hi - v + 1
            self.fx("st", to=f"h{c.h}", s="flipped")
        self.show_die(d, v, t if t in ("S", "X", "W") else None)
        d.pop("fc", None)
        c.keep.add(d["id"])

    def _inst_split(self, c, op):
        d = c.dice[0]
        c.x["dice"].remove(d)
        half = max(2, top_face(d["faces"]) // 2 + 1)
        for _ in range(2):
            c.x["dice"].append(self.new_die(c.h, list(range(1, half + 1)), "split"))
        c.keep.add(d["id"])
        self.fx("st", to=f"h{c.h}", s="split")

    def _inst_merge(self, c, op):
        size = min(20, sum(top_face(d["faces"]) for d in c.dice))
        for d in c.dice:
            c.x["dice"].remove(d)
            c.keep.add(d["id"])
        c.x["dice"].append(self.new_die(c.h, list(range(1, size + 1)), "graft"))
        self.fx("st", to=f"h{c.h}", s="grafted")

    def _inst_second_opinion(self, c, op):
        hid = [d for d in self.hs(c.other)["dice"] if not d["used"] and d.get("v") is None and not d.get("fc")]
        if hid:
            d = max(hid, key=lambda d: top_face(d["faces"]))
            rolls = [self.raw_roll(c.other, d) for _ in range(3)]
            self.show_die(d, *max(rolls, key=lambda r: (r[1] not in ("X", "S"), r[0] or 0)))
            self.fx("st", to=f"h{c.other}", s="second_opinion")

    def _inst_transfusion(self, c, op):
        v = self.roll(c.h, c.dice[0])
        self.fight_heal(c.other, v + 2 + c.m.get("heal_bonus", 0) + c.plus, c.h)
        y = self.hs(c.other)
        y["inspire"] = y.get("inspire", 0) + 2 + c.extra
        self.fx("st", to=f"h{c.other}", s="inspired")

    def _inst_bottle(self, c, op):
        v = self.roll(c.h, c.dice[0])
        key = "big_potion" if v >= 5 else "potion"
        for _ in range(2 if c.m.get("philosopher") else 1):
            self.gain_item(c.h, key)

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


# An infusion's element by the die's number (Spellblade), and what each does to the enemy hit.
def element_of(v):
    return "frost" if v <= 2 else "shock" if v <= 4 else "burn"


INFUSE_STATUS = {"frost": ("weak", 1), "shock": ("shock", 1), "burn": ("burn", 2)}


def sigil_worth(e):
    """What the target's Sigils add to a Burst: 3 each, or 5 on a 1 or 2 with Quiet Glyph."""
    return e.get("sig", 0) * (5 if e.get("qg") else 3)
