// Shared helpers for the engine audit's scripted cases (log #484, Evan's row 102; read-only, no engine or env change).
// A scene is a built game state (as env/staged/engine_confusion_test.js builds it) wrapped in env/engine.js's store;
// `play` dispatches an action and answers the prompts it raises from a script.
'use strict';
const path = require('path');
const { C, cm, newState, newStore } = require(path.join(__dirname, '..', '..', '..', 'env', 'engine.js'));

const card = name => {
  const proto = cm.getCardByName(name);
  if (!proto) throw new Error('no card ' + name);
  return new (proto.constructor)();
};

// spec per player (index 0 = player id 1): { active, energy: [], damage, sp: [], trainers: [], bench: [name | {name, energy, damage}],
//   hand: [], deck: n (filler cards), prizes: n, played: pokemonPlayedTurn of the Active }
// top-level: { turn, active: 0|1 (index of the player whose turn it is), rules: {..overrides} }
function scene(p1, p2, { turn = 5, active = 0, rules = {} } = {}) {
  const state = newState();
  Object.assign(state.rules, rules);
  state.players = [p1, p2].map((spec, i) => {
    const p = new C.Player();
    p.id = i + 1;
    p.name = 'P' + (i + 1);
    p.active = new C.PokemonSlot();
    p.active.pokemons.cards.push(card(spec.active));
    for (const e of spec.energy || []) p.active.energies.cards.push(card(e));
    for (const t of spec.trainers || []) p.active.trainers.cards.push(card(t));
    p.active.damage = spec.damage || 0;
    p.active.pokemonPlayedTurn = spec.played === undefined ? 0 : spec.played;
    for (const s of spec.sp || []) p.active.specialConditions.push(C.SpecialCondition[s]);
    for (let k = 0; k < 5; k++) p.bench.push(new C.PokemonSlot());
    (spec.bench || []).forEach((b, k) => {
      const o = typeof b === 'string' ? { name: b } : b;
      p.bench[k].pokemons.cards.push(card(o.name));
      for (const e of o.energy || []) p.bench[k].energies.cards.push(card(e));
      p.bench[k].damage = o.damage || 0;
      p.bench[k].pokemonPlayedTurn = o.played === undefined ? 0 : o.played;
    });
    for (const h of spec.hand || []) p.hand.cards.push(card(h));
    for (let k = 0; k < (spec.prizes === undefined ? 6 : spec.prizes); k++) { const z = new C.CardList(); z.cards.push(card('Scyther JU')); p.prizes.push(z); }
    for (let k = 0; k < (spec.deck === undefined ? 10 : spec.deck); k++) p.deck.cards.push(card('Scyther JU'));
    return p;
  });
  state.phase = C.GamePhase.PLAYER_TURN;
  state.activePlayer = active;
  state.turn = turn;
  return newStore(state);
}

// Dispatch `action` and answer the prompts it raises: coin flips from `flips` (default heads), a Choose attack prompt
// by `pick` ({index, name}), prizes the first, new Active the first Benched Pokemon. Returns { flips: used, error }.
function play(store, action, { flips = [], pick = null, target = null } = {}) {
  let n = 0, error = null;
  try {
    store.dispatch(action);
    for (let guard = 0; guard < 50; guard++) {
      const p = store.state.prompts.find(q => q.result === undefined);
      if (!p) break;
      let raw;
      if (p.type === 'Coin flip') raw = n < flips.length ? flips[n++] : true;
      else if (p.type === 'Choose attack') raw = p.decode(pick, store.state);
      else if (p.type === 'Choose energy') raw = p.energy.slice(0, p.cost.length);
      else if (p.type === 'Choose cards') raw = p.decode(Array.from({ length: Math.min(p.options.max, p.cards.cards.length) }, (_, i) => i));
      else if (p.type === 'Choose prize') raw = p.decode([0], store.state);
      else if (p.type === 'Choose pokemon') raw = p.decode(target ? [target] : [defaultTarget(p, store.state)], store.state);
      else if (p.type === 'Shuffle deck') raw = store.state.players.find(q => q.id === p.playerId).deck.cards.map((_, i) => i);
      else { error = 'unhandled prompt ' + p.type; break; }
      store.dispatch(new C.ResolvePromptAction(p.id, raw));
    }
  } catch (e) { error = String(e.message || e); }
  return { flips: n, error };
}
function defaultTarget(p, state) {
  const me = state.players.find(q => q.id === p.playerId);
  const i = me.bench.findIndex(s => s.pokemons.cards.length > 0);
  return { player: C.PlayerType.BOTTOM_PLAYER, slot: C.SlotType.BENCH, index: i };
}

const ACTIVE = { player: C.PlayerType.BOTTOM_PLAYER, slot: C.SlotType.ACTIVE, index: 0 };
const attackAction = (id, name) => new C.AttackAction(id, name);
const playHand = (id, handIndex, target = ACTIVE) => new C.PlayCardAction(id, handIndex, target);
const benchTarget = i => ({ player: C.PlayerType.BOTTOM_PLAYER, slot: C.SlotType.BENCH, index: i });
const players = store => store.state.players;
const prizesLeft = p => p.prizes.reduce((s, z) => s + z.cards.length, 0);

module.exports = { C, cm, card, scene, play, attackAction, playHand, benchTarget, ACTIVE, players, prizesLeft };
