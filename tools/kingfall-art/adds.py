# The small enemies some bosses call: one frame each, facing right (the game flips them).
from pix import P


def tadpole():
    """The Mire Mother's brood: a fat tadpole the size of a dog, with a whipping tail."""
    p = {'G': '#5e6e3c', 'g': '#435029', 'H': '#7a8a4e', 'B': '#b8ac7c', 'Y': '#e8c84a', 'o': '#141018'}
    g = P(24, 14, (12, 12), p)
    g.ell(15, 7, 8, 6, 'G'); g.ell(14, 5, 5, 3, 'H'); g.ell(16, 10, 5, 2, 'B')
    g.rows(0, 5, [(4, 8), (2, 8), (0, 8), (2, 8), (4, 8)], 'g')
    g.px(19, 5, 'Y'); g.px(20, 5, 'o')
    return g


def ghost():
    """The Bellwarden's choir: a hooded wisp of grey-violet light, mouth open in song."""
    p = {'V': '#b8a8d8', 'v': '#7a6a9a', 'l': '#e8e0f8', 'o': '#2a2040', 'e': '#f0e8ff'}
    g = P(18, 26, (9, 24), p)
    g.ell(9, 8, 7, 7, 'V'); g.rect(2, 8, 16, 20, 'V'); g.ell(7, 6, 3, 3, 'l')
    for x in range(2, 17, 3): g.rect(x, 20, x + 1, 22 + x % 3, 'v')
    g.ell(11, 9, 3, 3.6, 'o'); g.px(10, 8, 'e'); g.px(12, 8, 'e'); g.rect(10, 11, 12, 13, 'o')
    g.rect(14, 4, 15, 16, 'v')
    return g


def homunculus():
    """The Alchemist's creations: a waddling flask-bellied homunculus, green fluid sloshing inside."""
    p = {'K': '#c8d0d8', 'k': '#8a949e', 'p': '#8be04e', 'P': '#4a7a2a', 'o': '#141018', 's': '#a89a7c'}
    g = P(18, 20, (9, 19), p)
    g.ell(9, 11, 7, 7, 'k'); g.ell(9, 12, 5.6, 5.6, 'p'); g.ell(8, 14, 4, 2.4, 'P'); g.px(6, 9, 'K')
    g.rect(7, 2, 11, 5, 'K'); g.rect(6, 1, 12, 1, 's')
    g.px(11, 10, 'o'); g.px(13, 10, 'o')
    g.rect(5, 17, 6, 19, 's'); g.rect(12, 17, 13, 19, 's')
    return g


def reflection():
    """The Mirror Knight's reflections: a hero-shaped shard of silvered glass with a blade."""
    p = {'A': '#a8c4d2', 'a': '#6a8aa0', 'l': '#eef6fa', 'C': '#8ab0c8', 'w': '#e8f8ff', '*': '#ffffff'}
    g = P(24, 40, (10, 38), p)
    g.ell(10, 8, 6, 7, 'A'); g.tri([(4, 6), (10, 1), (10, 12)], 'l'); g.rect(9, 4, 10, 11, '*')
    g.rows(3, 15, [(1, 12), (0, 13)] + [(0, 13)] * 9 + [(1, 12)], 'A'); g.tri([(3, 15), (10, 15), (4, 26)], 'l')
    g.tri([(10, 15), (16, 15), (15, 26)], 'C')
    g.rect(5, 28, 8, 37, 'a'); g.rect(11, 28, 14, 37, 'a')
    g.line(17, 26, 23, 6, 'w', 2)
    return g


def mothling():
    """The Moth Saint's brood: a pale moth as big as a hand, its wings dusted with gold."""
    p = {'W': '#d8ccb0', 'w': '#a89a7c', 'Y': '#e8c84a', 'K': '#2a2030'}
    g = P(22, 16, (11, 14), p)
    g.tri([(10, 8), (0, 0), (2, 12)], 'W'); g.tri([(12, 8), (21, 1), (20, 12)], 'w')
    g.px(4, 5, 'Y'); g.px(17, 5, 'Y')
    g.rect(10, 4, 12, 13, 'K'); g.px(10, 3, 'K'); g.px(12, 3, 'K')
    return g


ADDS = {'mire.tadpole': tadpole, 'bellwarden.ghost': ghost, 'alchemist.homunculus': homunculus,
        'mirror.reflection': reflection, 'moth.mothling': mothling}
