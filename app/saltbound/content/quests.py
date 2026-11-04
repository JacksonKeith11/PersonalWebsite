"""The other regions' quests and more of their events (merged into archipelago: QUESTS, BUFFS, EVENTS).

A region's quest starts at its quest-giver (a `quest` place, one in each drawn region) and runs as a
trail of events (`Game` in quests.py): the giver's event, then a site somewhere in the region, then a
last site that ends it. A choice moves the quest on with `"quest": "start"` or `"quest": "next"`; a
choice that starts a fight carries `"win"`, an outcome played only if the party wins (and that's where
a fight's `"quest": "next"` goes, so losing leaves the site where it was, to come back to). Turning a
step down leaves it waiting too.

Outcome keys these events add (Game.outcome): `give` (one particular item, offered as a pick), `mat`
(a material into the bag: a key, or "random" for one of the enchant materials) and boons: buffs with
`perm` that never run out (`BOONS`, a region's mastery: some bend its map rule for whoever has it).
"""

# Boons: permanent blessings. `sandwalk`, `junglewalk` and `frostborn` are map rules (biome.py, rules.js).
BOONS = {
    "emberheart": {"name": "Emberheart", "text": "You can't be Burned, and your Burns are 1 stronger.",
                   "mods": {"burn_immune": 1, "burn_bonus": 1}},
    "sandstrider": {"name": "Sandstrider", "text": "Quicksand doesn't slow you. +2 max HP.", "mods": {"sandwalk": 1, "max_hp": 2}},
    "stoneblood": {"name": "Stoneblood", "text": "Start each fight with 3 Armor. +3 max HP.", "mods": {"start_armor": 3, "max_hp": 3}},
    "jungle_born": {"name": "Jungle-Born", "text": "Deep jungle costs you only 1 move a hex, and you heal 1 each round in fights.",
                    "mods": {"junglewalk": 1, "regen": 1}},
    "haloed": {"name": "Haloed", "text": "Your heals are 1 stronger. +4 max HP.", "mods": {"heal_bonus": 1, "max_hp": 4}},
    "clear_eyed": {"name": "Clear-Eyed", "text": "+1 automatic reroll per fight.", "mods": {"reroll": 1}},
    "lucid_dreamer": {"name": "Lucid Dreamer", "text": "Ignore the first Stun each fight, and +1 to every event roll.",
                      "mods": {"stun_ward": 1, "silver_voice": 1}},
    "frostborn": {"name": "Frostborn", "text": "No Frostbite, your dice can't be Frozen, and the frozen sea costs you 1 a hex.",
                  "mods": {"frostborn": 1, "freeze_immune": 1}},
}
BUFFS = {k: dict(v, turns=1, perm=True) for k, v in BOONS.items()}

# Each region's quest: who gives it, the events it runs through (the first is the giver's), and what
# the quest log says to do at each step after the first.
QUESTS = {
    "ash": {"name": "The Phoenix's Ashes", "giver": "The Keeper of Ashes", "steps": ["q_ash_1", "q_ash_2", "q_ash_3"],
            "goals": ["gather the phoenix's embers from the cooling pyre", "climb to the phoenix's nest"],
            "reward": "the Phoenix Plume, or the Emberheart boon"},
    "dunes": {"name": "The Sun-King's Tomb", "giver": "The Last Vizier", "steps": ["q_dunes_1", "q_dunes_2", "q_dunes_3"],
              "goals": ["find the sealed door under the dunes", "open the Sun-King's treasury"],
              "reward": "the Sun-King's Khopesh, or the Sandstrider boon"},
    "petrified": {"name": "The Heart of the Wood", "giver": "The Last Dryad", "steps": ["q_petrified_1", "q_petrified_2", "q_petrified_3"],
                  "goals": ["wake the stone grove", "find the heart of the Stillwood"],
                  "reward": "the Heart of the Stillwood, or the Stoneblood boon"},
    "jungle": {"name": "The Serpent's Fang", "giver": "The Snake-Charmer", "steps": ["q_jungle_1", "q_jungle_2", "q_jungle_3"],
               "goals": ["find the jade serpent's shed skin", "face the serpent in its temple"],
               "reward": "the Fang of the Jade Serpent, or the Jungle-Born boon"},
    "heaven": {"name": "The Fallen Wings", "giver": "The Wingless Angel", "steps": ["q_heaven_1", "q_heaven_2", "q_heaven_3"],
               "goals": ["find the feathers where she fell", "bring them before the Tribunal"],
               "reward": "the Wings of the Arbiter, or the Haloed boon"},
    "crystal": {"name": "The Heartprism", "giver": "The Blind Gemcutter", "steps": ["q_crystal_1", "q_crystal_2", "q_crystal_3"],
                "goals": ["tune the singing stones", "cut the Heartprism free"],
                "reward": "the Heartprism, or the Clear-Eyed boon"},
    "dream": {"name": "The Lantern of Sleep", "giver": "The Insomniac", "steps": ["q_dream_1", "q_dream_2", "q_dream_3"],
              "goals": ["find the Somnarch's lost lantern", "light it at the edge of waking"],
              "reward": "the Somnarch's Lantern, or the Lucid Dreamer boon"},
    "frost": {"name": "The Heart of Winter", "giver": "The Frozen Bard", "steps": ["q_frost_1", "q_frost_2", "q_frost_3"],
              "goals": ["follow the frozen song up the mountain", "claim winter's heart from its keeper"],
              "reward": "the Rimeheart, or the Frostborn boon"},
}
QUEST_OF = {ev: key for key, q in QUESTS.items() for ev in q["steps"]}

_ACCEPT = "It's marked on your map."

EVENTS = [
    # ================================================================ quests (never placed as events)
    # ---------------------------------------------------------------- Cinderreach: the Phoenix's Ashes
    {"key": "q_ash_1", "quest": "ash", "hidden": True, "title": "The Keeper of Ashes", "text": "An old man sits by a cold brazier in the "
     "middle of the ash fields, sifting cinders through his fingers. \"The phoenix died in the last eruption,\" he says. \"Her embers are "
     "scattered, and a wyrm sleeps on her pyre. Gather them, and she'll rise again. Or take what she leaves.\"",
     "choices": [
         {"label": "Take up his task", "ok": {"text": "He points with a blackened finger to where the pyre still smokes. " + _ACCEPT, "quest": "start", "xp": 6}},
         {"label": "Not now", "ok": {"text": "\"She's waited this long,\" he says, and goes back to his sifting."}},
     ]},
    {"key": "q_ash_2", "quest": "ash", "hidden": True, "title": "The Cooling Pyre", "text": "A ring of black glass where a great fire burned. "
     "Here and there an ember still glows, too hot to touch, and cinder imps are squabbling over them like gulls.",
     "choices": [
         {"label": "Drive off the imps", "ok": {"text": "They scatter, shrieking, and come back with friends.",
                                                "fight": ["cinder_imp", "cinder_imp", "ash_wraith"],
                                                "win": {"text": "The embers are yours. They pulse in their jar like a heartbeat. The nest is higher up.", "quest": "next", "gold": 10}}},
         {"label": "Snatch the embers", "check": {"die": "best", "n": 6},
          "ok": {"text": "Quick hands, singed sleeves, and every ember in the jar. The nest is higher up.", "quest": "next"},
          "bad": {"text": "Too slow. The imps scatter with half of them, and your fingers blister.", "hp": -5}},
         {"label": "Come back later", "ok": {"text": "The embers will keep. Embers are good at that."}},
     ]},
    {"key": "q_ash_3", "quest": "ash", "hidden": True, "title": "The Phoenix's Nest", "text": "On a ledge of the volcano, a nest of melted "
     "gold and bone. In it, wrapped round the phoenix's last feather, a caldera wyrm sleeps, its belly glowing. The embers in your jar "
     "begin to sing.",
     "choices": [
         {"label": "Kill the wyrm and take the feather", "ok": {"text": "It wakes as your shadow falls on it.",
                                                                "fight": ["caldera_wyrm", "lava_hound"],
                                                                "win": {"text": "The wyrm falls into the crater. The feather is warm, and alive, and yours.",
                                                                        "give": "phoenix_plume", "quest": "next", "xp": 20}}},
         {"label": "Pour the embers into the nest", "check": {"die": "party", "n": 6},
          "ok": {"text": "The wyrm flees the light. The phoenix rises in a column of fire, and her heat stays in you.",
                 "buff": "emberheart", "mat": "wyrm_ember", "quest": "next", "xp": 20},
          "bad": {"text": "The embers sputter. The wyrm stirs. You back away with the jar, slowly.", "hp": -6}},
         {"label": "Not yet", "ok": {"text": "The wyrm sleeps on. So, for now, does the phoenix."}},
     ]},
    # ---------------------------------------------------------------- the Shifting Sands: the Sun-King's Tomb
    {"key": "q_dunes_1", "quest": "dunes", "hidden": True, "title": "The Last Vizier", "text": "A man in moth-eaten silks keeps a tent "
     "beside a half-buried obelisk. He served the Sun-King, he says, three thousand years ago, and he would very much like to stop. "
     "\"Open the treasury. Take his sword. Let us both rest.\"",
     "choices": [
         {"label": "Swear to open it", "ok": {"text": "He draws the way in the sand with a dry finger. " + _ACCEPT, "quest": "start", "xp": 6}},
         {"label": "Ask how he's lasted so long", "ok": {"text": "\"Spite,\" he says. \"And dates.\" He gives you a handful. They are very good.", "hp": 8}},
     ]},
    {"key": "q_dunes_2", "quest": "dunes", "hidden": True, "title": "The Sealed Door", "text": "The wind has cleared the top of a door, carved "
     "with suns. Sand pours from the cracks like water. Something on the other side is scratching to get out.",
     "choices": [
         {"label": "Break the seal", "ok": {"text": "The door groans open, and the dead pour out with the sand.",
                                            "fight": ["wrapped_dead", "wrapped_dead", "scarab_swarm"],
                                            "win": {"text": "Beyond the door, stairs go down into the dark: the treasury is below.", "quest": "next", "gold": 12}}},
         {"label": "Read the carvings", "need": "arcanist", "ok": {"text": "A password, in the old tongue. The door opens politely.", "quest": "next", "xp": 8}},
         {"label": "Leave it sealed for now", "ok": {"text": "The scratching follows you for a while."}},
     ]},
    {"key": "q_dunes_3", "quest": "dunes", "hidden": True, "title": "The Treasury of the Sun", "text": "A hall of gold under the dunes, "
     "lit by shafts of sun through cracks in the ceiling. On a throne of sand sits the Sun-King's sword, and coiled round the throne, "
     "a sandworm the size of a ship.",
     "choices": [
         {"label": "Fight for the sword", "ok": {"text": "The worm rises, and the hall shakes.",
                                                 "fight": ["great_sandworm", "dune_scorpion"],
                                                 "win": {"text": "The worm sinks into the sand for good. The sword comes away from the throne with a sigh.",
                                                         "give": "sunking_khopesh", "quest": "next", "xp": 20}}},
         {"label": "Walk the worm's path", "check": {"die": "trinket", "n": 5},
          "ok": {"text": "You step only where it has stepped. You take nothing but its secret: how to walk on sand like water.",
                 "buff": "sandstrider", "mat": "starmetal", "quest": "next", "xp": 20},
          "bad": {"text": "A wrong step. The worm turns its head. You leave, quickly.", "hp": -6}},
         {"label": "Come back stronger", "ok": {"text": "The sword will wait. It has had practice."}},
     ]},
    # ---------------------------------------------------------------- the Stillwood: the Heart of the Wood
    {"key": "q_petrified_1", "quest": "petrified", "hidden": True, "title": "The Last Dryad", "text": "In a hollow of a stone oak, a dryad, "
     "grey to the waist and turning greyer. \"The wood's heart stopped,\" she whispers, \"and the trees stopped with it. Wake the grove. "
     "Find the heart. Before I'm stone too.\"",
     "choices": [
         {"label": "Promise to find it", "ok": {"text": "She presses a seed into your hand: it tugs, gently, the way you need to go. " + _ACCEPT,
                                                "quest": "start", "xp": 6}},
         {"label": "Not now", "ok": {"text": "\"Don't take long,\" she says. Her voice is already harder."}},
     ]},
    {"key": "q_petrified_2", "quest": "petrified", "hidden": True, "title": "The Stone Grove", "text": "A ring of stone trees round a dry "
     "spring. The seed in your hand is warm. The statues among the trees are watching it. Some of them are not statues.",
     "choices": [
         {"label": "Plant the seed in the spring", "check": {"die": "party", "n": 5},
          "ok": {"text": "Water wells up. The trees creak and sigh, and a path opens toward the wood's heart.", "quest": "next", "hp": 8, "all": True},
          "bad": {"text": "The guardians stir.", "fight": ["petrified_knight", "gargoyle"]}},
         {"label": "Clear the guardians first", "ok": {"text": "They step down off their plinths.",
                                                       "fight": ["petrified_knight", "gargoyle", "basilisk"],
                                                       "win": {"text": "With the grove cleared, the seed takes root. A path opens.", "quest": "next", "xp": 10}}},
         {"label": "Come back later", "ok": {"text": "The grove can wait. It's good at waiting."}},
     ]},
    {"key": "q_petrified_3", "quest": "petrified", "hidden": True, "title": "The Heart of the Stillwood", "text": "At the centre of the wood, "
     "a heart of living amber the size of a barrel, beating once a minute. Coiled round it, an elder basilisk, ancient and very awake.",
     "choices": [
         {"label": "Fight the basilisk for the heart", "ok": {"text": "Its eyes open, and the air thickens.",
                                                              "fight": ["elder_basilisk", "stone_treant"],
                                                              "win": {"text": "The basilisk crumbles. The heart beats faster in your hands: it'll guard you now.",
                                                                      "give": "stillwood_heart", "quest": "next", "xp": 20}}},
         {"label": "Lay your hand on the heart", "check": {"die": "armor", "n": 5},
          "ok": {"text": "You hold still as stone while the basilisk looks you over, and the heart beats into you. The wood wakes, and some of it stays in your blood.",
                 "buff": "stoneblood", "mat": "starmetal", "quest": "next", "xp": 20},
          "bad": {"text": "You flinch. Stone creeps up your arm before you pull free.", "buff": "petrifying"}},
         {"label": "Not yet", "ok": {"text": "The heart beats once. The basilisk watches you go."}},
     ]},
    # ---------------------------------------------------------------- the Verdant Deep: the Serpent's Fang
    {"key": "q_jungle_1", "quest": "jungle", "hidden": True, "title": "The Snake-Charmer", "text": "A woman with a python round her shoulders "
     "and a flute in her hand. \"The jade serpent sheds once a century, and this is the year. Find the skin and you'll find the way to "
     "its temple. Its fang is the finest poison in the world. Or ask it nicely for its blessing.\"",
     "choices": [
         {"label": "Go serpent-hunting", "ok": {"text": "She plays a tune, and her python points its nose into the jungle. " + _ACCEPT, "quest": "start", "xp": 6}},
         {"label": "Pass", "ok": {"text": "The python looks disappointed. The woman doesn't."}},
     ]},
    {"key": "q_jungle_2", "quest": "jungle", "hidden": True, "title": "The Shed Skin", "text": "Draped over a fallen temple column, a snakeskin "
     "of translucent green, forty feet long. A trail of crushed ferns leads away from it, and something big is eating the jungle's "
     "smaller residents nearby.",
     "choices": [
         {"label": "Follow the trail", "need": "ranger", "ok": {"text": "You read the jungle like a book. The temple is close.", "quest": "next", "xp": 10}},
         {"label": "Take the skin and follow", "ok": {"text": "Something else wants the skin.",
                                                      "fight": ["shadow_panther", "orchid_mantis"],
                                                      "win": {"text": "The skin is yours, and the trail beyond it leads to the temple.", "quest": "next", "gold": 10}}},
         {"label": "Search the column", "check": {"die": "trinket", "n": 4},
          "ok": {"text": "Carvings of a serpent, and a map scratched under them. The temple is close.", "quest": "next"},
          "bad": {"text": "A nest of dart frogs, very upset.", "hp": -4}},
     ]},
    {"key": "q_jungle_3", "quest": "jungle", "hidden": True, "title": "The Serpent's Temple", "text": "A ziggurat swallowed by the jungle. "
     "On its top, coiled in the sun, the jade serpent, scales like a hoard of emeralds, watching you climb with one lazy golden eye.",
     "choices": [
         {"label": "Take its fang", "ok": {"text": "It uncoils. All of it.",
                                           "fight": ["jade_serpent", "dart_frog", "dart_frog"],
                                           "win": {"text": "The serpent falls still. Its fang drips green, and it's yours.",
                                                   "give": "jade_fang", "quest": "next", "xp": 20}}},
         {"label": "Offer it the skin back", "check": {"die": "best", "n": 5},
          "ok": {"text": "It accepts, with a hiss that might be a laugh, and touches its nose to your brow. The jungle parts for you now.",
                 "buff": "jungle_born", "mat": "fate_feather", "quest": "next", "xp": 20},
          "bad": {"text": "It does not accept. It hisses you all the way down the steps.", "hp": -6}},
         {"label": "Come back later", "ok": {"text": "The serpent closes its eye. It isn't worried."}},
     ]},
    # ---------------------------------------------------------------- Aetherhold: the Fallen Wings
    {"key": "q_heaven_1", "quest": "heaven", "hidden": True, "title": "The Wingless Angel", "text": "An angel sits on the marble steps with "
     "her head in her hands. Two raw scars on her back where her wings were. \"I judged wrongly once,\" she says, \"and they took them. "
     "My feathers fell somewhere in the clouds. Bring them before the Tribunal, and plead for me.\"",
     "choices": [
         {"label": "Agree to plead for her", "ok": {"text": "She looks up for the first time. \"Thank you.\" " + _ACCEPT, "quest": "start", "xp": 6}},
         {"label": "Ask what she judged", "ok": {"text": "\"A mercy,\" she says, \"that wasn't mine to give.\" You think about that for a long time.", "xp": 6}},
     ]},
    {"key": "q_heaven_2", "quest": "heaven", "hidden": True, "title": "Feathers in the Clouds", "text": "White feathers lie scattered across "
     "a meadow of cloud, each one the length of your arm, still glowing faintly. A lantern archon drifts among them, gathering them up.",
     "choices": [
         {"label": "Ask the archon for them", "check": {"die": "best", "n": 5},
          "ok": {"text": "It considers you, and hands them over. \"For the Tribunal,\" it says.", "quest": "next", "xp": 8},
          "bad": {"text": "\"These are evidence,\" it says, and calls the guard.", "fight": ["lantern_archon", "haloed_knight"]}},
         {"label": "Gather them yourself", "ok": {"text": "The archon objects, strongly.",
                                                  "fight": ["lantern_archon", "choir_cherub", "choir_cherub"],
                                                  "win": {"text": "You have every feather. The Tribunal sits not far away.", "quest": "next"}}},
         {"label": "Plead her case to it", "need": "herald", "ok": {"text": "It listens, and gives you every feather. \"Tell them I said so.\"", "quest": "next", "xp": 10}},
     ]},
    {"key": "q_heaven_3", "quest": "heaven", "hidden": True, "title": "The Tribunal", "text": "A court of light at the top of the sky. The "
     "Eye of Judgment turns its wheel of gazes on you, and a voice like a bell asks why you have come.",
     "choices": [
         {"label": "Challenge the Tribunal's verdict", "ok": {"text": "\"Then be judged,\" says the bell.",
                                                              "fight": ["wheel_of_eyes", "seraph_sentinel"],
                                                              "win": {"text": "The Tribunal yields. The wings are restored, but she gives them to you: \"Fly better than I did.\"",
                                                                      "give": "arbiter_wings", "quest": "next", "xp": 20}}},
         {"label": "Plead for her mercy", "check": {"die": "party", "n": 6},
          "ok": {"text": "The court is moved. Her wings return to her, and a little of the light they give stays with you.",
                 "buff": "haloed", "mat": "fate_feather", "quest": "next", "xp": 20},
          "bad": {"text": "\"Not today,\" says the bell. You are shown, politely, out.", "buff": "jinx"}},
         {"label": "Come back with a better case", "ok": {"text": "The Tribunal has all the time there is."}},
     ]},
    # ---------------------------------------------------------------- the Prism Wood: the Heartprism
    {"key": "q_crystal_1", "quest": "crystal", "hidden": True, "title": "The Blind Gemcutter", "text": "An old gemcutter with milky eyes and "
     "perfectly steady hands. \"At the heart of the wood there's a prism that holds every colour there is. I've listened to it for "
     "forty years. Tune the singing stones, and it'll let itself be cut. I'd like to hear it up close, just once.\"",
     "choices": [
         {"label": "Take him up on it", "ok": {"text": "He hums you the note to listen for. " + _ACCEPT, "quest": "start", "xp": 6}},
         {"label": "Not now", "ok": {"text": "He goes back to his work, smiling at a sound you can't hear."}},
     ]},
    {"key": "q_crystal_2", "quest": "crystal", "hidden": True, "title": "The Singing Stones", "text": "A circle of crystal pillars, each ringing "
     "a different note, all of them slightly wrong. The resonance makes your teeth ache. Shardlings scuttle between them, feeding on the noise.",
     "choices": [
         {"label": "Tune the pillars", "check": {"die": "weapon", "n": 5},
          "ok": {"text": "A tap here, a tap there, and the circle sings in tune. Far off, something answers.", "quest": "next", "xp": 8},
          "bad": {"text": "A wrong note, and every shardling turns to look.", "fight": ["shardling", "shardling", "resonant_wisp"]}},
         {"label": "Clear out the shardlings", "ok": {"text": "They come at you in a glittering swarm.",
                                                      "fight": ["shardling", "shardling", "prism_spider"],
                                                      "win": {"text": "Without the noise-eaters, the pillars drift into tune on their own.", "quest": "next", "gold": 10}}},
         {"label": "Strike the perfect note", "need": "duelist", "ok": {"text": "One precise touch on the centre pillar, and the whole circle sings.", "quest": "next", "xp": 10}},
     ]},
    {"key": "q_crystal_3", "quest": "crystal", "hidden": True, "title": "The Heartprism", "text": "In a hollow of pure crystal, the Heartprism "
     "turns slowly in the air, throwing every colour there is across the walls. A prism colossus stands guard, its body a cathedral of glass.",
     "choices": [
         {"label": "Break the colossus", "ok": {"text": "It turns, and every facet of it catches the light.",
                                                "fight": ["prism_colossus", "facet_knight"],
                                                "win": {"text": "The colossus shatters into a thousand rainbows. The Heartprism settles into your hand.",
                                                        "give": "heartprism", "quest": "next", "xp": 20}}},
         {"label": "Look into the prism", "check": {"die": "trinket", "n": 5},
          "ok": {"text": "You see everything at once, and when you look away, you keep a little of it. The gemcutter would be proud.",
                 "buff": "clear_eyed", "mat": "starmetal", "quest": "next", "xp": 20},
          "bad": {"text": "Too much light. You see spots for an hour.", "hp": -5}},
         {"label": "Not yet", "ok": {"text": "The prism turns. The colossus doesn't."}},
     ]},
    # ---------------------------------------------------------------- the Drowsing Vale: the Lantern of Sleep
    {"key": "q_dream_1", "quest": "dream", "hidden": True, "title": "The Insomniac", "text": "A man with enormous bags under his eyes sits "
     "bolt upright in a field of poppies. \"The Somnarch lost her lantern,\" he says, \"and now nobody in the Vale can wake up properly, "
     "except me, and I can't sleep at all. Find it. Light it. Please. I'm so tired.\"",
     "choices": [
         {"label": "Find the lantern", "ok": {"text": "He waves vaguely toward the hills, yawning. " + _ACCEPT, "quest": "start", "xp": 6}},
         {"label": "Sing him to sleep", "need": "mender", "ok": {"text": "He's asleep before the second verse. He'll still want the lantern found, though. " + _ACCEPT,
                                                                "quest": "start", "xp": 12}},
         {"label": "Wish him luck", "ok": {"text": "He doesn't hear you. He's counting something."}},
     ]},
    {"key": "q_dream_2", "quest": "dream", "hidden": True, "title": "The Lost Lantern", "text": "The lantern hangs from the branch of a tree that "
     "isn't quite there. Its light is out. Under the tree, a dream eater is sleeping, curled round the trunk, and it snores in colours.",
     "choices": [
         {"label": "Climb past it", "check": {"die": "best", "n": 5},
          "ok": {"text": "Not a sound. The lantern is cold and heavy in your hand, and the edge of waking isn't far.", "quest": "next", "xp": 8},
          "bad": {"text": "A branch creaks. The dream eater opens its eyes, all of them.",
                  "fight": ["dream_eater", "dusk_moth"]}},
         {"label": "Wake it and fight", "ok": {"text": "It wakes hungry.",
                                               "fight": ["dream_eater", "dusk_moth", "dusk_moth"],
                                               "win": {"text": "The lantern drops into your hands. Now to light it, at the edge of waking.", "quest": "next", "gold": 10}}},
         {"label": "Come back later", "ok": {"text": "It goes on snoring, in violet."}},
     ]},
    {"key": "q_dream_3", "quest": "dream", "hidden": True, "title": "The Edge of Waking", "text": "The Vale ends in a cliff of mist. Beyond it is "
     "the waking world. On the brink paces a night mare, black and silver, its mane trailing nightmares, and it will not let the lantern pass.",
     "choices": [
         {"label": "Ride down the night mare", "ok": {"text": "It rears up, screaming.",
                                                      "fight": ["night_mare", "nightmare_knight"],
                                                      "win": {"text": "The mare flees into the mist. The lantern lights itself: it chooses you.",
                                                              "give": "somnarch_lantern", "quest": "next", "xp": 20}}},
         {"label": "Light the lantern and let it go", "check": {"die": "party", "n": 6},
          "ok": {"text": "The lantern floats out over the mist, and the whole Vale sighs and wakes, and dreams better. So do you.",
                 "buff": "lucid_dreamer", "mat": "fate_feather", "quest": "next", "xp": 20},
          "bad": {"text": "The flame gutters. The mare laughs.", "buff": "nightmares"}},
         {"label": "Not yet", "ok": {"text": "The mare paces. The mist waits."}},
     ]},
    # ---------------------------------------------------------------- the Frostpeaks: the Heart of Winter
    {"key": "q_frost_1", "quest": "frost", "hidden": True, "title": "The Frozen Bard", "text": "A bard frozen into a block of ice, mid-song, "
     "lute in hand. When you knock, the ice sings the rest of the verse for him: winter's heart lies at the top of the mountain, and "
     "whoever claims it can thaw anything.",
     "choices": [
         {"label": "Climb to winter's heart", "ok": {"text": "The ice hums the tune that leads the way. " + _ACCEPT, "quest": "start", "xp": 6}},
         {"label": "Try to thaw him now", "check": {"die": "weapon", "n": 6},
          "ok": {"text": "He tumbles out, frostbitten and furious that you interrupted. He tells you the way anyway. " + _ACCEPT, "quest": "start", "gold": 10},
          "bad": {"text": "The ice is harder than your weapon.", "hp": -3}},
     ]},
    {"key": "q_frost_2", "quest": "frost", "hidden": True, "title": "The Frozen Song", "text": "On a high ridge, the bard's tune hangs in the "
     "air as frost, note by note, leading up. Wolves have found the trail too, and they're hungry.",
     "choices": [
         {"label": "Fight off the pack", "ok": {"text": "They come out of the snow all at once.",
                                                "fight": ["frost_wolf", "frost_wolf", "ice_wraith"],
                                                "win": {"text": "The tune climbs on, to a cave near the summit.", "quest": "next", "gold": 10}}},
         {"label": "Sing the tune as you climb", "check": {"die": "party", "n": 5},
          "ok": {"text": "The wolves fall back and sit, ears up, listening. They let you pass.", "quest": "next", "xp": 8},
          "bad": {"text": "Off-key. The wolves don't care for it.", "fight": ["frost_wolf", "frost_wolf"]}},
         {"label": "Come back later", "ok": {"text": "The tune will hang there until spring. Spring isn't coming."}},
     ]},
    {"key": "q_frost_3", "quest": "frost", "hidden": True, "title": "Winter's Heart", "text": "A cave of blue ice at the top of the world. In "
     "the middle, a heart of frozen light beats slowly. An avalanche yeti sleeps round it, keeping it company. It has done this for "
     "a very long time.",
     "choices": [
         {"label": "Wrest the heart from it", "ok": {"text": "The yeti wakes, and the mountain wakes with it.",
                                                     "fight": ["avalanche_yeti", "frozen_revenant"],
                                                     "win": {"text": "The yeti lies still. The heart is cold enough to burn, and it's yours.",
                                                             "give": "rimeheart", "quest": "next", "xp": 20}}},
         {"label": "Keep the yeti company", "need": "warden", "ok": {"text": "You sit with it a while, the way it's sat with the heart. It shares "
                                                                     "a little winter with you when you go.",
                                                                     "buff": "frostborn", "mat": "wyrm_ember", "quest": "next", "xp": 20}},
         {"label": "Touch the heart", "check": {"die": "armor", "n": 5},
          "ok": {"text": "The cold goes through you and doesn't leave. You'll never freeze again.",
                 "buff": "frostborn", "mat": "starmetal", "quest": "next", "xp": 20},
          "bad": {"text": "The cold bites deep.", "hp": -6, "buff": "frostbite"}},
         {"label": "Not yet", "ok": {"text": "The yeti snores. The heart beats."}},
     ]},

    # ================================================================ more events, placed in their regions
    # ---------------------------------------------------------------- Cinderreach
    {"key": "ember_smith", "region": "ash", "title": "The Smith in the Caldera", "text": "A dwarf works an anvil set right on a vent of lava, "
     "hammering blades that hiss when they cool. \"Best forge in the world,\" she says. \"Mind the floor.\"",
     "choices": [
         {"label": "Buy an obsidian blade", "cost": 30, "ok": {"text": "She hands it over still warm.", "give": "obsidian_cleaver"}},
         {"label": "Ask her to work your weapon", "cost": 25, "ok": {"text": "She folds a wyrm's ember into the metal and hands it back, glowing.",
                                                                    "mat": "wyrm_ember"}},
         {"label": "Work the bellows for her", "check": {"die": "armor", "n": 4},
          "ok": {"text": "Hot work. She pays you in coin and a nod.", "gold": 15, "xp": 6},
          "bad": {"text": "The vent spits. So do you.", "hp": -5}},
     ]},
    {"key": "lava_tubes", "region": "ash", "title": "The Lava Tubes", "text": "A tunnel of glassy black rock, carved by old lava, leading "
     "under the mountain. It's warm, and dark, and on the walls someone has painted arrows pointing deeper.",
     "choices": [
         {"label": "Follow the arrows", "check": {"die": "best", "n": 5, "great": 8},
          "great": {"text": "A forgotten cult's treasury, and its relic.", "item": "legendary"},
          "ok": {"text": "A forgotten cult's offering bowl, still full.", "gold": 18, "item": "uncommon"},
          "bad": {"text": "The cult isn't as forgotten as you thought.", "fight": ["ember_cultist", "ember_cultist", "cinder_imp"]}},
         {"label": "Take shelter and rest", "ok": {"text": "Warm stone and no wind. You sleep like the dead.", "hp": 12, "all": True}},
     ]},
    # ---------------------------------------------------------------- the Shifting Sands
    {"key": "caravan_master", "region": "dunes", "title": "The Caravan Master", "text": "A caravan has made camp in the lee of a dune: "
     "camels, carpets, lanterns, and a caravan master with rings on every finger. Everything is for sale, including advice.",
     "choices": [
         {"label": "Buy a scarab amulet", "cost": 45, "ok": {"text": "\"It brought my grandfather back from the dead,\" he says. \"Twice.\"", "give": "scarab_amulet"}},
         {"label": "Buy a bow for the road", "cost": 18, "ok": {"text": "A good bow, strung with gut and sand-polished.", "give": "scarab_bow"}},
         {"label": "Guard the caravan a night", "check": {"die": "party", "n": 5},
          "ok": {"text": "A quiet night. He pays well, and throws in a flask.", "gold": 20, "potion": 1},
          "bad": {"text": "Not a quiet night.", "fight": ["dune_raider", "dune_raider", "carrion_vulture"]}},
     ]},
    {"key": "starfall_crater", "region": "dunes", "title": "The Starfall Crater", "text": "A crater of glassed sand, still faintly warm. At its "
     "bottom, half buried, a lump of black metal that sparkles when the light catches it.",
     "choices": [
         {"label": "Dig it out", "check": {"die": "weapon", "n": 5},
          "ok": {"text": "Starmetal. A smith would sell their own mother for it.", "mat": "starmetal"},
          "bad": {"text": "The glass shatters under you, and the slope is sharp.", "hp": -6}},
         {"label": "Chip off a piece", "ok": {"text": "A sliver of it, worth good gold in any town.", "gold": 15}},
         {"label": "Read the crater", "need": "arcanist", "ok": {"text": "It fell from a star you know the name of. Wonderful.", "xp": 15, "mat": "starmetal"}},
     ]},
    # ---------------------------------------------------------------- the Stillwood
    {"key": "statue_garden", "region": "petrified", "title": "The Statue Garden", "text": "Rows of stone soldiers stand in formation among "
     "the stone trees, an army frozen mid-march. Their general, at the front, holds out a stone sword, hilt first, as if offering it.",
     "choices": [
         {"label": "Take the general's sword", "check": {"die": "best", "n": 5},
          "ok": {"text": "It comes away clean, and it's lighter than stone has any right to be.", "give": "gorgon_glaive"},
          "bad": {"text": "The army turns its heads.", "fight": ["petrified_knight", "petrified_knight", "gargoyle"]}},
         {"label": "Salute and march past", "ok": {"text": "You could swear they salute back. You feel steadier for it.", "buff": "stone_skin"}},
         {"label": "Free one soldier", "need": "mender", "ok": {"text": "The stone softens to flesh under your hands. He weeps, and gives you his medal.", "item": "rare", "xp": 10}},
     ]},
    {"key": "amber_hunter", "region": "petrified", "title": "The Amber Hunter", "text": "A wiry woman with a lantern and a bag full of amber "
     "is picking through the roots of the stone trees. She holds up a drop with a tiny dragonfly inside. \"Trade?\"",
     "choices": [
         {"label": "Trade for the amber drop", "cost": 20, "ok": {"text": "It's warm, and never quite stops moving.", "give": "amber_drop"}},
         {"label": "Help her dig", "check": {"die": "trinket", "n": 4},
          "ok": {"text": "A good haul. She splits it with you.", "gold": 16, "xp": 6},
          "bad": {"text": "You dig up a fossil hound. It's not as fossilized as advertised.", "fight": ["fossil_hound", "fossil_hound"]}},
         {"label": "Ask where the old amber is", "ok": {"text": "She tells you a story about the wood's heart. It sounds like a real place.", "xp": 8}},
     ]},
    # ---------------------------------------------------------------- the Verdant Deep
    {"key": "witch_doctor_hut", "region": "jungle", "title": "The Witch Doctor's Hut", "text": "A hut on stilts, hung with bones and bottles. "
     "The witch doctor inside is stirring a pot that smells of rain. \"Something for the road? Everything has a price.\"",
     "choices": [
         {"label": "Buy a draught of venom", "cost": 22, "ok": {"text": "You rub it into your weapon. It's never quite dry again.", "give": "dart_blowpipe"}},
         {"label": "Drink from the pot", "check": {"die": "best", "n": 4},
          "ok": {"text": "Rain and green things. You feel like you could live forever.", "buff": "jungle_tonic", "hp": 10},
          "bad": {"text": "Rain and green things and something else.", "buff": "nightmares", "hp": -3}},
         {"label": "Trade remedies", "need": "alchemist", "ok": {"text": "She's impressed. You swap recipes, and potions.", "potion": 2, "xp": 10}},
     ]},
    {"key": "river_of_gold", "region": "jungle", "title": "The River of Gold", "text": "A slow brown river winds through the jungle, and in "
     "the shallows, the pebbles glitter. Something long and patient lies very still under the surface, waiting for greed.",
     "choices": [
         {"label": "Pan for gold", "check": {"die": "trinket", "n": 5},
          "ok": {"text": "A pouch of nuggets, and you keep all your fingers.", "gold": 25},
          "bad": {"text": "The patient thing stops being patient.", "fight": ["silverback", "strangler_vine"]}},
         {"label": "Fish instead", "ok": {"text": "Fat river fish, roasted on a stick.", "hp": 10, "all": True}},
         {"label": "Watch the water", "need": "ranger", "ok": {"text": "You spot where it lies, and pan downstream of it in perfect safety.", "gold": 25, "xp": 6}},
     ]},
    # ---------------------------------------------------------------- Aetherhold
    {"key": "celestial_armory", "region": "heaven", "title": "The Celestial Armory", "text": "A pavilion of white silk where angels' weapons "
     "rest on racks of light. A sign in a beautiful hand reads: TAKE WHAT YOU NEED. NOT WHAT YOU WANT.",
     "choices": [
         {"label": "Take what you need", "check": {"die": "armor", "n": 4},
          "ok": {"text": "Your hand closes on exactly the right thing.", "give": "guardian_mantle"},
          "bad": {"text": "Your hand closes on what you wanted. The armory takes it back, firmly.", "hp": -4}},
         {"label": "Take what you want", "ok": {"text": "It comes to your hand gladly, and the Sentinels come with it.",
                                                "fight": ["seraph_sentinel", "haloed_knight"],
                                                "win": {"text": "They concede the point. Keep it.", "give": "sunlance"}}},
         {"label": "Take nothing", "ok": {"text": "A bell rings somewhere. You feel lighter.", "buff": "grace"}},
     ]},
    {"key": "fountain_of_light", "region": "heaven", "title": "The Fountain of Light", "text": "A fountain where the water is light, falling "
     "upward into the sky. Coins glint at the bottom, thousands of years of wishes.",
     "choices": [
         {"label": "Make a wish", "cost": 10, "ok": {"text": "The light swirls round you, and something in you settles.", "hp": 20, "buff": "sun_blessed"}},
         {"label": "Fish out some wishes", "check": {"die": "best", "n": 5},
          "ok": {"text": "A handful of old coins, and a feather that was someone's wish once.", "gold": 15, "give": "angel_feather"},
          "bad": {"text": "The fountain disapproves.", "buff": "jinx"}},
         {"label": "Bathe in the light", "ok": {"text": "Every wound closes.", "hp": 14, "all": True}},
     ]},
    # ---------------------------------------------------------------- the Prism Wood
    {"key": "crystal_spider", "region": "crystal", "title": "The Glass Web", "text": "A web of crystal thread stretches between two trees, "
     "and tangled in it are the treasures of a hundred travellers: rings, blades, lanterns, a whole sea chest. The spider is nowhere to be seen.",
     "choices": [
         {"label": "Cut down the sea chest", "check": {"die": "weapon", "n": 5},
          "ok": {"text": "It thumps down, full of gems.", "gold": 20, "item": "rare"},
          "bad": {"text": "The web rings like a bell. The spider was somewhere to be seen.", "fight": ["prism_spider", "prism_spider", "shardling"]}},
         {"label": "Pluck a ring from the edge", "ok": {"text": "A small prize, but a safe one.", "item": "uncommon"}},
         {"label": "Play the web like a harp", "need": "herald", "ok": {"text": "The spider comes out to listen, and pays in shards.", "mat": "random", "xp": 10}},
     ]},
    {"key": "geode_miners", "region": "crystal", "title": "The Geode Miners", "text": "A camp of gnome miners, singing as they crack geodes "
     "the size of houses. They have far more crystal than they can carry, and they'd like you to take some off their hands. For a price.",
     "choices": [
         {"label": "Buy a crystal tuning fork", "cost": 24, "ok": {"text": "It hums at a pitch that makes your hands quicker.", "give": "tuning_fork"}},
         {"label": "Buy the good stuff", "cost": 40, "ok": {"text": "They lead you to the back of the cave and crack a geode just for you.", "mat": "random", "item": "uncommon"}},
         {"label": "Swing a pick with them", "check": {"die": "weapon", "n": 4},
          "ok": {"text": "They teach you the song. You earn your share.", "gold": 14, "xp": 8},
          "bad": {"text": "Wrong rhythm, wrong rock. Ow.", "hp": -4}},
     ]},
    # ---------------------------------------------------------------- the Drowsing Vale
    {"key": "dream_market", "region": "dream", "title": "The Night Market", "text": "Lanterns hang in the air over a market where the stalls "
     "sell bottled sunsets, second-hand memories, and tomorrow's weather. Everyone is in their nightclothes. Nobody seems to find this odd.",
     "choices": [
         {"label": "Buy a music box", "cost": 40, "ok": {"text": "It plays the song you most want to hear.", "give": "music_box"}},
         {"label": "Sell a bad memory", "ok": {"text": "The merchant pays well for it. You can't remember what it was, which seems to be the point.", "gold": 20, "xp": 4}},
         {"label": "Haggle for a feather", "need": "scoundrel", "ok": {"text": "You walk away with a fate feather and the merchant's purse.", "mat": "fate_feather", "gold": 8}},
         {"label": "Buy a bottled sunset", "cost": 8, "ok": {"text": "You open it. It's lovely.", "hp": 12, "all": True}},
     ]},
    {"key": "mirror_lake", "region": "dream", "title": "The Mirror Lake", "text": "A lake so still it shows the stars at noon. In it, your "
     "reflection is doing something else entirely: it's holding out a knife, handle first.",
     "choices": [
         {"label": "Take the knife", "check": {"die": "trinket", "n": 5},
          "ok": {"text": "Your hand goes into the water and comes out with it, dry.", "give": "sleepwalker_knife"},
          "bad": {"text": "Your reflection grabs your wrist, and climbs out.", "fight": ["mirror_shade", "mirror_shade", "sleepwalker"]}},
         {"label": "Wave to it", "ok": {"text": "It waves back, a little late, and you feel oddly encouraged.", "buff": "lucid"}},
         {"label": "Walk away", "ok": {"text": "Your reflection doesn't. You try not to think about it."}},
     ]},
    # ---------------------------------------------------------------- the Frostpeaks
    {"key": "mammoth_herd", "region": "frost", "title": "The Mammoth Herd", "text": "A herd of woolly mammoths shuffles through the snow, "
     "calves in the middle. One old bull has a broken tusk and a spear stuck in his side, and he watches you with tired eyes.",
     "choices": [
         {"label": "Pull out the spear", "check": {"die": "best", "n": 5},
          "ok": {"text": "He groans, then nudges you gently with his trunk. Around his neck, a hunter's amulet he's carried for years.", "give": "rime_amulet", "xp": 8},
          "bad": {"text": "He doesn't understand, and neither does the herd.", "fight": ["woolly_mammoth"]}},
         {"label": "Walk with the herd", "ok": {"text": "They break the wind for you all afternoon.", "buff": "warm_furs", "all": True}},
         {"label": "Tend his wound", "need": "warden", "ok": {"text": "The herd accepts you as one of its own. A calf gives you a lick.", "hp": 15, "all": True, "xp": 10}},
     ]},
    {"key": "ice_forge", "region": "frost", "title": "The Ice Forge", "text": "A frost giant's forge, cold and abandoned, where weapons were "
     "worked from ice that never melts. One is still on the anvil, half finished. The giant's hammer leans against the wall.",
     "choices": [
         {"label": "Finish the weapon", "check": {"die": "weapon", "n": 6},
          "ok": {"text": "Three blows, and the ice rings true. It's a blade fit for a giant's hand, cut down to yours.", "give": "frostbrand"},
          "bad": {"text": "The ice shatters, and the giant comes home to see what the noise was.", "fight": ["frost_giant"]}},
         {"label": "Take an ice pick from the rack", "ok": {"text": "Small, sharp, never warms.", "give": "ice_pick"}},
         {"label": "Search the forge", "check": {"die": "trinket", "n": 4},
          "ok": {"text": "A lump of starmetal, waiting to be worked.", "mat": "starmetal"},
          "bad": {"text": "Your fingers stick to the anvil.", "hp": -3}},
     ]},
]
