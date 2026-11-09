"""The Mirror Knight: tier 3. A knight of silvered glass in a hall of mirrors. It fights like the heroes
do (a three-cut combo, a lunge, a parrying stance) and fills the hall with their reflections: glass
copies that hunt whoever they mirror. Phase 2: it shatters the mirrors and shards rain on the hall.
"""

from .moves import DMG, arc, circle, rect, ring, proj, spawn, pose

DMG[0] = 1.15
GLASS = {"col": "#a0d8f0"}

MOVES = {
    # the heroes' own combo, turned on them: three cuts stepping in
    "combo": {
        "range": (0, 80), "weight": 4, "cd": 1.0, "phase": (1, 2), "dur": 1.9, "locks": [0.0, 0.55, 1.0],
        "motion": [(0.32, 0.42, 14), (0.72, 0.8, 12), (1.2, 1.3, 20)],
        "hits": [arc(0.36, 0.46, 66, -70, 70, 22, GLASS), arc(0.76, 0.86, 66, -70, 70, 22, GLASS), rect(1.24, 1.36, 0, 86, 14, 30, GLASS)],
        "anim": [(0, pose()), (0.3, pose(arm_f=-150, weapon=40, torso=-6)), (0.42, pose(arm_f=-30, weapon=100, torso=8)),
                 (0.68, pose(arm_f=-20, weapon=100)), (0.8, pose(arm_f=-140, weapon=-60, torso=-6)), (1.15, pose(arm_f=-100, weapon=-80, torso=-10)),
                 (1.28, pose(arm_f=-90, weapon=0, torso=14, lean=6)), (1.9, pose())],
    },
    # a gliding lunge across the hall
    "glide": {
        "range": (90, 320), "weight": 3, "cd": 2.5, "phase": (1, 2), "dur": 1.6, "locks": [0.0, 0.42],
        "motion": [(0.5, 0.78, ("target", 20, 60, 280))],
        "hits": [rect(0.55, 0.82, 0, 70, 14, 30, GLASS)],
        "anim": [(0, pose()), (0.42, pose(arm_f=-100, weapon=-50, torso=-10)), (0.6, pose(arm_f=-90, weapon=0, torso=14, lean=8)), (1.6, pose())],
    },
    # a fan of glass shards
    "shards": {
        "range": (80, 400), "weight": 3, "cd": 3.5, "phase": (1, 2), "dur": 1.5, "locks": [0.0, 0.5],
        "motion": [],
        "hits": [proj(0.65 + abs(a) / 600, 0, 20, a, 220, 7, 1.8, 18, GLASS) for a in (-45, -30, -15, 0, 15, 30, 45)],
        "anim": [(0, pose()), (0.5, pose(arm_f=-160, weapon=-20)), (0.65, pose(arm_f=-60, weapon=90, torso=10)), (1.5, pose())],
    },
    # it raises the blade and waits; strike its front and it answers
    "stance": {
        "range": (0, 120), "weight": 2, "cd": 6.0, "phase": (1, 2), "dur": 2.3, "locks": [0.0, 1.5], "guard": (0.2, 1.6),
        "motion": [(1.6, 1.7, 22)],
        "hits": [arc(1.62, 1.74, 76, -90, 90, 34, GLASS)],
        "anim": [(0, pose()), (0.2, pose(arm_f=-120, weapon=-80, torso=-6)), (1.55, pose(arm_f=-125, weapon=-85, torso=-8)),
                 (1.68, pose(arm_f=-10, weapon=110, torso=14, lean=6)), (2.3, pose())],
    },
    # reflections step out of the mirrors
    "reflect": {
        "range": (0, 500), "weight": 2, "cd": 15.0, "phase": (1, 2), "dur": 1.8, "locks": [0.0], "adds": "reflection", "max_adds": 4,
        "motion": [],
        "hits": [spawn(1.0, "reflection", 2, 70, 160)],
        "anim": [(0, pose()), (0.6, pose(arm_f=-170, weapon=0, arm_b=-170, head=-10)), (1.2, pose(arm_f=-170, arm_b=-170)), (1.8, pose())],
    },
    # phase 2: shards rain on the hall in marked circles
    "rain": {
        "range": (0, 500), "weight": 3, "cd": 6.0, "phase": (2,), "dur": 2.6, "locks": [0.0, 0.3], "reach": ("target", 0, 0, 300),
        "motion": [],
        "hits": [circle(1.2 + i * 0.15, 1.32 + i * 0.15, 30, s, f, 24, GLASS, mark=0.8, tx=True)
                 for i, (s, f) in enumerate(((0, 0), (-60, -30), (60, -30), (-40, 60), (40, 60), (0, -90), (-110, 20), (110, 20)))],
        "anim": [(0, pose()), (0.5, pose(arm_f=-170, weapon=0, head=-14)), (2.0, pose(arm_f=-170, weapon=0)), (2.6, pose())],
    },
}

PHASE2 = {
    "dur": 2.2, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(0.8, 1.4, 20, 190, 14, 12, {**GLASS, "kb": 110}), *[proj(1.0, 0, 0, a, 180, 7, 1.6, 14, GLASS) for a in range(-165, 180, 30)]],
    "anim": [(0, pose()), (0.6, pose(arm_f=-170, arm_b=-170, weapon=0, head=-16)), (1.6, pose(arm_f=-170, arm_b=-170)), (2.2, pose())],
}

BOSS = {
    "id": "mirror", "name": "The Mirror Knight", "tier": 3, "rig": "mirror", "art": "mirror", "arena": "glass",
    "hp": 2700, "poise": 150, "radius": 20, "speed": 64,
    "moves": MOVES, "phases": [0.5], "phase_moves": {2: PHASE2},
    "adds": {"reflection": {"hp": 70, "speed": 58, "radius": 10, "dmg": 12, "art": "mirror.reflection", "life": 22, "alpha": 0.8}},
}
