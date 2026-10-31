# Saltbound's enemies, one sprite each, drawn facing right (they're mirrored in fights).
from common import *

DROWN = {'s': '#8fb0a0', 'S': '#6a8a7c'}  # drowned skin: grey-green

def deckhand():  # drowned deckhand: grey-green skin, tattered striped shirt, rusty hook
    pal = {**DROWN, 'W': '#c8c4b4', 'w': '#5a6a8a', 'T': '#3a4a5a', 'k': '#24202a', 'L': '#3a4a5a', 'i': '#8a6a4a', 'K': '#4a7a3a', 'o': '#0e1a1a', 'g': '#c8e070'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'W')
    for y in range(14, 24, 2): g.rect(8, y, 19, y, 'w')
    g.rect(14, 17, 16, 19, 's'); g.rect(9, 22, 13, 23, 'T')
    g.rect(6, 13, 8, 20, 's'); g.rect(19, 14, 21, 18, 's'); g.rect(21, 17, 22, 18, 'i'); g.text(22, 14, ['ii', '  i', '  i', ' i '])
    face(g, 10, 5, 8, 7, eyes=False); g.px(12, 8, 'g'); g.px(15, 8, 'g'); g.rect(12, 10, 15, 10, 'o'); g.px(13, 11, 'S')
    g.rect(10, 4, 17, 4, 'K'); g.px(9, 5, 'K'); g.px(18, 6, 'K'); g.rect(9, 6, 9, 9, 'K')
    return g

def crab():  # crabfolk brute: big red shell, one huge claw raised
    pal = {'R': '#b84a3a', 'r': '#8a3428', 'O': '#e08a5a', 'e': E, 'w': '#f0e0c8', 'k': '#5a2418'}
    g = G(pal)
    g.ell(14, 20, 9, 6.5, 'R'); g.ell(14, 18.5, 7, 4, 'O'); g.ell(14, 22, 8, 3, 'r')
    for x in (7, 10, 17, 20): g.line(x, 24, x - 2 if x < 14 else x + 2, 29, 'r')
    g.rect(11, 12, 11, 15, 'k'); g.rect(16, 12, 16, 15, 'k'); g.rect(10, 11, 12, 12, 'w'); g.rect(15, 11, 17, 12, 'w'); g.px(11, 11, 'e'); g.px(16, 11, 'e')
    g.line(21, 17, 24, 12, 'R', 2); g.ell(25, 8, 4, 3.5, 'R'); g.ell(24, 10, 2, 1.2, 'r'); g.rect(26, 5, 29, 7, 'O'); g.px(28, 9, 'r')
    g.line(6, 18, 3, 15, 'R', 2); g.ell(3, 13, 2.4, 2, 'R')
    return g

def jelly():  # jellyfloat: translucent bell with trailing tentacles
    pal = {'P': '#b088d8', 'p': '#8a68b8', 'q': '#e0c8f8', 'e': E, 't': '#9a7ac8'}
    g = G(pal)
    g.ell(14, 12, 8, 6.5, 'P'); g.rect(6, 12, 22, 15, 'P'); g.ell(12, 9, 3, 2, 'q'); g.rect(6, 15, 22, 16, 'p')
    g.px(11, 13, 'e'); g.px(16, 13, 'e')
    for i, x in enumerate((8, 11, 14, 17, 20)):
        for y in range(17, 27 - i % 2 * 2): g.px(x + (1 if (y // 2 + i) % 2 else 0), y, 't')
    return g

def eel():  # reef eel: long green body curling up, gaping jaw
    pal = {'G': '#4a8a6a', 'g': '#356a50', 'Y': '#d8c870', 'e': E, 'w': '#f0f0e0', 'r': '#a83a3a'}
    g = G(pal)
    g.ell(10, 25, 7, 3.5, 'G'); g.ell(8, 26, 5, 1.6, 'Y')
    g.line(15, 24, 19, 16, 'G', 3); g.line(19, 16, 18, 9, 'G', 3)
    g.ell(20, 8, 4.5, 3.5, 'G'); g.rect(22, 8, 26, 10, 'r'); g.text(22, 7, ['w w w']); g.text(22, 11, ['w w']); g.px(20, 6, 'e'); g.px(20, 5, 'Y')
    g.text(15, 4, ['g g', ' g ']); g.px(4, 23, 'g'); g.px(2, 24, 'g')
    return g

def barnacle_priest():  # barnacle priest: crusted robe, mitre of shell, dripping censer-staff
    pal = {**DROWN, 'B': '#5a6a7a', 'b': '#44525e', 'c': '#d8d0c0', 'Y': '#a89040', 'w': '#6a5a40', 'g': '#c8e070', 'e': E, 'k': '#24202a'}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'B')
    for x, y in ((9, 16), (12, 19), (16, 22), (8, 24), (18, 17), (14, 26), (11, 25)): g.px(x, y, 'c'); g.px(x + 1, y, 'c')
    g.rect(13, 14, 14, 28, 'b')
    g.rect(21, 4, 22, 30, 'w'); g.ell(21.5, 4, 2.2, 2, 'Y'); g.px(21, 8, 'g')
    g.rect(19, 15, 21, 18, 'B'); g.rect(20, 18, 22, 19, 's')
    face(g, 10, 7, 8, 6, eyes=False); g.px(12, 9, 'g'); g.px(15, 9, 'g'); g.rect(12, 11, 15, 11, 'S')
    g.tri([(9, 7.5), (19, 7.5), (14, 0.5)], 'c'); g.rect(13, 2, 14, 6, 'Y')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    return g

def siren():  # siren: long dark hair, pale skin, scaled tail coiled, mouth open in song
    pal = {'s': '#c8d8e0', 'S': '#98aab8', 'H': '#2a3a5a', 'h': '#1e2a44', 'T': '#3a8a8a', 't': '#2a6a6a', 'e': E, 'm': '#7a3a5a', 'n': '#8fd8f0'}
    g = G(pal)
    g.ell(13, 25, 8, 4, 'T'); g.ell(13, 26, 6, 2, 't'); g.text(20, 21, ['TT', 'TTT', ' TT'])
    g.rect(10, 13, 16, 22, 's'); g.rect(10, 18, 16, 22, 'T')
    g.rect(16, 14, 19, 16, 's'); g.rect(19, 12, 20, 14, 's')
    face(g, 10, 6, 7, 6, eyes=False); g.px(12, 8, 'e'); g.px(15, 8, 'e'); g.rect(13, 10, 14, 11, 'm')
    g.rect(9, 3, 17, 5, 'H'); g.rect(8, 4, 9, 18, 'H'); g.rect(7, 8, 8, 20, 'h'); g.rect(17, 5, 18, 9, 'H')
    g.px(22, 8, 'n'); g.px(24, 6, 'n'); g.px(23, 10, 'n')
    return g

def bell_warden():  # the Bell-Warden: hulking drowned bellringer carrying a great green bronze bell
    pal = {**DROWN, 'B': '#4a8a6a', 'b': '#2e6a50', 'Y': '#9ac080', 'R': '#4a3a5a', 'r': '#36283e', 'k': '#24202a', 'g': '#c8e070', 'o': '#0e1a1a', 'c': '#d8d0c0'}
    g = G(pal)
    g.rect(9, 24, 12, 28, 'r'); g.rect(16, 24, 19, 28, 'r'); g.rect(8, 29, 12, 30, 'k'); g.rect(16, 29, 20, 30, 'k')
    g.rows(6, 11, [(2, 13), (1, 14), (0, 15), (0, 15), (0, 15), (0, 15), (0, 15), (0, 15), (0, 15), (0, 15), (1, 14), (1, 14), (2, 13)], 'R')
    g.rect(8, 22, 20, 23, 'r')
    g.rect(4, 13, 7, 21, 's')
    face(g, 10, 4, 8, 6, eyes=False); g.px(12, 6, 'g'); g.px(15, 6, 'g'); g.rect(11, 8, 16, 8, 'o'); g.rect(9, 2, 18, 3, 'R')
    # the bell, held out
    g.rect(20, 12, 23, 15, 's'); g.rect(24, 9, 25, 12, 'k')
    g.rows(19, 13, [(4, 7), (3, 8), (2, 9), (2, 9), (1, 10), (1, 10), (0, 11), (0, 11), (-1, 12)], 'B')
    g.rect(18, 22, 31, 22, 'b'); g.px(24, 23, 'Y'); g.px(25, 23, 'Y'); g.px(22, 16, 'Y'); g.px(23, 15, 'Y'); g.px(26, 18, 'c')
    return g

def cutthroat():  # cutthroat: eyepatch, striped bandana, dagger held low
    pal = {**SKIN2, 'R': '#2a2a3a', 'W': '#c8c4b4', 'w': '#a83030', 'V': '#5a3a2a', 'k': '#2a2028', 'L': '#4a3a30', 'e': E, 'i': '#dfe6ee', 'h': '#5a3a24', 'u': '#3a2418'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'W'); g.rows(8, 13, [(1, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'V'); g.rows(16, 13, [(0, 2), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'V')
    g.rect(9, 21, 18, 22, 'w')
    g.rect(20, 15, 22, 18, 'W'); g.rect(21, 18, 23, 19, 's'); g.rect(23, 19, 23, 20, 'h'); g.line(24, 20, 26, 23, 'i', 1); g.px(23, 21, 'i')
    g.rect(6, 13, 8, 19, 'W'); g.rect(6, 19, 8, 20, 's')
    face(g, 10, 5, 8, 7, eyes=False); g.px(15, 7, 'e'); g.rect(11, 6, 13, 8, 'R'); g.line(10, 5, 17, 9, 'R'); g.rect(12, 10, 15, 10, 'u')
    g.rect(10, 3, 17, 5, 'w'); g.rect(10, 4, 17, 4, 'W'); g.text(7, 4, ['ww', ' w'])
    return g

def deckhound():  # deckhound: scruffy grey dog with a spiked collar
    pal = {'G': '#7a7470', 'g': '#5a5450', 'R': '#a83030', 'i': '#c8c4b4', 'e': E, 'n': '#24202a', 'w': '#f0f0e0'}
    g = G(pal)
    g.ell(13, 20, 8, 4.5, 'G'); g.ell(12, 22, 6, 2, 'g')
    for x in (7, 10, 16, 19): g.rect(x, 23, x + 1, 29, 'G' if x in (7, 16) else 'g')
    g.line(5, 18, 2, 14, 'G', 2)
    g.ell(22, 14, 4.5, 4, 'G'); g.rect(24, 15, 28, 17, 'G'); g.px(28, 15, 'n'); g.px(23, 13, 'e'); g.text(25, 18, ['w w'])
    g.text(19, 9, ['G', 'GG']); g.rect(18, 16, 21, 17, 'R'); g.px(19, 15, 'i'); g.px(21, 15, 'i')
    return g

def brine_golem():  # brine golem: hulking body of wet rock and salt crust, kelp hanging off it
    pal = {'R': '#5a6a72', 'r': '#44525a', 'c': '#e8ecf0', 'K': '#4a7a3a', 'g': '#8fe0f0', 'k': '#2a2e34'}
    g = G(pal)
    g.rect(8, 23, 12, 29, 'r'); g.rect(16, 23, 20, 29, 'r'); g.rect(7, 29, 12, 30, 'k'); g.rect(16, 29, 21, 30, 'k')
    g.ell(14, 16, 9, 8, 'R'); g.ell(16, 18, 6, 5, 'r')
    g.ell(3, 18, 3, 6, 'R'); g.ell(25, 18, 3.5, 6, 'R'); g.rect(1, 23, 5, 26, 'r'); g.rect(23, 23, 28, 26, 'r')
    g.ell(14, 7, 5, 4, 'R'); g.px(12, 7, 'g'); g.px(16, 7, 'g')
    for x, y in ((8, 12), (10, 18), (18, 11), (20, 15), (13, 21), (24, 14), (3, 15)): g.px(x, y, 'c'); g.px(x + 1, y, 'c')
    g.rect(11, 9, 11, 14, 'K'); g.rect(19, 10, 19, 16, 'K'); g.rect(6, 17, 6, 21, 'K')
    return g

def powder_monkey():  # powder monkey: small sailor clutching a lit bomb
    pal = {**SKIN, 'B': '#3a5a8a', 'W': '#d8d0c0', 'k': '#2a2430', 'L': '#4a4048', 'e': E, 'b': '#24202a', 'f': '#ffb040', 'F': '#ffe080', 'H': '#6a3a22'}
    g = G(pal)
    g.rect(11, 25, 13, 28, 'L'); g.rect(15, 25, 17, 28, 'L'); g.rect(10, 29, 13, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rect(10, 17, 18, 24, 'W'); for_ = [g.rect(10, y, 18, y, 'B') for y in (18, 20, 22)]
    face(g, 10, 10, 8, 6); g.rect(10, 9, 17, 10, 'H'); g.rect(9, 10, 9, 12, 'H')
    g.rect(18, 18, 20, 20, 's'); g.ell(22, 19, 3, 3, 'b'); g.px(22, 15, 'H'); g.px(23, 14, 'f'); g.px(24, 13, 'F')
    return g

def tide_cultist():  # tide cultist: deep-blue hooded robe with a wave sigil, dagger of shell
    pal = {**SKIN, 'B': '#22385e', 'b': '#1a2a48', 'n': '#0e1424', 'c': '#8fd8f0', 'k': '#2a2430', 'w': '#e8dcc8', 'e': E, 'g': '#8fd8f0'}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'B')
    g.text(11, 16, ['c  c ', ' cc c', 'c  cc']); g.rect(13, 20, 14, 28, 'b')
    g.rect(19, 15, 21, 18, 'B'); g.rect(20, 18, 22, 19, 's'); g.line(22, 18, 25, 15, 'w')
    g.ell(13.5, 8, 6.5, 6.5, 'B'); g.rect(8, 9, 19, 13, 'B'); g.rect(10, 8, 17, 12, 'n'); g.px(12, 10, 'g'); g.px(15, 10, 'g')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    return g

def corsair_captain():  # corsair captain: plumed hat, long crimson coat, pistol levelled
    pal = {**SKIN, 'T': '#2a2430', 'P': '#e0e0d0', 'R': '#8a2424', 'r': '#6a1c1c', 'Y': '#c8a040', 'W': '#e0dacb', 'k': '#2a2430', 'L': '#2a2430', 'e': E,
           'H': '#2a1e18', 'i': '#7a8494'}
    g = G(pal)
    legs(g, 'L')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13)], 'R')
    g.rect(12, 13, 15, 22, 'W'); g.rect(8, 13, 8, 24, 'Y'); g.rect(19, 13, 19, 24, 'Y'); g.rect(9, 19, 18, 19, 'H')
    g.rect(19, 15, 23, 17, 'R'); g.rect(23, 15, 24, 17, 's'); g.rect(25, 15, 29, 16, 'i'); g.rect(24, 17, 25, 18, 'H')
    face(g, 10, 6, 8, 6); g.rect(11, 10, 16, 10, 'H'); g.rect(9, 7, 9, 12, 'H')
    g.rect(6, 5, 21, 5, 'T'); g.rows(9, 1, [(1, 8), (0, 9), (0, 9), (0, 9)], 'T'); g.text(5, 0, ['  PP ', ' PPP ', 'PP   ', 'P    ']); g.rect(9, 4, 18, 4, 'Y')
    return g

def gallows_admiral():  # the Gallows Admiral: skeletal admiral in a rotted bicorne, noose around the neck, cutlass
    pal = {'c': '#d8d0c0', 'C': '#b8b0a0', 'N': '#22385e', 'n': '#1a2a48', 'Y': '#c8a040', 'T': '#2a2430', 'e': '#ff6040', 'k': '#2a2430', 'L': '#22385e',
           'h': '#8a6a4a', 'w': '#dfe6ee', 'o': '#14101a'}
    g = G(pal)
    legs(g, 'L')
    g.rows(7, 13, [(1, 12), (0, 13), (0, 13), (0, 13), (0, 13), (0, 13), (-1, 14), (-1, 14), (-1, 14), (-2, 15), (-2, 15)], 'N')
    g.rect(13, 13, 14, 23, 'n'); g.rect(6, 13, 9, 14, 'Y'); g.rect(18, 13, 21, 14, 'Y'); g.px(11, 16, 'Y'); g.px(16, 16, 'Y'); g.px(11, 19, 'Y'); g.px(16, 19, 'Y')
    g.rect(20, 15, 22, 18, 'N'); g.rect(21, 18, 23, 19, 'c'); g.rect(22, 17, 24, 17, 'Y'); g.line(23, 16, 28, 9, 'w', 2)
    g.ell(13.5, 8, 4.5, 4.5, 'c'); g.rect(10, 9, 17, 11, 'c'); g.rect(11, 7, 12, 8, 'o'); g.rect(15, 7, 16, 8, 'o'); g.px(12, 8, 'e'); g.px(15, 8, 'e')
    g.rect(11, 11, 16, 11, 'C'); g.px(12, 11, 'o'); g.px(14, 11, 'o')
    g.rect(10, 12, 17, 12, 'h'); g.line(17, 12, 19, 4, 'h')
    g.rows(5, 1, [(4, 13), (2, 15), (0, 17), (2, 15)], 'T'); g.rect(8, 3, 19, 3, 'Y')
    return g

def crag_ram():  # crag ram: shaggy grey-brown ram with great curled horns
    pal = {'W': '#a8988a', 'w': '#86766a', 'H': '#d8c8a0', 'h': '#b0a078', 'e': E, 'k': '#3a3028'}
    g = G(pal)
    g.ell(12, 18, 9, 5.5, 'W'); g.ell(12, 20, 7, 3, 'w')
    for x in (5, 8, 15, 18): g.rect(x, 22, x + 1, 29, 'w'); g.px(x, 29, 'k'); g.px(x + 1, 29, 'k')
    g.ell(22, 13, 4, 3.5, 'W'); g.rect(24, 13, 27, 16, 'W'); g.px(27, 14, 'k'); g.px(23, 12, 'e')
    g.ell(20, 10, 3.6, 3.6, 'H'); g.ell(20, 10, 1.8, 1.8, 'h'); g.rect(17, 11, 18, 14, 'H')
    return g

def cliff_hermit():  # cliff hermit: wild-bearded old man in furs with a crook
    pal = {**SKIN, 'F': '#8a7058', 'f': '#6a5440', 'B': '#e0dacb', 'w': '#6a4a2e', 'k': '#2a2430', 'L': '#5a4a3a', 'e': E}
    g = G(pal)
    legs(g, 'L')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11)], 'F')
    for x, y in ((9, 15), (13, 18), (17, 14), (11, 21), (16, 22)): g.px(x, y, 'f')
    g.rect(22, 4, 23, 30, 'w'); g.text(21, 1, [' www', 'w  w', 'w   ']); g.rect(19, 15, 21, 18, 'F'); g.rect(20, 18, 22, 19, 's')
    face(g, 10, 5, 8, 6); g.rect(9, 3, 18, 5, 'B'); g.rows(9, 10, [(0, 9), (0, 9), (1, 8), (2, 7), (3, 6), (4, 5)], 'B'); g.rect(12, 10, 15, 10, 's')
    return g

def harpy():  # harpy: grey-winged bird-woman with talons
    pal = {'s': '#c8a888', 'S': '#a08060', 'G': '#6a6a7a', 'g': '#4e4e5c', 'H': '#3a2a4a', 'Y': '#d8b040', 'e': E}
    g = G(pal)
    g.tri([(10, 12), (1, 4), (3, 20)], 'G'); g.tri([(17, 12), (29, 3), (26, 20)], 'G'); g.tri([(10, 14), (4, 9), (5, 19)], 'g'); g.tri([(17, 14), (26, 7), (24, 18)], 'g')
    g.rect(11, 12, 16, 21, 's'); g.rect(11, 18, 16, 22, 'G')
    g.rect(11, 23, 12, 26, 'Y'); g.rect(15, 23, 16, 26, 'Y'); g.text(10, 27, ['Y  Y Y', ' YY  Y'])
    face(g, 11, 5, 6, 6, eyes=False); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.rect(10, 3, 17, 5, 'H'); g.rect(9, 4, 10, 11, 'H'); g.px(17, 9, 'Y')
    return g

def storm_wisp():  # storm wisp: a crackling ball of blue light with a trailing tail
    pal = {'z': '#e8f6ff', 'Z': '#7fd0ff', 'b': '#3a7ad8', 'e': '#14203a'}
    g = G(pal)
    g.ell(14, 12, 6, 6, 'b'); g.ell(14, 12, 4.5, 4.5, 'Z'); g.ell(13, 11, 2.4, 2.4, 'z'); g.px(12, 12, 'e'); g.px(16, 12, 'e')
    g.text(10, 18, [' bZb ', '  bZ ', '   b ', '  Zb ', ' b   '])
    g.px(5, 8, 'z'); g.px(23, 6, 'z'); g.px(22, 16, 'Z'); g.px(6, 15, 'Z')
    return g

def lightning_totem():  # lightning totem: carved post with a brass rod crackling at the top
    pal = {'W': '#7a5a3a', 'w': '#5a4028', 'R': '#a83a3a', 'Y': '#c8a040', 'z': '#e8f6ff', 'Z': '#7fd0ff', 'e': '#ffe080'}
    g = G(pal)
    g.rect(10, 9, 18, 29, 'W'); g.rect(9, 29, 19, 30, 'w')
    g.rect(10, 12, 18, 12, 'w'); g.rect(10, 19, 18, 19, 'w'); g.rect(10, 25, 18, 25, 'w')
    g.px(12, 15, 'e'); g.px(16, 15, 'e'); g.rect(12, 17, 16, 17, 'R'); g.px(12, 22, 'R'); g.px(16, 22, 'R')
    g.rect(13, 2, 15, 8, 'Y'); g.text(9, 0, ['z  Z  z', ' Z z Z ', '  zZz  '])
    return g

def thunder_wyvern():  # thunder wyvern: slate-blue wyvern with yellow-lit wings
    pal = {'B': '#4a5a7a', 'b': '#36425c', 'Y': '#d8c040', 'y': '#a89030', 'e': '#ffe080', 'w': '#f0f0e0', 'k': '#22283a'}
    g = G(pal)
    g.tri([(12, 14), (2, 2), (6, 18)], 'b'); g.tri([(12, 14), (4, 4), (7, 16)], 'y')
    g.ell(13, 19, 7, 5, 'B'); g.ell(12, 21, 5, 2.5, 'Y')
    g.line(6, 21, 1, 26, 'B', 2); g.rect(10, 23, 11, 29, 'b'); g.rect(15, 23, 16, 29, 'b')
    g.line(18, 16, 21, 9, 'B', 3); g.ell(23, 8, 4, 3, 'B'); g.rect(25, 8, 29, 10, 'B'); g.px(23, 7, 'e'); g.text(26, 11, ['w w']); g.text(21, 3, ['k k', ' k '])
    return g

def lamp_keeper():  # the Lamp Keeper: tall figure in an oilskin with a lighthouse lamp for a head
    pal = {'O': '#c8a040', 'o': '#a08030', 'D': '#2a2a38', 'k': '#2a2430', 'L': '#2a2a38', 'Y': '#c8a040', 'l': '#fff2b0', 'L2': '#ffd870', 'i': '#3a3440', 'b': '#e8f6ff'}
    pal = {k: v for k, v in pal.items() if len(k) == 1}; pal['m'] = '#ffd870'
    g = G(pal)
    legs(g, 'L')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13)], 'O')
    g.rect(12, 13, 15, 24, 'D'); g.rect(8, 19, 19, 19, 'o')
    g.rect(19, 14, 21, 18, 'O'); g.rect(20, 18, 22, 19, 'D')
    g.rect(10, 11, 17, 12, 'i'); g.rect(9, 3, 18, 10, 'i'); g.rect(10, 4, 17, 9, 'm'); g.rect(12, 5, 15, 8, 'l'); g.rect(9, 1, 18, 2, 'i'); g.rect(12, 0, 15, 0, 'i')
    g.line(18, 6, 29, 2, 'm'); g.line(18, 7, 29, 9, 'm'); g.px(25, 5, 'b')
    return g

def tide_guard():  # tide guard: drowned soldier in barnacled plate with a trident
    pal = {**DROWN, 'A': '#6a8a8a', 'a': '#4e6a6a', 'c': '#d8d0c0', 'g': '#c8e070', 'k': '#24202a', 'L': '#4e6a6a', 'Y': '#9ac080', 'w': '#8a9aa0', 'o': '#0e1a1a'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'A')
    for x, y in ((9, 15), (16, 18), (11, 21), (18, 14)): g.px(x, y, 'c')
    g.rect(9, 20, 18, 21, 'a')
    g.rect(22, 3, 22, 30, 'w'); g.text(20, 0, ['w w w', 'w w w', 'wwwww']); g.rect(19, 15, 21, 18, 'A'); g.rect(20, 18, 23, 19, 's')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8), (2, 7)], 'A'); g.rect(10, 7, 17, 8, 'o'); g.px(12, 7, 'g'); g.px(15, 7, 'g'); g.rect(13, 1, 14, 3, 'Y')
    return g

def drowned_crown():  # the Drowned Crown: a towering drowned king in sea-green robes and a coral crown, trident of pearl
    pal = {**DROWN, 'G': '#2a6a5a', 'g': '#1e5044', 'C': '#e07060', 'Y': '#c8a040', 'y': '#a88430', 'e': '#8fe8ff', 'o': '#0e1a1a', 'w': '#dff4ff', 'K': '#4a7a3a', 'k': '#24202a'}
    g = G(pal)
    g.rows(8, 12, [(1, 10), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13), (-3, 14), (-3, 14), (-3, 14), (-4, 15), (-4, 15), (-4, 15), (-4, 15), (-4, 15), (-4, 15)], 'G')
    g.rect(12, 12, 15, 29, 'g'); g.rect(7, 12, 20, 13, 'Y'); g.rect(13, 16, 14, 17, 'C')
    g.rect(23, 2, 23, 30, 'Y'); g.text(21, 0, ['w w w', 'w w w', 'wwwww']); g.rect(19, 14, 22, 17, 'G'); g.rect(21, 17, 24, 18, 's')
    face(g, 10, 5, 8, 7, eyes=False); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.rect(12, 10, 15, 10, 'o')
    g.rows(9, 9, [(0, 9), (1, 8), (2, 7), (3, 6)], 'K'); g.rect(12, 9, 15, 9, 's')
    g.text(9, 0, ['C  C  C  C', 'CC CC CC C', 'YYYYYYYYYY', 'Y y  y  yY'])
    return g

ALL = [deckhand, crab, jelly, eel, barnacle_priest, siren, bell_warden, cutthroat, deckhound, brine_golem, powder_monkey,
       tide_cultist, corsair_captain, gallows_admiral, crag_ram, cliff_hermit, harpy, storm_wisp, lightning_totem,
       thunder_wyvern, lamp_keeper, tide_guard, drowned_crown]

if __name__ == '__main__':
    import sys
    items = [(f.__name__, f().strings(), f().pal) for f in ALL]
    sheet(items, (sys.argv[1] if len(sys.argv) > 1 else '.') + '/foes.png', scale=4, cols=8, bg=(16, 22, 31))


# ---------------------------------------------------------------- the Warden's summons (hero side, drawn facing right)
def sapling():
    pal = {'G': '#5a9a40', 'g': '#3e7a2e', 'L': '#8ac860', 'w': '#6a4a2e', 'k': '#4a3020', 'e': E}
    g = G(pal)
    g.rect(13, 18, 15, 28, 'w'); g.rect(10, 28, 18, 29, 'k')
    g.ell(14, 13, 6, 5.5, 'G'); g.ell(12.5, 11.5, 2.5, 2, 'L'); g.ell(16, 16, 3, 2, 'g')
    g.px(12, 14, 'e'); g.px(16, 14, 'e')
    g.line(15, 22, 19, 19, 'w'); g.ell(20, 18, 1.6, 1.4, 'G')
    return g

def bear():
    pal = {'B': '#6a4a30', 'b': '#4e3422', 'M': '#a07a54', 'e': E, 'n': '#1a1210', 'w': '#f0f0e0'}
    g = G(pal)
    g.ell(13, 19, 9.5, 6.5, 'B'); g.ell(12, 22, 7, 3, 'b')
    for x in (6, 9, 16, 19): g.rect(x, 24, x + 2, 29, 'b' if x in (9, 19) else 'B')
    g.ell(23, 14, 5, 4.5, 'B'); g.ell(26, 16, 2.6, 2, 'M'); g.px(28, 15, 'n'); g.px(23, 12, 'e')
    g.ell(20.5, 10, 1.6, 1.6, 'B'); g.ell(25, 10, 1.6, 1.6, 'B'); g.text(25, 18, ['w w'])
    return g

def wasps():
    pal = {'Y': '#e0b830', 'k': '#2a2018', 'w': '#dfe8f0', 'e': E}
    g = G(pal)
    for cx, cy in ((9, 10), (19, 8), (14, 17), (22, 19), (7, 22)):
        g.ell(cx, cy, 2.6, 1.8, 'Y'); g.px(cx, cy, 'k'); g.px(cx - 1, cy, 'k'); g.px(cx + 2, cy - 1, 'e')
        g.px(cx - 1, cy - 2, 'w'); g.px(cx + 1, cy - 2, 'w')
    return g

def treant():
    pal = {'W': '#6a4a2e', 'w': '#4e3422', 'G': '#4a8a3c', 'g': '#3a6a2e', 'L': '#6aa84a', 'e': '#ffd870', 'k': '#2a1e14'}
    g = G(pal)
    g.rect(10, 12, 19, 27, 'W'); g.rect(12, 14, 17, 26, 'w'); g.rect(8, 27, 12, 30, 'W'); g.rect(17, 27, 21, 30, 'W')
    g.line(10, 15, 4, 10, 'W', 2); g.line(19, 15, 26, 9, 'W', 2)
    g.ell(14.5, 7, 8.5, 6, 'G'); g.ell(12, 5, 3, 2, 'L'); g.ell(18, 9, 3, 2, 'g'); g.ell(4, 8, 3, 2.5, 'G'); g.ell(26, 7, 3, 2.5, 'G')
    g.px(12, 17, 'e'); g.px(16, 17, 'e'); g.rect(12, 21, 16, 21, 'k')
    return g

SUMMONS = [sapling, bear, wasps, treant]
