"""Six status-focused enemies (owner's request, Nov 2026: more enemies that inflict statuses), one for
each of six regions, each bringing statuses its region's enemies lacked. Sprites in
`tools/saltbound-art/foes4.py` (the owner picked one of three looks for each).

Merged into `archipelago.py`'s tables after its status pass (`STATUS_UP`), so these numbers are final;
`GROUPS` here are added to each region's roaming groups, and `CRITS` to `foes.py`'s critical riders.
"""


def _d(n, *dk):
    return {"faces": list(range(1, n + 1)), "dk": list(dk)}


def _f(faces, *dk):
    return {"faces": list(faces), "dk": list(dk)}


EMBER = _f([1, 2, "F3", 4, "F5", 6])
RIME = _f([1, 2, "I3", 4, "I5", 6])

FOES = {
    # Smugglers' Keys: Poison and Root
    "bilge_rats": {"name": "Bilge Rats", "hp": 10, "row": "front", "speed": 6, "beast": True, "xp": 4, "gold": 2,
                   "dice": [_d(4), _d(4)],
                   "moves": {"gnaw": {"name": "Gnaw", "k": "attack", "n": 2, "each": True, "st": "poison", "sn": 1, "w": 2},
                             "swarm_over": {"name": "Swarm Over", "k": "attack", "n": 2, "pair": {"st": "root", "sn": 1}}}},
    # Stormcrag: Hex, a stolen die, Vulnerable
    "omen_raven": {"name": "Omen Raven", "hp": 9, "row": "back", "speed": 6, "beast": True, "xp": 5, "gold": 4,
                   "dice": [_d(6, "seer"), _d(4)],
                   "moves": {"ill_omen": {"name": "Ill Omen", "k": "debuff", "use": [0], "st": "hex", "sn": 1, "st_min": 3},
                             "shiny_grab": {"name": "Shiny Grab", "k": "attack", "use": [1], "st": "steal", "sn": 1, "tgt": "strongest"},
                             "rend": {"name": "Rend", "k": "attack", "use": [0, 1], "pair": {"st": "vuln", "sn": 1}, "w": 2}}},
    # Cinderreach: Poison on everyone, Root
    "sulphur_toad": {"name": "Sulphur Toad", "hp": 16, "row": "front", "speed": 2, "beast": True, "xp": 5, "gold": 3,
                     "dice": [_d(6), EMBER],
                     "moves": {"toxic_belch": {"name": "Toxic Belch", "k": "all", "use": [0], "st": "poison", "sn": 2},
                               "tongue_lash": {"name": "Tongue Lash", "k": "attack", "use": [1], "st": "root", "sn": 1, "w": 2},
                               "body_slam": {"name": "Body Slam", "k": "attack", "use": [0, 1], "w": 2}}},
    # the Frostpeaks: Root and Mark
    "rime_trapper": {"name": "Rimebound Trapper", "hp": 12, "row": "back", "speed": 5, "xp": 5, "gold": 4,
                     "dice": [RIME, _d(6)],
                     "moves": {"snare": {"name": "Snare", "k": "attack", "use": [1], "st": "root", "sn": 1},
                               "hunters_mark": {"name": "Hunter's Mark", "k": "debuff", "use": [1], "st": "mark", "sn": 1, "st_min": 3},
                               "frost_arrow": {"name": "Frost Arrow", "k": "attack", "use": [0], "w": 2}}},
    # the Verdant Deep: Weak on everyone, a crusted die
    "glowcap": {"name": "Glowcap", "hp": 12, "row": "front", "speed": 3, "xp": 5, "gold": 3, "splits": True,
                "dice": [_d(6), _d(4)],
                "moves": {"spore_cloud": {"name": "Spore Cloud", "k": "all", "use": [0], "st": "weak", "sn": 1, "st_min": 4},
                          "choking_spores": {"name": "Choking Spores", "k": "debuff", "use": [0], "st": "lock", "sn": 1, "tgt": "strongest"},
                          "cap_slam": {"name": "Cap Slam", "k": "attack", "use": [0, 1], "w": 2}}},
    # the Prism Wood: Static on your dice, Shock
    "arc_beetle": {"name": "Arc Beetle", "hp": 18, "row": "front", "speed": 3, "beast": True, "xp": 6, "gold": 4,
                   "dice": [_d(6), _d(6)],
                   "moves": {"static_field": {"name": "Static Field", "k": "debuff", "n": 1, "st": "static", "sn": 1, "tgt": "strongest"},
                             "arc_bite": {"name": "Arc Bite", "k": "attack", "n": 2, "st": "shock", "sn": 1, "w": 2},
                             "shell_up": {"name": "Shell Up", "k": "block", "n": 2}}},
}

# What a critical hit (an attack die on its top face) adds (`foes.py`'s FOE_CRIT).
CRITS = {"bilge_rats": ("poison", 2), "omen_raven": ("hex", 1), "sulphur_toad": ("burn", 2),
         "rime_trapper": ("freeze", 1), "glowcap": ("weak", 1), "arc_beetle": ("shock", 1)}

# Roaming groups added to each region's list: the newcomer alone, with a local, and in a bigger group.
GROUPS = {
    "keys": [["bilge_rats", "bilge_rats"], ["bilge_rats", "cutthroat"], ["bilge_rats", "rum_runner", "parrot"]],
    "storm": [["omen_raven"], ["omen_raven", "crag_ram"], ["omen_raven", "harpy", "rockling"]],
    "ash": [["sulphur_toad"], ["sulphur_toad", "cinder_imp"], ["sulphur_toad", "lava_hound", "ember_cultist"]],
    "frost": [["rime_trapper", "frost_wolf"], ["rime_trapper", "frozen_revenant"], ["rime_trapper", "frost_wolf", "ice_wraith"]],
    "jungle": [["glowcap"], ["glowcap", "dart_frog"], ["glowcap", "silverback", "strangler_vine"]],
    "crystal": [["arc_beetle"], ["arc_beetle", "shardling"], ["arc_beetle", "resonant_wisp", "prism_spider"]],
}
