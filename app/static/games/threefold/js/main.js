// Threefold Path: run flow, menus, events, shops and saving. Phaser draws the map and battles;
// everything text-heavy is plain HTML in #side and #screen.
import { GW, GH, ROWS_PER_ACT, ACTS, CLASSES, PROMOS, SKILLS, UPGRADES, ITEMS } from './data.js?v=2';
import { rnd, pick, chance, shuffle, newHero, heroStats, heroSprite, heroTitle, promote, skStats, describe, upgradeOffers, upgradesFor } from './rules.js?v=2';
import { buildTextures, iconCanvas, NODE_COLORS } from './art.js?v=2';
import { initAudio, sfx, music, audioState, toggleMusic, toggleSfx } from './audio.js?v=2';
import { env, startBattle, BattleScene } from './battle.js?v=2';
import { MapScene, mapEnv, mapHeight } from './mapscene.js?v=2';
import { h, sprImg, bar } from './ui.js?v=2';

const params = new URLSearchParams(location.search);
const AUTO = params.has('auto'); // heroes play themselves; used to test balance
const SAVE_KEY = 'threefold-path-run-v2';
const TS = 64;

const $ = id => document.getElementById(id);
const stage = $('stage'), side = $('side'), screen = $('screen'), modal = $('modal');
env.side = side;
env.auto = AUTO;
env.speed = AUTO ? 0.01 : 1;

let run = null;
let game = null;

// ---------- layout ----------
function showStage(scene, sideKids) {
  screen.hidden = true; screen.replaceChildren();
  stage.hidden = false;
  side.replaceChildren(...(sideKids || []));
  for (const k of ['map', 'battle']) if (k !== scene && game.scene.isActive(k)) game.scene.stop(k);
  game.scale.refresh();
  window.scrollTo(0, 0);
}
function setScreen(...kids) {
  for (const k of ['map', 'battle']) if (game.scene.isActive(k)) game.scene.stop(k);
  stage.hidden = true;
  screen.hidden = false;
  screen.replaceChildren(...kids);
  window.scrollTo(0, 0);
}
const auto = fn => { if (AUTO) setTimeout(fn, 5); };
const btn = (label, onclick, cls = '', disabled = false) => h('button', { class: 'btn ' + cls, disabled, onclick: e => { sfx('click'); onclick(e); } }, label);

function hud(inBattle) {
  const el = $('hud');
  const a = audioState();
  const audio = [
    h('button', { class: 'btn tiny', onclick: () => { toggleMusic(); hud(inBattle); } }, a.music ? 'Music on' : 'Music off'),
    h('button', { class: 'btn tiny', onclick: () => { toggleSfx(); hud(inBattle); } }, a.sfx ? 'Sound on' : 'Sound off'),
  ];
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
  run = { party: ['warrior', 'mage', 'rogue'].map(newHero), gold: 60, act: 0, map: genMap(), pos: null, visited: [], seen: [], stats: { kills: 0, battles: 0 } };
  env.run = run;
  if (AUTO && params.has('chaos')) {
    // stress test: promoted heroes with random upgrades on every skill and a pile of odd items
    const odd = shuffle(Object.keys(ITEMS).filter(id => ITEMS[id].unique));
    run.party.forEach((p, i) => {
      promote(p, pick(CLASSES[p.cls].promos));
      for (const s of p.skills) for (let k = 0; k < 4; k++) { const ups = upgradesFor(p, s); if (ups.length) s.ups.push(pick(ups)); }
      p.items.push(...odd.slice(i * 6, i * 6 + 6));
      p.hp = heroStats(p, run.gold).maxHp;
    });
  }
  actIntro();
}
const available = () => !run.pos ? Object.values(run.map).filter(n => n.r === 0) : run.map[run.pos].next.map(id => run.map[id]);
const level = n => run.act * (ROWS_PER_ACT + 1) + (n.id === 'boss' ? ROWS_PER_ACT + 1 : n.r + 1);
const hurtAll = n => run.party.forEach(p => { p.hp = Math.max(1, p.hp - n); });
const healAll = f => run.party.forEach(p => { const m = heroStats(p, run.gold).maxHp; p.hp = Math.min(m, p.hp + Math.round(m * f)); });

function actIntro() {
  const act = ACTS[run.act];
  hud();
  music('m_map');
  setScreen(h('div', { class: 'panel center' },
    h('div', { class: 'title-name' }, `Act ${run.act + 1}`),
    h('h2', {}, act.name),
    h('p', {}, ['The road climbs through the Greenwood toward the Thornmother\'s grove.',
      'Below the old city, the Hollow King hoards the dead.',
      'At the top of the burning peaks, the Cinder Wyrm waits.'][run.act]),
    btn('Begin', showMap, 'big go'),
  ));
  auto(showMap);
}

// ---------- map ----------
function showMap() {
  save();
  hud();
  music('m_map');
  const legend = h('div', { class: 'panel legend' }, h('h3', {}, ACTS[run.act].name),
    ...['battle', 'elite', 'event', 'shop', 'boss'].map(t => {
      const c = h('canvas', { width: 24, height: 24 });
      const x = c.getContext('2d');
      x.imageSmoothingEnabled = false;
      x.fillStyle = NODE_COLORS[t]; x.fillRect(0, 0, 24, 24);
      x.drawImage(iconCanvas(t), 4, 4, 16, 16);
      return h('div', {}, c, t === 'boss' ? ACTS[run.act].boss : { battle: 'Battle', elite: 'Elite battle (drops an item)', event: 'Unknown event', shop: 'Shop' }[t]);
    }),
    h('p', { class: 'muted' }, 'Pick a glowing node. Drag or scroll the map to look ahead. The last row before the boss is all shops.'));
  showStage('map', [legend]);
  Object.assign(mapEnv, { run, available, pick: enterNode, actName: `Act ${run.act + 1}: ${ACTS[run.act].name}`, leader: heroSprite(run.party[0]) });
  game.scene.start('map');
  auto(() => enterNode(pick(available())));
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
  const act = ACTS[run.act], n = run.map[run.pos];
  const lvl = level(n);
  const list = kind === 'boss' ? act.bossParty : kind === 'elite' ? pick(act.elite) : pick(n.r < 4 ? act.early : act.late);
  hud(true);
  music(kind === 'boss' ? 'm_boss' : 'm_' + act.theme);
  showStage('battle');
  startBattle({ kind, level: lvl, act, list, party: run.party });
}
env.onEnd = (b, win) => {
  if (AUTO) (window.__log ||= []).push({ act: run.act + 1, kind: b.kind, lvl: b.level, win, heroes: b.units.filter(u => u.ref).map(u => u.dead ? 0 : u.hp).join('/'),
    foes: win ? '' : b.units.filter(u => u.side === 'foe' && !u.dead).map(u => `${u.name}:${u.hp}`).join(' ') });
  if (!win) { gameOver(); return; }
  for (const u of b.units) {
    if (!u.ref) continue;
    const p = u.ref;
    p.maxHp += 4;
    p[CLASSES[p.cls].main] += 1;
    const max = heroStats(p, run.gold).maxHp;
    p.hp = u.dead ? Math.ceil(max * 0.25) : Math.min(max, u.hp + 3 + Math.round(max * 0.1));
  }
  run.stats.battles++;
  const tooth = run.party.some(p => p.items.includes('goldtooth')) ? 1.4 : 1;
  const base = b.kind === 'boss' ? rnd(90, 110) : b.kind === 'elite' ? rnd(55, 70) + b.level * 3 : rnd(20, 30) + b.level * 2;
  showRewards({ gold: Math.round(base * tooth), kind: b.kind });
};

// ---------- cards ----------
function upgradeCard(c, extra, onpick, disabled) {
  const p = run.party[c.hi], s = p.skills[c.si], up = UPGRADES[c.up];
  const after = skStats(p, { id: s.id, ups: [...s.ups, c.up] });
  return h('button', { class: 'pick' + (up.only ? ' sig' : ''), disabled, onclick: () => { sfx('select'); onpick(); } },
    h('div', { class: 'pick-head' }, sprImg(heroSprite(p)), h('b', {}, `${SKILLS[s.id].name}: ${up.name}`), extra),
    h('div', { class: 'new' }, up.note),
    h('div', { class: 'desc' }, describe(after)),
    s.ups.length ? h('div', { class: 'desc dim' }, 'Has: ' + s.ups.map(id => UPGRADES[id].name).join(', ')) : null);
}
function applyUpgrade(c) { run.party[c.hi].skills[c.si].ups.push(c.up); }
const ownedItems = () => new Set(run.party.flatMap(p => p.items));
function itemPool(n, weird) {
  const owned = ownedItems();
  const ids = Object.keys(ITEMS).filter(id => !(ITEMS[id].unique && owned.has(id)));
  const strange = shuffle(ids.filter(id => ITEMS[id].unique)), plain = shuffle(ids.filter(id => !ITEMS[id].unique));
  const k = Math.min(strange.length, weird ?? Math.ceil(n * 0.7));
  return shuffle([...strange.slice(0, k), ...plain.slice(0, n - k)]).slice(0, n);
}
function itemCard(id, extra, onpick, disabled) {
  const it = ITEMS[id];
  return h('button', { class: 'pick' + (it.unique ? ' weird' : ''), disabled, onclick: () => { sfx('select'); onpick(); } },
    h('div', { class: 'pick-head' }, h('b', {}, it.name), extra), h('div', { class: 'desc' }, it.txt));
}
function giveItem(id, next) {
  const it = ITEMS[id];
  const choose = p => {
    p.items.push(id);
    if (it.stats && it.stats.maxHp) p.hp += it.stats.maxHp;
    p.hp = Math.min(p.hp, heroStats(p, run.gold).maxHp);
    sfx('coin');
    next();
  };
  hud();
  setScreen(h('div', { class: 'panel' },
    h('h2', {}, `Who carries the ${it.name}?`), h('p', { class: 'muted' }, it.txt),
    h('div', { class: 'cards' }, run.party.map(p => h('button', { class: 'pick', onclick: () => choose(p) },
      h('div', { class: 'pick-head' }, sprImg(heroSprite(p)), h('b', {}, heroTitle(p))),
      h('div', { class: 'desc' }, p.items.length ? p.items.map(i => ITEMS[i].name).join(', ') : 'No items yet')))),
  ));
  auto(() => choose(pick(run.party)));
}
function showUpgradePick(title, offers, next, skipLabel = 'Skip') {
  if (!offers.length) { next(); return; }
  setScreen(h('div', { class: 'panel' }, h('h2', {}, title),
    h('div', { class: 'cards' }, offers.map(c => upgradeCard(c, null, () => { applyUpgrade(c); next(); }))),
    btn(skipLabel, next)));
  auto(() => { applyUpgrade(offers[0]); next(); });
}

// ---------- rewards, promotion, acts ----------
function showRewards(info) {
  run.gold += info.gold;
  hud();
  sfx('coin');
  const after = () => {
    if (info.kind === 'boss') { if (run.act >= ACTS.length - 1) victory(); else promotionScreen(nextAct); return; }
    if (info.kind !== 'elite') { showMap(); return; }
    const opts = itemPool(3);
    setScreen(h('div', { class: 'panel' }, h('h2', {}, 'The elite dropped treasure'), h('p', {}, 'Take one item.'),
      h('div', { class: 'cards' }, opts.map(id => itemCard(id, null, () => giveItem(id, showMap)))),
      btn('Leave it', showMap)));
    auto(() => giveItem(opts[0], showMap));
  };
  const offers = upgradeOffers(run.party, 3);
  setScreen(h('div', { class: 'panel' },
    h('h2', {}, info.kind === 'boss' ? `${ACTS[run.act].boss} is defeated!` : 'Victory!'),
    h('p', {}, `+${info.gold} gold. Every hero gains 4 max HP and 1 ${'ATK or MAG'}.`),
    offers.length ? h('h3', {}, 'Choose a skill upgrade') : null,
    h('div', { class: 'cards' }, offers.map(c => upgradeCard(c, null, () => { applyUpgrade(c); after(); }))),
    btn(offers.length ? 'Skip' : 'Continue', after),
  ));
  auto(() => { if (offers.length) applyUpgrade(offers[0]); after(); });
}
function promoCard(p, id, onpick) {
  const pr = PROMOS[id], sk = SKILLS[pr.skill];
  const o = skStats(p, { id: pr.skill, ups: [] });
  return h('button', { class: 'pick sig', onclick: () => { sfx('promote'); onpick(); } },
    h('div', { class: 'pick-head' }, sprImg(id, 'big'), h('b', {}, pr.name)),
    h('div', { class: 'new' }, Object.entries(pr.stats).map(([k, v]) => `+${v} ${k === 'maxHp' ? 'max HP' : k.toUpperCase()}`).join(', ')),
    h('div', { class: 'desc' }, pr.passive),
    h('div', { class: 'desc' }, h('b', { class: 'inline' }, `New skill: ${sk.name}. `), `${describe(o)}. ${sk.txt}`));
}
function promotionScreen(next, cost) {
  const cands = run.party.map((p, hi) => ({ p, hi })).filter(c => !c.p.promo);
  if (!cands.length) { next(); return; }
  const choose = hi => {
    const p = run.party[hi];
    setScreen(h('div', { class: 'panel' }, h('h2', {}, `The ${heroTitle(p)} can become...`),
      h('div', { class: 'cards' }, CLASSES[p.cls].promos.map(id => promoCard(p, id, () => { if (cost) run.gold -= cost; promote(p, id); next(); }))),
      btn('Back', () => promotionScreen(next, cost))));
    auto(() => { if (cost) run.gold -= cost; promote(p, pick(CLASSES[p.cls].promos)); next(); });
  };
  setScreen(h('div', { class: 'panel' },
    h('h2', {}, 'Promotion'),
    h('p', {}, cost ? `For ${cost} gold, one hero may take up an advanced class.` : 'Victory sharpens one of your heroes. Choose who takes up an advanced class: they gain stats, a passive and a new skill.'),
    h('div', { class: 'cards' }, cands.map(({ p, hi }) => h('button', { class: 'pick', onclick: () => { sfx('select'); choose(hi); } },
      h('div', { class: 'pick-head' }, sprImg(heroSprite(p), 'big'), h('b', {}, heroTitle(p))),
      h('div', { class: 'desc' }, 'Becomes ' + CLASSES[p.cls].promos.map(id => PROMOS[id].name).join(' or '))))),
    cost ? btn('Not now', next) : null,
  ));
  auto(() => choose(pick(cands).hi));
}
function nextAct() {
  if (run.act >= ACTS.length - 1) { victory(); return; }
  run.act++;
  run.map = genMap(); run.pos = null; run.visited = [];
  run.party.forEach(p => { p.hp = heroStats(p, run.gold).maxHp; });
  save();
  actIntro();
}

// ---------- events ----------
const EVENTS = [
  { title: 'Forgotten Shrine', text: 'A mossy altar hums with old power. Coins glint in its offering bowl.', choices: () => [
    { label: 'Pray', note: 'A random skill gains a random upgrade', go: () => {
      const c = upgradeOffers(run.party, 1)[0];
      if (!c) return 'The altar stays silent.';
      applyUpgrade(c);
      const p = run.party[c.hi];
      return `A warm light settles on the ${heroTitle(p)}. ${SKILLS[p.skills[c.si].id].name} becomes ${UPGRADES[c.up].name}: ${UPGRADES[c.up].note.toLowerCase()}.`;
    } },
    { label: 'Take the offerings', note: '+70 gold; every hero takes 7 damage', go: () => { run.gold += 70; hurtAll(7); return 'The coins are cold. Something in the dark resents you.'; } },
    { label: 'Leave', go: () => 'You leave the shrine in peace.' },
  ] },
  { title: 'Wounded Sellsword', text: 'A bleeding mercenary sits against a tree. "Spare some coin for a healer? I\'ll pay you back in kind."', choices: () => [
    { label: 'Give 30 gold', cond: run.gold >= 30, go: () => { run.gold -= 30; return { text: 'She presses something strange into your hand and limps off.', item: itemPool(1, 1)[0] }; } },
    { label: 'Walk on', go: () => 'Her curses follow you up the road.' },
  ] },
  { title: 'Healing Spring', text: 'Clear water bubbles up between mossy stones.', choices: () => [
    { label: 'Drink deeply', note: 'Heal 50% of max HP', go: () => { healAll(0.5); return 'The water tastes of mint and starlight.'; } },
    { label: 'Bathe slowly', note: '+5 max HP for every hero', go: () => { run.party.forEach(p => { p.maxHp += 5; p.hp += 5; }); return 'You leave feeling sturdier.'; } },
  ] },
  { title: 'Locked Chest', text: 'An iron-bound chest sits alone in a clearing. Too alone.', choices: () => [
    { label: 'Pry it open', note: 'Treasure... probably', go: () => chance(0.65) ? { text: 'Inside, wrapped in oilcloth, is something odd.', item: itemPool(1, 1)[0] } : { text: 'The chest was bait. Figures step out of hiding!', battle: true } },
    { label: 'Leave it', go: () => 'Some things are better left shut.' },
  ] },
  { title: 'Old Swordmaster', text: 'A grizzled master offers a lesson to one of you, if they can take a beating.', choices: () => [
    ...run.party.map((p, hi) => ({ label: `Train the ${heroTitle(p)}`, note: '−10 HP, then choose an upgrade for them', cond: p.skills.some(s => upgradesFor(p, s).length),
      go: () => { p.hp = Math.max(1, p.hp - 10); return { text: `The ${heroTitle(p)} limps back, bruised and wiser.`, upgradeHero: hi }; } })),
    { label: 'Decline', go: () => 'He shrugs and goes back to his tea.' },
  ] },
  { title: 'Card Sharp', text: 'A hooded figure shuffles a worn deck. "Double or nothing, friends?"', choices: () => [
    { label: 'Bet 40 gold', cond: run.gold >= 40, go: () => { if (chance(0.5)) { run.gold += 40; return 'You win! +40 gold.'; } run.gold -= 40; return 'The cards turn against you. −40 gold.'; } },
    { label: 'Decline', go: () => 'The figure chuckles and vanishes into the fog.' },
  ] },
  { title: 'Grinning Idol', text: 'A stone idol grins from a ruined plinth, offering power for a price.', choices: () => [
    { label: 'Accept its gift', note: 'Every hero: +2 ATK, +2 MAG, −6 max HP', go: () => {
      run.party.forEach(p => { p.atk += 2; p.mag += 2; p.maxHp = Math.max(10, p.maxHp - 6); p.hp = Math.min(p.hp, heroStats(p, run.gold).maxHp); });
      return 'Power floods in. Something else drains out.';
    } },
    { label: 'Smash it', note: '+30 gold', go: () => { run.gold += 30; return 'Gems tumble from its broken eyes. +30 gold.'; } },
  ] },
  { title: 'Abandoned Camp', text: 'A cold campfire, bedrolls, and a dropped pack.', choices: () => [
    { label: 'Rest by the ashes', note: 'Heal 30% of max HP', go: () => { healAll(0.3); return 'You sleep, lightly, and wake rested.'; } },
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
    { label: 'Buy a tonic', note: '25 gold: heal 40%', cond: run.gold >= 25, go: () => { run.gold -= 25; healAll(0.4); return 'It tastes awful and works wonders.'; } },
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
      return `The ${heroTitle(p)}'s reflection winks. ATK is now ${p.atk}, MAG ${p.mag}. Upgrades like Spellblade or Brute Force might help.`;
    } })),
    { label: 'Look away', go: () => 'The pool ripples, disappointed.' },
  ] },
  { title: 'Mad Tinkerer', text: 'A wild-eyed tinkerer grabs at your gear. "Give me something, I\'ll make it STRANGER."', choices: () => [
    ...run.party.filter(p => p.items.length).map(p => ({ label: `Hand over the ${heroTitle(p)}'s ${ITEMS[p.items[0]].name}`, note: 'Trade it for a random odd item', go: () => {
      const old = p.items.shift();
      const id = itemPool(1, 1)[0];
      if (!id) { p.items.unshift(old); return 'He sighs. "You already have all the interesting things."'; }
      p.items.push(id);
      return `With a bang and a puff of smoke, the ${ITEMS[old].name} becomes a ${ITEMS[id].name}: ${ITEMS[id].txt}`;
    } })),
    { label: 'Back away slowly', go: () => '"COWARDS!"' },
  ] },
  { title: 'Library of Echoes', act: r => r.act >= 1, text: 'Shelves of books whisper techniques nobody should know.', choices: () => [
    { label: 'Read', note: 'Choose a strange upgrade', go: () => ({ text: 'The words crawl off the page and into your hands.', strange: true }) },
    { label: 'Burn a few for warmth', note: 'Heal 25%', go: () => { healAll(0.25); return 'The books scream a little. You feel better.'; } },
  ] },
  { title: 'Ascension Shrine', w: 3, act: r => r.act >= 1 && r.party.some(p => !p.promo), text: 'A pillar of light hums in a ring of standing stones. It asks for gold, and offers change.', choices: () => [
    { label: 'Offer 80 gold', note: 'Promote a hero', cond: run.gold >= 80, go: () => ({ text: 'The light bends toward you.', promote: 80 }) },
    { label: 'Leave', go: () => 'The light dims as you go.' },
  ] },
  { title: 'Lava Forge', act: r => r.act === 2, text: 'A dwarven forge, still roaring, built over a lava vent.', choices: () => [
    { label: 'Temper your weapons', note: 'Every hero takes 8 damage; choose a fiery upgrade', go: () => { hurtAll(8); return { text: 'The heat is unbearable. The steel glows.', forge: true }; } },
    { label: 'Warm up and move on', note: 'Heal 20%', go: () => { healAll(0.2); return 'Toasty.'; } },
  ] },
];

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
      else if (res.item) giveItem(res.item, showMap);
      else if (res.upgradeHero != null) showUpgradePick('Choose an upgrade', upgradeOffers(run.party, 3, res.upgradeHero), showMap);
      else if (res.strange) showUpgradePick('Choose a strange upgrade', strangeOffers(3), showMap);
      else if (res.forge) showUpgradePick('Choose a fiery upgrade', forgeOffers(), showMap);
      else if (res.promote) promotionScreen(showMap, res.promote);
      else showMap();
    };
    setScreen(h('div', { class: 'panel' }, h('h2', {}, ev.title), h('p', {}, res.text), btn('Continue', next, 'go')));
    auto(next);
  };
  setScreen(h('div', { class: 'panel' }, h('h2', {}, ev.title), h('p', {}, ev.text),
    h('div', {}, choices.map(c => h('button', { class: 'btn', disabled: c.cond === false, onclick: () => choose(c) }, c.label, c.note ? h('small', {}, c.note) : null)))));
  auto(() => choose(choices.find(c => c.cond !== false)));
}
function strangeOffers(n) {
  const out = [];
  for (let i = 0; i < 20 && out.length < n; i++) {
    const c = upgradeOffers(run.party, 6).find(c => !UPGRADES[c.up].repeat && !out.some(o => o.hi === c.hi && o.si === c.si));
    if (c) out.push(c);
  }
  return out;
}
function forgeOffers() {
  const out = [];
  run.party.forEach((p, hi) => p.skills.forEach((s, si) => {
    const ok = upgradesFor(p, s).filter(u => u === 'molten' || u === 'kindling');
    if (ok.length) out.push({ hi, si, up: pick(ok) });
  }));
  return shuffle(out).slice(0, 3);
}

// ---------- shop ----------
const upgradePrice = c => 50 + 25 * run.party[c.hi].skills[c.si].ups.length;
function showShop(n) {
  n.shop ||= { items: itemPool(5).map(id => ({ id, price: ITEMS[id].price + rnd(-5, 10), sold: false })), ups: upgradeOffers(run.party, 3).map(c => ({ ...c, sold: false })), inn: false };
  const shop = n.shop, innCost = 30;
  hud();
  music('m_map');
  const again = () => showShop(n);
  setScreen(h('div', {},
    h('div', { class: 'panel' },
      h('h2', {}, 'Shop'),
      h('p', {}, 'A merchant has set up a stall under a patched awning. "Gear, lessons, a warm bed. Some of it is even safe."'),
      h('h3', {}, 'Wares'),
      h('div', { class: 'cards' }, shop.items.map(it => itemCard(it.id, h('span', { class: 'price' }, it.sold ? 'Sold' : `${it.price}g`), () => {
        run.gold -= it.price; it.sold = true; giveItem(it.id, again);
      }, it.sold || run.gold < it.price))),
      h('h3', {}, 'Training'),
      h('div', { class: 'cards' }, shop.ups.map(c => {
        const s = run.party[c.hi].skills[c.si], price = upgradePrice(c);
        const can = !c.sold && upgradesFor(run.party[c.hi], s).includes(c.up);
        return upgradeCard(c, h('span', { class: 'price' }, c.sold ? 'Done' : `${price}g`), () => {
          run.gold -= price; c.sold = true; applyUpgrade(c); sfx('coin'); again();
        }, !can || run.gold < price);
      })),
      h('h3', {}, 'Inn'),
      btn(shop.inn ? 'Rested' : `Rest: heal 40% (${innCost}g)`, () => { run.gold -= innCost; shop.inn = true; healAll(0.4); sfx('heal'); again(); }, '', shop.inn || run.gold < innCost),
    ),
    btn('Leave shop', showMap, 'big go'),
  ));
  auto(() => {
    const it = shop.items.find(i => !i.sold && run.gold >= i.price);
    if (it) { run.gold -= it.price; it.sold = true; giveItem(it.id, again); return; }
    const c = shop.ups.find(x => !x.sold && upgradesFor(run.party[x.hi], run.party[x.hi].skills[x.si]).includes(x.up) && run.gold >= upgradePrice(x));
    if (c) { run.gold -= upgradePrice(c); c.sold = true; applyUpgrade(c); again(); return; }
    if (!shop.inn && run.gold >= innCost) { run.gold -= innCost; shop.inn = true; healAll(0.4); }
    showMap();
  });
}

// ---------- party ----------
function showParty() {
  if (!run) return;
  sfx('click');
  const close = () => { modal.hidden = true; modal.replaceChildren(); };
  const give = (p, i) => {
    const id = p.items.splice(i, 1)[0];
    const to = run.party[(run.party.indexOf(p) + 1) % run.party.length];
    to.items.push(id);
    for (const q of [p, to]) q.hp = Math.min(q.hp, heroStats(q, run.gold).maxHp);
    showParty();
    hud();
  };
  modal.replaceChildren(h('div', { class: 'modal-box' },
    h('div', { class: 'row' }, h('h2', { class: 'grow' }, 'Your party'), h('button', { class: 'btn', onclick: close }, 'Close')),
    h('div', { class: 'hero-cards' }, run.party.map(p => {
      const st = heroStats(p, run.gold);
      return h('div', { class: 'hero-card' },
        h('div', { class: 'card-head' }, sprImg(heroSprite(p), 'big'), h('div', { class: 'who' }, h('b', {}, heroTitle(p)), bar(p.hp, st.maxHp, false), `${p.hp}/${st.maxHp} HP`)),
        h('div', { class: 'stats' }, `ATK ${st.atk} · MAG ${st.mag} · DEF ${st.def} · RES ${st.res} · SPD ${st.spd} · MOV ${st.mov} · CRIT ${st.crit}%`),
        p.promo ? h('div', { class: 'desc' }, PROMOS[p.promo].passive) : null,
        h('div', { class: 'skill-list' }, p.skills.map(s => {
          const o = skStats(p, s);
          return h('div', {}, h('b', {}, o.name), s.ups.length ? h('span', { class: 'lv' }, ' · ' + s.ups.map(id => UPGRADES[id].name).join(', ')) : null,
            h('br'), h('span', {}, `${describe(o)}.${o.txt ? ' ' + o.txt : ''}`));
        })),
        h('h3', { style: 'margin-top:10px' }, 'Items'),
        p.items.length ? h('ul', {}, p.items.map((id, i) => h('li', {}, `${ITEMS[id].name}: ${ITEMS[id].txt} `,
          h('button', { class: 'linkbtn', onclick: () => give(p, i) }, 'pass on')))) : h('div', { class: 'muted' }, 'None'),
      );
    })),
  ));
  modal.hidden = false;
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
    h('p', {}, 'Three heroes. Three acts. A forest, a crypt and a burning mountain.'),
    saved ? btn('Continue run', () => { run = saved; env.run = run; showMap(); }, 'big go') : null,
    btn(saved ? 'New run' : 'Start run', () => { clearSave(); newRun(); }, 'big'),
    h('div', { class: 'howto' },
      h('h3', {}, 'How to play'),
      h('ul', {},
        h('li', {}, 'Each act is a branching map of battles, events (?) and shops, ending in a boss. Beating a boss lets one hero take up an advanced class.'),
        h('li', {}, 'In battle, units take turns by speed (the "Next" strip). On a hero\'s turn, move once and act once, in either order.'),
        h('li', {}, 'Walls block movement and line of sight: bolts and arrows can\'t pass them, but lobbed skills can. Lava burns, brambles cut, high ground extends range, and cover cuts damage. Tap any tile to read it.'),
        h('li', {}, 'Flank: hitting a foe that another hero stands next to deals 25% more (the Rogue gets 50%).'),
        h('li', {}, 'Upgrades can rewrite skills: swap the stat they use, turn bolts into ricochets or shields, make attacks leap, swap places or melt the floor.'),
        h('li', {}, 'HP carries between fights. On touch screens, tap a target once to preview, again to confirm.'),
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
