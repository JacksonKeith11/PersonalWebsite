# First-tier promotions, four options each, built on the owner's chosen base looks.
from kit import *
E = '#1a1420'
KNIGHT = {'A': '#a8b0bc', 'a': '#7a8494', 'T': '#3a5aa8', 'Y': '#d0a840', 'P': '#c84040', 'k': '#2a2430', 'w': '#dfe6ee',
          'h': '#6a4a2e', 'n': '#1e1a26', 'S': '#8a3a2a', 's': '#b85a3a', 'f': '#e0b48a', 'F': '#a8785a', 'e': E}
def knight(over=None, shield=True, sword=True, plume=True, helm='closed', pauldron='plate'):
    g = G({**KNIGHT, **(over or {})})
    g.rect(10, 24, 12, 28, 'a'); g.rect(15, 24, 17, 28, 'a'); g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (1, 10), (1, 10), (1, 10), (1, 10)], 'A')
    g.rows(10, 16, [(0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (0, 7), (-1, 8), (-1, 8)], 'T')
    g.rect(13, 16, 14, 24, 'Y'); g.rect(10, 19, 17, 19, 'Y'); g.rect(9, 21, 18, 21, 'h')
    if pauldron == 'plate': g.rect(6, 13, 9, 15, 'a'); g.rect(18, 13, 21, 15, 'a')
    elif pauldron == 'big': g.rows(4, 12, [(2, 5), (0, 6), (0, 6), (1, 5)], 'a'); g.rows(17, 12, [(1, 4), (0, 6), (0, 6), (1, 5)], 'a')
    elif pauldron == 'spiked':
        g.rows(4, 12, [(2, 5), (0, 6), (0, 6), (1, 5)], 'a'); g.rows(17, 12, [(1, 4), (0, 6), (0, 6), (1, 5)], 'a')
        g.text(3, 10, ['w    ', ' w   ']); g.text(21, 10, ['   w', '  w '])
    if sword:
        g.rect(20, 15, 22, 18, 'A'); g.rect(21, 18, 23, 19, 'a'); g.rect(23, 4, 24, 16, 'w'); g.rect(21, 16, 26, 16, 'Y'); g.rect(23, 17, 24, 18, 'h')
    if shield:
        g.rows(2, 14, [(1, 7), (0, 8), (0, 8), (0, 8), (0, 8), (0, 8), (1, 7), (1, 7), (2, 6), (3, 5), (4, 4)], 'S')
        g.rows(2, 14, [(2, 6), (1, 7), (1, 7), (1, 7), (1, 7), (1, 7), (2, 6), (2, 6), (3, 5), (4, 4)], 's')
        g.rect(6, 15, 6, 22, 'Y'); g.rect(3, 17, 9, 17, 'Y')
    g.rows(9, 4, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (1, 8), (2, 7)], 'A')
    if helm == 'closed':
        g.rect(10, 8, 18, 8, 'n'); g.px(13, 9, 'n'); g.px(14, 9, 'n'); g.rect(13, 4, 14, 12, 'a'); g.rect(13, 8, 14, 8, 'n')
    else:  # open-faced: the face shows under the brow
        g.rect(11, 7, 16, 11, 'f'); g.rect(11, 7, 16, 7, 'F'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(13, 4, 14, 6, 'a')
    if plume: g.text(11, 0, ['  PPP ', ' PPPPP', 'PP  PP', 'P    '])
    return g
WIZ = {'H': '#5b3a8a', 'h': '#45296e', 'Y': '#c8a040', 's': '#e0b48a', 'S': '#a8785a', 'b': '#d8d4cc', 'w': '#6a4a2e',
       'c': '#7fd8e8', 'e': E, 'l': '#5a3a24', 'k': '#2e2438', 'R': '#3e2766'}
def wizard(over=None, staff=True, beard=True, hat='pointed', top='crystal'):
    g = G({**WIZ, **(over or {})})
    if staff:
        g.rect(21, 6, 22, 30, 'w')
        if top == 'crystal': g.text(19, 1, [' www ', 'w ccw', 'wcc w', 'w ccw', ' www '])
    g.rows(9, 14, [(1, 8), (0, 9), (0, 9), (0, 9), (0, 9), (0, 9), (-1, 10), (-1, 10), (-1, 10), (-1, 10), (-2, 11), (-2, 11), (-2, 11), (-2, 12), (-3, 12)], 'H')
    g.rect(13, 21, 14, 27, 'R'); g.rect(12, 21, 12, 27, 'Y'); g.rect(15, 21, 15, 27, 'Y')
    g.rect(7, 28, 21, 28, 'Y'); g.rect(9, 20, 18, 20, 'l'); g.px(13, 20, 'Y'); g.px(14, 20, 'Y')
    g.rows(7, 15, [(1, 2), (0, 2), (0, 2), (0, 2), (0, 2), (0, 2)], 'h'); g.rect(7, 21, 9, 22, 's')
    g.rows(18, 15, [(0, 1), (0, 2), (1, 3)], 'h'); g.rect(20, 17, 22, 19, 's')
    if beard: g.rows(10, 13, [(0, 7), (0, 7), (0, 7), (1, 6), (1, 6), (2, 5), (3, 4)], 'b')
    g.rect(10, 11, 17, 11, 'S'); g.rect(10, 12, 17, 13, 's'); g.px(12, 12, 'e'); g.px(15, 12, 'e')
    if beard: g.rect(11, 14, 16, 14, 'b')
    else: g.rect(11, 14, 16, 14, 's'); g.rect(12, 14, 15, 14, 'S')
    if hat == 'pointed':
        g.rows(5, 9, [(2, 15), (0, 17)], 'H'); g.rect(9, 8, 18, 8, 'Y')
        g.tri([(9, 8.5), (19, 8.5), (13, 1.5)], 'H'); g.text(8, 0, ['hh   ', ' hhH ', '  hH '])
    return g
BAND = {'R': '#3a5aa8', 'r': '#2a4280', 's': '#d8a880', 'S': '#a07658', 'u': '#3a2a20', 'C': '#4a5a3a', 'V': '#8a6a46',
        'v': '#6a4e32', 'w': '#dfe6ee', 'Y': '#c8a040', 'b': '#5a3a24', 'L': '#4a3e36', 'k': '#2a2028', 'e': E, 'o': '#e8e0d0'}
def bandit(over=None, cape=True, dagger=True, mask=False):
    g = G({**BAND, **(over or {})})
    g.rect(10, 26, 12, 28, 'L'); g.rect(15, 26, 17, 28, 'L'); g.rect(9, 29, 12, 30, 'k'); g.rect(15, 29, 18, 30, 'k')
    g.rows(8, 13, [(1, 10), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (0, 11), (1, 10), (1, 10), (1, 10), (1, 10), (1, 10), (1, 10)], 'o')
    g.rows(9, 14, [(0, 9)] * 9, 'V'); g.rect(12, 14, 15, 22, 'o')
    g.rect(9, 22, 18, 23, 'b'); g.rect(13, 22, 14, 23, 'Y'); g.rect(16, 24, 18, 25, 'v')
    if cape: g.rows(5, 12, [(2, 7), (1, 6), (0, 5), (0, 5), (0, 4), (0, 4), (0, 4), (0, 3), (0, 3), (1, 3), (1, 2)], 'C')
    else: g.rect(6, 15, 8, 21, 'o')
    g.rect(6, 22, 8, 23, 's')
    g.rect(19, 14, 21, 18, 'o'); g.rect(20, 18, 22, 19, 's')
    if dagger: g.rect(21, 17, 23, 17, 'Y'); g.text(22, 11, ['   ww', '  ww ', ' ww  ', ' w   ', 'w    ', 'w    '])
    g.rect(10, 6, 17, 12, 's'); g.rect(10, 6, 17, 7, 'S'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(11, 11, 16, 11, 'u'); g.px(17, 10, 'u')
    if mask: g.rect(10, 10, 17, 12, 'R'); g.rect(10, 12, 17, 12, 'r')
    g.rect(9, 4, 18, 7, 'R'); g.rect(10, 3, 17, 3, 'R'); g.rect(9, 7, 18, 7, 'r'); g.text(5, 6, ['RRrr', ' Rr ', '  r '])
    return g
def clear(g, x0, y0, x1, y1): g.rect(x0, y0, x1, y1, '.')

# ---------- Blademaster: speed and steel, ripostes ----------
def blademaster1():  # dual swords, no shield, crimson plume and tabard
    g = knight({'T': '#8a2a2a', 'P': '#e8e0d0', 'Y': '#c8c8d0'}, shield=False)
    g.rect(6, 15, 8, 19, 'A'); g.rect(5, 19, 7, 20, 'a'); g.rect(4, 8, 5, 18, 'w'); g.rect(2, 18, 7, 18, 'Y'); g.rect(4, 19, 5, 20, 'h')
    return g
def blademaster2():  # open helm, two-handed longsword raised overhead, short cape
    g = knight({'T': '#2e2e3a', 'P': '#3a5aa8', 'C': '#3a5aa8'}, shield=False, sword=False, helm='open')
    g.rows(18, 14, [(1, 3), (1, 4), (2, 4), (2, 4), (2, 4), (2, 4), (3, 4), (3, 4), (3, 4)], 'C')
    g.rect(19, 13, 21, 16, 'A'); g.rect(6, 13, 8, 16, 'A'); g.rect(17, 11, 20, 12, 'f')
    g.line(19, 10, 27, 2, 'w', 2); g.rect(17, 11, 19, 12, 'Y'); g.px(16, 12, 'h')
    return g
def blademaster3():  # duelist: half plate, flowing scarf, curved falchion held low
    g = knight({'T': '#5a2e4a', 'A': '#b8b0a8', 'a': '#8a8278', 'P': '#c8a040'}, shield=False, sword=False, helm='open', plume=False)
    g.text(17, 12, ['rrr   ', ' rrrr ', '   rrr', '    rr']); g.pal['r'] = '#c84040'
    g.rect(6, 15, 8, 21, 'A'); g.rect(6, 21, 8, 22, 'f')
    g.rect(19, 15, 21, 18, 'A'); g.rect(20, 18, 22, 19, 'f'); g.rect(21, 17, 21, 20, 'Y'); g.text(22, 19, ['ww   ', ' www ', '  www', '   ww', '    w'])
    g.rect(10, 3, 17, 4, 'h'); g.rect(9, 4, 9, 7, 'h')
    return g
def blademaster4():  # long sword and parrying dagger, black and gold
    g = knight({'A': '#4a4a58', 'a': '#33333e', 'T': '#c8a040', 'Y': '#2a2430', 'P': '#c8a040'}, shield=False)
    g.rect(6, 15, 8, 20, 'A'); g.rect(5, 20, 7, 21, 'a'); g.rect(3, 16, 4, 21, 'w'); g.rect(2, 21, 6, 21, 'Y'); g.pal['Y'] = '#d0a840'
    g.rect(13, 16, 14, 24, 'k'); g.rect(10, 19, 17, 19, 'k')
    return g
# ---------- Juggernaut: walls of steel ----------
def juggernaut1():  # spiked pauldrons, tower shield, gold-trimmed
    g = knight({'T': '#8a6a2a', 'S': '#6a6a78', 's': '#9a9aaa', 'P': '#d0a840'}, shield=False, pauldron='spiked')
    g.rect(1, 13, 9, 27, 'S'); g.rect(2, 14, 8, 26, 's'); g.rect(1, 13, 9, 13, 'Y'); g.rect(1, 27, 9, 27, 'Y'); g.rect(5, 15, 5, 25, 'Y'); g.ell(5, 20, 1.6, 1.6, 'Y')
    return g
def juggernaut2():  # horned great helm, round shield, broad build
    g = knight({'T': '#6a2a2a', 'S': '#5a3a24', 's': '#7a5232'}, shield=False, plume=False, pauldron='big')
    g.text(5, 1, ['ww      ', ' ww     ', '  www   ', '    ww  ']); g.text(19, 1, ['      ww', '     ww ', '   www  ', '  ww    '])
    g.ell(5.5, 19.5, 5.5, 6, 'S'); g.ell(5.5, 19.5, 4, 4.5, 's'); g.ell(5.5, 19.5, 1.5, 1.5, 'A')
    return g
def juggernaut3():  # behind a great shield: only the helm, the hammer and the boots show
    g = knight({'T': '#3a5aa8', 'S': '#5a6070', 's': '#7a8494', 'P': '#3a5aa8'}, shield=False, sword=False, pauldron='big')
    g.rect(21, 3, 22, 18, 'h'); g.rect(19, 2, 25, 6, 'A'); g.rect(19, 2, 25, 2, 'a'); g.rect(20, 17, 23, 19, 'A')
    g.rect(3, 14, 18, 28, 'S'); g.rect(4, 15, 17, 27, 's'); g.rect(3, 14, 18, 14, 'Y'); g.rect(3, 28, 18, 28, 'Y')
    g.rect(10, 17, 11, 25, 'Y'); g.rect(6, 20, 15, 21, 'Y')
    return g
def juggernaut4():  # bucket helm, flail, bigger kite shield, gold and grey
    g = knight({'T': '#5a5a66', 'S': '#c8a040', 's': '#e0c060', 'Y': '#8a3a2a', 'P': '#5a5a66'}, sword=False, plume=False, pauldron='big')
    g.rect(9, 3, 18, 4, 'a'); g.rect(10, 2, 17, 2, 'A')
    g.rect(20, 15, 22, 18, 'A'); g.rect(21, 18, 23, 19, 'a'); g.rect(22, 11, 23, 17, 'h'); g.line(23, 11, 26, 7, 'n'); g.ell(26.5, 5.5, 2.5, 2.5, 'n'); g.pal['n'] = '#5a5a66'
    g.text(24, 2, [' w  ', '    ', 'w   '])
    return g
# ---------- Pyromancer: fire ----------
def pyromancer1():  # red hat and robe, staff crowned with a flame
    g = wizard({'H': '#9a2e22', 'h': '#741e16', 'R': '#5a1a14', 'Y': '#e0a040'}, top=None)
    g.text(19, 0, ['  F  ', ' FfF ', ' FfF ', 'FffFw', ' www '][:5]); g.pal.update({'F': '#ff7a1a', 'f': '#ffd23f'})
    return g
def pyromancer2():  # no staff: a fireball in the raised hand, orange robe, ember band
    g = wizard({'H': '#c8641e', 'h': '#9a4614', 'R': '#7a2e10', 'Y': '#3a2418'}, staff=False)
    g.rect(20, 17, 22, 19, '.'); g.rows(18, 13, [(0, 1), (0, 2), (1, 3)], 'h'); g.rect(20, 11, 22, 13, 's')
    g.ell(21.5, 8, 3, 3, 'F'); g.ell(21, 8, 1.6, 1.8, 'f'); g.px(20, 4, 'F'); g.px(23, 4, 'f'); g.px(25, 7, 'F'); g.pal.update({'F': '#ff7a1a', 'f': '#ffe680'})
    return g
def pyromancer3():  # beardless and hooded in red, a brazier staff
    g = wizard({'H': '#7a1e22', 'h': '#5a141a', 'R': '#2a2028', 'Y': '#c8a040'}, beard=False, hat=None, top=None)
    g.ell(13.5, 8.5, 6, 6, 'h'); g.rect(8, 9, 19, 14, 'h'); g.rect(10, 9, 17, 14, 'n'); g.rect(11, 10, 16, 14, 's'); g.rect(11, 10, 16, 10, 'S'); g.px(12, 12, 'e'); g.px(15, 12, 'e'); g.pal['n'] = '#1e1418'
    g.text(19, 0, [' F f ', 'fFfF ', 'mmmmm', ' mmm ', '  w  ']); g.pal.update({'F': '#ff7a1a', 'f': '#ffd23f', 'm': '#5a5a66'})
    return g
def pyromancer4():  # charred black robe, flame-orange trim, a smouldering beard
    g = wizard({'H': '#2a2228', 'h': '#1e181e', 'R': '#3a2a2a', 'Y': '#ff7a1a', 'b': '#c85a2a', 'c': '#ffd23f', 'w': '#3a2a20'})
    g.px(12, 15, 'f'); g.px(15, 17, 'f'); g.px(13, 19, 'F'); g.pal.update({'F': '#ff7a1a', 'f': '#ffd23f'})
    return g
# ---------- Chronomancer: time ----------
def chronomancer1():  # deep blue, hourglass-topped staff
    g = wizard({'H': '#2a4a8a', 'h': '#1e3668', 'R': '#14244a', 'Y': '#d8c070'}, top=None)
    g.text(19, 0, ['YYYYY', ' gGg ', '  g  ', ' gGg ', 'YYYYY']); g.pal.update({'g': '#c8e8f8', 'G': '#e8c070'})
    return g
def chronomancer2():  # a clock face on the hat, a gold hourglass in hand, no staff
    g = wizard({'H': '#2e5a6a', 'h': '#204450', 'R': '#1a3038', 'Y': '#e0c070'}, staff=False)
    g.ell(13, 5.5, 2.4, 2.4, 'O'); g.px(13, 4, 'n'); g.px(13, 5, 'n'); g.px(14, 5, 'n'); g.pal.update({'O': '#f0e8d0', 'n': '#2a2020'})
    g.text(20, 15, ['YYY', ' g ', 'YYY']); g.pal['g'] = '#e8d080'
    return g
def chronomancer3():  # star-spangled teal robe, crescent staff
    g = wizard({'H': '#2a6a6a', 'h': '#1e5050', 'R': '#14383a', 'Y': '#e8e0a0'}, top=None)
    g.text(19, 0, [' YY  ', 'Y    ', 'Y   w', ' YY w']); g.px(9, 18, 'Y'); g.px(17, 24, 'Y'); g.px(10, 25, 'Y'); g.px(14, 4, 'Y'); g.px(11, 7, 'Y')
    return g
def chronomancer4():  # brass and gears: a cog on the staff, a pocket watch on a chain
    g = wizard({'H': '#5a4a3a', 'h': '#40342a', 'R': '#2e2620', 'Y': '#c8a040', 'w': '#8a6a3a'}, top=None)
    g.text(19, 0, [' Y Y ', 'YYYYY', 'Y n Y', 'YYYYY', ' Y Y ']); g.pal['n'] = '#2a2020'
    g.line(10, 21, 7, 24, 'Y'); g.ell(7, 25, 1.6, 1.6, 'O'); g.pal['O'] = '#f0e8d0'
    return g
# ---------- Assassin: shadows and poison ----------
def assassin1():  # bandana pulled over the face, dark leathers, a reversed blade
    g = bandit({'R': '#2a2a3a', 'r': '#1a1a26', 'V': '#3a3440', 'v': '#2a2430', 'o': '#4a4454', 'C': '#2a2430'}, mask=True, dagger=False)
    g.rect(21, 17, 23, 17, 'Y'); g.text(20, 20, ['w   ', 'ww  ', ' ww ', '  w '])
    return g
def assassin2():  # a hood over the blue bandana, two daggers
    g = bandit({'C': '#3a2e48', 'V': '#3a2e48', 'v': '#2a2236', 'o': '#5a4a6a'}, cape=False)
    g.ell(13.5, 6.5, 6, 5.5, 'C'); g.rect(8, 7, 19, 12, 'C'); g.rect(10, 6, 17, 12, 's'); g.rect(10, 6, 17, 7, 'S'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.rect(11, 11, 16, 11, 'u')
    g.rect(10, 5, 17, 5, 'R'); g.text(4, 22, ['  ww', ' ww ', 'ww  '])
    return g
def assassin3():  # black bandana, red scarf, a katar punch-blade
    g = bandit({'R': '#1e1e28', 'r': '#14141c', 'C': '#8a2028', 'V': '#2a2a34', 'v': '#1e1e26', 'o': '#3a3a46'}, dagger=False)
    g.rect(10, 12, 18, 13, 'C')
    g.rect(22, 16, 23, 20, 'w'); g.rect(24, 17, 26, 19, 'w'); g.rect(27, 18, 27, 18, 'w'); g.rect(21, 16, 21, 20, 'Y')
    return g
def assassin4():  # green cloak, a poison vial and a dagger
    g = bandit({'C': '#2e5a3a', 'R': '#2e5a3a', 'r': '#1e4028', 'V': '#3a3a2a', 'v': '#2a2a1e'})
    g.rect(6, 19, 8, 21, 'g'); g.rect(7, 18, 7, 18, 'k'); g.px(6, 19, 'G'); g.pal.update({'g': '#8be04e', 'G': '#d8ffa8'})
    return g
# ---------- Trickster: slippery and lucky ----------
def trickster1():  # purple and gold, flipping a coin
    g = bandit({'R': '#7a3a9a', 'r': '#5a2a72', 'C': '#c8a040', 'V': '#5a2a72', 'v': '#40205a'}, dagger=False)
    g.rect(21, 9, 23, 11, 'Y'); g.px(21, 9, 'G'); g.px(19, 7, 'G'); g.px(25, 8, 'G'); g.pal['G'] = '#fff0a0'
    return g
def trickster2():  # a feather in the bandana, a smoke bomb ready
    g = bandit({'C': '#7a2e2e'})
    g.text(17, 0, ['  FF', ' FF ', 'FF  ']); g.pal['F'] = '#e8e0c8'
    g.rect(5, 22, 9, 22, '.'); g.ell(7, 23, 2.5, 2.5, 'm'); g.px(6, 22, 'M'); g.px(8, 20, 'k'); g.px(9, 19, 'f'); g.px(10, 18, 'F'); g.pal.update({'m': '#3a3a46', 'M': '#6a6a7a', 'f': '#ff9a3a', 'F': '#ffe680'})
    return g
def trickster3():  # a fan of cards, a long purple cape
    g = bandit({'C': '#6a2a7a', 'R': '#c84040', 'r': '#8a2a2a'}, dagger=False)
    g.rows(5, 12, [(2, 7), (1, 6), (0, 5), (0, 5), (0, 4), (0, 4), (0, 4), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (0, 3), (1, 3), (1, 2)], 'C')
    g.text(21, 12, ['p p p', 'ppppp', ' ppp ']); g.px(21, 12, 'q'); g.px(25, 12, 'q'); g.pal.update({'p': '#f0e8d8', 'q': '#c83a3a'})
    return g
def trickster4():  # a domino mask, juggling knives overhead
    g = bandit({'R': '#2a8a8a', 'r': '#1e6464', 'C': '#c84a6a'}, dagger=False)
    g.rect(10, 8, 17, 9, 'm'); g.px(12, 9, 'e'); g.px(15, 9, 'e'); g.pal['m'] = '#2a2030'
    g.rect(20, 12, 22, 14, 's'); g.rect(19, 14, 21, 16, 'o')
    g.text(19, 1, [' w   ', ' w  w', '    w', 'w    ', 'w    ']); g.text(25, 6, ['w', 'w'])
    return g

CLASSES = [('Blademaster', [blademaster1, blademaster2, blademaster3, blademaster4]), ('Juggernaut', [juggernaut1, juggernaut2, juggernaut3, juggernaut4]),
           ('Pyromancer', [pyromancer1, pyromancer2, pyromancer3, pyromancer4]), ('Chronomancer', [chronomancer1, chronomancer2, chronomancer3, chronomancer4]),
           ('Assassin', [assassin1, assassin2, assassin3, assassin4]), ('Trickster', [trickster1, trickster2, trickster3, trickster4])]
