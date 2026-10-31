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
             "ops": [{"op": "dmg", "amt": "v+3"}], "miss": [{"op": "dmg", "amt": "v-1"}], "text": "4+: the die +3. Otherwise the die −1."},
    "zap": {"name": "Zap", "req": {"n": 1}, "tgt": "foe", "spell": True,
            "ops": [{"op": "dmg", "amt": "v-1"}, {"op": "status", "s": "shock", "n": 1}],
            "text": "Any row: the die −1, and Shock (its next hit also hits a neighbour)."},
    "flare": {"name": "Flare", "req": {"n": 1}, "tgt": "foe",
              "ops": [{"op": "dmg", "amt": "v//2"}, {"op": "status", "s": "mark", "n": 1}], "text": "Any row: half the die, and Mark."},
    "jab": {"name": "Jab", "req": {"n": 1}, "tgt": "foe", "melee": True,
            "ops": [{"op": "dmg", "amt": "v"}], "text": "Deal the die."},
    "harpoon": {"name": "Reel In", "req": {"n": 1, "min": 4}, "tgt": "foe",
                "ops": [{"op": "dmg", "amt": "v"}, {"op": "drag"}], "miss": [{"op": "dmg", "amt": "v-1"}],
                "text": "Any row. 4+: the die, and drag it to the front. Otherwise the die −1."},
    "shoot": {"name": "Aim and Loose", "req": {"n": 1, "min": 5}, "tgt": "foe",
              "ops": [{"op": "dmg", "amt": "v+4"}], "miss": [{"op": "dmg", "amt": "v-1"}], "text": "Any row. 5+: the die +4. Otherwise the die −1."},
    "slash": {"name": "Slash", "req": {"n": 1}, "tgt": "foe", "melee": True,
              "ops": [{"op": "dmg", "amt": "v+1"}], "text": "Deal the die +1."},
    "crush": {"name": "Crush", "req": {"n": 1, "min": 5}, "tgt": "foe", "melee": True,
              "ops": [{"op": "dmg", "amt": "v+5"}], "miss": [{"op": "dmg", "amt": "v-1"}], "text": "5+: the die +5. Otherwise the die −1."},
    "sweep": {"cd": 2, "name": "Sweep", "req": {"n": 2}, "tgt": "front", "melee": True,
              "ops": [{"op": "dmg", "amt": "sum//2+3*pair"}], "text": "Two dice: half the sum to the whole front row, +3 on a pair."},
    "tidal": {"cd": 2, "name": "Surge", "req": {"n": 2}, "tgt": "foes", "spell": True,
              "ops": [{"op": "dmg", "amt": "sum//2+3*pair"}], "text": "Two dice: half the sum to every enemy, +3 on a pair."},
    "storm_bolt": {"name": "Storm Bolt", "req": {"n": 1, "min": 6}, "tgt": "foe", "spell": True,
                   "ops": [{"op": "dmg", "amt": "v+4"}, {"op": "status", "s": "shock", "n": 1}], "miss": [{"op": "dmg", "amt": "v-1"}],
                   "text": "Any row. 6+: the die +4, and Shock. Otherwise the die −1."},
    "venom_stab": {"name": "Venom Stab", "req": {"n": 1}, "tgt": "foe", "melee": True,
                   "ops": [{"op": "dmg", "amt": "v//2"}, {"op": "status", "s": "poison", "n": 2}], "text": "Half the die, and Poison 2."},
    "blessing": {"name": "Blessing", "req": {"n": 1}, "tgt": "ally",
                 "ops": [{"op": "heal", "amt": "v"}, {"op": "armor", "amt": "2"}], "text": "Heal an ally the die and give 2 Armor."},
}

ITEMS = {
    # ---- starting gear
    "hand_axe": {"name": "Hand Axe", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["hack"],
                     "start": True},
    "oak_staff": {"name": "Oak Staff", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["zap"],
                        "start": True},
    "lantern_rod": {"name": "Lantern Rod", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["flare"],
                    "start": True},
    "rapier": {"name": "Rapier", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["jab"], "start": True},
    "great_axe": {"name": "Great Axe", "slot": "weapon", "rarity": "common", "die": D(8), "acts": ["crush"], "start": True},
    "short_bow": {"name": "Short Bow", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["shoot"], "start": True},
    "daggers": {"name": "Paired Daggers", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["venom_stab"], "start": True},
    "lute": {"name": "Lute", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["blessing"], "start": True},
    "sling": {"name": "Sling", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["shoot"], "start": True},
    "gnarled_staff": {"name": "Gnarled Staff", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["zap"], "start": True},
    "hide_vest": {"name": "Hide Vest", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"max_hp": 3}, "start": True},
    "leather_apron": {"name": "Leather Apron", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"bomb_bonus": 1}, "start": True},
    "padded_coat": {"name": "Padded Coat", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"max_hp": 2},
                    "start": True},
    "wool_robe": {"name": "Wool Robe", "slot": "armor", "rarity": "common", "die": D(4), "start": True},
    "nurses_apron": {"name": "Nurse's Apron", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"heal_bonus": 1},
                     "start": True},

    # ---- weapons
    "fishing_spear": {"name": "Fishing Spear", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["jab"]},
    "rusty_harpoon": {"name": "Rusty Harpoon", "slot": "weapon", "rarity": "common", "die": D(6), "acts": ["harpoon"]},
    "flintlock": {"name": "Flintlock", "slot": "weapon", "rarity": "common", "die": [1, 2, 3, 4, 5, 6, 6, 8], "acts": ["shoot"]},
    "coral_blade": {"name": "Coral Blade", "slot": "weapon", "rarity": "uncommon", "die": D(8), "dk": ["steady"], "acts": ["slash"]},
    "tide_hammer": {"name": "Tide Hammer", "slot": "weapon", "rarity": "uncommon", "die": [2, 3, 4, 5, 6, "S"],
                    "acts": ["crush"]},
    "kelp_wand": {"name": "Kelp Wand", "slot": "weapon", "rarity": "uncommon", "die": [1, 2, "P3", 4, 5, "P6", 7, 8], "acts": ["zap", "venom_stab"]},
    "chaplain_censer": {"name": "Chaplain's Censer", "slot": "weapon", "rarity": "uncommon", "die": D(8), "dk": ["augur"],
                        "acts": ["blessing"]},
    "captains_sabre": {"name": "Captain's Sabre", "slot": "weapon", "rarity": "rare", "die": D(10), "dk": ["fate"], "acts": ["slash", "sweep"]},
    "storm_staff": {"name": "Storm Staff", "slot": "weapon", "rarity": "rare", "die": [1, 2, 3, "I4", 5, 6, "I7", 8, 9, 10], "dk": ["exploding"], "acts": ["storm_bolt", "zap"]},
    "leviathan_rod": {"name": "Leviathan Rod", "slot": "weapon", "rarity": "rare", "die": D(10), "dk": ["seer"], "acts": ["tidal"]},
    "crownbreaker": {"name": "Crownbreaker", "slot": "weapon", "rarity": "legendary", "die": D(12), "dk": ["seer", "exploding"], "acts": ["crush", "sweep"]},
    "abyssal_tome": {"name": "Abyssal Tome", "slot": "weapon", "rarity": "legendary", "die": [1, 2, 3, 4, 5, 6, 7, 8, "W", "W"], "dk": ["fate"],
                     "acts": ["tidal", "storm_bolt"]},

    "ember_blade": {"name": "Ember Blade", "slot": "weapon", "rarity": "uncommon", "die": [1, 2, "F3", 4, "F5", 6], "acts": ["slash"]},
    "heirloom_sword": {"name": "Heirloom Sword", "slot": "weapon", "rarity": "uncommon", "die": D(6), "dk": ["heirloom"], "acts": ["slash"]},

    # ---- armor
    "sailcloth_wrap": {"name": "Sailcloth Wrap", "slot": "armor", "rarity": "common", "die": [1, 2, 3, "S"]},
    "cork_vest": {"name": "Cork Vest", "slot": "armor", "rarity": "common", "die": [2, 2, 3, 3, 4, 4], "mods": {"max_hp": 4}},
    "sharkskin": {"name": "Sharkskin", "slot": "armor", "rarity": "uncommon", "die": [2, 3, 4, 5, "S", "S"], "dk": ["steady"],
                  "mods": {"thorns": 1}},
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
    "drowned_idol": {"name": "Drowned Idol", "slot": "trinket", "rarity": "legendary", "die": [1, "W", 12, 12], "dk": ["exploding"],
                     "mods": {"might": 2}},

    "gamblers_bones": {"name": "Gambler's Bones", "slot": "trinket", "rarity": "rare", "die": ["X", "X", 8, 10, 12, 12]},
    "frost_locket": {"name": "Frost Locket", "slot": "trinket", "rarity": "uncommon", "die": [1, "I2", 3, "I4", 5, 6]},

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
}

CONSUMABLES = [k for k, v in ITEMS.items() if v["slot"] == "use"]
GEAR = [k for k, v in ITEMS.items() if v["slot"] != "use" and not v.get("start")]


def price(key):
    it = ITEMS[key]
    return it.get("price") or PRICE[it["rarity"]]
