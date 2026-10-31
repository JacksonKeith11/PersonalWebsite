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

# A passive's `mods` are read by the game where they apply. `override` replaces parts of an action.
PASSIVES = {
    # ---- Vanguard
    "thick_hide": {"name": "Thick Hide", "mods": {"max_hp": 6}, "text": "+6 max HP."},
    "iron_will": {"name": "Iron Will", "mods": {"stun_ward": 1}, "text": "Ignore the first Stun each fight."},
    "steady": {"name": "Shieldwall", "mods": {"shield_block": 1}, "tags": ["bulwark"], "text": "Shield faces block 4."},
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
    "overcharge": {"name": "Overcharge", "mods": {"overcharge": 2}, "text": "Whenever one of your dice explodes, it adds 2 more."},
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
    "aura": {"name": "Aura", "mods": {"aura": 1}, "tags": ["warding"], "text": "The party regenerates 1 HP a round in your fights."},
    "calm": {"name": "Calm", "mods": {"freeze_immune": 1}, "text": "Your dice can't be Frozen."},
    "miracle": {"name": "Miracle", "cap": True, "mods": {"miracle": 1}, "tags": ["restoration"],
                "text": "Once per run, a revive that would be spent isn't."},
    "aegis": {"name": "Aegis", "cap": True, "mods": {"aegis": 2}, "tags": ["warding"],
              "text": "Once you cast Sanctuary, every hit on the party deals 2 less for the rest of the fight."},
}

D = lambda n: list(range(1, n + 1))

# Dice are hidden until an action resolves (Seer, Augur and Fate dice excepted), so `req` is what
# the dice must roll for the action to hit; `miss` is what happens when they don't. An action with
# no conditions in `req` always hits. Pairs and straights are bonuses written into the amounts
# (`pair`, `straight` are 1 when the dice match), not requirements. Risky actions pay roughly a
# quarter more on average than a safe action with the same die.
ACTIONS = {
    # ---- for everyone
    "block": {"name": "Block", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v"}],
              "text": "Gain Armor equal to the die. Takes Guard dice."},
    "shift": {"name": "Shift", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "shift"}], "text": "Change rows."},
    "flee": {"name": "Flee", "req": {"n": 1, "min": 4}, "tgt": "self", "ops": [{"op": "flee"}],
             "text": "4+: run back the way you came. Otherwise you stay. Not in dungeons or against bosses."},

    # ---- Vanguard
    "strike": {"name": "Strike", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "v+2+armor//2"}],
               "text": "Deal the die +2, plus half your Armor (Brace first)."},
    "guard": {"name": "Guard", "req": {"n": 1}, "tgt": "other", "ops": [{"op": "guard"}, {"op": "armor", "amt": "v", "to": "self"}],
              "text": "The next hit on an ally hits you instead. Gain Armor equal to the die."},
    "taunt": {"cd": 2, "name": "Taunt", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "taunt"}, {"op": "armor", "amt": "v//2"}],
              "tags": ["bulwark"], "text": "Every enemy attack this round comes at you. Gain half the die as Armor."},
    "brace": {"name": "Brace", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v*2"}],
              "tags": ["bulwark"], "text": "Gain Armor equal to twice the die."},
    "rally_wall": {"cd": 2, "name": "Rally Wall", "req": {"n": 2}, "tgt": "self", "ops": [{"op": "armor", "amt": "sum//2+4*pair", "to": "myrow"}],
                   "tags": ["bulwark"], "text": "Two dice: everyone in your row gains half the sum as Armor, +4 on a pair."},
    "shield_bash": {"cd": 2, "name": "Shield Bash", "req": {"n": 1, "min": 5, "or_face": "S"}, "tgt": "foe", "melee": True,
                    "ops": [{"op": "dmg", "amt": "4"}, {"op": "status", "s": "stun", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                    "tags": ["juggernaut"], "text": "A shield face or 5+: deal 4 and Stun. Otherwise half the die."},
    "retaliate": {"name": "Retaliate", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "armor+v//2"}],
                  "tags": ["juggernaut"], "text": "Deal your Armor plus half the die."},
    "shoulder_charge": {"name": "Shoulder Charge", "req": {"n": 1, "min": 5}, "tgt": "foe",
                        "ops": [{"op": "dmg", "amt": "v+3"}, {"op": "drag"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                        "tags": ["juggernaut"], "text": "Any row. 5+: the die +3, and drag it to the front. Otherwise half the die."},

    # ---- Arcanist
    "bolt": {"name": "Bolt", "req": {"n": 1}, "tgt": "foe", "spell": True, "ops": [{"op": "dmg", "amt": "v"}],
             "text": "Deal the die. Your all-rounder."},
    "channel": {"name": "Channel", "req": {"n": 2}, "tgt": "foe", "spell": True, "ops": [{"op": "dmg", "amt": "sum+2"}],
                "text": "Two dice in one blast: the sum +2. Turns small dice into one big hit."},
    "fireball": {"cd": 2, "name": "Fireball", "req": {"n": 2, "sum_min": 10}, "tgt": "foes", "spell": True, "tags": ["elementalist"],
                 "ops": [{"op": "dmg", "amt": "sum//2+2"}, {"op": "status", "s": "burn", "n": 2}],
                 "miss": [],
                 "text": "Two dice summing to 10+: half the sum +2 to every enemy, and Burn 2. Otherwise nothing."},
    "frost_lance": {"name": "Frost Lance", "req": {"n": 1, "min": 5}, "tgt": "foe", "spell": True, "tags": ["elementalist"],
                    "ops": [{"op": "dmg", "amt": "v+3"}, {"op": "status", "s": "freeze", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                    "text": "5+: the die +3, and Freeze. Otherwise half the die."},
    "chain_lightning": {"name": "Chain Lightning", "req": {"n": 1, "odd": True}, "tgt": "foe", "spell": True, "tags": ["elementalist"],
                        "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "status", "s": "shock", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                        "text": "Odd: the die +2, and Shock. Even: half the die."},
    "hex": {"name": "Hex", "req": {"n": 1}, "tgt": "foe", "spell": True,
            "ops": [{"op": "status", "s": "weak", "n": 1}, {"op": "status", "s": "vuln", "n": 1}],
            "tags": ["hexer"], "text": "Weak and Vulnerable."},
    "siphon": {"name": "Siphon", "req": {"n": 1, "min": 4}, "tgt": "foe", "spell": True, "tags": ["hexer"],
               "ops": [{"op": "dmg", "amt": "v+1", "leech": 0.5}], "miss": [{"op": "dmg", "amt": "v//2", "leech": 0.5}],
               "text": "4+: the die +1, healing you half. Otherwise half the die, still healing half."},
    "doom": {"cd": 3, "name": "Doom", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": ["hexer"],
             "ops": [{"op": "status", "s": "doom", "n": "max(5,20-v)"}],
             "text": "The target takes 20 minus the die (at least 5) at the end of next round. Low rolls are worse news."},

    # ---- Mender
    "mend": {"name": "Mend", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "heal", "amt": "v+1"}], "text": "Heal an ally the die +1."},
    "lift": {"name": "Lift", "once": True, "req": {"n": 1}, "tgt": "downed", "ops": [{"op": "lift", "amt": "v*2+2"}],
             "text": "Once per fight: pick up a knocked-down ally with twice the die +2 HP."},
    "renew": {"cd": 2, "name": "Renew", "req": {"n": 2}, "tgt": "party", "ops": [{"op": "heal", "amt": "sum//2+(sum//2)*pair"}],
              "tags": ["restoration"], "text": "Two dice: heal the whole party half the sum, or the full sum on a pair."},
    "lifeline": {"cd": 2, "name": "Lifeline", "req": {"n": 1, "min": 5}, "tgt": "ally", "tags": ["restoration"],
                 "ops": [{"op": "status", "s": "lifeline", "n": 1}], "miss": [{"op": "heal", "amt": "v//2"}],
                 "text": "5+: the ally heals fully at the end of the round. Otherwise heal them half the die now."},
    "ward": {"name": "Ward", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "armor", "amt": "v*2"}],
             "tags": ["warding"], "text": "An ally gains twice the die as Armor."},
    "sanctuary": {"cd": 2, "name": "Sanctuary", "req": {"n": 1, "min": 5}, "tgt": "party", "tags": ["warding"],
                  "ops": [{"op": "sanct", "n": 3}], "miss": [{"op": "sanct", "n": 1}],
                  "text": "5+: every hit on the party deals 3 less this round. Otherwise 1 less."},
    "cleanse": {"name": "Cleanse", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "cleanse"}, {"op": "heal", "amt": "v"}],
                "text": "Remove an ally's Burn, Poison, Weak, Vulnerable, Mark and Root, and heal the die."},
    "smite": {"name": "Smite", "req": {"n": 1, "min": 4}, "tgt": "foe", "ops": [{"op": "dmg", "amt": "v+3+3*undead"}],
              "miss": [{"op": "dmg", "amt": "v//2"}], "text": "Any row. 4+: the die +3 (+3 more against the undead). Otherwise half the die."},
    "quick_lift": {"name": "Quick Lift", "req": {"n": 0}, "tgt": "downed", "once": True,
                   "ops": [{"op": "lift", "amt": "8"}], "text": "Once per fight, no die: pick up an ally with 8 HP."},

    # ---- Duelist
    "slash_d": {"name": "Riposte Cut", "req": {"n": 1, "min": 3}, "tgt": "foe", "melee": True,
                "ops": [{"op": "dmg", "amt": "v+2"}], "miss": [{"op": "dmg", "amt": "v//2"}], "text": "3+: the die +2. Otherwise half the die."},
    "parry": {"name": "Parry", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v"}, {"op": "status", "s": "riposte", "n": 2, "to": "self"}],
              "text": "Gain Armor equal to the die. If a hit is fully blocked this round, riposte for 2."},
    "twin_cut": {"name": "Twin Cut", "req": {"n": 2}, "tgt": "foe", "melee": True, "tags": ["flurry"],
                 "ops": [{"op": "dmg", "amt": "d+3*pair", "each": True}], "text": "Two dice: hit once with each, +3 each on a pair."},
    "whirl": {"name": "Whirl", "req": {"n": 3, "upto": True}, "tgt": "foes", "tags": ["flurry"],
              "ops": [{"op": "dmg", "amt": "d+1", "each": True, "random": True}], "text": "Up to three dice: each hits a random enemy for the die +1."},
    "lunge": {"cd": 2, "name": "Lunge", "req": {"n": 1, "min": 6}, "tgt": "foe", "tags": ["precision"],
              "ops": [{"op": "dmg", "amt": "v+10"}, {"op": "status", "s": "stun", "n": 1}], "miss": [],
              "text": "Any row. 6+: the die +10, and Stun. Otherwise nothing."},
    "finisher": {"name": "Finisher", "req": {"n": 3}, "tgt": "foe", "melee": True, "tags": ["precision"],
                 "ops": [{"op": "dmg", "amt": "sum+sum*straight"}], "text": "Three dice in one hit: the sum, doubled on a straight."},
    "pinpoint": {"name": "Pinpoint", "req": {"n": 1}, "tgt": "foe", "tags": ["precision"],
                 "ops": [{"op": "dmg", "amt": "v+14*matched", "pierce": True}],
                 "text": "Any row, ignoring Armor: the die, +14 if it equals the target's intent number."},
    "feint": {"name": "Feint", "req": {"n": 1}, "tgt": "foe", "ops": [{"op": "weaken", "amt": "v"}],
              "text": "Reduce an enemy's intent by the die."},
    "perfect_form": {"name": "Perfect Form", "req": {"n": 1}, "tgt": "self", "instant": True, "per_round": True,
                     "ops": [{"op": "setdie", "to": "max"}], "text": "Once a round: a die of yours will roll its top face. It stays unused."},

    # ---- Berserker
    "hack_b": {"name": "Hack", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "v+2"}], "text": "Deal the die +2."},
    "bloodprice": {"name": "Bloodprice", "req": {"n": 1}, "tgt": "self", "instant": True,
                   "ops": [{"op": "selfdmg", "amt": "3"}, {"op": "bump", "amt": "3"}], "text": "Pay 3 HP: a die of yours rolls 3 higher. It stays unused."},
    "drink_deep": {"name": "Drink Deep", "req": {"n": 1, "min": 4}, "tgt": "foe", "melee": True, "tags": ["bloodlust"],
                   "ops": [{"op": "dmg", "amt": "v+2", "onkill": "v+2"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                   "text": "4+: the die +2, and if it kills, heal that much. Otherwise half the die."},
    "frenzy": {"name": "Frenzy", "req": {"n": 2}, "tgt": "foe", "melee": True, "tags": ["bloodlust"],
               "ops": [{"op": "dmg", "amt": "sum+3"}, {"op": "selfdmg", "amt": "2"}], "text": "Two dice in one hit: the sum +3. Take 2."},
    "cleave": {"name": "Cleave", "req": {"n": 1, "min": 5}, "tgt": "front", "melee": True, "tags": ["rampage"],
               "ops": [{"op": "dmg", "amt": "v"}], "miss": [{"op": "dmg", "amt": "v//2", "to": "one"}],
               "text": "5+: the die to the whole front row. Otherwise half the die to one of them."},
    "earthshaker": {"cd": 2, "name": "Earthshaker", "req": {"n": 2, "sum_min": 12}, "tgt": "foes", "tags": ["rampage"],
                    "ops": [{"op": "dmg", "amt": "sum//2"}, {"op": "status", "s": "stun", "n": 1, "to": "random"}],
                    "miss": [],
                    "text": "Two dice summing to 12+: half the sum to every enemy, and Stun one. Otherwise nothing."},
    "reckless_swing": {"name": "Reckless Swing", "req": {"n": 1, "min": 8}, "tgt": "foe", "melee": True,
                       "ops": [{"op": "dmg", "amt": "v+12"}, {"op": "selfdmg", "amt": "3"}], "miss": [{"op": "selfdmg", "amt": "3"}],
                       "text": "8+: the die +12. Otherwise nothing. Take 3 either way."},
    "howl": {"cd": 2, "name": "Howl", "req": {"n": 1}, "tgt": "foes", "ops": [{"op": "status", "s": "weak", "n": 1}],
             "text": "Every enemy is Weak this round."},

    # ---- Ranger
    "shoot_r": {"name": "Shoot", "req": {"n": 1}, "tgt": "foe", "ops": [{"op": "dmg", "amt": "v+1"}], "text": "Any row: deal the die +1."},
    "hunters_mark": {"name": "Hunter's Mark", "req": {"n": 1}, "tgt": "foe",
                     "ops": [{"op": "status", "s": "mark", "n": 1}, {"op": "dmg", "amt": "v//3"}],
                     "text": "Mark an enemy (+3 damage from every hit) and deal a third of the die."},
    "aimed_shot": {"name": "Aimed Shot", "req": {"n": 1, "min": 6}, "tgt": "foe", "tags": ["marksman"],
                   "ops": [{"op": "dmg", "amt": "v*2+1"}], "miss": [],
                   "text": "Any row. 6+: twice the die +1. Otherwise nothing."},
    "called_shot": {"name": "Called Shot", "req": {"n": 2, "marked": True}, "tgt": "foe", "tags": ["marksman"],
                    "ops": [{"op": "dmg", "amt": "sum+6*pair", "pierce": True}],
                    "text": "Two dice on a Marked enemy, ignoring Armor: the sum, +6 on a pair."},
    "sic_em": {"name": "Sic 'Em", "req": {"n": 1}, "tgt": "foe", "tags": ["beastmaster"],
               "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "weak", "n": 1}], "text": "Your hawk dives: deal the die to any row, and Weak."},
    "pack_tactics": {"name": "Pack Tactics", "req": {"n": 1, "min": 4}, "tgt": "foe", "tags": ["beastmaster"],
                     "ops": [{"op": "dmg", "amt": "v+5"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                     "text": "Any row. 4+: you and your hawk together, the die +5. Otherwise half the die."},
    "volley": {"name": "Volley", "req": {"n": 3, "upto": True}, "tgt": "foes",
               "ops": [{"op": "dmg", "amt": "(d+1)//2", "each": True}],
               "text": "Up to three dice: every enemy takes half of each die (rounded up). Made for crowds."},
    "pinning_arrow": {"name": "Pinning Arrow", "req": {"n": 1, "min": 4}, "tgt": "foe",
                      "ops": [{"op": "dmg", "amt": "v+1"}, {"op": "status", "s": "root", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                      "text": "Any row. 4+: the die +1, and Root. Otherwise half the die."},

    # ---- Scoundrel
    "stab": {"name": "Stab", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "v+1+3*(1-aimed)"}],
             "text": "Deal the die +1, or +4 if the enemy isn't coming for you."},
    "slip": {"name": "Slip", "req": {"n": 1}, "tgt": "self", "free_shift": True,
             "ops": [{"op": "shift"}, {"op": "status", "s": "dodge", "n": 1, "to": "self", "if": "v>=4"}],
             "text": "Change rows, even when Rooted. On a 4+, also dodge the next hit."},
    "envenom": {"name": "Envenom", "req": {"n": 1}, "tgt": "foe", "tags": ["poisons"],
                "ops": [{"op": "status", "s": "poison", "n": "max(1,v//2)"}], "text": "Poison equal to half the die."},
    "garrote": {"cd": 2, "name": "Garrote", "req": {"n": 1, "min": 5}, "tgt": "foe", "melee": True, "tags": ["poisons"],
                "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "status", "s": "stun", "n": 1, "if": "poisoned"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                "text": "5+: the die +2, and Stun if it's Poisoned. Otherwise half the die."},
    "toxic_cloud": {"cd": 2, "name": "Toxic Cloud", "req": {"n": 2, "sum_min": 9}, "tgt": "foes", "tags": ["poisons"],
                    "ops": [{"op": "status", "s": "poison", "n": 3}], "miss": [],
                    "text": "Two dice summing to 9+: Poison 3 on every enemy. Otherwise nothing."},
    "pickpocket": {"cd": 3, "name": "Pickpocket", "req": {"n": 1, "min": 4}, "tgt": "foe", "tags": ["tricks"],
                   "ops": [{"op": "weaken", "amt": "v"}, {"op": "gold", "amt": "4"}], "miss": [{"op": "weaken", "amt": "v//2"}],
                   "text": "4+: reduce its intent by the die, and lift 4 gold. Otherwise reduce it by half the die."},
    "loaded_dice": {"name": "Loaded Dice", "req": {"n": 2}, "tgt": "self", "instant": True, "tags": ["tricks"],
                    "ops": [{"op": "loaded"}], "text": "Two of your dice become linked: the second rolls whatever the first does. Both stay unused."},
    "smoke_bomb": {"cd": 2, "name": "Smoke Bomb", "req": {"n": 2, "pair": True}, "tgt": "party",
                   "ops": [{"op": "status", "s": "dodge", "n": 1}], "miss": [],
                   "text": "Two dice: on a pair, everyone dodges their next hit. Otherwise nothing."},

    # ---- Herald
    "inspire": {"name": "Inspire", "req": {"n": 1}, "tgt": "other", "instant": True,
                "ops": [{"op": "inspire"}], "text": "Roll the die now: an ally's next die rolls higher by half of it (at least 2)."},
    "jab": {"name": "Cutting Words", "req": {"n": 1}, "tgt": "foe", "ops": [{"op": "dmg", "amt": "v"}], "text": "Any row: deal the die."},
    "hymn_of_valor": {"cd": 2, "name": "Hymn of Valor", "req": {"n": 2}, "tgt": "self", "instant": True, "tags": ["anthem"],
                      "ops": [{"op": "hymn"}], "text": "Two dice: every die the party rolls this round is 1 higher (2 if these two match, which you'll see)."},
    "lend_a_hand": {"name": "Lend a Hand", "req": {"n": 1}, "tgt": "other", "instant": True, "tags": ["anthem"],
                    "ops": [{"op": "give"}], "text": "Give one of your dice to an ally, Seer dice and all."},
    "crescendo": {"cd": 2, "name": "Crescendo", "req": {"n": 2}, "tgt": "party", "tags": ["anthem"],
                  "ops": [{"op": "status", "s": "crescendo", "n": 1}], "text": "Two dice: everyone's next damaging action deals 50% more."},
    "dirge": {"name": "Dirge", "req": {"n": 1}, "tgt": "foe", "tags": ["discord"],
              "ops": [{"op": "status", "s": "weak", "n": 1}, {"op": "dmg", "amt": "v//2"}], "text": "Weak an enemy and deal half the die."},
    "taunting_verse": {"name": "Taunting Verse", "req": {"n": 1, "min": 4}, "tgt": "foe", "tags": ["discord"],
                       "ops": [{"op": "retarget"}], "miss": [{"op": "weaken", "amt": "2"}],
                       "text": "4+: an enemy's attack swings to someone else (or nobody). Otherwise its intent drops by 2."},
    "cacophony": {"cd": 3, "name": "Cacophony", "req": {"n": 2, "sum_min": 8}, "tgt": "foe", "tags": ["discord"],
                  "ops": [{"op": "cancel"}], "miss": [{"op": "weaken", "amt": "sum//3"}],
                  "text": "Two dice summing to 8+: an enemy loses its turn. Otherwise its intent drops by a third of the sum."},
    "requiem": {"name": "Requiem", "req": {"n": 0}, "tgt": "foe", "once": True, "ops": [{"op": "cancel"}],
                "text": "Once per fight, no die: cancel an enemy's intent."},

    # ---- Alchemist
    "toss": {"name": "Toss", "req": {"n": 1}, "tgt": "foe", "bomb": True, "ops": [{"op": "dmg", "amt": "v", "splash": 1}],
             "text": "A bomb, any row: the die to one enemy, 1 to those beside it."},
    "tonic_a": {"name": "Tonic", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "heal", "amt": "v+1"}], "text": "Heal an ally the die +1."},
    "firebomb": {"cd": 2, "name": "Firebomb", "req": {"n": 1, "min": 4}, "tgt": "foe", "bomb": True, "tags": ["bombs"],
                 "ops": [{"op": "dmg", "amt": "v", "to": "row"}, {"op": "status", "s": "burn", "n": 1, "to": "row"}],
                 "miss": [{"op": "dmg", "amt": "v//2"}],
                 "text": "4+: the die to the target's whole row, and Burn 1. Otherwise half the die to the target."},
    "acid_flask": {"name": "Acid Flask", "req": {"n": 1}, "tgt": "foe", "tags": ["bombs"],
                   "ops": [{"op": "strip", "amt": "v*2"}, {"op": "status", "s": "vuln", "n": 1}], "text": "Strip twice the die in Armor, and Vulnerable."},
    "concussion": {"cd": 2, "name": "Concussion", "req": {"n": 1, "min": 5}, "tgt": "foe", "bomb": True, "tags": ["bombs"],
                   "ops": [{"op": "dmg", "amt": "3"}, {"op": "status", "s": "stun", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                   "text": "5+: deal 3 and Stun. Otherwise half the die."},
    "bottle_it": {"cd": 3, "name": "Bottle It", "req": {"n": 1}, "tgt": "self", "instant": True, "tags": ["elixirs"],
                  "ops": [{"op": "bottle"}], "text": "Roll the die now and bottle it: a Tonic, or a Rum Ration on 5+."},
    "quicksilver": {"cd": 3, "name": "Quicksilver", "req": {"n": 2}, "tgt": "other", "instant": True, "tags": ["elixirs"],
                    "ops": [{"op": "reroll_ally"}], "text": "Two dice: an ally gets 2 more automatic rerolls this fight."},
    "panacea": {"cd": 2, "name": "Panacea", "req": {"n": 2, "sum_min": 8}, "tgt": "party", "tags": ["elixirs"],
                "ops": [{"op": "cleanse"}, {"op": "heal", "amt": "sum//2"}], "miss": [{"op": "cleanse"}],
                "text": "Two dice summing to 8+: cleanse the party and heal half the sum. Otherwise just cleanse."},

    # ---- Warden
    "thornlash": {"name": "Thornlash", "req": {"n": 1}, "tgt": "foe",
                  "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "root", "n": 1, "if": "v>=5"}], "text": "Any row: deal the die; on a 5+, Root."},
    "sprout": {"name": "Sprout", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "summon", "k": "sapling", "hp": "v*2"}],
               "text": "Grow a sapling in the front row with HP equal to twice the die. It soaks up hits."},
    "call_bear": {"cd": 3, "name": "Call Bear", "req": {"n": 2, "sum_min": 9}, "tgt": "self", "tags": ["grove"],
                  "ops": [{"op": "summon", "k": "bear"}], "miss": [],
                  "text": "Two dice summing to 9+: a bear joins you (15 HP, hits for 4). Otherwise nothing."},
    "swarm": {"cd": 2, "name": "Swarm", "req": {"n": 2}, "tgt": "self", "tags": ["grove"],
              "ops": [{"op": "summon", "k": "wasps", "hp": "sum"}], "text": "Two dice: a wasp swarm with the sum in HP, stinging every enemy for 1 a round."},
    "regrowth": {"name": "Regrowth", "req": {"n": 1}, "tgt": "party", "tags": ["grove"],
                 "ops": [{"op": "heal", "amt": "v//2+1"}, {"op": "heal_summons", "amt": "v"}], "text": "Heal the party half the die +1, and your summons the die."},
    "entangle": {"name": "Entangle", "req": {"n": 1}, "tgt": "foe", "tags": ["thorns"],
                 "ops": [{"op": "status", "s": "root", "n": 1}, {"op": "status", "s": "weak", "n": 1}], "text": "Root and Weak."},
    "briar_wall": {"cd": 2, "name": "Briar Wall", "req": {"n": 2}, "tgt": "self", "tags": ["thorns"],
                   "ops": [{"op": "armor", "amt": "sum//2+2*pair", "to": "front"}, {"op": "status", "s": "thorns", "n": 2, "to": "front"}],
                   "text": "Two dice: the front row gains half the sum as Armor (+2 on a pair) and hits back for 2 this round."},
    "strangle": {"name": "Strangle", "req": {"n": 1, "min": 4}, "tgt": "foe", "tags": ["thorns"],
                 "ops": [{"op": "dmg", "amt": "(v+1)*(1+rooted)"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                 "text": "Any row. 4+: the die +1, doubled against a Rooted enemy. Otherwise half the die."},
    "ancient_guardian": {"name": "Ancient Guardian", "req": {"n": 0}, "tgt": "self", "once": True,
                         "ops": [{"op": "summon", "k": "treant"}], "text": "Once per fight, no die: a treant rises (25 HP, hits for 5)."},
}

# Each class's two class dice. A die is a list of faces, or {"faces": [...], "dk": [kinds]}.
# Faces: numbers; "S" shield (0, blocks 3); "X" skull (0, and you take 3); "W" wild (counts as the
# die's top face and passes any condition); "F3"/"I3"/"P3" a 3 that also Burns/Freezes/Poisons.
# Kinds: seer (rolled and shown while you plan), augur (shows high or low), fate (shows two faces,
# one comes up), exploding (a top face rolls again and adds), steady (rerolls once on a miss),
# heirloom (its lowest face rises with every level), link:<g> (dice in a group roll the same).
CLASS_DICE = {
    "vanguard": [{"faces": [1, 2, 3, 4, "S", "S"], "dk": []}, {"faces": D(6), "dk": ["steady"]}],
    "duelist": [{"faces": D(8), "dk": []}, {"faces": D(6), "dk": ["fate"]}],
    "berserker": [{"faces": ["X", 3, 4, 5, 6, 7, 8, 9, 10, 12], "dk": []}, {"faces": D(4), "dk": []}],
    "ranger": [{"faces": D(8), "dk": []}, {"faces": D(6), "dk": ["augur"]}],
    "arcanist": [{"faces": D(12), "dk": ["exploding"]}, {"faces": D(4), "dk": []}],
    "mender": [{"faces": [2, 3, 3, 4, 4, 5], "dk": []}, {"faces": [2, 3, 3, 4, 4, 5], "dk": []}],
    "scoundrel": [{"faces": D(6), "dk": ["link:pair"]}, {"faces": D(6), "dk": ["link:pair"]}],
    "herald": [{"faces": D(6), "dk": []}, {"faces": D(4), "dk": ["seer"]}],
    "alchemist": [{"faces": [1, 2, "F3", 4, "P5", 6], "dk": []}, {"faces": D(6), "dk": []}],
    "warden": [{"faces": D(8), "dk": ["heirloom"]}, {"faces": D(6), "dk": []}],
}


CLASSES = {
    "vanguard": {
        "name": "Vanguard", "row": "front", "hp": 36, "hp_lvl": 5, "role": "Tank",
        "dice": [D(6), [1, 2, 3, 4, "S", "S"]], "tags": ["bulwark", "juggernaut"],
        "map": {"key": "trailbreaker", "name": "Trailbreaker", "text": "Forest, hills and peaks cost you 1 move."},
        "start": ["strike", "guard"], "weapon": "hand_axe", "armor": "padded_coat",
        "pool": ["taunt", "brace", "rally_wall", "shield_bash", "retaliate", "shoulder_charge",
                 "thick_hide", "iron_will", "steady", "spiked_plate", "overguard", "last_stand",
                 "unbreakable", "avalanche"],
        "blurb": "Stands in front and takes the hits meant for everyone else.",
    },
    "arcanist": {
        "name": "Arcanist", "row": "back", "hp": 18, "hp_lvl": 2, "role": "Area damage and burst",
        "dice": [D(12), D(4)], "tags": ["elementalist", "hexer"],
        "map": {"key": "farsight", "name": "Farsight", "text": "See 3 hexes around you, and spot cursed items in loot."},
        "start": ["bolt", "channel"], "weapon": "oak_staff", "armor": "wool_robe",
        "pool": ["fireball", "frost_lance", "chain_lightning", "hex", "siphon", "doom",
                 "overcharge", "kindling", "cold_snap", "malediction", "arcane_shield", "spell_echo",
                 "cataclysm", "grand_curse"],
        "blurb": "Wild dice and big spells. Fragile; keep them in the back.",
    },
    "mender": {
        "name": "Mender", "row": "back", "hp": 22, "hp_lvl": 3, "role": "Healer",
        "dice": [D(6), D(6)], "tags": ["restoration", "warding"],
        "map": {"key": "field_medic", "name": "Field Medic", "text": "Everyone who rests on your hex heals an extra 10% of their max HP."},
        "start": ["mend", "lift"], "weapon": "lantern_rod", "armor": "nurses_apron",
        "pool": ["renew", "lifeline", "ward", "sanctuary", "cleanse", "smite",
                 "bedside_manner", "overflow", "quick_hands", "blessed_supplies", "aura", "calm",
                 "miracle", "aegis"],
        "blurb": "Keeps the party standing, and picks them up when they don't.",
    },
}

PASSIVES.update({
    # ---- Duelist
    "momentum": {"name": "Momentum", "mods": {"momentum": 1}, "tags": ["flurry"], "text": "Each of your actions after the first in a round deals +1."},
    "keen_edge": {"name": "Keen Edge", "mods": {"keen_edge": 1}, "tags": ["precision"], "text": "Your 6s count as 7."},
    "riposte_plus": {"name": "Riposte+", "mods": {"riposte_up": 2}, "text": "Your ripostes deal 2 more."},
    "footwork": {"name": "Footwork", "mods": {"footwork": 2}, "text": "Back-row enemies deal 2 less to you."},
    "opportunist": {"name": "Opportunist", "mods": {"opportunist": 3}, "text": "+3 damage against Stunned or Rooted enemies."},
    "second_wind": {"name": "Second Wind", "mods": {"kill_heal": 3}, "text": "Heal 3 whenever you kill an enemy."},
    "thousand_cuts": {"name": "Thousand Cuts", "cap": True, "tags": ["flurry"], "mods": {"override": {"twin_cut": {"req": {"n": 4, "upto": True}}}},
                      "text": "Twin Cut takes up to four dice."},
    "perfect_poise": {"name": "Perfect Poise", "cap": True, "tags": ["precision"], "mods": {"grant": "perfect_form"},
                      "text": "Learn Perfect Form: once a round, turn a die to its highest face."},
    # ---- Berserker
    "rage": {"name": "Rage", "mods": {"rage": 1}, "text": "+1 damage for every 5 HP you're missing."},
    "bloodlust": {"name": "Bloodlust", "mods": {"kill_heal": 3}, "tags": ["bloodlust"], "text": "Heal 3 whenever you kill an enemy."},
    "wide_arcs": {"name": "Wide Arcs", "mods": {"wide_arcs": 1}, "tags": ["rampage"], "text": "Cleave hits the back row for half."},
    "pain_engine": {"name": "Pain Engine", "mods": {"pain_engine": 1}, "tags": ["bloodlust"], "text": "Each hit you take makes your first die next round roll 1 higher."},
    "thick_skull": {"name": "Thick Skull", "mods": {"max_hp": 4, "weak_immune": 1}, "text": "+4 max HP, and you can't be made Weak."},
    "undying_fury": {"name": "Undying Fury", "mods": {"undying": 8}, "tags": ["rampage"], "text": "When you're knocked down, hit back at whoever did it for 8."},
    "red_mist": {"name": "Red Mist", "cap": True, "mods": {"red_mist": 1}, "tags": ["bloodlust"], "text": "Under half HP, all your damage heals you for half."},
    "unstoppable": {"name": "Unstoppable", "cap": True, "mods": {"unstoppable": 1}, "tags": ["rampage"], "text": "Cleave and Earthshaker ignore Armor, and Cleave reaches any row."},
    # ---- Ranger
    "eagle_eye": {"name": "Eagle Eye", "mods": {"eagle_eye": 1}, "tags": ["marksman"], "text": "A die showing its highest face deals double damage."},
    "companion": {"name": "Companion", "mods": {"pet": 4}, "tags": ["beastmaster"], "text": "Your hawk adds a d4 to your dice every round."},
    "field_dressing": {"name": "Field Dressing", "mods": {"regen": 2}, "tags": ["beastmaster"], "text": "Regenerate 2 HP a round in fights."},
    "quiver": {"name": "Quiver", "mods": {"override": {"volley": {"req": {"n": 4, "upto": True}}}}, "text": "Volley takes up to four dice."},
    "long_mark": {"name": "Long Mark", "mods": {"mark_ext": 1}, "tags": ["marksman"], "text": "Your Marks last a round longer."},
    "camouflage": {"name": "Camouflage", "mods": {"camouflage": 1}, "text": "Enemies attack you only when there's nobody else."},
    "deadeye": {"name": "Deadeye", "cap": True, "mods": {"deadeye": 1}, "tags": ["marksman"], "text": "Your biggest die is always a Seer die that shows its top face."},
    "alpha": {"name": "Alpha", "cap": True, "mods": {"pet": 4, "pet_strike": 1}, "tags": ["beastmaster"], "text": "Your hawk's die is a d8, and it strikes the weakest enemy for 3 every round."},
    # ---- Scoundrel
    "virulence": {"name": "Virulence", "mods": {"poison_bonus": 1}, "tags": ["poisons"], "text": "Your Poisons are 1 stronger."},
    "wayfinder": {"name": "Wayfinder", "mods": {"move": 2, "wayfinder": 1}, "tags": ["tricks"], "text": "+2 move, and you see further along your path."},
    "lucky_coin": {"name": "Lucky Coin", "mods": {"reroll": 1}, "tags": ["tricks"], "text": "+1 automatic reroll per fight: a die that misses rolls again."},
    "sticky_fingers": {"name": "Sticky Fingers", "mods": {"sticky": 5}, "text": "+5 gold after every fight you win."},
    "evasive": {"name": "Evasive", "mods": {"evasive": 1}, "text": "The first hit on you each fight misses."},
    "backstab": {"name": "Backstab", "mods": {"backstab": 4}, "text": "+4 damage against enemies coming for someone else."},
    "plague": {"name": "Plague", "cap": True, "mods": {"plague": 1}, "tags": ["poisons"], "text": "When a Poisoned enemy dies, its Poison spreads to another."},
    "sleight_of_hand": {"name": "Sleight of Hand", "cap": True, "mods": {"sleight": 1}, "tags": ["tricks"],
                        "text": "Your linked dice each roll 1 higher."},
    # ---- Herald
    "battle_hymn": {"name": "Battle Hymn", "mods": {"hymn_aura": 1}, "tags": ["anthem"], "text": "While you're standing, the party deals +1 damage."},
    "second_verse": {"name": "Second Verse", "mods": {"second_verse": 1}, "tags": ["anthem"], "text": "Dice you give or boost get +1 more."},
    "heckler": {"name": "Heckler", "mods": {"heckler": 3}, "tags": ["discord"], "text": "Enemies' first attacks each fight are 3 weaker."},
    "haggler": {"name": "Haggler", "mods": {"haggler": 1}, "text": "Sell for 60% instead of 40%."},
    "silver_voice": {"name": "Silver Voice", "mods": {"silver_voice": 1}, "text": "+1 to every event roll."},
    "encore": {"name": "Encore", "mods": {"reroll": 1}, "text": "+1 automatic reroll per fight: a die that misses rolls again."},
    "anthem_of_kings": {"name": "Anthem of Kings", "cap": True, "mods": {"anthem": 1}, "tags": ["anthem"], "text": "Every ally rolls an extra d4 each round."},
    "requiem_cap": {"name": "Requiem", "cap": True, "mods": {"grant": "requiem"}, "tags": ["discord"], "text": "Learn Requiem: once per fight, cancel an enemy's intent without a die."},
    # ---- Alchemist
    "volatile": {"name": "Volatile", "mods": {"bomb_bonus": 2}, "tags": ["bombs"], "text": "Your bombs deal +2."},
    "shrapnel": {"name": "Shrapnel", "mods": {"splash_bonus": 2}, "tags": ["bombs"], "text": "Your bombs' splash deals +2."},
    "potency": {"name": "Potency", "mods": {"potion_bonus": 0.5}, "tags": ["elixirs"], "text": "Potions you use heal 50% more."},
    "distiller": {"name": "Distiller", "mods": {"distiller": 1}, "tags": ["elixirs"], "text": "Resting brews two potions instead of one."},
    "deep_pockets": {"name": "Deep Pockets", "mods": {"bag": 2}, "text": "+2 bag slots."},
    "safety_goggles": {"name": "Safety Goggles", "mods": {"burn_immune": 1}, "text": "You can't be Burned."},
    "chain_reaction": {"name": "Chain Reaction", "cap": True, "mods": {"chain_reaction": 1}, "tags": ["bombs"],
                       "text": "Enemies your bombs kill explode for half their max HP."},
    "philosophers_draught": {"name": "Philosopher's Draught", "cap": True, "mods": {"philosopher": 1}, "tags": ["elixirs"],
                             "text": "Bottle It makes two potions."},
    # ---- Warden
    "deep_roots": {"name": "Deep Roots", "mods": {"summon_hp": 0.5}, "tags": ["grove"], "text": "Your summons have 50% more HP."},
    "pack_leader": {"name": "Pack Leader", "mods": {"summon_cap": 1}, "tags": ["grove"], "text": "Keep one more summon at a time."},
    "bramble_skin": {"name": "Bramble Skin", "mods": {"thorns": 2}, "tags": ["thorns"], "text": "Attackers take 2."},
    "overgrowth": {"name": "Overgrowth", "mods": {"root_ext": 1}, "tags": ["thorns"], "text": "Your Roots last a round longer."},
    "verdant": {"name": "Verdant", "mods": {"summon_regen": 2}, "text": "Your summons heal 2 a round."},
    "bark": {"name": "Bark", "mods": {"bark": 1}, "text": "Start every fight with a 6 HP sapling."},
    "guardian_call": {"name": "Ancient Guardian", "cap": True, "mods": {"grant": "ancient_guardian"}, "tags": ["grove"],
                      "text": "Learn Ancient Guardian: once per fight, a treant rises."},
    "crown_of_thorns": {"name": "Crown of Thorns", "cap": True, "mods": {"crown_thorns": 2}, "tags": ["thorns"],
                        "text": "All enemies take 2 at the start of every round."},
})

CLASSES.update({
    "duelist": {
        "name": "Duelist", "row": "front", "hp": 24, "hp_lvl": 3, "role": "Single-target damage",
        "dice": [D(8), D(6)], "tags": ["flurry", "precision"],
        "map": {"key": "ambush", "name": "Ambush", "text": "A fight you start gives the party a free first round."},
        "start": ["slash_d", "parry"], "weapon": "rapier", "armor": "padded_coat",
        "pool": ["twin_cut", "whirl", "lunge", "finisher", "pinpoint", "feint",
                 "momentum", "keen_edge", "riposte_plus", "footwork", "opportunist", "second_wind",
                 "thousand_cuts", "perfect_poise"],
        "blurb": "Fast, precise and deadly against one target at a time.",
    },
    "berserker": {
        "name": "Berserker", "row": "front", "hp": 34, "hp_lvl": 4, "role": "High-risk damage",
        "dice": [D(10), D(4)], "tags": ["bloodlust", "rampage"],
        "map": {"key": "forage", "name": "Forage", "text": "Resting at a camp heals you fully."},
        "start": ["hack_b", "bloodprice"], "weapon": "great_axe", "armor": "hide_vest",
        "pool": ["drink_deep", "frenzy", "cleave", "earthshaker", "reckless_swing", "howl",
                 "rage", "bloodlust", "wide_arcs", "pain_engine", "thick_skull", "undying_fury",
                 "red_mist", "unstoppable"],
        "blurb": "Trades blood for power, and gets more dangerous the more it's hurt.",
    },
    "ranger": {
        "name": "Ranger", "row": "back", "hp": 22, "hp_lvl": 3, "role": "Ranged damage",
        "dice": [D(8), D(6)], "tags": ["marksman", "beastmaster"],
        "map": {"key": "tracker", "name": "Tracker", "text": "+1 move on land, and you see enemies 2 hexes further off."},
        "start": ["shoot_r", "hunters_mark"], "weapon": "short_bow", "armor": "padded_coat",
        "pool": ["aimed_shot", "called_shot", "sic_em", "pack_tactics", "volley", "pinning_arrow",
                 "eagle_eye", "companion", "field_dressing", "quiver", "long_mark", "camouflage",
                 "deadeye", "alpha"],
        "blurb": "Picks enemies off from the back row, with a hawk for company.",
    },
    "scoundrel": {
        "name": "Scoundrel", "row": "either", "hp": 22, "hp_lvl": 3, "role": "Debuffs and loot",
        "dice": [D(6), D(6)], "tags": ["poisons", "tricks"],
        "map": {"key": "light_fingers", "name": "Light Fingers", "text": "One more choice whenever you loot a wreck or a chest."},
        "start": ["stab", "slip"], "weapon": "daggers", "armor": "padded_coat",
        "pool": ["envenom", "garrote", "toxic_cloud", "pickpocket", "loaded_dice", "smoke_bomb",
                 "virulence", "wayfinder", "lucky_coin", "sticky_fingers", "evasive", "backstab",
                 "plague", "sleight_of_hand"],
        "blurb": "Poisons, dirty tricks and loaded dice. Always comes out ahead.",
    },
    "herald": {
        "name": "Herald", "row": "back", "hp": 20, "hp_lvl": 3, "role": "Buffs for allies",
        "dice": [D(6), D(4)], "tags": ["anthem", "discord"],
        "map": {"key": "silver_tongue", "name": "Silver Tongue", "text": "Shops and inns are 20% cheaper, and some events open up."},
        "start": ["inspire", "jab"], "weapon": "lute", "armor": "padded_coat",
        "pool": ["hymn_of_valor", "lend_a_hand", "crescendo", "dirge", "taunting_verse", "cacophony",
                 "battle_hymn", "second_verse", "heckler", "haggler", "silver_voice", "encore",
                 "anthem_of_kings", "requiem_cap"],
        "blurb": "Makes everyone else's dice better, and throws enemies off their stride.",
    },
    "alchemist": {
        "name": "Alchemist", "row": "back", "hp": 20, "hp_lvl": 3, "role": "Items and gadgets",
        "dice": [D(6), D(6)], "tags": ["bombs", "elixirs"],
        "map": {"key": "brewer", "name": "Brewer", "text": "Brew a potion whenever you rest."},
        "start": ["toss", "tonic_a"], "weapon": "sling", "armor": "leather_apron",
        "pool": ["firebomb", "acid_flask", "concussion", "bottle_it", "quicksilver", "panacea",
                 "volatile", "shrapnel", "potency", "distiller", "deep_pockets", "safety_goggles",
                 "chain_reaction", "philosophers_draught"],
        "blurb": "Bombs for the enemy, potions for friends, and never enough bag space.",
    },
    "warden": {
        "name": "Warden", "row": "back", "hp": 24, "hp_lvl": 3, "role": "Summons and control",
        "dice": [D(8), D(6)], "tags": ["grove", "thorns"],
        "map": {"key": "wildspeak", "name": "Wildspeak", "text": "Forest costs you 1 move, and wild beasts won't hunt you."},
        "start": ["thornlash", "sprout"], "weapon": "gnarled_staff", "armor": "hide_vest",
        "pool": ["call_bear", "swarm", "regrowth", "entangle", "briar_wall", "strangle",
                 "deep_roots", "pack_leader", "bramble_skin", "overgrowth", "verdant", "bark",
                 "guardian_call", "crown_of_thorns"],
        "blurb": "Grows a wall of living things between the party and harm.",
    },
})

for _k, _dice in CLASS_DICE.items():
    CLASSES[_k]["dice"] = _dice

# Summons a Warden can call: hero-side units that soak hits and act after the heroes.
SUMMONS = {
    "sapling": {"name": "Sapling", "hp": 6, "atk": 0, "row": "front"},
    "bear": {"name": "Bear", "hp": 15, "atk": 4, "row": "front"},
    "wasps": {"name": "Wasp Swarm", "hp": 6, "atk": 1, "all": True, "row": "back"},
    "treant": {"name": "Treant", "hp": 25, "atk": 5, "row": "front"},
}
SUMMON_CAP = 2

GENERIC = ["block", "shift", "flee"]

# Guard dice (armor and some trinkets) only go on defensive actions: ones that do nothing but
# protect, heal, move or blunt the enemies' attacks.
DEF_OPS = {"armor", "guard", "heal", "lift", "taunt", "shift", "flee", "sanct", "cleanse", "heal_summons", "weaken", "retarget"}
DEF_STATUS = {"dodge", "riposte", "thorns", "lifeline"}


def is_defensive(a):
    ops = list(a["ops"]) + list(a.get("miss", []))
    return bool(ops) and not a.get("instant") and all(
        o["op"] in DEF_OPS or (o["op"] == "status" and o["s"] in DEF_STATUS) for o in ops)


# Cooldowns: only each class's basic action (the Vanguard's Brace too: a tank needs a defence it can
# count on every round), Block, Shift, Flee and Lift (plus weapon actions, in
# items.py) can be used every round. Everything else waits at least a round after use, so a hero
# can't win with one strong skill on repeat. `cd` N means usable every N rounds.
FREE = {"strike", "brace", "bolt", "slash_d", "hack_b", "shoot_r", "stab", "jab", "toss", "thornlash",
        "block", "shift", "flee"}  # the Mender's free action is its weapon's Flare; Mend cools, Lift is once a fight
BIG = {"finisher": 3, "called_shot": 3, "reckless_swing": 3}

for _k, _a in ACTIONS.items():
    _a["def"] = is_defensive(_a)
    if _k not in FREE and not _a.get("once"):
        _a["cd"] = max(_a.get("cd", 2), BIG.get(_k, 2))

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
