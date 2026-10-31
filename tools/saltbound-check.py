"""Forces every action of every Saltbound class through real fights, to catch crashes the bots'
play never reaches (instant dice tricks, summons, intent tricks, capstones).

    python3 tools/saltbound-check.py

For each class: a hero who knows every skill in the class's pool (every passive and capstone
too) fights a mixed group; each action is placed with dice that fit and a valid target, the
round is resolved, and fights restart as they end. Any exception other than Invalid is a bug.
"""

import os
import sys
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.saltbound import classes as C, game  # noqa: E402
from app.saltbound.combat import Invalid  # noqa: E402

FOES = ["cutthroat", "crab", "eel", "barnacle_priest", "storm_wisp"]


def fight(g, heroes):
    g.s["fights"] = []
    g.start_fight({"kind": "roam", "tile": g.hero(0)["tile"], "heroes": heroes, "foes": list(FOES), "by": 0})


def fit_dice(g, h, a, tgt):
    """Enough free dice for the action (their rolls decide hit or miss when it resolves)."""
    x = g.hs(h)
    n = a["req"].get("n", 1)
    if n == 0:
        return []
    while len([d for d in x["dice"] if not d["used"]]) < n:
        x["dice"].append({"id": f"t{len(x['dice'])}.{g.s['fight']['round']}", "faces": [1, 2, "S", "W", "F3", "X", 7, 8],
                          "dk": ["exploding"], "src": "base", "used": False, "v": None, "bonus": 0, "top": False})
    return [d["id"] for d in x["dice"] if not d["used"]][:n]


def target(g, h, a):
    kind = a["tgt"]
    f = g.s["fight"]
    if kind == "foe":
        pool = g.front_foes() if a.get("melee") else g.foes()
        if not pool:
            return False
        fo = pool[0]
        if a["req"].get("marked"):
            fo["st"]["mark"] = 1
        return f"f{fo['id']}"
    if kind == "downed":
        downed = [y for y in f["heroes"] if g.hs(y)["down"]]
        if not downed:
            g.hs(f["heroes"][1])["down"] = True
            g.hero(f["heroes"][1])["hp"] = 0
            downed = [f["heroes"][1]]
        return f"h{downed[0]}"
    if kind in ("ally", "other"):
        others = [y for y in g.actives() if y != h or kind == "ally"]
        return f"h{others[0]}" if others else False
    return None


def main():
    bad = 0
    tried = 0
    for k, c in C.CLASSES.items():
        others = [o for o in C.CLASSES if o != k][:2]
        g = game.Game.new(77, [k] + others, "normal")
        hero = g.hero(0)
        hero["skills"] = list(c["start"]) + list(c["pool"])
        hero["hp"] = g.maxhp(0)
        for y in range(3):
            g.hero(y)["tile"] = hero["tile"]
        fight(g, [0, 1, 2])
        for key in g.actions_of(0):
            for attempt in range(2):
                try:
                    if g.s["phase"] != "fight" or not g.s["fight"]:
                        g.s["phase"] = "plan"
                        for y in range(3):
                            g.hero(y).update(alive=True, hp=g.maxhp(y))
                        fight(g, [0, 1, 2])
                    if not g.active(0):
                        g.hs(0)["down"] = False
                        g.hero(0)["hp"] = g.maxhp(0)
                    if g.hs(0)["ready"]:
                        g.hs(0)["ready"] = False
                    g.hs(0)["st"].pop("root", None)
                    a = g.action_def(0, key)
                    if a.get("melee"):
                        g.hs(0)["row"] = "front"
                    tgt = target(g, 0, a)
                    if tgt is False:
                        continue
                    ids = fit_dice(g, 0, a, tgt)
                    if ids is None:
                        print(f"  {k}/{key}: no dice fit")
                        continue
                    tried += 1
                    g.act(0, {"t": "place", "a": a["key"], "dice": ids, "tgt": tgt})
                    for y in list(g.s["fight"]["heroes"]) if g.s["fight"] else []:
                        if g.s["fight"] and g.active(y) and not g.hs(y)["ready"]:
                            g.act(y, {"t": "fready"})
                    break
                except Invalid as e:
                    if attempt == 1:
                        print(f"  {k}/{key}: refused: {e}")
                except Exception:
                    bad += 1
                    print(f"  {k}/{key}: CRASH")
                    traceback.print_exc()
                    break
    print(f"{tried} placements, {bad} crashes")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
