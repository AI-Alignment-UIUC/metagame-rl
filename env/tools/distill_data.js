// Supervised dataset for checking a policy architecture (A4.2): an identity-encoded teacher
// (an ONNX checkpoint) plays itself over all archived deck pairs, with a share of random moves
// so the states are varied. At every decision with more than one option it records the state
// in both encodings, the teacher's greedy choice (the label) and the deciding player's final
// result (+1 / -1 / 0). Two rollout files with the same rows: <out>.tok.bin (token observations,
// actions = option indices) and <out>.id.bin (identity observations, actions = action ids).
// Also reports how often the token encoding can't tell two options of a decision apart, and how
// often states overflow the token or candidate limits.
//
// Run: node env/tools/distill_data.js --teacher runs/a4/model_it00249.onnx --games 500 --seed 1 --out runs/distill/d0
'use strict';
const fs = require('fs');
const { Env } = require('../env.js');
const { Encoder } = require('../encode.js');
const { TokenEncoder } = require('../tokens.js');
const { OnnxAgent, RandomAgent } = require('../agents.js');
const { archivedDecks } = require('../decks.js');
const { packRollout } = require('../runner.js');
const { Rng } = require('../rng.js');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const TEACHER = flag('teacher', 'runs/a4/model_it00249.onnx');
const GAMES = Number(flag('games', 200));
const SEED = Number(flag('seed', 1));
const EPS = Number(flag('eps', 0.1));
const OUT = flag('out', 'runs/distill/d');

(async () => {
  const decks = archivedDecks();
  const enc = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
  const tok = new TokenEncoder();
  const teacher = await OnnxAgent.load(TEACHER, enc.obsSize, enc.actionSize, { seed: SEED, greedy: true, reencode: enc });
  const rnd = new RandomAgent({ seed: SEED + 1 });
  const rng = new Rng(SEED + 2);
  const recT = { obs: [], action: [], logp: [], value: [], reward: [], done: [], traj: [], legal: [] };
  const recI = { obs: [], action: [], logp: [], value: [], reward: [], done: [], traj: [], legal: [] };
  const stats = { decisions: 0, ambiguous: 0, ambiguousLabel: 0, tokOverflow: 0, candOverflow: 0, maxTok: 0, maxCand: 0, cut: 0 };
  for (let g = 0; g < GAMES; g++) {
    const k = SEED * 100003 + g;
    const a = decks[k % decks.length], b = decks[Math.floor(k / decks.length) % decks.length];
    const env = new Env(tok, { u8: true });
    let t = env.reset(a.cards, b.cards, k);
    const rows = [];
    while (!t.done) {
      if (t.legal.length === 1) { t = env.step(t.legal[0]); continue; }
      const { game, current } = env;
      const batch = [{ obs: t.obs, legal: t.legal, env }];
      const label = (await teacher.act(batch))[0].action;              // option index
      const idLegal = current.options.map(o => enc.actionId(o.key));
      // Can the token encoding tell this decision's options apart?
      const seen = new Map();
      let amb = false, ambLabel = false;
      for (let i = 0; i < t.obs.nCand; i++) {
        const key = t.obs.cand.slice(6 * i, 6 * i + 6).join(',');
        if (seen.has(key)) { amb = true; if (i === label || seen.get(key) === label) ambLabel = true; } else seen.set(key, i);
      }
      stats.decisions++;
      if (amb) stats.ambiguous++;
      if (ambLabel) stats.ambiguousLabel++;
      if (t.obs.overflow && t.obs.nTok >= tok.MAX_TOK) stats.tokOverflow++;
      if (current.options.length > tok.MAX_CAND) stats.candOverflow++;
      stats.maxTok = Math.max(stats.maxTok, t.obs.nTok);
      stats.maxCand = Math.max(stats.maxCand, current.options.length);
      if (label < tok.MAX_CAND) {
        rows.push({ player: t.playerId,
          tok: { obs: t.obs, legal: t.legal.slice(0, tok.MAX_CAND), action: label },
          id: { obs: enc.encodeU8(game, current.playerId, env.visibleDecks(current.playerId)), legal: idLegal, action: idLegal[label] } });
      }
      const play = rng.float() < EPS ? (await rnd.act(batch))[0].action : label;
      t = env.step(play);
    }
    if (t.winner !== 1 && t.winner !== 2) stats.cut++;
    for (const r of rows) {
      const z = t.winner === r.player ? 1 : (t.winner === 1 || t.winner === 2) ? -1 : 0;
      for (const [rec, x] of [[recT, r.tok], [recI, r.id]]) {
        rec.obs.push(x.obs); rec.action.push(x.action); rec.legal.push(x.legal); rec.traj.push(g);
        rec.reward.push(z); rec.logp.push(0); rec.value.push(0); rec.done.push(0);
      }
    }
  }
  fs.writeFileSync(OUT + '.tok.bin', packRollout(recT, 0, { kind: 'distill-tokens', seed: SEED }));
  fs.writeFileSync(OUT + '.id.bin', packRollout(recI, enc.obsSize, { kind: 'distill-identity', seed: SEED, actionSize: enc.actionSize }));
  console.log(JSON.stringify({ games: GAMES, rows: recT.action.length, ...stats }));
  process.exit(0);
})();
