// Fingerprints seeded random-policy games: a hash of the whole game state after every step.
// Run it before and after an engine change; identical hashes mean the change altered nothing
// in any of these games. Use it for engine code the equivalence test (notes/scripts/
// ryuu_engine_equivalence.js) can't swap in and out.
//
// Run: node env/tools/trace_hash.js [--games 300] [--seed 1] [--out hashes.json]
//      node env/tools/trace_hash.js --compare a.json b.json
'use strict';
const crypto = require('crypto');
const fs = require('fs');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };

if (argv[0] === '--compare') {
  const a = JSON.parse(fs.readFileSync(argv[1], 'utf8')), b = JSON.parse(fs.readFileSync(argv[2], 'utf8'));
  const diff = a.games.map((h, i) => h === b.games[i] ? -1 : i).filter(i => i !== -1);
  console.log(`${a.games.length} games: ${diff.length ? diff.length + ' differ (first: game ' + diff[0] + ')' : 'all identical'}`);
  process.exit(diff.length ? 1 : 0);
}

const { Game } = require('../game.js');
const { archivedDecks } = require('../decks.js');
const { Rng } = require('../rng.js');
const { fingerprint } = require('../fingerprint.js');
const GAMES = Number(flag('games', 300));
const SEED = Number(flag('seed', 1));
const OUT = flag('out', null);

const decks = archivedDecks();
const games = [];
const t0 = Date.now();
for (let g = 0; g < GAMES; g++) {
  const seed = SEED * 1000003 + g;
  const pol = new Rng(seed ^ 0x5bd1e995);
  const game = new Game(decks[g % decks.length].cards, decks[(g * 7 + 3 + Math.floor(g / decks.length)) % decks.length].cards, seed);
  const h = crypto.createHash('sha1');
  const ids = new Map();
  while (!game.done) {
    const d = game.decision();
    if (!d) break;
    game.step(pol.int(d.options.length));
    h.update(fingerprint(game.state, ids));
  }
  h.update(String(game.winner));
  games.push(h.digest('hex'));
}
const all = crypto.createHash('sha1').update(games.join()).digest('hex');
console.log(`${GAMES} games in ${((Date.now() - t0) / 1000).toFixed(0)}s, combined hash ${all}`);
if (OUT) fs.writeFileSync(OUT, JSON.stringify({ all, games }));
