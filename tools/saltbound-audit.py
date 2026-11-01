"""Saved runs at moments worth looking at, for checking the UI (tools/saltbound-audit.js).

    python3 tools/saltbound-audit.py [scenario ...]

Plays runs with the bots until a scenario's moment (hero 0 choosing loot, levelling up, at an
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
    "level": lambda g: pending(g, "level"),
    "event": lambda g: pending(g, "event"),
    "fight": lambda g: g.s["phase"] == "fight" and 0 in g.s["fight"]["heroes"] and g.s["fight"]["round"] >= 2
    and not g.s["pending"]["0"],
    "boss": lambda g: g.s["phase"] == "fight" and g.s["fight"]["kind"] == "boss",
    "fork": lambda g: g.s["phase"] == "fork" and 0 in g.s["fork"]["heroes"],
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
        S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
        print(f"{name}: saved (seed {seed}, turn {g.s['turn']}, phase {g.s['phase']})")


if __name__ == "__main__":
    main()
