// Shared client state and the socket's send(), so screens don't import each other.
import { identity } from '../../shared/net.js?v=1';

export const S = {
  you: null, code: null, static: null, world: null, room: null, game: null, saves: [],
  sel: null, lastFx: 0, fresh: true, settings: { speed: 1, volume: 0.6, music: 0.5, autoReady: false }, seenHints: {},
};

const me = identity('saltbound');
export const saved = me.saved;
export const persist = me.save;
export const tab = me.tab;
if (saved.settings) Object.assign(S.settings, saved.settings);
if (saved.hints) S.seenHints = saved.hints;

let sender = () => {};
export function setSender(fn) { sender = fn; }
export function send(msg) { sender(msg); }

// Heroes this browser controls in the current run.
export function mine() {
  const r = S.room;
  if (!r || !r.ctl) return [];
  return r.ctl.map((c, h) => (c === S.you ? h : -1)).filter(h => h >= 0);
}
export function heroName(h) {
  const g = S.game;
  return g ? g.heroes[h].name : '';
}
export function controllerName(h) {
  const r = S.room;
  const c = r?.ctl?.[h];
  if (c === 'bot') return 'Bot';
  return r?.people.find(p => p.id === c)?.name || '—';
}
export function isOnline(h) {
  const r = S.room, c = r?.ctl?.[h];
  if (c === 'bot') return true;
  return !!r?.people.find(p => p.id === c)?.on;
}
