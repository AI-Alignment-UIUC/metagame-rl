// The play policy's own judgment of a matchup, without playing it out (plan item A5.2): for each
// deck pair (A, B), deal --openings games with A in seat 1 and as many with B in seat 1; the
// token policy makes the setup choices, and at the first main-phase decision (after setup and
// the first draw) its value head is read, from A's side. u(A, B) is the mean, in [-1, 1];
// u(B, A) = -u(A, B) by construction (only i < j is computed). Who goes first is the engine's
// coin flip, so both are covered.
//
// Run: node env/tools/start_values.js --model runs/a4-tok/model_it00249.onnx --decks-file pop.json
//        [--pairs pairs.json] [--openings 16] [--workers 16] [--seed 1] --out values.json
// --pairs: [[i, j], ...] indices into the decks (default: every i < j). Without --decks-file the
// archived decks are used. Output: { decks, openings, pairs: [[i, j, u, sd]], u: D x D (null if not computed) }.
'use strict';
const { fork } = require('child_process');
const fs = require('fs');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const MODEL = flag('model', null);
const DECKS_FILE = flag('decks-file', null);
const PAIRS_FILE = flag('pairs', null);
const OPENINGS = Number(flag('openings', 16));
const WORKERS = Number(flag('workers', 16));
const CONCURRENCY = Number(flag('concurrency', 64));
const SEED = Number(flag('seed', 1));
const OUT = flag('out', null);

function loadDecks() {
  const D = require('../decks.js');
  return DECKS_FILE ? D.decksFromFile(DECKS_FILE) : D.archivedDecks();
}

async function worker(jobs) {
  const { Env } = require('../env.js');
  const { TokenEncoder } = require('../tokens.js');
  const { OnnxTokenAgent } = require('../agents.js');
  const decks = loadDecks();
  const enc = new TokenEncoder();
  const agent = await OnnxTokenAgent.load(MODEL, enc, { seed: SEED, greedy: true });
  const sums = new Map();                  // "i,j" -> [sum, sumsq, n]
  let next = 0;
  const slots = [];
  const start = () => {
    const job = jobs[next++];
    const [a, b] = job.aFirst ? [job.i, job.j] : [job.j, job.i];
    const env = new Env(enc, { u8: true });
    const t = env.reset(decks[a].cards, decks[b].cards, job.seed);
    return { job, env, t, seatOfA: job.aFirst ? 1 : 2 };
  };
  while (slots.length < CONCURRENCY && next < jobs.length) slots.push(start());
  while (slots.length > 0) {
    const ask = [];
    for (let k = slots.length - 1; k >= 0; k--) {
      const s = slots[k];
      while (!s.t.done && s.t.legal.length === 1 && s.env.game.decision().prompt) s.t = s.env.step(s.t.legal[0]);
      if (s.t.done) {                       // ended in setup (rare): no reading
        slots.splice(k, 1);
        if (next < jobs.length) slots.push(start());
        continue;
      }
      ask.push(s);
    }
    if (ask.length === 0) continue;
    const out = await agent.act(ask.map(s => ({ obs: s.t.obs, legal: s.t.legal, env: s.env })));
    ask.forEach((s, k) => {
      if (!s.env.game.decision().prompt) {   // first main-phase decision: read the value
        const v = s.t.playerId === s.seatOfA ? out[k].value : -out[k].value;
        const key = s.job.i + ',' + s.job.j;
        const acc = sums.get(key) || [0, 0, 0];
        acc[0] += v; acc[1] += v * v; acc[2] += 1;
        sums.set(key, acc);
        slots.splice(slots.indexOf(s), 1);
        if (next < jobs.length) slots.push(start());
      } else {
        s.t = s.env.step(out[k].action);
      }
    });
  }
  return [...sums];
}

if (process.env.SV_WORKER) {
  process.on('message', async jobs => { process.send(await worker(jobs)); process.exit(0); });
} else {
  (async () => {
    if (!MODEL || !OUT) throw new Error('usage: --model <token.onnx> --out <file>');
    const decks = loadDecks();
    const D = decks.length;
    const pairs = PAIRS_FILE ? JSON.parse(fs.readFileSync(PAIRS_FILE, 'utf8')).map(([i, j]) => (i < j ? [i, j] : [j, i]))
      : [].concat(...decks.map((_, i) => decks.map((_, j) => [i, j]).filter(([x, y]) => x < y)));
    const jobs = [];
    pairs.forEach(([i, j], p) => {
      for (let k = 0; k < OPENINGS; k++) {
        for (const aFirst of [true, false]) jobs.push({ i, j, aFirst, seed: SEED * 10000019 + p * 1009 + 2 * k + (aFirst ? 0 : 1) });
      }
    });
    const t0 = Date.now();
    const chunks = Array.from({ length: WORKERS }, (_, w) => jobs.filter((_, k) => k % WORKERS === w)).filter(c => c.length);
    const parts = await Promise.all(chunks.map(c => new Promise((resolve, reject) => {
      const child = fork(__filename, argv, { env: { ...process.env, SV_WORKER: '1' } });
      child.on('message', resolve);
      child.on('exit', code => { if (code !== 0) reject(new Error('worker exited ' + code)); });
      child.send(c);
    })));
    const acc = new Map();
    for (const part of parts) for (const [key, [s, q, n]] of part) {
      const a = acc.get(key) || [0, 0, 0];
      acc.set(key, [a[0] + s, a[1] + q, a[2] + n]);
    }
    const u = Array.from({ length: D }, () => new Array(D).fill(null));
    const rows = [];
    for (let i = 0; i < D; i++) u[i][i] = 0;
    for (const [key, [s, q, n]] of acc) {
      const [i, j] = key.split(',').map(Number);
      const m = s / n, sd = Math.sqrt(Math.max(0, q / n - m * m));
      u[i][j] = m; u[j][i] = -m;
      rows.push([i, j, m, sd, n]);
    }
    fs.writeFileSync(OUT, JSON.stringify({ decks: decks.map(d => d.name), openings: OPENINGS, model: MODEL, pairs: rows, u }));
    console.log(`${pairs.length} pairs x ${2 * OPENINGS} openings in ${((Date.now() - t0) / 1000).toFixed(1)}s -> ${OUT}`);
  })();
}
