"""Criticals: an action whose die lands on its top face (a 6 on a d6, an 8 on a d8; a d10 or bigger
on its top two faces; a wild face, or anything pushed past the top, counts too) also does its crit. Shield and skull faces never crit.

`CRITS[key] = (ops, card line, sentence)`: the extra ops run after the action's own when it hits and
crits (Combat.act); the card line is what the action card shows after "Crit:", and the sentence ends
the action's text. Importing this module writes them onto the actions (`crit`, `crit_short`, and the
text), the way items.py merges PASSIVES.
"""
from . import classes as C
from .content import items as I

CRITS = {
    # ---- for everyone
    "block": ([{"op": "armor", "amt": "2"}], "+2 Armor", "gain 2 more Armor"),

    # ---- each class's basic
    "strike": ([{"op": "armor", "amt": "3", "to": "self"}], "+3 Armor", "you also gain 3 Armor"),
    "brace": ([{"op": "armor", "amt": "3", "to": "lowest"}], "the weakest ally +3 more", "your weakest ally gains 3 more"),
    "bolt": ([{"op": "status", "s": "shock", "n": "1"}], "Shock", "Shock the enemy (its next hit also hits a neighbour)"),
    "slash_d": ([{"op": "dmg", "amt": "v"}, {"op": "armor", "amt": "3", "to": "self"}], "strike again · +3 Armor",
                "strike again for the die, and gain 3 Armor"),
    "hack_b": ([{"op": "dmg", "amt": "v//2"}, {"op": "heal", "amt": "5", "to": "self"}], "hit again for ½ die · heal 5",
               "hit again for half the die, and heal 5"),
    "shoot_r": ([{"op": "dmg", "amt": "v", "to": "another"}], "the die to another enemy", "the arrow carries on: the die to another enemy"),
    "stab": ([{"op": "status", "s": "poison", "n": "1"}], "Poison 1", "Poison it for 1"),
    "jab": ([{"op": "status", "s": "mark", "n": "1"}], "Mark", "Mark it (every hit on it deals +3)"),
    "rebuke": ([{"op": "heal", "amt": "3", "to": "lowest"}], "weakest ally heals 3", "your weakest ally heals 3"),
    "toss": ([{"op": "status", "s": "burn", "n": "2"}], "Burn 2", "Burn it for 2"),
    "thornlash": ([{"op": "status", "s": "root", "n": "1", "to": "another"}], "Root another enemy", "the vines spread: Root another enemy"),
    "rune_cut": ([{"op": "carve", "n": 2}], "carve 2 more", "carve 2 more Sigils"),
    "searing_strike": ([{"op": "heat", "amt": "5"}], "+5 Heat", "add 5 Heat"),
    "claw": ([{"op": "status", "s": "poison", "n": "1"}], "Poison 1", "the wound festers: Poison 1"),
    "mind_spike": ([{"op": "status", "s": "weak", "n": "1"}], "Weak", "its mind reels: Weak"),

    # ---- the Spellblade's Burst: a crit infuses the blade
    "sigil_burst": ([{"op": "infuse", "n": 2, "amt": "v//2"}], "infuse 2 melee hits", "the blade drinks it in: your next two melee hits this round deal +half the die and carry its element"),

    # ---- weapon actions
    "hack": ([{"op": "dmg", "amt": "3"}], "hit again for 3", "hit again for 3"),
    "zap": ([{"op": "dmg", "amt": "v", "to": "another"}], "arc: the die to another", "it arcs: the die to another enemy"),
    "flare": ([{"op": "status", "s": "mark", "n": 1, "to": "another"}], "Mark another", "the light spreads: Mark another enemy too"),
    "thrust": ([{"op": "dmg", "amt": "3"}], "hit again for 3", "hit again for 3"),
    "harpoon": ([{"op": "dmg", "amt": "3"}], "3 more", "the barb tears: 3 more"),
    "shoot": ([{"op": "dmg", "amt": "4"}], "hit again for 4", "hit again for 4"),
    "slash": ([{"op": "status", "s": "poison", "n": "2"}], "bleed: Poison 2", "it bleeds: Poison 2"),
    "crush": ([{"op": "status", "s": "weak", "n": "1"}], "Weak", "it reels: Weak"),
    "sweep": ([{"op": "dmg", "amt": "2"}], "+2 to each", "each enemy hit takes 2 more"),
    "tidal": ([{"op": "status", "s": "weak", "n": "1"}], "every enemy Weak", "every enemy is Weak"),
    "storm_bolt": ([{"op": "status", "s": "shock", "n": 1}], "Shock it", "the storm clings: Shock it again"),
    "venom_stab": ([{"op": "status", "s": "poison", "n": "1"}], "Poison +1", "Poison it for 1 more"),
    "blessing": ([{"op": "heal", "amt": "3"}], "heal 3 more", "heal 3 more"),
    "good_luck": ([{"op": "heal", "amt": "3"}], "heal 3", "and they heal 3"),
    "pearls_calm": ([{"op": "armor", "amt": "3"}], "+3 Armor", "they gain 3 Armor"),
    "salt_ward": ([{"op": "armor", "amt": "3"}], "+3 Armor", "they gain 3 more Armor"),
    "rally_crew": ([{"op": "cue", "amt": "2", "to": "others"}], "their hits +2 more", "their next hits deal 2 more"),
    "featherlight": ([{"op": "armor", "amt": "3"}], "+3 Armor", "they gain 3 Armor"),
    "resonate": ([{"op": "cue", "amt": "3"}], "next hit +3", "their next hit deals 3 more too"),
    "lullaby": ([{"op": "heal", "amt": "2", "to": "party"}], "party heals 2", "everyone heals 2"),
    "cool_water": ([{"op": "heal", "amt": "2"}], "heal 2 more", "everyone heals 2 more"),
    "hone_edge": ([{"op": "cue", "amt": "3"}], "+3 more", "their next hit deals 3 more"),
    "rally_call": ([{"op": "armor", "amt": "2", "to": "others"}], "allies +2 Armor", "every ally gains 2 Armor"),
    "bind_wounds": ([{"op": "heal", "amt": "3"}], "heal 3 more", "heal 3 more"),
    "lash_together": ([{"op": "armor", "amt": "3"}], "ally +3 more", "your ally gains 3 more Armor"),
    "flash": ([{"op": "status", "s": "weak", "n": 1}], "Weak", "blinded: it's Weak"),
    "warm_hands": ([{"op": "heal", "amt": "3"}], "they heal 3", "they heal 3"),
    "benediction_bead": ([{"op": "heal", "amt": "3"}], "heal 3 more", "they heal 3 more"),
    "challenge": ([{"op": "armor", "amt": "3", "to": "self"}], "+3 Armor", "you also gain 3 Armor"),
    "skewer": ([{"op": "dmg", "amt": "3"}], "3 more", "it twists: 3 more"),
    "snag": ([{"op": "armor", "amt": "3", "to": "self"}], "+3 Armor", "you gain 3 more Armor"),
    "open_wound": ([{"op": "status", "s": "wound", "n": 1}], "deeper wound", "cut deeper: the wound grows by 1 more"),
    "point_blank": ([{"op": "status", "s": "burn", "n": 2}], "Burn 2", "powder burns: Burn it for 2"),
    "turnabout": ([{"op": "dmg", "amt": "3"}], "3 more", "luck turns: 3 more"),
    "last_shot": ([{"op": "dmg", "amt": "v"}], "the die again", "a second ball: the die again"),
    "tether": ([{"op": "armor", "amt": "3"}], "ally +3 Armor", "your ally gains 3 more Armor"),
    "magnetize": ([{"op": "status", "s": "root", "n": 1}], "Root", "it sticks fast: Root it"),
    "set_pike": ([{"op": "armor", "amt": "3", "to": "self"}], "+3 Armor", "you also gain 3 Armor"),
    "borrowed_time": ([{"op": "dmg", "amt": "v-v//2"}], "the full die", "deal the full die instead"),
    "mummify": ([{"op": "status", "s": "poison", "n": 2}], "Poison 2", "grave rot: Poison it for 2"),
    "sleep_dart": ([{"op": "status", "s": "poison", "n": 2}], "Poison 2", "a venomed dart: Poison it for 2"),
    "thorn_snare": ([{"op": "status", "s": "poison", "n": 2}], "Poison 2", "venomous thorns: Poison it for 2"),
    "judgment": ([{"op": "heal", "amt": "3", "to": "self"}], "heal 3", "righteous: heal 3"),
    "lifebinding": ([{"op": "heal", "amt": "3", "to": "lowest"}], "weakest ally heals 3 more", "your weakest ally heals 3 more"),
    "splinter": ([{"op": "dmg", "amt": "2", "to": "another"}], "a shard: 2 to another", "a shard flies: 2 to another enemy"),
    "mirror": ([{"op": "armor", "amt": "3", "to": "self"}], "+3 Armor", "you gain 3 Armor"),
    "sleep_thread": ([{"op": "status", "s": "weak", "n": 1}], "Weak", "it dreams badly: Weak"),
    "icefall": ([{"op": "status", "s": "freeze", "n": 1}], "Freeze", "Freeze it"),
    "rime_guard": ([{"op": "armor", "amt": "3", "to": "self"}], "+3 Armor", "you gain 3 more Armor"),
    "searbrand": ([{"op": "status", "s": "burn", "n": 2}], "Burn 2 more", "the brand bites: Burn it for 2 more"),
    "rake": ([{"op": "dmg", "amt": "v//2+1"}], "a third hit", "rake it a third time"),
    "kindle": ([{"op": "status", "s": "shock", "n": 1}], "Shock", "Shock it"),
    "tend_grove": ([{"op": "status", "s": "root", "n": 1}], "Root", "the roots take it: Root it"),
    "foresight": ([{"op": "status", "s": "weak", "n": 1}], "Weak", "you see the flaw: it's Weak"),
    "riptide": ([{"op": "dmg", "amt": "3"}], "3 more", "the undertow: 3 more"),
    "rallying_cut": ([{"op": "armor", "amt": "2", "to": "party"}], "party +2 Armor", "the whole party gains 2 Armor"),
    "flashpoint": ([{"op": "status", "s": "burn", "n": 2, "to": "another"}], "Burn another 2", "the blaze leaps: Burn another enemy for 2"),
    "ancestral_guard": ([{"op": "armor", "amt": "3", "to": "self"}], "+3 Armor", "gain 3 more Armor"),
    "disarm": ([{"op": "dmg", "amt": "3"}], "3 more", "3 more"),
    "reaping_arc": ([{"op": "dmg", "amt": "2"}], "+2 to each", "each enemy hit takes 2 more"),
    "vanish": ([{"op": "status", "s": "dodge", "n": 1, "to": "self"}], "the next hit misses", "the next hit on you misses"),
    "shatter": ([{"op": "status", "s": "freeze", "n": 1}], "Freeze", "it ices over again: Freeze it"),
    "royal_decree": ([{"op": "dmg", "amt": "2", "if": "low"}], "+2 to each", "each of them takes 2 more"),
    "choking_kelp": ([{"op": "status", "s": "poison", "n": 2}], "Poison 2", "Poison it for 2"),
    "thunderhead": ([{"op": "dmg", "amt": "2", "to": "foes"}], "all take 2", "lightning: every enemy takes 2"),
    "ricochet": ([{"op": "dmg", "amt": "v//2", "to": "another"}], "a third bounce", "it bounces again: half the die to another enemy"),
    "cinder_rain": ([{"op": "status", "s": "burn", "n": 1}], "Burn +1 each", "every enemy Burns 1 more"),
    "sand_eyes": ([{"op": "status", "s": "vuln", "n": 1}], "Vulnerable", "it's Vulnerable too"),
    "prism_shield": ([{"op": "armor", "amt": "3"}], "+3 Armor", "they gain 3 more Armor"),
    "nightmare": ([{"op": "status", "s": "weak", "n": 1}], "Weak", "it wakes shaken: Weak"),
    "cinder": ([{"op": "status", "s": "burn", "n": 2, "to": "another"}], "Burn another 2", "the fire leaps: Burn another enemy for 2"),
    "sandwind": ([{"op": "dmg", "amt": "2"}], "+2 to each", "each enemy takes 2 more"),
    "stonebolt": ([{"op": "dmg", "amt": "3"}], "3 more", "it cracks: 3 more"),
    "vinelash": ([{"op": "status", "s": "poison", "n": 2}], "Poison 2", "the thorns are venomous: Poison it for 2"),
    "radiant": ([{"op": "heal", "amt": "2", "to": "party"}], "party heals 2 more", "everyone heals 2 more"),
    "prism_ray": ([{"op": "status", "s": "mark", "n": 1}], "Mark", "the light pins it: Mark it"),
    "lull": ([{"op": "status", "s": "weak", "n": 1, "to": "another"}], "another Weak", "the lull spreads: another enemy is Weak"),
    "glacial": ([{"op": "dmg", "amt": "3"}], "3 more", "the ice shatters: 3 more"),

    # ---- armor actions (they take Block's place)
    "hunker": ([{"op": "armor", "amt": "3"}], "+3 Armor", "gain 3 more Armor"),
    "patch_up": ([{"op": "heal", "amt": "3", "to": "self"}], "heal 3 more", "heal 3 more"),
    "coral_growth": ([{"op": "armor", "amt": "3"}], "+3 Armor", "gain 3 more Armor"),
    "bristle": ([{"op": "status", "s": "thorns", "n": "5", "to": "self"}], "they take 5", "enemies that hit you take 5 instead"),
    "sidestep": ([{"op": "status", "s": "dodge", "n": "1", "to": "self"}], "the next hit misses", "the next hit on you misses"),
    "echo_shell": ([{"op": "weaken", "amt": "2", "to": "aiming"}], "they drop by 4", "every attack aimed at you drops by 4 instead"),
    "cover": ([{"op": "armor", "amt": "v", "to": "self"}], "you gain it too", "you gain the die as Armor too"),
    "tidewall": ([{"op": "armor", "amt": "2", "to": "party"}], "the party +2 more", "the whole party gains 2 more"),
    "stoneform": ([{"op": "armor", "amt": "3"}], "+3 Armor", "gain 3 more Armor"),
    "hold_fast": ([{"op": "armor", "amt": "3"}], "+3 Armor", "gain 3 more Armor"),
    "unmoving_wall": ([{"op": "armor", "amt": "2", "to": "others"}], "allies +2 Armor", "every ally gains 2 Armor"),
    "heartwood": ([{"op": "heal", "amt": "3", "to": "party"}], "party heals 3", "everyone heals 3"),
    "crown_smash": ([{"op": "dmg", "amt": "v"}], "the die again", "the crown breaks: the die again"),
    "drowned_tithe": ([{"op": "heal", "amt": "4", "to": "self"}], "the tithe returns", "the deep pays you back: heal 4"),
    "turn_the_glass": ([{"op": "armor", "amt": "3", "to": "party"}], "party +3 Armor", "everyone gains 3 Armor"),
    "dawnbreak": ([{"op": "armor", "amt": "2", "to": "party"}], "party +2 Armor", "everyone gains 2 Armor too"),
    "northern_lights": ([{"op": "dmg", "amt": "v", "to": "foes"}], "all take the die", "every enemy takes the die"),
    "rekindle": ([{"op": "status", "s": "burn", "n": 2, "to": "foes"}], "Burn 2 more", "every enemy Burns 2 more"),
    "winters_heart": ([{"op": "dmg", "amt": "v"}], "the die again", "it shatters: the die again"),
    "batten_down": ([{"op": "heal", "amt": "3", "to": "self"}], "heal 3", "heal 3"),
    "fade": ([{"op": "status", "s": "dodge", "n": 1, "to": "self"}], "the next hit misses", "the next hit on you misses"),
    "riposte_stance": ([{"op": "status", "s": "thorns", "n": 3, "to": "self"}], "attackers take 3", "enemies that hit you this round take 3"),
    "second_wind": ([{"op": "heal", "amt": "3", "to": "self"}], "heal 3", "heal 3 more"),
    "warding_light": ([{"op": "heal", "amt": "3", "to": "lowest"}], "weakest ally heals 3 more", "your weakest ally heals 3 more"),
    "shell_up": ([{"op": "armor", "amt": "3"}], "+3 Armor", "gain 3 more Armor"),
    "deflect": ([{"op": "weaken", "amt": "2", "to": "biggest"}], "it drops 2 more", "the biggest attack drops by 2 more"),
}

for _k, (_ops, _short, _say) in CRITS.items():
    _a = C.ACTIONS.get(_k) or I.WEAPON_ACTIONS[_k]
    if "crit" in _a:
        continue  # already written (a second import)
    _a["crit"] = _ops
    _a["crit_short"] = _short
    _a["text"] = f"{_a['text']} Crit: {_say}."


def crit_floor(faces):
    """The lowest number that crits on a die: its top face, or on a d10 or bigger its top two (so a big
    die crits about as often as a small one)."""
    nums = {int(f[1:]) if isinstance(f, str) else f for f in faces if isinstance(f, int) or (isinstance(f, str) and f[:1] in "FIP")}
    if not nums:
        return 10 ** 9
    nums = sorted(nums, reverse=True)
    return nums[1] if len(faces) >= 10 and len(nums) > 1 else nums[0]


def is_crit(d):
    """Whether a rolled die crits: it landed on its top face (a d10 or bigger: its top two), or past
    it; a wild face does; shields and skulls don't."""
    t = d.get("tag")
    if t in ("S", "X") or d.get("v") is None:
        return False
    return t == "W" or d["v"] >= crit_floor(d["faces"])
