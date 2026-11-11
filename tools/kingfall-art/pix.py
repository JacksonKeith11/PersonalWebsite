# Kingfall's pixel kit: cutout parts. Each part is a small grid of material letters with a pivot,
# shaded and outlined on its own by Roguelike Tactics' render() (docs/game-art.md), then animated by
# the game (js/rig.js) by moving and rotating parts around their pivots. Everything faces right.
import os, sys
import importlib.util
from PIL import Image
_spec = importlib.util.spec_from_file_location('tf_kit', os.path.join(os.path.dirname(__file__), '..', 'threefold-art', 'kit.py'))
_tf = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_tf)
render, hexrgb, mix = _tf.render, _tf.hexrgb, _tf.mix

E = '#1a1420'
SKIN = {'s': '#e0b48a', 'S': '#a8785a'}
SKIN2 = {'s': '#b8845e', 'S': '#86603f'}
# Player colours: cloth, plumes and sashes take these (C main, c shadow).
PLAYERS = [('#a83030', '#7a2024'), ('#3a5aa8', '#2a4280'), ('#c8a040', '#94742a'), ('#3a7a5a', '#285a40')]


class P:
    """A part: w x h grid of letters ('.' empty), a pivot (px, py) and a palette."""
    def __init__(s, w, h, pivot, pal):
        s.w, s.h, s.pivot, s.pal = w, h, pivot, dict(pal)
        s.g = [['.'] * w for _ in range(h)]

    def px(s, x, y, c):
        if 0 <= x < s.w and 0 <= y < s.h: s.g[y][x] = c

    def rect(s, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.px(x, y, c)

    def rows(s, x0, y0, spans, c):
        for i, (a, b) in enumerate(spans):
            for x in range(x0 + a, x0 + b + 1): s.px(x, y0 + i, c)

    def ell(s, cx, cy, rx, ry, c):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1: s.px(x, y, c)

    def line(s, x0, y0, x1, y1, c, w=1):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            x = round(x0 + (x1 - x0) * i / n); y = round(y0 + (y1 - y0) * i / n)
            for k in range(w): s.px(x + k, y, c)

    def tri(s, pts, c):
        (ax, ay), (bx, by), (cx, cy) = pts
        def sgn(px, py, x1, y1, x2, y2): return (px - x2) * (y1 - y2) - (x1 - x2) * (py - y2)
        for y in range(s.h):
            for x in range(s.w):
                p = (x + .5, y + .5)
                d1 = sgn(*p, ax, ay, bx, by); d2 = sgn(*p, bx, by, cx, cy); d3 = sgn(*p, cx, cy, ax, ay)
                if not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0)): s.px(x, y, c)

    def text(s, x0, y0, lines):
        """Stamp literal rows; ' ' leaves the pixel alone."""
        for i, row in enumerate(lines):
            for j, ch in enumerate(row):
                if ch != ' ': s.px(x0 + j, y0 + i, ch)

    def strings(s): return [''.join(r) for r in s.g]

    def image(s):
        """Shaded and outlined, with a 1px margin so the outline fits; pivot moves by (1, 1)."""
        rows = ['.' * (s.w + 2)] + ['.' + r + '.' for r in s.strings()] + ['.' * (s.w + 2)]
        used = set(''.join(rows)) - {'.'}
        missing = used - set(s.pal)
        assert not missing, f'letters without colours: {missing}'
        return render(rows, s.pal)


def compose(placed, size=(64, 64), origin=(32, 56)):
    """Preview a rig pose: placed = [(part, (x, y), angle_degrees)], x/y where the pivot goes,
    relative to origin (the feet). Drawn in list order. Rotation is nearest-neighbour, like the game."""
    out = Image.new('RGBA', size, (0, 0, 0, 0))
    for part, (x, y), ang in placed:
        im = part.image()
        px, py = part.pivot[0] + 1, part.pivot[1] + 1
        if ang:
            # rotate about the pivot: pad so the pivot is the centre, rotate, then place
            r = max(im.width, im.height) * 2
            pad = Image.new('RGBA', (r * 2, r * 2), (0, 0, 0, 0))
            pad.alpha_composite(im, (r - px, r - py))
            im = pad.rotate(-ang, resample=Image.NEAREST)
            px = py = r
        out.alpha_composite(im, (origin[0] + x - px, origin[1] + y - py)) if _fits(out, im, origin[0] + x - px, origin[1] + y - py) else _paste(out, im, origin[0] + x - px, origin[1] + y - py)
    return out


def _fits(out, im, x, y): return x >= 0 and y >= 0 and x + im.width <= out.width and y + im.height <= out.height


def _paste(out, im, x, y):
    layer = Image.new('RGBA', out.size, (0, 0, 0, 0))
    layer.paste(im, (x, y), im)
    out.alpha_composite(layer)


def humanoid(at, hand, order, defaults):
    p = {'leg_b': ('ground', *at['leg_b']), 'leg_f': ('ground', *at['leg_f']), 'torso': ('body', *at['torso']),
         'head': ('torso', *at['head']), 'cape': ('torso', *at['cape']),
         'arm_b': ('torso', *at['arm_b']), 'arm_f': ('torso', *at['arm_f']),
         'weapon': ('arm_f', at['arm_f'][0] + hand[0], at['arm_f'][1] + hand[1]),
         'shield': ('arm_b', at['arm_b'][0] + hand[0], at['arm_b'][1] + hand[1])}
    # 'front': poses with front=1 draw the shield just before the weapon instead of before the back arm
    return {'parts': p, 'order': order, 'defaults': defaults, 'front': {'shield': ['arm_b', 'weapon']}}
