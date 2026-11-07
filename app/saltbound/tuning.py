"""Saltbound's fight numbers, in one place: the code reads them from here, and docs/saltbound.md
explains them. Mostly tuning knobs; change them with the simulator (tools/saltbound-sim.py)."""

SHIELD_BLOCK = 3
DEBUFFS = ("burn", "poison", "weak", "vuln", "mark", "root", "hex")
TICKING = ("weak", "vuln", "mark", "root")
ROUND_ONLY = ("cocked", "riposte", "thorns", "glyphward", "emberward", "kindled", "wingguard", "kshield", "counter", "chill")  # hero statuses that clear at the end of the round
ONE_SHOT = ("stun", "freeze", "shock", "hex", "lock", "steal", "static")
UNSTOPPABLE = ("cleave", "earthshaker")
ENRAGE_FROM = 10
# Objectives scale with the party: each one cleared makes the dungeons still standing harder, on top of
# the 15% health and 10% damage every enemy gains per objective cleared. Index = objectives cleared.
DUNGEON_STEP_HP = (0.85, 1.0, 1.15)
DUNGEON_STEP_DMG = (0.9, 1.0, 1.1)
# The rising tide: each rise makes every enemy this share stronger, HP and damage (rises come every
# few turns, by difficulty; see DIFFICULTY in game.py).
SURGE = 0.0065  # was 0.0045, then 0.0055 (owner, Nov 2026: a stronger rising tide)
# Enemies met on the map (roaming groups and lairs) last longer but hit softer, so those fights
# take a few rounds without being deadlier. Elites and big threats are meant to be dangerous: no change.
ROAM_HP = 2.2
ROAM_DMG = 0.65
# Event fights: whoever is on or next to the hex joins; a hero alone meets weaker enemies.
EVENT_DMG = 0.7
EVENT_HP = {1: 0.9, 2: 1.4, 3: 1.9}
# The Drowned Crown: warded while a Tide Guard stands (phase 1), drags one hero under each round
# (the Undertow, phases 2 and 3: Armor or a Guard stops it), and alone it's exposed and furious.
CROWN_WARD = 0.5
CROWN_EXPOSED = 1.5
UNDERTOW = 3    # times the fight's damage multiplier
BELL_CRACK = 6  # hitting the Bell-Warden with a die showing its bell number
LAMP_DOUSE = 3  # different heroes hitting the Lamp Keeper in one round put its lamp out
KNELL_EVERY = 3    # the Bell-Warden's Death Knell comes every this many rounds...
KNELL_REQUIEM = 2  # ...and this often once it's bloodied
KEG_BLAST = 6      # a Powder Keg a hero breaks hits every enemy for this (times the difficulty's enemy HP)
CURSED_DIE = ["X", 1, 2, 3]

# Cross-hero combos: what two heroes do together (see COMBOS in classes.py for the words).
PINCER = 2      # the first hit on an enemy after an ally hit it this round...
PINCER_MATCH = 3  # ...and this much more if one of your dice shows a number one of theirs showed
COVERED = 3     # your first hit after an ally Guarded or Taunted for you this round
SHATTER = 4     # hitting an enemy an ally Froze breaks the ice
WILDFIRE = 1    # Burn meets an ally's Poison (or the reverse): it erupts for (Burn + Poison) x this
SWALLOW_GUT = 0.15  # the Reef Maw spits a hero out after taking this share of its health

# Passives that change what a die can show while planning (the bots' odds cache and the browser's
# hit chances need them): Sleight of Hand, Bulwark Faces, Weighted Coin, Keen Edge.
# The Swell die (a level-up pick): it starts each fight small and grows a step each round it goes
# unused, back to the start once used. (faces, flat bonus) per step. Each step pays better per round
# waited than spending it every round: a d4 is 2.5 a round; d10+2 after one round waited is 3.75 a
# round over the two; d12+7 after two, 4.5; d20+12 after three, 5.6. So holding it is the play, and
# the choice is when to cash it in.
SWELL = ((4, 0), (10, 2), (12, 7), (20, 12))
# The Echo die (a level-up pick): until an ally uses a die this round it's this size; after, it
# shows the biggest number of that ally's last play.
ECHO_FACES = 8

ROLL_MODS = ("sleight", "shield_top", "one_is_top", "keen_edge", "skull_top")

# Aim and Loose (the bows' weapon action): +2 for each round it waited ready and unused, up to this many.
AIM_CAP = 3
