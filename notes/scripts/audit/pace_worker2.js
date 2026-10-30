// Flow probe (follow-up to C115): C114's pace_worker.js plus more LOG-ONLY fields (hand Energy, start/Trainer draws, Oak/Bill held, attack choice
// and damage vs printed, benches, defender HP, opening hand and mulligans). Still no change to any game.
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
const POOL = {};                                      // printed damage: notes/data/cards/pool.json attacks[].damage, by card fullName and attack name
for (const c of JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'data', 'cards', 'pool.json'), 'utf8')).cards)
  if (c.attacks && c.attacks.length) POOL[c.fullName] = Object.fromEntries(c.attacks.map(a => [a.name, { d: a.damage, t: a.damageText }]));
const origReset = Env.prototype.reset;               // the seed of each game (Game does not keep it)
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };

const prizesLeft = p => p.prizes.reduce((s, z) => s + z.cards.length, 0);
const slotsOf = p => [p.active, ...p.bench];
const attached = p => slotsOf(p).reduce((s, x) => s + x.energies.cards.length, 0);
const damaging = card => (card.attacks || []).some(a => a.damage && a.damage !== '0');
const bare = n => String(n).replace(/ [A-Z0-9]+$/, '');
const isOB = c => c.superType === C.SuperType.TRAINER && ['Professor Oak', 'Bill'].includes(bare(c.name));
const nBench = p => p.bench.filter(s => s.pokemons.cards.length > 0).length;
const newRec = (st, me) => ({ p: me.id, t: st.turn, att: 0, attTo: null, attAtk: null, payS: null, payE: null, atk: 0, dmg: 0, kos: 0, prizes: 0,
  prizes0: prizesLeft(me), erLost: 0, retreat: 0, sw: 0, evolve: 0, basic: 0, trainers: 0, drawn: 0,
  hand: me.hand.cards.length, eH: me.hand.cards.filter(c => c.superType === C.SuperType.ENERGY).length,
  ob: me.hand.cards.filter(c => isOB(c)).length, obp: 0, ppP: 0, ifPP: 0, dS: null, dT: 0, dTn: {}, A: [] });

// the attacks of the Active whose cost the Energy attached covers (Transform: the Defending Pokemon's), and the card they belong to
function payList(store, st, player, slot) {
  const card = slot.getPokemonCard();
  if (!card) return { src: null, list: [] };
  let src = card, attacks = card.attacks || [];
  if ((card.powers || []).some(p => p.name === 'Transform')) {
    const oc = st.players.find(q => q !== player).active.getPokemonCard();
    src = oc; attacks = oc ? oc.attacks : [];
  }
  const list = [];
  for (const a of attacks) {
    try {
      const cost = new C.CheckAttackCostEffect(player, a);
      store.reduceEffect(st, cost);
      const prov = new C.CheckProvidedEnergyEffect(player, slot);
      store.reduceEffect(st, prov);
      if (C.StateUtils.checkEnoughEnergy(prov.energyMap, cost.cost) && !list.some(x => x.name === a.name)) list.push(a);
    } catch (e) { /* not priceable: not payable */ }
  }
  return { src, list };
}
const canPay = (store, st, player, slot) => payList(store, st, player, slot).list.length > 0;

// the attack decision: payable attacks, the one used, its printed damage and what should land after PlusPower, Weakness, Resistance, Defender
function attackInfo(game, st, me, opp, name) {
  const { src, list } = payList(game.store, st, me, me.active);
  const printed = a => { const p = src && POOL[src.fullName] && POOL[src.fullName][a.name]; return p ? p.d : (parseInt(a.damage, 10) || 0); };
  const used = list.find(a => a.name === name) || (src && src.attacks.find(a => a.name === name));
  const pd = used ? printed(used) : 0, ptxt = used && POOL[src.fullName] && POOL[src.fullName][name] ? POOL[src.fullName][name].t : null;
  const atk = me.active.getPokemonCard(), dc = opp.active.getPokemonCard();
  const pp = me.active.trainers.cards.filter(c => bare(c.name) === 'PlusPower').length, df = opp.active.trainers.cards.filter(c => bare(c.name) === 'Defender').length;
  let mult = 1, mod = 0;
  if (dc && atk) {
    for (const w of dc.weakness || []) if (atk.cardTypes.includes(w.type)) { if (w.value === undefined) mult *= 2; else mod += w.value; }
    for (const r of dc.resistance || []) if (atk.cardTypes.includes(r.type)) mod += r.value;
  }
  const exp = pd > 0 ? Math.max(0, (pd + 10 * pp) * mult + mod - 20 * df) : 0, mx = Math.max(0, ...list.map(printed));
  return { an: name, ac: atk ? atk.fullName : null, np: list.length, pd, pdMax: mx, top: pd >= mx, ptxt, plain: /^\d+$/.test(String(ptxt)),
    pp, df, mult, mod, exp, bA: nBench(me), bD: nBench(opp), hp: dc ? dc.hp : null, rem: dc ? dc.hp - opp.active.damage : null, payE: list.length > 0 };
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

// opening hand: each initial draw (first, then one more per mulligan) is read as its Shuffle deck prompt is answered during SETUP
function hookSetup(g, tr) {
  tr.setup = {};
  const orig = g.store.prompt;
  g.store.prompt = function (state, prompt, cb) {
    if (state.phase === C.GamePhase.SETUP && prompt && prompt.type === 'Shuffle deck' && typeof cb === 'function') {
      const cb2 = function () {
        const r = cb.apply(this, arguments);
        const pl = state.players.find(q => q.id === prompt.playerId), h = pl.hand.cards;
        const read = { b: h.filter(c => c.superType === C.SuperType.POKEMON && c.stage === C.Stage.BASIC).length, e: h.filter(c => c.superType === C.SuperType.ENERGY).length, n: h.length };
        const o = tr.setup[pl.id] || (tr.setup[pl.id] = { first: read, draws: 0 });
        o.draws++; o.last = read;
        return r;
      };
      return orig.call(this, state, prompt, cb2);
    }
    return orig.apply(this, arguments);
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
function ensure(game, tr, ctx) {
  const st = game.state;
  if (st.phase !== C.GamePhase.PLAYER_TURN || (tr.cur && tr.cur.t === st.turn)) return;
  closeRec(st, tr);
  const me = st.players[st.activePlayer];
  tr.cur = newRec(st, me);
  tr.cur.payS = canPay(game.store, st, me, me.active);
  tr.last = null;
  if (ctx) {                                          // start draw: the deck's drop in the dispatch that opened the turn (setup: from the hand)
    if (ctx.live) tr.cur.dS = ctx.decks[me.id] - me.deck.cards.length;
    else tr.cur.dS = me.hand.cards.length - ctx.hand[me.id] + slotsOf(me).filter(x => x.pokemons.cards.length > 0).length;
  }
}

const origDispatch = Game.prototype.dispatch;
Game.prototype.dispatch = function (action) {
  if (!OUT || this._pdone) return origDispatch.call(this, action);
  const st = this.state;
  const tr = this._ptr || (this._ptr = { cur: null, turns: [], pending: false });
  if (!this._phooked) { this._phooked = true; hook(this, tr); hookSetup(this, tr); }
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
        tr.last = n;
        if (n === 'Professor Oak' || n === 'Bill') cur.obp++;
        if (n === 'PlusPower') cur.ppP++;
        if (n === 'Switch' || n === 'Scoop Up') cur.sw++;
        if (n === 'Energy Removal' || n === 'Super Energy Removal') tr.pending = true;
      }
    } else {
      if (type !== 'RESOLVE_PROMPT') tr.pending = false;
      if (type === 'RETREAT_ACTION') cur.retreat++;
      if (type === 'ATTACK_ACTION') { const ai = attackInfo(this, st, me, opp, action.name); cur.A.push(ai); cur.payE = ai.payE; }
      else if (type === 'PASS_TURN' || (type === 'USE_ABILITY_ACTION' && action.name === 'Transform')) cur.payE = canPay(this.store, st, me, me.active);
    }
  }
  const ppIn = p => p.hand.cards.filter(c => bare(c.name) === 'PlusPower').length, ppD = p => p.discard.cards.filter(c => bare(c.name) === 'PlusPower').length;
  const ppH0 = me ? ppIn(me) : 0, ppD0 = me ? ppD(me) : 0;
  const live = st.phase === C.GamePhase.PLAYER_TURN, oppBefore = opp ? attached(opp) : 0, decks = {}, hand = {};
  for (const q of st.players) { decks[q.id] = q.deck.cards.length; hand[q.id] = q.hand.cards.length; }
  const r = origDispatch.call(this, action);
  if (cur && tr.pending && opp) cur.erLost += Math.max(0, oppBefore - attached(opp));
  if (cur && me && tr.last === 'Item Finder' && ppIn(me) > ppH0 && ppD(me) < ppD0) cur.ifPP += ppIn(me) - ppH0;   // Item Finder returned a PlusPower
  if (cur && live) {                                  // draws after the start draw, for the turn's owner (Trainers, Computer Search's fetch, Powers)
    const d = Math.max(0, decks[cur.p] - st.players.find(q => q.id === cur.p).deck.cards.length);
    cur.dT += d;
    if (d) { const k = tr.last || '-'; cur.dTn[k] = (cur.dTn[k] || 0) + d; }
  }
  if (!this.done) {
    ensure(this, tr, { live, decks, hand });
    const o = tr.cur, owner = o && st.players.find(q => q.id === o.p);
    if (o && live) o.drawn += Math.max(0, decks[owner.id] - owner.deck.cards.length);   // this dispatch's draws, for the turn owner
  } else if (!this._pdone) {
    this._pdone = true;
    closeRec(st, tr);
    const left = id => prizesLeft(st.players.find(p => p.id === id));
    fs.appendFileSync(OUT, JSON.stringify({ seed: this._seed, ending: this.ending, winner: this.winner, turn: st.turn,
      prizesLeft: { 1: left(1), 2: left(2) }, setup: tr.setup, error: this.error ? String(this.error.message || this.error) : null, turns: tr.turns }) + '\n');
  }
  return r;
};

require(path.join(ENV, 'remote_worker.js'));
