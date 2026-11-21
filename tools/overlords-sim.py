"""Plays whole Overlords matches with four bots, to see how commanders and augments do.

    python3 tools/overlords-sim.py [matches, default 100] [--level easy|normal|hard] [--fast]

Every match runs on a clock wound on instantly (as tools/overlords-check.py does). Prints how many
rounds a match lasts and how long that would take at full timers, then each commander's average
place (2.5 is even among four) and how often it won, and the augments picked most and how they
placed. Commanders and augments far from 2.5 are worth a look. `--fast` plays 4 matches (seconds).
About a second a match.
"""

import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.overlords import data as D  # noqa: E402
from app.overlords import game  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def match(seed, level):
    room = game.Room("SIM")
    room.rng.seed(seed)
    room.clock = Clock()
    room.bot_level = level
    room.bots = True
    room.start()
    start = room.clock.t
    while room.phase != "over" and room.round < 40:
        room.clock.t = room.ends + 0.01
        room.tick()
    return room, room.clock.t - start


def main():
    args = sys.argv[1:]
    n = 4 if "--fast" in args else int(next((a for a in args if a.isdigit()), 100))
    level = args[args.index("--level") + 1] if "--level" in args else "normal"
    places, wins = defaultdict(list), defaultdict(int)
    aug_places = defaultdict(list)
    rounds, secs = [], []
    started = time.perf_counter()
    for i in range(n):
        room, took = match(i, level)
        rounds.append(room.round)
        secs.append(took)
        for p in room.seated():
            places[p.commander].append(p.place)
            wins[p.commander] += p.place == 1
            for a in p.augments:
                aug_places[a].append(p.place)
    print(f"{n} matches ({level} bots), {time.perf_counter() - started:.0f} s: {sum(rounds) / n:.1f} rounds "
          f"({min(rounds)}-{max(rounds)}), about {sum(secs) / n / 60:.0f} minutes at full timers")
    print("\ncommanders (average place, wins, matches):")
    for c in sorted(places, key=lambda c: sum(places[c]) / len(places[c])):
        ps = places[c]
        print(f"  {D.COMMANDERS[c]['name']:18} {sum(ps) / len(ps):.2f}  {100 * wins[c] / len(ps):3.0f}%  {len(ps)}")
    print("\naugments picked most (average place, times):")
    common = sorted(aug_places, key=lambda a: -len(aug_places[a]))[:15]
    for a in sorted(common, key=lambda a: sum(aug_places[a]) / len(aug_places[a])):
        ps = aug_places[a]
        print(f"  {D.AUGMENTS[a]['name']:22} {sum(ps) / len(ps):.2f}  {len(ps)}")


if __name__ == "__main__":
    random.seed(0)
    main()
