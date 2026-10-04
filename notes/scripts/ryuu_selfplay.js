// Headless bot-vs-bot games in ryuu-play, with no server.
//
// ryuu-play only drives SimpleBot through the websocket server (BotGameHandler reacts to
// onStateChange and dispatches through a Game/Client pair). This runs the same BotAi against
// a bare Simulator instead, which is what an RL harness needs and what turns the §3
// per-dispatch number in sts-2000-engine-check.md into a games-per-second number with a real
// policy in the loop.
//
// Usage
//   node ryuu_selfplay.js <ryuu-play> --games 200                # throughput over the field
//   node ryuu_selfplay.js <ryuu-play> --games 200 --deck "15+ #1" --vs "15+ #2"
//   node ryuu_selfplay.js <ryuu-play> --matrix --games 40        # archetype matchup table
//   node ryuu_selfplay.js <ryuu-play> --mirror --games 12        # seat bias, deck held fixed
//   node ryuu_selfplay.js <ryuu-play> --workers 16 --games 160   # throughput across cores
//   node ryuu_selfplay.js <ryuu-play> --list                     # name the archived decks
//   ... --nopolicy                                               # no-search policy: engine cost alone
//   ... --seeded                                                 # deterministic, games repeat
//
// Decks come from notes/data/2000-super-trainer-showdown-california/cards.csv unless --deck
// names something else; --deck/--vs match on any substring of "division #place player (label)".
'use strict';
const fs = require('fs');
const path = require('path');
const H = require('./ryuu_harness.js');
const { buildArchivedDecks } = require('./ryuu_sts_decks.js');

const { Simulator, State, AddPlayerAction, BotFlipMode, BotShuffleMode, GamePhase, C } = H;
const SimpleBot = require(path.join(H.RYUU, 'packages', 'simple-bot')).SimpleBot;

// ---------------------------------------------------------------- args
const argv = process.argv.slice(2);
const flag = (name, dflt) => {
  const i = argv.indexOf('--' + name);
  if (i === -1) return dflt;
  const next = argv[i + 1];
  return next === undefined || next.startsWith('--') ? true : next;
};
const GAMES = Number(flag('games', 50));
const MAX_ACTIONS = Number(flag('max-actions', 4000));
const SEEDED = !!flag('seeded', false);   // deterministic flips/shuffles; games repeat exactly
const NOPOLICY = !!flag('nopolicy', false);  // no-search policy: isolates the engine cost
const PLAY = { seeded: SEEDED, noPolicy: NOPOLICY };

// ---------------------------------------------------------------- one game
function playGame(deckA, deckB, opts = {}) {
  const sim = new Simulator(new State(), {
    flipMode: opts.seeded ? BotFlipMode.ALL_HEADS : BotFlipMode.RANDOM,
    shuffleMode: opts.seeded ? BotShuffleMode.NO_SHUFFLE : BotShuffleMode.RANDOM,
  });

  // `tactics: []` keeps SimpleBot's prompt resolvers but drops every tactic, so
  // decodePlayerTurnAction falls straight through to PassTurn. That is a policy with no
  // search at all, which isolates what the engine costs when nothing is thinking.
  const factory = opts.noPolicy ? new SimpleBot('pass', { tactics: [] }) : new SimpleBot('bot');
  const ais = [factory.createBotAi(1, deckA), factory.createBotAi(2, deckB)];

  sim.dispatch(new AddPlayerAction(1, 'A', deckA));
  sim.dispatch(new AddPlayerAction(2, 'B', deckB));

  let actions = 0;
  let stuck = false;
  // SimpleBot searches one ply by cloning the state and dispatching candidate actions, so
  // its cost is nothing like the engine's. Time the two separately: the policy half is what
  // a trained network would replace, the engine half is the floor any harness pays.
  let policyNs = 0n;
  let engineNs = 0n;
  const t0 = process.hrtime.bigint();

  const aiById = new Map([[1, ais[0]], [2, ais[1]]]);

  while (sim.store.state.phase !== GamePhase.FINISHED) {
    if (actions >= MAX_ACTIONS) { stuck = true; break; }

    // Ask the one AI that can actually move: whoever owns the open prompt, else whoever's
    // turn it is. Polling both would charge the policy budget for AIs with nothing to do.
    const st = sim.store.state;
    const pending = st.prompts.find(p => p.result === undefined);
    const wantId = pending ? pending.playerId : st.players[st.activePlayer].id;
    const order = [aiById.get(wantId), ...ais].filter(Boolean);

    let moved = false;
    for (const ai of order) {
      const tp = process.hrtime.bigint();
      const action = ai.decodeNextAction(sim.store.state);
      policyNs += process.hrtime.bigint() - tp;
      if (!action) continue;
      const te = process.hrtime.bigint();
      try { sim.dispatch(action); } catch (e) { stuck = true; }
      engineNs += process.hrtime.bigint() - te;
      if (stuck) break;
      actions++;
      moved = true;
      break;
    }
    if (!moved || stuck) { stuck = stuck || !moved; break; }
  }

  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  const st = sim.store.state;

  // How a game ended says whether the bots are really playing it. All six prizes taken is a
  // game won on the board; an empty deck or an empty bench is a game that ran out.
  let ending = 'unfinished';
  if (st.phase === GamePhase.FINISHED) {
    const loser = st.players[st.winner === 0 ? 1 : 0];
    const winner = st.players[st.winner === 0 ? 0 : 1];
    if (winner && winner.prizes.every(z => z.cards.length === 0)) ending = 'prizes';
    else if (loser && loser.deck.cards.length === 0) ending = 'deck-out';
    else if (loser && loser.active.pokemons.cards.length === 0) ending = 'no Pokemon left';
    else ending = 'other';
  }

  return {
    winner: st.winner, turns: st.turn, actions, ms, stuck, phase: st.phase, ending,
    policyMs: Number(policyNs) / 1e6,
    engineMs: Number(engineNs) / 1e6,
  };
}

// ---------------------------------------------------------------- deck source
function loadDecks() {
  const csv = path.join(__dirname, '..', 'data', '2000-super-trainer-showdown-california', 'cards.csv');
  if (!fs.existsSync(csv)) return new Map();
  return buildArchivedDecks(csv);
}

// ---------------------------------------------------------------- runs
function summarise(label, results) {
  const done = results.filter(r => !r.stuck);
  const wins = [0, 0, 0];
  for (const r of done) {
    if (r.winner === 0) wins[0]++;
    else if (r.winner === 1) wins[1]++;
    else wins[2]++;
  }
  const totalMs = results.reduce((n, r) => n + r.ms, 0);
  const totalPolicy = results.reduce((n, r) => n + r.policyMs, 0);
  const totalEngine = results.reduce((n, r) => n + r.engineMs, 0);
  const totalActions = results.reduce((n, r) => n + r.actions, 0);
  const turns = done.map(r => r.turns).sort((a, b) => a - b);
  const median = turns.length ? turns[turns.length >> 1] : 0;
  const n = results.length;
  return {
    label,
    games: n,
    finished: done.length,
    stuck: n - done.length,
    winA: wins[0], winB: wins[1], draw: wins[2],
    msPerGame: totalMs / n,
    gamesPerSec: 1000 / (totalMs / n),
    policyMsPerGame: totalPolicy / n,
    engineMsPerGame: totalEngine / n,
    engineGamesPerSec: 1000 / (totalEngine / n),
    actionsPerGame: totalActions / n,
    usPerAction: totalActions ? (totalMs * 1000) / totalActions : 0,
    engineUsPerAction: totalActions ? (totalEngine * 1000) / totalActions : 0,
    medianTurns: median,
    endings: results.reduce((acc, r) => { acc[r.ending] = (acc[r.ending] || 0) + 1; return acc; }, {}),
  };
}

function printSummary(s) {
  const pct = (100 * s.winA / Math.max(s.finished, 1)).toFixed(1);
  console.log(`  ${s.label}`);
  console.log(`    ${s.games} games, ${s.finished} finished, ${s.stuck} stopped at the action cap`);
  console.log(`    seat A ${s.winA} / seat B ${s.winB} / draw ${s.draw}   (A win rate ${pct}%)`);
  console.log(`    ${s.actionsPerGame.toFixed(0)} actions/game, median ${s.medianTurns} turns`);
  console.log(`    endings: ${Object.entries(s.endings).map(([k, v]) => `${v} ${k}`).join(', ')}`);
  console.log('');
  console.log(`    whole game   ${s.msPerGame.toFixed(1)} ms  ->  ${s.gamesPerSec.toFixed(1)} games/s/core`);
  console.log(`      policy     ${s.policyMsPerGame.toFixed(1)} ms  (${(100 * s.policyMsPerGame / s.msPerGame).toFixed(0)}%)  SimpleBot searches one ply`);
  console.log(`      engine     ${s.engineMsPerGame.toFixed(1)} ms  (${(100 * s.engineMsPerGame / s.msPerGame).toFixed(0)}%)  ${s.engineUsPerAction.toFixed(0)} us/action`);
  console.log(`    engine-only ceiling (a policy with no search): ${s.engineGamesPerSec.toFixed(0)} games/s/core`);
}

const decks = loadDecks();

// ---------------------------------------------------------------- multi-core
// Node is single threaded and a game holds no shared state, so games fan out across cores
// with no coordination. This forks workers and sums their throughput, which is the number
// that decides whether a PSRO loop can afford this engine.
if (flag('workers', false) && !process.env.RYUU_SELFPLAY_WORKER) {
  const { fork } = require('child_process');
  const workers = Number(flag('workers', 4));
  const share = Math.max(1, Math.round(GAMES / workers));
  console.log(`forking ${workers} workers x ${share} games (${require('os').cpus().length} cores available)\n`);

  const t0 = process.hrtime.bigint();
  let done = 0;
  const totals = { games: 0, finished: 0, winA: 0, winB: 0, draw: 0, engineMs: 0, policyMs: 0, actions: 0 };

  for (let i = 0; i < workers; i++) {
    const childArgs = [H.RYUU, '--games', String(share), '--json'];
    if (NOPOLICY) childArgs.push('--nopolicy');
    if (SEEDED) childArgs.push('--seeded');
    const child = fork(__filename, childArgs,
      { env: { ...process.env, RYUU_SELFPLAY_WORKER: '1' }, stdio: ['ignore', 'pipe', 'inherit', 'ipc'] });
    let buf = '';
    child.stdout.on('data', d => { buf += d; });
    child.on('exit', () => {
      try {
        const r = JSON.parse(buf.trim().split('\n').pop());
        for (const k of Object.keys(totals)) totals[k] += r[k] || 0;
      } catch (e) { console.error('worker produced no JSON'); }
      if (++done === workers) {
        const wall = Number(process.hrtime.bigint() - t0) / 1e6;
        console.log(`  ${totals.games} games across ${workers} workers in ${(wall / 1000).toFixed(1)} s`);
        console.log(`    seat A ${totals.winA} / seat B ${totals.winB} / draw ${totals.draw}`);
        console.log(`    SimpleBot self-play:  ${(totals.games / wall * 1000).toFixed(1)} games/s across the box`);
        const engineShare = totals.engineMs / (totals.engineMs + totals.policyMs);
        console.log(`    engine-only estimate: ${(totals.games / wall * 1000 / engineShare).toFixed(0)} games/s across the box`
          + `  (engine is ${(100 * engineShare).toFixed(0)}% of in-game time)`);
      }
    });
  }
  return;
}

if (flag('list', false)) {
  console.log([...decks.keys()].map(k => '  ' + k).join('\n'));
  process.exit(0);
}

function pick(substr) {
  if (!substr || substr === true) return null;
  const hit = [...decks.keys()].find(k => k.toLowerCase().includes(String(substr).toLowerCase()));
  if (!hit) { console.error('no archived deck matching "' + substr + '"'); process.exit(1); }
  return hit;
}

console.log(`ryuu-play self-play | ${GAMES} games | ${SEEDED ? 'seeded (deterministic)' : 'random flips and shuffles'}`);
console.log(`${decks.size} archived decks loaded\n`);

if (flag('matrix', false)) {
  // one representative of each labelled archetype, highest placement first
  const byLabel = new Map();
  for (const [key, deck] of decks) {
    const label = key.slice(key.lastIndexOf('(') + 1, -1);
    if (!byLabel.has(label)) byLabel.set(label, { key, deck });
  }
  const entries = [...byLabel.entries()].slice(0, Number(flag('archetypes', 5)));
  console.log('matchup matrix, row = seat A:\n');
  const head = entries.map(([l]) => l.slice(0, 11).padStart(12)).join('');
  console.log(''.padEnd(26) + head);
  const t0 = process.hrtime.bigint();
  let games = 0;
  for (const [la, a] of entries) {
    const row = [];
    for (const [lb, b] of entries) {
      const rs = [];
      for (let i = 0; i < GAMES; i++) rs.push(playGame(a.deck, b.deck, PLAY));
      games += rs.length;
      const done = rs.filter(r => !r.stuck);
      const wa = done.filter(r => r.winner === 0).length;
      row.push((done.length ? (100 * wa / done.length).toFixed(0) + '%' : '-').padStart(12));
    }
    console.log(la.slice(0, 24).padEnd(26) + row.join(''));
  }
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  console.log(`\n${games} games in ${(ms / 1000).toFixed(1)} s  ->  ${(games / ms * 1000).toFixed(1)} games/s/core`);
  process.exit(0);
}

if (flag('mirror', false)) {
  // Same list on both sides, so anything away from 50% is seat or policy bias, not deck
  // strength. The research notes already call for swapped seats in human evaluation; this
  // is the same control applied to the bot baseline.
  const results = [];
  const perDeck = [];
  for (const [key, deck] of decks) {
    const rs = [];
    for (let i = 0; i < GAMES; i++) rs.push(playGame(deck, deck, PLAY));
    results.push(...rs);
    const done = rs.filter(r => !r.stuck);
    perDeck.push([key, done.filter(r => r.winner === 0).length, done.length]);
  }
  const s = summarise('mirror matches, every archived deck against itself', results);
  printSummary(s);
  const n = s.finished;
  const p = s.winA / Math.max(n, 1);
  const se = Math.sqrt(p * (1 - p) / Math.max(n, 1));
  console.log(`\n    seat-A win rate ${(100 * p).toFixed(1)}% +/- ${(100 * 1.96 * se).toFixed(1)} (95% CI over ${n} mirror games)`);
  console.log('    per deck (seat A wins / games):');
  perDeck.forEach(([k, w, t]) => console.log(`      ${k.padEnd(50)} ${w}/${t}`));
  process.exit(0);
}

const aKey = pick(flag('deck', null));
const bKey = pick(flag('vs', null));

if (aKey || bKey) {
  const a = decks.get(aKey || bKey), b = decks.get(bKey || aKey);
  const results = [];
  for (let i = 0; i < GAMES; i++) results.push(playGame(a, b, PLAY));
  printSummary(summarise(`${aKey || bKey}  vs  ${bKey || aKey}`, results));
} else {
  // throughput over the whole archived field: every deck mirror-matched once per round
  const all = [...decks.values()];
  if (!all.length) { console.error('no archived decks found'); process.exit(1); }
  const results = [];
  for (let i = 0; i < GAMES; i++) {
    const a = all[i % all.length];
    const b = all[(i + 1) % all.length];
    results.push(playGame(a, b, PLAY));
  }
  if (flag('json', false)) {
    const done = results.filter(r => !r.stuck);
    console.log(JSON.stringify({
      games: results.length,
      finished: done.length,
      winA: done.filter(r => r.winner === 0).length,
      winB: done.filter(r => r.winner === 1).length,
      draw: done.filter(r => r.winner !== 0 && r.winner !== 1).length,
      engineMs: results.reduce((n, r) => n + r.engineMs, 0),
      policyMs: results.reduce((n, r) => n + r.policyMs, 0),
      actions: results.reduce((n, r) => n + r.actions, 0),
    }));
  } else {
    printSummary(summarise('archived field, rotating pairings', results));
  }
}
