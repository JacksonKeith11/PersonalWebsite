"""Overlords' units, traits and their numbers, as data.

A unit has stats at one star (hp and ad grow by STAR_MULT at two and three stars), one origin and
one or two classes, and an ability: what it does when its mana fills, as a list of steps that
`sim.py` runs in order. A step is a dict with `do` (what), `to` (who: a selector) and numbers that
are either one value or a list of three, one per star. See sim.Fight.step_* and sim.Fight.select.

Steps:
    hit     damage `dmg` of `type` (magic by default, also phys and true); optional `stun` (seconds),
            `slow` (fraction of attack speed lost for 3 s), `burn` (fraction of the target's max
            hp per second for 3 s) and `heal_frac` (the caster heals that share of the damage done)
    heal    heal `amt`
    shield  a shield of `amt` for `secs`
    buff    `stat` (aspd_pct, ad, armor, mr, dodge) up by `amt` for `secs`
    summon  `count` (default 1) of `unit` (a key in UNITS with "summon": True) at the caster's star,
            next to the caster; a unit with "static": True never moves
    dash    jump next to the unit `to` picks (farthest, lowest_enemy...) and make it the target
    mana    give other allies `amt` mana
Selectors: target, self, around_target:R, around_self:R, line:L, nearest:N, farthest, random:N,
chain:N, lowest_enemy (the most hurt), lowest_ally, allies_near:R, allies, enemies. Ability damage and healing scale with ap
(100 = as written).

A trait counts the different units carrying it on a board (two copies of one unit count once).
At each threshold in `levels` the matching entry of `fx` applies, to the trait's own units
("who": "members") or to the whole board ("team"). Plain stats: hp_pct, ad_pct, aspd_pct, armor,
mr, ap, dodge, crit, critdmg, mana_cut. Special effects, run by sim.py: burn, regen, mana_regen,
revive, chill, shield, duel, double, leap, summon_boost.
"""

STAR_MULT = (1.0, 1.8, 3.24)  # hp and ad at one, two and three stars
COSTS = (1, 2, 3, 4, 5)

# ------------------------------------------------------------------ the match
START_HP = 60
BENCH = 8
SHOP_SIZE = 5
REROLL = 2
XP_COST, XP_GAIN = 4, 4
PASSIVE_XP = 2  # every round after the first
MAX_LEVEL = 8
LEVEL_XP = {1: 2, 2: 2, 3: 6, 4: 10, 5: 20, 6: 32, 7: 50}  # XP from each level to the next
# Chance (%) of each cost in a shop slot, by level.
SHOP_ODDS = {1: (100, 0, 0, 0, 0), 2: (100, 0, 0, 0, 0), 3: (75, 25, 0, 0, 0), 4: (55, 30, 15, 0, 0),
             5: (45, 33, 20, 2, 0), 6: (30, 40, 25, 5, 0), 7: (19, 30, 35, 15, 1), 8: (15, 20, 35, 25, 5)}
POOL = {1: 12, 2: 10, 3: 9, 4: 7, 5: 5}  # copies of each unit in a room, by cost
INTEREST_PER, MAX_INTEREST = 10, 5
PLAN_TIME, FIRST_PLAN = 30, 20
RESULT_PAUSE = 3.0  # seconds after the last fight ends before the next round
START_LEVEL = 1


def income(rnd):
    return 3 if rnd == 1 else 4 if rnd == 2 else 5


def streak_gold(streak):
    n = abs(streak)
    return 0 if n < 2 else 1 if n < 4 else 2 if n < 5 else 3


def loss_damage(rnd, survivors):
    """HP a player loses to a board that beat them: a base for the round, one for each star left
    standing, and from round 16 three more every round, so the match ends on time."""
    return 1 + rnd // 3 + 3 * max(0, rnd - 15) + sum(star for _, star in survivors)


# Monster rounds: what each player fights, in the monsters' own coordinates, and the gold for beating it.
PVE = {
    1: [("wolf", 1, 2, 3), ("wolf", 1, 4, 3)],
    2: [("wolf", 1, 1, 3), ("wolf", 1, 3, 3), ("wolf", 1, 5, 3)],
    6: [("bandit", 1, 2, 3), ("bandit", 1, 4, 3), ("bandit", 1, 3, 2), ("bandit_chief", 1, 3, 1)],
    11: [("stone_golem", 1, 2, 3), ("stone_golem", 1, 4, 3), ("bandit_chief", 2, 3, 1)],
}
PVE_GOLD = {1: 2, 2: 2, 6: 3, 11: 4}

TRAITS = {
    # ---------------------------------------------------------------- origins
    "emberforged": {
        "name": "Emberforged", "kind": "origin", "levels": [2, 4, 6],
        "text": "Emberforged attacks set the target burning, for a share of its max HP each second for 3 s.",
        "fx": [{"burn": 0.015}, {"burn": 0.03}, {"burn": 0.04}]},
    "thornwood": {
        "name": "Thornwood", "kind": "origin", "levels": [2, 4, 6],
        "text": "Thornwood units regrow a share of their max HP every second.",
        "fx": [{"regen": 0.01}, {"regen": 0.025}, {"regen": 0.04}]},
    "tidecallers": {
        "name": "Tidecallers", "kind": "origin", "levels": [2, 4],
        "text": "Tidecallers gain mana every second; at 4, so does the whole board.",
        "fx": [{"mana_regen": 5}, {"who": "team", "mana_regen": 6}]},
    "gravebound": {
        "name": "Gravebound", "kind": "origin", "levels": [2, 4, 6],
        "text": "The first time a Gravebound unit dies, it rises again with part of its HP.",
        "fx": [{"revive": 0.25}, {"revive": 0.45}, {"revive": 0.6}]},
    "skyborne": {
        "name": "Skyborne", "kind": "origin", "levels": [2, 4],
        "text": "Skyborne units dodge some attacks and attack faster.",
        "fx": [{"dodge": 0.25, "aspd_pct": 0.1}, {"dodge": 0.45, "aspd_pct": 0.25}]},
    "ironhold": {
        "name": "Ironhold", "kind": "origin", "levels": [2, 4, 6],
        "text": "Ironhold units gain armor and magic resist.",
        "fx": [{"armor": 25, "mr": 25}, {"armor": 50, "mr": 50}, {"armor": 75, "mr": 75}]},
    "starlit": {
        "name": "Starlit", "kind": "origin", "levels": [2, 4],
        "text": "Starlit abilities need less mana.",
        "fx": [{"mana_cut": 0.2}, {"mana_cut": 0.4}]},
    "mirefolk": {
        "name": "Mirefolk", "kind": "origin", "levels": [2, 4],
        "text": "Whoever attacks a Mirefolk unit is chilled, attacking slower for 2 s.",
        "fx": [{"chill": 0.2}, {"chill": 0.4}]},
    # ---------------------------------------------------------------- classes
    "vanguard": {
        "name": "Vanguard", "kind": "class", "levels": [2, 4, 6],
        "text": "Vanguards start the fight with a shield for 10 s.",
        "fx": [{"shield": 150}, {"shield": 400}, {"shield": 750}]},
    "duelist": {
        "name": "Duelist", "kind": "class", "levels": [2, 4, 6],
        "text": "Each Duelist attack speeds up their attacks, stacking up to 8 times.",
        "fx": [{"duel": 0.06}, {"duel": 0.1}, {"duel": 0.12}]},
    "ranger": {
        "name": "Ranger", "kind": "class", "levels": [2, 4],
        "text": "Ranger attacks have a chance to strike twice.",
        "fx": [{"double": 0.25}, {"double": 0.5}]},
    "arcanist": {
        "name": "Arcanist", "kind": "class", "levels": [2, 4, 6],
        "text": "The whole board's abilities hit harder and heal more.",
        "fx": [{"who": "team", "ap": 20}, {"who": "team", "ap": 45}, {"who": "team", "ap": 90}]},
    "mystic": {
        "name": "Mystic", "kind": "class", "levels": [2, 4],
        "text": "The whole board gains magic resist and regrows a little HP every second.",
        "fx": [{"who": "team", "mr": 30, "regen": 0.008}, {"who": "team", "mr": 60, "regen": 0.018}]},
    "assassin": {
        "name": "Assassin", "kind": "class", "levels": [2, 4, 6],
        "text": "Assassins leap to the enemy's back line at the start, and crit more often and harder.",
        "fx": [{"leap": 1, "crit": 0.2, "critdmg": 0.3}, {"leap": 1, "crit": 0.3, "critdmg": 0.4},
               {"leap": 1, "crit": 0.45, "critdmg": 0.6}]},
    "summoner": {
        "name": "Summoner", "kind": "class", "levels": [2, 4],
        "text": "What Summoners call up has more HP and damage.",
        "fx": [{"summon_boost": 0.3}, {"summon_boost": 0.7}]},
    "warden": {
        "name": "Warden", "kind": "class", "levels": [2, 4, 6],
        "text": "Wardens gain max HP.",
        "fx": [{"hp_pct": 0.25}, {"hp_pct": 0.5}, {"hp_pct": 0.9}]},
}


def U(name, cost, traits, hp, ad, aspd, rng, armor, mr, mana, start, ability, **extra):
    unit = {"name": name, "cost": cost, "traits": traits, "hp": hp, "ad": ad, "as": aspd, "range": rng,
            "armor": armor, "mr": mr, "mana": mana, "start": start, "ability": ability}
    unit.update(extra)
    return unit


def A(name, text, *steps):
    return {"name": name, "text": text, "steps": list(steps)}


UNITS = {
    # ---------------------------------------------------------------- cost 1
    "ashling": U("Ashling", 1, ["emberforged", "duelist"], 640, 68, 0.75, 1, 30, 20, 60, 0,
                 A("Flurry", "Attacks far faster for 4 s.",
                   {"do": "buff", "to": "self", "stat": "aspd_pct", "amt": [0.8, 1.0, 1.3], "secs": 4})),
    "bramble_guard": U("Bramble Guard", 1, ["thornwood", "vanguard"], 700, 61, 0.6, 1, 45, 30, 80, 30,
                       A("Barkskin", "Shields itself for 4 s.",
                         {"do": "shield", "to": "self", "amt": [300, 450, 700], "secs": 4})),
    "tide_acolyte": U("Tide Acolyte", 1, ["tidecallers", "mystic"], 500, 54, 0.65, 3, 20, 20, 70, 20,
                      A("Rising Water", "Heals the most hurt ally.",
                        {"do": "heal", "to": "lowest_ally", "amt": [250, 375, 550]})),
    # ---------------------------------------------------------------- cost 2
    "grave_archer": U("Grave Archer", 2, ["gravebound", "ranger"], 550, 74, 0.75, 4, 20, 20, 70, 0,
                      A("Bone Volley", "Looses bone arrows at three random enemies.",
                        {"do": "hit", "to": "random:3", "type": "phys", "dmg": [160, 240, 360]})),
    "iron_sentinel": U("Iron Sentinel", 2, ["ironhold", "warden"], 750, 68, 0.6, 1, 45, 30, 90, 40,
                       A("Shield Slam", "Slams its target, stunning it.",
                         {"do": "hit", "to": "target", "dmg": [160, 240, 360], "stun": [1.5, 1.75, 2]})),
    "mire_witch": U("Mire Witch", 2, ["mirefolk", "arcanist"], 550, 54, 0.65, 3, 20, 25, 80, 20,
                    A("Bog", "Floods the ground round its target, hurting and slowing everyone there.",
                      {"do": "hit", "to": "around_target:1", "dmg": [200, 300, 450], "slow": 0.3})),
    # ---------------------------------------------------------------- cost 3
    "sky_lancer": U("Sky Lancer", 3, ["skyborne", "duelist"], 820, 88, 0.75, 1, 35, 25, 70, 0,
                    A("Dive", "Dives at the farthest enemy and runs it through.",
                      {"do": "dash", "to": "farthest"},
                      {"do": "hit", "to": "target", "type": "phys", "dmg": [340, 510, 800]})),
    "ember_mage": U("Ember Mage", 3, ["emberforged", "arcanist"], 650, 61, 0.7, 4, 25, 25, 80, 20,
                    A("Fireball", "A fireball that bursts round its target and leaves it burning.",
                      {"do": "hit", "to": "around_target:1", "dmg": [280, 420, 680], "burn": 0.03})),
    "starlit_blade": U("Starlit Blade", 3, ["starlit", "assassin"], 650, 94, 0.8, 1, 25, 20, 60, 0,
                       A("Shadow Cut", "A cut that ignores armor.",
                         {"do": "hit", "to": "target", "type": "true", "dmg": [300, 450, 750]})),
    # ---------------------------------------------------------------- cost 4
    "thorn_shaman": U("Thorn Shaman", 4, ["thornwood", "summoner"], 800, 74, 0.7, 3, 30, 30, 90, 40,
                      A("Call the Grove", "Calls up a Treant beside itself.",
                        {"do": "summon", "unit": "treant"})),
    "grave_knight": U("Grave Knight", 4, ["gravebound", "vanguard", "warden"], 1000, 94, 0.65, 1, 50, 40, 100, 40,
                      A("Reaping Swing", "Swings round itself, healing for each enemy hit.",
                        {"do": "hit", "to": "around_self:1", "dmg": [250, 375, 1000]},
                        {"do": "heal", "to": "self", "amt": [250, 375, 1000]})),
    "storm_herald": U("Storm Herald", 4, ["skyborne", "mystic"], 850, 72, 0.7, 3, 25, 40, 80, 20,
                      A("Chain Lightning", "Lightning that leaps through five enemies.",
                        {"do": "hit", "to": "chain:5", "dmg": [330, 500, 1250]})),
    # ---------------------------------------------------------------- cost 5
    "deep_priest": U("Deep Priest", 5, ["tidecallers", "summoner", "arcanist"], 950, 74, 0.7, 4, 30, 40, 100, 40,
                     A("Tidal Wave", "A wave crashes down round its target, stunning everything it hits.",
                       {"do": "hit", "to": "around_target:2", "dmg": [400, 600, 2500], "stun": [1.5, 2, 4]})),
    "iron_colossus": U("Iron Colossus", 5, ["ironhold", "vanguard"], 1450, 108, 0.6, 1, 60, 50, 120, 60,
                       A("Earthshaker", "Stamps, stunning every enemy near it.",
                         {"do": "hit", "to": "around_self:2", "dmg": [200, 300, 1200], "stun": [1.5, 2, 6]})),
    "star_queen": U("Star Queen", 5, ["starlit", "mystic"], 900, 68, 0.7, 4, 30, 40, 100, 30,
                    A("Starfall Ward", "Shields the whole board for 5 s and heals the most hurt ally.",
                      {"do": "shield", "to": "allies", "amt": [350, 525, 2000], "secs": 5},
                      {"do": "heal", "to": "lowest_ally", "amt": [300, 450, 2000]})),
    # ================================================================ the rest of the roster
    # ---------------------------------------------------------------- cost 1
    "ember_squire": U("Ember Squire", 1, ["emberforged", "vanguard"], 700, 62, 0.6, 1, 45, 25, 80, 30,
                      A("Ember Guard", "Shields itself, then flares, scorching enemies beside it.",
                        {"do": "shield", "to": "self", "amt": [200, 300, 450], "secs": 4},
                        {"do": "hit", "to": "around_self:1", "dmg": [120, 180, 270]})),
    "thornling": U("Thornling", 1, ["thornwood", "ranger"], 480, 66, 0.7, 4, 15, 15, 70, 0,
                   A("Thorn Shot", "A barbed shot at its target.",
                     {"do": "hit", "to": "target", "type": "phys", "dmg": [180, 270, 400]})),
    "bone_rattler": U("Bone Rattler", 1, ["gravebound", "duelist"], 580, 70, 0.75, 1, 25, 20, 60, 0,
                      A("Gnaw", "Bites its target and heals for half the damage.",
                        {"do": "hit", "to": "target", "type": "phys", "dmg": [160, 240, 360], "heal_frac": 0.5})),
    "iron_recruit": U("Iron Recruit", 1, ["ironhold", "warden"], 720, 60, 0.6, 1, 45, 30, 80, 30,
                      A("Brace", "Braces for 5 s: far more armor and magic resist.",
                        {"do": "buff", "to": "self", "stat": "armor", "amt": [40, 60, 90], "secs": 5},
                        {"do": "buff", "to": "self", "stat": "mr", "amt": [40, 60, 90], "secs": 5})),
    "tide_scout": U("Tide Scout", 1, ["tidecallers", "ranger"], 480, 62, 0.7, 4, 15, 20, 70, 10,
                    A("Splash", "Water that splashes through three enemies.",
                      {"do": "hit", "to": "chain:3", "dmg": [120, 180, 270]})),
    "sky_sprite": U("Sky Sprite", 1, ["skyborne", "assassin"], 500, 70, 0.8, 1, 20, 20, 60, 0,
                    A("Pounce", "Pounces on the most hurt enemy.",
                      {"do": "dash", "to": "lowest_enemy"},
                      {"do": "hit", "to": "target", "type": "phys", "dmg": [200, 300, 450]})),
    "marsh_lurker": U("Marsh Lurker", 1, ["mirefolk", "assassin"], 520, 68, 0.75, 1, 20, 20, 60, 0,
                      A("Ambush", "A strike that ignores armor and slows.",
                        {"do": "hit", "to": "target", "type": "true", "dmg": [150, 225, 340], "slow": 0.3})),
    "star_novice": U("Starlit Novice", 1, ["starlit", "arcanist"], 500, 50, 0.65, 3, 15, 20, 70, 20,
                     A("Starbolt", "A bolt of starlight at its target.",
                       {"do": "hit", "to": "target", "dmg": [260, 390, 580]})),
    "grave_digger": U("Grave Digger", 1, ["gravebound", "warden"], 700, 58, 0.6, 1, 40, 25, 90, 40,
                      A("Shovel", "Clangs its target with a shovel, stunning it.",
                        {"do": "hit", "to": "target", "dmg": [140, 210, 320], "stun": [1, 1.25, 1.5]})),
    "forge_hound": U("Forge Hound", 1, ["emberforged", "duelist"], 560, 70, 0.8, 1, 25, 20, 60, 0,
                     A("Searing Bite", "A bite that leaves its target burning.",
                       {"do": "hit", "to": "target", "dmg": [140, 210, 320], "burn": 0.04})),
    # ---------------------------------------------------------------- cost 2
    "cinder_rogue": U("Cinder Rogue", 2, ["emberforged", "assassin"], 600, 80, 0.8, 1, 25, 20, 60, 0,
                      A("Flashstep", "Flashes to the farthest enemy and cuts it, setting it alight.",
                        {"do": "dash", "to": "farthest"},
                        {"do": "hit", "to": "target", "type": "phys", "dmg": [220, 330, 500], "burn": 0.02})),
    "moss_brute": U("Moss Brute", 2, ["thornwood", "warden"], 850, 66, 0.6, 1, 40, 30, 90, 40,
                    A("Overgrow", "Regrows HP and tangles enemies beside it.",
                      {"do": "heal", "to": "self", "amt": [300, 450, 700]},
                      {"do": "hit", "to": "around_self:1", "dmg": [100, 150, 220], "slow": 0.25})),
    "ghoul_reaver": U("Ghoul Reaver", 2, ["gravebound", "assassin"], 620, 80, 0.8, 1, 25, 20, 60, 0,
                      A("Feast", "Tears into the most hurt enemy, healing for part of it.",
                        {"do": "dash", "to": "lowest_enemy"},
                        {"do": "hit", "to": "target", "type": "phys", "dmg": [240, 360, 540], "heal_frac": 0.4})),
    "iron_crossbow": U("Iron Crossbow", 2, ["ironhold", "ranger"], 560, 78, 0.7, 4, 25, 20, 80, 0,
                       A("Piercing Bolt", "A bolt through everything in a line.",
                         {"do": "hit", "to": "line:5", "type": "phys", "dmg": [200, 300, 450]})),
    "reef_guard": U("Reef Guard", 2, ["tidecallers", "vanguard"], 820, 66, 0.6, 1, 45, 35, 90, 40,
                    A("Undertow", "Drags at the enemies beside it, stunning them.",
                      {"do": "hit", "to": "around_self:1", "dmg": [120, 180, 270], "stun": [1, 1.25, 1.5]})),
    "gale_dancer": U("Gale Dancer", 2, ["skyborne", "duelist"], 650, 78, 0.8, 1, 30, 20, 70, 0,
                     A("Whirlwind", "Spins through the enemies beside it and speeds up for 4 s.",
                       {"do": "hit", "to": "around_self:1", "type": "phys", "dmg": [120, 180, 270]},
                       {"do": "buff", "to": "self", "stat": "aspd_pct", "amt": [0.5, 0.7, 1.0], "secs": 4})),
    "bog_shaman": U("Bog Shaman", 2, ["mirefolk", "mystic"], 650, 60, 0.65, 3, 20, 30, 80, 30,
                    A("Peat Poultice", "Heals itself and every ally within 2 hexes.",
                      {"do": "heal", "to": "allies_near:2", "amt": [210, 315, 470]})),
    "thorn_dryad": U("Thorn Dryad", 2, ["thornwood", "mystic"], 580, 56, 0.65, 3, 20, 30, 80, 20,
                     A("Briar Lash", "Lashes the two nearest enemies, rooting them briefly.",
                       {"do": "hit", "to": "nearest:2", "dmg": [200, 300, 450], "stun": 0.75})),
    "iron_duelist": U("Iron Duelist", 2, ["ironhold", "duelist"], 680, 78, 0.75, 1, 40, 25, 70, 0,
                      A("Riposte", "Raises a guard and hits harder for 4 s.",
                        {"do": "shield", "to": "self", "amt": [220, 330, 500], "secs": 3},
                        {"do": "buff", "to": "self", "stat": "ad", "amt": [35, 55, 85], "secs": 4})),
    "star_archer": U("Starlit Archer", 2, ["starlit", "ranger"], 560, 76, 0.75, 4, 20, 20, 70, 0,
                     A("Moonvolley", "Arrows at four random enemies.",
                       {"do": "hit", "to": "random:4", "type": "phys", "dmg": [120, 180, 270]})),
    # ---------------------------------------------------------------- cost 3
    "lava_giant": U("Lava Giant", 3, ["emberforged", "warden"], 940, 76, 0.6, 1, 45, 35, 100, 40,
                    A("Eruption", "Erupts, burning every enemy within 2 hexes.",
                      {"do": "hit", "to": "around_self:2", "dmg": [200, 300, 480], "burn": 0.03})),
    "thorn_stalker": U("Thorn Stalker", 3, ["thornwood", "assassin"], 760, 104, 0.8, 1, 30, 25, 60, 0,
                       A("Bramble Trap", "Snares its target in brambles and strikes.",
                         {"do": "hit", "to": "target", "type": "phys", "dmg": [320, 480, 760], "stun": 1})),
    "wight_mage": U("Wight Mage", 3, ["gravebound", "arcanist"], 680, 54, 0.7, 4, 25, 30, 80, 20,
                    A("Soul Siphon", "Draws out its target's soul, healing for half.",
                      {"do": "hit", "to": "target", "dmg": [380, 570, 900], "heal_frac": 0.5})),
    "iron_warlord": U("Iron Warlord", 3, ["ironhold", "vanguard", "duelist"], 880, 82, 0.7, 1, 50, 35, 90, 30,
                      A("War Cry", "Allies within 2 hexes attack faster for 4 s; it shields itself.",
                        {"do": "buff", "to": "allies_near:2", "stat": "aspd_pct", "amt": [0.3, 0.4, 0.6], "secs": 4},
                        {"do": "shield", "to": "self", "amt": [200, 300, 450], "secs": 4})),
    "tidebinder": U("Tidebinder", 3, ["tidecallers", "arcanist"], 680, 54, 0.7, 4, 25, 30, 80, 30,
                    A("Riptide Bind", "Water binds everything round its target.",
                      {"do": "hit", "to": "around_target:1", "dmg": [300, 450, 720], "stun": 1.25})),
    "cloud_monk": U("Cloud Monk", 3, ["skyborne", "mystic"], 800, 76, 0.75, 1, 35, 40, 80, 20,
                    A("Calm Palm", "A palm strike that stuns, and calm that gives nearby allies mana.",
                      {"do": "hit", "to": "target", "dmg": [260, 390, 600], "stun": 1.25},
                      {"do": "mana", "to": "allies_near:2", "amt": [20, 25, 35]})),
    "mire_hag": U("Mire Hag", 3, ["mirefolk", "summoner"], 720, 54, 0.7, 3, 25, 30, 90, 30,
                  A("Bog Brood", "Calls up two bog imps.",
                    {"do": "summon", "unit": "bog_imp", "count": 2})),
    "star_warden": U("Star Warden", 3, ["starlit", "warden"], 950, 70, 0.65, 1, 45, 40, 90, 30,
                     A("Starshield", "Shields itself and the allies beside it for 4 s.",
                       {"do": "shield", "to": "allies_near:1", "amt": [200, 300, 480], "secs": 4})),
    # ---------------------------------------------------------------- cost 4
    "phoenix_knight": U("Phoenix Knight", 4, ["emberforged", "vanguard", "duelist"], 1050, 96, 0.7, 1, 50, 40, 100, 40,
                        A("Rebirth Flame", "Bursts into flame, burning enemies beside it and healing itself.",
                          {"do": "hit", "to": "around_self:1", "dmg": [300, 450, 1100], "burn": 0.04},
                          {"do": "heal", "to": "self", "amt": [300, 450, 1100]})),
    "elder_oak": U("Elder Oak", 4, ["thornwood", "warden", "vanguard"], 1300, 76, 0.55, 1, 55, 45, 110, 50,
                   A("Root Grasp", "Roots burst up, stunning every enemy within 2 hexes.",
                     {"do": "hit", "to": "around_self:2", "dmg": [150, 225, 700], "stun": [1.5, 2, 4]})),
    "lich": U("Lich", 4, ["gravebound", "summoner", "arcanist"], 850, 60, 0.7, 4, 30, 40, 100, 30,
              A("Raise Dead", "Raises two skeletons and blasts its target.",
                {"do": "summon", "unit": "skeleton", "count": 2},
                {"do": "hit", "to": "target", "dmg": [250, 375, 1000]})),
    "iron_engineer": U("Iron Engineer", 4, ["ironhold", "summoner"], 850, 66, 0.7, 3, 35, 35, 90, 40,
                       A("Deploy Turret", "Builds a turret that never moves but shoots far.",
                         {"do": "summon", "unit": "turret"})),
    "kraken_caller": U("Kraken Caller", 4, ["tidecallers", "assassin"], 960, 110, 0.8, 1, 35, 30, 70, 0,
                       A("Kraken Grasp", "Tentacles drag it to the most hurt enemy, which is crushed and held.",
                         {"do": "dash", "to": "lowest_enemy"},
                         {"do": "hit", "to": "target", "type": "phys", "dmg": [540, 810, 1800], "stun": 1})),
    # ---------------------------------------------------------------- cost 5
    "tempest_roc": U("Tempest Roc", 5, ["skyborne", "ranger"], 1000, 100, 0.8, 4, 30, 30, 90, 20,
                     A("Tempest", "Storm feathers rake five random enemies; it attacks faster for 5 s.",
                       {"do": "hit", "to": "random:5", "type": "phys", "dmg": [300, 450, 2000]},
                       {"do": "buff", "to": "self", "stat": "aspd_pct", "amt": [0.5, 0.7, 2.0], "secs": 5})),
    "mire_mother": U("Mire Mother", 5, ["mirefolk", "summoner", "arcanist"], 1100, 66, 0.7, 3, 35, 45, 110, 40,
                     A("Spawning Pool", "Spawns three mire spawn and floods the ground round its target.",
                       {"do": "summon", "unit": "mire_spawn", "count": [2, 2, 4]},
                       {"do": "hit", "to": "around_target:1", "dmg": [200, 300, 1200], "slow": 0.4})),
    # ---------------------------------------------------------------- summons (never in the shop)
    "treant": U("Treant", 0, [], 900, 80, 0.6, 1, 40, 30, 0, 0, None, summon=True),
    "bog_imp": U("Bog Imp", 0, [], 380, 50, 0.8, 1, 15, 15, 0, 0, None, summon=True),
    "skeleton": U("Skeleton", 0, [], 380, 55, 0.75, 1, 25, 10, 0, 0, None, summon=True),
    "turret": U("Turret", 0, [], 650, 75, 0.8, 4, 40, 40, 0, 0, None, summon=True, static=True),
    "mire_spawn": U("Mire Spawn", 0, [], 520, 55, 0.7, 1, 25, 25, 0, 0, None, summon=True),
    # ---------------------------------------------------------------- monsters (monster rounds)
    "wolf": U("Wolf", 0, [], 320, 32, 0.8, 1, 15, 15, 0, 0, None, summon=True),
    "bandit": U("Bandit", 0, [], 650, 60, 0.7, 1, 25, 20, 0, 0, None, summon=True),
    "bandit_chief": U("Bandit Chief", 0, [], 1300, 85, 0.7, 1, 35, 30, 0, 0, None, summon=True),
    "stone_golem": U("Stone Golem", 0, [], 2000, 95, 0.55, 1, 60, 40, 0, 0, None, summon=True),
}

SELECTORS = ("target", "self", "around_target", "around_self", "line", "nearest", "farthest", "random",
             "chain", "lowest_enemy", "lowest_ally", "allies_near", "allies", "enemies")
STEPS = ("hit", "heal", "shield", "buff", "summon", "dash", "mana")
PLAIN_STATS = ("hp_pct", "ad_pct", "aspd_pct", "armor", "mr", "ap", "dodge", "crit", "critdmg", "mana_cut")
SPECIAL = ("burn", "regen", "mana_regen", "revive", "chill", "shield", "duel", "double", "leap", "summon_boost")


def shop_units():
    return [k for k, u in UNITS.items() if not u.get("summon")]


def trait_counts(keys):
    """{trait: how many different units carry it} for the unit keys on a board."""
    counts = {}
    for key in set(keys):
        for t in UNITS[key]["traits"]:
            counts[t] = counts.get(t, 0) + 1
    return counts


def trait_level(trait, count):
    """The index into TRAITS[trait]["fx"] that `count` units reach, or -1."""
    level = -1
    for i, need in enumerate(TRAITS[trait]["levels"]):
        if count >= need:
            level = i
    return level
