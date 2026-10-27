// Pixel art for sprites and map icons, drawn from text grids and finished by the hi-fi pass (terrain is in tiles.js).

const K = '#1b1226';
export const ART = {
  warrior: {
    pal: { k: K, e: K, G: '#b9c3d3', g: '#6f7a8c', s: '#f0bf8a', b: '#3d6fd1', B: '#74a2f2', S: '#9c4a2e', Y: '#f2c94c', w: '#e7eef7', y: '#c8902c', L: '#4a3a2c' },
    rows: [
      '................',
      '.....kkkkk......',
      '....kGGGGGk.....',
      '....kGgggGk...k.',
      '....kkssskk..kwk',
      '....ksesesk..kwk',
      '.....kssssk..kwk',
      '...kkkbbbbkk.kwk',
      '..kSSkbBBbbk.kwk',
      '..kSYSkbbbbkkkkk',
      '..kSSSkbBbk.kyk.',
      '..kSSkkbbbk..k..',
      '...kk.kLLLk.....',
      '......kLkLk.....',
      '.....kkLkLkk....',
      '.....kkk.kkk....',
    ],
  },
  mage: {
    pal: { k: K, e: K, P: '#7446ae', p: '#4b2a78', Y: '#f2c94c', O: '#7fe3ff', w: '#9a6a3a', s: '#f0bf8a' },
    rows: [
      '......k.........',
      '.....kPk.....kk.',
      '.....kPPk...kOOk',
      '....kPPPk...kOOk',
      '...kPPYPPk...kk.',
      '..kkkkkkkkk..kwk',
      '....kssssk...kwk',
      '....ksesek...kwk',
      '....kssssk..kkwk',
      '...kPPPPPPkksswk',
      '..kPPpPPPPPkkkwk',
      '..kPpPPPPPPk.kwk',
      '..kPPPPPPPPk.kwk',
      '.kPPpPPPPpPPkkwk',
      '.kPPPPPPPPPPk.kk',
      '.kkkkkkkkkkkk...',
    ],
  },
  rogue: {
    pal: { k: K, e: K, H: '#2f7a4f', h: '#1f4f34', s: '#f0bf8a', c: '#4a3b30', C: '#6e5646', L: '#2b2b3a', w: '#dfe7ef' },
    rows: [
      '................',
      '.....kkkkk......',
      '....kHHHHHk.....',
      '...kHHhhhHHk....',
      '...kHhsssshk....',
      '...kHsesesk.....',
      '...kHhssssk.....',
      '...kkHHHHHkk....',
      '..kHHkcccckHk...',
      '..kHkcCcccksk.k.',
      '..kkkcccCcksskwk',
      '....kcCcckkkkwk.',
      '....kLLLLk..kk..',
      '....kLkkLk......',
      '...kkLk.kLk.....',
      '...kkkk.kkk.....',
    ],
  },
  slime: {
    pal: { k: K, e: K, G: '#6fcf5a', g: '#3f9a3a', h: '#b8f5a0' },
    rows: [
      '................', '................', '................', '................', '................', '................',
      '......kkkk......',
      '....kkGGGGkk....',
      '...kGGhGGGGGk...',
      '..kGhhGGGGGGGk..',
      '..kGGGGeGGeGGk..',
      '.kGGGGGeGGeGGGk.',
      '.kGGGGGGGGGGGGk.',
      '.kgGGGGGGGGGGgk.',
      '..kggggggggggk..',
      '...kkkkkkkkkk...',
    ],
  },
  goblin: {
    pal: { k: K, G: '#6aa84f', g: '#4b7d37', Y: '#ffe14d', b: '#7a5a3a', B: '#9a7650', w: '#d9e0e8' },
    rows: [
      '................', '................', '................',
      '.....kkkkk......',
      '.kk.kGGGGGk.kk..',
      '.kGkGGGGGGGkGk..',
      '..kGGkYGkYGGk...',
      '...kGGGGGGGk....',
      '....kGgggGk.....',
      '...kkkbbbkk...k.',
      '..kGkbBbbbkG.kwk',
      '..kGkbbbBbkGkkwk',
      '...kkbbbbbkkGGk.',
      '....kGk.kGk..k..',
      '...kkGk.kGkk....',
      '...kkkk.kkkk....',
    ],
  },
  archer: {
    pal: { k: K, G: '#6aa84f', g: '#4b7d37', Y: '#ffe14d', b: '#9b3b2f', B: '#c4563f', w: '#a0703a', q: '#e8e8e8' },
    rows: [
      '................', '................', '................',
      '.....kkkkk...kk.',
      '.kk.kbbbbbk.kwqk',
      '.kGkbbGGGbbkkwqk',
      '..kGGkYGkYGkw.qk',
      '...kGGGGGGGkw.qk',
      '....kGgggGk.w.qk',
      '...kkkbbbkk.w.qk',
      '..kGkbBbbbkGkGqk',
      '..kGkbbbBbkGw.qk',
      '...kkbbbbbkkw.qk',
      '....kGk.kGk.kwqk',
      '...kkGk.kGkk.kk.',
      '...kkkk.kkkk....',
    ],
  },
  wolf: {
    pal: { k: K, G: '#8d8f9a', g: '#5f6170', Y: '#ffcc33' },
    rows: [
      '................', '................', '................', '................',
      '..........k.k...',
      '.........kGkGk..',
      '.........kGGGGk.',
      '........kGGYGGGk',
      '.kk.....kGGGGGGk',
      'kGGkkkkkkGGGkkk.',
      '.kGGGGGGGGGGk...',
      '..kGGGGGGGGGk...',
      '..kGggGGGggGk...',
      '..kGk.kGk.kGk...',
      '..kGk.kGk.kGk...',
      '..kkk.kkk.kkk...',
    ],
  },
  bat: {
    pal: { k: K, P: '#6a4a82', p: '#3f2a56', R: '#ff4d4d' },
    rows: [
      '................', '................', '................', '................',
      '.k............k.',
      '.kk...k..k...kk.',
      '.kPk..kkkk..kPk.',
      '.kPPk.kPPk.kPPk.',
      '.kPPPkRPPRkPPPk.',
      '.kPpPPPPPPPPpPk.',
      '..kpkPPPPPPkpk..',
      '..kk.kkPPkk.kk..',
      '......k..k......',
      '................', '................', '................',
    ],
  },
  skeleton: {
    pal: { k: K, W: '#ece6d4', x: '#cfd8e0' },
    rows: [
      '................',
      '.....kkkkk......',
      '....kWWWWWk.....',
      '....kWkWkWk.....',
      '....kWWWWWk.....',
      '.....kWkWk......',
      '......kkk.....k.',
      '....kkWWWkk..kxk',
      '...kWkWWWkWk.kxk',
      '...kWkkWkkWk.kxk',
      '...kk.kWk.kWkkxk',
      '......kWk..kWWk.',
      '.....kWkWk..kk..',
      '.....kWkWk......',
      '....kkWkWkk.....',
      '....kkk.kkk.....',
    ],
  },
  cultist: {
    pal: { k: K, R: '#a3283b', r: '#6e1726', Y: '#ffdd55', O: '#ff8a3d' },
    rows: [
      '................',
      '......kkk.......',
      '.....kRRRk......',
      '....kRRRRRk.....',
      '...kRRkkkRRk....',
      '...kRkYkYkRk....',
      '...kRkkkkkRk....',
      '...kRRkkkRRk....',
      '..kRRRRRRRRRk...',
      '..kRrRRRRRrRk.k.',
      '.kRRrRRYRRrRRkOk',
      '.kRRrRRRRRrRk.k.',
      '.kRRrRRRRRrRRk..',
      'kRRRrRRRRRrRRRk.',
      'kRRRRRRRRRRRRRk.',
      'kkkkkkkkkkkkkkk.',
    ],
  },
  lich: {
    pal: { k: K, Y: '#f2c94c', P: '#3f2d60', p: '#291c40', W: '#ece6d4', O: '#7dfc9a', w: '#6b5a8a' },
    rows: [
      '....k.k.k.k.....',
      '....kYkYkYk.....',
      '....kYYYYYk.....',
      '...kPPPPPPPk....',
      '...kPkWWWkPk....',
      '...kPWkWkWPk....',
      '...kPWWWWWPk....',
      '...kPPWkWPPk....',
      '..kPPPPPPPPPk.k.',
      '..kPpPPPPPpPkkOk',
      '.kPPpPPYPPpPPkwk',
      '.kPPpPPPPPpPk.wk',
      '.kPPpPPPPPpPPkwk',
      'kPPPpPPPPPpPPPkw',
      'kPPPPPPPPPPPPPkw',
      'kkkkkkkkkkkkkkk.',
    ],
  },
  orc: {
    pal: { k: K, O: '#7a9a5a', R: '#ff3030', W: '#f4f0e0', A: '#c0c8d0', w: '#7a5230', b: '#5a4030', B: '#7a5a40', L: '#3a3028' },
    rows: [
      '..............k.',
      '.............kAk',
      '....kkkkkk..kAAk',
      '...kOOOOOOk.kAAk',
      '...kOROOROk..kwk',
      '...kOOOOOOk..kwk',
      '...kOWOOWOk..kwk',
      '..kkkOOOOkkk.kwk',
      '.kOOkbbbbkOOkkwk',
      '.kOOkbBBbkOOkOwk',
      '.kOOkbbbbkkOOOk.',
      '.kkkkbbbbbk.kk..',
      '....kLLLLLk.....',
      '....kLLkLLk.....',
      '...kkLLkLLkk....',
      '...kkkk.kkkk....',
    ],
  },
  golem: {
    pal: { k: K, S: '#8a8f99', s: '#62666f', C: '#5ff4ff' },
    rows: [
      '................',
      '................',
      '.....kkkkkk.....',
      '....kSSSSSSk....',
      '....kSCSSCSk....',
      '....kSSSSSSk....',
      '..kkkkSSSSkkkk..',
      '.kSSSkSSSSkSSSk.',
      '.kSsSkSSsSkSsSk.',
      '.kSSSkSSSSkSSSk.',
      '.kSSkkSsSSkkSSk.',
      '.kSSk.kSSk.kSSk.',
      '..kk.kSSSSk.kk..',
      '....kSSkkSSk....',
      '...kSSSkkSSSk...',
      '...kkkkkkkkkk...',
    ],
  },
};

export const ICONS = {
  battle: { pal: { w: '#eef2f7', k: '#3a2a1a', y: '#d9a33a' }, rows: ['.......w', '......ww', '.....ww.', '.k..ww..', '..kww...', '..yk....', '.y..k...', 'y.......'] },
  elite: { pal: { w: '#f1ead8', k: K }, rows: ['..wwww..', '.wwwwww.', '.wkwwkw.', '.wkwwkw.', '.wwwwww.', '..wkkw..', '..wwww..', '..w..w..'] },
  event: { pal: { y: '#ffe680' }, rows: ['..yyyy..', '.yy..yy.', '.....yy.', '....yy..', '...yy...', '...yy...', '........', '...yy...'] },
  shop: { pal: { k: '#6a4a1a', y: '#f2c94c', Y: '#fff0a0' }, rows: ['...kk...', '..kyyk..', '...kk...', '..yyyy..', '.yyYyyy.', '.yYyyyy.', '.yyyyyy.', '..yyyy..'] },
  boss: { pal: { y: '#f2c94c', r: '#e04848' }, rows: ['........', 'y..y..y.', 'yy.y.yy.', 'yyyyyyy.', 'yryyryy.', 'yyyyyyy.', 'yyyyyyy.', '........'] },
};


Object.assign(ART, {
  treant: {
    pal: { k: K, T: '#3f8f3a', t: '#6fc25a', b: '#7a5232', B: '#9a6e44', Y: '#ffe14d' },
    rows: [
      '....kk..kk......',
      '...kTTkkTTk.kk..',
      '..kTtTTTTtTkTTk.',
      '..kTTTTtTTTTTtk.',
      '...kTTTTTTTTTk..',
      '....kbbbbbbbk...',
      '...kbYbbbbYbk...',
      '...kbbbbbbbbk...',
      '..kbbkkkkkbbbk..',
      '..kbbbbbbbbbbk..',
      '.kTkbbbBbbbbkTk.',
      'kTk.kbbbbbbk.kTk',
      'kk..kbbBbbbk..kk',
      '...kbbbbbbbbk...',
      '..kbbk.kk.kbbk..',
      '..kkk......kkk..',
    ],
  },
  ghost: {
    pal: { k: '#2a3a5a', W: '#d6eaff', w: '#9fb8e0' },
    rows: [
      '................',
      '................',
      '.....kkkkkk.....',
      '....kWWWWWWk....',
      '...kWWWWWWWWk...',
      '...kWkkWWkkWk...',
      '...kWkkWWkkWk...',
      '...kWWWWWWWWk...',
      '...kWWWkkWWWk...',
      '...kWWWWWWWWk...',
      '..kWWWWWWWWWWk..',
      '..kWWWWWWWWWWk..',
      '..kWwWWwWWwWWk..',
      '...kwkWkwkWkwk..',
      '....k.k.k.k.k...',
      '................',
    ],
  },
  spider: {
    pal: { k: K, P: '#4a3a5a', R: '#ff4d4d' },
    rows: [
      '................', '................', '................', '................',
      '..k..........k..',
      '...k..kkkk..k...',
      'k...kkPPPPkk...k',
      '.k.kPPPPPPPPk.k.',
      '..kPPRPPPPRPPk..',
      'kkkPPPPPPPPPPkkk',
      '...kPPPPPPPPk...',
      '..k.kkPPPPkk.k..',
      '.k...k.kk.k...k.',
      'k...k......k...k',
      '................', '................',
    ],
  },
  imp: {
    pal: { k: K, R: '#d9442b', r: '#9a2a1a', Y: '#ffe14d', W: '#7a2a4a' },
    rows: [
      '................',
      '................',
      '...k.......k....',
      '...kRk...kRk....',
      '....kRkkkRk.....',
      '....kRRRRRk.....',
      '...kRYkRYkRk....',
      '...kRRRRRRRk....',
      '....kRkkkRk..kk.',
      '..kkkRRRRRkkkRk.',
      '.kWWkRRRRRkWWk..',
      '.kWWkRrRRRkWk...',
      '..kk.kRRRk.k....',
      '.....kRkRk......',
      '....kkk.kkk.....',
      '................',
    ],
  },
  salamander: {
    pal: { k: K, O: '#e0662a', o: '#ffb03b', Y: '#ffe14d' },
    rows: [
      '................', '................', '................', '................', '................',
      '..........kkkk..',
      '.........kOOOOk.',
      '........kOOYOOOk',
      '..kk....kOOOOOk.',
      '.kOOkkkkkOOOkk..',
      'kOOOOOOOOOOOk...',
      'kOoOOoOOoOOk....',
      '.kkOOOOOOOOk....',
      '...kOk..kOk.....',
      '...kk...kk......',
      '................',
    ],
  },
  wyrm: {
    pal: { k: K, R: '#b8322a', r: '#ff8a3d', Y: '#ffe14d' },
    rows: [
      '..........k.k...',
      '.........kRkRk..',
      '..k......kRRRRk.',
      '.kRk....kRRYRRRk',
      'kRRRk...kRRRRRRk',
      'kRrRRk..kRRRkkk.',
      '.kRrRRkkRRRRk...',
      '..kRrRRRRRRRk...',
      '...kRRRRRRRRRk..',
      '..kRRRRrrRRRRRk.',
      '..kRRRrrrrRRRRk.',
      '...kRRRRRRRRRk..',
      '....kRRkkkRRk...',
      '...kRRk...kRRk..',
      '...kkk.....kkk..',
      '................',
    ],
  },
  skeleton_ally: null,
});
const recolor = (base, pal) => ({ rows: ART[base].rows, pal: { ...ART[base].pal, ...pal } });
Object.assign(ART, {
  knight: { rows: ART.warrior.rows, pal: { k: K, e: '#ff4040', G: '#3e3650', g: '#272033', s: '#2a2033', b: '#7a1f2b', B: '#b13a3a', S: '#2b2b35', Y: '#d14b4b', w: '#c7c7d1', y: '#6a6a74', L: '#1f1a26' } },
  shaman: recolor('cultist', { R: '#3e7d4a', r: '#2a5734', Y: '#c9f7ff', O: '#9cf07a' }),
  skeleton_ally: recolor('skeleton', { W: '#bfe8c8', x: '#7dfc9a' }),
  ogre: recolor('orc', { O: '#a0805a', b: '#4a3a5a', B: '#6a5a7a' }),
  firecultist: recolor('cultist', { R: '#e0662a', r: '#9a3a14', Y: '#fff1a0', O: '#ffd23f' }),
  magmagolem: recolor('golem', { S: '#5a4040', s: '#2e2222', C: '#ff8a3d' }),
  blademaster: recolor('warrior', { G: '#c73b3b', g: '#8a2020', b: '#3a3a48', B: '#5a5a70', S: '#7a7a8a', Y: '#c73b3b', w: '#ffffff', y: '#f2c94c', L: '#26222e' }),
  juggernaut: recolor('warrior', { G: '#f2c94c', g: '#b0882a', b: '#c9a227', B: '#f5dc6a', S: '#e0e6ee', Y: '#4a8cff', L: '#6a5a3a' }),
  pyromancer: recolor('mage', { P: '#c0392b', p: '#7a1f1a', O: '#ffb03b', Y: '#ffe14d', w: '#3a2a2a' }),
  chronomancer: recolor('mage', { P: '#2c7a8a', p: '#1a4a58', O: '#f2c94c', Y: '#c9f7ff', w: '#c8a040' }),
  assassin: recolor('rogue', { H: '#2b2240', h: '#16112a', c: '#1f1a2e', C: '#3a3050', L: '#120e1c', w: '#c44dff' }),
  trickster: recolor('rogue', { H: '#d9a520', h: '#a03030', c: '#7a2a6a', C: '#b04090', L: '#30306a', w: '#7fe3ff' }),
});
ART.decoy = {
  pal: { k: K, Y: '#e0c060', y: '#a08030', B: '#6a4a2a', R: '#b03a3a', w: '#f2ead8', e: K },
  rows: [
    '................',
    '......kkkk......',
    '.....kYYYYk.....',
    '....kYYYYYYk....',
    '.....kwewek.....',
    '.....kwwwwk.....',
    '..kkkkRRRRkkkk..',
    '.kYyyBRRRRByyYk.',
    '..kkkkRRRRkkkk..',
    '.....kRyRRk.....',
    '.....kRRyRk.....',
    '......kBBk......',
    '......kBBk......',
    '......kBBk......',
    '.....kkBBkk.....',
    '....kkkkkkkk....',
  ],
};
// Master classes: a recolor plus replacement rows (row index -> 16-char row) for a new silhouette.
const variant = (base, pal, rows) => { const r = recolor(base, pal); r.rows = r.rows.map((row, i) => rows[i] || row); return r; };
Object.assign(ART, {
  samurai: variant('warrior', { G: '#2a2a3a', g: '#c73b3b', b: '#8a2020', B: '#c73b3b', S: '#2a2a3a', Y: '#f2c94c', w: '#ffffff', L: '#26222e' },
    { 0: '...Y.......Y....', 1: '....YkkkkkY.....' }),
  dragoon: variant('warrior', { G: '#3a5aa8', g: '#22336a', b: '#2a4a8a', B: '#5a7ad8', S: '#3a5aa8', Y: '#c9f7ff', w: '#e7eef7', L: '#1a2240' },
    { 0: '......k.......k.', 1: '.....kkkkk...kwk', 2: '....kGGGGGk..kwk', 3: '....kGgggGk..kwk' }),
  hoplite: variant('warrior', { G: '#d9a520', g: '#9a7414', b: '#a83232', B: '#d85050', S: '#d9a520', Y: '#a83232', L: '#4a3a2c' },
    { 0: '.....kBBBk......', 1: '.....kkkkk......' }),
  briarknight: variant('warrior', { G: '#3e6a32', g: '#24421e', b: '#4a6a2a', B: '#7aa04a', S: '#5a4a2a', Y: '#c8b45a', w: '#d8e8b8', L: '#2a3a1e' },
    { 0: '....k.k.k.k.....', 1: '.....kkkkk......' }),
  stormcaller: recolor('mage', { P: '#2a4a9a', p: '#16285a', O: '#ffe14d', Y: '#ffe14d', w: '#6a6a7a' }),
  warlock: variant('mage', { P: '#3a1a3a', p: '#1a0a1a', O: '#e04848', Y: '#e04848', w: '#2a1a1a', e: '#ff4040' },
    { 0: '....k.....k.....', 1: '....kPk...kPk...' }),
  arithmetician: recolor('mage', { P: '#e8e2d0', p: '#9a9480', O: '#7dff8a', Y: '#3a8a4a', w: '#6a4a2a' }),
  oracle: recolor('mage', { P: '#f2ead8', p: '#c8a040', O: '#c9a0ff', Y: '#c8a040', w: '#c8a040' }),
  ninja: variant('rogue', { H: '#1a1a24', h: '#0e0e16', c: '#1a1a24', C: '#2e2e3a', L: '#0e0e16', w: '#e04848' },
    { 5: '...kHkekekk.....', 6: '...kHhhhhhk.....' }),
  plaguebringer: variant('rogue', { H: '#3a2a20', h: '#1e140e', c: '#2a2a20', C: '#4a4a3a', L: '#1a1a14', w: '#8be04e', s: '#d8d0b8' },
    { 5: '...kHsesesskk...', 6: '...kHhsssssk.....'.slice(0, 16) }),
  bard: variant('rogue', { H: '#2a7ab0', h: '#1a4a70', c: '#b03a3a', C: '#e0a040', L: '#3a2a5a', w: '#f2c94c' },
    { 0: '.........ww.....', 1: '.....kkkkkw.....' }),
  mesmer: variant('rogue', { H: '#9a2a8a', h: '#5a1a5a', c: '#3a1a4a', C: '#ff8ad8', L: '#2a1a3a', w: '#ff8ad8', s: '#f8e8f0' },
    { 5: '...kHCeCeCk.....' }),
});

export function paint(art) {
  const w = art.rows[0].length, ht = art.rows.length;
  const c = document.createElement('canvas');
  c.width = w; c.height = ht;
  const x = c.getContext('2d');
  art.rows.forEach((row, y) => {
    for (let i = 0; i < w; i++) {
      const col = art.pal[row[i]];
      if (!col) continue;
      x.fillStyle = col;
      x.fillRect(i, y, 1, 1);
    }
  });
  return c;
}

export const NODE_COLORS = { battle: '#8e3a35', elite: '#6a2f9a', event: '#2f5f99', shop: '#94701c', boss: '#5a1d2a' };

// ---------- the hi-fi pass ----------
// Sprites are drawn as 16×16 letter grids; this turns one into a 32×32 canvas with the finish of
// hand-shaded art: EPX doubles it (rounding off diagonals), the doubled outline is thinned back to a
// single pixel, outlines take a dark shade of the colour they wrap instead of flat black, and each
// colour gets a warm highlight on its lit (upper-left) edge and a cool shade on its lower-right edge.
const hexRGB = c => { const n = parseInt(c.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
const toHex = ([r, g, b]) => '#' + [r, g, b].map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');
const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
// lighter and warmer, or darker and cooler: hue-shifted ramps read as light rather than as grey
export const lit = (rgb, t) => mix(rgb, [255, 236, 190], t);
export const shade = (rgb, t) => mix(rgb, [28, 16, 52], t);
function epx(g) {
  const h = g.length, w = g[0].length, out = Array.from({ length: h * 2 }, () => Array(w * 2));
  const at = (x, y) => (x < 0 || y < 0 || x >= w || y >= h ? '.' : g[y][x]);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const P = g[y][x], A = at(x, y - 1), B = at(x + 1, y), C = at(x - 1, y), D = at(x, y + 1);
    // dark detail (outlines, eyes, the gaps between ribs) is never worn away, only grown
    if (P === 'k' || P === 'e') { out[y * 2][x * 2] = out[y * 2][x * 2 + 1] = out[y * 2 + 1][x * 2] = out[y * 2 + 1][x * 2 + 1] = P; continue; }
    out[y * 2][x * 2] = C === A && C !== D && A !== B ? A : P;
    out[y * 2][x * 2 + 1] = A === B && A !== C && B !== D ? B : P;
    out[y * 2 + 1][x * 2] = D === C && D !== B && C !== A ? C : P;
    out[y * 2 + 1][x * 2 + 1] = B === D && B !== A && D !== C ? D : P;
  }
  return out;
}
const DIR4 = [[0, -1], [1, 0], [0, 1], [-1, 0]];
export function hifi(art) {
  const g = epx(art.rows.map(r => [...r])), h = g.length, w = g[0].length;
  const at = (x, y) => (x < 0 || y < 0 || x >= w || y >= h ? '.' : g[y][x]);
  const fill = c => c !== '.' && c !== 'k';
  const outer = (x, y) => at(x, y) === 'k' && DIR4.some(([dx, dy]) => at(x + dx, y + dy) === '.');
  // thin the doubled silhouette outline: its inner layer takes the colour inside it (dark detail
  // inside the sprite keeps its doubled weight, so eyes and gaps stay readable)
  const t = g.map(r => [...r]);
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (g[y][x] !== 'k' || outer(x, y)) continue;
    let rep = null;
    for (const [dx, dy] of DIR4) if (outer(x + dx, y + dy) && fill(at(x - dx, y - dy))) { rep = at(x - dx, y - dy); break; }
    if (rep) t[y][x] = rep;
  }
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const x2 = c.getContext('2d'), img = x2.createImageData(w, h);
  const T = (x, y) => (x < 0 || y < 0 || x >= w || y >= h ? '.' : t[y][x]);
  const edge = ch => ch === '.' || ch === 'k';
  const rgb = ch => hexRGB(art.pal[ch] || '#ff00ff');
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const ch = t[y][x];
    if (ch === '.' || !art.pal[ch]) continue;
    let col = rgb(ch);
    if (ch === 'k') {
      // an outline takes a deep shade of what it wraps; the bottom edge stays darkest
      const inside = DIR4.map(([dx, dy]) => T(x + dx, y + dy)).find(fill);
      col = inside ? shade(rgb(inside), T(x, y + 1) === '.' ? 0.86 : 0.74) : col;
    } else if (ch !== 'e') {
      const up = T(x, y - 1), left = T(x - 1, y), down = T(x, y + 1), right = T(x + 1, y);
      if (edge(down) || edge(right) && edge(T(x + 1, y + 1))) col = shade(col, 0.28);
      else if (edge(up) || edge(left)) col = lit(col, 0.2);
      else if (down !== ch && fill(down)) col = shade(col, 0.12);
    }
    const i = (y * w + x) * 4;
    img.data[i] = col[0]; img.data[i + 1] = col[1]; img.data[i + 2] = col[2]; img.data[i + 3] = 255;
  }
  x2.putImageData(img, 0, 0);
  return c;
}

const canvases = {};
export function spriteCanvas(name) { return canvases[name] ||= hifi(ART[name]); }
const urls = {};
export function spriteURL(name) { return urls[name] ||= spriteCanvas(name).toDataURL(); }
export function iconCanvas(name) { return canvases['icon_' + name] ||= paint(ICONS[name]); }

export function buildTextures(scene) {
  const tex = scene.textures;
  for (const name of Object.keys(ART)) if (ART[name] && !tex.exists('s_' + name)) tex.addCanvas('s_' + name, spriteCanvas(name));
  for (const name of Object.keys(ICONS)) if (!tex.exists('i_' + name)) tex.addCanvas('i_' + name, iconCanvas(name));
  if (!tex.exists('px')) {
    const c = document.createElement('canvas'); c.width = c.height = 4;
    const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, 4, 4);
    tex.addCanvas('px', c);
  }
}
