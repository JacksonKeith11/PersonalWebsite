// Kingfall: boot, the menus, and the connection to the room. docs/kingfall.md describes the game.
import { setAtlas } from './rig.js?v=2';
import { Input, slotOf, padName } from './input.js?v=2';
import { Net, ME } from './net.js?v=2';
import { FightScene } from './fight.js?v=2';
import { show, hide, navFrame, esc, portrait, setAtlasImage, LOOK_NAMES, buildHud, updateHud, banner, hideHud, $ } from './ui.js?v=2';
import { unlock, sfx } from './audio.js?v=2';

const VERSION = new URL(import.meta.url).searchParams.get('v');
const DEBUG = new URLSearchParams(location.search).has('debug');
const ONLY = DEBUG ? new URLSearchParams(location.search).get('boss') : null;  // ?debug&boss=mire starts the run there  // ?debug: window.kf, and the host may skip a fight
const BASE = '/static/games/kingfall/';
const LOOKS = ['knight', 'pilgrim', 'hunter', 'sellsword'];

const S = { me: null, code: null, data: null, lobby: null, scene: null, fightMsg: null, screen: 'title', error: '' };
const input = new Input();
let net = null;

// ------------------------------------------------------------------ Phaser, at a whole-number zoom
const zoom = () => Math.max(1, Math.floor(Math.min(innerWidth / 640, innerHeight / 360)));
class Boot extends Phaser.Scene {
  constructor() { super('boot'); }
  preload() {
    this.load.image('atlas', `${BASE}art/atlas.png?v=${VERSION}`);
    this.load.json('atlasmeta', `${BASE}art/atlas.json?v=${VERSION}`);
  }
  create() {
    setAtlas(this.cache.json.get('atlasmeta'));
    setAtlasImage(this.textures.get('atlas').getSourceImage());
    render();
  }
}
const game = new Phaser.Game({
  type: Phaser.AUTO, parent: 'game', width: 640, height: 360, zoom: zoom(), pixelArt: true, roundPixels: true,
  backgroundColor: '#0c0a10', scene: [Boot, FightScene], scale: { mode: Phaser.Scale.NONE },
  input: { mouse: { preventDefaultWheel: false } }, banner: false,
});
// fill the window at that zoom (wider screens see a little more of the arena)
function fit() {
  const z = zoom();
  game.scale.resize(Math.min(800, Math.ceil(innerWidth / z)), Math.min(450, Math.ceil(innerHeight / z)));
  game.scale.setZoom(z);
}
addEventListener('resize', fit);
fit();

// ------------------------------------------------------------------ the loop for menus and joining
function frame() {
  input.poll();
  if (!S.scene) navFrame(input);
  if (S.screen === 'lobby') lobbyDevices();
  requestAnimationFrame(frame);
if (DEBUG) window.kf = { S, input, win: () => net.send({ t: 'debugwin' }), get net() { return net; } };
}

function lobbyDevices() {
  const mine = myHeroes();
  for (const d of input.devices()) {
    const slot = slotOf(d.id);
    const typing = document.activeElement && document.activeElement.tagName === 'INPUT';
    if (d.id !== 'kb' && d.pressed('start') && !mine.some(h => h.slot === slot)) addHero(slot);
    if (d.id !== 'kb' && d.pressed('start') && mine.some(h => h.slot === slot) && S.lobby.host === S.me && !typing) start();
  }
}

const myHeroes = () => (S.lobby ? S.lobby.heroes.filter(h => h.conn === S.me) : []);

function addHero(slot) {
  if (!S.lobby || S.lobby.heroes.length >= 4) return;
  const used = new Set(S.lobby.heroes.map(h => h.look));
  const look = (slot === 0 && ME.saved.look) || LOOKS.find(l => !used.has(l)) || LOOKS[slot % 4];
  const name = slot === 0 ? (ME.saved.name || 'Wanderer') : `${ME.saved.name || 'Wanderer'} ${slot + 1}`;
  net.send({ t: 'add', slot, name, look, weapon: (slot === 0 && ME.saved.weapon) || 'sword' });
  sfx.ui();
}

function start() { if (S.lobby && S.lobby.heroes.length) net.send({ t: 'start', only: ONLY || undefined }); }

// ------------------------------------------------------------------ screens
function render() {
  if (S.scene) return;
  if (S.screen === 'title') return title();
  if (S.screen === 'lobby') return S.lobby && S.lobby.state === 'bonfire' ? bonfire() : lobby();
}

// ------------------------------------------------------------------ the Bonfire, between fights
const RARE_COL = { common: '#b8b0a0', rare: '#4a9ae0', epic: '#c060ff' };
const SLOT_NAME = { light: 'Light', heavy: 'Heavy', special: 'Special', dodge: 'Dodge', guard: 'Guard' };

function upgradeCard(uid, rarity, i, h) {
  const U = S.data.upgrades[uid], V = U.vow ? S.data.vows[U.vow] : null;
  const held = U.slot && h.ups.find(([x]) => S.data.upgrades[x].slot === U.slot);
  const kind = U.duo ? 'Duo' : U.pact ? 'Pact' : U.weapon ? 'Weapon Art' : U.slot ? SLOT_NAME[U.slot] : 'Passive';
  return `<button class="card-up" data-nav data-pick="${h.id}:${i}" style="--v:${V ? V.colour : '#c8a040'};--r:${RARE_COL[rarity]}">
    <span class="up-top"><b>${esc(U.name)}</b><i>${rarity}</i></span>
    <span class="up-kind">${V ? esc(V.name) + ' · ' : ''}${kind}</span>
    <span class="up-text">${esc(U.text[rarity])}</span>
    ${held ? `<span class="up-rep">Replaces ${esc(S.data.upgrades[held[0]].name)}</span>` : ''}
  </button>`;
}

function bonfire() {
  const L = S.lobby, D = S.data, mine = myHeroes();
  const next = D.bosses[L.run[L.stage]];
  const others = L.heroes.filter(h => h.conn !== S.me);
  const el = show(`<div class="screen bonfire">
    <div class="row" style="justify-content:space-between;align-items:flex-end">
      <div><h2 style="margin:0">The Bonfire</h2><div class="hint">Fight ${L.stage + 1} of ${L.of} next: <b style="color:var(--text)">${esc(next ? next.name : '')}</b></div></div>
      <div class="coins">${L.coins} <small>coins</small></div>
    </div>
    <div class="panels">${mine.map(h => panel(h)).join('')}</div>
    ${others.length ? `<div class="hint" style="margin-top:12px">${others.map(h => `${esc(h.name)}: ${h.ready ? 'ready' : 'choosing…'}`).join(' · ')}</div>` : ''}
  </div>`);
  const send = (t, h, extra = {}) => net.send({ t, h, ...extra });
  el.querySelectorAll('[data-pick]').forEach(b => b.onclick = () => { const [h, i] = b.dataset.pick.split(':').map(Number); send('pick', h, { i }); sfx.ui(); });
  el.querySelectorAll('[data-attr]').forEach(b => b.onclick = () => { const [h, a] = b.dataset.attr.split(':'); send('attr', +h, { a }); });
  el.querySelectorAll('[data-buy]').forEach(b => b.onclick = () => { const [h, item] = b.dataset.buy.split(':'); send('buy', +h, { item }); });
  el.querySelectorAll('[data-weapon]').forEach(b => b.onclick = () => { const [h, w] = b.dataset.weapon.split(':'); send('weapon', +h, { weapon: w }); });
  el.querySelectorAll('[data-ready]').forEach(b => b.onclick = () => { const h = L.heroes.find(x => x.id === +b.dataset.ready); send('ready', h.id, { on: !h.ready }); });
}

function panel(h) {
  const L = S.lobby, D = S.data, W = D.weapons[h.weapon], P = L.prices;
  const ups = h.ups.map(([u, r]) => `<span class="chip" style="--r:${RARE_COL[r]}" title="${esc(D.upgrades[u].text[r])}">${esc(D.upgrades[u].name)}</span>`).join('');
  return `<div class="panel" style="--c:${D.colours[h.colour]}">
    <div class="row"><b class="pname">${esc(h.name)}</b><span class="hint">Level ${h.level} · ${esc(W.name)} · ${h.mhp} health · ${h.maxflasks} flasks</span></div>
    ${h.points ? `<h3>Level up: ${h.points} point${h.points > 1 ? 's' : ''}</h3><div class="attrs">${D.attrs.map(([k, name, text]) =>
      `<button class="btn attr" data-nav data-attr="${h.id}:${k}"><b>${name} ${h.attrs[k]}</b><small>${text}</small></button>`).join('')}</div>` : ''}
    ${h.offer.length ? `<h3>Choose a blessing${h.picks > 1 ? ` (${h.picks})` : ''}</h3><div class="cards-up">${h.offer.map(([u, r], i) => upgradeCard(u, r, i, h)).join('')}</div>` : ''}
    ${h.swap ? `<h3>The weapon shrine</h3><div class="row">${Object.values(D.weapons).map(w =>
      `<button class="btn" data-nav data-weapon="${h.id}:${w.id}" ${w.id === h.weapon ? 'disabled' : ''}>${esc(w.name)}</button>`).join('')}</div><div class="hint">Changing weapon keeps your blessings but loses your Weapon Arts.</div>` : ''}
    <h3>Shop</h3><div class="row">
      ${h.offer.length ? `<button class="btn" data-nav data-buy="${h.id}:reroll" ${L.coins < P.reroll ? 'disabled' : ''}>Reroll (${P.reroll})</button>` : ''}
      <button class="btn" data-nav data-buy="${h.id}:flask" ${L.coins < P.flask ? 'disabled' : ''}>+1 flask (${P.flask})</button>
      <button class="btn" data-nav data-buy="${h.id}:ember" ${L.coins < P.ember ? 'disabled' : ''}>Extra blessing (${P.ember})</button>
    </div>
    ${ups ? `<h3>Blessings</h3><div class="chips">${ups}</div>` : ''}
    <div class="row" style="margin-top:14px;justify-content:flex-end">
      <button class="btn ${h.ready ? '' : 'primary'}" data-nav data-ready="${h.id}" ${!h.ready && (h.points || h.offer.length) ? 'title="You can still spend points and choose a blessing"' : ''}>${h.ready ? 'Not ready' : 'Ready'}</button>
    </div>
  </div>`;
}

function title() {
  const room = new URLSearchParams(location.search).get('room') || '';
  show(`<div class="screen title">
    <h1 class="logo">KINGFALL</h1>
    <p class="tag">The king is dead. His knights, his beasts and his gods are not.</p>
    <div class="row center"><input class="field" id="name" data-nav maxlength="16" placeholder="Your name" value="${esc(ME.saved.name || '')}"></div>
    <div class="row center" style="margin-top:14px">
      <button class="btn primary" id="create" data-nav ${room ? '' : 'data-autofocus'}>Create a room</button>
      <span class="hint">or</span>
      <input class="field code" id="code" data-nav maxlength="4" placeholder="CODE" value="${esc(room)}">
      <button class="btn" id="join" data-nav ${room ? 'data-autofocus' : ''}>Join</button>
    </div>
    <div class="err">${esc(S.error)}</div>
    <div class="controls">
      <div><b>Keyboard & mouse</b></div><div><b>Controller</b></div>
      <div><kbd>WASD</kbd> move · mouse aim</div><div>Left stick move · right stick aim</div>
      <div><kbd>LMB</kbd> light · hold <kbd>RMB</kbd> heavy</div><div><kbd>RB</kbd> light · hold <kbd>RT</kbd> heavy</div>
      <div><kbd>Space</kbd> roll · <kbd>Shift</kbd> block</div><div><kbd>B</kbd> roll · <kbd>LB</kbd> block</div>
      <div><kbd>Q</kbd> special · <kbd>R</kbd> flask</div><div><kbd>Y</kbd> special · <kbd>X</kbd> flask</div>
      <div><kbd>E</kbd> revive · <kbd>Tab</kbd> lock on</div><div><kbd>A</kbd> revive · <kbd>R3</kbd> lock on</div>
    </div>
  </div>`);
  const name = () => { const n = $('#name').value.trim().slice(0, 16); ME.saved.name = n; ME.save(); return n; };
  $('#create').onclick = () => { unlock(); name(); connect({ create: 1, debug: DEBUG ? 1 : 0 }); };
  $('#join').onclick = () => {
    unlock(); name();
    const code = $('#code').value.trim().toUpperCase();
    if (code.length !== 4) { S.error = 'Room codes are four letters.'; return title(); }
    connect({ room: code });
  };
  $('#code').onkeydown = e => { if (e.key === 'Enter') $('#join').click(); };
  $('#name').onkeydown = e => { if (e.key === 'Enter') (room ? $('#join') : $('#create')).click(); };
}

function lobby() {
  const L = S.lobby, data = S.data;
  if (!L || !data) return;
  const host = L.host === S.me, mine = myHeroes();
  const link = `${location.origin}/games/kingfall?room=${S.code}`;
  const over = L.state === 'over';
  const el = show(`<div class="screen">
    ${over ? `<h2 style="color:${L.result === 'won' ? 'var(--gold2)' : '#c03030'}">${L.result === 'won' ? 'The run is won' : 'The party has fallen'}</h2>` : ''}
    <div class="row" style="justify-content:space-between">
      <div><h3 style="margin-top:0">Room</h3><div class="code-big">${esc(S.code)}</div></div>
      <button class="btn" id="copy" data-nav>Copy invite link</button>
    </div>
    <h3>Heroes (${L.heroes.length}/4)</h3>
    <div class="heroes" id="heroes"></div>
    ${L.heroes.length < 4 ? `<div class="slot-empty">${mine.some(h => h.slot === 0) ? '' : '<button class="btn" id="joinkb" data-nav>Join with keyboard & mouse</button><br>'}
      Press <kbd>Start</kbd> on a controller to add a couch player · friends join with the code</div>` : ''}
    <div class="row" style="margin-top:20px;justify-content:space-between">
      <button class="btn" id="leave" data-nav data-back>Leave</button>
      ${host ? `<button class="btn primary" id="start" data-nav ${L.heroes.length ? 'data-autofocus' : 'disabled'}>${over ? 'Fight again' : 'Begin'}</button>`
    : '<span class="hint">Waiting for the host to begin…</span>'}
    </div>
    <div class="err">${esc(S.error)}</div>
  </div>`);
  const list = $('#heroes', el);
  for (const h of L.heroes) {
    const own = h.conn === S.me, W = data.weapons[h.weapon];
    const row = document.createElement('div');
    row.className = 'hero'; row.style.setProperty('--c', data.colours[h.colour]);
    row.appendChild(portrait(h, W));
    const info = document.createElement('div');
    info.innerHTML = `<div class="name">${esc(h.name)}</div>
      <div class="sub">${own ? (h.slot === 0 ? 'Keyboard & mouse' : padName('pad' + (h.slot - 1))) : 'Online'} · ${esc(LOOK_NAMES[h.look])} · ${esc(W.name)}</div>
      ${own && !over ? `<div style="margin-top:6px"><span class="pick"><button class="btn" data-nav data-lr data-look="${h.id}">◀ ${esc(LOOK_NAMES[h.look])} ▶</button></span>
        <span class="pick"><button class="btn" data-nav data-lr data-weap="${h.id}">◀ ${esc(W.name)} ▶</button></span></div>
        <div class="hint" style="margin-top:4px">${esc(W.blurb || '')}</div>` : ''}`;
    row.appendChild(info);
    const right = document.createElement('div');
    if (own && !over) right.innerHTML = `<button class="btn" data-nav data-drop="${h.id}">Remove</button>`;
    row.appendChild(right);
    list.appendChild(row);
  }
  el.querySelectorAll('[data-look]').forEach(b => {
    const cycle = dir => {
      const h = L.heroes.find(x => x.id === +b.dataset.look);
      const next = LOOKS[(LOOKS.indexOf(h.look) + dir + 4) % 4];
      if (h.slot === 0) { ME.saved.look = next; ME.save(); }
      net.send({ t: 'set', h: h.id, look: next });
    };
    b.onclick = () => cycle(1);
    b.addEventListener('lr', e => cycle(e.detail));
  });
  el.querySelectorAll('[data-weap]').forEach(b => {
    const ids = Object.keys(data.weapons);
    const cycle = dir => {
      const h = L.heroes.find(x => x.id === +b.dataset.weap);
      const next = ids[(ids.indexOf(h.weapon) + dir + ids.length) % ids.length];
      if (h.slot === 0) { ME.saved.weapon = next; ME.save(); }
      net.send({ t: 'set', h: h.id, weapon: next });
    };
    b.onclick = () => cycle(1);
    b.addEventListener('lr', e => cycle(e.detail));
  });
  el.querySelectorAll('[data-drop]').forEach(b => { b.onclick = () => net.send({ t: 'drop', h: +b.dataset.drop }); });
  $('#copy').onclick = () => { navigator.clipboard && navigator.clipboard.writeText(link); $('#copy').textContent = 'Copied'; };
  if ($('#joinkb')) $('#joinkb').onclick = () => addHero(0);
  if ($('#start')) $('#start').onclick = start;
  $('#leave').onclick = () => { net.sock.close(); S.screen = 'title'; S.lobby = null; history.replaceState(null, '', location.pathname); render(); };
  if (host && !mine.length && !over && L.heroes.length === 0) setTimeout(() => S.lobby && !myHeroes().length && addHero(0), 50);
}

// ------------------------------------------------------------------ the connection
function connect(hello) {
  S.error = '';
  if (net) net.sock.close();
  net = new Net(VERSION, onMessage);
  net.status = s => { const el = document.getElementById('status'); el.hidden = !s || s === 'Connecting…'; el.textContent = s; };
  net.connect(hello);
}

function onMessage(m) {
  switch (m.t) {
    case 'reload': location.reload(); return;
    case 'error': S.error = m.msg; net.sock.stop(); S.screen = 'title'; render(); return;
    case 'replaced': S.error = 'This room was opened in another tab.'; net.sock.stop(); S.screen = 'title'; render(); return;
    case 'welcome':
      document.getElementById('status').hidden = true;
      S.me = m.you; S.code = m.code; S.data = m.data;
      S.data.colours = ['#a83030', '#3a5aa8', '#c8a040', '#3a7a5a'];
      history.replaceState(null, '', `${location.pathname}?room=${m.code}`);
      S.screen = 'lobby';
      return;
    case 'lobby': {
      const prev = S.lobby;
      S.lobby = m;
      if (S.scene && m.state !== 'fight') endFight();
      else if (!S.scene && !S.starting && m.state !== 'fight') { S.screen = 'lobby'; if (!prev || JSON.stringify(prev) !== JSON.stringify(m)) render(); }
      return;
    }
    case 'fight': startFight(m); return;
  }
  if (S.scene) S.scene.onMsg(m);
  else if (S.starting) S.pending.push(m);
}

function startFight(m) {
  if (S.scene || S.starting) return;
  hide();
  S.fightMsg = m;
  S.starting = true; S.pending = [];
  const heroes = S.lobby.heroes;
  const boss = S.data.bosses[m.boss];
  buildHud(boss, heroes, S.data.colours, heroes.filter(h => h.conn === S.me).map(h => h.id));
  game.scene.start('fight', {
    net, input, data: S.data, fight: m, heroes, me: S.me, zoom,
    onReady: sc => { S.scene = sc; S.starting = false; for (const p of S.pending) sc.onMsg(p); S.pending = []; },
    onFrame: sc => updateHud(sc),
    onBanner: kind => banner(kind),
  });
}

function endFight() {
  const sc = S.scene;
  setTimeout(() => {
    if (S.scene !== sc) return;
    game.scene.stop('fight');
    S.scene = null;
    hideHud();
    S.screen = 'lobby';
    render();
  }, 600);
}

requestAnimationFrame(frame);
if (DEBUG) window.kf = { S, input, win: () => net.send({ t: 'debugwin' }), get net() { return net; } };
