// Summarises autoplay runs logged with `threefold-autoplay.js --json FILE`: win rates overall and by
// ascent, where runs end, and how runs holding each class, team artifact and artifact fared.
//
//   node tools/threefold-balance.js FILE [--min N]
//
// Artifacts are what the party held at the end, so ones found late look better than they are.
// To even that out, each one's win rate is compared within runs that reached act 3 (the "act-3
// win rate"): roughly, how often a party carrying it beat the last act.
const fs = require('fs');
const args = process.argv.slice(2);
const file = args.find(a => !a.startsWith('--'));
const min = +(args[args.indexOf('--min') + 1] || 0) || 4;
const runs = fs.readFileSync(file, 'utf8').trim().split('\n').map(l => JSON.parse(l)).filter(r => !r.chaos && r.build);
const pct = (a, b) => (b ? `${Math.round((100 * a) / b)}%` : '-').padStart(4);

console.log(`${runs.length} runs, ${runs.filter(r => r.win).length} wins (${pct(runs.filter(r => r.win).length, runs.length)})`);
const byAsc = {};
for (const r of runs) (byAsc[r.build.asc] ||= []).push(r);
for (const [a, rs] of Object.entries(byAsc)) console.log(`  ascent ${a}: ${rs.filter(r => r.win).length}/${rs.length} (${pct(rs.filter(r => r.win).length, rs.length)})`);
// where runs end: act and the kind of fight that ended them
const ends = {};
for (const r of runs.filter(r => !r.win)) { const l = r.log[r.log.length - 1]; const k = l ? `act ${l.act} ${l.kind}` : 'unknown'; ends[k] = (ends[k] || 0) + 1; }
console.log('losses by where they ended:', Object.entries(ends).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${k} ${n}`).join(', '));

const late = runs.filter(r => r.act >= 3);
const lateWins = late.filter(r => r.win).length;
console.log(`\nreached act 3: ${late.length}, won ${lateWins} (${pct(lateWins, late.length)} act-3 win rate overall)`);
function table(title, keyFn) {
  const stat = {};
  for (const r of late) for (const k of new Set(keyFn(r))) { const s = (stat[k] ||= { n: 0, w: 0 }); s.n++; if (r.win) s.w++; }
  const rows = Object.entries(stat).filter(([, s]) => s.n >= min).sort((a, b) => b[1].w / b[1].n - a[1].w / a[1].n);
  console.log(`\n${title} (act-3 win rate, runs; at least ${min} runs)`);
  for (const [k, s] of rows) console.log(`  ${pct(s.w, s.n)}  ${String(s.n).padStart(3)}  ${k}`);
}
table('Class lines', r => r.build.heroes.map(h => [h.cls, ...h.line].join(' > ')));
table('Team artifacts', r => r.build.team);
table('Hero artifacts', r => r.build.heroes.flatMap(h => h.items));
table('Skill artifacts', r => r.build.heroes.flatMap(h => h.skills.flatMap(s => s.mods)));
