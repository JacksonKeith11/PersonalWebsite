// Overlords in the browser: the lobby, the board (drawn on a canvas), the shop, the players and
// traits panels. The server (app/overlords/game.py) runs the match and simulates every fight; this
// draws the boards, plays back whichever fight is being watched (fight.js), and asks to buy,
// reroll, buy XP, move and sell.

import { person, startRoom } from '../../shared/lobby.js?v=1';
import { Playback } from './fight.js?v=18';
import { isMuted, play, setMuted } from './sound.js?v=18';
import { ATLAS_URL, GROUND_AWAY, GROUND_HOME, ICON_COLS, ICONS, ICONS_URL, PORTRAITS, PORTRAITS_URL, POSES, ROWS } from './atlas.js?v=18';

const $ = id => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};
const show = screen => { for (const id of ['menu', 'lobby', 'game']) $(id).hidden = id !== screen; };
const now = () => performance.now() / 1000;

// Phones and small windows (game.css's media query must match): side panels fold into sheets, and a tap
// does what hovering does with a mouse.
const COMPACT = matchMedia('(max-width: 820px), (max-height: 560px)');
const COARSE = matchMedia('(pointer: coarse)');
let lastPointer = 'mouse'; // the kind of the latest press: 'mouse', 'touch' or 'pen'
addEventListener('pointerdown', e => { lastPointer = e.pointerType || 'mouse'; }, true);
const touchy = () => lastPointer !== 'mouse';

// Shows `what()` in the info card: on hover with a mouse; with touch, on a long press (which then
// swallows the click), or on a tap too where `tap` is set. A card shown by touch stays until closed.
function hoverInfo(elem, what, tap = false) {
  let shown = null, timer = 0, start = null, long = false;
  elem.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse' && !S.pinned) { shown = what(); pin(shown, false); } });
  elem.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse' && S.hover === shown && !S.pinned) pin(null); });
  elem.addEventListener('pointerdown', e => {
    if (e.pointerType === 'mouse') return;
    long = false;
    start = { x: e.clientX, y: e.clientY };
    clearTimeout(timer);
    timer = setTimeout(() => { long = true; pin(what(), true); play('click'); }, 450);
  });
  elem.addEventListener('pointermove', e => {
    if (start && Math.hypot(e.clientX - start.x, e.clientY - start.y) > 10) clearTimeout(timer);
  });
  for (const ev of ['pointerup', 'pointercancel']) elem.addEventListener(ev, () => { clearTimeout(timer); start = null; });
  elem.addEventListener('contextmenu', e => { if (touchy()) e.preventDefault(); });
  elem.addEventListener('click', e => {
    if (long) { long = false; e.preventDefault(); e.stopImmediatePropagation(); return; }
    if (tap && touchy()) pin(what(), true);
  }, true);
}

// Sets what the info card shows; `pinned` (by touch) keeps it until closed or replaced.
function pin(hover, pinned = false, sel = null) {
  S.hover = hover;
  S.pinned = !!hover && pinned;
  S.sel = hover ? sel : null;
  info();
}
// Pixel art as an element: a 16x16 icon (item:<key>, trait:<key>), a commander's portrait or a unit's
// idle sprite (32x32), scaled to `px` with crisp pixels.
function sheetEl(url, cell, cols, i, px, cls = 'ico') {
  const s = el('span', cls);
  s.style.width = s.style.height = px + 'px';
  if (i == null) return s;
  const k = px / cell;
  s.style.backgroundImage = `url(${url})`;
  s.style.backgroundSize = `${cols * cell * k}px auto`;
  s.style.backgroundPosition = `${-(i % cols) * px}px ${-Math.floor(i / cols) * px}px`;
  return s;
}
const icon = (name, px = 32) => sheetEl(ICONS_URL, 16, ICON_COLS, ICONS[name], px);
const portrait = (key, px = 48) => sheetEl(PORTRAITS_URL, 32, Object.keys(PORTRAITS).length + 2, PORTRAITS[key], px, 'ico portrait');
const sprite = (key, px = 64) => sheetEl(ATLAS_URL, 32, POSES.length, ROWS[key] == null ? null : ROWS[key] * POSES.length, px, 'ico sprite');
const COST_COLORS = { 0: '#7a3a3a', 1: '#8d96a5', 2: '#46a856', 3: '#3a82d6', 4: '#a456d4', 5: '#e89a30' };
const MONSTER_COLOR = '#9a4a4a';

const S = {
  cfg: null,         // units, traits and rules (from `welcome`)
  st: null,          // the latest state
  endsAt: 0,         // now() when the current phase's timer runs out
  fights: [],        // this round's fights: { home, away, pve, ghost, res }
  fightT0: 0,        // now() at the fights' t = 0
  ft: 0,             // the fight's time as played here: runs at S.speed, so it can be ahead of the server
  speed: 1,          // fight playback speed (1 or 2), remembered
  lastFrame: 0,
  watch: null,       // the player whose board or fight is shown
  pb: null,          // the watched fight's Playback
  drag: null,        // { from: {b} | {c, r}, unit, x, y }
  hover: null,       // what the pointer is over: { kind: 'board'|'bench'|'fight'|'shop', ... }
  mouse: null,       // { x, y } on the canvas
  prev: null,        // last state's numbers for this player, to know when to play sounds
  lastFights: [],    // the previous round's fights, for the damage chart while planning
  meterTab: 'dealt', // what the damage chart shows: dealt, taken or healed
  meterAt: 0,        // now() when the chart was last drawn
  pinned: false,     // the info card was opened by touch: it stays until closed or replaced
  sel: null,         // a unit tapped to move: { from: {b} | {c, r}, key }; the next tap says where it goes
  over: null,        // the bench slot or hex under a dragging pointer: { kind: 'bench', i } | { kind: 'board', c, r }
  where: null,       // the watched fight's unit positions this frame (id -> [x, y]), for taps
};

const room = startRoom({ key: 'overlords', path: '/games/overlords', title: 'Overlords', show, onMessage: receive });
if (room.debug) window.OV = { S, room, G: null, hexXY: null };
const player = id => S.st?.players.find(p => p.id === id);
const me = () => player(room.you);
const seatedMe = () => { const m = me(); return m && m.seated ? m : null; };

// ------------------------------------------------------------------ messages

function receive(m) {
  if (m.t === 'welcome') {
    S.cfg = { units: m.units, traits: m.traits, rules: m.rules, items: m.items, commanders: m.commanders,
              augments: m.augments, augTiers: m.aug_tiers, talents: m.talents };
    $('room-code').textContent = m.code;
    $('game-code').textContent = m.code;
    S.watch = m.you;
  } else if (m.t === 'state') {
    const before = S.st;
    S.st = m;
    S.endsAt = m.left != null ? now() + m.left : 0;
    if (!player(S.watch) || (before && before.phase === 'lobby' && m.phase !== 'lobby')) S.watch = room.you;
    if (m.phase !== 'fight') {
      if (S.fights.length) S.lastFights = S.fights; // the damage chart keeps showing the last round's fights
      S.fights = [];
      S.pb = null;
    } else if (!S.pb) makePlayback();
    if (m.phase === 'lobby') S.lastFights = [];
    sounds(before, m);
    render();
  } else if (m.t === 'fights') {
    S.fights = m.list;
    S.fightT0 = now() - m.elapsed;
    S.ft = m.elapsed;
    makePlayback();
    if (m.elapsed < 1) play('fight');
  } else if (m.t === 'note') {
    $('lobby-note').textContent = m.msg;
  }
}

function sounds(before, st) {
  const mine = st.players.find(p => p.id === room.you);
  if (!mine || !mine.seated) return;
  const stars = (st.me?.bench || []).filter(Boolean).map(u => u[2]).concat(mine.board.map(u => u[2]));
  const now_ = { level: mine.level, stars: stars.reduce((a, s) => a + (s - 1) * 10 + 1, 0), count: stars.length, alive: mine.alive };
  const was = S.prev;
  S.prev = now_;
  if (!before || !was || before.phase === 'lobby') return;
  if (now_.level > was.level) play('level');
  if (now_.count < was.count && now_.stars > was.stars - (was.count - now_.count)) play('star');
  if (before.phase === 'fight' && st.phase === 'plan') {
    const mineSettled = st.settled.find(s => s.id === room.you);
    if (mineSettled) play(mineSettled.dmg ? 'lost' : 'won');
    setTimeout(() => play('plan'), 600);
  }
  if (was.alive && !now_.alive) play('out');
  if (st.phase === 'over' && before.phase !== 'over' && mine.place === 1) play('victory');
}

// ------------------------------------------------------------------ the screens

function render() {
  const st = S.st;
  if (!st || !S.cfg) return;
  if (S.exiting && !seatedMe()?.alive) { leaveRoom(); return; } // the forfeit went through
  document.body.classList.toggle('host', st.host === room.you);
  if (st.phase === 'lobby') {
    show('lobby');
    renderLobby();
    $('end').hidden = true;
    return;
  }
  show('game');
  renderHud();
  renderPlayers();
  renderShop();
  renderTraits();
  renderItems();
  renderArmory();
  renderCommander();
  renderChoose();
  renderDraft();
  renderEnd();
  renderSheets();
  checkPinned();
}

// Drops a tapped unit or fight unit from the info card once it's gone (moved, sold, merged, the fight over).
function checkPinned() {
  const h = S.hover;
  if (h?.kind === 'fight' && S.st.phase !== 'fight') { pin(null); return; }
  if (!S.sel) return;
  const mine = seatedMe(), from = S.sel.from;
  const u = !mine || !S.st.me ? null : from.b != null ? S.st.me.bench[from.b]
    : S.st.phase === 'fight' ? null : mine.board.find(b => b[3] === from.c && b[4] === from.r);
  if (!u || u[1] !== S.sel.key) { pin(null); return; }
  const [items, talents, stats] = from.b != null ? [u[3], u[4], u[5]] : [u[5], u[6], u[7]];
  if (u[2] !== h.star || JSON.stringify([items, talents, stats]) !== JSON.stringify([h.items || [], h.talents || [], h.stats])
      || !!talentOffer(u[0]) !== !!h.offer) {
    pin({ ...h, star: u[2], items, talents, stats, offer: !!talentOffer(u[0]) }, true, S.sel);
  }
}

// The sheet buttons beside the items (phones): which have something to show, and the power when it's ready.
function renderSheets() {
  const tabs = document.querySelectorAll('#sheet-tabs button');
  const has = { traits: true, cmd: !$('commander-box').hidden || !$('augments-box').hidden, meter: !$('meter').hidden };
  const mine = seatedMe(), me_ = S.st.me;
  const powerReady = mine?.alive && me_ && S.st.phase === 'plan' && !me_.next_fx && me_.charge >= (me_.charge_need ?? 99);
  for (const b of tabs) {
    b.disabled = !has[b.dataset.sheet];
    b.setAttribute('aria-pressed', String(document.body.dataset.sheet === b.dataset.sheet));
    if (b.dataset.sheet === 'cmd') {
      b.classList.toggle('ready', !!powerReady);
      b.textContent = powerReady ? 'Power ⚡' : mine?.commander ? 'Commander' : 'Augments';
    }
  }
  const open = document.body.dataset.sheet;
  if (open && !has[open]) openSheet('');
}

function openSheet(name) {
  if (name && S.pinned) pin(null); // a sheet and a tapped unit's card together would hide the board
  if (name) document.body.dataset.sheet = name;
  else delete document.body.dataset.sheet;
  for (const b of document.querySelectorAll('#sheet-tabs button')) b.setAttribute('aria-pressed', String(name === b.dataset.sheet));
}

// ------------------------------------------------------------------ items, commander, augments, draft

// Item rarities: Common, Rare, Epic, Legendary (the same hues as the unit tiers 1, 3, 4 and 5).
const RARITY_COLORS = { 1: '#8d96a5', 2: '#3a82d6', 3: '#a456d4', 4: '#e89a30' };
const rarityColor = key => RARITY_COLORS[S.cfg.items[key]?.rarity] || '#666';
const rarityName = key => S.cfg.rules.rarities[S.cfg.items[key]?.rarity] || '';

function renderItems() {
  const box = $('items'), st = S.st;
  const items = st.me?.items || [];
  if (S.pickedItem != null && S.pickedItem >= items.length) S.pickedItem = null;
  if (!items.length) { box.replaceChildren(el('span', 'none', 'None yet: buy some in the armory')); return; }
  box.replaceChildren(...items.map((key, i) => {
    const d = S.cfg.items[key];
    const b = el('button', 'item r' + d.rarity);
    b.style.setProperty('--rc', rarityColor(key));
    b.type = 'button';
    b.append(icon('item:' + key, 32));
    b.setAttribute('aria-label', d.name);
    b.classList.toggle('picked', S.pickedItem === i);
    b.addEventListener('pointerdown', e => {
      S.drag = { item: i, key, from: {}, moved: false };
      S.dragStart = { x: e.clientX, y: e.clientY };
      b.releasePointerCapture?.(e.pointerId);
    });
    hoverInfo(b, () => ({ kind: 'item', item: key, bench: true }));
    return b;
  }));
}

// The armory: whole items for gold, their rarities by the round. A tap or click buys; hover or a long press
// shows what it does.
function renderArmory() {
  const box = $('armory'), st = S.st, mine = seatedMe();
  const stock = st.me?.armory || [];
  box.hidden = !mine || !mine.alive || !stock.length;
  if (box.hidden) return;
  box.replaceChildren(el('span', 'armory-label', 'Armory'), ...stock.map((key, i) => {
    if (!key) {
      const gone = el('span', 'slot');
      gone.title = 'Bought: new stock next round';
      return gone;
    }
    const d = S.cfg.items[key];
    const price = st.me.armory_prices?.[i] ?? S.cfg.rules.item_price[d.rarity];
    const b = el('button', 'buy-item r' + d.rarity);
    b.style.setProperty('--rc', rarityColor(key));
    b.type = 'button';
    b.append(icon('item:' + key, 24), el('span', 'price', `${price}g`));
    b.setAttribute('aria-label', `Buy ${d.name} (${rarityName(key)}) for ${price} gold`);
    b.disabled = mine.gold < price;
    b.addEventListener('click', () => { room.send({ t: 'buy_item', i }); play('buy'); });
    hoverInfo(b, () => ({ kind: 'item', item: key, price }));
    return b;
  }));
}

// A trait in a line: what it does at each tier (augment cards and emblems).
function traitLine(t) {
  const def = S.cfg.traits[t];
  return `${def.name}: ${def.text} (` + def.levels.map((n, i) => `${n}: ${describeFx(def.fx[i])}${def.fx[i].who === 'team' ? ' for the whole board' : ''}`).join(' · ') + ')';
}

// Extra abilities (picked at 2 and 3 stars): the name, with the unit's own ability's name filled in.
const talentName = (tk, key) => S.cfg.talents[tk].name.replace('{ability}', S.cfg.units[key].ability?.name || 'Ability');
const talentOffer = id => S.st?.me?.talent_offers?.find(o => o.id === id);

function chooseTalent(id) {
  S.talentFor = id;
  S.chooseHidden = null;
  renderChoose();
}

function renderCommander() {
  const st = S.st, mine = seatedMe();
  const box = $('commander-box');
  box.hidden = !mine || !mine.commander;
  if (!box.hidden) {
    const c = S.cfg.commanders[mine.commander];
    $('commander-name').replaceChildren(portrait(mine.commander, 40), document.createTextNode(c.name));
    $('commander-passive').textContent = c.passive;
    const charge = st.me?.charge ?? 0, need = st.me?.charge_need ?? c.charge;
    const ready = charge >= need;
    $('power').textContent = st.me?.next_fx ? 'Power used: ready for the next fight' : ready ? 'Use power' : `Power charging: ${charge}/${need} rounds`;
    $('power').disabled = !ready || st.phase !== 'plan' || !mine.alive;
    $('power').classList.toggle('primary', ready && st.phase === 'plan');
    $('power-text').textContent = c.power;
  }
  const augs = (S.watch === room.you ? mine : player(S.watch))?.augments || [];
  $('augments-box').hidden = !augs.length;
  $('augments').replaceChildren(...augs.map(k => {
    const a = S.cfg.augments[k];
    const li = el('li');
    li.append(el('b', '', a.name), el('small', '', ` · ${a.text}`));
    if (a.trait) hoverInfo(li, () => ({ kind: 'trait', trait: a.trait }), true);
    return li;
  }));
}

function renderChoose() {
  const st = S.st, mine = seatedMe();
  const me_ = st.me;
  let mode = null;
  if (mine && mine.alive && me_ && !mine.commander && me_.offers?.length && st.phase !== 'over') mode = 'commander';
  else if (mine && mine.alive && me_?.aug_offer?.length && st.phase !== 'over') mode = 'augment';
  let offer = null;
  if (!mode && mine && mine.alive && me_?.talent_offers?.length && ['plan', 'fight'].includes(st.phase)) {
    mode = 'talent';
    offer = talentOffer(S.talentFor) || me_.talent_offers[0];
  }
  const key = !mode ? '' : mode === 'talent' ? `talent${offer.id}:${offer.star}`
    : mode + (mode === 'commander' ? me_.offers.join() : me_.aug_offer.join()) + me_.aug_rerolled;
  $('choose').hidden = !mode || S.chooseHidden === key;
  $('choose-show').hidden = !mode || S.chooseHidden !== key;
  $('choose-show').textContent = mode === 'commander' ? 'Choose your commander' : mode === 'talent'
    ? `Choose an extra ability${me_.talent_offers.length > 1 ? ` (${me_.talent_offers.length} waiting)` : ''}` : 'Choose your augment';
  $('choose-show').classList.toggle('talent', mode === 'talent'); // phones: the + on the unit and its card instead
  $('choose-hide').textContent = mode === 'talent' ? 'Later' : 'Look at the board first';
  $('choose-note').textContent = mode === 'commander' ? 'The first fight waits until everyone has chosen.'
    : mode === 'talent' ? 'It fights without one until you choose. You can also choose from its card.'
    : `If you haven't chosen when the fight starts, the first is taken for you.`;
  if (key === S.chooseKey) return;
  S.chooseKey = key;
  if (!mode) return;
  const opts = $('choose-options');
  opts.classList.toggle('four', mode === 'talent' && offer.options.length > 3);
  if (mode === 'commander') {
    $('choose-kicker').textContent = 'Before the first fight';
    $('choose-title').textContent = 'Choose your commander';
    $('choose-reroll').hidden = true;
    opts.replaceChildren(...me_.offers.map(k => {
      const c = S.cfg.commanders[k];
      const b = el('button');
      b.type = 'button';
      const head = el('span', 'head');
      head.append(portrait(k, 64), el('b', '', c.name));
      b.append(head, el('span', '', c.passive), el('small', '', `Power (every ${c.charge} rounds): ${c.power}`));
      b.addEventListener('click', () => { room.send({ t: 'commander', k }); play('level'); });
      return b;
    }));
  } else if (mode === 'talent') {
    const u = S.cfg.units[offer.unit];
    $('choose-kicker').textContent = `${u.name} reached ${'★'.repeat(offer.star)}`;
    $('choose-title').textContent = 'Choose an extra ability';
    $('choose-reroll').hidden = true;
    const own = el('p', 'own-ab');
    const said = el('span');
    said.append(el('b', '', u.ability.name + ': '), document.createTextNode(u.ability.text));
    own.append(sprite(offer.unit, 40), said);
    opts.replaceChildren(own, ...offer.options.map(k => {
      const t = S.cfg.talents[k];
      const b = el('button');
      b.type = 'button';
      const head = el('span', 'head');
      head.append(t.trait ? icon('trait:' + t.trait, 32) : sprite(offer.unit, 32), el('b', '', talentName(k, offer.unit)));
      b.append(el('span', 'tag', t.trait ? S.cfg.traits[t.trait].name : 'Its own ability'), head, el('span', '', t.text));
      b.addEventListener('click', () => { room.send({ t: 'talent', id: offer.id, k }); play('star'); S.talentFor = null; });
      return b;
    }));
  } else {
    const tier = S.cfg.augments[me_.aug_offer[0]].tier;
    $('choose-kicker').textContent = `${S.cfg.augTiers[tier]} augment`;
    $('choose-title').textContent = 'Choose an augment';
    $('choose-reroll').hidden = me_.aug_rerolled;
    opts.replaceChildren(...me_.aug_offer.map(k => {
      const a = S.cfg.augments[k];
      const b = el('button');
      b.type = 'button';
      const head = el('span', 'head');
      if (a.trait) head.append(icon('trait:' + a.trait, 32));
      head.append(el('b', '', a.name));
      b.append(el('span', 'tag', S.cfg.augTiers[a.tier]), head, el('span', '', a.text));
      if (a.trait) b.append(el('small', 'about', traitLine(a.trait)));
      b.addEventListener('click', () => { room.send({ t: 'augment', k }); play('star'); });
      return b;
    }));
  }
}

function renderDraft() {
  const st = S.st, d = st.draft;
  $('draft').hidden = st.phase !== 'draft' || !d;
  if ($('draft').hidden) return;
  const turn = player(d.turn);
  const mineTurn = d.turn === room.you;
  $('draft-title').textContent = mineTurn ? 'Your pick!' : `Draft: ${turn?.name || '…'} is picking`;
  const order = d.order.map(id => player(id)?.name).join(' → ');
  const r = S.cfg.items[d.options[0]?.[1]]?.rarity;
  const holds = r ? `${r === 2 ? 'a' : 'an'} ${S.cfg.rules.rarities[r]} item` : 'an item';
  $('draft-note').textContent = `Lowest HP picks first: ${order}. Each unit comes holding ${holds}.`;
  $('draft-options').replaceChildren(...d.options.map(([key, item, by], i) => {
    const u = S.cfg.units[key], it = S.cfg.items[item];
    const b = el('button', by ? 'taken' : '');
    b.type = 'button';
    b.style.setProperty('--cc', COST_COLORS[u.tier]);
    const hold = el('span', 'hold');
    hold.append(icon('item:' + item, 24), document.createTextNode(`holding ${/^[AEIOU]/.test(it.name) ? 'an' : 'a'} ${it.name}`));
    hold.title = it.text;
    b.append(sprite(key, 64), el('b', '', u.name), el('small', '', u.traits.map(t => S.cfg.traits[t].name).join(' · ')), hold);
    if (by) b.append(el('span', 'by', `taken by ${player(by)?.name || '?'}`));
    b.disabled = !mineTurn || !!by;
    b.addEventListener('click', () => { room.send({ t: 'pick', i }); play('buy'); });
    hoverInfo(b, () => ({ kind: 'shop', key }));
    return b;
  }));
}

function renderLobby() {
  const st = S.st;
  const seats = $('seats');
  seats.replaceChildren(...st.players.map(p => person(p, room.you, p.id === st.host ? 'host' : p.seated ? '' : 'watching')));
  const n = st.players.filter(p => p.seated).length;
  $('count').textContent = `${n} / ${S.cfg.rules.max}`;
  const host = st.host === room.you;
  $('bots').checked = st.bots;
  $('bots').disabled = !host;
  $('bot-level').value = st.level;
  $('bot-level').disabled = !host;
  $('lobby-note').textContent = host
    ? (st.bots ? `Bots will fill ${Math.max(0, S.cfg.rules.max - n)} empty seat${S.cfg.rules.max - n === 1 ? '' : 's'}.` : n < 2 ? 'Without bots you need a friend to play against.' : '')
    : 'Waiting for the host to start.';
  renderRecords();
}

const traitList = traits => Object.entries(traits || {}).sort((a, b) => b[1] - a[1])
  .map(([t, n]) => `${S.cfg.traits[t]?.name || t} ${n}`).join(', ');
const when = at => new Date(at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

function renderRecords() {
  const st = S.st, rec = st.record;
  const box = $('my-record');
  if (!rec) box.replaceChildren(el('p', 'note', 'No finished matches yet: play one to start your record.'));
  else {
    const head = el('p', '', `${rec.games} match${rec.games === 1 ? '' : 'es'}, ${rec.wins} win${rec.wins === 1 ? '' : 's'}, `
      + `${rec.top2} top-two finish${rec.top2 === 1 ? '' : 'es'}, average place ${rec.avg}.`);
    const fav = el('p', 'note', [rec.commander && `Favourite commander: ${S.cfg.commanders[rec.commander]?.name}`,
      rec.trait && `most played trait: ${S.cfg.traits[rec.trait]?.name}`].filter(Boolean).join(' · '));
    const list = el('ul');
    for (const r of rec.recent) {
      list.append(el('li', '', `${when(r.at)}: ${ordinal(r.place)} of ${r.of} after ${r.rounds} rounds`
        + (r.commander ? ` as ${S.cfg.commanders[r.commander]?.name}` : '') + (traitList(r.traits) ? ` (${traitList(r.traits)})` : '')));
    }
    box.replaceChildren(head, fav, list);
  }
  const leaders = st.leaders || [];
  $('leaders').replaceChildren(...(leaders.length ? leaders.map(l => el('li', '', `${l.name}: ${l.wins} win${l.wins === 1 ? '' : 's'} in ${l.games} (average ${l.avg})`))
    : [el('li', 'note', 'Nobody has won yet.')]));
}

function renderHud() {
  const st = S.st, mine = seatedMe();
  $('hud-round').textContent = `Round ${st.round}${st.pve ? ' · Monsters' : ''}`;
  if (mine) {
    $('hud-hp').innerHTML = `HP <b>${Math.max(0, mine.hp)}</b>`;
    $('hud-hp').classList.toggle('low', mine.hp <= 20);
    const inc = st.me?.income;
    $('hud-gold').innerHTML = `Gold <b>${mine.gold}</b>` + (inc && mine.alive ? ` <small>+${inc[0] + inc[1] + inc[2]} next round</small>` : '');
    $('hud-gold').title = inc ? `Next round: ${inc[0]} income, ${inc[1]} interest (1 for every 10 gold you keep)`
      + (inc[2] ? `, ${inc[2]} for your ${mine.streak > 0 ? 'winning' : 'losing'} streak` : '') : '';
    const need = st.me?.need;
    $('hud-level').textContent = COMPACT.matches
      ? `Lv ${mine.level}${need ? ` · ${st.me.xp}/${need} XP` : ''} · Board ${mine.board.length}/${mine.limit}`
      : `Level ${mine.level}${need ? ` · ${st.me.xp}/${need} XP` : ''} · ${mine.board.length}/${mine.limit} on board`;
    $('hud-level').title = 'Your level is how many units may stand on your board. Buy XP to level up; you also get 2 XP a round.';
  } else {
    $('hud-hp').textContent = 'Watching';
    $('hud-gold').textContent = $('hud-level').textContent = '';
  }
  const can = mine && mine.alive && st.me;
  $('xp').disabled = !can || mine.gold < S.cfg.rules.xp_cost || mine.level >= S.cfg.rules.max_level;
  const free = st.me?.free_rerolls || 0;
  const rc = st.me?.reroll_cost ?? S.cfg.rules.reroll;
  $('reroll').disabled = !can || (mine.gold < rc && !free);
  $('reroll').innerHTML = free ? `Reroll <small>free ×${free}<span class="key"> · D</span></small>` : `Reroll <small>${rc}g<span class="key"> · D</span></small>`;
  $('lock').disabled = !can;
  $('lock').setAttribute('aria-pressed', String(!!st.me?.locked));
  $('ready').disabled = !can || st.phase !== 'plan';
  $('ready').textContent = mine?.ready ? 'Ready ✓' : 'Ready';
  $('ready').title = mine?.ready ? 'Click again if you are not ready after all.' : 'End planning early once everyone is ready (Space).';
  $('lock').textContent = st.me?.locked ? 'Shop locked' : 'Lock shop';
  $('lock').title = 'A locked shop keeps the same units into the next round.';
  renderOdds();
  $('mute').textContent = isMuted() ? '🔇' : '🔊';
  $('speed').textContent = COMPACT.matches ? `${S.speed}×` : `Fights ${S.speed}×`;
  $('speed').setAttribute('aria-pressed', String(S.speed === 2));
  $('mute').setAttribute('aria-pressed', String(isMuted()));
}

// What the shop can roll at your level (the Oracle rolls a level higher): a chip a tier.
function renderOdds() {
  const mine = seatedMe(), box = $('odds');
  if (!mine || !mine.alive) { box.replaceChildren(); return; }
  const level = Math.min(S.cfg.rules.max_level, mine.level + (mine.commander === 'oracle' && mine.level >= 5 ? 1 : 0));
  const odds = S.cfg.rules.odds[level];
  box.replaceChildren(el('span', 'label', 'Shop odds'), ...odds.map((pct, i) => {
    const chip = el('span', 'chip' + (pct ? '' : ' none'), `${pct}%`);
    chip.style.setProperty('--cc', COST_COLORS[i + 1]);
    chip.title = `Tier ${i + 1} (${[1, 2, 3, 5, 8][i]} gold): ${pct}% of each slot at level ${level}`;
    return chip;
  }));
}

function tickHud() {
  const st = S.st;
  if (!st || st.phase === 'lobby') return;
  const left = Math.max(0, Math.ceil(S.endsAt - now()));
  const waiting = st.phase === 'plan' && left <= 0 && st.choosing?.length;
  const phase = waiting ? (st.choosing.includes(room.you) ? 'Waiting for you' : 'Waiting')
    : st.phase === 'plan' ? `Planning · ${left}s` : st.phase === 'fight' ? 'Fighting'
    : st.phase === 'draft' ? `Draft · ${left}s` : 'Game over';
  $('hud-phase').textContent = phase;
  $('hud-phase').classList.toggle('hurry', st.phase === 'plan' && left <= 5);
  banner();
}

function banner() {
  const st = S.st, b = $('banner');
  const w = player(S.watch);
  if (st.phase === 'fight') {
    const f = fightOf(S.watch);
    if (!f) { b.textContent = w ? `${w.name} isn't fighting this round.` : ''; return; }
    const home = player(f.home), away = f.pve ? null : player(f.away);
    const t = S.ft;
    let text = `<b>${esc(home?.name)}</b> vs <b>${f.pve ? 'Monsters' : esc(away?.name) + (f.ghost ? ' (a copy)' : '')}</b>`;
    if (t >= f.res.time) {
      const winner = f.res.winner;
      const youSide = f.home === room.you ? 0 : f.away === room.you ? 1 : null;
      if (winner == null) text += ' · <span class="lost">time ran out: both lose</span>';
      else if (youSide != null) text += winner === youSide ? ' · <span class="won">you won</span>' : ' · <span class="lost">you lost</span>';
      else text += ` · <b>${esc(winner === 0 ? home?.name : f.pve ? 'Monsters' : away?.name)}</b> won`;
    }
    b.innerHTML = text;
  } else if (st.phase === 'plan') {
    const mine = st.settled.find(s => s.id === room.you);
    const parts = [];
    if (S.watch !== room.you && w) parts.push(`Looking at <b>${esc(w.name)}</b>'s board`);
    if (mine && st.round > 1 && S.watch === room.you) parts.push(mine.dmg ? `<span class="lost">Last fight cost you ${mine.dmg} HP</span>` : '<span class="won">You won your last fight</span>');
    if (st.choosing?.length && S.endsAt - now() <= 0) {
      const names = st.choosing.filter(id => id !== room.you).map(id => esc(player(id)?.name));
      if (st.choosing.includes(room.you)) parts.push('<span class="hint">Everyone is waiting for you to choose a commander</span>');
      if (names.length) parts.push(`<span class="hint">Waiting for ${names.join(' and ')} to choose a commander</span>`);
    }
    if (st.pve) parts.push('Monsters this round');
    const mine2 = seatedMe();
    const waiting = (st.me?.bench || []).filter(Boolean).length;
    if (mine2?.alive && S.watch === room.you && waiting >= S.cfg.rules.bench) {
      parts.push(`<span class="hint">Your bench is full: ${COARSE.matches ? 'tap a unit and press Sell' : 'drag a unit onto the shop to sell it'}</span>`);
    }
    if (mine2?.alive && S.watch === room.you && mine2.board.length < mine2.limit && waiting) {
      const free = mine2.limit - mine2.board.length;
      parts.push(`<span class="hint">${free} empty place${free === 1 ? '' : 's'} on your board: filled from your bench when the fight starts</span>`);
    }
    b.innerHTML = parts.join(' · ');
  } else {
    b.textContent = '';
  }
}

const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

function renderPlayers() {
  const st = S.st;
  const list = st.players.filter(p => p.seated).sort((a, b) => (b.alive - a.alive) || (b.hp - a.hp) || ((a.place || 0) - (b.place || 0)));
  $('players').replaceChildren(...list.map(p => {
    const li = el('li');
    li.classList.toggle('watched', p.id === S.watch);
    li.classList.toggle('out', !p.alive);
    li.classList.toggle('off', !p.bot && !p.on);
    const dot = p.commander ? portrait(p.commander, 24) : el('span', 'dot');
    dot.classList.add('dot');
    dot.style.setProperty('--c', p.color);
    if (p.commander) dot.title = S.cfg.commanders[p.commander].name;
    const name = el('span', 'name', p.name);
    if (p.id === room.you) name.append(el('span', 'extra', ' (you)'));
    if (p.bot) name.append(el('span', 'extra', ' 🤖'));
    const hp = el('span', 'hp', p.alive ? String(Math.max(0, p.hp)) : `#${p.place}`);
    const bar = el('span', 'bar');
    const fill = el('i');
    fill.style.width = `${Math.max(0, Math.min(100, (100 * p.hp) / S.cfg.rules.start_hp))}%`;
    bar.append(fill);
    const sub = el('span', 'sub');
    sub.append(el('span', '', `Lv ${p.level}`), el('span', '', `${p.gold}g`));
    if (Math.abs(p.streak) >= 2) sub.append(el('span', p.streak > 0 ? 'w' : 'l', `${p.streak > 0 ? 'win' : 'loss'} streak ${Math.abs(p.streak)}`));
    if (st.phase === 'plan' && p.ready && !p.bot) sub.append(el('span', 'w', 'ready'));
    if (p.results?.length) {
      const dots = el('span', 'results');
      dots.title = 'Their last fights: won, lost or drawn';
      for (const r of p.results) dots.append(el('i', r, ''));
      sub.append(dots);
    }
    li.append(dot, name, hp, bar, sub);
    li.addEventListener('click', () => {
      S.watch = p.id;
      if (S.hover?.kind === 'fight' || S.hover?.kind === 'board') pin(null);
      makePlayback();
      render();
      play('click');
    });
    return li;
  }));
}

function renderShop() {
  const st = S.st, mine = seatedMe();
  const shop = $('shop');
  if (!mine || !st.me) { shop.replaceChildren(); return; }
  shop.style.setProperty('--n', st.me.shop.length);
  const owned = {};
  for (const u of [...mine.board.map(u => [u[0], u[1], u[2]]), ...st.me.bench.filter(Boolean)]) {
    if (u[2] === 1) owned[u[1]] = (owned[u[1]] || 0) + 1;
  }
  shop.replaceChildren(...st.me.shop.map((key, i) => {
    if (!key) return el('div', 'empty');
    const d = S.cfg.units[key];
    const b = el('button', 'card');
    b.type = 'button';
    b.style.setProperty('--cc', COST_COLORS[d.tier]);
    const tr = el('span', 'tr');
    for (const t of d.traits) {
      const one = el('span');
      one.append(icon('trait:' + t, 16), document.createTextNode(S.cfg.traits[t].name));
      tr.append(one);
    }
    b.append(sprite(key, 64), el('b', '', d.name), tr, el('span', 'cost', `${d.cost}g`));
    const n = owned[key] || 0;
    if (n) {
      b.classList.add('pair');
      b.classList.toggle('merge', n >= 2);
      b.append(el('span', 'copies', n >= 2 ? '★★ on buy' : `${n} of 3`));
    }
    const benchFull = !st.me.bench.some(x => !x) && n < 2;
    b.disabled = !mine.alive || mine.gold < d.cost || benchFull;
    b.title = benchFull ? 'Your bench is full: sell or place a unit first.' : mine.gold < d.cost ? `Costs ${d.cost} gold.` : '';
    b.addEventListener('click', () => { room.send({ t: 'buy', i }); play('buy'); });
    hoverInfo(b, () => ({ kind: 'shop', key }));
    return b;
  }));
}

function renderTraits() {
  const w = player(S.watch);
  $('traits-title').textContent = w && w.id !== room.you ? `${w.name}'s traits` : 'Traits';
  const counts = w ? w.traits : {};
  const rows = Object.entries(counts).map(([t, n]) => {
    const def = S.cfg.traits[t];
    let level = -1;
    def.levels.forEach((need, i) => { if (n >= need) level = i; });
    return { t, n, def, level };
  }).sort((a, b) => (b.level - a.level) || (b.n - a.n) || a.def.name.localeCompare(b.def.name));
  $('traits').replaceChildren(...rows.map(({ t, n, def, level }) => {
    const li = el('li', level >= 0 ? 'on' : '');
    const next = def.levels.find(need => need > n);
    const name = el('b');
    name.append(icon('trait:' + t, 16), document.createTextNode(def.name));
    li.append(name, el('span', 'lv', next ? `${n} / ${next}` : String(n)));
    const steps = el('span', 'steps');
    def.levels.forEach((need, i) => steps.append(el('i', i === level ? 'on' : i < level ? 'past' : '', String(need))));
    li.append(steps);
    const fx = def.fx[Math.max(0, level)];
    li.append(el('small', 'fx', (level >= 0 ? '' : `At ${def.levels[0]}: `) + describeFx(fx) + (fx.who === 'team' ? ' (whole board)' : '')));
    hoverInfo(li, () => ({ kind: 'trait', trait: t }), true);
    return li;
  }));
  if (!rows.length) $('traits').replaceChildren(el('li', '', 'No units on the board yet.'));
}

function renderEnd() {
  const st = S.st;
  $('end').hidden = st.phase !== 'over';
  if (st.phase !== 'over') return;
  const ranked = st.players.filter(p => p.seated).sort((a, b) => a.place - b.place);
  const mine = seatedMe();
  $('end-kicker').textContent = `After ${st.round} rounds`;
  $('end-title').textContent = mine ? (mine.place === 1 ? 'You are the last overlord standing!' : `You came ${ordinal(mine.place)}`) : `${ranked[0]?.name} wins`;
  $('end-rows').replaceChildren(...ranked.map(p => {
    const li = el('li');
    const sw = el('i', 'swatch');
    sw.style.background = p.color;
    li.append(sw, document.createTextNode(`${p.name}${p.bot ? ' (bot)' : ''}${p.place === 1 ? ` · ${p.hp} HP left` : ''}`));
    const parts = [p.commander && S.cfg.commanders[p.commander]?.name, traitList(p.final?.traits)].filter(Boolean);
    if (parts.length) li.append(el('small', '', parts.join(' · ')));
    return li;
  }));
  hpChart(ranked);
  const rec = st.record;
  $('end-record').textContent = rec ? `Your record: ${rec.wins} win${rec.wins === 1 ? '' : 's'} in ${rec.games} match${rec.games === 1 ? '' : 'es'}, average place ${rec.avg}.` : '';
}

// The end screen's line chart: each player's HP after each round, in their colour, named at the end of
// their line; hovering shows a round's numbers.
function hpChart(players) {
  const fig = $('end-chart');
  const logs = players.filter(p => p.hp_log?.length > 1);
  fig.hidden = !logs.length;
  if (!logs.length) return;
  const NS = 'http://www.w3.org/2000/svg';
  const mk = (tag, attrs, text) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (text != null) e.textContent = text;
    return e;
  };
  const W = 460, H = 190, L = 30, R = 92, T = 10, B = 24;
  const rounds = Math.max(...logs.map(p => p.hp_log.length - 1));
  const top = S.cfg.rules.start_hp;
  const x = i => L + ((W - L - R) * i) / Math.max(1, rounds);
  const y = hp => T + ((H - T - B) * (1 - Math.max(0, hp) / top));
  const svg = mk('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': "Each player's HP after each round" });
  for (const hp of [0, top / 2, top]) { // a recessive grid
    svg.append(mk('line', { x1: L, x2: W - R, y1: y(hp), y2: y(hp), class: 'grid' }));
    svg.append(mk('text', { x: L - 6, y: y(hp) + 4, class: 'axis', 'text-anchor': 'end' }, String(hp)));
  }
  const step = Math.max(1, Math.ceil(rounds / 8));
  for (let i = 0; i <= rounds; i += step) svg.append(mk('text', { x: x(i), y: H - 6, class: 'axis', 'text-anchor': 'middle' }, String(i)));
  const ends = [];
  for (const p of logs) {
    const pts = p.hp_log.map((hp, i) => `${x(i).toFixed(1)},${y(hp).toFixed(1)}`).join(' ');
    svg.append(mk('polyline', { points: pts, class: 'line', stroke: p.color }));
    const last = p.hp_log.length - 1;
    svg.append(mk('circle', { cx: x(last), cy: y(p.hp_log[last]), r: 4, fill: p.color, class: 'end' }));
    ends.push({ p, x: x(last), y: y(p.hp_log[last]) });
  }
  ends.sort((a, b) => a.y - b.y); // names at the line ends, nudged apart and kept inside the plot
  const ly = ends.map(e => e.y + 4);
  for (let i = 1; i < ly.length; i++) ly[i] = Math.max(ly[i], ly[i - 1] + 13);
  const over = ly.length ? ly[ly.length - 1] - (H - B + 2) : 0;
  if (over > 0) {
    for (let i = 0; i < ly.length; i++) ly[i] -= over;
    for (let i = ly.length - 2; i >= 0; i--) ly[i] = Math.min(ly[i], ly[i + 1] - 13);
  }
  ends.forEach((e, i) => svg.append(mk('text', { x: e.x + 8, y: ly[i], class: 'name' }, e.p.name.slice(0, 14))));
  const cross = mk('line', { y1: T, y2: H - B, class: 'cross', visibility: 'hidden' });
  svg.append(cross);
  const tip = el('div', 'tip');
  tip.hidden = true;
  svg.addEventListener('pointermove', ev => {
    const r = svg.getBoundingClientRect();
    const px = ((ev.clientX - r.left) / r.width) * W;
    const i = Math.max(0, Math.min(rounds, Math.round(((px - L) / (W - L - R)) * rounds)));
    cross.setAttribute('x1', x(i));
    cross.setAttribute('x2', x(i));
    cross.setAttribute('visibility', 'visible');
    tip.hidden = false;
    tip.replaceChildren(el('b', '', i ? `After round ${i}` : 'Start'), ...logs.map(p => {
      const line = el('span');
      const sw = el('i', 'swatch');
      sw.style.background = p.color;
      line.append(sw, document.createTextNode(`${p.name}: ${p.hp_log[i] != null ? p.hp_log[i] + ' HP' : 'out'}`));
      return line;
    }));
    tip.style.left = `${(x(i) / W) * 100}%`;
  });
  svg.addEventListener('pointerleave', () => { cross.setAttribute('visibility', 'hidden'); tip.hidden = true; });
  fig.querySelector('.plot').replaceChildren(svg, tip);
}

const ordinal = n => n + (['th', 'st', 'nd', 'rd'][n % 10 > 3 || Math.floor(n / 10) === 1 ? 0 : n % 10] || 'th');

// The info card: what's under the pointer, or what was tapped (with a close button, and Sell for your units).
function info() {
  infoBody();
  const box = $('info');
  box.classList.toggle('pinned', S.pinned);
  if (!box.childElementCount) return;
  const close = el('button', 'sheet-close', '×');
  close.type = 'button';
  close.setAttribute('aria-label', 'Close');
  close.addEventListener('click', () => { pin(null); play('click'); });
  box.prepend(close);
  if (S.sel && S.hover?.key) {
    const d = S.cfg.units[S.hover.key];
    const from = S.sel.from;
    const locked = from.c != null && S.st.phase !== 'plan'; // the board is locked mid-fight
    for (const li of box.querySelectorAll('ul.held li')) { // each of its items gets a button to take it off
      const k = +li.dataset.k;
      const off = el('button', '', 'Take off');
      off.type = 'button';
      off.disabled = locked;
      off.title = locked ? 'Not while it fights' : 'Back to your items';
      off.addEventListener('click', () => { room.send({ t: 'unequip', from, k }); play('click'); });
      li.append(off);
    }
    const offer = talentOffer(S.hover.id);
    if (offer) {
      const pick = el('button', 'primary pick', `Choose its ${'★'.repeat(offer.star)} extra ability`);
      pick.type = 'button';
      pick.addEventListener('click', () => { chooseTalent(offer.id); play('click'); });
      box.append(pick);
    }
    const row = el('div', 'sell-row');
    const sell = el('button', 'sell', `Sell for ${d.cost * 3 ** ((S.hover.star || 1) - 1)} gold`);
    sell.type = 'button';
    sell.disabled = locked;
    sell.addEventListener('click', () => { room.send({ t: 'sell', from }); play('sell'); pin(null); });
    row.append(sell);
    const hint = touchy() ? el('p', 'note', 'Tap an empty place or bench slot to move it there.') : null;
    if (COMPACT.matches) { // a phone's card is short and scrolls: what to do with the unit goes under its name
      box.querySelector('p.kind').after(...[box.querySelector('button.pick'), row, hint].filter(Boolean));
    } else {
      if (hint) box.append(hint);
      box.append(row);
    }
  }
}

// ------------------------------------------------------------------ the info card
// One card for whatever is hovered, long-pressed or tapped: a unit (shop, bench, board or fight), an item or
// a trait. A unit's numbers are the server's (sim.Unit.stats: traits, items, extra abilities and the
// commander counted), shown beside what it would have bare; its traits say what they're doing for it.

function infoBody() {
  const box = $('info');
  const h = S.hover;
  if (!h) { box.replaceChildren(); return; }
  if (h.kind === 'item') { box.replaceChildren(...itemCard(h)); return; }
  if (h.kind === 'trait') { box.replaceChildren(...traitCard(h.trait)); return; }
  const d = S.cfg.units[h.key];
  box.replaceChildren(...(d ? unitCard(h, d) : []));
}

function itemCard(h) {
  const d = S.cfg.items[h.item];
  const head = el('h3', 'with-art');
  head.append(icon('item:' + h.item, 32), document.createTextNode(d.name));
  const kind = { artifact: 'artifact', emblem: 'emblem' }[d.kind] || 'item';
  const tag = el('p', 'rarity', `${rarityName(h.item)} ${kind}${h.price ? ` · ${h.price} gold` : ''}`);
  tag.style.setProperty('--rc', rarityColor(h.item));
  const parts = [head, tag, el('p', 'effect', d.text)];
  if (d.stats) parts.push(labelled('Also', d.stats));
  if (d.trait) {
    const def = S.cfg.traits[d.trait];
    parts.push(labelled(def.name, def.text), traitTiers(d.trait, me()?.traits?.[d.trait] || 0));
  }
  const hint = h.price ? (touchy() ? 'Tap to buy: it goes to your items.' : 'Click to buy: it goes to your items.')
    : h.bench ? (touchy() ? 'Tap it, then one of your units, to give it. ' : 'Drag it onto one of your units, or click it and then the unit. ')
      + `A unit holds ${S.cfg.rules.max_items}; Take off on the unit's card gives it back.` : '';
  if (hint) parts.push(el('p', 'note', hint));
  return parts;
}

// "Label: text" in a paragraph.
function labelled(label, text, cls = '') {
  const p = el('p', cls);
  p.append(el('b', '', label + ': '), document.createTextNode(text));
  return p;
}

// A trait's tiers as a list, the tier reached at `n` units marked.
function traitTiers(t, n) {
  const def = S.cfg.traits[t];
  const level = traitLevel(t, n);
  const ol = el('ol', 'tiers');
  def.levels.forEach((need, i) => {
    const fx = def.fx[i];
    const li = el('li', i === level ? 'now' : '');
    li.append(el('b', '', String(need)),
      el('span', '', describeFx(fx) + (fx.who === 'team' ? ' (every unit on the board)' : ` (${def.name} units)`)));
    ol.append(li);
  });
  return ol;
}

function traitLevel(t, n) {
  let level = -1;
  S.cfg.traits[t].levels.forEach((need, i) => { if (n >= need) level = i; });
  return level;
}

// Extra trait counts a player's augments give (Hearts and Souls).
const augBonus = (p, t) => (p?.augments || []).reduce((n, a) => n + (S.cfg.augments[a]?.trait === t ? S.cfg.augments[a].bonus || 0 : 0), 0);

function traitCard(t) {
  const def = S.cfg.traits[t];
  const head = el('h3', 'with-art');
  head.append(icon('trait:' + t, 32), document.createTextNode(def.name));
  const w = player(S.watch);
  const n = w?.traits?.[t] || 0;
  const level = traitLevel(t, n);
  const parts = [head, el('p', 'kind', `${def.kind === 'origin' ? 'Origin' : 'Class'}: counts the different ${def.name} units on the board (copies count once)`),
    el('p', 'effect', def.text), traitTiers(t, n)];
  if (w) {
    const who = w.id === room.you ? 'You have' : `${w.name} has`;
    const bonus = augBonus(w, t);
    const next = def.levels.find(need => need > n);
    parts.push(el('p', 'sub', n ? `${who} ${n}${bonus ? ` (${bonus} from augments)` : ''}: ${level >= 0 ? `tier ${def.levels[level]} is on` : 'not on yet'}`
      + (next ? `; ${next - n} more for ${next}.` : '.') : `${who} none on the board.`));
  }
  const fielded = new Set((w?.board || []).map(u => u[1]));
  const benched = new Set(S.watch === room.you ? (S.st.me?.bench || []).filter(Boolean).map(u => u[1]) : []);
  const emblems = (w?.board || []).filter(u => !S.cfg.units[u[1]].traits.includes(t) && u[5].some(i => S.cfg.items[i]?.trait === t)).map(u => u[1]);
  const list = el('ul', 'trait-units');
  const keys = Object.keys(S.cfg.units).filter(k => S.cfg.units[k].cost && S.cfg.units[k].traits.includes(t))
    .sort((a, b) => S.cfg.units[a].tier - S.cfg.units[b].tier || S.cfg.units[a].name.localeCompare(S.cfg.units[b].name));
  for (const k of [...keys, ...new Set(emblems)]) {
    const u = S.cfg.units[k];
    const viaEmblem = !u.traits.includes(t);
    const li = el('li', fielded.has(k) ? 'on' : benched.has(k) ? 'bench' : '');
    li.style.setProperty('--cc', COST_COLORS[u.tier]);
    li.title = `${u.name} (${u.cost} gold)${viaEmblem ? ', with an emblem' : ''}${fielded.has(k) ? ': on the board' : benched.has(k) ? ': on the bench' : ''}`;
    li.append(sprite(k, 32), el('span', '', u.name + (viaEmblem ? ' (emblem)' : '')));
    list.append(li);
  }
  parts.push(el('p', 'sub', 'Units (gold: on the board, white: on the bench)'), list);
  return parts;
}

function unitCard(h, d) {
  const key = h.key, star = h.star || 1;
  const st = h.stats || h.live?.stats;
  const title = el('h3', 'with-art');
  title.append(sprite(key, COMPACT.matches ? 48 : 64), document.createTextNode(`${d.name} ${'★'.repeat(star)}`));
  const parts = [title, el('p', 'kind', d.cost ? `Tier ${d.tier} · ${d.cost} gold${star > 1 ? ` · ${3 ** (star - 1)} copies` : ''}` : 'Not for sale')];
  const traits = [...d.traits];
  for (const i of h.items || []) {
    const t = S.cfg.items[i]?.trait;
    if (t && !traits.includes(t)) traits.push(t);
  }
  if (traits.length) parts.push(unitTraits(h, traits, d));
  parts.push(...statBlock(d, star, st, h.live));
  if (d.ability) {
    const ab = el('p', 'ab');
    const nums = abilityNumbers(d.ability, star, st);
    ab.append(el('b', '', `${d.ability.name} (ability): `), document.createTextNode(`${d.ability.text} ${nums}`));
    parts.push(ab);
  }
  if (d.passive_text) parts.push(labelled('Always', d.passive_text, 'ab'));
  const talents = h.talents || h.live?.talents || [];
  for (const tk of talents) {
    const t = S.cfg.talents[tk];
    if (t) parts.push(labelled(`${talentName(tk, key)} (${'★'.repeat(t.star)} extra)`, t.text, 'ab talent'));
  }
  if (d.ability && star < 3 && !talents.length && h.kind !== 'fight' && !talentOffer(h.id)) {
    parts.push(el('p', 'note', 'At 2★ and 3★ it gets an extra ability of your choice.'));
  }
  if (h.items?.length) {
    const list = el('ul', 'held');
    h.items.forEach((it, k) => {
      const i = S.cfg.items[it];
      const li = el('li');
      li.dataset.k = k;
      li.style.setProperty('--rc', rarityColor(it));
      const what = el('span', 'what');
      what.append(el('b', '', i.name), el('small', '', i.text + (i.stats ? ` ${i.stats}.` : '')));
      li.append(icon('item:' + it, 24), what);
      list.append(li);
    });
    parts.push(list);
  }
  return parts;
}

// The unit's traits: whether each is on for it, and what it gives (or would, fielded).
function unitTraits(h, traits, d) {
  const onBoard = h.kind === 'board' || h.kind === 'fight';
  const counts = h.kind === 'fight' ? S.pb?.res?.traits?.[h.live.side] : h.kind === 'board' ? player(S.watch)?.traits : me()?.traits;
  const already = (me()?.board || []).some(u => u[1] === h.key);
  const ul = el('ul', 'unit-traits');
  for (const t of traits) {
    const def = S.cfg.traits[t];
    const n = onBoard ? counts?.[t] || 0 : (counts?.[t] || 0) + (already ? 0 : 1);
    const level = traitLevel(t, n);
    const li = el('li', level >= 0 ? 'on' : '');
    const name = el('b');
    name.append(icon('trait:' + t, 16), document.createTextNode(`${def.name}${d.traits.includes(t) ? '' : ' (emblem)'} ${n}/${def.levels[Math.max(0, level + (def.levels[level + 1] ? 1 : 0))]}`));
    const words = fx => describeFx(fx) + (fx.who === 'team' ? ' (whole board)' : '');
    const need = def.levels[0];
    const say = level >= 0 ? words(def.fx[level]) : `${n} of ${need}, not on yet (at ${need}: ${words(def.fx[0])})`;
    li.append(name, el('span', '', onBoard ? say : `Fielded, it makes ${level >= 0 ? `${n}: ` : ''}${say}`));
    li.title = def.text;
    ul.append(li);
  }
  return ul;
}

// Its numbers: what it fights with, as tiles, each with the difference from the unit bare (traits, items,
// extra abilities, augments, the commander). Hover a tile for what it means.
function statBlock(d, star, st, live) {
  const m = [1, 1.8, 3.24][star - 1];
  const base = { hp: Math.round(d.hp * m), ad: Math.round(d.ad * m), as: d.as, range: d.range, armor: d.armor, mr: d.mr,
    mana: d.start, maxmana: d.mana, ap: 100, crit: 0.25, critdmg: 1.4, dodge: 0, dr: 0, spell_dr: 0, power: 0, regen: 0 };
  const s = st || base;
  const box = el('div', 'stats');
  const tile = (label, value, delta, tip) => {
    const t = el('div', 'tile');
    t.append(el('span', 'l', label), el('b', '', value));
    if (delta) t.append(el('small', delta.startsWith('−') ? 'down' : 'up', delta));
    t.title = tip;
    box.append(t);
  };
  const diff = (a, b, unit = '') => (Math.round(a - b) ? `${a > b ? '+' : '−'}${Math.abs(Math.round(a - b))}${unit}` : '');
  tile('HP', live ? `${Math.round(live.hp)}/${Math.round(live.max)}` : String(s.hp), live ? '' : diff(s.hp, base.hp), 'Health.');
  tile('Attack', String(s.ad), diff(s.ad, base.ad), 'Physical damage each attack (armor reduces it).');
  tile('Attack speed', `${s.as.toFixed(2)}/s`, diff(s.as / base.as * 100, 100, '%'), 'Attacks a second.');
  tile('Range', s.range > 1 ? `${s.range} hexes` : 'Melee', '', 'How far away it can attack.');
  tile('Armor', String(s.armor), diff(s.armor, base.armor), `Takes ${cut(s.armor)}% less physical damage.`);
  tile('Resist', String(s.mr), diff(s.mr, base.mr), `Magic resist: takes ${cut(s.mr)}% less magic damage.`);
  const manaDelta = s.maxmana !== base.maxmana ? `${s.maxmana < base.maxmana ? '−' : '+'}${Math.abs(base.maxmana - s.maxmana)} to cast`
    : diff(s.mana, base.mana, ' at start');
  tile('Mana', live ? `${Math.round(live.mana)}/${live.maxmana}` : `${s.mana}/${s.maxmana}`, live ? '' : manaDelta,
    'Starting mana / mana to cast its ability. It gains 10 mana an attack and some when hurt.');
  tile('Ability power', String(s.ap), diff(s.ap, 100), `Its ability's damage, healing and shields ×${(s.ap / 100).toFixed(2)} (100 is as written).`);
  tile('Crit', `${Math.round(s.crit * 100)}%`, s.crit !== 0.25 || s.critdmg !== 1.4 ? `×${s.critdmg.toFixed(2)} damage` : '',
    `${Math.round(s.crit * 100)}% of attacks crit, for ×${s.critdmg.toFixed(2)} damage.`);
  const more = [`Armor: ${cut(s.armor)}% less physical damage`, `resist: ${cut(s.mr)}% less magic`];
  if (s.dodge) more.push(`dodges ${Math.round(Math.min(1, s.dodge) * 100)}% of attacks`);
  if (s.dr) more.push(`takes ${Math.round(s.dr * 100)}% less damage`);
  if (s.spell_dr) more.push(`${Math.round(Math.min(0.8, s.spell_dr) * 100)}% less from abilities`);
  if (s.regen) more.push(`regrows ${+(s.regen * 100).toFixed(1)}% HP a second`);
  if (s.power) more.push(`ability ${Math.round(s.power * 100)}% stronger`);
  return [box, el('p', 'more', more.join(' · ') + '.')];
}
const cut = armor => Math.round(100 - 10000 / (100 + Math.max(0, armor)));

// The numbers in an ability's steps at a star, with its ability power (and an Empowered pick) applied.
function abilityNumbers(ab, star, st) {
  const bits = [];
  const pct = x => `${Math.round(x * 100)}%`;
  const power = 1 + (st?.power || 0), spell = (st ? st.ap / 100 : 1) * power;
  const STAT = { ad: 'attack', ap: 'ability power', armor: 'armor', mr: 'resist', hp: 'HP' };
  for (const s of ab.steps) {
    const v = x => (Array.isArray(x) ? x[star - 1] : x);
    const sp = x => Math.round(v(x) * spell);
    if (s.dmg && s.do === 'zone') bits.push(`${sp(s.dmg)} damage a second for ${v(s.secs)} s`);
    else if (s.dmg) bits.push(`${sp(s.dmg)} ${s.type === 'phys' ? 'physical' : s.type === 'true' ? 'true' : 'magic'} damage`);
    if (s.heal && s.do === 'zone') bits.push(`${sp(s.heal)} healing a second`);
    if (s.amt && ['heal', 'shield'].includes(s.do)) bits.push(`${sp(s.amt)} ${s.do === 'heal' ? 'healing' : 'shield'}`);
    if (s.do === 'buff' || s.do === 'grow') {
      const amt = v(s.amt) * power;
      const what = ['aspd_pct', 'dodge', 'regen', 'burns', 'thorns'].includes(s.stat)
        ? `+${pct(amt)} ${{ aspd_pct: 'attack speed', dodge: 'dodge', regen: 'HP a second', burns: 'burn a second', thorns: 'of hits back' }[s.stat]}`
        : `+${Math.round(amt)} ${STAT[s.stat] || s.stat}`;
      bits.push(s.do === 'grow' ? `${what} for good` : what);
    }
    if (s.do === 'mana') bits.push(`${v(s.amt)} mana to allies`);
    if (s.do === 'summon' || s.do === 'raise') bits.push(`${v(s.count || 1)} × ${S.cfg.units[s.unit].name}`);
    if (s.do === 'taunt') bits.push(`taunts for ${v(s.secs)} s`);
    if (s.do === 'vanish') bits.push(`out of reach for ${v(s.secs)} s`);
    if (s.do === 'devour') bits.push(`swallowed for ${v(s.secs)} s`);
    if (s.stun) bits.push(`${v(s.stun)} s stun`);
    if (s.heal_frac) bits.push(`heals ${pct(v(s.heal_frac))} of it`);
    if (s.amp) bits.push(`+${pct(v(s.amp))} damage taken for ${s.amp_secs || 4} s`);
    if (s.wound) bits.push(`heals half for ${s.wound} s`);
    if (s.mana_burn) bits.push(`drains ${v(s.mana_burn)} mana`);
    if (s.knock) bits.push(`knocks ${s.knock} hex${s.knock > 1 ? 'es' : ''} back`);
    if (s.execute) bits.push(`finishes below ${pct(v(s.execute))} HP`);
    if (s.delay) bits.push(`lands after ${s.delay} s`);
  }
  return bits.length ? `(${bits.join(', ')}${Math.abs(spell - 1) > 0.005 ? `; ×${spell.toFixed(2)} from ability power` : ''})` : '';
}

// A trait's (or augment's) effects in words.
const fxPct = x => `${+(x * 100).toFixed(1)}%`;
const FX_WORDS = {
  hp_pct: v => `+${fxPct(v)} max HP`, ad_pct: v => `+${fxPct(v)} attack`, aspd_pct: v => `+${fxPct(v)} attack speed`,
  armor: v => `+${v} armor`, mr: v => `+${v} magic resist`, ap: v => `+${v} ability power`, ad: v => `+${v} attack`,
  hp: v => `+${v} HP`, mana: v => `+${v} starting mana`, dodge: v => `dodge ${fxPct(v)} of attacks`,
  crit: v => `+${fxPct(v)} crit chance`, critdmg: v => `crits ${fxPct(v)} harder`, mana_cut: v => `abilities need ${fxPct(v)} less mana`,
  burn: v => `attacks burn ${fxPct(v)} of max HP a second for 3 s`, regen: v => `regrow ${fxPct(v)} of max HP a second`,
  mana_regen: v => `+${v} mana a second`, revive: v => `rise once with ${fxPct(v)} HP`,
  chill: v => `attackers attack ${fxPct(v)} slower for 2 s`, shield: v => `a ${v} shield for the first 10 s`,
  duel: v => `+${fxPct(v)} attack speed each attack (up to 8 times)`, double: v => `${fxPct(v)} chance to strike twice`,
  leap: () => 'leap to the back line at the start', summon_boost: v => `summons get +${fxPct(v)} HP and attack`,
  spell_dr: v => `take ${fxPct(v)} less from abilities`,
};
function describeFx(fx) {
  return Object.entries(fx).filter(([k]) => FX_WORDS[k]).map(([k, v]) => FX_WORDS[k](v)).join(', ');
}

// ------------------------------------------------------------------ the damage chart
// Each unit's damage dealt (by type), damage taken, or healing and shielding given, in the watched
// player's fight: live as it plays, and the last round's fight while planning. From the fight's events
// (sim.py: d carries the source and type, h and s the healer).

const DMG_TYPES = [ // validated as a set against the panel's dark surface (dataviz: orange, blue, green, gold)
  { name: 'Physical', color: '#bf6f2c' }, { name: 'Magic', color: '#4a86e0' },
  { name: 'True', color: '#33a07e' }, { name: 'Burn', color: '#b08a20' },
];

function tally(res, upto) {
  const rows = new Map();
  const add = ([id, side, key, star]) => rows.set(id, { id, side, key, star, dealt: [0, 0, 0, 0], taken: 0, healed: 0 });
  for (const r of res.start) add(r);
  for (const e of res.events) {
    if (e[1] > upto) break;
    if (e[0] === 'sp') add(e[2]);
    else if (e[0] === 'd') {
      const src = rows.get(e[2]), dst = rows.get(e[3]);
      if (src && src.side !== dst?.side) src.dealt[e[5]] += e[4];
      if (dst) dst.taken += e[4];
    } else if (e[0] === 'h' && e[4] != null) {
      const src = rows.get(e[4]);
      if (src) src.healed += e[3];
    } else if (e[0] === 's' && e[5] != null) {
      const src = rows.get(e[5]);
      if (src) src.healed += e[3];
    }
  }
  return [...rows.values()];
}

function renderMeter() {
  const box = $('meter');
  const live = S.st.phase === 'fight';
  const f = live ? fightOf(S.watch) : S.lastFights.find(x => x.home === S.watch || (x.away === S.watch && !x.ghost));
  if (box.hidden !== !f) { box.hidden = !f; renderSheets(); }
  if (!f) return;
  const upto = live ? Math.min(S.ft, f.res.time) : f.res.time;
  const key = [f.home, f.away, f.res.time, f.res.events.length, S.watch, S.meterTab, live, Math.round(upto * 4)].join('|');
  if (key === S.meterKey) return; // nothing new to show
  S.meterKey = key;
  const mySide = f.home === S.watch ? 0 : 1;
  const name = side => (side === 0 ? player(f.home)?.name : f.pve ? 'Monsters' : player(f.away)?.name) || '?';
  $('meter-title').textContent = live ? 'Damage' : 'Damage, last fight';
  const tab = S.meterTab;
  const value = r => (tab === 'dealt' ? r.dealt.reduce((a, b) => a + b, 0) : r[tab]);
  const rows = tally(f.res, upto);
  const top = Math.max(1, ...rows.map(value));
  const legend = $('meter-legend');
  if (tab === 'dealt') {
    legend.replaceChildren(...DMG_TYPES.map(d => {
      const sw = el('span');
      const i = el('i');
      i.style.background = d.color;
      sw.append(i, document.createTextNode(d.name));
      return sw;
    }));
  } else legend.replaceChildren(document.createTextNode(tab === 'taken' ? 'Before shields soak it.' : 'Heals and shields given.'));
  const groups = [mySide, 1 - mySide].map(side => {
    const g = el('div', 'meter-side');
    g.append(el('h3', '', name(side)));
    const list = rows.filter(r => r.side === side).sort((a, b) => value(b) - value(a) || a.id - b.id);
    for (const r of list) {
      const v = value(r);
      const row = el('div', 'meter-row');
      const d = S.cfg.units[r.key];
      const label = el('div', 'meter-top');
      label.append(el('span', '', d.name + (r.star > 1 ? ' ' + '★'.repeat(r.star) : '')), el('b', '', String(Math.round(v))));
      const bar = el('div', 'meter-bar');
      const parts = tab === 'dealt' ? r.dealt.map((x, i) => [x, DMG_TYPES[i].color]) : [[v, tab === 'taken' ? '#c85a5a' : '#4aa86a']];
      for (const [x, color] of parts) {
        if (x <= 0) continue;
        const seg = el('i');
        seg.style.width = `${(100 * x) / top}%`;
        seg.style.background = color;
        bar.append(seg);
      }
      const text = el('div', 'meter-text');
      text.append(label, bar);
      row.append(sprite(r.key, 32), text);
      row.title = tab === 'dealt'
        ? `${d.name}: ` + DMG_TYPES.map((t, i) => `${t.name} ${Math.round(r.dealt[i])}`).join(' · ')
        : `${d.name}: ${Math.round(v)} ${tab === 'taken' ? 'damage taken' : 'healing and shields'}`;
      g.append(row);
    }
    return g;
  });
  $('meter-rows').replaceChildren(...groups);
}

for (const b of document.querySelectorAll('#meter .tabs button')) {
  b.addEventListener('click', () => {
    S.meterTab = b.dataset.tab;
    S.meterKey = null;
    for (const x of document.querySelectorAll('#meter .tabs button')) x.setAttribute('aria-pressed', String(x === b));
    renderMeter();
    play('click');
  });
}

// ------------------------------------------------------------------ fights

const fightOf = id => S.fights.find(f => f.home === id || (f.away === id && !f.ghost));

function makePlayback() {
  S.pb = null;
  const f = fightOf(S.watch);
  if (!f) return;
  S.pb = new Playback(f, S.fightT0, S.cfg, play);
  S.pb.advance(S.ft, true);
  S.pb.flip = f.away === S.watch && !f.pve; // the watched player's board goes at the bottom
}

// ------------------------------------------------------------------ the canvas

const canvas = $('board');
const ctx = canvas.getContext('2d');
const G = { R: 30, w: 52, ox: 0, oy: 0, bench: [] };

function layout() {
  const dpr = window.devicePixelRatio || 1;
  const cw = canvas.clientWidth, ch = canvas.clientHeight;
  if (canvas.width !== Math.round(cw * dpr) || canvas.height !== Math.round(ch * dpr)) {
    canvas.width = Math.round(cw * dpr);
    canvas.height = Math.round(ch * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const rules = S.cfg.rules;
  const benchH = 2.3; // in R
  G.R = Math.max(10, Math.min(cw / ((rules.cols + 0.5) * Math.sqrt(3) + 0.6), ch / (1.5 * (rules.rows - 1) + 2 + benchH + 0.4)));
  G.w = Math.sqrt(3) * G.R;
  const boardW = (rules.cols + 0.5) * G.w, boardH = 1.5 * G.R * (rules.rows - 1) + 2 * G.R;
  G.ox = (cw - boardW) / 2;
  G.oy = Math.max(4, (ch - boardH - benchH * G.R) / 2);
  const slot = Math.min(G.w * 1.05, (cw - 20) / rules.bench);
  const by = G.oy + boardH + G.R * 1.25;
  G.bench = Array.from({ length: rules.bench }, (_, i) => ({ x: cw / 2 + (i - (rules.bench - 1) / 2) * slot, y: by, s: slot }));
}

// pixel centre of battlefield hex (c, r): row 0 at the bottom
function hexXY(c, r) {
  const rows = S.cfg.rules.rows;
  return [G.ox + G.w * (c + 0.5 * (r & 1)) + G.w / 2, G.oy + 1.5 * G.R * (rows - 1 - r) + G.R];
}

// hexes apart, as sim.py's dist (odd-r offset coordinates)
function hexDist([ac, ar], [bc, br]) {
  const aq = ac - (ar - (ar & 1)) / 2, bq = bc - (br - (br & 1)) / 2;
  const dq = aq - bq, dr = ar - br;
  return Math.max(Math.abs(dq), Math.abs(dr), Math.abs(dq + dr));
}

function hexPath(x, y, R) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = Math.PI / 6 + (i * Math.PI) / 3;
    const px = x + R * Math.cos(a), py = y + R * Math.sin(a);
    if (i) ctx.lineTo(px, py); else ctx.moveTo(px, py);
  }
  ctx.closePath();
}

function hexAt(x, y) {
  const { cols, rows } = S.cfg.rules;
  let best = null, bd = G.R * 0.92;
  for (let c = 0; c < cols; c++) {
    for (let r = 0; r < rows; r++) {
      const [hx, hy] = hexXY(c, r);
      const d = Math.hypot(hx - x, hy - y);
      if (d < bd) { bd = d; best = [c, r]; }
    }
  }
  return best;
}

const benchAt = (x, y) => G.bench.findIndex(b => Math.abs(b.x - x) < b.s / 2 && Math.abs(b.y - y) < b.s / 2);

function short(name) {
  const words = name.split(' ');
  return words.length > 1 ? words.map(w => w[0]).join('').slice(0, 3) : name.slice(0, 3);
}

// The sprite atlas (tools/overlords-art/build.py): a row per unit, a 32x32 column per pose.
const atlas = new Image();
atlas.src = ATLAS_URL;
const iconSheet = new Image();
iconSheet.src = ICONS_URL;
const pics = new Image();
pics.src = PORTRAITS_URL;
const drawIcon = (name, x, y, size) => {
  const i = ICONS[name];
  if (i == null || !iconSheet.complete || !iconSheet.naturalWidth) return false;
  ctx.drawImage(iconSheet, (i % ICON_COLS) * 16, Math.floor(i / ICON_COLS) * 16, 16, 16, x, y, size, size);
  return true;
};
// What a ranged unit's attacks look like in flight: by unit, else by origin (proj:<kind> icons).
const PROJ = {
  grave_archer: 'bone', iron_crossbow: 'bolt', iron_engineer: 'bolt', turret: 'shell', ember_mage: 'fire',
  storm_herald: 'feather', tempest_roc: 'feather', thornling: 'arrow', tide_scout: 'arrow', star_archer: 'arrow',
};
const PROJ_ORIGIN = {
  emberforged: 'fire', thornwood: 'leaf', tidecallers: 'water', gravebound: 'shadow', skyborne: 'feather',
  ironhold: 'bolt', starlit: 'star', mirefolk: 'spit',
};
const projOf = key => PROJ[key] || PROJ_ORIGIN[(S.cfg.units[key]?.traits || []).find(t => PROJ_ORIGIN[t])] || 'arrow';
// the battlefield's ground: a pattern per half, cut from the portraits sheet once it has loaded
const ground = {};
function groundPattern(which) {
  if (ground[which]) return ground[which];
  if (!pics.complete || !pics.naturalWidth) return null;
  const c = document.createElement('canvas');
  c.width = c.height = 32;
  c.getContext('2d').drawImage(pics, (which === 'home' ? GROUND_HOME : GROUND_AWAY) * 32, 0, 32, 32, 0, 0, 32, 32);
  ground[which] = ctx.createPattern(c, 'repeat');
  return ground[which];
}
const ORIGIN_COLORS = {
  emberforged: '#ff8a3a', thornwood: '#a0d060', tidecallers: '#7fe3e0', gravebound: '#b48aff',
  skyborne: '#fff6a0', ironhold: '#ffb84a', starlit: '#e8e0ff', mirefolk: '#c8e070',
};
const unitColor = key => ORIGIN_COLORS[(S.cfg.units[key].traits || []).find(t => ORIGIN_COLORS[t])] || '#ffe9a0';

// A unit at (x, y), the middle of its hex: a ground ring in its owner's colour (filled by tier), the
// sprite standing on it in a pose, facing right unless `flip`, then stars, bars and items above and
// below. opts: ring, alpha, pose, flip, bob, flash, stunned, burning, monster, friend, bars, items.
function drawUnit(x, y, key, star, opts = {}) {
  const d = S.cfg.units[key];
  const R = G.R;
  const big = d.tier >= 4 || ['lava_giant', 'iron_colossus', 'moss_brute', 'mire_mother', 'tempest_roc', 'elder_oak',
    'stone_golem', 'bandit_chief'].includes(key);
  const size = R * (big ? 2.45 : 2.1);
  const feet = y + R * 0.5;
  ctx.save();
  ctx.globalAlpha = opts.alpha ?? 1;
  // the ground ring
  ctx.beginPath();
  ctx.ellipse(x, feet - R * 0.04, R * 0.6, R * 0.24, 0, 0, Math.PI * 2);
  ctx.fillStyle = d.tier ? COST_COLORS[d.tier] + '88' : (opts.monster ? MONSTER_COLOR + '88' : '#5c7a4a88');
  ctx.fill();
  ctx.lineWidth = Math.max(2, R * 0.08);
  ctx.strokeStyle = opts.ring || '#11151e';
  ctx.stroke();
  // the sprite
  const row = ROWS[key];
  const top = feet - size * 30.5 / 32 - (opts.bob || 0);
  if (atlas.complete && atlas.naturalWidth && row != null) {
    const col = Math.max(0, POSES.indexOf(opts.pose || 'idle'));
    ctx.imageSmoothingEnabled = false;
    if (opts.flip) {
      ctx.save();
      ctx.translate(x, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(atlas, col * 32, row * 32, 32, 32, -size / 2, top, size, size);
      ctx.restore();
    } else {
      ctx.drawImage(atlas, col * 32, row * 32, 32, 32, x - size / 2, top, size, size);
    }
    if (opts.flash) {
      ctx.globalAlpha = (opts.alpha ?? 1) * 0.35;
      ctx.fillStyle = '#fff';
      ctx.beginPath();
      ctx.ellipse(x, feet - size * 0.45, size * 0.3, size * 0.45, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = opts.alpha ?? 1;
    }
  } else { // the atlas hasn't loaded: a token with the unit's initials
    ctx.beginPath();
    ctx.arc(x, y, R * 0.6, 0, Math.PI * 2);
    ctx.fillStyle = d.tier ? COST_COLORS[d.tier] : '#5c7a4a';
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.font = `700 ${Math.round(R * 0.4)}px "Source Sans 3", sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(short(d.name), x, y);
  }
  const head = feet - size * 0.95;
  if (opts.burning) {
    for (let i = 0; i < 3; i++) {
      const fx = x + Math.sin(now() * 9 + i * 2.1) * R * 0.25, fy = feet - size * (0.25 + 0.2 * i) - ((now() * 30 + i * 7) % 6);
      ctx.fillStyle = i % 2 ? '#ffd23f' : '#ff7a1a';
      ctx.fillRect(fx - 2, fy - 2, 4, 4);
    }
  }
  if (star > 1) {
    ctx.fillStyle = star === 3 ? '#7ff0ff' : '#ffd75a';
    ctx.font = `${Math.round(R * 0.36)}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('★'.repeat(star), x, head - (opts.bars ? R * 0.42 : R * 0.1));
  }
  if (opts.bars) {
    const bw = R * 1.15, bx = x - bw / 2, byy = head - R * 0.18;
    const { hp, max, mana, maxmana, shield } = opts.bars;
    ctx.fillStyle = '#11151e';
    ctx.fillRect(bx - 1, byy - 1, bw + 2, 9);
    ctx.fillStyle = opts.friend ? '#5fd170' : '#e8584f';
    ctx.fillRect(bx, byy, (bw * Math.max(0, hp)) / Math.max(1, max + shield), 4);
    if (shield > 0) {
      ctx.fillStyle = '#eef3ff';
      ctx.fillRect(bx + (bw * Math.max(0, hp)) / (max + shield), byy, (bw * shield) / (max + shield), 4);
    }
    if (maxmana) {
      ctx.fillStyle = '#4aa3ff';
      ctx.fillRect(bx, byy + 5, (bw * Math.min(mana, maxmana)) / maxmana, 2.5);
    }
  }
  if (opts.items?.length) {
    const sz = Math.max(10, Math.round(R * 0.36)), gap = 2;
    const total = opts.items.length * sz + (opts.items.length - 1) * gap;
    opts.items.forEach((it, i) => {
      const ix = x - total / 2 + i * (sz + gap), iy = feet + R * 0.12;
      ctx.fillStyle = rarityColor(it); // a frame in the item's rarity
      ctx.fillRect(ix - 2, iy - 2, sz + 4, sz + 4);
      ctx.fillStyle = '#11151e';
      ctx.fillRect(ix - 1, iy - 1, sz + 2, sz + 2);
      if (!drawIcon('item:' + it, ix, iy, sz)) {
        ctx.fillStyle = rarityColor(it);
        ctx.fillRect(ix, iy, sz, sz);
      }
    });
  }
  if (opts.pick) { // an extra ability waiting to be chosen: a pulsing gold plus by its head
    const px = x + R * 0.62, py = head + R * 0.55, pr = R * (0.24 + 0.03 * Math.sin(now() * 6));
    ctx.fillStyle = '#f2c230';
    ctx.strokeStyle = '#11151e';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(px, py, pr, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = '#11151e';
    ctx.fillRect(px - pr * 0.55, py - pr * 0.16, pr * 1.1, pr * 0.32);
    ctx.fillRect(px - pr * 0.16, py - pr * 0.55, pr * 0.32, pr * 1.1);
  }
  if (opts.marked) { // a reticle: it takes more damage
    ctx.strokeStyle = '#e080ff';
    ctx.lineWidth = 2;
    const ry = feet - size * 0.42, rr = R * 0.42;
    ctx.beginPath();
    ctx.arc(x, ry, rr, 0, Math.PI * 2);
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      ctx.moveTo(x + dx * rr * 0.6, ry + dy * rr * 0.6);
      ctx.lineTo(x + dx * rr * 1.3, ry + dy * rr * 1.3);
    }
    ctx.stroke();
  }
  if (opts.taunting) { // a red ring at its feet: enemies must attack it
    ctx.strokeStyle = '#ff6a4a';
    ctx.lineWidth = Math.max(2, R * 0.08);
    ctx.beginPath();
    ctx.ellipse(x, feet - R * 0.04, R * 0.78, R * 0.32, 0, 0, Math.PI * 2);
    ctx.stroke();
  }
  if (opts.parrying) { // a glint of steel
    ctx.strokeStyle = '#eef3ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x + R * 0.35, feet - size * 0.45, R * 0.35, -1.2, 1.2);
    ctx.stroke();
  }
  if (opts.wounded) { // a cracked green cross: it heals half as much
    const wx = x - R * 0.55, wy = head + R * 0.35, a = R * 0.12;
    ctx.fillStyle = '#5aa84a';
    ctx.fillRect(wx - a, wy - a * 3, a * 2, a * 6);
    ctx.fillRect(wx - a * 3, wy - a, a * 6, a * 2);
    ctx.strokeStyle = '#ff5a4a';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(wx - a * 3, wy + a * 3);
    ctx.lineTo(wx + a * 3, wy - a * 3);
    ctx.stroke();
  }
  if (opts.stunned) { // stars circling the head
    for (let i = 0; i < 3; i++) {
      const a = now() * 5 + (i * Math.PI * 2) / 3;
      ctx.fillStyle = '#ffe14a';
      ctx.font = `${Math.round(R * 0.3)}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.fillText('✦', x + Math.cos(a) * R * 0.4, head + R * 0.15 + Math.sin(a) * R * 0.12);
    }
  }
  ctx.restore();
}

// a gentle idle bob, out of step from unit to unit
const bob = id => Math.round(Math.sin(now() * 2.6 + id * 1.7)) * (G.R / 22);

function draw() {
  requestAnimationFrame(draw);
  const t = now();
  if (S.lastFrame && S.st?.phase === 'fight') S.ft += (t - S.lastFrame) * S.speed;
  S.lastFrame = t;
  tickHud();
  const st = S.st;
  if (!st || !S.cfg || st.phase === 'lobby' || $('game').hidden) return;
  if (t - S.meterAt > 0.25) { S.meterAt = t; renderMeter(); }
  layout();
  const cw = canvas.clientWidth, ch = canvas.clientHeight;
  ctx.clearRect(0, 0, cw, ch);
  const { cols, rows } = S.cfg.rules;
  const mine = seatedMe();
  const planning = st.phase !== 'fight';
  const dragging = S.drag && S.drag.unit;
  for (let c = 0; c < cols; c++) {
    for (let r = 0; r < rows; r++) {
      const [x, y] = hexXY(c, r);
      hexPath(x, y, G.R * 0.96);
      const own = r < rows / 2;
      const pat = groundPattern(own ? 'home' : 'away');
      if (pat) {
        pat.setTransform(new DOMMatrix().scaleSelf(G.R / 20, G.R / 20));
        ctx.fillStyle = pat;
      } else ctx.fillStyle = own ? '#2c3650' : '#262b3c';
      ctx.fill();
      if ((dragging || (S.sel && touchy())) && planning && own && S.watch === room.you) {
        ctx.fillStyle = 'rgba(120, 150, 220, 0.18)';
        ctx.fill();
      }
      if ((S.over?.kind === 'board' && S.over.c === c && S.over.r === r && dragging)
        || (S.sel && S.sel.from.c === c && S.sel.from.r === r && planning && S.watch === room.you)) {
        ctx.strokeStyle = '#f2c230';
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
  }
  // the line between the halves
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.beginPath();
  const midY = (hexXY(0, rows / 2)[1] + hexXY(0, rows / 2 - 1)[1]) / 2;
  ctx.moveTo(G.ox, midY);
  ctx.lineTo(cw - G.ox, midY);
  ctx.stroke();

  if (st.phase === 'fight' && S.pb) drawFight();
  else drawBoard(player(S.watch));

  // the bench (always yours)
  if (mine && st.me) {
    st.me.bench.forEach((u, i) => {
      const b = G.bench[i];
      ctx.fillStyle = '#1f2433';
      ctx.strokeStyle = (S.over?.kind === 'bench' && S.over.i === i && dragging) || S.sel?.from.b === i ? '#f2c230' : '#3a4258';
      ctx.lineWidth = 2;
      roundRect(b.x - b.s / 2 + 3, b.y - b.s / 2 + 3, b.s - 6, b.s - 6, 8);
      ctx.fill();
      ctx.stroke();
      if (u && !(S.drag && S.drag.from.b === i && (S.drag.moved || !touchy()))) drawUnit(b.x, b.y, u[1], u[2], { ring: mine.color, items: u[3], pick: !!talentOffer(u[0]) });
    });
  }
  if (S.drag?.unit && S.mouse && (S.drag.moved || !touchy())) drawUnit(S.mouse.x, S.mouse.y, S.drag.unit[1], S.drag.unit[2], { ring: mine?.color, alpha: 0.85 });
  if (S.drag?.item != null && S.mouse && S.drag.moved) {
    ctx.imageSmoothingEnabled = false;
    if (!drawIcon('item:' + S.drag.key, S.mouse.x - 16, S.mouse.y - 16, 32)) {
      ctx.fillStyle = rarityColor(S.drag.key);
      ctx.fillRect(S.mouse.x - 12, S.mouse.y - 12, 24, 24);
    }
  }
}

function roundRect(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function drawBoard(p) {
  if (!p) return;
  for (const [id, key, star, c, r, items] of p.board) {
    if (S.drag?.unit && S.drag.from.c === c && S.drag.from.r === r && p.id === room.you && (S.drag.moved || !touchy())) continue;
    const [x, y] = hexXY(c, r);
    drawUnit(x, y, key, star, { ring: p.color, items, bob: bob(id), pick: p.id === room.you && !!talentOffer(id) });
  }
}

function drawFight() {
  const pb = S.pb;
  const t = Math.min(S.ft, pb.res.time + 5);
  pb.advance(t);
  const f = pb.fight;
  const flip = pb.flip;
  const { cols, rows } = S.cfg.rules;
  const view = ([c, r]) => (flip ? [cols - 1 - c, rows - 1 - r] : [c, r]);
  const colorOf = side => {
    if (side === 0) return player(f.home)?.color;
    return f.pve ? MONSTER_COLOR : player(f.away)?.color;
  };
  const friendSide = flip ? 1 : 0;
  const where = new Map();
  for (const u of pb.units.values()) {
    const p = pb.pos(u, t);
    const [ax, ay] = hexXY(...view(p.from));
    const [bx, by] = hexXY(...view(p.to));
    let x = ax + (bx - ax) * p.k, y = ay + (by - ay) * p.k;
    // melee lunge
    const since = t - u.attackAt;
    if (u.range <= 1 && since < 0.18 && u.target && pb.units.get(u.target)) {
      const v = pb.units.get(u.target);
      const [tx, ty] = hexXY(...view([v.c, v.r]));
      const k = Math.sin((since / 0.18) * Math.PI) * 0.25;
      x += (tx - x) * k;
      y += (ty - y) * k;
    }
    where.set(u.id, [x, y]);
  }
  // areas on the ground: lingering zones in the caster's colour, and a pulsing ring where a blow will land
  for (const z of pb.zones) {
    const { cols: C, rows: Rw } = S.cfg.rules;
    for (let c = 0; c < C; c++) {
      for (let r = 0; r < Rw; r++) {
        if (hexDist([c, r], [z.c, z.r]) > z.rad) continue;
        const [x, y] = hexXY(...view([c, r]));
        hexPath(x, y, G.R * 0.9);
        ctx.save();
        if (z.kind === 'warn') {
          const k = Math.min(1, (t - z.at) / Math.max(0.1, z.until - z.at));
          ctx.globalAlpha = 0.25 + 0.5 * k;
          ctx.strokeStyle = '#ff7a4a';
          ctx.lineWidth = 2 + 2 * k;
          ctx.setLineDash([5, 4]);
          ctx.stroke();
          ctx.globalAlpha = 0.12 + 0.2 * k;
          ctx.fillStyle = '#ff5a2a';
          ctx.fill();
        } else {
          const left = z.until - t;
          ctx.globalAlpha = 0.28 * Math.min(1, left / 0.4) * (0.85 + 0.15 * Math.sin(t * 6 + c + r));
          ctx.fillStyle = z.key ? unitColor(z.key) : '#a0d060';
          ctx.fill();
        }
        ctx.restore();
      }
    }
  }
  // the living draw back to front, the fallen beneath them
  const order = [...pb.units.values()].sort((a, b) => (a.alive - b.alive) || (where.get(a.id)[1] - where.get(b.id)[1]));
  for (const u of order) {
    let fade = u.alive ? 1 : Math.max(0, 1 - (t - u.deadAt - 0.6) / 0.5);
    if (fade <= 0) continue;
    const hidden = u.alive && t < u.hiddenUntil;
    if (hidden) fade = u.devoured ? 0.12 : 0.3 + 0.1 * Math.sin(t * 12);
    const [x, y] = where.get(u.id);
    const tgt = pb.units.get(u.target);
    if (tgt && tgt.alive && where.get(tgt.id)) u.flip = where.get(tgt.id)[0] < x - 2;
    const pose = !u.alive ? 'fallen' : t - u.castAt < 0.35 ? 'cast' : t - u.attackAt < 0.18 ? 'attack'
      : t - u.hitAt < 0.12 ? 'hurt' : 'idle';
    drawUnit(x, y, u.key, u.star, {
      ring: colorOf(u.side), alpha: fade, flash: t - u.hitAt < 0.07, stunned: u.alive && t < u.stunUntil,
      monster: f.pve && u.side === 1, friend: u.side === friendSide, items: u.items, pose, flip: u.flip,
      burning: u.alive && t < u.burnUntil, bob: pose === 'idle' && u.alive ? bob(u.id) : 0,
      taunting: u.alive && t < u.tauntUntil, marked: u.alive && t < u.markUntil, wounded: u.alive && t < u.woundUntil,
      parrying: u.alive && t < u.parryUntil,
      bars: u.alive ? { hp: u.hp, max: u.max, mana: u.mana, maxmana: u.maxmana, shield: u.shield } : null,
    });
  }
  for (const fx of pb.fx) {
    const k = (t - fx.at) / fx.life;
    if (k < 0 || k > 1) continue;
    ctx.save();
    if (fx.kind === 'shot') {
      const a = where.get(fx.from), b = where.get(fx.to);
      if (a && b) {
        const lift = G.R * 0.55;
        const x = a[0] + (b[0] - a[0]) * k, y = a[1] - lift + (b[1] - a[1]) * k;
        const sz = Math.max(12, G.R * 0.75);
        ctx.translate(x, y);
        ctx.rotate(Math.atan2(b[1] - a[1], b[0] - a[0]));
        ctx.imageSmoothingEnabled = false;
        if (!drawIcon('proj:' + projOf(fx.key), -sz / 2, -sz / 2, sz)) {
          ctx.fillStyle = fx.side === friendSide ? '#d6f5ff' : '#ffd6c9';
          ctx.beginPath();
          ctx.arc(0, 0, Math.max(2.5, G.R * 0.1), 0, Math.PI * 2);
          ctx.fill();
        }
      }
    } else if (fx.kind === 'text') {
      const p = where.get(fx.id);
      if (p) {
        ctx.globalAlpha = 1 - k;
        ctx.fillStyle = fx.color;
        ctx.font = `700 ${Math.round(G.R * (fx.big ? 0.62 : 0.45))}px "Source Sans 3", sans-serif`;
        ctx.textAlign = 'center';
        ctx.strokeStyle = 'rgba(0,0,0,0.6)';
        ctx.lineWidth = 3;
        const y = p[1] - G.R * 0.9 - k * G.R * 0.8;
        ctx.strokeText(fx.text, p[0] + G.R * 0.35, y);
        ctx.fillText(fx.text, p[0] + G.R * 0.35, y);
      }
    } else if (fx.kind === 'cast' || fx.kind === 'ring') {
      const p = where.get(fx.id);
      if (p) {
        ctx.globalAlpha = 1 - k;
        ctx.strokeStyle = fx.kind === 'cast' ? '#ffe9a0' : fx.color;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(p[0], p[1], G.R * (0.6 + k * (fx.kind === 'cast' ? 1.4 : 0.6)), 0, Math.PI * 2);
        ctx.stroke();
        if (fx.kind === 'cast' && fx.name) {
          ctx.fillStyle = '#ffe9a0';
          ctx.font = `600 ${Math.round(G.R * 0.4)}px "Source Sans 3", sans-serif`;
          ctx.textAlign = 'center';
          ctx.fillText(fx.name, p[0], p[1] + G.R * 1.05);
        }
      }
    } else if (fx.kind === 'bolt') {
      const a = where.get(fx.from), b = where.get(fx.to);
      if (a && b) {
        const lift = G.R * 0.5;
        const x = a[0] + (b[0] - a[0]) * Math.min(1, k * 1.6), y = a[1] - lift + (b[1] - a[1]) * Math.min(1, k * 1.6);
        ctx.globalAlpha = 1 - k * 0.6;
        ctx.strokeStyle = unitColor(fx.key);
        ctx.lineWidth = Math.max(2, G.R * 0.12);
        ctx.beginPath();
        ctx.moveTo(a[0] + (x - a[0]) * 0.6, a[1] - lift + (y - a[1] + lift) * 0.6);
        ctx.lineTo(x, y);
        ctx.stroke();
        const sz = Math.max(12, G.R * 0.8);
        ctx.globalAlpha = 1;
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(Math.atan2(b[1] - a[1], b[0] - a[0]));
        ctx.imageSmoothingEnabled = false;
        if (!drawIcon('proj:' + PROJ_ORIGIN[(S.cfg.units[fx.key]?.traits || []).find(t => PROJ_ORIGIN[t])], -sz / 2, -sz / 2, sz)) {
          ctx.fillStyle = '#fff';
          ctx.beginPath();
          ctx.arc(0, 0, Math.max(2, G.R * 0.1), 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      }
    } else if (fx.kind === 'zap') { // an item's lightning: a jagged line
      const a = where.get(fx.from), b = where.get(fx.to);
      if (a && b) {
        ctx.globalAlpha = 1 - k;
        ctx.strokeStyle = '#fff6a0';
        ctx.lineWidth = 2;
        ctx.beginPath();
        const ax = a[0], ay = a[1] - G.R * 0.6, bx = b[0], by = b[1] - G.R * 0.5;
        ctx.moveTo(ax, ay);
        for (let i = 1; i < 6; i++) {
          const f = i / 6;
          ctx.lineTo(ax + (bx - ax) * f + (Math.sin(i * 7 + fx.at * 13) * G.R * 0.25), ay + (by - ay) * f);
        }
        ctx.lineTo(bx, by);
        ctx.stroke();
      }
    } else if (fx.kind === 'area') {
      const p = where.get(fx.id);
      if (p) {
        ctx.globalAlpha = (1 - k) * 0.55;
        ctx.fillStyle = unitColor(fx.key);
        ctx.beginPath();
        ctx.ellipse(p[0], p[1] + G.R * 0.2, G.w * (fx.r + 0.5) * (0.4 + 0.6 * k), G.w * (fx.r + 0.5) * 0.55 * (0.4 + 0.6 * k), 0, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (fx.kind === 'line') {
      const a = where.get(fx.from), b = where.get(fx.to);
      if (a && b) {
        const len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
        const reach = G.w * fx.n;
        ctx.globalAlpha = 1 - k;
        ctx.strokeStyle = unitColor(fx.key);
        ctx.lineWidth = G.R * 0.5 * (1 - k * 0.5);
        ctx.beginPath();
        ctx.moveTo(a[0], a[1]);
        ctx.lineTo(a[0] + ((b[0] - a[0]) / len) * reach, a[1] + ((b[1] - a[1]) / len) * reach);
        ctx.stroke();
      }
    } else if (fx.kind === 'heal') {
      const p = where.get(fx.id);
      if (p) {
        ctx.globalAlpha = 1 - k;
        ctx.fillStyle = '#7be08a';
        for (let i = 0; i < 4; i++) {
          const a = i * 1.7 + fx.at;
          ctx.fillRect(p[0] + Math.cos(a) * G.R * 0.4 - 1.5, p[1] - G.R * (0.2 + k * 0.8) + Math.sin(a) * 4, 3, 3);
        }
      }
    } else if (fx.kind === 'jump') {
      const [ax, ay] = hexXY(...view(fx.from));
      const [bx, by] = hexXY(...view(fx.to));
      ctx.globalAlpha = 1 - k;
      ctx.strokeStyle = '#d8c8ff';
      ctx.lineWidth = 3;
      ctx.setLineDash([6, 5]);
      ctx.beginPath();
      ctx.moveTo(ax, ay);
      ctx.lineTo(bx, by);
      ctx.stroke();
    }
    ctx.restore();
  }
  S.where = where;
  // a fight unit tapped (touch) stays in the info card, its numbers live
  if (S.pinned && S.hover?.kind === 'fight') {
    const u = pb.units.get(S.hover.uid);
    if (u && Math.round(now() * 4) !== S.lastInfo) {
      S.lastInfo = Math.round(now() * 4);
      S.hover = { ...S.hover, live: u, star: u.star, items: u.items };
      info();
    }
  } else if (S.mouse && !S.drag && !S.pinned) { // hover info for fight units follows them
    let best = null, bd = G.R * 0.7;
    for (const u of pb.units.values()) {
      if (!u.alive || (u.devoured && pb.t < u.hiddenUntil)) continue;
      const [x, y] = where.get(u.id);
      const d = Math.hypot(x - S.mouse.x, y - S.mouse.y);
      if (d < bd) { bd = d; best = u; }
    }
    const was = S.hover;
    if (best) {
      S.hover = { kind: 'fight', key: best.key, star: best.star, live: best, items: best.items };
      if (!was || was.live !== best || Math.round(now() * 4) !== S.lastInfo) { S.lastInfo = Math.round(now() * 4); info(); }
    } else if (was?.kind === 'fight') { S.hover = null; info(); }
  }
}

// ------------------------------------------------------------------ dragging and hovering

function canvasXY(e) {
  const r = canvas.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
}

function myUnitAt(x, y) {
  const st = S.st, mine = seatedMe();
  if (!mine || !mine.alive || !st.me) return null;
  const i = benchAt(x, y);
  if (i >= 0 && st.me.bench[i]) return { from: { b: i }, unit: st.me.bench[i] };
  if (st.phase !== 'plan' || S.watch !== room.you) return null;
  const h = hexAt(x, y);
  if (!h) return null;
  const u = mine.board.find(b => b[3] === h[0] && b[4] === h[1]);
  return u ? { from: { c: h[0], r: h[1] }, unit: u } : null;
}

// What's at a canvas point, for the info card: a unit on your bench, on the watched board, or in the fight.
function unitAt(x, y) {
  const st = S.st;
  const i = benchAt(x, y);
  if (i >= 0) {
    const u = st.me?.bench[i];
    return u ? { kind: 'bench', i, key: u[1], star: u[2], items: u[3], talents: u[4], id: u[0], stats: u[5] } : null;
  }
  if (st.phase === 'fight') {
    if (!S.pb || !S.where) return null;
    let best = null, bd = G.R * 0.8;
    for (const u of S.pb.units.values()) {
      const pos = S.where.get(u.id);
      if (!pos || !u.alive || (u.devoured && S.pb.t < u.hiddenUntil)) continue;
      const d = Math.hypot(pos[0] - x, pos[1] - y);
      if (d < bd) { bd = d; best = u; }
    }
    return best ? { kind: 'fight', uid: best.id, key: best.key, star: best.star, live: best, items: best.items } : null;
  }
  const h = hexAt(x, y);
  const u = h && player(S.watch)?.board.find(b => b[3] === h[0] && b[4] === h[1]);
  return u ? { kind: 'board', c: h[0], r: h[1], key: u[1], star: u[2], items: u[5], talents: u[6], id: u[0], stats: u[7] } : null;
}

// Moves one of your units (from {b} or {c, r}) to the bench slot or own hex at (x, y). False if that's
// neither (a refused move, say over the limit, still counts as handled).
function moveTo(from, x, y) {
  const i = benchAt(x, y);
  if (i >= 0) {
    if (from.b !== i) room.send({ t: 'move', from, to: { b: i } });
    return true;
  }
  const h = hexAt(x, y);
  if (h && h[1] < S.cfg.rules.rows / 2 && S.st.phase !== 'fight' && S.watch === room.you) {
    const mine = seatedMe();
    const toEmpty = !mine.board.some(b => b[3] === h[0] && b[4] === h[1]);
    if (from.b != null && toEmpty && mine.board.length >= mine.limit) { play('deny'); return true; }
    if (from.c !== h[0] || from.r !== h[1]) room.send({ t: 'move', from, to: { c: h[0], r: h[1] } });
    return true;
  }
  return false;
}

canvas.addEventListener('pointerdown', e => {
  if (!S.st || !S.cfg) return;
  if (COMPACT.matches) openSheet('');
  const p = canvasXY(e);
  const got = myUnitAt(p.x, p.y);
  const touch = e.pointerType !== 'mouse';
  if (got && S.pickedItem != null) { // an item was picked from the strip: put it on this unit
    room.send({ t: 'equip', i: S.pickedItem, to: got.from });
    S.pickedItem = null;
    play('buy');
    renderItems();
    if (touch) pin(null);
    return;
  }
  if (touch && S.sel && !got && moveTo(S.sel.from, p.x, p.y)) { pin(null); return; } // a tapped unit's destination
  if (got) {
    S.drag = { ...got, moved: false };
    S.dragStart = { x: e.clientX, y: e.clientY };
    S.mouse = p;
    canvas.setPointerCapture(e.pointerId);
    if (!touch) play('click');
    return;
  }
  if (touch) { // a tap on anything else: read about the unit there, or close the card
    const u = unitAt(p.x, p.y);
    pin(u, true);
    if (u) play('click');
  } else if (S.pinned) pin(null); // a click away from a clicked unit lets go of it
});

addEventListener('pointermove', e => {
  if (!S.st || !S.cfg || $('game').hidden) return;
  const p = canvasXY(e);
  const inside = p.x >= 0 && p.y >= 0 && p.x <= canvas.clientWidth && p.y <= canvas.clientHeight;
  const mouse = e.pointerType === 'mouse';
  S.mouse = (inside && mouse) || S.drag ? p : null;
  if (S.drag && S.dragStart && Math.hypot(e.clientX - S.dragStart.x, e.clientY - S.dragStart.y) > 8) S.drag.moved = true;
  const overShop = S.drag?.unit && S.drag.moved && document.elementFromPoint(e.clientX, e.clientY)?.closest('#shopbar');
  $('shop').classList.toggle('sell', !!overShop);
  if (S.drag?.unit) {
    const [, key, star] = S.drag.unit;
    $('shop').dataset.sell = `Sell for ${S.cfg.units[key].cost * 3 ** (star - 1)} gold`;
  }
  if (!inside) {
    S.over = null;
    if (mouse && !S.pinned && S.hover && ['board', 'bench'].includes(S.hover.kind)) pin(null);
    return;
  }
  const i = benchAt(p.x, p.y);
  const h = hexAt(p.x, p.y);
  S.over = i >= 0 ? { kind: 'bench', i } : h ? { kind: 'board', c: h[0], r: h[1] } : null;
  if (mouse && !S.pinned) {
    const prev = S.hover;
    if (i >= 0) {
      const u = S.st.me?.bench[i];
      S.hover = { kind: 'bench', i, key: u?.[1], star: u?.[2], items: u?.[3], talents: u?.[4], id: u?.[0], stats: u?.[5] };
    } else if (h && S.st.phase !== 'fight') {
      const w = player(S.watch);
      const u = w?.board.find(b => b[3] === h[0] && b[4] === h[1]);
      S.hover = { kind: 'board', c: h[0], r: h[1], key: u?.[1], star: u?.[2], items: u?.[5], talents: u?.[6], id: u?.[0], stats: u?.[7] };
    } else if (S.st.phase !== 'fight') {
      S.hover = null;
    }
    if (prev?.key !== S.hover?.key || prev?.star !== S.hover?.star) info();
  }
  if (mouse) {
    canvas.style.cursor = S.drag ? 'grabbing' : myUnitAt(p.x, p.y) ? 'grab' : 'default';
  }
});

addEventListener('pointerup', e => {
  if (!S.drag) return;
  const drag = S.drag;
  S.drag = null;
  S.over = null;
  if (drag.item != null) { // an item from the strip: dropped on a unit, or a click that picks it
    if (!drag.moved) {
      S.pickedItem = S.pickedItem === drag.item ? null : drag.item;
      renderItems();
      if (e.pointerType !== 'mouse') pin(S.pickedItem != null ? { kind: 'item', item: drag.key, bench: true } : null, true);
      return;
    }
    const p = canvasXY(e);
    const got = myUnitAt(p.x, p.y) || (() => { // during a fight only the bench takes items
      const i = benchAt(p.x, p.y);
      return i >= 0 && S.st.me?.bench[i] ? { from: { b: i } } : null;
    })();
    if (got) { room.send({ t: 'equip', i: drag.item, to: got.from }); play('buy'); } else play('deny');
    return;
  }
  $('shop').classList.remove('sell');
  if (!drag.moved) { // a tap or click on your unit: its card stays, with Sell and Take off (touch: tap where it goes)
    const f = drag.from, s0 = S.sel?.from;
    if (s0 && s0.b === f.b && s0.c === f.c && s0.r === f.r) { pin(null); return; }
    const u = drag.unit;
    const hover = f.b != null ? { kind: 'bench', i: f.b, key: u[1], star: u[2], items: u[3], talents: u[4], id: u[0], stats: u[5] }
      : { kind: 'board', c: f.c, r: f.r, key: u[1], star: u[2], items: u[5], talents: u[6], id: u[0], stats: u[7] };
    pin(hover, true, { from: f, key: u[1] });
    play('click');
    return;
  }
  if (drag.moved && document.elementFromPoint(e.clientX, e.clientY)?.closest('#shopbar')) {
    room.send({ t: 'sell', from: drag.from });
    play('sell');
    if (S.sel) pin(null);
    return;
  }
  const p = canvasXY(e);
  if (moveTo(drag.from, p.x, p.y) && S.sel) pin(null);
});

addEventListener('pointercancel', () => { S.drag = null; S.over = null; $('shop').classList.remove('sell'); });

// ------------------------------------------------------------------ buttons and keys

const act = (t, sound) => { room.send({ t }); if (sound) play(sound); };
$('xp').addEventListener('click', () => act('xp'));
$('reroll').addEventListener('click', () => act('reroll', 'reroll'));
$('lock').addEventListener('click', () => act('lock', 'click'));
$('ready').addEventListener('click', () => act('ready', 'click'));
$('mute').addEventListener('click', () => { setMuted(!isMuted()); renderHud(); });
try { S.speed = localStorage.getItem('overlords-speed') === '2' ? 2 : 1; } catch { /* private mode */ }
$('speed').addEventListener('click', () => {
  S.speed = S.speed === 1 ? 2 : 1;
  try { localStorage.setItem('overlords-speed', String(S.speed)); } catch { /* private mode */ }
  renderHud();
});
$('again').addEventListener('click', () => room.send({ t: 'again' }));

// Exit: someone still in the match is asked first (they're knocked out for good); anyone else just leaves.
const leaveRoom = () => { location.href = '/games/overlords'; };
$('exit').addEventListener('click', () => {
  const mine = seatedMe();
  if (!mine || !mine.alive || !['plan', 'fight', 'draft'].includes(S.st?.phase)) { leaveRoom(); return; }
  const standing = S.st.players.filter(p => p.seated && p.alive).length;
  $('exit-text').textContent = `You'll be knocked out now and finish ${ordinal(standing)} of ${S.st.players.filter(p => p.seated).length}`
    + `, and your units go back to the pool. You can't come back into this match.`;
  $('exit-confirm').hidden = false;
  play('click');
});
$('exit-no').addEventListener('click', () => { $('exit-confirm').hidden = true; play('click'); });
$('exit-yes').addEventListener('click', () => {
  room.send({ t: 'forfeit' });
  $('exit-yes').disabled = true;
  S.exiting = true;
  setTimeout(leaveRoom, 1500); // in case the answer never comes
});
$('start').addEventListener('click', () => room.send({ t: 'start' }));
$('bots').addEventListener('change', () => room.send({ t: 'set', bots: $('bots').checked }));
$('bot-level').addEventListener('change', () => room.send({ t: 'set', level: $('bot-level').value }));
$('power').addEventListener('click', () => { room.send({ t: 'power' }); play('cast'); });
$('choose-reroll').addEventListener('click', () => { room.send({ t: 'aug_reroll' }); play('reroll'); });
$('choose-hide').addEventListener('click', () => { S.chooseHidden = S.chooseKey; renderChoose(); play('click'); });
$('choose-show').addEventListener('click', () => { S.chooseHidden = null; renderChoose(); play('click'); });
for (const b of document.querySelectorAll('#sheet-tabs button')) {
  b.addEventListener('click', () => { openSheet(document.body.dataset.sheet === b.dataset.sheet ? '' : b.dataset.sheet); play('click'); });
}
for (const b of document.querySelectorAll('.sheet .sheet-close')) b.addEventListener('click', () => { openSheet(''); play('click'); });

addEventListener('keydown', e => {
  if ($('game').hidden || e.target.closest?.('input, select, textarea') || e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === 'escape' && S.pinned) { pin(null); return; }
  if (k === 'd' && !$('reroll').disabled) act('reroll', 'reroll');
  else if (k === 'f' && !$('xp').disabled) act('xp');
  else if (k === ' ' && !$('ready').disabled) { e.preventDefault(); act('ready', 'click'); }
  else if (k === 'e' && S.mouse) {
    const got = myUnitAt(S.mouse.x, S.mouse.y);
    if (got) { room.send({ t: 'sell', from: got.from }); play('sell'); }
  }
});

addEventListener('resize', () => { if (S.st) render(); });
COMPACT.addEventListener('change', () => { openSheet(''); if (S.st) { render(); info(); } });
if (window.OV) Object.assign(window.OV, { G, hexXY, receive });
requestAnimationFrame(draw);
