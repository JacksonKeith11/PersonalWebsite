// Board Brawl in the browser: the connection, the menu and lobby, the board screen (players,
// what you can do this turn, the log) and the minigame overlays. The server sends the whole
// room state whenever it changes, and this redraws from it.

import { Board, ROUTE_COLORS } from './board.js?v=5';
import { Stage } from './mg.js?v=5';
import { TEAM_COLORS } from './base.js?v=5';
import * as sfx from './audio.js?v=5';

const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
const now = () => performance.now() / 1000;

// ---------------------------------------------------------------- who this browser is

const KEY = 'brawl';
const randomId = () => Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
let saved = {};
try { saved = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { /* private mode */ }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(saved)); } catch { /* private mode */ } };
if (!saved.token) { saved.token = randomId(); save(); }
let tab = '';
try {
  tab = sessionStorage.getItem(`${KEY}-tab`) || randomId();
  sessionStorage.setItem(`${KEY}-tab`, tab);
} catch { tab = randomId(); }

const S = { you: null, code: null, board: null, items: {}, prizes: {}, st: null, waitUntil: null, picking: null, lastCur: null };
let board = null;
const stage = new Stage($('mg-stage'), $('mg'), $('mg-text'));

// ---------------------------------------------------------------- the connection

let ws = null, wanted = false, retry = 1, join = null;

function connect(opts) {
  join = opts;
  wanted = true;
  open();
}

function open() {
  const sock = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/games/board-brawl/ws`);
  ws = sock;
  status('Connecting…');
  sock.onopen = () => {
    retry = 1;
    sock.send(JSON.stringify({
      t: 'hello', name: saved.name || 'Player', token: saved.token, tab,
      room: S.code || join.room || '', create: !S.code && !!join.create,
    }));
  };
  sock.onmessage = e => receive(JSON.parse(e.data));
  sock.onclose = () => {
    if (ws !== sock) return;
    ws = null;
    if (!wanted) return;
    status(`Disconnected. Reconnecting in ${retry}s…`);
    setTimeout(() => { if (wanted && !ws) open(); }, retry * 1000);
    retry = Math.min(retry * 2, 16);
  };
}

function send(m) {
  if (ws && ws.readyState === 1) ws.send(JSON.stringify(m));
}

function status(text) {
  $('status').textContent = text;
}

function receive(m) {
  if (m.t === 'welcome') {
    S.you = m.you;
    S.code = m.code;
    S.items = m.items;
    S.prizes = m.prizes;
    S.crown = m.crown;
    S.max = m.max;
    status('');
    history.replaceState(null, '', `/games/board-brawl?room=${m.code}`);
    if (!board) board = new Board($('board'), m.board, { onPick: i => send({ t: 'path', i }) });
  } else if (m.t === 'state') {
    const prev = S.st;
    S.st = m;
    S.waitUntil = m.wait != null ? now() + m.wait : null;
    sounds(prev, m);
    render();
  } else if (m.t === 'mg') {
    stage.snap(m);
  } else if (m.t === 'error') {
    wanted = false;
    S.code = null;
    history.replaceState(null, '', '/games/board-brawl');
    show('menu');
    status(m.msg);
  }
}

// ---------------------------------------------------------------- sounds for what happened

function sounds(prev, st) {
  const fx = st.fx || [];
  const kinds = new Set(fx.map(f => f.k));
  const map = { dice: 'roll', crown: 'crown', bomb: 'bomb', boo: 'boo', portal: 'portal', web: 'web', trap: 'trap',
    gift: 'gift', ghost: 'ghost', duel: 'duel', item: 'item', mirror: 'item', witching: 'witching' };
  for (const [k, name] of Object.entries(map)) if (kinds.has(k)) sfx.play(name);
  const mine = fx.filter(f => f.k === 'coins' && f.p === S.you);
  if (mine.some(f => f.n > 0)) sfx.play('coin');
  else if (mine.some(f => f.n < 0)) sfx.play('lose');
  if (prev && st.phase === 'board' && st.step === 'move' && prev.left !== st.left) sfx.play('step');
  if (st.phase === 'board' && st.cur === S.you && st.step === 'roll' && !(prev && prev.cur === S.you && prev.step === 'roll')) sfx.play('turn');
  if (st.phase === 'final' && prev && prev.phase !== 'final') sfx.play('win');
}

// ---------------------------------------------------------------- drawing the page from the state

function show(screen) {
  for (const id of ['menu', 'lobby', 'game']) $(id).hidden = id !== screen;
}

const player = id => S.st.players.find(p => p.id === id);
const me = () => player(S.you);
const isHost = () => S.st.host === S.you;

function render() {
  const st = S.st;
  document.body.classList.toggle('host', isHost());
  if (st.phase === 'lobby') {
    show('lobby');
    stage.close();
    for (const id of ['mg-intro', 'results', 'final']) $(id).hidden = true;
    renderLobby();
    return;
  }
  show('game');
  if (st.cur !== S.you || st.step !== 'roll' || st.used) S.picking = null;
  board.update(st, S.you);
  $('round').innerHTML = `Round ${st.round} of ${st.rounds}${st.witching ? ' · <b class="witch">Witching Hour</b>' : ''}`;
  $('game-code').textContent = S.code;
  renderCards();
  renderAction();
  $('log').innerHTML = st.log.slice().reverse().map(l => `<li>${esc(l)}</li>`).join('');
  renderOverlays();
}

function renderLobby() {
  const st = S.st;
  $('room-code').textContent = S.code;
  $('share').value = `${location.origin}/games/board-brawl?room=${S.code}`;
  const seated = st.players.filter(p => p.seated);
  $('count').textContent = `${seated.length} of ${S.max}`;
  $('seats').innerHTML = st.players.map(p => `
    <li><span class="dot" style="background:${p.color}"></span>
      <b>${esc(p.name)}</b>${p.id === S.you ? ' <small>(you)</small>' : ''}${p.id === st.host ? ' <small>host</small>' : ''}
      ${p.bot ? ' <small>bot</small>' : ''}${p.seated ? '' : ' <small>watching</small>'}</li>`).join('');
  $('rounds').value = String(st.rounds);
  $('bonus').checked = st.bonus;
  for (const el of document.querySelectorAll('.host-input')) el.disabled = !isHost();
  $('start').disabled = seated.length < 2;
  $('bot-add').disabled = seated.length >= S.max;
  $('bot-remove').disabled = !st.players.some(p => p.bot);
  $('lobby-note').textContent = !isHost()
    ? `Waiting for ${(player(st.host) || {}).name || 'the host'} to start.`
    : seated.length < 2 ? 'You need at least two players: invite a friend or add a bot.' : '';
}

function standing() {
  return [...S.st.order].map(player).filter(Boolean).sort((a, b) => b.crowns - a.crowns || b.coins - a.coins);
}

function renderCards() {
  const st = S.st;
  const ranked = standing();
  const place = p => 1 + ranked.filter(q => q.crowns > p.crowns || (q.crowns === p.crowns && q.coins > p.coins)).length;
  $('cards').innerHTML = st.order.map(player).filter(Boolean).map(p => `
    <li class="${p.id === st.cur ? 'turn' : ''} ${p.id === S.you ? 'me' : ''}" style="--c:${p.color}">
      <span class="place">${place(p)}</span>
      <span class="who"><b>${esc(p.name)}</b>${p.id === S.you ? ' <small>you</small>' : ''}${p.bot ? ' <small>bot</small>' : ''}${!p.on && !p.bot ? ' <small>away, auto-playing</small>' : ''}
        ${p.curse ? '<small class="bad">cursed</small>' : ''}${p.hex ? '<small class="bad">hexed</small>' : ''}</span>
      <span class="crowns" title="Crowns">👑 ${p.crowns}</span>
      <span class="coins" title="Coins">🪙 ${p.coins}</span>
      <span class="items">${p.items.map(k => `<i title="${esc(S.items[k].name)}: ${esc(S.items[k].desc)}">${S.items[k].icon}</i>`).join('')}</span>
    </li>`).join('');
}

const DIRS = [[0, -1, '⬆ Up'], [1, 0, '➡ Right'], [0, 1, '⬇ Down'], [-1, 0, '⬅ Left']];

function direction(from, to) {
  const a = board.space(from), b = board.space(to);
  const dx = b.x - a.x, dy = b.y - a.y;
  const m = Math.hypot(dx, dy) || 1;
  return DIRS.reduce((best, d) => ((d[0] * dx + d[1] * dy) / m > best.score ? { score: (d[0] * dx + d[1] * dy) / m, label: d[2] } : best), { score: -2, label: '' }).label;
}

const LANDS = {
  event: '❓ Event', item: '🎁 Chest', shop: '🛒 Shop',
  duel: '⚔️ Duel', portal: '🌀 Portal',
};

// what a way at a fork leads to: where you'd land, and what you'd pass on the way
function landing(st, routes) {
  if (!routes.length) return '';
  const ends = [...new Set(routes.map(rt => rt[rt.length - 1]))];
  const what = id => {
    const extra = [];
    if (id === st.crown) extra.push('👑');
    if (id === st.ghost) extra.push('👻');
    const trap = st.traps?.[id];
    if (trap != null && trap !== S.you) extra.push('⚠️ trap');
    if (st.webs?.[id] != null && st.webs[id] !== S.you) extra.push('🕸️ stuck');
    const kind = board.space(id).kind;
    const n = st.witching ? 6 : 3;
    const label = kind === 'blue' ? `🔵 +${n} coins` : kind === 'red' ? `🔴 −${n} coins` : LANDS[kind];
    return `${label}${extra.length ? ' ' + extra.join(' ') : ''}`;
  };
  const passes = new Set(routes.flatMap(rt => rt.slice(0, -1)));
  const via = [];
  if (st.crown != null && passes.has(st.crown)) via.push('👑 crown');
  if ([...passes].some(id => board.space(id).kind === 'shop')) via.push('🛒 shop');
  if (st.ghost != null && passes.has(st.ghost)) via.push('👻 ghost');
  const fork = routes.length > 1 ? ', another fork on the way' : '';
  return `Lands on ${ends.map(what).join(' or ')}${fork}${via.length ? ` · passes ${via.join(', ')}` : ''}`;
}

function renderAction() {
  const st = S.st;
  const el = $('action');
  if (st.phase !== 'board' || st.cur == null) {
    el.innerHTML = `<p class="what">${st.phase === 'final' ? 'Game over!' : 'Minigame time!'}</p>`;
    return;
  }
  const cur = player(st.cur);
  const mine = st.cur === S.you;
  const wait = '<span class="wait" id="wait"></span>';
  let html = '';
  if (!mine) {
    const doing = {
      roll: 'is thinking…', rolling: `rolled ${st.dice.join(' + ')}`, move: `is on the move: ${st.left} to go${st.back ? ', backwards' : ''}`,
      path: 'is picking a path', buy: 'is deciding whether to buy the crown', shop: st.passing ? 'stopped at a shop' : 'is shopping', duel: 'is picking someone to duel', landed: '',
    }[st.step] || '';
    html = `<p class="what"><span class="dot" style="background:${cur.color}"></span><b>${esc(cur.name)}</b> ${doing} ${wait}</p>`;
  } else if (st.step === 'roll') {
    const p = me();
    if (S.picking) {
      const spec = S.items[S.picking];
      html = `<p class="what">${spec.icon} <b>${esc(spec.name)}</b>: who? ${wait}</p><div class="btns">` +
        st.order.filter(id => id !== S.you).map(id => {
          const q = player(id);
          return `<button data-act="target" data-v="${id}" style="--c:${q.color}" class="who-btn">${esc(q.name)} <small>👑${q.crowns} 🪙${q.coins}</small></button>`;
        }).join('') + '<button data-act="cancel">Never mind</button></div>';
    } else {
      const dice = st.dice.length === 2 ? ' (two dice!)' : '';
      const notes = [p.curse ? 'You’re cursed: this roll is 1-3.' : '', p.hex ? 'You’re hexed: you’ll walk backwards.' : ''].filter(Boolean).join(' ');
      html = `<p class="what"><b>Your turn!</b>${dice} ${notes ? `<span class="bad">${notes}</span>` : ''} ${wait}</p>
        <div class="btns"><button class="primary big" data-act="roll">🎲 Roll <small>Space</small></button>` +
        p.items.map(k => {
          const spec = S.items[k];
          const off = st.used || spec.passive;
          return `<button data-act="item" data-v="${k}" ${off ? 'disabled' : ''} title="${esc(spec.desc)}">${spec.icon} ${esc(spec.name)}${spec.passive ? ' <small>(works by itself)</small>' : ''}</button>`;
        }).join('') + '</div>' + (p.items.length && !st.used ? '<p class="tip">You can use one item before you roll. Hover or long-press an item to see what it does.</p>' : '');
    }
  } else if (st.step === 'path') {
    html = `<p class="what"><b>Which way?</b> Tap a glowing space or pick: ${wait}</p><div class="btns">` +
      st.choices.map((s, i) => {
        const sp = board.space(s);
        return `<button data-act="path" data-v="${i}" class="way"><i style="background:${ROUTE_COLORS[i]}"></i>${direction(cur.pos, s)} <small>${sp.middle ? 'through the graveyard' : 'round the loop'}</small>
          <span class="lands">${landing(st, st.routes?.[i] || [])}</span></button>`;
      }).join('') + '</div>';
  } else if (st.step === 'buy') {
    const coins = me().coins;
    html = coins >= S.crown
      ? `<p class="what">👑 <b>You've reached the crown! Buy it for ${S.crown} coins?</b> You have ${coins}. ${wait}</p>
        <div class="btns"><button class="primary big" data-act="buy" data-v="1">Buy it!</button><button data-act="buy" data-v="0">No thanks</button></div>`
      : `<p class="what">👑 <b>You've reached the crown!</b> It costs ${S.crown} coins, but you only have ${coins}. ${wait}</p>
        <div class="btns"><button class="big" disabled>Buy it (${S.crown} 🪙)</button><button class="primary" data-act="buy" data-v="0">Walk on</button></div>`;
  } else if (st.step === 'shop') {
    const p = me();
    const cheap = Object.keys(S.items).some(k => st.prices[k] < S.items[k].price);
    const full = p.items.length >= 3;
    html = `<p class="what">🛒 <b>${st.passing ? 'You’re passing the Witch’s Shop. Buy anything?' : 'The Witch’s Shop'}</b>
      You have ${p.coins} 🪙 and ${p.items.length} of 3 items.${cheap ? ' <span class="good">Half price, since you’re behind!</span>' : ''} ${wait}</p><div class="shop">` +
      Object.entries(S.items).map(([k, spec]) => `
        <button data-act="shop" data-v="${k}" ${p.coins < st.prices[k] || full ? 'disabled' : ''}>
          <span class="icon">${spec.icon}</span><b>${esc(spec.name)}</b><span class="price">${st.prices[k]} 🪙</span>
          <small>${esc(spec.desc)}</small></button>`).join('') +
      `</div><div class="btns"><button class="primary" data-act="shop" data-v="">${st.passing ? 'Keep walking' : 'Done shopping'}</button></div>`;
  } else if (st.step === 'duel') {
    html = `<p class="what">⚔️ <b>Duel!</b> Pick someone: the winner takes up to ${S.prizes.duel} coins from the loser. ${wait}</p><div class="btns">` +
      st.order.filter(id => id !== S.you).map(id => {
        const q = player(id);
        return `<button data-act="duel" data-v="${id}" class="who-btn" style="--c:${q.color}">${esc(q.name)} <small>🪙${q.coins}</small></button>`;
      }).join('') + '</div>';
  } else {
    html = `<p class="what">${st.step === 'move' ? `On the move: ${st.left} to go${st.back ? ', backwards' : ''}` : esc(st.log[st.log.length - 1] || '')}</p>`;
  }
  el.innerHTML = html;
  tickWait();
}

function tickWait() {
  const w = $('wait');
  if (!w) return;
  if (S.waitUntil == null) { w.textContent = ''; return; }
  const left = Math.max(0, Math.ceil(S.waitUntil - now()));
  w.textContent = S.st.cur === S.you ? `(auto in ${left}s)` : `(${left}s)`;
}
setInterval(tickWait, 250);

// pointing at a way at a fork lights up its route on the board
$('action').addEventListener('pointerover', e => {
  const b = e.target.closest('button[data-act="path"]');
  if (board) board.hover = b ? +b.dataset.v : null;
});
$('action').addEventListener('pointerleave', () => { if (board) board.hover = null; });
$('action').addEventListener('click', e => {
  const b = e.target.closest('button[data-act]');
  if (!b || b.disabled) return;
  sfx.unlock();
  sfx.play('click');
  const act = b.dataset.act, v = b.dataset.v;
  if (act === 'roll') send({ t: 'roll' });
  else if (act === 'item') {
    if (S.items[v].target) { S.picking = v; renderAction(); return; }
    send({ t: 'item', item: v });
  } else if (act === 'target') { send({ t: 'item', item: S.picking, target: +v }); S.picking = null; }
  else if (act === 'cancel') { S.picking = null; renderAction(); }
  else if (act === 'path') send({ t: 'path', i: +v });
  else if (act === 'buy') send({ t: 'buy', yes: v === '1' });
  else if (act === 'shop') send({ t: 'shop', item: v || null });
  else if (act === 'duel') send({ t: 'duel', target: +v });
});

// ---------------------------------------------------------------- minigame overlays

const MODE_NAMES = { ffa: 'Free-for-all', team: '2 vs 2', '1vn': 'One vs all', duel: 'Duel' };

function renderOverlays() {
  const st = S.st;
  const players = Object.fromEntries(st.players.map(p => [p.id, { name: p.name, color: p.color }]));
  // intro
  $('mg-intro').hidden = st.phase !== 'mgintro';
  if (st.phase === 'mgintro' && st.mg) {
    const mg = st.mg;
    $('mg-mode').textContent = `Minigame · ${MODE_NAMES[mg.mode] || ''}`;
    $('mg-name').textContent = mg.name;
    const names = ids => ids.map(id => `<b style="color:${(players[id] || {}).color}">${esc((players[id] || {}).name)}</b>`).join(' & ');
    let teams = '';
    if (mg.mode === 'team' || mg.mode === '1vn') {
      teams = `<span class="team" style="--c:${TEAM_COLORS[0]}">${names(mg.teams[0])}</span> vs <span class="team" style="--c:${TEAM_COLORS[1]}">${names(mg.teams[1])}</span>`;
      teams += mg.mode === 'team'
        ? `<br><small>The winning pair get ${S.prizes.team} coins each.</small>`
        : `<br><small>If ${esc(players[mg.teams[0][0]].name)} wins, they get ${S.prizes.solo} coins; if the rest win, ${S.prizes.pack} each.</small>`;
    } else if (mg.mode === 'duel') {
      teams = `${names([mg.ids[0]])} vs ${names([mg.ids[1]])}<br><small>The winner takes up to ${S.prizes.duel} coins from the loser.</small>`;
    } else {
      teams = `<small>${S.prizes.ffa.filter(Boolean).map((n, i) => `${['1st', '2nd', '3rd', '4th'][i]}: ${n}`).join(' · ')} coins</small>`;
    }
    $('mg-teams').innerHTML = teams;
    $('mg-rules').textContent = mg.rules;
    $('mg-controls').textContent = mg.controls;
    $('mg-ready').innerHTML = mg.ids.map(id => {
      const p = player(id);
      return `<li class="${p.ready ? 'ready' : ''}"><span class="dot" style="background:${p.color}"></span>${esc(p.name)} ${p.ready ? '✓' : '…'}</li>`;
    }).join('');
    const inGame = mg.ids.includes(S.you);
    $('ready').hidden = !inGame || me().ready;
    $('mg-wait').textContent = inGame ? (me().ready ? 'Waiting for the others…' : 'Press Ready (or Space) when you’ve read it.') : 'You’re watching this one.';
  }
  // the game itself
  if (st.phase === 'mg' && st.mg) {
    if (!stage.open) stage.start(st.mg, { you: S.you, players, send });
    else stage.sync(st.mg);
  } else if (stage.open && st.phase !== 'mg') {
    stage.close();
  }
  // results
  $('results').hidden = st.phase !== 'mgresult' || !st.results;
  if (st.phase === 'mgresult' && st.results) {
    const r = st.results;
    $('res-name').textContent = `${r.name} · ${MODE_NAMES[r.mode]}`;
    $('res-rows').innerHTML = r.rows.map(row => {
      const p = player(row.id);
      const medal = ['🥇', '🥈', '🥉', '4th'][row.place - 1] || '';
      const team = row.team != null ? ` style="--c:${TEAM_COLORS[row.team]}" class="team-row"` : '';
      return `<tr${team}><td>${medal}</td><td><span class="dot" style="background:${p.color}"></span>${esc(p.name)}</td>
        <td>${esc(row.label)}</td><td class="${row.prize > 0 ? 'good' : row.prize < 0 ? 'bad' : ''}">${row.prize > 0 ? '+' : ''}${row.prize} 🪙</td></tr>`;
    }).join('');
  }
  // the end
  $('final').hidden = st.phase !== 'final' || !st.final;
  if (st.phase === 'final' && st.final) {
    const f = st.final;
    const winners = f.rows.filter(r => r.place === 1).map(r => player(r.id).name);
    $('fin-title').textContent = `${winners.join(' and ')} win${winners.length === 1 ? 's' : ''}!`;
    $('fin-bonus').innerHTML = f.bonus.length ? `<h3>Bonus crowns</h3><ul>${f.bonus.map(b =>
      `<li>⭐ <b>${esc(b.title)}</b>: ${b.ids.map(id => esc(player(id).name)).join(' & ')} ${esc(b.desc)} (${b.value})</li>`).join('')}</ul>` : '';
    $('fin-rows').innerHTML = f.rows.map(r => {
      const p = player(r.id);
      return `<tr><td>${['🥇', '🥈', '🥉', '4th'][r.place - 1]}</td><td><span class="dot" style="background:${p.color}"></span>${esc(p.name)}</td>
        <td>👑 ${r.crowns}</td><td>🪙 ${r.coins}</td></tr>`;
    }).join('');
  }
}

$('ready').addEventListener('click', () => { sfx.unlock(); send({ t: 'ready' }); });
$('again').addEventListener('click', () => send({ t: 'again' }));

// ---------------------------------------------------------------- keys on the board

window.addEventListener('keydown', e => {
  if (!S.st || e.repeat || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  sfx.unlock();
  const st = S.st;
  if (st.phase === 'mgintro' && (e.code === 'Space' || e.code === 'Enter') && st.mg && st.mg.ids.includes(S.you)) {
    e.preventDefault();
    send({ t: 'ready' });
  } else if (st.phase === 'board' && st.cur === S.you && st.step === 'roll' && !S.picking && (e.code === 'Space' || e.code === 'Enter')) {
    e.preventDefault();
    send({ t: 'roll' });
  }
});

// ---------------------------------------------------------------- the menu and lobby

const params = new URLSearchParams(location.search);
const roomParam = (params.get('room') || '').toUpperCase().slice(0, 4);
$('name').value = saved.name || '';
$('code').value = roomParam;

function takeName() {
  const n = $('name').value.trim().slice(0, 16);
  if (!n) { $('name').focus(); status('Pick a name first.'); return false; }
  saved.name = n;
  save();
  return true;
}

$('create').addEventListener('click', () => {
  sfx.unlock();
  if (!takeName()) return;
  S.code = null;
  connect({ create: true });
});

function joinRoom() {
  sfx.unlock();
  if (!takeName()) return;
  const code = $('code').value.trim().toUpperCase();
  if (code.length !== 4) { status('Room codes are four letters.'); return; }
  S.code = null;
  connect({ room: code });
}
$('join').addEventListener('click', joinRoom);
$('code').addEventListener('keydown', e => { if (e.key === 'Enter') joinRoom(); });
$('code').addEventListener('input', () => { $('code').value = $('code').value.toUpperCase().replace(/[^A-Z]/g, ''); });

$('copy').addEventListener('click', () => {
  navigator.clipboard?.writeText($('share').value).then(() => { $('copy').textContent = 'Copied!'; setTimeout(() => { $('copy').textContent = 'Copy'; }, 1500); });
});
$('bot-add').addEventListener('click', () => send({ t: 'bot', op: 'add' }));
$('bot-remove').addEventListener('click', () => send({ t: 'bot', op: 'remove' }));
$('rounds').addEventListener('change', () => send({ t: 'settings', rounds: +$('rounds').value }));
$('bonus').addEventListener('change', () => send({ t: 'settings', bonus: $('bonus').checked }));
$('start').addEventListener('click', () => { sfx.unlock(); send({ t: 'start' }); });

const mute = $('mute');
const showMute = () => { mute.textContent = sfx.isMuted() ? '🔇' : '🔊'; };
mute.addEventListener('click', () => { sfx.setMuted(!sfx.isMuted()); showMute(); });
showMute();

// Board animation.
let last = now();
function frame() {
  requestAnimationFrame(frame);
  const t = now();
  const dt = Math.min(0.1, t - last);
  last = t;
  if (board && !$('game').hidden && !stage.open) board.draw(dt);
}
requestAnimationFrame(frame);

// Coming back to a room link with a name already saved: straight back in.
if (roomParam && saved.name) connect({ room: roomParam });
else show('menu');

if (params.has('debug')) window.brawl = { S, send, stage, get board() { return board; } };
