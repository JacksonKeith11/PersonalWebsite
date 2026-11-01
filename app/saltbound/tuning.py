"""Saltbound's fight numbers, in one place: the code reads them from here, and docs/saltbound.md
explains them. Mostly tuning knobs; change them with the simulator (tools/saltbound-sim.py)."""

SHIELD_BLOCK = 3
DEBUFFS = ("burn", "poison", "weak", "vuln", "mark", "root", "hex")
TICKING = ("weak", "vuln", "mark", "root")
ROUND_ONLY = ("riposte", "thorns")  # hero statuses that clear at the end of the round
ONE_SHOT = ("stun", "freeze", "shock", "hex", "lock", "steal", "static")
UNSTOPPABLE = ("cleave", "earthshaker")
ENRAGE_FROM = 10
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
CURSED_DIE = ["X", 1, 2, 3]

# Cross-hero combos: what two heroes do together (see COMBOS in classes.py for the words).
PINCER = 2      # the first hit on an enemy after an ally hit it this round...
PINCER_MATCH = 3  # ...and this much more if one of your dice shows a number one of theirs showed
COVERED = 3     # your first hit after an ally Guarded or Taunted for you this round
SHATTER = 4     # hitting an enemy an ally Froze breaks the ice
WILDFIRE = 1    # Burn meets an ally's Poison (or the reverse): it erupts for (Burn + Poison) x this
SWALLOW_GUT = 0.15  # the Reef Maw spits a hero out after taking this share of its health
