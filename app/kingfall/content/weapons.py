"""The heroes' weapons. Each has a light combo, a charged heavy, a special (costs Focus) and its own
defensive move. The browser plays them (timing, animation, hit checks against the boss); the server
works out the damage from these numbers and the hero's build.

Per attack: dur (s), hit (t0, t1) when it can land, shape (as the bosses', in the aim's frame), mult
(of the weapon's base damage), poise, st (stamina), step (px lunge), next (from when the next attack
may be queued), anim keyframes. Ranged attacks fire `proj` (v speed, r radius, life, n, spread
degrees, pierce) instead of using a shape; `aoe` lands a circle `at` px ahead after `delay`, `ticks`
times; `blink` teleports the hero `blink` px along the aim first; `air` makes them untouchable
for that window (a leap); `hyper` keeps them from flinching when hit.

The defensive move (`guard.kind`): block (hold: blocks from the front, parry at first), dash (the
roll becomes a short dash with charges), counter (hold: a hit taken in the stance is absorbed and
answered), blink (the roll becomes a teleport), rollshot (the roll fires an arrow).
"""

from .moves import pose

SWORD = {
    "id": "sword", "name": "Sword & Shield", "art": "sword", "base": 22, "blurb": "All-rounder. Block, parry and riposte.",
    "light": [
        {"dur": 0.36, "hit": (0.09, 0.17), "shape": {"k": "arc", "r": 42, "a0": -65, "a1": 65}, "mult": 1.0, "poise": 10, "st": 12,
         "step": 8, "next": 0.2,
         "anim": [(0, pose(arm_f=-150, weapon=40, torso=-6)), (0.1, pose(arm_f=-30, weapon=100, torso=8, lean=2)), (0.36, pose(arm_f=-20, weapon=70))]},
        {"dur": 0.36, "hit": (0.09, 0.17), "shape": {"k": "arc", "r": 42, "a0": -65, "a1": 65}, "mult": 1.0, "poise": 10, "st": 12,
         "step": 8, "next": 0.2,
         "anim": [(0, pose(arm_f=-20, weapon=100, torso=8)), (0.1, pose(arm_f=-140, weapon=-60, torso=-6, lean=2)), (0.36, pose(arm_f=-120, weapon=-40))]},
        {"dur": 0.5, "hit": (0.14, 0.22), "shape": {"k": "rect", "x0": 0, "x1": 52, "w": 10}, "mult": 1.4, "poise": 18, "st": 16,
         "step": 16, "next": 0.36,
         "anim": [(0, pose(arm_f=-100, weapon=-80, torso=-10, lean=-2)), (0.14, pose(arm_f=-90, weapon=0, torso=12, lean=5)), (0.5, pose(arm_f=-80, weapon=10))]},
    ],
    "heavy": {"charge": 0.8, "dur": 0.55, "hit": (0.08, 0.16), "shape": {"k": "arc", "r": 50, "a0": -50, "a1": 50},
              "mult": (2.0, 3.0), "poise": (32, 55), "st": 30, "step": 14,
              "hold": pose(arm_f=-175, weapon=-10, torso=-12, head=-6),
              "anim": [(0, pose(arm_f=-175, weapon=-10, torso=-12)), (0.08, pose(arm_f=-40, weapon=110, torso=14, lean=5)), (0.55, pose(arm_f=-30, weapon=90))]},
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
         "anim": [(0, pose(arm_f=-160, weapon=20, torso=-10)), (0.22, pose(arm_f=-20, weapon=110, torso=12, lean=3)), (0.62, pose(arm_f=-10, weapon=100))]},
        {"dur": 0.66, "hit": (0.22, 0.32), "shape": {"k": "arc", "r": 54, "a0": -80, "a1": 80}, "mult": 1.15, "poise": 26, "st": 20, "step": 10, "next": 0.44,
         "anim": [(0, pose(arm_f=-10, weapon=110, torso=10)), (0.24, pose(arm_f=-150, weapon=-60, torso=-10, lean=3)), (0.66, pose(arm_f=-140, weapon=-50))]},
    ],
    "heavy": {"charge": 1.0, "dur": 0.75, "hit": (0.12, 0.22), "shape": {"k": "rect", "x0": 0, "x1": 72, "w": 20}, "hyper": True,
              "mult": (2.2, 3.6), "poise": (45, 80), "st": 34, "step": 16,
              "hold": pose(arm_f=-185, weapon=-15, torso=-14, head=-8),
              "anim": [(0, pose(arm_f=-185, weapon=-15, torso=-14)), (0.12, pose(arm_f=-40, weapon=110, torso=18, lean=6, dy=2)), (0.75, pose(arm_f=-30, weapon=100))]},
    "special": {"name": "Leaping Slam", "focus": 40, "dur": 0.9, "hit": (0.55, 0.66), "shape": {"k": "circle", "r": 44, "x": 30, "y": 0},
                "mult": 2.0, "poise": 60, "step": 90, "air": (0.1, 0.5),
                "anim": [(0, pose(dy=4, torso=-10)), (0.3, pose(arm_f=-185, weapon=-10, torso=-16, dy=-10)), (0.56, pose(arm_f=-40, weapon=110, torso=18, dy=2)),
                         (0.9, pose(arm_f=-30, weapon=100))]},
    "guard": {"kind": "block", "arc": 60, "parry": 0.12, "st_per_dmg": 1.3, "chip": 0.3, "speed": 0.35,
              "anim": pose(arm_f=-60, weapon=-80, torso=-6)},
}

DAGGERS = {
    "id": "daggers", "name": "Twin Daggers", "art": "dagger", "base": 13, "blurb": "Fast and slippery. A dash instead of a roll; build bleed.",
    "light": [
        {"dur": 0.22, "hit": (0.05, 0.11), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.0, "poise": 5, "st": 7, "step": 6, "next": 0.12,
         "anim": [(0, pose(arm_f=-120, weapon=60)), (0.06, pose(arm_f=-20, weapon=90, torso=6)), (0.22, pose(arm_f=-30, weapon=80))]},
        {"dur": 0.22, "hit": (0.05, 0.11), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.0, "poise": 5, "st": 7, "step": 6, "next": 0.12,
         "anim": [(0, pose(arm_b=-120, shield=60)), (0.06, pose(arm_b=-20, shield=90, torso=6, front=1)), (0.22, pose(arm_b=-30, shield=80, front=1))]},
        {"dur": 0.24, "hit": (0.06, 0.12), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.1, "poise": 6, "st": 7, "step": 6, "next": 0.13,
         "anim": [(0, pose(arm_f=-150, weapon=20)), (0.06, pose(arm_f=-40, weapon=110, torso=8)), (0.24, pose(arm_f=-40, weapon=100))]},
        {"dur": 0.24, "hit": (0.06, 0.12), "shape": {"k": "arc", "r": 36, "a0": -55, "a1": 55}, "mult": 1.1, "poise": 6, "st": 7, "step": 6, "next": 0.13,
         "anim": [(0, pose(arm_b=-150, shield=20)), (0.06, pose(arm_b=-40, shield=110, torso=8, front=1)), (0.24, pose(arm_b=-40, shield=100, front=1))]},
        {"dur": 0.4, "hit": (0.1, 0.18), "shape": {"k": "rect", "x0": 0, "x1": 50, "w": 10}, "mult": 1.8, "poise": 12, "st": 10, "step": 18, "next": 0.3,
         "anim": [(0, pose(arm_f=-100, arm_b=-100, weapon=-60, shield=-60, torso=-8)), (0.1, pose(arm_f=-90, arm_b=-90, weapon=0, shield=0, torso=14, lean=6, front=1)),
                  (0.4, pose(arm_f=-80, arm_b=-80))]},
    ],
    "heavy": {"charge": 0.6, "dur": 0.45, "hit": (0.14, 0.22), "shape": {"k": "arc", "r": 44, "a0": -70, "a1": 70},
              "mult": (1.6, 2.4), "poise": (14, 24), "st": 18, "step": -30,
              "hold": pose(arm_f=-60, arm_b=-60, weapon=-90, shield=-90, torso=-6, front=1),
              "anim": [(0, pose(arm_f=-60, arm_b=-60, torso=-8)), (0.14, pose(arm_f=30, arm_b=30, weapon=80, shield=80, torso=10, front=1)), (0.45, pose())]},
    "special": {"name": "Shadowstep", "focus": 30, "dur": 0.45, "hit": (0.08, 0.16), "shape": {"k": "arc", "r": 44, "a0": -90, "a1": 90}, "blink": 70,
                "mult": 2.2, "poise": 20, "step": 0,
                "anim": [(0, pose(arm_f=-150, arm_b=-150, torso=-10)), (0.08, pose(arm_f=-20, arm_b=-20, weapon=100, shield=100, torso=12, front=1)), (0.45, pose())]},
    "guard": {"kind": "dash", "charges": 2, "recharge": 1.2, "dist": 70, "dur": 0.24, "st": 15, "anim": pose()},
    "offhand": "dagger",
}

HALBERD = {
    "id": "halberd", "name": "Halberd", "art": "halberd", "base": 24, "blurb": "Reach. Sweeps, a vault over danger, a counter stance.",
    "light": [
        {"dur": 0.42, "hit": (0.12, 0.2), "shape": {"k": "rect", "x0": 10, "x1": 74, "w": 9}, "mult": 1.0, "poise": 10, "st": 13, "step": 8, "next": 0.26,
         "anim": [(0, pose(arm_f=-80, weapon=-90, torso=-8, lean=-2)), (0.12, pose(arm_f=-95, weapon=-90, torso=10, lean=5)), (0.42, pose(arm_f=-80, weapon=-80))]},
        {"dur": 0.42, "hit": (0.12, 0.2), "shape": {"k": "rect", "x0": 10, "x1": 74, "w": 9}, "mult": 1.0, "poise": 10, "st": 13, "step": 8, "next": 0.26,
         "anim": [(0, pose(arm_f=-80, weapon=-90, torso=-8, lean=-2)), (0.12, pose(arm_f=-95, weapon=-90, torso=10, lean=5)), (0.42, pose(arm_f=-80, weapon=-80))]},
        {"dur": 0.56, "hit": (0.16, 0.26), "shape": {"k": "arc", "r": 70, "a0": -70, "a1": 70}, "mult": 1.3, "poise": 16, "st": 16, "step": 6, "next": 0.36,
         "anim": [(0, pose(arm_f=-160, weapon=-40, torso=-10)), (0.18, pose(arm_f=-20, weapon=60, torso=10)), (0.56, pose(arm_f=-20, weapon=50))]},
    ],
    "heavy": {"charge": 0.8, "dur": 0.7, "hit": (0.14, 0.3), "shape": {"k": "arc", "r": 76, "a0": -135, "a1": 135},
              "mult": (1.8, 2.8), "poise": (30, 50), "st": 30, "step": 4,
              "hold": pose(arm_f=-150, weapon=-120, torso=-14),
              "anim": [(0, pose(arm_f=-150, weapon=-120, torso=-14)), (0.3, pose(arm_f=-10, weapon=90, torso=16)), (0.7, pose(arm_f=-20, weapon=80))]},
    "special": {"name": "Pole Vault", "focus": 30, "dur": 0.8, "hit": (0.55, 0.66), "shape": {"k": "circle", "r": 36, "x": 10, "y": 0},
                "mult": 1.6, "poise": 30, "step": 110, "air": (0.08, 0.52),
                "anim": [(0, pose(arm_f=-60, weapon=-170)), (0.3, pose(arm_f=-60, weapon=-170, torso=-30, dy=-14)), (0.56, pose(arm_f=-100, weapon=-90, torso=10)),
                         (0.8, pose())]},
    "guard": {"kind": "counter", "window": 0.7, "st": 20, "mult": 2.6, "poise": 40, "shape": {"k": "rect", "x0": 0, "x1": 80, "w": 14},
              "anim": pose(arm_f=-70, weapon=-140, torso=-8)},
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
                "anim": [(0, pose(arm_f=-160, arm_b=-140, weapon=-70)), (0.3, pose(arm_f=-170, arm_b=-120, weapon=-80)), (0.6, pose())]},
    "guard": {"kind": "rollshot", "mult": 0.8, "anim": pose()},
}

CATALYST = {
    "id": "catalyst", "name": "Catalyst", "art": "staff", "base": 17, "blurb": "Spells. Bolts and a charged orb; a blink instead of a roll.",
    "light": [
        {"dur": 0.4, "hit": (0.14, 0.15), "proj": {"v": 280, "r": 6, "life": 1.2, "col": "#a0c0ff"}, "mult": 1.0, "poise": 7, "st": 10, "step": 0, "next": 0.24,
         "anim": [(0, pose(arm_f=-60, weapon=-40)), (0.14, pose(arm_f=-100, weapon=-80, torso=6)), (0.4, pose(arm_f=-70, weapon=-50))]},
        {"dur": 0.4, "hit": (0.14, 0.15), "proj": {"v": 280, "r": 6, "life": 1.2, "col": "#a0c0ff"}, "mult": 1.0, "poise": 7, "st": 10, "step": 0, "next": 0.24,
         "anim": [(0, pose(arm_f=-60, weapon=-40)), (0.14, pose(arm_f=-100, weapon=-80, torso=6)), (0.4, pose(arm_f=-70, weapon=-50))]},
        {"dur": 0.55, "hit": (0.2, 0.21), "proj": {"v": 240, "r": 7, "life": 1.3, "n": 3, "spread": 18, "col": "#a0c0ff"}, "mult": 0.8, "poise": 6, "st": 14, "step": 0,
         "next": 0.34, "anim": [(0, pose(arm_f=-150, weapon=-20)), (0.2, pose(arm_f=-90, weapon=-90, torso=8)), (0.55, pose())]},
    ],
    "heavy": {"charge": 1.1, "dur": 0.5, "hit": (0.1, 0.11), "proj": {"v": 180, "r": 12, "life": 1.6, "boom": 52, "col": "#c080ff"},
              "mult": (2.2, 3.4), "poise": (24, 44), "st": 26, "step": -8,
              "hold": pose(arm_f=-170, weapon=0, torso=-10, head=-6),
              "anim": [(0, pose(arm_f=-170, weapon=0)), (0.1, pose(arm_f=-80, weapon=-80, torso=8)), (0.5, pose())]},
    "special": {"name": "Nova", "focus": 35, "dur": 0.6, "hit": (0.2, 0.3), "shape": {"k": "circle", "r": 62, "x": 0, "y": 0},
                "mult": 1.8, "poise": 34, "step": 0,
                "anim": [(0, pose(arm_f=-170, arm_b=-170, weapon=0)), (0.2, pose(arm_f=-60, arm_b=-60, weapon=-90, dy=2)), (0.6, pose())]},
    "guard": {"kind": "blink", "dist": 90, "st": 22, "anim": pose()},
}

WEAPONS = {"sword": SWORD, "greatsword": GREATSWORD, "daggers": DAGGERS, "halberd": HALBERD, "bow": BOW, "catalyst": CATALYST}
