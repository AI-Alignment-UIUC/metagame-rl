// Which prompts the 2000 STS field raises, and how big their choices are.
//
// Plays seeded SimpleBot games over the archived decks and counts every prompt a player has to
// answer (arbiter prompts, coin flips and shuffles, are left out), by type and message, with the
// option ranges seen. Scopes the legal-action enumerator (A1.2).
//
// Run: node env/tools/prompt_census.js [--games 200] [--seed 1]
'use strict';
const path = require('path');
const H = require('../../notes/scripts/ryuu_harness.js');
const { buildArchivedDecks } = require('../../notes/scripts/ryuu_sts_decks.js');

const { Simulator, State, AddPlayerAction, BotFlipMode, BotShuffleMode, GamePhase, C } = H;
const SimpleBot = require(path.join(H.RYUU, 'packages', 'simple-bot')).SimpleBot;

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const GAMES = Number(flag('games', 200));
const SEED = Number(flag('seed', 1));

function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

const ARBITER = new Set(['Coin flip', 'Shuffle deck']);
const census = new Map();
function note(prompt) {
  const key = `${prompt.type} | ${C.GameMessage[prompt.message] !== undefined ? prompt.message : prompt.message}`;
  let e = census.get(key);
  if (!e) { e = { n: 0, sizes: new Map(), opts: new Map() }; census.set(key, e); }
  e.n++;
  let size = '';
  if (prompt.cards && prompt.cards.cards) size = 'cards=' + prompt.cards.cards.length;
  else if (prompt.cards && Array.isArray(prompt.cards)) size = 'cards=' + prompt.cards.length;
  else if (prompt.energy) size = 'energy=' + prompt.energy.length + ' cost=' + prompt.cost.length;
  else if (prompt.cardList) size = 'cards=' + prompt.cardList.cards.length;
  else if (prompt.values) size = 'values=' + prompt.values.length;
  else if (prompt.attacks) size = 'attacks=' + prompt.attacks.length;
  else if (prompt.count !== undefined) size = 'count=' + prompt.count;
  e.sizes.set(size, (e.sizes.get(size) || 0) + 1);
  const o = prompt.options || {};
  const os = ['min', 'max', 'allowCancel', 'differentTypes', 'sameTarget', 'differentTargets']
    .filter(k => o[k] !== undefined && o[k] !== false).map(k => `${k}=${o[k]}`).join(' ');
  e.opts.set(os, (e.opts.get(os) || 0) + 1);
}

const csv = path.join(__dirname, '..', '..', 'notes', 'data', '2000-super-trainer-showdown-california', 'cards.csv');
const decks = [...buildArchivedDecks(csv).values()];
let turnDecisions = 0, promptDecisions = 0, actions = 0, handSum = 0;
const realRandom = Math.random;
for (let g = 0; g < GAMES; g++) {
  Math.random = mulberry32(SEED * 1000003 + g);
  const deckA = decks[g % decks.length], deckB = decks[(g * 7 + 3) % decks.length];
  const sim = new Simulator(new State(), { flipMode: BotFlipMode.RANDOM, shuffleMode: BotShuffleMode.RANDOM });
  const bot = new SimpleBot('bot');
  const ais = new Map([[1, bot.createBotAi(1, deckA)], [2, bot.createBotAi(2, deckB)]]);
  sim.dispatch(new AddPlayerAction(1, 'A', deckA));
  sim.dispatch(new AddPlayerAction(2, 'B', deckB));
  let n = 0;
  while (sim.store.state.phase !== GamePhase.FINISHED && n++ < 4000) {
    const st = sim.store.state;
    const pending = st.prompts.find(p => p.result === undefined);
    if (pending) {
      if (!ARBITER.has(pending.type)) { note(pending); promptDecisions++; }
    } else if (st.phase === GamePhase.PLAYER_TURN) {
      turnDecisions++;
      handSum += st.players[st.activePlayer].hand.cards.length;
    }
    const wantId = pending ? pending.playerId : st.players[st.activePlayer].id;
    let action;
    for (const ai of [ais.get(wantId), ...ais.values()]) { action = ai.decodeNextAction(sim.store.state); if (action) break; }
    if (!action) break;
    sim.dispatch(action);
    actions++;
  }
}
Math.random = realRandom;

console.log(`${GAMES} games, ${actions} actions: ${turnDecisions} main-phase decisions ` +
  `(mean hand ${(handSum / turnDecisions).toFixed(1)}), ${promptDecisions} prompt decisions`);
const rows = [...census.entries()].sort((a, b) => b[1].n - a[1].n);
for (const [key, e] of rows) {
  const top = m => [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([k, v]) => `${k || '-'} (${v})`).join(', ');
  console.log(`${String(e.n).padStart(6)}  ${key}\n          sizes: ${top(e.sizes)}\n          options: ${top(e.opts)}`);
}
