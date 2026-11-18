"""Holdfast's numbers: the towers, the enemies, the waves and the maps.

Distances are in tiles (the board is COLS x ROWS of them), times in seconds. The browser gets
TOWERS, ENEMIES and the chosen map as they are here, so its panels never disagree with the rules.
`tools/holdfast-sim.py` plays whole games with a simple builder to show how the numbers land.
"""

COLS, ROWS = 20, 12
LIVES = 20
WAVES = 30
START_GOLD = (130, 60)  # shared out between the players, plus this much each
SELL_BACK = 0.7
BUILD_TIME = (25, 12)  # seconds before the first wave, and between waves
DIFFICULTY = {"easy": 0.75, "normal": 1.0, "hard": 1.15}  # enemy health

# Each tower has its base numbers and two upgrade paths of four tiers. The first upgrade picks a
# path for good; tier four is the path's final evolution, which renames the tower, and only one of
# each final evolution can stand on the map at a time. A tier's `set` replaces numbers, in order.
#
# Numbers a tower can have (distances in tiles, times in seconds):
#   mode     shoot (one target per shot), splash (a blast where it lands), aura (everything in
#            reach), chain (lightning that jumps), support (beacons) or income (mints)
#   range    reach (mortars reach the whole board)   rate    seconds between shots
#   dmg      damage a hit                           shots   targets a volley (shoot, splash)
#   air      can it hit flyers?                     pierce  ignores armour
#   splash   blast radius                           cluster extra small blasts around each blast
#   slow     how much it slows (0.4: 40% slower), for `hold` s
#   stun     seconds a hit stops an enemy dead (bosses: a third as long)
#   burn     damage a second it sets burning, for `burn_for` s (burning ignores armour)
#   shred    armour a hit strips off for good      brittle  slowed enemies take this much more damage
#   boss     damage to Warlords is multiplied by this
#   chain    enemies a bolt jumps to
#   boost / reach / power   (beacons) nearby towers fire faster / reach further / hit harder; the
#            best beacon in reach counts for each, not the sum
#   income   (mints) gold to the builder at the end of every wave
#   bounty   (mints) kills in its reach pay everyone this much more
#   detect   can it see Ghosts (camouflaged)? Auras always can; a lightning chain can jump to one
#   reveal   (beacons) towers in its reach can see Ghosts too
#
# Each final evolution also has an `ability` (ABILITIES, below): a power anyone may trigger, on a
# cooldown that only runs while a wave is being fought.


def tier(name, cost, blurb, **set_):
    return {"name": name, "cost": cost, "blurb": blurb, "set": set_}


TOWERS = {
    "archer": {
        "name": "Archer", "cost": 50, "blurb": "Cheap and quick. Hits flyers.",
        "base": {"mode": "shoot", "range": 3.2, "rate": 0.6, "dmg": 10, "air": True},
        "paths": [
            {"name": "Marksman", "tiers": [
                tier("Sharp Arrows", 60, "Hits much harder.", dmg=22),
                tier("Longbow", 120, "Reaches further, hits harder, and spots Ghosts.", range=4.3, dmg=46, detect=True),
                tier("Bodkin Points", 260, "Arrows punch through armour.", dmg=106, pierce=True),
                tier("Eagle Eye", 1500, "Final evolution: a sharpshooter who sees the whole road and fells Warlords.",
                     range=9, dmg=565, rate=0.45, boss=2),
            ]},
            {"name": "Volley", "tiers": [
                tier("Quick Draw", 70, "Shoots faster.", rate=0.42, dmg=17),
                tier("Twin Shot", 150, "Two arrows a shot, at two enemies.", shots=2, dmg=19),
                tier("Triple Shot", 300, "Three arrows, faster still.", shots=3, rate=0.34, dmg=23),
                tier("Storm of Arrows", 1400, "Final evolution: eight arrows, five times a second.",
                     shots=8, rate=0.2, dmg=30, range=3.8),
            ]},
        ],
    },
    "cannon": {
        "name": "Cannon", "cost": 90, "blurb": "Blasts a crowd. Can't aim at flyers.",
        "base": {"mode": "splash", "range": 2.8, "rate": 1.4, "dmg": 22, "splash": 1.1, "air": False},
        "paths": [
            {"name": "Heavy", "tiers": [
                tier("Bigger Bombs", 100, "Harder hits, wider blasts.", dmg=46, splash=1.3),
                tier("Heavy Shells", 200, "Much harder hits.", dmg=95),
                tier("Shatter Shells", 380, "Each blast strips armour for good.", dmg=203, shred=2),
                tier("Doomsday Gun", 2200, "Final evolution: one enormous shell that flattens everything.",
                     dmg=1650, splash=2.3, rate=1.7, range=3.4, boss=1.5),
            ]},
            {"name": "Rapid", "tiers": [
                tier("Fast Loader", 110, "Fires faster.", rate=1.0, dmg=35),
                tier("Cluster Bombs", 220, "Each shell scatters three more small blasts.", cluster=3),
                tier("Concussion", 400, "Blasts stun what they hit.", stun=0.35, dmg=70),
                tier("Carpet Bomber", 2100, "Final evolution: a rain of clustered, stunning shells.",
                     rate=0.35, cluster=6, stun=0.45, dmg=96),
            ]},
        ],
    },
    "frost": {
        "name": "Frost", "cost": 70, "blurb": "Slows everything near it.",
        "base": {"mode": "aura", "range": 2.3, "rate": 1.0, "dmg": 2, "slow": 0.35, "hold": 1.5, "air": True},
        "paths": [
            {"name": "Deep Freeze", "tiers": [
                tier("Colder", 80, "Slows harder.", slow=0.45),
                tier("Wide Chill", 150, "Reaches further.", range=3.0),
                tier("Brittle Ice", 300, "Slowed enemies take a quarter more damage from everything.", brittle=0.25),
                tier("Absolute Zero", 1700, "Final evolution: the whole field crawls, and shatters.",
                     slow=0.7, range=4.6, brittle=0.5, dmg=10),
            ]},
            {"name": "Ice Shards", "tiers": [
                tier("Shards", 90, "Each pulse cuts.", dmg=9),
                tier("Flash Freeze", 200, "Pulses freeze enemies solid for a moment.", stun=0.3, dmg=10),
                tier("Shard Storm", 380, "Pulses cut deep.", dmg=28, rate=0.8),
                tier("Blizzard", 1800, "Final evolution: a storm of ice that freezes and shreds.",
                     dmg=73, rate=0.55, stun=0.55, range=3.2),
            ]},
        ],
    },
    "ballista": {
        "name": "Ballista", "cost": 120, "blurb": "Slow, far-reaching, and goes straight through armour.",
        "base": {"mode": "shoot", "range": 6.0, "rate": 2.2, "dmg": 75, "air": True, "pierce": True},
        "paths": [
            {"name": "Siege", "tiers": [
                tier("Heavy Bolts", 130, "Hits much harder, and spots Ghosts.", dmg=156, detect=True),
                tier("Steel Bolts", 260, "Hits harder still.", dmg=319),
                tier("Giant Slayer", 480, "Triple damage to Warlords.", dmg=668, boss=3),
                tier("Kingslayer", 2400, "Final evolution: one bolt fit to end a Warlord.",
                     dmg=4190, boss=4, rate=2.4, range=8),
            ]},
            {"name": "Repeater", "tiers": [
                tier("Winch", 140, "Reloads faster.", rate=1.6, dmg=118),
                tier("Double Crank", 280, "Reloads much faster.", rate=1.1, dmg=169),
                tier("Twin Bolts", 500, "Two bolts a shot.", shots=2, dmg=176),
                tier("Gatling Ballista", 2100, "Final evolution: bolts as fast as it can crank.",
                     rate=0.25, dmg=201, shots=2),
            ]},
        ],
    },
    "tesla": {
        "name": "Tesla", "cost": 140, "blurb": "Lightning that jumps from enemy to enemy.",
        "base": {"mode": "chain", "range": 2.6, "rate": 0.8, "dmg": 15, "chain": 3, "air": True},
        "paths": [
            {"name": "Arc", "tiers": [
                tier("Longer Arcs", 150, "Jumps to more enemies.", chain=5, dmg=21),
                tier("High Voltage", 280, "Hits harder.", dmg=41),
                tier("Arc Web", 500, "Jumps much further down the line.", chain=9, dmg=50),
                tier("Storm Spire", 2100, "Final evolution: lightning through the whole wave.",
                     chain=24, dmg=75, range=4.2, rate=0.5),
            ]},
            {"name": "Overload", "tiers": [
                tier("Jolt", 150, "Each hit stuns.", stun=0.2, dmg=31),
                tier("Capacitor", 300, "Strikes faster.", rate=0.55, dmg=43),
                tier("Overcharge", 520, "Harder, longer stuns.", dmg=88, stun=0.35),
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
                tier("Drums", 120, "Towers beside it fire faster still.", boost=0.3),
                tier("Tall Pole", 200, "Reaches further.", range=2.3),
                tier("Battle Hymn", 380, "Much faster firing.", boost=0.45),
                tier("War Banner", 1800, "Final evolution: towers near it fire far faster and hit harder.",
                     boost=0.8, range=3.2, power=0.5),
            ]},
            {"name": "Watch", "tiers": [
                tier("Spyglass", 120, "Towers beside it reach further and can see Ghosts.", reach=0.15, reveal=True),
                tier("Lookout", 220, "Reaches further, and so do they.", reach=0.25, range=2.0),
                tier("Sharpening Stone", 400, "Towers beside it hit harder.", power=0.25),
                tier("Lighthouse", 1700, "Final evolution: lights up the field for every tower near it.",
                     reach=0.5, range=3.5, power=0.35, boost=0.3),
            ]},
        ],
    },
    "brazier": {
        "name": "Brazier", "cost": 100, "blurb": "Sets everything near it burning. Burning ignores armour.",
        "base": {"mode": "aura", "range": 2.0, "rate": 0.5, "dmg": 5, "burn": 16, "burn_for": 2.0, "air": False},
        "paths": [
            {"name": "Inferno", "tiers": [
                tier("Hotter Coals", 110, "Burns harder.", burn=35, dmg=7.4),
                tier("Bellows", 210, "Reaches further.", range=2.4, dmg=25),
                tier("White Heat", 400, "Burns much harder and longer.", burn=72, burn_for=3.0, dmg=58),
                tier("Dragon's Breath", 2000, "Final evolution: a firestorm that reaches flyers too.",
                     burn=256, range=3.4, dmg=277, air=True),
            ]},
            {"name": "Pitch", "tiers": [
                tier("Pitch", 110, "Sticky fire slows what it touches.", slow=0.2, hold=1.0, dmg=15),
                tier("Melt", 230, "Fire strips armour for good.", shred=1, dmg=44),
                tier("Tar Pit", 420, "Slows harder, burns harder.", slow=0.35, burn=48, dmg=86),
                tier("Hellfire", 1800, "Final evolution: tar that holds and burns everything in it.",
                     slow=0.55, burn=176, dmg=404, range=2.8, shred=2),
            ]},
        ],
    },
    "mortar": {
        "name": "Mortar", "cost": 130, "blurb": "Shells anywhere on the board. Slow, and can't hit flyers.",
        "base": {"mode": "splash", "range": 30, "rate": 3.0, "dmg": 40, "splash": 1.3, "air": False},
        "paths": [
            {"name": "Big Shells", "tiers": [
                tier("Heavy Charge", 140, "Hits harder.", dmg=83),
                tier("Wide Shells", 260, "Bigger blasts.", splash=1.8, dmg=163),
                tier("Siege Shells", 460, "Hits much harder.", dmg=329),
                tier("Meteor", 2200, "Final evolution: shells like falling stars.",
                     dmg=2106, splash=2.7, rate=3.5, boss=1.5),
            ]},
            {"name": "Barrage", "tiers": [
                tier("Quick Crew", 140, "Fires faster.", rate=2.2, dmg=61),
                tier("Twin Tubes", 280, "Two shells at once.", shots=2),
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
                tier("Bigger Vault", 160, "Pays more.", income=45),
                tier("Counting House", 300, "Pays more still.", income=70),
                tier("Bank", 520, "Pays a lot.", income=105),
                tier("Royal Mint", 2100, "Final evolution: a river of gold.", income=360),
            ]},
            {"name": "Bounty", "tiers": [
                tier("Bounty Board", 160, "Kills in its reach pay everyone 15% more.", bounty=0.15),
                tier("Reward Posters", 300, "Kills near it pay 30% more, and it reaches further.", bounty=0.3, range=2.6),
                tier("Guild Hall", 520, "Kills near it pay 45% more.", bounty=0.45, income=35),
                tier("Tax Office", 2000, "Final evolution: everything that dies near it pays double.",
                     bounty=1.0, range=4.0, income=60),
            ]},
        ],
    },
}
EVOLUTION = 4  # the tier that's a final evolution

# Final evolutions' abilities, by (tower, path). `do` is what it does (Room.ability):
#   strike   `dmg` to enemies: the `pick` strongest (by health), "all" of them, or every enemy within
#            `radius` of the one nearest the keep ("lead"); `ground` only if set. Warlords take
#            `boss_frac` of their health instead, if that's given.
#   stun / slow / burn   every enemy (`ground` only if set) for `secs`; slows by `slow`, burns `dps`
#   overdrive  this tower fires `rate`x as fast for `secs`
#   rally      every tower fires `rate`x as fast for `secs`
#   mark       every enemy takes `more` extra damage for `secs`
#   gold       `gold` to each player now
#   bounty     kills pay `more` extra for `secs`
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
                      "blurb": "Kills the toughest enemy outright (takes 30% off a Warlord)."},
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
}
for (_kind, _path), _ability in ABILITIES.items():
    TOWERS[_kind]["paths"][_path]["tiers"][EVOLUTION - 1]["ability"] = _ability


def stats(kind, path=None, tiers=0):
    """A tower's numbers with `tiers` bought on `path`."""
    out = dict(TOWERS[kind]["base"])
    if path is not None:
        for t in TOWERS[kind]["paths"][path]["tiers"][:tiers]:
            out.update(t["set"])
    return out


# Each enemy: health and bounty before the wave's scaling, speed in tiles a second, armour taken off
# every hit (ballistas ignore it), lives lost if it gets through. Special ones:
#   camo     only towers that `detect` (or are revealed by a beacon) can target it
#   heal     mends enemies within 1.5 tiles by this share of their health a second (Menders
#            don't add up: an enemy near two is mended by one)
#   split    breaks into this many Swarmlings when it dies
#   summon   (Warlords) calls up this many Grunts every `every` seconds
ENEMIES = {
    "grunt": {"name": "Grunt", "hp": 30, "speed": 1.0, "bounty": 5},
    "runner": {"name": "Runner", "hp": 17, "speed": 1.9, "bounty": 4},
    "swarm": {"name": "Swarmling", "hp": 8, "speed": 1.35, "bounty": 2},
    "brute": {"name": "Brute", "hp": 150, "speed": 0.6, "bounty": 16},
    "shield": {"name": "Shieldbearer", "hp": 60, "speed": 0.8, "bounty": 10, "armor": 5},
    "flyer": {"name": "Flyer", "hp": 22, "speed": 1.1, "bounty": 6, "air": True},
    "ghost": {"name": "Ghost", "hp": 26, "speed": 1.15, "bounty": 7, "camo": True},
    "healer": {"name": "Mender", "hp": 45, "speed": 0.85, "bounty": 12, "heal": 0.02},
    "splitter": {"name": "Splitter", "hp": 55, "speed": 0.9, "bounty": 8, "split": 3},
    "gargoyle": {"name": "Gargoyle", "hp": 38, "speed": 0.8, "bounty": 12, "air": True, "armor": 2},
    "boss": {"name": "Warlord", "hp": 400, "speed": 0.45, "bounty": 120, "armor": 3, "lives": 5,
             "summon": 1, "every": 12},
}
KINDS = list(ENEMIES)  # snapshots name an enemy's kind by its index here


def health(wave):
    """How much tougher enemies are in a wave than in the first."""
    w = wave - 1
    return 1 + 0.45 * w + 0.06 * w * w


def bounty(wave):
    return 1 + 0.03 * (wave - 1)


def wave(w):
    """A wave as groups: (kind, how many, seconds between them, seconds before the first). Past
    wave 30 (endless) the same recipe carries on, with everything mixed in."""
    n = lambda base: round(base * (1 + w / 14))  # noqa: E731
    return _base_wave(w, n) + _extras(w, n)


def _extras(w, n):
    """The newer enemies, worked into the cycle once the basics are learnt."""
    c = w % 5
    out = []
    if w >= 7 and (c == 2 or w > 30):
        out.append(("ghost", n(4), 0.8, 2))
    if w >= 9 and (c == 1 or w > 30):
        out.append(("splitter", n(3), 1.4, 2))
    if w >= 12 and (c == 1 or w > 30):
        out.append(("healer", n(1), 2.5, 4))
    if w >= 18 and (c == 4 or w > 30):
        out.append(("gargoyle", max(1, w // 12), 1.5, 3))
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
