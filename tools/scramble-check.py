"""Runs Scramble's server headlessly, on a fake clock, and checks it holds together.

    python3 tools/scramble-check.py

Bots race whole games of every length; each must get round every course well inside the time
limit, and the points must add up. Then a pretend browser: its positions are passed on, a finish
that comes too soon is ignored, a real one starts the 25-second countdown, whoever doesn't finish
is placed by distance, and joining and leaving mid-race behave. Then items: who gets what, boxes,
and what each item does to people and to bots, shields included (and put up in time against a bolt
on its way); emotes, hats, the room's records and a round's awards. Prints how long the bots took.
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
        c, legs, risks, alts = C.build(seed, 8)
        assert len(c["segs"]) == 10 and len(risks) == 10 and c["finish"] < c["length"]
        for a, b in zip(legs, legs[1:]):
            assert abs(a[3] - b[1]) < 1e-6 and a[4] == b[2] and b[3] >= b[1] - 1e-6, (seed, a, b)
        assert all(leg[5] > 0 or leg[0] == "run" for leg in legs)
        for seg, alt in alts.items():  # another way through a segment starts and ends where it does
            mine = [leg for leg in legs if leg[7] == seg]
            assert alt[0][1:3] == mine[0][1:3] and alt[-1][3:5] == mine[-1][3:5], (seed, seg)
            for a, b in zip(alt, alt[1:]):
                assert abs(a[3] - b[1]) < 1e-6 and a[4] == b[2], (seed, a, b)

    # The fork's slow way: a bot on it waits for the lift, rides it up and carries on.
    c, legs, risks, alts = C.build(3, 1, [C.seg_fork], 0.8)
    room = game.Room("FORK")
    room.course, room.legs, room.risks, room.alts = c, legs, risks, alts
    bot = game.Player(1, "Bot", "#fff", bot=True)
    bot.skill, room.t0, room.ends, room.order, room.phase = 0.62, clock.t, None, [], "race"
    room.players = {1: bot}
    random_was = game.random.random
    game.random.random = lambda: 0.0  # takes the trench, dashes every long jump
    bot.legs = room.route_for(bot)
    game.random.random = random_was
    assert bot.calm == {1} and any(L[0] == "ride" for L in bot.legs)
    m = c["movers"][0]
    rode = dashed = 0
    for _ in range(round(30 / game.TICK)):
        room.move_bot(bot, game.TICK)
        if bot.legs[bot.leg][0] == "ride" and bot.ride and room.now() > bot.ride[0] + 0.3:
            rode += 1
            lift = m[1] + m[5] * game.math.sin(2 * game.math.pi * room.now() / m[6] + m[7])
            assert abs(bot.y - lift) < 1e-6 and m[0] <= bot.x <= m[0] + m[2], "off the lift"
        dashed += bot.air == 2
        clock.t += game.TICK
    assert bot.fin and rode and not bot.falls, (bot.fin, rode, bot.falls)
    bot = game.Player(2, "Ace", "#fff", bot=True)
    bot.skill = 0.92
    game.random.random = lambda: 0.99
    assert room.route_for(bot) is legs and not bot.calm, "a sure-footed bot takes the stones"
    game.random.random = random_was

    # Bots dash across long jumps (and show it), and get round quicker for it.
    c, legs, risks, alts = C.build(4, 1, [C.seg_gaps], 0.8)
    took = []
    for chance in (0.99, 0.0):
        room.course, room.legs, room.risks, room.alts = c, legs, [0] * 3, {}
        bot = game.Player(1, "Bot", "#fff", bot=True)
        bot.skill, room.t0, room.ends, room.order = 0.9, clock.t, None, []
        room.players = {1: bot}
        game.random.random = lambda: chance
        dashed = 0
        while not bot.fin:
            room.move_bot(bot, game.TICK)
            dashed += bot.air == 2
            clock.t += game.TICK
        game.random.random = random_was
        took.append((bot.fin, dashed))
    assert took[0][1] == 0 and took[1][1] > 0 and took[1][0] < took[0][0], took

    # Bots and the timed hazards: one that looks waits for the crushers and gets through untouched;
    # one that doesn't look is caught (as a person would be) unless it hops them; after
    # BOT_CAUGHT_MAX catches in a segment it's let through.
    def hazard_run(seed, chance, looks=True):
        c, legs, risks, alts = C.build(seed, 1, [C.seg_crushers], 1.0)
        room = game.Room("HAZ")
        room.course, room.legs, room.risks, room.alts = c, legs, [0] * 3, {}
        bot = game.Player(1, "Bot", "#fff", bot=True)
        bot.skill, room.t0, room.ends, room.order = 0.8, clock.t, None, []
        room.players = {1: bot}
        if not looks:
            room.bot_waits = lambda *a: False
        game.random.random = lambda: chance
        stood = hopped = 0
        try:
            while not bot.fin and room.now() < 120:
                x = bot.x
                room.move_bot(bot, game.TICK)
                stood += bot.x == x and not bot.dead
                hopped += bot.air and bot.leg < len(legs) and legs[bot.leg][0] == "run"
                clock.t += game.TICK
        finally:
            game.random.random = random_was
        return bot, stood, hopped

    for seed in range(3):
        bot, stood, _ = hazard_run(seed, 0.99)  # never rash, never hops
        assert bot.fin and not bot.falls and stood > 10, ("didn't wait for the crushers", seed, bot.falls, stood)
    bot, stood, _ = hazard_run(0, 0.99, looks=False)
    assert bot.fin and bot.falls == game.BOT_CAUGHT_MAX, ("a crusher should catch a bot that doesn't look", bot.falls)
    bot, stood, hopped = hazard_run(0, 0.0, looks=False)  # hops everything
    assert bot.fin and not bot.falls and hopped, ("a bot that hops shouldn't be caught", bot.falls, hopped)

    # Left alone, every bot gets to the end of every course, however clumsy it is.
    room = game.Room("TEST")
    for seed in range(30):
        room.course, room.legs, room.risks, room.alts = C.build(seed, 8)
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
    assert lead["curse"] == lead["grapple"] == 0 and last["curse"] > 0 and last["grapple"] > 0

    # Records: the room keeps the best time through each kind of segment, and a round's awards.
    room = game.Room("RECS")
    room.course, room.legs, room.risks, room.alts = C.build(5, 4)
    room.t0, room.phase = clock.t, "race"
    segs, names = room.course["segs"], room.course["names"]
    p = game.Player(1, "Rec", "#fff")
    p.racing = True
    room.players = {1: p}
    clock.t += 1
    p.x = segs[1] + 40
    room.timed(p)
    clock.t += 2.5
    p.x = segs[2] + 40
    room.timed(p)
    assert room.records == {names[1]: [2.5, "Rec"]} and room.new_records == [[names[1], 2.5, "Rec"]]
    room.warped(p)  # a swap: no record for the segment you land in
    clock.t += 0.5
    p.x = segs[3] + 40
    room.timed(p)
    assert names[2] not in room.records or names[2] == names[1]
    p.fin, p.falls, p.landed = 30, 0, 2
    q = game.Player(2, "Other", "#000")
    q.fin, q.falls, q.taken = 40, 3, 2
    assert game.awards([p, q]) == [["Never fell", 1], ["Most bolted", 2]], game.awards([p, q])

    room = game.Room("ITEM")
    a, b = Browser(room, "A"), Browser(room, "B")
    room.task.cancel()
    a.do(t="bot", op="add")
    a.do(t="start")
    bot = next(p for p in room.players.values() if p.bot)
    bot.skill = 0.0  # stays put unless something moves it
    room._hz_for, room._hz, room.hazard_segs = room.course, game.Hazards({}), set()  # (nor a saw catches it)
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
        a.last.pop("fx", None)
        a.last.pop("warn", None)
        room.use(p)
        if item in ("bolt", "freeze") and "warn" in a.read():
            # on its way: everyone is warned, and it lands a moment later
            warn = a.last["warn"]
            assert warn["k"] == item and warn["by"] == p.id and warn["in"] == game.INCOMING, warn
            for _ in range(round(2 / game.TICK)):
                clock.t += game.TICK
                room.tick()
                if "fx" in a.read():
                    break
        fx = a.read()["fx"]
        assert fx["k"] == item and fx["by"] == p.id and p.item is None, fx
        return fx

    # Bolt: the racer just ahead is knocked out, unless they have a shield.
    a.do(t="p", v=[1000, 0, 1, 0, 0])
    b.do(t="p", v=[1200, 0, 1, 0, 0])
    room.place_bot(bot, 3000, 0)  # (bots stand where their legs say)
    assert use(a, "bolt")["to"] == [b.p.id]
    b.p.shield = True
    fx = use(a, "bolt")
    assert fx["to"] == [] and fx["blocked"] == [b.p.id] and not b.p.shield
    fx = use(b, "bolt")
    assert fx["to"] == [bot.id] and bot.dead and bot.down == game.KNOCKOUT, (fx, bot.dead, bot.down)
    run(room, game.KNOCKOUT + 0.1)
    assert not bot.dead
    # Nobody ahead: it fizzles.
    room.place_bot(bot, 3000, 0)  # (bots stand where their legs say)
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
    # A bolt on its way can still be blocked by a shield put up in time.
    a.p.fin = None
    a.do(t="p", v=[1000, 0, 1, 0, 0])
    # (on ground ahead of A: the course is random, and a bot's place comes from its route)
    room.place_bot(bot, next(L[1] + 5 for L in room.legs if L[0] == "run" and L[1] >= 1200), 0)
    bot.item = "shield"
    a.p.item = "bolt"
    room.use(a.p)
    assert room.incoming and a.read()["warn"]["to"] == [bot.id]
    room.use(bot)
    assert bot.shield
    run(room, game.INCOMING + 0.1)
    assert not bot.dead and not bot.shield and a.read()["fx"]["blocked"] == [bot.id]
    # Curse: the racer ahead runs backwards for a while (bots: slowly).
    bot.boost_until = 0
    fx = use(a, "curse")
    assert fx["to"] == [bot.id] and room.speed(bot) == game.CURSE_SPEED, (fx, bot.x, a.p.x, room.speed(bot))
    run(room, 0.1)
    assert {q[0]: q for q in a.read()["pos"]["ps"]}[bot.id][6] & 8, "a cursed racer isn't drawn cursed"
    run(room, game.CURSE)
    assert room.speed(bot) == 1
    # Grapple: pulled to where the racer ahead last stood; they stay put.
    bot.safe, there = (bot.x, 0), bot.x
    fx = use(a, "grapple")
    assert fx["warp"][str(a.p.id)][:2] == [round(there), 0] and a.p.x == there == bot.x and str(bot.id) not in fx["warp"], fx
    # The round's numbers: items used and landed, and hits taken.
    assert a.p.used >= 5 and a.p.landed >= 3 and bot.taken >= 2, (a.p.used, a.p.landed, bot.taken)
    # Emotes, a moment apart at most; hats.
    a.last.pop("emote", None)
    a.do(t="emote", k=2)
    assert a.read()["emote"] == {"t": "emote", "by": a.p.id, "k": 2}
    a.last.pop("emote", None)
    a.do(t="emote", k=3)
    assert "emote" not in a.read(), "emotes weren't spaced out"
    clock.t += game.EMOTE_GAP
    for bad in (-1, game.EMOTES, "1"):
        a.do(t="emote", k=bad)
    assert "emote" not in a.read()
    a.do(t="hat", v=3)
    a.do(t="hat", v=game.HATS)
    assert a.p.hat == 3 and a.read()["state"]["players"][0]["hat"] == 3
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
    # Bots wait for a good moment: a grapple only once the racer ahead is well ahead (or they've
    # waited long enough), a trap only once someone's close behind.
    room.place_bot(bot, 3000, 0)  # (on the nearest ground at or before 3000: measure from where it is)
    a.do(t="p", v=[bot.x + 200, 0, 1, 0, 0])
    bot.item, bot.got_at = "grapple", room.now()
    bot.use_at = room.now()
    room.bot_items()
    assert bot.item == "grapple", "grappled someone barely ahead"
    far = next(L[1] + 10 for L in room.legs if L[0] == "run" and L[1] >= bot.x + 600)  # (on ground)
    a.do(t="p", v=[far, 0, 1, 0, 0])
    bot.use_at = room.now()
    room.bot_items()
    assert bot.item is None and abs(bot.x - far) < 300, (bot.item, bot.x)
    room.place_bot(bot, 3000, 0)
    a.do(t="p", v=[bot.x + 200, 0, 1, 0, 0])
    bot.item, bot.got_at, bot.use_at = "grapple", room.now() - game.BOT_PATIENCE - 1, room.now()
    room.bot_items()
    assert bot.item is None, "held on to a grapple for ever"
    bot.item, bot.got_at, bot.use_at = "trap", room.now(), room.now()
    room.bot_items()
    assert bot.item == "trap", "dropped a trap with nobody near behind"
    a.do(t="p", v=[bot.x - 200, 0, 1, 0, 0])
    bot.use_at = room.now()
    room.bot_items()
    assert bot.item is None and room.traps
    room.traps = []
    # Things put down (after Ultimate Chicken Horse): a crossbow, honey, a fan and a black hole go where
    # you stood, facing the way you faced; a plank under your feet and on ahead (lower in mid-air, to
    # land on); all of them are in `state` until they run out.
    room.traps, room.props = [], []
    a.p.fin, a.p.dead = None, 0
    a.do(t="p", v=[2000, 0, 1, 0, 0])
    for kind in ("crossbow", "honey", "fan", "hole"):
        a.p.item = kind
        a.do(t="use", at=[2010, 0, -1, 0])
    assert [q[1] for q in room.props] == ["crossbow", "honey", "fan", "hole"], room.props
    assert all(q[2:5] == [2010, 0, a.p.id] and q[7] == -1 and q[6] - q[5] == game.PROP_LIFE[q[1]] for q in room.props), room.props
    assert a.read()["state"]["props"] == room.props
    a.p.item = "plank"
    a.do(t="use", at=[2100, -200, 1, 1])
    assert room.props[-1][1:4] == ["plank", 2100, -150], "a plank used in mid-air goes below you"
    a.p.item = "honey"
    a.do(t="use", at=[9999, 0, 1, 0])  # nowhere near where A is: the last position is used instead
    assert room.props[-1][2] == 2000, room.props[-1]
    # A bot runs slowly through honey and fans, and may be caught by a crossbow or a black hole (once).
    room.props = []
    run_leg = next(i for i, L in enumerate(room.legs) if L[0] == "run" and L[3] - L[1] > 200 and L[2] == 0)
    L = room.legs[run_leg]
    bot.leg, bot.leg_t, bot.skill, bot.dead, bot.down, bot.fin = run_leg, 0.0, 0.9, 0, 0.0, None
    room.move_bot(bot, game.TICK)
    honey_at = bot.x + 80
    room.props = [[900, "honey", round(honey_at), L[2], a.p.id, room.now(), room.now() + 12, 1]]
    assert room.props_on_bot(bot) == 1.0
    bot.x = honey_at
    assert room.props_on_bot(bot) == game.HONEY
    room.props = [[901, "fan", round(bot.x + 100), L[2], a.p.id, room.now(), room.now() + 8, 1]]
    assert room.props_on_bot(bot) == game.FAN_SLOW
    room.props[0][7] = -1  # a fan facing the other way blows the other way
    assert room.props_on_bot(bot) == 1.0
    room.props = [[902, "crossbow", round(bot.x + 300), L[2], a.p.id, room.now(), room.now() + 10, 1]]
    random_was = game.random.random
    game.random.random = lambda: 0.0
    room.props_on_bot(bot)
    assert bot.dead and 902 in bot.wary, "the crossbow never caught the bot"
    bot.dead, bot.down = 0, 0.0
    room.props_on_bot(bot)
    assert not bot.dead, "a crossbow caught a bot twice"
    room.props[0][4] = bot.id  # its own crossbow doesn't shoot it
    bot.wary = set()
    room.props_on_bot(bot)
    assert not bot.dead
    game.random.random = random_was
    # Props run out.
    room.props = [[903, "plank", 100, 0, a.p.id, room.now(), room.now() + 0.2, 1]]
    run(room, 0.3)
    assert not room.props and not a.read()["state"]["props"]
    # Bomb: knocks out racers right by you (a shield still saves them) and clears what's put down nearby.
    a.do(t="p", v=[3000, 0, 1, 0, 0])
    room.place_bot(bot, 3000, 0)
    bot.x, bot.y, bot.shield = 3060, 0.0, False
    room.traps = [[50, 3100, 0, 40, bot.id, room.now() + 9]]
    room.props = [[51, "crossbow", 3300, 0, bot.id, room.now(), room.now() + 9, 1],
                  [52, "honey", 3800, 0, bot.id, room.now(), room.now() + 9, 1]]
    fx = use(a, "bomb")
    assert fx["to"] == [bot.id] and bot.dead and fx["cleared"] == 2 and fx["pos"] == [3000, 0], fx
    assert [q[0] for q in room.props] == [52] and not room.traps
    run(room, game.KNOCKOUT + 0.1)
    room.place_bot(bot, 3000, 0)
    bot.x, bot.y, bot.shield = 3060, 0.0, True
    fx = use(a, "bomb")
    assert fx["blocked"] == [bot.id] and not bot.dead and not bot.shield, fx
    # Bots put props down when someone's close behind, plank whenever, bomb when someone's near.
    room.props = []
    a.do(t="p", v=[bot.x - 1500, 0, 1, 0, 0])
    for kind in ("crossbow", "honey", "fan", "hole"):
        bot.item, bot.got_at, bot.use_at = kind, room.now(), room.now()
        room.bot_items()
        assert bot.item == kind, f"put a {kind} down with nobody near behind"
        a.do(t="p", v=[bot.x - 200, 0, 1, 0, 0])
        bot.use_at = room.now()
        room.bot_items()
        assert bot.item is None and room.props[-1][1] == kind and room.props[-1][4] == bot.id, kind
        a.do(t="p", v=[bot.x - 1500, 0, 1, 0, 0])
    bot.item, bot.got_at, bot.use_at = "bomb", room.now(), room.now()
    room.bot_items()
    assert bot.item == "bomb", "set off a bomb with nobody and nothing near"
    a.do(t="p", v=[bot.x + 60, bot.y, 1, 0, 0])
    a.p.shield = False
    bot.use_at = room.now()
    room.bot_items()
    assert bot.item is None and a.p.dead, "the bot didn't bomb the racer next to it"
    a.p.dead = 0
    room.props = []
    W = game.item_weights
    assert all(W(0, 0, 3)[k] > 0 for k in ("crossbow", "honey", "fan", "hole")), "the leader gets things to put down"
    assert all(W(1, 3, 0)[k] == 0 for k in ("crossbow", "honey", "fan", "hole")), "nobody behind: nothing to put down"
    assert W(1, 3, 0)["plank"] > W(0, 0, 3)["plank"]
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
