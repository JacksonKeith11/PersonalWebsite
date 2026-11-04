"""The other regions' gear: 52 pieces of loot, 8 relics and 3 materials (merged into `items.ITEMS`).

- Loot (`region`): each piece belongs to one of the eight newer regions and only turns up (in loot,
  shops, prizes and job rewards) in a run that drew that region (`Game.gear`). Its passive is spelled
  out in `text`, and only uses mod keys the engine already reads.
- Relics (`unique`): one per region, never in the loot; the region's quest ends with it (`quests.py`).
- Materials: the Fate Feather is an enchant material like the others (found where they are); Starmetal
  and Wyrm's Ember (`forge`) are rarer upgrades that quests and events hand out: they hone or mark a
  worn piece's die without counting against its work limit.
"""

D = lambda n: list(range(1, n + 1))

# One weapon action per region, the same shape as items.WEAPON_ACTIONS.
ACTIONS = {
    "cinder": {"name": "Cinder Cleave", "req": {"n": 1, "min": 4}, "tgt": "foe", "melee": True,
               "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "status", "s": "burn", "n": 2}], "miss": [{"op": "dmg", "amt": "v//2"}],
               "text": "On 4+: deal the die +2 and Burn the enemy for 2. Otherwise: deal half the die."},
    "sandwind": {"cd": 2, "name": "Scouring Wind", "req": {"n": 2}, "tgt": "foes", "spell": True,
                 "ops": [{"op": "dmg", "amt": "sum//3"}, {"op": "status", "s": "weak", "n": 1}],
                 "text": "Two dice: every enemy takes a third of their sum and is Weak for a round."},
    "stonebolt": {"name": "Stone Gaze", "req": {"n": 1, "min": 5}, "tgt": "foe",
                  "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "stun", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                  "text": "Any row. On 5+: deal the die and Stun the enemy. Otherwise: deal half the die."},
    "vinelash": {"name": "Vine Lash", "req": {"n": 1}, "tgt": "foe",
                 "ops": [{"op": "dmg", "amt": "v//2+1"}, {"op": "status", "s": "root", "n": 1}],
                 "text": "Any row: deal half the die +1 and Root the enemy."},
    "smite": {"name": "Smite", "req": {"n": 1}, "tgt": "foe", "melee": True,
              "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "heal", "amt": "2", "to": "self"}],
              "text": "Deal the die +2, and heal 2."},
    "prism_ray": {"name": "Prism Ray", "req": {"n": 1}, "tgt": "foe", "spell": True,
                  "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "mark", "n": 1, "if": "v>=6"}],
                  "text": "Any row: deal the die. On 6+, Mark the enemy too (allies deal +3 to it)."},
    "lull": {"name": "Lull", "req": {"n": 1}, "tgt": "foe", "spell": True,
             "ops": [{"op": "dmg", "amt": "v//2"}, {"op": "status", "s": "weak", "n": 1}, {"op": "status", "s": "vuln", "n": 1, "if": "v>=5"}],
             "text": "Any row: deal half the die and make the enemy Weak. On 5+, it's Vulnerable too."},
    "glacial": {"name": "Glacial Strike", "req": {"n": 1, "min": 4}, "tgt": "foe", "melee": True,
                "ops": [{"op": "dmg", "amt": "v+1"}, {"op": "status", "s": "freeze", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                "text": "On 4+: deal the die +1 and Freeze the enemy. Otherwise: deal half the die."},
    # an armor's own defensive action (takes the place of Block)
    "stoneform": {"name": "Stoneform", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v+2"}],
                  "text": "Gain the die +2 as Armor."},
}


def _g(name, slot, rarity, die, mods, text, region=None, acts=None, dk=None, guard=None, **extra):
    it = {"name": name, "slot": slot, "rarity": rarity, "die": die, "mods": mods, "text": text}
    if region:
        it["region"] = region
    if acts:
        it["acts"] = acts
    if dk:
        it["dk"] = dk
    if guard:
        it["guard"] = guard
    it.update(extra)
    return it


W, A, T = "weapon", "armor", "trinket"

ITEMS = {
    # ---------------------------------------------------------------- Cinderreach: obsidian and embers
    "obsidian_cleaver": _g("Obsidian Cleaver", W, "uncommon", [1, 2, 3, "F4", 5, 6, 7, "F8"], {"burn_bonus_hit": 2},
                           "Kindle: +2 damage against Burning enemies.", "ash", ["cinder"]),
    "magma_maul": _g("Magma Maul", W, "rare", [2, 3, 4, "F5", 6, 7, 8, "F9", "S", 10], {"burn_bonus": 2},
                     "Molten core: your Burns are 2 stronger.", "ash", ["crush", "cinder"]),
    "ashen_wand": _g("Ashen Wand", W, "common", [1, 2, "F3", 4, 5, 6], {"spell_burn": 1},
                     "Cinders: your spells also Burn 1.", "ash", ["zap"]),
    "slagplate": _g("Slagplate", A, "rare", [3, 4, "S", "S", 6, 7], {"thorns": 3, "burn_immune": 1},
                    "Molten skin: enemies that hit you take 3, and you can't be Burned.", "ash", guard="bristle"),
    "salamander_scale": _g("Salamander Scale", A, "uncommon", [1, 2, 3, "S", 5, 6], {"burn_immune": 1, "regen": 1},
                           "Fireproof: you can't be Burned, and you heal 1 each round in fights.", "ash", guard="patch_up"),
    "cinder_heart": _g("Cinder Heart", T, "rare", [1, 2, "F3", 4, "F5", "F6"], {"burn_bonus": 1, "might": 1},
                       "Banked fire: your Burns are 1 stronger, and +1 damage on every hit.", "ash"),

    # ---------------------------------------------------------------- the Shifting Sands: bronze and sandglass
    "khopesh": _g("Khopesh", W, "uncommon", [1, 2, 3, 4, 5, 6, 7, "W"], {"execute_bonus": 3},
                  "Hooked edge: +3 damage against enemies below half health.", "dunes", ["slash"]),
    "sandstorm_staff": _g("Sandstorm Staff", W, "rare", [1, 2, 3, 4, 5, 6, 7, 8, 9, "W"], {"open_weak": 1},
                          "Blinding sand: every enemy is Weak for the fight's first round.", "dunes", ["sandwind", "zap"]),
    "scarab_bow": _g("Scarab Bow", W, "common", [1, 2, 3, 4, "P5", 6], {"first_strike": 2},
                     "Desert ambush: your first hit each fight deals +2.", "dunes", ["shoot"]),
    "nomad_wraps": _g("Nomad's Wraps", A, "common", [1, 2, 3, "S"], {"move": 1},
                      "Light on the sand: +1 move on the map.", "dunes", guard="sidestep"),
    "sphinx_mantle": _g("Sphinx Mantle", A, "rare", [2, 3, 4, "S", "S", 6], {"silver_voice": 1, "max_hp": 4},
                        "Riddler's wit: +1 to every event roll. +4 max HP.", "dunes", dk=["seer"], guard="echo_shell"),
    "scarab_amulet": _g("Scarab Amulet", T, "rare", D(6), {"unbreakable": 1},
                        "Rebirth: once a fight, survive a lethal hit at 1 HP.", "dunes"),
    "oasis_flask": _g("Oasis Flask", T, "uncommon", D(6), {"rest_bonus": 0.2, "regen": 1},
                      "Sweet water: resting heals an extra 20% of your max HP, and you heal 1 each round in fights.", "dunes"),

    # ---------------------------------------------------------------- the Stillwood: stone and amber
    "petrified_club": _g("Petrified Club", W, "common", [2, 3, 3, 4, "S", 6], {"opportunist": 2},
                         "Heavy as stone: +2 damage against Stunned or Rooted enemies.", "petrified", ["crush"]),
    "gorgon_glaive": _g("Gorgon Glaive", W, "rare", [1, 2, 3, 4, 5, 6, 7, 8, "W", 10], {"opportunist": 3},
                        "Stone gaze: +3 damage against Stunned or Rooted enemies.", "petrified", ["stonebolt", "slash"]),
    "amber_rod": _g("Amber Rod", W, "uncommon", [1, 2, 3, 4, 5, 6, 7, "W"], {"mark_ext": 1},
                    "Preserved light: your Marks last a round longer.", "petrified", ["flare", "blessing"]),
    "bark_of_ages": _g("Bark of Ages", A, "uncommon", [2, 3, 3, 4, "S", "S"], {"max_hp": 5},
                       "Ironbark: +5 max HP.", "petrified", guard="stoneform"),
    "sentinel_plate": _g("Sentinel Plate", A, "legendary", ["S", "S", "S", 5, 6, 7, 8, 9], {"start_armor": 6, "first_hit_soak": 3},
                         "Unmoving: start each fight with 6 Armor, and the first hit on you each round deals 3 less.",
                         "petrified", dk=["steady"], guard="stoneform"),
    "amber_drop": _g("Amber Drop", T, "uncommon", [2, 2, 3, 3, 4, 4], {"debuff_ext": 1},
                     "Preserved: Weak, Vulnerable and Mark that you apply last a round longer.", "petrified", dk=["steady"]),
    "fossil_tooth": _g("Fossil Tooth", T, "common", D(4), {"engage": 3},
                       "First bite: +3 damage against enemies at full health.", "petrified"),

    # ---------------------------------------------------------------- the Verdant Deep: jade and vine
    "machete": _g("Machete", W, "common", [1, 2, 3, 4, 5, "P6"], {"kill_heal": 2},
                  "Clear a path: heal 2 whenever you kill an enemy.", "jungle", ["hack"]),
    "dart_blowpipe": _g("Dart Blowpipe", W, "uncommon", [1, "P2", 3, "P4", 5, "P6"], {"poison_bonus": 1},
                        "Frog venom: your Poisons are 1 stronger.", "jungle", ["shoot", "venom_stab"]),
    "jade_spear": _g("Jade Spear", W, "rare", [1, 2, 3, "P4", 5, 6, 7, "P8", 9, 10], {"fester": 1},
                     "Festering: every hit on a Poisoned enemy, by anyone, makes its Poison 1 stronger.", "jungle", ["thrust", "vinelash"]),
    "vinewoven_mail": _g("Vinewoven Mail", A, "uncommon", [1, 2, 3, 4, "S", 6], {"thorns": 2, "regen": 1},
                         "Living thorns: enemies that hit you take 2, and you heal 1 each round in fights.", "jungle", guard="coral_growth"),
    "jaguar_pelt": _g("Jaguar Pelt", A, "rare", [2, 3, 4, 5, "S", 7], {"evasive": 1, "backstab": 3},
                      "Prowler: the first hit on you each fight misses, and +3 damage against enemies aiming at someone else.",
                      "jungle", guard="sidestep"),
    "jade_frog": _g("Jade Frog", T, "uncommon", D(6), {"kill_heal": 3, "regen": 1},
                    "Lucky frog: heal 3 whenever you kill an enemy, and 1 each round in fights.", "jungle"),

    # ---------------------------------------------------------------- Aetherhold: gold and white light
    "seraph_blade": _g("Seraph Blade", W, "legendary", [1, 2, 3, "S", 5, 6, 7, 8, 9, 10, "W", 12], {"heal_armor": 2, "engage": 3},
                       "Halo: anyone you heal also gains 2 Armor, and +3 damage against enemies at full health.",
                       "heaven", ["smite", "sweep"], dk=["augur"]),
    "sunlance": _g("Sunlance", W, "uncommon", [1, 2, 3, 4, "F5", 6, 7, 8], {"engage": 3},
                   "Dawn strike: +3 damage against enemies at full health.", "heaven", ["thrust", "smite"]),
    "hymnal": _g("Hymnal", W, "common", D(6), {"heal_bonus": 1, "max_hp": 2},
                 "Psalms: your heals are 1 stronger. +2 max HP.", "heaven", ["blessing"]),
    "guardian_mantle": _g("Guardian's Mantle", A, "rare", [2, 3, 4, "S", "S", 7], {"last_stand": 5, "max_hp": 3},
                          "Last light: while you're at half HP or less, gain 5 Armor each round. +3 max HP.", "heaven", guard="cover"),
    "vestment_of_light": _g("Vestment of Light", A, "uncommon", [1, 2, 3, 4, "S", 6], {"weak_immune": 1, "heal_bonus": 1},
                            "Unbowed: you can't be made Weak, and your heals are 1 stronger.", "heaven", guard="patch_up"),
    "angel_feather": _g("Angel Feather", T, "uncommon", [1, 2, 3, 4, 5, "W"], {"evasive": 1},
                        "Lighter than air: the first hit on you each fight misses.", "heaven"),
    "sun_disc": _g("Sun Disc", T, "rare", [1, 2, 3, 4, 5, 6, 7, "W"], {"might": 1, "regen": 1},
                   "Noon: +1 damage on every hit, and heal 1 each round in fights.", "heaven"),

    # ---------------------------------------------------------------- the Prism Wood: glass and light
    "prism_staff": _g("Prism Staff", W, "rare", [1, 2, 3, 4, 5, 6, 7, "I8", 9, 10], {"spell_chain": 1},
                      "Refracted: a spell that hits one enemy also hits another for half.", "crystal", ["prism_ray", "zap"], dk=["seer"]),
    "crystal_shiv": _g("Crystal Shiv", W, "common", D(6), {"keen_edge": 1},
                       "Razor facet: your 6s count as 7s.", "crystal", ["thrust"]),
    "geode_hammer": _g("Geode Hammer", W, "uncommon", [2, 3, 4, 5, 6, "S"], {"kill_armor": 3},
                       "Shatterproof: each kill gives you 3 Armor.", "crystal", ["crush"]),
    "crystal_carapace": _g("Crystal Carapace", A, "rare", [3, 4, "S", "S", "S", 6], {"first_hit_soak": 2, "thorns": 2},
                           "Faceted: the first hit on you each round deals 2 less, and enemies that hit you take 2.",
                           "crystal", guard="echo_shell"),
    "prismweave_robe": _g("Prismweave Robe", A, "uncommon", D(6), {"spellweave": 2},
                          "Shifting colours: your spells deal +2 if you've cast a different spell earlier this round.",
                          "crystal", guard="sidestep"),
    "tuning_fork": _g("Tuning Fork", T, "uncommon", D(6), {"momentum": 1},
                      "Resonance: each of your actions after the first in a round deals +1.", "crystal"),
    "prism_shard": _g("Prism Shard", T, "rare", [1, 2, 3, 4, 5, "W"], {"eagle_eye": 1},
                      "Refraction: a die showing its highest face deals half again as much damage.", "crystal", dk=["fate"]),

    # ---------------------------------------------------------------- the Drowsing Vale: lavender and moonlight
    "dreamcatcher": _g("Dreamcatcher", W, "uncommon", [1, 2, 3, 4, 5, 6, "W", 8], {"debuff_ext": 1},
                       "Snared dreams: Weak, Vulnerable and Mark that you apply last a round longer.", "dream", ["lull", "zap"]),
    "sleepwalker_knife": _g("Sleepwalker's Knife", W, "rare", [1, 2, 3, 4, 5, 6, 7, 8, 9, "W"], {"unseen": 3},
                            "Unnoticed: while no enemy is aiming at you, your hits deal +3.", "dream", ["slash", "lull"], dk=["fate"]),
    "moonsilk_robe": _g("Moonsilk Robe", A, "uncommon", [1, 2, 3, 4, "S", 6], {"stun_ward": 1, "rest_bonus": 0.1},
                        "Restful: ignore the first Stun each fight, and resting heals an extra 10% of your max HP.",
                        "dream", guard="sidestep"),
    "nightmare_mail": _g("Nightmare Mail", A, "rare", [2, 3, 4, "S", "S", 6, 7, 8], {"heckler": 3, "max_hp": 3},
                         "Dread: each enemy's first attack each fight deals 3 less. +3 max HP.", "dream", guard="bristle"),
    "sandman_pouch": _g("Sandman's Pouch", T, "uncommon", D(6), {"cloak": 1},
                        "Drowse: each round, the first enemy that would attack you picks someone else (if there's anyone).", "dream"),
    "music_box": _g("Music Box", T, "rare", D(8), {"hymn_aura": 1, "reroll": 1},
                    "Lullaby: while you're above half health, the whole party deals +1 damage. +1 reroll per fight.", "dream"),

    # ---------------------------------------------------------------- the Frostpeaks: ice and fur
    "frostbrand": _g("Frostbrand", W, "rare", [1, 2, "I3", 4, 5, "I6", 7, 8, "I9", 10], {"frozen_bonus": 3},
                     "Bitter edge: Frozen enemies take +3 from you.", "frost", ["glacial", "slash"]),
    "ice_pick": _g("Ice Pick", W, "common", [1, 2, 3, "I4", 5, 6], {"frozen_bonus": 2},
                   "Crack the ice: Frozen enemies take +2 from you.", "frost", ["hack"]),
    "yeti_hide": _g("Yeti Hide", A, "uncommon", [2, 2, 3, 3, 4, "S"], {"freeze_immune": 1, "max_hp": 5},
                    "Thick fur: your dice can't be Frozen. +5 max HP.", "frost", guard="hunker"),
    "glacier_plate": _g("Glacier Plate", A, "rare", ["S", "S", 4, 5, 6, 7], {"freeze_immune": 1, "first_hit_soak": 2, "max_hp": 6},
                        "Glacial: your dice can't be Frozen, and the first hit on you each round deals 2 less. +6 max HP.",
                        "frost", guard="cover"),
    "rime_amulet": _g("Rime Amulet", T, "uncommon", [1, "I2", 3, "I4", 5, 6], {"frozen_bonus": 2, "freeze_immune": 1},
                      "Cold to the touch: Frozen enemies take +2 from you, and your dice can't be Frozen.", "frost"),
    "aurora_crystal": _g("Aurora Crystal", T, "legendary", [1, "W", 6, "I8", 10, 12], {"might": 2, "frozen_bonus": 2},
                         "Northern lights: +2 damage on every hit, and Frozen enemies take +2 more.", "frost", dk=["exploding"]),

    # ---------------------------------------------------------------- relics: each region's quest ends with one
    "phoenix_plume": _g("Phoenix Plume", T, "legendary", [1, 2, "F3", "F4", "F5", "F6", "F7", "F8"],
                        {"unbreakable": 1, "burn_immune": 1, "burn_bonus": 2},
                        "Rebirth in fire: once a fight, survive a lethal hit at 1 HP. You can't be Burned, and your Burns are 2 stronger.",
                        "ash", unique=True),
    "sunking_khopesh": _g("Sun-King's Khopesh", W, "legendary", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "W", 12],
                          {"execute_bonus": 4, "kill_gold": 3},
                          "The king's due: +4 damage against enemies below half health, and each kill gives you 3 gold.",
                          "dunes", ["slash", "sandwind"], dk=["seer"], unique=True),
    "stillwood_heart": _g("Heart of the Stillwood", A, "legendary", ["S", "S", "S", "S", 7, 8, 9, 10],
                          {"start_armor": 8, "max_hp": 8},
                          "Timeless: start each fight with 8 Armor. +8 max HP.", "petrified", dk=["steady"], guard="stoneform", unique=True),
    "jade_fang": _g("Fang of the Jade Serpent", W, "legendary", [1, "P2", 3, "P4", 5, "P6", 7, "P8", 9, 10, "P11", 12],
                    {"plague": 1, "poison_bonus": 2},
                    "Serpent's venom: your Poisons are 2 stronger, and when a Poisoned enemy dies its Poison spreads to another.",
                    "jungle", ["venom_stab", "vinelash"], unique=True),
    "arbiter_wings": _g("Wings of the Arbiter", A, "legendary", ["S", "S", "S", 6, 7, 8, 9, 10],
                        {"evasive": 1, "overflow": 1, "max_hp": 6},
                        "Judgment's grace: the first hit on you each fight misses, and healing beyond your max HP becomes Armor. +6 max HP.",
                        "heaven", guard="tidewall", unique=True),
    "heartprism": _g("The Heartprism", T, "legendary", [2, 4, 6, 8, 10, "W"], {"reroll": 2, "might": 1},
                     "Every facet: +2 rerolls per fight, and +1 damage on every hit.", "crystal", dk=["seer"], unique=True),
    "somnarch_lantern": _g("Somnarch's Lantern", W, "legendary", [1, 2, 3, 4, 5, 6, 7, 8, "W", "W"], {"debuff_ext": 1, "heckler": 3},
                           "Sweet dreams: Weak, Vulnerable and Mark that you apply last a round longer, and each enemy's first "
                           "attack each fight deals 3 less.", "dream", ["lull", "flare"], dk=["fate"], unique=True),
    "rimeheart": _g("Rimeheart", T, "legendary", [1, "I2", 3, "I4", 5, "I6", 7, "I8"], {"frozen_bonus": 4, "freeze_immune": 1, "max_hp": 4},
                    "Heart of winter: Frozen enemies take +4 from you, and your dice can't be Frozen. +4 max HP.",
                    "frost", dk=["exploding"], unique=True),

    # ---------------------------------------------------------------- materials
    "fate_feather": {"name": "Fate Feather", "slot": "use", "rarity": "rare", "enchant": "fate",
                     "text": "Enchant a piece of gear you wear: its die is a Fate die (you see two faces while you plan, and one of them comes up)."},
    "starmetal": {"name": "Starmetal Ingot", "slot": "use", "rarity": "legendary", "forge": "hone",
                  "text": "Hone a piece of gear you wear: its lowest number rises by 3. Doesn't count against its work limit."},
    "wyrm_ember": {"name": "Wyrm's Ember", "slot": "use", "rarity": "legendary", "forge": "mark",
                   "text": "Mark a piece of gear you wear: its lowest number becomes a special face (a shield on armor, "
                           "else more of its own kind, else a wild face). Doesn't count against its work limit."},
}

RELICS = [k for k, v in ITEMS.items() if v.get("unique")]
FORGE_MATS = [k for k, v in ITEMS.items() if v.get("forge")]
