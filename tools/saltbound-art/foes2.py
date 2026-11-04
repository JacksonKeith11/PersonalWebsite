# The other regions' enemies (content/biomes.py), one sprite each, drawn facing right like foes.py.
from common import *

_line = G.line


def _iline(s, x0, y0, x1, y1, c, w=1):  # lines between fractional points (the kit wants whole ones)
    _line(s, round(x0), round(y0), round(x1), round(y1), c, w)


G.line = _iline

ASH = {'s': '#8a8078', 'S': '#6a625c'}      # ash-grey skin
MUMMY = {'s': '#c8b890', 'S': '#a8986e'}    # linen
STONE = {'s': '#9a968c', 'S': '#7a766e'}    # weathered stone
HALO = '#e8d070'


# ================================================================ Cinderreach
def cinder_imp():  # cinder imp: a small coal-black imp with ember cracks, a flame on its head
    pal = {'K': '#3a2e2e', 'k': '#2a2222', 'F': '#e8782a', 'Y': '#ffd23f', 'e': '#ffd23f', 'w': '#5a4a44'}
    g = G(pal)
    g.ell(14, 21, 5.5, 5, 'K'); g.ell(14, 23, 3.5, 2.5, 'k')
    g.ell(15, 13, 5, 4.5, 'K')
    g.tri([(11, 10), (9, 4), (13, 9)], 'K'); g.tri([(18, 10), (21, 4), (17, 9)], 'K')
    g.px(13, 13, 'e'); g.px(17, 13, 'e'); g.rect(14, 16, 16, 16, 'F')
    g.ell(15, 7, 2, 3, 'F'); g.ell(15, 7.5, 1, 1.5, 'Y')
    g.line(9, 21, 6, 17, 'K'); g.line(19, 20, 23, 16, 'K'); g.ell(24, 15, 1.6, 1.6, 'F')
    g.rect(11, 26, 12, 29, 'k'); g.rect(16, 26, 17, 29, 'k')
    g.line(4, 24, 8, 23, 'K'); g.px(3, 25, 'F')
    for x, y in ((12, 20), (16, 22), (14, 18), (11, 23)): g.px(x, y, 'F')
    return g

def magma_crawler():  # magma crawler: a squat beetle with a cracked black shell glowing orange in the seams
    pal = {'K': '#3e3434', 'k': '#2a2222', 'F': '#e8782a', 'Y': '#ffd23f', 'e': '#ffd23f', 'L': '#5a4a44'}
    g = G(pal)
    g.ell(14, 19, 10, 6.5, 'K'); g.ell(14, 22, 9, 3, 'k')
    g.line(6, 15, 22, 15, 'F'); g.line(14, 13, 14, 24, 'F'); g.line(8, 19, 12, 22, 'F'); g.line(19, 18, 21, 22, 'F')
    g.ell(25, 19, 4, 3.5, 'L'); g.px(26, 18, 'e'); g.px(28, 18, 'e'); g.text(27, 21, ['YY'])
    for x in (6, 10, 16, 20): g.line(x, 24, x - 2 if x < 14 else x + 2, 29, 'k')
    g.line(27, 16, 30, 13, 'L'); g.line(27, 22, 30, 24, 'L')
    return g

def ash_wraith():  # ash wraith: a ragged grey shroud of smoke with a hollow face and ember eyes
    pal = {'G': '#7a726e', 'g': '#5a5450', 'D': '#3a3434', 'e': '#ff7a1a', 'F': '#c86a2a'}
    g = G(pal)
    g.rows(8, 8, [(3, 9), (2, 10), (1, 11), (1, 11), (0, 12), (0, 12), (0, 12), (-1, 13), (-1, 13), (-1, 13), (-1, 14),
                  (-2, 14), (-2, 15), (-2, 15), (-3, 15), (-3, 16), (-3, 16)], 'G')
    g.ell(14, 8, 6, 6, 'G'); g.ell(14, 9, 3.5, 3.5, 'D'); g.px(12, 9, 'e'); g.px(16, 9, 'e')
    for x, y in ((6, 25), (10, 26), (15, 25), (19, 26), (23, 25)): g.rect(x, y, x + 1, y + 3, 'g')
    g.line(21, 14, 27, 10, 'G', 2); g.px(28, 9, 'F'); g.px(27, 8, 'F')
    g.text(22, 2, ['g', ' g', 'g'])
    return g

def obsidian_golem():  # obsidian golem: a hulk of black volcanic glass, lava veins and a glowing core
    pal = {'O': '#2e2a36', 'o': '#22202a', 'G': '#4a4658', 'F': '#e8782a', 'Y': '#ffd23f', 'e': '#ffd23f', 'k': '#1e1a24'}
    g = G(pal)
    g.rect(8, 23, 12, 29, 'o'); g.rect(16, 23, 20, 29, 'o'); g.rect(7, 29, 12, 30, 'k'); g.rect(16, 29, 21, 30, 'k')
    g.tri([(5, 12), (23, 12), (14, 25)], 'O'); g.rect(6, 12, 22, 20, 'O')
    g.tri([(7, 12), (12, 12), (9, 17)], 'G'); g.tri([(17, 13), (21, 13), (19, 18)], 'G')
    g.ell(14, 17, 2.5, 2.5, 'F'); g.px(14, 17, 'Y')
    g.line(9, 21, 13, 18, 'F'); g.line(19, 14, 16, 17, 'F')
    g.ell(3, 17, 3, 6, 'O'); g.ell(25, 17, 3.5, 6, 'O'); g.rect(1, 22, 5, 25, 'G'); g.rect(23, 22, 28, 25, 'G')
    g.tri([(10, 11), (18, 11), (14, 3)], 'O'); g.px(12, 8, 'e'); g.px(16, 8, 'e')
    return g

def ember_cultist():  # ember cultist: a robed fanatic in red and black, a brazier-staff burning
    pal = {**ASH, 'R': '#8a2e2a', 'r': '#6a2220', 'K': '#2e2628', 'F': '#e8782a', 'Y': '#ffd23f', 'w': '#5a3a24', 'e': '#ff7a1a', 'k': '#24202a'}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12),
                   (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'R')
    g.rect(13, 14, 14, 28, 'K'); g.rect(7, 20, 21, 20, 'r')
    g.rect(21, 6, 22, 30, 'w'); g.rect(19, 4, 24, 6, 'K'); g.ell(21.5, 2, 2.5, 2.5, 'F'); g.px(21, 2, 'Y')
    g.rect(19, 15, 21, 18, 'R'); g.rect(20, 18, 22, 19, 's')
    g.rows(9, 3, [(3, 6), (1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'K')
    g.rect(11, 7, 16, 11, 's'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(11, 7, 16, 7, 'S')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    return g

def lava_hound():  # lava hound: a lean black hound with molten cracks and a flaming mane
    pal = {'K': '#3a3030', 'k': '#2a2222', 'F': '#e8782a', 'Y': '#ffd23f', 'e': '#ffd23f', 'w': '#f0e0c8'}
    g = G(pal)
    g.ell(13, 20, 8, 4, 'K'); g.ell(12, 22, 6, 2, 'k')
    for x in (7, 10, 16, 19): g.rect(x, 23, x + 1, 29, 'K' if x in (7, 16) else 'k')
    g.line(5, 18, 1, 13, 'K', 2); g.px(1, 12, 'F'); g.px(0, 11, 'Y')
    g.ell(22, 14, 4.5, 4, 'K'); g.rect(24, 15, 28, 17, 'K'); g.px(23, 13, 'e'); g.text(25, 18, ['w w'])
    g.text(15, 9, [' F F', 'FYFYF', ' FFF']); g.tri([(20, 10), (22, 6), (23, 11)], 'K')
    g.line(9, 19, 13, 21, 'F'); g.line(16, 18, 18, 21, 'F')
    return g

def forge_knight():  # forge-knight: blackened plate glowing red at the joints, a molten-edged greatsword
    pal = {'A': '#4a4652', 'a': '#36323e', 'F': '#e8782a', 'Y': '#ffd23f', 'I': '#a8b0bc', 'k': '#24202a', 'L': '#36323e', 'e': '#ffd23f'}
    g = G(pal)
    legs(g, 'L')
    torso(g, 'A'); g.rect(13, 14, 14, 23, 'a'); g.rect(8, 21, 19, 21, 'F'); g.px(11, 17, 'F'); g.px(16, 17, 'F')
    g.rect(6, 13, 8, 19, 'A'); g.rect(19, 14, 21, 18, 'A'); g.rect(20, 18, 22, 19, 'a')
    g.line(22, 18, 29, 3, 'I', 2); g.line(23, 17, 29, 5, 'F'); g.rect(20, 18, 24, 19, 'k')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(10, 7, 17, 7, 'k'); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.rect(13, 0, 14, 2, 'F')
    return g

def caldera_wyrm():  # the Caldera Wyrm: a huge black-scaled wyrm, molten belly, magma dripping from its jaws
    pal = {'K': '#3a3236', 'k': '#2a2428', 'F': '#e8782a', 'Y': '#ffd23f', 'e': '#ffd23f', 'w': '#f0e0c8', 'R': '#8a3a2a'}
    g = G(pal)
    g.ell(12, 22, 10, 6, 'K'); g.ell(12, 24, 8, 3, 'F'); g.line(5, 24, 19, 24, 'Y')
    g.line(3, 20, 0, 28, 'K', 3)
    g.tri([(10, 16), (2, 4), (13, 12)], 'R'); g.tri([(14, 15), (9, 3), (17, 12)], 'k')
    g.line(18, 18, 22, 10, 'K', 4); g.ell(24, 8, 5, 4, 'K'); g.rect(26, 9, 31, 12, 'K')
    g.text(26, 13, ['w w w']); g.px(24, 6, 'e'); g.tri([(22, 5), (21, 0), (24, 4)], 'k'); g.tri([(26, 5), (27, 0), (28, 5)], 'k')
    g.px(30, 14, 'F'); g.px(30, 16, 'Y'); g.px(29, 15, 'F')
    for x in (7, 11, 15): g.rect(x, 27, x + 2, 30, 'k')
    return g

def slag_tyrant():  # the Slag Tyrant: a smith-king of cooling slag, crown of bent iron, a molten hammer
    pal = {'K': '#4a3e3a', 'k': '#342a28', 'F': '#e8782a', 'Y': '#ffd23f', 'e': '#ffd23f', 'I': '#7a7a86', 'i': '#5a5a66', 'w': '#5a3a24', 'L': '#342a28'}
    g = G(pal)
    g.rect(8, 23, 12, 29, 'L'); g.rect(16, 23, 20, 29, 'L'); g.rect(7, 29, 12, 30, 'i'); g.rect(16, 29, 21, 30, 'i')
    g.rows(5, 11, [(2, 15), (1, 16), (0, 17), (0, 17), (0, 17), (0, 17), (0, 17), (0, 17), (0, 17), (0, 17), (1, 16), (1, 16), (2, 15)], 'K')
    g.rect(10, 13, 17, 20, 'k'); g.ell(13.5, 16, 2.5, 2.5, 'F'); g.px(13, 16, 'Y'); g.rect(5, 21, 22, 22, 'I')
    g.line(7, 13, 10, 20, 'F'); g.line(20, 13, 18, 19, 'F')
    g.rect(2, 13, 5, 21, 'K'); g.rect(22, 12, 25, 18, 'K')
    g.rect(25, 3, 26, 22, 'w'); g.rect(21, 1, 30, 6, 'I'); g.rect(21, 6, 30, 7, 'F'); g.px(23, 2, 'Y')
    face(g, 9, 4, 10, 7, eyes=False); g.rect(9, 4, 18, 10, 'K'); g.px(11, 7, 'e'); g.px(16, 7, 'e'); g.rect(11, 9, 16, 9, 'F')
    g.text(8, 0, ['I  I  I  I', 'IIIIIIIIII', 'i i  i i ']); g.rect(8, 3, 19, 3, 'I')
    return g


# ================================================================ the Shifting Sands
def dune_scorpion():  # dune scorpion: a sand-yellow scorpion, tail arched over with a purple sting
    pal = {'Y': '#c8a050', 'y': '#a07e3a', 'P': '#8a4a9a', 'e': E, 'k': '#6a5228'}
    g = G(pal)
    g.ell(13, 22, 8, 4, 'Y'); g.ell(13, 24, 6, 2, 'y')
    for x in (7, 10, 14, 18): g.line(x, 25, x - 2 if x < 13 else x + 2, 29, 'k')
    g.line(6, 21, 3, 16, 'Y', 2); g.line(3, 16, 5, 9, 'Y', 2); g.line(5, 9, 10, 5, 'Y', 2); g.tri([(10, 4), (14, 6), (11, 8)], 'P')
    g.line(20, 20, 25, 17, 'Y', 2); g.ell(27, 16, 3, 2.2, 'Y'); g.rect(28, 13, 30, 14, 'y'); g.rect(28, 18, 30, 19, 'y')
    g.px(19, 19, 'e'); g.px(21, 19, 'e')
    return g

def dune_raider():  # dune raider: wrapped head, scarf over the face, curved scimitar
    pal = {**SKIN2, 'W': '#d8c8a0', 'w': '#a89870', 'B': '#3a5aa8', 'R': '#a83030', 'k': '#4a3828', 'L': '#a89870', 'e': E, 'i': '#dfe6ee', 'h': '#5a3a24'}
    g = G(pal)
    legs(g, 'L'); torso(g, 'W'); g.rect(8, 21, 19, 22, 'R'); g.rect(9, 13, 18, 14, 'w')
    g.rect(20, 15, 22, 18, 'W'); g.rect(21, 18, 23, 19, 's')
    g.line(23, 19, 25, 14, 'i'); g.line(25, 14, 28, 12, 'i'); g.line(24, 18, 27, 13, 'i'); g.rect(22, 19, 24, 20, 'h')
    g.rect(6, 13, 8, 19, 'W'); g.rect(6, 19, 8, 20, 's')
    face(g, 10, 5, 8, 7, eyes=False); g.rect(10, 4, 17, 6, 'W'); g.rect(10, 9, 17, 11, 'B'); g.px(12, 7, 'e'); g.px(15, 7, 'e')
    g.rect(9, 3, 18, 4, 'W'); g.text(5, 5, ['WWWW', ' WW']); g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    return g

def wrapped_dead():  # wrapped dead: a mummy in yellowed linen strips, one glowing eye, arms reaching
    pal = {**MUMMY, 'L': '#a8986e', 'k': '#4a3e2e', 'e': '#7fe3ff', 'D': '#5a4e3e'}
    g = G(pal)
    legs(g, 'L', 'k'); torso(g, 's')
    for y in range(14, 24, 3): g.line(8, y, 19, y + 1, 'S')
    g.rect(19, 15, 26, 17, 's'); g.rect(19, 18, 25, 18, 'S'); g.rect(6, 15, 8, 21, 's')
    face(g, 10, 5, 8, 7, eyes=False); g.line(10, 6, 17, 8, 'S'); g.line(10, 9, 17, 10, 'S'); g.px(12, 8, 'D'); g.px(15, 8, 'e')
    g.text(26, 18, ['S', ' S'])
    return g

def glass_mage():  # glass mage: a slim robed caster in sun-white, a lens floating above an open hand
    pal = {**SKIN2, 'W': '#d8d0b8', 'w': '#b8ae94', 'G': '#c8a040', 'c': '#8ad0d8', 'C': '#d0f4f8', 'k': '#4a3828', 'e': E}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12),
                   (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'W')
    g.rect(13, 14, 14, 28, 'w'); g.rect(8, 19, 19, 19, 'G')
    g.rect(19, 15, 22, 17, 'W'); g.rect(22, 15, 24, 16, 's')
    g.ell(25, 10, 3, 3, 'c'); g.ell(24.5, 9.5, 1.2, 1.2, 'C'); g.line(25, 13, 25, 14, 'G')
    face(g, 10, 6, 8, 6); g.rows(9, 1, [(4, 5), (2, 7), (1, 8), (0, 9), (0, 9)], 'W'); g.rect(9, 5, 18, 5, 'G')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    return g

def carrion_vulture():  # carrion vulture: a hunched bald bird, ragged dark wings half open
    pal = {'B': '#4a3a34', 'b': '#362a26', 'P': '#c88a7a', 'Y': '#c8a050', 'e': E, 'w': '#d8d0c0'}
    g = G(pal)
    g.ell(13, 19, 7, 7, 'B'); g.tri([(8, 14), (1, 22), (9, 24)], 'b'); g.tri([(18, 14), (26, 23), (17, 24)], 'b')
    g.ell(13, 13, 4, 2.5, 'w')
    g.line(15, 12, 19, 7, 'P', 2); g.ell(21, 6, 3, 2.5, 'P'); g.tri([(23, 5), (27, 7), (23, 8)], 'Y'); g.px(21, 5, 'e')
    g.rect(11, 26, 11, 29, 'Y'); g.rect(15, 26, 15, 29, 'Y'); g.text(10, 29, ['Y Y']); g.text(14, 29, ['Y Y'])
    return g

def scarab_swarm():  # scarab swarm: a cluster of blue-green beetles with gold edges
    pal = {'B': '#2a5a6a', 'b': '#1e4450', 'G': '#c8a040', 'e': E}
    g = G(pal)
    for cx, cy, r in ((9, 21, 3.5), (17, 23, 3.8), (22, 17, 3.2), (12, 14, 3.2), (24, 25, 2.6), (6, 27, 2.4)):
        g.ell(cx, cy, r, r * 0.75, 'B'); g.line(cx, cy - r * 0.7, cx, cy + r * 0.7, 'b'); g.px(int(cx + r), int(cy), 'G')
        g.px(int(cx + r) + 1, int(cy) - 1, 'e')
    return g

def riddling_sphinx():  # riddling sphinx: a lioness with a pharaoh's striped headdress and wings folded
    pal = {**SKIN2, 'Y': '#c8a050', 'y': '#a07e3a', 'B': '#3a5aa8', 'G': '#c8a040', 'W': '#d8c8a0', 'e': E}
    g = G(pal)
    g.ell(12, 21, 9, 5, 'Y'); g.ell(11, 23, 7, 2.5, 'y')
    for x in (5, 9, 16, 19): g.rect(x, 24, x + 2, 29, 'Y' if x in (5, 16) else 'y')
    g.line(3, 20, 0, 14, 'Y', 2); g.px(0, 13, 'y')
    g.tri([(10, 16), (3, 8), (15, 15)], 'W'); g.tri([(12, 16), (8, 9), (16, 15)], 'G')
    g.rows(18, 6, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'B')
    for y in (7, 9, 11, 13): g.rect(18, y, 27, y, 'G')
    face(g, 20, 8, 6, 6, eyes=False); g.px(22, 10, 'e'); g.px(24, 10, 'e'); g.rect(22, 12, 24, 12, 'S')
    g.rect(21, 16, 25, 18, 'G')
    return g

def great_sandworm():  # the Great Sandworm: a ringed sand-coloured worm bursting up, a round mouth of teeth
    pal = {'Y': '#c8a070', 'y': '#a07e54', 'P': '#7a3a4a', 'w': '#f4ecd8', 'D': '#d8c49a'}
    g = G(pal)
    g.ell(16, 28, 14, 3.5, 'D'); g.text(0, 26, ['D D', ' D']); g.text(26, 26, ['D D', ' D'])
    g.line(14, 28, 17, 11, 'Y', 9)
    for y in (24, 20, 16): g.line(9, y, 21, y - 1, 'y')
    g.ell(19, 8, 8, 6.5, 'Y'); g.ell(21, 8, 5, 4.5, 'P')
    for a in range(10):
        import math
        x, y = 21 + 4 * math.cos(a * 0.628), 8 + 3.6 * math.sin(a * 0.628)
        g.px(int(round(x)), int(round(y)), 'w')
    return g

def sun_eaten_king():  # the Sun-Eaten King: a gaunt mummy-pharaoh, gold mask and a black sun-disc behind him
    pal = {**MUMMY, 'G': '#c8a040', 'g': '#a88430', 'B': '#3a5aa8', 'K': '#2a2430', 'e': '#ffd23f', 'D': '#5a4e3e', 'F': '#e8782a'}
    g = G(pal)
    g.ell(15, 9, 11, 9, 'K'); g.ell(15, 9, 8, 6.5, 'D'); g.px(5, 9, 'F'); g.px(25, 9, 'F'); g.px(15, 0, 'F')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13), (-3, 14), (-3, 14),
                   (-3, 14), (-4, 15), (-4, 15), (-4, 15), (-4, 15)], 's')
    for y in range(15, 29, 3): g.line(5, y, 22, y + 1, 'S')
    g.rect(7, 13, 20, 14, 'G'); g.rect(8, 15, 19, 15, 'B')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'B')
    for y in (4, 6, 8, 10): g.rect(9, y, 18, y, 'G')
    g.rect(11, 5, 16, 11, 'G'); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.rect(13, 9, 14, 10, 'g'); g.rect(13, 12, 14, 13, 'g')
    g.line(22, 14, 26, 6, 'G'); g.tri([(25, 4), (28, 6), (26, 8)], 'G'); g.rect(20, 14, 22, 17, 's')
    return g


# ================================================================ the Stillwood
def stone_treant():  # stone treant: a walking tree of grey petrified wood, lichen on its shoulders
    pal = {'R': '#8a8478', 'r': '#6a645c', 'L': '#8a9a5a', 'l': '#6a7a44', 'e': '#c8e070', 'k': '#4a463e'}
    g = G(pal)
    g.rect(9, 12, 19, 27, 'R'); g.rect(12, 14, 16, 26, 'r'); g.rect(7, 27, 12, 30, 'R'); g.rect(16, 27, 21, 30, 'R')
    g.line(10, 15, 3, 9, 'R', 2); g.line(3, 9, 1, 4, 'R'); g.line(19, 15, 26, 8, 'R', 2); g.line(26, 8, 29, 3, 'R')
    g.rows(7, 4, [(4, 10), (2, 12), (1, 13), (0, 14), (0, 14), (1, 13), (2, 12), (3, 11)], 'R')
    g.ell(9, 6, 3, 2, 'L'); g.ell(18, 7, 3, 2, 'l'); g.ell(5, 11, 2, 1.5, 'L'); g.ell(24, 10, 2, 1.5, 'L')
    g.px(12, 17, 'e'); g.px(16, 17, 'e'); g.rect(12, 21, 16, 21, 'k')
    return g

def basilisk():  # basilisk: a low green-grey lizard with a crest, eyes that glow pale gold
    pal = {'G': '#6a7a5a', 'g': '#4e5c42', 'C': '#a8a070', 'e': '#ffe14d', 'w': '#f0f0e0'}
    g = G(pal)
    g.ell(12, 22, 9, 4, 'G'); g.ell(12, 24, 7, 1.8, 'g')
    g.line(3, 22, 0, 18, 'G', 2)
    for x in (6, 10, 15, 18): g.rect(x, 24, x + 1, 28, 'g')
    g.ell(23, 19, 5, 3.5, 'G'); g.rect(26, 19, 30, 21, 'G'); g.px(24, 17, 'e'); g.px(25, 17, 'e'); g.text(26, 22, ['w w'])
    g.text(6, 16, ['C C C C C C C']); g.tri([(20, 16), (22, 11), (24, 16)], 'C')
    return g

def gargoyle():  # gargoyle: a crouching stone imp with bat wings and horns
    pal = {**STONE, 'G': '#8a867e', 'g': '#6a665e', 'e': '#ff4040', 'k': '#4a463e'}
    g = G(pal)
    g.tri([(10, 14), (1, 5), (4, 20)], 'g'); g.tri([(18, 14), (28, 4), (25, 20)], 'g')
    g.ell(14, 20, 6, 5.5, 'G'); g.rect(9, 24, 12, 28, 'G'); g.rect(16, 24, 19, 28, 'G'); g.rect(8, 28, 20, 29, 'k')
    g.ell(15, 12, 4.5, 4, 'G'); g.px(13, 12, 'e'); g.px(17, 12, 'e'); g.rect(14, 15, 16, 15, 'k')
    g.tri([(11, 10), (9, 5), (13, 9)], 'G'); g.tri([(19, 10), (21, 5), (17, 9)], 'G')
    g.line(20, 21, 23, 25, 'G')
    return g

def fossil_hound():  # fossil hound: a skeletal dog of yellowed bone, ribs showing, eyes like coals
    pal = {'B': '#d8d0b0', 'b': '#a8a080', 'D': '#4a4438', 'e': '#ff7a1a'}
    g = G(pal)
    g.ell(13, 20, 7, 3.5, 'D')
    for x in range(8, 19, 2): g.rect(x, 17, x, 23, 'B')
    g.line(6, 19, 20, 18, 'B'); g.line(6, 19, 1, 14, 'B'); g.text(0, 12, ['b', ' b'])
    for x in (7, 10, 16, 19): g.rect(x, 22, x, 29, 'B'); g.px(x + 1, 29, 'b')
    g.ell(22, 14, 4, 3.5, 'B'); g.rect(24, 15, 28, 17, 'B'); g.px(23, 13, 'e'); g.text(25, 17, ['D D'])
    g.tri([(20, 11), (21, 7), (23, 11)], 'b')
    return g

def amber_wisp():  # amber wisp: a floating drop of golden amber with a tiny trapped spark inside
    pal = {'A': '#c88a30', 'a': '#a06a22', 'Y': '#ffd23f', 'e': '#ffe14d', 'w': '#ffe9a0'}
    g = G(pal)
    g.ell(14, 15, 6, 6.5, 'A'); g.tri([(10, 11), (14, 2), (18, 11)], 'A'); g.ell(15, 18, 4, 3.5, 'a')
    g.ell(14, 15, 2, 2, 'Y'); g.px(14, 15, 'w'); g.px(12, 12, 'e'); g.px(17, 12, 'e')
    for x, y in ((8, 24), (13, 26), (19, 25), (22, 20), (6, 19)): g.px(x, y, 'Y')
    return g

def lichen_shaman():  # lichen shaman: a stooped figure overgrown with green-grey lichen, a stone-tipped staff
    pal = {**STONE, 'L': '#7a8a5a', 'l': '#5a6a44', 'w': '#6a5a40', 'e': '#c8e070', 'k': '#4a463e', 'G': '#a8b070'}
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12),
                   (-3, 13), (-3, 13), (-3, 13), (-3, 13), (-3, 13)], 'L')
    for x, y in ((8, 16), (14, 19), (10, 23), (17, 25), (12, 14)): g.ell(x, y, 1.5, 1, 'G')
    g.rect(21, 5, 22, 30, 'w'); g.ell(21.5, 4, 2.5, 2.5, 's')
    g.rect(19, 15, 21, 18, 'L'); g.rect(20, 18, 22, 19, 's')
    g.rows(9, 4, [(2, 7), (1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8), (1, 8)], 'l')
    g.rect(11, 8, 16, 12, 's'); g.px(12, 10, 'e'); g.px(15, 10, 'e')
    g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    return g

def sleeping_sentinel():  # sleeping sentinel: a stone knight-statue with a halberd, eyes closed
    pal = {**STONE, 'A': '#8a867e', 'a': '#6a665e', 'w': '#7a766e', 'k': '#4a463e', 'L': '#6a665e', 'o': '#3a3630', 'I': '#b8b4aa'}
    pal['z'] = pal['Z'] = '#d8d4f0'
    g = G(pal)
    legs(g, 'L', 'k'); torso(g, 'A'); g.rect(13, 14, 14, 23, 'a'); g.rect(8, 21, 19, 21, 'a')
    g.rect(22, 2, 23, 30, 'w'); g.tri([(20, 2), (26, 5), (23, 9)], 'I')
    g.rect(19, 14, 21, 18, 'A'); g.rect(20, 18, 23, 19, 'a'); g.rect(6, 13, 8, 20, 'A')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(11, 7, 12, 7, 'o'); g.rect(15, 7, 16, 7, 'o'); g.text(19, 0, ['z', ' z'])
    g.rect(6, 30, 21, 30, 'k')
    return g

def petrified_knight():  # petrified knight: armour gone to grey stone, cracks, moss, a broken lance
    pal = {**STONE, 'A': '#9a968c', 'a': '#7a766e', 'L': '#7a766e', 'k': '#4a463e', 'M': '#7a8a5a', 'e': '#c8e070', 'w': '#8a867e'}
    g = G(pal)
    legs(g, 'L', 'k'); torso(g, 'A'); g.rect(8, 21, 19, 22, 'a')
    g.line(9, 14, 13, 20, 'k'); g.line(17, 15, 15, 22, 'k'); g.ell(10, 15, 1.5, 1, 'M'); g.ell(17, 22, 1.5, 1, 'M')
    g.rect(2, 14, 7, 23, 'A'); g.rect(3, 15, 6, 22, 'a'); g.px(4, 18, 'M')
    g.line(20, 18, 30, 8, 'w', 2); g.rect(19, 15, 21, 18, 'A')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(10, 7, 17, 7, 'k'); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.ell(13.5, 2, 2.5, 1.2, 'M')
    return g

def elder_basilisk():  # the Elder Basilisk: a great coiled serpent-lizard of stone and moss, a crown of horns
    pal = {'G': '#6a7a5a', 'g': '#4e5c42', 'C': '#a8a070', 'e': '#ffe14d', 'w': '#f0f0e0', 'M': '#7a8a5a', 'R': '#8a8478'}
    g = G(pal)
    g.ell(13, 24, 12, 5, 'G'); g.ell(13, 26, 10, 2.5, 'g'); g.ell(10, 20, 7, 4, 'G')
    g.line(18, 22, 22, 12, 'G', 5); g.ell(24, 9, 6, 4.5, 'G'); g.rect(27, 10, 31, 13, 'G')
    g.px(24, 7, 'e'); g.px(26, 7, 'e'); g.text(27, 14, ['w w'])
    g.tri([(20, 6), (19, 0), (22, 5)], 'C'); g.tri([(24, 5), (24, 0), (26, 5)], 'C'); g.tri([(27, 6), (29, 1), (29, 6)], 'C')
    for x in range(3, 22, 3): g.px(x, 19 + (x % 2), 'R'); g.px(x + 1, 23, 'M')
    return g

def heartwood_gorgon():  # the Heartwood Gorgon: a tall gorgon of living wood, snake-hair, stone-grey skin, glowing eyes
    pal = {**STONE, 'G': '#4a6a3a', 'g': '#3a5a2e', 'W': '#6a4a2e', 'w': '#5a3a24', 'e': '#ffe14d', 'R': '#8a3a3a', 'L': '#8a9a5a'}
    g = G(pal)
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13), (-3, 14), (-3, 14),
                   (-3, 14), (-4, 15), (-4, 15), (-4, 15), (-4, 15), (-4, 15)], 'W')
    g.rect(12, 13, 15, 29, 'w'); g.rect(7, 13, 20, 14, 'L')
    g.rect(20, 14, 23, 18, 's'); g.rect(4, 14, 7, 18, 's')
    face(g, 10, 5, 8, 7, eyes=False); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.rect(12, 10, 15, 10, 'R')
    for i, x in enumerate((7, 10, 13, 16, 19)):
        g.line(x + 1, 5, x - 1 + (i % 2) * 3, 0, 'G'); g.px(x - 1 + (i % 2) * 3, 0, 'g')
    g.line(8, 4, 5, 8, 'G'); g.line(19, 4, 22, 8, 'G'); g.px(5, 9, 'g'); g.px(22, 9, 'g')
    return g


# ================================================================ the Verdant Deep
def shadow_panther():  # shadow panther: a sleek black panther, green eyes, low and ready to pounce
    pal = {'K': '#2e2a34', 'k': '#221e28', 'e': '#7fe36a', 'w': '#f0f0e0', 'P': '#4a4258'}
    g = G(pal)
    g.ell(13, 21, 9, 4, 'K'); g.ell(12, 23, 7, 2, 'k')
    for x in (6, 9, 17, 20): g.rect(x, 23, x + 1, 29, 'K' if x in (6, 17) else 'k')
    g.line(4, 20, 0, 13, 'K', 2); g.line(0, 13, 2, 10, 'K')
    g.ell(23, 17, 4.5, 4, 'K'); g.rect(25, 18, 29, 20, 'K'); g.px(24, 16, 'e'); g.text(26, 21, ['w w'])
    g.tri([(20, 14), (21, 10), (23, 14)], 'K'); g.tri([(24, 14), (26, 10), (27, 14)], 'K')
    g.line(8, 19, 18, 19, 'P')
    return g

def dart_frog():  # dart frog: a small bright frog, red with dark blue spots
    pal = {'R': '#c84a3a', 'r': '#9a3428', 'B': '#2a3a6a', 'e': E, 'w': '#f0e0c8'}
    g = G(pal)
    g.ell(14, 22, 7, 5, 'R'); g.ell(14, 24, 5, 2.5, 'r')
    g.ell(10, 17, 2.5, 2.5, 'R'); g.ell(18, 17, 2.5, 2.5, 'R'); g.px(10, 17, 'e'); g.px(18, 17, 'e')
    for x, y in ((11, 21), (16, 22), (13, 25), (18, 25), (9, 24)): g.px(x, y, 'B'); g.px(x + 1, y, 'B')
    g.line(7, 25, 3, 28, 'R'); g.line(21, 25, 25, 28, 'R'); g.rect(2, 28, 5, 29, 'r'); g.rect(23, 28, 26, 29, 'r')
    g.rect(12, 20, 16, 20, 'r')
    return g

def strangler_vine():  # strangler vine: a writhing knot of green vines with thorns and a flower-mouth
    pal = {'G': '#4a7a3c', 'g': '#36602e', 'R': '#a83a4a', 'Y': '#d8c040', 'w': '#f0e0c8', 'k': '#4a3020'}
    g = G(pal)
    g.ell(14, 28, 9, 2.5, 'k')
    g.line(10, 28, 8, 12, 'G', 3); g.line(16, 28, 19, 10, 'G', 3); g.line(13, 28, 13, 18, 'g', 2)
    g.line(8, 12, 3, 6, 'G', 2); g.line(19, 10, 25, 5, 'G', 2)
    g.ell(14, 10, 4, 3.5, 'R'); g.ell(14, 10, 1.6, 1.6, 'Y'); g.text(12, 13, ['w w'])
    for x, y in ((6, 18), (21, 17), (10, 23), (18, 22), (4, 8), (24, 7)): g.px(x, y, 'w')
    return g

def witch_doctor():  # witch doctor: a masked figure in a feathered cloak, a skull-topped rattle
    pal = {**SKIN2, 'M': '#c8a050', 'R': '#a83030', 'G': '#4a7a3c', 'B': '#3a5aa8', 'W': '#d8d0c0', 'w': '#5a3a24', 'k': '#2a2028', 'L': '#5a3a24', 'e': '#ffe14d'}
    g = G(pal)
    legs(g, 'L', 'k')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13), (-2, 13)], 'G')
    g.rect(10, 14, 17, 22, 's'); g.rect(10, 22, 17, 23, 'R')
    g.rect(21, 8, 22, 22, 'w'); g.ell(21.5, 7, 2.5, 2.2, 'W'); g.px(21, 7, 'k'); g.px(22, 7, 'k')
    g.rect(19, 15, 21, 18, 's')
    g.rows(9, 2, [(2, 7), (1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8), (2, 7)], 'M')
    g.px(11, 6, 'e'); g.px(16, 6, 'e'); g.rect(12, 8, 15, 9, 'R'); g.rect(13, 3, 14, 4, 'B')
    g.text(7, 0, ['R  B  R', ' R B R']); g.text(18, 1, ['G', 'G'])
    return g

def orchid_mantis():  # orchid mantis: a pink-white mantis shaped like an orchid, raptor arms raised
    pal = {'P': '#d8a0b8', 'p': '#b07a94', 'W': '#f0e0e8', 'G': '#7aa860', 'e': '#7fe36a'}
    g = G(pal)
    g.ell(11, 22, 6, 3.5, 'P'); g.ell(8, 21, 4, 3, 'W')
    g.line(14, 21, 18, 12, 'P', 2); g.ell(20, 9, 3, 2.5, 'P'); g.px(21, 8, 'e'); g.px(19, 8, 'e')
    g.line(17, 15, 23, 13, 'p'); g.line(23, 13, 25, 18, 'p'); g.line(18, 13, 24, 10, 'p'); g.line(24, 10, 27, 14, 'p')
    for x in (8, 11, 14): g.line(x, 24, x - 2, 29, 'G')
    g.tri([(5, 18), (1, 12), (8, 17)], 'W'); g.tri([(8, 18), (6, 11), (11, 17)], 'P')
    g.line(19, 6, 17, 2, 'p'); g.line(21, 6, 24, 2, 'p')
    return g

def silverback():  # silverback: a huge ape, silver back, knuckles down, mouth open in a roar
    pal = {'K': '#3a3436', 'k': '#2a2426', 'G': '#9a9aa0', 'S': '#6a5a50', 'e': E, 'w': '#f0f0e0', 'r': '#8a3a3a'}
    g = G(pal)
    g.ell(13, 16, 9, 8, 'K'); g.ell(11, 14, 6, 5, 'G')
    g.rect(4, 17, 8, 28, 'K'); g.rect(3, 27, 9, 29, 'k'); g.rect(19, 17, 23, 28, 'K'); g.rect(18, 27, 24, 29, 'k')
    g.rect(11, 22, 16, 28, 'k')
    g.ell(22, 10, 5, 4.5, 'K'); g.ell(23, 12, 3, 2.5, 'S'); g.px(22, 8, 'e'); g.px(25, 8, 'e')
    g.rect(22, 12, 25, 14, 'r'); g.text(22, 12, ['w  w'])
    return g

def idol_keeper():  # idol keeper: a priest in a jade mask and feathered headdress, an obsidian knife
    pal = {**SKIN2, 'J': '#3a8a6a', 'j': '#2a6a50', 'R': '#a83030', 'Y': '#c8a040', 'K': '#2a2430', 'W': '#d8d0c0', 'L': '#5a3a24', 'k': '#2a2028', 'e': '#ffe14d', 'F': '#7aa860'}
    g = G(pal)
    legs(g, 'L', 'k')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13)], 'R')
    g.rect(9, 13, 18, 15, 'Y'); g.rect(12, 16, 15, 23, 'W')
    g.rect(19, 15, 21, 18, 's'); g.tri([(21, 18), (26, 11), (23, 19)], 'K')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'J')
    g.px(11, 6, 'e'); g.px(16, 6, 'e'); g.rect(12, 8, 15, 8, 'j'); g.rect(11, 10, 16, 10, 'j')
    for i, x in enumerate(range(7, 21, 2)): g.line(x, 3, x - 1 + i % 3, -1 if i % 2 else 0, 'F' if i % 2 else 'R')
    return g

def jade_serpent():  # the Jade Serpent: a huge cobra of green jade, hood spread, gold markings
    pal = {'J': '#3a8a6a', 'j': '#2a6a50', 'Y': '#c8a040', 'e': '#ff4040', 'w': '#f0f0e0', 'p': '#d8c87a'}
    g = G(pal)
    g.ell(14, 27, 13, 3.5, 'J'); g.ell(8, 24, 6, 3, 'j')
    g.line(16, 27, 17, 14, 'J', 6); g.line(16, 22, 17, 16, 'p', 2)
    g.ell(18, 9, 9, 7, 'J'); g.ell(18, 10, 5, 5, 'j')
    g.ell(18, 8, 3.5, 3, 'J'); g.px(17, 7, 'e'); g.px(20, 7, 'e'); g.text(17, 10, ['w  w'])
    for x, y in ((11, 7), (25, 7), (12, 12), (24, 12)): g.px(x, y, 'Y'); g.px(x, y + 1, 'Y')
    g.rect(15, 15, 20, 15, 'Y')
    return g

def vine_mother():  # the Mother of Vines: a towering dryad of knotted vines, orchid crown, roots for feet
    pal = {'G': '#4a7a3c', 'g': '#36602e', 'W': '#6a4a2e', 'w': '#5a3a24', 'P': '#d8a0b8', 'R': '#a83a4a', 'Y': '#d8c040', 'e': '#ffe14d', 's': '#8ab870', 'S': '#6a9a54'}
    g = G(pal)
    g.rows(8, 12, [(2, 9), (1, 10), (1, 10), (0, 11), (0, 11), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-3, 14), (-3, 14),
                   (-4, 15), (-4, 15), (-4, 15), (-5, 16), (-5, 16)], 'G')
    for y in range(14, 28, 3): g.line(5, y, 21, y + 2, 'g')
    g.line(4, 28, 0, 31, 'W'); g.line(12, 28, 11, 31, 'W'); g.line(22, 28, 27, 31, 'W'); g.rect(3, 27, 24, 28, 'w')
    g.line(19, 14, 27, 8, 'G', 2); g.line(8, 14, 2, 9, 'G', 2); g.ell(27, 7, 2, 2, 'R'); g.ell(2, 8, 2, 2, 'R')
    face(g, 10, 4, 8, 7, eyes=False); g.px(12, 6, 'e'); g.px(15, 6, 'e'); g.rect(12, 9, 15, 9, 'S')
    g.text(8, 0, ['P R P R P', 'PYPYPYPYP', ' G  G  G ']); g.rect(8, 3, 19, 3, 'G')
    return g


# ================================================================ Aetherhold
def seraph_sentinel():  # seraph sentinel: a white-armoured angel with a tower shield and six small wings
    pal = {'A': '#d8d4c8', 'a': '#b0ac9e', 'G': '#c8a040', 'W': '#e8e4dc', 'w': '#c8c4b8', 'k': '#5a5650', 'L': '#b0ac9e', 'e': '#7fe3ff', 'Y': HALO}
    g = G(pal)
    g.tri([(10, 14), (2, 6), (5, 18)], 'w'); g.tri([(10, 18), (1, 16), (6, 24)], 'w')
    legs(g, 'L', 'k'); torso(g, 'A'); g.rect(13, 14, 14, 23, 'G')
    g.rect(18, 12, 25, 26, 'A'); g.rect(19, 13, 24, 25, 'a'); g.rect(21, 15, 22, 23, 'G'); g.rect(19, 18, 24, 19, 'G')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A'); g.rect(10, 6, 17, 7, 'k'); g.px(12, 6, 'e'); g.px(15, 6, 'e')
    g.ell(13.5, 1, 4, 1, 'Y')
    return g

def choir_cherub():  # choir cherub: a small round winged child-angel, a golden halo, mouth open in song
    pal = {**SKIN, 'W': '#e8e4dc', 'w': '#c8c4b8', 'Y': HALO, 'B': '#8aa0d8', 'e': E, 'm': '#a85a5a'}
    g = G(pal)
    g.tri([(10, 15), (2, 10), (6, 20)], 'W'); g.tri([(18, 15), (26, 10), (22, 20)], 'W')
    g.ell(14, 19, 5, 5, 'B'); g.ell(14, 21, 3, 2, 'w')
    face(g, 10, 8, 8, 7, eyes=False); g.px(12, 10, 'e'); g.px(15, 10, 'e'); g.rect(13, 12, 14, 13, 'm')
    g.ell(14, 5, 4, 1.2, 'Y'); g.rect(10, 7, 17, 8, 'Y')
    g.rect(11, 24, 12, 26, 's'); g.rect(16, 24, 17, 26, 's')
    return g

def haloed_knight():  # haloed knight: gold-trimmed white plate, a mace, a halo over the helm
    pal = {'A': '#c8c4b8', 'a': '#a8a498', 'G': '#c8a040', 'I': '#a8b0bc', 'k': '#5a5650', 'L': '#a8a498', 'e': '#7fe3ff', 'Y': HALO, 'R': '#3a5aa8'}
    g = G(pal)
    legs(g, 'L', 'k'); torso(g, 'A'); g.rect(8, 13, 19, 14, 'G'); g.rect(12, 15, 15, 22, 'R')
    g.rect(6, 13, 8, 20, 'A'); g.rect(19, 14, 21, 18, 'A'); g.rect(20, 18, 22, 19, 'a')
    g.rect(22, 9, 23, 20, 'k'); g.ell(22.5, 7, 3, 3, 'I'); g.px(20, 5, 'I'); g.px(25, 5, 'I'); g.px(22, 3, 'I')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A'); g.rect(10, 7, 17, 7, 'k'); g.px(12, 7, 'e'); g.px(15, 7, 'e')
    g.ell(13.5, 1, 4.5, 1, 'Y')
    return g

def eye_of_judgment():  # eye of judgment: a single great eye ringed by white wings and a gold ring
    pal = {'W': '#e8e4dc', 'w': '#c8c4b8', 'G': '#c8a040', 'g': '#a88430', 'B': '#3a7aa8', 'K': '#1a1420', 'e': '#7fe3ff'}
    g = G(pal)
    g.tri([(10, 14), (0, 6), (3, 20)], 'W'); g.tri([(20, 14), (30, 6), (27, 20)], 'W')
    g.tri([(10, 16), (3, 22), (9, 24)], 'w'); g.tri([(20, 16), (27, 22), (21, 24)], 'w')
    g.ell(15, 15, 7, 7, 'G'); g.ell(15, 15, 5.5, 5.5, 'g'); g.ell(15, 15, 4.5, 3.5, 'W')
    g.ell(15, 15, 2.5, 2.5, 'B'); g.ell(15, 15, 1, 1, 'K'); g.px(14, 14, 'e')
    return g

def fallen_angel():  # fallen angel: a grey-skinned angel with black tattered wings and a cracked halo
    pal = {'s': '#a8a4ac', 'S': '#88848e', 'K': '#2e2a34', 'k': '#221e28', 'R': '#5a2a3a', 'Y': '#8a7a40', 'e': '#ff4040', 'L': '#2e2a34'}
    g = G(pal)
    g.tri([(11, 14), (0, 3), (4, 22)], 'K'); g.tri([(16, 14), (28, 3), (25, 22)], 'K')
    for x in (2, 5, 24, 27): g.line(x, 20, x, 25, 'k')
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12),
                   (-3, 12), (-3, 12), (-3, 13), (-3, 13)], 'R')
    face(g, 10, 5, 8, 7, eyes=False); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.rect(10, 3, 17, 5, 'K')
    g.ell(13.5, 1, 4.5, 1, 'Y'); g.px(13, 1, 'k'); g.px(14, 0, 'k')
    return g

def lantern_archon():  # lantern archon: a floating lantern of gold filigree with a white flame, small wings
    pal = {'G': '#c8a040', 'g': '#a88430', 'F': '#f0e8c0', 'Y': '#ffd23f', 'W': '#e8e4dc', 'e': '#ffffff'}
    g = G(pal)
    g.tri([(10, 14), (3, 8), (6, 18)], 'W'); g.tri([(19, 14), (26, 8), (23, 18)], 'W')
    g.rect(10, 9, 19, 21, 'g'); g.rect(11, 10, 18, 20, 'F'); g.ell(14.5, 15, 2.5, 3.5, 'Y'); g.px(14, 14, 'e')
    g.rect(9, 7, 20, 8, 'G'); g.rect(9, 21, 20, 22, 'G'); g.rect(13, 3, 16, 6, 'G'); g.rect(14, 0, 15, 2, 'g')
    g.rect(13, 23, 16, 25, 'g'); g.px(14, 27, 'Y'); g.px(15, 29, 'Y')
    return g

def virtue_of_wrath():  # virtue of wrath: a red-and-gold war-angel with a flaming sword, wings swept back
    pal = {'A': '#c8a040', 'a': '#a88430', 'R': '#a83030', 'W': '#e8e4dc', 'w': '#c8c4b8', 'F': '#ff7a1a', 'Y': '#ffd23f', 'k': '#4a3a2a', 'L': '#a88430', 'e': '#ffd23f'}
    g = G(pal)
    g.tri([(10, 13), (0, 2), (3, 20)], 'W'); g.tri([(10, 16), (1, 12), (5, 24)], 'w')
    legs(g, 'L', 'k'); torso(g, 'A'); g.rect(11, 14, 16, 23, 'R')
    g.rect(19, 14, 21, 18, 'A'); g.rect(20, 18, 22, 19, 'a')
    g.line(22, 18, 29, 1, 'Y', 2); g.line(23, 16, 30, 3, 'F'); g.rect(20, 18, 24, 19, 'k')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A'); g.rect(10, 7, 17, 7, 'k'); g.px(12, 7, 'e'); g.px(15, 7, 'e')
    g.text(10, 0, ['F Y F', ' YFY'])
    return g

def wheel_of_eyes():  # the Wheel of Eyes: two interlocking burning gold rings studded with eyes, wings behind
    pal = {'G': '#c8a040', 'g': '#a88430', 'W': '#e8e4dc', 'B': '#3a7aa8', 'K': '#1a1420', 'F': '#ff7a1a', 'e': '#7fe3ff'}
    g = G(pal)
    g.tri([(15, 15), (0, 2), (2, 26)], 'W'); g.tri([(16, 15), (31, 2), (29, 26)], 'W')
    import math
    for r, c in ((13, 'G'), (12, 'g')):
        for a in range(80):
            g.px(int(round(15.5 + r * math.cos(a * 0.0785))), int(round(15.5 + r * 0.95 * math.sin(a * 0.0785))), c)
    for a in range(80):
        g.px(int(round(15.5 + 8 * math.cos(a * 0.0785))), int(round(15.5 + 11 * math.sin(a * 0.0785))), 'G')
    for a in range(0, 360, 45):
        x, y = 15.5 + 12.5 * math.cos(math.radians(a)), 15.5 + 12 * math.sin(math.radians(a))
        g.ell(x, y, 1.6, 1.2, 'W'); g.px(int(round(x)), int(round(y)), 'B')
    g.ell(15.5, 15.5, 3, 3, 'W'); g.ell(15.5, 15.5, 1.6, 1.6, 'B'); g.px(15, 15, 'K'); g.px(16, 14, 'e')
    return g

def radiant_arbiter():  # the Radiant Arbiter: a tall blindfolded angel-judge with golden scales and a sword of light
    pal = {**SKIN, 'W': '#e8e4dc', 'w': '#c8c4b8', 'G': '#c8a040', 'g': '#a88430', 'B': '#3a5aa8', 'Y': HALO, 'F': '#fff2b0', 'k': '#5a5650'}
    g = G(pal)
    g.tri([(9, 12), (0, 0), (2, 22)], 'W'); g.tri([(19, 12), (28, 0), (26, 22)], 'w')
    g.rows(8, 12, [(1, 10), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13), (-3, 14), (-3, 14),
                   (-3, 14), (-4, 15), (-4, 15), (-4, 15), (-4, 15), (-4, 15), (-4, 15)], 'W')
    g.rect(12, 12, 15, 29, 'B'); g.rect(7, 12, 20, 13, 'G')
    g.rect(20, 13, 23, 17, 'W'); g.line(23, 17, 30, 2, 'F', 2)
    g.rect(4, 13, 7, 17, 'W'); g.line(5, 17, 5, 22, 'g'); g.line(1, 22, 9, 22, 'G'); g.text(0, 23, ['GG     GG']); g.px(5, 22, 'G')
    face(g, 10, 4, 8, 7, eyes=False); g.rect(10, 6, 17, 7, 'k'); g.rect(12, 9, 15, 9, 'S')
    g.ell(13.5, 1, 5, 1.2, 'Y')
    return g


# ================================================================ the Prism Wood
def crystal_golem():  # crystal golem: a blocky body of pale violet crystal shards, a bright heart
    pal = {'C': '#a898d0', 'c': '#8070b0', 'W': '#d8d0f0', 'P': '#ff9ad5', 'e': '#ffffff', 'k': '#5a4a80'}
    g = G(pal)
    g.rect(8, 23, 12, 29, 'c'); g.rect(16, 23, 20, 29, 'c'); g.rect(7, 29, 12, 30, 'k'); g.rect(16, 29, 21, 30, 'k')
    g.tri([(5, 11), (23, 11), (14, 26)], 'C'); g.rect(6, 11, 22, 19, 'C')
    g.tri([(7, 11), (11, 11), (9, 5)], 'W'); g.tri([(17, 11), (22, 11), (20, 3)], 'C'); g.tri([(12, 11), (16, 11), (14, 6)], 'c')
    g.ell(14, 16, 2.5, 2.5, 'P'); g.px(14, 15, 'e')
    g.tri([(1, 14), (6, 12), (5, 24)], 'C'); g.tri([(27, 14), (22, 12), (23, 24)], 'c')
    g.px(11, 13, 'e'); g.px(17, 13, 'e')
    return g

def shardling():  # shardling: a little cluster of sharp crystal spikes on spindly legs
    pal = {'C': '#a898d0', 'c': '#8070b0', 'W': '#d8d0f0', 'e': '#ff9ad5', 'k': '#5a4a80'}
    g = G(pal)
    g.tri([(9, 22), (12, 8), (15, 22)], 'C'); g.tri([(13, 22), (17, 12), (21, 22)], 'c'); g.tri([(6, 22), (7, 14), (11, 22)], 'W')
    g.tri([(17, 22), (23, 15), (22, 23)], 'C'); g.rect(7, 21, 22, 23, 'c')
    for x in (8, 12, 17, 21): g.line(x, 24, x - 1 if x < 14 else x + 1, 29, 'k')
    g.px(13, 18, 'e'); g.px(16, 18, 'e')
    return g

def prism_spider():  # prism spider: a glassy spider whose body splits light into a rainbow band
    pal = {'C': '#b0c8e0', 'c': '#8aa0c0', 'R': '#e86a6a', 'Y': '#e8d070', 'G': '#7ac86a', 'B': '#6a9ae8', 'e': '#ff9ad5', 'k': '#5a6a80'}
    g = G(pal)
    g.ell(11, 18, 7, 5.5, 'C'); g.ell(20, 19, 4, 3.5, 'c')
    g.line(6, 17, 16, 17, 'R'); g.line(6, 18, 16, 18, 'Y'); g.line(6, 19, 16, 19, 'G'); g.line(6, 20, 16, 20, 'B')
    g.px(22, 18, 'e'); g.px(23, 20, 'e')
    for i, (x, y) in enumerate(((16, 21), (18, 22), (14, 22), (20, 22))):
        g.line(x, y, x + (5 if i % 2 else -5), y + 6, 'k'); g.line(x, y - 5, x + (6 if i % 2 else -6), y - 11, 'k')
    return g

def geode_tortoise():  # geode tortoise: a slow tortoise whose shell is a split geode full of amethyst
    pal = {'R': '#7a7066', 'r': '#5a524a', 'P': '#9a6ac8', 'p': '#c8a0e8', 'G': '#7a8a5a', 'g': '#5a6a44', 'e': E}
    g = G(pal)
    g.ell(13, 19, 10, 7, 'R'); g.ell(13, 18, 7.5, 5, 'P')
    for x, y in ((9, 16), (14, 15), (17, 19), (11, 20), (15, 21)): g.tri([(x, y + 2), (x + 1, y - 1), (x + 2, y + 2)], 'p')
    g.ell(13, 24, 10, 2.5, 'r')
    g.ell(25, 21, 4, 3, 'G'); g.px(26, 20, 'e')
    for x in (5, 10, 16, 20): g.rect(x, 24, x + 2, 28, 'g')
    return g

def resonant_wisp():  # resonant wisp: a hovering tuning-fork of light, rings of sound around it
    pal = {'C': '#d8d0f0', 'c': '#a898d0', 'P': '#ff9ad5', 'e': '#ffffff'}
    g = G(pal)
    g.rect(11, 6, 12, 18, 'C'); g.rect(17, 6, 18, 18, 'C'); g.rect(11, 18, 18, 20, 'C'); g.rect(14, 20, 15, 26, 'c')
    g.ell(14.5, 16, 2, 2, 'P'); g.px(14, 15, 'e')
    import math
    for r in (9, 12):
        for a in range(0, 360, 20):
            if (a // 20) % 2:
                g.px(int(round(14.5 + r * math.cos(math.radians(a)))), int(round(14 + r * 0.8 * math.sin(math.radians(a)))), 'c')
    return g

def crystal_stag():  # crystal stag: a pale stag whose antlers are branching crystal
    pal = {'W': '#d8d4cc', 'w': '#b0aca4', 'C': '#a898d0', 'c': '#d8d0f0', 'e': E, 'k': '#6a6660'}
    g = G(pal)
    g.ell(12, 18, 8, 4.5, 'W'); g.ell(11, 20, 6, 2, 'w')
    for x in (6, 9, 15, 18): g.rect(x, 21, x + 1, 29, 'W' if x in (6, 15) else 'w')
    g.line(18, 16, 21, 10, 'W', 3); g.ell(23, 9, 3.5, 2.8, 'W'); g.rect(25, 9, 28, 11, 'W'); g.px(23, 8, 'e'); g.px(28, 10, 'k')
    g.line(21, 7, 18, 1, 'C'); g.line(19, 4, 16, 3, 'c'); g.line(23, 6, 26, 0, 'C'); g.line(25, 3, 28, 2, 'c')
    g.px(3, 16, 'w')
    return g

def facet_knight():  # facet knight: armour of cut crystal plates, a prism shield and a glass sword
    pal = {'C': '#a898d0', 'c': '#8070b0', 'W': '#d8d0f0', 'k': '#4a3a70', 'L': '#8070b0', 'e': '#ff9ad5', 'R': '#e86a6a', 'Y': '#e8d070', 'B': '#6a9ae8'}
    g = G(pal)
    legs(g, 'L', 'k'); torso(g, 'C'); g.tri([(8, 13), (19, 13), (13, 23)], 'W'); g.line(13, 13, 13, 23, 'c')
    g.rect(1, 13, 7, 24, 'W'); g.line(1, 17, 7, 17, 'R'); g.line(1, 18, 7, 18, 'Y'); g.line(1, 19, 7, 19, 'B')
    g.rect(19, 14, 21, 18, 'C'); g.line(22, 18, 29, 4, 'W', 2); g.rect(20, 18, 24, 19, 'k')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'C'); g.rect(10, 7, 17, 7, 'k'); g.px(12, 7, 'e'); g.px(15, 7, 'e')
    g.tri([(11, 3), (13, 0), (15, 3)], 'W')
    return g

def prism_colossus():  # the Prism Colossus: a vast figure of stacked crystal pillars, a beam-eye
    pal = {'C': '#a898d0', 'c': '#8070b0', 'W': '#d8d0f0', 'P': '#ff9ad5', 'e': '#ffffff', 'k': '#4a3a70'}
    g = G(pal)
    g.rect(6, 22, 12, 30, 'c'); g.rect(17, 22, 23, 30, 'c'); g.rect(7, 23, 11, 30, 'C')
    g.rect(3, 8, 26, 22, 'C'); g.rect(5, 10, 9, 20, 'W'); g.rect(20, 10, 24, 20, 'c')
    g.tri([(3, 8), (8, 0), (12, 8)], 'W'); g.tri([(17, 8), (22, 1), (26, 8)], 'C'); g.tri([(10, 8), (15, 2), (19, 8)], 'c')
    g.ell(14.5, 14, 4, 3, 'k'); g.ell(14.5, 14, 2.5, 2, 'P'); g.px(14, 13, 'e')
    g.rect(0, 10, 3, 22, 'C'); g.rect(26, 10, 29, 22, 'c')
    return g

def shard_queen():  # the Shard Queen: a crystal-skinned queen in a gown of facets, a towering crystal crown
    pal = {'s': '#c8c0e8', 'S': '#a898d0', 'G': '#8070b0', 'g': '#5a4a80', 'W': '#d8d0f0', 'P': '#ff9ad5', 'e': '#ff9ad5', 'k': '#4a3a70'}
    g = G(pal)
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13), (-3, 14), (-3, 14),
                   (-3, 14), (-4, 15), (-4, 15), (-4, 15), (-4, 15), (-4, 15)], 'G')
    for x in range(5, 23, 4): g.tri([(x, 29), (x + 2, 18), (x + 4, 29)], 'S')
    g.rect(7, 13, 20, 14, 'W'); g.ell(13.5, 16, 1.6, 1.6, 'P')
    g.rect(20, 14, 23, 17, 's'); g.tri([(23, 17), (29, 6), (26, 18)], 'W'); g.rect(4, 14, 7, 17, 's')
    face(g, 10, 5, 8, 7, eyes=False); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.rect(12, 10, 15, 10, 'S')
    g.tri([(9, 5), (10, 0), (12, 5)], 'W'); g.tri([(12, 5), (13.5, -1), (15, 5)], 'S'); g.tri([(15, 5), (17, 0), (18, 5)], 'W')
    g.tri([(7, 6), (6, 2), (9, 6)], 'S'); g.tri([(18, 6), (21, 2), (20, 6)], 'S')
    return g


# ================================================================ the Drowsing Vale
def sleepwalker():  # sleepwalker: a figure in a nightgown and cap, arms out, eyes shut, a candle
    pal = {**SKIN, 'W': '#c8c0d8', 'w': '#a8a0b8', 'B': '#6a5a9a', 'Y': '#ffd27a', 'G': '#c8a040', 'k': '#4a4258', 'o': '#3a3040'}
    pal['z'] = pal['Z'] = '#d8d4f0'
    g = G(pal)
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12),
                   (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'W')
    g.rect(13, 14, 14, 28, 'w')
    g.rect(19, 15, 26, 17, 'W'); g.rect(24, 15, 26, 16, 's'); g.rect(25, 11, 26, 14, 'G'); g.px(25, 10, 'Y'); g.px(25, 9, 'Y')
    face(g, 10, 6, 8, 6, eyes=False); g.rect(11, 8, 12, 8, 'o'); g.rect(15, 8, 16, 8, 'o')
    g.rows(9, 2, [(3, 7), (1, 8), (0, 9), (0, 9)], 'B'); g.line(17, 3, 21, 6, 'B'); g.px(22, 7, 'W')
    g.text(2, 2, ['z', ' Z', 'z'])
    return g

def dusk_moth():  # dusk moth: a big soft moth, lilac wings with moon-eye spots
    pal = {'L': '#9a8ac8', 'l': '#7a6aa8', 'W': '#e8e0f0', 'B': '#4a3a6a', 'Y': '#e8d070', 'e': E}
    g = G(pal)
    g.ell(8, 12, 7, 7, 'L'); g.ell(21, 12, 7, 7, 'L'); g.ell(9, 22, 5, 5, 'l'); g.ell(20, 22, 5, 5, 'l')
    g.ell(8, 12, 2.5, 2.5, 'W'); g.ell(21, 12, 2.5, 2.5, 'W'); g.px(8, 12, 'B'); g.px(21, 12, 'B')
    g.ell(14.5, 17, 2, 8, 'B'); g.px(14, 10, 'e'); g.px(15, 10, 'e')
    g.line(14, 9, 11, 3, 'Y'); g.line(15, 9, 18, 3, 'Y')
    return g

def dream_eater():  # dream eater: a tapir-like beast, starry hide, long trunk snuffling
    pal = {'B': '#3a3a6a', 'b': '#2a2a50', 'W': '#e8e0f0', 'Y': '#e8d070', 'e': '#e8d070', 'P': '#c8a0e8'}
    g = G(pal)
    g.ell(12, 19, 9, 6, 'B'); g.ell(11, 22, 7, 2.5, 'b')
    for x in (5, 9, 15, 18): g.rect(x, 23, x + 2, 29, 'b')
    g.ell(22, 15, 5, 4.5, 'B'); g.line(26, 16, 29, 22, 'B', 2); g.px(29, 23, 'P')
    g.px(22, 13, 'e'); g.ell(20, 11, 1.5, 1.5, 'b')
    for x, y in ((8, 16), (13, 15), (16, 19), (6, 20), (11, 18), (24, 17)): g.px(x, y, 'W')
    g.px(10, 14, 'Y'); g.px(19, 21, 'Y')
    return g

def laughing_jester():  # laughing jester: a lanky jester in harlequin diamonds, bells, a mask grinning
    pal = {**SKIN, 'R': '#a83a5a', 'B': '#3a3a8a', 'Y': '#e8d070', 'W': '#e8e0f0', 'k': '#2a2430', 'L': '#3a3a8a', 'e': E, 'i': '#dfe6ee'}
    g = G(pal)
    legs(g, 'L', 'k'); g.rect(10, 24, 12, 28, 'R')
    torso(g, 'R'); g.rows(14, 13, [(0, 5), (0, 5), (0, 5), (0, 5), (0, 5), (0, 5), (0, 5), (0, 5), (0, 5), (0, 5), (0, 5)], 'B')
    g.rect(8, 13, 19, 14, 'Y')
    g.rect(19, 14, 21, 18, 'B'); g.rect(21, 12, 22, 14, 's'); g.line(22, 11, 25, 6, 'i'); g.line(24, 13, 28, 9, 'i')
    face(g, 10, 6, 8, 6, eyes=False); g.rect(10, 6, 17, 8, 'W'); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.rect(11, 10, 16, 10, 'k')
    g.tri([(9, 5), (4, 1), (12, 3)], 'R'); g.tri([(13, 4), (13, 0), (16, 4)], 'B'); g.tri([(16, 5), (22, 1), (18, 3)], 'R')
    g.px(4, 1, 'Y'); g.px(13, 0, 'Y'); g.px(22, 1, 'Y')
    return g

def mirror_shade():  # mirror shade: a shadowy figure inside a hand mirror's silver frame
    pal = {'G': '#a8b0bc', 'g': '#7a8494', 'K': '#3a3a5a', 'k': '#2a2a40', 'e': '#c8a0e8', 'W': '#e8e0f0'}
    g = G(pal)
    g.ell(14.5, 12, 8, 10, 'G'); g.ell(14.5, 12, 6.5, 8.5, 'K'); g.rect(13, 22, 16, 30, 'g'); g.rect(11, 29, 18, 30, 'G')
    g.ell(14.5, 9, 2.5, 2.5, 'k'); g.rows(11, 12, [(1, 6), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7)], 'k')
    g.px(13, 9, 'e'); g.px(16, 9, 'e'); g.px(10, 5, 'W'); g.px(11, 4, 'W')
    return g

def dreamsoft_golem():  # dreamsoft golem: a pillowy cloud-golem, stitched seams, sleepy button eyes
    pal = {'W': '#d8d0e8', 'w': '#b0a8c8', 'B': '#6a5a9a', 'e': '#3a3058', 'P': '#c8a0d8'}
    g = G(pal)
    g.ell(9, 26, 5, 3.5, 'w'); g.ell(20, 26, 5, 3.5, 'w')
    g.ell(14.5, 17, 11, 8, 'W'); g.ell(6, 13, 4, 3.5, 'W'); g.ell(23, 13, 4, 3.5, 'W'); g.ell(14.5, 9, 6, 5, 'W')
    g.ell(2, 19, 3, 4, 'w'); g.ell(27, 19, 3, 4, 'w')
    g.line(14, 13, 14, 23, 'P'); for_ = None
    for y in range(14, 23, 2): g.px(13, y, 'P'); g.px(15, y, 'P')
    g.ell(12, 9, 1.2, 1.2, 'e'); g.ell(17, 9, 1.2, 1.2, 'e'); g.rect(13, 12, 16, 12, 'B')
    return g

def nightmare_knight():  # nightmare knight: black armour wreathed in purple smoke, a horned helm, a jagged blade
    pal = {'A': '#3a3448', 'a': '#2a2436', 'P': '#7a5aa8', 'p': '#5a3a8a', 'I': '#a8b0bc', 'k': '#1e1a28', 'L': '#2a2436', 'e': '#c8a0ff'}
    g = G(pal)
    for x, y in ((4, 22), (22, 24), (7, 10), (24, 14)): g.ell(x, y, 2.5, 2, 'p')
    legs(g, 'L', 'k'); torso(g, 'A'); g.rect(8, 21, 19, 21, 'P'); g.rect(13, 14, 14, 20, 'P')
    g.rect(6, 13, 8, 20, 'A'); g.rect(19, 14, 21, 18, 'A')
    g.line(22, 18, 29, 4, 'I', 2); g.px(25, 11, 'k'); g.px(27, 7, 'k'); g.rect(20, 18, 24, 19, 'k')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A'); g.rect(10, 7, 17, 7, 'k'); g.px(12, 7, 'e'); g.px(15, 7, 'e')
    g.tri([(9, 4), (5, -1), (11, 3)], 'a'); g.tri([(18, 4), (22, -1), (16, 3)], 'a')
    return g

def night_mare():  # the Night Mare: a black horse with a mane and tail of violet flame, eyes like moons
    pal = {'K': '#2a2436', 'k': '#1e1a28', 'P': '#9a6ae8', 'p': '#6a3aa8', 'e': '#e8e0f0', 'Y': '#e8d070'}
    g = G(pal)
    g.ell(13, 17, 9, 5.5, 'K'); g.ell(12, 20, 7, 2.5, 'k')
    for x, dx in ((5, -2), (9, 0), (16, 0), (20, 2)): g.line(x, 21, x + dx, 29, 'K' if x in (5, 16) else 'k', 2)
    g.line(19, 14, 24, 6, 'K', 4); g.ell(26, 5, 3.5, 3, 'K'); g.rect(27, 5, 31, 8, 'K'); g.px(26, 4, 'e')
    g.text(17, 3, ['  P', ' PpP', 'PpP', 'pP', 'P']); g.text(1, 13, ['P', 'Pp', 'pP', ' P', 'P'])
    for x, dx in ((5, -2), (9, 0), (16, 0), (20, 2)): g.px(x + dx, 30, 'p')
    return g

def somnarch():  # the Somnarch: a regal sleeper on a floating crescent moon, robes of night sky, a sleeping mask
    pal = {**SKIN, 'B': '#2e2a5a', 'b': '#221e44', 'W': '#e8e0f0', 'Y': '#e8d070', 'y': '#b8a050', 'P': '#9a6ae8', 'k': '#1a1430'}
    pal['z'] = pal['Z'] = '#d8d4f0'
    g = G(pal)
    g.tri([(2, 24), (14, 31), (28, 24)], 'Y'); g.tri([(5, 24), (14, 28), (25, 24)], 'y')
    g.rows(8, 11, [(1, 10), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13), (-3, 14), (-3, 14), (-3, 14), (-4, 15)], 'B')
    for x, y in ((6, 18), (11, 15), (17, 20), (21, 17), (9, 21), (15, 13)): g.px(x, y, 'W')
    g.rect(12, 11, 15, 23, 'b'); g.rect(7, 11, 20, 12, 'P')
    g.rect(20, 12, 23, 15, 'B'); g.rect(22, 15, 24, 16, 's'); g.ell(25, 18, 2, 2, 'P')
    face(g, 10, 4, 8, 7, eyes=False); g.rect(10, 6, 17, 7, 'P'); g.rect(12, 9, 15, 9, 'S')
    g.text(9, 0, ['Y  Y  Y', 'YYYYYYYYY']); g.rect(9, 2, 18, 3, 'y')
    g.text(23, 1, ['z', ' Z', '  z'])
    return g


# ================================================================ the Frostpeaks
def frost_wolf():  # frost wolf: a white wolf with blue-grey back and icy breath
    pal = {'W': '#d8e0e8', 'w': '#a8b4c4', 'B': '#6a7a94', 'e': '#7fe3ff', 'k': '#3a4454', 'C': '#bfe8ff'}
    g = G(pal)
    g.ell(13, 20, 8, 4.5, 'W'); g.ell(12, 17, 6, 2.5, 'B')
    for x in (7, 10, 16, 19): g.rect(x, 23, x + 1, 29, 'W' if x in (7, 16) else 'w')
    g.line(5, 18, 1, 12, 'W', 2); g.px(1, 11, 'w')
    g.ell(22, 14, 4.5, 4, 'W'); g.rect(24, 15, 28, 17, 'W'); g.px(28, 15, 'k'); g.px(23, 13, 'e')
    g.tri([(20, 11), (21, 6), (23, 11)], 'B'); g.px(29, 18, 'C'); g.px(30, 17, 'C')
    return g

def ice_wraith():  # ice wraith: a hooded spectre of frost, icicle fingers, a pale blue glow
    pal = {'C': '#a8c8e0', 'c': '#7a9ab8', 'D': '#2a3a54', 'e': '#7fe3ff', 'W': '#e8f4ff'}
    g = G(pal)
    g.rows(8, 8, [(3, 9), (2, 10), (1, 11), (1, 11), (0, 12), (0, 12), (0, 12), (-1, 13), (-1, 13), (-1, 13), (-1, 14),
                  (-2, 14), (-2, 15), (-2, 15), (-3, 15), (-3, 16), (-3, 16)], 'C')
    g.ell(14, 8, 6, 6, 'C'); g.ell(14, 9, 3.5, 3.5, 'D'); g.px(12, 9, 'e'); g.px(16, 9, 'e')
    for x, y in ((6, 25), (10, 26), (15, 25), (19, 26), (23, 25)): g.tri([(x, y), (x + 2, y), (x + 1, y + 4)], 'c')
    g.line(21, 14, 27, 11, 'C', 2); for_x = (27, 28, 29)
    for x in for_x: g.line(x, 11, x + 1, 15, 'W')
    return g

def frozen_revenant():  # frozen revenant: a dead warrior encased in ice, a frost-rimed axe
    pal = {'s': '#8aa0b0', 'S': '#6a8090', 'C': '#bfe0f4', 'c': '#8ab0d0', 'A': '#5a6a7a', 'I': '#a8b0bc', 'k': '#2a3444', 'L': '#4a5a6a', 'e': '#7fe3ff', 'w': '#5a3a24'}
    g = G(pal)
    legs(g, 'L', 'k'); torso(g, 'A')
    g.tri([(7, 13), (10, 24), (5, 24)], 'C'); g.tri([(18, 14), (21, 24), (16, 24)], 'c')
    g.rect(19, 14, 21, 18, 'A'); g.rect(21, 4, 22, 20, 'w'); g.tri([(22, 4), (28, 2), (27, 10)], 'I'); g.px(26, 5, 'C')
    face(g, 10, 5, 8, 7, eyes=False); g.px(12, 7, 'e'); g.px(15, 7, 'e'); g.rect(12, 10, 15, 10, 'S')
    g.rect(9, 2, 18, 4, 'c'); g.tri([(10, 2), (11, -1), (12, 2)], 'C'); g.tri([(15, 2), (16, -1), (17, 2)], 'C')
    return g

def rime_hag():  # rime hag: a hunched crone in grey furs, frosted hair, a bubbling icy cauldron-staff
    pal = {'s': '#a8b8c8', 'S': '#8898a8', 'F': '#7a7068', 'f': '#5a524a', 'W': '#e8f0f4', 'w': '#5a3a24', 'C': '#7fe3ff', 'k': '#2a3444', 'e': '#7fe3ff'}
    g = G(pal)
    g.rows(8, 12, [(2, 10), (1, 11), (0, 12), (0, 12), (-1, 12), (-1, 13), (-1, 13), (-2, 13), (-2, 14), (-2, 14), (-3, 14),
                   (-3, 15), (-3, 15), (-3, 15), (-3, 15), (-3, 15), (-3, 15)], 'F')
    g.rect(13, 14, 15, 28, 'f')
    g.rect(22, 6, 23, 30, 'w'); g.ell(22.5, 5, 3, 2.2, 'k'); g.ell(22.5, 4, 2, 1, 'C'); g.px(21, 2, 'C'); g.px(24, 1, 'C')
    g.rect(20, 14, 22, 17, 'F'); g.rect(21, 17, 23, 18, 's')
    face(g, 9, 5, 8, 6, eyes=False); g.px(11, 7, 'e'); g.px(14, 7, 'e'); g.rect(11, 9, 14, 9, 'S'); g.px(16, 8, 'S')
    g.rows(7, 2, [(2, 9), (1, 10), (0, 11), (0, 2), (0, 1), (0, 1), (0, 1), (0, 1)], 'W')
    return g

def woolly_mammoth():  # woolly mammoth: shaggy brown hulk, curling ivory tusks, a raised trunk
    pal = {'B': '#6a4e3a', 'b': '#4e3828', 'W': '#e8e0cc', 'e': E, 'C': '#d8e8f4'}
    g = G(pal)
    g.ell(13, 16, 11, 8, 'B'); g.ell(12, 20, 9, 4, 'b')
    for x in (4, 9, 15, 19): g.rect(x, 21, x + 3, 29, 'B' if x in (4, 15) else 'b')
    g.ell(23, 12, 5, 5, 'B'); g.line(27, 14, 30, 8, 'B', 2); g.px(30, 7, 'b'); g.px(23, 10, 'e')
    g.line(25, 17, 29, 20, 'W', 2); g.line(29, 20, 30, 16, 'W')
    g.text(3, 8, ['C C', ' C C C'])
    return g

def icicle_sprite():  # icicle sprite: a tiny glittering sprite of ice crystals with frost wings
    pal = {'C': '#bfe0f4', 'c': '#8ab0d0', 'W': '#f0f8ff', 'e': '#3a6a9a'}
    g = G(pal)
    g.tri([(13, 14), (4, 6), (7, 18)], 'W'); g.tri([(16, 14), (25, 6), (22, 18)], 'W')
    g.tri([(12, 10), (14.5, 3), (17, 10)], 'C'); g.rect(12, 10, 17, 18, 'C'); g.tri([(12, 18), (14.5, 28), (17, 18)], 'c')
    g.px(13, 12, 'e'); g.px(16, 12, 'e')
    for x, y in ((5, 22), (24, 24), (9, 27), (21, 20)): g.px(x, y, 'W')
    return g

def frost_giant():  # frost giant: a huge blue-skinned giant, white beard, an ice-crusted club
    pal = {'s': '#7a9ab8', 'S': '#5a7a98', 'F': '#7a6a5a', 'f': '#5a4a3a', 'W': '#e8f0f4', 'C': '#bfe0f4', 'w': '#6a4a2e', 'k': '#2a3444', 'e': '#ffe14d'}
    g = G(pal)
    g.rect(8, 23, 12, 29, 'f'); g.rect(16, 23, 20, 29, 'f'); g.rect(7, 29, 12, 30, 'k'); g.rect(16, 29, 21, 30, 'k')
    g.rect(6, 12, 21, 23, 'F'); g.rect(10, 12, 17, 23, 's'); g.rect(6, 20, 21, 21, 'f')
    g.rect(2, 13, 5, 22, 's'); g.rect(22, 12, 25, 18, 's')
    g.line(24, 18, 28, 2, 'w', 3); g.ell(28, 3, 3, 3, 'C'); g.px(27, 1, 'W')
    face(g, 9, 3, 10, 7, eyes=False); g.px(11, 5, 'e'); g.px(16, 5, 'e'); g.rows(9, 8, [(0, 9), (0, 9), (1, 8), (2, 7), (3, 6), (4, 5)], 'W')
    g.rect(9, 2, 18, 3, 'W')
    return g

def avalanche_yeti():  # the Avalanche Yeti: a towering white-furred yeti, blue face, claws, snow sloughing off
    pal = {'W': '#e0e8ee', 'w': '#b8c4d0', 'B': '#6a8aa8', 'b': '#4a6a88', 'e': '#ffe14d', 'k': '#2a3444', 'C': '#f0f8ff'}
    g = G(pal)
    g.rect(7, 23, 12, 29, 'w'); g.rect(17, 23, 22, 29, 'w'); g.rect(6, 29, 12, 30, 'b'); g.rect(17, 29, 23, 30, 'b')
    g.ell(14.5, 16, 10, 9, 'W'); g.ell(14.5, 19, 6, 5, 'w')
    g.rect(1, 13, 5, 26, 'W'); g.rect(24, 13, 28, 26, 'W'); g.text(0, 26, ['b b b']); g.text(24, 26, ['b b b'])
    g.ell(14.5, 7, 6, 5, 'W'); g.ell(14.5, 8, 3.5, 3, 'B'); g.px(13, 7, 'e'); g.px(16, 7, 'e'); g.rect(13, 10, 16, 10, 'k')
    g.tri([(9, 5), (7, 0), (11, 4)], 'w'); g.tri([(20, 5), (22, 0), (18, 4)], 'w')
    for x, y in ((3, 6), (26, 5), (8, 29), (23, 2)): g.px(x, y, 'C')
    return g

def rime_matriarch():  # the Rime Matriarch: an ice-queen of the wolves, wolf-pelt cloak, a crown of icicles, a frost spear
    pal = {'s': '#b8c8d8', 'S': '#98a8b8', 'W': '#e0e8ee', 'w': '#b8c4d0', 'B': '#3a5a8a', 'b': '#2a4470', 'C': '#bfe0f4', 'I': '#e8f4ff', 'e': '#7fe3ff', 'k': '#2a3444'}
    g = G(pal)
    g.rows(8, 12, [(1, 10), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13), (-3, 14), (-3, 14),
                   (-3, 14), (-4, 15), (-4, 15), (-4, 15), (-4, 15), (-4, 15), (-4, 15)], 'B')
    g.rect(12, 12, 15, 29, 'b')
    g.rows(4, 11, [(0, 5), (0, 5), (-1, 5), (-1, 4), (-1, 4), (-1, 3)], 'W'); g.rows(19, 11, [(0, 5), (0, 5), (1, 6), (2, 6), (2, 6)], 'W')
    g.ell(6, 9, 3, 2.5, 'w'); g.px(5, 8, 'k')
    g.rect(21, 13, 24, 17, 'B'); g.rect(23, 1, 24, 30, 'C'); g.tri([(21, 3), (23.5, -2), (26, 3)], 'I')
    face(g, 10, 4, 8, 7, eyes=False); g.px(12, 6, 'e'); g.px(15, 6, 'e'); g.rect(12, 9, 15, 9, 'S')
    g.tri([(9, 4), (10, -1), (11, 4)], 'I'); g.tri([(12, 4), (13.5, -2), (15, 4)], 'C'); g.tri([(16, 4), (17, -1), (18, 4)], 'I')
    g.rect(9, 3, 18, 3, 'C')
    return g


ALL = [cinder_imp, magma_crawler, ash_wraith, obsidian_golem, ember_cultist, lava_hound, forge_knight, caldera_wyrm, slag_tyrant,
       dune_scorpion, dune_raider, wrapped_dead, glass_mage, carrion_vulture, scarab_swarm, riddling_sphinx, great_sandworm, sun_eaten_king,
       stone_treant, basilisk, gargoyle, fossil_hound, amber_wisp, lichen_shaman, sleeping_sentinel, petrified_knight, elder_basilisk, heartwood_gorgon,
       shadow_panther, dart_frog, strangler_vine, witch_doctor, orchid_mantis, silverback, idol_keeper, jade_serpent, vine_mother,
       seraph_sentinel, choir_cherub, haloed_knight, eye_of_judgment, fallen_angel, lantern_archon, virtue_of_wrath, wheel_of_eyes, radiant_arbiter,
       crystal_golem, shardling, prism_spider, geode_tortoise, resonant_wisp, crystal_stag, facet_knight, prism_colossus, shard_queen,
       sleepwalker, dusk_moth, dream_eater, laughing_jester, mirror_shade, dreamsoft_golem, nightmare_knight, night_mare, somnarch,
       frost_wolf, ice_wraith, frozen_revenant, rime_hag, woolly_mammoth, icicle_sprite, frost_giant, avalanche_yeti, rime_matriarch]

if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    items = [(f.__name__, f().strings(), f().pal) for f in ALL]
    sheet(items, out + '/foes2.png', scale=4, cols=9, bg=(16, 22, 31))
