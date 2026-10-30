"""Frag Arena's map, its geometry, and the movement physics.

The browser runs the same movement for its own player (`js/physics.js`); keep the two in step.
The server only moves bots with it. Coordinates are metres, y up, a player's position is the
centre of their feet.
"""

import math

# Counter-Strike's movement (Half-Life's, inherited from Quake 1) at a quicker run speed.
# In the air, the speed you can add toward where you're steering is capped at `air_cap`, but you
# add it fast (`air_accel`): so W does almost nothing mid-air, while strafing with A or D and
# turning the mouse the same way bends your path and builds speed. That's bunny-hopping and air
# strafing. Sent to the client in `welcome`.
PHYS = {
    "gravity": 25.0,
    "speed": 10.0,  # top run speed
    "accel": 6.0,  # CS: 5.5
    "air_accel": 12.0,  # CS:GO: 12
    "air_cap": 1.2,  # CS: 30 of 250 units/s, the same share of top speed
    "friction": 5.2,  # CS:GO: 5.2
    "stop_speed": 3.0,
    "jump": 8.4,
    "step": 0.5,  # highest ledge you walk up without jumping
    "radius": 0.4,
    "height": 1.8,
    "eye": 1.6,
    "pad_mul": 1.0,  # jump pads' launch speed; low gravity lowers it so pads land in the same place
}
BASE_PHYS = dict(PHYS)

R = PHYS["radius"]
H = PHYS["height"]
STEP = PHYS["step"]
EPS = 1e-5

# The map in play. Maps are built in code from axis-aligned boxes by the builders in MAPS, and
# `load_map` swaps one in: these lists are emptied and refilled in place, so anything holding them
# sees the new map.
BOXES: list[tuple] = []  # (x0, y0, z0, x1, y1, z1)
MATS: list[str] = []  # each box's material, which the browser draws it with
WALKABLE: list[tuple] = []  # the boxes whose tops get waypoints
PADS: list[dict] = []  # jump pads: a disc that launches you at a target
PICKUPS: list[dict] = []
POWER_SPOTS: list[dict] = []  # where the rare power weapons appear
SPAWNS: list[tuple] = []  # (x, y, z, yaw)
LINKS: list[tuple] = []  # hand-made waypoint links: (a, b, one_way)
HALF = [30.0, 30.0]  # the inside of the outer walls: |x| <= HALF[0], |z| <= HALF[1]
THEME: dict = {}  # sky, fog and light colours for the browser
MAP = {"key": "", "name": ""}


def box(x0, y0, z0, x1, y1, z1, mat, walk=False):
    b = (min(x0, x1), min(y0, y1), min(z0, z1), max(x0, x1), max(y0, y1), max(z0, z1))
    BOXES.append(b)
    MATS.append(mat)
    if walk:
        WALKABLE.append(b)
    return b


def stairs(a0, a1, start, direction, top, rise, run, mat="stone", axis="z", base=0.0):
    """Steps falling away from a ledge's edge at `start`, along `axis` in `direction` (+1/-1), from
    `top` down to `base`. a0..a1 is how far they reach across."""
    n = round((top - base) / rise)
    for k in range(n - 1):
        h = top - rise * (k + 1)
        s = start + direction * run * k
        if axis == "z":
            box(a0, 0, s, a1, h, s + direction * run, mat, walk=True)
        else:
            box(s, 0, a0, s + direction * run, h, a1, mat, walk=True)
    end = start + direction * run * (n - 1)
    mid = (a0 + a1) / 2
    lo, hi = end + direction * 0.8, start - direction * 0.8
    if axis == "z":
        LINKS.append(((mid, base, lo), (mid, top, hi), False))
    else:
        LINKS.append(((lo, base, mid), (hi, top, mid), False))


def jump_pad(x, z, tx, ty, tz, apex=3.5, y=0.0):
    """A pad at (x, y, z) that throws you onto (tx, ty, tz), peaking `apex` metres above the target.
    Worked out at normal gravity; low gravity scales the launch (`pad_mul`) to land in the same place."""
    g = BASE_PHYS["gravity"]
    vy = math.sqrt(2 * g * (ty - y + apex))
    t = vy / g + math.sqrt(2 * apex / g)
    vx, vz = (tx - x) / t, (tz - z) / t
    PADS.append({"x": x, "y": y, "z": z, "r": 1.0, "v": (vx, vy, vz)})
    LINKS.append(((x, y, z), (tx, ty, tz), True))


def pickup(kind, x, y, z):
    PICKUPS.append({"kind": kind, "x": x, "y": y, "z": z})


def power_spot(x, y, z, where, bots=True):
    """Where a power weapon can appear; `bots` says whether bots can walk there."""
    POWER_SPOTS.append({"x": x, "y": y, "z": z, "where": where, "bots": bots})


def spawn(x, y, z):
    SPAWNS.append((x, y, z, math.atan2(x, z)))  # facing the middle


def outer(hx, hz, height=16.0):
    """The floor and the four outer walls, around a space 2hx by 2hz."""
    HALF[:] = [hx, hz]
    box(-hx - 2, -1, -hz - 2, hx + 2, 0, hz + 2, "floor", walk=True)
    box(-hx - 2, 0, hz, hx + 2, height, hz + 2, "wall")
    box(-hx - 2, 0, -hz - 2, hx + 2, height, -hz, "wall")
    box(hx, 0, -hz, hx + 2, height, hz, "wall")
    box(-hx - 2, 0, -hz, -hx, height, hz, "wall")


def build_arena():
    """The first map: a square pit with a central platform, two ledges and four pillars."""
    outer(30, 30)
    THEME.update(sky=["#1e1830", "#7a4a3a", "#d08a50"], fog="#5a3f36", sun="#ffd8a8", ground="#3a2a20")

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

    power_spot(12, 7, -12, "on top of a pillar", bots=False)  # a rocket jump up
    power_spot(26, 0, 26, "in a corner")
    power_spot(-26, 0, -26, "in a corner")
    power_spot(25, 4, 13, "on the east ledge")
    power_spot(-25, 4, -13, "on the west ledge")

    for p in ((20, 0, 26), (-20, 0, -26), (-20, 0, 26), (20, 0, -26),
              (26, 4, -12), (-26, 4, 12), (-8, 0, 13), (8, 0, -13)):
        spawn(*p)


def build_warehouse():
    """A long hall with grated catwalks along both ends and a bridge across the middle, and
    shipping containers on the floor below. Fights happen on two levels at once."""
    outer(32, 24)
    THEME.update(sky=["#0e141c", "#34424f", "#8496a4"], fog="#27313b", sun="#d8e6ff", ground="#1c232b")

    # Catwalks 4 m up (you can walk underneath), joined by a bridge down the middle.
    box(-32, 3.6, 18, 32, 4, 24, "grate", walk=True)
    box(-32, 3.6, -24, 32, 4, -18, "grate", walk=True)
    box(-2.5, 3.6, -18, 2.5, 4, 18, "grate", walk=True)
    for x0, x1 in ((26, 30), (-30, -26)):
        stairs(x0, x1, 18, -1, 4.0, 0.4, 0.6, mat="metal")
        stairs(x0, x1, -18, +1, 4.0, 0.4, 0.6, mat="metal")
    jump_pad(16, 0, 0, 4, 0)  # onto the bridge, by the mega health
    jump_pad(-16, 0, 0, 4, 0)

    # Containers, and two stacked ones only a rocket jump reaches.
    for sx in (-1, 1):
        box(sx * 8, 0, sx * 6, sx * 14, 2.6, sx * 9, "metal")
        box(sx * 19, 0, sx * 4, sx * 22, 2.6, sx * 10, "metal")
        box(sx * 18, 0, sx * -10, sx * 24, 5.2, sx * -13, "metal")
        box(sx * 5, 0, sx * 10, sx * 6.5, 1.5, sx * 11.5, "crate")
        box(sx * 10, 0, sx * 14, sx * 12, 1, sx * 16, "crate")

    pickup("mega", 0, 4, 0)
    pickup("armor", 0, 4, 21)
    pickup("armor", 0, 4, -21)
    pickup("health", 10, 0, 2)
    pickup("health", -10, 0, -2)
    pickup("health", 20, 4, 21)
    pickup("health", -20, 4, -21)
    pickup("ammo", 26, 0, 0)
    pickup("ammo", -26, 0, 0)
    pickup("ammo", 14, 4, -21)
    pickup("ammo", -14, 4, 21)

    power_spot(-21, 5.2, -11.5, "on the stacked containers", bots=False)
    power_spot(29, 4, 21, "on the north catwalk")
    power_spot(-29, 4, -21, "on the south catwalk")
    power_spot(0, 0, 0, "under the bridge")

    for p in ((-28, 0, -8), (28, 0, 8), (14, 0, 13), (-14, 0, -13),
              (-20, 4, 21), (20, 4, -21), (0, 0, 6), (0, 0, -6)):
        spawn(*p)


def build_spire():
    """A stepped tower in the middle: stairs to the first two tiers, a jump pad to the top. Raised
    balconies in the corners."""
    outer(30, 30)
    THEME.update(sky=["#120c24", "#583a78", "#e28aa0"], fog="#3a2a4a", sun="#ffd0e4", ground="#2a1a30")

    box(-12, 0, -12, 12, 3, 12, "stone", walk=True)
    box(-6, 0, -6, 6, 6, 6, "metal", walk=True)
    box(-2.5, 0, -2.5, 2.5, 9, 2.5, "pillar", walk=True)
    # Up to the first tier from all four sides.
    stairs(-2, 2, 12, +1, 3.0, 0.375, 0.6)
    stairs(-2, 2, -12, -1, 3.0, 0.375, 0.6)
    stairs(-2, 2, 12, +1, 3.0, 0.375, 0.6, axis="x")
    stairs(-2, 2, -12, -1, 3.0, 0.375, 0.6, axis="x")
    # Up to the second from the east and west, and pads from there to the top.
    stairs(2, 5, 6, +1, 6.0, 0.375, 0.45, mat="metal", axis="x", base=3.0)
    stairs(-5, -2, -6, -1, 6.0, 0.375, 0.45, mat="metal", axis="x", base=3.0)
    jump_pad(0, 4.5, 0, 9, 0, y=6.0)
    jump_pad(0, -4.5, 0, 9, 0, y=6.0)
    for x in (-4.2, 4.2):
        LINKS.append(((0, 9, 0), (x, 6.0, 0), True))  # bots get down by stepping off the top

    # Corner balconies, each with stairs.
    for sx in (-1, 1):
        for sz in (-1, 1):
            box(sx * 22, 0, sz * 22, sx * 30, 4, sz * 30, "stone", walk=True)
            stairs(sz * 26, sz * 29, sx * 22, -sx, 4.0, 0.4, 0.6, axis="x")
            box(sx * 16, 0, sz * 16, sx * 18, 7, sz * 18, "pillar")
    # Low walls to duck behind on the floor.
    for s in (-1, 1):
        box(s * 22.5, 0, -4, s * 23.5, 1.2, 4, "crate")
        box(-4, 0, s * 22.5, 4, 1.2, s * 23.5, "crate")

    pickup("mega", 4.2, 6, 0)
    pickup("armor", 26, 4, 26)
    pickup("armor", -26, 4, -26)
    pickup("health", 26, 4, -26)
    pickup("health", -26, 4, 26)
    pickup("health", 0, 0, 26.5)
    pickup("health", 0, 0, -26.5)
    pickup("ammo", 9, 3, -9)
    pickup("ammo", -9, 3, 9)
    pickup("ammo", 26.5, 0, 0)
    pickup("ammo", -26.5, 0, 0)

    power_spot(0, 9, 0, "on top of the spire")
    power_spot(9, 3, 9, "on the spire's first tier")
    power_spot(-9, 3, -9, "on the spire's first tier")
    power_spot(26.5, 0, 9, "by the east wall")
    power_spot(-26.5, 0, -9, "by the west wall")

    for p in ((24, 0, 8), (-24, 0, -8), (8, 0, 24), (-8, 0, -24),
              (28, 4, 24), (-28, 4, -24), (24, 4, -28), (-24, 4, 28)):
        spawn(*p)


def build_bases():
    """Two raised bases facing each other across a long courtyard, Halo-style, each with a tower
    behind it. A low platform with the mega health sits in the middle."""
    outer(40, 20)
    THEME.update(sky=["#16262c", "#567676", "#cad8c0"], fog="#46564c", sun="#fff0d0", ground="#283028")

    for s in (-1, 1):
        box(s * 30, 0, -20, s * 40, 3, 20, "stone", walk=True)
        stairs(-13, -9, s * 30, -s, 3.0, 0.375, 0.6, axis="x")
        stairs(9, 13, s * 30, -s, 3.0, 0.375, 0.6, axis="x")
        box(s * 36, 0, -3, s * 40, 7, 3, "pillar")  # the tower: a rocket jump up
        box(s * 30, 3, -6, s * 31, 4.2, 6, "metal")  # a parapet to shoot over
        jump_pad(s * 22, 0, s * 34, 3, 0)
        box(s * 13, 0, -1, s * 15, 1.5, 1, "crate")
        box(s * 20, 0, s * 14, s * 22, 1.5, s * 16, "crate")
        box(-8, 0, s * 15.5, 8, 1.2, s * 16.5, "stone")
        for t in (-1, 1):
            box(s * 15, 0, t * 10, s * 17, 7, t * 12, "pillar")
    box(-6, 0, -6, 6, 2, 6, "metal", walk=True)
    stairs(-1.5, 1.5, 6, +1, 2.0, 0.4, 0.6, axis="x")
    stairs(-1.5, 1.5, -6, -1, 2.0, 0.4, 0.6, axis="x")

    pickup("mega", 0, 2, 0)
    pickup("armor", 35, 3, 12)
    pickup("armor", -35, 3, -12)
    pickup("health", 34, 3, -12)
    pickup("health", -34, 3, 12)
    pickup("health", 20, 0, -8)
    pickup("health", -20, 0, 8)
    pickup("ammo", 0, 0, 12)
    pickup("ammo", 0, 0, -12)
    pickup("ammo", 26, 0, -16)
    pickup("ammo", -26, 0, 16)

    power_spot(38, 7, 0, "on the east tower", bots=False)
    power_spot(-38, 7, 0, "on the west tower", bots=False)
    power_spot(0, 0, 18, "behind the north wall")
    power_spot(0, 0, -18, "behind the south wall")

    for p in ((35, 3, 8), (35, 3, -8), (-35, 3, 8), (-35, 3, -8),
              (22, 0, 18), (-22, 0, -18), (10, 0, -6), (-10, 0, 6)):
        spawn(*p)


# key: (name, builder, a line for the menu)
MAPS = {
    "arena": ("Arena", build_arena, "The original: a central platform, two ledges, four pillars."),
    "warehouse": ("Warehouse", build_warehouse, "Catwalks over a floor of shipping containers."),
    "spire": ("Spire", build_spire, "Climb the stepped tower in the middle; corner balconies."),
    "bases": ("Twin Bases", build_bases, "A long courtyard between two raised bases."),
}
_GRAPHS: dict = {}  # each map's waypoint graph, built the first time bots play it


def load_map(key):
    """Swap in another map. The waypoint graph comes back too if it was built before."""
    for lst in (BOXES, MATS, WALKABLE, PADS, PICKUPS, POWER_SPOTS, SPAWNS, LINKS, NODES, EDGES):
        lst.clear()
    THEME.clear()
    name, builder, _ = MAPS[key]
    MAP.update(key=key, name=name)
    builder()
    if key in _GRAPHS:
        nodes, edges = _GRAPHS[key]
        NODES.extend(nodes)
        EDGES.extend([e[:] for e in edges])


def map_payload():
    """What the client needs to draw and collide with the map."""
    return {
        "key": MAP["key"], "name": MAP["name"], "theme": THEME, "half": HALF,
        "boxes": [[*b, m] for b, m in zip(BOXES, MATS)],
        "pads": [[p["x"], p["y"], p["z"], p["r"], *p["v"]] for p in PADS],
        "pickups": [[p["kind"], p["x"], p["y"], p["z"]] for p in PICKUPS],
        "power": [[s["x"], s["y"], s["z"]] for s in POWER_SPOTS],
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
        self.fast = 1.0  # run speed multiplier (zombies are quicker)

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


def _accelerate(vel, wx, wz, wishspeed, accel, dt, cap=None):
    """Quake/Half-Life acceleration. `cap` limits the target speed but not the rate (air moves)."""
    current = vel[0] * wx + vel[2] * wz
    add = (wishspeed if cap is None else min(wishspeed, cap)) - current
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
    wishspeed = PHYS["speed"] * body.fast * min(wish, 1.0)

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
        _accelerate(v, wx, wz, wishspeed, PHYS["air_accel"], dt, PHYS["air_cap"])
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
                v[0], v[1], v[2] = (c * PHYS["pad_mul"] for c in pad["v"])
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
    # a grid 3 m apart, centred on the middle of the map
    xs, zs = ([1.5 + 3 * i for i in range(-20, 20) if abs(1.5 + 3 * i) <= h - 0.5] for h in HALF)
    for y in tops:
        for x in xs:
            for z in zs:
                if _on_walkable(x, y, z) and not inside_solid(x, y, z):
                    _add_node(x, y, z)
    for p in PICKUPS:
        _add_node(p["x"], p["y"], p["z"])
    for s in POWER_SPOTS:
        if s["bots"]:
            _add_node(s["x"], s["y"], s["z"])
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
    _GRAPHS[MAP["key"]] = (NODES[:], [e[:] for e in EDGES])


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


load_map("arena")
