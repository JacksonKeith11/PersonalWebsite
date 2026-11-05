"""Items: equipment (weapon, armor, trinket) and consumables. Generic, so any map can use them.

Equipment always gives a die (`die`: a list of faces; "S" is a shield face, worth 0 but blocking
3 damage) and may give actions (`acts`) and passive mods (`mods`, the same keys passives use).
Consumables are used from the bag, on the map or in a fight (no die needed), and are used up.
"""

D = lambda n: list(range(1, n + 1))

PRICE = {"common": 15, "uncommon": 30, "rare": 55, "legendary": 90}
RARITIES = ["common", "uncommon", "rare", "legendary"]

# Actions that come with weapons, in the same shape as classes.ACTIONS.
WEAPON_ACTIONS = {
    "hack": {"name": "Hack", "req": {"n": 1, "min": 4}, "tgt": "foe", "melee": True,
             "ops": [{"op": "dmg", "amt": "v+3"}], "miss": [{"op": "dmg", "amt": "v//2"}], "text": "On 4+: deal the die +3. Otherwise: deal half the die."},
    "zap": {"name": "Zap", "req": {"n": 1}, "tgt": "foe", "spell": True,
            "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "shock", "n": 1}],
            "text": "Any row: deal the die and Shock the enemy (its next hit also hits a neighbour)."},
    "flare": {"name": "Flare", "req": {"n": 1}, "tgt": "foe",
              "ops": [{"op": "dmg", "amt": "v//2"}, {"op": "status", "s": "mark", "n": 1}], "text": "Any row: deal half the die and Mark the enemy."},
    "thrust": {"name": "Jab", "req": {"n": 1}, "tgt": "foe", "melee": True,
            "ops": [{"op": "dmg", "amt": "v"}], "text": "Deal the die."},
    "harpoon": {"name": "Reel In", "req": {"n": 1, "min": 4}, "tgt": "foe",
                "ops": [{"op": "dmg", "amt": "v"}, {"op": "drag"}], "miss": [{"op": "dmg", "amt": "v//2"}],
                "text": "Any row. On 4+: deal the die and drag the enemy to the front row. Otherwise: deal half the die."},
    "shoot": {"name": "Aim and Loose", "req": {"n": 1, "min": 5}, "tgt": "foe",
              "ops": [{"op": "dmg", "amt": "v+4"}], "miss": [{"op": "dmg", "amt": "v//2"}], "text": "Any row. On 5+: deal the die +4. Otherwise: deal half the die."},
    "slash": {"name": "Slash", "req": {"n": 1}, "tgt": "foe", "melee": True,
              "ops": [{"op": "dmg", "amt": "v+1"}], "text": "Deal the die +1."},
    "crush": {"name": "Crush", "req": {"n": 1, "min": 5}, "tgt": "foe", "melee": True,
              "ops": [{"op": "dmg", "amt": "v+5"}], "miss": [{"op": "dmg", "amt": "v//2"}], "text": "On 5+: deal the die +5. Otherwise: deal half the die."},
    "sweep": {"cd": 2, "name": "Sweep", "req": {"n": 2}, "tgt": "front", "melee": True,
              "ops": [{"op": "dmg", "amt": "sum//2+3*pair"}], "text": "Two dice: every enemy in the front row takes half their sum (+3 if they're a pair)."},
    "tidal": {"cd": 2, "name": "Surge", "req": {"n": 2}, "tgt": "foes", "spell": True,
              "ops": [{"op": "dmg", "amt": "sum//2+3*pair"}], "text": "Two dice: every enemy takes half their sum (+3 if they're a pair)."},
    "storm_bolt": {"name": "Storm Bolt", "req": {"n": 1, "min": 6}, "tgt": "foe", "spell": True,
                   "ops": [{"op": "dmg", "amt": "v+4"}, {"op": "status", "s": "shock", "n": 1}], "miss": [],
                   "text": "Any row. On 6+: deal the die +4 and Shock the enemy. Otherwise: nothing."},
    "venom_stab": {"name": "Venom Stab", "req": {"n": 1}, "tgt": "foe", "melee": True,
                   "ops": [{"op": "dmg", "amt": "v//2"}, {"op": "status", "s": "poison", "n": 2}], "text": "Deal half the die and Poison the enemy for 2."},
    "pass_die": {"name": "Pass a Die", "req": {"n": 1}, "tgt": "other", "instant": True,
             "ops": [{"op": "give", "bonus": 2}], "text": "Give one of your dice to an ally to use this round; it rolls 2 higher."},
    "blessing": {"name": "Blessing", "req": {"n": 1}, "tgt": "ally",
                 "ops": [{"op": "heal", "amt": "v"}, {"op": "armor", "amt": "2"}], "text": "Heal an ally by the die and give them 2 Armor."},
}

# Each armor's own defensive action, which takes the place of Block for whoever wears it (`guard` on
# the armor; Game.actions_of swaps it in). All of them take a guard die.
ARMOR_ACTIONS = {
    "hunker": {"name": "Hunker Down", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v+1"}],
               "text": "Gain the die +1 as Armor."},
    "patch_up": {"name": "Patch Up", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v"}, {"op": "heal", "amt": "2", "to": "self"}],
                 "text": "Gain the die as Armor and heal 2."},
    "coral_growth": {"name": "Coral Growth", "req": {"n": 1}, "tgt": "self",
                     "ops": [{"op": "armor", "amt": "v"}, {"op": "heal", "amt": "3", "to": "self"}],
                     "text": "Gain the die as Armor and heal 3."},
    "bristle": {"name": "Bristle", "req": {"n": 1}, "tgt": "self",
                "ops": [{"op": "armor", "amt": "v"}, {"op": "status", "s": "thorns", "n": "2", "to": "self"}],
                "text": "Gain the die as Armor. Enemies that hit you this round take 2."},
    "sidestep": {"name": "Sidestep", "req": {"n": 1}, "tgt": "self",
                 "ops": [{"op": "armor", "amt": "v"}, {"op": "status", "s": "dodge", "n": "1", "to": "self", "if": "v>=5"}],
                 "text": "Gain the die as Armor. On 5+, the next hit on you also misses."},
    "echo_shell": {"name": "Echo Shell", "req": {"n": 1}, "tgt": "self",
                   "ops": [{"op": "armor", "amt": "v"}, {"op": "weaken", "amt": "2", "to": "aiming"}],
                   "text": "Gain the die as Armor. Every attack aimed at you drops by 2."},
    "cover": {"name": "Cover", "req": {"n": 1}, "tgt": "ally", "ops": [{"op": "armor", "amt": "v+1"}],
              "text": "You or an ally gains the die +1 as Armor."},
    "tidewall": {"name": "Tidewall", "req": {"n": 1}, "tgt": "self",
                 "ops": [{"op": "armor", "amt": "v"}, {"op": "armor", "amt": "2", "to": "party"}],
                 "text": "Gain the die as Armor, and the whole party gains 2 more."},
}
WEAPON_ACTIONS.update(ARMOR_ACTIONS)

ITEMS = {
    # ---- starting gear
    "hand_axe": {"name": "Hand Axe", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["hack"],
                     "start": True},
    "oak_staff": {"name": "Oak Staff", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["zap"],
                        "start": True},
    "lantern_rod": {"name": "Lantern Rod", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["flare"],
                    "start": True},
    "rapier": {"name": "Rapier", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["thrust"], "start": True},
    "great_axe": {"name": "Great Axe", "slot": "weapon", "rarity": "common", "die": D(8), "acts": ["crush"], "start": True},
    "short_bow": {"name": "Short Bow", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["shoot"], "start": True},
    "daggers": {"name": "Paired Daggers", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["venom_stab"], "start": True},
    "lute": {"name": "Lute", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["blessing"], "start": True},
    "sling": {"name": "Sling", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["shoot"], "start": True},
    "gnarled_staff": {"name": "Gnarled Staff", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["zap"], "start": True},
    "etched_sword": {"name": "Etched Sword", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["slash"], "start": True},
    "talon_gauntlets": {"name": "Talon Gauntlets", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["slash"], "start": True},
    "ember_mace": {"name": "Ember Mace", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["slash"], "start": True},
    "hide_vest": {"name": "Hide Vest", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"max_hp": 3}, "start": True},
    "leather_apron": {"name": "Leather Apron", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"bomb_bonus": 1}, "start": True},
    "padded_coat": {"name": "Padded Coat", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"max_hp": 2},
                    "start": True},
    "wool_robe": {"name": "Wool Robe", "slot": "armor", "rarity": "common", "die": D(4), "start": True},
    "nurses_apron": {"name": "Nurse's Apron", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"heal_bonus": 1},
                     "start": True},

    # ---- weapons
    "rusty_harpoon": {"name": "Rusty Harpoon", "slot": "weapon", "rarity": "common", "die": [1, 2, 3, "I4", 5, 6], "acts": ["harpoon"]},
    "flintlock": {"name": "Flintlock", "slot": "weapon", "rarity": "common", "die": [1, 2, 3, 4, 5, 6, "F6", 8], "acts": ["shoot"]},
    "coral_blade": {"name": "Coral Blade", "slot": "weapon", "rarity": "uncommon", "die": [1, 2, 3, 4, "S", 6, 7, 8], "dk": ["steady"], "acts": ["slash"]},
    "tide_hammer": {"name": "Tide Hammer", "slot": "weapon", "rarity": "uncommon", "die": [2, 3, 4, 5, 6, 7, 8, "S"],
                    "acts": ["crush"]},
    "kelp_wand": {"name": "Kelp Wand", "slot": "weapon", "rarity": "uncommon", "die": [1, 2, "P3", 4, 5, "P6", 7, 8], "acts": ["zap", "venom_stab"]},
    "chaplain_censer": {"name": "Chaplain's Censer", "slot": "weapon", "rarity": "uncommon", "die": [1, 2, 3, 4, 5, 6, 7, "W"], "dk": ["augur"],
                        "acts": ["blessing"]},
    "captains_sabre": {"name": "Captain's Sabre", "slot": "weapon", "rarity": "rare", "die": [1, 2, 3, 4, 5, 6, 7, 8, 9, "W"], "dk": ["fate"], "acts": ["slash", "sweep"]},
    "storm_staff": {"name": "Storm Staff", "slot": "weapon", "rarity": "rare", "die": [1, 2, 3, "I4", 5, 6, "I7", 8, 9, 10], "dk": ["exploding"], "acts": ["storm_bolt", "zap"]},
    "leviathan_rod": {"name": "Leviathan Rod", "slot": "weapon", "rarity": "rare", "die": [1, 2, 3, 4, 5, 6, "I7", 8, 9, 10], "dk": ["seer"], "acts": ["tidal"]},
    "crownbreaker": {"name": "Crownbreaker", "slot": "weapon", "rarity": "legendary", "die": [1, 2, "S", 4, 5, 6, 7, 8, 9, 10, 11, 12], "dk": ["seer", "exploding"], "acts": ["crush", "sweep"]},
    "abyssal_tome": {"name": "Abyssal Tome", "slot": "weapon", "rarity": "legendary", "die": [1, 2, 3, 4, 5, 6, 7, 8, "W", "W"], "dk": ["fate"],
                     "acts": ["tidal", "storm_bolt"]},

    "ember_blade": {"name": "Ember Blade", "slot": "weapon", "rarity": "uncommon", "die": [1, 2, "F3", 4, "F5", 6], "acts": ["slash"]},
    "heirloom_sword": {"name": "Heirloom Sword", "slot": "weapon", "rarity": "uncommon", "die": D(6), "dk": ["heirloom"], "acts": ["slash"]},

    # ---- armor
    "cork_vest": {"name": "Cork Vest", "slot": "armor", "rarity": "common", "die": [2, 2, 3, 3, 4, 4], "mods": {"max_hp": 4}},
    "sharkskin": {"name": "Sharkskin", "slot": "armor", "rarity": "uncommon", "die": [2, 3, 4, 5, "S", "S"], "dk": ["steady"],
                  "mods": {"thorns": 3}},
    "coral_mail": {"name": "Coral Mail", "slot": "armor", "rarity": "uncommon", "die": [1, 2, "S", "S", "S", 6],
                   "mods": {"max_hp": 4}},
    "pilgrim_shawl": {"name": "Pilgrim's Shawl", "slot": "armor", "rarity": "uncommon", "die": D(6), "dk": ["augur"],
                      "mods": {"heal_bonus": 2}},
    "whaleplate": {"name": "Whaleplate", "slot": "armor", "rarity": "rare", "die": [3, 4, 5, 6, "S", "S", "S", "S"], "dk": ["seer"],
                   "mods": {"max_hp": 6}},
    "mistweave": {"name": "Mistweave", "slot": "armor", "rarity": "rare", "die": D(8), "dk": ["fate"], "mods": {"start_armor": 4}},
    "tidelord_aegis": {"name": "Tidelord's Aegis", "slot": "armor", "rarity": "legendary", "die": ["S", "S", "S", 6, 7, 8], "dk": ["seer", "steady"],
                       "mods": {"start_armor": 6, "max_hp": 6}},

    # ---- trinkets
    "lucky_shell": {"name": "Lucky Shell", "slot": "trinket", "rarity": "common", "die": D(4), "mods": {"reroll": 1}},
    "brass_compass": {"name": "Brass Compass", "slot": "trinket", "rarity": "common", "die": [1, 1, 6, 6],
                      "mods": {"move": 1}},
    "shark_tooth": {"name": "Shark Tooth", "slot": "trinket", "rarity": "uncommon", "die": D(6), "dk": ["augur"], "mods": {"might": 1}},
    "pearl_charm": {"name": "Pearl Charm", "slot": "trinket", "rarity": "uncommon", "die": D(6), "dk": ["steady"], "mods": {"regen": 1}},
    "black_pearl": {"name": "Black Pearl", "slot": "trinket", "rarity": "rare", "die": [1, 6, 6, 6], "dk": ["seer"]},
    "storm_glass": {"name": "Storm Glass", "slot": "trinket", "rarity": "rare", "die": D(8), "dk": ["fate"], "mods": {"reroll": 1, "might": 1}},
    "drowned_idol": {"name": "Drowned Idol", "slot": "trinket", "rarity": "legendary", "die": [1, "W", 6, 12], "dk": ["exploding"],
                     "mods": {"might": 2}},

    "gamblers_bones": {"name": "Gambler's Bones", "slot": "trinket", "rarity": "rare", "die": ["X", "X", 8, 10, 12, 12]},
    "frost_locket": {"name": "Frost Locket", "slot": "trinket", "rarity": "uncommon", "die": [1, "I2", 3, "I4", 5, "I6"]},

    # ---- rule-benders: gear that changes how you play rather than adding numbers
    "forked_staff": {"name": "Forked Staff", "slot": "weapon", "rarity": "rare", "die": [1, 2, "I3", 4, 5, 6, 7, "W"], "acts": ["zap"]},
    "siren_conch": {"name": "Siren's Conch", "slot": "armor", "rarity": "uncommon", "die": [1, 2, 3, "S", "S", 5]},
    "tide_hourglass": {"name": "Tide Hourglass", "slot": "trinket", "rarity": "legendary", "die": D(8)},
    "powder_heart": {"name": "Powder Heart", "slot": "trinket", "rarity": "rare", "die": D(6)},
    "weighted_coin": {"name": "Weighted Coin", "slot": "trinket", "rarity": "uncommon", "die": D(6)},
    "bloodstone": {"name": "Bloodstone", "slot": "trinket", "rarity": "rare", "die": D(6)},
    "bosuns_whistle": {"name": "Bosun's Whistle", "slot": "trinket", "rarity": "uncommon", "die": D(6)},
    "bosuns_bell": {"name": "Bosun's Bell", "slot": "trinket", "rarity": "uncommon", "die": D(6), "acts": ["pass_die"]},
    "sea_glass_lens": {"name": "Sea-Glass Lens", "slot": "trinket", "rarity": "rare", "die": D(6), "dk": ["seer"]},

    # ---- more gear: low rarities that beat a rare in the right hands or the right fight
    "gutting_knife": {"name": "Gutting Knife", "slot": "weapon", "rarity": "common", "die": [1, 2, "P3", 4, 5, "P6"], "acts": ["venom_stab"]},
    "boarding_axe": {"name": "Boarding Axe", "slot": "weapon", "rarity": "common", "die": [1, 2, 3, 4, "S", 6, 7, 8], "acts": ["hack"]},
    "driftwood_staff": {"name": "Driftwood Staff", "slot": "weapon", "rarity": "common", "die": [1, 2, "I3", 4, 5, 6], "acts": ["flare"]},
    "shellbreaker": {"name": "Shellbreaker Maul", "slot": "weapon", "rarity": "uncommon", "die": [2, 3, 4, "S", 6, 6], "acts": ["crush"]},
    "gull_bow": {"name": "Gull-Feather Bow", "slot": "weapon", "rarity": "uncommon", "die": [1, 2, 3, 4, 5, 6, 7, "W"], "acts": ["shoot"]},
    "reef_lantern": {"name": "Reef Lantern", "slot": "weapon", "rarity": "uncommon", "die": [1, 2, 3, "W", 5, 6], "acts": ["blessing", "flare"]},
    "harpoon_gun": {"name": "Harpoon Gun", "slot": "weapon", "rarity": "rare", "die": [1, 2, 3, 4, "I5", 6, 7, 8, "I9", 10], "acts": ["harpoon", "shoot"]},
    "oilskin_coat": {"name": "Oilskin Coat", "slot": "armor", "rarity": "common", "die": [1, 2, 3, 4, "S", "S"]},
    "barnacle_plate": {"name": "Barnacle Plate", "slot": "armor", "rarity": "common", "die": [2, 3, 3, 4]},
    "divers_harness": {"name": "Diver's Harness", "slot": "armor", "rarity": "uncommon", "die": D(6)},
    "kelpweave_robe": {"name": "Kelpweave Robe", "slot": "armor", "rarity": "uncommon", "die": D(6)},
    "smugglers_cloak": {"name": "Smuggler's Cloak", "slot": "armor", "rarity": "uncommon", "die": D(6)},
    "gilded_cuirass": {"name": "Gilded Cuirass", "slot": "armor", "rarity": "rare", "die": [3, 4, 5, "S", "S", "S"], "dk": ["steady"]},
    "tarnished_ring": {"name": "Tarnished Ring", "slot": "trinket", "rarity": "common", "die": D(4)},
    "gull_bone": {"name": "Gull-Bone Charm", "slot": "trinket", "rarity": "common", "die": [1, 2, 2, 3]},
    "salt_locket": {"name": "Salt-Crusted Locket", "slot": "trinket", "rarity": "common", "die": D(4)},
    "rum_flask": {"name": "Rum Flask", "slot": "trinket", "rarity": "uncommon", "die": D(6)},
    "spyglass": {"name": "Spyglass", "slot": "trinket", "rarity": "uncommon", "die": D(8), "dk": ["seer"]},
    "ember_charm": {"name": "Ember Charm", "slot": "trinket", "rarity": "uncommon", "die": [1, 2, "F3", 4, "F5", "F6"]},
    "captains_medal": {"name": "Captain's Medal", "slot": "trinket", "rarity": "rare", "die": D(8)},
    "anchor_pendant": {"name": "Anchor Pendant", "slot": "trinket", "rarity": "rare", "die": [4, 4, 5, 5, 6, 6], "dk": ["steady"]},

    # ---- consumables
    "potion": {"name": "Tonic", "slot": "use", "rarity": "common", "price": 8, "use": {"heal": 10},
               "text": "Heal 10."},
    "big_potion": {"name": "Rum Ration", "slot": "use", "rarity": "uncommon", "price": 16, "use": {"heal": 22},
                   "text": "Heal 22."},
    "bomb": {"name": "Powder Keg", "slot": "use", "rarity": "common", "price": 10, "use": {"bomb": 8}, "fight": True,
             "text": "In a fight: deal 8 to an enemy."},
    "ward_scroll": {"name": "Ward Scroll", "slot": "use", "rarity": "uncommon", "price": 12, "use": {"party_armor": 6},
                    "fight": True, "text": "In a fight: the party gains 6 Armor."},
    "smelling_salts": {"name": "Smelling Salts", "slot": "use", "rarity": "uncommon", "price": 14, "use": {"lift": 6},
                       "fight": True, "text": "In a fight: pick up a knocked-down ally with 6 HP."},

    # ---- enchant materials: rubbed into a piece of gear you wear (out of fights), they give its die a kind for good.
    # Found, not sold: the sea shrine, a grotto's hoard and a guarded wreck's pool each hold one.
    "powder_salt": {"name": "Powder Salt", "slot": "use", "rarity": "rare", "enchant": "exploding",
                    "text": "Enchant a piece of gear you wear: its die explodes (a top-face roll rolls again and adds)."},
    "still_pearl": {"name": "Still Pearl", "slot": "use", "rarity": "rare", "enchant": "steady",
                    "text": "Enchant a piece of gear you wear: its die is Steady (if its action misses, it rerolls once)."},
    "seer_glass": {"name": "Seer's Glass", "slot": "use", "rarity": "rare", "enchant": "seer",
                   "text": "Enchant a piece of gear you wear: its die is a Seer die (rolled and shown while you plan)."},
}

# Passives: gear past the starting kit does something of its own, so a find changes how a hero plays.
# The mods are summed with passives' (game.mods); `text` is what the item says it does.
PASSIVES = {
    # weapons
    "flintlock": ({"first_strike": 2}, "First shot: your first hit each fight deals +2."),
    "coral_blade": ({"first_strike": 3}, "First blood: your first hit each fight deals +3."),
    "tide_hammer": ({"opportunist": 2}, "Undertow: +2 damage against Stunned or Rooted enemies."),
    "kelp_wand": ({"poison_bonus": 1}, "Your Poisons are 1 stronger."),
    "chaplain_censer": ({"heal_armor": 2}, "Consecrate: anyone you heal also gains 2 Armor."),
    "ember_blade": ({"burn_bonus_hit": 2}, "Kindle: +2 damage against Burning enemies."),
    "captains_sabre": ({"kill_armor": 4}, "Boarding party: each kill gives you 4 Armor."),
    "storm_staff": ({"frozen_bonus": 3}, "Frostbite: Frozen enemies take +3 from you."),
    "leviathan_rod": ({"open_weak": 1}, "Tidecaller: every enemy is Weak for the fight's first round."),
    "crownbreaker": ({"pierce_all": 1}, "Shatter: your hits ignore Armor."),
    "abyssal_tome": ({"echo_any": 1}, "Echo of the deep: your first action each fight happens twice, the second at half strength."),
    # armor
    "whaleplate": ({"first_hit_soak": 3}, "Blubber: the first hit on you each round deals 3 less."),
    "mistweave": ({"evasive": 1}, "Mist: the first hit on you each fight misses."),
    "tidelord_aegis": ({"unbreakable": 1}, "Unbreakable: once a fight, survive a lethal hit at 1 HP."),
    # trinkets
    "black_pearl": ({"kill_gold": 3}, "Pirate's luck: each kill gives you 3 gold."),
    "gamblers_bones": ({"skull_boost": 4}, "Double or nothing: a skull still hurts, but your next die rolls 4 higher."),
    "frost_locket": ({"frozen_bonus": 2}, "Frozen enemies take +2 from you."),
    "shark_tooth": ({"execute_bonus": 2}, "Bloodscent: +2 damage against enemies below half health."),
    "drowned_idol": ({"wild_heal": 4}, "The drowned god's favour: a wild face also heals you 4."),
    "cork_vest": ({"rest_bonus": 0.1}, "Buoyant: resting heals an extra 10% of your max HP."),
    # rule-benders
    "forked_staff": ({"spell_chain": 1}, "Forked lightning: a spell that hits one enemy also hits another for half."),
    "siren_conch": ({"mark_attacker": 1}, "Echoing shell: whoever hits you is Marked (allies deal +3 to it)."),
    "tide_hourglass": ({"hoard": 1}, "Slack water: your biggest unused die carries over to next round as an extra die."),
    "powder_heart": ({"all_explode": 1, "max_hp": -6}, "Powder heart: all your dice explode on their top face. −6 max HP."),
    "weighted_coin": ({"one_is_top": 1}, "Heads I win: a 1 you roll counts as the die's top face."),
    "bloodstone": ({"blood_reroll": 3}, "Blood price: out of rerolls, a miss rerolls anyway for 3 HP."),
    "bosuns_whistle": ({"combo_up": 2}, "All hands: your combos deal +2 more."),
    "bosuns_bell": ({}, "Ring it: hand one of your dice to an ally."),
    "sea_glass_lens": ({"guard_free": 1}, "Clear sight: your armor's die can go on attacks too."),
    # more gear
    "gutting_knife": ({"execute_bonus": 3}, "Finish them: +3 damage against enemies below half health."),
    "boarding_axe": ({"kill_heal": 3}, "Plunder: heal 3 whenever you kill an enemy."),
    "driftwood_staff": ({"mark_ext": 1}, "Lingering mark: your Marks last a round longer."),
    "shellbreaker": ({"pierce_all": 1}, "Crack the shell: your hits ignore Armor."),
    "gull_bow": ({"backstab": 3}, "From the rigging: +3 damage against enemies aiming at someone else."),
    "reef_lantern": ({"heal_bonus": 2}, "Kind light: your heals are 2 stronger."),
    "harpoon_gun": ({"opportunist": 3}, "Pinned: +3 damage against Stunned or Rooted enemies."),
    "oilskin_coat": ({"burn_immune": 1, "max_hp": 2}, "Waxed: you can't be Burned. +2 max HP."),
    "barnacle_plate": ({"thorns": 2}, "Barnacled: enemies that hit you take 2."),
    "divers_harness": ({"stun_ward": 1, "freeze_immune": 1}, "Steady breath: ignore the first Stun each fight, and your dice can't be Frozen."),
    "kelpweave_robe": ({"regen": 2}, "Living weave: heal 2 each round in fights."),
    "smugglers_cloak": ({"cloak": 1}, "Unseen: each round, the first enemy that would attack you picks someone else (if there's anyone)."),
    "gilded_cuirass": ({"start_armor": 5, "max_hp": 4}, "Gleaming: start each fight with 5 Armor. +4 max HP."),
    "tarnished_ring": ({"might": 1}, "Old weight: +1 damage on every hit."),
    "gull_bone": ({"heckler": 3}, "Bad omen: each enemy's first attack each fight deals 3 less."),
    "salt_locket": ({"weak_immune": 1, "max_hp": 3}, "Salted: you can't be made Weak. +3 max HP."),
    "rum_flask": ({"kill_heal": 5, "rest_bonus": 0.15}, "A swig: heal 5 per kill, and resting heals an extra 15% of your max HP."),
    "spyglass": ({"wayfinder": 1}, "Far sight: see further along your path on the map; its die shows while you plan."),
    "ember_charm": ({"burn_bonus": 2}, "Banked coals: your Burns are 2 stronger."),
    "captains_medal": ({"hymn_aura": 1}, "Rally the crew: while you're above half health, the whole party deals +1 damage."),
    "anchor_pendant": ({"first_hit_soak": 2}, "Anchored: the first hit on you each round deals 2 less."),
}
for _k, (_m, _t) in PASSIVES.items():
    ITEMS[_k]["mods"] = {**ITEMS[_k].get("mods", {}), **_m}
    ITEMS[_k]["text"] = (ITEMS[_k].get("text", "") + " " + _t).strip()

# The other regions' gear, relics and materials (gear2.py: their passives and guard actions come with them).
from . import gear2 as _G  # noqa: E402
WEAPON_ACTIONS.update(_G.ACTIONS)
ITEMS.update(_G.ITEMS)

GUARD_ACT = {'hide_vest': 'hunker',
             'padded_coat': 'hunker',
             'wool_robe': 'hunker',
             'leather_apron': 'hunker',
             'nurses_apron': 'patch_up',
             'cork_vest': 'hunker',
             'oilskin_coat': 'hunker',
             'barnacle_plate': 'bristle',
             'sharkskin': 'bristle',
             'coral_mail': 'coral_growth',
             'pilgrim_shawl': 'patch_up',
             'kelpweave_robe': 'patch_up',
             'divers_harness': 'cover',
             'smugglers_cloak': 'sidestep',
             'mistweave': 'sidestep',
             'siren_conch': 'echo_shell',
             'whaleplate': 'cover',
             'gilded_cuirass': 'cover',
             'tidelord_aegis': 'tidewall'}
for _k, _a in GUARD_ACT.items():
    ITEMS[_k]["guard"] = _a

# Guard dice: every armor's die (and any charm named in GUARD_TRINKETS) only goes on defensive actions (Block, Armor,
# healing, Dodge...), so armor protects instead of adding another attack die.
GUARD_TRINKETS = ()
for _k, _v in ITEMS.items():
    if _v["slot"] == "armor" or _k in GUARD_TRINKETS:
        _v["dk"] = ["guard"] + list(_v.get("dk", []))

# Where gear goes: one slot of each kind. (A second trinket slot was tried and taken out at the
# owner's request: the sixth die took Hard from about 37% to 51%.)
SLOTS = ("weapon", "armor", "trinket")


def slots_for(item_slot):
    """The equipment slots an item of this kind can go in."""
    return [item_slot]


CONSUMABLES = [k for k, v in ITEMS.items() if v["slot"] == "use" and not v.get("enchant") and not v.get("forge")]
MATERIALS = [k for k, v in ITEMS.items() if v.get("enchant")]  # found at random (shrines, grottos, wrecks, fights)
FORGE_MATS = list(_G.FORGE_MATS)  # Starmetal and Wyrm's Ember: only quests and events hand them out
RELICS = list(_G.RELICS)          # each region's quest reward, never in the loot
# loot: every piece of gear but the starting kit and the relics (Game.gear drops the regions a run didn't draw)
GEAR = [k for k, v in ITEMS.items() if v["slot"] != "use" and not v.get("start") and not v.get("unique")]


def price(key):
    it = ITEMS[base(key)]
    return it.get("price") or PRICE[it["rarity"]]


def base(key):
    """The catalogue item behind a key: worked gear (tempered or enchanted) has its own key, "rapier@3",
    so the work stays with that one item wherever it goes (`Game.item` looks it up)."""
    return key.split("@", 1)[0]
