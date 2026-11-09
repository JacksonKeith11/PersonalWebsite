"""Ser Corvin, the Oathless: tier 1. A fallen knight with a greatsword and a tower shield. He teaches
reading wind-ups, rolling through swings and flanking (his guard blocks hits from the front). Phase 2
sets the blade alight: a fourth combo hit and fire waves along the ground.

Times are seconds from the move's start, distances world pixels; see docs/kingfall.md, "Boss moves".
"""

from .moves import DMG, arc, circle, rect, ring, proj, pose

DMG[0] = 0.85  # tier 1: hits a little softer than written

BURN = {"fire": 1}


MOVES = {
    # three-hit combo; each swing re-aims at its target first, so walking away isn't enough
    "combo": {
        "range": (0, 70), "weight": 4, "cd": 1.0, "phase": (1,), "dur": 2.6, "locks": [0.0, 0.8, 1.4],
        "motion": [(0.45, 0.6, 14), (1.0, 1.1, 10), (1.65, 1.8, 22)],
        "hits": [arc(0.5, 0.62, 72, -75, 75, 24), arc(1.05, 1.16, 72, -75, 75, 24),
                 rect(1.72, 1.84, 0, 92, 16, 34)],
        "anim": [(0, pose()), (0.4, pose(arm_f=-150, weapon=60, torso=-10)), (0.55, pose(arm_f=-20, weapon=110, torso=8)),
                 (0.9, pose(arm_f=-130, weapon=120, torso=10)), (1.08, pose(arm_f=-170, weapon=-80, torso=-6)),
                 (1.5, pose(arm_f=-175, weapon=10, torso=-12, head=-6)), (1.75, pose(arm_f=-60, weapon=60, torso=12, lean=4)),
                 (2.6, pose())],
    },
    "combo2": {  # phase 2: the same three, then a burning slam whose ring spreads across the floor
        "range": (0, 70), "weight": 4, "cd": 1.0, "phase": (2,), "dur": 3.4, "locks": [0.0, 0.7, 1.25, 2.0],
        "motion": [(0.4, 0.55, 14), (0.9, 1.0, 10), (1.5, 1.65, 22), (2.3, 2.4, 10)],
        "hits": [arc(0.45, 0.56, 72, -75, 75, 24, BURN), arc(0.95, 1.06, 72, -75, 75, 24, BURN),
                 rect(1.56, 1.68, 0, 92, 16, 32, BURN), circle(2.38, 2.5, 36, 0, 40, 34, BURN, mark=0.4),
                 ring(2.55, 3.1, 36, 170, 12, 22, BURN, at=36)],
        "anim": [(0, pose()), (0.35, pose(arm_f=-150, weapon=60, torso=-10)), (0.5, pose(arm_f=-20, weapon=110, torso=8)),
                 (0.8, pose(arm_f=-130, weapon=120, torso=10)), (0.98, pose(arm_f=-170, weapon=-80, torso=-6)),
                 (1.35, pose(arm_f=-175, weapon=10, torso=-12)), (1.6, pose(arm_f=-60, weapon=60, torso=12, lean=4)),
                 (2.05, pose(arm_f=-180, weapon=0, torso=-14, head=-8, dy=-3)), (2.4, pose(arm_f=-40, weapon=110, torso=16, lean=6, dy=2)),
                 (3.4, pose())],
    },
    # the shield charge: he lowers his head, then runs at you, through you if you don't move
    "charge": {
        "range": (90, 300), "weight": 3, "cd": 4.0, "phase": (1, 2), "dur": 2.2, "locks": [0.0, 0.55],
        "motion": [(0.75, 1.3, ("target", 40, 70, 260))],
        "hits": [circle(0.75, 1.3, 30, 0, 18, 30, {"kb": 90}, mark=0.0)],
        "anim": [(0, pose()), (0.5, pose(arm_b=-70, shield=70, front=1, torso=-12, head=4, lean=-3)),
                 (0.75, pose(arm_b=-75, shield=75, front=1, torso=14, head=6, lean=8, run=1)),
                 (1.3, pose(arm_b=-75, shield=75, front=1, torso=14, lean=8, run=1)), (1.6, pose(arm_b=-40, shield=40, front=1)),
                 (2.2, pose())],
    },
    # the delayed overhead: he raises the sword and holds it, then brings it down hard
    "delayed": {
        "range": (0, 95), "weight": 3, "cd": 3.0, "phase": (1, 2), "dur": 2.5, "locks": [0.0, 1.1],
        "motion": [(1.3, 1.42, 18)],
        "hits": [rect(1.34, 1.46, 0, 100, 18, 44), circle(1.42, 1.54, 30, 0, 96, 16)],
        "anim": [(0, pose()), (0.5, pose(arm_f=-175, weapon=0, torso=-14, head=-8, dy=-2)),
                 (1.25, pose(arm_f=-185, weapon=-10, torso=-18, head=-10, dy=-3)), (1.38, pose(arm_f=-50, weapon=100, torso=18, lean=6, dy=2)),
                 (2.0, pose(arm_f=-50, weapon=100, torso=16, lean=5)), (2.5, pose())],
    },
    # the lunging thrust from mid-range
    "lunge": {
        "range": (60, 190), "weight": 3, "cd": 2.0, "phase": (1, 2), "dur": 1.8, "locks": [0.0, 0.38],
        "motion": [(0.55, 0.78, ("target", 10, 40, 160))],
        "hits": [rect(0.58, 0.8, 0, 66, 13, 30)],
        "anim": [(0, pose()), (0.45, pose(arm_f=-100, weapon=-50, torso=-10, lean=-3)),
                 (0.6, pose(arm_f=-90, weapon=0, torso=14, lean=8)), (1.2, pose(arm_f=-90, weapon=0, torso=10, lean=5)), (1.8, pose())],
    },
    # he turtles behind the shield (hits from the front glance off), then bashes whoever's in front
    "guard": {
        "range": (0, 120), "weight": 2, "cd": 7.0, "phase": (1, 2), "dur": 2.6, "locks": [0.0, 1.7], "guard": (0.25, 1.9),
        "motion": [(1.85, 1.95, 16)],
        "hits": [circle(1.88, 1.98, 30, 0, 26, 22, {"kb": 70})],
        "anim": [(0, pose()), (0.25, pose(arm_b=-70, shield=70, front=1, torso=-6)), (1.75, pose(arm_b=-70, shield=70, front=1, torso=-8)),
                 (1.9, pose(arm_b=-95, shield=95, front=1, torso=12, lean=6)), (2.6, pose())],
    },
    # phase 2: three waves of fire along the floor, fanned at whoever he's facing
    "embers": {
        "range": (100, 400), "weight": 3, "cd": 5.0, "phase": (2,), "dur": 2.0, "locks": [0.0, 0.6],
        "motion": [],
        "hits": [proj(0.85, 0, 30, a, 190, 11, 1.8, 24, BURN) for a in (-24, 0, 24)],
        "anim": [(0, pose()), (0.6, pose(arm_f=-180, weapon=0, torso=-14, dy=-2)), (0.85, pose(arm_f=-30, weapon=120, torso=18, lean=6)),
                 (2.0, pose())],
    },
}

# Between phases he plants the sword, and the blade catches fire; anyone close is thrown back.
PHASE2 = {
    "dur": 2.4, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(1.0, 1.5, 10, 160, 14, 8, {"kb": 120}, at=0)],
    "anim": [(0, pose()), (0.6, pose(arm_f=-90, weapon=180, torso=10, head=10)), (1.0, pose(arm_f=-170, weapon=0, torso=-16, head=-12, dy=-2)),
             (2.4, pose())],
}

BOSS = {
    "id": "corvin", "name": "Ser Corvin, the Oathless", "tier": 1, "rig": "knight", "art": "corvin",
    "hp": 1900, "poise": 120, "radius": 20, "speed": 52,
    "moves": MOVES, "phases": [0.5], "phase_moves": {2: PHASE2},
    "arena": "chapel",
}
