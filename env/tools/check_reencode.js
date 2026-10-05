// Check for OnnxAgent's reencode mode (an identity-encoded policy in a game with another
// encoder, e.g. against a token model): in identity-encoded games it must choose exactly what
// the plain agent chooses (same action, logp, value at every decision), and in token-encoded
// games it must answer with an option index on offer.
// Run: node env/tools/check_reencode.js <model.onnx> [--games 40]
'use strict';
const { Env } = require('../env.js');
const { Encoder } = require('../encode.js');
const { TokenEncoder } = require('../tokens.js');
const { OnnxAgent, RandomAgent } = require('../agents.js');
const { archivedDecks } = require('../decks.js');

(async () => {
  const file = process.argv[2];
  const i = process.argv.indexOf('--games');
  const GAMES = i === -1 ? 40 : Number(process.argv[i + 1]);
  const decks = archivedDecks();
  const enc = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
  const plain = await OnnxAgent.load(file, enc.obsSize, enc.actionSize, { seed: 1, greedy: true });
  const re = await OnnxAgent.load(file, enc.obsSize, enc.actionSize, { seed: 1, greedy: true, reencode: enc });
  const rnd = new RandomAgent({ seed: 5 });
  let checked = 0, mismatch = 0, tokChecked = 0, tokBad = 0;
  for (let g = 0; g < GAMES; g++) {
    const a = decks[g % decks.length], b = decks[(7 * g + 3) % decks.length];
    // Identity-encoded game: compare at every decision, then play on with a random move.
    const env = new Env(enc, { u8: true });
    let t = env.reset(a.cards, b.cards, 100 + g);
    while (!t.done) {
      const batch = [{ obs: t.obs, legal: t.legal, env }];
      const [p] = await plain.act(batch), [q] = await re.act(batch);
      checked++;
      if (p.action !== q.action || Math.abs(p.logp - q.logp) > 1e-6 || Math.abs(p.value - q.value) > 1e-6) mismatch++;
      t = env.step((await rnd.act(batch))[0].action);
    }
    // Token-encoded game: the re-encoding agent plays one side.
    const tenv = new Env(new TokenEncoder(), { u8: true });
    t = tenv.reset(a.cards, b.cards, 200 + g);
    while (!t.done) {
      const batch = [{ obs: t.obs, legal: t.legal, env: tenv }];
      let action;
      if (t.playerId === 1) { action = (await re.act(batch))[0].action; tokChecked++; if (!t.legal.includes(action)) { tokBad++; break; } }
      else action = (await rnd.act(batch))[0].action;
      t = tenv.step(action);
    }
  }
  console.log(`identity games: ${checked} decisions, ${mismatch} mismatches; token games: ${tokChecked} decisions, ${tokBad} invalid`);
  process.exit(mismatch || tokBad ? 1 : 0);
})();
