"""The Sinking Archipelago: its enemies, dungeons, final boss, events and shrine blessings.

Enemies have dice and moves (see `app/saltbound/foes.py` for how they work): `dice` is the pool,
`moves` what it can do with them (`w` the weight when picked at random, default 1), and `seq`, if
present, the order it goes through them instead. Traits: `thorns` N (whoever damages it takes N),
`pack` N (+N might when another enemy dies), `leech` (heals half the damage it deals), `volatile` N
(bursts for N on every hero when it dies). Enemies keep front and back rows (melee reaches the
front); heroes have none.
"""

# Dice used below. Faces: numbers, "X" skull, "S" shield, "W" wild, "F4"/"I4"/"P4" elemental.
def _d(n, *dk):
    return {"faces": list(range(1, n + 1)), "dk": list(dk)}


ROTTEN = {"faces": ["X", 2, 3, 4, 5, 6], "dk": []}           # a skull where the 1 should be
SHELL = {"faces": [1, 2, 3, "S", "S", 6], "dk": []}          # shield faces: it hides instead
TOXIC = {"faces": [1, "P2", "P3", 4], "dk": []}               # poison faces
FUSE = {"faces": [1, 2, "F3", "F4", 5, 6], "dk": []}         # fire faces
SEARING = {"faces": [1, 2, 3, 4, "F5", "F6", 7, 8], "dk": []}
FROST = {"faces": [1, 2, 3, "I4", 5, "I6", 7, 8, 9, 10], "dk": []}

FOES = {
    # ---------------------------------------------------------------- Coral Shallows
    "deckhand": {"name": "Drowned Deckhand", "hp": 12, "row": "front", "speed": 3, "undead": True, "xp": 4, "gold": 3,
                 "dice": [ROTTEN, ROTTEN],
                 "moves": {"hook": {"name": "Rusty Hook", "k": "attack", "n": 1, "w": 2},
                           "flail": {"name": "Flailing Swings", "k": "attack", "n": 2, "each": True}}},
    "crab": {"name": "Crabfolk Brute", "hp": 16, "row": "front", "speed": 2, "beast": True, "xp": 5, "gold": 4, "thorns": 2,
             "dice": [_d(6), SHELL],
             "moves": {"pinch": {"name": "Pinch", "k": "attack", "n": 1, "w": 2},
                       "clamp": {"name": "Clamp", "k": "attack", "n": 2, "pair": {"st": "root", "sn": 1}},
                       "shell": {"name": "Shell Up", "k": "block", "n": 2}}},
    "jelly": {"name": "Jellyfloat", "hp": 8, "row": "front", "speed": 4, "beast": True, "xp": 3, "gold": 2, "leech": True, "splits": True,
              "dice": [TOXIC],
              "moves": {"sting": {"name": "Sting", "k": "attack", "n": 1}}},
    "eel": {"name": "Reef Eel", "hp": 9, "row": "back", "speed": 6, "beast": True, "xp": 4, "gold": 3,
            "dice": [_d(4), _d(4)],
            "moves": {"bite": {"name": "Snapping Bites", "k": "attack", "n": 2, "each": True, "pair": {"st": "shock", "sn": 1}, "w": 2},
                      "jolt": {"name": "Jolt", "k": "attack", "n": 2, "st": "shock", "sn": 1}}},
    "barnacle_priest": {"name": "Barnacle Priest", "hp": 10, "row": "back", "speed": 2, "undead": True, "xp": 5, "gold": 5,
                        "dice": [_d(6), _d(4)],
                        "moves": {"mend": {"name": "Mend Flesh", "k": "heal", "n": 2, "w": 2},
                                  "spit": {"name": "Brine Spit", "k": "attack", "use": [1], "st": "weak", "sn": 1},
                                  "crust": {"name": "Barnacle Crust", "k": "debuff", "use": [1], "st": "lock", "sn": 1, "tgt": "strongest"}}},
    "siren": {"name": "Siren", "hp": 9, "row": "back", "speed": 5, "xp": 5, "gold": 5,
              "dice": [_d(6, "seer")],
              "moves": {"lullaby": {"name": "Lullaby", "k": "debuff", "n": 1, "st": "stun", "sn": 1, "st_min": 4},
                        "dirge": {"name": "Drowning Song", "k": "debuff", "n": 1, "st": "hex", "sn": 1, "st_min": 3},
                        "shriek": {"name": "Shriek", "k": "attack", "n": 1, "w": 2}}},
    "bell_warden": {"name": "The Bell-Warden", "hp": 70, "row": "front", "speed": 3, "undead": True, "boss": True,
                    "xp": 40, "gold": 30,
                    "dice": [_d(8), _d(8), {"faces": [1, 2, 3, 4, 5, 6], "dk": ["seer"]}],
                    "seq": ["swing", "toll", "ring", "crush"],
                    "moves": {"swing": {"name": "Censer Swing", "k": "attack", "use": [0, 1], "pair": {"st": "stun", "sn": 1}},
                              "toll": {"name": "Toll the Bell", "k": "all", "use": [2], "st": "stun", "sn": 1, "st_min": 6},
                              "ring": {"name": "Ring for the Drowned", "k": "summon", "f": "deckhand"},
                              "crush": {"name": "Bell Drop", "k": "attack", "use": [0, 1, 2], "tgt": "vengeful"},
                              # never in `seq`: it comes when the knell counts down (`Bosses.foe_round`)
                              "knell": {"name": "Death Knell", "k": "all", "use": [0, 1], "st": "hex", "sn": 1}},
                    "bloodied": {"might": 2, "rule": "requiem", "text": "it tolls a requiem: the Death Knell comes every other round.",
                                 "moves": {"peal": {"name": "Grave Peal", "k": "all", "use": [2], "st": "stun", "sn": 1, "st_min": 6}}}},

    # ---------------------------------------------------------------- Smugglers' Keys
    "cutthroat": {"name": "Cutthroat", "hp": 11, "row": "front", "speed": 7, "xp": 4, "gold": 5,
                  "dice": [_d(6, "exploding")],
                  "moves": {"shiv": {"name": "Shiv", "k": "attack", "n": 1, "st": "vuln", "sn": 1, "w": 2},
                            "low_blow": {"name": "Low Blow", "k": "attack", "n": 1, "st": "weak", "sn": 1, "tgt": "vengeful"},
                            "filch": {"name": "Filch", "k": "attack", "n": 1, "st": "steal", "sn": 1, "tgt": "strongest"}}},
    "deckhound": {"name": "Deckhound", "hp": 9, "row": "front", "speed": 8, "beast": True, "xp": 3, "gold": 1, "pack": 2,
                  "dice": [_d(4), _d(4)],
                  "moves": {"savage": {"name": "Savage", "k": "attack", "n": 2, "each": True, "tgt": "weakest"}}},
    "brine_golem": {"name": "Brine Golem", "hp": 24, "row": "front", "speed": 1, "xp": 7, "gold": 3, "shell_min": 4,
                    "dice": [_d(8, "steady"), _d(8, "steady")],
                    "moves": {"slam": {"name": "Slam", "k": "attack", "n": 2, "pair": {"st": "stun", "sn": 1}, "w": 2},
                              "harden": {"name": "Harden", "k": "block", "n": 2}}},
    "powder_monkey": {"name": "Powder Monkey", "hp": 8, "row": "back", "speed": 5, "xp": 4, "gold": 4, "volatile": 4,
                      "dice": [FUSE],
                      "moves": {"keg": {"name": "Powder Keg", "k": "attack", "n": 1, "sweep": 2}}},
    "tide_cultist": {"name": "Tide Cultist", "hp": 10, "row": "back", "speed": 3, "xp": 5, "gold": 5,
                     "dice": [_d(6), _d(4, "seer")],
                     "moves": {"rite": {"name": "Blood Rite", "k": "buff", "v": 2},
                               "curse": {"name": "Tide Curse", "k": "debuff", "use": [1], "st": "hex", "sn": 1, "st_min": 2},
                               "mend": {"name": "Dark Mending", "k": "heal", "use": [0]},
                               "lash": {"name": "Lash", "k": "attack", "use": [0]}}},
    "corsair_captain": {"name": "Corsair Captain", "hp": 18, "row": "back", "speed": 4, "xp": 9, "gold": 12, "elite": True,
                        "dice": [_d(8, "exploding"), _d(6)],
                        "moves": {"pistol": {"name": "Pistol Shot", "k": "attack", "use": [0], "tgt": "weakest", "w": 2},
                                  "flurry": {"name": "Cutlass Flurry", "k": "attack", "n": 2, "each": True},
                                  "rally": {"name": "Rally the Crew", "k": "buff", "v": 2}}},
    "gallows_admiral": {"name": "The Gallows Admiral", "hp": 80, "row": "back", "speed": 3, "boss": True,
                        "xp": 40, "gold": 40,
                        "dice": [_d(8), _d(8, "exploding"), _d(8), _d(6)],
                        "seq": ["guns", "volley", "boarders", "noose", "broadside"],
                        "moves": {"broadside": {"name": "Broadside", "k": "all", "use": [0]},
                                  "boarders": {"name": "Boarders, Away!", "k": "summon", "f": "cutthroat"},
                                  "guns": {"name": "Run Out the Guns", "k": "summon", "f": "cannon"},
                                  "volley": {"name": "Pistol Volley", "k": "attack", "use": [0, 1, 2], "each": True},
                                  "noose": {"name": "Hang 'em High", "k": "attack", "use": [1, 3], "st": "root", "sn": 1, "tgt": "strongest"}},
                        "bloodied": {"might": 2, "rule": "kegs", "text": "he rolls out powder kegs. Break one and it blows up among his crew.",
                                     "moves": {"grapeshot": {"name": "Grapeshot", "k": "attack", "use": [0, 2, 3], "each": True}}}},

    # ---------------------------------------------------------------- Stormcrag
    "crag_ram": {"name": "Crag Ram", "hp": 15, "row": "front", "speed": 4, "beast": True, "xp": 5, "gold": 2,
                 "dice": [_d(6), _d(6)],
                 "moves": {"ram": {"name": "Ram", "k": "attack", "n": 2, "pair": {"st": "stun", "sn": 1}, "w": 2},
                           "horns": {"name": "Lower Horns", "k": "charge"}}},
    "cliff_hermit": {"name": "Cliff Hermit", "hp": 12, "row": "front", "speed": 3, "xp": 4, "gold": 6,
                     "dice": [_d(6, "fate"), _d(4)],
                     "moves": {"snare": {"name": "Snare", "k": "attack", "use": [0], "st": "root", "sn": 1, "w": 2},
                               "hide": {"name": "Hide in the Rocks", "k": "block", "n": 2}}},
    "harpy": {"name": "Harpy", "hp": 9, "row": "back", "speed": 7, "beast": True, "xp": 4, "gold": 3, "pack": 2,
              "dice": [_d(4), _d(6)],
              "moves": {"talons": {"name": "Raking Talons", "k": "attack", "n": 2, "each": True, "w": 2},
                        "snatch_potion": {"name": "Snatch", "k": "thief"}}},
    "storm_wisp": {"name": "Storm Wisp", "hp": 8, "row": "back", "speed": 6, "xp": 4, "gold": 3,
                   "dice": [_d(6)],
                   "moves": {"arc": {"name": "Arc", "k": "attack", "n": 1, "chain": True, "st": "shock", "sn": 1, "st_min": 5},
                             "static_charge": {"name": "Static Charge", "k": "debuff", "n": 1, "st": "static", "sn": 1},
                             "merge": {"name": "Merge", "k": "merge", "w": 2}}},
    "lightning_totem": {"name": "Lightning Totem", "hp": 14, "row": "back", "speed": 1, "xp": 5, "gold": 4, "volatile": 5,
                        "dice": [_d(4, "grow")],
                        "seq": ["charge", "charge", "discharge"],
                        "moves": {"charge": {"name": "Gathering Charge", "k": "charge"},
                                  "discharge": {"name": "Discharge", "k": "all", "n": 1}}},
    "thunder_wyvern": {"name": "Thunder Wyvern", "hp": 22, "row": "back", "speed": 5, "beast": True, "elite": True,
                       "xp": 10, "gold": 10,
                       "dice": [_d(8), _d(8)],
                       "moves": {"breath": {"name": "Storm Breath", "k": "all", "use": [0], "st": "shock", "sn": 1, "st_min": 7, "w": 0},
                                 "inhale": {"name": "Draw Breath", "k": "charge", "next": "breath"},
                                 "rend": {"name": "Rend", "k": "attack", "n": 2, "pair": {"again": True}, "w": 2}}},
    "lamp_keeper": {"name": "The Lamp Keeper", "hp": 75, "row": "back", "speed": 3, "boss": True,
                    "xp": 40, "gold": 35,
                    "dice": [SEARING, _d(8), _d(6)],
                    "seq": ["sweep", "gather", "flash", "focus", "storm"],
                    "moves": {"sweep": {"name": "Sweeping Beam", "k": "all", "use": [0]},
                              # put the lamp out while it gathers and the beam scatters (`foe_hit_hooks`)
                              "gather": {"name": "Gather the Light", "k": "charge", "next": "beam"},
                              "beam": {"name": "Lighthouse Beam", "k": "all", "use": [0, 1, 2]},
                              "flash": {"name": "Blinding Flash", "k": "all", "use": [2], "st": "mark", "sn": 1},
                              "focus": {"name": "Focused Beam", "k": "attack", "use": [0, 1, 2], "tgt": "strongest"},
                              "storm": {"name": "Call the Storm", "k": "summon", "f": "storm_wisp"}},
                    "bloodied": {"might": 2, "rule": "blaze", "text": "the lamp blazes: put out, it relights the next round.",
                                 "moves": {"searing": {"name": "Searing Sweep", "k": "all", "use": [0], "st": "burn", "sn": 2}}}},

    # ---------------------------------------------------------------- big single threats (champion halls, late roamers)
    "reef_maw": {"name": "The Reef Maw", "hp": 46, "row": "front", "speed": 2, "beast": True, "elite": True, "big": True,
                 "xp": 16, "gold": 14, "thorns": 1,
                 "dice": [_d(8), _d(8), SHELL],
                 "moves": {"engulf": {"name": "Engulf", "k": "attack", "use": [0, 1], "tgt": "strongest", "st": "root", "sn": 1, "w": 2},
                           "undertow": {"name": "Undertow", "k": "all", "use": [0], "st": "weak", "sn": 1, "st_min": 6},
                           "clamp": {"name": "Clamp Shut", "k": "block", "use": [1, 2]}},
                 "pool": {"polyps": {"name": "Spawn Polyps", "k": "summon", "f": "jelly"},
                          "spray": {"name": "Brine Spray", "k": "attack", "use": [0, 1], "each": True}},
                 "bloodied": {"might": 2, "rule": "swallow", "text": "it swallows a hero whole. Hit it hard to make it spit them out.",
                              "moves": {"thrash": {"name": "Thrash", "k": "attack", "use": [0, 1, 2], "each": True}}}},
    "iron_bosun": {"name": "The Iron Bosun", "hp": 44, "row": "front", "speed": 3, "elite": True, "big": True, "xp": 16, "gold": 18,
                   "dice": [_d(10, "steady"), _d(6, "exploding"), _d(6)],
                   "moves": {"anchor": {"name": "Anchor Swing", "k": "attack", "use": [0], "sweep": 2, "w": 2},
                             "grapple": {"name": "Grapple", "k": "attack", "use": [1], "tgt": "weakest", "st": "root", "sn": 1},
                             "grog": {"name": "Swig of Grog", "k": "heal", "use": [2], "self": True}},
                   "pool": {"whistle": {"name": "Bosun's Whistle", "k": "summon", "f": "deckhound"},
                            "chainlash": {"name": "Chain Lash", "k": "attack", "use": [0, 2], "chain": True}},
                   "bloodied": {"might": 2, "rule": "allhands", "text": "he roars for the crew: a Deckhound joins every round.",
                                "moves": {"keelhaul": {"name": "Keelhaul", "k": "attack", "use": [0, 1, 2], "tgt": "vengeful",
                                                       "st": "stun", "sn": 1, "st_min": 8}}}},
    "storm_roc": {"name": "The Storm Roc", "hp": 40, "row": "back", "speed": 6, "beast": True, "elite": True, "big": True,
                  "xp": 16, "gold": 14,
                  "dice": [_d(8), _d(8), _d(6)],
                  "moves": {"dive": {"name": "Dive", "k": "attack", "use": [0, 1], "tgt": "weakest", "pair": {"again": True}, "w": 2},
                            "gale": {"name": "Gale", "k": "all", "use": [2], "st": "stun", "sn": 1, "st_min": 6},
                            "talons": {"name": "Talons", "k": "attack", "use": [0, 1, 2], "each": True}},
                  "pool": {"flock": {"name": "Call the Flock", "k": "summon", "f": "harpy"},
                           "feathers": {"name": "Lightning Feathers", "k": "attack", "use": [0], "chain": True, "st": "shock", "sn": 1}},
                  "bloodied": {"might": 2, "rule": "air", "text": "it takes to the air: only ranged attacks and spells can reach it.",
                               "moves": {"thunderclap": {"name": "Thunderclap", "k": "all", "use": [0, 1]}}}},

    # the Gallows Admiral's, bloodied: it blows up on the party after two fuses, or on his crew if a hero breaks it
    "powder_keg": {"name": "Powder Keg", "hp": 12, "row": "back", "speed": 1, "xp": 2, "gold": 0, "object": True, "keg": True,
                   "dice": [_d(8), _d(8)],
                   "seq": ["fuse", "fuse", "blow"],
                   "moves": {"fuse": {"name": "Fizzing Fuse", "k": "charge"},
                             "blow": {"name": "Blows Up!", "k": "all", "use": [0, 1]}}},
    "cannon": {"name": "Deck Cannon", "hp": 14, "row": "back", "speed": 2, "xp": 3, "gold": 0, "object": True,
               "dice": [_d(6), _d(6)],
               "seq": ["load", "load", "fire"],
               "moves": {"load": {"name": "Load the Cannon", "k": "charge"},
                         "fire": {"name": "Broadside!", "k": "all", "use": [0]}}},

    # ---------------------------------------------------------------- the peak
    "tide_guard": {"name": "Tide Guard", "hp": 16, "row": "front", "speed": 3, "undead": True, "xp": 6, "gold": 0,
                   "dice": [_d(6), SHELL],
                   "moves": {"halberd": {"name": "Halberd", "k": "attack", "use": [0], "w": 2},
                             "brace": {"name": "Shield the Crown", "k": "guard", "n": 2}}},
    "drowned_crown": {"name": "The Drowned Crown", "hp": 120, "row": "back", "speed": 4, "boss": True, "final": True,
                      "xp": 0, "gold": 0, "leech": True,
                      "dice": [FROST, _d(10), _d(8), _d(6)],
                      "seq": ["wave", "depths", "rise", "surge", "curse"],
                      "moves": {"wave": {"name": "Tidal Wave", "k": "all", "use": [3]},
                                "depths": {"name": "Crushing Depths", "k": "attack", "use": [1, 2, 3], "tgt": "vengeful"},
                                "rise": {"name": "Rise, Guard", "k": "summon", "f": "tide_guard"},
                                "surge": {"name": "Freezing Surge", "k": "attack", "use": [0], "sweep": 2},
                                "curse": {"name": "Drowned Curse", "k": "debuff", "use": [3], "st": "hex", "sn": 1, "tgt": "weakest"},
                                # never in `seq`: the round after each change of phase (`Bosses.boss_phase`)
                                "deluge": {"name": "The Deluge", "k": "all", "use": [0, 1, 2, 3]}}},
}

# Move pools: every enemy draws one of these when it appears, on top of its own moves.
POOLS = {
    "deckhand": {"drag_under": {"name": "Drag Under", "k": "attack", "n": 1, "st": "root", "sn": 1},
                 "rot_breath": {"name": "Rotten Breath", "k": "debuff", "n": 1, "st": "weak", "sn": 1, "st_min": 3}},
    "crab": {"crush_claw": {"name": "Crushing Claw", "k": "attack", "n": 2, "st": "vuln", "sn": 1, "st_min": 5},
             "shell_wall": {"name": "Shell Wall", "k": "guard", "n": 2, "all": True}},
    "jelly": {"bloom": {"name": "Bloom", "k": "summon", "f": "jelly"},
              "numb": {"name": "Numbing Touch", "k": "attack", "n": 1, "st": "stun", "sn": 1, "st_min": 4}},
    "eel": {"coil": {"name": "Coil", "k": "charge"},
            "lurk": {"name": "Lurk in the Reef", "k": "block", "n": 2}},
    "barnacle_priest": {"barnacle_ward": {"name": "Barnacle Ward", "k": "guard", "use": [0], "all": True},
                        "sermon": {"name": "Drowned Sermon", "k": "buff", "v": 1}},
    "siren": {"charm": {"name": "Charm", "k": "debuff", "n": 1, "st": "vuln", "sn": 2},
              "wail": {"name": "Wail", "k": "all", "n": 1, "st": "weak", "sn": 1, "st_min": 6}},
    "bell_warden": {"dirge": {"name": "Funeral Dirge", "k": "debuff", "use": [2], "st": "hex", "sn": 1, "tgt": "strongest"},
                    "barnacled": {"name": "Barnacled Bronze", "k": "block", "use": [0, 1]}},
    "cutthroat": {"throat": {"name": "Go for the Throat", "k": "attack", "n": 1, "tgt": "weakest"},
                  "sand": {"name": "Sand in the Eyes", "k": "debuff", "n": 1, "st": "weak", "sn": 1}},
    "deckhound": {"howl": {"name": "Howl", "k": "buff", "v": 1},
                  "lunge": {"name": "Lunge", "k": "attack", "n": 2, "tgt": "weakest", "pair": {"st": "vuln", "sn": 1}}},
    "brine_golem": {"salt_wave": {"name": "Salt Wave", "k": "all", "use": [0]},
                    "bulwark": {"name": "Brine Bulwark", "k": "guard", "n": 2, "all": True}},
    "powder_monkey": {"long_fuse": {"name": "Long Fuse", "k": "charge"},
                      "pitch": {"name": "Pitch Pot", "k": "attack", "n": 1, "st": "burn", "sn": 2}},
    "tide_cultist": {"call_deep": {"name": "Call the Deep", "k": "summon", "f": "deckhand"},
                     "drown": {"name": "Drowning Prayer", "k": "debuff", "use": [1], "st": "stun", "sn": 1, "st_min": 4}},
    "corsair_captain": {"parley": {"name": "Dirty Parley", "k": "debuff", "use": [1], "st": "vuln", "sn": 2},
                        "boarding": {"name": "Boarding Hook", "k": "attack", "use": [0, 1], "st": "root", "sn": 1}},
    "gallows_admiral": {"grog": {"name": "Grog Ration", "k": "heal", "use": [0, 3], "self": True},
                        "keelhaul": {"name": "Keelhaul", "k": "attack", "use": [0, 2], "tgt": "weakest", "st": "root", "sn": 1}},
    "crag_ram": {"stampede": {"name": "Stampede", "k": "attack", "n": 2, "sweep": 2},
                 "headbutt": {"name": "Headbutt", "k": "attack", "n": 1, "st": "stun", "sn": 1, "st_min": 6}},
    "cliff_hermit": {"rockslide": {"name": "Rockslide", "k": "all", "use": [1]},
                     "hermit_curse": {"name": "Hermit's Curse", "k": "debuff", "use": [0], "st": "hex", "sn": 1, "st_min": 4}},
    "harpy": {"screech": {"name": "Screech", "k": "debuff", "n": 1, "st": "weak", "sn": 1, "st_min": 3},
              "snatch": {"name": "Snatch", "k": "attack", "use": [1], "tgt": "weakest", "st": "vuln", "sn": 1}},
    "storm_wisp": {"flicker": {"name": "Flicker", "k": "block", "n": 1},
                   "static": {"name": "Static Field", "k": "all", "n": 1, "st": "shock", "sn": 1, "st_min": 6}},
    "lightning_totem": {"overload": {"name": "Overload", "k": "attack", "n": 1, "chain": True},
                        "grounding": {"name": "Grounding Field", "k": "guard", "n": 1, "all": True}},
    "thunder_wyvern": {"thunder_dive": {"name": "Thunder Dive", "k": "attack", "use": [0, 1], "tgt": "weakest"},
                       "roost": {"name": "Roost", "k": "heal", "use": [1], "self": True}},
    "lamp_keeper": {"glare": {"name": "Lens Glare", "k": "debuff", "use": [2], "st": "weak", "sn": 2, "tgt": "strongest"},
                    "refract": {"name": "Refracted Beam", "k": "attack", "use": [0, 1], "sweep": 2}},
    "tide_guard": {"phalanx": {"name": "Phalanx", "k": "guard", "n": 2, "all": True},
                   "hook": {"name": "Halberd Hook", "k": "attack", "use": [0], "st": "root", "sn": 1}},
    "drowned_crown": {"maelstrom": {"name": "Maelstrom", "k": "all", "use": [2], "st": "weak", "sn": 1, "st_min": 6},
                      "undertow": {"name": "Undertow", "k": "attack", "use": [1, 3], "tgt": "strongest", "st": "stun", "sn": 1, "st_min": 8}},
}
for _k, _v in POOLS.items():
    FOES[_k]["pool"] = _v

# Fights last longer than in the first pass: every enemy but the bosses has this much more health
# than its listed hp.
FOE_HP = 1.45
# ...and the bosses (the three objectives' and the Drowned Crown) this much more than theirs.
BOSS_HP = 1.0
for _v in FOES.values():
    _v["hp"] = round(_v["hp"] * (BOSS_HP if _v.get("boss") else FOE_HP))


# Who roams each region, by how many objectives the party has cleared (more cleared, more
# dangerous mixes). Each entry is a group.
GROUPS = {
    "coral": [["deckhand"], ["crab"], ["jelly", "jelly"], ["deckhand", "eel"], ["crab", "barnacle_priest"],
              ["deckhand", "deckhand", "siren"], ["crab", "jelly", "eel"], ["deckhand", "crab", "barnacle_priest"]],
    "keys": [["cutthroat"], ["deckhound", "deckhound"], ["cutthroat", "powder_monkey"], ["brine_golem"],
             ["cutthroat", "tide_cultist"], ["deckhound", "cutthroat", "powder_monkey"],
             ["brine_golem", "tide_cultist"], ["cutthroat", "cutthroat", "corsair_captain"]],
    "storm": [["crag_ram"], ["harpy"], ["cliff_hermit", "storm_wisp"], ["crag_ram", "harpy"],
              ["lightning_totem", "cliff_hermit"], ["harpy", "harpy", "storm_wisp"],
              ["crag_ram", "cliff_hermit", "lightning_totem"], ["crag_ram", "thunder_wyvern"]],
}
GROUPS["peak"] = [["deckhand", "cutthroat"], ["crag_ram", "eel"], ["brine_golem", "harpy"], ["tide_guard"],
                  ["tide_guard", "siren"], ["tide_guard", "storm_wisp", "tide_cultist"]]

LAIRS = {
    "coral": [["crab", "crab", "siren"], ["deckhand", "deckhand", "barnacle_priest", "eel"]],
    "keys": [["brine_golem", "powder_monkey", "tide_cultist"], ["cutthroat", "cutthroat", "corsair_captain"]],
    "storm": [["crag_ram", "cliff_hermit", "thunder_wyvern"], ["lightning_totem", "harpy", "harpy", "storm_wisp"]],
}

# Each objective is three fights: an opening fight (drawn from `open`), a fork between two paths
# (`PATHS`; a passage from `mid`, a champion from `champ`, a vault, or a shrine with no fight), then
# a second fork for how to take on the boss (its escort drawn from `escort`). A lineup entry is an
# enemy key, or {"k": key, "aff": affix} for an elite.
DUNGEONS = {
    "coral": {"name": "The Sunken Chapel", "boss": "bell_warden",
              "open": [["deckhand", "deckhand", "eel"], ["crab", "jelly", "jelly"], ["deckhand", "barnacle_priest", "eel"]],
              "mid": [["crab", "jelly", "barnacle_priest", "siren"], ["deckhand", "deckhand", "siren", "eel"],
                      ["crab", "crab", "barnacle_priest"]],
              "champ": [["reef_maw"], [{"k": "crab", "aff": "hulking"}, "jelly"],
                        [{"k": "siren", "aff": "warlord"}, "deckhand", "deckhand"]],
              "escort": [["deckhand", "barnacle_priest"], ["deckhand", "eel"], ["barnacle_priest", "siren"]]},
    "keys": {"name": "The Black Fort", "boss": "gallows_admiral",
             "open": [["cutthroat", "deckhound", "powder_monkey"], ["deckhound", "deckhound", "cutthroat"],
                      ["cutthroat", "tide_cultist", "powder_monkey"]],
             "mid": [["brine_golem", "cutthroat", "tide_cultist", "powder_monkey"],
                     ["cutthroat", "cutthroat", "powder_monkey", "deckhound"], ["brine_golem", "tide_cultist", "tide_cultist"]],
             "champ": [["iron_bosun"], [{"k": "corsair_captain", "aff": "frenzied"}, "deckhound"],
                       [{"k": "brine_golem", "aff": "ironclad"}, "powder_monkey"]],
             "escort": [["cutthroat", "cutthroat"], ["cutthroat", "powder_monkey"], ["deckhound", "tide_cultist"]]},
    "storm": {"name": "The Lighthouse", "boss": "lamp_keeper",
              "open": [["crag_ram", "harpy", "storm_wisp"], ["harpy", "harpy", "cliff_hermit"], ["crag_ram", "storm_wisp", "storm_wisp"]],
              "mid": [["cliff_hermit", "crag_ram", "lightning_totem", "harpy"], ["harpy", "harpy", "storm_wisp", "lightning_totem"],
                      ["crag_ram", "crag_ram", "cliff_hermit"]],
              "champ": [["storm_roc"], [{"k": "thunder_wyvern", "aff": "vampiric"}, "storm_wisp"],
                        [{"k": "crag_ram", "aff": "hulking"}, "cliff_hermit"]],
              "escort": [["cliff_hermit", "storm_wisp"], ["harpy", "storm_wisp"], ["cliff_hermit", "lightning_totem"]]},
}
DUNGEON_STEPS = 3

# The paths a fork can offer. `step` is the fight they lead to (1: the middle, 2: the boss).
PATHS = {
    "open": {"name": "The Way In", "step": 0, "text": "The first room.", "reward": "Loot: two to choose from."},
    "passage": {"name": "The Main Passage", "step": 1, "text": "More of the same, by the main way.",
                "reward": "Loot: two to choose from."},
    "champion": {"name": "The Champion's Hall", "step": 1, "text": "One big threat holds this hall.",
                 "reward": "Better loot: a rarity up, three to choose from."},
    "vault": {"name": "The Flooded Vault", "step": 1, "text": "A guarded treasure room. One guard is an elite.",
              "reward": "+12 gold each, and loot."},
    "shrine": {"name": "A Quiet Shrine", "step": 1, "text": "No fight: rest a moment by the old altar.",
               "reward": "Everyone heals 35% and shakes off curses. No loot."},
    "gate": {"name": "Storm the Hall", "step": 2, "text": "Straight at the boss and its escort.",
             "reward": "The boss's hoard: three to choose from."},
    "rest": {"name": "Rest at the Threshold", "step": 2, "text": "Catch your breath first. The escort grows while you wait.",
             "reward": "Heal 30% first, but one more enemy. Three to choose from."},
    "sneak": {"name": "The Back Way", "step": 2, "text": "Slip in behind them: they're caught off guard for a round.",
              "reward": "An ambush, but the hoard is half buried: two to choose from."},
}
MID_PATHS = ["passage", "champion", "vault", "shrine"]
BOSS_PATHS = ["gate", "rest", "sneak"]

# Elite affixes: more health, a twist, and double the XP and gold.
ELITES = {
    "hulking": {"name": "Hulking", "hp": 2.0, "text": "Twice the health. Its attacks roll an extra die."},
    "frenzied": {"name": "Frenzied", "hp": 1.6, "text": "Every die it rolls explodes on its top face."},
    "ironclad": {"name": "Ironclad", "hp": 1.6, "text": "Gains 4 Armor at the start of every round."},
    "venomous": {"name": "Venomous", "hp": 1.6, "text": "Its hits Poison 2."},
    "warlord": {"name": "Warlord", "hp": 1.6, "text": "Every round from the second, the other enemies gain +1 might."},
    "vampiric": {"name": "Vampiric", "hp": 1.6, "text": "Heals half the damage it deals."},
    "spiteful": {"name": "Spiteful", "hp": 1.6, "text": "Gains +1 might whenever a hero buffs, heals or shields."},
    "splitting": {"name": "Splitting", "hp": 1.6, "text": "Hit by two different heroes in one round, it splits in two (once)."},
}
BIG = {"coral": "reef_maw", "keys": "iron_bosun", "storm": "storm_roc"}
ROAM_ELITES = ["hulking", "frenzied", "ironclad", "venomous", "vampiric", "spiteful", "splitting"]

FINAL = ["tide_guard", "tide_guard", "drowned_crown"]

REGION_NAMES = {"coral": "Coral Shallows", "keys": "Smugglers' Keys", "storm": "Stormcrag", "peak": "the Peak"}

# Shrine blessings and event curses: (name, what it does, turns it lasts, mods)
BUFFS = {
    "swift": {"name": "Fair Winds", "text": "+1 move.", "turns": 6, "mods": {"move": 1}},
    "might": {"name": "Sea Strength", "text": "+1 damage on every hit.", "turns": 6, "mods": {"might": 1}},
    "warded": {"name": "Barnacle Skin", "text": "Start fights with 4 Armor.", "turns": 6, "mods": {"start_armor": 4}},
    "vigor": {"name": "Salt Vigor", "text": "+6 max HP.", "turns": 8, "mods": {"max_hp": 6}},
    "soggy": {"name": "Soggy Boots", "text": "−1 move.", "turns": 4, "mods": {"move": -1}, "curse": True},
    "jinx": {"name": "Jinxed", "text": "No reroll in fights.", "turns": 4, "mods": {"reroll": -1}, "curse": True},
    "frail": {"name": "Seasick", "text": "−4 max HP.", "turns": 6, "mods": {"max_hp": -4}, "curse": True},
    # a dark shrine's: stronger than a shrine's, and never free
    "dark_might": {"name": "Drowned Strength", "text": "+2 damage on every hit.", "turns": 8, "mods": {"might": 2}},
    "dark_ward": {"name": "Black Coral Skin", "text": "Start fights with 8 Armor.", "turns": 8, "mods": {"start_armor": 8}},
}
SHRINE_BUFFS = ["swift", "might", "warded", "vigor"]

# ---------------------------------------------------------------- the overworld's choices
# What a place shows before anyone gets there, places that ask a price, towns with a trade of their
# own, chances that last a few turns, and dungeons whose garrisons grow while they wait.

WRECK_RARITY = [("common", 3), ("uncommon", 2)]  # an unguarded wreck's loot, shown on the map
GUARDED_WRECKS = 3  # wrecks with enemies camped on them: beat them for a pool of rare loot
DARK_SHRINES = 2    # shrines that offer a stronger blessing at a price (the `dark_shrine` event)
WRECK_GUARDS = {reg: GROUPS[reg][2:6] for reg in ("coral", "keys", "storm")}

TOWN_SPECS = {
    "smith": {"name": "Smithy", "text": "Reforges a piece of your gear into a random one a rarity better, for the same slot."},
    "temple": {"name": "Temple", "text": "Lifts curses for free, and sells the party one revive."},
    "cartographer": {"name": "Cartographer", "text": "Sells charts that show a whole region: its places, lairs and wrecks."},
    "fence": {"name": "Fence", "text": "Pays half again as much for what you sell."},
}
REFORGE_COST = {"uncommon": 30, "rare": 60, "legendary": 100}
TEMPLE_REVIVE = 75
CHART_COST = 15
FENCE_BONUS = 20  # percentage points on the sell rate (40% -> 60%, 60% -> 80% with Haggler)

# Opportunities: they turn up every few turns somewhere a few turns' walk away and last `turns` turns
# (counting the one they appear on), so reaching one is a choice about the next few turns.
OPPS = {
    "ship": {"name": "Merchant ship", "turns": 4, "text": "Docked in town with three better-than-usual wares, then it sails."},
    "drift": {"name": "Drifting cargo", "turns": 3, "text": "Washed up on the shore: loot and gold for whoever gets there first."},
    "healer": {"name": "Wandering healer", "turns": 4, "text": "Camped here: heals each hero who arrives to full and lifts curses."},
}
OPP_EVERY = 5   # a new one every this many turns (from turn 3)...
OPP_MAX = 2     # ...while fewer than this many are about
OPP_RANGE = {"ship": (4, 14), "drift": (4, 10), "healer": (3, 12)}  # how far from the nearest hero

# Garrisons: every `GARRISON_EVERY` turns each objective not yet cleared grows. The first two growths
# add an escort to its boss fight; past that its boss gets `GARRISON_BOSS` more health per growth.
# An objective cleared before its garrison ever grew weakens the Drowned Crown by `CROWN_CUT`.
GARRISON_EVERY = 6
GARRISON_MAX = 6
GARRISON_ESCORTS = 2
GARRISON_BOSS = 0.15
CROWN_CUT = 0.1

# What the sea brings when the tide rises (`Game.tide_arrivals`): one arrival a rise, two from rise
# `TIDE_TWO_FROM`. Each has a weight before and after `TIDE_LATE` (early rises bring mostly gifts,
# later ones mostly threats) and the first rise it can come on. Arrivals land `range` hexes from the
# nearest hero and are shown on the map at once; enemies that land stay in sight for `TIDE_SIGHTED`
# turns. They never flood land or touch a town.
TIDE_ARRIVALS = {
    "wreckage": {"name": "Wreckage washes ashore", "from": 1, "w": (3, 1), "range": (3, 9),
                 "text": "A wreck on the beach: loot for whoever gets there."},
    "boon": {"name": "The tide brings visitors", "from": 1, "w": (2, 1), "range": None,
             "text": "A merchant ship, drifting cargo or a wandering healer turns up."},
    "landing": {"name": "Raiders come ashore", "from": 2, "w": (2, 3), "range": (4, 8),
                "text": "A band of enemies lands on the beach, close by."},
    "warband": {"name": "A war-band lands", "from": 4, "w": (1, 3), "range": (5, 10),
                "text": "Led by an elite and carrying a rare prize for whoever beats them."},
    "leviathan": {"name": "Something huge is beached", "from": 7, "w": (0, 2), "range": (5, 12),
                  "text": "A big threat lies on the shore and won't move. It guards a rare prize."},
}
TIDE_TWO_FROM = 6
TIDE_LATE = 6
TIDE_SIGHTED = 3
TIDE_STAY = 6    # turns an unfought landing stays before it goes back to sea (a beached big threat twice that)
TIDE_WRECKS = 3  # unlooted wrecks the tide has left that can be about at once
TIDE_GROUPS = 3  # enemy groups the tide has landed that can be on the map at once (apart from MAX_GROUPS)
TIDE_WRECK_RARITY = ([("common", 2), ("uncommon", 3)], [("uncommon", 3), ("rare", 1)])  # early, late

# Event chains: the follow-ups some events set up (`chain` in an outcome).
LOAN_DUE = 8      # turns until the moneylender comes to collect
CASTAWAY_AFTER = 5  # turns before the castaway you helped reaches a town (the next town you enter after)
CACHE_RANGE = (5, 12)

# Events. A choice may need a class (`need`), cost gold (`cost`) or roll a die (`check`): a number
# (your best die must roll at least that), or {die: weapon, armor, trinket (a bare d4 if that slot is
# empty), best, or party (the best die of anyone on your hex: bring friends), n: the target, vs: an
# opponent's die to beat instead, great: a roll that earns the `great` outcome}. Outcomes: text,
# gold (can be negative), hp, xp, item (a rarity), potion, buff (curses too; a list for several),
# revive, skiff, fight (enemy keys), all (healing and buffs reach everyone on your hex too), chain (a
# follow-up: "cache" marks a buried cache on the map, "loan" sends the moneylender after you
# `LOAN_DUE` turns later, "castaway" has the castaway reward you in a town later). A `hidden` event is
# never placed on the map: it's a follow-up or a place's own (the dark shrine).
EVENTS = [
    {"key": "bottle", "title": "A Bottle, Corked", "text": "A bottle bobs against the rocks with a rolled-up note inside. "
     "It has clearly been waiting for someone exactly like you, or at least anyone at all.",
     "choices": [
         {"label": "Read the note", "ok": {"text": "It's a treasure map. The treasure, it turns out, is taped to the back of the map.", "gold": 10}},
         {"label": "Smash it for the glass", "check": {"die": "trinket", "n": 3},
          "ok": {"text": "Glass everywhere, and in the middle of it, a trinket.", "item": "common"},
          "bad": {"text": "Glass everywhere, mostly in you.", "hp": -3}},
         {"label": "Write a reply and send it back", "need": "herald", "ok": {"text": "You compose a moving reply. Somewhere, someone is moved. You feel wiser.", "xp": 12}},
     ]},
    {"key": "smuggler", "title": "The Honest Smuggler", "text": "A man in a very large coat assures you that everything inside it is "
     "\"genuine, practically legal\" and \"only slightly damp\".",
     "choices": [
         {"label": "Buy something", "cost": 15, "ok": {"text": "It's genuinely good. He seems as surprised as you are.", "item": "uncommon"}},
         {"label": "Politely decline", "ok": {"text": "He tips a hat that you're fairly sure is also for sale."}},
         {"label": "Haggle him down to nothing", "need": "herald", "ok": {"text": "Somehow he pays you to take it.", "item": "uncommon", "gold": 5}},
     ]},
    {"key": "tidepool", "title": "Tide Pool", "text": "A clear pool among the rocks. Something glints at the bottom. Something else, "
     "with claws, is very interested in whether you'll reach for it.",
     "choices": [
         {"label": "Reach in and grab it", "check": {"die": "trinket", "n": 3, "great": 4},
          "great": {"text": "You snatch it out before the claws even twitch. It's better than it looked.", "item": "uncommon"},
          "ok": {"text": "You snatch it out before the claws close.", "item": "common"},
          "bad": {"text": "The crab disagrees, firmly, with your fingers.", "hp": -4}},
         {"label": "Shoo the crab off first", "check": {"die": "weapon", "n": 4},
          "ok": {"text": "It retreats, offended. The glint is yours.", "item": "common"},
          "bad": {"text": "It does not shoo. You leave, nursing a pinch.", "hp": -2}},
         {"label": "Leave it", "ok": {"text": "The crab looks disappointed. You'll get over it."}},
     ]},
    {"key": "cook", "title": "Shipwrecked Cook", "text": "A cook sits beside the wreck of his galley, stirring a pot of something he "
     "insists is chowder.",
     "choices": [
         {"label": "Have a bowl (bring friends)", "ok": {"text": "It's... fine. It's warm and it's fine. There's plenty.", "hp": 8, "all": True}},
         {"label": "Ask for the recipe", "ok": {"text": "The recipe is mostly a list of things that were nearby. You learn a lot.", "xp": 8}},
         {"label": "Check the pot first", "need": "mender", "ok": {"text": "You pick out the worrying bits. The result is genuinely restorative, and he gives you a flask for the road.", "hp": 15, "potion": 1, "all": True}},
     ]},
    {"key": "gulls", "title": "The Gull Parliament", "text": "Forty gulls stand in a solemn ring on the beach. One of them appears to "
     "be speaking. The motion before the house is, as always, chips.",
     "choices": [
         {"label": "Bow and back away", "ok": {"text": "The house notes your respect. A tailwind follows you.", "buff": "swift"}},
         {"label": "Address the house", "check": {"die": "best", "n": 5},
          "ok": {"text": "Your speech carries the vote. They pay you in shiny things.", "gold": 12},
          "bad": {"text": "The house rises as one. You are pecked, extensively.", "hp": -5}},
         {"label": "Translate the debate", "need": "arcanist", "ok": {"text": "Gull grammar is fascinating and also horrifying.", "xp": 15}},
     ]},
    {"key": "drowned_shrine", "title": "Half-Drowned Shrine", "text": "An old shrine to a sea god, knee-deep in water. Offerings still "
     "glitter in the bowl. Whoever prays here prays for everyone beside them.",
     "choices": [
         {"label": "Pray together", "check": {"die": "party", "n": 4},
          "ok": {"text": "Something old and wet approves of you all.", "buff": "warded", "all": True},
          "bad": {"text": "Something old and wet does not approve of you.", "buff": "soggy"}},
         {"label": "Take the offerings", "ok": {"text": "Fifteen gold richer. You feel watched.", "gold": 15, "buff": "jinx"}},
         {"label": "Clean the shrine", "need": "mender", "ok": {"text": "You scrub the barnacles off. The water warms around everyone's ankles.", "hp": 12, "all": True}},
         {"label": "Leave", "ok": {"text": "Probably wise."}},
     ]},
    {"key": "big_crab", "title": "A Very Large Crab", "text": "It is a crab. It is the size of a cart. It is blocking the path, and it is "
     "looking at you the way you look at a buffet.",
     "choices": [
         {"label": "Fight it", "ok": {"text": "It snaps its claws. Here we go.", "fight": ["crab", "crab"]}},
         {"label": "Sneak past", "check": {"die": "trinket", "n": 3},
          "ok": {"text": "You tiptoe past. It never knew.", "xp": 6},
          "bad": {"text": "It knew.", "fight": ["crab", "crab"]}},
         {"label": "Toss it a fish", "cost": 5, "ok": {"text": "It accepts the fish with surprising dignity and steps aside."}},
         {"label": "Stare it down", "need": "vanguard", "ok": {"text": "A long moment. The crab blinks first and scuttles off.", "xp": 12}},
     ]},
    {"key": "barrel_seer", "title": "Fortune Teller in a Barrel", "text": "A woman lives in a barrel. She says she can see the future. "
     "She says the future is mostly barrel.",
     "choices": [
         {"label": "Pay for a fortune", "cost": 5, "ok": {"text": "\"You will hit things harder.\" You do feel it.", "buff": "might"}},
         {"label": "Ask about the rising sea", "ok": {"text": "\"It rises,\" she says, and closes the lid.", "xp": 5}},
         {"label": "Compliment the barrel", "need": "herald", "ok": {"text": "Nobody ever compliments the barrel. Your fortune is free, and long.", "buff": "might", "xp": 6}},
     ]},
    {"key": "diary", "title": "A Keeper's Diary", "text": "A waterlogged diary in a hut. Most of it is about weather. The last page is "
     "about something under the water, wearing a crown.",
     "choices": [
         {"label": "Read it all", "ok": {"text": "You know a little more about what you're up against.", "xp": 12}},
         {"label": "Use it to start a fire", "ok": {"text": "A warm night. Everyone here sleeps well.", "hp": 10, "all": True}},
     ]},
    {"key": "crate", "title": "Floating Crate", "text": "A crate drifts just past the end of a broken jetty, stencilled FRAGILE and, "
     "below that, in smaller letters, VALUABLE.",
     "choices": [
         {"label": "Wade out and haul it in", "check": {"die": "armor", "n": 3},
          "ok": {"text": "You haul it in. Not that fragile, very valuable.", "item": "uncommon"},
          "bad": {"text": "The current takes your legs. The crate drifts away, looking smug.", "hp": -4}},
         {"label": "Pick the lock while it floats", "need": "scoundrel", "ok": {"text": "Easy.", "item": "rare"}},
         {"label": "Let it go", "ok": {"text": "Someone else's problem."}},
     ]},
    {"key": "herbs", "title": "A Hermit's Garden", "text": "A tidy garden on a rock, tended by nobody you can see. Labels on little "
     "sticks say things like \"for wounds\" and \"NOT for wounds\".",
     "choices": [
         {"label": "Take some \"for wounds\"", "ok": {"text": "You brew a tonic on the spot.", "potion": 1}},
         {"label": "Take some \"NOT for wounds\"", "ok": {"text": "That was a mistake, but an educational one.", "hp": -3, "xp": 10}},
         {"label": "Harvest it properly", "need": "mender", "ok": {"text": "Enough for the whole party, and then some.", "potion": 2, "hp": 6, "all": True}},
     ]},
    {"key": "revenant", "title": "Revenant at the Rail", "text": "A drowned sailor stands at the rail of a beached ship, staring out to "
     "sea, still waiting to be relieved of watch.",
     "choices": [
         {"label": "Relieve them of watch", "check": {"die": "best", "n": 5},
          "ok": {"text": "They salute, and sink into peace. Something of their stubbornness stays with you.", "revive": 1},
          "bad": {"text": "They do not recognise your authority.", "fight": ["deckhand", "deckhand"]}},
         {"label": "Lay them to rest", "need": "mender", "ok": {"text": "A gentle word. They go, and leave you their luck.", "revive": 1}},
         {"label": "Leave them to it", "ok": {"text": "Someone has to keep watch."}},
     ]},
    {"key": "wizard", "title": "The Seasick Wizard", "text": "A wizard is being sick over the side of a rowboat, which is beached. He "
     "says it's the principle of the thing.",
     "choices": [
         {"label": "Hold his hat", "ok": {"text": "He tips you for your trouble.", "gold": 8}},
         {"label": "Trade spells", "need": "arcanist", "ok": {"text": "Between heaves, he teaches you something genuinely useful.", "xp": 20}},
         {"label": "Ask for a lift", "ok": {"text": "He points at the sand. Fair.", "buff": "soggy"}},
     ]},
    {"key": "mutineers", "title": "The Mutineers", "text": "A dozen sailors are arguing about whose turn it was to have mutinied. "
     "Their captain is tied to a palm tree, offering a reward to anyone who'll untie him.",
     "choices": [
         {"label": "Untie the captain", "ok": {"text": "The sailors object, physically.", "fight": ["cutthroat", "cutthroat"]}},
         {"label": "Side with the crew", "ok": {"text": "They give you a cut of the captain's purse.", "gold": 14}},
         {"label": "Duel the ringleader for him", "check": {"die": "weapon", "vs": 8},
          "ok": {"text": "You win, the crew cheers whoever won, and the captain pays handsomely.", "gold": 22},
          "bad": {"text": "You lose, and the crew cheers anyway. They love a show.", "hp": -6}},
         {"label": "Settle it by vote", "need": "herald", "ok": {"text": "Democracy prevails. Everybody pays you for chairing.", "gold": 20}},
     ]},
    {"key": "liars_dice", "title": "Liar's Dice", "text": "A grinning sailor rattles a cup of dice on an upturned barrel. \"Ten gold says "
     "I roll higher. Twenty-five if you're brave.\" His dice look honest. His grin does not.",
     "choices": [
         {"label": "Take the bet", "cost": 10, "check": {"die": "best", "vs": 6},
          "ok": {"text": "Your die comes up higher. He pays, and asks for a rematch you wisely decline.", "gold": 25},
          "bad": {"text": "He wins. Of course he wins."}},
         {"label": "Raise to twenty-five", "cost": 25, "check": {"die": "best", "vs": 8},
          "ok": {"text": "A hush, a rattle, and the pot is yours.", "gold": 65},
          "bad": {"text": "He sweeps up the coins with a sympathetic wince."}},
         {"label": "Swap in your own dice", "need": "scoundrel", "ok": {"text": "He never notices. Or he's too polite to say.", "gold": 25}},
         {"label": "Walk away", "ok": {"text": "The only winning move, probably."}},
     ]},
    {"key": "tide_bell", "title": "The Tide Bell", "text": "A bronze bell hangs from a post in the shallows, green with age. The water "
     "around it is very still, as if it's waiting.",
     "choices": [
         {"label": "Ring it", "check": {"die": "party", "n": 4},
          "ok": {"text": "The note carries for miles. The wind turns to follow you, and everyone beside you.", "buff": "swift", "all": True},
          "bad": {"text": "The note carries for miles. Something answers it.", "fight": ["eel", "jelly"]}},
         {"label": "Ring it in tune", "need": "herald", "ok": {"text": "A perfect note. The sea itself seems to cheer you on.", "buff": "might", "all": True}},
         {"label": "Muffle it with your cloak and move on", "ok": {"text": "Whatever it was waiting for, it can keep waiting.", "xp": 6}},
     ]},
    {"key": "stuck_skiff", "title": "The Stranded Skiff", "text": "An abandoned skiff is wedged on a sandbar, oars and all. It would take "
     "a strong back, or several, to shift it.",
     "choices": [
         {"label": "Heave it free (anyone on your hex helps)", "check": {"die": "party", "n": 5},
          "ok": {"text": "It scrapes, groans and floats. It's yours now.", "skiff": True},
          "bad": {"text": "It doesn't budge. Your back has opinions about this.", "hp": -3}},
         {"label": "Lift it like a crate", "need": "vanguard", "ok": {"text": "You simply pick it up and put it in the water. Nobody says anything.", "skiff": True}},
         {"label": "Strip it for parts", "ok": {"text": "Some rope, a lantern, a few coins in the bilge.", "gold": 6}},
     ]},
    {"key": "riddle", "title": "The Mermaid's Riddle", "text": "A mermaid lounges on a rock, combing seaweed out of her hair. \"Answer me "
     "this: what rises without legs, and swallows without a mouth?\"",
     "choices": [
         {"label": "Guess", "check": {"die": "best", "n": 4},
          "ok": {"text": "\"The sea,\" you say. She looks annoyed, then tosses you a pearl-crusted bauble.", "item": "uncommon"},
          "bad": {"text": "Wrong. She laughs, and the laugh follows you for days.", "buff": "frail"}},
         {"label": "Answer like a scholar", "need": "arcanist", "ok": {"text": "You give the answer, three alternatives, and a footnote. She gives you her best trinket to make you stop.", "item": "rare"}},
         {"label": "Ask for a hint", "cost": 5, "ok": {"text": "The hint is long, and educational, and you never get round to answering.", "xp": 10}},
     ]},
    {"key": "cache", "title": "Under the Dock", "text": "Loose boards under a dock, and the smell of gunpowder and money. Someone has "
     "hidden something here, and they won't be happy to find it gone.",
     "choices": [
         {"label": "Pry the boards up", "check": {"die": "weapon", "n": 4},
          "ok": {"text": "A purse, fat and unattended.", "gold": 22},
          "bad": {"text": "The boards creak. Its owners come running.", "fight": ["cutthroat", "cutthroat"]}},
         {"label": "Find the hidden latch", "need": "scoundrel", "ok": {"text": "There's always a latch.", "gold": 30}},
         {"label": "Take only the gunpowder", "need": "alchemist", "ok": {"text": "Into the bag it goes, to become something useful later.", "potion": 2, "gold": 6}},
         {"label": "Leave it", "ok": {"text": "Not your gunpowder, not your problem."}},
     ]},
    {"key": "hawk", "title": "The Hurt Hawk", "text": "A hawk with a damaged wing hops along the beach, glaring at you as though "
     "this is all your fault.",
     "choices": [
         {"label": "Offer it food", "check": {"die": "trinket", "n": 3},
          "ok": {"text": "It eats, considers you, and drops something shiny at your feet.", "item": "common"},
          "bad": {"text": "It takes the food and a bit of your thumb.", "hp": -2}},
         {"label": "Splint the wing", "need": "ranger", "ok": {"text": "It lets you. When it flies off it circles twice, and you feel sharper for it.", "buff": "might", "xp": 10}},
         {"label": "Speak to it", "need": "warden", "ok": {"text": "It tells you which way the wind will blow. It's right.", "buff": "swift", "all": True}},
         {"label": "Leave it be", "ok": {"text": "It glares at you until you're out of sight."}},
     ]},
    {"key": "duel", "title": "En Garde!", "text": "A fencer in a ridiculous hat blocks the path. \"First blood buys dinner, and I am "
     "very hungry.\"",
     "choices": [
         {"label": "Accept", "check": {"die": "weapon", "vs": 8},
          "ok": {"text": "A touch! The fencer bows, pays for dinner, and wanders off still hungry.", "gold": 12, "xp": 8},
          "bad": {"text": "A touch, on you. Dinner is on you too.", "hp": -6, "gold": -6}},
         {"label": "Accept, with a flourish", "need": "duelist", "ok": {"text": "It's over in three moves. The hat is yours, and the respect.", "xp": 18, "gold": 10}},
         {"label": "Just buy them dinner", "cost": 8, "ok": {"text": "Dinner is excellent, and the company better than expected.", "hp": 10, "all": True}},
     ]},
    {"key": "choir", "title": "The Drowned Choir", "text": "Voices rise from under the waves, singing your name, a little off-key and "
     "getting closer.",
     "choices": [
         {"label": "Stand and listen", "check": {"die": "armor", "n": 3},
          "ok": {"text": "You hold your ground. The song fades, and leaves you wiser.", "xp": 12},
          "bad": {"text": "You wake up knee-deep in the surf with no idea how you got there.", "buff": "jinx"}},
         {"label": "Sing back, louder", "need": "herald", "ok": {"text": "They harmonise. It's beautiful. Everyone feels better.", "hp": 10, "all": True}},
         {"label": "Block your ears and hurry on", "ok": {"text": "The song follows you a while, then gives up."}},
     ]},
    {"key": "powder", "title": "The Ticking Barrel", "text": "Three barrels of powder sit under a tarp. One of them is ticking. "
     "Barrels shouldn't tick.",
     "choices": [
         {"label": "Light the others and run", "check": {"die": "trinket", "n": 3, "great": 4},
          "great": {"text": "The blast tears open a smugglers' cache, and you weren't even singed.", "item": "rare"},
          "ok": {"text": "The blast tears open a smugglers' cache.", "item": "uncommon"},
          "bad": {"text": "You don't run fast enough.", "hp": -6}},
         {"label": "Defuse and decant", "need": "alchemist", "ok": {"text": "Delicate work. It yields useful mixtures and some loose change.", "potion": 2, "gold": 8}},
         {"label": "Back away slowly", "ok": {"text": "It's still ticking when you lose sight of it."}},
     ]},
    {"key": "cairn", "title": "The Cairn of Skulls", "text": "A neat cairn of skulls, recently tidied. A painted sign reads TAKE ONE, "
     "LEAVE ONE.",
     "choices": [
         {"label": "Take one", "check": {"die": "best", "n": 4},
          "ok": {"text": "There's a ring still on its finger bone. Why a skull has a finger bone is not your concern.", "item": "common"},
          "bad": {"text": "Its owner wanted it back.", "buff": "jinx"}},
         {"label": "Add one from your collection", "need": "berserker", "ok": {"text": "The cairn accepts your offering. You feel monstrously strong.", "buff": "might", "all": True}},
         {"label": "Leave flowers instead", "need": "warden", "ok": {"text": "Something approves. You feel hale.", "buff": "vigor", "all": True}},
         {"label": "Leave both alone", "ok": {"text": "The sign seems disappointed."}},
     ]},
    # the start of a chain each
    {"key": "torn_chart", "title": "A Torn Chart", "text": "Half a sea chart, pinned under a stone. One X, a lot of "
     "underlining, and the word MINE written three times.",
     "choices": [
         {"label": "Follow it", "ok": {"text": "You match the coastline to the chart. The X is real, and not far. "
                                               "It's marked on your map.", "chain": "cache"}},
         {"label": "Sell it to the next fool", "ok": {"text": "A passing fisherman pays good money for it. He seems delighted.", "gold": 12}},
     ]},
    {"key": "moneylender", "title": "The Moneylender", "text": "A woman with a ledger and two very large associates offers "
     "a loan. \"Forty now. Sixty when I find you again. And I always find you.\"",
     "choices": [
         {"label": "Take the forty", "ok": {"text": "She counts it out and writes your name in the ledger. Twice, for some reason.",
                                            "gold": 40, "chain": "loan"}},
         {"label": "No thank you", "ok": {"text": "\"Suit yourself.\" The associates look disappointed."}},
     ]},
    {"key": "castaway", "title": "The Castaway", "text": "A sunburnt man on a spit of sand, waving a shirt. He's been here "
     "a while: he has named the crabs.",
     "choices": [
         {"label": "Share your water and point him to town", "ok": {"text": "He drinks, cries a little and sets off. "
                                                                            "\"I won't forget this!\" People say that.",
                                                                    "hp": -3, "chain": "castaway"}},
         {"label": "Wish him luck", "ok": {"text": "He waves the shirt after you, less hopefully."}},
     ]},
    # never placed on the map
    {"key": "collector", "hidden": True, "title": "The Debt Comes Due", "text": "The moneylender steps out from behind a rock, "
     "ledger open. \"Sixty, as agreed.\" Her associates crack their knuckles in unison.",
     "choices": [
         {"label": "Pay the sixty", "cost": 60, "ok": {"text": "She crosses your name out. Only once, which feels ominous."}},
         {"label": "Talk her down to thirty", "need": "herald", "cost": 30, "ok": {"text": "Somehow she leaves thanking you."}},
         {"label": "Refuse", "ok": {"text": "\"Then we'll take it out of you.\"", "fight": ["cutthroat", "cutthroat", "deckhound"]}},
     ]},
    {"key": "dark_shrine", "hidden": True, "title": "A Dark Shrine", "text": "Black coral grown into the shape of an altar, "
     "wet though the sun is out. It offers strength. It would like something back.",
     "choices": [
         {"label": "Drink from the black pool", "ok": {"text": "Power floods your arms. Your stomach disagrees with the arrangement.",
                                                        "buff": ["dark_might", "frail"]}},
         {"label": "Bleed on the altar", "ok": {"text": "The coral drinks. Your skin hardens like a reef.", "hp": -8, "buff": ["dark_ward"]}},
         {"label": "Leave it be", "ok": {"text": "Some offers are best refused. Probably."}},
     ]},
]


def event_risk(ev):
    """What the map says about an event before anyone steps on it: "fight" if a choice can start
    one, "risky" if a roll can go badly, else "safe"."""
    outs = [o for ch in ev["choices"] for o in (ch.get("ok"), ch.get("bad"), ch.get("great")) if o]
    if any(o.get("fight") for o in outs):
        return "fight"
    if any(ch.get("bad") for ch in ev["choices"]):
        return "risky"
    return "safe"

QUEST_REWARD = 25  # the gold every hero got for a job before rewards scaled (old saves' jobs keep it)

# Jobs on town notice boards: each board offers two (`JOBS_PER_BOARD`), one can be taken. Every job has a
# deadline from how far it is (a hero covers about `JOB_PACE` hexes a turn) plus `JOB_SLACK` turns, and
# pays every hero `JOB_GOLD` + `JOB_PER_HEX` per hex of the trip + the kind's bonus, and one more thing
# for whoever finishes it (`JOB_REWARDS`).
JOBS_PER_BOARD = 2
JOB_PACE = 3
JOB_SLACK = {"deliver": 3, "lair": 5, "bounty": 6, "salvage": 4}
JOB_GOLD = 8
JOB_PER_HEX = 2
JOB_BONUS = {"deliver": 0, "lair": 10, "bounty": 15, "salvage": 8}
JOB_KINDS = {
    "deliver": {"name": "Delivery", "text": "Carry a parcel to another town."},
    "lair": {"name": "Clear a lair", "text": "Clear out the lair that's been troubling the town."},
    "bounty": {"name": "Bounty", "text": "Hunt down a wanted crew. They run from you, a hex a turn, and stay on the map wherever they go."},
    "salvage": {"name": "Salvage", "text": "Fetch the cargo from a wreck and bring it back here. Whoever picks it up must carry it home."},
}
# what else a job pays, with weights; "trade" (a free go at the town's smithy, chart or temple revive)
# only from a town with one; the rest of the gold is cut a little when the extra is worth more
JOB_REWARDS = {"loot": 4, "item": 2, "revive": 1, "trade": 2, "restock": 1}
JOB_GOLD_CUT = {"loot": 1.0, "item": 0.5, "revive": 0.5, "trade": 0.7, "restock": 0.7}
BOUNTY_NAMES = ["Red Mag's crew", "One-Eyed Pell's lot", "the Brine Sisters", "Captain Gristle's gang", "Old Scuttle's mob",
                "the Gull-Eaters", "Salt Annie's band", "the Barnacle Brothers", "Mother Kelp's brood", "the Rusted Hooks"]
BOUNTY_RANGE = (5, 10)  # hexes from the town where the wanted crew is first seen
