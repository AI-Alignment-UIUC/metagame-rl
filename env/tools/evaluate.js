// Head-to-head evaluation between two agents (plan item A2 protocol).
//
// Agent X plays deck D1 against agent Y on deck D2, then the decks swap, so the result is
// reported for both directions of the matchup and together. Who goes first is a coin flip in
// the engine. Win rates come with a 95% confidence interval (normal approximation; draws and
// cut-off games count as half a win).
//
// Agents: random | first | heuristic | simplebot | search[:rollouts[:turns]] | onnx:<file.onnx>[:greedy]
//         | onnxtok:<file.onnx>[:greedy] (token model)
// Decks:  any substring of an archived deck name ("division #place player (label)"), or "all"
//         to cycle every archived deck on both sides.
//
//      --mirror: both sides play the same deck; --per-deck: a line per deck of X
// Run: node env/tools/evaluate.js --x simplebot --y random --d1 "Wigglytuff" --d2 "Haymaker"
//        [--games 200] [--workers 16] [--concurrency 16] [--seed 1] [--json out.json]
'use strict';
const { fork } = require('child_process');
const os = require('os');
const fs = require('fs');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const X = flag('x', 'simplebot'), Y = flag('y', 'random');
const D1 = flag('d1', 'all'), D2 = flag('d2', 'all');
const GAMES = Number(flag('games', 200));
const WORKERS = Number(flag('workers', Math.max(1, os.cpus().length - 4)));
const CONCURRENCY = Number(flag('concurrency', 16));
const SEED = Number(flag('seed', 1));
const JSON_OUT = flag('json', null);
const DECKS_FILE = flag('decks-file', null);   // JSON [{ name, cards }] instead of the archived decks
const MIRROR = argv.includes('--mirror');        // both sides play the same deck (piloting skill per deck)
const PER_DECK = argv.includes('--per-deck');    // print the win rate for each of X's decks

async function makeAgent(spec, enc, seed) {
  const { OnnxAgent, RandomAgent, FirstAgent, HeuristicAgent, SimpleBotAgent, SearchAgent } = require('../agents.js');
  if (spec === 'random') return new RandomAgent({ seed });
  if (spec === 'first') return new FirstAgent();
  if (spec === 'heuristic') return new HeuristicAgent();
  if (spec.startsWith('search')) { const [, r, d] = spec.split(':'); return new SearchAgent({ rollouts: Number(r || 8), depth: Number(d || 2), seed }); }
  if (spec === 'simplebot') return new SimpleBotAgent();
  if (spec.startsWith('onnxtok:')) {
    const { OnnxTokenAgent } = require('../agents.js');
    const { TokenEncoder } = require('../tokens.js');
    return OnnxTokenAgent.load(spec.slice(8).replace(/:greedy$/, ''), new TokenEncoder(), { seed, greedy: spec.endsWith(':greedy') });
  }
  if (spec.startsWith('onnx:')) {
    const parts = spec.slice(5).split(':greedy');
    return OnnxAgent.load(parts[0], enc.obsSize, enc.actionSize, { seed, greedy: spec.endsWith(':greedy') });
  }
  throw new Error('unknown agent ' + spec);
}

function pickDecks(decks, pattern) {
  if (pattern === 'all') return decks;
  const found = decks.filter(d => d.name.toLowerCase().includes(pattern.toLowerCase()));
  if (found.length === 0) throw new Error('no archived deck matches ' + pattern + '\n' + decks.map(d => d.name).join('\n'));
  return found;
}

async function worker(from, to) {
  const { Encoder } = require('../encode.js');
  const { Runner } = require('../runner.js');
  const { archivedDecks } = require('../decks.js');
  const decks = DECKS_FILE ? require('../decks.js').decksFromFile(DECKS_FILE) : archivedDecks();
  // A token-model agent needs token observations (the other agents choose by option either way).
  const tok = [X, Y].some(sp => sp.startsWith('onnxtok:'));
  // The identity vocabulary is the one the models train on (the field's cards), whatever the decks.
  const enc = tok ? new (require('../tokens.js').TokenEncoder)() : new Encoder([...new Set(archivedDecks().flatMap(d => d.cards))]);
  const agents = { x: await makeAgent(X, enc, SEED * 7919 + from), y: await makeAgent(Y, enc, SEED * 104729 + from) };
  const d1 = pickDecks(decks, D1), d2 = pickDecks(decks, D2);
  let g = from;
  const meta = new Map();
  const nextJob = () => {
    if (g >= to) return null;
    const i = g++;
    // Even games: X has D1; odd games: X has D2. Seats alternate too.
    const xDeckFirst = i % 2 === 0;
    const a = d1[Math.floor(i / 2) % d1.length], b = MIRROR ? a : d2[Math.floor(i / 2) % d2.length];
    const [xd, yd] = xDeckFirst ? [a, b] : [b, a];
    const xSeat = Math.floor(i / 2) % 2 === 0 ? 1 : 2;
    const seats = xSeat === 1 ? { 1: 'x', 2: 'y' } : { 1: 'y', 2: 'x' };
    const deckA = xSeat === 1 ? xd : yd, deckB = xSeat === 1 ? yd : xd;
    const job = { deckA: deckA.cards, deckB: deckB.cards, deckName: deckA.name, deckBName: deckB.name, seed: SEED * 1000003 + i, seats };
    meta.set(job.seed, { xDeckIsD1: xDeckFirst, xSeat, xDeck: xd.name });
    return job;
  };
  const runner = new Runner(enc, { concurrency: CONCURRENCY });
  const out = await runner.run(nextJob, agents);
  return out.results.map(r => {
    const m = meta.get(r.seed);
    return { xWins: r.winner === m.xSeat ? 1 : (r.winner === 1 || r.winner === 2) ? 0 : 0.5, cut: r.winner !== 1 && r.winner !== 2,
      xDeckIsD1: m.xDeckIsD1, xDeck: m.xDeck, xSeat: m.xSeat, steps: r.steps, error: r.error };
  });
}

function summary(rows) {
  const n = rows.length;
  const w = rows.reduce((a, r) => a + r.xWins, 0);
  const p = n ? w / n : 0;
  const ci = n ? 1.96 * Math.sqrt(p * (1 - p) / n) : 0;
  return { n, xWinRate: p, ci95: ci, cut: rows.filter(r => r.cut).length, errors: rows.filter(r => r.error).length };
}

if (process.env.EVAL_WORKER) {
  process.on('message', async ({ from, to }) => { process.send(await worker(from, to)); process.exit(0); });
} else {
  const t0 = Date.now();
  const per = Math.ceil(GAMES / WORKERS);
  const chunks = [];
  for (let w = 0; w < WORKERS; w++) { const from = w * per, to = Math.min(GAMES, from + per); if (from < to) chunks.push({ from, to }); }
  Promise.all(chunks.map(c => new Promise((resolve, reject) => {
    const child = fork(__filename, argv, { env: { ...process.env, EVAL_WORKER: '1' } });
    child.on('message', resolve);
    child.on('exit', code => { if (code !== 0) reject(new Error('worker exited ' + code)); });
    child.send(c);
  }))).then(parts => {
    const rows = parts.flat();
    const all = summary(rows);
    const dir1 = summary(rows.filter(r => r.xDeckIsD1));
    const dir2 = summary(rows.filter(r => !r.xDeckIsD1));
    const fmt = s => `${(100 * s.xWinRate).toFixed(1)}% ± ${(100 * s.ci95).toFixed(1)} (n=${s.n}${s.cut ? ', ' + s.cut + ' cut off' : ''}${s.errors ? ', ' + s.errors + ' errors' : ''})`;
    console.log(`${X} vs ${Y}, decks ${D1} / ${D2}, ${rows.length} games in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
    console.log(`  ${X} win rate overall:        ${fmt(all)}`);
    if (D1 !== D2) {
      console.log(`  ${X} on ${D1}, ${Y} on ${D2}: ${fmt(dir1)}`);
      console.log(`  ${X} on ${D2}, ${Y} on ${D1}: ${fmt(dir2)}`);
    }
    if (PER_DECK) {
      const by = new Map();
      for (const r of rows) { if (!by.has(r.xDeck)) by.set(r.xDeck, []); by.get(r.xDeck).push(r); }
      for (const [deck, rs] of [...by].sort((p, q) => summary(p[1]).xWinRate - summary(q[1]).xWinRate)) console.log(`    ${fmt(summary(rs))}  ${deck}`);
    }
    for (const r of rows.filter(r => r.error).slice(0, 5)) console.log('  ERROR', r.error);
    if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify({ x: X, y: Y, d1: D1, d2: D2, all, dir1, dir2, rows }, null, 1));
  }).catch(e => { console.error(e); process.exitCode = 1; });
}
