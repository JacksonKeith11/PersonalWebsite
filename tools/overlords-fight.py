"""Runs Overlords fights headlessly, to see how units and traits do.

    python3 tools/overlords-fight.py [fights, default 400] [--size N] [--seed S]
    python3 tools/overlords-fight.py --traits [fights per tier, default 150] [--size N]
    python3 tools/overlords-fight.py --show SEED [--size N]    one fight's events, readable

Units: random boards of `--size` different units (default 6; a third of them two-star) each fight
a board of the same costs and stars made of other units, so a unit's win rate (the share of fights
its side won) measures it against units of its own cost: 50% is right for every cost. Also prints
how long fights last, how many hit the time cap and how long one fight takes to simulate.

Traits (`--traits`): for each trait at each of its tiers, boards of `--size` (default 7) holding
exactly that many of its units, the rest random, fight cost-matched boards without it. A trait's
tier should win more the higher it is, roughly 55-65% at its first tier and 65-80% at its top
(the boards were built around it, the opponents weren't).
"""

import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.overlords import bots  # noqa: E402
from app.overlords import data as D  # noqa: E402
from app.overlords import sim  # noqa: E402


def arg(name, default):
    if name in sys.argv:
        return int(sys.argv[sys.argv.index(name) + 1])
    return default


def show(seed, size):
    rng = random.Random(seed)
    home, away = bots.random_board(rng, size), bots.random_board(rng, size)
    res = sim.fight(home, away, seed)
    names = {}
    for uid, side, key, star, c, r, hp, mana, m0 in res["start"]:
        names[uid] = f"{'AB'[side]}:{D.UNITS[key]['name']}{'*' * star}"
        print(f"{names[uid]:24} at {c},{r}  hp {hp}  mana {m0}/{mana}")
    for side in (0, 1):
        active = {t: n for t, n in res["traits"][side].items() if D.trait_level(t, n) >= 0}
        print("AB"[side], "traits:", ", ".join(f"{D.TRAITS[t]['name']} {n}" for t, n in active.items()) or "none")
    for e in res["events"]:
        kind, t = e[0], e[1]
        if kind == "v":
            continue
        if kind == "sp":
            names[e[2][0]] = f"{'AB'[e[2][1]]}:{D.UNITS[e[2][2]]['name']}"
            print(f"{t:6.2f} {names[e[2][0]]} summoned")
        elif kind == "d":
            print(f"{t:6.2f} {names.get(e[3])} takes {e[4]} {['phys', 'magic', 'true', 'burn'][e[5]]}"
                  f"{' crit' if e[6] else ''} from {names.get(e[2], '-')}")
        elif kind in ("m", "j"):
            print(f"{t:6.2f} {names[e[2]]} {'moves' if kind == 'm' else 'jumps'} to {e[3]},{e[4]}")
        elif kind == "a":
            pass
        elif kind == "c":
            print(f"{t:6.2f} {names[e[2]]} casts {D.UNITS[res_key(res, e[2])]['ability']['name']}")
        else:
            print(f"{t:6.2f} {kind} {names.get(e[2], e[2])} {e[3:]}")
    print("winner:", "AB"[res["winner"]] if res["winner"] is not None else "neither", "after", res["time"], "s")


def res_key(res, uid):
    for row in res["start"]:
        if row[0] == uid:
            return row[2]
    for e in res["events"]:
        if e[0] == "sp" and e[2][0] == uid:
            return e[2][2]


def matched(rng, board, avoid=()):
    """A board of the same costs and stars as `board`, at the same places, made of other units."""
    used, out = set(avoid) | {b["unit"] for b in board}, []
    for b in board:
        tier = D.UNITS[b["unit"]]["tier"]
        options = [k for k in D.shop_units() if D.UNITS[k]["tier"] == tier and k not in used
                   and not any(t in avoid for t in D.UNITS[k]["traits"])]
        if not options:
            options = [k for k in D.shop_units() if D.UNITS[k]["tier"] == tier and k not in used] or [b["unit"]]
        k = rng.choice(options)
        used.add(k)
        out.append({"unit": k, "star": b["star"]})
    return [{"unit": u["unit"], "star": u["star"], "col": c, "row": r} for u, c, r in bots.arrange(out)]


def traits(n, size, seed):
    rng = random.Random(seed)
    started, fights = time.perf_counter(), 0
    print(f"traits on boards of {size} vs cost-matched boards, {n} fights a tier:")
    for trait, t in D.TRAITS.items():
        members = [k for k in D.shop_units() if trait in D.UNITS[k]["traits"]]
        row = []
        for need in t["levels"]:
            wins = 0
            for i in range(n):
                picked = rng.sample(members, need)
                rest = [k for k in D.shop_units() if k not in picked and trait not in D.UNITS[k]["traits"]]
                picked += rng.sample(rest, max(0, size - need))
                units = [{"unit": k, "star": 2 if rng.random() < 0.3 else 1} for k in picked]
                home = [{"unit": u["unit"], "star": u["star"], "col": c, "row": r} for u, c, r in bots.arrange(units)]
                away = matched(rng, home, avoid=(trait,))
                side = i % 2  # swap sides half the time
                res = sim.fight(home, away, rng.randrange(1 << 30)) if side == 0 else sim.fight(away, home, rng.randrange(1 << 30))
                wins += res["winner"] == side
                fights += 1
            row.append(f"{need}: {100 * wins / n:4.0f}%")
        print(f"  {t['name']:12} " + "   ".join(row))
    print(f"({fights} fights, {time.perf_counter() - started:.0f} s)")


def report(n, size, seed):
    rng = random.Random(seed)
    unit_w, unit_n = defaultdict(int), defaultdict(int)
    trait_w, trait_n = defaultdict(int), defaultdict(int)
    times, capped, draws = [], 0, 0
    started = time.perf_counter()
    for i in range(n):
        home = bots.random_board(rng, size)
        boards = [home, matched(rng, home)]
        res = sim.fight(boards[0], boards[1], rng.randrange(1 << 30))
        times.append(res["time"])
        capped += res["time"] >= sim.TIME_CAP
        if res["winner"] is None:
            draws += 1
            continue
        for side in (0, 1):
            won = res["winner"] == side
            for b in boards[side]:
                unit_n[b["unit"]] += 1
                unit_w[b["unit"]] += won
            for t, c in res["traits"][side].items():
                level = D.trait_level(t, c)
                if level >= 0:
                    name = f"{t} {D.TRAITS[t]['levels'][level]}"
                    trait_n[name] += 1
                    trait_w[name] += won
    took = time.perf_counter() - started
    print(f"{n} fights of {size} units: {took / n * 1000:.1f} ms each, average {sum(times) / n:.1f} s, "
          f"{capped} hit the {sim.TIME_CAP:.0f} s cap, {draws} with no winner")
    print("\nunits (cost, win rate, fights):")
    for k in sorted(unit_n, key=lambda k: (D.UNITS[k]["tier"], -unit_w[k] / unit_n[k])):
        print(f"  {D.UNITS[k]['tier']}  {D.UNITS[k]['name']:16} {100 * unit_w[k] / unit_n[k]:5.1f}%  {unit_n[k]}")
    print("\ntraits (win rate, fights):")
    for k in sorted(trait_n, key=lambda k: -trait_w[k] / trait_n[k]):
        print(f"  {k:16} {100 * trait_w[k] / trait_n[k]:5.1f}%  {trait_n[k]}")


if __name__ == "__main__":
    size = arg("--size", 6)
    if "--show" in sys.argv:
        show(arg("--show", 1), size)
    elif "--traits" in sys.argv:
        i = sys.argv.index("--traits")
        n = int(sys.argv[i + 1]) if len(sys.argv) > i + 1 and sys.argv[i + 1].isdigit() else 150
        traits(n, arg("--size", 7), arg("--seed", 1))
    else:
        n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 400
        report(n, size, arg("--seed", 1))
