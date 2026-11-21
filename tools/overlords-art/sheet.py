# A preview sheet of Overlords' sprites: each big, then a strip at board size.
#     python3 tools/overlords-art/sheet.py out.png [name ...] [--poses]
# With no names, every sprite; --poses shows each one's five poses in a row.
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from kit import render, POSES, poses  # noqa: E402
from build import SPRITES  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    out, names = args[0], args[1:] or list(SPRITES)
    show_poses = '--poses' in sys.argv
    scale, cols = (4, len(POSES)) if show_poses else (5, 8)
    items = []
    for n in names:
        rows, pal = SPRITES[n]()
        if show_poses:
            items += [(f'{n}:{p}', r, pal) for p, r in poses(rows).items()]
        else:
            items.append((n, rows, pal))
    cw = 32 * scale + 8
    n_rows = (len(items) + cols - 1) // cols
    img = Image.new('RGBA', (cols * cw, n_rows * cw), (40, 46, 64, 255))
    for i, (_, rows, pal) in enumerate(items):
        im = render(rows, pal).resize((32 * scale, 32 * scale), Image.NEAREST)
        img.alpha_composite(im, ((i % cols) * cw + 4, (i // cols) * cw + 4))
    img.save(out)
    print(f'{len(items)} sprites -> {out}')


if __name__ == '__main__':
    main()
