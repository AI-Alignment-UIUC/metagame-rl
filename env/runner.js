// Plays many games at once with any agents in the seats, batching each agent's decisions
// across games so a network runs one inference call per batch rather than per decision.
//
//   const runner = new Runner(encoder, { concurrency: 32 });
//   const out = await runner.run(nextJob, agents, { record: new Set(['learner']) });
//
// nextJob(recorded, rec) returns { deckA, deckB, seed, seats: { 1: agentName, 2: agentName } } or null when
// no more games should start. Decisions with one option are played without asking anyone.
// For the agents named in `record`, every decision is kept for training: the observation
// (bytes), the action id, its log-probability and value estimate, the legal ids, and at each
// seat's last decision of a game the reward (+1 win, -1 loss, 0 draw or cut off), and the model
// slot of the agent that decided (-1 for agents without one; rl/league.py maps slots to agents), and whether the
// action was sampled from the policy (1) or its top option (0; mostly greedy collection, log #81).
'use strict';
const { Env } = require('./env.js');

class Runner {
  // deckoutWin: the reward for a win by deck-out (a win by prizes or knockout is 1), so a pilot
  // can be paid less for stalling than for taking prizes. Losses are -1 either way.
  // valueAtTurn: if set, each result also has valueAt { 1, 2 }: the value each seat's agent gave
  // at its first decision on or after that game turn (null if the game ended first).
  // maxTurns: every new deal ends as a draw at that turn limit (env/game.js; 0 none, log #140).
  // roundTurns: every new deal is played under the 2000 round rule (env/game.js, log #160), cut at T, a number, or at T
  // drawn per deal from a..b by its seed for [a, b]; rewards are then the event's points (Game.reward) and each result
  // carries its roundT.
  constructor(encoder, { concurrency = 32, showOpponentDecklist = true, deckoutWin = 1, valueAtTurn = 0, maxTurns = 0,
                         roundTurns = 0 } = {}) {
    this.encoder = encoder;
    this.maxTurns = maxTurns;
    this.roundTurns = roundTurns;
    this.deckoutWin = deckoutWin;
    this.valueAtTurn = valueAtTurn;
    this.concurrency = concurrency;
    this.showOpponentDecklist = showOpponentDecklist;
  }

  // onDecision(slot, answer, k), if given, sees every asked decision before it is played (the state is still the
  // one decided in): answer is the agent's { action, logp, value }, k its index in rec (-1 if not recorded).
  // A job with fromGame (a function returning a Game, e.g. a clone) starts from that game instead of a new deal,
  // with decklists { 1, 2 }; with first (an option key) that option is played before any agent is asked
  // (env/remote_worker.js qprobe). A job's tag is copied to its result. A job with untilTurnEnd stops at its first asked
  // decision once the game turn has advanced `horizon` turns (default 1: after the turn it started in; env/remote_worker.js
  // tsearch, logs #96, #103): its result has no winner and stopped { player, value }, the deciding player there and the
  // agent's value for it.
  async run(nextJob, agents, { record = new Set(), onDecision = null } = {}) {
    const rt = this.roundTurns;
    const roundT = seed => {                // the deal's cut under the round rule: fixed, or drawn from a..b by the seed
      if (!Array.isArray(rt)) return rt || 0;
      const h = Math.imul((seed % 0x7fffffff) ^ 0x5bd1e995, 0x9e3779b1) >>> 0;
      return rt[0] + h % (rt[1] - rt[0] + 1);
    };
    const enc = this.encoder;
    const rec = { obs: [], action: [], logp: [], value: [], reward: [], done: [], traj: [], legal: [], slot: [], sampled: [] };
    const results = [];
    const slots = [];
    let jobCount = 0, forced = 0, engineMoves = 0, fallbacks = 0;

    const start = job => {
      const env = new Env(enc, { u8: true, showOpponentDecklist: this.showOpponentDecklist });
      let t;
      let turn0;
      if (job.fromGame) {
        env.game = job.fromGame();
        env.decklists = job.decklists;
        turn0 = env.game.state.turn;
        t = env.observe();
        if (job.first !== undefined && !t.done) {
          const j = env.current.options.findIndex(o => o.key === job.first);
          if (j === -1) { env.game.error = new Error('option ' + job.first + ' not on offer in the copy'); t = env.observe(); }
          else t = env.step(env.current.legal[j]);
        }
      } else {
        const usesEngine = [1, 2].some(s => agents[job.seats[s]].engine);
        t = env.reset(job.deckA, job.deckB, job.seed, { backup: usesEngine, maxTurns: this.maxTurns, roundTurns: roundT(job.seed) });
      }
      return { job, env, t, id: jobCount++, last: { 1: -1, 2: -1 }, valueAt: { 1: null, 2: null }, turn0, stopped: null };
    };
    const fill = () => {
      while (slots.length < this.concurrency) {
        const job = nextJob(rec.action.length, rec);
        if (!job) break;
        slots.push(start(job));
      }
    };
    const finish = slot => {
      const w = slot.stopped ? slot.t.winner : slot.env.game.winner;
      for (const seat of [1, 2]) {
        const i = slot.last[seat];
        if (i === -1) continue;
        rec.done[i] = 1;
        rec.reward[i] = slot.stopped ? 0 : slot.env.game.reward(seat, this.deckoutWin);
      }
      for (const a of Object.values(agents)) if (a.forget) a.forget(slot.env.game);
      const left = seat => {             // prizes a seat still has to take at the end (rl/metagame.py margin)
        const p = slot.env.game.state.players.find(q => q.id === seat);
        return p ? p.prizes.reduce((a, z) => a + z.cards.length, 0) : 0;
      };
      results.push({ id: slot.id, seats: slot.job.seats, decks: [slot.job.deckName, slot.job.deckBName], seed: slot.job.seed,
        winner: w, ending: slot.env.game.ending, turns: slot.env.game.state.turn, prizesLeft: { 1: left(1), 2: left(2) },
        ...(slot.job.tag !== undefined ? { tag: slot.job.tag } : {}), ...(slot.stopped ? { stopped: slot.stopped } : {}),
        ...(this.valueAtTurn ? { valueAt: slot.valueAt } : {}), ...(this.roundTurns ? { roundT: slot.env.game.roundTurns } : {}), steps: slot.t.steps, error: slot.t.error ? String(slot.t.error.message || slot.t.error) : undefined });
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
      // Ask every agent at once: with central GPU inference each agent (learner, league snapshots)
      // is a separate request, and awaiting them one by one cost a round trip per agent per step,
      // which is why collection slowed from 7 s to 55 s an iteration as snapshots were added.
      const groups = [...byAgent];
      const outs = await Promise.all(groups.map(([name, group]) =>
        agents[name].act(group.map(s => ({ obs: s.t.obs, legal: s.t.legal, env: s.env })))));
      for (let gi = 0; gi < groups.length; gi++) {
        const [name, group] = groups[gi];
        const out = outs[gi];
        const keep = record.has(name);
        group.forEach((s, i) => {
          if (s.job.untilTurnEnd && s.env.game.state.turn >= s.turn0 + (s.job.horizon || 1)) {   // horizon turns over: stop
            s.stopped = { player: s.t.playerId, value: out[i].value };
            return;
          }
          if (this.valueAtTurn && s.valueAt[s.t.playerId] === null && s.env.game.state.turn >= this.valueAtTurn) {
            s.valueAt[s.t.playerId] = out[i].value;
          }
          if (onDecision) onDecision(s, out[i], keep ? rec.action.length : -1);
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
            rec.slot.push(agents[name].slot ?? -1);
            rec.sampled.push(out[i].sampled ?? 1);
            s.last[s.t.playerId] = k;
          }
          s.t = s.env.step(out[i].action);
        });
      }
      // Retire finished games and start new ones.
      for (let i = slots.length - 1; i >= 0; i--) {
        if (slots[i].t.done || slots[i].stopped) { finish(slots[i]); slots.splice(i, 1); }
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
  // Observations are byte vectors (identity encoder) or objects of fixed-size typed arrays
  // (token encoder); each token field becomes its own section, obs.<field>.
  const obsArrays = [];
  if (T > 0 && !(rec.obs[0] instanceof Uint8Array)) {
    for (const k of ['tokCard', 'tokKind', 'tokAux', 'glob', 'slots', 'cand']) {
      const w = rec.obs[0][k].length, Ctor = rec.obs[0][k].constructor;
      const all = new Ctor(T * w);
      rec.obs.forEach((o, i) => all.set(o[k], i * w));
      obsArrays.push(['obs.' + k, Ctor === Int16Array ? 'int16' : 'uint8', all]);
    }
    obsArrays.push(['obs.nCand', 'int32', Int32Array.from(rec.obs.map(o => o.nCand))]);
  }
  const obs = obsArrays.length ? new Uint8Array(0) : new Uint8Array(T * obsSize);
  if (!obsArrays.length) rec.obs.forEach((o, i) => obs.set(o, i * obsSize));
  const offsets = new Int32Array(T + 1);
  const ids = new Int32Array(L);
  let p = 0;
  rec.legal.forEach((l, i) => { offsets[i] = p; ids.set(l, p); p += l.length; });
  offsets[T] = p;
  arrays.push(['obs', 'uint8', obs], ['action', 'int32', Int32Array.from(rec.action)],
    ['logp', 'float32', Float32Array.from(rec.logp)], ['value', 'float32', Float32Array.from(rec.value)],
    ['reward', 'float32', Float32Array.from(rec.reward)], ['done', 'uint8', Uint8Array.from(rec.done)],
    ['traj', 'int32', Int32Array.from(rec.traj)], ['legal_offsets', 'int32', offsets], ['legal_ids', 'int32', ids], ...obsArrays);
  if (rec.slot && rec.slot.length === T) arrays.push(['slot', 'int32', Int32Array.from(rec.slot)]);
  if (rec.sampled && rec.sampled.length === T) arrays.push(['sampled', 'uint8', Uint8Array.from(rec.sampled)]);
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
