"""More events (Nov 2026): the first three regions' own (they had none, so their event hexes all drew
from the shared pool), and more shared ones. Merged into `archipelago.EVENTS`; the format is the same
as there (a choice's `need` is a class, `check` a roll, and `ok`/`great`/`bad` what happens). Several
choices belong to classes no event used before: the Gunslinger, Samurai, Psion, Spellblade, Dragonborn
and Emberknight."""

EVENTS = [
    # ---------------------------------------------------------------- Coral Shallows
    {"key": "pearl_bed", "region": "coral", "title": "The Pearl Bed", "text": "Oysters the size of cartwheels lie open in the shallows, "
     "each with a pearl inside and a very firm opinion about keeping it.",
     "choices": [
         {"label": "Pry one open", "check": {"die": "weapon", "n": 4, "great": 6},
          "great": {"text": "It gives with a sigh. Two pearls, and a ring someone lost in there.", "gold": 18, "item": "uncommon"},
          "ok": {"text": "A fat pearl, warm from the sun.", "gold": 14},
          "bad": {"text": "It shuts. On you.", "hp": -5}},
         {"label": "Sing to them until they yawn", "need": "herald", "ok": {"text": "Every shell opens. You take only what's offered.", "gold": 20}},
         {"label": "Leave them to it", "ok": {"text": "They clack approvingly as you go."}},
     ]},
    {"key": "drowned_bell_choir", "region": "coral", "title": "Bells Under the Water", "text": "Somewhere below the reef, bells are ringing a "
     "hymn nobody has sung for a hundred years. The water hums with it.",
     "choices": [
         {"label": "Listen until it ends", "ok": {"text": "The last note settles in your bones. You feel steadier.", "buff": "warded"}},
         {"label": "Dive for the bell tower", "check": {"die": "best", "n": 5},
          "ok": {"text": "You come up with a bronze clapper and a lungful of salt.", "mat": "random"},
          "bad": {"text": "Something in the tower rings back, and comes up after you.", "fight": ["deckhand", "deckhand", "siren"]}},
         {"label": "Hum the counter-melody", "need": "psion", "ok": {"text": "The bells fall silent, and something down there thanks you.", "xp": 18}},
     ]},
    {"key": "crab_court", "region": "coral", "title": "The Crab Court", "text": "A great old crab sits on a throne of driftwood, hearing "
     "cases. The current case appears to be about you.",
     "choices": [
         {"label": "Plead your case", "check": {"die": "party", "n": 4},
          "ok": {"text": "Acquitted. The court awards costs, in shiny things.", "gold": 12, "all": True},
          "bad": {"text": "Guilty. The bailiffs close in.", "fight": ["crab", "crab", "urchin"]}},
         {"label": "Bribe the bailiff", "cost": 10, "ok": {"text": "The case is dismissed on a technicality: the technicality is ten gold."}},
         {"label": "Challenge the judge to single combat", "need": "samurai",
          "ok": {"text": "You bow. It bows. It yields, gravely, and gives you its sword-hand's ring.", "item": "rare"}},
     ]},
    {"key": "kelp_maze", "region": "coral", "title": "The Kelp Maze", "text": "A forest of kelp sways at the tideline, and somewhere "
     "inside it a lantern is bobbing.",
     "choices": [
         {"label": "Follow the lantern", "check": {"die": "armor", "n": 3},
          "ok": {"text": "A lost fisher, very grateful, with a very full net.", "hp": 6, "potion": 1},
          "bad": {"text": "The kelp wraps tight. You cut free, slowly.", "hp": -4, "buff": "soggy"}},
         {"label": "Burn a path through", "need": "emberknight", "ok": {"text": "Steam and a smell of roasting seaweed. The lantern was a pearl diver's: you keep her pearls.", "gold": 16}},
         {"label": "Walk around", "ok": {"text": "A long way round. Your boots are dry, at least."}},
     ]},
    {"key": "shell_merchant", "region": "coral", "title": "The Shell Merchant", "text": "An old woman sells shells from a cart. Most are "
     "ordinary. One of them is definitely watching you.",
     "choices": [
         {"label": "Buy the watching one", "cost": 12, "ok": {"text": "It hums when trouble's near. Useful.", "item": "uncommon"}},
         {"label": "Ask about the shells", "ok": {"text": "You learn more about cowries than anyone has ever needed to.", "xp": 10}},
         {"label": "Read the shell's mind", "need": "psion", "ok": {"text": "It knows where a wreck lies. You go and look.", "chain": "cache"}},
     ]},

    # ---------------------------------------------------------------- Smugglers' Keys
    {"key": "card_game", "region": "keys", "title": "A Friendly Game", "text": "Three smugglers at a barrel-top table wave you over. "
     "The cards are marked. So, you notice, are the smugglers.",
     "choices": [
         {"label": "Play a hand", "cost": 5, "check": {"die": "trinket", "n": 4, "great": 6},
          "great": {"text": "You clean them out, marks and all.", "gold": 30},
          "ok": {"text": "You come out ahead, just.", "gold": 12},
          "bad": {"text": "You come out lighter."}},
         {"label": "Cheat better than they do", "need": "scoundrel", "ok": {"text": "They never see it. Neither, frankly, do you.", "gold": 25}},
         {"label": "Call them out", "check": {"die": "weapon", "n": 4},
          "ok": {"text": "They fold, and leave the pot.", "gold": 15},
          "bad": {"text": "They draw steel.", "fight": ["cutthroat", "rum_runner", "parrot"]}},
     ]},
    {"key": "quick_draw", "region": "keys", "title": "High Noon at the Keys", "text": "A gunfighter in a long coat blocks the jetty. "
     "\"Nobody passes,\" she says, \"who can't beat me to the draw.\"",
     "choices": [
         {"label": "Beat her to the draw", "need": "gunslinger", "ok": {"text": "Your shot clips her hat off before her hand moves. She tips what's left and hands you her spare cylinder.", "item": "rare"}},
         {"label": "Try your luck anyway", "check": {"die": "best", "n": 6},
          "ok": {"text": "You're faster. She's impressed, and pays the toll to you instead.", "gold": 15},
          "bad": {"text": "She's faster. She aims low, out of courtesy.", "hp": -6}},
         {"label": "Take the long way round", "ok": {"text": "She watches you go, a little disappointed."}},
     ]},
    {"key": "rum_cellar", "region": "keys", "title": "The Rum Cellar", "text": "A hidden cellar full of barrels. Some are rum. Some are "
     "powder. They are labelled, helpfully, in a code.",
     "choices": [
         {"label": "Crack the code", "need": "arcanist", "ok": {"text": "Rum on the left, powder on the right. You take a little of each.", "potion": 2, "gold": 10}},
         {"label": "Open a barrel and hope", "check": {"die": "trinket", "n": 4},
          "ok": {"text": "Rum. Excellent rum.", "hp": 10, "buff": "might"},
          "bad": {"text": "Powder. Briefly, excellent powder.", "hp": -7}},
         {"label": "Seal it up for the revenue men", "ok": {"text": "A tidy reward, paid in coin and a firm handshake.", "gold": 12}},
     ]},
    {"key": "parrot_ransom", "region": "keys", "title": "The Ransomed Parrot", "text": "A note pinned to a palm tree: \"WE HAVE THE "
     "CAPTAIN'S PARROT. BRING 20 GOLD.\" Below it, in another hand: \"PLEASE DON'T.\"",
     "choices": [
         {"label": "Pay the ransom", "cost": 20, "ok": {"text": "The parrot is returned. It tells you where the captain hid his good boots.", "item": "uncommon", "xp": 6}},
         {"label": "Storm the hideout", "ok": {"text": "Three of them, and the parrot is on their side.", "fight": ["cutthroat", "quartermaster", "parrot"],
                                               "win": {"text": "The parrot is free, and so is their purse.", "gold": 20}}},
         {"label": "Track them down quietly", "need": "ranger", "ok": {"text": "You find the parrot asleep, and the ransom money beside it.", "gold": 20}},
     ]},
    {"key": "harbour_master", "region": "keys", "title": "The Harbour Master", "text": "A harried official with a ledger stops you. "
     "There are dues, he says. There are always dues.",
     "choices": [
         {"label": "Pay the dues", "cost": 8, "ok": {"text": "He stamps your hand. Every dock in the Keys waves you through.", "buff": "swift"}},
         {"label": "Show him your sword", "need": "samurai", "ok": {"text": "He studies the blade, then his ledger, and finds you exempt.", "buff": "swift"}},
         {"label": "Dodge him", "check": {"die": "armor", "n": 3},
          "ok": {"text": "Through a crowd and over a crate. Gone."},
          "bad": {"text": "He catches you, and the fine is bigger than the dues.", "gold": -12}},
     ]},

    # ---------------------------------------------------------------- Stormcrag
    {"key": "eagle_nest", "region": "storm", "title": "The Eagle's Nest", "text": "A nest of driftwood on a crag, lined with bright "
     "things a storm eagle has stolen over the years. The eagle is out. For now.",
     "choices": [
         {"label": "Climb for it", "check": {"die": "armor", "n": 4, "great": 6},
          "great": {"text": "A whole nest of treasures, and you're down before the eagle's back.", "item": "rare"},
          "ok": {"text": "You grab what glints.", "item": "uncommon"},
          "bad": {"text": "The eagle comes back.", "fight": ["harpy", "harpy"]}},
         {"label": "Leave it", "ok": {"text": "You hear the eagle come home, and are glad you aren't in its nest."}},
         {"label": "Fly up on your own wings", "need": "dragonborn", "ok": {"text": "You land in the nest, take your pick, and are gone before it notices.", "item": "rare"}},
     ]},
    {"key": "lightning_rod", "region": "storm", "title": "The Lightning Rod", "text": "An iron rod on the crag's top, scorched black. "
     "The sky is darkening. Lightning will strike it in a minute, give or take.",
     "choices": [
         {"label": "Catch the bolt in your blade", "need": "spellblade", "ok": {"text": "The lightning runs down the rod, into your sword, and stays.", "buff": "might", "xp": 12}},
         {"label": "Stand clear and watch", "ok": {"text": "The bolt hits. The rod sings. You learn something about storms.", "xp": 10}},
         {"label": "Take the rod", "check": {"die": "best", "n": 5},
          "ok": {"text": "You wrench it free just before the bolt. Good iron.", "mat": "random"},
          "bad": {"text": "You don't.", "hp": -8}},
     ]},
    {"key": "hermit_tea", "region": "storm", "title": "Tea with a Hermit", "text": "A hermit invites you into his cave for tea. The "
     "tea is boiling on a fire of what are definitely someone's boots.",
     "choices": [
         {"label": "Drink the tea", "check": {"die": "party", "n": 3},
          "ok": {"text": "It's awful, and it works.", "hp": 10, "all": True},
          "bad": {"text": "It's awful, and it doesn't.", "buff": "frail"}},
         {"label": "Ask about the boots", "ok": {"text": "A long story about a harpy. You learn where it nests.", "xp": 8}},
         {"label": "Brew it properly", "need": "alchemist", "ok": {"text": "The hermit weeps. It's the best tea he's had in forty years.", "potion": 2, "xp": 8}},
     ]},
    {"key": "rockslide", "region": "storm", "title": "Rockslide!", "text": "The slope above starts to move. Rocks the size of sheep, and "
     "a few actual sheep, are coming down.",
     "choices": [
         {"label": "Brace and take it", "check": {"die": "armor", "n": 4},
          "ok": {"text": "The rocks bounce off your shield. A sheep doesn't, but it's fine.", "xp": 6},
          "bad": {"text": "The rocks don't bounce.", "hp": -7}},
         {"label": "Run for it", "check": {"die": "best", "n": 4},
          "ok": {"text": "You're clear. The sheep is too, and follows you for a while.", "buff": "swift"},
          "bad": {"text": "Not quite fast enough.", "hp": -4}},
         {"label": "Hold the slope", "need": "vanguard", "ok": {"text": "You plant your shield and the slide parts round you. Under the rocks: an old cache.", "gold": 18}},
     ]},
    {"key": "storm_shrine", "region": "storm", "title": "The Storm Shrine", "text": "A cairn of black stones on the cliff edge, crackling. "
     "Offerings of copper wire are wound round it.",
     "choices": [
         {"label": "Leave an offering", "cost": 6, "ok": {"text": "The crackling settles into a hum. The storms let you pass.", "buff": "warded"}},
         {"label": "Draw the storm into yourself", "need": "psion", "ok": {"text": "Your thoughts run fast and bright for days.", "xp": 18}},
         {"label": "Take the copper", "ok": {"text": "The shrine takes offence. So does what guards it.", "fight": ["storm_wisp", "storm_wisp", "stormcaller"],
                                             "win": {"text": "The guardians scatter into the wind. The copper is yours.", "gold": 15}}},
     ]},

    # ---------------------------------------------------------------- shared
    {"key": "star_shard", "title": "The Humming Stone", "text": "Something burned across the sky last night and came down here. It's "
     "still warm, and it's still humming.",
     "choices": [
         {"label": "Cut a piece off", "check": {"die": "weapon", "n": 5},
          "ok": {"text": "A sliver of starmetal, cool now.", "mat": "random"},
          "bad": {"text": "It bites back with a flash.", "hp": -6}},
         {"label": "Sit by it and think", "ok": {"text": "You think about very large things for a while.", "xp": 12}},
         {"label": "Listen to its song", "need": "psion", "ok": {"text": "It tells you where the next one will fall. You'll be rich, eventually.", "gold": 15, "xp": 8}},
     ]},
    {"key": "duelling_ghosts", "title": "Two Ghosts, One Grudge", "text": "Two ghosts in old uniforms are duelling with pistols "
     "that fire nothing. They've been at it for sixty years and would like a second.",
     "choices": [
         {"label": "Be the first one's second", "check": {"die": "best", "n": 4},
          "ok": {"text": "Your man wins at last. He fades, grateful, and his pistol stays behind.", "item": "uncommon"},
          "bad": {"text": "Your man loses again. They both blame you.", "buff": "jinx"}},
         {"label": "Declare a draw", "need": "herald", "ok": {"text": "Both ghosts accept, with relief. They leave you sixty years of back pay.", "gold": 22}},
         {"label": "Load the pistols properly", "need": "gunslinger", "ok": {"text": "Real shot, for once. Both miss. Both laugh. Both are finally at peace.", "xp": 20}},
     ]},
    {"key": "fortune_teller", "title": "The Fortune Teller", "text": "A tent pitched where no tent should be. Inside, a woman with "
     "seven rings turns over cards before you've sat down.",
     "choices": [
         {"label": "Have your fortune told", "cost": 5, "check": {"die": "trinket", "n": 4},
          "ok": {"text": "Good fortune. And then, oddly, it comes true.", "buff": "might"},
          "bad": {"text": "The Tower, the Drowned Man, and a card she won't show you.", "buff": "jinx"}},
         {"label": "Tell hers", "need": "psion", "ok": {"text": "She goes pale, packs her tent, and leaves you her best deck.", "item": "uncommon"}},
         {"label": "Politely leave", "ok": {"text": "She calls after you: \"Mind the third wave.\" You do."}},
     ]},
    {"key": "drake_egg", "title": "The Warm Egg", "text": "In a nest of scorched rock: an egg the size of a helmet, warm to the touch "
     "and ticking gently.",
     "choices": [
         {"label": "Keep it warm until it hatches", "need": "dragonborn", "ok": {"text": "A tiny drake, which looks at you, sneezes fire, and flies home. It leaves you a scale.", "mat": "random", "xp": 10}},
         {"label": "Sell it at the next town", "ok": {"text": "A collector pays well, and asks no questions.", "gold": 18}},
         {"label": "Leave it be", "ok": {"text": "Somewhere above, something large approves."}},
     ]},
    {"key": "sword_in_stone", "title": "The Sword in the Rock", "text": "A sword stands buried to the hilt in a boulder. A sign "
     "beside it reads: \"Seriously, don't.\"",
     "choices": [
         {"label": "Pull it out", "check": {"die": "weapon", "n": 6},
          "ok": {"text": "It slides free. It's a very good sword.", "item": "rare"},
          "bad": {"text": "It does not. You strain something.", "hp": -4}},
         {"label": "Draw it the right way", "need": "samurai", "ok": {"text": "One clean motion: the rock splits, and the sword is yours.", "item": "rare"}},
         {"label": "Respect the sign", "ok": {"text": "The sign seems relieved."}},
     ]},
    {"key": "forge_spirit", "title": "The Forge Spirit", "text": "An old forge, cold for years, flickers alight as you pass. A voice "
     "in the coals asks for something to burn.",
     "choices": [
         {"label": "Feed it some gold", "cost": 10, "ok": {"text": "The coals glow white. Your gear comes out of the flames better.", "temper": "hone"}},
         {"label": "Feed it your own fire", "need": "emberknight", "ok": {"text": "It burns with yours, and bakes a hard edge into your blade.", "temper": "edge", "xp": 8}},
         {"label": "Warm your hands and go", "ok": {"text": "It's a nice fire, for a haunted one.", "hp": 6}},
     ]},
    {"key": "mirror_pool", "title": "The Mirror Pool", "text": "A perfectly still pool. Your reflection in it is doing something "
     "slightly different from you.",
     "choices": [
         {"label": "Reach for your reflection", "check": {"die": "best", "n": 5},
          "ok": {"text": "It shakes your hand, and gives you something it had in its pocket.", "item": "uncommon"},
          "bad": {"text": "It pulls. You get away, but something stays behind.", "buff": "frail"}},
         {"label": "Out-stare it", "need": "spellblade", "ok": {"text": "It blinks first. You learn its tricks.", "xp": 16}},
         {"label": "Throw a stone in", "ok": {"text": "Ripples. When they settle, it's just you again. Probably."}},
     ]},
    {"key": "travelling_circus", "title": "The Travelling Circus", "text": "A circus has washed up, tents and all, and is putting on "
     "a show for nobody. Now it has an audience.",
     "choices": [
         {"label": "Watch the show (bring friends)", "ok": {"text": "Jugglers, a strongman, and an extremely talented seal. Everyone feels better.", "hp": 8, "all": True}},
         {"label": "Join the act", "check": {"die": "party", "n": 4},
          "ok": {"text": "A standing ovation, and a share of the take.", "gold": 10, "all": True},
          "bad": {"text": "You are booed by a seal.", "buff": "jinx"}},
         {"label": "Hire the strongman", "cost": 15, "ok": {"text": "He teaches you how to lift properly.", "buff": "vigor"}},
     ]},
]
