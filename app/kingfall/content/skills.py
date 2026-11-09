"""Skills: abilities on a cooldown that any hero can learn, whatever weapon they hold. A hero carries
at most two (MAX_SKILLS). After every fight each hero is offered three they don't know and may learn
one; with two already, the new one replaces whichever they choose.

A skill is played by the browser like a weapon attack (dur, hit, and one of shape / proj / aoe, see
weapons.py) and the server works out its damage: BASE x mult, with the hero's special-damage bonuses.
`pose` picks the casting animation ("cast": a hand thrust forward; "raise": both arms up). Skills
without a hit act the moment they're used: `blink` (px, untouchable for `iframes` s), `empower` (the
next hit's multiplier), `rally` (damage multiplier for `secs`, to allies within `radius` too), `heal`
(share of max health, allies within `radius` too), `ward` (damage soaked). `status`: (kind, amount)
built on what it hits.
"""

BASE = 20         # a skill's damage is BASE x mult: the same whatever weapon you hold
MAX_SKILLS = 2

SKILLS = {s["id"]: s for s in [
    {"id": "lance", "name": "Ember Lance", "cd": 8, "col": "#ff8a3a", "pose": "cast",
     "text": "Hurl a lance of fire that pierces everything in its path and builds Burn.",
     "dur": 0.45, "hit": (0.16, 0.17), "proj": {"v": 430, "r": 8, "life": 1.0, "pierce": True, "col": "#ff8a3a"},
     "mult": 3.2, "poise": 30, "status": ("burn", 45)},
    {"id": "nova", "name": "Frost Nova", "cd": 12, "col": "#7fe3ff", "pose": "raise",
     "text": "A ring of ice bursts out around you, building Frost and breaking poise.",
     "dur": 0.55, "hit": (0.18, 0.3), "shape": {"k": "circle", "r": 72, "x": 0, "y": 0},
     "mult": 2.2, "poise": 50, "status": ("frost", 60)},
    {"id": "smite", "name": "Judgement", "cd": 12, "col": "#ffe680", "pose": "raise",
     "text": "Call a pillar of light down where you aim. It lands after a moment and hits very hard.",
     "dur": 0.5, "hit": (0.2, 0.21), "aoe": {"at": 110, "r": 44, "delay": 0.55, "ticks": 1, "every": 0.2},
     "mult": 4.5, "poise": 60},
    {"id": "whirl", "name": "Reaping Whirl", "cd": 9, "col": "#e8ecf2", "pose": "raise",
     "text": "Spin, striking everything around you three times.",
     "dur": 0.6, "hit": (0.08, 0.09), "aoe": {"at": 0, "r": 58, "delay": 0.02, "ticks": 3, "every": 0.16},
     "mult": 1.3, "poise": 16},
    {"id": "step", "name": "Phase Step", "cd": 8, "col": "#c8b4ff", "pose": "cast",
     "text": "Vanish and reappear a long stride away, untouchable as you go. Your next hit deals 60% more.",
     "dur": 0.28, "blink": 120, "iframes": 0.28, "empower": 1.6},
    {"id": "rally", "name": "Rallying Cry", "cd": 22, "col": "#ffb040", "pose": "raise",
     "text": "You and allies near you deal 30% more damage for 6 seconds.",
     "dur": 0.5, "rally": 1.3, "secs": 6, "radius": 150},
    {"id": "mend", "name": "Litany of Mending", "cd": 30, "col": "#8be04e", "pose": "raise",
     "text": "Heal yourself and allies near you for a fifth of your health.",
     "dur": 0.7, "heal": 0.2, "radius": 120},
    {"id": "ward", "name": "Stone Ward", "cd": 20, "col": "#a8b0bc", "pose": "raise",
     "text": "A ward of stone soaks the next 45 damage you take.",
     "dur": 0.4, "ward": 45},
]}


def offer(known, rng, n=3):
    """n skills this hero doesn't know yet."""
    pool = [s for s in SKILLS if s not in known]
    rng.shuffle(pool)
    return pool[:n]
