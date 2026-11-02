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
             "ops": [{"op": "give"}], "text": "Give one of your dice to an ally to use this round."},
    "blessing": {"name": "Blessing", "req": {"n": 1}, "tgt": "ally",
                 "ops": [{"op": "heal", "amt": "v"}, {"op": "armor", "amt": "2"}], "text": "Heal an ally by the die and give them 2 Armor."},
}

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
    "hide_vest": {"name": "Hide Vest", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"max_hp": 3}, "start": True},
    "leather_apron": {"name": "Leather Apron", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"bomb_bonus": 1}, "start": True},
    "padded_coat": {"name": "Padded Coat", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"max_hp": 2},
                    "start": True},
    "wool_robe": {"name": "Wool Robe", "slot": "armor", "rarity": "common", "die": D(4), "start": True},
    "nurses_apron": {"name": "Nurse's Apron", "slot": "armor", "rarity": "common", "die": D(4), "mods": {"heal_bonus": 1},
                     "start": True},

    # ---- weapons
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

    # ---- rule-benders: gear that changes how you play rather than adding numbers
    "forked_staff": {"name": "Forked Staff", "slot": "weapon", "rarity": "rare", "die": D(8), "acts": ["zap"]},
    "siren_conch": {"name": "Siren's Conch", "slot": "armor", "rarity": "uncommon", "die": [1, 2, 3, "S", "S", 5]},
    "tide_hourglass": {"name": "Tide Hourglass", "slot": "trinket", "rarity": "legendary", "die": D(8)},
    "powder_heart": {"name": "Powder Heart", "slot": "trinket", "rarity": "rare", "die": D(6)},
    "weighted_coin": {"name": "Weighted Coin", "slot": "trinket", "rarity": "uncommon", "die": D(6)},
    "bloodstone": {"name": "Bloodstone", "slot": "trinket", "rarity": "rare", "die": D(6)},
    "bosuns_whistle": {"name": "Bosun's Whistle", "slot": "trinket", "rarity": "uncommon", "die": D(6)},
    "bosuns_bell": {"name": "Bosun's Bell", "slot": "trinket", "rarity": "uncommon", "die": D(6), "acts": ["pass_die"]},
    "sea_glass_lens": {"name": "Sea-Glass Lens", "slot": "trinket", "rarity": "rare", "die": D(6), "dk": ["seer"]},

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
    "leviathan_rod": ({"open_weak": 1}, "Tidecaller: every enemy starts the fight Weak."),
    "crownbreaker": ({"pierce_all": 1}, "Shatter: your hits ignore Armor."),
    "abyssal_tome": ({"echo_any": 1}, "Echo of the deep: your first action each fight happens twice, the second at half strength."),
    # armor
    "coral_mail": ({"block_heal": 2}, "Coral growth: Block also heals you 2."),
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
}
for _k, (_m, _t) in PASSIVES.items():
    ITEMS[_k]["mods"] = {**ITEMS[_k].get("mods", {}), **_m}
    ITEMS[_k]["text"] = (ITEMS[_k].get("text", "") + " " + _t).strip()

# Guard dice: every armor's die, and a few charms', only go on defensive actions (Block, Armor,
# healing, Dodge...), so armor protects instead of adding another attack die.
GUARD_TRINKETS = ("lucky_shell", "pearl_charm")
for _k, _v in ITEMS.items():
    if _v["slot"] == "armor" or _k in GUARD_TRINKETS:
        _v["dk"] = ["guard"] + list(_v.get("dk", []))

CONSUMABLES = [k for k, v in ITEMS.items() if v["slot"] == "use"]
GEAR = [k for k, v in ITEMS.items() if v["slot"] != "use" and not v.get("start")]


def price(key):
    it = ITEMS[key]
    return it.get("price") or PRICE[it["rarity"]]
