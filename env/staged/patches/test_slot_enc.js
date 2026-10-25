// Checks of slot_enc.patch (per-seat token encoder options, "slotEnc"; env/env.js seatEnc, env/runner.js, env/remote_worker.js), CPU only:
//   (a) jobs without seatEnc: every observation and every game result equals the tree without this patch (BASE_ENV), on fixed
//       seeds, for the encoder options history 3 / chain 4 with canon 0 and canon 1
//   (b) mixed games through env/runner.js with job.seatEnc: at every decision the seat's observation equals a fresh encoder
//       with that seat's options on the same state; canon seats carry no PICKED token, non-canon seats do when picks exist;
//       chain-K seats keep their chain rows in the last K rows of the candidate array and nothing in front of them
// Run (after card_latent.patch, card_state.patch and slot_enc.patch are applied to the tree ENV_DIR points at; BASE_ENV is the
// tree with the first two only; both need the ryuu-play and node_modules junctions):
//   ENV_DIR=<tree>/env BASE_ENV=<base tree>/env node test_slot_enc.js [--games 30]
'use strict';
const path = require('path');
const crypto = require('crypto');
const ENV = path.resolve(process.env.ENV_DIR || path.join(__dirname, '..', '..'));
const BASE = process.env.BASE_ENV ? path.resolve(process.env.BASE_ENV) : null;
const argv = process.argv.slice(2);
const GAMES = argv.includes('--games') ? Number(argv[argv.indexOf('--games') + 1]) : 30;
const fails = [];
const fail = m => { if (fails.length < 40) fails.push(m); };
const FIELDS = ['tokCard', 'tokKind', 'tokAux', 'glob', 'slots', 'cand'];
class Lcg { constructor(s) { this.s = s >>> 0; } next(n) { this.s = (Math.imul(this.s, 1664525) + 1013904223) >>> 0; return (this.s >>> 8) % n; } }

const load = dir => ({ Runner: require(path.join(dir, 'runner.js')).Runner, TokenEncoder: require(path.join(dir, 'tokens.js')).TokenEncoder,
                       KIND: require(path.join(dir, 'tokens.js')).KIND, decks: require(path.join(dir, 'decks.js')).archivedDecks() });
const T = load(ENV);
const jobsFor = (n, seatEnc) => Array.from({ length: n }, (_, g) => ({
  deckA: T.decks[(g * 5 + 1) % T.decks.length].cards, deckB: T.decks[(g * 11 + 3) % T.decks.length].cards,
  deckName: 'a' + g, deckBName: 'b' + g, seed: 700 + g, seats: { 1: 'x', 2: 'y' }, ...(seatEnc ? { seatEnc: seatEnc(g) } : {}) }));

// Runs the jobs with two random agents (x is player 1, y player 2); onItem(agent, item) sees each decision. -> { digest, results }
async function play(M, opts, jobs, onItem) {
  const enc = new M.TokenEncoder();
  Object.assign(enc, opts);
  const hash = crypto.createHash('sha1');
  const mk = name => {
    const rng = new Lcg(name === 'x' ? 11 : 29);
    return { slot: name === 'x' ? 0 : 1, act: batch => Promise.resolve(batch.map(b => {
      for (const f of FIELDS) hash.update(Buffer.from(b.obs[f].buffer));
      hash.update(String(b.obs.nTok) + ',' + b.obs.nCand + ';');
      if (onItem) onItem(name, b);
      return { action: b.legal[rng.next(b.legal.length)], logp: 0, value: 0 };
    })) };
  };
  let k = 0;
  const run = await new M.Runner(enc, { concurrency: 8 }).run(() => (k < jobs.length ? jobs[k++] : null), { x: mk('x'), y: mk('y') });
  const results = run.results.map(r => [r.seed, r.winner, r.ending, r.turns, r.steps, r.error || ''].join('|')).sort();
  return { digest: hash.digest('hex'), results };
}

(async () => {
  // (a) no seatEnc: equal to the tree without this patch
  if (BASE) {
    const B = load(BASE);
    for (const canon of [0, 1]) {
      const o = { history: 3, chain: 4, canon };
      const p = await play(T, o, jobsFor(GAMES)), b = await play(B, o, jobsFor(GAMES));
      const same = p.digest === b.digest, sameR = JSON.stringify(p.results) === JSON.stringify(b.results);
      console.log(`(a) canon=${canon}: ${p.results.length} games, observations ${same ? 'identical' : 'DIFFER'} (sha1 ${p.digest.slice(0, 12)}), results ${sameR ? 'identical' : 'DIFFER'}`);
      if (!same || !sameR) fail(`(a) canon=${canon}: patched tree differs from the base tree without seatEnc`);
    }
  } else console.log('(a) skipped: BASE_ENV not set');

  // (b) mixed seats
  const MIXES = {
    'canon vs plain (chain 4, history 3)': [{ canon: 1, chain: 0, history: 0 }, { canon: 0, chain: 4, history: 3 }],
    'canon+chain 4 vs plain+history 3': [{ canon: 1, chain: 4, history: 0 }, { canon: 0, chain: 0, history: 3 }],
    'chain 2 vs chain 4 (both plain)': [{ canon: 0, chain: 2, history: 0 }, { canon: 0, chain: 4, history: 3 }],
  };
  const ref = new Map();
  const fresh = o => { const k = JSON.stringify(o); if (!ref.has(k)) { const e = new T.TokenEncoder(); Object.assign(e, o); ref.set(k, e); } return ref.get(k); };
  for (const [name, [oa, ob]] of Object.entries(MIXES)) for (const flip of [0, 1]) {
    const opt = { x: flip ? ob : oa, y: flip ? oa : ob };
    const st = { n: 0, picked: { x: 0, y: 0 }, pickedSeen: 0, chainRows: { x: 0, y: 0 }, flags: { x: 0, y: 0 } };
    const wrong = (seat, msg) => fail(`(b) ${name}${flip ? ' flipped' : ''}: seat ${seat} ${msg}`);
    // the runner's own encoder starts on options no seat uses, so only seatEnc can produce the expected encodings
    const p = await play(T, { history: 9, chain: 1, canon: 0 }, jobsFor(GAMES, () => ({ 1: opt.x, 2: opt.y })), (seat, b) => {
      const o = opt[seat], pid = b.env.current.playerId, g = b.env.game;
      const want = fresh(o).encode(g, pid, b.env.visibleDecks(pid), b.env.current.options);
      st.n++;
      for (const f of FIELDS) if (Buffer.compare(Buffer.from(b.obs[f].buffer), Buffer.from(want[f].buffer)) !== 0) { wrong(seat, `field ${f} differs from a fresh encoder`); return; }
      if (b.obs.nTok !== want.nTok || b.obs.nCand !== want.nCand) wrong(seat, 'nTok / nCand differ');
      let picked = 0, flagged = 0;
      for (let i = 0; i < b.obs.nTok; i++) {
        if (b.obs.tokKind[i] === T.KIND.PICKED) picked++;
        if (o.canon && b.obs.tokKind[i] >= T.KIND.HAND && b.obs.tokKind[i] <= T.KIND.PICKED && (b.obs.tokAux[i] & 224)) flagged++;
      }
      if (o.canon && picked) wrong(seat, 'canon seat has a PICKED token');
      st.picked[seat] += picked; st.flags[seat] += flagged;
      if (!o.canon && picked) st.pickedSeen++;
      for (let r = 0; r < 128; r++) {
        const nz = b.obs.cand.subarray(r * 6, r * 6 + 6).some(v => v !== 0);
        if (r >= 128 - o.chain) { if (nz) st.chainRows[seat]++; }
        else if (r >= b.obs.nCand && nz) wrong(seat, `candidate row ${r} set outside the options and the last ${o.chain} rows`);
      }
    });
    if (!st.n) fail(`(b) ${name}: no decisions`);
    if (opt.x.canon !== opt.y.canon) {
      const cn = opt.x.canon ? 'x' : 'y';
      if (!st.pickedSeen) fail(`(b) ${name}: the non-canon seat never had a PICKED token (no picks seen)`);
      if (!st.flags[cn]) fail(`(b) ${name}: the canon seat never carried a flag`);
    }
    for (const s of ['x', 'y']) if (opt[s].chain && !st.chainRows[s]) fail(`(b) ${name}: chain seat ${s} never had a chain row`);
    console.log(`(b) ${name}${flip ? ' (seats flipped)' : ''}: ${st.n} decisions equal a fresh per-seat encoder; PICKED tokens x/y ${st.picked.x}/${st.picked.y};`
      + ` canon flags x/y ${st.flags.x}/${st.flags.y}; chain rows set x/y ${st.chainRows.x}/${st.chainRows.y}; ${p.results.length} games`);
  }
  if (fails.length) { console.log('FAIL', fails); process.exit(1); }
  console.log('ALL PASS');
})().catch(e => { console.log('ERROR', e && e.stack || e); process.exit(1); });
