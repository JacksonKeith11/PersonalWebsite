// Kingfall: boot, the menus, and the connection to the room. docs/kingfall.md describes the game.
import { setAtlas } from './rig.js?v=1';
import { Input, slotOf, padName } from './input.js?v=1';
import { Net, ME } from './net.js?v=1';
import { FightScene } from './fight.js?v=1';
import { show, hide, navFrame, esc, portrait, setAtlasImage, LOOK_NAMES, buildHud, updateHud, banner, hideHud, $ } from './ui.js?v=1';
import { unlock, sfx } from './audio.js?v=1';

const VERSION = new URL(import.meta.url).searchParams.get('v');
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
  net.send({ t: 'add', slot, name, look, weapon: 'sword' });
  sfx.ui();
}

function start() { if (S.lobby && S.lobby.heroes.length) net.send({ t: 'start' }); }

// ------------------------------------------------------------------ screens
function render() {
  if (S.scene) return;
  if (S.screen === 'title') return title();
  if (S.screen === 'lobby') return lobby();
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
  $('#create').onclick = () => { unlock(); name(); connect({ create: 1 }); };
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
      ${own && !over ? `<div style="margin-top:6px"><span class="pick"><button class="btn" data-nav data-lr data-look="${h.id}">◀ ${esc(LOOK_NAMES[h.look])} ▶</button></span></div>` : ''}`;
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
