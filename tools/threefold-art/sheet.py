from kit import render, Image
from PIL import ImageDraw, ImageFont
import sys, promos, masters
MOD = masters if "--masters" in sys.argv else promos
sys.argv = [a for a in sys.argv if a != "--masters"]
rows = MOD.CLASSES[int(sys.argv[3]):int(sys.argv[4])] if len(sys.argv) > 4 else MOD.CLASSES
S = int(sys.argv[2]) if len(sys.argv) > 2 else 5; cell = 32 * S; pad = 14; lab = 26
W = 4 * (cell + pad) + pad; H = len(rows) * (cell + 64 + lab + 2 * pad) + pad
out = Image.new('RGBA', (W, H), (34, 28, 46, 255)); d = ImageDraw.Draw(out)
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
y = pad
for name, fns in rows:
    for i, f in enumerate(fns):
        g = f(); im = render(g.strings(), g.pal); x = pad + i * (cell + pad)
        d.rectangle([x, y + lab, x + cell - 1, y + lab + cell + 70], fill=(58, 92, 46, 255))
        d.text((x, y), f'{name} {i + 1}', fill=(242, 201, 76), font=font)
        out.alpha_composite(im.resize((cell, cell), Image.NEAREST), (x, y + lab))
        out.alpha_composite(im.resize((64, 64), Image.NEAREST), (x + cell // 2 - 32, y + lab + cell + 3))
    y += cell + 64 + lab + 2 * pad
out.save(sys.argv[1])
