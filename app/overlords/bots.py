"""Overlords' bots, and how units get arranged on a board (bots, the auto-fill at a fight's start,
and the balance tools all use `arrange`).

A bot picks two traits to aim for at the start and plays its turn the moment a planning phase
begins, through the same room methods a browser's messages reach (`buy`, `reroll`, `buy_xp`,
`sell`), then sets its board directly. Its level decides how carefully: easy bots spend at random
and level late; normal ones keep gold for interest from round 5 and level on a schedule; hard ones
keep more, level sooner and spend everything once their HP runs low.

Bots also pick a commander (`pick_commander`), augments (`pick_augment`: hearts and souls of traits
they field, else gold, items or stats), draft picks (`pick_draft`: the unit they value most), use
their commander's power when it's charged, buy from the armory with gold left over after units
(the dearest first, while their units have room or it beats an item they hold), and put items on their
units: the rarest on their most valuable units, emblems only for traits they aim for, swapping a weaker
item off a full unit for a better one.
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
    pool = [k for k in D.shop_units() if D.UNITS[k]["tier"] <= max_cost]
    weights = [6 - abs(D.UNITS[k]["tier"] - (max_cost + 1) / 2) for k in pool]
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

    # the armory, with the gold left over: artifacts first, while their units have room for items
    room_for = sum(D.MAX_ITEMS - len(u["items"]) for u in p.units())
    stock = sorted(((room.item_price(k, p), i) for i, k in enumerate(p.armory)
                    if k and (D.ITEMS[k]["kind"] != "emblem" or D.ITEMS[k]["trait"] in (p.plan or []))), reverse=True)
    for price, i in stock:
        weakest = min([D.ITEMS[it]["rarity"] for u in p.units() for it in u["items"]] or [9])
        better = D.ITEMS[p.armory[i]]["rarity"] > weakest  # worth swapping in even when every slot is full
        if (len(p.items) < room_for or better) and p.gold - price >= keep:
            room.buy_item(p, i)

    # the commander's power, when charged
    if p.commander and p.charge >= D.COMMANDERS[p.commander]["charge"]:
        room.use_power(p)

    # the board: the most valuable units up to the level; sell what doesn't fit on the bench
    units = sorted(p.units(), key=lambda u: -(value(p, u["unit"], u["star"]) + 3 * len(u["items"])))
    room.set_board(p, units)
    spare = [u for u in p.bench if u]
    spare.sort(key=lambda u: -(value(p, u["unit"], u["star"]) + 3 * len(u["items"])))
    while len(spare) > D.BENCH - 2:
        worst = spare.pop()
        room.sell_unit(p, worst)
    equip(room, p)
    units = sorted(p.units(), key=lambda u: -(value(p, u["unit"], u["star"]) + 3 * len(u["items"])))
    room.set_board(p, units)


def equip(room, p):
    """Puts the bot's items on its board, rarest first onto its most valuable units: emblems only for
    the traits it aims for, where they add the trait. When a unit is full, a rarer item from the bench
    takes the place of its least rare one (which goes back to the bench)."""
    board = sorted(p.board.items(), key=lambda kv: -value(p, kv[1]["unit"], kv[1]["star"]))
    usable = lambda item: D.ITEMS[item]["kind"] != "emblem" or D.ITEMS[item]["trait"] in (p.plan or [])
    for _ in range(len(p.items) + 2 * D.MAX_ITEMS * len(board)):
        order = sorted((i for i, it in enumerate(p.items) if usable(it)), key=lambda i: -D.ITEMS[p.items[i]]["rarity"])
        done = False
        for i in order:
            for (c, r), u in board:
                if room.equip(p, i, {"c": c, "r": r}, False):
                    done = True
                    break
            if done:
                break
        if done:
            continue
        # every unit full (or refusing): swap a weaker item out for the rarest one waiting
        best = order[0] if order else None
        if best is None or D.ITEMS[p.items[best]]["kind"] == "emblem":
            break
        rarity = D.ITEMS[p.items[best]]["rarity"]
        swap = None
        for (c, r), u in board:
            for k, it in enumerate(u["items"]):
                if D.ITEMS[it]["kind"] == "item" and D.ITEMS[it]["rarity"] < rarity:
                    swap = (c, r, k)
                    break
            if swap:
                break
        if not swap or not room.unequip(p, {"c": swap[0], "r": swap[1]}, swap[2], False):
            break
        item = p.items[best]
        if not room.equip(p, p.items.index(item), {"c": swap[0], "r": swap[1]}, False):
            break


def pick_commander(p, rng):
    return rng.choice(p.offers)


def pick_augment(p, offer, rng):
    """Hearts and souls of a trait the bot fields or aims for, then crests of one, then the rest."""
    mine = set(p.traits()) | set(p.plan or [])
    def score(k):
        a = D.AUGMENTS[k]
        if a.get("trait"):
            return 3 if a["trait"] in mine else 0
        return 2
    return max(offer, key=lambda k: (score(k), rng.random()))


def pick_draft(p, options, rng):
    free = [i for i, o in enumerate(options) if o["by"] is None]
    return max(free, key=lambda i: (value(p, options[i]["unit"]), rng.random()))
