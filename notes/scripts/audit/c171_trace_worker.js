// C171's trace read (runs/probe/C171-table-drafting/record.md, Amendment 1 item 4a): env/remote_worker.js unchanged, plus a LOG-ONLY wrapper on Game.prototype.dispatch for attacks, one JSON line an attack to $TRACE_OUT, search
// copies skipped. Per attack: the attacker, the attack, the first damage put on the Defending Pokemon (base, after its Weakness and Resistance, before PlusPower and Defender), HP left before and after, each side's special
// conditions before and after, the attacker's hand and deck sizes before and after. A second line kind, kind "turn", is written at each pass or attack for an Active with a condition, so conditions can be followed. No game changes.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Game } = require(path.join(ENV, 'game.js'));
const { Env } = require(path.join(ENV, 'env.js'));
const OUT = process.env.TRACE_OUT;

const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };
const origClone = Game.prototype.clone;
Game.prototype.clone = function (...x) { const g = origClone.apply(this, x); g._trSkip = true; return g; };
const left = s => { const c = s.getPokemonCard(); return c ? c.hp - s.damage : null; };
const conds = s => (s.specialConditions || []).slice();

function hook(g) {
  const orig = g.store.reduceEffect;
  g.store.reduceEffect = function (state, effect) {
    const cap = g._trCap;
    if (cap && effect.type === 'PUT_DAMAGE_EFFECT' && effect.target === cap.target && cap.base === null) {
      cap.base = effect.baseDamage === undefined ? effect.damage : effect.baseDamage;
    }
    return orig.call(this, state, effect);
  };
}

const origDispatch = Game.prototype.dispatch;
Game.prototype.dispatch = function (action) {
  if (!OUT || this._trSkip || !action || action.type !== 'ATTACK_ACTION') return origDispatch.call(this, action);
  if (!this._trHooked) { this._trHooked = true; hook(this); }
  const st = this.state, me = st.players[st.activePlayer], opp = st.players.find(p => p !== me);
  const myActive = me.active, oppActive = opp.active;
  const atk = myActive.getPokemonCard(), dc = oppActive.getPokemonCard();
  const row = { seed: this._seed, turn: st.turn, ac: atk ? atk.fullName : null, an: action.name, dc: dc ? dc.fullName : null, left0: left(oppActive), self0: left(myActive), condA0: conds(myActive), condD0: conds(oppActive),
                hand0: me.hand.cards.length, deck0: me.deck.cards.length, dmgOnAttacker0: myActive.damage };
  this._trCap = { target: oppActive, base: null };
  const r = origDispatch.call(this, action);
  const cap = this._trCap; this._trCap = null;
  const same = oppActive.getPokemonCard() === dc;
  Object.assign(row, { base: cap.base, left1: same ? left(oppActive) : null, ko: !same && opp.discard.cards.includes(dc), condA1: myActive.getPokemonCard() === atk ? conds(myActive) : null, condD1: same ? conds(oppActive) : null,
                       self1: myActive.getPokemonCard() === atk ? left(myActive) : null, hand1: me.hand.cards.length, deck1: me.deck.cards.length });
  fs.appendFileSync(OUT, JSON.stringify(row) + '\n');
  return r;
};

require(path.join(ENV, 'remote_worker.js'));
