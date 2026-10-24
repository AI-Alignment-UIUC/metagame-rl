// Checks of env/agents.js PolicySearchAgent as search-strength judging plays it (log #148), with a stub pilot (the option
// heuristics of env/agents.js as logits, the prize-and-damage score as the value; deterministic, so any difference is the
// search's own):
//   - k = 1 plays exactly the greedy pilot's game, seed by seed (winner, ending, turns, steps and a hash of
//     game.history), through env/runner.js as env/remote_worker.js runs the searched games: the copies the search plays
//     on leave the real game as it was, and a batch's answers go to their own games
//   - k = 4 with 4 copies: every game finishes (prizes, no Pokemon or deck-out; or a draw at the turn limit with
//     --max-turns), no engine error in a game or a search line, and the search moves off the pilot's best somewhere
//   - a batch of decisions searched together answers exactly as each searched alone with the same seed (actions and
//     values), with fewer pilot calls; also with horizon 2 (log #147)
//   - no leak: searching leaves every real game's state, random state and history unchanged; a copy (Game.clone with
//     the decider as viewer) shows the decider exactly the real observation, while the hidden cards are re-dealt
//   - crn (C03, log #162): every candidate of a decision is played on the same dets re-deal seeds, while without it each
//     (candidate, copy) has its own; a crn batch still answers exactly as its decisions one by one
//
// Run: node env/tools/test_search.js [--games 6] [--search-games 4]
'use strict';
const crypto = require('crypto');
const { Env } = require('../env.js');
const { Game } = require('../game.js');
const { Runner } = require('../runner.js');
const { TokenEncoder } = require('../tokens.js');
const { archivedDecks } = require('../decks.js');
const { Rng } = require('../rng.js');
const { fingerprint } = require('../fingerprint.js');
const { PolicySearchAgent, turnScore, promptScore, searchScore } = require('../agents.js');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const GAMES = Number(flag('games', 6)), SEARCH_GAMES = Number(flag('search-games', 4));

const decks = archivedDecks();
const enc = new TokenEncoder();
const failures = [];
const fail = msg => { if (failures.length < 30) failures.push(msg); };

// A deterministic pilot over the env: the heuristics' option scores (a small hash of the key breaks ties), best first,
// and the value 2 x score - 1 from the deciding player's side. It reads b.env, so search lines must carry theirs.
const jitter = key => (crypto.createHash('md5').update(key).digest().readUInt16LE(0) % 997) / 1e5;
class StubPilot {
  constructor() { this.calls = 0; this.rows = 0; }
  async evaluate(batch) {
    this.calls++; this.rows += batch.length;
    return batch.map(b => {
      const g = b.env.game, d = g.decision();
      const sc = d.options.map(o => (d.prompt ? promptScore(o, d.prompt, g.state, g) : turnScore(o.key, g.state)) + jitter(o.key));
      const order = [...b.legal].sort((x, y) => sc[y] - sc[x] || x - y);
      return { order, best: order[0], value: 2 * searchScore(g, d.playerId) - 1 };
    });
  }
}
const greedyOf = pilot => ({ act: async batch => (await pilot.evaluate(batch)).map(e => ({ action: e.best, logp: 0, value: e.value })) });
const historyHash = game => crypto.createHash('sha1').update(JSON.stringify(game.history)).digest('hex').slice(0, 12);

// Games through env/runner.js with one agent in both seats; each result gets its game's history hash (the Runner calls
// every agent's forget(game) as a game finishes, just before its result is pushed).
async function play(agent, n, { seed0 = 1000, maxTurns = 0, concurrency = 6 } = {}) {
  let k = 0;
  const hashes = [];
  const nextJob = () => {
    if (k >= n) return null;
    const g = k++;
    const a = decks[(g * 7) % decks.length], b = decks[(g * 11 + 3) % decks.length];
    return { deckA: a.cards, deckB: b.cards, deckName: a.name, deckBName: b.name, seed: seed0 + g, seats: { 1: 'p', 2: 'p' } };
  };
  const recorder = { act: null, forget: game => hashes.push(historyHash(game)) };
  const out = await new Runner(enc, { concurrency, maxTurns }).run(nextJob, { p: agent, rec: recorder });
  return out.results.map((r, i) => ({ ...r, hash: hashes[i] }));
}

// Main-phase states with two or more options (no prompt open, so they can be copied), from greedy games of the stub.
function states(n, every = 5) {
  const out = [];
  for (let g = 0; out.length < n && g < 40; g++) {
    const env = new Env(enc, { u8: true });
    let t = env.reset(decks[(g * 5) % decks.length].cards, decks[(g * 13 + 1) % decks.length].cards, 500 + g);
    let step = 0;
    while (!t.done && out.length < n) {
      const d = env.game.decision();
      if (!d.prompt && t.legal.length >= 2 && step++ % every === every - 1) out.push({ game: env.game.clone(), decklists: env.decklists });
      const best = d.options.map(o => (d.prompt ? promptScore(o, d.prompt, env.game.state, env.game) : turnScore(o.key, env.game.state)) + jitter(o.key));
      let i = 0;
      for (let j = 1; j < t.legal.length; j++) if (best[t.legal[j]] > best[t.legal[i]]) i = j;
      t = env.step(t.legal[i]);
    }
  }
  return out;
}
// A fresh decision item over an identical copy of a snapshot (Game.clone without a viewer keeps everything).
function item(s) {
  const env = new Env(enc, { u8: true });
  env.game = s.game.clone();
  env.decklists = s.decklists;
  const t = env.observe();
  return { obs: t.obs, legal: t.legal, env };
}
const sameObs = (a, b) => ['tokCard', 'tokKind', 'tokAux', 'glob', 'slots', 'cand'].every(k => Buffer.compare(Buffer.from(a[k].buffer), Buffer.from(b[k].buffer)) === 0)
  && a.nCand === b.nCand && a.nTok === b.nTok;

async function main() {
  const t0 = Date.now();
  // 1. k = 1 is the greedy pilot, game for game
  const greedy = await play(greedyOf(new StubPilot()), GAMES);
  const k1 = new PolicySearchAgent(new StubPilot(), enc, { k: 1, dets: 2, seed: 3 });
  const searched1 = await play(k1, GAMES);
  const bySeed = new Map(greedy.map(r => [r.seed, r]));
  let same = 0;
  for (const r of searched1) {
    const g = bySeed.get(r.seed);
    const fields = ['winner', 'ending', 'turns', 'steps', 'hash'];
    const diff = fields.filter(f => r[f] !== g[f]);
    if (diff.length) fail(`k=1 game ${r.seed}: differs from greedy in ${diff.map(f => `${f} ${r[f]} / ${g[f]}`).join(', ')}`);
    else same++;
    if (r.error || g.error) fail(`k=1 game ${r.seed}: error ${r.error || g.error}`);
  }
  if (k1.stats.searches === 0 || k1.stats.lines === 0) fail('k=1: no searches ran');
  if (k1.stats.changed) fail(`k=1: the search moved off the pilot's best ${k1.stats.changed} times`);
  console.log(`k=1 vs greedy: ${same}/${GAMES} games identical (winner, ending, turns, steps, history hash), `
    + `${k1.stats.searches} searches, ${k1.stats.lines} lines (${((Date.now() - t0) / 1000).toFixed(1)}s)`);

  // 2. k = 4, 4 copies: legal, finished games without errors; and under a turn limit
  const t1 = Date.now();
  const k4 = new PolicySearchAgent(new StubPilot(), enc, { k: 4, dets: 4, seed: 5 });
  const res4 = await play(k4, SEARCH_GAMES, { seed0: 2000, concurrency: 4 });
  for (const r of res4) {
    if (r.error) fail(`k=4 game ${r.seed}: error ${r.error}`);
    if (!(r.winner === 1 || r.winner === 2 || r.winner === 0)) fail(`k=4 game ${r.seed}: did not finish (winner ${r.winner}, steps ${r.steps})`);
  }
  if (k4.stats.lineErrors) fail(`k=4: ${k4.stats.lineErrors} search lines ended in an engine error`);
  if (!k4.stats.changed) fail('k=4: the search never moved off the pilot\'s best (no search effect)');
  const kT = new PolicySearchAgent(new StubPilot(), enc, { k: 4, dets: 4, seed: 6 });
  const resT = await play(kT, 2, { seed0: 3000, maxTurns: 12, concurrency: 2 });
  for (const r of resT) {
    if (r.error || r.turns > 13 || !(r.winner === 0 ? r.ending === 'time' : r.winner === 1 || r.winner === 2)) {
      fail(`k=4 maxTurns 12 game ${r.seed}: turns ${r.turns}, winner ${r.winner}, ending ${r.ending}, error ${r.error}`);
    }
  }
  if (kT.stats.lineErrors) fail(`k=4 maxTurns: ${kT.stats.lineErrors} line errors`);
  const endings = {};
  for (const r of res4) endings[r.ending || 'none'] = (endings[r.ending || 'none'] || 0) + 1;
  console.log(`k=4 dets=4: ${res4.length} games, endings ${JSON.stringify(endings)}, turns ${res4.map(r => r.turns).join('/')}, `
    + `searches ${k4.stats.searches}, moved off the best ${(100 * k4.stats.changed / Math.max(1, k4.stats.searches)).toFixed(1)}%, `
    + `lines ${k4.stats.lines}, line errors ${k4.stats.lineErrors}, capped ${k4.stats.capped}; with maxTurns 12: `
    + `${resT.map(r => `${r.turns} turns ${r.ending}`).join(', ')} (${((Date.now() - t1) / 1000).toFixed(1)}s)`);

  // 3. a batch equals its decisions one by one; 4. searching leaves the real games as they were
  const snaps = states(12);
  for (const horizon of [1, 2]) {
    const pa = new StubPilot(), pb = new StubPilot();
    const A = new PolicySearchAgent(pa, enc, { k: 4, dets: 3, seed: 11, horizon, maxSteps: 40 * horizon });
    const B = new PolicySearchAgent(pb, enc, { k: 4, dets: 3, seed: 11, horizon, maxSteps: 40 * horizon });
    const itemsA = snaps.map(item), itemsB = snaps.map(item);
    const before = itemsA.map(b => [fingerprint(b.env.game.state), JSON.stringify(b.env.game.rng.s), b.env.game.history.length, b.env.game.steps]);
    const ra = await A.act(itemsA);
    const rb = [];
    for (const b of itemsB) rb.push((await B.act([b]))[0]);
    let eq = 0;
    ra.forEach((x, i) => {
      if (x.action !== rb[i].action || x.value !== rb[i].value) fail(`horizon ${horizon} state ${i}: batch ${x.action} ${x.value}, alone ${rb[i].action} ${rb[i].value}`);
      else eq++;
    });
    itemsA.forEach((b, i) => {
      const after = [fingerprint(b.env.game.state), JSON.stringify(b.env.game.rng.s), b.env.game.history.length, b.env.game.steps];
      if (after.some((v, q) => v !== before[i][q])) fail(`horizon ${horizon} state ${i}: the search changed the real game`);
    });
    if (A.stats.lineErrors || B.stats.lineErrors) fail(`horizon ${horizon}: line errors ${A.stats.lineErrors} / ${B.stats.lineErrors}`);
    console.log(`horizon ${horizon}: batch of ${snaps.length} = one by one in ${eq}/${snaps.length} (actions and values); pilot calls `
      + `${pa.calls} batched against ${pb.calls} alone; ${A.stats.lines} lines, moved off the best ${A.stats.changed}, capped ${A.stats.capped}`);
  }

  // 4b. a copy shows the decider exactly what the real game shows it, with the hidden cards re-dealt
  let obsSame = 0, oppHandMoved = 0, ownDeckMoved = 0, tried = 0;
  for (const s of snaps) {
    const real = item(s);
    const me = real.env.current.playerId;
    const opp = s.game.state.players.find(p => p.id !== me), mine = s.game.state.players.find(p => p.id === me);
    const names = z => z.cards.map(c => c.fullName).join(',');
    let handMoved = false, deckMoved = false;
    for (let r = 0; r < 8; r++) {
      const env = new Env(enc, { u8: true });
      env.game = s.game.clone(new Rng(900 + r), me);
      env.decklists = s.decklists;
      const t = env.observe();
      tried++;
      if (sameObs(t.obs, real.obs) && String(t.legal) === String(real.legal)) obsSame++;
      else fail(`copy of a state for player ${me}: the decider's observation differs from the real one`);
      const o2 = env.game.state.players.find(p => p.id !== me), m2 = env.game.state.players.find(p => p.id === me);
      if (names(o2.hand) !== names(opp.hand)) handMoved = true;
      if (names(m2.deck) !== names(mine.deck)) deckMoved = true;
    }
    const oppPool = new Set([...opp.hand.cards, ...opp.deck.cards, ...opp.prizes.flatMap(z => z.cards)].map(c => c.fullName));
    if (opp.hand.cards.length && oppPool.size > 1 && !handMoved) fail(`copies of a state for player ${me}: the opponent's hand never re-dealt`);
    if (mine.deck.cards.length > 1 && new Set(mine.deck.cards.map(c => c.fullName)).size > 1 && !deckMoved) fail(`copies of a state for player ${me}: own deck order never re-dealt`);
    oppHandMoved += handMoved; ownDeckMoved += deckMoved;
  }
  console.log(`copies: the decider's observation identical in ${obsSame}/${tried}; the opponent's hand re-dealt in ${oppHandMoved}/${snaps.length} `
    + `states, own deck in ${ownDeckMoved}/${snaps.length}`);

  // 5. common random numbers: the seeds each search's copies are dealt from, recorded at Game.clone
  const orig = Game.prototype.clone, seen = [];
  Game.prototype.clone = function (rng, viewer) { if (rng) seen.push(JSON.stringify(rng.s)); return orig.call(this, rng, viewer); };
  try {
    for (const crn of [true, false]) {
      const S = new PolicySearchAgent(new StubPilot(), enc, { k: 4, dets: 3, seed: 21, crn });
      let ok = 0;
      for (const sn of snaps) {
        const b = item(sn);
        const nc = Math.min(4, b.legal.length);
        seen.length = 0;
        await S.act([b]);
        const distinct = new Set(seen).size, want = crn ? 3 : nc * 3;
        if (seen.length !== nc * 3 || distinct !== want) fail(`crn ${crn}: ${seen.length} copies with ${distinct} seeds, expected ${nc * 3} with ${want}`);
        else ok++;
      }
      const A = new PolicySearchAgent(new StubPilot(), enc, { k: 4, dets: 3, seed: 23, crn });
      const B = new PolicySearchAgent(new StubPilot(), enc, { k: 4, dets: 3, seed: 23, crn });
      const ra = await A.act(snaps.map(item));
      let eq = 0;
      for (const [i, sn] of snaps.entries()) {
        const x = (await B.act([item(sn)]))[0];
        if (x.action !== ra[i].action || x.value !== ra[i].value) fail(`crn ${crn} state ${i}: batch differs from alone`);
        else eq++;
      }
      console.log(`crn ${crn}: copies dealt as expected in ${ok}/${snaps.length} searches; batch = one by one in ${eq}/${snaps.length}`);
    }
  } finally {
    Game.prototype.clone = orig;
  }

  // 6. keepLines (C49, log #169): every answer carries its candidates and per-copy scores, whose means give its choice
  {
    const S = new PolicySearchAgent(new StubPilot(), enc, { k: 4, dets: 3, seed: 31, crn: true, keepLines: true });
    const res = await S.act(snaps.map(item));
    let ok = 0;
    res.forEach((x, i) => {
      const means = (x.scores || []).map(r => { const v = r.filter(y => y !== null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : -Infinity; });
      const bi = means.indexOf(Math.max(...means));
      const good = x.cands && x.scores.length === x.cands.length && x.scores.every(r => r.length === 3)
        && x.cands[bi] === x.action && Math.abs(means[bi] - x.value) < 1e-9;
      if (!good) fail(`keepLines state ${i}: cands ${x.cands}, action ${x.action}, value ${x.value}, means ${means}`);
      else ok++;
    });
    console.log(`keepLines: ${ok}/${snaps.length} answers carry candidates and copy scores matching their choice`);
  }

  console.log(`${((Date.now() - t0) / 1000).toFixed(1)}s`);
  for (const f of failures) console.log('FAIL', f);
  console.log(failures.length ? 'FAIL' : 'PASS');
  process.exitCode = failures.length ? 1 : 0;
}

main().catch(e => { console.error(e); process.exitCode = 1; });
