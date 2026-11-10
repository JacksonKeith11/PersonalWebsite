"""Kingfall's data: bosses, weapons and the heroes' numbers. `client()` is what the browser gets."""

from . import alchemist, bastion, bellwarden, corvin, drake, headsmen, king, mire, mirror, moth, wolf, wyrm
from .weapons import WEAPONS

BOSSES = {b["id"]: b for b in (corvin.BOSS, mire.BOSS, bellwarden.BOSS, headsmen.BOSS, wolf.BOSS, alchemist.BOSS, wyrm.BOSS,
                                     mirror.BOSS, bastion.BOSS, moth.BOSS, king.BOSS, drake.BOSS)}

# A hero's base numbers. Seconds and world pixels.
HERO = {
    "hp": 100, "stamina": 100, "focus": 100, "speed": 116, "radius": 8,
    "st_regen": 55, "st_delay": 0.6,
    # The roll starts fast and eases into a run (hero.js, `rollSpeed`), can be steered (`turn` degrees a
    # second toward the stick) and takes a queued attack or another roll the moment it ends.
    "roll": {"dur": 0.38, "dist": 92, "iframes": (0.02, 0.29), "st": 22, "turn": 200},
    "flask": {"charges": 3, "dur": 1.0, "at": 0.75, "heal": 0.45, "speed": 0.4},
    "focus_per_dmg": 0.6,
    # A parry is timed from the press of block, not from when the guard comes up. Pressing block again
    # within `spam` s of the last press shrinks the window to the next share in `shrink` (none at all
    # from the fourth quick press); it is whole again after `spam` s without a press. Blocking still works.
    "parry": {"spam": 0.5, "shrink": (1.0, 0.5, 0.25, 0.0)},
    "down": {"bleed": 15.0, "revive": 2.0, "cost": 0.25, "rise": 0.3},
}

# Boss health and poise by party size (1-4).
SCALE_HP = (1.05, 2.05, 3.1, 4.1)
SCALE_POISE = (1.0, 1.4, 1.8, 2.2)


def client():
    from .upgrades import UPGRADES, VOWS, describe
    from ..build import ATTR_NAMES, ATTR_TEXT
    ups = {u["id"]: {"name": u["name"], "vow": u["vow"], "slot": u["slot"], "pact": u["pact"], "weapon": u["weapon"],
                     "duo": bool(u["needs"]), "text": {r: describe(u["id"], r) for r in ("common", "rare", "epic")}} for u in UPGRADES.values()}
    from .skills import SKILLS, MAX_SKILLS
    return {"bosses": BOSSES, "weapons": WEAPONS, "hero": HERO, "upgrades": ups, "vows": VOWS, "skills": SKILLS, "max_skills": MAX_SKILLS,
            "attrs": [[k, ATTR_NAMES[k], ATTR_TEXT[k]] for k in ATTR_NAMES]}
