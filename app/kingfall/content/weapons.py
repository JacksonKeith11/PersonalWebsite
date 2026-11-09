"""The heroes' weapons. Each has a light combo, a charged heavy, a special (costs Focus) and its own
defensive move. The browser plays them (timing, animation, hit checks against the boss); the server
works out the damage from these numbers and the hero's build.

Per attack: dur (s), hit (t0, t1) when it can land, shape (as the bosses', in the aim's frame), mult
(of the weapon's base damage), poise, st (stamina), step (px lunge), next (from when the next attack
may be queued), anim keyframes. Ranged attacks fire `proj` (v speed, r radius, life, n, spread
degrees, pierce) instead of using a shape; `aoe` lands a circle `at` px ahead after `delay`, `ticks`
times; `blink` teleports the hero `blink` px along the aim first; `air` makes them untouchable
for that window (a leap); `hyper` keeps them from flinching when hit. A weapon's own `status`
({slot: (kind, amount)}) builds on every hit of that slot, on top of what upgrades add.

The defensive move (`guard.kind`): block (hold: blocks from the front, parry at first), dash (the
roll becomes a short dash with charges), counter (hold: a hit taken in the stance is absorbed and
answered), blink (the roll becomes a teleport), rollshot (the roll fires an arrow).
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
    "id": "sword", "name": "Sword & Shield", "art": "sword", "base": 22, "blurb": "All-rounder. Block, parry and riposte.",
    "light": [
        {"dur": 0.36, "hit": (0.09, 0.17), "shape": {"k": "arc", "r": 42, "a0": -65, "a1": 65}, "mult": 1.0, "poise": 10, "st": 12,
         "step": 8, "next": 0.2,
         "anim": [(0, sw(-205, 140, torso=-8)), (0.09, sw(-120, 60, torso=2, lean=1)), (0.17, sw(-40, -25, torso=10, lean=3)), (0.36, sw(-25, -35, torso=6))]},
        {"dur": 0.36, "hit": (0.09, 0.17), "shape": {"k": "arc", "r": 42, "a0": -65, "a1": 65}, "mult": 1.0, "poise": 10, "st": 12,
         "step": 8, "next": 0.2,
         "anim": [(0, sw(-25, -40, torso=8)), (0.09, sw(-80, 10, torso=4, lean=2)), (0.17, sw(-165, 95, torso=-6, lean=2)), (0.36, sw(-150, 100))]},
        {"dur": 0.5, "hit": (0.14, 0.22), "shape": {"k": "rect", "x0": 0, "x1": 52, "w": 10}, "mult": 1.4, "poise": 18, "st": 16,
         "step": 16, "next": 0.36,
         "anim": [(0, sw(15, 0, torso=-10, lean=-3)), (0.14, sw(-90, 0, torso=12, lean=6)), (0.24, sw(-90, 0, torso=12, lean=6)), (0.5, sw(-60, 25, torso=4))]},
    ],
    "heavy": {"charge": 0.8, "dur": 0.55, "hit": (0.08, 0.16), "shape": {"k": "arc", "r": 50, "a0": -50, "a1": 50},
              "mult": (2.0, 3.0), "poise": (32, 55), "st": 30, "step": 14,
              "hold": sw(-205, 125, torso=-12, head=-6),
              "anim": [(0, sw(-205, 125, torso=-12)), (0.08, sw(-110, 40, torso=6, lean=3)), (0.16, sw(-35, -35, torso=16, lean=6)), (0.55, sw(-25, -40, torso=8))]},
    "special": {"name": "Shield Bash", "focus": 35, "dur": 0.5, "hit": (0.12, 0.22), "shape": {"k": "circle", "r": 22, "x": 20, "y": 0},
                "mult": 0.6, "poise": 50, "step": 22,
                "anim": [(0, pose(arm_b=-60, shield=60, front=1, torso=-8)), (0.12, pose(arm_b=-95, shield=95, front=1, torso=12, lean=6)), (0.5, pose(arm_b=-60, shield=60, front=1))]},
    # hold to block hits from the front (stamina pays for them); the first moments are a parry
    "guard": {"kind": "block", "arc": 80, "parry": 0.18, "st_per_dmg": 1.0, "speed": 0.45,
              "anim": pose(arm_b=-70, shield=70, front=1, torso=-4)},
    "offhand": "shield",
}

GREATSWORD = {
    "id": "greatsword", "name": "Greatsword", "art": "greatsword", "base": 34, "blurb": "Slow and heavy. Breaks poise; heavies shrug off hits.",
    "light": [
        {"dur": 0.62, "hit": (0.2, 0.3), "shape": {"k": "arc", "r": 54, "a0": -80, "a1": 80}, "mult": 1.0, "poise": 22, "st": 18, "step": 10, "next": 0.4,
         "anim": [(0, sw(-215, 150, torso=-12)), (0.2, sw(-150, 90, torso=-4)), (0.3, sw(-30, -35, torso=14, lean=4)), (0.62, sw(-15, -45, torso=8))]},
        {"dur": 0.66, "hit": (0.22, 0.32), "shape": {"k": "arc", "r": 54, "a0": -80, "a1": 80}, "mult": 1.15, "poise": 26, "st": 20, "step": 10, "next": 0.44,
         "anim": [(0, sw(-15, -45, torso=10)), (0.22, sw(-70, 0, torso=6, lean=2)), (0.32, sw(-190, 120, torso=-10, lean=3)), (0.66, sw(-175, 115, torso=-6))]},
    ],
    "heavy": {"charge": 1.0, "dur": 0.75, "hit": (0.12, 0.22), "shape": {"k": "rect", "x0": 0, "x1": 72, "w": 20}, "hyper": True,
              "mult": (2.2, 3.6), "poise": (45, 80), "st": 34, "step": 16,
              "hold": sw(-200, 100, torso=-14, head=-8),
              "anim": [(0, sw(-200, 100, torso=-14)), (0.12, sw(-95, 5, torso=14, lean=5)), (0.22, sw(-55, -30, torso=20, lean=7, dy=2)), (0.75, sw(-40, -30, torso=10))]},
    "special": {"name": "Leaping Slam", "focus": 40, "dur": 0.9, "hit": (0.55, 0.66), "shape": {"k": "circle", "r": 44, "x": 30, "y": 0},
                "mult": 2.0, "poise": 60, "step": 90, "air": (0.1, 0.5),
                "anim": [(0, sw(-30, 60, dy=4, torso=-10)), (0.3, sw(-200, 100, torso=-16, dy=-10)), (0.56, sw(-55, -30, torso=18, dy=2)),
                         (0.9, sw(-40, -30))]},
    "guard": {"kind": "block", "arc": 60, "parry": 0.12, "st_per_dmg": 1.3, "chip": 0.3, "speed": 0.35,
              "anim": sw(-100, 100, torso=-6)},
}

DAGGERS = {
    "id": "daggers", "name": "Twin Daggers", "art": "dagger", "base": 16, "blurb": "Fast and slippery. Three quick dashes instead of a roll; every cut builds Bleed.",
    "status": {"light": ("bleed", 4)},   # built on every light hit, before any upgrade
    "light": [
        {"dur": 0.22, "hit": (0.05, 0.11), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.0, "poise": 7, "st": 7, "step": 6, "next": 0.12,
         "anim": [(0, sw(-170, 120)), (0.05, sw(-100, 30, torso=4)), (0.11, sw(-40, -30, torso=8)), (0.22, sw(-40, -20))]},
        {"dur": 0.22, "hit": (0.05, 0.11), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.0, "poise": 7, "st": 7, "step": 6, "next": 0.12,
         "anim": [(0, off(-170, 120)), (0.05, off(-100, 30, torso=4, front=1)), (0.11, off(-40, -30, torso=8, front=1)), (0.22, off(-40, -20, front=1))]},
        {"dur": 0.24, "hit": (0.06, 0.12), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.1, "poise": 8, "st": 7, "step": 6, "next": 0.13,
         "anim": [(0, sw(-20, -40)), (0.06, sw(-90, 20, torso=4)), (0.12, sw(-160, 100, torso=-4)), (0.24, sw(-150, 100))]},
        {"dur": 0.24, "hit": (0.06, 0.12), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.1, "poise": 8, "st": 7, "step": 6, "next": 0.13,
         "anim": [(0, off(-20, -40)), (0.06, off(-90, 20, torso=4, front=1)), (0.12, off(-160, 100, torso=-4, front=1)), (0.24, off(-150, 100, front=1))]},
        {"dur": 0.4, "hit": (0.1, 0.18), "shape": {"k": "rect", "x0": 0, "x1": 50, "w": 10}, "mult": 1.8, "poise": 16, "st": 10, "step": 18, "next": 0.3,
         "anim": [(0, both(10, 0, torso=-8)), (0.1, both(-90, 0, torso=14, lean=6, front=1)), (0.2, both(-90, 0, torso=14, lean=6, front=1)),
                  (0.4, both(-60, 20))]},
    ],
    "heavy": {"charge": 0.6, "dur": 0.45, "hit": (0.14, 0.22), "shape": {"k": "arc", "r": 44, "a0": -70, "a1": 70},
              "mult": (1.6, 2.4), "poise": (20, 34), "st": 18, "step": -30,
              "hold": both(-120, 150, torso=-6, front=1),
              "anim": [(0, both(-120, 150, torso=-8, front=1)), (0.14, both(-70, 10, torso=4, front=1)), (0.22, both(-20, -50, torso=10, front=1)), (0.45, pose())]},
    "special": {"name": "Shadowstep", "focus": 30, "dur": 0.45, "hit": (0.08, 0.16), "shape": {"k": "arc", "r": 44, "a0": -90, "a1": 90}, "blink": 70,
                "mult": 2.6, "poise": 30, "step": 0,
                "anim": [(0, both(-190, 120, torso=-10)), (0.08, both(-100, 20, torso=6, front=1)), (0.16, both(-30, -40, torso=12, front=1)), (0.45, pose())]},
    "guard": {"kind": "dash", "charges": 3, "recharge": 0.8, "dist": 70, "dur": 0.28, "st": 15, "anim": pose()},
    "offhand": "dagger",
}

HALBERD = {
    "id": "halberd", "name": "Halberd", "art": "halberd", "base": 24, "blurb": "Reach. Sweeps, a vault over danger, a counter stance.",
    "light": [
        {"dur": 0.42, "hit": (0.12, 0.2), "shape": {"k": "rect", "x0": 10, "x1": 74, "w": 9}, "mult": 1.0, "poise": 10, "st": 13, "step": 8, "next": 0.26,
         "anim": [(0, sw(-40, 0, torso=-8, lean=-3)), (0.12, sw(-95, 0, torso=10, lean=6)), (0.22, sw(-95, 0, torso=10, lean=6)), (0.42, sw(-70, 15))]},
        {"dur": 0.42, "hit": (0.12, 0.2), "shape": {"k": "rect", "x0": 10, "x1": 74, "w": 9}, "mult": 1.0, "poise": 10, "st": 13, "step": 8, "next": 0.26,
         "anim": [(0, sw(-40, 0, torso=-8, lean=-3)), (0.12, sw(-95, 0, torso=10, lean=6)), (0.22, sw(-95, 0, torso=10, lean=6)), (0.42, sw(-70, 15))]},
        {"dur": 0.56, "hit": (0.16, 0.26), "shape": {"k": "arc", "r": 70, "a0": -70, "a1": 70}, "mult": 1.3, "poise": 16, "st": 16, "step": 6, "next": 0.36,
         "anim": [(0, sw(-200, 150, torso=-10)), (0.16, sw(-140, 80, torso=-2)), (0.26, sw(-40, -25, torso=10, lean=3)), (0.56, sw(-30, -30))]},
    ],
    "heavy": {"charge": 0.8, "dur": 0.7, "hit": (0.14, 0.3), "shape": {"k": "arc", "r": 76, "a0": -135, "a1": 135},
              "mult": (1.8, 2.8), "poise": (30, 50), "st": 30, "step": 4,
              "hold": sw(-190, 160, torso=-14),
              "anim": [(0, sw(-190, 160, torso=-14)), (0.14, sw(-120, 60, torso=0)), (0.3, sw(-30, -40, torso=16, lean=3)), (0.7, sw(-30, -30))]},
    "special": {"name": "Pole Vault", "focus": 30, "dur": 0.8, "hit": (0.55, 0.66), "shape": {"k": "circle", "r": 36, "x": 10, "y": 0},
                "mult": 1.6, "poise": 30, "step": 110, "air": (0.08, 0.52),
                "anim": [(0, sw(-60, -70)), (0.3, sw(-60, -80, torso=-30, dy=-14)), (0.56, sw(-90, -20, torso=10)),
                         (0.8, pose())]},
    "guard": {"kind": "counter", "window": 0.7, "st": 20, "mult": 2.6, "poise": 40, "shape": {"k": "rect", "x0": 0, "x1": 80, "w": 14},
              "anim": sw(-80, 60, torso=-8)},
}

BOW = {
    "id": "bow", "name": "Longbow", "art": "bow", "base": 15, "blurb": "Range. Charged piercing shots; your roll looses an arrow.",
    "light": [
        {"dur": 0.34, "hit": (0.12, 0.13), "proj": {"v": 380, "r": 4, "life": 0.9}, "mult": 1.0, "poise": 6, "st": 8, "step": 0, "next": 0.2,
         "anim": [(0, pose(arm_f=-90, arm_b=-90, weapon=90)), (0.12, pose(arm_f=-90, arm_b=-70, weapon=90, torso=-4)), (0.34, pose(arm_f=-90, arm_b=-90))]},
        {"dur": 0.34, "hit": (0.12, 0.13), "proj": {"v": 380, "r": 4, "life": 0.9}, "mult": 1.0, "poise": 6, "st": 8, "step": 0, "next": 0.2,
         "anim": [(0, pose(arm_f=-90, arm_b=-90, weapon=90)), (0.12, pose(arm_f=-90, arm_b=-70, weapon=90, torso=-4)), (0.34, pose(arm_f=-90, arm_b=-90))]},
        {"dur": 0.5, "hit": (0.18, 0.19), "proj": {"v": 360, "r": 4, "life": 0.9, "n": 3, "spread": 10}, "mult": 0.8, "poise": 5, "st": 12, "step": -6, "next": 0.3,
         "anim": [(0, pose(arm_f=-90, arm_b=-90, weapon=90)), (0.18, pose(arm_f=-90, arm_b=-60, weapon=90, torso=-6, lean=-2)), (0.5, pose(arm_f=-90, arm_b=-90))]},
    ],
    "heavy": {"charge": 1.0, "dur": 0.35, "hit": (0.05, 0.06), "proj": {"v": 520, "r": 6, "life": 1.0, "pierce": True},
              "mult": (2.0, 3.6), "poise": (16, 32), "st": 24, "step": -10,
              "hold": pose(arm_f=-90, arm_b=-50, weapon=90, torso=-6, lean=-2),
              "anim": [(0, pose(arm_f=-90, arm_b=-50, weapon=90)), (0.05, pose(arm_f=-90, arm_b=-100, weapon=90, torso=4)), (0.35, pose(arm_f=-90, arm_b=-90))]},
    "special": {"name": "Arrow Rain", "focus": 40, "dur": 0.6, "hit": (0.3, 0.31), "aoe": {"at": 130, "r": 46, "delay": 0.5, "ticks": 4, "every": 0.3},
                "mult": 0.9, "poise": 8, "step": 0,
                "anim": [(0, pose(arm_f=-140, arm_b=-120, weapon=90)), (0.3, pose(arm_f=-140, arm_b=-90, weapon=90, torso=-6)), (0.6, pose())]},
    "guard": {"kind": "rollshot", "mult": 0.8, "anim": pose()},
}

CATALYST = {
    "id": "catalyst", "name": "Catalyst", "art": "staff", "base": 18, "blurb": "Spells. Bolts and a charged orb; a blink instead of a roll.",
    "light": [
        {"dur": 0.4, "hit": (0.14, 0.15), "proj": {"v": 280, "r": 6, "life": 1.2, "col": "#a0c0ff"}, "mult": 1.0, "poise": 7, "st": 10, "step": 0, "next": 0.24,
         "anim": [(0, sw(-70, 80)), (0.07, sw(-110, 70, torso=-4)), (0.14, sw(-95, 10, torso=8, lean=3)), (0.4, sw(-70, 50))]},
        {"dur": 0.4, "hit": (0.14, 0.15), "proj": {"v": 280, "r": 6, "life": 1.2, "col": "#a0c0ff"}, "mult": 1.0, "poise": 7, "st": 10, "step": 0, "next": 0.24,
         "anim": [(0, sw(-70, 80)), (0.07, sw(-110, 70, torso=-4)), (0.14, sw(-95, 10, torso=8, lean=3)), (0.4, sw(-70, 50))]},
        {"dur": 0.55, "hit": (0.2, 0.21), "proj": {"v": 240, "r": 7, "life": 1.3, "n": 3, "spread": 18, "col": "#a0c0ff"}, "mult": 0.8, "poise": 6, "st": 14, "step": 0,
         "next": 0.34, "anim": [(0, sw(-170, 110, torso=-6)), (0.2, sw(-90, 0, torso=10, lean=4)), (0.3, sw(-90, 0, torso=10, lean=4)), (0.55, pose())]},
    ],
    "heavy": {"charge": 1.1, "dur": 0.5, "hit": (0.1, 0.11), "proj": {"v": 180, "r": 12, "life": 1.6, "boom": 52, "col": "#c080ff"},
              "mult": (2.2, 3.4), "poise": (24, 44), "st": 26, "step": -8,
              "hold": sw(-175, 90, torso=-10, head=-6),
              "anim": [(0, sw(-175, 90, torso=-10)), (0.1, sw(-90, 0, torso=10, lean=4)), (0.25, sw(-90, 0, torso=8, lean=3)), (0.5, pose())]},
    "special": {"name": "Nova", "focus": 35, "dur": 0.6, "hit": (0.2, 0.3), "shape": {"k": "circle", "r": 62, "x": 0, "y": 0},
                "mult": 1.8, "poise": 34, "step": 0,
                "anim": [(0, sw(-175, 90, arm_b=-170)), (0.2, sw(-70, 90, arm_b=-40, torso=6, dy=2)), (0.35, sw(-70, 90, arm_b=-40, torso=6, dy=2)), (0.6, pose())]},
    "guard": {"kind": "blink", "dist": 90, "st": 22, "anim": pose()},
}

WEAPONS = {"sword": SWORD, "greatsword": GREATSWORD, "daggers": DAGGERS, "halberd": HALBERD, "bow": BOW, "catalyst": CATALYST}
