"""Skills: abilities on a cooldown that any hero can learn, whatever weapon they hold. A hero carries
at most two (MAX_SKILLS). Each picks one in the lobby to start the run with (START if they don't).
After every fight each hero is offered three they don't know and may learn
one; with two already, the new one replaces whichever they choose.

A skill is played by the browser like a weapon attack (dur, hit, and one of shape / proj / aoe, see
weapons.py) and the server works out its damage: BASE x mult, with the hero's special-damage bonuses.
`pose` picks the casting animation (hero.js, `skillPose`: throw, fan, raise, slam, spin, toss, kneel).
`status`: (kind, amount) built on what it hits. An `aoe` with a `range` lands on what the hero aims at
(the cursor, or the boss they're locked on to), up to that far away; otherwise `at` px ahead.

Every skill asks for a decision (the Nov 2026 rework):
- `instant`: cast on the move, in any state but reeling, without stopping a combo (wards, cries, the step).
- `sub`: {name: {mult, poise, status}}: the skill's further hits, priced on their own (hits say `sub`).
- `trail`: pools left along a shot's path (priced as sub `trail`).
- `clear`: the hit destroys the boss's shots within that many px.
- `counter`: {dmg, poise}: multipliers when it lands on a boss that is mid-attack or winded.
- `walk`: the share of speed kept while it plays (`busy`: it can't be cut short before then); `cdhit`: seconds off its cooldown for each hit landed.
- `blink` (px, untouchable for `iframes` s), `empower` (the next hit's multiplier, within 5 s),
  `recast` (s): pressed again within that long it acts a second time (the step returns you to where you
  left; the knives fly back to your hand).
- `zone`: {r, secs, ...}: a circle left on the ground. `rally`: heroes inside deal that much more;
  `heal`: share of the caster's health healed over its life to whoever stands in it (every `every` s);
  `vuln`: a boss inside takes that much more from everyone. It lies where the hero stands, or where
  the skill's area lands (`at: "aoe"`: the browser says where).
- `guard` (s): for that long the next hit is soaked whole (not a room-wide blast), and the hero answers
  with sub `burst` (`burst_r` px round them); `refund`: the share of the cooldown given back for it.
- `stick` (s): its shots stay where they land for that long (for the recast).
- `leap`: it carries the hero up to that far toward what they aim at, in the `air` (untouchable).
- `brk`: its damage counts this many times over against a break bar.
- `dashes` (all refilled), `free` (s of dashes that cost nothing), `perfect_focus` (Focus for each hit
  dodged through in that time).
- `live`: seconds its hits still count after it's used (default SKILL_LIVE in fight.py).
- `brand`: {secs, frac}: its hit brands the body; after `secs` it is struck for `frac` of the damage it took meanwhile.
- an `aoe` with `clear` shatters boss shots inside it at every tick (a wall); with `trap` (s) it lies armed
  that long and goes off when a boss steps into it; `wave`: {n, gap, step}: that many more of the same area,
  each `gap` px further along the aim and `step` s later.
- `cost`: health spent to use it (never the last point); `focus`: Focus gained.
- `trance`: {secs, speed, dmg, taken}: for that long lights play `speed` faster and the hero deals `dmg` more,
  and takes `taken` times the damage.
- `counter.refund`: the share of its cooldown given back when it lands on a boss mid-attack or winded.
- `execute`: {below, dmg}: x `dmg` against a body under that share of its health.
"""

START = "lance"   # the skill a hero starts a run with unless they choose another
BASE = 20         # a skill's damage is BASE x mult: the same whatever weapon you hold
MAX_SKILLS = 2

SKILLS = {s["id"]: s for s in [
    {"id": "lance", "name": "Ember Lance", "cd": 8, "col": "#ff8a3a", "pose": "throw",
     "text": "Hurl a lance of fire that pierces everything and leaves its path burning for 3 s. Builds Burn.",
     "dur": 0.45, "hit": (0.16, 0.17), "proj": {"v": 430, "r": 8, "life": 1.0, "pierce": True, "col": "#ff8a3a"},
     "mult": 3.0, "poise": 20, "status": ("burn", 40),
     "trail": {"n": 5, "from": 40, "gap": 54, "r": 22, "delay": 0.25, "ticks": 6, "every": 0.5},
     "sub": {"trail": {"mult": 0.22, "poise": 1, "status": ("burn", 8)}}},
    {"id": "nova", "name": "Frost Nova", "cd": 12, "col": "#7fe3ff", "pose": "raise",
     "text": "A ring of ice bursts out around you: it shatters the boss's shots, builds Frost, and breaks twice the poise if the boss is mid-attack.",
     "dur": 0.5, "hit": (0.16, 0.28), "shape": {"k": "circle", "r": 72, "x": 0, "y": 0}, "mult": 2.2, "poise": 35, "status": ("frost", 60),
     "clear": 76, "counter": {"poise": 2.0}},
    {"id": "smite", "name": "Judgement", "cd": 12, "col": "#ffe08a", "pose": "raise",
     "text": "Call a pillar of light down where you aim. It lands a moment later: half as hard again on a boss that is mid-attack or winded.",
     "dur": 0.45, "hit": (0.18, 0.19), "aoe": {"at": 110, "range": 220, "r": 44, "delay": 0.55, "ticks": 1, "every": 0.2}, "mult": 4.0, "poise": 40,
     "counter": {"dmg": 1.5}},
    {"id": "whirl", "name": "Reaping Whirl", "cd": 9, "col": "#d8dce4", "pose": "spin",
     "text": "Spin, striking all round you three times as you walk. Each strike that lands brings it back a second sooner.",
     "dur": 0.56, "hit": (0.06, 0.07), "aoe": {"at": 0, "r": 58, "delay": 0.02, "ticks": 3, "every": 0.16, "carry": 1}, "mult": 1.3, "poise": 12,
     "walk": 0.7, "cdhit": 1.0, "busy": 0.4},
    {"id": "step", "name": "Phase Step", "cd": 8, "col": "#c8b4ff", "pose": "cast", "instant": True,
     "text": "Blink the way you're moving, untouchable. Your next hit deals 60% more. Press again within 3 s to return to where you left.",
     "dur": 0.28, "blink": 120, "iframes": 0.28, "empower": 1.6, "recast": 3.0},
    {"id": "rally", "name": "Rallying Cry", "cd": 22, "col": "#ffb040", "pose": "raise", "instant": True,
     "text": "Plant a banner for 8 s: heroes standing in its circle deal 30% more.",
     "dur": 0.3, "zone": {"r": 105, "secs": 8, "rally": 1.3}},
    {"id": "mend", "name": "Litany of Mending", "cd": 30, "col": "#8be04e", "pose": "kneel",
     "text": "Hallow the ground where you stand for 4 s: heroes who stay in the circle are healed a quarter of your health.",
     "dur": 0.4, "zone": {"r": 78, "secs": 4, "heal": 0.25, "every": 0.5}},
    {"id": "ward", "name": "Stone Ward", "cd": 20, "col": "#a8b0bc", "pose": "cast", "instant": True,
     "text": "Turn to stone for 1.2 s. A hit taken in that time is soaked whole and answered with a burst that breaks poise, and half the cooldown comes back.",
     "dur": 0.3, "guard": 1.2, "refund": 0.5, "burst_r": 64, "sub": {"burst": {"mult": 2.0, "poise": 50}}},
    {"id": "knives", "name": "Fan of Knives", "cd": 8, "col": "#e04a5a", "pose": "fan",
     "text": "Throw five knives in a fan, each building Bleed. They stay where they land: press again within 5 s to call them back through whatever is in the way.",
     "dur": 0.36, "hit": (0.12, 0.13), "proj": {"v": 400, "r": 4, "life": 0.5, "n": 5, "spread": 11, "col": "#e04a5a"}, "mult": 0.8, "poise": 6,
     "status": ("bleed", 14), "stick": 5.0, "recast": 5.0, "live": 12.0, "sub": {"back": {"mult": 0.8, "poise": 6, "status": ("bleed", 14)}}},
    {"id": "censer", "name": "Plague Censer", "cd": 16, "col": "#8be04e", "pose": "toss",
     "text": "Throw a censer where you aim: its cloud eats at what stands in it for 3 s, builds Rot, and a boss inside it takes 15% more from everyone.",
     "dur": 0.45, "hit": (0.18, 0.19), "aoe": {"at": 100, "range": 200, "r": 50, "delay": 0.3, "ticks": 6, "every": 0.5}, "mult": 0.6, "poise": 4,
     "status": ("rot", 22), "zone": {"r": 50, "secs": 3.3, "vuln": 1.15, "at": "aoe"}},
    {"id": "hammer", "name": "Hammerfall", "cd": 11, "col": "#ffd23f", "pose": "slam",
     "text": "Leap to where you aim, untouchable in the air, and bring a hammer of light down: the most poise damage of any skill, and double against a break bar.",
     "dur": 0.66, "hit": (0.32, 0.42), "shape": {"k": "circle", "r": 44, "x": 12, "y": 0}, "mult": 1.8, "poise": 75,
     "leap": 140, "air": (0.03, 0.3), "brk": 2.0},
    {"id": "breath", "name": "Second Breath", "cd": 24, "col": "#e8ecf2", "pose": "raise", "instant": True,
     "text": "Every dash comes back at once, and for 4 s dashes cost nothing and each hit you dodge through gives 20 Focus.",
     "dur": 0.3, "dashes": 1, "free": 4.0, "perfect_focus": 20},
    # ---- eight more (Nov 2026)
    {"id": "brand", "name": "Storm Brand", "cd": 14, "col": "#c8b4ff", "pose": "cast",
     "text": "Brand the boss with a touch of lightning. 4 s later it is struck for 35% of all the damage it took meanwhile.",
     "dur": 0.4, "hit": (0.12, 0.2), "shape": {"k": "arc", "r": 56, "a0": -50, "a1": 50}, "mult": 0.8, "poise": 8, "brand": {"secs": 4.0, "frac": 0.35}},
    {"id": "wall", "name": "Rime Wall", "cd": 16, "col": "#7fe3ff", "pose": "raise",
     "text": "Raise a wall of frost where you aim for 4 s: the boss's shots that touch it shatter, and it chills what stands in it.",
     "dur": 0.4, "hit": (0.14, 0.15), "aoe": {"at": 60, "range": 160, "r": 46, "delay": 0.1, "ticks": 16, "every": 0.25, "clear": 1}, "mult": 0.15, "poise": 2,
     "status": ("frost", 6), "live": 6.0},
    {"id": "pact", "name": "Blood Pact", "cd": 18, "col": "#c83a4a", "pose": "cast", "instant": True,
     "text": "Spend 15 health for 60 Focus, and your next hit within 5 s deals 40% more.",
     "dur": 0.3, "cost": 15, "focus": 60, "empower": 1.4},
    {"id": "quake", "name": "Stonebreaker", "cd": 10, "col": "#d8b070", "pose": "slam",
     "text": "Strike the ground: five eruptions march away along your aim, one after another, each breaking poise.",
     "dur": 0.5, "hit": (0.2, 0.21), "aoe": {"at": 36, "r": 26, "delay": 0.05, "ticks": 1, "every": 0.2, "boom": 1}, "wave": {"n": 4, "gap": 48, "step": 0.11},
     "mult": 1.5, "poise": 30},
    {"id": "trance", "name": "Battle Trance", "cd": 22, "col": "#ff6a3a", "pose": "raise", "instant": True,
     "text": "For 6 s your light attacks are 30% faster and you deal 15% more, but every hit you take hurts 30% more.",
     "dur": 0.3, "trance": {"secs": 6, "speed": 1.3, "dmg": 1.15, "taken": 1.3}},
    {"id": "bolt", "name": "Storm Bolt", "cd": 7, "col": "#c8b4ff", "pose": "throw",
     "text": "A fast bolt of lightning. Strike a boss that is mid-attack or winded and half its cooldown comes back at once.",
     "dur": 0.36, "hit": (0.1, 0.11), "proj": {"v": 620, "r": 6, "life": 0.5, "col": "#c8b4ff"}, "mult": 2.0, "poise": 14, "counter": {"dmg": 1.0, "refund": 0.5}},
    {"id": "execute", "name": "Deathblow", "cd": 13, "col": "#e8ecf2", "pose": "slam",
     "text": "A heavy blow straight ahead. Against a boss below 30% of its health it deals double.",
     "dur": 0.55, "hit": (0.2, 0.3), "shape": {"k": "rect", "x0": 0, "x1": 64, "w": 14}, "mult": 2.6, "poise": 36, "step": 14, "execute": {"below": 0.3, "dmg": 2.0}},
    {"id": "trap", "name": "Rune Trap", "cd": 12, "col": "#ffd23f", "pose": "kneel",
     "text": "Set a rune at your feet. It waits 12 s for the boss to step on it, then bursts, breaking a great deal of poise.",
     "dur": 0.3, "hit": (0.12, 0.13), "aoe": {"at": 0, "r": 40, "delay": 0.4, "ticks": 1, "every": 0.2, "boom": 1, "trap": 12.0}, "mult": 3.4, "poise": 45, "live": 14.0},
]}


def offer(known, rng, n=3, avoid=()):
    """n skills this hero doesn't know yet, leaving out `avoid` (the ones a reroll replaces) while others remain."""
    pool = [s for s in SKILLS if s not in known]
    rng.shuffle(pool)
    pool.sort(key=lambda s: s in avoid)  # stable: the avoided ones go last
    return pool[:n]
