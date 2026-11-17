#!/usr/bin/env python3
"""Kingfall's balance sim: bot parties fight bosses on the real server code (app/kingfall/fight.py), in
simulated time. Bots read each move's data the way a player reads its wind-up: they see a hit coming
`react` seconds before it lands and roll through it with probability `skill`, attack in openings,
drink when low and revive the fallen.

    python3 tools/kingfall-sim.py                     all bosses, parties of 1-4, 20 fights each
    python3 tools/kingfall-sim.py corvin 40 --size 2   one boss, 40 fights, parties of 2
    python3 tools/kingfall-sim.py --skill 0.6         weaker bots (default 0.8)
    python3 tools/kingfall-sim.py --weapon bow        every bot carries a bow (default sword; or 'mixed')
    python3 tools/kingfall-sim.py "" 8 --weapons      the weapons table: each weapon alone and paired, mixed 3s and 4s

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
from app.kingfall.geom import active, place_attack, place_hit, spared, touches  # noqa: E402
from app.kingfall.room import Hero  # noqa: E402
from app.kingfall.content.skills import MAX_SKILLS, SKILLS  # noqa: E402


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
        self.W = W = fh.hero.build().weapon(fh.hero.weapon)   # with what its blessings change in it
        first = W["light"][0]
        self.ranged = "proj" in first
        # how close it stands to fight: inside its first light attack's reach, or well back with a bow or catalyst
        self.stand = (min(150, first["proj"]["v"] * first["proj"]["life"] * 0.7) if self.ranged   # never beyond what its shots reach (the chakrams fly 175 px)
                      else (first["shape"]["r"] if first["shape"]["k"] == "arc" else first["shape"]["x1"] * 0.9) * 0.8)
        # its dodge: a roll, the daggers' dash or the catalyst's blink (each spends one of the weapon's dashes)
        G, R = W["guard"], C.HERO["roll"]
        self.dodge = ({"dur": G["dur"], "dist": G["dist"], "if": (0.0, G["dur"]), "cost": G.get("cost", 1)} if G["kind"] == "dash"
                      else {"dur": 0.16, "dist": G["dist"], "if": (0.0, 0.16), "blink": True} if G.get("dodge", G["kind"]) == "blink"
                      else {"dur": R["dur"], "dist": R["dist"], "if": R["iframes"]})
        st = fh.hero.build().stats   # dashes, as in the game: the weapon's count and recharge, and what the build changes
        self.max_dash = W["dodge"]["charges"] + st["dash_charges"]
        self.dashes = float(self.max_dash)
        self.dash_rate = st["dash_regen"] / (W["dodge"]["recharge"] * st["dash_time"])
        self.act = None    # the attack being made: (kind, its data, when it lands, when it ends)
        self.cd = {}       # skill id -> when it's ready again
        self.focus = 40.0
        self.moving = False
        self.grp = {}
        # the second six weapons (content/weapons.py): a streak, discs or rounds, played roughly as a player would
        self.streak = 0
        self.ammo = W["ammo"]["max"] if W.get("ammo") else 0
        self.discs = []     # when each thrown chakram is back in hand
        self.primed = False

    def iframes(self):
        a, b = self.dodge["if"]
        return self.state == "roll" and a <= self.t <= b


def danger(f, x, y, ahead):
    """Hits about to land on (x, y) within `ahead` seconds: [(key, seconds until)]."""
    out = []
    for m in f.moves():
      t = f_now[0] - m.start
      for i, h in enumerate(m.data["hits"]):
        if h["k"] == "spawn" or not active(m, h, i): continue
        if h.get("room") or "cover" in h or h.get("abs"): continue   # signature hits: answered by where you stand (answer_signature), not by rolling
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


def answer_signature(b, f, now, dt):
    """A signature hit is coming (a blast across the arena, a strip of it, a beam with cover): do what
    it asks, as a player would. Returns True if the bot is busy with that this tick."""
    fh, H = b.fh, C.HERO
    for m in f.moves():
        t = now - m.start
        for i, h in enumerate(m.data["hits"]):
            if not (h.get("room") or "cover" in h or h.get("abs")) or not active(m, h, i) or t > h["t1"]: continue
            key = f"sig{m.seq}:{i}"
            if key not in b.decided:
                b.decided.add(key)
                if b.rng.random() > 0.5 + 0.5 * b.skill: b.decided.add(key + "x")   # now and then it doesn't read it in time
            if key + "x" in b.decided: continue
            left = h["t0"] - t
            ox, oy = m.pos(m.start + h["t0"])
            goal = None
            if h.get("abs"):   # a strip of the arena: step out of it sideways
                if left > h.get("mark", 0.6): continue
                sh = place_hit(m, h, h["t0"])
                if not touches(sh, fh.x, fh.y, H["radius"] + 8): continue
                side = -math.sin(sh["a"]) * (fh.x - sh["cx"]) + math.cos(sh["a"]) * (fh.y - sh["cy"])
                a = sh["a"] + (math.pi / 2 if side >= 0 else -math.pi / 2)
                goal = (fh.x + math.cos(a) * 30, fh.y + math.sin(a) * 30)
            elif h.get("still"):
                if left < 0.4: return True   # stand still
                continue
            elif "near" in h:
                if math.hypot(fh.x - ox, fh.y - oy) > h["near"] - 14: goal = (ox, oy)
            else:
                spots = [q for q in m.c.get("spots", []) if q[3] == (m.c.get("v") if h.get("safe") == "v" else h.get("safe", h.get("cover")))]
                on = [q for q in spots if q[4]]
                if not spots: continue   # nowhere to stand: only breaking the move off will do (the bot keeps attacking)
                if not on:               # candles to light first: go to the nearest and strike it
                    q = min(spots, key=lambda q: math.hypot(q[0] - fh.x, q[1] - fh.y))
                    if math.hypot(q[0] - fh.x, q[1] - fh.y) > 34: goal = (q[0], q[1])
                else:
                    q = min(on, key=lambda q: math.hypot(q[0] - fh.x, q[1] - fh.y))
                    if "cover" in h:
                        d = max(1.0, math.hypot(q[0] - ox, q[1] - oy))
                        goal = (q[0] + (q[0] - ox) / d * (q[2] + 14), q[1] + (q[1] - oy) / d * (q[2] + 14))
                    else:
                        goal = (q[0], q[1])
                    far = math.hypot(goal[0] - fh.x, goal[1] - fh.y)
                    if far < 5:
                        if left < 1.0 or "cover" in h and not h.get("room"): return True   # there: wait for it
                        continue
                    if left > far / H["speed"] + 1.0 and h.get("room"): continue   # time to fight on a little longer
            if goal:
                a = math.atan2(goal[1] - fh.y, goal[0] - fh.x)
                step = min(H["speed"] * dt, math.hypot(goal[0] - fh.x, goal[1] - fh.y))
                fh.x, fh.y = f.clamp(fh.x + math.cos(a) * step, fh.y + math.sin(a) * step)
                b.state, b.act = "idle", None
                return True
    return False


def step_bot(b, f, now, dt, bots):
    """One tick of a bot. A bot that's held (a tongue, a chain) can strike but not move or dodge."""
    fh = b.fh
    x, y = fh.x, fh.y
    _step_bot(b, f, now, dt, bots)
    if fh.held > now:
        fh.x, fh.y = x, y
        if b.state == "roll": b.state, b.t = "idle", 0.0
    b.moving = abs(fh.x - x) + abs(fh.y - y) > 0.01


def _step_bot(b, f, now, dt, bots):
    fh, H = b.fh, C.HERO
    b.t += dt
    if fh.down or fh.dead:
        b.state = "idle"; return
    # hits landing on us now (the browser's job in the real game)
    for m in f.moves():
        t = now - m.start
        for i, h in enumerate(m.data["hits"]):
            if h["k"] == "spawn" or not active(m, h, i): continue
            key = f"{m.seq}:{i}" + (f":{int((t - h['t0']) / h['tick'])}" if h.get("tick") else "")
            if key in b.taken: continue
            grp = (m.seq, h["grp"]) if "grp" in h else None   # one sweep of a turning beam hurts once a while, not at every step
            if grp and now - b.grp.get(grp, -9) < 0.9: continue
            s = place_hit(m, h, t)
            if s and s["live"] and touches(s, fh.x, fh.y, H["radius"]) and not b.iframes() and not spared(m, h, fh.x, fh.y, b.moving):
                if grp: b.grp[grp] = now
                b.taken.add(key)
                if now < fh.guard_until and not h.get("room"):   # Stone Ward soaks it and answers
                    f.hurt(fh.hero.id, {"id": key, "ward": 1}, now)
                    b.cd["ward"] = b.cd.get("ward", now) - SKILLS["ward"]["cd"] * SKILLS["ward"]["refund"]
                    body0 = f.nearest_body(fh.x, fh.y)
                    if math.hypot(body0.x - fh.x, body0.y - fh.y) <= SKILLS["ward"]["burst_r"] + body0.d["radius"]:
                        b.swing += 1
                        f.hit_boss(fh.hero.id, {"atk": "skill", "sk": "ward", "sub": "burst", "sw": b.swing, "e": body0.e}, now)
                    continue
                b.hits += 1
                f.hurt(fh.hero.id, {"id": key}, now)
                b.state, b.t = "hurt", 0.0
                b.streak = int(b.streak * b.W.get("streak", {}).get("keep", 0))   # a hit taken ends a streak
    for a in list(f.adds.values()):  # adds bite once a second while touching
        if a["dmg"] and now - a["born"] > 1.0 and math.hypot(a["x"] - fh.x, a["y"] - fh.y) < a["r"] + H["radius"] and not b.iframes():
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
    G = b.W["guard"]
    b.dashes = min(b.max_dash, b.dashes + b.dash_rate * dt)
    if b.state == "roll":
        R = b.dodge
        if not R.get("blink"):
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
    if b.state in ("idle", "atk") and answer_signature(b, f, now, dt): return
    # see a hit coming: roll through it (or away), as a player would
    for key, until, long in danger(f, fh.x, fh.y, b.react + 0.15):
        if key in b.decided: continue
        if (until <= 0.12 + b.rng.uniform(-0.05, 0.05) * (1 - b.skill) or until <= 0.05) and b.state in ("idle", "atk"):
            b.decided.add(key)
            if b.rng.random() < b.skill:
                cost = b.dodge.get("cost", 1)   # the gauntlets' weave costs half a dash
                if b.dashes < cost: continue   # out of dashes: it takes the hit
                b.dashes -= cost
                b.state, b.t, b.act = "roll", 0.0, None
                side = b.rng.choice((-1, 1))
                b.roll_dir = toward + math.pi if long else (toward + side * math.pi / 2 if d < 70 else toward + math.pi)
                if b.dodge.get("blink"):   # a blink is there at once: go where nothing is about to land, as a player would
                    spots = [f.clamp(fh.x + math.cos(a) * b.dodge["dist"], fh.y + math.sin(a) * b.dodge["dist"])
                             for a in (b.roll_dir, toward + math.pi, toward + math.pi / 2, toward - math.pi / 2, toward + 2.4, toward - 2.4)]
                    fh.x, fh.y = next((p for p in spots if not danger(f, p[0], p[1], 0.6)), spots[0])
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
        if b.act and not b.landed and b.t >= b.act[2]:
            b.landed = True
            land(b, f, now, target, body, near_add, core_i, bx, by, d, toward)
        if b.t >= (b.act[3] if b.act else 0.4):
            if b.act and b.act[0] == "light": b.combo = (b.combo + 1) % len(b.W["light"])
            b.state, b.t, b.act = "idle", 0.0, None
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
    if b.state == "idle" and use_skill(b, f, now, d, body, target, bots): return
    stand = min(b.stand, 22) if core_i is not None and not b.ranged else b.stand
    if target[0] == "body" and core_i is None: stand = max(stand, body.d["radius"] + 12)   # a very short weapon (the gauntlets) still can't stand inside the boss
    if b.ranged and d < 80 and target[0] == "body":   # archers and casters back away
        fh.x -= math.cos(toward) * H["speed"] * dt; fh.y -= math.sin(toward) * H["speed"] * dt
    elif d > stand + (20 if b.ranged else 0):
        fh.x += math.cos(toward) * H["speed"] * dt; fh.y += math.sin(toward) * H["speed"] * dt
    elif (target[0] == "add" or b.ranged or not busy or b.rng.random() < 0.02 * (1 - b.skill)) and b.state == "idle":
        W, sp, hv = b.W, b.W["special"], b.W["heavy"]
        kind, atk, at = "light", W["light"][b.combo], 0.0
        A = W.get("ammo")
        if A and atk.get("ammo"):
            b.discs = [t for t in b.discs if t > now]
            if "reload" in A and b.ammo < 1:   # the cannon is empty: reload (a bot times the quick reload about as well as it reads a dodge)
                quick = b.rng.random() < b.skill * 0.7
                b.ammo, b.primed = A["max"], quick
                b.state, b.t, b.act, b.landed = "atk", 0.4 - (A["window"][0] + 0.1 if quick else A["reload"]), None, True
                return
            if "reload" not in A and len(b.discs) >= A["max"]:   # both chakrams are away: a punch that does next to nothing, and wait
                b.state, b.t, b.act, b.landed = "atk", 0.15, None, True
                return
        if target[0] == "body":
            left = body.until - now if body.state == "stagger" else 0.0
            if left > hv["charge"] + hv["hit"][0] + 0.1 and fh.hero.id not in body.crit_by and reach(hv) + body.d["radius"] >= d:
                kind, atk, at = "heavy", hv, hv["charge"]   # a staggered boss: wind up the charged heavy for the critical
            elif b.focus >= sp["focus"] and reach(sp) + body.d["radius"] >= d and (not b.ranged or d > 90):
                kind, atk = "special", sp
                b.focus -= sp["focus"]
        quick = 1 + W["streak"]["speed"] * b.streak if kind == "light" and W.get("streak") else 1.0   # a streak quickens the fists
        b.act = (kind, atk, at + atk["hit"][0] / quick, at + atk["dur"] / quick)
        b.state, b.t, b.landed = "atk", 0.0, False
    fh.x, fh.y = f.clamp(fh.x, fh.y)


def reach(atk):
    """How far an attack reaches from where the hero stands, counting its lunge, leap or blink."""
    far = max(0, atk.get("step", 0)) + atk.get("blink", 0)
    if "proj" in atk: return atk["proj"]["v"] * atk["proj"]["life"] * 0.8
    if "aoe" in atk: return atk["aoe"]["at"] + atk["aoe"]["r"]
    sh = atk["shape"]
    return far + (sh["x1"] if sh["k"] == "rect" else sh["r"] + sh.get("x", 0))


def land(b, f, now, target, body, near_add, core_i, bx, by, d, toward):
    """A bot's attack reaches its moment: report what it hit, as a browser would. Lights are checked
    against their real shape; a heavy or special by its reach; arrows and bolts hit what's in range (a
    volley lands more of its shots up close); a called-down area lands about half its ticks."""
    fh = b.fh
    kind, atk = b.act[0], b.act[1]
    r = near_add["r"] if target[0] == "add" else body.d["cores"][core_i]["r"] if core_i is not None else body.d["radius"]
    A, extra = b.W.get("ammo"), {}
    if A and atk.get("ammo") and kind == "light":
        if "reload" in A: b.ammo -= 1
        else: b.discs.append(now + 0.9)
        if b.primed or ("reload" not in A and b.rng.random() < b.skill * 0.6): extra["ch"] = 1   # a timed reload; a disc caught (bots stand where it returns)
        b.primed = False
    if kind == "heavy" and b.W["heavy"].get("spend") and b.streak: extra["sk"] = b.streak
    if "proj" in atk:
        n = atk["proj"].get("n", 1)
        hits = 0 if d > reach(atk) + r else 1 if n == 1 or d > 90 else 2 if d > 45 else n
        if hits and atk["proj"].get("disc") and atk["proj"].get("pierce"): hits *= 2   # a chakram cuts on its way out and on its way back
    elif "aoe" in atk:
        hits = (atk["aoe"]["ticks"] + 1) // 2 if abs(d - atk["aoe"]["at"]) < atk["aoe"]["r"] + r else 0
    elif kind == "light":
        hits = 1 + len(atk.get("more", ())) if touches(place_attack(atk["shape"], fh.x, fh.y, toward), bx, by, r) else 0   # `more`: a double jab
    else:
        hits = 1 if d <= reach(atk) + r else 0
        if hits and (atk.get("step", 0) > 40 or atk.get("blink")):   # a leap or a blink carries the hero to the target
            k = max(0.0, d - 30)
            fh.x, fh.y = f.clamp(fh.x + math.cos(toward) * k, fh.y + math.sin(toward) * k)
    for _ in range(hits):
        b.swing += 1
        msg = {"atk": kind, "i": b.combo, "c": 1.0, "sw": b.swing, **extra}
        if target[0] == "add":
            f.hit_add(fh.hero.id, {**msg, "a": near_add["id"]}, now)
        else:
            f.hit_boss(fh.hero.id, {**msg, "e": body.e, "core": core_i}, now)
            mult = atk["mult"][1] if isinstance(atk["mult"], tuple) else atk["mult"]
            if kind != "special": b.focus = min(100.0, b.focus + b.W["base"] * mult * C.HERO["focus_per_dmg"])
    if hits and target[0] != "add":
        st = b.W.get("streak")
        if st: b.streak = 0 if extra.get("sk") else min(st["max"], b.streak + hits)
        if atk.get("proj", {}).get("hook"):   # the sickle bites: the chain pulls the bot in to cut
            k = max(0.0, d - 30)
            fh.x, fh.y = f.clamp(fh.x + math.cos(toward) * k, fh.y + math.sin(toward) * k)
            b.swing += 1
            f.hit_boss(fh.hero.id, {"atk": "move", "m": "reap", "sw": b.swing, "e": body.e, "core": core_i}, now)
        if atk.get("plant"): f.plant(fh.hero.id, {"x": fh.x, "y": fh.y}, now)   # the standard stays where it was slammed down
    # What upgrades hang on this strike (content/upgrades.py, `proc`): a rough count, as for skills. One
    # hit (two ticks of a pool) if the attack landed. Roll, guard, flask and perfect-dodge procs aren't played.
    if hits and target[0] != "add":
        whens = {"light": ["finisher"] if b.combo == len(b.W["light"]) - 1 else [], "heavy": ["heavy", "heavy_full"], "special": ["special"]}.get(kind, [])
        for P in fh.hero.build().get("proc"):
            if P["when"] not in whens: continue
            for _ in range(2 if P.get("aoe", {}).get("ticks", 1) > 1 else 1):
                b.swing += 1
                f.hit_boss(fh.hero.id, {"atk": "proc", "p": P["uid"], "sw": b.swing, "e": body.e, "core": core_i}, now)


def use_skill(b, f, now, d, body, target, bots):
    """A bot uses a skill that's ready when it would do some good, roughly as a player would: damage
    skills when the boss is in their reach (how many of a skill's hits land is an estimate), a heal when
    hurt, a ward or a cry as the fight is joined. True if one was used (the bot stands a moment)."""
    fh = b.fh
    reach = body.d["radius"]
    for sid in fh.hero.skills:
        if b.cd.get(sid, 0) > now: continue
        s = SKILLS[sid]
        hits = 0
        if "trance" in s: continue   # bots get none of its speed and all of its cost: they leave it
        if "cost" in s and (fh.hero.hp < fh.hero.mhp() * 0.7 or b.focus > 40): continue   # Blood Pact: only when well and short of Focus
        if "focus" in s and "mult" not in s: b.focus = min(100.0, b.focus + s["focus"])
        if "mult" in s:
            if target[0] != "body" or body.untouchable(now): continue
            if "proj" in s:
                if d > 220: continue
                hits = 1 if s["proj"].get("n", 1) == 1 else (3 if d < 60 else 2)
            elif "shape" in s:
                sh = s["shape"]
                if d > (sh["x1"] if sh["k"] == "rect" else sh["r"] + sh.get("x", 0)) + reach - 6: continue
                hits = 1
            else:
                A = s["aoe"]
                if d > (A.get("range") or A["at"]) + A["r"] + reach - 10: continue
                hits = A["ticks"] if A["ticks"] <= 3 else A["ticks"] // 2   # a lingering cloud: the boss walks out of it
                if "wave" in s: hits += 1   # a line of eruptions: a big boss stands on two
                if A["delay"] > 0.4 and body.move is None and b.rng.random() > b.skill: hits = 0  # a slow pillar can miss a walking boss
        elif s.get("zone", {}).get("heal"):   # hallowed ground: when someone near is hurt (and then it stands in it, as bots stand anyway)
            if not any(o.fh.hero.hp < o.fh.hero.mhp() * 0.6 for o in bots if not o.fh.down and math.hypot(o.fh.x - fh.x, o.fh.y - fh.y) <= s["zone"]["r"]): continue
        elif "guard" in s:   # the ward: as a hit is about to land (a bot reads it about as well as it reads a dodge)
            if not danger(f, fh.x, fh.y, 0.5) or b.rng.random() > b.skill: continue
        elif "dashes" in s:
            if b.dashes >= 1: continue
            b.dashes = b.max_dash
        elif d > 90: continue   # a banner or a charged hit: as the fight is joined
        f.use_skill(fh.hero.id, {"sk": sid}, now)
        b.cd[sid] = now + s["cd"] * fh.hero.build().stats["skill_cd"]
        if s.get("zone", {}).get("at") == "aoe": f.zone_at(fh.hero.id, {"sk": sid, "x": body.x, "y": body.y}, now)
        for _ in range(hits):
            b.swing += 1
            f.hit_boss(fh.hero.id, {"atk": "skill", "sk": sid, "sw": b.swing, "e": body.e}, now)
            if s.get("cdhit"): b.cd[sid] -= s["cdhit"]
        # a skill's further hits, roughly: two ticks of a lance's burning trail, two of the knives on their way back
        for sub, n in (("trail", 2), ("back", 2)):
            for _ in range(n if hits and sub in s.get("sub", {}) else 0):
                b.swing += 1
                f.hit_boss(fh.hero.id, {"atk": "skill", "sk": sid, "sub": sub, "sw": b.swing, "e": body.e}, now)
        if s.get("instant"): return False   # cast on the move: it doesn't cost the bot its swing
        b.state, b.t, b.landed, b.combo, b.act = "atk", 0.0, True, 0, None   # the cast takes about as long as a swing
        return True
    return False


# how many Bonfires a run has passed before meeting a boss of each tier (two bosses a tier)
STAGE = {1: 1, 2: 3, 3: 5, 4: 6}


def level_up(h, n, rng, size):
    """Give a bot hero the levels and blessings a run gives by then: a point and a pick a Bonfire."""
    from app.kingfall.content.upgrades import UPGRADES, offer
    h.skills = [rng.choice(list(SKILLS))]   # the starting skill, then one learned at each Bonfire up to two
    for k in range(n):
        if len(h.skills) < MAX_SKILLS: h.skills.append(rng.choice([x for x in SKILLS if x not in h.skills]))
        h.level += 1
        # points go mostly into one attribute, as a player after its second trait would put them, the rest anywhere
        # (leaning to Vigor, as bots always have: with less health they simply lose more)
        if k == 0: h.calling = rng.choice(("vig", "vig", "end", "mig", "fin"))
        h.attrs[h.calling if rng.random() < 0.6 else rng.choice(("vig", "vig", "end", "mig", "fin"))] += 1
        cards = offer(h, size, rng, k + 1)
        if cards:
            uid, rarity = cards[0]
            slot = UPGRADES[uid]["slot"]
            if slot: h.ups = [(u, r) for u, r in h.ups if UPGRADES[u]["slot"] != slot]
            h.ups.append((uid, rarity))
    h.changed(); h.hp = h.mhp(); h.flasks = h.max_flasks()


WEAPONS = list(C.WEAPONS)


def fight_once(boss, size, skill, seed, limit=900, weapon="sword"):
    """One fight. `weapon`: every bot carries it, or "mixed" for a different weapon each (which ones
    turns with the seed)."""
    rng = random.Random(seed)
    random.seed(seed)
    carry = [WEAPONS[(seed + i * 5) % len(WEAPONS)] if weapon == "mixed" else weapon for i in range(size)]
    heroes = [Hero(i + 1, None, i, f"Bot{i + 1}", "knight", carry[i], i) for i in range(size)]
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
    ap.add_argument("--weapon", default="sword", help="what the bots carry: a weapon's id, or 'mixed'")
    ap.add_argument("--weapons", action="store_true", help="the weapons table: each weapon alone and in a pair, and mixed parties of 3 and 4")
    a = ap.parse_args()
    if a.weapons: return weapons_table(a)
    bosses = [a.boss] if a.boss else list(C.BOSSES)
    sizes = [a.size] if a.size else [1, 2, 3, 4]
    n = 2 if a.fast else a.n
    bad = False
    for boss in bosses:
        for size in sizes:
            rs = [fight_once(boss, size, a.skill, s, weapon=a.weapon) for s in range(n)]
            w = sum(r["won"] for r in rs) / n
            t = sum(r["time"] for r in rs) / n
            print(f"{boss:12} party {size}  won {w * 100:5.1f}%  {t / 60:4.1f} min  hits/hero {sum(r['hits'] for r in rs) / n:5.1f}  "
                  f"downs {sum(r['downs'] for r in rs) / n:4.1f}  staggers {sum(r['staggers'] for r in rs) / n:4.1f}  "
                  f"boss hp left {sum(r['hp'] for r in rs) / n * 100:4.0f}%  reached phase 2 {sum(r['phase'] == 2 for r in rs)}/{n}")
            if any(r["time"] >= 899 for r in rs): bad = True
    if a.fast:  # every weapon gets a fight or two, so none can break unnoticed
        for i, w in enumerate(WEAPONS):
            for boss in (list(C.BOSSES)[i % len(C.BOSSES)], list(C.BOSSES)[(i + 6) % len(C.BOSSES)]):
                r = fight_once(boss, 1 + i % 2, a.skill, i, weapon=w)
                print(f"{boss:12} {w:10} party {1 + i % 2}  {'won' if r['won'] else 'lost'}  {r['time'] / 60:4.1f} min")
                if r["time"] >= 899: bad = True
    if bad:
        print("a fight hit the time limit: the boss or the bots are stuck"); sys.exit(1)


def weapons_table(a):
    """Win % for each weapon (every bot carrying it) alone / in a pair, then mixed parties of 3 / 4,
    against each boss; then each weapon's averages. `n` fights a cell."""
    bosses = [a.boss] if a.boss else list(C.BOSSES)
    cols = [(w, (1, 2)) for w in WEAPONS] + [("mixed", (3, 4))]
    tot = {w: [0, 0, 0.0, 0.0] for w, _ in cols}   # wins, fights, minutes, staggers
    print(f"{'':12}" + "".join(f"{w:>12}" for w, _ in cols))
    for boss in bosses:
        row = f"{boss:12}"
        for w, sizes in cols:
            cell = []
            for size in sizes:
                rs = [fight_once(boss, size, a.skill, s, weapon=w) for s in range(a.n)]
                cell.append(round(100 * sum(r["won"] for r in rs) / a.n))
                t = tot[w]
                t[0] += sum(r["won"] for r in rs); t[1] += a.n; t[2] += sum(r["time"] for r in rs) / 60; t[3] += sum(r["staggers"] for r in rs)
            row += f"{'/'.join(map(str, cell)):>12}"
        print(row, flush=True)
    print(f"{'won %':12}" + "".join(f"{100 * tot[w][0] / tot[w][1]:>12.0f}" for w, _ in cols))
    print(f"{'minutes':12}" + "".join(f"{tot[w][2] / tot[w][1]:>12.1f}" for w, _ in cols))
    print(f"{'staggers':12}" + "".join(f"{tot[w][3] / tot[w][1]:>12.1f}" for w, _ in cols))


if __name__ == "__main__":
    main()
