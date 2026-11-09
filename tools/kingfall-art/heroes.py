# Kingfall's heroes: the four looks the owner picked (Nov 2026) from two options each: the plumed
# great-helm knight, the hooded pilgrim with a shadowed face, the witch hunter in a capotain hat and
# scarf, and the scarred, bearded sellsword. Then redrawn bigger (about 48 px tall) on request.
# A hero is a set of cutout parts (see pix.py); cloth, plumes and sashes take the player's colour
# (C/c). Weapons are separate (weapons.py), so every look holds every weapon.
# Letters: l/A/a steel (light, base, shadow), M/m mail, Y/y gold, h/H leather, k boots, n dark slits,
# '*' and 'o' are never shaded (glints, glowing eyes, holes).
from pix import P, E, SKIN

STEEL = {'l': '#c8d0da', 'A': '#a0a8b6', 'a': '#6e7888', 'n': '#1a1622', 'o': '#141018', 'Y': '#c8a040', 'y': '#94742a',
         'M': '#7a8290', 'm': '#565e6c', 'h': '#6a4a2e', 'H': '#4a3222', 'k': '#2e2632', 'e': E, '*': '#f4f0e0'}

# Where each part's pivot sits, relative to the feet (x right, y down). js/rig.js has the same table.
RIG = {'cape': (-4, -27), 'arm_b': (-6, -26), 'leg_b': (-3, -14), 'leg_f': (3, -14), 'torso': (0, -13),
       'head': (0, -26), 'arm_f': (6, -26)}
ORDER = ['cape', 'shield', 'arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'weapon', 'arm_f']  # 'front' poses move the shield after the head
HAND = (0, 10)  # where the front hand grips, from the arm's pivot


def pal(colour, *extra):
    p = {**STEEL, 'C': colour[0], 'c': colour[1]}
    for e in extra: p.update(e)
    return p


def stamp(w, h, pivot, p, rows):
    g = P(w, h, pivot, p)
    g.text(0, 0, rows)
    return g


def cape(p, h=20, main='C', shade='c', ragged=False):
    g = P(12, h, (8, 0), p)
    for y in range(h):
        a = max(0, 4 - y // 4)
        g.rect(a, y, 11, y, main)
    g.rect(9, 1, 11, h - 1, shade)
    for x in range(1, 9, 3): g.rect(x, 6 + x % 4, x, h - 2, shade)  # folds
    for x in range(0, 12, 2): g.px(x, h - 1, '.')
    if ragged:
        for x in range(0, 12, 3): g.px(x, h - 2, '.'); g.px(x + 1, h - 1, '.')
    return g


# ---------------------------------------------------------------- Knight: plumed great helm, tabard with a gold cross
def knight(colour):
    p = pal(colour)
    head = stamp(20, 22, (10, 21), p, [
        '      cCCCC         ',
        '    ccCCCCCCC       ',
        '   cCCCCCCCCCC      ',
        '  cCC  lllAAAAA     ',
        ' cC   lAAAAAAAAAA   ',
        ' c   lAAAAAAAAAAAA  ',
        'c    lAAAAAAAAAAAA  ',
        'c    lAAAAAAAAaAAAA ',
        '     AAAAAAAAAaAAAA ',
        '     AAAAAAAAAaAAAA ',
        '     AAAAAAnnnnnnnnn',
        '     AAAAAAAAAaAAAAA',
        '     AAAAAAAAAaAoAoA',
        '     aAAAAAAAAaAoAoA',
        '     aAAAAAAAAaAAAAA',
        '     aAAAAAAAAaAAAA ',
        '      aAAAAAAAaAAA  ',
        '       aaAAAAAAAa   ',
        '        aaaaaaaa    ',
        '       YaaaaaaaaY   ',
        '       aaaaaaaaaa   ',
        '        aaaaaaaa    '])
    torso = stamp(16, 15, (8, 14), p, [
        '  lAAAAAAAAAAa  ',
        ' lAAAAAAAAAAAAa ',
        'lAAAACCYYCCAAAAa',
        'AAAACCCYYCCCAAaa',
        'AAAACCCYYCCCAAaa',
        'AAAAYYYYYYYYAAaa',
        'AAAACCCYYCCCAAaa',
        'aAAACCCYYCCCcAaa',
        'aAAACCCYYCCCcAa ',
        'hhhhhhhhhYYhhhhh',
        'HhhhhhhhhYYhhhhH',
        ' MMCCCCCCCCCcMm ',
        ' MMCCCCCCCCCcMm ',
        ' MmCCCCCCCCccMm ',
        '  mcCCcCCcCCcm  '])
    leg = lambda: stamp(6, 14, (2, 0), p, [
        'MMMMm ', 'MMMMm ', 'MMMMm ', 'MMMMm ', 'MMMMm ', 'lAAAa ', 'AAYAa ', 'lAAAa ',
        'lAAAa ', 'lAAAa ', 'lAAAa ', 'aAAAAa', 'aAAAAA', 'aaaaaa'])
    arm = lambda: stamp(7, 14, (3, 2), p, [
        ' lAAAa ', 'lAAAAAa', 'AAAAAAa', 'aAAAAaa', ' aaaaa ', '  MMm  ', '  MMm  ',
        '  MMm  ', '  AAa  ', '  MMm  ', ' aAAAa ', ' AAAAa ', ' AAAAa ', '  aaa  '])
    return {'head': head, 'torso': torso, 'arm_f': arm(), 'arm_b': arm(), 'leg_f': leg(), 'leg_b': leg(), 'cape': cape(p)}


# ---------------------------------------------------------------- Pilgrim: deep hood, a shadowed face, two pale eyes
def pilgrim(colour):
    p = pal(colour, SKIN, {'d': '#1c141e', '*': '#f0e8b8', 'r': '#b89a6a', 'R': '#8a7048', 'W': '#e0d8c4', 'w': '#b0a890'})
    head = stamp(20, 22, (10, 21), p, [
        '                    ',
        '       cCCCC        ',
        '     cCCCCCCCC      ',
        '    cCCCCCCCCCC     ',
        '   cCCCCCCCCCCCC    ',
        '  cCCCCCCCCCCCCCC   ',
        '  cCCCCCCCCCCCCCCC  ',
        '  cCCCCCCCcdddddCC  ',
        '  cCCCCCCcdddddddCC ',
        ' cCCCCCCcdddddddddC ',
        ' cCCCCCCcdd*dddd*dd ',
        ' cCCCCCCcdd*dddd*d  ',
        ' cCCCCCCCcdddddddC  ',
        ' cCCCCCCCCcddddddC  ',
        ' ccCCCCCCCCCcdddCC  ',
        '  ccCCCCCCCCCCCCC   ',
        '   ccCCCCCCCCCCC    ',
        '    ccCCCCCCCCc     ',
        '     cCCCCCCCCc     ',
        '      cCCCCCCc      ',
        '      cCCCCCCc      ',
        '      ccccccc       '])
    torso = stamp(16, 18, (8, 14), p, [
        '   CCCCCCCCCC   ',
        '  CCCCCCCCCCCC  ',
        ' CCCCCCCCCCCcCC ',
        'CCCCCCCWWCCCcCCc',
        'CCCCCCWWWWCCcCCc',
        'CCCCCCCwWCCCcCCc',
        'CCCcCCCCCCCCcCCc',
        'CCCcCCCCCCCCcCCc',
        'CCCcCCCCCCCCcCCc',
        'rrrrrrrrrrrrrrrr',
        'RrrrrrrrrrrrrrrR',
        'CCCcCCCCCrCCcCCc',
        'CCCcCCCCCrCCcCCc',
        'CCCcCCCCCRCCcCCc',
        'CCcCCCCCCCCCCcCc',
        'CCcCCCCCCCCCCcCc',
        'cCcCCCcCCCCcCCcc',
        'cc  cc  cc  cc c'])
    sleeve = lambda shade: stamp(7, 14, (3, 2), p, [
        '  CCC  ', ' CCCCC ', ' CCCC' + shade + ' ', ' CCCC' + shade + ' ', ' CCCC' + shade + ' ', ' CCCC' + shade + ' ',
        ' CCCC' + shade + ' ', ' CCCC' + shade + ' ', 'CCCCCC' + shade, 'cccccc ', ' ssss  ', ' ssss  ', ' sSSs  ', '  SS   '])
    leg = lambda: stamp(6, 14, (2, 0), p, [
        'cccc  ', 'cccc  ', 'cccc  ', 'cccc  ', 'cccc  ', 'cccc  ', 'cccc  ', 'WwWw  ',
        'wWwW  ', 'WwWw  ', 'wWwW  ', 'hhhhh ', 'hhhhhh', 'HHHHHH'])
    return {'head': head, 'torso': torso, 'arm_f': sleeve('c'), 'arm_b': sleeve('c'), 'leg_f': leg(), 'leg_b': leg(),
            'cape': cape(p, 19, 'c', 'c', ragged=True)}


# ---------------------------------------------------------------- Witch hunter: buckled capotain, scarf, long coat, bandolier
def hunter(colour):
    p = pal(colour, SKIN, {'K': '#3e3442', 'J': '#2a2230', 'j': '#544a5a', 'W': '#d8d0c0', 'w': '#a89e8c', 'g': '#8a8478'})
    head = stamp(20, 24, (10, 23), p, [
        '      jKKKKKKK      ',
        '      jKKKKKKK      ',
        '      jKKKKKKJ      ',
        '      jKKKKKKJ      ',
        '      jKKKKKKJ      ',
        '      hhhYYYhh      ',
        '      hhhY*Yhh      ',
        '    jKKKKKKKKKJJ    ',
        ' jjKKKKKKKKKKKKKKJJ ',
        '  JJJJJJJJJJJJJJJJ  ',
        '     SSSSSSSSSS     ',
        '     ssssssssss     ',
        '     ssssssessss    ',
        '     sssssssssss    ',
        '     gsssssssss     ',
        '     CCCCCCCCCCC    ',
        '     CCCCCCCCCCCC   ',
        '     cCCCCCCCCCC    ',
        '     ccCCCCCCCcc    ',
        '     WWccccccWW     ',
        '     WWWWWWWWWW     ',
        '      wWWWWWWw      ',
        '       wwwwww       ',
        '       KKKKKK       '])
    head.px(15, 12, 'e')
    torso = stamp(16, 21, (8, 14), p, [
        '  jKKKKKKKKKKJ  ',
        ' jKKKKKKKKKKKKJ ',
        'jKKKKKKWWKKKKKKJ',
        'KhKKKKKWCKKKKKKJ',
        'KKhKKKKWCKKKKKKJ',
        'KKKYKKKKCKKKKKKJ',
        'KKKKhKKKCKKKKKKJ',
        'KKKKKYKKCKKKKKKJ',
        'KKKKKKhKCKKKKKJJ',
        'hhhhhhhhYhhhhhhh',
        'HhhhhhhhYhhhhhhH',
        'KKKKKKKJCKKKKKJJ',
        'KKKKKKKJCKKKKKJJ',
        'KKKKKKKJ KKKKKJJ',
        'KKKKKKJ   KKKKJJ',
        'KKKKKKJ   KKKKJJ',
        'KKKKKJ     KKKJJ',
        'KKKKKJ     KKKJJ',
        'KKKKJ       KKJJ',
        'JJJJ        JJJJ',
        'J J          J J'])
    sleeve = lambda: stamp(7, 14, (3, 2), p, [
        '  jKK  ', ' jKKKJ ', ' KKKKJ ', ' KKKKJ ', ' KKKKJ ', ' KKKKJ ', ' KKKKJ ',
        ' KKKKJ ', ' WWWWw ', ' hhhhH ', ' hhhhH ', ' hhhhH ', ' HhhH  ', '  HH   '])
    leg = lambda: stamp(6, 14, (2, 0), p, [
        'HHHH  ', 'HHHH  ', 'HHHH  ', 'HHHH  ', 'HHHH  ', 'kkkk  ', 'kkkk  ', 'kkkk  ',
        'kkkk  ', 'kkkk  ', 'kkkk  ', 'kkkkk ', 'kkkkkk', 'JJJJJJ'])
    return {'head': head, 'torso': torso, 'arm_f': sleeve(), 'arm_b': sleeve(), 'leg_f': leg(), 'leg_b': leg(),
            'cape': cape(p, 21, 'K', 'J')}


# ---------------------------------------------------------------- Sellsword: shaggy hair, a scar, a beard, fur mantle, sash
def sellsword(colour):
    p = pal(colour, SKIN, {'B': '#3a2a22', 'b': '#56402e', 'x': '#c87a6a', 'D': '#6e4e36', 'd': '#54392a', 'F': '#8a7a64', 'f': '#6a5a48', 'G': '#a8987e'})
    head = stamp(20, 22, (10, 21), p, [
        '                    ',
        '      bBBBBB        ',
        '    bBBBBBBBBB      ',
        '   bBBBBBBBBBBB     ',
        '  bBBBBBBBBBBBBB    ',
        '  BBBBBBBBBBBBBBB   ',
        ' bBBBBBBBBBBBBBBBB  ',
        ' BBBBBBBSSSSSSSBB   ',
        ' BBBBBBsssssssssB   ',
        ' BBBBBsssssssssss   ',
        ' BBBBsSsxssssesss   ',
        ' bBBBsSssxsssssss   ',
        '  BBBBsssxssssssss  ',
        '  bBBsssssssssssS   ',
        '   BBssDDDDDDDDD    ',
        '    bsDDDDsssDDD    ',
        '     DDDDDDDDDDD    ',
        '      DDDDDDDDD     ',
        '       DDDDDDd      ',
        '       ssssss       ',
        '       SSSSSS       ',
        '       SSSSSS       '])
    torso = stamp(16, 15, (8, 14), p, [
        ' GFFFFFFFFFFFFf ',
        'GFFfFFFfFFFfFFFf',
        'FFFFFFFFFFFFFFff',
        'fhhhhhhhhhhhhhHf',
        ' hhhHhhhhhhhhhH ',
        ' hhhhhhhhhhhhhH ',
        ' hhhHhhhhhhhhhH ',
        ' hhhhhhhhhhhhhH ',
        ' hhhHhhhhhhhhhH ',
        'CCCCCCCCCCCCCCcc',
        'CCCCCCCCCCCCCcCc',
        ' HhhhhhhhhhhhhH ',
        ' HhhhhhhhhhhhhH ',
        ' HhhhhhHhhhhhhH ',
        ' HHH HHH HHH HH '])
    for y in (4, 6, 8): torso.px(11, y, 'Y')
    arm = lambda: stamp(7, 14, (3, 2), p, [
        ' GFFFf ', 'GFFFFFf', 'FFfFFFf', ' fFFff ', '  sss  ', '  ssS  ', '  ssS  ',
        ' CCCCc ', ' hhhhH ', ' hhhhH ', ' hhhhH ', ' ssss  ', ' sSSs  ', '  SS   '])
    leg = lambda: stamp(6, 14, (2, 0), p, [
        'HHHH  ', 'HHHH  ', 'HHHH  ', 'HHHH  ', 'HHHH  ', 'HHHH  ', 'hhhh  ', 'hHhh  ',
        'hhhh  ', 'hHhh  ', 'hhhh  ', 'kkkkk ', 'kkkkkk', 'kkkkkk'])
    return {'head': head, 'torso': torso, 'arm_f': arm(), 'arm_b': arm(), 'leg_f': leg(), 'leg_b': leg(),
            'cape': cape(p, 15, 'F', 'f')}


LOOKS = {'knight': knight, 'pilgrim': pilgrim, 'hunter': hunter, 'sellsword': sellsword}
