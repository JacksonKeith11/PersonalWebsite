"""Overlords' rooms: the match around the fights.

Two to four players (bots fill the empty seats unless the host turns them off; later joiners
watch). Each round has a planning phase (buy from your shop, reroll, buy XP, arrange your board and
bench) and a fight phase. At the fight phase's start every fight of the round is simulated in one go
(sim.py) and sent to every browser with its whole timeline, so anyone can watch any fight live;
damage and gold are settled when the last fight has played out. Some rounds are monster rounds,
fought by everyone against the same monsters for gold.

A unit a player owns is {"id", "unit", "star"}, on their bench (a list of D.BENCH slots) or their
board ({(col, row): unit}, in their own coordinates, row 3 at the front). Three copies of a unit at
one star merge into one a star higher, wherever the first one on the board stood. Copies come out
of the room's shared pool when bought and go back when sold or when their owner is knocked out.
"""

import asyncio
import logging
import random
import time

from ..rooms import Codes, Refused, clean, dumps, hang_up, push
from . import bots as B
from . import data as D
from . import sim

log = logging.getLogger("overlords")

MAX_PLAYERS = 4
MAX_IN_ROOM = 10
ROOM_KEEP = 30 * 60
TICK = 0.25
COLORS = ["#d9534f", "#3f8fe8", "#e8b923", "#4fb85f"]
BOT_NAMES = ["Morgrave", "Lady Vesk", "Old Tarrow", "The Pale Duke", "Ysmay", "Brother Cull"]
BOT_LEVELS = ("easy", "normal", "hard")


class Player:
    def __init__(self, pid, name, color, queue=None, token=None, tab=None, bot=None):
        self.id, self.name, self.color = pid, name, color
        self.queue, self.token, self.tab = queue, token, tab
        self.bot = bot  # None for a person, else "easy", "normal" or "hard"
        self.connected = bot is None
        self.closing = False
        self.seated = False
        self.reset()

    def reset(self):
        self.hp = D.START_HP
        self.gold = 0
        self.level = D.START_LEVEL
        self.xp = 0
        self.bench = [None] * D.BENCH
        self.board = {}
        self.shop = [None] * D.SHOP_SIZE
        self.locked = False
        self.streak = 0  # wins in a row (positive) or losses (negative)
        self.alive = True
        self.place = None
        self.ready = False
        self.last_opp = None
        self.plan = None
        self.results = []  # "w", "l" or "d" each round

    def units(self):
        return list(self.board.values()) + [u for u in self.bench if u]

    def fight_board(self):
        return [{"unit": u["unit"], "star": u["star"], "col": c, "row": r} for (c, r), u in self.board.items()]


class Room:
    def __init__(self, code):
        self.code = code
        self.players: dict[int, Player] = {}
        self.next_id = 1
        self.host = None
        self.phase = "lobby"  # lobby, plan, fight, over
        self.bots = True
        self.bot_level = "normal"
        self.round = 0
        self.ends = 0.0
        self.pool = {}
        self.fights = []
        self.fight_started = 0.0
        self.settled = []  # what the last fight phase did to each player, for the browsers
        self.next_unit = 1
        self.rng = random.Random()
        self.task = None
        self.empty_since = None
        self.clock = time.monotonic  # the checks swap in a clock they can wind on

    # ------------------------------------------------------------ plumbing

    def send(self, p, data):
        if not p.connected or p.closing or p.queue is None:
            return
        if not push(p.queue, data, p.name, "overlords"):
            p.closing = True

    def humans(self):
        return [p for p in self.players.values() if p.bot is None and p.connected]

    def seated(self):
        return [p for p in self.players.values() if p.seated]

    def alive(self):
        return [p for p in self.seated() if p.alive]

    # ------------------------------------------------------------ joining and leaving

    def join(self, queue, name, token, tab):
        token, tab, name = clean(token, 40), clean(tab, 40), clean(name, 16) or "Player"
        p = next((q for q in self.players.values() if token and q.token == token), None)
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
                raise Refused({"t": "error", "msg": "That room is full."})
            p = Player(self.next_id, self.unique_name(name), self.free_color(), queue, token or None, tab)
            self.next_id += 1
            self.players[p.id] = p
            p.seated = self.phase == "lobby" and len(self.seated()) < MAX_PLAYERS
            p.alive = p.seated
        if self.host not in self.players or not self.players[self.host].connected:
            self.host = p.id
        self.empty_since = None
        self.send(p, self.welcome(p))
        self.send_state()
        if self.phase == "fight":
            self.send(p, self.fights_msg())
        if self.task is None:
            try:
                self.task = asyncio.get_running_loop().create_task(self.run())
            except RuntimeError:  # no event loop: the checks drive the room themselves
                pass
        return p

    def welcome(self, p):
        return {"t": "welcome", "you": p.id, "code": self.code, "units": D.UNITS, "traits": D.TRAITS,
                "rules": {"bench": D.BENCH, "shop": D.SHOP_SIZE, "reroll": D.REROLL, "xp_cost": D.XP_COST,
                          "xp_gain": D.XP_GAIN, "max_level": D.MAX_LEVEL, "level_xp": D.LEVEL_XP,
                          "odds": D.SHOP_ODDS, "start_hp": D.START_HP, "max": MAX_PLAYERS,
                          "cols": sim.COLS, "rows": sim.ROWS, "move_time": sim.MOVE_TIME,
                          "bot_levels": BOT_LEVELS, "pve": sorted(D.PVE)}}

    def leave(self, p, queue):
        if p.queue is not queue or not p.connected:
            return
        p.connected = False
        p.queue = None
        if self.phase == "lobby" or not p.seated:
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
        used = {q.color for q in self.players.values() if q.seated}
        return next((c for c in COLORS if c not in used), "#8a8580")

    # ------------------------------------------------------------ messages

    def handle(self, p, msg):
        t = msg.get("t")
        host = p.id == self.host
        if self.phase == "lobby":
            if t == "set" and host:
                if isinstance(msg.get("bots"), bool):
                    self.bots = msg["bots"]
                if msg.get("level") in BOT_LEVELS:
                    self.bot_level = msg["level"]
            elif t == "start" and host:
                self.start()
                return
            else:
                return
        elif self.phase == "over":
            if t == "again" and host:
                self.to_lobby()
            else:
                return
        elif p.seated and p.alive and self.phase in ("plan", "fight"):
            fighting = self.phase == "fight"
            if t == "buy":
                ok = self.buy(p, msg.get("i"))
            elif t == "reroll":
                ok = self.reroll(p)
            elif t == "xp":
                ok = self.buy_xp(p)
            elif t == "lock":
                p.locked = not p.locked
                ok = True
            elif t == "move":
                ok = self.move(p, msg.get("from"), msg.get("to"), fighting)
            elif t == "sell":
                ok = self.sell(p, msg.get("from"), fighting)
            elif t == "ready" and not fighting:
                p.ready = not p.ready
                if all(q.ready for q in self.alive() if q.bot is None and q.connected):
                    self.ends = min(self.ends, self.clock() + 1)
                ok = True
            else:
                return
            if not ok:
                return
        else:
            return
        self.send_state()

    # ------------------------------------------------------------ the match

    def start(self):
        for p in [p for p in self.players.values() if p.bot]:
            del self.players[p.id]
        if self.bots:
            names = self.rng.sample(BOT_NAMES, len(BOT_NAMES))
            while len(self.seated()) < MAX_PLAYERS:
                b = Player(self.next_id, names.pop(), self.free_color(), bot=self.bot_level)
                b.seated = True
                self.next_id += 1
                self.players[b.id] = b
        if len(self.seated()) < 2:
            host = self.players.get(self.host)
            if host:
                self.send(host, {"t": "note", "msg": "You need someone to play against: turn bots on or wait for a friend."})
            return
        self.pool = {k: D.POOL[D.UNITS[k]["cost"]] for k in D.shop_units()}
        for p in self.seated():
            p.reset()
        self.round = 0
        self.settled = []
        for p in self.seated():  # a free unit to start with
            key = self.draw(1)
            if key:
                self.pool[key] -= 1
                p.bench[0] = self.new_unit(key)
        self.next_round()

    def to_lobby(self):
        self.phase = "lobby"
        self.fights = []
        for q in [q for q in self.players.values() if q.bot or not q.connected]:
            del self.players[q.id]
        for i, q in enumerate(self.players.values()):
            q.seated = i < MAX_PLAYERS
            q.reset()
            q.alive = q.seated
        self.send_state()

    def new_unit(self, key, star=1):
        u = {"id": self.next_unit, "unit": key, "star": star}
        self.next_unit += 1
        return u

    def next_round(self):
        self.round += 1
        rnd = self.round
        for p in self.alive():
            if rnd > 1:
                p.xp += D.PASSIVE_XP
                self.level_up(p)
            p.gold += D.income(rnd) + min(D.MAX_INTEREST, p.gold // D.INTEREST_PER) + D.streak_gold(p.streak)
            if not p.locked or not any(p.shop):
                self.roll(p)
            p.locked = False
            p.ready = False
        self.phase = "plan"
        self.fights = []
        self.ends = self.clock() + (D.FIRST_PLAN if rnd == 1 else D.PLAN_TIME)
        for p in self.alive():
            if p.bot:
                try:
                    B.play(self, p, self.rng)
                except Exception:
                    log.exception("overlords: bot %s failed in room %s", p.name, self.code)
        self.send_state()

    def begin_fight(self):
        rnd = self.round
        alive = self.alive()
        for p in alive:
            self.fill_board(p)
        self.fights = []
        if rnd in D.PVE:
            monsters = [{"unit": k, "star": s, "col": c, "row": r} for k, s, c, r in D.PVE[rnd]]
            for p in alive:
                self.fights.append({"home": p.id, "away": 0, "pve": True, "ghost": False,
                                    "res": sim.fight(p.fight_board(), monsters, self.rng.randrange(1 << 30))})
        else:
            for a, b, ghost in self.pairings(alive):
                self.fights.append({"home": a.id, "away": b.id, "pve": False, "ghost": ghost,
                                    "res": sim.fight(a.fight_board(), b.fight_board(), self.rng.randrange(1 << 30))})
                a.last_opp = b.id
                if not ghost:
                    b.last_opp = a.id
        self.phase = "fight"
        self.fight_started = self.clock()
        longest = max((f["res"]["time"] for f in self.fights), default=0)
        self.ends = self.fight_started + longest + D.RESULT_PAUSE
        for p in self.players.values():
            self.send(p, self.fights_msg())
        self.send_state()

    def pairings(self, alive):
        """Who fights whom: [(home, away, away is a ghost copy)]. Nobody meets the same opponent
        twice running if it can be helped; with an odd number, someone fights a copy of another."""
        best = None
        for _ in range(30):
            order = alive[:]
            self.rng.shuffle(order)
            pairs = [(order[i], order[i + 1], False) for i in range(0, len(order) - 1, 2)]
            if len(order) % 2:
                odd = order[-1]
                pairs.append((odd, self.rng.choice([q for q in alive if q is not odd]), True))
            repeats = sum(a.last_opp == b.id for a, b, _ in pairs)
            if best is None or repeats < best[0]:
                best = (repeats, pairs)
            if repeats == 0:
                break
        return best[1]

    def end_fight(self):
        rnd = self.round
        self.settled = []
        hurt = {}
        for f in self.fights:
            res = f["res"]
            home = self.players[f["home"]]
            if f["pve"]:
                won = res["winner"] == 0
                if won:
                    home.gold += D.PVE_GOLD[rnd]
                else:
                    hurt[home.id] = hurt.get(home.id, 0) + D.loss_damage(rnd, res["survivors"][1])
                home.results.append("w" if won else "l")
                continue
            away = self.players[f["away"]]
            sides = [(home, 0)] if f["ghost"] else [(home, 0), (away, 1)]
            for p, side in sides:
                if res["winner"] == side:
                    p.streak = max(1, p.streak + 1)
                    p.results.append("w")
                else:
                    p.streak = min(-1, p.streak - 1)
                    p.results.append("l" if res["winner"] is not None else "d")
                    hurt[p.id] = hurt.get(p.id, 0) + D.loss_damage(rnd, res["survivors"][1 - side])
        for p in self.alive():
            dmg = hurt.get(p.id, 0)
            p.hp -= dmg
            self.settled.append({"id": p.id, "dmg": dmg})
        out = sorted((p for p in self.alive() if p.hp <= 0), key=lambda p: p.hp)
        left = len(self.alive())
        for p in out:
            p.alive = False
            p.place = left
            left -= 1
            for u in p.units():
                self.pool[u["unit"]] += 3 ** (u["star"] - 1)
            p.board, p.bench = {}, [None] * D.BENCH
        alive = self.alive()
        if len(alive) <= 1:
            for p in alive:
                p.place = 1
            self.phase = "over"
            self.fights = []
            self.send_state()
            return
        self.next_round()

    def tick(self):
        if self.phase == "plan" and self.clock() >= self.ends:
            self.begin_fight()
        elif self.phase == "fight" and self.clock() >= self.ends:
            self.end_fight()

    async def run(self):
        try:
            while self.humans():
                try:
                    self.tick()
                except Exception:
                    log.exception("overlords: tick failed in room %s", self.code)
                await asyncio.sleep(TICK)
        finally:
            self.task = None
            self.empty_since = time.monotonic()

    # ------------------------------------------------------------ the shop

    def draw(self, level):
        """A unit key for one shop slot at `level`, by the odds and what's left in the pool."""
        odds = D.SHOP_ODDS[level]
        cost = self.rng.choices(D.COSTS, odds)[0]
        for c in range(cost, 0, -1):
            keys = [k for k in D.shop_units() if D.UNITS[k]["cost"] == c and self.pool.get(k, 0) > 0]
            if keys:
                return self.rng.choices(keys, [self.pool[k] for k in keys])[0]
        return None

    def roll(self, p):
        p.shop = [self.draw(p.level) for _ in range(D.SHOP_SIZE)]

    def reroll(self, p):
        if p.gold < D.REROLL:
            return False
        p.gold -= D.REROLL
        p.locked = False
        self.roll(p)
        return True

    def level_up(self, p):
        while p.level < D.MAX_LEVEL and p.xp >= D.LEVEL_XP[p.level]:
            p.xp -= D.LEVEL_XP[p.level]
            p.level += 1
        if p.level >= D.MAX_LEVEL:
            p.xp = 0

    def buy_xp(self, p):
        if p.gold < D.XP_COST or p.level >= D.MAX_LEVEL:
            return False
        p.gold -= D.XP_COST
        p.xp += D.XP_GAIN
        self.level_up(p)
        return True

    def buy(self, p, i):
        if type(i) is not int or not 0 <= i < D.SHOP_SIZE or not p.shop[i]:
            return False
        key = p.shop[i]
        cost = D.UNITS[key]["cost"]
        if p.gold < cost or self.pool.get(key, 0) <= 0:
            return False
        free = next((j for j, u in enumerate(p.bench) if u is None), None)
        merges = sum(1 for u in p.units() if u["unit"] == key and u["star"] == 1) >= 2
        if free is None and not merges:
            return False
        p.gold -= cost
        self.pool[key] -= 1
        p.shop[i] = None
        u = self.new_unit(key)
        if free is not None:
            p.bench[free] = u
            self.merge(p, key)
        else:  # bench full, but the copy merges straight away
            spare = [x for x in p.units() if x["unit"] == key and x["star"] == 1]
            self.combine(p, spare[:2])  # the new copy is the third
        return True

    def merge(self, p, key):
        for star in (1, 2):
            same = [u for u in self.ordered(p) if u["unit"] == key and u["star"] == star]
            if len(same) >= 3:
                self.combine(p, same[:3])

    def ordered(self, p):
        """A player's units, board first (front to back, left to right), then the bench."""
        on_board = [p.board[h] for h in sorted(p.board, key=lambda h: (-h[1], h[0]))]
        return on_board + [u for u in p.bench if u]

    def combine(self, p, units):
        keep = units[0]
        for u in units[1:]:
            self.remove(p, u)
        keep["star"] += 1
        self.merge(p, keep["unit"])

    def remove(self, p, unit):
        for h, u in list(p.board.items()):
            if u is unit:
                del p.board[h]
                return
        for j, u in enumerate(p.bench):
            if u is unit:
                p.bench[j] = None
                return

    def sell_unit(self, p, unit):
        self.remove(p, unit)
        copies = 3 ** (unit["star"] - 1)
        p.gold += D.UNITS[unit["unit"]]["cost"] * copies
        self.pool[unit["unit"]] += copies

    # ------------------------------------------------------------ moving units

    def spot(self, p, where):
        """("bench", index) or ("board", (col, row)) from a browser's {"b": i} or {"c", "r"}."""
        if not isinstance(where, dict):
            return None
        if "b" in where:
            i = where["b"]
            return ("bench", i) if type(i) is int and 0 <= i < D.BENCH else None
        c, r = where.get("c"), where.get("r")
        if type(c) is int and type(r) is int and 0 <= c < sim.COLS and 0 <= r < 4:
            return ("board", (c, r))
        return None

    def at(self, p, s):
        return p.bench[s[1]] if s[0] == "bench" else p.board.get(s[1])

    def put(self, p, s, u):
        if s[0] == "bench":
            p.bench[s[1]] = u
        elif u is None:
            p.board.pop(s[1], None)
        else:
            p.board[s[1]] = u

    def move(self, p, src, dst, fighting):
        a, b = self.spot(p, src), self.spot(p, dst)
        if a is None or b is None or a == b:
            return False
        if fighting and "board" in (a[0], b[0]):
            return False
        ua, ub = self.at(p, a), self.at(p, b)
        if ua is None:
            return False
        if a[0] == "bench" and b[0] == "board" and ub is None and len(p.board) >= p.level:
            return False
        self.put(p, a, ub)
        self.put(p, b, ua)
        return True

    def sell(self, p, src, fighting):
        a = self.spot(p, src)
        if a is None or (fighting and a[0] == "board"):
            return False
        u = self.at(p, a)
        if u is None:
            return False
        self.sell_unit(p, u)
        return True

    def set_board(self, p, units):
        """Bots: put exactly these units on the board (arranged), the rest on the bench."""
        units = units[:p.level]
        rest = [u for u in p.units() if all(u is not x for x in units)]
        p.board = {(c, r): u for u, c, r in B.arrange(units)}
        p.bench = (rest + [None] * D.BENCH)[:D.BENCH]

    def fill_board(self, p):
        """At a fight's start, bench units fill any empty places on the board up to the level."""
        room = p.level - len(p.board)
        waiting = [u for u in p.bench if u]
        if room <= 0 or not waiting:
            return
        waiting.sort(key=lambda u: -D.UNITS[u["unit"]]["cost"] * 3 ** (u["star"] - 1))
        for u, c, r in B.arrange(waiting[:room], taken=set(p.board)):
            self.remove(p, u)
            p.board[(c, r)] = u

    # ------------------------------------------------------------ what the browsers see

    def fights_msg(self):
        return {"t": "fights", "round": self.round, "elapsed": round(self.clock() - self.fight_started, 2),
                "list": self.fights}

    def public(self, p):
        return {"id": p.id, "name": p.name, "color": p.color, "bot": p.bot, "on": p.connected,
                "seated": p.seated, "hp": p.hp, "level": p.level, "gold": p.gold, "alive": p.alive,
                "place": p.place, "streak": p.streak, "ready": p.ready, "results": p.results[-5:],
                "board": [[u["id"], u["unit"], u["star"], c, r] for (c, r), u in p.board.items()],
                "bench": sum(1 for u in p.bench if u),
                "traits": D.trait_counts([u["unit"] for u in p.board.values()])}

    def send_state(self):
        base = {"t": "state", "phase": self.phase, "host": self.host, "round": self.round,
                "left": round(max(0.0, self.ends - self.clock()), 1) if self.phase in ("plan", "fight") else None,
                "bots": self.bots, "level": self.bot_level, "pve": self.round in D.PVE,
                "next_pve": self.round + 1 in D.PVE, "settled": self.settled,
                "players": [self.public(p) for p in self.players.values()]}
        text = None
        for p in self.players.values():
            if not p.connected or p.bot:
                continue
            if p.seated:
                mine = dict(base, me={"shop": p.shop, "bench": [[u["id"], u["unit"], u["star"]] if u else None
                                                               for u in p.bench],
                                      "xp": p.xp, "need": D.LEVEL_XP.get(p.level), "locked": p.locked})
                self.send(p, dumps(mine))
            else:
                text = text or dumps(base)
                self.send(p, text)


ROOMS = Codes(ROOM_KEEP)
