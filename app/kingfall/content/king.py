"""The Hollow King: a final. Three phases in the throne room. First the dead king as he was, an elegant
duellist: lunges, a four-cut flourish, a riposte stance. Then the crown swells him into the hollow
giant (his art changes): a bone blade, slams, pools of void. Last, the roof gives way: stars fall in
marked circles while he fights on, faster.
"""

from .moves import DMG, arc, circle, rect, ring, proj, zone, pose

DMG[0] = 1.3
VOID = {"col": "#c060ff"}

MOVES = {
    # phase 1, the duellist ------------------------------------------------------------
    "lunge": {
        "range": (40, 220), "weight": 4, "cd": 1.4, "phase": (1,), "dur": 1.3, "locks": [0.0, 0.32],
        "motion": [(0.4, 0.58, ("target", 10, 40, 190))],
        "hits": [rect(0.44, 0.62, 0, 74, 9, 26)],
        "anim": [(0, pose()), (0.3, pose(arm_f=-100, weapon=-50, torso=-10, lean=-3)), (0.45, pose(arm_f=-90, weapon=0, torso=14, lean=8)), (1.3, pose())],
    },
    "flourish": {
        "range": (0, 80), "weight": 4, "cd": 1.5, "phase": (1,), "dur": 2.0, "locks": [0.0, 0.5, 0.85, 1.2],
        "motion": [(0.3, 0.38, 10), (0.65, 0.72, 10), (1.0, 1.07, 10), (1.38, 1.48, 18)],
        "hits": [arc(0.34, 0.42, 60, -60, 60, 18), arc(0.68, 0.76, 60, -60, 60, 18), arc(1.03, 1.11, 60, -60, 60, 18), rect(1.42, 1.54, 0, 86, 10, 28)],
        "anim": [(0, pose()), (0.28, pose(arm_f=-150, weapon=40)), (0.4, pose(arm_f=-20, weapon=100)), (0.62, pose(arm_f=-140, weapon=-50)),
                 (0.72, pose(arm_f=10, weapon=70)), (0.98, pose(arm_f=-160, weapon=20)), (1.08, pose(arm_f=-30, weapon=100)),
                 (1.35, pose(arm_f=-100, weapon=-60, torso=-8)), (1.46, pose(arm_f=-90, weapon=0, torso=14, lean=6)), (2.0, pose())],
    },
    "riposte": {
        "range": (0, 120), "weight": 2, "cd": 6.0, "phase": (1,), "dur": 2.0, "locks": [0.0, 1.25], "guard": (0.2, 1.3),
        "motion": [(1.35, 1.48, 30)],
        "hits": [rect(1.38, 1.52, 0, 90, 12, 34)],
        "anim": [(0, pose()), (0.2, pose(arm_f=-120, weapon=-100, torso=-8)), (1.3, pose(arm_f=-125, weapon=-105)),
                 (1.42, pose(arm_f=-90, weapon=0, torso=16, lean=8)), (2.0, pose())],
    },
    "backstep": {
        "range": (0, 60), "weight": 2, "cd": 4.0, "phase": (1,), "dur": 1.6, "locks": [0.0, 0.7],
        "motion": [(0.2, 0.42, -70), (0.85, 1.05, ("target", 10, 40, 200))],
        "hits": [rect(0.9, 1.08, 0, 70, 10, 26)],
        "anim": [(0, pose()), (0.3, pose(torso=-10, lean=-4)), (0.8, pose(arm_f=-100, weapon=-50)), (0.95, pose(arm_f=-90, weapon=0, torso=14, lean=8)),
                 (1.6, pose())],
    },
    # phases 2-3, the hollow giant -----------------------------------------------------
    "cleave": {
        "range": (0, 120), "weight": 4, "cd": 1.6, "phase": (2, 3), "dur": 2.0, "locks": [0.0, 0.65],
        "motion": [(0.85, 0.95, 16)],
        "hits": [arc(0.9, 1.04, 104, -100, 100, 40, VOID)],
        "anim": [(0, pose()), (0.7, pose(arm_f=-150, weapon=-60, torso=-12)), (0.92, pose(arm_f=-20, weapon=110, torso=16, lean=4)), (2.0, pose())],
    },
    "crash": {
        "range": (60, 300), "weight": 3, "cd": 4.0, "phase": (2, 3), "dur": 2.6, "locks": [0.0, 0.5], "air": (0.6, 1.3),
        "motion": [(0.6, 1.35, ("target", 0, 40, 260))],
        "hits": [circle(1.35, 1.48, 70, 0, 0, 44, VOID, mark=0.7), ring(1.4, 2.0, 50, 170, 14, 16, VOID), zone(1.45, 6.0, 40, 0, 0, 8, "void")],
        "anim": [(0, pose()), (0.5, pose(dy=4, torso=-10)), (0.95, pose(z=60, arm_f=-170, weapon=0, torso=-14)), (1.35, pose(z=0, arm_f=-30, weapon=110, dy=4)),
                 (2.6, pose())],
    },
    "sweep2": {
        "range": (0, 140), "weight": 3, "cd": 3.0, "phase": (2, 3), "dur": 2.4, "locks": [0.0, 0.6, 1.25],
        "motion": [(0.8, 0.9, 14), (1.45, 1.55, 14)],
        "hits": [arc(0.85, 0.98, 100, -110, 60, 34, VOID), arc(1.5, 1.63, 100, -60, 110, 34, VOID)],
        "anim": [(0, pose()), (0.7, pose(arm_f=-150, weapon=-60)), (0.9, pose(arm_f=-20, weapon=110, torso=12)), (1.35, pose(arm_f=-10, weapon=120)),
                 (1.55, pose(arm_f=-160, weapon=-50, torso=-10)), (2.4, pose())],
    },
    "voidbolts": {
        "range": (100, 500), "weight": 3, "cd": 4.0, "phase": (2, 3), "dur": 1.8, "locks": [0.0, 0.5, 0.9],
        "motion": [],
        "hits": [proj(0.6 + i * 0.25, 0, 20, a, 200, 9, 2.0, 22, VOID) for i, a in enumerate((-10, 10, 0))],
        "anim": [(0, pose()), (0.5, pose(arm_b=-100)), (1.4, pose(arm_b=-100)), (1.8, pose())],
    },
    # phase 3: the sky falls
    "starfall": {
        "range": (0, 600), "weight": 4, "cd": 5.0, "phase": (3,), "dur": 3.0, "locks": [0.0, 0.3, 1.2], "reach": ("target", 0, 0, 400),
        "motion": [],
        "hits": [circle(1.0 + i * 0.18, 1.12 + i * 0.18, 34, s, f, 32, {"col": "#fff0c0"}, mark=0.9, tx=True)
                 for i, (s, f) in enumerate(((0, 0), (-80, 40), (80, 40), (0, -90), (-120, -40), (120, -40), (0, 110), (-60, -120), (60, -120)))],
        "anim": [(0, pose()), (0.4, pose(arm_f=-170, weapon=0, head=-20)), (2.4, pose(arm_f=-170, weapon=0)), (3.0, pose())],
    },
}

PHASE2 = {  # the crown swells him into the hollow giant
    "dur": 3.0, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(1.4, 2.2, 20, 200, 16, 14, {**VOID, "kb": 130}), zone(1.6, 8.0, 46, 0, -150, 8, "void"), zone(1.6, 8.0, 46, 0, 150, 8, "void")],
    "anim": [(0, pose()), (1.0, pose(torso=20, head=20, arm_f=40, arm_b=40, dy=6)), (1.4, pose(torso=-20, head=-26, arm_f=-170, arm_b=-170)), (3.0, pose())],
}
PHASE3 = {  # the roof gives way
    "dur": 2.6, "locks": [0.0], "motion": [], "invuln": True,
    "hits": [ring(1.0, 1.8, 20, 200, 16, 14, {**VOID, "kb": 120}),
             *[circle(1.6 + i * 0.1, 1.72 + i * 0.1, 30, s, f, 24, {"col": "#fff0c0"}, mark=0.7) for i, (s, f) in enumerate(((-160, 120), (160, 120), (-160, -120), (160, -120)))]],
    "anim": [(0, pose()), (0.8, pose(arm_f=-175, arm_b=-175, head=-30, torso=-14)), (2.0, pose(arm_f=-175, arm_b=-175)), (2.6, pose())],
}

BOSS = {
    "id": "king", "name": "The Hollow King", "tier": 4, "rig": "king", "art": "king", "arena": "throne",
    "hp": 4600, "poise": 180, "radius": 18, "speed": 78,
    "moves": MOVES, "phases": [0.66, 0.33], "phase_moves": {2: PHASE2, 3: PHASE3},
    "phase_art": {2: "hollow"}, "phase_rig": {"hollow": "hollow"}, "adds": {},
}
