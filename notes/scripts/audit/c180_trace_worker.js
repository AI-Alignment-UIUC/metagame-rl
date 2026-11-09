// C180's deck-out trace (runs/probe/C180-dose-by-practice/record.md; research's after #858): env/remote_worker.js unchanged, plus LOG-ONLY wrappers on Env.reset and Env.step. Search's line copies carry no _seed, so only real games are logged. To $C180_TRACE, one JSON line each: ["T", seed, turn, player, card, deck, hand, options, hasPass] for a Trainer played, deck and hand before it; ["E", seed, turn, [[player, deck, hand, discard], ...], winner state] when a game ends.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Env } = require(path.join(ENV, 'env.js'));
const OUT = process.env.C180_TRACE;

const write = line => { try { fs.appendFileSync(OUT, JSON.stringify(line) + '\n'); } catch (e) { /* log only */ } };

const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };

const origStep = Env.prototype.step;
Env.prototype.step = function (actionId) {
  const g = this.game;
  const real = g && g._seed !== undefined;
  try {
    if (real && this.current) {
      const o = this.current.options[this.current.legal.indexOf(actionId)];
      if (o && String(o.key).startsWith('trainer|')) {
        const st = g.state;
        const p = st.players.find(q => q.id === this.current.playerId);
        write(['T', g._seed, st.turn, this.current.playerId, String(o.key).split('|')[1], p.deck.cards.length, p.hand.cards.length, this.current.options.length, this.current.options.some(q => q.key === 'pass')]);
      }
    }
  } catch (e) { /* log only */ }
  const t = origStep.apply(this, arguments);
  try {
    if (real && t && t.done) {
      const st = g.state;
      write(['E', g._seed, st.turn, st.players.map(p => [p.id, p.deck.cards.length, p.hand.cards.length, p.discard.cards.length]), t.winner === undefined ? null : t.winner]);
    }
  } catch (e) { /* log only */ }
  return t;
};

require(path.join(ENV, 'remote_worker.js'));
