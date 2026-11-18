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
    crumbles [x, top, w]                         blocks that fall half a second after you land on one
    belts   [x, top, w, v]                       conveyor blocks (24 high) carrying whoever stands on them at v px/s
    blinks  [x, top, w, period, phase]           platforms (22 high) there for the first half of each period
                                                 (phase is a fraction of the period)
    winds   [x, top, w, h, v, period, phase]     zones that push whoever is in them at v px/s while
                                                 sin(2 pi t / period + phase) > 0
    lavas   [x0, x1, trigger, base, rate, cap]   rising lava between x0 and x1: its surface is at `base`
                                                 until a racer passes `trigger`, then rises at `rate` px/s
                                                 to `cap` (each racer has their own, as with crumbles)
    boxes   [x, y]                               item boxes, at the start of every other obstacle
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
        self.plats, self.spikes, self.saws, self.movers, self.pads, self.crumbles = [], [], [], [], [], []
        self.belts, self.blinks, self.winds, self.lavas = [], [], [], []
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


def lerp(d, easy, hard):
    return easy + (hard - easy) * d


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
    n = 2 if d < 0.4 else 3 if d < 0.75 else 4
    w = 280 + n * 240
    s.ground(0, w)
    for i in range(n):
        s.saw(220 + i * 240, -112, 28, 0, lerp(d, 88, 100), r.uniform(1.7, 2.3) * lerp(d, 1, 0.7), r.uniform(0, 6.28))
    return s


def seg_ferry(r, d):
    s = Seg("ferry", 0.7)
    s.ground(0, 180)
    s.mover(355, 0, int(lerp(d, 110, 76)), 130, 0, r.uniform(3.0, 3.6) * lerp(d, 1, 0.7), r.uniform(0, 6.28))
    if d > 0.6:  # a saw sweeping the far half of the crossing
        s.saw(470, -150, 26, 0, 60, lerp(d, 2.6, 2.0), r.uniform(0, 6.28))
    s.ground(640, 180)
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
    for _ in range(5 + (d > 0.6)):
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
    return s


def seg_stones(r, d):
    s = Seg("stones", 0.9)
    x, top = s.ground(0, 160), 0
    w = int(lerp(d, 64, 44))
    for i in range(6 + (d > 0.6)):
        top = -30 if i % 2 else 10
        x = s.ground(x + r.randint(int(lerp(d, 90, 115)), int(lerp(d, 120, 145))), w, top, h=24)
    s.ground(x + 100, 160)
    return s


def seg_hurdles(r, d):
    s = Seg("hurdles", 0.7)
    sw = int(lerp(d, 56, 86))
    n = 3 + (d > 0.6)
    s.plats.append([0, 0, 260 * n + 260, DEEP])
    at = 0
    for i in range(n):
        x = 260 * (i + 1) + r.randint(-30, 30)
        s.plats.append([x, -70, 40, 70])
        s.spikes.append([x + 40, 0, sw])
        s.route += [(at, x - 30, 0), (x + 4, x + 36, -70)]
        at = x + 40 + sw + 26
    s.route.append((at, 260 * n + 260, 0))
    s.w = 260 * n + 260
    return s


def seg_crumble(r, d):
    """Blocks over a pit that fall away half a second after you land on one."""
    s = Seg("crumble", 1.0)
    x, top = s.ground(0, 170), 0
    for _ in range(4 + (d > 0.6)):
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
    for i in range(3 + (d > 0.6)):
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
    for i in range(5 + (d > 0.6)):
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
    for i in range(3 + (d > 0.6)):
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
        if d > 0.55 and r.random() < 0.5 and x < 760:  # a saw over the next gap
            s.saw(x + 60, -70, 24, 0, 40, r.uniform(1.6, 2.2), r.uniform(0, 6.28))
    s.movers.append([905, floor // 2, 90, 22, 0, floor // 2, round(r.uniform(2.8, 3.4), 3), round(r.uniform(0, 6.28), 3)])
    s.ground(1000, 200)
    return s


SEGMENTS = [seg_gaps, seg_stairs, seg_spikes, seg_saws, seg_ferry, seg_lift, seg_wall, seg_pillars,
            seg_bridge, seg_twins, seg_springs, seg_stones, seg_hurdles, seg_crumble, seg_tunnel, seg_launch,
            seg_belts, seg_blinks, seg_gusts, seg_lava, seg_fork]
THEMES = ("meadow", "desert", "snow", "dusk", "cave")
D_FIRST = 0.35  # the first obstacle's difficulty; the last is 1


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
    """A course of `n` obstacle segments (or exactly `makers`), from difficulty D_FIRST at the
    first to 1 at the last (or all at difficulty `d`, 0 to 1)."""
    r = random.Random(seed)
    if makers is None:
        pool = r.sample(SEGMENTS, len(SEGMENTS))
        makers = [pool[i % len(pool)] for i in range(n)]
    keys = ("plats", "spikes", "saws", "movers", "pads", "crumbles", "belts", "blinks", "winds")
    course = {k: [] for k in keys}
    course.update({"lavas": [], "boxes": [], "segs": [], "names": []})
    legs, risks, x = [], [], 0
    for i, make in enumerate([seg_start, *makers, seg_finish]):
        if d is not None:
            level = d
        else:
            level = D_FIRST + (1 - D_FIRST) * (i - 1) / max(1, len(makers) - 1)
        s = make(r, min(1.0, max(0.0, level)))
        for key in keys:
            course[key] += [[v[0] + x, *v[1:]] for v in getattr(s, key)]
        course["lavas"] += [[a + x, b + x, trig + x, *rest] for a, b, trig, *rest in s.lavas]
        route = [(a + x, b + x, top) for a, b, top in s.route]
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
    return course, legs, risks
