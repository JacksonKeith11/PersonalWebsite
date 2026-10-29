"""More Board Brawl minigames, the server's half: Halloween takes on fan favourites from the
Mario Party series (named in each class's docstring).

They use the same machinery as `minigames.py`: solo games extend `Scripted`, the arena games
`ArenaGame`, and the rest run their own clock in `tick`. Hex Heat and Spellbook Squirm are drawn
in 3D in the browser, but here they're the same flat 100 x 100 field as the others.
"""

import math
import random

from .minigames import ARENA, ArenaGame, Disc, Minigame, Scripted, _nums, _r


def _last_standing(game, alive):
    """Over when one player (or one team) is left standing."""
    if len(alive) <= (0 if len(game.ids) < 2 else 1):
        return True
    return bool(game.teams) and sum(1 for t in game.teams if any(p in alive for p in t)) <= 1


class Survival:
    """For games where you're in until you're out: rank the standing first, then by how long
    you lasted. Needs `self.out_at` (pid -> time or step out) and `self.alive_ids()`."""

    def key_of(self, pid):
        return (0, 0) if pid not in self.out_at else (1, -self.out_at[pid])

    def over(self):
        return self.t >= self.dur or _last_standing(self, self.alive_ids())


# ---------------------------------------------------------------- Hex Heat (3D)


class HexHeat(Survival, ArenaGame):
    """Hexagon Heat (Mario Party 2): a colour is called, and every tile of another colour drops."""
    key, name = "hexheat", "Hex Heat"
    rules = "A colour is called. Get onto a tile of that colour before the others drop into the pit. Shoving is allowed. Last one standing wins."
    controls = "WASD or arrows to roll, Space to dash. On a phone, drag to roll and tap DASH."
    dur = 50.0
    RINGS, SIZE = 3, 8.0
    COLORS = 4
    DROP, RISE = 1.4, 0.7

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.tiles = []
        for q in range(-self.RINGS, self.RINGS + 1):
            for r in range(-self.RINGS, self.RINGS + 1):
                if abs(q + r) <= self.RINGS:
                    self.tiles.append((50 + self.SIZE * math.sqrt(3) * (q + r / 2), 50 + self.SIZE * 1.5 * r))
        self.out_at = {}
        self.round = 0
        self.new_round()

    def new_round(self):
        # every colour is on the board, so there's always somewhere to go
        n = len(self.tiles)
        self.colors = [i % self.COLORS for i in range(n)]
        random.shuffle(self.colors)
        self.called = random.randrange(self.COLORS)
        self.phase = "call"
        self.phase_end = self.t + max(1.7, 4.2 - 0.35 * self.round)
        self.round += 1

    def alive_ids(self):
        return [d.pid for d in self.discs.values() if d.alive]

    def tile_at(self, x, y):
        best = min(range(len(self.tiles)), key=lambda i: math.hypot(self.tiles[i][0] - x, self.tiles[i][1] - y))
        tx, ty = self.tiles[best]
        return best if math.hypot(tx - x, ty - y) < self.SIZE * 0.93 else None

    def after_move(self, live, dt):
        if self.t >= self.phase_end:
            if self.phase == "call":
                self.phase, self.phase_end = "drop", self.t + self.DROP
            elif self.phase == "drop":
                self.phase, self.phase_end = "rise", self.t + self.RISE
            else:
                self.new_round()
        for d in live:
            i = self.tile_at(d.x, d.y)
            if i is None or (self.phase == "drop" and self.colors[i] != self.called):
                d.alive = False
                d.vx = d.vy = 0
                self.out_at[d.pid] = self.t

    def bot_tick(self, dt):
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if not d.alive or d.think > 0:
                continue
            d.think = random.uniform(0.12, 0.25)
            if self.phase == "call":
                if d.goal is None or self.colors[d.goal] != self.called:
                    good = [i for i, c in enumerate(self.colors) if c == self.called]
                    d.goal = min(good, key=lambda i: math.hypot(self.tiles[i][0] - d.x, self.tiles[i][1] - d.y)
                                 + random.uniform(0, 6))
                tx, ty = self.tiles[d.goal]
            else:
                d.goal = None
                i = self.tile_at(d.x, d.y)
                tx, ty = self.tiles[i] if i is not None else (50, 50)
            if math.hypot(tx - d.x, ty - d.y) < 2.5:
                d.ix = d.iy = 0.0
            else:
                self.steer(d, tx, ty, 0.12)

    def snap(self):
        s = super().snap()
        s.update({"tiles": self.colors, "phase": self.phase, "called": self.called,
                  "left": _r(self.phase_end - self.t), "size": self.SIZE, "xy": [[_r(x), _r(y)] for x, y in self.tiles]})
        return s

    def label(self, pid):
        return "Still standing" if pid not in self.out_at else f"Dropped at {self.out_at[pid]:.1f}s"


# ---------------------------------------------------------------- Spellbook Squirm (3D)


class Squirm(Survival, ArenaGame):
    """Booksquirm (Mario Party 4): giant pages fall, each with a hole cut out. Be in the hole."""
    key, name = "squirm", "Spellbook Squirm"
    rules = "Pages of a giant spellbook slam down, each with a hole cut out. Stand in the hole or get squashed. Last one standing wins."
    controls = "WASD or arrows to roll, Space to dash. On a phone, drag to roll and tap DASH."
    dur = 50.0
    WALLS = True
    GAP = 0.8

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.out_at = {}
        self.wave = 0
        self.page = None
        self.next_at = 0.5

    def alive_ids(self):
        return [d.pid for d in self.discs.values() if d.alive]

    def new_page(self):
        n = self.wave
        self.wave += 1
        fall = max(1.9, 3.6 - 0.18 * n)
        if random.random() < 0.5:
            r = max(8.0, 17 - n * 0.9)
            hole = {"shape": "circle", "x": random.uniform(20, 80), "y": random.uniform(20, 80), "r": r}
        else:
            w, h = max(10.0, 34 - n * 2) * random.uniform(0.5, 1.2), max(9.0, 22 - n * 1.3)
            if random.random() < 0.5:
                w, h = h, w
            hole = {"shape": "rect", "x": random.uniform(10 + w / 2, 90 - w / 2),
                    "y": random.uniform(10 + h / 2, 90 - h / 2), "w": w, "h": h}
        self.page = {**hole, "fall": fall, "lands": self.t + fall, "n": n}

    def inside(self, d):
        p = self.page
        if p["shape"] == "circle":
            return math.hypot(d.x - p["x"], d.y - p["y"]) <= p["r"]
        return abs(d.x - p["x"]) <= p["w"] / 2 and abs(d.y - p["y"]) <= p["h"] / 2

    def after_move(self, live, dt):
        if self.page is None and self.t >= self.next_at:
            self.new_page()
        if self.page and self.t >= self.page["lands"]:
            for d in live:
                if not self.inside(d):
                    d.alive = False
                    d.vx = d.vy = 0
                    self.out_at[d.pid] = self.t
            self.page = None
            self.next_at = self.t + self.GAP

    def bot_tick(self, dt):
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if not d.alive or d.think > 0:
                continue
            d.think = random.uniform(0.15, 0.3)
            p = self.page
            if not p:
                d.ix = d.iy = 0.0
                continue
            if d.goal is None or d.goal[0] != p["n"]:
                spread = (p["r"] if p["shape"] == "circle" else min(p["w"], p["h"]) / 2) * 0.5
                d.goal = (p["n"], p["x"] + random.uniform(-spread, spread), p["y"] + random.uniform(-spread, spread))
            _, tx, ty = d.goal
            if math.hypot(tx - d.x, ty - d.y) < 2:
                d.ix = d.iy = 0.0
            else:
                self.steer(d, tx, ty, 0.1)

    def snap(self):
        s = super().snap()
        if self.page:
            p = self.page
            s["page"] = {k: (_r(v) if isinstance(v, float) else v) for k, v in p.items() if k != "lands"}
            s["page"]["left"] = _r(p["lands"] - self.t)
        return s

    def label(self, pid):
        return "Still standing" if pid not in self.out_at else f"Squashed at {self.out_at[pid]:.1f}s"


# ---------------------------------------------------------------- Skeleton Says


class SkeletonSays(Survival, Minigame):
    """Shy Guy Says (Mario Party): raise the flag you're told to, or the other one if told not to."""
    key, name = "says", "Skeleton Says"
    rules = "The skeleton calls a flag: raise it. If it says DON'T raise one, raise the other. Too slow or wrong and you're out. It speeds up."
    controls = "Left (A or ←) for the pumpkin flag, right (D or →) for the bone flag. Or tap a side."
    dur = 75.0
    N, GAP = 30, 0.9
    CALLS = [("Pumpkin up!", 0), ("Bone up!", 1), ("Don't raise the pumpkin!", 1), ("Don't raise the bone!", 0)]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.calls = []
        t = 0.6
        for i in range(self.N):
            text, flag = random.choice(self.CALLS[:2] if i < 2 else self.CALLS)
            window = max(0.85, 2.3 - 0.075 * i)
            self.calls.append({"text": text, "flag": flag, "at": t, "end": t + window})
            t += window + self.GAP
        self.i = 0
        self.picks = {}  # pid -> flag for the current call
        self.last = None  # the previous call's answers, for the browser
        self.out_at = {}
        self.bot_plan = {}

    def alive_ids(self):
        return [p for p in self.ids if p not in self.out_at]

    def on(self, pid, msg):
        c = self.calls[self.i] if self.i < self.N else None
        if msg.get("t") == "flag" and c and msg.get("i") == self.i and msg.get("f") in (0, 1) \
                and c["at"] <= self.t < c["end"] and pid not in self.out_at and pid not in self.picks \
                and pid not in self.bots:
            self.picks[pid] = msg["f"]

    def bot_tick(self, dt):
        if self.i >= self.N:
            return
        c = self.calls[self.i]
        for pid in self.bots:
            if pid in self.out_at or pid in self.picks:
                continue
            if pid not in self.bot_plan or self.bot_plan[pid][0] != self.i:
                right = random.random() < 0.97 - 0.013 * self.i
                self.bot_plan[pid] = (self.i, c["at"] + random.uniform(0.35, 0.8), c["flag"] if right else 1 - c["flag"])
            _, when, f = self.bot_plan[pid]
            if self.t >= when and self.t < c["end"]:
                self.picks[pid] = f

    def tick(self, dt):
        super().tick(dt)
        if self.i < self.N and self.t >= self.calls[self.i]["end"]:
            c = self.calls[self.i]
            for pid in self.alive_ids():
                if self.picks.get(pid) != c["flag"]:
                    self.out_at[pid] = self.i
            self.last = {"i": self.i, "flag": c["flag"], "picks": {str(k): v for k, v in self.picks.items()}}
            self.picks = {}
            self.i += 1
            if self.i >= self.N:
                self.t = max(self.t, self.dur)

    def snap(self):
        c = self.calls[min(self.i, self.N - 1)]
        calling = self.i < self.N and c["at"] <= self.t < c["end"]
        return {"i": self.i, "text": c["text"] if calling else "", "calling": calling,
                "left": _r((c["end"] if calling else c["at"]) - self.t), "window": _r(c["end"] - c["at"]),
                "alive": self.alive_ids(), "in": list(self.picks), "last": self.last}

    def label(self, pid):
        return "Never fooled" if pid not in self.out_at else f"Out on call {self.out_at[pid] + 1}"


# ---------------------------------------------------------------- Pumpkin Lift


class PumpkinLift(Scripted):
    """Face Lift (Mario Party): drag a jumbled face back into the shape you're shown."""
    key, name = "lift", "Pumpkin Lift"
    rules = "Someone's carved a pumpkin wrong. Drag its eyes, nose and mouth to match the one you're shown. Closest match wins."
    controls = "Drag the features with the mouse or a finger. Press Done when you're happy."
    dur = 20.0
    FEATURES = ["leye", "reye", "nose", "mouth"]
    HOME = {"leye": (-0.38, -0.25), "reye": (0.38, -0.25), "nose": (0, 0.05), "mouth": (0, 0.42)}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        target = {f: [round(x + random.uniform(-0.14, 0.14), 3), round(y + random.uniform(-0.1, 0.1), 3)]
                  for f, (x, y) in self.HOME.items()}
        start = {f: [round(random.uniform(-0.6, 0.6), 3), round(random.uniform(-0.55, 0.6), 3)] for f in self.FEATURES}
        self.params = {"target": target, "start": start}
        for pid in self.bots:
            t = random.uniform(9, 18)
            self.plans[pid] = [(t, [1], random.randint(8, 40))]

    def clean_score(self, v):
        v = _nums(v, 1, 0, 999)
        return None if v is None else int(v[0])

    def clean_prog(self, v):
        return [1] if v else None

    def key_of(self, pid):
        return self.score.get(pid, 9999)

    def label(self, pid):
        return f"Off by {self.score[pid]}" if pid in self.score else "Didn't finish"


# ---------------------------------------------------------------- Hide and Go Boo!


class HideBoo(Minigame):
    """Hide and Go BOOM! (Mario Party 4): one seeker opens coffins; everyone else hides in them."""
    key, name = "hide", "Hide and Go Boo!"
    rules = "Everyone but the seeker hides in a coffin. Then the seeker opens three coffins, one at a time. The seeker wins by finding more than half the hiders; otherwise the hiders win."
    controls = "Click or tap a coffin. (You're all on a call, so bluff away.)"
    modes = {"1vn"}
    HIDE, PICK, SHOW = 9.0, 7.0, 2.0

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.seeker = self.teams[0][0]
        self.hiders = [p for p in self.ids if p != self.seeker]
        # Picked so a random seeker wins about half the time; bluffing on the call decides it.
        self.n = 6 if len(self.hiders) >= 3 else 4
        self.opens = 3
        self.need = len(self.hiders) // 2 + 1
        self.dur = self.HIDE + self.opens * (self.PICK + self.SHOW) + 0.5
        self.hide = {}  # hider -> coffin
        self.opened = []  # [coffin, [found]]
        self.caught = set()
        self.phase, self.phase_end = "hide", self.HIDE
        self.params = {"seeker": self.seeker, "n": self.n, "opens": self.opens, "need": self.need}
        taken = list(range(self.n))
        random.shuffle(taken)
        self.bot_hide = {pid: taken[i % self.n] for i, pid in enumerate(self.hiders)}

    def info(self):
        i = super().info()
        i["dur"] = self.dur
        return i

    def on(self, pid, msg):
        c = msg.get("c")
        if msg.get("t") != "pick" or c not in range(self.n) or pid in self.bots:
            return
        if self.phase == "hide" and pid in self.hiders:
            self.hide[pid] = c
        elif self.phase == "seek" and pid == self.seeker and c not in [o[0] for o in self.opened]:
            self.open(c)

    def open(self, c):
        found = [p for p in self.hiders if self.hide.get(p) == c]
        self.caught.update(found)
        self.opened.append([c, found])
        self.phase, self.phase_end = "show", self.t + self.SHOW

    def tick(self, dt):
        self.t += dt
        if self.phase == "hide":
            for pid in self.hiders:
                if pid in self.bots and self.t > random.uniform(1, 6):
                    self.hide.setdefault(pid, self.bot_hide[pid])
            if self.t >= self.phase_end:
                for pid in self.hiders:
                    self.hide.setdefault(pid, random.randrange(self.n))
                self.phase, self.phase_end = "seek", self.t + self.PICK
        elif self.phase == "seek":
            shut = [c for c in range(self.n) if c not in [o[0] for o in self.opened]]
            if self.seeker in self.bots and self.phase_end - self.t < self.PICK - 2.0:
                self.open(random.choice(shut))
            elif self.t >= self.phase_end:
                self.open(random.choice(shut))
        elif self.phase == "show" and self.t >= self.phase_end:
            if len(self.opened) >= self.opens or len(self.caught) == len(self.hiders):
                self.phase = "done"
            else:
                self.phase, self.phase_end = "seek", self.t + self.PICK

    def over(self):
        return self.phase == "done" or self.t >= self.dur + 2

    def snap(self):
        s = {"phase": self.phase, "left": _r(self.phase_end - self.t), "opened": self.opened,
             "caught": list(self.caught), "hidden": len(self.hide)}
        if self.phase == "done":
            s["hide"] = {str(k): v for k, v in self.hide.items()}
        return s

    def private(self, pid):
        return {"mine": self.hide[pid]} if pid in self.hide else None

    def seeker_won(self):
        return len(self.caught) >= self.need

    def key_of(self, pid):
        return 0 if (self.seeker_won() if pid == self.seeker else not self.seeker_won()) else 1

    def team_key(self, team):
        return self.key_of(team[0])

    def label(self, pid):
        if pid == self.seeker:
            return f"Seeker: found {len(self.caught)} of {len(self.hiders)}"
        return "Found!" if pid in self.caught else "Never found"


# ---------------------------------------------------------------- Skull Bowling


class Bowling(Minigame):
    """Bowl Over (Mario Party): one player bowls; the rest dodge along the far end."""
    key, name = "bowl", "Skull Bowling"
    rules = "One of you bowls a skull at everyone else, three times, and can curve it as it rolls. Everyone else dodges along the far end. If anyone's left standing, the dodgers win."
    controls = "Bowler: move left and right, Space or tap to throw, then steer to curve it. Dodgers: left and right."
    modes = {"1vn"}
    hz = 20
    dur = 32.0
    THROWS = 3
    ROW_Y, BOWL_Y = 16.0, 90.0
    BALL_R, PIN_R = 5.0, 4.2
    SPEED, CURVE = 62.0, 55.0
    ACC, DRAG = 110.0, 4.0

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.bowler = self.teams[0][0]
        self.runners = [p for p in self.ids if p != self.bowler]
        n = len(self.runners)
        self.x = {p: 20 + 60 * (i + 0.5) / n for i, p in enumerate(self.runners)}
        self.v = {p: 0.0 for p in self.runners}
        self.bx = 50.0
        self.stick = {p: 0.0 for p in self.ids}
        self.throw_req = False
        self.ball = None  # [x, y, vx]
        self.throws = 0
        self.wait_until = 1.0
        self.auto_throw = 9.0
        self.out_at = {}
        self.params = {"bowler": self.bowler, "row": self.ROW_Y, "bowl": self.BOWL_Y}
        self.think = {p: 0.0 for p in self.ids}
        self.aim = None

    def on(self, pid, msg):
        if msg.get("t") != "in" or pid in self.bots or pid not in self.stick:
            return
        try:
            x = float(msg.get("x", 0))
        except (TypeError, ValueError):
            return
        if math.isfinite(x):
            self.stick[pid] = max(-1.0, min(1.0, x))
        if msg.get("dash") and pid == self.bowler:
            self.throw_req = True

    def bot_tick(self, dt):
        for pid in self.bots:
            self.think[pid] -= dt
            if self.think[pid] > 0:
                continue
            self.think[pid] = random.uniform(0.1, 0.2)
            if pid == self.bowler:
                live = [p for p in self.runners if p not in self.out_at]
                if not live:
                    continue
                if self.aim not in live or random.random() < 0.03:
                    self.aim = random.choice(live)
                tx = self.x[self.aim]
                at = self.ball[0] if self.ball else self.bx
                self.stick[pid] = max(-1.0, min(1.0, (tx - at) / 8))
                if not self.ball and abs(tx - self.bx) < 4 and random.random() < 0.5:
                    self.throw_req = True
            elif pid not in self.out_at:
                if self.ball and self.ball[1] < 60:
                    away = self.x[pid] - self.ball[0]
                    self.stick[pid] = 1.0 if away > 0 else -1.0
                    if self.x[pid] > 85:
                        self.stick[pid] = -1.0
                    elif self.x[pid] < 15:
                        self.stick[pid] = 1.0
                else:
                    self.stick[pid] = random.choice([-1.0, 0.0, 0.0, 1.0])

    def tick(self, dt):
        self.t += dt
        self.bot_tick(dt)
        for p in self.runners:
            if p in self.out_at:
                continue
            self.v[p] = (self.v[p] + self.stick[p] * self.ACC * dt) * math.exp(-self.DRAG * dt)
            self.x[p] = min(94.0, max(6.0, self.x[p] + self.v[p] * dt))
        if self.ball:
            b = self.ball
            b[2] += self.stick[self.bowler] * self.CURVE * dt
            b[0] += b[2] * dt
            b[1] -= self.SPEED * dt
            if b[0] < self.BALL_R or b[0] > ARENA - self.BALL_R:
                b[2] = -b[2]
                b[0] = min(ARENA - self.BALL_R, max(self.BALL_R, b[0]))
            for p in self.runners:
                if p not in self.out_at and math.hypot(self.x[p] - b[0], self.ROW_Y - b[1]) < self.BALL_R + self.PIN_R:
                    self.out_at[p] = self.t
            if b[1] < -5:
                self.ball = None
                self.wait_until = self.t + 0.8
                self.auto_throw = self.t + 9.0
        else:
            self.bx = min(92.0, max(8.0, self.bx + self.stick[self.bowler] * 55 * dt))
            if self.throws < self.THROWS and self.t >= self.wait_until and (self.throw_req or self.t >= self.auto_throw):
                self.ball = [self.bx, self.BOWL_Y, 0.0]
                self.throws += 1
        self.throw_req = False

    def over(self):
        everyone_out = all(p in self.out_at for p in self.runners)
        done = self.throws >= self.THROWS and not self.ball
        return everyone_out or done or self.t >= self.dur

    def snap(self):
        return {"r": [[p, _r(self.x[p]), int(p not in self.out_at)] for p in self.runners], "bx": _r(self.bx),
                "ball": [_r(v) for v in self.ball[:2]] if self.ball else None, "left": self.THROWS - self.throws}

    def bowler_won(self):
        return all(p in self.out_at for p in self.runners)

    def key_of(self, pid):
        return 0 if (self.bowler_won() if pid == self.bowler else not self.bowler_won()) else 1

    def team_key(self, team):
        return self.key_of(team[0])

    def label(self, pid):
        if pid == self.bowler:
            return f"Bowler: knocked down {len(self.out_at)}"
        return "Still standing" if pid not in self.out_at else f"Bowled over at {self.out_at[pid]:.1f}s"


# ---------------------------------------------------------------- Grave Robbers


class GraveRobbers(Minigame):
    """Air to a Fortune (Super Mario Party) / Grab Bag: everyone secretly picks a grave to rob.
    If two of you pick the same one, you both get nothing."""
    key, name = "graves", "Grave Robbers"
    rules = "Five nights of grave robbing. Each night, secretly pick a grave to dig up and take its candy. If two of you pick the same grave, you scare each other off and nobody gets any. One grave is cursed."
    controls = "Click or tap a grave. You can change your mind until time's up."
    PICK, SHOW, ROUNDS = 7.0, 3.0, 5
    dur = ROUNDS * (PICK + SHOW)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.values = []
        for _ in range(self.ROUNDS):
            v = [random.choice([1, 2, 2, 3, 3, 4, 5, 6]) for _ in range(7)] + [10, -5]
            random.shuffle(v)
            self.values.append(v)
        self.picks = [{} for _ in range(self.ROUNDS)]
        self.points = {pid: 0 for pid in self.ids}
        self.bot_at = {pid: random.uniform(1.5, 5.5) for pid in self.bots}
        self.settled = -1

    def where(self):
        r = min(self.ROUNDS - 1, int(self.t // (self.PICK + self.SHOW)))
        return r, self.t - r * (self.PICK + self.SHOW)

    def on(self, pid, msg):
        r, into = self.where()
        if msg.get("t") == "pick" and msg.get("r") == r and into < self.PICK and msg.get("g") in range(9) \
                and pid not in self.bots:
            self.picks[r][pid] = msg["g"]

    def tick(self, dt):
        self.t += dt
        r, into = self.where()
        if into < self.PICK:
            for pid in self.bots:
                if pid not in self.picks[r] and into >= self.bot_at[pid]:
                    vals = self.values[r]
                    w = [max(0.05, v) ** 1.6 for v in vals]
                    self.picks[r][pid] = random.choices(range(9), w)[0]
        elif self.settled < r:
            self.settled = r
            counts = {}
            for g in self.picks[r].values():
                counts[g] = counts.get(g, 0) + 1
            for pid, g in self.picks[r].items():
                if counts[g] == 1:
                    self.points[pid] += self.values[r][g]
            self.bot_at = {pid: random.uniform(1.5, 5.5) for pid in self.bots}

    def over(self):
        return self.t >= self.dur

    def snap(self):
        r, into = self.where()
        picking = into < self.PICK
        s = {"r": r, "n": self.ROUNDS, "values": self.values[r], "picking": picking,
             "left": _r((self.PICK - into) if picking else (self.PICK + self.SHOW - into)),
             "in": list(self.picks[r]), "pts": {str(k): v for k, v in self.points.items()}}
        if not picking:
            s["picks"] = {str(k): v for k, v in self.picks[r].items()}
        return s

    def key_of(self, pid):
        return -self.points[pid]

    def team_key(self, team):
        return -sum(self.points[p] for p in team)

    def label(self, pid):
        return f"{self.points[pid]} candy"


# ---------------------------------------------------------------- Hot Pumpkin


class HotPumpkin(Survival, Minigame):
    """Lit Potato (Super Mario Party): pass the lit pumpkins round the circle before they blow."""
    key, name = "potato", "Hot Pumpkin"
    rules = "Lit pumpkins go round the circle. Pass them left or right before they blow: whoever's holding one when it goes off is out. Last one standing wins."
    controls = "Left (A or ←) or right (D or →) to pass, or tap the arrows."
    modes = {"ffa", "duel"}
    hz = 20
    dur = 60.0
    FLY, PAUSE = 0.35, 1.8

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.out_at = {}
        self.bombs = []  # {"at": pid, "to": pid|None, "land": t, "fuse": t}
        self.booms = []
        self.next_round = 0.4
        self.held_since = {}

    def alive_ids(self):
        return [p for p in self.ids if p not in self.out_at]

    def deal(self):
        alive = self.alive_ids()
        n = max(1, len(alive) - 1)
        holders = random.sample(alive, n)
        self.bombs = [{"at": h, "to": None, "land": 0.0, "fuse": self.t + random.uniform(5, 11)} for h in holders]
        self.held_since = {h: self.t for h in holders}

    def neighbour(self, pid, d):
        alive = self.alive_ids()
        i = alive.index(pid)
        return alive[(i + d) % len(alive)]

    def pass_(self, pid, d):
        b = next((b for b in self.bombs if b["at"] == pid and b["to"] is None), None)
        if b is None or len(self.alive_ids()) < 2:
            return
        b["to"] = self.neighbour(pid, d)
        b["land"] = self.t + self.FLY

    def on(self, pid, msg):
        if msg.get("t") == "pass" and msg.get("d") in (-1, 1) and pid not in self.bots and pid not in self.out_at:
            self.pass_(pid, msg["d"])

    def tick(self, dt):
        self.t += dt
        if not self.bombs:
            if self.next_round is not None and self.t >= self.next_round and len(self.alive_ids()) > 1:
                self.deal()
                self.next_round = None
            return
        for b in self.bombs:
            if b["to"] is not None and self.t >= b["land"]:
                b["at"], b["to"] = b["to"], None
                self.held_since[b["at"]] = self.t
        for pid in self.bots:
            if pid in self.out_at:
                continue
            held = [b for b in self.bombs if b["at"] == pid and b["to"] is None]
            if held and self.t - self.held_since.get(pid, self.t) > random.uniform(0.25, 1.1):
                self.pass_(pid, random.choice([-1, 1]))
                self.held_since[pid] = self.t
        for b in self.bombs:
            if self.t >= b["fuse"]:
                victim = b["to"] if b["to"] is not None else b["at"]
                self.out_at[victim] = self.t
                self.booms.append([victim, _r(self.t)])
                self.bombs = []
                self.next_round = self.t + self.PAUSE
                break
        self.booms = [b for b in self.booms if self.t - b[1] < 2]

    def snap(self):
        return {"alive": self.alive_ids(), "order": self.ids,
                "b": [[b["at"], b["to"], _r(max(0.0, b["land"] - self.t)) if b["to"] is not None else 0]
                      for b in self.bombs], "booms": self.booms}

    def label(self, pid):
        return "Never blew up" if pid not in self.out_at else f"Blew up at {self.out_at[pid]:.1f}s"


# ---------------------------------------------------------------- Slime Shooters


class SlimeShooters(Survival, ArenaGame):
    """Shell Shocked (Mario Party): tanks in an arena. Three hits and you're out."""
    key, name = "shoot", "Slime Shooters"
    rules = "Roll around firing slime. You fire the way you're rolling. Three hits and you're out; last one standing wins."
    controls = "WASD or arrows to roll and aim, Space to fire. On a phone, drag to roll and tap FIRE."
    dur = 45.0
    WALLS = True
    SHOT_SPEED, SHOT_LIFE, COOLDOWN = 46.0, 1.6, 0.75

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.out_at = {}
        self.shots = []  # [x, y, vx, vy, owner, dies_at]
        for d in self.discs.values():
            d.lives = 3
            a = math.atan2(50 - d.y, 50 - d.x)
            d.fx, d.fy = math.cos(a), math.sin(a)

    def alive_ids(self):
        return [d.pid for d in self.discs.values() if d.alive]

    def mate(self, a, b):
        return bool(self.teams) and any(a in t and b in t for t in self.teams)

    def dash(self, d):
        # Space fires instead of dashing
        self.shots.append([d.x + d.fx * 6, d.y + d.fy * 6, d.fx * self.SHOT_SPEED, d.fy * self.SHOT_SPEED,
                           d.pid, self.t + self.SHOT_LIFE])
        d.dash_cd = self.COOLDOWN

    def after_move(self, live, dt):
        for d in live:
            if math.hypot(d.ix, d.iy) > 0.3:
                m = math.hypot(d.ix, d.iy)
                d.fx, d.fy = d.ix / m, d.iy / m
        for s in list(self.shots):
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            gone = self.t >= s[5] or not (0 < s[0] < ARENA and 0 < s[1] < ARENA)
            for d in live:
                if not gone and d.pid != s[4] and not self.mate(d.pid, s[4]) and d.safe == 0 \
                        and math.hypot(d.x - s[0], d.y - s[1]) < Disc.R + 1.8:
                    d.lives -= 1
                    d.safe = 0.6
                    d.vx += s[2] * 0.4
                    d.vy += s[3] * 0.4
                    gone = True
                    if d.lives <= 0:
                        d.alive = False
                        d.vx = d.vy = 0
                        self.out_at[d.pid] = self.t
            if gone:
                self.shots.remove(s)

    def bot_tick(self, dt):
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if not d.alive or d.think > 0:
                continue
            d.think = random.uniform(0.12, 0.22)
            foes = [o for o in self.discs.values() if o.alive and o is not d and not self.mate(o.pid, pid)]
            if not foes:
                continue
            o = min(foes, key=lambda o: math.hypot(o.x - d.x, o.y - d.y))
            dist = math.hypot(o.x - d.x, o.y - d.y)
            lead = dist / self.SHOT_SPEED
            ax, ay = o.x + o.vx * lead - d.x, o.y + o.vy * lead - d.y
            am = math.hypot(ax, ay) or 1
            if d.dash_cd == 0 and random.random() < 0.09:
                a = math.atan2(ay, ax) + random.gauss(0, 0.3)
                d.fx, d.fy = math.cos(a), math.sin(a)
                d.ix, d.iy = d.fx * 0.2, d.fy * 0.2
                d.dash_req = True
                continue
            # keep a middling range and circle round
            side = 1 if pid % 2 else -1
            tx = d.x + (-ay / am) * side * 20 + (ax / am) * (dist - 28)
            ty = d.y + (ax / am) * side * 20 + (ay / am) * (dist - 28)
            self.steer(d, min(90, max(10, tx)), min(90, max(10, ty)), 0.2)

    def snap(self):
        s = super().snap()
        s["f"] = {str(d.pid): _r(math.atan2(d.fy, d.fx)) for d in self.discs.values()}
        s["s"] = [[_r(x[0]), _r(x[1]), x[4]] for x in self.shots]
        return s

    def key_of(self, pid):
        return (0, -self.discs[pid].lives) if pid not in self.out_at else (1, -self.out_at[pid])

    def label(self, pid):
        d = self.discs[pid]
        return f"Standing, {d.lives} hit{'s' if d.lives != 1 else ''} left" if d.alive else f"Slimed at {self.out_at[pid]:.1f}s"


# ---------------------------------------------------------------- Skull Pong


class SkullPong(Survival, Minigame):
    """Paddle Battle (Mario Party): four-way pong. Let a skull past three times and you're out."""
    key, name = "pong", "Skull Pong"
    rules = "Everyone guards a wall with a paddle. Let a skull past and you lose a life; three and you're out, and your wall closes. Last one standing wins."
    controls = "Left and right (A/D or arrows), or drag. Your wall is always at the bottom of your screen."
    modes = {"ffa", "duel"}
    hz = 20
    dur = 60.0
    HALF, SPEED, BALL_R = 11.0, 75.0, 2.6
    SIDES = {2: ["bottom", "top"], 3: ["bottom", "left", "right"], 4: ["bottom", "top", "left", "right"]}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        sides = self.SIDES[min(4, max(2, len(self.ids)))]
        self.side = {p: sides[i] for i, p in enumerate(self.ids)}
        self.pos = {p: 50.0 for p in self.ids}
        self.stick = {p: 0.0 for p in self.ids}
        self.lives = {p: 3 for p in self.ids}
        self.out_at = {}
        self.balls = []
        self.serve_at = [0.6]
        self.think = {p: 0.0 for p in self.ids}
        self.params = {"side": {str(k): v for k, v in self.side.items()}}

    def alive_ids(self):
        return [p for p in self.ids if p not in self.out_at]

    def on(self, pid, msg):
        if msg.get("t") != "in" or pid in self.bots or pid not in self.side:
            return
        try:
            x, y = float(msg.get("x", 0)), float(msg.get("y", 0))
        except (TypeError, ValueError):
            return
        if math.isfinite(x) and math.isfinite(y):
            v = x if self.side[pid] in ("bottom", "top") else y
            self.stick[pid] = max(-1.0, min(1.0, v))

    def speed(self):
        return min(70.0, 36 + self.t * 0.9)

    def serve(self):
        a = random.uniform(0, 2 * math.pi)
        # not straight along a wall
        a = math.copysign(max(0.35, abs(math.sin(a))), math.sin(a))
        ang = math.asin(a) + (0 if random.random() < 0.5 else math.pi)
        if random.random() < 0.5:
            ang += math.pi / 2
        s = self.speed()
        self.balls.append([50.0, 50.0, math.cos(ang) * s, math.sin(ang) * s])

    def owner(self, side):
        return next((p for p, s in self.side.items() if s == side and p not in self.out_at), None)

    def bot_tick(self, dt):
        for pid in self.bots:
            self.think[pid] -= dt
            if pid in self.out_at or self.think[pid] > 0:
                continue
            self.think[pid] = random.uniform(0.08, 0.18)
            side = self.side[pid]
            axis = 0 if side in ("bottom", "top") else 1
            coming = [b for b in self.balls if (side == "bottom" and b[3] > 0) or (side == "top" and b[3] < 0)
                      or (side == "left" and b[2] < 0) or (side == "right" and b[2] > 0)]
            target = 50.0
            if coming:
                wall = {"bottom": (1, 100), "top": (1, 0), "left": (0, 0), "right": (0, 100)}[side]
                b = min(coming, key=lambda b: abs(b[wall[0]] - wall[1]))
                target = b[axis] + random.uniform(-6, 6)
            diff = target - self.pos[pid]
            self.stick[pid] = max(-1.0, min(1.0, diff / 6)) * random.uniform(0.75, 1.0)

    def tick(self, dt):
        self.t += dt
        self.bot_tick(dt)
        for p in self.alive_ids():
            self.pos[p] = min(100 - self.HALF, max(self.HALF, self.pos[p] + self.stick[p] * self.SPEED * dt))
        for at in list(self.serve_at):
            if self.t >= at and len(self.alive_ids()) > 1:
                self.serve_at.remove(at)
                self.serve()
        if self.t > 12 and len(self.balls) + len(self.serve_at) < 2 and not getattr(self, "second", False):
            self.second = True
            self.serve_at.append(self.t)
        s = self.speed()
        for b in list(self.balls):
            m = math.hypot(b[2], b[3]) or 1
            b[2], b[3] = b[2] / m * s, b[3] / m * s
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            for side, axis, edge, along, sign in (("left", 0, self.BALL_R, 1, 1), ("right", 0, 100 - self.BALL_R, 1, -1),
                                                  ("top", 1, self.BALL_R, 0, 1), ("bottom", 1, 100 - self.BALL_R, 0, -1)):
                past = b[axis] < edge if sign > 0 else b[axis] > edge
                if not past:
                    continue
                p = self.owner(side)
                if p is None or abs(b[along] - self.pos[p]) <= self.HALF + self.BALL_R:
                    b[axis] = edge
                    b[2 + axis] = abs(b[2 + axis]) * sign
                    if p is not None:
                        # where it hits the paddle sets the angle back
                        off = (b[along] - self.pos[p]) / self.HALF
                        b[2 + along] += off * s * 0.6
                else:
                    self.lives[p] -= 1
                    if self.lives[p] <= 0:
                        self.out_at[p] = self.t
                    self.balls.remove(b)
                    self.serve_at.append(self.t + 1.0)
                break

    def snap(self):
        return {"pos": {str(p): _r(v) for p, v in self.pos.items()}, "lives": {str(p): v for p, v in self.lives.items()},
                "alive": self.alive_ids(), "balls": [[_r(b[0]), _r(b[1])] for b in self.balls]}

    def key_of(self, pid):
        return (0, -self.lives[pid]) if pid not in self.out_at else (1, -self.out_at[pid])

    def label(self, pid):
        return f"Standing, {self.lives[pid]} {'life' if self.lives[pid] == 1 else 'lives'} left" \
            if pid not in self.out_at else f"Out at {self.out_at[pid]:.1f}s"


# ---------------------------------------------------------------- Monster Mash


class MonsterMash(Scripted):
    """Mario Bandstand (Mario Party 3 / Superstars): hit the notes in time with the music."""
    key, name = "band", "Monster Mash"
    rules = "The monster band needs you. Hit each note as it reaches the line, in time with the music. Perfect hits score 2, close ones 1."
    controls = "D F J K or the arrow keys, or tap the four pads."
    BPM, LEAD, LEN = 112, 2.0, 24.0
    dur = LEAD + LEN + 2.0

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        beat = 60 / self.BPM
        notes = []
        t = self.LEAD
        lane = random.randrange(4)
        while t < self.LEAD + self.LEN:
            k = (t - self.LEAD) / self.LEN
            if random.random() < 0.8:
                lane = (lane + random.choice([-1, 1, 1, 2])) % 4
                notes.append([round(t, 3), lane])
            if k > 0.35 and random.random() < 0.3 + 0.3 * k:
                notes.append([round(t + beat / 2, 3), (lane + 2) % 4])
            t += beat
        self.notes = notes
        self.params = {"bpm": self.BPM, "lead": self.LEAD, "notes": notes, "len": self.LEN}
        for pid in self.bots:
            skill = random.uniform(0.55, 0.9)
            score, plan = 0, []
            for i, (nt, _) in enumerate(notes):
                r = random.random()
                score += 2 if r < skill * 0.5 else 1 if r < skill else 0
                if i % 6 == 5:
                    plan.append((nt + 0.1, [score], None))
            plan.append((self.LEAD + self.LEN + 0.5, [score], score))
            self.plans[pid] = plan

    def clean_score(self, v):
        v = _nums(v, 1, 0, 2 * len(self.notes))
        return None if v is None else int(v[0])

    def key_of(self, pid):
        s = self.score.get(pid)
        if s is None:
            s = (self.prog.get(pid) or [0])[0]
        return -s

    def team_key(self, team):
        return sum(self.key_of(p) for p in team)

    def label(self, pid):
        return f"{-self.key_of(pid)} points"


GAMES = [HexHeat, Squirm, SkeletonSays, PumpkinLift, HideBoo, Bowling, GraveRobbers, HotPumpkin, SlimeShooters,
         SkullPong, MonsterMash]
