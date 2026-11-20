"""Plays Holdfast headlessly with a simple builder, to see how the numbers land.

    python3 tools/holdfast-sim.py [games per setting, default 3] [--fast]

For each map and difficulty, with 1, 2 and 4 players, builders play whole games: each keeps a
fixed mix of towers, puts each where it covers the most road, and spends what's left on
upgrades, mostly for the towers that have done the most damage for the gold in them (`best_up`).
They play sensibly but simply: each tower's usual path (`PREFER`, single-target for archers and
ballistas, crowd-control for frost and tesla), something that can see Ghosts before they come, a
tower that can hurt what the next wave brings when nothing built can (flyers, immunities), sniper
ballistas aimed at the strongest enemy, one final evolution saved for at a time from wave 21 while
the waves are held (`Builder.star`), abilities when a crowd or something big is on the board
(single-target kills only for the big ones), teammates topping up whoever is short of their next
purchase (`pool`), heroes trained when it's cheap, and an item only when lives are really at stake.
They never sell or send a wave early, so a decent human should still do better. Prints how many
games were won, the wave reached and the lives left. `--fast` plays one game of each map on normal
with two players (a few seconds): `tools/check-all.sh` uses it to see the fight runs.
`--bosses <warlord|gravewarden|stormhulk|ironmaw|random>` picks the boss event (default Warlords).
Builders also buy a tier or two on a tower's other path now and then (crosspathing). Each puts a
hero down before the first wave (the four in turn, where it covers the most road) and uses its
abilities like a tower's.
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
SMART_UPS = True  # upgrade the towers doing the damage (see Builder.best_up)
# Waves ahead a shut gate's road starts counting for placement. Counting only open roads (2) lost
# every Breach game: towers by the stretch every gate's road ends on serve all of them.
LOOK_AHEAD = 99
COVER_CAP = 4  # reach counted when choosing where a tower goes (mortars reach everywhere)
UP_ODDS = 0.55  # how often a builder with five towers saves for an upgrade rather than a new tower


def road_for(room):
    """The tiles worth covering: the roads (those open within LOOK_AHEAD waves: all of them), and
    the lines the flyers take from them."""
    soon = room.wave + LOOK_AHEAD
    key = tuple(i for i, w in enumerate(room.opens) if w <= soon)
    if room.road_key != key:
        m = D.MAPS[room.map]
        room.road = sorted(D.path_tiles({"paths": [m["paths"][i] for i in key]}))
        for i in key:
            route, length = room.flights[i]
            (x0, y0), (x1, y1) = route[0][0], route[1][0]
            room.road += [(x0 + (x1 - x0) * j / length, y0 + (y1 - y0) * j / length) for j in range(0, int(length), 2)]
        room.road_key = key
    return room.road


def hurts(st, foe):
    """Can a tower with these numbers hurt this kind of enemy at all?"""
    w = st.get("sentry", st) if st["mode"] == "sentry" else st
    if st["mode"] in ("support", "income"):
        return False
    if foe.get("air") and (st["mode"] == "trap" or not w.get("air")):
        return False
    return w.get("dtype", "normal") == "normal" or w.get("dtype", "normal") not in foe.get("immune", ())


class Builder:
    """One player's hands: spends their own purse (topped up by teammates when it's short)."""

    def __init__(self, room, p, rng):
        self.room, self.p, self.rng = room, p, rng
        self.save_for = None

    def cover(self, kind, x, y):
        r = min((D.TOWERS.get(kind) or D.HEROES[kind])["base"]["range"], COVER_CAP)
        if kind in ("beacon", "mint"):
            return sum(1 for t in self.room.towers.values() if t.kind != "beacon" and not t.hero and math.hypot(t.x - x, t.y - y) <= r)
        return sum(1 for px, py in road_for(self.room) if math.hypot(px - x, py - y) <= r)

    def cost(self):
        """What the current plan costs, or None."""
        if self.save_for is None:
            return None
        what, arg, _ = self.save_for
        if what == "build":
            return D.TOWERS[arg]["cost"]
        t = self.room.towers.get(arg)
        if t is None or t.path is None and what == "side":
            return None
        path = 1 - t.path if what == "side" else self.plan(t)
        nxt = t.tiers[path]
        tiers = D.TOWERS[t.kind]["paths"][path]["tiers"]
        return tiers[nxt]["cost"] if nxt < len(tiers) else None

    def answer(self, towers):
        """A tower to build for what the next wave brings that nothing built can deal with: flyers
        with nothing that hits the air, or an enemy immune to everything built."""
        room = self.room
        kinds = {k for k, _, _, _ in room.groups(room.wave + 1)}
        if not towers:
            return None
        built = [t.stats for t in towers]
        for k in sorted(kinds):
            foe = D.ENEMIES[k]
            if any(hurts(st, foe) for st in built) or any(t.unlock for t in towers):
                continue
            able = [c for c in MIX if hurts(D.TOWERS[c]["base"], foe)]
            if able:
                return min(able, key=lambda c: D.TOWERS[c]["cost"])
        return None

    def items(self):
        """Only when lives are really at stake (a big enemy, or three or more, most of the way to the
        keep) and the item costs at most 30% of the purse: a Frost Flask, a Powder Keg on a crowd or a
        big one, or Caltrops on the road ahead. Firing one whenever anything got 80% of the way there
        spent so much that the builders won about half as many games."""
        room, p = self.room, self.p
        if not room.fighting:
            return
        foes = [e for e in room.enemies if e.hp > 0]
        close = [e for e in foes if e.d / e.length >= 0.8]
        if not close:
            return
        lead = max(close, key=lambda e: e.d / e.length)
        if not (lead.lives >= 3 and lead.d / lead.length >= 0.85) and len(close) < 3:
            return
        wave = max(1, room.wave)
        cheap = lambda k: D.item_cost(k, wave) <= 0.3 * p.gold  # noqa: E731
        if cheap("flask") and room.use_item(p, "flask"):
            return
        x, y = min(D.COLS - 1, max(0, round(lead.x))), min(D.ROWS - 1, max(0, round(lead.y)))
        if cheap("keg") and room.use_item(p, "keg", x, y):
            return
        if not lead.air and cheap("caltrops"):
            ahead = game.where(lead.route, min(lead.length - 0.5, lead.d + 1.5))
            tx, ty = round(ahead[0]), round(ahead[1])
            if (tx, ty) in room.road_tiles:
                room.use_item(p, "caltrops", tx, ty)

    def best_up(self, ups):
        """The tower to upgrade next: weighted by the damage it has done for the gold in it, so the
        well-placed ones grow (as a player would), with some chance for the rest. Towers that don't
        deal damage (beacons, mints) get the average."""
        if not SMART_UPS:
            return self.rng.choice(ups)
        fighters = [t for t in ups if t.stats["mode"] not in ("support", "income")]
        mean = sum(t.dmg / t.spent for t in fighters) / len(fighters) if fighters else 1.0
        weights = [(t.dmg / t.spent if t in fighters else mean) ** 2 + 1e-6 for t in ups]
        return self.rng.choices(ups, weights)[0]

    def train(self):
        """Train the hero when it's cheap next to what's in the purse."""
        h = self.room.hero_of(self.p)
        cost = self.room.train_cost(h) if h else None
        if cost is not None and cost <= 0.2 * self.p.gold:
            self.room.train(self.p, h)

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
        big = any(e.big for e in foes)
        if len(foes) < 8 and not big:
            return
        for t in list(room.towers.values()):
            for n, a in enumerate(t.abilities):
                # a killing blow for one or a few (Headshot, Execute...) waits for a boss or a blimp
                single = a["do"] == "strike" and isinstance(a.get("pick"), int) and a["pick"] <= 2
                if (t.cd2 if n else t.cd) <= 0 and (big or not single):
                    room.use_ability(t, n)

    def think(self):
        room, p = self.room, self.p
        towers = [t for t in room.towers.values() if not t.hero]
        self.abilities()
        self.items()
        if room.starrer is not self:
            self.train()
        for t in towers:  # sniper ballistas go for the toughest; the rest take the first in line
            if t.kind == "ballista" and t.path == 0:
                t.target = "strong"
        if self.save_for is None and room.wave < GHOSTS_FROM and not any(t.sees for t in towers):
            spotter = next((t for t in towers if t.kind == "archer" and t.path in (None, 0) and t.tier < 2), None)
            if spotter and len(towers) >= 4:
                spotter.plan = 0
                self.save_for = ("up", spotter.id, spotter.tier)
        if self.save_for is None or self.save_for[0] == "build":
            need = self.answer(towers)
            if need:
                self.save_for = ("build", need, None)
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
            elif ups and len(towers) >= 5 and self.rng.random() < UP_ODDS:
                t = self.best_up(ups)
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


def pool(builders):
    """Teammates top up whoever is shortest of their next purchase, as real players use the Give
    button: without it each builder saved from its own quarter of the income and four-player games
    fell early with little built. Never towards a final evolution (that builder saves alone)."""
    if len(builders) < 2:
        return
    room = builders[0].room
    needy = [(b, b.cost()) for b in builders if room.starrer is not b]
    needy = [(b, c) for b, c in needy if c is not None and c > b.p.gold]
    if not needy:
        return
    b, cost = max(needy, key=lambda bc: bc[0].p.gold / bc[1])
    for giver in builders:
        while giver is not b and giver.p.gold >= game.GIFT and b.p.gold < cost and room.starrer is not giver:
            before = giver.p.gold
            room.handle(giver.p, {"t": "give", "to": b.p.id})
            if giver.p.gold == before:  # refused (the game just ended)
                return


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
    room.road_key = None  # see road_for
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
            pool(builders)
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
