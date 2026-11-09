// C136 (runs/probe/C136-pp-price-search/record.md): C114's log-only trace (pace_worker2.js, and env/remote_worker.js beneath it)
// for C111's list-against-copy pairs, plus two log-only additions:
//   - search copies (Game.prototype.clone) get _pdone, which the trace hook skips, so PolicySearchAgent's simulated lines write no
//     trace rows (C132's guard; C122's own trace run had none);
//   - one JSON line per attack (either seat) to $C136_B10 with C135's b10 fields: base (after the Defender's W and R), PlusPower
//     attached (pp) and in hand (ppHand), Defender, the Defender's HP left before, ko, and b10state (the attack without this turn's
//     PlusPower, max(0, base - 20 x Defender), would leave exactly 10). Only the list's seat can hold PlusPower (its copy has none).
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Game } = require(path.join(ENV, 'game.js'));
const { Env } = require(path.join(ENV, 'env.js'));
const OUT = process.env.C136_B10;

const origClone = Game.prototype.clone;
Game.prototype.clone = function (...a) { const g = origClone.apply(this, a); g._pdone = true; g._bpSkip = true; return g; };
const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._c136seed = seed; return t; };

const bare = n => String(n).replace(/ [A-Z0-9]+$/, '');
const leftOf = s => { const c = s.getPokemonCard(); return c ? c.hp - s.damage : null; };
const count = (slot, name) => slot.trainers.cards.filter(c => bare(c.name) === name).length;
function hook(g) {
  const orig = g.store.reduceEffect;
  g.store.reduceEffect = function (state, effect) {
    const cap = g._bpCap;
    if (cap && effect.type === 'PUT_DAMAGE_EFFECT' && effect.target === cap.target && cap.base === null) cap.base = effect.baseDamage;
    return orig.call(this, state, effect);
  };
}
const origDispatch = Game.prototype.dispatch;
Game.prototype.dispatch = function (action) {
  if (!OUT || this._bpSkip || !action || action.type !== 'ATTACK_ACTION') return origDispatch.call(this, action);
  if (!this._bpHooked) { this._bpHooked = true; hook(this); }
  const st = this.state, me = st.players[st.activePlayer], opp = st.players.find(p => p !== me);
  const dc = opp.active.getPokemonCard(), left0 = leftOf(opp.active);
  const pp = count(me.active, 'PlusPower'), df = count(opp.active, 'Defender');
  const ppHand = me.hand.cards.filter(c => bare(c.name) === 'PlusPower').length;
  this._bpCap = { target: opp.active, base: null };
  const r = origDispatch.call(this, action);
  const base = this._bpCap.base; this._bpCap = null;
  const ko = opp.active.getPokemonCard() !== dc && opp.discard.cards.includes(dc);
  fs.appendFileSync(OUT, JSON.stringify({ seed: this._c136seed, turn: st.turn, p: me.id, dc: dc ? dc.fullName : null, base, pp, ppHand, df,
    left0, ko, b10state: base > 0 && left0 - Math.max(0, base - 20 * df) === 10 }) + '\n');
  return r;
};

require('./pace_worker2.js');
