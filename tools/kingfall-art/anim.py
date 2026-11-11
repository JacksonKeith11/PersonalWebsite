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
import heroes, bosses, weapons, rigs
from app.kingfall import content as C



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


def main(who, move, path, step=0.1):
    if who in C.BOSSES:
        B = C.BOSSES[who]
        data = B['phase2_move'] if move == 'phase2' else B['moves'][move]
        keys, dur, hits = data['anim'], data['dur'], [(h['t0'], h['t1']) for h in data['hits']]
        parts, kind = bosses.BOSSES[B['art']](), bosses.BOSS_RIG[B['art']]
        size, origin = tuple(B.get('frame', (200, 170))), tuple(B.get('origin', (100, 150)))
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
        R = rigs.RIGS[kind]
        im = rigs.paint(parts, R, sample(keys, t, R['defaults']), size, origin).resize((size[0] * S, size[1] * S), Image.NEAREST)
        x, y = (i % 10) * size[0] * S, (i // 10) * (size[1] * S + 16)
        sheet.alpha_composite(im, (x, y + 16))
        live = any(a <= t <= b for a, b in hits)
        dr.text((x + 4, y + 2), f'{t:.2f}s', fill=(255, 120, 120, 255) if live else (220, 210, 190, 255))
        if live: dr.rectangle((x, y + 14, x + size[0] * S - 2, y + 15), fill=(220, 60, 60, 255))
    sheet.save(path)


if __name__ == '__main__':
    main(*sys.argv[1:4])
