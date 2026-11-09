# A review sheet of bosses in their rest pose next to a hero, at 3x (game size on a 1080p screen):
#   python3 tools/kingfall-art/sheet.py out.png mire bellwarden
import sys
from PIL import Image, ImageDraw
from pix import PLAYERS
import bosses, heroes, weapons, rigs


def main(path, names):
    hero = rigs.paint({**heroes.LOOKS['knight'](PLAYERS[0]), 'weapon': weapons.ALL['sword']()}, rigs.RIGS['hero'], {}, (64, 64), (32, 60))
    cells = []
    for n in names:
        fn, rig = bosses.SHEET_ONLY.get(n, (bosses.BOSSES[n], bosses.BOSS_RIG[n]))
        cells.append((n, rigs.paint(fn(), rigs.RIGS[rig], {}, (200, 170), (110 if n != 'drake' else 90, 160))))
    S = 3
    cols = min(3, len(cells))
    sheet = Image.new('RGBA', (cols * 230 * S, ((len(cells) + cols - 1) // cols) * 180 * S), (40, 36, 44, 255))
    d = ImageDraw.Draw(sheet)
    for i, (n, im) in enumerate(cells):
        x, y = (i % cols) * 230 * S, (i // cols) * 180 * S
        sheet.alpha_composite(im.resize((200 * S, 170 * S), Image.NEAREST), (x, y))
        sheet.alpha_composite(hero.resize((64 * S, 64 * S), Image.NEAREST), (x + 150 * S, y + 106 * S))
        d.text((x + 10, y + 10), n, fill=(240, 230, 210, 255))
    sheet.save(path)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
