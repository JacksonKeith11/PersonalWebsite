"""Overlords' bots, and how units get arranged on a board (bots, the auto-fill at a fight's start,
and the balance tools all use `arrange`).

A bot picks two traits to aim for at the start and plays its turn the moment a planning phase
begins, through the same room methods a browser's messages reach (`buy`, `reroll`, `buy_xp`,
`sell`), then sets its board directly. Each plays a style (STYLES: spend it all, save for interest,
level fast, or go all in on one trait), picked at random when the match starts. Its level decides how
carefully: easy bots spend at random and level late; normal ones buy what's
worth it and level on a schedule; hard ones level sooner, reroll everything once their HP runs low,
and try a few arrangements of their board against the one they fight next (`place`: Room.pair_up
decides opponents when planning starts), keeping the one that does best.

Bots also pick a commander (`pick_commander`), augments (`pick_augment`: hearts and souls of traits
they field, build-arounds by what their board would get, else gold, items or stats), auction bids
(`auction_bids`: each lot's worth to them, never more than their gold), draft picks (`pick_draft`: the unit they value most), use
their commander's power when it's charged (powers that give gold, rerolls, XP, units or items before
they shop, fight powers only against players), buy from the armory with gold left over after units
(the dearest first, while their units have room or it beats an item they hold), and put items on their
units (`equip`): each where it fits (`fit`: attack items on attackers, ability items on casters, armour
on the front line), the rarest on their most valuable units, emblems only for traits they aim for,
swapping a weaker item off a full unit for a better one. They pick their units' extra abilities at 2 and 3 stars
(`pick_talents`), favouring those of the traits they aim for.
"""

import random

from . import data as D
from . import sim

FRONT, BACK = 3, 0  # rows of a player's own board
CENTRE = [3, 2, 4, 1, 5, 0, 6]
CORNERS = [0, 6, 1, 5, 2, 4, 3]

# The level a bot aims to be at by each round.
LEVEL_PLAN = {"easy": {3: 3, 6: 4, 9: 5, 12: 6, 15: 7},
              "normal": {2: 3, 4: 4, 6: 5, 9: 6, 12: 7, 15: 8},
              "hard": {2: 3, 4: 4, 5: 5, 8: 6, 11: 7, 13: 8}}
# How a bot plays, picked at random when its match starts (easy bots shop at random whatever theirs):
#   tempo:  spends everything, levels on schedule;
#   econ:   banks gold from round 4, a step of interest more each round up to its cap, levels with
#           what's over, and spends it all
#           once it's on level 8 or its HP runs low;
#   fast:   levels a round early all match and favours dear units;
#   trait:  goes all in on one trait, the one it has most units of by round 5 (its units, emblem and
#           augments first).
# A reroller (staying low to three-star cheap units) was tried and dropped: with about 7 gold a round it
# reached 8 of the 9 copies by round 11, too late to pay, and placed last (3.1-3.3) in every economy tried.
STYLES = ("tempo", "econ", "fast", "trait")
ROLL_ABOVE = 50  # anyone rerolls with more gold than this over what they keep
ECON_FROM, ECON_SPEND_HP = 4, 30
TRAIT_PICK_BY = 5  # all-in trait bots settle on their trait by this round
AUCTION_SAVE = 10  # gold every style keeps on the round before an auction
LEFT = list(range(7))
RIGHT = LEFT[::-1]
# Hard bots' arrangements to try against their next opponent: (front-row order, back-row order).
SHAPES = [(CENTRE, CORNERS), (LEFT, LEFT), (RIGHT, RIGHT), (CORNERS, CENTRE)]
PLACE_TRIES = {"easy": 0, "normal": 0, "hard": len(SHAPES)}
# Powers worth using before shopping (they give gold, rerolls, XP, units or items), and powers for a fight.
SHOP_POWERS = {"quartermaster", "merchant", "gambler", "sage", "oracle", "necromancer", "twinmaker",
               "alchemist", "forgemaster"}
FIGHT_POWERS = {"warlord", "archmage", "blademaster", "hexer", "chronomancer", "beastmaster"}
PANIC_HP = {"easy": 0, "normal": 25, "hard": 35}  # below this, spend it all


def arrange(units, taken=(), front_cols=CENTRE, back_cols=CORNERS):
    """Places units ({"unit", "star"}, anything else is kept): melee on the front rows, the toughest
    first (in the middle, by default); ranged on the back rows, assassins last (they leap anyway), the
    first in the corners. `front_cols` and `back_cols` are the column orders to fill. Returns [(unit, col, row)],
    skipping `taken` spots."""
    def melee(u):
        d = D.UNITS[u["unit"]]
        return d["range"] <= 1 and "assassin" not in d["traits"]
    front = sorted((u for u in units if melee(u)), key=lambda u: -D.UNITS[u["unit"]]["hp"] * D.STAR_MULT[u["star"] - 1])
    back = sorted((u for u in units if not melee(u)), key=lambda u: "assassin" in D.UNITS[u["unit"]]["traits"])
    spots_front = [(c, FRONT) for c in front_cols] + [(c, FRONT - 1) for c in front_cols]
    spots_back = [(c, BACK) for c in back_cols] + [(c, BACK + 1) for c in back_cols]
    used, out = set(taken), []
    for group, spots in ((front, spots_front + spots_back), (back, spots_back + spots_front)):
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
    already has (towards a star). All-in trait bots want their main trait's units more; fast levellers dear ones."""
    d = D.UNITS[key]
    v = d["cost"] * 3 ** (star - 1)
    v += 2.5 * sum(t in p.plan for t in d["traits"])
    have = sum(1 for u in p.units() if u["unit"] == key and u["star"] == star)
    if p.style == "trait" and p.plan and p.plan[0] in d["traits"]:
        v += 4
    if p.style == "fast":
        v += max(0, d["tier"] - 2)
    return v + 2 * have


def keep_gold(p, rnd, panic):
    """Gold the bot won't spend on units, rerolls or items this round (it may dip 10 under it for XP):
    by style, and AUCTION_SAVE on the round before an auction."""
    if panic:
        return 0
    if rnd + 1 in D.AUCTION_ROUNDS and p.style != "econ":
        return AUCTION_SAVE
    if p.style == "econ":
        cap = (p.interest_cap + 2 * (p.commander == "merchant")) * D.INTEREST_PER
        spend = p.level >= D.MAX_LEVEL or p.hp < ECON_SPEND_HP
        return 0 if rnd < ECON_FROM or spend else min(cap, D.INTEREST_PER * (rnd - ECON_FROM + 1))
    return 0


def level_plan(p):
    """{round: level} the bot aims for, by its level and style."""
    plan = dict(LEVEL_PLAN[p.bot])
    if p.style == "fast":
        plan = {max(1, r - 1): lv for r, lv in plan.items()}
    if p.commander == "oracle" and p.bot != "easy":  # it reaches 5 a round early: its passive starts there
        first5 = min(r for r, lv in plan.items() if lv >= 5)
        plan[max(1, first5 - 1)] = max(plan.get(first5 - 1, 0), 5)
    return plan


def worth(p, u):
    return value(p, u["unit"], u["star"]) + 3 * len(u["items"])


def play(room, p, rng):
    """One planning phase's worth of decisions for bot `p`."""
    level = p.bot
    if not p.plan:
        p.plan = rng.sample([t for t in D.TRAITS], 2)
    if not p.style:
        p.style = rng.choice(STYLES)
    if p.style == "trait" and room.round <= TRAIT_PICK_BY:  # commit to the trait it's furthest along
        have = D.trait_counts([(u["unit"], u["items"]) for u in p.units()])
        best = max(D.TRAITS, key=lambda t: (have.get(t, 0), t == p.plan[0]))
        if have.get(best, 0) > have.get(p.plan[0], 0):
            p.plan = [best, p.plan[0] if p.plan[0] != best else p.plan[1]]
    rnd = room.round
    sloppy = level == "easy"
    panic = p.hp < PANIC_HP[level]
    keep = 0 if sloppy else keep_gold(p, rnd, panic)

    # powers that help the shopping go first
    charged = p.commander and p.charge >= D.COMMANDERS[p.commander]["charge"]
    if charged and (p.commander in SHOP_POWERS or sloppy):
        charged = not room.use_power(p)

    # level up on schedule
    want = max([lv for r, lv in level_plan(p).items() if rnd >= r] or [1])
    while p.level < min(want, D.MAX_LEVEL) and p.gold - D.XP_COST >= keep - 10:
        if not room.buy_xp(p):
            break

    # buy, rerolling if rich or desperate (free rerolls and the Gambler's cheap one whenever they help)
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
                good = v >= 3 + rnd * 0.25 or sloppy or panic
                if good and p.gold - cost >= keep and room.buy(p, i):
                    bought = True
                    break
        cost = 0 if p.free_rerolls else room.reroll_cost(p)
        free_ish = not sloppy and (cost == 0 or (cost < D.REROLL and p.gold - cost >= keep)) and rolls < 12
        rich = p.gold - cost >= keep + (ROLL_ABOVE if not panic else 0) and rolls < 8
        desperate = panic and p.gold >= cost and rolls < 12
        if (free_ish or rich or desperate) and any(u is None for u in p.bench):
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

    # fight powers, against players (monsters aren't worth one)
    if charged and (rnd not in D.PVE or level == "easy" or p.commander not in FIGHT_POWERS):
        if p.commander != "survivor" or p.hp <= D.START_HP - 6:
            room.use_power(p)

    # the board: the most valuable units up to the level; sell what doesn't fit on the bench
    room.set_board(p, sorted(p.units(), key=lambda u: -worth(p, u)))
    spare = sorted((u for u in p.bench if u), key=lambda u: -worth(p, u))
    while len(spare) > D.BENCH - 2:
        room.sell_unit(p, spare.pop())
    equip(room, p)
    pick_talents(room, p, rng)
    units = sorted(p.units(), key=lambda u: -worth(p, u))
    room.set_board(p, units)


def place(room, p, rng):
    """Called once every bot has played (Room.start_plan), so the boards it tries against are this round's.
    Hard bots: fight the board they meet next (or the round's monsters) with each of SHAPES, all on one
    seed, and keep the arrangement whose side ends best (who won, then the share of HP left on each side)."""
    tries = PLACE_TRIES[p.bot]
    if not tries or len(p.board) < 2:
        return
    foe = room.next_foe(p)
    if room.round in D.PVE:
        theirs = [{"unit": k, "star": s, "col": c, "row": r} for k, s, c, r in D.PVE[room.round]]
        extras = (p.extras(), {})
    elif foe and foe[0] and foe[0].board:
        theirs = foe[0].fight_board()
        extras = (p.extras(), foe[0].extras())
    else:
        return
    units = list(p.board.values())
    seed = rng.randrange(1 << 30)
    best = None
    for k, (front, back) in enumerate(SHAPES[:tries]):
        spots = arrange(units, front_cols=front, back_cols=back)
        mine = [{"unit": u["unit"], "star": u["star"], "col": c, "row": r, "items": list(u["items"]),
                 "talents": list(u["talents"])} for u, c, r in spots]
        f = sim.Fight(mine, theirs, seed, extras)
        res = f.run()
        left = [sum(x.hp / x.max for x in f.units if x.side == side and x.alive and not x.summon) for side in (0, 1)]
        score = (res["winner"] == 0) - (res["winner"] == 1) + (left[0] / len(mine) - left[1] / max(1, len(theirs))) / 2
        if best is None or score > best[0] + 1e-9:
            best = (score, spots)
    p.board = {(c, r): u for u, c, r in best[1]}


# What each part of an item's fx is for: attacking, casting, or standing in front.
ATTACK_FX = {"ad", "aspd_pct", "crit", "critdmg", "shred", "omnivamp", "splash", "pct_hit", "chill_on_hit",
             "low_bonus", "frenzy", "multishot", "on_kill", "wound_on_hit", "execute", "mana_on_hit"}
CAST_FX = {"ap", "mana", "cast_share", "cast_grow_ap", "cast_mana", "cast_heal", "ability_crit", "echo", "every3"}
TANK_FX = {"hp", "armor", "mr", "dr", "shield", "spell_dr", "chill", "regen", "taunt_start", "thorns",
           "cc_immune", "grow_hp", "last_stand", "revive", "low_heal", "aura", "dodge"}


def item_role(item):
    """(attack, cast, tank) shares of an item's fx, summing to 1 (all 0 for one that suits anyone)."""
    fx = D.ITEMS[item]["fx"]
    n = [sum(k in group for k in fx) for group in (ATTACK_FX, CAST_FX, TANK_FX)]
    total = sum(n)
    return [x / total for x in n] if total else [0, 0, 0]


def unit_role(key):
    """(attack, cast, tank) weights for a unit, from its classes and range."""
    d = D.UNITS[key]
    tr = d["traits"]
    melee = d["range"] <= 1 and "assassin" not in tr
    tank = 1.0 if {"vanguard", "warden"} & set(tr) else 0.6 if melee else 0.0
    attack = 1.0 if {"duelist", "ranger", "assassin"} & set(tr) else 0.4
    cast = 1.0 if {"arcanist", "mystic", "summoner"} & set(tr) else 0.4
    return attack, cast, tank


def fit(p, u, item):
    """How much the bot wants `item` on unit u: the unit's worth, more where the item suits it."""
    role = item_role(item)
    if not any(role):
        return worth(p, u)
    match = sum(a * b for a, b in zip(role, unit_role(u["unit"])))
    return worth(p, u) * (0.4 + match)


def equip(room, p):
    """Puts the bot's items on its board, rarest first, each on the unit it fits best (`fit`): emblems only
    for the traits it aims for, where they add the trait. When every unit is full, a rarer item from the
    bench takes the place of the least rare one on the unit it fits best (which goes back to the bench)."""
    usable = lambda item: D.ITEMS[item]["kind"] != "emblem" or D.ITEMS[item]["trait"] in (p.plan or [])
    for _ in range(len(p.items) + 2 * D.MAX_ITEMS * len(p.board)):
        order = sorted((i for i, it in enumerate(p.items) if usable(it)), key=lambda i: -D.ITEMS[p.items[i]]["rarity"])
        done = False
        for i in order:
            item = p.items[i]
            for (c, r), u in sorted(p.board.items(), key=lambda kv: -fit(p, kv[1], item)):
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
        item = p.items[best]
        rarity = D.ITEMS[item]["rarity"]
        swap = None
        for (c, r), u in sorted(p.board.items(), key=lambda kv: -fit(p, kv[1], item)):
            weak = [(D.ITEMS[it]["rarity"], k) for k, it in enumerate(u["items"])
                    if D.ITEMS[it]["kind"] == "item" and D.ITEMS[it]["rarity"] < rarity]
            if weak:
                swap = (c, r, min(weak)[1])
                break
        if not swap or not room.unequip(p, {"c": swap[0], "r": swap[1]}, swap[2], False):
            break
        if not room.equip(p, p.items.index(item), {"c": swap[0], "r": swap[1]}, False):
            break


def pick_talents(room, p, rng):
    """An extra ability for each unit waiting for one: rather one of a trait the bot aims for, else any."""
    for u in p.units():
        while room.talent_offer(u):
            offer = room.talent_offer(u)
            k = max(offer, key=lambda k: (D.TALENTS[k]["trait"] in (p.plan or [])) * 1.5 + rng.random())
            if not room.choose_talent(p, u["id"], k):
                break


def pick_commander(p, rng):
    return rng.choice(p.offers)


def build_outlook(p, count):
    """How many a `per` build-around would count on the bot's board once it's built: what it counts now,
    plus what the traits it aims for should add (its board grows by a unit or two after each augment
    round). Before late November 2026 bots went by the count now alone and almost never took Kinship or
    Spellweave, which reward a board still to come."""
    n = p.build_count(count)
    if count.startswith("gold"):
        return n / 3
    plan = set(p.plan or [])
    if count.startswith("units:") and plan & set(count[6:].split(",")):
        n += 2
    elif count == "kin" and any(D.TRAITS[t]["kind"] == "origin" for t in plan):
        n += 2
    return n


def pick_augment(p, offer, rng):
    """Hearts and souls of a trait the bot fields or aims for, then crests of one; build-arounds by how
    much its board should get from them (`build_outlook`); then the rest."""
    mine = set(p.traits()) | set(p.plan or [])
    def score(k):
        a = D.AUGMENTS[k]
        if a.get("trait"):
            return 3 if a["trait"] in mine else 0
        if "per" in a:
            return 1 + 0.5 * min(5, build_outlook(p, a["per"]["count"]))
        if "when" in a:
            return 3.5 if p.build_count("origins") >= a["when"]["origins"] - 1 else 0.5
        if "stars" in a:
            return 1 + 0.6 * sum(1 for u in p.units() if u["star"] >= a["stars"]["min"])
        return 2
    return max(offer, key=lambda k: (score(k), rng.random()))


AUCTION_WORTH = {"item": 12, "legion": 16, "war_banner": 11, "ancestral_echo": 9, "iron_will": 9}
AUCTION_LIKES = {"econ": "war_banner", "fast": "legion", "tempo": "item"}  # each style's favourite lot


def auction_bids(room, p, lots, rng):
    """Sealed bids on the auction's lots: each lot's worth to the bot (a unit by `value`, plus its item;
    more for its style's favourite, AUCTION_LIKES), with some luck so bots don't all want the same lot,
    each bid no more than its gold (it can only win one)."""
    worth = []
    for lot in lots:
        if lot["kind"] == "unit":
            w = value(p, lot["unit"], lot["star"]) + 2 * D.ITEMS[lot["item"]]["rarity"]
        elif lot["kind"] == "item":
            w = AUCTION_WORTH["item"]
        else:
            w = AUCTION_WORTH.get(lot["augment"], 9)
            if lot["augment"] == "legion" and p.level < 6:
                w -= 5
        name = lot.get("augment") or lot["kind"]
        if AUCTION_LIKES.get(p.style) == name or (p.style == "trait" and lot["kind"] == "unit"
                                                   and p.plan and p.plan[0] in D.UNITS[lot["unit"]]["traits"]):
            w *= 1.6
        worth.append(w * rng.uniform(0.7, 1.3))
    bids = [0] * len(lots)
    for i in range(len(lots)):
        b = round(worth[i] * rng.uniform(0.5, 1.0))
        if p.bot == "easy":
            b = rng.randint(0, 10)
        b = min(b, p.gold)
        if b >= lots[i]["min"]:
            bids[i] = b
    return bids


def pick_draft(p, options, rng):
    free = [i for i, o in enumerate(options) if o["by"] is None]
    return max(free, key=lambda i: (value(p, options[i]["unit"]), rng.random()))
