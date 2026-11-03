// C161 (runs/probe/C161-search-disagreement/record.md): every game greedy on both seats (the slot's own RemoteAgent), and at a seeded
// share $C161_P of the main-phase decisions where a Trainer play is legal (at most $C161_MAX a worker), C135's SV search
// (env/agents.js PolicySearchAgent: k 64 = every legal option, dets 2, CRN, horizon 1, V-scored, trainerOnly, seed 135) is asked on
// the same state on the side; the game still plays the greedy action. env/remote_worker.js runs beneath, unchanged (log only).
// One JSON line a searched decision to $C161_OUT: seed (the game), turn, p (the seat), legal (bare names of the Trainers with a play
// legal), greedy / search / argmax (the option keys: the game's greedy action, the search's choice, and the pilot's top option as the
// search's own base evaluation saw it). With $C161_KEEP=n the first n searched states are also kept and, after the games, searched
// again by a fresh agent built as C135's, in the same order (acceptance), one line each to $C161_OUT.accept.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Runner } = require(path.join(ENV, 'runner.js'));
const { PolicySearchAgent } = require(path.join(ENV, 'agents.js'));
const { TokenEncoder } = require(path.join(ENV, 'tokens.js'));
const { Rng } = require(path.join(ENV, 'rng.js'));
const OUT = process.env.C161_OUT, P = Number(process.env.C161_P || 1), MAX = Number(process.env.C161_MAX || 500);
const KEEP = Number(process.env.C161_KEEP || 0);

const bare = k => k.split('|')[1].replace(/ [A-Z0-9]+$/, '');
const isTr = k => k.startsWith('trainer|');

// the searcher's pilot, built from the runner's own RemoteAgent (as notes/scripts/audit/c135_worker.js does)
function pilotOf(RA, slot) {
  return { agents: new Map(), evaluate(batch, k) {
    if (!this.agents.has(k)) this.agents.set(k, new RA(slot, 'tokens', true, k));
    return this.agents.get(k).act(batch).then(out => out.map(o => ({ order: [o.action, ...(o.top || []).filter(a => a !== o.action)], best: o.action, value: o.value })));
  } };
}
const c135 = ra => new PolicySearchAgent(pilotOf(ra.constructor, ra.slot), new TokenEncoder(),
  { k: 64, dets: 2, maxSteps: 40, seed: 135, crn: true, horizon: 1, trainerOnly: true, includeTrainer: false, score: 'value' });

let n = 0;
const coin = new Rng(161), kept = [];
class SideSearch {
  constructor(ra) { this.ra = ra; this.slot = ra.slot; this.ps = c135(ra); }
  forget(g) { this.ra.forget(g); }
  async act(batch) {
    const out = await this.ra.act(batch);                          // the game's greedy actions
    const pick = [];
    batch.forEach((b, i) => {
      if (n + pick.length >= MAX || b.env.game.decision().prompt || b.legal.length < 2) return;
      if (!b.legal.some(a => isTr(b.env.current.options[a].key))) return;
      if (coin.float() < P) pick.push(i);
    });
    if (!pick.length) return out;
    n += pick.length;
    const sub = pick.map(i => batch[i]);
    const base = await this.ps.pilot.evaluate(sub, 64);             // the pilot's argmax on these states
    const kc = kept.length < KEEP ? sub.slice(0, KEEP - kept.length).map(b => ({ game: b.env.game.clone(), decklists: b.env.decklists,
      show: b.env.showOpponentDecklist })) : [];
    const s = await this.ps.act(sub);
    const lines = sub.map((b, q) => {
      const opts = b.env.current.options, i = pick[q];
      return JSON.stringify({ seed: b.env.game._seed, turn: b.env.game.state.turn, p: b.env.current.playerId,
        legal: [...new Set(b.legal.map(a => opts[a].key).filter(isTr).map(bare))],
        greedy: opts[out[i].action].key, search: opts[s[q].action].key, argmax: opts[base[q].best].key });
    });
    kc.forEach((k, q) => kept.push({ ...k, search: JSON.parse(lines[q]).search }));
    fs.appendFileSync(OUT, lines.join('\n') + '\n');
    return out;
  }
}

const { Env } = require(path.join(ENV, 'env.js'));
const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };

const origRun = Runner.prototype.run;
Runner.prototype.run = async function (nextJob, agents, o) {
  const wrapped = (...a) => {
    const job = nextJob(...a);
    if (!job) return job;
    const name = job.seats[1];                                       // both seats: the slot's RemoteAgent, one pilot
    if (!agents.c161) agents.c161 = new SideSearch(agents[name]);
    job.seats = { 1: 'c161', 2: 'c161' };
    return job;
  };
  const res = await origRun.call(this, wrapped, agents, o);
  if (kept.length && agents.c161) {                                  // acceptance: a fresh C135 agent on the kept states, in order
    const fresh = c135(agents.c161.ra), enc = new TokenEncoder();
    const items = kept.map(k => { const env = new Env(enc, { showOpponentDecklist: k.show }); env.game = k.game; env.decklists = k.decklists;
      const t = env.observe(); return { obs: t.obs, legal: t.legal, env }; });
    const again = await fresh.act(items);
    fs.appendFileSync(OUT + '.accept', items.map((b, q) => JSON.stringify({ first: kept[q].search,
      again: b.env.current.options[again[q].action].key })).join('\n') + '\n');
    kept.length = 0;
  }
  return res;
};

require(path.join(ENV, 'remote_worker.js'));
