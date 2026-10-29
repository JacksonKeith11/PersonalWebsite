"""Yet more Board Brawl minigames, the server's half: games the owner's friends named in a Reddit
thread of favourite Mario Party minigames. Only the board is Halloween; these keep a plain look,
close to the games they're based on (named in each class's docstring).
"""

import math
import random

from .arcade import Survival
from .minigames import ArenaGame, Disc, Minigame, Scripted, _nums, _r


# ---------------------------------------------------------------- Say Cheese! (Slaparazzi)


class SayCheese(ArenaGame):
    """Slaparazzi (Super Mario Party): get yourself in the photo; shove everyone else out of it."""
    key, name = "cheese", "Say Cheese!"
    rules = "A photographer takes four pictures. Be inside the frame when the shutter clicks: 1 point, or 3 if you're in the middle. Shove people out of shot. Most points wins."
    controls = "WASD or arrows to move, Space to dash (shove)."
    dur = 30.0
    WALLS = True
    SHOTS = [7.0, 14.0, 21.0, 28.0]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.frames = []
        for i in range(len(self.SHOTS)):
            w, h = 36 - i * 3, 28 - i * 2.5
            self.frames.append({"x": random.uniform(10 + w / 2, 90 - w / 2), "y": random.uniform(10 + h / 2, 90 - h / 2),
                                "w": w, "h": h})
        self.i = 0
        self.points = {pid: 0 for pid in self.ids}
        self.last = None  # the last photo: {"i", "got": {pid: points}}

    def scored(self, d, f):
        if abs(d.x - f["x"]) > f["w"] / 2 or abs(d.y - f["y"]) > f["h"] / 2:
            return 0
        return 3 if math.hypot(d.x - f["x"], d.y - f["y"]) < min(f["w"], f["h"]) * 0.22 else 1

    def after_move(self, live, dt):
        if self.i < len(self.SHOTS) and self.t >= self.SHOTS[self.i]:
            f = self.frames[self.i]
            got = {}
            for d in live:
                p = self.scored(d, f)
                if p:
                    got[str(d.pid)] = p
                    self.points[d.pid] += p
            self.last = {"i": self.i, "got": got, "frame": f}
            self.i += 1

    def bot_tick(self, dt):
        if self.i >= len(self.SHOTS):
            return
        f = self.frames[self.i]
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if d.think > 0:
                continue
            d.think = random.uniform(0.12, 0.25)
            if d.goal is None or d.goal[0] != self.i:
                d.goal = (self.i, random.uniform(-3, 3), random.uniform(-3, 3))
            tx, ty = f["x"] + d.goal[1], f["y"] + d.goal[2]
            near = [o for o in self.discs.values() if o is not d and math.hypot(o.x - d.x, o.y - d.y) < 11]
            if near and random.random() < 0.25 and self.SHOTS[self.i] - self.t < 3:
                o = near[0]
                self.steer(d, o.x, o.y, 0.05)
                d.dash_req = True
            elif math.hypot(tx - d.x, ty - d.y) < 2:
                d.ix = d.iy = 0.0
            else:
                self.steer(d, tx, ty, 0.12)

    def snap(self):
        s = super().snap()
        if self.i < len(self.SHOTS):
            s["frame"] = {**{k: _r(v) for k, v in self.frames[self.i].items()}, "in": _r(self.SHOTS[self.i] - self.t)}
        s["last"] = self.last
        s["pts"] = {str(k): v for k, v in self.points.items()}
        return s

    def key_of(self, pid):
        return -self.points[pid]

    def team_key(self, team):
        return -sum(self.points[p] for p in team)

    def label(self, pid):
        return f"{self.points[pid]} point{'s' if self.points[pid] != 1 else ''}"


# ---------------------------------------------------------------- Tick Tock Hop


class TickTockHop(Survival, Minigame):
    """Tick Tock Hop (Mario Party 3): stand on a clock face and jump the hands as they sweep by."""
    key, name = "ticktock", "Tick Tock Hop"
    rules = "You're standing on a clock. Jump over the hands as they sweep round. They speed up, a second hand joins in, and they change direction. Get hit and you're out."
    controls = "Space, or click, to jump."
    hz = 20
    dur = 60.0
    AIR, GRACE, MARGIN = 0.55, 0.15, 0.09

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        n = len(self.ids)
        self.angle = {p: 2 * math.pi * (i + 0.5) / n - math.pi / 2 for i, p in enumerate(self.ids)}
        self.hands = [{"a": -math.pi / 2, "w": 1.5, "on": True, "flip": random.uniform(6, 10)},
                      {"a": math.pi / 2, "w": -1.1, "on": False, "flip": random.uniform(16, 22)}]
        self.air_until = {p: -1.0 for p in self.ids}
        self.pending = {}  # pid -> when a hand reached them; a jump just after still saves them
        self.out_at = {}
        self.react = {p: random.uniform(0.12, 0.3) for p in self.bots}
        self.params = {"angle": {str(k): _r(v) for k, v in self.angle.items()}}

    def alive_ids(self):
        return [p for p in self.ids if p not in self.out_at]

    def jump(self, pid):
        if pid in self.out_at or self.t < self.air_until[pid] + 0.08:
            return
        self.air_until[pid] = self.t + self.AIR
        if pid in self.pending and self.t - self.pending[pid] <= self.GRACE:
            del self.pending[pid]  # they jumped in time; the message was just late

    def on(self, pid, msg):
        if msg.get("t") == "jump" and pid not in self.bots:
            self.jump(pid)

    def ahead(self, h, p):
        """How far (radians) hand h has to turn to reach angle p."""
        d = (p - h["a"]) if h["w"] > 0 else (h["a"] - p)
        return d % (2 * math.pi)

    def tick(self, dt):
        self.t += dt
        speed = 1 + self.t / 25
        for h in self.hands:
            if not h["on"]:
                if self.t >= 12:
                    h["on"] = True
                continue
            if self.t >= h["flip"]:
                h["w"] = -h["w"]
                h["flip"] = self.t + random.uniform(5, 9)
            w = h["w"] * speed
            sweep = abs(w) * dt
            for p in self.alive_ids():
                if self.t < self.air_until[p] or p in self.pending:
                    continue
                if (self.ahead(h, self.angle[p]) + self.MARGIN) % (2 * math.pi) <= sweep + 2 * self.MARGIN:
                    self.pending[p] = self.t
            h["a"] = (h["a"] + w * dt) % (2 * math.pi)
        for p, at in list(self.pending.items()):
            if self.t - at > self.GRACE:
                del self.pending[p]
                self.out_at[p] = self.t
        # bots jump when a hand is about to reach them
        for p in self.bots:
            if p in self.out_at or self.t < self.air_until[p]:
                continue
            for h in self.hands:
                if not h["on"]:
                    continue
                eta = self.ahead(h, self.angle[p]) / (abs(h["w"]) * speed)
                if eta < self.react[p] and random.random() < 0.985:
                    self.jump(p)
                    self.react[p] = random.uniform(0.12, 0.3)
                    break

    def snap(self):
        speed = 1 + self.t / 25
        return {"hands": [[_r(h["a"]), _r(h["w"] * speed), int(h["on"])] for h in self.hands],
                "air": {str(p): _r(max(0.0, self.air_until[p] - self.t)) for p in self.ids}, "alive": self.alive_ids()}

    def label(self, pid):
        return "Never hit" if pid not in self.out_at else f"Hit at {self.out_at[pid]:.1f}s"


# ---------------------------------------------------------------- the solo games


class CookieCutter(Scripted):
    """Crazy Cutters (Mario Party) / Trace Race (Mario Party 4): trace the outline, quickly."""
    key, name = "cutter", "Cookie Cutter"
    rules = "Trace round the outline of the shape with the mouse. Score for covering it all and staying on the line, plus a bonus for finishing quickly."
    controls = "Hold the mouse button and trace. Press Done (or Enter) when you're round."
    dur = 22.0
    SHAPES = ["star", "heart", "circle", "bolt", "house", "cloud"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.params = {"shape": random.choice(self.SHAPES)}
        for pid in self.bots:
            t = random.uniform(9, 19)
            self.plans[pid] = [(t, [1], random.randint(40, 92))]

    def clean_score(self, v):
        v = _nums(v, 1, 0, 200)
        return None if v is None else int(v[0])

    def clean_prog(self, v):
        return [1] if v else None

    def key_of(self, pid):
        return -self.score.get(pid, -1)

    def label(self, pid):
        return f"{self.score[pid]} points" if pid in self.score else "Didn't finish"


class HotelHustle(Scripted):
    """Hotel Goomba (Mario Party 5): race up the floors; only one door on each leads upstairs."""
    key, name = "hotel", "Hotel Hustle"
    rules = "Race to the top of the hotel. On each floor only one door leads up; the others bounce you back for a moment. Everyone gets the same hotel, so watch who's ahead."
    controls = "Click a door, or press its number."
    dur = 40.0
    FLOORS = 8
    STUN = 1.2

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        floors = []
        for i in range(self.FLOORS):
            n = 3 if i < 4 else 4
            floors.append([n, random.randrange(n)])
        self.params = {"floors": floors, "stun": self.STUN}
        for pid in self.bots:
            t, plan = 0.0, []
            for i, (n, _) in enumerate(floors):
                tries = random.randint(1, n)
                t += tries * random.uniform(0.6, 1.0) + (tries - 1) * self.STUN
                if t > self.dur:
                    break
                plan.append((t, [i + 1, round(t, 2)], [i + 1, round(t, 2)] if i == self.FLOORS - 1 else None))
            self.plans[pid] = plan

    def clean_score(self, v):
        v = _nums(v, 2, 0, self.dur)
        return None if v is None else [min(self.FLOORS, int(v[0])), v[1]]

    def key_of(self, pid):
        s = self.score.get(pid) or self.prog.get(pid) or [0, self.dur]
        return (-s[0], s[1])

    def label(self, pid):
        s = self.score.get(pid) or self.prog.get(pid) or [0]
        return "Reached the roof" + (f" in {s[1]:.1f}s" if len(s) > 1 else "") if s[0] == self.FLOORS \
            else f"Floor {int(s[0])}"


class ShootingGallery(Scripted):
    """Aim of the Game (Mario Party 8): shoot the targets as they cross; leave the bombs."""
    key, name = "gallery", "Shooting Gallery"
    rules = "Targets slide across the gallery. Click them: ducks score 1, gold stars 3. Hitting a bomb costs 3."
    controls = "Point and click."
    dur = 25.0

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        targets, t = [], 0.4
        while t < self.dur - 3:
            r = random.random()
            kind = "gold" if r < 0.12 else "bomb" if r < 0.3 else "duck"
            d = random.choice([-1, 1])
            targets.append([round(t, 2), round(random.uniform(18, 88), 1), d, round(random.uniform(22, 42) * (1.4 if kind == "gold" else 1), 1), kind])
            t += random.uniform(0.25, 0.6)
        self.params = {"targets": targets}
        best = sum(3 if k[4] == "gold" else 1 for k in targets if k[4] != "bomb")
        for pid in self.bots:
            skill = random.uniform(0.4, 0.72)
            score = int(best * skill) - 3 * (random.random() < 0.3)
            self.plans[pid] = [(self.dur * f, [int(score * f)], None) for f in (0.25, 0.5, 0.75)] + \
                              [(self.dur - 2, [score], score)]

    def clean_score(self, v):
        v = _nums(v, 1, -99, 999)
        return None if v is None else int(v[0])

    def key_of(self, pid):
        s = self.score.get(pid)
        if s is None:
            s = (self.prog.get(pid) or [-99])[0]
        return -s

    def team_key(self, team):
        return sum(self.key_of(p) for p in team)

    def label(self, pid):
        return f"{-self.key_of(pid)} points"


class TenSeconds(Scripted):
    """The stop-the-clock game: stop a timer at exactly the target, though it vanishes partway."""
    key, name = "clock", "Ten Seconds Flat"
    rules = "Two rounds. A stopwatch starts; stop it on exactly the target time. The display disappears after 3 seconds, so you'll have to count. Smallest total miss wins."
    controls = "Space, Enter, or click to stop."
    HIDE = 3.0

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        targets = [10.0, random.choice([6.0, 7.0, 7.5, 8.0, 9.0])]
        self.params = {"targets": targets, "hide": self.HIDE}
        self.dur = sum(targets) + 2 * 5 + 6
        for pid in self.bots:
            t, misses, plan = 0.0, [], []
            for target in targets:
                miss = int(abs(random.gauss(0, 0.35)) * 1000)
                t += 1.0 + target + miss / 1000
                misses.append(miss)
                plan.append((t, list(misses), sum(misses) if len(misses) == 2 else None))
                t += 1.5
            self.plans[pid] = plan

    def info(self):
        i = super().info()
        i["dur"] = self.dur
        return i

    def clean_score(self, v):
        v = _nums(v, 2, 0, 20000)
        return None if v is None else int(sum(v))

    def key_of(self, pid):
        return self.score.get(pid, 99999)

    def label(self, pid):
        return f"Off by {self.score[pid] / 1000:.2f}s" if pid in self.score else "Never stopped it"


class Beanstalk(Scripted):
    """The vine-growing game: press the button shown to grow your beanstalk; first to the top wins."""
    key, name = "beanstalk", "Beanstalk"
    rules = "Press the arrow shown to grow your beanstalk one leaf. A wrong press stuns you for a moment. First to 30 leaves wins."
    controls = "Arrow keys (or WASD)."
    dur = 25.0
    GOAL = 30

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.params = {"seq": [random.randrange(4) for _ in range(self.GOAL)], "goal": self.GOAL, "stun": 0.6}
        for pid in self.bots:
            t, plan = 0.0, []
            rate = random.uniform(2.4, 3.4)
            for i in range(self.GOAL):
                t += 1 / rate + (0.6 if random.random() < 0.08 else 0)
                if t > self.dur:
                    break
                if i % 3 == 2 or i == self.GOAL - 1:
                    plan.append((t, [i + 1, round(t, 2)], [i + 1, round(t, 2)] if i == self.GOAL - 1 else None))
            self.plans[pid] = plan

    def clean_score(self, v):
        v = _nums(v, 2, 0, self.dur)
        return None if v is None else [min(self.GOAL, int(v[0])), v[1]]

    def key_of(self, pid):
        s = self.score.get(pid) or self.prog.get(pid) or [0, self.dur]
        return (-s[0], s[1])

    def label(self, pid):
        s = self.score.get(pid) or self.prog.get(pid) or [0]
        return f"Reached the top in {s[1]:.1f}s" if s[0] >= self.GOAL else f"{int(s[0])} leaves"


class MessyMemory(Scripted):
    """Messy Memory (Mario Party 3): study the shelf, then put everything back where it was."""
    key, name = "messy", "Messy Memory"
    rules = "Study where everything sits on the shelf. Then it all gets jumbled: drag each thing back to its spot. Most in the right place wins; ties go to the quicker."
    controls = "Drag things with the mouse; drop one on another to swap them. Press Done when you're sure."
    SHOW = 5.0
    dur = SHOW + 25.0
    KINDS = ["apple", "book", "cup", "lamp", "clock", "plant", "ball"]
    SLOTS = 12

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        kinds = random.sample(self.KINDS, 7)
        home = random.sample(range(self.SLOTS), len(kinds))
        moved = home[:]
        while any(a == b for a, b in zip(moved, home)):
            moved = random.sample(range(self.SLOTS), len(kinds))
        self.params = {"kinds": kinds, "home": home, "moved": moved, "slots": self.SLOTS, "show": self.SHOW}
        for pid in self.bots:
            t = self.SHOW + random.uniform(8, 20)
            right = random.choices(range(3, 8), [1, 2, 3, 3, 2])[0]
            self.plans[pid] = [(t, [1], [right, round(t - self.SHOW, 2)])]

    def clean_score(self, v):
        v = _nums(v, 2, 0, 999)
        if self.t < self.SHOW or v is None:
            return None
        return [min(7, int(v[0])), v[1]]

    def clean_prog(self, v):
        return [1] if v else None

    def key_of(self, pid):
        s = self.score.get(pid) or [0, 999]
        return (-s[0], s[1])

    def label(self, pid):
        return f"{self.score[pid][0]} of 7 right" if pid in self.score else "Didn't finish"


# ---------------------------------------------------------------- Snowball Summit


class SnowballSummit(Survival, ArenaGame):
    """Snowball Summit (Mario Party 3): snowballs roll down the mountain, growing as they go."""
    key, name = "snowball", "Snowball Summit"
    rules = "Snowballs roll down the mountain, getting bigger as they come. Dodge them; get flattened and you're out. Last one standing wins."
    controls = "WASD or arrows to move, Space to dash."
    dur = 45.0
    WALLS = True

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        n = len(self.ids)
        for i, pid in enumerate(self.ids):
            d = self.discs[pid]
            d.x, d.y = 20 + 60 * (i + 0.5) / n, 80
        self.balls = []  # [x, y, vx, vy]
        self.spawn_at = 0.6
        self.out_at = {}

    def alive_ids(self):
        return [d.pid for d in self.discs.values() if d.alive]

    @staticmethod
    def radius(y):
        return 2.5 + 7 * max(0.0, min(1.0, y / 100))

    def after_move(self, live, dt):
        if self.t >= self.spawn_at:
            self.spawn_at = self.t + max(0.28, 1.1 - self.t * 0.018)
            self.balls.append([random.uniform(5, 95), -6.0, random.uniform(-7, 7), random.uniform(26, 38) + self.t * 0.5])
        for b in self.balls:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            if b[0] < 3 or b[0] > 97:
                b[2] = -b[2]
        self.balls = [b for b in self.balls if b[1] < 115]
        for d in live:
            for b in self.balls:
                if math.hypot(d.x - b[0], d.y - b[1]) < self.radius(b[1]) + Disc.R * 0.75:
                    d.alive = False
                    d.vx = d.vy = 0
                    self.out_at[d.pid] = self.t
                    break

    def bot_tick(self, dt):
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if not d.alive or d.think > 0:
                continue
            d.think = random.uniform(0.1, 0.2)
            danger = [(b[0], b[1]) for b in self.balls
                      if b[1] < d.y + 4 and abs(b[0] - d.x) < self.radius(b[1]) + 9 and d.y - b[1] < 30]
            if danger:
                x, y = danger[0]
                self.steer(d, d.x + (12 if d.x >= x else -12), d.y + 2, 0.1)
            elif abs(d.y - 75) > 6:
                self.steer(d, d.x, 75, 0.3)
            else:
                d.ix = d.iy = 0.0

    def snap(self):
        s = super().snap()
        s["b"] = [[_r(b[0]), _r(b[1]), _r(self.radius(b[1]))] for b in self.balls]
        return s

    def label(self, pid):
        return "Never flattened" if pid not in self.out_at else f"Flattened at {self.out_at[pid]:.1f}s"


# ---------------------------------------------------------------- Speed Hockey


class SpeedHockey(ArenaGame):
    """Speed Hockey (Mario Party 2): air hockey, two against two (or a duel). Stay in your half."""
    key, name = "hockey", "Speed Hockey"
    rules = "Air hockey. Knock the puck into the other side's goal; keep it out of yours. You can't cross the middle line. First to 5, or most goals when time's up."
    controls = "WASD or arrows to move, Space to dash into the puck."
    modes = {"team", "duel"}
    dur = 50.0
    GOAL_LO, GOAL_HI, PUCK_R, WIN = 28.0, 72.0, 2.8, 5

    def __init__(self, ids, bots, teams=None, humans=()):
        teams = teams or [[ids[0]], [ids[1]]]
        super().__init__(ids, bots, teams, humans)
        self.side = {p: i for i, t in enumerate(self.teams) for p in t}
        for team, x in ((self.teams[0], 22), (self.teams[1], 78)):
            for k, p in enumerate(team):
                d = self.discs[p]
                d.x, d.y = x, (50 if len(team) == 1 else 32 + 36 * k)
        self.goals = [0, 0]
        self.reset_puck(random.choice([-1, 1]))
        self.params = {"side": {str(k): v for k, v in self.side.items()}, "lo": self.GOAL_LO, "hi": self.GOAL_HI}

    def reset_puck(self, toward):
        self.puck = [50.0, 50.0, toward * 12.0, random.uniform(-8, 8)]
        self.frozen = self.t + 1.0

    def after_move(self, live, dt):
        for d in live:
            lo, hi = (Disc.R, 50 - Disc.R) if self.side[d.pid] == 0 else (50 + Disc.R, 100 - Disc.R)
            d.x = min(hi, max(lo, d.x))
            d.y = min(100 - Disc.R, max(Disc.R, d.y))
        p = self.puck
        if self.t < self.frozen:
            return
        f = math.exp(-0.35 * dt)
        p[2] *= f
        p[3] *= f
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        r = self.PUCK_R
        if p[1] < r or p[1] > 100 - r:
            p[1] = min(100 - r, max(r, p[1]))
            p[3] = -p[3]
        in_mouth = self.GOAL_LO < p[1] < self.GOAL_HI
        if p[0] < r or p[0] > 100 - r:
            if in_mouth:
                scorer = 1 if p[0] < r else 0
                self.goals[scorer] += 1
                self.reset_puck(-1 if scorer == 0 else 1)
                return
            p[0] = min(100 - r, max(r, p[0]))
            p[2] = -p[2]
        for d in live:
            dx, dy = p[0] - d.x, p[1] - d.y
            dist = math.hypot(dx, dy)
            if 0 < dist < Disc.R + r:
                nx, ny = dx / dist, dy / dist
                p[0], p[1] = d.x + nx * (Disc.R + r), d.y + ny * (Disc.R + r)
                rel = (p[2] - d.vx) * nx + (p[3] - d.vy) * ny
                if rel < 0:
                    p[2] -= 2 * rel * nx
                    p[3] -= 2 * rel * ny
                p[2] += d.vx * 0.6 + nx * (25 if d.dash_t > 0 else 8)
                p[3] += d.vy * 0.6 + ny * (25 if d.dash_t > 0 else 8)
        m = math.hypot(p[2], p[3])
        if m > 95:
            p[2], p[3] = p[2] / m * 95, p[3] / m * 95

    def bot_tick(self, dt):
        p = self.puck
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if d.think > 0:
                continue
            d.think = random.uniform(0.1, 0.18)
            side = self.side[pid]
            home_x = 12 if side == 0 else 88
            mine = (p[0] < 50) == (side == 0)
            team = self.teams[side]
            # in a pair, the one nearer the puck goes for it and the other keeps goal
            chaser = min(team, key=lambda q: math.hypot(self.discs[q].x - p[0], self.discs[q].y - p[1]))
            if mine and (pid == chaser or len(team) == 1):
                # get behind the puck, then hit it toward their goal
                gx = 100 if side == 0 else 0
                ax, ay = gx - p[0], 50 - p[1]
                m = math.hypot(ax, ay) or 1
                bx, by = p[0] - ax / m * 5, p[1] - ay / m * 5
                if math.hypot(bx - d.x, by - d.y) < 4:
                    self.steer(d, p[0], p[1], 0.05)
                    if d.dash_cd == 0 and random.random() < 0.4:
                        d.dash_req = True
                else:
                    self.steer(d, bx, by, 0.1)
            else:
                # keepers drift a little, or bots would never concede
                ty = min(self.GOAL_HI, max(self.GOAL_LO, p[1] + random.uniform(-9, 9)))
                if math.hypot(home_x - d.x, ty - d.y) < 2:
                    d.ix = d.iy = 0.0
                else:
                    self.steer(d, home_x, ty, 0.1)

    def over(self):
        return self.t >= self.dur or max(self.goals) >= self.WIN

    def snap(self):
        s = super().snap()
        s["puck"] = [_r(self.puck[0]), _r(self.puck[1])]
        s["goals"] = self.goals
        return s

    def key_of(self, pid):
        side = self.side[pid]
        return -(self.goals[side] - self.goals[1 - side])

    def team_key(self, team):
        return self.key_of(team[0])

    def label(self, pid):
        side = self.side[pid]
        return f"{self.goals[side]}–{self.goals[1 - side]}"


GAMES = [SayCheese, TickTockHop, CookieCutter, HotelHustle, ShootingGallery, TenSeconds, Beanstalk, MessyMemory,
         SnowballSummit, SpeedHockey]
