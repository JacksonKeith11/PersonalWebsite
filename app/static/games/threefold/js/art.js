// Pixel art for sprites, tiles and map icons, drawn from text grids into canvases for Phaser and the DOM.

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
  tree: {
    pal: { k: '#173018', T: '#2f7a3a', t: '#4fa04c', b: '#6a4a2a' },
    rows: [
      '................',
      '......kkkk......',
      '....kkTTTTkk....',
      '...kTTtTTTTTk...',
      '..kTTTTTTtTTTk..',
      '..kTtTTTTTTTTk..',
      '.kTTTTTtTTTTTTk.',
      '.kTTtTTTTTTtTTk.',
      '.kTTTTTTTTTTTTk.',
      '..kTTTtTTTTTTk..',
      '...kkTTTTTTkk...',
      '.....kkbbkk.....',
      '.......bb.......',
      '......kbbk......',
      '.....kkkkkk.....',
      '................',
    ],
  },
  rock: {
    pal: { k: '#2a2a33', R: '#8a8a96', r: '#b2b2bd', d: '#5a5a68' },
    rows: [
      '................', '................', '................', '................',
      '......kkkk......',
      '....kkRRRRkk....',
      '...kRRrRRRRRk...',
      '..kRrrRRRRRRRk..',
      '..kRrRRRRRRdRk..',
      '.kRRRRRRRRRRdRk.',
      '.kRRRRRRRRRRRdk.',
      '.kdRRRRRRRRddRk.',
      '.kddRRRRRRRdddk.',
      '..kkkkkkkkkkkk..',
      '................', '................',
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

const PROPS = {
  rubble: { pal: { k: '#1e1c28', R: '#6e6c80', r: '#8e8ca0', W: '#e8e2d0' }, rows: [
    '................', '................', '................', '................', '................', '................',
    '.......kk.......',
    '......kRRk......',
    '...kk.kRrRk.....',
    '..kRRkkRRRkk....',
    '..kRrRRkRRRRk...',
    '.kRRRRRRRWWRRk..',
    '.kRRWWRRRRRRRk..',
    'kRRRRRRRRRRrRRk.',
    'kkkkkkkkkkkkkkk.',
    '................'] },
  ash: { pal: { k: '#1a1416', A: '#6a5c5e', a: '#8a7c7e', t: '#3a2a22' }, rows: [
    '................', '................',
    '......t.........',
    '.....tt..t......',
    '......t.tt......',
    '.......tt.......',
    '.......t........',
    '.......t........',
    '......kkkk......',
    '....kkAaAAkk....',
    '...kAAaAAAAAk...',
    '..kAAAAAAaAAAk..',
    '.kAaAAAAAAAAAAk.',
    '.kAAAAAaAAAAAAk.',
    'kkkkkkkkkkkkkkkk',
    '................'] },
  coffin: { pal: { k: '#14121c', C: '#5a4a3a', c: '#7a6a52', Y: '#c8a040' }, rows: [
    '................', '................',
    '......kkkk......',
    '.....kCccCk.....',
    '....kCcCCcCk....',
    '....kCCYYCCk....',
    '....kCCYYCCk....',
    '....kCYYYYCk....',
    '....kCCYYCCk....',
    '....kCCYYCCk....',
    '.....kCCCCk.....',
    '.....kCCCCk.....',
    '......kCCk......',
    '......kkkk......',
    '................', '................'] },
};

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

function seeded(seed) {
  return () => {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function canvas16(fn) {
  const c = document.createElement('canvas');
  c.width = c.height = 16;
  fn(c.getContext('2d'));
  return c;
}
const recolorArt = (art, pal) => ({ rows: art.rows, pal: { ...art.pal, ...pal } });

function floor(theme, x, seed) {
  const r = seeded(seed);
  const dot = (col, n) => { x.fillStyle = col; for (let i = 0; i < n; i++) x.fillRect(r() * 16 | 0, r() * 16 | 0, 1, 1); };
  if (theme === 'wood') {
    x.fillStyle = '#4f8a3c'; x.fillRect(0, 0, 16, 16);
    dot('#5f9c48', 13); dot('#437a33', 13);
    x.fillStyle = '#6fb052';
    for (let i = 0; i < 3; i++) x.fillRect(r() * 15 | 0, r() * 14 | 0, 1, 2);
  } else if (theme === 'crypt') {
    x.fillStyle = '#4b4b5e'; x.fillRect(0, 0, 16, 16);
    dot('#56566c', 14); dot('#424254', 10);
    x.fillStyle = '#353545';
    x.fillRect(0, 7, 16, 1); x.fillRect(0, 15, 16, 1);
    const o = seed % 2 ? 4 : 10;
    x.fillRect(o, 0, 1, 7); x.fillRect((o + 7) % 16, 8, 1, 7);
  } else {
    x.fillStyle = '#3a2f30'; x.fillRect(0, 0, 16, 16);
    dot('#47393a', 16); dot('#2e2425', 10);
    x.fillStyle = '#6a2416';
    let cx = r() * 16 | 0, cy = r() * 16 | 0;
    for (let i = 0; i < 6; i++) { x.fillRect(cx, cy, 1, 1); cx = (cx + (r() < 0.5 ? 1 : 0)) % 16; cy = (cy + 1) % 16; }
    if (r() < 0.5) { x.fillStyle = '#ff6a2a'; x.fillRect(cx, cy, 1, 1); }
  }
}
function bricks(x, base, mortar, hi, seed) {
  const r = seeded(seed);
  x.fillStyle = base; x.fillRect(0, 0, 16, 16);
  x.fillStyle = mortar;
  for (let y = 3; y < 16; y += 4) x.fillRect(0, y, 16, 1);
  for (let row = 0; row < 4; row++) for (let bx = (row % 2) * 4; bx < 16; bx += 8) x.fillRect(bx, row * 4, 1, 3);
  x.fillStyle = hi;
  for (let row = 0; row < 4; row++) for (let bx = (row % 2) * 4 + 1; bx < 16; bx += 8) x.fillRect(bx, row * 4, 5, 1);
  x.fillStyle = 'rgba(0,0,0,0.25)'; x.fillRect(0, 14, 16, 2);
  for (let i = 0; i < 5; i++) { x.fillStyle = 'rgba(0,0,0,0.18)'; x.fillRect(r() * 16 | 0, r() * 16 | 0, 1, 1); }
}
function spikes(x, theme, seed) {
  const r = seeded(seed);
  const [a, b] = theme === 'wood' ? ['#6a3a1a', '#4a8a3a'] : theme === 'crypt' ? ['#e8e2d0', '#b8b0a0'] : ['#c48aff', '#ff8a3d'];
  for (let i = 0; i < 5; i++) {
    const sx = 1 + (r() * 12 | 0), sy = 5 + (r() * 9 | 0);
    x.fillStyle = '#140c14'; x.fillRect(sx, sy - 3, 3, 4);
    x.fillStyle = a; x.fillRect(sx + 1, sy - 3, 1, 3); x.fillRect(sx, sy - 1, 3, 1);
    x.fillStyle = b; x.fillRect(sx + 1, sy - 4, 1, 1);
  }
}
const THEME_KEYS = ['wood', 'crypt', 'ember'];
export const TILE_VARIANTS = [4, 2, 2, 3, 2, 3, 2, 2];
export const ANIMATED = new Set([3, 5]);

function tileCanvas(theme, type, v) {
  const seed = (THEME_KEYS.indexOf(theme) + 1) * 1000 + type * 97 + v * 13;
  return canvas16(x => {
    if (type === 3) {
      if (theme === 'wood') {
        x.fillStyle = '#2e5d93'; x.fillRect(0, 0, 16, 16);
        x.fillStyle = '#3f74b0';
        for (let y = 1; y < 16; y += 4) for (let i = 0; i < 16; i += 8) x.fillRect((i + v * 2 + y) % 16, y, 3, 1);
        x.fillStyle = '#9cc4ee';
        for (let y = 3; y < 16; y += 6) x.fillRect((y * 3 + v * 3) % 14, y, 2, 1);
      } else {
        x.fillStyle = '#07050c'; x.fillRect(0, 0, 16, 16);
        x.fillStyle = theme === 'crypt' ? '#2a2a3c' : '#3a1410'; x.fillRect(0, 0, 16, 3);
        x.fillStyle = theme === 'crypt' ? '#1a1a26' : '#24100c'; x.fillRect(0, 3, 16, 2);
        if (theme === 'ember') { x.fillStyle = ['#5a1a10', '#7a2414', '#5a1a10'][v]; x.fillRect(0, 13, 16, 3); x.fillStyle = '#ff6a2a'; x.fillRect((v * 5 + 3) % 16, 14, 1, 1); }
        else { x.fillStyle = '#3a3a52'; x.fillRect((v * 5 + 2) % 16, 8, 1, 1); }
      }
      return;
    }
    if (type === 5) {
      const r = seeded(77 + v);
      x.fillStyle = '#c8401a'; x.fillRect(0, 0, 16, 16);
      x.fillStyle = '#7a1e10';
      for (let i = 0; i < 10; i++) x.fillRect(r() * 15 | 0, r() * 15 | 0, 2, 1);
      x.fillStyle = '#ff8a1a';
      for (let i = 0; i < 6; i++) { const bx = (r() * 13 + v * 2) % 13 | 0, by = r() * 14 | 0; x.fillRect(bx, by, 3, 2); }
      x.fillStyle = '#ffd23f';
      for (let i = 0; i < 4; i++) x.fillRect((r() * 15 + v * 3) % 15 | 0, r() * 15 | 0, 1, 1);
      return;
    }
    if (type === 4) {
      if (theme === 'wood') { bricks(x, '#77786a', '#4a4b40', '#9a9b88', seed); x.fillStyle = '#4f8a3c'; x.fillRect(2, 0, 3, 1); x.fillRect(10, 4, 2, 1); }
      else if (theme === 'crypt') bricks(x, '#3c3754', '#221f30', '#57507a', seed);
      else bricks(x, '#211a2c', '#0e0a14', '#4a3a66', seed);
      return;
    }
    floor(theme, x, seed);
    if (type === 1) {
      const art = theme === 'wood' ? ART.tree : theme === 'crypt' ? PROPS.rubble : PROPS.ash;
      x.drawImage(paint(art), 0, 0);
    } else if (type === 2) {
      const art = theme === 'wood' ? ART.rock : theme === 'crypt' ? PROPS.coffin : recolorArt(ART.rock, { R: '#2e2240', r: '#4e3a6e', d: '#1a1226', k: '#0a0610' });
      x.drawImage(paint(art), 0, 0);
    } else if (type === 6) {
      x.fillStyle = 'rgba(255,255,230,0.16)'; x.fillRect(2, 2, 12, 11); x.fillRect(4, 1, 8, 1);
      x.fillStyle = 'rgba(255,255,230,0.22)'; x.fillRect(4, 3, 8, 2);
      x.fillStyle = 'rgba(0,0,0,0.3)'; x.fillRect(1, 13, 14, 2); x.fillRect(2, 15, 12, 1);
      x.fillStyle = 'rgba(0,0,0,0.15)'; x.fillRect(1, 3, 1, 10); x.fillRect(14, 3, 1, 10);
    } else if (type === 7) {
      spikes(x, theme, seed);
    }
  });
}

export const tileKey = (theme, type, v) => `t_${theme}_${type}_${v}`;
export const NODE_COLORS = { battle: '#8e3a35', elite: '#6a2f9a', event: '#2f5f99', shop: '#94701c', boss: '#5a1d2a' };

const canvases = {};
export function spriteCanvas(name) { return canvases[name] ||= paint(ART[name]); }
const urls = {};
export function spriteURL(name) { return urls[name] ||= spriteCanvas(name).toDataURL(); }
export function iconCanvas(name) { return canvases['icon_' + name] ||= paint(ICONS[name]); }

export function buildTextures(scene) {
  const tex = scene.textures;
  for (const name of Object.keys(ART)) if (ART[name] && !tex.exists('s_' + name)) tex.addCanvas('s_' + name, spriteCanvas(name));
  for (const name of Object.keys(ICONS)) if (!tex.exists('i_' + name)) tex.addCanvas('i_' + name, iconCanvas(name));
  for (const theme of THEME_KEYS) for (let type = 0; type < 8; type++) for (let v = 0; v < TILE_VARIANTS[type]; v++) {
    const k = tileKey(theme, type, v);
    if (!tex.exists(k)) tex.addCanvas(k, tileCanvas(theme, type, v));
  }
  if (!tex.exists('px')) {
    const c = document.createElement('canvas'); c.width = c.height = 4;
    const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, 4, 4);
    tex.addCanvas('px', c);
  }
}
