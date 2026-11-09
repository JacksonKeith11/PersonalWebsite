# Renders a move's animation as a strip of frames, posed exactly as js/rig.js poses them, for checking
# keyframes while writing a boss or weapon. Each frame is labelled with its time; frames inside a hit's
# active window get a red bar.
#   python3 tools/kingfall-art/anim.py corvin combo out.png        a boss move
#   python3 tools/kingfall-art/anim.py sword light0 out.png        a weapon attack (light0-2, heavy, special)
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from PIL import Image, ImageDraw
from pix import PLAYERS
import heroes, bosses, weapons
from app.kingfall import content as C

DEFAULTS = {'hero': {'weapon': 40, 'arm_b': 8, 'shield': -8}, 'knight': {'weapon': 35, 'arm_b': 10, 'shield': -10}}


def rot(x, y, deg):
    r = math.radians(deg)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)


def sample(keys, t, d):
    if t <= keys[0][0]: return dict(keys[0][1])
    for i in range(1, len(keys)):
        t1, p1 = keys[i]
        if t <= t1:
            t0, p0 = keys[i - 1]
            u = (t - t0) / max(1e-6, t1 - t0); k = u * u * (3 - 2 * u)
            out = {}
            for key in set(p0) | set(p1):
                if key in ('front', 'run'): out[key] = p0.get(key) if u < 0.5 else p1.get(key); continue
                a, b = p0.get(key, d.get(key, 0)), p1.get(key, d.get(key, 0))
                out[key] = a + (b - a) * k
            return out
    return dict(keys[-1][1])


def paint(parts, kind, p, size, origin):
    at = heroes.RIG if kind == 'hero' else bosses.KNIGHT_RIG
    hand = heroes.HAND if kind == 'hero' else bosses.KNIGHT_HAND
    order = list(heroes.ORDER if kind == 'hero' else bosses.KNIGHT_ORDER)
    if 'shield' in order:
        order.remove('shield')
        order.insert(order.index('weapon') if p.get('front') else order.index('arm_b'), 'shield')
    d = DEFAULTS[kind]
    g = lambda k: p.get(k, d.get(k, 0))
    bx, by = round(g('lean')), round(g('dy'))
    tA = g('torso'); tp = (at['torso'][0] + bx, at['torso'][1] + by)
    def off(k):
        x, y = rot(at[k][0] - at['torso'][0], at[k][1] - at['torso'][1], tA); return tp[0] + x, tp[1] + y
    af, afA, ab, abA = off('arm_f'), tA + g('arm_f'), off('arm_b'), tA + g('arm_b')
    hx, hy = rot(*hand, afA); sx, sy = rot(*hand, abA)
    place = {'leg_b': (at['leg_b'], g('leg_b')), 'leg_f': (at['leg_f'], g('leg_f')), 'torso': (tp, tA),
             'head': (off('head'), tA + g('head')), 'cape': (off('cape'), tA + g('cape')), 'arm_f': (af, afA), 'arm_b': (ab, abA),
             'weapon': ((af[0] + hx, af[1] + hy), afA + g('weapon')), 'shield': ((ab[0] + sx, ab[1] + sy), abA + g('shield'))}
    out = Image.new('RGBA', size, (0, 0, 0, 0))
    for key in order:
        if key not in parts: continue
        im = parts[key].image(); px, py = parts[key].pivot[0] + 1, parts[key].pivot[1] + 1
        (x, y), a = place[key]
        r = max(im.width, im.height) * 2
        pad = Image.new('RGBA', (r * 2, r * 2), (0, 0, 0, 0)); pad.alpha_composite(im, (r - px, r - py))
        pad = pad.rotate(-a, resample=Image.NEAREST)
        layer = Image.new('RGBA', size, (0, 0, 0, 0))
        layer.paste(pad, (origin[0] + round(x) - r, origin[1] + round(y) - r), pad)
        out.alpha_composite(layer)
    return out


def main(who, move, path, step=0.1):
    if who in C.BOSSES:
        B = C.BOSSES[who]
        data = B['phase2_move'] if move == 'phase2' else B['moves'][move]
        keys, dur, hits = data['anim'], data['dur'], [(h['t0'], h['t1']) for h in data['hits']]
        parts, kind, size, origin = bosses.BOSSES[B['art']](), 'knight', (200, 170), (100, 150)
    else:
        W = C.WEAPONS[who]
        atk = W['light'][int(move[-1])] if move.startswith('light') else W[move]
        keys, dur, hits = atk['anim'], atk['dur'], [tuple(atk['hit'])]
        look = heroes.LOOKS['knight'](PLAYERS[0])
        parts = {**look, 'weapon': weapons.ALL[W['art']](), 'shield': weapons.OFFHAND['shield'](PLAYERS[0])}
        kind, size, origin, step = 'hero', (90, 80), (45, 66), 0.05
    n = int(dur / step) + 1
    S = 2
    sheet = Image.new('RGBA', (min(n, 10) * size[0] * S, ((n + 9) // 10) * (size[1] * S + 16)), (52, 48, 56, 255))
    dr = ImageDraw.Draw(sheet)
    for i in range(n):
        t = i * step
        im = paint(parts, kind, sample(keys, t, DEFAULTS[kind]), size, origin).resize((size[0] * S, size[1] * S), Image.NEAREST)
        x, y = (i % 10) * size[0] * S, (i // 10) * (size[1] * S + 16)
        sheet.alpha_composite(im, (x, y + 16))
        live = any(a <= t <= b for a, b in hits)
        dr.text((x + 4, y + 2), f'{t:.2f}s', fill=(255, 120, 120, 255) if live else (220, 210, 190, 255))
        if live: dr.rectangle((x, y + 14, x + size[0] * S - 2, y + 15), fill=(220, 60, 60, 255))
    sheet.save(path)


if __name__ == '__main__':
    main(*sys.argv[1:4])
