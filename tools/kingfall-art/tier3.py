# Tier 3 and the finals: the Mirror Knight, the Bastion, the Moth Saint, the Hollow King (both his
# forms) and the Eclipse Drake.
from pix import P, E, humanoid
from tier1 import _copy
from tier2 import _leg, _arm

KN = {'cape': (-9, -62), 'arm_b': (-15, -58), 'leg_b': (-7, -30), 'leg_f': (7, -30), 'torso': (0, -28),
      'head': (0, -59), 'arm_f': (15, -58)}


def _plate_leg(p, w=13, h=31):
    g = P(w, h, (6, 0), p)
    g.rect(1, 0, w - 3, 13, 'A'); g.rect(w - 5, 0, w - 3, 13, 'a'); g.rect(1, 0, 2, 13, 'l')
    g.ell(6, 15.5, 5, 3.4, 'A'); g.rect(2, 14, 3, 16, 'l')
    g.rect(1, 18, w - 3, 26, 'A'); g.rect(1, 18, 2, 26, 'l'); g.rect(w - 4, 18, w - 3, 26, 'a')
    g.rows(0, 27, [(1, w - 3), (0, w - 1), (0, w - 1), (0, w - 1)], 'a')
    return g


def _plate_arm(p):
    g = P(18, 31, (8, 5), p)
    g.ell(8.5, 6, 8.5, 6.2, 'A'); g.ell(6.5, 4, 4, 3, 'l'); g.rect(1, 9, 16, 9, 'a')
    g.rect(5, 12, 12, 19, 'A'); g.rect(10, 12, 12, 19, 'a'); g.ell(8.5, 21, 4.6, 2.8, 'A')
    g.rect(5, 23, 12, 25, 'A'); g.rows(4, 26, [(0, 9), (0, 9), (0, 9), (1, 8), (2, 7)], 'a')
    return g


# ------------------------------------------------------------------ the Mirror Knight
MIRROR_RIG = humanoid(KN, (0, 25), ['cape', 'arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'weapon', 'arm_f'], {'weapon': 35, 'arm_b': 10})


def mirror():
    """The Mirror Knight: armour of silvered glass, faceted and cold, catching every light; a faceless
    helm with one white slit; a cape of hanging shards; a sword of clear glass."""
    p = {'l': '#eef6fa', 'A': '#a8c4d2', 'a': '#6a8aa0', 'D': '#46607a', 'c': '#d0e8f4', 'C': '#8ab0c8', 'w': '#e8f8ff',
         'v': '#a0d8f0', '*': '#ffffff', 'n': '#1e2a36', 'o': '#141018'}
    head = P(26, 34, (13, 33), p)
    head.ell(13, 16, 10, 14, 'A'); head.rect(3, 16, 23, 28, 'A')
    head.tri([(3, 10), (13, 1), (13, 18)], 'l'); head.tri([(13, 1), (23, 10), (13, 18)], 'C')  # facets
    head.tri([(3, 18), (13, 18), (8, 30)], 'C'); head.tri([(13, 18), (23, 18), (18, 30)], 'a')
    head.rect(12, 6, 13, 26, '*'); head.rect(11, 8, 11, 24, 'v')  # the slit of light
    head.rows(5, 29, [(1, 15), (0, 16), (0, 16), (1, 15), (2, 14)], 'a')
    torso = P(38, 35, (19, 33), p)
    torso.ell(19, 11, 18, 11, 'A'); torso.rect(1, 11, 36, 26, 'A')
    for (pts, c) in [([(1, 8), (19, 0), (19, 16)], 'l'), ([(19, 0), (37, 8), (19, 16)], 'C'), ([(1, 8), (19, 16), (4, 26)], 'c'),
                     ([(37, 8), (19, 16), (34, 26)], 'a'), ([(4, 26), (19, 16), (34, 26)], 'A')]:
        torso.tri(pts, c)
    torso.line(19, 0, 19, 26, 'D'); torso.line(1, 8, 37, 8, 'D')
    torso.rows(3, 27, [(0, 31)] * 4 + [(2, 29)] * 4, 'a')
    for x in range(3, 34, 4): torso.line(x, 27, x + 1, 34, 'D')
    sword = P(13, 68, (6, 56), p)
    sword.rows(3, 0, [(3, 3), (2, 4), (1, 5)], 'w'); sword.rect(3, 3, 9, 50, 'v'); sword.rect(3, 3, 4, 50, 'w'); sword.rect(8, 4, 9, 50, 'C')
    sword.rect(6, 6, 6, 46, '*')
    sword.rect(0, 51, 12, 53, 'A'); sword.rect(4, 54, 8, 63, 'D'); sword.ell(6, 65, 2.6, 2.6, 'c')
    cape = P(26, 58, (17, 0), p)  # a cape of hanging shards
    for i, x in enumerate(range(0, 26, 4)):
        top = max(0, 12 - x // 2)
        cape.tri([(x, top), (x + 4, top), (x + 2, 40 + (i * 7) % 16)], 'C' if i % 2 else 'c')
        cape.line(x + 2, top, x + 2, 34 + (i * 7) % 14, 'l' if i % 2 else 'A')
    return {'head': head, 'torso': torso, 'arm_f': _plate_arm(p), 'arm_b': _plate_arm(p), 'leg_f': _plate_leg(p), 'leg_b': _plate_leg(p),
            'cape': cape, 'weapon': sword}


# ------------------------------------------------------------------ the Bastion
GOLEM_RIG = {
    'parts': {'leg_b': ('ground', -18, -40), 'leg_f': ('ground', 18, -40), 'torso': ('body', 0, -38),
              'arm_b': ('torso', -38, -100), 'head': ('torso', 6, -100), 'arm_f': ('torso', 40, -100)},
    'order': ['arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'arm_f'],
    'defaults': {'arm_f': -6, 'arm_b': 6},
}


def bastion():
    """The Bastion: a siege tower that learned to walk. Courses of grey stone bound in black iron, a
    crenellated head with one great furnace eye, arms like towers ending in iron-capped fists, and
    blue-white cores glowing at its knees and shoulders: break them to bring it down."""
    p = {'S': '#7a7480', 's': '#5a5462', 'l': '#9a94a0', 'I': '#3a3640', 'i': '#24202a', 'Y': '#ffb040', 'y': '#ff6a1a',
         'Q': '#a0e0ff', 'q': '#4a8ac8', 'm': '#4e5a3a', 'n': '#141018', 'R': '#6a4a30'}

    def masonry(g, x0, y0, x1, y1, course=6):
        g.rect(x0, y0, x1, y1, 'S')
        for y in range(y0, y1 + 1, course):
            g.rect(x0, y, x1, y, 's')
            off = 0 if (y // course) % 2 else 5
            for x in range(x0 + off, x1, 10): g.rect(x, y, x, min(y1, y + course), 's')
        g.rect(x0, y0, x0 + 1, y1, 'l')
    torso = P(70, 66, (35, 64), p)
    masonry(torso, 4, 10, 65, 60)
    torso.rows(0, 0, [(6, 63)] * 3 + [(2, 67)] * 4 + [(0, 69)] * 3, 'S')  # shoulders
    for x in (0, 10, 20, 30, 40, 50, 60): torso.rect(x, 0, x + 5, 4, 'S')  # crenels across the shoulders
    torso.rect(2, 22, 67, 25, 'I'); torso.rect(2, 44, 67, 47, 'I')   # iron bands
    for x in range(6, 66, 8): torso.px(x, 23, 'i'); torso.px(x, 45, 'i')
    torso.ell(35, 34, 9, 8, 'i'); torso.ell(35, 34, 6, 5, 'y'); torso.ell(35, 34, 3, 3, 'Y')  # the furnace heart
    torso.rect(8, 55, 61, 65, 's')
    for (x, y) in [(10, 14), (54, 52), (60, 16), (20, 50)]: torso.ell(x, y, 2.5, 1.5, 'm')  # moss
    head = P(34, 30, (17, 28), p)
    masonry(head, 2, 6, 31, 28, 5)
    for x in (2, 10, 18, 26): head.rect(x, 0, x + 5, 6, 'S')
    head.ell(19, 16, 7, 6, 'i'); head.ell(19, 16, 5, 4, 'y'); head.ell(20, 15, 2.4, 2.4, 'Y'); head.px(21, 14, '*')
    head.pal['*'] = '#fff0c0'
    arm = lambda: _tower_arm(p, masonry)
    leg = P(30, 42, (15, 2), p)
    masonry(leg, 3, 0, 26, 32, 6); leg.rect(0, 33, 29, 41, 'I'); leg.rect(0, 33, 29, 34, 'i')
    leg.ell(15, 14, 5, 5, 'q'); leg.ell(15, 14, 3, 3, 'Q')  # knee core
    return {'torso': torso, 'head': head, 'arm_f': arm(), 'arm_b': arm(), 'leg_f': leg, 'leg_b': _copy(leg)}


def _tower_arm(p, masonry):
    g = P(28, 74, (14, 6), p)
    masonry(g, 4, 0, 23, 54, 6)
    g.ell(14, 8, 6, 6, 'q'); g.ell(14, 8, 3.5, 3.5, 'Q')  # shoulder core
    g.rect(2, 26, 25, 29, 'I')
    g.rows(0, 55, [(1, 26), (0, 27)] + [(0, 27)] * 14 + [(2, 25), (4, 23)], 'I')  # the iron fist
    g.rect(0, 56, 27, 57, 'i'); [g.rect(x, 60, x, 70, 'i') for x in (7, 14, 21)]
    g.rect(2, 58, 5, 70, 'S')
    return g


# ------------------------------------------------------------------ the Moth Saint
MOTH_RIG = {
    'parts': {'wing_b': ('torso', -2, -58), 'arm_b': ('torso', -8, -60), 'torso': ('body', 0, -26), 'head': ('torso', 2, -62),
              'halo': ('head', 2, -76), 'arm_f': ('torso', 10, -60), 'wing_f': ('torso', -6, -56)},
    'order': ['wing_b', 'wing_f', 'arm_b', 'torso', 'halo', 'head', 'arm_f'],
    'defaults': {'wing_b': 62, 'wing_f': 44, 'arm_f': -30, 'arm_b': 20},
}


def moth():
    """The Moth Saint: a pale, veiled saint in dusty cream robes, hovering on enormous moth wings marked
    with gold-ringed eyes, a cracked halo of candlelight behind her head. Her dust glows."""
    p = {'W': '#d8ccb0', 'w': '#a89a7c', 'l': '#ece4d0', 'V': '#c8c0b0', 'v': '#948a7c', 'B': '#8a7458', 'b': '#5e4c38',
         'Y': '#e8c84a', 'y': '#a88a30', 'K': '#2a2030', 'o': '#141018', 's': '#e8d8c8', 'H': '#fff0b0', 'h': '#e8b84a', 'R': '#6a2a3a'}
    torso = P(26, 44, (13, 42), p)
    torso.rows(0, 0, [(7, 18), (5, 20), (4, 21), (3, 22)] + [(2, 23)] * 10 + [(1, 24)] * 10 + [(0, 25)] * 12 + [(-1, 26)] * 8, 'W')
    torso.rect(18, 4, 24, 43, 'w'); torso.rect(4, 6, 6, 40, 'l')
    torso.rect(11, 6, 13, 40, 'R'); torso.rect(11, 6, 11, 40, 'Y')  # a red stole with gold edge
    for x in range(0, 26, 3): torso.rect(x, 39 + x % 4, x, 43, '.')  # tattered hem, no feet
    head = P(18, 20, (9, 19), p)
    head.ell(9, 9, 7, 8, 'V'); head.rect(2, 9, 16, 19, 'V'); head.rect(12, 3, 16, 19, 'v')  # the veil
    head.ell(10, 9, 4, 5, 'K'); head.px(9, 8, 'H'); head.px(12, 8, 'H')  # darkness under the veil, two lights
    head.rect(5, 1, 13, 2, 'Y'); head.px(9, 0, 'Y')  # a thin gold circlet
    halo = P(30, 30, (15, 15), p)
    halo.ell(15, 15, 14, 14, 'h'); halo.ell(15, 15, 12, 12, '.'); halo.ell(15, 15, 13, 13, 'H'); halo.ell(15, 15, 12, 12, '.')
    for (x, y) in [(4, 6), (25, 9), (8, 26)]: halo.px(x, y, '.')  # cracks in the ring

    def wing(far):
        g = P(64, 72, (54, 24), p)
        body, edge = ('B', 'b') if far else ('W', 'w')
        g.rows(0, 0, [(40, 56)] + [(30 - i * 2, 60) for i in range(14)] + [(4, 62)] * 14 + [(6, 58), (10, 56), (14, 54), (18, 54), (24, 56)], body)
        g.rows(22, 34, [(10, 38), (8, 36), (6, 34)] + [(4, 32)] * 12 + [(6, 30), (8, 28), (10, 26), (14, 22), (18, 20), (20, 20)] + [(22, 22)] * 10, body)
        for y in range(2, 34, 5): g.line(54, 24, max(2, 30 - y), y, edge)  # veins from the root
        g.ell(26, 16, 7, 7, 'y'); g.ell(26, 16, 5, 5, 'Y'); g.ell(26, 16, 3, 3, 'K'); g.px(25, 15, 'l')  # the eye-spot
        g.ell(36, 50, 4, 4, 'y'); g.ell(36, 50, 2.4, 2.4, 'K')
        for x in range(4, 62, 4): g.px(x, 30 + (x * 3) % 3, edge)
        return g
    arm = lambda: _paleArm(p)
    return {'torso': torso, 'head': head, 'halo': halo, 'wing_f': wing(False), 'wing_b': wing(True), 'arm_f': arm(), 'arm_b': arm()}


def _paleArm(p):
    g = P(8, 26, (4, 3), p)
    g.ell(4, 4, 4, 4, 'W'); g.rows(1, 4, [(0, 5)] * 12 + [(-1, 6)] * 4, 'W'); g.rect(4, 6, 6, 19, 'w')
    g.rows(2, 21, [(0, 3), (0, 3), (1, 2), (1, 2), (1, 1)], 's')
    return g


# ------------------------------------------------------------------ the Hollow King
KING_AT = {'cape': (-9, -62), 'arm_b': (-14, -58), 'leg_b': (-6, -30), 'leg_f': (6, -30), 'torso': (0, -28),
           'head': (1, -59), 'arm_f': (14, -58)}
KING_RIG = humanoid(KING_AT, (0, 24), ['cape', 'arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'weapon', 'arm_f'], {'weapon': 50, 'arm_f': -30, 'arm_b': 6})
HOLLOW_AT = {'cape': (-14, -84), 'arm_b': (-26, -80), 'leg_b': (-12, -38), 'leg_f': (12, -38), 'torso': (0, -36),
             'head': (6, -84), 'arm_f': (26, -80)}
HOLLOW_RIG = humanoid(HOLLOW_AT, (0, 40), ['cape', 'arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'weapon', 'arm_f'], {'weapon': 20, 'arm_f': -10, 'arm_b': 20, 'torso': 10, 'head': -6})


def king():
    """The Hollow King, first form: the dead king as he was, an elegant duellist in tarnished gilt plate,
    a tall crown, a long violet mantle trimmed with ermine, a needle-thin rapier."""
    p = {'l': '#e8d090', 'A': '#c8a050', 'a': '#8a6a30', 'D': '#5a4220', 'C': '#5b3a8a', 'c': '#3a2460', 'W': '#e8e2d4', 'k': '#2a2430',
         'w': '#e4eaf0', 'v': '#a8b0bc', 'n': '#1a1420', 'g': '#c060ff', 'R': '#a83030', 's': '#a89a8a', 'S': '#7a6e62'}
    head = P(22, 30, (11, 29), p)
    head.rows(3, 0, [(0, 0), (3, 3), (6, 6), (9, 9), (12, 12), (15, 15)], 'A')
    head.rows(3, 1, [(0, 15)] * 5, 'A'); head.rect(3, 3, 18, 3, 'R'); head.px(10, 3, 'W')  # crown with a ruby
    for x in (3, 7, 11, 15, 18): head.rect(x, 0, x, 1, 'l')
    head.ell(11, 15, 8, 8, 'S'); head.ell(10, 13, 5, 4, 's')  # a grey, sunken face
    head.ell(14, 14, 1.5, 1.6, 'n'); head.px(14, 14, 'g'); head.ell(9, 14, 1.2, 1.4, 'n')
    head.rect(10, 19, 15, 19, 'n')
    head.rows(3, 21, [(0, 15)] * 3 + [(1, 14)] * 3 + [(3, 12)] * 3, 'a')  # gorget
    torso = P(36, 34, (18, 32), p)
    torso.ell(18, 10, 17, 10, 'A'); torso.rect(2, 10, 33, 24, 'A'); torso.ell(10, 6, 6, 4, 'l'); torso.rect(28, 4, 33, 24, 'a')
    torso.rect(16, 2, 19, 24, 'a'); torso.ell(18, 12, 3, 3, 'R')  # a ruby set in the breastplate
    torso.rect(2, 24, 33, 26, 'D'); torso.rows(4, 27, [(0, 27)] * 7, 'C'); torso.rect(24, 27, 31, 33, 'c')
    rapier = P(11, 60, (5, 50), p)
    rapier.rect(5, 0, 5, 44, 'w'); rapier.rect(6, 2, 6, 44, 'v')
    rapier.ell(5, 48, 5, 3, 'A'); rapier.line(0, 47, 5, 52, 'A'); rapier.rect(4, 50, 6, 56, 'D'); rapier.ell(5, 58, 2, 2, 'A')
    cape = P(28, 62, (19, 0), p)
    for y in range(62):
        a = max(0, 10 - y // 4)
        cape.rect(a, y, 27, y, 'C')
    cape.rect(22, 0, 27, 61, 'c'); cape.rect(0, 58, 27, 61, 'W'); [cape.px(x, 59, 'k') for x in range(2, 27, 4)]  # ermine hem
    return {'head': head, 'torso': torso, 'arm_f': _plate_arm(p), 'arm_b': _plate_arm(p), 'leg_f': _plate_leg(p, 12), 'leg_b': _plate_leg(p, 12),
            'cape': cape, 'weapon': rapier}


def hollow():
    """The Hollow King, second form: what the crown made of him. Black ichor has burst the gilt plate
    and swollen him to twice a man's height; the crown has fused into horns; one arm ends in a long
    blade of bone; violet light leaks from every crack."""
    p = {'A': '#8a6a30', 'a': '#5a4220', 'l': '#c8a050', 'X': '#2a1e30', 'x': '#1a1220', 'L': '#3e2e48', 'g': '#c060ff', 'G': '#7a30b0',
         'K': '#d8ccb0', 'k': '#a8987a', 'C': '#3a2460', 'c': '#241638', 'n': '#120e16', 'R': '#a83030'}
    head = P(30, 36, (15, 35), p)
    head.ell(15, 20, 11, 13, 'X'); head.ell(12, 16, 6, 6, 'L')
    for (x0, dx) in [(6, -1), (24, 1)]:  # the crown, fused into horns
        for i in range(12): head.rect(x0 + dx * (i // 3), 10 - i, x0 + dx * (i // 3) + 2, 10 - i, 'A' if i < 6 else 'l')
    head.rect(7, 9, 23, 11, 'A'); head.px(15, 10, 'R')
    head.ell(19, 18, 2.4, 2, 'g'); head.ell(11, 18, 1.8, 1.6, 'g')
    head.rows(9, 25, [(0, 12), (1, 11), (2, 10)], 'x'); head.rect(10, 26, 20, 26, 'G')  # a glowing maw
    torso = P(56, 50, (28, 48), p)
    torso.ell(28, 16, 27, 16, 'X'); torso.ell(28, 32, 24, 17, 'X'); torso.ell(20, 12, 12, 7, 'L')
    for (x, y, w, h) in [(6, 10, 14, 10), (34, 6, 16, 12), (10, 30, 12, 10), (36, 30, 12, 12)]:  # plates of the old armour, burst apart
        torso.rect(x, y, x + w, y + h, 'A'); torso.rect(x, y, x + w, y, 'l'); torso.rect(x + w - 1, y, x + w, y + h, 'a')
    for (x0, y0, x1, y1) in [(20, 8, 26, 30), (30, 20, 44, 26), (14, 24, 22, 40), (40, 18, 34, 40)]: torso.line(x0, y0, x1, y1, 'G')
    torso.ell(28, 22, 3, 3, 'g')
    torso.rows(6, 42, [(0, 43)] * 4 + [(2, 41)] * 4, 'C')
    blade = P(18, 80, (8, 12), p)  # the arm's bone blade, pivot at the wrist
    blade.ell(8, 8, 7, 8, 'X'); blade.rows(3, 14, [(0, 10)] * 50 + [(1, 9)] * 6 + [(2, 8)] * 4 + [(3, 6), (4, 5)], 'K')
    blade.rect(9, 14, 13, 73, 'k'); blade.rect(4, 14, 4, 70, 'l'); blade.pal['l'] = '#ece4d0'
    def big_arm():
        g = P(22, 44, (11, 5), p)
        g.ell(11, 7, 11, 8, 'A'); g.ell(8, 5, 6, 4, 'l'); g.rect(5, 14, 16, 34, 'X'); g.rect(13, 14, 16, 34, 'x')
        g.line(8, 16, 10, 30, 'G'); g.rows(3, 35, [(0, 15)] * 5 + [(1, 14), (2, 13), (4, 11)], 'X')
        for x in (5, 9, 13, 17): g.rect(x, 42, x, 43, 'K')  # claws
        return g
    leg = P(18, 39, (8, 0), p)
    leg.rect(2, 0, 15, 18, 'X'); leg.rect(12, 0, 15, 18, 'x'); leg.ell(9, 20, 7, 4, 'A')
    leg.rect(3, 23, 14, 32, 'X'); leg.line(6, 24, 8, 31, 'G'); leg.rows(0, 33, [(1, 15), (0, 17)] * 3, 'A')
    cape = P(36, 76, (24, 0), p)
    for y in range(76):
        a = max(0, 14 - y // 4)
        cape.rect(a, y, 35, y, 'C')
    cape.rect(28, 0, 35, 75, 'c')
    for x in range(36):
        for y in range(76 - (x * 7) % 9, 76): cape.px(x, y, '.')
    return {'head': head, 'torso': torso, 'arm_f': big_arm(), 'arm_b': big_arm(), 'leg_f': leg, 'leg_b': _copy(leg), 'cape': cape, 'weapon': blade}


# ------------------------------------------------------------------ the Eclipse Drake
DRAKE_RIG = {
    'parts': {'wing_b': ('body', 0, -66), 'leg_bb': ('ground', -34, -30), 'leg_fb': ('ground', 30, -30), 'tail': ('body', -50, -44),
              'body': ('body', 0, -28), 'neck': ('body', 38, -54), 'jaw': ('head', 60, -85), 'head': ('neck', 58, -76),
              'leg_bf': ('ground', -26, -28), 'leg_ff': ('ground', 36, -28), 'wing_f': ('body', 6, -62)},
    'order': ['wing_b', 'leg_bb', 'leg_fb', 'tail', 'body', 'neck', 'jaw', 'head', 'leg_bf', 'leg_ff', 'wing_f'],
    'defaults': {'wing_b': -30, 'wing_f': -18, 'tail': -10},
}


def drake():
    """The Eclipse Drake: a long black dragon with scales like cooled lava, molten orange showing in the
    seams, a pale corona of horns round its head like an eclipsed sun, and tattered violet wings."""
    p = {'D': '#2a2430', 'd': '#1a1620', 'L': '#4a4052', 'O': '#ff8a3a', 'o': '#c84a1a', 'Y': '#ffd23f', 'K': '#e8dcc0', 'k': '#b8a888',
         'M': '#4a2a5a', 'm': '#2e1a3a', 'n': '#120e16', 'B': '#3a3040'}
    body = P(92, 44, (50, 40), p)
    body.ell(46, 20, 44, 18, 'D'); body.ell(40, 12, 30, 7, 'L'); body.ell(52, 30, 30, 8, 'B')
    for (x0, y0, x1, y1) in [(20, 10, 30, 22), (44, 6, 50, 24), (64, 12, 72, 26), (34, 24, 42, 32)]: body.line(x0, y0, x1, y1, 'o')
    for x in range(10, 84, 7): body.tri([(x, 4), (x + 4, 4), (x + 2, -2 + (x % 3))], 'k')  # dorsal spines
    neck = P(32, 36, (4, 30), p)
    neck.rows(0, 0, [(22, 30), (20, 31), (18, 31), (16, 31), (14, 30), (12, 28), (10, 26), (8, 25), (6, 24), (5, 22)] + [(3, 20)] * 8 +
              [(1, 18)] * 8 + [(0, 16)] * 10, 'D')
    neck.line(10, 30, 26, 2, 'o'); neck.rows(14, 0, [(0, 2)] * 3, 'k')
    head = P(42, 30, (6, 24), p)
    head.rows(0, 6, [(6, 18), (2, 28), (0, 34), (0, 38), (0, 40), (0, 41), (0, 41), (0, 40), (1, 38), (2, 34), (4, 28)], 'D')
    head.ell(14, 10, 8, 3, 'L'); head.rect(22, 9, 25, 11, 'Y'); head.px(24, 10, 'n')  # eye
    head.rect(36, 9, 38, 10, 'n'); head.line(10, 14, 40, 15, 'o')  # nostril, a molten seam along the jaw
    for (x, y, l, dx) in [(4, 6, 10, -1), (8, 4, 12, -1), (12, 4, 9, 0), (16, 5, 7, 1)]:  # the corona of horns
        head.line(x, y, x + dx * l // 2 - 2, y - l, 'K'); head.line(x + 1, y, x + dx * l // 2 - 1, y - l + 1, 'k')
    jaw = P(36, 10, (2, 2), p)
    jaw.rows(0, 0, [(0, 34), (1, 33), (2, 31), (4, 28), (8, 22)], 'd'); jaw.rect(3, 0, 33, 0, 'o')
    for x in range(10, 34, 5): jaw.px(x, 0, 'K')
    tail = P(70, 26, (66, 10), p)
    tail.rows(0, 0, [(50, 68), (40, 69), (30, 69), (22, 68), (14, 66), (8, 62), (4, 56), (2, 48), (0, 40), (2, 30), (4, 22), (8, 14)], 'D')
    tail.tri([(0, 6), (10, 4), (4, 16)], 'k'); tail.line(14, 6, 56, 4, 'o')
    for x in range(20, 66, 8): tail.tri([(x, 0), (x + 3, 0), (x + 1, -3)], 'k')

    def wing(far):
        g = P(90, 64, (14, 58), p)  # pivot at the shoulder, membrane spreading up and back
        m, e = ('m', 'n') if far else ('M', 'm')
        g.line(14, 58, 40, 6, 'D'); g.line(15, 58, 41, 6, 'D'); g.line(40, 6, 88, 2, 'D')  # arm and finger
        g.tri([(14, 58), (40, 6), (88, 2)], m)
        for (x, y) in [(60, 4), (74, 3), (86, 2)]: g.line(40, 6, x, y + 2, 'D'); g.line(14, 58, x - 6, y + 30, e)
        for (x, y) in [(52, 30), (70, 20), (80, 12), (40, 40)]: g.ell(x, y, 2, 2, '.')  # tears
        g.tri([(40, 6), (38, 0), (44, 4)], 'K')
        return g

    def leg(fore):
        g = P(18, 34, (9, 4), p)
        g.ell(9, 8, 9, 8, 'D'); g.rect(4, 12, 13, 26, 'D'); g.rect(11, 12, 13, 26, 'd')
        g.rows(2, 27, [(0, 13), (0, 15), (0, 15)], 'D'); [g.rect(x, 30, x + 1, 32, 'K') for x in (3, 8, 13)]
        return g
    return {'body': body, 'neck': neck, 'head': head, 'jaw': jaw, 'tail': tail, 'wing_f': wing(False), 'wing_b': wing(True),
            'leg_ff': leg(True), 'leg_fb': leg(True), 'leg_bf': leg(False), 'leg_bb': leg(False)}
