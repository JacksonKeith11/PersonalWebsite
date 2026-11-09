# Review sheet of hero options: python3 preview.py out.png
# Each option: a big idle pose, a running pose and a swing, then the four player colours at game size.
import sys
from PIL import Image, ImageDraw
from pix import compose, PLAYERS
from heroes import LOOKS, RIG, ORDER, HAND
import weapons, math

POSES = {
    'idle': {'weapon': 40},
    'run': {'leg_f': 30, 'leg_b': -30, 'arm_f': -25, 'arm_b': 30, 'torso': 6, 'head': 4, 'cape': 25, 'weapon': 70, 'bob': -1},
    'swing': {'arm_f': -75, 'arm_b': 20, 'torso': 8, 'head': 4, 'weapon': 170, 'leg_f': -20, 'leg_b': 20, 'cape': 30},
}


def pose(parts, name, weapon='sword'):
    a = POSES[name]
    bob = a.get('bob', 0)
    placed = []
    w = weapons.ALL[weapon]()
    for key in ORDER:
        if key == 'weapon':
            continue
        x, y = RIG[key]
        placed.append((key, parts[key], (x, y + (bob if key != 'leg_f' and key != 'leg_b' else 0)), a.get(key, 0)))
    out = []
    for key, part, xy, ang in placed:
        if key == 'arm_f':
            r = math.radians(ang)
            hx = xy[0] + HAND[0] * math.cos(r) - HAND[1] * math.sin(r)
            hy = xy[1] + HAND[0] * math.sin(r) + HAND[1] * math.cos(r)
            out.append((w, (round(hx), round(hy)), ang + a.get('weapon', 0)))
        out.append((part, xy, ang))
    return compose(out)


def main(path):
    looks = list(LOOKS.items())
    rh = 300
    sheet = Image.new('RGBA', (1300, len(looks) * rh), (52, 48, 56, 255))
    d = ImageDraw.Draw(sheet)
    for n, (name, fn) in enumerate(looks):
        oy = n * rh
        if n % 2: d.rectangle((0, oy, 1300, oy + rh), fill=(60, 55, 64, 255))
        parts = fn(PLAYERS[0])
        sheet.alpha_composite(pose(parts, 'idle').resize((320, 320), Image.NEAREST), (0, max(0, oy - 20)))
        sheet.alpha_composite(pose(parts, 'run').resize((192, 192), Image.NEAREST), (310, oy + 80))
        sheet.alpha_composite(pose(parts, 'swing').resize((192, 192), Image.NEAREST), (490, oy + 80))
        for k, col in enumerate(PLAYERS):
            sheet.alpha_composite(pose(fn(col), 'idle').resize((192, 192), Image.NEAREST), (680 + k * 150, oy + 80))
        d.text((10, oy + 6), name, fill=(240, 230, 210, 255))
    d.text((330, 20), 'run / swing', fill=(200, 190, 170, 255)); d.text((700, 20), 'player colours at 3x, as on a 1080p screen', fill=(200, 190, 170, 255))
    sheet.save(path)


if __name__ == '__main__':
    main(sys.argv[1])
