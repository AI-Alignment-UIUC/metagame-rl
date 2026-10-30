// C114 (pace probe): env/remote_worker.js unchanged (required below), plus a LOG-ONLY wrapper on Game.prototype.dispatch and the
// store's reduceEffect. dispatch is where both a pilot's option (Game.step) and SimpleBot's engine action (applyEngineAction) arrive,
// so one hook sees every seat. One JSON line per finished game goes to $PACE_TRACE_OUT (unset: the hook is off). Per own turn:
// energy attach and its target, Active payable at the start and at the end of the turn, attack/damage/KOs/Prizes, Energy the
// opponent lost to our Energy Removal / Super Energy Removal, retreats, switches (Switch, Scoop Up), evolutions, basics, Trainers, drawn.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Game } = require(path.join(ENV, 'game.js'));
const { C } = require(path.join(ENV, 'engine.js'));
const { Env } = require(path.join(ENV, 'env.js'));
const OUT = process.env.PACE_TRACE_OUT;
const origReset = Env.prototype.reset;               // the seed of each game (Game does not keep it)
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };

const prizesLeft = p => p.prizes.reduce((s, z) => s + z.cards.length, 0);
const slotsOf = p => [p.active, ...p.bench];
const attached = p => slotsOf(p).reduce((s, x) => s + x.energies.cards.length, 0);
const damaging = card => (card.attacks || []).some(a => a.damage && a.damage !== '0');
const bare = n => String(n).replace(/ [A-Z0-9]+$/, '');
const newRec = (st, me) => ({ p: me.id, t: st.turn, att: 0, attTo: null, attAtk: null, payS: null, payE: null, atk: 0, dmg: 0, kos: 0, prizes: 0,
  prizes0: prizesLeft(me), erLost: 0, retreat: 0, sw: 0, evolve: 0, basic: 0, trainers: 0, drawn: 0 });

function canPay(store, st, player, slot) {
  const card = slot.getPokemonCard();
  if (!card) return false;
  let attacks = card.attacks || [];
  if ((card.powers || []).some(p => p.name === 'Transform')) {
    const oc = st.players.find(q => q !== player).active.getPokemonCard();
    attacks = oc ? oc.attacks : [];
  }
  for (const a of attacks) {
    try {
      const cost = new C.CheckAttackCostEffect(player, a);
      store.reduceEffect(st, cost);
      const prov = new C.CheckProvidedEnergyEffect(player, slot);
      store.reduceEffect(st, prov);
      if (C.StateUtils.checkEnoughEnergy(prov.energyMap, cost.cost)) return true;
    } catch (e) { /* not priceable: not payable */ }
  }
  return false;
}

function hook(g, tr) {
  const orig = g.store.reduceEffect;
  g.store.reduceEffect = function (state, effect) {
    const cur = tr.cur;
    if (effect.type === 'ATTACK_EFFECT') { if (cur) cur.atk = 1; }
    else if (effect.type === 'PUT_DAMAGE_EFFECT') {
      const r = orig.call(this, state, effect);
      if (cur && effect.target === effect.opponent.active) cur.dmg += Math.max(0, effect.damage);
      return r;
    } else if (effect.type === 'KNOCK_OUT_EFFECT') {
      const r = orig.call(this, state, effect);
      if (cur) cur.kos++;
      return r;
    }
    return orig.call(this, state, effect);
  };
}

function closeRec(st, tr) {
  const cur = tr.cur;
  if (!cur) return;
  cur.prizes = cur.prizes0 - prizesLeft(st.players.find(p => p.id === cur.p));
  delete cur.prizes0;
  tr.turns.push(cur);
  tr.cur = null;
}

// open the record of the turn in progress (and close the last one) if the turn number moved
function ensure(game, tr) {
  const st = game.state;
  if (st.phase !== C.GamePhase.PLAYER_TURN || (tr.cur && tr.cur.t === st.turn)) return;
  closeRec(st, tr);
  const me = st.players[st.activePlayer];
  tr.cur = newRec(st, me);
  tr.cur.payS = canPay(game.store, st, me, me.active);
}

const origDispatch = Game.prototype.dispatch;
Game.prototype.dispatch = function (action) {
  if (!OUT || this._pdone) return origDispatch.call(this, action);
  const st = this.state;
  const tr = this._ptr || (this._ptr = { cur: null, turns: [], pending: false });
  if (!this._phooked) { this._phooked = true; hook(this, tr); }
  ensure(this, tr);
  const cur = tr.cur;
  let me = null, opp = null;
  if (cur) {
    me = st.players[st.activePlayer]; opp = st.players.find(q => q !== me);
    const type = action.type;
    if (type === 'PLAY_CARD_ACTION') {
      const card = me.hand.cards[action.handIndex];
      const st_ = card && card.superType;
      tr.pending = false;
      if (st_ === C.SuperType.ENERGY) {
        const t = action.target, slot = t.slot === C.SlotType.ACTIVE ? me.active : me.bench[t.index];
        const pc = slot && slot.getPokemonCard();
        cur.att++; cur.attTo = t.slot === C.SlotType.ACTIVE ? 'active' : 'bench'; cur.attAtk = !!(pc && damaging(pc));
      } else if (st_ === C.SuperType.POKEMON) {
        if (card.stage === C.Stage.BASIC) cur.basic++; else cur.evolve++;
      } else if (st_ === C.SuperType.TRAINER) {
        const n = bare(card.name);
        cur.trainers++;
        if (n === 'Switch' || n === 'Scoop Up') cur.sw++;
        if (n === 'Energy Removal' || n === 'Super Energy Removal') tr.pending = true;
      }
    } else {
      if (type !== 'RESOLVE_PROMPT') tr.pending = false;
      if (type === 'RETREAT_ACTION') cur.retreat++;
      if (type === 'ATTACK_ACTION' || type === 'PASS_TURN' || (type === 'USE_ABILITY_ACTION' && action.name === 'Transform')) cur.payE = canPay(this.store, st, me, me.active);
    }
  }
  const live = st.phase === C.GamePhase.PLAYER_TURN, oppBefore = opp ? attached(opp) : 0, decks = {};
  for (const q of st.players) decks[q.id] = q.deck.cards.length;
  const r = origDispatch.call(this, action);
  if (cur && tr.pending && opp) cur.erLost += Math.max(0, oppBefore - attached(opp));
  if (!this.done) {
    ensure(this, tr);
    const o = tr.cur, owner = o && st.players.find(q => q.id === o.p);
    if (o && live) o.drawn += Math.max(0, decks[owner.id] - owner.deck.cards.length);   // this dispatch's draws, for the turn owner
  } else if (!this._pdone) {
    this._pdone = true;
    closeRec(st, tr);
    const left = id => prizesLeft(st.players.find(p => p.id === id));
    fs.appendFileSync(OUT, JSON.stringify({ seed: this._seed, ending: this.ending, winner: this.winner, turn: st.turn,
      prizesLeft: { 1: left(1), 2: left(2) }, error: this.error ? String(this.error.message || this.error) : null, turns: tr.turns }) + '\n');
  }
  return r;
};

require(path.join(ENV, 'remote_worker.js'));
