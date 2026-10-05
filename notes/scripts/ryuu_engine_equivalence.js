// Differential test for engine changes to Store (packages/common/src/store/store.ts).
//
// Plays the same seeded bot-vs-bot games twice: once with the current Store, once with the
// Store methods from a reference commit swapped in, and compares a fingerprint of the full
// game state (zones, cards, prompts, logs, ...) after every dispatched action. Any divergence
// fails the run and prints the first differing action.
//
// The reference store.ts is read with `git show <ref>:...`, transpiled, and loaded next to the
// compiled store.js so its relative requires resolve to the same modules (and the same
// classes). Only `reduce` and `propagateEffect` are swapped, so both runs share everything
// else.
//
// Also, per run:
//   - every propagateEffect call checks the new card order against the reference sort
//   - illegal actions are injected at random; each must throw and leave the state unchanged
//   - flips and shuffles are random but seeded (Math.random is replaced per game)
//
// Run: node ryuu_engine_equivalence.js [<ryuu-play>] [--games 300] [--ref 9cd20b6] [--seed 1]
//                                      [--illegal 0.05]
'use strict';
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const H = require('./ryuu_harness.js');
const { buildArchivedDecks } = require('./ryuu_sts_decks.js');

const { Simulator, State, AddPlayerAction, BotFlipMode, BotShuffleMode, GamePhase, C } = H;
const { Card, AttackAction, PlayCardAction, RetreatAction, PassTurnAction, UseAbilityAction } = C;
const SimpleBot = require(path.join(H.RYUU, 'packages', 'simple-bot')).SimpleBot;

const argv = process.argv.slice(2);
const flag = (name, dflt) => {
  const i = argv.indexOf('--' + name);
  return i === -1 || argv[i + 1] === undefined ? dflt : argv[i + 1];
};
const GAMES = Number(flag('games', 300));
const REF = flag('ref', '9cd20b6');
const SEED = Number(flag('seed', 1));
const ILLEGAL = Number(flag('illegal', 0.05));
const MAX_ACTIONS = 4000;

// ---------------------------------------------------------------- reference Store
const storeDir = path.join(H.RYUU, 'packages', 'common', 'dist', 'cjs', 'store');
const refFile = path.join(storeDir, `store.ref-${REF}-${process.pid}.js`);
const ts = require(path.join(H.RYUU, 'node_modules', 'typescript'));
const refSrc = execFileSync('git', ['-C', H.RYUU, 'show', `${REF}:packages/common/src/store/store.ts`], { encoding: 'utf8' });
fs.writeFileSync(refFile, ts.transpileModule(refSrc, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2017 },
}).outputText);
let RefStore;
try { RefStore = require(refFile).Store; } finally { fs.unlinkSync(refFile); }

const Store = new Simulator(new State(), {}).store.constructor;
const NEW = { reduce: Store.prototype.reduce, propagateEffect: Store.prototype.propagateEffect };
const OLD = { reduce: RefStore.prototype.reduce, propagateEffect: RefStore.prototype.propagateEffect };

// In the new mode, check every card order against the reference stable sort.
let orderChecks = 0;
function checkedPropagate(state, effect) {
  if (typeof this.sortCards === 'function') {
    const cards = collectCards(state);
    const want = cards.slice().sort((a, b) => (b.superType - a.superType) || a.fullName.localeCompare(b.fullName));
    const got = this.sortCards(cards);
    if (got.length !== want.length || got.some((c, i) => c !== want[i])) {
      throw new Error('propagateEffect order differs from the reference sort');
    }
    orderChecks++;
  }
  return NEW.propagateEffect.call(this, state, effect);
}
function collectCards(state) {   // same traversal as Store.propagateEffect
  const cards = [];
  for (const p of state.players) {
    cards.push(...p.stadium.cards, ...p.supporter.cards);
    for (const s of [p.active, ...p.bench]) cards.push(...s.trainers.cards, ...s.energies.cards, ...s.pokemons.cards);
    for (const z of p.prizes) cards.push(...z.cards);
    cards.push(...p.hand.cards, ...p.deck.cards, ...p.discard.cards);
  }
  return cards;
}

function useMode(mode) {
  const m = mode === 'old' ? OLD : NEW;
  Store.prototype.reduce = m.reduce;
  Store.prototype.propagateEffect = mode === 'old' ? m.propagateEffect : checkedPropagate;
}

// ---------------------------------------------------------------- fingerprint
// Canonical walk of the whole state. Cards are named by fullName plus a per-game identity
// index, so a card moving to a different zone or swapping places shows up.
//
// By default, an object or array reached twice is written as a back-reference, so the
// fingerprint also records which parts of the state are shared. With valuesOnly, everything is
// written out in full: deepClone (used for the rollback backup) does not preserve shared
// arrays, so after a rollback, resolved prompts hold copies of arrays such as hand.cards
// instead of the arrays themselves. That changes the sharing but not any value.
function fingerprint(state, cardIds, valuesOnly = false) {
  const seen = new Map();
  const path = new Set();
  const out = [];
  const walk = v => {
    if (v === null || v === undefined || typeof v !== 'object') { out.push(typeof v === 'function' ? 'fn' : JSON.stringify(v)); return; }
    if (v instanceof Card) {
      if (!cardIds.has(v)) cardIds.set(v, cardIds.size);
      out.push(`<${v.fullName}#${cardIds.get(v)}>`);
      return;
    }
    if (!valuesOnly && seen.has(v)) { out.push(`@${seen.get(v)}`); return; }
    if (path.has(v)) { out.push('cycle'); return; }
    seen.set(v, seen.size);
    path.add(v);
    if (Array.isArray(v)) { out.push('['); v.forEach(walk); out.push(']'); }
    else {
      out.push('{');
      for (const k of Object.keys(v).sort()) { out.push(k + ':'); walk(v[k]); }
      out.push('}');
    }
    path.delete(v);
  };
  walk(state);
  return out.join(',');
}

// ---------------------------------------------------------------- seeded randomness
function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// An action the engine must reject: wrong player, a card index past the hand, an attack or
// Power the Pokemon doesn't have, a retreat to an empty bench slot.
function illegalAction(state, rnd) {
  const turnPlayer = state.players[state.activePlayer];
  const other = state.players[1 - state.activePlayer];
  const pick = Math.floor(rnd() * 5);
  switch (pick) {
    case 0: return new AttackAction(turnPlayer.id, 'No Such Attack');
    case 1: return new PlayCardAction(turnPlayer.id, 99, { player: 0, slot: 0, index: 0 });
    case 2: return new PassTurnAction(other.id);
    case 3: return new RetreatAction(turnPlayer.id, 5 + Math.floor(rnd() * 10));   // the bench has slots 0-4
    default: return new UseAbilityAction(turnPlayer.id, 'No Such Power', { player: 0, slot: 0, index: 0 });
  }
}

// ---------------------------------------------------------------- one game
function playGame(deckA, deckB, seed, mode) {
  useMode(mode);
  const realRandom = Math.random;
  Math.random = mulberry32(seed);
  const illegalRnd = mulberry32(seed ^ 0x5bd1e995);
  const trace = [];
  const cardIds = new Map();
  let illegalTried = 0, illegalRejected = 0, illegalChanged = 0, illegalAccepted = 0, illegalReshared = 0;
  try {
    const sim = new Simulator(new State(), { flipMode: BotFlipMode.RANDOM, shuffleMode: BotShuffleMode.RANDOM });
    const bot = new SimpleBot('bot');
    const ais = new Map([[1, bot.createBotAi(1, deckA)], [2, bot.createBotAi(2, deckB)]]);
    sim.dispatch(new AddPlayerAction(1, 'A', deckA));
    sim.dispatch(new AddPlayerAction(2, 'B', deckB));
    trace.push(fingerprint(sim.store.state, cardIds));

    let actions = 0;
    while (sim.store.state.phase !== GamePhase.FINISHED && actions < MAX_ACTIONS) {
      const st = sim.store.state;
      const pending = st.prompts.find(p => p.result === undefined);

      if (!pending && st.phase === GamePhase.PLAYER_TURN && illegalRnd() < ILLEGAL) {
        const before = fingerprint(st, cardIds, true);
        const beforeShared = fingerprint(st, cardIds);
        illegalTried++;
        let threw = false;
        const lastIllegal = illegalAction(st, illegalRnd);
        try { sim.dispatch(lastIllegal); } catch (e) { threw = true; }
        if (threw) {
          illegalRejected++;
          if (fingerprint(sim.store.state, cardIds, true) !== before) illegalChanged++;
          else if (fingerprint(sim.store.state, cardIds) !== beforeShared) illegalReshared++;
        } else {
          illegalAccepted++;
          if (process.env.EQ_DEBUG) console.log("accepted:", JSON.stringify(lastIllegal));
        }
        trace.push('illegal:' + threw + ':' + fingerprint(sim.store.state, cardIds));
        if (sim.store.state.phase === GamePhase.FINISHED) break;
        continue;
      }

      const wantId = pending ? pending.playerId : st.players[st.activePlayer].id;
      const order = [ais.get(wantId), ...ais.values()];
      let action;
      for (const ai of order) { action = ai.decodeNextAction(sim.store.state); if (action) break; }
      if (!action) { trace.push('stuck'); break; }
      sim.dispatch(action);
      actions++;
      trace.push(action.constructor.name + ':' + fingerprint(sim.store.state, cardIds));
    }
    return { trace, actions, winner: sim.store.state.winner, illegalTried, illegalRejected, illegalChanged, illegalAccepted, illegalReshared };
  } finally {
    Math.random = realRandom;
  }
}

// ---------------------------------------------------------------- run
const csv = path.join(__dirname, '..', 'data', '2000-super-trainer-showdown-california', 'cards.csv');
const decks = [...buildArchivedDecks(csv).entries()];
if (decks.length === 0) throw new Error('no archived decks');

let mismatches = 0, totalActions = 0, finished = 0;
const ill = { tried: 0, rejected: 0, changed: 0, accepted: 0, reshared: 0 };
const t0 = Date.now();
for (let g = 0; g < GAMES; g++) {
  const seed = SEED * 1000003 + g;
  const [nameA, deckA] = decks[g % decks.length];
  const [nameB, deckB] = decks[Math.floor(g / decks.length + g * 7) % decks.length];
  const a = playGame(deckA, deckB, seed, 'old');
  const b = playGame(deckA, deckB, seed, 'new');

  let first = -1;
  for (let i = 0; i < Math.max(a.trace.length, b.trace.length); i++) {
    if (a.trace[i] !== b.trace[i]) { first = i; break; }
  }
  if (first !== -1) {
    mismatches++;
    console.log(`MISMATCH game ${g} (seed ${seed}) ${nameA} vs ${nameB}: first difference at step ${first}`);
    console.log('  old: ' + String(a.trace[first]).slice(0, 300));
    console.log('  new: ' + String(b.trace[first]).slice(0, 300));
  }
  for (const r of [a, b]) {
    ill.tried += r.illegalTried; ill.rejected += r.illegalRejected;
    ill.changed += r.illegalChanged; ill.accepted += r.illegalAccepted; ill.reshared += r.illegalReshared;
  }
  totalActions += a.actions;
  if (a.winner !== undefined && a.trace[a.trace.length - 1] !== 'stuck') finished++;
}

const secs = ((Date.now() - t0) / 1000).toFixed(1);
console.log(`${GAMES} games x 2 engines, ${totalActions} actions per engine, ${secs}s`);
console.log(`state identical after every action: ${GAMES - mismatches}/${GAMES} games`);
console.log(`card-order checks against the reference sort: ${orderChecks}, all equal`);
console.log(`illegal actions: ${ill.tried} tried, ${ill.rejected} rejected, ${ill.accepted} accepted, ` +
  `${ill.changed} rejected but changed a value, ${ill.reshared} rejected with only array sharing changed ` +
  '(both engines combined)');
if (ill.changed > 0 || ill.accepted > 0) process.exitCode = 1;
if (mismatches > 0) process.exitCode = 1;
