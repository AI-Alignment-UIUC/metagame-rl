// Tests the 2000 round rule (env/game.js roundTurns, log #160) on seeded random-policy games over the archived decks:
// (1) a game cut at T plays move for move as the untimed game with the same seed and choices until turn T + 1 begins;
// (2) its winner at the cut is the player with fewer Prizes left (a tie a draw), ending 'time', and reward() pays the
// event's points scaled to [-1, 1]; (3) untimed rewards match the old formula (win 1, deck-out deckoutWin, loss -1,
// draw or cut 0); (4) maxTurns with roundTurns throws; (5) the Runner's per-deal cut from [a, b] stays in a..b, is the
// same for the same seed, and its recorded rewards are the games' rewards.
//
// Run: node env/tools/test_round.js [--games 120]
'use strict';
const { Game } = require('../game.js');
const { Runner } = require('../runner.js');
const { RandomAgent } = require('../agents.js');
const { TokenEncoder } = require('../tokens.js');
const { archivedDecks } = require('../decks.js');
const { Rng } = require('../rng.js');
const { fingerprint } = require('../fingerprint.js');

const argv = process.argv.slice(2);
const GAMES = Number(argv[argv.indexOf('--games') + 1] || 120);
const decks = archivedDecks();
let fails = 0;
const check = (ok, msg) => { if (!ok) { fails++; if (fails <= 10) console.log('FAIL', msg); } };
const left = (g, id) => g.state.players.find(p => p.id === id).prizes.reduce((n, z) => n + z.cards.length, 0);

const play = (g, pol, untilTurn = Infinity) => {
  const trace = [];
  const ids = new Map();
  while (!g.done && g.state.turn <= untilTurn) {
    const d = g.decision();
    if (!d) break;
    g.step(pol.int(d.options.length));
    trace.push(fingerprint(g.state, ids));
  }
  return trace;
};

const tally = { time: 0, timeWins: 0, timeDraws: 0, finished: 0 };
for (let k = 0; k < GAMES; k++) {
  const seed = 7 * 1000003 + k, T = 10 + (k % 40);
  const [a, b] = [decks[k % decks.length].cards, decks[(k * 5 + 1) % decks.length].cards];
  const free = new Game(a, b, seed), timed = new Game(a, b, seed, { roundTurns: T });
  const tf = play(free, new Rng(seed ^ 0x5bd1e995)), tt = play(timed, new Rng(seed ^ 0x5bd1e995));
  check(tt.every((h, i) => h === tf[i]), `game ${k}: the timed game left the untimed one before its cut`);
  // (3) the untimed game's reward against the old formula
  const w = free.winner;
  for (const s of [1, 2]) {
    const old = w === s ? (free.ending === 'deck-out' ? 0.25 : 1) : (w === 1 || w === 2) ? -1 : 0;
    check(free.reward(s, 0.25) === old, `game ${k}: untimed reward ${free.reward(s, 0.25)} vs ${old}`);
  }
  if (timed.ending === 'time') {
    tally.time++;
    check(timed.state.turn === T + 1, `game ${k}: cut at turn ${timed.state.turn}, expected ${T + 1}`);
    const [l1, l2] = [left(timed, 1), left(timed, 2)];
    const want = l1 < l2 ? 1 : l2 < l1 ? 2 : 0;
    check(timed.winner === want, `game ${k}: time winner ${timed.winner}, Prizes left ${l1}/${l2}`);
    if (want) tally.timeWins++; else tally.timeDraws++;
    for (const s of [1, 2]) {
      const r = want === 0 ? -1 / 3 : want === s ? 1 / 3 : -1;
      check(timed.reward(s) === r, `game ${k}: time reward ${timed.reward(s)} vs ${r}`);
    }
    // the untimed game was still going at turn T + 1 with the same Prizes
    check(free.state.turn > T, `game ${k}: untimed game ended before the cut`);
  } else {
    tally.finished++;
    check(timed.winner === free.winner && timed.ending === free.ending, `game ${k}: finished timed game differs`);
    for (const s of [1, 2]) {
      const want = free.winner === s ? 1 : free.winner === 0 ? -1 / 3 : free.winner === -1 ? 0 : -1;
      check(timed.reward(s) === want, `game ${k}: finished timed reward ${timed.reward(s)} vs ${want}`);
    }
  }
}
let threw = false;
try { new Game(decks[0].cards, decks[1].cards, 1, { maxTurns: 40, roundTurns: 40 }); } catch (e) { threw = true; }
check(threw, 'maxTurns with roundTurns did not throw');

(async () => {
  const enc = new TokenEncoder();
  const results = [];
  for (const rep of [0, 1]) {
    const runner = new Runner(enc, { concurrency: 16, roundTurns: [20, 45] });
    let n = 0;
    const nextJob = () => n >= 48 ? null : { deckA: decks[n % decks.length].cards, deckB: decks[(n * 3 + 2) % decks.length].cards,
                                              seed: 1e9 + 977 * n++, seats: { 1: 'r', 2: 'r' } };
    const out = await runner.run(nextJob, { r: new RandomAgent({ seed: 3 }) }, { record: new Set(['r']) });
    results.push(out.results);
    const last = out.rec.reward.filter((_, i) => out.rec.done[i]);
    const pts = out.results.flatMap(r => [1, 2].map(s => r.winner === -1 ? 0 : r.winner === s ? (r.ending === 'time' ? 1 / 3 : 1)
      : r.winner === 0 ? -1 / 3 : -1));
    check(Math.abs(last.reduce((x, y) => x + y, 0) - pts.reduce((x, y) => x + y, 0)) < 1e-4, `runner: recorded rewards differ from the points`);
  }
  const cuts = results[0].map(r => r.roundT);
  check(cuts.every(t => t >= 20 && t <= 45), 'runner: a cut outside 20..45');
  check(new Set(cuts).size > 10, `runner: only ${new Set(cuts).size} distinct cuts`);
  const bySeed = rs => new Map(rs.map(r => [r.seed, r.roundT]));
  const [m0, m1] = results.map(bySeed);
  check([...m0].every(([s, t]) => m1.get(s) === t), 'runner: the same seed drew a different cut');
  console.log(`${GAMES} game pairs: ${tally.time} cut at time (${tally.timeWins} won on Prizes, ${tally.timeDraws} drawn), ` +
              `${tally.finished} finished first; runner cuts ${Math.min(...cuts)}-${Math.max(...cuts)}, ` +
              `${results[0].filter(r => r.ending === 'time').length}/48 at time`);
  console.log(fails ? `${fails} FAILED` : 'all passed');
  process.exit(fails ? 1 : 0);
})();
