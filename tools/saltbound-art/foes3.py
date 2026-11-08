# The first three regions' and the Peak's newer enemies (content/isles.py), drawn facing right like foes.py.
from common import *

DROWN = {'s': '#8fb0a0', 'S': '#6a8a7c'}  # drowned skin: grey-green
PALE = {'s': '#a8c0c8', 'S': '#84a0aa'}   # deep-water pallor


# ================================================================ Coral Shallows
def urchin():  # spine urchin: a purple ball bristling with long spines, two small eyes peering out
    pal = {'P': '#6a3a8a', 'p': '#4e2a6a', 'q': '#9a6ac0', 'n': '#d8c0f0', 'e': '#ffe27a'}
    g = G(pal)
    for a, b in (((4, 18), (9, 20)), ((6, 11), (10, 15)), ((12, 6), (13, 12)), ((20, 7), (18, 12)), ((26, 12), (21, 15)),
                 ((28, 19), (23, 20)), ((25, 26), (21, 24)), ((6, 26), (9, 24)), ((16, 4), (16, 10))):
        g.line(a[0], a[1], b[0], b[1], 'n')
    g.ell(15, 19, 8, 7, 'P'); g.ell(15, 22, 7, 3.5, 'p'); g.ell(13, 16, 3, 2, 'q')
    g.px(17, 18, 'e'); g.px(20, 18, 'e')
    for x in (9, 12, 15, 18, 21): g.px(x, 26, 'p')
    return g

def kelp_strangler():  # kelp strangler: a tangle of dark kelp fronds with grasping vine-arms and a pale bulb eye
    pal = {'K': '#3a6a3a', 'k': '#284e2a', 'G': '#6fa850', 'Y': '#e8e070', 'e': '#1a1420', 'w': '#5a4a30'}
    g = G(pal)
    for x, top in ((9, 8), (13, 4), (17, 6), (21, 9)):
        g.line(x, 29, x + (1 if x % 2 else -1), top, 'K', 2)
    g.ell(15, 22, 7, 7, 'k'); g.ell(15, 18, 5, 5, 'K')
    g.ell(16, 15, 2.5, 2.5, 'Y'); g.px(17, 15, 'e')
    g.line(20, 17, 27, 12, 'G', 2); g.line(27, 12, 29, 15, 'G'); g.line(10, 19, 4, 14, 'G', 2); g.line(4, 14, 2, 17, 'G')
    for x, y in ((8, 10), (22, 11), (12, 25), (19, 26)): g.px(x, y, 'G')
    g.rect(8, 29, 22, 30, 'w')
    return g

def pearl_diver():  # drowned pearl diver: pale drowned diver with a net bag of pearls and a short harpoon
    pal = {**DROWN, 'B': '#3a5a6a', 'b': '#2a4250', 'W': '#c8c8c0', 'w': '#6a5a40', 'p': '#f0f0e8', 'g': '#c8e070', 'k': '#24202a', 'L': '#2a4250', 'o': '#0e1a1a'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'B'); g.rect(9, 20, 18, 21, 'b')
    g.rect(6, 14, 8, 20, 's'); g.ell(6, 23, 2.5, 2.5, 'w'); g.px(5, 22, 'p'); g.px(7, 23, 'p'); g.px(6, 24, 'p')
    g.rect(19, 14, 21, 17, 's'); g.line(19, 18, 29, 12, 'w'); g.text(28, 10, ['W', 'WW', 'W'])
    face(g, 10, 5, 8, 7, eyes=False); g.px(12, 8, 'g'); g.px(15, 8, 'g'); g.rect(13, 10, 14, 10, 'o')
    g.rect(9, 3, 18, 5, 'W'); g.ell(13.5, 7, 5, 4.5, 'W'); g.ell(13.5, 7.5, 3.5, 3, 's'); g.px(12, 7, 'g'); g.px(15, 7, 'g')
    return g


# ================================================================ Smugglers' Keys
def rum_runner():  # rum runner: a stocky smuggler in a striped shirt and bandana, a lit bottle in hand
    pal = {**SKIN2, 'W': '#d8d0c0', 'w': '#9a3a3a', 'h': '#b83a3a', 'L': '#3a3a4a', 'k': '#24202a', 'G': '#4a8a5a', 'F': '#ffb03a', 'Y': '#ffe27a', 'e': E, 'H': '#2a1a14'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'W')
    for y in range(14, 23, 2): g.rect(8, y, 19, y, 'w')
    g.rect(9, 21, 18, 22, 'k')
    g.rect(6, 13, 8, 20, 's'); g.rect(19, 14, 21, 17, 's')
    g.rect(21, 11, 22, 17, 'G'); g.rect(21, 9, 22, 10, 'G'); g.px(21, 8, 'F'); g.px(22, 7, 'Y'); g.px(21, 6, 'F')
    face(g, 10, 6, 8, 6); g.rect(11, 10, 16, 10, 'H')
    g.rect(10, 4, 17, 5, 'h'); g.rect(9, 5, 9, 6, 'h'); g.text(6, 6, ['hhh', ' h'])
    return g

def parrot():  # lookout parrot: a bright green parrot with a red crest and a tiny eyepatch, wings flared
    pal = {'G': '#3ab84a', 'g': '#268a34', 'R': '#d83a3a', 'Y': '#ffd23f', 'B': '#3a6ad8', 'e': E, 'k': '#1a1420', 'w': '#5a4a30'}
    g = G(pal)
    g.ell(14, 18, 5, 6.5, 'G'); g.ell(13, 21, 3, 3.5, 'Y')
    g.ell(17, 10, 4, 4, 'G'); g.tri([(20, 10), (24, 12), (20, 13)], 'Y'); g.px(21, 12, 'k')
    g.rect(15, 5, 17, 6, 'R'); g.px(14, 6, 'R'); g.px(18, 9, 'e'); g.line(15, 8, 19, 10, 'k')
    g.tri([(10, 14), (2, 10), (9, 21)], 'g'); g.tri([(9, 15), (4, 13), (9, 19)], 'B')
    g.rect(12, 24, 13, 29, 'R'); g.rect(15, 24, 16, 28, 'B')
    g.rect(8, 29, 22, 29, 'w'); g.text(11, 28, ['k k k'])
    return g

def quartermaster():  # smuggler quartermaster: a heavyset man in a long coat with a ledger and a flared blunderbuss
    pal = {**SKIN, 'B': '#5a3a2a', 'b': '#44281e', 'T': '#c8a040', 'L': '#2a2a34', 'k': '#1a1420', 'W': '#8a8a92', 'w': '#5a3a20', 'H': '#6a6a6a', 'h': '#2a2a34', 'X': '#d8d0b0', 'e': E}
    g = G(pal)
    legs(g, 'L')
    g.rows(7, 13, [(1, 12), (0, 13), (0, 13), (0, 13), (0, 13), (0, 13), (-1, 14), (-1, 14), (-1, 14), (-2, 15), (-2, 15), (-2, 15)], 'B')
    g.rect(12, 13, 15, 23, 'b'); g.rect(9, 18, 18, 18, 'T'); g.px(13, 15, 'T'); g.px(13, 20, 'T')
    g.rect(2, 17, 7, 22, 'X'); g.rect(4, 17, 4, 22, 'w')
    g.rect(19, 15, 22, 18, 'w'); g.rect(22, 14, 28, 16, 'W'); g.text(28, 12, ['WW', 'WWW', 'WWW', 'WW'])
    face(g, 10, 5, 8, 7); g.rows(10, 9, [(0, 7), (1, 6), (2, 5)], 'H')
    g.rows(8, 1, [(3, 9), (0, 12), (2, 10)], 'h'); g.rect(8, 3, 19, 3, 'h')
    return g


# ================================================================ Stormcrag
def rockling():  # cliffside rockling: a squat living boulder, mossy top, little stone fists and glowing eyes
    pal = {'R': '#8a8478', 'r': '#6a6458', 'Q': '#aaa498', 'M': '#5a8a4a', 'e': '#9fe8ff', 'k': '#4a463e'}
    g = G(pal)
    g.ell(14, 19, 9, 8.5, 'R'); g.ell(14, 23, 8, 4, 'r'); g.ell(11, 15, 4, 3, 'Q')
    g.rows(8, 10, [(3, 8), (1, 11), (0, 12)], 'M')
    g.rect(15, 17, 16, 18, 'e'); g.rect(19, 17, 20, 18, 'e')
    g.line(9, 21, 13, 19, 'k'); g.line(16, 24, 19, 22, 'k')
    g.ell(25, 21, 3, 2.6, 'r'); g.ell(4, 22, 2.6, 2.4, 'r')
    g.rect(9, 27, 12, 29, 'r'); g.rect(16, 27, 19, 29, 'r')
    return g

def gale_sprite():  # gale sprite: a wisp of pale wind curling into a small laughing face, leaves caught in it
    pal = {'W': '#e0f0f8', 'w': '#a8d0e0', 'b': '#7ab0c8', 'e': '#2a4a6a', 'G': '#8ac86a'}
    g = G(pal)
    g.ell(16, 11, 6, 5.5, 'W'); g.ell(16, 12, 4, 3.5, 'w')
    g.px(14, 11, 'e'); g.px(18, 11, 'e'); g.line(15, 14, 17, 14, 'e')
    g.line(11, 15, 7, 20, 'W', 2); g.line(7, 20, 12, 24, 'w', 2); g.line(12, 24, 9, 29, 'b')
    g.line(20, 15, 25, 19, 'w'); g.line(25, 19, 22, 23, 'b')
    g.text(4, 6, ['w  w', ' ww ']); g.text(24, 4, ['ww', '  w'])
    g.px(6, 13, 'G'); g.px(24, 25, 'G'); g.px(13, 27, 'G')
    return g

def stormcaller():  # stormcaller acolyte: a hooded figure in storm-grey robes, a forked iron rod crackling with lightning
    pal = {**SKIN, 'B': '#4a5468', 'b': '#3a4256', 'T': '#8fa8c8', 'h': '#3a4256', 'x': '#2a3040', 'W': '#8a8a92', 'Y': '#fff27a', 'y': '#9fd8ff', 'e': E, 'k': '#1a1420'}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'B')
    g.rect(13, 14, 14, 28, 'b'); g.rect(8, 20, 19, 20, 'T')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rect(21, 4, 21, 30, 'W'); g.text(19, 1, ['W   W', 'W   W', ' W W ', '  W  '])
    g.line(18, 0, 16, 3, 'Y'); g.line(24, 0, 26, 3, 'Y'); g.px(21, 0, 'y'); g.px(15, 4, 'y'); g.px(27, 4, 'y')
    g.rect(19, 15, 21, 18, 'B'); g.rect(20, 18, 22, 19, 's')
    g.ell(13.5, 8, 6.5, 6.5, 'h'); g.rect(8, 9, 19, 13, 'h'); g.rect(10, 7, 17, 12, 'x'); g.rect(11, 8, 16, 12, 's')
    g.px(12, 10, 'y'); g.px(15, 10, 'y')
    return g


# ================================================================ the Peak: the Drowned Crown's court
def drowned_knight():  # drowned knight: barnacled, rusted plate dripping water, a green-glowing visor, a broad blade
    pal = {'A': '#6a7a7a', 'a': '#4e5c5c', 'R': '#8a5a3a', 'c': '#d8d0c0', 'g': '#9fe86a', 'W': '#b8c4c8', 'w': '#4a3a2a', 'k': '#24202a', 'L': '#4e5c5c', 'D': '#5ab0d0'}
    g = G(pal)
    legs(g, 'L', 'k')
    torso(g, 'A'); g.rect(9, 20, 18, 21, 'a'); g.rect(12, 14, 15, 19, 'a')
    for x, y in ((9, 15), (17, 17), (11, 22), (16, 13)): g.px(x, y, 'c')
    g.px(10, 18, 'R'); g.px(18, 21, 'R')
    g.rect(5, 13, 8, 20, 'A'); g.rect(19, 14, 22, 17, 'A'); g.rect(21, 17, 23, 19, 'w')
    g.line(23, 16, 30, 6, 'W', 2); g.px(30, 5, 'W')
    g.rect(9, 3, 18, 12, 'A'); g.rect(10, 7, 17, 8, 'k'); g.px(12, 7, 'g'); g.px(15, 7, 'g'); g.rect(13, 1, 14, 2, 'a')
    g.px(8, 24, 'D'); g.px(19, 26, 'D'); g.px(7, 21, 'D')
    return g

def crown_herald():  # crown herald: a gaunt drowned courtier in a sodden tabard, holding up a gilded rod and a scroll
    pal = {**PALE, 'B': '#2a4a6a', 'b': '#1e3650', 'T': '#e0c060', 'X': '#d8d0b0', 'w': '#8a6a3a', 'k': '#1a1420', 'L': '#1e3650', 'e': '#9fe8ff', 'H': '#4a5a5a'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'B'); g.rect(11, 13, 16, 23, 'T'); g.rect(12, 14, 15, 22, 'b'); g.px(13, 17, 'T'); g.px(14, 17, 'T')
    g.rect(6, 13, 8, 18, 'B'); g.rect(4, 17, 8, 21, 'X'); g.rect(4, 17, 4, 21, 'w')
    g.rect(19, 12, 21, 14, 'B'); g.rect(20, 10, 21, 11, 's'); g.rect(21, 2, 22, 10, 'T'); g.ell(21.5, 2, 2, 1.6, 'T')
    face(g, 10, 5, 8, 7, eyes=False); g.px(12, 8, 'e'); g.px(15, 8, 'e'); g.rect(12, 10, 15, 10, 'S')
    g.rect(10, 3, 17, 4, 'H'); g.rect(9, 4, 9, 9, 'H'); g.rect(18, 4, 18, 8, 'H')
    g.text(10, 1, ['T T T T', 'TTTTTTT'])
    return g

def abyss_angler():  # abyssal angler: a black deep-sea fish, a huge fanged mouth and a glowing lure on a stalk
    pal = {'D': '#2a2e3e', 'd': '#1e2230', 'B': '#3a4058', 'w': '#f0f0e0', 'Y': '#e8ff7a', 'y': '#9fe86a', 'e': '#ff6a5a'}
    g = G(pal)
    g.ell(13, 18, 10, 8, 'D'); g.ell(13, 22, 8, 3.5, 'd'); g.ell(10, 15, 4, 3, 'B')
    g.tri([(3, 18), (0, 12), (0, 24)], 'd')
    g.rect(16, 19, 24, 23, 'd'); g.text(16, 19, ['w w w w']); g.text(17, 23, ['w w w'])
    g.px(17, 14, 'e')
    g.line(14, 10, 19, 4, 'B'); g.line(19, 4, 24, 6, 'B'); g.ell(25, 7.5, 2, 2, 'Y'); g.px(25, 7, 'y')
    g.tri([(12, 26), (8, 30), (16, 28)], 'd')
    return g

def brine_wraith():  # brine wraith: a drifting shroud of sea-water, a hollow drowned face, icy trails dripping
    pal = {'B': '#5ab0d0', 'b': '#3a88a8', 'W': '#cfe8f0', 'D': '#1e3a4a', 'e': '#e8ff7a', 'i': '#e0f8ff'}
    g = G(pal)
    g.rows(8, 9, [(3, 9), (2, 10), (1, 11), (1, 11), (0, 12), (0, 12), (0, 12), (-1, 13), (-1, 13), (-1, 13), (-1, 14),
                  (-2, 14), (-2, 15), (-2, 15), (-3, 15), (-3, 16)], 'B')
    g.ell(14, 9, 6, 6, 'B'); g.ell(13, 7, 3, 2, 'W'); g.ell(14, 10, 3.5, 3.5, 'D'); g.px(12, 10, 'e'); g.px(16, 10, 'e')
    for x, y in ((6, 24), (10, 25), (15, 24), (19, 25), (23, 24)): g.rect(x, y, x + 1, y + 3, 'b')
    for x, y in ((7, 29), (16, 29), (22, 28)): g.px(x, y, 'i')
    g.line(21, 15, 27, 11, 'B', 2); g.px(28, 10, 'i')
    return g

def coral_colossus():  # coral colossus: a hulking giant grown from red and pink coral, barnacled fists, a glowing heart
    pal = {'C': '#d0605a', 'c': '#a8443e', 'P': '#ff9a8a', 'W': '#e8d8c8', 'Y': '#ffe27a', 'k': '#6a2a26', 'e': '#ffe27a'}
    g = G(pal)
    g.rect(8, 23, 12, 29, 'c'); g.rect(16, 23, 20, 29, 'c'); g.rect(7, 29, 12, 30, 'k'); g.rect(16, 29, 21, 30, 'k')
    g.ell(14, 17, 9, 8, 'C'); g.ell(14, 20, 7, 4, 'c'); g.ell(14, 17, 2.4, 2.4, 'Y')
    g.rect(1, 13, 5, 23, 'C'); g.rect(23, 13, 27, 23, 'C'); g.ell(3, 24, 3, 2.6, 'W'); g.ell(25, 24, 3, 2.6, 'W')
    g.ell(14, 8, 5, 4, 'C'); g.px(12, 8, 'e'); g.px(16, 8, 'e')
    g.text(8, 1, ['P  P   P', 'PP P  PP', ' PPPPPP ']); g.text(3, 9, ['P', 'PP']); g.text(24, 9, [' P', 'PP'])
    for x, y in ((9, 15), (19, 14), (11, 21), (18, 20)): g.px(x, y, 'P')
    return g


ALL = [urchin, kelp_strangler, pearl_diver, rum_runner, parrot, quartermaster, rockling, gale_sprite, stormcaller,
       drowned_knight, crown_herald, abyss_angler, brine_wraith, coral_colossus]
