// C149 stage 1's acceptance (runs/probe/C149-mirror-update/record.md): field H with the pilot in model slot 0 on both seats, one seat
// (seat 1 on an even seed, seat 2 on an odd one) designated. At the designated seat's main-phase decisions where "play PlusPower" and
// an attack are legal and some legal attack, played on an exact clone, leaves the opposing Active at exactly 10 HP (a b10 state), the
// afterstate search (env/agents.js PolicySearchAgent, afterstate: every legal option (k 64), dets 1, CRN, each line scored by the
// pilot's value at the first decision after the option resolves) scores every option. One JSON line a state to $C149_OUT (at most
// $C149_MAX a worker). The game always plays the pilot's greedy answer, so nothing it does changes (log only).
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Env } = require(path.join(ENV, 'env.js'));
const { Runner } = require(path.join(ENV, 'runner.js'));
const { PolicySearchAgent } = require(path.join(ENV, 'agents.js'));
const { TokenEncoder } = require(path.join(ENV, 'tokens.js'));
const OUT = process.env.C149_OUT, MAX = Number(process.env.C149_MAX || 5);

const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };

const leftOf = s => { const c = s.getPokemonCard(); return c ? c.hp - s.damage : null; };

// The key of a legal attack that, played on an exact clone, leaves the opposing Active (the same Pokemon) at exactly 10 HP, or null.
function b10(item) {
  const opts = item.env.current.options;
  for (const a of item.legal) {
    if (!opts[a].key.startsWith('attack|')) continue;
    const env = new Env(new TokenEncoder(), { showOpponentDecklist: item.env.showOpponentDecklist });
    env.game = item.env.game.clone();
    env.decklists = item.env.decklists;
    env.observe();
    const j = env.current.options.findIndex(o => o.key === opts[a].key);
    if (j < 0) continue;
    const st = env.game.state, me = st.players[st.activePlayer], opp = st.players.find(p => p !== me);
    const target = opp.active, before = target.getPokemonCard();
    env.step(j);
    if (target.getPokemonCard() === before && leftOf(target) === 10) return opts[a].key;
  }
  return null;
}

// the searcher's pilot, built from the runner's own RemoteAgent (as notes/scripts/audit/c135_worker.js)
function pilotOf(RA, slot) {
  return { agents: new Map(), evaluate(batch, k) {
    if (!this.agents.has(k)) this.agents.set(k, new RA(slot, 'tokens', true, k));
    return this.agents.get(k).act(batch).then(out => out.map(o => ({ order: [o.action, ...(o.top || []).filter(a => a !== o.action)], best: o.action, value: o.value })));
  } };
}

let found = 0;
class AcceptAgent {
  constructor(ra) {
    this.ra = ra; this.slot = ra.slot;
    this.S = new PolicySearchAgent(pilotOf(ra.constructor, ra.slot), new TokenEncoder(),
      { k: 64, dets: 1, maxSteps: 40, seed: 149, crn: true, keepLines: true, afterstate: true });
  }
  async act(batch) {
    const out = await this.ra.act(batch);
    if (!OUT || found >= MAX) return out;
    const pick = [];
    batch.forEach((b, i) => {
      if (found + pick.length >= MAX) return;
      const d = b.env.game.decision();
      if (!d || d.prompt || b.legal.length < 2) return;
      const keys = b.legal.map(a => b.env.current.options[a].key);
      if (!keys.some(k => k.startsWith('trainer|PlusPower')) || !keys.some(k => k.startsWith('attack|'))) return;
      const atk = b10(b);
      if (atk) pick.push({ i, atk });
    });
    if (!pick.length) return out;
    const res = await this.S.act(pick.map(p => batch[p.i]));
    const mean = s => { const v = (s || []).filter(x => x !== null); return v.length ? v.reduce((x, y) => x + y, 0) / v.length : null; };
    pick.forEach((p, n) => {
      const r = res[n], b = batch[p.i], opts = b.env.current.options;
      if (!r.cands) return;
      const keys = r.cands.map(a => opts[a].key), q = r.scores.map(mean);
      const greedy = opts[out[p.i].action].key, pp = keys.findIndex(k => k.startsWith('trainer|PlusPower')), gi = keys.indexOf(greedy);
      fs.appendFileSync(OUT, JSON.stringify({ seed: b.env.game._seed, turn: b.env.game.state.turn, attack: p.atk, greedy, keys, q,
        ppScore: pp >= 0 ? q[pp] : null, greedyScore: gi >= 0 ? q[gi] : null, greedyIsPP: greedy.startsWith('trainer|PlusPower'),
        options: b.legal.length, searched: keys.length, stats: this.S.stats }) + '\n');
      found++;
    });
    return out;
  }
}

const origRun = Runner.prototype.run;
Runner.prototype.run = function (nextJob, agents, o) {
  const wrapped = (...a) => {
    const job = nextJob(...a);
    if (!job) return job;
    if (!agents.c149a) agents.c149a = new AcceptAgent(agents[job.seats[1]]);
    job.seats = { ...job.seats, [job.seed % 2 === 0 ? 1 : 2]: 'c149a' };
    return job;
  };
  return origRun.call(this, wrapped, agents, o);
};

require(path.join(ENV, 'remote_worker.js'));
