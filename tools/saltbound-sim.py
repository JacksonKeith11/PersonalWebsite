"""Plays whole Saltbound runs with bots on the server's own rules, for balance and save checks.

    python3 tools/saltbound-sim.py [runs] [difficulty] [--classes a,b,c] [--saves]

Reports wins, losses and why, run length in map turns, the party's level, and how many runs got
stuck. With --saves, every run is also saved and loaded (through JSON) after every action, and must
finish exactly as the same run played straight through.
"""

import json
import os
import sys
from collections import Counter
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.saltbound import bot, game  # noqa: E402
from app.saltbound.classes import CLASSES  # noqa: E402
from app.saltbound.combat import Invalid  # noqa: E402

FALLBACK = {"plan": {"t": "ready"}, "fight": {"t": "fready"}}


def play(seed, classes, diff, roundtrip=False, limit=20000):
    g = game.Game.new(seed, classes, diff)
    steps = 0
    while g.s["phase"] != "end" and steps < limit:
        waiting = g.waiting()
        if not waiting:
            # dead heroes with spirit dice, or nothing to do: should never happen
            return g, steps, "stuck"
        moved = False
        for h in waiting:
            msg = bot.decide(g, h)
            if msg is None:
                continue
            try:
                g.act(h, msg)
            except Invalid:
                fb = dict(FALLBACK.get(g.s["phase"], {"t": "ready"}))
                if g.s["pending"][str(h)]:
                    fb = {"t": "choose", "n": -1 if g.s["pending"][str(h)][0]["type"] == "loot" else 0}
                try:
                    g.act(h, fb)
                except Invalid:
                    continue
            moved = True
            steps += 1
            if roundtrip:
                g = game.Game(json.loads(json.dumps(g.s)))
            break
        if not moved:
            return g, steps, "stuck"
    return g, steps, g.s["result"] or "limit"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    runs = int(args[0]) if args else 20
    diff = args[1] if len(args) > 1 else "normal"
    picks = None
    saves = "--saves" in sys.argv
    for a in sys.argv[1:]:
        if a.startswith("--classes"):
            picks = [a.split("=", 1)[1].split(",")]
    combos = picks or [list(c) for c in combinations(sorted(CLASSES), 3)]
    results, turns, levels, causes = Counter(), [], [], Counter()
    for i in range(runs):
        cls = combos[i % len(combos)]
        g, steps, res = play(1000 + i, cls, diff)
        results[res] += 1
        turns.append(g.s["turn"])
        levels.append(g.s["level"])
        if res == "lost":
            causes["flood" if g.s["rises"] >= game.LOSS_RISE else "party fell"] += 1
        if res in ("stuck", "limit"):
            print(f"  seed {1000 + i} {cls}: {res} after {steps} steps in phase {g.s['phase']}, turn {g.s['turn']}")
        if saves:
            g2, _, res2 = play(1000 + i, cls, diff, roundtrip=True)
            if json.dumps(g.s, sort_keys=True) != json.dumps(g2.s, sort_keys=True):
                print(f"  seed {1000 + i}: SAVE ROUND-TRIP DIFFERS ({res} vs {res2})")
    n = max(1, runs)
    print(f"{runs} runs on {diff}: " + ", ".join(f"{k} {v}" for k, v in results.most_common()))
    if causes:
        print("  losses: " + ", ".join(f"{k} {v}" for k, v in causes.items()))
    print(f"  turns: avg {sum(turns) / n:.1f}, min {min(turns)}, max {max(turns)}; level avg {sum(levels) / n:.1f}")


if __name__ == "__main__":
    main()
