"""Plays whole Saltbound runs with bots on the server's own rules, for balance and save checks.

    python3 tools/saltbound-sim.py [runs] [difficulty] [--classes=a,b,c] [--with=class] [--saves] [--report]
                                   [--json=out.json] [--jobs=N] [--seed=1000] [--fast] [--tally]

Two kinds of test:

- **--fast, for checking a feature works**: greedy bots (each fight move is the best single
  placement, no look-ahead), about 4x quicker. They play worse, so their win rates say nothing about
  balance, but they still reach every part of a run on Normal. Prints a tally of what happened
  (effects, events, fights by kind) so a new feature can be seen firing. 40 runs on Normal take about
  20 s. Its saved batches are kept apart (last-fast-<difficulty>.txt).
- **The full bots, for balance**: only for changes that directly affect game balance, and then once,
  at the end of a batch of changes. --tally adds the same tally to a full run.

Prints wins, losses and why, run length in map turns, the party's level, and any runs that got
stuck. With --report it also prints the balance analytics from tools/saltbound_stats.py: class win
rates and output per round, fights and the hardest encounters, enemies by damage dealt, every
class's actions (use share, hit rate, damage, healing, Armor, kills, overkill), level-up picks
against win rate, gear, consumables, and a list of balance flags. --json writes the raw numbers.
Runs are spread over --jobs worker processes (all cores by default).

With --saves, every run is also saved and loaded (through JSON) after every action, and must finish
exactly as the same run played straight through.

Every batch of 50 runs or more saves what it printed (with the date, the commit and the command) to
data/saltbound-sim/, the latest per difficulty as last-<difficulty>.txt. `--last` prints those
instead of playing anything, so a question about balance can be answered from the latest numbers:

    python3 tools/saltbound-sim.py --last          # every difficulty's latest batch
    python3 tools/saltbound-sim.py --last hard

Rough run times on all cores (full bots): 12 runs ~12 s, 100 runs ~1-1.5 min, 300 runs ~3-4 min (each
batch run at the same time as another doubles it). --fast is about 4x quicker.
"""

import contextlib
import io
import json
import os
import random
import subprocess
import sys
import textwrap
import time
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


TALLY = None  # what happened in the run being played, when tallying (a Counter)
FAST = (1, 1)  # --fast: the bots' fight search (beam, depth)


def _tallied(name, fn, key):
    def wrapped(self, *a, **kw):
        if TALLY is not None:
            k = key(*a, **kw)
            if k:
                TALLY[k] += 1
        return fn(self, *a, **kw)
    return wrapped


game.Game.fx = _tallied("fx", game.Game.fx, lambda kind_, **kw: None if kind_ in TALLY_SKIP else (
    f"event: {kw.get('key')}" if kind_ == "event" else f"fx: {kind_}"))
game.Game.start_fight = _tallied("start_fight", game.Game.start_fight, lambda spec: f"fight: {spec['kind']}")
game.Game.say = _tallied("say", game.Game.say, lambda text: next((f"log: {k}" for k in TALLY_LOG if k in text), None))
# effects too common or too small to be worth a line
TALLY_SKIP = {"move", "gmove", "roll", "dmg", "heal", "status", "act", "foe", "armor", "coins", "fact", "froll", "sact", "intent",
              "round", "block", "miss", "summon", "die", "float", "turn", "st", "combo", "fight", "fightend", "end"}
# log lines worth counting (the start of the message)
TALLY_LOG = ["takes a job", "Job done", "has failed", "hauls the cargo", "sighted", "garrisons grow", "weakened",
             "reforges", "temple's blessing", "buys a chart", "digs up the cache", "castaway you helped", "guards are beaten",
             "hauls in the drifting", "wandering healer sees", "learns", "is revived", "has fallen"]


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
        for h in bot.order(g, waiting):
            msg = bot.decide(g, h)
            if msg is None:
                continue
            q = g.s["pending"][str(h)]
            dialog = q[0] if q and msg.get("t") == "choose" else None
            if dialog and dialog["type"] == "pool":  # the pool can close as this claim lands
                dialog = {**dialog, "opts": list(g.s["pools"][str(dialog["id"])]["items"])}
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
    global TALLY
    seed, cls, diff, saves, fast, tally = job
    if fast:
        bot.BEAM, bot.DEPTH = FAST
    stats = SS.Stats()
    TALLY = Counter() if tally else None
    g, steps, res, run = play(seed, cls, diff, stats=stats)
    counted, TALLY = TALLY, None
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
        cause = "party fell"
    return res, g.s["turn"], g.s["level"], cause, note, stats.t, counted


SAVED = os.path.join(os.path.dirname(__file__), "..", "data", "saltbound-sim")


def show_last(which):
    """Print the latest saved batch for each difficulty (or one), without playing anything."""
    names = [f"last-{which}.txt"] if which else sorted(f for f in os.listdir(SAVED) if f.startswith("last-")) \
        if os.path.isdir(SAVED) else []
    shown = False
    for name in names:
        path = os.path.join(SAVED, name)
        if os.path.exists(path):
            print(open(path).read())
            shown = True
    if not shown:
        print("No saved batches yet: run 50 or more, e.g. python3 tools/saltbound-sim.py 300 hard --report")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(a[2:].split("=", 1) if "=" in a else (a[2:], True) for a in sys.argv[1:] if a.startswith("--"))
    if "last" in opt:
        show_last(args[0] if args else None)
        return
    if runs_wanted(args) >= 50:
        buf = io.StringIO()
        started = time.time()
        code = 0
        with contextlib.redirect_stdout(Tee(sys.stdout, buf)):
            try:
                play_batch(args, opt)
            except SystemExit as e:
                code = e.code or 0
        save_batch(args, buf.getvalue(), time.time() - started)
        sys.exit(code)
    play_batch(args, opt)


def runs_wanted(args):
    return int(args[0]) if args else 20


class Tee(io.TextIOBase):
    def __init__(self, *outs):
        self.outs = outs

    def write(self, text):
        for o in self.outs:
            o.write(text)
        return len(text)

    def flush(self):
        for o in self.outs:
            o.flush()


def save_batch(args, text, secs):
    diff = args[1] if len(args) > 1 else "normal"
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                                cwd=os.path.dirname(__file__)).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "app/saltbound"], capture_output=True, text=True,
                               cwd=os.path.join(os.path.dirname(__file__), "..")).stdout.strip()
    except OSError:
        commit, dirty = "?", ""
    head = (f"# {time.strftime('%Y-%m-%d %H:%M')} · commit {commit}{' + uncommitted changes' if dirty else ''} · "
            f"{secs / 60:.1f} min\n# python3 tools/saltbound-sim.py {' '.join(sys.argv[1:])}\n")
    os.makedirs(SAVED, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    kind = f"fast-{diff}" if "--fast" in sys.argv else diff
    for name in (f"{stamp}-{kind}.txt", f"last-{kind}.txt"):
        with open(os.path.join(SAVED, name), "w") as fh:
            fh.write(head + text)


def play_batch(args, opt):
    runs = runs_wanted(args)
    diff = args[1] if len(args) > 1 else "normal"
    seed0 = int(opt.get("seed", 1000))
    combos = [opt["classes"].split(",")] if "classes" in opt else [list(c) for c in combinations(sorted(CLASSES), 3)]
    if "with" in opt:  # every party includes this class (its picks are offered three times as often)
        combos = [c for c in combos if opt["with"] in c]
    random.Random(seed0).shuffle(combos)  # so a short batch still sees every class
    fast = "fast" in opt
    tally = fast or "tally" in opt
    jobs = [(seed0 + i, combos[i % len(combos)], diff, "saves" in opt, fast, tally) for i in range(runs)]
    workers = int(opt.get("jobs", os.cpu_count() or 1))
    results, turns, levels, causes = Counter(), [], [], Counter()
    total = SS.Stats()
    if workers > 1 and runs > 1:
        with Pool(min(workers, runs)) as pool:
            out = list(pool.imap(one, jobs))
    else:
        out = [one(j) for j in jobs]
    seen = Counter()
    for res, turn, level, cause, note, t, counted in out:
        if counted:
            seen.update(counted)
        results[res] += 1
        turns.append(turn)
        levels.append(level)
        if cause:
            causes[cause] += 1
        if note:
            print(note)
        total.merge(t)
    n = max(1, runs)
    print(f"{runs} runs on {diff}{' (fast: greedy bots, not for balance)' if fast else ''}: "
          + ", ".join(f"{k} {v}" for k, v in results.most_common()))
    if causes:
        print("  losses: " + ", ".join(f"{k} {v}" for k, v in causes.items()))
    print(f"  turns: avg {sum(turns) / n:.1f}, min {min(turns)}, max {max(turns)}; level avg {sum(levels) / n:.1f}")
    if tally:
        print(f"\nWhat happened (totals over the {runs} runs):")
        groups = {}
        for k in sorted(seen):
            g_, name = k.split(": ", 1)
            groups.setdefault(g_, []).append(f"{name} {seen[k]}")
        for g_ in ("fight", "log", "fx", "event"):
            if g_ in groups:
                print(textwrap.fill(", ".join(groups[g_]), width=110, initial_indent=f"  {g_ + 's:':<8}", subsequent_indent=" " * 10))
    if "report" in opt:
        print()
        print(SS.report(total))
    if "json" in opt:
        with open(opt["json"], "w") as fh:
            json.dump(total.t, fh, indent=1, sort_keys=True)
        print(f"Wrote {opt['json']}")
    # a stuck run, one that hit the step limit, or a save that doesn't load back the same
    sys.exit(1 if any(o[4] for o in out) else 0)


if __name__ == "__main__":
    main()
