// C134 (runs/probe/C134-breakpoints/record.md): env/remote_worker.js unchanged (required below), plus a LOG-ONLY wrapper on
// Game.prototype.dispatch for attacks. One JSON line per attack to $BP_OUT (unset: off). Search copies (Game.clone) are skipped.
// Per attack: the seed, game turn, attacker and attack; the engine's own base damage to the Defending Pokemon (the first
// PutDamageEffect on it during the attack, effect.baseDamage: after the Defender's Weakness and Resistance, before PlusPower and
// Defender, as pluspower.ts reads it) and raw, the attack's damage before Weakness and Resistance ((base - R) / W, exact for
// base > 0); the Defender's
// HP left before and after (null after if it left the Active: ko true when it went to the discard), its Weakness hit, PlusPower on
// the attacker (pp) and Defender on the Defender (df); and each benched opposing Pokemon's HP left with d10, the damage this attack
// would do it with one more PlusPower: max(0, raw x its Weakness + its Resistance) + 10 x (pp + 1), the engine's order (PlusPower after
// Weakness and Resistance, ryuu-play set-base/pluspower.ts). Logging only; no game changes.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Game } = require(path.join(ENV, 'game.js'));
const { Env } = require(path.join(ENV, 'env.js'));
const OUT = process.env.BP_OUT;

const origReset = Env.prototype.reset;               // the seed of each game (Game does not keep it)
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };
const origClone = Game.prototype.clone;
Game.prototype.clone = function (...a) { const g = origClone.apply(this, a); g._bpSkip = true; return g; };

const bare = n => String(n).replace(/ [A-Z0-9]+$/, '');
const leftOf = s => { const c = s.getPokemonCard(); return c ? c.hp - s.damage : null; };
const wr = (atk, dc) => {                             // Weakness and Resistance of dc against atk: [mult, mod, weakHit]
  let mult = 1, mod = 0, hit = false;
  for (const w of dc.weakness || []) if (atk.cardTypes.includes(w.type)) { hit = true; if (w.value === undefined) mult *= 2; else mod += w.value; }
  for (const r of dc.resistance || []) if (atk.cardTypes.includes(r.type)) mod += r.value;
  return [mult, mod, hit];
};
const count = (slot, name) => slot.trainers.cards.filter(c => bare(c.name) === name).length;

function hook(g) {
  const orig = g.store.reduceEffect;
  g.store.reduceEffect = function (state, effect) {
    const cap = g._bpCap;
    if (cap && effect.type === 'PUT_DAMAGE_EFFECT' && effect.target === cap.target && cap.base === null) {
      cap.base = effect.baseDamage === undefined ? effect.damage : effect.baseDamage;
      cap.first = effect.damage;
    }
    return orig.call(this, state, effect);
  };
}

const origDispatch = Game.prototype.dispatch;
Game.prototype.dispatch = function (action) {
  if (!OUT || this._bpSkip || !action || action.type !== 'ATTACK_ACTION') return origDispatch.call(this, action);
  if (!this._bpHooked) { this._bpHooked = true; hook(this); }
  const st = this.state, me = st.players[st.activePlayer], opp = st.players.find(p => p !== me);
  const atk = me.active.getPokemonCard(), dc = opp.active.getPokemonCard();
  const pre = { card: dc, left: leftOf(opp.active) };
  const pp = count(me.active, 'PlusPower'), df = count(opp.active, 'Defender');
  const bench = opp.bench.filter(s => s.pokemons.cards.length > 0).map(s => ({ c: s.getPokemonCard().fullName, left: leftOf(s), card: s.getPokemonCard() }));
  this._bpCap = { target: opp.active, base: null, first: null };
  const r = origDispatch.call(this, action);
  const cap = this._bpCap; this._bpCap = null;
  const nowCard = opp.active.getPokemonCard();
  const same = nowCard === pre.card;
  const ko = !same && opp.discard.cards.includes(pre.card);
  const [mA, oA, weak] = atk && dc ? wr(atk, dc) : [1, 0, false];
  const base = cap.base, raw = base > 0 ? (base - oA) / mA : 0;   // base is after the Defender's W and R (#609)
  const row = {
    seed: this._seed, turn: st.turn, p: me.id, ac: atk ? atk.fullName : null, an: action.name, base, raw, first: cap.first,
    dc: dc ? dc.fullName : null, hp: dc ? dc.hp : null, left0: pre.left, left1: same ? leftOf(opp.active) : null, ko, switched: !same && !ko,
    weak, multA: mA, modA: oA, pp, df,
    bench: bench.map(b => {
      const [m, o] = wr(atk, b.card);
      return { c: b.c, left: b.left, d10: base > 0 ? Math.max(0, raw * m + o) + 10 * (pp + 1) : 0 };
    }),
  };
  fs.appendFileSync(OUT, JSON.stringify(row) + '\n');
  return r;
};

require(path.join(ENV, 'remote_worker.js'));
