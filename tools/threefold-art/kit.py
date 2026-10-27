# Tiny pixel-art kit: draw material letters on a 32x32 grid with primitives, then shade, outline and render.
from PIL import Image
W = H = 32
class G:
    def __init__(s, pal): s.g = [['.'] * W for _ in range(H)]; s.pal = pal
    def px(s, x, y, c):
        if 0 <= x < W and 0 <= y < H: s.g[y][x] = c
    def rect(s, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.px(x, y, c)
    def rows(s, x0, y0, spans, c):  # spans: list of (dx_start, dx_end) per row from y0
        for i, (a, b) in enumerate(spans):
            for x in range(x0 + a, x0 + b + 1): s.px(x, y0 + i, c)
    def ell(s, cx, cy, rx, ry, c):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1: s.px(x, y, c)
    def line(s, x0, y0, x1, y1, c, w=1):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            x = round(x0 + (x1 - x0) * i / n); y = round(y0 + (y1 - y0) * i / n)
            for k in range(w): s.px(x + k, y, c)
    def tri(s, pts, c):
        (ax, ay), (bx, by), (cx, cy) = pts
        def sgn(px, py, x1, y1, x2, y2): return (px - x2) * (y1 - y2) - (x1 - x2) * (py - y2)
        for y in range(H):
            for x in range(W):
                p = (x + .5, y + .5)
                d1 = sgn(*p, ax, ay, bx, by); d2 = sgn(*p, bx, by, cx, cy); d3 = sgn(*p, cx, cy, ax, ay)
                if not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0)): s.px(x, y, c)
    def text(s, x0, y0, lines):  # stamp literal rows; ' ' is skip
        for i, row in enumerate(lines):
            for j, ch in enumerate(row):
                if ch != ' ': s.px(x0 + j, y0 + i, ch)
    def strings(s): return [''.join(r) for r in s.g]

def hexrgb(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
def mix(a, b, t): return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
DARK = (24, 16, 40); LIGHT = (255, 240, 210)
# Shading: each material is a flat fill; a 1-2px darker band where it ends to the lower right, a faint
# lighter edge where it starts upper left. Letters in FLAT skip shading (eyes, trim dots, glints).
FLAT = set('eo*')
def render(rows, pal):
    h, w = len(rows), len(rows[0])
    at = lambda x, y: rows[y][x] if 0 <= x < w and 0 <= y < h else '.'
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            c = at(x, y)
            if c == '.':
                n = [at(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
                inside = [k for k in n if k != '.']
                if inside:
                    base = hexrgb(pal[inside[0]]) if inside[0] in pal else DARK
                    img.putpixel((x, y), mix(base, DARK, 0.86) + (255,))
                continue
            col = hexrgb(pal[c])
            if c not in FLAT:
                ne = lambda dx, dy: at(x + dx, y + dy) != c
                if ne(1, 0) or ne(0, 1) or (ne(2, 0) and ne(1, 1)):
                    col = mix(col, DARK, 0.32)
                elif ne(-1, 0) or ne(0, -1):
                    col = mix(col, LIGHT, 0.08)
            img.putpixel((x, y), col + (255,))
    return img

def sheet(items, path, scale=6, cols=4, bg=(46, 64, 38)):
    # big renders with labels' slots in a grid, then a strip at in-game size (2x) on grass-ish ground
    cw = 32 * scale + 16
    rows_n = (len(items) + cols - 1) // cols
    out = Image.new('RGBA', (cols * cw, rows_n * cw + 64 + 24), bg + (255,))
    for i, (label, rows, pal) in enumerate(items):
        im = render(rows, pal).resize((32 * scale, 32 * scale), Image.NEAREST)
        out.alpha_composite(im, ((i % cols) * cw + 8, (i // cols) * cw + 8))
    y = rows_n * cw + 12
    for i, (label, rows, pal) in enumerate(items):
        out.alpha_composite(render(rows, pal).resize((64, 64), Image.NEAREST), (8 + i * 72, y))
    out.save(path)
