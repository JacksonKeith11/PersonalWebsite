# Overlords' small art: 16x16 icons for items, traits and projectiles, drawn with the same letters,
# shading and outline as the unit sprites (kit.py), on a 16x16 grid. Each function returns (rows, palette).
# Trait glyphs fit in the middle 10x10 so an emblem can be the same glyph inside a badge.
from kit import G as _G, pal, hexrgb, mix

N = 16


class G(_G):
    """kit's grid at 16x16."""

    def __init__(s, p, n=N):
        s.n = n
        s.g = [['.'] * n for _ in range(n)]
        s.pal = p

    def px(s, x, y, c):
        if 0 <= x < s.n and 0 <= y < s.n:
            s.g[y][x] = c

    def tri(s, pts, c):
        (ax, ay), (bx, by), (cx, cy) = pts

        def sgn(px, py, x1, y1, x2, y2):
            return (px - x2) * (y1 - y2) - (x1 - x2) * (py - y2)
        for y in range(s.n):
            for x in range(s.n):
                p = (x + .5, y + .5)
                d1, d2, d3 = sgn(*p, ax, ay, bx, by), sgn(*p, bx, by, cx, cy), sgn(*p, cx, cy, ax, ay)
                if not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0)):
                    s.px(x, y, c)


# The icons' materials. Capitals are made a quarter darker by pal() where not given.
BASE = {
    'm': '#a8b0bc', 'M': '#7a8494', 'l': '#e4eaf0', 'g': '#d0a840', 'w': '#7a5432', 'k': '#8a5a34',
    'r': '#c8443a', 'b': '#4a7ad8', 'p': '#9a64d0', 'n': '#5aa84a', 'f': '#ff7a1a', 'y': '#ffd23f',
    'i': '#a8e0f0', 't': '#3aa0a0', 'u': '#ddd4c2', 'h': '#ece0c4', 'c': '#6a5a8a', 'v': '#5a3a7a',
    'd': '#3a3a48', 'q': '#e86a8a', 'z': '#8ad0ff',
}


def P(**glow):
    """A palette: the base materials plus `*` (a glow, never shaded) and any overrides."""
    return pal(BASE, {'*': glow.pop('glow', '#ffffff')}, **glow)


# ------------------------------------------------------------------ shapes
def sword(g, blade='l', guard='g', grip='w', x=0, y=0, long=8, gem=None):
    """A sword pointing up and right, the hilt at the lower left."""
    g.line(5 + x, 10 + y, 5 + long + x, 10 - long + y, blade, 2)
    g.line(3 + x, 9 + y, 6 + x, 12 + y, guard)
    g.line(3 + x, 12 + y, 4 + x, 11 + y, grip)
    g.px(2 + x, 13 + y, guard)
    if gem:
        g.px(5 + x, 10 + y, gem)


def axe_head(g, x, y, c='m', edge='l', r=3):
    for i in range(-r, r + 1):
        w = r - abs(i) // 2
        g.rect(x + 1, y + i, x + w, y + i, c)
        g.px(x + w + 1, y + i, edge)


def bow_shape(g, x=0, c='k', string='h'):
    for xx, yy in ((5, 1), (7, 2), (8, 3), (9, 5), (9, 7), (9, 9), (8, 11), (7, 12), (5, 13)):
        g.px(xx + x, yy, c)
        g.px(xx + x - 1, yy, c) if yy in (1, 13) else None
    g.px(6 + x, 1, c)
    g.px(6 + x, 13, c)
    g.line(4 + x, 2, 4 + x, 12, string)


def rod_shape(g, top='*', haft='w', orb=True):
    g.line(3, 13, 10, 6, haft, 2)
    if orb:
        g.ell(11.5, 4.5, 2.6, 2.6, top)
    else:
        g.rect(10, 3, 12, 5, top)


def drop(g, c='b', hi='*'):
    g.rows(7, 2, [(0, 1), (0, 1), (-1, 2), (-2, 3), (-3, 4), (-3, 4), (-3, 4), (-3, 4), (-2, 3), (-1, 2)], c)
    g.px(6, 7, hi)
    g.px(6, 8, hi)


def vest_shape(g, c='m', d='M', trim='g'):
    g.rect(3, 4, 12, 13, c)
    g.rect(1, 4, 2, 8, c)
    g.rect(13, 4, 14, 8, c)
    g.rect(6, 2, 9, 4, '.')
    g.rect(6, 4, 9, 5, d)
    for y in (7, 10):
        g.rect(4, y, 11, y, d)
    g.rect(3, 13, 12, 13, trim)


def cloak_shape(g, c='c', clasp='g'):
    g.rows(5, 2, [(1, 4), (0, 5), (-1, 6), (-1, 6), (-2, 7), (-2, 7), (-2, 7), (-3, 8), (-3, 8), (-3, 8), (-4, 9), (-4, 9)], c)
    g.rect(6, 2, 9, 3, c.upper())
    g.px(7, 4, clasp)
    g.px(8, 4, clasp)


def belt_shape(g, c='k', buckle='g', big=False):
    g.rect(1, 6, 14, 9, c)
    g.rect(1, 10, 14, 10, c.upper())
    if big:
        g.rect(5, 4, 10, 11, buckle)
        g.rect(7, 6, 8, 9, c)
    else:
        g.rect(6, 5, 9, 10, buckle)
        g.rect(7, 7, 8, 8, c)


def shield_shape(g, c='m', rim='g', emblem=None):
    g.rect(3, 2, 12, 9, rim)
    g.rows(4, 10, [(0, 7), (1, 6), (2, 5), (3, 4)], rim)
    g.rect(4, 3, 11, 9, c)
    g.rows(5, 10, [(0, 5), (1, 4), (2, 3)], c)
    if emblem:
        g.rect(7, 4, 8, 10, emblem)
        g.rect(5, 6, 10, 7, emblem)


def badge(g, ring='g', fill='d'):
    """An emblem's round badge; the trait's glyph goes inside."""
    g.ell(7.5, 7.5, 7.3, 7.3, ring)
    g.ell(7.5, 7.5, 6.0, 6.0, fill)


# ------------------------------------------------------------------ components
def sword_c():
    p = P()
    g = G(p)
    sword(g)
    return g.strings(), p


def bow_c():
    p = P()
    g = G(p)
    bow_shape(g, 2)
    g.line(3, 7, 13, 7, 'u')
    g.px(13, 6, 'm')
    g.px(13, 8, 'm')
    g.px(14, 7, 'm')
    return g.strings(), p


def rod_c():
    p = P(glow='#c8a0ff')
    g = G(p)
    rod_shape(g)
    return g.strings(), p


def tear_c():
    p = P(glow='#e0f4ff')
    g = G(p)
    drop(g, 'b')
    return g.strings(), p


def vest_c():
    p = P()
    g = G(p)
    vest_shape(g)
    return g.strings(), p


def cloak_c():
    p = P()
    g = G(p)
    cloak_shape(g, 'v')
    return g.strings(), p


def belt_c():
    p = P()
    g = G(p)
    belt_shape(g)
    return g.strings(), p


def sigil_c():
    p = P(glow='#fff2a0')
    g = G(p)
    g.ell(7.5, 7.5, 6.3, 6.3, 'g')
    g.ell(7.5, 7.5, 4.6, 4.6, 'd')
    g.rect(7, 4, 8, 11, '*')
    g.rect(4, 7, 11, 8, '*')
    return g.strings(), p


# ------------------------------------------------------------------ finished items
def greatsword():
    p = P(glow='#ff6a5a')
    g = G(p)
    g.line(4, 11, 13, 2, 'l', 3)
    g.line(2, 9, 7, 14, 'g')
    g.line(1, 14, 3, 12, 'w', 2)
    g.px(5, 11, '*')
    return g.strings(), p


def ravager():
    p = P()
    g = G(p)
    g.line(3, 14, 10, 3, 'w', 2)
    axe_head(g, 9, 5, 'r', 'l', 4)
    return g.strings(), p


def spellblade():
    p = P(glow='#c8a0ff')
    g = G(p)
    sword(g, blade='p', gem='*')
    for x, y in ((12, 6), (9, 2), (14, 3)):
        g.px(x, y, '*')
    return g.strings(), p


def mana_edge():
    p = P(glow='#8ad0ff')
    g = G(p)
    sword(g, blade='b', gem='*')
    g.px(13, 1, '*')
    return g.strings(), p


def sunder_axe():
    p = P()
    g = G(p)
    g.line(7, 14, 7, 2, 'w', 2)
    for i in range(-3, 4):  # a head both ways
        w = 3 - abs(i) // 2
        g.rect(9, 5 + i, 9 + w, 5 + i, 'm')
        g.rect(6 - w, 5 + i, 6, 5 + i, 'm')
        g.px(10 + w, 5 + i, 'l')
        g.px(5 - w, 5 + i, 'l')
    return g.strings(), p


def hexblade():
    p = P(glow='#b080ff')
    g = G(p)
    for i, (x, y) in enumerate(((5, 10), (6, 9), (7, 8), (8, 6), (9, 5), (10, 4), (11, 3), (12, 3), (13, 2))):
        g.px(x, y, 'v')
        g.px(x + 1, y + 1, 'p')
    g.line(3, 9, 6, 12, 'g')
    g.line(3, 12, 4, 11, 'w')
    g.px(2, 13, '*')
    g.px(13, 1, '*')
    return g.strings(), p


def cleaver():
    p = P()
    g = G(p)
    g.rect(4, 2, 12, 8, 'm')
    g.rect(4, 8, 12, 8, 'l')
    g.px(11, 3, 'd')
    g.rect(2, 4, 3, 5, 'g')
    g.line(1, 13, 3, 6, 'w', 2)
    return g.strings(), p


def twin_bow():
    p = P()
    g = G(p)
    bow_shape(g, -1)
    bow_shape(g, 4, 'g')
    return g.strings(), p


def storm_rod():
    p = P(glow='#fff6a0')
    g = G(p)
    g.line(3, 13, 9, 7, 'w', 2)
    for x, y in ((10, 6), (11, 5), (10, 4), (11, 3), (12, 2), (13, 1), (12, 5), (13, 4)):
        g.px(x, y, '*')
    return g.strings(), p


def harp():
    p = P()
    g = G(p)
    g.line(3, 2, 3, 13, 'g', 2)
    g.line(3, 2, 12, 6, 'g')
    g.line(12, 6, 11, 13, 'g')
    g.rect(3, 13, 11, 13, 'g')
    for x in (6, 8, 10):
        g.line(x, 4 + (x - 6) // 2, x, 12, 'h')
    return g.strings(), p


def duel_guard():
    p = P()
    g = G(p)
    g.ell(7.5, 7.5, 5.5, 5.5, 'm')
    g.ell(7.5, 7.5, 3.5, 3.5, 'k')
    g.ell(7.5, 7.5, 1.4, 1.4, 'g')
    return g.strings(), p


def galeband():
    p = P(glow='#e8f8ff')
    g = G(p)
    for y, (a, b) in ((3, (3, 10)), (6, (1, 12)), (9, (4, 13)), (12, (2, 9))):
        g.rect(a, y, b, y, 'z')
        g.px(b + 1, y - 1, 'z')
    g.px(11, 2, '*')
    g.px(14, 8, '*')
    return g.strings(), p


def giant_bane():
    p = P()
    g = G(p)
    g.line(2, 13, 11, 4, 'w', 2)
    g.tri([(9, 2), (14, 1), (13, 6)], 'm')
    g.rect(2, 11, 3, 14, 'r')
    g.rect(1, 12, 4, 12, 'r')
    return g.strings(), p


def grimoire():
    p = P(glow='#ffe08a')
    g = G(p)
    g.rect(2, 3, 13, 13, 'v')
    g.rect(3, 13, 13, 13, 'h')
    g.rect(2, 3, 3, 13, 'c')
    g.ell(8.5, 8, 2.5, 2.5, 'g')
    g.px(8, 7, '*')
    g.px(9, 8, '*')
    return g.strings(), p


def archstaff():
    p = P(glow='#8ad0ff')
    g = G(p)
    g.line(2, 14, 9, 7, 'w', 2)
    g.ell(11.5, 4.5, 3.2, 3.2, 'b')
    g.ell(11, 4, 1.6, 1.6, '*')
    g.px(8, 4, 'g')
    g.px(13, 9, 'g')
    return g.strings(), p


def ember_mantle():
    p = P(glow='#ffd23f')
    g = G(p)
    cloak_shape(g, 'r')
    for x, y in ((3, 11), (6, 10), (9, 11), (12, 10)):
        g.px(x, y, 'f')
        g.px(x, y - 1, 'y')
    return g.strings(), p


def spellward():
    p = P(glow='#c8a0ff')
    g = G(p)
    shield_shape(g, 'v', 'g')
    g.ell(7.5, 7, 2, 2, '*')
    return g.strings(), p


def lifebloom():
    p = P(glow='#fff2a0')
    g = G(p)
    g.line(3, 14, 9, 8, 'n', 2)
    for dx, dy in ((0, -2), (2, 0), (0, 2), (-2, 0)):
        g.ell(11 + dx, 5 + dy, 1.5, 1.5, 'q')
    g.px(11, 5, '*')
    g.px(5, 10, 'n')
    g.px(4, 9, 'n')
    return g.strings(), p


def chalice():
    p = P(glow='#8ad0ff')
    g = G(p)
    g.rows(2, 2, [(0, 11), (0, 11), (1, 10), (1, 10), (2, 9), (3, 8)], 'g')
    g.rect(3, 2, 12, 2, 'b')
    g.px(5, 1, '*')
    g.px(9, 0, '*')
    g.rect(7, 8, 8, 11, 'g')
    g.rect(4, 12, 11, 13, 'g')
    return g.strings(), p


def frost_aegis():
    p = P(glow='#ffffff')
    g = G(p)
    shield_shape(g, 'i', 'z')
    g.line(7, 3, 7, 11, '*')
    g.line(4, 5, 10, 9, 'z')
    g.line(10, 5, 4, 9, 'z')
    return g.strings(), p


def mana_ward():
    p = P(glow='#8ad0ff')
    g = G(p)
    g.line(3, 1, 7, 7, 'g')
    g.line(12, 1, 8, 7, 'g')
    g.rows(7, 7, [(0, 1), (-1, 2), (-2, 3), (-2, 3), (-1, 2), (0, 1)], 'b')
    g.px(7, 9, '*')
    return g.strings(), p


def bell():
    p = P()
    g = G(p)
    g.rows(7, 2, [(0, 1), (-1, 2), (-2, 3), (-2, 3), (-3, 4), (-3, 4), (-3, 4), (-4, 5), (-5, 6)], 'g')
    g.rect(7, 0, 8, 1, 'k')
    g.rect(7, 11, 8, 12, 'w')
    g.px(4, 4, 'h')
    return g.strings(), p


def bastion():
    p = P()
    g = G(p)
    vest_shape(g, 'm', 'M', 'm')
    g.rect(0, 3, 3, 6, 'l')
    g.rect(12, 3, 15, 6, 'l')
    g.rect(7, 5, 8, 12, 'g')
    return g.strings(), p


def twin_ward():
    p = P()
    g = G(p)
    g.ell(5, 6, 4, 4.5, 'b')
    g.ell(5, 6, 1.5, 1.5, 'g')
    g.ell(10.5, 9.5, 4, 4.5, 'm')
    g.ell(10.5, 9.5, 1.5, 1.5, 'g')
    return g.strings(), p


def spiked_hide():
    p = P()
    g = G(p)
    vest_shape(g, 'k', 'K', 'w')
    for x, y in ((1, 3), (14, 3), (4, 8), (11, 8), (7, 11)):
        g.px(x, y - 1, 'l')
        g.px(x, y, 'm')
    return g.strings(), p


def veil():
    p = P(glow='#fff6c8')
    g = G(p)
    g.ell(7.5, 6, 5.5, 5, 'c')
    g.rows(2, 7, [(0, 11), (0, 11), (0, 11), (1, 10), (1, 10), (2, 9), (3, 8)], 'c')
    g.ell(7.5, 7, 3, 3, 'd')
    for x, y in ((3, 4), (12, 3), (4, 12), (11, 11)):
        g.px(x, y, '*')
    return g.strings(), p


def second_wind():
    p = P()
    g = G(p)
    g.ell(7.5, 7.5, 6, 6, 'n')
    g.ell(8.5, 6.5, 4, 4, '.')
    g.line(4, 12, 11, 3, 'N')
    g.ell(10.5, 9.5, 2.2, 2.2, 'z')
    return g.strings(), p


def colossus_belt():
    p = P(glow='#fff2a0')
    g = G(p)
    belt_shape(g, 'r', 'g', big=True)
    g.px(6, 5, '*')
    return g.strings(), p


def crown():
    p = P(glow='#ff6a8a')
    g = G(p)
    g.rect(2, 7, 13, 12, 'g')
    for x in (2, 7, 12):
        g.rect(x, 3, x + 1, 7, 'g')
    g.rect(4, 5, 5, 7, 'g')
    g.rect(10, 5, 11, 7, 'g')
    g.rect(2, 12, 13, 12, 'G')
    g.px(7, 9, '*')
    g.px(8, 9, '*')
    g.px(4, 10, 'b')
    g.px(11, 10, 'b')
    return g.strings(), p


# ------------------------------------------------------------------ trait glyphs (inside 3..12)
def g_emberforged(g):
    g.rows(7, 3, [(0, 0), (0, 1), (-1, 1), (-1, 2), (-2, 3), (-3, 3), (-3, 4), (-3, 4), (-2, 3)], 'f')
    g.rows(7, 8, [(0, 0), (-1, 1), (-1, 1)], 'y')


def g_thornwood(g):
    g.ell(8, 7, 4, 3, 'n')
    g.line(3, 12, 11, 4, 'w')
    g.line(6, 7, 8, 9, 'N')
    g.px(3, 10, 'w')
    g.px(5, 11, 'w')


def g_tidecallers(g):
    g.rows(3, 5, [(3, 6), (1, 8), (0, 2), (0, 1)], 't')
    g.rows(3, 8, [(4, 9), (0, 9), (0, 9), (1, 8)], 'z')
    g.px(8, 5, 'h')
    g.px(9, 6, 'h')


def g_gravebound(g):
    g.ell(7.5, 6.5, 4, 3.6, 'u')
    g.rect(5, 9, 10, 11, 'u')
    g.rect(5, 6, 6, 7, 'p')
    g.rect(9, 6, 10, 7, 'p')
    g.px(6, 11, 'U')
    g.px(8, 11, 'U')


def g_skyborne(g):
    g.rows(3, 4, [(5, 8), (3, 9), (1, 9), (0, 9), (2, 9), (4, 9)], 'h')
    g.line(4, 6, 9, 6, 'z')
    g.line(5, 8, 10, 8, 'z')
    g.px(12, 3, 'g')


def g_ironhold(g):
    g.rect(3, 4, 12, 6, 'm')
    g.rect(1, 4, 2, 5, 'm')
    g.rect(6, 7, 9, 9, 'M')
    g.rect(4, 10, 11, 11, 'M')
    g.rect(3, 4, 12, 4, 'l')


def g_starlit(g):
    g.text(3, 3, ["    y    ",
                  "   yyy   ",
                  "   yyy   ",
                  "yyyyyyyyy",
                  " yyy*yyy ",
                  "  yyyyy  ",
                  "  yy yy  ",
                  " yy   yy ",
                  " y     y "])


def g_mirefolk(g):
    g.ell(7.5, 8.5, 4.5, 3, 'n')
    g.ell(5, 5.5, 1.7, 1.7, 'n')
    g.ell(10, 5.5, 1.7, 1.7, 'n')
    g.px(5, 5, 'e')
    g.px(10, 5, 'e')
    g.rect(5, 10, 10, 10, 'N')


def g_vanguard(g):
    g.rect(4, 3, 11, 8, 'm')
    g.rows(5, 9, [(0, 5), (1, 4), (2, 3)], 'm')
    g.rect(7, 4, 8, 10, 'r')
    g.rect(5, 5, 10, 6, 'r')


def g_duelist(g):
    g.line(3, 3, 11, 11, 'l')
    g.line(12, 3, 4, 11, 'l')
    g.line(3, 9, 5, 11, 'g')
    g.line(12, 9, 10, 11, 'g')
    g.px(2, 12, 'w')
    g.px(13, 12, 'w')


def g_ranger(g):
    for x, y in ((5, 3), (7, 4), (8, 6), (8, 8), (7, 10), (5, 11)):
        g.px(x, y, 'k')
    g.line(4, 3, 4, 11, 'h')
    g.line(3, 7, 12, 7, 'u')
    g.px(12, 6, 'm')
    g.px(12, 8, 'm')
    g.px(13, 7, 'm')


def g_arcanist(g):
    g.ell(7.5, 7.5, 4.5, 4.5, 'p')
    g.ell(7.5, 7.5, 2.5, 2.5, 'P')
    g.px(7, 7, '*')
    g.px(8, 8, '*')
    g.px(4, 3, '*')
    g.px(12, 11, '*')


def g_mystic(g):
    g.ell(7.5, 7.5, 5, 3, 'h')
    g.ell(7.5, 7.5, 2.2, 2.2, 't')
    g.px(7, 7, 'e')
    g.px(8, 7, 'e')
    g.rect(3, 4, 4, 4, 't')
    g.rect(11, 11, 12, 11, 't')


def g_assassin(g):
    g.line(4, 12, 11, 5, 'l', 2)
    g.line(10, 4, 12, 4, 'l')
    g.line(3, 10, 5, 12, 'd')
    g.px(2, 13, 'r')
    g.ell(10, 10, 1.5, 1.5, 'r')


def g_summoner(g):
    g.ell(7.5, 6, 3.5, 3.5, 'z')
    g.rows(4, 9, [(0, 7), (1, 6), (2, 5)], 'z')
    g.px(6, 6, 'e')
    g.px(9, 6, 'e')
    g.rect(3, 12, 12, 12, 'p')


def g_warden(g):
    g.rect(4, 4, 11, 12, 'm')
    for x in (4, 7, 10):
        g.rect(x, 2, x + 1, 3, 'm')
    g.rect(7, 9, 8, 12, 'd')
    g.px(6, 6, 'd')
    g.px(9, 6, 'd')


GLYPHS = {
    'emberforged': (g_emberforged, '#ffd23f'), 'thornwood': (g_thornwood, '#fff'), 'tidecallers': (g_tidecallers, '#fff'),
    'gravebound': (g_gravebound, '#c8f0d8'), 'skyborne': (g_skyborne, '#fff'), 'ironhold': (g_ironhold, '#fff'),
    'starlit': (g_starlit, '#ffffff'), 'mirefolk': (g_mirefolk, '#fff'), 'vanguard': (g_vanguard, '#fff'),
    'duelist': (g_duelist, '#fff'), 'ranger': (g_ranger, '#fff'), 'arcanist': (g_arcanist, '#ffe8ff'),
    'mystic': (g_mystic, '#fff'), 'assassin': (g_assassin, '#fff'), 'summoner': (g_summoner, '#fff'),
    'warden': (g_warden, '#fff'),
}


def trait_icon(t):
    fn, glow = GLYPHS[t]
    p = P(glow=glow)
    g = G(p)
    fn(g)
    return g.strings(), p


def emblem_icon(t):
    fn, glow = GLYPHS[t]
    p = P(glow=glow)
    g = G(p)
    badge(g)
    fn(g)
    return g.strings(), p


# ------------------------------------------------------------------ projectiles (pointing right)
def p_arrow():
    p = P()
    g = G(p)
    g.line(2, 7, 11, 7, 'k')
    g.tri([(11, 5), (15, 7.5), (11, 10)], 'm')
    g.rect(1, 6, 3, 6, 'h')
    g.rect(1, 8, 3, 8, 'h')
    return g.strings(), p


def p_bolt():
    p = P()
    g = G(p)
    g.line(3, 7, 12, 7, 'w', 1)
    g.rect(3, 8, 12, 8, 'w')
    g.tri([(12, 5), (15, 7.5), (12, 10)], 'l')
    return g.strings(), p


def p_fire():
    p = P(glow='#fff2a0')
    g = G(p)
    g.ell(10, 7.5, 3.5, 3.5, 'f')
    g.rows(2, 6, [(3, 6), (0, 6), (2, 6)], 'f')
    g.ell(10.5, 7.5, 1.8, 1.8, 'y')
    g.px(10, 7, '*')
    return g.strings(), p


def p_water():
    p = P(glow='#ffffff')
    g = G(p)
    g.ell(10, 7.5, 3.5, 3, 't')
    g.rows(3, 6, [(4, 6), (1, 6), (4, 6)], 'z')
    g.px(10, 6, '*')
    return g.strings(), p


def p_bone():
    p = P()
    g = G(p)
    g.rect(4, 7, 11, 8, 'u')
    for x in (3, 12):
        g.rect(x - 1, 6, x, 6, 'u')
        g.rect(x - 1, 9, x, 9, 'u')
    return g.strings(), p


def p_star():
    p = P(glow='#ffffff')
    g = G(p)
    g.line(1, 7, 8, 7, 'Y')
    g.tri([(11, 3), (9, 9), (13, 9)], 'y')
    g.tri([(8, 6), (14, 6), (11, 10)], 'y')
    g.px(11, 7, '*')
    return g.strings(), p


def p_shadow():
    p = P(glow='#e0c8ff')
    g = G(p)
    g.ell(10, 7.5, 3.4, 3.4, 'v')
    g.rows(2, 6, [(4, 6), (0, 6), (3, 6)], 'p')
    g.px(10, 7, '*')
    return g.strings(), p


def p_leaf():
    p = P()
    g = G(p)
    g.ell(9, 7.5, 4.5, 2.4, 'n')
    g.line(3, 8, 13, 7, 'N')
    return g.strings(), p


def p_spit():
    p = P()
    g = G(p)
    g.ell(10.5, 7.5, 2.6, 2.6, 'n')
    g.px(6, 7, 'n')
    g.px(4, 8, 'n')
    g.px(10, 6, 'h')
    return g.strings(), p


def p_shell():
    p = P(glow='#ffd23f')
    g = G(p)
    g.rect(5, 6, 10, 9, 'M')
    g.ell(11, 7.5, 2.3, 2, 'm')
    g.px(3, 7, '*')
    g.px(4, 8, 'f')
    return g.strings(), p


def p_feather():
    p = P()
    g = G(p)
    g.ell(9, 7.5, 5, 2, 'h')
    g.line(2, 8, 14, 7, 'z')
    return g.strings(), p


ITEM_ICONS = {
    'sword': sword_c, 'bow': bow_c, 'rod': rod_c, 'tear': tear_c, 'vest': vest_c, 'cloak': cloak_c, 'belt': belt_c,
    'sigil': sigil_c, 'greatsword': greatsword, 'ravager': ravager, 'spellblade': spellblade, 'mana_edge': mana_edge,
    'sunder_axe': sunder_axe, 'hexblade': hexblade, 'cleaver': cleaver, 'twin_bow': twin_bow, 'storm_rod': storm_rod,
    'harp': harp, 'duel_guard': duel_guard, 'galeband': galeband, 'giant_bane': giant_bane, 'grimoire': grimoire,
    'archstaff': archstaff, 'ember_mantle': ember_mantle, 'spellward': spellward, 'lifebloom': lifebloom,
    'chalice': chalice, 'frost_aegis': frost_aegis, 'mana_ward': mana_ward, 'bell': bell, 'bastion': bastion,
    'twin_ward': twin_ward, 'spiked_hide': spiked_hide, 'veil': veil, 'second_wind': second_wind,
    'colossus_belt': colossus_belt, 'crown': crown,
}
PROJECTILES = {
    'arrow': p_arrow, 'bolt': p_bolt, 'fire': p_fire, 'water': p_water, 'bone': p_bone, 'star': p_star,
    'shadow': p_shadow, 'leaf': p_leaf, 'spit': p_spit, 'shell': p_shell, 'feather': p_feather,
}


def all_icons():
    """{atlas name: function} for every 16x16 icon: item:<key>, trait:<key>, proj:<kind>."""
    out = {}
    for k, f in ITEM_ICONS.items():
        out['item:' + k] = f
    for t in GLYPHS:
        out['trait:' + t] = (lambda t=t: trait_icon(t))
        out['item:emblem_' + t] = (lambda t=t: emblem_icon(t))
    for k, f in PROJECTILES.items():
        out['proj:' + k] = f
    return out
