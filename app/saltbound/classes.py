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
    "overguard": {"name": "Overguard", "mods": {"start_armor": 5}, "tags": ["bulwark"],
                  "text": "Start each fight with 5 Armor."},
    # what Overguard and Strike once did for every Vanguard, now level-ups (owner's request)
    "interpose": {"name": "Interpose", "tags": ["bulwark"],
                  "mods": {"override": {"guard": {"cd": 0, "ops": [{"op": "guard"}],
                                                  "text": "The next attack aimed at an ally this round hits you instead."}}},
                  "text": "Guard can be used every round, but gives you no Armor."},
    "iron_stance": {"name": "Iron Stance", "mods": {"overguard": 1}, "tags": ["bulwark"],
                    "text": "A third of your Armor carries over into the next round."},
    "shield_weight": {"name": "Shield Weight", "tags": ["juggernaut"],
                      "mods": {"override": {"strike": {"ops": [{"op": "dmg", "amt": "v+2+armor//3"}],
                                                       "text": "Deal the die +2, plus a third of your current Armor."}}},
                      "text": "Strike also deals a third of your current Armor. Gain Armor first (Block, Guard) to hit harder."},
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
    "strike": {"name": "Strike", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "v+2"}],
               "text": "Deal the die +2."},
    "guard": {"name": "Guard", "req": {"n": 1}, "tgt": "other", "ops": [{"op": "guard"}, {"op": "armor", "amt": "v+2", "to": "self"}],
              "text": "Gain the die +2 as Armor. The next attack aimed at an ally this round hits you instead."},
    "taunt": {"cd": 2, "name": "Taunt", "req": {"n": 1}, "tgt": "self",
              "ops": [{"op": "taunt"}, {"op": "armor", "amt": "v+2"}, {"op": "status", "s": "thorns", "n": 2}],
              "tags": ["bulwark"], "text": "Gain the die +2 as Armor. Every enemy attack this round hits you instead of your allies, and each attacker takes 2."},
    "brace": {"name": "Brace", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v+1"}, {"op": "armor", "amt": "2", "to": "lowest"}],
              "tags": ["bulwark"], "text": "Gain the die +1 as Armor. Your ally with the lowest HP gains 2 Armor."},
    "rally_wall": {"cd": 2, "name": "Hold the Line", "req": {"n": 1}, "tgt": "self",
                   "ops": [{"op": "sanct", "n": 1}, {"op": "armor", "amt": "v+2"}],
                   "tags": ["bulwark"], "text": "Every hit on the party this round deals 1 less, and you gain the die +2 as Armor."},
    "shield_bash": {"cd": 3, "name": "Shield Bash", "req": {"n": 1, "min": 6, "or_face": "S"}, "tgt": "foe", "melee": True,
                    "ops": [{"op": "dmg", "amt": "max(v,3)+3"}, {"op": "status", "s": "stun", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                    "tags": ["juggernaut"], "text": "On a shield face or 6+: deal the die +3 (at least 6) and Stun the enemy. Otherwise: deal half the die."},
    "retaliate": {"name": "Retaliate", "req": {"n": 1}, "tgt": "foe", "melee": True, "ops": [{"op": "dmg", "amt": "armor+v"}],
                  "tags": ["juggernaut"], "text": "Deal your current Armor plus the die."},
    # spend your defence for reach: the Armor you throw is gone
    "shield_throw": {"cd": 2, "name": "Shield Throw", "req": {"n": 1}, "tgt": "foe", "tags": ["juggernaut"],
                     "ops": [{"op": "dmg", "amt": "v+armor//2"}, {"op": "armor", "amt": "-(armor//2)", "to": "self"}],
                     "text": "Any row: deal the die plus half your Armor, then lose that half of your Armor."},
    "rallying_shout": {"cd": 3, "name": "Rallying Shout", "req": {"n": 2}, "tgt": "party", "tags": ["bulwark"],
                       "ops": [{"op": "cleanse"}, {"op": "armor", "amt": "sum//2"}],
                       "text": "Two dice: the whole party shakes off Burn, Poison, Weak, Hex and the rest, and gains half the sum as Armor."},
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
    "chain_lightning": {"name": "Chain Lightning", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": ["elementalist"],
                        "ops": [{"op": "dmg", "amt": "v+3"}, {"op": "status", "s": "shock", "n": 1}, {"op": "dmg", "amt": "(v+3)//2", "to": "another"}],
                        "text": "Deal the die +3 and Shock the enemy; the bolt arcs to another enemy for half."},
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
    "mend": {"name": "Mend", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "heal", "amt": "v+3"}], "text": "Heal an ally by the die +3."},
    "lift": {"name": "Lift", "per_rest": True, "req": {"n": 1}, "tgt": "downed", "ops": [{"op": "lift", "amt": "v*2"}],
             "text": "Once until you rest: revive a knocked-down ally with twice the die in HP."},
    "renew": {"cd": 2, "name": "Renew", "req": {"n": 2}, "tgt": "party", "ops": [{"op": "heal", "amt": "sum//2+(sum//2)*pair"}],
              "tags": ["restoration"], "text": "Two dice: heal everyone in the party by half their sum, or by the full sum if they're a pair."},
    "lifeline": {"cd": 2, "name": "Lifeline", "req": {"n": 1, "min": 5}, "tgt": "ally", "tags": ["restoration"],
                 "ops": [{"op": "status", "s": "lifeline", "n": 1}], "miss": [{"op": "heal", "amt": "v//2"}],
                 "text": "On 5+: at the end of this round, the ally heals half their max HP. Otherwise: heal them half the die now."},
    "ward": {"name": "Ward", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "armor", "amt": "v*2"}],
             "tags": ["warding"], "text": "Give an ally Armor equal to twice the die."},
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
                "ops": [{"op": "dmg", "amt": "v+2+3*aimed"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                "text": "On 3+: deal the die +2, and 3 more if that enemy is aiming at you. Otherwise: deal half the die."},
    "parry": {"name": "Parry", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v"}, {"op": "status", "s": "riposte", "n": 4, "to": "self"}],
              "text": "Gain Armor equal to the die. If it fully blocks a hit this round, strike back for 4."},
    "twin_cut": {"name": "Twin Cut", "req": {"n": 2}, "tgt": "foe", "melee": True, "tags": ["flurry"],
                 "ops": [{"op": "dmg", "amt": "d+4+3*pair", "each": True}], "text": "Two dice: hit once with each for the die +4 (+3 more to each hit if they're a pair)."},
    "whirl": {"name": "Whirl", "req": {"n": 3, "upto": True}, "tgt": "foes", "tags": ["flurry"],
              "ops": [{"op": "dmg", "amt": "d+1", "each": True, "random": True}], "text": "Up to three dice: each hits a random enemy for the die +1."},
    "read_blade": {"name": "Read the Blade", "req": {"n": 1}, "tgt": "foe", "tags": ["precision"],
                   "ops": [{"op": "foresee"}, {"op": "dmg", "amt": "v+(v+2)*outroll"}],
                   "text": "The enemy rolls its dice now, in the open. Deal the die; if your die beat all of theirs, deal double +2 instead."},
    "lunge": {"cd": 2, "name": "Lunge", "req": {"n": 1, "min": 6}, "tgt": "foe", "tags": ["precision"],
              "ops": [{"op": "dmg", "amt": "v+10"}], "miss": [],
              "text": "Any row. On a 6+: deal the die +10. Otherwise: nothing."},
    "finisher": {"name": "Finisher", "req": {"n": 3}, "tgt": "foe", "melee": True, "tags": ["precision"],
                 "ops": [{"op": "dmg", "amt": "(sum+6)*(1+straight)"}], "text": "Three dice as one hit: deal their sum +6, doubled if they make a straight (like 3-4-5)."},
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
                   "ops": [{"op": "dmg", "amt": "v+4", "onkill": "v+4"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                   "text": "On 4+: deal the die +4, and heal that much if it kills. Otherwise: deal half the die."},
    "frenzy": {"name": "Frenzy", "req": {"n": 2}, "tgt": "foe", "melee": True, "tags": ["bloodlust"],
               "ops": [{"op": "dmg", "amt": "sum+3"}, {"op": "selfdmg", "amt": "2"}], "text": "Two dice as one hit: deal their sum +3. You take 2 damage."},
    "cleave": {"name": "Cleave", "req": {"n": 1, "min": 5}, "tgt": "front", "melee": True, "tags": ["rampage"],
               "ops": [{"op": "dmg", "amt": "v"}], "miss": [{"op": "dmg", "amt": "v//2", "to": "one"}],
               "text": "On 5+: deal the die to every enemy in the front row. Otherwise: deal half the die to one of them."},
    "earthshaker": {"cd": 2, "name": "Earthshaker", "req": {"n": 2, "sum_min": 12}, "tgt": "foes", "tags": ["rampage"],
                    "ops": [{"op": "dmg", "amt": "sum//2"}, {"op": "weaken", "amt": "sum//2", "to": "random"}],
                    "miss": [],
                    "text": "Two dice summing to 12+: every enemy takes half the sum, and one enemy's coming attack drops by half the sum. Otherwise: nothing."},
    "reckless_swing": {"name": "Reckless Swing", "req": {"n": 1, "min": 7}, "tgt": "foe", "melee": True,
                       "ops": [{"op": "dmg", "amt": "v+12"}, {"op": "selfdmg", "amt": "2"}],
                       "miss": [{"op": "dmg", "amt": "v//2"}, {"op": "selfdmg", "amt": "2"}],
                       "text": "On 7+: deal the die +12. Otherwise: deal half the die. You take 2 damage either way."},
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
                    "ops": [{"op": "dmg", "amt": "sum+8+6*pair", "pierce": True}],
                    "text": "Two dice, only on a Marked enemy, ignoring Armor: deal their sum +8 (+6 more if they're a pair)."},
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
                "ops": [{"op": "status", "s": "poison", "n": "v//2+1"}, {"op": "dmg", "amt": "v//2"}],
                "text": "Poison an enemy for half the die +1, and deal half the die."},
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
    "mocking_jest": {"name": "Mocking Jest", "req": {"n": 1}, "tgt": "foe", "tags": ["discord"],
                     "ops": [{"op": "dmg", "amt": "v+1"}, {"op": "status", "s": "mark", "n": 1}],
                     "text": "Any row: deal the die +1 and Mark the enemy (every hit on it deals 3 more)."},
    "rousing_chorus": {"cd": 3, "name": "Rousing Chorus", "req": {"n": 1}, "tgt": "self", "instant": True, "tags": ["anthem"],
                       "ops": [{"op": "chorus"}],
                       "text": "Roll the die now: every ally's next die rolls higher by half of it (at least 2)."},
    "hymn_of_valor": {"cd": 2, "name": "Hymn of Valor", "req": {"n": 2}, "tgt": "self", "instant": True, "tags": ["anthem"],
                      "ops": [{"op": "hymn"}], "text": "Two dice: every die the party rolls this round is 2 higher (3 higher if the two dice match)."},
    "lend_a_hand": {"name": "Lend a Hand", "req": {"n": 1}, "tgt": "other", "instant": True, "tags": ["anthem"],
                    "ops": [{"op": "give", "bonus": 4}], "text": "Give one of your dice to an ally to use this round, and it rolls 4 higher (a Seer die stays a Seer die)."},
    "crescendo": {"cd": 3, "name": "Crescendo", "req": {"n": 1}, "tgt": "party", "tags": ["anthem"],
                  "ops": [{"op": "status", "s": "crescendo", "n": 1}], "text": "Everyone's next damaging action deals 50% more."},
    "dirge": {"name": "Dirge", "req": {"n": 1}, "tgt": "foe", "tags": ["discord"],
              "ops": [{"op": "status", "s": "weak", "n": 1}, {"op": "dmg", "amt": "v//2"}], "text": "Make an enemy Weak and deal half the die."},
    "taunting_verse": {"name": "Taunting Verse", "req": {"n": 1, "min": 3}, "tgt": "foe", "tags": ["discord"],
                       "ops": [{"op": "retarget"}, {"op": "status", "s": "mark", "n": 1}], "miss": [{"op": "weaken", "amt": "3"}],
                       "text": "On 3+: an enemy's attack turns on someone else (or no one), and it's Marked. Otherwise: its attack drops by 3."},
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
    "concussion": {"cd": 3, "name": "Concussion", "req": {"n": 1, "min": 6}, "tgt": "foe", "bomb": True, "tags": ["bombs"],
                   "ops": [{"op": "dmg", "amt": "3"}, {"op": "status", "s": "stun", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                   "text": "On a 6: deal 3 and Stun the enemy. Otherwise: deal half the die."},
    "bottle_it": {"cd": 3, "name": "Bottle It", "req": {"n": 1}, "tgt": "self", "instant": True, "tags": ["elixirs"],
                  "ops": [{"op": "bottle"}], "text": "Roll the die now and bottle a potion: a Tonic, or a Rum Ration on 5+."},
    "quicksilver": {"cd": 2, "name": "Quicksilver", "req": {"n": 1}, "tgt": "other", "instant": True, "tags": ["elixirs"],
                    "ops": [{"op": "reroll_ally"}], "text": "An ally gets 2 more automatic rerolls this fight, and their next die rolls 3 higher."},
    "panacea": {"cd": 2, "name": "Panacea", "req": {"n": 2, "sum_min": 8}, "tgt": "party", "tags": ["elixirs"],
                "ops": [{"op": "cleanse"}, {"op": "heal", "amt": "sum//2"}], "miss": [{"op": "cleanse"}],
                "text": "Two dice summing to 8+: remove every Burn, Poison, Weak, Vulnerable, Mark and Root from the party, and heal everyone half the sum. Otherwise: just remove them."},

    # ---- Warden
    "thornlash": {"name": "Thornlash", "req": {"n": 1}, "tgt": "foe",
                  "ops": [{"op": "dmg", "amt": "v+1"}, {"op": "status", "s": "root", "n": 1, "if": "v>=5"}], "text": "Any row: deal the die +1, and Root the enemy on 5+."},
    "sprout": {"name": "Sprout", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "summon", "k": "sapling", "hp": "v*2"}],
               "text": "Grow a sapling with twice the die in HP. It draws one attack this round (one aimed at you first), and enemies can attack it after that."},
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
                   "ops": [{"op": "armor", "amt": "sum//2+2*pair", "to": "party"}, {"op": "status", "s": "thorns", "n": 2, "to": "party"}],
                   "text": "Two dice: the party gains half their sum as Armor (+2 more each if they're a pair), and attackers take 2 this round."},
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
        "name": "Vanguard", "hp": 46, "hp_lvl": 5, "role": "Tank",
        "dice": [D(6), [1, 2, 3, 4, "S", "S"]], "tags": ["bulwark", "juggernaut"],
        "map": {"key": "trailbreaker", "name": "Trailbreaker", "text": "Forest, hills and peaks cost you 1 move."},
        "start": ["strike", "guard", "overguard"], "weapon": "hand_axe", "armor": "padded_coat",
        "pool": ["taunt", "brace", "rally_wall", "shield_bash", "retaliate", "shoulder_charge",
                 "thick_hide", "shield_throw", "steady", "rallying_shout", "interpose", "iron_stance", "shield_weight",
                 "unbreakable", "avalanche"],
        "blurb": "Wades in, armoured, and takes the hits meant for everyone else.",
    },
    "arcanist": {
        "name": "Arcanist", "hp": 23, "hp_lvl": 4, "role": "Area damage and burst",
        "dice": [D(12), D(4)], "tags": ["elementalist", "hexer"],
        "map": {"key": "farsight", "name": "Farsight", "text": "See 3 hexes around you, and spot cursed items in loot."},
        "start": ["bolt", "channel"], "weapon": "oak_staff", "armor": "wool_robe",
        "pool": ["fireball", "frost_lance", "chain_lightning", "hex", "siphon", "doom",
                 "spellweave", "kindling", "cold_snap", "wither", "backlash_ward", "spell_echo",
                 "cataclysm", "grand_curse"],
        "blurb": "Wild dice and big spells. Fragile; keep them covered.",
    },
    "mender": {
        "name": "Mender", "hp": 21, "hp_lvl": 4, "role": "Healer",
        "dice": [D(6), D(6)], "tags": ["restoration", "warding"],
        "map": {"key": "field_medic", "name": "Field Medic", "text": "Everyone who rests on your hex heals an extra 10% of their max HP."},
        "start": ["mend", "lift", "overflow"], "weapon": "lantern_rod", "armor": "nurses_apron",
        "pool": ["renew", "lifeline", "ward", "sanctuary", "cleanse", "smite",
                 "bedside_manner", "quick_hands", "blessed_supplies", "aura", "clean_bill", "transfusion",
                 "shared_burden", "aegis"],
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
    "battle_hymn": {"name": "Battle Hymn", "mods": {"hymn_aura": 1}, "tags": ["anthem"], "text": "While you're above half HP, the whole party deals +1 damage."},
    "bolster": {"name": "Bolster", "mods": {"bolster": 3}, "tags": ["anthem"],
                "text": "Inspire, Lend a Hand and Rousing Chorus also give each ally they help 3 Armor."},
    "second_verse": {"name": "Second Verse", "mods": {"second_verse": 1}, "tags": ["anthem"], "text": "Dice you give or boost get +1 more."},
    "heckler": {"name": "Heckler", "mods": {"heckler": 3}, "tags": ["discord"], "text": "Each enemy's first attack each fight deals 3 less."},
    "haggler": {"name": "Haggler", "mods": {"haggler": 1}, "text": "Sell items for 60% of their price instead of 40%."},
    "silver_voice": {"name": "Silver Voice", "mods": {"silver_voice": 1, "reroll": 1}, "text": "+1 to every event roll, and +1 automatic reroll per fight."},
    "anthem_of_kings": {"name": "Anthem of Kings", "cap": True, "mods": {"anthem": 1}, "tags": ["anthem"], "text": "Every ally rolls an extra d4 each round."},
    "requiem_cap": {"name": "Requiem", "cap": True, "mods": {"grant": "requiem"}, "tags": ["discord"], "text": "Learn Requiem: once per fight, cancel an enemy's coming action without a die."},
    # ---- Alchemist
    "volatile": {"name": "Volatile", "mods": {"bomb_bonus": 3}, "tags": ["bombs"], "text": "Your bombs deal +3."},
    "shrapnel": {"name": "Shrapnel", "mods": {"splash_bonus": 2}, "tags": ["bombs"], "text": "Your bombs' splash deals +2."},
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

# Replacements for flat-number picks (owner's request, Nov 2026: each makes you play differently).
# The picks they replaced stay above so saves load.
PASSIVES.update({
    "backlash_ward": {"name": "Backlash Ward", "mods": {"miss_armor": 1},
                      "text": "When one of your spells misses, gain Armor equal to its dice."},
    "spellweave": {"name": "Spellweave", "mods": {"spellweave": 3},
                   "text": "Your spells deal +3 if you've cast a different spell earlier this round."},
    "wither": {"name": "Wither", "mods": {"wither": 1}, "tags": ["hexer"],
               "text": "Your spells deal +1 for each kind of debuff on their target (Weak, Burn, Mark and the rest)."},
    "clean_bill": {"name": "Clean Bill", "mods": {"clean_bill": 2},
                   "text": "An ally you heal to full HP gets +2 on their next die."},
    "shared_burden": {"name": "Shared Burden", "cap": True, "mods": {"burden": 1}, "tags": ["restoration"],
                      "text": "Once per fight, when an ally would be knocked down, you take half of that hit instead and they take none."},
    "engage": {"name": "Engage", "mods": {"engage": 4}, "text": "+4 damage against enemies at full health."},
    "heedless": {"name": "Heedless", "mods": {"skull_top": 1},
                 "text": "Your skull faces count as your die's highest face (they still hurt you)."},
    "rampage": {"name": "Rampage", "mods": {"rampage": 1}, "tags": ["rampage"],
                "text": "An action that kills is ready again next round, whatever its cooldown."},
    "quarry": {"name": "Quarry", "mods": {"quarry": 2}, "tags": ["beastmaster"],
               "text": "+2 damage against an enemy for each round in a row you've hit it (up to +6). Switching targets starts over."},
    "pass_the_mark": {"name": "Pass the Mark", "mods": {"mark_pass": 1}, "tags": ["marksman"],
                      "text": "When a Marked enemy dies, its Mark jumps to another enemy."},
    "dirty_trick": {"name": "Dirty Trick", "mods": {"dirty_trick": 1},
                    "text": "When you kill an enemy, snatch the biggest die from another enemy's coming attack."},
    "fester": {"name": "Fester", "mods": {"fester": 1}, "tags": ["poisons"],
               "text": "Every hit on a Poisoned enemy, by anyone, makes its Poison 1 stronger."},
    "unseen": {"name": "Unseen", "mods": {"unseen": 2},
               "text": "While no enemy is aiming at you, your hits deal +2."},
    "call_response": {"name": "Call and Response", "mods": {"cue": 3}, "tags": ["anthem"],
                      "text": "After you act, each ally's next damaging action this round deals +3."},
    "short_fuse": {"name": "Short Fuse", "mods": {"short_fuse": 8}, "tags": ["bombs"],
                   "text": "A bomb whose die shows 1 or 2 deals damage as if it were an 8."},
    "reagents": {"name": "Reagents", "mods": {"reagents": 1},
                 "text": "Each bomb you throw makes your later bombs this fight deal 1 more (up to +5)."},
    "catalyst": {"name": "Catalyst", "mods": {"bomb_poison": 1}, "tags": ["elixirs"],
                 "text": "Your bombs also Poison 1 (and with an ally's Burn, that's Wildfire)."},
    "bloom": {"name": "Bloom", "mods": {"bloom": 1}, "text": "When one of your summons dies, the party heals half its max HP."},
})

CLASSES.update({
    "duelist": {
        "name": "Duelist", "hp": 31, "hp_lvl": 4, "role": "Single-target damage",
        "dice": [D(8), D(6)], "tags": ["flurry", "precision"],
        "map": {"key": "ambush", "name": "Ambush", "text": "A fight you start gives the party a free first round."},
        "start": ["slash_d", "parry"], "weapon": "rapier", "armor": "padded_coat",
        "pool": ["twin_cut", "whirl", "lunge", "finisher", "pinpoint", "feint", "read_blade",
                 "momentum", "keen_edge", "engage", "opportunist", "second_wind",
                 "thousand_cuts", "perfect_poise"],
        "blurb": "Fast, precise and deadly against one target at a time.",
    },
    "berserker": {
        "name": "Berserker", "hp": 30, "hp_lvl": 3, "role": "High-risk damage",
        "dice": [D(10), D(4)], "tags": ["bloodlust", "rampage"],
        "map": {"key": "forage", "name": "Forage", "text": "Resting at a camp heals you fully."},
        "start": ["hack_b", "bloodprice"], "weapon": "great_axe", "armor": "hide_vest",
        "pool": ["drink_deep", "frenzy", "cleave", "earthshaker", "reckless_swing", "howl",
                 "rage", "bloodlust", "wide_arcs", "pain_engine", "heedless", "rampage",
                 "red_mist", "unstoppable"],
        "blurb": "Trades blood for power, and gets more dangerous the more it's hurt.",
    },
    "ranger": {
        "name": "Ranger", "hp": 24, "hp_lvl": 4, "role": "Ranged damage",
        "dice": [D(8), D(6)], "tags": ["marksman", "beastmaster"],
        "map": {"key": "tracker", "name": "Tracker", "text": "+1 move on land, and you see enemies 2 hexes further off."},
        "start": ["shoot_r", "hunters_mark"], "weapon": "short_bow", "armor": "padded_coat",
        "pool": ["aimed_shot", "called_shot", "sic_em", "pack_tactics", "volley", "covering_fire", "spotter",
                 "eagle_eye", "companion", "quarry", "pass_the_mark", "camouflage",
                 "deadeye", "alpha"],
        "blurb": "Picks enemies off from afar, with a hawk for company.",
    },
    "scoundrel": {
        "name": "Scoundrel", "hp": 22, "hp_lvl": 3, "role": "Debuffs and loot",
        "dice": [D(6), D(6)], "tags": ["poisons", "tricks"],
        "map": {"key": "light_fingers", "name": "Light Fingers", "text": "One more choice whenever you loot a wreck or a chest."},
        "start": ["stab", "slip", "evasive"], "weapon": "daggers", "armor": "padded_coat",
        "pool": ["envenom", "garrote", "toxic_cloud", "pickpocket", "loaded_dice", "smoke_bomb",
                 "fester", "wayfinder", "lucky_coin", "dirty_trick", "unseen",
                 "plague", "sleight_of_hand"],
        "blurb": "Poisons, dirty tricks and loaded dice. Always comes out ahead.",
    },
    "herald": {
        "name": "Herald", "hp": 18, "hp_lvl": 3, "role": "Buffs for allies",
        "dice": [D(6), D(4)], "tags": ["anthem", "discord"],
        "map": {"key": "silver_tongue", "name": "Silver Tongue", "text": "Shops and inns are 20% cheaper, and some events open up."},
        "start": ["inspire", "jab"], "weapon": "lute", "armor": "padded_coat",
        "pool": ["hymn_of_valor", "lend_a_hand", "crescendo", "dirge", "taunting_verse", "cacophony",
                 "call_response", "second_verse", "mocking_jest", "rousing_chorus", "bolster", "encore",
                 "anthem_of_kings", "requiem_cap"],
        "blurb": "Makes everyone else's dice better, and throws enemies off their stride.",
    },
    "alchemist": {
        "name": "Alchemist", "hp": 21, "hp_lvl": 3, "role": "Items and gadgets",
        "dice": [D(6), D(6)], "tags": ["bombs", "elixirs"],
        "map": {"key": "brewer", "name": "Brewer", "text": "Brew a potion whenever you rest."},
        "start": ["toss", "tonic_a"], "weapon": "sling", "armor": "leather_apron",
        "pool": ["firebomb", "acid_flask", "concussion", "bottle_it", "quicksilver", "panacea",
                 "short_fuse", "shrapnel", "potency", "catalyst", "reagents", "safety_goggles",
                 "chain_reaction", "philosophers_draught"],
        "blurb": "Bombs for the enemy, potions for friends.",
    },
    "warden": {
        "name": "Warden", "hp": 26, "hp_lvl": 3, "role": "Summons and control",
        "dice": [D(8), D(6)], "tags": ["grove", "thorns"],
        "map": {"key": "wildspeak", "name": "Wildspeak", "text": "Forest costs you 1 move, and wild beasts won't hunt you."},
        "start": ["thornlash", "sprout"], "weapon": "gnarled_staff", "armor": "hide_vest",
        "pool": ["call_bear", "swarm", "regrowth", "entangle", "briar_wall", "strangle",
                 "deep_roots", "pack_leader", "bramble_skin", "overgrowth", "bloom", "bark",
                 "guardian_call", "crown_of_thorns"],
        "blurb": "Grows a wall of living things between the party and harm.",
    },
})

# ---- Spellblade (owner's request, Nov 2026; docs/saltbound-spellblade.md): the blade carves Sigils
# into enemies (`carve`, up to SIGIL_CAP), spells Burst them (`burst` on a dmg op spends the target's
# Sigils; `sig` in an amount is the target's Sigils, `sigv` what each is worth to a Burst), and
# infusions (`infuse`) make the next melee hits deal more and carry an element: Frost (Weak), Shock or
# Burn, picked by the die's number unless `el` says. Numbers in Combat (`carve`, `infuse_hit`).
SIGIL_CAP = 5
INFUSE_CAP = 4  # melee hits an infusion can hold
COVENANT_CAP = 3  # an infusion's bonus with Covenant Edge (it lasts the fight)
ACTIONS.update({
    "rune_cut": {"name": "Rune Cut", "req": {"n": 1}, "tgt": "foe", "melee": True, "tags": [],
                 "ops": [{"op": "dmg", "amt": "v+1"}, {"op": "carve", "n": 1}],
                 "text": "Deal the die +1 and carve a Sigil into the enemy."},
    "sigil_burst": {"name": "Sigil Burst", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": [],
                    "ops": [{"op": "dmg", "amt": "v+sigv", "burst": True}],
                    "text": "Any row: deal the die +3 per Sigil on the enemy, and spend them."},
    "elemental_infusion": {"name": "Elemental Infusion", "req": {"n": 1}, "tgt": "self", "spell": True, "tags": ["edge"],
                           "ops": [{"op": "infuse", "n": 3, "amt": "max(2,v//2)"}],
                           "text": "Infuse your blade: your next three melee hits this round deal +half the die (at least 2) and carry "
                                   "an element by the number: 1-2 Frost (Weak), 3-4 Shock, 5+ Burn 2."},
    "charged_bolt": {"name": "Charged Bolt", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": ["edge"],
                     "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "status", "s": "shock", "n": 1},
                             {"op": "infuse", "n": 1, "amt": "3", "el": "shock"}],
                     "text": "Any row: deal the die +2 and Shock the enemy. Your next melee hit this round deals +3 and Shocks."},
    "hilt_rune": {"name": "Hilt Rune", "req": {"n": 1, "min": 4}, "tgt": "foe", "melee": True, "tags": ["edge"],
                  "ops": [{"op": "dmg", "amt": "v+3"}, {"op": "carve", "n": 2}],
                  "miss": [{"op": "dmg", "amt": "v//2"}, {"op": "carve", "n": 1}],
                  "text": "On 4+: deal the die +3 and carve 2 Sigils. Otherwise: deal half the die and carve 1."},
    "sunder_glyph": {"name": "Sunder Glyph", "req": {"n": 1}, "tgt": "foe", "melee": True, "tags": ["edge"],
                     "ops": [{"op": "dmg", "amt": "v"}, {"op": "carve", "double": True}],
                     "text": "Deal the die and double the Sigils on the enemy (up to 5)."},
    "counter_glyph": {"name": "Counter-Glyph", "req": {"n": 1}, "tgt": "self", "tags": ["edge"],
                      "ops": [{"op": "armor", "amt": "v+1"}, {"op": "status", "s": "glyphward", "n": 3}],
                      "text": "Gain the die +1 as Armor. Every enemy that hits you this round has 3 Sigils carved into it."},
    "arc_rune": {"name": "Arc Rune", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": ["sigil"],
                 "ops": [{"op": "dmg", "amt": "v"}, {"op": "dmg", "amt": "2*sig", "to": "sigiled"}],
                 "text": "Any row: deal the die, then every enemy takes 2 per Sigil on it. The Sigils stay."},
    "detonate": {"cd": 2, "name": "Detonate", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": ["sigil"],
                 "ops": [{"op": "dmg", "amt": "v+sigv", "burst": True, "spill": 2}],
                 "text": "Any row: deal the die +3 per Sigil on the enemy and spend them; every other enemy takes 2 per Sigil spent."},
    "runic_ward": {"name": "Runic Ward", "req": {"n": 1}, "tgt": "self", "spell": True, "tags": ["sigil"],
                   "ops": [{"op": "armor", "amt": "v+1+min(6,allsig)"}, {"op": "infuse", "n": 1, "amt": "2", "el": "frost"}],
                   "text": "Gain the die +1 as Armor, +1 per Sigil on the enemies (up to +6). Your next melee hit this round "
                           "deals +2 and carries Frost (Weak)."},
    "brand": {"cd": 3, "name": "Brand", "req": {"n": 1, "min": 6, "sigils": 2}, "tgt": "foe", "spell": True, "tags": ["sigil"],
              "ops": [{"op": "dmg", "amt": "v+sigv", "burst": True}, {"op": "status", "s": "weak", "n": 2},
                      {"op": "status", "s": "vuln", "n": 2}], "miss": [],
              "text": "Any row, on an enemy with 2+ Sigils. On 6+: deal the die +3 per Sigil and spend them, and it's Weak "
                      "and Vulnerable for 2 rounds. Otherwise: nothing."},
})
PASSIVES.update({
    "whetted_runes": {"name": "Whetted Runes", "mods": {"whetted": 1}, "tags": ["edge"],
                      "text": "Rune Cut deals +1 per Sigil already on the enemy."},
    "infused_steel": {"name": "Infused Steel", "mods": {"infused_carve": 1}, "tags": ["edge"],
                      "text": "Your infused melee hits carve a Sigil too."},
    "bladesong": {"name": "Bladesong", "mods": {"bladesong": 3}, "tags": ["edge"],
                  "text": "A melee hit right after one of your spells, or a spell right after one of your melee hits, deals +3."},
    "spellstrike": {"name": "Spellstrike", "mods": {"spellstrike": 2}, "tags": ["edge"],
                    "text": "Every spell of yours that hits infuses your next melee hit this round: +2, and the element by the spell's die."},
    "rune_etched_blade": {"name": "Rune-Etched Blade", "mods": {"rune_face": 1}, "tags": ["edge"],
                          "text": "Your weapon die's lowest face is a rune: it counts as the die's top face and passes any "
                                  "condition, and the action it's on carves a Sigil."},
    "covenant_edge": {"name": "Covenant Edge", "cap": True, "mods": {"covenant": 1}, "tags": ["edge"],
                      "text": "Your infusions last the whole fight and aren't used up, but their bonus is at most +3. A new one replaces the element, keeping the bigger bonus."},
    "feedback_loop": {"name": "Feedback Loop", "mods": {"feedback_loop": 1}, "tags": ["sigil"],
                      "text": "Bursting 3 or more Sigils infuses your next two melee hits this round with the Burst's die "
                              "(+half of it, and its element)."},
    "quiet_glyph": {"name": "Quiet Glyph", "mods": {"quiet_glyph": 1}, "tags": ["sigil"],
                    "text": "A Burst on a 1 or 2 counts each Sigil as +5 instead of +3."},
    "open_circuit": {"name": "Open Circuit", "mods": {"open_circuit": 2}, "tags": ["sigil"],
                     "text": "Your allies' spells and bombs deal +2 per Sigil on their target, without spending them."},
    "runestorm": {"name": "Runestorm", "cap": True, "tags": ["sigil"],
                  "mods": {"override": {"sigil_burst": {"tgt": "foes", "ops": [{"op": "dmg", "amt": "v+sigv", "burst": True, "if": "sig"}],
                                                        "text": "Deal the die +3 per Sigil to every enemy with Sigils, and spend them."}}},
                  "text": "Sigil Burst hits every enemy with Sigils, each for its own."},
})
CLASS_DICE["spellblade"] = [{"faces": D(8), "dk": []}, {"faces": D(6), "dk": []}]
CLASSES["spellblade"] = {
    "name": "Spellblade", "hp": 27, "hp_lvl": 4, "role": "Melee and spell damage",
    "dice": [D(8), D(6)], "tags": ["edge", "sigil"],
    "map": {"key": "runewright", "name": "Runewright",
            "text": "In every fight, each enemy starts with a Sigil. After you rest, the next fight they start with 2; "
                    "after resting in a town, the next two fights."},
    "start": ["rune_cut", "sigil_burst", "elemental_infusion"], "weapon": "etched_sword", "armor": "padded_coat",
    "pool": ["charged_bolt", "hilt_rune", "sunder_glyph", "counter_glyph", "arc_rune", "detonate", "runic_ward", "brand",
             "whetted_runes", "infused_steel", "bladesong", "spellstrike", "feedback_loop", "quiet_glyph", "open_circuit",
             "covenant_edge", "runestorm"],
    "blurb": "Cuts runes into the enemy, then sets them off with a word.",
}

# ---- Emberknight (owner's request, Nov 2026; docs/saltbound-emberknight.md): every die it plays adds its
# number to its Heat (`x["heat"]`); its hits deal +1 per HEAT_STEP Heat; at HEAT_MAX it overheats
# (OVERHEAT_HP damage, Heat to HEAT_AFTER); Heat cools by half at the end of each round. The `heat` op
# adds (or, negative, spends) Heat; `heat` in an amount is the hero's Heat. Rules in Combat (`add_heat`).
HEAT_STEP = 5
HEAT_MAX = 25  # 20 overheated the bots about twice a fight (Nov 2026 batch)
HEAT_AFTER = 10
OVERHEAT_HP = 5
ACTIONS.update({
    "searing_strike": {"name": "Searing Strike", "req": {"n": 1}, "tgt": "foe", "melee": True, "tags": [],
                       "ops": [{"op": "dmg", "amt": "v+1"}], "text": "Deal the die +1."},
    "flashover": {"name": "Flashover", "req": {"n": 1}, "tgt": "foes", "tags": [],
                  "ops": [{"op": "dmg", "amt": "heat//2+v"}, {"op": "heat", "amt": "-heat"}],
                  "text": "Any row: spend all your Heat; every enemy takes half of it, plus the die."},
    "stoke": {"name": "Stoke", "req": {"n": 1}, "tgt": "foe", "melee": True, "tags": ["blaze"],
              "ops": [{"op": "dmg", "amt": "v"}, {"op": "heat", "amt": "2*v"}],
              "text": "Deal the die. This die heats you three times over."},
    "inferno_cleave": {"name": "Inferno Cleave", "req": {"n": 1}, "tgt": "front", "melee": True, "tags": ["blaze"],
                       "ops": [{"op": "dmg", "amt": "v"}],
                       "text": "Hit every front-row enemy for the die. The Heat bonus counts on each hit."},
    "meteor_fist": {"name": "Meteor Fist", "req": {"n": 1, "min": 5}, "tgt": "foe", "melee": True, "tags": ["blaze"],
                    "ops": [{"op": "dmg", "amt": "v+4+heat//5"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                    "text": "On 5+: deal the die +4, and the Heat bonus counts twice. Otherwise: deal half the die."},
    "cinder_lance": {"name": "Cinder Lance", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": ["blaze"],
                     "ops": [{"op": "dmg", "amt": "v+min(10,heat)"}, {"op": "heat", "amt": "-min(10,heat)"}],
                     "text": "Any row: spend up to 10 Heat, and deal the die plus the Heat spent."},
    "quench": {"name": "Quench", "req": {"n": 1}, "tgt": "self", "cool": True, "tags": ["temper"],
               "ops": [{"op": "armor", "amt": "min(heat,2*v)"}, {"op": "heat", "amt": "-2*v"}],
               "text": "Lose Heat equal to twice the die, and gain that much Armor (no more than the Heat lost). Its die adds no Heat."},
    "ember_ward": {"name": "Ember Ward", "req": {"n": 1}, "tgt": "self", "tags": ["temper"],
                   "ops": [{"op": "armor", "amt": "v+1"}, {"op": "status", "s": "emberward", "n": "max(1,heat//5)"}],
                   "text": "Gain the die +1 as Armor. Enemies that hit you this round Burn for 1 per 5 Heat you have (at least 1)."},
    "pass_the_flame": {"name": "Pass the Flame", "req": {"n": 1}, "tgt": "other", "cool": True, "tags": ["temper"],
                       "ops": [{"op": "kindle", "n": 2, "amt": "4+v//2"}, {"op": "heat", "amt": "-5"}],
                       "text": "Give an ally 5 of your Heat: their next two hits this round deal +4 and half the die, and Burn 2. "
                               "Its die adds no Heat."},
    "backdraft": {"cd": 2, "name": "Backdraft", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": ["temper"],
                  "ops": [{"op": "dmg", "amt": "v+heat//2"}, {"op": "weaken", "amt": "heat//4"}, {"op": "heat", "amt": "-(heat//2)"}],
                  "text": "Any row: spend half your Heat. The enemy takes it plus the die, and its attack this round deals half of it less."},
})
PASSIVES.update({
    "molten_edge": {"name": "Molten Edge", "mods": {"molten_edge": 1}, "tags": ["blaze"],
                    "text": "At 15 or more Heat, your hits also Burn 1."},
    "fan_the_flames": {"name": "Fan the Flames", "mods": {"fan_flames": 5}, "tags": ["blaze"],
                       "text": "Each kill adds 5 Heat."},
    "spark_gap": {"name": "Spark Gap", "mods": {"spark_gap": 5}, "tags": ["blaze"],
                  "text": "A die that rolls 1 or 2 adds 5 Heat instead of its number."},
    "redline": {"name": "Redline", "mods": {"redline": 1}, "tags": ["blaze"],
                "text": "Overheating still costs 5 HP, but your next hit this round deals double."},
    "bellows": {"name": "Bellows", "mods": {"bellows": 1}, "tags": ["blaze"],
                "text": "Your weapon die explodes while your Heat is 10 or more at the start of the round."},
    "wildfire_core": {"name": "Wildfire Core", "cap": True, "mods": {"wildfire_core": 1}, "tags": ["blaze"],
                      "text": "Flashover also Burns every enemy for a fifth of the Heat spent (at most 3)."},
    "bank_the_coals": {"name": "Bank the Coals", "mods": {"bank_coals": 1}, "tags": ["temper"],
                       "text": "Your Heat cools by a quarter at the end of the round, not half."},
    "pilot_light": {"name": "Pilot Light", "mods": {"pilot_light": 1}, "tags": ["temper"],
                    "text": "Overheating costs you 2 HP, not 5, and your Heat drops to 15, not 10."},
    "heat_sink": {"name": "Heat Sink", "mods": {"heat_sink": 5}, "tags": ["temper"],
                  "text": "When you overheat, every ally gains 5 Armor."},
    "hearthfire": {"name": "Hearthfire", "mods": {"hearthfire": 3}, "tags": ["temper"],
                   "text": "At the end of the round, if your Heat is 10 or more, your most wounded ally heals 3."},
    "heart_of_the_forge": {"name": "Heart of the Forge", "cap": True, "mods": {"white_heat": 5}, "tags": ["temper"],
                           "text": "At 25 Heat you don't overheat: you burn white for the rest of the round (+5 on every hit), "
                                   "and your Heat drops to 0."},
})
CLASS_DICE["emberknight"] = [{"faces": D(8), "dk": []}, {"faces": D(6), "dk": []}]
CLASSES["emberknight"] = {
    "name": "Emberknight", "hp": 28, "hp_lvl": 4, "role": "Damage that runs hot",
    "dice": [D(8), D(6)], "tags": ["blaze", "temper"],
    "map": {"key": "banked_coals", "name": "Banked Coals",
            "text": "Each fight starts with Heat equal to twice the map turns since your last fight (up to 10)."},
    "start": ["searing_strike", "flashover"], "weapon": "ember_mace", "armor": "padded_coat",
    "pool": ["stoke", "inferno_cleave", "meteor_fist", "cinder_lance", "quench", "ember_ward", "pass_the_flame", "backdraft",
             "molten_edge", "fan_the_flames", "spark_gap", "redline", "bellows", "bank_the_coals", "pilot_light",
             "heat_sink", "hearthfire", "wildfire_core", "heart_of_the_forge"],
    "blurb": "Every swing stokes the fire. Push it to the edge, then let it out.",
}

# ---- Dragonborn (owner's request, Nov 2026; docs/saltbound-dragonborn.md): every enemy hit that lands
# grows a Scale (`hero["scales"]`, up to SCALE_CAP, kept between fights; knocked down loses half, rounded
# up); each Scale is 1 Armor at the start of every round; Breath sheds them all for area damage. The
# `shed` op sheds Scales (`n`, or all); `scales` in an amount is the hero's Scales. Rules in Combat
# (`grow_scales`, `shed`). Half the picks don't touch Scales.
SCALE_CAP = 5
ACTIONS.update({
    "claw": {"name": "Claw", "req": {"n": 1}, "tgt": "foe", "melee": True, "tags": [],
             "ops": [{"op": "dmg", "amt": "v+2"}], "text": "Deal the die +2."},
    "breath": {"name": "Breath", "req": {"n": 1}, "tgt": "foes", "tags": [],
               "ops": [{"op": "dmg", "amt": "v+2*scales"}, {"op": "shed", "all": True}],
               "text": "Any row: shed all your Scales; every enemy takes the die +2 per Scale."},
    "tail_sweep": {"name": "Tail Sweep", "req": {"n": 1}, "tgt": "front", "melee": True, "tags": ["wrath"],
                   "ops": [{"op": "dmg", "amt": "v+2"}], "text": "Hit every front-row enemy for the die +2."},
    "sky_dive": {"name": "Sky Dive", "req": {"n": 1}, "tgt": "foe", "tags": ["wrath"],
                 "ops": [{"op": "dmg", "amt": "v+3"}, {"op": "status", "s": "weak", "n": 1, "if": "back"}],
                 "text": "Any row: deal the die +3. If the enemy is in the back row, it's Weak this round."},
    "rending_bite": {"name": "Rending Bite", "req": {"n": 1}, "tgt": "foe", "melee": True, "tags": ["wrath"],
                     "ops": [{"op": "dmg", "amt": "v+2", "onkill": "v"}, {"op": "status", "s": "poison", "n": 3}],
                     "text": "Deal the die +2 and Poison 3. If it kills, heal the die."},
    "focused_breath": {"name": "Focused Breath", "req": {"n": 1}, "tgt": "foe", "tags": ["wrath"],
                       "ops": [{"op": "dmg", "amt": "v+4*min(3,scales)"}, {"op": "shed", "n": 3}],
                       "text": "Any row: shed up to 3 Scales; the enemy takes the die +4 per Scale shed."},
    "draconic_roar": {"cd": 3, "name": "Draconic Roar", "req": {"n": 1}, "tgt": "foes", "tags": ["hide"],
                      "ops": [{"op": "status", "s": "weak", "n": "1+(v>=6)"}],
                      "text": "Every enemy is Weak; on 6+, for 2 rounds."},
    "dread_gaze": {"name": "Dread Gaze", "req": {"n": 1}, "tgt": "foe", "tags": ["hide"],
                   "ops": [{"op": "gaze"}, {"op": "weaken", "amt": "v"}, {"op": "armor", "amt": "v", "to": "self"}],
                   "text": "Any row: the enemy's attack this round turns on you instead and deals the die less, and you gain the die as Armor."},
    "wing_buffet": {"name": "Wing Buffet", "req": {"n": 1}, "tgt": "front", "tags": ["hide"],
                    "ops": [{"op": "weaken", "amt": "max(1,v//2)"}],
                    "text": "Every front-row enemy's attack this round deals half the die less (at least 1)."},
    "wing_guard": {"name": "Wing Guard", "req": {"n": 1}, "tgt": "other", "tags": ["hide"],
                   "ops": [{"op": "guard"}, {"op": "armor", "amt": "v", "to": "self"}, {"op": "status", "s": "wingguard", "n": 1, "to": "self"}],
                   "text": "Gain the die as Armor, and take the next attack aimed at an ally. Hits on you this round grow 2 Scales, not 1."},
    "molt": {"name": "Molt", "req": {"n": 1}, "tgt": "self", "tags": ["hide"],
             "ops": [{"op": "heal", "amt": "(v+3)*min(1,scales)"}, {"op": "shed", "n": 1}],
             "text": "Shed a Scale to heal the die +3 (nothing without a Scale)."},
    "brood_bond": {"name": "Brood Bond", "req": {"n": 1}, "tgt": "other", "tags": ["hide"],
                   "ops": [{"op": "brood", "n": 2}],
                   "text": "Lend an ally your hide for the fight: they gain 2 Armor now and at the start of each round. It costs no Scales."},
})
PASSIVES.update({
    "searing_breath": {"name": "Searing Breath", "mods": {"searing_breath": 1}, "tags": ["wrath"],
                       "text": "Breath also Burns every enemy for 1 per Scale shed."},
    "wyrmfire_claws": {"name": "Wyrmfire Claws", "mods": {"wyrmfire": 1}, "tags": ["wrath"],
                       "text": "Every Claw Burns 1; a crit Burns 3."},
    "hoards_gleam": {"name": "Hoard's Gleam", "mods": {"hoard_gleam": 80}, "tags": ["wrath"],
                     "text": "+1 damage on every hit per 80 gold you carry (up to +3)."},
    "ancestral_fury": {"name": "Ancestral Fury", "mods": {"ancestral_fury": 1}, "tags": ["wrath"],
                       "text": "When Breath sheds 5 Scales, your next hit this round deals double."},
    "dragons_wrath": {"name": "Dragon's Wrath", "cap": True, "mods": {"dragons_wrath": 1}, "tags": ["wrath"],
                      "text": "Breath sheds only half your Scales (rounded down), and every enemy takes the full amount anyway."},
    "thick_scales": {"name": "Thick Hide", "mods": {"thick_scales": 3}, "tags": ["hide"],
                     "text": "At the start of each fight, grow a Scale if you have fewer than 3."},
    "ancient_blood": {"name": "Ancient Blood", "mods": {"ancient_blood": 6}, "tags": ["hide"],
                      "text": "Once per fight, the first time you drop below half HP, heal 6."},
    "draconic_ascension": {"name": "Draconic Ascension", "cap": True, "mods": {"ascension": 2}, "tags": ["hide"],
                           "text": "Once per fight, below half HP, unfurl for the rest of the fight: +2 on every hit and 3 Armor each round."},
})
CLASS_DICE["dragonborn"] = [{"faces": D(8), "dk": []}, {"faces": D(6), "dk": []}]
CLASSES["dragonborn"] = {
    "name": "Dragonborn", "hp": 34, "hp_lvl": 4, "role": "Bruiser with breath",
    "dice": [D(8), D(6)], "tags": ["wrath", "hide"],
    "map": {"key": "dragons_rest", "name": "Dragon's Rest", "text": "Resting grows a Scale (2 at a camp or in a town)."},
    "start": ["claw", "breath"], "weapon": "talon_gauntlets", "armor": "hide_vest",
    "pool": ["tail_sweep", "sky_dive", "rending_bite", "focused_breath", "draconic_roar", "dread_gaze", "wing_buffet",
             "wing_guard", "molt", "brood_bond", "searing_breath", "wyrmfire_claws", "hoards_gleam", "ancestral_fury",
             "thick_scales", "ancient_blood", "dragons_wrath", "draconic_ascension"],
    "blurb": "Scales harden with every blow it takes. When the stack is full, it breathes.",
}

# ---- Psion (owner's request, Nov 2026; docs/saltbound-psion.md): all its dice are Seer dice (rolled and
# shown while it plans), and it has Focus each round (FOCUS_BASE, +1 at FOCUS_LEVELS): 1 Focus nudges a
# shown die up or down by 1 (the `nudge` message), or, by Mind Link, reveals an ally's hidden die. So
# its actions can ask for exact numbers, pairs and straights: the one class the skills doc allows to.
FOCUS_BASE = 2
FOCUS_LEVELS = (3, 6)
ACTIONS.update({
    "mind_spike": {"name": "Mind Spike", "req": {"n": 1}, "tgt": "foe", "spell": True, "tags": [],
                   "ops": [{"op": "dmg", "amt": "v+6*(v==6)"}],
                   "text": "Any row: deal the die. On exactly 6, deal 12 instead."},
    "kinetic_shield": {"name": "Kinetic Shield", "req": {"n": 1}, "tgt": "self", "tags": [],
                       "ops": [{"op": "armor", "amt": "8 if v==1 else v+2"}, {"op": "status", "s": "kshield", "n": 1}],
                       "text": "Gain the die +2 as Armor. On exactly 1, gain 8 instead."},
    "mind_crush": {"name": "Mind Crush", "req": {"n": 2, "pair": True}, "tgt": "foe", "spell": True, "tags": ["telekinesis"],
                   "ops": [{"op": "dmg", "amt": "3*v"}], "miss": [],
                   "text": "Two dice, a pair: any row, the enemy takes three times the pair's number. Otherwise: nothing."},
    "psionic_storm": {"cd": 3, "name": "Psionic Storm", "req": {"n": 3, "straight": True}, "tgt": "foes", "spell": True,
                      "tags": ["telekinesis"], "ops": [{"op": "dmg", "amt": "hi+4"}], "miss": [],
                      "text": "Three dice in a row (a straight): every enemy takes the highest die +4. Otherwise: nothing."},
    "telekinetic_hurl": {"name": "Telekinetic Hurl", "req": {"n": 1}, "tgt": "foe", "tags": ["telekinesis"],
                         "ops": [{"op": "dmg", "amt": "v"}, {"op": "drag"}, {"op": "dmg", "amt": "6", "if": "v==1"},
                                 {"op": "dmg", "amt": "6", "to": "another", "if": "v==1"}],
                         "text": "Any row: deal the die and drag the enemy to the front row. On exactly 1, it's thrown into "
                                 "another enemy: 6 more to it, and 6 to the other."},
    "gravity_well": {"name": "Gravity Well", "req": {"n": 1}, "tgt": "foes", "tags": ["telekinesis"],
                     "ops": [{"op": "dmg", "amt": "v", "if": "back"}, {"op": "drag", "if": "back"}],
                     "text": "Every back-row enemy takes the die and is dragged to the front row."},
    "read_intent": {"name": "Read Intent", "req": {"n": 0}, "tgt": "foe", "focus": 1, "tags": ["telepathy"],
                    "ops": [{"op": "foresee"}],
                    "text": "No die, 1 Focus: the enemy rolls its attack now, so the party sees the exact numbers."},
    "psychic_scream": {"cd": 3, "name": "Psychic Scream", "req": {"n": 1}, "tgt": "foes", "spell": True, "tags": ["telepathy"],
                       "ops": [{"op": "status", "s": "weak", "n": 1}, {"op": "status", "s": "vuln", "n": 1, "to": "biggest", "if": "v>=5"}],
                       "text": "Every enemy is Weak this round. On 5+, the one with the biggest attack is Vulnerable too."},
    "mind_fog": {"name": "Mind Fog", "req": {"n": 1}, "tgt": "foe", "tags": ["telepathy"],
                 "ops": [{"op": "weaken", "amt": "v+1"}],
                 "text": "Any row: the enemy's attack this round deals the die +1 less."},
    "puppet_strings": {"cd": 3, "name": "Puppet Strings", "req": {"n": 3, "exact": 6}, "tgt": "foe", "spell": True,
                       "tags": ["telepathy"], "ops": [{"op": "turn"}], "miss": [{"op": "dmg", "amt": "sum//2"}],
                       "text": "Three dice, all 6: the enemy turns its attack this round on another enemy (that one takes it now, "
                               "and the attack is spent). Otherwise: deal half the sum."},
})
PASSIVES.update({
    "mind_link": {"name": "Mind Link", "mods": {}, "tags": [],
                  "text": "Spend 1 Focus to reveal one of an ally's hidden dice (it's rolled now and shown); each further Focus "
                          "nudges it up or down by 1."},
    "overclock": {"name": "Overclock", "mods": {"overclock": 1}, "tags": ["telekinesis"],
                  "text": "+1 Focus each round, but spending it costs 1 HP."},
    "resonant_pair": {"name": "Resonant Pair", "mods": {"resonant_pair": 1}, "tags": ["telekinesis"],
                      "text": "Playing a pair on any action gives 1 Focus back."},
    "kinetic_rebound": {"name": "Kinetic Rebound", "mods": {"kinetic_rebound": 1}, "tags": ["telekinesis"],
                        "text": "After you play Kinetic Shield, the Armor you have left at the end of the round hits the last enemy that hit you."},
    "perfect_foresight": {"name": "Perfect Foresight", "cap": True, "mods": {"foresight": 1}, "tags": ["telekinesis"],
                          "text": "Once per fight, set one of your shown dice to any number it has."},
    "empathic_link": {"name": "Empathic Link", "mods": {"empathic": 1}, "tags": ["telepathy"],
                      "text": "Revealing an ally's die with Mind Link costs no Focus."},
    "shared_vision": {"name": "Shared Vision", "mods": {"shared_vision": 1}, "tags": ["telepathy"],
                      "text": "Each ally's biggest die is a Seer die: rolled and shown while they plan."},
    "calm_mind": {"name": "Calm Mind", "mods": {"calm_mind": 2}, "tags": ["telepathy"],
                  "text": "At the end of the round, heal 2 for each Focus you didn't spend."},
    "hive_mind": {"name": "Hive Mind", "cap": True, "mods": {"hive_mind": 1}, "tags": ["telepathy"],
                  "text": "At the start of each round, each ally takes 1 of your Focus, to nudge their own dice."},
})
CLASS_DICE["psion"] = [{"faces": D(6), "dk": []}, {"faces": D(6), "dk": []}]
CLASSES["psion"] = {
    "name": "Psion", "hp": 22, "hp_lvl": 3, "role": "Precise damage and party support",
    "dice": [D(6), D(6)], "tags": ["telekinesis", "telepathy"],
    "map": {"key": "precognition", "name": "Precognition",
            "text": "In a fight you're in, every enemy's first attack is rolled in the open: the party sees the exact numbers."},
    "start": ["mind_spike", "kinetic_shield", "mind_link"], "weapon": "focus_crystal", "armor": "wool_robe",
    "pool": ["mind_crush", "psionic_storm", "telekinetic_hurl", "gravity_well", "read_intent", "psychic_scream", "mind_fog",
             "puppet_strings", "overclock", "resonant_pair", "kinetic_rebound", "empathic_link", "shared_vision", "calm_mind",
             "perfect_foresight", "hive_mind"],
    "blurb": "Sees every roll before it lands, and bends the close ones.",
}

# ---- Signature mechanics for four original classes (owner's request, Nov 2026; docs/saltbound-skills.md):
# - Duelist, Combo: each hit on the enemy it hit last this round deals +COMBO_STEP per hit before it
#   (`x["combo"]`); hitting another enemy starts over. `combo` in an amount is that count.
# - Berserker, Berserk: once it has lost BERSERK_AT of its max HP in a fight, it's berserk for the rest:
#   its dice explode, its hits deal +BERSERK_MIGHT, and it can't use defensive actions (`x["berserk"]`).
# - Mender, Grace: healing it does fills Grace (`x["grace"]`); at GRACE_MAX its next heal is Radiance:
#   the whole party heals that much and is cleansed, and Grace starts over.
# - Alchemist, Reactions: its bombs leave a residue (`residue` on the action: fire, acid, frost) on the
#   enemy hit (`fo["res"]`); a different bomb on a residue reacts (REACTIONS) and uses it up.
COMBO_STEP = 1
BERSERK_AT = 1 / 3
BERSERK_MIGHT = 2  # added after the first batch: the Berserker was the weakest class (48.8% on Hard)
GRACE_MAX = 20
REACTIONS = {frozenset(("fire", "acid")): "caustic", frozenset(("fire", "frost")): "steam", frozenset(("acid", "frost")): "brittle"}
REACTION_TEXT = {"caustic": "Caustic burst: 6 to every enemy in its row", "steam": "Steam: its attack this round deals half",
                 "brittle": "Brittle: Vulnerable for 2 rounds"}
for _k, _r in (("toss", "fire"), ("firebomb", "fire"), ("acid_flask", "acid")):
    ACTIONS[_k]["residue"] = _r
ACTIONS.update({
    "coup_de_grace": {"name": "Coup de Grâce", "req": {"n": 1}, "tgt": "foe", "melee": True, "tags": ["flurry"],
                      "ops": [{"op": "dmg", "amt": "v+4*combo"}],
                      "text": "Deal the die +4 for each hit you've landed on this enemy this round."},
    "savage_blow": {"name": "Savage Blow", "req": {"n": 1}, "tgt": "foe", "melee": True, "tags": ["rampage"],
                    "ops": [{"op": "dmg", "amt": "v+2+v*berserk"}],
                    "text": "Deal the die +2. While you're berserk, deal twice the die +2."},
    "benediction": {"name": "Benediction", "req": {"n": 1}, "tgt": "ally", "tags": ["restoration"],
                    "ops": [{"op": "heal", "amt": "v+1"}, {"op": "grace", "amt": "5"}],
                    "text": "Heal an ally by the die +1, and gain 5 Grace."},
    "frost_flask": {"name": "Frost Flask", "req": {"n": 1}, "tgt": "foe", "bomb": True, "residue": "frost", "tags": ["bombs"],
                    "ops": [{"op": "dmg", "amt": "v"}],
                    "text": "A bomb, any row: deal the die and leave frost on the enemy."},
    "unstable_compound": {"name": "Unstable Compound", "req": {"n": 1}, "tgt": "foes", "tags": ["bombs"],
                          "ops": [{"op": "dmg", "amt": "v+6", "if": "res"}, {"op": "clear_res"}],
                          "text": "Every enemy with a residue on it takes the die +6, and the residues are used up."},
})
PASSIVES.update({
    "feint_step": {"name": "Feint Step", "mods": {"feint_step": 1}, "tags": ["flurry"],
                   "text": "Once a round, hitting a different enemy carries your combo over instead of starting again."},
    "relentless": {"name": "Relentless", "mods": {"relentless": 1}, "tags": ["precision"],
                   "text": "Your combo lasts into the next round, as long as your first hit then is on the same enemy."},
    "riposte_chain": {"name": "Riposte Chain", "mods": {"riposte_chain": 1}, "tags": ["precision"],
                      "text": "Your strike-backs get your combo bonus and count as combo hits."},
    "hair_trigger": {"name": "Hair Trigger", "mods": {"hair_trigger": 1}, "tags": ["bloodlust"],
                     "text": "You go berserk after losing a quarter of your max HP, not a third."},
    "red_haze": {"name": "Red Haze", "mods": {"red_haze": 2}, "tags": ["bloodlust"],
                 "text": "While you're berserk, every hit you land heals you 2."},
    "cold_fury": {"name": "Cold Fury", "mods": {"cold_fury": 1}, "tags": ["rampage"],
                  "text": "While you're berserk, you can still use one defensive action a round."},
    "overflowing_grace": {"name": "Overflowing Grace", "mods": {"overflowing_grace": 1}, "tags": ["restoration"],
                          "text": "Healing beyond max HP fills Grace twice over."},
    "martyr": {"name": "Martyr", "mods": {"martyr": 1}, "tags": ["warding"],
               "text": "Damage the party takes fills your Grace by half."},
    "blessed_rest": {"name": "Blessed Rest", "mods": {"blessed_rest": 1}, "tags": ["warding"],
                     "text": "Your Grace carries over from one fight to the next."},
    "volatile_agents": {"name": "Volatile Agents", "mods": {"volatile_agents": 1}, "tags": ["bombs"],
                        "text": "Burn on an enemy counts as fire for your reactions, and Poison as acid, so allies' statuses react too."},
    "potent_reactions": {"name": "Potent Reactions", "mods": {"potent_reactions": 6}, "tags": ["bombs"],
                         "text": "Your reactions also deal 6 to the enemy they happen on."},
})
CLASSES["duelist"]["pool"] += ["coup_de_grace", "feint_step", "relentless", "riposte_chain"]
CLASSES["berserker"]["pool"] += ["savage_blow", "hair_trigger", "red_haze", "cold_fury"]
CLASSES["mender"]["pool"] += ["benediction", "overflowing_grace", "martyr", "blessed_rest"]
CLASSES["alchemist"]["pool"] += ["frost_flask", "unstable_compound", "volatile_agents", "potent_reactions"]

# ---- Arcanist, Attunement and Flux (owner's request, Nov 2026): the Arcanist is attuned to Fire, Frost or
# Storm (`x["attune"]`, Fire at the start of a fight); its damaging spells add the attunement's rider
# (ATTUNE). A spell of another element (`element` on the action) moves the attunement and gives 1 Flux;
# at FLUX_MAX the next spell Converges: +50% and all three riders. Spells without an element take the
# current one. Rules in actions.py (`attune_cast`).
FLUX_MAX = 3
ATTUNE = {"fire": "Burn 1", "frost": "its attack this round −2", "storm": "arcs to another enemy for 2"}
for _k, _e in (("fireball", "fire"), ("frost_lance", "frost"), ("chain_lightning", "storm")):
    ACTIONS[_k]["element"] = _e
ACTIONS.update({
    "flame_wave": {"name": "Flame Wave", "req": {"n": 1}, "tgt": "front", "spell": True, "element": "fire", "tags": ["elementalist"],
                   "ops": [{"op": "dmg", "amt": "v+1"}], "text": "Fire. Every front-row enemy takes the die +1."},
    "ignite": {"name": "Ignite", "req": {"n": 1}, "tgt": "foe", "spell": True, "element": "fire", "tags": ["elementalist"],
               "ops": [{"op": "dmg", "amt": "v+3*burn"}, {"op": "douse"}],
               "text": "Fire, any row: deal the die + three times the enemy's Burn, and its Burn is spent."},
    "glacial_spike": {"name": "Glacial Spike", "req": {"n": 1}, "tgt": "foe", "spell": True, "element": "frost", "tags": ["elementalist"],
                      "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "status", "s": "weak", "n": 1}],
                      "text": "Frost, any row: deal the die +2, and the enemy is Weak this round."},
    "ice_ward": {"name": "Ice Ward", "req": {"n": 1}, "tgt": "ally", "spell": True, "element": "frost", "tags": ["hexer"],
                 "ops": [{"op": "armor", "amt": "v"}, {"op": "armor", "amt": "v", "to": "self"}],
                 "text": "Frost: you and an ally each gain the die as Armor."},
    "thunderclap": {"name": "Thunderclap", "req": {"n": 1}, "tgt": "foes", "spell": True, "element": "storm", "tags": ["elementalist"],
                    "ops": [{"op": "dmg", "amt": "max(1,v//2)"}, {"op": "status", "s": "shock", "n": 1}],
                    "text": "Storm: every enemy takes half the die (at least 1) and is Shocked."},
    "static_field": {"name": "Static Field", "req": {"n": 1}, "tgt": "foe", "spell": True, "element": "storm", "tags": ["hexer"],
                     "ops": [{"op": "dmg", "amt": "v"}, {"op": "static_field"}],
                     "text": "Storm, any row: deal the die. Your next spell this round arcs twice."},
})
PASSIVES.update({
    "elemental_mastery": {"name": "Elemental Mastery", "mods": {"mastery": 1}, "tags": ["elementalist"],
                          "text": "Casting the same element twice in a row doubles its attunement bonus."},
    "prismatic_mind": {"name": "Prismatic Mind", "mods": {"prismatic": 1}, "tags": ["elementalist"],
                       "text": "You Converge at 2 Flux, not 3."},
    "wild_flux": {"name": "Wild Flux", "mods": {"wild_flux": 1}, "tags": ["hexer"],
                  "text": "When one of your dice explodes, gain 1 Flux."},
    "elemental_resonance": {"name": "Elemental Resonance", "mods": {"resonance": 1}, "tags": ["hexer"],
                            "text": "Your Fire and Frost spells leave fire and frost on the enemy, for an Alchemist's reactions."},
    "avatar_of_the_storm": {"name": "Avatar of the Storm", "cap": True, "mods": {"avatar": 1}, "tags": ["elementalist"],
                            "text": "Your first Convergence each fight keeps your Flux, so the next spell Converges too."},
})
CLASSES["arcanist"]["pool"] += ["flame_wave", "ignite", "glacial_spike", "ice_ward", "thunderclap", "static_field",
                                "elemental_mastery", "prismatic_mind", "wild_flux", "elemental_resonance", "avatar_of_the_storm"]

# ---- Herald, Harmonies (owner's request, Nov 2026): three Harmonies hang over a fight (`f["harm"]`, 0 to
# HARMONY_CAP): Valor (+1 on every ally hit per level), Aegis (each ally starts the round with 1 Armor
# per level) and Dissonance (enemy hits on the party deal 1 less per level). The Herald's songs each
# raise one (`harmony` on the action, `harmony_n` levels); every Harmony falls by 1 at the end of each
# round. Rules in Combat (`raise_harmony`, `end_round`).
HARMONY_CAP = 3
HARMONIES = {"valor": "Valor", "aegis": "Aegis", "discord": "Dissonance"}
for _k, _hm in (("inspire", "valor"), ("hymn_of_valor", "valor"), ("rousing_chorus", "valor"), ("crescendo", "valor"),
                ("dirge", "discord"), ("cacophony", "discord"), ("mocking_jest", "discord"), ("taunting_verse", "aegis")):
    ACTIONS[_k]["harmony"] = _hm
ACTIONS.update({
    "ward_song": {"name": "Ward Song", "req": {"n": 1}, "tgt": "self", "harmony": "aegis", "tags": ["anthem"],
                  "ops": [{"op": "armor", "amt": "v"}], "text": "Gain the die as Armor. Raises Aegis."},
    "song_of_blades": {"name": "Song of Blades", "req": {"n": 1}, "tgt": "party", "harmony": "valor", "harmony_n": 2, "tags": ["anthem"],
                       "ops": [{"op": "armor", "amt": "max(1,v//2)"}], "text": "Every ally gains half the die as Armor (at least 1). Raises Valor twice."},
    "shield_hymn": {"name": "Shield Hymn", "req": {"n": 1}, "tgt": "other", "harmony": "aegis", "tags": ["anthem"],
                    "ops": [{"op": "armor", "amt": "v"}], "text": "An ally gains the die as Armor. Raises Aegis."},
    "jarring_note": {"name": "Jarring Note", "req": {"n": 1}, "tgt": "foe", "harmony": "discord", "tags": ["discord"],
                     "ops": [{"op": "dmg", "amt": "v+2"}], "text": "Any row: deal the die +2. Raises Dissonance."},
    "resonant_chord": {"name": "Resonant Chord", "req": {"n": 1}, "tgt": "self", "harmony": "chord", "tags": ["anthem"],
                       "ops": [], "text": "Raises your two lowest Harmonies."},
    "crescendo_of_light": {"cd": 3, "name": "Crescendo of Light", "req": {"n": 1}, "tgt": "party", "tags": ["anthem"],
                           "ops": [{"op": "heal", "amt": "3*harm"}, {"op": "harm_spend"}],
                           "text": "Spend every Harmony: each ally heals 3 per level spent."},
})
PASSIVES.update({
    "sustain": {"name": "Sustain", "mods": {"sustain": 1}, "tags": ["anthem"],
                "text": "Your Harmonies fall only every other round."},
    "overture": {"name": "Overture", "mods": {"overture": 1}, "tags": ["anthem"],
                 "text": "Each fight starts with Valor and Aegis at 1."},
    "perfect_pitch": {"name": "Perfect Pitch", "mods": {"perfect_pitch": 1}, "tags": ["discord"],
                      "text": "A Harmony can climb to 4."},
    "harmonic_echo": {"name": "Harmonic Echo", "mods": {"harmonic_echo": 1}, "tags": ["discord"],
                      "text": "When an ally kills an enemy, the Harmony you last raised rises again (once a round)."},
    "symphony": {"name": "Symphony", "cap": True, "mods": {"symphony": 1}, "tags": ["anthem"],
                 "text": "While all three Harmonies are at 2 or more, they don't fall."},
})
CLASSES["herald"]["start"] = ["inspire", "jab", "ward_song"]
CLASSES["herald"]["pool"] += ["song_of_blades", "shield_hymn", "jarring_note", "resonant_chord", "crescendo_of_light",
                              "sustain", "overture", "perfect_pitch", "harmonic_echo", "symphony"]

# ---- Scoundrel, Pickings (owner's request, Nov 2026): its crits and killing blows lift a random trinket
# (`x["trinkets"]`, up to TRINKET_CAP, gone when the fight ends), each used once without a die (the
# `trinket` message). Rules in Combat (`lift`, `do_trinket`). To keep the class from getting stronger
# with it (it was the strongest: 71.7% on Hard), its old strengths were cut at the same time: 18 HP
# (was 22), Evasive halves the first hit (it missed), Smoke Bomb halves the next hit (it missed),
# Toxic Cloud Poisons 2 (was 3).
TRINKET_CAP = 2  # was 3; crits also lift only once a round (the first batch: Scoundrel parties 67.8%)
TRINKETS = {
    "smoke": ("Smoke Pellet", "hero", "The next hit on you or an ally misses."),
    "caltrops": ("Caltrops", None, "Every front-row enemy's attack this round deals 2 less."),
    "flash": ("Flash Powder", "foe", "An enemy is Weak this round."),
    "venom": ("Vial of Venom", "foe", "Poison an enemy for 3."),
    "coin": ("Loaded Coin", "hero", "One of your dice, or an ally's, rolls 2 higher."),
    "purse": ("Stolen Purse", None, "+6 gold, and your next die rolls 2 higher."),
}
CLASSES["scoundrel"]["hp"] = 18
# the second pass (Scoundrel parties still 66.8%): Stab +2 (was +3) on an enemy aiming elsewhere, Slip on 5+ (was 4+)
ACTIONS["stab"]["ops"] = [{"op": "dmg", "amt": "v+2*(1-aimed)"}]
ACTIONS["stab"]["text"] = "Deal the die, +2 if the enemy is aiming at someone else."
ACTIONS["slip"]["req"] = {"n": 1, "min": 5}
ACTIONS["slip"]["text"] = "On 5+: the next hit on you misses. Otherwise: nothing."
PASSIVES["evasive"].update(mods={"evasive": 1}, text="The first hit on you each fight deals half.")
ACTIONS["smoke_bomb"].update(text="Two dice: if they're a pair, the next hit on each of you deals half. Otherwise: nothing.")
ACTIONS["smoke_bomb"]["ops"] = [{"op": "status", "s": "halfhit", "n": 1, "to": "party"}]
ACTIONS["toxic_cloud"]["ops"] = [{"op": "status", "s": "poison", "n": 2}]
ACTIONS["toxic_cloud"]["text"] = "Two dice summing to 9+: Poison every enemy for 2. Otherwise: nothing."
ACTIONS.update({
    "rob_blind": {"name": "Rob Blind", "req": {"n": 1}, "tgt": "foe", "tags": ["tricks"],
                  "ops": [{"op": "dmg", "amt": "v"}, {"op": "pilfer", "n": 1, "if": "v>=4"}],
                  "text": "Deal the die. On 4+, lift a trinket."},
    "ransack": {"cd": 3, "name": "Ransack", "req": {"n": 2}, "tgt": "foe", "melee": True, "tags": ["tricks"],
                "ops": [{"op": "dmg", "amt": "sum"}, {"op": "pilfer", "n": 2, "dead": True}],
                "text": "Two dice: deal their sum. If it kills, lift two trinkets."},
})
PASSIVES.update({
    "quick_fingers": {"name": "Quick Fingers", "mods": {"quick_fingers": 1}, "tags": ["poisons"],
                      "text": "The first time you Poison each enemy, lift a trinket."},
    "fences_eye": {"name": "Fence's Eye", "mods": {"fences_eye": 1}, "tags": ["tricks"],
                   "text": "Your killing blows lift two trinkets."},
    "stash": {"name": "Stash", "mods": {"stash": 1}, "tags": ["tricks"],
              "text": "Keep one trinket from one fight to the next."},
    "deep_sleeves": {"name": "Deep Sleeves", "mods": {"deep_sleeves": 2}, "tags": ["tricks"],
                     "text": "Hold up to 4 trinkets."},
    "pay_it_forward": {"name": "Pay It Forward", "mods": {"pay_forward": 1}, "tags": ["poisons"],
                       "text": "A Loaded Coin on an ally rolls 4 higher, and a Smoke Pellet on an ally gives them 3 Armor too."},
    "master_thief": {"name": "Master Thief", "cap": True, "mods": {"master_thief": 1}, "tags": ["tricks"],
                     "text": "Each trinket can be used twice before it's gone."},
})
CLASSES["scoundrel"]["pool"] = [k for k in CLASSES["scoundrel"]["pool"] if k != "wayfinder"] + [
    "rob_blind", "ransack", "quick_fingers", "fences_eye", "stash", "deep_sleeves", "pay_it_forward", "master_thief"]

# ---- Vanguard, Impact (owner's request, Nov 2026): every IMPACT_PER points of damage the Vanguard's
# Armor soaks (hits it draws with Guard and Taunt too) store 1 Impact (`x["impact"]`, up to IMPACT_CAP),
# which lasts the fight. Payback (the starting kit, in place of Retaliate) spends it all as damage. The
# `impact` op adds (or, negative, spends) Impact; `impact` in an amount is the hero's. Rules in Combat
# (`add_impact`, in `hurt_hero`).
IMPACT_CAP = 10
IMPACT_PER = 1  # blocked points per Impact (the owner's fallback if it runs strong: 2)
IMPACT_HOLD = 6  # Unmoved: Armor you gain is +2 while you hold this much
ACTIONS.update({
    "payback": {"name": "Payback", "req": {"n": 1}, "tgt": "foe", "melee": True, "tags": ["juggernaut"],
                "ops": [{"op": "dmg", "amt": "v+impact"}, {"op": "impact", "amt": "-impact"}],
                "text": "Deal the die plus your Impact, then spend all of it."},
    "brace_impact": {"name": "Brace for Impact", "req": {"n": 1}, "tgt": "self", "tags": ["bulwark"],
                     "ops": [{"op": "armor", "amt": "v+2"}, {"op": "impact_brace"}],
                     "text": "Gain the die +2 as Armor. The Impact you gain this round is doubled."},
    "shockwave": {"cd": 3, "name": "Shockwave", "req": {"n": 1}, "tgt": "front", "melee": True, "tags": ["juggernaut"],
                  "ops": [{"op": "dmg", "amt": "v+2+impact//2"}],
                  "text": "Every front-row enemy takes the die +2 plus half your Impact (not spent)."},
    "share_load": {"name": "Share the Load", "req": {"n": 1}, "tgt": "other", "tags": ["bulwark"],
                   "ops": [{"op": "armor", "amt": "v+impact"}, {"op": "impact", "amt": "-impact"}],
                   "text": "An ally gains the die plus your Impact as Armor. Spend all of it."},
    "linebreaker": {"name": "Linebreaker", "req": {"n": 1}, "tgt": "foe", "tags": ["juggernaut"],
                    "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "status", "s": "vuln", "n": 1}],
                    "text": "Any row: deal the die +2, and the enemy is Vulnerable this round."},
})
PASSIVES.update({
    "recoil": {"name": "Recoil", "mods": {"recoil": 1}, "tags": ["juggernaut"],
               "text": "At full Impact, each point your Armor blocks hits the attacker for 1 instead."},
    "unmoved": {"name": "Unmoved", "mods": {"unmoved": 2}, "tags": ["bulwark"],
                "text": f"While you hold {IMPACT_HOLD}+ Impact, Armor you gain is +2."},
    "stored_force": {"name": "Stored Force", "mods": {"stored_force": 1}, "tags": ["bulwark"],
                     "text": "Impact left when a fight ends becomes your Armor at the start of the next."},
    "immovable": {"name": "Immovable", "cap": True, "mods": {"impact_cap": 10, "payback_heal": 1}, "tags": ["bulwark"],
                  "text": "Impact holds up to 20, and Payback heals you for half the Impact it spends."},
})
PASSIVES["shield_weight"].update(
    mods={"override": {"strike": {"ops": [{"op": "dmg", "amt": "v+2+impact//3"}],
                                  "text": "Deal the die +2, plus a third of your Impact (not spent)."}}},
    text="Strike also deals a third of your Impact, without spending it.")
CLASSES["vanguard"]["start"] = ["strike", "guard", "payback", "overguard"]
CLASSES["vanguard"]["pool"] = [k for k in CLASSES["vanguard"]["pool"] if k not in ("retaliate", "avalanche")] + [
    "brace_impact", "shockwave", "share_load", "linebreaker", "recoil", "unmoved", "stored_force", "immovable"]

# ---- Ranger, the Hawk (owner's request, Nov 2026): every Ranger's hawk is with someone in a fight
# (`x["hawk"]`: "f<id>" hunting an enemy, "h<n>" watching a hero; the Ranger itself at the start). Once a
# round, while planning, the `hawk` message sends it elsewhere (no die). Hunting: the Ranger's hits on
# that enemy deal +HAWK_HUNT and the hawk pecks it for HAWK_PECK after the heroes act. Watching: the first
# hit on that hero each round deals HAWK_WATCH less. Alpha doubles both. Rules in Combat (`do_hawk`,
# `hawk_on`) and Actions (`dmg_bonus`); `hunted` in an amount is 1 on the hawk's enemy.
HAWK_HUNT = 1  # was 2: Ranger parties won 64.5% (400 Hard runs)
HAWK_PECK = 2
HAWK_WATCH = 3
ACTIONS["sic_em"].update(text="Your hawk dives at any row: deal the die and make the enemy Weak. The hawk stays to hunt it (this doesn't use its move).")
ACTIONS["sic_em"]["ops"] = [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "weak", "n": 1}, {"op": "hawk_to"}]
ACTIONS["pack_tactics"]["ops"] = [{"op": "dmg", "amt": "v+5+2*hunted"}]
ACTIONS["pack_tactics"]["text"] = "Any row. On 4+: you and your hawk strike together for the die +5 (+7 on the enemy it's hunting). Otherwise: deal half the die."
PASSIVES["alpha"].update(mods={"pet": 8, "alpha_hawk": 2},
                         text="Your hawk's die is a d8, and its peck and the hit it softens are doubled.")
ACTIONS.update({
    "swoop": {"name": "Swoop", "req": {"n": 1}, "tgt": "other", "tags": ["beastmaster"],
              "ops": [{"op": "armor", "amt": "v+2"}, {"op": "hawk_to"}],
              "text": "Your hawk swoops to an ally (this doesn't use its move): they gain the die +2 as Armor, and it watches them."},
})
PASSIVES.update({
    "pinned_prey": {"name": "Pinned Prey", "mods": {"pinned_prey": 1}, "tags": ["beastmaster"],
                    "text": "Your allies' melee can reach the enemy your hawk is hunting, even in the back row."},
    "harrier": {"name": "Harrier", "mods": {"harrier": 2}, "tags": ["beastmaster"],
                "text": "The enemy your hawk is hunting deals 2 less with each hit."},
    "eyes_in_sky": {"name": "Eyes in the Sky", "mods": {"eyes_sky": 1}, "tags": ["beastmaster"],
                    "text": "The enemy your hawk is hunting rolls its attack in the open, as Spotter shows it."},
    "mantle": {"name": "Mantle", "mods": {"mantle": 3}, "tags": ["beastmaster"],
               "text": "Sending your hawk to an ally gives them 3 Armor."},
    "apex_predator": {"name": "Apex Predator", "cap": True, "mods": {"apex": 5}, "tags": ["beastmaster"],
                      "text": "When the enemy your hawk is hunting dies, it moves on to the weakest enemy left, and your next hit deals +5."},
    "longshot": {"name": "Longshot", "mods": {"longshot": 3}, "tags": ["marksman"],
                 "text": "Your hits that aren't melee deal +3 to back-row enemies."},
})
CLASSES["ranger"]["pool"] += ["swoop", "pinned_prey", "harrier", "eyes_in_sky", "mantle", "apex_predator", "longshot"]

# ---- Warden, the Rootweb (owner's request, Nov 2026): while a Warden fights, every Rooted enemy is
# Entwined. When a hero (or their summon) hits an Entwined enemy, every other Entwined enemy takes
# WEB_SPLASH (a splash doesn't splash again); an Entwined enemy alone takes WEB_LONE more instead.
# Rules in Combat (`web_splash`, from `hurt_foe`).
WEB_SPLASH = 2
WEB_LONE = 1
ACTIONS.update({
    "tangleroot": {"name": "Tangleroot", "req": {"n": 1}, "tgt": "foe", "tags": ["thorns"],
                   "ops": [{"op": "status", "s": "root", "n": 1}, {"op": "dmg", "amt": "v//2"}, {"op": "tangle", "amt": "v//2"}],
                   "text": "Root an enemy and another one beside it, and deal half the die to each."},
    "choking_vines": {"cd": 3, "name": "Choking Vines", "req": {"n": 1}, "tgt": "foes", "tags": ["thorns"],
                      "ops": [{"op": "choke", "amt": "v"}],
                      "text": "Every Entwined (Rooted) enemy takes the die and is Weak this round."},
})
PASSIVES.update({
    "thicket": {"name": "Thicket", "mods": {"thicket": 1}, "tags": ["thorns"],
                "text": "The Rootweb carries 3 instead of 2."},
    "strangler_fig": {"name": "Strangler Fig", "mods": {"strangler_fig": 1}, "tags": ["grove"],
                      "text": "Your summons' hits Root the enemy they hit, so they weave the web too."},
    "snare_line": {"name": "Snare Line", "mods": {"snare_line": 1}, "tags": ["thorns"],
                   "text": "Each Entwined enemy deals 1 less with each hit for every other Entwined enemy."},
    "sapping_vines": {"name": "Sapping Vines", "mods": {"sapping_vines": 1}, "tags": ["grove"],
                      "text": "Whenever the Rootweb carries damage, your most wounded ally heals 1."},
    "thorned_tendrils": {"name": "Thorned Tendrils", "mods": {"thorned_tendrils": 2}, "tags": ["thorns"],
                         "text": "Entwined enemies that attack take 2."},
    "heart_of_wild": {"name": "Heart of the Wild", "cap": True, "mods": {"heart_wild": 1}, "tags": ["thorns"],
                      "text": "The Rootweb carries a third of each hit (at least 2, or 3 with Thicket)."},
})
ACTIONS["thornlash"]["text"] = "Any row: deal the die +1, and Root (Entwine) the enemy on 5+."
CLASSES["warden"]["start"] = ["thornlash", "sprout", "tangleroot"]
CLASSES["warden"]["pool"] += ["choking_vines", "thicket", "strangler_fig", "snare_line", "sapping_vines", "thorned_tendrils", "heart_of_wild"]

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
                "ops": [{"op": "split"}], "text": "Split one of your dice into two dice half its size plus one (a d8 becomes two d5s)."},
    "bramble_skin": {"name": "Grafting", "req": {"n": 2}, "tgt": "self", "instant": True, "tags": ["grove"],
                     "ops": [{"op": "merge"}], "text": "Graft two of your dice into one: their sizes add up (a d6 and a d4 make a d10)."},
    "aura": {"name": "Second Opinion", "req": {"n": 1}, "tgt": "other", "instant": True, "tags": ["warding"],
             "ops": [{"op": "second_opinion"}], "text": "An ally's biggest unrolled die rolls three times now, in the open, and keeps the best result."},
    "transfusion": {"name": "Transfusion", "req": {"n": 1}, "tgt": "other", "instant": True, "tags": ["restoration"],
                    "ops": [{"op": "transfusion"}], "text": "Roll the die now: heal an ally by that much +2, and their next die rolls 2 higher."},
})

# Dice picks: passives that change a hero's dice (Combat.dice_picks), or add one (the Swell and
# Echo dice, Combat.round_dice). One or two per class, in its flavour.
PASSIVES.update({
    "shield_rim": {"name": "Shield Rim", "mods": {"shield_rim": 1}, "tags": ["bulwark"],
                   "text": "Your armor die's two lowest faces become shield faces (3 Armor whenever one lands)."},
    "wild_surge": {"name": "Wild Surge", "mods": {"wild_low": 1}, "tags": ["elementalist"],
                   "text": "Your biggest die's two lowest faces become wild: they count as the top face, and crit."},
    "steady_hands": {"name": "Steady Hands", "mods": {"steady_all": 1}, "tags": ["restoration"],
                     "text": "All your dice are Steady: when an action misses, its dice reroll once."},
    "fated_blade": {"name": "Fated Blade", "mods": {"fate_weapon": 1}, "tags": ["precision"],
                    "text": "Your weapon's die is a Fate die: you see two faces while you plan, and one of them comes up."},
    "mirror_step": {"name": "Mirror Step", "mods": {"echo_die": 1}, "tags": ["flurry"],
                    "text": "Gain an Echo die: a d8 until an ally uses a die this round, then it shows the biggest number of their last play."},
    "building_rage": {"name": "Building Rage", "mods": {"swell_die": 1}, "tags": ["rampage"],
                      "text": "Gain a Swell die. It starts each fight as a d4 and grows each round you leave it: d10 +2, d12 +7, then d20 +12. Using it starts it over."},
    "powder_edge": {"name": "Powder Edge", "mods": {"explosive_weapon": 1}, "tags": ["bloodlust"],
                    "text": "Your weapon's die explodes: its top face rolls again and adds."},
    "hawks_eye": {"name": "Hawk's Eye", "mods": {"seer_augur": 1}, "tags": ["marksman"],
                  "text": "Your Augur die becomes a Seer die: rolled and shown while you plan."},
    "loaded_bones": {"name": "Loaded Bones", "mods": {"wild_link": 1}, "tags": ["tricks"],
                     "text": "The 1s and 2s on your linked dice are wild: they count as the top face, and crit."},
    "echo_chorus": {"name": "Echo Chorus", "mods": {"echo_die": 1}, "tags": ["anthem"],
                    "text": "Gain an Echo die: a d8 until an ally uses a die this round, then it shows the biggest number of their last play."},
    "reactive_mix": {"name": "Reactive Mix", "mods": {"catalyst": 1}, "tags": ["bombs"],
                     "text": "Your weapon die's two lowest numbers become a burn face and a poison face."},
    "sap_rising": {"name": "Sap Rising", "mods": {"swell_die": 1}, "tags": ["grove"],
                   "text": "Gain a Swell die. It starts each fight as a d4 and grows each round you leave it: d10 +2, d12 +7, then d20 +12. Using it starts it over."},
})
NEW_DICE_PICKS = {"vanguard": ["shield_rim"], "arcanist": ["wild_surge"], "mender": ["steady_hands"],
                  "duelist": ["fated_blade", "mirror_step"], "berserker": ["building_rage", "powder_edge"],
                  "ranger": ["hawks_eye"], "scoundrel": ["loaded_bones"], "herald": ["echo_chorus"],
                  "alchemist": ["reactive_mix"], "warden": ["sap_rising"]}
for _c, _ks in NEW_DICE_PICKS.items():
    CLASSES[_c]["pool"] += [k for k in _ks if k not in CLASSES[_c]["pool"]]

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
FREE = {"strike", "rune_cut", "searing_strike", "claw", "mind_spike", "brace", "bolt", "slash_d", "hack_b", "shoot_r", "stab", "jab", "thrust", "toss", "thornlash",
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
    "strike": ("sword", "die +2", None), "guard": ("shield", "take an ally's hit · die +2 Armor", None),
    "taunt": ("target", "all attacks on you · die +2 Armor · thorns 2", None), "brace": ("shield", "die +1 Armor · +2 to the weakest", None),
    "rally_wall": ("shield", "party hits −1 · die +2 Armor", None), "shield_bash": ("sword", "die +3 (6+) · Stun", "½ die"),
    "retaliate": ("sword", "your Armor + die", None), "shoulder_charge": ("sword", "die Armor · die +2 · drag", None),
    "bolt": ("sword", "die", None), "channel": ("sword", "sum +2", None),
    "fireball": ("flame", "all: ½ sum +2 · Burn 2", "nothing"), "frost_lance": ("snow", "die +3 · Freeze", "½ die"),
    "chain_lightning": ("bolt", "die +3 · Shock · arcs ½", None), "hex": ("down", "Weak + Vulnerable", None),
    "siphon": ("sword", "die +2 · heal half", "½ die · heal half"), "doom": ("skull", "26 − die, next round", None),
    "mend": ("plus", "heal die +3", None), "lift": ("hand", "revive: 2× die", None),
    "renew": ("plus", "party: heal ½ sum · pair: sum", None), "lifeline": ("plus", "heal ½ max HP at round end", "heal ½ die"),
    "ward": ("shield", "ally: 2× die Armor", None), "sanctuary": ("shield", "party: hits −2", "hits −1"),
    "cleanse": ("plus", "cure + heal die", None), "smite": ("sword", "die +4 · ally heals 2", "½ die"),
    "quick_lift": ("hand", "revive with 6 HP", None),
    "slash_d": ("sword", "die +2 · +3 if it aims at you", "½ die"), "parry": ("shield", "die Armor · riposte 4", None),
    "twin_cut": ("sword", "two hits, each die +4", None), "whirl": ("sword", "each die +1, random foes", None),
    "read_blade": ("eye", "reveal · die, 2× +2 if you beat it", None), "lunge": ("sword", "die +10", "nothing"),
    "finisher": ("sword", "sum +6 · straight 2×", None), "pinpoint": ("target", "die +1, 2× if it aims at you", None),
    "feint": ("down", "its attack −die", None), "perfect_form": ("star", "a die rolls its top face", None),
    "hack_b": ("sword", "die +1", None), "bloodprice": ("heart", "−3 HP · a die +2", None),
    "drink_deep": ("sword", "die +4 · heal on kill", "½ die"), "frenzy": ("sword", "sum +3 · take 2", None),
    "cleave": ("sword", "die to front row", "½ die to one"), "earthshaker": ("crack", "all: ½ sum · one attack −½ sum", "nothing"),
    "reckless_swing": ("sword", "die +12 · take 2", "½ die · take 2"), "howl": ("down", "all enemies Weak", None),
    "shoot_r": ("sword", "die +1", None), "hunters_mark": ("target", "Mark · ⅓ die", None),
    "aimed_shot": ("target", "2× die +1", "½ die"), "called_shot": ("target", "sum +8 · pair +6 · pierce", None),
    "sic_em": ("sword", "die · Weak · hawk hunts it", None), "pack_tactics": ("sword", "die +5 (+7 hunted)", "½ die"),
    "spotter": ("eye", "reveal all enemy dice · ½ die Armor", None), "volley": ("sword", "all: ½ each die +1", None),
    "covering_fire": ("down", "its attack −die · ½ die", None),
    "stab": ("sword", "die, +2 if not aimed at you", None), "slip": ("boot", "5+: dodge next hit", "nothing"),
    "envenom": ("drop", "Poison ½ die +1 · ½ die", None), "garrote": ("sword", "die +2 · Stun if Poisoned", "½ die"),
    "toxic_cloud": ("drop", "all: Poison 3", "nothing"), "pickpocket": ("hand", "steal its biggest die · 4 gold", "its attack −½ die"),
    "loaded_dice": ("link", "link two dice", None), "smoke_bomb": ("boot", "party dodges next hit", "nothing"),
    "inspire": ("up", "ally's next die +½", None), "jab": ("sword", "die", None),
    "hymn_of_valor": ("up", "party dice +2 · match +3", None), "lend_a_hand": ("hand", "give a die, +4", None),
    "mocking_jest": ("target", "die +1 · Mark", None), "rousing_chorus": ("up", "allies' next die +½ die", None),
    "shield_throw": ("sword", "die + ½ Armor · spend it", None), "rallying_shout": ("shield", "party: cleanse · ½ sum Armor", None),
    "crescendo": ("up", "party's next hit +50%", None), "dirge": ("down", "Weak · ½ die", None),
    "taunting_verse": ("arrow", "its attack swings away · Mark", "its attack −3"), "cacophony": ("x", "it loses its turn", "its attack −⅓ sum"),
    "requiem": ("x", "cancel an intent", None),
    "toss": ("sword", "die · splash 1", None), "tonic_a": ("plus", "heal die +1", None),
    "firebomb": ("flame", "die to its row · Burn 1", "½ die"), "acid_flask": ("drop", "strip Armor · Vuln 2 · die", None),
    "concussion": ("sword", "3 + Stun", "½ die"), "bottle_it": ("drop", "brew a potion", None),
    "quicksilver": ("refresh", "ally +2 rerolls · next die +3", None), "panacea": ("plus", "party: cure + heal ½ sum", "cure"),
    "thornlash": ("sword", "die +1 · 5+: Root", None), "sprout": ("spark", "sapling, 2× die HP", None),
    "call_bear": ("spark", "a bear joins", "nothing"), "swarm": ("spark", "wasps: sum HP, sting all 2", None),
    "regrowth": ("plus", "party: heal ½ die +1", None), "entangle": ("root", "Root + Weak · ½ die", None),
    "briar_wall": ("shield", "party: ½ sum Armor · thorns 2", None), "strangle": ("sword", "die +2, 2× if Rooted", "½ die"),
    "ancient_guardian": ("spark", "a treant rises", None),
    # weapon actions
    "hack": ("sword", "die +3", "½ die"), "zap": ("bolt", "die · Shock", None), "flare": ("target", "½ die · Mark", None),
    "thrust": ("sword", "die", None), "harpoon": ("sword", "die · drag to front", "½ die"),
    "shoot": ("sword", "die +4", "½ die"), "slash": ("sword", "die +1", None), "crush": ("sword", "die +5", "½ die"),
    "sweep": ("sword", "front row: ½ sum · pair +3", None), "tidal": ("wave", "all: ½ sum · pair +3", None),
    "storm_bolt": ("bolt", "die +4 · Shock", "nothing"), "venom_stab": ("drop", "½ die · Poison 2", None),
    "blessing": ("plus", "heal die · 2 Armor", None),
    "pass_die": ("spark", "give a die to an ally", None),
    # armor actions (they take Block's place)
    "hunker": ("shield", "die +1 Armor", None), "patch_up": ("shield", "die Armor · heal 2", None),
    "coral_growth": ("shield", "die Armor · heal 3", None), "bristle": ("shield", "die Armor · attackers take 2", None),
    "sidestep": ("shield", "die Armor · 5+: dodge the next hit", None), "echo_shell": ("shield", "die Armor · attacks on you −2", None),
    "cover": ("shield", "you or an ally: die +1 Armor", None), "tidewall": ("shield", "die Armor · party +2", None),
    "encore": ("refresh", "flip a low die, +1", None), "potency": ("spark", "split a die in two", None),
    "bramble_skin": ("spark", "merge two dice", None), "aura": ("refresh", "ally's die: best of three", None),
    "transfusion": ("plus", "heal die +2 · ally's next die +2", None),
}
SHORT.update({
    "rob_blind": ("hand", "die · 4+: lift a trinket", None), "ransack": ("hand", "sum · kill: lift two", None),
    "smoke_bomb": ("boot", "pair: everyone's next hit halved", "nothing"), "toxic_cloud": ("drop", "Σ9+: all Poison 2", "nothing"),
})
SHORT.update({
    "ward_song": ("shield", "die Armor · Aegis +1", None), "song_of_blades": ("up", "party ½ die Armor · Valor +2", None),
    "shield_hymn": ("shield", "ally: die Armor · Aegis +1", None), "jarring_note": ("bolt", "die +2 · Dissonance +1", None),
    "resonant_chord": ("up", "two lowest Harmonies +1", None), "crescendo_of_light": ("plus", "spend Harmonies: party heals 3 each", None),
})
SHORT.update({
    "flame_wave": ("flame", "Fire · front row: die +1", None), "ignite": ("flame", "Fire · die + 3× its Burn · spent", None),
    "glacial_spike": ("snow", "Frost · die +2 · Weak", None), "ice_ward": ("shield", "Frost · you and an ally: die Armor", None),
    "thunderclap": ("bolt", "Storm · all: ½ die · Shock", None), "static_field": ("bolt", "Storm · die · next spell arcs ×2", None),
})
SHORT.update({
    "coup_de_grace": ("sword", "die +4 per combo hit", None), "savage_blow": ("sword", "die +2 · berserk: 2× die +2", None),
    "benediction": ("plus", "heal die +1 · +5 Grace", None), "frost_flask": ("snow", "die · leaves frost", None),
    "unstable_compound": ("flame", "every residue: die +6 · used up", None),
})
SHORT.update({
    "mind_spike": ("bolt", "die · exactly 6: 12", None), "kinetic_shield": ("shield", "die +2 Armor · exactly 1: 8", None),
    "mind_crush": ("bolt", "pair: 3× its number", "nothing"), "psionic_storm": ("bolt", "straight: all, highest +4", "nothing"),
    "telekinetic_hurl": ("hand", "die · drag · on 1: thrown, 6 + 6", None), "gravity_well": ("hand", "back row: die · drag", None),
    "read_intent": ("eye", "1 Focus: its roll shown", None), "psychic_scream": ("down", "all Weak · 5+: biggest Vuln", None),
    "mind_fog": ("down", "its attack −(die +1)", None), "puppet_strings": ("link", "three 6s: its attack hits another", "½ sum"),
})
SHORT.update({
    "claw": ("sword", "die +2", None), "breath": ("flame", "all: die +2 per Scale · shed all", None),
    "tail_sweep": ("sword", "front row: die +2", None), "sky_dive": ("sword", "any row: die +3 · back row Weak", None),
    "rending_bite": ("sword", "die +2 · Poison 3 · kill: heal die", None), "focused_breath": ("flame", "die +4 per Scale (3) · shed", None),
    "draconic_roar": ("down", "all Weak (6+: 2 rounds)", None), "dread_gaze": ("target", "its attack → you, −die · die Armor", None),
    "wing_buffet": ("shield", "front row attacks −½ die", None), "wing_guard": ("shield", "guard · die Armor · hits grow 2", None),
    "molt": ("plus", "shed 1: heal die +3", None), "brood_bond": ("shield", "ally: 2 Armor a round, this fight", None),
})
SHORT.update({
    "searing_strike": ("sword", "die +1", None), "flashover": ("flame", "all: ½ Heat + die · spend all", None),
    "stoke": ("flame", "die · Heat ×3", None), "inferno_cleave": ("sword", "front row: die each", None),
    "meteor_fist": ("sword", "die +4 · Heat bonus ×2 (5+)", "½ die"), "cinder_lance": ("flame", "die + up to 10 Heat · spend", None),
    "quench": ("shield", "cool 2× die · as Armor", None), "ember_ward": ("shield", "die +1 Armor · attackers Burn", None),
    "pass_the_flame": ("flame", "ally: next 2 hits +4 +½ die · Burn 2", None), "backdraft": ("flame", "½ Heat + die · its attack −¼ Heat", None),
})
SHORT.update({
    "tangleroot": ("root", "Root 2 · ½ die each", None), "choking_vines": ("root", "Entwined: die · Weak", None),
})
SHORT.update({
    "swoop": ("shield", "ally: die +2 Armor · hawk watches", None),
})
SHORT.update({
    "payback": ("sword", "die + Impact · spend all", None), "brace_impact": ("shield", "die +2 Armor · Impact ×2", None),
    "shockwave": ("sword", "front row: die +2 + ½ Impact", None), "share_load": ("shield", "ally: die + Impact Armor", None),
    "linebreaker": ("sword", "any row: die +2 · Vulnerable", None),
})
SHORT.update({
    "rune_cut": ("sword", "die +1 · carve 1", None), "sigil_burst": ("spark", "die +3 per Sigil · spend", None),
    "elemental_infusion": ("flame", "next 3 melee: +½ die · element", None),
    "charged_bolt": ("bolt", "die +2 · Shock · next melee +3", None),
    "hilt_rune": ("sword", "die +3 · carve 2 (4+)", "½ die · carve 1"),
    "sunder_glyph": ("sword", "die · double Sigils", None), "counter_glyph": ("shield", "die +1 Armor · attackers carved 3", None),
    "arc_rune": ("bolt", "die · all: 2 per Sigil", None), "detonate": ("flame", "die +3 per Sigil · others 2 each", None),
    "runic_ward": ("shield", "die +1 +Sigils Armor · next melee Frost", None),
    "brand": ("down", "Burst · Weak + Vulnerable 2 (6+)", "nothing"),
})

# Cross-hero combos (the numbers are in combat.py): what two heroes do together.
COMBOS = {
    "pincer": {"name": "Pincer", "text": "Your first hit on an enemy an ally already hit this round: +2 damage, or +5 if one of your "
                                       "dice shows a number one of theirs showed. Once per enemy per round."},
    "covered": {"name": "Covered", "text": "Your first hit after an ally Guards or Taunts for you this round: +3 damage."},
    "shatter": {"name": "Shatter", "text": "Hit an enemy an ally Froze: the ice breaks for +4 damage (and the Freeze ends)."},
    "wildfire": {"name": "Wildfire", "text": "Burn meets an ally's Poison on one enemy (or Poison meets Burn): it erupts "
                                         "for Burn + Poison, and half that to every other enemy. Once per enemy."},
}
