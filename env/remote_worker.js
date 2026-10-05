// A rollout worker whose policies run in the learner process (rl/remote.py), on the GPU: it
// plays the games and sends each batch of decisions to the learner as a framed request
// (env/framing.js), getting actions, log-probabilities and values back.
//
// Commands (JSON frames), answered with one JSON frame each:
//   { "cmd": "info" }
//   { "cmd": "collect", "encoding": "identity" | "tokens", "transitions": 20000, "out": "<file>",
//     "seed": 1, "concurrency": 64, "matchups": [[deckA, deckB], ...],
//     "opponents": [{ "spec": "self" | "slot:<k>" | "random" | "first" | "heuristic", "weight": 1 }] }
//   { "cmd": "quit" }
// The learner is model slot 0; "slot:k" is another model the learner holds (a league snapshot).
'use strict';
const fs = require('fs');
const { Encoder } = require('./encode.js');
const { TokenEncoder } = require('./tokens.js');
const { Runner, packRollout } = require('./runner.js');
const { archivedDecks } = require('./decks.js');
const { RandomAgent, FirstAgent, HeuristicAgent } = require('./agents.js');
const { Rng } = require('./rng.js');
const F = require('./framing.js');

const decks = archivedDecks();
const identity = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
const tokens = new TokenEncoder();
const deckByName = name => {
  const d = decks.find(x => x.name === name) || decks.find(x => x.name.toLowerCase().includes(name.toLowerCase()));
  if (!d) throw new Error('no archived deck matches ' + name);
  return d;
};

const pending = new Map();
let nextId = 1;

class RemoteAgent {
  constructor(slot, encoding) { this.slot = slot; this.encoding = encoding; }

  act(batch) {
    const n = batch.length;
    const id = nextId++;
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
    arrays.push(['legal_offsets', offsets], ['legal_ids', ids]);
    F.writeFrame(process.stdout, F.REQUEST, F.packArrays({ id, slot: this.slot, n, encoding: this.encoding }, arrays));
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
  const runner = new Runner(enc, { concurrency: cmd.concurrency || 64 });
  const out = await runner.run(nextJob, agents, { record: new Set(['learner']) });
  fs.writeFileSync(cmd.out, packRollout(out.rec, enc.obsSize || 0, { encoding, actionSize: enc.actionSize || enc.MAX_CAND }));
  const results = out.results.map(r => ({ winner: r.winner, seats: r.seats, decks: r.decks, steps: r.steps, error: r.error }));
  return { ok: true, out: cmd.out, transitions: out.rec.action.length, games: out.stats.games, seconds: (Date.now() - t0) / 1000, results };
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
        F.writeJson(process.stdout, { ok: true, identity: { obsSize: identity.obsSize, actionSize: identity.actionSize },
          tokens: { maxTok: tokens.MAX_TOK, maxCand: tokens.MAX_CAND, globF: tokens.GLOB_F, slotF: tokens.SLOT_F, names: tokens.names.length } });
        return;
      }
      if (msg.cmd === 'collect') { F.writeJson(process.stdout, await collect(msg)); return; }
      throw new Error('unknown command ' + msg.cmd);
    } catch (e) {
      F.writeJson(process.stdout, { ok: false, error: String(e && e.stack || e) });
    }
  });
});
