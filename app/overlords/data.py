"""Overlords' units, traits and their numbers, as data.

A unit has stats at one star (hp and ad grow by STAR_MULT at two and three stars), one origin and
one or two classes, and an ability: what it does when its mana fills, as a list of steps that
`sim.py` runs in order. A step is a dict with `do` (what), `to` (who: a selector) and numbers that
are either one value or a list of three, one per star. See sim.Fight.step_* and sim.Fight.select.

Steps:
    hit     damage `dmg` of `type` (magic by default, also phys and true); optional `stun` (seconds),
            `slow` (fraction of attack speed lost for 3 s), `burn` (fraction of the target's max
            hp per second for 3 s), `heal_frac` (the caster heals that share of the damage done),
            `amp` (the target takes that much more damage for `amp_secs`, default 4), `wound` (it
            heals half as much for that many seconds), `mana_burn` (drains its mana), `knock` (shoves
            it that many hexes away), `execute` (finishes it below that share of HP), `missing` (up
            to that much more damage the more hurt it is), `refund` (a kill refills the caster's mana)
    heal    heal `amt`
    shield  a shield of `amt` for `secs`
    buff    `stat` (aspd_pct, ad, armor, mr, dodge, regen, burns, thorns) up by `amt` for `secs`
    grow    `stat` (ad, ap, armor, mr, aspd_pct, hp) up by `amt` for the rest of the fight
    summon  `count` (default 1) of `unit` (a key in UNITS with "summon": True) at the caster's star,
            next to the caster; a unit with "static": True never moves
    raise   like summon, but where units have fallen (beside the caster when nobody has)
    dash    jump next to the unit `to` picks (farthest, lowest_enemy...) and make it the target
    pull    drag the unit `to` picks next to the caster and make it the target
    taunt   the enemies `to` picks must attack the caster for `secs`
    vanish  the caster can't be targeted or hit for `secs`
    devour  swallow the unit `to` picks: `dmg`, then it can't act or be reached for `secs`
    cleanse clear burns, slows, stuns, marks and wounds from the allies `to` picks
    zone    lingering ground (radius `r`, `secs`) at `to` (target, self or cluster): `dmg` a second to
            enemies in it (and `slow`), or `heal` a second to allies
    mana    give other allies `amt` mana
Any step can have `delay` (seconds): it's marked on the ground and lands that much later.
Selectors: target, self, around_target:R, around_self:R, line:L, nearest:N, farthest, random:N,
chain:N, lowest_enemy (the most hurt), highest_hp, cluster:R (the thickest knot of enemies),
lowest_ally, allies_near:R, nearest_allies:N, allies, enemies. Ability damage and healing scale with
ap (100 = as written).

A unit's `passive` is fx it always has (as items give), with `passive_text` saying so.

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
# 1 gold per 8 saved, at most 5 (was per 10, then 6 before the auction gave saved gold a use: docs/overlords.md)
INTEREST_PER, MAX_INTEREST = 8, 5
PLAN_TIME, FIRST_PLAN = 30, 20
RESULT_PAUSE = 3.0  # seconds after the last fight ends before the next round
START_LEVEL = 1


# Spoils (the owner asked for gold earned in fights, after Guildrun, late November 2026): after a fight
# against a player, 1 gold for every SPOILS_PER of their units yours brought down, at most SPOILS_MAX
# (summons don't count; monster rounds pay PVE_GOLD instead).
SPOILS_PER, SPOILS_MAX = 3, 3


def spoils(fallen):
    return min(SPOILS_MAX, fallen // SPOILS_PER)


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
PVE_GOLD = {1: 3, 2: 4, 6: 6, 11: 8}  # items come from the armory, so monsters pay in gold only

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
        "fx": [{"revive": 0.25}, {"revive": 0.4}, {"revive": 0.5}]},
    "skyborne": {
        "name": "Skyborne", "kind": "origin", "levels": [2, 4],
        "text": "Skyborne units dodge some attacks and attack faster.",
        "fx": [{"dodge": 0.25, "aspd_pct": 0.15}, {"dodge": 0.4, "aspd_pct": 0.2}]},
    "ironhold": {
        "name": "Ironhold", "kind": "origin", "levels": [2, 4, 6],
        "text": "Ironhold units gain armor and magic resist.",
        "fx": [{"armor": 30, "mr": 30}, {"armor": 60, "mr": 60}, {"armor": 100, "mr": 100}]},
    "starlit": {
        "name": "Starlit", "kind": "origin", "levels": [2, 4],
        "text": "Starlit abilities need less mana.",
        "fx": [{"mana_cut": 0.25}, {"mana_cut": 0.4}]},
    "mirefolk": {
        "name": "Mirefolk", "kind": "origin", "levels": [2, 4],
        "text": "Whoever attacks a Mirefolk unit is chilled, attacking slower for 2 s.",
        "fx": [{"chill": 0.35}, {"chill": 0.42}]},
    # ---------------------------------------------------------------- classes
    "vanguard": {
        "name": "Vanguard", "kind": "class", "levels": [2, 4, 6],
        "text": "Vanguards start the fight with a shield for 10 s.",
        "fx": [{"shield": 260}, {"shield": 750}, {"shield": 1300}]},
    "duelist": {
        "name": "Duelist", "kind": "class", "levels": [2, 4, 6],
        "text": "Each Duelist attack speeds up their attacks, stacking up to 8 times.",
        "fx": [{"duel": 0.13}, {"duel": 0.14}, {"duel": 0.16}]},
    "ranger": {
        "name": "Ranger", "kind": "class", "levels": [2, 4],
        "text": "Ranger attacks have a chance to strike twice.",
        "fx": [{"double": 0.3}, {"double": 0.5}]},
    "arcanist": {
        "name": "Arcanist", "kind": "class", "levels": [2, 4, 6],
        "text": "The whole board's abilities hit harder and heal more.",
        "fx": [{"who": "team", "ap": 40}, {"who": "team", "ap": 75}, {"who": "team", "ap": 140}]},
    "mystic": {
        "name": "Mystic", "kind": "class", "levels": [2, 4],
        "text": "The whole board gains magic resist and regrows a little HP every second; at 4, abilities "
                "also hurt it less.",
        "fx": [{"who": "team", "mr": 30, "regen": 0.012},
               {"who": "team", "mr": 50, "regen": 0.018, "spell_dr": 0.2}]},
    "assassin": {
        "name": "Assassin", "kind": "class", "levels": [2, 4, 6],
        "text": "Assassins leap to the enemy's back line at the start, dodge some attacks, and crit more often and harder.",
        "fx": [{"leap": 1, "crit": 0.4, "critdmg": 0.6, "dodge": 0.15}, {"leap": 1, "crit": 0.42, "critdmg": 0.62, "dodge": 0.18},
               {"leap": 1, "crit": 0.45, "critdmg": 0.65, "dodge": 0.22}]},
    "summoner": {
        "name": "Summoner", "kind": "class", "levels": [2, 4],
        "text": "What Summoners call up has more HP and damage.",
        "fx": [{"summon_boost": 0.3}, {"summon_boost": 0.7}]},
    "warden": {
        "name": "Warden", "kind": "class", "levels": [2, 4, 6],
        "text": "Wardens gain max HP, and at 4 take less damage too.",
        "fx": [{"hp_pct": 0.35}, {"hp_pct": 0.6, "dr": 0.1}, {"hp_pct": 0.9, "dr": 0.18}]},
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
    # Each unit has its own trick (the roster review, November 2026): taunts, pulls, knockbacks, marks,
    # wounds, vanishing, lingering ground, delayed blows, executes, growth, raising the fallen,
    # swallowing. `passive` (fx, as items use) and `passive_text` are what a unit always has.
    # ---------------------------------------------------------------- cost 1
    "ashling": U("Ashling", 1, ["emberforged", "duelist"], 640, 68, 0.75, 1, 30, 20, 50, 0,
                 A("Flurry", "Attacks far faster for 4 s, and every hit meanwhile sets its target burning.",
                   {"do": "buff", "to": "self", "stat": "aspd_pct", "amt": [0.8, 1.0, 1.3], "secs": 4},
                   {"do": "buff", "to": "self", "stat": "burns", "amt": [0.02, 0.03, 0.04], "secs": 4})),
    "bramble_guard": U("Bramble Guard", 1, ["thornwood", "vanguard"], 700, 61, 0.6, 1, 45, 30, 80, 30,
                       A("Barkskin", "Shields itself and dares the enemies within 2 hexes to attack it.",
                         {"do": "shield", "to": "self", "amt": [250, 375, 600], "secs": 4},
                         {"do": "taunt", "to": "around_self:2", "secs": [2, 2.5, 3]})),
    "tide_acolyte": U("Tide Acolyte", 1, ["tidecallers", "mystic"], 500, 54, 0.65, 3, 20, 20, 70, 20,
                      A("Rising Water", "Heals the most hurt ally and washes off its burns, slows and marks.",
                        {"do": "heal", "to": "lowest_ally", "amt": [170, 255, 400]},
                        {"do": "cleanse", "to": "lowest_ally"})),
    "ember_squire": U("Ember Squire", 1, ["emberforged", "vanguard"], 660, 62, 0.6, 1, 45, 25, 80, 30,
                      A("Ember Guard", "Shields itself, then flares, setting enemies beside it burning.",
                        {"do": "shield", "to": "self", "amt": [200, 300, 450], "secs": 4},
                        {"do": "hit", "to": "around_self:1", "dmg": [90, 135, 200], "burn": 0.015})),
    "thornling": U("Thornling", 1, ["thornwood", "ranger"], 500, 72, 0.7, 4, 15, 15, 60, 0,
                   A("Thorn Shot", "A barbed shot: its target heals half as much for 5 s.",
                     {"do": "hit", "to": "target", "type": "phys", "dmg": [230, 345, 520], "wound": 5})),
    "bone_rattler": U("Bone Rattler", 1, ["gravebound", "duelist"], 580, 70, 0.75, 1, 25, 20, 60, 0,
                      A("Gnaw", "Bites its target and heals for half the damage.",
                        {"do": "hit", "to": "target", "type": "phys", "dmg": [150, 225, 340], "heal_frac": 0.5}),
                      passive={"death_burst": 90},
                      passive_text="When it falls for good, its bones burst over the enemies beside it (90 magic damage)."),
    "iron_recruit": U("Iron Recruit", 1, ["ironhold", "warden"], 720, 60, 0.6, 1, 45, 30, 80, 30,
                      A("Brace", "Braces for 5 s: far more armor and resist, and attackers take some of their hit back.",
                        {"do": "buff", "to": "self", "stat": "armor", "amt": [40, 60, 90], "secs": 5},
                        {"do": "buff", "to": "self", "stat": "mr", "amt": [40, 60, 90], "secs": 5},
                        {"do": "buff", "to": "self", "stat": "thorns", "amt": [0.25, 0.35, 0.5], "secs": 5})),
    "tide_scout": U("Tide Scout", 1, ["tidecallers", "ranger"], 480, 62, 0.7, 4, 15, 20, 70, 10,
                    A("Riptide Shot", "Water that splashes through three enemies, draining their mana.",
                      {"do": "hit", "to": "chain:3", "dmg": [110, 165, 250], "mana_burn": [15, 20, 30]})),
    "sky_sprite": U("Sky Sprite", 1, ["skyborne", "assassin"], 500, 70, 0.8, 1, 20, 20, 60, 0,
                    A("Pounce", "Pounces on the most hurt enemy; one left below 12% HP is finished off.",
                      {"do": "dash", "to": "lowest_enemy"},
                      {"do": "hit", "to": "target", "type": "phys", "dmg": [190, 285, 430], "execute": 0.12})),
    "marsh_lurker": U("Marsh Lurker", 1, ["mirefolk", "assassin"], 520, 68, 0.75, 1, 20, 20, 60, 0,
                      A("Ambush", "Sinks out of reach for a second, then strikes from the mud: true damage, and a slow.",
                        {"do": "vanish", "secs": 1.0},
                        {"do": "hit", "to": "target", "type": "true", "dmg": [170, 255, 380], "slow": 0.3, "delay": 1.0})),
    "star_novice": U("Starlit Novice", 1, ["starlit", "arcanist"], 500, 50, 0.65, 3, 15, 20, 70, 20,
                     A("Starbolt", "A bolt of starlight at its target. Each one leaves it 15 ability power stronger.",
                       {"do": "hit", "to": "target", "dmg": [230, 345, 520]},
                       {"do": "grow", "stat": "ap", "amt": 15})),
    "grave_digger": U("Grave Digger", 1, ["gravebound", "warden"], 700, 58, 0.6, 1, 40, 25, 90, 40,
                      A("Shovel", "Clangs its target, stunning it; one left below 20% HP is buried.",
                        {"do": "hit", "to": "target", "dmg": [130, 195, 300], "stun": [1, 1.25, 1.5], "execute": 0.2})),
    "forge_hound": U("Forge Hound", 1, ["emberforged", "duelist"], 560, 70, 0.8, 1, 25, 20, 60, 0,
                     A("Searing Bite", "A bite that leaves its target burning and raw: it takes 15% more damage for 3 s.",
                       {"do": "hit", "to": "target", "dmg": [130, 195, 300], "burn": 0.03, "amp": 0.15, "amp_secs": 3})),
    # ---------------------------------------------------------------- cost 2
    "grave_archer": U("Grave Archer", 2, ["gravebound", "ranger"], 550, 74, 0.75, 4, 20, 20, 70, 0,
                      A("Bone Volley", "Looses bone arrows at three random enemies.",
                        {"do": "hit", "to": "random:3", "type": "phys", "dmg": [160, 240, 360]})),
    "iron_sentinel": U("Iron Sentinel", 2, ["ironhold", "warden"], 750, 68, 0.6, 1, 45, 30, 90, 40,
                       A("Shield Slam", "Slams its target, stunning it and shoving it a hex back.",
                         {"do": "hit", "to": "target", "dmg": [160, 240, 360], "stun": [1.5, 1.75, 2], "knock": 1})),
    "mire_witch": U("Mire Witch", 2, ["mirefolk", "arcanist"], 550, 54, 0.65, 3, 20, 25, 80, 20,
                    A("Hex Bog", "Curses the ground round its target: everyone there is hurt, slowed, and takes 20% more damage for 4 s.",
                      {"do": "hit", "to": "around_target:1", "dmg": [170, 255, 380], "slow": 0.3, "amp": 0.2, "amp_secs": 4})),
    "cinder_rogue": U("Cinder Rogue", 2, ["emberforged", "assassin"], 600, 80, 0.8, 1, 25, 20, 60, 0,
                      A("Flashstep", "Flashes to the farthest enemy and cuts it, setting it alight.",
                        {"do": "dash", "to": "farthest"},
                        {"do": "hit", "to": "target", "type": "phys", "dmg": [220, 330, 500], "burn": 0.02})),
    "moss_brute": U("Moss Brute", 2, ["thornwood", "warden"], 850, 66, 0.6, 1, 40, 30, 90, 40,
                    A("Overgrow", "Regrows HP and tangles enemies beside it.",
                      {"do": "heal", "to": "self", "amt": [250, 375, 580]},
                      {"do": "hit", "to": "around_self:1", "dmg": [100, 150, 220], "slow": 0.25})),
    "ghoul_reaver": U("Ghoul Reaver", 2, ["gravebound", "assassin"], 580, 80, 0.8, 1, 25, 20, 60, 0,
                      A("Feast", "Tears into the most hurt enemy, healing for part of it. A kill refills its mana.",
                        {"do": "dash", "to": "lowest_enemy"},
                        {"do": "hit", "to": "target", "type": "phys", "dmg": [205, 310, 520], "heal_frac": 0.4,
                         "refund": True})),
    "iron_crossbow": U("Iron Crossbow", 2, ["ironhold", "ranger"], 560, 78, 0.7, 4, 25, 20, 70, 0,
                       A("Piercing Bolt", "A bolt through everything in a line.",
                         {"do": "hit", "to": "line:5", "type": "phys", "dmg": [260, 390, 580]})),
    "reef_guard": U("Reef Guard", 2, ["tidecallers", "vanguard"], 820, 66, 0.6, 1, 45, 35, 90, 40,
                    A("Undertow", "Drags at the enemies beside it, stunning them.",
                      {"do": "hit", "to": "around_self:1", "dmg": [120, 180, 270], "stun": [1, 1.25, 1.5]})),
    "gale_dancer": U("Gale Dancer", 2, ["skyborne", "duelist"], 650, 78, 0.8, 1, 30, 20, 70, 0,
                     A("Whirlwind", "Spins through the enemies beside it, slowing them, and speeds up for 4 s.",
                       {"do": "hit", "to": "around_self:1", "type": "phys", "dmg": [130, 195, 290], "slow": 0.25},
                       {"do": "buff", "to": "self", "stat": "aspd_pct", "amt": [0.5, 0.7, 1.0], "secs": 4})),
    "bog_shaman": U("Bog Shaman", 2, ["mirefolk", "mystic"], 650, 60, 0.65, 3, 20, 30, 80, 30,
                    A("Peat Poultice", "Heals itself and every ally within 2 hexes, and hardens their skin (+25 armor for 4 s).",
                      {"do": "heal", "to": "allies_near:2", "amt": [180, 270, 400]},
                      {"do": "buff", "to": "allies_near:2", "stat": "armor", "amt": [25, 35, 50], "secs": 4})),
    "thorn_dryad": U("Thorn Dryad", 2, ["thornwood", "mystic"], 580, 56, 0.65, 3, 20, 30, 80, 20,
                     A("Briar Patch", "Grows briars round its target for 4 s: enemies in them are hurt and slowed.",
                       {"do": "zone", "to": "target", "r": 1, "secs": 4, "dmg": [70, 105, 160], "slow": 0.3})),
    "iron_duelist": U("Iron Duelist", 2, ["ironhold", "duelist"], 680, 78, 0.75, 1, 40, 25, 70, 0,
                      A("Riposte", "Parries every attack for 1.5 s and hits harder for 4 s.",
                        {"do": "buff", "to": "self", "stat": "dodge", "amt": 1.0, "secs": 1.5},
                        {"do": "buff", "to": "self", "stat": "ad", "amt": [45, 70, 100], "secs": 4})),
    "star_archer": U("Starlit Archer", 2, ["starlit", "ranger"], 560, 76, 0.75, 4, 20, 20, 70, 0,
                     A("Moonvolley", "Arrows at four random enemies.",
                       {"do": "hit", "to": "random:4", "type": "phys", "dmg": [110, 165, 250]}),
                     passive={"multishot": 0.2},
                     passive_text="Each attack also strikes a second enemy near its target for 20%."),
    "toad_brawler": U("Toad Brawler", 2, ["mirefolk", "duelist"], 700, 74, 0.75, 1, 35, 25, 70, 0,
                      A("Tongue Lash", "Lashes out its tongue, dragging the farthest enemy over to be punched and dazed.",
                        {"do": "pull", "to": "farthest"},
                        {"do": "hit", "to": "target", "type": "phys", "dmg": [220, 330, 500], "stun": 0.75})),
    # ---------------------------------------------------------------- cost 3
    "sky_lancer": U("Sky Lancer", 3, ["skyborne", "duelist"], 820, 88, 0.75, 1, 35, 25, 70, 0,
                    A("Dive", "Dives at the farthest enemy and runs it through.",
                      {"do": "dash", "to": "farthest"},
                      {"do": "hit", "to": "target", "type": "phys", "dmg": [370, 555, 860]})),
    "ember_mage": U("Ember Mage", 3, ["emberforged", "arcanist"], 650, 61, 0.7, 4, 25, 25, 80, 20,
                    A("Meteor", "Calls a meteor down on the thickest knot of enemies: it lands a moment later and leaves them burning.",
                      {"do": "hit", "to": "cluster:1", "dmg": [340, 510, 800], "burn": 0.03, "delay": 0.8})),
    "starlit_blade": U("Starlit Blade", 3, ["starlit", "assassin"], 650, 94, 0.8, 1, 25, 20, 60, 0,
                       A("Shadow Cut", "A cut that ignores armor, up to twice as deep the more hurt its target is.",
                         {"do": "hit", "to": "target", "type": "true", "dmg": [300, 450, 720], "missing": 1.0})),
    "lava_giant": U("Lava Giant", 3, ["emberforged", "warden"], 940, 76, 0.6, 1, 45, 35, 100, 40,
                    A("Eruption", "Erupts, burning every enemy within 2 hexes, and leaves lava round itself for 4 s.",
                      {"do": "hit", "to": "around_self:2", "dmg": [140, 210, 340], "burn": 0.02},
                      {"do": "zone", "to": "self", "r": 1, "secs": 4, "dmg": [35, 55, 90]})),
    "thorn_stalker": U("Thorn Stalker", 3, ["thornwood", "assassin"], 760, 104, 0.8, 1, 30, 25, 60, 0,
                       A("Bramble Trap", "Snares its target in brambles and strikes.",
                         {"do": "hit", "to": "target", "type": "phys", "dmg": [320, 480, 760], "stun": 1})),
    "wight_mage": U("Wight Mage", 3, ["gravebound", "arcanist"], 680, 54, 0.7, 4, 25, 30, 80, 20,
                    A("Soul Siphon", "Draws out its target's soul and mana, healing for half the damage.",
                      {"do": "hit", "to": "target", "dmg": [360, 540, 860], "heal_frac": 0.5, "mana_burn": [30, 40, 60]})),
    "iron_warlord": U("Iron Warlord", 3, ["ironhold", "vanguard", "duelist"], 880, 82, 0.7, 1, 50, 35, 90, 30,
                      A("War Cry", "Allies within 2 hexes attack faster for 4 s; it shields itself.",
                        {"do": "buff", "to": "allies_near:2", "stat": "aspd_pct", "amt": [0.3, 0.4, 0.6], "secs": 4},
                        {"do": "shield", "to": "self", "amt": [200, 300, 450], "secs": 4})),
    "tidebinder": U("Tidebinder", 3, ["tidecallers", "arcanist"], 680, 54, 0.7, 4, 25, 30, 80, 30,
                    A("Riptide Bind", "Water binds everything round its target.",
                      {"do": "hit", "to": "around_target:1", "dmg": [280, 420, 680], "stun": 1.25})),
    "cloud_monk": U("Cloud Monk", 3, ["skyborne", "mystic"], 800, 76, 0.75, 1, 35, 40, 80, 20,
                    A("Calm Palm", "A palm strike that stuns and blows its target two hexes back; calm gives nearby allies mana.",
                      {"do": "hit", "to": "target", "dmg": [240, 360, 560], "stun": 1.25, "knock": 2},
                      {"do": "mana", "to": "allies_near:2", "amt": [20, 25, 35]})),
    "mire_hag": U("Mire Hag", 3, ["mirefolk", "summoner"], 720, 54, 0.7, 3, 25, 30, 90, 30,
                  A("Bog Brood", "Calls up two bog imps, which burst when they fall.",
                    {"do": "summon", "unit": "bog_imp", "count": 2})),
    "star_warden": U("Star Warden", 3, ["starlit", "warden"], 950, 70, 0.65, 1, 45, 40, 90, 30,
                     A("Starshield", "Shields itself and the allies beside it for 4 s.",
                       {"do": "shield", "to": "allies_near:1", "amt": [200, 300, 480], "secs": 4}),
                     passive={"guard_aura": 0.12},
                     passive_text="Allies beside it take 12% less damage."),
    "cinder_priest": U("Cinder Priest", 3, ["emberforged", "mystic"], 700, 56, 0.7, 3, 25, 35, 80, 30,
                       A("Cauterize", "Heals and cleanses the most hurt ally, and scorches the enemies round its own target.",
                         {"do": "heal", "to": "lowest_ally", "amt": [280, 420, 650]},
                         {"do": "cleanse", "to": "lowest_ally"},
                         {"do": "hit", "to": "around_target:1", "dmg": [110, 165, 250], "burn": 0.03})),
    "bog_knight": U("Bog Knight", 3, ["mirefolk", "vanguard"], 950, 70, 0.6, 1, 50, 35, 90, 40,
                    A("Mudwall", "Plants its shield: the enemies within 2 hexes must attack it, and it's shielded.",
                      {"do": "taunt", "to": "around_self:2", "secs": [2, 2.5, 3]},
                      {"do": "shield", "to": "self", "amt": [300, 450, 700], "secs": 4})),
    "wind_archer": U("Wind Archer", 3, ["skyborne", "ranger"], 680, 80, 0.75, 4, 20, 20, 70, 10,
                     A("Gust Arrow", "An arrow on a gale: it knocks its target two hexes back and slows it.",
                       {"do": "hit", "to": "target", "type": "phys", "dmg": [300, 450, 700], "knock": 2, "slow": 0.3})),
    # ---------------------------------------------------------------- cost 4
    "thorn_shaman": U("Thorn Shaman", 4, ["thornwood", "summoner"], 920, 74, 0.7, 3, 30, 30, 70, 40,
                      A("Call the Grove", "Calls up a Treant beside itself.",
                        {"do": "summon", "unit": "treant"})),
    "grave_knight": U("Grave Knight", 4, ["gravebound", "vanguard", "warden"], 1000, 94, 0.65, 1, 50, 40, 100, 40,
                      A("Reaping Swing", "Swings round itself, healing; enemies it leaves below 15% HP are reaped.",
                        {"do": "hit", "to": "around_self:1", "dmg": [250, 375, 1000], "execute": 0.15},
                        {"do": "heal", "to": "self", "amt": [250, 375, 1000]})),
    "storm_herald": U("Storm Herald", 4, ["skyborne", "mystic"], 850, 72, 0.7, 3, 25, 40, 80, 20,
                      A("Chain Lightning", "Lightning that leaps through five enemies, scattering their mana.",
                        {"do": "hit", "to": "chain:5", "dmg": [290, 435, 1200], "mana_burn": 15})),
    "phoenix_knight": U("Phoenix Knight", 4, ["emberforged", "vanguard", "duelist"], 1000, 92, 0.7, 1, 50, 40, 100, 40,
                        A("Rebirth Flame", "Bursts into flame, burning enemies beside it and healing itself.",
                          {"do": "hit", "to": "around_self:1", "dmg": [240, 360, 1000], "burn": 0.03},
                          {"do": "heal", "to": "self", "amt": [180, 270, 1000]}),
                        passive={"revive": 0.3},
                        passive_text="The first time it falls, it rises from its ashes with 30% HP."),
    "elder_oak": U("Elder Oak", 4, ["thornwood", "warden", "vanguard"], 1300, 76, 0.55, 1, 55, 45, 110, 50,
                   A("Root Grasp", "Roots burst up, stunning every enemy within 2 hexes.",
                     {"do": "hit", "to": "around_self:2", "dmg": [150, 225, 700], "stun": [1.5, 2, 4]})),
    "lich": U("Lich", 4, ["gravebound", "summoner", "arcanist"], 850, 60, 0.7, 4, 30, 40, 100, 30,
              A("Raise Dead", "Raises skeletons where units have fallen (beside itself if none have), and blasts its target.",
                {"do": "raise", "unit": "skeleton", "count": [2, 2, 4]},
                {"do": "hit", "to": "target", "dmg": [250, 375, 1000]})),
    "iron_engineer": U("Iron Engineer", 4, ["ironhold", "summoner"], 900, 70, 0.7, 3, 35, 35, 75, 40,
                       A("Deploy Turret", "Builds a turret that never moves but shoots far, cracking armor.",
                         {"do": "summon", "unit": "turret"})),
    "kraken_caller": U("Kraken Caller", 4, ["tidecallers", "assassin"], 960, 110, 0.8, 1, 35, 30, 70, 0,
                       A("Kraken Grasp", "Tentacles drag the most hurt enemy to it, to be crushed and held.",
                         {"do": "pull", "to": "lowest_enemy"},
                         {"do": "hit", "to": "target", "type": "phys", "dmg": [600, 900, 1800], "stun": 1})),
    "moonshadow": U("Moonshadow", 4, ["starlit", "assassin"], 950, 104, 0.8, 1, 35, 30, 70, 0,
                    A("Eclipse Step", "Steps through shadow to the farthest enemy, out of reach for a second, then cuts "
                      "it and those beside it (true damage).",
                      {"do": "dash", "to": "farthest"},
                      {"do": "vanish", "secs": 1.0},
                      {"do": "hit", "to": "around_target:1", "type": "true", "dmg": [360, 540, 1200], "delay": 0.8})),
    "bog_colossus": U("Bog Colossus", 4, ["mirefolk", "warden"], 1350, 80, 0.6, 1, 50, 40, 110, 50,
                      A("Swallow", "Swallows the nearest enemy whole: it can't act or be reached for a while. Then it "
                        "digests (healing itself).",
                        {"do": "devour", "to": "nearest:1", "secs": [2.5, 3, 5], "dmg": [300, 450, 1200]},
                        {"do": "heal", "to": "self", "amt": [250, 375, 900]})),
    "rune_smith": U("Rune Smith", 4, ["ironhold", "arcanist"], 1050, 88, 0.7, 1, 50, 40, 70, 40,
                    A("Runeforge", "Carves runes into the two nearest allies: for the rest of the fight they have more "
                      "attack and armor (it stacks), then hammers its target.",
                      {"do": "grow", "to": "nearest_allies:2", "stat": "ad", "amt": [30, 45, 120]},
                      {"do": "grow", "to": "nearest_allies:2", "stat": "armor", "amt": [20, 30, 80]},
                      {"do": "hit", "to": "target", "dmg": [220, 330, 800]})),
    # ---------------------------------------------------------------- cost 5
    "deep_priest": U("Deep Priest", 5, ["tidecallers", "summoner", "arcanist"], 950, 74, 0.7, 4, 30, 40, 100, 40,
                     A("Tidal Wave", "A wave crashes down round its target, stunning everything it hits.",
                       {"do": "hit", "to": "around_target:2", "dmg": [400, 600, 2500], "stun": [1.5, 2, 4]})),
    "iron_colossus": U("Iron Colossus", 5, ["ironhold", "vanguard"], 1700, 115, 0.6, 1, 60, 50, 120, 60,
                       A("Earthshaker", "Stamps, stunning every enemy near it, and stands firm: 40 more armor and resist "
                         "for 5 s.",
                         {"do": "hit", "to": "around_self:2", "dmg": [300, 450, 1500], "stun": [1.5, 2, 6]},
                         {"do": "buff", "to": "self", "stat": "armor", "amt": 40, "secs": 5},
                         {"do": "buff", "to": "self", "stat": "mr", "amt": 40, "secs": 5})),
    "star_queen": U("Star Queen", 5, ["starlit", "mystic"], 900, 68, 0.7, 4, 30, 40, 100, 30,
                    A("Starfall Ward", "Shields the whole board for 5 s and heals the most hurt ally.",
                      {"do": "shield", "to": "allies", "amt": [350, 525, 2000], "secs": 5},
                      {"do": "heal", "to": "lowest_ally", "amt": [300, 450, 2000]})),
    "tempest_roc": U("Tempest Roc", 5, ["skyborne", "ranger"], 1000, 100, 0.8, 4, 30, 30, 90, 20,
                     A("Tempest", "Storm feathers rake five random enemies; it attacks faster for 5 s.",
                       {"do": "hit", "to": "random:5", "type": "phys", "dmg": [250, 375, 2000]},
                       {"do": "buff", "to": "self", "stat": "aspd_pct", "amt": [0.4, 0.6, 2.0], "secs": 5})),
    "mire_mother": U("Mire Mother", 5, ["mirefolk", "summoner", "arcanist"], 1100, 66, 0.7, 3, 35, 45, 110, 40,
                     A("Spawning Pool", "Spawns mire spawn (which burst when they fall) and floods the ground round its target.",
                       {"do": "summon", "unit": "mire_spawn", "count": [2, 2, 4]},
                       {"do": "hit", "to": "around_target:1", "dmg": [260, 390, 1200], "slow": 0.4})),
    "ember_wyrm": U("Ember Wyrm", 5, ["emberforged", "ranger"], 1200, 95, 0.75, 3, 35, 35, 90, 30,
                    A("Dragonfire", "Breathes fire down a line, burning all it touches, and leaves the ground round its "
                      "target ablaze for 3 s.",
                      {"do": "hit", "to": "line:5", "dmg": [400, 600, 2500], "burn": 0.05},
                      {"do": "zone", "to": "target", "r": 1, "secs": 3, "dmg": [130, 200, 600]})),
    "old_mossheart": U("Old Mossheart", 5, ["thornwood", "mystic"], 1400, 80, 0.65, 1, 50, 50, 110, 40,
                       A("World Bloom", "Every ally is healed and regrows 2% a second for 5 s; enemies beside it are "
                         "rooted.",
                         {"do": "heal", "to": "allies", "amt": [140, 210, 2000]},
                         {"do": "buff", "to": "allies", "stat": "regen", "amt": [0.02, 0.03, 0.1], "secs": 5},
                         {"do": "hit", "to": "around_self:1", "dmg": [150, 225, 1000], "stun": [1.25, 1.5, 4]})),
    "bone_tyrant": U("Bone Tyrant", 5, ["gravebound", "vanguard"], 1450, 100, 0.65, 1, 50, 45, 120, 40,
                     A("Grave Decree", "Raises a skeleton from each of the fallen (up to its limit) and stuns enemies "
                       "within 2 hexes.",
                       {"do": "raise", "unit": "skeleton", "count": [2, 3, 8]},
                       {"do": "hit", "to": "around_self:2", "dmg": [150, 225, 1500], "stun": [1.0, 1.25, 4]})),
    # ---------------------------------------------------------------- summons (never in the shop)
    "treant": U("Treant", 0, [], 900, 80, 0.6, 1, 40, 30, 0, 0, None, summon=True,
                passive={"regen": 0.02}, passive_text="Regrows 2% of its HP a second."),
    "bog_imp": U("Bog Imp", 0, [], 380, 50, 0.8, 1, 15, 15, 0, 0, None, summon=True,
                 passive={"death_burst": 90}, passive_text="Bursts when it falls (90 magic damage beside it)."),
    "skeleton": U("Skeleton", 0, [], 380, 55, 0.75, 1, 25, 10, 0, 0, None, summon=True),
    "turret": U("Turret", 0, [], 650, 75, 0.8, 4, 40, 40, 0, 0, None, summon=True, static=True,
                passive={"shred": 20}, passive_text="Its shots strip 20 armor for 3 s."),
    "mire_spawn": U("Mire Spawn", 0, [], 520, 55, 0.7, 1, 25, 25, 0, 0, None, summon=True,
                    passive={"death_burst": 130}, passive_text="Bursts when it falls (130 magic damage beside it)."),
    "sapling": U("Sapling", 0, [], 420, 45, 0.7, 1, 25, 25, 0, 0, None, summon=True),
    # ---------------------------------------------------------------- monsters (monster rounds)
    "wolf": U("Wolf", 0, [], 320, 32, 0.8, 1, 15, 15, 0, 0, None, summon=True),
    "bandit": U("Bandit", 0, [], 650, 60, 0.7, 1, 25, 20, 0, 0, None, summon=True),
    "bandit_chief": U("Bandit Chief", 0, [], 1300, 85, 0.7, 1, 35, 30, 0, 0, None, summon=True),
    "stone_golem": U("Stone Golem", 0, [], 2000, 95, 0.55, 1, 60, 40, 0, 0, None, summon=True),
}

SELECTORS = ("target", "self", "around_target", "around_self", "line", "nearest", "farthest", "random",
             "chain", "lowest_enemy", "lowest_ally", "allies_near", "allies", "enemies", "cluster", "highest_hp",
             "nearest_allies")
STEPS = ("hit", "heal", "shield", "buff", "summon", "dash", "mana", "grow", "taunt", "vanish", "cleanse", "pull",
         "zone", "raise", "devour")
PLAIN_STATS = ("hp_pct", "ad_pct", "aspd_pct", "armor", "mr", "ap", "dodge", "crit", "critdmg", "mana_cut",
               "ad", "hp", "mana")
SPECIAL = ("burn", "regen", "mana_regen", "revive", "chill", "shield", "duel", "double", "leap", "summon_boost",
           # items
           "frenzy", "ability_crit", "mana_on_hit", "shred", "omnivamp", "splash", "on_hit_magic", "chill_on_hit",
           "pct_hit", "cast_mana", "aura", "cast_heal", "team_mana", "low_heal", "dr", "thorns", "cc_immune",
           # the roster review: units' passives, items and artifacts
           "multishot", "death_burst", "guard_aura", "taunt_start", "every3", "on_kill", "execute", "wound_on_hit",
           "grow_hp", "echo", "spell_dr", "last_stand", "summon_every", "low_bonus", "cast_grow_ap", "cast_share",
           "horn", "echo_first", "fallen_rally",
           # extra abilities
           "cast_power", "cast_burn", "mark_on_hit")

# ------------------------------------------------------------------ extra abilities
# Every unit has its own ability (above). When three copies merge into a 2-star, and again at 3 stars,
# its owner picks one extra ability for it (the owner asked for Guildrun's choice of abilities at each
# rank in November 2026). The options at a star are the extra ability of each of the unit's own traits
# at that star, plus one that strengthens the unit's own ability ("{ability}" in its name becomes that
# ability's name), so units sharing traits share options but every unit has three or four. `fx` is
# what items use (sim.Fight.give); new keys for these: cast_power (its ability's damage, healing,
# shields, buffs and summons are that much stronger), cast_burn (its ability sets what it hits burning,
# a share of max HP a second for 3 s), mark_on_hit (its attacks make the target take that much more
# damage for 3 s). Picks stay with the unit (selling loses them); a merge keeps the first copy's.
TALENTS = {
    # 2 stars
    "kindling": {"star": 2, "trait": "emberforged", "name": "Kindling", "fx": {"burn": 0.02, "cast_burn": 0.03},
                 "text": "Its attacks set the target burning (2% of max HP a second), and its ability burns "
                         "whatever it hits (3% a second)."},
    "deep_roots": {"star": 2, "trait": "thornwood", "name": "Deep Roots", "fx": {"regen": 0.02, "hp": 100},
                   "text": "Regrows 2% of its max HP every second, and has 100 more HP."},
    "flowing": {"star": 2, "trait": "tidecallers", "name": "Flowing Tide", "fx": {"mana_regen": 5, "mana": 15},
                "text": "Gains 5 mana every second and starts with 15 more."},
    "undying": {"star": 2, "trait": "gravebound", "name": "Undying", "fx": {"revive": 0.4},
                "text": "The first time it falls, it rises again with 40% HP."},
    "featherstep": {"star": 2, "trait": "skyborne", "name": "Featherstep", "fx": {"dodge": 0.2, "aspd_pct": 0.08},
                    "text": "Dodges 20% of attacks and attacks 8% faster."},
    "iron_skin": {"star": 2, "trait": "ironhold", "name": "Iron Skin", "fx": {"dr": 0.12},
                  "text": "Takes 12% less damage from everything."},
    "starlight": {"star": 2, "trait": "starlit", "name": "Starlight", "fx": {"mana_cut": 0.2},
                  "text": "Its ability needs 20% less mana."},
    "sludge": {"star": 2, "trait": "mirefolk", "name": "Sludge", "fx": {"chill_on_hit": 0.3, "chill": 0.2},
               "text": "Its attacks slow the target's attacks by 30% for 2 s, and whoever attacks it is slowed by 20%."},
    "bulwark": {"star": 2, "trait": "vanguard", "name": "Bulwark", "fx": {"shield": 400, "armor": 15},
                "text": "Starts each fight with a 400 shield (for 10 s), and has 15 more armor."},
    "momentum": {"star": 2, "trait": "duelist", "name": "Momentum", "fx": {"frenzy": 0.05},
                 "text": "Each attack makes it 5% faster, up to 10 times."},
    "split_shot": {"star": 2, "trait": "ranger", "name": "Split Shot", "fx": {"multishot": 0.45},
                   "text": "Each attack also strikes a second enemy near the target for 45%."},
    "focus": {"star": 2, "trait": "arcanist", "name": "Arcane Focus", "fx": {"ap": 35},
              "text": "+35 ability power: its ability hits harder and heals more."},
    "mending": {"star": 2, "trait": "mystic", "name": "Mending", "fx": {"cast_heal": 300},
                "text": "Each cast also heals the most hurt ally for 300."},
    "ambusher": {"star": 2, "trait": "assassin", "name": "Ambusher", "fx": {"low_bonus": 0.3, "crit": 0.1},
                 "text": "Does 30% more damage to enemies below half HP, and crits 10% more often."},
    "brood": {"star": 2, "trait": "summoner", "name": "Bigger Brood", "fx": {"summon_boost": 0.3, "ap": 15},
              "text": "What it calls up has 30% more HP and attack, and it has 15 more ability power."},
    "stalwart": {"star": 2, "trait": "warden", "name": "Stalwart", "fx": {"hp_pct": 0.16},
                 "text": "16% more max HP."},
    "empowered": {"star": 2, "trait": None, "name": "Empowered {ability}", "fx": {"cast_power": 0.3},
                  "text": "Its own ability is 30% stronger: damage, healing, shields, buffs and what it calls up."},
    # 3 stars
    "inferno": {"star": 3, "trait": "emberforged", "name": "Inferno Heart", "fx": {"aura": 0.02, "cast_burn": 0.04},
                "text": "Enemies beside it burn for 2% of their max HP a second, and its ability burns whatever "
                        "it hits (4% a second)."},
    "thornmail": {"star": 3, "trait": "thornwood", "name": "Thornmail", "fx": {"thorns": 0.4, "regen": 0.02},
                  "text": "Attackers take 40% of their hit back as magic damage, and it regrows 2% of its max HP a second."},
    "surge": {"star": 3, "trait": "tidecallers", "name": "Tidal Surge", "fx": {"cast_share": 30, "cast_mana": 25},
              "text": "After each cast, the two nearest allies get 30 mana and it starts again with 25."},
    "death_knell": {"star": 3, "trait": "gravebound", "name": "Death Knell", "fx": {"revive": 0.5, "death_burst": 300},
                    "text": "The first time it falls, it rises with 50% HP; when it falls for good, it bursts over the "
                            "enemies beside it (300 magic damage)."},
    "tailwind": {"star": 3, "trait": "skyborne", "name": "Tailwind", "fx": {"aspd_pct": 0.3, "dodge": 0.15},
                 "text": "Attacks 30% faster and dodges 15% of attacks."},
    "unbreakable": {"star": 3, "trait": "ironhold", "name": "Unbreakable", "fx": {"cc_immune": 1, "dr": 0.2},
                    "text": "Can't be stunned or swallowed, and takes 20% less damage."},
    "supernova": {"star": 3, "trait": "starlit", "name": "Supernova", "fx": {"cast_grow_ap": 25, "mana_cut": 0.15},
                  "text": "Each cast leaves it 25 ability power stronger for the rest of the fight, and its ability "
                          "needs 15% less mana."},
    "bog_grip": {"star": 3, "trait": "mirefolk", "name": "Bog Grip", "fx": {"mark_on_hit": 0.25, "chill": 0.3},
                 "text": "Its attacks mark the target to take 25% more damage for 3 s, and whoever attacks it is "
                         "slowed by 30%."},
    "challenge": {"star": 3, "trait": "vanguard", "name": "Challenge", "fx": {"taunt_start": 3, "shield": 900, "dr": 0.12},
                  "text": "Enemies within 3 hexes must attack it for the first 3 s; it starts with a 900 shield and takes "
                          "12% less damage."},
    "executioner": {"star": 3, "trait": "duelist", "name": "Executioner", "fx": {"execute": 0.15, "frenzy": 0.06},
                    "text": "Its attacks finish enemies below 15% HP, and each attack makes it 6% faster (up to 10)."},
    "deadeye": {"star": 3, "trait": "ranger", "name": "Deadeye", "fx": {"pct_hit": 0.04, "crit": 0.2},
                "text": "Attacks deal 4% of the target's max HP more, and crit 20% more often."},
    "spellsurge": {"star": 3, "trait": "arcanist", "name": "Spellsurge", "fx": {"ability_crit": 1, "crit": 0.3, "critdmg": 0.3, "ap": 50, "mana_cut": 0.1},
                   "text": "Its ability can crit; it crits 30% more often and 30% harder, has 50 more ability power, "
                           "and its ability needs 10% less mana."},
    "sanctuary": {"star": 3, "trait": "mystic", "name": "Sanctuary", "fx": {"low_heal": 500, "spell_dr": 0.25},
                  "text": "Abilities do 25% less to it; the first time it falls below half HP, it heals allies within "
                          "2 hexes for 500."},
    "shadowstep": {"star": 3, "trait": "assassin", "name": "Shadowstep", "fx": {"last_stand": [0.3, 1.5, 0.3], "critdmg": 0.3},
                   "text": "The first time it falls below 30% HP, it slips out of reach for 1.5 s and heals 30%; its "
                           "crits hit 30% harder."},
    "grove_call": {"star": 3, "trait": "summoner", "name": "Grove Call", "fx": {"summon_every": ["sapling", 4], "hp": 200},
                   "text": "Every 4 s, a sapling grows beside it and fights; it has 200 more HP."},
    "colossal": {"star": 3, "trait": "warden", "name": "Colossal", "fx": {"hp_pct": 0.1, "grow_hp": [0.03, 0.3]},
                 "text": "10% more max HP, and it grows 3% more every second, up to 30%."},
    "mastered": {"star": 3, "trait": None, "name": "Mastered {ability}", "fx": {"cast_power": 0.3, "mana_cut": 0.2},
                 "text": "Its own ability is 30% stronger and needs 20% less mana."},
}
TALENT_STARS = (2, 3)


def talent_options(key, star):
    """The extra abilities a unit can pick from on reaching `star`: its traits' (in order), then its own
    ability's."""
    if star not in TALENT_STARS or not UNITS[key].get("ability"):
        return []
    traits = UNITS[key]["traits"]
    mine = sorted((k for k, t in TALENTS.items() if t["star"] == star and t["trait"] in traits),
                  key=lambda k: traits.index(TALENTS[k]["trait"]))
    return mine + [k for k, t in TALENTS.items() if t["star"] == star and t["trait"] is None]


def talent_name(tkey, key):
    return TALENTS[tkey]["name"].replace("{ability}", UNITS[key]["ability"]["name"])


# ------------------------------------------------------------------ items
# Items are bought whole in the armory (no components or recipes since November 2026: the owner asked
# for items bought directly, in rarity tiers of rising power). A unit holds up to MAX_ITEMS; an item can
# be taken off again (back to the item bench). `fx` keys are the plain stats and specials sim.py knows
# (flat ad, hp and mana are added; the rest as in traits).
#   1 Common     plain stats
#   2 Rare       a trick of its own and one stat
#   3 Epic       a stronger trick and two stats; emblems (the holder gains a trait) are Epic too
#   4 Legendary  artifacts (a trick no other item has, with stats), and the Crown (one more board place)
MAX_ITEMS = 3
RARITIES = {1: "Common", 2: "Rare", 3: "Epic", 4: "Legendary"}
ITEM_PRICE = {1: 2, 2: 4, 3: 6, 4: 9}
_S = {  # the stat lines items are built from
    "atk": {"ad": 12}, "spd": {"aspd_pct": 0.12}, "ap": {"ap": 15}, "mana": {"mana": 15},
    "arm": {"armor": 25}, "res": {"mr": 25}, "hp": {"hp": 180},
}
_COMMON = [
    ("sword", "Iron Sword", {"ad": 20}, "+20 attack."),
    ("bow", "Recurve Bow", {"aspd_pct": 0.2}, "+20% attack speed."),
    ("rod", "Oak Rod", {"ap": 25}, "+25 ability power."),
    ("tear", "Mana Tear", {"mana": 25}, "+25 starting mana."),
    ("vest", "Chain Vest", {"armor": 40}, "+40 armor."),
    ("cloak", "Warding Cloak", {"mr": 40}, "+40 magic resist."),
    ("belt", "Giant's Belt", {"hp": 300}, "+300 HP."),
]
# (key, name, rarity, stat lines, effect fx, text): the stat lines' numbers are added to the effect.
_TRICKS = [
    # rare: one stat line
    ("mana_edge", "Mana Edge", 2, ["atk"], {"mana_on_hit": 6}, "Each attack gives 6 more mana."),
    ("sunder_axe", "Sunder Axe", 2, ["atk"], {"shred": 30}, "Attacks strip 30 armor from the target for 3 s."),
    ("hexblade", "Hexblade", 2, ["atk"], {"omnivamp": 0.2}, "Heals for 20% of all the damage it does."),
    ("cleaver", "Titan Cleaver", 2, ["hp"], {"splash": 0.35}, "Attacks also hit enemies beside the target for 35%."),
    ("harp", "Quickcast Harp", 2, ["mana"], {"mana_on_hit": 4, "aspd_pct": 0.1}, "Faster attacks that give 4 more mana."),
    ("duel_guard", "Duelist's Guard", 2, ["spd"], {"dodge": 0.25}, "Dodges a quarter of attacks."),
    ("galeband", "Galeband", 2, ["spd"], {"chill_on_hit": 0.25}, "Attacks slow the target's attacks by 25% for 2 s."),
    ("giant_bane", "Giant's Bane", 2, ["spd"], {"pct_hit": 0.03}, "Attacks deal 3% of the target's max HP more."),
    ("spellward", "Spellward", 2, ["res"], {"spell_dr": 0.3, "shield": 150}, "Abilities do 30% less to it, and it starts with a 150 shield."),
    ("chalice", "Overflowing Chalice", 2, ["mana"], {"cast_share": 20}, "After casting, the two nearest allies get 20 mana."),
    ("frost_aegis", "Frost Aegis", 2, ["arm"], {"chill": 0.3}, "Whoever attacks it attacks 30% slower for 2 s."),
    ("mana_ward", "Mana Ward", 2, ["res"], {"team_mana": 20}, "Allies beside it start with 20 more mana."),
    ("twin_ward", "Twin Ward", 2, ["arm"], {"dr": 0.08, "shield": 200}, "Takes 8% less damage and starts with a 200 shield."),
    ("second_wind", "Second Wind", 2, ["hp"], {"regen": 0.02}, "Regrows 2% of its max HP every second."),
    # epic: two stat lines
    ("greatsword", "Executioner's Greatsword", 3, ["atk", "atk"], {"crit": 0.15, "critdmg": 0.2, "low_bonus": 0.25},
     "Crits more, and does 25% more damage to enemies below half HP."),
    ("ravager", "Ravager", 3, ["atk", "spd"], {"frenzy": 0.05}, "Each attack makes it 5% faster, up to 10 times."),
    ("spellblade", "Spellblade", 3, ["atk", "ap"], {"ability_crit": 1, "crit": 0.15}, "Its abilities can crit."),
    ("twin_bow", "Twin Bow", 3, ["spd", "spd"], {"multishot": 0.6}, "Each attack also strikes a second enemy near the target for 60%."),
    ("storm_rod", "Storm Rod", 3, ["spd", "ap"], {"every3": 110}, "Every third attack calls lightning down on three enemies (110 magic damage each)."),
    ("grimoire", "Grand Grimoire", 3, ["ap", "ap"], {"cast_grow_ap": 12}, "Each cast leaves it 12 ability power stronger for the rest of the fight."),
    ("archstaff", "Archmage Staff", 3, ["ap", "mana"], {"cast_mana": 25}, "After casting, starts again with 25 mana."),
    ("ember_mantle", "Ember Mantle", 3, ["ap", "arm"], {"aura": 0.012}, "Burns enemies beside it for 1.2% of their max HP a second."),
    ("lifebloom", "Lifebloom Staff", 3, ["ap", "hp"], {"cast_heal": 180}, "Each cast also heals the most hurt ally for 180."),
    ("bell", "Redemption Bell", 3, ["mana", "hp"], {"low_heal": 300}, "The first time it falls below half HP, heals allies within 2 hexes for 300."),
    ("bastion", "Bastion Plate", 3, ["arm", "arm"], {"taunt_start": 3, "dr": 0.08}, "Enemies within 3 hexes must attack it for the first 3 s; takes 8% less damage."),
    ("spiked_hide", "Spiked Hide", 3, ["arm", "hp"], {"thorns": 0.35}, "Attackers take 35% of their hit back as magic damage."),
    ("veil", "Veil of Stillness", 3, ["res", "res"], {"cc_immune": 1}, "Can't be stunned or swallowed."),
    ("colossus_belt", "Colossus Belt", 3, ["hp", "hp"], {"grow_hp": [0.02, 0.3]}, "Grows: 2% more max HP every second, up to 30%."),
]
# Artifacts (Legendary): tricks no other item has.
ARTIFACTS = [
    ("hourglass", "Stopped Hourglass", {"armor": 20, "mr": 20, "last_stand": [0.3, 2.0, 0.25]},
     "The first time it falls below 30% HP, it slips out of time for 2 s (nothing can reach it) and heals 25%."),
    ("soulreaver", "Soulreaver Scythe", {"ad": 20, "on_kill": [0.25, 0.2]},
     "Each kill makes it attack 25% faster for the rest of the fight and heals it 20%."),
    ("phoenix_feather", "Phoenix Feather", {"hp": 150, "revive": 0.5}, "The first time it falls, it rises with 50% HP."),
    ("warhorn", "Warhorn", {"hp": 150, "horn": [0.3, 6, 2]}, "At the start, allies within 2 hexes attack 30% faster for 6 s."),
    ("witherbloom", "Witherbloom Thorn", {"aspd_pct": 0.15, "wound_on_hit": 5}, "Its attacks halve the target's healing for 5 s."),
    ("echo_tome", "Echoing Tome", {"ap": 10, "echo": 0.5}, "Its ability goes off a second time, at half strength (not summons or moves)."),
    ("executioner", "Executioner's Edge", {"ad": 15, "execute": 0.15}, "Its attacks finish enemies below 15% HP."),
    ("world_seed", "Seed of the Elder Grove", {"hp": 200, "summon_every": ["sapling", 6]}, "Every 6 s, a sapling grows beside it and fights."),
    ("quicksilver", "Quicksilver Draught", {"mana": 200, "aspd_pct": 0.2}, "Starts the fight with full mana, and attacks 20% faster."),
]

# Relics (Legendary, kind "relic"): won only at the auction (AUCTION_ROUNDS), never in the armory or a draft.
RELICS = [
    ("mountain_heart", "Mountain's Heart", {"hp": 400, "armor": 30, "mr": 30, "taunt_start": 4},
     "Enemies within 3 hexes must attack it for the first 4 s."),
    ("star_blade", "Starforged Blade", {"ad": 35, "crit": 0.25, "critdmg": 0.35, "ability_crit": 1},
     "Crits often and hard, and its abilities can crit."),
    ("wellspring", "Wellspring Orb", {"ap": 40, "mana": 30, "cast_mana": 40, "cast_share": 20},
     "After casting, it starts again with 40 mana and the two nearest allies get 20."),
    ("twinfang", "Twinfang", {"aspd_pct": 0.3, "multishot": 0.7, "mana_on_hit": 4},
     "Each attack also strikes a second enemy near the target for 70%, and gives 4 more mana."),
]


def _sum_fx(*fxs):
    out = {}
    for fx in fxs:
        for k, v in fx.items():
            out[k] = list(v) if isinstance(v, list) else out.get(k, 0) + v
    return out


_STAT_TEXT = {"ad": "+{:g} attack", "aspd_pct": "+{:g}% attack speed", "ap": "+{:g} ability power",
              "mana": "+{:g} mana", "armor": "+{:g} armor", "mr": "+{:g} magic resist", "hp": "+{:g} HP"}
ITEMS = {}
for _k, _name, _fx, _text in _COMMON:
    ITEMS[_k] = {"name": _name, "kind": "item", "rarity": 1, "fx": dict(_fx), "text": _text}
for _k, _name, _r, _lines, _fx, _text in _TRICKS:
    _stats = _sum_fx(*[_S[x] for x in _lines])
    ITEMS[_k] = {"name": _name, "kind": "item", "rarity": _r, "fx": _sum_fx(_stats, _fx), "text": _text,
                 "stats": ", ".join(_STAT_TEXT[n].format(v * 100 if n == "aspd_pct" else v) for n, v in _stats.items())}
for _k, _name, _fx, _text in ARTIFACTS:
    ITEMS[_k] = {"name": _name, "kind": "artifact", "rarity": 4, "fx": dict(_fx), "text": _text}
for _k, _name, _fx, _text in RELICS:
    ITEMS[_k] = {"name": _name, "kind": "relic", "rarity": 4, "fx": dict(_fx), "text": _text}
for _t in TRAITS:  # every trait has an emblem
    ITEMS["emblem_" + _t] = {"name": TRAITS[_t]["name"] + " Emblem", "kind": "emblem", "rarity": 3, "trait": _t,
                             "fx": {"hp": 150}, "text": f"Its holder is also {TRAITS[_t]['name']}.", "stats": "+150 HP"}
ITEMS["crown"] = {"name": "Crown", "kind": "crown", "rarity": 4, "fx": {"hp": 160}, "stats": "+160 HP",
                  "text": "One more unit may stand on your board while its holder does."}


def items_of(rarity, kinds=None):
    """Item keys of a rarity (and of the given kinds)."""
    return [k for k, i in ITEMS.items() if i["rarity"] == rarity and (kinds is None or i["kind"] in kinds)]


def artifacts():
    return items_of(4, ("artifact",))


# The armory: items bought whole, beside the unit shop (the owner asked for items in the shop in
# November 2026, then for whole items in rarity tiers). Each round it offers ARMORY_SIZE items, each slot's
# rarity drawn by ARMORY_ODDS for the round (repeats allowed); within Epic an emblem one time in
# EMBLEM_SHARE, within Legendary a Crown one time in CROWN_SHARE. It restocks each new round (rerolls
# don't touch it), a locked shop keeps it, and a bought slot stays empty until the next round.
ARMORY_SIZE = 4
ARMORY_ODDS = [  # (from round, % for Common, Rare, Epic, Legendary)
    (1, (70, 30, 0, 0)),
    (4, (40, 45, 15, 0)),
    (8, (20, 45, 30, 5)),
    (12, (5, 35, 45, 15)),
    (16, (0, 25, 50, 25)),
]
EMBLEM_SHARE = 4
CROWN_SHARE = 8


def armory_odds(rnd):
    return next(odds for start, odds in reversed(ARMORY_ODDS) if rnd >= start)


# ------------------------------------------------------------------ commanders
# Each player picks one of three at the start: a passive, and a power that charges over `charge`
# rounds and is used during planning. game.py does what they say.
COMMANDERS = {
    "quartermaster": {"name": "The Quartermaster", "passive": "Your shop has six slots.",
                      "power": "Three free rerolls.", "charge": 3},
    "warlord": {"name": "The Warlord", "passive": "Units on your front row have 12% more HP. Each time one falls, "
                                                  "the rest of your units attack 10% faster.",
                "power": "Next fight, every unit of yours starts with a 300 shield.", "charge": 4},
    "necromancer": {"name": "The Necromancer", "passive": "The first of your units to die each fight rises with 40% HP.",
                    "power": "Raise a random tier-2 unit onto your bench.", "charge": 4},
    "alchemist": {"name": "The Alchemist", "passive": "A free Rare item at rounds 5, 10 and 15.",
                  "power": "Brew a random Rare item.", "charge": 4},
    "merchant": {"name": "The Merchant", "passive": "Interest goes up to 7 gold instead of 5.",
                 "power": "Gain 4 gold.", "charge": 3},
    "sage": {"name": "The Sage", "passive": "One more XP every other round.", "power": "Gain 5 XP.", "charge": 4},
    "beastmaster": {"name": "The Beastmaster", "passive": "Your summons have 40% more HP and attack.",
                    "power": "Next fight, a Treant (at your highest star) fights for you.", "charge": 2},
    "archmage": {"name": "The Archmage", "passive": "Each of your units' first ability in a fight echoes: it goes off "
                                                    "again at half strength.",
                 "power": "Next fight, every unit of yours starts with 40 more mana.", "charge": 3},
    "survivor": {"name": "The Survivor", "passive": "You lose 15% less HP when you lose a fight, and below 25 HP "
                                                    "your units have 15% more HP.",
                 "power": "Heal 6 HP.", "charge": 5},
    "blademaster": {"name": "The Blademaster", "passive": "Each attack your units make speeds them up 2%, up to 20%.",
                    "power": "Next fight, your units attack 40% faster for the first 6 s.", "charge": 3},
    "forgemaster": {"name": "The Forgemaster", "passive": "Start with a Common item, and the armory sells you "
                                                          "everything for 1 gold less.",
                    "power": "Forge a random Epic item (one time in four, a Legendary artifact).", "charge": 5},
    "oracle": {"name": "The Oracle", "passive": "From level 5, your shop rolls as if you were a level higher.",
               "power": "A free reroll that favours units you already own.", "charge": 2},
    # added in the roster review (November 2026)
    "gambler": {"name": "The Gambler", "passive": "Your first reroll each round costs 1 gold instead of 2.",
                "power": "Roll the bones: gain 1 to 8 gold.", "charge": 3},
    "hexer": {"name": "The Hexer", "passive": "Each fight, the enemy's best unit (most stars, then price) is hexed: "
                                              "it takes 30% more damage.",
              "power": "Next fight, every enemy unit is hexed too (25% more damage) for the first 10 s.", "charge": 2},
    "chronomancer": {"name": "The Chronomancer", "passive": "Your units start fights with 20 more mana.",
                     "power": "Next fight, the enemy's units start with no mana, and gain it half as fast for 8 s.",
                     "charge": 4},
    "twinmaker": {"name": "The Twinmaker", "passive": "Each round's first shop has at least one unit you already own, "
                                                      "when the pool has one.",
                  "power": "Twin the 1-star unit you have most copies of (the copy comes from the pool).", "charge": 6},
}
COMMANDER_CHOICES = 3

# ------------------------------------------------------------------ augments
# One of three at AUGMENT_ROUNDS (one free reroll each time). All three offered are the same tier
# (1 lesser, 2 greater, 3 grand), drawn by AUGMENT_TIER_ODDS. game.py does what they say: `gold`,
# `xp`, `items` (a random item of each rarity listed), `units` (random of a tier), `heal` (HP), `team`
# (fx for all your units in every fight), `bonus` (+n to a trait you field), `emblem` (that trait's
# emblem item), `interest` (more interest cap), `revive_first` (the first of your units to die each
# fight rises with that share of HP), `crown` (a Crown item).
AUGMENT_ROUNDS = (3, 8, 13)
AUGMENT_TIER_ODDS = {3: (60, 35, 5), 8: (20, 60, 20), 13: (5, 40, 55)}
AUGMENT_TIER_NAMES = {1: "Lesser", 2: "Greater", 3: "Grand", 4: "Auction"}
AUGMENTS = {
    # lesser
    "pocket_change": {"tier": 1, "name": "Pocket Change", "text": "Gain 6 gold.", "gold": 6},
    "study": {"tier": 1, "name": "Late-Night Study", "text": "Gain 8 XP.", "xp": 8},
    "spare_parts": {"tier": 1, "name": "Spare Parts", "text": "Gain a random Rare item.", "items": [2]},
    "recruits": {"tier": 1, "name": "Fresh Recruits", "text": "Gain two random tier-1 units.", "units": [1, 1]},
    "thick_skin": {"tier": 1, "name": "Thick Skin", "text": "Heal 8 HP.", "heal": 8},
    "whetstone": {"tier": 1, "name": "Whetstone", "text": "Your units have 8 more attack.", "team": {"ad": 8}},
    # greater
    "treasure": {"tier": 2, "name": "Buried Treasure", "text": "Gain 15 gold.", "gold": 15},
    "armory": {"tier": 2, "name": "Armory", "text": "Gain a random Epic item.", "items": [3]},
    "fast_track": {"tier": 2, "name": "Fast Track", "text": "Gain 14 XP.", "xp": 14},
    "battle_hardened": {"tier": 2, "name": "Battle Hardened", "text": "Your units have 120 more HP.", "team": {"hp": 120}},
    "rich": {"tier": 2, "name": "Rich Get Richer", "text": "Gain 6 gold; interest goes 2 higher.", "gold": 6, "interest": 2},
    "second_life": {"tier": 2, "name": "Second Life", "text": "The first of your units to die each fight rises with 30% HP.",
                    "revive_first": 0.3},
    # grand
    "hoard": {"tier": 3, "name": "Dragon's Hoard", "text": "Gain 30 gold.", "gold": 30},
    "arsenal": {"tier": 3, "name": "Arsenal", "text": "Gain two random Epic items.", "items": [3, 3]},
    "crowned": {"tier": 3, "name": "Crowned", "text": "Gain a Crown: one more unit on your board.", "crown": 1},
    "titanic": {"tier": 3, "name": "Titanic Strength", "text": "Your units have 12% more HP and 10 more attack.",
                "team": {"hp_pct": 0.12, "ad": 10}},
    "ancient_armory": {"tier": 3, "name": "Ancient Armory", "text": "Gain a random Legendary artifact.",
                       "artifacts": 1},
    "relic_hunter": {"tier": 2, "name": "Relic Hunter", "text": "Gain a random Legendary artifact; lose 6 HP.",
                     "artifacts": 1, "heal": -6},
    # build-arounds (the owner asked for Guildrun-style ones, November 2026): they grow with the board you
    # build (`per`: so much for each unit counted; `when`: once a condition holds; `stars`: units of at
    # least that star; `convert`: one stat turned into another at a fight's start). Player.extras works
    # them out each fight, so the unit cards show them.
    "kinship": {"tier": 1, "name": "Kinship", "text": "Your units have 25 more HP for each unit of your "
                "most common origin you field.", "per": {"count": "kin", "fx": {"hp": 25}}},
    "spellweave": {"tier": 2, "name": "Spellweave", "text": "Your units have 10 more ability power for each "
                   "Arcanist, Mystic and Summoner you field.",
                   "per": {"count": "units:arcanist,mystic,summoner", "fx": {"ap": 10}}},
    "bladework": {"tier": 2, "name": "Bladework", "text": "Your units attack 3% faster for each Duelist, "
                  "Ranger and Assassin you field.",
                  "per": {"count": "units:duelist,ranger,assassin", "fx": {"aspd_pct": 0.03}}},
    "shield_wall": {"tier": 2, "name": "Shield Wall", "text": "Your front row has 8 armor and magic resist "
                    "for each unit standing on it.", "per": {"count": "front", "fx": {"armor": 8, "mr": 8},
                                                             "front": True}},
    "war_chest": {"tier": 2, "name": "War Chest", "text": "When a fight starts, your units have 1 more attack "
                  "for every 3 gold you hold (up to 20).", "per": {"count": "gold:3", "fx": {"ad": 1}, "max": 20}},
    "melting_pot": {"tier": 3, "name": "Melting Pot", "text": "If you field units of five or more different "
                    "origins, your units have 15% more HP and attack 15% faster.",
                    "when": {"origins": 5, "fx": {"hp_pct": 0.15, "aspd_pct": 0.15}}},
    "elite_guard": {"tier": 3, "name": "Elite Guard", "text": "Your units of two stars or more have 15% more HP "
                    "and 15 more attack.", "stars": {"min": 2, "fx": {"hp_pct": 0.15, "ad": 15}}},
    "giants_heart": {"tier": 3, "name": "Giant's Heart", "text": "Every 200 max HP a unit has beyond its own "
                     "becomes 20 attack.", "convert": {"hp_to_ad": [200, 20]}},
    "runeplate": {"tier": 3, "name": "Runeplate", "text": "Armor and magic resist your units have beyond "
                  "their own become ability power (1 for every 2).", "convert": {"res_to_ap": 0.5}},
    "quickening": {"tier": 3, "name": "Quickening", "text": "Every 10% attack speed a unit has beyond its own "
                   "gives it 2 mana a second.", "convert": {"aspd_to_mana": 20}},
    # auction only (tier 4: never offered at AUGMENT_ROUNDS)
    "legion": {"tier": 4, "name": "Legion", "text": "One more unit may stand on your board, for the rest of "
               "the match.", "slots": 1},
    "war_banner": {"tier": 4, "name": "War Banner", "text": "Your units have 10% more HP and attack 10% faster.",
                   "team": {"hp_pct": 0.1, "aspd_pct": 0.1}},
    "ancestral_echo": {"tier": 4, "name": "Ancestral Echo", "text": "Each of your units' first ability in a "
                       "fight echoes: it goes off again at half strength.", "team": {"echo_first": 0.5}},
    "iron_will": {"tier": 4, "name": "Iron Will", "text": "Your front row can't be stunned or swallowed, and "
                  "starts each fight with a 300 shield.", "front": {"cc_immune": 1, "shield": 300}},
}
for _t, _d in TRAITS.items():
    AUGMENTS["heart_" + _t] = {"tier": 1, "name": _d["name"] + " Heart", "trait": _t, "bonus": 1,
                               "text": f"Counts as one more {_d['name']} unit, if you field one."}
    AUGMENTS["crest_" + _t] = {"tier": 2, "name": _d["name"] + " Crest", "trait": _t, "emblem": _t,
                               "text": f"Gain {'an' if _d['name'][0] in 'AEIOU' else 'a'} {_d['name']} Emblem: "
                                       f"the unit holding it counts as {_d['name']} too."}
    AUGMENTS["soul_" + _t] = {"tier": 3, "name": _d["name"] + " Soul", "trait": _t, "bonus": 2,
                              "text": f"Counts as two more {_d['name']} units, if you field one."}
AUGMENT_CHOICES = 3

# ------------------------------------------------------------------ shared drafts
# At DRAFT_ROUNDS, before planning, everyone picks one unit (each holding an item) from a shared
# set, lowest HP first. DRAFT_TIERS: the tiers on offer that round.
DRAFT_ROUNDS = (4, 9, 14)
DRAFT_TIERS = {4: (1, 2), 9: (2, 3), 14: (3, 4)}
DRAFT_ITEM_RARITY = {4: 2, 9: 3, 14: 4}  # the rarity of the items the draft's units hold (14: artifacts)
DRAFT_TURN = 8  # seconds a person has for their pick
DRAFT_EXTRA = 2  # options beyond one each

# ------------------------------------------------------------------ the auction
# At AUCTION_ROUNDS (the monster rounds that close each act), before planning, three lots go under a
# sealed-bid auction: a two-star unit of AUCTION_UNIT's tier holding an item of its rarity, a relic (won
# nowhere else) and an auction augment (tier 4). Everyone bids on any of them at once, at least
# AUCTION_MIN each, each bid no more than their gold (as nobody wins more than one lot, they never pay
# two: until late November 2026 the bids together had to fit, and the augment went unsold half the time);
# the highest bid of all takes its lot and pays what it bid (ties to the lower HP), and so on down,
# nobody winning more than one lot (so saving up can't buy the lot). AUCTION_TIME seconds, or until
# every person has bid.
AUCTION_ROUNDS = (6, 11)
AUCTION_UNIT = {6: (3, 3), 11: (4, 4)}  # round: (unit tier, item rarity)
AUCTION_MIN = 3
AUCTION_LOT_MIN = {"legion": 10}  # lots with a higher reserve than AUCTION_MIN (by augment)
AUCTION_TIME = 25


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
