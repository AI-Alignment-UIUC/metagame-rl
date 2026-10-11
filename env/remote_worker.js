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
//     "jobs": [{ "i": 0, "j": 1, "iSeat": 1, "seed": 7 }], "slots": [0, 3, ...] }
//     matrix rows (A5): deck i is piloted by model slot slots[i] (slot 0 in both seats without "slots")
//   { "cmd": "values", "decks": [{ name, cards }], "jobs": [{ "a": 0, "b": 1, "seed": 7, "slot": 0 }] }
//     the value model slot `slot` (default 0) gives deck a (seat 1) at its first decision of a fresh deal
//   { "cmd": "league", "transitions": 20000, "out": "<file>", "seed": 1, "concurrency": 64, "deckoutWin": 1,
//     "matches": [{ "a": { "deck": { name, cards }, "slot": 0, "record": true }, "b": { ... } }],
//     "slotQuota": { "<slot>": transitions } }   (optional: env/league_jobs.js)
//     league training games (rl/league.py): each game is a random match, seats at random, each side
//     piloted by its own model slot; only the decisions of sides with "record" are kept, so an agent
//     learns from its own matches, not from every game it is an opponent in (tokens encoding)
//   { "cmd": "quit" }
// The learner is model slot 0; "slot:k" is another model the learner holds (a league snapshot).
'use strict';
const fs = require('fs');
const { Encoder } = require('./encode.js');
const { TokenEncoder } = require('./tokens.js');
const { Runner, packRollout } = require('./runner.js');
const { archivedDecks } = require('./decks.js');
const { RandomAgent, FirstAgent, HeuristicAgent, SimpleBotAgent } = require('./agents.js');
const { Rng } = require('./rng.js');
const { makeLeagueNextJob } = require('./league_jobs.js');
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

class RemoteAgent {
  constructor(slot, encoding, greedy = false) { this.slot = slot; this.encoding = encoding; this.greedy = greedy; }

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

// Plays the listed games and reports each one's result (rl/gpu_matrix.py); nothing is recorded.
// Deck i is piloted by model slot cmd.slots[i], or by slot 0 in both seats.
async function games(cmd) {
  const t0 = Date.now();
  const encoding = cmd.encoding || 'tokens';
  const enc = encoding === 'tokens' ? tokens : identity;
  const agents = {};
  const pilot = i => {
    const slot = cmd.slots ? cmd.slots[i] : 0;
    const name = 's' + slot;
    if (!agents[name]) agents[name] = new RemoteAgent(slot, encoding, !!cmd.greedy);
    return name;
  };
  let k = 0;
  const nextJob = () => {
    if (k >= cmd.jobs.length) return null;
    const job = cmd.jobs[k++];
    const [ia, ib] = job.iSeat === 1 ? [job.i, job.j] : [job.j, job.i];
    const [a, b] = [cmd.decks[ia], cmd.decks[ib]];
    return { deckA: a.cards, deckB: b.cards, deckName: a.name, deckBName: b.name, seed: job.seed, seats: { 1: pilot(ia), 2: pilot(ib) } };
  };
  const out = await new Runner(enc, { concurrency: cmd.concurrency || 64, valueAtTurn: cmd.valueAtTurn || 0 }).run(nextJob, agents);
  const bySeed = new Map(cmd.jobs.map(j => [j.seed, j]));
  const results = out.results.map(r => {
    const job = bySeed.get(r.seed);
    return { i: job.i, j: job.j, iSeat: job.iSeat, seed: job.seed, winner: r.winner, ending: r.ending, turns: r.turns, valueAt: r.valueAt,
             steps: r.steps, error: r.error };
  });
  return { ok: true, games: results.length, seconds: (Date.now() - t0) / 1000, results };
}

async function values(cmd) {
  const { Env } = require('./env.js');
  const obs = [];
  for (const job of cmd.jobs) {
    const env = new Env(tokens, { u8: true, showOpponentDecklist: true });
    let t = env.reset(cmd.decks[job.a].cards, cmd.decks[job.b].cards, job.seed);
    while (!t.done && t.playerId !== 1) t = env.step(t.legal[0]);   // the opponent's setup, if it acts first
    obs.push(t.done ? null : { obs: t.obs, legal: t.legal });
  }
  // Read by each job's model slot; one slot's jobs go in job order (rl/gpu_matrix.py matches captured
  // states to the live jobs in that order, and allows states only with a single slot).
  const vals = obs.map(() => 0);
  const bySlot = new Map();
  cmd.jobs.forEach((job, i) => {
    if (!obs[i]) return;
    const s = job.slot || 0;
    if (!bySlot.has(s)) bySlot.set(s, []);
    bySlot.get(s).push(i);
  });
  for (const [s, idx] of bySlot) {
    const agent = new RemoteAgent(s, 'tokens', true);
    for (let c = 0; c < idx.length; c += 1024) {
      const part = idx.slice(c, c + 1024);
      const out = await agent.act(part.map(i => obs[i]));
      part.forEach((i, k) => { vals[i] = out[k].value; });
    }
  }
  return { ok: true, values: vals, live: obs.map(o => (o ? 1 : 0)) };
}

// League training games (rl/league.py): every match names each side's deck and model slot.
async function league(cmd) {
  const t0 = Date.now();
  const rng = new Rng(cmd.seed);
  // A side that records plays as 'r<slot>', one that doesn't as 'o<slot>': the same model slot (one
  // inference request stream per name), but only the 'r' names are recorded.
  const agents = {};
  const nameOf = side => (side.record ? 'r' : 'o') + side.slot;
  for (const m of cmd.matches) {
    for (const side of [m.a, m.b]) {
      if (!agents[nameOf(side)]) agents[nameOf(side)] = new RemoteAgent(side.slot, 'tokens');
    }
  }
  const record = new Set(Object.keys(agents).filter(k => k.startsWith('r')));
  const nextJob = makeLeagueNextJob(cmd, rng, nameOf);   // per-slot quotas with cmd.slotQuota (env/league_jobs.js)
  const runner = new Runner(tokens, { concurrency: cmd.concurrency || 64, deckoutWin: cmd.deckoutWin ?? 1 });
  const out = await runner.run(nextJob, agents, { record });
  fs.writeFileSync(cmd.out, packRollout(out.rec, 0, { encoding: 'tokens', actionSize: tokens.MAX_CAND }));
  const results = out.results.map(r => ({ winner: r.winner, ending: r.ending, seats: r.seats, decks: r.decks, steps: r.steps, error: r.error }));
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
        F.writeJson(process.stdout, { ok: true, decks: decks.map(d => d.name), identity: { obsSize: identity.obsSize, actionSize: identity.actionSize },
          tokens: { maxTok: tokens.MAX_TOK, maxCand: tokens.MAX_CAND, globF: tokens.GLOB_F, slotF: tokens.SLOT_F, names: tokens.names.length } });
        return;
      }
      if (msg.cmd === 'collect') { F.writeJson(process.stdout, await collect(msg)); return; }
      if (msg.cmd === 'games') { F.writeJson(process.stdout, await games(msg)); return; }
      if (msg.cmd === 'values') { F.writeJson(process.stdout, await values(msg)); return; }
      if (msg.cmd === 'league') { F.writeJson(process.stdout, await league(msg)); return; }
      throw new Error('unknown command ' + msg.cmd);
    } catch (e) {
      F.writeJson(process.stdout, { ok: false, error: String(e && e.stack || e) });
    }
  });
});
