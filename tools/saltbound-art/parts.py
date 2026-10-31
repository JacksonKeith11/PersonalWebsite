# Interchangeable parts for hero sprites (bodies, heads, headwear, weapons, off-hand items), so a
# class's four options are quick to vary. Palette letters: s/S skin, e eyes, B/b clothes, T trim,
# H hair, h headwear, W metal, w wood, k boots, L legs, X/x an accent colour.
from common import *

ROBE = [(0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12), (-3, 12), (-3, 13), (-3, 13), (-3, 13)]

def body(g, kind):
    if kind == 'robe':
        g.rows(9, 13, ROBE, 'B'); g.rect(13, 14, 14, 28, 'b'); g.rect(8, 20, 19, 20, 'T')
        g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    elif kind == 'coat':
        legs(g, 'L')
        g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (-1, 12), (-1, 12), (-1, 12), (-2, 13), (-2, 13), (-2, 13)], 'B')
        g.rect(12, 13, 15, 22, 'b'); g.rect(9, 19, 18, 19, 'T')
    elif kind == 'vest':
        legs(g, 'L')
        torso(g, 'b')
        g.rows(8, 13, [(1, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'B'); g.rows(16, 13, [(0, 2), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'B')
        g.rect(9, 21, 18, 22, 'T')
    elif kind == 'bare':  # barbarian: bare chest, fur kilt
        g.rect(10, 25, 12, 28, 's'); g.rect(15, 25, 17, 28, 's'); g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
        torso(g, 's', rows=8); g.rect(12, 16, 15, 17, 'S'); g.rows(7, 21, [(0, 13), (0, 13), (1, 12), (1, 12)], 'B'); g.rect(8, 20, 19, 20, 'T')
        g.line(9, 13, 17, 20, 'b')
    else:  # tunic
        legs(g, 'L')
        torso(g, 'B')
        g.rect(9, 20, 18, 21, 'T')

def arms(g, robe=False, left_y=15):
    c = 'B'
    g.rows(6, left_y, [(1, 3), (0, 3), (0, 3), (0, 3)], c); g.rect(6, left_y + 4, 8, left_y + 5, 's')
    g.rows(19, 14, [(0, 2), (0, 3), (1, 3)], c); g.rect(20, 17, 22, 19, 's')

def arms_bare(g):
    g.rect(6, 13, 8, 19, 's'); g.rect(19, 14, 21, 18, 's'); g.rect(20, 17, 22, 19, 's'); g.rect(6, 17, 8, 17, 'T'); g.rect(19, 17, 21, 17, 'T')

def head(g, hair='short', beard=None, y=6):
    face(g, 10, y, 8, 6)
    g.rect(12, y + 4, 15, y + 4, 'S')
    if hair == 'short':
        g.rect(10, y - 2, 17, y, 'H'); g.rect(9, y - 1, 9, y + 2, 'H'); g.rect(18, y - 1, 18, y + 1, 'H')
    elif hair == 'long':
        g.rect(9, y - 2, 18, y, 'H'); g.rect(9, y, 9, y + 9, 'H'); g.rect(18, y, 18, y + 8, 'H'); g.px(8, y + 9, 'H')
    elif hair == 'pony':
        g.rect(10, y - 2, 17, y, 'H'); g.rect(9, y - 1, 9, y + 1, 'H'); g.rect(18, y - 1, 19, y + 1, 'H'); g.rect(19, y + 2, 20, y + 7, 'H')
    elif hair == 'wild':
        g.text(8, y - 3, [' H H H H ', 'HHHHHHHHHH', 'HHHHHHHHHH']); g.rect(8, y, 9, y + 6, 'H'); g.rect(18, y, 19, y + 5, 'H')
    elif hair == 'mohawk':
        g.rect(12, y - 4, 15, y, 'H')
    elif hair == 'bald':
        g.rect(11, y - 1, 16, y - 1, 's')
    if beard == 'full':
        g.rows(10, y + 4, [(0, 7), (0, 7), (1, 6), (2, 5), (3, 4)], 'H'); g.rect(12, y + 4, 15, y + 4, 's')
    elif beard == 'goatee':
        g.rect(13, y + 5, 14, y + 6, 'H'); g.rect(12, y + 4, 15, y + 4, 'H')
    elif beard == 'stache':
        g.rect(11, y + 4, 16, y + 4, 'H')

def hat(g, kind, y=6):
    if kind == 'hood':
        g.ell(13.5, y + 2, 6.5, 6.5, 'h'); g.rect(8, y + 3, 19, y + 7, 'h')
        g.rect(10, y + 1, 17, y + 6, 'x'); g.rect(11, y + 2, 16, y + 6, 's'); g.rect(11, y + 2, 16, y + 2, 'S')
        g.px(12, y + 4, 'e'); g.px(15, y + 4, 'e')
    elif kind == 'feather_cap':
        g.rows(8, y - 3, [(2, 9), (1, 10), (0, 11)], 'h'); g.line(18, y - 2, 23, y - 7, 'X'); g.px(22, y - 7, 'X'); g.px(23, y - 6, 'X')
    elif kind == 'wide':
        g.rect(6, y - 1, 21, y - 1, 'h'); g.rows(10, y - 5, [(1, 6), (0, 7), (0, 7), (0, 7)], 'h'); g.rect(10, y - 2, 17, y - 2, 'X')
    elif kind == 'bandana':
        g.rect(10, y - 2, 17, y, 'h'); g.rect(9, y - 1, 9, y, 'h'); g.text(7, y, ['hh', ' h'])
    elif kind == 'horned':
        g.rows(9, y - 3, [(1, 8), (0, 9), (0, 9)], 'W'); g.rect(9, y, 9, y + 3, 'W'); g.rect(18, y, 18, y + 3, 'W')
        g.text(5, y - 6, ['w            w', 'ww          ww', ' ww        ww ', '  w        w  '])
    elif kind == 'circlet':
        g.rect(10, y - 1, 17, y - 1, 'X'); g.px(13, y - 2, 'X'); g.px(14, y - 2, 'X')
    elif kind == 'wreath':
        g.text(9, y - 2, ['X X X X X', 'XxXxXxXxX'])
    elif kind == 'antlers':
        g.ell(13.5, y + 2, 6.5, 6.5, 'h'); g.rect(8, y + 3, 19, y + 7, 'h')
        g.rect(10, y + 1, 17, y + 6, 'x'); g.rect(11, y + 2, 16, y + 6, 's'); g.px(12, y + 4, 'e'); g.px(15, y + 4, 'e')
        g.text(6, y - 5, ['w w      w w', ' ww      ww ', '  w      w  '])
    elif kind == 'goggles':
        g.rect(10, y + 1, 17, y + 1, 'h'); g.rect(10, y, 12, y + 2, 'X'); g.rect(15, y, 17, y + 2, 'X')
    elif kind == 'beret':
        g.rows(9, y - 3, [(2, 9), (0, 10), (0, 9)], 'h'); g.px(13, y - 4, 'h')
    elif kind == 'skullcap':
        g.rows(9, y - 2, [(1, 8), (0, 9)], 'h')

def weapon(g, kind):
    if kind == 'sword':
        g.rect(22, 17, 24, 17, 'T'); g.line(23, 16, 28, 10, 'W', 2)
    elif kind == 'rapier':
        g.rect(21, 16, 23, 18, 'T'); g.line(23, 16, 30, 9, 'W')
    elif kind == 'axe':
        g.rect(22, 4, 23, 20, 'w'); g.text(21, 2, ['  WWW', ' WWWW', 'WWWWW', ' WWWW', '  WWW'])
    elif kind == 'greataxe':
        g.rect(22, 2, 23, 28, 'w'); g.text(16, 1, ['WWW   ', 'WWWW  ', 'WWWWW ', 'WWWWW ', 'WWWW  ', 'WWW   ']); g.text(24, 1, ['  WWW', ' WWWW', 'WWWWW', 'WWWWW', ' WWWW', '  WWW'])
    elif kind == 'maul':
        g.rect(22, 6, 23, 20, 'w'); g.rect(19, 2, 26, 6, 'W')
    elif kind == 'bow':
        g.text(22, 6, [' w', 'w ', 'w ', 'w ', 'w ', 'w ', 'w ', 'w ', 'w ', 'w ', ' w']); g.line(23, 6, 23, 16, 'X'); g.line(18, 11, 26, 11, 'W')
    elif kind == 'crossbow':
        g.rect(20, 16, 27, 17, 'w'); g.line(24, 13, 24, 20, 'W'); g.px(28, 16, 'W')
    elif kind == 'dagger':
        g.rect(22, 18, 22, 19, 'w'); g.line(23, 17, 25, 14, 'W')
    elif kind == 'staff':
        g.rect(21, 6, 22, 30, 'w'); g.ell(21.5, 4.5, 2, 2, 'X')
    elif kind == 'branch':
        g.rect(22, 4, 23, 30, 'w'); g.text(19, 0, [' X X ', 'XxXxX', ' XxX ', '  X  ']); g.px(24, 9, 'X'); g.px(20, 13, 'X')
    elif kind == 'lute':
        g.ell(23, 21, 3.5, 3, 'w'); g.ell(23, 21, 1, 1, 'x'); g.line(21, 19, 15, 13, 'w', 2); g.rect(14, 12, 15, 13, 'X')
    elif kind == 'horn':
        g.text(21, 13, ['  XXX', ' XX  ', 'XX   ', 'X    '])
    elif kind == 'flask':
        g.rect(23, 14, 24, 15, 'w'); g.ell(23.5, 18, 2.5, 2.5, 'X'); g.px(23, 17, 'x')
    elif kind == 'bomb':
        g.ell(24, 18, 2.6, 2.6, 'x'); g.px(25, 14, 'w'); g.px(26, 13, 'X')
    elif kind == 'sling':
        g.line(22, 18, 25, 22, 'w'); g.ell(25.5, 23, 1.2, 1.2, 'x')
    elif kind == 'banner':
        g.rect(22, 2, 22, 30, 'w'); g.rect(23, 3, 28, 9, 'X'); g.rect(23, 10, 25, 11, 'X')
    elif kind == 'flail':
        g.rect(21, 13, 22, 18, 'w'); g.line(22, 12, 25, 8, 'W'); g.ell(26, 7, 2, 2, 'W')
    elif kind == 'claws':
        g.text(22, 16, ['W W', 'W W W', ' W W'])
    elif kind == 'sickle':
        g.rect(22, 15, 22, 20, 'w'); g.text(22, 10, [' WWW', 'W   W', '    W', '   W '])

def offhand(g, kind):
    if kind == 'buckler':
        g.ell(6, 19, 3.6, 3.6, 'W'); g.ell(6, 19, 2.4, 2.4, 'X'); g.px(6, 19, 'W')
    elif kind == 'dagger':
        g.line(5, 21, 3, 25, 'W'); g.px(6, 20, 'w')
    elif kind == 'flask':
        g.rect(5, 18, 6, 19, 'w'); g.ell(5.5, 22, 2.5, 2.5, 'X')
    elif kind == 'book':
        g.rect(2, 18, 8, 23, 'X'); g.rect(3, 19, 7, 22, 'W'); g.rect(5, 18, 5, 23, 'x')
    elif kind == 'hawk':
        g.text(1, 8, [' oo  ', 'oOOo ', 'OOOOy', ' OO  ', ' O O ']); g.rect(3, 13, 6, 14, 'B')
    elif kind == 'satchel':
        g.rect(3, 19, 8, 24, 'w'); g.rect(4, 20, 7, 23, 'b'); g.px(5, 18, 'X'); g.px(7, 17, 'X')
    elif kind == 'lantern':
        g.rect(4, 21, 7, 25, 'W'); g.rect(5, 22, 6, 24, 'X'); g.px(5, 20, 'W')
    elif kind == 'orb':
        g.ell(5, 20, 2.5, 2.5, 'X'); g.px(4, 19, 'W')
    elif kind == 'quiver':
        g.rect(16, 9, 18, 18, 'w'); g.px(16, 8, 'X'); g.px(18, 7, 'X'); g.px(17, 8, 'W')
    elif kind == 'shield':
        g.ell(6, 19, 5, 5.5, 'w'); g.ell(6, 19, 3.8, 4.2, 'b'); g.ell(6, 19, 1.4, 1.4, 'W')
    elif kind == 'potions':
        g.rect(2, 21, 9, 24, 'w'); g.rect(3, 18, 4, 21, 'X'); g.rect(6, 19, 7, 21, 'x'); g.px(3, 17, 'W'); g.px(6, 18, 'W')
    elif kind == 'acorn':
        g.ell(5, 20, 2, 2.5, 'X'); g.rect(4, 17, 6, 18, 'w')
