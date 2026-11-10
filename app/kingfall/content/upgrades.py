"""Upgrades: what a hero picks at each Bonfire. Most belong to one of six Vows and attach to one slot
(light, heavy, special, dodge, guard): a slot holds one, and taking another replaces it, so picking
means choosing. Passives have no slot. Pacts only appear with two or more heroes. Duos appear once a
hero holds upgrades from both of their Vows. Weapon Arts reshape one weapon.

An upgrade is a list of effects (`fx`), each a dict with a type `t`. The server works them all out
(hero.Build); the browser only gets the stats that change how a hero moves (`client_stats`).
Numbers marked in `scale` grow with rarity (rare x1.5, epic x2). `{v}` in the text is the first one.

Effect types:
  dmg      {slot, mult}            damage of that slot ('all' for every attack, 'skill' for skills) x mult
  poise    {slot, mult}
  status   {slot, kind, amt}       build a status on the boss per hit (burn, frost, bleed, rot)
  stat     {key, add|mult}         mhp, speed, focus_gain, special_cost, reach, flasks, heal, iframes,
                                   revive_time, dash_regen (dashes come back x mult faster), dash_time
                                   (the seconds a dash takes to come back x mult), dash_charges, block_cost
                                   (the share of a dash a blocked hit uses x mult), skill_cd
                                   (cooldowns x mult), skill_focus (Focus gained on using a skill)
  skillheal {amt}                  using a skill heals you amt
  skillward {amt}                  using a skill wards you against the next amt damage
  lowhp    {mult}                  all damage x mult while below half health
  steal    {slot, frac}            heal by frac of that slot's damage
  chain    {every, dmg}            every Nth light hit adds dmg (lightning)
  crit     {mult}                  critical hits (on a staggered boss) x mult
  perfect  {dash, dmg, heal}       a dodge that iframes through a hit gives back `dash` of a dash; the next hit
                                   within 2 s deals dmg more; heals heal
  parry    {mult}                  the next hit after a parry x mult
  dodge    {kind, amt}             rolling past the boss (within 50 px) builds a status
  near     {mult}                  damage x mult while an ally is within 90 px
  flaskall {frac}                  your flask also heals allies within 70 px by frac of yours
  revive   {free, shield, fast}    reviving costs no health / the revived get a shield / quicker
  ondown   {mult, dur}             when an ally goes down, your damage x mult for dur seconds
  proc     {when, pow, ...}        an extra attack the browser looses (hero.js, `proc`) when something happens:
                                   `when` is finisher (the light combo's last hit), heavy, heavy_full (fully
                                   charged), roll_end, guard (a block, parry or counter; `cd` s apart), perfect
                                   (a roll through a hit) or flask. It is a `proj` or an `aoe` as in weapons.py
                                   (an aoe's `mid`: centred halfway back along the roll). Damage is pow x 20
                                   whatever the weapon (as skills); `poise`; `kind` + `amt` build a status.
                                   The server prices it (atk 'proc', p the upgrade's id).
  ramp     {mult}                  each hit of a light combo deals this much more than the one before
  burstheal {kind, amt}            heal amt when that status bursts on the boss
  unbowed  {amt}                   once a fight, a hit that would down you leaves you on amt health
  stat keys the browser acts on:   light_speed (light attacks play faster), roll_haste (speed for 2 s after
                                   a roll), light_pierce (light arrows pierce), light_shots (extra bolts a cast)
"""

RARITY = {"common": 1.0, "rare": 1.5, "epic": 2.0}
SLOTS = ("light", "heavy", "special", "dodge", "guard")
VOWS = {
    "ember": {"name": "Ember", "colour": "#ff7a1a", "blurb": "Burn and blast."},
    "rime": {"name": "Rime", "colour": "#7fe3ff", "blurb": "Frost that slows and shatters."},
    "blood": {"name": "Blood", "colour": "#c83a4a", "blurb": "Bleed, and drink it back."},
    "storm": {"name": "Storm", "colour": "#c8b4ff", "blurb": "Chains of lightning, quick feet."},
    "rot": {"name": "Rot", "colour": "#8be04e", "blurb": "Poison that eats poise."},
    "iron": {"name": "Iron", "colour": "#b8c0cc", "blurb": "Poise, guard and stubbornness."},
}
UPGRADES = {}


def U(uid, name, vow, slot, text, fx, scale=(), weapon=None, needs=None, pact=False, req=None):
    UPGRADES[uid] = {"id": uid, "name": name, "vow": vow, "slot": slot, "text": text, "fx": fx, "scale": list(scale),
                     "weapon": weapon, "needs": needs, "pact": pact, "req": req}


def usable(u, weapon):
    """Can a hero holding `weapon` make any use of upgrade u? Only those are offered. `req`: "block"
    (the sword's and greatsword's guard, which also parries), "guard" (a block or the halberd's counter),
    "roll" (an ordinary roll, not the daggers' dash or the catalyst's blink), "melee" (swings with reach)."""
    from .weapons import WEAPONS
    g = WEAPONS[weapon]["guard"]["kind"]
    return {None: True, "block": g == "block", "guard": g in ("block", "counter"), "roll": g not in ("dash", "blink"),
            "melee": weapon not in ("bow", "catalyst")}[u["req"]]


# ------------------------------------------------------------------ Ember
U("ember_light", "Kindling Edge", "ember", "light", "The last hit of your light combo throws a wave of fire ({v} damage) that passes through everything and builds Burn.",
  [{"t": "proc", "when": "finisher", "pow": 1.0, "poise": 6, "kind": "burn", "amt": 30, "proj": {"v": 300, "r": 11, "life": 0.5, "pierce": True, "col": "#ff8a3a"}}], ["pow", "amt"])
U("ember_heavy", "Pyre Strike", "ember", "heavy", "A fully charged heavy erupts where it lands: a blast of {v} damage that builds Burn.",
  [{"t": "proc", "when": "heavy_full", "pow": 1.6, "poise": 10, "kind": "burn", "amt": 45, "aoe": {"at": 40, "r": 50, "delay": 0.12, "ticks": 1, "every": 0.2, "col": "#ff8a3a", "boom": 1}}], ["pow", "amt"])
U("ember_special", "Cinder Burst", "ember", "special", "Your special builds Burn ({v}) and costs 20% less Focus.", [{"t": "status", "slot": "special", "kind": "burn", "amt": 60}, {"t": "stat", "key": "special_cost", "mult": 0.8}], ["amt"])
U("ember_dodge", "Fire Walk", "ember", "dodge", "Your roll leaves fire burning behind you for 2 s ({v} damage a tick, building Burn).",
  [{"t": "proc", "when": "roll_end", "pow": 0.4, "poise": 2, "kind": "burn", "amt": 12, "aoe": {"at": 0, "mid": 1, "r": 34, "delay": 0.05, "ticks": 4, "every": 0.5, "col": "#ff8a3a"}}], ["pow", "amt"])
U("ember_guard", "Hearth Ward", "ember", "guard", "Blocking or parrying a hit builds {v} Burn on the boss.", [{"t": "guard_status", "kind": "burn", "amt": 35}], ["amt"], req="guard")
U("ember_p1", "Smouldering", "ember", None, "Burn bursts deal {v}% more.", [{"t": "statusmult", "kind": "burn", "mult": 1.3}], ["mult"])
U("ember_p2", "Cauterise", "ember", None, "When a Burn bursts on the boss, you heal {v}.", [{"t": "burstheal", "kind": "burn", "amt": 8}], ["amt"])
U("ember_p3", "Ashen Resolve", "ember", None, "Deal {v}% more to a burning boss (for 4 s after a Burn).", [{"t": "vsstatus", "kind": "burn", "mult": 1.15}], ["mult"])
U("ember_p4", "Flashpoint", "ember", None, "Critical hits deal {v}% more.", [{"t": "crit", "mult": 1.3}], ["mult"])

# ------------------------------------------------------------------ Rime
U("rime_light", "Frostbite", "rime", "light", "Light attacks build Frost ({v} a hit).", [{"t": "status", "slot": "light", "kind": "frost", "amt": 14}], ["amt"])
U("rime_heavy", "Glacier Blow", "rime", "heavy", "Heavy attacks throw three shards of ice ahead ({v} damage each, building Frost).",
  [{"t": "proc", "when": "heavy", "pow": 0.55, "poise": 6, "kind": "frost", "amt": 16, "proj": {"v": 280, "r": 6, "life": 0.5, "n": 3, "spread": 16, "col": "#7fe3ff"}}], ["pow", "amt"])
U("rime_special", "Hoarfrost", "rime", "special", "Your special builds {v} Frost.", [{"t": "status", "slot": "special", "kind": "frost", "amt": 70}], ["amt"])
U("rime_dodge", "Ice Trail", "rime", "dodge", "Rolling past the boss freezes its feet: {v} Frost.", [{"t": "dodge", "kind": "frost", "amt": 32}], ["amt"])
U("rime_guard", "Winter's Wall", "rime", "guard", "Blocking or parrying a hit bursts frost around you ({v} damage, building Frost; once every 3 s).",
  [{"t": "proc", "when": "guard", "cd": 3, "pow": 1.2, "poise": 14, "kind": "frost", "amt": 45, "aoe": {"at": 0, "r": 62, "delay": 0.05, "ticks": 1, "every": 0.2, "col": "#7fe3ff", "boom": 1}}], ["pow", "amt"], req="guard")
U("rime_p1", "Shatter", "rime", None, "Frost bursts break {v}% more poise.", [{"t": "statusmult", "kind": "frost", "mult": 1.35}], ["mult"])
U("rime_p2", "Cold Blood", "rime", None, "Drinking your flask bursts frost around you ({v} damage, building Frost).",
  [{"t": "proc", "when": "flask", "pow": 1.0, "poise": 14, "kind": "frost", "amt": 60, "aoe": {"at": 0, "r": 72, "delay": 0.05, "ticks": 1, "every": 0.2, "col": "#7fe3ff", "boom": 1}}], ["pow", "amt"])
U("rime_p3", "Still Air", "rime", None, "Deal {v}% more to a frozen boss.", [{"t": "vsstatus", "kind": "frost", "mult": 1.15}], ["mult"])
U("rime_p4", "Patience", "rime", None, "Your dashes come back {v}% faster.", [{"t": "stat", "key": "dash_regen", "mult": 1.2}], ["mult"])

# ------------------------------------------------------------------ Blood
U("blood_light", "Opened Vein", "blood", "light", "Light attacks build Bleed ({v} a hit).", [{"t": "status", "slot": "light", "kind": "bleed", "amt": 15}], ["amt"])
U("blood_heavy", "Sanguine Cleave", "blood", "heavy", "Heavy attacks heal you for {v}% of their damage.", [{"t": "steal", "slot": "heavy", "frac": 0.06}], ["frac"])
U("blood_special", "Bloodletting", "blood", "special", "Your special builds {v} Bleed.", [{"t": "status", "slot": "special", "kind": "bleed", "amt": 70}], ["amt"])
U("blood_dodge", "Red Wake", "blood", "dodge", "Rolling past the boss cuts it: {v} Bleed.", [{"t": "dodge", "kind": "bleed", "amt": 30}], ["amt"])
U("blood_guard", "Thirsting Parry", "blood", "guard", "A parry heals you {v} health.", [{"t": "parryheal", "amt": 10}], ["amt"], req="block")
U("blood_p1", "Haemophage", "blood", None, "Below half health, deal {v}% more.", [{"t": "lowhp", "mult": 1.25}], ["mult"])
U("blood_p2", "Iron Taste", "blood", None, "All attacks heal you for {v}% of their damage.", [{"t": "steal", "slot": "all", "frac": 0.02}], ["frac"])
U("blood_p3", "Exsanguinate", "blood", None, "Bleed bursts deal {v}% more.", [{"t": "statusmult", "kind": "bleed", "mult": 1.35}], ["mult"])
U("blood_p4", "Blood Price", "blood", None, "Deal 10% more; lose {v} maximum health.", [{"t": "dmg", "slot": "all", "mult": 1.1}, {"t": "stat", "key": "mhp", "add": -10}], [])

# ------------------------------------------------------------------ Storm
U("storm_light", "Arc Edge", "storm", "light", "Every third light hit throws lightning: +{v} damage.", [{"t": "chain", "every": 3, "dmg": 18}], ["dmg"])
U("storm_heavy", "Thunderclap", "storm", "heavy", "A fully charged heavy calls lightning down where it lands a moment later ({v} damage).",
  [{"t": "proc", "when": "heavy_full", "pow": 2.2, "poise": 16, "aoe": {"at": 46, "r": 40, "delay": 0.4, "ticks": 1, "every": 0.2, "col": "#c8b4ff", "pillar": 1}}], ["pow"])
U("storm_special", "Static Field", "storm", "special", "Your special refunds {v} Focus when it hits.", [{"t": "focusback", "amt": 12}], ["amt"])
U("storm_dodge", "Galestep", "storm", "dodge", "Your roll ends in a clap of thunder around you ({v} damage).",
  [{"t": "proc", "when": "roll_end", "pow": 0.7, "poise": 8, "aoe": {"at": 0, "r": 44, "delay": 0.02, "ticks": 1, "every": 0.2, "col": "#c8b4ff", "boom": 1}}], ["pow"])
U("storm_guard", "Lightning Rod", "storm", "guard", "A parry calls lightning: +{v} damage to the boss.", [{"t": "parrybolt", "dmg": 40}], ["dmg"], req="block")
U("storm_p1", "Quickened", "storm", None, "Move {v}% faster.", [{"t": "stat", "key": "speed", "mult": 1.08}], ["mult"])
U("storm_p2", "Overcharge", "storm", None, "Gain {v}% more Focus.", [{"t": "stat", "key": "focus_gain", "mult": 1.3}], ["mult"])
U("storm_p3", "Stormcaller", "storm", None, "Your light attacks are {v}% faster.", [{"t": "stat", "key": "light_speed", "mult": 1.15}], ["mult"])
U("storm_p4", "Tailwind", "storm", None, "For 2 s after a roll you move {v}% faster.", [{"t": "stat", "key": "roll_haste", "mult": 1.25}], ["mult"])

# ------------------------------------------------------------------ Rot
U("rot_light", "Festering Cut", "rot", "light", "Light attacks build Rot ({v} a hit).", [{"t": "status", "slot": "light", "kind": "rot", "amt": 15}], ["amt"])
U("rot_heavy", "Blight Hammer", "rot", "heavy", "Heavy attacks leave a pool of rot where they land for 3 s ({v} damage a tick, building Rot).",
  [{"t": "proc", "when": "heavy", "pow": 0.35, "poise": 2, "kind": "rot", "amt": 14, "aoe": {"at": 40, "r": 40, "delay": 0.2, "ticks": 5, "every": 0.6, "col": "#8be04e"}}], ["pow", "amt"])
U("rot_special", "Plague Breath", "rot", "special", "Your special builds {v} Rot.", [{"t": "status", "slot": "special", "kind": "rot", "amt": 70}], ["amt"])
U("rot_dodge", "Spore Cloud", "rot", "dodge", "Rolling past the boss leaves {v} Rot.", [{"t": "dodge", "kind": "rot", "amt": 32}], ["amt"])
U("rot_guard", "Mouldering Shield", "rot", "guard", "Blocking a hit builds {v} Rot on the boss.", [{"t": "guard_status", "kind": "rot", "amt": 30}], ["amt"], req="guard")
U("rot_p1", "Virulence", "rot", None, "Rot deals {v}% more.", [{"t": "statusmult", "kind": "rot", "mult": 1.35}], ["mult"])
U("rot_p2", "Withering", "rot", None, "A rotting boss's poise doesn't refill, and breaks {v}% faster.", [{"t": "vsstatus_poise", "kind": "rot", "mult": 1.25}], ["mult"])
U("rot_p3", "Carrion", "rot", None, "Deal {v}% more to a rotting boss.", [{"t": "vsstatus", "kind": "rot", "mult": 1.15}], ["mult"])
U("rot_p4", "Carrion Feast", "rot", None, "When your Rot takes hold of the boss, you heal {v}.", [{"t": "burstheal", "kind": "rot", "amt": 8}], ["amt"])

# ------------------------------------------------------------------ Iron
U("iron_light", "Hammering Blows", "iron", "light", "The last hit of your light combo lands with a shockwave ({v} damage) that breaks poise.",
  [{"t": "proc", "when": "finisher", "pow": 0.6, "poise": 30, "aoe": {"at": 30, "r": 38, "delay": 0.04, "ticks": 1, "every": 0.2, "col": "#d8dce4", "boom": 1}}], ["pow"])
U("iron_heavy", "Siegebreaker", "iron", "heavy", "Heavy attacks break {v}% more poise.", [{"t": "poise", "slot": "heavy", "mult": 1.35}], ["mult"])
U("iron_special", "Battering Ram", "iron", "special", "Your special deals {v}% more and breaks more poise.", [{"t": "dmg", "slot": "special", "mult": 1.3}, {"t": "poise", "slot": "special", "mult": 1.3}], ["mult"])
U("iron_dodge", "Steady Roll", "iron", "dodge", "Rolls keep you invulnerable a little longer (+{v} ms).", [{"t": "stat", "key": "iframes", "add": 0.05}], ["add"], req="roll")
U("iron_guard", "Bulwark", "iron", "guard", "Blocking a hit uses {v}% less of a dash.", [{"t": "stat", "key": "block_cost", "mult": 0.6}], ["mult"], req="block")
U("iron_p1", "Executioner", "iron", None, "Critical hits deal {v}% more.", [{"t": "crit", "mult": 1.4}], ["mult"])
U("iron_p2", "Unbowed", "iron", None, "Once a fight, a hit that would down you leaves you standing on {v} health.", [{"t": "unbowed", "amt": 10}], ["amt"])
U("iron_p3", "Perfect Form", "iron", None, "Dodging through a hit gives back {v}% of the dash; your next hit within 2 s deals 30% more.",
  [{"t": "perfect", "dash": 0.5, "dmg": 1.3, "heal": 0}], ["dash"])
U("iron_p4", "Extra Flask", "iron", None, "+1 flask charge.", [{"t": "stat", "key": "flasks", "add": 1}], [])

# ------------------------------------------------------------------ passives with no Vow
U("any_flask", "Deep Flask", None, None, "+1 flask charge.", [{"t": "stat", "key": "flasks", "add": 1}], [])
U("any_reach", "Long Reach", None, None, "Your attacks reach {v}% further.", [{"t": "stat", "key": "reach", "mult": 1.12}], ["mult"], req="melee")
U("any_focus", "Meditation", None, None, "Specials cost {v}% less Focus.", [{"t": "stat", "key": "special_cost", "mult": 0.8}], ["mult"])
U("any_all", "Momentum", None, None, "Each hit of a light combo deals {v}% more than the one before it.", [{"t": "ramp", "mult": 1.07}], ["mult"])
U("any_vigour", "Afterimage", None, None, "Rolling through a hit leaves an echo that strikes where you were ({v} damage).",
  [{"t": "proc", "when": "perfect", "pow": 2.0, "poise": 14, "aoe": {"at": 0, "r": 48, "delay": 0.15, "ticks": 1, "every": 0.2, "col": "#e8ecf2", "boom": 1}}], ["pow"])
U("any_skillcd", "Quick Study", None, None, "Your skills come back {v}% sooner.", [{"t": "stat", "key": "skill_cd", "mult": 0.85}], ["mult"])
U("any_skilldmg", "Battle Hymn", None, None, "Your skills deal {v}% more.", [{"t": "dmg", "slot": "skill", "mult": 1.2}], ["mult"])
U("any_skillheal", "Second Nature", None, None, "Using a skill heals you {v}.", [{"t": "skillheal", "amt": 6}], ["amt"])
U("any_skillward", "Stoneskin", None, None, "Using a skill wards you against the next {v} damage.", [{"t": "skillward", "amt": 10}], ["amt"])
U("any_skillfocus", "Resonance", None, None, "Using a skill gives you {v} Focus.", [{"t": "stat", "key": "skill_focus", "add": 15}], ["add"])

# ------------------------------------------------------------------ Pacts (two or more heroes)
U("pact_revive", "Pact of Mercy", None, None, "Reviving costs you no health, and the one you raise rises with a {v}-point shield.",
  [{"t": "revive", "free": True, "shield": 25}], ["shield"], pact=True)
U("pact_fast", "Pact of Haste", None, None, "You revive allies {v}% faster.", [{"t": "stat", "key": "revive_time", "mult": 0.6}], ["mult"], pact=True)
U("pact_near", "Pact of Brothers", None, None, "Deal {v}% more while an ally is within reach.", [{"t": "near", "mult": 1.12}], ["mult"], pact=True)
U("pact_flask", "Pact of the Cup", None, None, "Your flask also heals allies close by ({v}% of what it heals you).", [{"t": "flaskall", "frac": 0.5}], ["frac"], pact=True)
U("pact_vengeance", "Pact of Vengeance", None, None, "When an ally goes down, deal {v}% more for 8 s.", [{"t": "ondown", "mult": 1.35, "dur": 8}], ["mult"], pact=True)
U("pact_parry", "Pact of the Opening", None, None, "When anyone parries, your next hit deals {v}% more.", [{"t": "allyparry", "mult": 1.4}], ["mult"], pact=True, req="block")

# ------------------------------------------------------------------ Duos
U("duo_wildfire", "Wildfire", "ember", None, "Lightning sets the boss alight: chain hits build 25 Burn.", [{"t": "chainstatus", "kind": "burn", "amt": 25}], [], needs=["ember", "storm"])
U("duo_thaw", "Thaw", "rime", None, "Burn bursts on a frozen boss deal double.", [{"t": "combo", "a": "burn", "b": "frost", "mult": 2.0}], [], needs=["ember", "rime"])
U("duo_septic", "Septic Wounds", "rot", None, "Bleed bursts also build 40 Rot.", [{"t": "procbuild", "on": "bleed", "kind": "rot", "amt": 40}], [], needs=["blood", "rot"])
U("duo_anvil", "Anvil", "iron", None, "Frost bursts break a boss's poise outright if it's below half.", [{"t": "frostbreak"}], [], needs=["rime", "iron"])
U("duo_galvanic", "Galvanic Blood", "blood", None, "Chain lightning heals you 3.", [{"t": "chainheal", "amt": 3}], [], needs=["blood", "storm"])
U("duo_slag", "Slag", "ember", None, "Critical hits build 60 Burn and 60 Rot.", [{"t": "critstatus", "amt": 60}], [], needs=["ember", "rot"])

# ------------------------------------------------------------------ Weapon Arts (the sword's; the others' are in their weapon files)
U("art_sword_riposte", "Riposte", None, None, "After a parry, your next hit is a critical.", [{"t": "parry", "mult": 3.0}], [], weapon="sword")
U("art_sword_bulwark", "Tower Shield", None, None, "Your block covers a wider arc, and a blocked hit uses half a dash.", [{"t": "stat", "key": "block_cost", "mult": 0.5}, {"t": "stat", "key": "guard_arc", "mult": 1.4}], [], weapon="sword")
U("art_sword_oath", "Oathblade", None, None, "Your shield bash heals you {v}.", [{"t": "specialheal", "amt": 12}], ["amt"], weapon="sword")
U("art_sword_flurry", "Flurry", None, None, "Your light attacks are {v}% faster.", [{"t": "stat", "key": "light_speed", "mult": 1.2}], ["mult"], weapon="sword")


U("art_gs_titan", "Titan's Grip", None, None, "A fully charged heavy sends a shockwave along the ground ({v} damage) that passes through everything.",
  [{"t": "proc", "when": "heavy_full", "pow": 1.5, "poise": 20, "proj": {"v": 320, "r": 14, "life": 0.5, "pierce": True, "col": "#d8dce4"}}], ["pow"], weapon="greatsword")
U("art_gs_quake", "Earthsplitter", None, None, "Your Leaping Slam breaks {v}% more poise.", [{"t": "poise", "slot": "special", "mult": 1.4}], ["mult"], weapon="greatsword")
U("art_gs_wall", "Living Wall", None, None, "Blocking a hit uses {v}% less of a dash.", [{"t": "stat", "key": "block_cost", "mult": 0.65}], ["mult"], weapon="greatsword")
U("art_gs_cleave", "Wide Cleave", None, None, "Your swings reach {v}% further.", [{"t": "stat", "key": "reach", "mult": 1.15}], ["mult"], weapon="greatsword")
U("art_dg_venom", "Serrated Edges", None, None, "Light attacks build {v} Bleed.", [{"t": "status", "slot": "light", "kind": "bleed", "amt": 9}], ["amt"], weapon="daggers")
U("art_dg_shadow", "Umbral Step", None, None, "Shadowstep deals {v}% more and costs less Focus.", [{"t": "dmg", "slot": "special", "mult": 1.3}, {"t": "stat", "key": "special_cost", "mult": 0.8}], ["mult"], weapon="daggers")
U("art_dg_third", "Fourth Dash", None, None, "Your dash has one more charge.", [{"t": "stat", "key": "dash_charges", "add": 1}], [], weapon="daggers")
U("art_dg_flurry", "Thousand Cuts", None, None, "The flurry's last stab throws both daggers ({v} damage each, building Bleed).",
  [{"t": "proc", "when": "finisher", "pow": 0.8, "poise": 4, "kind": "bleed", "amt": 10, "proj": {"v": 420, "r": 4, "life": 0.6, "n": 2, "spread": 8}}], ["pow", "amt"], weapon="daggers")
U("art_hb_reach", "Long Haft", None, None, "Your thrusts and sweeps reach {v}% further.", [{"t": "stat", "key": "reach", "mult": 1.15}], ["mult"], weapon="halberd")
U("art_hb_counter", "Answering Blade", None, None, "Your counter deals {v}% more.", [{"t": "dmg", "slot": "guard", "mult": 1.4}], ["mult"], weapon="halberd")
U("art_hb_vault", "High Vault", None, None, "Pole Vault breaks {v}% more poise.", [{"t": "poise", "slot": "special", "mult": 1.5}], ["mult"], weapon="halberd")
U("art_hb_sweep", "Reaper's Arc", None, None, "Heavy sweeps deal {v}% more.", [{"t": "dmg", "slot": "heavy", "mult": 1.2}], ["mult"], weapon="halberd")
U("art_bw_pierce", "Piercing Shafts", None, None, "Your light arrows pass through everything they hit.", [{"t": "stat", "key": "light_pierce", "add": 1}], [], weapon="bow")
U("art_bw_rain", "Storm of Arrows", None, None, "Arrow Rain deals {v}% more.", [{"t": "dmg", "slot": "special", "mult": 1.35}], ["mult"], weapon="bow")
U("art_bw_draw", "Heavy Draw", None, None, "Charged shots break {v}% more poise.", [{"t": "poise", "slot": "heavy", "mult": 1.4}], ["mult"], weapon="bow")
U("art_bw_roll", "Skirmisher", None, None, "Your roll-shot deals {v}% more.", [{"t": "dmg", "slot": "guard", "mult": 1.5}], ["mult"], weapon="bow")
U("art_ct_orb", "Greater Orb", None, None, "Your charged orb deals {v}% more.", [{"t": "dmg", "slot": "heavy", "mult": 1.25}], ["mult"], weapon="catalyst")
U("art_ct_nova", "Starburst", None, None, "Nova deals {v}% more.", [{"t": "dmg", "slot": "special", "mult": 1.3}], ["mult"], weapon="catalyst")
U("art_ct_bolt", "Split Bolts", None, None, "Every light cast looses one more bolt; bolts deal 30% less.", [{"t": "stat", "key": "light_shots", "add": 1}, {"t": "dmg", "slot": "light", "mult": 0.7}], [], weapon="catalyst")
U("art_ct_blink", "Far Blink", None, None, "Your blink comes back {v}% sooner.", [{"t": "stat", "key": "dash_time", "mult": 0.7}], ["mult"], weapon="catalyst")


def offer(hero, n_heroes, rng, stage):
    """Three upgrade cards for a hero: [(id, rarity)]. Leans toward the Vows they already follow."""
    held = {u for u, _ in hero.ups}
    vows = {UPGRADES[u]["vow"] for u in held if UPGRADES[u]["vow"]}
    pool = []
    for u in UPGRADES.values():
        if u["id"] in held: continue
        if u["pact"] and n_heroes < 2: continue
        if u["weapon"] and u["weapon"] != hero.weapon: continue
        if not usable(u, hero.weapon): continue
        if u["needs"] and not all(v in vows for v in u["needs"]): continue
        w = 1.0
        if u["vow"] in vows: w = 2.2
        if u["needs"]: w = 3.0
        if u["weapon"]: w = 1.6
        pool.append((u["id"], w))
    picks = []
    for _ in range(3):
        if not pool: break
        r = rng.random() * sum(w for _, w in pool)
        for i, (uid, w) in enumerate(pool):
            r -= w
            if r <= 0: break
        picks.append(pool.pop(i)[0])
    out = []
    for uid in picks:
        roll = rng.random() + stage * 0.06
        out.append((uid, "epic" if roll > 1.0 else "rare" if roll > 0.72 else "common"))
    return out


def scaled(uid, rarity):
    """An upgrade's effects with its rarity applied."""
    u, k = UPGRADES[uid], RARITY[rarity]
    out = []
    for f in u["fx"]:
        f = dict(f)
        for key in u["scale"]:
            if key in f and isinstance(f[key], (int, float)) and not isinstance(f[key], bool):
                f[key] = 1 + (f[key] - 1) * k if key == "mult" else f[key] * k
        out.append(f)
    return out


def describe(uid, rarity):
    u = UPGRADES[uid]
    fx = scaled(uid, rarity)
    v = ""
    for f in fx:
        for key in u["scale"]:
            if key in f:
                x = f[key]
                if f["t"] == "proc" and key == "pow": v = str(round(x * 20)); break
                v = f"{round(x * 1000)}" if f.get("key") == "iframes" else f"{round((1 - x) * 100)}" if key == "mult" and x < 1 else f"{round((x - 1) * 100)}" if key == "mult" else f"{round(x * 100)}" if key in ("frac", "dash") or (key == "add" and x < 1) else f"{round(x)}" if x >= 1 else f"{x:.2f}"
                break
        if v: break
    return u["text"].replace("{v}", v)
