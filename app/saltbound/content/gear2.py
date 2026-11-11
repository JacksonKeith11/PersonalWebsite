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

# One weapon action per region, the same shape as items.WEAPON_ACTIONS (every one gets the weapon
# cooldown there; Stone Gaze, a Stun, waits 3).
ACTIONS = {
    "cinder": {"name": "Cinder Cleave", "req": {"n": 1}, "tgt": "foe", "melee": True,
               "ops": [{"op": "dmg", "amt": "v+2+burn"}, {"op": "status", "s": "burn", "n": 2}],
               "text": "Deal the die +2 plus the enemy's Burn, then Burn it for 2."},
    "sandwind": {"cd": 2, "name": "Scouring Wind", "req": {"n": 2}, "tgt": "foes", "spell": True,
                 "ops": [{"op": "dmg", "amt": "sum//3"}, {"op": "status", "s": "weak", "n": 1}],
                 "text": "Two dice: every enemy takes a third of their sum and is Weak for a round."},
    "stonebolt": {"cd": 3, "name": "Stone Gaze", "req": {"n": 1, "min": 5}, "tgt": "foe",
                  "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "stun", "n": 1}], "miss": [{"op": "dmg", "amt": "v//2"}],
                  "text": "Any row. On 5+: deal the die and Stun the enemy. Otherwise: deal half the die."},
    "vinelash": {"name": "Vine Lash", "req": {"n": 1}, "tgt": "foe",
                 "ops": [{"op": "status", "s": "root", "n": 1}, {"op": "dmg", "amt": "v//2+psn"}],
                 "text": "Any row: Root the enemy and deal half the die plus its Poison (the Poison stays)."},
    "radiant": {"name": "Radiant Strike", "req": {"n": 1}, "tgt": "foe", "melee": True,
                "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "heal", "amt": "2", "to": "party"}],
                "text": "Deal the die +2, and everyone in the party heals 2."},
    "prism_ray": {"name": "Prism Ray", "req": {"n": 1}, "tgt": "foe", "spell": True,
                  "ops": [{"op": "dmg", "amt": "v+2"}, {"op": "status", "s": "burn", "n": 2, "if": "v%2==1"},
                          {"op": "status", "s": "weak", "n": 1, "if": "v%2==0"}],
                  "text": "Any row: deal the die +2. An odd die Burns the enemy for 2; an even one makes it Weak."},
    "lull": {"name": "Lull", "req": {"n": 1}, "tgt": "foe", "spell": True,
             "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "weak", "n": 1}, {"op": "status", "s": "vuln", "n": 1, "if": "v>=5"}],
             "text": "Any row: deal the die and make the enemy Weak. On 5+, it's Vulnerable too."},
    "glacial": {"name": "Glacial Strike", "req": {"n": 1, "min": 4}, "tgt": "foe", "melee": True,
                "ops": [{"op": "dmg", "amt": "v+3"}, {"op": "status", "s": "freeze", "n": 1}], "miss": [{"op": "dmg", "amt": "v"}],
                "text": "On 4+: deal the die +3 and Freeze the enemy (it hits for half). Otherwise: deal the die."},
    # an armor's own defensive action (takes the place of Block)
    "stoneform": {"name": "Stoneform", "req": {"n": 1}, "tgt": "self", "ops": [{"op": "armor", "amt": "v+2"}],
                  "text": "Gain the die +2 as Armor."},
}
GUARD_ACTIONS = {"stoneform"}

# The armory (owner's request, Nov 2026): twenty more weapons, each with a cooldown skill of its own.
ACTIONS.update({
    "skewer": {"name": "Skewer", "req": {"n": 1}, "tgt": "foe",
               "ops": [{"op": "dmg", "amt": "v+1"}, {"op": "dmg", "amt": "v//2", "to": "behind"}],
               "text": "Any row: deal the die +1 to the enemy, and half the die to the enemy behind it in the other row."},
    "snag": {"name": "Snag", "req": {"n": 1}, "tgt": "foe",
             "ops": [{"op": "snag"}, {"op": "dmg", "amt": "v"}],
             "text": "Any row: take all of the enemy's Armor as your own, then deal the die."},
    "open_wound": {"name": "Open Wound", "req": {"n": 1}, "tgt": "foe", "melee": True,
                   "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "wound", "n": 1}],
                   "text": "Deal the die. For the rest of the fight every hit on that enemy deals +1 (stacks to +3)."},
    "point_blank": {"name": "Point Blank", "req": {"n": 1}, "tgt": "foe", "melee": True,
                    "ops": [{"op": "dmg", "amt": "v*2"}, {"op": "selfdmg", "amt": "3"}],
                    "text": "Deal twice the die to a front-row enemy, and you take 3."},
    "turnabout": {"name": "Turnabout", "req": {"n": 1}, "tgt": "foe", "melee": True,
                  "ops": [{"op": "dmg", "amt": "max(v,9-v)+2"}],
                  "text": "Deal the die or its opposite face (9 minus it), whichever is higher, +2."},
    "last_shot": {"name": "Last Shot", "once": True, "req": {"n": 1}, "tgt": "foe",
                  "ops": [{"op": "dmg", "amt": "v*3"}],
                  "text": "Once per fight, any row: deal three times the die."},
    "tether": {"name": "Tether", "req": {"n": 1}, "tgt": "other",
               "ops": [{"op": "tether"}, {"op": "armor", "amt": "v//2"}, {"op": "armor", "amt": "v//2", "to": "self"}],
               "text": "Tie yourself to an ally: you both gain half the die as Armor, and the first hit on either of you this round is split between you."},
    "magnetize": {"name": "Magnetize", "req": {"n": 1}, "tgt": "foe", "melee": True,
                  "ops": [{"op": "dmg", "amt": "v"}, {"op": "drag", "to": "foes"}],
                  "text": "Deal the die, and every enemy is pulled into the front row (Rooted ones stay put)."},
    "set_pike": {"name": "Set the Pike", "req": {"n": 1}, "tgt": "self",
                 "ops": [{"op": "status", "s": "counter", "n": "v*2", "to": "self"}],
                 "text": "The first enemy that attacks you this round takes twice the die before its hit lands."},
    "borrowed_time": {"name": "Borrowed Time", "req": {"n": 1}, "tgt": "foe",
                      "ops": [{"op": "dmg", "amt": "v//2"}, {"op": "refresh"}],
                      "text": "Any row: deal half the die, and your other skill with the longest cooldown left is ready again."},
    "mummify": {"name": "Mummify", "req": {"n": 1}, "tgt": "foe", "melee": True,
                "ops": [{"op": "dmg", "amt": "v"}, {"op": "status", "s": "mummy", "n": 1}],
                "text": "Deal the die. For the rest of the fight the enemy can't heal or gain Armor."},
    "sleep_dart": {"cd": 3, "name": "Sleep Dart", "req": {"n": 1}, "tgt": "foe",
                   "ops": [{"op": "dmg", "amt": "1"}, {"op": "delay"}],
                   "text": "Any row: deal 1. The enemy loses this round's attack, but its next hit deals half of it more."},
    "thorn_snare": {"name": "Thorn Snare", "req": {"n": 1}, "tgt": "foe",
                    "ops": [{"op": "status", "s": "snare", "n": "v+3"}],
                    "text": "Any row: snare the enemy. When it next attacks, it first takes the die +3 and is Rooted."},
    "judgment": {"name": "Judgment", "req": {"n": 1}, "tgt": "foe", "melee": True,
                 "ops": [{"op": "dmg", "amt": "v+2+2*min(3,grudge)"}],
                 "text": "Deal the die +2, and 2 more for each hero that enemy has hit this fight (up to +6)."},
    "lifebinding": {"name": "Lifebinding Arrow", "req": {"n": 1}, "tgt": "foe",
                    "ops": [{"op": "dmg", "amt": "v", "bind": True}],
                    "text": "Any row: deal the die, and your ally with the lowest HP heals half of what it dealt."},
    "splinter": {"name": "Splinter", "req": {"n": 1}, "tgt": "foe",
                 "ops": [{"op": "dmg", "amt": "v+1", "if": "v>=3"}, {"op": "dmg", "amt": "4", "to": "foes", "if": "v<=2"}],
                 "text": "Any row: deal the die +1. On a 1 or 2 it splinters: every enemy takes 4 instead."},
    "mirror": {"name": "Mirror", "req": {"n": 1}, "tgt": "self",
               "ops": [{"op": "mirror"}],
               "text": "Repeat the last attack or heal an ally played this round, with this die (its damage, healing, Armor and statuses)."},
    "sleep_thread": {"cd": 3, "name": "Sleep Thread", "req": {"n": 1}, "tgt": "foe",
                     "ops": [{"op": "sleep"}],
                     "text": "Any row: the enemy falls asleep and skips its attack this round, but wakes the moment anyone hits it."},
    "icefall": {"name": "Icefall", "req": {"n": 1}, "tgt": "foe", "melee": True,
                "ops": [{"op": "dmg", "amt": "v"}, {"op": "dmg", "amt": "v", "to": "frozen"}],
                "text": "Deal the die to the enemy, and every other Frozen enemy also takes the die."},
    "rime_guard": {"name": "Rime Guard", "req": {"n": 1}, "tgt": "other",
                   "ops": [{"op": "armor", "amt": "v"}, {"op": "armor", "amt": "v", "to": "self"},
                           {"op": "status", "s": "chill", "n": 1}, {"op": "status", "s": "chill", "n": 1, "to": "self"}],
                   "text": "You and an ally gain the die as Armor. The next enemy to hit either of you this round is Frozen."},
})


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
                     "Cinders: your spells also Burn 1.", "ash", ["cinder_rain"]),
    "slagplate": _g("Slagplate", A, "rare", [3, 4, "S", "S", 6, 7], {"thorns": 3, "burn_immune": 1},
                    "Molten skin: enemies that hit you take 3, and you can't be Burned.", "ash", guard="bristle"),
    "salamander_scale": _g("Salamander Scale", A, "uncommon", [1, 2, 3, "S", 5, 6], {"burn_immune": 1, "regen": 1},
                           "Fireproof: you can't be Burned, and you heal 1 each round in fights.", "ash", guard="second_wind"),
    "cinder_heart": _g("Cinder Heart", T, "rare", [1, 2, "F3", 4, "F5", "F6"], {"burn_bonus": 1, "might": 1},
                       "Banked fire: your Burns are 1 stronger, and +1 damage on every hit.", "ash"),

    # ---------------------------------------------------------------- the Shifting Sands: bronze and sandglass
    "khopesh": _g("Khopesh", W, "uncommon", [1, 2, 3, 4, 5, 6, 7, "W"], {"execute_bonus": 3},
                  "Hooked edge: +3 damage against enemies below half health.", "dunes", ["disarm"]),
    "sandstorm_staff": _g("Sandstorm Staff", W, "rare", [1, 2, 3, 4, 5, 6, 7, 8, 9, "W"], {"open_weak": 1},
                          "Blinding sand: every enemy is Weak for the fight's first round.", "dunes", ["sandwind", "sand_eyes"]),
    "scarab_bow": _g("Scarab Bow", W, "common", [1, 2, 3, 4, "P5", 6], {"first_strike": 2},
                     "Desert ambush: your first hit each fight deals +2.", "dunes", ["shoot"]),
    "nomad_wraps": _g("Nomad's Wraps", A, "common", [1, 2, 3, "S"], {"move": 1},
                      "Light on the sand: +1 move on the map.", "dunes", guard="sidestep"),
    "sphinx_mantle": _g("Sphinx Mantle", A, "rare", [2, 3, 4, "S", "S", 6], {"silver_voice": 1, "max_hp": 4},
                        "Riddler's wit: +1 to every event roll. +4 max HP.", "dunes", dk=["seer"], guard="echo_shell"),
    "scarab_amulet": _g("Scarab Amulet", T, "rare", D(6), {"unbreakable": 1},
                        "Rebirth: once a fight, survive a lethal hit at 1 HP.", "dunes"),
    "oasis_flask": _g("Oasis Flask", T, "uncommon", D(6), {"rest_bonus": 0.2, "regen": 1},
                      "Sweet water: resting heals an extra 20% of your max HP, and you heal 1 each round in fights.", "dunes", acts=["cool_water"]),

    # ---------------------------------------------------------------- the Stillwood: stone and amber
    "petrified_club": _g("Petrified Club", W, "common", [2, 3, 3, 4, "S", 6], {"opportunist": 2},
                         "Heavy as stone: +2 damage against Stunned or Rooted enemies.", "petrified", ["crush"]),
    "gorgon_glaive": _g("Gorgon Glaive", W, "rare", [1, 2, 3, 4, 5, 6, 7, 8, "W", 10], {"opportunist": 3},
                        "Stone gaze: +3 damage against Stunned or Rooted enemies.", "petrified", ["stonebolt", "reaping_arc"]),
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
    "jaguar_pelt": _g("Jaguar Pelt", A, "rare", [2, 3, 4, 5, "S", 7], {"backstab": 4},
                      "Prowler: +4 damage against enemies aiming at someone else.",
                      "jungle", guard="riposte_stance"),
    "jade_frog": _g("Jade Frog", T, "uncommon", D(6), {"kill_heal": 3, "regen": 1},
                    "Lucky frog: heal 3 whenever you kill an enemy, and 1 each round in fights.", "jungle"),

    # ---------------------------------------------------------------- Aetherhold: gold and white light
    "seraph_blade": _g("Seraph Blade", W, "legendary", [1, 2, 3, "S", 5, 6, 7, 8, 9, 10, "W", 12], {"heal_armor": 2, "engage": 3},
                       "Halo: anyone you heal also gains 2 Armor, and +3 damage against enemies at full health.",
                       "heaven", ["radiant", "sweep"], dk=["augur"]),
    "sunlance": _g("Sunlance", W, "uncommon", [1, 2, 3, 4, "F5", 6, 7, 8], {"engage": 3},
                   "Dawn strike: +3 damage against enemies at full health.", "heaven", ["thrust", "radiant"]),
    "hymnal": _g("Hymnal", W, "common", D(6), {"heal_bonus": 1, "max_hp": 2},
                 "Psalms: your heals are 1 stronger. +2 max HP.", "heaven", ["blessing"]),
    "guardian_mantle": _g("Guardian's Mantle", A, "rare", [2, 3, 4, "S", "S", 7], {"last_stand": 5, "max_hp": 3},
                          "Last light: while you're at half HP or less, gain 5 Armor each round. +3 max HP.", "heaven", guard="cover"),
    "vestment_of_light": _g("Vestment of Light", A, "uncommon", [1, 2, 3, 4, "S", 6], {"weak_immune": 1, "heal_bonus": 1},
                            "Unbowed: you can't be made Weak, and your heals are 1 stronger.", "heaven", guard="warding_light"),
    "angel_feather": _g("Angel Feather", T, "uncommon", [1, 2, 3, 4, 5, "W"], {"evasive": 1},
                        "Lighter than air: the first hit on you each fight deals half.", "heaven", acts=["featherlight"]),
    "sun_disc": _g("Sun Disc", T, "rare", [1, 2, 3, 4, 5, 6, 7, "W"], {"might": 1, "regen": 1},
                   "Noon: +1 damage on every hit, and heal 1 each round in fights.", "heaven"),

    # ---------------------------------------------------------------- the Prism Wood: glass and light
    "prism_staff": _g("Prism Staff", W, "rare", [1, 2, 3, 4, 5, 6, 7, "I8", 9, 10], {"spell_chain": 1},
                      "Refracted: a spell that hits one enemy also hits another for half.", "crystal", ["prism_ray", "prism_shield"], dk=["seer"]),
    "crystal_shiv": _g("Crystal Shiv", W, "common", D(6), {"keen_edge": 1},
                       "Razor facet: your 6s count as 7s.", "crystal", ["thrust"]),
    "geode_hammer": _g("Geode Hammer", W, "uncommon", [2, 3, 4, 5, 6, "S"], {"kill_armor": 3},
                       "Shatterproof: each kill gives you 3 Armor.", "crystal", ["crush"]),
    "crystal_carapace": _g("Crystal Carapace", A, "rare", [3, 4, "S", "S", "S", 6], {"first_hit_soak": 2, "thorns": 2},
                           "Faceted: the first hit on you each round deals 2 less, and enemies that hit you take 2.",
                           "crystal", guard="shell_up"),
    "prismweave_robe": _g("Prismweave Robe", A, "uncommon", D(6), {"spellweave": 2},
                          "Shifting colours: your spells deal +2 if you've cast a different spell earlier this round.",
                          "crystal", guard="fade"),
    "tuning_fork": _g("Tuning Fork", T, "uncommon", [1, "R", 3, 4, "R", 6], {"momentum": 1},
                      "Resonance: each of your actions after the first in a round deals +1, and its die has two "
                      "Resonance faces.", "crystal", acts=["resonate"]),
    "prism_shard": _g("Prism Shard", T, "rare", [1, 2, 3, 4, 5, "W"], {"eagle_eye": 1},
                      "Refraction: a die showing its highest face deals half again as much damage.", "crystal", dk=["fate"]),

    # ---------------------------------------------------------------- the Drowsing Vale: lavender and moonlight
    "dreamcatcher": _g("Dreamcatcher", W, "uncommon", [1, 2, 3, 4, 5, 6, "W", 8], {"debuff_ext": 1},
                       "Snared dreams: Weak, Vulnerable and Mark that you apply last a round longer.", "dream", ["lull", "nightmare"]),
    "sleepwalker_knife": _g("Sleepwalker's Knife", W, "rare", [1, 2, 3, 4, 5, 6, 7, 8, 9, "W"], {"unseen": 3},
                            "Unnoticed: while no enemy is aiming at you, your hits deal +3.", "dream", ["vanish", "lull"], dk=["fate"]),
    "moonsilk_robe": _g("Moonsilk Robe", A, "uncommon", [1, 2, 3, 4, "S", 6], {"stun_ward": 1, "rest_bonus": 0.1},
                        "Restful: ignore the first Stun each fight, and resting heals an extra 10% of your max HP.",
                        "dream", guard="hold_fast"),
    "nightmare_mail": _g("Nightmare Mail", A, "rare", [2, 3, 4, "S", "S", 6, 7, 8], {"heckler": 3, "max_hp": 3},
                         "Dread: each enemy's first attack each fight deals 3 less. +3 max HP.", "dream", guard="bristle"),
    "sandman_pouch": _g("Sandman's Pouch", T, "uncommon", D(6), {"cloak": 1},
                        "Drowse: each round, the first enemy that would attack you picks someone else (if there's anyone).", "dream"),
    "music_box": _g("Music Box", T, "rare", D(8), {"hymn_aura": 1, "reroll": 1},
                    "Lullaby: while you're above half health, the whole party deals +1 damage. +1 reroll per fight.", "dream", acts=["lullaby"]),

    # ---------------------------------------------------------------- the Frostpeaks: ice and fur
    "frostbrand": _g("Frostbrand", W, "rare", [1, 2, "I3", 4, 5, "I6", 7, 8, "I9", 10], {"frozen_bonus": 3},
                     "Bitter edge: Frozen enemies take +3 from you.", "frost", ["glacial", "shatter"]),
    "ice_pick": _g("Ice Pick", W, "common", [1, 2, 3, "I4", 5, 6], {"frozen_bonus": 2},
                   "Crack the ice: Frozen enemies take +2 from you.", "frost", ["hack"]),
    "yeti_hide": _g("Yeti Hide", A, "uncommon", [2, 2, 3, 3, 4, "S"], {"freeze_immune": 1, "max_hp": 5},
                    "Thick fur: your dice can't be Frozen. +5 max HP.", "frost", guard="hold_fast"),
    "glacier_plate": _g("Glacier Plate", A, "rare", ["S", "S", 4, 5, 6, 7], {"freeze_immune": 1, "first_hit_soak": 2, "max_hp": 6},
                        "Glacial: your dice can't be Frozen, and the first hit on you each round deals 2 less. +6 max HP.",
                        "frost", guard="shell_up"),
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
                          "dunes", ["royal_decree", "sandwind"], dk=["seer"], unique=True),
    "stillwood_heart": _g("Heart of the Stillwood", A, "legendary", ["S", "S", "S", "S", 7, 8, 9, 10],
                          {"start_armor": 8, "max_hp": 8},
                          "Timeless: start each fight with 8 Armor. +8 max HP.", "petrified", dk=["steady"], guard="stoneform", unique=True),
    "jade_fang": _g("Fang of the Jade Serpent", W, "legendary", [1, "P2", 3, "P4", 5, "P6", 7, "P8", 9, 10, "P11", 12],
                    {"plague": 1, "poison_bonus": 2},
                    "Serpent's venom: your Poisons are 2 stronger, and when a Poisoned enemy dies its Poison spreads to another.",
                    "jungle", ["venom_stab", "vinelash"], unique=True),
    "arbiter_wings": _g("Wings of the Arbiter", A, "legendary", ["S", "S", "S", 6, 7, 8, 9, 10],
                        {"evasive": 1, "overflow": 1, "max_hp": 6},
                        "Judgment's grace: the first hit on you each fight deals half, and healing beyond your max HP becomes Armor. +6 max HP.",
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
    "augur_bone": {"name": "Augur's Bone", "slot": "use", "rarity": "rare", "enchant": "augur",
                   "text": "Enchant a piece of gear you wear: its die is an Augur die (while you plan, it shows whether it "
                           "rolled high or low)."},
    "tidebell_shard": {"name": "Tidebell Shard", "slot": "use", "rarity": "rare", "forge": "tune", "found": True,
                       "text": "Tune a piece of gear you wear: its lowest number becomes a Resonance face (it copies the last "
                               "number an ally played). Doesn't count against its work limit."},
    "starmetal": {"name": "Starmetal Ingot", "slot": "use", "rarity": "legendary", "forge": "hone",
                  "text": "Hone a piece of gear you wear: its lowest number rises by 3. Doesn't count against its work limit."},
    "wyrm_ember": {"name": "Wyrm's Ember", "slot": "use", "rarity": "legendary", "forge": "mark",
                   "text": "Mark a piece of gear you wear: its lowest number becomes a special face (a shield on armor, "
                           "else more of its own kind, else a wild face). Doesn't count against its work limit."},
}

RELICS = [k for k, v in ITEMS.items() if v.get("unique")]
FORGE_MATS = [k for k, v in ITEMS.items() if v.get("forge") and not v.get("found")]


# ---------------------------------------------------------------- the armory: twenty more weapons (Nov 2026)
ITEMS.update({
    "tideforged_trident": _g("Tideforged Trident", W, "rare", [1, 2, 3, 4, 5, 6, "I7", 8, 9, 10], {"frozen_bonus": 2},
                             "Tide-cold: Frozen enemies take +2 from you.", None, ["skewer"]),
    "grappling_hook": _g("Grappling Hook", W, "common", D(6), {"move": 1}, "Climber: +1 move on the map.", None, ["snag"]),
    "bonesaw": _g("Bonesaw", W, "uncommon", [1, 2, 3, 4, 5, "P6"], {"execute_bonus": 2},
                  "Surgeon's eye: +2 damage against enemies below half health.", None, ["open_wound"]),
    "blunderbuss": _g("Blunderbuss", W, "uncommon", [1, 2, 3, 4, 5, 6, 7, "F8"], {"first_strike": 2},
                      "Opening volley: your first hit each fight deals +2.", None, ["point_blank"]),
    "gamblers_cutlass": _g("Gambler's Cutlass", W, "rare", [1, 2, 3, 4, 5, 6, 7, "W"], {"reroll": 1},
                           "Loaded luck: +1 automatic reroll per fight.", None, ["turnabout"]),
    "corsair_pistol": _g("Corsair's Pistol", W, "common", D(8), {"kill_gold": 2},
                         "Bounty: each kill gives you 2 gold.", None, ["last_shot"]),
    "rope_dart": _g("Bosun's Rope Dart", W, "uncommon", D(6), {"max_hp": 2}, "Knotted: +2 max HP.", None, ["tether"]),
    "lodestone_mace": _g("Lodestone Mace", W, "uncommon", [1, 2, 3, 4, "S", 6, 7, 8], {"opportunist": 2},
                         "Pinning weight: +2 damage against Stunned or Rooted enemies.", "petrified", ["magnetize"]),
    "fossil_pike": _g("Fossil Pike", W, "common", D(6), {"max_hp": 3}, "Old bones: +3 max HP.", "petrified", ["set_pike"]),
    "hourglass_blade": _g("Hourglass Blade", W, "rare", [1, 2, 3, 4, 5, 6, 7, 8, 9, "W"], {"silver_voice": 1},
                          "Patient: +1 to every event roll.", "dunes", ["borrowed_time"]),
    "scarab_flail": _g("Scarab Flail", W, "uncommon", [1, 2, 3, "P4", 5, 6, 7, 8], {"poison_bonus": 1},
                       "Beetle venom: your Poisons are 1 stronger.", "dunes", ["mummify"]),
    "tranq_pipe": _g("Tranquilizer Pipe", W, "uncommon", [1, "P2", 3, 4, "P5", 6], {"heckler": 2},
                     "Drowsy: each enemy's first attack each fight deals 2 less.", "jungle", ["sleep_dart"]),
    "thornvine_whip": _g("Thornvine Whip", W, "common", D(6), {"root_ext": 1},
                         "Clinging: your Roots last a round longer.", "jungle", ["thorn_snare"]),
    "judgment_halberd": _g("Halberd of Judgment", W, "rare", [1, 2, 3, 4, 5, 6, 7, 8, 9, "W"], {"heal_bonus": 1},
                           "Mercy: your heals are 1 stronger.", "heaven", ["judgment"]),
    "cherub_bow": _g("Cherub's Bow", W, "uncommon", D(8), {"max_hp": 3}, "Blessed: +3 max HP.", "heaven", ["lifebinding"]),
    "geode_sling": _g("Geode Sling", W, "common", D(6), {"keen_edge": 1}, "Razor facet: your 6s count as 7s.", "crystal", ["splinter"]),
    "mirror_blade": _g("Mirror Blade", W, "rare", [1, 2, 3, 4, 5, 6, 7, "W"], {"might": 1},
                       "Bright edge: +1 damage on every hit.", "crystal", ["mirror"]),
    "dream_needle": _g("Dreamweaver's Needle", W, "uncommon", D(8), {"debuff_ext": 1},
                       "Snared dreams: Weak, Vulnerable and Mark that you apply last a round longer.", "dream", ["sleep_thread"]),
    "icebreaker_axe": _g("Icebreaker Axe", W, "uncommon", [1, 2, "I3", 4, 5, "I6", 7, 8], {"freeze_immune": 1},
                         "Warm grip: your dice can't be Frozen.", "frost", ["icefall"]),
    "glacier_lance": _g("Glacier Lance", W, "rare", [1, 2, 3, "I4", 5, 6, 7, "I8", 9, 10], {"frozen_bonus": 3},
                        "Bitter cold: Frozen enemies take +3 from you.", "frost", ["rime_guard"]),
})

# ---------------------------------------------------------------- more regional trinkets (Nov 2026)
ITEMS.update({
    "tinderbox": _g("Tinderbox", T, "uncommon", [1, 2, "F3", 4, "F5", 6], {"burn_bonus": 1},
                    "Dry tinder: your Burns are 1 stronger.", "ash", ["warm_hands"]),
    "prayer_beads": _g("Prayer Beads", T, "common", D(4), {"heal_bonus": 1},
                       "Devotion: your heals are 1 stronger.", "heaven", ["benediction_bead"]),
    "frost_charm": _g("Frostbitten Charm", T, "common", [1, "I2", 3, 4], {"frozen_bonus": 1},
                      "Chilled: Frozen enemies take +1 from you.", "frost"),
})
