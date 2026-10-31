"""Balance analytics for Saltbound's simulator: what the bots did, and what it did to them.

`Collector(game, stats)` hooks one game's damage, healing and effect calls and credits each point to
whoever caused it: a hero's action, a summon, an item, an enemy, or a ticking status. `Stats` is a
plain nested dict of numbers (section -> key -> metric -> total), so runs from worker processes add
up with `merge`. `report(stats)` turns it into tables and a list of balance flags.
"""

from app.saltbound import classes as C
from app.saltbound.content import archipelago as A
from app.saltbound.content import items as I

AUTO = {"sic_em"}  # actions that happen by themselves each round, not placed with dice
RISKY = ("min", "max", "exact", "odd", "even", "sum_min", "pair", "or_face")


class Stats:
    def __init__(self, t=None):
        self.t = t or {}

    def add(self, sec, key, metric, v=1):
        d = self.t.setdefault(sec, {}).setdefault(key, {})
        d[metric] = d.get(metric, 0) + v

    def merge(self, other):
        for sec, keys in (other.t if isinstance(other, Stats) else other).items():
            for key, ms in keys.items():
                for m, v in ms.items():
                    self.add(sec, key, m, v)

    def get(self, sec, key, metric, default=0):
        return self.t.get(sec, {}).get(key, {}).get(metric, default)


class Collector:
    """Watches one game. Works by wrapping the game's own methods on the instance."""

    def __init__(self, g, stats):
        self.g, self.st = g, stats
        self.ctx = ("tick",)
        self.fight = None
        for name in ("fx", "start_fight", "finish_fight", "hurt_foe", "hurt_hero", "hurt_unit", "fight_heal",
                     "fight_use", "new_round", "end_round"):
            setattr(g, name, getattr(self, "w_" + name)(getattr(g, name)))

    def cls(self, h):
        return self.g.hero(h)["cls"]

    def src(self):
        """The stats key that the current damage or healing belongs to, and the hero behind it."""
        c = self.ctx
        if c[0] == "act":
            return f"{self.cls(c[1])}:{c[2]}", c[1]
        if c[0] == "summon":
            return f"{self.cls(c[1])}:summon:{c[2]}", c[1]
        if c[0] == "item":
            return f"item:{c[2]}", c[1]
        if c[0] == "roll":
            return f"{self.cls(c[1])}:dice faces", c[1]  # shield faces' Armor, skull faces' damage
        return None, None

    # ---- the event stream sets who is acting
    def w_fx(self, orig):
        def fx(kind_, **kw):
            orig(kind_, **kw)
            g, st = self.g, self.st
            if kind_ == "act" and not kw.get("echo"):
                h, a = kw["h"], kw["a"]
                auto = a in AUTO and "hit" not in kw  # the pet strike shares Sic 'Em's name but rolls nothing
                if auto:
                    a = "pet strike"
                self.ctx = ("act", h, a)
                key = f"{self.cls(h)}:{a}"
                st.add("actions", key, "auto" if auto else "uses")
                try:
                    req = g.action_def(h, a).get("req", {})
                except KeyError:
                    req = {}
                if any(k in req for k in RISKY):
                    st.add("actions", key, "risky")
                    st.add("actions", key, "hits" if kw.get("hit") else "misses")
            elif kind_ == "act":
                self.ctx = ("act", kw["h"], kw["a"])
            elif kind_ == "sact":
                al = g.ally(kw["s"])
                self.ctx = ("summon", al["owner"], al["k"]) if al else ("tick",)
            elif kind_ == "fact":
                fo = g.foe(kw["f"])
                self.ctx = ("foe", fo["k"]) if fo else ("tick",)
                if fo:
                    st.add("foes", fo["k"], "intents:" + str(kw.get("ik")))
            elif kind_ == "roll":
                self.ctx = ("roll", kw["h"])
            elif kind_ == "armor" and str(kw.get("to", "")).startswith("h"):
                key, _ = self.src()
                if key:
                    st.add("actions" if not key.startswith("item:") else "consumables", key, "armor", kw["n"])
            elif kind_ == "dmg" and str(kw.get("to", "")).startswith("h") and kw.get("block"):
                st.add("classes", self.cls(int(kw["to"][1:])), "blocked", kw["block"])
            elif kind_ == "down":
                h = int(kw["to"][1:])
                st.add("classes", self.cls(h), "downs")
                if self.ctx[0] == "foe":
                    st.add("foes", self.ctx[1], "downs")
                if self.fight:
                    self.fight["downs"] += 1
            elif kind_ == "dead":
                st.add("classes", self.cls(kw["h"]), "deaths")
            elif kind_ == "summon" and "f" in kw:
                fo = g.foe(kw["f"])
                if fo:
                    st.add("foes", fo["k"], "seen")
            elif kind_ == "round" and g.s["fight"]:
                for h in g.actives():
                    st.add("classes", self.cls(h), "rounds")
        return fx

    def w_new_round(self, orig):
        def new_round():
            self.ctx = ("tick",)
            return orig()
        return new_round

    def w_end_round(self, orig):
        def end_round():
            self.ctx = ("tick",)
            return orig()
        return end_round

    # ---- fights
    def w_start_fight(self, orig):
        def start_fight(spec):
            self.ctx = ("tick",)
            r = orig(spec)
            g = self.g
            f = g.s["fight"]
            if f:
                self.fight = {"f": f, "hp0": {h: g.hero(h)["hp"] for h in f["heroes"]},
                              "max": sum(g.maxhp(h) for h in f["heroes"]), "downs": 0,
                              "sig": f["kind"] + ": " + " + ".join(sorted(A.FOES[fo["k"]]["name"] for fo in f["foes"]))}
                for fo in f["foes"]:
                    self.st.add("foes", fo["k"], "seen")
            return r
        return start_fight

    def w_finish_fight(self, orig):
        def finish_fight(result):
            g, st, fi = self.g, self.st, self.fight
            if fi and g.s["fight"] is fi["f"]:
                f = fi["f"]
                lost = sum(max(0, hp0 - g.hero(h)["hp"]) for h, hp0 in fi["hp0"].items()) / max(1, fi["max"])
                for sec, key in (("fights", f["kind"]), ("encounters", fi["sig"])):
                    st.add(sec, key, "n")
                    st.add(sec, key, "won", result == "won")
                    st.add(sec, key, "rounds", f["round"])
                    st.add(sec, key, "hplost", lost)
                    st.add(sec, key, "downs", fi["downs"])
                for fo in f["foes"]:
                    if fo["hp"] > 0:
                        st.add("foes", fo["k"], "survived")
            self.fight = None
            self.ctx = ("tick",)
            return orig(result)
        return finish_fight

    # ---- damage and healing
    def w_hurt_foe(self, orig):
        def hurt_foe(fo, n, h, *a, **kw):
            before = fo["hp"]
            r = orig(fo, n, h, *a, **kw)
            dealt = min(r, max(0, before))
            died = before > 0 and fo["hp"] <= 0
            st = self.st
            st.add("foes", fo["k"], "taken", dealt)
            if died:
                st.add("foes", fo["k"], "killed")
            key, _ = self.src()
            if self.ctx[0] == "foe" and h is not None:
                key = f"{self.cls(h)}:retaliation"
            elif key is None:
                key = f"{self.cls(h)}:passive" if h is not None else "status ticks"
            sec = "consumables" if key.startswith("item:") else "sources" if key == "status ticks" else "actions"
            st.add(sec, key, "dmg", dealt)
            st.add(sec, key, "overkill", r - dealt)
            if died:
                st.add(sec, key, "kills")
            if h is not None:
                st.add("classes", self.cls(h), "dmg", dealt)
            return r
        return hurt_foe

    def w_hurt_hero(self, orig):
        def hurt_hero(h, n, fo, *a, **kw):
            g = self.g
            before = {y: g.hero(y)["hp"] for y in range(3)}
            r = orig(h, n, fo, *a, **kw)
            for y, hp in before.items():
                lost = max(0, hp - max(0, g.hero(y)["hp"]))
                if not lost:
                    continue
                self.st.add("classes", self.cls(y), "taken", lost)
                if fo is not None:
                    self.st.add("foes", fo["k"], "dealt", lost)
                else:
                    key, _ = self.src()
                    self.st.add("sources", key if key and self.ctx[0] == "roll" else "statuses on heroes", "dmg", lost)
            return r
        return hurt_hero

    def w_hurt_unit(self, orig):
        def hurt_unit(uid, n, fo, *a, **kw):
            r = orig(uid, n, fo, *a, **kw)
            if not uid.startswith("h") and fo is not None:
                self.st.add("foes", fo["k"], "dealt_summons", r)
            return r
        return hurt_unit

    def w_fight_heal(self, orig):
        def fight_heal(h, n, by):
            got = orig(h, n, by)
            key, who = self.src()
            st = self.st
            if key and by is not None and by == who:
                sec = "consumables" if key.startswith("item:") else "actions"
                st.add(sec, key, "heal", got)
                st.add(sec, key, "overheal", max(0, n - got))
            elif got:
                st.add("sources", "regen and passives", "heal", got)
            if by is not None:
                st.add("classes", self.cls(by), "heal", got)
            return got
        return fight_heal

    def w_fight_use(self, orig):
        def fight_use(h, i, tgt):
            key = self.g.hero(h)["bag"][i]
            self.st.add("consumables", f"item:{key}", "uses")
            old, self.ctx = self.ctx, ("item", h, key)
            try:
                return orig(h, i, tgt)
            finally:
                self.ctx = old
        return fight_use


# ---------------------------------------------------------------------- run-level records

def record_choice(stats, g, h, dialog, n, run):
    """A bot's pick from a level-up, loot or event dialog."""
    cls = g.hero(h)["cls"]
    if dialog["type"] == "level":
        for o in dialog["opts"]:
            stats.add("picks", f"{cls}:{o}", "offered")
        if 0 <= n < len(dialog["opts"]):
            stats.add("picks", f"{cls}:{dialog['opts'][n]}", "taken")
            run["picks"].append(f"{cls}:{dialog['opts'][n]}")
    elif dialog["type"] == "loot":
        for o in dialog["opts"]:
            stats.add("loot", o, "offered")
        if 0 <= n < len(dialog["opts"]):
            stats.add("loot", dialog["opts"][n], "taken")
    elif dialog["type"] == "event":
        stats.add("events", f"{dialog['key']}:{n}", "n")


def record_run(stats, g, res, run):
    won = res == "won"
    s = g.s
    combo = "+".join(sorted(h["cls"] for h in s["heroes"]))
    stats.add("runs", "all", "n")
    stats.add("runs", "all", res)
    stats.add("runs", "all", "turns", s["turn"])
    stats.add("runs", "all", "level", s["level"])
    stats.add("runs", "all", "rises", s["rises"])
    stats.add("runs", "all", "cleared", len(s["cleared"]))
    stats.add("combos", combo, "n")
    stats.add("combos", combo, "won", won)
    for hero in s["heroes"]:
        stats.add("classes", hero["cls"], "runs")
        stats.add("classes", hero["cls"], "wins", won)
        for key in hero["equip"].values():
            if key:
                stats.add("gear", key, "runs")
                stats.add("gear", key, "wins", won)
    for p in run["picks"]:
        stats.add("picks", p, "won", won)
    if res == "lost":
        stats.add("runs", "lost at turn", str(10 * (s["turn"] // 10)) + "s")
        stats.add("runs", "lost with regions cleared", str(len(s["cleared"])))


# ---------------------------------------------------------------------- the report

def _pct(a, b):
    return f"{100 * a / b:5.1f}%" if b else "    -"


def _table(title, head, rows, out):
    if not rows:
        return
    out.append("")
    out.append(title)
    widths = [max(len(str(r[i])) for r in [head] + rows) for i in range(len(head))]
    fmt = lambda r: "  " + "  ".join(str(c).ljust(w) if i == 0 else str(c).rjust(w) for i, (c, w) in enumerate(zip(r, widths)))
    out.append(fmt(head))
    out.extend(fmt(r) for r in rows)


def _name(key):
    """'arcanist:fireball' -> 'Fireball'; summons and others as they are."""
    k = key.split(":", 1)[1] if ":" in key else key
    base = k.rstrip("+")
    d = C.ACTIONS.get(base) or I.WEAPON_ACTIONS.get(base) or C.PASSIVES.get(base)
    return (d["name"] + ("+" if k.endswith("+") else "")) if d else k


def report(stats, top=12):
    t = stats.t
    out = []
    flags = []
    runs = t.get("runs", {}).get("all", {})
    n = runs.get("n", 0)
    if not n:
        return "No runs."
    wins = runs.get("won", 0)
    base_wr = wins / n
    out.append(f"{n} runs: won {wins} ({_pct(wins, n).strip()}), lost {runs.get('lost', 0)}"
               + "".join(f", {k} {runs[k]}" for k in ("stuck", "limit") if runs.get(k)))
    out.append(f"  avg turn {runs['turns'] / n:.1f}, level {runs['level'] / n:.1f}, sea rises {runs['rises'] / n:.1f}, "
               f"regions cleared {runs['cleared'] / n:.2f}")
    when = t.get("runs", {}).get("lost at turn", {})
    if when:
        out.append("  losses by turn: " + ", ".join(f"{k} {v}" for k, v in sorted(when.items(), key=lambda kv: int(kv[0][:-1]))))
    reg = t.get("runs", {}).get("lost with regions cleared", {})
    if reg:
        out.append("  losses by regions cleared: " + ", ".join(f"{k}: {v}" for k, v in sorted(reg.items())))

    # classes
    rows = []
    for cls, d in sorted(t.get("classes", {}).items(), key=lambda kv: -kv[1].get("wins", 0) / max(1, kv[1].get("runs", 1))):
        r = max(1, d.get("rounds", 0))
        wr = d.get("wins", 0) / max(1, d.get("runs", 0))
        rows.append([C.CLASSES[cls]["name"], d.get("runs", 0), _pct(d.get("wins", 0), d.get("runs", 0)),
                     f"{d.get('dmg', 0) / r:.1f}", f"{d.get('heal', 0) / r:.1f}", f"{d.get('blocked', 0) / r:.1f}",
                     f"{d.get('taken', 0) / r:.1f}", f"{d.get('downs', 0) / max(1, d.get('runs', 0)):.2f}",
                     f"{d.get('deaths', 0) / max(1, d.get('runs', 0)):.2f}"])
        if d.get("runs", 0) >= 10 and abs(wr - base_wr) > 0.12:
            flags.append(f"{C.CLASSES[cls]['name']} wins {100 * wr:.0f}% of its runs vs {100 * base_wr:.0f}% overall.")
    _table("Classes (per fight round: damage, healing, armor blocked, damage taken; per run: downs, deaths)",
           ["class", "runs", "win", "dmg", "heal", "block", "taken", "downs", "deaths"], rows, out)

    combos = sorted(((k, d) for k, d in t.get("combos", {}).items() if d["n"] >= 2), key=lambda kv: -kv[1]["won"] / kv[1]["n"])
    if len(combos) >= 4:
        pick = combos[:5] + [c for c in combos[-5:] if c not in combos[:5]]
        _table("Parties (best and worst, at least 2 runs)", ["party", "runs", "win"],
               [[k.replace("+", ", "), d["n"], _pct(d["won"], d["n"])] for k, d in pick], out)

    # fights
    rows = []
    for kind, d in sorted(t.get("fights", {}).items(), key=lambda kv: -kv[1]["n"]):
        rows.append([kind, d["n"], _pct(d["won"], d["n"]), f"{d['rounds'] / d['n']:.1f}",
                     f"{100 * d['hplost'] / d['n']:.0f}%", f"{d['downs'] / d['n']:.2f}"])
    _table("Fights by kind (party HP lost is net of healing, as a share of the party's max HP)",
           ["kind", "n", "won", "rounds", "HP lost", "downs"], rows, out)
    enc = [(k, d) for k, d in t.get("encounters", {}).items() if d["n"] >= 3]
    enc.sort(key=lambda kv: -(kv[1]["hplost"] / kv[1]["n"] + (1 - kv[1]["won"] / kv[1]["n"])))
    _table("Hardest encounters (at least 3 fights)", ["encounter", "n", "won", "rounds", "HP lost", "downs"],
           [[k[:70], d["n"], _pct(d["won"], d["n"]), f"{d['rounds'] / d['n']:.1f}", f"{100 * d['hplost'] / d['n']:.0f}%",
             f"{d['downs'] / d['n']:.2f}"] for k, d in enc[:top]], out)
    for k, d in enc:
        if d["n"] >= 5 and d["won"] / d["n"] < 0.7 and not k.startswith("boss"):
            flags.append(f"{k} is won only {100 * d['won'] / d['n']:.0f}% of the time ({d['n']} fights).")

    # foes
    foes = [(k, d) for k, d in t.get("foes", {}).items() if d.get("seen", 0) >= 3]
    foes.sort(key=lambda kv: -kv[1].get("dealt", 0) / kv[1]["seen"])
    per = sorted(d.get("dealt", 0) / d["seen"] for _, d in foes)
    median = per[len(per) // 2] if per else 0
    rows = []
    for k, d in foes:
        dmg = d.get("dealt", 0) / d["seen"]
        rows.append([A.FOES[k]["name"], d["seen"], f"{dmg:.1f}", f"{d.get('dealt_summons', 0) / d['seen']:.1f}",
                     f"{d.get('downs', 0) / d['seen']:.2f}", _pct(d.get("killed", 0), d["seen"]),
                     f"{d.get('dealt', 0) / max(1, A.FOES[k]['hp']):.1f}"])
        if median and dmg > 2.2 * median and d["seen"] >= 8 and not A.FOES[k].get("boss"):
            flags.append(f"{A.FOES[k]['name']} deals {dmg:.1f} per fight, over twice the median enemy ({median:.1f}).")
    _table("Enemies (per appearance: damage to heroes and to summons, downs caused; killed share; damage per base HP)",
           ["enemy", "seen", "dmg", "summons", "downs", "killed", "dmg/hp"], rows, out)

    # actions, per class
    acts = t.get("actions", {})
    by_cls = {}
    for key, d in acts.items():
        by_cls.setdefault(key.split(":", 1)[0], []).append((key, d))
    for cls in sorted(by_cls):
        items = by_cls[cls]
        total = sum(d.get("uses", 0) for _, d in items) or 1
        rows = []
        for key, d in sorted(items, key=lambda kv: -(kv[1].get("uses", 0) * 1000 + kv[1].get("dmg", 0))):
            if not any(d.get(m) for m in ("uses", "auto", "dmg", "heal", "armor")):
                continue
            u = d.get("uses", 0) or d.get("auto", 0)
            per_use = lambda m: (f"{d.get(m, 0) / u:.1f}" if u else f"{d[m]} total") if d.get(m) else ""
            hit = _pct(d.get("hits", 0), d.get("risky", 0)) if d.get("risky") else ""
            rows.append([_name(key) + (" (auto)" if d.get("auto") else ""), u, _pct(u, total) if d.get("uses") else "", hit, per_use("dmg"), per_use("heal"), per_use("armor"),
                         d.get("kills", ""), f"{100 * d.get('overkill', 0) / max(1, d.get('dmg', 0) + d.get('overkill', 0)):.0f}%"
                         if d.get("dmg") else "", d.get("dmg", "") if not u else ""])
            if d.get("risky", 0) >= 20 and d.get("hits", 0) / d["risky"] < 0.4:
                flags.append(f"{C.CLASSES[cls]['name']}'s {_name(key)} hits only {100 * d['hits'] / d['risky']:.0f}% of the time.")
            if u and total >= 150 and u / total > 0.45 and not key.endswith((":shift",)):
                flags.append(f"{C.CLASSES[cls]['name']} spends {100 * u / total:.0f}% of its actions on {_name(key)}.")
        if cls in C.CLASSES:
            for key in C.CLASSES[cls]["start"]:
                if f"{cls}:{key}" not in acts and key not in C.GENERIC and total >= 150:
                    flags.append(f"{C.CLASSES[cls]['name']} never used its starting action {_name(key)}.")
        _table(f"{C.CLASSES[cls]['name'] if cls in C.CLASSES else cls}: actions", ["action", "uses", "share", "hit",
               "dmg/use", "heal/use", "armor/use", "kills", "overkill", "total dmg"], rows, out)

    # level-up picks
    picks = t.get("picks", {})
    rows = []
    for key, d in sorted(picks.items(), key=lambda kv: (kv[0].split(":")[0], -kv[1].get("taken", 0))):
        if d.get("offered", 0) < 4:
            continue
        cls = key.split(":")[0]
        cd = t.get("classes", {}).get(cls, {})
        cwr = cd.get("wins", 0) / max(1, cd.get("runs", 0))
        wr = d.get("won", 0) / d["taken"] if d.get("taken") else None
        rows.append([f"{C.CLASSES[cls]['name']}: {_name(key)}", d["offered"], _pct(d.get("taken", 0), d["offered"]),
                     _pct(d.get("won", 0), d.get("taken", 0)) if d.get("taken") else "", f"{100 * (wr - cwr):+.0f}" if wr is not None else ""])
        if wr is not None and d["taken"] >= 12 and abs(wr - cwr) > 0.18:
            flags.append(f"Runs where {C.CLASSES[cls]['name']} took {_name(key)} win {100 * wr:.0f}% vs {100 * cwr:.0f}% for the class.")
    _table("Level-up picks (taken: how often the bot chose it; won: runs that took it; vs class: points above the class's win rate)",
           ["pick", "offered", "taken", "won", "vs class"], rows, out)

    # gear and consumables
    gear = [(k, d) for k, d in t.get("gear", {}).items() if d["runs"] >= 4]
    gear.sort(key=lambda kv: -kv[1]["wins"] / kv[1]["runs"])
    _table("Gear worn at the end of a run (at least 4 runs)", ["item", "rarity", "runs", "won"],
           [[I.ITEMS[k]["name"], I.ITEMS[k]["rarity"], d["runs"], _pct(d["wins"], d["runs"])] for k, d in gear], out)
    cons = t.get("consumables", {})
    _table("Consumables used in fights", ["item", "uses", "dmg", "heal", "armor"],
           [[I.ITEMS[k[5:]]["name"], d.get("uses", 0), d.get("dmg", ""), d.get("heal", ""), d.get("armor", "")]
            for k, d in sorted(cons.items(), key=lambda kv: -kv[1].get("uses", 0))], out)
    src = t.get("sources", {})
    _table("Other sources", ["source", "dmg", "heal"],
           [[k if ":" not in k else f"{C.CLASSES[k.split(':')[0]]['name']} {k.split(':', 1)[1]}", d.get("dmg", ""), d.get("heal", "")]
            for k, d in sorted(src.items())], out)

    out.append("")
    out.append("Balance flags")
    out.extend(f"  - {f}" for f in flags) if flags else out.append("  none")
    return "\n".join(out)
