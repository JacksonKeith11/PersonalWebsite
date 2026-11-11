"""The Bastion: tier 3. A siege tower that learned to walk, on a broken wall. Slow and enormous: rocket
fists, stomps, a furnace eye whose beam sweeps the battlements. Its stone shrugs off most of a blow
(armour) until its three glowing cores are broken: both knees and the one on its back. Break them all
and it topples for a long while, open to criticals; then the cores glow again. Phase 2: it fires both
fists and the beam sweeps both ways.
"""

from .moves import DMG, arc, circle, rect, ring, zone, pose

DMG[0] = 1.15
STONE = {"col": "#a8a0b0"}
BEAM = {"col": "#ffb040", "fire": 1, "unblock": True}

MOVES = {
    # a fist on a chain of fire, flung straight down the wall
    "rocket": {
        "range": (60, 400), "weight": 4, "cd": 3.0, "phase": (1, 2), "dur": 2.4, "locks": [0.0, 0.8],
        "motion": [],
        "hits": [rect(1.1, 1.32, 20, 240, 18, 42, STONE, mark=0.6)],
        "anim": [(0, pose()), (0.8, pose(arm_f=-60, torso=-6)), (1.1, pose(arm_f=-90, torso=8, lean=4)), (1.6, pose(arm_f=-90)), (2.4, pose())],
    },
    # it stamps and the stones jump
    "stomp": {
        "range": (0, 120), "weight": 4, "cd": 3.0, "phase": (1, 2), "dur": 2.0, "locks": [0.0],
        "motion": [],
        "hits": [circle(0.95, 1.08, 74, 0, 0, 36, STONE, mark=0.55), ring(1.0, 1.6, 60, 170, 12, 9, STONE)],
        "anim": [(0, pose()), (0.75, pose(leg_f=-40, torso=-6, dy=-4)), (0.98, pose(leg_f=6, torso=6, dy=3)), (2.0, pose())],
    },
    # the furnace eye: a beam that sweeps across from one side to the other
    "beam": {
        "range": (60, 500), "weight": 3, "cd": 6.0, "phase": (1, 2), "dur": 3.0, "locks": [0.0, 0.7],
        "motion": [],
        "hits": [rect(1.1 + i * 0.14, 1.26 + i * 0.14, 30, 330, 10, 20, BEAM, rot=-60 + i * 20, mark=0.4 if i == 0 else None) for i in range(7)],
        "anim": [(0, pose()), (0.8, pose(head=-14, torso=-6)), (1.1, pose(head=-8)), (2.1, pose(head=8)), (3.0, pose())],
    },
    # both fists brought down in front of it
    "hammer": {
        "range": (0, 130), "weight": 3, "cd": 3.5, "phase": (1, 2), "dur": 2.6, "locks": [0.0, 1.1],
        "motion": [(1.3, 1.4, 16)],
        "hits": [rect(1.36, 1.5, 0, 120, 34, 50, STONE), ring(1.42, 2.0, 40, 150, 12, 8, STONE, at=90)],
        "anim": [(0, pose()), (0.9, pose(arm_f=-170, arm_b=-170, torso=-10, dy=-4)), (1.3, pose(arm_f=-175, arm_b=-175, torso=-12)),
                 (1.42, pose(arm_f=-20, arm_b=-20, torso=16, lean=6, dy=3)), (2.6, pose())],
    },
    # phase 2: both fists, one after the other
    "rocket2": {
        "range": (60, 420), "weight": 4, "cd": 4.0, "phase": (2,), "dur": 3.0, "locks": [0.0, 0.7, 1.4],
        "motion": [],
        "hits": [rect(0.95, 1.15, 20, 240, 18, 40, STONE, mark=0.5), rect(1.65, 1.85, 20, 240, 18, 40, STONE, mark=0.5)],
        "anim": [(0, pose()), (0.7, pose(arm_f=-60)), (0.95, pose(arm_f=-90, lean=4)), (1.4, pose(arm_b=-60, arm_f=-40)), (1.65, pose(arm_b=-90, lean=4)),
                 (3.0, pose())],
    },
    # phase 2: the beam sweeps there and back
    "beam2": {
        "range": (60, 500), "weight": 3, "cd": 7.0, "phase": (2,), "dur": 3.6, "locks": [0.0, 0.6],
        "motion": [],
        "hits": [rect(0.95 + i * 0.14, 1.11 + i * 0.14, 30, 330, 10, 20, BEAM, rot=-60 + i * 20, mark=0.4 if i == 0 else None) for i in range(7)]
        + [rect(2.0 + i * 0.14, 2.16 + i * 0.14, 30, 330, 10, 20, BEAM, rot=60 - i * 20) for i in range(7)],
        "anim": [(0, pose()), (0.7, pose(head=-14)), (2.0, pose(head=8)), (3.0, pose(head=-8)), (3.6, pose())],
    },
}

# the back core lobs shells over the wall at whoever it looks at; each leaves fire behind
MOVES["mortar"] = {
    "range": (100, 520), "weight": 3, "cd": 6.0, "phase": (1, 2), "dur": 2.6, "locks": [0.0, 0.6], "reach": ("target", 0, 0, 460),
    "motion": [],
    "hits": [h for i, (s, f) in enumerate(((0, 0), (-56, 36), (56, -36)))
             for h in (circle(1.3 + i * 0.22, 1.42 + i * 0.22, 32, s, f, 28, {"col": "#ffb040", "fire": 1}, mark=0.9, tx=True),
                       zone(1.36 + i * 0.22, 3.0, 28, s, f, 6, "fire", tx=True))],
    "anim": [(0, pose()), (0.6, pose(torso=-14, head=-16, dy=-3)), (0.9, pose(torso=8, head=4, dy=2)), (1.1, pose(torso=-10, head=-12)),
             (1.3, pose(torso=6)), (2.6, pose())],
}

PHASE2 = {
    "dur": 2.4, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [circle(1.0, 1.12, 90, 0, 0, 20, {**STONE, "kb": 130}, mark=0.6), ring(1.05, 1.8, 80, 190, 14, 14, STONE)],
    "anim": [(0, pose()), (0.7, pose(arm_f=-170, arm_b=-170, head=-16, dy=-4)), (1.05, pose(arm_f=-10, arm_b=-10, dy=4)), (2.4, pose())],
}

BOSS = {
    "id": "bastion", "name": "The Bastion", "tier": 3, "rig": "golem", "art": "bastion", "arena": "wall",
    "hp": 2300, "poise": 400, "radius": 34, "speed": 26, "armor": 0.5,
    "cores": [{"dx": -18, "dy": 6, "r": 13, "hp": 140, "h": 22}, {"dx": 18, "dy": 6, "r": 13, "hp": 140, "h": 22},
              {"dx": -40, "dy": -10, "r": 14, "hp": 180, "h": 96}],
    "moves": MOVES, "phases": [0.5], "phase_moves": {2: PHASE2}, "adds": {},
    "stagger_pose": {"torso": 14, "head": 12, "arm_f": 20, "arm_b": 20, "dy": 8}, "dead_pose": {"torso": 24, "head": 20, "dy": 14},
}
