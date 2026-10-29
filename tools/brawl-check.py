"""Plays Board Brawl between bots, headlessly and on a fake clock, and checks it holds together.

    python3 tools/brawl-check.py [games]

First every minigame is played by bots in every format it suits, and each must finish within
its time and rank everyone. Then whole 10-round games are played by 2-4 bots; each must finish
without an exception or a stall. It prints how often each minigame and format came up and how
the crowns fell, for a feel of the balance.
"""

import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brawl import game  # noqa: E402
from app.brawl import minigames as M  # noqa: E402

TICK = game.TICK


def check_minigames():
    for key, cls in M.GAMES.items():
        for mode in sorted(cls.modes):
            for n in (2, 3, 4):
                if mode == "team" and n != 4 or mode == "duel" and n != 2 or mode == "1vn" and n < 3:
                    continue
                if n < cls.min_players:
                    continue
                ids = list(range(1, n + 1))
                humans = ids[:cls.needs_humans]
                teams = [[1, 2], [3, 4]] if mode == "team" else [[1], ids[1:]] if mode == "1vn" else None
                g = M.make(key, ids, [i for i in ids if i not in humans], teams)
                steps = 0
                while not g.over():
                    g.tick(TICK)
                    g.snap()
                    steps += 1
                    assert steps * TICK <= g.dur + 1, f"{key} ran over time"
                keys = [g.key_of(i) for i in ids]
                if teams:
                    tk = [g.team_key(t) for t in teams]
                    assert tk[0] is not None and tk[1] is not None
                labels = [g.label(i) for i in ids]
                assert all(isinstance(x, str) and x for x in labels), (key, labels)
                sorted(keys)
        print(f"  {key}: ok in {', '.join(sorted(cls.modes))}")


def play(n_bots, seed):
    random.seed(seed)
    room = game.Room("TEST")
    for _ in range(n_bots):
        room.add_bot()
    room.host = next(iter(room.players))
    room.rounds = 10
    room.start_game()
    now, seen, modes = 0.0, Counter(), Counter()
    last_phase = None
    while room.phase != "final":
        now += TICK
        room.tick(now)
        if room.phase != last_phase:
            last_phase = room.phase
            if room.phase == "mgresult":
                seen[room.results["key"]] += 1
                modes[room.results["mode"]] += 1
        if now > 90 * 60:
            raise AssertionError(f"stalled in {room.phase}/{room.step}")
    return room, now, seen, modes


def main():
    games = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    print("minigames:")
    check_minigames()
    mgs, modes, crowns, minutes = Counter(), Counter(), Counter(), []
    for i in range(games):
        n = 2 + i % 3
        room, t, seen, md = play(n, i)
        mgs.update(seen)
        modes.update(md)
        minutes.append(t / 60)
        for p in room.seated():
            crowns[p.crowns] += 1
        top = room.final["rows"][0]
        print(f"game {i}: {n} bots, {t / 60:.1f} min, winner {room.players[top['id']].name} "
              f"with {top['crowns']} crowns, {top['coins']} coins; bonus: "
              + ", ".join(f"{b['title']} {b['value']}" for b in room.final["bonus"]))
    print("minigames played:", dict(mgs))
    print("formats:", dict(modes))
    print("crowns per player:", dict(sorted(crowns.items())))
    print(f"ok: {games} games, {sum(minutes) / len(minutes):.1f} min on average (bots don't dawdle)")


main()
