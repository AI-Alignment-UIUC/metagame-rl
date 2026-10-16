// A rollout worker whose policies run in the learner process (rl/remote.py), on the GPU: it
// plays the games and sends each batch of decisions to the learner as a framed request
// (env/framing.js), getting actions, log-probabilities and values back.
//
// Commands (JSON frames), answered with one JSON frame each:
//   { "cmd": "info" }
//   { "cmd": "collect", "encoding": "identity" | "tokens", "transitions": 20000, "out": "<file>",
//     "seed": 1, "concurrency": 64, "matchups": [[deckA, deckB], ...],
//     "opponents": [{ "spec": "self" | "slot:<k>" | "random" | "first" | "heuristic", "weight": 1 }] }
//   { "cmd": "games", "encoding": "tokens", "decks": [{ name, cards }], "greedy": true, "concurrency": 64,
//     "jobs": [{ "i": 0, "j": 1, "iSeat": 1, "seed": 7, "rec": true }], "slots": [0, 3, ...], "out": "<file>",
//     "deckoutWin": 1 }
//     each listed game once: deck i is piloted by model slot slots[i] (slot 0 in both seats without
//     "slots"); with "out", every decision of both seats of the jobs with "rec" is recorded there
//     (rl/metagame.py training games)
//   { "cmd": "qprobe", "decks", "jobs", "out", "probeP": 0.1, "maxProbes": 4, "maxOptions": 8, "rollouts": 8,
//     "seed", "concurrency", "deckoutWin", "redeal": false, "history": 0 }
//     the jobs' games recorded (both seats), plus Monte Carlo values of the options at sampled decisions (qprobe below)
//   { "cmd": "quit" }
// The learner is model slot 0; "slot:k" is another model the learner holds (a league snapshot).
'use strict';
const fs = require('fs');
const { Encoder } = require('./encode.js');
const { TokenEncoder, PRIZE_GLOB } = require('./tokens.js');
const { Runner, packRollout } = require('./runner.js');
const { archivedDecks } = require('./decks.js');
const { RandomAgent, FirstAgent, HeuristicAgent, SimpleBotAgent } = require('./agents.js');
const { Rng } = require('./rng.js');
const F = require('./framing.js');

const decks = archivedDecks();
const identity = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
const tokens = new TokenEncoder();
const deckByName = name => {
  if (typeof name === 'object') return name;   // a decklist { name, cards } (built decks, A5)
  const d = decks.find(x => x.name === name) || decks.find(x => x.name.toLowerCase().includes(name.toLowerCase()));
  if (!d) throw new Error('no archived deck matches ' + name);
  return d;
};

const pending = new Map();
let nextId = 1;
// Memory keys (log #76): each request row carries its game's uid * 2 + seat - 1, so a pilot with memory (rl/remote.py)
// can carry its state between a seat's decisions; finished games' uids go with the next request, to be dropped.
let nextGameUid = 1;
let drops = [];

class RemoteAgent {
  constructor(slot, encoding, greedy = false) { this.slot = slot; this.encoding = encoding; this.greedy = greedy; }

  forget(game) { if (game.uid) { drops.push(game.uid); game.uid = 0; } }

  act(batch) {
    const n = batch.length;
    const id = nextId++;
    const keys = new Int32Array(n);
    batch.forEach((b, i) => {
      const g = b.env.game;
      if (!g.uid) g.uid = nextGameUid++;
      keys[i] = g.uid * 2 + (b.env.current.playerId - 1);
    });
    const L = batch.reduce((a, b) => a + b.legal.length, 0);
    const offsets = new Int32Array(n + 1), ids = new Int32Array(L);
    let p = 0;
    batch.forEach((b, i) => { offsets[i] = p; ids.set(b.legal, p); p += b.legal.length; });
    offsets[n] = p;
    let arrays;
    if (this.encoding === 'tokens') {
      const e = tokens;
      const tc = new Int16Array(n * e.MAX_TOK), tk = new Uint8Array(n * e.MAX_TOK), ta = new Uint8Array(n * e.MAX_TOK);
      const gl = new Uint8Array(n * e.GLOB_F), sl = new Uint8Array(n * 12 * e.SLOT_F), cd = new Int16Array(n * e.MAX_CAND * 6);
      const nc = new Int32Array(n);
      batch.forEach((b, i) => {
        const o = b.obs;
        tc.set(o.tokCard, i * e.MAX_TOK); tk.set(o.tokKind, i * e.MAX_TOK); ta.set(o.tokAux, i * e.MAX_TOK);
        gl.set(o.glob, i * e.GLOB_F); sl.set(o.slots, i * 12 * e.SLOT_F); cd.set(o.cand, i * e.MAX_CAND * 6); nc[i] = o.nCand;
      });
      arrays = [['tok_card', tc], ['tok_kind', tk], ['tok_aux', ta], ['glob', gl], ['slots', sl], ['cand', cd], ['n_cand', nc]];
    } else {
      const O = identity.obsSize;
      const x = new Uint8Array(n * O);
      batch.forEach((b, i) => x.set(b.obs, i * O));
      arrays = [['obs', x]];
    }
    arrays.push(['legal_offsets', offsets], ['legal_ids', ids], ['keys', keys], ['drop', Int32Array.from(drops)]);
    drops = [];
    F.writeFrame(process.stdout, F.REQUEST, F.packArrays({ id, slot: this.slot, n, encoding: this.encoding, greedy: this.greedy }, arrays));
    return new Promise(resolve => pending.set(id, resolve));
  }
}

async function collect(cmd) {
  const t0 = Date.now();
  const rng = new Rng(cmd.seed);
  const encoding = cmd.encoding || 'identity';
  const enc = encoding === 'tokens' ? tokens : identity;
  const agents = { learner: new RemoteAgent(0, encoding) };
  const opponents = [];
  for (const [i, o] of (cmd.opponents || [{ spec: 'self', weight: 1 }]).entries()) {
    const name = 'opp' + i;
    if (o.spec === 'self') { opponents.push({ name: 'learner', weight: o.weight }); continue; }
    if (o.spec.startsWith('slot:')) agents[name] = new RemoteAgent(Number(o.spec.slice(5)), encoding);
    else if (o.spec === 'random') agents[name] = new RandomAgent({ seed: cmd.seed + i });
    else if (o.spec === 'first') agents[name] = new FirstAgent();
    else if (o.spec === 'heuristic') agents[name] = new HeuristicAgent();
    else if (o.spec === 'simplebot') agents[name] = new SimpleBotAgent();
    else throw new Error('unknown opponent ' + o.spec);
    opponents.push({ name, weight: o.weight });
  }
  const totalWeight = opponents.reduce((a, o) => a + o.weight, 0);
  const matchups = cmd.matchups.map(([a, b]) => [deckByName(a), deckByName(b)]);
  let n = 0;
  const nextJob = recorded => {
    if (recorded >= cmd.transitions) return null;
    const [da, db] = matchups[rng.int(matchups.length)];
    let u = rng.float() * totalWeight, opp = opponents[0];
    for (const o of opponents) { u -= o.weight; if (u <= 0) { opp = o; break; } }
    const learnerSeat = rng.int(2) + 1;
    const seats = learnerSeat === 1 ? { 1: 'learner', 2: opp.name } : { 1: opp.name, 2: 'learner' };
    const [deckA, deckB] = learnerSeat === 1 ? [da, db] : [db, da];
    return { deckA: deckA.cards, deckB: deckB.cards, deckName: deckA.name, deckBName: deckB.name, seed: cmd.seed * 100003 + n++, seats };
  };
  const runner = new Runner(enc, { concurrency: cmd.concurrency || 64, deckoutWin: cmd.deckoutWin ?? 1 });
  const out = await runner.run(nextJob, agents, { record: new Set(['learner']) });
  fs.writeFileSync(cmd.out, packRollout(out.rec, enc.obsSize || 0, { encoding, actionSize: enc.actionSize || enc.MAX_CAND }));
  const results = out.results.map(r => ({ winner: r.winner, ending: r.ending, seats: r.seats, decks: r.decks, steps: r.steps, error: r.error }));
  return { ok: true, out: cmd.out, transitions: out.rec.action.length, games: out.stats.games, seconds: (Date.now() - t0) / 1000, results };
}

// Plays the listed games and reports each one's result (rl/gpu_matrix.py, rl/metagame.py). Deck i is
// piloted by model slot cmd.slots[i], or by slot 0 in both seats. With cmd.out, both seats' decisions
// are recorded and written there.
async function games(cmd) {
  const t0 = Date.now();
  const encoding = cmd.encoding || 'tokens';
  const enc = encoding === 'tokens' ? tokens : identity;
  const agents = {};
  // A recorded seat plays as 'r<slot>', an unrecorded one as 'o<slot>': the same model slot, but only the
  // 'r' names are recorded.
  const pilot = (i, rec) => {
    const slot = cmd.slots ? cmd.slots[i] : 0;
    const name = (rec ? 'r' : 'o') + slot;
    if (!agents[name]) agents[name] = new RemoteAgent(slot, encoding, !!cmd.greedy);
    return name;
  };
  let k = 0;
  // A job with bot: "simplebot" has deck j played by SimpleBot instead of a model (pilots with memory, which have no
  // ONNX export, against SimpleBot; log #76).
  const bots = { simplebot: () => new SimpleBotAgent() };
  const nextJob = () => {
    if (k >= cmd.jobs.length) return null;
    const job = cmd.jobs[k++];
    const [ia, ib] = job.iSeat === 1 ? [job.i, job.j] : [job.j, job.i];
    const [a, b] = [cmd.decks[ia], cmd.decks[ib]];
    const rec = !!cmd.out && job.rec !== false;
    const seat = i => {
      if (!job.bot || i !== job.j) return pilot(i, rec);
      if (!agents['bot:' + job.bot]) agents['bot:' + job.bot] = bots[job.bot]();
      return 'bot:' + job.bot;
    };
    return { deckA: a.cards, deckB: b.cards, deckName: a.name, deckBName: b.name, seed: job.seed,
             seats: { 1: seat(ia), 2: seat(ib) } };
  };
  const recorded = new Set();
  for (const s of new Set(cmd.slots || [0])) recorded.add(pilot(cmd.slots ? cmd.slots.indexOf(s) : 0, true));
  const runner = new Runner(enc, { concurrency: cmd.concurrency || 64, valueAtTurn: cmd.valueAtTurn || 0, deckoutWin: cmd.deckoutWin ?? 1 });
  const out = await runner.run(nextJob, agents, { record: cmd.out ? recorded : new Set() });
  if (cmd.out) fs.writeFileSync(cmd.out, packRollout(out.rec, 0, { encoding, actionSize: enc.MAX_CAND }));
  const bySeed = new Map(cmd.jobs.map(j => [j.seed, j]));
  const results = out.results.map(r => {
    const job = bySeed.get(r.seed);
    return { i: job.i, j: job.j, iSeat: job.iSeat, seed: job.seed, winner: r.winner, ending: r.ending, turns: r.turns, valueAt: r.valueAt,
             prizesLeft: r.prizesLeft, steps: r.steps, error: r.error };
  });
  return { ok: true, games: results.length, seconds: (Date.now() - t0) / 1000, results,
           ...(cmd.out ? { out: cmd.out, transitions: out.rec.action.length } : {}) };
}

// Ground-truth action values for the credit diagnostic (notes/scripts/credit_diag.py, log #75); evaluation only.
// Phase 1 plays cmd.jobs (as `games`) with model slot 0 sampling in both seats and records every asked decision of
// both seats to cmd.out. At a main-phase decision (no prompt open) with two or more options it takes a probe with
// probability probeP, at most maxProbes a game: a copy of the game as it stands. Phase 2 plays each probed option
// `rollouts` times to the end of the game, each from a fresh copy (the hidden cards where they are, fresh
// randomness from then on), slot 0 sampling in both seats: Q^pi of the option. An option list longer than
// maxOptions is cut to the option played plus a random sample of the others. A line's result, from the deciding
// player's side, is the reward training pays (win 1, by deck-out deckoutWin, loss -1, draw or cut 0).
const LAMS = [0, 0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 1];

async function qprobe(cmd) {
  const t0 = Date.now();
  const rng = new Rng(cmd.seed);
  const deckoutWin = cmd.deckoutWin ?? 1;
  const R = cmd.rollouts || 8, maxOptions = cmd.maxOptions || 8, maxProbes = cmd.maxProbes || 4, probeP = cmd.probeP ?? 0.1;
  const agents = { r0: new RemoteAgent(0, 'tokens', false), o0: new RemoteAgent(0, 'tokens', false) };
  let k = 0;
  const nextGame = () => {
    if (k >= cmd.jobs.length) return null;
    const job = cmd.jobs[k++];
    const [ia, ib] = job.iSeat === 1 ? [job.i, job.j] : [job.j, job.i];
    const [a, b] = [cmd.decks[ia], cmd.decks[ib]];
    return { deckA: a.cards, deckB: b.cards, deckName: a.name, deckBName: b.name, seed: job.seed, seats: { 1: 'r0', 2: 'r0' } };
  };
  const probes = [], perGame = new Map();
  const onDecision = (s, ans, idx) => {
    if (idx < 0 || s.t.legal.length < 2) return;
    const d = s.env.game.decision();
    if (d.prompt || (perGame.get(s.id) || 0) >= maxProbes || rng.float() >= probeP) return;
    let copy;
    try { copy = s.env.game.clone(new Rng(1)); } catch (e) { return; }
    perGame.set(s.id, (perGame.get(s.id) || 0) + 1);
    probes.push({ k: idx, game: copy, decklists: s.env.decklists, player: s.t.playerId, turn: s.env.game.state.turn, v: ans.value,
                  steps: s.env.game.steps, keys: d.options.map(o => o.key), chosen: ans.action, gameSeed: s.job.seed });
  };
  const runner = new Runner(tokens, { concurrency: cmd.concurrency || 64, deckoutWin });
  const base = await runner.run(nextGame, agents, { record: new Set(['r0']), onDecision });
  fs.writeFileSync(cmd.out, packRollout(base.rec, 0, { encoding: 'tokens', actionSize: tokens.MAX_CAND }));

  const lines = [];
  probes.forEach((p, pi) => {
    let opts = p.keys.map((_, i) => i);
    if (opts.length > maxOptions) {
      const others = opts.filter(i => i !== p.chosen);
      const order = rng.permutation(others.length);
      opts = [p.chosen, ...order.slice(0, maxOptions - 1).map(i => others[i])].sort((x, y) => x - y);
    }
    p.probed = opts;
    p.q = opts.map(() => []);
    p.after = opts.map(() => []);
    p.sig = opts.map(() => LAMS.map(() => []));
    opts.forEach((o, oi) => {
      for (let r = 0; r < R; r++) lines.push({ pi, oi, seed: rng.u32(), vals: [] });
    });
  });
  let n = 0;
  const nextLine = () => {
    if (n >= lines.length) return null;
    const l = lines[n++];
    const p = probes[l.pi];
    // redeal: what the deciding player can't see is re-dealt in each copy (Game.clone with a viewer), so Q is the
    // option's value over the player's information set rather than the true deal.
    return { fromGame: () => p.game.clone(new Rng(l.seed), cmd.redeal ? p.player : undefined), decklists: p.decklists,
             first: p.keys[p.probed[l.oi]],
             seats: { 1: 'o0', 2: 'o0' }, seed: n, tag: [l.pi, l.oi, n - 1] };
  };
  // The probing player's values along each line: the advantage training would give the probed decision on that
  // line, GAE(lambda) from the probe's own value p.v (gamma 1, reward only at the end), for each of LAMS.
  const onLine = (s, ans) => { const l = lines[s.job.tag[2]]; if (s.t.playerId === probes[l.pi].player) l.vals.push(ans.value); };
  const roll = await runner.run(nextLine, agents, { onDecision: onLine });
  let errors = 0;
  for (const r of roll.results) {
    const [pi, oi] = r.tag;
    const p = probes[pi];
    if (r.error) errors++;
    const win = r.ending === 'deck-out' ? deckoutWin : 1;
    const z = r.winner === p.player ? win : (r.winner === 1 || r.winner === 2) ? -1 : 0;
    p.q[oi].push(z);
    p.after[oi].push(r.steps - p.steps);
    const seq = [p.v, ...lines[r.tag[2]].vals];
    LAMS.forEach((lam, li) => {
      let a = 0;
      for (let i = seq.length - 1; i >= 0; i--) a = ((i === seq.length - 1 ? z : seq[i + 1]) - seq[i]) + lam * a;
      p.sig[oi][li].push(Math.round(a * 1e4) / 1e4);
    });
  }
  const results = base.results.map(r => ({ seed: r.seed, winner: r.winner, ending: r.ending, turns: r.turns, steps: r.steps, error: r.error }));
  return { ok: true, out: cmd.out, transitions: base.rec.action.length, games: results.length, lines: lines.length, lineErrors: errors,
           seconds: (Date.now() - t0) / 1000, results,
           probes: probes.map(p => ({ k: p.k, player: p.player, turn: p.turn, steps: p.steps, nOptions: p.keys.length, chosen: p.chosen,
                                      probed: p.probed, keys: p.probed.map(i => p.keys[i]), q: p.q, after: p.after, gameSeed: p.gameSeed,
                                      v: p.v, sig: p.sig, lams: LAMS })) };
}

let queue = Promise.resolve();
F.readFrames(process.stdin, (type, payload) => {
  if (type === F.RESPONSE) {
    const { header, arrays } = F.unpackArrays(payload);
    const resolve = pending.get(header.id);
    pending.delete(header.id);
    resolve(Array.from({ length: header.n }, (_, i) => ({ action: arrays.action[i], logp: arrays.logp[i], value: arrays.value[i] })));
    return;
  }
  if (type !== F.JSON_FRAME) return;
  const msg = JSON.parse(payload.toString('utf8'));
  queue = queue.then(async () => {
    try {
      if (msg.cmd === 'quit') process.exit(0);
      if (msg.cmd === 'info') {
        F.writeJson(process.stdout, { ok: true, decks: decks.map(d => d.name), identity: { obsSize: identity.obsSize, actionSize: identity.actionSize },
          tokens: { maxTok: tokens.MAX_TOK, maxCand: tokens.MAX_CAND, globF: tokens.GLOB_F, slotF: tokens.SLOT_F, names: tokens.names.length,
                    prizeGlob: PRIZE_GLOB } });
        return;
      }
      if (msg.cmd === 'collect' || msg.cmd === 'games' || msg.cmd === 'qprobe') tokens.history = msg.history || 0;
      if (msg.cmd === 'collect') { F.writeJson(process.stdout, await collect(msg)); return; }
      if (msg.cmd === 'games') { F.writeJson(process.stdout, await games(msg)); return; }
      if (msg.cmd === 'qprobe') { F.writeJson(process.stdout, await qprobe(msg)); return; }
      throw new Error('unknown command ' + msg.cmd);
    } catch (e) {
      F.writeJson(process.stdout, { ok: false, error: String(e && e.stack || e) });
    }
  });
});
