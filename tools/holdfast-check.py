"""Checks Holdfast's room headlessly: the rules around the fight rather than its balance.

    python3 tools/holdfast-check.py

Pretend browsers join a room and play: building is refused on the road, on rocks, on another tower,
off the board and without the gold; anyone may upgrade but only the builder may sell; gold can be
given; Ready sends the wave early; kills pay everyone equally and the snapshots carry the enemies;
a fifth player watches; a lost keep ends the game and the host reopens the room. Every wave of
every map is also checked to be made of known enemies. Heroes, forks and gates have their own checks. (`tools/holdfast-sim.py` covers balance.)
"""

import asyncio
import json
import math
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["HOLDFAST_DB"] = os.path.join(tempfile.mkdtemp(prefix="holdfast-check-"), "holdfast.db")

from app.holdfast import data as D  # noqa: E402
from app.holdfast import game  # noqa: E402


class Browser:
    def __init__(self, room, name):
        self.queue = asyncio.Queue(maxsize=5000)
        self.room = room
        self.p = room.join(self.queue, name, f"token-{name}", "tab")
        self.last = {}

    def read(self):
        while not self.queue.empty():
            text = self.queue.get_nowait()
            if text is not None:
                m = json.loads(text)
                self.last[m["t"]] = m
        return self.last

    def do(self, **msg):
        self.room.handle(self.p, msg)


def run(room, secs):
    for _ in range(round(secs / game.STEP)):
        room.tick()


async def main():
    # The data hangs together.
    for w in range(1, D.WAVES + 1):
        assert D.wave(w) and all(k in D.ENEMIES and n > 0 and gap > 0 for k, n, gap, _ in D.wave(w)), w
        assert D.health(w) >= D.health(max(1, w - 1))
    for kind, t in D.TOWERS.items():
        assert len(t["paths"]) == 2 and all(len(p["tiers"]) == D.EVOLUTION for p in t["paths"]), kind
        for p in t["paths"]:
            assert [x["cost"] for x in p["tiers"]] == sorted(x["cost"] for x in p["tiers"]), f"{kind}: tiers get cheaper"
            pi = t["paths"].index(p)
            for n in range(D.EVOLUTION + 1):
                for side in range(D.CROSS_MAX + 1):
                    tiers = [n, side] if pi == 0 else [side, n]
                    st = D.stats(kind, tiers, pi)
                    assert st["mode"] in ("shoot", "splash", "radial", "aura", "chain", "trap", "sentry", "support",
                                          "income") and st["range"] > 0, (kind, tiers)
                    assert st["mode"] in ("support", "income", "sentry") or (st["dmg"] > 0 and st["rate"] > 0), (kind, tiers)
                    assert st["mode"] != "sentry" or (st["sentry"]["dmg"] > 0 and st["max"] > 0), (kind, tiers)
                    assert st.get("dtype", "normal") in D.DTYPES, (kind, tiers)
            for x in p["tiers"][:D.CROSS_MAX]:
                assert x["cross"], f"{kind}: {x['name']} gives nothing on the side"
    for kind, e in D.ENEMIES.items():
        assert all(k in D.ENEMIES for k, _ in e.get("children", [])) and set(e.get("immune", ())) <= set(D.DTYPES), kind
    for name, m in D.MAPS.items():
        road = D.path_tiles(m)
        assert not road & set(map(tuple, m["rocks"])), f"{name}: a rock on the road"
        for path in m["paths"]:
            assert all(x0 == x1 or y0 == y1 for (x0, y0), (x1, y1) in zip(path, path[1:])), f"{name}: a diagonal road"
            assert path[-1] == m["paths"][0][-1], f"{name}: roads that end in different places"

    room = game.Room("TEST")
    a, b = Browser(room, "A"), Browser(room, "B")
    room.task.cancel()  # the test turns the clock by hand
    b.do(t="start")
    assert room.phase == "lobby"
    b.do(t="set", map="coil")
    a.do(t="set", map="meadow", diff="hard")
    a.do(t="set", map="nowhere", diff="silly")
    assert (room.map, room.diff) == ("meadow", "hard")
    a.do(t="start")
    assert room.phase == "play" and a.p.gold == b.p.gold == 125
    assert a.read()["map"]["paths"] == [[list(pt) for pt in path] for path in D.MAPS["meadow"]["paths"]]

    # Building.
    for bad in [dict(k="archer", x=2, y=2), dict(k="archer", x=1, y=6), dict(k="archer", x=-1, y=0),
                dict(k="archer", x=20, y=0), dict(k="archer", x=1.5, y=3), dict(k="archer", x="1", y=3),
                dict(k="dragon", x=2, y=3), dict(k="tesla", x=2, y=3)]:
        a.do(t="build", **bad)
    assert not room.towers and a.p.gold == 125
    a.do(t="build", k="archer", x=2, y=3)
    a.do(t="build", k="archer", x=2, y=3)
    assert len(room.towers) == 1 and a.p.gold == 75
    t = next(iter(room.towers.values()))
    view = a.read()["state"]["towers"][0]
    assert {k: v for k, v in view.items() if k != "un"} == {
        "id": t.id, "k": "archer", "p": None, "n": 0, "c": [0, 0], "f": None, "x": 2, "y": 3, "o": a.p.id, "s": 50,
        "kills": 0, "dmg": 0, "tg": "first", "cs": False, "ul": False, "bo": 0.0, "pw": 0.0, "rc": 0.0}, view
    assert view["un"][0] == a.p.id and 0 < view["un"][1] <= game.UNDO
    # Anyone may upgrade; only the builder may sell.
    b.do(t="up", id=t.id)
    b.do(t="up", id=t.id, path=2)
    assert t.tier == 0
    b.do(t="up", id=t.id, path=0)
    assert (t.path, t.tier) == (0, 1) and b.p.gold == 65 and t.spent == 110 and t.stats["dmg"] == D.stats("archer", (1, 0))["dmg"]
    b.do(t="sell", id=t.id)
    assert t.id in room.towers
    b.do(t="up", id=t.id, path=0)  # can't afford the next tier
    b.do(t="up", id=999, path=0)
    assert t.tier == 1
    # Giving.
    a.do(t="give", to=b.p.id)
    a.do(t="give", to=a.p.id)
    a.do(t="give", to=999)
    assert (a.p.gold, b.p.gold) == (50, 90)
    # A beacon speeds up the tower beside it, and stops when it's sold.
    b.p.gold = 110
    b.do(t="build", k="beacon", x=3, y=3)
    assert t.boost == 0.2
    b.do(t="sell", id=room.at[(3, 3)].id)
    assert t.boost == 0 and b.p.gold == 77 and (3, 3) not in room.at

    # The first wave comes after the build time, or at once when everyone's ready.
    run(room, 3)
    assert not room.fighting and a.read()["s"]["n"] > 20 and a.last["state"]["coming"] == [["grunt", 11]]
    a.do(t="ready")
    run(room, 1)
    assert not room.fighting
    b.do(t="ready")
    run(room, 1)
    assert room.fighting and room.wave == 1 and not a.p.ready
    gold = a.p.gold
    run(room, 6)
    snap = a.read()["s"]
    assert snap["e"] and all(len(e) == 7 and D.KINDS[e[1]] == "grunt" for e in snap["e"])
    assert t.kills and "k" in snap, "a tower's kills weren't counted"
    assert a.p.kills and a.p.gold > gold and abs((a.p.gold - gold) - (b.p.gold - 77)) < 1e-6, "kills should pay both"
    assert set(snap["g"]) == {str(a.p.id), str(b.p.id)}

    # More players than seats: the fifth watches, and can't build.
    others = [Browser(room, n) for n in "CDE"]
    assert [o.p.seated for o in others] == [True, True, False]
    others[2].p.gold = 500
    others[2].do(t="build", k="archer", x=10, y=10)
    assert (10, 10) not in room.at
    # Someone seated who drops keeps their seat and their towers; kills now pay the rest.
    room.leave(b.p, b.queue)
    assert b.p.id in room.players and b.p not in room.crew()
    # Speed is the host's.
    others[0].do(t="speed", v=3)
    assert room.speed == 1
    a.do(t="speed", v=3)
    assert room.speed == 3

    # One archer can't hold the road on hard: the keep falls, and the host reopens the room.
    for _ in range(4000):
        if room.phase != "play":
            break
        run(room, 1)
    assert room.phase == "lost" and room.lives == 0 and a.read()["state"]["phase"] == "lost"
    others[0].do(t="again")
    assert room.phase == "lost"
    a.do(t="again")
    assert room.phase == "lobby" and b.p.id not in room.players and sum(p.seated for p in room.players.values()) == 4
    a.do(t="start")
    assert room.phase == "play" and not room.towers and room.lives == D.LIVES and room.wave == 0
    lab()
    newer()
    crosspaths()
    projectiles()
    immunities()
    layers()
    board_things()
    bosses()
    items()
    new_abilities()
    endless_and_stuns()
    heroes()
    gates()
    saves()
    print("Holdfast: building, upgrading, crosspathing, evolving, selling, giving, readying, watching, every "
          "tower's effects, projectiles and pierce, immunities, layers, traps, sentries, bosses, items, targeting, "
          "Ghosts, undo, abilities, Menders, Splitters, summons, endless, heroes, forks, gates, records, saving and resuming hold up")


def lab():
    """Each tower's effects, on enemies placed by hand."""
    room = game.Room("LAB")
    room.send = lambda p, data: None
    p = game.Player(1, "P", "#fff", None, None, None)
    room.players[1] = p
    room.start()
    room.fighting = True  # so advance() fights rather than counting down
    room.spawns = [(999, "grunt", 0)]  # the wave isn't over while this is waiting
    route, length = room.routes[0]

    def enemy(kind, d, hp=None):
        room.spawn(kind, 0)
        e = room.enemies[-1]
        e.d = d
        (x0, y0), _ = route[0]
        room.advance(0)  # put it on the road
        e.speed = 0 if hp is None else e.speed
        if hp:
            e.max = e.hp = hp
        return e

    def tower(kind, x, y, path=None, tiers=0):
        p.gold = 99999
        t = room.build(p, kind, x, y)
        assert t, (kind, x, y)
        for _ in range(tiers):
            assert room.upgrade(p, t, path), (kind, path)
        return t

    def clear():
        for t in list(room.towers.values()):
            room.sell(p, t)
        room.enemies = []

    def fight(secs):
        for _ in range(round(secs / game.STEP)):
            room.advance(game.STEP)

    # Meadow's road: (-1,2) to (4,2), then down column 4 to row 8. d = 5 is the corner at (4, 2).
    # Evolutions: one of each at a time; the other path's evolution is a different one.
    a1, a2 = tower("archer", 3, 3, 0, 3), tower("archer", 5, 3, 0, 3)
    assert room.upgrade(p, a1, 0) and a1.tier == D.EVOLUTION and a1.stats["range"] == 9
    assert not room.upgrade(p, a2, 0), "two Eagle Eyes at once"
    a3 = tower("archer", 5, 4, 1, 3)
    assert room.upgrade(p, a3, 1), "a Storm of Arrows was refused for an Eagle Eye"
    assert not room.upgrade(p, a1, 0), "evolved past the last tier"
    room.sell(p, a1)
    assert room.upgrade(p, a2, 0), "selling the Eagle Eye should free its place"
    clear()

    # Kill counts: the tower that kills gets the credit.
    t = tower("archer", 3, 3)
    e = enemy("grunt", 5, hp=5)
    fight(1)
    assert e.hp <= 0 and t.kills == 1 and t.dmg >= 5
    clear()
    # Volley: several targets a shot.
    t = tower("archer", 3, 3, 1, 2)
    es = [enemy("grunt", 5 + i, hp=1000) for i in range(3)]
    for e in es:
        e.speed = 0
    fight(0.45)  # one volley (a new tower waits 0.3 s), and the arrows' flight
    assert sum(e.hp < 1000 for e in es) == 2, "a Twin Shot should hit two"
    clear()
    # Burning: keeps hurting after the brazier, and ignores armour.
    t = tower("brazier", 3, 3)
    e = enemy("shield", 5, hp=1000)
    e.armor = 100
    fight(0.4)
    room.sell(p, t)
    hp = e.hp
    fight(1)
    assert e.burn_for > 0 or hp > e.hp
    assert e.hp < hp, "burning stopped when the brazier went"
    clear()
    # Stun: a jolted enemy stops.
    t = tower("tesla", 3, 3, 1, 1)
    e = enemy("grunt", 5, hp=10000)
    e.speed = 1.0
    fight(0.4)
    assert e.stun > 0
    d = e.d
    room.advance(game.STEP)
    assert e.d == d, "a stunned enemy moved"
    clear()
    # Shred: Shatter Shells strip armour for good.
    t = tower("cannon", 3, 3, 0, 3)
    e = enemy("shield", 5, hp=100000)
    armour = e.armor
    fight(0.5)
    assert e.armor < armour
    clear()
    # Frost's Brittle Ice: slowed enemies take more from everything.
    f = tower("frost", 3, 3, 0, 3)
    e = enemy("grunt", 5, hp=100000)
    fight(0.4)
    assert e.slow > 0 and e.brittle == 0.25
    clear()
    # Mortar reaches across the board; a cannon can't hit flyers.
    t = tower("mortar", 18, 0)
    e = enemy("grunt", 5, hp=100000)
    e.speed = 0
    fight(1.4)  # a lobbed shell is in the air for a while
    assert e.hp < 100000, "the mortar couldn't reach"
    clear()
    c = tower("cannon", 3, 3)
    room.spawn("flyer", 0)
    fly = room.enemies[-1]
    fly.speed, fly.x, fly.y = 0, 3, 2
    fight(1)
    assert fly.hp == fly.max and c.kills == 0
    clear()
    # Beacons: reach and power for their neighbours.
    t = tower("archer", 3, 3)
    b = tower("beacon", 3, 4, 1, 3)
    assert t.reach == 0.25 and t.power == 0.25 and t.range == 3.2 * 1.25
    clear()
    # Mints: income to their builder after each wave, and a bounty bonus on kills near them.
    m = tower("mint", 3, 4, 1, 1)
    t = tower("archer", 3, 3, 0, 2)
    e = enemy("grunt", 5, hp=1)
    gold = p.gold
    fight(1)
    assert e.hp <= 0 and abs((p.gold - gold) - e.bounty * 1.15) < 1e-6, "the mint's bounty bonus was missed"
    room.spawns = []
    room.enemies = []
    gold = p.gold
    room.advance(game.STEP)  # the wave ends
    assert not room.fighting and p.gold - gold == 20 + 4 * room.wave + D.stats("mint", (0, 1))["income"]
    clear()




def fresh(map_id="meadow", players=1):
    room = game.Room("NEW")
    room.send = lambda p, data: None
    room.saving = False
    room.map = map_id
    for i in range(players):
        room.players[i + 1] = game.Player(i + 1, f"P{i + 1}", "#fff", None, f"tok{i + 1}", None)
    room.start()
    room.fighting = True
    room.spawns = [(999, "grunt", 0)]
    return room


def put(room, kind, d, hp=1000, speed=0):
    room.spawn(kind, 0)
    e = room.enemies[-1]
    e.d, e.speed = d, speed
    e.max = e.hp = hp
    room.advance(0)
    return e


def tower_at(room, p, kind, x, y, path=None, tiers=0):
    p.gold = 99999
    t = room.build(p, kind, x, y)
    for _ in range(tiers):
        assert room.upgrade(p, t, path)
    return t


def steps(room, secs):
    for _ in range(round(secs / game.STEP)):
        room.advance(game.STEP)


def newer():
    """Targeting, Ghosts, undo, abilities and the newer enemies."""
    import time as clock
    room = fresh()
    p = room.players[1]
    # Targeting: "strong" picks the toughest in reach, "first" the one nearest the keep.
    t = tower_at(room, p, "archer", 3, 3)
    weak, tough = put(room, "grunt", 5.5, hp=1000), put(room, "grunt", 4.5, hp=5000)
    steps(room, 0.4)
    assert weak.hp < 1000 and tough.hp == 5000, "first should aim at the one nearest the keep"
    t.target = "strong"
    steps(room, 0.7)
    assert tough.hp < 5000, "strong should aim at the toughest"
    room.enemies = []
    # Ghosts: unseen by a plain archer, seen by a Longbow, an aura, or next to a Spyglass.
    ghost = put(room, "ghost", 5)
    steps(room, 1)
    assert ghost.hp == 1000 and not t.sees
    room.upgrade(p, t, 0)
    room.upgrade(p, t, 0)
    assert t.sees
    steps(room, 1)
    assert ghost.hp < 1000, "a Longbow should see Ghosts"
    room.enemies = []
    other = tower_at(room, p, "archer", 5, 3)
    assert not other.sees
    tower_at(room, p, "beacon", 6, 3, 1, 1)
    assert other.sees, "a Spyglass should reveal Ghosts to its neighbours"
    assert other.view()["cs"], "the browser's wave preview needs to know what sees Ghosts"
    for x in list(room.towers.values()):
        room.sell(p, x)
    # Undo: a build or upgrade comes back in full for a few seconds, only to whoever paid.
    p.gold = 1000
    t = room.build(p, "cannon", 3, 3)
    room.undo(p, t)
    assert p.gold == 1000 and t.id not in room.towers and (3, 3) not in room.at
    t = room.build(p, "cannon", 3, 3)
    room.upgrade(p, t, 1)
    gold = p.gold
    room.undo(p, t)
    assert p.gold == gold + D.TOWERS["cannon"]["paths"][1]["tiers"][0]["cost"] and t.tier == 0 and t.path is None
    room.undo(p, t)
    assert t.id in room.towers, "a second undo took back the build too"
    room.upgrade(p, t, 0)
    t.undo = (clock.monotonic() - 1, p.id, "up", 100, 0)
    gold = p.gold
    room.undo(p, t)
    assert p.gold == gold and t.tier == 1, "an undo after the window"
    room.sell(p, t)
    # Abilities: only when evolved, ready and fighting; then on cooldown.
    a = tower_at(room, p, "archer", 3, 3, 0, 4)
    assert a.ability["name"] == "Headshot"
    boss = put(room, "boss", 5, hp=10000)
    grunt = put(room, "grunt", 3, hp=2000)
    assert room.use_ability(a) and boss.hp == 10000 * 0.75 and grunt.hp == 2000
    assert not room.use_ability(a), "an ability fired again during its cooldown"
    steps(room, a.ability["cd"] + 0.1)
    room.fighting = False
    a.cd = 0
    assert not room.use_ability(a), "an ability fired between waves"
    room.fighting = True
    room.enemies = []
    room.sell(p, a)
    # every other kind of ability does what it says
    checks = {
        ("frost", 0): lambda e: e.stun > 0,
        ("brazier", 0): lambda e: e.burn_for > 0,
        ("brazier", 1): lambda e: e.slow > 0,
        ("tesla", 0): lambda e: e.hp < 1000,
    }
    for (kind, path), ok in checks.items():
        e = put(room, "grunt", 4)
        t = tower_at(room, p, kind, 3, 3, path, 4)
        assert room.use_ability(t) and ok(e), (kind, path)
        room.sell(p, t)
        room.enemies = []
    put(room, "grunt", 4)
    t = tower_at(room, p, "beacon", 3, 3, 0, 4)
    room.use_ability(t)
    assert room.rally[0] > room.fight_t and room.rally[1] == 2
    room.sell(p, t)
    t = tower_at(room, p, "mint", 3, 3, 0, 4)
    p.gold = 0
    room.use_ability(t)
    assert p.gold == 400
    room.sell(p, t)
    t = tower_at(room, p, "ballista", 3, 3, 1, 4)
    room.use_ability(t)
    assert t.overdrive[1] == 4
    room.sell(p, t)
    room.enemies = []
    assert room.effects, "abilities used should be in the next snapshot"
    # Menders heal; one Mender's worth, however many are near.
    e = put(room, "grunt", 4, hp=1000)
    e.hp = 500
    put(room, "healer", 4.2)
    put(room, "healer", 4.4)
    steps(room, 1)
    assert 515 < e.hp < 525, e.hp
    room.enemies = []
    # Splitters burst into Swarmlings; Warlords call up Grunts.
    s_ = put(room, "splitter", 4, hp=1)
    t = tower_at(room, p, "archer", 3, 3)
    room.damage(s_, 5, t)
    room.advance(0)
    swarm = [e for e in room.enemies if e.kind == "swarm"]
    assert s_.hp <= 0 and len(swarm) == D.ENEMIES["splitter"]["children"][0][1] and all(e.d <= 4 for e in swarm)
    room.sell(p, t)
    room.enemies = []
    w = put(room, "boss", 6, hp=10 ** 7)
    steps(room, D.ENEMIES["boss"]["every"] + 0.1)
    grunts = [e for e in room.enemies if e.kind == "grunt"]
    assert len(grunts) == D.ENEMIES["boss"]["summon"] and all(g.d < w.d for g in grunts)
    room.enemies = []
    # Quarry: only its cleared ground can be built on.
    q = fresh("quarry")
    qp = q.players[1]
    qp.gold = 9999
    assert not q.build(qp, "archer", 0, 0) and q.build(qp, "archer", 3, 4)
    # Every map's roads are straight runs and end at one keep; Knot crosses itself.
    knot = D.MAPS["knot"]["paths"][0]
    tiles = []
    for (x0, y0), (x1, y1) in zip(knot, knot[1:]):
        n = abs(x1 - x0) + abs(y1 - y0)
        tiles += [(x0 + (x1 > x0) * i - (x1 < x0) * i, y0 + (y1 > y0) * i - (y1 < y0) * i) for i in range(n)]
    assert len(tiles) != len(set(tiles)), "Knot's road should cross itself"
    # Endless: after wave 30 the host can carry on; the waves keep coming.
    assert D.wave(31) and D.wave(45) and all(k in D.ENEMIES for k, *_ in D.wave(45))


def crosspaths():
    """Both paths can be bought, but only one past tier 2; the side path gives its `cross` bonus."""
    room = fresh()
    p = room.players[1]
    p.gold = 99999
    t = room.build(p, "archer", 3, 3)
    assert room.upgrade(p, t, 0) and room.upgrade(p, t, 1), "a tier on each path should be allowed"
    assert t.path == 0 and t.tiers == [1, 1], "the path bought first is the main one on a tie"
    assert t.stats == D.stats("archer", (1, 1), 0) and t.stats["dmg"] == 22 and abs(t.stats["rate"] - 0.6 * 0.85) < 1e-9
    assert room.upgrade(p, t, 1) and room.upgrade(p, t, 1), "the second path to tier 3 while the first is at 1"
    assert t.path == 1 and t.tiers == [1, 3], "the path with more tiers is the main one"
    assert room.upgrade(p, t, 0) and not room.upgrade(p, t, 0), "the side path past tier 2"
    assert t.tiers == [2, 3] and t.stats["detect"] and t.stats["shots"] == 3, t.stats
    assert room.upgrade(p, t, 1) and t.tier == D.EVOLUTION and room.tower_name(t) == "Storm of Arrows"
    assert t.ability["name"] == "Arrow Rain"
    # undoing the side path's tier takes its bonus away; undoing the last tier of the first path hands
    # "first" over to the other
    u = room.build(p, "cannon", 5, 5)
    room.upgrade(p, u, 1)
    room.upgrade(p, u, 0)
    assert u.first == 1 and u.path == 1
    room.undo(p, u)
    assert u.tiers == [0, 1] and u.stats == D.stats("cannon", (0, 1), 1)
    u.undo = None
    v = room.build(p, "frost", 6, 6)
    room.upgrade(p, v, 0)
    room.upgrade(p, v, 1)
    v.undo = (v.undo[0], p.id, "up", D.TOWERS["frost"]["paths"][0]["tiers"][0]["cost"], 0)
    room.undo(p, v)
    assert v.tiers == [0, 1] and v.first == 1 and v.path == 1


def projectiles():
    """Arrows fly, aim ahead, can miss, and go through `pierce` enemies."""
    room = fresh()
    p = room.players[1]
    # A ballista's bolt goes through three in a line; an archer's arrow stops at the first.
    b = tower_at(room, p, "ballista", 4, 9)  # below Meadow's road down column 4
    line = [put(room, "grunt", 5 + i * 0.6, hp=10000) for i in range(4)]
    b.target = "last"
    steps(room, 0.9)
    assert sum(e.hp < 10000 for e in line) == 3, [e.hp for e in line]
    room.sell(p, b)
    room.enemies = []
    room.flying = []
    a = tower_at(room, p, "archer", 5, 6)
    pair = [put(room, "grunt", 9, hp=1000), put(room, "grunt", 9.4, hp=1000)]  # (4, 6) and (4, 6.4)
    steps(room, 0.4)
    assert sum(e.hp < 1000 for e in pair) == 1, "an arrow with pierce 1 hit two"
    room.sell(p, a)
    room.enemies = []
    room.flying = []
    # Arrows lead a moving target; one that stops dead after the arrow is loosed is missed.
    a = tower_at(room, p, "archer", 6, 6)
    e = put(room, "grunt", 7, hp=1000, speed=4.0)  # running down column 4
    assert room.lead(a.x, a.y, e, 14)[1] > e.y + 0.05, "the arrow wasn't aimed ahead of a walking enemy"
    a.cool = 0
    room.fire(a)
    assert room.flying and e.hp == 1000
    e.stun = 5
    for _ in range(20):
        room.fly(game.STEP)
    assert e.hp == 1000 and not room.flying, "a stopped enemy was still hit, or the arrow never landed"
    room.sell(p, a)
    room.enemies = []
    # Bladewheels throw blades all round; their Ring of Fire turns them into an aura.
    w = tower_at(room, p, "bladewheel", 5, 4)
    es = [put(room, "grunt", d, hp=1000) for d in (7, 7.5)]  # (4, 4) and (4, 4.5), beside it
    steps(room, 1.6)
    assert any(e.hp < 1000 for e in es)
    room.upgrade(p, w, 1)
    room.upgrade(p, w, 1)
    assert w.stats["mode"] == "aura" and w.sees
    room.sell(p, w)


def immunities():
    """Immune enemies take nothing from that damage type, unless the tower hurts anything."""
    room = fresh()
    p = room.players[1]
    a = tower_at(room, p, "archer", 3, 3)
    iron = put(room, "ironclad", 5, hp=1000)
    iron.armor = 0
    steps(room, 1)
    assert iron.hp == 1000, "an arrow hurt an Ironclad"
    room.upgrade(p, a, 0)
    room.upgrade(p, a, 0)
    room.upgrade(p, a, 0)  # Bodkin Points: normal damage
    steps(room, 1)
    assert iron.hp < 1000, "Bodkin Points should hurt anything"
    room.sell(p, a)
    # A Solvent Draught beside a plain archer lets it hurt Ironclads.
    a = tower_at(room, p, "archer", 3, 3)
    al = tower_at(room, p, "alchemist", 2, 3, 1, 2)
    assert a.unlock and a.view()["ul"]
    iron.hp = 1000
    steps(room, 1)
    assert iron.hp < 1000, "a Solvent Draught should unlock its neighbours"
    room.sell(p, al)
    assert not a.unlock
    room.sell(p, a)
    # Frost can't slow Frostborn; Unmake strips immunities for a while.
    room.enemies, room.flying = [], []  # (arrows already loosed would still land)
    f = tower_at(room, p, "frost", 3, 4)
    fb = put(room, "frostborn", 5)
    steps(room, 1.2)
    assert fb.slow == 0 and fb.hp == 1000, "frost touched a Frostborn"
    room.unmake = room.fight_t + 5
    steps(room, 1.2)
    assert fb.slow > 0, "Unmake should strip immunities"
    room.unmake = 0
    room.sell(p, f)
    room.enemies = []


def layers():
    """Enemies burst into their children, who keep their camouflage."""
    room = fresh()
    p = room.players[1]
    t = tower_at(room, p, "archer", 3, 3)
    brute = put(room, "brute", 6, hp=5)
    brute.camo = True
    room.damage(brute, 10, t)
    room.advance(0)
    kids = [e for e in room.enemies if e.kind == "grunt"]
    assert len(kids) == 2 and all(k.camo and k.d <= 6 for k in kids)
    room.enemies = []
    j = put(room, "juggernaut", 8, hp=5)
    room.damage(j, 10, t)
    room.advance(0)
    assert sorted(e.kind for e in room.enemies) == ["brute"] * 4
    assert j.big and not j.boss and D.ENEMIES["colossus"]["children"] == [["juggernaut", 2]]
    room.enemies = []


def board_things():
    """Trappers lay piles on the road that hurt what walks over them; Workshops build sentries."""
    room = fresh()
    p = room.players[1]
    tr = tower_at(room, p, "trapper", 3, 3)
    steps(room, 0.5)
    assert len(room.traps) == 1 and all(room.road_pts and math.hypot(x.x - 3, x.y - 3) <= tr.range for x in room.traps)
    pile = room.traps[0]
    assert (round(pile.x), round(pile.y)) in room.road_tiles
    e = put(room, "grunt", 0, hp=1000)
    e.d = 0
    e.x, e.y = pile.x, pile.y
    room.spring()
    assert e.hp < 1000 and pile.hits == D.TOWERS["trapper"]["base"]["hits"] - 1 and tr.dmg > 0
    hits = pile.hits
    room.spring()
    assert pile.hits == hits, "one enemy set off the same pile twice"
    steps(room, 30)
    assert len(room.traps) <= tr.stats["max"]
    room.sell(p, tr)
    room.traps, room.enemies = [], []
    # Mines burst on the first enemy, hurting everything near.
    m = tower_at(room, p, "trapper", 3, 3, 1, 1)
    es = [put(room, "grunt", 5, hp=1000), put(room, "grunt", 5.3, hp=1000)]
    room.put_trap("mine", 4.0, 2.0, m.stats, m, 30)
    room.spring()
    assert all(e.hp < 1000 for e in es) and not room.traps
    room.sell(p, m)
    room.enemies = []
    # A workshop builds sentries beside the road while there's a fight; they shoot and credit it.
    w = tower_at(room, p, "workshop", 3, 3)
    target = put(room, "grunt", 5, hp=100000)
    steps(room, 0.5)
    assert len(room.sentries) == 1
    sn = room.sentries[0]
    assert (round(sn.x), round(sn.y)) not in room.road_tiles
    steps(room, 3)
    assert target.hp < 100000 and w.dmg > 0, "the sentry didn't fight for its workshop"
    steps(room, 20)
    assert len(room.sentries) <= w.stats["max"]
    room.enemies = []
    room.spawns = []
    room.advance(game.STEP)
    assert not room.fighting and not room.sentries, "sentries should pack up between waves"


def bosses():
    """Boss events: the chosen boss on every tenth wave, tougher with each tier, with its skulls."""
    room = fresh()
    p = room.players[1]
    assert [k for k, *_ in room.groups(10)][0] == "boss"
    room.bosses = "ironmaw"
    first = room.groups(10)[0]
    assert first[0] == "ironmaw" and first[1] == 1
    room.bosses = "random"
    assert room.groups(20)[0][0] in game.EVENT_BOSSES and room.groups(20) == room.groups(20)
    room.wave = 20
    big = room.spawn("ironmaw", 0)
    room.wave = 10
    small = room.spawn("ironmaw", 0)
    assert big.tier == 2 and small.tier == 1 and big.max > small.max * 3, "tier 2 should be tougher"
    room.enemies = []
    # The Ironmaw: sharp things bounce off; at a skull it grows a shell and charges.
    e = put(room, "ironmaw", 6, hp=10000)
    a = tower_at(room, p, "archer", 3, 3)
    room.hurt(e, 500, a, a.stats)
    assert e.hp == 10000
    room.damage(e, 3500, None)
    assert e.shell > 0 and e.charge > room.fight_t and len(e.skulls) == 1
    hp = e.hp
    room.damage(e, 10, None)
    assert e.hp == hp, "the shell should soak up damage first"
    room.sell(p, a)
    room.enemies = []
    # The Gravewarden turns untouchable at a skull and raises Ghosts.
    g = put(room, "gravewarden", 8, hp=10000)
    room.damage(g, 3500, None)
    room.advance(0)
    assert g.shield > room.fight_t and sum(e.kind == "ghost" for e in room.enemies) == D.RAISE[0] + D.RAISE[1]
    hp = g.hp
    room.damage(g, 100, None)
    assert g.hp == hp, "a shielded Gravewarden was hurt"
    room.enemies = []
    # The Stormhulk knocks out the best tower near it, which stops firing.
    t = tower_at(room, p, "archer", 5, 3)
    t.spent = 9999
    s = put(room, "stormhulk", 6, hp=10 ** 7)
    s.zap_t = 0.01
    room.advance(game.STEP)
    assert t.dazed > room.fight_t and any(x[1] == "zap" for x in room.effects)
    kills, cool = t.dmg, t.cool
    steps(room, 1)
    assert t.dmg == kills, "a knocked-out tower fired"
    room.sell(p, t)
    room.enemies = []


def items():
    """One-use items: paid from your own purse, aimed where they belong, on a cooldown."""
    room = fresh()
    p = room.players[1]
    p.gold = 1000
    assert not room.use_item(p, "caltrops", 2, 3), "caltrops off the road"
    assert room.use_item(p, "caltrops", 2, 2) and len(room.traps) == 1
    assert p.gold == 1000 - D.item_cost("caltrops", 1)
    assert not room.use_item(p, "caltrops", 3, 2), "caltrops again during the cooldown"
    assert not room.use_item(p, "nonsense", 2, 2) and not room.use_item(p, "keg", 2.5, 2)
    gold = p.gold
    e = put(room, "grunt", 5, hp=1000)
    assert room.use_item(p, "keg", 4, 2) and e.hp < 1000 and p.gold < gold
    assert room.use_item(p, "tar", 4, 4) and room.traps[-1].kind == "tar"
    e.d, e.speed = 7, 0
    room.advance(0)
    room.spring()
    assert e.slow > 0, "tar should slow"
    assert not room.use_item(p, "hired", 4, 4), "a hired bow on the road"
    assert room.use_item(p, "hired", 5, 5) and room.sentries and room.sentries[-1].parent is None
    assert room.use_item(p, "horn") and room.rally[1] == D.ITEMS["horn"]["rate"]
    assert room.use_item(p, "flask") and e.stun > 0
    room.fighting = False
    assert not room.use_item(p, "keg", 4, 2), "a powder keg between waves"
    p.gold = 0
    room.fighting = True
    p.items = {}
    assert not room.use_item(p, "caltrops", 2, 2), "an item with no gold"
    assert D.item_cost("caltrops", 30) > D.item_cost("caltrops", 1)


def endless_and_stuns():
    """Endless grows much tougher and faster past wave 30; towers' stuns can't lock an enemy forever."""
    assert D.health(40) > 5 * (1 + 0.45 * 39 + 0.06 * 39 ** 2), "endless health should compound"
    assert D.health(30) == 1 + 0.45 * 29 + 0.06 * 29 ** 2 and D.pace(30) == 1 and 1 < D.pace(40) <= D.ENDLESS_SPEED_MAX
    room = fresh()
    p = room.players[1]
    tower_at(room, p, "frost", 3, 3, 1, 4)  # Blizzard: stunning pulses every 0.55 s
    e = put(room, "grunt", 5, hp=10 ** 9, speed=0.0001)
    stunned = 0
    for _ in range(300):
        room.advance(game.STEP)
        stunned += e.stun > 0
    assert stunned < 0.6 * 300, f"stunned {stunned} of 300 steps: towers' stuns lock enemies"
    assert stunned > 0


def heroes():
    """Heroes: free, one each, placed on free squares; they level on the waves they see (the
    experience is the player's), anyone may train them, only their owner moves them (between waves),
    they can't be sold or upgraded, they fight, they unlock two abilities, and each is once in a room."""
    for kind, h in D.HEROES.items():
        assert len(h["levels"]) == D.HERO_LEVELS - 1 and len(h["abilities"]) == 2, kind
        assert all(k in h["base"] for k in ("mode", "range", "rate", "dmg")), kind
    assert D.HERO_XP_TO == sorted(D.HERO_XP_TO) and D.hero_level(0) == 1 and D.hero_level(10 ** 6) == D.HERO_LEVELS
    room = game.Room("HER")
    room.saving = False
    a, b = Browser(room, "A"), Browser(room, "B")
    room.task.cancel()
    a.do(t="start")
    gold = a.p.gold
    a.do(t="hero", k="wren", x=2, y=2)  # on the road: refused
    a.do(t="hero", k="nobody", x=2, y=3)
    assert not room.towers
    a.do(t="hero", k="wren", x=2, y=3)
    h = room.at[(2, 3)]
    assert h.hero and h.level == 1 and a.p.gold == gold, "a hero is free"
    a.do(t="hero", k="oda", x=3, y=3)
    assert len(room.towers) == 1, "one hero each"
    b.do(t="hero", k="wren", x=3, y=3)
    assert len(room.towers) == 1, "each hero only once in a room"
    b.do(t="hero", k="oda", x=3, y=3)
    assert len(room.towers) == 2
    hb = room.at[(3, 3)]
    a.do(t="sell", id=h.id)
    a.do(t="up", id=h.id, path=0)
    assert h.id in room.towers and h.tiers == [0, 0], "heroes can't be sold or upgraded"
    a.read()
    assert any(t.get("h") and t["lv"] == 1 for t in a.read()["state"]["towers"])
    # a wave seen: experience for each hero's owner
    room.wave, room.fighting, room.spawns, room.enemies = 12, True, [], []
    room.advance(game.STEP)
    xp = round(D.HERO_XP(12) * D.hero_share(2))  # two players: each hero gets two thirds
    assert D.hero_share(1) == 1 and a.p.hero_xp == xp and b.p.hero_xp == xp and h.level == 2, (a.p.hero_xp, h.level)
    assert h.stats["dmg"] == D.HEROES["wren"]["levels"][0]["set"]["dmg"]
    # training: anyone may pay, up a level at a time
    b.p.gold = 10000
    cost = room.train_cost(h)
    assert cost == math.ceil((D.HERO_XP_TO[2] - a.p.hero_xp) * D.TRAIN_PRICE)
    b.do(t="train", id=h.id)
    assert h.level == 3 and b.p.gold == 10000 - cost and [x["name"] for x in h.abilities] == ["Piercing Volley"]
    for _ in range(10):
        b.do(t="train", id=h.id)
    assert h.level == D.HERO_LEVELS and room.train_cost(h) is None and len(h.abilities) == 2
    assert h.abilities[0]["dmg"] > D.HEROES["wren"]["abilities"][0][1]["dmg"], "abilities grow with the levels"
    # it fights, and both abilities go off
    room.fighting = True
    room.spawns = [(999, "grunt", 0)]
    e = put(room, "grunt", 2.5, hp=10 ** 6)
    steps(room, 2)
    assert h.dmg > 0 and h.kills == 0
    a.do(t="ability", id=h.id, n=0)
    a.do(t="ability", id=h.id, n=1)
    assert h.cd > 0 and h.cd2 > 0 and room.mark[0] > room.fight_t and e.hp < 10 ** 6
    snap = room.snapshot()
    assert snap["a"][h.id] > 0 and snap["a2"][h.id] > 0
    # moving: only its owner, only between waves; the level stays with the player
    a.do(t="dismiss", id=h.id)
    assert h.id in room.towers, "a hero moved mid-wave"
    b.do(t="dismiss", id=h.id)
    room.fighting, room.enemies, room.spawns = False, [], []
    b.do(t="dismiss", id=h.id)
    assert h.id in room.towers, "someone else moved a hero"
    a.do(t="dismiss", id=h.id)
    assert h.id not in room.towers
    a.do(t="hero", k="ysolde", x=5, y=5)
    assert room.at[(5, 5)].level == D.HERO_LEVELS, "a new hero should come at the player's level"
    # Brannoc makes towers beside him hit harder; Oda's Supply Drop is shared out
    b.p.hero_xp = D.HERO_XP_TO[-1]
    room.level_heroes()
    room.fighting = True
    room.spawns = [(999, "grunt", 0)]
    put(room, "grunt", 2.5, hp=10 ** 6)
    before = a.p.gold + b.p.gold
    b.do(t="ability", id=hb.id, n=0)
    assert round(a.p.gold + b.p.gold - before) == hb.abilities[0]["gold"], "Supply Drop pays its gold once, shared out"
    room.fighting, room.enemies, room.spawns = False, [], []
    b.do(t="dismiss", id=hb.id)
    b.do(t="hero", k="brannoc", x=6, y=3)
    b.p.hero_xp = D.HERO_XP_TO[-1]
    room.level_heroes()
    arch = tower_at(room, b.p, "archer", 7, 3)
    assert arch.power == D.hero_stats("brannoc", D.HERO_LEVELS)["power"]


def gates():
    """Forks share their enemies; a gate opens on its wave, trappers learn the new road, the browsers
    are told."""
    room = fresh("fork")
    room.fighting = False
    room.wave = 0
    room.start_wave()
    routes = {r for _, _, r in room.spawns}
    assert routes == {0, 1}, "a fork's enemies should take both ways"
    room = fresh("breach")
    room.fighting = False
    room.wave = 9
    room.start_wave()
    assert {r for _, _, r in room.spawns} == {0} and room.open == (0,)
    pts = len(room.road_pts)
    room.fighting, room.spawns = False, []
    room.start_wave()
    assert room.wave == 11 and room.open == (0, 1) and len(room.road_pts) > pts
    assert {r for _, _, r in room.spawns} == {0, 1} and [0, "gate"] in room.effects
    room.fighting, room.spawns, room.wave = False, [], 20
    room.start_wave()
    assert room.open == (0, 1, 2) and {r for _, _, r in room.spawns} == {0, 1, 2}
    for m in D.MAPS.values():
        assert len(D.opens(m)) == len(m["paths"]) and min(D.opens(m)) == 1


def new_abilities():
    """The new towers' final evolutions' abilities do what they say."""
    room = fresh()
    p = room.players[1]
    put(room, "grunt", 4, hp=10 ** 6)
    t = tower_at(room, p, "trapper", 3, 3, 0, 4)
    assert room.use_ability(t) and len(room.traps) >= 10, "Carpet of Spikes"
    room.sell(p, t)
    room.traps = []
    t = tower_at(room, p, "trapper", 3, 3, 1, 4)
    assert not room.use_ability(t), "Detonate with no mines laid"
    room.put_trap("mine", 4.0, 3.0, t.stats, t, 30)
    e = room.enemies[0]
    hp = e.hp
    assert room.use_ability(t) and e.hp < hp and not [x for x in room.traps if x.hits > 0], "Detonate"
    room.sell(p, t)
    t = tower_at(room, p, "workshop", 3, 3, 1, 4)
    assert room.use_ability(t) and len(room.sentries) == 2 * t.stats["max"], "Emergency Build"
    room.sell(p, t)
    room.sentries = []
    t = tower_at(room, p, "arcanist", 3, 3, 1, 4)
    assert room.use_ability(t) and room.unmake > room.fight_t, "Unmake"
    room.sell(p, t)
    room.enemies = []
    victims = [put(room, "grunt", 4 + i * 0.1, hp=1000) for i in range(3)]
    t = tower_at(room, p, "alchemist", 3, 3, 0, 4)
    gold = p.gold
    bounty = sum(v.bounty for v in victims)
    assert room.use_ability(t) and all(v.hp <= 0 for v in victims), "Transmute"
    assert abs(p.gold - gold - 2 * bounty) < 1e-6, "Transmute should pay double"
    room.sell(p, t)
    room.enemies = []
    near, far = put(room, "grunt", 7, hp=1000), put(room, "grunt", 20, hp=1000)
    t = tower_at(room, p, "bladewheel", 5, 4, 0, 4)
    assert room.use_ability(t) and near.hp <= 0 and far.hp == 1000, "Blade Storm"
    room.sell(p, t)


def saves():
    """Records, the end-of-game summary, and saving and resuming a game."""
    import importlib
    from app.holdfast import save as S
    importlib.reload(S)
    room = game.Room("SAV")
    a, b = Browser(room, "A"), Browser(room, "B")
    room.task.cancel()
    a.do(t="start")
    t1 = room.build(a.p, "archer", 2, 3)
    room.upgrade(b.p, t1, 0)
    t1.kills, t1.dmg, t1.target = 7, 300.0, "strong"
    hero = room.place_hero(a.p, "oda", 5, 5)
    a.p.hero_xp = D.HERO_XP_TO[4]
    room.level_heroes()
    hero.kills = 3
    room.lives, room.leaks = 17, {3: 3}
    room.wave = 4
    room.save_game()
    listed = S.list_for(a.p.token)
    assert len(listed) == 1 and "wave 5 next" in listed[0]["summary"] and S.list_for(b.p.token)
    assert a.read()["saves"]["list"][0]["id"] == room.game_id
    gid = room.game_id
    # A new room: A comes back (B doesn't, yet), and resumes.
    room2 = game.Room("RES")
    a2 = Browser(room2, "A")
    room2.task.cancel()
    assert a2.read()["saves"]["list"][0]["id"] == gid
    a2.do(t="resume", id="nope")
    assert room2.phase == "lobby" and "note" in a2.read()
    a2.do(t="resume", id=gid)
    assert room2.phase == "play" and room2.wave == 4 and room2.lives == 17 and room2.leaks == {3: 3}
    t = next(t for t in room2.towers.values() if not t.hero)
    assert (t.kind, t.path, t.tier, t.kills, t.target, t.owner) == ("archer", 0, 1, 7, "strong", a2.p.id)
    h2 = next(t for t in room2.towers.values() if t.hero)
    assert (h2.kind, h2.level, h2.kills, h2.owner, a2.p.hero_xp) == ("oda", 5, 3, a2.p.id, D.HERO_XP_TO[4])
    ghost_b = next(q for q in room2.players.values() if q.name == "B")
    assert not ghost_b.connected and ghost_b.seated, "B should have a seat to come back to"
    b2 = Browser(room2, "B")
    assert b2.p is ghost_b and b2.p.connected, "B came back as someone new"
    assert a2.read()["state"]["players"][0]["gold"] == int(a.p.gold)
    # Losing ends the game: a record, a summary, and the save is gone.
    room2.lives = 0
    room2.fighting = True
    room2.spawns = [(999, "grunt", 0)]
    room2.tick()
    st = a2.read()["state"]
    assert st["phase"] == "lost" and st["summary"]["mvp"]["kills"] == 7 and st["summary"]["leaks"] == [[3, 3]], st.get("summary")
    assert st["record_new"] and st["records"][0]["wave"] == 4 and not S.list_for(a.p.token)
    # Winning: wave 30 done, then the host can carry on into endless waves.
    room3 = game.Room("WIN")
    c = Browser(room3, "C")
    room3.task.cancel()
    c.do(t="start")
    room3.wave, room3.fighting, room3.spawns, room3.enemies = D.WAVES, True, [], []
    room3.tick()
    assert room3.phase == "won" and c.read()["state"]["summary"]["won"]
    assert S.records("meadow", "normal")[0]["wave"] == D.WAVES
    c.do(t="endless")
    assert room3.phase == "play" and room3.endless and not room3.fighting
    room3.next_in = 0
    room3.advance(game.STEP)
    assert room3.wave == D.WAVES + 1 and room3.fighting


asyncio.run(main())
