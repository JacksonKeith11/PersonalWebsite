"""Where a boss hit's shape is and whether it touches a hero: the Python twin of js/moves.js's placeHit
and touches. The game itself checks hits in the browser; this is for the test bots and the balance
sim (tools/kingfall-sim.py). tools/kingfall-parity.mjs checks the two agree."""

import math

from .content.moves import aim_at

D2R = math.pi / 180


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def place_hit(move, h, t, lead=0.0):
    """move: a fight.Move (pos(now) works in server time, so use move_pos). Returns a dict or None."""
    if t < h["t0"] - lead or t > h["t1"]: return None
    k = h["k"]
    pos = lambda tt: _pos(move, tt)
    if k in ("proj", "ring"):
        bx, by = pos(h["t0"]); a = aim_at(move.aims, h["t0"])
        ox = bx + math.cos(a) * h.get("x", 0) - math.sin(a) * h.get("y", 0)
        oy = by + math.sin(a) * h.get("x", 0) + math.cos(a) * h.get("y", 0)
        dt = max(0.0, t - h["t0"])
        if k == "proj":
            pa = a + h.get("a", 0) * D2R
            return {"k": k, "cx": ox + math.cos(pa) * h["v"] * dt, "cy": oy + math.sin(pa) * h["v"] * dt, "a": pa, "r": h["r"], "live": t >= h["t0"]}
        return {"k": k, "cx": ox, "cy": oy, "a": a, "r": h["r0"] + h["v"] * dt, "th": h["th"], "gaps": h.get("gaps", []), "live": t >= h["t0"]}
    tt = max(t, h["t0"])
    bx, by = pos(tt); a = aim_at(move.aims, tt)
    if k == "circle":
        return {"k": k, "cx": bx + math.cos(a) * h["x"] - math.sin(a) * h["y"], "cy": by + math.sin(a) * h["x"] + math.cos(a) * h["y"],
                "a": a, "r": h["r"], "live": t >= h["t0"]}
    return {**h, "cx": bx, "cy": by, "a": a, "live": t >= h["t0"]}


def _pos(move, t):
    return move.pos(move.start + t)


def touches(s, px, py, pr):
    dx, dy = px - s["cx"], py - s["cy"]
    d = math.hypot(dx, dy)
    k = s["k"]
    if k in ("circle", "proj"): return d < s["r"] + pr
    if k == "arc":
        if d > s["r"] + pr: return False
        if d < pr + 6: return True
        rel = wrap(math.atan2(dy, dx) - s["a"]) / D2R
        slack = math.asin(min(1, pr / d)) / D2R
        return s["a0"] - slack <= rel <= s["a1"] + slack
    if k == "rect":
        fx = math.cos(s["a"]) * dx + math.sin(s["a"]) * dy
        fy = -math.sin(s["a"]) * dx + math.cos(s["a"]) * dy
        return s["x0"] - pr <= fx <= s["x1"] + pr and abs(fy) <= s["w"] + pr
    if k == "ring":
        if abs(d - s["r"]) > s["th"] / 2 + pr: return False
        rel = wrap(math.atan2(dy, dx) - s["a"]) / D2R
        return not any(g0 <= rel <= g1 for g0, g1 in s.get("gaps", []))
    return False


def place_attack(shape, x, y, a):
    if shape["k"] == "circle":
        return {"k": "circle", "cx": x + math.cos(a) * shape["x"] - math.sin(a) * shape.get("y", 0),
                "cy": y + math.sin(a) * shape["x"] + math.cos(a) * shape.get("y", 0), "r": shape["r"], "a": a}
    return {**shape, "cx": x, "cy": y, "a": a}
