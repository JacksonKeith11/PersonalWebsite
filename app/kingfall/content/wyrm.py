"""The Gravewyrm: tier 2. A serpent of bone in a boneyard. It burrows (its path shows as a ridge of
churned earth) and bursts up under you, bites, spits bone shards, and coils round to trap you in a
closing ring. Its glowing vertebrae can be struck as well as its head. Phase 2: it burrows twice and
the ring closes faster.
"""

from .moves import DMG, arc, circle, rect, ring, proj, zone, pose

DMG[0] = 1.25
BONE = {"col": "#d8ccb0"}

MOVES = {
    # it dives, slides under the floor and bursts up beneath you
    "burrow": {
        "range": (80, 420), "weight": 4, "cd": 3.0, "phase": (1, 2), "dur": 2.6, "locks": [0.0, 0.9], "under": (0.5, 1.6),
        "motion": [(0.6, 1.5, ("target", 0, 60, 320))],
        "hits": [circle(1.62, 1.76, 50, 0, 0, 38, mark=0.45)],
        "anim": [(0, pose()), (0.45, pose(head=30, z=-8)), (1.6, pose(head=-40, z=30, jaw=40)), (1.9, pose(head=-10, z=8, jaw=20)), (2.6, pose())],
    },
    # a lunging bite
    "bite": {
        "range": (0, 140), "weight": 4, "cd": 0.8, "phase": (1, 2), "dur": 1.5, "locks": [0.0, 0.42],
        "motion": [(0.5, 0.7, ("target", 0, 20, 110))],
        "hits": [rect(0.55, 0.74, 0, 64, 16, 32)],
        "anim": [(0, pose()), (0.42, pose(head=-20, jaw=10)), (0.6, pose(head=10, jaw=40)), (0.75, pose(head=6, jaw=0)), (1.5, pose())],
    },
    # it spits a fan of bone shards
    "shards": {
        "range": (80, 400), "weight": 3, "cd": 3.5, "phase": (1, 2), "dur": 1.6, "locks": [0.0, 0.5],
        "motion": [],
        "hits": [proj(0.7 + abs(a) / 400, 0, 20, a, 210, 7, 1.8, 18, BONE) for a in (-40, -24, -8, 8, 24, 40)],
        "anim": [(0, pose()), (0.5, pose(head=-24, jaw=6)), (0.7, pose(head=8, jaw=40)), (1.0, pose(jaw=10)), (1.6, pose())],
    },
    # it thrashes its coils round itself
    "thrash": {
        "range": (0, 100), "weight": 3, "cd": 3.0, "phase": (1, 2), "dur": 1.6, "locks": [0.0],
        "motion": [],
        "hits": [circle(0.72, 0.86, 76, 0, 0, 30, BONE, mark=0.4)],
        "anim": [(0, pose()), (0.5, pose(head=-30, z=8)), (0.75, pose(head=30, z=0)), (1.6, pose())],
    },
    # the coil: a ring of bone closes in round you; roll through it before it meets
    "coil": {
        "range": (40, 260), "weight": 3, "cd": 6.0, "phase": (1, 2), "dur": 2.6, "locks": [0.0, 0.6], "reach": ("target", 0, 40, 240),
        "motion": [],
        "hits": [ring(0.9, 2.3, 130, -85, 12, 22, BONE, at=0, tx=True), circle(2.3, 2.45, 26, 0, 0, 30, BONE, tx=True, mark=0.5)],
        "anim": [(0, pose()), (0.6, pose(head=-20, jaw=30)), (2.3, pose(head=10, jaw=0)), (2.6, pose())],
    },
    # phase 2: two burrows, the second chasing where you rolled to
    "burrow2": {
        "range": (80, 420), "weight": 4, "cd": 5.0, "phase": (2,), "dur": 3.6, "locks": [0.0, 0.8, 1.9], "under": (0.45, 2.6),
        "motion": [(0.55, 1.35, ("target", 0, 60, 300)), (1.95, 2.55, ("target", 0, 40, 240))],
        "hits": [circle(1.42, 1.54, 42, 0, 0, 26, mark=0.45), circle(2.62, 2.76, 48, 0, 0, 32, mark=0.45), zone(2.7, 4.0, 30, 0, 0, 6, "void")],
        "anim": [(0, pose()), (0.4, pose(head=30, z=-8)), (2.6, pose(head=-40, z=30, jaw=40)), (2.9, pose(head=-10, z=8, jaw=20)), (3.6, pose())],
    },
}

PHASE2 = {
    "dur": 2.2, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(0.8, 1.4, 20, 180, 14, 10, {**BONE, "kb": 110}), *[proj(1.0, 0, 0, a, 170, 7, 1.6, 12, BONE) for a in range(-180, 180, 30)]],
    "anim": [(0, pose()), (0.6, pose(head=-40, z=20, jaw=40)), (1.6, pose(head=-40, z=20, jaw=40)), (2.2, pose())],
}

BOSS = {
    "id": "wyrm", "name": "The Gravewyrm", "tier": 2, "rig": "wyrm", "art": "wyrm", "arena": "boneyard", "render": "wyrm",
    "hp": 3000, "poise": 260, "radius": 18, "speed": 84,
    "moves": MOVES, "phases": [0.5], "phase_moves": {2: PHASE2}, "adds": {},
    "stagger_pose": {"head": 30, "jaw": 30, "z": -4}, "dead_pose": {"head": 40, "jaw": 40, "z": -6},
}
