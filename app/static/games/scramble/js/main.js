// Scramble in the browser: the lobby, this player's own physics and controls, everyone else as the
// server reports them, items, emotes, and the drawing. The server (app/scramble/game.py) makes the
// course, runs the bots and keeps the clock, the scores and the records.

import { BELT_H, BLINK_H, CRUMBLE, CRUMBLE_H, DT, PH, PW, SPIKE_H, blinkOn, gusting, lavaTop, posX, posY, prepare, spawn, step } from './physics.js?v=4';
import { person, startRoom } from '../../shared/lobby.js?v=1';

const $ = id => document.getElementById(id);
const show = screen => { for (const id of ['menu', 'lobby', 'game']) $(id).hidden = id !== screen; };

const S = {
  st: null,
  course: null,
  me: null,            // this browser's player (physics.js), while racing
  others: new Map(),   // id -> where the server last said they were, and where we draw them
  offset: null,        // race time minus this browser's clock
  downAt: 0,           // when this player was knocked out, to respawn a moment later
  cam: { x: 0, y: -448 },
  grabbed: new Set(),  // boxes this player has asked for an item from
  frozenUntil: 0,      // race times this player's freeze, boost and curse wear off
  boostUntil: 0,
  curseUntil: 0,
  effects: [],         // items going off, to draw for a moment: { k, by, to, blocked, at }
  incoming: [],        // bolts and freezes on their way: { k, by, to, at, dur }
  note: null,          // a line under the HUD: { text, until }
  itemsSeen: 0,        // how many items have gone off this round (the smoke test counts them)
  parts: [],           // particles, in the world: { x, y, vx, vy, life, max, color, size, g }
  shake: 0,            // how hard the screen is shaking
  emotes: new Map(),   // id -> { k, at }: a bubble over their head
  feed: [],            // the last few emotes, as lines: { text, at }
  watch: null,         // who the camera follows while this player isn't running
  landAt: -9,          // local time this player last landed (for the squash)
};

const KNOCKOUT = 1.2;   // seconds before a knocked-out racer is back at their flag (game.py too)
const FREEZE = 2.5, FREEZE_SPEED = 0.5, BOOST = 2.0, BOOST_SPEED = 1.5, CURSE = 3.0;   // game.py too
const ITEMS = {
  bolt: { icon: '⚡', name: 'Bolt', tip: 'zaps the racer just ahead', did: 'zapped', color: '#ffe14d' },
  freeze: { icon: '❄', name: 'Freeze', tip: 'slows everyone ahead', did: 'froze', color: '#9fe6ff' },
  trap: { icon: '▲', name: 'Spike trap', tip: 'drops spikes where you stand', did: 'trapped', color: '#e8452f' },
  swap: { icon: '⇄', name: 'Swap', tip: 'trade places with the racer ahead', did: 'swapped places with', color: '#c58cff' },
  shield: { icon: '◯', name: 'Shield', tip: 'blocks the next item used on you', did: 'shielded', color: '#7fd0ff' },
  boost: { icon: '»', name: 'Boost', tip: 'run faster for a moment', did: 'boosted', color: '#ffb347' },
  curse: { icon: '↺', name: 'Curse', tip: "flips the controls of the racer just ahead", did: 'cursed', color: '#b26bff' },
  grapple: { icon: '⥅', name: 'Grapple', tip: 'pulls you to the racer just ahead', did: 'grappled over to', color: '#8fe08a' },
};
const EMOTES = ['👋', '😂', '😱', '😤', '🔥', 'GG'];   // game.py's EMOTES is how many
const HATS = ['None', 'Cap', 'Crown', 'Top hat', 'Bow', 'Horns', 'Headband', 'Propeller', 'Party hat'];   // game.py's HATS
const THEMES = {
  meadow: { name: 'Meadow', sky: ['#6fb1e0', '#d6ecf5'], hills: ['#a9d0c0', '#8fbf9c'], dirt: '#7a5433', top: '#5fae4e',
    thin: ['#b07a45', '#d19a5c'], label: 'rgba(20,40,60,0.75)' },
  desert: { name: 'Dunes', tip: 'Sand slows your running: hop to keep your speed', sky: ['#f0a95f', '#fbe6bf'], hills: ['#ecc893', '#dcab6c'], dirt: '#b5773f', top: '#e6c47c',
    thin: ['#a8693a', '#d39c5d'], label: 'rgba(70,35,10,0.8)' },
  snow: { name: 'Snowfield', tip: 'Icy underfoot: slow to get going, slow to stop', sky: ['#93aecb', '#eaf2f8'], hills: ['#e3ecf3', '#c9d9e6'], dirt: '#666b7a', top: '#f6f9fc',
    thin: ['#7f8796', '#e9f1f7'], label: 'rgba(20,40,60,0.8)' },
  dusk: { name: 'Dusk', sky: ['#24285a', '#e0807a'], hills: ['#55437a', '#3b3260'], dirt: '#4b3a3a', top: '#6f8f5a',
    thin: ['#7b5a48', '#a77b5e'], label: 'rgba(255,240,230,0.85)' },
  cave: { name: 'Caverns', tip: 'Dark: you only see what\'s near you, and what glows', sky: ['#17161d', '#3a3442'], hills: ['#2c2833', '#231f29'], dirt: '#4a4250', top: '#857590',
    thin: ['#5c5060', '#8f7f94'], label: 'rgba(240,230,250,0.85)' },
};
const theme = () => THEMES[S.course?.theme] || THEMES.meadow;

const room = startRoom({ key: 'scramble', path: '/games/scramble', title: 'Scramble', show, onMessage: receive });
const local = () => performance.now() / 1000;
const raceTime = () => (S.offset == null ? -9 : local() + S.offset);
const player = id => S.st?.players.find(p => p.id === id);
const mine = () => player(room.you);
const racing = () => S.st?.phase === 'race' && S.course && mine()?.racing && mine().fin == null;

function receive(m) {
  if (m.t === 'welcome') {
    if (room.saved.hat != null) room.send({ t: 'hat', v: room.saved.hat });
  } else if (m.t === 'state') {
    const had = mine()?.item, old = S.st;
    S.st = m;
    if (S.course) S.course.traps = (m.traps || []).map(([id, x, y, w, owner]) => ({ id, x, y, w, owner }));
    if (mine()?.item && mine().item !== had) sound('item');
    if (S.course && old?.phase === 'race' && m.phase === 'race') {   // someone crossed the line: confetti
      for (const p of m.players) {
        if (p.fin != null && old.players.find(q => q.id === p.id)?.fin == null) {
          confetti(S.course.finish, -60, 40);
          if (p.id === room.you) sound('win');
        }
      }
    }
    render();
  } else if (m.t === 'course') {
    S.course = prepare(m.course);
    S.offset = m.now - local();
    S.me = Object.assign(spawn(S.course), { id: room.you });
    S.others.clear();
    S.grabbed.clear();
    S.effects = [];
    S.incoming = [];
    S.parts = [];
    S.itemsSeen = 0;
    S.note = null;
    S.watch = null;
    S.frozenUntil = S.boostUntil = S.curseUntil = 0;
    S.cam.x = 0;
    const th = theme();
    if (th.tip) S.note = { text: `${th.name}: ${th.tip}`, until: local() - m.now + 3.5 };   // shown once the race is on
  } else if (m.t === 'fx') {
    itemUsed(m);
  } else if (m.t === 'warn') {
    S.incoming.push({ ...m, at: local(), dur: m.in });
    if (m.to.includes(room.you) && racing()) {
      const shield = mine()?.item === 'shield';
      S.note = { text: `${ITEMS[m.k].icon} ${ITEMS[m.k].name} incoming!${shield ? ' Shield up!' : ''}`, until: local() + m.in + 0.2, warn: true };
      sound('warn');
    }
  } else if (m.t === 'emote') {
    S.emotes.set(m.by, { k: m.k, at: local() });
    const who = player(m.by);
    if (who) S.feed = [...S.feed.slice(-3), { text: `${who.name}: ${EMOTES[m.k]}`, color: who.color, at: local() }];
    renderFeed();
    sound('emote');
  } else if (m.t === 'pos') {
    // the clock: the message that took the least time to get here is nearest the truth
    const est = m.now - local();
    S.offset = S.offset == null || Math.abs(est - S.offset) > 0.5 ? est : Math.max(est, S.offset - 0.0005);
    for (const [id, x, y, face, air, dead, marks] of m.ps) {
      const o = S.others.get(id) || { x, y, air, dead };
      if (id !== room.you || !racing()) {
        if (o.air && !air) { o.landAt = local(); dust(x, y, 5); }
        if (!o.air && air && y < o.ty) dust(x, y, 4);
        if (!o.dead && dead) burst(x, y - PH / 2, player(id)?.color || '#fff', 14);
      }
      S.others.set(id, Object.assign(o, { tx: x, ty: y, face, air, dead, marks }));
      if (air === 2 && (id !== room.you || !racing())) {   // dashing: leave afterimages like this player's
        S.parts.push({ x, y: y - PH / 2, vx: 0, vy: 0, life: 0.18, max: 0.18, color: player(id)?.color || '#fff', size: 0, g: 0, ghost: face });
      }
    }
  }
}

// Someone used an item. If it hit this player, this browser does it to them.
function itemUsed(m) {
  const now = raceTime(), me = room.you, by = player(m.by)?.name || 'Someone', item = ITEMS[m.k];
  S.effects.push({ ...m, at: local() });
  S.incoming = S.incoming.filter(i => !(i.by === m.by && i.k === m.k));
  S.itemsSeen++;
  const hitMe = m.to.includes(me), savedMe = m.blocked.includes(me);
  if (hitMe && S.me && racing()) {
    if (m.k === 'bolt') { S.me.dead = true; S.shake = 14; }
    else if (m.k === 'freeze') S.frozenUntil = now + FREEZE;
    else if (m.k === 'boost') S.boostUntil = now + BOOST;
    else if (m.k === 'curse') S.curseUntil = now + CURSE;
  }
  if (m.warp?.[me] && S.me && racing()) {
    const [x, y, cp] = m.warp[me];
    burst(S.me.x, S.me.y - PH / 2, item.color, 10);
    Object.assign(S.me, { x, y: y - 1, vx: 0, vy: 0, cp, stood: {}, lava: {}, dead: false, on: -1, dashT: 0 });
    burst(x, y - PH / 2, item.color, 10);
  }
  const named = m.to.filter(id => id !== m.by).map(id => player(id)?.name).filter(Boolean);
  let text = '';
  if (m.by === me) {
    if (m.blocked.length) text = `${m.blocked.map(id => player(id)?.name).join(', ')} blocked your ${item.name.toLowerCase()}`;
    else if (named.length) text = `You ${item.did} ${named.join(', ')}`;
    else if (['bolt', 'swap', 'freeze', 'curse', 'grapple'].includes(m.k)) text = 'Nobody ahead to hit';
  } else if (hitMe && m.k === 'grapple') text = `${by} grappled over to you`;
  else if (hitMe) text = `${by} ${item.did} you!`;
  else if (savedMe) text = `Your shield blocked ${by}'s ${item.name.toLowerCase()}`;
  if (text) S.note = { text, until: local() + 2.5 };
  if (hitMe || m.by === me || savedMe) sound(savedMe ? 'blocked' : m.k);
}

// ---------------------------------------------------------------- the lobby, the HUD and the results

const ORDINAL = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th'];
const clock = secs => `${Math.floor(secs / 60)}:${(secs % 60).toFixed(1).padStart(4, '0')}`;
const NAMES = { gaps: 'Gaps', stairs: 'Stairs', spikes: 'Spikes', saws: 'Saws', ferry: 'Ferry', lift: 'Lift', wall: 'Wall',
  pillars: 'Pillars', bridge: 'Bridge', twins: 'Twin lifts', springs: 'Springs', stones: 'Stones', hurdles: 'Hurdles',
  crumble: 'Crumble', tunnel: 'Tunnel', launch: 'Launch', belts: 'Belts', blinkers: 'Blinkers', gusts: 'Gusts',
  lava: 'Lava', fork: 'Fork' };
const AWARD_ICONS = { 'Never fell': '🪶', Sharpshooter: '🎯', 'Most bolted': '⚡', 'Item hoarder': '🎁', 'Bounced back': '🔁' };

function hatPicker() {
  const me = mine();
  const box = $('hats');
  if (box.childElementCount !== HATS.length) {
    box.replaceChildren(...HATS.map((name, i) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.title = name;
      b.setAttribute('aria-label', name);
      const c = document.createElement('canvas');
      c.width = c.height = 88;
      b.append(c);
      b.addEventListener('click', () => {
        room.saved.hat = i;
        room.save();
        room.send({ t: 'hat', v: i });
      });
      return b;
    }));
  }
  [...box.children].forEach((b, i) => {
    b.classList.toggle('on', me?.hat === i);
    const c = b.querySelector('canvas'), g = c.getContext('2d');
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.clearRect(0, 0, 88, 88);
    g.setTransform(1.5, 0, 0, 1.5, 44, 80);
    runnerOn(g, { color: me?.color || '#888', face: 1, hat: i, still: true });
  });
}

function render() {
  const st = S.st;
  document.body.classList.toggle('host', st.host === room.you);
  if (st.phase === 'lobby') {
    show('lobby');
    const n = st.players.length;
    $('room-code').textContent = room.code;
    $('count').textContent = `${n} of 8`;
    $('seats').replaceChildren(...st.players.map(p => person(p, room.you, p.bot ? 'Bot' : p.id === st.host ? 'Host' : '')));
    $('rounds').value = st.rounds;
    $('rounds').disabled = st.host !== room.you;
    $('bot-add').disabled = n >= 8;
    $('bot-remove').disabled = !st.players.some(p => p.bot);
    $('lobby-note').textContent = st.host === room.you
      ? (n === 1 ? 'You can race the clock alone, or add bots to race against.' : '')
      : `Waiting for ${player(st.host)?.name || 'the host'} to start.`;
    hatPicker();
    return;
  }
  show('game');
  resize();
  $('hud-round').textContent = `Round ${st.round} of ${st.rounds}${S.course ? ` · ${theme().name}` : ''}`;
  const over = st.phase !== 'race';
  $('results').hidden = !over;
  if (!over) return;
  const final = st.phase === 'final';
  const rows = final ? [...st.players].filter(p => p.racing || p.pts).sort((a, b) => b.pts - a.pts)
    : st.order.map(player).filter(Boolean);
  $('res-kicker').textContent = final ? 'Final standings' : `Round ${st.round} of ${st.rounds}`;
  $('res-title').textContent = final ? `${rows[0]?.name || 'Nobody'} wins!` : `${rows[0]?.name || 'Nobody'} takes the round`;
  $('res-rows').replaceChildren(...rows.map((p, i) => {
    const tr = document.createElement('tr');
    if (p.id === room.you) tr.className = 'me';
    const cell = (text, cls) => { const td = document.createElement('td'); td.textContent = text; if (cls) td.className = cls; return td; };
    const name = cell(p.name);
    const dot = document.createElement('span');
    dot.className = 'dot';
    dot.style.setProperty('--c', p.color);
    name.prepend(dot);
    if (!final && p.stats) {
      const [falls, used, landed] = p.stats;
      const line = document.createElement('small');
      line.className = 'stats';
      const bits = [falls ? `${falls} ${falls === 1 ? 'fall' : 'falls'}` : 'no falls'];
      if (used) bits.push(`${used} ${used === 1 ? 'item' : 'items'}${landed ? `, ${landed} landed` : ''}`);
      line.textContent = bits.join(' · ');
      name.append(line);
    }
    tr.append(cell(ORDINAL[i] || ''), name, cell(p.fin != null ? clock(p.fin) : 'Did not finish'), cell(p.gain ? `+${p.gain}` : '', 'gain'), cell(p.pts));
    return tr;
  }));
  $('res-awards').replaceChildren(...(st.awards || []).map(([title, id]) => {
    const li = document.createElement('li');
    const p = player(id);
    li.textContent = `${AWARD_ICONS[title] || '🏅'} ${title}: `;
    const b = document.createElement('b');
    b.textContent = p?.name || '?';
    li.append(b);
    return li;
  }));
  const recs = st.records || [];
  $('res-records').hidden = !recs.length;
  $('res-records-title').textContent = final ? "This room's best times" : recs.length === 1 ? 'New record' : 'New records';
  $('res-records-list').replaceChildren(...recs.map(([seg, secs, who]) => {
    const li = document.createElement('li');
    li.textContent = `${NAMES[seg] || seg} ${secs.toFixed(2)} s, ${who}`;
    return li;
  }));
  $('res-note').textContent = final ? '' : 'The next course is being built…';
  $('again').hidden = $('res-leave').hidden = !final;
}

function renderFeed() {
  const t = local();
  S.feed = S.feed.filter(f => t - f.at < 4);
  $('feed').replaceChildren(...S.feed.map(f => {
    const li = document.createElement('li');
    li.textContent = f.text;
    li.style.borderLeftColor = f.color;
    return li;
  }));
}
setInterval(() => { if (S.feed.length) renderFeed(); }, 500);

$('bot-add').addEventListener('click', () => room.send({ t: 'bot', op: 'add' }));
$('bot-remove').addEventListener('click', () => room.send({ t: 'bot', op: 'remove' }));
$('rounds').addEventListener('change', () => room.send({ t: 'rounds', v: +$('rounds').value }));
$('start').addEventListener('click', () => { sound('go'); room.send({ t: 'start' }); });
$('again').addEventListener('click', () => room.send({ t: 'again' }));

// ---------------------------------------------------------------- controls

const keys = new Set();
let tapped = false, dashTapped = false;   // pressed since the last physics step, however briefly
const touch = { left: false, right: false, jump: false, dash: false };
const KEYMAP = { ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right', ArrowUp: 'jump', KeyW: 'jump', Space: 'jump',
  KeyX: 'dash', KeyK: 'dash', KeyS: 'dash', ArrowDown: 'dash' };
const USE_KEYS = new Set(['KeyE', 'ShiftLeft', 'ShiftRight', 'KeyF']);
const useItem = () => { if (racing() && mine()?.item && raceTime() > 0) room.send({ t: 'use' }); };
const emote = k => room.send({ t: 'emote', k });
addEventListener('keydown', e => {
  if ($('game').hidden || e.target.tagName === 'INPUT') return;
  if (USE_KEYS.has(e.code) && !e.repeat) { useItem(); e.preventDefault(); return; }
  const n = /^(Digit|Numpad)([1-6])$/.exec(e.code);
  if (n && !e.repeat) { emote(+n[2] - 1); return; }
  const k = KEYMAP[e.code];
  if (!k) return;
  if (!e.repeat && (k === 'left' || k === 'right') && !racing()) cycleWatch(k === 'left' ? -1 : 1);
  if (k === 'jump' && !keys.has(k)) tapped = true;
  if (k === 'dash' && !keys.has(k)) dashTapped = true;
  keys.add(k);
  e.preventDefault();
});
addEventListener('keyup', e => keys.delete(KEYMAP[e.code]));
addEventListener('blur', () => keys.clear());
for (const [id, k] of [['t-left', 'left'], ['t-right', 'right'], ['t-jump', 'jump'], ['t-dash', 'dash']]) {
  const b = $(id);
  const set = on => e => {
    e.preventDefault();
    touch[k] = on;
    if (on && k === 'jump') tapped = true;
    if (on && k === 'dash') dashTapped = true;
    if (on && (k === 'left' || k === 'right') && !racing()) cycleWatch(k === 'left' ? -1 : 1);
    b.classList.toggle('down', on);
  };
  b.addEventListener('pointerdown', set(true));
  for (const type of ['pointerup', 'pointercancel', 'pointerleave']) b.addEventListener(type, set(false));
  b.addEventListener('contextmenu', e => e.preventDefault());
}
$('t-use').addEventListener('pointerdown', e => { e.preventDefault(); useItem(); });
const coarse = matchMedia('(pointer: coarse)').matches;
$('touch').hidden = !coarse;
document.body.classList.toggle('coarse', coarse);
$('emotes').replaceChildren(...EMOTES.map((icon, k) => {
  const b = document.createElement('button');
  b.type = 'button';
  b.textContent = icon;
  b.title = `${icon} (${k + 1})`;
  b.addEventListener('click', () => { emote(k); if (coarse) $('emotes').classList.remove('open'); });
  return b;
}));
$('emote-toggle').addEventListener('click', () => $('emotes').classList.toggle('open'));
const input = () => {
  const dir = (keys.has('right') || touch.right ? 1 : 0) - (keys.has('left') || touch.left ? 1 : 0);
  return {
    dir: raceTime() < S.curseUntil ? -dir : dir,   // cursed: left is right
    jump: keys.has('jump') || touch.jump || tapped,
    dash: keys.has('dash') || touch.dash || dashTapped,
  };
};

// Watching: who's still running, front first; the arrows move along them.
function runningOthers() {
  return [...S.others.entries()].filter(([id]) => player(id)?.fin == null && player(id)?.racing && id !== room.you)
    .sort((a, b) => b[1].x - a[1].x).map(([id]) => id);
}
function cycleWatch(step) {
  const ids = runningOthers();
  if (!ids.length) return;
  const i = ids.indexOf(S.watch);
  S.watch = ids[((i < 0 ? 0 : i + step) % ids.length + ids.length) % ids.length];
}

// ---------------------------------------------------------------- sounds

let audio = null;
function sound(kind) {
  try {
    audio ||= new AudioContext();
    const [f0, f1, secs, type] = { jump: [300, 620, 0.12, 'square'], spring: [240, 980, 0.22, 'square'], out: [260, 70, 0.3, 'sawtooth'],
      flag: [520, 780, 0.1, 'triangle'], item: [700, 1400, 0.15, 'triangle'], bolt: [1600, 200, 0.25, 'sawtooth'],
      freeze: [1200, 900, 0.4, 'sine'], trap: [300, 200, 0.12, 'square'], swap: [400, 1200, 0.3, 'sine'],
      shield: [500, 900, 0.25, 'sine'], boost: [300, 900, 0.3, 'square'], blocked: [900, 500, 0.15, 'triangle'], win: [660, 1320, 0.5, 'triangle'],
      go: [880, 880, 0.25, 'square'], tick: [440, 440, 0.1, 'square'], dash: [500, 1100, 0.1, 'sawtooth'], warn: [1000, 1000, 0.18, 'square'],
      curse: [600, 150, 0.4, 'sine'], grapple: [200, 900, 0.25, 'triangle'], emote: [800, 1000, 0.06, 'sine'] }[kind];
    const o = audio.createOscillator(), g = audio.createGain(), t = audio.currentTime;
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    o.frequency.exponentialRampToValueAtTime(f1, t + secs);
    g.gain.setValueAtTime(kind === 'emote' ? 0.03 : 0.06, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + secs);
    o.connect(g).connect(audio.destination);
    o.start(t);
    o.stop(t + secs);
  } catch { /* no sound, then */ }
}

// ---------------------------------------------------------------- particles

function puff(x, y, n, color, { speed = 120, up = 60, life = 0.5, size = 5, g = 200 } = {}) {
  if (S.parts.length > 600) return;
  for (let i = 0; i < n; i++) {
    const a = Math.random() * Math.PI * 2, v = speed * (0.4 + Math.random() * 0.6);
    S.parts.push({ x, y, vx: Math.cos(a) * v, vy: Math.sin(a) * v * 0.5 - up, life, max: life, color, size: size * (0.6 + Math.random() * 0.6), g });
  }
}
const dust = (x, y, n) => puff(x, y - 2, n, 'rgba(255,255,255,0.75)', { speed: 90, up: 30, life: 0.4, size: 5, g: 60 });
const burst = (x, y, color, n) => puff(x, y, n, color, { speed: 260, up: 120, life: 0.7, size: 6, g: 700 });
function confetti(x, y, n) {
  const colors = ['#e8552f', '#3f8fe8', '#e8b923', '#4fb85f', '#9a5fd6', '#e86fa5'];
  for (let i = 0; i < n; i++) {
    puff(x + (Math.random() - 0.5) * 80, y - 100, 1, colors[i % colors.length], { speed: 240, up: 260, life: 1.6, size: 6, g: 420 });
  }
}

// ---------------------------------------------------------------- each frame: physics, then the picture

const canvas = $('view'), ctx = canvas.getContext('2d');
const VIEW_H = 640, VIEW_W = 560;   // the least of the world, in its units, that must fit on screen
function resize() {
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
  if (w && (canvas.width !== w || canvas.height !== h)) { canvas.width = w; canvas.height = h; }
}
addEventListener('resize', resize);

let lastFrame = local(), simTime = null, lastSent = 0, lastCount = null;

function simulate(now) {
  const p = S.me, c = S.course;
  if (simTime == null || now - simTime > 0.25) simTime = now;   // a tab that was asleep doesn't catch up
  const inp = input();
  while (simTime + DT <= now) {
    simTime += DT;
    if (simTime < 0) continue;   // still on the start line
    if (p.dead) {
      if (!S.downAt) {
        S.downAt = simTime;
        sound('out');
        burst(p.x, p.y - PH / 2, mine().color, 16);
        S.shake = Math.max(S.shake, 10);
      }
      if (simTime - S.downAt > KNOCKOUT) { S.me = Object.assign(p, spawn(c, p.cp)); S.downAt = 0; }
      continue;
    }
    const was = { ground: p.ground, cp: p.cp, sprung: p.sprung, vy: p.vy, dashT: p.dashT };
    p.speed = (simTime < S.frozenUntil ? FREEZE_SPEED : 1) * (simTime < S.boostUntil ? BOOST_SPEED : 1);
    step(p, inp, simTime, c);
    if (!p.dead && !mine()?.item) {
      c.boxes.forEach(([bx, by], i) => {
        if (!S.grabbed.has(i) && Math.abs(p.x - bx) < PW / 2 + 13 && p.y > by - 13 && p.y - PH < by + 13) {
          S.grabbed.add(i);
          room.send({ t: 'grab', i });
          puff(bx, by, 10, '#f2c230', { speed: 160, up: 40, life: 0.4, size: 5, g: 300 });
        }
      });
    }
    if (tapped) { tapped = false; inp.jump = keys.has('jump') || touch.jump; }
    if (dashTapped) { dashTapped = false; inp.dash = keys.has('dash') || touch.dash; }
    if (p.sprung !== was.sprung) { sound('spring'); puff(p.x, p.y, 8, '#ffd27a', { speed: 140, up: 40, life: 0.4, g: 300 }); }
    else if (was.ground && p.vy < -400) { sound('jump'); dust(p.x, p.y, 5); }
    if (!was.ground && p.ground && was.vy > 250) { S.landAt = local(); dust(p.x, p.y, Math.min(10, was.vy / 80)); }
    if (p.dashT && !was.dashT) { sound('dash'); puff(p.x, p.y - PH / 2, 8, 'rgba(255,255,255,0.8)', { speed: 80, up: 0, life: 0.3, size: 6, g: 0 }); }
    if (p.dashT) S.parts.push({ x: p.x, y: p.y - PH / 2, vx: 0, vy: 0, life: 0.18, max: 0.18, color: mine().color, size: 0, g: 0, ghost: p.face });
    if (p.cp !== was.cp) sound('flag');
  }
  if (now - lastSent > 0.066) {
    lastSent = now;
    room.send({ t: 'p', v: [Math.round(p.x), Math.round(p.y), p.face, p.ground ? 0 : p.dashT ? 2 : 1, p.dead ? 1 : 0] });
  }
}

function hud(now) {
  const st = S.st, me = mine(), banner = $('banner');
  const racers = [...S.others.entries()].map(([id, o]) => ({ id, x: id === room.you && S.me && racing() ? S.me.x : o.tx, fin: player(id)?.fin }));
  const ahead = racers.filter(r => r.id !== room.you && (r.fin != null || (me?.fin == null && r.x > (S.me?.x ?? 0)))).length;
  const place = me?.fin != null ? st.order.indexOf(room.you) : ahead;
  $('hud-place').textContent = me?.racing && racers.length > 1 ? ORDINAL[place] || '' : '';
  $('hud-time').textContent = clock(Math.max(0, me?.fin ?? now));
  let text = '', small = false;
  if (st.phase === 'race') {
    if (now < 0) {
      const n = Math.ceil(-now);
      text = n > 3 ? theme().name : String(n);
      if (n > 3 && theme().tip) { text += ` · ${theme().tip}`; small = true; }
      if (n !== lastCount && n <= 3) sound('tick');
      lastCount = n;
    } else if (now < 0.8) {
      text = 'Go!';
      if (lastCount !== 0) { lastCount = 0; sound('go'); }
    } else if (S.note?.warn && local() < S.note.until) {
      text = S.note.text;
      small = true;
    } else if (me?.fin != null) {
      text = `Finished ${ORDINAL[st.order.indexOf(room.you)] || ''}!`;
      small = now - me.fin > 2;
    } else if (!me?.racing) {
      text = "Watching: you'll race in the next round";
      small = true;
    } else if (st.ends != null) {
      text = `${Math.max(0, Math.ceil(st.ends - now))} s left`;
      small = true;
    } else if (now < S.curseUntil) {
      text = '↺ Cursed: your controls are flipped';
      small = true;
    }
  }
  if (!text && S.note && local() < S.note.until) { text = S.note.text; small = true; }
  banner.hidden = !text;
  banner.textContent = text;
  banner.classList.toggle('small', small);
  banner.classList.toggle('warn', !!(S.note?.warn && local() < S.note.until && text === S.note.text));
  const item = racing() ? ITEMS[me?.item] : null;
  $('item').hidden = !item;
  $('t-use').classList.toggle('empty', !item);
  if (item) {
    $('item-icon').textContent = item.icon;
    $('item-icon').style.color = item.color;
    $('item-name').textContent = item.name;
    $('item-tip').textContent = `${item.tip}. ${coarse ? 'Tap Use' : 'E or Shift to use'}`;
  }
  // watching someone else
  const f = st.phase === 'race' && !followingMe(now) ? S.followed : null;
  $('watching').hidden = !f;
  if (f) $('watching').textContent = `Watching ${player(f)?.name || ''} · ${coarse ? '◀ ▶' : '← →'} to switch`;
}

function frame() {
  requestAnimationFrame(frame);
  const t = local(), dt = Math.min(0.1, t - lastFrame);
  lastFrame = t;
  if (!S.st || S.st.phase === 'lobby' || !S.course || $('game').hidden) return;
  const now = raceTime();
  if (racing()) simulate(now); else simTime = null;
  for (const o of S.others.values()) {   // ease everyone else towards where they were last seen
    const k = 1 - Math.exp(-dt * 18);
    if (Math.abs(o.tx - o.x) > 400) { o.x = o.tx; o.y = o.ty; }
    o.x += (o.tx - o.x) * k;
    o.y += (o.ty - o.y) * k;
  }
  for (const q of S.parts) {
    q.life -= dt;
    q.vy += q.g * dt;
    q.x += q.vx * dt;
    q.y += q.vy * dt;
  }
  S.parts = S.parts.filter(q => q.life > 0);
  S.shake *= Math.exp(-dt * 9);
  hud(now);
  draw(now, dt);
}

// Who the camera follows: this player, or (watching, or finished) whoever they picked, or whoever is
// still running in front.
const followingMe = now => S.me && mine()?.racing && (racing() || S.st.phase !== 'race' || now - mine().fin < 2.5);
function focus(now) {
  S.followed = null;
  if (followingMe(now)) return S.me;
  const ids = runningOthers();
  if (!ids.includes(S.watch)) S.watch = ids[0] ?? null;
  S.followed = S.watch;
  return S.others.get(S.watch) || S.me || { x: 0, y: 0 };
}

function draw(now, dt) {
  const c = S.course, th = theme(), k = Math.min(canvas.height / VIEW_H, canvas.width / VIEW_W), vw = canvas.width / k, vh = canvas.height / k;
  const floor = -vh * 0.7;   // the camera's resting height: the ground 70% of the way down
  const f = focus(now), cam = S.cam;
  const wantX = Math.max(0, Math.min(f.x - vw * 0.4, c.length - vw));
  const wantY = Math.min(floor, f.y - vh * 0.4);
  const ease = 1 - Math.exp(-dt * 8);
  cam.x += (wantX - cam.x) * (Math.abs(wantX - cam.x) > 900 ? 1 : ease);
  cam.y += (wantY - cam.y) * ease;
  const t = Math.max(0, now), wall = local();
  const sx0 = (Math.random() - 0.5) * S.shake, sy0 = (Math.random() - 0.5) * S.shake;

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const sky = ctx.createLinearGradient(0, 0, 0, canvas.height);
  sky.addColorStop(0, th.sky[0]);
  sky.addColorStop(1, th.sky[1]);
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  backdrop(th, k, vw, vh, cam, wall);

  ctx.setTransform(k, 0, 0, k, (-cam.x + sx0) * k, (-cam.y + sy0) * k);
  const seen = (x, w) => x + w > cam.x - 50 && x < cam.x + vw + 50;

  // checkpoint flags and the finish
  c.segs.forEach((x, i) => {
    if (!i || i === c.segs.length - 1 || !seen(x, 80)) return;
    const up = S.me && S.me.cp >= i;
    ctx.fillStyle = '#5b4a3a';
    ctx.fillRect(x + 38, -64, 4, 64);
    ctx.fillStyle = up ? '#f2c230' : '#e9e4d8';
    const wave = Math.sin(wall * 5 + i) * 3;
    ctx.beginPath();
    ctx.moveTo(x + 42, -64); ctx.lineTo(x + 70, -54 + wave); ctx.lineTo(x + 42, -44);
    ctx.fill();
  });
  if (seen(c.finish, 60)) {
    ctx.fillStyle = '#4a3b2c';
    ctx.fillRect(c.finish - 3, -170, 6, 170);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 3; j++) {
      ctx.fillStyle = (i + j) % 2 ? '#1d1b19' : '#fff';
      ctx.fillRect(c.finish + 3 + i * 16, -170 + j * 16 + Math.sin(wall * 4 + i * 0.8) * 2, 16, 16);
    }
  }

  // rising lava, as this player sees it (each racer sets their own going)
  c.lavas.forEach((l, i) => {
    if (!seen(l.x0, l.x1 - l.x0)) return;
    const top = S.me && mine()?.racing ? lavaTop(S.me, l, i, t) : l.base;
    const g = ctx.createLinearGradient(0, top, 0, top + 200);
    g.addColorStop(0, '#ffb12e');
    g.addColorStop(0.15, '#f0561e');
    g.addColorStop(1, '#8a1d10');
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.moveTo(l.x0, 700);
    for (let x = l.x0; x <= l.x1; x += 16) ctx.lineTo(x, top + Math.sin(x / 30 + wall * 4) * 4);
    ctx.lineTo(l.x1, top);
    ctx.lineTo(l.x1, 700);
    ctx.fill();
    if (Math.random() < 0.3) puff(l.x0 + Math.random() * (l.x1 - l.x0), top, 1, '#ffcf5a', { speed: 40, up: 120, life: 0.6, size: 4, g: 300 });
  });

  for (const s of c.plats) {
    if (!seen(s.x, s.w)) continue;
    const thin = s.h <= 30;
    ctx.fillStyle = thin ? th.thin[0] : th.dirt;
    ctx.fillRect(s.x, s.y, s.w, s.h);
    ctx.fillStyle = thin ? th.thin[1] : th.top;
    ctx.fillRect(s.x, s.y, s.w, thin ? 6 : 12);
    if (!thin) { ctx.fillStyle = 'rgba(0,0,0,0.12)'; ctx.fillRect(s.x, s.y + 12, s.w, 5); }
  }
  for (const m of c.movers) {
    const x = posX(m, t), y = posY(m, t);
    if (!seen(x, m.w)) continue;
    ctx.fillStyle = '#56657a';
    ctx.fillRect(x, y, m.w, m.h);
    ctx.fillStyle = '#9fb0c6';
    ctx.fillRect(x, y, m.w, 6);
    ctx.fillStyle = '#2f3a48';
    for (const bx of [8, m.w - 12]) ctx.fillRect(x + bx, y + 11, 4, 4);
  }
  for (const s of c.belts) {
    if (!seen(s.x, s.w)) continue;
    ctx.fillStyle = '#3b3f48';
    ctx.beginPath(); ctx.roundRect(s.x, s.y, s.w, BELT_H, 10); ctx.fill();
    ctx.save();
    ctx.beginPath(); ctx.rect(s.x + 6, s.y + 3, s.w - 12, BELT_H - 6); ctx.clip();
    ctx.strokeStyle = s.v > 0 ? '#7fe08a' : '#ff8a6a';
    ctx.lineWidth = 3;
    const dir = Math.sign(s.v), off = ((t * s.v) % 24 + 24) % 24;
    for (let x = s.x - 24 + off; x < s.x + s.w + 24; x += 24) {
      ctx.beginPath(); ctx.moveTo(x - 4 * dir, s.y + 6); ctx.lineTo(x + 4 * dir, s.y + 12); ctx.lineTo(x - 4 * dir, s.y + 18); ctx.stroke();
    }
    ctx.restore();
  }
  for (const s of c.blinks) {
    if (!seen(s.x, s.w)) continue;
    const frac = ((t / s.period + s.phase) % 1 + 1) % 1;
    if (blinkOn(s, t)) {
      ctx.globalAlpha = frac > 0.38 && Math.floor(wall * 14) % 2 ? 0.45 : 1;   // flickering: about to go
      ctx.fillStyle = '#2fb5b0';
      ctx.fillRect(s.x, s.y, s.w, BLINK_H);
      ctx.fillStyle = '#9ff2e9';
      ctx.fillRect(s.x, s.y, s.w, 5);
      ctx.globalAlpha = 1;
    } else {
      ctx.strokeStyle = 'rgba(47,181,176,0.5)';
      ctx.setLineDash([6, 6]);
      ctx.lineWidth = 2;
      ctx.strokeRect(s.x + 1, s.y + 1, s.w - 2, BLINK_H - 2);
      ctx.setLineDash([]);
    }
  }
  for (const w of c.winds) {
    if (!seen(w.x, w.w)) continue;
    const on = gusting(w, t);
    ctx.strokeStyle = on ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.15)';
    ctx.lineWidth = 2;
    for (let i = 0; i < 9; i++) {
      const y = -300 + i * 33 + Math.sin(i * 7.1) * 10;
      const len = 26 + (i % 3) * 10;
      const x = w.x + ((i * 53 + (on ? wall * w.v * 1.6 : 0)) % w.w + w.w) % w.w;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.sign(w.v) * len, y); ctx.stroke();
    }
    ctx.fillStyle = on ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.35)';
    ctx.font = '700 22px "Source Sans 3", sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(w.v < 0 ? '«' : '»', w.x + w.w / 2, -330);
  }
  for (const s of c.pads) {
    if (!seen(s.x, s.w)) continue;
    const squash = S.me?.sprung != null && t - S.me.sprung < 0.15 && Math.abs(S.me.x - s.x - s.w / 2) < 120 ? 6 : 0;
    ctx.fillStyle = '#3b3f48';
    ctx.fillRect(s.x + 6, s.y - 8 + squash, s.w - 12, 8 - squash);
    ctx.fillStyle = '#e8452f';
    ctx.fillRect(s.x, s.y - 14 + squash, s.w, 6);
  }
  // crumbling blocks: as this player sees them (each racer crumbles their own)
  c.crumbles.forEach((s, i) => {
    if (!seen(s.x, s.w)) return;
    const since = S.me?.stood[i] != null ? t - S.me.stood[i] : null;
    let dx = 0, dy = 0, alpha = 1;
    if (since != null && since < CRUMBLE) dx = Math.sin(since * 80) * 2.5;
    else if (since != null) { dy = (since - CRUMBLE) ** 2 * 1400; alpha = Math.max(0, 1 - (since - CRUMBLE) * 1.5); }
    if (alpha <= 0) return;
    ctx.globalAlpha = alpha;
    ctx.fillStyle = '#9a7b5b';
    ctx.fillRect(s.x + dx, s.y + dy, s.w, CRUMBLE_H);
    ctx.fillStyle = '#6f553c';
    for (let cx = s.x + 14; cx < s.x + s.w - 8; cx += 22) ctx.fillRect(cx + dx, s.y + dy + 6, 3, CRUMBLE_H - 10);
    ctx.globalAlpha = 1;
  });
  // item boxes: faded once this player has had one
  ctx.font = '700 18px "Source Sans 3", sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  c.boxes.forEach(([bx, by], i) => {
    if (!seen(bx - 15, 30)) return;
    const bob = Math.sin(t * 3 + i) * 3;
    ctx.globalAlpha = S.grabbed.has(i) ? 0.3 : 1;
    ctx.fillStyle = '#f2c230';
    ctx.beginPath(); ctx.roundRect(bx - 13, by - 13 + bob, 26, 26, 5); ctx.fill();
    ctx.strokeStyle = '#9a6b0f'; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = '#5a3d00';
    ctx.fillText('?', bx, by + 1 + bob);
    ctx.globalAlpha = 1;
  });
  ctx.textBaseline = 'alphabetic';
  for (const s of c.traps) {
    if (!seen(s.x, s.w)) continue;
    const n = 3, w = s.w / n;
    ctx.fillStyle = player(s.owner)?.color || '#e8452f';
    ctx.beginPath();
    for (let i = 0; i < n; i++) { ctx.moveTo(s.x + i * w, s.y); ctx.lineTo(s.x + (i + 0.5) * w, s.y - SPIKE_H); ctx.lineTo(s.x + (i + 1) * w, s.y); }
    ctx.fill();
    ctx.strokeStyle = '#1d1b19'; ctx.lineWidth = 1.5; ctx.stroke();
  }
  ctx.fillStyle = '#c9ced6';
  for (const s of c.spikes) {
    if (!seen(s.x, s.w)) continue;
    const n = Math.max(2, Math.round(s.w / 14)), w = s.w / n;
    ctx.beginPath();
    for (let i = 0; i < n; i++) { ctx.moveTo(s.x + i * w, s.y); ctx.lineTo(s.x + (i + 0.5) * w, s.y - SPIKE_H); ctx.lineTo(s.x + (i + 1) * w, s.y); }
    ctx.fill();
  }
  for (const s of c.saws) {
    const x = posX(s, t), y = posY(s, t);
    if (!seen(x - s.r, s.r * 2)) continue;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(t * 9);
    ctx.fillStyle = '#d4d9e0';
    ctx.beginPath();
    for (let i = 0; i < 20; i++) { const a = i / 20 * Math.PI * 2, r = i % 2 ? s.r : s.r - 7; ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r); }
    ctx.fill();
    ctx.fillStyle = '#7d8794';
    ctx.beginPath(); ctx.arc(0, 0, s.r * 0.35, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  // everyone else, then this player on top
  ctx.font = '600 13px "Source Sans 3", sans-serif';
  ctx.textAlign = 'center';
  const meRacing = S.me && mine()?.racing;
  for (const [id, o] of S.others) {
    if (id === room.you && meRacing) continue;
    const p = player(id);
    if (!p || !seen(o.x - 20, 40)) continue;
    runner(o.x, o.y, { color: p.color, face: o.face, air: o.air, dead: o.dead, alpha: 0.85, marks: o.marks || 0, hat: p.hat,
      landed: wall - (o.landAt ?? -9), moving: Math.abs(o.tx - o.x) > 0.5, dashing: o.air === 2 });
    ctx.fillStyle = th.label;
    ctx.fillText(p.name, o.x, o.y - PH - 12);
    if (p.item && p.fin == null) holding(o.x + ctx.measureText(p.name).width / 2 + 12, o.y - PH - 17);
  }
  // dash afterimages
  for (const q of S.parts) {
    if (q.ghost == null) continue;
    ctx.globalAlpha = q.life / q.max * 0.4;
    ctx.fillStyle = q.color;
    ctx.beginPath(); ctx.roundRect(q.x - PW / 2, q.y - PH / 2, PW, PH - 8, 7); ctx.fill();
  }
  ctx.globalAlpha = 1;
  if (meRacing) {
    const p = S.me;
    const marks = (mine().shield ? 1 : 0) | (t < S.frozenUntil ? 2 : 0) | (t < S.boostUntil ? 4 : 0) | (t < S.curseUntil ? 8 : 0);
    runner(p.x, p.y, { color: mine().color, face: p.face, air: !p.ground, dead: p.dead, alpha: 1, marks, hat: mine().hat,
      landed: wall - S.landAt, moving: Math.abs(p.vx) > 20, dashing: p.dashT > 0 });
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.moveTo(p.x - 6, p.y - PH - 18); ctx.lineTo(p.x + 6, p.y - PH - 18); ctx.lineTo(p.x, p.y - PH - 10); ctx.fill();
  }
  for (const q of S.parts) {
    if (q.ghost != null) continue;
    ctx.globalAlpha = Math.min(1, q.life / q.max * 1.5);
    ctx.fillStyle = q.color;
    ctx.fillRect(q.x - q.size / 2, q.y - q.size / 2, q.size, q.size);
  }
  ctx.globalAlpha = 1;
  drawIncoming();
  drawEffects();
  drawEmotes(wall);

  // in front of everything, on the screen: the caverns' dark, the weather, then the race so far
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  if (c.theme === 'cave') darkness(f, k, cam.x - sx0, cam.y - sy0, t, wall);
  weather(th, wall);
  if (S.incoming.some(i => i.to.includes(room.you)) && racing()) {
    const g = ctx.createRadialGradient(canvas.width / 2, canvas.height / 2, canvas.height * 0.35, canvas.width / 2, canvas.height / 2, canvas.height * 0.8);
    g.addColorStop(0, 'rgba(255,40,40,0)');
    g.addColorStop(1, `rgba(255,40,40,${0.25 + 0.15 * Math.sin(wall * 20)})`);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  progress();
}

// The caverns are dark: everything goes dim except near the racer the camera follows, faintly near
// the others, and round what glows (saws, item boxes, flags, the finish, rising lava).
function darkness(f, k, cx, cy, t, wall) {
  const W = canvas.width, H = canvas.height, c = S.course;
  const g = (S.dark ||= document.createElement('canvas')).getContext('2d');
  if (S.dark.width !== W || S.dark.height !== H) { S.dark.width = W; S.dark.height = H; }
  g.globalCompositeOperation = 'source-over';
  g.clearRect(0, 0, W, H);
  g.fillStyle = 'rgba(8,6,14,0.88)';
  g.fillRect(0, 0, W, H);
  g.globalCompositeOperation = 'destination-out';
  const light = (x, y, r, a = 1) => {
    const sx = (x - cx) * k, sy = (y - cy) * k, sr = r * k;
    if (sx < -sr || sx > W + sr || sy < -sr || sy > H + sr) return;
    const grad = g.createRadialGradient(sx, sy, sr * 0.35, sx, sy, sr);
    grad.addColorStop(0, `rgba(0,0,0,${a})`);
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    g.fillStyle = grad;
    g.fillRect(sx - sr, sy - sr, sr * 2, sr * 2);
  };
  const flicker = 1 + Math.sin(wall * 9) * 0.02 + Math.sin(wall * 23) * 0.015;
  light(f.x, f.y - PH / 2, 300 * flicker);
  for (const [id, o] of S.others) if (o !== f && !(id === room.you && f === S.me)) light(o.x, o.y - PH / 2, 90, 0.7);
  for (const s of c.saws) light(posX(s, t), posY(s, t), s.r + 46, 0.75);
  for (const [bx, by] of c.boxes) light(bx, by, 60, 0.7);
  c.segs.forEach((x, i) => { if (i) light(x + 50, -54, 70, 0.6); });
  light(c.finish + 30, -100, 200, 0.8);
  c.lavas.forEach((l, i) => {
    const top = S.me && mine()?.racing ? lavaTop(S.me, l, i, t) : l.base;
    for (let x = l.x0 + 60; x < l.x1; x += 120) light(x, top, 110, 0.6);
  });
  ctx.drawImage(S.dark, 0, 0);
}

// The sky's far layers, and what's in it, by theme.
function backdrop(th, k, vw, vh, cam, wall) {
  const W = canvas.width, H = canvas.height;
  if (S.course.theme === 'dusk' || S.course.theme === 'cave') {
    ctx.fillStyle = 'rgba(255,255,255,0.8)';
    for (let i = 0; i < 60; i++) {
      const x = ((i * 137.5 - cam.x * 0.03) % W + W) % W, y = (i * 61.7) % (H * 0.5);
      const tw = S.course.theme === 'dusk' ? 0.5 + 0.5 * Math.sin(wall * 2 + i) : 0.25;
      ctx.globalAlpha = tw;
      ctx.fillRect(x, y, 2, 2);
    }
    ctx.globalAlpha = 1;
  }
  if (S.course.theme === 'dusk') {
    ctx.fillStyle = '#f6e7c8';
    ctx.beginPath(); ctx.arc(W * 0.78, H * 0.2, 34 * k, 0, Math.PI * 2); ctx.fill();
  } else if (S.course.theme === 'desert') {
    ctx.fillStyle = 'rgba(255,240,180,0.9)';
    ctx.beginPath(); ctx.arc(W * 0.8, H * 0.22, 48 * k, 0, Math.PI * 2); ctx.fill();
  } else if (S.course.theme === 'meadow' || S.course.theme === 'snow') {
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    for (let i = 0; i < 5; i++) {
      const x = ((i * 420 - cam.x * 0.08 + wall * 6) % (vw + 300) + vw + 300) % (vw + 300) - 150, y = 60 + (i * 47) % 140;
      for (const [dx, dy, r] of [[0, 0, 28], [30, -10, 34], [62, 0, 26]]) {
        ctx.beginPath(); ctx.arc((x + dx) * k, (y + dy) * k, r * k, 0, Math.PI * 2); ctx.fill();
      }
    }
  }
  // far hills (or cave walls), drifting past slower than the course
  for (const [i, depth, h, wave] of [[0, 0.15, 150, 520], [1, 0.35, 100, 340]]) {
    ctx.fillStyle = th.hills[i];
    ctx.beginPath();
    ctx.moveTo(0, H);
    for (let sx = 0; sx <= vw + 40; sx += 40) {
      const wx = sx + cam.x * depth;
      let y = vh * 0.72 - h * (0.5 + 0.5 * Math.sin(wx / wave) * Math.cos(wx / (wave * 2.7)));
      if (S.course.theme === 'desert') y = vh * 0.72 - h * 0.6 * (0.5 + 0.5 * Math.sin(wx / (wave * 1.4)));
      if (S.course.theme === 'snow') y = vh * 0.72 - h * 1.3 * Math.abs(Math.sin(wx / (wave * 0.8)));
      ctx.lineTo(sx * k, y * k);
    }
    ctx.lineTo(W, H);
    ctx.fill();
  }
  if (S.course.theme === 'cave') {   // stalactites along the roof
    ctx.fillStyle = '#2a2530';
    for (let sx = -40; sx <= vw + 40; sx += 34) {
      const wx = sx + cam.x * 0.5, n = Math.sin(wx * 0.37) * 0.5 + 0.5;
      const x = sx - ((cam.x * 0.5) % 34);
      ctx.beginPath(); ctx.moveTo(x * k, 0); ctx.lineTo((x + 17) * k, (20 + n * 70) * k); ctx.lineTo((x + 34) * k, 0); ctx.fill();
    }
  }
}

// Falling snow, or drifting embers in the cave, over everything.
function weather(th, wall) {
  const W = canvas.width, H = canvas.height, theme = S.course.theme;
  if (theme !== 'snow' && theme !== 'cave' && theme !== 'desert') return;
  const n = theme === 'snow' ? 70 : 25;
  ctx.fillStyle = theme === 'snow' ? 'rgba(255,255,255,0.85)' : theme === 'cave' ? 'rgba(255,170,80,0.6)' : 'rgba(255,230,180,0.5)';
  for (let i = 0; i < n; i++) {
    const speed = theme === 'snow' ? 40 + (i % 5) * 12 : theme === 'cave' ? -18 - (i % 4) * 6 : 6;
    const x = ((i * 97.3 + Math.sin(wall + i) * 20 + (theme === 'desert' ? wall * 120 : 0) - S.cam.x * 0.4) % W + W) % W;
    const y = ((i * 53.1 + wall * speed * 3) % H + H) % H;
    const r = theme === 'snow' ? 1.5 + (i % 3) : 1.5;
    ctx.fillRect(x, y, r * 2, r * 2);
  }
}

// The race so far, as a strip along the top: the flags, the finish and everyone on it.
function progress() {
  const c = S.course, dpr = canvas.width / (canvas.clientWidth || canvas.width);
  const top = (coarse ? 50 : 46) * dpr, x0 = 18 * dpr, x1 = canvas.width - 18 * dpr, span = x1 - x0;
  const at = x => x0 + span * Math.max(0, Math.min(1, x / c.finish));
  ctx.fillStyle = 'rgba(20,40,60,0.35)';
  ctx.beginPath(); ctx.roundRect(x0 - 6 * dpr, top - 7 * dpr, span + 12 * dpr, 14 * dpr, 7 * dpr); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.55)';
  ctx.fillRect(x0, top - dpr, span, 2 * dpr);
  for (let i = 1; i < c.segs.length - 1; i++) {
    ctx.fillStyle = S.me && S.me.cp >= i && mine()?.racing ? '#f2c230' : 'rgba(255,255,255,0.7)';
    ctx.fillRect(at(c.segs[i]) - dpr, top - 5 * dpr, 2 * dpr, 10 * dpr);
  }
  for (let i = 0; i < 3; i++) {   // a chequered finish
    ctx.fillStyle = i % 2 ? '#1d1b19' : '#fff';
    ctx.fillRect(x1 - 2 * dpr, top - 6 * dpr + i * 4 * dpr, 4 * dpr, 4 * dpr);
  }
  const dots = [...S.others.entries()].map(([id, o]) => ({ id, x: id === room.you && S.me && racing() ? S.me.x : o.x }));
  dots.sort((a, b) => (a.id === room.you) - (b.id === room.you));   // this player on top
  for (const d of dots) {
    const p = player(d.id);
    if (!p?.racing) continue;
    const me = d.id === room.you;
    ctx.fillStyle = p.color;
    ctx.strokeStyle = me ? '#fff' : 'rgba(0,0,0,0.4)';
    ctx.lineWidth = (me ? 2.5 : 1) * dpr;
    ctx.beginPath(); ctx.arc(at(d.x), top, (me ? 7 : 5) * dpr, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }
}

// Where a racer is drawn: this player from their own physics, anyone else as last reported.
function at(id) {
  if (id === room.you && S.me && mine()?.racing) return S.me;
  return S.others.get(id);
}

// A "?" over a racer holding something.
function holding(x, y) {
  ctx.fillStyle = '#f2c230';
  ctx.beginPath(); ctx.roundRect(x - 8, y - 8, 16, 16, 4); ctx.fill();
  ctx.fillStyle = '#5a3d00';
  ctx.font = '700 12px "Source Sans 3", sans-serif';
  ctx.fillText('?', x, y + 4);
  ctx.font = '600 13px "Source Sans 3", sans-serif';
}

// Bolts and freezes on their way: a glowing ball flying from the user to each target.
function drawIncoming() {
  const t = local();
  S.incoming = S.incoming.filter(i => t - i.at < i.dur + 0.3);
  for (const i of S.incoming) {
    const from = at(i.by), u = Math.min(1, (t - i.at) / i.dur);
    if (!from) continue;
    for (const id of i.to) {
      const to = at(id);
      if (!to) continue;
      const x = from.x + (to.x - from.x) * u, y = from.y - PH / 2 + (to.y - from.y) * u - Math.sin(u * Math.PI) * 90;
      ctx.fillStyle = ITEMS[i.k].color;
      ctx.globalAlpha = 0.35;
      ctx.beginPath(); ctx.arc(x, y, 16, 0, Math.PI * 2); ctx.fill();
      ctx.globalAlpha = 1;
      ctx.beginPath(); ctx.arc(x, y, 8, 0, Math.PI * 2); ctx.fill();
      if (Math.random() < 0.5) S.parts.push({ x, y, vx: 0, vy: 0, life: 0.3, max: 0.3, color: ITEMS[i.k].color, size: 4, g: 0 });
    }
  }
}

// Items going off: a bolt's lightning, a freeze's frost, a swap's swirl, a blocked hit's pop.
function drawEffects() {
  const t = local();
  S.effects = S.effects.filter(e => t - e.at < 0.6);
  for (const e of S.effects) {
    const age = (t - e.at) / 0.6, from = at(e.by);
    ctx.globalAlpha = 1 - age;
    ctx.strokeStyle = ITEMS[e.k].color;
    ctx.lineWidth = 4;
    for (const id of [...e.to, ...e.blocked]) {
      const to = at(id);
      if (!to) continue;
      if ((e.k === 'bolt' || e.k === 'grapple') && from) {
        ctx.beginPath();
        ctx.moveTo(from.x, from.y - PH / 2);
        for (let i = 1; i <= 8; i++) {
          const u = i / 8, jag = e.k === 'bolt' && i < 8 ? Math.sin(i * 12.9 + e.at * 50) * 14 : 0;
          ctx.lineTo(from.x + (to.x - from.x) * u + jag, from.y - PH / 2 + (to.y - from.y) * u - Math.sin(u * Math.PI) * 60);
        }
        ctx.stroke();
      }
      if (e.k !== 'boost') {
        ctx.beginPath();
        ctx.arc(to.x, to.y - PH / 2, 20 + age * 40, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }
}

// Emote bubbles over racers' heads, for two seconds.
function drawEmotes(wall) {
  for (const [id, e] of S.emotes) {
    const age = wall - e.at;
    if (age > 2) { S.emotes.delete(id); continue; }
    const o = at(id);
    if (!o || !player(id)?.racing) continue;
    const pop = Math.min(1, age * 8), y = o.y - PH - 48 - Math.min(age, 0.3) * 20;
    ctx.globalAlpha = age > 1.6 ? (2 - age) / 0.4 : 1;
    ctx.save();
    ctx.translate(o.x, y);
    ctx.scale(pop, pop);
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.roundRect(-22, -18, 44, 32, 10); ctx.fill();
    ctx.beginPath(); ctx.moveTo(-6, 14); ctx.lineTo(0, 22); ctx.lineTo(6, 14); ctx.fill();
    ctx.fillStyle = '#2b2620';
    ctx.font = EMOTES[e.k] === 'GG' ? '800 16px "Source Sans 3", sans-serif' : '20px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(EMOTES[e.k], 0, -2);
    ctx.restore();
    ctx.textBaseline = 'alphabetic';
    ctx.globalAlpha = 1;
  }
  ctx.font = '600 13px "Source Sans 3", sans-serif';
}

// A racer at (x, y), the middle of their feet.
function runner(x, y, opts) {
  ctx.save();
  ctx.translate(x, y);
  runnerOn(ctx, { ...opts, x });
  ctx.restore();
}

// A racer drawn at the origin on `g` (the hat picker uses it too). `landed` is seconds since they
// last landed (for the squash); `moving` swings the legs.
function runnerOn(g, { color, face = 1, air = false, dead = false, alpha = 1, marks = 0, hat = 0, landed = 9, moving = false, dashing = false, x = 0, still = false }) {
  g.globalAlpha = dead ? 0.35 : alpha;
  const sq = landed < 0.18 ? Math.sin(landed / 0.18 * Math.PI) * 0.22 : 0;
  const stretch = air && !dashing ? 0.08 : 0;
  g.scale(1 + sq - stretch + (dashing ? 0.2 : 0), 1 - sq + stretch - (dashing ? 0.15 : 0));
  const body = PH - 9, w = PW;
  if (marks & 4) {   // boosted: speed lines behind
    g.strokeStyle = '#ffb347';
    g.lineWidth = 3;
    for (const ly of [-PH * 0.3, -PH * 0.55, -PH * 0.8]) { g.beginPath(); g.moveTo(-face * 18, ly); g.lineTo(-face * 40, ly); g.stroke(); }
  }
  // legs: a run cycle by distance while on the ground, tucked in the air
  g.strokeStyle = shade(color, -0.35);
  g.lineWidth = 5;
  g.lineCap = 'round';
  const phase = still ? 0 : x / 14;
  for (const side of [-1, 1]) {
    let fx, fy;
    if (air) { fx = side * 5 + face * 3; fy = -4; }
    else if (moving) { fx = side * 3 + Math.sin(phase + (side > 0 ? Math.PI : 0)) * 8; fy = -Math.max(0, Math.cos(phase + (side > 0 ? Math.PI : 0))) * 4 - 1; }
    else { fx = side * 6; fy = -1; }
    g.beginPath(); g.moveTo(side * 5, -9); g.lineTo(fx, fy); g.stroke();
  }
  g.fillStyle = color;
  g.beginPath();
  g.roundRect(-w / 2, -PH, w, body, 8);
  g.fill();
  g.fillStyle = 'rgba(255,255,255,0.18)';
  g.beginPath(); g.roundRect(-w / 2 + 3, -PH + 3, 6, body - 10, 3); g.fill();
  // eyes
  g.fillStyle = '#fff';
  g.fillRect(face > 0 ? 1 : -9, -PH + 9, 8, 9);
  g.fillStyle = '#1d1b19';
  if (dead) { g.fillRect(face > 0 ? 2 : -8, -PH + 13, 6, 2); }
  else g.fillRect(face > 0 ? 5 : -9, -PH + 12, 4, 5);
  drawHat(g, hat, face, color);
  if (marks & 2) {   // frozen: a crust of ice
    g.fillStyle = 'rgba(170, 230, 255, 0.55)';
    g.beginPath(); g.roundRect(-w / 2 - 3, -PH - 3, w + 6, PH + 3, 8); g.fill();
  }
  if (marks & 8) {   // cursed: a purple swirl round the head
    const a = performance.now() / 150;
    g.fillStyle = '#b26bff';
    for (let i = 0; i < 3; i++) {
      const b = a + i * 2.1;
      g.beginPath(); g.arc(Math.cos(b) * 16, -PH - 6 + Math.sin(b) * 4, 3.5, 0, Math.PI * 2); g.fill();
    }
  }
  if (marks & 1) {   // shielded: a bubble
    g.strokeStyle = 'rgba(127, 208, 255, 0.9)';
    g.fillStyle = 'rgba(127, 208, 255, 0.15)';
    g.lineWidth = 2.5;
    g.beginPath(); g.arc(0, -PH / 2, PH * 0.8, 0, Math.PI * 2); g.fill(); g.stroke();
  }
  g.globalAlpha = 1;
}

function shade(hex, by) {
  const n = parseInt(hex.slice(1), 16);
  const ch = s => Math.max(0, Math.min(255, Math.round(((n >> s) & 255) * (1 + by))));
  return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
}

// Hats sit on top of the head (y = -PH); `face` is which way they look.
function drawHat(g, hat, face, color) {
  const top = -PH;
  g.lineCap = 'butt';
  switch (hat) {
    case 1:   // cap
      g.fillStyle = '#2f5fb3';
      g.beginPath(); g.arc(0, top + 2, 13, Math.PI, 0); g.fill();
      g.fillRect(face > 0 ? 4 : -20, top, 16, 4);
      break;
    case 2:   // crown
      g.fillStyle = '#f2c230';
      g.beginPath();
      g.moveTo(-12, top + 2); g.lineTo(-12, top - 10); g.lineTo(-6, top - 4); g.lineTo(0, top - 13); g.lineTo(6, top - 4); g.lineTo(12, top - 10); g.lineTo(12, top + 2);
      g.fill();
      g.fillStyle = '#e8452f'; g.fillRect(-2, top - 4, 4, 4);
      break;
    case 3:   // top hat
      g.fillStyle = '#1d1b19';
      g.fillRect(-15, top - 1, 30, 4);
      g.fillRect(-10, top - 20, 20, 20);
      g.fillStyle = '#c0392b'; g.fillRect(-10, top - 6, 20, 4);
      break;
    case 4:   // bow
      g.fillStyle = '#e86fa5';
      g.beginPath(); g.moveTo(0, top + 1); g.lineTo(-11, top - 7); g.lineTo(-11, top + 7); g.fill();
      g.beginPath(); g.moveTo(0, top + 1); g.lineTo(11, top - 7); g.lineTo(11, top + 7); g.fill();
      g.beginPath(); g.arc(0, top + 1, 3.5, 0, Math.PI * 2); g.fill();
      break;
    case 5:   // horns
      g.fillStyle = '#e9dcbc';
      g.strokeStyle = '#7d6a48';
      g.lineWidth = 1.5;
      for (const s of [-1, 1]) {
        g.beginPath(); g.moveTo(s * 5, top + 2); g.quadraticCurveTo(s * 17, top - 2, s * 15, top - 14); g.lineTo(s * 12, top + 2); g.closePath(); g.fill(); g.stroke();
      }
      break;
    case 6:   // headband
      g.fillStyle = '#e8452f';
      g.fillRect(-PW / 2, top + 4, PW, 4);
      g.beginPath(); g.moveTo(-face * PW / 2, top + 5); g.lineTo(-face * (PW / 2 + 10), top + 2); g.lineTo(-face * (PW / 2 + 9), top + 9); g.fill();
      break;
    case 7: {   // propeller beanie
      g.fillStyle = shade(color, 0.35);
      g.beginPath(); g.arc(0, top + 2, 11, Math.PI, 0); g.fill();
      g.fillStyle = '#1d1b19'; g.fillRect(-1, top - 13, 2, 6);
      const spin = Math.sin(performance.now() / 40) * 12;
      g.fillStyle = '#e8b923'; g.fillRect(-Math.abs(spin), top - 15, Math.abs(spin) * 2, 3);
      break;
    }
    case 8:   // party hat
      g.fillStyle = '#9a5fd6';
      g.beginPath(); g.moveTo(-9, top + 1); g.lineTo(0, top - 20); g.lineTo(9, top + 1); g.fill();
      g.fillStyle = '#e8b923';
      g.beginPath(); g.arc(0, top - 20, 3.5, 0, Math.PI * 2); g.fill();
      g.fillRect(-5, top - 9, 10, 2.5);
      break;
    default:
  }
}

requestAnimationFrame(frame);
if (room.debug) window.scramble = { S, room, keys, raceTime };
