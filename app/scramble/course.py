"""Scramble's courses: a start, a run of obstacle segments picked at random, and a finish.

Everything is in pixels with y pointing down; the ground's surface is y = 0 and every segment
starts and ends on it, so any segment can follow any other. A player is a 28 x 40 box that runs at
RUN px/s and jumps about 144 high and 228 far (the physics is the browser's: js/physics.js).
`tools/scramble-check.mjs` proves every segment can be got through by searching the physics.

A built course is plain data for the browser:
    plats   [x, top, w, h]                       solid blocks
    spikes  [x, top, w]                          deadly, standing on a surface at `top`
    saws    [x, y, r, dx, dy, period, phase]     deadly circles, swinging dx/dy either side of x, y
    movers  [x, top, w, h, dx, dy, period, phase] solid platforms that swing the same way
    pads    [x, top, w]                          springs
    segs    [x, ...]                             where each segment starts (the checkpoints)
plus, for the server's bots only, `legs`: the way through as runs and jumps (see `legs_of`).
"""

import math
import random

RUN = 300  # px/s; the same number as js/physics.js
DEEP = 600  # how far down a ground block goes (past the bottom of the screen)
SPIKE_H = 18


class Seg:
    """One segment being built, in its own coordinates (x from 0)."""

    def __init__(self, name, risk):
        self.name, self.risk = name, risk
        self.plats, self.spikes, self.saws, self.movers, self.pads = [], [], [], [], []
        self.route = []  # (x0, x1, top): the surfaces a bot crosses, in order
        self.w = 0

    def ground(self, x, w, top=0, h=DEEP, spikes=()):
        """A block to run across. `spikes` are (x, w) patches on it; the bots' route hops them."""
        self.plats.append([x, top, w, h])
        at = x
        for sx, sw in spikes:
            self.spikes.append([sx, top, sw])
            self.route.append((at, sx - 26, top))
            at = sx + sw + 26
        self.route.append((at, x + w, top))
        self.w = max(self.w, x + w)
        return x + w

    def mover(self, x, top, w, dx, dy, period, phase=0.0):
        self.movers.append([x, top, w, 22, dx, dy, period, phase])
        self.route.append((x + w * 0.3, x + w * 0.7, top))
        return x + w

    def saw(self, x, y, r, dx, dy, period, phase=0.0):
        self.saws.append([x, y, r, dx, dy, period, phase])

    def pad(self, x, top=0, w=56):
        self.pads.append([x, top, w])


def seg_start(r, d):
    s = Seg("start", 0)
    s.ground(0, 520)
    return s


def seg_finish(r, d):
    s = Seg("finish", 0)
    s.ground(0, 700)
    return s


def seg_gaps(r, d):
    s = Seg("gaps", 0.5)
    x, top = s.ground(0, 170), 0
    for _ in range(r.choice([3, 4])):
        top = max(-80, min(60, top + r.choice([-50, 0, 50])))
        x = s.ground(x + r.randint(110, 150 + int(30 * d)), r.randint(120, 210), top)
    s.ground(x + 120, 170)
    return s


def seg_stairs(r, d):
    s = Seg("stairs", 0.4)
    x, top = s.ground(0, 200), 0
    for _ in range(4):
        top -= 80
        x = s.ground(x + r.randint(60, 90), 110, top, h=30)
    x = s.ground(x + 70, 200, top, h=30)
    s.ground(x + 90, 200)
    return s


def seg_spikes(r, d):
    s = Seg("spikes", 0.6)
    spikes = [(260 + i * 290 + r.randint(-40, 40), r.randint(50, 80 + int(20 * d))) for i in range(3)]
    s.ground(0, 1120, spikes=spikes)
    return s


def seg_saws(r, d):
    s = Seg("saws", 0.8)
    s.ground(0, 1000)
    for x in ([300, 560, 820] if d > 0.5 else [330, 690]):
        s.saw(x, -112, 28, 0, 88, r.uniform(1.7, 2.3), r.uniform(0, 6.28))
    return s


def seg_ferry(r, d):
    s = Seg("ferry", 0.7)
    s.ground(0, 180)
    s.mover(355, 0, 110, 130, 0, r.uniform(3.0, 3.6), r.uniform(0, 6.28))
    s.ground(640, 180)
    return s


def seg_lift(r, d):
    s = Seg("lift", 0.6)
    s.ground(0, 200)
    s.mover(230, -130, 110, 0, 130, r.uniform(3.2, 3.8), r.uniform(0, 6.28))
    s.ground(370, 260, -250, h=30)
    s.ground(700, 200)
    return s


def seg_wall(r, d):
    s = Seg("wall", 0.5)
    s.plats.append([0, 0, 900, DEEP])
    s.plats.append([380, -260, 80, 260])
    s.pad(300)
    s.route += [(0, 328, 0), (385, 455, -260)]
    if d > 0.4:
        s.spikes.append([580, 0, 60])
        s.route += [(480, 554, 0), (666, 900, 0)]
    else:
        s.route.append((480, 900, 0))
    s.w = 900
    return s


def seg_pillars(r, d):
    s = Seg("pillars", 0.8)
    x, top = s.ground(0, 160), 0
    for _ in range(5):
        top = max(-80, min(60, top + r.choice([-60, -30, 30, 60])))
        x = s.ground(x + r.randint(105, 135), 58, top)
    s.ground(x + 110, 160)
    return s


def seg_bridge(r, d):
    s = Seg("bridge", 0.8)
    x = s.ground(0, 160)
    x = s.ground(x + 130, 440, -30, h=30)
    s.saw(x - 220, -52, 26, 150, 0, r.uniform(2.2, 2.8), r.uniform(0, 6.28))
    s.ground(x + 130, 160)
    return s


def seg_twins(r, d):
    s = Seg("twins", 0.9)
    s.ground(0, 180)
    period, phase = r.uniform(2.6, 3.2), r.uniform(0, 6.28)
    s.mover(250, -40, 100, 0, 90, period, phase)
    s.mover(440, -40, 100, 0, 90, period, phase + math.pi)
    s.ground(620, 180)
    return s


def seg_springs(r, d):
    s = Seg("springs", 1.0)
    s.ground(0, 200)
    s.pad(132, 0, 60)
    s.ground(460, 110)
    s.pad(485, 0, 60)
    s.ground(830, 110)
    s.pad(855, 0, 60)
    s.ground(1200, 200)
    return s


def seg_stones(r, d):
    s = Seg("stones", 0.9)
    x, top = s.ground(0, 160), 0
    for i in range(6):
        top = -30 if i % 2 else 10
        x = s.ground(x + r.randint(90, 120), 64, top, h=24)
    s.ground(x + 100, 160)
    return s


def seg_hurdles(r, d):
    s = Seg("hurdles", 0.7)
    s.plats.append([0, 0, 1040, DEEP])
    at = 0
    for x in (260, 520, 780):
        x += r.randint(-30, 30)
        s.plats.append([x, -70, 40, 70])
        s.spikes.append([x + 40, 0, 56])
        s.route += [(at, x - 30, 0), (x + 4, x + 36, -70)]
        at = x + 40 + 56 + 26
    s.route.append((at, 1040, 0))
    s.w = 1040
    return s


SEGMENTS = [seg_gaps, seg_stairs, seg_spikes, seg_saws, seg_ferry, seg_lift, seg_wall, seg_pillars,
            seg_bridge, seg_twins, seg_springs, seg_stones, seg_hurdles]


def legs_of(route, seg):
    """A route as legs for a bot: ("run" | "jump", x0, y0, x1, y1, seconds, arc height, segment)."""
    legs = []
    for i, (x0, x1, top) in enumerate(route):
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
    """A course of `n` obstacle segments (or exactly `makers`), harder towards the end (or all at
    difficulty `d`, 0 to 1)."""
    r = random.Random(seed)
    if makers is None:
        pool = r.sample(SEGMENTS, len(SEGMENTS))
        makers = [pool[i % len(pool)] for i in range(n)]
    course = {"plats": [], "spikes": [], "saws": [], "movers": [], "pads": [], "segs": [], "names": []}
    legs, risks, x = [], [], 0
    for i, make in enumerate([seg_start, *makers, seg_finish]):
        s = make(r, i / (len(makers) + 1) if d is None else d)
        for key in ("plats", "spikes", "saws", "movers", "pads"):
            course[key] += [[v[0] + x, *v[1:]] for v in getattr(s, key)]
        route = [(a + x, b + x, top) for a, b, top in s.route]
        if legs:  # carry on from where the last segment's route ended
            route[0] = (legs[-1][3], route[0][1], route[0][2])
            legs += legs_of([(legs[-1][3], legs[-1][3], legs[-1][4]), *route], i)[1:]
        else:
            legs += legs_of(route, i)
        course["segs"].append(x)
        course["names"].append(s.name)
        risks.append(s.risk)
        x += s.w
    course["finish"] = x - 400
    course["length"] = x
    return course, legs, risks
