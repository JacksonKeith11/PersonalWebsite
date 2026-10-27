# Contact sheet of monsters: python3 monsheet.py out.png name1 name2 ...
import sys
from kit import render, Image
from PIL import ImageDraw, ImageFont
import monsters
names = sys.argv[2:]
S = 5; cell = 32 * S; pad = 12; lab = 22; cols = 5
rows_n = (len(names) + cols - 1) // cols
out = Image.new('RGBA', (cols * (cell + pad) + pad, rows_n * (cell + 64 + lab + 2 * pad) + pad), (34, 28, 46, 255)); d = ImageDraw.Draw(out)
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
for i, n in enumerate(names):
    g = getattr(monsters, n)(); im = render(g.strings(), g.pal)
    x = pad + (i % cols) * (cell + pad); y = pad + (i // cols) * (cell + 64 + lab + 2 * pad)
    d.rectangle([x, y + lab, x + cell - 1, y + lab + cell + 70], fill=(58, 92, 46, 255)); d.text((x, y), n, fill=(242, 201, 76), font=font)
    out.alpha_composite(im.resize((cell, cell), Image.NEAREST), (x, y + lab))
    out.alpha_composite(im.resize((64, 64), Image.NEAREST), (x + cell // 2 - 32, y + lab + cell + 3))
out.save(sys.argv[1])
