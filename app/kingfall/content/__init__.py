"""Kingfall's data: bosses, weapons and the heroes' numbers. `client()` is what the browser gets."""

from . import alchemist, bastion, bellwarden, corvin, drake, headsmen, king, mire, mirror, moth, wolf, wyrm
from .weapons import WEAPONS

BOSSES = {b["id"]: b for b in (corvin.BOSS, mire.BOSS, bellwarden.BOSS, headsmen.BOSS, wolf.BOSS, alchemist.BOSS, wyrm.BOSS,
                                     mirror.BOSS, bastion.BOSS, moth.BOSS, king.BOSS, drake.BOSS)}

# A hero's base numbers. Seconds and world pixels.
HERO = {
    "hp": 100, "stamina": 100, "focus": 100, "speed": 92, "radius": 8,
    "st_regen": 55, "st_delay": 0.6,
    "roll": {"dur": 0.42, "dist": 74, "iframes": (0.03, 0.32), "st": 25},
    "flask": {"charges": 3, "dur": 1.0, "at": 0.75, "heal": 0.45, "speed": 0.4},
    "focus_per_dmg": 0.6,
    "down": {"bleed": 15.0, "revive": 2.0, "cost": 0.25, "rise": 0.3},
}

# Boss health and poise by party size (1-4).
SCALE_HP = (1.0, 2.0, 3.0, 4.0)
SCALE_POISE = (1.0, 1.4, 1.8, 2.2)


def client():
    from .upgrades import UPGRADES, VOWS, describe
    from ..build import ATTR_NAMES, ATTR_TEXT
    ups = {u["id"]: {"name": u["name"], "vow": u["vow"], "slot": u["slot"], "pact": u["pact"], "weapon": u["weapon"],
                     "duo": bool(u["needs"]), "text": {r: describe(u["id"], r) for r in ("common", "rare", "epic")}} for u in UPGRADES.values()}
    return {"bosses": BOSSES, "weapons": WEAPONS, "hero": HERO, "upgrades": ups, "vows": VOWS,
            "attrs": [[k, ATTR_NAMES[k], ATTR_TEXT[k]] for k in ATTR_NAMES]}
