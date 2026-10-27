# Every sprite in the game: art key -> (module, drawing function). build.py turns this into js/sprites.js.
import monsters
PICKS = {
    # base classes
    'warrior': ('warrior', 'warrior1'), 'mage': ('mage', 'mage1'), 'rogue': ('rogue', 'rogue2'),
    # first tier
    'blademaster': ('promos', 'blademaster4'), 'juggernaut': ('promos', 'juggernaut3'), 'pyromancer': ('promos', 'pyromancer1'),
    'chronomancer': ('promos', 'chronomancer3'), 'assassin': ('promos', 'assassin3'), 'trickster': ('promos', 'trickster4'),
    # masters
    'samurai': ('masters', 'samurai4'), 'dragoon': ('masters', 'dragoon_red'), 'hoplite': ('masters', 'hoplite1'),
    'briarknight': ('masters', 'briarknight2'), 'stormcaller': ('masters', 'stormcaller3'), 'warlock': ('masters', 'warlock1'),
    'arithmetician': ('masters', 'arithmetician2'), 'oracle': ('masters', 'oracle_orb'), 'ninja': ('masters', 'ninja_back'),
    'plaguebringer': ('masters', 'plaguebringer2'), 'bard': ('masters', 'bard1'), 'mesmer': ('masters', 'mesmer2'),
}
PICKS.update({k: ('monsters', f) for k, f in monsters.KEYS.items()})
