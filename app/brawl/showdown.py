"""More one-against-the-rest minigames, after Mario Party's 1 v 3 games.

Candy Bash runs on the arena physics; Look Away and Red Light, Green Light are their own small
loops. In each, teams[0][0] is the one, and everyone else is on the other side.
"""

import math
import random

from .minigames import ARENA, Disc, Minigame, OneVsMany, _r


class OneSide:
    """Ranking for a one-against-the-rest game: the side that won shares first place."""

    def solo_won(self):
        raise NotImplementedError

    def key_of(self, pid):
        return 0 if (self.solo_won() if pid == self.solo else not self.solo_won()) else 1

    def team_key(self, team):
        return self.key_of(team[0])


# ---------------------------------------------------------------- Candy Bash


class CandyBash(OneVsMany):
    """Bash 'n' Cash (Mario Party): everyone chases the one with the sack and knocks candy out."""
    key, name = "bash", "Candy Bash"
    rules = "One of you carries a big sack of candy. Everyone else: bump into them to knock candy out (a dash knocks out more). The sack-carrier wins by keeping at least 14 of their 30."
    controls = "WASD or arrows to roll, Space to dash. On a phone, drag to roll and tap DASH."
    dur = 25.0
    BAG, KEEP, BUMP, DASH_BUMP = 30, 14, 2, 4
    SAFE = 0.85  # after a bump the sack can't be hit again for a moment
    SOLO_ACC = 1.12

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.bag = self.BAG
        self.keep = self.KEEP
        self.loose = []  # [x, y, ready_at]
        self.grabbed = {pid: 0 for pid in self.ids}
        self.params.update({"bag": self.BAG, "keep": self.keep})

    def acc_of(self, d):
        return self.ACC * (self.SOLO_ACC if d.pid == self.solo else 1.0)

    def touch(self, a, b):
        sack = a if a.pid == self.solo else b if b.pid == self.solo else None
        if sack is None or sack.safe > 0 or self.bag <= 0:
            return False
        hitter = b if sack is a else a
        n = min(self.bag, self.DASH_BUMP if hitter.dash_t > 0 else self.BUMP)
        self.bag -= n
        sack.safe = self.SAFE
        for _ in range(n):
            ang = random.uniform(0, 2 * math.pi)
            x = min(95, max(5, sack.x + 13 * math.cos(ang)))
            y = min(95, max(5, sack.y + 13 * math.sin(ang)))
            self.loose.append([x, y, self.t + 0.35])
        return False

    def after_move(self, live, dt):
        for d in live:
            if d.pid == self.solo:
                continue
            for c in list(self.loose):
                if c[2] <= self.t and math.hypot(c[0] - d.x, c[1] - d.y) < Disc.R + 2.5:
                    self.loose.remove(c)
                    self.grabbed[d.pid] += 1

    def solo_won(self):
        return self.bag >= self.keep

    def over(self):
        return self.t >= self.dur or self.bag < self.keep

    def bot_tick(self, dt):
        s = self.discs[self.solo]
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if d.think > 0:
                continue
            d.think = random.uniform(0.12, 0.22)
            if pid == self.solo:
                self.escape(d, [(r.x, r.y) for r in self.runners()])
                continue
            near = [c for c in self.loose if c[2] <= self.t + 0.2 and math.hypot(c[0] - d.x, c[1] - d.y) < 9]
            if near:
                c = min(near, key=lambda c: math.hypot(c[0] - d.x, c[1] - d.y))
                self.steer(d, c[0], c[1], 0.1)
                continue
            self.steer(d, s.x + s.vx * 0.35, s.y + s.vy * 0.35, 0.2)
            if math.hypot(s.x - d.x, s.y - d.y) < 15 and random.random() < 0.25:
                d.dash_req = True

    def snap(self):
        s = super().snap()
        s.update({"bag": self.bag, "c": [[_r(c[0]), _r(c[1])] for c in self.loose],
                  "safe": int(self.discs[self.solo].safe > 0)})
        return s

    def label(self, pid):
        if pid == self.solo:
            return f"Kept {self.bag} of {self.BAG}"
        n = self.grabbed[pid]
        return f"Grabbed {n} cand{'y' if n == 1 else 'ies'}"


# ---------------------------------------------------------------- Look Away


class LookAway(OneSide, Minigame):
    """Look Away (Mario Party 2): everyone picks a way to look; whoever looks the way the pointer
    points is out."""
    key, name = "look", "Look Away"
    rules = "Each round the pointer picks a direction in secret, and everyone else picks one to look. Look the same way the pointer points and you're out. Five rounds: the pointer wins by getting everyone."
    controls = "Arrow keys or WASD, or click an arrow. You're on a call: bluff."
    modes = {"1vn"}
    PICK, SHOW, ROUNDS = 4.0, 2.5, 5
    dur = ROUNDS * (PICK + SHOW) + 0.5
    DIRS = 4

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.solo = self.teams[0][0]
        self.lookers = [p for p in self.ids if p != self.solo]
        self.params = {"solo": self.solo, "rounds": self.ROUNDS}
        self.round = 0
        self.phase, self.phase_end = "pick", self.PICK
        self.picks = {}
        self.out = {}  # looker -> round they went out
        self.last = None  # the last reveal: {"solo": dir, "picks": {pid: dir}}
        self.bot_when = {}

    def alive(self):
        return [p for p in self.lookers if p not in self.out]

    def on(self, pid, msg):
        d = msg.get("d")
        if msg.get("t") == "look" and self.phase == "pick" and d in range(self.DIRS) and pid not in self.bots \
                and (pid == self.solo or pid in self.alive()):
            self.picks[pid] = d

    def tick(self, dt):
        self.t += dt
        if self.phase == "pick":
            for pid in self.bots:
                if pid not in self.bot_when:
                    self.bot_when[pid] = self.t + random.uniform(0.6, self.PICK - 0.6)
                if self.t >= self.bot_when[pid] and (pid == self.solo or pid in self.alive()):
                    self.picks.setdefault(pid, random.randrange(self.DIRS))
            if self.t >= self.phase_end:
                for pid in [self.solo, *self.alive()]:
                    self.picks.setdefault(pid, random.randrange(self.DIRS))
                way = self.picks[self.solo]
                for pid in self.alive():
                    if self.picks[pid] == way:
                        self.out[pid] = self.round
                self.last = {"solo": way, "picks": {str(p): v for p, v in self.picks.items() if p != self.solo}}
                self.phase, self.phase_end = "show", self.t + self.SHOW
        elif self.phase == "show" and self.t >= self.phase_end:
            self.round += 1
            if self.round >= self.ROUNDS or not self.alive():
                self.phase = "done"
            else:
                self.phase, self.phase_end = "pick", self.t + self.PICK
                self.picks, self.bot_when = {}, {}

    def over(self):
        return self.phase == "done" or self.t >= self.dur + 2

    def solo_won(self):
        return not self.alive()

    def snap(self):
        return {"phase": self.phase, "left": _r(self.phase_end - self.t), "round": self.round,
                "out": {str(k): v for k, v in self.out.items()}, "in": list(self.picks),
                "last": self.last if self.phase != "pick" else None}

    def private(self, pid):
        return {"mine": self.picks[pid]} if pid in self.picks and self.phase == "pick" else None

    def label(self, pid):
        if pid == self.solo:
            n = len(self.out)
            return f"Caught {n} of {len(self.lookers)}"
        return f"Caught in round {self.out[pid] + 1}" if pid in self.out else "Never caught"


# ---------------------------------------------------------------- Red Light, Green Light


class RedLight(OneSide, Minigame):
    """Red light, green light: run while the watcher's back is turned, freeze when they look."""
    key, name = "redlight", "Red Light, Green Light"
    rules = "One of you is the watcher. Everyone else: run for the finish while the watcher's back is turned, and freeze when they turn round. Anyone caught moving goes back to the start. The runners win if most of them get to the finish."
    controls = "Runners: hold ↑ or W (or hold the mouse down) to run. Watcher: Space or click to turn round."
    modes = {"1vn"}
    hz = 20
    dur = 22.0
    SPEED, ACCEL = 14.0, 52.0  # full tilt crosses the track in about 7 s; stopping takes a quarter second
    TURN, LOOK, REST = 0.45, 1.5, 0.5  # turning round, looking, then a rest before the next look
    STILL, GRACE = 1.5, 0.15  # moving means faster than this; a moment's grace for latency

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.solo = self.teams[0][0]
        self.runners = [p for p in self.ids if p != self.solo]
        self.params = {"solo": self.solo}
        self.pos = {p: 0.0 for p in self.runners}
        self.vel = {p: 0.0 for p in self.runners}
        self.held = {p: False for p in self.runners}
        self.sent_back = {p: 0 for p in self.runners}
        self.home = []  # runners over the line, in order
        self.need = (len(self.runners) + 1) // 2  # most of them: 2 of 3, 1 of 2
        self.params["need"] = self.need
        self.state, self.state_end = "away", 0.0  # away, turning, looking, rest
        self.flash = []  # [pid, t] for the browser: who was just sent back
        self.bot_look = random.uniform(1.0, 3.0)
        self.bot_react = {}
        self.caught = set()  # sent back during this look: they stay put until it's over

    def on(self, pid, msg):
        if pid in self.bots:
            return
        if msg.get("t") == "run" and pid in self.runners:
            self.held[pid] = bool(msg.get("on"))
        elif msg.get("t") == "turn" and pid == self.solo:
            self.turn()

    def turn(self):
        if self.state == "away" and not self.over():
            self.state, self.state_end = "turning", self.t + self.TURN

    def tick(self, dt):
        self.t += dt
        self.bot_tick(dt)
        if self.state != "away" and self.t >= self.state_end:
            if self.state == "turning":
                self.state, self.state_end = "looking", self.t + self.LOOK
            elif self.state == "looking":
                self.state, self.state_end = "rest", self.t + self.REST
            else:
                self.state = "away"
        if self.state != "looking":
            self.caught.clear()
        for p in self.runners:
            if p in self.home:
                continue
            target = self.SPEED if self.held[p] and p not in self.caught else 0.0
            v = self.vel[p]
            v = min(target, v + self.ACCEL * dt) if target > v else max(target, v - self.ACCEL * dt)
            self.vel[p] = v
            self.pos[p] += v * dt
            if self.pos[p] >= 100:
                self.pos[p], self.vel[p] = 100.0, 0.0
                self.home.append(p)
                continue
            looking_for = self.t - (self.state_end - self.LOOK)
            if self.state == "looking" and looking_for > self.GRACE and v > self.STILL:
                self.pos[p], self.vel[p] = 0.0, 0.0
                self.caught.add(p)
                self.sent_back[p] += 1
                self.flash.append([p, _r(self.t)])
        self.flash = [f for f in self.flash if self.t - f[1] < 1.5]

    def bot_tick(self, dt):
        if self.solo in self.bots and self.state == "away":
            self.bot_look -= dt
            if self.bot_look <= 0:
                self.turn()
                self.bot_look = random.uniform(0.6, 2.6)
        for p in self.runners:
            if p not in self.bots:
                continue
            if self.state in ("turning", "looking"):
                # people take a moment to notice the turn; bots too
                if p not in self.bot_react:
                    self.bot_react[p] = self.t + random.uniform(0.2, 0.6)
                if self.t >= self.bot_react[p]:
                    self.held[p] = False
            else:
                self.bot_react.pop(p, None)
                self.held[p] = True

    def over(self):
        return len(self.home) >= self.need or self.t >= self.dur

    def solo_won(self):
        return len(self.home) < self.need

    def snap(self):
        return {"state": self.state, "left": _r(self.state_end - self.t) if self.state != "away" else 0,
                "pos": {str(p): _r(v) for p, v in self.pos.items()},
                "mv": [p for p in self.runners if self.vel[p] > self.STILL], "home": self.home,
                "flash": self.flash, "back": {str(p): n for p, n in self.sent_back.items()}}

    def label(self, pid):
        if pid == self.solo:
            n = sum(self.sent_back.values())
            return f"Watcher: sent {n} back"
        if pid in self.home:
            return "Made it!"
        return f"Got {int(self.pos[pid])}% of the way"


GAMES = [CandyBash, LookAway, RedLight]
