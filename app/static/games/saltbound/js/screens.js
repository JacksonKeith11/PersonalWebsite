// The screens around a run: title (new, join, resume), the lobby (claiming heroes, difficulty,
// saved runs) and the end of a run.
import { S, saved, persist, send } from './store.js?v=3';
import { $, h, icon, toast } from './ui.js?v=3';
import { spriteURL } from './art.js?v=3';
import { dieLabel } from './rules.js?v=3';
import { paintTerrain, MAP_W, MAP_H } from './hexmap.js?v=3';
import { connect, disconnect, debug } from './main.js?v=3';

const app = () => $('app');

// ------------------------------------------------------------------ a painted archipelago behind the menus
let backdrop = null;
function makeBackdrop() {
  if (backdrop) return backdrop;
  const W = 30, H = 22, elev = [], bio = [];
  const isl = [[15, 9, 6, 13], [6, 5, 4, 9], [24, 6, 4.5, 10], [8, 16, 4, 9], [23, 16, 5, 11], [15, 19, 2.5, 6], [3, 11, 2.2, 5]];
  for (let r = 0; r < H; r++) for (let q = 0; q < W; q++) {
    const x = q + 0.5 * (r & 1), y = r * 0.866;
    let v = 0;
    for (const [ix, iy, ir, ih] of isl) { const d = Math.hypot(x - ix, y - iy) / ir; if (d < 1) v = Math.max(v, ih * (1 - d * d)); }
    v += Math.sin(q * 1.7 + r) * 0.8 + Math.cos(r * 2.1 - q * 0.6) * 0.6;
    const e = Math.max(0, Math.round(v));
    elev.push(e);
    bio.push(e < 2 ? 'sea' : e < 3 ? 'beach' : e > 11 ? 'peak' : e > 8 ? 'hills' : (q * 7 + r * 3) % 5 < 2 ? 'forest' : 'grass');
  }
  const c = document.createElement('canvas');
  c.width = MAP_W; c.height = MAP_H;
  c.className = 'pix';
  paintTerrain(c, { elev, bio }, { sea: 1, tide: 'low' });
  return (backdrop = c);
}
function withBackdrop(...kids) {
  return h('div.screen', null, h('div.backdrop', null, makeBackdrop()), ...kids);
}

// ------------------------------------------------------------------ title
export function renderTitle() {
  const name = h('input.input', { id: 'name', maxlength: 16, placeholder: 'Your name', value: saved.name || '', autocomplete: 'nickname', spellcheck: 'false' });
  name.addEventListener('change', () => { saved.name = name.value.trim().slice(0, 16); persist(); });
  const code = h('input.input.code', { maxlength: 4, placeholder: 'CODE', 'aria-label': 'Room code', autocomplete: 'off', spellcheck: 'false' });
  const go = (opts) => { saved.name = name.value.trim().slice(0, 16) || 'Sailor'; persist(); connect(opts); };
  code.addEventListener('keydown', e => { if (e.key === 'Enter' && code.value.trim()) go({ room: code.value.trim().toUpperCase() }); });
  const saves = S.saves || [];
  app().replaceChildren(withBackdrop(
    h('a.back-link', { href: '/games' }, '← Games'),
    h('div.title-wrap', null,
      h('div.brand', null,
        h('h1', null, 'Salt', h('span', null, 'bound')),
        h('p', null, 'A co-op voyage across a sinking archipelago, for one to three players.')),
      h('div.title-card.panel', null,
        h('label.field', null, 'Your name', name),
        h('div.title-actions', null,
          h('button.btn.primary.lg', { onclick: () => go({ create: true }) }, icon('sail'), 'Start a new voyage'),
          h('div.join-row', null, code, h('button.btn.lg', { onclick: () => code.value.trim() ? go({ room: code.value.trim().toUpperCase() }) : code.focus() }, 'Join'))),
        saves.length ? h('div.saves', null,
          h('div.eyebrow', null, 'Your saved voyages'),
          ...saves.map(sv => h('div.save-row.card', null,
            h('div.grow', null, h('b', null, sv.title), h('span.muted', null, ago(sv.updated))),
            h('button.btn.sm', { disabled: !sv.ok, tip: sv.ok ? null : 'Saved by an older version', onclick: () => { S.afterJoin = { t: 'resume', id: sv.id }; go({ create: true }); } }, 'Resume'),
            h('button.btn.sm.ghost', { 'aria-label': 'Delete save', tip: 'Delete this save', onclick: () => deleteSave(sv) }, icon('x'))))) : null,
        h('p#status.status-line', { role: 'status' }))),
  ));
}

function deleteSave(sv) {
  if (!confirm(`Delete "${sv.title}"? This can't be undone.`)) return;
  // deleting needs a socket; the title screen has none, so do it through a quick connection
  S.afterJoin = { t: 'delsave', id: sv.id, leave: true };
  connect({ create: true });
}

function ago(ts) {
  const s = Date.now() / 1000 - ts;
  if (s < 90) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} minutes ago`;
  if (s < 86400) return `${Math.round(s / 3600)} hours ago`;
  return `${Math.round(s / 86400)} days ago`;
}

// ------------------------------------------------------------------ lobby
export function renderLobby() {
  const r = S.room, st = S.static;
  if (S.afterJoin) {
    const a = S.afterJoin; S.afterJoin = null;
    send(a);
    if (a.leave) { setTimeout(disconnect, 300); return; }
  }
  const host = r.host === S.you;
  const mySlot = r.slots.findIndex(s => s.pid === S.you);
  const taken = new Set(r.slots.map(s => s.cls).filter(Boolean));
  const person = id => r.people.find(p => p.id === id);
  const ready = r.slots.every(s => s.cls);

  const slots = r.slots.map((slot, i) => {
    const c = slot.cls && st.classes[slot.cls];
    const isMine = slot.pid === S.you;
    const who = slot.pid === 'bot' ? 'Bot' : slot.pid ? person(slot.pid)?.name || 'Someone' : 'Open';
    const ctl = host ? h('select.input', {
      style: { height: '32px', fontSize: '14px', padding: '0 8px', maxWidth: '130px' }, 'aria-label': `Who plays hero ${i + 1}`,
      onchange: e => send({ t: 'assign', slot: i, pid: e.target.value === '' ? null : e.target.value === 'bot' ? 'bot' : +e.target.value }),
    }, h('option', { value: '' }, 'Open'), ...r.people.map(p => h('option', { value: p.id, selected: slot.pid === p.id }, p.name)),
      debug ? h('option', { value: 'bot', selected: slot.pid === 'bot' }, 'Bot (testing)') : null)
      : h('span.chip' + (isMine ? '.brass' : ''), null, icon('person'), who);
    let body;
    if (c) {
      body = [
        h('div.portrait', null, h('img.pix', { src: spriteURL(slot.cls), alt: '' })),
        h('div', null, h('h3', null, c.name), h('div.role', null, `${c.role} · ${c.row === 'front' ? 'Front row' : c.row === 'back' ? 'Back row' : 'Either row'}`)),
        h('p.blurb', null, c.blurb),
        h('div.meta', null,
          h('div', null, h('b', null, 'Dice  '), c.dice.map(dieLabel).join(' + '), ' + gear'),
          h('div', { tip: `${c.map.name}\n${c.map.text}` }, h('b', null, c.map.name + '  '), c.map.text),
          h('div', null, h('b', null, 'Starts with  '), c.start.map(k => st.actions[k].name).join(', '))),
        h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: 'auto' } },
          !slot.pid && !r.resume ? h('button.btn.sm', { onclick: () => send({ t: 'claim', slot: i, cls: slot.cls }) }, 'Play this hero') : null,
          !slot.pid && r.resume ? h('button.btn.sm', { onclick: () => send({ t: 'claim', slot: i }) }, 'Play this hero') : null,
          (isMine || (host && !slot.pid)) && !r.resume ? h('button.btn.sm.ghost', { onclick: () => send({ t: 'setcls', slot: i, cls: null }) }, 'Change class') : null,
          isMine ? h('button.btn.sm.ghost', { onclick: () => send({ t: 'unclaim', slot: i }) }, 'Leave seat') : null),
      ];
    } else {
      const canPick = mySlot < 0 || isMine || host;
      body = [
        h('p.muted', null, canPick ? 'Choose a class:' : 'Waiting for someone to choose.'),
        h('div.class-pick', null, ...Object.entries(st.classes).map(([k, cl]) => h('button.class-opt', {
          disabled: taken.has(k) || !canPick,
          onclick: () => (mySlot < 0 && !slot.pid) || isMine ? send({ t: 'claim', slot: i, cls: k }) : send({ t: 'setcls', slot: i, cls: k }),
        }, h('img.pix', { src: spriteURL(k), alt: '' }), h('div', null, h('b', null, cl.name), h('span', null, cl.role))))),
      ];
    }
    return h('div.slot.card' + (isMine ? '.mine' : ''), null, h('div.slot-head', null, h('span.eyebrow', null, `Hero ${i + 1}`), ctl), ...body);
  });

  const saves = S.saves || [];
  const diffs = [['story', 'Story'], ['normal', 'Normal'], ['hard', 'Hard']];
  const link = `${location.origin}/games/saltbound?room=${r.code}`;
  app().replaceChildren(withBackdrop(
    h('div.lobby.panel', null,
      h('div.lobby-head', null,
        h('div', null, h('div.eyebrow', null, r.resume ? 'Resuming a voyage' : 'New voyage'), h('h1', null, 'Gather your crew')),
        h('div.code-box', null,
          h('span.muted', null, 'Room'), h('span.code', null, r.code),
          h('button.btn.sm', { onclick: () => { navigator.clipboard?.writeText(link); toast('Invite link copied'); } }, icon('link'), 'Copy invite link'),
          h('button.btn.sm.ghost', { onclick: disconnect }, 'Leave'))),
      h('div.lobby-grid', null,
        h('div.slots', null, ...slots),
        h('div.side', null,
          h('div.card', null,
            h('div.eyebrow', null, 'Difficulty'),
            h('div.seg', { role: 'group' }, ...diffs.map(([k, label]) => h('button', {
              'aria-pressed': String(r.diff === k), disabled: !host || !!r.resume, onclick: () => send({ t: 'diff', d: k }),
            }, label))),
            h('p.muted', { style: { fontSize: '14px' } }, {
              story: 'More revives, softer enemies, a slower sea.', normal: 'The voyage as designed.', hard: 'Fewer revives, tougher enemies, a fast-rising sea.',
            }[r.diff])),
          h('div.card', null,
            h('div.eyebrow', null, 'Crew'),
            h('div.people', null, ...r.people.map(p => h('div.person', null, h('span.dot' + (p.on ? '' : '.off')), p.name,
              p.id === r.host ? h('span.chip.brass', { style: { marginLeft: 'auto' } }, 'Host') : null, p.id === S.you ? h('span.muted', null, ' (you)') : null)))),
          r.resume ? h('div.card', null,
            h('div.eyebrow', null, 'Saved voyage'),
            h('div', null, `Turn ${r.resume.turn} · level ${r.resume.level} · ${r.resume.cleared.length} of 3 cleared`),
            host ? h('button.btn.sm.ghost', { onclick: () => send({ t: 'fresh' }) }, 'Start a new voyage instead') : null)
            : host && saves.length ? h('div.card', null,
              h('div.eyebrow', null, 'Or resume'),
              ...saves.map(sv => h('div', { style: { display: 'flex', gap: '8px', alignItems: 'center' } },
                h('span', { style: { flex: 1, fontSize: '14px' } }, sv.title),
                h('button.btn.sm', { disabled: !sv.ok, onclick: () => send({ t: 'resume', id: sv.id }) }, 'Load')))) : null,
          host ? h('button.btn.primary.lg', { disabled: !ready, onclick: () => send({ t: 'start' }) }, 'Set sail')
            : h('p.muted', { style: { textAlign: 'center' } }, 'The host starts the voyage.'),
          host && !ready ? h('p.muted', { style: { fontSize: '14px', textAlign: 'center' } }, 'Every hero needs a class. Heroes nobody claims are played by the host.') : null)),
    ),
  ));
}

// ------------------------------------------------------------------ the end of a run
export function renderEnd() {
  const g = S.game, r = S.room, st = S.static;
  const won = g.result === 'won';
  const host = r.host === S.you;
  app().replaceChildren(withBackdrop(
    h('div.end.panel' + (won ? '.won' : '.lost'), null,
      h('div.eyebrow', null, won ? 'Victory' : 'Defeat'),
      h('h1', null, won ? 'The isles are saved' : g.rises >= g.loss_rise ? 'The sea took the peak' : 'Lost at sea'),
      h('p.muted', null, `Turn ${g.turn} · party level ${g.level} · ${g.cleared.length} of 3 objectives cleared · ${g.diff[0].toUpperCase() + g.diff.slice(1)}`),
      h('table.summary', null,
        h('thead', null, h('tr', null, ...['Hero', 'Damage dealt', 'Healing', 'Kills', 'Damage taken'].map(t => h('th', null, t)))),
        h('tbody', null, ...g.heroes.map((hero, i) => h('tr', null,
          h('td', null, h('img.pix', { src: spriteURL(hero.cls), alt: '' }), hero.name, h('span.muted', null, st.classes[hero.cls].name)),
          h('td', null, g.stats[i].dmg), h('td', null, g.stats[i].heal), h('td', null, g.stats[i].kills), h('td', null, g.stats[i].taken))))),
      h('div', { style: { display: 'flex', gap: '12px', justifyContent: 'center' } },
        host ? h('button.btn.primary.lg', { onclick: () => send({ t: 'quit' }) }, 'Back to the lobby') : h('p.muted', null, 'The host can take everyone back to the lobby.'),
        h('button.btn.lg', { onclick: disconnect }, 'Leave')),
      h('p.faint', { style: { fontSize: '14px' } }, `Seed ${S.world?.seed ?? ''}`)),
  ));
}
