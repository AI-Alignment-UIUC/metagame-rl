// Group A (the walls) against group B (the human lists) with a different agent on each side (evaluation only; log
// #137's question: does stronger play of the human lists flip the walls' matchups?). Unlike env/tools/evaluate.js the
// decks never swap agents: A's decks are always played by --a-agent and B's by --b-agent.
//
// Deals match notes/scripts/probe_matchups.py / rl/gpu_matrix.py jobs_for: pair p = i * |B| + j (j the index in the
// full B list, also when --b-subset picks some), game g has seed SEED * 1000003 + p * STRIDE + g, and A's deck sits in
// seat 1 on even g, seat 2 on odd g. So --seed 11 --stride 32 gives the same deals as log #137's 32-game probe, and
// two runs with the same seed differ only in the agents. --trim cuts the ONNX inputs to the batch's longest state.
//
// Jobs go g-major (every pair's game 0, then every pair's game 1, ...) round robin to the workers, so a run stopped
// early is still balanced over the pairs. Each finished game is a JSON line in --out as it ends.
//
//   node notes/scripts/walls_vs_humans.js --a runs/probe/walls_resetcap499.json --b runs/probe/archived.json \
//     --a-agent onnxtok:runs/probe/resetcap499.onnx:greedy --b-agent psearch:runs/probe/resetcap499.onnx:4:4 \
//     --games 8 --seed 11 --stride 32 --workers 4 --concurrency 8 --out runs/probe/x.jsonl [--b-subset 0,1,5]
//   --dump-obs N file: instead, play greedy games and write N real observations with the A agent's ONNX outputs
//     (for notes/scripts/export_pilot_onnx.py --check).
'use strict';
const path = require('path');
const fs = require('fs');
const { fork } = require('child_process');

const ROOT = path.resolve(__dirname, '..', '..');
const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const A_FILE = flag('a'), B_FILE = flag('b');
const A_AGENT = flag('a-agent'), B_AGENT = flag('b-agent');
const GAMES = Number(flag('games', 8)), STRIDE = Number(flag('stride', 32)), SEED = Number(flag('seed', 11));
const G0 = Number(flag('g0', 0));                     // first game index (to extend a run with new deals)
const WORKERS = Math.min(4, Number(flag('workers', 4)));   // the probe's cap: 4 processes, 1 ONNX thread each
const CONC = Number(flag('concurrency', 8));
const OUT = flag('out', null);
// --skip FILE: leave out the (i, j, g) games already in FILE (a run's earlier .jsonl), so an unfinished run is completed
// on its own deals into a new --out (log #155).
const SKIP = flag('skip', null);
const DUMP = flag('dump-obs', null);
const DUMP_FILE = DUMP ? argv[argv.indexOf('--dump-obs') + 2] : null;

const A = JSON.parse(fs.readFileSync(path.resolve(ROOT, A_FILE), 'utf8'));
const B = JSON.parse(fs.readFileSync(path.resolve(ROOT, B_FILE), 'utf8'));
const SUBSET = flag('b-subset', null) ? flag('b-subset').split(',').map(Number) : B.map((_, j) => j);

// --trim: the token inputs cut to the batch's longest state (obs.nTok, at least the 13 global and slot tokens) before
// the ONNX call. Needs an export with a dynamic token axis (notes/scripts/export_pilot_onnx.py --dyn-tok); the padding is
// masked, so the outputs are the same (checked there to 1e-5) at a fraction of the cost (states hold ~50-120 of 256).
const TRIM = argv.includes('--trim');
function trimmedAgentClass() {
  const { OnnxTokenAgent } = require(path.join(ROOT, 'env', 'agents.js'));
  const { sampleMasked } = require(path.join(ROOT, 'env', 'agents.js'));
  return class TrimmedTokenAgent extends OnnxTokenAgent {
    static async load(file, enc, opts) {
      const ort = require('onnxruntime-node');
      const session = await ort.InferenceSession.create(file, { intraOpNumThreads: 1, interOpNumThreads: 1 });
      return new TrimmedTokenAgent(session, enc, opts);
    }
    async act(batch, raw = false) {
      const ort = require('onnxruntime-node');
      const n = batch.length, e = this.enc;
      const T = Math.max(13, ...batch.map(b => b.obs.nTok));
      const tc = new Int16Array(n * T), tk = new Uint8Array(n * T), ta = new Uint8Array(n * T);
      const gl = new Uint8Array(n * e.GLOB_F), sl = new Uint8Array(n * 12 * e.SLOT_F), cd = new Int16Array(n * e.MAX_CAND * 6);
      const nc = new Int32Array(n);
      batch.forEach((b, i) => {
        const o = b.obs;
        tc.set(o.tokCard.subarray(0, T), i * T); tk.set(o.tokKind.subarray(0, T), i * T); ta.set(o.tokAux.subarray(0, T), i * T);
        gl.set(o.glob, i * e.GLOB_F); sl.set(o.slots, i * 12 * e.SLOT_F); cd.set(o.cand, i * e.MAX_CAND * 6); nc[i] = o.nCand;
      });
      const out = await this.session.run({
        tok_card: new ort.Tensor('int16', tc, [n, T]), tok_kind: new ort.Tensor('uint8', tk, [n, T]),
        tok_aux: new ort.Tensor('uint8', ta, [n, T]), glob: new ort.Tensor('uint8', gl, [n, e.GLOB_F]),
        slots: new ort.Tensor('uint8', sl, [n, 12 * e.SLOT_F]), cand: new ort.Tensor('int16', cd, [n, e.MAX_CAND * 6]),
        n_cand: new ort.Tensor('int32', nc, [n]),
      });
      const logits = out.logits.data, value = out.value.data;
      if (raw) return { logits, value };
      return batch.map((b, i) => {
        const s = sampleMasked(logits, i * e.MAX_CAND, b.legal, this.rng, this.greedy);
        return { action: s.action, logp: s.logp, value: value[i] };
      });
    }
  };
}

// nodraw:N:<spec> (diagnosis only, log #141): <spec>, except that while the deciding player's deck holds N cards or fewer
// it is not offered Professor Oak, Bill or Gambler. Does the pilot of the human lists lose to the walls by drawing
// itself out? Counted in stats.masked (decisions where an offered draw card was hidden).
const DRAW_CARDS = ['Professor Oak BS', 'Bill BS', 'Gambler FO'];
async function makeAgent(spec, enc, seed, stats) {
  if (spec.startsWith('nodraw:')) {
    const [, n, ...rest] = spec.split(':');
    const inner = await makeAgent(rest.join(':'), enc, seed, stats);
    const N = Number(n);
    return {
      async act(batch) {
        const cut = batch.map(b => {
          const g = b.env.game, d = g.decision();
          const me = g.state.players.find(p => p.id === d.playerId);
          if (!me || me.deck.cards.length > N) return b;
          const legal = b.legal.filter(k => !(d.options[k].key.startsWith('trainer|')
                                              && DRAW_CARDS.some(c => d.options[k].key.includes(c))));
          if (legal.length < b.legal.length) stats.masked = (stats.masked || 0) + 1;
          return legal.length ? { ...b, legal } : b;
        });
        return inner.act(cut);
      },
    };
  }
  const { PolicySearchAgent } = require(path.join(ROOT, 'env', 'agents.js'));
  const OnnxTokenAgent = TRIM ? trimmedAgentClass() : require(path.join(ROOT, 'env', 'agents.js')).OnnxTokenAgent;
  if (spec.startsWith('onnxtok:')) {
    return OnnxTokenAgent.load(path.resolve(ROOT, spec.slice(8).replace(/:greedy$/, '')), enc, { seed, greedy: spec.endsWith(':greedy') });
  }
  if (spec.startsWith('psearch:')) {
    const [file, k, dets, horizon] = spec.slice(8).split(':');   // psearch:<onnx>:k:dets[:horizon] (log #147)
    const pilot = await OnnxTokenAgent.load(path.resolve(ROOT, file), enc, { seed, greedy: true });
    const H = Number(horizon || 1);
    const ps = new PolicySearchAgent(pilot, enc, { k: Number(k || 4), dets: Number(dets || 4), seed, horizon: H, maxSteps: 40 * H });
    const orig = ps.searchAll.bind(ps);
    ps.searchAll = async items => {             // count searches and how often they overrule the greedy pilot
      const t0 = Date.now();                    // (a batch's searches run together since log #148: ms per search is shared)
      const r = await orig(items);
      stats.searches += items.length; stats.searchMs += Date.now() - t0;
      r.forEach((x, q) => { if (x.action !== items[q].e.best) stats.changed++; });
      return r;
    };
    return ps;
  }
  throw new Error('unknown agent ' + spec);
}

async function worker(jobs) {
  const { Env } = require(path.join(ROOT, 'env', 'env.js'));
  const { TokenEncoder } = require(path.join(ROOT, 'env', 'tokens.js'));
  const enc = new TokenEncoder();
  enc.history = 0;
  const stats = { searches: 0, changed: 0, searchMs: 0, decisions: { a: 0, b: 0 } };
  const wid = jobs.length ? jobs[0].w : 0;
  const agents = { a: await makeAgent(A_AGENT, enc, SEED * 7919 + wid, stats), b: await makeAgent(B_AGENT, enc, SEED * 104729 + wid, stats) };
  const dump = [];
  let next = 0;
  const slots = [];
  const start = job => {
    const env = new Env(enc, { u8: true, showOpponentDecklist: true });
    const aSeat = job.g % 2 === 0 ? 1 : 2;
    const [d1, d2] = aSeat === 1 ? [A[job.i], B[job.j]] : [B[job.j], A[job.i]];
    const t = env.reset(d1.cards, d2.cards, job.seed);
    return { job, env, t, aSeat, seats: aSeat === 1 ? { 1: 'a', 2: 'b' } : { 1: 'b', 2: 'a' }, trace: [], lastTurn: -1 };
  };
  const prizesLeft = (g, id) => { const p = g.state.players.find(q => q.id === id); return p ? p.prizes.reduce((a, z) => a + z.cards.length, 0) : 0; };
  // The Prizes each side has left as each turn begins ([turn, A's, B's], log #150), so a round rule that decides an
  // unfinished game by Prizes can be scored exactly at any cut T from one run: the last entry with turn <= T + 1.
  const mark = s => {
    const g = s.env.game;
    if (g.state.turn === s.lastTurn) return;
    s.lastTurn = g.state.turn;
    s.trace.push([g.state.turn, prizesLeft(g, s.aSeat), prizesLeft(g, 3 - s.aSeat)]);
  };
  // A file <out>.stop ends the run gracefully: no new games start, the ones in play finish, and the stats are reported.
  const stopFile = OUT ? path.resolve(ROOT, OUT + '.stop') : null;
  const fill = () => {
    if (stopFile && fs.existsSync(stopFile)) return;
    while (slots.length < CONC && next < jobs.length) slots.push(start(jobs[next++]));
  };
  const finish = s => {
    const g = s.env.game, w = s.t.winner;
    const left = id => prizesLeft(g, id);
    const row = { i: s.job.i, j: s.job.j, g: s.job.g, seed: s.job.seed, aSeat: s.aSeat, winner: w, ending: g.ending,
      aScore: w === s.aSeat ? 1 : (w === 1 || w === 2) ? 0 : 0.5, turns: g.state.turn,
      prizesLeftA: left(s.aSeat), prizesLeftB: left(3 - s.aSeat), steps: s.t.steps, prizeTrace: s.trace,
      error: s.t.error ? String(s.t.error.message || s.t.error) : undefined };
    process.send({ row });
  };
  fill();
  while (slots.length) {
    for (const s of slots) { mark(s); while (!s.t.done && s.t.legal.length === 1) { s.t = s.env.step(s.t.legal[0]); mark(s); } }
    const by = new Map();
    for (const s of slots) {
      if (s.t.done) continue;
      const who = s.seats[s.t.playerId];
      if (!by.has(who)) by.set(who, []);
      by.get(who).push(s);
    }
    const groups = [...by];
    const outs = await Promise.all(groups.map(([who, group]) => agents[who].act(group.map(s => ({ obs: s.t.obs, legal: s.t.legal, env: s.env })))));
    groups.forEach(([who, group], gi) => group.forEach((s, k) => {
      stats.decisions[who]++;
      if (DUMP && dump.length < Number(DUMP)) dump.push(s.t.obs);
      s.t = s.env.step(outs[gi][k].action);
      mark(s);
    }));
    for (let k = slots.length - 1; k >= 0; k--) if (slots[k].t.done) { finish(slots[k]); slots.splice(k, 1); }
    if (DUMP && dump.length >= Number(DUMP)) break;
    fill();
  }
  if (DUMP) {
    const raw = await agents.a.act(dump.map(o => ({ obs: o, legal: [...Array(o.nCand).keys()] })), true);
    const M = enc.MAX_CAND;
    const rows = dump.map((o, i) => ({ tokCard: [...o.tokCard], tokKind: [...o.tokKind], tokAux: [...o.tokAux], glob: [...o.glob],
      slots: [...o.slots], cand: [...o.cand], nCand: o.nCand, logits: [...raw.logits.slice(i * M, (i + 1) * M)], value: raw.value[i] }));
    fs.writeFileSync(path.resolve(ROOT, DUMP_FILE), JSON.stringify({ rows }));
  }
  process.send({ stats });
}

if (process.env.WVH_WORKER) {
  process.on('message', async ({ jobs }) => { try { await worker(jobs); } catch (e) { console.error(e); process.exit(1); } process.exit(0); });
} else {
  const jobs = [];
  for (let g = G0; g < G0 + GAMES; g++) for (let i = 0; i < A.length; i++) for (const j of SUBSET) {
    if (g >= STRIDE) throw new Error('g must stay below --stride so deals do not overlap another pair\'s');
    const p = i * B.length + j;
    jobs.push({ i, j, g, seed: SEED * 1000003 + p * STRIDE + g });
  }
  if (SKIP) {
    const done = new Set(fs.readFileSync(path.resolve(ROOT, SKIP), 'utf8').split('\n').filter(Boolean)
      .map(l => JSON.parse(l)).map(r => `${r.i},${r.j},${r.g}`));
    const before = jobs.length;
    jobs.splice(0, jobs.length, ...jobs.filter(x => !done.has(`${x.i},${x.j},${x.g}`)));
    console.log(`--skip ${SKIP}: ${before - jobs.length} games already played, ${jobs.length} left`);
  }
  const nW = DUMP ? 1 : WORKERS;
  const shards = [...Array(nW)].map((_, w) => jobs.filter((_, k) => k % nW === w).map(j => ({ ...j, w })));
  const t0 = Date.now();
  const rows = [];
  const allStats = [];
  const outStream = OUT ? fs.createWriteStream(path.resolve(ROOT, OUT), { flags: 'w' }) : null;
  console.log(`${A_AGENT} on ${A.length} A decks vs ${B_AGENT} on ${SUBSET.length} B decks, games ${G0}..${G0 + GAMES - 1} a pair: ${jobs.length} games, ${nW} workers x ${CONC}`);
  let lastPrint = 0;
  Promise.all(shards.map(sh => new Promise((resolve, reject) => {
    const child = fork(__filename, argv, { env: { ...process.env, WVH_WORKER: '1' } });
    child.on('message', m => {
      if (m.row) {
        rows.push(m.row);
        if (outStream) outStream.write(JSON.stringify(m.row) + '\n');
        if (Date.now() - lastPrint > 60000) {
          lastPrint = Date.now();
          const sc = rows.reduce((a, r) => a + r.aScore, 0) / rows.length;
          console.log(`  ${rows.length}/${jobs.length} games, ${((Date.now() - t0) / 60000).toFixed(1)} min, A's score so far ${sc.toFixed(3)}`);
        }
      }
      if (m.stats) { allStats.push(m.stats); resolve(); }
    });
    child.on('exit', code => { if (code !== 0) reject(new Error('worker exited ' + code)); });
    child.send({ jobs: sh });
  }))).then(() => {
    if (outStream) outStream.end();
    const n = rows.length, sc = rows.reduce((a, r) => a + r.aScore, 0) / Math.max(n, 1);
    const ci = 1.96 * Math.sqrt(sc * (1 - sc) / Math.max(n, 1));
    const end = {};
    for (const r of rows) { const k = r.ending || 'none'; end[k] = end[k] || [0, 0, 0]; end[k][r.aScore === 1 ? 0 : r.aScore === 0 ? 1 : 2]++; }
    const st = allStats.reduce((a, s) => ({ searches: a.searches + s.searches, changed: a.changed + s.changed, searchMs: a.searchMs + s.searchMs,
      da: a.da + s.decisions.a, db: a.db + s.decisions.b }), { searches: 0, changed: 0, searchMs: 0, da: 0, db: 0 });
    console.log(`done: ${n} games in ${((Date.now() - t0) / 60000).toFixed(1)} min, errors ${rows.filter(r => r.error).length}`);
    console.log(`A's score ${sc.toFixed(3)} +- ${ci.toFixed(3)} (per-game binomial)`);
    console.log('endings [A wins, B wins, other]:', JSON.stringify(end));
    console.log('decisions A/B', st.da, st.db, st.searches ? `searches ${st.searches}, overruled the pilot ${(100 * st.changed / st.searches).toFixed(1)}%, mean ${(st.searchMs / st.searches).toFixed(0)} ms` : '');
    for (const r of rows.filter(r => r.error).slice(0, 5)) console.log('  ERROR', r.error);
    if (OUT) fs.writeFileSync(path.resolve(ROOT, OUT.replace(/\.jsonl$/, '') + '.summary.json'), JSON.stringify({ a: A_AGENT, b: B_AGENT,
      seed: SEED, stride: STRIDE, g0: G0, games: GAMES, subset: SUBSET, n, score: sc, ci95: ci, endings: end, stats: st, minutes: (Date.now() - t0) / 60000 }, null, 1));
  }).catch(e => { console.error(e); process.exitCode = 1; });
}
