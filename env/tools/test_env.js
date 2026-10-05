// Checks of the RL environment API and encoder (plan items A1.3, A1.4), on random-policy games:
//   - a seed replays exactly: same seed and actions give the same observations and result
//   - every observation feature is a multiple of 1/48 that fits a byte (encodeU8 is exact)
//   - every option the game offers maps into the action space (actionId never throws), and
//     the ids on offer at a decision are distinct
//   - no engine errors, every game finishes
//
// Run: node env/tools/test_env.js [--games 200]
'use strict';
const crypto = require('crypto');
const { Env } = require('../env.js');
const { Encoder } = require('../encode.js');
const { archivedDecks } = require('../decks.js');
const { Rng } = require('../rng.js');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const GAMES = Number(flag('games', 200));

const decks = archivedDecks();
const enc = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
const failures = [];
const fail = msg => { if (failures.length < 20) failures.push(msg); };

function play(g) {
  const env = new Env(enc);
  const pol = new Rng(77 + g);
  const h = crypto.createHash('sha1');
  let t = env.reset(decks[g % decks.length].cards, decks[(g * 5 + 1) % decks.length].cards, g);
  let steps = 0, maxByte = 0;
  while (!t.done) {
    if (new Set(t.legal).size !== t.legal.length) fail(`game ${g} step ${steps}: duplicate action ids on offer`);
    for (const v of t.obs) {
      const b = v * 48;
      if (Math.abs(b - Math.round(b)) > 1e-4 || b < 0 || b > 255) { fail(`game ${g} step ${steps}: feature ${v} is not a byte multiple of 1/48`); break; }
      if (b > maxByte) maxByte = b;
    }
    h.update(Buffer.from(t.obs.buffer));
    h.update(String(t.legal));
    t = env.step(t.legal[pol.int(t.legal.length)]);
    steps++;
  }
  return { hash: h.digest('hex'), winner: t.winner, steps, error: t.error, maxByte };
}

const t0 = Date.now();
let steps = 0, maxByte = 0;
for (let g = 0; g < GAMES; g++) {
  let a;
  try { a = play(g); } catch (e) { fail(`game ${g}: ${e.message}`); continue; }
  steps += a.steps;
  maxByte = Math.max(maxByte, a.maxByte);
  if (a.error) fail(`game ${g}: engine error ${a.error.message || a.error}`);
  if (a.winner === -1) fail(`game ${g}: did not finish`);
  if (g % 4 === 0) {
    const b = play(g);
    if (b.hash !== a.hash || b.winner !== a.winner) fail(`game ${g}: replay differs`);
  }
}
console.log(`${GAMES} games, ${steps} decisions in ${((Date.now() - t0) / 1000).toFixed(1)}s; obs ${enc.obsSize}, actions ${enc.actionSize}, largest feature byte ${maxByte}`);
for (const f of failures) console.log('FAIL', f);
console.log(failures.length ? 'FAIL' : 'PASS');
process.exitCode = failures.length ? 1 : 0;
