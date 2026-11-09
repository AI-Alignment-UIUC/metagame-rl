// C135 (runs/probe/C135-fullwidth-pp/record.md): field H with the pilot in model slot 0 on both seats, one seat (seat 1 on an even
// seed, seat 2 on an odd one) designated. $C135_ARM: G (both seats greedy), SV or SP (the designated seat is env/agents.js
// PolicySearchAgent at Trainer-playable main-phase decisions, k 64 = every legal option, dets 2, CRN, horizon 1, scored by V or by
// C132's "prizes"; the other seat greedy). env/remote_worker.js runs beneath, unchanged; this file only wraps it (log only).
// One JSON line per attack by the designated seat to $C135_OUT, with C134's fields (bp_worker.js: base after the Defender's W and R,
// raw, HP left, KO, PlusPower and Defender) plus:
//   ppHand / gustHand: PlusPower / Gust of Wind in hand at the attack; ppPlayed / gustPlayed: played this turn before it;
//   start: the turn's first decision's snapshot (PlusPower and Gust in hand, the opposing Active and Bench with HP left);
//   gusted: the Defender was on the opposing Bench at that snapshot;
//   b10state: the attack without this turn's PlusPower, max(0, base - 20 x Defender), would leave exactly 10;
//   bGstate: some Pokemon benched at the snapshot has HP left at or under max(0, raw x its W + its R) + 10, and the snapshot's Active
//     would survive this attack without PlusPower (max(0, max(0, raw x W + R) - 20 x its Defender) under its HP left).
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Game } = require(path.join(ENV, 'game.js'));
const { Env } = require(path.join(ENV, 'env.js'));
const { Runner } = require(path.join(ENV, 'runner.js'));
const { PolicySearchAgent } = require(path.join(ENV, 'agents.js'));
const { TokenEncoder } = require(path.join(ENV, 'tokens.js'));
const { C } = require(path.join(ENV, 'engine.js'));
const OUT = process.env.C135_OUT, ARM = process.env.C135_ARM || 'G';

const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };
const origClone = Game.prototype.clone;
Game.prototype.clone = function (...a) { const g = origClone.apply(this, a); g._bpSkip = true; return g; };

const bare = n => String(n).replace(/ [A-Z0-9]+$/, '');
const leftOf = s => { const c = s.getPokemonCard(); return c ? c.hp - s.damage : null; };
const wr = (atk, dc) => {
  let mult = 1, mod = 0, hit = false;
  for (const w of dc.weakness || []) if (atk.cardTypes.includes(w.type)) { hit = true; if (w.value === undefined) mult *= 2; else mod += w.value; }
  for (const r of dc.resistance || []) if (atk.cardTypes.includes(r.type)) mod += r.value;
  return [mult, mod, hit];
};
const count = (slot, name) => slot.trainers.cards.filter(c => bare(c.name) === name).length;
const inHand = (p, name) => p.hand.cards.filter(c => bare(c.name) === name).length;
const seatOf = g => (g._seed % 2 === 0 ? 1 : 2);     // the designated seat

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
  if (!OUT || this._bpSkip || !action || this._seed === undefined) return origDispatch.call(this, action);
  const st = this.state, me = st.players[st.activePlayer];
  if (!me || me.id !== seatOf(this) || st.phase !== C.GamePhase.PLAYER_TURN) return origDispatch.call(this, action);
  const opp = st.players.find(p => p !== me);
  if (this._c135t !== st.turn) {                     // the turn's first decision: the snapshot
    this._c135t = st.turn;
    this._c135 = { ppStart: inHand(me, 'PlusPower'), gustStart: inHand(me, 'Gust of Wind'), ppPlayed: 0, gustPlayed: 0,
      active: opp.active.getPokemonCard() ? { card: opp.active.getPokemonCard(), left: leftOf(opp.active), df: count(opp.active, 'Defender') } : null,
      bench: opp.bench.filter(s => s.pokemons.cards.length > 0).map(s => ({ card: s.getPokemonCard(), left: leftOf(s) })) };
  }
  const T = this._c135;
  if (action.type === 'PLAY_CARD_ACTION') {
    const card = me.hand.cards[action.handIndex], n = card && bare(card.name);
    if (n === 'PlusPower') T.ppPlayed++;
    if (n === 'Gust of Wind') T.gustPlayed++;
    return origDispatch.call(this, action);
  }
  if (action.type !== 'ATTACK_ACTION') return origDispatch.call(this, action);
  if (!this._bpHooked) { this._bpHooked = true; hook(this); }
  const atk = me.active.getPokemonCard(), dc = opp.active.getPokemonCard();
  const pre = { card: dc, left: leftOf(opp.active) };
  const pp = count(me.active, 'PlusPower'), df = count(opp.active, 'Defender');
  const ppHand = inHand(me, 'PlusPower'), gustHand = inHand(me, 'Gust of Wind');
  this._bpCap = { target: opp.active, base: null };
  const r = origDispatch.call(this, action);
  const base = this._bpCap.base; this._bpCap = null;
  const now = opp.active.getPokemonCard(), same = now === pre.card, ko = !same && opp.discard.cards.includes(pre.card);
  const [mA, oA, weak] = atk && dc ? wr(atk, dc) : [1, 0, false];
  const raw = base > 0 ? (base - oA) / mA : 0;
  const gusted = !!(dc && T.bench.some(b => b.card === dc));
  const b10state = base > 0 && pre.left - Math.max(0, base - 20 * df) === 10;
  const benchOpp = base > 0 && T.bench.some(b => { const [m, o] = wr(atk, b.card); return b.left > 0 && b.left <= Math.max(0, raw * m + o) + 10; });
  const a0 = T.active;
  const activeKoPlain = !!(a0 && base > 0 && (() => { const [m, o] = wr(atk, a0.card); return a0.left <= Math.max(0, Math.max(0, raw * m + o) - 20 * a0.df); })());
  fs.appendFileSync(OUT, JSON.stringify({
    seed: this._seed, turn: st.turn, p: me.id, arm: ARM, ac: atk ? atk.fullName : null, an: action.name, base, raw,
    dc: dc ? dc.fullName : null, left0: pre.left, left1: same ? leftOf(opp.active) : null, ko, weak, pp, df, ppHand, gustHand,
    ppPlayed: T.ppPlayed, gustPlayed: T.gustPlayed, ppStart: T.ppStart, gustStart: T.gustStart, gusted,
    b10state, bGstate: benchOpp && !activeKoPlain,
  }) + '\n');
  return r;
};

// the designated seat's searcher, built from the runner's own RemoteAgent (the module doesn't export RemotePilot)
function pilotOf(RA, slot) {
  return { agents: new Map(), evaluate(batch, k) {
    if (!this.agents.has(k)) this.agents.set(k, new RA(slot, 'tokens', true, k));
    return this.agents.get(k).act(batch).then(out => out.map(o => ({ order: [o.action, ...(o.top || []).filter(a => a !== o.action)], best: o.action, value: o.value })));
  } };
}
const origRun = Runner.prototype.run;
Runner.prototype.run = function (nextJob, agents, o) {
  const wrapped = (...a) => {
    const job = nextJob(...a);
    if (!job || ARM === 'G') return job;
    const name = job.seats[1];                       // both seats are the slot's RemoteAgent (one model, a mirror of pilots)
    if (!agents.c135s) {
      const ra = agents[name];
      agents.c135s = new PolicySearchAgent(pilotOf(ra.constructor, ra.slot), new TokenEncoder(),
        { k: Number(process.env.C135_K || 64), dets: 2, maxSteps: 40, seed: 135, crn: true, horizon: 1, trainerOnly: true, includeTrainer: false,
          allTrainers: process.env.C135_ALLTR === '1',   // C138's acceptance: the top C135_K plus every legal Trainer play
          score: ARM === 'SP' ? 'prizes' : 'value' });
    }
    job.seats = { ...job.seats, [job.seed % 2 === 0 ? 1 : 2]: 'c135s' };
    return job;
  };
  return origRun.call(this, wrapped, agents, o);
};

require(path.join(ENV, 'remote_worker.js'));
