"""The hero classes, their actions and passives.

Classes are generic: nothing here may mention the sea, tides or skiffs, so they carry over to future
maps. A class's map ability is a key the game checks at its hooks (`on_move_cost`, `on_reveal`,
`on_loot`, `on_rest`, `on_shop`, `on_event`, `on_combat_start`).

An action is a card with dice slots:
- `req`: what dice it takes. `n` dice (0 for a free action), and any of `min`, `max`, `exact`,
  `odd`, `even` (each die), `pair`, `straight`, `sum_min` (the set), `face: "S"` (a shield face),
  `upto: True` (1..n dice).
- `tgt`: `foe`, `ally`, `other` (an ally but not yourself), `downed`, `self`, `foes`, `front`,
  `party`.
- `ops`: what it does, in order. Amounts are expressions over `v` (the first die), `sum`, `n`,
  `armor` (yours), `missing` (your missing HP) and `undead` (1 if the target is).
- `melee`: you must be in the front row, and it hits the front row while there is one.
- `spell`: counts for Spell Echo. `once`: once per fight.

Learning an action you already have upgrades it (`strike+`): +2 to every amount and +1 to every
status that stacks (Burn, Poison, Sanctuary).
"""

ACTIONS = {
    # ---- for everyone
    "shift": {"name": "Shift", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "shift"}],
              "text": "Change rows."},
    "flee": {"name": "Flee", "req": {"n": 1, "min": 4}, "tgt": "self", "ops": [{"op": "flee"}],
             "text": "Run back the way you came. Not in dungeons or against bosses."},

    # ---- Vanguard
    "strike": {"name": "Strike", "req": {"n": 1}, "tgt": "foe", "melee": True,
               "ops": [{"op": "dmg", "amt": "v"}], "text": "Deal the die's value."},
    "guard": {"name": "Guard", "req": {"n": 1}, "tgt": "other",
              "ops": [{"op": "guard"}, {"op": "armor", "amt": "v", "to": "self"}],
              "text": "The next hit on an ally hits you instead. Gain Armor equal to the die."},
    "taunt": {"name": "Taunt", "req": {"n": 1, "min": 3}, "tgt": "self", "ops": [{"op": "taunt"}],
              "tags": ["bulwark"], "text": "Every enemy attack this round comes at you."},
    "brace": {"name": "Brace", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v*2"}],
              "tags": ["bulwark"], "text": "Gain Armor equal to twice the die."},
    "rally_wall": {"name": "Rally Wall", "req": {"n": 2, "pair": True}, "tgt": "self",
                   "ops": [{"op": "armor", "amt": "4", "to": "myrow"}], "tags": ["bulwark"],
                   "text": "Everyone in your row gains 4 Armor."},
    "shield_bash": {"name": "Shield Bash", "req": {"n": 1, "face": "S"}, "tgt": "foe", "melee": True,
                    "ops": [{"op": "dmg", "amt": "3"}, {"op": "status", "s": "stun", "n": 1}],
                    "tags": ["juggernaut"], "text": "Deal 3 and Stun."},
    "retaliate": {"name": "Retaliate", "req": {"n": 1, "min": 4}, "tgt": "foe", "melee": True,
                  "ops": [{"op": "dmg", "amt": "armor"}], "tags": ["juggernaut"],
                  "text": "Deal damage equal to your Armor."},
    "shoulder_charge": {"name": "Shoulder Charge", "req": {"n": 1, "min": 5}, "tgt": "foe",
                        "ops": [{"op": "dmg", "amt": "v"}, {"op": "drag"}], "tags": ["juggernaut"],
                        "text": "Hit any enemy and drag it to the front row."},

    # ---- Arcanist
    "bolt": {"name": "Bolt", "req": {"n": 1}, "tgt": "foe", "spell": True,
             "ops": [{"op": "dmg", "amt": "v"}], "text": "Deal the die's value."},
    "channel": {"name": "Channel", "req": {"n": 2}, "tgt": "foe", "spell": True,
                "ops": [{"op": "dmg", "amt": "sum-2"}], "text": "Deal the sum of two dice, minus 2."},
    "fireball": {"name": "Fireball", "req": {"n": 2, "sum_min": 10}, "tgt": "foes", "spell": True,
                 "ops": [{"op": "dmg", "amt": "sum//2"}, {"op": "status", "s": "burn", "n": 2}],
                 "tags": ["elementalist"], "text": "Half the sum to every enemy, and Burn 2."},
    "frost_lance": {"name": "Frost Lance", "req": {"n": 1, "min": 5}, "tgt": "foe", "spell": True,
                    "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "freeze", "n": 1}],
                    "tags": ["elementalist"], "text": "Deal the die's value and Freeze."},
    "chain_lightning": {"name": "Chain Lightning", "req": {"n": 1, "odd": True}, "tgt": "foe", "spell": True,
                        "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "shock", "n": 1}],
                        "tags": ["elementalist"], "text": "Deal the die's value and Shock."},
    "hex": {"name": "Hex", "req": {"n": 1}, "tgt": "foe", "spell": True,
            "ops": [{"op": "status", "s": "weak", "n": 1}, {"op": "status", "s": "vuln", "n": 1}],
            "tags": ["hexer"], "text": "Weak and Vulnerable."},
    "siphon": {"name": "Siphon", "req": {"n": 1, "min": 4}, "tgt": "foe", "spell": True,
               "ops": [{"op": "dmg", "amt": "v", "leech": 0.5}], "tags": ["hexer"],
               "text": "Deal the die's value and heal half of it."},
    "doom": {"name": "Doom", "req": {"n": 1, "exact": 1}, "tgt": "foe", "spell": True,
             "ops": [{"op": "status", "s": "doom", "n": 20}], "tags": ["hexer"],
             "text": "The target takes 20 at the end of next round."},

    # ---- Mender
    "mend": {"name": "Mend", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "heal", "amt": "v+2"}],
             "text": "Heal an ally the die's value +2."},
    "lift": {"name": "Lift", "req": {"n": 1}, "tgt": "downed", "ops": [{"op": "lift", "amt": "v*2"}],
             "text": "Pick up a knocked-down ally with HP equal to twice the die."},
    "renew": {"name": "Renew", "req": {"n": 2, "pair": True}, "tgt": "party", "ops": [{"op": "heal", "amt": "sum"}],
              "tags": ["restoration"], "text": "Heal the whole party the sum."},
    "lifeline": {"name": "Lifeline", "req": {"n": 1, "exact": 6}, "tgt": "ally",
                 "ops": [{"op": "status", "s": "lifeline", "n": 1}], "tags": ["restoration"],
                 "text": "The ally heals fully at the end of the round."},
    "ward": {"name": "Ward", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "armor", "amt": "v*2"}],
             "tags": ["warding"], "text": "An ally gains Armor equal to twice the die."},
    "sanctuary": {"name": "Sanctuary", "req": {"n": 1, "min": 5}, "tgt": "party",
                  "ops": [{"op": "sanct", "n": 3}], "tags": ["warding"],
                  "text": "Every hit on the party deals 3 less this round."},
    "cleanse": {"name": "Cleanse", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "cleanse"}, {"op": "heal", "amt": "2"}],
                "text": "Remove an ally's Burn, Poison, Weak, Vulnerable, Mark and Root, and heal 2."},
    "smite": {"name": "Smite", "req": {"n": 1, "min": 4}, "tgt": "foe", "ops": [{"op": "dmg", "amt": "v+3*undead"}],
              "text": "Deal the die's value, +3 against the undead."},
    "quick_lift": {"name": "Quick Lift", "req": {"n": 0}, "tgt": "downed", "once": True,
                   "ops": [{"op": "lift", "amt": "8"}], "text": "Once per fight, no die: pick up an ally with 8 HP."},
}

# A passive's `mods` are read by the game where they apply. `override` replaces parts of an action.
PASSIVES = {
    # ---- Vanguard
    "thick_hide": {"name": "Thick Hide", "mods": {"max_hp": 6}, "text": "+6 max HP."},
    "iron_will": {"name": "Iron Will", "mods": {"stun_ward": 1}, "text": "Ignore the first Stun each fight."},
    "steady": {"name": "Steady", "mods": {"shield_block": 1}, "tags": ["bulwark"], "text": "Shield faces block 4."},
    "spiked_plate": {"name": "Spiked Plate", "mods": {"thorns": 2}, "tags": ["juggernaut"],
                     "text": "Attackers take 2."},
    "overguard": {"name": "Overguard", "mods": {"overguard": 1}, "tags": ["bulwark"],
                  "text": "Half your Armor carries into the next round."},
    "last_stand": {"name": "Last Stand", "mods": {"last_stand": 5}, "text": "At 25% HP or less, gain 5 Armor each round."},
    "unbreakable": {"name": "Unbreakable", "cap": True, "mods": {"unbreakable": 1}, "tags": ["bulwark"],
                    "text": "Once per fight, survive a lethal hit at 1 HP."},
    "avalanche": {"name": "Avalanche", "cap": True, "mods": {"override": {"retaliate": {"tgt": "front"}}},
                  "tags": ["juggernaut"], "text": "Retaliate hits the whole front row."},

    # ---- Arcanist
    "overcharge": {"name": "Overcharge", "mods": {"overcharge": 1}, "text": "A d12 that rolls 12 rolls again and adds it."},
    "kindling": {"name": "Kindling", "mods": {"burn_bonus": 1}, "tags": ["elementalist"], "text": "Your Burns tick 1 harder."},
    "cold_snap": {"name": "Cold Snap", "mods": {"frozen_bonus": 3}, "tags": ["elementalist"],
                  "text": "Frozen targets take +3 from you."},
    "malediction": {"name": "Malediction", "mods": {"debuff_ext": 1}, "tags": ["hexer"],
                    "text": "Your Weak, Vulnerable and Mark last a round longer."},
    "arcane_shield": {"name": "Arcane Shield", "mods": {"start_armor": 6}, "text": "Start each fight with 6 Armor."},
    "spell_echo": {"name": "Spell Echo", "mods": {"spell_echo": 1},
                   "text": "Your first spell each fight casts twice, the second at half strength."},
    "cataclysm": {"name": "Cataclysm", "cap": True, "tags": ["elementalist"],
                  "mods": {"override": {"fireball": {"ops": [{"op": "dmg", "amt": "sum"}, {"op": "status", "s": "burn", "n": 2}]}}},
                  "text": "Fireball hits every enemy for the full sum."},
    "grand_curse": {"name": "Grand Curse", "cap": True, "tags": ["hexer"], "mods": {"override": {"hex": {"tgt": "foes"}}},
                    "text": "Hex hits every enemy."},

    # ---- Mender
    "bedside_manner": {"name": "Bedside Manner", "mods": {"heal_bonus": 2}, "tags": ["restoration"],
                       "text": "+2 to all your heals."},
    "overflow": {"name": "Overflow", "mods": {"overflow": 1}, "tags": ["warding"], "text": "Your overhealing becomes Armor."},
    "quick_hands": {"name": "Quick Hands", "mods": {"grant": "quick_lift"}, "tags": ["restoration"],
                    "text": "Learn Quick Lift: once per fight, pick up an ally without a die."},
    "blessed_supplies": {"name": "Blessed Supplies", "mods": {"potion_bonus": 0.5}, "text": "Potions you use heal 50% more."},
    "aura": {"name": "Aura", "mods": {"regen": 1}, "tags": ["warding"], "text": "The party regenerates 1 HP a round in your fights."},
    "calm": {"name": "Calm", "mods": {"freeze_immune": 1}, "text": "Your dice can't be Frozen."},
    "miracle": {"name": "Miracle", "cap": True, "mods": {"miracle": 1}, "tags": ["restoration"],
                "text": "Once per run, a revive that would be spent isn't."},
    "aegis": {"name": "Aegis", "cap": True, "mods": {"aegis": 2}, "tags": ["warding"],
              "text": "Once you cast Sanctuary, every hit on the party deals 2 less for the rest of the fight."},
}

D = lambda n: list(range(1, n + 1))

CLASSES = {
    "vanguard": {
        "name": "Vanguard", "row": "front", "hp": 30, "hp_lvl": 4, "role": "Tank",
        "dice": [D(6), [1, 2, 3, 4, "S", "S"]], "tags": ["bulwark", "juggernaut"],
        "map": {"key": "trailbreaker", "name": "Trailbreaker", "text": "Forest, hills and peaks cost you 1 move."},
        "start": ["strike", "guard"], "weapon": "boarding_axe", "armor": "padded_coat",
        "pool": ["taunt", "brace", "rally_wall", "shield_bash", "retaliate", "shoulder_charge",
                 "thick_hide", "iron_will", "steady", "spiked_plate", "overguard", "last_stand",
                 "unbreakable", "avalanche"],
        "blurb": "Stands in front and takes the hits meant for everyone else.",
    },
    "arcanist": {
        "name": "Arcanist", "row": "back", "hp": 18, "hp_lvl": 2, "role": "Area damage and burst",
        "dice": [D(12), D(4)], "tags": ["elementalist", "hexer"],
        "map": {"key": "farsight", "name": "Farsight", "text": "See 3 hexes around you, and spot cursed items in loot."},
        "start": ["bolt", "channel"], "weapon": "driftwood_staff", "armor": "oilskin_robe",
        "pool": ["fireball", "frost_lance", "chain_lightning", "hex", "siphon", "doom",
                 "overcharge", "kindling", "cold_snap", "malediction", "arcane_shield", "spell_echo",
                 "cataclysm", "grand_curse"],
        "blurb": "Wild dice and big spells. Fragile; keep them in the back.",
    },
    "mender": {
        "name": "Mender", "row": "back", "hp": 22, "hp_lvl": 3, "role": "Healer",
        "dice": [D(6), D(6)], "tags": ["restoration", "warding"],
        "map": {"key": "field_medic", "name": "Field Medic", "text": "Everyone who rests on your hex heals by half."},
        "start": ["mend", "lift"], "weapon": "lantern_rod", "armor": "nurses_apron",
        "pool": ["renew", "lifeline", "ward", "sanctuary", "cleanse", "smite",
                 "bedside_manner", "overflow", "quick_hands", "blessed_supplies", "aura", "calm",
                 "miracle", "aegis"],
        "blurb": "Keeps the party standing, and picks them up when they don't.",
    },
}

GENERIC = ["shift", "flee"]

# Party XP needed for each level (index = level - 1).
XP_FOR = [0, 20, 50, 90, 140, 200, 270, 350]
MAX_LEVEL = len(XP_FOR)
DIE_UP_LEVELS = (3, 6)
DIE_LADDER = [4, 6, 8, 10, 12]


def level_for(xp):
    lvl = 1
    for i, need in enumerate(XP_FOR):
        if xp >= need:
            lvl = i + 1
    return lvl


def skill_def(key):
    """An action or passive by key, or None."""
    base = key.rstrip("+")
    return ACTIONS.get(base) or PASSIVES.get(base)
