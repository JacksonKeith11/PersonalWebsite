# Saltbound's heroes: four options each for the owner to pick from. Heroes are ordinary fantasy
# adventurers, not sea-themed (only the enemies belong to the archipelago), so they carry over to
# future maps like the classes do.
from common import *

# ------------------------------------------------------------------ Vanguard: tank
def vanguard1():  # shieldbearer: great helm with a visor slit, blue tabard, tall heater shield, spear (the owner's pick)
    pal = {'A': '#a8b0bc', 'a': '#7a8494', 'T': '#3a5aa8', 't': '#2a4280', 'Y': '#d0a840', 'n': '#1e1a26', 'L': '#5a6070', 'k': '#2a2430',
           'S': '#c8c4b4', 's': '#3a5aa8', 'h': '#5a3a24', 'M': '#8a929e', 'w': '#dfe6ee'}
    g = G(pal)
    legs(g, 'a')
    torso(g, 'A')
    g.rows(10, 15, [(0, 7)] * 8 + [(-1, 8)], 'T'); g.rect(9, 20, 18, 20, 'h'); g.rect(13, 20, 14, 20, 'Y')
    g.rect(6, 13, 9, 15, 'a'); g.rect(18, 13, 21, 15, 'a')
    # spear upright, as the spear-warden holds it
    g.rect(20, 15, 22, 18, 'A'); g.rect(22, 2, 22, 30, 'h'); g.rect(21, 18, 23, 19, 'a'); g.text(21, 0, [' w ', 'www', 'www', ' w '])
    # heater shield
    g.rows(1, 12, [(0, 8), (0, 8), (0, 8), (0, 8), (0, 8), (0, 8), (0, 8), (1, 7), (1, 7), (2, 6), (3, 5), (4, 4)], 'S')
    g.rows(1, 13, [(1, 7)] * 6 + [(2, 6), (2, 6), (3, 5), (4, 4)], 's'); g.rect(5, 13, 5, 21, 'Y'); g.rect(2, 16, 8, 16, 'Y')
    # great helm
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(10, 7, 18, 7, 'n'); g.rect(13, 3, 14, 11, 'a'); g.rect(13, 7, 14, 7, 'n'); g.px(11, 9, 'n'); g.px(16, 9, 'n')
    return g

def vanguard2():  # spear-warden: nasal helm, braided beard, mail, round painted shield, spear upright
    pal = {**SKIN, 'A': '#9aa2ae', 'a': '#6e7684', 'M': '#7a8290', 'm': '#5e6672', 'B': '#c88a3a', 'R': '#8a2a2a', 'r': '#e0c060',
           'w': '#dfe6ee', 'h': '#5a3a24', 'k': '#2a2430', 'L': '#4a3a30', 'e': E, 'H': '#b8783a'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'M')
    for y in range(14, 24, 2):
        for x in range(8 + (y // 2) % 2, 20, 2): g.px(x, y, 'm')
    g.rect(9, 20, 18, 21, 'h')
    g.rect(20, 15, 22, 18, 'M'); g.rect(21, 18, 23, 19, 's'); g.rect(22, 2, 22, 30, 'h'); g.text(21, 0, [' w ', 'www', 'www', ' w '])
    g.ell(6, 19, 5.5, 5.5, 'R'); g.ell(6, 19, 4.5, 4.5, 'r'); g.rows(2, 15, [(4, 4), (3, 5), (2, 6), (1, 7), (2, 6), (3, 5), (4, 4)], 'R'); g.ell(6, 19, 1.4, 1.4, 'A')
    face(g, 10, 6, 8, 6)
    g.rows(10, 10, [(0, 7), (1, 6), (2, 5), (3, 4), (3, 4)], 'H'); g.rect(12, 10, 15, 10, 's'); g.px(13, 13, 'r'); g.px(14, 13, 'r')
    g.rows(9, 2, [(2, 7), (1, 8), (0, 9), (0, 9)], 'A'); g.rect(9, 5, 18, 5, 'a'); g.rect(13, 6, 14, 9, 'a')
    return g

def vanguard3():  # paladin: open helm, white tabard with a gold sun, kite shield, sword held forward
    pal = {**SKIN, 'A': '#b8c0cc', 'a': '#8a94a4', 'W': '#e8e2d4', 'w': '#c8c0b0', 'Y': '#d0a840', 'y': '#a88430', 'H': '#c8a060',
           'b': '#dfe6ee', 'h': '#5a3a24', 'k': '#2a2430', 'L': '#8a94a4', 'e': E, 'R': '#a83030'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'A')
    g.rows(10, 14, [(0, 7)] * 9 + [(-1, 8)], 'W'); g.ell(13.5, 17, 2, 2, 'Y'); g.px(13, 14, 'Y'); g.px(14, 20, 'Y'); g.px(10, 17, 'Y'); g.px(17, 17, 'Y')
    g.rect(9, 21, 18, 21, 'h')
    g.rect(20, 15, 22, 18, 'A'); g.rect(21, 18, 23, 19, 's'); g.rect(22, 17, 24, 17, 'Y'); g.line(23, 16, 28, 10, 'b', 2)
    g.rows(1, 13, [(1, 7), (0, 8), (0, 8), (0, 8), (0, 8), (0, 8), (1, 7), (1, 7), (2, 6), (3, 5), (4, 4)], 'W')
    g.rows(1, 14, [(2, 6), (1, 7), (1, 7), (1, 7), (1, 7), (2, 6), (2, 6), (3, 5), (4, 4)], 'R'); g.rect(5, 14, 5, 22, 'Y'); g.rect(2, 17, 8, 17, 'Y')
    face(g, 10, 6, 8, 6); g.rect(12, 10, 15, 10, 'S')
    g.rows(9, 2, [(1, 8), (0, 9), (0, 9), (0, 9)], 'A'); g.rect(9, 6, 9, 11, 'A'); g.rect(18, 6, 18, 11, 'A'); g.rect(9, 5, 18, 5, 'a')
    g.rect(10, 3, 17, 4, 'H'); g.px(10, 6, 'H'); g.px(17, 6, 'H')
    return g

def vanguard4():  # sentinel: dark plate, horned helm, big pavise shield, warhammer
    pal = {'A': '#5e6674', 'a': '#444b58', 'D': '#7a8494', 'R': '#7a2a2a', 'Y': '#a88a40', 'n': '#14101a', 'g': '#ffb040', 'k': '#2a2430',
           'L': '#444b58', 'h': '#5a3a24', 'B': '#d8d0c0', 'P': '#3a3a48', 'p': '#2a2a36'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'A')
    g.rect(12, 14, 15, 22, 'a'); g.rect(9, 20, 18, 20, 'R'); g.rect(6, 12, 9, 15, 'D'); g.rect(18, 12, 21, 15, 'D')
    g.rect(20, 15, 22, 18, 'A'); g.rect(21, 18, 23, 19, 'a'); g.rect(22, 5, 23, 19, 'h'); g.rect(19, 2, 26, 6, 'D'); g.rect(19, 6, 26, 6, 'a')
    g.rect(1, 12, 9, 28, 'P'); g.rect(2, 13, 8, 27, 'p'); g.rect(1, 12, 9, 12, 'Y'); g.rect(1, 28, 9, 28, 'Y'); g.rect(4, 17, 6, 22, 'R'); g.rect(3, 19, 7, 19, 'R')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(10, 7, 17, 8, 'n'); g.px(12, 7, 'g'); g.px(15, 7, 'g'); g.rect(13, 9, 14, 11, 'a')
    g.text(6, 0, ['B         B', 'BB       BB', ' BB     BB '])
    return g

# ------------------------------------------------------------------ Arcanist: caster
def arcanist1():  # pyromancer: crimson robes, hood down, red hair, staff crowned with a flame
    pal = {**SKIN, 'R': '#a83a30', 'r': '#7a2a24', 'H': '#c85a30', 'Y': '#d0a840', 'w': '#6a4a2e', 'f': '#ff9a2a', 'F': '#ffe14d', 'k': '#2a2230', 'e': E, 'D': '#5a2420'}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'R')
    g.rect(13, 14, 14, 28, 'r'); g.rect(8, 20, 19, 20, 'Y'); g.rect(8, 13, 19, 14, 'D')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rect(21, 7, 22, 30, 'w'); g.text(19, 0, ['  f  ', ' fFf ', 'fFFFf', ' fFf ', ' www ']); g.px(21, 5, 'w')
    g.rows(19, 15, [(0, 2), (0, 3), (1, 3)], 'r'); g.rect(20, 17, 22, 19, 's')
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], 'r'); g.rect(6, 19, 8, 20, 's')
    face(g, 10, 6, 8, 6)
    g.rect(9, 3, 18, 5, 'H'); g.rect(9, 5, 9, 12, 'H'); g.rect(18, 5, 18, 11, 'H'); g.px(8, 12, 'H')
    g.rect(12, 10, 15, 10, 'S')
    return g

def arcanist2():  # sorceress: braided dark hair, blue robe with silver trim, a spellbook floating open
    pal = {**SKIN, 'B': '#3a5aa8', 'b': '#2a4280', 'W': '#c8ccd8', 'H': '#2a1e2a', 'P': '#e8dcc0', 'p': '#a88a5a', 'c': '#9ff0ff', 'k': '#2a2230', 'e': E}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'B')
    g.rect(13, 14, 14, 28, 'W'); g.rect(6, 28, 21, 28, 'W'); g.rect(9, 19, 18, 19, 'b')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rows(19, 14, [(0, 2), (0, 3), (1, 4)], 'B'); g.rect(22, 16, 24, 17, 's')
    g.rect(21, 9, 27, 13, 'P'); g.rect(24, 9, 24, 13, 'p'); g.rect(21, 13, 27, 13, 'p'); g.px(22, 10, 'p'); g.px(26, 11, 'p'); g.px(23, 6, 'c'); g.px(26, 5, 'c'); g.px(25, 7, 'c')
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], 'B'); g.rect(6, 19, 8, 20, 's')
    face(g, 10, 6, 8, 6); g.rect(12, 10, 15, 10, 'S')
    g.rect(9, 3, 18, 5, 'H'); g.rect(9, 5, 9, 9, 'H'); g.rect(18, 5, 18, 8, 'H'); g.rect(18, 9, 19, 18, 'H'); g.px(19, 12, 'W'); g.px(19, 16, 'W')
    return g

def arcanist3():  # scholar: deep hood, round spectacles, long grey robe, wand and a scroll
    pal = {**SKIN, 'G': '#5a5a6a', 'g': '#44444f', 'n': '#1e1a26', 'q': '#cfe6f0', 'u': '#6a4a2e', 'P': '#e8dcc0', 'p': '#b8a888', 'c': '#d0a8ff', 'w': '#3a2a1a', 'k': '#2a2230', 'e': E}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'G')
    g.rect(13, 14, 14, 28, 'g'); g.rect(8, 20, 19, 20, 'u')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rows(19, 14, [(0, 2), (0, 3), (1, 3)], 'G'); g.rect(20, 17, 22, 18, 's'); g.line(22, 16, 26, 11, 'w'); g.px(27, 10, 'c'); g.px(28, 9, 'c'); g.px(26, 8, 'c')
    g.rows(5, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], 'G'); g.rect(3, 19, 8, 22, 'P'); g.rect(3, 19, 3, 22, 'p'); g.rect(8, 19, 8, 22, 'p'); g.rect(4, 20, 7, 20, 'p')
    g.ell(13.5, 8, 6.5, 6.5, 'G'); g.rect(8, 9, 19, 13, 'G'); g.text(14, 0, [' gg', 'ggG'])
    g.rect(10, 7, 17, 12, 'n'); g.rect(11, 8, 16, 12, 's'); g.rect(11, 8, 16, 8, 'S')
    g.rect(11, 9, 13, 10, 'q'); g.rect(14, 9, 16, 10, 'q'); g.px(12, 10, 'e'); g.px(15, 10, 'e')
    return g

def arcanist4():  # elementalist: shaved head, sash, a flame in one hand and frost in the other
    pal = {**SKIN2, 'O': '#d8c8a8', 'o': '#b8a888', 'S2': '#2a6a6a', 'f': '#ff9a2a', 'F': '#ffe14d', 'i': '#7fe3ff', 'I': '#e8f8ff', 'k': '#2a2230', 'L': '#6a5a4a', 'e': E, 'u': '#4a3020'}
    pal = {k: v for k, v in pal.items() if len(k) == 1}; pal['T'] = '#2a6a6a'
    g = G(pal)
    legs(g, 'L')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13)], 'O')
    g.line(9, 13, 18, 22, 'T', 2); g.rect(8, 19, 19, 19, 'o')
    g.rows(19, 13, [(0, 2), (0, 3), (1, 4), (2, 4)], 'O'); g.rect(22, 10, 24, 12, 's'); g.text(21, 4, ['  f  ', ' fFf ', 'fFFFf', ' fFf '])
    g.rows(5, 14, [(1, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'O'); g.rect(4, 19, 6, 20, 's'); g.text(1, 14, [' i ', 'iIi', ' i ', 'i i'])
    g.ell(13.5, 7.5, 4.5, 4.5, 's'); g.rect(10, 7, 17, 12, 's'); g.px(12, 8, 'e'); g.px(15, 8, 'e'); g.rect(12, 10, 15, 10, 'S')
    g.px(13, 3, 'T'); g.px(14, 3, 'T')
    return g

# ------------------------------------------------------------------ Mender: healer
def mender1():  # cleric: white robe with gold trim, hood back, staff topped with a gold sunburst
    pal = {**SKIN, 'W': '#e8e2d4', 'w': '#c8c0b0', 'Y': '#d0a840', 'y': '#ffe080', 'H': '#7a4a2a', 'h': '#6a4a2e', 'k': '#2a2430', 'e': E}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'W')
    g.rect(13, 14, 14, 28, 'Y'); g.rect(6, 28, 21, 28, 'Y'); g.rect(8, 20, 19, 20, 'w'); g.rect(8, 12, 19, 13, 'w')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rect(21, 6, 22, 30, 'h'); g.text(18, 0, ['  Y Y  ', 'Y yYy Y', ' YyyyY ', 'YYy yYY', ' YyyyY ', 'Y yYy Y'])
    g.rows(19, 15, [(0, 2), (0, 3), (1, 3)], 'W'); g.rect(20, 17, 22, 19, 's')
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], 'W'); g.rect(6, 19, 8, 20, 's')
    face(g, 10, 6, 8, 6); g.rect(12, 10, 15, 10, 'S')
    g.rect(10, 3, 17, 5, 'H'); g.rect(9, 5, 9, 9, 'H'); g.rect(18, 5, 18, 9, 'H')
    return g

def mender2():  # druid: green hood, leaf-wound staff, herb pouch, bare feet in sandals
    pal = {**SKIN, 'G': '#4a7a44', 'g': '#3a6034', 'D': '#8a6a4a', 'd': '#6a503a', 'w': '#6a4a2e', 'l': '#7ab858', 'L': '#5a9a40', 'k': '#5a4028', 'e': E, 'n': '#1e2a1a', 'p': '#e07090'}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'D')
    g.rows(8, 12, [(0, 11), (0, 11), (0, 11), (1, 10), (2, 9), (3, 8), (4, 7)], 'G')
    g.rect(13, 19, 14, 28, 'd'); g.rect(8, 21, 19, 21, 'w')
    g.rect(4, 20, 8, 24, 'w'); g.rect(5, 21, 7, 23, 'd'); g.px(5, 19, 'l'); g.px(7, 18, 'L')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rect(22, 3, 23, 30, 'w'); g.text(20, 0, [' l L ', 'lLlLl', ' LlL ', '  p  ']); g.px(21, 8, 'l'); g.px(24, 11, 'L'); g.px(21, 15, 'l')
    g.rows(19, 15, [(0, 2), (0, 3), (1, 3)], 'G'); g.rect(20, 17, 22, 19, 's')
    g.ell(13.5, 8, 6.5, 6.5, 'G'); g.rect(8, 9, 19, 12, 'G'); g.text(13, 0, ['gg', ' gg'])
    g.rect(10, 7, 17, 12, 'n'); g.rect(11, 8, 16, 12, 's'); g.rect(11, 8, 16, 8, 'S'); g.px(12, 10, 'e'); g.px(15, 10, 'e')
    return g

def mender3():  # field medic: short hair, rolled sleeves, leather apron with bandages, satchel at the hip
    pal = {**SKIN, 'H': '#5a3a24', 'W': '#d8d0c0', 'B': '#8a5a36', 'b': '#6a4428', 'r': '#c84a3a', 'w': '#f0ece0', 'k': '#2a2430', 'L': '#4a4048', 'e': E}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'W')
    g.rows(10, 15, [(0, 7)] * 8 + [(-1, 8)], 'B'); g.rect(10, 15, 17, 15, 'b'); g.rect(11, 18, 16, 18, 'w'); g.rect(11, 20, 16, 20, 'w')
    g.line(8, 13, 19, 22, 'b'); g.rect(17, 21, 21, 25, 'b'); g.rect(18, 22, 20, 24, 'B'); g.px(19, 22, 'r'); g.px(19, 23, 'r'); g.px(18, 23, 'r'); g.px(20, 23, 'r')
    g.rect(6, 13, 8, 17, 'W'); g.rect(6, 17, 8, 20, 's')
    g.rect(19, 13, 21, 16, 'W'); g.rect(21, 15, 23, 17, 's'); g.rect(23, 13, 26, 15, 'w'); g.px(24, 14, 'r')
    face(g, 10, 5, 8, 7); g.rect(12, 10, 15, 10, 'S')
    g.rect(10, 3, 17, 5, 'H'); g.rect(9, 4, 9, 7, 'H'); g.rect(18, 4, 18, 6, 'H')
    return g

def mender4():  # lantern priestess: white veil, grey habit, lantern held high
    pal = {**SKIN, 'W': '#e8e2d4', 'w': '#c8c0b0', 'G': '#6a6878', 'g': '#52505e', 'Y': '#c8a040', 'y': '#ffd870', 'F': '#fff2b0', 'i': '#3a3440', 'k': '#2a2430', 'e': E}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'G')
    g.rect(10, 13, 17, 15, 'W'); g.rect(13, 16, 14, 22, 'Y'); g.rect(11, 18, 16, 18, 'Y'); g.rect(8, 21, 19, 21, 'g')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rows(19, 13, [(0, 2), (0, 3), (1, 4), (2, 4)], 'G'); g.rect(22, 10, 24, 12, 's'); g.rect(23, 4, 23, 9, 'i')
    g.rect(21, 4, 25, 4, 'i'); g.rect(21, 5, 25, 9, 'Y'); g.rect(22, 6, 24, 8, 'y'); g.px(23, 7, 'F'); g.rect(22, 10, 24, 10, 'i'); g.px(23, 3, 'i')
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], 'G'); g.rect(6, 19, 8, 20, 's')
    g.ell(13.5, 8, 6, 6.5, 'W'); g.rect(8, 9, 19, 13, 'W'); g.rect(8, 11, 8, 14, 'w'); g.rect(19, 11, 19, 14, 'w')
    g.rect(10, 7, 17, 12, 's'); g.rect(10, 7, 17, 7, 'w'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(12, 11, 15, 11, 'S')
    return g

ALL = {'vanguard': [vanguard1, vanguard2, vanguard3, vanguard4],
       'arcanist': [arcanist1, arcanist2, arcanist3, arcanist4],
       'mender': [mender1, mender2, mender3, mender4]}

if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    for cls, fns in ALL.items():
        items = [(f.__name__, f().strings(), f().pal) for f in fns]
        sheet(items, f'{out}/{cls}.png', scale=6, cols=4, bg=(16, 22, 31))
