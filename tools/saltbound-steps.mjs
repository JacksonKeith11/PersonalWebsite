// The browser's step costs (js/rules.js stepCost) for a batch of steps, so tools/saltbound-check.py
// can compare them with the server's (Game.step_cost).
//
//   node tools/saltbound-steps.mjs < cases.json
//
// Input: {world, games: [{game, static, steps: [[h, a, b, afloat], ...]}]}; prints one [cost, afloat]
// (or null) per step, per game, as JSON.
import { stepCost } from '../app/static/games/saltbound/js/rules.js';

let raw = '';
process.stdin.on('data', d => { raw += d; });
process.stdin.on('end', () => {
  const { world, games } = JSON.parse(raw);
  const out = games.map(({ game, static: st, steps }) => steps.map(([h, a, b, af]) => stepCost(world, game, st, h, a, b, af)));
  process.stdout.write(JSON.stringify(out));
});
