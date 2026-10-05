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
  constructor(session, obsSize, actionSize, { seed = 0, greedy = false } = {}) {
    this.session = session;
    this.obsSize = obsSize;
    this.actionSize = actionSize;
    this.rng = new Rng(seed);
    this.greedy = greedy;
  }

  static async load(file, obsSize, actionSize, opts) {
    const ort = require('onnxruntime-node');
    const session = await ort.InferenceSession.create(file, { intraOpNumThreads: 1, interOpNumThreads: 1 });
    return new OnnxAgent(session, obsSize, actionSize, opts);
  }

  async act(batch) {
    const ort = require('onnxruntime-node');
    const n = batch.length;
    const x = new Uint8Array(n * this.obsSize);
    batch.forEach((b, i) => x.set(b.obs, i * this.obsSize));
    const out = await this.session.run({ obs: new ort.Tensor('uint8', x, [n, this.obsSize]) });
    const logits = out.logits.data, value = out.value.data;
    return batch.map((b, i) => {
      const s = sampleMasked(logits, i * this.actionSize, b.legal, this.rng, this.greedy);
      return { action: s.action, logp: s.logp, value: value[i] };
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

module.exports = { OnnxAgent, RandomAgent, FirstAgent, HeuristicAgent, SimpleBotAgent, sampleMasked };

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
