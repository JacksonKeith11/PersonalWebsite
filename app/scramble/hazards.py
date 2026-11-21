"""Where a course's timed hazards are at any moment, as js/physics.js has them, so bots can see
them coming (and be caught by them): saws, firebars, cannon shots, crushers and jets.

Everything else bots still leave to dice (`risk` in game.py): spikes are hopped on rails, and lava,
boulders, crumbling and blinking blocks and the rest are each racer's own or a matter of footing.
Change how one of these moves in physics.js and it must change here too.
"""

import math

HALF, PH = 14, 40  # a racer's half-width and height (physics.js: PW / 2, PH)
BAR_R = BULLET_R = 9
BUCKET = 256  # px: hazards are filed by the stretches of course they can reach


def slam(u):
    u %= 1
    if u < 0.4:
        return 0.0
    if u < 0.48:
        return ((u - 0.4) / 0.08) ** 2
    if u < 0.65:
        return 1.0
    return 1 - (u - 0.65) / 0.35


def offset(dx, dy, period, phase, kind, t):
    a = 2 * math.pi * t / period + phase
    if kind == 1:
        return dx * math.cos(a), dy * math.sin(a)
    if kind == 2:
        g = dy * math.sin(a)
        return dx * math.sin(g), -dx * (1 - math.cos(g))
    if kind == 3:
        s = slam(a / (2 * math.pi))
        return dx * s, dy * s
    s = math.sin(a)
    return dx * s, dy * s


def touches(x, y, cx, cy, r):
    """A racer standing with feet at x, y touches a circle (physics.js's `touches`)."""
    nx, ny = max(x - HALF, min(cx, x + HALF)), max(y - PH, min(cy, y))
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r


def hits(x, y, bx, by, bw, bh):
    return x + HALF > bx and x - HALF < bx + bw and y > by and y - PH < by + bh


class Hazards:
    def __init__(self, course):
        self.near_x = {}
        for s in course.get("saws", []):
            x, y, r, dx, dy, period, phase, kind = (list(s) + [0])[:8]
            reach = abs(dx) + r
            self.file(x - reach, x + reach, ("saw", x, y, r, dx, dy, period, phase, kind))
        for b in course.get("bars", []):
            x, y, length, n, period, phase, *arms = b
            self.file(x - length - BAR_R, x + length + BAR_R, ("bar", x, y, length, n, period, phase, arms[0] if arms else 1))
        for c in course.get("cannons", []):
            x, y, vx, vy, period, phase, reach = c
            v = math.hypot(vx, vy)
            end = x + vx * reach / v
            self.file(min(x, end) - BULLET_R, max(x, end) + BULLET_R, ("cannon", x, y, vx, vy, period, phase, reach / v))
        for m in course.get("crushers", []):
            x, top, w, h, dx, dy, period, phase, *kind = m
            self.file(x - abs(dx), x + w + abs(dx), ("crusher", x, top, w, h, dx, dy, period, phase, kind[0] if kind else 3))
        for j in course.get("jets", []):
            x, top, w, h, period, phase, duty, *_ = j
            self.file(x, x + w, ("jet", x, top, w, h, period, phase, duty))

    def file(self, x0, x1, h):
        for k in range(int(x0 - HALF) // BUCKET, int(x1 + HALF) // BUCKET + 1):
            self.near_x.setdefault(k, []).append(h)

    def near(self, x):
        return self.near_x.get(int(x) // BUCKET, ())

    def hit(self, x, y, t, pad=0.0):
        """Would a racer with feet at x, y be caught at race time t? `pad` widens (or, below 0,
        narrows) every hazard by that many px: bots looking ahead give them room."""
        for h in self.near(x):
            kind = h[0]
            if kind == "saw":
                _, hx, hy, r, dx, dy, period, phase, k = h
                ox, oy = offset(dx, dy, period, phase, k, t)
                if touches(x, y, hx + ox, hy + oy, r - 3 + pad):
                    return True
            elif kind == "bar":
                _, bx, by, length, n, period, phase, arms = h
                for j in range(arms):
                    a = 2 * math.pi * t / period + phase + j * 2 * math.pi / arms
                    ca, sa = math.cos(a), math.sin(a)
                    for i in range(n):
                        d = length if n == 1 else 10 + (length - 10) * i / (n - 1)
                        if touches(x, y, bx + ca * d, by + sa * d, BAR_R - 2 + pad):
                            return True
            elif kind == "cannon":
                _, cx, cy, vx, vy, period, phase, life = h
                k = math.floor(t / period - phase)
                while True:
                    age = t - (k + phase) * period
                    if age > life:
                        break
                    if age >= 0 and touches(x, y, cx + vx * age, cy + vy * age, BULLET_R - 2 + pad):
                        return True
                    k -= 1
            elif kind == "crusher":
                _, cx, top, w, hh, dx, dy, period, phase, k = h
                ox, oy = offset(dx, dy, period, phase, k, t)
                if hits(x, y, cx + ox + 3 - pad, top + oy + 3 - pad, w - 6 + 2 * pad, hh - 6 + 2 * pad):
                    return True
            else:  # a jet, while it's out
                _, jx, top, w, hh, period, phase, duty = h
                if (t / period + phase) % 1 < duty and hits(x, y, jx + 4 - pad, top + 4 - pad, w - 8 + 2 * pad, hh - 8 + 2 * pad):
                    return True
        return False
