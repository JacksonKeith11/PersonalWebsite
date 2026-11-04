"""Saved runs at moments worth looking at, for checking the UI (tools/saltbound-audit.js).

    python3 tools/saltbound-audit.py [scenario ...]

Plays runs with the bots until a scenario's moment (hero 0 choosing loot or claiming from a fight's shared pool, levelling up, at an
event, in a fight, a boss fight, the end of a run...), then saves it to the server's database
for the browser token "audit", titled "audit: <scenario>". Hero 0 is left to the browser.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.saltbound import bot, game  # noqa: E402
from app.saltbound import save as S  # noqa: E402
from app.saltbound.combat import Invalid  # noqa: E402

PARTY = ["vanguard", "arcanist", "mender"]


def pending(g, kind):
    q = g.s["pending"]["0"]
    return bool(q) and q[0]["type"] == kind


SCENARIOS = {
    "start": lambda g: True,
    "loot": lambda g: pending(g, "loot"),
    "pool": lambda g: pending(g, "pool") and len(g.s["pools"][str(g.s["pending"]["0"][0]["id"])]["heroes"]) > 1,
    "level": lambda g: pending(g, "level"),
    "results": lambda g: len({d["type"] for d in g.s["pending"]["0"]}) >= 2,
    "event": lambda g: pending(g, "event"),
    "fight": lambda g: g.s["phase"] == "fight" and 0 in g.s["fight"]["heroes"] and g.s["fight"]["round"] >= 2
    and not g.s["pending"]["0"],
    "boss": lambda g: g.s["phase"] == "fight" and g.s["fight"]["kind"] == "boss",
    "fork": lambda g: g.s["phase"] == "fork" and 0 in g.s["fork"]["heroes"],
    # the overworld's choices
    "opp": lambda g: g.s["phase"] == "plan" and g.s.get("opps") and not g.s["pending"]["0"] and g.s["turn"] > 5,
    "trade": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"]
    and (g.place(g.hero(0)["tile"]) or {}).get("spec") in ("smith", "temple", "cartographer"),
    "garrison": lambda g: g.s["phase"] == "fork" and 0 in g.s["fork"]["heroes"] and (g.s["fork"].get("garrison") or {}).get("foes"),
    "board": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"]
    and len((g.place(g.hero(0)["tile"]) or {}).get("jobs") or []) == 2 and not g.place(g.hero(0)["tile"]).get("quest_taken"),
    "job": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"]
    and any(q["kind"] in ("bounty", "salvage") and not q["done"] and not q.get("failed") for q in g.s["quests"]),
    # the turn after the tide rose and landed enemies
    "tide": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"] and (g.s["turn"] - 1) % g.diff()["rise"] == 0
    and any(n.get("g") is not None for n in g.s.get("tidenews", [])),
    # the sea, raids and the weather
    "raid": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"]
    and any(x.get("raid") and not x.get("occupy") for x in g.s["groups"]) and g.s.get("squalls"),
    "occupied": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"] and any(x.get("occupy") for x in g.s["groups"]),
    "seafight": lambda g: g.s["phase"] == "fight" and 0 in g.s["fight"]["heroes"] and not g.s["pending"]["0"]
    and g.s["world"]["elev"][g.s["fight"]["tile"]] <= g.s["sea"],
    "ground": lambda g: g.s["phase"] == "fight" and 0 in g.s["fight"]["heroes"] and not g.s["pending"]["0"]
    and g.s["fight"].get("ground") and g.s["fight"]["round"] == 1,
    # an ally's event, for two players (tools/saltbound-mp.js events): set up in main()
    "partyevent": lambda g: g.s["phase"] == "plan" and g.s["turn"] >= 3 and not any(g.s["pending"].values()),
    "won": lambda g: g.s["phase"] == "end" and g.s["result"] == "won",
    "lost": lambda g: g.s["phase"] == "end" and g.s["result"] == "lost",
}


def run_until(cond, seed, limit=20000):
    g = game.Game.new(seed, PARTY, "normal")
    for _ in range(limit):
        if cond(g):
            return g
        if g.s["phase"] == "end":
            return None
        moved = False
        for h in bot.order(g, g.waiting()):
            msg = bot.decide(g, h)
            if msg is None:
                continue
            try:
                g.act(h, msg)
            except Invalid:
                try:
                    g.act(h, {"t": "fready"} if g.s["phase"] == "fight" else {"t": "ready"})
                except Invalid:
                    continue
            moved = True
            break
        if not moved:
            return None
    return None


def main():
    names = sys.argv[1:] or list(SCENARIOS)
    for name in names:
        g = None
        for seed in range(500, 560):
            g = run_until(SCENARIOS[name], seed)
            if g:
                break
        if not g:
            print(f"{name}: not reached")
            continue
        if name == "loot":
            # show off the rarities
            g.s["pending"]["0"][0]["opts"] = ["crownbreaker", "storm_glass", "coral_blade"]
        if name == "partyevent":
            # everyone on one hex, and hero 1 (the second player's) at an event with a party check
            for y in (0, 2):
                g.hero(y)["tile"], g.hero(y)["afloat"] = g.hero(1)["tile"], g.hero(1)["afloat"]
            g.s["pending"]["1"] = [{"type": "event", "key": "stuck_skiff"}]
            g.s["plans"] = {str(y): {"path": [], "ready": False, "rest": False} for y in range(3)}
        S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
        print(f"{name}: saved (seed {seed}, turn {g.s['turn']}, phase {g.s['phase']})")


if __name__ == "__main__":
    main()
