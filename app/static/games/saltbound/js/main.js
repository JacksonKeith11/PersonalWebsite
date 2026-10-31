// Saltbound in the browser: the connection, and choosing which screen to show from the room
// state the server sends whenever anything changes.
import { S, saved, persist, tab, setSender, send, mine } from './store.js?v=13';
import { $, toast } from './ui.js?v=13';
import { renderTitle, renderLobby, renderEnd } from './screens.js?v=13';
import { renderGame, handleFx, teardownGame } from './hud.js?v=13';
import { combatBusy } from './combat.js?v=13';
import * as sfx from './audio.js?v=13';

const VERSION = new URL(import.meta.url).searchParams.get('v');
const params = new URLSearchParams(location.search);
const DEBUG = params.has('bots');

let ws = null, wanted = false, retry = 1, join = null;

export function connect(opts) {
  join = opts;
  wanted = true;
  open();
}

export function disconnect() {
  wanted = false;
  S.code = null; S.room = null; S.game = null; S.world = null;
  if (ws) ws.close();
  history.replaceState(null, '', location.pathname + (DEBUG ? '?bots' : ''));
  teardownGame();
  render();
}

function open() {
  const sock = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/games/saltbound/ws`);
  ws = sock;
  setStatus('Connecting…');
  sock.onopen = () => {
    retry = 1;
    sock.send(JSON.stringify({
      t: 'hello', v: VERSION, name: saved.name || 'Sailor', token: saved.token, tab, debug: DEBUG,
      room: S.code || join.room || '', create: !S.code && !!join.create,
    }));
  };
  sock.onmessage = e => receive(JSON.parse(e.data));
  sock.onclose = () => {
    if (ws !== sock) return;
    ws = null;
    if (!wanted) return;
    setStatus(`Disconnected. Reconnecting in ${retry}s…`);
    toast(`Connection lost. Reconnecting in ${retry}s…`, 'err');
    setTimeout(() => { if (wanted && !ws) open(); }, retry * 1000);
    retry = Math.min(retry * 2, 16);
  };
}

setSender(m => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(m)); });

function setStatus(text) { const el = $('status'); if (el) el.textContent = text; }

function receive(m) {
  switch (m.t) {
    case 'welcome':
      S.you = m.you; S.code = m.code; S.static = m.static;
      history.replaceState(null, '', `${location.pathname}?room=${m.code}${DEBUG ? '&bots' : ''}`);
      break;
    case 'saves': S.saves = m.list; render(); break;
    case 'world': S.world = m; S.fresh = true; break;
    case 'state': {
      const before = S.game;
      S.room = m.room; S.game = m.game;
      if (S.game) {
        const fx = S.game.fx.filter(f => f.id > S.lastFx);
        if (S.fresh) { S.fresh = false; S.lastFx = S.game.fx.length ? S.game.fx[S.game.fx.length - 1].id : 0; render(); }
        else {
          // effects first, so animations start from the old positions instead of flashing the new state
          if (fx.length) S.lastFx = fx[fx.length - 1].id;
          if (shown === 'game') handleFx(fx, before);
          render();
          if (shown !== 'game') handleFx(fx, before);
        }
      } else {
        S.lastFx = 0; S.fresh = true; render();
      }
      break;
    }
    case 'err': toast(m.msg, 'err'); sfx.play('error'); break;
    case 'error': wanted = false; S.code = null; render(); setStatus(m.msg); toast(m.msg, 'err'); break;
    case 'reload': location.reload(); break;
  }
}

let shown = null;
export function render() {
  renderScreen();
  sfx.music(shown === 'game' && combatOpenNow() ? 'fight' : shown === 'end' ? null : 'map');
}
function combatOpenNow() { return !!document.querySelector('.combat'); }
function renderScreen() {
  const r = S.room, g = S.game;
  if (!S.code || !r) { if (shown !== 'title') teardownGame(); shown = 'title'; renderTitle(); return; }
  if (!g) { if (shown === 'game' || shown === 'end') teardownGame(); shown = 'lobby'; renderLobby(); return; }
  if (g.phase === 'end' && !combatBusy()) { if (shown === 'game') teardownGame(); shown = 'end'; renderEnd(); return; }
  if (!S.world) return;
  if (S.sel === null || !mine().includes(S.sel)) S.sel = mine()[0] ?? 0;
  shown = 'game';
  renderGame();
}

export const debug = DEBUG;
if (params.get('room')) connect({ room: params.get('room').toUpperCase() });
else render();
if (DEBUG) { window.saltbound = S; window.saltboundSend = send; }
