# Weapons are their own parts, held in the front hand; the game rotates them through each swing.
# Drawn pointing up, pivot on the grip.
from pix import P
from heroes import STEEL

W = {**STEEL, 'w': '#e4eaf0', 'v': '#a8b0bc', 'u': '#7a8494'}


def sword():
    g = P(7, 30, (3, 24), W)
    g.rows(2, 0, [(1, 1), (0, 2)], 'w')
    g.rect(2, 2, 4, 20, 'w'); g.rect(4, 2, 4, 20, 'v'); g.rect(3, 4, 3, 18, 'v')
    g.rect(0, 21, 6, 22, 'Y'); g.px(0, 20, 'Y'); g.px(6, 20, 'Y')
    g.rect(2, 23, 4, 27, 'h'); g.px(3, 24, 'H'); g.px(3, 26, 'H')
    g.rect(2, 28, 4, 29, 'Y')
    return g


def shield(colour):
    """The sword's kite shield, in the player's colour with a steel rim; held by the back hand."""
    g = P(13, 17, (6, 6), {**W, 'C': colour[0], 'c': colour[1]})
    g.rows(0, 0, [(1, 11), (0, 12), (0, 12), (0, 12), (0, 12), (0, 12), (0, 12), (0, 12), (1, 11), (1, 11), (2, 10), (2, 10), (3, 9), (4, 8), (5, 7), (6, 6)], 'A')
    g.rows(1, 1, [(1, 9), (0, 10), (0, 10), (0, 10), (0, 10), (0, 10), (0, 10), (1, 9), (1, 9), (2, 8), (2, 8), (3, 7), (4, 6)], 'C')
    g.rect(6, 1, 6, 13, 'Y'); g.rect(2, 5, 10, 5, 'Y'); g.rect(8, 2, 10, 9, 'c')
    return g


ALL = {'sword': sword}
OFFHAND = {'shield': shield}  # drawn per player colour
