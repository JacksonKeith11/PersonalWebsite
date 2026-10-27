// Rules shared by the battle and the menus: hero stats, skill stats after upgrades, descriptions.
import { CLASSES, PROMOS, SKILLS, UPGRADES, ITEMS, MAX_UPGRADES } from './data.js?v=2';

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

export function newHero(cls) {
  const c = CLASSES[cls];
  return { cls, promo: null, maxHp: c.hp, hp: c.hp, atk: c.atk, mag: c.mag, def: c.def, res: c.res, spd: c.spd, mov: c.mov, crit: c.crit, items: [],
    skills: c.skills.map(id => ({ id, ups: [] })) };
}

// Stats with items applied. gold feeds the Gold Tooth.
export function heroStats(p, gold = 0) {
  const o = { maxHp: p.maxHp, atk: p.atk, mag: p.mag, def: p.def, res: p.res, spd: p.spd, mov: p.mov, crit: p.crit };
  for (const id of p.items) for (const [k, v] of Object.entries(ITEMS[id].stats || {})) o[k] += v;
  if (p.items.includes('anklet')) o.maxHp = Math.round(o.maxHp * 0.75);
  if (p.items.includes('goldtooth')) { const b = Math.floor(gold / 100); o.atk += b; o.mag += b; }
  if (p.items.includes('swapstone')) [o.atk, o.mag] = [o.mag, o.atk];
  o.mov = Math.max(1, o.mov); o.spd = Math.max(1, o.spd);
  return o;
}

export function promote(p, id) {
  p.promo = id;
  const pr = PROMOS[id];
  for (const [k, v] of Object.entries(pr.stats)) { p[k] += v; if (k === 'maxHp') p.hp += v; }
  p.skills.push({ id: pr.skill, ups: [] });
}

// The skill as it stands after its upgrades and the holder's items.
export function skStats(u, s) {
  const d = SKILLS[s.id];
  const o = { ...d, id: s.id, range: [...d.range], ups: s.ups || [] };
  o.stat = d.stat || (d.kind === 'phys' ? 'atk' : 'mag');
  if (!o.hits) o.hits = o.kind === 'heal' || o.kind === 'shield' ? 'allies' : 'foes';
  for (const id of o.ups) UPGRADES[id].apply(o);
  if (has(u, 'scope') && o.range[1] > 1 && o.tgt !== 'self') o.range = [o.range[0], o.range[1] + 1];
  if (has(u, 'belt') && o.aoe) o.aoe += 1;
  if (has(u, 'hourglass') && o.cd > 1) o.cd -= 1;
  if (has(u, 'bloodpact') && o.cd > 0) { o.cd = 0; o.bloodpact = true; }
  o.cd = Math.max(0, o.cd);
  o.pow = Math.round(o.pow * 100) / 100;
  return o;
}

const STAT_NAMES = { atk: 'ATK', mag: 'MAG', def: 'DEF', res: 'RES', spd: 'SPD', missing: 'missing HP', heft: '30% max HP' };
export function describe(o) {
  const parts = [];
  const [a, b] = o.range;
  if (o.shape === 'random') parts.push('A random foe anywhere');
  else if (o.shape === 'multi') parts.push(`${o.multiN} random foes within ${b}`);
  else if (o.tgt === 'self') parts.push(o.aoe ? `Around you, radius ${o.aoe}${o.diag ? ' (diagonals too)' : ''}` : 'Self');
  else parts.push(`${o.shape === 'line' ? 'Line, ' : ''}Range ${a === b ? a : a + '–' + b}`);
  if (o.aoe && o.tgt !== 'self') parts.push(`Area ${o.aoe}`);
  const pct = `${Math.round(o.pow * 100)}% ${STAT_NAMES[o.stat]}`;
  if (o.kind === 'heal') parts.push(`Heals ${pct}`);
  else if (o.kind === 'shield') parts.push(`Shields ${pct}`);
  else if (o.kind === 'phys' || o.kind === 'mag') parts.push(`${pct}${o.kind === 'mag' && o.stat !== 'mag' ? ' (magic)' : o.kind === 'phys' && o.stat !== 'atk' ? ' (physical)' : ''}${o.double ? ' ×2' : ''}`);
  if (o.shape === 'chain') parts.push(`Bounces ${o.chainN}×`);
  if (o.hits === 'all' && o.aoe) parts.push('Hits allies too');
  if (o.ranged !== false && b > 1 && o.tgt !== 'self' && !o.lob) parts.push('Needs line of sight');
  const flags = [['stun', 'Stuns'], ['stunLow', 'Stuns if under half HP'], ['slow', 'Slows'], ['poison', 'Poisons'], ['burn', 'Burns'], ['knock', 'Knockback'], ['pull', 'Pulls'],
    ['swap', 'Swaps places'], ['leap', 'Leaps in'], ['dash', 'Dashes'], ['taunt', 'Taunts'], ['rally', 'Rallies'], ['blind', 'Blinds'], ['execute', '×2 under half HP'],
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

// Upgrades that could go on this skill right now.
export function upgradesFor(p, s) {
  if (s.ups.length >= MAX_UPGRADES) return [];
  const o = skStats(p, s);
  const groups = new Set(s.ups.map(id => UPGRADES[id].group).filter(Boolean));
  return Object.entries(UPGRADES).filter(([id, up]) => {
    if (up.only && up.only !== s.id) return false;
    if (!up.repeat && s.ups.includes(id)) return false;
    if (up.group && groups.has(up.group)) return false;
    return up.ok(o);
  }).map(([id]) => id);
}

// n offers across the party: { hi, si, up }, preferring different skills and a mix of plain and strange.
export function upgradeOffers(party, n, onlyHero) {
  const pool = [];
  party.forEach((p, hi) => {
    if (onlyHero != null && hi !== onlyHero) return;
    p.skills.forEach((s, si) => {
      for (const up of upgradesFor(p, s)) {
        const u = UPGRADES[up];
        pool.push({ hi, si, up, w: u.only ? 4 : u.repeat ? 1.2 : 1.6 });
      }
    });
  });
  const out = [];
  const used = new Set();
  while (out.length < n && pool.length) {
    const avail = pool.filter(c => !used.has(c.hi + ':' + c.si));
    const from = avail.length ? avail : pool;
    let r = Math.random() * from.reduce((t, c) => t + c.w, 0);
    const c = from.find(x => (r -= x.w) <= 0) || from[0];
    out.push(c);
    used.add(c.hi + ':' + c.si);
    pool.splice(pool.indexOf(c), 1);
    for (let i = pool.length - 1; i >= 0; i--) if (pool[i].hi === c.hi && pool[i].si === c.si && pool[i].up === c.up) pool.splice(i, 1);
  }
  return out;
}
