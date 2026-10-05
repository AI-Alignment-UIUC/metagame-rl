// Policies that can sit in a seat, behind one interface:
//
//   agent.act(batch) -> Promise<[{ action, logp, value }]>     batch: [{ obs, legal, env }]
//
//   OnnxAgent    a policy network exported from rl/model.py (masked softmax over the legal ids)
//   RandomAgent  uniform over the legal ids
//   FirstAgent   always the first option (a cheap deterministic baseline)
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

module.exports = { OnnxAgent, RandomAgent, FirstAgent, SimpleBotAgent, sampleMasked };
