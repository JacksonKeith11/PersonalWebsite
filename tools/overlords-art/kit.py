# Overlords' pixel kit: Roguelike Tactics' 32x32 grid and renderer (tools/threefold-art/kit.py: flat
# material letters, then outline and cel shading; docs/game-art.md has the rules), plus a humanoid
# builder, creature parts and the derived poses. Everything faces right with feet on rows 29-30.
import importlib.util
import os

_spec = importlib.util.spec_from_file_location('tf_kit', os.path.join(os.path.dirname(__file__), '..', 'threefold-art', 'kit.py'))
_tf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tf)
G, render, hexrgb, mix, W, H = _tf.G, _tf.render, _tf.hexrgb, _tf.mix, _tf.W, _tf.H

# Shared materials (docs/game-art.md). Letters: s/S skin, h hair, c/C cloth, a/A armour, m/M metal,
# l blade, w/W wood, g gold, b boots, e eyes (never shaded), * glow (never shaded), x/X y/Y z/Z accents.
SKIN = {'s': '#e0b48a', 'S': '#a8785a'}
SKIN_DARK = {'s': '#b8845e', 'S': '#86603f'}
STEEL = {'m': '#a8b0bc', 'M': '#7a8494', 'l': '#dfe6ee'}
WOOD = {'w': '#6a4a2e', 'W': '#5a3a24'}
GOLD = {'g': '#c8a040'}
EYE = {'e': '#1a1420'}
BONE = {'s': '#d8d0c0', 'S': '#b8b0a0'}
BOOTS = {'b': '#4a3628'}

# Each origin's palette, so a trait reads at a glance (the same idea as the acts in docs/game-art.md).
ORIGIN = {
    'emberforged': {'c': '#3e3438', 'C': '#2a2226', 'x': '#ff7a1a', 'y': '#ffd23f', 'a': '#5a4a4a', 'A': '#3e3232'},
    'thornwood': {'c': '#4a6a3a', 'C': '#34502a', 'x': '#7a5a32', 'y': '#a0c060', 'a': '#6a5236', 'A': '#4a3a26'},
    'tidecallers': {'c': '#2a6a7a', 'C': '#1e4e5c', 'x': '#e08a6a', 'y': '#bfe8e0', 'a': '#3a8a8a', 'A': '#2a6464'},
    'gravebound': {'c': '#4a3a5e', 'C': '#33284a', 'x': '#8a6ab8', 'y': '#c8f0d8', 'a': '#5a5a66', 'A': '#40404a'},
    'skyborne': {'c': '#8ab0d8', 'C': '#6a8cb4', 'x': '#f0f0f4', 'y': '#e0c060', 'a': '#b8c8dc', 'A': '#8ea4bc'},
    'ironhold': {'c': '#7a5a3a', 'C': '#5a4028', 'x': '#c8a040', 'y': '#d08040', 'a': '#8a929c', 'A': '#626a74'},
    'starlit': {'c': '#3a3a78', 'C': '#2a2a5a', 'x': '#c8d0e8', 'y': '#ffe8a0', 'a': '#5a5a90', 'A': '#40406a'},
    'mirefolk': {'c': '#5a6a3a', 'C': '#424e2a', 'x': '#8a9a4a', 'y': '#c8b060', 'a': '#4e6a5a', 'A': '#3a5244'},
}
FROG = {'s': '#7a9a4e', 'S': '#5a7a38'}


def pal(*parts, **extra):
    """A palette from parts. Wood and gold are always there (weapons use them), and a letter's
    shadow (its capital) is made a quarter darker when it isn't given."""
    out = dict(WOOD)
    out.update(BOOTS)
    out.update(GOLD)
    for p in parts:
        out.update(p)
    out.update(EYE)
    out.update(extra)
    for k, v in list(out.items()):
        if k.islower() and k.upper() not in out:
            r, g_, b = mix(hexrgb(v), (24, 16, 40), 0.25)
            out[k.upper()] = f'#{r:02x}{g_:02x}{b:02x}'
    return out


# ------------------------------------------------------------------ the humanoid
# build: 'normal' (about 25 px), 'short' (dwarves, about 21), 'big' (fills the canvas), 'small' (17)
BODY = {
    'normal': dict(head=(16, 9.5, 4, 4.2), torso=(12, 14, 19, 21), legs=(22, 28), arm=(15, 21), eyes=(15, 18, 10)),
    'short': dict(head=(16, 13, 4.5, 4), torso=(11, 17, 20, 24), legs=(25, 28), arm=(18, 23), eyes=(15, 18, 13)),
    'big': dict(head=(17, 7, 4.5, 4.5), torso=(9, 12, 23, 23), legs=(24, 28), arm=(13, 22), eyes=(16, 20, 7)),
    'small': dict(head=(16, 15, 4, 4), torso=(13, 20, 18, 25), legs=(26, 28), arm=(20, 25), eyes=(15, 18, 15)),
}


class Fig:
    """A humanoid drawn onto a grid. Fields after build() say where the hands, head and so on are,
    for weapons and gear."""

    def __init__(s, g, build='normal'):
        s.g, s.build, s.b = g, build, BODY[build]

    def body(s, robe=False, legs='c', torso='c', arms='c', boots='b', belt=None, skin='s', armless=False):
        g, b = s.g, s.b
        x0, y0, x1, y1 = b['torso']
        ly0, ly1 = b['legs']
        cx = (x0 + x1) // 2
        if robe:  # a robe flares to the feet
            for i, y in enumerate(range(y0, 29)):
                spread = min(3, i // 3)
                g.rect(x0 - spread, y, x1 + spread, y, torso)
            g.rect(x0 - 2, 29, x1 + 2, 29, torso.upper() if torso.upper() != torso else torso)
        else:
            g.rect(x0, y0, x1, y1, torso)
            g.rect(x0 + 1, ly0, cx - 1, ly1, legs)
            g.rect(cx + 2, ly0, x1, ly1, legs)
            g.rect(x0 + 1, 29, cx - 1, 30, boots)
            g.rect(cx + 2, 29, x1 + 1, 30, boots)
        if belt:
            g.rect(x0, y1, x1, y1, belt)
        ay0, ay1 = b['arm']
        if not armless:
            g.rect(x0 - 2, ay0, x0 - 1, ay1, arms.upper() if arms.islower() else arms)  # the far arm, in shadow
            g.rect(x1 + 1, ay0, x1 + 2, ay1, arms)
            g.rect(x1 + 1, ay1 + 1, x1 + 2, ay1 + 1, skin)
            g.rect(x0 - 2, ay1 + 1, x0 - 1, ay1 + 1, skin.upper() if skin.islower() else skin)
        s.hand = (x1 + 2, ay1 + 1)  # the near hand
        s.back_hand = (x0 - 2, ay1 + 1)
        s.x0, s.x1, s.y0, s.y1 = x0, x1, y0, y1
        return s

    def head(s, skin='s', eyes='e', glow=None):
        g, b = s.g, s.b
        cx, cy, rx, ry = b['head']
        g.ell(cx, cy, rx, ry, skin)
        ex1, ex2, ey = b['eyes']
        g.px(ex1, ey, glow or eyes)
        g.px(ex2, ey, glow or eyes)
        s.hx, s.hy, s.hrx, s.hry = cx, cy, rx, ry
        s.top = int(cy - ry)
        return s

    def hair(s, c='h', long=False):
        g = s.g
        cx, cy, rx, ry = s.hx, s.hy, s.hrx, s.hry
        top = int(cy - ry)
        g.rect(int(cx - rx), top, int(cx + rx) - 1, top + 1, c)
        g.rect(int(cx - rx), top, int(cx - rx) + 1, int(cy) + (4 if long else 1), c)
        return s

    def helm(s, c='a', visor=True, plume=None, horns=None):
        g = s.g
        cx, cy, rx, ry = s.hx, s.hy, s.hrx, s.hry
        top = int(cy - ry)
        g.rect(int(cx - rx), top, int(cx + rx) - 1, int(cy) + 1, c)
        g.ell(cx, cy - 1, rx + 0.3, ry - 0.5, c)
        if visor:
            ey = s.b['eyes'][2]
            g.rect(int(cx) - 1, ey, int(cx + rx) - 1, ey, 'e')
        if plume:
            g.rect(int(cx) - 2, top - 2, int(cx) + 1, top - 1, plume)
            g.rect(int(cx) - 4, top - 1, int(cx) - 3, top + 1, plume)
        if horns:
            g.line(int(cx - rx) - 1, top + 1, int(cx - rx) - 2, top - 3, horns, 2)
            g.line(int(cx + rx), top + 1, int(cx + rx) + 1, top - 3, horns, 2)
        return s

    def hood(s, c='c', shadow='C'):
        g = s.g
        cx, cy, rx, ry = s.hx, s.hy, s.hrx, s.hry
        top = int(cy - ry)
        g.ell(cx - 0.5, cy - 0.5, rx + 1, ry + 0.8, c)
        g.rect(int(cx) - 1, int(cy) - 1, int(cx + rx) - 1, int(cy) + 2, shadow)
        ex1, ex2, ey = s.b['eyes']
        g.px(ex1 + 1, ey, 'e')
        g.px(ex2, ey, 'e')
        g.rect(int(cx - rx) - 1, int(cy), int(cx - rx), int(cy + ry) + 2, c)
        s.top = top - 1
        return s

    def hat(s, c='c', band=None, tall=8, bend=True):
        g = s.g
        cx, cy, rx = s.hx, s.hy, s.hrx
        top = int(cy - s.hry)
        g.rect(int(cx - rx) - 2, top + 1, int(cx + rx) + 1, top + 2, c)
        for i in range(tall):
            w = max(0, 3 - i // 2)
            g.rect(int(cx) - w - (1 if i < 2 else 0), top - i, int(cx) + w, top - i, c)
        if bend:
            g.rect(int(cx) - 3, top - tall, int(cx) - 1, top - tall, c)
        if band:
            g.rect(int(cx) - 3, top, int(cx) + 3, top, band)
        s.top = top - tall
        return s

    def crown(s, c='g', gem='*'):
        g = s.g
        cx, top = int(s.hx), int(s.hy - s.hry)
        g.rect(cx - 3, top - 1, cx + 3, top, c)
        for x in (cx - 3, cx, cx + 3):
            g.px(x, top - 2, c)
        g.px(cx, top - 1, gem)
        return s

    def beard(s, c='h', long=True):
        g = s.g
        cx, cy, rx, ry = s.hx, s.hy, s.hrx, s.hry
        ey = s.b['eyes'][2]
        g.rect(int(cx) - 1, ey + 2, int(cx + rx) - 1, int(cy + ry), c)
        if long:
            g.rows(int(cx) - 1, int(cy + ry) + 1, [(0, 5), (0, 4), (1, 3)], c)
        return s

    def cape(s, c='x'):
        g = s.g
        g.rows(s.x0 - 3, s.y0, [(1, 2), (0, 2), (0, 2), (-1, 2), (-1, 2), (-1, 2), (-2, 2), (-2, 2), (-2, 2), (-2, 1), (-2, 1), (-2, 1)], c)
        return s

    def wings(s, c='x', d='y'):
        g = s.g
        x, y = s.x0 - 2, s.y0 - 1
        g.rows(x - 7, y - 3, [(6, 7), (4, 7), (2, 7), (0, 7), (0, 7), (1, 7), (2, 7), (3, 7), (5, 7)], c)
        g.line(x - 6, y + 1, x, y + 2, d)
        g.line(x - 5, y + 3, x, y + 4, d)
        return s


# ------------------------------------------------------------------ weapons and gear, held in a hand (x, y)
def sword(g, hand, blade='l', hilt='g', grip='w', length=9, up=True):
    hx, hy = hand
    g.px(hx, hy, grip)
    g.rect(hx - 1, hy - 1, hx + 1, hy - 1, hilt)
    for i in range(length):
        g.px(hx + (i // 3 if not up else 0) + (1 if up else 1 + i // 3), hy - 2 - i if up else hy - 1 - i // 2, blade)


def blade_up(g, hand, length=10, c='l', guard='g', lean=1):
    hx, hy = hand
    g.rect(hx - 1, hy - 1, hx + 1, hy - 1, guard)
    for i in range(length):
        x = hx + (i * lean) // 4
        g.px(x, hy - 2 - i, c)
        g.px(x + 1, hy - 2 - i, c if i < length - 1 else '.')


def dagger(g, hand, c='l', grip='W'):
    hx, hy = hand
    g.px(hx, hy, grip)
    g.line(hx + 1, hy - 1, hx + 3, hy - 3, c)


def axe(g, hand, head='M', haft='w', big=False, edge='l'):
    """A haft with a crescent head on the far side and a bright cutting edge."""
    hx, hy = hand
    r = 4 if big else 3
    top = hy - 9
    for i in range(-r, r + 1):  # the head: widest in the middle, an edge down its outside
        w = r - abs(i) // 2
        g.rect(hx + 1, top + i, hx + w, top + i, head)
        g.px(hx + w + 1, top + i, edge)
    g.line(hx, hy + 2, hx, top - r - 1, haft)


def hammer(g, hand, head='m', haft='w'):
    hx, hy = hand
    g.line(hx, hy + 2, hx, hy - 8, haft)
    g.rect(hx - 2, hy - 11, hx + 3, hy - 7, head)


def spear(g, hand, tip='l', haft='w', length=16, lance=False):
    hx, hy = hand
    g.line(hx, hy + 4, hx + 2, hy - length + 4, haft)
    g.rect(hx + 1, hy - length + 1, hx + 3, hy - length + 3, tip)
    g.px(hx + 2, hy - length, tip)
    if lance:
        g.rect(hx - 1, hy - 2, hx + 2, hy - 1, tip)


def trident(g, hand, tip='m', haft='w'):
    hx, hy = hand
    g.line(hx, hy + 4, hx + 1, hy - 12, haft)
    g.rect(hx - 1, hy - 13, hx + 3, hy - 13, tip)
    for x in (hx - 1, hx + 1, hx + 3):
        g.rect(x, hy - 16, x, hy - 14, tip)


def staff(g, hand, top='*', haft='w', length=15, orb=True):
    hx, hy = hand
    g.line(hx, hy + 5, hx + 1, hy - length + 5, haft)
    if orb:
        g.ell(hx + 1.5, hy - length + 3, 1.8, 1.8, top)
    else:
        g.rect(hx, hy - length + 2, hx + 2, hy - length + 4, top)


def bow(g, hand, c='w', string='y'):
    hx, hy = hand
    pts = [(hx + 2, hy - 8), (hx + 3, hy - 7), (hx + 4, hy - 5), (hx + 4, hy - 3), (hx + 4, hy - 1), (hx + 4, hy + 1),
           (hx + 3, hy + 3), (hx + 2, hy + 4)]
    for x, y in pts:
        g.px(x, y, c)
    g.line(hx + 2, hy - 8, hx + 2, hy + 4, string)


def crossbow(g, hand, c='w', m='m'):
    hx, hy = hand
    g.rect(hx, hy - 2, hx + 6, hy - 1, c)
    g.line(hx + 5, hy - 6, hx + 5, hy + 3, m)
    g.px(hx + 7, hy - 2, m)


def shield(g, x, y, c='a', d='A', emblem=None, w=5, h=7, round_=False):
    if round_:
        g.ell(x + w / 2, y + h / 2, w / 2, h / 2, c)
    else:
        g.rect(x, y, x + w - 1, y + h - 2, c)
        g.rect(x + 1, y + h - 1, x + w - 2, y + h - 1, c)
    g.rect(x, y, x, y + h - 2, d)
    if emblem:
        g.rect(x + w // 2, y + 1, x + w // 2, y + h - 3, emblem)
        g.rect(x + 1, y + h // 2 - 1, x + w - 2, y + h // 2 - 1, emblem)


def flame(g, x, y, big=False):
    g.rows(x - 1, y - (4 if big else 3), [(1, 1), (0, 2), (0, 2), (-1, 3)] if big else [(1, 1), (0, 2), (0, 2)], 'x')
    g.px(x, y - 1, 'y')
    g.px(x + 1, y - 1, 'y')


def star(g, x, y, c='*'):
    g.px(x, y, c)
    g.px(x - 1, y, c)
    g.px(x + 1, y, c)
    g.px(x, y - 1, c)
    g.px(x, y + 1, c)


# ------------------------------------------------------------------ creatures
def quadruped(g, body='c', dark='C', head_c=None, length=14, tall=7, legs='C', tail=True, ears=True, x0=6):
    """A four-legged beast, low on the ground, head on the right."""
    head_c = head_c or body
    y1 = 27
    g.ell(x0 + length / 2, y1 - tall / 2 - 2, length / 2, tall / 2, body)
    for lx in (x0 + 1, x0 + 4, x0 + length - 5, x0 + length - 2):
        g.rect(lx, y1 - 3, lx + 1, 30, legs)
    hx = x0 + length + 2
    g.ell(hx, y1 - tall - 1, 3.5, 3, head_c)
    g.rect(hx + 2, y1 - tall, hx + 5, y1 - tall + 1, head_c)
    g.px(hx + 1, y1 - tall - 2, 'e')
    if ears:
        g.rect(hx - 2, y1 - tall - 5, hx - 1, y1 - tall - 3, dark)
    if tail:
        g.line(x0, y1 - tall, x0 - 4, y1 - tall - 4, body, 2)
    return hx, y1 - tall - 1


def blob(g, c='c', d='C', cx=16, w=7, h=5, eyes=True):
    g.ell(cx, 29 - h, w, h, c)
    g.rect(cx - w + 1, 29, cx + w - 2, 29, d)
    if eyes:
        g.px(cx + 1, 28 - h, 'e')
        g.px(cx + 4, 28 - h, 'e')


def tree(g, bark='w', dark='W', leaf='x', leaf_d='y', big=False):
    """A walking tree: a trunk with a face, branch arms, a crown of leaves."""
    x0, x1 = (11, 21) if big else (12, 20)
    top = 10 if big else 13
    g.rect(x0, top, x1, 26, bark)
    g.rect(x0 - 1, 27, x0 + 3, 30, dark)
    g.rect(x1 - 3, 27, x1 + 1, 30, dark)
    g.ell(16, top - 2 if big else top - 1, 9 if big else 7, 6 if big else 5, leaf)
    g.ell(19, top - 4 if big else top - 3, 4, 2.5, leaf_d)
    g.line(x1, top + 5, x1 + 6, top + 1, bark, 2)
    g.line(x0, top + 6, x0 - 5, top + 2, dark, 2)
    g.px(x1 - 4, top + 4, '*')
    g.px(x1 - 1, top + 4, '*')
    g.rect(x1 - 4, top + 7, x1 - 1, top + 7, dark)


def golem(g, c='a', d='A', core='*', big=True):
    g.rect(10, 9, 22, 23, c)
    g.rect(8, 11, 9, 22, d)
    g.rect(23, 11, 25, 22, c)
    g.rect(23, 23, 25, 25, d)
    g.rect(13, 4, 20, 9, c)
    g.px(17, 6, core)
    g.px(19, 6, core)
    g.rect(11, 24, 15, 28, d)
    g.rect(17, 24, 21, 28, d)
    g.rect(10, 29, 15, 30, d)
    g.rect(17, 29, 22, 30, d)
    g.rect(15, 14, 17, 16, core)


# ------------------------------------------------------------------ derived poses (as Saltbound's poseCanvas)
def _bounds(rows):
    ys = [y for y, r in enumerate(rows) if r.strip('.')]
    xs = [x for r in rows for x, ch in enumerate(r) if ch != '.']
    return (min(ys), max(ys), min(xs), max(xs)) if ys else (0, 0, 0, 0)


def _shift(row, k):
    if k > 0:
        return ('.' * k + row)[:len(row)]
    if k < 0:
        return (row[-k:] + '.' * -k)
    return row


def lean(rows, k, nudge=0):
    top, bottom, _, _ = _bounds(rows)
    tall = max(1, bottom - top)
    return [_shift(r, round(k * max(0, bottom - y) / tall) + nudge) for y, r in enumerate(rows)]


def lie_down(rows):
    n, w = len(rows), len(rows[0])
    top, bottom, left, right = _bounds(rows)
    if right - left > (bottom - top) * 1.1:  # wider than tall: rolls over where it stood
        flipped = rows[top:bottom + 1][::-1]
        return [flipped[y - top] if top <= y <= bottom else '.' * w for y in range(n)]
    out = [''.join(rows[x][w - 1 - y] for x in range(n)) for y in range(w)]
    b_top, b_bottom, _, _ = _bounds(out)
    drop = bottom - b_bottom
    blank = '.' * n
    moved = [out[y - drop] if 0 <= y - drop < len(out) else blank for y in range(len(out))]
    _, _, c_left, c_right = _bounds(moved)
    shift = round((w - 1 - c_right - c_left) / 2)
    return [_shift(r, shift) for r in moved]


POSES = ('idle', 'attack', 'cast', 'hurt', 'fallen')


def poses(rows):
    return {'idle': rows, 'attack': lean(rows, 3, 1), 'cast': lean(rows, -2), 'hurt': lean(rows, -3, -1),
            'fallen': lie_down(rows)}
