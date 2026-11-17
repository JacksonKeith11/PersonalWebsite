"""Holdfast's numbers: the towers, the enemies, the waves and the maps.

Distances are in tiles (the board is COLS x ROWS of them), times in seconds. The browser gets
TOWERS, ENEMIES and the chosen map as they are here, so its panels never disagree with the rules.
`tools/holdfast-sim.py` plays whole games with a simple builder to show how the numbers land.
"""

COLS, ROWS = 20, 12
LIVES = 20
WAVES = 30
START_GOLD = (130, 60)  # shared out between the players, plus this much each
SELL_BACK = 0.7
BUILD_TIME = (25, 12)  # seconds before the first wave, and between waves
DIFFICULTY = {"easy": 0.75, "normal": 1.0, "hard": 1.3}  # enemy health

# Each tower: what it costs to build and then to upgrade (twice), and its numbers at each level.
#   range    tiles                      rate    seconds between shots
#   dmg      damage a shot              air     can it hit flyers?
#   splash   radius of the blast        slow    how much it slows (0.4 = 40% slower), for `hold` s
#   chain    enemies a bolt jumps to    pierce  ignores armour
#   boost    nearby towers fire this much faster (the best beacon in reach counts, not the sum)
TOWERS = {
    "archer": {"name": "Archer", "cost": [50, 60, 110], "air": True,
               "blurb": "Cheap and quick. Hits flyers.",
               "levels": [{"range": 3.2, "rate": 0.6, "dmg": 10}, {"range": 3.4, "rate": 0.6, "dmg": 19},
                          {"range": 3.7, "rate": 0.5, "dmg": 32}]},
    "cannon": {"name": "Cannon", "cost": [90, 100, 180], "air": False,
               "blurb": "Blasts a crowd. Can't aim at flyers.",
               "levels": [{"range": 2.8, "rate": 1.4, "dmg": 22, "splash": 1.1},
                          {"range": 3.0, "rate": 1.4, "dmg": 42, "splash": 1.2},
                          {"range": 3.2, "rate": 1.3, "dmg": 78, "splash": 1.45}]},
    "frost": {"name": "Frost", "cost": [70, 80, 140], "air": True,
              "blurb": "Slows everything near it.",
              "levels": [{"range": 2.3, "rate": 1.0, "dmg": 2, "slow": 0.35, "hold": 1.5},
                         {"range": 2.6, "rate": 1.0, "dmg": 4, "slow": 0.45, "hold": 1.5},
                         {"range": 3.0, "rate": 1.0, "dmg": 8, "slow": 0.55, "hold": 1.8}]},
    "ballista": {"name": "Ballista", "cost": [120, 130, 240], "air": True, "pierce": True,
                 "blurb": "Slow, far-reaching, and goes straight through armour.",
                 "levels": [{"range": 6.0, "rate": 2.2, "dmg": 75}, {"range": 6.5, "rate": 2.1, "dmg": 150},
                            {"range": 7.0, "rate": 2.0, "dmg": 300}]},
    "tesla": {"name": "Tesla", "cost": [140, 150, 260], "air": True,
              "blurb": "Lightning that jumps from enemy to enemy.",
              "levels": [{"range": 2.6, "rate": 0.8, "dmg": 15, "chain": 3},
                         {"range": 2.8, "rate": 0.8, "dmg": 26, "chain": 4},
                         {"range": 3.0, "rate": 0.75, "dmg": 44, "chain": 5}]},
    "beacon": {"name": "Beacon", "cost": [110, 120, 200], "air": False,
               "blurb": "Doesn't shoot. Towers beside it fire faster.",
               "levels": [{"range": 1.6, "boost": 0.2}, {"range": 1.6, "boost": 0.32}, {"range": 2.3, "boost": 0.45}]},
}

# Each enemy: health and bounty before the wave's scaling, speed in tiles a second, armour taken off
# every hit (ballistas ignore it), lives lost if it gets through.
ENEMIES = {
    "grunt": {"name": "Grunt", "hp": 30, "speed": 1.0, "bounty": 5},
    "runner": {"name": "Runner", "hp": 17, "speed": 1.9, "bounty": 4},
    "swarm": {"name": "Swarmling", "hp": 8, "speed": 1.35, "bounty": 2},
    "brute": {"name": "Brute", "hp": 150, "speed": 0.6, "bounty": 16},
    "shield": {"name": "Shieldbearer", "hp": 60, "speed": 0.8, "bounty": 10, "armor": 5},
    "flyer": {"name": "Flyer", "hp": 22, "speed": 1.3, "bounty": 6, "air": True},
    "boss": {"name": "Warlord", "hp": 400, "speed": 0.45, "bounty": 120, "armor": 3, "lives": 5},
}
KINDS = list(ENEMIES)  # snapshots name an enemy's kind by its index here


def health(wave):
    """How much tougher enemies are in a wave than in the first."""
    w = wave - 1
    return 1 + 0.45 * w + 0.06 * w * w


def bounty(wave):
    return 1 + 0.03 * (wave - 1)


def wave(w):
    """A wave as groups: (kind, how many, seconds between them, seconds before the first)."""
    n = lambda base: round(base * (1 + w / 14))  # noqa: E731
    if w % 10 == 0:
        return [("boss", w // 10, 5.0, 0), ("grunt", n(8), 0.7, 2)]
    c = w % 5
    if c == 1:
        return [("grunt", n(10), 0.8, 0)]
    if c == 2:
        return [("runner", n(9), 0.5, 0)] + ([("grunt", n(5), 0.9, 3)] if w > 5 else [])
    if c == 3:
        return [("swarm", n(22), 0.22, 0)] + ([("shield", n(3), 1.6, 2)] if w > 6 else [])
    if c == 4:
        return ([("flyer", n(7), 0.7, 0)] if w >= 4 else []) + [("shield" if w > 8 else "grunt", n(6), 1.0, 1)]
    return [("brute", n(4), 1.8, 0), ("runner", n(6), 0.5, 4)]


# Maps: each path is the corners an enemy walks between, as tile (column, row); it starts off the
# board and ends on the keep. Nothing can be built on a path or a rock.
MAPS = {
    "meadow": {"name": "Meadow", "blurb": "One long, winding road.",
               "paths": [[(-1, 2), (4, 2), (4, 8), (9, 8), (9, 3), (14, 3), (14, 9), (19, 9)]],
               "rocks": [(1, 6), (7, 1), (11, 10), (17, 4), (6, 5), (12, 6)]},
    "crossing": {"name": "Crossing", "blurb": "Two roads that meet in the middle. The hard one.",
                 "paths": [[(-1, 1), (6, 1), (6, 6), (13, 6), (13, 10), (19, 10)],
                           [(-1, 10), (6, 10), (6, 6), (13, 6), (13, 10), (19, 10)]],
                 "rocks": [(3, 5), (9, 3), (10, 9), (16, 7), (2, 7), (16, 3)]},
    "coil": {"name": "Coil", "blurb": "A long spiral in to the keep. The gentle one.",
             "paths": [[(-1, 1), (17, 1), (17, 10), (2, 10), (2, 4), (13, 4), (13, 7), (7, 7)]],
             "rocks": [(0, 6), (19, 5), (9, 11), (5, 2), (15, 6), (10, 9)]},
}


def path_tiles(m):
    tiles = set()
    for path in m["paths"]:
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            for i in range(abs(x1 - x0) + abs(y1 - y0) + 1):
                x = x0 + (x1 > x0) * i - (x1 < x0) * i
                y = y0 + (y1 > y0) * i - (y1 < y0) * i
                if 0 <= x < COLS and 0 <= y < ROWS:
                    tiles.add((x, y))
    return tiles
