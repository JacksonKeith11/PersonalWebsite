"""Checks Holdfast's room headlessly: the rules around the fight rather than its balance.

    python3 tools/holdfast-check.py

Pretend browsers join a room and play: building is refused on the road, on rocks, on another tower,
off the board and without the gold; anyone may upgrade but only the builder may sell; gold can be
given; Ready sends the wave early; kills pay everyone equally and the snapshots carry the enemies;
a fifth player watches; a lost keep ends the game and the host reopens the room. Every wave of
every map is also checked to be made of known enemies. (`tools/holdfast-sim.py` covers balance.)
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
            for n in range(D.EVOLUTION + 1):
                st = D.stats(kind, t["paths"].index(p), n)
                assert st["mode"] in ("shoot", "splash", "aura", "chain", "support", "income") and st["range"] > 0
                assert st["mode"] in ("support", "income") or (st["dmg"] > 0 and st["rate"] > 0), (kind, n)
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
    assert a.read()["state"]["towers"] == [{"id": t.id, "k": "archer", "p": None, "n": 0, "x": 2, "y": 3,
                                            "o": a.p.id, "s": 50, "kills": 0, "dmg": 0}]
    # Anyone may upgrade; only the builder may sell. The first upgrade picks the path for good.
    b.do(t="up", id=t.id)
    b.do(t="up", id=t.id, path=2)
    assert t.tier == 0
    b.do(t="up", id=t.id, path=0)
    assert (t.path, t.tier) == (0, 1) and b.p.gold == 65 and t.spent == 110 and t.stats["dmg"] == D.stats("archer", 0, 1)["dmg"]
    b.p.gold += 500
    b.do(t="up", id=t.id, path=1)
    assert t.tier == 1, "a tower changed path"
    b.p.gold -= 500
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
    run(room, 12)
    snap = a.read()["s"]
    assert snap["e"] and all(len(e) == 6 and D.KINDS[e[1]] == "grunt" for e in snap["e"])
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
    print("Holdfast: building, upgrading, evolving, selling, giving, readying, watching, every tower's effects, "
          "losing and starting again hold up")


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
    es = [enemy("grunt", 5 + i * 0.2, hp=1000) for i in range(3)]
    fight(0.4)  # one volley (a new tower waits 0.3 s)
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
    fight(0.5)
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
    assert not room.fighting and p.gold - gold == 20 + 4 * room.wave + D.stats("mint", 1, 1)["income"]
    clear()


asyncio.run(main())
