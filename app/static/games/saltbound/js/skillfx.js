// What every action and enemy move looks like in a fight, built from the effects kit combat.js
// passes in (`x`, made by fxKit there):
//   x.t: the targets; x.from: the actor; x.miss; x.party / x.foes: the standing units on each side
//   x.hit(cls, colour, ms, delay, glyph)   an effect on each target
//   x.on(id, ...)  / x.me(...)             the same on one unit / on the actor
//   x.shot(cls, colour, [impact cls, colour, ms], { arc, spin, delay, stagger, to, back })
//   x.back(...)                            a shot from each target back to the actor
//   x.bolt(from, to), x.screen(cls, ms, colour), x.shake(delay), x.quake(delay), x.move(id, cls, ms)
//   x.later(fn, ms)                        (all timings scale with the animation speed)
// A hero's entry returns how the hero moves: 'melee' (lunge), 'charge', 'spin', 'retreat', 'brace',
// 'cast' or 'act'. Effects take their colour as --c in the stylesheet (the "skill effects" section).

const C = {
  steel: '#e4ecf4', shield: '#8cc8ff', blood: '#ff5a4a', gold: '#ffd36b', holy: '#ffe9a0', heal: '#6ee59a',
  arcane: '#b48cff', shadow: '#8a63ff', poison: '#8ee04a', acid: '#c4f03a', fire: '#ffa030', nature: '#6fd36a',
  song: '#ff9ad5', smoke: 'rgba(170, 180, 190, 0.75)', silver: '#d8e4ee', water: '#7cc8ff', storm: '#bfe0ff', dark: '#5a3a8a',
};

// ------------------------------------------------------------------ hero actions
export const SKILL_FX = {
  // everyone
  block: x => { x.me('shieldfx', null, 700); x.me('hoop', C.shield, 500, 80); return 'brace'; },
  flee: x => { x.me('smoke', C.smoke, 800); return 'retreat'; },

  // armor's own actions (they take Block's place)
  hunker: x => { x.me('shieldfx', null, 700); x.me('slam', C.shield, 480, 60); return 'brace'; },
  patch_up: x => { x.me('shieldfx', null, 700); x.me('healglow', null, 900, 120); return 'brace'; },
  coral_growth: x => { x.me('shieldfx', null, 700); x.me('vines', '#ff8a7a', 800, 80); x.me('healglow', null, 900, 200); return 'brace'; },
  bristle: x => { x.me('dome thorny', null, 900); return 'brace'; },
  sidestep: x => { x.me('shieldfx', null, 600); x.me('smoke', C.smoke, 700, 100); return 'retreat'; },
  echo_shell: x => { x.me('shieldfx', null, 700); x.me('hoop', C.song, 600, 120); x.foes.forEach((u, i) => x.on(u, 'hoop', C.song, 500, 260 + i * 60)); return 'brace'; },
  cover: x => { x.t[0] === x.from ? x.me('shieldfx', null, 700) : x.shot('shieldorb', null, ['shieldfx', null, 700]); return 'brace'; },
  tidewall: x => { x.me('shieldfx', null, 700); x.party.forEach((u, i) => x.on(u, 'tidewall', C.water, 800, 100 + i * 70)); return 'brace'; },

  // Vanguard
  strike: x => { x.hit('slash', null, 420, 150); if (!x.miss) x.hit('pop small', C.steel, 400, 260); return 'melee'; },
  brace: x => { x.me('slam', C.shield, 520); x.me('shieldfx', null, 700, 120); return 'brace'; },
  shield_bash: x => { x.hit('slam', C.shield, 480, 150); if (!x.miss) { x.hit('star', null, 520, 260); x.shake(200); } return 'charge'; },
  retaliate: x => { x.me('shieldfx', null, 500); x.hit('bigslash', null, 520, 200); if (!x.miss) x.shake(260); return 'melee'; },
  shield_throw: x => {
    x.shot('disc', C.shield, ['slam', C.shield, 420], { spin: true });
    x.later(() => x.back('disc', C.shield, null, { spin: true }), 340);
    return 'act';
  },
  rallying_shout: x => { x.me('shout', C.gold, 800); x.party.forEach((u, i) => x.on(u, 'aura', C.gold, 900, 120 + i * 80)); x.screen('gold', 400); return 'brace'; },
  shoulder_charge: x => { x.me('shieldfx', null, 500); x.hit('slam', C.steel, 480, 220); if (!x.miss) { x.hit('star', null, 520, 300); x.shake(240); } return 'charge'; },

  // Arcanist
  bolt: x => { x.shot('orb', C.arcane, ['pop', C.arcane, 520]); return 'cast'; },
  channel: x => {
    x.me('gather', C.arcane, 520);
    x.later(() => { x.shot('orb big', C.arcane, ['pop big', C.arcane, 640]); if (!x.miss) x.later(() => x.screen('tint', 360, 'rgba(160, 110, 255, 0.25)'), 260); }, 320);
    return 'cast';
  },
  hex: x => { x.shot('orb small', C.shadow, ['rune', C.shadow, 1000]); return 'cast'; },
  siphon: x => {
    x.shot('orb', C.shadow, ['pop', C.shadow, 480]);
    if (!x.miss) x.later(() => x.back('drop', C.blood, ['healglow', null, 800], { stagger: 60 }), 320);
    return 'cast';
  },

  // Mender
  mend: x => { x.shot('orb', C.heal, ['healglow', null, 900]); x.hit('drops', C.heal, 900, 280); return 'cast'; },
  lift: x => { x.hit('beam', null, 700); x.hit('healglow big', null, 1000, 300); x.screen('gold', 400); return 'cast'; },
  quick_lift: x => { x.hit('beam', null, 500); x.hit('healglow big', null, 800, 160); return 'cast'; },
  lifeline: x => { x.shot('orb small', C.heal, ['hoop', C.heal, 700]); x.hit('hoop', C.heal, 700, 420); return 'cast'; },
  ward: x => { x.shot('shieldorb', null, ['shieldfx', null, 700]); x.hit('glyph', C.shield, 800, 300, '◆'); return 'cast'; },
  cleanse: x => { x.hit('splash', C.water, 600); x.hit('healglow', null, 900, 200); x.hit('drops', C.water, 900, 120); return 'cast'; },

  // Duelist
  slash_d: x => { x.hit('slash', null, 420, 140); if (!x.miss) x.hit('star', null, 480, 260); return 'melee'; },
  parry: x => { x.me('cross', C.steel, 620); x.me('shieldfx', null, 700, 120); return 'brace'; },
  twin_cut: x => { x.hit('chop', C.steel, 400, 120); x.hit('chop flip', C.steel, 400, 260); return 'melee'; },
  whirl: x => { x.t.forEach((u, i) => x.on(u, 'arc', null, 500, 120 + i * 110)); return 'spin'; },
  read_blade: x => { x.hit('crosshair', C.gold, 520); x.hit('slash', null, 420, 340); return 'melee'; },
  pinpoint: x => { x.hit('crosshair', C.steel, 420); x.hit('thrust', null, 420, 260); if (!x.miss) x.hit('star', null, 480, 380); return 'melee'; },
  feint: x => { x.hit('slash ghost', null, 420, 120); x.hit('glyph', C.gold, 800, 260, '?'); return 'act'; },
  perfect_form: x => { x.me('aura', C.steel, 900); x.me('glyph', C.gold, 900, 200, '✦'); return 'cast'; },

  // Berserker
  hack_b: x => { x.hit('chop', C.blood, 420, 150); if (!x.miss) x.shake(220); return 'melee'; },
  bloodprice: x => { x.me('drops', C.blood, 900); x.me('aura', C.blood, 900, 100); return 'brace'; },
  drink_deep: x => {
    x.hit('bite', C.blood, 480, 140);
    if (!x.miss) x.later(() => x.back('drop', C.blood, ['healglow', null, 700], { stagger: 60 }), 360);
    return 'melee';
  },
  frenzy: x => { [0, 100, 200].forEach((ms, i) => x.hit(i % 2 ? 'chop flip' : 'chop', C.blood, 380, 120 + ms)); if (!x.miss) x.shake(320); x.me('pop small', C.blood, 400, 360); return 'melee'; },
  howl: x => { x.me('shout', C.blood, 800); x.hit('hoop', C.arcane, 600, 260); x.hit('glyph', C.arcane, 800, 300, '↓'); return 'brace'; },

  // Ranger
  shoot_r: x => { x.shot('ranged', null, ['pierce', null, 420]); return 'act'; },
  hunters_mark: x => { x.hit('crosshair', C.blood, 600); x.later(() => x.shot('ranged', null, ['pierce', null, 420]), 300); return 'act'; },
  sic_em: x => { x.shot('hawk', C.gold, ['claw', C.gold, 460], { arc: -70 }); return 'act'; },
  pack_tactics: x => {
    x.shot('hawk', C.gold, ['claw', C.gold, 460], { arc: -70 });
    x.later(() => x.shot('ranged', null, ['pierce', null, 420]), 160);
    return 'act';
  },
  spotter: x => { x.hit('crosshair', C.gold, 700, 0); x.me('glyph', C.gold, 900, 0, '◉'); return 'cast'; },
  covering_fire: x => { [0, 90, 180].forEach(ms => x.shot('ranged', null, ['pierce', null, 360], { delay: ms })); x.party.forEach(u => x.on(u, 'hoop', C.shield, 500, 300)); return 'act'; },

  // Scoundrel
  stab: x => { x.hit('stabfx', C.steel, 360, 120); if (!x.miss) x.hit('pop small', C.blood, 380, 220); return 'melee'; },
  slip: x => { x.me('smoke', C.smoke, 800); return x.miss ? 'act' : 'retreat'; },
  envenom: x => { x.shot('dagger', C.poison, ['splash', C.poison, 560]); x.hit('drops', C.poison, 900, 320); return 'act'; },
  garrote: x => { x.hit('squeeze', C.steel, 700, 120); if (!x.miss) x.hit('pop small', C.blood, 400, 520); return 'melee'; },
  pickpocket: x => { x.hit('claw', C.steel, 420, 120); if (!x.miss) x.later(() => x.back('coin', null, ['glyph', C.gold, 700, 0, '+'], { spin: true }), 300); return 'melee'; },
  loaded_dice: x => { x.me('glyph spin', C.gold, 900, 0, '⚅'); x.me('glyph spin', C.gold, 900, 220, '⚅'); return 'cast'; },
  smoke_bomb: x => { x.party.forEach((u, i) => x.on(u, 'smoke', C.smoke, 1000, i * 90)); x.screen('tint', 500, 'rgba(150, 160, 170, 0.25)'); return 'act'; },

  // Herald
  inspire: x => { x.shot('note', C.gold, ['notes', null, 1000]); x.hit('aura', C.gold, 900, 300); return 'cast'; },
  jab: x => { x.shot('wave', C.song, ['pop', C.song, 460]); return 'cast'; },
  mocking_jest: x => { x.shot('wave', C.song, ['glyph', C.song, 800, 0, '!']); x.hit('crosshair', C.blood, 520, 260); return 'cast'; },
  rousing_chorus: x => { x.me('notes', null, 1100); x.party.forEach((u, i) => x.on(u, 'aura', C.gold, 900, 150 + i * 90)); x.screen('gold', 400); return 'cast'; },
  lend_a_hand: x => { x.shot('orb small', C.gold, ['glyph spin', C.gold, 800, 0, '⚂']); return 'cast'; },
  dirge: x => { x.shot('wave', C.shadow, ['notes dark', null, 1000]); x.hit('hoop', C.shadow, 600, 300); return 'cast'; },
  taunting_verse: x => { x.shot('wave', C.song, ['shout small', null, 700]); x.hit('crosshair', C.blood, 520, 300); return 'cast'; },
  cacophony: x => { [0, 100, 200].forEach(ms => x.shot('wave', C.song, null, { delay: ms })); if (!x.miss) { x.hit('zap', null, 500, 320); x.shake(320); } return 'cast'; },
  requiem: x => { x.hit('rune', C.dark, 1100); x.hit('notes dark', null, 1000, 200); x.screen('tint', 600, 'rgba(40, 20, 70, 0.35)'); return 'cast'; },
  encore: x => { x.me('glyph spin', C.song, 900, 0, '⚄'); x.me('notes', null, 1000, 100); return 'cast'; },

  // Alchemist
  toss: x => { x.shot('flask', C.fire, ['pop', C.fire, 520], { arc: 70, spin: true }); return 'act'; },
  tonic_a: x => { x.shot('flask', C.heal, ['healglow', null, 900], { arc: 60, spin: true }); x.hit('drops', C.heal, 800, 300); return 'act'; },
  firebomb: x => {
    x.shot('flask', C.fire, x.miss ? ['pop small', C.fire, 400] : ['fireburst', null, 800], { arc: 80, spin: true });
    if (!x.miss) x.later(() => x.screen('fire', 400), 300);
    return 'act';
  },
  acid_flask: x => { x.shot('flask', C.acid, ['splash', C.acid, 600], { arc: 70, spin: true }); x.hit('smoke', 'rgba(180, 230, 60, 0.6)', 900, 300); return 'act'; },
  concussion: x => {
    x.shot('flask', C.steel, ['slam', C.steel, 480], { arc: 70, spin: true });
    if (!x.miss) { x.hit('star', null, 520, 320); x.later(() => x.screen('white', 220), 300); }
    return 'act';
  },
  bottle_it: x => { x.me('drops', C.heal, 900); x.me('glyph', C.heal, 900, 120, '⚗'); return 'cast'; },
  quicksilver: x => { x.shot('orb', C.silver, ['aura', C.silver, 900]); x.hit('glyph spin', C.silver, 800, 300, '↻'); return 'cast'; },
  potency: x => { x.me('pop', C.acid, 500); x.me('glyph', C.acid, 800, 160, '⚁'); return 'cast'; },
  bramble_skin: x => { x.me('vines', C.nature, 900); x.me('glyph', C.nature, 800, 200, '⚃'); return 'cast'; },
  aura: x => { [0, 160, 320].forEach(ms => x.hit('glyph spin', C.gold, 700, ms, '⚄')); x.hit('aura', C.gold, 900, 200); return 'cast'; },
  transfusion: x => { x.me('drops', C.blood, 700); x.shot('drop', C.blood, ['healglow', null, 900], { stagger: 0 }); x.later(() => x.shot('drop', C.blood, null), 90); return 'cast'; },

  // Warden
  thornlash: x => { x.shot('thorn', C.nature, ['pop small', C.nature, 400]); if (!x.miss) x.hit('vines', C.nature, 800, 260); return 'act'; },
  sprout: x => { x.me('circle', null, 900); x.me('vines', C.nature, 900, 120); return 'cast'; },
  entangle: x => { x.hit('vines', C.nature, 1000); x.hit('squeeze', C.nature, 700, 300); return 'cast'; },
  strangle: x => { x.hit('vines', C.nature, 900); x.hit('squeeze', C.nature, 700, 250); if (!x.miss) x.shake(420); return 'cast'; },
};

// ------------------------------------------------------------------ enemy moves
// Each kind of enemy has a way of attacking: a motion (lunge, pounce, slam, charge) and an impact
// for the melee ones, or a projectile for the ranged ones, in its colour.
const LOOK = {
  deckhand: { m: 'lunge', hit: 'slash', c: '#b8c8b0' },
  crab: { m: 'lunge', hit: 'claw', c: '#ff8a5a' },
  jelly: { m: 'lunge', hit: 'zap', c: '#d79cff' },
  eel: { m: 'pounce', hit: 'bite', c: '#8fd8ff' },
  barnacle_priest: { shot: 'glob', hit: 'splash', c: '#9be06a' },
  siren: { shot: 'wave', hit: 'hoop', c: C.song },
  bell_warden: { m: 'slam', hit: 'slam', c: '#e0b060' },
  cutthroat: { m: 'lunge', hit: 'stabfx', c: C.steel },
  deckhound: { m: 'pounce', hit: 'bite', c: '#f0e0c8' },
  brine_golem: { m: 'slam', hit: 'slam', c: '#cfe6f0' },
  powder_monkey: { shot: 'flask', arc: 70, hit: 'pop', c: C.fire },
  tide_cultist: { shot: 'orb', hit: 'pop', c: C.shadow },
  corsair_captain: { shot: 'bullet', hit: 'pierce', c: '#ffd27a' },
  gallows_admiral: { shot: 'bullet', hit: 'pierce', c: '#ffd27a' },
  crag_ram: { m: 'charge', hit: 'slam', c: '#d8c8a8' },
  cliff_hermit: { shot: 'rock', arc: 60, hit: 'pop', c: '#b9ad98' },
  harpy: { m: 'pounce', hit: 'claw', c: '#f0d8b0' },
  storm_wisp: { bolt: true, hit: 'zap', c: C.storm },
  lightning_totem: { bolt: true, hit: 'zap', c: C.storm },
  thunder_wyvern: { m: 'pounce', hit: 'claw', c: C.storm },
  lamp_keeper: { shot: 'orb', hit: 'pop', c: '#fff2b0' },
  reef_maw: { m: 'pounce', hit: 'bite', c: '#ff9a8a' },
  iron_bosun: { m: 'slam', hit: 'slam', c: '#c8ccd4' },
  storm_roc: { m: 'pounce', hit: 'claw', c: C.storm },
  powder_keg: { m: 'slam', hit: 'fireburst', c: C.fire },
  cannon: { shot: 'ball', hit: 'pop', c: C.fire },
  tide_guard: { m: 'lunge', hit: 'thrust', c: C.steel },
  drowned_crown: { shot: 'orb', hit: 'pop', c: C.water },
};
// A move's name can say more than its enemy's kind: a pistol, a song, a breath, a wave.
const BY_NAME = [
  [/Pistol|Shot\b/, { shot: 'bullet', hit: 'pierce', c: '#ffd27a' }],
  [/Breath|Spray|Spit/, { shot: 'glob', hit: 'splash', many: 3 }],
  [/Beam|Flash|Glare/, { shot: 'orb', hit: 'pop', c: '#fff2b0', beam: true }],
  [/Bolt|Arc\b|Jolt|Overload|Discharge|Lightning|Static|Thunder/, { bolt: true, hit: 'zap', c: C.storm }],
  [/Song|Lullaby|Wail|Shriek|Screech|Dirge|Sermon|Prayer|Knell|Toll|Whistle/, { shot: 'wave', hit: 'hoop', c: C.song, sound: true }],
  [/Curse|Hex/, { shot: 'orb', hit: 'rune', c: C.shadow }],
  [/Wave|Deluge|Surge|Undertow|Maelstrom|Tidal|Depths/, { water: true, shot: 'orb', hit: 'splash', c: C.water }],
  [/Keg|Pot\b|Bomb|Blows Up/, { shot: 'flask', arc: 70, hit: 'fireburst', c: C.fire }],
  [/Broadside|Cannon|Guns/, { shot: 'ball', arc: 40, hit: 'pop', c: C.fire, many: 3 }],
  [/Rockslide/, { rocks: true, c: '#b9ad98' }],
  [/Hook|Grapple|Chain|Snare|Keelhaul|Hang/, { shot: 'chain', hit: 'squeeze', c: '#c8ccd4' }],
  [/Gale/, { gale: true, c: C.storm }],
];
// what a status rider looks like when it lands
const ST_C = { weak: C.arcane, vuln: '#ff7a6a', stun: '#ffe27a', hex: C.shadow, root: C.nature, burn: C.fire, shock: C.storm, mark: '#ff6a5a', lock: '#9be06a', static: C.storm, steal: C.gold };

function lookOf(fo, it) {
  const base = LOOK[fo.k] || { m: 'lunge', hit: 'slash', c: C.steel };
  const named = BY_NAME.find(([re]) => re.test(it.name || ''))?.[1];
  return named ? { ...base, m: undefined, ...named, c: named.c || base.c } : base;
}

// One impact on a unit, in the look's way.
function land(x, u, look, delay = 0) {
  if (look.bolt) { x.later(() => { x.bolt(x.from, u); x.on(u, 'zap', null, 500); }, delay); return; }
  if (look.shot) {
    const n = look.many || 1;
    for (let i = 0; i < n; i++)
      x.shot(look.shot, look.c, i === n - 1 ? [look.hit, look.c, 520] : null, { to: [u], arc: look.arc, spin: look.shot === 'flask' || look.shot === 'rock', delay: delay + i * 80 });
    return;
  }
  x.on(u, look.hit, look.c, 520, delay + 160);
}

// Returns how long the move takes to show, before its damage plays.
export function foeFx(x, fo, it, motion) {
  const look = lookOf(fo, it);
  const k = it.k;
  const st = it.st && ST_C[it.st];
  if (k === 'attack') {
    if (!look.shot && !look.bolt) motion(look.m || 'lunge');
    else motion('cast');
    x.t.forEach((u, i) => land(x, u, look, i * 90));
    if (st) x.later(() => x.hit('hoop', st, 520), 380);
    if (look.m === 'slam' || look.m === 'charge') x.shake(220);
    return look.shot || look.bolt ? 460 : 360;
  }
  if (k === 'all') {
    motion(look.shot || look.bolt || look.water || look.sound || look.rocks || look.gale ? 'cast' : look.m || 'slam');
    const us = x.t;
    if (look.water) {
      us.forEach((u, i) => x.on(u, 'tidewall', C.water, 800, 120 + i * 70));
      x.screen('tint', 600, 'rgba(60, 140, 220, 0.25)');
    } else if (look.sound) {
      x.me('shout', look.c, 800);
      us.forEach((u, i) => x.on(u, 'hoop', look.c, 600, 200 + i * 70));
      x.screen('tint', 500, 'rgba(255, 140, 210, 0.15)');
    } else if (look.rocks) {
      us.forEach((u, i) => [0, 120].forEach(ms => x.on(u, 'rockfall', look.c, 600, i * 80 + ms)));
      x.quake(300);
    } else if (look.gale) {
      us.forEach((u, i) => x.on(u, 'smoke', 'rgba(220, 235, 255, 0.6)', 800, i * 70));
      x.screen('tint', 500, 'rgba(200, 225, 255, 0.2)');
    } else if (look.shot || look.bolt) {
      us.forEach((u, i) => land(x, u, look, i * 80));
      if (look.bolt) x.later(() => x.screen('bolt', 200), 60);
    } else {
      us.forEach((u, i) => x.on(u, look.hit === 'slam' ? 'slam' : 'quake', look.c, 600, 200 + i * 60));
      x.quake(200);
    }
    if (st) x.later(() => x.hit('hoop', st, 520), 460);
    return 560;
  }
  if (k === 'debuff') {
    motion('cast');
    const c = st || C.shadow;
    x.shot('orb small', c, ['rune', c, 900]);
    return 420;
  }
  if (k === 'block') { motion('brace'); x.me('shieldfx', null, 700); return 300; }
  if (k === 'guard') {
    motion('brace');
    const to = typeof it.tgt === 'string' && it.tgt.startsWith('f') ? it.tgt : null;
    if (it.all) x.foes.forEach(u => x.on(u, 'shieldfx', null, 700, 120));
    else if (to && to !== x.from) x.shot('shieldorb', null, ['shieldfx', null, 700], { to: [to] });
    else x.me('shieldfx', null, 700);
    return 320;
  }
  if (k === 'heal') {
    motion('cast');
    const to = !it.self && typeof it.tgt === 'string' && it.tgt.startsWith('f') ? it.tgt : x.from;
    if (to === x.from) x.me('healglow', null, 900); else x.shot('orb', C.heal, ['healglow', null, 900], { to: [to] });
    return 320;
  }
  if (k === 'buff') {
    motion('brace');
    x.me('shout', C.blood, 800);
    if (!it.self) x.foes.filter(u => u !== x.from).forEach((u, i) => x.on(u, 'aura', C.blood, 800, 160 + i * 60));
    return 360;
  }
  if (k === 'summon') { motion('cast'); x.me('gather', C.water, 700); x.me('circle', null, 900, 200); return 420; }
  if (k === 'charge') { motion('brace'); x.me('gather', look.c, 800); return 360; }
  if (k === 'thief') {
    motion('pounce');
    x.hit('claw', look.c, 460, 140);
    x.later(() => x.back('coin', null, null, { spin: true }), 320);
    return 440;
  }
  if (k === 'merge') { motion('cast'); x.me('gather', C.storm, 700); x.me('pop', C.storm, 500, 400); return 420; }
  return 0;
}
