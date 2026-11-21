// Overlords in the browser: the lobby, the board (drawn on a canvas), the shop, the players and
// traits panels. The server (app/overlords/game.py) runs the match and simulates every fight; this
// draws the boards, plays back whichever fight is being watched (fight.js), and asks to buy,
// reroll, buy XP, move and sell.

import { person, startRoom } from '../../shared/lobby.js?v=1';
import { Playback } from './fight.js?v=9';
import { isMuted, play, setMuted } from './sound.js?v=9';
import { ATLAS_URL, GROUND_AWAY, GROUND_HOME, ICON_COLS, ICONS, ICONS_URL, PORTRAITS, PORTRAITS_URL, POSES, ROWS } from './atlas.js?v=9';

const $ = id => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};
const show = screen => { for (const id of ['menu', 'lobby', 'game']) $(id).hidden = id !== screen; };
const now = () => performance.now() / 1000;
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
              augments: m.augments, augTiers: m.aug_tiers };
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
  renderCommander();
  renderChoose();
  renderDraft();
  renderEnd();
}

// ------------------------------------------------------------------ items, commander, augments, draft

const ITEM_COLORS = { component: '#5b6478', item: '#8a6a2a', emblem: '#2f7a6a', crown: '#b08a1a', artifact: '#8a2a4a' };

function renderItems() {
  const box = $('items'), st = S.st;
  const items = st.me?.items || [];
  if (S.pickedItem != null && S.pickedItem >= items.length) S.pickedItem = null;
  if (!items.length) { box.replaceChildren(el('span', 'none', 'None yet: monster rounds drop components.')); return; }
  box.replaceChildren(...items.map((key, i) => {
    const d = S.cfg.items[key];
    const b = el('button', 'item ' + d.kind);
    b.type = 'button';
    b.append(icon('item:' + key, 32));
    b.setAttribute('aria-label', d.name);
    b.classList.toggle('picked', S.pickedItem === i);
    b.title = `${d.name}: ${d.text} Drag it onto a unit, or click it and then the unit.`
      + (d.kind === 'component' ? ' Two components on one unit combine.' : '');
    b.addEventListener('pointerdown', e => {
      S.drag = { item: i, key, from: {}, moved: false };
      S.dragStart = { x: e.clientX, y: e.clientY };
      b.releasePointerCapture?.(e.pointerId);
    });
    b.addEventListener('pointerenter', () => { S.hover = { kind: 'item', item: key }; info(); });
    b.addEventListener('pointerleave', () => { if (S.hover?.kind === 'item') { S.hover = null; info(); } });
    return b;
  }));
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
    return li;
  }));
}

function renderChoose() {
  const st = S.st, mine = seatedMe();
  const me_ = st.me;
  let mode = null;
  if (mine && mine.alive && me_ && !mine.commander && me_.offers?.length && st.phase !== 'over') mode = 'commander';
  else if (mine && mine.alive && me_?.aug_offer?.length && st.phase !== 'over') mode = 'augment';
  const key = mode ? mode + (mode === 'commander' ? me_.offers.join() : me_.aug_offer.join()) + me_.aug_rerolled : '';
  $('choose').hidden = !mode || S.chooseHidden === key;
  $('choose-show').hidden = !mode || S.chooseHidden !== key;
  $('choose-show').textContent = mode === 'commander' ? 'Choose your commander' : 'Choose your augment';
  $('choose-note').textContent = `If you haven't chosen when the fight starts, the first is taken for you.`;
  if (key === S.chooseKey) return;
  S.chooseKey = key;
  if (!mode) return;
  const opts = $('choose-options');
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
  const holds = d.options.some(o => S.cfg.items[o[1]]?.kind === 'artifact') ? 'an artifact' : 'a component';
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
    b.addEventListener('pointerenter', () => { S.hover = { kind: 'shop', key }; info(); });
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
    $('hud-level').textContent = `Level ${mine.level}${need ? ` · ${st.me.xp}/${need} XP` : ''} · ${mine.board.length}/${mine.limit} on board`;
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
  $('reroll').innerHTML = free ? `Reroll <small>free ×${free} · D</small>` : `Reroll <small>${rc}g · D</small>`;
  $('lock').disabled = !can;
  $('lock').setAttribute('aria-pressed', String(!!st.me?.locked));
  $('ready').disabled = !can || st.phase !== 'plan';
  $('ready').textContent = mine?.ready ? 'Ready ✓' : 'Ready';
  $('ready').title = mine?.ready ? 'Click again if you are not ready after all.' : 'End planning early once everyone is ready (Space).';
  $('lock').textContent = st.me?.locked ? 'Shop locked' : 'Lock shop';
  $('lock').title = 'A locked shop keeps the same units into the next round.';
  renderOdds();
  $('mute').textContent = isMuted() ? '🔇' : '🔊';
  $('speed').textContent = `Fights ${S.speed}×`;
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
  const phase = st.phase === 'plan' ? `Planning · ${left}s` : st.phase === 'fight' ? 'Fighting'
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
    if (st.pve) parts.push('Monsters this round');
    const mine2 = seatedMe();
    const waiting = (st.me?.bench || []).filter(Boolean).length;
    if (mine2?.alive && S.watch === room.you && waiting >= S.cfg.rules.bench) {
      parts.push('<span class="hint">Your bench is full: drag a unit onto the shop to sell it</span>');
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
    const name = el('span', 'name', p.name + (p.id === room.you ? ' (you)' : '') + (p.bot ? ' 🤖' : ''));
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
    li.addEventListener('click', () => { S.watch = p.id; makePlayback(); render(); play('click'); });
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
    b.addEventListener('pointerenter', () => { S.hover = { kind: 'shop', key }; info(); });
    b.addEventListener('pointerleave', () => { if (S.hover?.kind === 'shop') { S.hover = null; info(); } });
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
    def.levels.forEach((need, i) => steps.append(el('i', i <= level ? 'on' : '', String(need))));
    li.append(steps);
    li.title = def.text;
    li.addEventListener('pointerenter', () => { S.hover = { kind: 'trait', trait: t }; info(); });
    li.addEventListener('pointerleave', () => { if (S.hover?.kind === 'trait') { S.hover = null; info(); } });
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

// The info panel: what's under the pointer.
function info() {
  const box = $('info');
  const h = S.hover;
  if (!h) { box.replaceChildren(); return; }
  if (h.kind === 'item') {
    const d = S.cfg.items[h.item];
    const head = el('h3', 'with-art');
    head.append(icon('item:' + h.item, 32), document.createTextNode(d.name));
    const parts = [head, el('p', '', d.text)];
    if (d.from) parts.push(el('p', '', `From ${d.from.map(c => S.cfg.items[c].name).join(' + ')}.`));
    if (d.kind === 'artifact') parts.push(el('p', '', 'An artifact: no recipe makes it. Monster round 11, the last draft, '
      + 'the Ancient Armory and Relic Hunter augments and the Forgemaster find them.'));
    if (d.kind === 'component') {
      const makes = Object.entries(S.cfg.items).filter(([, x]) => x.from && x.from.includes(h.item))
        .map(([, x]) => `${x.name} (+ ${S.cfg.items[x.from[0] === h.item ? x.from[1] : x.from[0]].name})`);
      parts.push(el('p', '', 'Makes: ' + makes.join(', ')));
    }
    box.replaceChildren(...parts);
    return;
  }
  if (h.kind === 'trait') {
    const def = S.cfg.traits[h.trait];
    const head = el('h3', 'with-art');
    head.append(icon('trait:' + h.trait, 32), document.createTextNode(def.name));
    const w = player(S.watch);
    const fielded = new Set((w?.board || []).map(u => u[1]));
    const benched = new Set(S.watch === room.you ? (S.st.me?.bench || []).filter(Boolean).map(u => u[1]) : []);
    const list = el('ul', 'trait-units');
    const keys = Object.keys(S.cfg.units).filter(k => S.cfg.units[k].cost && S.cfg.units[k].traits.includes(h.trait))
      .sort((a, b) => S.cfg.units[a].tier - S.cfg.units[b].tier || S.cfg.units[a].name.localeCompare(S.cfg.units[b].name));
    for (const k of keys) {
      const u = S.cfg.units[k];
      const li = el('li', fielded.has(k) ? 'on' : benched.has(k) ? 'bench' : '');
      li.style.setProperty('--cc', COST_COLORS[u.tier]);
      li.title = `${u.name} (${u.cost} gold)${fielded.has(k) ? ': on the board' : benched.has(k) ? ': on the bench' : ''}`;
      li.append(sprite(k, 32), el('span', '', u.name));
      list.append(li);
    }
    box.replaceChildren(head, el('p', '', def.text),
      el('p', '', def.levels.map((n, i) => `${n}: ${describeFx(def.fx[i])}`).join(' · ')), list);
    return;
  }
  const key = h.key, d = S.cfg.units[key];
  if (!d) { box.replaceChildren(); return; }
  const star = h.star || 1, m = [1, 1.8, 3.24][star - 1];
  const title = el('h3', 'with-art');
  title.append(sprite(key, 64), document.createTextNode(`${d.name} ${'★'.repeat(star)}`));
  const kind = d.cost ? `Tier ${d.tier} · ${d.cost} gold · ${d.traits.map(t => S.cfg.traits[t].name).join(', ')}` : 'Not for sale';
  const dl = el('dl');
  const live = h.live;
  const stats = [
    ['HP', live ? `${Math.round(live.hp)}/${Math.round(live.max)}` : Math.round(d.hp * m)], ['Attack', Math.round(d.ad * m)],
    ['Speed', d.as], ['Range', d.range], ['Armor', d.armor], ['Resist', d.mr],
    ['Mana', live ? `${Math.round(live.mana)}/${live.maxmana}` : `${d.start}/${d.mana}`],
  ];
  for (const [k, v] of stats) dl.append(el('dt', '', k), el('dd', '', String(v)));
  const parts = [title, el('p', '', kind), dl];
  if (h.items?.length) {
    const its = el('p', 'items');
    for (const i of h.items) {
      const one = el('span');
      one.append(icon('item:' + i, 16), document.createTextNode(S.cfg.items[i].name));
      its.append(one);
    }
    parts.push(its);
  }
  if (d.ability) {
    const ab = el('p', 'ab');
    ab.append(el('b', '', d.ability.name + ': '), document.createTextNode(d.ability.text + ' ' + abilityNumbers(d.ability, star)));
    parts.push(ab);
  }
  if (d.passive_text) {
    const pa = el('p', 'ab');
    pa.append(el('b', '', 'Always: '), document.createTextNode(d.passive_text));
    parts.push(pa);
  }
  box.replaceChildren(...parts);
}

function abilityNumbers(ab, star) {
  const bits = [];
  const pct = x => `${Math.round(x * 100)}%`;
  const STAT = { ad: 'attack', ap: 'ability power', armor: 'armor', mr: 'resist', hp: 'HP' };
  for (const s of ab.steps) {
    const v = x => (Array.isArray(x) ? x[star - 1] : x);
    if (s.dmg && s.do === 'zone') bits.push(`${v(s.dmg)} damage a second for ${v(s.secs)} s`);
    else if (s.dmg) bits.push(`${v(s.dmg)} ${s.type === 'phys' ? 'physical' : s.type === 'true' ? 'true' : 'magic'} damage`);
    if (s.heal && s.do === 'zone') bits.push(`${v(s.heal)} healing a second`);
    if (s.amt && ['heal', 'shield'].includes(s.do)) bits.push(`${v(s.amt)} ${s.do === 'heal' ? 'healing' : 'shield'}`);
    if (s.do === 'buff' || s.do === 'grow') {
      const amt = v(s.amt);
      const what = ['aspd_pct', 'dodge', 'regen', 'burns', 'thorns'].includes(s.stat)
        ? `+${pct(amt)} ${{ aspd_pct: 'attack speed', dodge: 'dodge', regen: 'HP a second', burns: 'burn a second', thorns: 'of hits back' }[s.stat]}`
        : `+${amt} ${STAT[s.stat] || s.stat}`;
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
  return bits.length ? `(${bits.join(', ')})` : '';
}

function describeFx(fx) {
  const names = {
    burn: v => `burn ${v * 100}%/s`, regen: v => `regrow ${v * 100}%/s`, mana_regen: v => `+${v} mana/s`,
    revive: v => `rise with ${v * 100}%`, dodge: v => `${v * 100}% dodge`, armor: v => `+${v} armor`, mr: v => `+${v} resist`,
    mana_cut: v => `-${v * 100}% mana`, chill: v => `-${v * 100}% attack speed`, shield: v => `${v} shield`,
    duel: v => `+${v * 100}% speed a hit`, double: v => `${v * 100}% double strike`, ap: v => `+${v}% ability power`,
    crit: v => `+${v * 100}% crit`, summon_boost: v => `+${v * 100}% summons`, hp_pct: v => `+${v * 100}% HP`,
    spell_dr: v => `${v * 100}% less from abilities`,
  };
  const out = [];
  for (const [k, v] of Object.entries(fx)) if (names[k]) out.push(names[k](v));
  return out.join(', ') + (fx.who === 'team' ? ' (everyone)' : '');
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
  box.hidden = !f;
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
      ctx.fillStyle = '#11151ecc';
      ctx.fillRect(ix - 1, iy - 1, sz + 2, sz + 2);
      if (!drawIcon('item:' + it, ix, iy, sz)) {
        ctx.fillStyle = ITEM_COLORS[S.cfg.items[it]?.kind] || '#666';
        ctx.fillRect(ix, iy, sz, sz);
      }
    });
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
      if (dragging && planning && own && S.watch === room.you) {
        ctx.fillStyle = 'rgba(120, 150, 220, 0.18)';
        ctx.fill();
      }
      if (S.hover?.kind === 'board' && S.hover.c === c && S.hover.r === r && dragging) {
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
      ctx.strokeStyle = S.hover?.kind === 'bench' && S.hover.i === i && dragging ? '#f2c230' : '#3a4258';
      ctx.lineWidth = 2;
      roundRect(b.x - b.s / 2 + 3, b.y - b.s / 2 + 3, b.s - 6, b.s - 6, 8);
      ctx.fill();
      ctx.stroke();
      if (u && !(S.drag && S.drag.from.b === i)) drawUnit(b.x, b.y, u[1], u[2], { ring: mine.color, items: u[3] });
    });
  }
  if (S.drag?.unit && S.mouse) drawUnit(S.mouse.x, S.mouse.y, S.drag.unit[1], S.drag.unit[2], { ring: mine?.color, alpha: 0.85 });
  if (S.drag?.item != null && S.mouse && S.drag.moved) {
    ctx.imageSmoothingEnabled = false;
    if (!drawIcon('item:' + S.drag.key, S.mouse.x - 16, S.mouse.y - 16, 32)) {
      ctx.fillStyle = ITEM_COLORS[S.cfg.items[S.drag.key].kind];
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
    if (S.drag?.unit && S.drag.from.c === c && S.drag.from.r === r && p.id === room.you) continue;
    const [x, y] = hexXY(c, r);
    drawUnit(x, y, key, star, { ring: p.color, items, bob: bob(id) });
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
  // hover info for fight units follows them
  if (S.mouse && !S.drag) {
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

canvas.addEventListener('pointerdown', e => {
  if (!S.st || !S.cfg) return;
  const p = canvasXY(e);
  const got = myUnitAt(p.x, p.y);
  if (got && S.pickedItem != null) { // an item was picked from the strip: put it on this unit
    room.send({ t: 'equip', i: S.pickedItem, to: got.from });
    S.pickedItem = null;
    play('buy');
    renderItems();
    return;
  }
  if (got) {
    S.drag = got;
    S.mouse = p;
    canvas.setPointerCapture(e.pointerId);
    play('click');
  }
});

addEventListener('pointermove', e => {
  if (!S.st || !S.cfg || $('game').hidden) return;
  const p = canvasXY(e);
  const inside = p.x >= 0 && p.y >= 0 && p.x <= canvas.clientWidth && p.y <= canvas.clientHeight;
  S.mouse = inside || S.drag ? p : null;
  if (S.drag?.item != null && S.dragStart && Math.hypot(e.clientX - S.dragStart.x, e.clientY - S.dragStart.y) > 6) S.drag.moved = true;
  const overShop = S.drag?.unit && document.elementFromPoint(e.clientX, e.clientY)?.closest('#shopbar');
  $('shop').classList.toggle('sell', !!overShop);
  if (S.drag?.unit) {
    const [, key, star] = S.drag.unit;
    $('shop').dataset.sell = `Sell for ${S.cfg.units[key].cost * 3 ** (star - 1)} gold`;
  }
  if (!inside) {
    if (S.hover && ['board', 'bench'].includes(S.hover.kind)) { S.hover = null; info(); }
    return;
  }
  const i = benchAt(p.x, p.y);
  const h = hexAt(p.x, p.y);
  const prev = S.hover;
  if (i >= 0) {
    const u = S.st.me?.bench[i];
    S.hover = { kind: 'bench', i, key: u?.[1], star: u?.[2], items: u?.[3] };
  } else if (h && S.st.phase !== 'fight') {
    const w = player(S.watch);
    const u = w?.board.find(b => b[3] === h[0] && b[4] === h[1]);
    S.hover = { kind: 'board', c: h[0], r: h[1], key: u?.[1], star: u?.[2], items: u?.[5] };
  } else if (S.st.phase !== 'fight') {
    S.hover = null;
  }
  if (prev?.key !== S.hover?.key || prev?.star !== S.hover?.star) info();
  canvas.style.cursor = S.drag ? 'grabbing' : myUnitAt(p.x, p.y) ? 'grab' : 'default';
});

addEventListener('pointerup', e => {
  if (!S.drag) return;
  const drag = S.drag;
  S.drag = null;
  if (drag.item != null) { // an item from the strip: dropped on a unit, or a click that picks it
    if (!drag.moved) {
      S.pickedItem = S.pickedItem === drag.item ? null : drag.item;
      renderItems();
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
  if (document.elementFromPoint(e.clientX, e.clientY)?.closest('#shopbar')) {
    room.send({ t: 'sell', from: drag.from });
    play('sell');
    return;
  }
  const p = canvasXY(e);
  const i = benchAt(p.x, p.y);
  if (i >= 0) {
    if (drag.from.b !== i) room.send({ t: 'move', from: drag.from, to: { b: i } });
    return;
  }
  const h = hexAt(p.x, p.y);
  if (h && h[1] < S.cfg.rules.rows / 2 && S.st.phase !== 'fight' && S.watch === room.you) {
    const mine = seatedMe();
    const toEmpty = !mine.board.some(b => b[3] === h[0] && b[4] === h[1]);
    if (drag.from.b != null && toEmpty && mine.board.length >= mine.limit) { play('deny'); return; }
    room.send({ t: 'move', from: drag.from, to: { c: h[0], r: h[1] } });
  }
});

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
$('start').addEventListener('click', () => room.send({ t: 'start' }));
$('bots').addEventListener('change', () => room.send({ t: 'set', bots: $('bots').checked }));
$('bot-level').addEventListener('change', () => room.send({ t: 'set', level: $('bot-level').value }));
$('power').addEventListener('click', () => { room.send({ t: 'power' }); play('cast'); });
$('choose-reroll').addEventListener('click', () => { room.send({ t: 'aug_reroll' }); play('reroll'); });
$('choose-hide').addEventListener('click', () => { S.chooseHidden = S.chooseKey; renderChoose(); play('click'); });
$('choose-show').addEventListener('click', () => { S.chooseHidden = null; renderChoose(); play('click'); });

addEventListener('keydown', e => {
  if ($('game').hidden || e.target.closest?.('input, select, textarea') || e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === 'd' && !$('reroll').disabled) act('reroll', 'reroll');
  else if (k === 'f' && !$('xp').disabled) act('xp');
  else if (k === ' ' && !$('ready').disabled) { e.preventDefault(); act('ready', 'click'); }
  else if (k === 'e' && S.mouse) {
    const got = myUnitAt(S.mouse.x, S.mouse.y);
    if (got) { room.send({ t: 'sell', from: got.from }); play('sell'); }
  }
});

addEventListener('resize', () => { if (S.st) render(); });
if (window.OV) Object.assign(window.OV, { G, hexXY, receive });
requestAnimationFrame(draw);
