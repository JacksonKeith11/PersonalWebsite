"""How often the one wins Board Brawl's one-against-the-rest minigames, played by bots.

    python3 tools/brawl-balance.py [keys] [games]

Plays each 1 v 3 minigame (or just the comma-separated keys given) a few hundred times with bots
on both sides and prints how often the one won and how long games lasted. Aim for 40-60%.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.brawl import game  # noqa: E402
from app.brawl import minigames as M  # noqa: E402


def main():
    keys = sys.argv[1].split(",") if len(sys.argv) > 1 else [k for k, g in M.GAMES.items() if "1vn" in g.modes]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    ids = [1, 2, 3, 4]
    for key in keys:
        wins, took = 0, 0.0
        for _ in range(n):
            g = M.make(key, ids, ids, [[1], [2, 3, 4]])
            while not g.over() and g.t < 400:
                g.tick(game.TICK)
                g.snap()
            took += g.t
            wins += g.team_key([1]) < g.team_key([2, 3, 4])
        print(f"{key:10} the one wins {100 * wins / n:3.0f}%   {took / n:5.1f}s a game")


if __name__ == "__main__":
    main()
