"""Plays Holdfast headlessly with a simple builder, to see how the numbers land.

    python3 tools/holdfast-sim.py [games per setting, default 3] [--fast]

For each map and difficulty, with 1, 2 and 4 players, builders play whole games: each keeps a
fixed mix of towers, puts each where it covers the most road, and spends what's left on upgrades.
They never sell, hand gold over or send a wave early, so a decent human should do better. Prints
how many games were won, the wave reached and the lives left. `--fast` plays one game of each map
on normal with two players (a few seconds): `tools/check-all.sh` uses it to see the fight runs.
"""

import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.holdfast import data as D  # noqa: E402
from app.holdfast import game  # noqa: E402

MIX = {"archer": 3, "cannon": 2, "tesla": 1.5, "ballista": 1, "frost": 1, "beacon": 0.6}


class Builder:
    """One player's hands: spends their own purse."""

    def __init__(self, room, p, rng):
        self.room, self.p, self.rng = room, p, rng
        self.save_for = None

    def cover(self, kind, x, y):
        r = D.TOWERS[kind]["levels"][0]["range"]
        if kind == "beacon":
            return sum(1 for t in self.room.towers.values() if t.kind != "beacon" and math.hypot(t.x - x, t.y - y) <= r)
        return sum(1 for px, py in self.room.road if math.hypot(px - x, py - y) <= r)

    def think(self):
        room, p = self.room, self.p
        towers = list(room.towers.values())
        if self.save_for is None:
            counts = {k: sum(t.kind == k for t in towers) for k in MIX}
            kind = min(MIX, key=lambda k: (counts[k] + 0.5) / MIX[k])
            ups = [t for t in towers if t.level < 2]
            if ups and len(towers) >= 5 and self.rng.random() < 0.55:
                self.save_for = ("up", self.rng.choice(ups).id)
            else:
                self.save_for = ("build", kind)
        what, arg = self.save_for
        if what == "up":
            t = room.towers.get(arg)
            if t is None or t.level >= 2:
                self.save_for = None
            elif room.upgrade(p, t):
                self.save_for = None
        elif p.gold >= D.TOWERS[arg]["cost"][0]:
            spots = [(x, y) for x in range(D.COLS) for y in range(D.ROWS) if room.free(x, y)]
            if spots:
                best = max(spots, key=lambda s: (self.cover(arg, *s), self.rng.random()))
                room.build(p, arg, *best)
            self.save_for = None


def play(map_id, diff, n, seed):
    rng = random.Random(seed)
    room = game.Room("SIM")
    room.send = lambda p, data: None
    room.map, room.diff = map_id, diff
    for i in range(n):
        p = game.Player(i + 1, f"P{i + 1}", "#fff", None, None, None)
        room.players[p.id] = p
    room.start()
    # the tiles worth covering: the roads, and the line the flyers take
    room.road = sorted(D.path_tiles(D.MAPS[map_id]))
    for route, length in room.flights:
        (x0, y0), (x1, y1) = route[0][0], route[1][0]
        room.road += [(x0 + (x1 - x0) * i / length, y0 + (y1 - y0) * i / length) for i in range(0, int(length), 2)]
    builders = [Builder(room, p, rng) for p in room.players.values()]
    steps = 0
    while room.phase == "play":
        room.advance(game.STEP)
        steps += 1
        if steps % 8 == 0:
            for b in builders:
                b.think()
        assert steps < 400_000, "the game never ended"
    return room


def main():
    fast = "--fast" in sys.argv
    games = next((int(a) for a in sys.argv[1:] if a.isdigit()), 3)
    t0 = time.time()
    settings = [(m, "normal", 2) for m in D.MAPS] if fast else \
        [(m, d, n) for m in D.MAPS for d in D.DIFFICULTY for n in (1, 2, 4)]
    for map_id, diff, n in settings:
        rooms = [play(map_id, diff, n, seed) for seed in range(1 if fast else games)]
        for room in rooms:
            assert room.phase in ("won", "lost") and 1 <= room.wave <= D.WAVES
            assert all(p.gold >= 0 for p in room.players.values())
        won = sum(r.phase == "won" for r in rooms)
        waves = sorted(r.wave for r in rooms)
        lives = sorted(r.lives for r in rooms)
        towers = sum(len(r.towers) for r in rooms) / len(rooms)
        print(f"{map_id:9} {diff:7} {n} players: won {won}/{len(rooms)}, reached wave {waves[0]}-{waves[-1]}, "
              f"lives left {lives[0]}-{lives[-1]}, {towers:.0f} towers")
    print(f"({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
