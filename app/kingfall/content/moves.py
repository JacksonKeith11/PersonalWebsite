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


def _hit(kind, t0, t1, dmg, extra, mark, rot=0, tx=False, **shape):
    h = {"k": kind, "t0": t0, "t1": t1, "dmg": round(dmg * DMG[0]), **shape}
    if rot: h["rot"] = rot   # degrees off the aim (beams and breath that sweep)
    if tx: h["tx"] = True    # x counts from the move's reach (the target) instead of the boss
    if extra: h.update(extra)
    if mark is not None: h["mark"] = mark
    return h


def arc(t0, t1, r, a0, a1, dmg, extra=None, mark=None, rot=0, tx=False):
    """A swing: the sector of radius r between a0 and a1 degrees either side of the aim."""
    return _hit("arc", t0, t1, dmg, extra, mark, rot, tx, r=r, a0=a0, a1=a1)


def circle(t0, t1, r, side, fwd, dmg, extra=None, mark=None, rot=0, tx=False):
    return _hit("circle", t0, t1, dmg, extra, mark, rot, tx, r=r, x=fwd, y=side)


def rect(t0, t1, x0, x1, w, dmg, extra=None, mark=None, rot=0, tx=False):
    """A thrust or a slam: from x0 to x1 ahead of the boss, w either side of the aim line."""
    return _hit("rect", t0, t1, dmg, extra, mark, rot, tx, x0=x0, x1=x1, w=w)


def ring(t0, t1, r0, v, th, dmg, extra=None, at=0, gaps=None, mark=None, rot=0, tx=False):
    """A shockwave: a ring th thick that grows from r0 at v px/s, centred `at` ahead of where the
    boss stood at t0. Roll through it or outrun it. gaps: [(a0, a1)] degrees it doesn't cover."""
    return _hit("ring", t0, t1, dmg, extra, mark, rot, tx, r0=r0, v=v, th=th, x=at, gaps=gaps or [])


def proj(t, side, fwd, a, v, r, life, dmg, extra=None, rot=0, tx=False):
    """A projectile fired at t from (fwd, side), a degrees off the aim, flying v px/s for life s."""
    return _hit("proj", t, t + life, dmg, extra, None, rot, tx, x=fwd, y=side, a=a, v=v, r=r)


def zone(t0, life, r, side, fwd, dmg, pool, tick=0.6, extra=None, mark=None, rot=0, tx=False):
    """A lingering hazard (a pool of poison, a patch of fire) placed at t0 where the boss stood, for
    `life` seconds; it hurts whoever stands in it every `tick` seconds."""
    return _hit("zone", t0, t0 + life, dmg, extra, mark, rot, tx, r=r, x=fwd, y=side, pool=pool, tick=tick)


def spawn(t, kind, n=1, dist=30, spread=0):
    """Call adds at time t: n of `kind` (the boss's 'adds' table), dist ahead, fanned by spread degrees."""
    return {"k": "spawn", "t0": t, "t1": t, "dmg": 0, "kind": kind, "n": n, "x": dist, "spread": spread}


def room(t0, dmg=60, life=0.5, mark=None, **extra):
    """A blast across the whole arena (a signature move). It can't be blocked and lasts longer than a
    roll's invulnerability, so it must be answered the way its move says: `safe=tag` spares a hero
    standing in one of the cast's spots with that tag (tag "v": the spot the cast's variant picked),
    `cover=tag` one standing behind such a spot as seen from the boss, `still=1` one who isn't moving.
    Its damage is written as it lands (not scaled by the boss's DMG): about 60% of a hero's health."""
    h = {"k": "circle", "t0": t0, "t1": t0 + life, "dmg": dmg, "r": 1400, "x": 0, "y": 0, "room": 1, "unblock": 1, **extra}
    if mark is not None: h["mark"] = mark
    return h


def lane(t0, t1, ox, oy, deg, length, w, dmg, mark=None, **extra):
    """A strip of the arena itself: from (ox, oy) in arena coordinates, `deg` degrees, `length` long and
    w either side. `abs` hits ignore where the boss stands and aims."""
    h = {"k": "rect", "t0": t0, "t1": t1, "dmg": round(dmg * DMG[0]), "x0": 0, "x1": length, "w": w, "abs": [ox, oy], "rot": deg, **extra}
    if mark is not None: h["mark"] = mark
    return h


def delay(move, d, trim=0.0):
    """Lengthen a move's wind-up by d seconds (everything after its start moves later) and take
    `trim` off its recovery: for openers that struck too soon to read."""
    sh = lambda t: t + d if t > 0 else t
    move["locks"] = [sh(t) for t in move.get("locks", [0.0])]
    move["motion"] = [(t0 + d, t1 + d, dist) for t0, t1, dist in move["motion"]]
    for h in move["hits"]: h["t0"] += d; h["t1"] += d
    for h in move["hits"]: h["t0"], h["t1"] = round(h["t0"], 3), round(h["t1"], 3)
    move["anim"] = [(sh(t), p) for t, p in move["anim"][:-1]] + [(move["anim"][-1][0] + d - trim, move["anim"][-1][1])]
    for k in ("air", "under", "guard"):
        if k in move: move[k] = (move[k][0] + d, move[k][1] + d)
    move["dur"] = round(move["dur"] + d - trim, 3)
    return move


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


def n_dists(move):
    """How many numbers a move's resolved distances hold: one per motion step, then its reach."""
    return len(move["motion"]) + (1 if move.get("reach") else 0)


def resolve(move, lock_t, dist_to_target, dists):
    """Work out the target-relative step lengths for motion steps after the lock at lock_t (and
    before the next lock), and the move's reach (how far ahead hits marked tx=True land: lobbed
    flasks, pillars under the target). Returns the updated list."""
    out = list(dists) + [0.0] * (n_dists(move) - len(dists))
    if move.get("reach"):
        _, extra, lo, hi = move["reach"]
        out[len(move["motion"])] = float(min(hi, max(lo, dist_to_target + extra)))
    later = [t for t in move.get("locks", [0]) if t > lock_t]
    until = later[0] if later else 1e9
    for i, (t0, _, d) in enumerate(move["motion"]):
        if isinstance(d, (int, float)):
            out[i] = float(d)
        elif lock_t <= t0 < until:
            _, extra, lo, hi = d
            out[i] = float(min(hi, max(lo, dist_to_target + extra)))
    return out
