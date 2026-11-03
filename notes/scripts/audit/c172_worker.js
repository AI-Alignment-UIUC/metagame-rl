// C172 (runs/probe/C172-offlist-names/record.md; research's addition): env/remote_worker.js unchanged, plus a LOG-ONLY wrapper on Game.prototype.dispatch. While the acting player's Active is Paralyzed, one JSON line an action to $C172_OUT: the seed, turn, action
// type and card played, and whether Full Heal or Switch is in hand. Search copies are skipped. Nothing else changes: SpecialCondition.PARALYZED is 0, and a Paralyzed Pokemon can't retreat or attack by the 2000 rules.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Game } = require(path.join(ENV, 'game.js'));
const { Env } = require(path.join(ENV, 'env.js'));
const OUT = process.env.C172_OUT;

const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };
const origClone = Game.prototype.clone;
Game.prototype.clone = function (...x) { const g = origClone.apply(this, x); g._c172Skip = true; return g; };
const has = (hand, name) => hand.cards.some(c => c.name === name);

const origDispatch = Game.prototype.dispatch;
Game.prototype.dispatch = function (action) {
  if (OUT && !this._c172Skip && action && this.state && this.state.players && this.state.players.length === 2) {
    const me = this.state.players[this.state.activePlayer];
    if (me && me.active && (me.active.specialConditions || []).includes(0)) {
      const cardName = action.handIndex !== undefined && me.hand.cards[action.handIndex] ? me.hand.cards[action.handIndex].name : null;
      fs.appendFileSync(OUT, JSON.stringify({ seed: this._seed, turn: this.state.turn, type: action.type, card: cardName, name: action.name || null, fullHeal: has(me.hand, 'Full Heal'), sw: has(me.hand, 'Switch') }) + '\n');
    }
  }
  return origDispatch.call(this, action);
};

require(path.join(ENV, 'remote_worker.js'));
