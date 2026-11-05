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
