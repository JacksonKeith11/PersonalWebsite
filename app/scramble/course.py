"""Scramble's courses: a start, a run of obstacle segments picked at random, and a finish.

Everything is in pixels with y pointing down; the ground's surface is y = 0 and every segment
starts and ends on it, so any segment can follow any other. A player is a 28 x 40 box that runs at
RUN px/s and jumps about 144 high and 228 far (the physics is the browser's: js/physics.js).
`tools/scramble-check.mjs` proves every segment can be got through by searching the physics.

A built course is plain data for the browser:
    plats   [x, top, w, h, look]                 solid blocks (look 1: a pipe; only the drawing)
    spikes  [x, top, w]                          deadly, standing on a surface at `top`
    saws    [x, y, r, dx, dy, period, phase, kind, look]  deadly circles, swinging dx/dy either side of x, y
                                                 (kind 1 round an ellipse, 2 a pendulum dx long swinging dy radians,
                                                 3 slamming; look 1 a fireball, 2 a spiked ball on a chain)
    movers  [x, top, w, h, dx, dy, period, phase, kind] solid platforms that move the same ways
    pads    [x, top, w, v]                       springs (v: how hard they throw you up; 1150 if left out)
    crumbles [x, top, w]                         blocks that fall half a second after you land on one
    belts   [x, top, w, v]                       conveyor blocks (24 high) carrying whoever stands on them at v px/s
    blinks  [x, top, w, period, phase]           platforms (22 high) there for the first half of each period
                                                 (phase is a fraction of the period)
    winds   [x, top, w, h, v, period, phase]     zones that push whoever is in them at v px/s while
                                                 sin(2 pi t / period + phase) > 0
    lavas   [x0, x1, trigger, base, rate, cap]   rising lava between x0 and x1: its surface is at `base`
                                                 until a racer passes `trigger`, then rises at `rate` px/s
                                                 to `cap` (each racer has their own, as with crumbles)
    bars    [x, y, len, n, period, phase, arms]  firebars: `arms` arms of `n` deadly balls turning round x, y
    crushers [x, top, w, h, dx, dy, period, phase, kind]  deadly blocks moving like movers (kind 3, slamming, if left out)
    cannons [x, y, vx, vy, period, phase, range] fire a deadly shot every period (at (k + phase) periods) that flies `range` px
    jets    [x, top, w, h, period, phase, duty, look]  deadly for the first `duty` of each period (look: 0 flame,
                                                 1 pop-up spikes, 2 laser, 3 plant, 4 chopper, 5 jaws)
    rings   [x, y]                               jump rings: jump while touching one for another jump in mid-air
    barrels [x, y, angle, swing, period, phase, speed, auto]  barrel cannons: jump in, and it fires you off at
                                                 angle (degrees, 0 right, -90 up) + swing * sin(...), by itself if `auto`
    chasers [x0, x1, trigger, speed]             a boulder rolling from x0 to x1 once a racer passes `trigger`
                                                 (each racer has their own, as with lava)
    zones   [x, top, w, h, kind]                 0 low gravity, 1 goo (slow running), 2 ice, 3 updraft
    ledges  [x, top, w]                          one-way platforms: jump up through them, land on top
    portals [ax, ay, bx, by]                     touch the ring at ax, ay and come out at bx, by
    boxes   [x, y]                               item boxes, at the start of every other obstacle
    segs    [x, ...]                             where each segment starts (the checkpoints)
    theme   "meadow" | "desert" | "snow" | "dusk" | "cave"  (set by the server: snow is icy and the
            dunes' sand slows running, in physics.js; the caverns are dark, in main.js)
plus, for the server's bots only, `legs`: the way through as runs and jumps (see `legs_of`), and
`alts`: other ways through some segments (the fork's trench), by segment index, for bots to choose.
"""

import math
import random

RUN = 300  # px/s; the same number as js/physics.js
SAND = 0.8  # running on the dunes' sand is this fast (js/physics.js too)
DEEP = 600  # how far down a ground block goes (past the bottom of the screen)
SPIKE_H = 18


class Seg:
    """One segment being built, in its own coordinates (x from 0)."""

    def __init__(self, name, risk):
        self.name, self.risk = name, risk
        self.plats, self.spikes, self.saws, self.movers, self.pads, self.crumbles = [], [], [], [], [], []
        self.belts, self.blinks, self.winds, self.lavas = [], [], [], []
        self.bars, self.crushers, self.cannons, self.jets, self.rings, self.barrels = [], [], [], [], [], []
        self.chasers, self.zones, self.ledges, self.portals = [], [], [], []
        self.route = []  # (x0, x1, top): the surfaces a bot crosses, in order
        self.alt = []  # another way through, the same way (plus ("ride", mover, x, x, bottom, top) items)
        self.w = 0

    def ground(self, x, w, top=0, h=DEEP, spikes=(), look=0):
        """A block to run across. `spikes` are (x, w) patches on it; the bots' route hops them."""
        self.plats.append([x, top, w, h] + ([look] if look else []))
        at = x
        for sx, sw in spikes:
            self.spikes.append([sx, top, sw])
            self.route.append((at, sx - 26, top))
            at = sx + sw + 26
        self.route.append((at, x + w, top))
        self.w = max(self.w, x + w)
        return x + w

    def mover(self, x, top, w, dx, dy, period, phase=0.0, kind=0, h=22):
        self.movers.append([x, top, w, h, dx, dy, round(period, 3), round(phase, 3), kind])
        self.route.append((x + w * 0.3, x + w * 0.7, top))
        return x + w

    def saw(self, x, y, r, dx, dy, period, phase=0.0, kind=0, look=0):
        self.saws.append([x, y, r, dx, dy, round(period, 3), round(phase, 3), kind, look])

    def pad(self, x, top=0, w=56, v=None):
        self.pads.append([x, top, w] + ([v] if v else []))

    def bar(self, x, y, length, n, period, phase, arms=1):
        self.bars.append([x, y, length, n, round(period, 3), round(phase, 3), arms])

    def crusher(self, x, top, w, h, dx, dy, period, phase, kind=3):
        self.crushers.append([x, top, w, h, dx, dy, round(period, 3), round(phase, 3), kind])

    def cannon(self, x, y, vx, vy, period, phase, reach):
        self.cannons.append([x, y, vx, vy, round(period, 3), round(phase, 3), reach])

    def jet(self, x, top, w, h, period, phase, duty, look=0):
        self.jets.append([x, top, w, h, round(period, 3), round(phase % 1, 3), duty, look])

    def ledge(self, x, top, w, route=None):
        """A one-way platform (bots stand on it like any other; `route`, (x0, x1), if they only
        cross part of it, so the route keeps running left to right where ledges overlap)."""
        self.ledges.append([x, top, w])
        self.route.append((*(route or (x, x + w)), top))
        self.w = max(self.w, x + w)
        return x + w

    def zone(self, x, top, w, h, kind):
        self.zones.append([x, top, w, h, kind])


def seg_start(r, d):
    s = Seg("start", 0)
    s.ground(0, 520)
    return s


def seg_finish(r, d):
    s = Seg("finish", 0)
    s.ground(0, 700)
    return s


def lerp(d, easy, hard):
    return easy + (hard - easy) * d


def more(d):
    """How many extra of a segment's repeated obstacle to add: one past 0.6, two past 1.1."""
    return (d > 0.6) + (d > 1.1)


def seg_gaps(r, d):
    s = Seg("gaps", 0.5)
    x, top = s.ground(0, 170), 0
    for _ in range(r.choice([3, 4]) + (d > 0.6)):
        top = max(-80, min(60, top + r.choice([-50, 0, 50])))
        gap = r.randint(int(lerp(d, 110, 150)), int(lerp(d, 150, 185)))
        x = s.ground(x + gap, r.randint(int(lerp(d, 120, 70)), int(lerp(d, 210, 120))), top)
    s.ground(x + int(lerp(d, 120, 160)), 170)
    return s


def seg_stairs(r, d):
    s = Seg("stairs", 0.4)
    x, top = s.ground(0, 200), 0
    w = int(lerp(d, 110, 70))
    for _ in range(4):
        top -= 80
        x = s.ground(x + r.randint(int(lerp(d, 60, 100)), int(lerp(d, 90, 130))), w, top, h=30)
    x = s.ground(x + 70, 200, top, h=30)
    if d > 0.55:  # a saw guarding the top step
        s.saw(x - 100, top - 70, 24, 70, 0, lerp(d, 2.4, 1.6), r.uniform(0, 6.28))
    s.ground(x + int(lerp(d, 90, 150)), 200)
    return s


def seg_spikes(r, d):
    s = Seg("spikes", 0.6)
    n = 3 + (d > 0.6)
    spikes = [(260 + i * 290 + r.randint(-40, 40), r.randint(int(lerp(d, 50, 90)), int(lerp(d, 80, 140))))
              for i in range(n)]
    s.ground(0, 260 + n * 290, spikes=spikes)
    return s


def seg_saws(r, d):
    s = Seg("saws", 0.8)
    n = 2 if d < 0.4 else 3 if d < 0.7 else 5 + (d > 1.1)
    w = 280 + n * 240
    s.ground(0, w)
    for i in range(n):
        s.saw(220 + i * 240, -112, int(lerp(d, 28, 32)), 0, lerp(d, 88, 100), r.uniform(1.7, 2.3) * lerp(d, 1, 0.7), r.uniform(0, 6.28))
    return s


def seg_ferry(r, d):
    s = Seg("ferry", 0.7)
    s.ground(0, 180)
    s.mover(355, 0, int(lerp(d, 110, 76)), 130, 0, r.uniform(3.0, 3.6) * lerp(d, 1, 0.7), r.uniform(0, 6.28))
    if d > 0.6:  # a saw sweeping the far half of the crossing
        s.saw(470, -150, 26, 0, 60, lerp(d, 2.6, 2.0), r.uniform(0, 6.28))
    s.ground(640, 180, spikes=[(650, int(lerp(d, 20, 50)))] if d > 0.7 else ())  # and spikes on the lip
    return s


def seg_lift(r, d):
    s = Seg("lift", 0.6)
    s.ground(0, 200)
    s.mover(230, -130, int(lerp(d, 110, 76)), 0, 130, r.uniform(3.2, 3.8) * lerp(d, 1, 0.7), r.uniform(0, 6.28))
    if d > 0.5:  # spikes on the ledge you jump to
        s.ground(370, 260, -250, h=30, spikes=[(370 + 90, int(lerp(d, 40, 70)))])
    else:
        s.ground(370, 260, -250, h=30)
    s.ground(700, 200)
    return s


def seg_wall(r, d):
    s = Seg("wall", 0.5)
    s.plats.append([0, 0, 900, DEEP])
    s.plats.append([380, -260, 80, 260])
    s.pad(300)
    s.route += [(0, 328, 0), (385, 455, -260)]
    if d > 0.3:
        w = int(lerp(d, 60, 110))
        s.spikes.append([580, 0, w])
        s.route += [(480, 554, 0), (580 + w + 26, 900, 0)]
    else:
        s.route.append((480, 900, 0))
    s.w = 900
    return s


def seg_pillars(r, d):
    s = Seg("pillars", 0.8)
    x, top = s.ground(0, 160), 0
    w = int(lerp(d, 58, 40))
    for _ in range(5 + more(d)):
        top = max(-80, min(60, top + r.choice([-60, -30, 30, 60])))
        x = s.ground(x + r.randint(int(lerp(d, 105, 125)), int(lerp(d, 135, 160))), w, top)
    s.ground(x + 110, 160)
    return s


def seg_bridge(r, d):
    s = Seg("bridge", 0.8)
    x = s.ground(0, 160)
    x = s.ground(x + 130, 440, -30, h=30)
    s.saw(x - 220, -52, 26, 150, 0, r.uniform(2.2, 2.8) * lerp(d, 1, 0.75), r.uniform(0, 6.28))
    if d > 0.6:
        s.saw(x - 220, -52, 26, 150, 0, r.uniform(2.2, 2.8) * lerp(d, 1, 0.75), r.uniform(0, 6.28))
    s.ground(x + 130, 160)
    return s


def seg_twins(r, d):
    s = Seg("twins", 0.9)
    s.ground(0, 180)
    period, phase = r.uniform(2.6, 3.2) * lerp(d, 1, 0.75), r.uniform(0, 6.28)
    w = int(lerp(d, 100, 70))
    s.mover(250, -40, w, 0, 90, period, phase)
    s.mover(440, -40, w, 0, 90, period, phase + math.pi)
    s.ground(620, 180)
    return s


def seg_springs(r, d):
    s = Seg("springs", 1.0)
    s.ground(0, 200)
    s.pad(132, 0, 60)
    w = int(lerp(d, 110, 80))
    s.ground(460, w)
    s.pad(460 + (w - 60) // 2, 0, 60)
    s.ground(830, w)
    s.pad(830 + (w - 60) // 2, 0, 60)
    s.ground(1200, 200)
    if d > 0.7:  # a saw crossing the top of the first bounce (the one you can wait for)
        s.saw(310, -350, 22, int(lerp(d, 60, 90)), 0, r.uniform(1.8, 2.2) * lerp(d, 1.1, 0.9), r.uniform(0, 6.28))
    return s


def seg_stones(r, d):
    s = Seg("stones", 0.9)
    x, top = s.ground(0, 160), 0
    w = int(lerp(d, 64, 44))
    for i in range(6 + more(d)):
        top = -30 if i % 2 else 10
        x = s.ground(x + r.randint(int(lerp(d, 90, 115)), int(lerp(d, 120, 145))), w, top, h=24)
    s.ground(x + 100, 160)
    return s


def seg_hurdles(r, d):
    s = Seg("hurdles", 0.7)
    n = 3 + more(d)
    at, x = 0, 0
    hurdles = []
    for i in range(n):  # uneven, so it takes looking: no steady beat clears them
        x += r.randint(int(lerp(d, 200, 190)), int(lerp(d, 300, 330)))
        sw, hh = r.randint(int(lerp(d, 70, 90)), int(lerp(d, 100, 125))), r.choice([60, 70, 80])
        hurdles.append((x, sw, hh))
        x += 40 + sw
    w = x + 260
    s.plats.append([0, 0, w, DEEP])
    for x, sw, hh in hurdles:  # spikes before each (to jump from the right place) and after (to clear)
        s.plats.append([x, -hh, 40, hh])
        s.spikes += [[x - 30, 0, 30], [x + 40, 0, sw]]
        s.route += [(at, x - 56, 0), (x + 4, x + 36, -hh)]
        at = x + 40 + sw + 26
    s.route.append((at, w, 0))
    s.w = w
    return s


def seg_crumble(r, d):
    """Blocks over a pit that fall away half a second after you land on one."""
    s = Seg("crumble", 1.0)
    x, top = s.ground(0, 170), 0
    for _ in range(4 + more(d)):
        top = max(-60, min(40, top + r.choice([-40, 0, 40])))
        x += r.randint(int(lerp(d, 80, 110)), int(lerp(d, 105, 135)))
        w = int(lerp(d, 90, 64))
        s.crumbles.append([x, top, w])
        s.route.append((x, x + w, top))
        x += w
    s.ground(x + 110, 170)
    return s


def seg_tunnel(r, d):
    """A low roof hung with saws over a floor of spike patches: only short hops will do."""
    s = Seg("tunnel", 1.0)
    n = 3 + (d > 0.6)
    w = 240 + n * 230
    roof = -150
    spikes = []
    for i in range(n):
        x = 200 + i * 230 + r.randint(-20, 20)
        spikes.append((x, int(lerp(d, 36, 52))))
        s.saw(x + 20 + r.choice([-70, 70]), roof, 26, 40, 0, r.uniform(1.6, 2.2), r.uniform(0, 6.28))
    s.ground(0, w, spikes=spikes)
    s.plats.append([140, roof - 400, w - 240, 400])
    return s


def seg_launch(r, d):
    """A spring over a spiked pit onto a swinging ledge, then a leap to safety."""
    s = Seg("launch", 1.0)
    s.ground(0, 200)
    s.pad(132, 0, 60)
    s.ground(200, 340, 60, spikes=[(200, 340)])  # the pit floor: all spikes
    s.route.pop()  # nobody runs along it
    s.route.pop()
    s.mover(430, -120, int(lerp(d, 120, 90)), int(lerp(d, 50, 80)), 0, r.uniform(2.6, 3.2), r.uniform(0, 6.28))
    s.ground(740, 200)
    return s


def seg_belts(r, d):
    """Conveyor belts over a pit, some carrying you on, some back."""
    s = Seg("belts", 0.6)
    x, top = s.ground(0, 170), 0
    for i in range(3 + more(d)):
        top = max(-60, min(40, top + r.choice([-40, 0, 40])))
        x += r.randint(int(lerp(d, 80, 110)), int(lerp(d, 100, 130)))
        w = r.randint(160, 230)
        v = (1 if i == 0 or r.random() < 0.35 else -1) * int(lerp(d, 90, 150))
        s.belts.append([x, top, w, v])
        s.route.append((x, x + w, top))
        x += w
    s.ground(x + int(lerp(d, 90, 120)), 170)
    return s


def seg_blinks(r, d):
    """Platforms that come and go in a wave: keep up with it."""
    s = Seg("blinkers", 0.9)
    x, top = s.ground(0, 170), 0
    period = r.uniform(3.0, 3.3) * lerp(d, 1, 0.85)  # the wave moves a platform on every quarter period
    w = int(lerp(d, 100, 80))
    for i in range(5 + more(d)):
        top = -30 if i % 2 else 0
        x += r.randint(int(lerp(d, 70, 90)), int(lerp(d, 90, 110)))
        s.blinks.append([x, top, w, round(period, 3), round(-0.25 * i, 3)])
        s.route.append((x, x + w, top))
        x += w
    s.ground(x + 90, 170)
    return s


def seg_gusts(r, d):
    """Gaps with the wind gusting through them, mostly in your face."""
    s = Seg("gusts", 0.6)
    x = s.ground(0, 170)
    for i in range(3 + more(d)):
        gap = r.randint(int(lerp(d, 100, 120)), int(lerp(d, 120, 145)))
        v = (1 if r.random() < 0.3 else -1) * int(lerp(d, 120, 170))
        s.winds.append([x, -420, gap, 620, v, round(r.uniform(2.0, 2.8), 3), round(r.uniform(0, 6.28), 3)])
        x = s.ground(x + gap, r.randint(130, 180))
    return s


def seg_lava(r, d):
    """Lava rises once you step off: climb the ledges above it before it catches you."""
    s = Seg("lava", 0.9)
    x = s.ground(0, 180)
    x0, top = x, 0
    w = int(lerp(d, 110, 84))
    for _ in range(4):
        top -= 55
        x = s.ground(x + r.randint(int(lerp(d, 60, 80)), int(lerp(d, 80, 100))), w, top, h=30)
    top -= 50
    x = s.ground(x + r.randint(60, 80), 200, top, h=30)
    s.lavas.append([x0, x, x0, 40, int(lerp(d, 45, 60)), top + 35])
    s.ground(x, 240)
    return s


def seg_fork(r, d):
    """Two ways over a trench: hop the stones (quick, and saws later on), or drop to the floor and
    ride the lift back up (safe, and slow). Bots take the stones."""
    s = Seg("fork", 0.8)
    s.ground(0, 200)
    floor = 150
    s.plats.append([200, floor, 700, DEEP])  # the trench floor: nobody's route, but a soft landing
    w = int(lerp(d, 56, 40))
    x = 200
    while x < 760:
        x += r.randint(int(lerp(d, 100, 120)), int(lerp(d, 120, 140)))
        if x + w > 880:
            break
        s.ground(x, w, 0, h=24)
        x += w
        if d > 0.55 and r.random() < 0.75 and x < 760:  # a saw over the next gap
            s.saw(x + 60, -70, 24, 0, 40, r.uniform(1.6, 2.2), r.uniform(0, 6.28))
    s.movers.append([905, floor // 2, 90, 22, 0, floor // 2, round(r.uniform(2.8, 3.4), 3), round(r.uniform(0, 6.28), 3)])
    s.ground(1000, 200)
    # the slow way, for cautious bots: down to the floor (spikes to hop on it later on), wait by the lift, ride it up
    sw = int(lerp(d, 40, 70))
    hops = [420, 660] if d > 0.7 else []
    s.spikes += [[x, floor, sw] for x in hops]
    floor_route, at = [], 240
    for x in hops:
        floor_route.append((at, x - 26, floor))
        at = x + sw + 26
    floor_route.append((at, 880, floor))
    s.alt = [(0, 200, 0), *floor_route, ("ride", len(s.movers) - 1, 880, 950, floor, 0), (1000, 1200, 0)]
    return s



# ---------------------------------------------------------------- more segments, after other games
# (what each borrows from is in its docstring; the mechanics are all in js/physics.js)

GRAV, JUMP, DT = 2000, 760, 1 / 120  # js/physics.js's numbers, for working out where a barrel's shot goes


def fly(x, y, angle, v, secs):
    """Where a barrel cannon's shot (the racer's middle) is `secs` after it fires, step by step as
    physics.js moves it (nobody steers for the first FLING seconds)."""
    a = math.radians(angle)
    vx, vy = math.cos(a) * v, math.sin(a) * v
    for _ in range(round(secs / DT)):
        vy = min(vy + GRAV * DT, 1200)
        x, y = x + vx * DT, y + vy * DT
    return round(x), round(y)


def landing(x, y, angle, v, top):
    """Where a shot from a barrel at x, y comes down to `top`, nobody steering: (x at landing)."""
    a = math.radians(angle)
    vx, vy, t = math.cos(a) * v, math.sin(a) * v, 0.0
    while not (vy > 0 and y + 20 >= top):
        vy = min(vy + GRAV * DT, 1200)
        t += DT
        if t > 0.45:  # after the fling, the air slows you to a stop (nobody pressing)
            vx = max(0.0, vx - 1800 * DT) if vx > 0 else min(0.0, vx + 1800 * DT)
        x, y = x + vx * DT, y + vy * DT
    return x


def seg_firebars(r, d):
    """Firebars turning over the path, as in a castle: go while the arm's up."""
    s = Seg("firebars", 0.8)
    n = 2 + (d > 0.6)
    s.ground(0, 260 + n * 300)
    for i in range(n):
        x = 260 + i * 300 + r.randint(-20, 20)
        s.bar(x, -60, int(lerp(d, 90, 115)), 5 + (d > 0.6), r.uniform(2.6, 3.2) * lerp(d, 1.1, 0.85) * r.choice([1, -1]),
              r.uniform(0, 6.28), 2 if d > 0.7 and i % 2 == 0 else 1)
    return s


def seg_firesteps(r, d):
    """Stepping stones over a pit, each with a firebar turning in it: land while it's underneath."""
    s = Seg("firesteps", 1.0)
    x = s.ground(0, 170)
    w = int(lerp(d, 110, 90))
    for i in range(2 + more(d)):
        x = s.ground(x + r.randint(int(lerp(d, 90, 110)), int(lerp(d, 110, 130))), w, -30 * (i % 2), h=40)
        s.bar(x - w // 2, -30 * (i % 2) + 16, int(lerp(d, 70, 90)), 4, r.uniform(2.6, 3.0) * r.choice([1, -1]), r.uniform(0, 6.28))
    s.ground(x + int(lerp(d, 100, 130)), 170)
    return s


def seg_crushers(r, d):
    """A corridor of crushers slamming down: dash under while they're up."""
    s = Seg("crushers", 0.8)
    n = 3 + more(d)
    s.ground(0, 240 + n * 220)
    # on one beat, each a quarter of a beat on from the last for someone running through, so nobody
    # gets through them all without stopping between
    period, phase = r.uniform(2.4, 3.0) * lerp(d, 1, 0.8), r.uniform(0, 6.28)
    for i in range(n):
        s.crusher(240 + i * 220, -330, int(lerp(d, 105, 125)), 70, 0, 260, period,
                  phase + 2 * math.pi * (0.25 * i - i * 220 / RUN / period))
    return s


def seg_crushsteps(r, d):
    """Stepping stones over a pit with a crusher over each: land, then off before it falls."""
    s = Seg("crushsteps", 0.9)
    x = s.ground(0, 170)
    w = int(lerp(d, 110, 90))
    for i in range(3 + more(d)):
        top = -30 * (i % 2)
        x = s.ground(x + r.randint(int(lerp(d, 90, 110)), int(lerp(d, 110, 130))), w, top, h=30)
        s.crusher(x - w + 5, top - 300, w - 10, 60, 0, 240, r.uniform(2.6, 3.2) * lerp(d, 1, 0.85), r.uniform(0, 6.28))
    s.ground(x + int(lerp(d, 100, 130)), 170)
    return s


def seg_cannons(r, d):
    """A cannon on a wall shooting along the ground at you: hop the shots, climb past it."""
    s = Seg("cannons", 0.7)
    run = int(lerp(d, 560, 760))
    s.ground(0, run)
    s.ground(run, 220, -60)
    s.cannon(run - 6, -22, -int(lerp(d, 220, 270)), 0, lerp(d, 2.1, 1.6), r.random(), run - 40)
    if d > 0.7:  # a second gun beside it, on another beat
        s.cannon(run - 6, -22, -int(lerp(d, 180, 220)), 0, lerp(d, 2.9, 2.3), r.random(), run - 40)
    if d > 0.6:  # and another on the wall's top, shooting along it
        s.cannon(run + 214, -82, -230, 0, 2.2, r.random(), 200)
    s.ground(run + 220, 200)
    return s


def seg_crossfire(r, d):
    """Steps up into two cannons' fire, one shooting high and one low."""
    s = Seg("crossfire", 0.8)
    x, top = s.ground(0, 240), 0
    for _ in range(3):
        top -= 50
        x = s.ground(x, int(lerp(d, 200, 160)), top)
    s.cannon(x - 6, top - 22, -240, 0, lerp(d, 2.2, 1.6), r.random(), x - 240)
    s.cannon(x - 6, top - 96, -300, 0, lerp(d, 2.2, 1.6), r.random(), x - 240)
    x = s.ground(x, 200, top)
    s.ground(x, 200)
    return s


def seg_drips(r, d):
    """Drops falling from the cave roof in columns: slip between them."""
    s = Seg("drips", 0.6)
    n = 4 + more(d) * 2
    w = 220 + n * 110
    spikes = [(200 + 110 * i + 40, int(lerp(d, 30, 44))) for i in range(n) if i % 3 == 2 and d > 0.5]
    s.ground(0, w, spikes=spikes)
    for i in range(n):
        s.cannon(200 + 110 * i + r.randint(-10, 10), -430, 0, int(lerp(d, 300, 380)), r.uniform(1.2, 1.7), r.random(), 430)
    return s


def seg_pipes(r, d):
    """Pipes over a pit with biting plants that pop out of them: land when a plant's gone down."""
    s = Seg("pipes", 0.9)
    x = s.ground(0, 170)
    period = r.uniform(2.6, 3.0)
    for i in range(3 + more(d)):
        top = -r.choice([40, 70, 100])
        x += r.randint(int(lerp(d, 80, 100)), int(lerp(d, 100, 120)))
        s.ground(x, 76, top, look=1)
        s.jet(x + 14, top - 48, 48, 48, period, r.random(), round(lerp(d, 0.4, 0.5), 2), 3)
        x += 76
    s.ground(x + int(lerp(d, 90, 120)), 170)
    return s


def seg_ferris(r, d):
    """A wheel of platforms turning over a pit: ride it over the top."""
    s = Seg("ferris", 0.7)
    s.ground(0, 180)
    R, w = 120, int(lerp(d, 76, 56))
    cx = 180 + 60 + R
    period, phase = r.uniform(6.5, 7.5) * lerp(d, 1, 0.7), r.uniform(0, 6.28)
    for k in range(4):
        s.movers.append([cx - w // 2, -40, w, 22, R, R, round(period, 3), round(phase + k * math.pi / 2, 3), 1])
    s.route += [(cx - R - w // 2 + 10, cx - R + w // 2 - 10, -40), (cx - w // 2, cx + w // 2, -40 - R),
                (cx + R - w // 2 + 10, cx + R + w // 2 - 10, -40)]
    if d > 0.7:  # a firebar turning the other way inside the wheel: ride round it, don't jump through
        s.bar(cx, -40, 70, 4, -period / 2, r.uniform(0, 6.28))
    s.ground(cx + R + 60 + w // 2, 180)
    return s


def seg_carousel(r, d):
    """Platforms going round a long loop over a pit, forwards on top and back underneath."""
    s = Seg("carousel", 0.7)
    s.ground(0, 180)
    dx, w = 170, int(lerp(d, 88, 64))
    cx = 180 + 50 + dx
    period, phase = r.uniform(4.8, 5.6) * lerp(d, 1, 0.75), r.uniform(0, 6.28)
    for k in range(3):
        s.movers.append([cx - w // 2, -10, w, 22, dx, 60, round(period, 3), round(phase + k * 2 * math.pi / 3, 3), 1])
    s.route += [(cx - dx - w // 2 + 10, cx - dx, -10), (cx - w // 2, cx + w // 2, -70), (cx + dx, cx + dx + w // 2 - 10, -10)]
    s.ground(cx + dx + 50 + w // 2, 180)
    return s


def seg_switch(r, d):
    """Red and blue blocks that swap in time with each other: hop across as they change."""
    s = Seg("switch", 0.9)
    x = s.ground(0, 170)
    period = round(r.uniform(3.0, 3.4) * lerp(d, 1.05, 0.9), 3)
    for i in range(4 + more(d)):
        x += r.randint(70, int(lerp(d, 90, 95)))
        w = int(lerp(d, 120, 104))
        top = -r.choice([0, 20, 40])
        s.blinks.append([x, top, w, period, 0.5 * (i % 2), 1])
        s.route.append((x, x + w, top))
        x += w
    s.ground(x + 90, 170)
    return s


def seg_fireballs(r, d):
    """Stones over lava, with fireballs leaping out of it between them."""
    s = Seg("fireballs", 0.8)
    x = s.ground(0, 170)
    x0 = x
    for i in range(3 + more(d)):
        gap = r.randint(int(lerp(d, 100, 120)), int(lerp(d, 120, 140)))
        s.saw(x + gap // 2, -30, 14, 0, 130, r.uniform(2.2, 2.8) * lerp(d, 1.1, 0.9), r.uniform(0, 6.28), 0, 1)
        x = s.ground(x + gap, int(lerp(d, 90, 70)), -30 * (i % 2), h=40)
    gap = int(lerp(d, 100, 130))
    s.saw(x + gap // 2, -30, 14, 0, 130, r.uniform(2.2, 2.8), r.uniform(0, 6.28), 0, 1)
    s.lavas.append([x0, x + gap, 10 ** 6, 40, 0, 40])  # never rises: a lake
    s.ground(x + gap, 170)
    return s


def seg_maces(r, d):
    """Spiked balls swinging on chains low across the path."""
    s = Seg("maces", 0.8)
    n = 3 + more(d) + (d > 0.7)
    s.ground(0, 300 + n * 280)
    for i in range(n):
        s.saw(280 + i * 280, -30, 24, 210, round(lerp(d, 0.8, 1.0), 2), r.uniform(2.4, 2.9) * lerp(d, 1.1, 0.9),
              r.uniform(0, 6.28), 2, 2)
    return s


def seg_swings(r, d):
    """Platforms swinging from chains over a pit: jump between them at the ends of their swings."""
    s = Seg("swings", 0.8)
    s.ground(0, 180)
    w, L, A = int(lerp(d, 100, 76)), 170, 0.55
    reach = round(L * math.sin(A))
    period, phase = round(r.uniform(2.8, 3.3), 3), r.uniform(0, 6.28)
    x = 180 + 60 + reach
    for k in range(2 + more(d)):
        s.movers.append([x, -20, w, 22, L, A, period, round(phase + k * math.pi, 3), 2])
        s.route.append((x + 10, x + w - 10, -20))
        x += w + reach + int(lerp(d, 50, 70)) + reach
    s.ground(x - reach - int(lerp(d, 50, 70)) + 60, 180)
    return s


def seg_grinders(r, d):
    """Platforms over a pit, each with a saw running round it: wait in the middle, go behind it."""
    s = Seg("grinders", 0.9)
    x = s.ground(0, 170)
    for i in range(3 + more(d)):
        x += r.randint(int(lerp(d, 90, 110)), int(lerp(d, 110, 130)))
        w = int(lerp(d, 110, 100))
        top = -30 * (i % 2)
        s.ground(x, w, top, h=24)
        s.saw(x + w // 2, top + 12, 20, 82, 82, r.uniform(2.4, 3.0) * lerp(d, 1.1, 0.9) * r.choice([1, -1]), r.uniform(0, 6.28), 1)
        x += w
    s.ground(x + 110, 170)
    return s


def seg_windmill(r, d):
    """A great cross of fire turning over the path: walk under it between the arms."""
    s = Seg("windmill", 1.0)
    s.ground(0, 700)
    s.bar(350, -80, int(lerp(d, 120, 130)), 6, -r.uniform(6.5, 7.5) * lerp(d, 1.1, 0.9), r.uniform(0, 6.28), 3 if d < 0.6 else 4)
    return s


def seg_poppers(r, d):
    """A floor of spikes that pop up in turn: land where they've gone down."""
    s = Seg("poppers", 0.8)
    n = 5 + (d > 0.6) * 2
    w = int(lerp(d, 80, 90))
    s.ground(0, 300 + n * w)
    period = r.uniform(2.2, 2.6) * lerp(d, 1.05, 0.9)
    for i in range(n):
        s.jet(170 + i * w, -26, w, 26, period, r.random(), round(lerp(d, 0.4, 0.5), 2), 1)
    return s


def seg_rings(r, d):
    """A wide pit with rings hanging over it: jump at each ring to jump again in mid-air."""
    s = Seg("rings", 0.8)
    s.ground(0, 180)
    x = 180 + 150
    for i in range(2 + more(d)):
        s.rings.append([x, -100 - 20 * (i % 2)])
        x += int(lerp(d, 200, 220))
    s.ground(x - 40, 180)
    return s


def seg_updraft(r, d):
    """A pit with an updraft over it that carries you up onto a high ledge."""
    s = Seg("updraft", 0.6)
    s.ground(0, 180)
    s.zone(230, -330, int(lerp(d, 170, 140)), 940, 3)
    if d > 0.6:  # a saw by the ledge
        s.saw(330, -420, 22, 60, 0, 2.4, r.uniform(0, 6.28))
    x = s.ground(230 + int(lerp(d, 170, 140)) + 20, 220, -280)
    s.ground(x, 200)
    return s


def seg_thorns(r, d):
    """Stones under a ceiling of thorn balls: short hops only."""
    s = Seg("thorns", 0.8)
    x = s.ground(0, 170)
    for i in range(4 + more(d)):
        gap = r.randint(int(lerp(d, 90, 110)), int(lerp(d, 110, 125)))
        s.saw(x + gap // 2, int(lerp(d, -175, -155)), 22, 0, 0, 1, 0)
        x = s.ground(x + gap, int(lerp(d, 100, 80)), 0, h=30)
    gap = 110
    s.saw(x + gap // 2, -165, 22, 0, 0, 1, 0)
    s.ground(x + gap, 170)
    return s


def seg_barrels(r, d):
    """Barrel cannons that fire you on to the next by themselves: get into the first."""
    s = Seg("barrels", 0.6)
    s.ground(0, 180)
    x, y = 250, -90
    # a saw bobs across the middle of each shot, all on one beat and timed so that there's a moment to
    # get into the first barrel that takes you between every one of them (each barrel holds you 0.25 s)
    period, phase, off = round(r.uniform(1.5, 1.8) * lerp(d, 1.1, 0.9), 3), r.uniform(0, 6.28), 0.25
    # (it bobs from just above the shot to well below, so it's clear of it only near the bottom)
    amp = 48
    for i in range(2 + more(d)):
        angle = r.randint(-30, -10)
        s.barrels.append([x, y, angle, 0, 1, 0, 900, 1])
        mx, my = fly(x, y, angle, 900, 0.165)
        s.saw(mx, my + 10, 20, 0, amp, period, phase + math.pi / 2 - 2 * math.pi * (off + 0.165) / period)
        x, y = fly(x, y, angle, 900, 0.33)
        y = max(-200, y)
        off += 0.33 + 0.25
    angle = -40
    s.barrels.append([x, y, angle, 0, 1, 0, 820, 1])
    land = landing(x, y, angle, 820, 0)
    x = s.ground(int(land) - 200, 420)
    return s


def seg_aim(r, d):
    """Barrel cannons that sway: jump to fire one when it points the right way, at an island and
    then at the far side."""
    s = Seg("aim", 0.8)
    s.ground(0, 180)
    bx, by = 250, -80
    for i, top in enumerate((-40, 0)):
        s.barrels.append([bx, by, -45, int(lerp(d, 20, 30)), round(r.uniform(2.0, 2.4) * lerp(d, 1.0, 0.85), 3),
                          round(r.uniform(0, 6.28), 3), 900, 0])
        tol = lerp(d, 8.5, 6.5)  # degrees either side of -45 that land you
        a, b = landing(bx, by, -45 - tol, 900, top), landing(bx, by, -45 + tol, 900, top)
        lo, hi = int(min(a, b)), int(max(a, b))
        if i == 0:
            x = s.ground(lo - 30, max(110, hi - lo + 40), top, h=40)
            bx, by = x + 70, top - 80
        else:  # a landing as narrow, then a gap: overshoot and you're in it
            x = s.ground(lo - 30, max(110, hi - lo + 40))
            s.ground(x + 110, 220)
    return s


def seg_tires(r, d):
    """Bouncy tyres over a spiked pit: each one throws you on to the next."""
    s = Seg("tires", 0.7)
    s.ground(0, 180)
    x = 180 + int(lerp(d, 90, 110))
    s.ground(180, 1000, 70, spikes=[(180, 1000)])
    s.route.pop()
    s.route.pop()
    for i in range(3 + more(d)):
        w = int(lerp(d, 80, 64))
        s.plats.append([x, -20, w, 90])
        s.pad(x, -20, w, int(lerp(d, 950, 900)))
        s.route.append((x, x + w, -20))
        x += w + int(lerp(d, 170, 190))
    s.plats[1][2] = x - 180  # the spikes run the whole way
    s.spikes[0][2] = x - 180
    s.ground(x, 180)
    return s


def seg_boulder(r, d):
    """A boulder rolling after you down a run of hurdles: don't stop."""
    s = Seg("boulder", 0.8)
    n = 4 + (d > 0.6)
    gaps = [r.randint(230, 300) for _ in range(n)]  # uneven, so it takes looking
    at = [300 + sum(gaps[:i]) for i in range(n)]
    w = 400 + sum(gaps)
    spikes = [(at[i] + 70, int(lerp(d, 60, 100))) for i in range(n) if i % 2]
    s.ground(0, w, spikes=spikes)
    for i in range(n):
        if i % 2 == 0:
            x = at[i]
            s.plats.append([x, -int(lerp(d, 55, 80)), 50, 80])
    # the bots' route over the hurdles: rebuild it from the blocks
    s.route = []
    at = 0
    obstacles = sorted([(p[0], p[0] + p[2], p[1]) for p in s.plats[1:]] + [(a, a + b, None) for a, b in spikes])
    for a, b, top in obstacles:
        if top is None:
            s.route.append((at, a - 26, 0))
            at = b + 26
        else:
            s.route += [(at, a - 30, 0), (a + 4, b - 4, top)]
            at = b + 30
    s.route.append((at, w, 0))
    s.chasers.append([0, w - 80, 230, int(lerp(d, 225, 262))])
    return s


def seg_ropebridge(r, d):
    """A rope bridge of loose planks over a pit: every one gives way as you cross."""
    s = Seg("ropebridge", 0.8)
    x = s.ground(0, 170)
    for i in range(int(lerp(d, 8, 11))):
        x += r.randint(int(lerp(d, 25, 45)), int(lerp(d, 50, 90)))  # uneven, so it takes looking
        w = r.randint(int(lerp(d, 40, 30)), int(lerp(d, 56, 44)))
        s.crumbles.append([x, 0, w])
        s.route.append((x, x + w, 0))
        x += w
    s.ground(x + int(lerp(d, 30, 50)), 170)
    return s


def seg_yoku(r, d):
    """Blocks that appear one after another up a staircase and vanish behind you."""
    s = Seg("yoku", 0.9)
    x, top = s.ground(0, 170), 0
    period = r.uniform(3.2, 3.5) * lerp(d, 1, 0.9)
    w = int(lerp(d, 90, 76))
    for i in range(6):
        top += -50 if i < 4 else 60
        x += r.randint(int(lerp(d, 60, 80)), int(lerp(d, 80, 95)))
        s.blinks.append([x, top, w, round(period, 3), round(-0.25 * i, 3), 2])
        s.route.append((x, x + w, top))
        x += w
    s.ground(x + 80, 170)
    return s


def seg_icefloes(r, d):
    """Slippery floes over a pit: you slide on, and you slide off."""
    s = Seg("icefloes", 0.8)
    x, top = s.ground(0, 170), 0
    for _ in range(4 + more(d)):
        top = max(-60, min(40, top + r.choice([-40, 0, 40])))
        x = s.ground(x + r.randint(int(lerp(d, 90, 110)), int(lerp(d, 110, 140))), r.randint(int(lerp(d, 140, 100)), int(lerp(d, 200, 140))), top, h=30)
    x = s.ground(x + 110, 170)
    s.zone(170, -600, x - 340, 1200, 2)
    return s


def seg_lasers(r, d):
    """Laser gates switching on and off: through each while it's off."""
    s = Seg("lasers", 0.7)
    n = 3 + (d > 0.6) * 2
    w = 260 + n * 170
    spikes = [(200 + 170 * i + 90, 36) for i in range(n - 1) if d > 0.6 and i % 2]
    s.ground(0, w, spikes=spikes)
    period = r.uniform(2.2, 2.6) * lerp(d, 1.05, 0.9)
    for i in range(n):
        s.jet(200 + 170 * i, -440, 16, 440, period, r.random(), round(lerp(d, 0.5, 0.58), 2), 2)
    return s


def seg_pistons(r, d):
    """Pistons in a pit that shoot up and sink back slowly: ride them up, hop across."""
    s = Seg("pistons", 0.8)
    x = s.ground(0, 170)
    for i in range(3 + more(d)):
        x += r.randint(int(lerp(d, 70, 90)), int(lerp(d, 90, 110)))
        w = int(lerp(d, 100, 80))
        s.mover(x, 30, w, 0, -int(lerp(d, 100, 130)), r.uniform(2.6, 3.2), r.uniform(0, 6.28), 3, h=40)
        x += w
    s.ground(x + 90, 170)
    return s


def seg_factory(r, d):
    """Conveyor belts with saws running along them: jump the saws, mind the belts."""
    s = Seg("factory", 0.8)
    x, top = s.ground(0, 170), 0
    for i in range(3 + more(d)):
        top = max(-40, min(40, top + r.choice([-40, 0, 40])))
        x += r.randint(int(lerp(d, 80, 100)), int(lerp(d, 100, 120)))
        w = r.randint(200, 240)
        v = (1 if r.random() < 0.5 else -1) * int(lerp(d, 80, 130))
        s.belts.append([x, top, w, v])
        s.route.append((x, x + w, top))
        s.saw(x + w // 2, top - 20, 18, w // 2 - 24, 0, r.uniform(2.2, 2.8) * lerp(d, 1.1, 0.9), r.uniform(0, 6.28))
        x += w
    s.ground(x + 100, 170)
    return s


def seg_sweeper(r, d):
    """A long bar spinning round a post at knee height: jump it as it sweeps past."""
    s = Seg("sweeper", 0.9)
    n = 1 + (d > 0.6)
    s.ground(0, 280 + n * 460)
    for i in range(n):
        s.bar(340 + i * 460, -50, int(lerp(d, 160, 190)), 9, r.uniform(3.2, 3.6) * lerp(d, 1.1, 0.85) * (1 if i % 2 else -1),
              r.uniform(0, 6.28), 2)
    return s


def seg_slime(r, d):
    """Rising slime under a climb of one-way ledges: jump up through them before it gets you."""
    s = Seg("slime", 0.9)
    x0 = s.ground(0, 180)
    top, x = 0, x0
    w = int(lerp(d, 140, 120))
    step = int(lerp(d, 60, 70))
    for i in range(5):
        top -= 62
        lx = x0 + 30 + step * i
        s.ledge(lx, top, w, (lx, lx + step))
    x = lx + w
    top -= 50
    x = s.ground(x + 30, 200, top, h=30)
    s.lavas.append([x0, x, x0, 40, int(lerp(d, 45, 60)), top + 35])
    s.ground(x, 240)
    return s


def seg_hexfloor(r, d):
    """Two floors of tiles over a pit, each giving way: drop through the top to the bottom."""
    s = Seg("hexfloor", 0.8)
    x0 = s.ground(0, 170)
    n = int(lerp(d, 9, 12))
    w, gap = 58, int(lerp(d, 32, 44))
    x = x0 + 40
    for i in range(n):
        tw = r.randint(int(lerp(d, 40, 32)), w)  # tiles of all sizes
        s.crumbles.append([x, -110, tw])
        s.route.append((x, x + tw, -110))
        if i < n - 1:
            s.crumbles.append([x + (tw + gap) // 2, 0, tw])
        x += tw + gap
    s.ground(x + 60, 170)
    return s


def seg_hammers(r, d):
    """Short platforms over a pit, swept by swinging hammers that shove you off."""
    s = Seg("hammers", 0.8)
    x = s.ground(0, 170)
    for i in range(2 + more(d)):
        x += int(lerp(d, 90, 110))
        w = int(lerp(d, 170, 140))
        s.ground(x, w, 0, h=30)
        s.movers.append([x + w // 2 - 20, -60, 40, 56, 200, round(lerp(d, 0.7, 0.85), 2), round(r.uniform(2.4, 2.9), 3),
                         round(r.uniform(0, 6.28), 3), 2])
        x += w
    s.ground(x + 100, 170)
    return s


def seg_sawmill(r, d):
    """Stones between saws going every way: along, up and down, round and round."""
    s = Seg("sawmill", 1.0)
    x = s.ground(0, 170)
    for i in range(3 + more(d)):
        gap = r.randint(int(lerp(d, 90, 110)), int(lerp(d, 110, 130)))
        kind = r.choice([0, 0, 1])
        if kind == 1:
            s.saw(x + gap // 2, -40, 20, 70, 70, r.uniform(2.4, 3.0) * r.choice([1, -1]), r.uniform(0, 6.28), 1)
        elif r.random() < 0.5:
            s.saw(x + gap // 2, -80, 22, 0, 70, r.uniform(1.8, 2.4), r.uniform(0, 6.28))
        else:
            s.saw(x + gap // 2, -150, 22, 50, 0, r.uniform(1.8, 2.4), r.uniform(0, 6.28))
        x = s.ground(x + gap, int(lerp(d, 90, 70)), -30 * (i % 2), h=30)
    s.ground(x + 110, 170)
    return s


def seg_crocs(r, d):
    """Crocodiles in a pit to hop across, snapping their jaws now and then."""
    s = Seg("crocs", 0.9)
    x = s.ground(0, 170)
    period = r.uniform(2.4, 2.8)
    for i in range(3 + more(d)):
        x += r.randint(int(lerp(d, 70, 90)), int(lerp(d, 90, 110)))
        w = int(lerp(d, 120, 100))
        s.ground(x, w, 10, h=36, look=2)
        s.jet(x, -24, w, 34, period, r.random(), round(lerp(d, 0.3, 0.4), 2), 5)
        x += w
    s.ground(x + 90, 170)
    return s


def seg_moon(r, d):
    """Low gravity: floaty jumps across gaps too wide anywhere else."""
    s = Seg("moon", 0.6)
    x, top = s.ground(0, 170), 0
    for _ in range(3 + more(d)):
        top = max(-120, min(60, top + r.choice([-60, 0, 60])))
        gap = r.randint(int(lerp(d, 240, 290)), int(lerp(d, 290, 340)))
        x = s.ground(x + gap, r.randint(int(lerp(d, 110, 80)), int(lerp(d, 160, 110))), top, h=30)
    x = s.ground(x + int(lerp(d, 240, 300)), 170)
    s.zone(0, -900, x, 1500, 0)
    return s


def seg_clouds(r, d):
    """Clouds you can jump up through: climb them, then down the far side."""
    s = Seg("clouds", 0.7)
    x0 = s.ground(0, 170)
    w, step, top = int(lerp(d, 150, 120)), int(lerp(d, 80, 95)), 0
    for i in range(6):
        top += -66 if i < 4 else 70
        lx = x0 + 40 + i * step + (40 if i >= 4 else 0)
        s.ledge(lx, top, w, (lx, lx + (step if i < 5 else w)))
    s.ground(lx + w + int(lerp(d, 60, 90)), 170)
    return s


def seg_tower(r, d):
    """A tall climb of one-way ledges with a cannon shooting across it."""
    s = Seg("tower", 0.8)
    x0 = s.ground(0, 170)
    w, top = 120, 0
    for i in range(5):
        top -= 70
        lx = x0 + 30 + i * 46
        s.ledge(lx, top, w, (lx, lx + 46))
    x = s.ground(lx + w + 20, 200, top - 40, h=30)
    s.cannon(x - 10, -200, -int(lerp(d, 200, 260)), 0, lerp(d, 2.6, 2.0), r.random(), x - x0 - 20)
    s.ground(x + int(lerp(d, 60, 90)), 200)
    return s


def seg_choppers(r, d):
    """Blades that chop down across a low corridor: through between chops."""
    s = Seg("choppers", 0.8)
    n = 3 + more(d)
    w = 240 + n * 150
    s.ground(0, w)
    s.plats.append([150, -520, w - 300, 410])  # the roof
    period = r.uniform(1.8, 2.2) * lerp(d, 1.1, 0.9)
    for i in range(n):
        s.jet(200 + 150 * i, -110, 22, 110, period, r.random(), round(lerp(d, 0.32, 0.46), 2), 4)
    return s


def seg_darts(r, d):
    """Climbing steps while darts fly down them from the top."""
    s = Seg("darts", 0.8)
    x, top = s.ground(0, 200), 0
    tops = []
    for _ in range(4):
        top -= 70
        tops.append((x, top))
        x = s.ground(x + int(lerp(d, 50, 70)), int(lerp(d, 150, 120)), top, h=30)
    x = s.ground(x + 60, 220, top - 20, h=30)
    for sx, st in tops[1::2]:
        s.cannon(x - 30, st - 20, -260, 0, lerp(d, 2.4, 1.9), r.random(), x - 30 - sx)
    s.ground(x + 60, 180)
    return s


def seg_portals(r, d):
    """A wall too tall to jump: a portal before it puts you on the far side."""
    s = Seg("portals", 0.5)
    s.ground(0, 900)
    s.plats.append([420, -420, 100, 420])
    s.portals.append([300, -100, 640, -140])  # (a jump up to it)
    period, phase = r.uniform(1.8, 2.2) * lerp(d, 1.0, 0.8), r.uniform(0, 6.28)
    for k in range(1 + (d > 0.7)):  # circling it
        s.saw(300, -100, 21, int(lerp(d, 56, 64)), int(lerp(d, 56, 64)), period, phase + k * math.pi, 1)
    # spikes where you come out: go in on the way up of a jump to carry over them
    sw = int(lerp(d, 110, 170))
    s.spikes.append([600, 0, sw])
    s.route = [(0, 280, 0), (600 + sw + 26, 900, 0)]
    return s


def seg_burners(r, d):
    """Burners that roar up out of the floor in turn: past while they're off, or over the top."""
    s = Seg("burners", 0.8)
    n = 3 + (d > 0.6)
    s.ground(0, 260 + n * 200)
    period = r.uniform(2.2, 2.6) * lerp(d, 1.05, 0.9)
    for i in range(n):
        s.jet(200 + 200 * i, -130, 36, 130, period, r.random(), round(lerp(d, 0.4, 0.5), 2), 0)
    return s


def seg_skyway(r, d):
    """Platforms sliding to and fro at different heights over a pit."""
    s = Seg("skyway", 0.8)
    x = s.ground(0, 180)
    for i in range(3):
        w = int(lerp(d, 100, 80))
        x = s.mover(x + 140, -60 - 60 * (i % 2), w, 70, 0, r.uniform(2.6, 3.2) * lerp(d, 1, 0.85), r.uniform(0, 6.28))
    s.ground(x + 140, 180)
    return s


def seg_sliders(r, d):
    """Bridges that shoot out over a pit and creep back: ride one out, jump to the next."""
    s = Seg("sliders", 0.8)
    x = s.ground(0, 180)
    for i in range(2 + more(d)):
        w = int(lerp(d, 120, 100))
        s.mover(x, -30 * (i % 2), w, 150, 0, r.uniform(2.8, 3.2), r.uniform(0, 6.28), 3)
        x += w + 150 + int(lerp(d, 40, 60))
    s.ground(x, 180)
    return s


def seg_ceiling(r, d):
    """A spiked ceiling that comes down to the floor and goes up again: under it while it's high."""
    s = Seg("ceiling", 0.7)
    n = 1 + more(d)
    w = int(lerp(d, 380, 480))
    s.ground(0, 160 + n * (w + 120) + 80,
             spikes=[(160 + i * (w + 120) + w // 2 - 20, 40) for i in range(n)] if d > 0.7 else ())  # to hop under it
    for i in range(n):
        s.crusher(160 + i * (w + 120), -550, w, 400, 0, 140, r.uniform(3.4, 4.0) * lerp(d, 1.1, 0.85), r.uniform(0, 6.28), 0)
    return s


def seg_elevators(r, d):
    """Lifts going up and down, one after another, up to a high ledge."""
    s = Seg("elevators", 0.7)
    x = s.ground(0, 180)
    x = s.mover(x + 50, -70, int(lerp(d, 100, 80)), 0, 70, r.uniform(2.8, 3.4), r.uniform(0, 6.28))
    x = s.ground(x + 70, 110, -150, h=30)
    x = s.mover(x + 50, -220, int(lerp(d, 100, 80)), 0, 70, r.uniform(2.8, 3.4), r.uniform(0, 6.28))
    x = s.ground(x + 70, 160, -300, h=30)
    s.ground(x + 80, 200)
    return s


def seg_swamp(r, d):
    """Sticky goo that slows running: hop across it (hops keep your speed)."""
    s = Seg("swamp", 0.5)
    n = 3 + more(d)
    spikes, x = [], 220
    for _ in range(n):  # uneven, so it takes looking
        sw = r.randint(int(lerp(d, 50, 70)), int(lerp(d, 75, 100)))
        spikes.append((x, sw))
        x += sw + r.randint(int(lerp(d, 170, 150)), int(lerp(d, 260, 240)))
    w = x + 120
    s.ground(0, w, spikes=spikes)
    s.zone(150, -10, w - 260, 20, 1)
    return s


def seg_geysers(r, d):
    """Stones over lava, with fire spouting up out of it between them."""
    s = Seg("geysers", 0.8)
    x = s.ground(0, 170)
    x0 = x
    period = r.uniform(2.2, 2.6)
    for i in range(3 + more(d)):
        gap = r.randint(int(lerp(d, 100, 120)), int(lerp(d, 120, 140)))
        s.jet(x + 12, -220, gap - 24, 250, period, r.random(), round(lerp(d, 0.35, 0.45), 2), 0)
        x = s.ground(x + gap, int(lerp(d, 100, 80)), -20 * (i % 2), h=40)
    gap = 110
    s.lavas.append([x0, x + gap, 10 ** 6, 40, 0, 40])
    s.ground(x + gap, 170)
    return s


def seg_skyrings(r, d):
    """Rings up and down over a pit, with saws by some of them."""
    s = Seg("skyrings", 0.9)
    s.ground(0, 180)
    x, y = 330, -100
    for i in range(3 + more(d)):
        s.rings.append([x, y])
        if i % 2 and d > 0.5:
            s.saw(x, y + 110, 20, 40, 0, 2.2, r.uniform(0, 6.28))
        x += int(lerp(d, 200, 215))
        y = -100 - r.choice([0, 30, 50])
    s.ground(x - 40, 180)
    return s


def seg_chimney(r, d):
    """An updraft up a chimney, with saws sliding across it: steer round them on the way up."""
    s = Seg("chimney", 0.8)
    s.ground(0, 180)
    s.zone(220, -360, 200, 960, 3)
    s.saw(320, -150, 20, int(lerp(d, 60, 80)), 0, r.uniform(2.2, 2.8), r.uniform(0, 6.28))
    if d > 0.5:
        s.saw(320, -260, 20, int(lerp(d, 60, 80)), 0, r.uniform(2.2, 2.8), r.uniform(0, 6.28))
    x = s.ground(440, 200, -310)
    s.ground(x, 180)
    return s


def seg_asteroids(r, d):
    """Low gravity, and saws circling the rocks you land on."""
    s = Seg("asteroids", 0.8)
    x, top = s.ground(0, 170), 0
    for i in range(3 + more(d)):
        top = -r.choice([0, 60, 120])
        gap = r.randint(int(lerp(d, 220, 260)), int(lerp(d, 260, 300)))
        w = int(lerp(d, 120, 100))
        x = s.ground(x + gap, w, top, h=30)
        s.saw(x - w // 2, top + 15, 18, 95, 95, r.uniform(3.0, 3.6) * r.choice([1, -1]), r.uniform(0, 6.28), 1)
    x = s.ground(x + 260, 170)
    s.zone(0, -900, x, 1500, 0)
    return s


def seg_furnace(r, d):
    """Conveyor belts with burners coming up through them."""
    s = Seg("furnace", 0.9)
    x, top = s.ground(0, 170), 0
    period = r.uniform(2.2, 2.6)
    for i in range(2 + more(d)):
        x += r.randint(int(lerp(d, 80, 100)), int(lerp(d, 100, 120)))
        w = r.randint(220, 260)
        v = (1 if r.random() < 0.5 else -1) * int(lerp(d, 80, 120))
        top = -30 * (i % 2)
        s.belts.append([x, top, w, v])
        s.route.append((x, x + w, top))
        s.jet(x + w // 2 - 18, top - 120, 36, 120, period, r.random(), round(lerp(d, 0.35, 0.45), 2), 0)
        x += w
    s.ground(x + 100, 170)
    return s


def seg_gauntlet(r, d):
    """A bit of everything in a row: spikes, a crusher, a firebar, and more spikes."""
    s = Seg("gauntlet", 1.0)
    s.ground(0, 1100, spikes=[(200, int(lerp(d, 50, 80))), (840, int(lerp(d, 50, 80)))])
    s.crusher(400, -330, 80, 70, 0, 260, r.uniform(2.6, 3.0), r.uniform(0, 6.28))
    s.bar(650, -60, int(lerp(d, 90, 110)), 5, r.uniform(2.6, 3.0) * r.choice([1, -1]), r.uniform(0, 6.28))
    return s


MORE = [seg_firebars, seg_firesteps, seg_crushers, seg_crushsteps, seg_cannons, seg_crossfire, seg_drips, seg_pipes,
        seg_ferris, seg_carousel, seg_switch, seg_fireballs, seg_maces, seg_swings, seg_grinders, seg_windmill,
        seg_poppers, seg_rings, seg_updraft, seg_thorns, seg_barrels, seg_aim, seg_tires, seg_boulder, seg_ropebridge,
        seg_yoku, seg_icefloes, seg_lasers, seg_pistons, seg_factory, seg_sweeper, seg_slime, seg_hexfloor, seg_hammers,
        seg_sawmill, seg_crocs, seg_moon, seg_clouds, seg_tower, seg_choppers, seg_darts, seg_portals, seg_burners,
        seg_skyway, seg_sliders, seg_ceiling, seg_elevators, seg_swamp, seg_geysers, seg_skyrings, seg_chimney,
        seg_asteroids, seg_furnace, seg_gauntlet]

SEGMENTS = [seg_gaps, seg_stairs, seg_spikes, seg_saws, seg_ferry, seg_lift, seg_wall, seg_pillars,
            seg_bridge, seg_twins, seg_springs, seg_stones, seg_hurdles, seg_crumble, seg_tunnel, seg_launch,
            seg_belts, seg_blinks, seg_gusts, seg_lava, seg_fork, *MORE]
THEMES = ("meadow", "desert", "snow", "dusk", "cave")
D_FIRST, D_LAST = 0.75, 1.3  # the first and last obstacles' difficulty (past 1, segments go on scaling past their "hard" numbers)


def legs_of(route, seg, movers=0):
    """A route as legs for a bot: ("run" | "jump", x0, y0, x1, y1, seconds, arc height, segment), or
    ("ride", x0, y0, x1, y1, 0, mover, segment): wait at x0 for the lift `mover` (its index in the
    course, `movers` being how many came before this segment's) to come down, then ride it up."""
    legs = []
    for i, item in enumerate(route):
        if item[0] == "ride":
            _, m, xa, xb, bottom, top = item
            legs.append(("ride", xa, bottom, xb, top, 0.0, movers + m, seg))
            continue
        x0, x1, top = item
        if i and not (x0 - legs[-1][3] < 1 and top == legs[-1][4]):
            px, py = legs[-1][3], legs[-1][4]
            rise = max(0, py - top)
            arc = 60 + rise
            secs = max(0.42 + rise / 500, (x0 - px) / RUN)
            legs.append(("jump", px, py, x0, top, secs, arc, seg))
        if x1 > x0 or not i:
            legs.append(("run", x0, top, max(x0, x1), top, max(0.0, x1 - x0) / RUN, 0, seg))
    return legs


def build(seed, n, makers=None, d=None):
    """A course of `n` obstacle segments (or exactly `makers`), from difficulty D_FIRST at the
    first to 1 at the last (or all at difficulty `d`, 0 to 1). Returns the course, the bots' legs,
    each segment's risk and the other ways through ({segment: legs}, to swap in for that segment's)."""
    r = random.Random(seed)
    if makers is None:
        pool = r.sample(SEGMENTS, len(SEGMENTS))
        makers = [pool[i % len(pool)] for i in range(n)]
    keys = ("plats", "spikes", "saws", "movers", "pads", "crumbles", "belts", "blinks", "winds", "bars", "crushers",
            "cannons", "jets", "rings", "barrels", "zones", "ledges")
    course = {k: [] for k in keys}
    course.update({"lavas": [], "chasers": [], "portals": [], "boxes": [], "segs": [], "names": []})
    legs, risks, alts, x = [], [], {}, 0
    for i, make in enumerate([seg_start, *makers, seg_finish]):
        if d is not None:
            level = d
        else:
            level = D_FIRST + (D_LAST - D_FIRST) * (i - 1) / max(1, len(makers) - 1)
        s = make(r, min(D_LAST, max(0.0, level)))
        movers = len(course["movers"])
        for key in keys:
            course[key] += [[v[0] + x, *v[1:]] for v in getattr(s, key)]
        course["lavas"] += [[a + x, b + x, trig + x, *rest] for a, b, trig, *rest in s.lavas]
        course["chasers"] += [[a + x, b + x, trig + x, v] for a, b, trig, v in s.chasers]
        course["portals"] += [[ax + x, ay, bx + x, by] for ax, ay, bx, by in s.portals]
        route = [(a + x, b + x, top) for a, b, top in s.route]
        if s.alt and legs:
            alt = [(v[0], v[1], v[2] + x, v[3] + x, *v[4:]) if v[0] == "ride" else (v[0] + x, v[1] + x, v[2])
                   for v in s.alt]
            alt[0] = (legs[-1][3], alt[0][1], alt[0][2])
            alts[i] = legs_of([(legs[-1][3], legs[-1][3], legs[-1][4]), *alt], i, movers)[1:]
        if legs:  # carry on from where the last segment's route ended
            route[0] = (legs[-1][3], route[0][1], route[0][2])
            legs += legs_of([(legs[-1][3], legs[-1][3], legs[-1][4]), *route], i)[1:]
        else:
            legs += legs_of(route, i)
        course["segs"].append(x)
        course["names"].append(s.name)
        risks.append(s.risk * (0.6 + 0.6 * level) if 0 < i <= len(makers) else 0)
        if i % 2 and i <= len(makers):  # every other obstacle starts with an item box
            course["boxes"].append([x + 90, -30])
        x += s.w
    course["finish"] = x - 400
    course["length"] = x
    return course, legs, risks, alts
