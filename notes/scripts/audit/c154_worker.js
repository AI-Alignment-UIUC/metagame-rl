// C154 (runs/probe/C154-value-signal/record.md): env/remote_worker.js beneath, unchanged; this file only wraps it (log only). Every job's
// deck i is the focus seat (the command job's iSeat, read as the worker parses the command). The focus seat's decisions go through a pass-through agent around the job's own agent, which
// logs the pilot's value V (the deciding seat's, as the agent returned it) at the focus seat's first decision of its own turns 2, 3 and 4.
// At game end the engine's reward for the focus seat (env/game.js reward, the value's training target) is logged too, standing in for a
// turn the game didn't reach. One JSON line a game to $C154_OUT: { seed, i, j, focus, v: { "2", "3", "4" }, end, own }. The first
// $C154_KEEP logged states a worker also carry their encoded observation (for the acceptance's direct evaluation).
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Env } = require(path.join(ENV, 'env.js'));
const { Runner } = require(path.join(ENV, 'runner.js'));
const F = require(path.join(ENV, 'framing.js'));
const OUT = process.env.C154_OUT, KEEP = Number(process.env.C154_KEEP || 0), TURNS = [2, 3, 4];

const info = new Map();                              // game seed -> its job's focus and the log so far (a worker holds a seed once)
const cmdJobs = new Map();                           // game seed -> the command's job { i, j, iSeat } (the Runner's job lacks them)
const origRead = F.readFrames;                       // the worker parses its commands through this (the same cached module)
F.readFrames = (stream, onFrame) => origRead(stream, (type, payload) => {
  if (type === F.JSON_FRAME) {
    const msg = JSON.parse(payload.toString('utf8'));
    if (msg && msg.cmd === 'games') for (const j of msg.jobs || []) cmdJobs.set(j.seed, { i: j.i, j: j.j, iSeat: j.iSeat });
  }
  return onFrame(type, payload);
});
let kept = 0;
const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };
const origObserve = Env.prototype.observe;
Env.prototype.observe = function () {
  const t = origObserve.apply(this, arguments);
  const g = this.game, x = g && info.get(g._seed);
  if (t.done && x && !x.done) {
    x.done = true;
    if (OUT) fs.appendFileSync(OUT, JSON.stringify({ seed: g._seed, i: x.i, j: x.j, focus: x.focus, v: x.v, end: g.reward(x.focus), own: x.own,
      ...(x.obs.length ? { obs: x.obs } : {}) }) + '\n');
    info.delete(g._seed);
  }
  return t;
};

class FocusAgent {                                   // the focus seat's decisions, answered by the job's own agent
  constructor(inner) { this.inner = inner; this.slot = inner.slot; }
  async act(batch) {
    const out = await this.inner.act(batch);
    batch.forEach((b, k) => {
      const g = b.env.game, x = info.get(g._seed);
      if (!x || b.env.current.playerId !== x.focus) return;
      if (g.state.turn !== x.turn) {
        x.turn = g.state.turn;
        x.own++;
        if (TURNS.includes(x.own)) {
          x.v[x.own] = out[k].value;
          if (kept < KEEP) {
            kept++;
            const o = b.obs;
            x.obs.push({ turn: x.own, value: out[k].value, tokCard: Array.from(o.tokCard), tokKind: Array.from(o.tokKind), tokAux: Array.from(o.tokAux),
              glob: Array.from(o.glob), slots: Array.from(o.slots), cand: Array.from(o.cand), nCand: o.nCand });
          }
        }
      }
    });
    return out;
  }
}

const origRun = Runner.prototype.run;
Runner.prototype.run = function (nextJob, agents, o) {
  const wrapped = (...a) => {
    const job = nextJob(...a);
    if (!job) return job;
    const cj = cmdJobs.get(job.seed);
    if (!cj) return job;
    const focus = cj.iSeat, name = job.seats[focus];
    if (!agents['c154' + name]) agents['c154' + name] = new FocusAgent(agents[name]);
    info.set(job.seed, { i: cj.i, j: cj.j, focus, turn: -1, own: 0, v: {}, obs: [], done: false });
    job.seats = { ...job.seats, [focus]: 'c154' + name };
    return job;
  };
  return origRun.call(this, wrapped, agents, o);
};

require(path.join(ENV, 'remote_worker.js'));
