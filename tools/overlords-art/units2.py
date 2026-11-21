# Overlords' units, part 2: Skyborne, Ironhold, Starlit and Mirefolk, the summons not drawn in part 1,
# and the monsters. Each function returns (rows, palette).
from kit import (G, Fig, pal, lean, ORIGIN, SKIN, SKIN_DARK, STEEL, GOLD, BOOTS, FROG, blade_up, dagger, axe,
                 hammer, spear, staff, bow, crossbow, shield, star, quadruped, golem, blob)

S_, I, L, M = ORIGIN['skyborne'], ORIGIN['ironhold'], ORIGIN['starlit'], ORIGIN['mirefolk']
ELF = {'s': '#e8c8b0', 'S': '#b8987e'}


def ear(g, f, c='s'):
    """A pointed elf ear on the back of the head."""
    x, y = int(f.hx - f.hrx) - 1, int(f.hy)
    g.px(x, y, c)
    g.px(x - 1, y - 1, c)
    g.px(x - 2, y - 2, c)


# ------------------------------------------------------------------ Skyborne: pale blue, white, gold
def sky_sprite():
    p = pal(S_, {'s': '#f0dcc8', 'S': '#c8b49e'}, STEEL, {'h': '#e0c060'})
    g = G(p)
    f = Fig(g, 'small').body(belt='y').head().hair('h')
    g.rows(5, 13, [(4, 6), (2, 7), (0, 7), (1, 7), (3, 7)], 'x')  # a dragonfly's wings
    g.rows(5, 19, [(3, 7), (1, 7), (3, 7)], 'c')
    dagger(g, f.hand)
    return g.strings(), p


def gale_dancer():
    p = pal(S_, SKIN, STEEL, BOOTS, {'h': '#3a2a20', 'z': '#e05a6a'})
    g = G(p)
    f = Fig(g).body(belt='y').head().hair('h', long=True)
    g.rect(12, 13, 19, 14, 'z')  # a long scarf in the wind
    g.line(11, 14, 5, 12, 'z', 2)
    g.line(5, 12, 3, 14, 'z')
    blade_up(g, f.hand, 7, lean=3)
    blade_up(g, f.back_hand, 6, lean=-2)
    return lean(g.strings(), 2), p


def sky_lancer():
    p = pal(S_, SKIN, STEEL, GOLD, BOOTS)
    g = G(p)
    f = Fig(g).body(torso='a', arms='a', legs='A', belt='y')
    f.wings('x', 'c')
    f.head().helm('a', plume='y')
    spear(g, f.hand, length=20, lance=True)
    return g.strings(), p


def cloud_monk():
    p = pal(S_, SKIN, BOOTS, {'z': '#e0a040'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='z', arms='s').head()
    g.rect(12, 15, 15, 21, 'c')  # a blue sash over the shoulder
    g.line(12, 15, 18, 22, 'c')
    g.ell(15, 7, 1, 1, 'x')
    g.rect(f.hand[0], f.hand[1] - 1, f.hand[0] + 1, f.hand[1], 's')
    for dx, dy in ((3, -3), (4, 0), (3, 3)):  # a gust from the fist
        g.px(f.hand[0] + dx, f.hand[1] + dy, 'x')
    return g.strings(), p


def storm_herald():
    p = pal(S_, SKIN, GOLD, {'*': '#fff6a0', 'h': '#f0f0f4'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c')
    f.wings('x', 'C')
    f.head().hair('h', long=True)
    g.rect(13, 15, 18, 15, 'y')
    hx, hy = f.hand
    g.line(hx, hy + 5, hx + 1, hy - 10, 'g')
    for x, y in ((hx + 1, hy - 11), (hx + 2, hy - 12), (hx + 1, hy - 13), (hx + 2, hy - 14), (hx + 3, hy - 15)):
        g.px(x, y, '*')  # a bolt at the staff's head
    return g.strings(), p


def tempest_roc():
    p = pal(S_, {'z': '#e0c060', '*': '#fff6a0'})
    g = G(p)
    g.ell(15, 18, 8, 6, 'c')  # body
    g.ell(23, 10, 4, 4, 'x')  # head
    g.rows(26, 9, [(0, 2), (0, 3), (0, 2)], 'z')  # beak
    g.px(24, 9, 'e')
    g.rows(1, 6, [(10, 13), (7, 14), (4, 14), (2, 14), (0, 13), (0, 12), (1, 11), (3, 10)], 'C')  # raised wing
    g.rows(3, 8, [(8, 12), (5, 12), (3, 12)], 'x')
    g.rect(6, 21, 11, 23, 'x')  # tail
    for x in (13, 17):
        g.rect(x, 24, x + 1, 28, 'z')
        g.rect(x - 1, 29, x + 2, 30, 'z')
    g.px(20, 15, '*')
    return g.strings(), p


# ------------------------------------------------------------------ Ironhold: steel and brass dwarves
def dwarf(g, torso='a', beard='h', helm=True, plume=None, horns=None):
    f = Fig(g, 'short').body(torso=torso, arms=torso, legs='C', belt='x').head()
    if helm:
        f.helm('a', visor=False, plume=plume, horns=horns)
    f.beard(beard)
    return f


def iron_recruit():
    p = pal(I, SKIN, STEEL, BOOTS, {'h': '#a8603a'})
    g = G(p)
    f = dwarf(g, torso='c')
    spear(g, f.hand, length=17)
    shield(g, 6, 18, 'a', 'A', emblem='x', w=6, h=8, round_=True)
    return g.strings(), p


def iron_sentinel():
    p = pal(I, SKIN, STEEL, BOOTS, {'h': '#5a3a24'})
    g = G(p)
    f = dwarf(g, plume='y')
    hammer(g, f.hand)
    shield(g, 5, 14, 'a', 'A', emblem='x', w=7, h=14)
    return g.strings(), p


def iron_crossbow():
    p = pal(I, SKIN, STEEL, BOOTS, {'h': '#d8a050'})
    g = G(p)
    f = dwarf(g, torso='c', helm=False)
    f.hair('h')
    g.rect(12, 9, 20, 10, 'C')  # a leather cap
    crossbow(g, (f.hand[0] - 1, f.hand[1] - 2))
    return g.strings(), p


def iron_duelist():
    p = pal(I, SKIN, STEEL, GOLD, BOOTS, {'h': '#2a2020'})
    g = G(p)
    f = Fig(g).body(torso='a', arms='a', legs='C', belt='x').head().hair('h')
    g.rect(16, 13, 18, 13, 'h')  # moustache
    blade_up(g, f.hand, 11, c='l', guard='x', lean=4)
    shield(g, 8, 17, 'x', 'A', w=4, h=4, round_=True)
    return g.strings(), p


def iron_warlord():
    p = pal(I, SKIN, STEEL, BOOTS, {'h': '#c06a30', 'z': '#d8d0c0'})
    g = G(p)
    f = dwarf(g, horns='z')
    f.cape('y')
    axe(g, f.hand, big=True)
    return g.strings(), p


def iron_engineer():
    p = pal(I, SKIN, STEEL, BOOTS, {'h': '#8a8a8a', '*': '#7fe3ff'})
    g = G(p)
    f = dwarf(g, torso='c', helm=False)
    f.hair('h')
    g.rect(13, 11, 20, 12, 'x')  # goggles
    g.px(15, 12, '*')
    g.px(18, 12, '*')
    hx, hy = f.hand
    g.line(hx, hy + 1, hx + 2, hy - 6, 'm', 1)  # a wrench
    g.rect(hx + 1, hy - 9, hx + 4, hy - 7, 'm')
    g.px(hx + 2, hy - 8, '.')
    g.rect(7, 19, 9, 24, 'x')  # a pack of tools
    return g.strings(), p


def iron_colossus():
    p = pal(I, {'a': '#7a828c', 'A': '#565e68', '*': '#ffb84a'})
    g = G(p)
    golem(g, 'a', 'A', '*')
    for y in (12, 18):  # rivets and plates
        for x in (11, 14, 18, 21):
            g.px(x, y, 'x')
    g.rect(10, 9, 22, 10, 'x')
    return g.strings(), p


def turret():
    p = pal(I, STEEL, {'*': '#ff8a4a'})
    g = G(p)
    g.rect(10, 26, 22, 30, 'A')  # base
    g.rect(12, 22, 20, 25, 'a')
    g.ell(16, 18, 5, 4, 'm')
    g.rect(18, 16, 27, 18, 'M')  # barrel
    g.px(15, 17, '*')
    g.rect(13, 27, 19, 27, 'x')
    return g.strings(), p


# ------------------------------------------------------------------ Starlit: midnight and silver elves
def star_novice():
    p = pal(L, ELF, {'h': '#e8e0c8', '*': '#ffe8a0'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head().hair('h', long=True)
    ear(g, f)
    g.px(14, 20, 'x')
    g.px(17, 24, 'x')
    g.px(13, 26, 'x')
    g.line(f.hand[0], f.hand[1], f.hand[0] + 3, f.hand[1] - 5, 'x')  # a wand
    star(g, f.hand[0] + 4, f.hand[1] - 7)
    return g.strings(), p


def star_archer():
    p = pal(L, ELF, BOOTS, {'h': '#c8c8d8'})
    g = G(p)
    f = Fig(g).body(belt='x').head().hair('h', long=True)
    ear(g, f)
    f.cape('C')
    bow(g, f.hand, 'x', 'y')
    return g.strings(), p


def starlit_blade():
    p = pal(L, ELF, {'l': '#e8eef8'})
    g = G(p)
    f = Fig(g).body(torso='C', arms='C', legs='C', belt='x').head().hood('C', 'c')
    ear(g, f, 'C')
    hx, hy = f.hand  # a crescent blade
    for x, y in ((hx, hy - 1), (hx + 1, hy - 2), (hx + 2, hy - 3), (hx + 3, hy - 5), (hx + 3, hy - 6),
                 (hx + 3, hy - 7), (hx + 2, hy - 9), (hx + 1, hy - 10)):
        g.px(x, y, 'l')
        g.px(x + 1, y, 'l')
    g.px(hx + 5, hy - 6, 'l')
    g.px(hx + 5, hy - 5, 'l')
    return lean(g.strings(), 2), p


def star_warden():
    p = pal(L, ELF, STEEL, BOOTS, {'a': '#9aa4c8', 'A': '#6e78a0', '*': '#ffe8a0'})
    g = G(p)
    f = Fig(g).body(torso='a', arms='a', legs='C', belt='x').head().helm('a', visor=False, plume='x')
    spear(g, f.hand, length=18)
    shield(g, 6, 14, 'c', 'C', w=7, h=11)
    star(g, 9, 19)
    return g.strings(), p


def star_queen():
    p = pal(L, ELF, GOLD, {'h': '#f0ead8', '*': '#ffe8a0'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head().hair('h', long=True).crown('g', '*')
    ear(g, f)
    g.rect(13, 15, 18, 15, 'x')
    for x, y in ((14, 19), (17, 22), (13, 25), (18, 27)):
        g.px(x, y, 'y')
    staff(g, f.hand, top='g', length=18, orb=False)
    star(g, f.hand[0] + 1, f.hand[1] - 15)
    return g.strings(), p


# ------------------------------------------------------------------ Mirefolk: olive frogfolk
def frog_head(f, g, c='s'):
    """A wide frog's head with eyes bulging on top."""
    cx, cy = f.hx, f.hy + 1
    g.ell(cx + 0.5, cy, f.hrx + 1, f.hry - 1, c)
    g.ell(cx - 1, cy - 3, 1.6, 1.6, c)
    g.ell(cx + 3, cy - 3, 1.6, 1.6, c)
    g.px(int(cx - 1), int(cy - 3), 'e')
    g.px(int(cx + 3), int(cy - 3), 'e')
    g.rect(int(cx) - 1, int(cy + 1), int(cx + f.hrx), int(cy + 1), 'S')


def marsh_lurker():
    p = pal(M, FROG, STEEL)
    g = G(p)
    f = Fig(g, 'small').body(torso='c', arms='s', legs='s', boots='S').head()
    frog_head(f, g)
    dagger(g, f.hand)
    return lean(g.strings(), 2), p


def mire_witch():
    p = pal(M, FROG, {'*': '#c8e070'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head()
    frog_head(f, g)
    f.hat('C', band='y', tall=8)
    staff(g, f.hand, top='*', length=15)
    return g.strings(), p


def bog_shaman():
    p = pal(M, FROG, {'z': '#e05a3a'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='s').head()
    frog_head(f, g)
    for x, c in ((12, 'z'), (14, 'y'), (16, 'z'), (18, 'y')):  # a feathered headdress
        g.rect(x, 2, x, 5, c)
    g.rect(12, 5, 19, 5, 'x')
    hx, hy = f.hand  # a totem staff
    g.line(hx, hy + 5, hx, hy - 8, 'w')
    g.rect(hx - 1, hy - 12, hx + 2, hy - 9, 'y')
    g.px(hx, hy - 11, 'e')
    return g.strings(), p


def mire_hag():
    p = pal(M, {'s': '#8a9a6a', 'S': '#6a7a4e'}, {'h': '#c8c0a8', '*': '#c8e070'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='C', arms='C').head().hair('h', long=True)
    g.px(int(f.hx + f.hrx), int(f.hy + 1), 's')  # a hooked nose
    g.px(int(f.hx + f.hrx) + 1, int(f.hy + 2), 's')
    g.ell(23, 26, 4, 3, 'a')  # a little cauldron
    g.rect(20, 23, 26, 23, 'A')
    g.px(22, 22, '*')
    g.px(24, 21, '*')
    return lean(g.strings(), 2), p


def mire_mother():
    p = pal(M, FROG, {'*': '#e0f080', 'z': '#c8b060'})
    g = G(p)
    g.ell(16, 21, 13, 8, 's')  # a huge squat frog
    g.ell(16, 24, 10, 5, 'z')
    g.ell(10, 12, 3.5, 3.5, 's')
    g.ell(22, 12, 3.5, 3.5, 's')
    g.px(10, 11, 'e')
    g.px(22, 11, 'e')
    g.rect(9, 18, 23, 18, 'S')
    for x in (4, 26):
        g.rect(x, 26, x + 3, 30, 'S')
    g.px(15, 15, '*')
    g.px(17, 14, '*')
    return g.strings(), p


def bog_imp():
    p = pal(M, {'s': '#6a8a6a', 'S': '#4e6a4e'}, {'*': '#ffe060'})
    g = G(p)
    f = Fig(g, 'small').body(torso='s', arms='s', legs='s', boots='S').head(glow='*')
    g.px(13, 11, 's')
    g.px(12, 10, 's')
    g.px(19, 11, 's')
    g.px(20, 10, 's')
    g.line(12, 26, 8, 28, 'S')
    return g.strings(), p


def mire_spawn():
    p = pal(M, FROG)
    g = G(p)
    blob(g, 's', 'S', cx=17, w=7, h=5)
    g.line(10, 25, 5, 23, 'S', 2)  # a tadpole's tail
    return g.strings(), p


# ------------------------------------------------------------------ monsters
def wolf():
    p = pal({'c': '#7a7a80', 'C': '#56565c'})
    g = G(p)
    quadruped(g, 'c', 'C', length=13, tall=7)
    return g.strings(), p


def bandit():
    p = pal(SKIN, STEEL, BOOTS, {'c': '#6a5a4a', 'C': '#4a3e32', 'x': '#8a3030'})
    g = G(p)
    f = Fig(g).body(belt='x').head().hood('c', 'C')
    g.rect(16, 11, 19, 12, 'x')  # a mask over the mouth
    blade_up(g, f.hand, 8, lean=2)
    return g.strings(), p


def bandit_chief():
    p = pal(SKIN_DARK, STEEL, BOOTS, {'c': '#8a3030', 'C': '#622222', 'h': '#2a2020', 'a': '#6a5a4a', 'A': '#4a3e32'})
    g = G(p)
    f = Fig(g, 'big').body(torso='a', arms='c', legs='C', belt='h').head().hair('h').beard('h', long=False)
    axe(g, f.hand, big=True)
    return g.strings(), p


def stone_golem():
    p = pal({'a': '#8a8a84', 'A': '#626260', '*': '#7fe3ff', 'x': '#6a8a5a'})
    g = G(p)
    golem(g, 'a', 'A', '*')
    g.rect(10, 9, 13, 10, 'x')  # moss
    g.rect(20, 20, 22, 21, 'x')
    return g.strings(), p
