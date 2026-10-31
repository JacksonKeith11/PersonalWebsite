# Sprite options for the seven classes added in build step 2. Plain fantasy adventurers, like the
# first three: no sea theme on heroes.
from parts import *

def build(pal, b, hair=None, beard=None, hat_=None, wpn=None, off=None, bare=False):
    def fn():
        g = G({**pal, 'e': E})
        body(g, b)
        if off == 'quiver':
            offhand(g, 'quiver')
        if bare:
            arms_bare(g)
        else:
            arms(g)
        if hat_ in ('hood', 'antlers'):
            hat(g, hat_)
        else:
            head(g, hair or 'short', beard)
            if hat_:
                hat(g, hat_)
        if wpn:
            weapon(g, wpn)
        if off and off != 'quiver':
            offhand(g, off)
        return g
    return fn

SK = SKIN
OPTIONS = {
    'duelist': [
        ('Fencer', build({**SK, 'B': '#8a2a3a', 'b': '#e8e2d4', 'T': '#c8a040', 'H': '#2a1e18', 'h': '#2a2430', 'X': '#e8e2d4', 'W': '#dfe6ee', 'w': '#5a3a24', 'k': '#2a2028', 'L': '#2a2430'},
                         'coat', 'short', 'goatee', 'feather_cap', 'rapier', 'buckler')),
        ('Swordswoman', build({**SK, 'B': '#3a5a8a', 'b': '#c8c4b4', 'T': '#5a3a24', 'H': '#c88a3a', 'W': '#dfe6ee', 'w': '#5a3a24', 'X': '#c8a040', 'k': '#2a2028', 'L': '#4a3a30'},
                              'tunic', 'pony', None, None, 'sword', 'dagger')),
        ('Blademaster', build({**SKIN2, 'B': '#2a2a3a', 'b': '#a83a30', 'T': '#c8a040', 'H': '#1a1420', 'W': '#dfe6ee', 'w': '#2a2028', 'X': '#a83a30', 'k': '#1a1420', 'L': '#2a2a3a'},
                              'coat', 'short', 'stache', 'circlet', 'sword', None)),
        ('Rogue Knight', build({**SK, 'B': '#5a5e6a', 'b': '#3a3e48', 'T': '#8a6a3a', 'H': '#6a4a2e', 'h': '#5a5e6a', 'W': '#dfe6ee', 'w': '#5a3a24', 'X': '#c8a040', 'x': '#1e1a26', 'k': '#2a2028', 'L': '#3a3e48'},
                               'tunic', 'short', 'full', 'skullcap', 'rapier', 'buckler')),
    ],
    'berserker': [
        ('Barbarian', build({**SK, 'B': '#7a5a3a', 'b': '#5a3a24', 'T': '#c8a040', 'H': '#a85a2a', 'W': '#a8b0bc', 'w': '#5a3a24', 'k': '#3a2a20'},
                            'bare', 'wild', 'full', None, 'greataxe', None, bare=True)),
        ('Raider', build({**SK, 'B': '#6a6a5a', 'b': '#4a4a3e', 'T': '#5a3a24', 'H': '#d8b860', 'W': '#a8b0bc', 'w': '#5a3a24', 'X': '#a83030', 'k': '#2a2028', 'L': '#4a3a30'},
                         'tunic', 'long', 'full', 'horned', 'axe', 'shield')),
        ('Pit Fighter', build({**SKIN2, 'B': '#8a3a2a', 'b': '#5a2420', 'T': '#c8a040', 'H': '#1a1420', 'W': '#a8b0bc', 'w': '#5a3a24', 'k': '#2a2028'},
                              'bare', 'mohawk', None, None, 'flail', None, bare=True)),
        ('Wildling', build({**SK, 'B': '#5a6a4a', 'b': '#3e4a34', 'T': '#8a6a4a', 'H': '#3a2a1a', 'h': '#7a6a5a', 'W': '#d8d0c0', 'w': '#5a3a24', 'x': '#1e1a26', 'k': '#3a2a20'},
                           'bare', 'wild', 'full', None, 'claws', None, bare=True)),
    ],
    'ranger': [
        ('Archer', build({**SK, 'B': '#4a6a3a', 'b': '#3a5030', 'T': '#6a4a2e', 'H': '#8a5a2a', 'h': '#3a5030', 'x': '#1e2a1a', 'W': '#a8b0bc', 'w': '#7a5a34', 'X': '#d8d0c0', 'k': '#3a2a20', 'L': '#5a4a3a'},
                         'tunic', None, None, 'hood', 'bow', 'quiver')),
        ('Falconer', build({**SK, 'B': '#7a5a3a', 'b': '#5a4028', 'T': '#c8a040', 'H': '#2a1e18', 'W': '#a8b0bc', 'w': '#7a5a34', 'X': '#d8d0c0', 'O': '#8a6a4a', 'o': '#5a4028', 'y': '#e0b040', 'k': '#3a2a20', 'L': '#4a3a30'},
                           'tunic', 'short', 'stache', None, 'bow', 'hawk')),
        ('Huntress', build({**SK, 'B': '#3a4a3a', 'b': '#2a3a2a', 'T': '#8a6a4a', 'H': '#d8b860', 'W': '#a8b0bc', 'w': '#5a3a24', 'X': '#d8d0c0', 'k': '#3a2a20', 'L': '#3a3a30'},
                           'tunic', 'pony', None, None, 'crossbow', 'quiver')),
        ('Scout', build({**SK, 'B': '#6a5a3a', 'b': '#4a3e28', 'T': '#3a5030', 'H': '#5a3a24', 'h': '#3a5030', 'W': '#a8b0bc', 'w': '#7a5a34', 'X': '#a83030', 'k': '#3a2a20', 'L': '#4a3a30'},
                        'vest', 'short', None, 'feather_cap', 'bow', 'quiver')),
    ],
    'scoundrel': [
        ('Thief', build({**SK, 'B': '#3a3a48', 'b': '#2a2a36', 'T': '#6a4a2e', 'h': '#2a2a36', 'x': '#14101a', 'W': '#dfe6ee', 'w': '#3a2a1a', 'k': '#1e1a26', 'L': '#2a2a36'},
                        'tunic', None, None, 'hood', 'dagger', 'dagger')),
        ('Rake', build({**SK, 'B': '#7a2a4a', 'b': '#e8e2d4', 'T': '#c8a040', 'H': '#1a1420', 'h': '#2a2430', 'X': '#c8a040', 'W': '#dfe6ee', 'w': '#3a2a1a', 'k': '#1e1a26', 'L': '#2a2430'},
                       'coat', 'short', 'stache', 'wide', 'dagger', None)),
        ('Cutpurse', build({**SK, 'B': '#6a5a3a', 'b': '#c8c4b4', 'T': '#5a3a24', 'H': '#a85a2a', 'h': '#3a5a8a', 'W': '#dfe6ee', 'w': '#3a2a1a', 'X': '#c8a040', 'k': '#2a2028', 'L': '#4a3a30'},
                           'vest', 'short', None, 'bandana', 'dagger', 'satchel')),
        ('Poisoner', build({**SK, 'B': '#3a4a3a', 'b': '#2a3a2a', 'T': '#5a3a24', 'h': '#2a3a2a', 'x': '#14201a', 'W': '#dfe6ee', 'w': '#3a2a1a', 'X': '#8be04e', 'k': '#1e1a26', 'L': '#2a3a2a'},
                           'coat', None, None, 'hood', 'dagger', 'flask')),
    ],
    'herald': [
        ('Bard', build({**SK, 'B': '#3a6a5a', 'b': '#e8e2d4', 'T': '#c8a040', 'H': '#c88a3a', 'h': '#7a2a3a', 'X': '#e8e2d4', 'W': '#dfe6ee', 'w': '#8a5a34', 'x': '#3a2a1a', 'k': '#3a2a20', 'L': '#4a3a30'},
                       'coat', 'short', None, 'feather_cap', 'lute', None)),
        ('Minstrel', build({**SK, 'B': '#8a5a2a', 'b': '#e0c890', 'T': '#5a3a24', 'H': '#2a1e18', 'W': '#dfe6ee', 'w': '#a0703e', 'X': '#c8a040', 'x': '#3a2a1a', 'k': '#3a2a20', 'L': '#5a4a3a'},
                           'tunic', 'long', None, None, 'lute', None)),
        ('Herald', build({**SK, 'B': '#3a5aa8', 'b': '#c8a040', 'T': '#e8e2d4', 'H': '#6a4a2e', 'h': '#3a5aa8', 'X': '#c8a040', 'W': '#dfe6ee', 'w': '#5a3a24', 'k': '#2a2028', 'L': '#e8e2d4'},
                         'coat', 'short', 'goatee', 'beret', 'banner', None)),
        ('Skald', build({**SK, 'B': '#5a4a6a', 'b': '#3e3448', 'T': '#c8a040', 'H': '#d8b860', 'W': '#a8b0bc', 'w': '#5a3a24', 'X': '#d8d0c0', 'k': '#2a2028', 'L': '#3e3448'},
                        'tunic', 'long', 'full', None, 'horn', 'shield')),
    ],
    'alchemist': [
        ('Alchemist', build({**SK, 'B': '#6a4a2e', 'b': '#4a3420', 'T': '#c8a040', 'H': '#8a8a8a', 'h': '#3a3440', 'X': '#8be04e', 'x': '#3a7a2a', 'W': '#dfe6ee', 'w': '#6a4a2e', 'k': '#2a2028', 'L': '#3a3440'},
                            'coat', 'short', 'full', 'goggles', 'flask', 'potions')),
        ('Bombardier', build({**SK, 'B': '#5a5e6a', 'b': '#3a3e48', 'T': '#a83030', 'H': '#a85a2a', 'h': '#5a3a24', 'X': '#ffb040', 'x': '#24202a', 'W': '#dfe6ee', 'w': '#6a4a2e', 'k': '#2a2028', 'L': '#3a3e48'},
                             'vest', 'short', 'stache', 'goggles', 'bomb', None)),
        ('Herb-witch', build({**SK, 'B': '#5a3a6a', 'b': '#3e2a4a', 'T': '#8be04e', 'H': '#1a1420', 'h': '#3e2a4a', 'X': '#e070c0', 'x': '#8a3a7a', 'W': '#dfe6ee', 'w': '#6a4a2e', 'k': '#2a2028'},
                             'robe', 'long', None, 'wide', 'flask', 'satchel')),
        ('Tinker', build({**SK, 'B': '#7a6a3a', 'b': '#5a4e2a', 'T': '#5a3a24', 'H': '#2a1e18', 'h': '#5a3a24', 'X': '#7fe3ff', 'x': '#24202a', 'W': '#a8b0bc', 'w': '#6a4a2e', 'k': '#2a2028', 'L': '#4a3a30'},
                         'vest', 'short', None, 'goggles', 'sling', 'potions')),
    ],
    'warden': [
        ('Druid', build({**SK, 'B': '#5a6a3a', 'b': '#3e4a28', 'T': '#8a6a4a', 'H': '#e0dacb', 'h': '#4a5a30', 'X': '#7ab858', 'x': '#3a6034', 'W': '#d8d0c0', 'w': '#6a4a2e', 'k': '#3a2a20'},
                        'robe', 'long', 'full', 'wreath', 'branch', None)),
        ('Antlered Warden', build({**SK, 'B': '#4a5a3a', 'b': '#3a4a2a', 'T': '#8a6a4a', 'h': '#3a4a2a', 'x': '#14201a', 'X': '#7ab858', 'W': '#d8d0c0', 'w': '#8a6a4a', 'k': '#3a2a20'},
                                  'robe', None, None, 'antlers', 'branch', None)),
        ('Grove Keeper', build({**SK, 'B': '#6a5a3a', 'b': '#4a3e28', 'T': '#3a6034', 'H': '#8a5a2a', 'X': '#7ab858', 'x': '#c8a040', 'W': '#d8d0c0', 'w': '#6a4a2e', 'k': '#3a2a20', 'L': '#4a3a30'},
                               'tunic', 'pony', None, 'wreath', 'sickle', 'acorn')),
        ('Thornspeaker', build({**SKIN2, 'B': '#3a4a2a', 'b': '#2a3a1e', 'T': '#a83030', 'H': '#1a1420', 'h': '#2a3a1e', 'x': '#0e1a0e', 'X': '#c84a3a', 'W': '#d8d0c0', 'w': '#5a3a24', 'k': '#3a2a20'},
                               'robe', None, None, 'hood', 'staff', 'orb')),
    ],
}

if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    from PIL import Image, ImageDraw
    rows = []
    for cls, opts in OPTIONS.items():
        items = [(name, fn().strings(), fn().pal) for name, fn in opts]
        sheet(items, f'{out}/{cls}.png', scale=5, cols=4, bg=(16, 22, 31))
        rows.append((cls, Image.open(f'{out}/{cls}.png')))
    w = max(i.width for _, i in rows); hh = [i.height - 80 for _, i in rows]
    big = Image.new('RGBA', (w + 30, sum(hh) + 34 * len(rows)), (16, 22, 31, 255)); d = ImageDraw.Draw(big)
    y = 0
    for (cls, im), h in zip(rows, hh):
        d.text((12, y + 10), cls.capitalize() + ':  ' + ',  '.join(f'{i + 1} {n}' for i, (n, _) in enumerate(OPTIONS[cls])), fill=(201, 162, 74))
        big.alpha_composite(im.crop((0, 0, im.width, h)), (15, y + 26)); y += h + 34
    big.save(f'{out}/new-hero-options.png')
