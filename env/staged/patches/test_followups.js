// Checks of the followups option of env/agents.js PolicySearchAgent (env/staged/patches/followups.patch; run AFTER the
// patch is applied), with the stub pilot of env/tools/test_search.js (deterministic, no GPU or Python):
//   (a) followups absent vs { followups: 1 }: identical moves, values and per-copy scores on fixed seeds, no follow-up stats
//   (b) followups 3: every per-copy score >= the followups 1 score on the same seeds and copies (replicate 0 is greedy)
//   (c) on states where a Trainer move is searched, some prompts are answered by sampling (followupPrompts > 0)
//   (e) no per-copy n=3 score comes from a capped replicate (small maxSteps, diverged replicates made long)
//   (d) no new engine errors (lineErrors equal to the n = 1 run's, none from replicates)
// Run from the repo root: node env/staged/patches/test_followups.js [--states 30]
// (after applying the patch the file may be moved to env/tools/; set ENV_DIR to the env folder if it stays elsewhere)
'use strict';
const crypto = require('crypto');
const path = require('path');
const ENV = process.env.ENV_DIR ? path.resolve(process.env.ENV_DIR) : path.resolve(__dirname, '..', '..');
const { Env } = require(path.join(ENV, 'env.js'));
const { TokenEncoder } = require(path.join(ENV, 'tokens.js'));
const { archivedDecks } = require(path.join(ENV, 'decks.js'));
const { PolicySearchAgent, turnScore, promptScore, searchScore } = require(path.join(ENV, 'agents.js'));

const argv = process.argv.slice(2);
const NS = Number(argv.includes('--states') ? argv[argv.indexOf('--states') + 1] : 30);
const decks = archivedDecks(), enc = new TokenEncoder();
const failures = [];
const fail = msg => { if (failures.length < 30) failures.push(msg); };

const jitter = key => (crypto.createHash('md5').update(key).digest().readUInt16LE(0) % 997) / 1e5;
class StubPilot {
  async evaluate(batch) {
    return batch.map(b => {
      const g = b.env.game, d = g.decision();
      const sc = d.options.map(o => (d.prompt ? promptScore(o, d.prompt, g.state, g) : turnScore(o.key, g.state)) + jitter(o.key));
      const order = [...b.legal].sort((x, y) => sc[y] - sc[x] || x - y);
      return { order, best: order[0], value: 2 * searchScore(g, d.playerId) - 1 };
    });
  }
}
// Main-phase states with two or more options, from greedy stub games.
function states(n, every = 3) {
  const out = [];
  for (let g = 0; out.length < n && g < 60; g++) {
    const env = new Env(enc, { u8: true });
    let t = env.reset(decks[(g * 5) % decks.length].cards, decks[(g * 13 + 1) % decks.length].cards, 500 + g);
    let step = 0;
    while (!t.done && out.length < n) {
      const d = env.game.decision();
      if (!d.prompt && t.legal.length >= 2 && step++ % every === every - 1) out.push({ game: env.game.clone(), decklists: env.decklists });
      const sc = d.options.map(o => (d.prompt ? promptScore(o, d.prompt, env.game.state, env.game) : turnScore(o.key, env.game.state)) + jitter(o.key));
      let i = 0;
      for (let j = 1; j < t.legal.length; j++) if (sc[t.legal[j]] > sc[t.legal[i]]) i = j;
      t = env.step(t.legal[i]);
    }
  }
  return out;
}
function item(s) {
  const env = new Env(enc, { u8: true });
  env.game = s.game.clone();
  env.decklists = s.decklists;
  const t = env.observe();
  return { obs: t.obs, legal: t.legal, env };
}
const run = async (snaps, opts) => {
  const S = new PolicySearchAgent(new StubPilot(), enc, { k: 8, dets: 3, seed: 41, crn: true, keepLines: true, ...opts });
  const res = [];
  for (const sn of snaps) res.push((await S.act([item(sn)]))[0]);
  return { S, res };
};

async function main() {
  const snaps = states(NS);
  console.log(`${snaps.length} main-phase states`);
  const base = await run(snaps, {});
  const one = await run(snaps, { followups: 1 });
  const three = await run(snaps, { followups: 3 });

  // (a)
  let same = 0;
  base.res.forEach((x, i) => {
    const y = one.res[i];
    if (JSON.stringify(x) === JSON.stringify(y)) same++; else fail(`(a) state ${i}: absent and n=1 differ`);
  });
  if (one.S.stats.followupLines || one.S.stats.followupPrompts) fail('(a) n=1 ran follow-up lines');
  if (JSON.stringify(base.S.stats) !== JSON.stringify(one.S.stats)) fail('(a) stats differ');
  console.log(`(a) absent vs n=1: ${same}/${snaps.length} answers identical (action, value, cands, scores)`);

  // (b)
  let cells = 0, higher = 0, ok = 0;
  three.res.forEach((x, i) => {
    const y = one.res[i];
    if (JSON.stringify(x.cands) !== JSON.stringify(y.cands) || x.scores.length !== y.scores.length) return fail(`(b) state ${i}: candidates differ`);
    let good = true;
    x.scores.forEach((row, c) => {
      if (row.length !== y.scores[c].length) good = false;
      row.forEach((v, r) => {
        const w = y.scores[c][r];
        if ((v === null) !== (w === null)) { good = false; return; }
        if (v === null) return;
        cells++;
        if (v > w) higher++;
        if (v < w) good = false;
      });
    });
    if (good) ok++; else fail(`(b) state ${i}: a copy scored below its greedy line`);
  });
  console.log(`(b) n=3 vs n=1: ${ok}/${snaps.length} answers with every copy score >= greedy; ${higher}/${cells} copy scores higher`);

  // (c)
  const st = three.S.stats;
  let trainerStates = 0;
  three.res.forEach((x, i) => {
    const opts = item(snaps[i]).env.current.options;
    if (x.cands.some(a => opts[a].key.startsWith('trainer|'))) trainerStates++;
  });
  if (!(st.followupPrompts > 0)) fail('(c) no prompt was answered by sampling');
  if (!(st.followupLines > 0)) fail('(c) no replicate lines ran');
  if (st.followupLines !== 2 * st.lines) fail(`(c) followupLines ${st.followupLines} != 2 x lines ${st.lines}`);
  console.log(`(c) n=3: ${trainerStates}/${snaps.length} states search a Trainer; followupLines ${st.followupLines}, followupPrompts ${st.followupPrompts}, lines ${st.lines}`);

  // (d)
  if (three.S.stats.lineErrors !== one.S.stats.lineErrors) fail(`(d) lineErrors ${three.S.stats.lineErrors} vs ${one.S.stats.lineErrors}`);
  console.log(`(d) lineErrors n=3 ${three.S.stats.lineErrors}, n=1 ${one.S.stats.lineErrors}; capped ${three.S.stats.capped} / ${one.S.stats.capped}`);

  // (e) a replicate that diverges from the greedy answer (marked by a spy on Env.step) then avoids ending its turn
  // (no pass, no attack) where it can, so it runs long and hits a small maxSteps where its greedy line does not. The pilot's value is always +0.5, so a line that ends its turn scores -0.5:
  // an uncapped line scores +-0.5 or +-1, a capped one 0, so a 0 that replaces a nonzero greedy score can only be a
  // capped replicate that won the max.
  {
    const lastBest = new WeakMap(), marked = new WeakSet(), step0 = Env.prototype.step;
    Env.prototype.step = function (a) {   // a step right after a pilot call on this very state that is not the pilot's best
      const p = lastBest.get(this);
      if (p && p.steps === this.game.steps && p.best !== a) marked.add(this);
      return step0.call(this, a);
    };
    const stub = new StubPilot();
    const neg = { evaluate: async batch => (await stub.evaluate(batch)).map((e, i) => {
      const env = batch[i].env, opts = env.game.decision().options;
      const last = e.order.find(x => !/^(pass|attack)/.test(opts[x].key)) ?? e.best;   // the best move that keeps the turn going
      const best = marked.has(env) ? last : e.best;   // a marked line keeps its turn going, so it runs long
      lastBest.set(env, { best: e.best, steps: env.game.steps });
      return { ...e, best, value: 0.5 };
    }) };
    let bad = 0, cap1 = 0, cap3 = 0;
    try {
      for (let ms = 6; ms <= 14; ms += 2) {
        const go = async f => { const S = new PolicySearchAgent(neg, enc, { k: 8, dets: 3, seed: 41, crn: true, keepLines: true, maxSteps: ms, followups: f });
          const res = []; for (const sn of snaps) res.push((await S.act([item(sn)]))[0]); return { S, res }; };
        const e1 = await go(1), e3 = await go(3);
        cap1 += e1.S.stats.capped; cap3 += e3.S.stats.capped;
        e3.res.forEach((x, i) => x.scores.forEach((row, c) => row.forEach((v, r) => {
          const w = e1.res[i].scores[c][r];
          if (v !== null && w !== null && w !== 0 && v === 0) bad++;
        })));
      }
    } finally { Env.prototype.step = step0; }
    if (bad) fail(`(e) ${bad} copy scores taken from a capped replicate`);
    if (!(cap3 > 3 * cap1)) fail('(e) no replicate was capped beyond its greedy line, so the check is vacuous');
    console.log(`(e) maxSteps 6..14: capped n=3 ${cap3}, n=1 ${cap1}; copy scores taken from a capped replicate: ${bad}`);
  }

  if (failures.length) { console.log('FAIL\n' + failures.join('\n')); process.exit(1); }
  console.log('PASS');
}
main().catch(e => { console.error(e); process.exit(1); });
