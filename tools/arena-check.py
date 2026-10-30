"""Plays Frag Arena with bots only, headlessly, and checks the map and the bots behave.

    python3 tools/arena-check.py [seconds]

Checks every map: fails if its waypoint graph has unreachable parts, or a spawn, pickup or power
spot is inside a wall or off the graph. Then plays each map with 6 bots and fails if a bot spends
long stuck, nobody scores, or ticks get slow (99th percentile over a quarter of the 33 ms
budget). Then plays each party mode (and some mutators) and fails if the mode doesn't do its
thing: Gun Game players climbing the ladder, Infection spreading and ending, a Juggernaut crowned.
"""

import math
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.arena import game, world


def check_graph(key):
    world.load_map(key)
    world.build_graph()
    n = len(world.NODES)
    seen = {0}
    todo = [0]
    while todo:
        for j in world.EDGES[todo.pop()]:
            if j not in seen:
                seen.add(j)
                todo.append(j)
    print(f"{world.MAP['name']} graph: {n} nodes, {sum(map(len, world.EDGES))} links, {len(seen)} reachable from node 0")
    bad = []
    for i in range(n):
        if not world.path(i, 0) and i != 0:
            bad.append(world.NODES[i])
    if len(seen) != n or bad:
        print("unreachable:", [world.NODES[i] for i in range(n) if i not in seen][:10], "can't return:", bad[:10])
        return False
    for i, (x, y, z) in enumerate(world.NODES):
        if world.inside_solid(x, y, z):
            print("node inside a wall:", world.NODES[i])
            return False
    spots = [("spawn", *s[:3]) for s in world.SPAWNS]
    spots += [(p["kind"], p["x"], p["y"], p["z"]) for p in world.PICKUPS]
    spots += [("power", p["x"], p["y"], p["z"]) for p in world.POWER_SPOTS if p["bots"]]
    for kind, x, y, z in spots:
        near = min((math.hypot(a - x, c - z) for a, b, c in world.NODES if abs(b - y) < 0.1), default=99)
        if world.inside_solid(x, y, z) or (kind != "spawn" and near > 0.01) or near > 4.4:
            print(f"{kind} at {(x, y, z)} is inside a wall or off the waypoints")
            return False
    return True


def run(seconds, mode="dm", muts=(), key="arena"):
    random.seed(1)
    g = game.Game()
    g.mode, g.muts = mode, set(muts)
    g.set_map(key)
    g.new_round()
    wins = []
    end_round = g.end_round
    g.end_round = lambda w, text=None: (wins.append((w.name if w else None, text)), end_round(w, text))
    seen = {"jugg": 0, "zombies": 0, "rung": 0}
    kills = []  # counted here, since a round ending resets the scores
    kill = g.kill
    g.kill = lambda t, by, w: (kills.append(w), kill(t, by, w))
    for _ in range(6):
        g.add_bot()
    sim_now = [0.0]
    g.now = lambda: sim_now[0]
    for p in g.players.values():
        p.died_at = -99
    stuck = {p.id: [0.0, None] for p in g.players.values()}
    times = []
    ticks = int(seconds / game.TICK)
    longest_stuck = 0.0
    for i in range(ticks):
        sim_now[0] = i * game.TICK
        t0 = time.perf_counter()
        g.tick()
        times.append(time.perf_counter() - t0)
        ps = list(g.players.values())
        seen["jugg"] = max(seen["jugg"], sum(p.role == "jugg" for p in ps))
        seen["zombies"] = max(seen["zombies"], sum(p.role == "zombie" for p in ps))
        if mode == "gun":
            seen["rung"] = max([seen["rung"]] + [p.score // game.GUN_KILLS for p in ps])
        for p in g.players.values():
            s = stuck[p.id]
            if not p.alive:
                s[:] = [sim_now[0], None]
                continue
            if s[1] is None or math.dist(s[1], p.pos) > 1.5:
                s[:] = [sim_now[0], p.pos[:]]
            elif sim_now[0] - s[0] > longest_stuck:
                longest_stuck = sim_now[0] - s[0]
                if longest_stuck > 8:
                    print(f"  {p.name} stuck at {[round(c, 1) for c in p.pos]} for {longest_stuck:.0f}s")
    deaths = len(kills)
    used = sorted({game.WEAPONS[w]["short"] for w in kills})
    print(f"{g.describe()}, {seconds}s simulated: {deaths} deaths, by {', '.join(used)}; rounds won: {wins}; {seen}")
    for p in sorted(g.players.values(), key=lambda p: -p.score):
        print(f"  {p.name:6} {p.score:3} frags {p.deaths:3} deaths")
    times.sort()
    p99 = times[int(len(times) * 0.99)]
    print(f"tick: mean {sum(times) / ticks * 1000:.2f} ms, 99th percentile {p99 * 1000:.2f} ms, "
          f"worst {times[-1] * 1000:.2f} ms; longest stuck {longest_stuck:.1f}s")
    ok = deaths >= seconds / 20 and p99 < game.TICK * 0.25 and longest_stuck < 12
    if mode == "gun":
        ok = ok and seen["rung"] >= 3
    elif mode == "infect":
        ok = ok and seen["zombies"] >= 3 and bool(wins)
    elif mode == "jugg":
        ok = ok and seen["jugg"] == 1
    world.PHYS.update(world.BASE_PHYS)
    return ok


def main():
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 180
    graphs = [check_graph(key) for key in world.MAPS]  # every map, even after one fails
    ok = all(graphs)
    for key in world.MAPS:
        ok = run(seconds, key=key) and ok
    for mode, muts, key in (("gun", (), "warehouse"), ("infect", (), "spire"), ("jugg", ("frenzy",), "bases"),
                            ("dm", ("lowgrav", "insta"), "arena"), ("dm", ("rockets", "lowgrav"), "spire")):
        ok = run(200, mode, muts, key) and ok
    print("OK" if ok else "FAILED")
    sys.exit(0 if ok else 1)


main()
