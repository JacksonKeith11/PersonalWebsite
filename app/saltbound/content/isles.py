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

# ---------------------------------------------------------------- the final bosses (one is drawn per run: FINALS)
# Each final works like the Drowned Crown (bosses.py): warded while its `court` stands, then at two thirds of its
# health the `drag` (a blow marked on a hero, landing at the round's end) and its `deluge`, and at a third alone,
# exposed and furious. `phase_text` is what's said at each change, `win_text` when it falls.
FINAL_FOES = {
    "leviathan": {"name": "The Abyssal Leviathan", "hp": 110, "row": "back", "speed": 3, "boss": True, "final": True,
                  "beast": True, "xp": 0, "gold": 0,
                  "dice": [_d(10), _d(10), _d(8), _d(6)],
                  "seq": ["slam", "ink", "lure", "coil", "roar"],
                  "moves": {"slam": {"name": "Tail Slam", "k": "attack", "use": [0, 1], "tgt": "strongest", "brk": 0.3},
                            "ink": {"name": "Ink Cloud", "k": "all", "use": [3], "st": "weak", "sn": 1, "st_min": 4},
                            "lure": {"name": "Lights in the Deep", "k": "summon", "f": "abyss_angler"},
                            "coil": {"name": "Coil", "k": "attack", "use": [2], "tgt": "weakest", "st": "root", "sn": 1},
                            "roar": {"name": "Abyssal Roar", "k": "all", "use": [2]},
                            "breach": {"name": "The Breach", "k": "all", "use": [0, 1, 2, 3], "brk": 0.3}},
                  "court": "abyss_angler", "drag": "Crushing Coils", "deluge": "breach",
                  "phase_text": ["The Leviathan rises from the deep: each round its coils crush someone. Armor or a Guard stops "
                                 "it. Next round it breaches.",
                                 "The Leviathan's lures go dark: it fights alone, exposed, and furious. Next round it breaches."],
                  "win_text": "The Abyssal Leviathan sinks back into the dark it came from. The isles are saved!"},
    "storm_queen": {"name": "The Storm Queen", "hp": 95, "row": "back", "speed": 5, "boss": True, "final": True,
                    "xp": 0, "gold": 0,
                    "dice": [_d(10, "exploding"), _d(8), _d(8), _d(6)],
                    "seq": ["bolt", "thunder", "call", "gale", "brand"],
                    "moves": {"bolt": {"name": "Chain Lightning", "k": "attack", "use": [0], "chain": True, "st": "shock", "sn": 1},
                              "thunder": {"name": "Thunderclap", "k": "all", "use": [3], "st": "stun", "sn": 1, "st_min": 6},
                              "call": {"name": "Call the Faithful", "k": "summon", "f": "stormcaller"},
                              "gale": {"name": "Gale Wall", "k": "guard", "use": [1], "all": True},
                              "brand": {"name": "Storm Brand", "k": "debuff", "use": [3], "st": "mark", "sn": 1, "tgt": "strongest"},
                              "tempest": {"name": "The Tempest", "k": "all", "use": [0, 1, 2, 3], "brk": 0.3}},
                    "court": "stormcaller", "drag": "Lightning Strike", "deluge": "tempest",
                    "phase_text": ["The sky breaks open: each round lightning picks someone out. Armor or a Guard stops it. "
                                   "Next round the Tempest hits everyone.",
                                   "Her acolytes burn out: the Storm Queen fights alone, exposed, and furious. Next round the "
                                   "Tempest hits everyone."],
                    "win_text": "The Storm Queen's crown cracks, and the sky clears over the isles. The isles are saved!"},
}
FOES.update(FINAL_FOES)

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
    "leviathan": {"swallow": {"name": "Swallow the Light", "k": "heal", "use": [1], "self": True},
                  "wake": {"name": "Wake", "k": "attack", "use": [0, 1], "sweep": 2}},
    "storm_queen": {"hail": {"name": "Hailstorm", "k": "all", "use": [2], "st": "weak", "sn": 1, "st_min": 6},
                    "eye": {"name": "Eye of the Storm", "k": "attack", "use": [0, 1], "tgt": "weakest", "st": "shock", "sn": 2}},
    "coral_colossus": {"reef": {"name": "Reef Wall", "k": "guard", "use": [1], "all": True},
                       "shards": {"name": "Coral Shards", "k": "attack", "use": [0], "sweep": 2}},
}

# Enemy crits (foes.FOE_CRIT): what a top-face hit adds.
CRITS = {
    "urchin": ("poison", 2), "kelp_strangler": ("root", 1), "pearl_diver": ("vuln", 1),
    "rum_runner": ("burn", 2), "parrot": ("mark", 1), "quartermaster": ("half", None),
    "rockling": ("weak", 1), "gale_sprite": ("weak", 1), "stormcaller": ("shock", 1),
    "drowned_knight": ("half", None), "crown_herald": ("hex", 1), "abyss_angler": ("vuln", 1),
    "brine_wraith": ("freeze", 1), "coral_colossus": ("half", None), "leviathan": ("half", None), "storm_queen": ("half", None),
}
