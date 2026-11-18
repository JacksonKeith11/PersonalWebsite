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
    view = a.read()["state"]["towers"][0]
    assert {k: v for k, v in view.items() if k != "un"} == {
        "id": t.id, "k": "archer", "p": None, "n": 0, "x": 2, "y": 3, "o": a.p.id, "s": 50, "kills": 0, "dmg": 0,
        "tg": "first", "cs": False}, view
    assert view["un"][0] == a.p.id and 0 < view["un"][1] <= game.UNDO
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
    saves()
    print("Holdfast: building, upgrading, evolving, selling, giving, readying, watching, every tower's effects, "
          "targeting, Ghosts, undo, abilities, Menders, Splitters, summons, endless, records, saving and "
          "resuming hold up")


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
    t.undo = (clock.monotonic() - 1, p.id, "up", 100)
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
    assert s_.hp <= 0 and len(swarm) == D.ENEMIES["splitter"]["split"] and all(e.d <= 4 for e in swarm)
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
    t = next(iter(room2.towers.values()))
    assert (t.kind, t.path, t.tier, t.kills, t.target, t.owner) == ("archer", 0, 1, 7, "strong", a2.p.id)
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
