# Master classes, four options each, built on the owner's first-tier picks.
from kit import *
from promos import knight, wizard, bandit, clear, E

# ---- shared gear ----
def arm_r(g, c='A', hand='f'):  # right arm forward, hand at about (21-23, 18-19)
    g.rect(19, 15, 21, 18, c); g.rect(21, 18, 23, 19, hand)
def arm_l(g, c='A', hand='f'):  # left arm down, hand at about (5-7, 20-21)
    g.rect(6, 15, 8, 20, c); g.rect(5, 20, 7, 21, hand)
def katana_up(g):
    g.line(22, 17, 27, 2, 'w'); g.line(23, 17, 28, 2, 'W'); g.rect(21, 16, 24, 16, 'Y'); g.rect(22, 18, 23, 20, 'h')
def lance(g, x=23, top=0, bot=30, tip='w'):
    g.rect(x, top + 3, x, bot, 'h'); g.text(x - 1, top, [' ' + tip + ' ', tip + tip + tip, ' ' + tip + ' '])
def spear(g):
    g.line(22, 21, 27, 0, 'h'); g.text(26, 0, [' w', 'ww', 'w '])
def round_shield(g, cx=6, cy=19, rx=5.5, ry=6, rim='S', face='s', boss='Y'):
    g.ell(cx, cy, rx, ry, rim); g.ell(cx, cy, rx - 1.5, ry - 1.5, face); g.ell(cx, cy, 1.4, 1.4, boss)
def great_shield(g, face='s', rim='S', trim='Y'):
    g.rect(3, 14, 18, 28, rim); g.rect(4, 15, 17, 27, face); g.rect(3, 14, 18, 14, trim); g.rect(3, 28, 18, 28, trim)
def hammer(g):
    g.rect(21, 3, 22, 18, 'h'); g.rect(19, 2, 25, 6, 'A'); g.rect(19, 2, 25, 2, 'a'); g.rect(20, 17, 23, 19, 'A')

BM = {'A': '#4a4a58', 'a': '#33333e', 'T': '#c8a040', 'Y': '#d0a840', 'P': '#c8a040', 'W': '#a8b0bc'}
JG = {'T': '#3a5aa8', 'S': '#5a6070', 's': '#7a8494', 'P': '#3a5aa8', 'W': '#a8b0bc'}

# ---------- Samurai (from the black-and-gold Blademaster) ----------
def samurai1():  # lacquered red armour, kabuto with a gold crescent crest, katana raised
    g = knight({**BM, 'A': '#8a2a2a', 'a': '#5a1a1a', 'T': '#2a2430'}, shield=False, sword=False, plume=False)
    g.text(9, 0, ['Y        Y', 'YY      YY', ' YYY  YYY ', '   YYYY   ']); arm_r(g); katana_up(g); arm_l(g)
    g.rect(8, 11, 19, 12, 'a')  # neck guard flare
    return g
def samurai2():  # bare head with a topknot, red armour, katana held two-handed low
    g = knight({**BM, 'A': '#8a2a2a', 'a': '#5a1a1a', 'T': '#2a2430'}, shield=False, sword=False, plume=False, helm='open')
    g.rect(9, 3, 18, 7, 'u'); g.rect(13, 0, 14, 3, 'u'); g.rect(10, 7, 17, 7, 'u'); g.rect(9, 7, 9, 10, 'u'); g.rect(18, 7, 18, 9, 'u'); g.pal['u'] = '#1e1a22'
    g.rect(11, 8, 16, 11, 'f'); g.px(12, 9, 'e'); g.px(15, 9, 'e')
    arm_r(g); g.rect(14, 18, 20, 19, 'f'); g.line(23, 20, 29, 27, 'w'); g.line(23, 21, 28, 27, 'W'); g.rect(21, 18, 22, 21, 'h')
    return g
def samurai3():  # horned kabuto, red menpo face mask, katana and wakizashi
    g = knight({**BM, 'A': '#2a2a34', 'a': '#1a1a22', 'T': '#8a2a2a'}, shield=False, sword=False, plume=False)
    g.text(7, 1, ['Y          Y', 'YY        YY', ' YY      YY ', '  YY    YY  ']); g.rect(10, 9, 17, 12, 'm'); g.rect(10, 10, 17, 10, 'n'); g.pal['m'] = '#a83030'
    arm_r(g); katana_up(g); arm_l(g); g.line(5, 22, 2, 27, 'w')
    return g
def samurai4():  # straw jingasa hat, dark armour, hand resting on a sheathed katana
    g = knight({**BM, 'T': '#3a3a48'}, shield=False, sword=False, plume=False, helm='open')
    g.rows(4, 3, [(8, 11), (5, 14), (2, 17), (0, 19)], 'j'); g.pal['j'] = '#c8a868'; g.rect(4, 6, 23, 6, 'J'); g.pal['J'] = '#8a7040'
    g.rect(11, 8, 16, 11, 'f'); g.rect(11, 8, 16, 8, 'F'); g.px(12, 9, 'e'); g.px(15, 9, 'e')
    g.line(6, 24, 21, 19, 'm'); g.line(6, 25, 21, 20, 'm'); g.rect(19, 18, 20, 21, 'Y'); g.pal['m'] = '#2a1a1a'
    g.rect(19, 15, 21, 18, 'A'); g.rect(20, 18, 21, 19, 'f'); arm_l(g)
    return g
# ---------- Dragoon (from the Blademaster) ----------
def dragoon1():  # blue armour, spiked dragon-crest helm, lance held upright
    g = knight({**BM, 'A': '#3a5aa8', 'a': '#2a4280', 'T': '#c8a040'}, shield=False, sword=False, plume=False)
    g.text(9, 0, ['  a  a  a ', ' aa aa aa ', '  aaaaaa  ', '   aaaa   ']); arm_r(g); lance(g, 23); arm_l(g)
    return g
def dragoon2():  # winged helm, lance angled up, small round shield
    g = knight({**BM, 'A': '#3a6a9a', 'a': '#264a70', 'T': '#e8e0c8', 'S': '#c8a040', 's': '#e0c060'}, shield=False, sword=False, plume=False)
    g.text(4, 2, ['W    ', 'WW   ', 'WWW  ', ' WWWW']); g.text(19, 2, ['    W', '   WW', '  WWW', 'WWWW ']); g.pal['W'] = '#e8eef4'
    arm_r(g); g.line(22, 19, 28, 1, 'h'); g.text(27, 0, ['ww', 'w ']); round_shield(g, 6, 19, 4, 4.5)
    return g
def dragoon3():  # black-violet armour, long fin helm, lance couched for a charge
    g = knight({**BM, 'A': '#3a2e4a', 'a': '#2a2036', 'T': '#7a3a9a'}, shield=False, sword=False, plume=False)
    g.text(13, 0, ['  P', ' PP', 'PPP', 'PP ']); g.text(16, 1, ['PPP', 'PPPP', 'PPPPP']); g.pal['P'] = '#7a3a9a'
    arm_r(g); g.line(14, 21, 30, 14, 'h'); g.text(28, 12, ['ww', 'www', 'ww']); arm_l(g)
    return g
def dragoon4():  # green dragon-scale armour, horned helm, spear with a red pennant
    g = knight({**BM, 'A': '#3e7a5a', 'a': '#2a5a40', 'T': '#c8a040'}, shield=False, sword=False, plume=False)
    for y in range(14, 23, 2):
        for x in range(9 + (y // 2) % 2, 19, 2): g.px(x, y, 'a')
    g.text(8, 2, ['W        W', 'WW      WW', ' W      W ']); g.pal['W'] = '#e8e0c8'
    arm_r(g); lance(g, 23); g.text(24, 4, ['rrrr', 'rrr ', 'rr  ']); g.pal['r'] = '#c83a3a'; arm_l(g)
    return g
# ---------- Hoplite (from the shield-wall Juggernaut) ----------
def hoplite1():  # Corinthian helm with a crest, bronze round shield, spear raised
    g = knight({**JG, 'A': '#c8903a', 'a': '#9a6a28', 'T': '#a83030', 'S': '#9a6a28', 's': '#c8903a'}, shield=False, sword=False, plume=False)
    g.text(7, 0, ['  rrrrrrrrrr ', ' rrrrrrrrrrrr', 'r   r   r   r']); g.pal['r'] = '#c83a3a'
    arm_r(g); spear(g); round_shield(g, 8, 20, 7, 7.5)
    return g
def hoplite2():  # a tall red scutum and a spear
    g = knight({**JG, 'A': '#a8b0bc', 'S': '#8a2a2a', 's': '#a83a3a', 'Y': '#d0a840', 'P': '#d0a840'}, shield=False, sword=False)
    arm_r(g); spear(g); great_shield(g, 's', 'S', 'Y'); g.ell(10.5, 21, 2, 2, 'Y'); g.rect(5, 16, 16, 16, 'Y'); g.rect(5, 26, 16, 26, 'Y')
    return g
def hoplite3():  # tall horsehair crest, bronze armour, lambda shield, spear over the shoulder
    g = knight({**JG, 'A': '#c8903a', 'a': '#9a6a28', 'T': '#e8e0c8', 'S': '#2a2430', 's': '#a83030'}, shield=False, sword=False, plume=False)
    g.text(12, 0, ['  rr', ' rrrr', 'rrrrr', 'rr  ']); g.pal['r'] = '#2a2430'
    arm_r(g); g.line(14, 26, 27, 2, 'h'); g.text(26, 0, [' w', 'ww', 'w ']); round_shield(g, 7, 20, 6.5, 7, 'Y', 's', 'Y')
    g.line(5, 23, 7, 17, 'L'); g.line(7, 17, 9, 23, 'L'); g.pal['L'] = '#e8e0c8'
    return g
def hoplite4():  # a red cloak, bronze shield held forward, spear pointed ahead
    g = knight({**JG, 'A': '#b8a070', 'a': '#8a7448', 'T': '#a83030', 'S': '#9a6a28', 's': '#c8903a'}, shield=False, sword=False, plume=False, helm='open')
    g.rows(18, 13, [(1, 3), (1, 4), (2, 5), (2, 5), (3, 5), (3, 5), (3, 5), (4, 5), (4, 5), (4, 5), (4, 5)], 'C'); g.pal['C'] = '#a83030'
    g.text(9, 1, ['  rrrrrr  ', ' rrrrrrrr ']); g.pal['r'] = '#a83030'
    arm_r(g); g.line(12, 18, 30, 15, 'h'); g.text(29, 14, ['w', 'ww', 'w']); round_shield(g, 6, 20, 5.5, 7)
    return g
# ---------- Briar Knight (from the Juggernaut) ----------
def briarknight1():  # green armour wrapped in thorny vines, rose shield, hammer
    g = knight({**JG, 'A': '#6a8a5a', 'a': '#4a6a3e', 'T': '#3a5a2a', 'S': '#3a2a1e', 's': '#5a4230', 'P': '#c83a5a'}, shield=False, sword=False)
    hammer(g); great_shield(g, 's', 'S', 'v'); g.ell(10.5, 21, 3, 3, 'q'); g.ell(10.5, 21, 1.4, 1.4, 'Q'); g.pal.update({'v': '#4a6a2a', 'q': '#c83a5a', 'Q': '#ff8aa0'})
    for x, y in [(4, 16), (7, 25), (15, 17), (16, 26), (9, 6), (17, 10)]: g.px(x, y, 'v')
    return g
def briarknight2():  # antler-branch helm, bark shield, thorned mace
    g = knight({**JG, 'A': '#7a8a6a', 'a': '#5a6a4e', 'T': '#5a3a24', 'S': '#3a2618', 's': '#6a4a30'}, shield=False, sword=False, plume=False)
    g.text(6, 0, ['b   b      b   b', ' b b        b b ', '  bb        bb  ', '   b        b   ']); g.pal['b'] = '#6a4a30'
    great_shield(g, 's', 'S', 'S'); [g.rect(x, 15, x, 27, 'S') for x in (7, 11, 15)]
    arm_r(g); g.rect(22, 9, 22, 17, 'h'); g.ell(22.5, 7, 2.6, 2.6, 'v'); g.text(19, 3, ['  v  ', 'v   v', '     ', '     ', 'v   v']); g.pal['v'] = '#4a6a2a'
    return g
def briarknight3():  # leaf cloak, great shield ringed with spikes, spiked club
    g = knight({**JG, 'A': '#4a5a48', 'a': '#33402f', 'T': '#2a4a22', 'S': '#2e3a28', 's': '#4a6a3a', 'P': '#4a6a3a'}, shield=False, sword=False)
    g.rows(18, 13, [(1, 3), (1, 4), (2, 5), (2, 5), (3, 5), (3, 5), (3, 5), (4, 5), (4, 5), (4, 4)], 'l'); g.pal['l'] = '#3e6a2a'
    great_shield(g, 's', 'S', 'S'); [g.px(x, 13, 'w') for x in (4, 8, 12, 16)]; [g.px(2, y, 'w') for y in (17, 21, 25)]
    arm_r(g); g.line(21, 17, 25, 4, 'h', 2); [g.px(x, y, 'w') for x, y in ((26, 5), (23, 6), (27, 8), (24, 10))]
    return g
def briarknight4():  # rose-red accents and a rose on the helm, hammer and shield
    g = knight({**JG, 'A': '#8a9488', 'a': '#646e62', 'T': '#8a2a3a', 'S': '#2e4a2a', 's': '#4a6a3a', 'P': '#c83a5a'}, shield=False, sword=False, plume=False)
    g.ell(13.5, 2.5, 2.5, 2.5, 'q'); g.px(13, 2, 'Q'); g.text(10, 3, ['vv', ' v']); g.pal.update({'q': '#c83a5a', 'Q': '#ff8aa0', 'v': '#4a6a2a'})
    hammer(g); great_shield(g, 's', 'S', 'q'); g.line(5, 17, 16, 26, 'v'); g.line(5, 26, 16, 17, 'v')
    return g
# ---------- Stormcaller (from the red flame Pyromancer) ----------
PY = {'H': '#9a2e22', 'h': '#741e16', 'R': '#5a1a14', 'Y': '#e0a040'}
def bolt(g, x, y, c='z'):
    g.text(x, y, ['  zz', ' zz ', 'zzzz', '  z ', ' z  ']); g.pal.setdefault('z', '#ffe14d')
def stormcaller1():  # deep blue, staff tipped with a lightning bolt
    g = wizard({'H': '#2a3a7a', 'h': '#1e2a5a', 'R': '#14183a', 'Y': '#ffe14d', 'w': '#4a4a5a'}, top=None)
    bolt(g, 19, 0); g.px(25, 3, 'z'); g.px(18, 6, 'z')
    return g
def stormcaller2():  # storm-grey hat, zig-zag trim, lightning from the raised hand
    g = wizard({'H': '#4a5468', 'h': '#343c4e', 'R': '#2a2e3a', 'Y': '#ffe14d'}, staff=False)
    g.rect(20, 17, 22, 19, '.'); g.rows(18, 13, [(0, 1), (0, 2), (1, 3)], 'h'); g.rect(20, 11, 22, 13, 's')
    bolt(g, 20, 4); g.px(25, 2, 'z'); g.px(19, 2, 'z')
    for i, x in enumerate(range(7, 22)): g.px(x, 28 - (i % 2), 'Y')
    return g
def stormcaller3():  # a little thundercloud riding the staff, rain and a crackle of light
    g = wizard({'H': '#3a4a8a', 'h': '#2a3668', 'R': '#1e2448', 'Y': '#c8d8ff'}, top=None)
    g.ell(21.5, 2.5, 4, 2.4, 'q'); g.ell(19.5, 3, 2.4, 2, 'q'); g.ell(23.5, 3, 2.4, 2, 'Q'); g.pal.update({'q': '#8a94b0', 'Q': '#6a7490'})
    g.px(19, 6, 'z'); g.px(24, 7, 'z'); g.px(25, 5, 'z'); g.pal['z'] = '#ffe14d'
    return g
def stormcaller4():  # navy, no staff: ball lightning in both hands, eyes alight
    g = wizard({'H': '#1e2a5a', 'h': '#141c40', 'R': '#0e1228', 'Y': '#7fe3ff', 'e': '#ffe14d'}, staff=False)
    g.ell(8, 22, 2.6, 2.6, 'z'); g.ell(21, 18, 2.6, 2.6, 'z'); g.px(8, 22, 'Z'); g.px(21, 18, 'Z'); g.px(5, 19, 'z'); g.px(24, 15, 'z')
    g.pal.update({'z': '#7fe3ff', 'Z': '#ffffff'})
    return g
# ---------- Warlock (from the Pyromancer) ----------
def warlock1():  # black-violet robe, horned hat, skull-topped staff
    g = wizard({'H': '#2e1e3a', 'h': '#1e1428', 'R': '#4a1a2a', 'Y': '#a83a4a', 'b': '#8a8a96', 'w': '#3a2a2a'}, top=None)
    g.text(6, 2, ['W      ', 'WW     ', ' WW    ']); g.text(16, 2, ['     W', '    WW', '   WW ']); g.pal['W'] = '#d8d0c0'
    g.text(19, 0, [' WWW ', 'WeWeW', 'WWWWW', ' W W ']); g.pal['e'] = E
    return g
def warlock2():  # a deep hood with red eyes, a dark staff set with a red gem
    g = wizard({'H': '#2a1e2e', 'h': '#1e1422', 'R': '#4a1420', 'Y': '#8a2a3a', 'w': '#2a1e1e', 'c': '#e04848'}, beard=False, hat=None)
    g.ell(13.5, 8.5, 6, 6.5, 'h'); g.rect(8, 9, 19, 15, 'h'); g.rect(10, 9, 17, 15, 'n'); g.px(12, 12, 'r'); g.px(15, 12, 'r'); g.pal.update({'n': '#0e0a10', 'r': '#ff4040'})
    return g
def warlock3():  # crimson and black, a crown of bone, a floating tome
    g = wizard({'H': '#6a1a22', 'h': '#4a1218', 'R': '#1e141a', 'Y': '#d8d0c0'}, staff=False, hat=None)
    g.rect(10, 9, 17, 10, 'W'); [g.px(x, 8, 'W') for x in (10, 12, 14, 16)]; g.pal['W'] = '#d8d0c0'
    g.rect(19, 10, 26, 15, 'v'); g.rect(20, 10, 22, 14, 'p'); g.rect(23, 10, 25, 14, 'p'); g.rect(20, 12, 22, 12, 'q'); g.rect(23, 11, 25, 11, 'q')
    g.px(21, 8, 'm'); g.px(24, 7, 'm'); g.px(26, 8, 'm'); g.pal.update({'v': '#4a1a2a', 'p': '#e0d8c0', 'q': '#a89a80', 'm': '#c84a6a'})
    return g
def warlock4():  # tattered hat, grey beard, a skull held in the hand
    g = wizard({'H': '#2a2228', 'h': '#1e181e', 'R': '#3a1a22', 'Y': '#6a3a4a', 'b': '#8a8a8a', 'w': '#2a1e1a'}, top=None)
    g.text(19, 0, [' w w ', 'wwww ', '  w  ']); g.text(6, 9, ['h  h']); g.text(17, 8, [' h'])
    g.ell(8, 22, 2.4, 2.4, 'W'); g.px(7, 22, 'e'); g.px(9, 22, 'e'); g.pal['W'] = '#d8d0c0'
    return g
# ---------- Arithmetician (from the starry teal Chronomancer) ----------
CH = {'H': '#2a6a6a', 'h': '#1e5050', 'R': '#14383a', 'Y': '#e8e0a0'}
def arithmetician1():  # white and green, abacus staff
    g = wizard({'H': '#e8e2d0', 'h': '#b8b2a0', 'R': '#3a7a4a', 'Y': '#3a8a4a', 'w': '#6a4a2e'}, top=None)
    g.text(18, 0, ['wwwwwww', 'w r g w', 'w g r w', 'w r g w', 'wwwwwww']); g.pal.update({'r': '#c84040', 'g': '#3a8a4a'})
    return g
def arithmetician2():  # scholar: mortarboard, spectacles, a scroll
    g = wizard({**CH}, staff=False, hat=None)
    g.rect(8, 8, 19, 9, 'n'); g.rect(10, 6, 17, 7, 'n'); g.rect(17, 8, 17, 12, 'Y'); g.pal['n'] = '#1e1a26'
    g.rect(11, 12, 16, 12, 'G'); g.px(13, 12, 's'); g.px(14, 12, 's'); g.pal['G'] = '#c8a040'
    g.rect(19, 15, 24, 18, 'p'); g.rect(19, 15, 19, 18, 'q'); g.rect(24, 15, 24, 18, 'q'); g.pal.update({'p': '#e8e0c8', 'q': '#a8986e'})
    return g
def arithmetician3():  # teal with triangles on the robe, compass staff
    g = wizard({**CH}, top=None)
    for x, y in ((9, 22), (17, 24), (10, 26)): g.text(x, y, [' Y ', 'YYY'])
    g.text(19, 0, ['  Y  ', ' Y Y ', ' Y Y ', 'Y   Y'])
    return g
def arithmetician4():  # numerals on the robe, a glowing cube in the hand, no staff
    g = wizard({**CH, 'Y': '#9ff0d0'}, staff=False)
    g.text(9, 23, ['Y Y', ' Y ', 'Y Y']); g.text(16, 23, [' Y ', 'YYY', ' Y '])
    g.rect(20, 13, 23, 16, 'q'); g.rect(20, 13, 23, 13, 'Q'); g.rect(23, 13, 23, 16, 'n'); g.pal.update({'q': '#3ad8b8', 'Q': '#c8fff0', 'n': '#1e8a7a'})
    return g
# ---------- Oracle (from the Chronomancer) ----------
def oracle1():  # white and gold robes, a veil, an eye-topped staff
    g = wizard({'H': '#e8e2d0', 'h': '#c8c0a8', 'R': '#c8a040', 'Y': '#c8a040'}, beard=False, top=None, hat=None)
    g.ell(13.5, 9, 5.5, 5, 'H'); g.rect(8, 9, 19, 16, 'H'); g.rect(10, 10, 17, 14, 's'); g.rect(10, 13, 17, 15, 'v'); g.px(12, 11, 'e'); g.px(15, 11, 'e'); g.pal['v'] = '#d8d0e8'
    g.text(19, 0, [' YYY ', 'YwqwY', ' YYY ']); g.pal.update({'q': '#3a7ab0', 'w': '#6a4a2e'})
    return g
def oracle2():  # blindfolded, white robe, holding a glowing orb
    g = wizard({'H': '#e0dcd0', 'h': '#b8b2a4', 'R': '#8a7ab0', 'Y': '#8a7ab0', 'b': '#c8c4bc'}, staff=False, hat=None)
    g.rect(9, 9, 18, 10, 'u'); g.rect(9, 11, 18, 11, 'v'); g.rect(10, 12, 17, 12, 'v'); g.pal['u'] = '#c8c0d8'; g.pal['v'] = '#3a2a5a'
    g.ell(21.5, 15.5, 2.8, 2.8, 'o'); g.px(21, 15, 'O'); g.pal.update({'o': '#c9a0ff', 'O': '#ffffff'})
    return g
def oracle3():  # a tall headdress and a sun-disk staff
    g = wizard({**CH, 'Y': '#e0b040'}, beard=False, top=None, hat=None)
    g.rect(10, 3, 17, 10, 'Y'); g.rect(11, 2, 16, 2, 'Y'); g.rect(12, 5, 15, 9, 'q'); g.px(13, 6, 'e'); g.px(14, 6, 'e'); g.pal['q'] = '#2a6a6a'
    g.ell(21.5, 3, 3, 3, 'Y'); g.ell(21.5, 3, 1.6, 1.6, 'O'); g.pal['O'] = '#fff0a0'
    return g
def oracle4():  # a hooded robe with an eye emblem, a candle
    g = wizard({'H': '#4a3a6a', 'h': '#36284e', 'R': '#2a1e3a', 'Y': '#c8a040'}, staff=False, hat=None)
    g.ell(13.5, 8.5, 6, 6.5, 'h'); g.rect(8, 9, 19, 15, 'h'); g.rect(10, 10, 17, 15, 's'); g.rect(10, 10, 17, 10, 'S'); g.px(12, 12, 'e'); g.px(15, 12, 'e'); g.rect(10, 14, 17, 15, 'b')
    g.text(11, 22, [' YYY ', 'YwqwY', ' YYY ']); g.pal.update({'w': '#e8e0d0', 'q': '#3a7ab0'})
    g.rect(21, 13, 22, 17, 'c'); g.px(21, 12, 'f'); g.px(21, 11, 'F'); g.pal.update({'c': '#e8e0c8', 'f': '#ff9a3a', 'F': '#ffe680'})
    return g
# ---------- Ninja (from the red-scarfed Assassin) ----------
AS = {'R': '#1e1e28', 'r': '#14141c', 'C': '#8a2028', 'V': '#2a2a34', 'v': '#1e1e26', 'o': '#3a3a46'}
def ninja1():  # full black with a face mask, long red scarf, two kunai
    g = bandit({**AS}, dagger=False, mask=True, cape=False)
    g.text(16, 12, ['CCCCC  ', '  CCCCC', '     CC']); g.text(21, 15, ['  w', ' w ', 'w  ']); g.text(3, 22, ['w  ', ' w ', '  w'])
    return g
def ninja2():  # a violet hood, katana on the back
    g = bandit({**AS, 'C': '#3a2a5a', 'R': '#3a2a5a', 'r': '#2a1e44'}, dagger=False, mask=True)
    g.line(5, 3, 18, 22, 'w'); g.line(5, 4, 17, 22, 'w'); g.rect(4, 2, 6, 4, 'Y')
    g.ell(13.5, 6.5, 6, 5.5, 'R'); g.rect(8, 7, 19, 12, 'R'); g.rect(10, 8, 17, 9, 's'); g.px(12, 9, 'e'); g.px(15, 9, 'e')
    return g
def ninja3():  # grey garb, a shuriken ready to throw
    g = bandit({**AS, 'R': '#4a4a58', 'r': '#33333e', 'V': '#4a4a58', 'o': '#5e5e6c', 'C': '#33333e'}, dagger=False, mask=True)
    g.text(21, 12, [' w ', 'www', ' w ']); g.px(22, 13, 'n'); g.pal['n'] = '#1e1a26'
    return g
def ninja4():  # black with a red headband, a reversed ninjato
    g = bandit({**AS, 'C': '#1e1e28'}, dagger=False, mask=True)
    g.rect(9, 6, 18, 6, 'q'); g.text(4, 6, ['qqq ', ' qq ']); g.pal['q'] = '#c83a3a'
    g.line(21, 20, 21, 26, 'w'); g.line(22, 20, 22, 25, 'w'); g.rect(20, 19, 23, 19, 'Y')
    return g
# ---------- Plaguebringer (from the Assassin) ----------
def plaguebringer1():  # plague doctor: beak mask, wide hat, dark coat, a green vial
    g = bandit({**AS, 'C': '#2a2a24', 'V': '#2a2a24', 'o': '#3a3a30'}, dagger=False, cape=False)
    g.rect(10, 7, 17, 12, 'm'); g.text(17, 9, ['mmm', 'mmmm', 'mmm']); g.px(12, 9, 'g'); g.px(15, 9, 'g'); g.pal.update({'m': '#c8bca0', 'g': '#8be04e'})
    g.rows(5, 4, [(2, 15), (0, 17)], 'R'); g.rect(8, 1, 15, 3, 'R')
    g.rect(21, 15, 22, 18, 'g'); g.px(21, 14, 'k')
    return g
def plaguebringer2():  # a hood and a gas mask, green fumes
    g = bandit({**AS, 'C': '#3a4a2a', 'R': '#3a4a2a', 'r': '#2a3a1e'}, dagger=False, cape=False)
    g.ell(13.5, 6.5, 6, 5.5, 'R'); g.rect(8, 7, 19, 12, 'R'); g.rect(10, 8, 17, 12, 'm'); g.ell(12, 9.5, 1, 1, 'G'); g.ell(16, 9.5, 1, 1, 'G'); g.rect(13, 11, 15, 13, 'n')
    g.pal.update({'m': '#5a5a4a', 'G': '#8be04e', 'n': '#2a2a24'})
    for x, y in ((20, 8), (22, 6), (21, 4), (24, 5), (6, 20), (4, 18)): g.px(x, y, 'G')
    return g
def plaguebringer3():  # ragged and bandaged, a flask and a needle-knife
    g = bandit({**AS, 'C': '#4a4232', 'V': '#4a4232', 'o': '#d8d0b8', 'R': '#d8d0b8', 'r': '#a8a088'}, dagger=False)
    for y in range(15, 22, 2): g.rect(13, y, 15, y, 'v')
    g.rect(6, 19, 8, 22, 'g'); g.px(7, 18, 'k'); g.pal['g'] = '#8be04e'
    g.line(22, 18, 27, 13, 'w')
    return g
def plaguebringer4():  # beaked mask, lantern of green fire
    g = bandit({**AS, 'C': '#2e2a3a', 'V': '#2e2a3a', 'o': '#3e3a4a', 'R': '#2e2a3a'}, dagger=False, cape=False)
    g.rect(10, 7, 17, 12, 'm'); g.text(17, 9, ['mmm', 'mmmm', 'mmm']); g.px(12, 9, 'g'); g.px(15, 9, 'g'); g.pal.update({'m': '#c8bca0', 'g': '#8be04e'})
    g.rect(21, 19, 21, 20, 'k'); g.rect(20, 21, 23, 25, 'l'); g.rect(21, 22, 22, 24, 'g'); g.pal['l'] = '#5a4a2a'
    return g
# ---------- Bard (from the masked juggling Trickster) ----------
TR = {'R': '#2a8a8a', 'r': '#1e6464', 'C': '#c84a6a'}
def mask(g): g.rect(10, 8, 17, 9, 'm'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.pal['m'] = '#2a2030'
def lute(g, x=16, y=17):
    g.ell(x + 2, y + 4, 3.5, 3.2, 'T'); g.ell(x + 2, y + 4, 1, 1, 'n'); g.line(x + 4, y + 2, x + 9, y - 3, 'h'); g.rect(x + 8, y - 5, x + 10, y - 3, 'h')
    g.pal.update({'T': '#b8783a', 'n': '#3a2414', 'h': '#5a3a24'})
def bard1():  # a feathered cap, a lute, the cape
    g = bandit({**TR}, dagger=False)
    mask(g); g.rows(8, 2, [(2, 8), (1, 10), (0, 11)], 'R'); g.text(17, 0, ['  FF', ' FF ', 'FF  ']); g.pal['F'] = '#e8e0c8'
    lute(g)
    return g
def bard2():  # teal bandana, a lute, a bright vest
    g = bandit({**TR, 'V': '#c8a040', 'v': '#9a7a28'}, dagger=False)
    mask(g); lute(g)
    return g
def bard3():  # jester colours and a flute
    g = bandit({**TR, 'V': '#c84a6a', 'o': '#2a8a8a', 'C': '#e8c040'}, dagger=False)
    mask(g); g.line(17, 12, 27, 7, 'Y'); g.pal['Y'] = '#c8a040'; g.px(20, 11, 'n'); g.px(23, 9, 'n'); g.pal['n'] = '#3a2414'
    g.text(5, 0, ['b         b', ' b       b ', '  b     b  ']); g.pal['b'] = '#e8c040'
    return g
def bard4():  # a golden lyre held up
    g = bandit({**TR}, dagger=False)
    mask(g); g.text(20, 9, ['Y   Y', 'Y   Y', 'YllY ', ' YYY ', '  Y  ']); g.pal['l'] = '#e8e0c8'
    return g
# ---------- Mesmer (from the Trickster) ----------
def mesmer1():  # masquerade mask, pink and violet, a hypnotic swirl in hand
    g = bandit({**TR, 'R': '#8a2a7a', 'r': '#5a1a5a', 'C': '#3a1a4a', 'V': '#5a2a6a'}, dagger=False)
    g.rect(9, 8, 18, 9, 'm'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.px(8, 7, 'm'); g.px(19, 7, 'm'); g.pal['m'] = '#ff8ad8'
    g.text(21, 9, [' pp ', 'p  p', 'p pp', ' p  ']); g.pal['p'] = '#ff8ad8'
    return g
def mesmer2():  # feathered mask, long cape, a swinging pendulum
    g = bandit({**TR, 'R': '#2a1a3a', 'C': '#5a1a5a', 'V': '#3a1a4a'}, dagger=False)
    mask(g); g.text(16, 5, ['  FF', ' FF ']); g.pal['F'] = '#ff8ad8'
    g.rows(5, 12, [(2, 7), (1, 6), (0, 5), (0, 5), (0, 4), (0, 4), (0, 4), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (1, 3), (1, 2)], 'C')
    g.line(22, 19, 25, 24, 'Y'); g.ell(25.5, 25.5, 1.6, 1.6, 'p'); g.pal['p'] = '#c9a0ff'
    return g
def mesmer3():  # a hood with glowing eyes, pink mist curling from the hands
    g = bandit({**TR, 'R': '#4a2a5a', 'r': '#36203e', 'C': '#4a2a5a', 'e': '#ff8ad8'}, dagger=False, cape=False)
    g.ell(13.5, 6.5, 6, 5.5, 'R'); g.rect(8, 7, 19, 12, 'R'); g.rect(10, 8, 17, 12, 'n'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.pal['n'] = '#1a1020'
    for x, y in ((22, 16), (24, 14), (23, 12), (25, 11), (5, 23), (4, 21), (6, 25)): g.px(x, y, 'p')
    g.pal['p'] = '#ff8ad8'
    return g
def mesmer4():  # a two-tone jester hat, a mask, a hand mirror
    g = bandit({**TR, 'R': '#8a2a7a', 'C': '#2a8a8a'}, dagger=False)
    mask(g); g.text(5, 0, ['b         c', ' bb     cc ', '  bbbbccc  ', '   bbbccc  ']); g.pal.update({'b': '#8a2a7a', 'c': '#2a8a8a'})
    g.ell(23, 13, 2.2, 2.6, 'Y'); g.ell(23, 13, 1.3, 1.6, 'q'); g.rect(22, 16, 23, 18, 'Y'); g.pal.update({'Y': '#c8a040', 'q': '#c8e8f8'})
    return g

CLASSES = [('Samurai', [samurai1, samurai2, samurai3, samurai4]), ('Dragoon', [dragoon1, dragoon2, dragoon3, dragoon4]),
           ('Hoplite', [hoplite1, hoplite2, hoplite3, hoplite4]), ('Briar Knight', [briarknight1, briarknight2, briarknight3, briarknight4]),
           ('Stormcaller', [stormcaller1, stormcaller2, stormcaller3, stormcaller4]), ('Warlock', [warlock1, warlock2, warlock3, warlock4]),
           ('Arithmetician', [arithmetician1, arithmetician2, arithmetician3, arithmetician4]), ('Oracle', [oracle1, oracle2, oracle3, oracle4]),
           ('Ninja', [ninja1, ninja2, ninja3, ninja4]), ('Plaguebringer', [plaguebringer1, plaguebringer2, plaguebringer3, plaguebringer4]),
           ('Bard', [bard1, bard2, bard3, bard4]), ('Mesmer', [mesmer1, mesmer2, mesmer3, mesmer4])]

# ---------- the owner's adjustments ----------
def behind(g, x0, y0, x1, y1, c):  # a line that only shows where nothing is drawn yet: it passes behind
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(n + 1):
        x = round(x0 + (x1 - x0) * i / n); y = round(y0 + (y1 - y0) * i / n)
        if 0 <= x < 32 and 0 <= y < 32 and g.g[y][x] == '.': g.px(x, y, c)
def dragoon_red():
    g = knight({**BM, 'A': '#a83030', 'a': '#7a2020', 'T': '#c8a040'}, shield=False, sword=False, plume=False)
    g.text(9, 0, ['  a  a  a ', ' aa aa aa ', '  aaaaaa  ', '   aaaa   ']); arm_r(g); lance(g, 23); arm_l(g)
    return g
def oracle_orb():  # Oracle 3's headdress with Oracle 2's orb in place of the staff
    g = wizard({**CH, 'Y': '#e0b040'}, beard=False, staff=False, hat=None)
    g.rect(10, 3, 17, 10, 'Y'); g.rect(11, 2, 16, 2, 'Y'); g.rect(12, 5, 15, 9, 'q'); g.px(13, 6, 'e'); g.px(14, 6, 'e'); g.pal['q'] = '#2a6a6a'
    g.ell(21.5, 15.5, 2.8, 2.8, 'o'); g.px(21, 15, 'O'); g.pal.update({'o': '#c9a0ff', 'O': '#ffffff'})
    return g
def ninja_back():  # Ninja 2 with the katana slung behind the body: hilt over the shoulder, tip by the hip
    g = bandit({**AS, 'C': '#3a2a5a', 'R': '#3a2a5a', 'r': '#2a1e44'}, dagger=False, mask=True)
    g.ell(13.5, 6.5, 6, 5.5, 'R'); g.rect(8, 7, 19, 12, 'R'); g.rect(10, 8, 17, 9, 's'); g.px(12, 9, 'e'); g.px(15, 9, 'e')
    behind(g, 5, 3, 22, 27, 'w'); behind(g, 6, 3, 23, 27, 'w'); g.rect(4, 1, 6, 3, 'Y') if g.g[2][5] == '.' else None
    for (x, y) in ((4, 1), (5, 1), (4, 2), (5, 2), (6, 2), (5, 3)):
        if g.g[y][x] == '.': g.px(x, y, 'Y')
    return g
