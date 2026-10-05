// Loads the ryuu-play engine (the ryuu-play/ submodule, or RYUU_PLAY) and registers the
// Base-era format once per process.
//
// Also provides a Store that skips the rollback backup. ryuu-play deep-clones the whole state
// before every action so it can restore it if the action throws. The environment only ever
// dispatches actions from the legal-action enumerator, so the backup is dead weight; a throw
// from a "legal" action is an enumerator or engine bug, and the game is reported as broken.
'use strict';
const path = require('path');

const RYUU = path.resolve(process.env.RYUU_PLAY || path.join(__dirname, '..', 'ryuu-play'));
const ROOT = path.join(RYUU, 'packages');
const C = require(path.join(ROOT, 'common'));

// The compiled engine re-exports everything through chains of getters (TypeScript's live
// bindings), and card code reads them on every effect: \`effect instanceof common_1.AttackEffect\`
// runs several getters for each of ~80 cards on each of ~17 effects per action. The exports are
// classes and functions that never change, so the card sets get a plain snapshot instead.
const Module = require('module');
const PLAIN_COMMON = Object.freeze(Object.assign(Object.create(null), C));
const realLoad = Module._load;
Module._load = function (request, parent, isMain) {
  if (request === '@ptcg/common' && parent && parent.filename && parent.filename.includes(path.join('packages', 'sets'))) {
    return PLAIN_COMMON;
  }
  return realLoad.apply(this, arguments);
};
const S = require(path.join(ROOT, 'sets'));
Module._load = realLoad;
const DIST = path.join(ROOT, 'common', 'dist', 'cjs', 'store');
const { setupPhaseReducer } = require(path.join(DIST, 'reducers', 'setup-reducer.js'));
const { playCardReducer } = require(path.join(DIST, 'reducers', 'play-card-reducer.js'));
const { playerTurnReducer } = require(path.join(DIST, 'reducers', 'player-turn-reducer.js'));
const { checkState } = require(path.join(DIST, 'effect-reducers', 'check-effect.js'));

const FORMAT = 'Base Sets';
// 2000 rules: Mysterious Fossil is a Trainer in hand at setup, not a starting Pokemon.
const RULES = new C.Rules({ fossilsAsStarters: false });
const cm = C.CardManager.getInstance();
if (!cm.getAllFormats().some(f => f.name === FORMAT)) {
  const sets = [S.baseSets.setBase, S.baseSets.setJungle, S.baseSets.setFossil, S.baseSets.setTeamRocket];
  if (S.baseSets.setPromos) sets.push(S.baseSets.setPromos);
  cm.defineFormat(FORMAT, sets, RULES);
}

// A fresh game state under the format's rules.
function newState() {
  const state = new C.State();
  state.rules = new C.Rules(RULES);
  return state;
}

// Store.reduce without the backup clone. Same steps as the original otherwise.
function reduceWithoutBackup(state, action) {
  this.promptItems.length = 0;
  state = setupPhaseReducer(this, state, action);
  state = playCardReducer(this, state, action);
  state = playerTurnReducer(this, state, action);
  this.resolveWaitItems();
  if (this.promptItems.length === 0) {
    state = checkState(this, state);
  }
  this.handler.onStateChange(state);
  return state;
}

// For trials: legality is settled by the reducers, so the post-action state check (knockouts,
// prizes, winner: ~10 effect propagations) is skipped.
function reduceWithoutBackupOrCheck(state, action) {
  this.promptItems.length = 0;
  state = setupPhaseReducer(this, state, action);
  state = playCardReducer(this, state, action);
  state = playerTurnReducer(this, state, action);
  this.resolveWaitItems();
  return state;
}

const NOOP_HANDLER = { onStateChange() {} };

// Answered prompts stay in state.prompts for the whole game, and every clone copies them along
// with the hands and decks they point to. Once no prompt is open they are dead, so they are
// dropped then (never while a group of prompts is half answered: the store reads the answered
// ones back when the last one comes in). Prompt ids restart, deterministically.
function dispatchAndPrune(action) {
  const state = C.Store.prototype.dispatch.call(this, action);
  const prompts = this.state.prompts;
  if (prompts.length > 0 && prompts.every(p => p.result !== undefined)) this.state.prompts = [];
  return state;
}

function noLog() {}

// backup: keep ryuu-play's rollback clone. logs: keep the game log (debug output only).
function newStore(state, { backup = false, logs = false } = {}) {
  const store = new C.Store(NOOP_HANDLER);
  if (state !== undefined) store.state = state;
  if (!backup) store.reduce = reduceWithoutBackup;
  if (!logs) store.log = noLog;
  store.dispatch = dispatchAndPrune;
  return store;
}

// True if the engine accepts `action` in `state`. Runs it on a deep clone, so `state` is left
// as it was. Used by the oracle and for the legality rules that live in card code.
//
// Coin flips, shuffles and prize picks raised along the way are answered too, because the
// engine sometimes checks legality after one: an attack under a Smokescreen-style effect flips
// before the Energy check, so on tails it never notices the attack can't be paid for. The
// action is legal only if it goes through with every flip heads and with every flip tails.
//
// `from` is the store that owns `state`: the trial reuses its card-order cache (the cards are
// the same objects), which otherwise gets rebuilt, with a sort of every card, in each trial.
function accepts(state, action, from) {
  return tryAction(state, action, from).ok;
}

// Legality as accepts(), plus the state right after the action with every flip heads (null if
// the turn ended in the trial, or the action was rejected).
function tryAction(state, action, from) {
  const heads = trial(state, action, true, from);
  if (!heads.ok) return { ok: false, after: null };
  if (heads.flips > 0 && !trial(state, action, false, from).ok) return { ok: false, after: null };
  return { ok: true, after: heads.state || null };
}

// Thrown inside a trial when the turn ends: whatever follows (between-turns effects, the next
// player's draw) can't make the action illegal, and it is most of an attack's cost.
const TURN_ENDED = { turnEnded: true };
function reduceEffectUntilTurnEnds(state, effect) {
  if (effect instanceof C.EndTurnEffect) throw TURN_ENDED;
  return C.Store.prototype.reduceEffect.call(this, state, effect);
}

function trial(state, action, flip, from) {
  const store = newStore(C.deepClone(state, [C.Card]));
  if (from !== undefined) store.cardRanks = from.cardRanks;
  store.reduceEffect = reduceEffectUntilTurnEnds;
  store.reduce = reduceWithoutBackupOrCheck;
  let flips = 0;
  try {
    store.dispatch(action);
    for (;;) {
      const p = store.state.prompts.find(q => q.result === undefined
        && (q.type === 'Coin flip' || q.type === 'Shuffle deck' || q.type === 'Choose prize'));
      if (!p) break;
      let result;
      if (p.type === 'Coin flip') { result = flip; flips++; }
      else if (p.type === 'Shuffle deck') {
        const player = store.state.players.find(q => q.id === p.playerId);
        result = player.deck.cards.map((_, i) => i);
      } else {
        result = p.decode(Array.from({ length: p.options.count }, (_, i) => i), store.state);
      }
      store.dispatch(new C.ResolvePromptAction(p.id, result));
    }
    return { ok: true, flips, state: store.state };
  } catch (e) {
    if (e === TURN_ENDED) return { ok: true, flips };
    if (e instanceof C.GameError) return { ok: false, flips };
    throw e;
  }
}

// The state right after `action` (all coin flips heads), or null if the engine rejects it.
function stateAfter(state, action, from) {
  const r = trial(state, action, true, from);
  return r.ok ? (r.state || null) : null;
}

module.exports = { RYUU, C, S, cm, FORMAT, RULES, newState, newStore, accepts, tryAction, stateAfter };
