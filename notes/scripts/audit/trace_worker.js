// Engine audit part 1 (log #484, Evan's row 102): a rollout worker with a per-turn tracer. It is env/remote_worker.js unchanged
// (required below), plus wrappers on Game.prototype.step and the game's store.reduceEffect that only READ: nothing a game does
// changes. Each finished game appends one JSON line to $AUDIT_TRACE_OUT. Started by notes/scripts/audit/trace_games.py.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Game } = require(path.join(ENV, 'game.js'));
const { Env } = require(path.join(ENV, 'env.js'));
const { C } = require(path.join(ENV, 'engine.js'));
const OUT = process.env.AUDIT_TRACE_OUT;

// the seed of each game (Game does not keep it)
const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) {
  const t = origReset.apply(this, arguments);
  this.game._seed = seed;
  return t;
};

const prizesLeft = p => p.prizes.reduce((s, z) => s + z.cards.length, 0);
const slotsOf = p => [p.active, ...p.bench];
const damageSum = p => slotsOf(p).reduce((s, x) => s + (x.pokemons.cards.length ? x.damage : 0), 0);
const newTurn = (st, player) => ({ turn: st.turn, player, atkLegal: false, tried: false, attacked: false, attack: null, dmg: 0, kos: 0, prizes: 0,
  prizes0: null, heal: 0, otherDec: 0, attach: 0, retreat: 0, evolve: 0, basic: 0, trainers: [], activeCanPay: false, anyCanPay: false, closed: false });

// Can this slot pay for any attack it (or, for an Active Ditto, the Defending Pokemon it copies) has?
function canPay(store, st, player, slot, isActive) {
  const card = slot.getPokemonCard();
  if (!card) return false;
  let attacks = card.attacks || [];
  if (isActive && (card.powers || []).some(p => p.name === 'Transform')) {
    const opp = st.players.find(q => q !== player);
    const oc = opp.active.getPokemonCard();
    attacks = oc ? oc.attacks : [];
  }
  for (const a of attacks) {
    try {
      const cost = new C.CheckAttackCostEffect(player, a);
      store.reduceEffect(st, cost);
      const prov = new C.CheckProvidedEnergyEffect(player, slot);
      store.reduceEffect(st, prov);
      if (C.StateUtils.checkEnoughEnergy(prov.energyMap, cost.cost)) return true;
    } catch (e) { /* an attack the engine cannot price counts as not payable */ }
  }
  return false;
}

function hook(g, tr) {
  const store = g.store, orig = store.reduceEffect;
  store.reduceEffect = function (state, effect) {
    const cur = tr.cur;
    switch (effect.type) {
      case 'ATTACK_EFFECT':
        if (cur) { cur.attacked = true; cur.attack = effect.attack.name; }
        tr.attacks.push({ turn: state.turn, seat: effect.player.id, attacker: effect.player.active.getPokemonCard().name, attack: effect.attack.name,
                          defender: (effect.opponent.active.getPokemonCard() || {}).name });
        break;
      case 'PUT_DAMAGE_EFFECT': {
        const r = orig.call(this, state, effect);
        if (cur && effect.target === effect.opponent.active) {
          const dmg = Math.max(0, effect.damage);
          cur.dmg += dmg;
          const last = tr.attacks[tr.attacks.length - 1];
          if (last) { last.base = effect.baseDamage; last.dmg = dmg; last.printed = effect.attack.damage; }
        }
        return r;
      }
      case 'KNOCK_OUT_EFFECT': {
        const dmg = effect.target.damage;
        const r = orig.call(this, state, effect);
        tr.kos.push({ turn: state.turn, owner: effect.player.id, prizeCount: effect.prizeCount, damage: dmg, by: cur ? cur.player : null });
        tr.koDamage[effect.player.id] = (tr.koDamage[effect.player.id] || 0) + dmg;
        if (cur) cur.kos++;
        return r;
      }
      case 'HEAL_EFFECT': {
        const before = effect.target.damage;
        const r = orig.call(this, state, effect);
        const removed = before - effect.target.damage;
        tr.healStep[effect.player.id] = (tr.healStep[effect.player.id] || 0) + removed;
        if (cur) cur.heal += removed;
        tr.healTotal += removed;
        return r;
      }
      default: break;
    }
    return orig.call(this, state, effect);
  };
}

function closeTurn(st, tr) {
  const cur = tr.cur;
  if (!cur || cur.closed) return;
  cur.closed = true;
  const me = st.players.find(p => p.id === cur.player);
  cur.prizes = cur.prizes0 - prizesLeft(me);
  tr.turns.push(cur);
}

const origStep = Game.prototype.step;
Game.prototype.step = function (i) {
  if (this.done || !OUT) return origStep.call(this, i);
  const st = this.state;
  const tr = this._tr || (this._tr = { cur: null, turns: [], kos: [], attacks: [], koDamage: {}, healStep: {}, healTotal: 0, done: false });
  if (!this._hooked) { this._hooked = true; hook(this, tr); }
  const d = this.decision();
  const opt = d && d.options[i];
  let before = null;
  if (d && opt) {
    if (!d.prompt) {
      if (!tr.cur || tr.cur.turn !== st.turn) {
        closeTurn(st, tr);
        const me = st.players.find(p => p.id === d.playerId);
        tr.cur = newTurn(st, d.playerId);
        tr.cur.prizes0 = prizesLeft(me);
      }
      const cur = tr.cur, key = opt.key, verb = key.split('|')[0];
      if (verb === 'attach') cur.attach++;
      else if (verb === 'retreat') cur.retreat++;
      else if (verb === 'evolve') cur.evolve++;
      else if (verb === 'basic') cur.basic++;
      else if (verb === 'trainer') cur.trainers.push(key.split('|')[1]);
      // the turn ends at a pass or an attack: that decision is the turn's last main-phase decision
      const isAttack = verb === 'attack' || key.startsWith('power|Transform');
      if (key === 'pass' || isAttack) {
        const me = st.players.find(p => p.id === d.playerId);
        cur.atkLegal = d.options.some(o => o.key.startsWith('attack|') || o.key.startsWith('power|Transform'));
        cur.tried = isAttack;
        cur.activeCanPay = canPay(this.store, st, me, me.active, true);
        cur.anyCanPay = cur.activeCanPay || me.bench.some(b => canPay(this.store, st, me, b, false));
      }
    }
    before = st.players.map(p => damageSum(p));
    tr.healStep = {}; tr.koDamage = {};
  }
  const r = origStep.call(this, i);
  if (before && tr.cur) {
    st.players.forEach((p, k) => {
      const dec = before[k] - damageSum(p) - (tr.healStep[p.id] || 0) - (tr.koDamage[p.id] || 0);
      if (dec > 0) tr.cur.otherDec += dec;
    });
  }
  if (this.done && !tr.done) {
    tr.done = true;
    closeTurn(st, tr);
    const left = id => prizesLeft(st.players.find(p => p.id === id));
    fs.appendFileSync(OUT, JSON.stringify({ seed: this._seed, ending: this.ending, winner: this.winner, turn: st.turn, roundT: this.roundTurns,
      prizesLeft: { 1: left(1), 2: left(2) }, error: this.error ? String(this.error.message || this.error) : null,
      turns: tr.turns, kos: tr.kos, attacks: tr.attacks, healTotal: tr.healTotal }) + '\n');
  }
  return r;
};

require(path.join(ENV, 'remote_worker.js'));
