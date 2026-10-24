// Policies that can sit in a seat, behind one interface:
//
//   agent.act(batch) -> Promise<[{ action, logp, value }]>     batch: [{ obs, legal, env }]
//
//   OnnxAgent    a policy network exported from rl/model.py (masked softmax over the legal ids)
//   RandomAgent  uniform over the legal ids
//   FirstAgent   always the first option (a cheap deterministic baseline)
//   HeuristicAgent simple rules over the option keys (set up, then attack)
//   SimpleBotAgent ryuu-play's bundled bot (an evaluation floor; it plays through the engine,
//                not through option ids, see actEngine)
'use strict';
const path = require('path');
const { Rng } = require('./rng.js');
const { RYUU, C } = require('./engine.js');

function sampleMasked(logits, offset, legal, rng, greedy) {
  let max = -Infinity;
  for (const a of legal) { const v = logits[offset + a]; if (v > max) max = v; }
  let z = 0;
  const p = new Float64Array(legal.length);
  for (let i = 0; i < legal.length; i++) { p[i] = Math.exp(logits[offset + legal[i]] - max); z += p[i]; }
  let i = 0;
  if (greedy) {
    for (let j = 1; j < legal.length; j++) if (p[j] > p[i]) i = j;
  } else {
    let u = rng.float() * z;
    for (i = 0; i < legal.length - 1; i++) { u -= p[i]; if (u <= 0) break; }
  }
  return { action: legal[i], logp: Math.log(p[i] / z) };
}

class OnnxAgent {
  // reencode: an identity Encoder for games whose Env uses another encoder (the token one, when
  // this agent plays a token model): the agent then encodes the state itself and maps the
  // options on offer to its action ids, and answers with the Env's own action (option index).
  constructor(session, obsSize, actionSize, { seed = 0, greedy = false, reencode = null } = {}) {
    this.session = session;
    this.obsSize = obsSize;
    this.actionSize = actionSize;
    this.rng = new Rng(seed);
    this.greedy = greedy;
    this.reencode = reencode;
  }

  static async load(file, obsSize, actionSize, opts) {
    const ort = require('onnxruntime-node');
    const session = await ort.InferenceSession.create(file, { intraOpNumThreads: 1, interOpNumThreads: 1 });
    return new OnnxAgent(session, obsSize, actionSize, opts);
  }

  async act(batch) {
    const ort = require('onnxruntime-node');
    const n = batch.length, enc = this.reencode;
    const x = new Uint8Array(n * this.obsSize);
    const legal = batch.map((b, i) => {
      if (!enc) { x.set(b.obs, i * this.obsSize); return b.legal; }
      const { game, current } = b.env;
      x.set(enc.encodeU8(game, current.playerId, b.env.visibleDecks(current.playerId)), i * this.obsSize);
      return current.options.map(o => enc.actionId(o.key));
    });
    const out = await this.session.run({ obs: new ort.Tensor('uint8', x, [n, this.obsSize]) });
    const logits = out.logits.data, value = out.value.data;
    return batch.map((b, i) => {
      const s = sampleMasked(logits, i * this.actionSize, legal[i], this.rng, this.greedy);
      const action = enc ? b.legal[legal[i].indexOf(s.action)] : s.action;
      return { action, logp: s.logp, value: value[i] };
    });
  }
}

// A token + pointer policy (rl/token_model.py): inputs are env/tokens.js fields, outputs one
// logit per candidate; actions are option indices.
class OnnxTokenAgent {
  constructor(session, enc, { seed = 0, greedy = false } = {}) {
    this.session = session;
    this.enc = enc;
    this.rng = new Rng(seed);
    this.greedy = greedy;
  }

  static async load(file, enc, opts) {
    const ort = require('onnxruntime-node');
    const session = await ort.InferenceSession.create(file, { intraOpNumThreads: 1, interOpNumThreads: 1 });
    return new OnnxTokenAgent(session, enc, opts);
  }

  async act(batch, raw = false) {
    const ort = require('onnxruntime-node');
    const n = batch.length, e = this.enc;
    const tc = new Int16Array(n * e.MAX_TOK), tk = new Uint8Array(n * e.MAX_TOK), ta = new Uint8Array(n * e.MAX_TOK);
    const gl = new Uint8Array(n * e.GLOB_F), sl = new Uint8Array(n * 12 * e.SLOT_F), cd = new Int16Array(n * e.MAX_CAND * 6);
    const nc = new Int32Array(n);
    batch.forEach((b, i) => {
      const o = b.obs;
      tc.set(o.tokCard, i * e.MAX_TOK); tk.set(o.tokKind, i * e.MAX_TOK); ta.set(o.tokAux, i * e.MAX_TOK);
      gl.set(o.glob, i * e.GLOB_F); sl.set(o.slots, i * 12 * e.SLOT_F); cd.set(o.cand, i * e.MAX_CAND * 6); nc[i] = o.nCand;
    });
    const out = await this.session.run({
      tok_card: new ort.Tensor('int16', tc, [n, e.MAX_TOK]), tok_kind: new ort.Tensor('uint8', tk, [n, e.MAX_TOK]),
      tok_aux: new ort.Tensor('uint8', ta, [n, e.MAX_TOK]), glob: new ort.Tensor('uint8', gl, [n, e.GLOB_F]),
      slots: new ort.Tensor('uint8', sl, [n, 12 * e.SLOT_F]), cand: new ort.Tensor('int16', cd, [n, e.MAX_CAND * 6]),
      n_cand: new ort.Tensor('int32', nc, [n]),
    });
    const logits = out.logits.data, value = out.value.data;
    if (raw) return { logits, value };
    return batch.map((b, i) => {
      const s = sampleMasked(logits, i * e.MAX_CAND, b.legal, this.rng, this.greedy);
      return { action: s.action, logp: s.logp, value: value[i] };
    });
  }

  // Per state: the legal actions in order of the policy's preference, the best one, and the value.
  async evaluate(batch) {
    const { logits, value } = await this.act(batch, true);
    const M = this.enc.MAX_CAND;
    return batch.map((b, i) => {
      const order = [...b.legal].sort((x, y) => logits[i * M + y] - logits[i * M + x]);
      return { order, best: order[0], value: value[i] };
    });
  }
}

class RandomAgent {
  constructor({ seed = 0 } = {}) { this.rng = new Rng(seed); }
  async act(batch) {
    return batch.map(b => ({ action: b.legal[this.rng.int(b.legal.length)], logp: -Math.log(b.legal.length), value: 0 }));
  }
}

class FirstAgent {
  async act(batch) { return batch.map(b => ({ action: b.legal[0], logp: 0, value: 0 })); }
}

// A cheap rule-based player over the option keys (a ladder rung between random and SimpleBot):
// set up first (attach to the Active, evolve, bench Basics, useful Trainers), then attack with
// the strongest attack, else pass. Prompts get simple defaults. Deterministic.
const DRAW_TRAINERS = new Set(['Bill', 'Professor Oak', 'Imposter Professor Oak', 'Computer Search', 'Item Finder']);
function damageOf(attack) { const m = /\d+/.exec(attack && attack.damage || ''); return m ? Number(m[0]) : 0; }

class HeuristicAgent {
  async act(batch) {
    return batch.map(b => {
      const env = b.env, game = env.game, state = game.state;
      const options = env.current.options;
      const d = game.decision();
      let best = 0, bestScore = -Infinity;
      options.forEach((o, i) => {
        const sc = d.prompt ? promptScore(o, d.prompt, state, game) : turnScore(o.key, state);
        if (sc > bestScore) { bestScore = sc; best = i; }
      });
      return { action: b.legal[best], logp: 0, value: 0 };
    });
  }
}

function turnScore(key, state) {
  const me = state.players[state.activePlayer], opp = state.players[1 - state.activePlayer];
  const [verb, a, t] = key.split('|');
  const active = me.active.getPokemonCard();
  const unmet = slot => {
    const p = slot.getPokemonCard();
    if (!p) return false;
    const have = slot.energies.cards.length;
    return p.attacks.some(x => x.cost.length > have);
  };
  switch (verb) {
    case 'attach': {
      const slot = t === 'A' ? me.active : me.bench[Number(t.slice(1))];
      return (t === 'A' ? 60 : 40) + (unmet(slot) ? 10 : -30);
    }
    case 'evolve': return 55;
    case 'basic': return me.bench.filter(b => b.pokemons.cards.length).length < 3 ? 50 : 20;
    case 'trainer': {
      const name = a.replace(/ (BS|JU|FO|TR|PR\d*)$/, '');
      if (DRAW_TRAINERS.has(name)) return me.deck.cards.length < 10 ? -5 : name === 'Professor Oak' ? (me.hand.cards.length <= 3 ? 35 : -5) : 30;
      if (name === 'PlusPower') return active && active.attacks.some(x => x.cost.length <= me.active.energies.cards.length) ? 45 : -5;
      if (/Energy Removal/.test(name)) return opp.active.energies.cards.length ? 42 : -5;
      if (/Potion|Pokemon Center/.test(name)) return me.active.damage >= 30 ? 40 : -5;
      if (name === 'Gust of Wind') return 25;
      if (name === 'Switch' || name === 'Scoop Up') return -2;
      return 20;
    }
    case 'power': return a === 'Rain Dance' ? 52 : 10;
    case 'attack': {
      const atk = active && active.attacks.find(x => x.name === a);
      return 15 + damageOf(atk) / 100;
    }
    case 'retreat': return me.active.damage >= 50 ? 12 : -10;
    case 'pass': return 0;
    default: return 1;
  }
}

function promptScore(o, prompt, state, game) {
  if (o.key === 'cancel') return -50;
  if (o.key === 'done') return game.picks.length > 0 ? 10 : -1;
  if (o.key === 'res|yes' || o.key === 'res|ok') return 5;
  if (o.key.startsWith('res|') && prompt.type === 'Choose attack') {
    const [, card, name] = o.key.split('|');
    const pc = prompt.cards.find(c => c.fullName === card);
    return 5 + damageOf(pc && pc.attacks.find(x => x.name === name)) / 100;
  }
  if (o.key.startsWith('pick|')) {
    const item = o.key.slice(5);
    if (prompt.type === 'Choose pokemon') {
      const me = state.players.find(p => p.id === prompt.playerId), opp = state.players.find(p => p.id !== prompt.playerId);
      const side = item.startsWith('o') ? opp : me;
      const code = item.replace(/^o/, '');
      const slot = code === 'A' ? side.active : side.bench[Number(code.slice(1))];
      const pc = slot && slot.getPokemonCard();
      const hpLeft = pc ? (pc.hp || 0) - slot.damage : 0;
      return item.startsWith('o') ? 20 - hpLeft / 10 : 20 + hpLeft / 10;   // own: healthiest; theirs: weakest
    }
    if (prompt.type === 'Choose cards' && prompt.message === C.GameMessage.CHOOSE_STARTING_POKEMONS) {
      const card = C.CardManager.getInstance().getCardByName(item);
      return 20 + (card && card.hp || 0) / 100;
    }
    return 15;
  }
  return 1;
}

// SimpleBot decides with the engine's own actions. It needs an engine Simulator view of the
// state (it tries candidate actions on clones), and answers whole prompts at once.
class SimpleBotAgent {
  constructor() {
    const { SimpleBot } = require(path.join(RYUU, 'packages', 'simple-bot'));
    this.bot = new SimpleBot('simple-bot');
    this.ais = new Map();
    this.engine = true;
  }

  actEngine(game, playerId, decklist) {
    const key = game;
    let ais = this.ais.get(key);
    if (!ais) { ais = new Map(); this.ais.set(key, ais); }
    let ai = ais.get(playerId);
    if (!ai) { ai = this.bot.createBotAi(playerId, decklist); ais.set(playerId, ai); }
    return ai.decodeNextAction(game.state);
  }

  forget(game) { this.ais.delete(game); }
}

module.exports = { OnnxAgent, OnnxTokenAgent, RandomAgent, FirstAgent, HeuristicAgent, SimpleBotAgent, sampleMasked };

// Flat Monte Carlo search with determinization (a fixed-budget relative scale for the ladder).
// At a main-phase decision every option is tried in `rollouts` copies of the game where the
// hidden cards are re-dealt at random, each played on by the heuristic for both players for
// `depth` turns; the option with the best mean score is played. Score: 1 / 0 for a finished
// game, otherwise 0.5 plus prize and damage differences. Prompts are answered by the heuristic.
class SearchAgent {
  constructor({ rollouts = 8, depth = 2, seed = 0 } = {}) {
    this.rollouts = rollouts;
    this.depth = depth;
    this.rng = new Rng(seed);
    this.heuristic = new HeuristicAgent();
  }

  async act(batch) {
    const out = [];
    for (const b of batch) out.push(await this.decide(b));
    return out;
  }

  async decide(b) {
    const game = b.env.game;
    const d = game.decision();
    if (d.prompt || d.options.length === 1) return (await this.heuristic.act([b]))[0];
    const me = d.playerId;
    let best = 0, bestScore = -Infinity;
    for (let i = 0; i < d.options.length; i++) {
      let total = 0;
      for (let r = 0; r < this.rollouts; r++) total += this.rollout(game, i, me);
      if (total > bestScore) { bestScore = total; best = i; }
    }
    return { action: b.legal[best], logp: 0, value: bestScore / this.rollouts };
  }

  rollout(game, optionIndex, me) {
    const g = game.clone(new Rng(this.rng.u32()), me);
    g.decision();
    g.step(optionIndex);
    const stopTurn = game.state.turn + this.depth;
    while (!g.done && g.state.turn < stopTurn) {
      const d = g.decision();
      if (!d) break;
      g.step(heuristicIndex(g, d));
    }
    return score(g, me);
  }
}

function heuristicIndex(game, d) {
  let best = 0, bestScore = -Infinity;
  d.options.forEach((o, i) => {
    const sc = d.prompt ? promptScore(o, d.prompt, game.state, game) : turnScore(o.key, game.state);
    if (sc > bestScore) { bestScore = sc; best = i; }
  });
  return best;
}

function score(game, me) {
  if (game.state.phase === C.GamePhase.FINISHED) {
    const w = game.winner;
    return w === me ? 1 : (w === 1 || w === 2) ? 0 : 0.5;
  }
  const mine = game.state.players.find(p => p.id === me), theirs = game.state.players.find(p => p.id !== me);
  const prizesLeft = p => p.prizes.reduce((a, z) => a + z.cards.length, 0);
  const damage = p => [p.active, ...p.bench].reduce((a, s) => a + s.damage, 0);
  const v = 0.5 + 0.08 * (prizesLeft(theirs) - prizesLeft(mine)) + 0.002 * (damage(theirs) - damage(mine));
  return Math.max(0, Math.min(1, v));
}

module.exports.SearchAgent = SearchAgent;
module.exports.heuristicIndex = heuristicIndex;
module.exports.turnScore = turnScore;           // env/tools/test_search.js's stub pilot (log #148)
module.exports.promptScore = promptScore;
module.exports.searchScore = score;

// Flat policy-guided search over the token pilot (log #47), a first step toward ISMCTS. At a
// main-phase decision with several options it takes the pilot's `k` most likely moves; for each,
// `dets` copies of the game are made with what the deciding player can't see re-dealt at random
// (Game.clone with a viewer), the move is played, and the pilot plays on (greedy, both seats)
// until the turn changes or the game ends. The line is scored by the result, or the pilot's value
// read from the deciding player's side; the move with the best mean wins. Prompts and single-option
// decisions are left to the pilot. Rollouts of one decision run in lockstep, one batch per step.
// horizon (log #147): a line stops once the game turn has advanced `horizon` turns (1: the end of the deciding
// player's turn; 2: after the opponent's reply, played by the same pilot).
// Batched (log #148, search-strength judging): every decision of a batch is searched at once, all their lines in one
// lockstep, so the pilot (the GPU learner through env/remote_worker.js RemotePilot) gets one request a step instead of
// one per decision; the copies' seeds are drawn decision by decision in the batch's order, as one by one, so a batch
// searches exactly as its decisions would singly. A line's items carry its env (a remote pilot keys its rows by game),
// and a line's forced moves (one option, inside the horizon) are played without asking the pilot, whose best of one
// option is that option; they still count toward maxSteps, so every line ends as it did. pilot.evaluate(batch, k) gets
// k = 0 for the lines' states, which need only the best option and the value. stats: decisions searched, how many the
// search moved off the pilot's best, lines, lines ended by an engine error, lines cut at maxSteps.
// keepLines (C49, log #169): each answer also carries cands (the options searched) and scores (per candidate, the
// score of each copy r = 0..dets-1, null where the move did not exist in that copy), paired across candidates under crn.
// crn (C03, log #162): common random numbers, the same dets re-deal seeds for every candidate of a decision, so options
// are compared on the same hidden cards and coin flips; off, every (candidate, copy) draws its own seed as before.
class PolicySearchAgent {
  constructor(pilot, enc, { k = 4, dets = 4, maxSteps = 40, seed = 0, horizon = 1, crn = false, keepLines = false } = {}) {
    this.pilot = pilot;
    this.horizon = horizon;
    this.crn = crn;
    this.keepLines = keepLines;
    this.enc = enc;
    this.k = k; this.dets = dets; this.maxSteps = maxSteps;
    this.rng = new Rng(seed);
    this.stats = { searches: 0, changed: 0, lines: 0, lineErrors: 0, capped: 0 };
  }

  async act(batch) {
    const base = await this.pilot.evaluate(batch, this.k);
    const out = new Array(batch.length), todo = [];
    for (let i = 0; i < batch.length; i++) {
      const b = batch[i], e = base[i];
      const d = b.env.game.decision();
      if (d.prompt || b.legal.length < 2) { out[i] = { action: e.best, logp: 0, value: e.value }; continue; }
      todo.push(i);
    }
    if (todo.length) {
      const res = await this.searchAll(todo.map(i => ({ b: batch[i], e: base[i] })));
      todo.forEach((i, q) => { out[i] = res[q]; });
    }
    return out;
  }

  async search(b, e) { return (await this.searchAll([{ b, e }]))[0]; }

  async searchAll(items) {
    const { Env } = require('./env.js');
    const lines = [];
    const probs = items.map(({ b, e }, pi) => {
      const me = b.env.current.playerId;
      const cands = e.order.slice(0, this.k);
      const startTurn = b.env.game.state.turn;
      // Moves are matched by key, not position: re-dealing the hidden cards can change which moves
      // exist (a search card with nothing left to find), so a copy may lack one or order them
      // differently. A move missing from a copy gets no line there.
      const keyOf = a => b.env.current.options[a].key;
      const seeds = this.crn ? Array.from({ length: this.dets }, () => this.rng.u32()) : null;
      for (const a of cands) {
        for (let r = 0; r < this.dets; r++) {
          const env = new Env(this.enc, { showOpponentDecklist: b.env.showOpponentDecklist, u8: b.env.u8 });
          env.game = b.env.game.clone(new Rng(this.crn ? seeds[r] : this.rng.u32()), me);
          env.decklists = b.env.decklists;
          const t0 = env.observe();
          const j = env.current.options.findIndex(o => o.key === keyOf(a));
          if (j === -1 || !t0.legal.includes(j)) continue;
          lines.push({ pi, a, r, env, t: env.step(j), score: null, n: 0 });
        }
      }
      return { me, cands, startTurn, best: e.best };
    });
    this.stats.searches += items.length;
    this.stats.lines += lines.length;
    const turned = l => l.env.game.state.turn - probs[l.pi].startTurn >= this.horizon;
    for (;;) {
      const ask = [];
      for (const l of lines) {
        if (l.score !== null) continue;
        while (l.n < this.maxSteps && !l.t.done && l.t.legal.length === 1 && !turned(l)) { l.t = l.env.step(l.t.legal[0]); l.n++; }
        if (l.n >= this.maxSteps) { l.score = 0; this.stats.capped++; continue; }   // still in the turn after maxSteps
        if (l.t.done) {
          const me = probs[l.pi].me;
          if (l.t.error) this.stats.lineErrors++;
          l.score = l.env.game.reward(me);        // +1 / -1 / 0, or the round rule's points (env/game.js, log #160)
          continue;
        }
        ask.push(l);
      }
      if (!ask.length) break;
      const ev = await this.pilot.evaluate(ask.map(l => ({ obs: l.t.obs, legal: l.t.legal, env: l.env })), 0);
      ask.forEach((l, i) => {
        if (turned(l)) {
          l.score = l.t.playerId === probs[l.pi].me ? ev[i].value : -ev[i].value;
        } else {
          l.t = l.env.step(ev[i].best);
          l.n++;
        }
      });
    }
    const byProb = probs.map(() => []);
    for (const l of lines) byProb[l.pi].push(l);
    return probs.map((p, pi) => {
      let best = p.cands[0], bestMean = -Infinity;
      for (const a of p.cands) {
        const s = byProb[pi].filter(l => l.a === a).map(l => l.score);
        if (!s.length) continue;
        const m = s.reduce((x, y) => x + y, 0) / s.length;
        if (m > bestMean) { bestMean = m; best = a; }
      }
      if (best !== p.best) this.stats.changed++;
      if (!this.keepLines) return { action: best, logp: 0, value: bestMean };
      const scores = p.cands.map(a => {
        const row = new Array(this.dets).fill(null);
        for (const l of byProb[pi]) if (l.a === a) row[l.r] = l.score;
        return row;
      });
      return { action: best, logp: 0, value: bestMean, cands: p.cands, scores };
    });
  }
}
module.exports.PolicySearchAgent = PolicySearchAgent;
