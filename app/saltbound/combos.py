"""Cross-hero combos (Covered, Pincer, Shatter, the Bell's crack, Wildfire) and Spiteful elites.
The numbers are in tuning.py, the words in COMBOS in classes.py. Mixed into `Game` through `Combat`."""

from .dice import num
from .tuning import BELL_CRACK, COVERED, PINCER, PINCER_MATCH, SHATTER, WILDFIRE


class Combos:
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
        for name, bonus in self.combo_peek(h, t, [num(d) for d in dice], used):
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

    def spite(self, a):
        """Spiteful elites gain might when a hero buffs, heals or shields."""
        if a.get("def") or a.get("instant") or a["tgt"] in ("ally", "other", "party"):
            for fo in self.foes():
                if fo.get("aff") == "spiteful":
                    fo["might"] += 1
                    self.fx("st", to=f"f{fo['id']}", s="spite")
