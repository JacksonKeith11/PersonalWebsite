// Rules shared by the battle and the menus: hero stats, skill stats after artifacts, descriptions, reward pools.
import { CLASSES, PROMOS, SKILLS, MODS, ITEMS, MAX_MODS, MAX_SKILLS, MAX_RELICS } from './data.js?v=3';

export const rnd = (a, b) => a + Math.floor(Math.random() * (b - a + 1));
export const pick = a => a[Math.floor(Math.random() * a.length)];
export const chance = p => Math.random() < p;
export function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

export const has = (u, id) => !!(u.items && u.items.includes(id));
export const heroSprite = p => p.promo || p.cls;
export const heroTitle = p => p.promo ? PROMOS[p.promo].name : CLASSES[p.cls].name;
export const isSkillArt = id => !!MODS[id];
export const artName = id => (MODS[id] || ITEMS[id]).name;
export const artText = id => MODS[id] ? MODS[id].note : ITEMS[id].txt;
export const artPrice = id => (MODS[id] || ITEMS[id]).price;

export function newHero(cls) {
  const c = CLASSES[cls];
  return { cls, promo: null, maxHp: c.hp, hp: c.hp, atk: c.atk, mag: c.mag, def: c.def, res: c.res, spd: c.spd, mov: c.mov, crit: c.crit, items: [],
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
// What describe() and the damage numbers read stats from, for a hero outside battle.
export const heroSrc = (p, gold) => ({ ...heroStats(p, gold), hp: p.hp, items: p.items });

export function promote(p, id) {
  p.promo = id;
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
  o.cd = Math.max(0, o.cd);
  o.pow = Math.round(o.pow * 100) / 100;
  return o;
}

export function statVal(u, stat) {
  let v = stat === 'missing' ? (u.maxHp - u.hp) * 0.6 + 3 : stat === 'heft' ? u.maxHp * 0.3 : u[stat];
  if (u.tmp && u.tmp[stat]) v += u.tmp[stat];
  return Math.max(0, v || 0);
}

const STAT_NAMES = { atk: 'ATK', mag: 'MAG', def: 'DEF', res: 'RES', spd: 'SPD', missing: 'missing HP', heft: '30% max HP' };
// src (a battle unit or heroSrc()) adds the raw number the skill puts out, before the target's defenses.
export function describe(o, src) {
  const parts = [];
  const [a, b] = o.range;
  if (o.shape === 'random') parts.push('A random foe anywhere');
  else if (o.shape === 'multi') parts.push(`${o.multiN} random foes within ${b}`);
  else if (o.tgt === 'self') parts.push(o.aoe ? `Around you, radius ${o.aoe}${o.diag ? ' (diagonals too)' : ''}` : 'Self');
  else parts.push(`${o.shape === 'line' ? 'Line, ' : ''}Range ${a === b ? a : a + '–' + b}`);
  if (o.aoe && o.tgt !== 'self') parts.push(`Area ${o.aoe}`);
  const n = src ? ` = ${Math.round(statVal(src, o.stat) * o.pow)}` : '';
  const pct = `${Math.round(o.pow * 100)}% ${STAT_NAMES[o.stat]}${n}`;
  const times = o.times || (o.double ? 2 : 1);
  if (o.kind === 'heal') parts.push(`Heals ${pct}`);
  else if (o.kind === 'shield') parts.push(`Shields ${pct}`);
  else if (o.kind === 'phys' || o.kind === 'mag') parts.push(`${pct} ${o.kind === 'mag' ? 'magic' : 'physical'}${times > 1 ? ' ×' + times : ''}`);
  if (o.shape === 'chain') parts.push(`Bounces ${o.chainN}×`);
  if (o.hits === 'all' && o.aoe) parts.push('Hits allies too');
  if (b > 1 && o.tgt !== 'self' && !o.lob && o.shape !== 'line') parts.push('Needs line of sight');
  const flags = [['stun', 'Stuns'], ['stunLow', 'Stuns if under half HP'], ['slow', 'Slows'], ['poison', 'Poisons'], ['burn', 'Burns'], ['knock', 'Knockback'], ['pull', 'Pulls'],
    ['swap', 'Swaps places'], ['leap', 'Leaps in'], ['dash', 'Dashes'], ['teleport', 'Teleports'], ['taunt', 'Taunts'], ['rally', 'Rallies'], ['blind', 'Blinds'], ['execute', '×2 under half HP'],
    ['drain', 'Drains'], ['generous', 'Heals an ally'], ['vuln', 'Exposes'], ['terrain', 'Reshapes ground'], ['walls', 'Raises walls'], ['echo', 'May echo'],
    ['gamble', 'Random damage'], ['ctTake', 'Delays target'], ['ctGive', 'Hastes'], ['stealth', 'Stealth'], ['riposte', 'Riposte'], ['vortex', 'Pulls foes in'],
    ['selfShield', 'Shields you'], ['overflow', 'Overflow shields'], ['backstab', 'Backstab'], ['recoil', 'Hops away']];
  for (const [k, label] of flags) if (o[k]) parts.push(label);
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
export function artifactPool(run, n, skillShare = 0.55) {
  const owned = new Set([...run.party.flatMap(p => [...p.items, ...p.skills.flatMap(s => s.mods)]), ...run.stash]);
  const skillArts = shuffle(Object.keys(MODS).filter(id => (MODS[id].repeat || !owned.has(id)) && fitsParty(run.party, id)));
  const heroArts = shuffle(Object.keys(ITEMS).filter(id => !(ITEMS[id].unique && owned.has(id))));
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
  const pool = [...CLASSES[p.cls].start, ...CLASSES[p.cls].pool, ...(p.promo ? [PROMOS[p.promo].skill, ...PROMOS[p.promo].pool] : [])];
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
