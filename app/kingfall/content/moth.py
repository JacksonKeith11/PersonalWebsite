"""The Moth Saint: tier 3. A veiled saint hovering on moth wings in a candlelit sanctum. She keeps her
distance and fills the air: spirals of glowing dust, pillars of light that fall where you stand, gusts
from her wings, and a brood of mothlings. Phase 2: she snuffs the candles; the sanctum goes dark and
her spirals double.
"""

from .moves import DMG, arc, circle, rect, ring, proj, spawn, pose

DMG[0] = 1.15
DUST = {"col": "#f0e0a0"}
LIGHT = {"col": "#fff0b0", "unblock": True}

FLAP = [(0, pose()), (0.3, pose(wing_b=80, wing_f=60)), (0.6, pose(wing_b=40, wing_f=24)), (0.9, pose(wing_b=80, wing_f=60)), (1.2, pose())]

MOVES = {
    # a spiral of dust thrown out round her
    "spiral": {
        "range": (0, 500), "weight": 4, "cd": 3.0, "phase": (1, 2), "dur": 2.6, "locks": [0.0],
        "motion": [],
        "hits": [proj(0.6 + i * 0.07, 0, 0, i * 37 % 360 - 180, 120, 6, 2.6, 12, DUST) for i in range(18)],
        "anim": [(0, pose()), (0.6, pose(arm_f=-160, arm_b=-160, wing_b=90, wing_f=70)), (1.9, pose(arm_f=-160, arm_b=-160, wing_b=30, wing_f=10)), (2.6, pose())],
    },
    # pillars of light fall where you stand and around you
    "pillars": {
        "range": (0, 500), "weight": 4, "cd": 3.5, "phase": (1, 2), "dur": 2.2, "locks": [0.0, 0.4], "reach": ("target", 0, 0, 400),
        "motion": [],
        "hits": [circle(1.2, 1.35, 30, 0, 0, 30, LIGHT, mark=0.8, tx=True)]
        + [circle(1.5, 1.65, 26, s, f, 26, LIGHT, mark=0.8, tx=True) for s, f in ((-70, 0), (70, 0), (0, -70), (0, 70))],
        "anim": [(0, pose()), (0.4, pose(arm_f=-170, head=-14)), (1.2, pose(arm_f=-170, head=-14)), (2.2, pose())],
    },
    # a gust from her wings throws you back
    "gust": {
        "range": (0, 140), "weight": 3, "cd": 2.5, "phase": (1, 2), "dur": 1.6, "locks": [0.0, 0.5],
        "motion": [(0.7, 0.9, -30)],
        "hits": [arc(0.7, 0.86, 120, -60, 60, 16, {**DUST, "kb": 160})],
        "anim": [(0, pose()), (0.5, pose(wing_b=100, wing_f=90)), (0.75, pose(wing_b=0, wing_f=-10)), (1.6, pose())],
    },
    # a stream of dust aimed at you, chasing as she turns
    "stream": {
        "range": (80, 400), "weight": 3, "cd": 3.0, "phase": (1, 2), "dur": 2.0, "locks": [0.0, 0.5, 0.9, 1.3],
        "motion": [],
        "hits": [proj(0.6 + i * 0.12, 0, 10, 0, 210, 7, 1.8, 12, DUST) for i in range(10)],
        "anim": [(0, pose()), (0.5, pose(arm_f=-90)), (1.9, pose(arm_f=-90)), (2.0, pose())],
    },
    # a brood of mothlings
    "brood": {
        "range": (0, 500), "weight": 2, "cd": 14.0, "phase": (1, 2), "dur": 1.4, "locks": [0.0], "adds": "mothling", "max_adds": 5,
        "motion": [],
        "hits": [spawn(0.8, "mothling", 3, 40, 120)],
        "anim": FLAP,
    },
    # phase 2: a double spiral, turning both ways
    "spiral2": {
        "range": (0, 500), "weight": 4, "cd": 4.0, "phase": (2,), "dur": 3.0, "locks": [0.0],
        "motion": [],
        "hits": [proj(0.6 + i * 0.07, 0, 0, i * 37 % 360 - 180, 120, 6, 2.6, 12, DUST) for i in range(18)]
        + [proj(0.6 + i * 0.07, 0, 0, 180 - i * 37 % 360, 100, 6, 2.6, 12, DUST) for i in range(18)],
        "anim": [(0, pose()), (0.6, pose(arm_f=-160, arm_b=-160, wing_b=90, wing_f=70)), (2.4, pose(arm_f=-160, arm_b=-160)), (3.0, pose())],
    },
}

PHASE2 = {  # she snuffs the candles
    "dur": 2.4, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(0.9, 1.6, 20, 180, 14, 10, {**DUST, "kb": 110}), spawn(1.2, "mothling", 3, 60, 160)],
    "anim": [(0, pose()), (0.7, pose(wing_b=100, wing_f=90, arm_f=-170, arm_b=-170)), (1.6, pose(wing_b=10, wing_f=0)), (2.4, pose())],
}

BOSS = {
    "id": "moth", "name": "The Moth Saint", "tier": 3, "rig": "moth", "art": "moth", "arena": "sanctum",
    "hp": 2500, "poise": 120, "radius": 20, "speed": 55, "keep": 150, "hover": 16,
    "moves": MOVES, "phases": [0.5], "phase_moves": {2: PHASE2}, "dark": 2,
    "adds": {"mothling": {"hp": 30, "speed": 66, "radius": 8, "dmg": 8, "art": "moth.mothling", "life": 20, "float": 14}},
    "stagger_pose": {"torso": 16, "head": 14, "wing_b": 10, "wing_f": 0, "z": -12}, "dead_pose": {"torso": 30, "head": 20, "wing_b": 0, "wing_f": -10, "z": -16},
}
