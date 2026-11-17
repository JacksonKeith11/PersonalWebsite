"""Scramble: an obstacle-course race for 1-8 players, with bots for empty lanes.

Every round is a new course (course.py). Each browser runs its own player's physics and tells
the server where it is; the server passes everyone's position on, runs the bots along the course's
route, and decides who finished when. Players don't touch each other, so nothing needs agreeing
between browsers beyond the clock (moving platforms and saws are a function of the race time).
Points by finishing place each round; most points after the last round wins.
"""

import asyncio
import logging
import math
import random
import time

from ..rooms import Codes, Refused, clean, dumps, hang_up, push
from . import course as C

log = logging.getLogger("scramble")

TICK = 1 / 20
MAX_PLAYERS = 8
MAX_IN_ROOM = 16  # players and people watching
COLORS = ["#e8552f", "#3f8fe8", "#e8b923", "#4fb85f", "#9a5fd6", "#e86fa5", "#2fb5b0", "#8f6b3f"]
BOT_NAMES = ["Dash", "Hopper", "Skid", "Zippy", "Tumble", "Bolt", "Wobble"]
ROOM_KEEP = 30 * 60
POINTS = [10, 7, 5, 4, 3, 2, 1, 1]
ROUNDS = (3, 5, 7)
COUNTDOWN = 3.5  # seconds on the start line
AFTER_FIRST = 25  # seconds the rest get once someone has finished
RACE_LIMIT = 150
RESULTS_TIME = 8
SEGMENTS = (5, 8)  # obstacle segments in the first and the last round


class Player:
    def __init__(self, pid, name, color, queue=None, token=None, tab=None, bot=False):
        self.id, self.name, self.color = pid, name, color
        self.queue, self.token, self.tab, self.bot = queue, token, tab, bot
        self.connected = True
        self.closing = False
        self.points = 0
        self.racing = False
        self.reset()

    def reset(self):
        self.x, self.y, self.face, self.air, self.dead = 60.0, 0.0, 1, 0, 0
        self.fin = None  # race time when they crossed the line
        self.gain = 0
        # bots only
        self.leg, self.leg_t, self.fail_leg, self.down = 0, 0.0, None, 0.0
        self.skill = random.uniform(0.62, 0.92)


class Room:
    def __init__(self, code):
        self.code = code
        self.players: dict[int, Player] = {}
        self.next_id = 1
        self.host = None
        self.rounds = 5
        self.phase = "lobby"  # lobby, race, results, final
        self.round = 0
        self.course = self.legs = self.risks = None
        self.t0 = 0.0  # monotonic time the race started (after the countdown)
        self.ends = None  # race time the round ends, once someone has finished
        self.until = 0.0  # monotonic time the results screen ends
        self.order = []  # ids in finishing order
        self.task = None
        self.empty_since = None

    # ------------------------------------------------------------ plumbing

    def now(self):
        return time.monotonic() - self.t0

    def send(self, p, data):
        if p.bot or not p.connected or p.closing or p.queue is None:
            return
        if not push(p.queue, data, p.name, "scramble"):
            p.closing = True

    def everyone(self, data):
        text = dumps(data)
        for p in self.players.values():
            self.send(p, text)

    def humans(self):
        return [p for p in self.players.values() if not p.bot and p.connected]

    def racers(self):
        return [p for p in self.players.values() if p.racing]

    # ------------------------------------------------------------ joining and leaving

    def join(self, queue, name, token, tab):
        token, tab, name = clean(token, 40), clean(tab, 40), clean(name, 16) or "Player"
        p = next((q for q in self.players.values() if token and q.token == token and not q.bot), None)
        if p is not None and p.connected and p.tab != tab:
            p, token = None, ""  # a second tab of the same browser: someone new
        if p is not None:
            if p.connected and p.queue is not None:
                hang_up(p.queue)
            p.queue, p.tab, p.connected, p.closing = queue, tab, True, False
            if p.name != name:
                p.name = self.unique_name(name, skip=p)
        else:
            if len(self.players) >= MAX_IN_ROOM:
                bots = [q for q in self.players.values() if q.bot]
                if not bots or self.phase != "lobby":
                    raise Refused({"t": "error", "msg": "That room is full."})
                del self.players[bots[-1].id]
            p = Player(self.next_id, self.unique_name(name), self.free_color(), queue, token or None, tab)
            self.next_id += 1
            self.players[p.id] = p
        if self.host not in self.players or not self.players[self.host].connected:
            self.host = p.id
        self.empty_since = None
        self.send(p, {"t": "welcome", "you": p.id, "code": self.code, "max": MAX_PLAYERS, "points": POINTS})
        if self.phase == "race":
            self.send_course(p)
        self.send_state()
        if self.task is None:
            self.task = asyncio.get_running_loop().create_task(self.run())
        return p

    def leave(self, p, queue):
        if p.queue is not queue or not p.connected:
            return
        p.connected = False
        p.queue = None
        if self.phase == "lobby" or not (p.racing or p.points):
            self.players.pop(p.id, None)
        if self.host == p.id:
            nxt = next(iter(self.humans()), None)
            self.host = nxt.id if nxt else self.host
        self.send_state()

    def unique_name(self, name, skip=None):
        taken = {q.name for q in self.players.values() if q is not skip}
        if name not in taken:
            return name
        n = 2
        while f"{name[:13]} {n}" in taken:
            n += 1
        return f"{name[:13]} {n}"

    def free_color(self):
        used = {q.color for q in self.players.values()}
        return next((c for c in COLORS if c not in used), random.choice(COLORS))

    # ------------------------------------------------------------ messages

    def handle(self, p, msg):
        t = msg.get("t")
        if t == "p":
            self.moved(p, msg)
            return
        host = p.id == self.host
        if t == "bot" and host and self.phase == "lobby":
            bots = [q for q in self.players.values() if q.bot]
            if msg.get("op") == "add" and len(self.players) < MAX_PLAYERS:
                taken = {q.name for q in self.players.values()}
                name = next((n for n in BOT_NAMES if n not in taken), f"Bot {self.next_id}")
                self.players[self.next_id] = Player(self.next_id, name, self.free_color(), bot=True)
                self.next_id += 1
            elif msg.get("op") == "remove" and bots:
                del self.players[bots[-1].id]
        elif t == "rounds" and host and self.phase == "lobby" and msg.get("v") in ROUNDS:
            self.rounds = msg["v"]
        elif t == "start" and host and self.phase == "lobby":
            for q in self.players.values():
                q.points = 0
            self.round = 0
            self.start_round()
        elif t == "again" and host and self.phase == "final":
            self.phase = "lobby"
            for q in [q for q in self.players.values() if not q.bot and not q.connected]:
                del self.players[q.id]
        else:
            return
        self.send_state()

    def moved(self, p, msg):
        """A browser saying where its player is."""
        if self.phase != "race" or not p.racing or p.fin is not None:
            return
        v = msg.get("v")
        if not isinstance(v, list) or len(v) != 5 or not all(isinstance(n, (int, float)) for n in v):
            return
        x, y = float(v[0]), float(v[1])
        if not (math.isfinite(x) and math.isfinite(y)):
            return
        p.x, p.y = max(0.0, min(x, self.course["length"])), max(-2000.0, min(y, 2000.0))
        p.face, p.air, p.dead = (-1 if v[2] < 0 else 1), int(bool(v[3])), int(bool(v[4]))
        # nobody gets round a course faster than flat out with no obstacles
        if p.x >= self.course["finish"] and self.now() > self.course["finish"] / C.RUN * 0.8:
            self.finished(p)

    # ------------------------------------------------------------ a round

    def start_round(self):
        self.round += 1
        lo, hi = SEGMENTS
        n = lo + round((hi - lo) * (self.round - 1) / max(1, self.rounds - 1))
        self.course, self.legs, self.risks = C.build(random.getrandbits(32), n)
        self.phase = "race"
        self.t0 = time.monotonic() + COUNTDOWN
        self.ends = None
        self.order = []
        seats = [p for p in self.players.values() if p.bot or p.connected][:MAX_PLAYERS]
        for p in self.players.values():
            p.reset()
            p.racing = p in seats
        for p in self.players.values():
            self.send_course(p)

    def send_course(self, p):
        self.send(p, {"t": "course", "round": self.round, "course": self.course, "now": round(self.now(), 3)})

    def finished(self, p):
        p.fin = round(self.now(), 2)
        self.order.append(p.id)
        if self.ends is None:
            self.ends = min(RACE_LIMIT, p.fin + AFTER_FIRST)
        self.send_state()

    def move_bot(self, p, dt):
        """Walk a bot along the course's legs; now and then it fluffs a segment and starts it again."""
        if p.fin is not None:
            return
        if p.down > 0:
            p.down -= dt
            if p.down <= 0:  # back to the start of the segment it fell in
                seg = self.legs[p.leg][7]
                p.leg = next(i for i, leg in enumerate(self.legs) if leg[7] == seg)
                p.leg_t, p.dead = 0.0, 0
            return
        p.leg_t += dt * p.skill
        while True:
            kind, x0, y0, x1, y1, secs, arc, seg = self.legs[p.leg]
            if p.leg_t < secs:
                break
            if p.leg + 1 == len(self.legs):
                p.x, p.y, p.air = x1, y1, 0
                return
            p.leg_t -= secs
            p.leg += 1
            if self.legs[p.leg][7] != seg:  # a new segment: will this one go wrong?
                seg = self.legs[p.leg][7]
                mine = [i for i, leg in enumerate(self.legs) if leg[7] == seg and leg[0] == "jump"]
                bad = mine and random.random() < self.risks[seg] * (1.05 - p.skill) * 1.3
                p.fail_leg = random.choice(mine) if bad else None
        u = p.leg_t / secs if secs else 1.0
        p.x = x0 + (x1 - x0) * u
        p.y = y0 + (y1 - y0) * u - 4 * arc * u * (1 - u)
        p.air = int(kind == "jump")
        p.face = 1
        if p.leg == p.fail_leg and u > 0.55:
            p.fail_leg, p.dead, p.down = None, 1, 0.9
        if p.x >= self.course["finish"]:
            self.finished(p)

    def end_round(self):
        # whoever didn't finish is placed by how far they got
        rest = sorted((p for p in self.racers() if p.fin is None), key=lambda p: -p.x)
        self.order += [p.id for p in rest]
        for place, pid in enumerate(self.order):
            p = self.players[pid]
            p.gain = POINTS[place] if place < len(POINTS) else 0
            p.points += p.gain
        last = self.round >= self.rounds
        self.phase = "final" if last else "results"
        self.until = time.monotonic() + RESULTS_TIME
        self.send_state()

    def tick(self):
        if self.phase == "race":
            now = self.now()
            if now > 0:
                for p in self.racers():
                    if p.bot:
                        self.move_bot(p, TICK)
            racers = self.racers()
            self.everyone({"t": "pos", "now": round(now, 3),
                           "ps": [[p.id, round(p.x), round(p.y), p.face, p.air, p.dead] for p in racers]})
            waiting = [p for p in racers if p.fin is None and (p.bot or p.connected)]
            people = [p for p in waiting if not p.bot]
            if self.ends is not None and not people and any(not p.bot for p in racers):
                self.ends = min(self.ends, now + 2)  # only bots still running: don't make people wait
            if not waiting or now > RACE_LIMIT or (self.ends is not None and now > self.ends):
                self.end_round()
        elif self.phase == "results" and time.monotonic() > self.until:
            self.start_round()
            self.send_state()

    async def run(self):
        next_t = time.monotonic()
        try:
            while self.humans():
                try:
                    self.tick()
                except Exception:
                    log.exception("scramble: tick failed in room %s", self.code)
                next_t += TICK
                delay = next_t - time.monotonic()
                if delay < -0.5:
                    next_t = time.monotonic()
                await asyncio.sleep(max(0.0, delay))
        finally:
            self.task = None
            self.empty_since = time.monotonic()

    # ------------------------------------------------------------ what the browsers see

    def send_state(self):
        st = {
            "t": "state", "phase": self.phase, "host": self.host, "rounds": self.rounds, "round": self.round,
            "players": [{"id": p.id, "name": p.name, "color": p.color, "on": p.connected, "bot": p.bot,
                         "pts": p.points, "racing": p.racing, "fin": p.fin, "gain": p.gain}
                        for p in self.players.values()],
            "order": self.order,
            "ends": self.ends,
        }
        if self.phase == "results":
            st["next"] = round(max(0.0, self.until - time.monotonic()), 1)
        self.everyone(st)


ROOMS = Codes(ROOM_KEEP)
