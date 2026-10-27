# Monsters, one design each, drawn to docs/game-art.md. All face right; enemies are mirrored in battle.
from kit import *
from promos import knight, bandit
E = '#1a1420'
GOB = {'G': '#6a9a4a', 'g': '#4a7a34', 'Y': '#e8d04a', 'e': E, 'n': '#2a1e1a', 'b': '#7a5a3a', 'B': '#5a4028', 'L': '#4a3a2a',
       'k': '#2a2028', 'w': '#dfe6ee', 'h': '#5a3a24'}

def goblin_body(g, tunic='b', belt='B'):
    g.rect(12, 26, 13, 28, 'L'); g.rect(16, 26, 17, 28, 'L'); g.rect(11, 29, 13, 30, 'k'); g.rect(16, 29, 18, 30, 'k')
    g.rows(11, 17, [(1, 6), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (-1, 8), (-1, 8), (-1, 8)], tunic)
    g.rect(11, 22, 18, 22, belt)
    g.rect(9, 18, 10, 22, 'G'); g.rect(8, 22, 10, 23, 'G')      # left arm
    g.rect(19, 18, 20, 21, 'G'); g.rect(20, 21, 22, 22, 'G')    # right arm, hand forward
def goblin_head(g, y=8):
    g.rect(11, y, 18, y + 7, 'G'); g.rect(12, y - 1, 17, y - 1, 'G')
    g.tri([(5, y + 1), (11.5, y + 2.5), (11.5, y + 5)], 'G'); g.tri([(24, y + 1), (17.5, y + 2.5), (17.5, y + 5)], 'G')
    g.rect(13, y + 3, 14, y + 3, 'Y'); g.rect(16, y + 3, 17, y + 3, 'Y'); g.px(14, y + 3, 'e'); g.px(17, y + 3, 'e')
    g.px(18, y + 4, 'g'); g.rect(14, y + 6, 17, y + 6, 'n'); g.px(15, y + 7, 'w')

def decoy():  # scarecrow: a straw man on a post, sack head, patched coat
    g = G({'w': '#8a6a3e', 'W': '#6a4a2a', 's': '#d8c088', 'S': '#b89a5a', 'c': '#7a3a3a', 'p': '#3a5a7a', 'H': '#4a3a2a', 'e': E, 'o': E})
    g.rect(15, 14, 16, 30, 'w'); g.rect(4, 15, 27, 16, 'W')
    g.rows(9, 14, [(1, 13), (0, 14), (0, 14), (1, 13), (1, 13), (1, 13), (2, 12), (2, 12), (3, 11)], 'c'); g.rect(12, 18, 14, 20, 'p')
    g.text(3, 16, ['ss', 'sss', ' s']); g.text(26, 16, [' ss', 'sss', 's'])
    g.ell(15.5, 9, 4.5, 4.5, 's'); g.px(14, 9, 'o'); g.px(17, 9, 'o'); g.rect(14, 11, 17, 11, 'o')
    g.rows(9, 3, [(3, 10), (2, 11), (0, 13)], 'H'); g.rect(13, 1, 18, 2, 'H')
    return g
def slime():
    g = G({'G': '#6aaa4a', 'g': '#4a8a34', 'h': '#a8d888', 'e': E, 'o': E})
    g.ell(15.5, 23, 10.5, 7.5, 'G'); g.rect(6, 25, 25, 29, 'G'); g.ell(15.5, 29, 10, 1.5, 'g')
    g.rect(10, 19, 12, 20, 'h'); g.px(9, 21, 'h')
    g.rect(17, 21, 18, 23, 'e'); g.rect(22, 21, 23, 23, 'e'); g.rect(19, 26, 21, 26, 'o')
    return g
def bloat():
    g = G({'G': '#7ab84e', 'g': '#4f8a34', 'h': '#c0e8a0', 'e': E, 'o': E, 'b': '#a8d888'})
    g.ell(15.5, 19, 13, 11, 'G'); g.ell(15.5, 28, 13, 2.5, 'g')
    g.rect(8, 12, 10, 14, 'h'); g.px(7, 15, 'h'); g.ell(9, 23, 1.5, 1.5, 'b'); g.ell(12, 26, 1, 1, 'b'); g.ell(25, 14, 1.2, 1.2, 'b')
    g.rect(17, 16, 18, 19, 'e'); g.rect(23, 16, 24, 19, 'e'); g.rows(18, 22, [(1, 4), (0, 5), (1, 4)], 'o')
    return g
def goblin():
    g = G(GOB); goblin_body(g); goblin_head(g)
    g.line(22, 20, 25, 15, 'w'); g.line(23, 21, 26, 16, 'w')
    return g
def archer():  # goblin in a red hood with a short bow
    g = G({**GOB, 'R': '#9a3a2e', 'r': '#7a2a20'}); goblin_body(g, 'r'); goblin_head(g)
    g.rows(10, 5, [(2, 7), (1, 8), (0, 9), (0, 1), (0, 1), (0, 1)], 'R'); g.rect(11, 5, 18, 6, 'R')
    g.text(21, 12, [' hh ', 'h  w', 'h  w', 'h  w', 'h  w', 'h  w', 'h  w', 'h  w', ' hh ']); g.rect(20, 18, 22, 19, 'G')
    return g
def sapper():  # goblin with a leather cap and a lit bomb
    g = G({**GOB, 'c': '#6a4a2a', 'm': '#3a3a46', 'M': '#5a5a6a', 'f': '#ff9a3a', 'F': '#ffe680'}); goblin_body(g); goblin_head(g)
    g.rect(11, 6, 18, 8, 'c'); g.rect(12, 5, 17, 5, 'c')
    g.ell(23.5, 18.5, 3.2, 3.2, 'm'); g.px(22, 17, 'M'); g.px(24, 14, 'k'); g.px(25, 13, 'f'); g.px(26, 12, 'F')
    return g
def shaman():  # goblin in a mossy robe with a feather headdress and a bone staff
    g = G({**GOB, 'R': '#3e6a4a', 'r': '#2a5034', 'F': '#c84a3a', 'f': '#e8d04a', 'W': '#d8d0c0', 'c': '#9cf07a'})
    g.rect(11, 29, 13, 30, 'k'); g.rect(16, 29, 18, 30, 'k')
    g.rows(11, 16, [(1, 6), (0, 7), (0, 7), (0, 7), (-1, 8), (-1, 8), (-1, 8), (-2, 9), (-2, 9), (-2, 9), (-2, 9), (-3, 10), (-3, 10)], 'R'); g.rect(14, 18, 15, 28, 'r')
    g.rect(9, 18, 10, 22, 'R'); g.rect(8, 22, 10, 23, 'G'); goblin_head(g)
    g.text(11, 2, ['F f F f', ' FfFfF ']); g.rect(11, 6, 18, 7, 'r')
    g.rect(22, 6, 22, 30, 'W'); g.ell(22.5, 5, 2, 2, 'c'); g.rect(19, 18, 21, 20, 'R'); g.rect(21, 19, 23, 20, 'G')
    return g
def wolf():
    g = G({'G': '#8a8c98', 'g': '#5e606c', 'w': '#c8cad4', 'Y': '#e8c040', 'e': E, 'n': '#2a2430'})
    g.rect(6, 15, 21, 22, 'G'); g.rect(8, 22, 20, 23, 'w')                          # body
    g.rect(7, 23, 9, 29, 'g'); g.rect(11, 23, 13, 29, 'G'); g.rect(16, 23, 18, 29, 'g'); g.rect(19, 23, 21, 29, 'G')  # legs
    g.rows(1, 13, [(4, 5), (2, 5), (1, 5), (0, 4), (0, 3)], 'g')                     # tail
    g.rows(19, 10, [(1, 2), (0, 7), (0, 9), (0, 10), (0, 10), (0, 8), (1, 6), (1, 4)], 'G')  # head
    g.text(20, 7, ['g  g', 'gg gg']); g.rect(27, 13, 29, 14, 'n'); g.px(24, 12, 'Y'); g.px(25, 12, 'e'); g.rect(23, 16, 27, 16, 'w')
    return g
def bat():
    g = G({'B': '#4a3a5a', 'b': '#33284a', 'w': '#6a5a7a', 'R': '#e04848', 'e': E, 'f': '#d8d0c0'})
    g.ell(15.5, 17, 4, 5, 'B'); g.text(12, 10, ['B      B', 'BB    BB'])
    g.tri([(13, 14), (1, 9), (4, 22)], 'w'); g.tri([(18, 14), (30, 9), (27, 22)], 'w')
    g.line(2, 10, 12, 15, 'b'); g.line(29, 10, 19, 15, 'b'); g.px(14, 16, 'R'); g.px(17, 16, 'R'); g.px(14, 20, 'f'); g.px(17, 20, 'f')
    return g
def golem():  # stacked stone with a mossy cap and glowing eyes
    g = G({'S': '#8a8e98', 's': '#62666f', 'C': '#5ff4ff', 'm': '#5a8a3e', 'e': E})
    g.rect(9, 28, 13, 30, 's'); g.rect(18, 28, 22, 30, 's'); g.rect(10, 23, 13, 27, 'S'); g.rect(18, 23, 21, 27, 'S')
    g.rect(7, 13, 24, 23, 'S'); g.rect(8, 17, 23, 17, 's'); g.rect(15, 13, 16, 22, 's')
    g.rect(2, 13, 6, 22, 'S'); g.rect(25, 13, 29, 22, 'S'); g.rect(2, 23, 7, 26, 's'); g.rect(24, 23, 29, 26, 's')
    g.rect(11, 5, 21, 12, 'S'); g.rect(11, 5, 21, 6, 'm'); g.rect(13, 8, 14, 9, 'C'); g.rect(18, 8, 19, 9, 'C'); g.text(7, 12, ['mm', ' m'])
    return g
def ogre():  # big tan brute with a club and a loincloth
    g = G({'s': '#c8a07a', 'S': '#9a7a58', 'b': '#6a4a2e', 'B': '#4a3220', 'w': '#7a5a3a', 'k': '#2a2028', 'e': E, 'n': '#3a2420', 't': '#e8e0c8'})
    g.rect(8, 25, 12, 28, 's'); g.rect(17, 25, 21, 28, 's'); g.rect(7, 29, 12, 30, 'k'); g.rect(17, 29, 22, 30, 'k')
    g.ell(15, 18, 10, 8, 's'); g.rect(6, 21, 24, 25, 'b'); g.rect(6, 21, 24, 21, 'B')
    g.rect(2, 13, 6, 23, 's'); g.rect(2, 23, 6, 25, 'S')
    g.rect(23, 13, 26, 20, 's'); g.rect(24, 20, 27, 22, 'S'); g.line(26, 21, 29, 4, 'w', 2); g.ell(28.5, 4, 2.5, 3, 'w')
    g.rect(10, 4, 19, 11, 's'); g.rect(10, 4, 19, 5, 'S'); g.px(13, 7, 'e'); g.px(17, 7, 'e'); g.rect(12, 10, 18, 10, 'n'); g.px(12, 9, 't'); g.px(18, 9, 't')
    return g
def treant():  # the Thornmother: a walking tree with a face in the bark, roots for feet
    g = G({'b': '#6a4a30', 'B': '#4a3220', 'L': '#3e7a3a', 'l': '#2a5a2a', 'Y': '#ffd23f', 'f': '#c83a5a', 'e': E})
    g.rect(9, 12, 22, 27, 'b'); g.rect(13, 12, 14, 27, 'B'); g.rect(19, 14, 20, 26, 'B')
    g.rows(6, 27, [(0, 6), (-2, 2), (-3, 1)], 'b'); g.rows(18, 27, [(0, 6), (5, 9), (7, 11)], 'b')
    g.line(9, 15, 3, 9, 'b', 2); g.line(22, 15, 28, 9, 'b', 2); g.line(4, 9, 2, 6, 'B'); g.line(27, 9, 29, 6, 'B')
    g.ell(15.5, 7, 11, 6, 'L'); g.ell(10, 6, 5, 4, 'l'); g.ell(22, 5, 5, 4, 'L')
    g.rect(12, 16, 13, 17, 'Y'); g.rect(18, 16, 19, 17, 'Y'); g.rect(13, 21, 18, 22, 'B')
    for x, y in ((6, 4), (20, 2), (25, 7), (13, 3)): g.px(x, y, 'f')
    return g
def boar():
    g = G({'B': '#8a5a3a', 'b': '#5a3a26', 'h': '#3a2418', 't': '#f0e6d0', 'p': '#c87a6a', 'Y': '#e8c040', 'e': E})
    g.ell(13, 19, 10, 6, 'B'); g.rows(3, 12, [(6, 14), (4, 15), (3, 16)], 'h')
    g.rect(5, 23, 7, 29, 'b'); g.rect(9, 23, 11, 29, 'B'); g.rect(15, 23, 17, 29, 'b'); g.rect(19, 22, 21, 29, 'B')
    g.rows(19, 13, [(0, 5), (0, 7), (0, 9), (0, 10), (0, 10), (0, 9), (1, 7)], 'B'); g.rect(28, 16, 30, 18, 'p'); g.px(29, 16, 'e')
    g.px(24, 15, 'Y'); g.px(25, 15, 'e'); g.text(26, 18, ['t ', 'tt', ' t']); g.text(20, 11, ['bb', ' b'])
    return g
def totem():  # carved war totem: two stacked faces, painted, feathers
    g = G({'W': '#8a5a32', 'w': '#6a4224', 'R': '#a83a2a', 'Y': '#e8c040', 'F': '#e8e0d0', 'f': '#c84a3a', 'e': E, 'o': E, 'k': '#3a2a1e'})
    g.rect(10, 4, 21, 28, 'W'); g.rect(8, 28, 23, 30, 'k')
    g.rect(10, 4, 21, 13, 'R'); g.rect(12, 7, 13, 8, 'Y'); g.rect(18, 7, 19, 8, 'Y'); g.rect(12, 11, 19, 12, 'o')
    g.rect(12, 17, 13, 18, 'Y'); g.rect(18, 17, 19, 18, 'Y'); g.rect(13, 21, 18, 23, 'w'); g.rect(10, 15, 21, 15, 'w'); g.rect(10, 25, 21, 25, 'w')
    g.text(5, 3, ['F  ', 'FF ', ' Ff', '  F']); g.text(23, 3, ['  F', ' FF', 'fF ', 'F  '])
    g.rect(6, 15, 9, 16, 'w'); g.rect(22, 15, 25, 16, 'w')
    return g
def cutpurse():  # a hooded thief with a bulging coin sack
    g = bandit({'R': '#5a4a6a', 'r': '#3a2e48', 'C': '#4a3a5a', 'V': '#4a3a2a', 'v': '#33281c', 'o': '#8a7a6a'}, dagger=False, mask=True)
    g.ell(13.5, 6.5, 6, 5.5, 'R'); g.rect(8, 7, 19, 12, 'R'); g.rect(10, 8, 17, 9, 's'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(10, 10, 17, 12, 'r')
    g.ell(23, 21, 3.5, 3.5, 'q'); g.rect(22, 16, 24, 17, 'q'); g.px(22, 21, 'Y'); g.px(24, 22, 'Y'); g.pal['q'] = '#a8885a'
    return g

GREENWOOD = ['decoy', 'slime', 'bloat', 'goblin', 'archer', 'sapper', 'shaman', 'wolf', 'bat', 'golem', 'ogre', 'treant', 'boar', 'totem', 'cutpurse']

# ---------- Crypt and Rime Halls ----------
BONE = {'W': '#d8d0c0', 'w': '#b0a890', 'e': E, 'o': E, 'x': '#a8b0bc', 'X': '#dfe6ee', 'h': '#5a3a24', 'r': '#6a2a2a', 'k': '#2a2430'}
def skel_body(g, eyes='e'):
    g.rect(12, 24, 13, 29, 'W'); g.rect(16, 24, 17, 29, 'W'); g.rect(11, 30, 13, 30, 'W'); g.rect(16, 30, 18, 30, 'W')
    g.rect(12, 22, 17, 23, 'W')                                 # pelvis
    g.rect(14, 14, 15, 21, 'W')                                 # spine
    for y in (15, 17, 19): g.rect(11, y, 18, y, 'W')            # ribs
    g.rect(9, 14, 20, 14, 'W')                                  # shoulders
    g.rect(9, 15, 9, 21, 'W'); g.rect(8, 21, 9, 22, 'W')        # left arm
    g.rect(20, 15, 20, 19, 'W'); g.rect(20, 19, 22, 20, 'W')    # right arm forward
    g.ell(14.5, 8.5, 5, 5, 'W'); g.rect(12, 11, 17, 13, 'W')    # skull and jaw
    g.rect(11, 8, 12, 9, eyes); g.rect(16, 8, 17, 9, eyes); g.px(14, 10, 'o'); g.rect(12, 12, 17, 12, 'o')
def skeleton():
    g = G({**BONE}); skel_body(g)
    g.line(22, 19, 26, 9, 'X', 2); g.rect(21, 18, 24, 18, 'x')
    return g
def skeleton_ally():  # risen for the heroes: blue-lit eyes, a blue sash
    g = G({**BONE, 'c': '#7fe3ff', 'b': '#3a5aa8'}); skel_body(g, 'c')
    g.line(11, 14, 18, 21, 'b'); g.line(22, 19, 26, 9, 'X', 2); g.rect(21, 18, 24, 18, 'x')
    return g
def bulwark():  # skeleton behind a battered tower shield
    g = G({**BONE, 'S': '#5a5a6e', 's': '#76768a', 'Y': '#c8a040'}); skel_body(g)
    g.rect(3, 13, 12, 28, 'S'); g.rect(4, 14, 11, 27, 's'); g.rect(3, 13, 12, 13, 'Y'); g.rect(3, 28, 12, 28, 'Y'); g.rect(7, 16, 8, 25, 'Y')
    g.line(22, 19, 26, 9, 'X', 2); g.rect(21, 18, 24, 18, 'x')
    return g
def cultist():  # hooded red robe, hands crackling with a hex
    g = G({'R': '#8a2a2a', 'r': '#5a1a1e', 'n': '#1a1014', 'Y': '#c8a040', 'm': '#e070c0', 'M': '#ffb0e8', 's': '#c8a08a', 'k': '#2a2028', 'e': '#ff6a6a'})
    g.rows(10, 13, [(1, 9), (0, 10), (0, 10), (-1, 11), (-1, 11), (-1, 11), (-2, 12), (-2, 12), (-2, 12), (-3, 13), (-3, 13), (-3, 13), (-3, 13), (-4, 14), (-4, 14), (-4, 14), (-4, 14)], 'R')
    g.rect(14, 15, 15, 29, 'r'); g.rect(8, 21, 21, 21, 'Y')
    g.ell(14.5, 8, 5.5, 6, 'R'); g.rect(10, 7, 19, 13, 'R'); g.rect(11, 8, 18, 13, 'n'); g.px(13, 10, 'e'); g.px(16, 10, 'e')
    g.rect(20, 17, 22, 18, 's'); g.ell(23.5, 15.5, 2.2, 2.2, 'm'); g.px(23, 15, 'M'); g.rect(7, 19, 9, 20, 's')
    return g
def ghost():
    g = G({'W': '#cfe2f6', 'w': '#9ab8dc', 'e': E, 'o': E})
    g.ell(15.5, 12, 8, 8, 'W'); g.rect(8, 12, 23, 24, 'W'); g.text(8, 25, ['WW WW WW WW ', 'W  W  W  W  '][:2])
    g.rect(13, 10, 14, 12, 'e'); g.rect(18, 10, 19, 12, 'e'); g.rows(14, 15, [(1, 3), (0, 4), (1, 3)], 'o')
    g.rect(23, 15, 26, 17, 'W'); g.rect(5, 16, 7, 18, 'W')
    return g
def shade():  # a ghost of mirror-silver whose face is a looking glass
    g = G({'W': '#e0e0ea', 'w': '#a8a8bc', 'q': '#8ab8d8', 'Q': '#d8f0ff', 'Y': '#c8a040', 'e': E})
    g.ell(15.5, 12, 8, 8, 'W'); g.rect(8, 12, 23, 24, 'W'); g.text(8, 25, ['WW WW WW WW ', 'W  W  W  W  '])
    g.ell(16, 12, 4.5, 5, 'Y'); g.ell(16, 12, 3.4, 3.9, 'q'); g.rect(14, 10, 15, 11, 'Q'); g.px(17, 14, 'Q')
    g.rect(23, 15, 26, 17, 'W'); g.rect(5, 16, 7, 18, 'W')
    return g
def spider():
    g = G({'P': '#4a3a5a', 'p': '#33284a', 'R': '#ff4d4d', 'e': E, 'f': '#d8d0c0'})
    for sx, sy, ex, ey in ((12, 19, 3, 14), (12, 21, 2, 22), (13, 23, 4, 29), (14, 24, 8, 30), (19, 19, 28, 14), (19, 21, 29, 22), (18, 23, 27, 29), (17, 24, 23, 30)):
        mx, my = (sx + ex) // 2, min(sy, ey) - 2
        g.line(sx, sy, mx, my, 'p'); g.line(mx, my, ex, ey, 'p')
    g.ell(10, 20, 5.5, 5, 'P'); g.ell(19, 21, 4, 3.5, 'P'); g.px(21, 20, 'R'); g.px(23, 20, 'R'); g.px(22, 22, 'R'); g.px(22, 24, 'f'); g.px(24, 24, 'f')
    g.rect(8, 18, 11, 18, 'p')
    return g
def broodmother():  # a bloated spider queen, red hourglass on her back, eggs clinging
    g = spider(); g.pal.update({'P': '#5a2a3a', 'p': '#3a1a26', 'Y': '#ffd23f', 'v': '#e8e0c8'})
    g.ell(9, 18, 7, 6.5, 'P'); g.text(8, 15, ['YYY', ' Y ', 'YYY']); g.ell(4, 23, 1.5, 1.5, 'v'); g.ell(7, 25, 1.4, 1.4, 'v'); g.ell(12, 25, 1.3, 1.3, 'v')
    return g
def knight_dark():  # the Dark Knight: horned black plate, red eyes in the visor, a heavy blade
    g = knight({'A': '#3e3650', 'a': '#272033', 'T': '#7a1f2b', 'Y': '#b13a3a', 'S': '#2b2b35', 's': '#3e3e4a', 'n': '#ff4040', 'w': '#c7c7d1'}, plume=False)
    g.text(7, 1, ['A          ', 'AA        A', ' AA      AA', '         AA ']); g.rect(10, 8, 18, 8, 'z'); g.px(12, 8, 'n'); g.px(16, 8, 'n'); g.pal['z'] = '#120c16'
    g.rect(6, 15, 6, 22, 'Y'); g.rect(3, 17, 9, 17, 'Y')
    return g
def lich():  # the Hollow King: crowned skull, tattered violet robes, a staff with a green soul-light
    g = G({'R': '#3a2a5a', 'r': '#261a40', 'W': '#d8d0c0', 'Y': '#d0a840', 'e': E, 'g': '#7dff8a', 'G': '#c8ffd0', 'w': '#4a3a3a', 'o': E})
    g.rows(9, 13, [(0, 10), (-1, 11), (-1, 11), (-1, 11), (-2, 12), (-2, 12), (-2, 12), (-3, 13), (-3, 13), (-3, 13), (-4, 14), (-4, 14), (-4, 14), (-4, 14), (-5, 15), (-5, 15)], 'R')
    g.text(4, 29, ['R R R R R R R R R R']); g.rect(14, 14, 15, 28, 'r'); g.rect(11, 14, 18, 15, 'Y'); g.px(14, 22, 'Y'); g.px(15, 22, 'Y')
    g.ell(14.5, 8.5, 4.5, 4.5, 'W'); g.rect(12, 11, 17, 13, 'W'); g.rect(12, 8, 13, 9, 'e'); g.rect(16, 8, 17, 9, 'e'); g.px(12, 8, 'g'); g.px(16, 8, 'g'); g.rect(13, 12, 16, 12, 'o')
    g.text(10, 1, ['Y Y Y Y', 'YYYYYYY', 'YYYYYYY']); g.px(13, 1, 'g')
    g.rect(23, 6, 23, 30, 'w'); g.ell(23.5, 4, 2.5, 2.5, 'g'); g.px(23, 3, 'G'); g.rect(20, 17, 24, 18, 'W'); g.rect(6, 18, 8, 19, 'W')
    return g
def wight():  # a barrow wight: crowned skull, cloak, rusted blade, cold blue eyes
    g = G({**BONE, 'C': '#3a4a5a', 'c': '#26323e', 'B': '#7fe3ff', 'Y': '#a88a40'})
    g.rows(10, 13, [(0, 9), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 11), (-3, 12), (-3, 12), (-3, 12), (-3, 12), (-3, 12), (-4, 13), (-4, 13)], 'C')
    g.rect(14, 15, 15, 27, 'c'); g.rect(11, 28, 13, 30, 'W'); g.rect(16, 28, 18, 30, 'W')
    g.ell(14.5, 8.5, 4.5, 4.5, 'W'); g.rect(12, 11, 17, 13, 'W'); g.rect(12, 8, 13, 9, 'e'); g.rect(16, 8, 17, 9, 'e'); g.px(13, 9, 'B'); g.px(17, 9, 'B'); g.rect(13, 12, 16, 12, 'o')
    g.text(10, 2, ['Y Y Y', 'YYYYY']); g.rect(10, 4, 19, 4, 'C')
    g.rect(21, 17, 23, 18, 'W'); g.line(23, 16, 27, 6, 'x', 2); g.rect(20, 17, 25, 17, 'Y'); g.rect(6, 19, 8, 20, 'W')
    return g
def icewight():
    g = wight(); g.pal.update({'C': '#5a7a9a', 'c': '#3a5a7a', 'B': '#c9f7ff', 'x': '#b8e0f8', 'W': '#e0eaf4'})
    for x, y in ((8, 28), (12, 27), (20, 28)): g.px(x, y, 'B')
    return g
def frostarcher():  # a hooded archer in white furs with a pale bow
    g = G({'F': '#e0e8f0', 'f': '#a8b8cc', 'b': '#3a5a8a', 'B': '#5a7ab0', 's': '#e0b48a', 'S': '#a8785a', 'e': E, 'w': '#c8d8e8', 'h': '#6a5a4a', 'k': '#2a2a3a', 'q': '#7fe3ff'})
    g.rect(11, 25, 13, 28, 'b'); g.rect(16, 25, 18, 28, 'b'); g.rect(10, 29, 13, 30, 'k'); g.rect(16, 29, 19, 30, 'k')
    g.rows(10, 14, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9)], 'B'); g.rect(10, 21, 19, 22, 'F'); g.rect(10, 14, 19, 15, 'F')
    g.ell(14.5, 8, 6, 6, 'F'); g.rect(9, 8, 20, 13, 'F'); g.rect(11, 8, 18, 13, 's'); g.rect(11, 8, 18, 8, 'S'); g.px(13, 10, 'e'); g.px(16, 10, 'e'); g.rect(9, 7, 20, 7, 'f')
    g.rect(7, 15, 9, 20, 'B'); g.rect(6, 20, 8, 21, 's')
    g.text(21, 9, [' ww ', 'w  q', 'w  q', 'w  q', 'w  q', 'w  q', 'w  q', 'w  q', 'w  q', ' ww ']); g.rect(20, 16, 22, 17, 's')
    return g
def snowwolf():
    g = wolf(); g.pal.update({'G': '#e8eef4', 'g': '#a8b4c4', 'w': '#ffffff', 'Y': '#7fe3ff'})
    return g
def yeti():
    g = G({'W': '#e8eef4', 'w': '#b8c4d4', 'B': '#5a7aa8', 'b': '#3a5a88', 'e': E, 'o': E, 't': '#ffffff'})
    g.rect(8, 26, 12, 30, 'W'); g.rect(18, 26, 22, 30, 'W'); g.rect(7, 29, 12, 30, 'B'); g.rect(18, 29, 23, 30, 'B')
    g.ell(15, 18, 10, 9, 'W'); g.ell(15, 21, 6, 5, 'w')
    g.rect(2, 12, 6, 24, 'W'); g.rect(1, 24, 6, 27, 'B'); g.rect(24, 12, 28, 24, 'W'); g.rect(24, 24, 29, 27, 'B')
    g.ell(15, 7, 6, 5.5, 'W'); g.rect(11, 6, 19, 11, 'B'); g.px(13, 7, 'e'); g.px(17, 7, 'e'); g.rect(13, 10, 17, 10, 'o'); g.px(13, 11, 't'); g.px(17, 11, 't')
    return g
def icegolem():
    g = golem(); g.pal.update({'S': '#a8d8f0', 's': '#6aa8d0', 'C': '#ffffff', 'm': '#e8f8ff'})
    g.text(2, 9, ['  C ', ' CC ', 'CCC ']); g.text(26, 9, [' C  ', ' CC ', ' CCC'])
    return g
def frostqueen():  # tall and regal: ice crown, pale skin, gown of frost, a staff of ice
    g = G({'W': '#e8f4ff', 'B': '#7fb8e0', 'b': '#3a6a9a', 'S': '#f0e4ec', 's': '#c8b4c4', 'Y': '#c9f7ff', 'h': '#d8e8f8', 'e': E, 'q': '#3a7ab0', 'o': E})
    g.rows(8, 14, [(2, 11), (1, 12), (1, 12), (0, 13), (0, 13), (-1, 14), (-1, 14), (-2, 15), (-2, 15), (-3, 16), (-3, 16), (-4, 17), (-4, 17), (-5, 18), (-5, 18), (-6, 19), (-6, 19)], 'B')
    g.tri([(15, 14), (9, 30), (21, 30)], 'W'); g.rect(10, 14, 19, 15, 'W')
    g.ell(14.5, 8.5, 4.5, 5, 'S'); g.rect(10, 4, 19, 13, 'h'); g.rect(11, 6, 18, 12, 'S'); g.rect(11, 6, 18, 6, 's'); g.px(13, 9, 'e'); g.px(16, 9, 'e'); g.rect(14, 11, 15, 11, 's')
    g.text(10, 0, ['Y  Y  Y   ', 'YY YY YY  ', 'YYYYYYYYYY', ' YYYYYYYY ']); g.pal['Y'] = '#c9f7ff'
    g.rect(24, 6, 24, 30, 'Y'); g.text(22, 1, ['  Y  ', ' YYY ', 'Y Y Y', ' YYY ', '  Y  ']); g.rect(20, 17, 24, 18, 'S'); g.rect(5, 19, 7, 20, 'S')
    return g

CRYPT_RIME = ['skeleton', 'skeleton_ally', 'bulwark', 'cultist', 'ghost', 'shade', 'spider', 'broodmother', 'knight_dark', 'lich', 'wight',
              'icewight', 'frostarcher', 'snowwolf', 'yeti', 'icegolem', 'frostqueen']

# ---------- Ember Peaks, Drowned Marsh, Foundry ----------
FIRE = {'f': '#ff7a1a', 'F': '#ffd23f'}
def imp():
    g = G({'R': '#c84a2a', 'r': '#8a2a1a', 'w': '#7a2a2a', 'Y': '#ffd23f', 'e': E, 'h': '#e8d0a0', **FIRE})
    g.tri([(12, 13), (2, 6), (5, 19)], 'w'); g.tri([(19, 13), (29, 6), (26, 19)], 'w')
    g.rect(12, 21, 13, 26, 'r'); g.rect(17, 21, 18, 26, 'r'); g.ell(15.5, 17, 5, 5, 'R'); g.ell(15.5, 11, 5, 4.5, 'R')
    g.text(10, 5, ['h      h', 'hh    hh']); g.px(13, 10, 'Y'); g.px(17, 10, 'Y'); g.rect(14, 13, 17, 13, 'r')
    g.line(19, 22, 24, 25, 'r'); g.px(25, 25, 'r'); g.rect(20, 15, 22, 16, 'R'); g.ell(24, 13.5, 2, 2, 'f'); g.px(24, 13, 'F')
    return g
def salamander():  # a low fire lizard with a burning tail
    g = G({'R': '#c8401a', 'r': '#8a2a12', 'y': '#e8a040', 'Y': '#ffd23f', 'e': E, **FIRE})
    g.rows(6, 18, [(0, 14), (-1, 15), (-1, 15), (0, 14)], 'R'); g.rect(6, 21, 20, 21, 'y')
    g.rows(1, 16, [(3, 5), (1, 5), (0, 4)], 'r'); g.text(0, 12, [' F ', 'fFf', ' f '])
    g.rect(7, 22, 8, 25, 'r'); g.rect(11, 22, 12, 24, 'R'); g.rect(16, 22, 17, 25, 'r'); g.rect(19, 22, 20, 24, 'R')
    g.rows(20, 16, [(0, 6), (0, 9), (0, 9), (0, 7)], 'R'); g.px(25, 17, 'Y'); g.px(26, 17, 'e'); g.rect(26, 19, 29, 19, 'r')
    for x in (9, 13, 17): g.px(x, 17, 'y')
    return g
def orc():  # grey-green brute with tusks and a cleaver
    g = G({'G': '#6a7a4a', 'g': '#4a5a34', 'b': '#5a4a3a', 'B': '#3a3028', 'A': '#8a909c', 'a': '#5a606c', 't': '#e8e0c8', 'e': E, 'n': '#2a1e1a', 'k': '#2a2028', 'r': '#a83030'})
    g.rect(10, 25, 13, 28, 'b'); g.rect(17, 25, 20, 28, 'b'); g.rect(9, 29, 13, 30, 'k'); g.rect(17, 29, 21, 30, 'k')
    g.rows(8, 13, [(1, 13), (0, 14), (0, 14), (0, 14), (0, 14), (1, 13), (1, 13), (1, 13), (1, 13), (1, 13), (1, 13), (1, 13)], 'b')
    g.rect(7, 13, 10, 15, 'A'); g.rect(20, 13, 23, 15, 'A'); g.rect(9, 21, 21, 22, 'B'); g.rect(14, 21, 15, 22, 'r')
    g.rect(5, 15, 7, 22, 'G'); g.rect(4, 22, 7, 24, 'G'); g.rect(22, 15, 24, 19, 'G'); g.rect(23, 19, 25, 21, 'G')
    g.rect(24, 9, 28, 14, 'A'); g.rect(25, 15, 25, 20, 'n'); g.rect(24, 9, 28, 9, 'a')
    g.rect(10, 4, 19, 11, 'G'); g.rect(10, 4, 19, 5, 'g'); g.px(12, 7, 'e'); g.px(17, 7, 'e'); g.rect(12, 10, 17, 10, 'n'); g.px(12, 9, 't'); g.px(17, 9, 't'); g.rect(11, 6, 18, 6, 'g')
    return g
def firecultist():  # the Ash Priest: grey robes, an ember mask, a staff of coals
    g = cultist(); g.pal.update({'R': '#5a5052', 'r': '#3a3234', 'n': '#2a1a14', 'Y': '#ff7a1a', 'm': '#ff7a1a', 'M': '#ffe680', 'e': '#ffd23f'})
    return g
def magmagolem():
    g = golem(); g.pal.update({'S': '#3a2e2e', 's': '#241c1c', 'C': '#ffd23f', 'm': '#ff7a1a'})
    for x0, y0, x1, y1 in ((9, 14, 12, 20), (20, 15, 17, 22), (3, 15, 5, 20), (27, 14, 26, 21), (12, 24, 11, 27)): g.line(x0, y0, x1, y1, 'm')
    return g
def wyrm():  # the Cinder Wyrm: a red dragon, wings up, glowing chest, curled tail
    g = G({'R': '#a8301e', 'r': '#741e12', 'w': '#5a1a14', 'y': '#e8a040', 'Y': '#ffd23f', 'h': '#e8d8b8', 'e': E, **FIRE})
    g.tri([(10, 12), (2, 1), (1, 17)], 'w'); g.tri([(16, 11), (14, 0), (4, 6)], 'w'); g.line(2, 1, 10, 12, 'r'); g.line(14, 0, 14, 11, 'r')
    g.ell(13, 20, 8, 7, 'R'); g.ell(14, 22, 4, 4, 'y'); g.ell(14, 22, 2, 2, 'f')
    g.rows(1, 21, [(4, 6), (2, 5), (0, 4), (0, 2), (1, 3)], 'r'); g.text(0, 26, ['RR '])
    g.rect(8, 26, 10, 30, 'r'); g.rect(15, 26, 17, 30, 'R'); g.rect(7, 30, 11, 30, 'h'); g.rect(14, 30, 18, 30, 'h')
    g.rows(18, 9, [(1, 4), (0, 5), (0, 5), (1, 5), (2, 5)], 'R')
    g.rows(19, 5, [(1, 7), (0, 10), (0, 11), (0, 11), (1, 9)], 'R'); g.text(19, 2, ['h  h', 'hh hh']); g.px(23, 6, 'Y'); g.px(24, 6, 'e'); g.rect(26, 8, 30, 8, 'r')
    g.text(28, 9, ['fF', 'Ff']); g.px(26, 5, 'r')
    return g
def kobold():  # a little red lizard sapper hauling a powder keg
    g = sapper(); g.pal.update({'G': '#c86a3a', 'g': '#8a4424', 'c': '#5a3a24'})
    g.rect(18, 12, 21, 13, 'G'); g.px(20, 12, 'g')  # snout
    return g
def lavaworm():
    g = G({'R': '#c8401a', 'r': '#8a2a12', 'Y': '#ffd23f', 'e': E, 'D': '#3a2a2a', 'd': '#5a4444', 'o': E, **FIRE})
    g.rows(2, 27, [(4, 24), (1, 27), (0, 28)], 'D'); g.rect(4, 27, 7, 27, 'd'); g.rect(20, 28, 24, 28, 'd'); g.px(8, 26, 'f'); g.px(23, 26, 'F')
    g.rect(12, 14, 19, 27, 'R')
    for y in (16, 19, 22, 25): g.rect(12, y, 19, y, 'r')
    g.ell(16, 10, 6, 5.5, 'R'); g.rect(14, 7, 15, 8, 'Y'); g.rect(19, 7, 20, 8, 'Y'); g.rows(14, 11, [(1, 6), (0, 7), (1, 6)], 'o'); g.px(16, 12, 'f'); g.px(19, 12, 'f')
    return g
def brazier():
    g = G({'S': '#6a6070', 's': '#4a4250', 'k': '#2a2430', 'e': E, **FIRE, 'r': '#c8401a'})
    g.rect(12, 14, 19, 27, 'S'); g.rect(12, 18, 19, 18, 's'); g.rect(12, 23, 19, 23, 's'); g.rect(9, 27, 22, 30, 's')
    g.rows(6, 10, [(0, 19), (1, 18), (2, 17), (4, 15)], 'S')
    g.text(8, 1, ['   f   F  f    ', '  fFf fFf fF   ', ' fFrFffFrFfFf  ', ' frrFrfFrrFrf  ', '  rrrrrrrrrrr  '][:5])
    g.px(14, 20, 'f'); g.px(17, 20, 'f')
    return g
def toad():
    g = G({'G': '#5a8a3a', 'g': '#3e6a2a', 'Y': '#e8c040', 'w': '#d8e0a0', 'p': '#c85a6a', 'e': E, 'o': E})
    g.ell(15.5, 21, 12, 8, 'G'); g.ell(15.5, 24, 8, 5, 'w')
    g.ell(10, 13, 3, 3, 'G'); g.ell(21, 13, 3, 3, 'G'); g.rect(9, 12, 11, 13, 'Y'); g.rect(20, 12, 22, 13, 'Y'); g.px(11, 13, 'e'); g.px(22, 13, 'e')
    g.rect(9, 18, 22, 18, 'o'); g.px(8, 17, 'o'); g.px(23, 17, 'o')
    g.rect(2, 26, 7, 29, 'g'); g.rect(24, 26, 29, 29, 'g')
    for x, y in ((8, 21), (21, 20), (14, 16), (19, 23)): g.px(x, y, 'g')
    return g
def leech():
    g = G({'L': '#6a3a4a', 'l': '#4a2430', 'R': '#e04848', 'e': E, 'o': E})
    g.rows(3, 19, [(14, 20), (9, 22), (5, 23), (2, 21), (0, 16), (1, 12), (3, 8)], 'L')
    for x in (9, 13, 17, 21): g.line(x, 20, x - 1, 24, 'l')
    g.ell(25, 20, 3.5, 3, 'L'); g.ell(26.5, 20.5, 1.8, 1.8, 'R'); g.rows(25, 19, [(1, 3), (0, 4), (1, 3)], 'o'); g.px(23, 18, 'e')
    return g
def lizard():  # lizardfolk spearman: teal scales, a frill, a long spear and a tail
    g = G({'G': '#3a8a7a', 'g': '#2a6a5e', 'y': '#d8c890', 'b': '#7a5a3a', 'B': '#5a4028', 'Y': '#ffd23f', 'e': E, 'w': '#c8c8d8', 'h': '#6a4a2e', 'k': '#24302c', 'r': '#c84a3a'})
    g.rect(11, 25, 13, 28, 'G'); g.rect(16, 25, 18, 28, 'G'); g.rect(10, 29, 13, 30, 'k'); g.rect(16, 29, 19, 30, 'k')
    g.rows(1, 23, [(8, 9), (5, 9), (2, 8), (0, 5)], 'g')
    g.rows(10, 14, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8), (1, 8), (1, 8), (1, 8), (1, 8)], 'G'); g.rect(13, 15, 16, 24, 'y'); g.rect(10, 21, 19, 22, 'b')
    g.rect(8, 15, 9, 21, 'G'); g.rect(7, 21, 9, 22, 'G')
    g.rect(23, 1, 23, 30, 'h'); g.text(22, 0, [' w ', 'www', ' w ']); g.rect(20, 16, 24, 17, 'G')
    g.rect(12, 6, 19, 13, 'G'); g.rect(19, 9, 24, 12, 'G'); g.rect(19, 12, 24, 12, 'g'); g.px(17, 8, 'Y'); g.px(18, 8, 'e')
    g.text(9, 4, ['r r r', ' rrrr']); g.px(23, 10, 'e')
    return g
def wisp():
    g = G({'B': '#7fe3ff', 'b': '#3ab0d0', 'w': '#e8ffff', 'e': E, 'q': '#1e6a8a'})
    g.tri([(15.5, 2), (9, 16), (22, 16)], 'b'); g.ell(15.5, 17, 7, 7, 'B'); g.ell(15.5, 17, 4, 4.5, 'w')
    g.px(13, 17, 'e'); g.px(18, 17, 'e'); g.text(10, 24, ['b b  b', ' b  b ']); g.px(12, 28, 'b'); g.px(19, 27, 'b')
    return g
def croc():
    g = G({'G': '#4a6a3a', 'g': '#2e4a24', 'y': '#a8a870', 'Y': '#f2c94c', 'w': '#e8e0c0', 'e': E, 'o': E})
    g.rows(1, 18, [(6, 20), (3, 21), (1, 22), (0, 22), (2, 20)], 'G'); g.rect(6, 22, 21, 22, 'y')
    g.rows(0, 20, [(0, 2), (0, 4)], 'g')
    for x in (6, 10, 14, 18): g.rect(x, 16, x + 1, 17, 'g')
    g.rect(5, 23, 7, 26, 'g'); g.rect(10, 23, 12, 26, 'G'); g.rect(16, 23, 18, 26, 'g'); g.rect(20, 23, 22, 26, 'G')
    g.rows(22, 17, [(0, 3), (0, 8), (0, 9), (0, 9), (0, 8)], 'G'); g.rect(22, 21, 31, 21, 'o'); g.text(24, 20, ['w w w ']); g.text(24, 22, [' w w w'])
    g.px(24, 18, 'Y'); g.px(25, 18, 'e')
    return g
def hydra():  # the Bog Hydra: three heads on long necks rising from a heavy body in the water
    g = G({'G': '#3a7a5a', 'g': '#245a40', 'Y': '#ffd23f', 'e': E, 'y': '#c8d0a0', 'b': '#2a4a4a', 'B': '#4a7a7a', 'o': E})
    g.ell(15.5, 24, 12, 6, 'G'); g.ell(15.5, 26, 7, 3, 'y'); g.rows(1, 28, [(0, 29), (2, 27)], 'b'); g.rect(4, 28, 8, 28, 'B'); g.rect(20, 29, 25, 29, 'B')
    for (nx, ny, hx, hy) in ((9, 20, 4, 6), (15, 19, 15, 3), (21, 20, 25, 7)):
        g.line(nx, ny, hx, hy + 3, 'G', 3)
        g.rect(hx - 2, hy, hx + 3, hy + 3, 'G'); g.rect(hx + 3, hy + 2, hx + 5, hy + 3, 'G'); g.px(hx + 1, hy + 1, 'Y'); g.px(hx + 2, hy + 1, 'e'); g.rect(hx + 3, hy + 3, hx + 5, hy + 3, 'o')
    return g
def hydrahead():  # a single head on a neck rising from the water
    g = G({'G': '#3a7a5a', 'g': '#245a40', 'Y': '#ffd23f', 'e': E, 'b': '#2a4a4a', 'B': '#4a7a7a', 'o': E, 'w': '#e8e0c0'})
    g.rows(4, 27, [(0, 23), (2, 21)], 'b'); g.rect(7, 27, 11, 27, 'B'); g.rect(18, 28, 22, 28, 'B')
    g.line(13, 27, 11, 12, 'G', 4); g.rows(8, 6, [(2, 7), (0, 10), (0, 12), (0, 12), (1, 11), (2, 8)], 'G'); g.rect(16, 10, 20, 10, 'o'); g.px(17, 11, 'w'); g.px(19, 11, 'w')
    g.px(13, 8, 'Y'); g.px(14, 8, 'e'); g.text(9, 4, ['g g', ' g '])
    return g
BRASS = {'Y': '#c8a040', 'y': '#8a6a28', 'C': '#7fe3ff', 'M': '#6a6a7a', 'm': '#4a4a58', 'e': E, 'o': E, 'k': '#2a2a34'}
def automaton():  # a brass soldier-machine with a cyan eye-slit and a riveted chest
    g = G({**BRASS, 'w': '#dfe6ee'})
    g.rect(11, 24, 13, 28, 'M'); g.rect(17, 24, 19, 28, 'M'); g.rect(10, 29, 14, 30, 'k'); g.rect(16, 29, 20, 30, 'k')
    g.rect(9, 13, 21, 23, 'Y'); g.rect(12, 16, 18, 20, 'y'); g.ell(15, 18, 1.6, 1.6, 'C'); g.px(10, 14, 'm'); g.px(20, 14, 'm'); g.px(10, 22, 'm'); g.px(20, 22, 'm')
    g.rect(5, 13, 8, 16, 'y'); g.rect(22, 13, 25, 16, 'y'); g.rect(6, 17, 7, 22, 'M'); g.rect(5, 22, 8, 24, 'Y'); g.rect(23, 17, 24, 19, 'M'); g.rect(23, 19, 25, 21, 'Y')
    g.line(25, 19, 28, 8, 'w', 2)
    g.rect(11, 4, 19, 11, 'Y'); g.rect(11, 4, 19, 5, 'y'); g.rect(12, 7, 18, 8, 'k'); g.rect(13, 7, 17, 7, 'C'); g.rect(14, 12, 16, 12, 'M'); g.rect(15, 1, 15, 3, 'M'); g.px(15, 0, 'C')
    return g
def turret():
    g = G({**BRASS})
    g.rect(8, 26, 23, 30, 'm'); g.rect(10, 24, 21, 25, 'M'); g.rect(13, 18, 18, 23, 'Y'); g.rect(13, 18, 18, 18, 'y')
    g.ell(15.5, 13, 7, 5.5, 'M'); g.rect(9, 13, 22, 16, 'M'); g.rect(20, 11, 29, 14, 'm'); g.rect(29, 10, 30, 15, 'C'); g.rect(11, 11, 14, 12, 'C'); g.rect(9, 16, 22, 16, 'm')
    return g
def sparkbot():
    g = G({**BRASS, 'Y': '#ffe14d'})
    g.ell(15.5, 20, 8, 7, 'M'); g.rect(8, 20, 23, 22, 'm'); g.rect(12, 17, 14, 19, 'C'); g.rect(18, 17, 20, 19, 'C'); g.rect(13, 23, 19, 23, 'k')
    g.rect(9, 26, 11, 29, 'm'); g.rect(20, 26, 22, 29, 'm'); g.rect(8, 29, 12, 30, 'k'); g.rect(19, 29, 23, 30, 'k')
    g.rect(15, 9, 16, 13, 'k'); g.ell(15.5, 7, 2, 2, 'Y'); g.px(12, 5, 'Y'); g.px(19, 4, 'Y'); g.px(20, 8, 'Y')
    return g
def tinker():  # a gnome engineer: goggles up, white beard, apron, a wrench
    g = G({'s': '#e0b48a', 'S': '#a8785a', 'W': '#e8e4dc', 'a': '#6a4a3a', 'b': '#3a5a8a', 'Y': '#c8a040', 'q': '#7fe3ff', 'M': '#8a8a9a', 'k': '#2a2028', 'e': E, 'r': '#a83a3a'})
    g.rect(12, 26, 13, 28, 'b'); g.rect(16, 26, 17, 28, 'b'); g.rect(11, 29, 13, 30, 'k'); g.rect(16, 29, 18, 30, 'k')
    g.rows(11, 17, [(1, 6), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7)], 'b'); g.rect(12, 18, 17, 25, 'a')
    g.rect(9, 18, 10, 23, 'b'); g.rect(8, 23, 10, 24, 's'); g.rect(19, 18, 20, 21, 'b'); g.rect(20, 21, 22, 22, 's')
    g.line(22, 20, 26, 14, 'M', 2); g.text(25, 11, ['M M', 'MMM'])
    g.rect(11, 8, 18, 15, 's'); g.rows(10, 12, [(1, 8), (0, 9), (1, 8), (2, 7), (3, 6), (4, 5)], 'W'); g.px(13, 11, 'e'); g.px(16, 11, 'e'); g.rect(14, 12, 15, 13, 'S')
    g.rows(10, 3, [(3, 6), (1, 8), (0, 9), (0, 9)], 'r'); g.rect(10, 7, 19, 8, 'Y'); g.ell(12.5, 7.5, 1.2, 1.2, 'q'); g.ell(16.5, 7.5, 1.2, 1.2, 'q')
    return g
def clocksoldier():  # the knight's build in brass, a cyan lens for a visor, a key in its back
    g = knight({'A': '#b8863a', 'a': '#7a5a20', 'T': '#4a4a58', 'Y': '#7fe3ff', 'S': '#5a5a6a', 's': '#7a7a8a', 'n': '#7fe3ff', 'P': '#7fe3ff'}, plume=False)
    g.text(5, 6, ['YYY', ' Y ', 'YYY']); g.rect(8, 7, 8, 7, 'a')
    return g
def steamjugg():  # a walking boiler: brass tank, smokestack, piston arms, a furnace glow
    g = G({**BRASS, 'f': '#ff7a1a', 'F': '#ffd23f', 'g': '#9a9aaa'})
    g.rect(8, 25, 12, 28, 'M'); g.rect(19, 25, 23, 28, 'M'); g.rect(6, 29, 13, 30, 'k'); g.rect(18, 29, 25, 30, 'k')
    g.ell(15.5, 17, 10, 9, 'Y')
    for y in (10, 15, 20): g.rect(6, y, 25, y, 'y')
    g.rect(12, 19, 19, 23, 'm'); g.rect(13, 20, 18, 22, 'f'); g.px(15, 21, 'F'); g.px(16, 20, 'F')
    g.rect(19, 2, 22, 9, 'M'); g.rect(18, 2, 23, 2, 'm'); g.text(18, 0, ['g g', ' g '])
    g.rect(1, 14, 5, 17, 'M'); g.rect(0, 18, 5, 22, 'm'); g.rect(26, 14, 30, 17, 'M'); g.rect(26, 18, 31, 22, 'm')
    g.rect(11, 9, 14, 11, 'k'); g.rect(12, 10, 13, 10, 'C')
    return g
def colossus():  # the Brass Colossus: a broad-shouldered machine giant with a burning core
    g = G({**BRASS, 'C': '#ff4a2a', 'c': '#ffb04a', 'w': '#dfe6ee'})
    g.rect(8, 24, 12, 28, 'M'); g.rect(19, 24, 23, 28, 'M'); g.rect(6, 29, 13, 30, 'k'); g.rect(18, 29, 25, 30, 'k')
    g.rows(5, 10, [(2, 19), (0, 21), (0, 21), (0, 21), (1, 20), (2, 19), (3, 18), (3, 18), (3, 18), (4, 17), (4, 17), (4, 17), (5, 16), (5, 16)], 'Y')
    g.ell(15.5, 16, 3.2, 3.2, 'C'); g.ell(15.5, 16, 1.6, 1.6, 'c'); g.rect(8, 21, 23, 21, 'y')
    for x, y in ((9, 12), (22, 12), (9, 19), (22, 19)): g.px(x, y, 'm')
    g.rect(0, 9, 5, 14, 'y'); g.rect(26, 9, 31, 14, 'y'); g.rect(1, 15, 4, 21, 'M'); g.rect(27, 15, 30, 21, 'M'); g.rect(0, 22, 5, 26, 'Y'); g.rect(26, 22, 31, 26, 'Y')
    g.rect(12, 3, 19, 9, 'Y'); g.rect(12, 3, 19, 4, 'y'); g.rect(13, 6, 18, 7, 'k'); g.rect(14, 6, 15, 6, 'C'); g.rect(17, 6, 18, 6, 'C')
    return g

EMBER_MARSH_FOUNDRY = ['imp', 'salamander', 'orc', 'firecultist', 'magmagolem', 'wyrm', 'kobold', 'lavaworm', 'brazier', 'toad', 'leech', 'lizard', 'wisp',
                       'croc', 'hydra', 'hydrahead', 'automaton', 'turret', 'sparkbot', 'tinker', 'clocksoldier', 'steamjugg', 'colossus']

# art.js key -> drawing function
KEYS = {n: n for n in GREENWOOD + CRYPT_RIME + EMBER_MARSH_FOUNDRY}
KEYS['knight'] = KEYS.pop('knight_dark')
