// C173 (runs/probe/C173-search-table/record.md; stage A): env/remote_worker.js unchanged, plus a LOG-ONLY wrapper on Game.prototype.dispatch, one JSON line to $C173_OUT per: an action while the acting player's Active is Paralyzed (as audit/c172_worker.js), and an attack by a Pokemon named in
// C173_NAMES (Tauros, Lickitung, Kangaskhan, Snorlax by default), with the attack's name and whether its Active was on the deck's own side. Search copies are skipped; nothing else changes.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Game } = require(path.join(ENV, 'game.js'));
const { Env } = require(path.join(ENV, 'env.js'));
const OUT = process.env.C173_OUT;
const NAMES = new Set((process.env.C173_NAMES || 'Tauros,Lickitung,Kangaskhan,Snorlax').split(','));

const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };
const origClone = Game.prototype.clone;
Game.prototype.clone = function (...x) { const g = origClone.apply(this, x); g._c173Skip = true; return g; };
const has = (hand, name) => hand.cards.some(c => c.name === name);

const origDispatch = Game.prototype.dispatch;
Game.prototype.dispatch = function (action) {
  if (OUT && !this._c173Skip && action && this.state && this.state.players && this.state.players.length === 2) {
    const me = this.state.players[this.state.activePlayer];
    if (me && me.active) {
      if ((me.active.specialConditions || []).includes(0)) {
        const cardName = action.handIndex !== undefined && me.hand.cards[action.handIndex] ? me.hand.cards[action.handIndex].name : null;
        fs.appendFileSync(OUT, JSON.stringify({ kind: 'paralyzed', seed: this._seed, turn: this.state.turn, type: action.type, card: cardName, fullHeal: has(me.hand, 'Full Heal'), sw: has(me.hand, 'Switch') }) + '\n');
      }
      const atk = me.active.getPokemonCard();
      if (action.type === 'ATTACK_ACTION' && atk && NAMES.has(atk.name)) fs.appendFileSync(OUT, JSON.stringify({ kind: 'attack', ac: atk.name, an: action.name }) + '\n');
    }
  }
  return origDispatch.call(this, action);
};

require(path.join(ENV, 'remote_worker.js'));
