"""More enemies for the first three regions and the Peak (Nov 2026: they had 5 of their own each, the
Peak 1). Merged into `archipelago.FOES` and `POOLS`, and their crits into `foes.FOE_CRIT`, the way
biomes.py's are; the groups and lineups that use them are in archipelago.py. Same format as there."""


def _d(n, *dk):
    return {"faces": list(range(1, n + 1)), "dk": list(dk)}


SPINES = {"faces": [1, 2, "P3", "S", 5, 6], "dk": []}            # an urchin: poison spines, a shell face
SHELL = {"faces": [1, 2, 3, "S", "S", 6], "dk": []}
FUSE = {"faces": [1, 2, "F3", "F4", 5, 6], "dk": []}
CORAL = {"faces": [1, 2, 3, "S", 5, 6, "S", 8], "dk": []}         # living coral: hard to hurt
DEEP_ICE = {"faces": [1, 2, "I3", 4, "I5", 6, 7, 8], "dk": []}

FOES = {
    # ---------------------------------------------------------------- Coral Shallows
    "urchin": {"name": "Spine Urchin", "hp": 10, "row": "front", "speed": 2, "beast": True, "xp": 4, "gold": 3, "thorns": 3,
               "dice": [SPINES],
               "moves": {"roll": {"name": "Spine Roll", "k": "attack", "n": 1, "w": 2},
                         "bristle": {"name": "Bristle", "k": "block", "n": 1}}},
    "kelp_strangler": {"name": "Kelp Strangler", "hp": 14, "row": "front", "speed": 3, "beast": True, "xp": 5, "gold": 3,
                       "dice": [_d(6), _d(6)],
                       "moves": {"entangle": {"name": "Entangle", "k": "attack", "n": 1, "st": "root", "sn": 1, "tgt": "strongest", "w": 2},
                                 "drag": {"name": "Drag Down", "k": "attack", "n": 2, "pair": {"st": "weak", "sn": 1}}}},
    "pearl_diver": {"name": "Drowned Pearl Diver", "hp": 9, "row": "back", "speed": 5, "undead": True, "xp": 5, "gold": 6,
                    "dice": [_d(6, "seer"), _d(4)],
                    "moves": {"harpoon": {"name": "Harpoon", "k": "attack", "use": [0], "tgt": "weakest", "st": "vuln", "sn": 1, "w": 2},
                              "glint": {"name": "Pearl Glint", "k": "debuff", "use": [0], "st": "weak", "sn": 1, "st_min": 4}}},

    # ---------------------------------------------------------------- Smugglers' Keys
    "rum_runner": {"name": "Rum Runner", "hp": 11, "row": "front", "speed": 6, "xp": 4, "gold": 6,
                   "dice": [FUSE],
                   "moves": {"bottle": {"name": "Bottle Smash", "k": "attack", "n": 1, "w": 2},
                             "swig": {"name": "Swig", "k": "heal", "n": 1, "self": True}}},
    "parrot": {"name": "Lookout Parrot", "hp": 6, "row": "back", "speed": 9, "beast": True, "xp": 3, "gold": 2, "pack": 1,
               "dice": [_d(4), _d(4)],
               "moves": {"peck": {"name": "Peck", "k": "attack", "n": 1, "w": 2},
                         "squawk": {"name": "Squawk!", "k": "debuff", "n": 1, "st": "mark", "sn": 1, "tgt": "strongest"}}},
    "quartermaster": {"name": "Smuggler Quartermaster", "hp": 13, "row": "back", "speed": 3, "xp": 6, "gold": 9,
                      "dice": [_d(8), _d(6)],
                      "moves": {"blunderbuss": {"name": "Blunderbuss", "k": "attack", "use": [0], "sweep": 2, "w": 2},
                                "rations": {"name": "Hand Out Grog", "k": "heal", "use": [1]},
                                "pay": {"name": "Double Pay", "k": "buff", "v": 1}}},

    # ---------------------------------------------------------------- Stormcrag
    "rockling": {"name": "Cliffside Rockling", "hp": 14, "row": "front", "speed": 2, "xp": 5, "gold": 3, "shell_min": 3,
                 "dice": [_d(6, "steady"), SHELL],
                 "moves": {"tumble": {"name": "Tumble", "k": "attack", "n": 2, "pair": {"st": "stun", "sn": 1}, "w": 2},
                           "settle": {"name": "Settle", "k": "block", "n": 2}}},
    "gale_sprite": {"name": "Gale Sprite", "hp": 7, "row": "back", "speed": 8, "xp": 3, "gold": 3,
                    "dice": [_d(6)],
                    "moves": {"gust": {"name": "Gust", "k": "attack", "n": 1, "chain": True, "w": 2},
                              "tailwind": {"name": "Tailwind", "k": "buff", "v": 1}}},
    "stormcaller": {"name": "Stormcaller Acolyte", "hp": 11, "row": "back", "speed": 3, "xp": 6, "gold": 6,
                    "dice": [_d(8), _d(4, "seer")],
                    "moves": {"call": {"name": "Call Lightning", "k": "attack", "use": [0], "st": "shock", "sn": 1, "w": 2},
                              "ward": {"name": "Thunder Ward", "k": "guard", "use": [1], "all": True},
                              "rain": {"name": "Hard Rain", "k": "all", "use": [1], "st": "static", "sn": 1, "st_min": 4}}},

    # ---------------------------------------------------------------- the Peak: the Drowned Crown's court
    "drowned_knight": {"name": "Drowned Knight", "hp": 20, "row": "front", "speed": 3, "undead": True, "xp": 7, "gold": 4,
                       "dice": [_d(8), _d(6)],
                       "moves": {"blade": {"name": "Sunken Blade", "k": "attack", "use": [0], "w": 2},
                                 "ready": {"name": "Raise the Blade", "k": "charge", "next": "cleave"},
                                 "cleave": {"name": "Tidal Cleave", "k": "attack", "use": [0, 1], "sweep": 2, "w": 0}}},
    "crown_herald": {"name": "Crown Herald", "hp": 12, "row": "back", "speed": 4, "undead": True, "xp": 6, "gold": 5,
                     "dice": [_d(6), _d(6, "seer")],
                     "moves": {"proclaim": {"name": "Proclamation", "k": "buff", "v": 2, "w": 2},
                               "doom": {"name": "Pronounce Doom", "k": "debuff", "use": [1], "st": "hex", "sn": 1, "st_min": 3,
                                        "tgt": "strongest"},
                               "rod": {"name": "Rod of Office", "k": "attack", "use": [0]}}},
    "abyss_angler": {"name": "Abyssal Angler", "hp": 14, "row": "back", "speed": 4, "beast": True, "xp": 6, "gold": 4,
                     "dice": [_d(8), _d(4)],
                     "moves": {"lure": {"name": "Lure Light", "k": "debuff", "use": [1], "st": "mark", "sn": 1, "tgt": "weakest"},
                               "maw": {"name": "Abyssal Bite", "k": "attack", "use": [0, 1], "tgt": "weakest", "w": 2}}},
    "brine_wraith": {"name": "Brine Wraith", "hp": 10, "row": "back", "speed": 6, "undead": True, "xp": 6, "gold": 3, "leech": True,
                     "dice": [DEEP_ICE],
                     "moves": {"chill": {"name": "Drowning Chill", "k": "attack", "n": 1, "st": "weak", "sn": 1, "w": 2},
                               "seep": {"name": "Seep In", "k": "attack", "n": 1, "each": True, "tgt": "strongest"}}},
    "coral_colossus": {"name": "Coral Colossus", "hp": 26, "row": "front", "speed": 1, "xp": 9, "gold": 5, "thorns": 2,
                       "shell_min": 4,
                       "dice": [CORAL, _d(8, "steady")],
                       "moves": {"crush": {"name": "Crushing Reef", "k": "attack", "use": [0, 1], "pair": {"st": "stun", "sn": 1}, "w": 2},
                                 "grow": {"name": "Grow Coral", "k": "block", "use": [0, 1]}}},
}

POOLS = {
    "urchin": {"needle": {"name": "Needle Burst", "k": "all", "n": 1, "st": "poison", "sn": 1, "st_min": 5},
               "anchor": {"name": "Cling Fast", "k": "guard", "n": 1}},
    "kelp_strangler": {"choke": {"name": "Choke", "k": "attack", "n": 2, "tgt": "weakest"},
                       "sway": {"name": "Sway", "k": "block", "n": 1}},
    "pearl_diver": {"spear": {"name": "Spear Lunge", "k": "attack", "use": [0, 1]},
                    "pearls": {"name": "Pearls for the Deep", "k": "summon", "f": "deckhand"}},
    "rum_runner": {"firebottle": {"name": "Firebottle", "k": "attack", "n": 1, "st": "burn", "sn": 2},
                   "toast": {"name": "A Toast!", "k": "buff", "v": 1}},
    "parrot": {"pilfer": {"name": "Pilfer", "k": "thief"},
               "flurry": {"name": "Feather Flurry", "k": "attack", "n": 2, "each": True}},
    "quartermaster": {"ledger": {"name": "Settle the Ledger", "k": "debuff", "use": [1], "st": "vuln", "sn": 1},
                      "crates": {"name": "Crate Wall", "k": "guard", "use": [0], "all": True}},
    "rockling": {"split": {"name": "Shed Pebbles", "k": "attack", "n": 2, "each": True},
                 "avalanche": {"name": "Small Avalanche", "k": "all", "n": 1, "st_min": 5, "st": "weak", "sn": 1}},
    "gale_sprite": {"whirl": {"name": "Whirlwind", "k": "all", "n": 1},
                    "slip": {"name": "Slip the Wind", "k": "block", "n": 1}},
    "stormcaller": {"summon": {"name": "Raise a Wisp", "k": "summon", "f": "storm_wisp"},
                    "fork": {"name": "Forked Bolt", "k": "attack", "use": [0], "chain": True}},
    "drowned_knight": {"oath": {"name": "Drowned Oath", "k": "guard", "use": [1], "all": True},
                       "riposte": {"name": "Riposte", "k": "attack", "use": [1], "tgt": "vengeful", "st": "vuln", "sn": 1}},
    "crown_herald": {"summons": {"name": "Summon the Court", "k": "summon", "f": "tide_guard"},
                     "decree": {"name": "Decree", "k": "all", "use": [1], "st": "weak", "sn": 1, "st_min": 5}},
    "abyss_angler": {"dark": {"name": "Lights Out", "k": "block", "use": [0]},
                     "gulp": {"name": "Gulp", "k": "attack", "use": [0], "tgt": "weakest", "st": "root", "sn": 1}},
    "brine_wraith": {"wail": {"name": "Deep Wail", "k": "all", "n": 1, "st": "weak", "sn": 1, "st_min": 6},
                     "fade": {"name": "Fade", "k": "block", "n": 1}},
    "coral_colossus": {"reef": {"name": "Reef Wall", "k": "guard", "use": [1], "all": True},
                       "shards": {"name": "Coral Shards", "k": "attack", "use": [0], "sweep": 2}},
}

# Enemy crits (foes.FOE_CRIT): what a top-face hit adds.
CRITS = {
    "urchin": ("poison", 2), "kelp_strangler": ("root", 1), "pearl_diver": ("vuln", 1),
    "rum_runner": ("burn", 2), "parrot": ("mark", 1), "quartermaster": ("half", None),
    "rockling": ("weak", 1), "gale_sprite": ("weak", 1), "stormcaller": ("shock", 1),
    "drowned_knight": ("half", None), "crown_herald": ("hex", 1), "abyss_angler": ("vuln", 1),
    "brine_wraith": ("freeze", 1), "coral_colossus": ("half", None),
}
