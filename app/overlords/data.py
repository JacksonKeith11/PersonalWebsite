"""Overlords' units, traits and their numbers, as data.

A unit has stats at one star (hp and ad grow by STAR_MULT at two and three stars), one origin and
one or two classes, and an ability: what it does when its mana fills, as a list of steps that
`sim.py` runs in order. A step is a dict with `do` (what), `to` (who: a selector) and numbers that
are either one value or a list of three, one per star. See sim.Fight.step_* and sim.Fight.select.

Steps:
    hit     damage `dmg` of `type` (magic by default, also phys and true); optional `stun` (seconds),
            `slow` (fraction of attack speed lost for 3 s) and `burn` (fraction of the target's max
            hp per second for 3 s)
    heal    heal `amt`
    shield  a shield of `amt` for `secs`
    buff    `stat` (aspd_pct, ad, armor, mr) up by `amt` for `secs`
    summon  `unit` (a key in UNITS with "summon": True) at the caster's star, next to the caster
    dash    jump next to the farthest enemy and make it the target
Selectors: target, self, around_target:R, around_self:R, line:L, nearest:N, farthest, random:N,
chain:N, lowest_ally, allies_near:R, allies, enemies. Ability damage and healing scale with ap
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
        "fx": [{"burn": 0.015}, {"burn": 0.03}, {"burn": 0.05}]},
    "thornwood": {
        "name": "Thornwood", "kind": "origin", "levels": [2, 4, 6],
        "text": "Thornwood units regrow a share of their max HP every second.",
        "fx": [{"regen": 0.01}, {"regen": 0.02}, {"regen": 0.04}]},
    "tidecallers": {
        "name": "Tidecallers", "kind": "origin", "levels": [2, 4],
        "text": "Tidecallers gain mana every second; at 4, so does the whole board.",
        "fx": [{"mana_regen": 3}, {"who": "team", "mana_regen": 5}]},
    "gravebound": {
        "name": "Gravebound", "kind": "origin", "levels": [2, 4, 6],
        "text": "The first time a Gravebound unit dies, it rises again with part of its HP.",
        "fx": [{"revive": 0.25}, {"revive": 0.45}, {"revive": 0.7}]},
    "skyborne": {
        "name": "Skyborne", "kind": "origin", "levels": [2, 4],
        "text": "Skyborne units dodge some attacks.",
        "fx": [{"dodge": 0.2}, {"dodge": 0.4}]},
    "ironhold": {
        "name": "Ironhold", "kind": "origin", "levels": [2, 4, 6],
        "text": "Ironhold units gain armor and magic resist.",
        "fx": [{"armor": 25, "mr": 25}, {"armor": 50, "mr": 50}, {"armor": 90, "mr": 90}]},
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
        "fx": [{"shield": 200}, {"shield": 450}, {"shield": 800}]},
    "duelist": {
        "name": "Duelist", "kind": "class", "levels": [2, 4, 6],
        "text": "Each Duelist attack speeds up their attacks, stacking up to 8 times.",
        "fx": [{"duel": 0.06}, {"duel": 0.1}, {"duel": 0.15}]},
    "ranger": {
        "name": "Ranger", "kind": "class", "levels": [2, 4],
        "text": "Ranger attacks have a chance to strike twice.",
        "fx": [{"double": 0.25}, {"double": 0.5}]},
    "arcanist": {
        "name": "Arcanist", "kind": "class", "levels": [2, 4, 6],
        "text": "The whole board's abilities hit harder and heal more.",
        "fx": [{"who": "team", "ap": 15}, {"who": "team", "ap": 40}, {"who": "team", "ap": 75}]},
    "mystic": {
        "name": "Mystic", "kind": "class", "levels": [2, 4],
        "text": "The whole board gains magic resist.",
        "fx": [{"who": "team", "mr": 25}, {"who": "team", "mr": 55}]},
    "assassin": {
        "name": "Assassin", "kind": "class", "levels": [2, 4, 6],
        "text": "Assassins leap to the enemy's back line at the start, and crit more often and harder.",
        "fx": [{"leap": 1, "crit": 0.15, "critdmg": 0.25}, {"leap": 1, "crit": 0.3, "critdmg": 0.4},
               {"leap": 1, "crit": 0.45, "critdmg": 0.6}]},
    "summoner": {
        "name": "Summoner", "kind": "class", "levels": [2, 4],
        "text": "What Summoners call up has more HP and damage.",
        "fx": [{"summon_boost": 0.5}, {"summon_boost": 1.2}]},
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
    "ashling": U("Ashling", 1, ["emberforged", "duelist"], 600, 68, 0.75, 1, 30, 20, 60, 0,
                 A("Flurry", "Attacks far faster for 4 s.",
                   {"do": "buff", "to": "self", "stat": "aspd_pct", "amt": [0.6, 0.8, 1.1], "secs": 4})),
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
                      {"do": "hit", "to": "around_target:1", "dmg": [180, 270, 400], "slow": 0.3})),
    # ---------------------------------------------------------------- cost 3
    "sky_lancer": U("Sky Lancer", 3, ["skyborne", "duelist"], 750, 88, 0.75, 1, 35, 25, 70, 0,
                    A("Dive", "Dives at the farthest enemy and runs it through.",
                      {"do": "dash", "to": "farthest"},
                      {"do": "hit", "to": "target", "type": "phys", "dmg": [260, 390, 620]})),
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
    "storm_herald": U("Storm Herald", 4, ["skyborne", "mystic"], 750, 68, 0.7, 3, 25, 40, 90, 20,
                      A("Chain Lightning", "Lightning that leaps through five enemies.",
                        {"do": "hit", "to": "chain:5", "dmg": [240, 360, 950]})),
    # ---------------------------------------------------------------- cost 5
    "deep_priest": U("Deep Priest", 5, ["tidecallers", "summoner", "arcanist"], 900, 74, 0.7, 4, 30, 40, 110, 40,
                     A("Tidal Wave", "A wave down a line that stuns everything it hits.",
                       {"do": "hit", "to": "line:6", "dmg": [450, 700, 3000], "stun": [1.5, 2, 4]})),
    "iron_colossus": U("Iron Colossus", 5, ["ironhold", "vanguard"], 1300, 108, 0.6, 1, 60, 50, 120, 60,
                       A("Earthshaker", "Stamps, stunning every enemy near it.",
                         {"do": "hit", "to": "around_self:2", "dmg": [200, 300, 1200], "stun": [1.5, 2, 6]})),
    "star_queen": U("Star Queen", 5, ["starlit", "mystic"], 900, 68, 0.7, 4, 30, 40, 100, 30,
                    A("Starfall Ward", "Shields the whole board for 5 s.",
                      {"do": "shield", "to": "allies", "amt": [300, 450, 2000], "secs": 5})),
    # ---------------------------------------------------------------- summons (never in the shop)
    "treant": U("Treant", 0, [], 900, 80, 0.6, 1, 40, 30, 0, 0, None, summon=True),
    # ---------------------------------------------------------------- monsters (monster rounds)
    "wolf": U("Wolf", 0, [], 320, 32, 0.8, 1, 15, 15, 0, 0, None, summon=True),
    "bandit": U("Bandit", 0, [], 650, 60, 0.7, 1, 25, 20, 0, 0, None, summon=True),
    "bandit_chief": U("Bandit Chief", 0, [], 1300, 85, 0.7, 1, 35, 30, 0, 0, None, summon=True),
    "stone_golem": U("Stone Golem", 0, [], 2000, 95, 0.55, 1, 60, 40, 0, 0, None, summon=True),
}

SELECTORS = ("target", "self", "around_target", "around_self", "line", "nearest", "farthest", "random",
             "chain", "lowest_ally", "allies_near", "allies", "enemies")
STEPS = ("hit", "heal", "shield", "buff", "summon", "dash")
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
