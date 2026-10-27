'use strict';
// Threefold Path: a branching-map roguelike with grid tactics battles.
// Everything is drawn from the pixel maps below; there are no image files.
(() => {
  const params = new URLSearchParams(location.search);
  const AUTO = params.has('auto'); // heroes play themselves; used to test balance
  const SPEED = AUTO ? 0.01 : 1;
  const S = 4;                 // canvas pixels per art pixel
  const TS = 16 * S;           // tile size on the board canvas
  const GW = 10, GH = 8;       // board size in tiles
  const MAP_ROWS = 12, MAP_COLS = 7, MAP_TOP = 56, MAP_STEP = 64;
  const SAVE_KEY = 'threefold-path-run';
  const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];

  // ---------- helpers ----------
  const rnd = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
  const pick = a => a[Math.floor(Math.random() * a.length)];
  const chance = p => Math.random() < p;
  const key = (x, y) => x + ',' + y;
  const inb = (x, y) => x >= 0 && y >= 0 && x < GW && y < GH;
  const dist = (a, b) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
  const sleep = ms => new Promise(r => setTimeout(r, ms * SPEED));
  function shuffle(a) {
    for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  }
  function tween(ms, fn) {
    ms *= SPEED;
    if (ms < 8) { fn(1); return Promise.resolve(); }
    return new Promise(res => {
      const t0 = performance.now();
      const step = now => {
        const t = Math.min(1, (now - t0) / ms);
        fn(t);
        if (t < 1) requestAnimationFrame(step); else res();
      };
      requestAnimationFrame(step);
    });
  }
  function seeded(seed) {
    return () => {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function h(tag, attrs = {}, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') el.className = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else if (v !== false && v != null) el.setAttribute(k, v === true ? '' : v);
    }
    for (const c of kids.flat()) {
      if (c == null || c === false) continue;
      el.append(c.nodeType ? c : document.createTextNode(String(c)));
    }
    return el;
  }

  // ---------- pixel art ----------
  const K = '#1b1226';
  const ART = {
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
  ART.knight = { rows: ART.warrior.rows, pal: { k: K, e: '#ff4040', G: '#3e3650', g: '#272033', s: '#2a2033', b: '#7a1f2b', B: '#b13a3a', S: '#2b2b35', Y: '#d14b4b', w: '#c7c7d1', y: '#6a6a74', L: '#1f1a26' } };
  ART.shaman = { rows: ART.cultist.rows, pal: { k: K, R: '#3e7d4a', r: '#2a5734', Y: '#c9f7ff', O: '#9cf07a' } };

  const ICONS = {
    battle: { pal: { w: '#eef2f7', k: '#3a2a1a', y: '#d9a33a' }, rows: ['.......w', '......ww', '.....ww.', '.k..ww..', '..kww...', '..yk....', '.y..k...', 'y.......'] },
    elite: { pal: { w: '#f1ead8', k: K }, rows: ['..wwww..', '.wwwwww.', '.wkwwkw.', '.wkwwkw.', '.wwwwww.', '..wkkw..', '..wwww..', '..w..w..'] },
    event: { pal: { y: '#ffe680' }, rows: ['..yyyy..', '.yy..yy.', '.....yy.', '....yy..', '...yy...', '...yy...', '........', '...yy...'] },
    shop: { pal: { k: '#6a4a1a', y: '#f2c94c', Y: '#fff0a0' }, rows: ['...kk...', '..kyyk..', '...kk...', '..yyyy..', '.yyYyyy.', '.yYyyyy.', '.yyyyyy.', '..yyyy..'] },
    boss: { pal: { y: '#f2c94c', r: '#e04848' }, rows: ['........', 'y..y..y.', 'yy.y.yy.', 'yyyyyyy.', 'yryyryy.', 'yyyyyyy.', 'yyyyyyy.', '........'] },
  };

  function paint(art) {
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
  function flipped(src) {
    const c = document.createElement('canvas');
    c.width = src.width; c.height = src.height;
    const x = c.getContext('2d');
    x.translate(src.width, 0); x.scale(-1, 1); x.drawImage(src, 0, 0);
    return c;
  }
  function whitened(src) {
    const c = document.createElement('canvas');
    c.width = src.width; c.height = src.height;
    const x = c.getContext('2d');
    x.drawImage(src, 0, 0);
    x.globalCompositeOperation = 'source-in';
    x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height);
    return c;
  }
  const SPR = {};
  for (const [name, art] of Object.entries(ART)) {
    const n = paint(art), f = flipped(n);
    SPR[name] = { n, f, wn: whitened(n), wf: whitened(f) };
  }
  const ICON = {};
  for (const [name, art] of Object.entries(ICONS)) ICON[name] = paint(art);
  const urlCache = {};
  function sprURL(name, flip) {
    const k = name + (flip ? ':f' : '');
    return urlCache[k] ||= (flip ? SPR[name].f : SPR[name].n).toDataURL();
  }
  const sprImg = (name, flip, title) => h('img', { class: 'spr', src: sprURL(name, flip), alt: title || '' });

  function tile(fn) {
    const c = document.createElement('canvas');
    c.width = c.height = 16;
    fn(c.getContext('2d'));
    return c;
  }
  function grass(x, seed) {
    const r = seeded(seed);
    x.fillStyle = '#4f8a3c'; x.fillRect(0, 0, 16, 16);
    for (let i = 0; i < 26; i++) {
      x.fillStyle = r() < 0.5 ? '#5f9c48' : '#437a33';
      x.fillRect(r() * 16 | 0, r() * 16 | 0, 1, 1);
    }
    for (let i = 0; i < 3; i++) {
      const gx = r() * 15 | 0, gy = r() * 14 | 0;
      x.fillStyle = '#6fb052'; x.fillRect(gx, gy, 1, 2);
    }
  }
  const TILE = {
    grass: [1, 2, 3, 4].map(s => tile(x => grass(x, s * 977))),
    forest: [5, 6].map(s => tile(x => { grass(x, s * 977); x.drawImage(paint(ART.tree), 0, 0); })),
    rock: [7, 8].map(s => tile(x => { grass(x, s * 977); x.drawImage(paint(ART.rock), 0, 0); })),
    water: [0, 1, 2].map(f => tile(x => {
      x.fillStyle = '#2e5d93'; x.fillRect(0, 0, 16, 16);
      x.fillStyle = '#3f74b0';
      for (let y = 1; y < 16; y += 4) for (let i = 0; i < 16; i += 8) x.fillRect((i + f * 2 + y) % 16, y, 3, 1);
      x.fillStyle = '#9cc4ee';
      for (let y = 3; y < 16; y += 6) x.fillRect((y * 3 + f * 3) % 14, y, 2, 1);
    })),
  };

  // ---------- data ----------
  const CLASSES = {
    warrior: { name: 'Warrior', hp: 44, atk: 10, mag: 2, def: 5, res: 2, spd: 8, mov: 3, crit: 5, main: 'atk', skills: ['strike', 'cleave', 'bash', 'warcry'] },
    mage: { name: 'Mage', hp: 28, atk: 3, mag: 11, def: 1, res: 5, spd: 7, mov: 3, crit: 5, main: 'mag', skills: ['bolt', 'fireball', 'frost', 'heal'] },
    rogue: { name: 'Rogue', hp: 32, atk: 9, mag: 2, def: 2, res: 2, spd: 11, mov: 4, crit: 15, flank: 1.5, main: 'atk', skills: ['stab', 'knives', 'venom', 'assassinate'] },
  };

  // Each upgrade overrides fields of the skill; level N applies the first N-1 upgrades.
  const SKILLS = {
    strike: { name: 'Strike', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0, txt: 'A solid sword blow.',
      ups: [{ note: 'Power 115%', pow: 1.15 }, { note: 'Power 130%', pow: 1.3 }, { note: 'Knocks the target back', knock: true }] },
    cleave: { name: 'Cleave', kind: 'phys', tgt: 'self', range: [0, 0], aoe: 1, hits: 'foes', pow: 0.9, cd: 2, txt: 'Sweep every foe next to you.',
      ups: [{ note: 'Power 110%', pow: 1.1 }, { note: 'Also hits diagonals', diag: true }, { note: 'Power 130%, cooldown 1', pow: 1.3, cd: 1 }] },
    bash: { name: 'Shield Bash', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 0.7, cd: 3, stun: 1, txt: 'The target loses its next turn.',
      ups: [{ note: 'Power 95%', pow: 0.95 }, { note: 'Cooldown 2', cd: 2 }, { note: 'Power 115%, knocks back', pow: 1.15, knock: true }] },
    warcry: { name: 'War Cry', kind: 'buff', tgt: 'self', range: [0, 0], aoe: 3, hits: 'foes', taunt: 2, guard: true, cd: 4,
      txt: 'Nearby foes must attack you, and you take 40% less damage until your next turn.',
      ups: [{ note: 'Radius 4', aoe: 4 }, { note: 'Cooldown 3', cd: 3 }, { note: 'Also heals you 25% of max HP', selfHeal: 0.25 }] },

    bolt: { name: 'Arcane Bolt', kind: 'mag', tgt: 'foe', range: [2, 4], pow: 0.75, cd: 0, txt: 'A bolt of force from afar.',
      ups: [{ note: 'Power 90%', pow: 0.9 }, { note: 'Range 1–5', range: [1, 5] }, { note: 'Power 105%', pow: 1.05 }] },
    fireball: { name: 'Fireball', kind: 'mag', tgt: 'tile', range: [2, 5], aoe: 1, hits: 'all', pow: 1.15, cd: 3, txt: 'Explodes on a tile. Burns friend and foe alike.',
      ups: [{ note: 'Power 140%', pow: 1.4 }, { note: 'No longer hurts allies', hits: 'foes' }, { note: 'Power 160%, sets targets burning', pow: 1.6, burn: 2 }] },
    frost: { name: 'Frost Lance', kind: 'mag', tgt: 'foe', range: [1, 4], pow: 0.9, cd: 2, slow: 2, txt: 'The target acts at half speed for 2 turns.',
      ups: [{ note: 'Power 115%', pow: 1.15 }, { note: 'Shatters onto adjacent foes', aoe: 1, hits: 'foes' }, { note: 'Power 135%, cooldown 1', pow: 1.35, cd: 1 }] },
    heal: { name: 'Mend', kind: 'heal', tgt: 'ally', range: [0, 3], pow: 1.0, cd: 2, cleanse: true, txt: 'Restores HP and cures poison and burns.',
      ups: [{ note: 'Heals 130%', pow: 1.3 }, { note: 'Also heals allies around the target', aoe: 1, hits: 'allies' }, { note: 'Heals 160%, cooldown 1', pow: 1.6, cd: 1 }] },

    stab: { name: 'Stab', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0, txt: 'Quick dagger work.',
      ups: [{ note: 'Power 115%', pow: 1.15 }, { note: 'Strikes twice at 75%', double: true, pow: 0.75 }, { note: 'Strikes twice at 90%', pow: 0.9 }] },
    knives: { name: 'Throwing Knives', kind: 'phys', tgt: 'foe', range: [2, 4], pow: 0.7, cd: 1, txt: 'A knife from a distance.',
      ups: [{ note: 'Power 85%', pow: 0.85 }, { note: 'Range 2–5, no cooldown', range: [2, 5], cd: 0 }, { note: 'Throws two knives', double: true }] },
    venom: { name: 'Venom Blade', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 0.8, cd: 3, poison: 3, poisonPow: 0.35, txt: 'Poison deals damage at the start of each of its next 3 turns.',
      ups: [{ note: 'Stronger poison', poisonPow: 0.55 }, { note: 'Cooldown 2', cd: 2 }, { note: 'Power 100%, also slows', pow: 1.0, slow: 2 }] },
    assassinate: { name: 'Assassinate', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.3, cd: 4, execute: true, txt: 'Double damage against targets under half HP.',
      ups: [{ note: 'Power 160%', pow: 1.6 }, { note: 'Cooldown 3', cd: 3 }, { note: 'A kill resets the cooldown and lets you move again', resetOnKill: true }] },

    e_slam: { name: 'Slam', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0 },
    e_stab: { name: 'Stab', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0 },
    e_shoot: { name: 'Shoot', kind: 'phys', tgt: 'foe', range: [2, 5], pow: 0.9, cd: 0 },
    e_bite: { name: 'Rending Bite', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 0.9, poison: 2, poisonPow: 0.25, cd: 0, txt: 'Leaves the target bleeding.' },
    e_drain: { name: 'Drain', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 0.9, drain: 0.5, cd: 0, txt: 'Heals itself for half the damage.' },
    e_slash: { name: 'Slash', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0 },
    e_hex: { name: 'Hex', kind: 'mag', tgt: 'foe', range: [2, 4], pow: 0.8, cd: 0 },
    e_flame: { name: 'Flame Burst', kind: 'mag', tgt: 'tile', range: [2, 4], aoe: 1, hits: 'all', pow: 1.0, burn: 2, cd: 3 },
    e_zap: { name: 'Zap', kind: 'mag', tgt: 'foe', range: [2, 3], pow: 0.6, cd: 0 },
    e_mend: { name: 'Mend', kind: 'heal', tgt: 'ally', range: [0, 3], pow: 1.2, cd: 2 },
    e_smash: { name: 'Smash', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.15, cd: 0 },
    e_stomp: { name: 'Stomp', kind: 'phys', tgt: 'self', range: [0, 0], aoe: 1, hits: 'foes', pow: 0.8, stun: 1, cd: 3 },
    e_kcleave: { name: 'Reaping Arc', kind: 'phys', tgt: 'self', range: [0, 0], aoe: 1, diag: true, hits: 'foes', pow: 1.0, cd: 2 },
    e_pound: { name: 'Pound', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.2, stun: 1, cd: 3 },
    e_rock: { name: 'Hurl Rock', kind: 'phys', tgt: 'foe', range: [2, 4], pow: 0.8, cd: 2 },
    e_deathbolt: { name: 'Death Bolt', kind: 'mag', tgt: 'foe', range: [2, 5], pow: 1.0, cd: 0 },
    e_nova: { name: 'Grave Nova', kind: 'mag', tgt: 'self', range: [0, 0], aoe: 2, hits: 'foes', pow: 0.85, cd: 3 },
    e_raise: { name: 'Raise Dead', kind: 'summon', tgt: 'self', range: [0, 0], cd: 4, txt: 'Calls up two skeletons.' },
  };

  const FOES = {
    slime: { name: 'Slime', hp: 18, atk: 6, def: 1, res: 1, spd: 5, mov: 2, skills: ['e_slam'] },
    goblin: { name: 'Goblin', hp: 15, atk: 7, def: 1, res: 1, spd: 10, mov: 4, skills: ['e_stab'] },
    archer: { name: 'Goblin Archer', hp: 13, atk: 7, def: 1, res: 1, spd: 8, mov: 3, skills: ['e_shoot'], ai: 'ranged' },
    wolf: { name: 'Wolf', hp: 17, atk: 7, def: 1, res: 1, spd: 12, mov: 5, skills: ['e_bite'] },
    bat: { name: 'Bat', hp: 10, atk: 5, def: 0, res: 1, spd: 13, mov: 5, fly: true, skills: ['e_drain'] },
    skeleton: { name: 'Skeleton', hp: 24, atk: 8, def: 4, res: 0, spd: 6, mov: 3, skills: ['e_slash'] },
    cultist: { name: 'Cultist', hp: 17, atk: 3, mag: 9, def: 1, res: 3, spd: 7, mov: 3, skills: ['e_flame', 'e_hex'], ai: 'ranged' },
    shaman: { name: 'Shaman', hp: 18, atk: 3, mag: 8, def: 1, res: 3, spd: 7, mov: 3, skills: ['e_mend', 'e_zap'], ai: 'ranged' },
    orc: { name: 'Orc Brute', hp: 36, atk: 11, def: 3, res: 1, spd: 5, mov: 3, skills: ['e_stomp', 'e_smash'] },
    knight: { name: 'Dark Knight', hp: 60, atk: 12, def: 6, res: 3, spd: 7, mov: 3, skills: ['e_kcleave', 'e_slash'] },
    golem: { name: 'Stone Golem', hp: 75, atk: 13, def: 8, res: 2, spd: 4, mov: 2, skills: ['e_pound', 'e_rock', 'e_slam'] },
    lich: { name: 'The Hollow King', hp: 110, atk: 4, mag: 12, def: 3, res: 6, spd: 8, mov: 3, skills: ['e_raise', 'e_nova', 'e_deathbolt'], ai: 'ranged', boss: true },
  };

  const ENCOUNTERS = {
    1: [['slime', 'slime', 'goblin'], ['goblin', 'goblin', 'archer'], ['slime', 'slime', 'slime'], ['wolf', 'wolf', 'goblin'], ['goblin', 'archer', 'slime']],
    2: [['skeleton', 'skeleton', 'archer', 'cultist'], ['orc', 'goblin', 'goblin', 'shaman'], ['wolf', 'wolf', 'wolf', 'bat', 'bat'],
      ['cultist', 'skeleton', 'bat', 'bat'], ['orc', 'archer', 'archer'], ['skeleton', 'shaman', 'wolf', 'archer']],
    3: [['orc', 'orc', 'shaman', 'archer'], ['skeleton', 'skeleton', 'cultist', 'cultist'], ['orc', 'wolf', 'wolf', 'shaman'],
      ['skeleton', 'orc', 'shaman', 'bat', 'bat'], ['cultist', 'orc', 'archer', 'skeleton']],
    elite2: [['golem', 'slime', 'slime'], ['knight', 'goblin', 'goblin']],
    elite3: [['golem', 'knight'], ['knight', 'knight', 'shaman'], ['golem', 'cultist', 'cultist']],
    boss: [['lich', 'skeleton', 'cultist']],
  };

  const ITEMS = {
    shield: { name: 'Iron Buckler', price: 55, stats: { def: 3 }, txt: '+3 DEF' },
    band: { name: 'Power Band', price: 65, stats: { atk: 3 }, txt: '+3 ATK' },
    ring: { name: "Sage's Ring", price: 65, stats: { mag: 3 }, txt: '+3 MAG' },
    cloak: { name: 'Warding Cloak', price: 50, stats: { res: 3 }, txt: '+3 RES' },
    heart: { name: 'Heartstone', price: 60, stats: { maxHp: 12 }, txt: '+12 max HP' },
    feather: { name: 'Quick Feather', price: 55, stats: { spd: 3 }, txt: '+3 SPD: takes turns more often' },
    coin: { name: 'Lucky Coin', price: 50, stats: { crit: 10 }, txt: '+10% critical hit chance' },
    boots: { name: 'Swift Boots', price: 80, stats: { mov: 1 }, unique: true, txt: '+1 MOV' },
    scope: { name: 'Long Scope', price: 80, unique: true, txt: 'Ranged skills reach 1 tile farther' },
    hourglass: { name: 'Hourglass', price: 100, unique: true, txt: 'Cooldowns of 2 or more are 1 turn shorter' },
    fang: { name: 'Vampire Fang', price: 90, unique: true, txt: 'Heal 20% of the damage you deal' },
    venom: { name: 'Venom Vial', price: 75, unique: true, txt: 'Physical hits poison for 2 turns' },
    ember: { name: 'Ember Gem', price: 75, unique: true, txt: 'Magic hits burn for 2 turns' },
    belt: { name: "Giant's Belt", price: 100, unique: true, txt: 'Area skills grow 1 tile in radius' },
    thorns: { name: 'Thorn Mail', price: 70, unique: true, txt: 'Adjacent attackers take 30% of their damage back' },
    focus: { name: 'Focus Crystal', price: 85, unique: true, txt: 'Skills with a cooldown of 2+ deal 30% more' },
    axe: { name: "Executioner's Edge", price: 80, unique: true, txt: '+40% damage to targets under half HP' },
    charm: { name: 'Mending Charm', price: 70, unique: true, txt: 'Regain 8% of max HP at the start of each turn' },
  };

  // ---------- run state ----------
  let run = null;

  function newHero(cls) {
    const c = CLASSES[cls];
    return { cls, name: c.name, maxHp: c.hp, hp: c.hp, atk: c.atk, mag: c.mag, def: c.def, res: c.res, spd: c.spd, mov: c.mov, crit: c.crit, items: [], skills: c.skills.map(id => ({ id, lv: 1 })) };
  }
  function heroStats(hero) {
    const o = { maxHp: hero.maxHp, atk: hero.atk, mag: hero.mag, def: hero.def, res: hero.res, spd: hero.spd, mov: hero.mov, crit: hero.crit };
    for (const id of hero.items) for (const [k, v] of Object.entries(ITEMS[id].stats || {})) o[k] += v;
    return o;
  }
  const has = (u, id) => !!(u.items && u.items.includes(id));

  function newRun() {
    run = { party: ['warrior', 'mage', 'rogue'].map(newHero), gold: 60, map: genMap(), pos: null, visited: [], seen: [], stats: { kills: 0, battles: 0 } };
    showMap();
  }
  function save() {
    try { localStorage.setItem(SAVE_KEY, JSON.stringify(run)); } catch (e) { /* storage unavailable */ }
  }
  function load() {
    try { const s = localStorage.getItem(SAVE_KEY); return s ? JSON.parse(s) : null; } catch (e) { return null; }
  }
  function clearSave() {
    try { localStorage.removeItem(SAVE_KEY); } catch (e) { /* storage unavailable */ }
  }

  function skStats(u, s) {
    const d = SKILLS[s.id];
    const o = { ...d, id: s.id, lv: s.lv };
    for (let i = 0; i < s.lv - 1 && d.ups && i < d.ups.length; i++) {
      const { note, ...rest } = d.ups[i];
      Object.assign(o, rest);
    }
    if (!o.hits) o.hits = o.kind === 'heal' ? 'allies' : 'foes';
    if (has(u, 'scope') && o.range[1] > 1 && o.tgt !== 'self') o.range = [o.range[0], o.range[1] + 1];
    if (has(u, 'belt') && o.aoe) o.aoe += 1;
    if (has(u, 'hourglass') && o.cd > 1) o.cd -= 1;
    return o;
  }
  function describe(o) {
    const parts = [];
    const [a, b] = o.range;
    if (o.tgt === 'self') parts.push(o.aoe ? `Around you, radius ${o.aoe}${o.diag ? ' (with diagonals)' : ''}` : 'Self');
    else parts.push(`Range ${a === b ? a : a + '–' + b}`);
    if (o.aoe && o.tgt !== 'self') parts.push(`Area ${o.aoe}`);
    if (o.kind === 'heal') parts.push(`Heals ${Math.round(o.pow * 100)}% MAG`);
    else if (o.kind === 'phys' || o.kind === 'mag') parts.push(`${Math.round(o.pow * 100)}% ${o.kind === 'mag' ? 'MAG' : 'ATK'}${o.double ? ' ×2' : ''}`);
    if (o.hits === 'all' && o.aoe) parts.push('Hits allies too');
    if (o.stun) parts.push('Stuns');
    if (o.slow) parts.push('Slows');
    if (o.poison) parts.push('Poisons');
    if (o.burn) parts.push('Burns');
    if (o.knock) parts.push('Knockback');
    if (o.taunt) parts.push('Taunts');
    if (o.execute) parts.push('×2 under half HP');
    if (o.drain) parts.push('Drains');
    parts.push(o.cd ? `Cooldown ${o.cd}` : 'No cooldown');
    return parts.join(' · ');
  }

  // ---------- map ----------
  function genMap() {
    const nodes = {};
    const edges = new Set();
    const node = (r, c) => nodes[r + ':' + c] ||= { id: r + ':' + c, r, c, type: null, next: [], jx: rnd(-10, 10), jy: rnd(-8, 8) };
    const starts = shuffle([0, 1, 2, 3, 4, 5, 6]);
    for (let p = 0; p < 6; p++) {
      let c = p < 3 ? starts[p] : pick(starts.slice(0, 3));
      node(0, c);
      for (let r = 0; r < MAP_ROWS - 1; r++) {
        const opts = [c - 1, c, c + 1].filter(n => n >= 0 && n < MAP_COLS &&
          !(n === c + 1 && edges.has(`${r}:${c + 1}>${r + 1}:${c}`)) &&
          !(n === c - 1 && edges.has(`${r}:${c - 1}>${r + 1}:${c}`)));
        const n = pick(opts);
        const e = `${r}:${c}>${r + 1}:${n}`;
        if (!edges.has(e)) { edges.add(e); node(r, c).next.push(node(r + 1, n).id); }
        c = n;
      }
    }
    const boss = { id: 'boss', r: MAP_ROWS, c: 3, type: 'boss', next: [], jx: 0, jy: 0 };
    for (const n of Object.values(nodes)) {
      if (n.r === MAP_ROWS - 1) { n.next.push('boss'); n.type = 'shop'; continue; }
      if (n.r === 0) { n.type = 'battle'; continue; }
      const roll = Math.random();
      if (n.r >= 4 && roll < 0.16) n.type = 'elite';
      else if (n.r >= 2 && roll < 0.30) n.type = 'shop';
      else if (roll < 0.56) n.type = 'event';
      else n.type = 'battle';
    }
    nodes.boss = boss;
    return nodes;
  }
  const nodePos = n => n.id === 'boss'
    ? { x: 240, y: MAP_TOP }
    : { x: 48 + n.c * 64 + n.jx, y: MAP_TOP + (MAP_ROWS - n.r) * MAP_STEP + n.jy };
  function available() {
    if (!run.pos) return Object.values(run.map).filter(n => n.r === 0);
    return run.map[run.pos].next.map(id => run.map[id]);
  }
  const floorOf = n => n.r + 1;
  const NODE_COLORS = { battle: '#8e3a35', elite: '#6a2f9a', event: '#2f5f99', shop: '#94701c', boss: '#5a1d2a' };
  const NODE_NAMES = { battle: 'Battle', elite: 'Elite battle', event: 'Unknown event', shop: 'Shop', boss: 'The Hollow King' };

  // ---------- screens ----------
  const screen = document.getElementById('screen');
  const modal = document.getElementById('modal');
  let drawFn = null;
  function setScreen(...kids) {
    drawFn = null;
    screen.replaceChildren(...kids);
    window.scrollTo(0, 0);
  }
  function loop(now) {
    if (drawFn) drawFn(now);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  const auto = fn => { if (AUTO) setTimeout(fn, 5); };

  function hud(inBattle) {
    const el = document.getElementById('hud');
    if (!run) { el.replaceChildren(); return; }
    const floor = run.pos ? floorOf(run.map[run.pos]) : 1;
    el.replaceChildren(
      h('span', { class: 'hud-item' }, 'Floor ', h('b', {}, `${floor}/${MAP_ROWS + 1}`)),
      h('span', { class: 'hud-item' }, 'Gold ', h('b', {}, run.gold)),
      ...run.party.map(p => h('span', { class: 'hud-hero', title: p.name }, sprImg(p.cls), `${p.hp}/${heroStats(p).maxHp}`)),
      ...(inBattle ? [] : [h('button', { class: 'btn', onclick: showParty }, 'Party')]),
    );
  }

  function showTitle() {
    run = null;
    hud();
    const saved = load();
    setScreen(h('div', { class: 'panel center' },
      h('div', { class: 'title-name' }, 'Threefold Path'),
      h('div', { class: 'title-art' }, sprImg('warrior'), sprImg('mage'), sprImg('rogue')),
      h('p', {}, 'Three heroes. One branching road. The Hollow King waits at the top.'),
      saved ? h('button', { class: 'btn big go', onclick: () => { run = saved; showMap(); } }, 'Continue run') : null,
      h('button', { class: 'btn big', onclick: () => { clearSave(); newRun(); } }, saved ? 'New run' : 'Start run'),
      h('div', { class: 'howto' },
        h('h3', {}, 'How to play'),
        h('ul', {},
          h('li', {}, 'Pick a path up the map. Each step is a battle, an event (?), or a shop. Elite battles (skulls) are harder but drop an item.'),
          h('li', {}, 'In battle, units take turns by speed (see the "Next" strip). On a hero\'s turn, move once and act once, in either order.'),
          h('li', {}, 'Blue tiles show where you can move; red tiles show what a skill can reach. Forests slow movement but cut damage taken by 20%.'),
          h('li', {}, 'Flank: hitting a foe that another hero is standing next to deals 25% more (the Rogue gets 50%).'),
          h('li', {}, 'HP carries between fights. Win to earn gold and a skill upgrade; spend gold in shops on gear, training and rest.'),
          h('li', {}, 'Tap any unit to see its stats and abilities. On touch screens, tap a target once to preview, again to confirm.'),
        ),
      ),
    ));
    auto(() => { clearSave(); newRun(); });
  }

  function showMap() {
    save();
    hud();
    const height = MAP_TOP * 2 + MAP_ROWS * MAP_STEP;
    const cv = h('canvas', { width: 480, height });
    const wrap = h('div', { class: 'mapwrap' }, cv);
    const legend = h('div', { class: 'legend panel' }, h('h3', {}, 'Choose your path'),
      ...['battle', 'elite', 'event', 'shop', 'boss'].map(t => {
        const c = h('canvas', { width: 24, height: 24 });
        const x = c.getContext('2d');
        x.imageSmoothingEnabled = false;
        x.fillStyle = NODE_COLORS[t]; x.fillRect(0, 0, 24, 24);
        x.drawImage(ICON[t], 4, 4, 16, 16);
        return h('div', {}, c, NODE_NAMES[t]);
      }),
      h('p', { class: 'muted' }, 'Glowing nodes are reachable. The last row before the boss is all shops.'));
    setScreen(h('div', { class: 'map-layout' }, wrap, legend));
    const ctx = cv.getContext('2d');
    const avail = new Set(available().map(n => n.id));
    const visited = new Set(run.visited);
    drawFn = now => drawMap(ctx, avail, visited, now);
    cv.addEventListener('click', e => {
      const r = cv.getBoundingClientRect();
      const mx = (e.clientX - r.left) * 480 / r.width, my = (e.clientY - r.top) * height / r.height;
      for (const id of avail) {
        const p = nodePos(run.map[id]);
        if (Math.hypot(p.x - mx, p.y - my) < 26) { enterNode(run.map[id]); return; }
      }
    });
    const first = run.map[[...avail][0]];
    if (first) requestAnimationFrame(() => { wrap.scrollTop = nodePos(first).y * cv.clientHeight / height - wrap.clientHeight * 0.6; });
    auto(() => enterNode(run.map[pick([...avail])]));
  }

  function drawMap(c, avail, visited, now) {
    c.imageSmoothingEnabled = false;
    c.fillStyle = '#1d1628'; c.fillRect(0, 0, c.canvas.width, c.canvas.height);
    c.fillStyle = '#251c33';
    for (let y = 0; y < c.canvas.height; y += 16) for (let x = (y / 16 % 2) * 16; x < 480; x += 32) c.fillRect(x, y, 16, 16);
    const nodes = Object.values(run.map);
    for (const n of nodes) {
      const a = nodePos(n);
      for (const id of n.next) {
        const b = nodePos(run.map[id]);
        const walked = visited.has(n.id) && visited.has(id);
        const len = Math.hypot(b.x - a.x, b.y - a.y), steps = Math.floor(len / 10);
        c.fillStyle = walked ? '#f2c94c' : (n.id === run.pos || (!run.pos && n.r === 0)) && avail.has(id) ? '#c8b8e0' : '#4d3c66';
        for (let i = 2; i < steps - 1; i++) {
          const t = i / steps;
          c.fillRect(Math.round(a.x + (b.x - a.x) * t) - 2, Math.round(a.y + (b.y - a.y) * t) - 2, 4, 4);
        }
      }
    }
    for (const n of nodes) {
      const p = nodePos(n);
      const big = n.type === 'boss';
      const r = big ? 26 : 18;
      const on = avail.has(n.id);
      if (on) {
        const pulse = 3 + Math.round(Math.sin(now / 200) * 2 + 2);
        c.fillStyle = '#f2c94c';
        c.fillRect(p.x - r - pulse, p.y - r - pulse, (r + pulse) * 2, (r + pulse) * 2);
      }
      c.fillStyle = '#000'; c.fillRect(p.x - r - 3, p.y - r - 3, r * 2 + 6, r * 2 + 6);
      c.fillStyle = visited.has(n.id) || on || big ? NODE_COLORS[n.type] : '#3a2f48';
      c.fillRect(p.x - r, p.y - r, r * 2, r * 2);
      c.globalAlpha = visited.has(n.id) ? 0.45 : (on || big ? 1 : 0.7);
      const s = big ? 32 : 24;
      c.drawImage(ICON[n.type], p.x - s / 2, p.y - s / 2, s, s);
      c.globalAlpha = 1;
      if (n.id === run.pos) {
        c.drawImage(SPR.warrior.n, p.x - 16, p.y - r - 30, 32, 32);
      }
    }
  }

  function enterNode(n) {
    run.pos = n.id;
    run.visited.push(n.id);
    if (n.type === 'battle') startBattle('normal');
    else if (n.type === 'elite') startBattle('elite');
    else if (n.type === 'boss') startBattle('boss');
    else if (n.type === 'event') showEvent();
    else showShop(n);
  }

  function showParty() {
    if (!run) return;
    const close = () => { modal.hidden = true; modal.replaceChildren(); };
    modal.replaceChildren(h('div', { class: 'modal-box' },
      h('div', { class: 'row' }, h('h2', { class: 'grow' }, 'Your party'), h('button', { class: 'btn', onclick: close }, 'Close')),
      h('div', { class: 'hero-cards' }, run.party.map(heroCard)),
    ));
    modal.hidden = false;
    modal.onclick = e => { if (e.target === modal) close(); };
  }
  function heroCard(p) {
    const st = heroStats(p);
    return h('div', { class: 'hero-card' },
      h('div', { class: 'card-head' }, sprImg(p.cls), h('div', { class: 'who' }, h('b', {}, p.name), bar(p.hp, st.maxHp, false), `${p.hp}/${st.maxHp} HP`)),
      h('div', { class: 'stats' }, `ATK ${st.atk} · MAG ${st.mag} · DEF ${st.def} · RES ${st.res} · SPD ${st.spd} · MOV ${st.mov} · CRIT ${st.crit}%`),
      h('div', { class: 'skill-list' }, p.skills.map(s => {
        const o = skStats(p, s);
        return h('div', {}, h('b', {}, o.name), ' ', h('span', { class: 'lv' }, `Lv${s.lv}`), h('br'), h('span', {}, `${describe(o)}. ${o.txt || ''}`));
      })),
      h('h3', { style: 'margin-top:10px' }, 'Items'),
      p.items.length ? h('ul', {}, p.items.map(id => h('li', {}, `${ITEMS[id].name}: ${ITEMS[id].txt}`))) : h('div', { class: 'muted' }, 'None'),
    );
  }
  function bar(v, max, foe) {
    return h('div', { class: 'bar' + (foe ? ' foe' : '') }, h('i', { style: `width:${Math.max(0, Math.round(100 * v / max))}%` }));
  }

  // Upgrades, items and rewards
  function upgradeOptions(n, onlyHero) {
    const all = [];
    run.party.forEach((p, hi) => {
      if (onlyHero != null && hi !== onlyHero) return;
      p.skills.forEach((s, si) => { if (s.lv < 4) all.push({ hi, si }); });
    });
    return shuffle(all).slice(0, n);
  }
  function upgradeCard(u, extra, onpick, disabled) {
    const p = run.party[u.hi], s = p.skills[u.si], d = SKILLS[s.id];
    if (s.lv >= 4) return h('button', { class: 'pick', disabled: true }, h('b', {}, `${d.name} is maxed`));
    const next = skStats(p, { id: s.id, lv: s.lv + 1 });
    return h('button', { class: 'pick', disabled, onclick: onpick },
      h('div', { class: 'pick-head' }, sprImg(p.cls), h('b', {}, `${d.name} to Lv${s.lv + 1}`), extra),
      h('div', { class: 'new' }, d.ups[s.lv - 1].note),
      h('div', { class: 'desc' }, describe(next)));
  }
  function applyUpgrade(u) { run.party[u.hi].skills[u.si].lv++; }
  const ownedItems = () => new Set(run.party.flatMap(p => p.items));
  function itemPool(n) {
    const owned = ownedItems();
    return shuffle(Object.keys(ITEMS).filter(id => !(ITEMS[id].unique && owned.has(id)))).slice(0, n);
  }
  function itemCard(id, extra, onpick, disabled) {
    const it = ITEMS[id];
    return h('button', { class: 'pick', disabled, onclick: onpick },
      h('div', { class: 'pick-head' }, h('b', {}, it.name), extra),
      h('div', { class: 'desc' }, it.txt));
  }
  function giveItem(id, next) {
    const it = ITEMS[id];
    const choose = p => {
      p.items.push(id);
      if (it.stats && it.stats.maxHp) p.hp += it.stats.maxHp;
      next();
    };
    hud();
    setScreen(h('div', { class: 'panel' },
      h('h2', {}, `Who carries the ${it.name}?`),
      h('p', { class: 'muted' }, it.txt),
      h('div', { class: 'cards' }, run.party.map(p => h('button', { class: 'pick', onclick: () => choose(p) },
        h('div', { class: 'pick-head' }, sprImg(p.cls), h('b', {}, p.name)),
        h('div', { class: 'desc' }, p.items.length ? p.items.map(i => ITEMS[i].name).join(', ') : 'No items yet')))),
    ));
    auto(() => choose(pick(run.party)));
  }

  function showRewards(info) {
    run.gold += info.gold;
    hud();
    const done = () => {
      if (!info.elite) { showMap(); return; }
      const opts = itemPool(3);
      setScreen(h('div', { class: 'panel' },
        h('h2', {}, 'The elite dropped treasure'),
        h('p', {}, 'Take one item.'),
        h('div', { class: 'cards' }, opts.map(id => itemCard(id, null, () => giveItem(id, showMap)))),
        h('button', { class: 'btn', onclick: showMap }, 'Leave it'),
      ));
      auto(() => giveItem(opts[0], showMap));
    };
    const opts = upgradeOptions(3);
    setScreen(h('div', { class: 'panel' },
      h('h2', {}, 'Victory!'),
      h('p', {}, `+${info.gold} gold. Every hero gains 4 max HP and 1 ATK or MAG.`),
      opts.length ? h('h3', {}, 'Choose a skill upgrade') : null,
      h('div', { class: 'cards' }, opts.map(u => upgradeCard(u, null, () => { applyUpgrade(u); done(); }))),
      h('button', { class: 'btn', onclick: done }, opts.length ? 'Skip' : 'Continue'),
    ));
    auto(() => { if (opts.length) applyUpgrade(opts[0]); done(); });
  }

  // Events
  const hurtAll = n => run.party.forEach(p => { p.hp = Math.max(1, p.hp - n); });
  const healAll = f => run.party.forEach(p => { const m = heroStats(p).maxHp; p.hp = Math.min(m, p.hp + Math.round(m * f)); });
  const EVENTS = [
    { title: 'Forgotten Shrine', text: 'A mossy altar hums with old power. Coins glint in its offering bowl.', choices: () => [
      { label: 'Pray', note: 'Upgrade a random skill', go: () => {
        const u = upgradeOptions(1)[0];
        if (!u) return 'The altar stays silent.';
        applyUpgrade(u);
        const p = run.party[u.hi], s = p.skills[u.si];
        return `A warm light settles on the ${p.name}. ${SKILLS[s.id].name} rises to Lv${s.lv}.`;
      } },
      { label: 'Take the offerings', note: '+70 gold; every hero takes 7 damage', go: () => { run.gold += 70; hurtAll(7); return 'The coins are cold. Something in the dark resents you.'; } },
      { label: 'Leave', go: () => 'You leave the shrine in peace.' },
    ] },
    { title: 'Wounded Sellsword', text: 'A bleeding mercenary sits against a tree. "Spare some coin for a healer? I\'ll pay you back in kind."', choices: () => [
      { label: 'Give 30 gold', cond: run.gold >= 30, go: () => { run.gold -= 30; return { text: 'She presses something into your hand and limps off toward town.', item: itemPool(1)[0] }; } },
      { label: 'Walk on', go: () => 'Her curses follow you up the road.' },
    ] },
    { title: 'Healing Spring', text: 'Clear water bubbles up between mossy stones.', choices: () => [
      { label: 'Drink deeply', note: 'Heal 50% of max HP', go: () => { healAll(0.5); return 'The water tastes of mint and starlight.'; } },
      { label: 'Bathe slowly', note: '+5 max HP for every hero', go: () => { run.party.forEach(p => { p.maxHp += 5; p.hp += 5; }); return 'You leave feeling sturdier.'; } },
    ] },
    { title: 'Locked Chest', text: 'An iron-bound chest sits alone in a clearing. Too alone.', choices: () => [
      { label: 'Pry it open', note: 'Treasure... probably', go: () => chance(0.65)
        ? { text: 'Inside, wrapped in oilcloth, is something useful.', item: itemPool(1)[0] }
        : { text: 'The chest was bait. Figures step out of the trees!', battle: true } },
      { label: 'Leave it', go: () => 'Some things are better left shut.' },
    ] },
    { title: 'Old Swordmaster', text: 'A grizzled master offers a lesson to one of you, if they can take a beating.', choices: () => [
      ...run.party.map((p, hi) => ({ label: `Train the ${p.name}`, note: '−10 HP, upgrade one of their skills', cond: p.skills.some(s => s.lv < 4),
        go: () => { p.hp = Math.max(1, p.hp - 10); return { text: `The ${p.name} limps back, bruised and wiser.`, upgradeHero: hi }; } })),
      { label: 'Decline', go: () => 'He shrugs and goes back to his tea.' },
    ] },
    { title: 'Card Sharp', text: 'A hooded figure shuffles a worn deck. "Double or nothing, friends?"', choices: () => [
      { label: 'Bet 40 gold', cond: run.gold >= 40, go: () => {
        if (chance(0.5)) { run.gold += 40; return 'You win! +40 gold.'; }
        run.gold -= 40; return 'The cards turn against you. −40 gold.';
      } },
      { label: 'Decline', go: () => 'The figure chuckles and vanishes into the fog.' },
    ] },
    { title: 'Grinning Idol', text: 'A stone idol grins from a ruined plinth, offering power for a price.', choices: () => [
      { label: 'Accept its gift', note: 'Every hero: +2 ATK, +2 MAG, −6 max HP', go: () => {
        run.party.forEach(p => { p.atk += 2; p.mag += 2; p.maxHp = Math.max(10, p.maxHp - 6); p.hp = Math.min(p.hp, heroStats(p).maxHp); });
        return 'Power floods in. Something else drains out.';
      } },
      { label: 'Smash it', note: '+30 gold', go: () => { run.gold += 30; return 'Gems tumble from its broken eyes. +30 gold.'; } },
    ] },
    { title: 'Abandoned Camp', text: 'A cold campfire, bedrolls, and a dropped pack.', choices: () => [
      { label: 'Rest by the ashes', note: 'Heal 30% of max HP', go: () => { healAll(0.3); return 'You sleep, lightly, and wake rested.'; } },
      { label: 'Search the pack', note: 'Find gold', go: () => { const g = rnd(40, 80); run.gold += g; return `A purse! +${g} gold.`; } },
    ] },
    { title: 'Fairy Ring', text: 'Mushrooms circle a patch of glowing grass. Bells chime from nowhere.', choices: () => [
      ...run.party.map(p => ({ label: `Send in the ${p.name}`, note: '+1 MOV or +3 SPD', go: () => {
        if (chance(0.5)) { p.mov += 1; return `The ${p.name} feels light on their feet. +1 MOV.`; }
        p.spd += 3; return `The ${p.name} moves in a blur. +3 SPD.`;
      } })),
      { label: 'Leave', go: () => 'The bells fall silent behind you.' },
    ] },
    { title: 'Wandering Alchemist', text: 'A soot-stained alchemist waves a bubbling flask. "Free sample! Mostly safe!"', choices: () => [
      { label: 'Buy a tonic', note: '25 gold: heal 40%', cond: run.gold >= 25, go: () => { run.gold -= 25; healAll(0.4); return 'It tastes awful and works wonders.'; } },
      { label: 'Try the sample', note: 'A random hero... reacts', go: () => {
        const p = pick(run.party);
        if (chance(0.55)) { p.def += 2; p.res += 2; return `The ${p.name}'s skin hardens like bark. +2 DEF and RES.`; }
        p.hp = Math.max(1, p.hp - 10); return `The ${p.name} turns green and loses 10 HP.`;
      } },
      { label: 'Decline', go: () => '"Your loss!"' },
    ] },
    { title: 'Ambush!', text: 'Arrows thud into the road ahead. You are surrounded.', choices: () => [
      { label: 'Fight!', go: () => ({ text: 'Weapons out!', battle: true }) },
    ] },
  ];

  function showEvent() {
    hud();
    let pool = EVENTS.filter(e => !run.seen.includes(e.title));
    if (!pool.length) { run.seen = []; pool = EVENTS; }
    const ev = pick(pool);
    run.seen.push(ev.title);
    const choices = ev.choices();
    const choose = c => {
      let res = c.go();
      if (typeof res === 'string') res = { text: res };
      hud();
      const next = () => {
        if (res.battle) startBattle('normal');
        else if (res.item) giveItem(res.item, showMap);
        else if (res.upgradeHero != null) showUpgradePick(upgradeOptions(3, res.upgradeHero), showMap);
        else showMap();
      };
      setScreen(h('div', { class: 'panel' }, h('h2', {}, ev.title), h('p', {}, res.text),
        h('button', { class: 'btn go', onclick: next }, 'Continue')));
      auto(next);
    };
    setScreen(h('div', { class: 'panel' },
      h('h2', {}, ev.title),
      h('p', {}, ev.text),
      h('div', {}, choices.map(c => h('button', { class: 'btn', disabled: c.cond === false, onclick: () => choose(c) }, c.label, c.note ? h('small', {}, c.note) : null))),
    ));
    auto(() => choose(choices.find(c => c.cond !== false)));
  }
  function showUpgradePick(opts, next) {
    if (!opts.length) { next(); return; }
    setScreen(h('div', { class: 'panel' },
      h('h2', {}, 'Choose an upgrade'),
      h('div', { class: 'cards' }, opts.map(u => upgradeCard(u, null, () => { applyUpgrade(u); next(); })))));
    auto(() => { applyUpgrade(opts[0]); next(); });
  }

  // Shop
  const upgradePrice = u => 35 + 25 * run.party[u.hi].skills[u.si].lv;
  function showShop(n) {
    n.shop ||= { items: itemPool(4).map(id => ({ id, price: ITEMS[id].price + rnd(-5, 10), sold: false })), ups: upgradeOptions(3).map(u => ({ ...u, sold: false })), inn: false };
    const shop = n.shop;
    hud();
    const again = () => showShop(n);
    const innCost = 30;
    setScreen(h('div', {},
      h('div', { class: 'panel' },
        h('h2', {}, 'Shop'),
        h('p', {}, 'A merchant has set up a stall under a patched awning. "Gear, lessons, a warm bed: all for coin."'),
        h('h3', {}, 'Wares'),
        h('div', { class: 'cards' }, shop.items.map(it => itemCard(it.id, h('span', { class: 'price' }, it.sold ? 'Sold' : `${it.price}g`), () => {
          run.gold -= it.price; it.sold = true; giveItem(it.id, again);
        }, it.sold || run.gold < it.price))),
        h('h3', {}, 'Training'),
        h('div', { class: 'cards' }, shop.ups.map(u => {
          const lv = run.party[u.hi].skills[u.si].lv, price = upgradePrice(u);
          return upgradeCard(u, h('span', { class: 'price' }, u.sold ? 'Done' : `${price}g`), () => {
            run.gold -= price; u.sold = true; applyUpgrade(u); again();
          }, u.sold || lv >= 4 || run.gold < price);
        })),
        h('h3', {}, 'Inn'),
        h('button', { class: 'btn', disabled: shop.inn || run.gold < innCost, onclick: () => { run.gold -= innCost; shop.inn = true; healAll(0.4); again(); } },
          shop.inn ? 'Rested' : `Rest: heal 40% (${innCost}g)`),
      ),
      h('button', { class: 'btn big go', onclick: showMap }, 'Leave shop'),
    ));
    auto(() => {
      const it = shop.items.find(i => !i.sold && run.gold >= i.price);
      if (it) { run.gold -= it.price; it.sold = true; giveItem(it.id, again); return; }
      const u = shop.ups.find(x => !x.sold && run.party[x.hi].skills[x.si].lv < 4 && run.gold >= upgradePrice(x));
      if (u) { run.gold -= upgradePrice(u); u.sold = true; applyUpgrade(u); again(); return; }
      if (!shop.inn && run.gold >= innCost) { run.gold -= innCost; shop.inn = true; healAll(0.4); }
      showMap();
    });
  }

  function gameOver() {
    const floor = run.pos ? floorOf(run.map[run.pos]) : 0;
    const stats = { ...run.stats, floor };
    clearSave();
    hud();
    setScreen(h('div', { class: 'panel center' },
      h('div', { class: 'title-name' }, 'Defeat'),
      h('div', { class: 'title-art' }, sprImg('lich', true)),
      h('p', {}, `Your party fell on floor ${floor}. Battles won: ${run.stats.battles}. Foes slain: ${run.stats.kills}.`),
      h('button', { class: 'btn big go', onclick: newRun }, 'Try again'),
      h('button', { class: 'btn big', onclick: showTitle }, 'Title'),
    ));
    if (AUTO) { window.__result = { win: false, ...stats }; }
  }
  function victory() {
    clearSave();
    hud();
    setScreen(h('div', { class: 'panel center' },
      h('div', { class: 'title-name' }, 'Victory!'),
      h('div', { class: 'title-art' }, sprImg('warrior'), sprImg('mage'), sprImg('rogue')),
      h('p', {}, `The Hollow King crumbles to dust. Battles won: ${run.stats.battles}. Foes slain: ${run.stats.kills}.`),
      h('button', { class: 'btn big go', onclick: newRun }, 'New run'),
    ));
    if (AUTO) { window.__result = { win: true, floor: MAP_ROWS + 1, ...run.stats }; }
  }

  // ---------- battle ----------
  let B = null;
  let uid = 0;

  function heroUnit(p) {
    const st = heroStats(p);
    return { id: ++uid, side: 'hero', spr: p.cls, name: p.name, ref: p, hp: Math.min(p.hp, st.maxHp), ...st, flank: CLASSES[p.cls].flank || 1.25,
      items: p.items, skills: p.skills.map(s => ({ id: s.id, lv: s.lv, cd: 0 })), st: {}, ct: rnd(0, 30) };
  }
  function foeUnit(kind, f) {
    const d = FOES[kind];
    const hm = 1 + 0.07 * (f - 1), sm = 1 + 0.05 * (f - 1), dp = Math.floor((f - 1) / 5);
    const hp = Math.round(d.hp * hm);
    return { id: ++uid, side: 'foe', kind, spr: kind, name: d.name, hp, maxHp: hp, atk: Math.round(d.atk * sm), mag: Math.round((d.mag || 0) * sm),
      def: d.def + dp, res: d.res + dp, spd: d.spd, mov: d.mov, fly: !!d.fly, crit: 5, flank: 1.25, items: [], ai: d.ai || 'melee', boss: !!d.boss,
      skills: d.skills.map(id => ({ id, lv: 1, cd: id === 'e_raise' ? 1 : 0 })), st: {}, ct: rnd(0, 30) };
  }

  function genGrid() {
    for (let tries = 0; tries < 200; tries++) {
      const g = Array.from({ length: GH }, () => Array(GW).fill(0));
      const mid = (x, y) => x >= 2 && x < GW - 3 && inb(x, y);
      for (let i = rnd(2, 4); i > 0; i--) {
        const cx = rnd(1, GW - 2), cy = rnd(0, GH - 1);
        for (const [dx, dy] of [[0, 0], ...DIRS, [1, 1], [-1, -1]]) if (inb(cx + dx, cy + dy) && chance(0.6)) g[cy + dy][cx + dx] = 1;
      }
      for (let i = rnd(2, 5); i > 0; i--) { const x = rnd(2, GW - 4), y = rnd(0, GH - 1); g[y][x] = 2; }
      if (chance(0.55)) {
        let x = rnd(3, GW - 5), y = rnd(1, GH - 2);
        for (let i = rnd(2, 4); i > 0; i--) { if (mid(x, y)) g[y][x] = 3; const [dx, dy] = pick(DIRS); x += dx; y += dy; }
      }
      // keep the deployment columns clear and check every open tile connects
      for (let y = 0; y < GH; y++) for (const x of [0, 1, GW - 3, GW - 2, GW - 1]) if (g[y][x] > 1) g[y][x] = 0;
      const open = [];
      for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) if (g[y][x] < 2) open.push(key(x, y));
      const seen = new Set([key(0, 0)]), q = [[0, 0]];
      while (q.length) {
        const [x, y] = q.pop();
        for (const [dx, dy] of DIRS) {
          const nx = x + dx, ny = y + dy, k = key(nx, ny);
          if (inb(nx, ny) && g[ny][nx] < 2 && !seen.has(k)) { seen.add(k); q.push([nx, ny]); }
        }
      }
      if (seen.size === open.length) return g;
    }
    return Array.from({ length: GH }, () => Array(GW).fill(0));
  }

  function startBattle(kind) {
    const node = run.map[run.pos];
    const f = node.id === 'boss' ? MAP_ROWS + 1 : floorOf(node);
    const tier = f <= 3 ? 1 : f <= 8 ? 2 : 3;
    const list = pick(kind === 'boss' ? ENCOUNTERS.boss : kind === 'elite' ? ENCOUNTERS[tier === 3 ? 'elite3' : 'elite2'] : ENCOUNTERS[tier]);
    const grid = genGrid();
    B = { kind, floor: f, grid, vari: grid.map(r => r.map(() => rnd(0, 3))), units: [], fx: [], log: [], mode: null, active: null };
    const heroRows = shuffle([...Array(GH).keys()]);
    run.party.forEach((p, i) => {
      const u = heroUnit(p);
      u.x = i === 0 ? 1 : 0; u.y = heroRows[i];
      if (u.hp <= 0) { u.hp = 0; u.dead = true; u.gone = true; }
      B.units.push(u);
    });
    const spots = shuffle([...Array(GH).keys()].flatMap(y => [GW - 1, GW - 2, GW - 3].map(x => ({ x, y }))))
      .sort((a, b) => a.x === GW - 3 ? 1 : b.x === GW - 3 ? -1 : 0);
    list.forEach((k, i) => {
      const u = foeUnit(k, f);
      const s = k === 'lich' ? { x: GW - 2, y: GH >> 1 } : spots.find(p => !B.units.some(o => o.x === p.x && o.y === p.y));
      u.x = s.x; u.y = s.y;
      B.units.push(u);
    });
    for (const u of B.units) { u.px = u.x; u.py = u.y; if (u.alpha == null) u.alpha = 1; }
    hud(true);
    setupBattleDom();
    log(kind === 'boss' ? 'The Hollow King rises from his throne!' : kind === 'elite' ? 'A powerful foe blocks the path!' : 'Enemies approach!');
    battleLoop(B);
  }

  function setupBattleDom() {
    const cv = h('canvas', { class: 'board', width: GW * TS, height: GH * TS });
    const side = h('div', { class: 'side' });
    setScreen(h('div', { class: 'battle' }, h('div', { class: 'boardwrap' }, cv), side));
    B.cv = cv; B.ctx = cv.getContext('2d'); B.side = side;
    const cell = e => {
      const r = cv.getBoundingClientRect();
      const x = Math.floor((e.clientX - r.left) / r.width * GW), y = Math.floor((e.clientY - r.top) / r.height * GH);
      return inb(x, y) ? { x, y } : null;
    };
    cv.addEventListener('pointermove', e => { if (e.pointerType === 'mouse') B.hover = cell(e); });
    cv.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse') B.hover = null; });
    cv.addEventListener('pointerup', e => onTap(cell(e), e.pointerType !== 'mouse'));
    drawFn = drawBattle;
  }

  const alive = () => B.units.filter(u => !u.dead);
  const unitAt = (x, y) => B.units.find(u => !u.dead && u.x === x && u.y === y);
  const spdOf = u => u.st.slow > 0 ? Math.max(1, Math.floor(u.spd / 2)) : u.spd;
  function log(s) { B.log.push(s); if (B.log.length > 30) B.log.shift(); }

  function moveCost(u, x, y) {
    if (u.fly) return 1;
    const t = B.grid[y][x];
    return t === 0 ? 1 : t === 1 ? 2 : Infinity;
  }
  function reach(u) {
    const res = new Map([[key(u.x, u.y), { x: u.x, y: u.y, c: 0, prev: null, stop: true }]]);
    const q = [[u.x, u.y, 0]];
    while (q.length) {
      q.sort((a, b) => a[2] - b[2]);
      const [x, y, c] = q.shift();
      if (c > res.get(key(x, y)).c) continue;
      for (const [dx, dy] of DIRS) {
        const nx = x + dx, ny = y + dy;
        if (!inb(nx, ny)) continue;
        const o = unitAt(nx, ny);
        if (o && o.side !== u.side && !u.fly) continue;
        const nc = c + moveCost(u, nx, ny);
        if (nc > u.mov) continue;
        const k = key(nx, ny), ex = res.get(k);
        if (!ex || nc < ex.c) { res.set(k, { x: nx, y: ny, c: nc, prev: key(x, y), stop: !o }); q.push([nx, ny, nc]); }
      }
    }
    return res;
  }
  function pathTo(res, k) {
    const out = [];
    for (let v = res.get(k); v; v = v.prev ? res.get(v.prev) : null) out.unshift({ x: v.x, y: v.y });
    return out;
  }
  function inArea(cx, cy, x, y, r, diag) {
    const dx = Math.abs(cx - x), dy = Math.abs(cy - y);
    return diag ? Math.max(dx, dy) <= r : dx + dy <= r;
  }
  function validTarget(u, o, x, y) {
    if (!inb(x, y)) return false;
    const d = Math.abs(u.x - x) + Math.abs(u.y - y);
    if (d < o.range[0] || d > o.range[1]) return false;
    const t = unitAt(x, y);
    if (o.tgt === 'foe') return !!t && t.side !== u.side;
    if (o.tgt === 'ally') return !!t && t.side === u.side;
    if (o.tgt === 'self') return x === u.x && y === u.y;
    return true;
  }
  function affected(u, o, x, y) {
    if (o.kind === 'summon') return [];
    if (!o.aoe) { const t = unitAt(x, y); return t ? [t] : []; }
    return alive().filter(t => inArea(x, y, t.x, t.y, o.aoe, o.diag) &&
      (o.hits === 'all' || (o.hits === 'allies' ? t.side === u.side : t.side !== u.side)));
  }
  const adjacent = (a, b) => dist(a, b) === 1;
  function flanked(a, t) {
    return B.units.some(o => !o.dead && o !== a && o.side === a.side && adjacent(o, t));
  }
  function calcDmg(a, t, o) {
    const magic = o.kind === 'mag';
    let v = (magic ? a.mag : a.atk) * o.pow * 12 / (12 + (magic ? t.res : t.def));
    if (t.side !== a.side && flanked(a, t)) v *= a.flank;
    if (B.grid[t.y][t.x] === 1 && !t.fly) v *= 0.8;
    if (t.st.guard) v *= 0.6;
    if (o.execute && t.hp * 2 < t.maxHp) v *= 2;
    if (has(a, 'axe') && t.hp * 2 < t.maxHp) v *= 1.4;
    if (has(a, 'focus') && o.cd >= 2) v *= 1.3;
    return Math.max(1, v);
  }
  function rollDmg(a, t, o) {
    let v = calcDmg(a, t, o) * (0.9 + Math.random() * 0.2);
    const crit = Math.random() * 100 < a.crit;
    if (crit) v *= 1.5;
    return { dmg: Math.max(1, Math.round(v)), crit };
  }

  // effects
  function fxText(t, text, color) {
    B.fx.push({ kind: 'text', x: t.px, y: t.py, text, color, t0: performance.now(), dur: 900 });
  }
  function hit(t, dmg, crit) {
    if (t.dead) return;
    t.hp = Math.max(0, t.hp - dmg);
    t.flashUntil = performance.now() + 160;
    fxText(t, (crit ? 'CRIT ' : '') + dmg, crit ? '#ffd23f' : '#ffffff');
    if (t.hp <= 0) kill(t);
  }
  function kill(t) {
    t.dead = true;
    t.st = {};
    log(`${t.name} falls.`);
    if (t.side === 'foe') run.stats.kills++;
    tween(450, p => { t.alpha = 1 - p; }).then(() => { t.gone = true; });
  }
  function heal(t, n) {
    if (t.dead) return 0;
    const a = Math.max(0, Math.min(n, t.maxHp - t.hp));
    t.hp += a;
    if (a > 0) fxText(t, '+' + a, '#7dff8a');
    return a;
  }
  function lunge(u, x, y) {
    const dx = Math.sign(x - u.x) * 0.35, dy = Math.sign(y - u.y) * 0.35;
    return tween(180, p => { const k = p < 0.5 ? p * 2 : (1 - p) * 2; u.px = u.x + dx * k; u.py = u.y + dy * k; });
  }
  function projectile(u, x, y, color) {
    const fx = { kind: 'proj', x0: u.x, y0: u.y, x1: x, y1: y, p: 0, color };
    B.fx.push(fx);
    return tween(60 * (Math.abs(u.x - x) + Math.abs(u.y - y)) + 80, p => { fx.p = p; }).then(() => { fx.done = true; });
  }
  function areaFlash(o, x, y, color) {
    const tiles = [];
    for (let ty = 0; ty < GH; ty++) for (let tx = 0; tx < GW; tx++) if (inArea(x, y, tx, ty, o.aoe, o.diag)) tiles.push([tx, ty]);
    B.fx.push({ kind: 'area', tiles, color, t0: performance.now(), dur: 380 });
  }
  async function moveUnit(u, path) {
    for (let i = 1; i < path.length; i++) {
      const a = path[i - 1], b = path[i];
      await tween(95, p => { u.px = a.x + (b.x - a.x) * p; u.py = a.y + (b.y - a.y) * p; });
    }
    const end = path[path.length - 1];
    u.x = u.px = end.x; u.y = u.py = end.y;
    u.moved = true;
  }
  async function knock(u, t) {
    let dx = Math.sign(t.x - u.x), dy = Math.sign(t.y - u.y);
    if (dx && dy) { if (Math.abs(t.x - u.x) >= Math.abs(t.y - u.y)) dy = 0; else dx = 0; }
    if (!dx && !dy) return;
    const nx = t.x + dx, ny = t.y + dy;
    if (inb(nx, ny) && moveCost(t, nx, ny) < Infinity && !unitAt(nx, ny)) {
      const sx = t.x, sy = t.y;
      t.x = nx; t.y = ny;
      await tween(120, p => { t.px = sx + dx * p; t.py = sy + dy * p; });
    } else {
      hit(t, Math.max(1, Math.round(u.atk * 0.3)), false);
      log(`${t.name} slams into an obstacle.`);
    }
  }
  function applyStatus(u, t, o) {
    if (o.stun && !t.boss) t.st.stun = 1;
    if (o.slow) t.st.slow = Math.max(t.st.slow || 0, o.slow);
    if (o.poison) { t.st.poison = o.poison; t.st.poisonDmg = Math.max(t.st.poisonDmg || 0, Math.max(1, Math.round(u.atk * o.poisonPow))); }
    if (o.burn) { t.st.burn = o.burn; t.st.burnDmg = Math.max(t.st.burnDmg || 0, Math.max(1, Math.round(u.mag * 0.3))); }
    if (o.taunt && t.side !== u.side) { t.st.taunt = o.taunt; t.st.tauntBy = u; }
    if (o.kind === 'phys' && has(u, 'venom')) { t.st.poison = Math.max(t.st.poison || 0, 2); t.st.poisonDmg = Math.max(t.st.poisonDmg || 0, Math.max(1, Math.round(u.atk * 0.25))); }
    if (o.kind === 'mag' && has(u, 'ember')) { t.st.burn = Math.max(t.st.burn || 0, 2); t.st.burnDmg = Math.max(t.st.burnDmg || 0, Math.max(1, Math.round(u.mag * 0.25))); }
  }
  function summon(u) {
    const spots = [];
    for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
      const d = Math.abs(x - u.x) + Math.abs(y - u.y);
      if (d > 0 && d <= 3 && B.grid[y][x] < 2 && !unitAt(x, y)) spots.push({ x, y, d });
    }
    spots.sort((a, b) => a.d - b.d || Math.random() - 0.5);
    for (const s of spots.slice(0, 2)) {
      const sk = foeUnit('skeleton', B.floor);
      Object.assign(sk, { x: s.x, y: s.y, px: s.x, py: s.y, ct: 0, alpha: 0, summoned: true });
      B.units.push(sk);
      tween(400, p => { sk.alpha = p; });
    }
    log(`${u.name} raises the dead!`);
  }

  async function useSkill(u, s, tx, ty) {
    const o = skStats(u, s);
    s.cd = o.cd;
    u.acted = true;
    B.mode = null; B.pending = null;
    renderPanel();
    log(`${u.name}: ${o.name}`);
    fxText(u, o.name, '#c9b8ff');
    const targets = affected(u, o, tx, ty);
    const ranged = o.tgt !== 'self' && Math.abs(u.x - tx) + Math.abs(u.y - ty) > 1;
    const color = o.kind === 'heal' ? '#7dff8a' : o.burn || o.id === 'fireball' ? '#ff8a3d' : o.kind === 'mag' ? '#9fd8ff' : '#e8e8e8';
    if (ranged) await projectile(u, tx, ty, color);
    else if (o.tgt !== 'self' && !(tx === u.x && ty === u.y)) await lunge(u, tx, ty);
    else await sleep(200);
    if (o.aoe) areaFlash(o, tx, ty, o.kind === 'heal' ? 'rgba(120,255,140,0.5)' : o.kind === 'buff' ? 'rgba(255,90,90,0.35)' : 'rgba(255,170,60,0.55)');
    let killed = false;
    for (const t of targets) {
      if (o.kind === 'heal') {
        heal(t, Math.round(u.mag * o.pow));
        if (o.cleanse) { t.st.poison = 0; t.st.burn = 0; }
        continue;
      }
      if (o.kind === 'buff') { applyStatus(u, t, o); continue; }
      for (let i = 0; i < (o.double ? 2 : 1) && !t.dead; i++) {
        const r = rollDmg(u, t, o);
        hit(t, r.dmg, r.crit);
        if (o.drain) heal(u, Math.round(r.dmg * o.drain));
        else if (has(u, 'fang')) heal(u, Math.round(r.dmg * 0.2));
        if (has(t, 'thorns') && adjacent(u, t) && !u.dead) hit(u, Math.max(1, Math.round(r.dmg * 0.3)), false);
        if (i === 0 && o.double) await sleep(150);
      }
      if (t.dead) killed = true;
      else {
        applyStatus(u, t, o);
        if (o.knock) await knock(u, t);
      }
      await sleep(60);
    }
    if (o.guard) u.st.guard = 1;
    if (o.selfHeal) heal(u, Math.round(u.maxHp * o.selfHeal));
    if (o.kind === 'summon') summon(u);
    if (o.resetOnKill && killed && !u.dead) { s.cd = 0; u.moved = false; fxText(u, 'Again!', '#ffd23f'); }
    await sleep(380);
    checkEnd();
  }

  function nextActor() {
    for (let guard = 0; guard < 10000; guard++) {
      const ready = alive().filter(u => u.ct >= 100);
      if (ready.length) return ready.sort((a, b) => b.ct - a.ct || spdOf(b) - spdOf(a))[0];
      for (const u of alive()) u.ct += spdOf(u);
    }
    return alive()[0];
  }
  function predictOrder(n) {
    const sim = alive().map(u => ({ u, ct: u.ct, spd: spdOf(u) }));
    const out = [];
    if (B.active && !B.active.dead) {
      out.push(B.active);
      const a = sim.find(x => x.u === B.active);
      if (a) a.ct -= 100;
    }
    for (let guard = 0; out.length < n && guard < 5000; guard++) {
      const ready = sim.filter(x => x.ct >= 100);
      if (ready.length) {
        ready.sort((a, b) => b.ct - a.ct || b.spd - a.spd);
        out.push(ready[0].u);
        ready[0].ct -= 100;
      } else sim.forEach(x => { x.ct += x.spd; });
    }
    return out;
  }

  function checkEnd() {
    if (B.over) return true;
    const heroes = B.units.some(u => u.side === 'hero' && !u.dead), foes = B.units.some(u => u.side === 'foe' && !u.dead);
    if (heroes && foes) return false;
    B.over = true;
    if (B.resolveTurn) { const r = B.resolveTurn; B.resolveTurn = null; r(); }
    const b = B;
    sleep(900).then(() => endBattle(b, heroes));
    return true;
  }

  async function battleLoop(b) {
    while (!b.over) {
      const u = nextActor();
      b.active = u; b.inspect = null; b.startPos = null;
      u.moved = false; u.acted = false;
      renderPanel();
      const skip = await startTurn(u);
      if (checkEnd()) return;
      if (!skip) {
        if (u.side === 'hero' && !AUTO) await playerTurn(u);
        else await aiTurn(u);
      }
      if (b.over) return;
      endTurn(u);
    }
  }
  async function startTurn(u) {
    for (const s of u.skills) if (s.cd > 0) s.cd--;
    u.st.guard = 0;
    if (has(u, 'charm')) heal(u, Math.max(1, Math.round(u.maxHp * 0.08)));
    if (u.st.poison > 0) { hit(u, u.st.poisonDmg, false); log(`${u.name} suffers from poison.`); await sleep(350); }
    if (!u.dead && u.st.burn > 0) { hit(u, u.st.burnDmg, false); log(`${u.name} burns.`); await sleep(350); }
    if (u.dead) return true;
    if (u.st.stun) {
      u.st.stun = 0;
      fxText(u, 'Stunned', '#ffd23f');
      log(`${u.name} is stunned.`);
      await sleep(550);
      return true;
    }
    return false;
  }
  function endTurn(u) {
    if (u.dead) return;
    u.ct -= 100 - (u.moved ? 0 : 20) - (u.acted ? 0 : 20);
    for (const k of ['poison', 'burn', 'slow', 'taunt']) if (u.st[k] > 0) u.st[k]--;
    if (!u.st.taunt) u.st.tauntBy = null;
  }

  function playerTurn(u) {
    return new Promise(res => {
      B.resolveTurn = res;
      B.mode = 'move';
      B.reach = reach(u);
      B.sel = null; B.pending = null;
      renderPanel();
    });
  }
  function finishTurn() {
    if (!B || !B.resolveTurn || B.busy) return;
    const r = B.resolveTurn;
    B.resolveTurn = null; B.mode = null; B.pending = null;
    r();
  }
  function afterHeroStep(u) {
    if (B.over) return;
    if (u.moved && u.acted) { finishTurn(); return; }
    B.mode = u.moved ? null : 'move';
    if (B.mode) B.reach = reach(u);
    B.sel = null; B.pending = null;
    renderPanel();
  }
  async function doMove(u, path) {
    B.busy = true;
    B.startPos = { x: u.x, y: u.y };
    B.mode = null;
    renderPanel();
    await moveUnit(u, path);
    B.busy = false;
    afterHeroStep(u);
  }
  function undoMove(u) {
    if (!B.startPos || u.acted || B.busy) return;
    u.x = u.px = B.startPos.x; u.y = u.py = B.startPos.y;
    u.moved = false; B.startPos = null;
    afterHeroStep(u);
  }
  async function doSkill(u, s, x, y) {
    B.busy = true;
    await useSkill(u, s, x, y);
    B.busy = false;
    B.startPos = null;
    afterHeroStep(u);
  }
  function selectSkill(i) {
    const u = B.active;
    if (B.mode === 'skill' && B.sel === i) { afterHeroStep(u); return; }
    const s = u.skills[i], o = skStats(u, s);
    B.mode = 'skill'; B.sel = i; B.selO = o;
    B.targets = new Set();
    for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) if (validTarget(u, o, x, y)) B.targets.add(key(x, y));
    B.pending = o.tgt === 'self' ? { x: u.x, y: u.y } : null;
    renderPanel();
  }
  function onTap(g, touch) {
    if (!B || B.busy || B.over || !g) return;
    const u = B.active;
    const mine = u && u.side === 'hero' && B.resolveTurn && !AUTO;
    const who = unitAt(g.x, g.y);
    if (mine && B.mode === 'move') {
      const v = B.reach.get(key(g.x, g.y));
      if (v && v.stop && !(g.x === u.x && g.y === u.y)) { doMove(u, pathTo(B.reach, key(g.x, g.y))); return; }
    }
    if (mine && B.mode === 'skill' && B.targets.has(key(g.x, g.y))) {
      if (touch && !(B.pending && B.pending.x === g.x && B.pending.y === g.y)) { B.pending = g; renderPanel(); return; }
      doSkill(u, u.skills[B.sel], g.x, g.y);
      return;
    }
    if (who) { B.inspect = who; renderPanel(); }
  }

  // AI: try every reachable tile, skill and target; take the best score, else close in.
  function scoreAction(u, o, tg) {
    if (o.kind === 'summon') return B.units.filter(t => t.summoned && !t.dead).length < 2 ? 20 : 0;
    let s = 0;
    for (const t of tg) {
      const foe = t.side !== u.side;
      if (o.kind === 'heal') {
        if (foe) continue;
        s += Math.min(t.maxHp - t.hp, u.mag * o.pow) * 1.2 + (o.cleanse && (t.st.poison || t.st.burn) ? 3 : 0);
        continue;
      }
      if (o.kind === 'buff') { if (foe) s += 4; continue; }
      let d = calcDmg(u, t, o) * (o.double ? 2 : 1);
      const kills = d >= t.hp;
      d = Math.min(d, t.hp);
      const extra = kills ? 25 : (o.stun && !t.boss ? 8 : 0) + (o.slow ? 3 : 0) + (o.poison ? o.poison * 2 : 0) + (o.burn ? 4 : 0);
      s += foe ? d + extra : -(d + extra) * 1.5;
    }
    return s;
  }
  function distField(u, targets) {
    const d = Array.from({ length: GH }, () => Array(GW).fill(Infinity));
    const q = [];
    for (const t of targets) { d[t.y][t.x] = 0; q.push([t.x, t.y, 0]); }
    while (q.length) {
      q.sort((a, b) => a[2] - b[2]);
      const [x, y, c] = q.shift();
      if (c > d[y][x]) continue;
      for (const [dx, dy] of DIRS) {
        const nx = x + dx, ny = y + dy;
        if (!inb(nx, ny)) continue;
        const nc = c + moveCost(u, nx, ny);
        if (nc < d[ny][nx]) { d[ny][nx] = nc; q.push([nx, ny, nc]); }
      }
    }
    return d;
  }
  function planAI(u) {
    const R = reach(u);
    const ox = u.x, oy = u.y;
    const hostile = alive().filter(t => t.side !== u.side);
    const taunter = u.st.taunt > 0 && u.st.tauntBy && !u.st.tauntBy.dead ? u.st.tauntBy : null;
    let best = null;
    for (const v of R.values()) {
      if (!v.stop) continue;
      u.x = v.x; u.y = v.y;
      let pos = (B.grid[v.y][v.x] === 1 && !u.fly ? 1 : 0) - v.c * 0.05;
      if (u.ai === 'ranged' || u.spr === 'mage') pos += Math.min(...hostile.map(t => dist(t, v))) >= 2 ? 3 : -2;
      for (const s of u.skills) {
        if (s.cd > 0) continue;
        const o = skStats(u, s);
        for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
          if (!validTarget(u, o, x, y)) continue;
          const tg = affected(u, o, x, y);
          if (taunter && (o.kind === 'phys' || o.kind === 'mag') && !tg.includes(taunter)) continue;
          const sc = scoreAction(u, o, tg);
          if (sc <= 0) continue;
          if (!best || sc + pos > best.score) best = { score: sc + pos, v, s, x, y };
        }
      }
    }
    u.x = ox; u.y = oy;
    if (best) return { path: pathTo(R, key(best.v.x, best.v.y)), skill: best.s, tx: best.x, ty: best.y };
    const df = distField(u, taunter ? [taunter] : hostile);
    let bv = null, bs = Infinity;
    for (const v of R.values()) {
      if (!v.stop) continue;
      const dd = df[v.y][v.x];
      const sc = (u.ai === 'ranged' ? Math.abs(dd - 3) : dd) - (B.grid[v.y][v.x] === 1 ? 0.3 : 0) + v.c * 0.01;
      if (sc < bs) { bs = sc; bv = v; }
    }
    return { path: bv ? pathTo(R, key(bv.x, bv.y)) : null };
  }
  async function aiTurn(u) {
    B.busy = true;
    renderPanel();
    await sleep(300);
    const plan = planAI(u);
    if (plan.path && plan.path.length > 1) await moveUnit(u, plan.path);
    if (plan.skill && !B.over) await useSkill(u, plan.skill, plan.tx, plan.ty);
    else await sleep(150);
    B.busy = false;
  }

  function endBattle(b, win) {
    if (B !== b) return;
    B = null;
    if (AUTO) (window.__log ||= []).push({ kind: b.kind, floor: b.floor, win, heroes: b.units.filter(u => u.side === 'hero').map(u => u.dead ? 0 : u.hp), foes: b.units.filter(u => u.side === 'foe' && !u.dead).map(u => `${u.name}:${u.hp}`).join(' ') });
    if (!win) { gameOver(); return; }
    for (const u of b.units) {
      if (u.side !== 'hero') continue;
      const p = u.ref, cls = CLASSES[p.cls];
      p.maxHp += 4;
      p[cls.main] += 1;
      const max = heroStats(p).maxHp;
      p.hp = u.dead ? Math.ceil(max * 0.25) : Math.min(max, u.hp + 3 + Math.round(max * 0.1));
    }
    run.stats.battles++;
    if (b.kind === 'boss') { victory(); return; }
    const gold = b.kind === 'elite' ? rnd(55, 70) + b.floor * 4 : rnd(20, 30) + b.floor * 3;
    showRewards({ gold, elite: b.kind === 'elite' });
  }

  // battle panel
  function statusText(u) {
    const st = u.st, out = [];
    if (st.stun) out.push('Stunned');
    if (st.poison > 0) out.push(`Poisoned (${st.poison})`);
    if (st.burn > 0) out.push(`Burning (${st.burn})`);
    if (st.slow > 0) out.push(`Slowed (${st.slow})`);
    if (st.taunt > 0) out.push(`Taunted (${st.taunt})`);
    if (st.guard) out.push('Guarding');
    if (B.grid[u.y][u.x] === 1 && !u.fly) out.push('In forest');
    return out.join(' · ');
  }
  function unitCard(u, withSkills) {
    return h('div', { class: 'card' },
      h('div', { class: 'card-head' }, sprImg(u.spr, u.side === 'foe'),
        h('div', { class: 'who' }, h('b', {}, u.name), bar(u.hp, u.maxHp, u.side === 'foe'), `${u.hp}/${u.maxHp} HP`)),
      h('div', { class: 'stats' }, `ATK ${u.atk} · MAG ${u.mag} · DEF ${u.def} · RES ${u.res} · SPD ${spdOf(u)} · MOV ${u.mov}${u.fly ? ' · Flying' : ''}`),
      h('div', { class: 'status' }, statusText(u)),
      withSkills ? h('div', { class: 'skill-list' }, u.skills.map(s => {
        const o = skStats(u, s);
        return h('div', {}, h('b', {}, o.name), s.cd > 0 ? h('span', {}, ` (ready in ${s.cd})`) : null, h('br'), h('span', {}, describe(o) + (o.txt ? '. ' + o.txt : '')));
      })) : null);
  }
  function hintText() {
    const u = B.active;
    if (B.mode === 'move') return 'Tap a blue tile to move, or choose an action.';
    if (B.mode === 'skill') {
      const o = B.selO;
      const what = `${o.name}: ${describe(o)}.${o.txt ? ' ' + o.txt : ''}`;
      if (!B.targets.size) return `${what} No targets in range.`;
      if (B.pending) return `${what} Tap again or press Confirm.`;
      return `${what} Tap a highlighted tile.`;
    }
    if (u.moved && u.acted) return '';
    return u.acted ? 'Move, or end your turn.' : 'Choose an action, or end your turn.';
  }
  function renderPanel() {
    if (!B || !B.side) return;
    const u = B.active;
    const mine = u && u.side === 'hero' && B.resolveTurn && !B.busy && !AUTO;
    const order = h('div', { class: 'order' }, h('span', { class: 'lbl' }, 'NEXT'),
      predictOrder(9).map((t, i) => h('img', { class: `spr ${t.side}${i === 0 ? ' now' : ''}`, src: sprURL(t.spr, t.side === 'foe'), title: t.name, alt: t.name })));
    const shown = B.inspect && !B.inspect.dead ? B.inspect : u;
    const kids = [order];
    if (shown) kids.push(unitCard(shown, !(mine && shown === u)));
    if (mine) {
      kids.push(h('div', { class: 'actions' },
        h('button', { class: 'btn' + (B.mode === 'move' ? ' sel' : ''), disabled: u.moved, onclick: () => {
          if (B.mode === 'move') { B.mode = null; renderPanel(); } else afterHeroStep(u);
        } }, 'Move'),
        u.moved && !u.acted && B.startPos ? h('button', { class: 'btn', onclick: () => undoMove(u) }, 'Undo move') : null,
        u.skills.map((s, i) => {
          const o = skStats(u, s);
          return h('button', { class: 'btn' + (B.mode === 'skill' && B.sel === i ? ' sel' : ''), disabled: u.acted || s.cd > 0, title: `${o.name}: ${describe(o)}`, onclick: () => selectSkill(i) },
            o.name, s.cd > 0 ? h('span', { class: 'cd' }, ` ${s.cd}`) : null);
        }),
        B.mode === 'skill' && B.pending ? h('button', { class: 'btn go', onclick: () => doSkill(u, u.skills[B.sel], B.pending.x, B.pending.y) }, 'Confirm') : null,
        h('button', { class: 'btn', onclick: finishTurn }, 'End turn'),
      ));
      kids.push(h('div', { class: 'hint' }, hintText()));
    } else {
      kids.push(h('div', { class: 'hint' }, u && !B.over ? `${u.name} is acting…` : ''));
    }
    kids.push(h('div', { class: 'log' }, B.log.slice(-5).map(l => h('div', {}, l))));
    B.side.replaceChildren(...kids);
  }

  // battle drawing
  function fillTile(c, x, y, color) { c.fillStyle = color; c.fillRect(x * TS, y * TS, TS, TS); }
  function outline(c, x, y, color, w) {
    c.strokeStyle = color; c.lineWidth = w;
    c.strokeRect(x * TS + w / 2, y * TS + w / 2, TS - w, TS - w);
  }
  function text(c, s, x, y, color, size) {
    c.font = `${size}px "Press Start 2P", monospace`;
    c.textAlign = 'center';
    c.lineWidth = 5; c.strokeStyle = '#000';
    c.strokeText(s, x, y);
    c.fillStyle = color;
    c.fillText(s, x, y);
  }
  function drawBattle(now) {
    if (!B || !B.ctx) return;
    const c = B.ctx;
    c.imageSmoothingEnabled = false;
    const wf = Math.floor(now / 450) % 3;
    for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
      const t = B.grid[y][x], v = B.vari[y][x];
      const img = t === 0 ? TILE.grass[v] : t === 1 ? TILE.forest[v % 2] : t === 2 ? TILE.rock[v % 2] : TILE.water[(wf + v) % 3];
      c.drawImage(img, x * TS, y * TS, TS, TS);
    }
    c.fillStyle = 'rgba(0,0,0,0.13)';
    for (let x = 1; x < GW; x++) c.fillRect(x * TS - 1, 0, 2, GH * TS);
    for (let y = 1; y < GH; y++) c.fillRect(0, y * TS - 1, GW * TS, 2);

    const u = B.active;
    const mine = u && u.side === 'hero' && B.resolveTurn && !AUTO;
    if (mine && B.mode === 'move' && B.reach && !B.busy) {
      for (const v of B.reach.values()) if (v.stop && !(v.x === u.x && v.y === u.y)) { fillTile(c, v.x, v.y, 'rgba(70,150,255,0.38)'); outline(c, v.x, v.y, 'rgba(150,200,255,0.6)', 2); }
    }
    let preview = null;
    if (mine && B.mode === 'skill') {
      const o = B.selO;
      for (const k of B.targets) { const [x, y] = k.split(',').map(Number); fillTile(c, x, y, o.kind === 'heal' ? 'rgba(80,220,120,0.32)' : 'rgba(255,70,70,0.3)'); }
      const p = B.hover && B.targets.has(key(B.hover.x, B.hover.y)) ? B.hover : B.pending;
      if (p) {
        if (o.aoe) { for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) if (inArea(p.x, p.y, x, y, o.aoe, o.diag)) fillTile(c, x, y, 'rgba(255,210,70,0.4)'); }
        else fillTile(c, p.x, p.y, 'rgba(255,210,70,0.45)');
        outline(c, p.x, p.y, '#ffe680', 4);
        preview = { o, list: affected(u, o, p.x, p.y) };
      }
    }
    if (B.hover && mine) outline(c, B.hover.x, B.hover.y, 'rgba(255,255,255,0.7)', 2);
    if (u && !u.dead && !B.over) {
      const pulse = Math.floor(now / 250) % 2 ? 4 : 2;
      c.fillStyle = '#ffe14d';
      const px = u.px * TS, py = u.py * TS, L = 14;
      for (const [cx, cy, sx, sy] of [[px, py, 1, 1], [px + TS, py, -1, 1], [px, py + TS, 1, -1], [px + TS, py + TS, -1, -1]]) {
        c.fillRect(cx - (sx < 0 ? L : 0), cy - (sy < 0 ? pulse : 0), L, pulse);
        c.fillRect(cx - (sx < 0 ? pulse : 0), cy - (sy < 0 ? L : 0), pulse, L);
      }
    }
    for (const fx of B.fx) if (fx.kind === 'area') {
      const p = (now - fx.t0) / fx.dur;
      if (p < 1) { c.globalAlpha = 1 - p; for (const [x, y] of fx.tiles) fillTile(c, x, y, fx.color); c.globalAlpha = 1; }
    }

    const units = B.units.filter(t => !t.gone).sort((a, b) => a.py - b.py);
    for (const t of units) {
      const px = t.px * TS, py = t.py * TS;
      c.globalAlpha = t.alpha ?? 1;
      c.fillStyle = 'rgba(0,0,0,0.3)';
      c.fillRect(px + 4 * S, py + 14 * S, 8 * S, 2 * S);
      const bob = (t === u && !t.dead) ? (Math.floor(now / 300) % 2) * S : 0;
      const fly = t.fly ? Math.round(Math.sin(now / 220 + t.id) * S) - 2 * S : 0;
      const spr = SPR[t.spr];
      const img = t.flashUntil > now ? (t.side === 'foe' ? spr.wf : spr.wn) : (t.side === 'foe' ? spr.f : spr.n);
      c.drawImage(img, px, py - bob + fly, TS, TS);
      if (!t.dead) {
        const bx = px + 2 * S, by = py + TS - 2 * S, bw = 12 * S;
        c.fillStyle = '#120b18'; c.fillRect(bx - 2, by - 2, bw + 4, S + 4);
        c.fillStyle = t.side === 'hero' ? '#74d65e' : '#e5574f';
        c.fillRect(bx, by, Math.round(bw * t.hp / t.maxHp), S);
        const pips = [];
        if (t.st.poison > 0) pips.push('#8be04e');
        if (t.st.burn > 0) pips.push('#ff8a3d');
        if (t.st.slow > 0) pips.push('#7fd8ff');
        if (t.st.stun) pips.push('#ffe14d');
        if (t.st.taunt > 0) pips.push('#ff4d4d');
        if (t.st.guard) pips.push('#d8d8e8');
        pips.forEach((col, i) => { c.fillStyle = '#000'; c.fillRect(px + 2 + i * 14, py + 2, 12, 12); c.fillStyle = col; c.fillRect(px + 4 + i * 14, py + 4, 8, 8); });
      }
      c.globalAlpha = 1;
    }
    if (preview) {
      for (const t of preview.list) {
        const o = preview.o;
        let label, col;
        if (o.kind === 'heal') { if (t.side !== u.side) continue; label = '+' + Math.min(t.maxHp - t.hp, Math.round(u.mag * o.pow)); col = '#7dff8a'; }
        else if (o.kind === 'buff') { if (t.side === u.side) continue; label = 'TAUNT'; col = '#ff8080'; }
        else {
          const d = Math.round(calcDmg(u, t, o) * (o.double ? 2 : 1));
          label = d >= t.hp ? 'KO' : '-' + d; col = t.side === u.side ? '#ff9a9a' : '#ffe14d';
        }
        text(c, label, t.px * TS + TS / 2, t.py * TS + 6 * S, col, 18);
      }
    }
    for (const fx of B.fx) {
      if (fx.kind === 'proj' && !fx.done) {
        const x = (fx.x0 + (fx.x1 - fx.x0) * fx.p) * TS + TS / 2, y = (fx.y0 + (fx.y1 - fx.y0) * fx.p) * TS + TS / 2 - Math.sin(fx.p * Math.PI) * 20;
        c.fillStyle = '#000'; c.fillRect(x - 3 * S, y - 3 * S, 6 * S, 6 * S);
        c.fillStyle = fx.color; c.fillRect(x - 2 * S, y - 2 * S, 4 * S, 4 * S);
        c.fillStyle = '#fff'; c.fillRect(x - S, y - S, S, S);
      } else if (fx.kind === 'text') {
        const p = (now - fx.t0) / fx.dur;
        if (p < 1) {
          c.globalAlpha = p < 0.7 ? 1 : (1 - p) / 0.3;
          text(c, fx.text, fx.x * TS + TS / 2, fx.y * TS + 4 * S - p * 28, fx.color, fx.text.length > 6 ? 14 : 20);
          c.globalAlpha = 1;
        }
      }
    }
    B.fx = B.fx.filter(fx => fx.kind === 'proj' ? !fx.done : now - fx.t0 < fx.dur);
  }

  if (AUTO) window.__tf = { get run() { return run; } };
  showTitle();
})();
