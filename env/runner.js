// Plays many games at once with any agents in the seats, batching each agent's decisions
// across games so a network runs one inference call per batch rather than per decision.
//
//   const runner = new Runner(encoder, { concurrency: 32 });
//   const out = await runner.run(nextJob, agents, { record: new Set(['learner']) });
//
// nextJob() returns { deckA, deckB, seed, seats: { 1: agentName, 2: agentName } } or null when
// no more games should start. Decisions with one option are played without asking anyone.
// For the agents named in `record`, every decision is kept for training: the observation
// (bytes), the action id, its log-probability and value estimate, the legal ids, and at each
// seat's last decision of a game the reward (+1 win, -1 loss, 0 draw or cut off).
'use strict';
const { Env } = require('./env.js');

class Runner {
  constructor(encoder, { concurrency = 32, showOpponentDecklist = true } = {}) {
    this.encoder = encoder;
    this.concurrency = concurrency;
    this.showOpponentDecklist = showOpponentDecklist;
  }

  async run(nextJob, agents, { record = new Set() } = {}) {
    const enc = this.encoder;
    const rec = { obs: [], action: [], logp: [], value: [], reward: [], done: [], traj: [], legal: [] };
    const results = [];
    const slots = [];
    let jobCount = 0, forced = 0, engineMoves = 0, fallbacks = 0;

    const start = job => {
      const env = new Env(enc, { u8: true, showOpponentDecklist: this.showOpponentDecklist });
      const usesEngine = [1, 2].some(s => agents[job.seats[s]].engine);
      const t = env.reset(job.deckA, job.deckB, job.seed, { backup: usesEngine });
      return { job, env, t, id: jobCount++, last: { 1: -1, 2: -1 } };
    };
    const fill = () => {
      while (slots.length < this.concurrency) {
        const job = nextJob(rec.action.length);
        if (!job) break;
        slots.push(start(job));
      }
    };
    const finish = slot => {
      const w = slot.t.winner;
      for (const seat of [1, 2]) {
        const i = slot.last[seat];
        if (i === -1) continue;
        rec.done[i] = 1;
        rec.reward[i] = w === seat ? 1 : (w === 1 || w === 2) ? -1 : 0;
      }
      for (const a of Object.values(agents)) if (a.forget) a.forget(slot.env.game);
      results.push({ seats: slot.job.seats, decks: [slot.job.deckName, slot.job.deckBName], seed: slot.job.seed,
        winner: w, steps: slot.t.steps, error: slot.t.error ? String(slot.t.error.message || slot.t.error) : undefined });
    };

    fill();
    while (slots.length > 0) {
      // Play forced moves and engine-driven seats without batching.
      for (const s of slots) {
        while (!s.t.done) {
          const agent = agents[s.job.seats[s.t.playerId]];
          if (agent.engine) {
            const action = agent.actEngine(s.env.game, s.t.playerId, s.env.decklists[s.t.playerId]);
            engineMoves++;
            if (action) { s.env.game.applyEngineAction(action); s.t = s.env.observe(); }
            else { fallbacks++; s.t = s.env.step(s.t.legal[0]); }
          } else if (s.t.legal.length === 1) {
            forced++;
            s.t = s.env.step(s.t.legal[0]);
          } else break;
        }
      }
      // Batch the remaining decisions by agent.
      const byAgent = new Map();
      for (const s of slots) {
        if (s.t.done) continue;
        const name = s.job.seats[s.t.playerId];
        if (!byAgent.has(name)) byAgent.set(name, []);
        byAgent.get(name).push(s);
      }
      for (const [name, group] of byAgent) {
        const out = await agents[name].act(group.map(s => ({ obs: s.t.obs, legal: s.t.legal, env: s.env })));
        const keep = record.has(name);
        group.forEach((s, i) => {
          if (keep) {
            const k = rec.action.length;
            rec.obs.push(s.t.obs);
            rec.action.push(out[i].action);
            rec.logp.push(out[i].logp);
            rec.value.push(out[i].value);
            rec.reward.push(0);
            rec.done.push(0);
            rec.traj.push(s.id * 2 + s.t.playerId - 1);
            rec.legal.push(s.t.legal);
            s.last[s.t.playerId] = k;
          }
          s.t = s.env.step(out[i].action);
        });
      }
      // Retire finished games and start new ones.
      for (let i = slots.length - 1; i >= 0; i--) {
        if (slots[i].t.done) { finish(slots[i]); slots.splice(i, 1); }
      }
      fill();
    }
    return { rec, results, stats: { games: jobCount, forced, engineMoves, fallbacks } };
  }
}

// Binary rollout file for rl/rollouts.py: a JSON header, then the arrays, each padded to 8 bytes.
function packRollout(rec, obsSize, meta = {}) {
  const T = rec.action.length;
  const L = rec.legal.reduce((a, l) => a + l.length, 0);
  const arrays = [];
  const obs = new Uint8Array(T * obsSize);
  rec.obs.forEach((o, i) => obs.set(o, i * obsSize));
  const offsets = new Int32Array(T + 1);
  const ids = new Int32Array(L);
  let p = 0;
  rec.legal.forEach((l, i) => { offsets[i] = p; ids.set(l, p); p += l.length; });
  offsets[T] = p;
  arrays.push(['obs', 'uint8', obs], ['action', 'int32', Int32Array.from(rec.action)],
    ['logp', 'float32', Float32Array.from(rec.logp)], ['value', 'float32', Float32Array.from(rec.value)],
    ['reward', 'float32', Float32Array.from(rec.reward)], ['done', 'uint8', Uint8Array.from(rec.done)],
    ['traj', 'int32', Int32Array.from(rec.traj)], ['legal_offsets', 'int32', offsets], ['legal_ids', 'int32', ids]);
  const sections = [];
  let offset = 0;
  for (const [name, dtype, arr] of arrays) {
    sections.push({ name, dtype, offset, length: arr.length });
    offset += arr.byteLength + ((8 - arr.byteLength % 8) % 8);
  }
  const header = Buffer.from(JSON.stringify({ T, obsSize, sections, ...meta }), 'utf8');
  const pre = Buffer.alloc(8);
  pre.writeUInt32LE(header.length, 0);
  const headPad = Buffer.alloc((8 - header.length % 8) % 8);
  const body = [];
  for (const [, , arr] of arrays) {
    body.push(Buffer.from(arr.buffer, arr.byteOffset, arr.byteLength));
    const pad = (8 - arr.byteLength % 8) % 8;
    if (pad) body.push(Buffer.alloc(pad));
  }
  return Buffer.concat([pre, header, headPad, ...body]);
}

module.exports = { Runner, packRollout };
