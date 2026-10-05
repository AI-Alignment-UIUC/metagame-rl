// Matchup matrix of the archived decks with one agent piloting both sides (plan items A2, A5.1).
//
// Every unordered pair of distinct decks plays --games games, half with each deck in seat 1
// (who goes first is a coin flip in the engine). Mirrors are 0.5 by symmetry and not played.
// Writes { decks, wins[i][j], games[i][j] } where wins[i][j] counts deck i's wins against deck j
// (draws and cut-off games count half). rl/nash.py solves the meta game.
//
// Run: node env/tools/matrix.js --agent simplebot [--games 200] [--workers 16] [--concurrency 8]
//        [--seed 1] [--decks "substr1,substr2,..."] --out notes/data/eval/matrix_simplebot.json
'use strict';
const { fork } = require('child_process');
const os = require('os');
const fs = require('fs');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const AGENT = flag('agent', 'simplebot');
const GAMES = Number(flag('games', 200));
const WORKERS = Number(flag('workers', Math.max(1, os.cpus().length - 4)));
const CONCURRENCY = Number(flag('concurrency', 8));
const SEED = Number(flag('seed', 1));
const DECKS = flag('decks', null);
const DECKS_FILE = flag('decks-file', null);   // JSON [{ name, cards }] instead of the archived decks
const OUT = flag('out', null);
const NEW = Number(flag('new', 0));   // only pairs involving the last NEW decks (incremental PSRO rows)

function deckList() {
  const { archivedDecks, decksFromFile } = require('../decks.js');
  const all = DECKS_FILE ? decksFromFile(DECKS_FILE) : archivedDecks();
  if (!DECKS) return all;
  return DECKS.split(',').map(p => {
    const d = all.find(x => x.name.toLowerCase().includes(p.trim().toLowerCase()));
    if (!d) throw new Error('no deck matches ' + p);
    return d;
  });
}

// Game k of the whole run -> (i, j, seat of deck i).
function jobsFor(n) {
  const pairs = [];
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (!NEW || j >= n - NEW) pairs.push([i, j]);
  const jobs = [];
  for (const [i, j] of pairs) for (let g = 0; g < GAMES; g++) jobs.push({ i, j, iSeat: g % 2 === 0 ? 1 : 2 });
  return jobs;
}

async function worker(from, to) {
  const { Encoder } = require('../encode.js');
  const { Runner } = require('../runner.js');
  const { archivedDecks } = require('../decks.js');
  const agents = require('../agents.js');
  const decks = deckList();
  const tok = AGENT.startsWith('onnxtok:');
  const enc = tok ? new (require('../tokens.js').TokenEncoder)() : new Encoder([...new Set(archivedDecks().flatMap(d => d.cards))]);
  const make = () => {
    if (AGENT === 'simplebot') return new agents.SimpleBotAgent();
    if (AGENT === 'heuristic') return new agents.HeuristicAgent();
    if (AGENT === 'random') return new agents.RandomAgent({ seed: SEED + from });
    if (tok) return agents.OnnxTokenAgent.load(AGENT.slice(8).replace(/:greedy$/, ''), enc, { seed: SEED + from, greedy: AGENT.endsWith(':greedy') });
    if (AGENT.startsWith('onnx:')) return agents.OnnxAgent.load(AGENT.slice(5).replace(/:greedy$/, ''), enc.obsSize, enc.actionSize, { seed: SEED + from, greedy: AGENT.endsWith(':greedy') });
    throw new Error('unknown agent ' + AGENT);
  };
  const agent = await make();
  const jobs = jobsFor(decks.length);
  const meta = new Map();
  let k = from;
  const nextJob = () => {
    if (k >= to) return null;
    const job = jobs[k], seed = SEED * 1000003 + k;
    k++;
    const [a, b] = job.iSeat === 1 ? [decks[job.i], decks[job.j]] : [decks[job.j], decks[job.i]];
    meta.set(seed, job);
    return { deckA: a.cards, deckB: b.cards, deckName: a.name, deckBName: b.name, seed, seats: { 1: 'p', 2: 'p' } };
  };
  const out = await new Runner(enc, { concurrency: CONCURRENCY }).run(nextJob, { p: agent });
  return out.results.map(r => {
    const job = meta.get(r.seed);
    const iWin = r.winner === job.iSeat ? 1 : (r.winner === 1 || r.winner === 2) ? 0 : 0.5;
    return { i: job.i, j: job.j, iWin, steps: r.steps, error: r.error };
  });
}

if (process.env.MATRIX_WORKER) {
  process.on('message', async ({ from, to }) => { process.send(await worker(from, to)); process.exit(0); });
} else {
  const decks = deckList();
  const total = jobsFor(decks.length).length;
  const t0 = Date.now();
  // Interleave chunks so slow and fast pairs spread over workers.
  const per = Math.ceil(total / (WORKERS * 4));
  const chunks = [];
  for (let from = 0; from < total; from += per) chunks.push({ from, to: Math.min(total, from + per) });
  const results = [];
  let next = 0, running = 0;
  const run = () => new Promise((resolve, reject) => {
    const launch = () => {
      while (running < WORKERS && next < chunks.length) {
        const c = chunks[next++];
        running++;
        const child = fork(__filename, argv, { env: { ...process.env, MATRIX_WORKER: '1' } });
        child.on('message', m => { results.push(...m); });
        child.on('exit', code => {
          running--;
          if (code !== 0) return reject(new Error('worker exited ' + code));
          process.stdout.write(`\r${results.length}/${total} games, ${((Date.now() - t0) / 1000).toFixed(0)}s   `);
          if (next >= chunks.length && running === 0) resolve(); else launch();
        });
        child.send(c);
      }
    };
    launch();
  });
  run().then(() => {
    const n = decks.length;
    const wins = Array.from({ length: n }, () => new Array(n).fill(0));
    const games = Array.from({ length: n }, () => new Array(n).fill(0));
    for (const r of results) {
      wins[r.i][r.j] += r.iWin; wins[r.j][r.i] += 1 - r.iWin;
      games[r.i][r.j]++; games[r.j][r.i]++;
    }
    for (let i = 0; i < n; i++) { wins[i][i] = GAMES / 2; games[i][i] = GAMES; }   // mirrors: 0.5 by symmetry
    const errors = results.filter(r => r.error).length;
    const cut = results.filter(r => r.iWin === 0.5).length;
    console.log(`\n${results.length} games in ${((Date.now() - t0) / 1000).toFixed(0)}s, ${errors} errors, ${cut} draws or cut off`);
    if (OUT) fs.writeFileSync(OUT, JSON.stringify({ agent: AGENT, gamesPerPair: GAMES, seed: SEED, decks: decks.map(d => d.name), wins, games }, null, 1));
  }).catch(e => { console.error(e); process.exitCode = 1; });
}
