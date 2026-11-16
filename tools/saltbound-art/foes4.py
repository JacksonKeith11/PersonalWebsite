# Status-focused enemies (owner's request, Nov 2026: more enemies that inflict statuses), drawn facing
# right like foes.py. Three looks each for the owner to pick from (OPTIONS); the picks go in ALL.
from common import *


# ================================================================ Bilge Rats (Smugglers' Keys): Poison, Root
def bilge_rats1():  # a pack: three mangy rats huddled together, pink tails, red eyes
    pal = {'R': '#6a5a52', 'r': '#4e423c', 'Q': '#8a7a70', 'T': '#d89a9a', 'e': '#ff4a3a', 'n': '#e8b0b0', 'G': '#8ab84a'}
    g = G(pal)
    for cx, cy, s in ((9, 18, 0.85), (21, 19, 0.85), (15, 24, 1.0)):
        g.ell(cx, cy, 6 * s, 4 * s, 'R'); g.ell(cx, cy + 1.5 * s, 5 * s, 2.2 * s, 'r')
        g.ell(cx + 5 * s, cy - 1, 2.6 * s, 2.2 * s, 'Q'); g.px(round(cx + 7 * s), round(cy - 1), 'n')
        g.px(round(cx + 5 * s), round(cy - 2), 'e'); g.px(round(cx + 4 * s), round(cy - 3.5 * s), 'T')
    g.line(3, 18, 1, 13, 'T'); g.line(15, 19, 13, 13, 'T'); g.line(9, 25, 4, 29, 'T')
    g.px(11, 22, 'G'); g.px(19, 17, 'G')
    return g

def bilge_rats2():  # a plague rat: one big rat on its hind legs, green sores, a gnawed rope in its paws
    pal = {'R': '#6a5a52', 'r': '#4e423c', 'Q': '#8a7a70', 'T': '#d89a9a', 'e': '#ff4a3a', 'n': '#e8b0b0', 'G': '#9ad04a', 'w': '#b89a6a', 'k': '#2a2420'}
    g = G(pal)
    g.ell(14, 20, 6, 8, 'R'); g.ell(15, 22, 4, 5, 'Q')
    g.ell(17, 10, 4.5, 4, 'R'); g.ell(21, 11, 2.5, 2, 'Q'); g.px(23, 11, 'n'); g.px(18, 9, 'e')
    g.ell(15, 6, 1.6, 2, 'T'); g.ell(19, 6, 1.6, 2, 'T')
    g.line(19, 16, 22, 19, 'r', 2); g.line(10, 16, 8, 19, 'r', 2)
    g.line(5, 20, 25, 19, 'w'); g.px(26, 20, 'w')
    g.rect(10, 27, 13, 28, 'r'); g.rect(16, 27, 19, 28, 'r')
    g.line(9, 26, 2, 29, 'T'); g.px(1, 28, 'T')
    for x, y in ((12, 17), (16, 24), (11, 23), (19, 8)): g.px(x, y, 'G')
    g.px(20, 13, 'k')
    return g

def bilge_rats3():  # out of a barrel: a split rum barrel spilling rats, one climbing over the rim
    pal = {'R': '#6a5a52', 'r': '#4e423c', 'Q': '#8a7a70', 'T': '#d89a9a', 'e': '#ff4a3a', 'B': '#8a5a2a', 'b': '#6a4220', 'I': '#5a5a62'}
    g = G(pal)
    g.rows(6, 12, [(1, 13), (0, 14)] + [(0, 14)] * 14 + [(1, 13)], 'B')
    g.rect(6, 15, 20, 16, 'I'); g.rect(6, 24, 20, 25, 'I')
    for x in (9, 13, 17): g.line(x, 13, x, 28, 'b')
    g.rows(8, 10, [(2, 8), (0, 10)], 'r')
    g.ell(13, 9, 3.5, 2.5, 'R'); g.ell(17, 8, 2, 1.8, 'Q'); g.px(16, 7, 'e'); g.px(15, 6, 'T')
    g.ell(25, 26, 4, 2.6, 'R'); g.ell(28, 25, 1.8, 1.6, 'Q'); g.px(28, 24, 'e'); g.line(21, 27, 18, 30, 'T')
    g.ell(4, 28, 3, 2, 'R'); g.px(6, 27, 'e'); g.line(1, 28, 0, 25, 'T')
    return g


# ================================================================ Omen Raven (Stormcrag): Hex, a stolen die, Vulnerable
def omen_raven1():  # a storm raven: black, wings half spread, one lightning-blue eye
    pal = {'K': '#24202e', 'k': '#3a3448', 'q': '#5a5272', 'Y': '#9fd8ff', 'B': '#c8a83a', 'F': '#4a4058'}
    g = G(pal)
    g.ell(14, 18, 6, 6, 'K'); g.ell(19, 11, 4, 3.5, 'K'); g.ell(13, 19, 4, 3.5, 'k')
    g.tri(((23, 10), (28, 12), (23, 13)), 'B')
    g.px(20, 10, 'Y'); g.px(21, 10, 'Y')
    g.tri(((9, 14), (1, 8), (6, 22)), 'k'); g.tri(((10, 15), (3, 12), (7, 21)), 'q')
    g.tri(((8, 22), (2, 28), (12, 24)), 'K')
    g.rect(14, 24, 14, 28, 'F'); g.rect(17, 24, 17, 28, 'F'); g.rect(12, 28, 19, 28, 'F')
    return g

def omen_raven2():  # on a bone perch: a raven on a horned skull totem, a stolen die glinting in its beak
    pal = {'K': '#24202e', 'k': '#3a3448', 'q': '#5a5272', 'Y': '#9fd8ff', 'B': '#c8a83a', 'W': '#e0d8c8', 'w': '#b0a898', 'P': '#7a5a3a', 'd': '#f0e8d8', 'e': '#1a1420'}
    g = G(pal)
    g.rect(13, 22, 16, 30, 'P'); g.ell(14.5, 21, 5, 3.5, 'W'); g.px(12, 21, 'e'); g.px(17, 21, 'e')
    g.line(9, 20, 6, 16, 'w', 2); g.line(20, 20, 23, 16, 'w', 2)
    g.ell(14, 13, 5, 5, 'K'); g.ell(18, 7, 3.5, 3, 'K'); g.ell(13, 14, 3.5, 3, 'k')
    g.tri(((21, 6), (25, 8), (21, 9)), 'B'); g.px(19, 6, 'Y')
    g.rect(25, 7, 27, 9, 'd'); g.px(26, 8, 'e')
    g.tri(((9, 11), (4, 16), (10, 17)), 'q')
    return g

def omen_raven3():  # the three-eyed: a raven with a hex-glowing third eye and purple-sheened feathers
    pal = {'K': '#24202e', 'k': '#3a3448', 'q': '#6a4a8a', 'H': '#c86aff', 'h': '#8a3ac8', 'Y': '#9fd8ff', 'B': '#c8a83a', 'F': '#4a4058'}
    g = G(pal)
    g.ell(14, 19, 6.5, 6, 'K'); g.ell(18, 11, 4.5, 4, 'K'); g.ell(13, 20, 4, 3.5, 'q')
    g.tri(((22, 10), (27, 11), (22, 13)), 'B')
    g.px(19, 10, 'Y'); g.px(21, 10, 'Y'); g.px(20, 8, 'H'); g.px(20, 7, 'h')
    g.tri(((8, 15), (2, 20), (9, 22)), 'k')
    g.text(4, 3, ['H  ', ' h ']); g.text(24, 3, ['h', ' H']); g.px(27, 16, 'h')
    g.tri(((8, 23), (1, 27), (11, 25)), 'K')
    g.rect(14, 25, 14, 28, 'F'); g.rect(17, 25, 17, 28, 'F'); g.rect(12, 28, 19, 28, 'F')
    return g


# ================================================================ Sulphur Toad (Cinderreach): Poison on everyone, Root
def sulphur_toad1():  # a squat yellow toad, a puff of yellow-green sulphur gas from its mouth
    pal = {'Y': '#d8b83a', 'y': '#a88a2a', 'O': '#e8d870', 'G': '#b8c84a', 'g': '#8a9a3a', 'e': '#1a1420', 'E': '#ff8a3a'}
    g = G(pal)
    g.ell(14, 21, 9, 6.5, 'Y'); g.ell(14, 24, 7, 3, 'O')
    g.ell(10, 14, 2.5, 2.5, 'Y'); g.ell(17, 14, 2.5, 2.5, 'Y'); g.px(10, 14, 'E'); g.px(17, 14, 'E'); g.px(11, 14, 'e'); g.px(18, 14, 'e')
    g.line(19, 20, 23, 19, 'y')
    g.rect(5, 26, 9, 28, 'y'); g.rect(18, 26, 22, 28, 'y')
    g.ell(26, 15, 3.5, 3, 'G'); g.ell(29, 10, 2.5, 2.2, 'g'); g.ell(24, 9, 1.8, 1.6, 'G')
    for x, y in ((8, 19), (13, 18), (18, 21), (11, 22)): g.px(x, y, 'y')
    return g

def sulphur_toad2():  # a magma toad: dark warty hide with glowing cracks, a long tongue lashing out
    pal = {'D': '#4a3a32', 'd': '#3a2c26', 'L': '#ff8a3a', 'l': '#ffd23f', 'T': '#e86a8a', 'e': '#ffe27a', 'k': '#1a1420'}
    g = G(pal)
    g.ell(13, 21, 9, 6.5, 'D'); g.ell(13, 24, 7, 3, 'd')
    g.ell(9, 14, 2.6, 2.6, 'D'); g.ell(16, 14, 2.6, 2.6, 'D'); g.px(9, 14, 'e'); g.px(16, 14, 'e')
    g.line(19, 19, 30, 17, 'T'); g.ell(30, 17, 1.4, 1.4, 'T')
    for a, b in (((6, 20), (9, 23)), ((12, 18), (14, 21)), ((15, 23), (18, 21)), ((8, 25), (11, 26))): g.line(*a, *b, 'L')
    g.px(13, 19, 'l'); g.px(7, 21, 'l'); g.px(17, 22, 'l')
    g.rect(4, 26, 8, 28, 'd'); g.rect(17, 26, 21, 28, 'd'); g.px(19, 20, 'k')
    return g

def sulphur_toad3():  # a crusted toad: a big toad with a back of yellow sulphur crystals, vents steaming
    pal = {'G': '#7a8a4a', 'g': '#5a6a3a', 'O': '#b8c07a', 'C': '#f0d84a', 'c': '#c8a82a', 'S': '#d8d8c8', 'e': '#1a1420', 'E': '#ffb03a'}
    g = G(pal)
    g.ell(14, 21, 10, 7, 'G'); g.ell(15, 25, 7, 2.8, 'O')
    g.ell(19, 15, 3, 2.6, 'G'); g.px(20, 14, 'E'); g.px(21, 14, 'e')
    for x, h in ((6, 5), (9, 7), (12, 6), (15, 4)): g.tri(((x - 2, 17), (x, 17 - h), (x + 2, 17)), 'C'); g.px(x, 16, 'c')
    g.ell(7, 8, 1.6, 1.4, 'S'); g.ell(9, 5, 1.3, 1.2, 'S'); g.ell(13, 9, 1.2, 1.1, 'S')
    g.line(22, 20, 25, 19, 'g')
    g.rect(5, 27, 9, 29, 'g'); g.rect(18, 27, 22, 29, 'g')
    return g


# ================================================================ Rimebound Trapper (the Frostpeaks): Root, Mark
def rime_trapper1():  # a fur-hooded hunter with a short bow, a coiled snare rope at the hip
    pal = {**SKIN, 'F': '#e8e0d0', 'f': '#b8b0a0', 'B': '#5a6a7a', 'b': '#44525e', 'W': '#7a5a3a', 'R': '#c8a87a', 'I': '#bfe8ff', 'e': E, 'k': '#2a2420', 'L': '#44525e'}
    g = G(pal)
    legs(g, 'L', 'k')
    torso(g, 'B'); g.rect(8, 13, 19, 14, 'F')
    g.ell(9, 21, 2.6, 2.2, 'R'); g.px(9, 21, 'W')
    g.rect(6, 14, 7, 20, 'B'); g.rect(20, 14, 21, 17, 's')
    g.line(23, 6, 25, 14, 'W'); g.line(25, 14, 23, 22, 'W'); g.line(23, 6, 23, 22, 'f')
    g.line(21, 15, 26, 13, 'I')
    face(g, 10, 6, 8, 6)
    g.rows(8, 2, [(2, 9), (1, 10), (0, 11), (0, 11), (0, 1), (0, 1), (0, 1), (0, 1)], 'F'); g.rect(18, 4, 19, 10, 'F')
    return g

def rime_trapper2():  # a frost goblin: small, blue-grey, a spear in one hand and a toothed trap in the other
    pal = {'s': '#8aa8c0', 'S': '#6a88a0', 'F': '#c8c0b0', 'W': '#7a5a3a', 'I': '#bfe8ff', 'M': '#8a8a92', 'm': '#5a5a62', 'e': '#ffe27a', 'k': '#2a2420', 'L': '#5a4a3a'}
    g = G(pal)
    g.rect(11, 25, 12, 29, 'L'); g.rect(15, 25, 16, 29, 'L')
    g.ell(13.5, 20, 5, 5.5, 'F'); g.ell(13.5, 11, 5, 4.5, 's')
    g.tri(((8, 9), (3, 6), (9, 12)), 's'); g.tri(((19, 9), (24, 6), (18, 12)), 's')
    g.px(12, 11, 'e'); g.px(15, 11, 'e'); g.line(12, 14, 15, 14, 'k')
    g.line(21, 4, 21, 29, 'W'); g.tri(((20, 4), (21, 0), (22, 4)), 'I')
    g.rect(19, 18, 20, 19, 's'); g.rect(7, 18, 8, 20, 's')
    g.ell(5, 25, 4, 2, 'M'); g.text(2, 22, ['m m m', 'mmmmm'])
    return g

def rime_trapper3():  # a masked hunter: white bone mask, a weighted net over one shoulder, ice-tipped bolas
    pal = {'B': '#3a4a5a', 'b': '#2a3642', 'W': '#e8e8e0', 'w': '#b8b8b0', 'N': '#a89a7a', 'I': '#bfe8ff', 'e': '#1a1420', 'k': '#24202a', 'L': '#2a3642'}
    g = G(pal)
    legs(g, 'L', 'k')
    torso(g, 'B'); g.rect(9, 21, 18, 22, 'b')
    g.rect(6, 14, 8, 20, 'B'); g.rect(19, 14, 21, 17, 'B')
    for i in range(5): g.line(4 + i * 2, 12, 2 + i * 2, 24, 'N')
    for y in (15, 19, 23): g.line(2, y, 11, y, 'N')
    g.line(21, 17, 26, 21, 'w'); g.ell(26, 22, 1.5, 1.5, 'I'); g.line(21, 17, 27, 15, 'w'); g.ell(28, 15, 1.5, 1.5, 'I')
    g.rect(10, 5, 17, 11, 'W'); g.rect(10, 5, 17, 5, 'w'); g.px(12, 8, 'e'); g.px(15, 8, 'e'); g.line(13, 10, 14, 10, 'w')
    g.rows(9, 2, [(1, 8), (0, 9), (0, 9)], 'B')
    return g


# ================================================================ Glowcap (the Verdant Deep): Weak on everyone, a crusted die
def glowcap1():  # a mushroom person: a tall pale stalk with stubby arms and a glowing blue-green cap, spores drifting
    pal = {'C': '#3ac8a8', 'c': '#2a9a80', 'D': '#9ff0d8', 'S': '#e0d8c0', 's': '#b8b098', 'e': '#1a1420', 'P': '#c8ffe8'}
    g = G(pal)
    g.rows(11, 14, [(0, 6)] * 15, 'S'); g.rect(11, 14, 12, 28, 's')
    g.line(10, 18, 6, 21, 's', 2); g.line(18, 18, 21, 22, 's', 2)
    g.rect(11, 29, 13, 30, 's'); g.rect(15, 29, 17, 30, 's')
    g.ell(14, 10, 10, 5.5, 'C'); g.ell(14, 13, 9, 2, 'c')
    for x, y in ((8, 8), (13, 6), (18, 8), (11, 11), (20, 11)): g.ell(x, y, 1.3, 1.1, 'D')
    g.px(13, 17, 'e'); g.px(16, 17, 'e'); g.line(14, 20, 15, 20, 'e')
    for x, y in ((3, 4), (26, 3), (28, 16), (2, 15), (24, 26), (5, 27)): g.px(x, y, 'P')
    return g

def glowcap2():  # a cluster: three glowing mushrooms on a mossy clump, a sleepy face on the biggest
    pal = {'C': '#3ac8a8', 'c': '#2a9a80', 'V': '#a86ad8', 'v': '#7a4aa8', 'S': '#e0d8c0', 's': '#b8b098', 'M': '#4a7a3a', 'm': '#3a5e2e', 'e': '#1a1420', 'P': '#c8ffe8'}
    g = G(pal)
    g.ell(15, 27, 12, 3.5, 'M'); g.ell(15, 29, 11, 1.8, 'm')
    g.rect(13, 13, 18, 26, 'S'); g.ell(15.5, 11, 9, 5, 'C'); g.ell(15.5, 14, 8, 1.6, 'c')
    g.px(14, 18, 'e'); g.px(17, 18, 'e'); g.line(14, 18, 15, 18, 'e'); g.line(17, 18, 18, 18, 'e'); g.px(15, 21, 'e')
    g.rect(5, 19, 7, 26, 's'); g.ell(6, 18, 4, 2.6, 'V'); g.ell(6, 19, 3.5, 1, 'v')
    g.rect(23, 21, 24, 26, 's'); g.ell(23.5, 20, 3, 2, 'V')
    for x, y in ((4, 9), (26, 8), (28, 15), (9, 4), (21, 3)): g.px(x, y, 'P')
    return g

def glowcap3():  # a walker: a broad glowing cap carried on four spindly root-legs, a gill-mouth underneath
    pal = {'C': '#3ac8a8', 'c': '#2a9a80', 'D': '#9ff0d8', 'R': '#8a7a5a', 'r': '#6a5a40', 'G': '#d8c8a0', 'e': '#ffe27a', 'P': '#c8ffe8'}
    g = G(pal)
    g.ell(15, 13, 12, 6, 'C'); g.ell(15, 17, 11, 2, 'c')
    for x in range(6, 25, 2): g.px(x, 18, 'G')
    for x, y in ((9, 10), (15, 9), (21, 11), (12, 14), (19, 14)): g.ell(x, y, 1.3, 1.1, 'D')
    g.px(13, 17, 'e'); g.px(18, 17, 'e')
    for a, b, c2 in (((8, 19), (5, 24), (4, 29)), ((12, 19), (11, 24), (10, 29)), ((18, 19), (19, 24), (20, 29)), ((22, 19), (25, 24), (26, 29))):
        g.line(*a, *b, 'R'); g.line(*b, *c2, 'r')
    for x, y in ((4, 4), (27, 5), (2, 13), (29, 20)): g.px(x, y, 'P')
    return g


# ================================================================ Arc Beetle (the Prism Wood): Static on your dice, Shock
def arc_beetle1():  # a crystal-shelled beetle, a spark jumping between its two antennae
    pal = {'C': '#6ac8e8', 'c': '#3a8ab8', 'D': '#c8f0ff', 'K': '#2a3048', 'k': '#3a4460', 'Y': '#fff27a', 'y': '#9fd8ff', 'e': '#fff27a'}
    g = G(pal)
    g.ell(13, 20, 9, 6.5, 'C'); g.line(13, 14, 13, 26, 'c'); g.ell(9, 18, 2.5, 2, 'D'); g.ell(17, 18, 2, 1.6, 'D')
    g.ell(23, 19, 3.5, 3.5, 'K'); g.px(25, 18, 'e')
    g.line(24, 16, 27, 10, 'k'); g.line(26, 16, 30, 12, 'k')
    g.line(27, 10, 28, 12, 'Y'); g.line(28, 12, 30, 11, 'Y'); g.px(29, 9, 'y'); g.px(31, 13, 'y')
    for x in (7, 12, 17): g.line(x, 25, x - 2, 29, 'k')
    g.line(22, 22, 24, 27, 'k')
    return g

def arc_beetle2():  # a prism horn: a dark beetle with one huge faceted crystal horn crackling with light
    pal = {'K': '#2a3048', 'k': '#3a4460', 'q': '#5a6680', 'P': '#e8a8ff', 'p': '#a86ad8', 'D': '#ffffff', 'Y': '#fff27a', 'y': '#9fd8ff', 'e': '#ff6a5a'}
    g = G(pal)
    g.ell(12, 21, 9, 6, 'K'); g.ell(11, 19, 6, 3, 'q'); g.line(12, 16, 12, 26, 'k')
    g.ell(21, 21, 3.5, 3, 'k'); g.px(22, 20, 'e')
    g.tri(((22, 18), (29, 6), (25, 19)), 'P'); g.line(23, 17, 28, 7, 'p'); g.px(27, 9, 'D')
    g.text(26, 2, ['y Y', ' Y ', 'Y y']); g.px(30, 10, 'Y')
    for x in (6, 11, 16): g.line(x, 26, x - 2, 30, 'k')
    g.line(20, 24, 22, 29, 'k')
    return g

def arc_beetle3():  # in flight: wing cases flung open, buzzing wings, blue arcs crawling over its shell
    pal = {'C': '#3a8ab8', 'c': '#2a6a90', 'W': '#d8f0ff', 'w': '#a8d0e8', 'K': '#2a3048', 'Y': '#fff27a', 'y': '#9fd8ff', 'e': '#fff27a'}
    g = G(pal)
    g.ell(9, 10, 6, 3, 'w'); g.ell(20, 9, 6, 3, 'W')
    g.ell(15, 17, 5.5, 7, 'K'); g.tri(((10, 12), (4, 20), (11, 21)), 'C'); g.tri(((20, 12), (26, 20), (19, 21)), 'c')
    g.ell(15, 9, 3, 2.6, 'K'); g.px(14, 8, 'e'); g.px(17, 8, 'e')
    g.line(13, 7, 11, 3, 'K'); g.line(17, 7, 19, 3, 'K')
    g.line(12, 15, 14, 18, 'y'); g.line(14, 18, 13, 21, 'Y'); g.line(18, 17, 17, 20, 'y'); g.px(6, 17, 'Y'); g.px(24, 18, 'Y')
    for x in (12, 15, 18): g.line(x, 24, x + (x - 15) // 2, 28, 'K')
    return g


# The owner's picks among each enemy's looks (0-based), written to sprites.js by build.py.
OPTIONS = {
    'bilge_rats': [('A pack', bilge_rats1), ('A plague rat', bilge_rats2), ('Out of a barrel', bilge_rats3)],
    'omen_raven': [('Storm raven', omen_raven1), ('On a bone perch', omen_raven2), ('Three-eyed', omen_raven3)],
    'sulphur_toad': [('Sulphur puff', sulphur_toad1), ('Magma toad', sulphur_toad2), ('Crystal-crusted', sulphur_toad3)],
    'rime_trapper': [('Fur-hooded archer', rime_trapper1), ('Frost goblin', rime_trapper2), ('Masked netter', rime_trapper3)],
    'glowcap': [('Mushroom person', glowcap1), ('A cluster', glowcap2), ('A walker', glowcap3)],
    'arc_beetle': [('Crystal shell', arc_beetle1), ('Prism horn', arc_beetle2), ('In flight', arc_beetle3)],
}
PICKED = {'bilge_rats': 2, 'omen_raven': 0, 'sulphur_toad': 1, 'rime_trapper': 2, 'glowcap': 0, 'arc_beetle': 1}
