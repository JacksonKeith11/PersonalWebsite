"""The Bellwarden: tier 1. A belfry ghoul with a cracked bell on its back. It teaches reading rings:
every toll sends out waves of sound with gaps to roll through. It claws at whoever's close, slams the
bell down, and calls a choir of ghosts. Phase 2: tolls come in threes and it drags the bell round in
a sweeping arc.
"""

from .moves import DMG, arc, circle, rect, ring, zone, spawn, pose

DMG[0] = 0.75
SOUND = {"col": "#c8a8ff", "unblock": True}  # sound passes through shields
SIDES = [(55, 95), (-95, -55)]
BACK = [(150, 180), (-180, -150)]

MOVES = {
    # the toll: it heaves the bell over and strikes it; a ring of sound spreads with gaps at its sides
    "toll": {
        "range": (0, 300), "weight": 4, "cd": 3.5, "phase": (1,), "dur": 2.4, "locks": [0.0],
        "motion": [],
        "hits": [circle(0.95, 1.05, 34, 0, 26, 24, mark=0.45), ring(1.0, 2.2, 30, 150, 12, 15, SOUND, at=26, gaps=SIDES)],
        "anim": [(0, pose()), (0.6, pose(bell=-120, front=1, torso=0, head=-10, arm_f=-150, arm_b=-150)),
                 (0.95, pose(bell=-200, front=1, torso=40, head=-30, arm_f=-40, arm_b=-40, dy=2)), (1.6, pose(bell=-190, front=1, torso=36)),
                 (2.4, pose())],
    },
    # phase 2: three tolls, each ring gapped differently
    "toll3": {
        "range": (0, 320), "weight": 4, "cd": 5.0, "phase": (2,), "dur": 3.3, "locks": [0.0, 1.0, 1.8],
        "motion": [],
        "hits": [ring(0.9, 2.0, 30, 150, 12, 11, SOUND, at=26, gaps=SIDES), ring(1.6, 2.7, 30, 150, 12, 11, SOUND, at=26, gaps=BACK),
                 ring(2.3, 3.3, 30, 160, 12, 12, SOUND, at=26, gaps=SIDES), circle(0.85, 0.95, 34, 0, 26, 22, mark=0.4)],
        "anim": [(0, pose()), (0.5, pose(bell=-120, front=1, torso=0, arm_f=-150, arm_b=-150)), (0.85, pose(bell=-200, front=1, torso=40, arm_f=-40)),
                 (1.25, pose(bell=-140, front=1, torso=10, arm_f=-140)), (1.55, pose(bell=-200, front=1, torso=40, arm_f=-40)),
                 (1.95, pose(bell=-140, front=1, torso=10, arm_f=-140)), (2.25, pose(bell=-200, front=1, torso=40, arm_f=-40)), (3.3, pose())],
    },
    # long arms raking whoever's close
    "rake": {
        "range": (0, 70), "weight": 4, "cd": 1.2, "phase": (1, 2), "dur": 1.5, "locks": [0.0, 0.62],
        "motion": [(0.42, 0.5, 12), (0.82, 0.9, 12)],
        "hits": [arc(0.45, 0.56, 66, -85, 85, 22), arc(0.86, 0.96, 66, -85, 85, 22)],
        "anim": [(0, pose()), (0.35, pose(arm_f=-160, torso=14)), (0.5, pose(arm_f=30, torso=36)), (0.75, pose(arm_b=-150, arm_f=10)),
                 (0.9, pose(arm_b=40, torso=38)), (1.5, pose())],
    },
    # the bell-slam: a long heave, then the bell comes down in front of it like a hammer
    "slam": {
        "range": (0, 110), "weight": 3, "cd": 3.0, "phase": (1, 2), "dur": 2.4, "locks": [0.0, 0.95],
        "motion": [(1.15, 1.25, 14)],
        "hits": [rect(1.2, 1.3, 0, 92, 24, 40), ring(1.25, 1.8, 20, 120, 10, 8, SOUND, at=70)],
        "anim": [(0, pose()), (0.7, pose(bell=-150, front=1, torso=-10, head=-6, arm_f=-170, arm_b=-170, dy=-3)),
                 (1.15, pose(bell=-160, front=1, torso=-14, arm_f=-175, arm_b=-175, dy=-4)),
                 (1.25, pose(bell=-215, front=1, torso=50, head=-36, arm_f=-30, arm_b=-30, dy=3)), (1.9, pose(bell=-210, front=1, torso=46)),
                 (2.4, pose())],
    },
    # it lurches at you, arms wide
    "lurch": {
        "range": (60, 200), "weight": 3, "cd": 2.0, "phase": (1, 2), "dur": 1.7, "locks": [0.0, 0.4],
        "motion": [(0.5, 0.78, ("target", 10, 40, 170))],
        "hits": [rect(0.55, 0.82, 0, 54, 18, 26)],
        "anim": [(0, pose()), (0.42, pose(torso=10, arm_f=-110, arm_b=-110)), (0.6, pose(torso=46, arm_f=-80, arm_b=-80, lean=6, run=1)),
                 (0.85, pose(torso=40, arm_f=-20, arm_b=-20)), (1.7, pose())],
    },
    # it rings the bell softly and the dead come to sing
    "choir": {
        "range": (0, 500), "weight": 2, "cd": 14.0, "phase": (1, 2), "dur": 1.8, "locks": [0.0], "adds": "ghost", "max_adds": 4,
        "motion": [],
        "hits": [spawn(1.0, "ghost", 2, 60, 120)],
        "anim": [(0, pose()), (0.6, pose(bell=-100, front=1, arm_f=-130, torso=10)), (1.0, pose(bell=-130, front=1, arm_f=-100)), (1.8, pose())],
    },
    # phase 2: it drags the bell round itself in a wide grinding arc
    "drag": {
        "range": (0, 120), "weight": 3, "cd": 4.0, "phase": (2,), "dur": 2.2, "locks": [0.0],
        "motion": [],
        "hits": [arc(0.8, 0.95, 84, -90, -30, 24), arc(0.95, 1.1, 84, -30, 30, 24), arc(1.1, 1.25, 84, 30, 90, 24),
                 arc(1.25, 1.4, 84, 90, 150, 24), zone(1.3, 3.0, 26, 0, 60, 4, "void")],
        "anim": [(0, pose()), (0.6, pose(bell=-120, front=1, arm_f=-120, arm_b=-120, torso=10)),
                 (0.8, pose(bell=-200, front=1, torso=50, arm_f=-40, arm_b=-40)), (1.4, pose(bell=-200, front=1, torso=40, lean=-6)), (2.2, pose())],
    },
}

# ghost bells fall on whoever it looks at, three in a row, each one re-aimed (marked, so step aside)
MOVES["knell"] = {
    "range": (80, 460), "weight": 3, "cd": 6.0, "phase": (1, 2), "dur": 2.8, "locks": [0.0, 0.5, 1.0, 1.5], "reach": ("target", 0, 0, 380),
    "motion": [],
    "hits": [circle(1.1 + i * 0.5, 1.22 + i * 0.5, 34, 0, 0, 24, {"col": "#c8a8ff"}, mark=0.6, tx=True) for i in range(3)],
    "anim": [(0, pose()), (0.4, pose(bell=-100, front=1, arm_f=-140, arm_b=-140)), (0.9, pose(bell=-60, front=1, arm_f=-110)),
             (1.4, pose(bell=-100, front=1, arm_f=-140)), (1.9, pose(bell=-60, front=1, arm_f=-110)), (2.8, pose())],
}

PHASE2 = {
    "dur": 2.6, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(1.0, 2.2, 20, 200, 16, 14, {**SOUND, "kb": 100}), spawn(1.4, "ghost", 2, 70, 140)],
    "anim": [(0, pose()), (0.7, pose(bell=-140, front=1, torso=0, head=-30, arm_f=-170, arm_b=-170)),
             (1.0, pose(bell=-210, front=1, torso=44, head=-40, arm_f=-40, arm_b=-40)), (2.6, pose())],
}

BOSS = {
    "id": "bellwarden", "name": "The Bellwarden", "tier": 1, "rig": "bellwarden", "art": "bellwarden", "arena": "belfry",
    "hp": 1450, "poise": 110, "radius": 18, "speed": 56,
    "moves": MOVES, "phases": [0.5], "phase_moves": {2: PHASE2},
    "adds": {"ghost": {"hp": 40, "speed": 32, "radius": 10, "dmg": 7, "art": "bellwarden.ghost", "life": 30, "float": 8, "alpha": 0.85}},
    "stagger_pose": {"torso": 50, "head": -40, "arm_f": 20, "arm_b": 20, "dy": 4}, "dead_pose": {"torso": 70, "head": -50, "arm_f": 30, "dy": 8},
}
