# Tier 1 bosses after Ser Corvin: the Mire Mother (a giant toad) and the Bellwarden (a belfry ghoul
# with a great bell). Same rules as every sprite: matte, dark outlines from render(), three tones a
# material at most, muted colours with small glowing accents.
from pix import P, E

# ------------------------------------------------------------------ the Mire Mother
MIRE_RIG = {
    'parts': {'hind_b': ('ground', -26, -14), 'fore_b': ('ground', 14, -18), 'body': ('body', -6, -8),
              'mouth': ('body', 20, -33), 'jaw': ('body', 14, -30), 'head': ('body', 22, -30),
              'hind_f': ('ground', -20, -10), 'fore_f': ('ground', 20, -14)},
    'order': ['hind_b', 'fore_b', 'body', 'mouth', 'jaw', 'head', 'hind_f', 'fore_f'],
    'defaults': {},
}


def mire():
    """The Mire Mother: a bloated, warty toad the size of a cart, olive and mud-brown with a pale
    belly, clusters of eggs on her back, reeds and a bone crown on her brow, yellow slit eyes."""
    p = {'G': '#5e6e3c', 'g': '#435029', 'H': '#7a8a4e', 'B': '#b8ac7c', 'b': '#948a60', 'w': '#8a9a56',
         'E': '#c8d4a0', 'e': '#56603a', 'Y': '#e8c84a', 'o': '#141018', 'n': '#1e1a16', 'R': '#6a5a34', 'r': '#8a7a48',
         'M': '#3e4a30', 'K': '#d8d0c0', 'k': '#a89c88', 'P': '#7a2a34', 'p': '#4a1820', 'T': '#c86a7a'}
    body = P(78, 50, (42, 46), p)
    body.ell(40, 26, 37, 22, 'G')
    body.ell(52, 34, 22, 13, 'B'); body.ell(56, 38, 16, 8, 'b')       # pale belly toward the front
    body.ell(26, 14, 18, 9, 'H')                                       # lit back
    for (x, y) in [(14, 20), (20, 28), (30, 22), (36, 30), (44, 18), (24, 34), (12, 30), (50, 24), (40, 10), (18, 12)]:
        body.ell(x, y, 2.2, 1.6, 'w'); body.px(x + 1, y + 1, 'g')      # warts
    for (x, y, r) in [(22, 6, 5), (31, 4, 4.5), (14, 9, 4), (27, 11, 3.5), (37, 7, 3.5), (18, 3, 3)]:  # eggs
        body.ell(x, y, r, r, 'E'); body.px(x, y, 'e')
    for x in range(6, 30, 5):  # moss hanging off her flank
        body.rect(x, 30 + x % 3, x, 38 + (x * 7) % 6, 'M')
    body.rows(2, 44, [(4, 30), (8, 26)], 'g')
    head = P(52, 30, (14, 26), p)
    head.ell(26, 17, 25, 12, 'G'); head.ell(22, 12, 16, 7, 'H')
    head.ell(34, 6, 7, 6, 'G'); head.ell(34, 5, 4.5, 4, 'Y'); head.rect(34, 2, 34, 8, 'o')  # near eye
    head.ell(20, 7, 5.5, 4.5, 'g'); head.ell(20, 6, 3, 2.5, 'Y'); head.rect(20, 4, 20, 7, 'o')  # far eye
    head.px(48, 13, 'n'); head.px(45, 12, 'n')  # nostrils
    head.line(4, 22, 50, 20, 'n'); head.line(4, 23, 49, 21, 'g')  # the long mouth
    for (x, y) in [(10, 14), (14, 18), (40, 15), (28, 16)]: head.px(x, y, 'w')
    for i, x in enumerate((24, 27, 30)):  # a crown of bones and reeds between the eyes
        head.rect(x, 0, x, 3 + i % 2, 'K' if i != 1 else 'R'); head.px(x, 0, 'k')
    jaw = P(46, 12, (2, 2), p)
    jaw.rows(0, 0, [(0, 44), (1, 44), (2, 43), (3, 41), (5, 38), (8, 34), (12, 28)], 'B')
    jaw.rect(4, 0, 43, 0, 'g'); jaw.rows(14, 4, [(0, 20), (2, 16)], 'b')
    mouth = P(34, 12, (2, 2), p)  # the inside of her mouth, seen when the jaw drops
    mouth.rows(0, 0, [(0, 32)] * 7 + [(2, 30), (4, 28), (8, 24)], 'p'); mouth.ell(16, 5, 10, 3, 'P'); mouth.ell(14, 4, 5, 1.6, 'T')
    fore = lambda: _limb(p, 12, 20, (5, 2), [(3, 8)] * 10 + [(3, 9)] * 4 + [(1, 11), (0, 11), (0, 11)], 'G', 'g')
    hind = P(34, 26, (16, 4), p)
    hind.ell(16, 10, 15, 10, 'G'); hind.ell(12, 7, 9, 5, 'H')
    hind.rows(18, 16, [(0, 10), (0, 12), (-2, 14), (-4, 15), (-6, 15)], 'G'); hind.rect(14, 24, 33, 25, 'g')
    for x in (16, 22, 28): hind.px(x, 25, 'n')
    return {'body': body, 'head': head, 'jaw': jaw, 'mouth': mouth, 'fore_f': fore(), 'fore_b': fore(), 'hind_f': hind, 'hind_b': _copy(hind)}


def _limb(p, w, h, pivot, spans, c, shade):
    g = P(w, h, pivot, p)
    g.rows(0, 0, spans, c)
    g.rect(spans[0][1], 0, spans[0][1], len(spans) - 4, shade)
    for x in range(0, w, 3): g.px(x, h - 1, 'n')
    return g


def _copy(part):
    q = P(part.w, part.h, part.pivot, part.pal)
    q.g = [row[:] for row in part.g]
    return q


# ------------------------------------------------------------------ the Bellwarden
BELL_RIG_AT = {'cape': (-10, -50), 'arm_b': (-8, -46), 'leg_b': (-6, -26), 'leg_f': (6, -26), 'torso': (0, -24),
               'head': (10, -46), 'arm_f': (12, -46)}


BELL_RIG = {
    'parts': {'leg_b': ('ground', -6, -26), 'leg_f': ('ground', 6, -26), 'torso': ('body', 0, -24),
              'cape': ('torso', -10, -50), 'arm_b': ('torso', -8, -46), 'arm_f': ('torso', 12, -46), 'head': ('torso', 10, -46),
              'bell': ('torso', -14, -62)},  # the bell rides his back, its yoke over his shoulders
    'order': ['cape', 'arm_b', 'leg_b', 'leg_f', 'torso', 'bell', 'head', 'arm_f'],
    'defaults': {'torso': 28, 'head': -24, 'arm_f': -12, 'arm_b': 10, 'leg_f': -14, 'leg_b': 10, 'cape': -18, 'bell': -22},
    'front': {'bell': ['head', 'arm_f']},
}


def bellwarden():
    """The Bellwarden: a gaunt grey ghoul bent double under a hood of rotten sacking, all ribs and long
    arms, dragging a cracked bronze bell by its yoke. A violet witch-light burns inside the bell."""
    p = {'S': '#9a968c', 's': '#6e6a62', 'L': '#bab6aa', 'C': '#4a3e36', 'c': '#2e2622', 'k': '#5e4e3e',
         'Z': '#b07a3a', 'z': '#7a5226', 'X': '#d8a050', 'v': '#e070c0', 'V': '#8a3a7a', 'o': '#141018', 'n': '#120e16',
         'h': '#4a3424', 'I': '#3a3440', 'e': '#e8e0b0', 'R': '#5a4a3a'}
    torso = P(30, 30, (12, 28), p)
    torso.ell(16, 12, 13, 11, 'S'); torso.rect(6, 12, 22, 26, 'S'); torso.rect(18, 4, 24, 24, 's')
    for y in (10, 14, 18, 22): torso.rect(8, y, 18, y, 's')                     # ribs
    torso.rows(5, 24, [(0, 18), (-1, 19), (-2, 20), (-2, 20), (-1, 18), (0, 16)], 'C')  # a rag round the hips
    for x in (5, 9, 14, 19): torso.px(x, 29, '.')
    torso.rows(0, 0, [(6, 22), (3, 24), (1, 26), (0, 27), (0, 27), (1, 24), (2, 18)], 'C')  # sacking over the back
    torso.rect(2, 2, 6, 8, 'c')
    head = P(22, 24, (6, 22), p)
    head.rows(0, 0, [(4, 15), (2, 17), (1, 19), (0, 20), (0, 20), (0, 20), (0, 19), (1, 18), (2, 16)], 'C')  # hood
    head.ell(13, 12, 7, 8, 'S'); head.ell(11, 9, 4, 4, 'L')
    head.ell(15, 11, 2, 2.4, 'o'); head.px(15, 11, 'e'); head.ell(10, 11, 1.4, 2, 'o')   # hollow eyes, one lit
    head.rows(9, 17, [(0, 9), (1, 9), (2, 8), (3, 7)], 's'); head.rect(11, 18, 17, 18, 'n')  # long jaw, a slot of a mouth
    for x in (12, 14, 16): head.px(x, 19, 'L')
    head.rect(0, 6, 3, 16, 'c'); head.rect(0, 17, 2, 21, 'C')
    arm = lambda: _bonearm(p)
    leg = P(8, 27, (3, 0), p)
    leg.rect(1, 0, 5, 12, 'S'); leg.rect(4, 0, 5, 12, 's'); leg.rect(1, 6, 6, 12, 'k')  # rag wraps
    leg.rect(2, 13, 5, 22, 'S'); leg.rect(1, 16, 6, 19, 'k'); leg.rows(0, 23, [(1, 6), (0, 7), (0, 7), (0, 7)], 's')
    cape = P(20, 44, (14, 0), p)
    for y in range(44):
        a = max(0, 8 - y // 5)
        cape.rect(a, y, 19, y, 'C')
    cape.rect(16, 0, 19, 43, 'c')
    for x in range(20):
        for y in range(44 - (x * 5) % 7, 44): cape.px(x, y, '.')
    bell = P(44, 44, (22, 3), p)  # pivot at the yoke ring, held from above
    bell.ell(22, 2, 3, 3, 'h'); bell.rect(19, 3, 25, 6, 'h')
    for y in range(6, 41):
        u = (y - 6) / 32
        hw = round(7 + 9 * u ** 1.5) if y < 38 else 20 - (y - 38)  # crown, waist, flared lip
        if y < 9: hw = 4 + (y - 6) * 1.2
        hw = int(hw)
        bell.rect(22 - hw, y, 22 + hw, y, 'Z')
        bell.rect(22 + hw // 3, y, 22 + hw, y, 'z')                     # the shadowed side
        if y > 7: bell.rect(22 - hw + 1, y, 22 - hw + 2, y, 'X')       # a lit edge
    for y in (14, 32, 36): bell.rect(22 - int(7 + 9 * ((y - 6) / 32) ** 1.5), y, 22 + int(7 + 9 * ((y - 6) / 32) ** 1.5), y, 'z')  # bands
    bell.line(25, 10, 21, 20, 'n'); bell.line(21, 20, 25, 29, 'n'); bell.line(25, 29, 22, 37, 'n')  # the crack
    bell.rows(8, 40, [(4, 24), (7, 21), (11, 17)], 'V'); bell.rows(12, 40, [(4, 16), (6, 14)], 'v')  # witch-light below
    for (x, y) in [(15, 22), (17, 26), (14, 30), (29, 24)]: bell.px(x, y, 'v')  # runes
    return {'torso': torso, 'head': head, 'arm_f': arm(), 'arm_b': arm(), 'leg_f': leg, 'leg_b': _copy(leg),
            'cape': cape, 'bell': bell}


def _bonearm(p):
    g = P(9, 34, (4, 2), p)
    g.ell(4, 3, 4, 3, 'C')
    g.rect(3, 4, 5, 15, 'S'); g.rect(5, 4, 5, 15, 's'); g.ell(4, 16, 2.4, 2, 'S')
    g.rect(3, 17, 5, 27, 'S'); g.rect(5, 17, 5, 27, 's')
    g.rows(1, 28, [(1, 6), (0, 7), (0, 7), (1, 6), (1, 2), (4, 5)], 'S')  # big hand, long fingers
    return g
