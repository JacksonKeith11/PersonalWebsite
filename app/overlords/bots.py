"""Overlords' bots, and how units get arranged on a board (bots, the auto-fill at a fight's start,
and the balance tools all use `arrange`).

A bot picks two traits to aim for at the start and plays its turn the moment a planning phase
begins, through the same room methods a browser's messages reach (`buy`, `reroll`, `buy_xp`,
`sell`), then sets its board directly. Its level decides how carefully: easy bots spend at random
and level late; normal ones keep gold for interest from round 5 and level on a schedule; hard ones
keep more, level sooner and spend everything once their HP runs low.
"""

import random

from . import data as D

FRONT, BACK = 3, 0  # rows of a player's own board
CENTRE = [3, 2, 4, 1, 5, 0, 6]
CORNERS = [0, 6, 1, 5, 2, 4, 3]
SPOTS_FRONT = [(c, FRONT) for c in CENTRE] + [(c, FRONT - 1) for c in CENTRE]
SPOTS_BACK = [(c, BACK) for c in CORNERS] + [(c, BACK + 1) for c in CORNERS]

# The level a bot aims to be at by each round.
LEVEL_PLAN = {"easy": {3: 3, 6: 4, 9: 5, 12: 6, 15: 7},
              "normal": {2: 3, 4: 4, 6: 5, 9: 6, 12: 7, 15: 8},
              "hard": {2: 3, 4: 4, 5: 5, 8: 6, 11: 7, 13: 8}}
KEEP = {"easy": 0, "normal": 20, "hard": 30}  # gold kept for interest from round 5
PANIC_HP = {"easy": 0, "normal": 25, "hard": 35}  # below this, spend it all


def arrange(units, taken=()):
    """Places units ({"unit", "star"}, anything else is kept): melee on the front rows, the toughest
    in the middle; ranged on the back rows, assassins last (they leap anyway). Returns
    [(unit, col, row)], skipping `taken` spots."""
    def melee(u):
        d = D.UNITS[u["unit"]]
        return d["range"] <= 1 and "assassin" not in d["traits"]
    front = sorted((u for u in units if melee(u)), key=lambda u: -D.UNITS[u["unit"]]["hp"] * D.STAR_MULT[u["star"] - 1])
    back = sorted((u for u in units if not melee(u)), key=lambda u: "assassin" in D.UNITS[u["unit"]]["traits"])
    used, out = set(taken), []
    for group, spots in ((front, SPOTS_FRONT + SPOTS_BACK), (back, SPOTS_BACK + SPOTS_FRONT)):
        for u in group:
            spot = next((s for s in spots if s not in used), None)
            if spot is None:
                break
            used.add(spot)
            out.append((u, spot[0], spot[1]))
    return out


def random_board(rng, size, max_cost=5, two_star=0.3):
    """A plausible board of `size` different units, for tests: costs weighted towards the middle."""
    pool = [k for k in D.shop_units() if D.UNITS[k]["cost"] <= max_cost]
    weights = [6 - abs(D.UNITS[k]["cost"] - (max_cost + 1) / 2) for k in pool]
    picked = []
    while len(picked) < min(size, len(pool)):
        k = rng.choices(pool, weights)[0]
        if k not in picked:
            picked.append(k)
    units = [{"unit": k, "star": 2 if rng.random() < two_star else 1} for k in picked]
    return [{"unit": u["unit"], "star": u["star"], "col": c, "row": r} for u, c, r in arrange(units)]


def value(p, key, star=1):
    """How much a bot wants a unit: its worth in gold, more for its chosen traits and for copies it
    already has (towards a star)."""
    d = D.UNITS[key]
    v = d["cost"] * 3 ** (star - 1)
    v += 2.5 * sum(t in p.plan for t in d["traits"])
    have = sum(1 for u in p.units() if u["unit"] == key and u["star"] == star)
    return v + 2 * have


def play(room, p, rng):
    """One planning phase's worth of decisions for bot `p`."""
    level = p.bot
    if not p.plan:
        p.plan = rng.sample([t for t in D.TRAITS], 2)
    rnd = room.round
    sloppy = level == "easy"
    panic = p.hp < PANIC_HP[level]
    keep = 0 if panic or rnd < 5 else KEEP[level]

    # level up on schedule
    want = max([lv for r, lv in LEVEL_PLAN[level].items() if rnd >= r] or [1])
    while p.level < min(want, D.MAX_LEVEL) and p.gold - D.XP_COST >= (0 if panic else keep // 2):
        if not room.buy_xp(p):
            break

    # buy, rerolling if rich or desperate
    rolls = 0
    while True:
        bought = True
        while bought:
            bought = False
            options = [(value(p, k), i, k) for i, k in enumerate(p.shop) if k]
            if sloppy:
                rng.shuffle(options)
            else:
                options.sort(reverse=True)
            for v, i, k in options:
                cost = D.UNITS[k]["cost"]
                worth = v >= 3 + rnd * 0.25 or sloppy or panic
                if worth and p.gold - cost >= keep and room.buy(p, i):
                    bought = True
                    break
        if p.gold - D.REROLL >= max(keep, 50 if not panic else 0) and rolls < 8 or (panic and p.gold >= D.REROLL and rolls < 12):
            if not room.reroll(p):
                break
            rolls += 1
        else:
            break

    # the board: the most valuable units up to the level; sell what doesn't fit on the bench
    units = sorted(p.units(), key=lambda u: -value(p, u["unit"], u["star"]))
    room.set_board(p, units[:p.level])
    spare = units[p.level:]
    while len(spare) > D.BENCH - 2:
        worst = spare.pop()
        room.sell_unit(p, worst)
