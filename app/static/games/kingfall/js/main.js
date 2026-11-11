// Kingfall: boot, the menus, and the connection to the room. docs/kingfall.md describes the game.
import { setAtlas } from './rig.js?v=33';
import { Input, slotOf, padName, deviceOfSlot, glyph, firstPadFamily } from './input.js?v=33';
import { icon } from './icons.js?v=33';
import { Net, ME } from './net.js?v=33';
import { FightScene } from './fight.js?v=33';
import { show, hide, openMenu, closeMenu, navFrame, setOwners, esc, portrait, setAtlasImage, LOOK_NAMES, buildHud, updateHud, banner, hideHud, $ } from './ui.js?v=33';
import { unlock, sfx, setVolume } from './audio.js?v=33';
import { music } from './music.js?v=33';

const VERSION = new URL(import.meta.url).searchParams.get('v');
const DEBUG = new URLSearchParams(location.search).has('debug');
const ONLY = DEBUG ? new URLSearchParams(location.search).get('boss') : null;  // ?debug&boss=mire starts the run there  // ?debug: window.kf, and the host may skip a fight
const BASE = '/static/games/kingfall/';
const LOOKS = ['knight', 'pilgrim', 'hunter', 'sellsword'];

const S = { me: null, code: null, data: null, lobby: null, scene: null, fightMsg: null, screen: 'title', error: '', p1pad: null };
// S.p1pad: the controller player one uses alongside the keyboard (the first controller to press Start
// while player one has none). Every other controller that presses Start gets a couch hero of its own.
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
  type: Phaser.AUTO, parent: 'game', width: 640, height: 360, zoom: 1, pixelArt: true, roundPixels: false,
  backgroundColor: '#0c0a10', scene: [Boot, FightScene], scale: { mode: Phaser.Scale.NONE },
  input: { mouse: { preventDefaultWheel: false } }, banner: false,
});
// fill the window at that zoom (wider screens see a little more of the arena)
function fit() {
  // The canvas is at screen resolution and the fight's camera magnifies by z: sprites stay crisp pixel
  // art, while drawn effects (slashes, bolts, ground marks) and rotated parts are smooth.
  const z = zoom();
  game.scale.resize(Math.min(800, Math.ceil(innerWidth / z)) * z, Math.min(450, Math.ceil(innerHeight / z)) * z);
  game.scale.setZoom(1);
}
addEventListener('resize', fit);
fit();

// ------------------------------------------------------------------ the loop for menus and joining
// A broken script: say so on screen (with a way out) and tell the server, which logs it. Each distinct
// message once. The menu loop and the fight's frame catch their own errors and come here, so one bad
// frame doesn't freeze the page.
const reported = new Set();
function oops(e) {
  const msg = String((e && e.message) || e).slice(0, 300), at = String((e && e.stack) || '').split('\n').slice(0, 4).join(' | ');
  console.error(e);
  if (reported.has(msg) || reported.size >= 5) return;
  reported.add(msg);
  try { if (net) net.send({ t: 'clienterr', msg, at }); } catch (_) { /* not connected */ }
  const el = document.getElementById('oops');
  el.innerHTML = `<b>Something broke on this screen.</b> <span>${esc(msg)}</span> <span>Reload, then press Join to get back into the room.</span> <button class="btn" id="oops-reload">Reload</button>`;
  el.hidden = false;
  document.getElementById('oops-reload').onclick = () => location.reload();
}
addEventListener('error', e => oops(e.error || e.message));
addEventListener('unhandledrejection', e => oops(e.reason));

function frame() {
  try { frameBody(); } catch (e) { oops(e); }
  requestAnimationFrame(frame);
}
function frameBody() {
  input.poll();
  // The menu during a run: Esc (Start on a controller) opens it over a fight or the Bonfire; Esc, B or
  // Start closes it. While it's up it takes the keys, and this browser's heroes stand idle.
  const inRun = !!S.lobby && S.screen === 'lobby' && (S.lobby.state === 'fight' || S.lobby.state === 'bonfire');
  const was = S.menu, start = Object.values(input.pads).some(d => d.pressed('start'));
  if (!S.scene || S.menu) navFrame(input);
  if (was && S.menu && (start || !inRun)) closeRunMenu();
  else if (!was && inRun && (input.kb.pressed('back') || start)) runMenu();
  const bound = bindP1();
  if (S.screen === 'lobby') lobbyDevices(bound);
  if (S.scene && !S.menu) strayPads();
  setVolume(ME.saved.sfx ?? 0.6); music.setVolume(ME.saved.music ?? 0.5);
if (DEBUG) window.kf = { S, input, win: () => net.send({ t: 'debugwin' }), safe: () => net.send({ t: 'debugsafe' }), get net() { return net; } };
}

// ------------------------------------------------------------------ the menu during a run
function closeRunMenu() { S.menu = false; closeMenu(); }

function leaveRoom() {
  closeRunMenu();
  if (S.scene) { game.scene.stop('fight'); S.scene = null; hideHud(); }
  S.starting = false;
  net.sock.close(); S.screen = 'title'; S.lobby = null;
  history.replaceState(null, '', location.pathname);
  music.play('bonfire');
  render();
}

// `ask`: 'quit' or 'leave' shows that question instead of the menu
function runMenu(ask = null) {
  const host = S.lobby.host === S.me, fighting = S.lobby.state === 'fight';
  S.menu = true;
  const el = openMenu(ask === 'quit' ? `<div class="screen menu">
      <h2>Quit the run?</h2>
      <p class="hint">Everyone goes back to the lobby. ${S.lobby.stage > 0 ? 'The run stays saved at its last Bonfire, and you can resume it from there.' : 'This run has not reached a Bonfire, so nothing of it is saved.'}</p>
      <div class="row" style="justify-content:flex-end"><button class="btn" id="m-back" data-nav data-back data-autofocus>Keep playing</button><button class="btn primary" id="m-yes" data-nav>Quit the run</button></div>
    </div>` : ask === 'leave' ? `<div class="screen menu">
      <h2>Leave the room?</h2>
      <p class="hint">${S.lobby.heroes.length > myHeroes().length ? 'The others carry on; your hero stays where they stand.' : 'The room closes once it is empty; a run saved at a Bonfire can be resumed later.'}</p>
      <div class="row" style="justify-content:flex-end"><button class="btn" id="m-back" data-nav data-back data-autofocus>Stay</button><button class="btn primary" id="m-yes" data-nav>Leave the room</button></div>
    </div>` : `<div class="screen menu">
      <h2>Menu</h2>
      ${fighting ? '<p class="hint">The fight carries on while this is open.</p>' : ''}
      <div class="row" style="gap:18px;margin:6px 0 16px">
        <label class="hint">Sound <input type="range" id="m-sfx" min="0" max="1" step="0.05" value="${ME.saved.sfx ?? 0.6}" data-nav></label>
        <label class="hint">Music <input type="range" id="m-mus" min="0" max="1" step="0.05" value="${ME.saved.music ?? 0.5}" data-nav></label>
      </div>
      <div class="menu-list">
        <button class="btn primary" id="m-resume" data-nav data-back data-autofocus>Back to the game</button>
        ${host ? '<button class="btn" id="m-quit" data-nav>Quit the run</button>' : '<span class="hint">Only the host can quit the run for everyone.</span>'}
        <button class="btn" id="m-leave" data-nav>Leave the room</button>
      </div>
    </div>`);
  const on = (id, fn) => { const b = $(id, el); if (b) b.onclick = fn; };
  on('#m-resume', closeRunMenu);
  on('#m-quit', () => runMenu('quit'));
  on('#m-leave', () => runMenu('leave'));
  on('#m-back', () => runMenu());
  on('#m-yes', () => { if (ask === 'quit') { net.send({ t: 'quit' }); closeRunMenu(); } else leaveRoom(); });
  if ($('#m-sfx', el)) $('#m-sfx', el).oninput = e => { ME.saved.sfx = +e.target.value; ME.save(); setVolume(+e.target.value); };
  if ($('#m-mus', el)) $('#m-mus', el).oninput = e => { ME.saved.music = +e.target.value; ME.save(); music.setVolume(+e.target.value); };
}

// Player one takes the first controller used (any button or the stick) that has no hero of its own,
// while it has none: one player can pick up a controller and play. More controllers press Start for a
// couch hero each; "Split off" in the lobby gives player one's controller its own hero instead.
// When player one first appears, a controller used more recently than the keyboard and mouse (the one
// that pressed Create or Join) is taken as theirs at once, so a friend's Start can't take player one.
function bindP1() {
  const p1 = myHeroes().find(h => h.slot === 0);
  if (S.p1pad && (!p1 || !input.pads[S.p1pad])) { S.p1pad = null; if (!S.scene) render(); }   // unplugged, or player one gone
  if (p1 && !S.p1pad && S.p1seen !== p1.id) {
    S.p1seen = p1.id;
    const last = Object.values(input.pads).filter(d => !heroOf(d.id)).sort((x, y) => y.lastUsed - x.lastUsed)[0];
    if (last && last.lastUsed > input.kb.lastUsed) { S.p1pad = last.id; if (!S.scene && !S.menu) render(); return last.id; }
  }
  if (!p1 || S.p1pad) return null;
  for (const d of Object.values(input.pads)) {
    if (heroOf(d.id)) continue;
    if (Object.keys(d.now).some(b => d.pressed(b)) || Math.hypot(d.move.x, d.move.y) > 0.5) {
      S.p1pad = d.id;
      if (!S.scene && !S.menu) render();
      return d.id;
    }
  }
  return null;
}

// In a fight, a controller with no hero here does nothing: say so, rather than leave its player wondering.
let toastTimer = 0;
function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg; el.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { el.hidden = true; }, 3500);
}
function strayPads() {
  for (const d of Object.values(input.pads)) {
    if (heroOf(d.id) || !Object.keys(d.now).some(b => b !== 'start' && d.pressed(b))) continue;
    toast(`${padName(d.id)} has no hero in this fight. In the lobby, press Start on it to join` + (S.p1pad ? `, or Split off ${padName(S.p1pad)}.` : '.'));
  }
}

function lobbyDevices(bound) {
  for (const d of input.devices()) {
    if (d.id === 'kb' || d.id === bound || !d.pressed('start')) continue;   // the press that bound a controller does nothing more
    const typing = document.activeElement && document.activeElement.tagName === 'INPUT';
    if (heroOf(d.id)) { if (S.lobby.host === S.me && !typing) start(); }
    else addHero(slotOf(d.id));
  }
}

const myHeroes = () => (S.lobby ? S.lobby.heroes.filter(h => h.conn === S.me) : []);
// the hero a device drives on this browser: the keyboard and player one's controller drive player one,
// any other controller the hero of its slot (or none)
function heroOf(devId) {
  const mine = myHeroes();
  if (devId === 'kb' || devId === S.p1pad) return mine.find(h => h.slot === 0) || null;
  return mine.find(h => h.slot === slotOf(devId)) || null;
}
// whose menu cursor a device steers (see the top of the navigation code in js/ui.js)
setOwners(devId => {
  const mine = myHeroes(), main = mine.find(h => h.slot === 0) || (mine.length === 1 ? mine[0] : null);
  const h = heroOf(devId);
  if (!h || h === main) return { key: 'main', hero: main ? main.id : null };
  return { key: String(h.id), hero: h.id, colour: S.data.colours[h.colour] };
});

function addHero(slot) {
  if (!S.lobby || S.lobby.heroes.length >= 4) return;
  const used = new Set(S.lobby.heroes.map(h => h.look));
  const look = (slot === 0 && ME.saved.look) || LOOKS.find(l => !used.has(l)) || LOOKS[slot % 4];
  const name = slot === 0 ? (ME.saved.name || 'Wanderer') : `${ME.saved.name || 'Wanderer'} ${slot + 1}`;
  net.send({ t: 'add', slot, name, look, weapon: (slot === 0 && ME.saved.weapon) || 'sword', skill: (slot === 0 && ME.saved.skill) || undefined });
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

// How many blessings of each Vow a hero holds: {ember: 2, ...}
const vowCounts = h => h.ups.reduce((n, [u]) => { const v = S.data.upgrades[u].vow; if (v) n[v] = (n[v] || 0) + 1; return n; }, {});
// a blessing's emblem: its Vow's, else its weapon's for a Weapon Art, else a crown (passives, pacts)
const emblem = U => icon(U.vow || (U.weapon ? U.weapon : U.pact ? 'blood' : 'crown'));
// cards deal in with an animation only when the offer is new, not on every redraw of the Bonfire
const dealt = {};
function dealClass(key, sig) { if (dealt[key] === sig) return ''; dealt[key] = sig; return ' deal'; }

function upgradeCard(uid, rarity, i, h, deal) {
  const U = S.data.upgrades[uid], V = U.vow ? S.data.vows[U.vow] : null, vc = vowCounts(h);
  const held = U.slot && h.ups.find(([x]) => S.data.upgrades[x].slot === U.slot);
  const kind = U.duo ? 'Duo' : U.pact ? 'Pact' : U.weapon ? 'Weapon Art' : U.slot ? SLOT_NAME[U.slot] : 'Passive';
  const col = V ? V.colour : '#c8a040';
  // a Duo shows the two Vows it joins; a Vow blessing how many of that Vow you hold already
  const foot = U.duo ? `<span class="up-duo">${U.needs.map(v => `<span style="--v:${S.data.vows[v].colour}">${icon(v)} ${esc(S.data.vows[v].name)}</span>`).join('<em>+</em>')}</span>`
    : V ? `<span class="up-vow">${vc[U.vow] ? `You hold ${vc[U.vow]} ${esc(V.name)}` : `First of ${esc(V.name)}`} · <i>${esc(V.blurb)}</i></span>` : '';
  return `<button class="card-up r-${rarity}${deal}" data-nav data-pick="${h.id}:${i}" style="--v:${col};--r:${RARE_COL[rarity]};--i:${i}">
    <span class="up-head"><span class="up-em">${emblem(U)}</span><span class="up-top"><b>${esc(U.name)}</b><i>${rarity}</i></span></span>
    <span class="up-kind">${V ? esc(V.name) + ' · ' : ''}${kind}</span>
    <span class="up-text">${esc(U.text[rarity])}</span>
    ${foot}
    ${held ? `<span class="up-rep">Replaces ${esc(S.data.upgrades[held[0]].name)}</span>` : ''}
  </button>`;
}

// A skill on offer. With a free slot the card itself learns it; with both full it holds a button for
// each skill it could replace.
function skillCard(id, i, h, deal) {
  const K = S.data.skills[id], full = h.skills.length >= S.data.max_skills;
  const body = `<span class="up-head"><span class="up-em">${icon(id)}</span><span class="up-top"><b>${esc(K.name)}</b></span></span>
    <span class="up-kind">Skill · ${K.cd}s cooldown</span><span class="up-text">${esc(K.text)}</span>`;
  if (!full) return `<button class="card-up skill${deal}" data-nav data-learn="${h.id}:${i}" style="--v:${K.col};--r:${K.col};--i:${i}">${body}</button>`;
  return `<div class="card-up skill${deal}" style="--v:${K.col};--r:${K.col};--i:${i}">${body}<span class="sk-rep">${h.skills.map((old, at) =>
    `<button class="btn" data-nav data-learn="${h.id}:${i}:${at}">Replace ${esc(S.data.skills[old].name)}</button>`).join('')}</span></div>`;
}

// The Vows a hero holds, and the Duos within reach: Sephiria-style, so a build's direction is visible.
// Each Vow shows its emblem and count; a Duo lights each half you hold (both halves: it can be offered).
function vowRow(h) {
  const D = S.data, vc = vowCounts(h);
  const held = Object.keys(D.vows).filter(v => vc[v]);
  if (!held.length) return '';
  const owned = new Set(h.ups.map(([u]) => u));
  const duos = Object.entries(D.upgrades).filter(([id, U]) => U.duo && !owned.has(id) && U.needs.some(v => vc[v]));
  return `<h3>Vows</h3><div class="vows">${held.map(v => `<span class="vow" style="--v:${D.vows[v].colour}" data-nav data-chip="${h.id}:v:${v}"
      data-tip-h="${esc(D.vows[v].name)}" data-tip-k="${vc[v]} held" data-tip="${esc(D.vows[v].blurb)}">${icon(v)}<b>${vc[v]}</b></span>`).join('')}</div>
    ${duos.length ? `<div class="duos">${duos.map(([id, U]) => `<span class="duo ${U.needs.every(v => vc[v]) ? 'ready' : ''}" data-nav data-chip="${h.id}:d:${id}"
      data-tip-h="${esc(U.name)}" data-tip-k="Duo · ${U.needs.map(v => esc(D.vows[v].name)).join(' + ')}" data-tip="${esc(U.text.common)}">${U.needs.map(v =>
      `<span class="${vc[v] ? 'on' : ''}" style="--v:${D.vows[v].colour}">${icon(v)}</span>`).join('')} ${esc(U.name)}</span>`).join('')}</div>` : ''}`;
}

function bonfire() {
  music.play('bonfire');
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
  // picking a blessing: the chosen card lifts and glows, the others fall away, then it's sent
  el.querySelectorAll('[data-pick]').forEach(b => b.onclick = () => {
    if (b.classList.contains('chosen')) return;
    const [h, i] = b.dataset.pick.split(':').map(Number);
    b.classList.add('chosen'); b.parentElement.querySelectorAll('.card-up').forEach(c => c !== b && c.classList.add('gone'));
    sfx.sting(0); setTimeout(() => send('pick', h, { i }), 280);
  });
  el.querySelectorAll('[data-learn]').forEach(b => b.onclick = () => {
    const [h, i, at] = b.dataset.learn.split(':');
    send('learn', +h, i === 'skip' ? { skip: 1 } : { i: +i, at: at === undefined ? undefined : +at }); sfx.ui();
  });
  el.querySelectorAll('[data-attr]').forEach(b => b.onclick = () => { const [h, a] = b.dataset.attr.split(':'); send('attr', +h, { a }); });
  el.querySelectorAll('[data-buy]').forEach(b => b.onclick = () => { const [h, item] = b.dataset.buy.split(':'); send('buy', +h, { item }); });
  el.querySelectorAll('[data-ready]').forEach(b => b.onclick = () => { const h = L.heroes.find(x => x.id === +b.dataset.ready); send('ready', h.id, { on: !h.ready }); });
}

function panel(h) {
  const L = S.lobby, D = S.data, W = D.weapons[h.weapon], P = L.prices;
  const dev = deviceOfSlot(h.slot);
  // what the hero already has: hover a chip (or move onto it with a controller) to read what it does
  const known = h.skills.map((id, i) => `<span class="chip" data-nav data-chip="${h.id}:s:${id}" style="--r:${D.skills[id].col}" data-tip-h="${esc(D.skills[id].name)}"
    data-tip-k="Skill · ${D.skills[id].cd}s cooldown" data-tip="${esc(D.skills[id].text)}">${glyph(dev, i ? 'skill2' : 'skill1')} ${icon(id)} ${esc(D.skills[id].name)} · ${D.skills[id].cd}s</span>`).join('');
  const ups = h.ups.map(([u, r]) => {
    const U = D.upgrades[u], V = U.vow ? D.vows[U.vow] : null;
    const kind = U.duo ? 'Duo' : U.pact ? 'Pact' : U.weapon ? 'Weapon Art' : U.slot ? SLOT_NAME[U.slot] : 'Passive';
    return `<span class="chip" data-nav data-chip="${h.id}:u:${u}" style="--r:${RARE_COL[r]};--v:${V ? V.colour : 'var(--gold)'}" data-tip-h="${esc(U.name)}" data-tip-k="${V ? esc(V.name) + ' · ' : ''}${kind} · ${r}"
      data-tip="${esc(U.text[r])}">${V || U.weapon ? `<span class="em">${emblem(U)}</span>` : ''}${esc(U.name)}</span>`; }).join('');
  return `<div class="panel" data-owner="${h.id}" style="--c:${D.colours[h.colour]}">
    <div class="row"><b class="pname">${esc(h.name)}</b><span class="hint">Level ${h.level} · ${esc(W.name)} · ${h.mhp} health · ${h.maxflasks} flasks</span></div>
    ${h.points ? `<h3>Level up: ${h.points} point${h.points > 1 ? 's' : ''}</h3><div class="attrs">${D.attrs.map(([k, name, text]) =>
      `<button class="btn attr" data-nav data-attr="${h.id}:${k}"><b>${name} ${h.attrs[k]}</b><small>${text}</small></button>`).join('')}</div>` : ''}
    ${h.offer.length ? `<h3>Choose a blessing${h.picks > 1 ? ` (${h.picks})` : ''}</h3><div class="cards-up">${(d => h.offer.map(([u, r], i) => upgradeCard(u, r, i, h, d)).join(''))(dealClass('up' + h.id, JSON.stringify(h.offer)))}</div>` : ''}
    ${h.skill_offer.length ? `<h3>Learn a skill${h.skills.length >= D.max_skills ? ' (you carry two: one must go)' : ''}</h3>
      <div class="cards-up">${(d => h.skill_offer.map((id, i) => skillCard(id, i, h, d)).join(''))(dealClass('sk' + h.id, JSON.stringify(h.skill_offer)))}</div>
      <div class="row" style="margin-top:8px"><button class="btn" data-nav data-learn="${h.id}:skip">Pass</button>
        <span class="hint">Skills work with any weapon and come back on a cooldown.</span></div>` : ''}
    <h3>Shop</h3><div class="row">
      ${h.offer.length ? `<button class="btn" data-nav data-buy="${h.id}:reroll" ${L.coins < P.reroll ? 'disabled' : ''}>Reroll (${P.reroll})</button>` : ''}
      ${h.skill_offer.length ? `<button class="btn" data-nav data-buy="${h.id}:skills" ${L.coins < P.skills ? 'disabled' : ''}>Other skills (${P.skills})</button>` : ''}
      <button class="btn" data-nav data-buy="${h.id}:flask" ${L.coins < P.flask ? 'disabled' : ''}>+1 flask (${P.flask})</button>
      <button class="btn" data-nav data-buy="${h.id}:ember" ${L.coins < P.ember ? 'disabled' : ''}>Extra blessing (${P.ember})</button>
    </div>
    ${known ? `<h3>Skills</h3><div class="chips">${known}</div>` : ''}
    ${vowRow(h)}
    ${ups ? `<h3>Blessings</h3><div class="chips">${ups}</div>` : ''}
    <div class="row" style="margin-top:14px;justify-content:flex-end">
      <button class="btn ${h.ready ? '' : 'primary'}" data-nav data-ready="${h.id}" ${!h.ready && (h.points || h.offer.length || h.skill_offer.length) ? 'title="You can still spend points, choose a blessing and learn a skill"' : ''}>${h.ready ? 'Not ready' : 'Ready'}</button>
    </div>
  </div>`;
}

// The controls, with the keys and the buttons of the controller plugged in (Xbox labels when there's none)
function controlsTable() {
  const f = firstPadFamily(), pid = f === 'xbox' ? null : Object.keys(input.pads)[0];
  const k = a => glyph('kb', a), p = a => pid ? glyph(pid, a) : glyph('xbox-pad', a);
  return `<div><b>Keyboard & mouse</b></div><div><b>Controller</b></div>
      <div><kbd class="key">WASD</kbd> move · mouse aim</div><div>Left stick move · right stick aim</div>
      <div>${k('light')} light · hold ${k('heavy')} heavy</div><div>${p('light')} light · hold ${p('heavy')} heavy</div>
      <div>${k('dodge')} roll · ${k('block')} block (press just before a hit to parry)</div><div>${p('dodge')} roll · ${p('block')} block</div>
      <div>${k('special')} special · ${k('flask')} flask</div><div>${p('special')} special · ${p('flask')} flask</div>
      <div>hold ${k('revive')} to revive · ${k('lock')} lock on</div><div>hold ${p('revive')} by a fallen ally to revive · ${p('lock')} lock on</div>
      <div>${k('back')} menu (quit the run, volume)</div><div>${p('start')} menu</div>
      <div>${k('skill1')} ${k('skill2')} skills (or <kbd class="key">1</kbd> <kbd class="key">2</kbd>)</div><div>${p('skill1')} · ${p('skill2')} skills</div>`;
}

// The title's backdrop: the four heroes side by side before a fire, embers rising past them
function titleArt() {
  const el = $('.screen.title');
  if (!el || $('.lineup', el)) return;
  const row = document.createElement('div');
  row.className = 'lineup';
  const HEROES = [['pilgrim', 1, { art: 'staff' }], ['knight', 0, { art: 'sword', offhand: 'shield' }], ['sellsword', 2, { art: 'greatsword' }], ['hunter', 3, { art: 'bow' }]];
  try { for (const [look, colour, W] of HEROES) row.appendChild(portrait({ look, colour }, W, 120)); } catch (e) { return; }   // the art isn't loaded yet
  const embers = document.createElement('div');
  embers.className = 'embers';
  embers.innerHTML = Array.from({ length: 22 }, () => `<i style="left:${Math.random() * 100}%;animation-delay:${(Math.random() * 6).toFixed(2)}s;animation-duration:${(4 + Math.random() * 4).toFixed(2)}s"></i>`).join('');
  el.prepend(embers);
  $('.tag', el).after(row);
}

function title() {
  const room = new URLSearchParams(location.search).get('room') || '';
  show(`<div class="screen title">
    <div class="crest">${icon('crown')}</div>
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
    <div class="row center" style="gap:18px;margin-top:6px">
      <label class="hint">Sound <input type="range" id="vsfx" min="0" max="1" step="0.05" value="${ME.saved.sfx ?? 0.6}" data-nav></label>
      <label class="hint">Music <input type="range" id="vmus" min="0" max="1" step="0.05" value="${ME.saved.music ?? 0.5}" data-nav></label>
    </div>
    <div class="controls">${controlsTable()}</div>
  </div>`);
  titleArt();
  const name = () => { const n = $('#name').value.trim().slice(0, 16); ME.saved.name = n; ME.save(); return n; };
  $('#create').onclick = () => { unlock(); name(); connect({ create: 1, debug: DEBUG ? 1 : 0 }); };
  $('#join').onclick = () => {
    unlock(); name();
    const code = $('#code').value.trim().toUpperCase();
    if (code.length !== 4) { S.error = 'Room codes are four letters.'; return title(); }
    connect({ room: code });
  };
  $('#code').onkeydown = e => { if (e.key === 'Enter') $('#join').click(); };
  $('#vsfx').oninput = e => { ME.saved.sfx = +e.target.value; ME.save(); setVolume(+e.target.value); };
  $('#vmus').oninput = e => { ME.saved.music = +e.target.value; ME.save(); music.setVolume(+e.target.value); };
  $('#name').onkeydown = e => { if (e.key === 'Enter') (room ? $('#join') : $('#create')).click(); };
}

// Which way a click on a "◀ name ▶" picker goes: back on its left half, on on its right. A press from
// a controller or the keyboard has no place, and goes on (left and right on the stick do both ways).
const side = (e, b) => { if (!e.clientX && !e.clientY) return 1; const r = b.getBoundingClientRect(); return e.clientX < r.left + r.width / 2 ? -1 : 1; };

function lobby() {
  const L = S.lobby, data = S.data;
  if (!L || !data) return;
  const host = L.host === S.me, mine = myHeroes();
  const link = `${location.origin}/games/kingfall?room=${S.code}`;
  const over = L.state === 'over';
  const el = show(`<div class="screen">
    ${over ? `<h2 style="color:${L.result === 'won' ? 'var(--gold2)' : L.result === 'quit' ? 'var(--dim)' : '#c03030'}">${L.result === 'won' ? 'The run is won' : L.result === 'quit' ? 'The run was left' : 'The party has fallen'}</h2>` : ''}
    ${over ? '<div class="hint" style="margin:-6px 0 10px">Change your look, weapon or starting skill below before you fight again.</div>' : ''}
    <div class="row" style="justify-content:space-between">
      <div><h3 style="margin-top:0">Room</h3><div class="code-big">${esc(S.code)}</div></div>
      <button class="btn" id="copy" data-nav>Copy invite link</button>
    </div>
    <h3>Heroes (${L.heroes.length}/4)</h3>
    <div class="heroes" id="heroes"></div>
    ${L.heroes.length < 4 ? `<div class="slot-empty">${mine.some(h => h.slot === 0) ? '' : '<button class="btn" id="joinkb" data-nav>Join with keyboard & mouse</button><br>'}
      ${mine.some(h => h.slot === 0) && !S.p1pad ? `Pick up a controller to play player one with it; more controllers press ${glyph(Object.keys(input.pads)[0] || 'xbox-pad', 'start')} to add couch players` : `Press ${glyph(Object.keys(input.pads)[0] || 'xbox-pad', 'start')} on a controller to add a couch player`} · friends join with the code</div>` : ''}
    <h3>Difficulty</h3>
    <div class="row">${Object.entries(S.diffs || {}).map(([k, n]) => host
      ? `<button class="btn ${L.diff === k ? 'primary' : ''}" data-nav data-diff="${k}">${esc(n)}</button>`
      : `<span class="chip" style="--r:${L.diff === k ? 'var(--gold)' : 'var(--line)'}">${esc(n)}</span>`).join('')}
      <span class="hint">${{ squire: 'Gentler bosses, for a relaxed night.', knight: 'As designed: souls-hard.', hard: 'Faster, meaner bosses; no Second Wind.' }[L.diff] || ''}</span></div>
    ${host && (S.saves || []).length ? `<h3>Saved runs</h3><div class="heroes">${S.saves.map(s =>
      `<div class="row" style="justify-content:space-between"><span class="hint">${esc(s.summary)}</span><span><button class="btn" data-nav data-forget="${esc(s.id)}">Delete</button> <button class="btn" data-nav data-resume="${esc(s.id)}">Resume</button></span></div>`).join('')}</div>` : ''}
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
    if (own) row.dataset.owner = h.id;
    row.appendChild(portrait(h, W));
    const info = document.createElement('div');
    info.innerHTML = `<div class="name">${esc(h.name)}</div>
      <div class="sub">${own ? (h.slot === 0 ? 'Keyboard & mouse' + (S.p1pad ? ' + ' + padName(S.p1pad) : '') : padName('pad' + (h.slot - 1))) : 'Online'} · ${esc(LOOK_NAMES[h.look])} · ${esc(W.name)} · ${esc(data.skills[h.start_skill].name)}</div>
      ${own ? `<div class="picks">${[['look', LOOK_NAMES[h.look], ''], ['weap', W.name, ''], ['skill', data.skills[h.start_skill].name, `style="border-color:${data.skills[h.start_skill].col}"`]]
        .map(([k, name, st]) => `<button class="btn pick" data-nav data-lr data-${k}="${h.id}" ${st}><i>◀</i><span>${esc(name)}</span><i>▶</i></button>`).join('')}</div>
        <div class="hint" style="margin-top:4px">${esc(W.blurb || '')}</div>
        <div class="hint">Starting skill: ${esc(data.skills[h.start_skill].text)}</div>` : ''}`;
    row.appendChild(info);
    const right = document.createElement('div');
    if (own) right.innerHTML = `<div class="col"><button class="btn" data-nav data-drop="${h.id}">Remove</button>
      ${h.slot === 0 && S.p1pad ? `<button class="btn" data-nav data-split title="${esc(padName(S.p1pad))} leaves player one and gets a couch hero of its own">Split off</button>` : ''}</div>`;
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
    b.onclick = e => cycle(side(e, b));
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
    b.onclick = e => cycle(side(e, b));
    b.addEventListener('lr', e => cycle(e.detail));
  });
  el.querySelectorAll('[data-skill]').forEach(b => {
    const ids = Object.keys(data.skills);
    const cycle = dir => {
      const h = L.heroes.find(x => x.id === +b.dataset.skill);
      const next = ids[(ids.indexOf(h.start_skill) + dir + ids.length) % ids.length];
      if (h.slot === 0) { ME.saved.skill = next; ME.save(); }
      net.send({ t: 'set', h: h.id, skill: next });
    };
    b.onclick = e => cycle(side(e, b));
    b.addEventListener('lr', e => cycle(e.detail));
  });
  el.querySelectorAll('[data-diff]').forEach(b => { b.onclick = () => net.send({ t: 'diff', d: b.dataset.diff }); });
  el.querySelectorAll('[data-forget]').forEach(b => { b.onclick = () => net.send({ t: 'forget', id: b.dataset.forget }); });
  el.querySelectorAll('[data-resume]').forEach(b => { b.onclick = () => net.send({ t: 'resume', id: b.dataset.resume }); });
  el.querySelectorAll('[data-drop]').forEach(b => { b.onclick = () => net.send({ t: 'drop', h: +b.dataset.drop }); });
  if ($('[data-split]', el)) $('[data-split]', el).onclick = () => { const pad = S.p1pad; S.p1pad = null; addHero(slotOf(pad)); };
  $('#copy').onclick = () => { navigator.clipboard && navigator.clipboard.writeText(link); $('#copy').textContent = 'Copied'; };
  if ($('#joinkb')) $('#joinkb').onclick = () => addHero(0);
  if ($('#start')) $('#start').onclick = start;
  $('#leave').onclick = leaveRoom;
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
    case 'error':
      S.error = m.msg;
      if (m.soft) { render(); return; }
      net.sock.stop(); S.screen = 'title'; render(); return;
    case 'saves': S.saves = m.list; if (!S.scene) render(); return;
    case 'replaced': S.error = 'This room was opened in another tab.'; net.sock.stop(); S.screen = 'title'; render(); return;
    case 'welcome':
      document.getElementById('status').hidden = true;
      S.me = m.you; S.code = m.code; S.data = m.data; S.diffs = m.diffs;
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
  buildHud(boss, heroes, S.data.colours, heroes.filter(h => h.conn === S.me).map(h => h.id), S.data.skills, S.data.weapons);
  game.scene.start('fight', {
    net, input, data: S.data, fight: m, heroes, me: S.me, zoom,
    onReady: sc => { S.scene = sc; S.starting = false; for (const p of S.pending) sc.onMsg(p); S.pending = []; },
    onFrame: sc => updateHud(sc),
    onBanner: (kind, sub) => banner(kind, sub),
    menuOpen: () => !!S.menu,
    onError: e => oops(e),
    p1pad: () => S.p1pad,
  });
}

function endFight() {
  const sc = S.scene;
  try { sc.cameras.main.fadeOut(550, 5, 3, 10); } catch (e) { /* the scene is already gone */ }
  setTimeout(() => {
    if (S.scene !== sc) return;
    game.scene.stop('fight');
    S.scene = null;
    hideHud();
    music.play('bonfire');
    S.screen = 'lobby';
    render();
  }, 600);
}

setVolume(ME.saved.sfx ?? 0.6); music.setVolume(ME.saved.music ?? 0.5);
requestAnimationFrame(frame);
if (DEBUG) window.kf = { S, input, win: () => net.send({ t: 'debugwin' }), safe: () => net.send({ t: 'debugsafe' }), get net() { return net; } };
