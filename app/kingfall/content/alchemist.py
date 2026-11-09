"""The Ashen Alchemist: tier 2. A tall figure on stilts in a ruined laboratory, who keeps its distance
and throws: fire that pools, frost that lingers, poison that eats the floor. It hops away from anyone
who closes in and calls up waddling homunculi. Phase 2: it transmutes the floor, scattering pools
across the room, and its mixtures explode where they meet.
"""

from .moves import DMG, arc, circle, rect, ring, zone, spawn, proj, pose

DMG[0] = 1.0
FIRE = {"fire": 1}

THROW = [(0, pose()), (0.45, pose(arm_f=-170, weapon=0, torso=-10)), (0.62, pose(arm_f=-40, weapon=60, torso=10)), (1.4, pose())]

MOVES = {
    # a flask of fire lobbed at you; it bursts and burns there a while
    "fireflask": {
        "range": (60, 400), "weight": 4, "cd": 2.5, "phase": (1, 2), "dur": 1.4, "locks": [0.0, 0.45], "reach": ("target", 0, 50, 320),
        "motion": [],
        "hits": [circle(0.95, 1.05, 34, 0, 0, 24, FIRE, mark=0.4, tx=True), zone(1.0, 4.0, 26, 0, 0, 4, "fire", tx=True)],
        "anim": THROW,
    },
    # three flasks at once, fanned around you
    "volley": {
        "range": (80, 400), "weight": 3, "cd": 4.0, "phase": (1, 2), "dur": 1.8, "locks": [0.0, 0.5], "reach": ("target", 0, 60, 300),
        "motion": [],
        "hits": [circle(1.05, 1.15, 30, s, f, 20, {"col": c}, mark=0.45, tx=True) for s, f, c in ((-60, 0, "#7fe3ff"), (0, 30, "#8be04e"), (60, 0, "#ff8a3a"))]
        + [zone(1.1, 4.0, 24, -60, 0, 3, "ice", tx=True), zone(1.1, 4.0, 24, 0, 30, 4, "poison", tx=True), zone(1.1, 3.5, 22, 60, 0, 4, "fire", tx=True)],
        "anim": [(0, pose()), (0.5, pose(arm_f=-170, arm_b=-170, weapon=0, torso=-12)), (0.7, pose(arm_f=-30, arm_b=-30, weapon=60, torso=12)), (1.8, pose())],
    },
    # a stamp of the stilts when you're under it
    "stamp": {
        "range": (0, 70), "weight": 3, "cd": 2.0, "phase": (1, 2), "dur": 1.3, "locks": [0.0],
        "motion": [],
        "hits": [circle(0.55, 0.65, 46, 0, 8, 24, mark=0.35)],
        "anim": [(0, pose()), (0.4, pose(leg_f=-40, dy=-4)), (0.58, pose(leg_f=6, dy=1)), (1.3, pose())],
    },
    # it vaults away from whoever's close, leaving a puff of poison
    "vault": {
        "range": (0, 90), "weight": 3, "cd": 3.0, "phase": (1, 2), "dur": 1.2, "locks": [0.0], "air": (0.25, 0.65),
        "motion": [(0.25, 0.7, -110)],
        "hits": [zone(0.2, 4.0, 30, 0, 0, 7, "poison")],
        "anim": [(0, pose()), (0.2, pose(dy=4, torso=10)), (0.45, pose(z=26, torso=-10, leg_f=-20, leg_b=20)), (0.7, pose(z=0)), (1.2, pose())],
    },
    # glass-bellied homunculi waddle out of the smoke
    "homunculi": {
        "range": (0, 500), "weight": 2, "cd": 14.0, "phase": (1, 2), "dur": 1.6, "locks": [0.0], "adds": "homunculus", "max_adds": 4,
        "motion": [],
        "hits": [spawn(0.9, "homunculus", 2, 40, 90)],
        "anim": [(0, pose()), (0.6, pose(arm_f=-120, arm_b=-120, weapon=40)), (1.0, pose(arm_f=-60, arm_b=-60)), (1.6, pose())],
    },
    # phase 2: the great mixture: three flasks round you, then the blast where they meet
    "mixture": {
        "range": (60, 400), "weight": 4, "cd": 6.0, "phase": (2,), "dur": 2.6, "locks": [0.0, 0.5], "reach": ("target", 0, 60, 300),
        "motion": [],
        "hits": [zone(0.95, 1.3, 24, s, f, 8, p, tx=True) for s, f, p in ((-55, -30, "fire"), (55, -30, "ice"), (0, 55, "poison"))]
        + [circle(2.25, 2.4, 82, 0, 0, 40, FIRE, mark=1.0, tx=True)],
        "anim": [(0, pose()), (0.5, pose(arm_f=-170, weapon=0)), (0.7, pose(arm_f=-30, weapon=60)), (2.0, pose(arm_f=-160, arm_b=-160, torso=-14)),
                 (2.3, pose(arm_f=-60, arm_b=-60, torso=8)), (2.6, pose())],
    },
    # phase 2: a spray of burning droplets
    "spray": {
        "range": (60, 260), "weight": 3, "cd": 4.0, "phase": (2,), "dur": 1.7, "locks": [0.0, 0.5],
        "motion": [],
        "hits": [proj(0.7 + i * 0.05, 0, 16, a, 170, 8, 1.6, 14, FIRE) for i, a in enumerate((-40, -20, 0, 20, 40, -30, 30))],
        "anim": [(0, pose()), (0.55, pose(arm_f=-130, weapon=-60)), (0.75, pose(arm_f=-80, weapon=-90)), (1.0, pose(arm_f=-60, weapon=-90)), (1.7, pose())],
    },
}

PHASE2 = {  # it transmutes the floor: pools bloom all over the laboratory
    "dur": 2.6, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(0.9, 1.5, 20, 180, 14, 10, {"kb": 100})]
    + [zone(1.3 + i * 0.12, 7.0, 26, s, f, 7, p, mark=0.4) for i, (s, f, p) in
       enumerate(((-150, 90, "poison"), (150, 90, "fire"), (-80, 200, "ice"), (80, 200, "poison"), (0, -150, "fire"), (-200, -60, "ice"), (200, -60, "poison")))],
    "anim": [(0, pose()), (0.6, pose(arm_f=-170, arm_b=-170, torso=-14, head=-10)), (1.6, pose(arm_f=-170, arm_b=-170)), (2.6, pose())],
}

BOSS = {
    "id": "alchemist", "name": "The Ashen Alchemist", "tier": 2, "rig": "alchemist", "art": "alchemist", "arena": "lab",
    "hp": 1550, "poise": 105, "radius": 16, "speed": 58, "keep": 160,
    "moves": MOVES, "phases": [0.5], "phase_moves": {2: PHASE2},
    "adds": {"homunculus": {"hp": 36, "speed": 40, "radius": 9, "dmg": 6, "art": "alchemist.homunculus", "life": 25}},
    "stagger_pose": {"torso": 20, "head": 14, "arm_f": 30, "arm_b": 30, "dy": 4}, "dead_pose": {"torso": 34, "head": 20, "dy": 10},
}
