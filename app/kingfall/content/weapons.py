"""The heroes' weapons. Each has a light combo, a charged heavy, a special (costs Focus) and its own
defensive move. The browser plays them (timing, animation, hit checks against the boss); the server
works out the damage from these numbers and the hero's build.

Per attack: dur (s), hit (t0, t1) when it can land, shape (as the bosses', in the aim's frame), mult
(of the weapon's base damage), poise,
step (px lunge), next (from when the next attack may follow), anim keyframes. Holding light runs the
combo and starts it again after the last hit. Ranged attacks fire `proj` (v speed, r radius, life, n, spread
degrees, pierce) instead of using a shape; `aoe` lands a circle `at` px ahead after `delay`, `ticks`
times; `blink` teleports the hero `blink` px along the aim first; `air` makes them untouchable
for that window (a leap); `hyper` keeps them from flinching when hit. A weapon's own `status`
({slot: (kind, amount)}) builds on every hit of that slot, on top of what upgrades add.

Dashes (`dodge`): `charges` a hero holds and the seconds one takes to come back (`recharge`; they
refill one at a time). A roll, dash or blink spends one; so does blocking a hit or taking the
halberd's counter stance (the guard's `cost`, in dashes). Heavier weapons hold fewer or regain them
slower; the daggers hold the most.

The defensive move (`guard.kind`): block (hold: blocks from the front, parry at first), dash (the
roll becomes a short dash with charges), counter (hold: a hit taken in the stance is absorbed and
answered), blink (the roll becomes a teleport), rollshot (the roll fires an arrow).

Every weapon has its own string and one thing only it does (Nov 2026, after Hades' weapons):
- `moves`: named attacks outside the light string, shaped like a light, with a `slot` (whose upgrades
  and statuses apply: light or heavy). `dash` is the dash-strike: light pressed during or just after a
  dodge. The sword has `riposte` (light just after a block or parry) and `rush` (heavy while blocking,
  `guarding`: hits from the front are blocked as it charges); the greatsword `spin` (the whirlwind).
- per attack: `more` (further hit windows: each strikes afresh), `pass` (the hero goes through bosses
  while it steps), `into` (a light: the move that follows while light stays held), `loop` + `drain`
  `throw` (shots loosed with a melee swing, priced as the move `as`),
  (a move repeats while light is held, spending dashes a second) + `walk` (share of speed kept),
  `whirl` (the figure turns about with each strike).
- per weapon: `backstab` (damage x this from behind a boss), `tip` (x this when struck with the outer
  part of the reach, past `tip_from` of it), `sigil` (lights mark the boss, up to `max`; a heavy or special
  spends them for +`per` each), and on the bow's heavy `power` (released within `window` s of full draw).
"""

from .moves import pose


def _blade(arm, blade):
    """The weapon's angle on the hand that makes it point `blade` degrees (0 forward, 90 up, 180 back,
    -90 down) when the arm is at `arm` (0 hanging, -90 forward, -180 up). On the rig a weapon at 0 lies
    back along the arm, so write swings with these helpers, never with raw weapon angles."""
    return 90 - blade - arm


def sw(arm, blade, **kw):
    """A pose with the weapon arm at `arm` and the blade pointing `blade`."""
    return pose(arm_f=arm, weapon=_blade(arm, blade), **kw)


def off(arm, blade, **kw):
    """The same for the off hand (the second dagger)."""
    return pose(arm_b=arm, shield=_blade(arm, blade), **kw)


def both(arm, blade, **kw):
    return pose(arm_f=arm, weapon=_blade(arm, blade), arm_b=arm, shield=_blade(arm, blade), **kw)

SWORD = {
    "dodge": {"charges": 3, "recharge": 1.0},
    "id": "sword", "name": "Sword & Shield", "art": "sword", "base": 22, "blurb": "All-rounder. Block and parry, then answer with a riposte; charge behind the shield.",
    "light": [
        {"dur": 0.36, "hit": (0.09, 0.17), "shape": {"k": "arc", "r": 42, "a0": -65, "a1": 65}, "mult": 1.0, "poise": 10,
         "step": 8, "next": 0.2,
         "anim": [(0, sw(-205, 140, torso=-8)), (0.09, sw(-120, 60, torso=2, lean=1)), (0.17, sw(-40, -25, torso=10, lean=3)), (0.36, sw(-25, -35, torso=6))]},
        {"dur": 0.36, "hit": (0.09, 0.17), "shape": {"k": "arc", "r": 42, "a0": -65, "a1": 65}, "mult": 1.0, "poise": 10,
         "step": 8, "next": 0.2,
         "anim": [(0, sw(-25, -40, torso=8)), (0.09, sw(-80, 10, torso=4, lean=2)), (0.17, sw(-165, 95, torso=-6, lean=2)), (0.36, sw(-150, 100))]},
        # a shield punch: quick, light on damage, heavy on poise
        {"dur": 0.3, "hit": (0.06, 0.13), "shape": {"k": "circle", "r": 20, "x": 22, "y": 0}, "mult": 0.7, "poise": 24,
         "step": 10, "next": 0.17,
         "anim": [(0, pose(arm_b=-30, shield=40, front=1, torso=-10, lean=-2, arm_f=-150, weapon=100)), (0.06, pose(arm_b=-95, shield=95, front=1, torso=12, lean=5, arm_f=-150, weapon=100)),
                  (0.14, pose(arm_b=-95, shield=95, front=1, torso=12, lean=5, arm_f=-120, weapon=70)), (0.3, pose(arm_b=-60, shield=60, front=1, torso=2, arm_f=10, weapon=85))]},
        # the finisher: a long lunging thrust
        {"dur": 0.5, "hit": (0.12, 0.2), "shape": {"k": "rect", "x0": 0, "x1": 56, "w": 10}, "mult": 1.4, "poise": 18,
         "step": 24, "next": 0.36,
         "anim": [(0, sw(15, 0, torso=-10, lean=-3)), (0.12, sw(-90, 0, torso=14, lean=7)), (0.24, sw(-90, 0, torso=14, lean=7)), (0.5, sw(-60, 25, torso=4))]},
    ],
    "heavy": {"charge": 0.8, "dur": 0.55, "hit": (0.08, 0.16), "shape": {"k": "arc", "r": 50, "a0": -50, "a1": 50},
              "mult": (2.0, 3.0), "poise": (32, 55), "step": 14,
              "hold": sw(-205, 125, torso=-12, head=-6),
              "anim": [(0, sw(-205, 125, torso=-12)), (0.08, sw(-110, 40, torso=6, lean=3)), (0.16, sw(-35, -35, torso=16, lean=6)), (0.55, sw(-25, -40, torso=8))]},
    "special": {"name": "Shield Bash", "focus": 50, "dur": 0.5, "hit": (0.12, 0.22), "shape": {"k": "circle", "r": 22, "x": 20, "y": 0},
                "mult": 1.15, "poise": 70, "step": 22,
                "anim": [(0, pose(arm_b=-60, shield=60, front=1, torso=-8)), (0.12, pose(arm_b=-95, shield=95, front=1, torso=12, lean=6)), (0.5, pose(arm_b=-60, shield=60, front=1))]},
    # hold to block hits from the front (each blocked hit uses a dash); the first moments are a parry
    "guard": {"kind": "block", "arc": 80, "parry": 0.18, "cost": 1.0, "speed": 0.45,
              "anim": pose(arm_b=-70, shield=70, front=1, torso=-4)},
    "offhand": "shield",
    "moves": {
        # light out of a roll: a low running slash that carries you on
        "dash": {"slot": "light", "dur": 0.32, "hit": (0.04, 0.14), "shape": {"k": "arc", "r": 46, "a0": -80, "a1": 80}, "mult": 1.3, "poise": 14,
                 "step": 30, "next": 0.18,
                 "anim": [(0, sw(-30, -60, torso=20, lean=6, dy=3)), (0.05, sw(-70, 10, torso=22, lean=7, dy=3)), (0.14, sw(-150, 100, torso=10, lean=5, dy=1)), (0.32, sw(-140, 100))]},
        # light just after a block or a parry: an instant thrust
        "riposte": {"slot": "light", "dur": 0.36, "hit": (0.05, 0.13), "shape": {"k": "rect", "x0": 0, "x1": 58, "w": 12}, "mult": 2.2, "poise": 34,
                    "step": 18, "next": 0.22,
                    "anim": [(0, sw(-20, 0, torso=-6, arm_b=-70, shield=70, front=1)), (0.05, sw(-92, 0, torso=16, lean=8, arm_b=-40, shield=50, front=1)),
                             (0.16, sw(-92, 0, torso=16, lean=8, arm_b=-40, shield=50, front=1)), (0.36, sw(-60, 25, torso=4))]},
        # heavy while blocking: a charge behind the shield, blocking from the front as it goes
        "rush": {"slot": "heavy", "dur": 0.5, "hit": (0.06, 0.3), "shape": {"k": "circle", "r": 22, "x": 18, "y": 0}, "mult": 1.8, "poise": 50,
                 "step": 84, "next": 0.4, "guarding": True,
                 "anim": [(0, pose(arm_b=-80, shield=80, front=1, torso=14, lean=5, run=1)), (0.3, pose(arm_b=-95, shield=95, front=1, torso=20, lean=8, run=1)),
                          (0.38, pose(arm_b=-95, shield=95, front=1, torso=10, lean=4)), (0.5, pose(arm_b=-60, shield=60, front=1))]},
    },
}

GREATSWORD = {
    "dodge": {"charges": 2, "recharge": 1.1},
    "id": "greatsword", "name": "Greatsword", "art": "greatsword", "base": 34, "blurb": "Slow and heavy. Breaks poise; heavies shrug off hits. Hold past the chop to whirl.",
    "light": [
        # each swing wider and quicker off the last; hold on past the chop and the blade keeps turning (moves.spin)
        {"dur": 0.64, "hit": (0.2, 0.3), "shape": {"k": "arc", "r": 54, "a0": -65, "a1": 65}, "mult": 1.0, "poise": 22, "step": 10, "next": 0.42,
         "anim": [(0, sw(-215, 150, torso=-12)), (0.2, sw(-150, 90, torso=-4)), (0.3, sw(-30, -35, torso=14, lean=4)), (0.64, sw(-15, -45, torso=8))]},
        {"dur": 0.6, "hit": (0.17, 0.27), "shape": {"k": "arc", "r": 56, "a0": -100, "a1": 100}, "mult": 1.15, "poise": 26, "step": 12, "next": 0.4,
         "anim": [(0, sw(-15, -45, torso=10)), (0.17, sw(-70, 0, torso=6, lean=2)), (0.27, sw(-190, 120, torso=-10, lean=3)), (0.6, sw(-175, 115, torso=-6))]},
        # the finisher: an overhead chop straight down the aim
        {"dur": 0.76, "hit": (0.22, 0.32), "shape": {"k": "rect", "x0": 0, "x1": 64, "w": 14}, "mult": 1.5, "poise": 36, "step": 14, "next": 0.5, "into": "spin",
         "anim": [(0, sw(-175, 115, torso=-8)), (0.22, sw(-200, 100, torso=-14, dy=-2)), (0.32, sw(-55, -30, torso=18, lean=6, dy=2)), (0.76, sw(-40, -30, torso=8))]},
    ],
    "heavy": {"charge": 1.0, "dur": 0.75, "hit": (0.12, 0.22), "shape": {"k": "rect", "x0": 0, "x1": 72, "w": 20}, "hyper": True,
              "mult": (2.2, 3.6), "poise": (45, 80), "step": 16,
              "hold": sw(-200, 100, torso=-14, head=-8),
              "anim": [(0, sw(-200, 100, torso=-14)), (0.12, sw(-95, 5, torso=14, lean=5)), (0.22, sw(-55, -30, torso=20, lean=7, dy=2)), (0.75, sw(-40, -30, torso=10))]},
    "special": {"name": "Leaping Slam", "focus": 50, "dur": 0.9, "hit": (0.55, 0.66), "shape": {"k": "circle", "r": 44, "x": 30, "y": 0},
                "mult": 3.8, "poise": 85, "step": 90, "air": (0.1, 0.5),
                "anim": [(0, sw(-30, 60, dy=4, torso=-10)), (0.3, sw(-200, 100, torso=-16, dy=-10)), (0.56, sw(-55, -30, torso=18, dy=2)),
                         (0.9, sw(-40, -30))]},
    "guard": {"kind": "block", "arc": 60, "parry": 0.12, "cost": 1.0, "chip": 0.3, "speed": 0.35,
              "anim": sw(-100, 100, torso=-6)},
    "moves": {
        # light out of a roll: a rising cut
        "dash": {"slot": "light", "dur": 0.5, "hit": (0.1, 0.2), "shape": {"k": "arc", "r": 54, "a0": -70, "a1": 70}, "mult": 1.5, "poise": 30,
                 "step": 22, "next": 0.34,
                 "anim": [(0, sw(-10, -70, torso=22, lean=5, dy=4)), (0.1, sw(-50, -30, torso=14, lean=6, dy=2)), (0.2, sw(-190, 110, torso=-12, lean=3, dy=-5)), (0.5, sw(-175, 115, torso=-6))]},
        # the whirlwind: the blade turning, a strike all round each turn, for as long as light is held and
        # there are dashes to spend; you can walk as it turns
        "spin": {"slot": "light", "dur": 0.34, "hit": (0.04, 0.3), "shape": {"k": "arc", "r": 56, "a0": -180, "a1": 180}, "mult": 0.8, "poise": 16,
                 "step": 0, "next": 0.34, "loop": True, "drain": 0.8, "walk": 0.55, "whirl": True,
                 "anim": [(0, sw(-95, 0, torso=10, lean=2)), (0.17, sw(-100, 5, torso=12, lean=3, dy=1)), (0.34, sw(-95, 0, torso=10, lean=2))]},
    },
}

DAGGERS = {
    "dodge": {"charges": 4, "recharge": 0.9},
    "id": "daggers", "name": "Twin Daggers", "art": "dagger", "base": 15, "blurb": "Fast and slippery. Dashes instead of a roll; cuts build Bleed and bite deeper from behind.",
    "status": {"light": ("bleed", 4)},   # built on every light hit, before any upgrade
    "light": [
        {"dur": 0.22, "hit": (0.05, 0.11), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.0, "poise": 7, "step": 6, "next": 0.12,
         "anim": [(0, sw(-170, 120)), (0.05, sw(-100, 30, torso=4)), (0.11, sw(-40, -30, torso=8)), (0.22, sw(-40, -20))]},
        {"dur": 0.22, "hit": (0.05, 0.11), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.0, "poise": 7, "step": 6, "next": 0.12,
         "anim": [(0, off(-170, 120)), (0.05, off(-100, 30, torso=4, front=1)), (0.11, off(-40, -30, torso=8, front=1)), (0.22, off(-40, -20, front=1))]},
        {"dur": 0.24, "hit": (0.06, 0.12), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.1, "poise": 8, "step": 6, "next": 0.13,
         "anim": [(0, sw(-20, -40)), (0.06, sw(-90, 20, torso=4)), (0.12, sw(-160, 100, torso=-4)), (0.24, sw(-150, 100))]},
        {"dur": 0.24, "hit": (0.06, 0.12), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.1, "poise": 8, "step": 6, "next": 0.13,
         "anim": [(0, off(-20, -40)), (0.06, off(-90, 20, torso=4, front=1)), (0.12, off(-160, 100, torso=-4, front=1)), (0.24, off(-150, 100, front=1))]},
        # the finisher: a cross-cut that carries you through to its back
        {"dur": 0.4, "hit": (0.06, 0.2), "shape": {"k": "arc", "r": 34, "a0": -110, "a1": 110}, "mult": 1.6, "poise": 16, "step": 62, "next": 0.3, "pass": True,
         "anim": [(0, both(10, 0, torso=-8)), (0.06, pose(arm_f=-150, weapon=_blade(-150, 60), arm_b=-30, shield=_blade(-30, -40), torso=18, lean=7, front=1)),
                  (0.2, pose(arm_f=-30, weapon=_blade(-30, -40), arm_b=-150, shield=_blade(-150, 60), torso=18, lean=7, front=1)), (0.4, both(-60, 20))]},
    ],
    # a backstep cut that throws a fan of knives as it goes: three, five when fully charged (`throw`: shots
    # loosed with the swing, each priced as the move named by `as`)
    "heavy": {"charge": 0.6, "dur": 0.45, "hit": (0.14, 0.22), "shape": {"k": "arc", "r": 44, "a0": -70, "a1": 70},
              "throw": {"v": 460, "r": 4, "life": 0.42, "n": 3, "n_full": 5, "spread": 11, "as": "knife"},
              "mult": (1.6, 2.4), "poise": (20, 34), "step": -30,
              "hold": both(-120, 150, torso=-6, front=1),
              "anim": [(0, both(-120, 150, torso=-8, front=1)), (0.14, both(-70, 10, torso=4, front=1)), (0.22, both(-20, -50, torso=10, front=1)), (0.45, pose())]},
    "special": {"name": "Shadowstep", "focus": 50, "dur": 0.45, "hit": (0.08, 0.16), "shape": {"k": "arc", "r": 44, "a0": -90, "a1": 90}, "blink": 70,
                "mult": 4.9, "poise": 42, "step": 0,
                "anim": [(0, both(-190, 120, torso=-10)), (0.08, both(-100, 20, torso=6, front=1)), (0.16, both(-30, -40, torso=12, front=1)), (0.45, pose())]},
    "guard": {"kind": "dash", "dist": 70, "dur": 0.28, "anim": pose()},
    "offhand": "dagger",
    "backstab": 1.25,   # damage from behind a boss (the browser says which hits were)
    "moves": {
        "knife": {"slot": "light", "mult": 0.4, "poise": 4},   # each knife thrown by the heavy
        # light out of a dash: a crossing cut that goes through it
        "dash": {"slot": "light", "dur": 0.28, "hit": (0.02, 0.16), "shape": {"k": "arc", "r": 34, "a0": -110, "a1": 110}, "mult": 1.4, "poise": 12,
                 "step": 66, "next": 0.18, "pass": True,
                 "anim": [(0, pose(arm_f=-150, weapon=_blade(-150, 60), arm_b=-30, shield=_blade(-30, -40), torso=20, lean=7, front=1)),
                          (0.16, pose(arm_f=-30, weapon=_blade(-30, -40), arm_b=-150, shield=_blade(-150, 60), torso=20, lean=7, front=1)), (0.28, both(-50, 10))]},
    },
}

HALBERD = {
    "dodge": {"charges": 3, "recharge": 1.1},
    "id": "halberd", "name": "Halberd", "art": "halberd", "base": 24, "blurb": "Reach. Jabs that bite hardest at the tip, a vault over danger, a counter stance.",
    "light": [
        {"dur": 0.4, "hit": (0.1, 0.18), "shape": {"k": "rect", "x0": 10, "x1": 74, "w": 9}, "mult": 1.0, "poise": 10, "step": 8, "next": 0.24,
         "anim": [(0, sw(-40, 0, torso=-8, lean=-3)), (0.1, sw(-95, 0, torso=10, lean=6)), (0.2, sw(-95, 0, torso=10, lean=6)), (0.4, sw(-70, 15))]},
        {"dur": 0.4, "hit": (0.1, 0.18), "shape": {"k": "rect", "x0": 10, "x1": 74, "w": 9}, "mult": 1.0, "poise": 10, "step": 8, "next": 0.24,
         "anim": [(0, sw(-55, 10, torso=-6, lean=-2)), (0.1, sw(-100, -6, torso=10, lean=6)), (0.2, sw(-100, -6, torso=10, lean=6)), (0.4, sw(-70, 15))]},
        # two jabs in a breath
        {"dur": 0.52, "hit": (0.08, 0.14), "more": [(0.26, 0.32)], "shape": {"k": "rect", "x0": 10, "x1": 74, "w": 9}, "mult": 0.6, "poise": 7, "step": 6, "next": 0.4,
         "anim": [(0, sw(-40, 0, torso=-8, lean=-3)), (0.08, sw(-95, 0, torso=10, lean=6)), (0.15, sw(-95, 0, torso=10, lean=6)), (0.21, sw(-45, 0, torso=-6, lean=-2)), (0.27, sw(-95, 0, torso=12, lean=7)), (0.34, sw(-95, 0, torso=12, lean=7)), (0.52, sw(-70, 15))]},
        # the finisher: a skewer at full stretch
        {"dur": 0.58, "hit": (0.16, 0.26), "shape": {"k": "rect", "x0": 10, "x1": 92, "w": 10}, "mult": 1.3, "poise": 18, "step": 16, "next": 0.4,
         "anim": [(0, sw(-20, 0, torso=-14, lean=-5)), (0.16, sw(-30, 0, torso=-16, lean=-6)), (0.26, sw(-95, 0, torso=18, lean=9)), (0.36, sw(-95, 0, torso=18, lean=9)), (0.58, sw(-70, 15))]},
    ],
    "heavy": {"charge": 0.8, "dur": 0.7, "hit": (0.14, 0.3), "shape": {"k": "arc", "r": 76, "a0": -135, "a1": 135},
              "mult": (1.8, 2.8), "poise": (30, 50), "step": 4,
              "hold": sw(-190, 160, torso=-14),
              "anim": [(0, sw(-190, 160, torso=-14)), (0.14, sw(-120, 60, torso=0)), (0.3, sw(-30, -40, torso=16, lean=3)), (0.7, sw(-30, -30))]},
    "special": {"name": "Pole Vault", "focus": 50, "dur": 0.8, "hit": (0.55, 0.66), "shape": {"k": "circle", "r": 36, "x": 10, "y": 0},
                "mult": 3.0, "poise": 42, "step": 110, "air": (0.08, 0.52),
                "anim": [(0, sw(-60, -70)), (0.3, sw(-60, -80, torso=-30, dy=-14)), (0.56, sw(-90, -20, torso=10)),
                         (0.8, pose())]},
    "guard": {"kind": "counter", "window": 0.7, "cost": 1.0, "mult": 2.6, "poise": 40, "shape": {"k": "rect", "x0": 0, "x1": 80, "w": 14},
              "anim": sw(-80, 60, torso=-8)},
    "tip": 1.2, "tip_from": 0.6,   # struck with the outer part of the reach: more damage (the browser says which hits were)
    "moves": {
        # light out of a roll: a sliding poke at full reach
        "dash": {"slot": "light", "dur": 0.36, "hit": (0.05, 0.16), "shape": {"k": "rect", "x0": 10, "x1": 88, "w": 9}, "mult": 1.3, "poise": 14,
                 "step": 28, "next": 0.22,
                 "anim": [(0, sw(-60, 0, torso=14, lean=4, dy=3)), (0.05, sw(-95, 0, torso=20, lean=9, dy=3)), (0.18, sw(-95, 0, torso=20, lean=9, dy=2)), (0.36, sw(-70, 15))]},
    },
}

BOW = {
    "dodge": {"charges": 3, "recharge": 0.8},
    "id": "bow", "name": "Longbow", "art": "bow", "base": 15, "blurb": "Range. Shots that quicken; loose a full draw on the flash for a Power Shot; your roll looses a fan.",
    "light": [
        # the draw quickens shot by shot, and the string ends in a fan
        {"dur": 0.36, "hit": (0.12, 0.13), "proj": {"v": 380, "r": 4, "life": 0.9}, "mult": 1.0, "poise": 6, "step": 0, "next": 0.24,
         "anim": [(0, pose(arm_f=-90, arm_b=-90, weapon=90)), (0.12, pose(arm_f=-90, arm_b=-70, weapon=90, torso=-4)), (0.36, pose(arm_f=-90, arm_b=-90))]},
        {"dur": 0.32, "hit": (0.1, 0.11), "proj": {"v": 380, "r": 4, "life": 0.9}, "mult": 1.0, "poise": 6, "step": 0, "next": 0.2,
         "anim": [(0, pose(arm_f=-90, arm_b=-90, weapon=90)), (0.1, pose(arm_f=-90, arm_b=-70, weapon=90, torso=-4)), (0.32, pose(arm_f=-90, arm_b=-90))]},
        {"dur": 0.28, "hit": (0.08, 0.09), "proj": {"v": 380, "r": 4, "life": 0.9}, "mult": 1.0, "poise": 6, "step": 0, "next": 0.17,
         "anim": [(0, pose(arm_f=-90, arm_b=-90, weapon=90)), (0.08, pose(arm_f=-90, arm_b=-70, weapon=90, torso=-4)), (0.28, pose(arm_f=-90, arm_b=-90))]},
        {"dur": 0.26, "hit": (0.07, 0.08), "proj": {"v": 380, "r": 4, "life": 0.9}, "mult": 1.0, "poise": 6, "step": 0, "next": 0.14,
         "anim": [(0, pose(arm_f=-90, arm_b=-90, weapon=90)), (0.07, pose(arm_f=-90, arm_b=-70, weapon=90, torso=-4)), (0.26, pose(arm_f=-90, arm_b=-90))]},
        {"dur": 0.55, "hit": (0.18, 0.19), "proj": {"v": 360, "r": 4, "life": 0.9, "n": 5, "spread": 8}, "mult": 0.5, "poise": 4, "step": -8, "next": 0.36,
         "anim": [(0, pose(arm_f=-90, arm_b=-90, weapon=90)), (0.18, pose(arm_f=-90, arm_b=-55, weapon=90, torso=-8, lean=-3)), (0.55, pose(arm_f=-90, arm_b=-90))]},
    ],
    # let fly in the instant the draw is full (`window` s) and it is a Power Shot: harder, wider, faster
    "heavy": {"charge": 1.0, "dur": 0.35, "hit": (0.05, 0.06), "proj": {"v": 520, "r": 6, "life": 1.0, "pierce": True},
              "power": {"window": 0.24, "mult": 1.3, "proj": {"v": 680, "r": 10, "life": 1.0, "pierce": True, "col": "#fff0c0"}},
              "mult": (2.0, 3.6), "poise": (16, 32), "step": -10,
              "hold": pose(arm_f=-90, arm_b=-50, weapon=90, torso=-6, lean=-2),
              "anim": [(0, pose(arm_f=-90, arm_b=-50, weapon=90)), (0.05, pose(arm_f=-90, arm_b=-100, weapon=90, torso=4)), (0.35, pose(arm_f=-90, arm_b=-90))]},
    "special": {"name": "Arrow Rain", "focus": 50, "dur": 0.6, "hit": (0.3, 0.31), "aoe": {"at": 130, "r": 46, "delay": 0.5, "ticks": 4, "every": 0.3},
                "mult": 1.7, "poise": 11, "step": 0,
                "anim": [(0, pose(arm_f=-140, arm_b=-120, weapon=90)), (0.3, pose(arm_f=-140, arm_b=-90, weapon=90, torso=-6)), (0.6, pose())]},
    "guard": {"kind": "rollshot", "mult": 0.6, "n": 3, "spread": 9, "anim": pose()},
}

CATALYST = {
    "dodge": {"charges": 3, "recharge": 1.2},
    "id": "catalyst", "name": "Catalyst", "art": "staff", "base": 18, "blurb": "Spells. Bolts mark the boss with sigils for the charged orb to spend; a blink that leaves a burst.",
    "light": [
        {"dur": 0.4, "hit": (0.14, 0.15), "proj": {"v": 280, "r": 6, "life": 1.2, "col": "#a0c0ff"}, "mult": 1.0, "poise": 7, "step": 0, "next": 0.24,
         "anim": [(0, sw(-70, 80)), (0.07, sw(-110, 70, torso=-4)), (0.14, sw(-95, 10, torso=8, lean=3)), (0.4, sw(-70, 50))]},
        {"dur": 0.4, "hit": (0.14, 0.15), "proj": {"v": 280, "r": 6, "life": 1.2, "col": "#a0c0ff"}, "mult": 1.0, "poise": 7, "step": 0, "next": 0.24,
         "anim": [(0, sw(-70, 80)), (0.07, sw(-110, 70, torso=-4)), (0.14, sw(-95, 10, torso=8, lean=3)), (0.4, sw(-70, 50))]},
        # the finisher: a sweep of the staff that throws a wide wave through everything near
        {"dur": 0.52, "hit": (0.18, 0.19), "proj": {"v": 300, "r": 15, "life": 0.42, "pierce": True, "col": "#c0d4ff"}, "mult": 1.9, "poise": 16, "step": 0,
         "next": 0.34, "anim": [(0, sw(-200, 140, torso=-12)), (0.1, sw(-150, 80, torso=-4)), (0.18, sw(-40, -30, torso=14, lean=4)), (0.3, sw(-30, -35, torso=12, lean=3)), (0.52, pose())]},
    ],
    "heavy": {"charge": 1.1, "dur": 0.5, "hit": (0.1, 0.11), "proj": {"v": 180, "r": 12, "life": 1.6, "boom": 52, "col": "#c080ff"},
              "mult": (2.2, 3.4), "poise": (24, 44), "step": -8,
              "hold": sw(-175, 90, torso=-10, head=-6),
              "anim": [(0, sw(-175, 90, torso=-10)), (0.1, sw(-90, 0, torso=10, lean=4)), (0.25, sw(-90, 0, torso=8, lean=3)), (0.5, pose())]},
    "special": {"name": "Nova", "focus": 50, "dur": 0.6, "hit": (0.2, 0.3), "shape": {"k": "circle", "r": 62, "x": 0, "y": 0},
                "mult": 3.4, "poise": 48, "step": 0,
                "anim": [(0, sw(-175, 90, arm_b=-170)), (0.2, sw(-70, 90, arm_b=-40, torso=6, dy=2)), (0.35, sw(-70, 90, arm_b=-40, torso=6, dy=2)), (0.6, pose())]},
    # a blink leaves a burst where you stood (`burst`: priced as moves.dash)
    "guard": {"kind": "blink", "dist": 90, "anim": pose(), "burst": {"r": 40, "delay": 0.14, "col": "#c080ff"}},
    # every light that hits marks the boss (up to `max`, lasting `live` s from the last); a heavy or the special spends them
    "sigil": {"max": 4, "per": 0.15, "live": 8.0},
    "moves": {"dash": {"slot": "light", "mult": 1.2, "poise": 12}},
}

WEAPONS = {"sword": SWORD, "greatsword": GREATSWORD, "daggers": DAGGERS, "halberd": HALBERD, "bow": BOW, "catalyst": CATALYST}
