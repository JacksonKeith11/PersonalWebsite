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
    "jelly": {"name": "Jellyfloat", "hp": 8, "row": "front", "speed": 4, "beast": True, "xp": 3, "gold": 2, "leech": True,
              "dice": [TOXIC],
              "moves": {"sting": {"name": "Sting", "k": "attack", "n": 1}}},
    "eel": {"name": "Reef Eel", "hp": 9, "row": "back", "speed": 6, "beast": True, "xp": 4, "gold": 3,
            "dice": [_d(4), _d(4)],
            "moves": {"bite": {"name": "Snapping Bites", "k": "attack", "n": 2, "each": True, "pair": {"st": "shock", "sn": 1}, "w": 2},
                      "jolt": {"name": "Jolt", "k": "attack", "n": 2, "st": "shock", "sn": 1}}},
    "barnacle_priest": {"name": "Barnacle Priest", "hp": 10, "row": "back", "speed": 2, "undead": True, "xp": 5, "gold": 5,
                        "dice": [_d(6), _d(4)],
                        "moves": {"mend": {"name": "Mend Flesh", "k": "heal", "n": 2, "w": 2},
                                  "spit": {"name": "Brine Spit", "k": "attack", "use": [1], "st": "weak", "sn": 1}}},
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
                              "crush": {"name": "Bell Drop", "k": "attack", "use": [0, 1, 2], "tgt": "vengeful"}}},

    # ---------------------------------------------------------------- Smugglers' Keys
    "cutthroat": {"name": "Cutthroat", "hp": 11, "row": "front", "speed": 7, "xp": 4, "gold": 5,
                  "dice": [_d(6, "exploding")],
                  "moves": {"shiv": {"name": "Shiv", "k": "attack", "n": 1, "st": "vuln", "sn": 1, "w": 2},
                            "low_blow": {"name": "Low Blow", "k": "attack", "n": 1, "st": "weak", "sn": 1, "tgt": "vengeful"}}},
    "deckhound": {"name": "Deckhound", "hp": 9, "row": "front", "speed": 8, "beast": True, "xp": 3, "gold": 1, "pack": 2,
                  "dice": [_d(4), _d(4)],
                  "moves": {"savage": {"name": "Savage", "k": "attack", "n": 2, "each": True, "tgt": "weakest"}}},
    "brine_golem": {"name": "Brine Golem", "hp": 24, "row": "front", "speed": 1, "xp": 7, "gold": 3,
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
                        "seq": ["broadside", "boarders", "volley", "noose"],
                        "moves": {"broadside": {"name": "Broadside", "k": "all", "use": [0]},
                                  "boarders": {"name": "Boarders, Away!", "k": "summon", "f": "cutthroat"},
                                  "volley": {"name": "Pistol Volley", "k": "attack", "use": [0, 1, 2], "each": True},
                                  "noose": {"name": "Hang 'em High", "k": "attack", "use": [1, 3], "st": "root", "sn": 1, "tgt": "strongest"}}},

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
              "moves": {"talons": {"name": "Raking Talons", "k": "attack", "n": 2, "each": True}}},
    "storm_wisp": {"name": "Storm Wisp", "hp": 8, "row": "back", "speed": 6, "xp": 4, "gold": 3,
                   "dice": [_d(6)],
                   "moves": {"arc": {"name": "Arc", "k": "attack", "n": 1, "chain": True, "st": "shock", "sn": 1, "st_min": 5}}},
    "lightning_totem": {"name": "Lightning Totem", "hp": 14, "row": "back", "speed": 1, "xp": 5, "gold": 4, "volatile": 5,
                        "dice": [_d(4, "grow")],
                        "seq": ["charge", "charge", "discharge"],
                        "moves": {"charge": {"name": "Gathering Charge", "k": "charge"},
                                  "discharge": {"name": "Discharge", "k": "all", "n": 1}}},
    "thunder_wyvern": {"name": "Thunder Wyvern", "hp": 22, "row": "back", "speed": 5, "beast": True, "elite": True,
                       "xp": 10, "gold": 10,
                       "dice": [_d(8), _d(8)],
                       "moves": {"breath": {"name": "Storm Breath", "k": "all", "use": [0], "st": "shock", "sn": 1, "st_min": 7},
                                 "rend": {"name": "Rend", "k": "attack", "n": 2, "pair": {"again": True}, "w": 2}}},
    "lamp_keeper": {"name": "The Lamp Keeper", "hp": 75, "row": "back", "speed": 3, "boss": True,
                    "xp": 40, "gold": 35,
                    "dice": [SEARING, _d(8), _d(6)],
                    "seq": ["sweep", "flash", "focus", "storm"],
                    "moves": {"sweep": {"name": "Sweeping Beam", "k": "all", "use": [0]},
                              "flash": {"name": "Blinding Flash", "k": "all", "use": [2], "st": "mark", "sn": 1},
                              "focus": {"name": "Focused Beam", "k": "attack", "use": [0, 1, 2], "tgt": "strongest"},
                              "storm": {"name": "Call the Storm", "k": "summon", "f": "storm_wisp"}}},

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
                                "curse": {"name": "Drowned Curse", "k": "debuff", "use": [3], "st": "hex", "sn": 1, "tgt": "weakest"}}},
}

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

DUNGEONS = {
    "coral": {"name": "The Sunken Chapel", "fights": [["deckhand", "deckhand", "eel"], ["crab", "jelly", "barnacle_priest", "siren"],
                                                   ["deckhand", "bell_warden", "barnacle_priest"]]},
    "keys": {"name": "The Black Fort", "fights": [["cutthroat", "deckhound", "powder_monkey"],
                                               ["brine_golem", "cutthroat", "tide_cultist", "powder_monkey"],
                                               ["cutthroat", "cutthroat", "gallows_admiral"]]},
    "storm": {"name": "The Lighthouse", "fights": [["crag_ram", "harpy", "storm_wisp"],
                                                ["cliff_hermit", "crag_ram", "lightning_totem", "harpy"],
                                                ["cliff_hermit", "lamp_keeper", "storm_wisp"]]},
}
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
}
SHRINE_BUFFS = ["swift", "might", "warded", "vigor"]

# Events. A choice may need a class (`need`), cost gold (`cost`) or roll a die (`check`): a number
# (your best die must roll at least that), or {die: weapon, armor, trinket (a bare d4 if that slot is
# empty), best, or party (the best die of anyone on your hex: bring friends), n: the target, vs: an
# opponent's die to beat instead, great: a roll that earns the `great` outcome}. Outcomes: text,
# gold (can be negative), hp, xp, item (a rarity), potion, buff (curses too), revive, skiff, fight
# (enemy keys), all (healing and buffs reach everyone on your hex too).
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
]

QUEST_REWARD = 25
