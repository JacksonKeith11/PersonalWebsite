# Overlords' units, part 3: the ten added in the roster review (November 2026). Each function returns
# (rows, palette). See kit.py for the letters and docs/overlords.md for the look.
from kit import (G, Fig, pal, lean, ORIGIN, SKIN, SKIN_DARK, STEEL, GOLD, BOOTS, BONE, FROG, WOOD, blade_up, bow,
                 shield, quadruped)
from units1 import skeleton_fig
from units2 import dwarf, frog_head, ear

E, T, R = ORIGIN['emberforged'], ORIGIN['thornwood'], ORIGIN['gravebound']
S_, I, L, M = ORIGIN['skyborne'], ORIGIN['ironhold'], ORIGIN['starlit'], ORIGIN['mirefolk']
ELF = {'s': '#e8c8b0', 'S': '#b8987e'}


def cinder_priest():
    """A bald priest in a charcoal robe, swinging a censer of embers."""
    p = pal(E, SKIN_DARK, GOLD, {'*': '#ffd23f'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head()
    g.rect(14, 13, 17, 28, 'x')  # an orange stole
    g.px(16, 7, 'x')  # an ember mark on the brow
    g.px(17, 6, 'x')
    hx, hy = f.hand
    g.line(hx, hy, hx + 3, hy + 3, 'g')  # the censer on its chain
    g.ell(hx + 4, hy + 5, 2, 2, 'g')
    g.px(hx + 4, hy + 5, '*')
    g.px(hx + 5, hy + 2, 'x')
    g.px(hx + 6, hy + 1, 'y')
    return g.strings(), p


def bog_knight():
    """A frogfolk knight in mossy plate behind a big round shield."""
    p = pal(M, FROG, STEEL, GOLD, {'a': '#5a7a5a', 'A': '#3e5a40'})
    g = G(p)
    f = Fig(g).body(torso='a', arms='a', legs='A', belt='y').head()
    frog_head(f, g)
    g.rect(12, 5, 19, 6, 'a')  # a helm band between the eyes
    blade_up(g, f.hand, 8)
    shield(g, 5, 13, 'x', 'C', emblem='y', w=8, h=12, round_=True)
    return g.strings(), p


def wind_archer():
    """A Skyborne archer with a feather in white hair and a long bow."""
    p = pal(S_, ELF, BOOTS, {'h': '#f0f0f4', 'w': '#8a6a3a', 'z': '#e0c060'})
    g = G(p)
    f = Fig(g).body(belt='y').head().hair('h', long=True)
    ear(g, f)
    g.line(11, 5, 8, 1, 'z')  # a feather
    g.rect(10, 15, 11, 25, 'x')  # a short cape
    bow(g, f.hand, 'w', 'x')
    g.line(f.hand[0] - 3, f.hand[1] - 2, f.hand[0] + 3, f.hand[1] - 2, 'x')  # an arrow nocked
    return g.strings(), p


def moonshadow():
    """A Starlit assassin, hooded in midnight, with two crescent blades."""
    p = pal(L, ELF, STEEL, {'*': '#e8f0ff'})
    g = G(p)
    f = Fig(g).body(belt='x', torso='C', arms='C', legs='C').head().hood('c', 'C')
    g.px(17, 10, '*')
    g.px(19, 10, '*')
    hx, hy = f.hand
    for i, (dx, dy) in enumerate(((1, -1), (2, -2), (3, -2), (4, -1), (4, 0))):  # crescent blades
        g.px(hx + dx, hy + dy, 'l')
    bx, by = f.back_hand
    for dx, dy in ((-1, 1), (-2, 2), (-3, 2), (-4, 1)):
        g.px(bx + dx, by + dy, 'l')
    g.px(22, 4, '*')
    return lean(g.strings(), 2), p


def bog_colossus():
    """A hulking frogman, moss on its shoulders, a stump of a club."""
    p = pal(M, {'s': '#6a8a46', 'S': '#4e6a34'}, {'z': '#c8b060', 'w': '#5a4a32', 'W': '#3e3222'})
    g = G(p)
    f = Fig(g, 'big').body(torso='s', arms='s', legs='s', boots='S', belt='c').head()
    frog_head(f, g)
    g.ell(16, 18, 5, 3.5, 'z')  # a pale belly
    g.rect(8, 11, 13, 12, 'x')  # moss
    g.rect(20, 11, 25, 12, 'x')
    hx, hy = f.hand
    g.rect(hx - 1, hy - 9, hx + 2, hy + 1, 'w')  # a club
    g.rect(hx - 2, hy - 11, hx + 3, hy - 8, 'w')
    return g.strings(), p


def rune_smith():
    """A dwarf with a hammer whose runes glow."""
    p = pal(I, SKIN, STEEL, BOOTS, {'h': '#d8d0c0', '*': '#7ae8ff'})
    g = G(p)
    f = dwarf(g, torso='c', helm=False)
    g.rect(12, 6, 19, 7, 'x')  # a leather cap
    g.rect(13, 5, 18, 5, 'x')
    hx, hy = f.hand
    g.line(hx, hy + 2, hx, hy - 8, 'w')
    g.rect(hx - 2, hy - 12, hx + 3, hy - 8, 'm')
    g.px(hx, hy - 10, '*')
    g.px(hx + 1, hy - 11, '*')
    g.px(hx + 2, hy - 10, '*')
    g.px(10, 20, '*')  # a rune on the apron
    g.px(11, 21, '*')
    return g.strings(), p


def ember_wyrm():
    """A small dragon of coal and fire, wings up, flame in its jaws."""
    p = pal(E, {'c': '#4a3a3e', 'C': '#2e2428', '*': '#ffd23f', 'z': '#a8443a'})
    g = G(p)
    g.rows(2, 5, [(9, 10), (7, 11), (5, 12), (3, 13), (1, 13), (0, 14), (1, 14), (3, 14), (6, 13), (9, 13)], 'z')  # a wing raised
    for x in (4, 8, 12):
        g.line(x + 2, 6, x + 4, 13, 'C')
    g.ell(13, 20, 8, 5.5, 'c')  # the body
    g.ell(14, 22.5, 6, 2.5, 'z')  # its belly
    for lx in (7, 10, 16, 19):
        g.rect(lx, 25, lx + 2, 29, 'C')
        g.rect(lx - 1, 30, lx + 2, 30, 'C')
    g.line(5, 19, 1, 23, 'c', 2)  # the tail
    g.px(0, 24, 'x')
    g.px(1, 25, 'x')
    g.ell(21, 14, 3, 4, 'c')  # a thick neck
    g.ell(24, 9, 4.5, 3.5, 'c')  # the head
    g.rect(26, 9, 30, 12, 'c')
    g.rect(27, 12, 30, 12, 'C')
    g.px(25, 8, '*')
    g.line(21, 6, 18, 2, 'C', 2)  # horns
    g.line(24, 5, 23, 1, 'C')
    g.px(31, 10, 'x')  # fire in its jaws
    g.px(31, 11, 'y')
    g.px(30, 13, 'x')
    for x, y in ((9, 18), (14, 17), (18, 21), (11, 21)):  # embers in its scales
        g.px(x, y, 'x')
    return g.strings(), p


def old_mossheart():
    """A great forest stag, moss on its back and blossoms in its antlers."""
    p = pal(T, {'c': '#7a5a3a', 'C': '#5a4028', '*': '#ffe0f0', 'q': '#e890b0', 'h': '#d8c8a0'})
    g = G(p)
    g.ell(13, 18, 8, 4.5, 'c')  # the body
    for lx in (7, 9, 16, 18):  # long legs
        g.rect(lx, 21, lx + 1, 30, 'C')
    g.rect(5, 15, 6, 17, 'h')  # a pale tail
    g.ell(20, 13, 2.5, 4, 'c')  # the neck
    g.ell(23, 10, 3.5, 2.5, 'c')  # the head
    g.rect(24, 10, 28, 12, 'c')
    g.px(28, 11, 'e')
    g.px(23, 9, 'e')
    g.rect(21, 7, 22, 8, 'C')  # an ear
    for x0, lean_ in ((21, -1), (24, 1)):  # wide antlers
        g.line(x0, 7, x0 + 3 * lean_, 0, 'h')
        g.line(x0 + lean_, 5, x0 + 4 * lean_, 4, 'h')
        g.line(x0 + 2 * lean_, 3, x0 + 5 * lean_, 1, 'h')
    for x, y, c in ((18, 0, 'q'), (28, 1, 'q'), (26, 4, '*'), (16, 3, '*')):
        g.px(x, y, c)
    g.rows(6, 13, [(2, 12), (0, 13), (1, 11)], 'y')  # moss over its back
    g.px(9, 12, 'q')
    g.px(15, 12, '*')
    g.px(12, 13, 'x')
    return g.strings(), p


def bone_tyrant():
    """A towering skeleton king in a violet robe, crowned, with a greatsword."""
    p = pal(R, BONE, STEEL, GOLD, {'*': '#c8f0d8'})
    g = G(p)
    f = Fig(g, 'big')
    f.body(torso='c', arms='s', legs='s', boots='S', skin='s', belt='g')
    f.cape('x')
    for y in (13, 15, 17, 19):  # ribs showing through the open robe
        g.rect(14, y, 19, y, 's')
    f.head(glow='*')
    g.rect(int(f.hx), int(f.hy + 2), int(f.hx) + 3, int(f.hy + 2), 'C')
    f.crown('g', '*')
    blade_up(g, f.hand, 13, c='l', guard='g')
    return g.strings(), p


def toad_brawler():
    """A stocky frogfolk boxer, fists wrapped, tongue out."""
    p = pal(M, FROG, {'z': '#e8e0c8', 'q': '#d86a7a'})
    g = G(p)
    f = Fig(g, 'short').body(torso='s', arms='s', legs='c', belt='y').head()
    frog_head(f, g)
    hx, hy = f.hand
    g.rect(hx - 1, hy - 1, hx + 1, hy + 1, 'z')  # wrapped fists
    bx, by = f.back_hand
    g.rect(bx - 1, by - 3, bx + 1, by - 1, 'z')
    g.line(int(f.hx + f.hrx), int(f.hy + 2), int(f.hx + f.hrx) + 4, int(f.hy + 3), 'q')  # tongue
    return lean(g.strings(), 1), p


def sapling():
    """A young tree on two root feet (the Seed of the Elder Grove grows them)."""
    p = pal(T, WOOD, {'*': '#e0d070'})
    g = G(p)
    g.rect(14, 17, 18, 26, 'w')
    g.rect(13, 27, 15, 29, 'W')
    g.rect(17, 27, 19, 29, 'W')
    g.ell(16, 14, 5, 4, 'c')
    g.ell(17.5, 12.5, 2.5, 1.6, 'y')
    g.line(18, 20, 21, 17, 'w')
    g.px(15, 20, '*')
    g.px(17, 20, '*')
    return g.strings(), p
