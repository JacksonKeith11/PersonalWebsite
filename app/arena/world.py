"""Frag Arena's map, its geometry, and the movement physics.

The browser runs the same movement for its own player (`js/physics.js`); keep the two in step.
The server only moves bots with it. Coordinates are metres, y up, a player's position is the
centre of their feet.
"""

import math

# Quake 3's movement, scaled from its units at 32 to the metre. Sent to the client in `welcome`.
PHYS = {
    "gravity": 25.0,
    "speed": 10.0,  # top run speed
    "accel": 10.0,
    "air_accel": 1.5,  # Q3 is 1.0; a little more air control for people new to strafe-jumping
    "friction": 6.0,
    "stop_speed": 3.1,
    "jump": 8.4,
    "step": 0.5,  # highest ledge you walk up without jumping
    "radius": 0.4,
    "height": 1.8,
    "eye": 1.6,
}

R = PHYS["radius"]
H = PHYS["height"]
STEP = PHYS["step"]
EPS = 1e-5

# Boxes are (x0, y0, z0, x1, y1, z1); the map also keeps a material name and whether bots walk on top.
BOXES: list[tuple] = []
MATS: list[str] = []
WALKABLE: list[tuple] = []  # the boxes whose tops get waypoints
PADS: list[dict] = []  # jump pads: a disc on the floor that launches you at a target
PICKUPS: list[dict] = []
SPAWNS: list[tuple] = []  # (x, y, z, yaw)
LINKS: list[tuple] = []  # hand-made waypoint links: (a, b, one_way)


def box(x0, y0, z0, x1, y1, z1, mat, walk=False):
    b = (min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1))
    BOXES.append(b)
    MATS.append(mat)
    if walk:
        WALKABLE.append(b)
    return b


def stairs(x0, x1, z_start, direction, top, rise, run, mat="stone"):
    """Steps falling away from a ledge's edge at z_start, along z in `direction` (+1/-1)."""
    n = round(top / rise)
    for k in range(n - 1):
        h = top - rise * (k + 1)
        za = z_start + direction * run * k
        box(x0, 0, za, x1, h, za + direction * run, mat, walk=True)
    end = z_start + direction * run * (n - 1)
    mid = (x0 + x1) / 2
    LINKS.append(((mid, 0.0, end + direction * 0.8), (mid, top, z_start - direction * 0.8), False))


def jump_pad(x, z, tx, ty, tz, apex=3.5):
    """A pad at (x, 0, z) that throws you onto (tx, ty, tz), peaking `apex` metres above the target."""
    g = PHYS["gravity"]
    peak = ty + apex
    vy = math.sqrt(2 * g * peak)
    t = vy / g + math.sqrt(2 * apex / g)
    vx, vz = (tx - x) / t, (tz - z) / t
    PADS.append({"x": x, "y": 0.0, "z": z, "r": 1.0, "v": (vx, vy, vz)})
    LINKS.append(((x, 0.0, z), (tx, ty, tz), True))


def pickup(kind, x, y, z):
    PICKUPS.append({"kind": kind, "x": x, "y": y, "z": z})


def spawn(x, y, z):
    SPAWNS.append((x, y, z, math.atan2(x, z)))  # facing the middle


def build_map():
    # Floor and outer walls. The arena is 60 x 60 inside.
    box(-32, -1, -32, 32, 0, 32, "floor", walk=True)
    box(-32, 0, 30, 32, 14, 32, "wall")
    box(-32, 0, -32, 32, 14, -30, "wall")
    box(30, 0, -30, 32, 14, 30, "wall")
    box(-32, 0, -30, -30, 14, 30, "wall")

    # Central platform with the mega health, stairs north and south.
    box(-5, 0, -5, 5, 3, 5, "metal", walk=True)
    stairs(-2, 2, 5, +1, 3.0, 0.375, 0.6)
    stairs(-2, 2, -5, -1, 3.0, 0.375, 0.6)

    # East and west ledges, each with stairs at one end and a jump pad in front.
    box(22, 0, -16, 30, 4, 16, "stone", walk=True)
    box(-30, 0, -16, -22, 4, 16, "stone", walk=True)
    stairs(24, 30, 16, +1, 4.0, 0.4, 0.6)
    stairs(-30, -24, -16, -1, 4.0, 0.4, 0.6)
    jump_pad(16, 0, 26, 4, 0)
    jump_pad(-16, 0, -26, 4, 0)

    # Pillars and crates for cover.
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(sx * 12 - 1, 0, sz * 12 - 1, sx * 12 + 1, 7, sz * 12 + 1, "pillar")
    box(-1.5, 0, 18, 1.5, 1.5, 21, "crate")
    box(-1.5, 0, -21, 1.5, 1.5, -18, "crate")
    box(14, 0, -24, 16, 1, -22, "crate")
    box(-16, 0, 22, -14, 1, 24, "crate")
    box(14, 0, 22, 16, 1, 24, "crate")
    box(-16, 0, -24, -14, 1, -22, "crate")

    pickup("mega", 0, 3, 0)
    pickup("armor", 27, 4, -8)
    pickup("armor", -27, 4, 8)
    pickup("health", 8, 0, 14)
    pickup("health", -8, 0, -14)
    pickup("health", 18, 0, -8)
    pickup("health", -18, 0, 8)
    pickup("ammo", 0, 0, 25)
    pickup("ammo", 0, 0, -25)
    pickup("ammo", 27, 4, 8)
    pickup("ammo", -27, 4, -8)

    for x, y, z in (
        (20, 0, 26), (-20, 0, -26), (-20, 0, 26), (20, 0, -26),
        (26, 4, -12), (-26, 4, 12), (-8, 0, 13), (8, 0, -13),
    ):
        spawn(x, y, z)


build_map()


def map_payload():
    """What the client needs to draw and collide with the map."""
    return {
        "boxes": [[*b, m] for b, m in zip(BOXES, MATS)],
        "pads": [[p["x"], p["y"], p["z"], p["r"], *p["v"]] for p in PADS],
        "pickups": [[p["kind"], p["x"], p["y"], p["z"]] for p in PICKUPS],
    }


# ---------------------------------------------------------------- geometry


def player_hits(boxes, x, y, z):
    """Boxes overlapping a player standing at (x, y, z)."""
    x0, x1, y1, z0, z1 = x - R, x + R, y + H, z - R, z + R
    return [
        b for b in boxes
        if b[0] < x1 - EPS and b[3] > x0 + EPS and b[1] < y1 - EPS and b[4] > y + EPS
        and b[2] < z1 - EPS and b[5] > z0 + EPS
    ]


def ray_box(ox, oy, oz, dx, dy, dz, b, tmax):
    """Distance along a ray (unit direction) to box b, or None if it misses within tmax."""
    t0, t1 = 0.0, tmax
    for o, d, lo, hi in ((ox, dx, b[0], b[3]), (oy, dy, b[1], b[4]), (oz, dz, b[2], b[5])):
        if abs(d) < 1e-9:
            if o < lo or o > hi:
                return None
            continue
        a, c = (lo - o) / d, (hi - o) / d
        if a > c:
            a, c = c, a
        t0, t1 = max(t0, a), min(t1, c)
        if t0 > t1:
            return None
    return t0


def ray_world(o, d, tmax):
    """Distance to the first map box along a ray, capped at tmax."""
    best = tmax
    for b in BOXES:
        t = ray_box(o[0], o[1], o[2], d[0], d[1], d[2], b, best)
        if t is not None and t < best:
            best = t
    return best


def clear_line(a, b):
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
    if dist < 1e-6:
        return True
    return ray_world(a, (dx / dist, dy / dist, dz / dist), dist) >= dist - 1e-4


def player_box(x, y, z, grow=0.0):
    return (x - R - grow, y - grow, z - R - grow, x + R + grow, y + H + grow, z + R + grow)


def inside_solid(x, y, z):
    return bool(player_hits(BOXES, x, y, z))


# ---------------------------------------------------------------- movement


class Body:
    """A moving player: position, velocity and whether they stand on something."""

    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.pos = [x, y, z]
        self.vel = [0.0, 0.0, 0.0]
        self.ground = False

    def knock(self, vx, vy, vz):
        self.vel[0] += vx
        self.vel[1] += vy
        self.vel[2] += vz
        if self.vel[1] > 0.5:
            self.ground = False


def _move_axis(cands, pos, axis, d):
    """Move along one axis, stopping at the first box. Returns True if something blocked it."""
    if d == 0:
        return False
    pos[axis] += d
    hits = player_hits(cands, *pos)
    if not hits:
        return False
    if axis == 1:
        pos[1] = max(b[4] for b in hits) if d < 0 else min(b[1] for b in hits) - H
    elif d > 0:
        pos[axis] = min(b[axis] for b in hits) - R
    else:
        pos[axis] = max(b[axis + 3] for b in hits) + R
    return True


def _move_flat(cands, pos, dx, dz, ground):
    start = pos[:]
    bx = _move_axis(cands, pos, 0, dx)
    bz = _move_axis(cands, pos, 2, dz)
    if not (bx or bz) or not ground:
        return bx, bz
    # Blocked on the ground: try again a step higher, then settle back down.
    up = [start[0], start[1] + STEP, start[2]]
    if player_hits(cands, *up):
        return bx, bz
    ux = _move_axis(cands, up, 0, dx)
    uz = _move_axis(cands, up, 2, dz)
    _move_axis(cands, up, 1, -STEP)
    if math.hypot(up[0] - start[0], up[2] - start[2]) > math.hypot(pos[0] - start[0], pos[2] - start[2]) + 1e-4:
        pos[:] = up
        return ux, uz
    return bx, bz


def _accelerate(vel, wx, wz, wishspeed, accel, dt):
    current = vel[0] * wx + vel[2] * wz
    add = wishspeed - current
    if add <= 0:
        return
    a = min(accel * dt * wishspeed, add)
    vel[0] += a * wx
    vel[2] += a * wz


def move(body, wx, wz, jump, dt):
    """One physics step. (wx, wz) is the wished direction, length 0..1."""
    p, v = body.pos, body.vel
    wish = math.hypot(wx, wz)
    if wish > 1e-6:
        wx, wz = wx / wish, wz / wish
    wishspeed = PHYS["speed"] * min(wish, 1.0)

    if body.ground and jump:
        v[1] = PHYS["jump"]
        body.ground = False
    if body.ground:
        speed = math.hypot(v[0], v[2])
        if speed > 0:
            drop = max(speed, PHYS["stop_speed"]) * PHYS["friction"] * dt
            scale = max(speed - drop, 0) / speed
            v[0] *= scale
            v[2] *= scale
        _accelerate(v, wx, wz, wishspeed, PHYS["accel"], dt)
    else:
        _accelerate(v, wx, wz, wishspeed, PHYS["air_accel"], dt)
        v[1] -= PHYS["gravity"] * dt

    dx, dy, dz = v[0] * dt, v[1] * dt, v[2] * dt
    reach = abs(dx) + abs(dz) + STEP + 0.1
    lo_y, hi_y = p[1] - STEP - abs(dy) - 0.1, p[1] + H + STEP + abs(dy) + 0.1
    cands = [
        b for b in BOXES
        if b[0] < p[0] + R + reach and b[3] > p[0] - R - reach and b[2] < p[2] + R + reach
        and b[5] > p[2] - R - reach and b[1] < hi_y and b[4] > lo_y
    ]

    bx, bz = _move_flat(cands, p, dx, dz, body.ground)
    if bx:
        v[0] = 0.0
    if bz:
        v[2] = 0.0

    if body.ground:
        # Stay glued to the floor walking down steps; walking off an edge starts a fall.
        probe = p[:]
        if _move_axis(cands, probe, 1, -STEP):
            p[1] = probe[1]
            v[1] = 0.0
        else:
            body.ground = False
    else:
        if _move_axis(cands, p, 1, dy):
            if v[1] < 0:
                body.ground = True
            v[1] = 0.0

    if body.ground:
        for pad in PADS:
            if abs(p[1] - pad["y"]) < 0.05 and math.hypot(p[0] - pad["x"], p[2] - pad["z"]) < pad["r"]:
                v[0], v[1], v[2] = pad["v"]
                body.ground = False
                return "pad"
    return None


# ---------------------------------------------------------------- waypoints for bots

NODES: list[tuple] = []  # (x, y, z)
EDGES: list[list[int]] = []


def _on_walkable(x, y, z, margin=R):
    return any(
        abs(b[4] - y) < 0.05 and b[0] + margin <= x <= b[3] - margin and b[2] + margin <= z <= b[5] - margin
        for b in WALKABLE
    )


def _corridor_clear(a, b):
    """Can a player walk straight from a to b on one level?"""
    dx, dz = b[0] - a[0], b[2] - a[2]
    dist = math.hypot(dx, dz)
    if dist < 1e-6:
        return True
    nx, nz = -dz / dist * R, dx / dist * R
    for off, h in ((0.0, 0.3), (1.0, 0.9), (-1.0, 0.9), (0.0, 1.5)):
        s = (a[0] + nx * off, a[1] + h, a[2] + nz * off)
        e = (b[0] + nx * off, b[1] + h, b[2] + nz * off)
        if not clear_line(s, e):
            return False
    steps = max(1, int(dist / 0.75))
    for i in range(steps + 1):
        f = i / steps
        x, z = a[0] + dx * f, a[2] + dz * f
        if not _on_walkable(x, a[1], z, margin=0.05):
            return False
        # Don't route bots across a jump pad unless the pad is where they're going.
        for p in PADS:
            crosses = abs(p["y"] - a[1]) < 0.05 and math.hypot(x - p["x"], z - p["z"]) < p["r"] + R
            ends_there = min(math.hypot(b[0] - p["x"], b[2] - p["z"]), math.hypot(a[0] - p["x"], a[2] - p["z"])) <= 0.1
            if crosses and not ends_there:
                return False
    return True


def _add_node(x, y, z):
    for i, n in enumerate(NODES):
        if abs(n[0] - x) < 0.3 and abs(n[1] - y) < 0.1 and abs(n[2] - z) < 0.3:
            return i
    NODES.append((x, y, z))
    EDGES.append([])
    return len(NODES) - 1


def build_graph():
    """Waypoints on a 3 m grid over every walkable top, plus the stairs, pads and pickups."""
    if NODES:
        return
    tops = sorted({round(b[4], 3) for b in WALKABLE if b[4] > 0.5 or b[4] == 0})
    for y in tops:
        for i in range(20):
            for k in range(20):
                x, z = -28.5 + 3 * i, -28.5 + 3 * k
                if _on_walkable(x, y, z) and not inside_solid(x, y, z):
                    _add_node(x, y, z)
    for p in PICKUPS:
        _add_node(p["x"], p["y"], p["z"])
    for p in PADS:
        _add_node(p["x"], p["y"], p["z"])
    special = []
    for a, b, one_way in LINKS:
        ia, ib = _add_node(*a), _add_node(*b)
        special.append((ia, ib, one_way))

    n = len(NODES)
    for i in range(n):
        a = NODES[i]
        for j in range(i + 1, n):
            b = NODES[j]
            if abs(a[1] - b[1]) > 0.05:
                continue
            d = math.hypot(a[0] - b[0], a[2] - b[2])
            if d <= 4.4 and _corridor_clear(a, b):
                EDGES[i].append(j)
                EDGES[j].append(i)
    pad_nodes = {_add_node(p["x"], p["y"], p["z"]) for p in PADS}
    for ia, ib, one_way in special:
        EDGES[ia].append(ib)
        if not one_way:
            EDGES[ib].append(ia)
    # Walking over a pad launches you, so a pad only leads to its landing.
    for i in pad_nodes:
        EDGES[i] = [j for j in EDGES[i] if any(j == ib for ia, ib, _ in special if ia == i)]


def nearest_node(x, y, z):
    best, bi = 1e9, 0
    for i, n in enumerate(NODES):
        if abs(n[1] - y) > 1.2:
            continue
        d = (n[0] - x) ** 2 + (n[2] - z) ** 2
        if d < best:
            best, bi = d, i
    return bi


def path(start, goal):
    """A* over the waypoint graph; returns node indices after start, or [] if unreachable."""
    import heapq

    def h(i):
        a, b = NODES[i], NODES[goal]
        return math.dist(a, b)

    open_ = [(h(start), 0.0, start)]
    came = {start: None}
    cost = {start: 0.0}
    while open_:
        _, c, cur = heapq.heappop(open_)
        if cur == goal:
            out = []
            while cur != start:
                out.append(cur)
                cur = came[cur]
            return out[::-1]
        if c > cost[cur]:
            continue
        for nb in EDGES[cur]:
            nc = c + math.dist(NODES[cur], NODES[nb])
            if nc < cost.get(nb, 1e18):
                cost[nb] = nc
                came[nb] = cur
                heapq.heappush(open_, (nc + h(nb), nc, nb))
    return []
