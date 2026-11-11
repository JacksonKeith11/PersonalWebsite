"""The Twin Headsmen: tier 2. Two executioners fought at once in the execution yard: the Hook, quick and
lean, who drags people in with a hooked chain; and the Axe, a slab of a man with a headsman's axe. They
try to split the party. When one falls, the other takes up their power: the Hook learns the Axe's
execution, the Axe learns to spin the chain.
"""

from .moves import DMG, arc, circle, rect, ring, proj, zone, pose

DMG[0] = 0.8
CHAIN = {"col": "#a8b0bc"}

HOOK_MOVES = {
    # the hook flies out and drags whoever it catches to his feet
    "chain": {
        "range": (60, 230), "weight": 4, "cd": 3.0, "phase": (1, 3), "dur": 1.6, "locks": [0.0, 0.4],
        "motion": [],
        "hits": [rect(0.55, 0.72, 10, 210, 9, 18, {**CHAIN, "kb": -150})],
        "anim": [(0, pose()), (0.45, pose(arm_f=-160, weapon=180, torso=-10)), (0.6, pose(arm_f=-90, weapon=90, torso=10, lean=3)), (1.6, pose())],
    },
    # three quick cuts, stepping in
    "flurry": {
        "range": (0, 70), "weight": 4, "cd": 1.2, "phase": (1, 3), "dur": 1.5, "locks": [0.0, 0.5, 0.8],
        "motion": [(0.3, 0.38, 10), (0.58, 0.66, 10), (0.88, 0.96, 14)],
        "hits": [arc(0.34, 0.42, 50, -70, 70, 12), arc(0.62, 0.7, 50, -70, 70, 12), arc(0.92, 1.0, 54, -60, 60, 15)],
        "anim": [(0, pose()), (0.28, pose(arm_f=-140, weapon=40)), (0.38, pose(arm_f=-10, weapon=100, torso=8)), (0.56, pose(arm_f=-150, weapon=140)),
                 (0.66, pose(arm_f=20, weapon=60, torso=8)), (0.86, pose(arm_f=-170, weapon=180, torso=-8)), (0.96, pose(arm_f=-40, weapon=110, torso=12)),
                 (1.5, pose())],
    },
    # he whirls the chain round him; get out or roll through
    "whirl": {
        "range": (0, 110), "weight": 3, "cd": 4.0, "phase": (1, 3), "dur": 2.0, "locks": [0.0],
        "motion": [],
        "hits": [circle(0.75, 1.15, 72, 0, 0, 20, CHAIN, mark=0.45)],
        "anim": [(0, pose()), (0.4, pose(arm_f=-170, weapon=180, torso=-6)), (0.75, pose(arm_f=-90, weapon=90)), (1.1, pose(arm_f=-90, weapon=90)),
                 (1.45, pose(arm_f=-90, weapon=90)), (2.0, pose())],
    },
    # a sudden dash and a cut
    "dash": {
        "range": (80, 260), "weight": 3, "cd": 2.5, "phase": (1, 3), "dur": 1.4, "locks": [0.0, 0.32],
        "motion": [(0.42, 0.62, ("target", 10, 50, 220))],
        "hits": [rect(0.48, 0.66, 0, 50, 14, 20)],
        "anim": [(0, pose()), (0.35, pose(torso=-14, arm_f=-150, weapon=200)), (0.45, pose(torso=24, lean=6, arm_f=-60, weapon=90, run=1)), (1.4, pose())],
    },
    # avenging the Axe: the execution, with the hook as the blade
    "execution": {
        "range": (0, 110), "weight": 3, "cd": 4.0, "phase": (3,), "enraged": True, "dur": 2.2, "locks": [0.0, 1.0],
        "motion": [(1.15, 1.25, 16)],
        "hits": [rect(1.2, 1.32, 0, 100, 18, 40), ring(1.25, 1.8, 20, 140, 10, 9, at=80)],
        "anim": [(0, pose()), (0.8, pose(arm_f=-185, weapon=160, torso=-14, dy=-2)), (1.15, pose(arm_f=-190, weapon=150, torso=-16)),
                 (1.25, pose(arm_f=-40, weapon=110, torso=20, lean=6, dy=2)), (2.2, pose())],
    },
}

AXE_MOVES = {
    # the execution: the axe goes up, hangs there, and falls
    "execution": {
        "range": (0, 110), "weight": 4, "cd": 3.0, "phase": (1, 3), "dur": 2.5, "locks": [0.0, 1.15],
        "motion": [(1.35, 1.45, 18)],
        "hits": [rect(1.4, 1.52, 0, 104, 22, 48), ring(1.45, 2.0, 24, 140, 12, 9, at=90)],
        "anim": [(0, pose()), (0.7, pose(arm_f=-180, arm_b=-180, weapon=170, torso=-14, dy=-3)), (1.35, pose(arm_f=-190, arm_b=-190, weapon=160, torso=-18)),
                 (1.45, pose(arm_f=-40, arm_b=-40, weapon=110, torso=22, lean=6, dy=3)), (2.5, pose())],
    },
    # a wide horizontal sweep
    "sweep": {
        "range": (0, 100), "weight": 4, "cd": 2.5, "phase": (1, 3), "dur": 2.0, "locks": [0.0, 0.6],
        "motion": [(0.85, 0.95, 12)],
        "hits": [arc(0.9, 1.04, 88, -105, 105, 36)],
        "anim": [(0, pose()), (0.7, pose(arm_f=-120, arm_b=-120, weapon=60, torso=-16)), (0.9, pose(arm_f=-60, arm_b=-60, weapon=80, torso=14, lean=4)),
                 (2.0, pose())],
    },
    # he stamps and the yard jumps
    "stomp": {
        "range": (0, 90), "weight": 3, "cd": 3.5, "phase": (1, 3), "dur": 1.6, "locks": [0.0],
        "motion": [],
        "hits": [circle(0.75, 0.85, 62, 0, 0, 26, mark=0.45), ring(0.8, 1.3, 50, 140, 10, 8)],
        "anim": [(0, pose()), (0.6, pose(leg_f=-50, torso=-8, dy=-3)), (0.78, pose(leg_f=10, torso=6, dy=2)), (1.6, pose())],
    },
    # a shoulder charge across the yard
    "charge": {
        "range": (120, 340), "weight": 3, "cd": 5.0, "phase": (1, 3), "dur": 2.4, "locks": [0.0, 0.7],
        "motion": [(0.9, 1.5, ("target", 50, 80, 300))],
        "hits": [circle(0.9, 1.5, 32, 0, 20, 30, {"kb": 110})],
        "anim": [(0, pose()), (0.7, pose(torso=-16, arm_b=-60, lean=-4)), (0.9, pose(torso=22, lean=8, arm_b=-80, run=1)), (1.5, pose(torso=20, lean=6, run=1)),
                 (2.4, pose())],
    },
    # avenging the Hook: he spins with the axe out, walking you down
    "whirlwind": {
        "range": (0, 220), "weight": 4, "cd": 4.0, "phase": (3,), "enraged": True, "dur": 3.0, "locks": [0.0, 1.3],
        "motion": [(0.7, 1.4, ("target", 0, 30, 120)), (1.4, 2.2, ("target", 0, 30, 120))],
        "hits": [circle(0.7, 2.2, 66, 0, 0, 24, mark=0.4)],
        "anim": [(0, pose()), (0.5, pose(arm_f=-90, arm_b=-90, weapon=90)), (1.0, pose(arm_f=-90, arm_b=-90, weapon=90, run=1)),
                 (1.5, pose(arm_f=-90, arm_b=-90, weapon=90, run=1)), (2.2, pose(arm_f=-90, arm_b=-90, weapon=90)), (3.0, pose())],
    },
}

HOOK_MOVES.update({
    # three throwing hooks, fanned
    "hooks": {
        "range": (100, 380), "weight": 1, "cd": 8.0, "phase": (1, 3), "dur": 1.5, "locks": [0.0, 0.45],
        "motion": [],
        "hits": [proj(0.6 + i * 0.08, 0, 16, a, 240, 7, 1.6, 18, CHAIN) for i, a in enumerate((-18, 0, 18))],
        "anim": [(0, pose()), (0.45, pose(arm_f=-160, weapon=200, torso=-10)), (0.62, pose(arm_f=-40, weapon=90, torso=10, lean=3)), (1.5, pose())],
    },
    # chains flung across the ground round you: they bleed whoever stands in them for a while
    "snare": {
        "range": (60, 360), "weight": 1, "cd": 12.0, "phase": (1, 3), "dur": 1.8, "locks": [0.0, 0.5], "reach": ("target", 0, 0, 320),
        "motion": [],
        "hits": [circle(1.0, 1.12, 26, 0, 0, 18, CHAIN, mark=0.5, tx=True),
                 *[zone(1.05, 5.0, 24, s, f, 6, "blood", tx=True, mark=0.5) for s, f in ((0, 44), (38, -22), (-38, -22))]],
        "anim": [(0, pose()), (0.5, pose(arm_f=-170, weapon=160, torso=-12)), (0.95, pose(arm_f=-60, weapon=100, torso=12, lean=4)), (1.8, pose())],
    },
})
AXE_MOVES["hurl"] = {  # it throws the axe: slow, big, and back to its hand after
    "range": (120, 420), "weight": 1, "cd": 9.0, "phase": (1, 3), "dur": 2.0, "locks": [0.0, 0.7],
    "motion": [],
    "hits": [proj(0.95, 0, 20, 0, 200, 16, 1.8, 34, {"col": "#c8c0b0", "kb": 80})],
    "anim": [(0, pose()), (0.7, pose(arm_f=-190, arm_b=-190, weapon=150, torso=-16, dy=-2)), (0.95, pose(arm_f=-40, arm_b=-40, weapon=90, torso=16, lean=5)),
             (2.0, pose())],
}

RAGE = {  # the survivor's roar when the other falls
    "dur": 2.0, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(0.8, 1.4, 20, 180, 14, 10, {"kb": 120})],
    "anim": [(0, pose()), (0.6, pose(torso=-16, head=-20, arm_f=-150, arm_b=-150)), (1.4, pose(torso=-14, head=-18, arm_f=-150, arm_b=-150)), (2.0, pose())],
}

HOOK = {"key": "hook", "name": "The Hook", "rig": "hook", "art": "hook", "hp": 1050, "poise": 85, "radius": 14, "speed": 74,
        "moves": HOOK_MOVES, "avenge": True, "phase_moves": {3: RAGE}}
AXE = {"key": "axe", "name": "The Axe", "rig": "axe", "art": "axe", "hp": 1450, "poise": 150, "radius": 22, "speed": 40,
       "moves": AXE_MOVES, "avenge": True, "phase_moves": {3: RAGE}}

BOSS = {"id": "headsmen", "name": "The Twin Headsmen", "tier": 2, "arena": "yard", "bodies": [HOOK, AXE], "adds": {}}
