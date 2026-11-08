"""Saved runs at moments worth looking at, for checking the UI (tools/saltbound-audit.js).

    python3 tools/saltbound-audit.py [scenario ...]

Plays runs with the bots until a scenario's moment (hero 0 choosing loot or claiming from a fight's shared pool, levelling up, at an
event, in a fight, a boss fight, the end of a run...), then saves it to the server's database
for the browser token "audit", titled "audit: <scenario>". Hero 0 is left to the browser.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.saltbound.content import archipelago as A  # noqa: E402
from app.saltbound import bot, game  # noqa: E402
from app.saltbound import save as S  # noqa: E402
from app.saltbound.combat import Invalid  # noqa: E402

PARTY = ["vanguard", "arcanist", "mender"]


def pending(g, kind):
    q = g.s["pending"]["0"]
    return bool(q) and q[0]["type"] == kind


SCENARIOS = {
    "start": lambda g: True,
    "loot": lambda g: pending(g, "loot"),
    "pool": lambda g: pending(g, "pool") and len(g.s["pools"][str(g.s["pending"]["0"][0]["id"])]["heroes"]) > 1,
    "level": lambda g: pending(g, "level"),
    "results": lambda g: len({d["type"] for d in g.s["pending"]["0"]}) >= 2,
    "event": lambda g: pending(g, "event"),
    "fight": lambda g: g.s["phase"] == "fight" and 0 in g.s["fight"]["heroes"] and g.s["fight"]["round"] >= 2
    and not g.s["pending"]["0"],
    "boss": lambda g: g.s["phase"] == "fight" and g.s["fight"]["kind"] == "boss",
    "fork": lambda g: g.s["phase"] == "fork" and 0 in g.s["fork"]["heroes"],
    # the overworld's choices
    "opp": lambda g: g.s["phase"] == "plan" and g.s.get("opps") and not g.s["pending"]["0"] and g.s["turn"] > 5,
    "trade": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"]
    and (g.place(g.hero(0)["tile"]) or {}).get("spec") in ("smith", "temple", "cartographer"),
    "garrison": lambda g: g.s["phase"] == "fork" and 0 in g.s["fork"]["heroes"] and (g.s["fork"].get("garrison") or {}).get("foes"),
    "board": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"]
    and len((g.place(g.hero(0)["tile"]) or {}).get("jobs") or []) == 2,
    "job": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"]
    and any(q["kind"] in ("bounty", "salvage") and not q["done"] and not q.get("failed") for q in g.s["quests"]),
    # the turn after the tide rose and landed enemies
    "tide": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"] and (g.s["turn"] - 1) % g.diff()["rise"] == 0
    and any(n.get("g") is not None for n in g.s.get("tidenews", [])),
    # the sea, raids and the weather
    "raid": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"]
    and any(x.get("raid") and not x.get("occupy") for x in g.s["groups"]) and g.s.get("squalls"),
    "occupied": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"] and any(x.get("occupy") for x in g.s["groups"]),
    "seafight": lambda g: g.s["phase"] == "fight" and 0 in g.s["fight"]["heroes"] and not g.s["pending"]["0"]
    and g.s["world"]["elev"][g.s["fight"]["tile"]] <= g.s["sea"],
    "ground": lambda g: g.s["phase"] == "fight" and 0 in g.s["fight"]["heroes"] and not g.s["pending"]["0"]
    and g.s["fight"].get("ground") and g.s["fight"]["round"] == 1,
    # worked gear: hero 0 in a smithy with gold and enchant materials (set up in main())
    "smithy": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"] and (g.place(g.hero(0)["tile"]) or {}).get("spec") == "smith",
    # a region's quest under way: its next step's event waiting, a boon, forge materials (set up in main())
    "quest": lambda g: g.s["phase"] == "plan" and not g.s["pending"]["0"]
    and any(q["kind"] == "trail" and not q["done"] and q["step"] == 2 for q in g.s["quests"]),
    # beacons and a travelling merchant: hero 0 on a lit beacon with a caravan on its hex (set up in main())
    "travel": lambda g: g.s["phase"] == "plan" and g.s["turn"] >= 3 and not any(g.s["pending"].values()),
    # an ally's event, for two players (tools/saltbound-mp.js events): set up in main()
    "partyevent": lambda g: g.s["phase"] == "plan" and g.s["turn"] >= 3 and not any(g.s["pending"].values()),
    # a Spellblade's fight: Sigils on the enemies, an infused blade (built in main(), not played to)
    "spellblade": None,
    "emberknight": None,
    "dragonborn": None,
    "psion": None,
    "arcanist": None,
    "herald": None,
    # the Vanguard's Impact: a fight with Impact stored and Brace for Impact on (built in main())
    "vanguard": None,
    # the Ranger's hawk: hunting an enemy, with Pinned Prey and Swoop (built in main())
    "ranger": None,
    # the Warden's Rootweb: two enemies Rooted (Entwined), vines between them (built in main())
    "warden": None,
    "won": lambda g: g.s["phase"] == "end" and g.s["result"] == "won",
    "lost": lambda g: g.s["phase"] == "end" and g.s["result"] == "lost",
}


def run_until(cond, seed, limit=20000):
    g = game.Game.new(seed, PARTY, "normal")
    for _ in range(limit):
        if cond(g):
            return g
        if g.s["phase"] == "end":
            return None
        moved = False
        for h in bot.order(g, g.waiting()):
            msg = bot.decide(g, h)
            if msg is None:
                continue
            try:
                g.act(h, msg)
            except Invalid:
                try:
                    g.act(h, {"t": "fready"} if g.s["phase"] == "fight" else {"t": "ready"})
                except Invalid:
                    continue
            moved = True
            break
        if not moved:
            return None
    return None


def main():
    names = sys.argv[1:] or list(SCENARIOS)
    for name in names:
        g = None
        if name == "warden":
            g, seed = game.Game.new(501, ["warden", "vanguard", "mender"], "normal"), 501
            g.hero(0)["skills"] += ["choking_vines", "thicket"]
            g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": [0, 1, 2], "foes": ["cutthroat", "crab", "eel"], "by": 0})
            for fo in g.s["fight"]["foes"][:2]:
                fo["st"]["root"] = 1
            S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
            print(f"{name}: saved")
            continue
        if name == "ranger":
            g, seed = game.Game.new(501, ["ranger", "vanguard", "mender"], "normal"), 501
            g.hero(0)["skills"] += ["swoop", "pinned_prey", "pack_tactics"]
            g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": [0, 1, 2], "foes": ["cutthroat", "crab", "eel"], "by": 0})
            g.hs(0)["hawk"] = f"f{g.s['fight']['foes'][-1]['id']}"
            S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
            print(f"{name}: saved")
            continue
        if name == "vanguard":
            g, seed = game.Game.new(501, ["vanguard", "arcanist", "mender"], "normal"), 501
            g.hero(0)["skills"] += ["shockwave", "share_load", "brace_impact"]
            g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": [0, 1, 2], "foes": ["cutthroat", "crab", "eel"], "by": 0})
            g.hs(0).update(impact=7, imp2=1)
            S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
            print(f"{name}: saved")
            continue
        if name == "herald":
            g, seed = game.Game.new(501, ["herald", "vanguard", "mender"], "normal"), 501
            g.hero(0)["skills"] += ["song_of_blades", "jarring_note", "resonant_chord", "crescendo_of_light"]
            g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": [0, 1, 2], "foes": ["cutthroat", "crab", "eel"], "by": 0})
            g.s["fight"]["harm"] = {"valor": 2, "aegis": 1, "discord": 3}
            S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
            print(f"{name}: saved")
            continue
        if name == "arcanist":
            # three Arcanists can't share a party, so one at a time: ?arcanist=fire|frost|storm|converge on the audit save
            g, seed = game.Game.new(501, ["arcanist", "vanguard", "mender"], "normal"), 501
            g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": [0, 1, 2], "foes": ["cutthroat", "crab", "eel"], "by": 0})
            g.hs(0)["attune"] = sys.argv[2] if len(sys.argv) > 2 else "fire"
            if g.hs(0)["attune"] == "converge":
                g.hs(0).update(attune="storm", converge=True, flux=3)
            S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
            print(f"{name}: saved ({g.hs(0)['attune']})")
            return
        if name == "psion":
            g, seed = game.Game.new(501, ["psion", "vanguard", "mender"], "normal"), 501
            g.hero(0)["skills"] += ["mind_crush", "psionic_storm", "puppet_strings", "perfect_foresight"]
            g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": [0, 1, 2], "foes": ["cutthroat", "crab", "eel"], "by": 0})
            S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
            print(f"{name}: saved")
            continue
        if name == "dragonborn":
            g, seed = game.Game.new(501, ["dragonborn", "vanguard", "mender"], "normal"), 501
            g.hero(0)["skills"] += ["tail_sweep", "focused_breath", "wing_guard", "draconic_roar"]
            g.hero(0)["scales"] = 4
            g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": [0, 1, 2], "foes": ["cutthroat", "crab", "eel"], "by": 0})
            S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
            print(f"{name}: saved")
            continue
        if name == "emberknight":
            g, seed = game.Game.new(501, ["emberknight", "vanguard", "mender"], "normal"), 501
            g.hero(0)["skills"] += ["stoke", "cinder_lance", "pass_the_flame", "quench"]
            g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": [0, 1, 2], "foes": ["cutthroat", "crab", "eel"], "by": 0})
            g.hs(0)["heat"] = 16
            S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
            print(f"{name}: saved")
            continue
        if name == "spellblade":
            g, seed = game.Game.new(501, ["spellblade", "vanguard", "mender"], "normal"), 501
            g.hero(0)["skills"] += ["charged_bolt", "arc_rune", "detonate", "counter_glyph", "bladesong"]
            g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": [0, 1, 2], "foes": ["cutthroat", "crab", "eel"], "by": 0})
            for fo in g.foes():
                fo["st"]["sigil"] = 2
            g.foes()[0]["st"]["sigil"] = 4
            g.infuse(0, 2, 3, "burn")
            S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
            print(f"{name}: saved")
            continue
        for seed in range(500, 560):
            g = run_until(SCENARIOS[name], seed)
            if g:
                break
        if not g:
            print(f"{name}: not reached")
            continue
        if name == "loot":
            # show off the rarities
            g.s["pending"]["0"][0]["opts"] = ["crownbreaker", "storm_glass", "coral_blade"]
        if name == "smithy":
            hero = g.hero(0)
            hero["gold"] = 160
            hero["bag"] += ["powder_salt", "seer_glass"]
            for sl in ("weapon", "armor", "trinket"):  # undo whatever the bots did here, then hone the weapon once
                if hero["equip"].get(sl) in g.s.get("forged", {}):
                    hero["equip"][sl] = g.s["forged"][hero["equip"][sl]]["base"]
            if "hone" in g.temper_options(hero["equip"]["weapon"]):
                g.act(0, {"t": "temper", "slot": "weapon", "what": "hone"})
            hero["gold"] = 160
        if name == "quest":
            q = next(q for q in g.s["quests"] if q["kind"] == "trail" and not q["done"])
            g.s["pending"]["0"] = [{"type": "event", "key": A.QUESTS[q["key"]]["steps"][q["step"]]}]
            g.hero(0)["bag"] += ["starmetal", "wyrm_ember", "fate_feather"]
            g.hero(0)["buffs"]["sandstrider"] = 1
        if name == "travel":
            hero = g.hero(0)
            beacons = [int(t) for t, p in g.s["world"]["places"].items() if p["kind"] == "beacon"]
            for t in beacons:
                g.place(t)["lit"] = True
                g.reveal(t, 2)
            for y in range(3):
                g.hero(y)["tile"], g.hero(y)["afloat"] = beacons[0], False
            g.reveal(beacons[0], 4)
            g.s["merchants"][0]["tile"] = beacons[0]
            hero["gold"] = 300
            hero["bag"] += ["starmetal", "powder_salt", "fate_feather"]
        if name == "partyevent":
            # everyone on one hex, and hero 1 (the second player's) at an event with a party check
            for y in (0, 2):
                g.hero(y)["tile"], g.hero(y)["afloat"] = g.hero(1)["tile"], g.hero(1)["afloat"]
            g.s["pending"]["1"] = [{"type": "event", "key": "stuck_skiff"}]
            g.s["plans"] = {str(y): {"path": [], "ready": False, "rest": False} for y in range(3)}
        S.save(f"audit-{name}", ["audit"], g, f"audit: {name}")
        print(f"{name}: saved (seed {seed}, turn {g.s['turn']}, phase {g.s['phase']})")


if __name__ == "__main__":
    main()
