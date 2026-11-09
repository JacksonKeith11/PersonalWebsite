# Tier 2 bosses: the Twin Headsmen (the Hook and the Axe), the Briar Wolf, the Ashen Alchemist and
# the Gravewyrm. Same rules as every sprite (docs/game-art.md): matte, three tones a material,
# muted colours with small glowing accents.
from pix import P, E, humanoid
from tier1 import _copy

SKINP = {'s': '#c8a888', 'S': '#94765c', 'L': '#dcc0a0'}


def _leg(p, w=9, h=27, thigh='T', boot='k', wrap=None):
    g = P(w, h, (w // 2 - 1, 0), p)
    g.rect(1, 0, w - 3, h - 9, thigh); g.rect(w - 4, 0, w - 3, h - 9, thigh.lower() if thigh.lower() in p else thigh)
    if wrap: [g.rect(1, y, w - 3, y, wrap) for y in range(4, h - 9, 4)]
    g.rows(0, h - 8, [(1, w - 3)] * 4 + [(0, w - 2), (0, w - 1), (0, w - 1), (0, w - 1)], boot)
    return g


def _arm(p, w, h, skin='s', shade='S', cuff=None, glove=None):
    g = P(w, h, (w // 2, 3), p)
    g.ell(w / 2, 4, w / 2, 4, skin)
    g.rect(w // 2 - 2, 4, w // 2 + 2, h - 6, skin); g.rect(w // 2 + 1, 6, w // 2 + 2, h - 6, shade)
    if cuff: g.rect(w // 2 - 2, h - 10, w // 2 + 2, h - 8, cuff)
    g.rows(w // 2 - 3, h - 6, [(0, 6), (0, 6), (0, 6), (1, 5), (1, 5), (2, 4)], glove or skin)
    return g


# ------------------------------------------------------------------ the Twin Headsmen
HOOK_AT = {'cape': (-6, -60), 'arm_b': (-11, -57), 'leg_b': (-5, -30), 'leg_f': (5, -30), 'torso': (0, -28),
           'head': (1, -57), 'arm_f': (11, -57)}
AXE_AT = {'cape': (-10, -70), 'arm_b': (-22, -64), 'leg_b': (-10, -30), 'leg_f': (10, -30), 'torso': (0, -28),
          'head': (3, -70), 'arm_f': (22, -64)}
HOOK_RIG = humanoid(HOOK_AT, (0, 26), ['arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'weapon', 'arm_f'], {'weapon': 70, 'arm_f': -20, 'arm_b': 14})
AXE_RIG = humanoid(AXE_AT, (0, 28), ['arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'weapon', 'arm_f'], {'weapon': -20, 'arm_f': -10, 'arm_b': -30})


def _hood(p, w, h, eyes):
    g = P(w, h, (w // 2, h - 1), p)
    g.ell(w / 2, h / 2 - 1, w / 2 - 1, h / 2 - 1, 'H'); g.rect(2, h // 2, w - 3, h - 2, 'H')
    g.ell(w / 2 - 2, h / 2 - 4, w / 4, h / 5, 'J')  # a sheen on the leather
    g.rect(w - 4, 4, w - 2, h - 2, 'h')
    for (x, y) in eyes: g.rect(x, y, x + 2, y + 1, 'o'); g.px(x + 1, y, 'r')
    for y in range(5, h - 2, 4): g.px(w // 2 - 4, y, 'h')  # stitches up the back
    return g


def hook():
    """The Hook: tall, lean and quick. A stitched black hood, bare corded arms, a leather apron hung
    with keys, a heavy hook on a chain."""
    p = {**SKINP, 'H': '#2e2830', 'h': '#1e1a22', 'J': '#46404a', 'o': '#141018', 'r': '#e04040',
         'A': '#6a4a30', 'a': '#4a3222', 'T': '#3e3440', 't': '#2a2230', 'k': '#2a2024', 'M': '#8a929e', 'm': '#5e6672',
         'Y': '#a88a40', 'n': '#120e16'}
    head = _hood(p, 18, 22, [(10, 9), (14, 9)])
    torso = P(24, 30, (12, 28), p)
    torso.ell(12, 9, 11, 8, 's'); torso.rect(2, 9, 21, 22, 's'); torso.rect(17, 4, 21, 22, 'S')
    torso.rect(9, 6, 9, 12, 'S'); torso.rect(4, 14, 18, 14, 'S')  # sternum, the line of the ribs
    torso.rows(3, 12, [(2, 16), (1, 17)] + [(0, 18)] * 16, 'A'); torso.rect(16, 13, 18, 29, 'a')  # the apron
    torso.line(4, 4, 20, 13, 'a'); torso.line(5, 4, 21, 13, 'a')  # its strap
    for (x, y) in [(6, 20), (8, 22), (10, 20)]: torso.px(x, y, 'Y')  # keys
    torso.rect(2, 22, 21, 23, 'k')
    hookp = P(13, 40, (6, 4), p)  # held by the chain's end; the hook swings below the fist
    for y in range(0, 26, 3): hookp.rect(5, y, 7, y + 1, 'M'); hookp.px(6, y + 2, 'm')
    hookp.rows(0, 26, [(4, 9), (3, 10), (2, 11), (1, 11), (0, 3), (0, 3), (0, 3), (1, 4), (2, 6), (4, 8), (7, 9), (8, 9)], 'M')
    hookp.rect(9, 26, 11, 30, 'm'); hookp.px(0, 30, '*'); hookp.pal['*'] = '#e8ecf2'
    return {'head': head, 'torso': torso, 'arm_f': _arm(p, 9, 30, cuff='a'), 'arm_b': _arm(p, 9, 30, cuff='a'),
            'leg_f': _leg(p, wrap='a'), 'leg_b': _leg(p, wrap='a'), 'weapon': hookp}


def axe():
    """The Axe: a slab of a man, belly and shoulders bare, a black hood over a too-small head, a great
    two-handed headsman's axe gone brown with rust."""
    p = {**SKINP, 'H': '#2e2830', 'h': '#1e1a22', 'J': '#46404a', 'o': '#141018', 'r': '#e04040',
         'A': '#5a4a3a', 'a': '#3e3226', 'T': '#4a3a32', 't': '#32261e', 'k': '#2a2024', 'M': '#8a929e', 'm': '#5e6672',
         'w': '#a87a52', 'R': '#7a4a2a', 'x': '#8a2a2a', 'n': '#120e16', 'Y': '#a88a40'}
    head = _hood(p, 16, 20, [(9, 8), (12, 8)])
    torso = P(44, 40, (22, 38), p)
    torso.ell(22, 14, 21, 13, 's'); torso.ell(22, 26, 19, 13, 's'); torso.rect(3, 14, 40, 26, 's')
    torso.ell(30, 26, 11, 10, 'S'); torso.ell(14, 10, 8, 4, 'L')  # belly in shadow, a lit shoulder
    torso.rect(12, 16, 32, 16, 'S'); torso.px(22, 22, 'S')
    torso.rows(4, 32, [(0, 35)] * 3 + [(1, 34)] * 5, 'T'); torso.rect(4, 32, 39, 33, 'A'); torso.rect(20, 32, 23, 33, 'Y')
    torso.line(6, 4, 14, 30, 'a')  # a rope crossing his chest
    for (x, y) in [(31, 10), (33, 12), (12, 22)]: torso.px(x, y, 'x')  # scars
    axep = P(34, 66, (12, 44), p)  # pivot on the haft where the hands grip
    axep.rect(11, 2, 14, 65, 'w'); axep.rect(13, 2, 14, 65, 'R'); axep.rect(10, 60, 15, 63, 'a')
    for y in range(4, 30):  # a bearded blade: narrow at the haft, flaring to a curved edge
        u = (y - 4) / 25
        reach = int(8 + 12 * (1 - (2 * u - 1) ** 2) + (6 * u if u > 0.5 else 0))
        axep.rect(15, y, 15 + reach, y, 'm')
        axep.rect(15 + reach - 3, y, 15 + reach, y, 'M')       # the honed edge
    axep.rect(15, 4, 17, 29, 'D'); axep.pal['D'] = '#4a4e58'  # where the blade meets the haft
    for (x, y) in [(20, 10), (24, 16), (21, 22), (27, 20), (19, 26)]: axep.px(x, y, 'R')  # rust
    return {'head': head, 'torso': torso, 'arm_f': _arm(p, 14, 34, cuff='a'), 'arm_b': _arm(p, 14, 34, cuff='a'),
            'leg_f': _leg(p, 12, 30, 'T', 'k'), 'leg_b': _leg(p, 12, 30, 'T', 'k'), 'weapon': axep}


# ------------------------------------------------------------------ the Briar Wolf
WOLF_RIG = {
    'parts': {'leg_bb': ('ground', -28, -30), 'leg_fb': ('ground', 18, -32), 'tail': ('body', -40, -46), 'body': ('body', -6, -30),
              'neck': ('body', 22, -48), 'jaw': ('neck', 40, -46), 'head': ('neck', 34, -52), 'mane': ('body', 8, -54),
              'leg_bf': ('ground', -22, -28), 'leg_ff': ('ground', 24, -30)},
    'order': ['leg_bb', 'leg_fb', 'tail', 'body', 'neck', 'jaw', 'head', 'mane', 'leg_bf', 'leg_ff'],
    'defaults': {'tail': -20},
}


def wolf():
    """The Briar Wolf: a gaunt wolf as big as a horse, dark grey fur gone to bramble along its spine,
    thorns of old bone, red eyes. Thorn-vines wrap its legs and trail from its jaws."""
    p = {'F': '#4e4a50', 'f': '#36323a', 'G': '#68646a', 'B': '#2e3a26', 'b': '#1e2818', 'V': '#4a5a34', 'K': '#d8d0c0',
         'k': '#a89c88', 'r': '#ff4040', 'R': '#8a1e1e', 'o': '#141018', 'n': '#120e16', 'W': '#e8e0d0', 'P': '#5a1e24'}
    body = P(64, 34, (34, 30), p)
    body.ell(32, 16, 31, 14, 'F'); body.ell(26, 10, 22, 6, 'G'); body.ell(40, 24, 18, 7, 'f')
    for x in range(6, 58, 4): body.rect(x, 26 + (x % 3), x, 30 + (x * 3) % 4, 'f')  # shaggy underside
    for x in range(4, 56, 6): body.px(x, 6 + (x * 5) % 4, 'f')
    neck = P(30, 26, (6, 20), p)
    neck.rows(0, 0, [(6, 20), (4, 22), (2, 24), (1, 25), (0, 26)] + [(0, 27)] * 16 + [(2, 24), (4, 20)], 'F')
    neck.ell(14, 6, 9, 4, 'G'); neck.rect(18, 16, 27, 22, 'f')
    head = P(32, 20, (4, 14), p)
    head.rows(0, 2, [(4, 12), (2, 18), (1, 24), (0, 28), (0, 30), (0, 31), (0, 31), (0, 30), (1, 29), (2, 27), (4, 24), (6, 18)], 'F')
    head.ell(12, 6, 8, 3, 'G'); head.rows(4, 0, [(0, 2), (0, 3), (1, 3)], 'F'); head.rows(10, 0, [(0, 2), (0, 3), (1, 3)], 'f')  # ears
    head.rect(17, 6, 19, 7, 'R'); head.px(18, 6, 'r')  # eye
    head.rect(29, 6, 31, 8, 'o')  # nose
    head.rows(16, 11, [(0, 15), (1, 14)], 'n')  # the line of the mouth
    for x in (20, 24, 28): head.px(x, 12, 'W')
    jaw = P(26, 9, (2, 2), p)
    jaw.rows(0, 0, [(0, 24), (1, 24), (2, 22), (4, 19), (7, 15)], 'f'); jaw.rect(4, 0, 24, 0, 'P')
    for x in (8, 14, 20): jaw.px(x, 0, 'W')
    jaw.line(8, 4, 2, 8, 'V')  # a vine trailing from the jaw
    mane = P(46, 24, (24, 18), p)  # bramble along the spine and shoulders
    for (x, y, r) in [(8, 16, 6), (16, 12, 7), (25, 10, 8), (34, 12, 7), (41, 16, 5)]:
        mane.ell(x, y, r, r * 0.8, 'B'); mane.ell(x - 1, y - 2, r * 0.5, r * 0.4, 'V')
    for (x, y, l) in [(6, 9, 4), (14, 4, 5), (24, 1, 6), (33, 3, 5), (41, 9, 4), (20, 6, 3), (29, 6, 3)]:
        mane.line(x, y + l, x + 1, y, 'K'); mane.px(x + 1, y, 'k')  # thorns of bone
    tail = P(30, 12, (28, 4), p)
    tail.rows(0, 0, [(14, 29), (6, 29), (2, 28), (0, 26), (1, 20), (4, 14), (8, 10)], 'F')
    for (x, y) in [(6, 2), (12, 1), (18, 3)]: tail.line(x, y, x - 2, y - 2, 'K')
    tail.rows(0, 2, [(2, 8), (0, 6)], 'B')

    def leg(fore):
        g = P(12, 32, (6, 2), p)
        g.ell(6, 6, 6, 6, 'F'); g.rect(3, 6, 8, 18, 'F') if fore else g.rows(2, 6, [(0, 7)] * 8 + [(1, 7), (2, 7), (3, 7), (3, 7)], 'F')
        g.rect(4, 18, 7, 28, 'F'); g.rect(6, 8, 8, 28, 'f')
        g.rows(3, 28, [(0, 5), (0, 7), (0, 8), (0, 8)], 'f'); g.px(11, 31, 'K'); g.px(9, 31, 'K')
        for y in (12, 20, 24): g.line(3, y, 8, y + 2, 'V')  # vines round the leg
        return g
    return {'body': body, 'neck': neck, 'head': head, 'jaw': jaw, 'mane': mane, 'tail': tail,
            'leg_ff': leg(True), 'leg_fb': leg(True), 'leg_bf': leg(False), 'leg_bb': leg(False)}


# ------------------------------------------------------------------ the Ashen Alchemist
ALCH_AT = {'cape': (-6, -78), 'arm_b': (-9, -76), 'leg_b': (-4, -48), 'leg_f': (4, -48), 'torso': (0, -46),
           'head': (2, -76), 'arm_f': (10, -76)}
ALCH_RIG = humanoid(ALCH_AT, (0, 22), ['cape', 'arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'weapon', 'arm_f'], {'weapon': 10, 'arm_f': -30, 'arm_b': 20})


def alchemist():
    """The Ashen Alchemist: a tall figure on wooden stilts in long ash-grey robes, a brass rebreather
    mask with two green glass eyes, a rack of bubbling flasks on the back, a flask in hand."""
    p = {'A': '#8a8478', 'a': '#5e5a52', 'l': '#a8a296', 'Z': '#b08a4a', 'z': '#7a5e30', 'g': '#8be04e', 'G': '#4a7a2a',
         'w': '#7a5a3a', 'W': '#5a3e26', 'o': '#141018', 'n': '#120e16', 'r': '#e05a2a', 'b': '#4aa0e0', 'p': '#8be04e',
         'K': '#c8d0d8', 'k': '#8a949e', 'h': '#4a3424', 's': '#c8a888'}
    torso = P(24, 34, (12, 32), p)
    torso.rows(0, 0, [(4, 19), (2, 21), (1, 22)] + [(0, 23)] * 24 + [(-1, 24)] * 7, 'A')
    torso.rect(17, 2, 23, 33, 'a'); torso.rect(3, 4, 5, 30, 'l')
    torso.rect(0, 16, 23, 17, 'h'); torso.rect(9, 16, 11, 17, 'Z')  # belt
    for (x, c) in [(4, 'r'), (8, 'b'), (14, 'p')]:  # vials on the belt
        torso.rect(x, 18, x + 1, 21, c); torso.px(x, 18, 'K')
    for x in range(0, 24, 3): torso.px(x, 33, '.')
    head = P(20, 22, (10, 21), p)
    head.rows(1, 0, [(5, 12), (3, 14), (2, 15), (1, 16), (0, 17)] + [(0, 17)] * 9, 'A')  # hood
    head.ell(12, 11, 7, 6, 'Z'); head.ell(10, 9, 4, 3, 'z')  # the brass mask
    head.ell(14, 9, 2.4, 2.4, 'G'); head.px(14, 9, 'g'); head.ell(9, 9, 1.8, 2, 'G'); head.px(9, 9, 'g')  # glass eyes
    head.rows(12, 14, [(0, 5), (0, 6), (1, 6), (2, 5)], 'z'); head.ell(18, 16, 2, 2, 'Z')  # the rebreather snout and filter
    head.rect(3, 15, 9, 20, 'a')
    rack = P(16, 30, (8, 2), p)  # the rack of flasks on the back, drawn as the cape
    rack.rect(1, 2, 14, 27, 'W'); rack.rect(2, 3, 13, 26, 'w')
    for (x, y, c) in [(3, 5, 'r'), (8, 5, 'b'), (3, 15, 'p'), (8, 15, 'r'), (5, 22, 'b')]:
        rack.rect(x, y + 2, x + 3, y + 6, c); rack.rect(x + 1, y, x + 2, y + 1, 'K')
    flask = P(9, 14, (4, 2), p)
    flask.rect(3, 0, 5, 3, 'K'); flask.ell(4.5, 9, 4.2, 4.2, 'k'); flask.ell(4.5, 9.5, 3.4, 3.4, 'p'); flask.px(3, 7, 'K')
    stilt = P(8, 49, (3, 0), p)
    stilt.rows(0, 0, [(0, 6)] * 6, 'A'); stilt.rect(2, 6, 4, 48, 'w'); stilt.rect(4, 6, 4, 48, 'W')
    for y in (14, 30): stilt.rect(1, y, 5, y + 1, 'h')
    stilt.rect(1, 46, 5, 48, 'W')
    arm = lambda: _robearm(p)
    return {'torso': torso, 'head': head, 'cape': rack, 'weapon': flask, 'arm_f': arm(), 'arm_b': arm(),
            'leg_f': stilt, 'leg_b': _copy(stilt)}


def _robearm(p):
    g = P(9, 25, (4, 3), p)
    g.ell(4, 4, 4, 4, 'A'); g.rows(1, 4, [(0, 6)] * 14 + [(-1, 7)] * 4, 'A'); g.rect(5, 6, 7, 21, 'a')
    g.rows(2, 22, [(0, 4), (0, 4), (1, 3)], 's')
    return g


# ------------------------------------------------------------------ the Gravewyrm
def wyrm():
    """The Gravewyrm: a serpent of yellowed bone, a horned skull with a lower jaw that unhinges, a long
    chain of vertebrae with rib-hooks, a ghost-green light in its eyes and joints. The game draws its
    segments along the path its head has taken."""
    p = {'K': '#d8ccb0', 'k': '#a8987a', 'D': '#786a54', 'g': '#8be0a0', 'G': '#3a7a5a', 'o': '#141018', 'n': '#120e16'}
    head = P(40, 30, (10, 16), p)
    head.rows(0, 4, [(10, 26), (6, 30), (4, 34), (2, 36), (1, 38), (0, 39), (0, 39), (0, 39), (1, 38), (2, 37), (4, 35), (6, 32), (8, 28)], 'K')
    head.ell(14, 8, 9, 4, 'k'); head.rect(4, 14, 36, 16, 'k')
    head.ell(22, 10, 3.5, 3, 'o'); head.px(22, 10, 'g'); head.px(23, 10, 'g')  # eye
    head.rect(34, 8, 36, 9, 'o')  # nostril
    for x in range(18, 38, 3): head.rect(x, 16, x, 18, 'K')  # upper teeth
    head.line(6, 6, 0, 0, 'K'); head.line(7, 6, 1, 0, 'K'); head.line(12, 4, 8, -1, 'k')  # horns sweeping back
    head.rows(0, 0, [(0, 1), (0, 2)], 'K')
    jaw = P(32, 10, (2, 2), p)
    jaw.rows(0, 0, [(0, 30), (1, 31), (2, 30), (4, 27), (8, 22)], 'k'); jaw.rect(2, 0, 30, 0, 'D')
    for x in range(10, 30, 4): jaw.rect(x, -1, x, 0, 'K'); jaw.px(x, 0, 'K')
    seg = P(22, 28, (11, 14), p)  # a vertebra, side on: dorsal spine, body, ribs hooking down
    seg.tri([(8, 9), (14, 9), (12, 0)], 'K'); seg.line(12, 1, 12, 8, 'k')
    seg.rows(3, 9, [(1, 15), (0, 16), (0, 16), (0, 16), (0, 16), (0, 16), (1, 15)], 'K')
    seg.rect(13, 10, 19, 15, 'k'); seg.rect(3, 15, 19, 15, 'D')
    seg.ell(4, 12, 1.5, 1.5, 'G'); seg.px(4, 12, 'g'); seg.ell(18, 12, 1.5, 1.5, 'G'); seg.px(18, 12, 'g')  # glowing joints
    for x0, dx in [(5, -1), (9, 0), (13, 0), (17, 1)]:  # ribs
        seg.line(x0, 16, x0 + dx * 2, 22, 'K'); seg.line(x0 + dx * 2, 22, x0 + dx * 2 + (1 if dx >= 0 else -1), 26, 'k')
    tail = P(18, 14, (2, 7), p)
    tail.rows(0, 2, [(0, 8), (0, 11), (0, 14), (0, 17), (0, 14), (0, 11), (0, 8)], 'K'); tail.ell(4, 5, 3, 3, 'k')
    for x in (6, 10, 14): tail.px(x, 5, 'D')
    return {'head': head, 'jaw': jaw, 'seg': seg, 'tail': tail}


WYRM_GAME_RIG = {  # in the game the rig is just the head; js/boss.js lays the vertebrae along its path
    'parts': {'jaw': ('body', -6, -14), 'head': ('body', 0, -16)},
    'order': ['jaw', 'head'],
    'defaults': {},
}
WYRM_RIG = {  # for the review sheet only; the game strings the segments along its path
    'parts': {'tail': ('ground', -66, -20), 'seg3': ('ground', -48, -26), 'seg2': ('ground', -32, -30), 'seg1': ('ground', -16, -34),
              'seg0': ('ground', 0, -36), 'jaw': ('body', 14, -42), 'head': ('body', 12, -44)},
    'order': ['tail', 'seg3', 'seg2', 'seg1', 'seg0', 'jaw', 'head'],
    'defaults': {},
}


def wyrm_sheet():
    w = wyrm()
    return {'head': w['head'], 'jaw': w['jaw'], 'seg0': w['seg'], 'seg1': w['seg'], 'seg2': w['seg'], 'seg3': w['seg'], 'tail': w['tail']}
