# Sprite options for the seven classes added in build step 2. Plain fantasy adventurers, like the
# first three: no sea theme on heroes.
from parts import *

def build(pal, b, hair=None, beard=None, hat_=None, wpn=None, off=None, bare=False):
    def fn():
        g = G({**pal, 'e': E})
        body(g, b)
        if off == 'quiver':
            offhand(g, 'quiver')
        if bare:
            arms_bare(g)
        else:
            arms(g)
        if hat_ in ('hood', 'antlers'):
            hat(g, hat_)
        else:
            head(g, hair or 'short', beard)
            if hat_:
                hat(g, hat_)
        if wpn:
            weapon(g, wpn)
        if off and off != 'quiver':
            offhand(g, off)
        return g
    return fn


# Emberknight alternatives (owner's request, Nov 2026): knights in orange-to-red plate.
EMBER = {'A': '#d8642a', 'a': '#a8401e', 'D': '#f08c3a', 'R': '#8a2418', 'r': '#5e1810', 'G': '#ffd36b', 'g': '#ffa030',
         'n': '#1e1210', 'k': '#2a1a18', 'h': '#4a3428', 'L': '#8a2418', 'W': '#ffb048', 'Y': '#e0b048'}

def plate(g, body='A', shade='a', belt='h'):
    legs(g, 'r')
    g.rect(10, 26, 12, 27, shade); g.rect(15, 26, 17, 27, shade)  # greaves
    torso(g, body)
    g.rect(12, 14, 15, 22, shade); g.rect(9, 20, 18, 20, belt); g.rect(13, 20, 14, 20, 'Y')
    g.rect(6, 12, 9, 15, 'D'); g.rect(18, 12, 21, 15, 'D')  # pauldrons
    g.rect(6, 16, 8, 19, shade); g.rect(19, 15, 21, 18, shade)  # arms

def ember_mace(g, y=2):
    g.rect(20, 15, 22, 18, 'a'); g.rect(22, y + 4, 23, 19, 'h'); g.rect(19, y, 26, y + 4, 'g'); g.rect(20, y + 1, 25, y + 3, 'G')
    g.px(18, y + 2, 'g'); g.px(27, y + 2, 'g'); g.px(22, y - 1, 'G')

def ember1():  # Ember Knight: great helm with a glowing visor slit, orange plate, glowing mace
    g = G(dict(EMBER))
    plate(g)
    ember_mace(g)
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(10, 7, 17, 7, 'G'); g.rect(13, 3, 14, 11, 'a'); g.rect(13, 7, 14, 7, 'g'); g.px(11, 9, 'n'); g.px(16, 9, 'n')
    return g

def ember2():  # Flame Paladin: crested helm, red plate with orange pauldrons, kite shield with a flame
    g = G(dict(EMBER, A='#b8341e', a='#7e2216'))
    plate(g)
    ember_mace(g, 4)
    g.rows(1, 13, [(1, 7), (0, 8), (0, 8), (0, 8), (0, 8), (0, 8), (1, 7), (1, 7), (2, 6), (3, 5), (4, 4)], 'D')
    g.rows(1, 14, [(2, 6), (1, 7), (1, 7), (1, 7), (1, 7), (2, 6), (2, 6), (3, 5), (4, 4)], 'R')
    g.text(3, 15, [' G ', 'GgG', 'GgG', ' g '])
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(10, 7, 17, 8, 'n'); g.px(12, 7, 'G'); g.px(15, 7, 'G'); g.rect(13, 9, 14, 11, 'a')
    g.text(11, 0, ['  g  ', ' gGg ', 'gGGGg'])  # flame crest
    return g

def ember3():  # Cinder Sentinel: dark red heavy plate, horned helm, burning eyes, flaming greatsword
    g = G(dict(EMBER, A='#7a2418', a='#541810', D='#c8502a', B='#e8c8a0'))
    plate(g, belt='g')
    g.rect(20, 15, 22, 18, 'a'); g.rect(21, 17, 25, 18, 'Y'); g.line(23, 16, 29, 4, 'D', 3); g.line(23, 15, 29, 5, 'G')
    g.px(28, 2, 'g'); g.px(30, 4, 'g')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(10, 7, 17, 8, 'n'); g.px(11, 7, 'G'); g.px(12, 7, 'g'); g.px(15, 7, 'g'); g.px(16, 7, 'G'); g.rect(13, 9, 14, 11, 'a')
    g.text(6, 0, ['B         B', 'BB       BB', ' BB     BB '])
    return g

def ember4():  # Pyre Knight: bucket helm under a crown of fire, orange plate cracked with molten seams
    g = G(dict(EMBER))
    plate(g)
    for x, y in ((10, 15), (11, 17), (16, 16), (17, 18), (12, 22), (15, 23), (7, 17), (20, 16)):
        g.px(x, y, 'G')
    g.rect(20, 15, 22, 18, 'a'); g.rect(21, 13, 22, 21, 'h'); g.line(22, 12, 25, 8, 'D'); g.ell(26, 7, 2.2, 2.2, 'g'); g.px(26, 7, 'G')
    g.rows(9, 3, [(0, 9)] * 9, 'D')
    g.rect(9, 7, 18, 7, 'n'); g.px(11, 7, 'G'); g.px(16, 7, 'G'); g.rect(9, 3, 18, 3, 'a'); g.rect(9, 11, 18, 11, 'a')
    g.text(9, 0, [' g   g  g ', 'gGg gGggGg', 'GGGGGGGGGG'])
    return g


# Spellblade alternatives (owner's request, Nov 2026): a blade lit with runes, steel and violet.
RUNE = {**SKIN, 'e': E, 'A': '#a8b0bc', 'a': '#7a8494', 'V': '#b48cff', 'v': '#6a4aa8', 'G': '#e8dcff', 'n': '#1e1a26',
        'k': '#2a2430', 'h': '#4a3a5a', 'Y': '#d0a840', 'P': '#3a2a5a', 'p': '#2a2040', 'H': '#2a1e18', 'L': '#3a3448'}

def rune_sword(g, x=22, y=16, length=7):
    g.rect(x - 1, y + 1, x + 1, y + 1, 'Y'); g.line(x, y, x + length - 1, y - length + 1, 'V', 2); g.line(x, y - 1, x + length - 1, y - length, 'G')
    g.px(x + length, y - length, 'V')

def spellblade1():  # Runeknight: steel plate with violet trim, open helm, a rune-lit sword
    g = G(dict(RUNE))
    legs(g, 'a'); torso(g, 'A')
    g.rows(10, 14, [(0, 7)] * 8, 'P'); g.rect(13, 14, 14, 21, 'V'); g.rect(9, 21, 18, 21, 'h')
    g.rect(6, 12, 9, 15, 'a'); g.rect(18, 12, 21, 15, 'a'); g.rect(6, 16, 8, 19, 'A'); g.rect(19, 15, 21, 17, 'A'); g.rect(20, 17, 22, 19, 's')
    rune_sword(g, 22, 16, 8)
    face(g, 10, 6, 8, 6); g.rect(12, 10, 15, 10, 'S')
    g.rows(9, 2, [(1, 8), (0, 9), (0, 9), (0, 9)], 'A'); g.rect(9, 6, 9, 11, 'A'); g.rect(18, 6, 18, 11, 'A'); g.rect(9, 5, 18, 5, 'a')
    g.px(13, 3, 'V'); g.px(14, 3, 'V')
    return g

def spellblade2():  # Arcane Duelist: hooded long coat, sword in hand, a rune glyph floating by the other
    g = G(dict(RUNE, B='#3a2a5a', b='#2a2040'))
    legs(g, 'L')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13)], 'B')
    g.rect(12, 13, 15, 24, 'b'); g.rect(9, 19, 18, 19, 'V')
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], 'B'); g.rect(6, 19, 8, 20, 's'); g.rows(19, 14, [(0, 2), (0, 3), (1, 3)], 'B'); g.rect(20, 17, 22, 19, 's')
    rune_sword(g, 22, 16, 8)
    g.text(1, 18, [' V ', 'VGV', ' V ']); g.px(2, 15, 'v'); g.px(4, 22, 'v')
    face(g, 10, 6, 8, 6); g.rect(12, 10, 15, 10, 'S')
    g.rows(8, 2, [(2, 8), (1, 9), (0, 10), (0, 1), (0, 1), (0, 1), (0, 1), (0, 1)], 'B'); g.rows(17, 5, [(0, 1)] * 6, 'B')
    g.rect(10, 5, 17, 5, 'b'); g.px(11, 7, 'V'); g.px(16, 7, 'V')
    return g

def spellblade3():  # Battlemage: plated robe, circlet, sword raised, lightning crackling in the off hand
    g = G(dict(RUNE, B='#4a3a7a', b='#2e2450', T='#d0a840', H='#e0dacb'))
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)], 'B')
    g.rect(13, 14, 14, 28, 'b'); g.rect(8, 20, 19, 20, 'T'); g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rect(6, 12, 9, 15, 'A'); g.rect(18, 12, 21, 15, 'A'); g.rect(6, 16, 8, 19, 'B'); g.rect(6, 19, 8, 20, 's'); g.rect(19, 15, 21, 17, 'B'); g.rect(20, 17, 22, 19, 's')
    g.rect(21, 4, 22, 17, 'V'); g.rect(21, 3, 22, 3, 'G'); g.rect(20, 17, 23, 17, 'Y'); g.rect(21, 18, 22, 20, 'h')
    g.text(1, 18, ['  G ', ' GV ', 'GVV ', ' VG ', ' G  '])
    head(g, 'long', None); g.rect(9, 3, 18, 3, 'Y'); g.px(13, 3, 'V'); g.px(14, 3, 'V')
    return g

def spellblade4():  # Hexblade: dark plate, a cape, a masked helm with violet eyes, a sword wreathed in violet flame
    g = G(dict(RUNE, A='#4a4a5e', a='#34344a', C='#5a2a6a', c='#3a1a4a'))
    g.rows(5, 12, [(1, 16), (0, 17), (0, 17)] + [(0, 17)] * 10 + [(1, 16)] * 3, 'c')
    legs(g, 'a'); torso(g, 'A'); g.rect(12, 14, 15, 22, 'a'); g.rect(9, 20, 18, 20, 'C')
    g.rect(6, 12, 9, 15, 'a'); g.rect(18, 12, 21, 15, 'a'); g.rect(6, 16, 8, 19, 'A'); g.rect(19, 15, 21, 18, 'A')
    rune_sword(g, 22, 16, 8); g.px(25, 10, 'v'); g.px(28, 8, 'v'); g.px(27, 6, 'G')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(10, 7, 17, 8, 'n'); g.px(11, 7, 'V'); g.px(16, 7, 'V'); g.rect(13, 9, 14, 11, 'a'); g.rect(9, 3, 18, 3, 'a')
    return g


# Dragonborn looks for the owner's review (Nov 2026): two scaled dragon-folk, two armoured warriors
# with dragon motifs. Not built into the game until the class is.
def drake_head(g, sc='Q', dk='q', horn='B', eye='G'):
    g.rows(9, 3, [(1, 7), (0, 8), (0, 8), (0, 9), (0, 10), (0, 11), (0, 11), (1, 10), (2, 8)], sc)  # head and snout
    g.rect(14, 9, 20, 9, dk); g.px(20, 7, dk); g.px(19, 7, dk)  # jaw line, nostril
    g.px(14, 6, eye); g.px(15, 6, 'n')
    g.text(7, 0, ['BB      ', ' BBB    ', '  BBB   '])  # swept-back horns
    g.rect(9, 12, 16, 12, dk)

def tail(g, c='Q'):
    g.line(9, 23, 4, 26, c, 2); g.line(4, 26, 1, 24, c, 2); g.px(1, 23, c)

def dragonborn1():  # Red Wyrmkin: red scales, swept horns, a leather harness, bare claws
    pal = {'Q': '#b8402a', 'q': '#7a2a1e', 'B': '#e8dcc0', 'G': '#ffd36b', 'n': '#1e1210', 'T': '#5a3a24', 'Y': '#d0a840',
           'k': '#2a1a18', 'L': '#7a2a1e', 'W': '#e8dcc0', 'P': '#e8a070'}
    g = G(pal)
    tail(g)
    legs(g, 'Q'); torso(g, 'Q'); g.rect(12, 15, 15, 22, 'P')  # pale belly scales
    g.line(9, 13, 17, 21, 'T'); g.rect(9, 21, 18, 22, 'T'); g.rect(13, 21, 14, 21, 'Y')
    g.rect(6, 13, 8, 19, 'Q'); g.rect(19, 14, 21, 18, 'Q'); g.text(19, 19, ['W W', ' W ']); g.text(5, 20, ['W W'])
    drake_head(g)
    return g

def dragonborn2():  # Bronze Drake: bronze scales, a frill, a travelling cloak, a long spear
    pal = {'Q': '#b8863a', 'q': '#7a5624', 'B': '#3a2a20', 'G': '#7fe3ff', 'n': '#1e1210', 'C': '#3a5a4a', 'c': '#2a4038',
           'k': '#2a1a18', 'L': '#7a5624', 'W': '#dfe6ee', 'h': '#5a3a24', 'P': '#e0c080'}
    g = G(pal)
    g.rows(6, 12, [(1, 14), (0, 15)] + [(0, 15)] * 12, 'c')  # cloak
    tail(g)
    legs(g, 'Q'); torso(g, 'C'); g.rect(12, 14, 15, 22, 'P')
    g.rect(6, 13, 8, 19, 'C'); g.rect(19, 14, 21, 18, 'C'); g.rect(20, 17, 22, 19, 'Q')
    g.rect(22, 2, 22, 30, 'h'); g.text(21, 0, [' W ', 'WWW', 'WWW', ' W '])
    drake_head(g)
    g.text(6, 4, ['q ', 'qq', 'qq', 'q '])  # frill
    return g

def dragonborn3():  # Dragon Knight: dark green plate, a dragon-head helm with horns, wing pauldrons, a sword
    pal = {'A': '#3a6a4a', 'a': '#264a34', 'D': '#5a8a5a', 'G': '#ffd36b', 'n': '#101a12', 'B': '#e8dcc0', 'Y': '#d0a840',
           'k': '#1a201a', 'L': '#264a34', 'W': '#dfe6ee', 'T': '#c8a040', 'h': '#3a2a20'}
    g = G(pal)
    legs(g, 'a'); torso(g, 'A'); g.rect(12, 14, 15, 22, 'a'); g.rect(9, 20, 18, 20, 'h'); g.rect(13, 20, 14, 20, 'Y')
    g.text(3, 10, ['DD    ', 'DDDD  ', ' DDDDD', '  DDDD'])  # wing pauldron, left
    g.text(18, 11, ['  DD', 'DDDD', 'DDD '])
    g.rect(6, 15, 8, 19, 'A'); g.rect(19, 15, 21, 17, 'A'); g.rect(20, 17, 22, 19, 'a')
    g.rect(21, 17, 25, 17, 'T'); g.line(23, 16, 29, 10, 'W', 2)
    g.rows(9, 3, [(1, 7), (0, 8), (0, 9), (0, 10), (0, 11), (0, 11), (0, 10), (1, 8)], 'A')  # helm with a snout visor
    g.rect(13, 6, 19, 6, 'n'); g.px(14, 6, 'G'); g.rect(13, 8, 20, 8, 'a')
    g.text(7, 0, ['BB      ', ' BBB    ', '  BBB   '])
    return g

def dragonborn4():  # Wyrm Guard: gold and teal scale mail, a winged crest helm, a round shield with a dragon
    pal = {'A': '#c8a040', 'a': '#8a6a24', 'M': '#3a7a7a', 'm': '#2a5a5a', 'G': '#7fe3ff', 'n': '#14101a', 'R': '#8a2a2a',
           'k': '#2a2018', 'L': '#2a5a5a', 'W': '#dfe6ee', 'h': '#5a3a24', 'S': '#e8e2d4'}
    g = G(pal)
    legs(g, 'm'); torso(g, 'M')
    for y in range(14, 22, 2):
        for x in range(9 + (y // 2) % 2, 19, 2): g.px(x, y, 'm')  # scale mail
    g.rect(9, 21, 18, 21, 'A'); g.rect(6, 12, 9, 14, 'A'); g.rect(18, 12, 21, 14, 'A')
    g.rect(19, 15, 21, 17, 'M'); g.rect(20, 17, 22, 19, 'A'); g.rect(21, 18, 23, 18, 'a'); g.line(23, 17, 29, 11, 'W', 2)
    g.ell(6, 19, 5, 5.5, 'A'); g.ell(6, 19, 4, 4.5, 'R'); g.text(4, 16, [' SS ', 'SSS ', ' SSS', '  S ', ' S  '])  # dragon emblem
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'A')
    g.rect(10, 7, 17, 8, 'n'); g.px(12, 7, 'G'); g.px(15, 7, 'G'); g.rect(13, 9, 14, 11, 'a')
    g.text(5, 0, ['MM          MM', ' MMM      MMM ', '  MMMM  MMMM  '])  # crest wings
    return g


# Psion looks for the owner's review (Nov 2026): a robed mystic, an armoured mind-knight, and two
# stranger ones (floating, glowing eyes). Kept out of sprites.js until the class is built.
PSI = {**SKIN, 'e': E, 'V': '#7fe3ff', 'v': '#3a9ab8', 'G': '#e8fbff', 'n': '#14101a', 'k': '#2a2430', 'Y': '#d0a840', 'L': '#3a3448'}

def psion1():  # Robed Mystic: deep blue robe, shaved head with a glowing third-eye mark, a crystal floating over the palm
    g = G(dict(PSI, B='#2a3a6a', b='#1e2a4e', T='#7fe3ff', H='#2a1e18'))
    body(g, 'robe'); arms(g)
    face(g, 10, 6, 8, 6); g.rect(12, 10, 15, 10, 'S'); g.rect(11, 5, 16, 5, 's'); g.px(13, 6, 'V'); g.px(14, 6, 'V')
    g.text(20, 11, [' G ', 'GVG', ' V ']); g.px(19, 15, 'v'); g.px(23, 14, 'v')  # floating crystal
    return g

def psion2():  # Mind-Knight: silver-blue plate, a smooth helm with a glowing visor band, a crystal blade
    g = G(dict(PSI, A='#8a9ab8', a='#5a6a88', D='#b8c8e0', h='#3a3448'))
    legs(g, 'a'); torso(g, 'A'); g.rect(12, 14, 15, 22, 'a'); g.rect(9, 20, 18, 20, 'h'); g.ell(13.5, 16.5, 1.5, 1.5, 'V')
    g.rect(6, 12, 9, 15, 'D'); g.rect(18, 12, 21, 15, 'D'); g.rect(6, 16, 8, 19, 'A'); g.rect(19, 15, 21, 18, 'A')
    g.rect(21, 17, 25, 17, 'Y'); g.line(23, 16, 29, 10, 'V', 2); g.line(23, 15, 29, 9, 'G')
    g.rows(9, 3, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8)], 'D')
    g.rect(9, 7, 18, 8, 'V'); g.rect(10, 7, 17, 7, 'G'); g.rect(9, 11, 18, 11, 'a')
    return g

def psion3():  # Floating Seer: hooded, hovering above the ground with no feet showing, glowing eyes, orbiting stones
    g = G(dict(PSI, B='#4a2a6a', b='#2e1a44', T='#7fe3ff'))
    g.rows(9, 10, ROBE[:13], 'B'); g.rect(13, 11, 14, 22, 'b'); g.rect(8, 17, 19, 17, 'T')
    g.rows(8, 23, [(1, 11), (3, 9), (5, 7)], 'b')  # robe trailing to a point, off the ground
    g.rows(6, 12, [(1, 3), (0, 3), (0, 3)], 'B'); g.rows(19, 11, [(0, 2), (0, 3), (1, 3)], 'B')
    g.rows(8, 1, [(2, 8), (1, 9), (0, 10), (0, 10), (0, 10), (0, 10), (0, 10), (1, 9)], 'B'); g.rect(10, 4, 17, 8, 'n')
    g.px(11, 6, 'V'); g.px(12, 6, 'G'); g.px(15, 6, 'G'); g.px(16, 6, 'V')
    for x, y in ((3, 14), (24, 9), (25, 20), (4, 24)):
        g.rect(x, y, x + 1, y + 1, 'v'); g.px(x, y, 'V')
    g.text(9, 29, ['  vVVVv  '])  # the glow beneath
    return g

def psion4():  # Void Monk: bare-armed, a blindfold, a halo of floating shards, wrapped hands crackling with light
    g = G(dict(PSI, B='#e0dacb', b='#a89a88', T='#3a9ab8', H='#1a1420', X='#7fe3ff'))
    legs(g, 'L'); torso(g, 'B'); g.rect(9, 20, 18, 21, 'T'); arms_bare(g)
    g.rect(6, 17, 8, 19, 'b'); g.rect(20, 17, 22, 19, 'b'); g.px(5, 18, 'V'); g.px(23, 18, 'V'); g.px(4, 17, 'G'); g.px(24, 19, 'G')
    face(g, 10, 6, 8, 6, eyes=False); g.rect(9, 7, 18, 8, 'T'); g.rect(12, 10, 15, 10, 'S'); g.rect(10, 4, 17, 5, 'H')
    for x, y in ((8, 1), (12, 0), (16, 0), (20, 2), (6, 4)):
        g.px(x, y, 'V'); g.px(x + 1, y, 'G')
    return g

# Gunslinger options (owner's request, Nov 2026): two frontier looks and two flintlock ones.
GUN = {**SKIN, 'e': E, 'W': '#b8c0cc', 'w': '#6a4a2e', 'G': '#f0f4f8', 'k': '#2a1e18', 'n': '#14101a'}

def duster(g, coat='B', shirt='b', belt='T', long=True):
    legs(g, 'L')
    spans = [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13)]
    if long:
        spans += [(-2, 4), (-3, 4), (-3, 4)]
    g.rows(8, 13, spans, coat)
    if long:
        g.rows(17, 25, [(0, 5), (0, 6), (0, 6)], coat)
    g.rect(12, 13, 15, 21, shirt); g.rect(10, 20, 17, 20, belt)

def gun_arms(g, coat='B'):
    g.rows(6, 15, [(1, 3), (0, 3), (0, 3), (0, 3)], coat); g.rect(6, 19, 8, 20, 's')
    g.rows(19, 14, [(0, 2), (0, 3), (1, 3)], coat); g.rect(20, 16, 22, 18, 's')

def revolver(g, x=22, y=15):
    g.rect(x, y, x + 6, y, 'W'); g.rect(x + 1, y, x + 2, y + 1, 'W'); g.px(x + 2, y + 1, 'n'); g.px(x, y - 1, 'W')
    g.rect(x, y + 1, x, y + 3, 'w'); g.px(x + 6, y - 1, 'W')

def flintlock(g, x=22, y=15):
    g.rect(x + 2, y, x + 7, y, 'W'); g.rect(x, y, x + 2, y + 1, 'w'); g.rect(x - 1, y + 2, x, y + 3, 'w')
    g.px(x + 1, y - 1, 'X'); g.px(x + 2, y + 1, 'X')

def cowboy(g, y=6):
    g.rect(6, y - 1, 21, y - 1, 'h'); g.px(6, y - 2, 'h'); g.px(21, y - 2, 'h')
    g.rect(10, y - 4, 17, y - 2, 'h'); g.rect(11, y - 5, 12, y - 5, 'h'); g.rect(15, y - 5, 16, y - 5, 'h')
    g.rect(10, y - 2, 17, y - 2, 'X')

def holster(g):
    g.rect(8, 21, 9, 24, 'w'); g.px(8, 20, 'W'); g.px(9, 20, 'w')

def gunslinger1():  # Drifter: tan duster, cowboy hat, stubble, a revolver drawn and a second in its holster
    g = G({**GUN, 'B': '#a88a5a', 'b': '#e0d6bc', 'T': '#5a3a24', 'H': '#6a4a2e', 'h': '#5a4030', 'X': '#2a1e18', 'L': '#3a3440'})
    duster(g); gun_arms(g); head(g, 'short', 'stache'); g.rect(11, 11, 16, 11, 'S'); cowboy(g)
    holster(g); revolver(g)
    return g

def gunslinger2():  # Outlaw: striped poncho, a red bandana over the face, flat wide hat, revolver out of the poncho
    g = G({**GUN, 'B': '#8a5a3a', 'b': '#5a3a24', 'T': '#e0c070', 'R': '#a83030', 'H': '#1a1420', 'h': '#2a2028', 'X': '#a83030', 'L': '#4a3a30'})
    legs(g, 'L'); torso(g, 'b')
    spans = [(2, 13), (1, 14), (0, 15), (0, 15), (0, 15), (1, 14), (2, 13), (3, 12), (4, 11), (5, 10), (6, 9)]
    g.rows(6, 13, spans, 'B'); g.rows(6, 17, [spans[4]], 'T'); g.rows(6, 20, [spans[7]], 'T'); g.rows(6, 22, [spans[9]], 'T')
    g.rect(13, 13, 14, 14, 'R')
    g.rect(20, 16, 22, 18, 's')
    head(g, 'long'); g.rect(10, 9, 17, 11, 'R'); g.px(13, 12, 'R'); g.px(14, 12, 'R')
    g.rect(5, 5, 22, 5, 'h'); g.rows(10, 1, [(1, 6), (0, 7), (0, 7), (0, 7)], 'h'); g.rect(10, 4, 17, 4, 'T')
    revolver(g)
    return g

def gunslinger3():  # Pistoleer: tricorne, blue coat with gold trim, a long flintlock, a powder horn at the hip
    g = G({**GUN, 'B': '#2a4a7a', 'b': '#e8e2d4', 'T': '#c8a040', 'H': '#8a5a2a', 'h': '#1e1a26', 'X': '#c8a040', 'L': '#e8e2d4', 'O': '#e8dcc0', 'o': '#a89878'})
    duster(g, long=False); g.rect(8, 13, 8, 24, 'T'); g.rect(19, 13, 19, 24, 'T'); gun_arms(g)
    head(g, 'pony', 'goatee')
    g.text(8, 2, ['   hhhhhh   ', ' hhhhhhhhhh ', 'hhhhhhhhhhhh', 'hXXXXXXXXXXh']); g.px(7, 3, 'h'); g.px(20, 3, 'h')
    g.text(3, 20, ['O   ', 'OO  ', ' Oo ', '  ow'])
    flintlock(g)
    return g

def gunslinger4():  # Witch-hunter: tall buckled hat with a low brim shading the eyes, black coat, bandolier, twin silver flintlocks
    g = G({**GUN, 'B': '#24202a', 'b': '#8a2a2a', 'T': '#c8ccd6', 'H': '#d8d0c0', 'h': '#1a1620', 'X': '#d8dce6', 'L': '#2a2630', 'Y': '#f0f4f8'})
    duster(g, shirt='b'); gun_arms(g)
    head(g, 'long'); g.rect(10, 6, 17, 7, 'S'); g.px(12, 8, 'Y'); g.px(15, 8, 'Y'); g.px(12, 9, 's'); g.px(15, 9, 's')
    g.rect(10, -1, 17, 4, 'h'); g.rect(7, 5, 20, 5, 'h'); g.rect(10, 3, 17, 3, 'T'); g.rect(13, 2, 14, 4, 'X')
    for i, (x, y) in enumerate(((9, 13), (10, 14), (11, 15), (12, 16), (13, 17), (14, 18), (15, 19))):
        g.px(x, y, 'w')
        if i % 2: g.px(x + 1, y, 'X')
    g.rect(6, 21, 6, 26, 'W'); g.rect(7, 19, 8, 21, 'w'); g.px(6, 27, 'W')
    flintlock(g)
    return g

# Samurai options (owner's request, Nov 2026): for review (build.REVIEW).
SAM = {**SKIN, 'e': E, 'W': '#e8eef4', 'w': '#2a1e18', 'k': '#1a1620', 'n': '#14101a', 'G': '#ffd36b'}

def hakama(g, c='L', dark='l'):
    g.rows(8, 22, [(1, 10), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13)], c)
    g.rect(13, 24, 14, 28, dark); g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')

def kimono(g, c='B', inner='b', sash='T'):
    torso(g, c, rows=10); g.line(10, 13, 14, 18, inner); g.line(17, 13, 14, 17, inner); g.rect(9, 20, 18, 21, sash)

def katana(g, high=False):
    if high:
        g.rect(21, 13, 22, 15, 'w'); g.rect(20, 12, 23, 12, 'X'); g.line(22, 11, 27, 1, 'W')
    else:
        g.px(20, 19, 'w'); g.px(21, 18, 'w'); g.rect(22, 16, 23, 17, 'X'); g.line(24, 15, 30, 9, 'W')

def saya(g, drawn=True):
    g.line(3, 25, 9, 20, 'w'); g.line(4, 25, 10, 20, 'w')
    if not drawn:
        g.rect(10, 18, 11, 19, 'X'); g.line(12, 17, 14, 15, 'k')

def topknot(g, y=6):
    g.rect(10, y - 2, 17, y, 'H'); g.rect(9, y - 1, 9, y + 2, 'H'); g.rect(18, y - 1, 18, y + 1, 'H'); g.rect(13, y - 4, 14, y - 3, 'H')

def samurai1():  # Ronin: topknot, stubble, faded blue kimono and grey hakama, katana drawn, the scabbard at the hip
    g = G({**SAM, 'B': '#3a5a7a', 'b': '#d8d0c0', 'T': '#2a2a36', 'L': '#5a5e6a', 'l': '#3a3e48', 'H': '#1a1420', 'X': '#a88a3a'})
    hakama(g); kimono(g); arms(g); face(g, 10, 6, 8, 6); g.rect(12, 10, 15, 10, 'S'); g.rect(11, 11, 16, 11, 'S'); topknot(g)
    saya(g); katana(g)
    return g

def samurai2():  # Wanderer: wide straw hat shading the eyes, dark haori, hand on the hilt of a sheathed blade
    g = G({**SAM, 'B': '#2a2a36', 'b': '#8a2a2a', 'T': '#c8a040', 'L': '#3a3440', 'l': '#24202a', 'h': '#c8a868', 'x': '#8a6a3a', 'X': '#c8a040'})
    hakama(g); kimono(g); arms(g); face(g, 10, 6, 8, 6); g.rect(10, 6, 17, 7, 'S')
    g.text(5, 0, ['        hh        ', '      hhhhhh      ', '    hhhhhhhhhh    ', '  hhhhhhhhhhhhhh  ', 'xhhhhhhhhhhhhhhhhx'])
    g.rect(5, 5, 22, 5, 'x')
    g.line(13, 24, 25, 17, 'w'); g.line(14, 24, 26, 17, 'w'); g.rect(19, 19, 20, 20, 'X'); g.line(21, 18, 24, 16, 'k')  # saya forward, hilt in hand
    g.rect(20, 16, 22, 18, 's')
    return g

def samurai3():  # Armoured samurai: kabuto with a gold crescent crest, red lacquered plate and shoulder boards, a face mask, katana drawn
    g = G({**SAM, 'B': '#a82a24', 'b': '#6a1a18', 'T': '#c8a040', 'L': '#2a2430', 'l': '#1a1620', 'A': '#24202a', 'X': '#c8a040', 'M': '#6a1a18'})
    hakama(g, 'B', 'b'); g.rect(9, 22, 18, 22, 'T')
    torso(g, 'B', rows=10); g.rect(9, 15, 18, 15, 'b'); g.rect(9, 17, 18, 17, 'b'); g.rect(9, 19, 18, 19, 'b'); g.rect(9, 21, 18, 21, 'T')
    arms(g); g.rect(5, 13, 9, 17, 'A'); g.rect(18, 13, 22, 16, 'A'); g.rect(5, 15, 9, 15, 'T'); g.rect(18, 15, 22, 15, 'T')  # sode
    face(g, 10, 6, 8, 6); g.rect(10, 9, 17, 11, 'M'); g.px(13, 10, 'n'); g.px(14, 10, 'n')  # menpo
    g.rows(9, 2, [(1, 8), (0, 9), (0, 9), (-1, 10)], 'A'); g.rect(8, 6, 9, 9, 'A'); g.rect(18, 6, 19, 9, 'A')
    g.text(7, 0, ['X            X', ' XX   XX   XX ', '   XXX  XXX   ']); g.rect(13, 3, 14, 4, 'X')
    saya(g); katana(g)
    return g

def samurai4():  # Kensei: long tied-back hair, white headband with trailing tails, white kimono and red hakama, katana raised high
    g = G({**SAM, 'B': '#e8e2d4', 'b': '#a8a090', 'T': '#2a2a36', 'L': '#a82a24', 'l': '#6a1a18', 'H': '#1a1420', 'X': '#c8a040', 'Y': '#f4f0e8'})
    hakama(g); kimono(g); arms(g, left_y=15); g.rect(20, 13, 22, 15, 's'); g.rows(19, 14, [(0, 2), (0, 2)], 'B')
    head(g, 'pony'); g.rect(9, 5, 18, 5, 'Y'); g.text(4, 5, ['YYYY ', '  YY ', '   Y '])
    saya(g); katana(g, high=True)
    return g

SK = SKIN
OPTIONS = {
    'duelist': [
        ('Fencer', build({**SK, 'B': '#8a2a3a', 'b': '#e8e2d4', 'T': '#c8a040', 'H': '#2a1e18', 'h': '#2a2430', 'X': '#e8e2d4', 'W': '#dfe6ee', 'w': '#5a3a24', 'k': '#2a2028', 'L': '#2a2430'},
                         'coat', 'short', 'goatee', 'feather_cap', 'rapier', 'buckler')),
        ('Swordswoman', build({**SK, 'B': '#3a5a8a', 'b': '#c8c4b4', 'T': '#5a3a24', 'H': '#c88a3a', 'W': '#dfe6ee', 'w': '#5a3a24', 'X': '#c8a040', 'k': '#2a2028', 'L': '#4a3a30'},
                              'tunic', 'pony', None, None, 'sword', 'dagger')),
        ('Blademaster', build({**SKIN2, 'B': '#2a2a3a', 'b': '#a83a30', 'T': '#c8a040', 'H': '#1a1420', 'W': '#dfe6ee', 'w': '#2a2028', 'X': '#a83a30', 'k': '#1a1420', 'L': '#2a2a3a'},
                              'coat', 'short', 'stache', 'circlet', 'sword', None)),
        ('Rogue Knight', build({**SK, 'B': '#5a5e6a', 'b': '#3a3e48', 'T': '#8a6a3a', 'H': '#6a4a2e', 'h': '#5a5e6a', 'W': '#dfe6ee', 'w': '#5a3a24', 'X': '#c8a040', 'x': '#1e1a26', 'k': '#2a2028', 'L': '#3a3e48'},
                               'tunic', 'short', 'full', 'skullcap', 'rapier', 'buckler')),
    ],
    'berserker': [
        ('Barbarian', build({**SK, 'B': '#7a5a3a', 'b': '#5a3a24', 'T': '#c8a040', 'H': '#a85a2a', 'W': '#a8b0bc', 'w': '#5a3a24', 'k': '#3a2a20'},
                            'bare', 'wild', 'full', None, 'greataxe', None, bare=True)),
        ('Raider', build({**SK, 'B': '#6a6a5a', 'b': '#4a4a3e', 'T': '#5a3a24', 'H': '#d8b860', 'W': '#a8b0bc', 'w': '#5a3a24', 'X': '#a83030', 'k': '#2a2028', 'L': '#4a3a30'},
                         'tunic', 'long', 'full', 'horned', 'axe', 'shield')),
        ('Pit Fighter', build({**SKIN2, 'B': '#8a3a2a', 'b': '#5a2420', 'T': '#c8a040', 'H': '#1a1420', 'W': '#a8b0bc', 'w': '#5a3a24', 'k': '#2a2028'},
                              'bare', 'mohawk', None, None, 'flail', None, bare=True)),
        ('Wildling', build({**SK, 'B': '#5a6a4a', 'b': '#3e4a34', 'T': '#8a6a4a', 'H': '#3a2a1a', 'h': '#7a6a5a', 'W': '#d8d0c0', 'w': '#5a3a24', 'x': '#1e1a26', 'k': '#3a2a20'},
                           'bare', 'wild', 'full', None, 'claws', None, bare=True)),
    ],
    'ranger': [
        ('Archer', build({**SK, 'B': '#4a6a3a', 'b': '#3a5030', 'T': '#6a4a2e', 'H': '#8a5a2a', 'h': '#3a5030', 'x': '#1e2a1a', 'W': '#a8b0bc', 'w': '#7a5a34', 'X': '#d8d0c0', 'k': '#3a2a20', 'L': '#5a4a3a'},
                         'tunic', None, None, 'hood', 'bow', 'quiver')),
        ('Falconer', build({**SK, 'B': '#7a5a3a', 'b': '#5a4028', 'T': '#c8a040', 'H': '#2a1e18', 'W': '#a8b0bc', 'w': '#7a5a34', 'X': '#d8d0c0', 'O': '#8a6a4a', 'o': '#5a4028', 'y': '#e0b040', 'k': '#3a2a20', 'L': '#4a3a30'},
                           'tunic', 'short', 'stache', None, 'bow', 'hawk')),
        ('Huntress', build({**SK, 'B': '#3a4a3a', 'b': '#2a3a2a', 'T': '#8a6a4a', 'H': '#d8b860', 'W': '#a8b0bc', 'w': '#5a3a24', 'X': '#d8d0c0', 'k': '#3a2a20', 'L': '#3a3a30'},
                           'tunic', 'pony', None, None, 'crossbow', 'quiver')),
        ('Scout', build({**SK, 'B': '#6a5a3a', 'b': '#4a3e28', 'T': '#3a5030', 'H': '#5a3a24', 'h': '#3a5030', 'W': '#a8b0bc', 'w': '#7a5a34', 'X': '#a83030', 'k': '#3a2a20', 'L': '#4a3a30'},
                        'vest', 'short', None, 'feather_cap', 'bow', 'quiver')),
    ],
    'scoundrel': [
        ('Thief', build({**SK, 'B': '#3a3a48', 'b': '#2a2a36', 'T': '#6a4a2e', 'h': '#2a2a36', 'x': '#14101a', 'W': '#dfe6ee', 'w': '#3a2a1a', 'k': '#1e1a26', 'L': '#2a2a36'},
                        'tunic', None, None, 'hood', 'dagger', 'dagger')),
        ('Rake', build({**SK, 'B': '#7a2a4a', 'b': '#e8e2d4', 'T': '#c8a040', 'H': '#1a1420', 'h': '#2a2430', 'X': '#c8a040', 'W': '#dfe6ee', 'w': '#3a2a1a', 'k': '#1e1a26', 'L': '#2a2430'},
                       'coat', 'short', 'stache', 'wide', 'dagger', None)),
        ('Cutpurse', build({**SK, 'B': '#6a5a3a', 'b': '#c8c4b4', 'T': '#5a3a24', 'H': '#a85a2a', 'h': '#3a5a8a', 'W': '#dfe6ee', 'w': '#3a2a1a', 'X': '#c8a040', 'k': '#2a2028', 'L': '#4a3a30'},
                           'vest', 'short', None, 'bandana', 'dagger', 'satchel')),
        ('Poisoner', build({**SK, 'B': '#3a4a3a', 'b': '#2a3a2a', 'T': '#5a3a24', 'h': '#2a3a2a', 'x': '#14201a', 'W': '#dfe6ee', 'w': '#3a2a1a', 'X': '#8be04e', 'k': '#1e1a26', 'L': '#2a3a2a'},
                           'coat', None, None, 'hood', 'dagger', 'flask')),
    ],
    'herald': [
        ('Bard', build({**SK, 'B': '#3a6a5a', 'b': '#e8e2d4', 'T': '#c8a040', 'H': '#c88a3a', 'h': '#7a2a3a', 'X': '#e8e2d4', 'W': '#dfe6ee', 'w': '#8a5a34', 'x': '#3a2a1a', 'k': '#3a2a20', 'L': '#4a3a30'},
                       'coat', 'short', None, 'feather_cap', 'lute', None)),
        ('Minstrel', build({**SK, 'B': '#8a5a2a', 'b': '#e0c890', 'T': '#5a3a24', 'H': '#2a1e18', 'W': '#dfe6ee', 'w': '#a0703e', 'X': '#c8a040', 'x': '#3a2a1a', 'k': '#3a2a20', 'L': '#5a4a3a'},
                           'tunic', 'long', None, None, 'lute', None)),
        ('Herald', build({**SK, 'B': '#3a5aa8', 'b': '#c8a040', 'T': '#e8e2d4', 'H': '#6a4a2e', 'h': '#3a5aa8', 'X': '#c8a040', 'W': '#dfe6ee', 'w': '#5a3a24', 'k': '#2a2028', 'L': '#e8e2d4'},
                         'coat', 'short', 'goatee', 'beret', 'banner', None)),
        ('Skald', build({**SK, 'B': '#5a4a6a', 'b': '#3e3448', 'T': '#c8a040', 'H': '#d8b860', 'W': '#a8b0bc', 'w': '#5a3a24', 'X': '#d8d0c0', 'k': '#2a2028', 'L': '#3e3448'},
                        'tunic', 'long', 'full', None, 'horn', 'shield')),
    ],
    'alchemist': [
        ('Alchemist', build({**SK, 'B': '#6a4a2e', 'b': '#4a3420', 'T': '#c8a040', 'H': '#8a8a8a', 'h': '#3a3440', 'X': '#8be04e', 'x': '#3a7a2a', 'W': '#dfe6ee', 'w': '#6a4a2e', 'k': '#2a2028', 'L': '#3a3440'},
                            'coat', 'short', 'full', 'goggles', 'flask', 'potions')),
        ('Bombardier', build({**SK, 'B': '#5a5e6a', 'b': '#3a3e48', 'T': '#a83030', 'H': '#a85a2a', 'h': '#5a3a24', 'X': '#ffb040', 'x': '#24202a', 'W': '#dfe6ee', 'w': '#6a4a2e', 'k': '#2a2028', 'L': '#3a3e48'},
                             'vest', 'short', 'stache', 'goggles', 'bomb', None)),
        ('Herb-witch', build({**SK, 'B': '#5a3a6a', 'b': '#3e2a4a', 'T': '#8be04e', 'H': '#1a1420', 'h': '#3e2a4a', 'X': '#e070c0', 'x': '#8a3a7a', 'W': '#dfe6ee', 'w': '#6a4a2e', 'k': '#2a2028'},
                             'robe', 'long', None, 'wide', 'flask', 'satchel')),
        ('Tinker', build({**SK, 'B': '#7a6a3a', 'b': '#5a4e2a', 'T': '#5a3a24', 'H': '#2a1e18', 'h': '#5a3a24', 'X': '#7fe3ff', 'x': '#24202a', 'W': '#a8b0bc', 'w': '#6a4a2e', 'k': '#2a2028', 'L': '#4a3a30'},
                         'vest', 'short', None, 'goggles', 'sling', 'potions')),
    ],
    'warden': [
        ('Druid', build({**SK, 'B': '#5a6a3a', 'b': '#3e4a28', 'T': '#8a6a4a', 'H': '#e0dacb', 'h': '#4a5a30', 'X': '#7ab858', 'x': '#3a6034', 'W': '#d8d0c0', 'w': '#6a4a2e', 'k': '#3a2a20'},
                        'robe', 'long', 'full', 'wreath', 'branch', None)),
        ('Antlered Warden', build({**SK, 'B': '#4a5a3a', 'b': '#3a4a2a', 'T': '#8a6a4a', 'h': '#3a4a2a', 'x': '#14201a', 'X': '#7ab858', 'W': '#d8d0c0', 'w': '#8a6a4a', 'k': '#3a2a20'},
                                  'robe', None, None, 'antlers', 'branch', None)),
        ('Grove Keeper', build({**SK, 'B': '#6a5a3a', 'b': '#4a3e28', 'T': '#3a6034', 'H': '#8a5a2a', 'X': '#7ab858', 'x': '#c8a040', 'W': '#d8d0c0', 'w': '#6a4a2e', 'k': '#3a2a20', 'L': '#4a3a30'},
                               'tunic', 'pony', None, 'wreath', 'sickle', 'acorn')),
        ('Thornspeaker', build({**SKIN2, 'B': '#3a4a2a', 'b': '#2a3a1e', 'T': '#a83030', 'H': '#1a1420', 'h': '#2a3a1e', 'x': '#0e1a0e', 'X': '#c84a3a', 'W': '#d8d0c0', 'w': '#5a3a24', 'k': '#3a2a20'},
                               'robe', None, None, 'hood', 'staff', 'orb')),
    ],
    # owner's request, Nov 2026: a sword in one hand, a rune-lit orb in the other
    'spellblade': [
        ('Spellblade', build({**SK, 'B': '#4a3a6a', 'b': '#2a2440', 'T': '#c8a040', 'H': '#e0dacb', 'h': '#2a2440', 'X': '#b48cff', 'x': '#6a4aa8', 'W': '#dfe6ee', 'w': '#5a3a24', 'k': '#1e1a26', 'L': '#2a2440'},
                             'coat', 'long', None, 'circlet', 'sword', 'orb')),
        ('Runeknight', spellblade1), ('Arcane Duelist', spellblade2), ('Battlemage', spellblade3), ('Hexblade', spellblade4),
    ],
    # owner's request, Nov 2026: a knight running hot, with a glowing mace (option 1); then knights in
    # orange-to-red plate
    'psion': [
        ('Robed Mystic', psion1), ('Mind-Knight', psion2), ('Floating Seer', psion3), ('Void Monk', psion4),
    ],
    'dragonborn': [
        ('Red Wyrmkin', dragonborn1), ('Bronze Drake', dragonborn2), ('Dragon Knight', dragonborn3), ('Wyrm Guard', dragonborn4),
    ],
    # owner's request, Nov 2026: for review, not built yet (build.REVIEW)
    'gunslinger': [
        ('Drifter', gunslinger1), ('Outlaw', gunslinger2), ('Pistoleer', gunslinger3), ('Witch-hunter', gunslinger4),
    ],
    # owner's request, Nov 2026: for review, not built yet (build.REVIEW)
    'samurai': [
        ('Ronin', samurai1), ('Wanderer', samurai2), ('Armoured Samurai', samurai3), ('Kensei', samurai4),
    ],
    'emberknight': [
        ('Emberknight', build({**SK, 'B': '#7a2a1e', 'b': '#3a2a2a', 'T': '#e0a040', 'H': '#2a1e18', 'h': '#5a5e6a', 'X': '#ffa030', 'x': '#c0501a', 'W': '#ffb048', 'w': '#4a3a30', 'k': '#1e1a1a', 'L': '#3a2a2a'},
                              'tunic', 'short', 'full', 'skullcap', 'maul', None)),
        ('Ember Knight', ember1), ('Flame Paladin', ember2), ('Cinder Sentinel', ember3), ('Pyre Knight', ember4),
    ],
}

if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    from PIL import Image, ImageDraw
    rows = []
    for cls, opts in OPTIONS.items():
        items = [(name, fn().strings(), fn().pal) for name, fn in opts]
        sheet(items, f'{out}/{cls}.png', scale=5, cols=4, bg=(16, 22, 31))
        rows.append((cls, Image.open(f'{out}/{cls}.png')))
    w = max(i.width for _, i in rows); hh = [i.height - 80 for _, i in rows]
    big = Image.new('RGBA', (w + 30, sum(hh) + 34 * len(rows)), (16, 22, 31, 255)); d = ImageDraw.Draw(big)
    y = 0
    for (cls, im), h in zip(rows, hh):
        d.text((12, y + 10), cls.capitalize() + ':  ' + ',  '.join(f'{i + 1} {n}' for i, (n, _) in enumerate(OPTIONS[cls])), fill=(201, 162, 74))
        big.alpha_composite(im.crop((0, 0, im.width, h)), (15, y + 26)); y += h + 34
    big.save(f'{out}/new-hero-options.png')
