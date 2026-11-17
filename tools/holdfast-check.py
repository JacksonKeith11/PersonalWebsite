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
        assert len(t["cost"]) == len(t["levels"]) == 3, kind
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
    assert a.read()["state"]["towers"] == [[t.id, "archer", 0, 2, 3, a.p.id, 50]]
    # Anyone may upgrade; only the builder may sell.
    b.do(t="up", id=t.id)
    assert t.level == 1 and b.p.gold == 65 and t.spent == 110
    b.do(t="sell", id=t.id)
    assert t.id in room.towers
    b.do(t="up", id=t.id)  # can't afford the last level
    b.do(t="up", id=999)
    assert t.level == 1
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
    print("Holdfast: building, upgrading, selling, giving, readying, watching, losing and starting again hold up")


asyncio.run(main())
