"""The hero classes, their actions and passives.

Classes are generic: nothing here may mention the sea, tides or skiffs, so they carry over to future
maps. A class's map ability is a key the game checks at its hooks (`on_move_cost`, `on_reveal`,
`on_loot`, `on_rest`, `on_shop`, `on_event`, `on_combat_start`).

An action is a card with dice slots:
- `req`: what dice it takes. `n` dice (0 for a free action), and any of `min`, `max`, `exact`,
  `odd`, `even` (each die), `pair`, `straight`, `sum_min` (the set), `face: "S"` (a shield face),
  `upto: True` (1..n dice).
- `tgt`: `foe`, `ally`, `other` (an ally but not yourself), `downed`, `self`, `foes`, `front`
  (the enemies' front row), `party`.
- `ops`: what it does, in order. Amounts are expressions over `v` (the first die), `sum`, `n`,
  `armor` (yours), `missing` (your missing HP) and `undead` (1 if the target is).
- `melee`: reaches only the enemies' front row while there is one. Heroes have no rows.
- `spell`: counts for Spell Echo. `once`: once per fight.

Learning an action you already have upgrades it (`strike+`): +2 to every amount and +1 to every
status that stacks (Burn, Poison, Sanctuary).
"""

# A passive's `mods` are read by the game where they apply. `override` replaces parts of an action.
PASSIVES = {
    # ---- Vanguard
    "thick_hide": {"name": "Bulwark Faces", "mods": {"shield_top": 1, "max_hp": 4}, "tags": ["bulwark"],
                   "text": "Your shield faces also count as your die's highest face (and still block). +4 max HP."},
    "iron_will": {"name": "Iron Will", "mods": {"stun_ward": 1, "first_hit_soak": 3},
                  "text": "Ignore the first Stun each fight. The first hit on you each round deals 3 less."},
    "steady": {"name": "Shieldwall", "mods": {"guard_share": 4, "shield_block": 2, "start_armor": 6}, "tags": ["bulwark"],
               "text": "Start each fight with 6 Armor. Your Guard also gives the guarded ally 4 Armor, your Taunt gives every ally 2 Armor, and your shield faces block 5."},
    "spiked_plate": {"name": "Spiked Plate", "mods": {"thorns": 3}, "tags": ["juggernaut"],
                     "text": "Enemies that hit you take 3 damage."},
    "overguard": {"name": "Overguard", "mods": {"overguard": 1, "start_armor": 5}, "tags": ["bulwark"],
                  "text": "Start each fight with 5 Armor, and half your Armor carries over into the next round."},
    "last_stand": {"name": "Last Stand", "mods": {"last_stand": 6}, "text": "While you're at half HP or less, gain 6 Armor each round."},
    "unbreakable": {"name": "Unbreakable", "cap": True, "mods": {"unbreakable": 1}, "tags": ["bulwark"],
                    "text": "Once per fight, a hit that would knock you down leaves you at 1 HP instead."},
    "avalanche": {"name": "Avalanche", "cap": True, "mods": {"override": {"retaliate": {"tgt": "front"}}},
                  "tags": ["juggernaut"], "text": "Retaliate hits every enemy in the front row."},

    # ---- Arcanist
    "overcharge": {"name": "Overcharge", "mods": {"overcharge": 2}, "text": "When one of your dice explodes, it adds 2 more."},
    "kindling": {"name": "Kindling", "mods": {"spell_burn": 1, "burn_bonus": 1}, "tags": ["elementalist"],
                 "text": "Your spells also Burn 1, and your Burns deal 1 more each tick."},
    "cold_snap": {"name": "Cold Snap", "mods": {"frozen_bonus": 3}, "tags": ["elementalist"],
                  "text": "Frozen enemies take +3 from your hits."},
    "malediction": {"name": "Malediction", "mods": {"debuff_ext": 1}, "tags": ["hexer"],
                    "text": "Weak, Vulnerable and Mark that you apply last a round longer."},
    "arcane_shield": {"name": "Arcane Shield", "mods": {"start_armor": 10}, "text": "Start each fight with 10 Armor."},
    "spell_echo": {"name": "Spell Echo", "mods": {"spell_echo": 1},
                   "text": "Your first spell each fight happens twice; the second time at half strength."},
    "cataclysm": {"name": "Cataclysm", "cap": True, "tags": ["elementalist"],
                  "mods": {"override": {"fireball": {"ops": [{"op": "dmg", "amt": "sum"}, {"op": "status", "s": "burn", "n": 2}]}}},
                  "text": "Fireball deals the full sum to every enemy, not half."},
    "grand_curse": {"name": "Grand Curse", "cap": True, "tags": ["hexer"], "mods": {"override": {"hex": {"tgt": "foes"}}},
                    "text": "Hex hits every enemy."},

    # ---- Mender
    "bedside_manner": {"name": "Diagnosis", "mods": {"seer_small": 1}, "tags": ["restoration"],
                       "text": "Your smallest die is a Seer die: it's rolled and shown while you plan, so you know what your heal will be."},
    "overflow": {"name": "Overflow", "mods": {"overflow": 1}, "tags": ["warding"], "text": "Healing beyond max HP becomes Armor."},
    "quick_hands": {"name": "Quick Hands", "mods": {"grant": "quick_lift"}, "tags": ["restoration"],
                    "text": "Learn Quick Lift: once until you rest, revive a knocked-down ally without a die."},
    "blessed_supplies": {"name": "Triage", "mods": {"triage": 1}, "tags": ["restoration"],
                         "text": "At the end of each round, your biggest unused die rolls and heals your most wounded ally by half of it."},
    "calm": {"name": "Calm", "mods": {"freeze_immune": 1}, "text": "Your dice can't be Frozen."},
    "miracle": {"name": "Miracle", "cap": True, "mods": {"miracle": 1}, "tags": ["restoration"],
                "text": "Once per run, a revive that would be used up isn't."},
    "aegis": {"name": "Aegis", "cap": True, "mods": {"aegis": 1}, "tags": ["warding"],
              "text": "Once your Sanctuary rolls 5+, every hit on the party deals 1 less for the rest of the fight."},
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
    "flee": {"name": "Flee", "req": {"n": 1, "min": 4}, "tgt": "self", "ops": [{"op": "flee"}],
             "text": "On 4+: escape the fight, back the way you came. Otherwise: you stay. Not in dungeons or boss fights."},

    # ---- Vanguard
    "strike": {"name": "Strike", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "v+1+armor//3"}],
               "text": "Deal the die +1, plus a third of your current Armor. Gain Armor first (Block, Guard) to hit harder."},
    "guard": {"name": "Guard", "req": {"n": 1}, "tgt": "other", "ops": [{"op": "guard"}, {"op": "armor", "amt": "v+2", "to": "self"}],
              "text": "Gain the die +2 as Armor. The next attack aimed at an ally this round hits you instead."},
    "taunt": {"cd": 2, "name": "Taunt", "req": {"n": 1}, "tgt": "self",
              "ops": [{"op": "taunt"}, {"op": "armor", "amt": "v+2"}, {"op": "status", "s": "thorns", "n": 2}],
              "tags": ["bulwark"], "text": "Gain the die +2 as Armor. Every enemy attack this round hits you instead of your allies, and each attacker takes 2."},
    "brace": {"name": "Brace", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v+2"}, {"op": "armor", "amt": "2", "to": "lowest"}],
              "tags": ["bulwark"], "text": "Gain the die +2 as Armor. Your ally with the lowest HP gains 2 Armor."},
    "rally_wall": {"cd": 2, "name": "Hold the Line", "req": {"n": 1}, "tgt": "self",
                   "ops": [{"op": "sanct", "n": 2}, {"op": "armor", "amt": "v+3"}],
                   "tags": ["bulwark"], "text": "Every hit on the party this round deals 2 less, and you gain the die +3 as Armor."},
    "shield_bash": {"cd": 2, "name": "Shield Bash", "req": {"n": 1, "min": 5, "or_face": "S"}, "tgt": "foe", "melee": True,
                    "ops": [{"op": "dmg", "amt": "max(v,3)+3"}, {"op": "status", "s": "stun", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                    "tags": ["juggernaut"], "text": "On a shield face or 5+: deal the die +3 (at least 6) and Stun the enemy. Otherwise: deal half the die."},
    "retaliate": {"name": "Retaliate", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "armor+v"}],
                  "tags": ["juggernaut"], "text": "Deal your current Armor plus the die."},
    "shoulder_charge": {"cd": 2, "name": "Shoulder Charge", "req": {"n": 1}, "tgt": "foe",
                        "ops": [{"op": "armor", "amt": "v", "to": "self"}, {"op": "dmg", "amt": "v+2"}, {"op": "drag"}],
                        "tags": ["juggernaut"], "text": "Any row: gain the die as Armor, deal the die +2, and drag the enemy to the front row."},

    # ---- Arcanist
    "bolt": {"name": "Bolt", "req": {"n": 1}, "tgt": "foe", "spell": True, "ops": [{"op": "dmg", "amt": "v"}],
             "text": "Deal the die. Reaches any row."},
    "channel": {"name": "Channel", "req": {"n": 2}, "tgt": "foe", "spell": True, "ops": [{"op": "dmg", "amt": "sum+2"}],
                "text": "Two dice as one blast: deal their sum +2."},
    "fireball": {"cd": 2, "name": "Fireball", "req": {"n": 2, "sum_min": 10}, "tgt": "foes", "spell": True, "tags": ["elementalist"],
                 "ops": [{"op": "dmg", "amt": "sum//2+2"}, {"op": "status", "s": "burn", "n": 2}],
                 "miss": [],
                 "text": "Two dice summing to 10+: every enemy takes half the sum +2 and Burns 2. Otherwise: nothing."},
    "frost_lance": {"name": "Frost Lance", "req": {"n": 1, "min": 5}, "tgt": "foe", "spell": True, "tags": ["elementalist"],
                    "ops": [{"op": "dmg", "amt": "v+3"}, {"op": "status", "s": "freeze", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                    "text": "On 5+: deal the die +3 and Freeze the enemy. Otherwise: deal half the die."},
    "chain_lightning": {"name": "Chain Lightning", "req": {"n": 1, "odd": True}, "tgt": "foe", "spell": True, "tags": ["elementalist"],
                        "ops": [{"op": "dmg", "amt": "v+3"}, {"op": "status", "s": "shock", "n": 1}, {"op": "dmg", "amt": "(v+3)//2", "to": "another"}],
                        "miss": [{"op": "dmg", "amt": "v"}],
                        "text": "On an odd number: deal the die +3, Shock the enemy, and the bolt arcs to another enemy for half. On an even one: deal the die."},
    "hex": {"name": "Hex", "req": {"n": 1}, "tgt": "foe", "spell": True,
            "ops": [{"op": "status", "s": "weak", "n": 1}, {"op": "status", "s": "vuln", "n": 1}],
            "tags": ["hexer"], "text": "Make an enemy Weak and Vulnerable."},
    "siphon": {"name": "Siphon", "req": {"n": 1, "min": 4}, "tgt": "foe", "spell": True, "tags": ["hexer"],
               "ops": [{"op": "dmg", "amt": "v+2", "leech": 0.5}], "miss": [{"op": "dmg", "amt": "v//2", "leech": 0.5}],
               "text": "On 4+: deal the die +2. Otherwise: deal half the die. Either way, heal half the damage dealt."},
    "doom": {"cd": 3, "name": "Doom", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": ["hexer"],
             "ops": [{"op": "status", "s": "doom", "n": "max(8,26-v)"}],
             "text": "At the end of next round, the enemy takes 26 minus the die (at least 8). The lower the roll, the bigger the hit."},

    # ---- Mender
    "mend": {"name": "Mend", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "heal", "amt": "v"}], "text": "Heal an ally by the die."},
    "lift": {"name": "Lift", "per_rest": True, "req": {"n": 1}, "tgt": "downed", "ops": [{"op": "lift", "amt": "v*2"}],
             "text": "Once until you rest: revive a knocked-down ally with twice the die in HP."},
    "renew": {"cd": 2, "name": "Renew", "req": {"n": 2}, "tgt": "party", "ops": [{"op": "heal", "amt": "sum//2+(sum//2)*pair"}],
              "tags": ["restoration"], "text": "Two dice: heal everyone in the party by half their sum, or by the full sum if they're a pair."},
    "lifeline": {"cd": 2, "name": "Lifeline", "req": {"n": 1, "min": 5}, "tgt": "ally", "tags": ["restoration"],
                 "ops": [{"op": "status", "s": "lifeline", "n": 1}], "miss": [{"op": "heal", "amt": "v//2"}],
                 "text": "On 5+: at the end of this round, the ally heals half their max HP. Otherwise: heal them half the die now."},
    "ward": {"name": "Ward", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "armor", "amt": "v+v//2"}],
             "tags": ["warding"], "text": "Give an ally Armor equal to one and a half times the die."},
    "sanctuary": {"cd": 2, "name": "Sanctuary", "req": {"n": 1, "min": 5}, "tgt": "party", "tags": ["warding"],
                  "ops": [{"op": "sanct", "n": 2}], "miss": [{"op": "sanct", "n": 1}],
                  "text": "On 5+: every hit on the party this round deals 2 less. Otherwise: 1 less."},
    "cleanse": {"name": "Cleanse", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "cleanse"}, {"op": "heal", "amt": "v"}],
                "text": "Remove Burn, Poison, Weak, Vulnerable, Mark and Root from an ally, and heal them by the die."},
    "smite": {"name": "Smite", "req": {"n": 1, "min": 4}, "tgt": "foe", "ops": [{"op": "dmg", "amt": "v+4+3*undead"}, {"op": "heal", "amt": "2", "to": "lowest"}],
              "miss": [{"op": "dmg", "amt": "v//2"}], "text": "Any row. On 4+: deal the die +4 (+3 more against the undead), and your ally with the lowest HP heals 2. Otherwise: deal half the die."},
    "quick_lift": {"name": "Quick Lift", "req": {"n": 0}, "tgt": "downed", "per_rest": True,
                   "ops": [{"op": "lift", "amt": "6"}], "text": "Once until you rest, no die needed: revive a knocked-down ally with 6 HP."},

    # ---- Duelist
    "slash_d": {"name": "Riposte Cut", "req": {"n": 1, "min": 3}, "tgt": "foe", "melee": True,
                "ops": [{"op": "dmg", "amt": "v+2"}], "miss": [{"op": "dmg", "amt": "v//2"}], "text": "On 3+: deal the die +2. Otherwise: deal half the die."},
    "parry": {"name": "Parry", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v"}, {"op": "status", "s": "riposte", "n": 2, "to": "self"}],
              "text": "Gain Armor equal to the die. If it fully blocks a hit this round, strike back for 2."},
    "twin_cut": {"name": "Twin Cut", "req": {"n": 2}, "tgt": "foe", "melee": True, "tags": ["flurry"],
                 "ops": [{"op": "dmg", "amt": "d+2+3*pair", "each": True}], "text": "Two dice: hit once with each for the die +2 (+3 more to each hit if they're a pair)."},
    "whirl": {"name": "Whirl", "req": {"n": 3, "upto": True}, "tgt": "foes", "tags": ["flurry"],
              "ops": [{"op": "dmg", "amt": "d+1", "each": True, "random": True}], "text": "Up to three dice: each hits a random enemy for the die +1."},
    "read_blade": {"name": "Read the Blade", "req": {"n": 1}, "tgt": "foe", "tags": ["precision"],
                   "ops": [{"op": "foresee"}, {"op": "dmg", "amt": "v+(v+2)*outroll"}],
                   "text": "The enemy rolls its dice now, in the open. Deal the die; if your die beat all of theirs, deal double +2 instead."},
    "lunge": {"cd": 2, "name": "Lunge", "req": {"n": 1, "min": 6}, "tgt": "foe", "tags": ["precision"],
              "ops": [{"op": "dmg", "amt": "v+10"}, {"op": "status", "s": "stun", "n": 1}], "miss": [],
              "text": "Any row. On a 6+: deal the die +10 and Stun the enemy. Otherwise: nothing."},
    "finisher": {"name": "Finisher", "req": {"n": 3}, "tgt": "foe", "melee": True, "tags": ["precision"],
                 "ops": [{"op": "dmg", "amt": "(sum+3)*(1+straight)"}], "text": "Three dice as one hit: deal their sum +3, doubled if they make a straight (like 3-4-5)."},
    "pinpoint": {"name": "Pinpoint", "req": {"n": 1}, "tgt": "foe", "tags": ["precision"],
                 "ops": [{"op": "dmg", "amt": "(v+1)*(1+aimed)", "pierce": True}],
                 "text": "Any row, ignoring Armor: deal the die +1, doubled if that enemy is aiming at you. Bait it, then punish it."},
    "feint": {"name": "Feint", "req": {"n": 1}, "tgt": "foe", "ops": [{"op": "weaken", "amt": "v"}],
              "text": "Lower an enemy's coming attack by the die."},
    "perfect_form": {"name": "Perfect Form", "req": {"n": 1}, "tgt": "self", "instant": True, "per_round": True,
                     "ops": [{"op": "setdie", "to": "max"}], "text": "Once a round: pick one of your dice; it will roll its highest face. That die stays free to use."},

    # ---- Berserker
    "hack_b": {"name": "Hack", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "v+1"}], "text": "Deal the die +1."},
    "bloodprice": {"name": "Bloodprice", "req": {"n": 1}, "tgt": "self", "instant": True,
                   "ops": [{"op": "selfdmg", "amt": "3"}, {"op": "bump", "amt": "2"}], "text": "Pay 3 HP: one of your dice rolls 2 higher. That die stays free to use."},
    "drink_deep": {"name": "Drink Deep", "req": {"n": 1, "min": 4}, "tgt": "foe", "melee": True, "tags": ["bloodlust"],
                   "ops": [{"op": "dmg", "amt": "v+2", "onkill": "v+2"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                   "text": "On 4+: deal the die +2, and heal that much if it kills. Otherwise: deal half the die."},
    "frenzy": {"name": "Frenzy", "req": {"n": 2}, "tgt": "foe", "melee": True, "tags": ["bloodlust"],
               "ops": [{"op": "dmg", "amt": "sum+3"}, {"op": "selfdmg", "amt": "2"}], "text": "Two dice as one hit: deal their sum +3. You take 2 damage."},
    "cleave": {"name": "Cleave", "req": {"n": 1, "min": 5}, "tgt": "front", "melee": True, "tags": ["rampage"],
               "ops": [{"op": "dmg", "amt": "v"}], "miss": [{"op": "dmg", "amt": "v//2", "to": "one"}],
               "text": "On 5+: deal the die to every enemy in the front row. Otherwise: deal half the die to one of them."},
    "earthshaker": {"cd": 2, "name": "Earthshaker", "req": {"n": 2, "sum_min": 12}, "tgt": "foes", "tags": ["rampage"],
                    "ops": [{"op": "dmg", "amt": "sum//2"}, {"op": "status", "s": "stun", "n": 1, "to": "random"}],
                    "miss": [],
                    "text": "Two dice summing to 12+: every enemy takes half the sum, and one is Stunned. Otherwise: nothing."},
    "reckless_swing": {"name": "Reckless Swing", "req": {"n": 1, "min": 8}, "tgt": "foe", "melee": True,
                       "ops": [{"op": "dmg", "amt": "v+12"}, {"op": "selfdmg", "amt": "3"}], "miss": [{"op": "selfdmg", "amt": "3"}],
                       "text": "On 8+: deal the die +12. Otherwise: nothing. You take 3 damage either way."},
    "howl": {"cd": 2, "name": "Howl", "req": {"n": 1}, "tgt": "foes", "ops": [{"op": "status", "s": "weak", "n": 1}],
             "text": "Every enemy is Weak this round."},

    # ---- Ranger
    "shoot_r": {"name": "Shoot", "req": {"n": 1}, "tgt": "foe", "ops": [{"op": "dmg", "amt": "v+1"}], "text": "Any row: deal the die +1."},
    "hunters_mark": {"name": "Hunter's Mark", "req": {"n": 1}, "tgt": "foe",
                     "ops": [{"op": "status", "s": "mark", "n": 1}, {"op": "dmg", "amt": "v//3"}],
                     "text": "Mark an enemy (every hit on it deals +3) and deal a third of the die."},
    "aimed_shot": {"name": "Aimed Shot", "req": {"n": 1, "min": 5}, "tgt": "foe", "tags": ["marksman"],
                   "ops": [{"op": "dmg", "amt": "v*2+1"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                   "text": "Any row. On 5+: deal twice the die +1. Otherwise: deal half the die."},
    "called_shot": {"name": "Called Shot", "req": {"n": 2, "marked": True}, "tgt": "foe", "tags": ["marksman"],
                    "ops": [{"op": "dmg", "amt": "sum+6*pair", "pierce": True}],
                    "text": "Two dice, only on a Marked enemy, ignoring Armor: deal their sum (+6 if they're a pair)."},
    "sic_em": {"name": "Sic 'Em", "req": {"n": 1}, "tgt": "foe", "tags": ["beastmaster"],
               "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "weak", "n": 1}], "text": "Your hawk dives at any row: deal the die and make the enemy Weak."},
    "pack_tactics": {"name": "Pack Tactics", "req": {"n": 1, "min": 4}, "tgt": "foe", "tags": ["beastmaster"],
                     "ops": [{"op": "dmg", "amt": "v+5"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                     "text": "Any row. On 4+: you and your hawk strike together for the die +5. Otherwise: deal half the die."},
    "spotter": {"cd": 3, "name": "Spotter", "req": {"n": 1}, "tgt": "foes", "tags": ["marksman"],
                "ops": [{"op": "foresee"}, {"op": "armor", "amt": "v//2", "to": "self"}],
                "text": "Every enemy rolls its dice now, in the open, so the party sees exactly what's coming. Gain half the die as Armor."},
    "volley": {"name": "Volley", "req": {"n": 3, "upto": True}, "tgt": "foes",
               "ops": [{"op": "dmg", "amt": "(d+1)//2+1", "each": True}],
               "text": "Up to three dice: every enemy takes half of each die (rounded up) +1. Made for crowds."},
    "covering_fire": {"name": "Covering Fire", "req": {"n": 1}, "tgt": "foe",
                      "ops": [{"op": "weaken", "amt": "v"}, {"op": "dmg", "amt": "v//2"}],
                      "text": "Any row: the enemy's coming attack drops by the die, and it takes half the die. Shoot whoever is about to hit hardest."},

    # ---- Scoundrel
    "stab": {"name": "Stab", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "v+3*(1-aimed)"}],
             "text": "Deal the die, +3 if the enemy is aiming at someone else."},
    "slip": {"name": "Slip", "req": {"n": 1, "min": 4}, "tgt": "self",
             "ops": [{"op": "status", "s": "dodge", "n": 1, "to": "self"}], "miss": [],
             "text": "On 4+: the next hit on you misses. Otherwise: nothing."},
    "envenom": {"name": "Envenom", "req": {"n": 1}, "tgt": "foe", "tags": ["poisons"],
                "ops": [{"op": "status", "s": "poison", "n": "max(1,v//2)"}], "text": "Poison an enemy for half the die."},
    "garrote": {"cd": 2, "name": "Garrote", "req": {"n": 1, "min": 5}, "tgt": "foe", "melee": True, "tags": ["poisons"],
                "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "status", "s": "stun", "n": 1, "if": "poisoned"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                "text": "On 5+: deal the die +2, and Stun the enemy if it's Poisoned. Otherwise: deal half the die."},
    "toxic_cloud": {"cd": 2, "name": "Toxic Cloud", "req": {"n": 2, "sum_min": 9}, "tgt": "foes", "tags": ["poisons"],
                    "ops": [{"op": "status", "s": "poison", "n": 3}], "miss": [],
                    "text": "Two dice summing to 9+: Poison every enemy for 3. Otherwise: nothing."},
    "pickpocket": {"cd": 3, "name": "Pickpocket", "req": {"n": 1, "min": 4}, "tgt": "foe", "tags": ["tricks"],
                   "ops": [{"op": "steal"}, {"op": "gold", "amt": "4"}], "miss": [{"op": "weaken", "amt": "v//2"}],
                   "text": "On 4+: steal the biggest die from an enemy's coming attack, and 4 gold. Otherwise: its attack drops by half the die."},
    "loaded_dice": {"name": "Loaded Dice", "req": {"n": 2}, "tgt": "self", "instant": True, "tags": ["tricks"],
                    "ops": [{"op": "loaded"}], "text": "Link two of your dice: the second rolls whatever the first does. Both stay free to use."},
    "smoke_bomb": {"cd": 2, "name": "Smoke Bomb", "req": {"n": 2, "pair": True}, "tgt": "party",
                   "ops": [{"op": "status", "s": "dodge", "n": 1}], "miss": [],
                   "text": "Two dice: if they're a pair, the next hit on each of you misses. Otherwise: nothing."},

    # ---- Herald
    "inspire": {"name": "Inspire", "req": {"n": 1}, "tgt": "other", "instant": True,
                "ops": [{"op": "inspire"}], "text": "Roll the die now: an ally's next die rolls higher by half of it (at least 2)."},
    "jab": {"name": "Cutting Words", "req": {"n": 1}, "tgt": "foe", "ops": [{"op": "dmg", "amt": "v"}], "text": "Any row: deal the die."},
    "hymn_of_valor": {"cd": 2, "name": "Hymn of Valor", "req": {"n": 2}, "tgt": "self", "instant": True, "tags": ["anthem"],
                      "ops": [{"op": "hymn"}], "text": "Two dice: every die the party rolls this round is 1 higher (2 higher if the two dice match)."},
    "lend_a_hand": {"name": "Lend a Hand", "req": {"n": 1}, "tgt": "other", "instant": True, "tags": ["anthem"],
                    "ops": [{"op": "give", "bonus": 2}], "text": "Give one of your dice to an ally to use this round, and it rolls 2 higher (a Seer die stays a Seer die)."},
    "crescendo": {"cd": 2, "name": "Crescendo", "req": {"n": 2}, "tgt": "party", "tags": ["anthem"],
                  "ops": [{"op": "status", "s": "crescendo", "n": 1}], "text": "Two dice: everyone's next damaging action deals 50% more."},
    "dirge": {"name": "Dirge", "req": {"n": 1}, "tgt": "foe", "tags": ["discord"],
              "ops": [{"op": "status", "s": "weak", "n": 1}, {"op": "dmg", "amt": "v//2"}], "text": "Make an enemy Weak and deal half the die."},
    "taunting_verse": {"name": "Taunting Verse", "req": {"n": 1, "min": 4}, "tgt": "foe", "tags": ["discord"],
                       "ops": [{"op": "retarget"}], "miss": [{"op": "weaken", "amt": "2"}],
                       "text": "On 4+: an enemy's attack turns on someone else (or no one). Otherwise: its attack drops by 2."},
    "cacophony": {"cd": 3, "name": "Cacophony", "req": {"n": 2, "sum_min": 8}, "tgt": "foe", "tags": ["discord"],
                  "ops": [{"op": "cancel"}], "miss": [{"op": "weaken", "amt": "sum//3"}],
                  "text": "Two dice summing to 8+: an enemy loses its turn. Otherwise: its attack drops by a third of the sum."},
    "requiem": {"name": "Requiem", "req": {"n": 0}, "tgt": "foe", "once": True, "ops": [{"op": "cancel"}],
                "text": "Once per fight, no die needed: cancel an enemy's coming action."},

    # ---- Alchemist
    "toss": {"name": "Toss", "req": {"n": 1}, "tgt": "foe", "bomb": True, "ops": [{"op": "dmg", "amt": "v", "splash": 1}],
             "text": "A bomb, any row: deal the die to one enemy and 1 to each enemy beside it."},
    "tonic_a": {"name": "Tonic", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "heal", "amt": "v+1"}], "text": "Heal an ally by the die +1."},
    "firebomb": {"cd": 2, "name": "Firebomb", "req": {"n": 1, "min": 4}, "tgt": "foe", "bomb": True, "tags": ["bombs"],
                 "ops": [{"op": "dmg", "amt": "v", "to": "row"}, {"op": "status", "s": "burn", "n": 1, "to": "row"}],
                 "miss": [{"op": "dmg", "amt": "v//2"}],
                 "text": "On 4+: deal the die to every enemy in the target's row, and Burn them 1. Otherwise: deal half the die to the target."},
    "acid_flask": {"name": "Acid Flask", "req": {"n": 1}, "tgt": "foe", "bomb": True, "tags": ["bombs"],
                   "ops": [{"op": "strip", "amt": "99"}, {"op": "status", "s": "vuln", "n": 2}, {"op": "dmg", "amt": "v"}],
                   "text": "A bomb, any row: strip all of an enemy's Armor, make it Vulnerable for 2 rounds, and deal the die. Throw it before the big hits."},
    "concussion": {"cd": 2, "name": "Concussion", "req": {"n": 1, "min": 5}, "tgt": "foe", "bomb": True, "tags": ["bombs"],
                   "ops": [{"op": "dmg", "amt": "3"}, {"op": "status", "s": "stun", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                   "text": "On 5+: deal 3 and Stun the enemy. Otherwise: deal half the die."},
    "bottle_it": {"cd": 3, "name": "Bottle It", "req": {"n": 1}, "tgt": "self", "instant": True, "tags": ["elixirs"],
                  "ops": [{"op": "bottle"}], "text": "Roll the die now and bottle a potion: a Tonic, or a Rum Ration on 5+."},
    "quicksilver": {"cd": 3, "name": "Quicksilver", "req": {"n": 1}, "tgt": "other", "instant": True, "tags": ["elixirs"],
                    "ops": [{"op": "reroll_ally"}], "text": "An ally gets 2 more automatic rerolls this fight, and their next die rolls 2 higher."},
    "panacea": {"cd": 2, "name": "Panacea", "req": {"n": 2, "sum_min": 8}, "tgt": "party", "tags": ["elixirs"],
                "ops": [{"op": "cleanse"}, {"op": "heal", "amt": "sum//2"}], "miss": [{"op": "cleanse"}],
                "text": "Two dice summing to 8+: remove every Burn, Poison, Weak, Vulnerable, Mark and Root from the party, and heal everyone half the sum. Otherwise: just remove them."},

    # ---- Warden
    "thornlash": {"name": "Thornlash", "req": {"n": 1}, "tgt": "foe",
                  "ops": [{"op": "dmg", "amt": "v+1"}, {"op": "status", "s": "root", "n": 1, "if": "v>=5"}], "text": "Any row: deal the die +1, and Root the enemy on 5+."},
    "sprout": {"name": "Sprout", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "summon", "k": "sapling", "hp": "v*2"}],
               "text": "Grow a sapling with twice the die in HP. Enemies can attack it instead of you."},
    "call_bear": {"cd": 3, "name": "Call Bear", "req": {"n": 2, "sum_min": 9}, "tgt": "self", "tags": ["grove"],
                  "ops": [{"op": "summon", "k": "bear"}], "miss": [],
                  "text": "Two dice summing to 9+: a bear joins the fight (15 HP, hits for 4 each round). Otherwise: nothing."},
    "swarm": {"cd": 2, "name": "Swarm", "req": {"n": 2}, "tgt": "self", "tags": ["grove"],
              "ops": [{"op": "summon", "k": "wasps", "hp": "sum"}], "text": "Two dice: summon a wasp swarm with their sum in HP that stings every enemy for 2 each round."},
    "regrowth": {"name": "Regrowth", "req": {"n": 1}, "tgt": "party", "tags": ["grove"],
                 "ops": [{"op": "heal", "amt": "v//2+1"}, {"op": "heal_summons", "amt": "v"}], "text": "Heal everyone in the party by half the die +1, and your summons by the die."},
    "entangle": {"name": "Entangle", "req": {"n": 1}, "tgt": "foe", "tags": ["thorns"],
                 "ops": [{"op": "status", "s": "root", "n": 1}, {"op": "status", "s": "weak", "n": 1}, {"op": "dmg", "amt": "v//2"}],
                 "text": "Root an enemy, make it Weak, and deal half the die."},
    "briar_wall": {"cd": 2, "name": "Briar Wall", "req": {"n": 2}, "tgt": "self", "tags": ["thorns"],
                   "ops": [{"op": "armor", "amt": "sum//3+2*pair", "to": "party"}, {"op": "status", "s": "thorns", "n": 2, "to": "party"}],
                   "text": "Two dice: the party gains a third of their sum as Armor (+2 more each if they're a pair), and attackers take 2 this round."},
    "strangle": {"name": "Strangle", "req": {"n": 1, "min": 3}, "tgt": "foe", "tags": ["thorns"],
                 "ops": [{"op": "dmg", "amt": "(v+2)*(1+rooted)"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                 "text": "Any row. On 3+: deal the die +2, doubled against a Rooted enemy. Otherwise: deal half the die."},
    "ancient_guardian": {"name": "Ancient Guardian", "req": {"n": 0}, "tgt": "self", "once": True,
                         "ops": [{"op": "summon", "k": "treant"}], "text": "Once per fight, no die needed: a treant rises to fight beside you (25 HP, hits for 5 each round)."},
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
        "name": "Vanguard", "hp": 50, "hp_lvl": 6, "role": "Tank",
        "dice": [D(6), [1, 2, 3, 4, "S", "S"]], "tags": ["bulwark", "juggernaut"],
        "map": {"key": "trailbreaker", "name": "Trailbreaker", "text": "Forest, hills and peaks cost you 1 move."},
        "start": ["strike", "guard", "overguard"], "weapon": "hand_axe", "armor": "padded_coat",
        "pool": ["taunt", "brace", "rally_wall", "shield_bash", "retaliate", "shoulder_charge",
                 "thick_hide", "iron_will", "steady", "spiked_plate", "last_stand",
                 "unbreakable", "avalanche"],
        "blurb": "Wades in, armoured, and takes the hits meant for everyone else.",
    },
    "arcanist": {
        "name": "Arcanist", "hp": 23, "hp_lvl": 4, "role": "Area damage and burst",
        "dice": [D(12), D(4)], "tags": ["elementalist", "hexer"],
        "map": {"key": "farsight", "name": "Farsight", "text": "See 3 hexes around you, and spot cursed items in loot."},
        "start": ["bolt", "channel"], "weapon": "oak_staff", "armor": "wool_robe",
        "pool": ["fireball", "frost_lance", "chain_lightning", "hex", "siphon", "doom",
                 "overcharge", "kindling", "cold_snap", "malediction", "arcane_shield", "spell_echo",
                 "cataclysm", "grand_curse"],
        "blurb": "Wild dice and big spells. Fragile; keep them covered.",
    },
    "mender": {
        "name": "Mender", "hp": 17, "hp_lvl": 3, "role": "Healer",
        "dice": [D(6), D(6)], "tags": ["restoration", "warding"],
        "map": {"key": "field_medic", "name": "Field Medic", "text": "Everyone who rests on your hex heals an extra 10% of their max HP."},
        "start": ["mend", "lift"], "weapon": "lantern_rod", "armor": "nurses_apron",
        "pool": ["renew", "lifeline", "ward", "sanctuary", "cleanse", "smite",
                 "bedside_manner", "overflow", "quick_hands", "blessed_supplies", "aura", "calm", "transfusion",
                 "miracle", "aegis"],
        "blurb": "Keeps the party standing, and picks them up when they don't.",
    },
}

PASSIVES.update({
    # ---- Duelist
    "momentum": {"name": "Momentum", "mods": {"momentum": 1}, "tags": ["flurry"], "text": "Each of your actions after the first in a round deals +1."},
    "keen_edge": {"name": "Keen Edge", "mods": {"keen_edge": 1}, "tags": ["precision"], "text": "Your 6s count as 7s."},
    "footwork": {"name": "Footwork", "mods": {"footwork": 2}, "text": "Back-row enemies deal 2 less to you."},
    "opportunist": {"name": "Opportunist", "mods": {"opportunist": 3}, "text": "+3 damage against Stunned or Rooted enemies."},
    "second_wind": {"name": "Steal Tempo", "mods": {"tempo": 1},
                    "text": "When your die beats every die an enemy has shown (after Read the Blade or Spotter), gain a free d6 this round."},
    "thousand_cuts": {"name": "Thousand Cuts", "cap": True, "tags": ["flurry"], "mods": {"override": {"twin_cut": {"req": {"n": 4, "upto": True}}}},
                      "text": "Twin Cut takes up to four dice."},
    "perfect_poise": {"name": "Perfect Poise", "cap": True, "tags": ["precision"], "mods": {"grant": "perfect_form"},
                      "text": "Learn Perfect Form: once a round, make one of your dice roll its highest face."},
    # ---- Berserker
    "rage": {"name": "Rage", "mods": {"rage": 1}, "text": "+1 damage for every 5 HP you're missing."},
    "bloodlust": {"name": "Bloodlust", "mods": {"kill_heal": 4, "kill_die": 6}, "tags": ["bloodlust"], "text": "Whenever you kill an enemy, heal 4. Your first kill each round also gives you a fresh d6 to keep swinging."},
    "wide_arcs": {"name": "Wide Arcs", "mods": {"wide_arcs": 1}, "tags": ["rampage"], "text": "Cleave also hits the back row, for half."},
    "pain_engine": {"name": "Pain Engine", "mods": {"pain_engine": 1}, "tags": ["bloodlust"], "text": "Each hit you take makes your first die next round roll 1 higher."},
    "thick_skull": {"name": "Thick Skull", "mods": {"max_hp": 4, "weak_immune": 1}, "text": "+4 max HP, and you can't be made Weak."},
    "undying_fury": {"name": "Undying Fury", "mods": {"undying": 12}, "tags": ["rampage"], "text": "When you're knocked down, hit whoever did it for 12."},
    "red_mist": {"name": "Red Mist", "cap": True, "mods": {"red_mist": 1}, "tags": ["bloodlust"], "text": "While you're under half HP, a third of the damage you deal heals you."},
    "unstoppable": {"name": "Unstoppable", "cap": True, "mods": {"unstoppable": 1}, "tags": ["rampage"], "text": "Cleave and Earthshaker ignore Armor, and Cleave reaches any row."},
    # ---- Ranger
    "eagle_eye": {"name": "Eagle Eye", "mods": {"eagle_eye": 1}, "tags": ["marksman"], "text": "A die showing its highest face deals half again as much damage."},
    "companion": {"name": "Companion", "mods": {"pet": 6}, "tags": ["beastmaster"], "text": "Your hawk adds a d6 to your dice every round."},
    "field_dressing": {"name": "Field Dressing", "mods": {"regen": 3}, "tags": ["beastmaster"], "text": "Heal 3 HP each round in fights."},
    "long_mark": {"name": "Long Mark", "mods": {"mark_ext": 1}, "tags": ["marksman"], "text": "Your Marks last a round longer."},
    "camouflage": {"name": "Camouflage", "mods": {"camouflage": 1}, "text": "Enemies attack you only when there's no one else to attack."},
    "deadeye": {"name": "Deadeye", "cap": True, "mods": {"deadeye": 1}, "tags": ["marksman"], "text": "Your biggest die is a Seer die that always shows its highest face."},
    "alpha": {"name": "Alpha", "cap": True, "mods": {"pet": 8, "pet_strike": 1}, "tags": ["beastmaster"], "text": "Your hawk's die is a d8, and it strikes the weakest enemy for 3 every round."},
    # ---- Scoundrel
    "virulence": {"name": "Virulence", "mods": {"poison_bonus": 1}, "tags": ["poisons"], "text": "Your Poisons are 1 stronger."},
    "wayfinder": {"name": "Wayfinder", "mods": {"move": 2, "wayfinder": 1}, "tags": ["tricks"], "text": "+2 move on the map, and you see further along your path."},
    "lucky_coin": {"name": "Lucky Coin", "mods": {"reroll": 1}, "tags": ["tricks"], "text": "+1 automatic reroll per fight: when an action misses, a die rolls again."},
    "sticky_fingers": {"name": "Sticky Fingers", "mods": {"sticky": 5}, "text": "+5 gold after every fight you win."},
    "evasive": {"name": "Evasive", "mods": {"evasive": 1}, "text": "The first hit on you each fight misses."},
    "backstab": {"name": "Backstab", "mods": {"backstab": 4}, "text": "+4 damage against enemies aiming at someone else."},
    "plague": {"name": "Plague", "cap": True, "mods": {"plague": 1}, "tags": ["poisons"], "text": "When a Poisoned enemy dies, its Poison spreads to another enemy."},
    "sleight_of_hand": {"name": "Sleight of Hand", "cap": True, "mods": {"sleight": 1}, "tags": ["tricks"],
                        "text": "Your linked dice each roll 1 higher."},
    # ---- Herald
    "battle_hymn": {"name": "Battle Hymn", "mods": {"hymn_aura": 1}, "tags": ["anthem"], "text": "While you're standing, the whole party deals +1 damage."},
    "second_verse": {"name": "Second Verse", "mods": {"second_verse": 1}, "tags": ["anthem"], "text": "Dice you give or boost get +1 more."},
    "heckler": {"name": "Heckler", "mods": {"heckler": 3}, "tags": ["discord"], "text": "Each enemy's first attack each fight deals 3 less."},
    "haggler": {"name": "Haggler", "mods": {"haggler": 1}, "text": "Sell items for 60% of their price instead of 40%."},
    "silver_voice": {"name": "Silver Voice", "mods": {"silver_voice": 1, "reroll": 1}, "text": "+1 to every event roll, and +1 automatic reroll per fight."},
    "anthem_of_kings": {"name": "Anthem of Kings", "cap": True, "mods": {"anthem": 1}, "tags": ["anthem"], "text": "Every ally rolls an extra d4 each round."},
    "requiem_cap": {"name": "Requiem", "cap": True, "mods": {"grant": "requiem"}, "tags": ["discord"], "text": "Learn Requiem: once per fight, cancel an enemy's coming action without a die."},
    # ---- Alchemist
    "volatile": {"name": "Volatile", "mods": {"bomb_bonus": 3}, "tags": ["bombs"], "text": "Your bombs deal +3."},
    "shrapnel": {"name": "Shrapnel", "mods": {"splash_bonus": 3}, "tags": ["bombs"], "text": "Your bombs' splash deals +3."},
    "distiller": {"name": "Distiller", "mods": {"distiller": 1}, "tags": ["elixirs"], "text": "Resting brews two potions instead of one."},
    "deep_pockets": {"name": "Deep Pockets", "mods": {"reroll": 1, "sticky": 3}, "text": "Spares for everything: +1 automatic reroll per fight, and +3 gold after every fight you win."},
    "safety_goggles": {"name": "Field Kit", "mods": {"heal_armor": 2, "burn_immune": 1}, "tags": ["elixirs"],
                       "text": "Your heals also give 2 Armor, and you can't be Burned."},
    "chain_reaction": {"name": "Chain Reaction", "cap": True, "mods": {"chain_reaction": 1}, "tags": ["bombs"],
                       "text": "Enemies killed by your bombs explode for half their max HP."},
    "philosophers_draught": {"name": "Philosopher's Draught", "cap": True, "mods": {"philosopher": 1}, "tags": ["elixirs"],
                             "text": "Bottle It makes two potions."},
    # ---- Warden
    "deep_roots": {"name": "Deep Roots", "mods": {"summon_hp": 0.5}, "tags": ["grove"], "text": "Your summons have 50% more HP."},
    "pack_leader": {"name": "Pack Leader", "mods": {"summon_cap": 1}, "tags": ["grove"], "text": "Keep one more summon at a time."},
    "overgrowth": {"name": "Overgrowth", "mods": {"root_ext": 1}, "tags": ["thorns"], "text": "Your Roots last a round longer."},
    "verdant": {"name": "Verdant", "mods": {"summon_regen": 2}, "text": "Your summons heal 2 HP each round."},
    "bark": {"name": "Bark", "mods": {"bark": 1}, "text": "Start every fight with a 10 HP sapling."},
    "guardian_call": {"name": "Ancient Guardian", "cap": True, "mods": {"grant": "ancient_guardian"}, "tags": ["grove"],
                      "text": "Learn Ancient Guardian: once per fight, a treant rises to fight beside you."},
    "crown_of_thorns": {"name": "Crown of Thorns", "cap": True, "mods": {"crown_thorns": 2}, "tags": ["thorns"],
                        "text": "Every enemy takes 2 damage at the start of each round."},
})

CLASSES.update({
    "duelist": {
        "name": "Duelist", "hp": 24, "hp_lvl": 3, "role": "Single-target damage",
        "dice": [D(8), D(6)], "tags": ["flurry", "precision"],
        "map": {"key": "ambush", "name": "Ambush", "text": "A fight you start gives the party a free first round."},
        "start": ["slash_d", "parry"], "weapon": "rapier", "armor": "padded_coat",
        "pool": ["twin_cut", "whirl", "lunge", "finisher", "pinpoint", "feint", "read_blade",
                 "momentum", "keen_edge", "footwork", "opportunist", "second_wind",
                 "thousand_cuts", "perfect_poise"],
        "blurb": "Fast, precise and deadly against one target at a time.",
    },
    "berserker": {
        "name": "Berserker", "hp": 30, "hp_lvl": 3, "role": "High-risk damage",
        "dice": [D(10), D(4)], "tags": ["bloodlust", "rampage"],
        "map": {"key": "forage", "name": "Forage", "text": "Resting at a camp heals you fully."},
        "start": ["hack_b", "bloodprice"], "weapon": "great_axe", "armor": "hide_vest",
        "pool": ["drink_deep", "frenzy", "cleave", "earthshaker", "reckless_swing", "howl",
                 "rage", "bloodlust", "wide_arcs", "pain_engine", "thick_skull", "undying_fury",
                 "red_mist", "unstoppable"],
        "blurb": "Trades blood for power, and gets more dangerous the more it's hurt.",
    },
    "ranger": {
        "name": "Ranger", "hp": 24, "hp_lvl": 4, "role": "Ranged damage",
        "dice": [D(8), D(6)], "tags": ["marksman", "beastmaster"],
        "map": {"key": "tracker", "name": "Tracker", "text": "+1 move on land, and you see enemies 2 hexes further off."},
        "start": ["shoot_r", "hunters_mark"], "weapon": "short_bow", "armor": "padded_coat",
        "pool": ["aimed_shot", "called_shot", "sic_em", "pack_tactics", "volley", "covering_fire", "spotter",
                 "eagle_eye", "companion", "field_dressing", "long_mark", "camouflage",
                 "deadeye", "alpha"],
        "blurb": "Picks enemies off from afar, with a hawk for company.",
    },
    "scoundrel": {
        "name": "Scoundrel", "hp": 22, "hp_lvl": 3, "role": "Debuffs and loot",
        "dice": [D(6), D(6)], "tags": ["poisons", "tricks"],
        "map": {"key": "light_fingers", "name": "Light Fingers", "text": "One more choice whenever you loot a wreck or a chest."},
        "start": ["stab", "slip", "evasive"], "weapon": "daggers", "armor": "padded_coat",
        "pool": ["envenom", "garrote", "toxic_cloud", "pickpocket", "loaded_dice", "smoke_bomb",
                 "virulence", "wayfinder", "lucky_coin", "sticky_fingers", "backstab",
                 "plague", "sleight_of_hand"],
        "blurb": "Poisons, dirty tricks and loaded dice. Always comes out ahead.",
    },
    "herald": {
        "name": "Herald", "hp": 18, "hp_lvl": 3, "role": "Buffs for allies",
        "dice": [D(6), D(4)], "tags": ["anthem", "discord"],
        "map": {"key": "silver_tongue", "name": "Silver Tongue", "text": "Shops and inns are 20% cheaper, and some events open up."},
        "start": ["inspire", "jab"], "weapon": "lute", "armor": "padded_coat",
        "pool": ["hymn_of_valor", "lend_a_hand", "crescendo", "dirge", "taunting_verse", "cacophony",
                 "battle_hymn", "second_verse", "heckler", "haggler", "silver_voice", "encore",
                 "anthem_of_kings", "requiem_cap"],
        "blurb": "Makes everyone else's dice better, and throws enemies off their stride.",
    },
    "alchemist": {
        "name": "Alchemist", "hp": 21, "hp_lvl": 3, "role": "Items and gadgets",
        "dice": [D(6), D(6)], "tags": ["bombs", "elixirs"],
        "map": {"key": "brewer", "name": "Brewer", "text": "Brew a potion whenever you rest."},
        "start": ["toss", "tonic_a"], "weapon": "sling", "armor": "leather_apron",
        "pool": ["firebomb", "acid_flask", "concussion", "bottle_it", "quicksilver", "panacea",
                 "volatile", "shrapnel", "potency", "distiller", "deep_pockets", "safety_goggles",
                 "chain_reaction", "philosophers_draught"],
        "blurb": "Bombs for the enemy, potions for friends.",
    },
    "warden": {
        "name": "Warden", "hp": 26, "hp_lvl": 3, "role": "Summons and control",
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
    "wasps": {"name": "Wasp Swarm", "hp": 6, "atk": 2, "all": True, "row": "back"},
    "treant": {"name": "Treant", "hp": 25, "atk": 5, "row": "front"},
}
SUMMON_CAP = 2

# Dice verbs and the Mender's rework: actions that change dice rather than add numbers.
ACTIONS.update({
    "encore": {"name": "Counterpoint", "req": {"n": 1}, "tgt": "self", "instant": True, "tags": ["anthem"],
               "ops": [{"op": "flip"}], "text": "Roll one of your dice now, in the open. If it lands in the bottom half, flip it to the opposite face, +1 (a 2 on a d6 becomes a 6). That die stays free to use."},
    "potency": {"name": "Splitting Flask", "req": {"n": 1}, "tgt": "self", "instant": True, "tags": ["elixirs"],
                "ops": [{"op": "split"}], "text": "Split one of your dice into two dice half its size (a d8 becomes two d4s)."},
    "bramble_skin": {"name": "Grafting", "req": {"n": 2}, "tgt": "self", "instant": True, "tags": ["grove"],
                     "ops": [{"op": "merge"}], "text": "Graft two of your dice into one: their sizes add up (a d6 and a d4 make a d10)."},
    "aura": {"name": "Second Opinion", "req": {"n": 1}, "tgt": "other", "instant": True, "tags": ["warding"],
             "ops": [{"op": "second_opinion"}], "text": "An ally's biggest unrolled die rolls twice now, in the open, and keeps the better result."},
    "transfusion": {"name": "Transfusion", "req": {"n": 1}, "tgt": "other", "instant": True, "tags": ["restoration"],
                    "ops": [{"op": "transfusion"}], "text": "Roll the die now: heal an ally by that much +2, and their next die rolls 2 higher."},
})

GENERIC = ["block", "flee"]

# Guard dice (armor and some trinkets) only go on defensive actions: ones that do nothing but
# protect, heal, move or blunt the enemies' attacks.
DEF_OPS = {"armor", "guard", "heal", "lift", "taunt", "flee", "sanct", "cleanse", "heal_summons", "weaken", "retarget"}
DEF_STATUS = {"dodge", "riposte", "thorns", "lifeline"}


def is_defensive(a):
    ops = list(a["ops"]) + list(a.get("miss", []))
    return bool(ops) and not a.get("instant") and all(
        o["op"] in DEF_OPS or (o["op"] == "status" and o["s"] in DEF_STATUS) for o in ops)


# Cooldowns: only each class's basic action (the Vanguard's Brace too: a tank needs a defence it can
# count on every round), Block, Flee and Lift (plus weapon actions, in
# items.py) can be used every round. Everything else waits at least a round after use, so a hero
# can't win with one strong skill on repeat. `cd` N means usable every N rounds.
FREE = {"strike", "brace", "bolt", "slash_d", "hack_b", "shoot_r", "stab", "jab", "thrust", "toss", "thornlash",
        "block", "flee"}  # the Mender's free action is its weapon's Flare; Mend cools, Lift is once per rest
BIG = {"finisher": 3, "called_shot": 3, "reckless_swing": 3, "howl": 3, "mend": 3}

for _k, _a in ACTIONS.items():
    _a["def"] = is_defensive(_a)
    if _k not in FREE and not _a.get("once") and not _a.get("per_rest"):
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


# The card face of every action, for reading at a glance: (icon, effect, effect on a miss or None).
# The requirement badge comes from `req`; the full rules stay in `text`, shown in the tooltip.
# "die" is the die you put on it, "sum" the dice added up.
SHORT = {
    "block": ("shield", "die as Armor", None), "flee": ("boot", "run away", "stay"),
    "strike": ("sword", "die +1 + ⅓ Armor", None), "guard": ("shield", "take an ally's hit · die +2 Armor", None),
    "taunt": ("target", "all attacks on you · die +2 Armor · thorns 2", None), "brace": ("shield", "die +2 Armor · +2 to the weakest", None),
    "rally_wall": ("shield", "party hits −2 · die +3 Armor", None), "shield_bash": ("sword", "die +3 (6+) · Stun", "½ die"),
    "retaliate": ("sword", "your Armor + die", None), "shoulder_charge": ("sword", "die Armor · die +2 · drag", None),
    "bolt": ("sword", "die", None), "channel": ("sword", "sum +2", None),
    "fireball": ("flame", "all: ½ sum +2 · Burn 2", "nothing"), "frost_lance": ("snow", "die +3 · Freeze", "½ die"),
    "chain_lightning": ("bolt", "die +3 · Shock · arcs ½", "die"), "hex": ("down", "Weak + Vulnerable", None),
    "siphon": ("sword", "die +2 · heal half", "½ die · heal half"), "doom": ("skull", "26 − die, next round", None),
    "mend": ("plus", "heal die", None), "lift": ("hand", "revive: 2× die", None),
    "renew": ("plus", "party: heal ½ sum · pair: sum", None), "lifeline": ("plus", "heal ½ max HP at round end", "heal ½ die"),
    "ward": ("shield", "ally: 1½× die Armor", None), "sanctuary": ("shield", "party: hits −2", "hits −1"),
    "cleanse": ("plus", "cure + heal die", None), "smite": ("sword", "die +4 · ally heals 2", "½ die"),
    "quick_lift": ("hand", "revive with 6 HP", None),
    "slash_d": ("sword", "die +2", "½ die"), "parry": ("shield", "die Armor · riposte 2", None),
    "twin_cut": ("sword", "two hits, each die +2", None), "whirl": ("sword", "each die +1, random foes", None),
    "read_blade": ("eye", "reveal · die, 2× +2 if you beat it", None), "lunge": ("sword", "die +10 · Stun", "nothing"),
    "finisher": ("sword", "sum +3 · straight 2×", None), "pinpoint": ("target", "die +1, 2× if it aims at you", None),
    "feint": ("down", "its attack −die", None), "perfect_form": ("star", "a die rolls its top face", None),
    "hack_b": ("sword", "die +1", None), "bloodprice": ("heart", "−3 HP · a die +2", None),
    "drink_deep": ("sword", "die +2 · heal on kill", "½ die"), "frenzy": ("sword", "sum +3 · take 2", None),
    "cleave": ("sword", "die to front row", "½ die to one"), "earthshaker": ("crack", "all: ½ sum · Stun one", "nothing"),
    "reckless_swing": ("sword", "die +12 · take 3", "take 3"), "howl": ("down", "all enemies Weak", None),
    "shoot_r": ("sword", "die +1", None), "hunters_mark": ("target", "Mark · ⅓ die", None),
    "aimed_shot": ("target", "2× die +1", "½ die"), "called_shot": ("target", "sum · pair +6 · pierce", None),
    "sic_em": ("sword", "die · Weak", None), "pack_tactics": ("sword", "die +5", "½ die"),
    "spotter": ("eye", "reveal all enemy dice · ½ die Armor", None), "volley": ("sword", "all: ½ each die +1", None),
    "covering_fire": ("down", "its attack −die · ½ die", None),
    "stab": ("sword", "die, +3 if not aimed at you", None), "slip": ("boot", "dodge next hit", "nothing"),
    "envenom": ("drop", "Poison ½ die", None), "garrote": ("sword", "die +2 · Stun if Poisoned", "½ die"),
    "toxic_cloud": ("drop", "all: Poison 3", "nothing"), "pickpocket": ("hand", "steal its biggest die · 4 gold", "its attack −½ die"),
    "loaded_dice": ("link", "link two dice", None), "smoke_bomb": ("boot", "party dodges next hit", "nothing"),
    "inspire": ("up", "ally's next die +½", None), "jab": ("sword", "die", None),
    "hymn_of_valor": ("up", "party dice +1 · match +2", None), "lend_a_hand": ("hand", "give a die, +2", None),
    "crescendo": ("up", "party's next hit +50%", None), "dirge": ("down", "Weak · ½ die", None),
    "taunting_verse": ("arrow", "its attack swings away", "its attack −2"), "cacophony": ("x", "it loses its turn", "its attack −⅓ sum"),
    "requiem": ("x", "cancel an intent", None),
    "toss": ("sword", "die · splash 1", None), "tonic_a": ("plus", "heal die +1", None),
    "firebomb": ("flame", "die to its row · Burn 1", "½ die"), "acid_flask": ("drop", "strip Armor · Vuln 2 · die", None),
    "concussion": ("sword", "3 + Stun", "½ die"), "bottle_it": ("drop", "brew a potion", None),
    "quicksilver": ("refresh", "ally +2 rerolls · next die +2", None), "panacea": ("plus", "party: cure + heal ½ sum", "cure"),
    "thornlash": ("sword", "die +1 · 5+: Root", None), "sprout": ("spark", "sapling, 2× die HP", None),
    "call_bear": ("spark", "a bear joins", "nothing"), "swarm": ("spark", "wasps: sum HP, sting all 2", None),
    "regrowth": ("plus", "party: heal ½ die +1", None), "entangle": ("root", "Root + Weak · ½ die", None),
    "briar_wall": ("shield", "party: ⅓ sum Armor · thorns 2", None), "strangle": ("sword", "die +2, 2× if Rooted", "½ die"),
    "ancient_guardian": ("spark", "a treant rises", None),
    # weapon actions
    "hack": ("sword", "die +3", "½ die"), "zap": ("bolt", "die · Shock", None), "flare": ("target", "½ die · Mark", None),
    "thrust": ("sword", "die", None), "harpoon": ("sword", "die · drag to front", "½ die"),
    "shoot": ("sword", "die +4", "½ die"), "slash": ("sword", "die +1", None), "crush": ("sword", "die +5", "½ die"),
    "sweep": ("sword", "front row: ½ sum · pair +3", None), "tidal": ("wave", "all: ½ sum · pair +3", None),
    "storm_bolt": ("bolt", "die +4 · Shock", "nothing"), "venom_stab": ("drop", "½ die · Poison 2", None),
    "blessing": ("plus", "heal die · 2 Armor", None),
    "pass_die": ("spark", "give a die to an ally", None),
    "encore": ("refresh", "flip a low die, +1", None), "potency": ("spark", "split a die in two", None),
    "bramble_skin": ("spark", "merge two dice", None), "aura": ("refresh", "ally's die: best of two", None),
    "transfusion": ("plus", "heal die +2 · ally's next die +2", None),
}

# Cross-hero combos (the numbers are in combat.py): what two heroes do together.
COMBOS = {
    "pincer": {"name": "Pincer", "text": "Your first hit on an enemy an ally already hit this round: +2 damage, or +5 if one of your "
                                       "dice shows a number one of theirs showed. Once per enemy per round."},
    "covered": {"name": "Covered", "text": "Your first hit after an ally Guards or Taunts for you this round: +3 damage."},
    "shatter": {"name": "Shatter", "text": "Hit an enemy an ally Froze: the ice breaks for +4 damage (and the Freeze ends)."},
    "wildfire": {"name": "Wildfire", "text": "Burn meets an ally's Poison on one enemy (or Poison meets Burn): it erupts "
                                         "for Burn + Poison, and half that to every other enemy. Once per enemy."},
}
