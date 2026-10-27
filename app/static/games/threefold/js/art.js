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

// ---------- enemies added with the alternative acts ----------
const mir = rows => rows.map(r => [...r].reverse().join(''));
Object.assign(ART, {
  bloat: { pal: { k: K, e: K, G: '#7ad04e', g: '#4f9a34', w: '#e8ffd0' }, rows: [
    '................', '................',
    '.....kkkkkk.....',
    '...kkGGGGGGkk...',
    '..kGGwwGGGGGGk..',
    '..kGwwGGGGgGGk..',
    '.kGGGGGGGGGGGGk.',
    '.kGGeeGGGGeeGGk.',
    '.kGGeeGGGGeeGGk.',
    'kGGGGGGGGGGGGgGk',
    'kGgGGGGkkGGGGGGk',
    'kGGGGGGGGGGGgGGk',
    'kgGGGgGGGGGGGGgk',
    '.kggGGGGGGGGggk.',
    '..kkkkkkkkkkkk..',
    '................'] },
  boar: { pal: { k: K, B: '#8a5a3a', b: '#5a3422', t: '#f0e6d0', Y: '#ffcc33', p: '#c87a6a', h: '#3a2418' }, rows: mir([
    '................', '................', '................',
    '....kk..........',
    '...khhkkkkkk....',
    '..khhhhbbbbbkk..',
    '.kBBhhBBBBBBbbk.',
    'kpBYkBBBBBBBBbk.',
    'kppBBBBBBBBBBbk.',
    'ktpkBBBBBBBBBbk.',
    '.tkkBBBBbbBBBk..',
    '..kbbkkbbkkbbk..',
    '..kbk..kbk.kbk..',
    '..kbk..kbk.kbk..',
    '..kkk..kkk.kkk..',
    '................']) },
  sapper: variant('goblin', { b: '#5a4a3a', B: '#7a6a4a', O: '#3a3a4a', F: '#ff8a1a', q: '#9a9aaa' }, {
    2: '..............F.',
    3: '.....kkkkk...kFk',
    8: '....kGgggGk..kk.',
    9: '...kkkbbbkk.kOOk',
    10: '..kGkbBbbbkGkOqk',
    11: '..kGkbbbBbkGkOOk',
    12: '...kkbbbbbkkGkk.' }),
  totem: { pal: { k: K, W: '#8a5a32', w: '#6a4224', R: '#c83a2a', Y: '#f2c94c', F: '#e8e0d0' }, rows: [
    '................',
    '...F.kkkkk.F....',
    '...FkRRRRRkF....',
    '....kRYRYRk.....',
    '....kRRRRRk.....',
    '....kWkkkWk.....',
    '....kWWWWWk.....',
    '....kWYwYWk.....',
    '....kWWWWWk.....',
    '....kWkkkWk.....',
    '....kWWWWWk.....',
    '....kWwWWWk.....',
    '...kkWWwWWkk....',
    '..kwwWWWWWwwk...',
    '..kkkkkkkkkkk...',
    '................'] },
  cutpurse: recolor('rogue', { H: '#5a4a6a', h: '#3a2e48', c: '#4a3a2a', C: '#c8a040', w: '#f2c94c' }),
  bulwark: { pal: { k: K, W: '#ece6d4', x: '#cfd8e0', S: '#5a5a6e', Y: '#c8a040' }, rows: [
    '................',
    '.....kkkkk......',
    '....kWWWWWk.....',
    '....kWkWkWk.....',
    '....kWWWWWk.....',
    '.kkkkkWkWk......',
    '.kSSSkkkk.....k.',
    '.kSYSkWWWkk..kxk',
    '.kSYSkWWWkWk.kxk',
    '.kSYSkkWkkWk.kxk',
    '.kSYSk.kWk.kWkxk',
    '.kSSSk.kWk..kWWk',
    '.kSSSkWkWk...kk.',
    '..kkkkWkWk......',
    '....kkWkWkk.....',
    '....kkk.kkk.....'] },
  shade: recolor('ghost', { k: '#3a3a4a', W: '#f0f0f8', w: '#b8b8d0' }),
  wight: { pal: { k: K, C: '#3a4a5a', c: '#24303c', W: '#c8d0d8', B: '#7fe3ff', x: '#9aa4b0' }, rows: [
    '................',
    '.....kkkkk......',
    '....kWWWWWk.....',
    '....kWBWBWk.....',
    '....kWWWWWk.....',
    '.....kWkWk......',
    '...kkCCCCCkk.k..',
    '..kCCcCCCcCCkxk.',
    '..kCkCCCCCkCkxk.',
    '..kWkCCcCCkWkxk.',
    '...kkCCCCCkkWk..',
    '....kCcCCcCkk...',
    '...kCCCcCCCCk...',
    '...kCcCCCcCCk...',
    '..kCCkCCkCCkCk..',
    '..kkk.kk.kk.kk..'] },
  broodmother: recolor('spider', { P: '#5a2a3a', R: '#ffd23f' }),
  lavaworm: { pal: { k: K, R: '#c8401a', r: '#8a2a12', Y: '#ffd23f', D: '#3a2a2a', d: '#5a4444' }, rows: [
    '................', '................',
    '.......kkkk.....',
    '......kRRRRk....',
    '.....kRYRRYRk...',
    '.....kRRRRRRk...',
    '.....kRkkkkRk...',
    '.....kRkYYkRk...',
    '......kRRRRk....',
    '......krRRrk....',
    '.....kRRrRRk....',
    '.....kRRRRrk....',
    '....kkrRRRRkk...',
    '..kkDDkkkkkDDkk.',
    '.kDdDDDdDDDdDDk.',
    '..kkkkkkkkkkkk..'] },
  brazier: { pal: { k: K, S: '#6a6070', s: '#4a4250', F: '#ff8a1a', f: '#ffd23f', R: '#c8401a' }, rows: [
    '................',
    '......f..f......',
    '.....fFf.Ff.....',
    '....fFRFfFRf....',
    '...kkFRRFRRFkk..',
    '..kSSSSSSSSSSk..',
    '...kSsSSSSsSk...',
    '....kkSSSSkk....',
    '.....kSssSk.....',
    '.....kSSSSk.....',
    '.....kSssSk.....',
    '.....kSSSSk.....',
    '....kSSSSSSk....',
    '...kSsSSSSsSk...',
    '...kkkkkkkkkk...',
    '................'] },
  toad: { pal: { k: K, e: K, G: '#5a8a3a', g: '#3e6a2a', Y: '#f2c94c', w: '#d8e0a0', p: '#c85a6a' }, rows: [
    '................', '................', '................',
    '....kk....kk....',
    '...kYYk..kYYk...',
    '..kGYekkkkeYGk..',
    '..kGGGGGGGGGGk..',
    '.kGGgGGGGGGgGGk.',
    '.kGGGGkkkkGGGGk.',
    '.kGgGGGppGGGgGk.',
    'kGGGwwwwwwwwGGGk',
    'kGgGwwwwwwwwGgGk',
    'kGGkwwwwwwwwkGGk',
    '.kGGkkkkkkkkGGk.',
    '.kkkk......kkkk.',
    '................'] },
  leech: { pal: { k: K, L: '#6a3a4a', l: '#4a2430', R: '#e04848' }, rows: mir([
    '................', '................', '................', '................',
    '.........kkk....',
    '........kLLLk...',
    '.......kLlLRRk..',
    '..kkk.kLLLLkRk..',
    '.kLLLkLLlLLk.k..',
    'kLlLLLLLLLk.....',
    'kLLLlLLLLk......',
    'kLLLLLLLk.......',
    '.kkkkkkk........',
    '................', '................', '................']) },
  lizard: variant('goblin', { G: '#4a9a8a', g: '#2e6a5e', b: '#7a6a3a', B: '#9a8a50', Y: '#ffd23f', w: '#c8c8d8' }, {
    0: '..............k.', 1: '.............kwk', 2: '.............kwk', 3: '.....kkkkk...kwk',
    4: '.kk.kGGGGGk..kwk', 5: '.kGkGGGGGGGk.kwk', 6: '..kGGkYGkYGGk.kwk'.slice(0, 16), 7: '...kGGGGGGGk.kwk', 8: '....kGgggGk..kwk',
    9: '...kkkbbbkk..kwk', 10: '..kGkbBbbbkGkkwk', 11: '..kGkbbbBbkGkkwk', 12: '...kkbbbbbkkGGk.' }),
  wisp: { pal: { k: '#1a4a6a', B: '#7fe3ff', b: '#3ab0d0', w: '#ffffff' }, rows: [
    '................', '................',
    '.......kk.......',
    '......kBBk......',
    '.....kBwwBk.....',
    '....kBwwwwBk....',
    '...kBBwwwwBBk...',
    '...kBwkwwkwBk...',
    '...kBBwwwwBBk...',
    '....kBBwwBBk....',
    '.....kbBBbk.....',
    '......kbbk......',
    '.....kbkkbk.....',
    '....kb....bk....',
    '................', '................'] },
  croc: { pal: { k: K, G: '#4a6a3a', g: '#2e4a24', Y: '#f2c94c', w: '#e8e0c0' }, rows: [
    '................', '................', '................', '................', '................',
    '.........kkkk...',
    '..kkk...kGGYGk..',
    '.kGgGkkkGGGGGGkk',
    'kGGGGGGGGGGGGGGk',
    'kgGgGGgGGGkwkwkk',
    'kGGGGGGGGGGkkkk.',
    '.kGkkGGkkGGk....',
    '.kGk.kGk.kGk....',
    '.kkk.kkk.kkk....',
    '................', '................'] },
  hydra: { pal: { k: K, G: '#3a7a5a', g: '#245a40', Y: '#ffd23f', w: '#d8e8c0' }, rows: [
    '..kk.......kk...',
    '.kGYk.....kYGk..',
    '.kGGkk...kkGGk..',
    '..kGGk.kk.kGGk..',
    '...kGGkGGkkGk...',
    '...kGgkYGkGgk...',
    '....kGkGGkGk....',
    '....kGGGGGGk....',
    '...kGGgGGgGGk...',
    '..kGGGGGGGGGGk..',
    '.kGGgGwwwwGgGGk.',
    '.kGGGwwwwwwGGGk.',
    'kGGgGwwwwwwGgGGk',
    'kGGGGGwwwwGGGGGk',
    '.kkGGkkkkkkGGkk.',
    '...kkk....kkk...'] },
  hydrahead: { pal: { k: K, G: '#3a7a5a', g: '#245a40', Y: '#ffd23f', w: '#e8e0c0', b: '#4a88c8' }, rows: [
    '................', '................',
    '......kkkk......',
    '.....kGGYGk.....',
    '....kGGGGGGkk...',
    '....kGGkkwkwk...',
    '....kGGk.kkk....',
    '.....kGGk.......',
    '......kGk.......',
    '......kGGk......',
    '.....kGgGk......',
    '.....kGGGk......',
    '....kGgGGGk.....',
    '...kGGGgGGGk....',
    '..kbbbbbbbbbk...',
    '...kkkkkkkkk....'] },
  yeti: { pal: { k: K, e: K, W: '#e8eef4', w: '#b8c4d4', B: '#5a7aa8' }, rows: [
    '................',
    '.....kkkkk......',
    '....kWWWWWk.....',
    '...kWBBBBBWk....',
    '...kWBeBeBWk....',
    '...kWBBBBBWk....',
    '..kWWkBkkBkWk...',
    '.kWWWWWWWWWWWk..',
    'kWWwWWWWWWWwWWk.',
    'kWwWkWWWWWkWwWk.',
    'kWWWkWWwWWkWWWk.',
    '.kkkkWWWWWkkkkk.',
    '....kWWkWWWk....',
    '...kWWWkkWWWk...',
    '...kBBBk.kBBBk..',
    '...kkkkk.kkkkk..'] },
  frostqueen: { pal: { k: K, e: K, W: '#e8f4ff', B: '#7fc8f0', b: '#3a7ab0', S: '#f0e8f8', Y: '#c9f7ff' }, rows: [
    '.....k.k.k......',
    '....kYkYkYk.....',
    '....kYYYYYk.....',
    '....kSSSSSk.....',
    '....kSeSeSk.....',
    '....kSSSSSk..kk.',
    '...kBWkkkWBkkYk.',
    '..kBWWBBBWWBkYk.',
    '..kBWBBWBBWBkbk.',
    '..kSkBBWBBkSkbk.',
    '...kkBWBBWBkkbk.',
    '...kBBBWBBBBkbk.',
    '..kBBWBBBWBBBkk.',
    '..kBWBBBBBWBBBk.',
    '.kBBBBWBBBBBWBBk',
    '.kkkkkkkkkkkkkkk'] },
  automaton: { pal: { k: K, Y: '#c8a040', y: '#8a6a28', C: '#7fe3ff', s: '#5a5a6a' }, rows: [
    '................',
    '.....kkkkkk.....',
    '....kYYYYYYk....',
    '....kYCYYCYk....',
    '....kYYYYYYk....',
    '.....kkssk......',
    '..kkkYYYYYYkkk..',
    '.kYYkYyYYyYkYYk.',
    '.kYykYYCCYYkyYk.',
    '.kYYkYYYYYYkYYk.',
    '.kssk.kYYk.kssk.',
    '..kk.kYyyYk.kk..',
    '.....kYkkYk.....',
    '....kYYkkYYk....',
    '....kssk.kssk...',
    '....kkkk.kkkk...'] },
  turret: { pal: { k: K, M: '#6a6a7a', m: '#4a4a58', C: '#7fe3ff', Y: '#c8a040' }, rows: [
    '................', '................', '................', '................',
    '..........kkk...',
    '....kkkkkkCCCk..',
    '...kMMMMMkkkkk..',
    '..kMCCMMMMMMk...',
    '..kMMMMmMMMMk...',
    '...kMMMMMMMk....',
    '....kkYYYkk.....',
    '.....kYYYk......',
    '....kmMMMmk.....',
    '...kMMMMMMMk....',
    '...kmmmmmmmk....',
    '...kkkkkkkkk....'] },
  sparkbot: { pal: { k: K, M: '#8a8a9a', m: '#5a5a6a', Y: '#ffe14d', C: '#7fe3ff' }, rows: [
    '................', '................',
    '........Y.......',
    '.......YkY......',
    '........k.......',
    '......kkkkk.....',
    '....kkMMMMMkk...',
    '...kMMMMMMMMMk..',
    '...kMCkMMMCkMk..',
    '...kMMMMMMMMMk..',
    '...kMmMMMMMmMk..',
    '....kkMMMMMkk...',
    '....kmk...kmk...',
    '...kmmk...kmmk..',
    '...kkkk...kkkk..',
    '................'] },
  tinker: recolor('goblin', { G: '#f0bf8a', g: '#c8905a', b: '#5a6a8a', B: '#7a8ab0', Y: '#3a2a2a', w: '#c8a040' }),
  clocksoldier: { rows: ART.warrior.rows, pal: { k: K, e: '#7fe3ff', G: '#b8863a', g: '#7a5a20', s: '#5a5a6a', b: '#6a6a7a', B: '#9a9aaa', S: '#b8863a', Y: '#7fe3ff', w: '#e8e8f0', y: '#7a5a20', L: '#3a3a48' } },
  steamjugg: recolor('golem', { S: '#b8863a', s: '#7a5a20', C: '#ff6a2a' }),
});
Object.assign(ART, {
  icewight: recolor('wight', { C: '#5a7a9a', c: '#3a5a7a', B: '#c9f7ff' }),
  frostarcher: recolor('archer', { G: '#d8e4f0', g: '#a8b8cc', b: '#3a5a8a', B: '#5a7ab0' }),
  snowwolf: recolor('wolf', { G: '#e8eef4', g: '#a8b4c4', Y: '#7fe3ff' }),
  icegolem: recolor('golem', { S: '#a8d8f0', s: '#6aa8d0', C: '#ffffff' }),
  colossus: recolor('automaton', { Y: '#b8863a', y: '#7a5a20', C: '#ff4a2a' }),
  kobold: recolor('sapper', { G: '#c86a3a', g: '#8a4424', Y: '#ffe14d' }),
});

// ---------- hand-drawn 32×32 sprites ----------
// Drawn at full size (no doubling), as flat colour regions without outlines; flat32() adds the outline
// and the matte shading. They replace the 16×16 base classes only after every variant and recolour above
// has been built from the old grids, so the promotions and the Dark Knight keep working unchanged.
Object.assign(ART, {
  warrior: { pal: {'A': '#a8b0bc', 'a': '#7a8494', 'T': '#3a5aa8', 'Y': '#d0a840', 'P': '#c84040', 'k': '#2a2430', 'w': '#dfe6ee', 'h': '#6a4a2e', 'n': '#1e1a26', 'S': '#8a3a2a', 's': '#b85a3a'}, rows: [
    '.............PPP................',
    '............PPPPP...............',
    '...........PP..PP...............',
    '...........P....................',
    '..........AAAaaAAA.....ww.......',
    '.........AAAAaaAAAA....ww.......',
    '.........AAAAaaAAAA....ww.......',
    '.........AAAAaaAAAA....ww.......',
    '.........Annnnnnnnn....ww.......',
    '.........AAAAaaAAAA....ww.......',
    '.........AAAAaaAAAA....ww.......',
    '..........AAAaaAAA.....ww.......',
    '...........AAaaAA......ww.......',
    '......aaaaAAAAAAAAaaaa.ww.......',
    '...SsssssSAAAAAAAAaaaa.ww.......',
    '..SsssYsssSAAAAAAAaaAAAww.......',
    '..SsssYsssSTTYYTTTAAAYYYYYY.....',
    '..SYYYYYYYSTTYYTTTAAAAAhh.......',
    '..SsssYsssSTTYYTTTAAAaahh.......',
    '..SsssYsssSYYYYYYYAA.aaa........',
    '...SssYssSTTTYYTTTA.............',
    '...SssYssShhhhhhhhh.............',
    '....SsYsSATTTYYTTTA.............',
    '.....SsS.TTTTYYTTTT.............',
    '......S..TTTTYYTTTT.............',
    '..........aaa..aaa..............',
    '..........aaa..aaa..............',
    '..........aaa..aaa..............',
    '..........aaa..aaa..............',
    '.........kkkk..kkkk.............',
    '.........kkkk..kkkk.............',
    '................................'] },
  mage: { pal: {'H': '#5b3a8a', 'h': '#45296e', 'Y': '#c8a040', 's': '#e0b48a', 'S': '#a8785a', 'b': '#d8d4cc', 'w': '#6a4a2e', 'c': '#7fd8e8', 'e': '#1a1420', 'l': '#5a3a24', 'k': '#2e2438', 'R': '#3e2766'}, rows: [
    '........hh......................',
    '.........hhH........www.........',
    '..........hHHH.....w.ccw........',
    '............HHH....wcc.w........',
    '...........HHHHH...w.ccw........',
    '...........HHHHH....www.........',
    '..........HHHHHHH....ww.........',
    '..........HHHHHHHH...ww.........',
    '.........HHHHHHHHHH..ww.........',
    '.......HHHHHHHHHHHHHHww.........',
    '.....HHHHHHHHHHHHHHHHHH.........',
    '..........SSSSSSSS...ww.........',
    '..........ssessess...ww.........',
    '..........ssssssss...ww.........',
    '..........bbbbbbbb...ww.........',
    '........hhbbbbbbbbhh.ww.........',
    '.......hhhHbbbbbbHhhhww.........',
    '.......hhhHbbbbbbHHhsss.........',
    '.......hhhHHbbbbHHH.sss.........',
    '.......hhhHHHbbHHHH.sss.........',
    '.......hhhlllYYllllH.ww.........',
    '.......sssHHYRRYHHHH.ww.........',
    '.......sssHHYRRYHHHH.ww.........',
    '........HHHHYRRYHHHH.ww.........',
    '.......HHHHHYRRYHHHHHww.........',
    '.......HHHHHYRRYHHHHHww.........',
    '.......HHHHHYRRYHHHHHww.........',
    '.......HHHHHYRRYHHHHHHw.........',
    '......HYYYYYYYYYYYYYYYw.........',
    '.........kkkk..kkkk..ww.........',
    '.........kkkk..kkkk..ww.........',
    '................................'] },
  rogue: { pal: {'R': '#3a5aa8', 'r': '#2a4280', 's': '#d8a880', 'u': '#3a2a20', 'C': '#4a5a3a', 'V': '#8a6a46', 'v': '#6a4e32', 'w': '#dfe6ee', 'Y': '#c8a040', 'b': '#5a3a24', 'L': '#4a3e36', 'k': '#2a2028', 'e': '#1a1420', 'o': '#e8e0d0'}, rows: [
    '................................',
    '................................',
    '................................',
    '..........RRRRRRRR..............',
    '.........RRRRRRRRRR.............',
    '.........RRRRRRRRRR.............',
    '.....RRrrRRRRRRRRRR.............',
    '......Rr.rrrrrrrrrr.............',
    '.......r..ssssssss..............',
    '..........ssessess..............',
    '..........sssssssu..............',
    '..........suuuuuus.......ww.....',
    '.......CCCssssssss......ww......',
    '......CCCCCCooooooo....ww.......',
    '.....CCCCCCVooooVVVooo.w........',
    '.....CCCCCCVooooVVVooow.........',
    '.....CCCCCVVooooVVVooow.........',
    '.....CCCCCVVooooVVVooYYY........',
    '.....CCCCCVVooooVVVosss.........',
    '.....CCCCVVVooooVVVosss.........',
    '.....CCCCVVVooooVVV.............',
    '......CCCVVVooooVVV.............',
    '......sssbbbbYYbbbb.............',
    '......sssbbbbYYbbbb.............',
    '.........ooooooovvv.............',
    '.........ooooooovvv.............',
    '..........LLL..LLL..............',
    '..........LLL..LLL..............',
    '..........LLL..LLL..............',
    '.........kkkk..kkkk.............',
    '.........kkkk..kkkk.............',
    '................................'] },
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
// matte, hand-shaded art: EPX doubles it (rounding off diagonals), the doubled outline is thinned back
// to a single pixel, outlines go near black tinted by what they wrap, colours are muted, and each
// colour is a flat fill with one darker band on its lower-right side. No highlights: the owner wants
// it matte, not glossy.
const hexRGB = c => { const n = parseInt(c.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
const toHex = ([r, g, b]) => '#' + [r, g, b].map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('');
const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
// darker and cooler: a hue-shifted shade reads as shadow rather than as grey
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
  // a matte palette: colours pulled a fifth of the way toward grey and dimmed a touch
  const rgb = ch => { const c = hexRGB(art.pal[ch] || '#ff00ff'), l = c[0] * 0.3 + c[1] * 0.59 + c[2] * 0.11; return c.map(v => (v + (l - v) * 0.2) * 0.94); };
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const ch = t[y][x];
    if (ch === '.' || !art.pal[ch]) continue;
    let col = rgb(ch);
    if (ch === 'k') {
      // an outline is near black, tinted by what it wraps
      const inside = DIR4.map(([dx, dy]) => T(x + dx, y + dy)).find(fill);
      col = inside ? shade(rgb(inside), 0.88) : col;
    } else if (ch !== 'e') {
      // flat cel shading, no highlights: each colour keeps its flat fill, with one darker band along
      // its lower-right side, two pixels deep, where light from the upper left wouldn't reach
      const out = (dx, dy) => { const n = T(x + dx, y + dy); return n !== ch; };
      if (out(0, 1) || out(1, 0) || (out(2, 0) && out(1, 1)) || (out(0, 2) && out(1, 1))) col = shade(col, 0.3);
    }
    const i = (y * w + x) * 4;
    img.data[i] = col[0]; img.data[i + 1] = col[1]; img.data[i + 2] = col[2]; img.data[i + 3] = 255;
  }
  x2.putImageData(img, 0, 0);
  return c;
}

// The finish for a 32×32 grid: each colour a flat fill, one darker band where it ends to the lower
// right, a faint lighter edge where it starts upper left, and a near-black outline around the outside.
// 'e' (eyes) and 'o' (dark lines) stay flat.
function flat32(art) {
  const rows = art.rows, h = rows.length, w = rows[0].length;
  const at = (x, y) => (x < 0 || y < 0 || x >= w || y >= h ? '.' : rows[y][x]);
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const x2 = c.getContext('2d'), img = x2.createImageData(w, h);
  const DARK = [24, 16, 40], LIGHT = [255, 240, 210];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const ch = at(x, y);
    let col;
    if (ch === '.') {
      const inside = DIR4.map(([dx, dy]) => at(x + dx, y + dy)).find(n => n !== '.');
      if (!inside) continue;
      col = mix(art.pal[inside] ? hexRGB(art.pal[inside]) : DARK, DARK, 0.86);
    } else {
      col = hexRGB(art.pal[ch] || '#ff00ff');
      if (ch !== 'e' && ch !== 'o') {
        const ne = (dx, dy) => at(x + dx, y + dy) !== ch;
        if (ne(1, 0) || ne(0, 1) || (ne(2, 0) && ne(1, 1))) col = mix(col, DARK, 0.32);
        else if (ne(-1, 0) || ne(0, -1)) col = mix(col, LIGHT, 0.08);
      }
    }
    const i = (y * w + x) * 4;
    img.data[i] = col[0]; img.data[i + 1] = col[1]; img.data[i + 2] = col[2]; img.data[i + 3] = 255;
  }
  x2.putImageData(img, 0, 0);
  return c;
}

const canvases = {};
export function spriteCanvas(name) { return canvases[name] ||= (ART[name].rows.length === 32 ? flat32 : hifi)(ART[name]); }
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
