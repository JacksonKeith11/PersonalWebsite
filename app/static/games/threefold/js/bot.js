// The autopilot's choices outside battle (used only with ?auto): naive but synergy-minded. It
// stacks a hero's archetypes (shield and thorns on the tank, elemental and hex on the mage, poison
// and fortune on the rogue), puts skill artifacts where they add the most, learns stronger skills,
// rests when hurt and takes elites when healthy. Battles still use the enemy AI in battle.js.
import { CLASSES, PROMOS, MODS, ITEMS } from './data.js?v=41';
import { heroStats, heroSrc, skStats, statVal, canSocket, canWear, artTags, artPrice, itemMult } from './rules.js?v=41';

// What a hero leans toward: class archetypes count most, then what they already carry.
export function heroTags(p) {
  const w = {};
  const add = (t, n) => { w[t] = (w[t] || 0) + n; };
  for (const t of CLASSES[p.cls].arch) add(t, 2);
  for (const c of p.line || []) for (const t of PROMOS[c].arch) add(t, 3);
  for (const id of [...p.items, ...p.skills.flatMap(s => s.mods)]) for (const t of artTags(id)) add(t, 1);
  return w;
}
const ROLE = { warrior: 'tank', mage: 'caster', rogue: 'striker' };
const STAT_W = {
  tank: { maxHp: 0.5, def: 2.5, res: 1.5, atk: 1.2, mag: 0, spd: 1.5, mov: 4, crit: 0.2 },
  caster: { maxHp: 0.4, def: 0.8, res: 1.2, atk: 0, mag: 2.5, spd: 1.8, mov: 4, crit: 0.2 },
  striker: { maxHp: 0.4, def: 0.8, res: 0.6, atk: 2.5, mag: 0, spd: 2.2, mov: 4, crit: 0.6 },
};
const tagFit = (p, id) => artTags(id).reduce((t, a) => t + (heroTags(p)[a] || 0), 0);

// A rough worth for a skill as hero p would use it: damage per turn, spread over cooldown, with
// bonuses for areas and control; heals and shields count for less, other buffs a flat amount.
export function skillValue(p, s) {
  const o = skStats(p, s), src = heroSrc(p, 0);
  const pace = 1 / (1 + (o.cd || 0) * 0.35);
  if (o.kind === 'phys' || o.kind === 'mag') {
    const times = o.times || (o.double ? 2 : 1) * (o.shape === 'multi' ? o.multiN || 3 : 1);
    const spread = o.aoe ? 1 + o.aoe * 0.8 : o.shape === 'line' || o.shape === 'chain' ? 1.6 : 1;
    let v = statVal(src, o.stat) * o.pow * times * spread * itemMult(src);
    if (o.stun) v += 6; if (o.slow || o.root) v += 2; if (o.poison || o.burn) v += 3; if (o.range[1] > 1) v *= 1.15;
    return v * pace;
  }
  if (o.kind === 'heal' || o.kind === 'shield') return statVal(src, o.stat) * o.pow * 0.7 * pace * (o.aoe ? 1.6 : 1);
  if (o.kind === 'summon') return 8 * pace;
  return 6 * pace;
}

// How much hero p gains from artifact id, and on which skill for a skill artifact.
export function placement(p, id) {
  if (MODS[id]) {
    let best = null;
    for (const s of p.skills) {
      if (!canSocket(p, s, id)) continue;
      const gain = skillValue(p, { ...s, mods: [...s.mods, id] }) - skillValue(p, s);
      const sc = gain * 1.5 + tagFit(p, id) * 3 + artPrice(id) / 20;
      if (!best || sc > best.score) best = { p, s, score: sc };
    }
    return best;
  }
  if (!canWear(p, id)) return null;
  const st0 = heroStats(p), st1 = heroStats({ ...p, items: [...p.items, id] }), w = STAT_W[ROLE[p.cls]];
  let sc = Object.keys(w).reduce((t, k) => t + (st1[k] - st0[k]) * w[k], 0);
  const gain = p.skills.reduce((t, s) => t + skillValue({ ...p, items: [...p.items, id] }, s) - skillValue(p, s), 0);
  sc += gain + tagFit(p, id) * 3 + (ITEMS[id].stats ? 0 : artPrice(id) / 10) - (ITEMS[id].down ? 2 : 0);
  return { p, score: sc };
}
export const bestPlacement = (party, id) => party.map(p => placement(p, id)).filter(Boolean).sort((a, b) => b.score - a.score)[0] || null;
// The best artifact among the offers, by its best placement.
export const pickArtifact = (party, ids) => ids.map(id => ({ id, pl: bestPlacement(party, id) })).filter(x => x.pl).sort((a, b) => b.pl.score - a.pl.score)[0] || null;

// Learning: the offer with the biggest gain, forgetting the weakest skill once full.
export function pickLesson(party, offers, max) {
  let best = null;
  for (const c of offers) {
    const p = party[c.hi], v = skillValue(p, { id: c.id, mods: [] });
    const weakest = p.skills.length >= max ? Math.min(...p.skills.map(s => skillValue(p, s) + s.mods.length * 4)) : 0;
    const gain = v - weakest;
    if (gain > 0 && (!best || gain > best.gain)) best = { ...c, gain };
  }
  return best;
}
export const weakestSkill = p => p.skills.map((s, i) => ({ i, v: skillValue(p, s) + s.mods.length * 4 })).sort((a, b) => a.v - b.v)[0].i;
// Promotion: the class whose archetypes match what the hero already leans toward.
// (a coin flip a third of the time, so balance runs see every class)
export const pickClass = (p, opts) => Math.random() < 0.35 ? opts[Math.floor(Math.random() * opts.length)] : opts.map(id => ({ id, v: PROMOS[id].arch.reduce((t, a) => t + (heroTags(p)[a] || 0), 0) + Math.random() })).sort((a, b) => b.v - a.v)[0].id;
// Team artifacts, best first by a fixed judgement of their power.
const TEAM_RANK = ['glasscrown', 'warhorn', 'overclock', 'phalanx', 'echostone', 'bloodoath', 'aegis', 'kingsglass', 'lichbargain', 'warbanner', 'packtotem', 'leaden', 'goldfever'];
export const pickTeam = ids => [...ids].sort((a, b) => TEAM_RANK.indexOf(a) - TEAM_RANK.indexOf(b))[0];
// The map: rest when hurt, take elites when healthy, otherwise fight for experience.
export function pickNode(party, opts, gold) {
  const hp = party.reduce((t, p) => t + p.hp / heroStats(p, gold).maxHp, 0) / party.length;
  const pref = hp < 0.45 ? ['rest', 'shop', 'event', 'battle', 'elite'] : hp < 0.7 ? ['rest', 'battle', 'event', 'shop', 'elite'] : ['elite', 'battle', 'shop', 'event', 'rest'];
  return [...opts].sort((a, b) => pref.indexOf(a.type) - pref.indexOf(b.type))[0];
}
export const partyHp = (party, gold) => party.reduce((t, p) => t + p.hp / heroStats(p, gold).maxHp, 0) / party.length;
