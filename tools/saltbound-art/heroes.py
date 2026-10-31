# Saltbound's heroes: four options each for the owner to pick from (see docs/saltbound.md).
from common import *

# ------------------------------------------------------------------ Vanguard: tank
def vanguard1():  # harbour guard: crested morion, breastplate over a navy coat, brass-rimmed buckler, boarding axe raised
    pal = {**SKIN, 'A': '#a8b0bc', 'a': '#7a8494', 'N': '#2e4466', 'n': '#22344e', 'Y': '#c8a040', 'y': '#a88430',
           'R': '#7a5232', 'r': '#a0703e', 'w': '#dfe6ee', 'h': '#5a3a24', 'k': '#2a2430', 'L': '#3a3a4a', 'e': E, 'u': '#5a3a24'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'N')
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8), (1, 8)], 'A')  # breastplate
    g.rect(13, 13, 14, 19, 'a'); g.rect(9, 20, 18, 21, 'h'); g.rect(13, 20, 14, 21, 'Y')
    g.rect(8, 22, 19, 23, 'n')
    g.rect(6, 13, 8, 15, 'a'); g.rect(19, 13, 21, 15, 'a')
    # axe arm raised
    g.rect(20, 15, 22, 18, 'N'); g.rect(21, 18, 23, 19, 's'); g.rect(22, 3, 23, 20, 'h')
    g.text(20, 2, ['  ww ', ' wwww', 'wwwww', ' wwww', '  ww '])
    g.rect(23, 3, 25, 6, 'A')
    # buckler
    g.ell(6, 19, 5, 5, 'Y'); g.ell(6, 19, 4, 4, 'R'); g.ell(6, 19, 2.8, 2.8, 'r'); g.ell(6, 19, 1.2, 1.2, 'Y')
    # face and morion
    face(g, 10, 7, 8, 6); g.rect(11, 11, 16, 11, 'u')
    g.rows(8, 6, [(0, 11)], 'A'); g.rows(9, 2, [(2, 7), (1, 8), (0, 9), (0, 9)], 'A'); g.rect(9, 6, 18, 6, 'a')
    g.rect(12, 0, 15, 2, 'A'); g.rect(13, 0, 14, 0, 'a')
    return g

def vanguard2():  # diver: brass diving helmet with a round porthole, canvas suit, riveted door-shield, maul
    pal = {'B': '#c8a040', 'b': '#9a7a2e', 'g': '#5a8ab0', 'G': '#8ec0e0', 'C': '#8a8070', 'c': '#6a6254', 'D': '#6a5038', 'd': '#4e3a28',
           'i': '#a8b0bc', 'k': '#2a2430', 'L': '#6a6254', 'h': '#5a3a24', 'w': '#9aa2ae'}
    g = G(pal)
    legs(g, 'L', 'k')
    torso(g, 'C')
    g.rect(9, 20, 18, 21, 'd'); g.rect(13, 20, 14, 21, 'B')
    g.rect(8, 13, 19, 14, 'B')  # brass collar
    # maul over the shoulder
    g.rect(20, 15, 22, 18, 'C'); g.rect(22, 6, 23, 19, 'h'); g.rect(20, 3, 25, 7, 'w'); g.rect(20, 7, 25, 7, 'c')
    # door shield
    g.rect(1, 13, 9, 26, 'D'); g.rect(2, 14, 8, 25, 'd'); g.rect(1, 17, 9, 17, 'i'); g.rect(1, 22, 9, 22, 'i')
    for y in (15, 20, 24):
        g.px(2, y, 'i'); g.px(8, y, 'i')
    # helmet
    g.ell(13.5, 7, 6, 6, 'B'); g.rect(8, 10, 19, 12, 'b')
    g.ell(14.5, 7, 3, 3, 'b'); g.ell(14.5, 7, 2.2, 2.2, 'g'); g.px(14, 6, 'G'); g.px(13, 7, 'G')
    g.px(9, 7, 'b'); g.px(18, 4, 'b')
    return g

def vanguard3():  # bosun: red bandana, big beard, leather vest, round wooden shield with an iron boss, cutlass
    pal = {**SKIN, 'R': '#a83030', 'H': '#6a3a22', 'V': '#7a5236', 'v': '#5a3a26', 'W': '#d8d0c0', 'O': '#8a5a32', 'o': '#a8783e',
           'i': '#7a8494', 'w': '#dfe6ee', 'Y': '#c8a040', 'h': '#5a3a24', 'k': '#2a2028', 'L': '#3e3448', 'e': E}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'W')
    g.rows(8, 13, [(1, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'V'); g.rows(16, 13, [(0, 2), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'V')
    g.rect(9, 21, 18, 22, 'h'); g.rect(13, 21, 14, 22, 'Y')
    # cutlass arm forward
    g.rect(20, 15, 22, 18, 'W'); g.rect(21, 18, 23, 19, 's'); g.rect(22, 17, 24, 17, 'Y'); g.line(23, 16, 27, 11, 'w', 2); g.px(28, 10, 'w')
    # shield
    g.ell(6, 19, 5.5, 5.5, 'O'); g.ell(6, 19, 4.4, 4.4, 'o'); g.rect(1, 19, 11, 19, 'O'); g.rect(6, 14, 6, 24, 'O'); g.ell(6, 19, 1.6, 1.6, 'i')
    # head: bandana and beard
    face(g, 10, 5, 8, 6)
    g.rect(10, 4, 17, 6, 'R'); g.rect(9, 5, 9, 6, 'R'); g.text(7, 6, ['RR', ' R'])
    g.rows(9, 9, [(1, 8), (0, 9), (0, 9), (1, 8), (2, 7), (3, 6)], 'H'); g.rect(12, 10, 15, 10, 's'); g.rect(12, 9, 15, 9, 'H')
    return g

def vanguard4():  # marine: tricorn, red coat with brass buttons, steel gorget, tall tower shield with an anchor, short spear
    pal = {**SKIN, 'T': '#2a2430', 't': '#c8a040', 'R': '#9a3030', 'r': '#7a2424', 'W': '#d8d0c0', 'A': '#a8b0bc', 'a': '#7a8494',
           'P': '#3a5a8a', 'p': '#2a4470', 'Y': '#c8a040', 'w': '#dfe6ee', 'h': '#5a3a24', 'k': '#2a2430', 'L': '#d8d0c0', 'e': E, 'u': '#5a3a24'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'R')
    g.rect(12, 14, 15, 23, 'W'); g.px(13, 16, 'Y'); g.px(13, 19, 'Y'); g.px(13, 22, 'Y')
    g.rect(9, 21, 18, 21, 'k')
    # spear upright in the right hand
    g.rect(20, 15, 22, 18, 'R'); g.rect(21, 18, 23, 19, 's'); g.rect(22, 2, 22, 28, 'h'); g.text(21, 0, [' w ', 'www', 'www', ' w '])
    # tower shield with an anchor
    g.rect(1, 12, 9, 27, 'P'); g.rect(1, 12, 9, 12, 'Y'); g.rect(1, 27, 9, 27, 'Y'); g.rect(1, 12, 1, 27, 'Y'); g.rect(9, 12, 9, 27, 'Y')
    g.rect(5, 15, 5, 23, 'W'); g.rect(3, 16, 7, 16, 'W'); g.text(2, 21, ['W   W', ' W W ', '  W  ']); g.px(5, 14, 'W')
    # head, gorget, tricorn
    face(g, 10, 6, 8, 6); g.rect(11, 10, 16, 10, 'u')
    g.rect(10, 12, 17, 12, 'A')
    g.rows(7, 3, [(2, 11), (0, 13), (1, 12)], 'T'); g.rect(10, 1, 17, 3, 'T'); g.rect(7, 4, 20, 4, 't')
    return g

# ------------------------------------------------------------------ Arcanist: caster
def arcanist1():  # tide witch: teal hood and robes, seaweed hair, coral staff with a glowing pearl
    pal = {**SKIN, 'H': '#2a6a6a', 'h': '#1e5050', 'K': '#4a7a3a', 'C': '#e07060', 'c': '#b85048', 'O': '#dff4ff', 'o': '#8fd8f0',
           'Y': '#c8a040', 'k': '#2a2230', 'n': '#14282c', 'e': E}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'H')
    g.rect(13, 14, 14, 28, 'h'); g.rect(8, 20, 19, 20, 'Y')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    # staff of coral
    g.rect(21, 7, 22, 30, 'c'); g.text(19, 3, ['C   C', 'CC CC', ' CCC ', '  C  ']); g.ell(21.5, 2.5, 1.8, 1.8, 'O'); g.px(21, 2, 'o')
    g.rows(19, 15, [(0, 2), (0, 3), (1, 3)], 'h'); g.rect(20, 17, 22, 19, 's')
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], 'h'); g.rect(6, 19, 8, 20, 's')
    # hood with seaweed hair
    g.ell(13.5, 8, 6.5, 6.5, 'H'); g.rect(8, 9, 19, 13, 'H')
    g.rect(10, 8, 17, 12, 'n'); g.rect(11, 9, 16, 12, 's'); g.rect(11, 9, 16, 9, 'S'); g.px(12, 10, 'e'); g.px(15, 10, 'e')
    g.rect(10, 9, 10, 15, 'K'); g.rect(17, 9, 17, 14, 'K'); g.px(9, 14, 'K'); g.px(18, 15, 'K')
    return g

def arcanist2():  # navigator: wide-brimmed hat, long blue coat, a glowing astrolabe held up
    pal = {**SKIN, 'T': '#2a2a3a', 't': '#3a3a52', 'B': '#2e4a7a', 'b': '#22385e', 'W': '#d8d0c0', 'Y': '#d0a840', 'y': '#a88430',
           'O': '#9ff0ff', 'o': '#3ab8d8', 'k': '#2a2230', 'L': '#4a3a30', 'e': E, 'u': '#6a4a2e'}
    g = G(pal)
    legs(g, 'L')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13)], 'B')
    g.rect(12, 13, 15, 22, 'W'); g.rect(13, 13, 14, 24, 'b'); g.rect(8, 19, 19, 19, 'u'); g.px(13, 19, 'Y')
    # arm raised with the astrolabe
    g.rows(19, 13, [(0, 2), (0, 3), (1, 4), (2, 4)], 'B'); g.rect(22, 10, 24, 12, 's')
    g.ell(23.5, 6.5, 3.4, 3.4, 'Y'); g.ell(23.5, 6.5, 2.4, 2.4, 'o'); g.ell(23.5, 6.5, 1.2, 1.2, 'O'); g.rect(20, 6, 27, 6, 'y')
    g.px(26, 2, 'O'); g.px(20, 3, 'O')
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'B'); g.rect(6, 20, 8, 21, 's')
    # face, beard stubble, wide hat
    face(g, 10, 6, 8, 6); g.rect(11, 10, 16, 11, 'u'); g.rect(12, 10, 15, 10, 's')
    g.rect(6, 5, 21, 5, 'T'); g.rect(7, 6, 20, 6, 't'); g.rows(10, 1, [(1, 6), (0, 7), (0, 7), (0, 7)], 'T'); g.rect(10, 4, 17, 4, 'Y')
    return g

def arcanist3():  # salt wizard: bent sea-green hat, kelp-green beard, driftwood staff with a blue crystal
    pal = {**SKIN, 'H': '#2a6a5a', 'h': '#1e5044', 'Y': '#c8a040', 'b': '#6aa060', 'B': '#4a7a44', 'w': '#7a5a3a', 'W': '#5a4028',
           'c': '#7fd8e8', 'C': '#3a9ab8', 'e': E, 'l': '#5a3a24', 'k': '#2e2438', 'R': '#1e4a40'}
    g = G(pal)
    g.rect(21, 6, 22, 30, 'w'); g.text(19, 1, [' WWW ', 'W ccW', 'WCc W', 'W cCW', ' WWW '])
    g.rows(9, 14, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12)], 'H')
    g.rect(13, 21, 14, 27, 'R'); g.rect(7, 28, 21, 28, 'Y')
    g.rect(9, 20, 18, 20, 'l'); g.px(13, 20, 'Y')
    g.rows(7, 15, [(1, 2), (0, 2), (0, 2), (0, 2), (0, 2), (0, 2)], 'h'); g.rect(7, 21, 9, 22, 's')
    g.rows(18, 15, [(0, 1), (0, 2), (1, 3)], 'h'); g.rect(20, 17, 22, 19, 's')
    g.rows(10, 13, [(0, 7), (0, 7), (0, 7), (1, 6), (1, 6), (2, 5), (3, 4), (3, 3)], 'b'); g.px(11, 15, 'B'); g.px(15, 17, 'B'); g.px(13, 18, 'B')
    g.rect(10, 11, 17, 11, 'S'); g.rect(10, 12, 17, 12, 's'); g.px(12, 12, 'e'); g.px(15, 12, 'e')
    g.rows(5, 9, [(2, 15), (0, 17)], 'H'); g.rect(9, 8, 18, 8, 'Y')
    g.tri([(9, 8.5), (19, 8.5), (14, 1.5)], 'H'); g.text(14, 0, [' hh', 'hhH', 'hH '])
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    return g

def arcanist4():  # stormcaller: bald, blue tattoos, oilskin coat, lightning crackling in a raised hand
    pal = {**SKIN2, 'O': '#c8a040', 'o': '#a08030', 'D': '#3a3a4a', 'd': '#2a2a38', 't': '#3a6aa8', 'z': '#e8f6ff', 'Z': '#7fd0ff',
           'k': '#2a2230', 'L': '#2a2a38', 'e': E, 'u': '#4a3020'}
    g = G(pal)
    legs(g, 'L')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13)], 'O')
    g.rect(12, 13, 15, 24, 'D'); g.rect(13, 13, 14, 24, 'd'); g.rect(8, 19, 19, 19, 'o')
    # raised hand with lightning
    g.rows(19, 13, [(0, 2), (0, 3), (1, 4), (2, 4)], 'O'); g.rect(22, 10, 24, 12, 's')
    g.text(20, 1, ['  z  ', ' Zz  ', '  zZ ', ' zZ  ', 'Zz zZ', ' Z z ', '  Z  '])
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'O'); g.rect(6, 20, 8, 21, 's'); g.px(7, 18, 't')
    # bald head with tattoos and a beard
    g.ell(13.5, 7.5, 4.5, 4.5, 's'); g.rect(10, 7, 17, 12, 's'); g.px(12, 8, 'e'); g.px(15, 8, 'e')
    g.px(11, 4, 't'); g.px(12, 5, 't'); g.px(16, 4, 't'); g.px(15, 5, 't'); g.px(17, 7, 't')
    g.rect(11, 10, 16, 12, 'u'); g.rect(12, 10, 15, 10, 's')
    return g

# ------------------------------------------------------------------ Mender: healer
def mender1():  # lamplighter: white wimple and grey habit, lantern held high
    pal = {**SKIN, 'W': '#e8e2d4', 'w': '#c8c0b0', 'G': '#6a6878', 'g': '#52505e', 'Y': '#c8a040', 'y': '#ffd870', 'F': '#fff2b0',
           'i': '#3a3440', 'k': '#2a2430', 'e': E, 'r': '#a03a3a'}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'G')
    g.rect(10, 13, 17, 15, 'W'); g.rect(13, 16, 14, 22, 'Y'); g.rect(11, 18, 16, 18, 'Y'); g.rect(8, 21, 19, 21, 'g')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    # lantern held high
    g.rows(19, 13, [(0, 2), (0, 3), (1, 4), (2, 4)], 'G'); g.rect(22, 10, 24, 12, 's'); g.rect(23, 4, 23, 9, 'i')
    g.rect(21, 4, 25, 4, 'i'); g.rect(21, 5, 25, 9, 'Y'); g.rect(22, 6, 24, 8, 'y'); g.px(23, 7, 'F'); g.rect(22, 10, 24, 10, 'i'); g.px(23, 3, 'i')
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], 'G'); g.rect(6, 19, 8, 20, 's')
    # wimple
    g.ell(13.5, 8, 6, 6.5, 'W'); g.rect(8, 9, 19, 13, 'W'); g.rect(8, 11, 8, 14, 'w'); g.rect(19, 11, 19, 14, 'w')
    g.rect(10, 7, 17, 12, 's'); g.rect(10, 7, 17, 7, 'w'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(12, 11, 15, 11, 'S')
    return g

def mender2():  # ship's surgeon: spectacles, rolled sleeves, long apron, black bag
    pal = {**SKIN, 'H': '#5a3a24', 'W': '#e0dacb', 'w': '#b8b0a0', 'V': '#4a5a3a', 'g': '#5fb07a', 'B': '#2a2430', 'b': '#3e3446',
           'Y': '#c8a040', 'k': '#2a2430', 'L': '#4a4048', 'e': E, 'q': '#cfe6f0', 'u': '#7a5a3a'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'V')
    g.rows(10, 13, [(0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (-1, 8), (-1, 8), (-1, 8), (-1, 8), (-1, 8), (-1, 8)], 'W')
    g.rect(12, 16, 15, 16, 'g'); g.rect(13, 15, 14, 18, 'g')
    g.rect(6, 13, 8, 19, 'V'); g.rect(6, 19, 8, 20, 's')
    # bag held out
    g.rect(19, 14, 21, 18, 'V'); g.rect(20, 18, 22, 19, 's'); g.rect(19, 20, 26, 25, 'B'); g.rect(20, 21, 25, 24, 'b'); g.rect(21, 19, 24, 19, 'B'); g.rect(22, 22, 23, 22, 'Y')
    # head: hair, spectacles
    face(g, 10, 5, 8, 7, eyes=False)
    g.rect(10, 3, 17, 5, 'H'); g.rect(9, 4, 9, 8, 'H'); g.rect(18, 4, 18, 7, 'H')
    g.rect(11, 7, 13, 8, 'q'); g.rect(15, 7, 17, 8, 'q'); g.px(14, 7, 'u'); g.px(12, 8, 'e'); g.px(16, 8, 'e')
    g.rect(12, 10, 15, 10, 'S')
    return g

def mender3():  # herbalist: straw hat, green shawl, staff hung with a little lantern, herb satchel
    pal = {**SKIN, 'Y': '#d8b860', 'y': '#b8983e', 'G': '#4a7a44', 'g': '#3a6034', 'D': '#8a6a4a', 'd': '#6a503a', 'w': '#6a4a2e',
           'l': '#ffd870', 'i': '#3a3440', 'b': '#6aa060', 'k': '#2a2430', 'L': '#5a4a3a', 'e': E, 'H': '#7a4a2a'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'D')
    g.rows(8, 13, [(0, 11), (0, 11), (1, 10), (2, 9), (3, 8), (4, 7)], 'G'); g.px(13, 18, 'g')
    g.rect(9, 21, 18, 22, 'd')
    # satchel with herbs
    g.rect(4, 18, 9, 23, 'w'); g.rect(5, 19, 8, 22, 'D'); g.px(5, 17, 'b'); g.px(7, 16, 'b'); g.px(8, 17, 'b')
    g.rect(6, 13, 8, 17, 'G'); g.rect(6, 17, 8, 18, 's')
    # staff with a hanging lantern
    g.rect(22, 2, 23, 30, 'w'); g.rect(23, 2, 26, 2, 'w'); g.rect(26, 3, 26, 4, 'i'); g.rect(25, 5, 27, 8, 'i'); g.rect(26, 6, 26, 7, 'l')
    g.rect(19, 14, 21, 17, 'G'); g.rect(20, 17, 22, 18, 's')
    # head and straw hat
    face(g, 10, 7, 8, 6); g.rect(10, 7, 10, 10, 'H'); g.rect(17, 7, 17, 9, 'H')
    g.rect(5, 6, 22, 6, 'Y'); g.rect(6, 7, 21, 7, 'y'); g.rows(10, 2, [(1, 6), (0, 7), (0, 7), (0, 7)], 'Y'); g.rect(10, 5, 17, 5, 'g')
    return g

def mender4():  # pilgrim: brown hooded cloak, scallop-shell badge, brass censer trailing smoke
    pal = {**SKIN, 'C': '#6a4a36', 'c': '#52382a', 'R': '#8a7a5a', 'W': '#e8e0d0', 'Y': '#c8a040', 'y': '#a88430', 'm': '#b8b4c8',
           'M': '#9894aa', 'h': '#3a3440', 'k': '#2a2430', 'e': E, 'n': '#2a1e18'}
    g = G(pal)
    g.rows(8, 12, [(1, 10), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13), (-2, 13), (-3, 14), (-3, 14), (-3, 14), (-3, 14), (-3, 14)], 'C')
    g.rect(12, 14, 15, 28, 'R'); g.rect(9, 20, 18, 20, 'c')
    g.text(9, 15, ['WWW', 'W W', 'WWW', ' W '])
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    # censer on a chain, swinging out front, with smoke
    g.rows(19, 14, [(0, 2), (0, 3), (1, 3)], 'C'); g.rect(20, 17, 22, 18, 's')
    g.line(22, 18, 24, 22, 'h'); g.ell(25, 24, 2.4, 2.2, 'Y'); g.rect(23, 23, 27, 23, 'y'); g.px(25, 21, 'Y')
    g.px(26, 20, 'm'); g.px(27, 19, 'M'); g.px(27, 17, 'm'); g.px(28, 16, 'M'); g.px(27, 14, 'm')
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], 'C'); g.rect(6, 19, 8, 20, 's')
    # hood
    g.ell(13.5, 7.5, 6.5, 6.5, 'C'); g.rect(8, 8, 19, 13, 'C'); g.text(13, 0, ['cc', ' cc'])
    g.rect(10, 7, 17, 12, 'n'); g.rect(11, 8, 16, 12, 's'); g.rect(11, 8, 16, 8, 'S'); g.px(12, 10, 'e'); g.px(15, 10, 'e')
    return g

ALL = {'vanguard': [vanguard1, vanguard2, vanguard3, vanguard4],
       'arcanist': [arcanist1, arcanist2, arcanist3, arcanist4],
       'mender': [mender1, mender2, mender3, mender4]}

if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    for cls, fns in ALL.items():
        items = []
        for f in fns:
            g = f(); items.append((f.__name__, g.strings(), g.pal))
        sheet(items, f'{out}/{cls}.png', scale=6, cols=4, bg=(16, 22, 31))
