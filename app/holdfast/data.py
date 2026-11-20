"""Holdfast's numbers: the towers, the enemies, the bosses, the items, the waves and the maps.

Distances are in tiles (the board is COLS x ROWS of them), times in seconds. The browser gets
TOWERS, ENEMIES, ITEMS and the chosen map as they are here, so its panels never disagree with the
rules. `tools/holdfast-sim.py` plays whole games with a simple builder to show how the numbers land.
"""

COLS, ROWS = 20, 12
LIVES = 20
WAVES = 30
START_GOLD = (130, 60)  # shared out between the players, plus this much each
SELL_BACK = 0.7
BUILD_TIME = (25, 12)  # seconds before the first wave, and between waves
DIFFICULTY = {"easy": 0.75, "normal": 1.0, "hard": 1.15}  # enemy health

# Each tower has its base numbers and two upgrade paths of four tiers. Both paths can be bought
# ("crosspathing"), but only one of them past tier 2: a tower is at most 4-2. The path with more
# tiers is the tower's main path (on a tie, the one bought first): its tiers' `set` replace numbers,
# in order. The other path's tiers give only their `cross` bonus (below). Tier four is the main
# path's final evolution, which renames the tower; only one of each may stand on the map at a time.
#
# Numbers a tower can have (distances in tiles, times in seconds):
#   mode     shoot (projectiles at enemies), splash (a shell that bursts on the first enemy it meets,
#            or where it lands), radial (projectiles all round), aura (everything in reach), chain
#            (lightning that jumps), trap (piles on the road), sentry (builds little turrets),
#            support (helps towers in reach) or income (pays gold)
#   range    reach (mortars reach the whole board)   rate    seconds between shots
#   dmg      damage a hit                           shots   projectiles a volley
#   dtype    damage type: sharp, blast, cold, energy, fire, arcane or normal. Some enemies are immune
#            to a type (ENEMIES' `immune`); normal hurts everything
#   speed    how fast its projectiles fly, tiles a second   pierce  enemies one projectile can hit
#   lob      (splash) the shell is lobbed: it lands where it was aimed, after a flight
#   air      can it hit flyers?                     ground  can it hit things on the ground (default yes)?
#   ap       ignores armour
#   splash   blast radius                           cluster extra small blasts around each blast
#   slow     how much it slows (0.4: 40% slower), for `hold` s
#   stun     seconds a hit stops an enemy dead (bosses and blimps: a third as long)
#   burn     damage a second it sets burning, for `burn_for` s (burning ignores armour)
#   shred    armour a hit strips off for good      brittle  slowed enemies take this much more damage
#   boss     damage to bosses and blimps (Warlords, Juggernauts...) is multiplied by this
#   chain    enemies a bolt jumps to
#   trap     (traps) spike, mine (bursts with `splash`) or tar; `hits` enemies a pile hurts before it's
#            used up, `max` piles at once, each lasting `life` seconds of fighting
#   sentry   (sentries) the turret's own numbers; `max` at once, each lasting `life` seconds of fighting
#   boost / reach / power   (support) towers in reach fire faster / reach further / hit harder; the
#            best in reach counts for each, not the sum
#   unlock   (support) towers in reach hurt every type, immune or not
#   income   gold to the builder at the end of every wave
#   bounty   kills in its reach pay everyone this much more
#   detect   can it see Ghosts (camouflaged)? Auras always can; projectiles hit any Ghost they meet
#   reveal   (support) towers in its reach can see Ghosts too
#
# A tier's `cross` is what it gives a tower whose main path is the other one: `dmg`, `rate`, `range`,
# `splash`, `burn`, `income`, `life` and `speed` multiply; `pierce`, `chain`, `cluster`, `hits`,
# `max`, `shred` and `shots` add; other numbers raise to at least that much; yes/no ones turn on.
#
# Each final evolution also has an `ability` (ABILITIES, below): a power anyone may trigger, on a
# cooldown that only runs while a wave is being fought.

CROSS_MUL = {"dmg", "rate", "range", "splash", "burn", "income", "life", "speed"}
CROSS_ADD = {"pierce", "chain", "cluster", "hits", "max", "shred", "shots"}
DTYPES = ("sharp", "blast", "cold", "energy", "fire", "arcane", "normal")


def tier(name, cost, blurb, cross=None, **set_):
    return {"name": name, "cost": cost, "blurb": blurb, "set": set_, "cross": cross or {}}


TOWERS = {
    "archer": {
        "name": "Archer", "cost": 50, "blurb": "Cheap and quick. Hits flyers.",
        "base": {"mode": "shoot", "range": 3.2, "rate": 0.6, "dmg": 10, "air": True, "dtype": "sharp",
                 "speed": 14, "pierce": 1},
        "paths": [
            {"name": "Marksman", "tiers": [
                tier("Sharp Arrows", 60, "Hits much harder, and each arrow goes through two.", dict(dmg=1.25),
                     dmg=22, pierce=2),
                tier("Longbow", 120, "Reaches further, hits harder, and spots Ghosts.", dict(range=1.1, detect=True),
                     range=4.3, dmg=46, detect=True),
                tier("Bodkin Points", 260, "Arrows punch through armour, and hurt anything.", dmg=106, ap=True,
                     dtype="normal", speed=20),
                tier("Eagle Eye", 1500, "Final evolution: a sharpshooter who sees the whole road and fells bosses.",
                     range=9, dmg=565, rate=0.45, boss=2, speed=30, pierce=3),
            ]},
            {"name": "Volley", "tiers": [
                tier("Quick Draw", 70, "Shoots faster.", dict(rate=0.85), rate=0.42, dmg=17),
                tier("Twin Shot", 150, "Two arrows a shot, at two enemies.", dict(pierce=1), shots=2, dmg=19),
                tier("Triple Shot", 300, "Three arrows, faster still.", shots=3, rate=0.34, dmg=23),
                tier("Storm of Arrows", 1400, "Final evolution: eight arrows, five times a second.",
                     shots=8, rate=0.2, dmg=30, range=3.8, pierce=2),
            ]},
        ],
    },
    "cannon": {
        "name": "Cannon", "cost": 90, "blurb": "Blasts a crowd. Can't aim at flyers.",
        "base": {"mode": "splash", "range": 2.8, "rate": 1.4, "dmg": 22, "splash": 1.1, "air": False,
                 "dtype": "blast", "speed": 9},
        "paths": [
            {"name": "Heavy", "tiers": [
                tier("Bigger Bombs", 100, "Harder hits, wider blasts.", dict(splash=1.2), dmg=46, splash=1.3),
                tier("Heavy Shells", 200, "Much harder hits.", dict(dmg=1.25), dmg=95),
                tier("Shatter Shells", 380, "Each blast strips armour for good, and hurts anything.", dmg=203, shred=2,
                     dtype="normal"),
                tier("Doomsday Gun", 2200, "Final evolution: one enormous shell that flattens everything.",
                     dmg=1650, splash=2.3, rate=1.7, range=3.4, boss=1.5),
            ]},
            {"name": "Rapid", "tiers": [
                tier("Fast Loader", 110, "Fires faster.", dict(rate=0.85), rate=1.0, dmg=35),
                tier("Cluster Bombs", 220, "Each shell scatters three more small blasts.", dict(cluster=1), cluster=3),
                tier("Concussion", 400, "Blasts stun what they hit.", stun=0.35, dmg=70),
                tier("Carpet Bomber", 2100, "Final evolution: a rain of clustered, stunning shells.",
                     rate=0.35, cluster=6, stun=0.45, dmg=96),
            ]},
        ],
    },
    "frost": {
        "name": "Frost", "cost": 70, "blurb": "Slows everything near it.",
        "base": {"mode": "aura", "range": 2.3, "rate": 1.0, "dmg": 2, "slow": 0.35, "hold": 1.5, "air": True,
                 "dtype": "cold"},
        "paths": [
            {"name": "Deep Freeze", "tiers": [
                tier("Colder", 80, "Slows harder.", dict(slow=0.4), slow=0.45),
                tier("Wide Chill", 150, "Reaches further.", dict(range=1.15), range=3.0),
                tier("Brittle Ice", 300, "Slowed enemies take a quarter more damage from everything.", brittle=0.25),
                tier("Absolute Zero", 1700, "Final evolution: the whole field crawls, and shatters.",
                     slow=0.7, range=4.6, brittle=0.5, dmg=10),
            ]},
            {"name": "Ice Shards", "tiers": [
                tier("Shards", 90, "Each pulse cuts.", dict(dmg=2.5), dmg=9),
                tier("Flash Freeze", 200, "Pulses freeze enemies solid for a moment.", dict(stun=0.15), stun=0.3, dmg=10),
                tier("Shard Storm", 380, "Pulses cut deep.", dmg=28, rate=0.8),
                tier("Blizzard", 1800, "Final evolution: a storm of ice that freezes and shreds.",
                     dmg=73, rate=0.55, stun=0.55, range=3.2),
            ]},
        ],
    },
    "ballista": {
        "name": "Ballista", "cost": 120, "blurb": "Slow and far-reaching. Its bolts go through armour and through three enemies.",
        "base": {"mode": "shoot", "range": 6.0, "rate": 2.2, "dmg": 75, "air": True, "ap": True, "dtype": "sharp",
                 "speed": 18, "pierce": 3},
        "paths": [
            {"name": "Siege", "tiers": [
                tier("Heavy Bolts", 130, "Hits much harder, and spots Ghosts.", dict(detect=True), dmg=156, detect=True),
                tier("Steel Bolts", 260, "Hits harder still, and hurts anything.", dict(dmg=1.2), dmg=319, dtype="normal"),
                tier("Giant Slayer", 480, "Triple damage to bosses and blimps.", dmg=668, boss=3),
                tier("Kingslayer", 2400, "Final evolution: one bolt fit to end a Warlord.",
                     dmg=4190, boss=4, rate=2.4, range=8, pierce=6),
            ]},
            {"name": "Repeater", "tiers": [
                tier("Winch", 140, "Reloads faster.", dict(rate=0.85), rate=1.6, dmg=118),
                tier("Double Crank", 280, "Reloads much faster.", dict(pierce=2), rate=1.1, dmg=169),
                tier("Twin Bolts", 500, "Two bolts a shot.", shots=2, dmg=176),
                tier("Gatling Ballista", 2100, "Final evolution: bolts as fast as it can crank.",
                     rate=0.25, dmg=201, shots=2),
            ]},
        ],
    },
    "tesla": {
        "name": "Tesla", "cost": 140, "blurb": "Lightning that jumps from enemy to enemy.",
        "base": {"mode": "chain", "range": 2.6, "rate": 0.8, "dmg": 15, "chain": 3, "air": True, "dtype": "energy"},
        "paths": [
            {"name": "Arc", "tiers": [
                tier("Longer Arcs", 150, "Jumps to more enemies.", dict(chain=1), chain=5, dmg=21),
                tier("High Voltage", 280, "Hits harder.", dict(dmg=1.25), dmg=41),
                tier("Arc Web", 500, "Jumps much further down the line.", chain=9, dmg=50),
                tier("Storm Spire", 2100, "Final evolution: lightning through the whole wave.",
                     chain=24, dmg=75, range=4.2, rate=0.5),
            ]},
            {"name": "Overload", "tiers": [
                tier("Jolt", 150, "Each hit stuns.", dict(stun=0.1), stun=0.2, dmg=31),
                tier("Capacitor", 300, "Strikes faster.", dict(rate=0.85), rate=0.55, dmg=43),
                tier("Overcharge", 520, "Harder, longer stuns, and it hurts anything.", dmg=88, stun=0.35, dtype="normal"),
                tier("Thunder God", 2200, "Final evolution: bolts that stop anything in its tracks.",
                     dmg=254, stun=0.8, chain=6, rate=0.55, boss=1.5),
            ]},
        ],
    },
    "beacon": {
        "name": "Beacon", "cost": 110, "blurb": "Doesn't shoot. Towers beside it fire faster.",
        "base": {"mode": "support", "range": 1.6, "boost": 0.2, "air": False},
        "paths": [
            {"name": "Rally", "tiers": [
                tier("Drums", 120, "Towers beside it fire faster still.", dict(boost=0.25), boost=0.3),
                tier("Tall Pole", 200, "Reaches further.", dict(range=1.2), range=2.3),
                tier("Battle Hymn", 380, "Much faster firing.", boost=0.45),
                tier("War Banner", 1800, "Final evolution: towers near it fire far faster and hit harder.",
                     boost=0.8, range=3.2, power=0.5),
            ]},
            {"name": "Watch", "tiers": [
                tier("Spyglass", 120, "Towers beside it reach further and can see Ghosts.", dict(reveal=True),
                     reach=0.15, reveal=True),
                tier("Lookout", 220, "Reaches further, and so do they.", dict(reach=0.15), reach=0.25, range=2.0),
                tier("Sharpening Stone", 400, "Towers beside it hit harder.", power=0.25),
                tier("Lighthouse", 1700, "Final evolution: lights up the field for every tower near it.",
                     reach=0.5, range=3.5, power=0.35, boost=0.3),
            ]},
        ],
    },
    "brazier": {
        "name": "Brazier", "cost": 100, "blurb": "Sets everything near it burning. Burning ignores armour.",
        "base": {"mode": "aura", "range": 2.0, "rate": 0.5, "dmg": 5, "burn": 16, "burn_for": 2.0, "air": False,
                 "dtype": "fire"},
        "paths": [
            {"name": "Inferno", "tiers": [
                tier("Hotter Coals", 110, "Burns harder.", dict(burn=1.3), burn=35, dmg=7.4),
                tier("Bellows", 210, "Reaches further.", dict(range=1.1), range=2.4, dmg=25),
                tier("White Heat", 400, "Burns much harder and longer.", burn=72, burn_for=3.0, dmg=58),
                tier("Dragon's Breath", 2000, "Final evolution: a firestorm that reaches flyers and burns anything.",
                     burn=256, range=3.4, dmg=277, air=True, dtype="normal"),
            ]},
            {"name": "Pitch", "tiers": [
                tier("Pitch", 110, "Sticky fire slows what it touches.", dict(slow=0.15, hold=1.0), slow=0.2, hold=1.0, dmg=15),
                tier("Melt", 230, "Fire strips armour for good.", dict(shred=1), shred=1, dmg=44),
                tier("Tar Pit", 420, "Slows harder, burns harder.", slow=0.35, burn=48, dmg=86),
                tier("Hellfire", 1800, "Final evolution: tar that holds and burns everything in it.",
                     slow=0.55, burn=176, dmg=404, range=2.8, shred=2),
            ]},
        ],
    },
    "mortar": {
        "name": "Mortar", "cost": 130, "blurb": "Lobs shells anywhere on the board. Slow, can't hit flyers, and moving targets can dodge.",
        "base": {"mode": "splash", "lob": True, "range": 30, "rate": 3.0, "dmg": 40, "splash": 1.3, "air": False,
                 "dtype": "blast"},
        "paths": [
            {"name": "Big Shells", "tiers": [
                tier("Heavy Charge", 140, "Hits harder.", dict(dmg=1.25), dmg=83),
                tier("Wide Shells", 260, "Bigger blasts.", dict(splash=1.2), splash=1.8, dmg=163),
                tier("Siege Shells", 460, "Hits much harder, and hurts anything.", dmg=329, dtype="normal"),
                tier("Meteor", 2200, "Final evolution: shells like falling stars.",
                     dmg=2106, splash=2.7, rate=3.5, boss=1.5),
            ]},
            {"name": "Barrage", "tiers": [
                tier("Quick Crew", 140, "Fires faster.", dict(rate=0.85), rate=2.2, dmg=61),
                tier("Twin Tubes", 280, "Two shells at once.", dict(shots=1, dmg=0.6), shots=2),
                tier("Incendiary", 480, "Shells set everything burning.", burn=25, burn_for=2.5, dmg=66),
                tier("Rain of Fire", 2100, "Final evolution: six burning shells a volley.",
                     shots=6, rate=1.8, burn=50, dmg=73),
            ]},
        ],
    },
    "mint": {
        "name": "Mint", "cost": 150, "blurb": "Doesn't shoot. Pays its builder after every wave.",
        "base": {"mode": "income", "range": 2.0, "income": 25, "air": False},
        "paths": [
            {"name": "Treasury", "tiers": [
                tier("Bigger Vault", 160, "Pays more.", dict(income=1.4), income=45),
                tier("Counting House", 300, "Pays more still.", dict(income=1.3), income=70),
                tier("Bank", 520, "Pays a lot.", income=105),
                tier("Royal Mint", 2100, "Final evolution: a river of gold.", income=360),
            ]},
            {"name": "Bounty", "tiers": [
                tier("Bounty Board", 160, "Kills in its reach pay everyone 15% more.", dict(bounty=0.1), bounty=0.15),
                tier("Reward Posters", 300, "Kills near it pay 30% more, and it reaches further.", dict(range=1.3),
                     bounty=0.3, range=2.6),
                tier("Guild Hall", 520, "Kills near it pay 45% more.", bounty=0.45, income=35),
                tier("Tax Office", 2000, "Final evolution: everything that dies near it pays double.",
                     bounty=1.0, range=4.0, income=60),
            ]},
        ],
    },
    "bladewheel": {
        "name": "Bladewheel", "cost": 85, "blurb": "Flings blades all round itself. Short reach.",
        "base": {"mode": "radial", "range": 1.7, "rate": 1.1, "dmg": 9, "shots": 8, "pierce": 2, "speed": 9,
                 "air": True, "dtype": "sharp"},
        "paths": [
            {"name": "Razor", "tiers": [
                tier("Sharper Blades", 90, "Harder hits, and each blade goes through three.", dict(pierce=1), dmg=16, pierce=3),
                tier("More Blades", 180, "Twelve blades a turn.", dict(rate=0.85), shots=12),
                tier("Whirling Saws", 360, "Faster, harder saws that cut through five.", rate=0.6, dmg=34, pierce=5),
                tier("Maelstrom", 1700, "Final evolution: a whirlwind of twenty saws, four times a second.",
                     shots=20, rate=0.25, dmg=60, pierce=8, range=2.2),
            ]},
            {"name": "Ring of Fire", "tiers": [
                tier("Hot Blades", 100, "Blades set what they cut burning.", dict(burn=10, burn_for=2), burn=10, burn_for=2.0, dmg=12, dtype="fire"),
                tier("Ring of Fire", 220, "Becomes a ring of fire that burns everything near it.", dict(range=1.15),
                     mode="aura", range=1.8, dmg=20, burn=30, rate=0.6),
                tier("Wildfire", 400, "A wider, hotter ring.", range=2.3, dmg=45, burn=60),
                tier("Sunwheel", 1800, "Final evolution: a blazing sun that reaches flyers and burns anything.",
                     range=3.0, dmg=180, burn=180, rate=0.35, dtype="normal"),
            ]},
        ],
    },
    "trapper": {
        "name": "Trapper", "cost": 110, "blurb": "Scatters spikes on the road nearby. Each pile hurts six enemies.",
        "base": {"mode": "trap", "trap": "spike", "range": 2.2, "rate": 2.4, "dmg": 14, "hits": 6, "max": 6,
                 "life": 30, "air": False, "dtype": "sharp"},
        "paths": [
            {"name": "Spikes", "tiers": [
                tier("Sharper Spikes", 100, "Harder spikes that last for nine.", dict(hits=3), dmg=20, hits=9),
                tier("Faster Production", 200, "Lays piles faster, more at a time.", dict(rate=0.8), rate=1.6, max=9),
                tier("Iron Spikes", 380, "Spikes go through armour and hurt anything.", dmg=48, hits=14, ap=True,
                     dtype="normal"),
                tier("Spike Storm", 1800, "Final evolution: the road disappears under spikes.",
                     rate=0.35, hits=25, dmg=120, max=20, life=40),
            ]},
            {"name": "Mines", "tiers": [
                tier("Blasting Caps", 110, "Lays mines that burst on the first enemy over them.", dict(dmg=1.3),
                     trap="mine", dtype="blast", dmg=60, splash=1.0, hits=1),
                tier("Bigger Charges", 220, "Bigger, wider blasts.", dict(max=2), dmg=130, splash=1.3),
                tier("Shrapnel Mines", 420, "Blasts stun what they hit.", dmg=240, stun=0.4),
                tier("Minefield", 1900, "Final evolution: a field of huge mines that hurt anything.",
                     dmg=900, splash=1.8, rate=0.6, max=16, stun=0.6, dtype="normal"),
            ]},
        ],
    },
    "workshop": {
        "name": "Workshop", "cost": 120, "blurb": "Builds crossbow sentries beside the road. Each lasts 20 seconds.",
        "base": {"mode": "sentry", "range": 2.5, "rate": 6.0, "max": 2, "life": 20, "air": False,
                 "sentry": {"mode": "shoot", "range": 2.6, "rate": 0.7, "dmg": 12, "pierce": 1, "speed": 12,
                            "dtype": "sharp", "air": True}},
        "paths": [
            {"name": "Crossbows", "tiers": [
                tier("Better Sentries", 110, "Sentries hit twice as hard.", dict(max=1),
                     sentry={"mode": "shoot", "range": 2.6, "rate": 0.7, "dmg": 24, "pierce": 1, "speed": 12,
                             "dtype": "sharp", "air": True}),
                tier("Faster Assembly", 220, "Builds sentries much faster.", dict(rate=0.8), rate=3.5),
                tier("Sentry Guns", 420, "Quick, hard-hitting sentries that see Ghosts; four at a time.", max=4,
                     sentry={"mode": "shoot", "range": 2.8, "rate": 0.4, "dmg": 50, "pierce": 2, "speed": 14,
                             "dtype": "sharp", "air": True, "detect": True}),
                tier("Clockwork Legion", 1900, "Final evolution: an army of ten clockwork sentries.",
                     rate=1.2, max=10,
                     sentry={"mode": "shoot", "range": 3.0, "rate": 0.25, "dmg": 110, "pierce": 3, "speed": 16,
                             "dtype": "sharp", "air": True, "detect": True}),
            ]},
            {"name": "Siege Engines", "tiers": [
                tier("Bomb Sentries", 120, "Sentries lob bombs instead.", dict(life=1.5),
                     sentry={"mode": "splash", "range": 2.4, "rate": 1.2, "dmg": 30, "splash": 0.9, "speed": 9,
                             "dtype": "blast", "air": False}),
                tier("Bigger Bombs", 240, "Harder, wider bombs.", dict(rate=0.8),
                     sentry={"mode": "splash", "range": 2.4, "rate": 1.2, "dmg": 70, "splash": 1.1, "speed": 9,
                             "dtype": "blast", "air": False}),
                tier("Tesla Sentries", 440, "Sentries throw lightning that jumps four times.",
                     sentry={"mode": "chain", "range": 2.6, "rate": 0.7, "dmg": 60, "chain": 4, "dtype": "energy",
                             "air": True}),
                tier("Thunder Forge", 2000, "Final evolution: five storm sentries whose lightning stuns.",
                     rate=2.0, max=5,
                     sentry={"mode": "chain", "range": 3.0, "rate": 0.5, "dmg": 200, "chain": 7, "stun": 0.3,
                             "dtype": "energy", "air": True}),
            ]},
        ],
    },
    "arcanist": {
        "name": "Arcanist", "cost": 160, "blurb": "Arcane bolts that go through two enemies and hit flyers.",
        "base": {"mode": "shoot", "range": 3.0, "rate": 1.0, "dmg": 26, "pierce": 2, "speed": 11, "air": True,
                 "dtype": "arcane"},
        "paths": [
            {"name": "Pyromancy", "tiers": [
                tier("Fire Bolt", 150, "Bolts of fire set what they hit burning.", dict(burn=10, burn_for=2),
                     dmg=34, burn=12, burn_for=2.0, dtype="fire"),
                tier("Fireball", 280, "Fireballs burst over a crowd.", dict(dmg=1.25), mode="splash", splash=1.0, dmg=60),
                tier("Dragonfire", 500, "Bigger, hotter fireballs.", dmg=140, burn=40, splash=1.3),
                tier("Archmage of Flame", 2100, "Final evolution: fireballs that burn anything.",
                     dmg=520, burn=160, splash=1.8, rate=0.6, range=3.8, dtype="normal"),
            ]},
            {"name": "Arcana", "tiers": [
                tier("Seer's Eye", 140, "Sees Ghosts and reaches further.", dict(detect=True), detect=True, range=3.4),
                tier("Arcane Lance", 300, "Lances that fly fast and go through six.", dict(pierce=2), pierce=6, speed=18, dmg=50),
                tier("Unravel", 520, "Lances that pierce armour, strip it and hurt anything.", dmg=120, ap=True, shred=1,
                     dtype="normal"),
                tier("Archmage of Stars", 2100, "Final evolution: three star-lances at once, through ten each.",
                     shots=3, dmg=400, pierce=10, rate=0.5),
            ]},
        ],
    },
    "skyhook": {
        "name": "Skyhook", "cost": 100, "blurb": "Harpoons flyers out of the sky. Can't hit the ground.",
        "base": {"mode": "shoot", "range": 4.5, "rate": 1.0, "dmg": 40, "pierce": 2, "speed": 20, "air": True,
                 "ground": False, "dtype": "sharp"},
        "paths": [
            {"name": "Harpoons", "tiers": [
                tier("Barbed Harpoons", 100, "Hits much harder.", dict(dmg=1.25), dmg=85),
                tier("Heavy Harpoons", 200, "Harpoons that go through armour.", dict(ap=True), dmg=180, ap=True),
                tier("Skewer", 400, "Harpoons that skewer four.", dmg=400, pierce=4, detect=True),
                tier("Dragonslayer", 1700, "Final evolution: nothing flies over it and lives.",
                     dmg=1500, rate=0.8, range=8, pierce=6, boss=2),
            ]},
            {"name": "Flak", "tiers": [
                tier("Flak Shells", 110, "Shells that burst among flyers.", dict(rate=0.85), mode="splash", splash=1.0,
                     dmg=30, speed=14),
                tier("Ground Targeting", 230, "Can hit the ground too; its shells blast.", dict(ground=True), ground=True,
                     dtype="blast"),
                tier("Bombard", 420, "Harder, wider, faster shells.", dmg=110, splash=1.4, rate=0.6),
                tier("Sky Fortress", 2000, "Final evolution: twin batteries that rule the skies and the road.",
                     dmg=350, splash=1.8, rate=0.3, shots=2, range=5.5),
            ]},
        ],
    },
    "alchemist": {
        "name": "Alchemist", "cost": 130, "blurb": "Throws acid that hurts anything and eats armour. Can't hit flyers.",
        "base": {"mode": "splash", "range": 2.6, "rate": 1.4, "dmg": 14, "splash": 0.8, "speed": 8, "shred": 1,
                 "air": False, "dtype": "normal"},
        "paths": [
            {"name": "Acid", "tiers": [
                tier("Stronger Acid", 120, "Harder hits; strips more armour.", dict(shred=1), dmg=30, shred=2),
                tier("Acid Pools", 240, "Acid keeps eating at what it splashed.", dict(dmg=1.25), burn=20, burn_for=3.0),
                tier("Dissolve", 450, "Acid that dissolves armour and flesh.", dmg=80, shred=4, burn=60),
                tier("Universal Solvent", 1900, "Final evolution: nothing holds together under it.",
                     dmg=400, splash=1.4, shred=8, burn=200, rate=0.9),
            ]},
            {"name": "Elixirs", "tiers": [
                tier("Tonic", 130, "Towers in its reach hit 15% harder.", dict(power=0.1), power=0.15),
                tier("Solvent Draught", 260, "Towers in its reach hurt every type, immune or not.", dict(range=1.2),
                     unlock=True),
                tier("Berserker Brew", 480, "Towers in its reach hit harder and fire faster.", power=0.3, boost=0.2),
                tier("Philosopher's Stone", 1900, "Final evolution: a stone that makes every tower near it a legend.",
                     power=0.5, boost=0.35, range=3.4, income=150),
            ]},
        ],
    },
}
EVOLUTION = 4  # the tier that's a final evolution
CROSS_MAX = 2  # the most tiers the side path can have

# Final evolutions' abilities, by (tower, path). `do` is what it does (Room.ability):
#   strike   `dmg` to enemies: the `pick` strongest (by health), "all" of them, every enemy within
#            `radius` of the one nearest the keep ("lead") or of this tower ("near"); `ground` only
#            if set. Warlords and other bosses take `boss_frac` of their health instead, if given.
#   stun / slow / burn   every enemy (`ground` only if set) for `secs`; slows by `slow`, burns `dps`
#   overdrive  this tower (and its sentries) fire `rate`x as fast for `secs`
#   rally      every tower fires `rate`x as fast for `secs`
#   mark       every enemy takes `more` extra damage for `secs`
#   gold       `gold` to each player now
#   bounty     kills pay `more` extra for `secs`
#   carpet     `piles` piles of this tower's spikes, `mult`x as strong, spread along every road
#   detonate   every pile this tower laid bursts at once, `mult`x as strong
#   deploy     builds this tower's sentries up to twice its limit at once
#   unmake     for `secs`, every enemy loses its immunities and armour
#   transmute  the `pick` toughest enemies that aren't bosses turn to gold: they die, paying `mult`x
ABILITIES = {
    ("archer", 0): {"name": "Headshot", "cd": 30, "do": "strike", "pick": 1, "dmg": 4000, "boss_frac": 0.25,
                    "blurb": "Deals a crushing blow to the toughest enemy on the board."},
    ("archer", 1): {"name": "Arrow Rain", "cd": 40, "do": "strike", "pick": "all", "dmg": 400,
                    "blurb": "Arrows fall on every enemy on the board."},
    ("cannon", 0): {"name": "Doomsday", "cd": 45, "do": "strike", "pick": "lead", "radius": 4, "dmg": 3000, "ground": True,
                    "blurb": "Flattens everything on the ground around the leading enemy."},
    ("cannon", 1): {"name": "Bombing Run", "cd": 40, "do": "stun", "secs": 2.5, "ground": True,
                    "blurb": "Stops every enemy on the ground for 2.5 seconds."},
    ("frost", 0): {"name": "Freeze the Field", "cd": 45, "do": "stun", "secs": 3,
                   "blurb": "Freezes every enemy solid for 3 seconds."},
    ("frost", 1): {"name": "Hailstorm", "cd": 40, "do": "strike", "pick": "all", "dmg": 500,
                   "blurb": "Hail hammers every enemy on the board."},
    ("ballista", 0): {"name": "Execute", "cd": 40, "do": "strike", "pick": 1, "dmg": 999999, "boss_frac": 0.3,
                      "blurb": "Kills the toughest enemy outright (takes 30% off a boss)."},
    ("ballista", 1): {"name": "Overdrive", "cd": 40, "do": "overdrive", "rate": 4, "secs": 6,
                      "blurb": "Fires four times as fast for 6 seconds."},
    ("tesla", 0): {"name": "Thunderstorm", "cd": 40, "do": "strike", "pick": "all", "dmg": 350,
                   "blurb": "Lightning strikes every enemy on the board."},
    ("tesla", 1): {"name": "Smite", "cd": 35, "do": "stun", "secs": 2,
                   "blurb": "Stops every enemy for 2 seconds."},
    ("beacon", 0): {"name": "Rally", "cd": 60, "do": "rally", "rate": 2, "secs": 8,
                    "blurb": "Every tower fires twice as fast for 8 seconds."},
    ("beacon", 1): {"name": "Mark Them", "cd": 50, "do": "mark", "more": 0.5, "secs": 8,
                    "blurb": "Every enemy takes half again as much damage for 8 seconds."},
    ("brazier", 0): {"name": "Firestorm", "cd": 45, "do": "burn", "dps": 200, "secs": 4,
                     "blurb": "Sets every enemy on the board ablaze."},
    ("brazier", 1): {"name": "Tar Flood", "cd": 45, "do": "slow", "slow": 0.7, "secs": 5, "ground": True,
                     "blurb": "Every enemy on the ground crawls for 5 seconds."},
    ("mortar", 0): {"name": "Meteor Shower", "cd": 45, "do": "strike", "pick": 8, "dmg": 2500, "ground": True,
                    "boss_frac": 0.1, "blurb": "Meteors hit the eight toughest enemies on the ground."},
    ("mortar", 1): {"name": "Carpet of Fire", "cd": 40, "do": "burn", "dps": 120, "secs": 5, "ground": True,
                    "blurb": "Sets every enemy on the ground burning for 5 seconds."},
    ("mint", 0): {"name": "Windfall", "cd": 90, "do": "gold", "gold": 400,
                  "blurb": "400 gold to every player, now."},
    ("mint", 1): {"name": "Bounty Hunt", "cd": 60, "do": "bounty", "more": 2.0, "secs": 10,
                  "blurb": "Kills pay three times as much for 10 seconds."},
    ("bladewheel", 0): {"name": "Blade Storm", "cd": 35, "do": "strike", "pick": "near", "radius": 3.5, "dmg": 2500,
                        "blurb": "Shreds everything within three and a half squares."},
    ("bladewheel", 1): {"name": "Solar Flare", "cd": 45, "do": "burn", "dps": 220, "secs": 4,
                        "blurb": "Sets every enemy on the board ablaze."},
    ("trapper", 0): {"name": "Carpet of Spikes", "cd": 45, "do": "carpet", "piles": 16, "mult": 2,
                     "blurb": "Spreads sixteen piles of double-strength spikes along every road."},
    ("trapper", 1): {"name": "Detonate", "cd": 35, "do": "detonate", "mult": 3,
                     "blurb": "Every mine it laid bursts at once, three times as hard."},
    ("workshop", 0): {"name": "Overclock", "cd": 40, "do": "overdrive", "rate": 3, "secs": 8,
                      "blurb": "Its sentries fire three times as fast for 8 seconds."},
    ("workshop", 1): {"name": "Emergency Build", "cd": 45, "do": "deploy",
                      "blurb": "Builds twice its usual sentries, at once."},
    ("arcanist", 0): {"name": "Inferno Rain", "cd": 45, "do": "burn", "dps": 260, "secs": 4,
                      "blurb": "Fire rains on every enemy on the board."},
    ("arcanist", 1): {"name": "Unmake", "cd": 50, "do": "unmake", "secs": 8,
                      "blurb": "For 8 seconds every enemy loses its immunities and its armour."},
    ("skyhook", 0): {"name": "Skyfall", "cd": 40, "do": "strike", "pick": 6, "dmg": 5000, "boss_frac": 0.15,
                     "blurb": "Harpoons drag down the six toughest enemies on the board."},
    ("skyhook", 1): {"name": "Air Raid", "cd": 40, "do": "strike", "pick": "all", "dmg": 700,
                     "blurb": "Bombs fall on every enemy on the board."},
    ("alchemist", 0): {"name": "Transmute", "cd": 50, "do": "transmute", "pick": 5, "mult": 2,
                       "blurb": "The five toughest enemies (not bosses) turn to gold, paying double."},
    ("alchemist", 1): {"name": "Elixir of Fury", "cd": 55, "do": "rally", "rate": 2, "secs": 10,
                       "blurb": "Every tower fires twice as fast for 10 seconds."},
}
for (_kind, _path), _ability in ABILITIES.items():
    TOWERS[_kind]["paths"][_path]["tiers"][EVOLUTION - 1]["ability"] = _ability


def main_path(tiers, first=None):
    """The path whose tiers count in full: the one with more, or on a tie the one bought first."""
    if not tiers[0] and not tiers[1]:
        return None
    if tiers[0] != tiers[1]:
        return 0 if tiers[0] > tiers[1] else 1
    return first if first in (0, 1) else 0


def stats(kind, tiers=(0, 0), first=None):
    """A tower's numbers with `tiers` bought on each path (see the comment above TOWERS)."""
    out = dict(TOWERS[kind]["base"])
    main = main_path(tiers, first)
    if main is None:
        return out
    paths = TOWERS[kind]["paths"]
    for t in paths[main]["tiers"][:tiers[main]]:
        out.update(t["set"])
    for t in paths[1 - main]["tiers"][:tiers[1 - main]]:
        for k, v in t["cross"].items():
            if v is True:
                out[k] = True
            elif k in CROSS_MUL:
                out[k] = out.get(k, 0) * v
            elif k in CROSS_ADD:
                out[k] = out.get(k, 0) + v
            else:
                out[k] = max(out.get(k, 0), v)
    return out


def can_buy(tiers, path):
    """Whether the next tier on `path` may be bought: at most four a path, and only one past two."""
    nxt = tiers[path] + 1
    return nxt <= EVOLUTION and (nxt <= CROSS_MAX or tiers[1 - path] <= CROSS_MAX)


# Each enemy: health and bounty before the wave's scaling, speed in tiles a second, size (radius in
# tiles, for projectiles), armour taken off every hit (unless `ap`), lives lost if it gets through.
# Special ones:
#   camo     only towers that `detect` (or are revealed by a support tower) can target it
#   immune   damage types that can't hurt it (nor slow, stun or burn it)
#   heal     mends enemies within 1.5 tiles by this share of their health a second (Menders
#            don't add up: an enemy near two is mended by one)
#   children what it bursts into when it dies, [[kind, how many]] (they keep its camouflage)
#   summon   calls up this many Grunts every `every` seconds
#   blimp    one of the big ones: towers' `boss` bonus counts against it, stuns last a third
#   boss     a boss: as blimp, and abilities with `boss_frac` take that share of its health
#   event    a boss event's boss (BOSSES): `skulls` are the shares of health at which it does its
#            `move`; it grows tougher with each boss wave (its tier)
ENEMIES = {
    "grunt": {"name": "Grunt", "hp": 30, "speed": 1.0, "bounty": 5, "size": 0.27},
    "runner": {"name": "Runner", "hp": 17, "speed": 1.9, "bounty": 4, "size": 0.2},
    "swarm": {"name": "Swarmling", "hp": 8, "speed": 1.35, "bounty": 2, "size": 0.15},
    "brute": {"name": "Brute", "hp": 110, "speed": 0.6, "bounty": 8, "size": 0.4, "children": [["grunt", 2]]},
    "shield": {"name": "Shieldbearer", "hp": 60, "speed": 0.8, "bounty": 10, "armor": 5, "size": 0.3},
    "flyer": {"name": "Flyer", "hp": 22, "speed": 1.1, "bounty": 6, "air": True, "size": 0.26},
    "ghost": {"name": "Ghost", "hp": 26, "speed": 1.15, "bounty": 7, "camo": True, "size": 0.25},
    "healer": {"name": "Mender", "hp": 45, "speed": 0.85, "bounty": 12, "heal": 0.02, "size": 0.28},
    "splitter": {"name": "Splitter", "hp": 55, "speed": 0.9, "bounty": 8, "children": [["swarm", 3]], "size": 0.3},
    "gargoyle": {"name": "Gargoyle", "hp": 38, "speed": 0.8, "bounty": 12, "air": True, "armor": 2, "size": 0.3},
    "boss": {"name": "Warlord", "hp": 400, "speed": 0.45, "bounty": 120, "armor": 3, "lives": 5,
             "summon": 1, "every": 12, "boss": True, "size": 0.55},
    "ironclad": {"name": "Ironclad", "hp": 70, "speed": 0.75, "bounty": 8, "armor": 2, "immune": ["sharp"],
                 "children": [["grunt", 2]], "size": 0.32},
    "cinder": {"name": "Cinder", "hp": 30, "speed": 1.25, "bounty": 5, "immune": ["blast"],
               "children": [["swarm", 2]], "size": 0.22},
    "frostborn": {"name": "Frostborn", "hp": 40, "speed": 1.3, "bounty": 6, "immune": ["cold"],
                  "children": [["runner", 2]], "size": 0.25},
    "warded": {"name": "Warded", "hp": 50, "speed": 1.2, "bounty": 8, "immune": ["energy", "fire", "arcane"],
               "children": [["runner", 2]], "size": 0.27},
    "juggernaut": {"name": "Juggernaut", "hp": 550, "speed": 0.38, "bounty": 50, "armor": 3, "lives": 4,
                   "children": [["brute", 4]], "blimp": True, "size": 0.6},
    "colossus": {"name": "Colossus", "hp": 1500, "speed": 0.3, "bounty": 120, "armor": 5, "lives": 10,
                 "children": [["juggernaut", 2]], "blimp": True, "size": 0.75},
    # boss events' bosses
    "gravewarden": {"name": "The Gravewarden", "hp": 450, "speed": 0.42, "bounty": 250, "armor": 2, "lives": 10,
                    "boss": True, "event": True, "size": 0.62, "summon": 2, "every": 8,
                    "skulls": [0.66, 0.33], "move": "raise",
                    "blurb": "Calls up Grunts as it walks. At each skull it turns untouchable for a moment and raises a ring of Ghosts."},
    "stormhulk": {"name": "The Stormhulk", "hp": 480, "speed": 0.4, "bounty": 250, "armor": 3, "lives": 10,
                  "boss": True, "event": True, "size": 0.64, "immune": ["energy"], "zap": 9,
                  "skulls": [0.66, 0.33], "move": "storm",
                  "blurb": "Immune to lightning. Every few seconds it knocks out the best tower near it; at each skull, every tower near it."},
    "ironmaw": {"name": "The Ironmaw", "hp": 420, "speed": 0.36, "bounty": 250, "armor": 5, "lives": 10,
                "boss": True, "event": True, "size": 0.62, "immune": ["sharp"],
                "skulls": [0.66, 0.33], "move": "charge",
                "blurb": "Thick armour, and sharp things bounce off. At each skull it grows a shell and charges."},
}
KINDS = list(ENEMIES)  # snapshots name an enemy's kind by its index here

# Boss events: the host picks who comes on every tenth wave. "warlord" is the classic: Warlords,
# one more each time; the others send one named boss, a tier tougher each time (tier = wave / 10).
BOSSES = {"warlord": "Warlords", "gravewarden": "The Gravewarden", "stormhulk": "The Stormhulk",
          "ironmaw": "The Ironmaw", "random": "A random boss each time"}
BOSS_TIER_HP = 0.5  # each tier past the first adds this much of the boss's health
ZAP_RANGE, ZAP_FOR = 5.0, 3.0  # the Stormhulk knocks a tower out for ZAP_FOR s, within ZAP_RANGE
STORM_RANGE = 4.0  # its skulls knock out every tower this near
RAISE = (3, 2)  # the Gravewarden raises this many Ghosts, plus this many a tier
SHIELD_FOR = 2.5  # seconds a Gravewarden is untouchable after a skull
CHARGE = (0.12, 2.5, 3.0)  # the Ironmaw's shell (share of its health), how much faster it charges, how long


# One-use items, bought from your own purse. `place`: road (a road square), free (a square nothing's
# built on, off the road), any, or none (no aiming). Costs grow with the wave: cost x (1 + wave / 10).
# Damage grows too: x max(1, 0.4 x health(wave)). Each player waits `cd` seconds of fighting before
# using the same item again. `fight`: only while a wave is on.
ITEMS = {
    "caltrops": {"name": "Caltrops", "cost": 40, "cd": 20, "place": "road", "hits": 30, "dmg": 12, "life": 40,
                 "blurb": "A pile of spikes on the road that hurts thirty enemies."},
    "tar": {"name": "Tar Pot", "cost": 50, "cd": 25, "place": "road", "slow": 0.5, "radius": 1.2, "life": 10,
            "blurb": "A pool of tar that slows everything walking through it by half, for 10 seconds."},
    "keg": {"name": "Powder Keg", "cost": 60, "cd": 25, "place": "any", "fight": True, "dmg": 60, "splash": 1.6,
            "blurb": "A big blast wherever you drop it."},
    "hired": {"name": "Hired Bow", "cost": 80, "cd": 30, "place": "free", "life": 45,
              "sentry": {"mode": "shoot", "range": 3.4, "rate": 0.5, "dmg": 20, "pierce": 2, "speed": 14,
                         "dtype": "normal", "air": True, "detect": True},
              "blurb": "A hired archer who fights for 45 seconds, sees Ghosts and hurts anything."},
    "horn": {"name": "War Horn", "cost": 120, "cd": 45, "place": "none", "fight": True, "rate": 1.5, "secs": 8,
             "blurb": "Every tower fires half again as fast for 8 seconds."},
    "flask": {"name": "Frost Flask", "cost": 90, "cd": 45, "place": "none", "fight": True, "secs": 2,
              "blurb": "Freezes every enemy for 2 seconds (bosses and blimps for less)."},
}


def item_cost(kind, wave):
    return round(ITEMS[kind]["cost"] * (1 + max(1, wave) / 10))


def item_power(wave):
    return max(1.0, 0.4 * health(max(1, wave)))


# Endless (past WAVES): health also compounds by ENDLESS_GROWTH a wave and enemies walk faster, by
# ENDLESS_SPEED a wave up to ENDLESS_SPEED_MAX, while bounties keep growing only slowly, so income
# falls behind and every defence falls in the end. Without this the polynomial alone let the test
# builders sit at wave 70 and beyond with every evolution built and thousands of gold unspent.
ENDLESS_GROWTH = 1.2
ENDLESS_SPEED, ENDLESS_SPEED_MAX = 0.015, 1.5
STUN_GUARD = 1.0  # after a tower's stun wears off, an enemy shrugs off towers' stuns for this long


def health(wave):
    """How much tougher enemies are in a wave than in the first."""
    w = wave - 1
    return (1 + 0.45 * w + 0.06 * w * w) * ENDLESS_GROWTH ** max(0, wave - WAVES)


def pace(wave):
    """How much faster enemies walk than usual (only in endless)."""
    return min(ENDLESS_SPEED_MAX, 1 + ENDLESS_SPEED * max(0, wave - WAVES))


def bounty(wave):
    return 1 + 0.03 * (wave - 1)


def wave(w):
    """A wave as groups: (kind, how many, seconds between them, seconds before the first). Past
    wave 30 (endless) the same recipe carries on, with everything mixed in. "boss" is whoever the
    room's boss event sends (a Warlord unless the host picked another)."""
    n = lambda base: round(base * (1 + w / 14))  # noqa: E731
    return _base_wave(w, n) + _extras(w, n)


def _extras(w, n):
    """The newer enemies, worked into the cycle once the basics are learnt."""
    c = w % 5
    late = w > 30
    out = []
    if w >= 7 and (c == 2 or late):
        out.append(("ghost", n(4), 0.8, 2))
    if w >= 8 and (c == 3 or late):
        out.append(("ironclad", n(2), 1.4, 3))
    if w >= 9 and (c == 1 or late):
        out.append(("splitter", n(3), 1.4, 2))
    if w >= 11 and (c == 2 or late):
        out.append(("cinder", n(3), 0.6, 4))
    if w >= 12 and (c == 1 or late):
        out.append(("healer", n(1), 2.5, 4))
    if w >= 13 and (c == 4 or late):
        out.append(("frostborn", n(3), 0.7, 2))
    if w >= 15 and ((c == 0 and w % 10) or (c == 3 and w > 20) or late):
        out.append(("warded", n(3), 0.8, 3))
    if w >= 18 and (c == 4 or late):
        out.append(("gargoyle", max(1, w // 12), 1.5, 3))
    if w >= 22 and (c == 2 or (late and w % 3 == 0)):
        out.append(("juggernaut", 1 + max(0, (w - 27) // 6), 6.0, 6))
    if w >= 29 and (c == 4 or (late and w % 5 == 4)):
        out.append(("colossus", 1 + max(0, (w - 30) // 15), 10.0, 8))
    return out


def _base_wave(w, n):
    if w % 10 == 0:
        return [("boss", w // 10, 5.0, 0), ("grunt", n(8), 0.7, 2)]
    c = w % 5
    if c == 1:
        return [("grunt", n(10), 0.8, 0)]
    if c == 2:
        return [("runner", n(9), 0.5, 0)] + ([("grunt", n(5), 0.9, 3)] if w > 5 else [])
    if c == 3:
        return [("swarm", n(22), 0.22, 0)] + ([("shield", n(3), 1.6, 2)] if w > 6 else [])
    if c == 4:
        return ([("flyer", n(5), 0.8, 0)] if w >= 4 else []) + [("shield" if w > 8 else "grunt", n(6), 1.0, 1)]
    return [("brute", n(4), 1.8, 0), ("runner", n(6), 0.5, 4)]


# Maps: each path is the corners an enemy walks between, as tile (column, row); it starts off the
# board and ends on the keep. Nothing can be built on a path or a rock; a map with `build` can be
# built on only there.
MAPS = {
    "meadow": {"name": "Meadow", "blurb": "One long, winding road. The gentle one.",
               "paths": [[(-1, 2), (4, 2), (4, 8), (9, 8), (9, 3), (14, 3), (14, 9), (19, 9)]],
               "rocks": [(1, 6), (7, 1), (11, 10), (17, 4), (6, 5), (12, 6)]},
    "crossing": {"name": "Crossing", "blurb": "Two roads that meet in the middle. The hard one.",
                 "paths": [[(-1, 1), (6, 1), (6, 6), (13, 6), (13, 10), (19, 10)],
                           [(-1, 10), (6, 10), (6, 6), (13, 6), (13, 10), (19, 10)]],
                 "rocks": [(3, 5), (9, 3), (10, 9), (16, 7), (2, 7), (16, 3)]},
    "coil": {"name": "Coil", "blurb": "A long spiral in to the keep.",
             "paths": [[(-1, 1), (17, 1), (17, 10), (2, 10), (2, 4), (13, 4), (13, 7), (7, 7)]],
             "rocks": [(0, 6), (19, 5), (9, 11), (5, 2), (15, 6), (10, 9)]},
    "knot": {"name": "Knot", "blurb": "A road that crosses itself: towers at the crossing see everything twice. A hard one.",
             "paths": [[(-1, 3), (14, 3), (14, 9), (8, 9), (8, 1), (17, 1), (17, 10), (19, 10)]],
             "rocks": [(2, 7), (11, 6), (4, 10), (19, 4), (12, 11), (3, 0)]},
    "quarry": {"name": "Quarry", "blurb": "Rubble everywhere: only a few patches of cleared ground to build on.",
               "paths": [[(-1, 6), (5, 6), (5, 2), (12, 2), (12, 9), (19, 9)]],
               "rocks": [],
               "build": [(3, 4), (4, 4), (3, 5), (4, 7), (6, 4), (6, 5), (7, 3), (8, 3), (7, 1), (9, 1),
                         (10, 3), (11, 3), (11, 4), (13, 1), (13, 3), (10, 6), (11, 6), (13, 6), (10, 8),
                         (11, 8), (13, 8), (14, 8), (15, 10), (17, 8), (16, 10), (1, 5), (2, 7)]},
}


def buildable(m):
    """The tiles a map can be built on."""
    road = path_tiles(m)
    if "build" in m:
        return {tuple(t) for t in m["build"]} - road
    return {(x, y) for x in range(COLS) for y in range(ROWS)} - road - {tuple(r) for r in m["rocks"]}


def path_tiles(m):
    tiles = set()
    for path in m["paths"]:
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            for i in range(abs(x1 - x0) + abs(y1 - y0) + 1):
                x = x0 + (x1 > x0) * i - (x1 < x0) * i
                y = y0 + (y1 > y0) * i - (y1 < y0) * i
                if 0 <= x < COLS and 0 <= y < ROWS:
                    tiles.add((x, y))
    return tiles
