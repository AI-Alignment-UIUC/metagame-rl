// A rollout worker for rl/train.py (the training bridge, plan item A1.5).
//
// Reads one JSON command per line on stdin and answers one JSON line on stdout:
//   { "cmd": "collect", "model": "<policy.onnx>", "transitions": 20000, "out": "<file>",
//     "seed": 1, "concurrency": 32, "matchups": [[deckA, deckB], ...],
//     "opponents": [{ "spec": "self" | "random" | "first" | "onnx:<file>", "weight": 1 }] }
//   -> { "ok": true, "out": "<file>", "transitions": n, "games": n, "results": [...] }
//   { "cmd": "quit" }
//
// Each game draws a matchup (deck names as in env/decks.js, substring match) and an opponent;
// the learner takes a random seat. With "self" both seats are the learner and both are
// recorded. Games already started when the transition budget is reached are played out.
'use strict';
const readline = require('readline');
const fs = require('fs');
const { Encoder } = require('./encode.js');
const { Runner, packRollout } = require('./runner.js');
const { archivedDecks } = require('./decks.js');
const { OnnxAgent, RandomAgent, FirstAgent } = require('./agents.js');
const { Rng } = require('./rng.js');

const decks = archivedDecks();
const encoder = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
const deckByName = name => {
  const d = decks.find(x => x.name === name) || decks.find(x => x.name.toLowerCase().includes(name.toLowerCase()));
  if (!d) throw new Error('no archived deck matches ' + name);
  return d;
};
const sessions = new Map();
async function onnx(file, seed) {
  if (!sessions.has(file)) sessions.set(file, await OnnxAgent.load(file, encoder.obsSize, encoder.actionSize, { seed }));
  const a = sessions.get(file);
  return new OnnxAgent(a.session, encoder.obsSize, encoder.actionSize, { seed });
}

async function collect(cmd) {
  const t0 = Date.now();
  const rng = new Rng(cmd.seed);
  const learner = await onnx(cmd.model, cmd.seed);
  const agents = { learner };
  const opponents = [];
  for (const [i, o] of (cmd.opponents || [{ spec: 'self', weight: 1 }]).entries()) {
    const name = 'opp' + i;
    if (o.spec === 'self') opponents.push({ name: 'learner', weight: o.weight });
    else {
      agents[name] = o.spec === 'random' ? new RandomAgent({ seed: cmd.seed + i })
        : o.spec === 'first' ? new FirstAgent()
        : await onnx(o.spec.replace(/^onnx:/, ''), cmd.seed + 17 * i);
      opponents.push({ name, weight: o.weight });
    }
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
    // The learner's deck is the first of the matchup pair; flip pairs in the config for both directions.
    const [deckA, deckB] = learnerSeat === 1 ? [da, db] : [db, da];
    return { deckA: deckA.cards, deckB: deckB.cards, deckName: deckA.name, deckBName: deckB.name, seed: cmd.seed * 100003 + n++, seats };
  };
  const runner = new Runner(encoder, { concurrency: cmd.concurrency || 32, deckoutWin: cmd.deckoutWin ?? 1 });
  const out = await runner.run(nextJob, agents, { record: new Set(['learner']) });
  fs.writeFileSync(cmd.out, packRollout(out.rec, encoder.obsSize, { actionSize: encoder.actionSize }));
  const results = out.results.map(r => ({ winner: r.winner, ending: r.ending, seats: r.seats, decks: r.decks, steps: r.steps, error: r.error }));
  return { ok: true, out: cmd.out, transitions: out.rec.action.length, games: out.stats.games, forced: out.stats.forced,
    seconds: (Date.now() - t0) / 1000, results };
}

const rl = readline.createInterface({ input: process.stdin });
let queue = Promise.resolve();
rl.on('line', line => {
  queue = queue.then(async () => {
    let msg;
    try {
      msg = JSON.parse(line);
      if (msg.cmd === 'quit') { process.exit(0); }
      if (msg.cmd === 'info') {
        process.stdout.write(JSON.stringify({ ok: true, obsSize: encoder.obsSize, actionSize: encoder.actionSize, decks: decks.map(d => d.name) }) + '\n');
        return;
      }
      if (msg.cmd === 'collect') { process.stdout.write(JSON.stringify(await collect(msg)) + '\n'); return; }
      throw new Error('unknown command ' + msg.cmd);
    } catch (e) {
      process.stdout.write(JSON.stringify({ ok: false, error: String(e && e.stack || e) }) + '\n');
    }
  });
});
