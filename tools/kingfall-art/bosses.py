# Kingfall's bosses, drawn as cutout parts like the heroes at the same pixel scale (heroes are about
# 48 px tall, bosses about twice that). The owner picks each boss's look from options.
from pix import P, E

# Humanoid boss rig: pivots relative to the feet. js/rig.js has the same table.
KNIGHT_RIG = {'cape': (-9, -62), 'arm_b': (-15, -58), 'leg_b': (-7, -30), 'leg_f': (7, -30), 'torso': (0, -28),
              'head': (0, -59), 'arm_f': (15, -58)}
KNIGHT_ORDER = ['cape', 'arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'shield', 'weapon', 'arm_f']
KNIGHT_HAND = (0, 25)


def _leg(p):
    g = P(13, 31, (6, 0), p)
    g.rect(1, 0, 10, 13, 'M'); g.rect(8, 0, 10, 13, 'm')
    for y in range(1, 13, 2): g.px(3 + y % 4, y, 'm')
    g.ell(6, 15.5, 5, 3.6, 'A'); g.rect(2, 14, 3, 16, 'l'); g.ell(6, 15.5, 1.5, 1.2, 'Y')
    g.rect(1, 18, 10, 26, 'A'); g.rect(1, 18, 2, 26, 'l'); g.rect(9, 18, 10, 26, 'a'); g.rect(1, 22, 10, 22, 'a')
    g.rows(0, 27, [(1, 10), (0, 12), (0, 12), (0, 12)], 'a'); g.rect(1, 27, 9, 27, 'A')
    return g


def _arm(p):
    g = P(18, 31, (8, 5), p)
    g.ell(8.5, 6, 8.5, 6.2, 'A'); g.ell(6.5, 4, 4, 3, 'l')
    g.rect(1, 7, 16, 7, 'a'); g.rect(1, 10, 16, 10, 'a')  # lames
    g.rect(5, 12, 12, 19, 'M'); g.rect(10, 12, 12, 19, 'm')
    g.ell(8.5, 21, 4.6, 2.8, 'A'); g.px(8, 21, 'Y')
    g.rect(5, 23, 12, 25, 'A'); g.rect(11, 23, 12, 25, 'a')
    g.rows(4, 26, [(0, 9), (0, 9), (0, 9), (1, 8), (2, 7)], 'a'); g.rect(4, 26, 13, 26, 'A')
    return g


def _cape(p, h=58):
    g = P(26, h, (17, 0), p)
    for y in range(h):
        a = max(0, 10 - y // 4)
        g.rect(a, y, 25, y, 'C')
    g.rect(21, 2, 25, h - 1, 'c')
    for x in (4, 9, 14): g.rect(x, 12 + x % 5, x, h - 3, 'c')
    for x in range(26):  # ragged hem, holes burned through
        for y in range(h - (x * 7) % 6, h): g.px(x, y, '.')
    for (x, y) in [(5, 40), (6, 41), (12, 33), (13, 34), (4, 50), (17, 46), (18, 46)]: g.px(x, y, '.')
    return g


def _greatsword(p):
    g = P(15, 70, (7, 58), p)
    g.rows(4, 0, [(3, 3), (2, 4), (1, 5)], 'w')
    g.rect(4, 3, 10, 50, 'w'); g.rect(9, 4, 10, 50, 'v'); g.rect(4, 3, 4, 50, '*')
    g.rect(7, 6, 7, 47, 'v')  # fuller
    for y in range(9, 47, 6): g.px(6, y, 'g'); g.px(6, y + 1, 'G')  # ember runes
    g.rect(0, 51, 14, 53, 'Y'); g.rect(0, 51, 1, 50, 'Y'); g.rect(13, 51, 14, 50, 'Y'); g.rect(1, 53, 13, 53, 'y')
    g.rect(5, 54, 9, 64, 'h'); [g.rect(5, y, 9, y, 'H') for y in range(55, 64, 2)]
    g.ell(7, 66.5, 3.2, 3.2, 'Y'); g.px(7, 66, 'g')
    return g


def _tower(p):
    g = P(30, 50, (15, 24), p)
    outline = [(4, 25), (2, 27), (1, 28)] + [(0, 29)] * 40 + [(1, 28), (2, 27), (3, 26), (5, 24), (7, 22), (10, 19), (13, 16)]
    g.rows(0, 0, outline, 'R')
    g.rows(0, 0, [(a + 2, b - 2) for a, b in outline[2:-2]], 'S')
    g.rect(14, 3, 15, 44, 'R'); g.rect(3, 16, 26, 17, 'R')
    g.rect(2, 3, 2, 42, 's'); g.rect(4, 2, 25, 2, 's')
    g.ell(15, 16.5, 5, 5, 'Y'); g.ell(15, 16.5, 3, 3, 'y')
    g.line(9, 10, 21, 23, 'n'); g.line(10, 10, 22, 23, 'n')  # the sun scratched through
    for (x, y) in [(3, 3), (26, 3), (3, 40), (26, 40), (15, 46)]: g.px(x, y, 'Y')
    for (x, y) in [(8, 30), (9, 31), (20, 36), (22, 28)]: g.px(x, y, 'R')  # dents
    return g


def corvin():
    """Ser Corvin, the Oathless (the owner's pick): blackened plate, a horned great helm, a torn red
    tabard with its sun scratched out, a tower shield, an ember-runed greatsword."""
    p = {'l': '#8a94a4', 'A': '#5e6674', 'a': '#3a404c', 'M': '#4e5462', 'm': '#343944', 'Y': '#a88a40', 'y': '#7a6430',
         'C': '#7a2a2a', 'c': '#561c20', 'w': '#c8ccd4', 'v': '#8a909c', '*': '#eef0f4', 'h': '#4a3424', 'H': '#2e2018',
         'n': '#120e16', 'g': '#ffb040', 'G': '#ff6a1a', 'B': '#d8d0c0', 'b': '#a89c88', 'S': '#4a4048', 's': '#5e5460',
         'R': '#2a242c', 'e': E}
    head = P(36, 38, (18, 37), p)
    for i in range(10):  # horns: thick at the root, curving up and out
        w = 3 if i < 6 else 2
        g = 'B' if i < 7 else 'b'
        y = 15 - int(i * 1.4)
        head.rect(9 - i, y, 9 - i + w, y + 1, g)
        head.rect(26 + i - w, y, 26 + i, y + 1, g)
    for y in range(4, 17, 3): head.px(8 - (16 - y) // 2, y, 'b'); head.px(27 + (16 - y) // 2, y, 'b')
    head.ell(18, 21, 10.5, 12, 'A'); head.rect(8, 20, 28, 31, 'A')
    head.ell(14, 15, 4, 4, 'l'); head.rect(8, 18, 9, 30, 'l')
    head.rect(17, 9, 18, 32, 'a')  # the ridge down the face
    head.rect(12, 21, 30, 23, 'n'); head.rect(20, 22, 29, 22, 'g')  # slit with an ember glow behind it
    for y in (26, 28, 30):
        for x in (22, 25): head.px(x, y, 'o')
    head.rect(26, 18, 28, 31, 'a'); head.rect(8, 31, 28, 32, 'a')
    head.rows(9, 33, [(1, 17), (0, 18), (0, 18), (1, 17), (2, 16)], 'a'); head.rect(10, 33, 26, 33, 'A')
    head.pal['o'] = '#120e16'
    torso = P(38, 35, (19, 33), p)
    torso.ell(19, 11, 18, 11, 'A'); torso.rect(1, 11, 36, 23, 'A'); torso.rect(31, 4, 36, 23, 'a'); torso.ell(10, 7, 6, 4, 'l')
    torso.rows(8, 6, [(2, 19)] + [(1, 20)] * 22, 'C'); torso.rect(27, 6, 29, 28, 'c')
    torso.rect(9, 10, 9, 26, 'c'); torso.rect(16, 12, 16, 27, 'c')  # folds
    torso.ell(19, 14, 4.6, 4.6, 'Y'); torso.ell(19, 14, 2.6, 2.6, 'C')
    for (dx, dy) in [(0, -7), (0, 7), (-7, 0), (7, 0), (-5, -5), (5, 5), (-5, 5), (5, -5)]: torso.px(19 + dx, 14 + dy, 'Y')
    torso.line(12, 7, 26, 21, 'n'); torso.line(13, 7, 27, 21, 'n')  # the sun scratched out
    for (x, y) in [(10, 22), (11, 23), (24, 25), (12, 27)]: torso.px(x, y, '.')  # tears
    torso.rect(1, 24, 36, 26, 'h'); torso.rect(1, 24, 36, 24, 'H'); torso.rect(17, 24, 21, 26, 'Y'); torso.rect(18, 25, 20, 25, 'y')
    torso.rows(3, 27, [(0, 31)] * 4 + [(1, 30)] * 4, 'M')
    torso.rows(9, 27, [(0, 19)] * 8, 'C'); torso.rect(25, 27, 28, 34, 'c')
    for x in (10, 15, 21, 26): torso.px(x, 34, '.'); torso.px(x + 1, 34, '.')
    return {'head': head, 'torso': torso, 'arm_f': _arm(p), 'arm_b': _arm(p), 'leg_f': _leg(p), 'leg_b': _leg(p),
            'cape': _cape(p), 'weapon': _greatsword(p), 'shield': _tower(p)}


RIGS = {}  # the non-humanoid bosses' rigs (see rigs.py); humanoids use 'knight'
BOSSES = {'corvin': corvin}
BOSS_RIG = {'corvin': 'knight'}
