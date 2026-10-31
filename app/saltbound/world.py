"""The hex map: geometry, generating a run's archipelago from its seed, and terrain queries.

Hexes are pointy-topped in an "odd-r" offset grid (odd rows sit half a hex to the right); a tile is
addressed by its index `r * W + q`. Each tile has an elevation: the sea level rises over the run
and floods everything at or below it. Land elevations are handed out by rank, so each rise floods
about the same amount of land (`LAND_BANDS` bands over `2..17`); the three objective dungeons and
the final peak sit at `PROTECTED`, above every band, until the peak floods and the run is lost.
"""

import math

from .rng import Rng

W, H = 30, 22
SEA0 = 1  # the starting sea level: elevation <= sea is water
LAND_MIN = 2
LAND_BANDS = 16  # land gets elevations LAND_MIN .. LAND_MIN + LAND_BANDS - 1
PROTECTED = LAND_MIN + LAND_BANDS  # 18: objectives and the final peak

REGIONS = ["coral", "keys", "storm"]

# Terrain costs on foot. Shallows and water are handled in `step_cost`.
COST = {"beach": 1, "grass": 1, "forest": 2, "hills": 2, "peak": 2, "town": 1}


# ---------------------------------------------------------------- geometry

def idx(q, r):
    return r * W + q


def qr(i):
    return i % W, i // W


def inside(q, r):
    return 0 <= q < W and 0 <= r < H


def to_cube(i):
    q, r = qr(i)
    x = q - (r - (r & 1)) // 2
    return x, r, -x - r


def dist(a, b):
    ax, ay, az = to_cube(a)
    bx, by, bz = to_cube(b)
    return max(abs(ax - bx), abs(ay - by), abs(az - bz))


_EVEN = [(1, 0), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]
_ODD = [(1, 0), (1, -1), (0, -1), (-1, 0), (0, 1), (1, 1)]


def neighbors(i):
    q, r = qr(i)
    out = []
    for dq, dr in (_ODD if r & 1 else _EVEN):
        nq, nr = q + dq, r + dr
        if inside(nq, nr):
            out.append(idx(nq, nr))
    return out


def within(i, n):
    """Every tile within n steps of i (including i)."""
    seen = {i}
    edge = [i]
    for _ in range(n):
        nxt = []
        for t in edge:
            for u in neighbors(t):
                if u not in seen:
                    seen.add(u)
                    nxt.append(u)
        edge = nxt
    return seen


def _pos(i):
    q, r = qr(i)
    return q + 0.5 * (r & 1), r * 0.866


# ---------------------------------------------------------------- generation

def _noise(rng, scale):
    """Smooth value noise over the map, 0..1."""
    gw, gh = int(W / scale) + 3, int(H * 0.866 / scale) + 3
    lattice = [[rng.random() for _ in range(gw)] for _ in range(gh)]

    def at(x, y):
        x, y = x / scale, y / scale
        x0, y0 = int(x), int(y)
        fx, fy = x - x0, y - y0
        x0, y0 = x0 % (gw - 1), y0 % (gh - 1)
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a = lattice[y0][x0] + (lattice[y0][x0 + 1] - lattice[y0][x0]) * fx
        b = lattice[y0 + 1][x0] + (lattice[y0 + 1][x0 + 1] - lattice[y0 + 1][x0]) * fx
        return a + (b - a) * fy
    return at


def generate(seed):
    """Make a run's world: elevations, biomes, regions and the places on the map."""
    rng = Rng(seed ^ 0x5A17B0D)
    cx, cy = W / 2 - 0.25, H * 0.866 / 2
    islands = [(cx, cy, 5.2, 1.0, "peak")]
    a0 = rng.random() * math.tau
    for k, reg in enumerate(REGIONS):
        a = a0 + k * math.tau / 3
        islands.append((cx + 9.6 * math.cos(a), cy + 6.2 * math.sin(a), 4.6, 0.92, reg))
    tries = 0
    while len(islands) < 16 and tries < 400:
        tries += 1
        x, y = rng.random() * (W - 4) + 2, rng.random() * (H * 0.866 - 4) + 2
        r = 1.6 + rng.random() * 1.8
        if all(math.hypot(x - ix, y - iy) > ir + r - 0.5 for ix, iy, ir, _, _ in islands):
            islands.append((x, y, r, 0.45 + rng.random() * 0.3, None))
    n1, n2 = _noise(rng, 3.0), _noise(rng, 1.4)

    f = []
    for i in range(W * H):
        q, r = qr(i)
        x, y = _pos(i)
        v = 0.0
        for ix, iy, ir, ih, _ in islands:
            d = math.hypot(x - ix, y - iy) / ir
            if d < 1.25:
                v = max(v, ih * (1 - d * d))
        v += (n1(x, y) - 0.5) * 0.28 + (n2(x, y) - 0.5) * 0.1
        if q == 0 or r == 0 or q == W - 1 or r == H - 1:
            v = -1
        f.append(v)

    land = sorted((i for i in range(W * H) if f[i] > 0.1), key=lambda i: f[i])
    elev = [0 if f[i] < -0.05 else SEA0 for i in range(W * H)]
    for rank, i in enumerate(land):
        elev[i] = LAND_MIN + rank * LAND_BANDS // len(land)

    def region_of(i):
        x, y = _pos(i)
        best, bd = None, 1e9
        for ix, iy, ir, _, reg in islands[:4]:
            d = math.hypot(x - ix, y - iy) / (ir if reg != "peak" else ir * 0.75)
            if d < bd:
                best, bd = reg, d
        return best

    region = [region_of(i) for i in range(W * H)]
    bio = []
    for i in range(W * H):
        e = elev[i]
        x, y = _pos(i)
        frac = (e - LAND_MIN) / LAND_BANDS
        if e < LAND_MIN:
            bio.append("sea")
        elif frac < 0.13:
            bio.append("beach")
        elif frac > 0.86:
            bio.append("peak")
        elif frac > 0.66:
            bio.append("hills" if n2(x * 1.7, y * 1.7) < 0.6 else "forest")
        else:
            bio.append("forest" if n1(x * 1.9 + 7, y * 1.9) > 0.56 else "grass")

    places = {}
    taken = set()

    def free(i, gap=2):
        return all(dist(i, t) >= gap for t in taken)

    def put(i, kind, **kw):
        places[i] = {"kind": kind, **kw}
        taken.add(i)

    def coastal(i):
        return any(elev[n] <= SEA0 for n in neighbors(i))

    land_tiles = [i for i in range(W * H) if elev[i] >= LAND_MIN]

    # The peak and the three objectives: the highest tile of each, raised above every band, with
    # their neighbours raised too so there's somewhere to stand beside them at the end.
    def crown(i):
        elev[i] = PROTECTED
        bio[i] = "peak"
        for n in neighbors(i):
            if elev[n] >= LAND_MIN:
                elev[n] = max(elev[n], PROTECTED - 1)
    peak_tiles = [i for i in land_tiles if region[i] == "peak"]
    peak = max(peak_tiles or land_tiles, key=lambda i: f[i])
    crown(peak)
    put(peak, "peak")
    for reg in REGIONS:
        tiles = [i for i in land_tiles if region[i] == reg and dist(i, peak) >= 6]
        if not tiles:
            tiles = [i for i in land_tiles if dist(i, peak) >= 6 and free(i, 6)]
        best = max(tiles, key=lambda i: f[i])
        crown(best)
        put(best, "dungeon", region=reg)

    # The starting town: on the peak's island, by the water, raised so it lasts.
    starts = [i for i in land_tiles if region[i] == "peak" and coastal(i) and free(i, 3)] or \
        [i for i in land_tiles if coastal(i) and free(i, 3)]
    start = min(starts, key=lambda i: (abs(dist(i, peak) - 4), -f[i]))
    elev[start] = max(elev[start], 12)
    bio[start] = "town"
    put(start, "town", name=None, start=True)

    def pick(cands, n, kind, gap=2, **kw):
        rng.shuffle(cands)
        got = []
        for i in cands:
            if len(got) >= n:
                break
            if i not in places and free(i, gap):
                put(i, kind, **kw)
                got.append(i)
        return got

    for reg in REGIONS:
        towns = pick([i for i in land_tiles if region[i] == reg and coastal(i) and elev[i] < PROTECTED - 1],
                     2, "town", gap=4)
        for t in towns:
            elev[t] = max(elev[t], 7)
            bio[t] = "town"
        pick([i for i in land_tiles if region[i] == reg and 7 <= elev[i] < PROTECTED - 1], 1, "shrine", gap=3)
        pick([i for i in land_tiles if region[i] == reg and 5 <= elev[i] < PROTECTED - 1], 2, "lair", gap=3)
    pick([i for i in land_tiles if region[i] == "peak" and 6 <= elev[i] < PROTECTED - 1], 1, "shrine", gap=3)
    pick([i for i in land_tiles if 4 <= elev[i] < PROTECTED - 1], 5, "camp", gap=3)
    pick([i for i in land_tiles if 3 <= elev[i] < PROTECTED - 1], 14, "event", gap=2)
    pick([i for i in land_tiles if elev[i] <= 5], 8, "wreck", gap=2)

    # Town names, drawn without repeats
    names = rng.shuffle(list(TOWN_NAMES))
    k = 0
    for i, p in places.items():
        if p["kind"] == "town":
            p["name"] = names[k]
            k += 1

    return {"w": W, "h": H, "elev": elev, "bio": bio, "reg": region, "start": start, "peak": peak,
            "places": {str(i): p for i, p in places.items()}}


TOWN_NAMES = ["Saltmarrow", "Gullhaven", "Tarry Cove", "Brinewick", "Lowmoor", "Kelpstead", "Wrackford",
              "Barnacle Row", "Fathom's End", "Mizzen", "Driftholm", "Cragsby"]
