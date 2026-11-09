"""The heroes' weapons. Each has a light combo, a charged heavy, a special (costs Focus) and its own
defensive move. The browser plays them (timing, animation, hit checks against the boss); the server
works out the damage from these numbers and the hero's build.

Per attack: dur (s), hit (t0, t1) when it can land, shape (as the bosses', in the aim's frame), mult
(of the weapon's base damage), poise, st (stamina), step (px lunge), next (from when the next attack
may be queued), anim keyframes.
"""

from .moves import pose

SWORD = {
    "id": "sword", "name": "Sword & Shield", "art": "sword", "base": 22, "blurb": "All-rounder. Block, parry and riposte.",
    "light": [
        {"dur": 0.36, "hit": (0.09, 0.17), "shape": {"k": "arc", "r": 42, "a0": -65, "a1": 65}, "mult": 1.0, "poise": 10, "st": 12,
         "step": 8, "next": 0.2,
         "anim": [(0, pose(arm_f=-150, weapon=40, torso=-6)), (0.1, pose(arm_f=-30, weapon=100, torso=8, lean=2)), (0.36, pose(arm_f=-20, weapon=70))]},
        {"dur": 0.36, "hit": (0.09, 0.17), "shape": {"k": "arc", "r": 42, "a0": -65, "a1": 65}, "mult": 1.0, "poise": 10, "st": 12,
         "step": 8, "next": 0.2,
         "anim": [(0, pose(arm_f=-20, weapon=100, torso=8)), (0.1, pose(arm_f=-140, weapon=-60, torso=-6, lean=2)), (0.36, pose(arm_f=-120, weapon=-40))]},
        {"dur": 0.5, "hit": (0.14, 0.22), "shape": {"k": "rect", "x0": 0, "x1": 52, "w": 10}, "mult": 1.4, "poise": 18, "st": 16,
         "step": 16, "next": 0.36,
         "anim": [(0, pose(arm_f=-100, weapon=-80, torso=-10, lean=-2)), (0.14, pose(arm_f=-90, weapon=0, torso=12, lean=5)), (0.5, pose(arm_f=-80, weapon=10))]},
    ],
    "heavy": {"charge": 0.8, "dur": 0.55, "hit": (0.08, 0.16), "shape": {"k": "arc", "r": 50, "a0": -50, "a1": 50},
              "mult": (2.0, 3.0), "poise": (32, 55), "st": 30, "step": 14,
              "hold": pose(arm_f=-175, weapon=-10, torso=-12, head=-6),
              "anim": [(0, pose(arm_f=-175, weapon=-10, torso=-12)), (0.08, pose(arm_f=-40, weapon=110, torso=14, lean=5)), (0.55, pose(arm_f=-30, weapon=90))]},
    "special": {"name": "Shield Bash", "focus": 35, "dur": 0.5, "hit": (0.12, 0.22), "shape": {"k": "circle", "r": 22, "x": 20, "y": 0},
                "mult": 0.6, "poise": 50, "step": 22,
                "anim": [(0, pose(arm_b=-60, shield=60, front=1, torso=-8)), (0.12, pose(arm_b=-95, shield=95, front=1, torso=12, lean=6)), (0.5, pose(arm_b=-60, shield=60, front=1))]},
    # hold to block hits from the front (stamina pays for them); the first moments are a parry
    "guard": {"kind": "block", "arc": 80, "parry": 0.18, "st_per_dmg": 1.0, "speed": 0.45,
              "anim": pose(arm_b=-70, shield=70, front=1, torso=-4)},
    "offhand": "shield",
}

WEAPONS = {"sword": SWORD}
