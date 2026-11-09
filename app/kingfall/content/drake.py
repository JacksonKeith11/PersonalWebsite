"""The Eclipse Drake: a final. A black dragon on a broken sky-bridge. Fire sweeps across the bridge
and leaves it burning; claws, a tail that sweeps behind it, a gust from its wings. Phase 2: it takes
to the air, diving across the bridge (its shadow shows the line) and raining fire. Phase 3: the
bridge's edges burn and everything comes faster.
"""

from .moves import DMG, arc, circle, rect, ring, proj, zone, pose

DMG[0] = 1.3
FIRE = {"fire": 1, "col": "#ff8a3a"}
BREATH = {"fire": 1, "col": "#ff8a3a", "unblock": True}

MOVES = {
    # it rears and sweeps a cone of fire across the bridge; the stones burn after
    "breath": {
        "range": (40, 360), "weight": 4, "cd": 3.5, "phase": (1, 2, 3), "dur": 3.0, "locks": [0.0, 0.8],
        "motion": [],
        "hits": [rect(1.1 + i * 0.14, 1.28 + i * 0.14, 20, 220, 16, 22, BREATH, rot=-50 + i * 20, mark=0.4 if i == 0 else None) for i in range(6)]
        + [zone(1.3 + i * 0.14, 4.0, 26, 0, 130, 6, "fire", rot=-50 + i * 20) for i in range(0, 6, 2)],
        "anim": [(0, pose()), (0.8, pose(neck=-30, head=-20, jaw=10, body=-6)), (1.1, pose(neck=10, head=0, jaw=40)), (1.9, pose(neck=10, jaw=40)),
                 (2.2, pose(jaw=10)), (3.0, pose())],
    },
    # claws raking forward, twice
    "claws": {
        "range": (0, 110), "weight": 4, "cd": 1.4, "phase": (1, 2, 3), "dur": 1.8, "locks": [0.0, 0.7],
        "motion": [(0.5, 0.6, 14), (0.95, 1.05, 14)],
        "hits": [arc(0.55, 0.66, 92, -70, 70, 32), arc(1.0, 1.11, 92, -70, 70, 32)],
        "anim": [(0, pose()), (0.4, pose(leg_ff=-60, body=-6, neck=-10)), (0.58, pose(leg_ff=30, body=6, neck=10, jaw=20)),
                 (0.85, pose(leg_fb=-60, body=-6)), (1.02, pose(leg_fb=30, body=6, jaw=20)), (1.8, pose())],
    },
    # it swings round and its tail sweeps behind it
    "tail": {
        "range": (0, 160), "weight": 3, "cd": 3.0, "phase": (1, 2, 3), "dur": 1.8, "locks": [0.0],
        "motion": [],
        "hits": [arc(0.7, 0.84, 140, 110, 180, 30), arc(0.7, 0.84, 140, -180, -110, 30)],
        "anim": [(0, pose()), (0.5, pose(tail=-50, body=-8)), (0.75, pose(tail=60, body=8)), (1.8, pose())],
    },
    # a beat of its wings throws everyone back
    "gust": {
        "range": (0, 200), "weight": 2, "cd": 5.0, "phase": (1, 2, 3), "dur": 1.8, "locks": [0.0],
        "motion": [(0.8, 1.0, -30)],
        "hits": [circle(0.8, 0.95, 110, 0, 20, 14, {"kb": 180}, mark=0.4)],
        "anim": [(0, pose()), (0.5, pose(wing_b=-70, wing_f=-60, dy=-4)), (0.85, pose(wing_b=20, wing_f=20, dy=2)), (1.8, pose())],
    },
    # phase 2+: it takes off and dives along the bridge
    "dive": {
        "range": (80, 500), "weight": 4, "cd": 5.0, "phase": (2, 3), "dur": 3.4, "locks": [0.0, 0.9], "air": (0.6, 2.2),
        "motion": [(1.2, 2.0, ("target", 120, 160, 420))],
        "hits": [rect(1.2, 2.0, -30, 30, 40, 40, FIRE, mark=0.0), zone(2.0, 4.0, 40, 0, 0, 7, "fire")],
        "anim": [(0, pose()), (0.6, pose(z=30, wing_b=-80, wing_f=-70)), (1.0, pose(z=90, wing_b=10, wing_f=10)), (1.2, pose(z=40, body=14, neck=20)),
                 (2.0, pose(z=0, body=0)), (2.4, pose()), (3.4, pose())],
    },
    # phase 2+: fire rains down where you stand
    "firerain": {
        "range": (0, 600), "weight": 3, "cd": 5.0, "phase": (2, 3), "dur": 2.8, "locks": [0.0, 0.3, 1.1], "reach": ("target", 0, 0, 400), "air": (0.4, 2.2),
        "motion": [],
        "hits": [circle(1.0 + i * 0.16, 1.12 + i * 0.16, 32, s, f, 30, FIRE, mark=0.8, tx=True)
                 for i, (s, f) in enumerate(((0, 0), (-70, 30), (70, 30), (0, -80), (-110, -50), (110, -50), (0, 100)))],
        "anim": [(0, pose()), (0.4, pose(z=60, wing_b=-80, wing_f=-70)), (2.2, pose(z=60, wing_b=10)), (2.8, pose(z=0))],
    },
}

PHASE2 = {
    "dur": 2.6, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(1.0, 1.8, 30, 200, 16, 14, {**FIRE, "kb": 130})],
    "anim": [(0, pose()), (0.7, pose(z=40, wing_b=-90, wing_f=-80, neck=-30, jaw=40)), (1.8, pose(z=40, wing_b=10, wing_f=10)), (2.6, pose())],
}
PHASE3 = {  # the bridge's edges catch fire and stay burning
    "dur": 2.4, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(1.0, 1.8, 30, 210, 16, 14, {**FIRE, "kb": 120})]
    + [zone(1.4, 60.0, 34, side * 190, f, 8, "fire") for side in (-1, 1) for f in (-160, -80, 0, 80, 160)],
    "anim": [(0, pose()), (0.7, pose(neck=-34, head=-20, jaw=40)), (1.8, pose(neck=-34, jaw=40)), (2.4, pose())],
}

BOSS = {
    "id": "drake", "name": "The Eclipse Drake", "tier": 4, "rig": "drake", "art": "drake", "arena": "bridge",
    "hp": 4800, "poise": 220, "radius": 34, "speed": 46,
    "moves": MOVES, "phases": [0.6, 0.25], "phase_moves": {2: PHASE2, 3: PHASE3}, "adds": {},
    "stagger_pose": {"body": 8, "neck": 30, "head": 20, "dy": 6}, "dead_pose": {"body": 12, "neck": 40, "head": 30, "dy": 10},
}
