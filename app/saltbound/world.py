"""The hex map: geometry, generating a run's archipelago from its seed, and terrain queries.

Hexes are pointy-topped in an "odd-r" offset grid (odd rows sit half a hex to the right); a tile is
addressed by its index `r * W + q`. Each tile has an elevation: everything at or below the sea level
(`SEA0`, fixed for the run) is water, and one above it is tidal shallows. Land elevations are handed
out by rank (`LAND_BANDS` bands over `2..17`), which shapes the terrain: beaches low, hills and peak
high; the three objective dungeons and the final peak sit at `PROTECTED`, above every band. (The sea
once rose and flooded the bands one by one; now the rising tide only makes enemies stronger.)
"""

import math

from .rng import Rng

W, H = 30, 22
SEA0 = 1  # the starting sea level: elevation <= sea is water
LAND_MIN = 2
LAND_BANDS = 16  # land gets elevations LAND_MIN .. LAND_MIN + LAND_BANDS - 1
PROTECTED = LAND_MIN + LAND_BANDS  # 18: objectives and the final peak

# The three objectives' regions of a world from before regions were drawn per run; a world now names
# its own three (`w["regions"]`, drawn from the content's pool), read through `regions(w)`.
REGIONS = ["coral", "keys", "storm"]


def regions(w):
    """The world's three objective regions, in the order they were laid out."""
    return w.get("regions") or REGIONS

# Terrain costs on foot. Shallows and water are handled in `step_cost`.
COST = {"beach": 1, "grass": 1, "forest": 2, "hills": 2, "peak": 2, "town": 1, "ice": 2}
JUNGLE_COST = 3   # the Verdant Deep's deep jungle (a forest hex there), until someone cuts a trail through it
SINK_COST = 4     # quicksand: it takes a whole turn's moves to get out of
# Map talents that make rough ground cost 1: the class's map key -> terrain
FAST = {"trailbreaker": ["forest", "hills", "peak"], "wildspeak": ["forest"]}


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


def from_cube(x, y):
    """The tile at cube coordinates (x, y), or None off the map."""
    q, r = x + (y - (y & 1)) // 2, y
    return idx(q, r) if inside(q, r) else None


CUBE_DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]  # cube (x, y) steps: east, then anticlockwise


def step_dir(t, d):
    """The tile one step from t in hex direction d (0..5), or None off the map."""
    x, y, _ = to_cube(t)
    dx, dy = CUBE_DIRS[d % 6]
    return from_cube(x + dx, y + dy)


def dist(a, b):
    ax, ay, az = to_cube(a)
    bx, by, bz = to_cube(b)
    return max(abs(ax - bx), abs(ay - by), abs(az - bz))


_EVEN = [(1, 0), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]
_ODD = [(1, 0), (1, -1), (0, -1), (-1, 0), (0, 1), (1, 1)]


def neighbors(i):
    """The tiles next to i (a fresh list; computed once per tile)."""
    return list(_NEIGH[i])


def _neighbors(i):
    q, r = qr(i)
    out = []
    for dq, dr in (_ODD if r & 1 else _EVEN):
        nq, nr = q + dq, r + dr
        if inside(nq, nr):
            out.append(idx(nq, nr))
    return out


_NEIGH = [tuple(_neighbors(i)) for i in range(W * H)]


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


def generate(seed, pool=None):
    """Make a run's world: elevations, biomes, regions and the places on the map. Its three objective
    regions are drawn from `pool` (every region the content has; the original three without one)."""
    rng = Rng(seed ^ 0x5A17B0D)
    REGIONS = Rng(seed ^ 0x0B1EC7).sample(sorted(pool), 3) if pool else globals()["REGIONS"]
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

    world = {"w": W, "h": H, "elev": elev, "bio": bio, "reg": region, "start": start, "peak": peak,
             "places": {str(i): p for i, p in places.items()}, "regions": list(REGIONS)}
    add_features(world, Rng(seed ^ 0x5EA5))
    add_biomes(world, Rng(seed ^ 0xB10E))
    return world


# ---------------------------------------------------------------- the sea's and the land's extras

LANES = 3         # currents
LANE_MAX = 9      # hexes in a current at most
REEFS = 6         # single-hex reefs: a skiff can cross only at high tide
POOLS = 2         # whirlpools: no skiff can enter one, and the hexes around cost a skiff 1 more
SEA_PLACES = (("shrine", 1, 2), ("cove", 2, 2), ("flotsam", 3, 1))  # (kind, how many, hexes off the land at least)  # out at sea, reached only by skiff
GROTTOS = ("hoard", "hoard", "spring")  # hidden until someone walks within a hex (Farsight: two)


def on_edge(i):
    q, r = qr(i)
    return q == 0 or r == 0 or q == W - 1 or r == H - 1


def add_features(w, rng):
    """What a world gets on top of its islands (new runs, and old saves' worlds, which have none):
    currents (`cur`: a hex -> the next hex downstream; riding one costs a skiff nothing), reefs
    (`reef`), whirlpools (`pool`), places out at sea (coves, flotsam, a drowned shrine), a lookout on
    each region's high ground and hidden grottos. Uses only `rng`, so the run's own generator is
    untouched, and keeps clear of every place already there."""
    if "cur" in w:
        return
    elev, bio, reg = w["elev"], w["bio"], w["reg"]
    places = w["places"]
    taken = {int(t) for t in places}
    water = [i for i in range(W * H) if elev[i] <= SEA0]
    # how far each water hex is from land (land is 0)
    shore = {i: 0 for i in range(W * H) if elev[i] > SEA0}
    edge = list(shore)
    while edge:
        nxt = []
        for t in edge:
            for n in neighbors(t):
                if n not in shore:
                    shore[n] = shore[t] + 1
                    nxt.append(n)
        edge = nxt
    open_sea = [i for i in water if not on_edge(i)]

    def free(i, gap):
        return all(dist(i, t) >= gap for t in taken)

    # Currents: a few one-way lanes of open water, 6-9 hexes long, preferring ones that join two
    # regions' waters, routed a hex off the land where they can be. Riding one is a free trip.
    REGIONS = regions(w)
    land_of = {r: [i for i in range(W * H) if reg[i] == r and elev[i] > SEA0] for r in REGIONS}
    sea_ok = lambda i: shore.get(i, 0) >= 1 and not on_edge(i)
    cur, lanes, blocked = {}, [], set()
    tries = 0
    while len(lanes) < LANES and tries < 80:
        tries += 1
        opts = [i for i in open_sea if i not in blocked]
        if not opts:
            break
        s0 = rng.choice(opts)
        far = [i for i in opts if 7 <= dist(i, s0) <= 10 and (tries > 40 or reg[i] != reg[s0])]
        if not far:
            continue
        g0 = rng.choice(far)
        dist_, prev, pq = {s0: 0}, {}, [(0, s0)]
        while pq:
            pq.sort()
            d, t = pq.pop(0)
            if t == g0:
                break
            if d > dist_[t]:
                continue
            for n in neighbors(t):
                if not sea_ok(n) or n in blocked:
                    continue
                nd = d + 1 + (1 if shore[n] == 1 else 0)
                if nd < dist_.get(n, 1e9):
                    dist_[n] = nd
                    prev[n] = t
                    pq.append((nd, n))
        if g0 not in prev:
            continue
        lane = [g0]
        while lane[-1] != s0:
            lane.append(prev[lane[-1]])
        lane.reverse()
        if len(lane) > 1.5 * dist(s0, g0) + 1:
            continue  # a winding route isn't a current
        lane = lane[:LANE_MAX]
        for x, y in zip(lane, lane[1:]):
            cur[x] = y
        lanes.append(lane)
        blocked |= {n for t in lane for n in neighbors(t)} | set(lane)
    on_lane = {t for lane in lanes for t in lane}
    near_lane = {n for t in on_lane for n in neighbors(t)} | on_lane

    def pick(cands, n, gap, kind=None, **kw):
        rng.shuffle(cands)
        got = []
        for i in cands:
            if len(got) >= n:
                break
            if i not in taken and free(i, gap) and all(dist(i, x) >= gap for x in got):
                got.append(i)
                if kind:
                    places[str(i)] = {"kind": kind, **kw}
                    taken.add(i)
        return got

    reefs = pick([i for i in open_sea if elev[i] == SEA0 and 1 <= shore[i] <= 2 and i not in near_lane], REEFS, 3)
    pools = pick([i for i in open_sea if shore[i] >= 2 and i not in near_lane], POOLS, 5)
    swirl = {n for p in pools for n in neighbors(p)} | set(pools)
    hazard = set(reefs) | swirl
    for kind, n, off in SEA_PLACES:
        cands = [i for i in open_sea if shore[i] >= off and i not in hazard and i not in on_lane]
        extra = {"sea": True} if kind == "shrine" else {}
        pick(cands, n, 3, kind, **extra)
    # a lookout on each region's high ground, away from its other places
    for r in REGIONS:
        hi = [i for i in land_of.get(r, []) if bio[i] in ("hills", "peak") and elev[i] < PROTECTED - 1]
        hi.sort(key=lambda i: -elev[i])
        pick(hi[:30], 1, 2, "lookout")
    towns = [int(t) for t, p in places.items() if p["kind"] == "town"]
    kinds = rng.shuffle(list(GROTTOS))
    for k, r in enumerate(REGIONS):
        cands = [i for i in land_of.get(r, []) if bio[i] in ("forest", "hills") and elev[i] < PROTECTED - 1
                 and all(dist(i, t) >= 3 for t in towns)]
        pick(cands, 1, 2, "grotto", grotto=kinds[k % len(kinds)], hidden=True)
    w["cur"] = {str(a): b for a, b in cur.items()}
    w["reef"] = sorted(reefs)
    w["pool"] = sorted(pools)


# ---------------------------------------------------------------- each region's own land

SINKS = 6          # the Shifting Sands: quicksand hexes
OASES = 2          # ...and oases (full heal, curses lifted; once per hero)
FOSSILS = 2        # the Stillwood: fossil beds to dig
GEODES = 2         # the Prism Wood: geodes holding enchant materials
GATES = 2          # Aetherhold: pairs of light-gates (one end there, one far off)
ICE_REACH = 2      # the Frostpeaks: open water this close to its land is frozen


def add_biomes(w, rng):
    """The fixed features of the regions that have them (only for the regions this world drew):
    quicksand (`sink`) and oases in the Shifting Sands, fossil beds in the Stillwood, geodes in the
    Prism Wood, light-gates from Aetherhold (each `gate` names its twin in `to`), and the frozen sea
    round the Frostpeaks (`ice`: water hexes that are walked on, not sailed). Uses only `rng`."""
    if "ice" in w:
        return
    regs = regions(w)
    elev, bio, reg, places = w["elev"], w["bio"], w["reg"], w["places"]
    taken = {int(t) for t in places}
    hazards = set(w.get("reef", [])) | set(w.get("pool", [])) | {int(a) for a in w.get("cur", {})} | set(w.get("cur", {}).values())

    def free(i, gap):
        return i not in taken and all(dist(i, t) >= gap for t in taken)

    def land(r, kinds=None):
        return [i for i in range(W * H) if reg[i] == r and LAND_MIN <= elev[i] < PROTECTED - 1 and bio[i] != "town"
                and (kinds is None or bio[i] in kinds)]

    def put(cands, n, kind, gap=2, **kw):
        """Up to n new places among cands, kept `gap` hexes off the others (closer if there's no room)."""
        rng.shuffle(cands)
        got = []
        for g in range(gap, 0, -1):
            for i in cands:
                if len(got) >= n:
                    return got
                if free(i, g):
                    places[str(i)] = {"kind": kind, **kw}
                    taken.add(i)
                    got.append(i)
        return got

    sink = []
    if "dunes" in regs:
        cands = rng.shuffle(land("dunes", ("grass", "hills")))
        for i in cands:
            if len(sink) >= SINKS:
                break
            if i not in taken and all(dist(i, x) >= 2 for x in sink) and all(dist(i, t) >= 1 for t in taken):
                sink.append(i)
        put(land("dunes", ("grass", "beach", "forest")), OASES, "oasis", gap=3)
    if "petrified" in regs:
        put(land("petrified", ("forest", "hills", "grass")), FOSSILS, "fossil", gap=3)
    if "crystal" in regs:
        put(land("crystal", ("forest", "hills")), GEODES, "geode", gap=3)
    if "heaven" in regs:
        here = land("heaven")
        start = w["start"]
        others = [i for r in regs if r != "heaven" for i in land(r)]
        homes = [i for i in range(W * H) if reg[i] == "peak" and LAND_MIN <= elev[i] < PROTECTED - 1 and bio[i] != "town" and 2 <= dist(i, start) <= 4]
        for far in (homes, sorted(others, key=lambda i: -dist(i, w["peak"]))[:20]):
            a = put(list(here), 1, "gate", gap=3)
            b = put(list(far), 1, "gate", gap=3)
            if a and b:
                places[str(a[0])]["to"], places[str(b[0])]["to"] = b[0], a[0]
            else:
                for x in a + b:
                    places.pop(str(x), None)
                    taken.discard(x)
    ice = []
    if "frost" in regs:
        frost = [i for i in range(W * H) if reg[i] == "frost" and elev[i] > SEA0]
        for i in range(W * H):
            if elev[i] <= SEA0 and not on_edge(i) and i not in hazards and i not in taken \
                    and any(dist(i, x) <= ICE_REACH for x in frost) \
                    and min((dist(i, x) for x in range(W * H) if elev[x] > SEA0), default=99) == min(dist(i, x) for x in frost):
                ice.append(i)
    w["sink"] = sorted(sink)
    w["ice"] = sorted(ice)


TOWN_NAMES = ["Saltmarrow", "Gullhaven", "Tarry Cove", "Brinewick", "Lowmoor", "Kelpstead", "Wrackford",
              "Barnacle Row", "Fathom's End", "Mizzen", "Driftholm", "Cragsby"]
