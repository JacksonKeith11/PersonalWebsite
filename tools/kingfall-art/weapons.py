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


def greatsword():
    g = P(9, 46, (4, 38), W)
    g.rows(3, 0, [(1, 1), (0, 2)], 'w')
    g.rect(2, 2, 6, 32, 'w'); g.rect(5, 2, 6, 32, 'v'); g.rect(4, 4, 4, 30, 'u')
    g.rect(0, 33, 8, 35, 'Y'); g.rect(3, 36, 5, 43, 'h'); [g.px(4, y, 'H') for y in range(37, 43, 2)]
    g.rect(2, 44, 6, 45, 'Y')
    return g


def dagger():
    g = P(5, 18, (2, 13), W)
    g.px(2, 0, 'w'); g.rect(1, 1, 3, 10, 'w'); g.rect(3, 1, 3, 10, 'v')
    g.rect(0, 11, 4, 11, 'Y'); g.rect(1, 12, 3, 16, 'h'); g.px(2, 17, 'Y')
    return g


def halberd():
    g = P(13, 66, (6, 46), W)
    g.rect(5, 6, 7, 65, 'h'); g.rect(7, 6, 7, 65, 'H')
    g.rows(5, 0, [(1, 1), (0, 2), (0, 2), (0, 2), (0, 2), (0, 2)], 'w')  # the spike
    g.rows(8, 7, [(0, 2), (0, 3), (0, 4), (0, 4), (0, 4), (0, 4), (0, 4), (0, 3), (0, 2)], 'w')  # the axe blade
    g.rect(11, 8, 12, 14, 'v')
    g.rows(1, 9, [(3, 4), (2, 4), (3, 4)], 'v')  # the back hook
    g.rect(4, 17, 8, 18, 'Y'); g.rect(4, 62, 8, 63, 'a')
    return g


def bow():
    g = P(9, 40, (4, 20), W)
    for y in range(40):
        x = 1 + round(5 * (1 - ((y - 20) / 20) ** 2))
        g.rect(x, y, x + 1, y, 'h')
    g.rect(1, 0, 1, 39, 'k'); g.pal['k'] = '#d8d0c0'  # the string
    g.rect(5, 17, 7, 23, 'H'); g.px(6, 0, 'Y'); g.px(1, 39, 'Y')
    return g


def staff():
    g = P(9, 50, (4, 34), {**W, 'Q': '#a0c0ff', 'q': '#5a7ac8', 'X': '#e8f0ff'})
    g.rect(3, 10, 5, 49, 'h'); g.rect(5, 10, 5, 49, 'H')
    g.rows(1, 3, [(1, 5), (0, 6), (0, 6)], 'Y')  # the claw that holds the stone
    g.ell(4, 5, 3.4, 4.4, 'Q'); g.ell(4.5, 6, 2, 2.4, 'q'); g.px(3, 3, 'X')
    g.rect(2, 30, 6, 31, 'Y'); g.rect(3, 47, 5, 49, 'a')
    return g


ALL = {'sword': sword, 'greatsword': greatsword, 'dagger': dagger, 'halberd': halberd, 'bow': bow, 'staff': staff}
OFFHAND = {'shield': shield}  # drawn per player colour
