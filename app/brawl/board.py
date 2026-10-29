"""Board Brawl's board, Haunted Hollow: a loop around a graveyard, with paths through the middle.

Spaces sit on a 1000 x 640 plane; the browser scales it to fit and draws the scenery. Each space
has a kind, the spaces you step to next and the ones you step back to (for walking backwards).

The loop runs clockwise. Two paths cross the middle and meet at the Crossroads, the centre
space: one from the top of the loop down to the bottom, one from the right side over to the left.
So there are forks at the top, on the right and at the Crossroads.
"""

import math
from collections import deque

W, H = 1000, 640
NAME = "Haunted Hollow"

KINDS = {"B": "blue", "R": "red", "?": "event", "$": "shop", "I": "item", "D": "duel", "P": "portal"}

# Read clockwise from just right of the top-left corner.
LOOP = "BBIB?BRB$BDBB?BIRBPB?BB$BRIBD?BP"
DOWN_TOP = "R?"  # top of the loop down to the Crossroads
DOWN_BOTTOM = "RI"  # Crossroads down to the bottom of the loop
ACROSS_RIGHT = "BRDR"  # right side of the loop to the Crossroads
ACROSS_LEFT = "R$?R"  # Crossroads to the left side
CROSSROADS = "?"


def _rounded_rect(x0, y0, x1, y1, r, n):
    """n points evenly spaced along a rounded rectangle, clockwise from the top-left corner's end."""
    w, h = x1 - x0 - 2 * r, y1 - y0 - 2 * r
    arc = math.pi * r / 2
    segs = [("line", w), ("arc", arc), ("line", h), ("arc", arc)] * 2
    total = sum(s[1] for s in segs)
    corners = [(x1 - r, y0 + r), (x1 - r, y1 - r), (x0 + r, y1 - r), (x0 + r, y0 + r)]
    starts = [(x0 + r, y0), (x1, y0 + r), (x1 - r, y1), (x0, y1 - r)]
    dirs = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    pts = []
    for i in range(n):
        d = total * i / n
        for k, (kind, length) in enumerate(segs):
            if d <= length or k == len(segs) - 1:
                side = k // 2
                if kind == "line":
                    sx, sy = starts[side]
                    dx, dy = dirs[side]
                    pts.append((sx + dx * d, sy + dy * d))
                else:
                    cx, cy = corners[side]
                    a = -math.pi / 2 + side * math.pi / 2 + (d / length) * math.pi / 2
                    pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                break
            d -= length
    return pts


def build():
    spaces = []

    def add(x, y, k, **extra):
        s = {"id": len(spaces), "x": round(x), "y": round(y), "kind": KINDS[k], "next": [], **extra}
        spaces.append(s)
        return s

    pts = _rounded_rect(80, 66, 920, 574, 96, len(LOOP))
    loop = [add(x, y, k) for (x, y), k in zip(pts, LOOP)]
    for i, s in enumerate(loop):
        s["next"].append(loop[(i + 1) % len(loop)]["id"])

    def nearest(pred, x, y):
        return min((s for s in loop if pred(s)), key=lambda s: math.hypot(s["x"] - x, s["y"] - y))

    top = nearest(lambda s: s["y"] < 100, W / 2, 0)
    bottom = nearest(lambda s: s["y"] > H - 100, W / 2, H)
    right = nearest(lambda s: s["x"] > W - 100, W, H / 2)
    left = nearest(lambda s: s["x"] < 100, 0, H / 2)
    cross = add(W / 2, H / 2, CROSSROADS, middle=True, label="Crossroads")

    def path(a, b, kinds):
        prev = a
        for j, k in enumerate(kinds):
            f = (j + 1) / (len(kinds) + 1)
            s = add(a["x"] + (b["x"] - a["x"]) * f, a["y"] + (b["y"] - a["y"]) * f, k, middle=True)
            prev["next"].append(s["id"])
            prev = s
        prev["next"].append(b["id"])

    path(top, cross, DOWN_TOP)
    path(cross, bottom, DOWN_BOTTOM)
    path(right, cross, ACROSS_RIGHT)
    path(cross, left, ACROSS_LEFT)
    for s in spaces:
        s["prev"] = [t["id"] for t in spaces if s["id"] in t["next"]]
    portals = [s for s in spaces if s["kind"] == "portal"]
    assert len(portals) == 2, "the board needs exactly two portals"
    portals[0]["to"], portals[1]["to"] = portals[1]["id"], portals[0]["id"]
    return spaces, cross["id"]


SPACES, CROSSROADS_ID = build()
START = 0
JUNCTIONS = [s["id"] for s in SPACES if len(s["next"]) > 1]


def payload():
    return {"w": W, "h": H, "name": NAME, "spaces": SPACES, "start": START}


def _bfs(src, edges):
    dist = {src: 0}
    queue = deque([src])
    while queue:
        cur = queue.popleft()
        for n in edges(cur):
            if n not in dist:
                dist[n] = dist[cur] + 1
                queue.append(n)
    return dist


def distances_to(target):
    """Steps from every space to `target`, walking forward."""
    return _bfs(target, lambda s: SPACES[s]["prev"])


def distances_from(src):
    """Steps from `src` to every space, walking forward."""
    return _bfs(src, lambda s: SPACES[s]["next"])


def nearby(src, n):
    """Spaces within n steps of `src`, forwards or backwards."""
    return _bfs(src, lambda s: SPACES[s]["next"] + SPACES[s]["prev"])


def within(src, n):
    return {s for s, d in nearby(src, n).items() if d <= n}
