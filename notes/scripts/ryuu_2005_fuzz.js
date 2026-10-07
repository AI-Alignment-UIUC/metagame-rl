// Full-game fuzz of the engine's Worlds 2005 card pool (engine branch worlds-2005), after
// ryuu_promo_fuzz.js: seeded SimpleBot games between random legal decks drawn from every 2005-legal
// card the engine has (notes/data/eval/legal_pool_2005.json, engine_legal_fullnames), so cards no
// archived list or targeted test reaches still get played. A game fails on:
//   - an exception from the engine on an action SimpleBot already checked on a clone
//   - a position where neither bot has an action
//   - a game that runs past the action cap
// On a share of turns (--force) the harness itself tries a random attack of the Active Pokemon or a
// random Trainer from the hand first, since SimpleBot leaves many moves unplayed; the engine may
// reject it (a GameError, rolled back). It counts which attacks and Trainers were ever accepted, so
// cards that never came up are listed rather than silently untested.
//
// Random decks (card-agnostic, verification only): 2-3 Basic Pokemon of the pool with 3-4 copies,
// their evolutions in the pool (2-3 Stage 1, 1-3 Stage 2), 13-19 basic Energy of the attackers'
// types, 0-3 Special Energy, the rest random Trainers; at most 4 per name and one Pokemon Star.
// Each game is printed before it starts, so a hang (an infinite loop inside one action) shows
// which seed and decks to replay: run under `timeout`.
//
// Run: RYUU_PLAY=<engine on worlds-2005> node ryuu_2005_fuzz.js [--games 300] [--seed 1] [--force 0.3]
'use strict';
const path = require('path');
const H = require('./ryuu_harness.js');
const { Simulator, State, AddPlayerAction, BotFlipMode, BotShuffleMode, GamePhase, C, cm } = H;
const { AttackAction, PlayCardAction, ResolvePromptAction, GameError, PlayerType, SlotType, SuperType, Stage,
  EnergyType } = C;
const SimpleBot = require(path.join(H.RYUU, 'packages', 'simple-bot')).SimpleBot;

const argv = process.argv.slice(2);
const flag = (name, dflt) => {
  const i = argv.indexOf('--' + name);
  return i === -1 || argv[i + 1] === undefined ? dflt : argv[i + 1];
};
const GAMES = Number(flag('games', 300));
const SEED = Number(flag('seed', 1));
const FORCE = Number(flag('force', 0.3));
const MAX_ACTIONS = 4000;
const ONLY = flag('only', null);       // replay one game index, tracing every step to stderr
const trace = msg => { if (ONLY !== null) process.stderr.write(msg + '\n'); };

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

// ---------------------------------------------------------------- the pool
// The CardManager knows only the Base-era sets until the EX sets are registered (as in
// ryuu_2005_cards_tests.js); register every EX set the engine exports.
const EX = H.S.exSets;
if (!EX || !EX.setEmerald) { console.error('engine lacks the EX sets (needs the worlds-2005 branch)'); process.exit(1); }
if (!cm.getAllFormats().some(f => f.name === 'EX 2005 (fuzz)')) cm.defineFormat('EX 2005 (fuzz)', Object.values(EX));
const names = require(path.join(__dirname, '..', 'data', 'eval', 'legal_pool_2005.json')).engine_legal_fullnames;
const pool = names.map(n => cm.getCardByName(n)).filter(Boolean);
const missing = names.filter(n => !cm.getCardByName(n));
if (missing.length) console.log(`warning: ${missing.length} legal names unknown to this engine: ${missing.slice(0, 5).join(', ')}`);
const isStar = c => /★|Star/.test(c.name);
const pokemon = pool.filter(c => c.superType === SuperType.POKEMON);
const basics = pokemon.filter(c => c.stage === Stage.BASIC);
const trainers = pool.filter(c => c.superType === SuperType.TRAINER);
const basicEnergy = pool.filter(c => c.superType === SuperType.ENERGY && c.energyType === EnergyType.BASIC);
const specialEnergy = pool.filter(c => c.superType === SuperType.ENERGY && c.energyType !== EnergyType.BASIC);
const byName = new Map();
for (const c of pool) byName.set(c.name, [...(byName.get(c.name) || []), c]);

function randomDeck(rnd) {
  const pick = arr => arr[Math.floor(rnd() * arr.length)];
  const deck = [];
  const perName = new Map();
  let star = false;
  const add = (card, k) => {
    for (let i = 0; i < k; i++) {
      if (deck.length >= 60) return;
      if (isStar(card) && star) return;
      const isBasicEnergy = card.superType === SuperType.ENERGY && card.energyType === EnergyType.BASIC;
      if (!isBasicEnergy && (perName.get(card.name) || 0) >= 4) return;
      deck.push(card);
      perName.set(card.name, (perName.get(card.name) || 0) + 1);
      if (isStar(card)) star = true;
    }
  };
  const types = new Set();
  const lines = 2 + Math.floor(rnd() * 2);
  for (let l = 0; l < lines; l++) {
    const b = pick(basics);
    add(b, 3 + Math.floor(rnd() * 2));
    (b.cardTypes || [b.cardType]).forEach(t => types.add(t));
    const s1 = pokemon.filter(c => c.stage === Stage.STAGE_1 && c.evolvesFrom === b.name);
    if (s1.length) {
      const e1 = pick(s1);
      add(e1, 2 + Math.floor(rnd() * 2));
      (e1.cardTypes || [e1.cardType]).forEach(t => types.add(t));
      const s2 = pokemon.filter(c => c.stage === Stage.STAGE_2 && c.evolvesFrom === e1.name);
      if (s2.length) {
        const e2 = pick(s2);
        add(e2, 1 + Math.floor(rnd() * 3));
        (e2.cardTypes || [e2.cardType]).forEach(t => types.add(t));
      }
    }
  }
  const typed = basicEnergy.filter(e => (e.provides || []).some(t => types.has(t)));
  const nEnergy = 13 + Math.floor(rnd() * 7);
  for (let i = 0; i < nEnergy; i++) add(pick(typed.length ? typed : basicEnergy), 1);
  const nSpecial = Math.floor(rnd() * 4);
  for (let i = 0; i < nSpecial && specialEnergy.length; i++) add(pick(specialEnergy), 1);
  for (let tries = 0; deck.length < 60 && tries < 2000; tries++) add(pick(trainers), 1);
  while (deck.length < 60) add(pick(typed.length ? typed : basicEnergy), 1);
  return deck.map(c => c.fullName);
}

// ---------------------------------------------------------------- usage
const usage = new Map();
const count = key => usage.set(key, (usage.get(key) || 0) + 1);
function useOf(state, action) {
  const playerId = action instanceof PlayCardAction ? action.id : action.clientId;
  const player = state.players.find(p => p.id === playerId);
  if (!player) return undefined;
  if (action instanceof AttackAction) {
    const card = player.active.getPokemonCard();
    return card ? `${card.fullName}: ${action.name}` : undefined;
  }
  if (action instanceof PlayCardAction) {
    const card = player.hand.cards[action.handIndex];
    if (card && card.superType === SuperType.TRAINER) return `${card.fullName}: played`;
  }
  return undefined;
}
function forcedMove(state, rnd) {
  const player = state.players[state.activePlayer];
  const moves = [];
  const active = player.active.getPokemonCard();
  if (active) for (const a of active.attacks) moves.push(new AttackAction(player.id, a.name));
  player.hand.cards.forEach((card, i) => {
    if (card.superType === SuperType.TRAINER) {
      moves.push(new PlayCardAction(player.id, i, { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.BOARD, index: 0 }));
    }
  });
  return moves.length ? moves[Math.floor(rnd() * moves.length)] : undefined;
}

function playGame(deckA, deckB, seed) {
  const realRandom = Math.random;
  Math.random = mulberry32(seed);
  const forceRnd = mulberry32(seed ^ 0x2545F491);
  try {
    const sim = new Simulator(new State(), { flipMode: BotFlipMode.RANDOM, shuffleMode: BotShuffleMode.RANDOM });
    const bot = new SimpleBot('bot');
    const ais = new Map([[1, bot.createBotAi(1, deckA)], [2, bot.createBotAi(2, deckB)]]);
    sim.dispatch(new AddPlayerAction(1, 'A', deckA));
    sim.dispatch(new AddPlayerAction(2, 'B', deckB));
    let actions = 0;
    while (sim.store.state.phase !== GamePhase.FINISHED) {
      if (actions >= MAX_ACTIONS) return { result: 'cap', actions };
      const st = sim.store.state;
      const pending = st.prompts.find(p => p.result === undefined);
      if (!pending && st.phase === GamePhase.PLAYER_TURN && forceRnd() < FORCE) {
        const move = forcedMove(st, forceRnd);
        if (move) {
          trace(`step ${actions}: forced ${useOf(st, move) || move.constructor.name}`);
          const use = useOf(st, move);
          try {
            sim.dispatch(move);
            if (use) count(use);
            trace(`  forced accepted, phase ${sim.store.state.phase}`);
            actions++;
            continue;
          } catch (e) {
            trace(`  forced rejected: ${e && e.message}, phase ${sim.store.state.phase}`);
            if (!(e instanceof GameError)) {
              return { result: 'error', actions, error: `forced ${use || move.constructor.name}: ${e && e.message || e}`, stack: e && e.stack };
            }
            // A rejected action makes the store restore its backup as a new State object, so `st`
            // (read above) is now the half-applied state: read the state again before anyone acts.
            // (ryuu_promo_fuzz.js decides on the stale state here.)
            continue;
          }
        }
      }
      const wantId = pending ? pending.playerId : st.players[st.activePlayer].id;
      let action;
      trace(`step ${actions}: bot ${wantId} deciding` + (pending ? ` (prompt ${pending.constructor.name}: ${pending.message})` : ''));
      for (const ai of [ais.get(wantId), ...ais.values()]) { action = ai.decodeNextAction(st); if (action) break; }
      trace(`step ${actions}: dispatch ${action ? action.constructor.name + " " + (action.name || action.handIndex || "") + " " + (useOf(st, action) || "") : "(none)"}`);
      if (!action) {
        // What the position looks like: the open prompt, whose turn, and whether a plain pass is legal.
        const p = st.players[st.activePlayer];
        let pass = 'pass accepted';
        try { sim.dispatch(new C.PassTurnAction(p.id)); } catch (e) { pass = `pass rejected: ${e && e.message || e}`; }
        const why = pending ? `open prompt ${pending.constructor.name} (${pending.message}) for player ${pending.playerId}`
          : `no prompt, phase ${st.phase}, player ${p.id} to act, active ${p.active.getPokemonCard() && p.active.getPokemonCard().fullName}`;
        return { result: 'stuck', actions, error: `${why}; ${pass}` };
      }
      const use = action instanceof ResolvePromptAction ? undefined : useOf(st, action);
      try {
        sim.dispatch(action);
        if (use) count(use);
      } catch (e) {
        return { result: 'error', actions, error: `${use || action.constructor.name}: ${e && e.message || e}`, stack: e && e.stack };
      }
      actions++;
    }
    return { result: 'finished', actions };
  } finally {
    Math.random = realRandom;
  }
}

// ---------------------------------------------------------------- run
const results = { finished: 0, stuck: 0, cap: 0, error: 0 };
const failures = [];
const t0 = Date.now();
for (let g = 0; g < GAMES; g++) {
  if (ONLY !== null && g !== Number(ONLY)) { const r0 = mulberry32((SEED * 1000003 + g) ^ 0x5bd1e995); randomDeck(r0); randomDeck(r0); continue; }
  const seed = SEED * 1000003 + g;
  const rnd = mulberry32(seed ^ 0x5bd1e995);
  const a = randomDeck(rnd), b = randomDeck(rnd);
  process.stdout.write(`game ${g} seed ${seed}\r`);
  trace(`decks:\n  A: ${a.join(', ')}\n  B: ${b.join(', ')}`);
  const r = playGame(a, b, seed);
  results[r.result]++;
  if (r.result !== 'finished') failures.push({ g, seed, a, b, ...r });
}
console.log(`${GAMES} games in ${((Date.now() - t0) / 1000).toFixed(1)}s: ` +
  Object.entries(results).map(([k, v]) => `${v} ${k}`).join(', '));
for (const f of failures.slice(0, 15)) {
  console.log(`  ${f.result.toUpperCase()} game ${f.g} (seed ${f.seed}) after ${f.actions} actions` + (f.error ? `: ${f.error}` : ''));
  if (f.stack) console.log('    ' + f.stack.split('\n').slice(1, 5).join('\n    '));
}

const attacks = [], played = [];
for (const c of pool) {
  for (const a of c.attacks || []) attacks.push(`${c.fullName}: ${a.name}`);
  if (c.superType === SuperType.TRAINER) played.push(`${c.fullName}: played`);
}
const seen = keys => keys.filter(k => usage.get(k)).length;
console.log(`\ncoverage: ${seen(attacks)}/${attacks.length} attacks and ${seen(played)}/${played.length} Trainers accepted at least once`);
const never = [...attacks, ...played].filter(k => !usage.get(k));
console.log(`never accepted (${never.length}): ${never.slice(0, 40).join('; ')}${never.length > 40 ? ' ...' : ''}`);
if (results.error + results.stuck + results.cap > 0) process.exitCode = 1;
