// Game data: terrain, acts, classes, skills, upgrades, items and enemies.
// Every import in this folder carries the same ?v= so Cloudflare serves fresh copies; bump them together.

export const GW = 10, GH = 8;
export const ROWS_PER_ACT = 8;   // map rows before each act's boss
export const MAX_UPGRADES = 4;   // upgrades a single skill can hold

// ---------- terrain ----------
export const T = { FLOOR: 0, COVER: 1, ROCK: 2, WATER: 3, WALL: 4, LAVA: 5, HILL: 6, THORN: 7 };
export const TERRAIN = [
  { cost: 1 },
  { cost: 2, cover: true },
  { cost: Infinity, fly: true },
  { cost: Infinity, fly: true },
  { cost: Infinity, los: true, phase: true },
  { cost: 1, lava: true },
  { cost: 2, hill: true },
  { cost: 2, thorn: true },
];
export const TERRAIN_HELP = [
  'Open ground.',
  'Cover: units here take 20% less damage. Costs 2 movement.',
  'Blocks walking (flyers pass over). Does not block sight.',
  'Only flyers can cross.',
  'Blocks movement and line of sight. Ghosts drift through.',
  'Deals 12% of max HP and sets burning when entered, or when a turn starts here.',
  'High ground: costs 2 movement; ranged skills from here reach 1 farther and hit 15% harder.',
  'Cuts anyone who walks in. Costs 2 movement.',
];
export const THEMES = {
  wood: ['Grass', 'Forest', 'Boulder', 'Water', 'Ruined wall', 'Lava', 'Hill', 'Brambles'],
  crypt: ['Flagstones', 'Rubble', 'Sarcophagus', 'Pit', 'Crypt wall', 'Lava', 'Dais', 'Bone spikes'],
  ember: ['Basalt', 'Ash drift', 'Obsidian', 'Chasm', 'Obsidian wall', 'Lava', 'Ridge', 'Glass shards'],
};

// ---------- acts ----------
export const ACTS = [
  {
    name: 'The Greenwood', theme: 'wood', boss: 'The Thornmother',
    terrain: { cover: [2, 4], rock: [1, 3], water: 0.5, walls: [0, 1], lava: [0, 0], hill: [1, 2], thorn: [0, 2] },
    early: [['slime', 'slime', 'goblin'], ['goblin', 'goblin', 'archer'], ['wolf', 'wolf'], ['slime', 'archer', 'goblin'], ['bat', 'bat', 'goblin']],
    late: [['wolf', 'wolf', 'archer', 'goblin'], ['goblin', 'goblin', 'archer', 'archer'], ['slime', 'slime', 'shaman', 'wolf'], ['wolf', 'bat', 'bat', 'archer']],
    elite: [['golem', 'slime', 'slime'], ['ogre', 'goblin', 'goblin']],
    bossParty: ['treant', 'wolf', 'archer'],
  },
  {
    name: 'The Sunken Crypt', theme: 'crypt', boss: 'The Hollow King',
    terrain: { cover: [1, 2], rock: [1, 2], water: 0.4, walls: [2, 4], lava: [0, 0], hill: [0, 1], thorn: [0, 2] },
    early: [['skeleton', 'skeleton', 'cultist'], ['ghost', 'ghost', 'bat'], ['spider', 'spider', 'skeleton'], ['cultist', 'shaman', 'skeleton']],
    late: [['skeleton', 'skeleton', 'ghost', 'cultist'], ['spider', 'spider', 'ghost', 'shaman'], ['skeleton', 'cultist', 'cultist', 'bat'], ['ghost', 'ghost', 'spider', 'skeleton']],
    elite: [['knight', 'skeleton', 'skeleton'], ['knight', 'ghost', 'shaman']],
    bossParty: ['lich', 'skeleton', 'cultist'],
  },
  {
    name: 'The Ember Peaks', theme: 'ember', boss: 'The Cinder Wyrm',
    terrain: { cover: [1, 2], rock: [1, 3], water: 0.3, walls: [1, 2], lava: [2, 4], hill: [1, 2], thorn: [0, 1] },
    early: [['imp', 'imp', 'orc'], ['salamander', 'salamander', 'orc'], ['orc', 'orc', 'shaman'], ['imp', 'salamander', 'firecultist']],
    late: [['orc', 'orc', 'imp', 'firecultist', 'imp'], ['salamander', 'salamander', 'imp', 'imp', 'orc'], ['magmagolem', 'imp', 'imp', 'firecultist'], ['orc', 'salamander', 'firecultist', 'shaman', 'imp']],
    elite: [['knight', 'knight', 'shaman', 'imp'], ['magmagolem', 'salamander', 'salamander', 'firecultist'], ['ogre', 'imp', 'imp', 'orc']],
    bossParty: ['wyrm', 'imp', 'imp', 'salamander'],
  },
];

// ---------- classes ----------
export const CLASSES = {
  warrior: { name: 'Warrior', hp: 44, atk: 10, mag: 2, def: 5, res: 2, spd: 8, mov: 3, crit: 5, main: 'atk', skills: ['strike', 'cleave', 'bash', 'warcry'], promos: ['blademaster', 'juggernaut'] },
  mage: { name: 'Mage', hp: 28, atk: 3, mag: 11, def: 1, res: 5, spd: 7, mov: 3, crit: 5, main: 'mag', skills: ['bolt', 'fireball', 'frost', 'mend'], promos: ['pyromancer', 'chronomancer'] },
  rogue: { name: 'Rogue', hp: 32, atk: 9, mag: 2, def: 2, res: 2, spd: 11, mov: 4, crit: 15, flank: 1.5, main: 'atk', skills: ['stab', 'knives', 'venom', 'assassinate'], promos: ['assassin', 'trickster'] },
};
export const PROMOS = {
  blademaster: { name: 'Blademaster', stats: { atk: 4, spd: 3 }, skill: 'whirldash',
    passive: 'Riposte: strikes back at anyone who hits them in melee (60% ATK).' },
  juggernaut: { name: 'Juggernaut', stats: { maxHp: 20, def: 3, res: 3 }, skill: 'aegis',
    passive: 'Bulwark: starts every battle with a shield worth 40% of max HP, and can\'t be knocked around.' },
  pyromancer: { name: 'Pyromancer', stats: { mag: 4 }, skill: 'eruption',
    passive: 'Ember Soul: immune to lava and burning; every magic hit sets the target alight.' },
  chronomancer: { name: 'Chronomancer', stats: { mag: 2, spd: 4 }, skill: 'quicken',
    passive: 'Time Sense: acts early in every battle, and magic hits shove the target back in the turn order.' },
  assassin: { name: 'Assassin', stats: { atk: 4, crit: 10 }, skill: 'shadowstep',
    passive: 'Shadow: always crits targets under half HP; a kill cloaks them in stealth.' },
  trickster: { name: 'Trickster', stats: { spd: 3, mov: 1 }, skill: 'smokebomb',
    passive: 'Slippery: walks straight through enemies, and every hit pockets 3 gold.' },
};

// ---------- skills ----------
// kind: phys | mag (damage), heal, shield, buff, summon. tgt: foe | ally | tile | self.
// shape: (none) single or area by aoe | line | chain | multi | random.
export const SKILLS = {
  strike: { name: 'Strike', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0, txt: 'A solid sword blow.' },
  cleave: { name: 'Cleave', kind: 'phys', tgt: 'self', range: [0, 0], aoe: 1, hits: 'foes', pow: 0.9, cd: 2, txt: 'Sweep every foe next to you.' },
  bash: { name: 'Shield Bash', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 0.7, cd: 3, stun: 1, txt: 'The target loses its next turn.' },
  warcry: { name: 'War Cry', kind: 'buff', tgt: 'self', range: [0, 0], aoe: 3, hits: 'foes', taunt: 2, guard: true, cd: 4,
    txt: 'Nearby foes must attack you, and you take 40% less damage until your next turn.' },

  bolt: { name: 'Arcane Bolt', kind: 'mag', tgt: 'foe', range: [2, 4], pow: 0.75, cd: 0, txt: 'A bolt of force. Needs line of sight.' },
  fireball: { name: 'Fireball', kind: 'mag', tgt: 'tile', range: [2, 5], aoe: 1, hits: 'all', pow: 1.15, cd: 3, lob: true, txt: 'Lobbed over walls. Burns friend and foe alike.' },
  frost: { name: 'Frost Lance', kind: 'mag', tgt: 'foe', range: [1, 4], pow: 0.9, cd: 2, slow: 2, txt: 'The target acts at half speed for 2 turns.' },
  mend: { name: 'Mend', kind: 'heal', tgt: 'ally', range: [0, 3], pow: 1.0, cd: 2, cleanse: true, lob: true, txt: 'Restores HP and cures poison and burns.' },

  stab: { name: 'Stab', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0, txt: 'Quick dagger work.' },
  knives: { name: 'Throwing Knives', kind: 'phys', tgt: 'foe', range: [2, 4], pow: 0.7, cd: 1, txt: 'A knife from a distance.' },
  venom: { name: 'Venom Blade', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 0.8, cd: 3, poison: 3, poisonPow: 0.35, txt: 'Poison bites at the start of each of its next 3 turns.' },
  assassinate: { name: 'Assassinate', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.3, cd: 4, execute: true, txt: 'Double damage against targets under half HP.' },

  whirldash: { name: 'Whirlwind Dash', kind: 'phys', tgt: 'tile', shape: 'line', range: [1, 4], hits: 'foes', pow: 0.9, cd: 3, dash: true,
    txt: 'Dash in a straight line, cutting every foe you pass.' },
  aegis: { name: 'Aegis', kind: 'shield', stat: 'def', tgt: 'self', range: [0, 0], aoe: 2, hits: 'allies', pow: 2.0, cd: 3,
    txt: 'Shields every ally within 2 tiles. Shields soak damage before HP.' },
  eruption: { name: 'Eruption', kind: 'mag', tgt: 'tile', range: [2, 5], aoe: 1, hits: 'foes', pow: 1.1, cd: 4, burn: 2, terrain: T.LAVA, lob: true,
    txt: 'The ground splits: the area becomes lava.' },
  quicken: { name: 'Quicken', kind: 'buff', tgt: 'ally', range: [1, 4], pow: 0, cd: 3, ctGive: 100, cdReduce: 1, lob: true,
    txt: 'The ally acts right away and their cooldowns tick down by 1.' },
  shadowstep: { name: 'Shadowstep', kind: 'phys', tgt: 'foe', range: [1, 6], pow: 1.2, cd: 3, leap: true, lob: true, stealth: true,
    txt: 'Vanish, reappear beside the target and strike. Leaves you stealthed: foes can\'t single you out until you attack again.' },
  smokebomb: { name: 'Smoke Bomb', kind: 'buff', tgt: 'tile', range: [1, 4], aoe: 1, hits: 'foes', blind: 2, cd: 3, lob: true,
    txt: 'Blinded foes miss half their attacks for 2 turns.' },

  e_slam: { name: 'Slam', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0 },
  e_stab: { name: 'Stab', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0 },
  e_shoot: { name: 'Shoot', kind: 'phys', tgt: 'foe', range: [2, 5], pow: 0.9, cd: 0 },
  e_bite: { name: 'Rending Bite', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 0.9, poison: 2, poisonPow: 0.25, cd: 0, txt: 'Leaves the target bleeding.' },
  e_drain: { name: 'Drain', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 0.9, drain: 0.5, cd: 0, txt: 'Heals itself for half the damage.' },
  e_slash: { name: 'Slash', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, cd: 0 },
  e_hex: { name: 'Hex', kind: 'mag', tgt: 'foe', range: [2, 4], pow: 0.8, cd: 0 },
  e_flame: { name: 'Flame Burst', kind: 'mag', tgt: 'tile', range: [2, 4], aoe: 1, hits: 'all', pow: 1.0, burn: 2, cd: 3, lob: true },
  e_zap: { name: 'Zap', kind: 'mag', tgt: 'foe', range: [2, 3], pow: 0.6, cd: 0 },
  e_mend: { name: 'Mend', kind: 'heal', tgt: 'ally', range: [0, 3], pow: 1.2, cd: 2, lob: true },
  e_smash: { name: 'Smash', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.15, cd: 0 },
  e_stomp: { name: 'Stomp', kind: 'phys', tgt: 'self', range: [0, 0], aoe: 1, hits: 'foes', pow: 0.8, stun: 1, cd: 3 },
  e_kcleave: { name: 'Reaping Arc', kind: 'phys', tgt: 'self', range: [0, 0], aoe: 1, diag: true, hits: 'foes', pow: 1.0, cd: 2 },
  e_pound: { name: 'Pound', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.2, stun: 1, cd: 3 },
  e_rock: { name: 'Hurl Rock', kind: 'phys', tgt: 'foe', range: [2, 4], pow: 0.8, cd: 2, lob: true },
  e_boulder: { name: 'Hurl Boulder', kind: 'phys', tgt: 'foe', range: [2, 4], pow: 0.9, knock: true, cd: 2, lob: true },
  e_deathbolt: { name: 'Death Bolt', kind: 'mag', tgt: 'foe', range: [2, 5], pow: 1.0, cd: 0 },
  e_nova: { name: 'Grave Nova', kind: 'mag', tgt: 'self', range: [0, 0], aoe: 2, hits: 'foes', pow: 0.85, cd: 3 },
  e_raise: { name: 'Raise Dead', kind: 'summon', tgt: 'self', range: [0, 0], cd: 4, summon: 'skeleton', txt: 'Calls up two skeletons.' },
  e_roots: { name: 'Grasping Roots', kind: 'mag', tgt: 'foe', range: [2, 5], pow: 0.7, pull: 9, slow: 2, cd: 2, lob: true, txt: 'Drags the target to the Thornmother.' },
  e_thornburst: { name: 'Thornburst', kind: 'phys', tgt: 'self', range: [0, 0], aoe: 2, hits: 'foes', pow: 0.7, poison: 2, poisonPow: 0.3, cd: 3 },
  e_overgrow: { name: 'Overgrowth', kind: 'mag', tgt: 'tile', range: [2, 5], aoe: 1, hits: 'foes', pow: 0.5, terrain: T.THORN, lob: true, cd: 3, txt: 'Brambles burst from the ground.' },
  e_wail: { name: 'Wail', kind: 'mag', tgt: 'foe', range: [1, 3], pow: 0.8, vuln: 2, vulnAmt: 0.3, cd: 0, txt: 'The target takes 30% more damage for 2 turns.' },
  e_web: { name: 'Web', kind: 'phys', tgt: 'foe', range: [2, 4], pow: 0.4, slow: 2, cd: 2 },
  e_spiderbite: { name: 'Venom Bite', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 0.8, poison: 3, poisonPow: 0.3, cd: 0 },
  e_firebolt: { name: 'Firebolt', kind: 'mag', tgt: 'foe', range: [2, 4], pow: 0.8, burn: 2, cd: 0 },
  e_flamebite: { name: 'Flame Bite', kind: 'phys', tgt: 'foe', range: [1, 1], pow: 1.0, burn: 2, cd: 0 },
  e_magmaslam: { name: 'Magma Slam', kind: 'phys', tgt: 'self', range: [0, 0], aoe: 1, hits: 'foes', pow: 1.0, terrain: T.LAVA, cd: 3, txt: 'Leaves the ground around it molten.' },
  e_breath: { name: 'Flame Breath', kind: 'mag', tgt: 'tile', shape: 'line', range: [1, 5], hits: 'foes', pow: 1.0, burn: 2, cd: 2 },
  e_tailsweep: { name: 'Tail Sweep', kind: 'phys', tgt: 'self', range: [0, 0], aoe: 1, diag: true, hits: 'foes', pow: 0.9, knock: true, cd: 2 },
  e_firerain: { name: 'Fire Rain', kind: 'mag', tgt: 'tile', range: [2, 6], aoe: 1, hits: 'foes', pow: 0.9, terrain: T.LAVA, lob: true, cd: 3 },
};

// ---------- upgrades ----------
// Each upgrade rewrites the skill. ok(o) decides whether it can apply to the skill as it stands;
// group makes upgrades in the same group exclusive; repeat lets an upgrade stack.
const dmg = o => o.kind === 'phys' || o.kind === 'mag';
const powered = o => dmg(o) || o.kind === 'heal' || o.kind === 'shield';
const single = o => o.tgt === 'foe' && !o.aoe && !o.shape;
const ranged = o => o.range[1] > 1 && o.tgt !== 'self';
const melee = o => o.tgt === 'foe' && o.range[1] === 1 && !o.shape;

export const UPGRADES = {
  honed: { name: 'Honed', note: '+25% power', repeat: true, ok: powered, apply: o => { o.pow *= 1.25; } },
  hasty: { name: 'Hasty', note: 'Cooldown 1 shorter', repeat: true, ok: o => o.cd > 0, apply: o => { o.cd -= 1; } },
  reach: { name: 'Far-reaching', note: '+1 range', repeat: true, ok: o => ranged(o) && o.shape !== 'random', apply: o => { o.range = [o.range[0], o.range[1] + 1]; } },

  ironclad: { name: 'Ironclad', note: 'Scales with DEF instead, at +50% power', group: 'stat', ok: o => powered(o) && o.stat !== 'def', apply: o => { o.stat = 'def'; o.pow *= 1.5; } },
  quicksilver: { name: 'Quicksilver', note: 'Scales with SPD instead', group: 'stat', ok: o => powered(o) && o.stat !== 'spd', apply: o => { o.stat = 'spd'; } },
  desperate: { name: 'Desperation', note: 'Scales with how much HP you\'re missing', group: 'stat', ok: powered, apply: o => { o.stat = 'missing'; } },
  heft: { name: 'Heft', note: 'Scales with 30% of your max HP instead', group: 'stat', ok: powered, apply: o => { o.stat = 'heft'; } },
  spellblade: { name: 'Spellblade', note: 'Becomes magic: uses MAG, hits RES', group: 'stat', ok: o => o.kind === 'phys', apply: o => { o.kind = 'mag'; o.stat = 'mag'; } },
  brute: { name: 'Brute Force', note: 'Becomes physical: uses ATK, hits DEF', group: 'stat', ok: o => o.kind === 'mag', apply: o => { o.kind = 'phys'; o.stat = 'atk'; } },

  piercing: { name: 'Piercing', note: 'Becomes a line that hits everything in its path', group: 'shape', ok: o => single(o) && dmg(o),
    apply: o => { o.shape = 'line'; o.tgt = 'tile'; o.range = [1, Math.max(3, o.range[1])]; o.hits = 'foes'; } },
  ricochet: { name: 'Ricochet', note: 'Bounces to 2 more foes nearby (60%)', group: 'shape', ok: o => single(o) && dmg(o), apply: o => { o.shape = 'chain'; o.chainN = 2; o.chainPow = 0.6; } },
  splash: { name: 'Splash', note: 'Hits foes around the target too (75%)', group: 'shape', ok: o => single(o) && dmg(o), apply: o => { o.aoe = 1; o.hits = 'foes'; o.pow *= 0.75; } },
  wild: { name: 'Wild Magic', note: 'Hits a random foe anywhere, +40% power', group: 'shape', ok: o => single(o) && dmg(o),
    apply: o => { o.shape = 'random'; o.tgt = 'self'; o.range = [0, 0]; o.pow *= 1.4; } },
  pointblank: { name: 'Point Blank', note: 'Range 1 only, +60% power', group: 'shape', ok: o => single(o) && ranged(o) && dmg(o), apply: o => { o.range = [1, 1]; o.pow *= 1.6; } },
  sniper: { name: 'Sniper', note: 'Range 3+ only, +2 range, +25% power', group: 'shape', ok: o => single(o) && o.range[1] >= 3 && dmg(o),
    apply: o => { o.range = [3, o.range[1] + 2]; o.pow *= 1.25; } },
  barrage: { name: 'Barrage', note: 'Fires at 3 random foes in range (55% each)', group: 'shape', ok: o => single(o) && ranged(o) && dmg(o),
    apply: o => { o.shape = 'multi'; o.multiN = 3; o.pow *= 0.55; o.tgt = 'self'; } },
  leap: { name: 'Leaping', note: 'Range 1–4: you leap next to the target first', group: 'move', ok: melee, apply: o => { o.range = [1, 4]; o.leap = true; } },
  spin: { name: 'Spin', note: '+1 radius, and diagonals count', group: 'shape', ok: o => o.tgt === 'self' && o.aoe > 0, apply: o => { o.aoe += 1; o.diag = true; } },
  arcing: { name: 'Arcing', note: 'Ignores walls', group: 'lob', ok: o => ranged(o) && !o.lob, apply: o => { o.lob = true; } },

  aegis: { name: 'Aegis Conversion', note: 'No longer hurts anyone: shields allies for the amount instead', group: 'effect', ok: o => dmg(o) && o.shape !== 'random' && o.shape !== 'multi',
    apply: o => {
      o.kind = 'shield'; o.hits = 'allies'; o.pow *= 0.8;
      if (o.tgt === 'foe') { o.tgt = 'ally'; o.range = [0, o.range[1]]; }
      for (const k of ['stun', 'slow', 'poison', 'burn', 'knock', 'pull', 'execute', 'vuln', 'leap', 'dash']) delete o[k];
    } },
  reverse: { name: 'Reverse Polarity', note: 'Hurts foes instead of healing (magic)', group: 'effect', ok: o => o.kind === 'heal',
    apply: o => { o.kind = 'mag'; o.stat = 'mag'; o.tgt = 'foe'; o.hits = 'foes'; o.range = [1, o.range[1]]; delete o.cleanse; } },
  overflow: { name: 'Overflow', note: 'Healing past full HP becomes a shield', group: 'effect', ok: o => o.kind === 'heal', apply: o => { o.overflow = true; } },
  vampiric: { name: 'Vampiric', note: 'Heals you for half the damage dealt', group: 'life', ok: dmg, apply: o => { o.drain = 0.5; } },
  generous: { name: 'Generous', note: '40% of the damage heals your most hurt ally', group: 'life', ok: dmg, apply: o => { o.generous = 0.4; } },
  martyr: { name: 'Martyrdom', note: 'Costs 15% of your max HP, +60% power', group: 'cost', ok: powered, apply: o => { o.hpCost = 0.15; o.pow *= 1.6; } },

  frostbite: { name: 'Frostbite', note: 'Slows for 2 turns', ok: o => dmg(o) && !o.slow, apply: o => { o.slow = 2; } },
  venomous: { name: 'Venomous', note: 'Poisons for 3 turns', ok: o => dmg(o) && !o.poison, apply: o => { o.poison = 3; o.poisonPow = 0.3; } },
  kindling: { name: 'Kindling', note: 'Sets targets burning for 2 turns', ok: o => dmg(o) && !o.burn, apply: o => { o.burn = 2; } },
  concussive: { name: 'Concussive', note: 'Stuns targets under half HP', ok: o => dmg(o) && !o.stun, apply: o => { o.stunLow = true; } },
  hex: { name: 'Hex', note: 'Targets take 30% more damage for 2 turns', ok: o => dmg(o) && !o.vuln, apply: o => { o.vuln = 2; o.vulnAmt = 0.3; } },
  shove: { name: 'Shove', note: 'Knocks targets back', group: 'push', ok: o => dmg(o) && o.tgt !== 'self' || (o.tgt === 'self' && o.aoe > 0 && dmg(o)), apply: o => { o.knock = true; } },
  grapple: { name: 'Grapple', note: 'Yanks the target next to you', group: 'push', ok: o => single(o) && ranged(o) && dmg(o), apply: o => { o.pull = 9; } },
  switcheroo: { name: 'Switcheroo', note: 'You swap places with the target', group: 'push', ok: o => (o.tgt === 'foe' || o.tgt === 'ally') && !o.shape && !o.aoe && !o.leap, apply: o => { o.swap = true; } },
  hitrun: { name: 'Hit and Run', note: 'Afterwards you hop up to 2 tiles away', group: 'move', ok: o => melee(o) && dmg(o), apply: o => { o.recoil = 2; } },

  molten: { name: 'Molten', note: 'The ground it hits turns to lava', group: 'terrain', ok: o => dmg(o) && o.tgt !== 'self' && o.shape !== 'random' && o.shape !== 'multi', apply: o => { o.terrain = T.LAVA; } },
  overgrowth: { name: 'Overgrowth', note: 'The ground it hits sprouts brambles', group: 'terrain', ok: o => dmg(o) && o.tgt !== 'self' && o.shape !== 'random' && o.shape !== 'multi', apply: o => { o.terrain = T.THORN; } },
  earthshaper: { name: 'Earthshaper', note: 'Raises walls on the open tiles around the target', group: 'terrain', ok: o => (o.tgt === 'foe' || o.tgt === 'tile') && !o.shape, apply: o => { o.walls = true; } },

  echoing: { name: 'Echoing', note: '40% chance to fire again for free', group: 'echo', ok: o => o.kind !== 'summon', apply: o => { o.echo = 0.4; } },
  twinned: { name: 'Twinned', note: 'Hits twice at 65% power', ok: o => dmg(o) && !o.double, apply: o => { o.double = true; o.pow *= 0.65; } },
  gamble: { name: 'Loaded Dice', note: 'Damage rolls anywhere from 0% to 250%', ok: dmg, apply: o => { o.gamble = true; } },
  timedebt: { name: 'Time Debt', note: 'No cooldown, but your next turn comes later', ok: o => o.cd > 0, apply: o => { o.cd = 0; o.ctCost = 35; } },
  chronoshock: { name: 'Chronoshock', note: 'Targets are shoved 30 back in the turn order', ok: dmg, apply: o => { o.ctTake = 30; } },

  // signature upgrades: only offered for one skill
  riposte: { name: 'Riposte Stance', only: 'strike', note: 'Also readies a counterattack against the next melee hit', ok: () => true, apply: o => { o.riposte = true; } },
  maelstrom: { name: 'Maelstrom', only: 'cleave', note: 'First drags every foe within 2 tiles toward you', ok: () => true, apply: o => { o.vortex = 2; } },
  bulwark: { name: 'Bulwark', only: 'bash', note: 'You gain a shield worth twice the damage dealt', ok: dmg, apply: o => { o.selfShield = 2; } },
  rally: { name: 'Rallying Cry', only: 'warcry', group: 'effect', note: 'Instead of taunting, allies in range deal +30% damage for 2 turns', ok: () => true,
    apply: o => { o.hits = 'allies'; delete o.taunt; o.rally = 2; } },
  missiles: { name: 'Magic Missile', only: 'bolt', group: 'shape', note: 'Splits into 3 missiles at random foes in range (50% each)', ok: single,
    apply: o => { o.shape = 'multi'; o.multiN = 3; o.pow *= 0.67; o.tgt = 'self'; o.range = [o.range[0], o.range[1]]; } },
  meteor: { name: 'Meteor', only: 'fireball', group: 'shape', note: 'Range 3–8, radius 2, +40% power, cooldown +2', ok: o => o.aoe > 0,
    apply: o => { o.range = [3, 8]; o.aoe += 1; o.pow *= 1.4; o.cd += 2; } },
  deepfreeze: { name: 'Deep Freeze', only: 'frost', note: 'Freezes the target solid: stunned, but takes half damage', ok: () => true, apply: o => { o.stun = 1; o.pow *= 0.5; } },
  transfusion: { name: 'Transfusion', only: 'mend', group: 'effect', note: 'Drains a foe and gives the HP to your most hurt ally', ok: o => o.kind === 'heal',
    apply: o => { o.kind = 'mag'; o.stat = 'mag'; o.tgt = 'foe'; o.hits = 'foes'; o.range = [1, o.range[1] + 1]; o.generous = 1; delete o.cleanse; } },
  backstab: { name: 'Backstab', only: 'stab', note: 'Flanked targets take double damage', ok: () => true, apply: o => { o.backstab = true; } },
  fan: { name: 'Fan of Knives', only: 'knives', group: 'shape', note: 'Hits every foe within 2 tiles of you (70%)', ok: single,
    apply: o => { o.tgt = 'self'; o.range = [0, 0]; o.aoe = 2; o.hits = 'foes'; o.pow *= 1.0; } },
  plague: { name: 'Plague', only: 'venom', group: 'shape', note: 'Splashes poison onto foes around the target', ok: single, apply: o => { o.aoe = 1; o.hits = 'foes'; o.pow *= 0.7; } },
  markdeath: { name: 'Mark for Death', only: 'assassinate', group: 'effect', note: 'No damage: the target takes +75% from everyone for 3 turns, cooldown 2',
    ok: () => true, apply: o => { o.kind = 'buff'; o.vuln = 3; o.vulnAmt = 0.75; o.cd = 2; delete o.execute; } },
};

// ---------- items ----------
export const ITEMS = {
  band: { name: 'Power Band', price: 55, stats: { atk: 3 }, txt: '+3 ATK' },
  ring: { name: "Sage's Ring", price: 55, stats: { mag: 3 }, txt: '+3 MAG' },
  shield: { name: 'Iron Buckler', price: 50, stats: { def: 3 }, txt: '+3 DEF' },
  cloak: { name: 'Warding Cloak', price: 45, stats: { res: 3 }, txt: '+3 RES' },
  heart: { name: 'Heartstone', price: 55, stats: { maxHp: 15 }, txt: '+15 max HP' },
  feather: { name: 'Quick Feather', price: 50, stats: { spd: 4 }, txt: '+4 SPD: takes turns more often' },

  monocle: { name: 'Glass Monocle', price: 70, unique: true, txt: 'Deal 50% more damage. Take 50% more damage.' },
  swapstone: { name: 'Swapstone', price: 40, unique: true, txt: 'Your ATK and MAG trade places.' },
  tortoise: { name: 'Tortoise Shell', price: 60, unique: true, stats: { def: 7, spd: -3, mov: -1 }, txt: '+7 DEF, −3 SPD, −1 MOV' },
  anklet: { name: 'Featherweight Anklet', price: 65, unique: true, stats: { mov: 2, spd: 3 }, txt: '+2 MOV and +3 SPD, but −25% max HP' },
  phoenix: { name: 'Phoenix Feather', price: 110, unique: true, txt: 'Once per battle, rise again at 50% HP when knocked out.' },
  spite: { name: 'Spite Doll', price: 70, unique: true, txt: 'When you\'re knocked out, every foe loses 30% of its max HP.' },
  bees: { name: 'Bag of Bees', price: 60, unique: true, txt: 'Whenever you use a skill, a bee stings a random foe.' },
  echo: { name: 'Echo Bell', price: 100, unique: true, txt: '25% chance to cast any skill twice.' },
  bloodpact: { name: 'Blood Pact', price: 90, unique: true, txt: 'Your skills have no cooldowns, but each use costs 10% of max HP.' },
  lavawalkers: { name: 'Lava Walkers', price: 75, unique: true, txt: 'Immune to lava. Every tile you walk off turns to lava.' },
  magnet: { name: 'Magnet Gauntlet', price: 60, unique: true, txt: 'Your hits drag targets 1 tile toward you.' },
  clockwork: { name: 'Clockwork Heart', price: 110, unique: true, txt: 'Every third turn, you immediately take another turn.' },
  crown: { name: 'Cursed Crown', price: 70, unique: true, txt: '+40% damage, but lose 5% of max HP every turn.' },
  mirror: { name: 'Mirror Shard', price: 75, unique: true, txt: 'Attackers take 35% of the damage they deal you, at any range.' },
  blink: { name: 'Blink Boots', price: 80, unique: true, txt: 'You teleport instead of walking: terrain and bodies don\'t slow you.' },
  thornseed: { name: 'Thornseed Pouch', price: 45, unique: true, txt: 'Ground you hit sprouts brambles.' },
  frostlocket: { name: 'Frostbite Locket', price: 80, unique: true, txt: 'Your hits slow, and slowed foes take 40% more from you.' },
  phylactery: { name: "Lich's Phylactery", price: 110, unique: true, txt: 'Foes you kill rise as skeletons on your side for the rest of the battle.' },
  martyr: { name: "Martyr's Locket", price: 65, unique: true, txt: 'Damage aimed at adjacent allies hits you instead, at half strength.' },
  chaos: { name: 'Chaos Die', price: 55, unique: true, txt: 'Each turn, a random stat gets +8 for that turn.' },
  goldtooth: { name: 'Gold Tooth', price: 70, unique: true, txt: '+40% gold from battles, and +1 ATK and MAG for every 100 gold the party carries.' },
  hollow: { name: 'Hollow Mask', price: 45, unique: true, txt: 'Allies\' attacks heal you instead of hurting you.' },
  lantern: { name: "Hermit's Lantern", price: 60, unique: true, txt: '+45% damage while no ally is within 2 tiles.' },
  collar: { name: 'Pack Collar', price: 60, unique: true, txt: '+15% damage for every ally standing next to you.' },
  fang: { name: 'Vampire Fang', price: 85, unique: true, txt: 'Heal 20% of the damage you deal.' },
  hourglass: { name: 'Cracked Hourglass', price: 95, unique: true, txt: 'Cooldowns of 2 or more are 1 turn shorter.' },
  belt: { name: "Giant's Belt", price: 95, unique: true, txt: 'Area skills grow 1 tile in radius.' },
  scope: { name: 'Long Scope', price: 75, unique: true, txt: 'Ranged skills reach 1 tile farther.' },
};

// ---------- enemies ----------
export const FOES = {
  slime: { name: 'Slime', hp: 18, atk: 6, def: 1, res: 1, spd: 5, mov: 2, skills: ['e_slam'] },
  goblin: { name: 'Goblin', hp: 15, atk: 7, def: 1, res: 1, spd: 10, mov: 4, skills: ['e_stab'] },
  archer: { name: 'Goblin Archer', hp: 13, atk: 7, def: 1, res: 1, spd: 8, mov: 3, skills: ['e_shoot'], ai: 'ranged' },
  wolf: { name: 'Wolf', hp: 17, atk: 7, def: 1, res: 1, spd: 12, mov: 5, skills: ['e_bite'] },
  bat: { name: 'Bat', hp: 10, atk: 5, def: 0, res: 1, spd: 13, mov: 5, fly: true, skills: ['e_drain'] },
  shaman: { name: 'Shaman', hp: 18, atk: 3, mag: 8, def: 1, res: 3, spd: 7, mov: 3, skills: ['e_mend', 'e_zap'], ai: 'ranged' },
  golem: { name: 'Stone Golem', hp: 75, atk: 13, def: 8, res: 2, spd: 4, mov: 2, skills: ['e_pound', 'e_rock', 'e_slam'], scale: 1.2 },
  ogre: { name: 'Ogre Warlord', hp: 70, atk: 14, def: 4, res: 1, spd: 5, mov: 3, skills: ['e_boulder', 'e_stomp', 'e_smash'], scale: 1.25 },
  treant: { name: 'The Thornmother', hp: 140, atk: 10, mag: 9, def: 4, res: 3, spd: 6, mov: 2, skills: ['e_roots', 'e_thornburst', 'e_overgrow', 'e_slam'], boss: true, regen: 0.04, scale: 1.5,
    info: 'Regrows 4% of her HP every turn.' },
  skeleton: { name: 'Skeleton', hp: 24, atk: 8, def: 4, res: 0, spd: 6, mov: 3, skills: ['e_slash'] },
  cultist: { name: 'Cultist', hp: 17, atk: 3, mag: 9, def: 1, res: 3, spd: 7, mov: 3, skills: ['e_flame', 'e_hex'], ai: 'ranged' },
  ghost: { name: 'Ghost', hp: 16, atk: 3, mag: 8, def: 1, res: 6, spd: 9, mov: 4, fly: true, phase: true, skills: ['e_wail'], ai: 'ranged', info: 'Drifts through walls.' },
  spider: { name: 'Crypt Spider', hp: 16, atk: 7, def: 2, res: 1, spd: 11, mov: 4, skills: ['e_web', 'e_spiderbite'] },
  knight: { name: 'Dark Knight', hp: 60, atk: 12, def: 6, res: 3, spd: 7, mov: 3, skills: ['e_kcleave', 'e_slash'], scale: 1.1 },
  lich: { name: 'The Hollow King', hp: 110, atk: 4, mag: 12, def: 3, res: 6, spd: 8, mov: 3, skills: ['e_raise', 'e_nova', 'e_deathbolt'], ai: 'ranged', boss: true, scale: 1.4 },
  imp: { name: 'Imp', hp: 14, atk: 3, mag: 9, def: 1, res: 3, spd: 12, mov: 4, fly: true, fireproof: true, skills: ['e_firebolt'], ai: 'ranged' },
  salamander: { name: 'Salamander', hp: 26, atk: 10, def: 3, res: 2, spd: 8, mov: 4, fireproof: true, trail: true, skills: ['e_flamebite'], info: 'Leaves lava where it walks.' },
  orc: { name: 'Orc Brute', hp: 36, atk: 11, def: 3, res: 1, spd: 5, mov: 3, skills: ['e_stomp', 'e_smash'] },
  firecultist: { name: 'Ash Priest', hp: 20, atk: 3, mag: 11, def: 1, res: 4, spd: 7, mov: 3, skills: ['e_flame', 'e_firebolt'], ai: 'ranged' },
  magmagolem: { name: 'Magma Golem', hp: 85, atk: 14, def: 8, res: 3, spd: 4, mov: 2, fireproof: true, skills: ['e_magmaslam', 'e_pound', 'e_rock'], scale: 1.2 },
  wyrm: { name: 'The Cinder Wyrm', hp: 125, atk: 13, mag: 14, def: 6, res: 5, spd: 9, mov: 3, fly: true, fireproof: true, skills: ['e_breath', 'e_tailsweep', 'e_firerain', 'e_flamebite'], boss: true, scale: 1.6 },
};
