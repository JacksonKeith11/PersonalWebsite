#!/usr/bin/env python3
"""Kingfall's balance sim: bot parties fight bosses on the real server code (app/kingfall/fight.py), in
simulated time. Bots read each move's data the way a player reads its wind-up: they see a hit coming
`react` seconds before it lands and roll through it with probability `skill`, attack in openings,
drink when low and revive the fallen.

    python3 tools/kingfall-sim.py                     all bosses, parties of 1-4, 20 fights each
    python3 tools/kingfall-sim.py corvin 40 --size 2   one boss, 40 fights, parties of 2
    python3 tools/kingfall-sim.py --skill 0.6         weaker bots (default 0.8)

Prints win rate, average fight length and hits taken per hero. A fight about two to four minutes
long that skilled bots win most of the time and middling ones about half the time is the target
(docs/kingfall.md, "Testing").
"""

import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app.kingfall import content as C  # noqa: E402
from app.kingfall.fight import TICK, Fight  # noqa: E402
from app.kingfall.geom import place_attack, place_hit, touches  # noqa: E402
from app.kingfall.room import Hero  # noqa: E402


class Stub:
    def __init__(self): self.events = []
    def broadcast(self, m):
        if m.get("t") == "fx" and m.get("k") in ("down", "dead", "stagger", "topple", "parry", "crit"):
            self.events.append("stagger" if m["k"] == "topple" else m["k"])


class Bot:
    def __init__(self, fh, skill, rng):
        self.fh, self.skill, self.rng = fh, skill, rng
        self.react = 0.32 - 0.12 * skill
        self.state, self.t = "idle", 0.0
        self.combo = 0
        self.roll_dir = 0.0
        self.taken = set()
        self.hits = 0
        self.swing = 0
        self.decided = set()
        self.revive_t = 0.0
        self.W = C.WEAPONS[fh.hero.weapon]

    def iframes(self):
        a, b = C.HERO["roll"]["iframes"]
        return self.state == "roll" and a <= self.t <= b


def danger(f, x, y, ahead):
    """Hits about to land on (x, y) within `ahead` seconds: [(key, seconds until)]."""
    out = []
    for m in f.moves():
      t = f_now[0] - m.start
      for i, h in enumerate(m.data["hits"]):
        if h["k"] == "spawn": continue
        # sample the hit across its life (charges, rings and projectiles move): when does it first reach us?
        for k in range(8):
          ht = h["t0"] + (h["t1"] - h["t0"]) * k / 7
          dt = ht - t
          if dt < 0: continue
          if dt > ahead: break
          s = place_hit(m, h, ht)
          if s and touches(s, x, y, C.HERO["radius"] + 6):
              out.append((f"{m.seq}:{i}", dt, h["t1"] - h["t0"] > 0.35)); break
    return out


f_now = [0.0]


def step_bot(b, f, now, dt, bots):
    fh, H = b.fh, C.HERO
    b.t += dt
    if fh.down or fh.dead:
        b.state = "idle"; return
    # hits landing on us now (the browser's job in the real game)
    for m in f.moves():
        t = now - m.start
        for i, h in enumerate(m.data["hits"]):
            if h["k"] == "spawn": continue
            key = f"{m.seq}:{i}" + (f":{int((t - h['t0']) / h['tick'])}" if h.get("tick") else "")
            if key in b.taken: continue
            s = place_hit(m, h, t)
            if s and s["live"] and touches(s, fh.x, fh.y, H["radius"]) and not b.iframes():
                b.taken.add(key); b.hits += 1
                f.hurt(fh.hero.id, {"id": key}, now)
                b.state, b.t = "hurt", 0.0
    for a in list(f.adds.values()):  # adds bite once a second while touching
        if now - a["born"] > 1.0 and math.hypot(a["x"] - fh.x, a["y"] - fh.y) < a["r"] + H["radius"] and not b.iframes():
            key = f"a{a['id']}:{int(now / 2)}"
            if key not in b.taken:
                b.taken.add(key); b.hits += 1; f.hurt(fh.hero.id, {"id": key}, now)
    body = f.nearest_body(fh.x, fh.y)
    near_add = min(f.adds.values(), key=lambda a: math.hypot(a["x"] - fh.x, a["y"] - fh.y), default=None)
    target = ("add", near_add) if near_add and math.hypot(near_add["x"] - fh.x, near_add["y"] - fh.y) < 120 else ("body", body)
    bx, by = (near_add["x"], near_add["y"]) if target[0] == "add" else (body.x, body.y)
    core_i = None
    if target[0] == "body" and body.armored():  # an armoured boss: go for its glowing cores
        live = [i for i, hp in enumerate(body.cores) if hp > 0]
        core_i = min(live, key=lambda i: math.hypot(body.core_pos(i)[0] - fh.x, body.core_pos(i)[1] - fh.y))
        bx, by = body.core_pos(core_i)
    d = math.hypot(bx - fh.x, by - fh.y)
    toward = math.atan2(by - fh.y, bx - fh.x)
    if b.state == "roll":
        R = H["roll"]
        sp = R["dist"] / R["dur"]
        fh.x += math.cos(b.roll_dir) * sp * dt; fh.y += math.sin(b.roll_dir) * sp * dt
        fh.x, fh.y = f.clamp(fh.x, fh.y)
        if b.t >= R["dur"]: b.state, b.t = "idle", 0.0
        return
    if b.state == "hurt":
        if b.t > 0.32: b.state, b.t = "idle", 0.0
        return
    if b.state == "drink":
        if b.t > H["flask"]["dur"]: b.state = "idle"
        return
    # see a hit coming: roll through it (or away), as a player would
    for key, until, long in danger(f, fh.x, fh.y, b.react + 0.15):
        if key in b.decided: continue
        if (until <= 0.12 + b.rng.uniform(-0.05, 0.05) * (1 - b.skill) or until <= 0.05) and b.state in ("idle", "atk"):
            b.decided.add(key)
            if b.rng.random() < b.skill:
                b.state, b.t = "roll", 0.0
                side = b.rng.choice((-1, 1))
                b.roll_dir = toward + math.pi if long else (toward + side * math.pi / 2 if d < 70 else toward + math.pi)
                return
    if b.state == "idle":  # step out of any pool you're standing in, as a player would
        for m in f.moves():
            t = now - m.start
            for h in m.data["hits"]:
                if h["k"] != "zone" or not (h["t0"] - 0.3 <= t <= h["t1"]): continue
                s = place_hit(m, h, max(t, h["t0"]))
                if s and math.hypot(s["cx"] - fh.x, s["cy"] - fh.y) < s["r"] + H["radius"] + 4:
                    a = math.atan2(fh.y - s["cy"], fh.x - s["cx"])
                    fh.x += math.cos(a) * H["speed"] * dt; fh.y += math.sin(a) * H["speed"] * dt
                    fh.x, fh.y = f.clamp(fh.x, fh.y)
                    return
    if b.state == "atk":
        atk = b.W["light"][b.combo]
        if atk["hit"][0] <= b.t and not getattr(b, "landed", False):
            s = place_attack(atk["shape"], fh.x, fh.y, toward)
            r = near_add["r"] if target[0] == "add" else body.d["cores"][core_i]["r"] if core_i is not None else body.d["radius"]
            if touches(s, bx, by, r):
                b.swing += 1
                if target[0] == "add":
                    f.hit_add(fh.hero.id, {"atk": "light", "i": b.combo, "sw": b.swing, "a": near_add["id"]}, now)
                else:
                    f.hit_boss(fh.hero.id, {"atk": "light", "i": b.combo, "sw": b.swing, "e": body.e, "core": core_i}, now)
                b.landed = True
        if b.t >= atk["dur"]:
            b.combo = (b.combo + 1) % len(b.W["light"])
            b.state, b.t = "idle", 0.0
        return
    # revive a fallen friend close by
    fallen = [o.fh for o in bots if o.fh.down and not o.fh.dead and o is not b]
    if fallen:
        o = min(fallen, key=lambda q: math.hypot(q.x - fh.x, q.y - fh.y))
        od = math.hypot(o.x - fh.x, o.y - fh.y)
        if od < 28:
            b.revive_t += dt
            if b.revive_t >= H["down"]["revive"]:
                f.revive(fh.hero.id, o.hero.id, now); b.revive_t = 0
            return
        if od < 200:
            a = math.atan2(o.y - fh.y, o.x - fh.x)
            fh.x += math.cos(a) * H["speed"] * dt; fh.y += math.sin(a) * H["speed"] * dt
            return
    if fh.hero.hp < fh.hero.mhp() * 0.4 and fh.hero.flasks > 0 and (d > 90 or not body.move):
        f.drink(fh.hero.id, now); b.state, b.t = "drink", 0.0
        return
    busy = body.move is not None and now - body.move.start < body.move.data["dur"] * 0.6
    if d > (22 if core_i is not None else 34):
        fh.x += math.cos(toward) * H["speed"] * dt; fh.y += math.sin(toward) * H["speed"] * dt
    elif (target[0] == "add" or not busy or b.rng.random() < 0.02 * (1 - b.skill)) and b.state == "idle":
        b.state, b.t, b.landed = "atk", 0.0, False
    fh.x, fh.y = f.clamp(fh.x, fh.y)


# how many Bonfires a run has passed before meeting a boss of each tier (two bosses a tier)
STAGE = {1: 1, 2: 3, 3: 5, 4: 6}


def level_up(h, n, rng, size):
    """Give a bot hero the levels and blessings a run gives by then: a point and a pick a Bonfire."""
    from app.kingfall.content.upgrades import UPGRADES, offer
    for k in range(n):
        h.level += 1
        h.attrs[rng.choice(("vig", "vig", "end", "mig", "fin"))] += 1
        cards = offer(h, size, rng, k + 1)
        if cards:
            uid, rarity = cards[0]
            slot = UPGRADES[uid]["slot"]
            if slot: h.ups = [(u, r) for u, r in h.ups if UPGRADES[u]["slot"] != slot]
            h.ups.append((uid, rarity))
    h.changed(); h.hp = h.mhp(); h.flasks = h.max_flasks()


def fight_once(boss, size, skill, seed, limit=900):
    rng = random.Random(seed)
    random.seed(seed)
    heroes = [Hero(i + 1, None, i, f"Bot{i + 1}", "knight", "sword", i) for i in range(size)]
    for h in heroes: level_up(h, STAGE[C.BOSSES[boss].get("tier", 1)] - 1 + rng.randint(0, 1), rng, size)
    st = Stub()
    f = Fight(st, boss, heroes, 0.0)
    bots = [Bot(fh, skill, rng) for fh in f.heroes.values()]
    now = 0.0
    while now < limit and f.over is None:
        f_now[0] = now
        f.tick(now)
        for b in bots: step_bot(b, f, now, TICK, bots)
        now += TICK
    return {"won": f.over == "won", "time": now, "hits": sum(b.hits for b in bots) / size,
            "downs": st.events.count("down"), "staggers": st.events.count("stagger"), "phase": f.phase, "hp": f.hp / f.mhp}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("boss", nargs="?", default=None)
    ap.add_argument("n", nargs="?", type=int, default=20)
    ap.add_argument("--size", type=int, default=0)
    ap.add_argument("--skill", type=float, default=0.8)
    ap.add_argument("--fast", action="store_true", help="a quick run for tools/check-all.sh")
    a = ap.parse_args()
    bosses = [a.boss] if a.boss else list(C.BOSSES)
    sizes = [a.size] if a.size else [1, 2, 3, 4]
    n = 2 if a.fast else a.n
    bad = False
    for boss in bosses:
        for size in sizes:
            rs = [fight_once(boss, size, a.skill, s) for s in range(n)]
            w = sum(r["won"] for r in rs) / n
            t = sum(r["time"] for r in rs) / n
            print(f"{boss:12} party {size}  won {w * 100:5.1f}%  {t / 60:4.1f} min  hits/hero {sum(r['hits'] for r in rs) / n:5.1f}  "
                  f"downs {sum(r['downs'] for r in rs) / n:4.1f}  staggers {sum(r['staggers'] for r in rs) / n:4.1f}  "
                  f"boss hp left {sum(r['hp'] for r in rs) / n * 100:4.0f}%  reached phase 2 {sum(r['phase'] == 2 for r in rs)}/{n}")
            if any(r["time"] >= 899 for r in rs): bad = True
    if bad:
        print("a fight hit the time limit: the boss or the bots are stuck"); sys.exit(1)


if __name__ == "__main__":
    main()
