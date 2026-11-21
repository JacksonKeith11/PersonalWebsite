"""Checks Overlords' rules headlessly: the data and the fight, not their balance.

    python3 tools/overlords-check.py

Every unit's traits, ability steps and selectors are known; every trait has one effect per level;
every shop unit's ability actually goes off in a fight; the same seed gives the same fight; two
copies of a unit count once towards a trait; the away board is turned round correctly; and a few
hundred random fights finish inside the time cap without errors.

Then the room: a pretend browser joins and the host starts with bots; buying, merging three copies
into a star, the bench and board limits, moving and selling all follow the rules; whole matches of
bots play to one winner on a clock the check winds on, with the shared pool never gaining or losing
a copy, and print how long a match would take in real time. Items (every one in a fight; rarities
and prices rising; the armory's odds; equipping and taking off; emblems counting and refused on a unit
with the trait; the Crown's extra place; items surviving merges and sales), every commander's power,
every augment, a draft (lowest HP picks first, each pick holds an item of the round's rarity, the
rest go back to the pool), and extra abilities (three or four to pick from at 2 and 3 stars, picked once,
kept through a merge, lost with a sale, each working in a fight) have their own checks, and so do the unit
cards' numbers (traits, items, picks and augments counted on the board; items and picks on the bench).
The roster review's tricks (taunts, vanishing, pulls, shoves, zones, delayed blows, raising,
swallowing, executes, wounds, multishot, death bursts, the Hexer's and Chronomancer's effects, saplings)
each get a staged fight, and some random fights are stepped to make sure no two units share a hex.
(`tools/overlords-fight.py` covers balance.)
"""

import asyncio
import json
import os
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["OVERLORDS_DB"] = os.path.join(tempfile.mkdtemp(prefix="overlords-check-"), "overlords.db")

from app.overlords import bots  # noqa: E402
from app.overlords import data as D  # noqa: E402
from app.overlords import game  # noqa: E402
from app.overlords import save as SAVE  # noqa: E402
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


def B(unit, c, r, star=1, items=()):
    return {"unit": unit, "star": star, "col": c, "row": r, "items": list(items)}


def mechanics():
    """The roster review's tricks each do what they say."""
    def first(f, key, side=0):
        return next(u for u in f.units if u.key == key and u.side == side)

    def cast(f, u):
        u.target = f.nearest(u, f.foes(u))
        u.mana = u.maxmana
        f.cast(u)

    f = sim.Fight([B("bramble_guard", 3, 3)], [B("wolf", 2, 3), B("wolf", 4, 3)], 1)
    g = first(f, "bramble_guard")
    cast(f, g)
    check(all(w.taunt[0] is g for w in f.units if w.side == 1), "a taunt makes enemies attack the taunter")
    f = sim.Fight([B("marsh_lurker", 3, 3)], [B("wolf", 3, 3)], 1)
    m, w = first(f, "marsh_lurker"), first(f, "wolf", 1)
    cast(f, m)
    check(m not in f.foes(w) and f.later, "a vanished unit can't be targeted, and its blow is on the way")
    f.t += 1.1
    f.tick()
    check(any(e[0] == "d" and e[2] == m.id for e in f.events), "the delayed blow lands")
    f = sim.Fight([B("toad_brawler", 3, 3)], [B("wolf", 0, 0), B("wolf", 3, 3)], 1)
    t = first(f, "toad_brawler")
    far = max((u for u in f.units if u.side == 1), key=lambda u: sim.dist(u.hex, t.hex))
    cast(f, t)
    check(sim.dist(far.hex, t.hex) == 1, "a pull drags the farthest enemy next to the caster")
    f = sim.Fight([B("cloud_monk", 3, 3)], [B("wolf", 3, 3)], 1)
    c, w = first(f, "cloud_monk"), first(f, "wolf", 1)
    f.jump(w, sim.free_hex if False else next(n for n in sim.neighbours(c.hex) if n not in f.occ and n[1] > c.hex[1]))
    before = sim.dist(c.hex, w.hex)
    cast(f, c)
    check(sim.dist(c.hex, w.hex) > before, "a knockback shoves the target away")
    f = sim.Fight([B("thorn_dryad", 3, 0)], [B("stone_golem", 3, 3)], 1)
    d, s_ = first(f, "thorn_dryad"), first(f, "stone_golem", 1)
    cast(f, d)
    hp = s_.hp
    for _ in range(20):
        f.tick()
        f.t += sim.DT
    check(f.zones and s_.hp < hp, "a zone hurts enemies standing in it")
    f = sim.Fight([B("lich", 3, 0)], [B("wolf", 3, 3)], 1)
    li = first(f, "lich")
    f.corpses.append((0, 5))
    cast(f, li)
    check(any(u.key == "skeleton" and u.hex == (0, 5) for u in f.units), "raise brings skeletons up where units fell")
    f = sim.Fight([B("bog_colossus", 3, 3)], [B("bandit", 3, 3)], 1)
    b, x = first(f, "bog_colossus"), first(f, "bandit", 1)
    cast(f, b)
    check(x.hidden(f.t) and x.stun > f.t, "a swallowed unit can't act or be reached")
    f = sim.Fight([B("grave_digger", 3, 3)], [B("bandit", 3, 3)], 1)
    gd, x = first(f, "grave_digger"), first(f, "bandit", 1)
    x.hp = x.max * 0.25
    cast(f, gd)
    check(not x.alive, "an execute finishes a target left below its threshold")
    f = sim.Fight([B("thornling", 3, 3)], [B("bandit", 3, 3)], 1)
    th, x = first(f, "thornling"), first(f, "bandit", 1)
    cast(f, th)
    x.hp = 100
    f.heal(x, 200, x)
    check(x.alive and round(x.hp) == 200, "a wounded unit heals half as much")
    f = sim.Fight([B("star_archer", 3, 0)], [B("bandit", 2, 3), B("bandit", 3, 3)], 1)
    a = first(f, "star_archer")
    f.attack(a, f.nearest(a, f.foes(a)))
    check(sum(e[0] == "a" for e in f.events) == 2, "multishot strikes a second enemy")
    f = sim.Fight([B("bone_rattler", 3, 3)], [B("wolf", 3, 3)], 1)
    r, w = first(f, "bone_rattler"), first(f, "wolf", 1)
    f.jump(w, next(n for n in sim.neighbours(r.hex) if n not in f.occ))
    hp = w.hp
    f.die(r)
    check(w.hp < hp, "a death burst hurts the enemies beside it")
    f = sim.Fight([B("ashling", 3, 3, 2), B("ember_mage", 3, 0)], [B("ashling", 3, 3, 2), B("ember_mage", 3, 0)], 1,
                  ({"hex_strongest": 0.2, "drain": [0.5, 8]}, {}))
    foe = [u for u in f.units if u.side == 1]
    check(any(u.amp[0] == 0.2 for u in foe) and all(u.mana == 0 and u.mana_slow[0] == 0.5 for u in foe),
          "the Hexer's and the Chronomancer's effects reach the enemy")
    f = sim.Fight([B("sky_lancer", 3, 3, 1, ["world_seed"])], [B("stone_golem", 3, 3)], 1)
    for _ in range(int(6.2 / sim.DT)):
        f.tick()
        f.t += sim.DT
    check(any(u.key == "sapling" for u in f.units), "the Seed of the Elder Grove grows a sapling")
    # an Ember Mantle's burn kills a foe whose death burst kills the holder: the holder mustn't act after
    f = sim.Fight([B("sky_lancer", 3, 3, 1, ["ember_mantle"])], [B("bone_rattler", 3, 3)], 1)
    h, r = first(f, "sky_lancer"), first(f, "bone_rattler", 1)
    f.jump(r, next(n for n in sim.neighbours(h.hex) if n not in f.occ))
    h.hp, r.hp, h.mana = 1, 0.001, h.maxmana
    f.tick()
    check(not h.alive and not any(e[0] == "c" and e[2] == h.id for e in f.events),
          "a unit killed by a death burst in its own turn doesn't go on to act")


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
        if i % 25 == 0:  # nobody ever shares a hex (raising, pulls and shoves move units about)
            f = sim.Fight(bots.random_board(rng, size), bots.random_board(rng, size), i)
            while f.t < sim.TIME_CAP and f.alive(0) and f.alive(1):
                f.tick()
                f.t += sim.DT
                living = [u for u in f.units if u.alive]
                if len({u.hex for u in living}) != len(living) or set(f.occ) != {u.hex for u in living}:
                    check(False, f"fight {i}: two units on one hex, or the board's record is wrong, at {f.t:.2f}")
                    break
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
    if room.phase == "auction" and room.auction:  # so is the auction's unit (three copies)
        total += sum(3 for lot in room.auction["lots"] if lot["kind"] == "unit")
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
    room.handle(me, {"t": "commander", "k": me.offers[0]})
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


def pairing():
    """Opponents are paired when planning starts; the fights follow those pairs; hard bots arrange
    against the board they'll meet; someone leaving mid-plan gets everyone paired again."""
    room = game.Room("PAIR")
    room.rng.seed(5)
    room.clock = Clock()
    room.saving = False
    me, q = browser(room, "Ann", "a")
    room.handle(me, {"t": "set", "bots": True, "level": "hard"})
    room.handle(me, {"t": "start"})
    room.handle(me, {"t": "commander", "k": me.offers[0]})
    while not (room.phase == "plan" and room.round not in D.PVE):
        room.clock.t = room.ends + 0.01
        room.tick()
    ids = sorted(i for pair in room.next_pairs for i in pair[:2])
    check(ids == sorted(p.id for p in room.alive()), f"planning starts with everyone paired ({room.next_pairs})")
    st = last_state(q)
    check(st and st["pairs"] == [list(x) for x in room.next_pairs], "the browsers see the pairs")
    foe = room.next_foe(me)
    check(foe and foe[0] and foe[0].id != me.id, "next_foe names Ann's opponent")
    bot = next(p for p in room.alive() if p.bot)
    tried = []
    real = game.B.sim.Fight
    class Spy(real):
        def run(self):
            tried.append(1)
            return real.run(self)
    game.B.sim.Fight = Spy
    try:
        game.B.place(room, bot, room.rng)
    finally:
        game.B.sim.Fight = real
    check(len(bot.board) < 2 or len(tried) == len(game.B.SHAPES), f"a hard bot tries {len(tried)} arrangements")
    pairs = list(room.next_pairs)
    room.clock.t = room.ends + 0.01
    room.tick()
    check(room.phase == "fight" and [(f["home"], f["away"], f["ghost"]) for f in room.fights] == pairs,
          "the fights are the pairs shown while planning")
    room.clock.t = room.ends + 0.01
    room.tick()
    while not (room.phase == "plan" and room.round not in D.PVE):
        room.clock.t = room.ends + 0.01
        room.tick()
    gone = next(p for p in room.alive() if p.bot)
    room.forfeit(gone)
    ids = sorted(i for pair in room.next_pairs for i in pair[:2])
    check(gone.id not in ids and set(ids) == {p.id for p in room.alive()}, "someone leaving gets everyone paired again")
    check(len(room.alive()) % 2 == 0 or any(g for _, _, g in room.next_pairs), "an odd number means a ghost fight")
    while not q.empty():
        q.get_nowait()


def auction():
    """The auction at D.AUCTION_ROUNDS: three lots, sealed bids checked, the highest bid wins and pays,
    unsold units go back to the pool, results shown while planning; relics only here."""
    room = game.Room("AUCT")
    room.rng.seed(8)
    room.clock = Clock()
    room.saving = False
    me, q = browser(room, "Ann", "a")
    room.handle(me, {"t": "set", "bots": True, "level": "normal"})
    room.handle(me, {"t": "start"})
    room.handle(me, {"t": "commander", "k": me.offers[0]})
    full = copies(room)
    while room.phase != "auction" and room.round < 12:
        room.clock.t = room.ends + 0.01
        room.tick()
        if me.aug_offer:
            room.handle(me, {"t": "augment", "k": me.aug_offer[0]})
        if not me.alive:
            break
    check(room.phase == "auction" and room.round == D.AUCTION_ROUNDS[0], f"an auction at round {D.AUCTION_ROUNDS[0]}")
    if room.phase != "auction":
        return
    lots = room.auction["lots"]
    check([lot["kind"] for lot in lots] == ["unit", "item", "augment"], "three lots: a unit, a relic, an augment")
    check(lots[0]["star"] == 2 and D.ITEMS[lots[1]["item"]]["kind"] == "relic" and D.AUGMENTS[lots[2]["augment"]]["tier"] == 4,
          "a two-star unit, a relic and an auction augment")
    check(copies(room) == full, "the auction's unit is held out of the pool")
    st = last_state(q)
    check(st and st["phase"] == "auction" and len(st["auction"]["lots"]) == 3 and "bids" not in st["auction"],
          "the browsers see the lots but not the bids")
    me.gold = 200
    check(not room.bid(me, [150, 30, 21]) and not room.bid(me, [2, 0, 0]) and not room.bid(me, [5, 5]),
          "bids over your gold, under the minimum or the wrong length are refused")
    check(room.bid(me, [150, 30, 20]), "a fair set of bids is taken")
    room.handle(me, {"t": "buy", "i": 0})
    check(me.gold == 200, "no shopping during the auction")
    room.tick()  # every person has bid: it closes at once
    check(room.phase in ("plan", "draft"), "the auction closes once everyone has bid")
    won = [r for r in room.auction_results["results"] if r[1] == me.id]
    check(won == [[0, me.id, 150]] and me.gold == 50, f"Ann's top bid takes its lot and she pays it, one lot only ({won})")
    check(lots[1]["item"] not in me.items and lots[2]["augment"] not in me.augments, "the other lots aren't Ann's")
    check(any(u["unit"] == lots[0]["unit"] and lots[0]["item"] in u["items"] for u in me.units())
          or lots[0]["item"] in me.items, "the unit joins Ann's bench with its item")
    check(copies(room) == full, "the pool still adds up after the auction")
    st = last_state(q)
    check(st and st.get("auction_results"), "the results are shown while planning")
    relics = {k for k, i in D.ITEMS.items() if i["kind"] == "relic"}
    drawn = {room.random_item(r) for r in (1, 2, 3, 4) for _ in range(300)}
    check(not (relics & drawn), "relics never turn up in the armory")
    # nobody bids: the unit goes back to the pool
    room2 = game.Room("AUC2")
    room2.rng.seed(9)
    room2.clock = Clock()
    room2.saving = False
    room2.bots = True
    room2.start()
    while room2.round < D.AUCTION_ROUNDS[0] - 1:
        room2.clock.t = room2.ends + 0.01
        room2.tick()
    for p in room2.alive():
        p.gold = 0
    full2 = copies(room2)
    while room2.phase != "auction":
        room2.clock.t = room2.ends + 0.01
        room2.tick()
    for p in room2.alive():
        room2.auction["bids"][p.id] = [0, 0, 0]
    room2.clock.t = room2.ends + 0.01
    room2.tick()
    check(all(r[1] is None for r in room2.auction_results["results"]) and copies(room2) == full2,
          "unsold lots: the unit goes back to the pool")
    while not q.empty():
        q.get_nowait()


def build_arounds():
    """Augments that grow with the board work out right, reach the fight and the unit cards; auction
    augments never come up at the usual augment rounds."""
    room = game.Room("BLD")
    p = game.Player(1, "Ann", "#fff")
    p.level = 6
    units = [("ember_mage", 2, (3, 0)), ("star_queen", 1, (2, 0)), ("iron_sentinel", 2, (3, 3)),
             ("iron_recruit", 1, (2, 3)), ("ashling", 1, (4, 3))]
    for key, star, h in units:
        p.board[h] = room.new_unit(key, star)
    casters = p.build_count("units:arcanist,mystic,summoner")
    check(p.build_count("front") == 3, "a build-around counts the front row")
    p.augments = ["spellweave", "shield_wall", "war_chest", "elite_guard", "giants_heart"]
    p.gold = 31
    ex = p.extras()
    check(ex["team"].get("ap") == 10 * casters and casters >= 1, f"Spellweave: 10 ability power a caster ({casters})")
    check(ex["front"].get("armor") == 24 and ex["team"].get("ad") == 10, "Shield Wall's front row; War Chest's gold")
    check(ex["stars"] == [[2, D.AUGMENTS["elite_guard"]["stars"]["fx"]]] and ex["convert"] == {"hp_to_ad": [200, 20]},
          "Elite Guard and Giant's Heart reach the fight")
    cards = p.card_stats()
    plain = game.Player(2, "Bo", "#000")
    plain.board = p.board
    bare = plain.card_stats()
    sentinel = p.board[(3, 3)]["id"]
    check(cards[sentinel]["ad"] > bare[sentinel]["ad"] and cards[sentinel]["hp"] > bare[sentinel]["hp"],
          "the unit cards count build-arounds")
    f = sim.Fight([B("iron_sentinel", 3, 3, 1, ["belt", "vest"])], [B("wolf", 3, 3)], 1,
                  ({"convert": {"hp_to_ad": [200, 20], "res_to_ap": 0.5}}, {}))
    u = next(u for u in f.units if u.key == "iron_sentinel")
    check(round(u.ad) == round(D.UNITS["iron_sentinel"]["ad"] + 20) and round(u.ap) == 120,
          "conversions turn extra HP into attack and armor into ability power")
    p.augments = []
    room.apply_augment(p, "legion")
    check(p.limit() == p.level + 1, "Legion: one more board place")
    room.apply_augment(p, "iron_will")
    check(p.extras()["front"].get("cc_immune") == 1, "Iron Will reaches the front row")
    room.round = 13
    offered = set()
    for _ in range(200):
        p.augments = []
        room.offer_augments(p)
        offered.update(p.aug_offer)
    check(not any(D.AUGMENTS[k]["tier"] == 4 for k in offered), "auction augments never come up as an ordinary pick")
    check(any(k in offered for k in ("giants_heart", "runeplate", "quickening", "melting_pot", "elite_guard")),
          "grand build-arounds do come up")


def matches(n=3):
    secs, rounds = [], []
    for i in range(n):
        room = game.Room("SIM%d" % i)
        room.rng.seed(i)
        room.clock = Clock()
        room.saving = False
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
        check(all(p.style in game.B.STYLES for p in room.seated()), f"match {i}: every bot plays a style")
        secs.append(room.clock.t - start)
        rounds.append(room.round)
        while not q.empty():
            q.get_nowait()
    print(f"bot matches: {rounds} rounds, about {sum(secs) / len(secs) / 60:.0f} minutes each at full timers")


def art():
    """Every unit, summon and monster has a row in the sprite atlas, every item and trait an icon and every
    commander a portrait (tools/overlords-art/build.py)."""
    text = (Path(__file__).resolve().parent.parent / "app/static/games/overlords/js/atlas.js").read_text()
    rows = json.loads(text.split("export const ROWS = ", 1)[1].split(";", 1)[0])
    missing = [k for k in D.UNITS if k not in rows]
    check(not missing, f"no sprite for {missing}: run tools/overlords-art/build.py")
    icons = json.loads(text.split("export const ICONS = ", 1)[1].split(";", 1)[0])
    missing = [k for k in D.ITEMS if "item:" + k not in icons] + [t for t in D.TRAITS if "trait:" + t not in icons]
    check(not missing, f"no icon for {missing}: draw one in tools/overlords-art/icons.py and build")
    pics = json.loads(text.split("export const PORTRAITS = ", 1)[1].split(";", 1)[0])
    missing = [k for k in D.COMMANDERS if k not in pics]
    check(not missing, f"no portrait for {missing}: draw one in tools/overlords-art/portraits.py and build")


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
    check(all(i.get("rarity") in D.RARITIES for i in D.ITEMS.values()), "every item has a rarity")
    check(all(D.ITEM_PRICE[r] < D.ITEM_PRICE[r + 1] for r in (1, 2, 3)), "rarer items cost more")
    check(all(len(D.items_of(r)) >= 5 for r in D.RARITIES), "every rarity has items to sell")
    check(all(sum(o) == 100 for _, o in D.ARMORY_ODDS), "the armory's odds add up")
    check(D.armory_odds(1)[3] == 0 and D.armory_odds(30)[3] > 0, "Legendary items come late")


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
    me.items = ["ravager", "crown", "emblem_duelist", "emblem_ranger"]
    room.handle(me, {"t": "equip", "i": 0, "to": {"c": 3, "r": 3}})
    unit = me.board[(3, 3)]
    check(unit["items"] == ["ravager"], f"an item goes on a unit (got {unit['items']})")
    check(not room.equip(me, me.items.index("emblem_duelist"), {"c": 3, "r": 3}, False), "no emblem for a trait it has")
    room.handle(me, {"t": "equip", "i": me.items.index("crown"), "to": {"c": 3, "r": 3}})
    check("crown" in unit["items"] and me.limit() == me.level + 1, "a Crown adds a place on the board")
    check(room.equip(me, me.items.index("emblem_ranger"), {"c": 3, "r": 3}, False), "a third item fits")
    # taking items off
    room.handle(me, {"t": "unequip", "from": {"c": 3, "r": 3}, "k": unit["items"].index("emblem_ranger")})
    check("emblem_ranger" in me.items and "emblem_ranger" not in unit["items"], "an item comes off, back to the item bench")
    check(not room.unequip(me, {"c": 3, "r": 3}, 9, False) and not room.unequip(me, {"b": 7}, 0, False), "nonsense is refused")
    check(not room.unequip(me, {"c": 3, "r": 3}, 0, True), "nothing comes off the board mid-fight")
    room.equip(me, me.items.index("emblem_ranger"), {"c": 3, "r": 3}, False)
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
        if key == "twinmaker":  # it twins a unit you have
            me.bench[0] = room.new_unit("ashling")
            room.pool["ashling"] -= 1
        before = (me.gold, me.hp, len(me.items), me.free_rerolls, len(me.units()), me.level, me.xp, dict(me.next_fx))
        ok = room.use_power(me)
        after = (me.gold, me.hp, len(me.items), me.free_rerolls, len(me.units()), me.level, me.xp, dict(me.next_fx))
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
    check(all(any(u["items"] for u in p.units()) for p in room.seated()), "every pick holds its item")
    check(copies(room) == full, "unpicked options go back to the pool")


def commander_wait_and_exit():
    """The first fight waits for a connected person still choosing a commander (no auto-pick), but not for
    one who has left. Exit knocks a person out on the spot; when only bots are left standing, it's over."""
    room = game.Room("WAIT")
    room.rng.seed(5)
    room.clock = Clock()
    ann, qa = browser(room, "Ann", "tok-a")
    bo, qb = browser(room, "Bo", "tok-b")
    room.handle(ann, {"t": "start"})
    room.handle(bo, {"t": "commander", "k": bo.offers[0]})
    for _ in range(3):
        room.clock.t = room.ends + 5
        room.tick()
    check(room.phase == "plan" and room.round == 1 and not ann.commander, "the first fight waits while Ann chooses")
    st = last_state(qa)
    check(st and st["choosing"] == [ann.id], "the browsers are told who everyone waits for")
    room.handle(ann, {"t": "commander", "k": ann.offers[1]})
    room.tick()
    check(room.phase == "fight" and ann.commander, "the fight starts as soon as Ann has chosen")
    # someone who leaves while choosing gets the first offer
    room = game.Room("WAIT2")
    room.rng.seed(6)
    room.clock = Clock()
    ann, qa = browser(room, "Ann", "tok-a")
    bo, qb = browser(room, "Bo", "tok-b")
    room.handle(ann, {"t": "start"})
    room.handle(ann, {"t": "commander", "k": ann.offers[0]})
    first = bo.offers[0]
    room.clock.t = room.ends + 5
    room.tick()
    check(room.phase == "plan", "the first fight waits for Bo")
    room.leave(bo, qb)
    room.tick()
    check(room.phase == "fight" and bo.commander == first, "Bo left: he gets the first offer and the fight starts")
    # Exit: Bo forfeits; Ann is the only person standing with two bots
    full = copies(room)
    bo.connected, bo.queue = True, qb  # back, and presses Exit
    room.handle(bo, {"t": "forfeit"})
    check(not bo.alive and bo.place == 4 and not bo.units(), "Exit knocks Bo out in last place")
    check(copies(room) == full, "his units go back to the pool")
    check(room.phase == "fight", "the match goes on while a person is standing")
    room.handle(ann, {"t": "forfeit"})
    check(room.phase == "over" and ann.place == 3, "when only bots are left, the match ends")
    check(sorted(p.place for p in room.seated()) == [1, 2, 3, 4], "everyone has a place")


def armory_and_last_person():
    """Items are bought in the armory; monsters only give gold. When the last person is knocked out and
    only bots stand, the match ends at once."""
    room = game.Room("ARMS")
    room.rng.seed(8)
    room.clock = Clock()
    ann, q = browser(room, "Ann", "tok-a")
    room.handle(ann, {"t": "start"})
    room.handle(ann, {"t": "commander", "k": next(k for k in ann.offers if k not in ("forgemaster", "alchemist"))})
    check(len(ann.armory) == D.ARMORY_SIZE and all(D.ITEMS[k]["rarity"] <= 2 for k in ann.armory),
          "the armory offers Common and Rare items in round 1")
    st = last_state(q)
    check(st and st["me"]["armory"] == ann.armory, "the browser sees the armory")
    key = ann.armory[0]
    ann.gold = room.item_price(key) + 1
    room.handle(ann, {"t": "buy_item", "i": 0})
    check(ann.items == [key] and ann.gold == 1 and ann.armory[0] is None, "buying an item")
    room.handle(ann, {"t": "buy_item", "i": 1})
    check(len(ann.items) == 1 and ann.armory[1], "not without the gold")
    room.handle(ann, {"t": "buy_item", "i": 0})
    check(len(ann.items) == 1, "nor twice")
    ann.locked = True
    kept = list(ann.armory)
    for p in room.seated():
        p.hp = 99
    room.clock.t = room.ends + 0.01
    room.tick()
    room.clock.t = room.ends + 0.01
    room.tick()
    check(room.round == 2 and ann.armory == kept, "a locked shop keeps the armory")
    check(len(ann.items) == 1, "monsters drop no items")
    seen = {r: 0 for r in D.RARITIES}
    for rnd in (2, 20):  # the armory's rarities follow the round
        room.round = rnd
        for _ in range(200):
            room.stock_armory(ann)
            for k in ann.armory:
                seen[D.ITEMS[k]["rarity"]] += rnd == 20
        check(rnd == 20 or all(D.ITEMS[k]["rarity"] <= 2 for k in ann.armory), "early armories are Common and Rare")
    check(seen[1] == 0 and seen[4] > 0 and seen[3] > seen[2], "late armories run Epic and Legendary")
    check(room.item_price("hourglass") == D.ITEM_PRICE[4] and room.item_price("sword") == D.ITEM_PRICE[1], "prices by rarity")
    ann.commander = "forgemaster"
    check(room.item_price("sword", ann) == D.ITEM_PRICE[1] - 1, "the Forgemaster pays a gold less")
    ann.commander = None
    room.round = 2
    # Ann goes out: the bots' match ends there
    for _ in range(40):
        if room.phase == "over":
            break
        ann.hp = 1
        for p in room.seated():
            if p is not ann:
                p.hp = 99
        ann.board = {}
        room.clock.t = room.ends + 0.01
        room.tick()
    check(room.phase == "over" and ann.place == 4, "the last person out ends the match at once")
    check(sorted(p.place for p in room.seated()) == [1, 2, 3, 4], "everyone has a place")


def talents():
    """Extra abilities: three or four to pick from at 2 and 3 stars, picked once, kept through a merge,
    lost with a sale, and working in a fight."""
    for key, t in D.TALENTS.items():
        check(t["star"] in D.TALENT_STARS and t["text"] and (t["trait"] is None or t["trait"] in D.TRAITS), f"talent {key}")
        check(("{ability}" in t["name"]) == (t["trait"] is None), f"talent {key}: only the own-ability ones name it")
        for k in t["fx"]:
            check(k in D.PLAIN_STATS or k in D.SPECIAL, f"talent {key}: unknown effect {k}")
    for trait in D.TRAITS:
        for star in D.TALENT_STARS:
            check(sum(t["trait"] == trait and t["star"] == star for t in D.TALENTS.values()) == 1, f"{trait}: one at {star}")
    for key in D.shop_units():
        for star in D.TALENT_STARS:
            opts = D.talent_options(key, star)
            check(3 <= len(opts) <= 4 and len(set(opts)) == len(opts), f"{key}: options at {star} stars ({opts})")
    check(D.talent_options("ashling", 1) == [] and D.talent_options("treant", 2) == [], "none at 1 star or for summons")
    check(D.talent_name("empowered", "ashling") == "Empowered Flurry", "the own-ability one is named after it")

    room = game.Room("TLNT")
    room.clock = Clock()
    me, q = browser(room, "Ann", "t")
    room.handle(me, {"t": "start"})
    room.handle(me, {"t": "commander", "k": me.offers[0]})
    for u in me.units():
        room.sell_unit(me, u)
    me.gold, me.level = 200, 5
    me.shop = ["ashling"] * len(me.shop)
    for i in range(3):
        room.handle(me, {"t": "buy", "i": i})
    two = next(u for u in me.units() if u["unit"] == "ashling")
    check(two["star"] == 2 and room.talent_offer(two) == D.talent_options("ashling", 2), "a 2-star has picks waiting")
    st = last_state(q)
    offers = st["me"]["talent_offers"] if st else []
    check(offers and offers[0]["id"] == two["id"] and offers[0]["star"] == 2, "the browser is told what's waiting")
    check(not room.choose_talent(me, two["id"], "mastered"), "a 3-star pick is refused at 2 stars")
    check(not room.choose_talent(me, two["id"], "split_shot"), "another trait's pick is refused")
    check(not room.choose_talent(me, 9999, "kindling"), "an unknown unit is refused")
    room.handle(me, {"t": "talent", "id": two["id"], "k": "kindling"})
    check(two["talents"] == ["kindling"] and not room.talent_offer(two), "picked once")
    check(not room.choose_talent(me, two["id"], "momentum"), "no second pick at 2 stars")
    st = last_state(q)
    bench = [b for b in st["me"]["bench"] if b and b[0] == two["id"]] if st else []
    check(bench and bench[0][4] == ["kindling"] and not st["me"]["talent_offers"], "the bench shows it")
    # two more 2-stars (one with a pick, one without) merge into a 3-star that keeps the first's
    for _ in range(2):
        me.shop = ["ashling"] * len(me.shop)
        for i in range(3):
            room.handle(me, {"t": "buy", "i": i})
    later = [u for u in me.units() if u["unit"] == "ashling"]
    check(len(later) == 1 and later[0]["star"] == 3, f"three 2-stars make a 3-star ({[u['star'] for u in later]})")
    three = later[0]
    check(three["talents"] == ["kindling"], f"the 3-star keeps the first copy's pick ({three['talents']})")
    check(room.talent_offer(three) == D.talent_options("ashling", 3), "and has its 3-star pick waiting")
    check(room.choose_talent(me, three["id"], "executioner") and three["talents"] == ["kindling", "executioner"], "3-star pick")
    # a 3-star that skipped its 2-star pick picks that first
    skip = room.new_unit("thornling", 3)
    me.bench[me.bench.index(None)] = skip
    check(room.talent_offer(skip) == D.talent_options("thornling", 2), "a skipped 2-star pick comes first")
    gold = me.gold
    room.sell_unit(me, three)
    check(me.gold > gold and "kindling" not in str(me.units()), "selling loses its picks")
    # bots pick theirs
    bot = next(p for p in room.seated() if p.bot)
    bu = room.new_unit("iron_recruit", 2)
    bot.bench[0] = bu
    bots.pick_talents(room, bot, random.Random(1))
    check(len(bu["talents"]) == 1 and bu["talents"][0] in D.talent_options("iron_recruit", 2), "bots pick")

    # in a fight
    dummy = [{"unit": "iron_colossus", "col": 3, "row": 3}]
    plain = sim.Fight([B("iron_recruit", 3, 3, 2)], dummy)
    tough = sim.Fight([dict(B("iron_recruit", 3, 3, 2), talents=["stalwart"])], dummy)
    hp = lambda f: next(u.max for u in f.units if u.key == "iron_recruit")
    check(abs(hp(tough) / hp(plain) - (1 + D.TALENTS["stalwart"]["fx"]["hp_pct"])) < 0.01, "Stalwart adds HP")
    check(any(r[10] == ["stalwart"] for r in tough.start), "the browsers see picks")
    junk = sim.Fight([dict(B("iron_recruit", 3, 3, 2), talents=["nonsense", "stalwart"])], dummy)
    check(next(u for u in junk.units if u.key == "iron_recruit").talents == ["stalwart"], "unknown picks are dropped")
    dmg = {}
    for tal in ([], ["empowered"]):
        f = sim.Fight([dict(B("thornling", 3, 0, 2), talents=tal)], [{"unit": "stone_golem", "col": 3, "row": 0}], seed=4)
        r = f.run()
        me_id = next(row[0] for row in r["start"] if row[2] == "thornling")
        dmg[bool(tal)] = max((e[4] for e in r["events"] if e[0] == "d" and e[2] == me_id and e[5] == 0), default=0)
    check(dmg[True] > dmg[False] * 1.2, f"Empowered abilities hit harder ({dmg})")
    f = sim.Fight([dict(B("forge_hound", 3, 3, 2), talents=["sludge"])], [{"unit": "stone_golem", "col": 3, "row": 3}], seed=1)
    f.units.sort(key=lambda u: u.id)
    hound, golem = f.units
    f.attack(hound, golem)
    check(golem.slow[0] >= 0.3, "Sludge slows")
    f = sim.Fight([dict(B("toad_brawler", 3, 3, 3), talents=["sludge", "bog_grip"])], [{"unit": "stone_golem", "col": 3, "row": 3}])
    f.units.sort(key=lambda u: u.id)
    toad, golem = f.units
    f.attack(toad, golem)
    check(golem.amp[0] == 0.25 and golem.amp[1] > f.t, "Bog Grip marks")
    f = sim.Fight([dict(B("ashling", 3, 3, 2), talents=["kindling"])], [{"unit": "stone_golem", "col": 3, "row": 3}])
    f.units.sort(key=lambda u: u.id)
    ash, golem = f.units
    ash.target = golem
    f.step_hit(ash, {"do": "hit", "to": "target", "dmg": 10})
    check(golem.burn[0] > 0 and golem.burn[2] is ash, "Kindling's ability burns")


def card_numbers():
    """The unit cards' numbers: a board unit's count its traits, items, picks and augments; a bench unit's
    only its items and picks; both reach the browser, and fights' start rows carry them too."""
    room = game.Room("CARD")
    room.clock = Clock()
    me, q = browser(room, "Ann", "c")
    room.handle(me, {"t": "start"})
    room.handle(me, {"t": "commander", "k": me.offers[0]})
    for u in me.units():
        room.sell_unit(me, u)
    me.commander, me.level = "sage", 5  # a commander that adds nothing to a fight
    me.team_fx = {"ad": 8}
    mage = room.new_unit("ember_mage", 2, ["rod", "emblem_ironhold"])
    me.board = {(3, 0): mage, (2, 3): room.new_unit("iron_recruit"), (4, 3): room.new_unit("iron_sentinel")}
    bench = room.new_unit("ember_mage", 2, ["rod"])
    bench["talents"] = ["empowered"]
    me.bench[0] = bench
    room.send_state()
    st = last_state(q)
    row = next(r for r in st["players"] if r["id"] == me.id)["board"]
    card = next(r[7] for r in row if r[0] == mage["id"])
    d = D.UNITS["ember_mage"]
    check(card["hp"] == round(d["hp"] * 1.8) + 150 and card["ap"] == 125 and card["ad"] == round(d["ad"] * 1.8) + 8,
          f"a board unit's card counts its items and augments ({card})")
    check(card["armor"] == d["armor"] + 30, f"and the Ironhold its emblem joins ({card['armor']})")
    b = st["me"]["bench"][0][5]
    check(b["armor"] == d["armor"] and b["ap"] == 125 and b["power"] == 0.3, f"a bench unit's: items and picks only ({b})")
    f = sim.Fight(me.fight_board(), [])
    check(all(len(r) == 12 and r[11]["hp"] == r[6] for r in f.start), "fights' start rows carry the numbers")
    lone = game.Room("CRD2")
    lone.clock = Clock()
    lone.bots = True
    lone.start()
    bot = lone.seated()[0]
    lone.send_state()
    check(bot.cards == {}, "nobody to see them: no numbers worked out")


def records():
    """A finished match with a person in it is saved; their record and the Hall of Overlords show it."""
    room = game.Room("RECS")
    room.rng.seed(3)
    room.clock = Clock()
    me, q = browser(room, "Ann", "tok-ann")
    room.handle(me, {"t": "start"})
    while room.phase != "over" and room.round < 40:
        room.clock.t = room.ends + 0.01
        room.tick()
        if me.offers and not me.commander:
            room.handle(me, {"t": "commander", "k": me.offers[0]})
        if room.phase == "plan" and me.alive:  # Ann plays like a normal bot
            me.bot = "normal"
            game.B.play(room, me, room.rng)
            me.bot = None
    check(room.phase == "over", "the recorded match ended")
    st = last_state(q)
    rec = st.get("record") if st else None
    check(rec and rec["games"] == 1 and rec["recent"][0]["place"] == me.place, "Ann's record shows the match")
    check(st and all(p.get("final") is not None for p in st["players"] if p["seated"]), "everyone's final board is shown")
    check(SAVE.stats("someone-else") is None, "a stranger has no record")
    lead = SAVE.leaders()
    check(not lead or lead[0]["wins"] == 1, "the Hall of Overlords counts wins")
    check(me.place != 1 or (lead and lead[0]["name"] == "Ann"), "a win puts Ann in the Hall")


data()
art()
records()
commander_wait_and_exit()
armory_and_last_person()
items_in_fights()
room_items_and_powers()
talents()
card_numbers()
draft()
room_rules()
pairing()
auction()
build_arounds()
matches()
every_ability_fires()
mechanics()
determinism_and_geometry()
random_fights()
if failures:
    print("\n".join(failures[:40]))
    sys.exit(1)
print(f"ok: {len(D.shop_units())} units, {len(D.TRAITS)} traits, every ability fires, fights finish")
