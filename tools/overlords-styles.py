"""The bot style tournament: every Overlords match seats the four bot styles (bots.STYLES), shuffled,
and each style's average place is printed (2.5 is even). Use it before changing income, interest, XP
or prices: a style far behind the others means that way of playing doesn't pay.

    python3 tools/overlords-styles.py [matches, default 300] [--level easy|normal|hard]

About 0.4 s a normal match (300 in two minutes, about ±0.07 a style); hard bots take about 3 s a match.
"""

import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.overlords import bots as B  # noqa: E402
from app.overlords import game  # noqa: E402


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def main():
    args = sys.argv[1:]
    n = int(next((a for a in args if a.isdigit()), 300))
    level = args[args.index("--level") + 1] if "--level" in args else "normal"
    places = {s: [] for s in B.STYLES}
    rounds = []
    assign = {}
    play = B.play

    def styled(room, p, rng):  # each bot's style is set before its first turn
        if not p.style:
            p.style = assign[p.id]
        return play(room, p, rng)

    B.play = styled
    started = time.perf_counter()
    for i in range(n):
        room = game.Room("STYLES")
        room.rng.seed(50_000 + i)
        room.clock = Clock()
        room.bot_level, room.bots, room.saving = level, True, False
        order = list(B.STYLES)
        random.Random(i).shuffle(order)
        assign.clear()
        assign.update({room.next_id + k: order[k % len(order)] for k in range(game.MAX_PLAYERS)})
        room.start()
        while room.phase != "over" and room.round < 40:
            room.clock.t = room.ends + 0.01
            room.tick()
        rounds.append(room.round)
        for p in room.seated():
            places[p.style].append(p.place)
    print(f"{n} matches ({level} bots), {time.perf_counter() - started:.0f} s, {statistics.mean(rounds):.1f} rounds")
    for s, v in sorted(places.items(), key=lambda kv: statistics.mean(kv[1])):
        print(f"  {s:6} {statistics.mean(v):.2f}  wins {sum(x == 1 for x in v)}")


if __name__ == "__main__":
    main()
