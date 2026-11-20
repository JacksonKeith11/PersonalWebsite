"""Plays Holdfast headlessly with a simple builder, to see how the numbers land.

    python3 tools/holdfast-sim.py [games per setting, default 3] [--fast]

For each map and difficulty, with 1, 2 and 4 players, builders play whole games: each keeps a
fixed mix of towers, puts each where it covers the most road, and spends what's left on upgrades.
They play sensibly but simply: each tower's usual path (`PREFER`, single-target for archers and
ballistas, crowd-control for frost and tesla), something that can see Ghosts before they come,
sniper ballistas aimed at the strongest enemy (archers aimed that way let flyers past), one final
evolution saved for at a time from wave 21 while the waves are held (`Builder.star`), and abilities
used when a crowd or a Warlord is on the board.
They never sell, hand gold over or send a wave early, so a decent human should do better. Prints
how many games were won, the wave reached and the lives left. `--fast` plays one game of each map
on normal with two players (a few seconds): `tools/check-all.sh` uses it to see the fight runs.
`--bosses <warlord|gravewarden|stormhulk|ironmaw|random>` picks the boss event (default Warlords).
Builders also buy a tier or two on a tower's other path now and then (crosspathing), but never use
items. Each puts a hero down before the first wave (the four in turn, where it covers the most road),
never trains it with gold, and uses its abilities like a tower's.
"""

import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.holdfast import data as D  # noqa: E402
from app.holdfast import game  # noqa: E402

MIX = {"archer": 2.4, "cannon": 1.5, "tesla": 1.2, "ballista": 1, "frost": 0.8, "beacon": 0.5, "brazier": 0.6,
       "mortar": 0.5, "mint": 0.25, "bladewheel": 0.8, "trapper": 0.7, "workshop": 0.5, "arcanist": 0.6,
       "skyhook": 0.4, "alchemist": 0.5}


# The path each tower usually takes, and how often (else the other).
PREFER = {"archer": (0, 0.7), "cannon": (0, 0.6), "frost": (1, 0.6), "ballista": (0, 0.8), "tesla": (1, 0.6),
          "beacon": (0, 0.7), "brazier": (0, 0.6), "mortar": (0, 0.6), "mint": (0, 0.8), "bladewheel": (0, 0.5),
          "trapper": (0, 0.5), "workshop": (0, 0.6), "arcanist": (1, 0.5), "skyhook": (1, 0.6), "alchemist": (1, 0.5)}
GHOSTS_FROM = 7  # the first wave with Ghosts in it


class Builder:
    """One player's hands: spends their own purse."""

    def __init__(self, room, p, rng):
        self.room, self.p, self.rng = room, p, rng
        self.save_for = None

    def cover(self, kind, x, y):
        r = min((D.TOWERS.get(kind) or D.HEROES[kind])["base"]["range"], 4)
        if kind in ("beacon", "mint"):
            return sum(1 for t in self.room.towers.values() if t.kind != "beacon" and not t.hero and math.hypot(t.x - x, t.y - y) <= r)
        return sum(1 for px, py in self.room.road if math.hypot(px - x, py - y) <= r)

    def plan(self, t):
        """The path this builder means to take a tower down."""
        if t.path is not None:
            return t.path
        if not hasattr(t, "plan"):
            path, odds = PREFER[t.kind]
            t.plan = path if self.rng.random() < odds else 1 - path
        return t.plan

    def drop(self):
        self.save_for = None
        if self.room.starrer is self:
            self.room.starrer = None

    def star(self):
        """After the second Warlord (wave 21 on), one builder at a time saves for a final evolution
        (the cheapest a tier-3 tower can take), once three waves in a row were held cleanly, until a
        leak puts the gold back to work. Saving earlier, or while lives were going, lost games."""
        room = self.room
        if room.wave < 21 or room.starrer is not None or any(room.leaks.get(room.wave - i) for i in range(3)):
            return
        cost = lambda t: D.TOWERS[t.kind]["paths"][self.plan(t)]["tiers"][D.EVOLUTION - 1]["cost"]  # noqa: E731
        ready = [t for t in room.towers.values()
                 if not t.hero and t.tier == D.EVOLUTION - 1 and not room.evolved(t.kind, self.plan(t))]
        if ready:
            t = min(ready, key=cost)
            self.save_for = ("up", t.id, t.tier)
            room.starrer = self

    def abilities(self):
        room = self.room
        if not room.fighting:
            return
        foes = [e for e in room.enemies if e.hp > 0]
        if len(foes) < 8 and not any(e.boss for e in foes):
            return
        for t in list(room.towers.values()):
            for n, _ in enumerate(t.abilities):
                if (t.cd2 if n else t.cd) <= 0:
                    room.use_ability(t, n)

    def think(self):
        room, p = self.room, self.p
        towers = [t for t in room.towers.values() if not t.hero]
        self.abilities()
        for t in towers:  # sniper ballistas go for the toughest; the rest take the first in line
            if t.kind == "ballista" and t.path == 0:
                t.target = "strong"
        if self.save_for is None and room.wave < GHOSTS_FROM and not any(t.sees for t in towers):
            spotter = next((t for t in towers if t.kind == "archer" and t.path in (None, 0) and t.tier < 2), None)
            if spotter and len(towers) >= 4:
                spotter.plan = 0
                self.save_for = ("up", spotter.id, spotter.tier)
        if self.save_for is None:
            self.star()
        if self.save_for is None:
            counts = {k: sum(t.kind == k for t in towers) for k in MIX}
            kind = min(MIX, key=lambda k: (counts[k] + 0.5) / MIX[k])
            def worth(t):  # final evolutions go through `star`
                return t.tier < D.EVOLUTION - 1

            ups = [t for t in towers if worth(t)]
            side = [t for t in towers if t.tier >= 3 and t.tiers[1 - t.path] < D.CROSS_MAX]
            if side and self.rng.random() < 0.15:  # a tier or two on the other path (crosspathing)
                t = self.rng.choice(side)
                self.save_for = ("side", t.id, t.tiers[1 - t.path])
            elif ups and len(towers) >= 5 and self.rng.random() < 0.55:
                t = self.rng.choice(ups)
                self.save_for = ("up", t.id, t.tier)
            else:
                self.save_for = ("build", kind, None)
        what, arg, tier = self.save_for
        if room.starrer is self and room.leaks.get(room.wave):  # the road needs the gold more
            self.drop()
        elif what == "side":
            t = room.towers.get(arg)
            if t is None or t.path is None or t.tiers[1 - t.path] != tier or room.upgrade(p, t, 1 - t.path):
                self.drop()
        elif what == "up":
            t = room.towers.get(arg)
            path = self.plan(t) if t is not None else 0
            # gone, or someone else bought the tier this was saving for
            if t is None or t.tier != tier or t.tier >= D.EVOLUTION or (t.tier + 1 == D.EVOLUTION and room.evolved(t.kind, path)):
                self.drop()
            elif room.upgrade(p, t, path):
                self.drop()
        elif p.gold >= D.TOWERS[arg]["cost"]:
            spots = [xy for xy in room.buildable if xy not in room.at]
            if spots:
                best = max(spots, key=lambda s: (self.cover(arg, *s), self.rng.random()))
                room.build(p, arg, *best)
            self.save_for = None


def play(map_id, diff, n, seed, bosses="warlord"):
    rng = random.Random(seed)
    room = game.Room("SIM")
    room.send = lambda p, data: None
    room.saving = False
    room.map, room.diff, room.bosses = map_id, diff, bosses
    for i in range(n):
        p = game.Player(i + 1, f"P{i + 1}", "#fff", None, None, None)
        room.players[p.id] = p
    room.start()
    # the tiles worth covering: the roads, and the line the flyers take
    room.road = sorted(D.path_tiles(D.MAPS[map_id]))
    for route, length in room.flights:
        (x0, y0), (x1, y1) = route[0][0], route[1][0]
        room.road += [(x0 + (x1 - x0) * i / length, y0 + (y1 - y0) * i / length) for i in range(0, int(length), 2)]
    room.starrer = None  # the builder saving for a final evolution
    builders = [Builder(room, p, rng) for p in room.players.values()]
    heroes = list(D.HEROES)
    for i, b in enumerate(builders if heroes else []):
        kind = heroes[(seed + i) % len(heroes)]
        spots = [xy for xy in room.buildable if xy not in room.at]
        room.place_hero(b.p, kind, *max(spots, key=lambda s: (b.cover(kind, *s), rng.random())))
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
    bosses = sys.argv[sys.argv.index("--bosses") + 1] if "--bosses" in sys.argv else "warlord"
    t0 = time.time()
    settings = [(m, "normal", 2) for m in D.MAPS] if fast else \
        [(m, d, n) for m in D.MAPS for d in D.DIFFICULTY for n in (1, 2, 4)]
    for map_id, diff, n in settings:
        rooms = [play(map_id, diff, n, seed, bosses) for seed in range(1 if fast else games)]
        for room in rooms:
            assert room.phase in ("won", "lost") and 1 <= room.wave <= D.WAVES
            assert all(p.gold >= 0 for p in room.players.values())
        won = sum(r.phase == "won" for r in rooms)
        waves = sorted(r.wave for r in rooms)
        lives = sorted(r.lives for r in rooms)
        towers = sum(len(r.towers) for r in rooms) / len(rooms)
        evos = sum(t.tier == D.EVOLUTION for r in rooms for t in r.towers.values()) / len(rooms)
        print(f"{map_id:9} {diff:7} {n} players: won {won}/{len(rooms)}, reached wave {waves[0]}-{waves[-1]}, "
              f"lives left {lives[0]}-{lives[-1]}, {towers:.0f} towers, {evos:.1f} evolved")
    print(f"({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
