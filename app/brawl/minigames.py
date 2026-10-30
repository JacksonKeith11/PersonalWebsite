"""Board Brawl's minigames, the server's half.

Two kinds:
- "Solo" games (pump, quick draw, needle, copycat, count, whack-a-bat, odd ghost out)
  are played in each browser against content the server deals out, the same for everyone. The
  browser reports progress and a final score. Like Frag Arena, the browser is trusted: it's for
  friends.
- "Live" games run here: the arena games (bumper ring, candy grab, ghost tag, pumpkin drop) at
  20 Hz from each browser's stick and dash; tug of doom from pumps; trivia and draw-and-guess
  from answers and guesses; potion math is trivia with sums.

Formats: "ffa" (everyone for themselves), "duel" (two players, from a duel space), "team" (2 v 2)
and "1vn" (one against the rest). Each game lists the formats it suits in `modes`.

Every game ranks players by `key_of(pid)`, lowest first; equal keys share a place. Teams are
ranked by `team_key(team)`, by default their best player's key. Bots (and anyone disconnected
when the game starts) are played here.
"""

import math
import random

from . import content

ARENA = 100.0  # arena games happen on a 100 x 100 field


def _r(x):
    return round(x, 2)


def _nums(v, n, lo, hi):
    """A list of exactly n numbers, clamped, or None."""
    if not isinstance(v, list) or len(v) != n or not all(isinstance(x, (int, float)) for x in v):
        return None
    return [min(hi, max(lo, x)) for x in v]


class Minigame:
    key = name = rules = controls = ""
    modes = {"ffa", "duel", "team"}
    dur = 20.0
    hz = 10
    min_players = 2
    needs_humans = 0  # e.g. someone has to draw

    def __init__(self, ids, bots, teams=None, humans=()):
        self.ids = list(ids)
        self.bots = set(bots)
        self.teams = teams  # [[pid, ...], [pid, ...]] or None
        self.humans = [pid for pid in ids if pid not in self.bots]
        self.params = {}
        self.t = 0.0  # seconds since the game started
        self.score = {}  # pid -> final score, for solo games
        self.prog = {pid: None for pid in self.ids}  # what others see of your progress

    def info(self):
        return {"key": self.key, "name": self.name, "rules": self.rules, "controls": self.controls,
                "dur": self.dur, "params": self.params}

    def tick(self, dt):
        self.t += dt
        self.bot_tick(dt)

    def bot_tick(self, dt):
        pass

    def on(self, pid, msg):
        pass

    def over(self):
        return self.t >= self.dur or all(pid in self.score for pid in self.ids)

    def snap(self):
        return {"prog": {str(k): v for k, v in self.prog.items()}}

    def full_snap(self):
        return self.snap()

    def private(self, pid):
        return None

    def key_of(self, pid):
        raise NotImplementedError

    def team_key(self, team):
        return min(self.key_of(pid) for pid in team)

    def label(self, pid):
        return ""


# ---------------------------------------------------------------- solo games


class Scripted(Minigame):
    """A solo game whose bots post progress at set times: [(t, prog, final_score_or_None)]."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.plans = {}

    def bot_tick(self, dt):
        for pid, plan in self.plans.items():
            while plan and plan[0][0] <= self.t:
                _, prog, final = plan.pop(0)
                self.prog[pid] = prog
                if final is not None:
                    self.score[pid] = final

    def on(self, pid, msg):
        if pid in self.bots or pid in self.score:
            return
        if msg.get("t") == "prog":
            self.prog[pid] = self.clean_prog(msg.get("v"))
        elif msg.get("t") == "done":
            s = self.clean_score(msg.get("v"))
            if s is not None:
                self.score[pid] = s
                self.prog[pid] = self.clean_prog(msg.get("v"))

    def clean_prog(self, v):
        if isinstance(v, list):
            return [x for x in v[:12] if isinstance(x, (int, float))]
        return None

    def clean_score(self, v):
        raise NotImplementedError


class Pump(Minigame):
    key, name = "pump", "Boo-lloon Pump"
    rules = "Pump up your ghost balloon until it pops: left, right, left, right. The same key twice does nothing. First to pop wins."
    controls = "Alternate ← and → (or A and D). On a phone, tap left then right."
    dur = 20.0
    TARGET = 60

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.params = {"target": self.TARGET}
        self.count = {pid: 0 for pid in self.ids}
        self.last = {pid: -1.0 for pid in self.ids}
        self.fin = {}
        self.rate = {pid: random.uniform(6.0, 8.8) for pid in self.bots}
        self.acc = {pid: 0.0 for pid in self.bots}

    def bot_tick(self, dt):
        for pid in self.bots:
            self.acc[pid] += self.rate[pid] * dt * random.uniform(0.6, 1.4)
            while self.acc[pid] >= 1:
                self.acc[pid] -= 1
                self.pump(pid)

    def pump(self, pid):
        if pid in self.fin:
            return
        self.count[pid] += 1
        self.prog[pid] = self.count[pid]
        if self.count[pid] >= self.TARGET:
            self.fin[pid] = self.t

    def on(self, pid, msg):
        # 20 pumps a second is faster than anyone mashes; it stops a held key or a script.
        if msg.get("t") == "pump" and pid not in self.bots and self.t - self.last[pid] >= 0.05:
            self.last[pid] = self.t
            self.pump(pid)

    def over(self):
        return self.t >= self.dur or len(self.fin) == len(self.ids)

    def key_of(self, pid):
        return (0, self.fin[pid]) if pid in self.fin else (1, -self.count[pid])

    def label(self, pid):
        return f"Popped in {self.fin[pid]:.2f}s" if pid in self.fin else f"{self.count[pid]} / {self.TARGET} pumps"


class QuickDraw(Scripted):
    key, name = "draw", "Quick Draw"
    rules = "Three rounds. When the coffin bursts open, hit it as fast as you can. Jump the gun and that round costs you a full second."
    controls = "Space, click or tap."
    dur = 26.0
    PAUSE = 1.3  # between rounds, in the browser too

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.params = {"delays": [round(random.uniform(1.4, 4.2), 2) for _ in range(3)], "pause": self.PAUSE}
        for pid in self.bots:
            t, times, plan = 0.0, [], []
            for d in self.params["delays"]:
                ms = 1000 if random.random() < 0.08 else random.randint(230, 430)
                t += d + ms / 1000
                times.append(ms)
                plan.append((t, list(times), sum(times) if len(times) == 3 else None))
                t += self.PAUSE
            self.plans[pid] = plan

    def clean_score(self, v):
        v = _nums(v, 3, 80, 1000)
        return None if v is None else int(sum(v))

    def key_of(self, pid):
        return self.score.get(pid, 99999)

    def label(self, pid):
        return f"{self.score[pid] / 1000:.2f}s in all" if pid in self.score else "No time"


class Needle(Scripted):
    key, name = "needle", "Stop the Needle"
    rules = "The witch's needle swings, faster each try. Stop it dead centre. Three tries; the smallest total miss wins."
    controls = "Space, click or tap."
    dur = 22.0

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.params = {"speeds": [0.55, 0.85, 1.25], "phase": [round(random.random(), 3) for _ in range(3)]}
        for pid in self.bots:
            t, misses, plan = 0.0, [], []
            for _ in range(3):
                t += random.uniform(1.5, 4.0)
                misses.append(random.randint(2, 40))
                plan.append((t, list(misses), sum(misses) if len(misses) == 3 else None))
                t += 1.0
            self.plans[pid] = plan

    def clean_score(self, v):
        v = _nums(v, 3, 0, 100)
        return None if v is None else int(sum(v))

    def key_of(self, pid):
        return self.score.get(pid, 999)

    def label(self, pid):
        return f"{self.score[pid]}% off centre in all" if pid in self.score else "Didn't finish"


class Memory(Scripted):
    key, name = "memory", "Copycat Spell"
    rules = "Watch the spell's arrows, then cast them back. Each round adds one. One slip and you're out; the longest spell wins."
    controls = "Arrow keys or WASD, or tap the arrows."
    dur = 60.0
    START, MAX = 3, 10

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.params = {"seq": [random.randrange(4) for _ in range(self.MAX)], "start": self.START, "max": self.MAX}
        for pid in self.bots:
            reach = min(self.MAX, max(self.START - 1, int(random.gauss(6.5, 1.6))))
            t, plan = 0.0, []
            for n in range(self.START, reach + 2):
                if n > self.MAX:
                    break
                t += n * 0.55 + 0.6 + n * random.uniform(0.35, 0.6)
                done = n - 1 if n > reach else n
                final = n == reach + 1 or n == self.MAX
                plan.append((t, [done, round(t, 2)], [done, round(t, 2)] if final else None))
            self.plans[pid] = plan

    def clean_score(self, v):
        v = _nums(v, 2, 0, self.dur)
        return None if v is None else [min(self.MAX, int(v[0])), v[1]]

    def key_of(self, pid):
        s = self.score.get(pid) or self.prog.get(pid) or [0, self.dur]
        return (-s[0], s[1])

    def label(self, pid):
        s = self.score.get(pid) or self.prog.get(pid)
        return f"Remembered {s[0]}" if s else "Remembered nothing"


class Count(Scripted):
    key, name = "count", "Count the Creeps"
    rules = "Three rounds. Creepy critters pop up for a few seconds: count the ones you're asked for. Your misses add up over the rounds; the smallest total wins, and ties go to the quicker."
    controls = "Watch, then pick your number: arrows or typing, Enter to lock in."
    SHOW, ANS, REVEAL, ROUNDS = 6.0, 5.0, 1.5, 3
    dur = ROUNDS * (SHOW + ANS + REVEAL) + 0.5
    SHAPES = ["bat", "ghost", "pumpkin", "spider"]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        rounds, self.answers = [], []
        for _ in range(self.ROUNDS):
            target = random.choice(self.SHAPES)
            answer = random.randint(7, 15)
            others = random.randint(16, 24)
            items = [target] * answer + [random.choice([s for s in self.SHAPES if s != target]) for _ in range(others)]
            random.shuffle(items)
            crit = []
            for i, kind in enumerate(items):
                at = 0.2 + (self.SHOW - 1.4) * i / len(items) + random.uniform(-0.15, 0.15)
                crit.append([kind, random.randint(8, 92), random.randint(12, 88), round(max(0.0, at), 2)])
            rounds.append({"target": target, "items": crit})
            self.answers.append(answer)
        self.params = {"rounds": rounds, "show": self.SHOW, "ans": self.ANS, "reveal": self.REVEAL, "life": 1.1}
        span = self.SHOW + self.ANS + self.REVEAL
        for pid in self.bots:
            plan, miss, took = [], 0, 0.0
            for r, answer in enumerate(self.answers):
                guess = answer + random.choice([-3, -2, -1, -1, 0, 0, 0, 1, 1, 2])
                wait = random.uniform(1.2, 4.5)
                miss += abs(guess - answer)
                took += wait
                last = r == self.ROUNDS - 1
                plan.append((r * span + self.SHOW + wait, [r + 1], [miss, round(took, 2)] if last else None))
            self.plans[pid] = plan

    def clean_score(self, v):
        v = _nums(v, 2, 0, 999)
        if v is None or self.t < (self.ROUNDS - 1) * (self.SHOW + self.ANS + self.REVEAL) + self.SHOW - 0.5:
            return None
        return [int(v[0]), v[1]]

    def clean_prog(self, v):
        # just how many rounds they've answered, so nobody sees a guess before the reveal
        return [min(self.ROUNDS, int(v[0]))] if isinstance(v, list) and v and isinstance(v[0], (int, float)) else None

    def key_of(self, pid):
        if pid not in self.score:
            return (999, 0)
        return tuple(self.score[pid])

    def label(self, pid):
        if pid not in self.score:
            return "Didn't finish"
        m = self.score[pid][0]
        return "Spot on every time" if m == 0 else f"Off by {m} in all"


class BatWhack(Scripted):
    key, name = "whack", "Whack-a-Bat"
    rules = "Bats pop out of the graves: whack them for a point. Don't whack the ghosts: they cost you two."
    controls = "Click or tap the graves, or the keys Q W E / A S D / Z X C."
    dur = 22.0
    UP = 0.9

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        pops, t = [], 0.6
        while t < self.dur - 2:
            pops.append([round(t, 2), random.randrange(9), "ghost" if random.random() < 0.22 else "bat"])
            t += random.uniform(0.28, 0.6)
        self.params = {"pops": pops, "up": self.UP}
        for pid in self.bots:
            skill = random.uniform(0.55, 0.85)
            score, plan = 0, []
            for p in pops:
                if p[2] == "bat" and random.random() < skill:
                    score += 1
                elif p[2] == "ghost" and random.random() < 0.12:
                    score -= 2
                if len(plan) == 0 or p[0] - plan[-1][0] > 2:
                    plan.append((p[0] + 0.5, [score], None))
            plan.append((pops[-1][0] + 1.2, [score], score))
            self.plans[pid] = plan

    def clean_score(self, v):
        v = _nums(v, 1, -99, 999)
        return None if v is None else int(v[0])

    def key_of(self, pid):
        s = self.score.get(pid)
        if s is None:
            s = (self.prog.get(pid) or [-99])[0]
        return -s

    def team_key(self, team):
        return sum(self.key_of(pid) for pid in team)

    def label(self, pid):
        return f"{-self.key_of(pid)} points"


class OddOne(Scripted):
    key, name = "odd", "Odd Ghost Out"
    rules = "One critter in each crowd is different. Find it. Six crowds; a wrong pick costs two seconds. Quickest wins."
    controls = "Click or tap the odd one."
    dur = 50.0
    ROUNDS = 6

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        rounds = []
        for i in range(self.ROUNDS):
            cols = [4, 5, 5, 6, 6, 7][i]
            rows = [3, 3, 4, 4, 5, 5][i]
            rounds.append({"cols": cols, "rows": rows, "odd": random.randrange(cols * rows),
                           "kind": random.choice(["ghost", "pumpkin", "bat", "skull"]),
                           "diff": random.choice(["eye", "mouth", "tilt", "shade", "small"]),
                           "seed": random.randrange(1 << 30)})
        self.params = {"rounds": rounds}
        for pid in self.bots:
            t, plan = 0.0, []
            for i in range(self.ROUNDS):
                t += random.uniform(2.0, 6.5) + (2 if random.random() < 0.2 else 0)
                if t > self.dur:
                    break
                plan.append((t, [i + 1, round(t, 2)], [i + 1, round(t, 2)] if i == self.ROUNDS - 1 else None))
            self.plans[pid] = plan

    def clean_score(self, v):
        v = _nums(v, 2, 0, 999)
        return None if v is None else [min(self.ROUNDS, int(v[0])), v[1]]

    def key_of(self, pid):
        s = self.score.get(pid) or self.prog.get(pid) or [0, 999]
        return (-s[0], s[1])

    def label(self, pid):
        s = self.score.get(pid) or self.prog.get(pid) or [0]
        if s[0] == self.ROUNDS:
            return f"All six in {s[1]:.1f}s"
        return f"Found {int(s[0])}"


# ---------------------------------------------------------------- live games


class Trivia(Minigame):
    key, name = "trivia", "Trivia Night"
    rules = "Four questions, ten seconds each. Right answers score, and quick right answers score more."
    controls = "Click or tap an answer, or press 1-4."
    ASK, SHOW, N = 10.0, 3.0, 4
    dur = N * (ASK + SHOW)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.qs = self.make_qs()
        self.picks = [{} for _ in self.qs]  # pid -> (answer, seconds taken)
        self.points = {pid: 0 for pid in self.ids}
        self.bot_plan = {pid: [(random.uniform(2, 8), random.random() < 0.6) for _ in self.qs] for pid in self.bots}

    def make_qs(self):
        return content.trivia(self.N)

    def where(self):
        i = min(self.N - 1, int(self.t // (self.ASK + self.SHOW)))
        into = self.t - i * (self.ASK + self.SHOW)
        return i, into

    def bot_tick(self, dt):
        i, into = self.where()
        if into >= self.ASK:
            return
        for pid in self.bots:
            when, right = self.bot_plan[pid][i]
            if into >= when and pid not in self.picks[i]:
                a = self.qs[i]["a"] if right else random.choice([k for k in range(4) if k != self.qs[i]["a"]])
                self.answer(pid, i, a, into)

    def answer(self, pid, i, a, into):
        self.picks[i][pid] = (a, into)
        if a == self.qs[i]["a"]:
            self.points[pid] += int(500 + 500 * (1 - into / self.ASK))

    def on(self, pid, msg):
        i, into = self.where()
        if msg.get("t") == "ans" and msg.get("q") == i and into < self.ASK and pid not in self.picks[i] \
                and msg.get("a") in range(4) and pid not in self.bots:
            self.answer(pid, i, msg["a"], into)

    def over(self):
        return self.t >= self.dur

    def snap(self):
        i, into = self.where()
        q = self.qs[i]
        asking = into < self.ASK
        s = {"i": i, "n": self.N, "q": q["q"], "opts": q["opts"], "asking": asking,
             "left": _r((self.ASK - into) if asking else (self.ASK + self.SHOW - into)),
             "in": [pid for pid in self.picks[i]], "pts": {str(k): v for k, v in self.points.items()}}
        if not asking:
            s["a"] = q["a"]
            s["picks"] = {str(k): v[0] for k, v in self.picks[i].items()}
        return s

    def key_of(self, pid):
        return -self.points[pid]

    def team_key(self, team):
        return -sum(self.points[pid] for pid in team)

    def label(self, pid):
        right = sum(1 for i, q in enumerate(self.qs) if self.picks[i].get(pid, (None,))[0] == q["a"])
        return f"{right} of {self.N} right, {self.points[pid]} points"


class PotionMath(Trivia):
    """Trivia's rules with sums: everyone races the same sum, and the first right answer gets a
    bonus on top of the speed points."""
    key, name = "math", "Potion Math"
    rules = "Race to brew the same potions: work out each sum and pick the answer. Quick right answers score more, and the first right answer gets a bonus. A wrong one costs you."
    controls = "Click or tap an answer, or press 1-4."
    ASK, SHOW, N = 7.0, 2.0, 6
    dur = N * (ASK + SHOW)
    FIRST, WRONG = 400, 200

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.first = [None] * self.N
        self.bot_plan = {pid: [(random.uniform(1.6, 5.5), random.random() < 0.8) for _ in self.qs] for pid in self.bots}

    def make_qs(self):
        qs = []
        for text, ans in content.sums(self.N + 2)[2:]:  # skip the two easiest
            wrong = set()
            while len(wrong) < 3:
                w = ans + random.choice([-10, -2, -1, 1, 2, 10, random.randint(-6, 6)])
                if w != ans and w >= 0:
                    wrong.add(w)
            opts = [ans, *wrong]
            random.shuffle(opts)
            qs.append({"q": f"{text} = ?", "opts": [str(o) for o in opts], "a": opts.index(ans)})
        return qs

    def answer(self, pid, i, a, into):
        super().answer(pid, i, a, into)
        if a == self.qs[i]["a"]:
            if self.first[i] is None:
                self.first[i] = pid
                self.points[pid] += self.FIRST
        else:
            self.points[pid] -= self.WRONG

    def snap(self):
        s = super().snap()
        s["ask"] = self.ASK
        if not s["asking"]:
            s["first"] = self.first[s["i"]]
        return s


class Sketch(Minigame):
    key, name = "sketch", "Sketchy Spirits"
    rules = "One player draws the secret word; everyone else types guesses. Guess it first to win. The artist scores when people get it."
    controls = "Artist: drag to draw. Everyone else: type a guess and press Enter."
    modes = {"ffa"}
    dur = 70.0
    min_players = 3
    needs_humans = 2
    MAX_OPS = 6000

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.artist = random.choice(self.humans) if self.humans else self.ids[0]
        self.word = content.word()
        self.ops = []  # ["n", x, y] starts a line, ["l", x, y] continues it, ["c"] clears
        self.sent = 0
        self.got = {}  # pid -> seconds
        self.feed = []
        self.bot_plan = {pid: random.uniform(18, 60) if random.random() < 0.5 else None for pid in self.bots}
        self.params = {"artist": self.artist, "hint": " ".join("_" if c != " " else " " for c in self.word)}

    def private(self, pid):
        return {"word": self.word} if pid == self.artist else None

    def bot_tick(self, dt):
        if not self.ops:
            return  # nobody guesses a blank page
        for pid, when in self.bot_plan.items():
            if when is not None and self.t >= when and pid not in self.got and pid != self.artist:
                self.got[pid] = self.t
                self.feed.append([pid, None])

    def on(self, pid, msg):
        t = msg.get("t")
        if t == "ink" and pid == self.artist and len(self.ops) < self.MAX_OPS:
            for op in (msg.get("ops") or [])[:200]:
                if isinstance(op, list) and op and op[0] == "c":
                    self.ops.append(["c"])
                elif isinstance(op, list) and len(op) == 3 and op[0] in ("n", "l") \
                        and all(isinstance(v, (int, float)) for v in op[1:]):
                    self.ops.append([op[0], _r(min(100, max(0, op[1]))), _r(min(100, max(0, op[2])))])
        elif t == "guess" and pid != self.artist and pid not in self.got:
            text = "".join(c for c in str(msg.get("text", ""))[:40].lower() if c.isalnum() or c == " ").strip()
            if not text:
                return
            if text.replace(" ", "") == self.word.replace(" ", ""):
                self.got[pid] = self.t
                self.feed.append([pid, None])
            else:
                self.feed.append([pid, text])
            self.feed = self.feed[-30:]

    def over(self):
        guessers = [pid for pid in self.ids if pid != self.artist]
        return self.t >= self.dur or all(pid in self.got for pid in guessers)

    def snap(self):
        s = {"from": self.sent, "ops": self.ops[self.sent:], "feed": self.feed[-8:],
             "got": [pid for pid in self.got], "left": _r(self.dur - self.t)}
        self.sent = len(self.ops)
        return s

    def full_snap(self):
        # for someone (re)joining: everything so far, without moving on what the others were sent
        return {"from": 0, "ops": self.ops, "feed": self.feed[-8:], "got": list(self.got),
                "left": _r(self.dur - self.t)}

    def key_of(self, pid):
        if pid == self.artist:
            if not self.got:
                return (2, 0)
            return (0, sum(self.got.values()) / len(self.got) + 0.01)
        return (0, self.got[pid]) if pid in self.got else (1, 0)

    def label(self, pid):
        if pid == self.artist:
            n = len(self.got)
            return f"Drew “{self.word}”: {n} got it"
        return f"Got it in {self.got[pid]:.1f}s" if pid in self.got else "Didn't get it"


class Tug(Minigame):
    key, name = "tug", "Tug of Doom"
    rules = "Two against two over a bubbling pit. Mash to haul the rope your way. Drag the other team in to win."
    controls = "Mash Space, or tap the rope."
    modes = {"team"}
    dur = 20.0
    PULL = 0.022

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.rope = 0.0  # -1: team 0 wins, +1: team 1 wins
        self.side = {pid: (-1 if pid in self.teams[0] else 1) for pid in self.ids}
        self.last = {pid: -1.0 for pid in self.ids}
        self.pumps = {pid: 0 for pid in self.ids}
        self.rate = {pid: random.uniform(6.5, 9) for pid in self.bots}
        self.acc = {pid: 0.0 for pid in self.bots}

    def pull(self, pid):
        if abs(self.rope) < 1:
            self.rope = max(-1.0, min(1.0, self.rope + self.side[pid] * self.PULL))
            self.pumps[pid] += 1

    def bot_tick(self, dt):
        for pid in self.bots:
            self.acc[pid] += self.rate[pid] * dt * random.uniform(0.6, 1.4)
            while self.acc[pid] >= 1:
                self.acc[pid] -= 1
                self.pull(pid)

    def on(self, pid, msg):
        if msg.get("t") == "pump" and pid not in self.bots and self.t - self.last[pid] >= 0.05:
            self.last[pid] = self.t
            self.pull(pid)

    def over(self):
        return self.t >= self.dur or abs(self.rope) >= 1

    def snap(self):
        return {"rope": round(self.rope, 3), "side": {str(k): v for k, v in self.side.items()}}

    def key_of(self, pid):
        return 0 if self.rope * self.side[pid] > 0 else 1 if self.rope != 0 else 0

    def team_key(self, team):
        return self.key_of(team[0])

    def label(self, pid):
        return f"{self.pumps[pid]} heaves"


class Disc:
    R = 4.2

    def __init__(self, pid, x, y):
        self.pid = pid
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.ix = self.iy = 0.0  # the stick, length up to 1
        self.dash_cd = 0.0
        self.dash_t = 0.0  # time left on an active dash
        self.dash_req = False
        self.alive = True
        self.out_t = None
        self.coins = 0
        self.lives = 2
        self.safe = 0.0  # untouchable for a moment after a hit
        self.think = 0.0
        self.goal = None


class ArenaGame(Minigame):
    hz = 20
    ACC, DRAG = 95.0, 3.0  # top speed ACC / DRAG ≈ 32 a second
    DASH, DASH_CD = 42.0, 1.6
    WALLS = False

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.discs = {}
        n = len(self.ids)
        for i, pid in enumerate(self.ids):
            a = -math.pi / 2 + 2 * math.pi * i / n
            self.discs[pid] = Disc(pid, 50 + 24 * math.cos(a), 50 + 24 * math.sin(a))

    def acc_of(self, d):
        return self.ACC

    def on(self, pid, msg):
        d = self.discs.get(pid)
        if d is None or pid in self.bots or msg.get("t") != "in":
            return
        try:
            x, y = float(msg.get("x", 0)), float(msg.get("y", 0))
        except (TypeError, ValueError):
            return
        if not (math.isfinite(x) and math.isfinite(y)):
            return
        m = math.hypot(x, y)
        if m > 1:
            x, y = x / m, y / m
        d.ix, d.iy = x, y
        if msg.get("dash"):
            d.dash_req = True

    def tick(self, dt):
        self.t += dt
        self.bot_tick(dt)
        live = [d for d in self.discs.values() if d.alive]
        for d in live:
            d.dash_cd = max(0.0, d.dash_cd - dt)
            d.dash_t = max(0.0, d.dash_t - dt)
            d.safe = max(0.0, d.safe - dt)
            if d.dash_req and d.dash_cd == 0:
                self.dash(d)
            d.dash_req = False
            acc = self.acc_of(d)
            d.vx += d.ix * acc * dt
            d.vy += d.iy * acc * dt
            f = math.exp(-self.DRAG * dt)
            d.vx *= f
            d.vy *= f
            d.x += d.vx * dt
            d.y += d.vy * dt
        for i, a in enumerate(live):
            for b in live[i + 1:]:
                self.collide(a, b)
        if self.WALLS:
            for d in live:
                for axis in ("x", "y"):
                    v = getattr(d, axis)
                    if v < Disc.R or v > ARENA - Disc.R:
                        setattr(d, axis, min(ARENA - Disc.R, max(Disc.R, v)))
                        setattr(d, "v" + axis, -getattr(d, "v" + axis) * 0.7)
        self.after_move(live, dt)

    def dash(self, d):
        dx, dy = (d.ix, d.iy) if math.hypot(d.ix, d.iy) > 0.2 else (d.vx, d.vy)
        m = math.hypot(dx, dy)
        if m > 0.01:
            d.vx += dx / m * self.DASH
            d.vy += dy / m * self.DASH
            d.dash_cd, d.dash_t = self.DASH_CD, 0.3

    def collide(self, a, b):
        dx, dy = b.x - a.x, b.y - a.y
        dist = math.hypot(dx, dy)
        if dist >= 2 * Disc.R or dist == 0:
            return
        if self.touch(a, b):
            return
        nx, ny = dx / dist, dy / dist
        push = (2 * Disc.R - dist) / 2
        a.x -= nx * push
        a.y -= ny * push
        b.x += nx * push
        b.y += ny * push
        closing = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
        if closing <= 0:
            return
        # A bouncy, even trade, plus a kick so bumps feel like bumps. A dash hits harder and
        # shrugs off more of the push back.
        j = closing * 0.75 + 3
        ja = j * (1.6 if b.dash_t > 0 else 1.0) * (0.5 if a.dash_t > 0 else 1.0)
        jb = j * (1.6 if a.dash_t > 0 else 1.0) * (0.5 if b.dash_t > 0 else 1.0)
        a.vx -= nx * ja
        a.vy -= ny * ja
        b.vx += nx * jb
        b.vy += ny * jb
        self.bumped(a, b)

    def touch(self, a, b):
        """Two discs met. Return True to skip the bounce."""
        return False

    def bumped(self, a, b):
        pass

    def after_move(self, live, dt):
        pass

    def steer(self, d, tx, ty, jitter=0.25):
        dx, dy = tx - d.x, ty - d.y
        m = math.hypot(dx, dy) or 1
        d.ix = dx / m + random.uniform(-jitter, jitter)
        d.iy = dy / m + random.uniform(-jitter, jitter)
        m = math.hypot(d.ix, d.iy) or 1
        d.ix, d.iy = d.ix / m, d.iy / m

    def flee(self, d, threats, jitter=0.3):
        """Steer away from the threats and from the walls."""
        fx = fy = 0.0
        for x, y in threats:
            dx, dy = d.x - x, d.y - y
            m = math.hypot(dx, dy) or 0.1
            fx += dx / m / m * 30
            fy += dy / m / m * 30
        for wall, axis, sign in ((d.x, "x", 1), (ARENA - d.x, "x", -1), (d.y, "y", 1), (ARENA - d.y, "y", -1)):
            push = sign * 6 / max(wall, 1) ** 1.5
            if axis == "x":
                fx += push
            else:
                fy += push
        self.steer(d, d.x + fx * 50, d.y + fy * 50, jitter)

    def snap(self):
        return {"d": [[d.pid, _r(d.x), _r(d.y), int(d.alive), int(d.dash_t > 0), d.coins, d.lives]
                      for d in self.discs.values()]}


class Bumper(ArenaGame):
    key, name = "bumper", "Bumper Ring"
    rules = "Shove everyone off the crumbling tombstone. It shrinks as you go. Last one standing wins."
    controls = "WASD or arrows to roll, Space to dash. On a phone, drag to roll and tap DASH."
    dur = 45.0
    R0, R1, SHRINK = 44.0, 16.0, 32.0

    def radius(self):
        return self.R0 - (self.R0 - self.R1) * min(1.0, self.t / self.SHRINK)

    def after_move(self, live, dt):
        r = self.radius()
        for d in live:
            if math.hypot(d.x - 50, d.y - 50) > r:
                d.alive = False
                d.out_t = self.t
                d.vx = d.vy = 0

    def bot_tick(self, dt):
        r = self.radius()
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if not d.alive or d.think > 0:
                continue
            d.think = random.uniform(0.12, 0.25)
            if math.hypot(d.x - 50, d.y - 50) > r - 9:
                self.steer(d, 50, 50, 0.1)
                continue
            foes = [o for o in self.discs.values() if o.alive and o is not d and not self.mate(d, o)]
            if not foes:
                continue
            o = min(foes, key=lambda o: math.hypot(o.x - d.x, o.y - d.y))
            # aim a little past them, away from the centre, to push them out
            ax, ay = o.x - 50, o.y - 50
            m = math.hypot(ax, ay) or 1
            self.steer(d, o.x + ax / m * 4, o.y + ay / m * 4)
            if math.hypot(o.x - d.x, o.y - d.y) < 15 and random.random() < 0.35:
                d.dash_req = True

    def mate(self, a, b):
        return bool(self.teams) and any(a.pid in t and b.pid in t for t in self.teams)

    def over(self):
        alive = [d.pid for d in self.discs.values() if d.alive]
        if self.t >= self.dur or len(alive) <= (0 if len(self.ids) < 2 else 1):
            return True
        return bool(self.teams) and sum(1 for t in self.teams if any(p in alive for p in t)) <= 1

    def snap(self):
        s = super().snap()
        s["r"] = _r(self.radius())
        return s

    def key_of(self, pid):
        d = self.discs[pid]
        return (0, math.hypot(d.x - 50, d.y - 50)) if d.alive else (1, -d.out_t)

    def label(self, pid):
        d = self.discs[pid]
        return "Still standing" if d.alive else f"Fell off at {d.out_t:.1f}s"


class CandyGrab(ArenaGame):
    key, name = "candy", "Candy Grab"
    rules = "Grab the candy; golden apples are worth 3. Dash into someone to knock candy out of them. Most candy wins."
    controls = "WASD or arrows to roll, Space to dash. On a phone, drag to roll and tap DASH."
    dur = 30.0
    ON_FIELD = 7
    WALLS = True

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.coins = []  # [x, y, value, ready_at]
        self.gem_at = 6.0
        for _ in range(self.ON_FIELD):
            self.spawn(1)

    def spawn(self, value, x=None, y=None, ready=0.0):
        if x is None:
            x, y = random.uniform(8, 92), random.uniform(8, 92)
        self.coins.append([min(95, max(5, x)), min(95, max(5, y)), value, self.t + ready])

    def after_move(self, live, dt):
        for d in live:
            for c in list(self.coins):
                if c[3] <= self.t and math.hypot(c[0] - d.x, c[1] - d.y) < Disc.R + 2.5:
                    self.coins.remove(c)
                    d.coins += c[2]
                    if c[2] == 1 and sum(1 for k in self.coins if k[2] == 1) < self.ON_FIELD:
                        self.spawn(1)
        if self.t >= self.gem_at:
            self.gem_at = self.t + random.uniform(5, 8)
            self.spawn(3)

    def bumped(self, a, b):
        for hitter, victim in ((a, b), (b, a)):
            if hitter.dash_t > 0 and victim.dash_t == 0 and victim.coins > 0:
                n = min(3, victim.coins)
                victim.coins -= n
                for _ in range(n):
                    ang = random.uniform(0, 2 * math.pi)
                    self.spawn(1, victim.x + 12 * math.cos(ang), victim.y + 12 * math.sin(ang), ready=0.4)
                hitter.dash_t = 0

    def bot_tick(self, dt):
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if d.think > 0:
                continue
            d.think = random.uniform(0.15, 0.3)
            ready = [c for c in self.coins if c[3] <= self.t + 0.3]
            rich = [o for o in self.discs.values() if o is not d and o.coins >= 3
                    and math.hypot(o.x - d.x, o.y - d.y) < 14]
            if rich and d.dash_cd == 0 and random.random() < 0.4:
                o = rich[0]
                self.steer(d, o.x, o.y, 0.05)
                d.dash_req = True
            elif ready:
                c = min(ready, key=lambda c: math.hypot(c[0] - d.x, c[1] - d.y) / c[2])
                self.steer(d, c[0], c[1])

    def snap(self):
        s = super().snap()
        s["c"] = [[_r(c[0]), _r(c[1]), c[2]] for c in self.coins]
        return s

    def key_of(self, pid):
        return -self.discs[pid].coins

    def team_key(self, team):
        return sum(self.key_of(pid) for pid in team)

    def label(self, pid):
        n = self.discs[pid].coins
        return f"{n} candy"


class OneVsMany(ArenaGame):
    """One player (teams[0][0]) against the rest, who win if any of them is still in at the end."""
    modes = {"1vn"}
    WALLS = True

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.solo = self.teams[0][0]
        self.params = {"solo": self.solo}
        n = len(self.ids) - 1
        for i, pid in enumerate(p for p in self.ids if p != self.solo):
            a = -math.pi / 2 + 2 * math.pi * i / max(n, 1)
            d = self.discs[pid]
            d.x, d.y = 50 + 34 * math.cos(a), 50 + 34 * math.sin(a)
        s = self.discs[self.solo]
        s.x, s.y = 50, 50

    def escape(self, d, threats, jitter=0.15):
        """Steer the way that keeps furthest from the threats half a second on, out of the corners."""
        best, pick = -1e9, (0.0, 0.0)
        for i in range(16):
            a = 2 * math.pi * i / 16
            x, y = d.x + math.cos(a) * 16, d.y + math.sin(a) * 16
            room = min(x, ARENA - x, y, ARENA - y)
            score = min(math.hypot(x - tx, y - ty) for tx, ty in threats) + min(0.0, room - 14) * 2.5
            if score > best:
                best, pick = score, (x, y)
        self.steer(d, pick[0], pick[1], jitter)

    def runners(self):
        return [d for pid, d in self.discs.items() if pid != self.solo]

    def out(self, d):
        d.alive = False
        d.out_t = self.t
        d.vx = d.vy = 0

    def over(self):
        return self.t >= self.dur or not any(d.alive for d in self.runners())

    def solo_won(self):
        return not any(d.alive for d in self.runners())

    def key_of(self, pid):
        won = self.solo_won() if pid == self.solo else not self.solo_won()
        return 0 if won else 1

    def team_key(self, team):
        return self.key_of(team[0])


class GhostTag(OneVsMany):
    """Freeze tag: the ghost freezes whoever it touches, and a runner thaws a frozen friend by
    touching them. The ghost wins by having everyone frozen at once."""
    key, name = "tag", "Ghost Tag"
    rules = "One of you is the ghost: touch the others to freeze them. Touch a frozen friend to thaw them; the ice melts by itself after a few seconds anyway. The ghost wins if everyone's frozen at once; otherwise the living win."
    controls = "WASD or arrows to roll, Space to dash. On a phone, drag to roll and tap DASH."
    dur = 30.0
    GHOST = 1.0  # the ghost's acceleration, against the runners'
    GHOST_DASH_CD = 1.0  # the ghost's dash recharges faster than everyone else's
    THAW = 3.5  # a frozen runner thaws by themselves after this long

    def dash(self, d):
        super().dash(d)
        if d.pid == self.solo and d.dash_cd:
            d.dash_cd = self.GHOST_DASH_CD

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.frozen = {}  # pid -> (x, y, when they thaw)
        self.freezes = 0
        self.thaws = {pid: 0 for pid in self.ids}

    def acc_of(self, d):
        if d.pid in self.frozen:
            return 0.0
        return self.ACC * (self.GHOST if d.pid == self.solo else 1.0)

    def touch(self, a, b):
        ghost = a if a.pid == self.solo else b if b.pid == self.solo else None
        if ghost is not None:
            r = b if ghost is a else a
            if r.pid in self.frozen or r.safe > 0:
                return False
            self.frozen[r.pid] = (r.x, r.y, self.t + self.THAW)
            self.freezes += 1
            r.vx = r.vy = 0
            return True
        for x, y in ((a, b), (b, a)):
            if x.pid in self.frozen and y.pid not in self.frozen:
                del self.frozen[x.pid]
                x.safe = 1.0  # a moment to get away
                self.thaws[y.pid] += 1
        return False

    def after_move(self, live, dt):
        for pid, (x, y, until) in list(self.frozen.items()):
            d = self.discs[pid]
            d.x, d.y, d.vx, d.vy = x, y, 0.0, 0.0
            if self.t >= until and not self.solo_won():
                del self.frozen[pid]
                d.safe = 1.0

    def solo_won(self):
        return all(r.pid in self.frozen for r in self.runners())

    def over(self):
        return self.t >= self.dur or self.solo_won()

    def bot_tick(self, dt):
        g = self.discs[self.solo]
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if d.think > 0 or pid in self.frozen:
                continue
            d.think = random.uniform(0.12, 0.22)
            if pid == self.solo:
                free = [r for r in self.runners() if r.pid not in self.frozen and r.safe == 0]
                if free:
                    r = min(free, key=lambda r: math.hypot(r.x - d.x, r.y - d.y))
                    self.steer(d, r.x + r.vx * 0.3, r.y + r.vy * 0.3, 0.2)
                    if math.hypot(r.x - d.x, r.y - d.y) < 14 and random.random() < 0.25:
                        d.dash_req = True
                continue
            gd = math.hypot(g.x - d.x, g.y - d.y)
            stuck = [self.discs[p] for p in self.frozen]
            if stuck and gd > 22:
                f = min(stuck, key=lambda f: math.hypot(f.x - d.x, f.y - d.y))
                self.steer(d, f.x, f.y, 0.15)
            else:
                self.escape(d, [(g.x, g.y)])
                if gd < 12 and random.random() < 0.3:
                    d.dash_req = True

    def snap(self):
        s = super().snap()
        s["fz"] = {str(pid): _r(f[2] - self.t) for pid, f in self.frozen.items()}
        return s

    def label(self, pid):
        if pid == self.solo:
            return f"Ghost: {self.freezes} freeze{'s' if self.freezes != 1 else ''}"
        if pid in self.frozen:
            return "Frozen at the end"
        n = self.thaws[pid]
        return f"Free, thawed {n} friend{'s' if n != 1 else ''}" if n else "Free at the end"


class PumpkinDrop(OneVsMany):
    key, name = "drop", "Pumpkin Drop"
    rules = "One of you flies a bat that drops pumpkins; everyone else dodges the shadows. Two hits and you're out. If anyone's left, the dodgers win."
    controls = "WASD or arrows to move, Space to dash (or drop, if you're the bat). On a phone, drag and tap the button."
    dur = 30.0
    FALL, BLAST, DROP_CD, BAT_SPEED = 0.95, 9.5, 0.7, 58.0

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.pumpkins = []  # [x, y, lands_at]
        self.booms = []  # [x, y, t] for the browser
        self.cd = 0.0
        bat = self.discs[self.solo]
        bat.lives = 0

    def tick(self, dt):
        bat = self.discs[self.solo]
        # The bat flies over everything: move it before the discs, and keep it out of their way.
        bat.x = min(97, max(3, bat.x + bat.ix * self.BAT_SPEED * dt))
        bat.y = min(97, max(3, bat.y + bat.iy * self.BAT_SPEED * dt))
        self.cd = max(0.0, self.cd - dt)
        if bat.dash_req and self.cd == 0:
            self.pumpkins.append([bat.x, bat.y, self.t + self.FALL])
            self.cd = self.DROP_CD
        bat.dash_req = False
        bx, by = bat.x, bat.y
        bat.alive = False
        super().tick(dt)
        bat.alive = True
        bat.x, bat.y, bat.vx, bat.vy = bx, by, 0, 0
        for p in [p for p in self.pumpkins if p[2] <= self.t]:
            self.pumpkins.remove(p)
            self.booms.append([_r(p[0]), _r(p[1]), _r(self.t)])
            for r in self.runners():
                if r.alive and r.safe == 0 and math.hypot(r.x - p[0], r.y - p[1]) < self.BLAST:
                    r.lives -= 1
                    r.safe = 1.0
                    if r.lives <= 0:
                        self.out(r)
        self.booms = [b for b in self.booms if self.t - b[2] < 1]

    def bot_tick(self, dt):
        for pid in self.bots:
            d = self.discs[pid]
            d.think -= dt
            if d.think > 0 or (pid != self.solo and not d.alive):
                continue
            d.think = random.uniform(0.1, 0.2)
            if pid == self.solo:
                live = [r for r in self.runners() if r.alive]
                if live:
                    if d.goal not in [r.pid for r in live] or random.random() < 0.05:
                        d.goal = random.choice(live).pid
                    r = self.discs[d.goal]
                    tx, ty = r.x + r.vx * self.FALL * 0.7, r.y + r.vy * self.FALL * 0.7
                    self.steer(d, tx, ty, 0.05)
                    if math.hypot(tx - d.x, ty - d.y) < 6:
                        d.dash_req = True
            else:
                # a person takes about a third of a second to spot a new shadow
                near = [(p[0], p[1]) for p in self.pumpkins if p[2] - self.t < self.FALL - 0.3
                        and math.hypot(p[0] - d.x, p[1] - d.y) < self.BLAST + 8]
                if near:
                    self.escape(d, near, 0.2)
                elif random.random() < 0.2:
                    self.steer(d, random.uniform(15, 85), random.uniform(15, 85), 0.4)

    def snap(self):
        s = super().snap()
        s["pk"] = [[_r(p[0]), _r(p[1]), _r(p[2] - self.t)] for p in self.pumpkins]
        s["bm"] = self.booms
        return s

    def label(self, pid):
        if pid == self.solo:
            n = sum(1 for r in self.runners() if not r.alive)
            return f"Bat: squashed {n}"
        d = self.discs[pid]
        return "Survived" if d.alive else f"Squashed at {d.out_t:.1f}s"


from . import arcade, classics, showdown  # noqa: E402  (their games build on the classes above)

GAMES = {g.key: g for g in (Pump, QuickDraw, Needle, Memory, Count, BatWhack, OddOne,
                            Trivia, PotionMath, Sketch, Tug, Bumper, CandyGrab, GhostTag, PumpkinDrop, *arcade.GAMES,
                            *classics.GAMES, *showdown.GAMES)}


def suits(key, mode, n_players, n_humans):
    g = GAMES[key]
    return mode in g.modes and n_players >= g.min_players and n_humans >= g.needs_humans


def make(key, ids, bots, teams=None):
    return GAMES[key](ids, bots, teams)
