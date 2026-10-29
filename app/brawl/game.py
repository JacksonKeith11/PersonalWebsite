"""Board Brawl's rooms: who's in them, the board game's turns, and the minigames.

A room is made by one player and joined by code. Each round every player takes a turn (use an
item, roll, walk, maybe buy the crown, land on something), then the ghost drifts toward the
leader, then everyone plays a minigame: free-for-all, 2 v 2 or 1 v the rest. Duel spaces start a
1 v 1 mid-turn. After the last round bonus crowns are handed out, and whoever has the most crowns
(then coins) wins.

Players are meant to be mean to each other (items, traps, webs, bombs), and the game helps
whoever's behind: the ghost hunts the leader, shops are half price for the bottom half, item and
event luck leans their way, and the last rounds are the Witching Hour.

Everything is driven by `Room.tick(now)`, 20 times a second while anyone is connected. Waits
(a dice roll on screen, a bot thinking, someone taking too long) are one pending alarm,
`Room.at(delay, fn)`, since the game only ever waits for one thing at a time. The full room state
goes to everyone whenever it changes; live minigames add their own snapshots.
"""

import asyncio
import json
import logging
import random
import secrets
import time
from collections import deque

from . import board as B
from . import minigames as M

log = logging.getLogger("brawl")

TICK = 1 / 20
MAX_PLAYERS = 4
COLORS = ["#e8552f", "#4f8fe8", "#e8c22f", "#5cc46a"]
BOT_NAMES = ["Boney", "Pumpkinhead", "Wisp", "Count Beep"]
START_COINS = 10
CROWN_COST = 20
STEP_TIME = 0.32  # seconds per space walked
MAX_ITEMS = 3
ROOM_KEEP = 30 * 60  # how long a room with nobody connected lingers, for rejoining
CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # no I or O

PRIZES = [10, 6, 3, 1]  # free-for-all, by place
TEAM_PRIZE, TEAM_DRAW = 8, 3  # 2 v 2, each
SOLO_PRIZE, PACK_PRIZE = 15, 6  # 1 v the rest: the one, or each of the rest
DUEL_STAKE = 10  # a duel's winner takes up to this from the loser
GHOST_STEPS, GHOST_BITE, GHOST_BOO = 6, 10, 5

# tier: how strong it is. Gifts lean strong for whoever's behind and weak for the leader.
ITEMS = {
    "double": {"name": "Double Dice", "price": 5, "tier": 1, "target": False, "icon": "🎲",
               "desc": "Roll two dice this turn."},
    "trap": {"name": "Coin Trap", "price": 5, "tier": 1, "target": False, "icon": "🪤",
             "desc": "Hide a trap on your space. The next rival to land there pays you 10 coins."},
    "web": {"name": "Spider Web", "price": 4, "tier": 1, "target": False, "icon": "🕸️",
            "desc": "Spin a web on your space. The next rival to walk onto it is stuck there."},
    "mirror": {"name": "Magic Mirror", "price": 6, "tier": 1, "target": False, "icon": "🪞", "passive": True,
               "desc": "Just carry it: the next item aimed at you bounces back at whoever used it."},
    "curse": {"name": "Curse Doll", "price": 6, "tier": 2, "target": True, "icon": "🪆",
              "desc": "A player's next roll can only be 1, 2 or 3."},
    "hex": {"name": "Hex Broom", "price": 7, "tier": 2, "target": True, "icon": "🧹",
            "desc": "A player walks their next roll backwards."},
    "thief": {"name": "Pickpocket", "price": 8, "tier": 2, "target": True, "icon": "🧤",
              "desc": "Steal up to 10 coins from a player."},
    "hand": {"name": "Zombie Hand", "price": 6, "tier": 2, "target": True, "icon": "🧟",
             "desc": "Drag a player to your space."},
    "warp": {"name": "Warp Swap", "price": 7, "tier": 3, "target": True, "icon": "🌀",
             "desc": "Trade places with a player."},
    "bomb": {"name": "Pumpkin Bomb", "price": 9, "tier": 3, "target": False, "icon": "🎃",
             "desc": "Everyone within 3 spaces of you drops 8 coins in a pile where they stand. Anyone can grab a pile by walking over it."},
    "cauldron": {"name": "Chaos Cauldron", "price": 8, "tier": 3, "target": False, "icon": "🧪",
                 "desc": "Shuffle where everyone is standing."},
}

# What a ? space can do: (kind, good for you?, weight)
EVENTS = [("shower", 1, 4), ("tax", 1, 2), ("gift", 1, 3), ("express", 1, 2),
          ("pothole", -1, 3), ("charity", -1, 2), ("boo", -1, 2),
          ("swap", 0, 2), ("hop", 0, 1)]

# Humans get this long to act before the game does it for them.
WAIT = {"roll": 40, "path": 25, "buy": 25, "broke": 6, "shop": 30, "duel": 25, "ready": 25}


def _clean(text, n):
    text = str(text or "")
    return "".join(c for c in text if c.isprintable()).strip()[:n]


class Player:
    def __init__(self, pid, name, color, bot=False, queue=None, token=None, tab=None):
        self.id = pid
        self.name = name
        self.color = color
        self.bot = bot
        self.queue = queue
        self.token = token
        self.tab = tab
        self.connected = not bot
        self.closing = False
        self.seated = True  # False for someone watching a game that started without them
        self.reset()

    def reset(self):
        self.pos = B.START
        self.coins = START_COINS
        self.crowns = 0
        self.items = []
        self.curse = False
        self.hex = False
        self.ready = False
        self.stats = {"wins": 0, "most": START_COINS, "menace": 0}

    def view(self):
        return {"id": self.id, "name": self.name, "color": self.color, "bot": self.bot, "on": self.connected,
                "pos": self.pos, "coins": self.coins, "crowns": self.crowns, "items": self.items,
                "curse": self.curse, "hex": self.hex, "ready": self.ready, "seated": self.seated}


class Room:
    def __init__(self, code):
        self.code = code
        self.players: dict[int, Player] = {}
        self.next_id = 1
        self.host = None
        self.rounds = 10
        self.bonus = True
        self.phase = "lobby"  # lobby, board, mgintro, mg, mgresult, final
        self.order = []
        self.round = 0
        self.turn = 0
        self.step = None  # within a turn: roll, rolling, move, path, buy, shop, duel, landed
        self.dice = []
        self.left = 0
        self.back = False  # walking backwards (hexed)
        self.used_item = False
        self.shop_passing = False  # in the shop on the way past, rather than having landed there
        self.crown_at = None
        self.ghost_at = B.CROSSROADS_ID
        self.traps = {}  # space -> pid of whoever set it
        self.webs = {}  # space -> pid
        self.piles = {}  # space -> coins lying there
        self.log = []
        self.fx = []  # one-off effects for this broadcast, for the browser to animate
        self.alarm = None
        self.deadline = None  # when the current wait times out, if a human is being waited on
        self.mg = None
        self.mg_mode = None
        self.mg_bags = {}
        self.mg_start = 0.0
        self.mg_send_at = 0.0
        self.duel = None  # (challenger, opponent) while a duel is on
        self.results = None
        self.final = None
        self.dirty = True
        self.task = None
        self.clock0 = time.monotonic()
        self.now = 0.0
        self.empty_since = None

    # ------------------------------------------------------------ plumbing

    def clock(self):
        return time.monotonic() - self.clock0

    def at(self, delay, fn):
        self.alarm = (self.now + delay, fn)

    def wait_for(self, p, kind, auto, think=1.1):
        """Wait on `p` to do something; a bot or an absent player does `auto` after `think` seconds."""
        if self.auto(p):
            self.deadline = None
            self.at(think * random.uniform(0.8, 1.3), auto)
        else:
            self.deadline = self.now + WAIT[kind]
            self.at(WAIT[kind], auto)

    def auto(self, p):
        return p.bot or not p.connected

    def send(self, p, data):
        if p.bot or not p.connected or p.closing or p.queue is None:
            return
        text = data if isinstance(data, str) else json.dumps(data, separators=(",", ":"))
        try:
            p.queue.put_nowait(text)
        except asyncio.QueueFull:
            log.info("brawl: dropping %s, send queue full", p.name)
            self.hang_up(p.queue)
            p.closing = True

    @staticmethod
    def hang_up(queue):
        while not queue.empty():
            queue.get_nowait()
        queue.put_nowait(None)

    def everyone(self, data):
        text = json.dumps(data, separators=(",", ":"))
        for p in self.players.values():
            self.send(p, text)

    def humans(self):
        return [p for p in self.players.values() if not p.bot and p.connected]

    def seated(self):
        return [self.players[i] for i in self.order] if self.order else \
            [p for p in self.players.values() if p.seated]

    def say(self, text):
        self.log.append(text)
        self.log = self.log[-10:]
        self.dirty = True

    def effect(self, kind, **kw):
        self.fx.append({"k": kind, **kw})
        self.dirty = True

    def coins(self, p, n, why=None):
        """Give (or take, if n < 0) coins; returns how many actually changed hands."""
        n = max(n, -p.coins)
        p.coins += n
        p.stats["most"] = max(p.stats["most"], p.coins)
        if n:
            self.effect("coins", p=p.id, n=n)
        if why:
            self.say(why)
        return n

    def take(self, src, dst, n):
        """Move up to n coins from src to dst (a rival's doing); returns how many."""
        got = -self.coins(src, -n)
        self.coins(dst, got)
        dst.stats["menace"] += got
        return got

    def standing(self):
        """Seated players, best first."""
        return sorted(self.seated(), key=lambda p: (-p.crowns, -p.coins))

    def behind(self, p):
        """In the bottom half? (The last player, with two or three playing.)"""
        st = self.standing()
        n = max(1, len(st) // 2)
        worst = st[-n:]
        return p in worst and (p.crowns, p.coins) != (st[0].crowns, st[0].coins)

    def leader(self, p):
        st = self.standing()
        return p is st[0] and (len(st) < 2 or (p.crowns, p.coins) != (st[1].crowns, st[1].coins))

    def price(self, p, item):
        base = ITEMS[item]["price"]
        return (base + 1) // 2 if self.behind(p) else base

    def witching_from(self):
        """The first round of the Witching Hour: the last three, or the last one in a short game."""
        return self.rounds - (2 if self.rounds >= 5 else 0)

    def witching(self):
        return self.phase != "lobby" and self.round >= self.witching_from()

    # ------------------------------------------------------------ joining and leaving

    def join(self, queue, name, token, tab):
        token, tab, name = _clean(token, 40), _clean(tab, 40), _clean(name, 16) or "Player"
        p = next((q for q in self.players.values() if token and q.token == token and not q.bot), None)
        if p is not None and p.connected and p.tab != tab:
            p, token = None, ""  # a second tab of the same browser: someone new
        if p is not None:
            if p.connected and p.queue is not None:
                self.hang_up(p.queue)
            p.queue, p.tab, p.connected, p.closing = queue, tab, True, False
            if p.name != name:
                p.name = self.unique_name(name, skip=p)
            self.say(f"{p.name} is back")
        else:
            p = Player(self.next_id, self.unique_name(name), self.free_color(), queue=queue, token=token or None,
                       tab=tab)
            self.next_id += 1
            if self.phase != "lobby" or len(self.seated()) >= MAX_PLAYERS:
                if self.phase == "lobby" and any(q.bot for q in self.players.values()):
                    self.remove_bot()
                else:
                    p.seated = False
            self.players[p.id] = p
            self.say(f"{p.name} {'joined' if p.seated else 'is watching'}")
        if self.host is None or self.host not in self.players or not self.players[self.host].connected:
            self.host = p.id
        self.empty_since = None
        self.send(p, {"t": "welcome", "you": p.id, "code": self.code, "board": B.payload(), "items": ITEMS,
                      "crown": CROWN_COST, "prizes": {"ffa": PRIZES, "team": TEAM_PRIZE, "solo": SOLO_PRIZE,
                                                      "pack": PACK_PRIZE, "duel": DUEL_STAKE},
                      "max": MAX_PLAYERS})
        if self.phase in ("mgintro", "mg") and self.mg:
            self.send(p, {"t": "mg", **self.mg.full_snap(), **(self.mg.private(p.id) or {})})
        self.dirty = True
        if self.task is None:
            self.task = asyncio.get_running_loop().create_task(self.run())
        return p

    def leave(self, p, queue):
        if p.queue is not queue or not p.connected:
            return
        p.connected = False
        p.queue = None
        if self.phase == "lobby" or not p.seated:
            self.players.pop(p.id, None)
        self.say(f"{p.name} left")
        if self.host == p.id:
            nxt = next((q for q in self.players.values() if not q.bot and q.connected), None)
            if nxt:
                self.host = nxt.id
            elif p.id not in self.players:
                self.host = None
        # If the game was waiting on them, carry on without them.
        if self.phase == "board" and self.order and self.order[self.turn] == p.id and self.alarm:
            self.alarm = (min(self.alarm[0], self.now + 1.0), self.alarm[1])
            self.deadline = None
        if self.phase == "mgintro":
            self.check_ready()
        self.dirty = True

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

    def add_bot(self):
        if self.phase != "lobby" or len(self.seated()) >= MAX_PLAYERS:
            return
        taken = {q.name for q in self.players.values()}
        name = next((n for n in BOT_NAMES if n not in taken), f"Bot {self.next_id}")
        p = Player(self.next_id, name, self.free_color(), bot=True)
        self.next_id += 1
        self.players[p.id] = p
        self.dirty = True

    def remove_bot(self):
        bots = [p for p in self.players.values() if p.bot]
        if self.phase == "lobby" and bots:
            del self.players[bots[-1].id]
            self.dirty = True

    # ------------------------------------------------------------ messages

    def handle(self, p, msg):
        t = msg.get("t")
        host = p.id == self.host
        if t == "name" and self.phase == "lobby":
            p.name = self.unique_name(_clean(msg.get("name"), 16) or p.name, skip=p)
            self.dirty = True
        elif t == "bot" and host:
            self.add_bot() if msg.get("op") == "add" else self.remove_bot()
        elif t == "settings" and host and self.phase == "lobby":
            if msg.get("rounds") in (3, 5, 10, 15, 20):
                self.rounds = msg["rounds"]
            if isinstance(msg.get("bonus"), bool):
                self.bonus = msg["bonus"]
            self.dirty = True
        elif t == "start" and host and self.phase == "lobby" and len(self.seated()) >= 2:
            self.start_game()
        elif t == "again" and host and self.phase == "final":
            self.to_lobby()
        elif t == "ready" and self.phase == "mgintro" and self.mg and p.id in self.mg.ids:
            p.ready = True
            self.dirty = True
            self.check_ready()
        elif self.phase == "mg" and self.mg and p.id in self.mg.ids and self.now >= self.mg_start:
            self.mg.on(p.id, msg)
        elif self.phase == "board" and self.order and self.order[self.turn] == p.id:
            self.on_turn(p, t, msg)

    def on_turn(self, p, t, msg):
        if t == "roll" and self.step == "roll":
            self.roll(p)
        elif t == "item" and self.step == "roll":
            self.use_item(p, msg.get("item"), msg.get("target"))
        elif t == "path" and self.step == "path" and msg.get("i") in range(len(self.ways(p.pos))):
            self.go(p, self.ways(p.pos)[msg["i"]])
        elif t == "buy" and self.step == "buy":
            self.buy_crown(p, bool(msg.get("yes")))
        elif t == "shop" and self.step == "shop":
            self.shop(p, msg.get("item"))
        elif t == "duel" and self.step == "duel" and msg.get("target") in self.order and msg["target"] != p.id:
            self.start_duel(p, self.players[msg["target"]])

    # ------------------------------------------------------------ the game

    def start_game(self):
        ps = self.seated()
        random.shuffle(ps)
        self.order = [p.id for p in ps]
        for p in self.players.values():
            p.reset()
        self.round, self.turn = 1, 0
        self.traps, self.webs, self.piles = {}, {}, {}
        self.ghost_at = B.CROSSROADS_ID
        self.mg_bags = {}
        self.results = self.final = self.duel = None
        self.log = []
        self.crown_at = None
        self.move_crown(first=True)
        self.phase = "board"
        self.say(f"Turn order: {', '.join(p.name for p in ps)}")
        self.start_turn()

    def to_lobby(self):
        self.phase = "lobby"
        for p in [p for p in self.players.values() if not p.bot and not p.connected]:
            del self.players[p.id]
        while len(self.players) > MAX_PLAYERS and any(p.bot for p in self.players.values()):
            self.remove_bot()
        for i, p in enumerate(sorted(self.players.values(), key=lambda p: p.id)):
            p.seated = i < MAX_PLAYERS
            p.reset()
        self.order = []
        self.step = None
        self.alarm = self.deadline = None
        self.mg = self.results = self.final = self.duel = None
        self.dirty = True

    def current(self):
        return self.players[self.order[self.turn]]

    def start_turn(self):
        p = self.current()
        self.step = "roll"
        self.dice = []
        self.back = False
        self.used_item = False
        self.dirty = True
        self.wait_for(p, "roll", lambda: self.bot_turn(p), think=1.4)

    def bot_turn(self, p):
        if self.auto(p) and not self.used_item and p.items:
            self.bot_item(p)
        self.roll(p)

    def bot_item(self, p):
        others = [q for q in self.seated() if q is not p]
        dist = B.distances_to(self.crown_at)
        mine = dist.get(p.pos, 99)
        near = min(others, key=lambda q: dist.get(q.pos, 99))
        rich = max(others, key=lambda q: q.coins)
        top = self.standing()[0] if self.standing()[0] is not p else self.standing()[1]
        here = B.SPACES[p.pos]["kind"]
        for item in random.sample(p.items, len(p.items)):
            if item == "double" and random.random() < 0.6:
                return self.use_item(p, item)
            if item == "thief" and rich.coins >= 6:
                return self.use_item(p, item, rich.id)
            if item == "warp" and dist.get(near.pos, 99) + 5 < mine:
                return self.use_item(p, item, near.id)
            if item == "hand" and dist.get(near.pos, 99) < 8 and dist.get(near.pos, 99) + 3 < mine:
                return self.use_item(p, item, near.id)
            if item == "hex" and dist.get(near.pos, 99) <= 10 and not near.hex:
                return self.use_item(p, item, near.id)
            if item == "curse" and not top.curse:
                return self.use_item(p, item, top.id)
            if item == "bomb" and any(q.pos in B.within(p.pos, 3) and q.coins >= 5 for q in others):
                return self.use_item(p, item)
            if item == "cauldron" and mine > 15 and random.random() < 0.5:
                return self.use_item(p, item)
            if item in ("trap", "web") and here in ("blue", "red", "event") and p.pos not in self.traps \
                    and p.pos not in self.webs and random.random() < 0.45:
                return self.use_item(p, item)

    def use_item(self, p, item, target=None):
        if self.used_item or item not in p.items or ITEMS[item].get("passive"):
            return
        spec = ITEMS[item]
        q = self.players.get(target) if spec["target"] else None
        if spec["target"] and (q is None or q is p or q.id not in self.order):
            return
        if item in ("trap", "web") and (p.pos in self.traps or p.pos in self.webs):
            return
        p.items.remove(item)
        self.used_item = True
        self.effect("item", p=p.id, item=item, target=q.id if q else None)
        name = spec["name"]
        if q is not None and "mirror" in q.items:
            q.items.remove("mirror")
            self.effect("mirror", p=q.id)
            self.say(f"{q.name}'s Magic Mirror bounced {p.name}'s {name} back!")
            p, q = q, p  # q's mirror: now q uses it on p
        if item == "double":
            self.dice = [0, 0]
            self.say(f"{p.name} will roll two dice")
        elif item == "trap":
            self.traps[p.pos] = p.id
            self.say(f"{p.name} hid a coin trap")
        elif item == "web":
            self.webs[p.pos] = p.id
            self.say(f"{p.name} spun a spider web")
        elif item == "warp":
            p.pos, q.pos = q.pos, p.pos
            self.say(f"{p.name} swapped places with {q.name}")
        elif item == "thief":
            n = self.take(q, p, 10)
            self.say(f"{p.name} pickpocketed {n} coins from {q.name}")
        elif item == "curse":
            q.curse = True
            self.say(f"{p.name} cursed {q.name}: their next roll is tiny")
        elif item == "hex":
            q.hex = True
            self.say(f"{p.name} hexed {q.name}: they'll walk backwards")
        elif item == "hand":
            q.pos = p.pos
            self.say(f"A zombie hand drags {q.name} over to {p.name}")
        elif item == "bomb":
            hit = [r for r in self.seated() if r is not p and r.pos in B.within(p.pos, 3)]
            self.effect("bomb", s=p.pos)
            for r in hit:
                n = -self.coins(r, -8)
                if n:
                    self.piles[r.pos] = self.piles.get(r.pos, 0) + n
                    p.stats["menace"] += n
            self.say(f"{p.name}'s pumpkin bomb blew coins out of {', '.join(r.name for r in hit)}" if hit
                     else f"{p.name}'s pumpkin bomb hit nobody")
        elif item == "cauldron":
            ps = self.seated()
            spots = [r.pos for r in ps]
            random.shuffle(spots)
            for r, s in zip(ps, spots):
                r.pos = s
            self.say(f"{p.name} stirred the Chaos Cauldron: everyone's shuffled")
        self.dirty = True

    def roll(self, p):
        n = 2 if self.dice else 1
        top = 3 if p.curse else 10
        self.dice = [random.randint(1, top) for _ in range(n)]
        if p.curse:
            p.curse = False
            self.say(f"The curse holds {p.name} back")
        self.back = p.hex
        p.hex = False
        self.left = sum(self.dice)
        self.step = "rolling"
        self.deadline = None
        self.effect("dice", p=p.id, dice=self.dice)
        self.say(f"{p.name} rolled {' + '.join(map(str, self.dice))}" + (f" = {self.left}" if n > 1 else "")
                 + (", backwards!" if self.back else ""))
        self.at(1.6, lambda: self.walk(p))

    def ways(self, space):
        return B.SPACES[space]["prev" if self.back else "next"]

    def walk(self, p):
        """Take the next step, or stop to ask at a fork, or land."""
        self.step = "move"
        self.dirty = True
        if self.left <= 0:
            return self.land(p)
        nxt = self.ways(p.pos)
        if len(nxt) > 1:
            self.step = "path"
            self.wait_for(p, "path", lambda: self.go(p, self.bot_path(p)), think=0.8)
            return
        self.go(p, nxt[0])

    def bot_path(self, p):
        nxt = self.ways(p.pos)
        if not self.back and p.coins >= CROWN_COST and random.random() < 0.85:
            dist = B.distances_to(self.crown_at)
            return min(nxt, key=lambda s: dist.get(s, 99))
        return random.choice(nxt)

    def go(self, p, space):
        """Step onto `space`, with whatever happens when you pass through it."""
        self.deadline = None
        p.pos = space
        self.left -= 1
        self.step = "move"
        self.dirty = True
        if self.piles.get(space):
            n = self.piles.pop(space)
            self.coins(p, n, f"{p.name} scooped up a pile of {n} coins")
        if space == self.ghost_at:
            n = -self.coins(p, -GHOST_BOO)
            self.effect("boo", p=p.id)
            self.say(f"Boo! The ghost scares {n} coins out of {p.name}")
        web = self.webs.get(space)
        if web is not None and web != p.id:
            del self.webs[space]
            self.left = 0
            self.effect("web", s=space, p=p.id)
            self.say(f"{p.name} is stuck in {self.players[web].name}'s web!")
        if space == self.crown_at:
            # Always ask. Someone who can't afford it sees the price, and walks on after a moment.
            afford = p.coins >= CROWN_COST
            self.step = "buy"
            self.wait_for(p, "buy" if afford else "broke", lambda: self.buy_crown(p, afford), think=0.9)
            return
        if B.SPACES[space]["kind"] == "shop" and self.left > 0:
            return self.open_shop(p, passing=True)
        self.at(STEP_TIME, lambda: self.walk(p))

    def buy_crown(self, p, yes):
        if yes and p.coins < CROWN_COST:
            return  # can't afford it: the question stays up until they walk on
        if yes:
            self.coins(p, -CROWN_COST)
            p.crowns += 1
            self.effect("crown", p=p.id)
            self.say(f"{p.name} bought a crown!")
            self.move_crown()
        elif p.coins < CROWN_COST:
            self.say(f"{p.name} can't afford the crown yet")
        else:
            self.say(f"{p.name} walks past the crown")
        self.step = "move"
        self.deadline = None
        self.at(1.4 if yes else STEP_TIME, lambda: self.walk(p))

    def move_crown(self, first=False):
        blues = [s["id"] for s in B.SPACES if s["kind"] == "blue" and s["id"] != self.crown_at
                 and s["id"] != B.START]
        if first:
            # Somewhere nobody can reach on their first roll.
            blues = [s for s in blues if B.distances_to(s).get(B.START, 0) >= 11] or blues
        else:
            here = {p.pos for p in self.seated()}
            blues = [s for s in blues if s not in here] or blues
        self.crown_at = random.choice(blues)
        self.effect("crownmove", s=self.crown_at)
        self.dirty = True

    def land(self, p):
        space = B.SPACES[p.pos]
        owner = self.traps.get(p.pos)
        if owner is not None and owner != p.id:
            del self.traps[p.pos]
            o = self.players[owner]
            n = self.take(p, o, 10)
            self.effect("trap", s=p.pos, p=p.id)
            self.say(f"{p.name} sprang {o.name}'s trap and paid {n} coins")
        kind = space["kind"]
        x = 2 if self.witching() else 1
        self.step = "landed"
        if kind == "blue":
            self.coins(p, 3 * x)
        elif kind == "red":
            self.coins(p, -3 * x)
        elif kind == "event":
            self.event(p)
        elif kind == "item":
            self.gift(p, "A treasure chest!")
        elif kind == "portal":
            p.pos = space["to"]
            self.effect("portal", p=p.id, a=space["id"], b=space["to"])
            self.say(f"{p.name} stepped through the crypt portal")
        elif kind == "duel":
            self.step = "duel"
            self.wait_for(p, "duel", lambda: self.start_duel(p, self.bot_duel(p)), think=1.3)
            return
        elif kind == "shop":
            return self.open_shop(p, passing=False)
        self.at(1.5, self.end_turn)

    def gift(self, p, why):
        if len(p.items) >= MAX_ITEMS:
            self.coins(p, 5, f"{why} {p.name}'s pockets are full, so 5 coins instead")
            return
        # Whoever's behind gets the good stuff; the leader gets the little things.
        lean = 1 if self.behind(p) else -1 if self.leader(p) else 0
        weights = [max(0.3, 2 + lean * (spec["tier"] - 2) * 1.5) for spec in ITEMS.values()]
        item = random.choices(list(ITEMS), weights)[0]
        p.items.append(item)
        self.effect("gift", p=p.id, item=item)
        self.say(f"{why} {p.name} gets {ITEMS[item]['name']}")

    def event(self, p):
        lean = 1 if self.behind(p) else -1 if self.leader(p) else 0
        weights = [w * (1.8 if good == lean else 0.5 if good == -lean and lean else 1) for _, good, w in EVENTS]
        kind = random.choices([e for e, _, _ in EVENTS], weights)[0]
        others = [q for q in self.seated() if q is not p]
        self.effect("event", p=p.id, e=kind)
        if kind == "shower":
            n = random.randint(5, 10)
            self.coins(p, n, f"Candy shower! {p.name} catches {n} coins")
        elif kind == "tax":
            got = sum(self.take(q, p, 2) for q in others)
            self.say(f"Trick or treat! Everyone pays {p.name} 2 coins ({got} in all)")
        elif kind == "gift":
            self.gift(p, "A gift from the witch!")
        elif kind == "express":
            dist = B.distances_to(self.crown_at)
            near = [s for s, d in dist.items() if 2 <= d <= 4] or [self.crown_at]
            p.pos = random.choice(near)
            self.say(f"The hearse gives {p.name} a ride toward the crown")
        elif kind == "pothole":
            n = -self.coins(p, -6)
            self.say(f"An open grave! {p.name} drops {n} coins in it")
        elif kind == "charity":
            for q in others:
                self.coins(q, -self.coins(p, -2))
            self.say(f"Ghostly guilt! {p.name} gives everyone 2 coins")
        elif kind == "boo":
            self.ghost_at = p.pos
            n = -self.coins(p, -GHOST_BOO)
            self.effect("boo", p=p.id)
            self.say(f"The ghost appears right behind {p.name}! {n} coins scared away")
        elif kind == "swap":
            q = random.choice(others)
            p.pos, q.pos = q.pos, p.pos
            self.say(f"A bat swarm! {p.name} and {q.name} are carried off and swapped")
        elif kind == "hop":
            self.move_crown()
            self.say("The crown got restless and moved")
        self.dirty = True

    def open_shop(self, p, passing):
        """Walking past or landing on a shop: ask whether they'd like to buy anything."""
        self.shop_passing = passing
        if len(p.items) >= MAX_ITEMS:
            self.say(f"{p.name}'s pockets are full: no shopping")
            return self.leave_shop(p)
        self.step = "shop"
        self.wait_for(p, "shop", lambda: self.shop(p, self.bot_shop(p) if self.auto(p) else None), think=1.5)

    def shop(self, p, item):
        """Buy `item`, or leave if it's None. People can keep buying until they leave."""
        self.deadline = None
        if item in ITEMS and p.coins >= self.price(p, item) and len(p.items) < MAX_ITEMS:
            self.coins(p, -self.price(p, item))
            p.items.append(item)
            self.effect("bought", p=p.id, item=item)
            self.say(f"{p.name} bought {ITEMS[item]['name']}")
            more = len(p.items) < MAX_ITEMS and any(p.coins >= self.price(p, k) for k in ITEMS)
            if more and not self.auto(p):
                self.wait_for(p, "shop", lambda: self.shop(p, None))
                return
        elif item is None:
            self.say(f"{p.name} {'walks on' if self.shop_passing else 'leaves the shop'}")
        else:
            return  # can't buy that: stay in the shop
        self.leave_shop(p)

    def leave_shop(self, p):
        self.deadline = None
        if self.shop_passing:
            self.step = "move"
            self.at(STEP_TIME, lambda: self.walk(p))
        else:
            self.step = "landed"
            self.at(1.0, self.end_turn)

    def bot_shop(self, p):
        # walking past, a bot keeps enough back to stay on course for a crown
        keep, chance = (14, 0.5) if self.shop_passing else (8, 0.7)
        afford = [k for k in ITEMS if p.coins - self.price(p, k) >= keep]
        return random.choice(afford) if afford and random.random() < chance else None

    def bot_duel(self, p):
        others = [q for q in self.seated() if q is not p]
        return max(others, key=lambda q: q.coins + random.uniform(0, 6))

    def end_turn(self):
        self.turn += 1
        self.step = None
        self.dirty = True
        if self.turn >= len(self.order):
            self.turn = 0
            self.haunt()
        else:
            self.start_turn()

    def haunt(self):
        """End of the round: the ghost drifts toward the leader, then the minigame."""
        st = self.standing()
        lead = st[0]
        tied = len(st) > 1 and (st[1].crowns, st[1].coins) == (lead.crowns, lead.coins)
        if not tied:
            path = self.ghost_path(self.ghost_at, lead.pos)
            self.ghost_at = path[min(len(path) - 1, GHOST_STEPS)]
            self.effect("ghost", s=self.ghost_at, path=path[:GHOST_STEPS + 1])
            if self.ghost_at == lead.pos:
                n = -self.coins(lead, -GHOST_BITE)
                self.say(f"The ghost catches up with {lead.name}, the leader, and takes {n} coins!")
            else:
                self.say(f"The ghost drifts after {lead.name}")
        self.at(2.0 if not tied else 0.5, self.start_minigame)

    def ghost_path(self, a, b):
        """The ghost floats either way along the paths: the shortest route from a to b."""
        prev = {a: None}
        queue = deque([a])
        while queue:
            cur = queue.popleft()
            if cur == b:
                break
            for n in B.SPACES[cur]["next"] + B.SPACES[cur]["prev"]:
                if n not in prev:
                    prev[n] = cur
                    queue.append(n)
        path, cur = [], b
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        return path[::-1]

    # ------------------------------------------------------------ minigames

    def pick_game(self, mode, n, humans):
        bag = self.mg_bags.get(mode) or []
        bag = [k for k in bag if M.suits(k, mode, n, humans)]
        if not bag:
            bag = [k for k in M.GAMES if M.suits(k, mode, n, humans)]
            random.shuffle(bag)
            if self.mg and len(bag) > 1 and bag[-1] == self.mg.key:
                bag[0], bag[-1] = bag[-1], bag[0]
        key = bag.pop()
        self.mg_bags[mode] = bag
        return key

    def start_minigame(self, mode=None, ids=None):
        ps = [self.players[i] for i in ids] if ids else self.seated()
        n = len(ps)
        if mode is None:
            r = random.random()
            mode = "ffa" if n == 2 else ("ffa" if r < 0.6 else "1vn") if n == 3 else \
                "ffa" if r < 0.45 else "team" if r < 0.75 else "1vn"
        teams = None
        shuffled = random.sample(ps, n)
        if mode == "team":
            teams = [[p.id for p in shuffled[:2]], [p.id for p in shuffled[2:]]]
        elif mode == "1vn":
            teams = [[shuffled[0].id], [p.id for p in shuffled[1:]]]
        humans = sum(1 for p in ps if not self.auto(p))
        key = self.pick_game(mode, n, humans)
        self.mg = M.make(key, [p.id for p in ps], [p.id for p in ps if self.auto(p)], teams)
        self.mg_mode = mode
        self.results = None
        if mode == "duel" and all(self.auto(p) for p in ps):
            # Nobody to watch play a bot duel: settle it on the spot and show the result.
            while not self.mg.over():
                self.mg.tick(TICK)
            return self.finish_minigame()
        self.phase = "mgintro"
        for p in self.seated():
            p.ready = self.auto(p) or p not in ps
        self.deadline = self.now + WAIT["ready"]
        self.at(WAIT["ready"], self.begin_minigame)
        self.dirty = True
        self.check_ready()

    def start_duel(self, p, q):
        if self.step != "duel":
            return
        self.deadline = None
        self.duel = (p.id, q.id)
        self.say(f"{p.name} challenges {q.name} to a duel!")
        self.effect("duel", p=p.id, q=q.id)
        self.step = "landed"
        self.at(1.2, lambda: self.start_minigame("duel", [p.id, q.id]))

    def check_ready(self):
        if self.phase == "mgintro" and all(p.ready or self.auto(p) for p in self.seated()):
            self.at(0.6, self.begin_minigame)

    def begin_minigame(self):
        if self.phase != "mgintro":
            return
        self.phase = "mg"
        self.deadline = None
        self.mg_start = self.now + 3.0
        self.alarm = None
        self.dirty = True
        self.send_snap()  # so everyone's piece is in place during the countdown

    def finish_minigame(self):
        mg, mode = self.mg, self.mg_mode
        ps = [self.players[i] for i in mg.ids]
        rows = []
        if mode in ("ffa", "duel"):
            keys = {p.id: mg.key_of(p.id) for p in ps}
            for p in sorted(ps, key=lambda p: keys[p.id]):
                place = 1 + sum(1 for q in ps if keys[q.id] < keys[p.id])
                rows.append({"id": p.id, "place": place, "label": mg.label(p.id), "prize": 0})
            if mode == "ffa":
                for r in rows:
                    r["prize"] = self.coins(self.players[r["id"]], PRIZES[r["place"] - 1])
            else:
                win = [r for r in rows if r["place"] == 1]
                if len(win) == 1:
                    w, l = self.players[rows[0]["id"]], self.players[rows[1]["id"]]
                    n = self.take(l, w, DUEL_STAKE)
                    rows[0]["prize"], rows[1]["prize"] = n, -n
        else:
            tk = [mg.team_key(t) for t in mg.teams]
            for ti, team in enumerate(mg.teams):
                won = tk[ti] < tk[1 - ti]
                draw = tk[0] == tk[1]
                for pid in team:
                    p = self.players[pid]
                    if mode == "team":
                        prize = TEAM_PRIZE if won else TEAM_DRAW if draw else 0
                    else:
                        prize = (SOLO_PRIZE if ti == 0 else PACK_PRIZE) if won else 0
                    rows.append({"id": pid, "place": 1 if won or draw else 2, "label": mg.label(pid),
                                 "prize": self.coins(p, prize), "team": ti})
            rows.sort(key=lambda r: r["place"])
        for r in rows:
            if r["place"] == 1:
                self.players[r["id"]].stats["wins"] += 1
        winners = [self.players[r["id"]].name for r in rows if r["place"] == 1]
        self.say(f"{' and '.join(winners)} won {mg.name}")
        self.results = {"key": mg.key, "name": mg.name, "mode": mode, "rows": rows}
        self.phase = "mgresult"
        self.at(4.0 if all(self.auto(p) for p in ps) else 7.0, self.after_minigame)
        self.dirty = True

    def after_minigame(self):
        self.results = None
        if self.mg_mode == "duel":
            self.duel = None
            self.phase = "board"
            self.mg = None
            return self.end_turn()
        if self.round >= self.rounds:
            return self.finish_game()
        self.round += 1
        self.phase = "board"
        if self.round == self.witching_from():
            last = self.standing()[-1]
            self.say(f"The Witching Hour strikes! Spaces count double, and {last.name}, in last place, "
                     f"gets 10 coins and a gift")
            self.coins(last, 10)
            self.gift(last, "The witch's gift:")
            self.effect("witching")
        self.start_turn()

    def finish_game(self):
        ps = self.seated()
        bonus = []
        if self.bonus:
            for title, stat, desc in (("Minigame Star", "wins", "won the most minigames"),
                                      ("Coin Star", "most", "held the most coins at once"),
                                      ("Menace Star", "menace", "took the most coins from rivals")):
                best = max(p.stats[stat] for p in ps)
                if best <= 0:
                    continue
                ids = [p.id for p in ps if p.stats[stat] == best]
                for i in ids:
                    self.players[i].crowns += 1
                bonus.append({"title": title, "desc": desc, "ids": ids, "value": best})
        rows = []
        for p in sorted(ps, key=lambda p: (-p.crowns, -p.coins)):
            place = 1 + sum(1 for q in ps if (q.crowns, q.coins) > (p.crowns, p.coins))
            rows.append({"id": p.id, "place": place, "crowns": p.crowns, "coins": p.coins})
        self.final = {"bonus": bonus, "rows": rows}
        self.phase = "final"
        self.step = None
        self.alarm = self.deadline = None
        winners = [self.players[r["id"]].name for r in rows if r["place"] == 1]
        self.say(f"{' and '.join(winners)} win{'s' if len(winners) == 1 else ''} the game!")
        self.dirty = True

    # ------------------------------------------------------------ the loop

    def state(self):
        mg = None
        if self.mg and self.phase in ("mgintro", "mg"):
            mg = self.mg.info()
            mg["starts_in"] = round(self.mg_start - self.now, 3) if self.phase == "mg" else None
            mg["ids"] = self.mg.ids
            mg["mode"] = self.mg_mode
            mg["teams"] = self.mg.teams
        cur = self.order[self.turn] if self.phase == "board" and self.order else None
        prices = {k: self.price(self.players[cur], k) for k in ITEMS} if cur and self.step == "shop" else None
        return {
            "t": "state", "phase": self.phase, "host": self.host, "rounds": self.rounds, "bonus": self.bonus,
            "round": self.round, "order": self.order, "players": [p.view() for p in self.players.values()],
            "cur": cur, "step": self.step, "dice": self.dice, "left": self.left, "back": self.back,
            "used": self.used_item, "crown": self.crown_at, "ghost": self.ghost_at,
            "traps": {str(k): v for k, v in self.traps.items()}, "webs": {str(k): v for k, v in self.webs.items()},
            "piles": {str(k): v for k, v in self.piles.items()}, "witching": self.witching(),
            "log": self.log, "wait": round(self.deadline - self.now, 1) if self.deadline else None,
            "mg": mg, "results": self.results, "final": self.final, "fx": self.fx, "prices": prices,
            "duel": self.duel, "passing": self.shop_passing,
            "choices": self.ways(self.players[cur].pos) if cur and self.step == "path" else None,
        }

    def send_snap(self, extra=None):
        snap = {"t": "mg", **self.mg.snap(), **(extra or {})}
        text = json.dumps(snap, separators=(",", ":"))
        for p in self.players.values():
            priv = self.mg.private(p.id)
            self.send(p, {**snap, **priv} if priv else text)

    def tick(self, now):
        dt = now - self.now if self.now else TICK
        self.now = now
        if self.alarm and now >= self.alarm[0]:
            fn = self.alarm[1]
            self.alarm = None
            fn()
        if self.phase == "mg" and self.mg and now >= self.mg_start:
            self.mg.tick(min(dt, 0.1))
            if self.mg.over():
                self.send_snap({"end": True})
                self.finish_minigame()
            elif now >= self.mg_send_at:
                self.mg_send_at = now + 1 / self.mg.hz - 0.001
                self.send_snap()
        if self.dirty:
            self.dirty = False
            self.everyone(self.state())
            self.fx = []

    async def run(self):
        log.info("brawl: room %s running", self.code)
        next_t = time.monotonic()
        try:
            while self.humans():
                try:
                    self.tick(self.clock())
                except Exception:
                    log.exception("brawl: tick failed in room %s", self.code)
                next_t += TICK
                delay = next_t - time.monotonic()
                if delay < -0.5:
                    next_t = time.monotonic()
                await asyncio.sleep(max(0.0, delay))
        finally:
            self.task = None
            self.empty_since = time.monotonic()
            log.info("brawl: room %s idle", self.code)


ROOMS: dict[str, Room] = {}


def sweep():
    now = time.monotonic()
    for code in [c for c, r in ROOMS.items() if r.empty_since and now - r.empty_since > ROOM_KEEP]:
        del ROOMS[code]


def new_room():
    sweep()
    while True:
        code = "".join(secrets.choice(CODE_LETTERS) for _ in range(4))
        if code not in ROOMS:
            ROOMS[code] = Room(code)
            return ROOMS[code]


def find_room(code):
    sweep()
    return ROOMS.get(_clean(code, 8).upper())
