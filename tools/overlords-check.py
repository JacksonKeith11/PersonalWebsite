"""Checks Overlords' rules headlessly: the data and the fight, not their balance.

    python3 tools/overlords-check.py

Every unit's traits, ability steps and selectors are known; every trait has one effect per level;
every shop unit's ability actually goes off in a fight; the same seed gives the same fight; two
copies of a unit count once towards a trait; the away board is turned round correctly; and a few
hundred random fights finish inside the time cap without errors.

Then the room: a pretend browser joins and the host starts with bots; buying, merging three copies
into a star, the bench and board limits, moving and selling all follow the rules; whole matches of
bots play to one winner on a clock the check winds on, with the shared pool never gaining or losing
a copy, and print how long a match would take in real time. Items (every one in a fight; combining;
emblems counting and refused on a unit with the trait; the Crown's extra place; items surviving
merges and sales), every commander's power, every augment, and a draft (lowest HP picks first, each
pick holds its component, the rest go back to the pool) have their own checks.
(`tools/overlords-fight.py` covers balance.)
"""

import asyncio
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.overlords import bots  # noqa: E402
from app.overlords import data as D  # noqa: E402
from app.overlords import game  # noqa: E402
from app.overlords import sim  # noqa: E402

failures = []


def check(ok, what):
    if not ok:
        failures.append(what)


def data():
    for key, t in D.TRAITS.items():
        check(len(t["fx"]) == len(t["levels"]), f"{key}: one effect per level")
        check(t["levels"] == sorted(t["levels"]), f"{key}: levels go up")
        for fx in t["fx"]:
            for k in fx:
                check(k == "who" or k in D.PLAIN_STATS or k in D.SPECIAL, f"{key}: unknown effect {k}")
    for key, u in D.UNITS.items():
        for t in u["traits"]:
            check(t in D.TRAITS, f"{key}: unknown trait {t}")
        if u.get("summon"):
            check(u["cost"] == 0 and u["tier"] == 0, f"{key}: summons cost 0")
            continue
        check(u["tier"] in D.TIERS and u["cost"] == D.PRICE[u["tier"]], f"{key}: tier and price")
        check(2 <= len(u["traits"]) <= 3, f"{key}: an origin and one or two classes")
        check(sum(D.TRAITS[t]["kind"] == "origin" for t in u["traits"] if t in D.TRAITS) == 1, f"{key}: one origin")
        check(u["ability"] is not None and u["mana"] > u["start"] >= 0, f"{key}: an ability and its mana")
        for st in u["ability"]["steps"]:
            check(st["do"] in D.STEPS, f"{key}: unknown step {st['do']}")
            if "to" in st:
                check(st["to"].partition(":")[0] in D.SELECTORS, f"{key}: unknown selector {st['to']}")
            if st["do"] == "summon":
                check(D.UNITS.get(st["unit"], {}).get("summon"), f"{key}: summons a non-summon")
            for v in st.values():
                if isinstance(v, list):
                    check(len(v) == 3, f"{key}: per-star numbers need three values")


def every_ability_fires():
    dummies = [{"unit": "iron_colossus", "col": c, "row": r} for c in (1, 3, 5) for r in (2, 3)]
    for key in D.shop_units():
        for star in (1, 2, 3):
            f = sim.Fight([{"unit": key, "star": star, "col": 3, "row": 2}], dummies, 7)
            for u in f.units:
                if u.side == 1:  # harmless and hard to kill
                    u.ad, u.ability, u.max, u.hp = 0, None, 1e6, 1e6
            res = f.run()
            uid = next(r[0] for r in res["start"] if r[2] == key)
            check(any(e[0] == "c" and e[2] == uid for e in res["events"]), f"{key} {star}*: never cast")


def determinism_and_geometry():
    rng = random.Random(5)
    home, away = bots.random_board(rng, 7), bots.random_board(rng, 7)
    a, b = sim.fight(home, away, 42), sim.fight(home, away, 42)
    check(json.dumps(a) == json.dumps(b), "the same seed gives the same fight")
    check(D.trait_counts(["ashling", "ashling", "ember_mage"]).get("emberforged") == 2, "copies count once")
    check(D.trait_level("emberforged", 3) == 0 and D.trait_level("emberforged", 1) == -1, "trait levels")
    check(sim.to_grid(1, 0, 3) == (6, 4) and sim.to_grid(0, 0, 3) == (0, 3), "the away board is turned round")
    # turning round keeps neighbours neighbours
    for c in range(sim.COLS):
        for r in range(4):
            for n in sim.neighbours((c, r)):
                if n[1] < 4:
                    check(sim.dist(sim.to_grid(1, c, r), sim.to_grid(1, *n)) == 1, "rotation keeps hexes adjacent")
    # a lone unit against nothing wins at once; two empty boards don't fight
    check(sim.fight([{"unit": "ashling", "col": 0, "row": 0}], [])["winner"] == 0, "an empty board loses")
    check(sim.fight([], [])["winner"] is None, "two empty boards")


def random_fights(n=300):
    rng = random.Random(11)
    capped = 0
    for i in range(n):
        size = rng.randint(1, 9)
        res = sim.fight(bots.random_board(rng, size), bots.random_board(rng, size), i)
        check(res["time"] <= sim.TIME_CAP + sim.DT, f"fight {i} ran past the cap")
        capped += res["time"] >= sim.TIME_CAP
        alive = {}
        for e in res["events"]:
            if e[0] == "k":
                check(alive.get(e[2], True), f"fight {i}: a unit died twice")
                alive[e[2]] = False
        check(len(json.dumps(res)) < 400_000, f"fight {i}: timeline too big to send")
    check(capped < n * 0.05, f"{capped} of {n} fights hit the time cap")


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def browser(room, name, token):
    q = asyncio.Queue(maxsize=100000)
    p = room.join(q, name, token, token)
    return p, q


def last_state(q):
    st = None
    while not q.empty():
        m = json.loads(q.get_nowait())
        if m["t"] == "state":
            st = m
    return st


def copies(room):
    total = sum(room.pool.values())
    if room.phase == "draft" and room.draft:  # options on offer are held out of the pool
        total += sum(1 for o in room.draft["options"] if o["by"] is None)
    for p in room.seated():
        total += sum(3 ** (u["star"] - 1) for u in p.units())
    return total


def room_rules():
    room = game.Room("TEST")
    room.clock = Clock()
    me, q = browser(room, "Ann", "a")
    room.handle(me, {"t": "set", "bots": True, "level": "normal"})
    room.handle(me, {"t": "start"})
    check(room.phase == "plan" and len(room.seated()) == 4, "the host starts with three bots")
    check(sum(1 for u in me.bench if u) == 1, "everyone starts with a free unit")
    full = sum(D.POOL[D.UNITS[k]["tier"]] for k in D.shop_units())
    check(copies(room) == full, "the pool and the players hold every copy")
    st = last_state(q)
    check(st and st["me"]["shop"] and len(st["players"]) == 4, "the state carries the shop and the players")
    # merging: three one-stars become a two-star where the first one on the board stood
    for u in me.units():
        room.sell_unit(me, u)
    me.gold = 100
    me.level = 3
    me.shop = ["ashling"] * D.SHOP_SIZE
    room.handle(me, {"t": "buy", "i": 0})
    room.handle(me, {"t": "move", "from": {"b": 0}, "to": {"c": 2, "r": 3}})
    room.handle(me, {"t": "buy", "i": 1})
    room.handle(me, {"t": "buy", "i": 2})
    check(len(me.units()) == 1 and me.board.get((2, 3), {}).get("star") == 2, "three copies merge on the board")
    check(me.gold == 97, "each copy costs its price")
    # the board holds as many units as the level
    me.shop = ["bramble_guard", "tide_acolyte", "grave_archer", "mire_witch", "iron_sentinel"]
    for i in range(5):
        room.handle(me, {"t": "buy", "i": i})
    for i in range(5):
        room.handle(me, {"t": "move", "from": {"b": i}, "to": {"c": i, "r": 0}})
    check(len(me.board) == 3, f"the board holds level-many units (has {len(me.board)})")
    # swapping a bench unit with a board unit is fine at the limit
    before = me.board[(0, 0)]["unit"]
    bench_i = next(i for i, u in enumerate(me.bench) if u)
    room.handle(me, {"t": "move", "from": {"b": bench_i}, "to": {"c": 0, "r": 0}})
    check(me.board[(0, 0)]["unit"] != before, "swapping onto a full board")
    # selling gives the copies back
    gold, pool = me.gold, room.pool["ashling"]
    room.handle(me, {"t": "sell", "from": {"c": 2, "r": 3}})
    check(me.gold == gold + 3 and room.pool["ashling"] == pool + 3, "selling a two-star returns three copies")
    check(not room.buy(me, 9) and not room.move(me, {"b": 99}, {"c": 0, "r": 0}, False), "nonsense is refused")
    # during a fight the board is locked but the bench isn't
    room.clock.t = room.ends + 0.01
    room.tick()
    check(room.phase == "fight" and room.fights, "the fight phase starts on time")
    spot = next(iter(me.board))
    check(not room.move(me, {"c": spot[0], "r": spot[1]}, {"b": 7}, True), "the board is locked mid-fight")
    check(copies(room) == full, "the pool still adds up")


def matches(n=3):
    secs, rounds = [], []
    for i in range(n):
        room = game.Room("SIM%d" % i)
        room.rng.seed(i)
        room.clock = Clock()
        watcher, q = browser(room, "Watcher", "w")
        room.handle(watcher, {"t": "start"})
        watcher.seated = False  # lets the bots play it out: the watcher's seat goes to a bot
        watcher.alive = False
        room.players.pop(watcher.id)
        room.to_lobby()
        room.players[watcher.id] = watcher
        watcher.seated = False
        room.start()
        full = copies(room)
        start = room.clock.t
        while room.phase != "over" and room.round < 40:
            room.clock.t = room.ends + 0.01
            room.tick()
            check(copies(room) == full, f"match {i}: the pool lost or gained copies in round {room.round}")
        check(room.phase == "over", f"match {i} never ended")
        places = sorted(p.place for p in room.seated())
        check(places == [1, 2, 3, 4], f"match {i}: places {places}")
        secs.append(room.clock.t - start)
        rounds.append(room.round)
        while not q.empty():
            q.get_nowait()
    print(f"bot matches: {rounds} rounds, about {sum(secs) / len(secs) / 60:.0f} minutes each at full timers")


def items_in_fights():
    foes = [{"unit": "iron_colossus", "star": 1, "col": c, "row": 3} for c in (2, 3, 4)]
    for item, d in D.ITEMS.items():
        home = [{"unit": "ashling", "star": 2, "col": 3, "row": 3, "items": [item]},
                {"unit": "ember_mage", "star": 2, "col": 3, "row": 0, "items": [item]}]
        try:
            sim.fight(home, foes, 3)
        except Exception as e:  # noqa: BLE001
            check(False, f"item {item}: {e!r}")
    # a few effects that must show
    f = sim.Fight([{"unit": "iron_sentinel", "col": 3, "row": 3, "items": ["spiked_hide"]}],
                  [{"unit": "ashling", "col": 3, "row": 3}], 1)
    res = f.run()
    holder = next(r[0] for r in res["start"] if r[2] == "iron_sentinel")
    check(any(e[0] == "d" and e[2] == holder and e[5] == 1 for e in res["events"]), "Spiked Hide hurts attackers")
    f = sim.Fight([{"unit": "ashling", "col": 3, "row": 3, "items": ["veil"]}],
                  [{"unit": "iron_colossus", "star": 3, "col": 3, "row": 3}], 1)
    res = f.run()
    ash = next(r[0] for r in res["start"] if r[2] == "ashling")
    check(not any(e[0] == "st" and e[2] == ash for e in res["events"]), "the Veil stops stuns")
    counts = D.trait_counts([("ashling", ["emblem_ranger"]), ("thornling", [])])
    check(counts.get("ranger") == 2, "an emblem counts towards its trait")
    check(D.combine("sword", "bow") == "ravager" and D.combine("sigil", "sigil") == "crown", "recipes")


def room_items_and_powers():
    room = game.Room("ITEM")
    room.clock = Clock()
    me, q = browser(room, "Ann", "a")
    room.handle(me, {"t": "set", "bots": True})
    room.handle(me, {"t": "start"})
    check(len(me.offers) == D.COMMANDER_CHOICES and not me.commander, "three commanders to pick from")
    room.handle(me, {"t": "commander", "k": me.offers[0]})
    check(me.commander is not None, "a commander picked")
    for u in me.units():
        room.sell_unit(me, u)
    me.items = []
    me.gold, me.level = 100, 4
    me.shop = ["ashling"] * len(me.shop)
    room.handle(me, {"t": "buy", "i": 0})
    room.handle(me, {"t": "move", "from": {"b": 0}, "to": {"c": 3, "r": 3}})
    me.items = ["sword", "bow", "sigil", "sigil", "emblem_duelist", "emblem_ranger"]
    room.handle(me, {"t": "equip", "i": 0, "to": {"c": 3, "r": 3}})
    room.handle(me, {"t": "equip", "i": 0, "to": {"c": 3, "r": 3}})
    unit = me.board[(3, 3)]
    check(unit["items"] == ["ravager"], f"two components combine (got {unit['items']})")
    check(not room.equip(me, me.items.index("emblem_duelist"), {"c": 3, "r": 3}, False), "no emblem for a trait it has")
    room.handle(me, {"t": "equip", "i": me.items.index("sigil"), "to": {"c": 3, "r": 3}})
    room.handle(me, {"t": "equip", "i": me.items.index("sigil"), "to": {"c": 3, "r": 3}})
    check("crown" in unit["items"] and me.limit() == me.level + 1, "a Crown adds a place on the board")
    check(room.equip(me, me.items.index("emblem_ranger"), {"c": 3, "r": 3}, False), "a third item fits")
    me.items.append("vest")
    check(not room.equip(me, me.items.index("vest"), {"c": 3, "r": 3}, False), "three items at most")
    # merging keeps items; selling returns them
    room.handle(me, {"t": "buy", "i": 1})
    room.handle(me, {"t": "buy", "i": 2})
    merged = me.board.get((3, 3))
    check(merged and merged["star"] == 2 and "ravager" in merged["items"], "a merged unit keeps its items")
    n, held = len(me.items), len(merged["items"])
    room.handle(me, {"t": "sell", "from": {"c": 3, "r": 3}})
    check(held == 3 and len(me.items) == n + held, "selling puts its items back on the item bench")
    # every commander's power
    for key in D.COMMANDERS:
        me.commander, me.charge, me.gold, me.level, me.xp = key, 99, 50, 3, 0
        me.bench = [None] * D.BENCH
        before = (me.gold, me.hp, len(me.items), me.free_rerolls, len(me.units()), me.level, dict(me.next_fx))
        ok = room.use_power(me)
        after = (me.gold, me.hp, len(me.items), me.free_rerolls, len(me.units()), me.level, dict(me.next_fx))
        check(ok and me.charge == 0, f"{key}: the power works when charged")
        check(key in ("oracle", "survivor") or before != after, f"{key}: the power did something")
        me.next_fx = {}
    me.commander, me.charge = "merchant", 0
    check(not room.use_power(me), "an uncharged power is refused")
    ex = game.Player(99, "x", "#fff")
    ex.commander, ex.bonus = "warlord", {"vanguard": 1}
    check(ex.extras()["front"] == {"hp_pct": 0.12} and ex.extras()["bonus"] == {"vanguard": 1}, "extras")
    # every augment
    for key in D.AUGMENTS:
        me.aug_offer = [key]
        me.bench = [None] * D.BENCH
        try:
            check(room.choose_augment(me, key), f"augment {key} applies")
        except Exception as e:  # noqa: BLE001
            check(False, f"augment {key}: {e!r}")
    check(me.bonus.get("ranger") == 3 and "emblem_ranger" in me.items and me.team_fx.get("hp"), "augments add up")


def draft():
    room = game.Room("DRFT")
    room.clock = Clock()
    me, q = browser(room, "Ann", "a")
    room.handle(me, {"t": "start"})
    for i, p in enumerate(room.seated()):
        p.hp = 50 - i * 10
        p.bench = [None] * D.BENCH
    room.round = D.DRAFT_ROUNDS[0] - 1
    full = copies(room)
    room.next_round()
    check(room.phase == "draft", "a draft round starts with the draft")
    order = room.draft["order"]
    check([room.players[i].hp for i in order] == sorted(p.hp for p in room.seated()), "lowest HP picks first")
    check(len(room.draft["options"]) == len(room.seated()) + D.DRAFT_EXTRA, "one option each, and spares")
    check(copies(room) == full, "draft options are held from the pool")
    for _ in range(40):
        if room.phase != "draft":
            break
        cur = room.players[room.draft["order"][room.draft["turn"]]]
        if cur is me:
            free = [i for i, o in enumerate(room.draft["options"]) if o["by"] is None]
            check(not room.pick(room.players[order[-1]] if order[-1] != me.id else room.players[order[0]], free[0])
                  or len(order) == 1, "only the player whose turn it is may pick")
            room.handle(me, {"t": "pick", "i": free[0]})
        else:
            room.clock.t += 1
            room.tick()
    check(room.phase == "plan", "the draft ends in planning")
    check(all(any(u["items"] for u in p.units()) for p in room.seated()), "every pick holds its component")
    check(copies(room) == full, "unpicked options go back to the pool")


data()
items_in_fights()
room_items_and_powers()
draft()
room_rules()
matches()
every_ability_fires()
determinism_and_geometry()
random_fights()
if failures:
    print("\n".join(failures[:40]))
    sys.exit(1)
print(f"ok: {len(D.shop_units())} units, {len(D.TRAITS)} traits, every ability fires, fights finish")
