"""Building blocks for boss moves, and the one bit of move maths the server needs: where the boss is.

A move is a timeline (seconds from its start) of:
  locks   times the boss (re)aims at its target; motion and hits after a lock use that aim
  motion  (t0, t1, dist) steps along the aim; dist may be ("target", extra, lo, hi): the distance to
          the target plus extra, clamped, worked out at the last lock before t0
  hits    shapes that hurt during [t0, t1] (see the builders below)
  anim    keyframes for the rig: (t, pose)
Shapes are in the aim's frame: x forward, y to the right. The browser has the same maths in
js/moves.js, and checks the shapes against its own players (the dodger decides).
"""

import math


DMG = [1.0]  # set by a boss file before building its moves (see corvin.py)


def _hit(kind, t0, t1, dmg, extra, mark, **shape):
    h = {"k": kind, "t0": t0, "t1": t1, "dmg": round(dmg * DMG[0]), **shape}
    if extra: h.update(extra)
    if mark is not None: h["mark"] = mark
    return h


def arc(t0, t1, r, a0, a1, dmg, extra=None, mark=None):
    """A swing: the sector of radius r between a0 and a1 degrees either side of the aim."""
    return _hit("arc", t0, t1, dmg, extra, mark, r=r, a0=a0, a1=a1)


def circle(t0, t1, r, side, fwd, dmg, extra=None, mark=None):
    return _hit("circle", t0, t1, dmg, extra, mark, r=r, x=fwd, y=side)


def rect(t0, t1, x0, x1, w, dmg, extra=None, mark=None):
    """A thrust or a slam: from x0 to x1 ahead of the boss, w either side of the aim line."""
    return _hit("rect", t0, t1, dmg, extra, mark, x0=x0, x1=x1, w=w)


def ring(t0, t1, r0, v, th, dmg, extra=None, at=0, gaps=None, mark=None):
    """A shockwave: a ring th thick that grows from r0 at v px/s, centred `at` ahead of where the
    boss stood at t0. Roll through it or outrun it. gaps: [(a0, a1)] degrees it doesn't cover."""
    return _hit("ring", t0, t1, dmg, extra, mark, r0=r0, v=v, th=th, x=at, gaps=gaps or [])


def proj(t, side, fwd, a, v, r, life, dmg, extra=None):
    """A projectile fired at t from (fwd, side), a degrees off the aim, flying v px/s for life s."""
    return _hit("proj", t, t + life, dmg, extra, None, x=fwd, y=side, a=a, v=v, r=r)


def pose(**kw):
    """Rig keyframe: part angles in degrees (arm_f, arm_b, weapon, shield, torso, head, leg_f, leg_b,
    cape), lean/dy (body offset), front=1 (shield in front), run=1 (legs cycle)."""
    return kw


def ease(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) * (1 - u)


def aim_at(aims, t):
    """aims: [(t, angle)] sorted; the aim in force at time t."""
    a = aims[0][1]
    for at, ang in aims:
        if at <= t: a = ang
    return a


def offset(move, aims, dists, t):
    """How far the boss has moved from the move's origin by time t: (dx, dy)."""
    dx = dy = 0.0
    for (t0, t1, _), d in zip(move["motion"], dists):
        if t <= t0: continue
        a = aim_at(aims, t0)
        u = ease((t - t0) / max(1e-6, t1 - t0))
        dx += math.cos(a) * d * u
        dy += math.sin(a) * d * u
    return dx, dy


def resolve(move, lock_t, dist_to_target, dists):
    """Work out the target-relative step lengths for motion steps after the lock at lock_t (and
    before the next lock). Returns the updated list."""
    out = list(dists)
    later = [t for t in move.get("locks", [0]) if t > lock_t]
    until = later[0] if later else 1e9
    for i, (t0, _, d) in enumerate(move["motion"]):
        if isinstance(d, (int, float)):
            out[i] = float(d)
        elif lock_t <= t0 < until:
            _, extra, lo, hi = d
            out[i] = float(min(hi, max(lo, dist_to_target + extra)))
    return out
