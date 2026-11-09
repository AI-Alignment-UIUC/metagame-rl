// C133 (runs/probe/C133-scripted-rank/record.md; copy of wiggly_worker.js): C115b's scripted Wigglytuff attacker against the passive
// Goldfish, with the pilot in model slot 0 as a shadow. $C133_MODE:
//   shadow (default): the scripted move is always played; at each of its main-phase decisions with 2+ legal options the slot's top-64
//     reply (a fresh RemoteAgent with topk, built from the runner's own one) gives the scripted move's rank and probability, the
//     pilot's top-1 and V, one JSON line a decision to $C133_OUT;
//   pilot: the attacker seat is the model slot itself, played greedily (arm 0's own games on the same deals), and each of its
//     main-phase decisions with 2+ options writes the same line (rank 1, its own move), for V at the same own turns.
// Each line: seed, game turn, own turn (the attacker's turns counted from 1), key, kind, rank (null past 64), n legal, p, top1 key, v.
// The C114 trace (pace_worker2.js) still writes the games' per-turn rows to $PACE_TRACE_OUT, for the turns-to-six check.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Runner } = require(path.join(ENV, 'runner.js'));
const { GoldfishAgent } = require('./goldfish_agent.js');
const { WigglyAgent } = require('./wiggly_agent.js');
const { C } = require(path.join(ENV, 'engine.js'));

const OUT = process.env.C133_OUT, MODE = process.env.C133_MODE || 'shadow';
const TRAINERS = ['PlusPower', 'Item Finder', 'Professor Oak', 'Bill', 'Computer Search'];
const bare = n => String(n).replace(/ [A-Z0-9]+$/, '');
function kindOf(key) {
  const [k, a, b] = key.split('|');
  if (k === 'attach') return b && b.startsWith('A') ? 'attach-active' : 'attach-bench';
  if (k === 'trainer') { const n = bare(a); return 'trainer:' + (TRAINERS.includes(n) ? n : 'other'); }
  if (k === 'basic') return 'bench';
  if (k === 'pass') return 'end-turn';
  return k;                                          // evolve, attack, retreat, power, ...
}

// own turns: the attacker's player turns counted from 1 (setup excluded, as C114's trace), kept on the game
function ownTurn(b) {
  const g = b.env.game, t = g.state.turn;
  const s = g._c133 || (g._c133 = { last: -1, own: 0 });
  if (g.state.phase === C.GamePhase.PLAYER_TURN && t !== s.last) { s.last = t; s.own++; }   // setup isn't an own turn (as the trace)
  return s.own;
}
const loggable = b => !b.env.game.decision().prompt && b.legal.length >= 2;
const line = (b, a, e) => {
  const opts = b.env.current.options, top = e.top || [], lp = e.topLp || [], r = top.indexOf(a), key = opts[a].key;
  return JSON.stringify({ seed: b.env.game._seed, turn: b.env.game.state.turn, own: b.env.game._c133.own, key, kind: kindOf(key),
    rank: r >= 0 ? r + 1 : null, n: b.legal.length, p: r >= 0 && lp[r] !== undefined ? Math.exp(lp[r]) : null,
    top1: top.length ? opts[top[0]].key : null, v: e.value });
};

class Shadow {                                       // the scripted attacker, read by the pilot at each decision
  constructor(inner) { this.inner = inner; this.ask = null; this.stats = {}; }
  async act(batch) {
    batch.forEach(ownTurn);
    const acts = await this.inner.act(batch);
    const idx = batch.map((b, i) => i).filter(i => loggable(batch[i]));
    if (idx.length && OUT) {
      const ev = await this.ask.act(idx.map(i => batch[i]));
      fs.appendFileSync(OUT, idx.map((i, q) => line(batch[i], acts[i].action, ev[q])).join('\n') + '\n');
    }
    return acts;
  }
}

class Pilot {                                        // arm 0's own greedy play, its V logged at the same decisions
  constructor(ra) { this.ra = ra; this.stats = {}; }
  async act(batch) {
    batch.forEach(ownTurn);
    const acts = await this.ra.act(batch);           // greedy, with its top-64 and their log-probabilities (topk set below)
    const idx = batch.map((b, i) => i).filter(i => loggable(batch[i]));
    if (idx.length && OUT) fs.appendFileSync(OUT, idx.map(i => line(batch[i], acts[i].action, acts[i])).join('\n') + '\n');
    return acts;
  }
}

const origRun = Runner.prototype.run;
Runner.prototype.run = function (nextJob, agents, o) {
  if (!agents.goldfish) agents.goldfish = Object.assign(new GoldfishAgent(), { stats: {} });
  const wrapped = (...a) => {
    const job = nextJob(...a);
    if (!job) return job;
    const ra = Object.values(agents).find(x => x && x.constructor && x.constructor.name === 'RemoteAgent');
    if (MODE === 'pilot') {
      if (!agents.c133pilot) agents.c133pilot = new Pilot(new ra.constructor(ra.slot, ra.encoding, true, 64));
      job.seats = job.seed % 2 === 0 ? { 1: 'c133pilot', 2: 'goldfish' } : { 1: 'goldfish', 2: 'c133pilot' };
    } else {
      if (!agents.wiggly) agents.wiggly = new Shadow(new WigglyAgent());
      if (!agents.wiggly.ask) agents.wiggly.ask = new ra.constructor(ra.slot, ra.encoding, true, 64);
      job.seats = job.seed % 2 === 0 ? { 1: 'wiggly', 2: 'goldfish' } : { 1: 'goldfish', 2: 'wiggly' };
    }
    return job;
  };
  return origRun.call(this, wrapped, agents, o);
};

require('./pace_worker2.js');
