"""Region quests, mixed into `Game` (the content is in content/quests.py).

Each drawn region (of the newer eight) gets a quest-giver: a `quest` place with `q` (the region key),
placed when the world is set up. Landing there offers the quest's first event; a choice with
`"quest": "start"` puts a trail in `s["quests"]` (kind "trail", next to the town jobs, so the quest
log, the map tag and the forecast show it) with a site somewhere in the region. Ending a turn on the
site offers that step's event; `"quest": "next"` (directly, or in a fight's `win`) moves the trail to
its next site, or finishes it. A trail has no deadline, and nothing fails it: a step turned down or a
fight lost leaves the site where it was.
"""

from . import world as Wd
from .content import archipelago as A


class Quests:
    def place_quests(self, rng):
        """A quest-giver in each drawn region that has a quest, on open land near its middle."""
        s = self.s
        w = s["world"]
        places = w["places"]
        for reg in self.regions():
            if reg not in A.QUESTS or any(p["kind"] == "quest" and p.get("q") == reg for p in places.values()):
                continue
            mine = [t for t in range(Wd.W * Wd.H) if w["reg"][t] == reg]
            free = [t for t in mine if self.quest_ground(t)
                    and all(not self.place(n) for n in Wd.neighbors(t))]
            if not free:
                continue
            mid = sorted(free, key=lambda t: sum(Wd.dist(t, x) for x in mine[::7]))
            t = rng.choice(mid[:max(1, len(mid) // 4)])
            places[str(t)] = {"kind": "quest", "q": reg, "name": A.QUESTS[reg]["giver"]}

    def quest_ground(self, t):
        """Open land a quest place or site can go on."""
        return self.terrain(t) in Wd.COST and self.terrain(t) not in ("town", "ice") and not self.place(t) \
            and not self.group_at(t) and str(t) not in self.s.get("lava", {})

    def trail(self, key):
        return next((q for q in self.s["quests"] if q["kind"] == "trail" and q["key"] == key and not q["done"]), None)

    def quest_land(self, h, t, p):
        """A hero ends a turn on a quest-giver: offer the quest, unless it's under way or done."""
        key = p["q"]
        if p.get("taken") or self.trail(key):
            return
        first = A.QUESTS[key]["steps"][0]
        if not any(d["type"] == "event" and d["key"] == first for d in self.s["pending"][str(h)]):
            self.push(h, {"type": "event", "key": first})

    def trail_land(self, h, q, t):
        """A hero on a trail's site: offer the step's event (once at a time)."""
        if q["tile"] != t or self.group_at(t):
            return
        ev = A.QUESTS[q["key"]]["steps"][q["step"]]
        if not any(d["type"] == "event" and d["key"] == ev for x in range(3) for d in self.s["pending"][str(x)]):
            self.push(h, {"type": "event", "key": ev})

    def quest_site(self, key, near):
        """Somewhere in the region for the next step: a few hexes on from `near` if it can be."""
        w = self.s["world"]
        cands = [t for t in range(Wd.W * Wd.H) if w["reg"][t] == key and self.quest_ground(t)]
        if not cands:
            cands = [t for t in Wd.within(near, 4) if self.quest_ground(t)] or [near]
        good = [t for t in cands if 3 <= Wd.dist(t, near) <= 7]
        return self.rng.choice(good or sorted(cands, key=lambda t: abs(Wd.dist(t, near) - 4))[:3])

    def quest_move(self, h, ev_key, how):
        """An outcome moved a quest on: "start" it, or take it to its "next" step (or finish it)."""
        s = self.s
        key = A.QUEST_OF.get(ev_key)
        if not key:
            return
        Q = A.QUESTS[key]
        at = self.hero(h)["tile"]
        if how == "start":
            if self.trail(key):
                return
            giver = next((int(t) for t, p in s["world"]["places"].items() if p["kind"] == "quest" and p.get("q") == key), at)
            if self.place(giver):
                self.place(giver)["taken"] = True
            s["jobid"] = s.get("jobid", 0) + 1
            site = self.quest_site(key, at)
            s["quests"].append({"id": s["jobid"], "kind": "trail", "key": key, "step": 1, "tile": site, "done": False, "failed": False,
                                "src": Q["name"], "src_tile": giver})
            self.reveal(site, 1)
            self.say(f"{self.hero(h)['name']} takes up a quest: {Q['name']}. Next: {Q['goals'][0]}.")
            self.fx("quest", h=h, key=key, tile=site)
            return
        q = self.trail(key)
        if not q:
            return
        q["step"] += 1
        if q["step"] >= len(Q["steps"]):
            q["done"] = True
            self.say(f"Quest complete: {Q['name']}!")
            self.fx("quest", h=h, key=key, done=True)
            return
        q["tile"] = self.quest_site(key, at)
        self.reveal(q["tile"], 1)
        self.say(f"{Q['name']}: next, {Q['goals'][q['step'] - 1]}.")
        self.fx("quest", h=h, key=key, tile=q["tile"])

