# Packs every Kingfall part into app/static/games/kingfall/art/atlas.png, with atlas.json giving each
# frame's rectangle and pivot, and the rigs (where each part's pivot sits, drawing order, hands).
# Run from anywhere: python3 tools/kingfall-art/build.py. Never edit the outputs by hand.
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
from pix import PLAYERS
import heroes, weapons, bosses

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app', 'static', 'games', 'kingfall', 'art')


def frames():
    """(name, part) for every frame in the atlas."""
    for look, fn in heroes.LOOKS.items():
        for i, colour in enumerate(PLAYERS):
            for key, part in fn(colour).items():
                yield f'{look}.{i}.{key}', part
    for name, fn in weapons.ALL.items():
        yield f'w.{name}', fn()
    for name, fn in weapons.OFFHAND.items():
        for i, colour in enumerate(PLAYERS):
            yield f'w.{name}.{i}', fn(colour)
    for name, fn in bosses.BOSSES.items():
        for key, part in fn().items():
            yield f'{name}.{key}', part


def pack(items, width=1024):
    """Shelf packing, tallest first. Returns ({name: (x, y)}, height)."""
    items = sorted(items, key=lambda it: -it[1].height)
    x = y = shelf = 0
    at = {}
    for name, im in items:
        if x + im.width > width:
            x, y, shelf = 0, y + shelf + 1, 0
        at[name] = (x, y)
        x += im.width + 1
        shelf = max(shelf, im.height)
    return at, y + shelf


def main():
    os.makedirs(OUT, exist_ok=True)
    imgs, pivots = [], {}
    for name, part in frames():
        imgs.append((name, part.image()))
        pivots[name] = (part.pivot[0] + 1, part.pivot[1] + 1)  # image() adds a 1px margin
    at, h = pack(imgs)
    sheet = Image.new('RGBA', (1024, h), (0, 0, 0, 0))
    meta = {'frames': {}, 'rigs': {}}
    for name, im in imgs:
        sheet.paste(im, at[name])
        meta['frames'][name] = [*at[name], im.width, im.height, *pivots[name]]
    meta['rigs']['hero'] = {'at': heroes.RIG, 'order': heroes.ORDER, 'hand': heroes.HAND}
    meta['rigs']['knight'] = {'at': bosses.KNIGHT_RIG, 'order': bosses.KNIGHT_ORDER, 'hand': bosses.KNIGHT_HAND}
    meta['looks'] = list(heroes.LOOKS)
    meta['colours'] = [c[0] for c in PLAYERS]
    sheet.save(os.path.join(OUT, 'atlas.png'), optimize=True)
    with open(os.path.join(OUT, 'atlas.json'), 'w') as f:
        json.dump(meta, f, separators=(',', ':'))
    print(f'{len(imgs)} frames, 1024x{h}, to {os.path.normpath(OUT)}')


if __name__ == '__main__':
    main()
