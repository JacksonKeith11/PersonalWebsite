"""Runs Scramble's server headlessly, on a fake clock, and checks it holds together.

    python3 tools/scramble-check.py

Bots race whole games of every length; each must get round every course well inside the time
limit, and the points must add up. Then a pretend browser: its positions are passed on, a finish
that comes too soon is ignored, a real one starts the 25-second countdown, whoever doesn't finish
is placed by distance, and joining and leaving mid-race behave. Prints how long the bots took.
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
            assert len(room.course["segs"]) - 2 == game.SEGMENTS[0] + round(3 * (rnd - 1) / (rounds - 1))
            run(room, game.COUNTDOWN - 0.2)
            assert all(p.x == 60 for p in room.racers()), "a bot left before the start"
            # the host never moves; the bots must all get round on their own
            while room.phase == "race":
                run(room, 1)
            bots = [p for p in room.players.values() if p.bot]
            done = [p.fin for p in bots if p.fin]
            assert done and min(done) < 90, f"no bot got round the course in round {rnd}"
            assert max(done) <= min(done) + game.AFTER_FIRST + 0.1
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
    # Someone arriving mid-race watches, and gets the course; leaving again, they're forgotten.
    b = Browser(room, "B")
    assert not b.p.racing and b.read()["course"]["round"] == 1
    room.leave(b.p, b.queue)
    assert b.p.id not in room.players
    run(room, room.course["finish"] / C.RUN)
    a.do(t="p", v=[room.course["finish"] + 50, 0, 1, 0, 0])
    assert a.p.fin and room.ends == a.p.fin + game.AFTER_FIRST and a.read()["state"]["ends"] == room.ends
    # A drops out: with only a bot still running the round ends in a couple of seconds, and A keeps the points.
    room.leave(a.p, a.queue)
    assert a.p.id in room.players
    left = room.now()
    while room.phase == "race":
        run(room, game.TICK)
    assert room.now() - left < 2.2, "the round waited for a bot with nobody left watching"
    assert room.phase == "results" and a.p.points == 10 and bot.points == 7
    print(f"Scramble: {len(times)} bot runs finished in {min(times):.0f}-{max(times):.0f} s "
          f"(average {sum(times) / len(times):.0f}), {slow} ran out of time; scoring, finishing and watching hold up")


asyncio.run(main())
