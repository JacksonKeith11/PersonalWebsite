"""The Mire Mother: tier 1. A cart-sized toad in a drowned bog. She teaches watching the ground: her
belly-flop's shadow marks where she'll land, her poison pools shrink the safe floor, and her tongue
pulls you into her reach. Phase 2: she sinks into the mire and bursts up beneath you, and flops twice.
"""

from .moves import DMG, arc, circle, rect, ring, zone, spawn, proj, pose

DMG[0] = 0.85
TONGUE = {"col": "#c86a7a"}

MOVES = {
    # the tongue lash: her head rocks back, the jaw drops, then the tongue snaps out and drags you in
    "tongue": {
        "range": (40, 210), "weight": 4, "cd": 2.5, "phase": (1, 2), "dur": 1.6, "locks": [0.0, 0.42],
        "motion": [],
        "hits": [rect(0.62, 0.76, 22, 190, 9, 20, {**TONGUE, "kb": -110})],
        "anim": [(0, pose()), (0.45, pose(head=-14, body=-6, jaw=12)), (0.62, pose(head=6, body=4, jaw=34)),
                 (0.9, pose(head=4, jaw=30)), (1.6, pose())],
    },
    # the belly-flop: she squats, leaps, and lands where her shadow is
    "flop": {
        "range": (70, 280), "weight": 4, "cd": 3.0, "phase": (1, 2), "dur": 2.5, "locks": [0.0, 0.45], "air": (0.6, 1.2),
        "motion": [(0.55, 1.25, ("target", 0, 40, 230))],
        "hits": [circle(1.25, 1.36, 58, 0, 0, 34, mark=0.7), ring(1.3, 1.8, 40, 160, 10, 12, at=0)],
        "anim": [(0, pose()), (0.5, pose(dy=4, body=-8, hind_f=-20, hind_b=-20, fore_f=20)),
                 (0.9, pose(z=62, body=10, hind_f=50, hind_b=50, fore_f=-40, fore_b=-40)), (1.25, pose(z=0, dy=6, body=0, jaw=10)),
                 (1.5, pose(dy=3)), (2.5, pose())],
    },
    # phase 2: two flops back to back
    "flop2": {
        "range": (60, 300), "weight": 3, "cd": 5.0, "phase": (2,), "dur": 3.3, "locks": [0.0, 0.4, 1.5], "air": (0.55, 1.1),
        "motion": [(0.5, 1.12, ("target", 0, 40, 200)), (1.65, 2.25, ("target", 0, 40, 220))],
        "hits": [circle(1.12, 1.22, 54, 0, 0, 30, mark=0.6), circle(2.25, 2.35, 60, 0, 0, 34, mark=0.6),
                 ring(2.3, 2.8, 40, 170, 10, 12)],
        "anim": [(0, pose()), (0.45, pose(dy=4, body=-8, hind_f=-20, hind_b=-20)), (0.8, pose(z=50, body=10, hind_f=50, hind_b=50)),
                 (1.12, pose(z=0, dy=6)), (1.6, pose(dy=4, body=-8, hind_f=-20, hind_b=-20)),
                 (1.95, pose(z=60, body=10, hind_f=50, hind_b=50, fore_f=-40)), (2.25, pose(z=0, dy=6, jaw=12)), (3.3, pose())],
    },
    # she spits three gobs of poison that leave pools for a while
    "spit": {
        "range": (60, 360), "weight": 3, "cd": 6.0, "phase": (1, 2), "dur": 1.8, "locks": [0.0, 0.5], "reach": ("target", 0, 60, 220),
        "motion": [],
        "hits": [zone(0.95, 8.0, 26, s, f, 8, "poison", tx=True, mark=0.4) for s, f in ((-46, -10), (0, 18), (46, -10))],
        "anim": [(0, pose()), (0.5, pose(head=-18, body=-8, jaw=6)), (0.7, pose(head=8, jaw=36, body=4)), (1.0, pose(jaw=20)), (1.8, pose())],
    },
    # a quick slap with a forelimb when you're under her chin
    "slap": {
        "range": (0, 62), "weight": 3, "cd": 1.5, "phase": (1, 2), "dur": 1.2, "locks": [0.0, 0.3],
        "motion": [(0.4, 0.5, 10)],
        "hits": [arc(0.45, 0.56, 66, -80, 80, 22)],
        "anim": [(0, pose()), (0.35, pose(fore_f=-70, body=-6)), (0.48, pose(fore_f=40, body=6)), (1.2, pose())],
    },
    # she croaks up a brood of tadpoles
    "brood": {
        "range": (0, 500), "weight": 2, "cd": 16.0, "phase": (1, 2), "dur": 1.6, "locks": [0.0], "adds": "tadpole", "max_adds": 4,
        "motion": [],
        "hits": [spawn(0.9, "tadpole", 2, 50, 70)],
        "anim": [(0, pose()), (0.6, pose(dy=-3, body=-6, jaw=24, head=-10)), (0.9, pose(dy=2, jaw=6)), (1.6, pose())],
    },
    # phase 2: she sinks into the mire, slides under the floor and bursts up under you
    "erupt": {
        "range": (60, 400), "weight": 3, "cd": 6.0, "phase": (2,), "dur": 2.8, "locks": [0.0, 1.05], "under": (0.55, 1.75),
        "motion": [(0.7, 1.6, ("target", 0, 40, 300))],
        "hits": [circle(1.75, 1.88, 52, 0, 0, 36, mark=0.55), zone(1.8, 6.0, 34, 0, 0, 8, "poison")],
        "anim": [(0, pose()), (0.5, pose(dy=10)), (1.7, pose(dy=10)), (1.8, pose(z=34, jaw=30, head=-10)), (2.1, pose(z=0, jaw=10)), (2.8, pose())],
    },
}

MOVES["bile"] = {  # a spray of bile globs, fanned at whoever hangs back
    "range": (100, 400), "weight": 2, "cd": 5.0, "phase": (1, 2), "dur": 1.8, "locks": [0.0, 0.6],
    "motion": [],
    "hits": [proj(0.8 + abs(a) / 400, 0, 22, a, 170, 9, 2.2, 18, {"col": "#9ab83a"}) for a in (-40, -20, 0, 20, 40)],
    "anim": [(0, pose()), (0.6, pose(head=-18, body=-8, jaw=10)), (0.8, pose(head=8, jaw=40, body=4)), (1.2, pose(jaw=30)), (1.8, pose())],
}

PHASE2 = {
    "dur": 2.4, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(0.9, 1.5, 20, 190, 14, 10, {"kb": 120}), spawn(1.2, "tadpole", 3, 60, 80),
             zone(1.0, 7.0, 40, -90, 30, 8, "poison"), zone(1.0, 7.0, 40, 90, 30, 8, "poison")],
    "anim": [(0, pose()), (0.6, pose(dy=-4, jaw=36, head=-16, body=-8)), (1.4, pose(dy=-4, jaw=36, head=-12)), (2.4, pose())],
}

BOSS = {
    "id": "mire", "name": "The Mire Mother", "tier": 1, "rig": "toad", "art": "mire", "arena": "bog",
    "hp": 1900, "poise": 120, "radius": 30, "speed": 44,
    "moves": MOVES, "phases": [0.5], "phase_moves": {2: PHASE2},
    "adds": {"tadpole": {"hp": 34, "speed": 62, "radius": 9, "dmg": 7, "art": "mire.tadpole", "life": 25}},
    "stagger_pose": {"body": 10, "head": 14, "jaw": 20, "dy": 4}, "dead_pose": {"body": 12, "head": 20, "jaw": 30, "dy": 8},
}
