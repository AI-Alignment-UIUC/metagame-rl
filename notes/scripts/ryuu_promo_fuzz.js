// Full-game fuzz of the Wizards Black Star Promos (#1-#16) in ryuu-play.
//
// The promo specs test each attack and Power in a rigged position. This plays whole seeded
// SimpleBot games with two decks built around the promos, against each other and against the
// archived STS California field, and fails on anything that is not a normal game:
//   - an exception from the engine (SimpleBot only dispatches actions it has already checked
//     on a cloned state, so a throw on the real state is a bug)
//   - a position where neither bot has an action
//   - a game that runs past the action cap
// It also counts how often each promo attack, Power and Trainer was used, so a card that
// never comes up in play is visible rather than silently untested.
//
// SimpleBot never picks some promo moves on its own (Telekinesis, Texture Magic, Computer
// Error, ...), so on a share of turns the harness itself tries a promo move first: an attack of
// the Active promo Pokemon, or a promo Trainer from the hand. The engine may reject it (not
// enough Energy, say); a rejected try is a GameError, rolled back, and the bots carry on.
//
// Run: node ryuu_promo_fuzz.js [<ryuu-play>] [--games 400] [--seed 1]
'use strict';
const path = require('path');
const H = require('./ryuu_harness.js');
const { buildArchivedDecks } = require('./ryuu_sts_decks.js');

const { Simulator, State, AddPlayerAction, BotFlipMode, BotShuffleMode, GamePhase, C, expand } = H;
const { AttackAction, UseAbilityAction, PlayCardAction, ResolvePromptAction, GameMessage, GameError,
  PlayerType, SlotType, SuperType } = C;
const SimpleBot = require(path.join(H.RYUU, 'packages', 'simple-bot')).SimpleBot;

const argv = process.argv.slice(2);
const flag = (name, dflt) => {
  const i = argv.indexOf('--' + name);
  return i === -1 || argv[i + 1] === undefined ? dflt : argv[i + 1];
};
const GAMES = Number(flag('games', 400));
const SEED = Number(flag('seed', 1));
const MAX_ACTIONS = 4000;
const FORCE = Number(flag('force', 0.3));   // share of turns the harness tries a promo move first

// Pikachu PR1 and PR4 share the name Pikachu, so together they count against one 4-copy limit.
const PROMO_BASICS = expand([
  ['Pikachu PR1', 2], ['Pikachu PR4', 2], ['Electabuzz PR2', 4], ['Jigglypuff PR7', 4], ['Meowth PR10', 4],
  ['Cool Porygon PR15', 4], ['Mewtwo PR12', 4], ['Mew PR', 1], ['Computer Error PR16', 4], ['Bill BS', 4],
  ['Lightning Energy BS', 17], ['Psychic Energy BS', 6], ['Double Colorless Energy BS', 4],
]);
const PROMO_EVOLUTIONS = expand([
  ['Dratini BS', 4], ['Dragonair BS', 3], ['Dragonite PR5', 3], ['Growlithe BS', 4], ['Arcanine PR6', 3],
  ['Bulbasaur BS', 4], ['Ivysaur BS', 3], ['Venusaur PR13', 3], ['Eevee PR11', 4], ['Flareon JU', 2],
  ['Jolteon JU', 1], ['Vaporeon JU', 1], ['Computer Error PR16', 2], ['Bill BS', 2],
  ['Fire Energy BS', 9], ['Grass Energy BS', 8], ['Double Colorless Energy BS', 4],
]);
for (const [name, deck] of [['promo basics', PROMO_BASICS], ['promo evolutions', PROMO_EVOLUTIONS]]) {
  if (deck.length !== 60) throw new Error(`${name} has ${deck.length} cards`);
}

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

const isPromo = card => card && card.set === 'PR';
const usage = new Map();
const count = key => usage.set(key, (usage.get(key) || 0) + 1);

// Name what an action does with a promo, read before it is dispatched; counted only once the
// engine accepts it.
function promoUse(state, action, forced = false) {
  const tag = forced ? ' (forced)' : '';
  // PlayCardAction names its player `id`; the other actions use `clientId`.
  const playerId = action instanceof PlayCardAction ? action.id : action.clientId;
  const player = state.players.find(p => p.id === playerId);
  if (!player) return undefined;
  if (action instanceof AttackAction) {
    const card = player.active.getPokemonCard();
    if (isPromo(card)) return `${card.fullName}: ${action.name}${tag}`;
  } else if (action instanceof UseAbilityAction) {
    for (const slot of [player.active, ...player.bench]) {
      const card = slot.getPokemonCard();
      if (isPromo(card) && card.powers.some(p => p.name === action.name)) return `${card.fullName}: ${action.name}`;
    }
  } else if (action instanceof PlayCardAction) {
    const card = player.hand.cards[action.handIndex];
    if (isPromo(card)) return `${card.fullName}: played${tag}`;
  }
  return undefined;
}

// A promo move for the player whose turn it is, or undefined.
function promoMove(state, rnd) {
  const player = state.players[state.activePlayer];
  const moves = [];
  const active = player.active.getPokemonCard();
  if (isPromo(active)) for (const a of active.attacks) moves.push(new AttackAction(player.id, a.name));
  player.hand.cards.forEach((card, i) => {
    if (isPromo(card) && card.superType === SuperType.TRAINER) {
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
        const move = promoMove(st, forceRnd);
        if (move) {
          const use = promoUse(st, move, true);
          try {
            sim.dispatch(move);
            if (use) count(use);
            actions++;
            continue;
          } catch (e) {
            if (!(e instanceof GameError)) {
              return { result: 'error', actions, error: `forced ${move.constructor.name}: ${e && e.message || e}`, stack: e && e.stack };
            }
            count(`(rejected) ${use || move.constructor.name} -> ${e.message}`);
          }
        }
      }

      const wantId = pending ? pending.playerId : sim.store.state.players[sim.store.state.activePlayer].id;
      let action;
      for (const ai of [ais.get(wantId), ...ais.values()]) { action = ai.decodeNextAction(st); if (action) break; }
      if (!action) return { result: 'stuck', actions };

      if (action instanceof ResolvePromptAction && pending && pending.message === GameMessage.WANT_TO_USE_ABILITY
        && action.result === true) {
        count('Eevee PR11: Chain Reaction');
      }
      const use = promoUse(st, action);
      try {
        sim.dispatch(action);
        if (use) count(use);
      } catch (e) {
        return { result: 'error', actions, error: `${action.constructor.name}: ${e && e.message || e}`, stack: e && e.stack };
      }
      actions++;
    }
    return { result: 'finished', actions };
  } finally {
    Math.random = realRandom;
  }
}

// ---------------------------------------------------------------- run
const csv = path.join(__dirname, '..', 'data', '2000-super-trainer-showdown-california', 'cards.csv');
const field = [...buildArchivedDecks(csv).entries()];
const promoDecks = [['promo basics', PROMO_BASICS], ['promo evolutions', PROMO_EVOLUTIONS]];

const results = { finished: 0, stuck: 0, cap: 0, error: 0 };
const failures = [];
const t0 = Date.now();
for (let g = 0; g < GAMES; g++) {
  const seed = SEED * 1000003 + g;
  const a = promoDecks[g % 2];
  // A quarter promo vs promo, the rest promo vs a field deck; seats alternate.
  const b = g % 4 === 0 ? promoDecks[(g >> 1) % 2] : field[(g * 5 + 1) % field.length];
  const [first, second] = (g >> 2) % 2 === 0 ? [a, b] : [b, a];
  const r = playGame(first[1], second[1], seed);
  results[r.result]++;
  if (r.result !== 'finished') failures.push({ g, seed, decks: `${first[0]} vs ${second[0]}`, ...r });
}

console.log(`${GAMES} games in ${((Date.now() - t0) / 1000).toFixed(1)}s: ` +
  Object.entries(results).map(([k, v]) => `${v} ${k}`).join(', '));
for (const f of failures.slice(0, 10)) {
  console.log(`  ${f.result.toUpperCase()} game ${f.g} (seed ${f.seed}) ${f.decks} after ${f.actions} actions` +
    (f.error ? `: ${f.error}` : ''));
  if (f.stack) console.log('    ' + f.stack.split('\n').slice(1, 6).join('\n    '));
}

console.log('\npromo usage across all games:');
const promoNames = H.S.baseSets.setPromos.map(c => c.fullName);
const expected = [];
for (const name of promoNames) {
  const card = H.cm.getCardByName(name);
  for (const a of card.attacks || []) expected.push(`${name}: ${a.name}`);
  for (const p of card.powers || []) expected.push(`${name}: ${p.name}`);
  if (card.superType === C.SuperType.TRAINER) expected.push(`${name}: played`);
}
for (const key of expected) console.log(`  ${String(usage.get(key) || 0).padStart(6)}  ${key}`);
const extra = [...usage.keys()].filter(k => !expected.includes(k));
for (const key of extra) console.log(`  ${String(usage.get(key)).padStart(6)}  ${key}`);

if (results.error + results.stuck + results.cap > 0) process.exitCode = 1;
