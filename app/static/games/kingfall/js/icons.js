// Icons, as inline SVG drawn in currentColor on a 24 x 24 grid: an emblem for each Vow (blessing family),
// one for each skill and one for each weapon's special. icon(name) gives the <svg>; unknown names get a
// plain star, so a new skill or vow shows something until it has its own.
const P = {
  // vows
  ember: '<path d="M12 2c1 4 5 6 5 11a5 5 0 0 1-10 0c0-3 2-4 2-7 1.5 1 2 2.5 2 4 1-2 1.5-5 1-8z"/><path d="M12 21a2.2 2.2 0 0 1-2.2-2.2c0-1.5 1.2-2.2 2.2-3.8 1 1.6 2.2 2.3 2.2 3.8A2.2 2.2 0 0 1 12 21z" fill="currentColor" stroke="none"/>',
  rime: '<path d="M12 2v20M3.3 7l17.4 10M3.3 17l17.4-10"/><path d="M9.5 3.5 12 6l2.5-2.5M9.5 20.5 12 18l2.5 2.5M3.5 10l3.4-.9L6 5.7M20.5 14l-3.4.9.9 3.4M3.5 14l3.4.9-.9 3.4M20.5 10l-3.4-.9.9-3.4"/>',
  blood: '<path d="M12 2.5C9 7 6 10 6 14a6 6 0 0 0 12 0c0-4-3-7-6-11.5z"/><path d="M9 14.5a3 3 0 0 0 3 3"/>',
  storm: '<path d="M13.5 2 5 13.5h6L9.5 22 19 9.5h-6.5z" fill="currentColor" fill-opacity=".25"/>',
  rot: '<circle cx="9" cy="15" r="5"/><circle cx="16.5" cy="9" r="3.5"/><circle cx="17.5" cy="18" r="2"/><circle cx="8" cy="5" r="1.6"/>',
  iron: '<path d="M12 2.5 4 5.5v6c0 5 3.4 8.6 8 10 4.6-1.4 8-5 8-10v-6z"/><path d="M12 2.5v19M4 10h16"/>',
  // skills
  lance: '<path d="M3 21 15 9"/><path d="M14 4l6 0 0 6-3.5-2.5L13.5 10.5 13.5 7.5z" fill="currentColor" fill-opacity=".3"/><path d="M6 14c-2 1-3 3-3 3s2 0 3.5-1M9 17c-1 2-1 4-1 4"/>',
  nova: '<circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="7.5" stroke-dasharray="3 2.4"/><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3"/>',
  smite: '<path d="M9 2h6l-1 14h-4z" fill="currentColor" fill-opacity=".25"/><ellipse cx="12" cy="19" rx="7" ry="2.5"/><path d="M4 15l2 1M20 15l-2 1"/>',
  whirl: '<path d="M20 12a8 8 0 1 1-3-6.3"/><path d="M17.5 2.5l-.6 3.4 3.4.6"/><path d="M15 12a3 3 0 1 1-1.2-2.4"/>',
  step: '<path d="M8 20c-2.5 0-3-3-2.5-5s3.5-2 4 0-.5 5-1.5 5zM15 11c-2.5 0-3-3-2.5-5s3.5-2 4 0-.5 5-1.5 5z"/><path d="M2 8h4M3 12h3M18 18h4M19 14h3" stroke-dasharray="1.5 1.5"/>',
  rally: '<path d="M6 21V3"/><path d="M6 4h12l-3 4 3 4H6" fill="currentColor" fill-opacity=".25"/><path d="M10 16l2 2 4-4"/>',
  mend: '<path d="M9.5 3h5v6.5H21v5h-6.5V21h-5v-6.5H3v-5h6.5z" fill="currentColor" fill-opacity=".2"/>',
  ward: '<path d="M5 9 12 3l7 6v6l-7 6-7-6z" fill="currentColor" fill-opacity=".2"/><path d="M5 9l7 3 7-3M12 12v9"/>',
  knives: '<path d="M12 21V8l1.5-5L15 8v13z"/><path d="M5 20l3.5-11 2.2-3.8.2 4.3L7.5 20.8zM19 20l-3.5-11-2.2-3.8-.2 4.3L16.5 20.8z"/>',
  censer: '<path d="M12 2v4"/><path d="M7 9h10l-1.5 7h-7z" fill="currentColor" fill-opacity=".2"/><path d="M9 16v2h6v-2"/><path d="M6 6c-2 0-3 1.5-2 3M18 6c2 0 3 1.5 2 3M5 20c1.5-1 3 0 4 1M19 20c-1.5-1-3 0-4 1"/>',
  hammer: '<path d="M4 4h10v6H4z" fill="currentColor" fill-opacity=".25"/><path d="M9 10v11"/><path d="M15 15l3-1 3 2M15 19l4 1"/>',
  breath: '<path d="M3 9h11a3 3 0 1 0-3-3"/><path d="M3 14h15a3 3 0 1 1-3 3"/><path d="M3 19h6"/>',
  // weapon specials
  sword: '<path d="M5 4h9v8c0 4-2.5 7-4.5 8C7.5 19 5 16 5 12z" fill="currentColor" fill-opacity=".2"/><path d="M17 7l4-2M17.5 11h4.5M17 15l4 2"/>',
  greatsword: '<path d="M12 2v13"/><path d="M8 15h8M12 15v3"/><path d="M4 21h16M7 21l2-3M17 21l-2-3M12 21v-1"/>',
  daggers: '<path d="M16 3a8 8 0 1 0 5 13A7 7 0 0 1 16 3z" fill="currentColor" fill-opacity=".2"/><path d="M4 20l7-7 1.5 1.5-7 7zM10 12l2-2"/>',
  halberd: '<path d="M4 21 17 5"/><path d="M15 3l6 0-1 5"/><path d="M3 9c3-6 10-7 15-4" stroke-dasharray="2 2"/>',
  bow: '<path d="M6 2v7M12 3v8M18 2v7"/><path d="M4 7l2 3 2-3M10 8l2 3 2-3M16 7l2 3 2-3"/><ellipse cx="12" cy="19" rx="8" ry="2.5"/>',
  catalyst: '<path d="M12 2l2.2 6.8L21 12l-6.8 2.2L12 21l-2.2-6.8L3 12l6.8-3.2z" fill="currentColor" fill-opacity=".25"/><circle cx="12" cy="12" r="2"/>',
  // anything else
  star: '<path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6-4.5-4.2 6.1-.7z"/>',
  crown: '<path d="M3 18h18l-1-10-5 4-3-7-3 7-5-4z" fill="currentColor" fill-opacity=".2"/><path d="M3 21h18"/>',
};

export const icon = (name, cls = '') =>
  `<svg class="ico ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[name] || P.star}</svg>`;
