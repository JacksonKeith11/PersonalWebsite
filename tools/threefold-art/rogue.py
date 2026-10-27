from kit import *
E = '#1a1420'
def boots(g, c='k', y=26):
    g.rect(10, y, 12, 28, 'L'); g.rect(15, y, 17, 28, 'L'); g.rect(9, 29, 12, 30, c); g.rect(15, 29, 18, 30, c)
def rogue1():  # hooded assassin: hood, face scarf, leather vest, two daggers, belt pouches
    pal = {'H': '#2f6a4a', 'h': '#214c36', 'n': '#16201a', 's': '#e0b48a', 'S': '#a8785a', 'V': '#5a4232', 'v': '#40301f', 'm': '#3a3a44',
           'w': '#dfe6ee', 'W': '#a8b0bc', 'Y': '#c8a040', 'b': '#6a4a2e', 'L': '#3a3440', 'k': '#241e28', 'e': E}
    g = G(pal)
    boots(g)
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (1, 10), (1, 10), (1, 10), (1, 10), (1, 10), (1, 10), (1, 10)], 'V')
    g.rect(13, 14, 14, 21, 'v'); g.rect(9, 22, 18, 22, 'b'); g.rect(12, 22, 13, 22, 'Y'); g.rect(16, 23, 17, 24, 'b'); g.rect(10, 23, 11, 24, 'b')
    g.rows(7, 12, [(1, 13), (0, 14), (0, 3), (0, 2), (0, 2)], 'H'); g.rect(19, 13, 21, 15, 'H')  # cowl over the shoulders
    # arms with daggers: one reversed grip, one forward
    g.rect(6, 15, 8, 20, 'h'); g.rect(6, 20, 8, 21, 's'); g.line(5, 22, 3, 26, 'w'); g.line(6, 22, 4, 26, 'W'); g.rect(5, 21, 9, 21, 'm')
    g.rect(19, 15, 21, 18, 'h'); g.rect(20, 18, 22, 19, 's'); g.rect(22, 17, 22, 20, 'm'); g.line(23, 18, 27, 14, 'w'); g.line(23, 19, 27, 15, 'W')
    # hood and masked face
    g.ell(13.5, 7.5, 6, 6, 'H'); g.rect(8, 8, 19, 12, 'H')
    g.rect(10, 7, 17, 12, 'n'); g.rect(11, 8, 16, 9, 's'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(10, 10, 17, 12, 'h')
    g.text(9, 1, ['  hhh', ' hhHhh'])
    return g
def rogue2():  # bandit: bandana with a trailing knot, short cape on one shoulder, curved dagger
    pal = {'R': '#3a5aa8', 'r': '#2a4280', 's': '#d8a880', 'S': '#a07658', 'u': '#3a2a20', 'C': '#4a5a3a', 'c': '#36422a', 'V': '#8a6a46',
           'v': '#6a4e32', 'w': '#dfe6ee', 'W': '#a8b0bc', 'Y': '#c8a040', 'b': '#5a3a24', 'L': '#4a3e36', 'k': '#2a2028', 'e': E, 'o': '#e8e0d0'}
    g = G(pal)
    boots(g)
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (1, 10), (1, 10), (1, 10), (1, 10), (1, 10), (1, 10)], 'o')  # shirt
    g.rows(9, 14, [(0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9)], 'V'); g.rect(12, 14, 15, 22, 'o')  # open vest
    g.rect(9, 22, 18, 23, 'b'); g.rect(13, 22, 14, 23, 'Y'); g.rect(16, 24, 18, 25, 'v')
    # cape over the left shoulder
    g.rows(5, 12, [(2, 7), (1, 6), (0, 5), (0, 5), (0, 4), (0, 4), (0, 4), (0, 3), (0, 3), (1, 3), (1, 2)], 'C')
    g.rect(6, 22, 8, 23, 's')
    # curved dagger
    g.rect(19, 14, 21, 18, 'o'); g.rect(20, 18, 22, 19, 's'); g.rect(21, 17, 23, 17, 'Y'); g.text(22, 11, ['   ww', '  ww ', ' ww  ', ' w   ', 'w    ', 'w    '])
    # head with bandana
    g.rect(10, 6, 17, 12, 's'); g.rect(10, 6, 17, 7, 'S'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(11, 11, 16, 11, 'u'); g.px(17, 10, 'u')
    g.rect(9, 4, 18, 7, 'R'); g.rect(10, 3, 17, 3, 'R'); g.rect(9, 7, 18, 7, 'r'); g.text(5, 6, ['RRrr', ' Rr ', '  r '])
    return g
def rogue3():  # cloaked: a long hooded cloak wrapped tight, one hand out with a fan of knives
    pal = {'C': '#3a3450', 'c': '#2a2440', 'n': '#14101e', 's': '#e0b48a', 'S': '#a8785a', 'Y': '#9a8ab8', 'w': '#dfe6ee', 'W': '#a8b0bc',
           'k': '#1e1a26', 'L': '#2a2436', 'e': '#e8d070'}
    g = G(pal)
    g.rows(8, 12, [(1, 11), (0, 12), (-1, 13), (-1, 13), (-1, 13), (-1, 14), (-2, 14), (-2, 14), (-2, 14), (-2, 15), (-3, 15), (-3, 15), (-3, 15), (-3, 16), (-4, 16), (-4, 16), (-4, 16)], 'C')
    g.line(13, 14, 11, 28, 'c'); g.line(17, 16, 19, 28, 'c'); g.rect(5, 28, 23, 28, 'Y')
    g.rect(10, 29, 12, 30, 'k'); g.rect(15, 29, 17, 30, 'k')
    # the knife hand
    g.rect(19, 16, 21, 17, 'C'); g.rect(21, 15, 23, 17, 's')
    g.line(23, 14, 26, 9, 'w'); g.line(24, 15, 28, 12, 'w'); g.line(24, 16, 29, 15, 'W')
    # deep hood with glinting eyes
    g.ell(13.5, 7.5, 6.5, 6.5, 'C'); g.rect(7, 8, 20, 13, 'C')
    g.rect(10, 7, 17, 12, 'n'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(11, 11, 16, 12, 'S')
    g.text(8, 1, ['   ccc', '  cCCcc'])
    g.rect(13, 13, 14, 13, 'Y')  # clasp
    return g
def rogue4():  # swashbuckler: feathered cap, vest, sash, rapier
    pal = {'H': '#3a5a8a', 'h': '#2a4268', 'F': '#e8e0c8', 'f': '#c84a4a', 's': '#e0b48a', 'S': '#a8785a', 'u': '#4a2e1e', 'o': '#e8e0d0',
           'V': '#7a3a5a', 'v': '#5a2a42', 'R': '#c8a040', 'w': '#dfe6ee', 'Y': '#d8b048', 'L': '#3a3448', 'k': '#2a2028', 'e': E}
    g = G(pal)
    boots(g, 'k', 25)
    g.rect(9, 27, 12, 30, 'k'); g.rect(15, 27, 18, 30, 'k')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (1, 10), (1, 10), (1, 10), (1, 10), (1, 10)], 'o')
    g.rows(9, 14, [(0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'V'); g.rows(15, 14, [(0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3)], 'V')
    g.rect(9, 21, 18, 22, 'f'); g.text(16, 23, ['ff', ' f'])
    g.rect(6, 15, 8, 20, 'o'); g.rect(6, 20, 8, 21, 's')
    # rapier lunging forward
    g.rect(19, 15, 21, 17, 'o'); g.rect(21, 16, 23, 18, 's'); g.rect(22, 15, 24, 15, 'Y'); g.rect(22, 18, 24, 18, 'Y'); g.line(24, 16, 30, 12, 'w')
    # head, curls and a feathered cap
    g.rect(10, 7, 17, 12, 's'); g.rect(10, 7, 17, 7, 'S'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(12, 11, 15, 11, 'S'); g.px(12, 12, 'u'); g.px(15, 12, 'u'); g.rect(13, 12, 14, 12, 'u')
    g.rect(9, 7, 9, 11, 'u'); g.rect(18, 7, 18, 10, 'u')
    g.rows(8, 4, [(1, 10), (0, 11), (0, 11)], 'H'); g.rect(8, 6, 19, 6, 'h'); g.rows(10, 2, [(1, 5), (0, 6)], 'H')
    g.text(4, 0, ['FF    ', ' FFF  ', '  FFFF', '    FF'])
    return g
if __name__ == '__main__':  # preview sheet
    items = [(n, f().strings(), f().pal) for n, f in [('r1', rogue1), ('r2', rogue2), ('r3', rogue3), ('r4', rogue4)]]
    sheet(items, 'rogue.png')
