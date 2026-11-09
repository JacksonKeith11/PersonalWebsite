# Review sheet of boss options: python3 bosspreview.py out.png
import sys, math
from PIL import Image, ImageDraw
from pix import compose
from bosses import BOSSES, KNIGHT_RIG, KNIGHT_ORDER, KNIGHT_HAND

POSES = {
    'idle': {'arm_b': 10, 'shield': -10, 'weapon': 35, 'arm_f': -5, 'back_shield': 1},
    'guard': {'arm_b': -70, 'shield': 70, 'arm_f': 30, 'weapon': 30, 'torso': -4, 'head': 3},
    'overhead': {'arm_f': -165, 'weapon': 105, 'arm_b': 15, 'shield': -15, 'torso': -10, 'head': -8, 'leg_f': -15, 'leg_b': 20, 'cape': 20, 'back_shield': 1},
}


def hand(xy, ang):
    r = math.radians(ang)
    return (round(xy[0] - KNIGHT_HAND[1] * math.sin(r)), round(xy[1] + KNIGHT_HAND[1] * math.cos(r)))


def pose(parts, name):
    a = POSES[name]
    out = []
    order = list(KNIGHT_ORDER)
    if a.get('back_shield'):
        order.remove('shield'); order.insert(order.index('arm_b'), 'shield')
    for key in order:
        if key == 'shield':
            ab = a.get('arm_b', 0)
            out.append((parts['shield'], hand(KNIGHT_RIG['arm_b'], ab), ab + a.get('shield', 0)))
        elif key == 'weapon':
            af = a.get('arm_f', 0)
            out.append((parts['weapon'], hand(KNIGHT_RIG['arm_f'], af), af + a.get('weapon', 0)))
        else:
            out.append((parts[key], KNIGHT_RIG[key], a.get(key, 0)))
    return compose(out, (192, 192), (96, 176))


def main(path):
    sheet = Image.new('RGBA', (3 * 400 + 20, len(BOSSES) * 420), (52, 48, 56, 255))
    d = ImageDraw.Draw(sheet)
    for n, (name, f) in enumerate(BOSSES.items()):
        parts = f()
        for k, pz in enumerate(POSES):
            sheet.alpha_composite(pose(parts, pz).resize((384, 384), Image.NEAREST), (10 + k * 400, n * 420 + 20))
        d.text((10, n * 420 + 4), f'{name}  (2x; 3x in game at 1080p)', fill=(240, 230, 210, 255))
    sheet.save(path)


if __name__ == '__main__':
    main(sys.argv[1])
