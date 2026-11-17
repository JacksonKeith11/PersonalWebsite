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
  mod      {set: {path: value}}    changes the hero's weapon itself (build.py, `Build.weapon`; hero.js, `weaponOf`):
                                   each path ("special.proj", "light.3", "moves.rush.mult", "guard.dodge") is set
                                   in their own copy of the weapon table, on the server and in every browser.
                                   This is how a blessing replaces a move.
  proc, further `when`s:           special (as the special strikes), pass (a dodge: `pass` px round the hero is
                                   struck all the way along it; a blink strikes the line it crossed); `heal`
                                   heals the hero when it lands; an aoe's `clear` destroys boss shots inside it
  bloodfin {mult, cost}            the light combo's last hit deals x mult and costs health
  overcharge {mult, cost}          a heavy held 0.5 s past full (the browser says `oc`) deals x mult for health
  bloodspecial {cost}              a special without the Focus for it spends health instead ({t: 'pay'})
  echo     {frac}                  a second special within 2 s is free (the browser says `eh`), at frac damage
  growth   {frac, secs, amt}       a special plants a canker: after secs it bursts for frac of the damage the
                                   body took meanwhile and builds amt Rot
  counterhit {slot, mult, poise}   that slot ('special', 'skill') deals x mult and breaks x poise on a boss that
                                   is mid-attack or winded (fight.py, `Fight.open`)
  critextend {secs}                a critical keeps the stagger going that much longer
  burstgain {kind, cd, focus}      when that status bursts: skills come back cd s sooner / Focus gained
  perfectgain {focus}              a hit dodged through gives Focus; perfectstatus {kind, amt} builds a status
  flaskrally {mult, dur}           drinking gives x mult damage for dur seconds
  movedmg  {move, mult}            that weapon move deals x mult
  countershot {dmg}                a projectile countered (the halberd's stance) is hurled back for dmg
  meditate {}                      a skill used at full Focus (the browser says `ff`) comes back in half the time
  revivegain {}                    raising an ally refills both heroes' dashes
  stat keys the browser acts on:   light_speed (light attacks play faster), roll_haste (speed for 2 s after
                                   a roll), light_pierce (light arrows pierce), light_shots (extra bolts a cast),
                                   patience (a second standing still charges the next heavy), haste_light (light
                                   attacks x mult faster for 2 s after a dodge), drink_speed (drink at a run),
                                   dash_refund (a dash-strike that lands gives the dash back), and overcharge,
                                   bloodspecial, echo, meditate (1 when the blessing of that name is held)
"""

from .weapons import sw

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
U("ember_special", "Scorched Earth", "ember", "special", "Your special leaves the ground burning where it lands for 3 s ({v} damage a tick, building Burn).",
  [{"t": "proc", "when": "special", "pow": 0.4, "poise": 2, "kind": "burn", "amt": 14, "aoe": {"at": 36, "r": 46, "delay": 0.1, "ticks": 6, "every": 0.5, "col": "#ff8a3a"}}], ["pow", "amt"])
U("ember_dodge", "Fire Walk", "ember", "dodge", "Your roll leaves fire burning behind you for 2 s ({v} damage a tick, building Burn).",
  [{"t": "proc", "when": "roll_end", "pow": 0.4, "poise": 2, "kind": "burn", "amt": 12, "aoe": {"at": 0, "mid": 1, "r": 34, "delay": 0.05, "ticks": 4, "every": 0.5, "col": "#ff8a3a"}}], ["pow", "amt"])
U("ember_guard", "Hearth Ward", "ember", "guard", "Blocking or parrying a hit builds {v} Burn on the boss.", [{"t": "guard_status", "kind": "burn", "amt": 35}], ["amt"], req="guard")
U("ember_p1", "Smouldering", "ember", None, "Burn bursts deal {v}% more.", [{"t": "statusmult", "kind": "burn", "mult": 1.3}], ["mult"])
U("ember_p2", "Cauterise", "ember", None, "When a Burn bursts on the boss, you heal {v}.", [{"t": "burstheal", "kind": "burn", "amt": 8}], ["amt"])
U("ember_p3", "Ashen Resolve", "ember", None, "Deal {v}% more to a burning boss (for 4 s after a Burn).", [{"t": "vsstatus", "kind": "burn", "mult": 1.15}], ["mult"])
U("ember_p4", "Flashpoint", "ember", None, "When a Burn bursts on the boss, your skills come back {v} s sooner.", [{"t": "burstgain", "kind": "burn", "cd": 2}], ["cd"])

# ------------------------------------------------------------------ Rime
U("rime_light", "Rimeblade", "rime", "light", "The last hit of your light combo bursts with frost where it lands ({v} damage, building Frost).",
  [{"t": "proc", "when": "finisher", "pow": 0.7, "poise": 10, "kind": "frost", "amt": 40, "aoe": {"at": 30, "r": 44, "delay": 0.05, "ticks": 1, "every": 0.2, "col": "#7fe3ff", "boom": 1}}], ["pow", "amt"])
U("rime_heavy", "Glacier Blow", "rime", "heavy", "Heavy attacks throw three shards of ice ahead ({v} damage each, building Frost).",
  [{"t": "proc", "when": "heavy", "pow": 0.55, "poise": 6, "kind": "frost", "amt": 16, "proj": {"v": 280, "r": 6, "life": 0.5, "n": 3, "spread": 16, "col": "#7fe3ff"}}], ["pow", "amt"])
U("rime_special", "Hoarfrost", "rime", "special", "Your special bursts with frost where it lands ({v} damage, building Frost) and shatters the boss's shots there.",
  [{"t": "proc", "when": "special", "pow": 0.6, "poise": 10, "kind": "frost", "amt": 55, "aoe": {"at": 36, "r": 70, "delay": 0.05, "ticks": 1, "every": 0.2, "col": "#7fe3ff", "boom": 1, "clear": 1}}], ["pow", "amt"])
U("rime_dodge", "Ice Trail", "rime", "dodge", "Your dodge leaves a patch of ice that bursts a second later ({v} damage, building Frost).",
  [{"t": "proc", "when": "roll_end", "pow": 1.2, "poise": 12, "kind": "frost", "amt": 45, "aoe": {"at": 0, "mid": 1, "r": 46, "delay": 1.0, "ticks": 1, "every": 0.2, "col": "#7fe3ff", "boom": 1}}], ["pow", "amt"])
U("rime_guard", "Winter's Wall", "rime", "guard", "Blocking or parrying a hit bursts frost around you ({v} damage, building Frost; once every 3 s).",
  [{"t": "proc", "when": "guard", "cd": 3, "pow": 1.2, "poise": 14, "kind": "frost", "amt": 45, "aoe": {"at": 0, "r": 62, "delay": 0.05, "ticks": 1, "every": 0.2, "col": "#7fe3ff", "boom": 1}}], ["pow", "amt"], req="guard")
U("rime_p1", "Shatter", "rime", None, "Frost bursts break {v}% more poise.", [{"t": "statusmult", "kind": "frost", "mult": 1.35}], ["mult"])
U("rime_p2", "Cold Blood", "rime", None, "Drinking your flask bursts frost around you ({v} damage, building Frost).",
  [{"t": "proc", "when": "flask", "pow": 1.0, "poise": 14, "kind": "frost", "amt": 60, "aoe": {"at": 0, "r": 72, "delay": 0.05, "ticks": 1, "every": 0.2, "col": "#7fe3ff", "boom": 1}}], ["pow", "amt"])
U("rime_p3", "Still Air", "rime", None, "Deal {v}% more to a frozen boss.", [{"t": "vsstatus", "kind": "frost", "mult": 1.15}], ["mult"])
U("rime_p4", "Patience", "rime", None, "Stand still for a second and your next heavy is fully charged at once.", [{"t": "stat", "key": "patience", "add": 1}], [])

# ------------------------------------------------------------------ Blood
U("blood_light", "Opened Vein", "blood", "light", "The last hit of your light combo costs you 4 health and deals {v}% more. Light attacks build 8 Bleed.",
  [{"t": "bloodfin", "mult": 1.4, "cost": 4}, {"t": "status", "slot": "light", "kind": "bleed", "amt": 8}], ["mult"])
U("blood_heavy", "Sanguine Cleave", "blood", "heavy", "Hold a heavy half a second past full and it drinks 8 of your health to hit {v}% harder.",
  [{"t": "overcharge", "mult": 1.35, "cost": 8}, {"t": "stat", "key": "overcharge", "add": 1}], ["mult"])
U("blood_special", "Bloodletting", "blood", "special", "Without the Focus for it, your special spends 15 health instead. It builds {v} Bleed.",
  [{"t": "status", "slot": "special", "kind": "bleed", "amt": 40}, {"t": "bloodspecial", "cost": 15}, {"t": "stat", "key": "bloodspecial", "add": 1}], ["amt"])
U("blood_dodge", "Red Wake", "blood", "dodge", "Your dodge cuts what you pass through ({v} damage, building Bleed) and heals you 3.",
  [{"t": "proc", "when": "pass", "pow": 0.6, "poise": 4, "kind": "bleed", "amt": 25, "heal": 3, "pass": 22}], ["pow", "amt"])
U("blood_guard", "Thirsting Parry", "blood", "guard", "A parry heals you {v} health.", [{"t": "parryheal", "amt": 10}], ["amt"], req="block")
U("blood_p1", "Haemophage", "blood", None, "Below half health, deal {v}% more.", [{"t": "lowhp", "mult": 1.25}], ["mult"])
U("blood_p2", "Iron Taste", "blood", None, "All attacks heal you for {v}% of their damage.", [{"t": "steal", "slot": "all", "frac": 0.02}], ["frac"])
U("blood_p3", "Exsanguinate", "blood", None, "When a Bleed bursts on the boss, you gain {v} Focus.", [{"t": "burstgain", "kind": "bleed", "focus": 25}], ["focus"])
U("blood_p4", "Blood Price", "blood", None, "Drinking your flask gives you {v}% more damage for 6 s.", [{"t": "flaskrally", "mult": 1.3, "dur": 6}], ["mult"])

# ------------------------------------------------------------------ Storm
U("storm_light", "Arc Edge", "storm", "light", "Every third light hit throws lightning: +{v} damage.", [{"t": "chain", "every": 3, "dmg": 18}], ["dmg"])
U("storm_heavy", "Thunderclap", "storm", "heavy", "A fully charged heavy calls lightning down where it lands a moment later ({v} damage).",
  [{"t": "proc", "when": "heavy_full", "pow": 2.2, "poise": 16, "aoe": {"at": 46, "r": 40, "delay": 0.4, "ticks": 1, "every": 0.2, "col": "#c8b4ff", "pillar": 1}}], ["pow"])
U("storm_special", "Echo", "storm", "special", "Within 2 s of a special you may use it again for no Focus, at half its damage.", [{"t": "echo", "frac": 0.5}, {"t": "stat", "key": "echo", "add": 1}], [])
U("storm_dodge", "Stormstep", "storm", "dodge", "Your dodge becomes a blink of lightning that strikes what it crosses ({v} damage).",
  [{"t": "mod", "set": {"guard.dodge": "blink", "guard.dist": 95}}, {"t": "proc", "when": "pass", "pow": 0.9, "poise": 8, "pass": 22, "col": "#c8b4ff"}], ["pow"])
U("storm_guard", "Lightning Rod", "storm", "guard", "A parry calls lightning: +{v} damage to the boss.", [{"t": "parrybolt", "dmg": 40}], ["dmg"], req="block")
U("storm_p1", "Quickened", "storm", None, "Move {v}% faster.", [{"t": "stat", "key": "speed", "mult": 1.08}], ["mult"])
U("storm_p2", "Overcharge", "storm", None, "Dodging through a hit gives you {v} Focus.", [{"t": "perfectgain", "focus": 15}], ["focus"])
U("storm_p3", "Stormcaller", "storm", None, "For 2 s after a dodge your light attacks are {v}% faster.", [{"t": "stat", "key": "haste_light", "mult": 1.2}], ["mult"])
U("storm_p4", "Tailwind", "storm", None, "For 2 s after a roll you move {v}% faster.", [{"t": "stat", "key": "roll_haste", "mult": 1.25}], ["mult"])

# ------------------------------------------------------------------ Rot
U("rot_light", "Festering Cut", "rot", "light", "The last hit of your light combo bursts a cloud of spores that hangs for 3 s ({v} damage a tick, building Rot).",
  [{"t": "proc", "when": "finisher", "pow": 0.3, "poise": 2, "kind": "rot", "amt": 14, "aoe": {"at": 30, "r": 40, "delay": 0.1, "ticks": 6, "every": 0.5, "col": "#8be04e"}}], ["pow", "amt"])
U("rot_heavy", "Blight Hammer", "rot", "heavy", "Heavy attacks leave a pool of rot where they land for 3 s ({v} damage a tick, building Rot).",
  [{"t": "proc", "when": "heavy", "pow": 0.35, "poise": 2, "kind": "rot", "amt": 14, "aoe": {"at": 40, "r": 40, "delay": 0.2, "ticks": 5, "every": 0.6, "col": "#8be04e"}}], ["pow", "amt"])
U("rot_special", "Canker", "rot", "special", "Your special plants a canker on the boss: 2.5 s later it bursts for {v}% of all the damage the boss took meanwhile, and builds 50 Rot.",
  [{"t": "growth", "frac": 0.3, "secs": 2.5, "amt": 50}], ["frac"])
U("rot_dodge", "Spore Cloud", "rot", "dodge", "Dodging through a hit seeds the boss with {v} Rot.", [{"t": "perfectstatus", "kind": "rot", "amt": 60}], ["amt"])
U("rot_guard", "Mouldering Shield", "rot", "guard", "Blocking a hit builds {v} Rot on the boss.", [{"t": "guard_status", "kind": "rot", "amt": 30}], ["amt"], req="guard")
U("rot_p1", "Virulence", "rot", None, "Rot deals {v}% more.", [{"t": "statusmult", "kind": "rot", "mult": 1.35}], ["mult"])
U("rot_p2", "Withering", "rot", None, "A rotting boss's poise doesn't refill, and breaks {v}% faster.", [{"t": "vsstatus_poise", "kind": "rot", "mult": 1.25}], ["mult"])
U("rot_p3", "Carrion", "rot", None, "Deal {v}% more to a rotting boss.", [{"t": "vsstatus", "kind": "rot", "mult": 1.15}], ["mult"])
U("rot_p4", "Carrion Feast", "rot", None, "When your Rot takes hold of the boss, you heal {v}.", [{"t": "burstheal", "kind": "rot", "amt": 8}], ["amt"])

# ------------------------------------------------------------------ Iron
U("iron_light", "Hammering Blows", "iron", "light", "The last hit of your light combo lands with a shockwave ({v} damage) that breaks poise.",
  [{"t": "proc", "when": "finisher", "pow": 0.6, "poise": 30, "aoe": {"at": 30, "r": 38, "delay": 0.04, "ticks": 1, "every": 0.2, "col": "#d8dce4", "boom": 1}}], ["pow"])
U("iron_heavy", "Siegebreaker", "iron", "heavy", "Nothing interrupts you while you charge or swing a heavy (you still take the damage), and it breaks {v}% more poise.",
  [{"t": "mod", "set": {"heavy.hyper": True, "heavy.hypercharge": True}}, {"t": "poise", "slot": "heavy", "mult": 1.2}], ["mult"])
U("iron_special", "Battering Ram", "iron", "special", "A special that lands on a boss that is mid-attack or winded deals {v}% more and breaks 80% more poise.",
  [{"t": "counterhit", "slot": "special", "mult": 1.2, "poise": 1.8}], ["mult"])
U("iron_dodge", "Shoulder Charge", "iron", "dodge", "Your dodge is a shoulder charge: what you pass through takes {v} damage and loses a great deal of poise.",
  [{"t": "proc", "when": "pass", "pow": 0.4, "poise": 30, "pass": 22}], ["pow"])
U("iron_guard", "Bulwark", "iron", "guard", "A blocked or countered hit throws a shockwave forward ({v} damage) that breaks poise (once every 2 s).",
  [{"t": "proc", "when": "guard", "cd": 2, "pow": 0.5, "poise": 35, "aoe": {"at": 30, "r": 44, "delay": 0.05, "ticks": 1, "every": 0.2, "col": "#d8dce4", "boom": 1}}], ["pow"], req="guard")
U("iron_p1", "Executioner", "iron", None, "Your critical hit on a staggered boss keeps it reeling {v} s longer.", [{"t": "critextend", "secs": 1.5}], ["secs"])
U("iron_p2", "Unbowed", "iron", None, "Once a fight, a hit that would down you leaves you standing on {v} health.", [{"t": "unbowed", "amt": 10}], ["amt"])
U("iron_p3", "Perfect Form", "iron", None, "Dodging through a hit gives back {v}% of the dash; your next hit within 2 s deals 30% more.",
  [{"t": "perfect", "dash": 0.5, "dmg": 1.3, "heal": 0}], ["dash"])
U("iron_p4", "Extra Flask", "iron", None, "+1 flask charge.", [{"t": "stat", "key": "flasks", "add": 1}], [])

# ------------------------------------------------------------------ passives with no Vow
U("any_flask", "Swift Draught", None, None, "You drink from your flask at a full run.", [{"t": "stat", "key": "drink_speed", "add": 1}], [])
U("any_reach", "Follow Through", None, None, "Your dash-strike deals {v}% more, and gives the dash back when it lands.",
  [{"t": "movedmg", "move": "dash", "mult": 1.3}, {"t": "stat", "key": "dash_refund", "add": 1}], ["mult"], req="melee")
U("any_focus", "Meditation", None, None, "A skill used at full Focus spends 30 of it and comes back in half the time.", [{"t": "meditate"}, {"t": "stat", "key": "meditate", "add": 1}], [])
U("any_all", "Momentum", None, None, "Each hit of a light combo deals {v}% more than the one before it.", [{"t": "ramp", "mult": 1.07}], ["mult"])
U("any_vigour", "Afterimage", None, None, "Rolling through a hit leaves an echo that strikes where you were ({v} damage).",
  [{"t": "proc", "when": "perfect", "pow": 2.0, "poise": 14, "aoe": {"at": 0, "r": 48, "delay": 0.15, "ticks": 1, "every": 0.2, "col": "#e8ecf2", "boom": 1}}], ["pow"])
U("any_skillcd", "Quick Study", None, None, "Your skills come back {v}% sooner.", [{"t": "stat", "key": "skill_cd", "mult": 0.85}], ["mult"])
U("any_skilldmg", "Battle Hymn", None, None, "Your skills deal {v}% more to a boss that is mid-attack or winded.", [{"t": "counterhit", "slot": "skill", "mult": 1.35, "poise": 1.0}], ["mult"])
U("any_skillheal", "Second Nature", None, None, "Using a skill heals you {v}.", [{"t": "skillheal", "amt": 6}], ["amt"])
U("any_skillward", "Stoneskin", None, None, "Using a skill wards you against the next {v} damage.", [{"t": "skillward", "amt": 10}], ["amt"])
U("any_skillfocus", "Resonance", None, None, "Using a skill gives you {v} Focus.", [{"t": "stat", "key": "skill_focus", "add": 15}], ["add"])

# ------------------------------------------------------------------ Pacts (two or more heroes)
U("pact_revive", "Pact of Mercy", None, None, "Reviving costs you no health, and the one you raise rises with a {v}-point shield.",
  [{"t": "revive", "free": True, "shield": 25}], ["shield"], pact=True)
U("pact_fast", "Pact of Haste", None, None, "You revive allies {v}% faster, and raising one refills every dash for you both.",
  [{"t": "stat", "key": "revive_time", "mult": 0.6}, {"t": "revivegain"}], ["mult"], pact=True)
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
U("art_sword_riposte", "Killing Answer", None, None, "After a parry, your next hit is a critical.", [{"t": "parry", "mult": 3.0}], [], weapon="sword")
U("art_sword_bulwark", "Shield Throw", None, None, "Shield Bash becomes a thrown shield: it flies out through everything and comes back to your arm, striking both ways.",
  [{"t": "mod", "set": {"special.name": "Shield Throw", "special.proj": {"v": 360, "r": 12, "life": 0.42, "pierce": True, "back": True, "col": "#e8ecf2"},
                        "special.hit": (0.12, 0.13), "special.step": 0, "special.mult": 1.0, "special.poise": 40}}], [], weapon="sword")
U("art_sword_oath", "Whirling Edge", None, None, "Your light combo ends in a spinning cut that strikes all round you, in place of the thrust.",
  [{"t": "mod", "set": {"light.3": {"dur": 0.5, "hit": (0.1, 0.26), "shape": {"k": "arc", "r": 50, "a0": -180, "a1": 180}, "mult": 1.5, "poise": 22, "step": 10, "next": 0.38, "whirl": True,
                                    "anim": [(0, sw(-150, 100, torso=-8)), (0.1, sw(-95, 0, torso=10, lean=2)), (0.26, sw(-100, 5, torso=12, lean=3, dy=1)), (0.5, sw(-60, 25, torso=4))]}}}], [], weapon="sword")
U("art_sword_flurry", "Battering Rush", None, None, "Bull Rush strikes twice, ending in a rising shield blow, and breaks far more poise.",
  [{"t": "mod", "set": {"moves.rush.more": [(0.36, 0.46)], "moves.rush.mult": 1.3, "moves.rush.poise": 60, "moves.rush.dur": 0.58}}], [], weapon="sword")


U("art_gs_titan", "Titan's Grip", None, None, "A fully charged heavy sends a shockwave along the ground ({v} damage) that passes through everything.",
  [{"t": "proc", "when": "heavy_full", "pow": 1.5, "poise": 20, "proj": {"v": 320, "r": 14, "life": 0.5, "pierce": True, "col": "#d8dce4"}}], ["pow"], weapon="greatsword")
U("art_gs_quake", "Aftershock", None, None, "Your Leaping Slam is followed a moment later by a second, wider ring ({v} damage).",
  [{"t": "proc", "when": "special", "pow": 1.8, "poise": 40, "aoe": {"at": 30, "r": 84, "delay": 0.4, "ticks": 1, "every": 0.2, "col": "#d8dce4", "boom": 1}}], ["pow"], weapon="greatsword")
U("art_gs_wall", "Living Wall", None, None, "While you charge a heavy, hits from the front are blocked (each uses a dash).", [{"t": "mod", "set": {"heavy.guardcharge": True}}], [], weapon="greatsword")
U("art_gs_cleave", "Endless Whirl", None, None, "The whirlwind costs no dashes, but you walk slower while it turns.", [{"t": "mod", "set": {"moves.spin.drain": 0, "moves.spin.walk": 0.3}}], [], weapon="greatsword")
U("art_dg_venom", "Homing Steel", None, None, "The knives your heavy throws pass through what they hit and fly back to your hand, cutting again on the way.",
  [{"t": "mod", "set": {"heavy.throw.back": True, "heavy.throw.pierce": True}}], [], weapon="daggers")
U("art_dg_shadow", "Umbral Step", None, None, "Shadowstep reaches further and always brings you out behind the boss.", [{"t": "mod", "set": {"special.behind": True, "special.blink": 130}}], [], weapon="daggers")
U("art_dg_third", "Razor Dash", None, None, "Your dash cuts what you pass through ({v} damage, building Bleed).",
  [{"t": "proc", "when": "pass", "pow": 0.7, "poise": 5, "kind": "bleed", "amt": 14, "pass": 22}], ["pow", "amt"], weapon="daggers")
U("art_dg_flurry", "Thousand Cuts", None, None, "The flurry's last stab throws both daggers ({v} damage each, building Bleed).",
  [{"t": "proc", "when": "finisher", "pow": 0.8, "poise": 4, "kind": "bleed", "amt": 10, "proj": {"v": 420, "r": 4, "life": 0.6, "n": 2, "spread": 8}}], ["pow", "amt"], weapon="daggers")
U("art_hb_reach", "Thrown Spear", None, None, "Your light combo ends by throwing the halberd like a spear: it flies far and passes through everything.",
  [{"t": "mod", "set": {"light.3.proj": {"v": 480, "r": 7, "life": 0.5, "pierce": True}, "light.3.mult": 1.4}}], [], weapon="halberd")
U("art_hb_counter", "Answering Blade", None, None, "You can walk in your counter stance and it lasts longer; a shot you counter is hurled back at the boss ({v} damage).",
  [{"t": "mod", "set": {"guard.walk": 0.5, "guard.window": 1.1}}, {"t": "countershot", "dmg": 70}], ["dmg"], weapon="halberd")
U("art_hb_vault", "High Vault", None, None, "Pole Vault strikes as you take off as well as where you land.",
  [{"t": "mod", "set": {"special.hit": (0.03, 0.12), "special.more": [(0.55, 0.66)], "special.step_t": 0.66, "special.mult": 2.0, "special.poise": 30}}], [], weapon="halberd")
U("art_hb_sweep", "Reaper's Arc", None, None, "Your heavy sweep goes all the way round, twice.",
  [{"t": "mod", "set": {"heavy.more": [(0.4, 0.56)], "heavy.dur": 0.9, "heavy.mult": (1.2, 1.9), "heavy.poise": (20, 34), "heavy.whirl": True,
                        "heavy.shape": {"k": "arc", "r": 76, "a0": -180, "a1": 180}}}], [], weapon="halberd")
U("art_bw_pierce", "Piercing Shafts", None, None, "Your light arrows pass through everything they hit.", [{"t": "stat", "key": "light_pierce", "add": 1}], [], weapon="bow")
U("art_bw_rain", "Hunting Rain", None, None, "Arrow Rain falls for longer and drifts after the boss as it falls.", [{"t": "mod", "set": {"special.aoe.follow": 44, "special.aoe.ticks": 5}}], [], weapon="bow")
U("art_bw_draw", "Quick Draw", None, None, "Your heavy draws in a third of the time, for half the damage.",
  [{"t": "mod", "set": {"heavy.charge": 0.34, "heavy.mult": (1.0, 1.8), "heavy.poise": (8, 16)}}], [], weapon="bow")
U("art_bw_roll", "Blast Arrow", None, None, "Your roll looses one heavy arrow that bursts where it strikes.",
  [{"t": "mod", "set": {"guard.n": 1, "guard.spread": 0, "guard.boom": 46, "guard.mult": 1.5, "guard.poise": 20}}], [], weapon="bow")
U("art_ct_orb", "Lingering Orb", None, None, "Where your orb strikes it hangs for 2 s, pulsing four times ({v} damage each).",
  [{"t": "proc", "when": "heavy", "pow": 0.55, "poise": 4, "aoe": {"at": 60, "r": 46, "delay": 0.3, "ticks": 4, "every": 0.5, "col": "#c080ff"}}], ["pow"], weapon="catalyst")
U("art_ct_nova", "Lance of Stars", None, None, "Nova becomes a beam along your aim that strikes three times.",
  [{"t": "mod", "set": {"special.name": "Lance of Stars", "special.shape": {"k": "rect", "x0": 0, "x1": 240, "w": 16}, "special.hit": (0.16, 0.22), "special.more": [(0.3, 0.36), (0.44, 0.5)],
                        "special.dur": 0.7, "special.mult": 1.5, "special.poise": 20}}], [], weapon="catalyst")
U("art_ct_bolt", "Split Bolts", None, None, "Every light cast looses one more bolt; bolts deal 30% less.", [{"t": "stat", "key": "light_shots", "add": 1}, {"t": "dmg", "slot": "light", "mult": 0.7}], [], weapon="catalyst")
U("art_ct_blink", "Twin Rune", None, None, "Your blink leaves a second burst where you arrive ({v} damage).",
  [{"t": "proc", "when": "roll_end", "pow": 1.0, "poise": 10, "aoe": {"at": 0, "r": 44, "delay": 0.14, "ticks": 1, "every": 0.2, "col": "#c080ff", "boom": 1}}], ["pow"], weapon="catalyst")


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
                v = f"{round(x * 1000)}" if f.get("key") == "iframes" else f"{round((1 - x) * 100)}" if key == "mult" and x < 1 else f"{round((x - 1) * 100)}" if key == "mult" else f"{round(x * 100)}" if key in ("frac", "dash") or (key == "add" and x < 1) else f"{round(x)}" if x >= 1 and key != "secs" else f"{x:g}"
                break
        if v: break
    return u["text"].replace("{v}", v)
