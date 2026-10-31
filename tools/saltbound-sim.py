"""Plays whole Saltbound runs with bots on the server's own rules, for balance and save checks.

    python3 tools/saltbound-sim.py [runs] [difficulty] [--classes=a,b,c] [--saves] [--report]
                                   [--json=out.json] [--jobs=N] [--seed=1000]

Prints wins, losses and why, run length in map turns, the party's level, and any runs that got
stuck. With --report it also prints the balance analytics from tools/saltbound_stats.py: class win
rates and output per round, fights and the hardest encounters, enemies by damage dealt, every
class's actions (use share, hit rate, damage, healing, Armor, kills, overkill), level-up picks
against win rate, gear, consumables, and a list of balance flags. --json writes the raw numbers.
Runs are spread over --jobs worker processes (all cores by default).

With --saves, every run is also saved and loaded (through JSON) after every action, and must finish
exactly as the same run played straight through.
"""

import json
import os
import random
import sys
from collections import Counter
from itertools import combinations
from multiprocessing import Pool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from app.saltbound import bot, game  # noqa: E402
from app.saltbound.classes import CLASSES  # noqa: E402
from app.saltbound.combat import Invalid  # noqa: E402
import saltbound_stats as SS  # noqa: E402

FALLBACK = {"plan": {"t": "ready"}, "fight": {"t": "fready"}}


def play(seed, classes, diff, roundtrip=False, limit=20000, stats=None):
    g = game.Game.new(seed, classes, diff)
    run = {"picks": []}
    if stats is not None:
        SS.Collector(g, stats)
    steps = 0
    while g.s["phase"] != "end" and steps < limit:
        waiting = g.waiting()
        if not waiting:
            # dead heroes with spirit dice, or nothing to do: should never happen
            return g, steps, "stuck", run
        moved = False
        for h in waiting:
            msg = bot.decide(g, h)
            if msg is None:
                continue
            q = g.s["pending"][str(h)]
            dialog = q[0] if q and msg.get("t") == "choose" else None
            try:
                g.act(h, msg)
                if dialog and stats is not None:
                    SS.record_choice(stats, g, h, dialog, msg["n"], run)
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
            return g, steps, "stuck", run
    return g, steps, g.s["result"] or "limit", run


def one(job):
    """A worker's run: the summary line's numbers, the analytics, and any save mismatch."""
    seed, cls, diff, saves = job
    stats = SS.Stats()
    g, steps, res, run = play(seed, cls, diff, stats=stats)
    SS.record_run(stats, g, res, run)
    note = None
    if res in ("stuck", "limit"):
        note = f"  seed {seed} {cls}: {res} after {steps} steps in phase {g.s['phase']}, turn {g.s['turn']}"
    if saves:
        g2, _, res2, _ = play(seed, cls, diff, roundtrip=True)
        g3, _, _, _ = play(seed, cls, diff)  # the same run without the analytics hooks
        if json.dumps(g3.s, sort_keys=True) != json.dumps(g2.s, sort_keys=True):
            note = (note or "") + f"\n  seed {seed}: SAVE ROUND-TRIP DIFFERS ({res} vs {res2})"
        if json.dumps(g3.s, sort_keys=True) != json.dumps(g.s, sort_keys=True):
            note = (note or "") + f"\n  seed {seed}: THE ANALYTICS HOOKS CHANGED THE RUN"
    cause = None
    if res == "lost":
        cause = "flood" if g.s["rises"] >= game.LOSS_RISE else "party fell"
    return res, g.s["turn"], g.s["level"], cause, note, stats.t


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) if "=" in a else (a[2:], True) for a in sys.argv[1:] if a.startswith("--"))
    runs = int(args[0]) if args else 20
    diff = args[1] if len(args) > 1 else "normal"
    seed0 = int(opt.get("seed", 1000))
    combos = [opt["classes"].split(",")] if "classes" in opt else [list(c) for c in combinations(sorted(CLASSES), 3)]
    random.Random(seed0).shuffle(combos)  # so a short batch still sees every class
    jobs = [(seed0 + i, combos[i % len(combos)], diff, "saves" in opt) for i in range(runs)]
    workers = int(opt.get("jobs", os.cpu_count() or 1))
    results, turns, levels, causes = Counter(), [], [], Counter()
    total = SS.Stats()
    if workers > 1 and runs > 1:
        with Pool(min(workers, runs)) as pool:
            out = list(pool.imap(one, jobs))
    else:
        out = [one(j) for j in jobs]
    for res, turn, level, cause, note, t in out:
        results[res] += 1
        turns.append(turn)
        levels.append(level)
        if cause:
            causes[cause] += 1
        if note:
            print(note)
        total.merge(t)
    n = max(1, runs)
    print(f"{runs} runs on {diff}: " + ", ".join(f"{k} {v}" for k, v in results.most_common()))
    if causes:
        print("  losses: " + ", ".join(f"{k} {v}" for k, v in causes.items()))
    print(f"  turns: avg {sum(turns) / n:.1f}, min {min(turns)}, max {max(turns)}; level avg {sum(levels) / n:.1f}")
    if "report" in opt:
        print()
        print(SS.report(total))
    if "json" in opt:
        with open(opt["json"], "w") as fh:
            json.dump(total.t, fh, indent=1, sort_keys=True)
        print(f"Wrote {opt['json']}")


if __name__ == "__main__":
    main()
