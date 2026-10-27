// Rules shared by the battle and the menus: hero stats, skill stats after artifacts, descriptions, reward pools.
import { CLASSES, PROMOS, SKILLS, MODS, ITEMS, ARCHES, MAX_MODS, MAX_SKILLS, MAX_RELICS } from './data.js?v=6';

export const rnd = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
export const pick = a => a[Math.floor(Math.random() * a.length)];
export const chance = p => Math.random() < p;
export function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

export const has = (u, id) => !!(u.items && u.items.includes(id));
// u.line lists the classes a hero has promoted into, oldest first; their passives all apply.
export const isClass = (u, id) => !!(u.line && u.line.includes(id));
export const artTags = id => (MODS[id] || ITEMS[id]).tags || [];
export const heroSprite = p => p.promo || p.cls;
export const heroTitle = p => p.promo ? PROMOS[p.promo].name : CLASSES[p.cls].name;
export const isSkillArt = id => !!MODS[id];
export const artName = id => (MODS[id] || ITEMS[id]).name;
export const artText = id => MODS[id] ? MODS[id].note : ITEMS[id].txt;
export const artPrice = id => (MODS[id] || ITEMS[id]).price;

export function newHero(cls) {
  const c = CLASSES[cls];
  return { cls, promo: null, maxHp: c.hp, hp: c.hp, atk: c.atk, mag: c.mag, def: c.def, res: c.res, spd: c.spd, mov: c.mov, crit: c.crit, items: [], line: [],
    skills: c.start.map(id => ({ id, mods: [] })) };
}

// Stats with hero artifacts applied. gold feeds the Gold Tooth.
export function heroStats(p, gold = 0) {
  const o = { maxHp: p.maxHp, atk: p.atk, mag: p.mag, def: p.def, res: p.res, spd: p.spd, mov: p.mov, crit: p.crit };
  for (const id of p.items) for (const [k, v] of Object.entries(ITEMS[id].stats || {})) o[k] += v;
  if (p.items.includes('anklet')) o.maxHp = Math.round(o.maxHp * 0.75);
  if (p.items.includes('goldtooth')) { const b = Math.floor(gold / 100); o.atk += b; o.mag += b; }
  if (p.items.includes('swapstone')) [o.atk, o.mag] = [o.mag, o.atk];
  o.mov = Math.max(1, o.mov); o.spd = Math.max(1, o.spd);
  return o;
}
// The shield a hero starts each battle with.
export const startShield = (p, maxHp) => Math.round(maxHp * ((isClass(p, 'juggernaut') ? 0.4 : 0) + (p.items.includes('capacitor') ? 0.25 : 0)));
// What describe() and the damage numbers read stats from, for a hero outside battle.
export const heroSrc = (p, gold) => { const st = heroStats(p, gold); return { ...st, hp: p.hp, items: p.items, line: p.line, shield: startShield(p, st.maxHp) }; };

// The classes hero p can promote into next: two after each act boss, none once they're tier 2.
export function promoOptions(p) {
  const line = p.line || [];
  return line.length === 0 ? CLASSES[p.cls].promos : line.length === 1 ? PROMOS[line[0]].next : [];
}
export function promote(p, id) {
  p.promo = id;
  p.line = [...(p.line || []), id];
  for (const [k, v] of Object.entries(PROMOS[id].stats)) { p[k] += v; if (k === 'maxHp') p.hp += v; }
}

// The skill as it stands after its artifacts and the holder's hero artifacts.
export function skStats(u, s) {
  const d = SKILLS[s.id];
  const o = { ...d, id: s.id, range: [...d.range], mods: s.mods || [] };
  o.stat = d.stat || (d.kind === 'phys' ? 'atk' : 'mag');
  if (!o.hits) o.hits = o.kind === 'heal' || o.kind === 'shield' ? 'allies' : 'foes';
  for (const id of o.mods) MODS[id].apply(o);
  if (has(u, 'scope') && o.range[1] > 1 && o.tgt !== 'self') o.range = [o.range[0], o.range[1] + 1];
  if (has(u, 'belt') && o.aoe) o.aoe += 1;
  if (has(u, 'hourglass') && o.cd > 1) o.cd -= 1;
  if (has(u, 'bloodpact') && o.cd > 0) { o.cd = 0; o.bloodpact = true; }
  if (has(u, 'aegisheart') && o.kind === 'shield') o.pow *= 1.4;
  const dmg = o.kind === 'phys' || o.kind === 'mag';
  if (isClass(u, 'ninja') && dmg && o.tgt === 'foe' && o.range[1] === 1 && !o.shape && !o.aoe && !o.times && !o.double) { o.double = true; o.pow *= 0.6; }
  if (isClass(u, 'warlock') && dmg) { o.hpCost = (o.hpCost || 0) + 0.06; o.pow *= 1.35; }
  o.cd = Math.max(0, o.cd);
  o.pow = Math.round(o.pow * 100) / 100;
  return o;
}

// Thorns: damage dealt back to melee attackers (battle.js doubles it in brambles for the Briar Knight and Briar Boots).
export function thornsOf(u) {
  let v = 0;
  if (isClass(u, 'briarknight')) v += 8 + u.def * 0.5;
  if (has(u, 'thornmail')) v += 5 + u.def * 0.5;
  if (u.st && u.st.thorns > 0) v += 6 + u.def * 0.5;
  return Math.round(v);
}
export function statVal(u, stat) {
  let v = stat === 'missing' ? (u.maxHp - u.hp) * 0.6 + 3 : stat === 'heft' ? u.maxHp * 0.3 : stat === 'shield' ? (u.shield || 0) : stat === 'thorns' ? thornsOf(u) : u[stat];
  if (u.tmp && u.tmp[stat]) v += u.tmp[stat];
  return Math.max(0, v || 0);
}

// Damage multipliers from worn artifacts that always apply. Situational ones (Hermit's Lantern,
// Berserker's Torc and the like) only show up in the battle previews.
export const itemMult = u => (has(u, 'monocle') ? 1.5 : 1) * (has(u, 'crown') ? 1.4 : 1);
const isDmg = o => o.kind === 'phys' || o.kind === 'mag';
// Burn and poison a skill leaves, as battle.js applyStatus computes them: { turns, n (per turn) }.
export function burnOf(o, src) {
  const turns = o.burn || (isClass(src, 'pyromancer') && o.kind === 'mag' ? 2 : 0);
  if (!turns) return null;
  const ember = has(src, 'emberheart');
  return { turns: turns + (ember ? 2 : 0), n: Math.max(1, Math.round(statVal(src, o.stat) * 0.3 * (ember ? 1.5 : 1))), pct: ember ? 45 : 30 };
}
export function poisonOf(o, src) {
  if (!o.poison) return null;
  const pow = o.poisonPow || 0.3;
  return { turns: o.poison, n: Math.max(1, Math.round(statVal(src, o.stat) * pow)), pct: Math.round(pow * 100) };
}
// The headline numbers of a skill for src, e.g. "18 physical ×2, burn 4/turn for 2". Used for before/after.
export function outputOf(o, src) {
  const out = [];
  const n = Math.round(statVal(src, o.stat) * o.pow * (isDmg(o) ? itemMult(src) : 1));
  const times = o.times || (o.double ? 2 : 1);
  if (o.gravity) out.push(`${Math.round(o.gravity * 100)}% of current HP`);
  else if (isDmg(o)) out.push(`${n}${times > 1 ? ' ×' + times : ''} ${o.kind === 'mag' ? 'magic' : 'physical'}`);
  else if (o.kind === 'heal') out.push(`heals ${n}`);
  else if (o.kind === 'shield') out.push(`shields ${n}`);
  const b = burnOf(o, src), p = poisonOf(o, src);
  if (b) out.push(`burn ${b.n}/turn for ${b.turns}`);
  if (p) out.push(`poison ${p.n}/turn for ${p.turns}`);
  if (o.thornsUp && src) out.push(`thorns ${Math.round(6 + src.def * 0.5)}`);
  return out.join(', ');
}
const STAT_NAMES = { atk: 'ATK', mag: 'MAG', def: 'DEF', res: 'RES', spd: 'SPD', missing: 'missing HP', heft: '30% max HP', shield: 'shield', thorns: 'thorns' };
const RULES = { prime: 'Every foe whose HP is prime', even: 'Every unit with even HP', grid3: 'Every foe where row + column is a multiple of 3', poisoned: 'Every poisoned foe',
  odd: 'Every foe with odd HP', square: 'Every foe whose HP is a perfect square', fib: 'Every foe whose HP is a Fibonacci number', evenpos: 'Every ally on a "white" square (row + column even)',
  bramble: 'Every foe standing in brambles', all: 'Every foe on the board' };
const RULES_ALLY = { all: 'Every ally on the board', prime: 'Every ally whose HP is prime', evenpos: 'Every ally on a "white" square (row + column even)' };
// src (a battle unit or heroSrc()) adds the raw number the skill puts out, before the target's defenses.
export function describe(o, src) {
  const parts = [];
  const [a, b] = o.range;
  if (o.shape === 'random') parts.push('A random foe anywhere');
  else if (o.shape === 'math') parts.push(o.hits === 'allies' ? RULES_ALLY[o.rule] || RULES[o.rule] : o.hits === 'all' && o.rule === 'all' ? 'Every unit on the board' : RULES[o.rule]);
  else if (o.shape === 'coin') parts.push('Coin flip: every foe, or every ally');
  else if (o.mimic) parts.push('Copies the last skill an ally used');
  else if (o.shape === 'multi') parts.push(`${o.multiN} random foes within ${b}`);
  else if (o.tgt === 'self') parts.push(o.aoe ? `Around you, radius ${o.aoe}${o.diag ? ' (diagonals too)' : ''}` : 'Self');
  else parts.push(`${o.shape === 'line' ? 'Line, ' : ''}Range ${a === b ? a : a + '–' + b}`);
  if (o.aoe && o.tgt !== 'self') parts.push(`Area ${o.aoe}`);
  const n = src ? ` = ${Math.round(statVal(src, o.stat) * o.pow * (isDmg(o) ? itemMult(src) : 1))}` : '';
  const pct = `${Math.round(o.pow * 100)}% ${STAT_NAMES[o.stat]}${n}`;
  const times = o.times || (o.double ? 2 : 1);
  if (o.gravity) parts.push(`Takes ${Math.round(o.gravity * 100)}% of current HP (half on bosses)`);
  else if (o.kind === 'heal') parts.push(`Heals ${pct}`);
  else if (o.kind === 'shield') parts.push(`Shields ${pct}`);
  else if (o.kind === 'phys' || o.kind === 'mag') parts.push(`${pct} ${o.kind === 'mag' ? 'magic' : 'physical'}${times > 1 ? ' ×' + times : ''}`);
  if (o.shape === 'chain') parts.push(`Bounces ${o.chainN}×`);
  if (o.hits === 'all' && o.aoe) parts.push('Hits allies too');
  if (b > 1 && o.tgt !== 'self' && !o.lob && o.shape !== 'line') parts.push('Needs line of sight');
  const flags = [['stun', 'Stuns'], ['stunLow', 'Stuns if under half HP'], ['slow', 'Slows'], ['knock', 'Knockback'], ['pull', 'Pulls'],
    ['swap', 'Swaps places'], ['leap', 'Leaps in'], ['dash', 'Dashes'], ['teleport', 'Teleports'], ['taunt', 'Taunts'], ['rally', 'Rallies'], ['blind', 'Blinds'], ['execute', '×2 under half HP'],
    ['drain', 'Drains'], ['generous', 'Heals an ally'], ['vuln', 'Exposes'], ['terrain', 'Reshapes ground'], ['walls', 'Raises walls'], ['echo', 'May echo'],
    ['gamble', 'Random damage'], ['ctTake', 'Delays target'], ['ctGive', 'Hastes'], ['stealth', 'Stealth'], ['riposte', 'Riposte'], ['vortex', 'Pulls foes in'],
    ['selfShield', 'Shields you'], ['overflow', 'Overflow shields'], ['backstab', 'Backstab'], ['recoil', 'Hops away'],
    ['shock', 'Shocks'], ['charm', 'Charms'], ['doom', 'Dooms'], ['cdLock', 'Silences'], ['ward', 'Wards'], ['land', 'Jumps'],
    ['steal', 'Steals gold'], ['still', '+50% if you stayed put'], ['fester', '+15% per poison turn'], ['shatter', '+60% vs slowed'], ['bramble', '+60% vs brambled'],
    ['sanguine', '+1% per 1% HP missing'], ['leech', 'Poison heals you'], ['selfHaste', 'Hastes you'], ['brace', 'Braces'], ['guard', 'Guards'],
    ['root', 'Roots'], ['disarm', 'Disarms'], ['weak', 'Weakens'], ['oil', 'Oils'], ['wet', 'Soaks'], ['sleep', 'Sleep'], ['confuse', 'Confuses'], ['purify', 'Purifies'],
    ['dispel', 'Dispels'], ['movUp', '+1 MOV'], ['focus', 'Focus'], ['ctZero', 'Resets their turn'], ['pincer', '+40% per ally beside the target'], ['momentum', '+8% per tile away'],
    ['perDebuff', '+30% per debuff on the target'], ['recoilDmg', 'Hurts you too'], ['sure', 'Can\'t miss'], ['stealShield', 'Steals shields'], ['spread', 'Spreads debuffs'],
    ['trap', 'Lays traps'], ['onLava', '+60% vs targets on lava'], ['delay', 'Lands next turn'], ['counter', 'Readies a counter']];
  // damage over time, with its scaling and (given a source) the number per turn
  const sName = STAT_NAMES[o.stat];
  const burn = src ? burnOf(o, src) : o.burn ? { turns: o.burn, pct: 30 } : null;
  if (burn) parts.push(`Burns ${burn.turns} turns (${burn.pct}% ${sName}${src ? ` = ${burn.n}` : ''}/turn)${!o.burn ? ' from Ember Soul' : ''}`);
  const poison = src ? poisonOf(o, src) : o.poison ? { turns: o.poison, pct: Math.round((o.poisonPow || 0.3) * 100) } : null;
  if (poison) parts.push(`Poisons ${poison.turns} turns (${poison.pct}% ${sName}${src ? ` = ${poison.n}` : ''}/turn)${src && (isClass(src, 'plaguebringer') || has(src, 'toxicheart')) ? ', stacking' : ''}`);
  if (o.thornsUp) parts.push(`Grows thorns for ${o.thornsUp} turns (6 + 50% DEF${src && o.tgt === 'self' ? ` = ${Math.round(6 + src.def * 0.5)}` : ''})`);
  if (o.selfShield) parts.push(`Shields you for ${Math.round(o.selfShield * 100)}% of damage dealt`);
  if (o.drain) parts.push(`Heals you ${Math.round(o.drain * 100)}% of damage dealt`);
  for (const [k, label] of flags) if (o[k] && k !== 'drain' && k !== 'selfShield') parts.push(label);
  if (o.detonate) parts.push(`Detonates ${o.detonate === 'burn' ? 'burns' : 'poison'}`);
  if (o.push) parts.push(`Pushes ${o.push}`);
  if (o.cull) parts.push(`Kills under ${Math.round(o.cull * 100)}% HP`);
  if (o.imbue) parts.push(`Imbues ${o.imbue}`);
  if (o.kind === 'summon') parts.push(`Summons ${o.summonN || 2}`);
  if (o.hpCost) parts.push(`Costs ${Math.round(o.hpCost * 100)}% HP`);
  if (o.bloodpact) parts.push('Costs 10% HP');
  if (o.ctCost) parts.push('Delays your next turn');
  parts.push(o.cd ? `Cooldown ${o.cd}` : 'No cooldown');
  return parts.join(' · ');
}

// ---------- artifacts ----------
// Can skill artifact id go into skill s of hero p?
export function canSocket(p, s, id) {
  const m = MODS[id];
  if (!m || s.mods.length >= MAX_MODS) return false;
  if (m.only && m.only !== s.id) return false;
  if (!m.repeat && s.mods.includes(id)) return false;
  if (m.group && s.mods.some(x => MODS[x].group === m.group)) return false;
  return m.ok(skStats(p, s));
}
export const canWear = (p, id) => !!ITEMS[id] && p.items.length < MAX_RELICS;
// Would this skill artifact fit some skill in the party, ignoring full slots?
function fitsParty(party, id) {
  return party.some(p => p.skills.some(s => canSocket(p, s.mods.length < MAX_MODS ? s : { ...s, mods: s.mods.slice(0, MAX_MODS - 1) }, id)));
}
// The party's archetypes, from its classes and the artifacts it owns, with a weight for each.
export function partyArches(run) {
  const w = {};
  const add = (t, n) => { w[t] = (w[t] || 0) + n; };
  for (const p of run.party) {
    for (const t of CLASSES[p.cls].arch) add(t, 1);
    for (const c of p.line || []) for (const t of PROMOS[c].arch) add(t, 2);
  }
  for (const id of [...run.party.flatMap(p => [...p.items, ...p.skills.flatMap(s => s.mods)]), ...run.stash]) for (const t of artTags(id)) add(t, 1);
  return w;
}
// Shuffle that puts artifacts matching the party's archetypes first more often (weighted random order).
function leanShuffle(ids, arches) {
  const weight = id => 1 + Math.min(4, artTags(id).reduce((t, a) => t + (arches[a] || 0), 0)) * 0.6;
  return ids.map(id => ({ id, k: Math.random() ** (1 / weight(id)) })).sort((a, b) => b.k - a.k).map(e => e.id);
}
export function artifactPool(run, n, skillShare = 0.55, tag = null) {
  const owned = new Set([...run.party.flatMap(p => [...p.items, ...p.skills.flatMap(s => s.mods)]), ...run.stash]);
  const arches = partyArches(run), tagged = id => !tag || artTags(id).includes(tag);
  const skillArts = leanShuffle(Object.keys(MODS).filter(id => tagged(id) && (MODS[id].repeat || !owned.has(id)) && fitsParty(run.party, id)), arches);
  const heroArts = leanShuffle(Object.keys(ITEMS).filter(id => tagged(id) && !(ITEMS[id].unique && owned.has(id))), arches);
  const odd = heroArts.filter(id => ITEMS[id].unique), plain = heroArts.filter(id => !ITEMS[id].unique);
  const out = [];
  while (out.length < n && (skillArts.length || odd.length || plain.length)) {
    const from = (chance(skillShare) && skillArts.length) || (!odd.length && !plain.length) ? skillArts : chance(0.75) && odd.length ? odd : plain.length ? plain : odd;
    out.push(from.shift());
  }
  return out;
}

// ---------- skills ----------
export function skillPool(p) {
  const known = new Set(p.skills.map(s => s.id));
  const pool = [...CLASSES[p.cls].start, ...CLASSES[p.cls].pool, ...(p.line || []).flatMap(c => [PROMOS[c].skill, ...PROMOS[c].pool])];
  return pool.filter(id => !known.has(id));
}
// n offers of { hi, id } spread across the party.
export function skillOffers(party, n, onlyHero) {
  const per = party.map((p, hi) => onlyHero != null && hi !== onlyHero ? [] : shuffle(skillPool(p)).map(id => ({ hi, id })));
  const out = [];
  for (let round = 0; out.length < n && per.some(l => l.length); round++) {
    for (const hi of shuffle(per.map((_, i) => i))) if (per[hi].length && out.length < n) out.push(per[hi].shift());
  }
  return out;
}
export const skillsFull = p => p.skills.length >= MAX_SKILLS;

export const archName = t => ARCHES[t].name;
