// Where ryuu-play's engine time goes, and what the two hot spots are worth.
//
// Reports, in order:
//   1. how the per-dispatch deepClone cost grows over a single game, and why
//   2. what clearing the accumulating state.logs array buys
//   3. how many effects an action raises and how many cards each one walks
//   4. what propagateEffect's per-effect sort costs, and what caching it would save
//
// For a function-level profile instead:
//   node --cpu-prof --cpu-prof-dir=. ryuu_selfplay.js <ryuu-play> --nopolicy --games 150
//   node cpuprofile_top.mjs CPU.*.cpuprofile
//
// Run: node ryuu_hotspots.js <path-to-ryuu-play>
'use strict';
const path = require('path');
const H = require('./ryuu_harness.js');
const { buildArchivedDecks } = require('./ryuu_sts_decks.js');
const SimpleBot = require(path.join(H.RYUU, 'packages', 'simple-bot')).SimpleBot;
const { Simulator, State, AddPlayerAction, BotFlipMode, BotShuffleMode, GamePhase, C } = H;
const { deepClone, Card } = C;

const CSV = path.join(__dirname, '..', 'data', '2000-super-trainer-showdown-california', 'cards.csv');
const list = [...buildArchivedDecks(CSV).values()];

function newGame(a, b, tactics) {
  const sim = new Simulator(new State(), { flipMode: BotFlipMode.RANDOM, shuffleMode: BotShuffleMode.RANDOM });
  const factory = tactics === null ? new SimpleBot('pass', { tactics: [] }) : new SimpleBot('bot');
  const ais = [factory.createBotAi(1, a), factory.createBotAi(2, b)];
  sim.dispatch(new AddPlayerAction(1, 'A', a));
  sim.dispatch(new AddPlayerAction(2, 'B', b));
  return { sim, aiById: new Map([[1, ais[0]], [2, ais[1]]]), ais };
}
function step(g) {
  const st = g.sim.store.state;
  const pending = st.prompts.find(p => p.result === undefined);
  const wantId = pending ? pending.playerId : st.players[st.activePlayer].id;
  for (const ai of [g.aiById.get(wantId), ...g.ais]) {
    if (!ai) continue;
    const a = ai.decodeNextAction(g.sim.store.state);
    if (!a) continue;
    try { g.sim.dispatch(a); return true; } catch (e) { return false; }
  }
  return false;
}

// ------------------------------------------------- 1. clone cost over a game
console.log('=== 1. the per-dispatch state clone, over one game ===\n');
function countNodes(o, seen = new Set()) {
  if (o === null || typeof o !== 'object' || o instanceof Card || seen.has(o)) return 0;
  seen.add(o);
  let n = 1;
  if (Array.isArray(o)) { for (const v of o) n += countNodes(v, seen); return n; }
  for (const k in o) if (Object.prototype.hasOwnProperty.call(o, k)) n += countNodes(o[k], seen);
  return n;
}
{
  const g = newGame(list[0], list[1], null);
  const cloneUs = () => {
    const t = process.hrtime.bigint();
    for (let i = 0; i < 20; i++) deepClone(g.sim.store.state, [Card]);
    return Number(process.hrtime.bigint() - t) / 1000 / 20;
  };
  console.log('  actions  turn  prompts  logs  objects  clone_us');
  const show = n => {
    const st = g.sim.store.state;
    console.log(String(n).padStart(9) + String(st.turn).padStart(6) + String(st.prompts.length).padStart(9) +
      String(st.logs.length).padStart(6) + String(countNodes(st)).padStart(9) + cloneUs().toFixed(1).padStart(10));
  };
  let n = 0; show(0);
  while (g.sim.store.state.phase !== GamePhase.FINISHED && n < 2000) {
    if (!step(g)) break;
    if (++n % 20 === 0) show(n);
  }
  console.log('\n  prompts are pruned; state.logs is not, and every log entry is re-cloned each dispatch.');
}

// ------------------------------------------------- 2. what the logs cost
console.log('\n=== 2. cost of the accumulating state.logs array ===\n');
function run(games, clearLogs) {
  let actions = 0;
  const t = process.hrtime.bigint();
  for (let i = 0; i < games; i++) {
    const g = newGame(list[i % list.length], list[(i + 1) % list.length], null);
    let n = 0;
    while (g.sim.store.state.phase !== GamePhase.FINISHED && n < 2000) {
      if (clearLogs) g.sim.store.state.logs.length = 0;
      if (!step(g)) break;
      n++;
    }
    actions += n;
  }
  const ms = Number(process.hrtime.bigint() - t) / 1e6;
  return { ms, actions, games };
}
const GAMES = Number(process.argv[3] || 60);
const base = run(GAMES, false), cleared = run(GAMES, true);
const show2 = (t, r) => console.log(`  ${t.padEnd(16)} ${(r.ms / r.games).toFixed(1).padStart(7)} ms/game  ` +
  `${(1000 / (r.ms / r.games)).toFixed(1).padStart(6)} games/s  ${((r.ms * 1000) / r.actions).toFixed(0).padStart(5)} us/action`);
show2('as shipped', base); show2('logs cleared', cleared);
console.log(`\n  clearing logs alone: ${(base.ms / cleared.ms).toFixed(2)}x faster`);

// ------------------------------------------------- 3. propagation fan-out
console.log('\n=== 3. effects per action, cards walked per effect ===\n');
{
  let effects = 0, visits = 0, actions = 0;
  for (let i = 0; i < 8; i++) {
    const g = newGame(list[i % list.length], list[(i + 1) % list.length], null);
    const orig = g.sim.store.reduceEffect.bind(g.sim.store);
    g.sim.store.reduceEffect = (state, effect) => {
      effects++;
      for (const p of state.players) {
        visits += p.hand.cards.length + p.deck.cards.length + p.discard.cards.length
          + p.active.pokemons.cards.length + p.active.energies.cards.length + p.active.trainers.cards.length
          + p.prizes.reduce((n, z) => n + z.cards.length, 0)
          + p.bench.reduce((n, s) => n + s.pokemons.cards.length + s.energies.cards.length + s.trainers.cards.length, 0);
      }
      return orig(state, effect);
    };
    let n = 0;
    while (g.sim.store.state.phase !== GamePhase.FINISHED && n < 2000) { if (!step(g)) break; n++; }
    actions += n;
  }
  console.log(`  ${(effects / actions).toFixed(1)} store.reduceEffect calls per action`);
  console.log(`  ${(visits / effects).toFixed(0)} cards walked per effect`);
  console.log(`  -> ${(visits / actions).toFixed(0)} card.reduceEffect invocations per action, ~${(visits / 8 / 1000).toFixed(0)}k per game`);
}

// ------------------------------------------------- 4. the sort
console.log('\n=== 4. propagateEffect re-sorts 120 cards on every effect ===\n');
{
  const pool = list[0].map(n => H.cm.getCardByName(n));
  const all = pool.concat(pool);
  const EPA = 17.3, APG = 96;
  const bench = (label, fn) => {
    fn();
    const t = process.hrtime.bigint();
    for (let i = 0; i < 2000; i++) fn();
    const us = Number(process.hrtime.bigint() - t) / 1000 / 2000;
    console.log(`  ${label.padEnd(42)} ${us.toFixed(1).padStart(6)} us/sort -> ${(us * EPA).toFixed(0).padStart(4)} us/action`);
    return us;
  };
  const shipped = bench('as shipped (localeCompare, every effect)', () => {
    const a = all.slice();
    a.sort((c1, c2) => (c2.superType - c1.superType) || c1.fullName.localeCompare(c2.fullName));
    return a;
  });
  bench('plain < > comparator', () => {
    const a = all.slice();
    a.sort((c1, c2) => (c2.superType - c1.superType) || (c1.fullName < c2.fullName ? -1 : c1.fullName > c2.fullName ? 1 : 0));
    return a;
  });
  let cached = null;
  bench('cached order (set is invariant per game)', () => cached || (cached = all.slice()
    .sort((c1, c2) => (c2.superType - c1.superType) || c1.fullName.localeCompare(c2.fullName))));
  console.log(`\n  the sort is ~${(100 * shipped * EPA / 540).toFixed(0)}% of the ~540 us/action baseline.`);
  console.log('  Cards move between zones but the set of 120 never changes within a game,');
  console.log('  so the sorted order could be computed once instead of ' + (EPA * APG).toFixed(0) + ' times a game.');
}
