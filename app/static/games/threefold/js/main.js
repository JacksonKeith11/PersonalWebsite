// Threefold Path: run flow, menus, events, shops and saving. Phaser draws the map and battles;
// everything text-heavy is plain HTML in #side and #screen.
import { GW, GH, ROWS_PER_ACT, ACTS, ACT_SLOTS, CLASSES, PROMOS, SKILLS, MODS, ITEMS, ARCHES, MAX_SKILLS, MAX_MODS, MAX_RELICS } from './data.js?v=23';
import { rnd, pick, chance, shuffle, newHero, heroStats, heroSrc, heroSprite, heroTitle, promote, skStats, describe,
  isSkillArt, artName, artText, artPrice, artTags, outputOf, levelUp, gainsText, growthText, growthClass, nextBreakpoint, canSocket, canWear, artifactPool, skillPool, skillOffers, skillsFull, promoOptions, partyArches } from './rules.js?v=23';
import { buildTextures, iconCanvas, NODE_COLORS } from './art.js?v=23';
import { initAudio, sfx, music, audioState, toggleMusic, toggleSfx } from './audio.js?v=23';
import { env, startBattle, BattleScene } from './battle.js?v=23';
import { MapScene, mapEnv, mapHeight } from './mapscene.js?v=23';
import { h, sprImg, bar, skillText, initTips } from './ui.js?v=23';

const params = new URLSearchParams(location.search);
const AUTO = params.has('auto'); // heroes play themselves; used to test balance
const SAVE_KEY = 'threefold-path-run-v4';
const TS = 64;

const $ = id => document.getElementById(id);
const stage = $('stage'), side = $('side'), screen = $('screen'), modal = $('modal');
env.side = side;
env.auto = AUTO;
// Battle speed: 1x, 2x or 3x animations, remembered between visits.
let SPEED = 1;
try { SPEED = Math.min(3, Math.max(1, +localStorage.getItem('threefold-speed') || 1)); } catch (e) { /* storage unavailable */ }
env.speed = AUTO ? 0.01 : 1 / SPEED;

let run = null;
let game = null;

// ---------- layout ----------
function showStage(scene, sideKids) {
  screen.hidden = true; screen.replaceChildren();
  stage.hidden = false;
  side.replaceChildren(...(sideKids || []));
  for (const k of ['map', 'battle']) if (k !== scene && game.scene.isActive(k)) game.scene.stop(k);
  document.body.classList.toggle('in-battle', scene === 'battle');
  // the canvas was display:none; Phaser has to re-measure its parent or it stays 0px wide
  game.scale.getParentBounds();
  game.scale.refresh();
  window.scrollTo(0, 0);
}
function setScreen(...kids) {
  for (const k of ['map', 'battle']) if (game.scene.isActive(k)) game.scene.stop(k);
  stage.hidden = true;
  document.body.classList.remove('in-battle');
  screen.hidden = false;
  screen.replaceChildren(...kids);
  window.scrollTo(0, 0);
}
const auto = fn => { if (AUTO) setTimeout(fn, 5); };
const btn = (label, onclick, cls = '', disabled = false) => h('button', { class: 'btn ' + cls, disabled, onclick: e => { sfx('click'); onclick(e); } }, label);

function hud(inBattle) {
  const el = $('hud');
  const a = audioState();
  const small = window.innerWidth <= 640; // phones get short labels so the HUD stays on two rows
  const audio = [
    h('button', { class: 'btn tiny', title: 'Music', onclick: () => { toggleMusic(); hud(inBattle); } }, small ? (a.music ? '♪ on' : '♪ off') : a.music ? 'Music on' : 'Music off'),
    h('button', { class: 'btn tiny', title: 'Sound effects', onclick: () => { toggleSfx(); hud(inBattle); } }, small ? (a.sfx ? 'SFX on' : 'SFX off') : a.sfx ? 'Sound on' : 'Sound off'),
  ];
  if (inBattle && !AUTO) audio.unshift(h('button', { class: 'btn tiny', title: 'Battle animation speed', onclick: () => {
    SPEED = SPEED % 3 + 1;
    env.speed = 1 / SPEED;
    try { localStorage.setItem('threefold-speed', SPEED); } catch (e) { /* storage unavailable */ }
    hud(inBattle);
  } }, small ? `${SPEED}×` : `Speed ${SPEED}×`));
  if (!run) { el.replaceChildren(...audio); return; }
  const floor = run.pos === 'boss' ? ROWS_PER_ACT + 1 : run.pos ? run.map[run.pos].r + 1 : 1;
  el.replaceChildren(
    h('span', { class: 'hud-item' }, `Act ${run.act + 1} `, h('b', {}, `${floor}/${ROWS_PER_ACT + 1}`)),
    h('span', { class: 'hud-item' }, 'Gold ', h('b', {}, run.gold)),
    ...run.party.map(p => h('span', { class: 'hud-hero', title: heroTitle(p) }, sprImg(heroSprite(p)), `${p.hp}/${heroStats(p, run.gold).maxHp}`)),
    ...(inBattle ? [] : [h('button', { class: 'btn tiny', onclick: showParty }, 'Party')]),
    ...audio,
  );
}

// ---------- saving ----------
function save() { try { localStorage.setItem(SAVE_KEY, JSON.stringify(run)); } catch (e) { /* storage unavailable */ } }
function load() { try { const s = localStorage.getItem(SAVE_KEY); return s ? JSON.parse(s) : null; } catch (e) { return null; } }
function clearSave() { try { localStorage.removeItem(SAVE_KEY); } catch (e) { /* storage unavailable */ } }

// ---------- run ----------
function genMap() {
  const nodes = {}, edges = new Set(), COLS = 6, R = ROWS_PER_ACT;
  const node = (r, c) => nodes[r + ':' + c] ||= { id: r + ':' + c, r, c, type: null, next: [], jx: rnd(-10, 10), jy: rnd(-8, 8) };
  const starts = shuffle([0, 1, 2, 3, 4, 5]);
  for (let p = 0; p < 6; p++) {
    let c = p < 3 ? starts[p] : pick(starts.slice(0, 3));
    node(0, c);
    for (let r = 0; r < R - 1; r++) {
      const opts = [c - 1, c, c + 1].filter(n => n >= 0 && n < COLS &&
        !(n === c + 1 && edges.has(`${r}:${c + 1}>${r + 1}:${c}`)) && !(n === c - 1 && edges.has(`${r}:${c - 1}>${r + 1}:${c}`)));
      const n = pick(opts), e = `${r}:${c}>${r + 1}:${n}`;
      if (!edges.has(e)) { edges.add(e); node(r, c).next.push(node(r + 1, n).id); }
      c = n;
    }
  }
  for (const n of Object.values(nodes)) {
    if (n.r === R - 1) { n.next.push('boss'); n.type = 'shop'; continue; }
    if (n.r === 0) { n.type = 'battle'; continue; }
    const roll = Math.random();
    n.type = n.r >= 3 && roll < 0.17 ? 'elite' : n.r >= 2 && roll < 0.31 ? 'shop' : roll < 0.58 ? 'event' : 'battle';
  }
  nodes.boss = { id: 'boss', r: R, c: 2, type: 'boss', next: [], jx: 0, jy: 0 };
  return nodes;
}
function newRun() {
  run = { party: ['warrior', 'mage', 'rogue'].map(newHero), gold: 60, act: 0, acts: ACT_SLOTS.map(slot => pick(slot)), map: genMap(), pos: null, visited: [], seen: [], stash: [], stats: { kills: 0, battles: 0 } };
  env.run = run;
  if (AUTO && params.has('chaos')) {
    // stress test: promoted heroes with four random skills, every slot filled with random artifacts
    const odd = shuffle(Object.keys(ITEMS).filter(id => ITEMS[id].unique));
    run.party.forEach((p, i) => {
      promote(p, pick(promoOptions(p)));
      promote(p, pick(promoOptions(p)));
      p.skills = shuffle(skillPool(p).concat(p.skills.map(s => s.id))).slice(0, MAX_SKILLS).map(id => ({ id, mods: [] }));
      for (const s of p.skills) for (const id of shuffle(Object.keys(MODS))) if (canSocket(p, s, id)) s.mods.push(id);
      p.items.push(...odd.slice(i * MAX_RELICS, (i + 1) * MAX_RELICS));
      p.hp = heroStats(p, run.gold).maxHp;
    });
  }
  actIntro();
}
// This run's act: one of the two in each slot, drawn when the run starts (older saves get the first).
const curAct = () => ACTS[(run.acts || ACT_SLOTS.map(s => s[0]))[run.act]];
const available = () => !run.pos ? Object.values(run.map).filter(n => n.r === 0) : run.map[run.pos].next.map(id => run.map[id]);
const level = n => run.act * (ROWS_PER_ACT + 1) + (n.id === 'boss' ? ROWS_PER_ACT + 1 : n.r + 1);
const hurtAll = n => run.party.forEach(p => { p.hp = Math.max(1, p.hp - n); });
const healAll = f => run.party.forEach(p => { const m = heroStats(p, run.gold).maxHp; p.hp = Math.min(m, p.hp + Math.round(m * f)); });

function actIntro() {
  const act = curAct();
  hud();
  music('m_map');
  setScreen(h('div', { class: 'panel center' },
    h('div', { class: 'title-name' }, `Act ${run.act + 1}`),
    h('h2', {}, act.name),
    h('p', {}, act.intro),
    btn('Begin', showMap, 'big go'),
  ));
  auto(showMap);
}

// ---------- map ----------
function showMap() {
  save();
  hud();
  music('m_map');
  const legend = h('div', { class: 'panel legend' }, h('h3', {}, curAct().name),
    ...['battle', 'elite', 'event', 'shop', 'boss'].map(t => {
      const c = h('canvas', { width: 24, height: 24 });
      const x = c.getContext('2d');
      x.imageSmoothingEnabled = false;
      x.fillStyle = NODE_COLORS[t]; x.fillRect(0, 0, 24, 24);
      x.drawImage(iconCanvas(t), 4, 4, 16, 16);
      return h('div', {}, c, t === 'boss' ? curAct().boss : { battle: 'Battle', elite: 'Elite battle (two artifacts)', event: 'Unknown event', shop: 'Shop (rest, lessons, artifacts)' }[t]);
    }),
    h('p', { class: 'muted' }, 'Pick a glowing node. Drag or scroll the map to look ahead. Healing is rare: wounds carry between fights, and only a new act restores everyone fully.'));
  showStage('map', [legend]);
  Object.assign(mapEnv, { run, available, pick: enterNode, actName: `Act ${run.act + 1}: ${curAct().name}`, theme: curAct().theme, leader: heroSprite(run.party[0]) });
  game.scene.start('map');
  auto(() => {
    const opts = available(), low = run.party.some(p => p.hp < heroStats(p, run.gold).maxHp * 0.45);
    enterNode((low && opts.find(n => n.type === 'shop' || n.type === 'event')) || pick(opts));
  });
}
function enterNode(n) {
  sfx('select');
  run.pos = n.id;
  run.visited.push(n.id);
  if (n.type === 'battle') battle('normal');
  else if (n.type === 'elite') battle('elite');
  else if (n.type === 'boss') battle('boss');
  else if (n.type === 'event') showEvent();
  else showShop(n);
}

// ---------- battle ----------
function battle(kind) {
  const act = curAct(), n = run.map[run.pos];
  const lvl = level(n);
  const list = kind === 'boss' ? act.bossParty : kind === 'elite' ? pick(act.elite) : pick(n.r < 4 ? act.early : act.late);
  hud(true);
  music(kind === 'boss' ? 'm_boss' : act.music);
  showStage('battle');
  startBattle({ kind, level: lvl, act, list, party: run.party });
}
env.onEnd = (b, win) => {
  if (AUTO) (window.__log ||= []).push({ act: run.act + 1, kind: b.kind, lvl: b.level, win, heroes: b.units.filter(u => u.ref).map(u => u.dead ? 0 : u.hp).join('/'),
    foes: win ? '' : b.units.filter(u => u.side === 'foe' && !u.dead).map(u => `${u.name}:${u.hp}`).join(' ') });
  if (!win) { gameOver(); return; }
  const levels = [];
  for (const u of b.units) {
    if (!u.ref) continue;
    const p = u.ref;
    const gains = levelUp(p);
    levels.push({ p, gains });
    // no healing after a fight: wounds carry over (the new max HP comes filled), and the fallen get up with 10% HP
    p.hp = u.dead ? Math.ceil(heroStats(p, run.gold).maxHp * 0.1) : Math.min(u.hp + (gains.maxHp || 0), heroStats(p, run.gold).maxHp);
  }
  run.stats.battles++;
  const tooth = run.party.some(p => p.items.includes('goldtooth')) ? 1.4 : 1;
  const base = b.kind === 'boss' ? rnd(90, 110) : b.kind === 'elite' ? rnd(55, 70) + b.level * 3 : rnd(20, 30) + b.level * 2;
  showRewards({ gold: Math.round(base * tooth), kind: b.kind, levels });
};

// ---------- cards ----------
const archChips = tags => tags.length ? h('span', { class: 'chips' }, tags.map(t => h('span', { class: 'chip', style: `--c:${ARCHES[t].color}` }, ARCHES[t].name))) : null;
const modalShow = el => { modal.replaceChildren(h('div', { class: 'modal-box' }, el)); modal.hidden = false; };
// "Fits: Strike, Cleave (Warrior) · Arcane Bolt (Mage)": the party's skills a skill artifact could go
// into. A full skill still counts, since an artifact can be moved off it.
function fitsLine(id) {
  const groups = run.party.map(p => ({ p, names: p.skills.filter(s => canSocket(p, s.mods.length < MAX_MODS ? s : { ...s, mods: s.mods.slice(0, MAX_MODS - 1) }, id)).map(s => SKILLS[s.id].name) }))
    .filter(g => g.names.length);
  if (!groups.length) return h('div', { class: 'fits none' }, 'Fits none of your skills right now.');
  return h('div', { class: 'fits' }, 'Fits: ', groups.map(g => `${g.names.join(', ')} (${heroTitle(g.p)})`).join(' · '));
}
function artCard(id, extra, onpick, disabled) {
  const skill = isSkillArt(id);
  return h('button', { class: 'pick ' + (skill ? 'skillart' : 'heroart'), disabled, onclick: () => { sfx('select'); onpick(); } },
    h('div', { class: 'pick-head' }, h('b', {}, artName(id)), extra),
    h('div', { class: 'kind' }, skill ? (MODS[id].only ? `Skill artifact · ${SKILLS[MODS[id].only].name} only` : 'Skill artifact') : 'Hero artifact', archChips(artTags(id))),
    h('div', { class: 'desc' }, artText(id)),
    skill && run ? fitsLine(id) : null);
}
function skillCard(p, id, extra, onpick, disabled) {
  const o = skStats(p, { id, mods: [] });
  return h('button', { class: 'pick', disabled, onclick: () => { sfx('select'); onpick(); } },
    h('div', { class: 'pick-head' }, sprImg(heroSprite(p)), h('b', {}, o.name), extra),
    h('div', { class: 'kind' }, `${heroTitle(p)} skill`),
    h('div', { class: 'desc' }, skillText(o, heroSrc(p, run.gold))));
}

// Put an artifact on a hero or a skill, or in the pack. show() is setScreen or modalShow.
// back, if given, returns to the screen the artifact was chosen on, with nothing taken or spent.
function equipFlow(id, next, show = setScreen, back = null) {
  const backBtn = () => back ? btn('Back', back) : null;
  const keep = () => { run.stash.push(id); next(); };
  hud();
  if (isSkillArt(id)) {
    const targets = [];
    run.party.forEach(p => p.skills.forEach(s => targets.push({ p, s, ok: canSocket(p, s, id) })));
    const socket = t => { t.s.mods.push(id); sfx('shield'); next(); };
    show(h('div', { class: 'panel' },
      h('h2', {}, `Socket the ${artName(id)}`), h('p', { class: 'muted' }, `${artText(id).replace(/\.$/, '')}. Each skill holds ${MAX_MODS}. You can move it later from the Party screen.`),
      h('div', { class: 'cards' }, targets.map(t => {
        const after = t.ok ? skStats(t.p, { ...t.s, mods: [...t.s.mods, id] }) : null;
        const src = heroSrc(t.p, run.gold), a = outputOf(skStats(t.p, t.s), src), b = after ? outputOf(after, src) : '';
        return h('button', { class: 'pick', disabled: !t.ok, onclick: () => socket(t) },
          h('div', { class: 'pick-head' }, sprImg(heroSprite(t.p)), h('b', {}, SKILLS[t.s.id].name)),
          t.s.mods.length ? h('div', { class: 'kind' }, t.s.mods.map(artName).join(', ')) : null,
          after && a !== b ? delta('', a, b) : null,
          h('div', { class: 'desc' }, after ? skillText({ ...after, txt: '' }, heroSrc(t.p, run.gold)) : t.s.mods.length >= MAX_MODS ? 'No free slot' : 'Doesn\'t fit this skill'));
      })),
      btn('Keep in pack', keep), backBtn()));
    auto(() => { const t = targets.find(t => t.ok); if (t) socket(t); else keep(); });
  } else {
    const wear = p => { p.items.push(id); const it = ITEMS[id]; if (it.stats && it.stats.maxHp > 0) p.hp += it.stats.maxHp; clampHp(); sfx('coin'); next(); };
    show(h('div', { class: 'panel' },
      h('h2', {}, `Who wears the ${artName(id)}?`), h('p', { class: 'muted' }, `${artText(id).replace(/\.$/, '')}. Each hero wears ${MAX_RELICS}.`),
      h('div', { class: 'cards' }, run.party.map(p => h('button', { class: 'pick', disabled: !canWear(p, id), onclick: () => wear(p) },
        h('div', { class: 'pick-head' }, sprImg(heroSprite(p)), h('b', {}, heroTitle(p))),
        h('div', { class: 'desc' }, p.items.length ? `Wearing ${p.items.map(artName).join(', ')}` : 'Nothing worn yet'),
        ...(canWear(p, id) ? wearPreview(p, id) : [])))),
      btn('Keep in pack', keep), backBtn()));
    auto(() => { const p = run.party.find(p => canWear(p, id)); if (p) wear(p); else keep(); });
  }
}
// "Strike: 12 physical → 15 physical" lines for what an artifact would change.
const delta = (label, a, b) => h('div', { class: 'delta' }, label ? h('b', { class: 'inline' }, label + ': ') : null, h('span', { class: 'was' }, a || 'nothing'), ' → ', h('span', { class: 'now' }, b || 'nothing'));
function wearPreview(p, id) {
  const w = { ...p, items: [...p.items, id] };
  const st0 = heroStats(p, run.gold), st1 = heroStats(w, run.gold);
  const src0 = heroSrc(p, run.gold), src1 = heroSrc(w, run.gold);
  const names = { maxHp: 'max HP', atk: 'ATK', mag: 'MAG', def: 'DEF', res: 'RES', spd: 'SPD', mov: 'MOV', crit: 'CRIT' };
  const stats = Object.keys(names).filter(k => st0[k] !== st1[k]).map(k => `${names[k]} ${st0[k]} → ${st1[k]}`);
  const skills = p.skills.map(s => ({ s, a: outputOf(skStats(p, s), src0), b: outputOf(skStats(w, s), src1), d0: describe(skStats(p, s), src0), d1: describe(skStats(w, s), src1) }))
    .filter(x => x.a !== x.b || x.d0 !== x.d1);
  return [
    stats.length ? h('div', { class: 'delta' }, stats.join(' · ')) : null,
    ...skills.map(x => x.a !== x.b ? delta(SKILLS[x.s.id].name, x.a, x.b) : h('div', { class: 'delta' }, h('b', { class: 'inline' }, SKILLS[x.s.id].name + ': '), describe(skStats(w, x.s), src1))),
    !stats.length && !skills.length ? h('div', { class: 'desc dim' }, 'No change to stats or skill numbers; it works in battle.') : null,
  ];
}
const clampHp = () => run.party.forEach(p => { p.hp = Math.min(p.hp, heroStats(p, run.gold).maxHp); });

// Teach hero hi skill id; at MAX_SKILLS they forget one (its artifacts go to the pack).
// back, if given, returns to the offers so another hero's skill can be picked instead.
function learnFlow(hi, id, next, show = setScreen, back = null) {
  const p = run.party[hi];
  if (!skillsFull(p)) { p.skills.push({ id, mods: [] }); sfx('buff'); next(); return; }
  const forget = i => { run.stash.push(...p.skills[i].mods); p.skills[i] = { id, mods: [] }; sfx('buff'); next(); };
  show(h('div', { class: 'panel' },
    h('h2', {}, `The ${heroTitle(p)} can only know ${MAX_SKILLS} skills`), h('p', {}, `Forget one to learn ${SKILLS[id].name}? Its artifacts go to your pack.`),
    h('div', { class: 'cards' }, skillCard(p, id, h('span', { class: 'price' }, 'New'), () => {}, true)),
    h('h3', {}, 'Forget'),
    h('div', { class: 'cards' }, p.skills.map((s, i) => skillCard(p, s.id, s.mods.length ? h('span', { class: 'price' }, `${s.mods.length} art.`) : null, () => forget(i)))),
    back ? btn('Back: choose a different skill', back) : btn(`Don't learn ${SKILLS[id].name}`, next)));
  auto(() => chance(0.5) ? forget(rnd(0, p.skills.length - 1)) : next());
}

// ---------- rewards, promotion, acts ----------
function showRewards(info) {
  run.gold += info.gold;
  hud();
  sfx('coin');
  const picks = info.kind === 'elite' ? 2 : 1;
  let offers = artifactPool(run, info.kind === 'normal' ? 3 : 4);
  let taken = 0;
  const after = () => {
    if (info.kind === 'boss') { if (run.act >= ACT_SLOTS.length - 1) victory(); else promotionScreen(nextAct); return; }
    showMap();
  };
  let opts = null;
  const learn = () => {
    opts ||= skillOffers(run.party, 3);
    if (!opts.length) { after(); return; }
    setScreen(h('div', { class: 'panel' },
      h('h2', {}, 'Learn a new skill?'), h('p', { class: 'muted' }, `Each hero can know ${MAX_SKILLS} skills.`),
      h('div', { class: 'cards' }, opts.map(c => skillCard(run.party[c.hi], c.id, skillsFull(run.party[c.hi]) ? h('span', { class: 'price' }, 'Replaces one') : null,
        () => learnFlow(c.hi, c.id, after, setScreen, learn)))),
      btn('Skip', after)));
    auto(() => learnFlow(opts[0].hi, opts[0].id, after));
  };
  const spoils = () => {
    if (taken >= picks || !offers.length) { learn(); return; }
    setScreen(h('div', { class: 'panel' },
      h('h2', {}, taken ? 'Take one more' : info.kind === 'boss' ? `${curAct().boss} is defeated!` : 'Victory!'),
      taken ? null : h('p', {}, `+${info.gold} gold. Wounds stay until you rest.`),
      taken || !info.levels ? null : h('div', { class: 'levels' }, info.levels.map(({ p, gains }) => h('div', {}, sprImg(heroSprite(p)),
        h('b', {}, `${heroTitle(p)} Lv ${p.lvl}`), ` ${gainsText(gains)}`))),
      h('h3', {}, picks > 1 ? `Spoils: choose ${picks - taken}` : 'Spoils: choose one'),
      h('div', { class: 'cards' }, offers.map(id => artCard(id, null, () => equipFlow(id, () => { taken++; offers = offers.filter(x => x !== id); spoils(); }, setScreen, spoils)))),
      btn('Leave them', learn)));
    auto(() => { taken++; const id = offers.shift(); equipFlow(id, spoils); });
  };
  spoils();
}
function promoCard(p, id, onpick) {
  const pr = PROMOS[id], o = skStats(p, { id: pr.skill, mods: [] });
  return h('button', { class: 'pick sig', onclick: () => { sfx('promote'); onpick(); } },
    h('div', { class: 'pick-head' }, sprImg(id, 'big'), h('b', {}, pr.name), archChips(pr.arch)),
    h('div', { class: 'new' }, Object.entries(pr.stats).map(([k, v]) => `${v > 0 ? '+' : ''}${v} ${k === 'maxHp' ? 'max HP' : k.toUpperCase()}`).join(', ')),
    h('div', { class: 'desc' }, pr.passive),
    h('div', { class: 'desc dim' }, `Growth: ${growthText(id)}`),
    h('div', { class: 'desc' }, h('b', { class: 'inline' }, `Learns ${o.name}`), skillText(o, heroSrc(p, run.gold))),
    h('div', { class: 'desc dim' }, `Adds to their skill pool: ${pr.pool.map(s => SKILLS[s].name).join(', ')}.`),
    pr.next ? h('div', { class: 'desc dim' }, `Can later become a ${pr.next.map(n => PROMOS[n].name).join(' or ')}.`) : null);
}
// After an act boss every hero promotes, choosing between two classes.
function promotionScreen(next) {
  const queue = run.party.map((p, hi) => hi).filter(hi => promoOptions(run.party[hi]).length);
  const step = () => {
    if (!queue.length) { next(); return; }
    const hi = queue.shift(), p = run.party[hi], opts = promoOptions(p);
    const become = id => { promote(p, id); clampHp(); hud(); learnFlow(hi, PROMOS[id].skill, step); };
    setScreen(h('div', { class: 'panel' },
      h('h2', {}, `The ${heroTitle(p)} can become...`),
      h('p', { class: 'muted' }, p.line && p.line.length ? 'A master class. The old passive stays; the new one stacks on top.' : 'Victory sharpens every hero. Each gains stats, a passive and a new skill pool.'),
      h('div', { class: 'cards' }, opts.map(id => promoCard(p, id, () => become(id))))));
    auto(() => become(pick(opts)));
  };
  step();
}
function nextAct() {
  if (run.act >= ACT_SLOTS.length - 1) { victory(); return; }
  run.act++;
  run.map = genMap(); run.pos = null; run.visited = [];
  run.party.forEach(p => { p.hp = heroStats(p, run.gold).maxHp; });
  save();
  actIntro();
}

// ---------- events ----------
const EVENTS = [
  { title: 'Forgotten Shrine', text: 'A mossy altar hums with old power. Coins glint in its offering bowl.', choices: () => [
    { label: 'Pray', note: 'Receive a skill artifact', go: () => { const id = artifactPool(run, 1, 1)[0]; return id ? { text: `Something settles into your hands: the ${artName(id)}.`, art: id } : 'The altar stays silent.'; } },
    { label: 'Take the offerings', note: '+70 gold; every hero takes 7 damage', go: () => { run.gold += 70; hurtAll(7); return 'The coins are cold. Something in the dark resents you.'; } },
    { label: 'Leave', go: () => 'You leave the shrine in peace.' },
  ] },
  { title: 'Wounded Sellsword', text: 'A bleeding mercenary sits against a tree. "Spare some coin for a healer? I\'ll pay you back in kind."', choices: () => [
    { label: 'Give 30 gold', cond: run.gold >= 30, go: () => { run.gold -= 30; return { text: 'She presses something strange into your hand and limps off.', art: artifactPool(run, 1, 0)[0] }; } },
    { label: 'Walk on', go: () => 'Her curses follow you up the road.' },
  ] },
  { title: 'Healing Spring', text: 'A thin trickle of clear water seeps between mossy stones.', choices: () => [
    { label: 'Drink', note: 'Heal 25% of max HP', go: () => { healAll(0.25); return 'The water tastes of mint and starlight.'; } },
    { label: 'Bathe', note: '+5 max HP for every hero', go: () => { run.party.forEach(p => { p.maxHp += 5; }); return 'You leave feeling sturdier, if no less sore.'; } },
  ] },
  { title: 'Locked Chest', text: 'An iron-bound chest sits alone in a clearing. Too alone.', choices: () => [
    { label: 'Pry it open', note: 'Treasure... probably', go: () => chance(0.65) ? { text: 'Inside, wrapped in oilcloth, is something odd.', art: artifactPool(run, 1)[0] } : { text: 'The chest was bait. Figures step out of hiding!', battle: true } },
    { label: 'Leave it', go: () => 'Some things are better left shut.' },
  ] },
  { title: 'Old Swordmaster', text: 'A grizzled master offers to teach one of you a new technique, if they can take a beating.', choices: () => [
    ...run.party.map((p, hi) => ({ label: `Train the ${heroTitle(p)}`, note: '−10 HP, then choose a skill for them', cond: skillPool(p).length > 0,
      go: () => { p.hp = Math.max(1, p.hp - 10); return { text: `The ${heroTitle(p)} limps back, bruised and wiser.`, learnHero: hi }; } })),
    { label: 'Decline', go: () => 'He shrugs and goes back to his tea.' },
  ] },
  { title: 'Card Sharp', text: 'A hooded figure shuffles a worn deck. "Double or nothing, friends?"', choices: () => [
    { label: 'Bet 40 gold', cond: run.gold >= 40, go: () => { if (chance(0.5)) { run.gold += 40; return 'You win! +40 gold.'; } run.gold -= 40; return 'The cards turn against you. −40 gold.'; } },
    { label: 'Decline', go: () => 'The figure chuckles and vanishes into the fog.' },
  ] },
  { title: 'Grinning Idol', text: 'A stone idol grins from a ruined plinth, offering power for a price.', choices: () => [
    { label: 'Accept its gift', note: 'Every hero: +2 ATK, +2 MAG, −6 max HP', go: () => {
      run.party.forEach(p => { p.atk += 2; p.mag += 2; p.maxHp = Math.max(10, p.maxHp - 6); });
      clampHp();
      return 'Power floods in. Something else drains out.';
    } },
    { label: 'Smash it', note: '+30 gold', go: () => { run.gold += 30; return 'Gems tumble from its broken eyes. +30 gold.'; } },
  ] },
  { title: 'Abandoned Camp', text: 'A cold campfire, bedrolls, and a dropped pack.', choices: () => [
    { label: 'Rest by the ashes', note: 'Heal 15% of max HP', go: () => { healAll(0.15); return 'You doze fitfully and wake a little better.'; } },
    { label: 'Search the pack', note: 'Find gold', go: () => { const g = rnd(40, 80); run.gold += g; return `A purse! +${g} gold.`; } },
  ] },
  { title: 'Fairy Ring', text: 'Mushrooms circle a patch of glowing grass. Bells chime from nowhere.', choices: () => [
    ...run.party.map(p => ({ label: `Send in the ${heroTitle(p)}`, note: '+1 MOV or +3 SPD', go: () => {
      if (chance(0.5)) { p.mov += 1; return `The ${heroTitle(p)} feels light on their feet. +1 MOV.`; }
      p.spd += 3; return `The ${heroTitle(p)} moves in a blur. +3 SPD.`;
    } })),
    { label: 'Leave', go: () => 'The bells fall silent behind you.' },
  ] },
  { title: 'Wandering Alchemist', text: 'A soot-stained alchemist waves a bubbling flask. "Free sample! Mostly safe!"', choices: () => [
    { label: 'Buy a tonic', note: '40 gold: heal 25%', cond: run.gold >= 40, go: () => { run.gold -= 40; healAll(0.25); return 'It tastes awful and works, mostly.'; } },
    { label: 'Try the sample', note: 'A random hero... reacts', go: () => {
      const p = pick(run.party);
      if (chance(0.55)) { p.def += 2; p.res += 2; return `The ${heroTitle(p)}'s skin hardens like bark. +2 DEF and RES.`; }
      p.hp = Math.max(1, p.hp - 10); return `The ${heroTitle(p)} turns green and loses 10 HP.`;
    } },
    { label: 'Decline', go: () => '"Your loss!"' },
  ] },
  { title: 'Ambush!', text: 'Shapes rush out of hiding. You are surrounded.', choices: () => [{ label: 'Fight!', go: () => ({ text: 'Weapons out!', battle: true }) }] },
  { title: 'Mirror Pool', text: 'A still pool shows each of you as you might have been.', choices: () => [
    ...run.party.map(p => ({ label: `The ${heroTitle(p)} gazes in`, note: 'Their base ATK and MAG swap, forever', go: () => {
      [p.atk, p.mag] = [p.mag, p.atk];
      return `The ${heroTitle(p)}'s reflection winks. ATK is now ${p.atk}, MAG ${p.mag}. A Runed Edge or Brass Knuckles might help.`;
    } })),
    { label: 'Look away', go: () => 'The pool ripples, disappointed.' },
  ] },
  { title: 'Mad Tinkerer', text: 'A wild-eyed tinkerer grabs at your gear. "Give me something, I\'ll make it STRANGER."', choices: () => [
    ...run.party.filter(p => p.items.length).map(p => ({ label: `Hand over the ${heroTitle(p)}'s ${artName(p.items[0])}`, note: 'Trade it for a random odd hero artifact', go: () => {
      const old = p.items.shift();
      const id = artifactPool(run, 1, 0).find(x => ITEMS[x].unique);
      if (!id) { p.items.unshift(old); return 'He sighs. "You already have all the interesting things."'; }
      p.items.push(id);
      clampHp();
      return `With a bang and a puff of smoke, the ${artName(old)} becomes a ${artName(id)}: ${artText(id)}`;
    } })),
    { label: 'Back away slowly', go: () => '"COWARDS!"' },
  ] },
  { title: 'Library of Echoes', act: r => r.act >= 1, text: 'Shelves of books whisper techniques nobody should know.', choices: () => [
    { label: 'Read', note: 'Choose a skill artifact', go: () => ({ text: 'The words crawl off the page and harden into something you can hold.', arts: artifactPool(run, 3, 1) }) },
    { label: 'Burn a few for warmth', note: 'Heal 10%', go: () => { healAll(0.1); return 'The books scream a little. You feel slightly better.'; } },
  ] },
  { title: 'Curio Peddler', w: 2, text: 'A peddler unrolls a mat of strange goods, sorted with great care into little heaps. "Pick a heap, any heap. Forty gold."', choices: () => [
    ...shuffle(Object.keys(ARCHES)).slice(0, 3).map(t => ({ label: `The ${ARCHES[t].name.toLowerCase()} heap`, note: `40 gold: choose from three ${ARCHES[t].name.toLowerCase()} artifacts`, cond: run.gold >= 40,
      go: () => { run.gold -= 40; return { text: 'She sweeps the heap toward you. "Choose. Quickly."', arts: artifactPool(run, 3, 0.5, t) }; } })),
    { label: 'Browse and leave', go: () => '"Window shoppers," she mutters.' },
  ] },
  { title: 'Thorned Altar', text: 'Brambles have grown into the shape of a kneeling knight. Its outstretched hand is full of thorns.', choices: () => [
    { label: 'Clasp the hand', note: 'Every hero takes 6 damage; choose a thorns artifact', go: () => { hurtAll(6); return { text: 'The thorns bite deep and come away in your palm.', arts: artifactPool(run, 2, 0.5, 'thorns') }; } },
    { label: 'Cut it down', note: '+25 gold', go: () => { run.gold += 25; return 'Coins tumble out of the hollow knight.'; } },
  ] },
  { title: 'Gambler\'s Den', text: 'A smoky tent. A one-eyed dealer shuffles cards without looking at them. "Feeling lucky?"', choices: () => [
    { label: 'Play a hand for his charms', note: 'Even odds: a free fortune artifact, or lose 25 gold', cond: run.gold >= 25, go: () => {
      if (chance(0.5)) return { text: 'You win. He pushes a tray of charms across the table.', arts: artifactPool(run, 2, 0.5, 'fortune') };
      run.gold -= 25; return 'The card turns. The dealer sweeps your coins away.'; } },
    { label: 'Buy a lucky charm', note: '35 gold: choose a fortune artifact', cond: run.gold >= 35, go: () => { run.gold -= 35; return { text: '"This one\'s never lost me a bet."', arts: artifactPool(run, 2, 0.5, 'fortune') }; } },
    { label: 'Leave', go: () => '"Next time, then."' },
  ] },
  { title: 'Hanging Tree', act: r => r.act >= 1, text: 'Every branch of a dead oak is hung with dolls of twig and hair. One turns to watch you.', choices: () => [
    { label: 'Take a doll', note: 'Every hero takes 5 damage; choose a hex artifact', go: () => { hurtAll(5); return { text: 'Something cold follows you a little way down the road.', arts: artifactPool(run, 2, 0.5, 'hex') }; } },
    { label: 'Burn the tree', note: '+20 gold', go: () => { run.gold += 20; return 'Coins drop from the ashes. The dolls don\'t burn.'; } },
  ] },
  { title: 'Battlefield Ossuary', text: 'Bones of an old war, stacked with care. Trophies hang from every skull.', choices: () => [
    { label: 'Take a trophy', note: 'Choose a carnage artifact', go: () => ({ text: 'It still smells of the hunt.', arts: artifactPool(run, 2, 0.5, 'carnage') }) },
    { label: 'Pay respects', note: 'Heal 8%', go: () => { healAll(0.08); return 'A quiet moment helps.'; } },
  ] },
  { title: 'Poisoner\'s Garden', act: r => r.act >= 1, text: 'Neat rows of beautiful, deadly plants. A sign reads "Take one. Don\'t eat it."', choices: () => [
    { label: 'Take a cutting', note: 'Choose a poison artifact', go: () => ({ text: 'You wrap it carefully in cloth.', arts: artifactPool(run, 2, 0.5, 'poison') }) },
    { label: 'Eat one', note: 'A random hero: +3 ATK and MAG, −12 max HP', go: () => { const p = pick(run.party); p.atk += 3; p.mag += 3; p.maxHp = Math.max(10, p.maxHp - 12); clampHp(); return `The ${heroTitle(p)} goes green, then grins.`; } },
  ] },
  { title: 'Lava Forge', act: r => r.act === 2, text: 'A dwarven forge, still roaring, built over a lava vent.', choices: () => [
    { label: 'Forge something', note: 'Every hero takes 8 damage; choose a fiery skill artifact', go: () => { hurtAll(8); return { text: 'The heat is unbearable. Something glows on the anvil.', arts: ['molten', 'kindling'] }; } },
    { label: 'Warm up and move on', note: 'Heal 10%', go: () => { healAll(0.1); return 'Toasty.'; } },
  ] },
];

function chooseArtifact(title, ids, next) {
  if (!ids.length) { next(); return; }
  setScreen(h('div', { class: 'panel' }, h('h2', {}, title),
    h('div', { class: 'cards' }, ids.map(id => artCard(id, null, () => equipFlow(id, next, setScreen, () => chooseArtifact(title, ids, next))))), btn('Take nothing', next)));
  auto(() => equipFlow(ids[0], next));
}
function showEvent() {
  hud();
  const ok = e => !e.act || e.act(run);
  let pool = EVENTS.filter(e => ok(e) && !run.seen.includes(e.title));
  if (!pool.length) { run.seen = []; pool = EVENTS.filter(ok); }
  let r = Math.random() * pool.reduce((t, e) => t + (e.w || 1), 0);
  const ev = pool.find(e => (r -= e.w || 1) <= 0) || pool[0];
  run.seen.push(ev.title);
  const choices = ev.choices();
  const choose = c => {
    let res = c.go();
    if (typeof res === 'string') res = { text: res };
    hud();
    sfx(res.battle ? 'roar' : 'select');
    const next = () => {
      if (res.battle) battle('normal');
      else if (res.art) equipFlow(res.art, showMap);
      else if (res.arts) chooseArtifact('Choose one', res.arts, showMap);
      else if (res.learnHero != null) {
        const opts = skillOffers(run.party, 3, res.learnHero);
        const offer = () => setScreen(h('div', { class: 'panel' }, h('h2', {}, 'Choose a technique'),
          h('div', { class: 'cards' }, opts.map(c => skillCard(run.party[c.hi], c.id, null, () => learnFlow(c.hi, c.id, showMap, setScreen, offer)))), btn('Skip', showMap)));
        offer();
        auto(() => opts.length ? learnFlow(opts[0].hi, opts[0].id, showMap) : showMap());
      } else showMap();
    };
    setScreen(h('div', { class: 'panel' }, h('h2', {}, ev.title), h('p', {}, res.text), btn('Continue', next, 'go')));
    auto(next);
  };
  setScreen(h('div', { class: 'panel' }, h('h2', {}, ev.title), h('p', {}, ev.text),
    h('div', { class: 'choices' }, choices.map(c => h('button', { class: 'btn', disabled: c.cond === false, onclick: () => choose(c) }, c.label, c.note ? h('small', {}, c.note) : null)))));
  auto(() => choose(choices.find(c => c.cond !== false)));
}

// ---------- shop ----------
const TUTOR = 60, INN = 45;
const innHeal = n => n.r === ROWS_PER_ACT - 1 ? 0.4 : 0.25; // the shops just before a boss have proper beds
function showShop(n) {
  n.shop ||= { items: artifactPool(run, 6, 0.5).map(id => ({ id, price: artPrice(id) + rnd(-5, 10), sold: false })),
    lessons: skillOffers(run.party, 2).map(c => ({ ...c, sold: false })), inn: false };
  const shop = n.shop;
  hud();
  music('m_map');
  const again = () => showShop(n);
  const buy = it => equipFlow(it.id, () => { run.gold -= it.price; it.sold = true; again(); }, setScreen, again);
  const lesson = c => learnFlow(c.hi, c.id, () => { run.gold -= TUTOR; c.sold = true; again(); }, setScreen, again);
  const rest = () => { run.gold -= INN; shop.inn = true; healAll(innHeal(n)); sfx('heal'); again(); };
  setScreen(h('div', {},
    h('div', { class: 'panel' },
      h('h2', {}, 'Shop'),
      h('p', {}, 'A merchant has set up a stall under a patched awning. "Curios, lessons, a lumpy bed. Some of it is even safe."'),
      h('h3', {}, 'Artifacts'),
      h('div', { class: 'cards' }, shop.items.map(it => artCard(it.id, h('span', { class: 'price' }, it.sold ? 'Sold' : `${it.price}g`), () => buy(it), it.sold || run.gold < it.price))),
      h('h3', {}, `Lessons (${TUTOR}g)`),
      h('div', { class: 'cards' }, shop.lessons.map(c => skillCard(run.party[c.hi], c.id, h('span', { class: 'price' }, c.sold ? 'Learned' : `${TUTOR}g`), () => lesson(c),
        c.sold || run.gold < TUTOR || run.party[c.hi].skills.some(s => s.id === c.id)))),
      h('h3', {}, 'Inn'),
      btn(shop.inn ? 'Rested' : `Rest: heal ${innHeal(n) * 100}% (${INN}g)`, rest, '', shop.inn || run.gold < INN),
    ),
    btn('Leave shop', showMap, 'big go'),
  ));
  auto(() => {
    const hurt = run.party.some(p => p.hp < heroStats(p, run.gold).maxHp * 0.65);
    if (hurt && !shop.inn && run.gold >= INN) { rest(); return; }
    const it = shop.items.find(i => !i.sold && run.gold >= i.price);
    if (it) { buy(it); return; }
    showMap();
  });
}

// ---------- party ----------
function showParty() {
  if (!run) return;
  sfx('click');
  const close = () => { modal.hidden = true; modal.replaceChildren(); };
  const refresh = () => { hud(); showParty(); };
  const unsocket = (s, i) => { run.stash.push(s.mods.splice(i, 1)[0]); refresh(); };
  const unwear = (p, i) => { run.stash.push(p.items.splice(i, 1)[0]); clampHp(); refresh(); };
  const equip = i => { const id = run.stash[i]; equipFlow(id, () => { run.stash.splice(run.stash.indexOf(id), 1); refresh(); }, modalShow, refresh); };
  const x = (label, fn) => h('button', { class: 'linkbtn', onclick: fn }, label);
  modalShow(h('div', {},
    h('div', { class: 'row modal-head' }, h('h2', { class: 'grow' }, 'Your party'), h('button', { class: 'btn', onclick: close }, 'Close')),
    h('div', { class: 'hero-cards' }, run.party.map(p => {
      const st = heroStats(p, run.gold), src = heroSrc(p, run.gold);
      return h('div', { class: 'hero-card' },
        h('div', { class: 'card-head' }, sprImg(heroSprite(p), 'big'), h('div', { class: 'who' }, h('b', {}, heroTitle(p)), bar(p.hp, st.maxHp, false), `${p.hp}/${st.maxHp} HP`)),
        h('div', { class: 'stats' }, `ATK ${st.atk} · MAG ${st.mag} · DEF ${st.def} · RES ${st.res} · SPD ${st.spd} · MOV ${st.mov} · CRIT ${st.crit}%`),
        h('div', { class: 'desc' }, h('b', { class: 'inline' }, `Lv ${p.lvl || 1} `), `Growth: ${growthText(growthClass(p))}`,
          nextBreakpoint(p) ? h('span', { class: 'next-bp' }, ` · next ${nextBreakpoint(p)}`) : null),
        ...(p.line || []).map(c => h('div', { class: 'desc' }, h('b', { class: 'inline' }, PROMOS[c].name + ' '), PROMOS[c].passive)),
        h('h3', { style: 'margin-top:10px' }, `Skills ${p.skills.length}/${MAX_SKILLS}`),
        h('div', { class: 'skill-list' }, p.skills.map(s => {
          const o = skStats(p, s);
          return h('div', {}, h('b', {}, o.name), skillText(o, src),
            h('div', { class: 'mods' }, s.mods.map((id, i) => h('span', { class: 'mod' }, `◆ ${artName(id)} `, x('remove', () => unsocket(s, i)))),
              s.mods.length < MAX_MODS ? h('span', { class: 'mod empty' }, `◇ empty slot`) : null));
        })),
        h('h3', { style: 'margin-top:10px' }, `Worn ${p.items.length}/${MAX_RELICS}`),
        p.items.length ? h('ul', {}, p.items.map((id, i) => h('li', {}, `${artName(id)}: ${artText(id)} `, x('remove', () => unwear(p, i))))) : h('div', { class: 'muted' }, 'Nothing'),
      );
    })),
    h('div', { class: 'panel', style: 'margin-top:16px' }, h('h3', {}, 'Archetypes'),
      h('p', { class: 'muted' }, 'Rewards lean toward the archetypes your classes and artifacts share.'),
      archChips(Object.entries(partyArches(run)).sort((a, b) => b[1] - a[1]).map(([t]) => t))),
    h('div', { class: 'panel', style: 'margin-top:16px' }, h('h3', {}, 'Pack'),
      run.stash.length ? h('div', { class: 'cards' }, run.stash.map((id, i) => artCard(id, h('span', { class: 'price' }, 'Equip'), () => equip(i)))) : h('div', { class: 'muted' }, 'Empty. Removed artifacts wait here.')),
  ));
  modal.onclick = e => { if (e.target === modal) close(); };
}

// ---------- title and endings ----------
function showTitle() {
  run = null;
  hud();
  music('m_map');
  const saved = load();
  setScreen(h('div', { class: 'panel center' },
    h('div', { class: 'title-name' }, 'Threefold Path'),
    h('div', { class: 'title-art' }, sprImg('warrior', 'huge'), sprImg('mage', 'huge'), sprImg('rogue', 'huge')),
    h('p', {}, 'Three heroes. Three acts, each drawn from two lands, each with its own boss.'),
    saved ? btn('Continue run', () => { run = saved; env.run = run; showMap(); }, 'big go') : null,
    btn(saved ? 'New run' : 'Start run', () => { clearSave(); newRun(); }, 'big'),
    h('details', { class: 'howto', open: !saved && window.innerWidth > 640 },
      h('summary', {}, h('h3', {}, 'How to play')),
      h('ul', {},
        h('li', {}, 'Each act is a branching map of battles, events (?) and shops, ending in a boss. Beating a boss promotes every hero: each picks one of two advanced classes after Act 1, then one of two master classes after Act 2. Passives stack.'),
        h('li', {}, 'In battle, units take turns by speed (the "Next" strip). On a hero\'s turn, move once and act once, in either order.'),
        h('li', {}, 'Walls block movement and line of sight: bolts and arrows can\'t pass them, but lobbed skills can. Lava burns, brambles cut, high ground extends range, and cover cuts damage. Tap any tile to read it.'),
        h('li', {}, 'Flank: hitting a foe that another hero stands next to deals 25% more (the Rogue gets 50%).'),
        h('li', {}, 'Battles pay out in artifacts. Skill artifacts socket into a skill and rewrite it: swap the stat it uses, turn bolts into ricochets or shields, make attacks leap or melt the floor. Hero artifacts are worn and change the hero.'),
        h('li', {}, `Artifacts and classes share archetypes (${Object.values(ARCHES).map(a => a.name.toLowerCase()).join(', ')}). Stack one and rewards start leaning toward it. Tap an underlined word to read what it does.`),
        h('li', {}, 'After a fight a hero can learn a new skill from their class. Each knows at most 4, so learning may mean forgetting.'),
        h('li', {}, 'Healing is scarce. Wounds carry between fights, there\'s no healing after a battle, and the fallen get up with 10% HP. Each new act restores everyone. Dawdle in a fight and the enemy grows furious.'),
        h('li', {}, 'On touch screens, tap a target once to preview, again to confirm.'),
      )),
  ));
  auto(() => { clearSave(); newRun(); });
}
function gameOver() {
  clearSave();
  hud();
  music(null);
  setScreen(h('div', { class: 'panel center' },
    h('div', { class: 'title-name' }, 'Defeat'),
    h('p', {}, `Your party fell in Act ${run.act + 1}. Battles won: ${run.stats.battles}. Foes slain: ${run.stats.kills}.`),
    btn('Try again', newRun, 'big go'), btn('Title', showTitle, 'big')));
  if (AUTO) window.__result = { win: false, act: run.act + 1, ...run.stats };
}
function victory() {
  clearSave();
  hud();
  music('m_map');
  sfx('promote');
  setScreen(h('div', { class: 'panel center' },
    h('div', { class: 'title-name' }, 'Victory!'),
    h('div', { class: 'title-art' }, run.party.map(p => sprImg(heroSprite(p), 'huge'))),
    h('p', {}, `The Cinder Wyrm falls and the mountain goes quiet. Battles won: ${run.stats.battles}. Foes slain: ${run.stats.kills}.`),
    h('p', { class: 'muted' }, run.party.map(heroTitle).join(', ')),
    btn('New run', newRun, 'big go')));
  if (AUTO) window.__result = { win: true, act: 3, ...run.stats };
}

// ---------- boot ----------
class Boot extends Phaser.Scene {
  constructor() { super('boot'); }
  create() {
    buildTextures(this);
    if (!AUTO) initAudio(this.game);
    showTitle();
  }
}
initTips();
game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  width: GW * TS,
  height: GH * TS,
  pixelArt: true,
  backgroundColor: '#000000',
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_HORIZONTALLY },
  audio: { disableWebAudio: false },
  banner: false,
  scene: [Boot, MapScene, BattleScene],
});
env.game = game;
if (AUTO) window.__tf = { get run() { return run; } };
