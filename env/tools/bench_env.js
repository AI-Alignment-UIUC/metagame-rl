// Environment throughput with a uniform random policy, single process (plan item A1 exit:
// >= 50 random-policy games/s/core). Splits the time between enumerating options and stepping.
//
// Run: node env/tools/bench_env.js [--games 200] [--seed 1]
'use strict';
const { Game } = require('../game.js');
const { archivedDecks } = require('../decks.js');
const { Rng } = require('../rng.js');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const GAMES = Number(flag('games', 200));
const SEED = Number(flag('seed', 1));

const decks = archivedDecks();
let steps = 0, turnDecisions = 0, promptDecisions = 0, tDecide = 0n, tStep = 0n, errors = 0, cut = 0;
const t0 = process.hrtime.bigint();
for (let g = 0; g < GAMES; g++) {
  const seed = SEED * 1000003 + g;
  const pol = new Rng(seed ^ 0x9e3779b9);
  const game = new Game(decks[g % decks.length].cards, decks[(g * 7 + 3 + Math.floor(g / decks.length)) % decks.length].cards, seed);
  while (!game.done) {
    const a = process.hrtime.bigint();
    const d = game.decision();
    const b = process.hrtime.bigint();
    if (!d) break;
    if (d.prompt) promptDecisions++; else turnDecisions++;
    game.step(pol.int(d.options.length));
    tDecide += b - a;
    tStep += process.hrtime.bigint() - b;
  }
  steps += game.steps;
  if (game.error) errors++;
  else if (game.winner === -1) cut++;
}
const secs = Number(process.hrtime.bigint() - t0) / 1e9;
const us = x => (Number(x) / 1e3 / steps).toFixed(0);
console.log(`${GAMES} games in ${secs.toFixed(1)}s: ${(GAMES / secs).toFixed(1)} games/s/core, ${(steps / GAMES).toFixed(0)} steps/game ` +
  `(${turnDecisions} main-phase, ${promptDecisions} prompt), ${(1e6 * secs / steps).toFixed(0)} us/step`);
console.log(`  per step: ${us(tDecide)} us enumerating, ${us(tStep)} us stepping    errors ${errors}, cut off ${cut}`);
