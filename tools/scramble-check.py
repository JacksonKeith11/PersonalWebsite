"""Runs Scramble's server headlessly, on a fake clock, and checks it holds together.

    python3 tools/scramble-check.py

Bots race whole games of every length; each must get round every course well inside the time
limit, and the points must add up. Then a pretend browser: its positions are passed on, a finish
that comes too soon is ignored, a real one starts the 25-second countdown, whoever doesn't finish
is placed by distance, and joining and leaving mid-race behave. Then items: who gets what, boxes,
and what each item does to people and to bots, shields included. Prints how long the bots took.
(`tools/scramble-check.mjs` is the other half: it proves a player can get through each segment.)
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.scramble import course as C  # noqa: E402
from app.scramble import game  # noqa: E402


class Clock:
    t = 1000.0

    def monotonic(self):
        return self.t


clock = Clock()
game.time = clock


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
    for _ in range(round(secs / game.TICK)):
        clock.t += game.TICK
        room.tick()


async def main():
    # Courses: every segment's route is continuous and runs left to right.
    for seed in range(40):
        c, legs, risks = C.build(seed, 8)
        assert len(c["segs"]) == 10 and len(risks) == 10 and c["finish"] < c["length"]
        for a, b in zip(legs, legs[1:]):
            assert abs(a[3] - b[1]) < 1e-6 and a[4] == b[2] and b[3] >= b[1] - 1e-6, (seed, a, b)
        assert all(leg[5] > 0 or leg[0] == "run" for leg in legs)

    # Left alone, every bot gets to the end of every course, however clumsy it is.
    room = game.Room("TEST")
    for seed in range(30):
        room.course, room.legs, room.risks = C.build(seed, 8)
        bot = game.Player(1, "Bot", "#fff", bot=True)
        bot.skill, room.t0, room.ends, room.order = 0.62, clock.t, None, []
        room.players = {1: bot}
        for _ in range(round(240 / game.TICK)):
            room.move_bot(bot, game.TICK)
            clock.t += game.TICK
        assert bot.fin, f"a bot never finished course {seed}"

    times, slow = [], 0
    for rounds in game.ROUNDS:
        room = game.Room("TEST")
        host = Browser(room, "Host")
        room.task.cancel()  # the test turns the clock by hand
        for _ in range(7):
            host.do(t="bot", op="add")
        host.do(t="bot", op="add")  # a ninth racer: no room
        assert len(room.players) == 8
        host.do(t="rounds", v=rounds)
        host.do(t="start")
        for rnd in range(1, rounds + 1):
            assert room.phase == "race" and room.round == rnd, (room.phase, room.round)
            lo, hi = game.SEGMENTS
            assert len(room.course["segs"]) - 2 == lo + round((hi - lo) * (rnd - 1) / (rounds - 1))
            run(room, game.COUNTDOWN - 0.2)
            assert all(p.x == 60 for p in room.racers()), "a bot left before the start"
            # the host never moves; the bots must all get round on their own
            while room.phase == "race":
                run(room, 1)
            bots = [p for p in room.players.values() if p.bot]
            done = [p.fin for p in bots if p.fin]
            assert done and min(done) < 150, f"no bot got round the course in round {rnd}"
            assert max(done) <= min(done) + max(game.AFTER_FIRST, game.AFTER_SHARE * min(done)) + 0.1
            times += done
            slow += len(bots) - len(done)
            assert room.order[-1] == host.p.id and host.p.gain == game.POINTS[7]
            assert sorted(p.gain for p in room.players.values()) == sorted(game.POINTS)
            while room.phase == "results":
                run(room, game.TICK)
        assert room.phase == "final"
        assert sum(p.points for p in room.players.values()) == sum(game.POINTS) * rounds
        host.do(t="again")
        assert room.phase == "lobby"

    # A browser racing one bot.
    room = game.Room("TEST")
    a = Browser(room, "A")
    room.task.cancel()
    a.do(t="bot", op="add")
    a.do(t="rounds", v=3)
    a.do(t="start")
    bot = next(p for p in room.players.values() if p.bot)
    bot.skill = 0.3  # slow enough that A finishes first
    bot.boxes = set(range(99))  # and no items, so it can't swap its way there
    assert a.read()["course"]["course"]["finish"] == room.course["finish"] and "legs" not in a.last["course"]["course"]
    run(room, game.COUNTDOWN + 1)
    a.do(t="p", v=[400, -30, 1, 1, 0])
    assert (a.p.x, a.p.y, a.p.air) == (400, -30, 1)
    for bad in ([1, 2], "x", [1, 2, 3, 4, "5"], [float("nan"), 0, 1, 0, 0]):
        a.do(t="p", v=bad)
    assert a.p.x == 400
    run(room, 0.1)
    ps = {p[0]: p for p in a.read()["pos"]["ps"]}
    assert ps[a.p.id][1:3] == [400, -30] and ps[bot.id][1] > 60
    a.do(t="p", v=[room.course["finish"] + 50, 0, 1, 0, 0])
    assert a.p.fin is None, "a finish a second into the race was believed"
    a.do(t="p", v=[400, 0, 1, 0, 0])
    # Someone arriving mid-race watches, and gets the course; leaving again, they're forgotten.
    b = Browser(room, "B")
    assert not b.p.racing and b.read()["course"]["round"] == 1
    room.leave(b.p, b.queue)
    assert b.p.id not in room.players
    run(room, room.course["finish"] / C.RUN)
    a.do(t="p", v=[room.course["finish"] + 50, 0, 1, 0, 0])
    assert a.p.fin and room.ends == a.p.fin + max(game.AFTER_FIRST, game.AFTER_SHARE * a.p.fin) and a.read()["state"]["ends"] == room.ends, (a.p.fin, room.ends, bot.fin, room.order)
    # A drops out: with only a bot still running the round ends in a couple of seconds, and A keeps the points.
    room.leave(a.p, a.queue)
    assert a.p.id in room.players
    left = room.now()
    while room.phase == "race":
        run(room, game.TICK)
    assert room.now() - left < 2.2, "the round waited for a bot with nobody left watching"
    assert room.phase == "results" and a.p.points == 10 and bot.points == 7

    # Items.
    W = game.item_weights
    assert W(0, 0, 0) == {"boost": 1.0}, "alone, only boosts are any use"
    lead = W(0, 0, 3)
    assert lead["bolt"] == lead["freeze"] == lead["swap"] == 0 and lead["trap"] > 0
    last = W(1, 3, 0)
    assert last["trap"] == 0 and last["swap"] > 0 and last["freeze"] > last["shield"]
    assert W(0.4, 2, 2)["swap"] == 0, "only the back half may swap"

    room = game.Room("ITEM")
    a, b = Browser(room, "A"), Browser(room, "B")
    room.task.cancel()
    a.do(t="bot", op="add")
    a.do(t="start")
    bot = next(p for p in room.players.values() if p.bot)
    bot.skill = 0.0  # stays put unless something moves it
    run(room, game.COUNTDOWN + 0.5)
    boxes = room.course["boxes"]
    assert boxes and all(len(bx) == 2 for bx in boxes) and len(boxes) == (len(room.course["segs"]) - 1) // 2
    # A box gives one item, once, to someone near it with empty hands.
    a.do(t="p", v=[boxes[0][0] - 400, 0, 1, 0, 0])
    a.do(t="grab", i=0)
    assert a.p.item is None, "a box was claimed from too far away"
    a.do(t="p", v=[boxes[0][0], 0, 1, 0, 0])
    for bad in (-1, 99, "0", 0.0):
        a.do(t="grab", i=bad)
    assert a.p.item is None
    a.do(t="grab", i=0)
    assert a.p.item in game.ITEMS and a.read()["state"]["players"][0]["item"] == a.p.item
    first = a.p.item
    a.do(t="grab", i=0)
    assert a.p.item == first and a.p.boxes == {0}

    def use(who, item):
        """`who` (a Browser, or a bot) uses `item`; returns the fx as A's browser saw it."""
        p = who if isinstance(who, game.Player) else who.p
        p.item = item
        room.use(p)
        fx = a.read()["fx"]
        assert fx["k"] == item and fx["by"] == p.id and p.item is None, fx
        return fx

    # Bolt: the racer just ahead is knocked out, unless they have a shield.
    a.do(t="p", v=[1000, 0, 1, 0, 0])
    b.do(t="p", v=[1200, 0, 1, 0, 0])
    bot.x = 3000
    assert use(a, "bolt")["to"] == [b.p.id]
    b.p.shield = True
    fx = use(a, "bolt")
    assert fx["to"] == [] and fx["blocked"] == [b.p.id] and not b.p.shield
    assert use(b, "bolt")["to"] == [bot.id] and bot.dead and bot.down == game.KNOCKOUT
    run(room, game.KNOCKOUT + 0.1)
    assert not bot.dead
    # Nobody ahead: it fizzles.
    bot.x = 3000
    assert use(bot, "bolt")["to"] == []
    # Freeze: everyone ahead runs at half speed for a while.
    fx = use(a, "freeze")
    assert sorted(fx["to"]) == sorted([b.p.id, bot.id]) and room.speed(bot) == game.FREEZE_SPEED
    run(room, 0.1)
    pos = {q[0]: q for q in a.read()["pos"]["ps"]}
    assert pos[bot.id][6] & 2, "a frozen racer isn't drawn frozen"
    run(room, game.FREEZE)
    assert room.speed(bot) == 1
    # Boost.
    assert use(bot, "boost")["to"] == [bot.id] and room.speed(bot) == game.BOOST_SPEED
    # Swap: the two trade the last places they stood.
    a.do(t="p", v=[1500, -30, 1, 0, 0])
    b.do(t="p", v=[1700, 0, 1, 0, 0])
    b.do(t="p", v=[1750, -200, 1, 1, 0])  # mid-jump: where B last stood still counts
    bot.x = 100
    fx = use(a, "swap")
    assert fx["warp"][str(a.p.id)][:2] == [1700, 0] and fx["warp"][str(b.p.id)][:2] == [1500, -30], fx
    assert (a.p.x, b.p.x) == (1700, 1500)
    # Swapping with a bot puts it down on the course where you were.
    room.leave(b.p, b.queue)
    b.p.fin = 1  # out of the way
    bot.x, bot.safe = 2500, (2500, 0)
    a.do(t="p", v=[2000, 0, 1, 0, 0])
    use(a, "swap")
    assert a.p.x == 2500 and 1700 < bot.x <= 2000 and not bot.dead, (a.p.x, bot.x, bot.dead)
    # Shield.
    use(a, "shield")
    assert a.p.shield and a.read()["state"]["players"][0]["shield"]
    # Trap: dropped where you stand (or when you land); it catches a bot once, then expires.
    a.do(t="p", v=[2600, 0, 1, 1, 0])
    a.p.safe = (2400, 0)
    use(a, "trap")
    assert not room.traps and a.p.trap_pending
    a.do(t="p", v=[2650, 0, 1, 0, 0])
    assert room.traps and room.traps[0][1:4] == [2650 - game.TRAP_W // 2, 0, game.TRAP_W]
    assert a.read()["state"]["traps"][0][4] == a.p.id
    tid, tx = room.traps[0][0], room.traps[0][1]
    run_leg = next(i for i, L in enumerate(room.legs) if L[0] == "run" and L[3] - L[1] > 100 and L[2] == 0)
    room.traps[0][1:3] = [room.legs[run_leg][1] + 30, room.legs[run_leg][2]]
    bot.leg, bot.leg_t, bot.skill, bot.dead, bot.down = run_leg, 0.0, 0.9, 0, 0.0
    run(room, 0.5)
    assert bot.dead and tid in bot.wary, "the trap didn't catch the bot"
    run(room, game.TRAP_LIFE)
    assert not room.traps and not a.read()["state"]["traps"]
    # Bots grab and use items on their own.
    room.leave(a.p, a.queue)
    used = 0
    for p in room.players.values():
        p.fin = None
    bot.leg, bot.leg_t, bot.item, bot.use_at, bot.boxes, bot.dead, bot.down = 0, 0.0, None, None, set(), 0, 0.0
    seen = set()
    a2 = Browser(room, "A")  # someone ahead, to use things on
    a2.do(t="p", v=[room.course["finish"] - 50, 0, 1, 0, 0])
    for _ in range(round(120 / game.TICK)):
        clock.t += game.TICK
        room.tick()
        if bot.item:
            seen.add(bot.item)
        while not a2.queue.empty():
            text = a2.queue.get_nowait()
            if text and '"t":"fx"' in text and f'"by":{bot.id}' in text:
                used += 1
        if room.phase != "race":
            break
    assert seen and used, "the bot never picked up or used an item"
    print(f"Scramble: {len(times)} bot runs finished in {min(times):.0f}-{max(times):.0f} s "
          f"(average {sum(times) / len(times):.0f}), {slow} ran out of time; scoring, finishing and watching hold up")


asyncio.run(main())
