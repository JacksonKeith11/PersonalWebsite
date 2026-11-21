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
TIERS = (1, 2, 3, 4, 5)
# A unit's price in gold by tier: steeper at the top (the owner asked for prices that don't scale
# linearly), so a tier-5 unit is something to save for and three-starring one is rare.
PRICE = {0: 0, 1: 1, 2: 2, 3: 3, 4: 5, 5: 8}
# Tiers 4 and 5 cost more than before the curve, so their HP and attack are scaled up a little to
# earn it. Applied by U() below, so the numbers written for each unit are before it.
TIER_POWER = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.08, 5: 1.15}

# ------------------------------------------------------------------ the match
START_HP = 60
BENCH = 8
SHOP_SIZE = 5
REROLL = 2
XP_COST, XP_GAIN = 4, 4
PASSIVE_XP = 2  # every round after the first
MAX_LEVEL = 8
LEVEL_XP = {1: 2, 2: 2, 3: 6, 4: 10, 5: 20, 6: 32, 7: 50}  # XP from each level to the next
# Chance (%) of each tier in a shop slot, by level.
SHOP_ODDS = {1: (100, 0, 0, 0, 0), 2: (100, 0, 0, 0, 0), 3: (75, 25, 0, 0, 0), 4: (55, 30, 15, 0, 0),
             5: (45, 33, 20, 2, 0), 6: (30, 40, 25, 5, 0), 7: (19, 30, 35, 15, 1), 8: (15, 20, 35, 25, 5)}
POOL = {1: 12, 2: 10, 3: 9, 4: 7, 5: 5}  # copies of each unit in a room, by tier
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
        "fx": [{"mana_regen": 5}, {"who": "team", "mana_regen": 5}]},
    "gravebound": {
        "name": "Gravebound", "kind": "origin", "levels": [2, 4, 6],
        "text": "The first time a Gravebound unit dies, it rises again with part of its HP.",
        "fx": [{"revive": 0.25}, {"revive": 0.45}, {"revive": 0.6}]},
    "skyborne": {
        "name": "Skyborne", "kind": "origin", "levels": [2, 4],
        "text": "Skyborne units dodge some attacks and attack faster.",
        "fx": [{"dodge": 0.25, "aspd_pct": 0.1}, {"dodge": 0.4, "aspd_pct": 0.2}]},
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
        "fx": [{"who": "team", "ap": 25}, {"who": "team", "ap": 45}, {"who": "team", "ap": 90}]},
    "mystic": {
        "name": "Mystic", "kind": "class", "levels": [2, 4],
        "text": "The whole board gains magic resist and regrows a little HP every second.",
        "fx": [{"who": "team", "mr": 30, "regen": 0.012}, {"who": "team", "mr": 60, "regen": 0.018}]},
    "assassin": {
        "name": "Assassin", "kind": "class", "levels": [2, 4, 6],
        "text": "Assassins leap to the enemy's back line at the start, and crit more often and harder.",
        "fx": [{"leap": 1, "crit": 0.2, "critdmg": 0.3}, {"leap": 1, "crit": 0.3, "critdmg": 0.4},
               {"leap": 1, "crit": 0.5, "critdmg": 0.7}]},
    "summoner": {
        "name": "Summoner", "kind": "class", "levels": [2, 4],
        "text": "What Summoners call up has more HP and damage.",
        "fx": [{"summon_boost": 0.3}, {"summon_boost": 0.7}]},
    "warden": {
        "name": "Warden", "kind": "class", "levels": [2, 4, 6],
        "text": "Wardens gain max HP.",
        "fx": [{"hp_pct": 0.25}, {"hp_pct": 0.5}, {"hp_pct": 0.75}]},
}


def U(name, tier, traits, hp, ad, aspd, rng, armor, mr, mana, start, ability, **extra):
    """A unit. `tier` (1-5, 0 for summons and monsters) sets its shop odds and pool; `cost` is its
    price in gold (PRICE)."""
    power = TIER_POWER[tier]
    unit = {"name": name, "tier": tier, "cost": PRICE[tier], "traits": traits, "hp": round(hp * power),
            "ad": round(ad * power), "as": aspd, "range": rng,
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
    "iron_colossus": U("Iron Colossus", 5, ["ironhold", "vanguard"], 1600, 115, 0.6, 1, 60, 50, 120, 60,
                       A("Earthshaker", "Stamps, stunning every enemy near it.",
                         {"do": "hit", "to": "around_self:2", "dmg": [300, 450, 1500], "stun": [1.5, 2, 6]})),
    "star_queen": U("Star Queen", 5, ["starlit", "mystic"], 900, 68, 0.7, 4, 30, 40, 100, 30,
                    A("Starfall Ward", "Shields the whole board for 5 s and heals the most hurt ally.",
                      {"do": "shield", "to": "allies", "amt": [350, 525, 2000], "secs": 5},
                      {"do": "heal", "to": "lowest_ally", "amt": [300, 450, 2000]})),
    # ================================================================ the rest of the roster
    # ---------------------------------------------------------------- cost 1
    "ember_squire": U("Ember Squire", 1, ["emberforged", "vanguard"], 660, 62, 0.6, 1, 45, 25, 80, 30,
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
                      {"do": "heal", "to": "self", "amt": [250, 375, 580]},
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
                       {"do": "hit", "to": "random:5", "type": "phys", "dmg": [250, 375, 2000]},
                       {"do": "buff", "to": "self", "stat": "aspd_pct", "amt": [0.4, 0.6, 2.0], "secs": 5})),
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
PLAIN_STATS = ("hp_pct", "ad_pct", "aspd_pct", "armor", "mr", "ap", "dodge", "crit", "critdmg", "mana_cut",
               "ad", "hp", "mana")
SPECIAL = ("burn", "regen", "mana_regen", "revive", "chill", "shield", "duel", "double", "leap", "summon_boost",
           # items
           "frenzy", "ability_crit", "mana_on_hit", "shred", "omnivamp", "splash", "on_hit_magic", "chill_on_hit",
           "pct_hit", "cast_mana", "aura", "cast_heal", "team_mana", "low_heal", "dr", "thorns", "cc_immune")

# ------------------------------------------------------------------ items
# Components drop from monster rounds and come with draft picks. Two components on one unit combine
# into an item (its `fx` plus both components' stats). A Sigil with another component makes that
# component's emblem (the holder gains the trait); two Sigils make a Crown (one more unit may stand on
# the board). A unit holds up to MAX_ITEMS. `fx` keys are the plain stats and specials sim.py knows
# (flat ad, hp and mana are added; the rest as in traits).
MAX_ITEMS = 3
COMPONENTS = {
    "sword": {"name": "Sword", "fx": {"ad": 12}, "text": "+12 attack"},
    "bow": {"name": "Bow", "fx": {"aspd_pct": 0.12}, "text": "+12% attack speed"},
    "rod": {"name": "Rod", "fx": {"ap": 15}, "text": "+15 ability power"},
    "tear": {"name": "Tear", "fx": {"mana": 15}, "text": "+15 starting mana"},
    "vest": {"name": "Vest", "fx": {"armor": 25}, "text": "+25 armor"},
    "cloak": {"name": "Cloak", "fx": {"mr": 25}, "text": "+25 magic resist"},
    "belt": {"name": "Belt", "fx": {"hp": 180}, "text": "+180 HP"},
    "sigil": {"name": "Sigil", "fx": {"hp": 80}, "text": "+80 HP; with another component, an emblem"},
}
COMPONENT_WEIGHT = {"sigil": 0.5}  # how often each drops (others 1)
_RECIPES = [
    ("greatsword", "Greatsword", "sword", "sword", {"crit": 0.2, "critdmg": 0.3}, "Crits more often and harder."),
    ("ravager", "Ravager", "sword", "bow", {"frenzy": 0.05}, "Each attack makes it 5% faster, up to 10 times."),
    ("spellblade", "Spellblade", "sword", "rod", {"ability_crit": 1, "crit": 0.15}, "Its abilities can crit."),
    ("mana_edge", "Mana Edge", "sword", "tear", {"mana_on_hit": 6}, "Each attack gives 6 more mana."),
    ("sunder_axe", "Sunder Axe", "sword", "vest", {"shred": 30}, "Attacks strip 30 armor from the target for 3 s."),
    ("hexblade", "Hexblade", "sword", "cloak", {"omnivamp": 0.2}, "Heals for 20% of all the damage it does."),
    ("cleaver", "Titan Cleaver", "sword", "belt", {"splash": 0.35}, "Attacks also hit enemies beside the target for 35%."),
    ("twin_bow", "Twin Bow", "bow", "bow", {"double": 0.3}, "Attacks have a 30% chance to strike twice."),
    ("storm_rod", "Storm Rod", "bow", "rod", {"on_hit_magic": 45}, "Attacks deal 45 more magic damage."),
    ("harp", "Quickcast Harp", "bow", "tear", {"mana_on_hit": 4, "aspd_pct": 0.1}, "Faster attacks that give 4 more mana."),
    ("duel_guard", "Duelist's Guard", "bow", "vest", {"dodge": 0.25}, "Dodges a quarter of attacks."),
    ("galeband", "Galeband", "bow", "cloak", {"chill_on_hit": 0.25}, "Attacks slow the target's attacks by 25% for 2 s."),
    ("giant_bane", "Giant's Bane", "bow", "belt", {"pct_hit": 0.03}, "Attacks deal 3% of the target's max HP more."),
    ("grimoire", "Grand Grimoire", "rod", "rod", {"ap": 30}, "Another +30 ability power."),
    ("archstaff", "Archmage Staff", "rod", "tear", {"cast_mana": 25}, "After casting, starts again with 25 mana."),
    ("ember_mantle", "Ember Mantle", "rod", "vest", {"aura": 0.012}, "Burns enemies beside it for 1.2% of their max HP a second."),
    ("spellward", "Spellward", "rod", "cloak", {"shield": 350}, "Starts the fight with a 350 shield."),
    ("lifebloom", "Lifebloom Staff", "rod", "belt", {"cast_heal": 180}, "Each cast also heals the most hurt ally for 180."),
    ("chalice", "Overflowing Chalice", "tear", "tear", {"mana_regen": 4}, "4 more mana every second."),
    ("frost_aegis", "Frost Aegis", "tear", "vest", {"chill": 0.3}, "Whoever attacks it attacks 30% slower for 2 s."),
    ("mana_ward", "Mana Ward", "tear", "cloak", {"team_mana": 20}, "Allies beside it start with 20 more mana."),
    ("bell", "Redemption Bell", "tear", "belt", {"low_heal": 300}, "The first time it falls below half HP, heals allies within 2 hexes for 300."),
    ("bastion", "Bastion Plate", "vest", "vest", {"dr": 0.15}, "Takes 15% less damage."),
    ("twin_ward", "Twin Ward", "vest", "cloak", {"dr": 0.08, "shield": 200}, "Takes 8% less damage and starts with a 200 shield."),
    ("spiked_hide", "Spiked Hide", "vest", "belt", {"thorns": 0.35}, "Attackers take 35% of their hit back as magic damage."),
    ("veil", "Veil of Stillness", "cloak", "cloak", {"cc_immune": 1}, "Can't be stunned."),
    ("second_wind", "Second Wind", "cloak", "belt", {"regen": 0.02}, "Regrows 2% of its max HP every second."),
    ("colossus_belt", "Colossus Belt", "belt", "belt", {"hp_pct": 0.15, "regen": 0.01}, "15% more max HP, and regrows 1% a second."),
]
EMBLEM_FROM = {"sword": "duelist", "bow": "ranger", "rod": "arcanist", "tear": "mystic", "vest": "vanguard",
               "cloak": "warden", "belt": "summoner"}


def _sum_fx(*fxs):
    out = {}
    for fx in fxs:
        for k, v in fx.items():
            out[k] = out.get(k, 0) + v
    return out


ITEMS = {}
for _k, _c in COMPONENTS.items():
    ITEMS[_k] = {"name": _c["name"], "kind": "component", "from": None, "fx": dict(_c["fx"]), "text": _c["text"]}
for _k, _name, _a, _b, _fx, _text in _RECIPES:
    ITEMS[_k] = {"name": _name, "kind": "item", "from": [_a, _b],
                 "fx": _sum_fx(COMPONENTS[_a]["fx"], COMPONENTS[_b]["fx"], _fx), "text": _text}
for _t in TRAITS:  # every trait has an emblem; seven can be made with a Sigil, the rest come from augments
    _comp = next((c for c, t in EMBLEM_FROM.items() if t == _t), None)
    ITEMS["emblem_" + _t] = {"name": TRAITS[_t]["name"] + " Emblem", "kind": "emblem", "trait": _t,
                             "from": ["sigil", _comp] if _comp else None,
                             "fx": _sum_fx(COMPONENTS["sigil"]["fx"], COMPONENTS[_comp]["fx"]) if _comp else {"hp": 150},
                             "text": f"Its holder is also {TRAITS[_t]['name']}."}
ITEMS["crown"] = {"name": "Crown", "kind": "crown", "from": ["sigil", "sigil"], "fx": {"hp": 160},
                  "text": "One more unit may stand on your board while its holder does."}
RECIPE = {tuple(sorted(i["from"])): k for k, i in ITEMS.items() if i["from"]}


def combine(a, b):
    """The item two components make, or None."""
    return RECIPE.get(tuple(sorted((a, b))))


def completed_items():
    return [k for k, i in ITEMS.items() if i["kind"] == "item"]


# Components a monster round drops to a winner (a loser gets one if it drops two or more).
PVE_DROPS = {1: 1, 2: 1, 6: 2, 11: 2}

# ------------------------------------------------------------------ commanders
# Each player picks one of three at the start: a passive, and a power that charges over `charge`
# rounds and is used during planning. game.py does what they say.
COMMANDERS = {
    "quartermaster": {"name": "The Quartermaster", "passive": "Your shop has six slots.",
                      "power": "Three free rerolls.", "charge": 3},
    "warlord": {"name": "The Warlord", "passive": "Units on your front row have 12% more HP.",
                "power": "Next fight, every unit of yours starts with a 300 shield.", "charge": 4},
    "necromancer": {"name": "The Necromancer", "passive": "The first of your units to die each fight rises with 40% HP.",
                    "power": "Raise a random tier-2 unit onto your bench.", "charge": 4},
    "alchemist": {"name": "The Alchemist", "passive": "A free component at rounds 5, 10 and 15.",
                  "power": "Brew a random component.", "charge": 4},
    "merchant": {"name": "The Merchant", "passive": "Interest goes up to 7 gold instead of 5.",
                 "power": "Gain 4 gold.", "charge": 3},
    "sage": {"name": "The Sage", "passive": "One more XP every other round.", "power": "Gain 5 XP.", "charge": 4},
    "beastmaster": {"name": "The Beastmaster", "passive": "Your summons have 30% more HP and attack.",
                    "power": "Next fight, a Treant (at your highest star) fights for you.", "charge": 3},
    "archmage": {"name": "The Archmage", "passive": "Your units have 20 more ability power.",
                 "power": "Next fight, every unit of yours starts with 40 more mana.", "charge": 3},
    "survivor": {"name": "The Survivor", "passive": "You lose 15% less HP when you lose a fight.",
                 "power": "Heal 6 HP.", "charge": 5},
    "blademaster": {"name": "The Blademaster", "passive": "Your units attack 8% faster.",
                    "power": "Next fight, your units attack 40% faster for the first 6 s.", "charge": 3},
    "forgemaster": {"name": "The Forgemaster", "passive": "Start with two components.",
                    "power": "Forge a random finished item.", "charge": 5},
    "oracle": {"name": "The Oracle", "passive": "Your shop rolls as if you were a level higher.",
               "power": "A free reroll that favours units you already own.", "charge": 2},
}
COMMANDER_CHOICES = 3

# ------------------------------------------------------------------ augments
# One of three at AUGMENT_ROUNDS (one free reroll each time). All three offered are the same tier
# (1 lesser, 2 greater, 3 grand), drawn by AUGMENT_TIER_ODDS. game.py does what they say: `gold`,
# `xp`, `components`, `items` (random finished), `units` (random of a tier), `heal` (HP), `team`
# (fx for all your units in every fight), `bonus` (+n to a trait you field), `emblem` (that trait's
# emblem item), `interest` (more interest cap), `revive_first` (the first of your units to die each
# fight rises with that share of HP), `crown` (a Crown item).
AUGMENT_ROUNDS = (3, 8, 13)
AUGMENT_TIER_ODDS = {3: (60, 35, 5), 8: (20, 60, 20), 13: (5, 40, 55)}
AUGMENT_TIER_NAMES = {1: "Lesser", 2: "Greater", 3: "Grand"}
AUGMENTS = {
    # lesser
    "pocket_change": {"tier": 1, "name": "Pocket Change", "text": "Gain 6 gold.", "gold": 6},
    "study": {"tier": 1, "name": "Late-Night Study", "text": "Gain 8 XP.", "xp": 8},
    "spare_parts": {"tier": 1, "name": "Spare Parts", "text": "Gain a random component.", "components": 1},
    "recruits": {"tier": 1, "name": "Fresh Recruits", "text": "Gain two random tier-1 units.", "units": [1, 1]},
    "thick_skin": {"tier": 1, "name": "Thick Skin", "text": "Heal 8 HP.", "heal": 8},
    "whetstone": {"tier": 1, "name": "Whetstone", "text": "Your units have 8 more attack.", "team": {"ad": 8}},
    # greater
    "treasure": {"tier": 2, "name": "Buried Treasure", "text": "Gain 15 gold.", "gold": 15},
    "armory": {"tier": 2, "name": "Armory", "text": "Gain two random components.", "components": 2},
    "fast_track": {"tier": 2, "name": "Fast Track", "text": "Gain 14 XP.", "xp": 14},
    "battle_hardened": {"tier": 2, "name": "Battle Hardened", "text": "Your units have 120 more HP.", "team": {"hp": 120}},
    "rich": {"tier": 2, "name": "Rich Get Richer", "text": "Gain 6 gold; interest goes 2 higher.", "gold": 6, "interest": 2},
    "second_life": {"tier": 2, "name": "Second Life", "text": "The first of your units to die each fight rises with 30% HP.",
                    "revive_first": 0.3},
    # grand
    "hoard": {"tier": 3, "name": "Dragon's Hoard", "text": "Gain 30 gold.", "gold": 30},
    "arsenal": {"tier": 3, "name": "Arsenal", "text": "Gain a random finished item and a component.", "items": 1, "components": 1},
    "crowned": {"tier": 3, "name": "Crowned", "text": "Gain a Crown: one more unit on your board.", "crown": 1},
    "titanic": {"tier": 3, "name": "Titanic Strength", "text": "Your units have 12% more HP and 10 more attack.",
                "team": {"hp_pct": 0.12, "ad": 10}},
}
for _t, _d in TRAITS.items():
    AUGMENTS["heart_" + _t] = {"tier": 1, "name": _d["name"] + " Heart", "trait": _t, "bonus": 1,
                               "text": f"Counts as one more {_d['name']} unit, if you field one."}
    AUGMENTS["crest_" + _t] = {"tier": 2, "name": _d["name"] + " Crest", "trait": _t, "emblem": _t,
                               "text": f"Gain a {_d['name']} Emblem."}
    AUGMENTS["soul_" + _t] = {"tier": 3, "name": _d["name"] + " Soul", "trait": _t, "bonus": 2,
                              "text": f"Counts as two more {_d['name']} units, if you field one."}
AUGMENT_CHOICES = 3

# ------------------------------------------------------------------ shared drafts
# At DRAFT_ROUNDS, before planning, everyone picks one unit (each holding a component) from a shared
# set, lowest HP first. DRAFT_TIERS: the tiers on offer that round.
DRAFT_ROUNDS = (4, 9, 14)
DRAFT_TIERS = {4: (1, 2), 9: (2, 3), 14: (3, 4)}
DRAFT_TURN = 8  # seconds a person has for their pick
DRAFT_EXTRA = 2  # options beyond one each


def shop_units():
    return [k for k, u in UNITS.items() if not u.get("summon")]


def unit_traits(key, items=()):
    """A unit's traits, plus any its emblems give."""
    traits = list(UNITS[key]["traits"])
    for i in items:
        t = ITEMS.get(i, {}).get("trait")
        if t and t not in traits:
            traits.append(t)
    return traits


def trait_counts(units, bonus=None):
    """{trait: how many different units carry it} for a board: `units` is unit keys, or (key, items)
    pairs so emblems count. A copy of a unit with an emblem counts for that trait once, like any
    copy. `bonus` (augments) adds to traits the board already has."""
    seen = {}
    for u in units:
        key, items = (u, ()) if isinstance(u, str) else u
        seen.setdefault(key, set()).update(unit_traits(key, items))
    counts = {}
    for traits in seen.values():
        for t in traits:
            counts[t] = counts.get(t, 0) + 1
    for t, n in (bonus or {}).items():
        if counts.get(t):
            counts[t] += n
    return counts


def trait_level(trait, count):
    """The index into TRAITS[trait]["fx"] that `count` units reach, or -1."""
    level = -1
    for i, need in enumerate(TRAITS[trait]["levels"]):
        if count >= need:
            level = i
    return level
