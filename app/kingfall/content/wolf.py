"""The Briar Wolf: tier 2. A gaunt wolf the size of a horse in a thorn forest. Fast, circling, full of
feints: it crouches as if to pounce, then backs off and pounces a beat later. Its howl raises walls of
thorn that split the party. Phase 2: the forest goes dark; only its eyes and a glint before each
strike show, and it pounces twice.
"""

from .moves import DMG, arc, circle, rect, ring, zone, proj, pose

DMG[0] = 1.0
THORN = {"col": "#6a8a3a"}

MOVES = {
    # the pounce: a crouch, a leap, and teeth where it lands
    "pounce": {
        "range": (70, 260), "weight": 4, "cd": 2.5, "phase": (1, 2), "dur": 1.9, "locks": [0.0, 0.42], "air": (0.55, 0.85),
        "motion": [(0.5, 0.88, ("target", 10, 50, 230))],
        "hits": [circle(0.82, 0.95, 36, 0, 14, 30, mark=0.35)],
        "anim": [(0, pose()), (0.45, pose(dy=4, body=6, neck=10, leg_ff=30, leg_fb=30, leg_bf=-30, leg_bb=-30)),
                 (0.68, pose(z=34, body=-10, neck=-14, leg_ff=-50, leg_fb=-50, leg_bf=40, leg_bb=40, tail=-40)),
                 (0.88, pose(z=0, body=8, neck=14, jaw=30)), (1.2, pose(jaw=10)), (1.9, pose())],
    },
    # the feint: it crouches, hops back, then pounces for real
    "feint": {
        "range": (60, 200), "weight": 3, "cd": 4.0, "phase": (1, 2), "dur": 2.4, "locks": [0.0, 1.0], "air": (1.08, 1.38),
        "motion": [(0.45, 0.65, -50), (1.05, 1.42, ("target", 10, 60, 250))],
        "hits": [circle(1.36, 1.48, 36, 0, 14, 32, mark=0.3)],
        "anim": [(0, pose()), (0.4, pose(dy=4, body=6, neck=10, leg_ff=30, leg_bf=-30)), (0.6, pose(dy=0, body=-4, neck=-10)),
                 (0.95, pose(dy=4, body=6, neck=10, leg_ff=30, leg_bf=-30)), (1.2, pose(z=34, body=-10, neck=-14, leg_ff=-50, leg_bf=40, tail=-40)),
                 (1.42, pose(z=0, body=8, neck=14, jaw=30)), (2.4, pose())],
    },
    # two snapping bites
    "bite": {
        "range": (0, 70), "weight": 4, "cd": 1.2, "phase": (1, 2), "dur": 1.3, "locks": [0.0, 0.55],
        "motion": [(0.32, 0.4, 12), (0.7, 0.78, 12)],
        "hits": [arc(0.36, 0.45, 56, -45, 45, 22), arc(0.74, 0.83, 56, -45, 45, 22)],
        "anim": [(0, pose()), (0.3, pose(neck=-16, jaw=30)), (0.4, pose(neck=14, jaw=0)), (0.66, pose(neck=-16, jaw=30)), (0.78, pose(neck=14, jaw=0)),
                 (1.3, pose())],
    },
    # it wheels and lashes its thorned tail behind it
    "tail": {
        "range": (0, 90), "weight": 2, "cd": 3.0, "phase": (1, 2), "dur": 1.4, "locks": [0.0],
        "motion": [],
        "hits": [arc(0.55, 0.66, 80, 120, 180, 22, THORN), arc(0.55, 0.66, 80, -180, -120, 22, THORN), arc(0.62, 0.72, 64, -60, 60, 14)],
        "anim": [(0, pose()), (0.45, pose(tail=-60, body=-6)), (0.6, pose(tail=50, body=6)), (1.4, pose())],
    },
    # the howl: walls of thorn burst up across the clearing
    "howl": {
        "range": (0, 500), "weight": 2, "cd": 14.0, "phase": (1, 2), "dur": 2.0, "locks": [0.0],
        "motion": [],
        "hits": [zone(0.9, 7.0, 18, y, 70, 10, "thorn", tick=0.7, mark=0.6) for y in range(-210, 211, 35)],
        "anim": [(0, pose()), (0.5, pose(neck=-30, head=-20, jaw=36, body=-6)), (1.6, pose(neck=-30, head=-20, jaw=36)), (2.0, pose())],
    },
    # phase 2: two pounces from the dark
    "pounce2": {
        "range": (60, 300), "weight": 4, "cd": 4.0, "phase": (2,), "dur": 2.6, "locks": [0.0, 0.4, 1.3], "air": (0.5, 0.8),
        "motion": [(0.48, 0.82, ("target", 10, 50, 230)), (1.45, 1.8, ("target", 10, 50, 230))],
        "hits": [circle(0.78, 0.9, 36, 0, 14, 28, mark=0.3), circle(1.75, 1.87, 38, 0, 14, 30, mark=0.3)],
        "anim": [(0, pose()), (0.42, pose(dy=4, body=6, leg_ff=30, leg_bf=-30)), (0.65, pose(z=34, body=-10, leg_ff=-50, leg_bf=40)),
                 (0.82, pose(z=0, jaw=30)), (1.35, pose(dy=4, body=6, leg_ff=30, leg_bf=-30)), (1.6, pose(z=34, body=-10, leg_ff=-50, leg_bf=40)),
                 (1.8, pose(z=0, jaw=30)), (2.6, pose())],
    },
}

MOVES.update({
    # it flicks a spray of thorns from its tail
    "thorns": {
        "range": (100, 380), "weight": 2, "cd": 5.0, "phase": (1, 2), "dur": 1.5, "locks": [0.0, 0.45],
        "motion": [],
        "hits": [proj(0.65, 0, -6, a, 210, 7, 1.8, 16, THORN) for a in (-30, -15, 0, 15, 30)],
        "anim": [(0, pose()), (0.45, pose(tail=-70, body=-8, neck=-10)), (0.65, pose(tail=60, body=6, neck=6)), (1.5, pose())],
    },
    # roots burst under you and leave a thicket round the spot: get out before it closes
    "briar": {
        "range": (60, 400), "weight": 2, "cd": 8.0, "phase": (1, 2), "dur": 1.8, "locks": [0.0, 0.4], "reach": ("target", 0, 0, 360),
        "motion": [],
        "hits": [circle(1.05, 1.18, 34, 0, 0, 22, THORN, mark=0.65, tx=True),
                 *[zone(1.15, 5.0, 18, s, f, 8, "thorn", tick=0.7, tx=True, mark=0.65) for s, f in ((0, 52), (0, -52), (52, 0), (-52, 0))]],
        "anim": [(0, pose()), (0.4, pose(neck=-20, head=-14, jaw=20, body=-6, dy=2)), (1.0, pose(neck=14, jaw=30, leg_ff=-20, dy=3)), (1.8, pose())],
    },
})

PHASE2 = {
    "dur": 2.4, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(1.0, 1.6, 20, 170, 14, 10, {"kb": 100}),
             *[zone(1.2, 6.0, 18, y, -80, 10, "thorn", tick=0.7, mark=0.5) for y in range(-140, 141, 35)]],
    "anim": [(0, pose()), (0.7, pose(neck=-34, head=-22, jaw=40, body=-8)), (1.8, pose(neck=-34, head=-22, jaw=40)), (2.4, pose())],
}

BOSS = {
    "id": "wolf", "name": "The Briar Wolf", "tier": 2, "rig": "wolf", "art": "wolf", "arena": "forest",
    "hp": 2300, "poise": 140, "radius": 24, "speed": 88,
    "moves": MOVES, "phases": [0.5], "phase_moves": {2: PHASE2}, "dark": 2, "adds": {},
    "stagger_pose": {"body": 10, "neck": 20, "head": 10, "dy": 5}, "dead_pose": {"body": 14, "neck": 30, "head": 20, "dy": 10},
}
