# Overlords' commander portraits: 32x32 head-and-shoulders busts, facing the viewer, drawn with the unit
# sprites' kit (letters, then shading and outline by code). Each function returns (rows, palette).
from kit import G, pal, SKIN, SKIN_DARK, STEEL, GOLD, WOOD

PALE = {'s': '#d8c8c0', 'S': '#a89890'}
DWARF = {'s': '#d0a080', 'S': '#a07858'}


def bust(g, cloth='c', skin='s', mouth='S', eyes='e', wide=False):
    """Shoulders, neck and a front-facing head; returns the head's (left, right, top) for gear."""
    g.rows(3 if wide else 4, 23, [(5, 20), (3, 22), (1, 24), (0, 25), (0, 25), (0, 25), (0, 25), (0, 25), (0, 25)]
           if wide else [(4, 19), (2, 21), (1, 22), (0, 23), (0, 23), (0, 23), (0, 23), (0, 23), (0, 23)], cloth)
    g.rect(13, 18, 18, 23, skin)
    g.rect(13, 22, 18, 23, skin.upper())
    g.ell(15.5, 12, 6.2, 7.2, skin)
    g.px(9, 12, skin)
    g.px(22, 12, skin)
    g.px(13, 12, eyes)
    g.px(18, 12, eyes)
    g.rect(14, 16, 17, 16, mouth)
    return 9, 22, 5


def quartermaster():
    p = pal(SKIN, GOLD, WOOD, {'c': '#7a5a3a', 'k': '#5a4a3a', 'h': '#6a4a2a', 'x': '#c8b890', 'm': '#4a3a2a'})
    g = G(p)
    bust(g, 'c')
    g.rect(14, 23, 17, 31, 'x')  # shirt
    for y in (25, 28):
        g.px(12, y, 'g')
        g.px(19, y, 'g')
    g.rect(9, 4, 22, 7, 'k')  # cap and brim
    g.rect(8, 8, 23, 8, 'K')
    g.rect(10, 3, 21, 3, 'k')
    g.rect(12, 14, 19, 14, 'h')  # moustache
    g.px(11, 15, 'h')
    g.px(20, 15, 'h')
    g.line(24, 18, 28, 13, 'x')  # a quill behind the ear
    g.px(28, 12, 'w')
    return g.strings(), p


def warlord():
    p = pal(SKIN_DARK, STEEL, GOLD, {'c': '#8a2a24', 'a': '#6a7280', 'h': '#d8d0c0', 'r': '#b04a4a'})
    g = G(p)
    bust(g, 'c', wide=True)
    g.ell(4, 25, 4, 3, 'a')  # pauldrons
    g.ell(27, 25, 4, 3, 'a')
    g.rect(8, 3, 23, 10, 'a')  # helm
    g.ell(15.5, 7, 7.5, 5, 'a')
    g.rect(9, 11, 10, 15, 'a')
    g.rect(21, 11, 22, 15, 'a')
    g.rect(15, 6, 16, 14, 'A')  # nose guard
    g.line(8, 5, 4, 0, 'h', 2)  # horns
    g.line(23, 5, 27, 0, 'h', 2)
    g.line(17, 10, 20, 14, 'r')  # a scar
    g.rect(13, 16, 18, 17, 'S')
    return g.strings(), p


def necromancer():
    p = pal(PALE, GOLD, {'c': '#2a2238', 'C': '#1a1428', 'u': '#d8d0c0', '*': '#7af0a0'})
    g = G(p)
    bust(g, 'c', eyes='*')
    g.ell(15.5, 10, 8.5, 9, 'c')  # hood
    g.ell(15.5, 12.5, 5.5, 6.5, 's')
    g.rect(10, 11, 21, 13, 'C')
    g.px(13, 12, '*')
    g.px(18, 12, '*')
    g.rect(14, 16, 17, 16, 'S')
    g.rect(6, 20, 9, 31, 'c')
    g.rect(22, 20, 25, 31, 'c')
    g.ell(15.5, 26, 2.2, 2, 'u')  # a skull clasp
    g.px(14, 26, 'e')
    g.px(17, 26, 'e')
    return g.strings(), p


def alchemist():
    p = pal(SKIN, GOLD, WOOD, {'c': '#4a6a4a', 'h': '#c87a3a', 'x': '#d8c8a0', 'm': '#8a929c', 'z': '#7ad0ff',
                               '*': '#9aff7a', 'q': '#3a8a3a'})
    g = G(p)
    bust(g, 'c')
    g.rect(11, 22, 20, 31, 'x')  # apron
    g.rows(9, 2, [(2, 10), (0, 12), (-1, 13), (-1, 13)], 'h')  # wild hair
    g.px(7, 6, 'h')
    g.px(24, 5, 'h')
    g.rect(9, 7, 22, 8, 'm')  # goggles up on the brow
    g.ell(12.5, 7.5, 2, 1.6, 'z')
    g.ell(18.5, 7.5, 2, 1.6, 'z')
    g.rect(24, 20, 27, 27, 'q')  # a flask
    g.rect(25, 18, 26, 19, 'x')
    g.px(25, 22, '*')
    g.px(26, 24, '*')
    return g.strings(), p


def merchant():
    p = pal(SKIN, GOLD, {'c': '#7a2a5a', 'k': '#3a2a4a', 'x': '#e8e0d0', 'h': '#3a2a20', 'q': '#e05a6a'})
    g = G(p)
    bust(g, 'c')
    g.rows(10, 21, [(1, 10), (0, 11), (1, 10)], 'x')  # a ruff collar
    g.rect(4, 6, 27, 7, 'k')  # a broad hat
    g.ell(15.5, 4, 6, 3, 'k')
    g.rect(10, 5, 21, 5, 'g')
    g.line(21, 3, 27, 0, 'q', 2)  # its feather
    g.rect(10, 8, 11, 13, 'h')
    g.rect(20, 8, 21, 13, 'h')
    g.px(22, 14, 'g')  # an earring
    g.rect(14, 15, 17, 15, 'h')
    g.ell(26, 27, 2.5, 2.5, 'g')  # a coin
    g.px(26, 27, 'G')
    return g.strings(), p


def sage():
    p = pal(SKIN, GOLD, {'c': '#2a4a8a', 'h': '#eeeae0', 'y': '#ffe08a'})
    g = G(p)
    bust(g, 'c')
    g.rows(10, 14, [(0, 11), (0, 11), (1, 10), (1, 10), (2, 9), (2, 9), (3, 8), (3, 8), (4, 7), (4, 7), (5, 6)], 'h')
    g.rect(13, 15, 18, 15, 'S')
    g.rect(12, 13, 19, 13, 'h')
    g.rect(8, 6, 23, 7, 'c')  # a pointed hat, bent at the tip
    for i in range(8):
        w = max(1, 6 - i)
        g.rect(16 - w, 5 - i, 15 + w // 2 + 1, 5 - i, 'c')
    g.rect(18, 0, 21, 0, 'c')
    g.px(13, 3, 'y')
    g.px(17, 1, 'y')
    g.px(11, 5, 'y')
    return g.strings(), p


def beastmaster():
    p = pal(SKIN_DARK, GOLD, {'c': '#5a4a3a', 'f': '#8a8078', 'F': '#5a5450', 'h': '#2a2020', 'u': '#e8e0d0',
                              '*': '#ffd23f'})
    g = G(p)
    bust(g, 'c', wide=True)
    g.rows(3, 21, [(3, 9), (1, 10), (0, 10)], 'f')  # a fur mantle
    g.rows(19, 21, [(2, 8), (1, 10), (1, 11)], 'f')
    g.ell(15.5, 6, 8, 5, 'f')  # a wolf's head over its own
    g.rect(8, 6, 9, 14, 'f')
    g.rect(22, 6, 23, 14, 'f')
    g.rect(9, 0, 11, 3, 'F')  # the wolf's ears
    g.rect(20, 0, 22, 3, 'F')
    g.px(12, 6, '*')
    g.px(19, 6, '*')
    g.rect(13, 9, 18, 10, 'F')
    g.px(14, 11, 'u')
    g.px(17, 11, 'u')
    g.rect(11, 15, 20, 16, 'h')  # a beard
    return g.strings(), p


def archmage():
    p = pal(PALE, GOLD, {'c': '#5a2a7a', 'h': '#eeeae0', 'y': '#ffe08a', '*': '#c8a0ff', 'w': '#6a4a2e'})
    g = G(p)
    bust(g, 'c')
    g.rect(13, 21, 18, 31, 'y')  # a gold stole
    g.rect(14, 16, 17, 19, 'h')  # a goatee
    g.rect(13, 15, 18, 15, 'h')
    for i in range(10):  # a tall hat
        w = max(0, 7 - i * 3 // 4)
        g.rect(15 - w, 6 - i, 16 + w, 6 - i, 'c')
    g.rect(6, 6, 25, 7, 'c')
    g.rect(9, 5, 22, 5, 'y')
    g.line(27, 31, 27, 11, 'w')  # a staff with a glowing orb
    g.ell(27, 9, 2.4, 2.4, '*')
    return g.strings(), p


def survivor():
    p = pal(SKIN, {'c': '#5a5a4a', 'C': '#3e3e32', 'x': '#e8e0d0', 'h': '#6a4a30', 'r': '#a84a3a'})
    g = G(p)
    bust(g, 'c')
    g.rect(9, 4, 22, 6, 'h')  # hair
    g.rect(9, 7, 22, 8, 'x')  # a bandage round the head
    g.px(23, 8, 'x')
    g.px(24, 9, 'x')
    g.px(19, 7, 'r')
    g.line(12, 10, 14, 14, 'r')  # a scar
    for x in range(11, 21, 2):  # stubble
        g.px(x, 17, 'S')
    g.px(4, 26, 'C')  # a torn cloak
    g.rect(5, 24, 8, 25, 'C')
    g.px(26, 27, 'C')
    return g.strings(), p


def blademaster():
    p = pal(SKIN, STEEL, GOLD, {'c': '#2a2a3a', 'h': '#1a1418', 'r': '#c8443a', 'x': '#e8e0d0', 'w': '#5a3a24'})
    g = G(p)
    bust(g, 'c')
    g.rows(9, 21, [(4, 9), (3, 10), (2, 11)], 'x')  # a white collar
    g.line(4, 31, 10, 18, 'w', 2)  # a hilt over the shoulder
    g.rect(9, 17, 12, 18, 'g')
    g.rect(9, 3, 22, 7, 'h')  # hair, tied up
    g.rect(13, 0, 17, 3, 'h')
    g.rect(9, 7, 22, 8, 'r')  # headband
    g.line(8, 8, 5, 11, 'r')
    g.line(12, 11, 14, 11, 'h')  # stern brows
    g.line(17, 11, 19, 11, 'h')
    return g.strings(), p


def forgemaster():
    p = pal(DWARF, STEEL, GOLD, WOOD, {'c': '#5a4030', 'h': '#c85a2a', 'k': '#3a2a20', 'd': '#3a3a40'})
    g = G(p)
    bust(g, 'c', wide=True)
    g.rect(10, 21, 21, 31, 'k')  # a leather apron
    g.rect(9, 4, 22, 7, 'd')  # a soot-dark cap
    g.rows(9, 13, [(0, 13), (0, 13), (0, 13), (1, 12), (1, 12), (2, 11), (2, 11), (3, 10), (4, 9), (5, 8)], 'h')
    g.rect(13, 14, 18, 14, 'S')
    for y in (18, 21):  # braids
        g.px(13, y, 'g')
        g.px(18, y, 'g')
    g.line(26, 31, 26, 15, 'w', 2)  # a hammer on the shoulder
    g.rect(24, 11, 30, 15, 'm')
    g.px(11, 11, 'd')  # soot
    return g.strings(), p


def oracle():
    p = pal(SKIN_DARK, GOLD, {'c': '#2a6a7a', 'C': '#1e4e5c', 'x': '#e8e0d0', '*': '#9ff0ff', 'h': '#1a1418'})
    g = G(p)
    bust(g, 'c')
    g.ell(15.5, 9, 7.5, 6, 'h')  # dark hair
    g.rect(8, 9, 10, 22, 'h')
    g.rect(21, 9, 23, 22, 'h')
    g.ell(15.5, 13, 5.6, 5.5, 's')
    g.rect(10, 11, 21, 13, 'x')  # a blindfold
    g.px(15, 8, '*')  # the third eye
    g.px(16, 8, '*')
    g.px(15, 7, 'g')
    g.px(16, 9, 'g')
    g.rect(14, 16, 17, 16, 'S')
    g.ell(15.5, 26, 1.8, 1.8, '*')
    return g.strings(), p


PORTRAITS = {k: globals()[k] for k in ('quartermaster', 'warlord', 'necromancer', 'alchemist', 'merchant', 'sage',
                                       'beastmaster', 'archmage', 'survivor', 'blademaster', 'forgemaster', 'oracle')}
