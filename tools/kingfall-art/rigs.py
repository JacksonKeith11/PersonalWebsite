# Rigs: how a character's parts hang together. Each part has a parent and its pivot's rest position
# (relative to the feet). Parent 'ground' parts stay put (legs); 'body' parts move with the pose's
# lean/dy; any other parent carries its children round as it turns. js/rig.js poses them the same way
# (build.py writes these tables into atlas.json), and solve() here is what anim.py and the previews use.
import math
from PIL import Image
import heroes, bosses


def humanoid(at, hand, order, defaults):
    p = {'leg_b': ('ground', *at['leg_b']), 'leg_f': ('ground', *at['leg_f']), 'torso': ('body', *at['torso']),
         'head': ('torso', *at['head']), 'cape': ('torso', *at['cape']),
         'arm_b': ('torso', *at['arm_b']), 'arm_f': ('torso', *at['arm_f']),
         'weapon': ('arm_f', at['arm_f'][0] + hand[0], at['arm_f'][1] + hand[1]),
         'shield': ('arm_b', at['arm_b'][0] + hand[0], at['arm_b'][1] + hand[1])}
    # 'front': poses with front=1 draw the shield just before the weapon instead of before the back arm
    return {'parts': p, 'order': order, 'defaults': defaults, 'front': {'shield': ['arm_b', 'weapon']}}


RIGS = {
    'hero': humanoid(heroes.RIG, heroes.HAND, heroes.ORDER, {'weapon': 40, 'arm_b': 8, 'shield': -8}),
    'knight': humanoid(bosses.KNIGHT_RIG, bosses.KNIGHT_HAND, bosses.KNIGHT_ORDER, {'weapon': 35, 'arm_b': 10, 'shield': -10}),
    **bosses.RIGS,
}


def rot(x, y, deg):
    r = math.radians(deg)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)


def solve(rig, pose):
    """{part: (x, y, angle)} for a pose. Pose keys: part angles; lean, dy (the body); <part>_x/_y nudge a
    part along its parent's frame."""
    d = rig['defaults']
    g = lambda k: pose.get(k, d.get(k, 0))
    out = {}
    parts = rig['parts']

    def place(k):
        if k in out: return out[k]
        parent, x, y = parts[k]
        nx, ny = g(k + '_x'), g(k + '_y')
        if parent == 'ground':
            out[k] = (x + nx, y + ny, g(k))
        elif parent == 'body':
            out[k] = (x + round(g('lean')) + nx, y + round(g('dy')) + ny, g(k))
        else:
            px, py, pa = place(parent)
            _, ax, ay = parts[parent]
            ox, oy = rot(x - ax + nx, y - ay + ny, pa)
            out[k] = (px + ox, py + oy, pa + g(k))
        return out[k]
    for k in parts: place(k)
    return out


def order(rig, pose):
    o = list(rig['order'])
    for k, (back, front) in rig.get('front', {}).items():
        if k in o:
            o.remove(k)
            before = front if pose.get('front') else back
            o.insert(o.index(before) if before in o else len(o), k)
    return o


def paint(images, rig, pose, size, origin):
    """images: {part: P}. Returns the posed figure as an image."""
    at = solve(rig, pose)
    out = Image.new('RGBA', size, (0, 0, 0, 0))
    for k in order(rig, pose):
        if k not in images: continue
        im = images[k].image(); px, py = images[k].pivot[0] + 1, images[k].pivot[1] + 1
        x, y, a = at[k]
        r = max(im.width, im.height) * 2
        pad = Image.new('RGBA', (r * 2, r * 2), (0, 0, 0, 0)); pad.alpha_composite(im, (r - px, r - py))
        pad = pad.rotate(-a, resample=Image.NEAREST)
        layer = Image.new('RGBA', size, (0, 0, 0, 0))
        layer.paste(pad, (origin[0] + round(x) - r, origin[1] + round(y) - r), pad)
        out.alpha_composite(layer)
    return out
