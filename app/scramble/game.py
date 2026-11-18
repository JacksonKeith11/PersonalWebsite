"""Scramble: an obstacle-course race for 1-8 players, with bots for empty lanes.

Every round is a new course (course.py). Each browser runs its own player's physics and tells
the server where it is; the server passes everyone's position on, runs the bots along the course's
route, and decides who finished when. Players don't touch each other, so nothing needs agreeing
between browsers beyond the clock (moving platforms and saws are a function of the race time).
Points by finishing place each round; most points after the last round wins.

Item boxes sit at the start of every other obstacle. A racer holds one item at a time and uses it
when they like; the server rolls it (nastier the further back they are), decides who it hits from
everyone's positions, and broadcasts it (`fx`). A browser named in `to` applies the hit to its own
player; the server applies it to bots.
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
AFTER_FIRST = 25  # seconds the rest get once someone has finished, at least
AFTER_SHARE = 0.7  # or this share of the winner's time, if that's longer
RACE_LIMIT = 210
RESULTS_TIME = 8
SEGMENTS = (7, 11)  # obstacle segments in the first and the last round
KNOCKOUT = 1.2  # seconds a knocked-out racer waits before going back to their flag (js/main.js too)

# Items. Effects that last are timed on the server (for bots, and so everyone can see them).
ITEMS = ("bolt", "freeze", "trap", "swap", "shield", "boost", "curse", "grapple")
FREEZE, FREEZE_SPEED = 2.5, 0.5  # seconds, and how fast the frozen run
BOOST, BOOST_SPEED = 2.0, 1.5
CURSE, CURSE_SPEED = 3.0, 0.6  # seconds a curse reverses a racer's controls (bots: run this slowly)
INCOMING = 0.7  # seconds between a bolt or freeze being used and it landing: time to put a shield up
HATS = 9  # how many hats there are to pick from (js/main.js draws them; 0 is none)
EMOTES = 6  # how many emotes (js/main.js has them)
EMOTE_GAP = 1.2  # seconds between one racer's emotes
RECORD_LEAST = 1.0  # a segment run quicker than this isn't believed (no segment is that short)
TRAP_LIFE, TRAP_W = 12, 40
DASH_PACE = 1.3  # a bot dashing across a jump gets over it this much quicker
ICE_RISK = 1.15
BOT_PATIENCE = 8  # seconds a bot waits for a good moment to use an item  # bots fluff segments this much more often on snow's ice
GRAB_REACH = 120  # how far from a box a browser may claim it from (it's checked loosely)


def item_weights(f, ahead, behind):
    """How likely each item is for a racer `f` of the way back (0 leading, 1 last), with `ahead`
    racers still running in front of them and `behind` behind."""
    if not ahead and not behind:
        return {"boost": 1.0}
    return {
        "shield": 3 - 2 * f,
        "boost": 1 + 3 * f,
        "trap": (3 - 1.5 * f) if behind else 0,
        "bolt": (1 + 3 * f) if ahead else 0,
        "freeze": 4 * f if ahead else 0,
        "swap": 3 * f if ahead and f >= 0.5 else 0,
        "curse": 2 * f if ahead else 0,
        "grapple": 2.5 * f if ahead and f >= 0.4 else 0,
    }


class Player:
    def __init__(self, pid, name, color, queue=None, token=None, tab=None, bot=False):
        self.id, self.name, self.color = pid, name, color
        self.queue, self.token, self.tab, self.bot = queue, token, tab, bot
        self.connected = True
        self.closing = False
        self.points = 0
        self.racing = False
        self.hat = random.randrange(1, HATS) if bot else 0
        self.emoted = -99.0
        self.reset()

    def reset(self):
        self.x, self.y, self.face, self.air, self.dead = 60.0, 0.0, 1, 0, 0
        self.fin = None  # race time when they crossed the line
        self.gain = 0
        self.item = None
        self.shield = False
        self.frozen_until = self.boost_until = self.cursed_until = 0.0
        # this round's numbers, for the results: knocked out, items used, landed on others, taken
        self.falls = self.used = self.landed = self.taken = 0
        self.seg, self.seg_t = 0, 0.0  # the segment they're in, and the race time they entered it
        self.boxes = set()  # the boxes they've had an item from this round
        self.safe = (60.0, 0.0)  # the last place they stood (where a swap puts someone)
        self.trap_pending = False  # used a trap in the air: it's dropped when they land
        self.use_at = None  # bots: when to use the item they hold
        self.wary = set()  # bots: traps that have already caught them
        # bots only
        self.leg, self.leg_t, self.fail_leg, self.down = 0, 0.0, None, 0.0
        self.skill = random.uniform(0.62, 0.92)
        self.legs = None  # their way round, if not the course's (`Room.route_for`)
        self.calm = set()  # segments they're taking the slow, safe way through
        self.ride = None  # (boards at, gets off at): riding a lift
        self.dashing = False  # dashing across the jump they're on
        self.got_at = 0.0  # race time they got the item they hold


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
        self.alts = {}  # other ways through some segments, for bots (course.build)
        self.t0 = 0.0  # monotonic time the race started (after the countdown)
        self.ends = None  # race time the round ends, once someone has finished
        self.until = 0.0  # monotonic time the results screen ends
        self.order = []  # ids in finishing order
        self.traps = []  # [id, x, y, w, owner, until]
        self.next_trap = 1
        self.incoming = []  # [lands at, item, user, [targets]]: bolts and freezes on their way
        self.records = {}  # segment name -> [seconds, racer's name]: the room's best through each kind
        self.new_records = []  # this round's: [segment name, seconds, racer's name]
        self.awards = []  # this round's: [title, player id]
        self.themes = []
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
        if t == "grab":
            self.grab(p, msg.get("i"))
            return
        if t == "use":
            self.use(p)
            return
        if t == "emote":
            self.emote(p, msg.get("k"))
            return
        if t == "hat" and type(msg.get("v")) is int and 0 <= msg["v"] < HATS:
            p.hat = msg["v"]
            self.send_state()
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
        dead = int(bool(v[4]))
        if dead and not p.dead:
            p.falls += 1
        p.face, p.air, p.dead = (-1 if v[2] < 0 else 1), (2 if v[3] == 2 else int(bool(v[3]))), dead
        self.timed(p)
        if not p.air and not p.dead:
            p.safe = (p.x, p.y)
            if p.trap_pending:
                self.drop_trap(p)
        # nobody gets round a course faster than flat out with no obstacles
        if p.x >= self.course["finish"] and self.now() > self.course["finish"] / C.RUN * 0.8:
            self.finished(p)

    # ------------------------------------------------------------ a round

    def start_round(self):
        self.round += 1
        lo, hi = SEGMENTS
        n = lo + round((hi - lo) * (self.round - 1) / max(1, self.rounds - 1))
        self.course, self.legs, self.risks, self.alts = C.build(random.getrandbits(32), n)
        if not self.themes:
            self.themes = random.sample(C.THEMES, len(C.THEMES))
        self.course["theme"] = self.themes.pop()
        self.phase = "race"
        self.t0 = time.monotonic() + COUNTDOWN
        self.ends = None
        self.order = []
        self.traps = []
        self.incoming = []
        self.new_records, self.awards = [], []
        seats = [p for p in self.players.values() if p.bot or p.connected][:MAX_PLAYERS]
        for p in self.players.values():
            p.reset()
            p.racing = p in seats
            if p.bot:
                p.legs = self.route_for(p)
        for p in self.players.values():
            self.send_course(p)

    def send_course(self, p):
        self.send(p, {"t": "course", "round": self.round, "course": self.course, "now": round(self.now(), 3)})

    def timed(self, p):
        """Time racers through each segment: the room keeps the best through each kind."""
        segs = self.course["segs"]
        now = self.now()
        was = p.seg
        while p.seg + 1 < len(segs) and p.x >= segs[p.seg + 1] + 30:
            p.seg += 1
        if p.seg != was:
            # just got through an obstacle (one at a time: a jump past several isn't a run through them)
            if p.seg >= 2 and p.seg == was + 1 and p.seg_t is not None and now - p.seg_t >= RECORD_LEAST:
                name, secs = self.course["names"][p.seg - 1], round(now - p.seg_t, 2)
                best = self.records.get(name)
                if best is None or secs < best[0]:
                    self.records[name] = [secs, p.name]
                    self.new_records = [r for r in self.new_records if r[0] != name] + [[name, secs, p.name]]
            p.seg_t = max(0.0, now)

    def finished(self, p):
        self.timed(p)
        p.fin = round(self.now(), 2)
        if p.bot and random.random() < 0.5:
            self.emote(p, 5 if self.order else 4)  # GG, or a flame for the winner
        self.order.append(p.id)
        if self.ends is None:
            self.ends = min(RACE_LIMIT, p.fin + max(AFTER_FIRST, AFTER_SHARE * p.fin))
        self.send_state()

    def route_for(self, p):
        """A bot's way round: where a segment has a slow, safe way through (the fork's trench), the
        clumsier the bot, the likelier it takes it."""
        legs = self.legs
        for seg, alt in self.alts.items():
            if random.random() < 0.15 + 0.9 * (0.92 - p.skill):
                at = [i for i, leg in enumerate(legs) if leg[7] == seg]
                legs = legs[:at[0]] + alt + legs[at[-1] + 1:]
                p.calm.add(seg)
        return legs

    def bot_legs(self, p):
        return p.legs or self.legs

    def ride(self, p, leg):
        """A bot waiting for a lift to come down, then riding it up. Lifts move with the race clock,
        so this goes by the clock, not the bot's pace."""
        kind, x0, y0, x1, y1, _, mover, seg = leg
        top, dy, period, phase = (self.course["movers"][mover][i] for i in (1, 5, 6, 7))
        now = self.now()
        if p.ride is None:
            # the lift is at the bottom when sin(2 pi t / period + phase) = 1
            first = (math.pi / 2 - phase) / (2 * math.pi) * period
            board = first + math.ceil((now - first) / period) * period
            p.ride = (board, board + period / 2)
        board, off = p.ride
        if now < board:
            p.x, p.y = x0, y0
        else:
            u = min(1.0, (now - board) / 0.3)
            p.x = x0 + (x1 - x0) * u
            p.y = top + dy * math.sin(2 * math.pi * now / period + phase)
        p.air = 0
        if now >= off:
            p.ride, p.leg, p.leg_t = None, p.leg + 1, 0.0
            p.x, p.y = x1, y1

    def move_bot(self, p, dt):
        """Walk a bot along its legs; now and then it fluffs a segment and starts it again."""
        if p.fin is not None:
            return
        legs = self.bot_legs(p)
        if p.down > 0:
            p.down -= dt
            if p.down <= 0:  # back to the start of the segment it fell in
                seg = legs[p.leg][7]
                p.leg = next(i for i, leg in enumerate(legs) if leg[7] == seg)
                p.leg_t, p.dead, p.ride, p.dashing = 0.0, 0, None, False
            return
        if legs[p.leg][0] == "ride":
            self.ride(p, legs[p.leg])
            self.timed(p)
            return
        theme = self.course.get("theme")
        pace = dt * p.skill * self.speed(p)
        if legs[p.leg][0] == "run" and theme == "desert":
            pace *= (1 + C.SAND) / 2  # the sand slows bots too (half as much: people can hop it)
        if p.dashing:
            pace *= DASH_PACE
        p.leg_t += pace
        while True:
            kind, x0, y0, x1, y1, secs, arc, seg = legs[p.leg]
            if p.leg_t < secs:
                break
            if p.leg + 1 == len(legs):
                p.x, p.y, p.air = x1, y1, 0
                return
            p.leg_t = 0.0 if legs[p.leg + 1][0] == "ride" else p.leg_t - secs
            p.leg += 1
            nxt = legs[p.leg]
            # a long jump: a bot that's any good dashes across it
            p.dashing = nxt[0] == "jump" and nxt[3] - nxt[1] > 150 and random.random() < p.skill - 0.2
            if nxt[7] != seg:  # a new segment: will this one go wrong?
                seg = nxt[7]
                mine = [i for i, leg in enumerate(legs) if leg[7] == seg and leg[0] == "jump"]
                risk = self.risks[seg] * (1.05 - p.skill) * 1.3 * (ICE_RISK if theme == "snow" else 1)
                bad = mine and seg not in p.calm and random.random() < risk
                p.fail_leg = random.choice(mine) if bad else None
            if nxt[0] == "ride":
                self.ride(p, nxt)
                self.timed(p)
                return
        u = p.leg_t / secs if secs else 1.0
        p.x = x0 + (x1 - x0) * u
        p.y = y0 + (y1 - y0) * u - 4 * arc * u * (1 - u)
        p.air = (2 if p.dashing and 0.25 < u < 0.7 else 1) if kind == "jump" else 0
        p.face = 1
        if not p.air:
            p.safe = (p.x, p.y)
            if p.trap_pending:
                self.drop_trap(p)
        self.timed(p)
        if p.leg == p.fail_leg and u > 0.55:
            p.fail_leg, p.dead, p.down = None, 1, KNOCKOUT
            p.falls += 1
        if p.item is None:
            for i, (bx, _) in enumerate(self.course["boxes"]):
                if i not in p.boxes and abs(p.x - bx) < 20:
                    self.grab(p, i)
        for trap in self.traps:
            tid, tx, ty, tw, owner, _ = trap
            if owner != p.id and tid not in p.wary and not p.air and abs(p.y - ty) < 6 and tx - 14 < p.x < tx + tw + 14:
                p.wary.add(tid)
                self.knock(p)
                p.falls += 1
        if p.x >= self.course["finish"]:
            self.finished(p)

    # ------------------------------------------------------------ items

    def speed(self, p):
        now = self.now()
        return ((FREEZE_SPEED if now < p.frozen_until else 1.0) *
                (BOOST_SPEED if now < p.boost_until else 1.0) *
                (CURSE_SPEED if now < p.cursed_until else 1.0))

    def running(self, but=None):
        return [q for q in self.racers() if q.fin is None and q is not but]

    def grab(self, p, i):
        if (self.phase != "race" or not p.racing or p.fin is not None or p.item is not None or p.dead
                or type(i) is not int or not 0 <= i < len(self.course["boxes"]) or i in p.boxes
                or abs(p.x - self.course["boxes"][i][0]) > GRAB_REACH):
            return
        p.boxes.add(i)
        others = self.running(but=p)
        ahead = [q for q in others if q.x > p.x]
        behind = [q for q in others if q.x <= p.x]
        done = sum(q.fin is not None for q in self.racers())
        place = done + len(ahead)
        f = place / max(1, len(self.racers()) - 1)
        weights = item_weights(min(1.0, f), len(ahead), len(behind))
        kinds = [k for k in weights if weights[k] > 0]
        p.item = random.choices(kinds, [weights[k] for k in kinds])[0]
        if p.bot:
            p.got_at = self.now()
            p.use_at = p.got_at + random.uniform(0.8, 3.5)
        self.send_state()

    def knock(self, q):
        """Knock a racer out (they go back to their flag). Browsers do it to themselves on `fx`."""
        if q.bot:
            q.dead, q.down, q.fail_leg = 1, KNOCKOUT, None
        else:
            q.dead = 1

    def checkpoint(self, x):
        segs = self.course["segs"]
        return max(i for i in range(len(segs) - 1) if segs[i] <= x)

    def place_bot(self, q, x, y):
        """Put a bot down at x: on the run it covers, or the nearest ground before it."""
        legs = self.bot_legs(q)
        runs = [i for i, L in enumerate(legs) if L[0] == "run" and L[1] <= x]
        leg = runs[-1] if runs else 0
        L = legs[leg]
        x, y = min(x, L[3]), L[2]
        q.leg, q.leg_t = leg, (x - L[1]) / C.RUN
        q.x, q.y, q.dead, q.down, q.fail_leg, q.ride, q.dashing = x, y, 0, 0.0, None, None, False
        self.warped(q)

    def warped(self, q):
        """Moved by a swap or a grapple: no record for the segment they land in."""
        q.seg, q.seg_t = self.checkpoint(q.x), None

    def drop_trap(self, p):
        p.trap_pending = False
        x, y = p.safe
        self.traps.append([self.next_trap, round(x - TRAP_W / 2), round(y), TRAP_W, p.id, self.now() + TRAP_LIFE])
        self.next_trap += 1
        self.send_state()

    def use(self, p):
        if self.phase != "race" or not p.racing or p.fin is not None or p.item is None or self.now() < 0:
            return
        item, p.item, p.use_at = p.item, None, None
        p.used += 1
        now = self.now()
        ahead = sorted((q for q in self.running(but=p) if q.x > p.x), key=lambda q: q.x)
        fx = {"t": "fx", "k": item, "by": p.id, "to": [], "blocked": []}

        if item in ("bolt", "freeze") and ahead:
            # on its way: the targets are warned, and a shield put up in time still blocks it
            to = [ahead[0].id] if item == "bolt" else [q.id for q in ahead]
            self.incoming.append([now + INCOMING, item, p.id, to])
            self.everyone({"t": "warn", "k": item, "by": p.id, "to": to, "in": INCOMING})
            for q in ahead:
                if q.bot and q.id in to and q.item == "shield" and random.random() < 0.6:
                    q.use_at = now + random.uniform(0.1, INCOMING - 0.15)
            self.send_state()
            return
        if item == "swap" and ahead:
            q = ahead[0]
            if self.hit(p, q, fx):
                mine, theirs = p.safe, q.safe
                fx["warp"] = {}
                for who, (x, y) in ((p, theirs), (q, mine)):
                    self.warp(who, x, y, fx)
        elif item == "grapple" and ahead:
            q = ahead[0]
            fx["to"].append(q.id)  # who you were pulled to (it does nothing to them)
            fx["warp"] = {}
            self.warp(p, *q.safe, fx)
        elif item == "curse" and ahead:
            q = ahead[0]
            if self.hit(p, q, fx):
                q.cursed_until = now + CURSE
        elif item == "trap":
            if p.air:
                p.trap_pending = True
            else:
                self.drop_trap(p)
        elif item == "shield":
            p.shield = True
        elif item == "boost":
            p.boost_until = now + BOOST
            fx["to"].append(p.id)
        self.everyone(fx)
        self.send_state()

    def hit(self, by, q, fx):
        """An item lands on q, unless their shield takes it."""
        if q.shield:
            q.shield = False
            fx["blocked"].append(q.id)
            return False
        fx["to"].append(q.id)
        by.landed += 1
        q.taken += 1
        if by.bot and random.random() < 0.3:
            self.emote(by, random.choice((1, 4)))
        return True

    def warp(self, who, x, y, fx):
        fx["warp"][who.id] = [round(x), round(y), self.checkpoint(x)]
        if who.bot:
            self.place_bot(who, x, y)
        else:
            who.x, who.y = x, y
            self.warped(who)
        who.safe = (x, y)

    def land_incoming(self):
        """Bolts and freezes arriving."""
        now = self.now()
        due = [i for i in self.incoming if i[0] <= now]
        if not due:
            return
        self.incoming = [i for i in self.incoming if i[0] > now]
        for _, item, by, to in due:
            p = self.players.get(by)
            if p is None:
                continue
            fx = {"t": "fx", "k": item, "by": by, "to": [], "blocked": []}
            for q in [self.players.get(i) for i in to]:
                if q is None or q not in self.running() or not self.hit(p, q, fx):
                    continue
                if item == "bolt":
                    self.knock(q)
                    q.falls += 1
                else:
                    q.frozen_until = now + FREEZE
            self.everyone(fx)
        self.send_state()

    def emote(self, p, k):
        now = time.monotonic()
        if type(k) is not int or not 0 <= k < EMOTES or now - p.emoted < EMOTE_GAP:
            return
        p.emoted = now
        self.everyone({"t": "emote", "by": p.id, "k": k})

    def bot_items(self):
        """Bots use what they hold when it'll do some good: a curse on someone in a hard segment, a
        swap or grapple when the one ahead is well ahead, a trap when someone's close behind. Held too
        long, they use it anyway if anyone's there to use it on."""
        now = self.now()
        for p in self.racers():
            if not p.bot or p.item is None or p.fin is not None or p.use_at is None or now < p.use_at:
                continue
            ahead = sorted((q for q in self.running(but=p) if q.x > p.x), key=lambda q: q.x)
            behind = [q for q in self.running(but=p) if q.x < p.x]
            impatient = now - p.got_at > BOT_PATIENCE
            gap = ahead[0].x - p.x if ahead else 0
            if p.item in ("bolt", "freeze", "swap", "curse", "grapple") and not ahead or p.item == "trap" and not behind:
                good = False
            elif p.item in ("swap", "grapple"):
                good = gap > (150 if impatient else 400)
            elif p.item == "curse":
                q = ahead[0]
                good = impatient or self.risks[self.checkpoint(q.x)] >= 0.6
            elif p.item == "freeze":
                good = impatient or len(ahead) >= 2 or gap < 900
            elif p.item == "trap":
                good = p.air == 0 and (impatient or min(p.x - q.x for q in behind) < 450)
            else:
                good = True
            if good:
                self.use(p)
            else:
                p.use_at = now + 0.5  # not yet: look again in a moment

    def end_round(self):
        # whoever didn't finish is placed by how far they got
        rest = sorted((p for p in self.racers() if p.fin is None), key=lambda p: -p.x)
        self.order += [p.id for p in rest]
        for place, pid in enumerate(self.order):
            p = self.players[pid]
            p.gain = POINTS[place] if place < len(POINTS) else 0
            p.points += p.gain
        self.awards = awards(self.racers())
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
                self.bot_items()
            self.land_incoming()
            if any(trap[5] < now for trap in self.traps):
                self.traps = [trap for trap in self.traps if trap[5] >= now]
                self.send_state()
            racers = self.racers()
            self.everyone({"t": "pos", "now": round(now, 3),
                           "ps": [[p.id, round(p.x), round(p.y), p.face, p.air, p.dead, self.marks(p, now)]
                                  for p in racers]})
            waiting = [p for p in racers if p.fin is None and (p.bot or p.connected)]
            people = [p for p in waiting if not p.bot]
            if self.ends is not None and not people and any(not p.bot for p in racers):
                self.ends = min(self.ends, now + 2)  # only bots still running: don't make people wait
            if not waiting or now > RACE_LIMIT or (self.ends is not None and now > self.ends):
                self.end_round()
        elif self.phase == "results" and time.monotonic() > self.until:
            self.start_round()
            self.send_state()

    @staticmethod
    def marks(p, now):
        """What to draw on a racer: 1 shielded, 2 frozen, 4 boosted, 8 cursed."""
        return (int(p.shield) | 2 * (now < p.frozen_until) | 4 * (now < p.boost_until)
                | 8 * (now < p.cursed_until))

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
                         "pts": p.points, "racing": p.racing, "fin": p.fin, "gain": p.gain,
                         "item": p.item, "shield": p.shield, "hat": p.hat,
                         "stats": [p.falls, p.used, p.landed, p.taken]}
                        for p in self.players.values()],
            "order": self.order,
            "records": self.new_records if self.phase == "results" else
            sorted([k, *v] for k, v in self.records.items()) if self.phase == "final" else [],
            "awards": self.awards if self.phase in ("results", "final") else [],
            "traps": [t[:5] for t in self.traps],
            "ends": self.ends,
        }
        if self.phase == "results":
            st["next"] = round(max(0.0, self.until - time.monotonic()), 1)
        self.everyone(st)


def awards(racers):
    """A few titles for the round: [title, player id], at most one each."""
    out, given = [], set()

    def give(title, p):
        if p is not None and p.id not in given:
            out.append([title, p.id])
            given.add(p.id)

    def most(key, least=1):
        best = max(racers, key=key, default=None)
        if best is None or key(best) < least or sum(key(q) == key(best) for q in racers) > 1:
            return None
        return best

    clean = [p for p in racers if p.fin is not None and p.falls == 0]
    give("Never fell", min(clean, key=lambda p: p.fin, default=None))
    give("Sharpshooter", most(lambda p: p.landed, 2))
    give("Most bolted", most(lambda p: p.taken, 2))
    give("Item hoarder", most(lambda p: p.used, 3))
    give("Bounced back", most(lambda p: p.falls if p.fin is not None else -1, 4))
    return out[:4]


ROOMS = Codes(ROOM_KEEP)
