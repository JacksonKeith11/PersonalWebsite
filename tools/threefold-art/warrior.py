from kit import *
E = '#1a1420'
def legs(g, c='L', boot='k', y=24, gap=True):
    g.rect(10, y, 12, 28, c); g.rect(15, y, 17, 28, c); g.rect(9, 29, 12, 30, boot); g.rect(15, 29, 18, 30, boot)
def warrior1():  # knight: closed great helm with plume, plate, tabard, kite shield, raised sword
    pal = {'A': '#a8b0bc', 'a': '#7a8494', 'T': '#3a5aa8', 't': '#2a4280', 'Y': '#d0a840', 'P': '#c84040', 'L': '#5a6070', 'k': '#2a2430',
           'w': '#dfe6ee', 'h': '#6a4a2e', 'n': '#1e1a26', 'S': '#8a3a2a', 's': '#b85a3a'}
    g = G(pal)
    legs(g, 'a')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (1, 10), (1, 10), (1, 10), (1, 10)], 'A')  # breastplate
    g.rows(10, 16, [(0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (-1, 8), (-1, 8)], 'T')  # tabard
    g.rect(13, 16, 14, 24, 'Y'); g.rect(10, 19, 17, 19, 'Y')
    g.rect(9, 21, 18, 21, 'h')
    g.rect(6, 13, 9, 15, 'a'); g.rect(18, 13, 21, 15, 'a')  # pauldrons
    # sword arm raised
    g.rect(20, 15, 22, 18, 'A'); g.rect(21, 18, 23, 19, 'a'); g.rect(23, 4, 24, 16, 'w'); g.rect(21, 16, 26, 16, 'Y'); g.rect(23, 17, 24, 18, 'h')
    # kite shield
    g.rows(2, 14, [(1, 7), (0, 8), (0, 8), (0, 8), (0, 8), (0, 8), (1, 7), (1, 7), (2, 6), (3, 5), (4, 4)], 'S')
    g.rows(2, 14, [(2, 6), (1, 7), (1, 7), (1, 7), (1, 7), (1, 7), (2, 6), (2, 6), (3, 5), (4, 4)], 's')
    g.rect(6, 15, 6, 22, 'Y'); g.rect(3, 17, 9, 17, 'Y')
    # helm
    g.rows(9, 4, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8), (2, 7)], 'A')
    g.rect(10, 8, 18, 8, 'n'); g.px(13, 9, 'n'); g.px(14, 9, 'n'); g.rect(13, 4, 14, 12, 'a'); g.rect(13, 8, 14, 8, 'n')
    g.text(11, 0, ['  PPP ', ' PPPPP', 'PP  PP', 'P    '])
    return g
def warrior2():  # footman: kettle hat, mustache, chainmail, tabard with a cross, round shield, sword low
    pal = {'A': '#9aa2ae', 'a': '#6e7684', 'M': '#7a8290', 'm': '#5e6672', 'T': '#2e6a4a', 'Y': '#d8c870', 's': '#e0b48a', 'S': '#a8785a',
           'u': '#6a4428', 'R': '#8a5a32', 'r': '#a8783e', 'w': '#dfe6ee', 'h': '#5a3a24', 'k': '#2a2430', 'L': '#4a3a30', 'e': E}
    g = G(pal)
    legs(g, 'L')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11)], 'M')
    for y in range(13, 24, 2):
        for x in range(8 + (y // 2) % 2, 20, 2): g.px(x, y, 'm')
    g.rows(10, 15, [(0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (-1, 8)], 'T')
    g.rect(13, 16, 14, 22, 'Y'); g.rect(11, 18, 16, 18, 'Y'); g.rect(9, 20, 18, 20, 'h')
    # sword held low and forward
    g.rect(19, 15, 21, 19, 'M'); g.rect(20, 19, 22, 20, 's'); g.rect(21, 18, 21, 21, 'Y'); g.line(22, 21, 26, 26, 'w', 2)
    # round shield
    g.ell(6, 19, 5, 5.5, 'R'); g.ell(6, 19, 3.6, 4, 'r'); g.ell(6, 19, 1.4, 1.4, 'A'); g.px(5, 18, 'a')
    # face and kettle hat
    g.rect(10, 7, 17, 12, 's'); g.rect(10, 7, 17, 7, 'S'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(11, 11, 16, 11, 'u'); g.px(10, 12, 'u'); g.px(17, 12, 'u')
    g.rows(6, 5, [(2, 13), (0, 15)], 'A'); g.rows(9, 1, [(2, 7), (1, 8), (0, 9), (0, 9)], 'A'); g.rect(9, 4, 18, 4, 'a')
    return g
def warrior3():  # fighter: bare head with a headband, leather, steel pauldrons, greatsword over the shoulder
    pal = {'A': '#a8b0bc', 'a': '#7a8494', 'B': '#7a5236', 'b': '#5a3a26', 's': '#e0b48a', 'S': '#a8785a', 'H': '#4a2e1e', 'r': '#b83a3a',
           'w': '#dfe6ee', 'W': '#b8c0cc', 'h': '#5a3a24', 'Y': '#c8a040', 'k': '#2a2028', 'L': '#3e3448', 'e': E}
    g = G(pal)
    legs(g, 'L')
    # greatsword behind, over the right shoulder
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (1, 10), (1, 10), (1, 10), (1, 10)], 'B')
    g.rect(10, 13, 17, 23, 'b'); g.rect(11, 14, 16, 22, 'B'); g.rect(9, 20, 18, 21, 'h'); g.rect(13, 20, 14, 21, 'Y')
    g.rows(5, 12, [(1, 4), (0, 5), (0, 5), (1, 4)], 'A'); g.rows(18, 12, [(1, 4), (0, 5), (0, 5), (1, 4)], 'A')
    g.rect(6, 16, 8, 21, 's'); g.rect(6, 21, 8, 22, 'b')
    g.rect(19, 16, 21, 17, 's'); g.rect(21, 17, 23, 19, 's')
    # greatsword resting on the right shoulder, blade rising behind the head
    g.line(21, 15, 25, 1, 'w', 2); g.line(22, 15, 26, 1, 'W'); g.rect(19, 15, 24, 15, 'Y'); g.rect(21, 16, 22, 19, 'h'); g.rect(21, 20, 22, 20, 'Y')
    # head
    g.rect(10, 5, 17, 11, 's'); g.rect(10, 4, 17, 5, 'H'); g.px(9, 5, 'H'); g.px(18, 5, 'H'); g.rect(9, 6, 9, 8, 'H'); g.rect(18, 6, 18, 7, 'H')
    g.rect(10, 6, 17, 6, 'r'); g.text(7, 6, ['rr', ' r'])
    g.px(12, 8, 'e'); g.px(15, 8, 'e'); g.rect(12, 10, 15, 10, 'S'); g.rect(10, 11, 17, 11, 'S')
    return g
def warrior4():  # paladin: winged helm, gold trim, red cape, tower shield, mace
    pal = {'A': '#c0c4cc', 'a': '#8a909c', 'Y': '#d8b048', 'C': '#a83030', 'c': '#7a2020', 's': '#e0b48a', 'S': '#a8785a', 'F': '#e8eef4',
           'T': '#e8e0c8', 't': '#b8ae94', 'm': '#6a6a78', 'h': '#5a3a24', 'k': '#2a2430', 'L': '#5a6070', 'e': E}
    g = G(pal)
    g.rows(7, 13, [(2, 12), (1, 13), (0, 14), (0, 14), (0, 14), (0, 15), (0, 15), (-1, 15), (-1, 15), (-1, 16), (-1, 16), (-1, 16), (-2, 16), (-2, 16), (-2, 16), (-2, 16)], 'C')  # cape
    legs(g, 'a')
    g.rows(9, 13, [(0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9)], 'A')
    g.rect(10, 16, 17, 23, 'T'); g.rect(13, 16, 14, 23, 'Y'); g.rect(9, 20, 18, 20, 'Y')
    g.rect(7, 13, 10, 15, 'Y'); g.rect(17, 13, 20, 15, 'Y')
    # mace raised in the right hand
    g.rect(19, 15, 21, 18, 'A'); g.rect(21, 17, 23, 18, 's'); g.rect(22, 9, 22, 16, 'h'); g.ell(22.5, 7.5, 2.5, 2.5, 'm'); g.px(22, 4, 'm'); g.px(25, 7, 'm'); g.px(19, 7, 'm')
    # tower shield in front
    g.rect(2, 14, 9, 26, 'T'); g.rect(2, 14, 9, 14, 'Y'); g.rect(2, 26, 9, 26, 'Y'); g.rect(2, 14, 2, 26, 'Y'); g.rect(9, 14, 9, 26, 'Y')
    g.rect(5, 16, 6, 24, 'C'); g.rect(3, 18, 8, 19, 'C')
    # face and winged helm
    g.rect(10, 7, 17, 12, 's'); g.rect(10, 7, 17, 7, 'S'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(12, 11, 15, 11, 'S')
    g.rows(9, 3, [(2, 7), (1, 8), (0, 9), (0, 9)], 'A'); g.rect(9, 6, 9, 9, 'A'); g.rect(18, 6, 18, 9, 'A'); g.rect(9, 5, 18, 5, 'Y'); g.rect(13, 2, 14, 6, 'Y')
    g.text(4, 1, ['F    ', 'FF   ', 'FFF  ', ' FFFF', '  FF '])
    g.text(19, 1, ['    F', '   FF', '  FFF', 'FFFF ', ' FF  '])
    return g
if __name__ == '__main__':  # preview sheet
    items = [(n, f().strings(), f().pal) for n, f in [('w1', warrior1), ('w2', warrior2), ('w3', warrior3), ('w4', warrior4)]]
    sheet(items, 'warrior.png')
