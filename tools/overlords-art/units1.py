# Overlords' units, part 1: Emberforged, Thornwood, Tidecallers and Gravebound. Each function returns
# (rows, palette). See kit.py for the letters and docs/overlords.md for the look.
from kit import (G, Fig, pal, lean, ORIGIN, SKIN, SKIN_DARK, STEEL, WOOD, GOLD, BONE, BOOTS, blade_up, dagger,
                 hammer, trident, staff, bow, shield, quadruped, tree, golem)

E, T, D, R = ORIGIN['emberforged'], ORIGIN['thornwood'], ORIGIN['tidecallers'], ORIGIN['gravebound']
ASH = {'s': '#8a8088', 'S': '#625a62'}


# ------------------------------------------------------------------ Emberforged: charcoal and fire
def ashling():
    p = pal(E, ASH, STEEL, BOOTS, h='#ff7a1a', H='#ffd23f')
    g = G(p)
    f = Fig(g, 'small').body(belt='x').head()
    g.rows(13, 8, [(2, 3), (1, 4), (0, 5), (0, 6)], 'h')  # hair of flame
    g.px(15, 9, 'H')
    g.px(17, 10, 'H')
    dagger(g, f.hand)
    dagger(g, (f.back_hand[0] - 3, f.back_hand[1]))
    return g.strings(), p


def ember_squire():
    p = pal(E, SKIN_DARK, STEEL, GOLD, BOOTS, WOOD)
    g = G(p)
    f = Fig(g).body(torso='a', arms='a', legs='A', belt='x').head().helm('a', plume='x')
    blade_up(g, f.hand, 9)
    shield(g, 8, 15, 'C', 'x', emblem='y', w=5, h=8)
    return g.strings(), p


def forge_hound():
    p = pal(E, {'b': '#2a2226', '*': '#ffd23f'})
    g = G(p)
    hx, hy = quadruped(g, 'c', 'C', length=13, tall=7)
    g.rect(9, 18, 16, 18, 'x')
    g.rect(11, 17, 13, 17, 'y')
    g.px(hx + 1, hy - 1, '*')
    g.line(4, 16, 2, 13, 'x')
    return g.strings(), p


def cinder_rogue():
    p = pal(E, SKIN, STEEL, BOOTS)
    g = G(p)
    f = Fig(g).body(belt='x').head().hood('c', 'C')
    g.rect(13, 13, 19, 14, 'x')  # scarf
    g.rect(10, 15, 11, 18, 'x')
    dagger(g, f.hand)
    return g.strings(), p


def ember_mage():
    p = pal(E, SKIN, WOOD, GOLD, h='#d8d0c0')
    g = G(p)
    f = Fig(g).body(robe=True, torso='x', arms='x').head().hat('C', band='y', tall=7).beard('h')
    g.rect(15, 15, 16, 28, 'C')
    staff(g, f.hand, top='y', length=16)
    g.px(f.hand[0] + 1, f.hand[1] - 14, 'x')
    g.px(f.hand[0] + 2, f.hand[1] - 15, 'x')
    return g.strings(), p


def lava_giant():
    p = pal(E, {'a': '#4a3a3a', 'A': '#2e2426', '*': '#ffb03a'})
    g = G(p)
    golem(g, 'a', 'A', '*')
    for x, y in ((12, 11), (20, 19), (11, 20), (21, 12), (14, 22)):
        g.px(x, y, 'x')
        g.px(x + 1, y, 'x')
    g.rows(14, 1, [(1, 2), (0, 3), (0, 5)], 'x')
    return g.strings(), p


def phoenix_knight():
    p = pal(E, SKIN_DARK, STEEL, GOLD, BOOTS, {'a': '#a83a2a', 'A': '#7a2a20'})
    g = G(p)
    f = Fig(g).body(torso='a', arms='a', legs='A', belt='g')
    f.wings('x', 'y')
    f.head().helm('a', plume='y')
    blade_up(g, f.hand, 10, c='y', guard='g')
    return g.strings(), p


# ------------------------------------------------------------------ Thornwood: bark and leaves
def bramble_guard():
    p = pal(T, SKIN, WOOD, BOOTS)
    g = G(p)
    f = Fig(g).body(torso='a', arms='a', legs='c', belt='x').head()
    g.ell(15, 6, 5, 2.5, 'y')  # leaf helm
    g.rect(11, 6, 20, 7, 'c')
    hammer(g, f.hand, head='w', haft='W')
    shield(g, 7, 14, 'x', 'W', w=6, h=9)
    for y in (16, 19):
        g.rect(8, y, 11, y, 'W')
    return g.strings(), p


def thornling():
    p = pal(T, SKIN, WOOD, BOOTS)
    g = G(p)
    f = Fig(g, 'small').body(belt='x').head()
    g.ell(15.5, 13, 5, 3.5, 'c')  # leaf hood
    g.rect(15, 14, 19, 16, 's')
    g.px(15, 15, 'e')
    g.px(18, 15, 'e')
    g.px(10, 11, 'y')
    bow(g, f.hand)
    return g.strings(), p


def moss_brute():
    p = pal(T, {'s': '#7a8a5a', 'S': '#5a6a40'}, WOOD, BOOTS)
    g = G(p)
    f = Fig(g, 'big').body(torso='s', arms='s', legs='x', belt='c').head()
    g.rect(9, 12, 23, 14, 'c')  # moss over the shoulders
    g.ell(17, 3, 4, 2, 'y')
    g.rect(13, 17, 16, 19, 'y')
    hammer(g, f.hand, head='w', haft='W')
    return g.strings(), p


def thorn_dryad():
    p = pal(T, {'s': '#b8c890', 'S': '#8a9a68'}, WOOD)
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='s').head()
    g.ell(14, 7, 5, 4, 'y')  # leaf hair
    g.rect(10, 7, 12, 15, 'y')
    g.line(f.hand[0], f.hand[1], f.hand[0] + 5, f.hand[1] - 5, 'x')
    g.px(f.hand[0] + 5, f.hand[1] - 6, 'y')
    g.px(f.hand[0] + 3, f.hand[1] - 3, 'y')
    return g.strings(), p


def thorn_stalker():
    p = pal(T, SKIN, STEEL, BOOTS, WOOD)
    g = G(p)
    f = Fig(g).body(belt='x').head().hood('c', 'C')
    g.rect(16, 9, 19, 11, 'x')  # bark mask
    g.px(17, 10, 'e')
    g.px(19, 10, 'e')
    blade_up(g, f.hand, 6, lean=3)
    g.line(f.back_hand[0], f.back_hand[1], f.back_hand[0] - 3, f.back_hand[1] + 3, 'l')
    return g.strings(), p


def thorn_shaman():
    p = pal(T, SKIN_DARK, WOOD, {'*': '#a0e060'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head()
    g.rect(12, 5, 19, 6, 'x')
    g.line(13, 5, 10, 1, 'x')   # antlers
    g.line(11, 3, 9, 3, 'x')
    g.line(18, 5, 21, 1, 'x')
    g.line(20, 3, 22, 3, 'x')
    g.rect(13, 15, 18, 16, 'y')
    staff(g, f.hand, top='*', length=16)
    return g.strings(), p


def elder_oak():
    p = pal(T, WOOD, {'*': '#e0d070'})
    g = G(p)
    tree(g, 'w', 'W', 'c', 'y', big=True)
    return g.strings(), p


def treant():
    p = pal(T, WOOD, {'*': '#e0d070'})
    g = G(p)
    tree(g, 'w', 'W', 'c', 'y')
    return g.strings(), p


# ------------------------------------------------------------------ Tidecallers: teal and coral
def tide_acolyte():
    p = pal(D, SKIN, WOOD, {'*': '#bfe8e0'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head().hood('c', 'C')
    g.rect(14, 16, 17, 27, 'y')
    staff(g, f.hand, top='x', length=15)
    return g.strings(), p


def tide_scout():
    p = pal(D, SKIN, WOOD, BOOTS, h='#3a2a20')
    g = G(p)
    f = Fig(g).body(belt='x').head().hair('h')
    g.rect(12, 6, 20, 7, 'c')  # bandana
    g.rect(10, 7, 11, 9, 'c')
    bow(g, f.hand, 'w', 'y')
    return g.strings(), p


def reef_guard():
    p = pal(D, {'s': '#7ab0a8', 'S': '#5a8a84'}, STEEL, BOOTS, WOOD)
    g = G(p)
    f = Fig(g).body(torso='a', arms='a', legs='A', belt='x').head().helm('a', visor=False)
    g.rect(13, 4, 18, 5, 'x')  # coral crest
    g.px(14, 3, 'x')
    g.px(17, 2, 'x')
    trident(g, f.hand)
    shield(g, 7, 15, 'x', 'C', w=5, h=8, round_=True)
    return g.strings(), p


def tidebinder():
    p = pal(D, {'s': '#8ac0b8', 'S': '#5e9690'}, WOOD, {'*': '#e0f8ff', 'h': '#1e4e5c'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head().hair('h', long=True)
    g.rect(13, 15, 18, 15, 'x')
    g.line(f.hand[0], f.hand[1] + 5, f.hand[0] + 1, f.hand[1] - 9, 'w')
    g.ell(f.hand[0] + 2, f.hand[1] - 11, 2.5, 2, 'x')  # a conch on a staff
    g.px(f.hand[0] + 3, f.hand[1] - 11, '*')
    return g.strings(), p


def kraken_caller():
    p = pal(D, SKIN, STEEL, BOOTS, WOOD, {'z': '#8a4a7a'})
    g = G(p)
    for x0 in (9, 22):  # tentacles curling up behind
        g.line(x0, 28, x0 - 1, 21, 'z', 2)
        g.line(x0 - 1, 21, x0 + 1, 17, 'z')
    f = Fig(g).body(torso='c', arms='z', legs='C', belt='x').head().hair('C', long=True)
    trident(g, f.hand, 'x')
    return g.strings(), p


def deep_priest():
    p = pal(D, {'s': '#6a9aa0', 'S': '#4a7a80'}, WOOD, GOLD, {'*': '#bfe8e0'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head()
    g.rows(12, 0, [(2, 4), (1, 5), (0, 6), (0, 7), (0, 7), (0, 7)], 'g')  # a tall fish-mitre
    g.px(17, 2, 'e')
    g.rect(13, 15, 18, 27, 'y')
    g.rect(15, 15, 16, 27, 'x')
    staff(g, f.hand, top='*', length=18)
    return g.strings(), p


# ------------------------------------------------------------------ Gravebound: bone and violet
def skeleton_fig(g, build='normal'):
    f = Fig(g, build).body(torso='s', arms='s', legs='s', boots='S', skin='s')
    for y in range(f.y0 + 1, f.y1, 2):  # ribs
        g.rect(f.x0 + 1, y, f.x1 - 1, y, 'C')
    f.head(glow='*')
    g.rect(int(f.hx), int(f.hy + 2), int(f.hx) + 3, int(f.hy + 2), 'C')
    return f


def bone_rattler():
    p = pal(R, BONE, STEEL, {'*': '#c8f0d8'})
    g = G(p)
    f = skeleton_fig(g)
    blade_up(g, f.hand, 8, lean=2)
    blade_up(g, f.back_hand, 7)
    return g.strings(), p


def grave_digger():
    p = pal(R, {'s': '#9aa08a', 'S': '#747a66'}, STEEL, WOOD, BOOTS, {'h': '#3a3036'})
    g = G(p)
    f = Fig(g).body(torso='c', arms='c', legs='C', belt='w').head()
    g.rect(11, 4, 20, 5, 'h')  # a battered hat
    g.rect(13, 1, 18, 4, 'h')
    g.line(f.hand[0], f.hand[1] + 4, f.hand[0] + 1, f.hand[1] - 9, 'w')  # a shovel
    g.rect(f.hand[0] - 1, f.hand[1] - 13, f.hand[0] + 3, f.hand[1] - 10, 'm')
    return g.strings(), p


def grave_archer():
    p = pal(R, BONE, WOOD, {'*': '#c8f0d8'})
    g = G(p)
    f = skeleton_fig(g)
    f.hood('c', 'C')
    g.px(18, 10, '*')
    bow(g, f.hand, 'w', 'y')
    return g.strings(), p


def ghoul_reaver():
    p = pal(R, {'s': '#8a9a8a', 'S': '#627062'}, BOOTS, {'*': '#ff5a5a', 'l': '#d8d0c0'})
    g = G(p)
    f = Fig(g).body(torso='C', arms='s', legs='C').head(glow='*')
    g.rect(11, 5, 13, 9, 'C')
    hx, hy = f.hand
    for k in range(3):  # claws
        g.line(hx + k, hy, hx + 2 + k, hy + 2, 'l')
    return lean(g.strings(), 3), p


def wight_mage():
    p = pal(R, BONE, WOOD, {'*': '#c8f0d8', 'z': '#8a6ab8'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head(skin='s', glow='*').hood('c', 'C')
    g.px(17, 10, '*')
    g.px(19, 10, '*')
    g.rect(13, 16, 18, 16, 'x')
    g.ell(f.hand[0] + 2, f.hand[1] - 3, 2, 2, 'z')
    g.px(f.hand[0] + 2, f.hand[1] - 3, '*')
    return g.strings(), p


def grave_knight():
    p = pal(R, STEEL, GOLD, BONE, {'a': '#3a3440', 'A': '#28222e', '*': '#c8f0d8', 'b': '#28222e'})
    g = G(p)
    f = Fig(g).body(torso='a', arms='a', legs='A', belt='x')
    f.cape('x')
    f.head(skin='s', glow='*').helm('a', visor=False, horns='s')
    g.rect(15, 9, 19, 11, 's')  # a skull face-plate
    g.px(16, 10, '*')
    g.px(18, 10, '*')
    blade_up(g, f.hand, 13, c='l', guard='x', lean=0)
    return g.strings(), p


def lich():
    p = pal(R, BONE, WOOD, GOLD, {'*': '#c8f0d8'})
    g = G(p)
    f = Fig(g).body(robe=True, torso='c', arms='c').head(skin='s', glow='*').crown('g', '*')
    g.rect(16, 12, 19, 12, 'C')
    g.rect(13, 15, 18, 28, 'x')
    g.rect(15, 15, 16, 28, 'C')
    staff(g, f.hand, top='*', length=17)
    g.ell(f.hand[0] + 1.5, f.hand[1] - 14, 2.2, 2.2, 's')
    g.px(f.hand[0] + 1, f.hand[1] - 14, 'e')
    g.px(f.hand[0] + 3, f.hand[1] - 14, 'e')
    return g.strings(), p


def skeleton():
    p = pal(R, BONE, STEEL, {'*': '#c8f0d8'})
    g = G(p)
    f = skeleton_fig(g)
    blade_up(g, f.hand, 7, lean=2)
    return g.strings(), p
