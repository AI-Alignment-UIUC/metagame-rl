// Puzzle positions with provable answers (plan item A2): "win this turn".
//
// Generate: plays seeded heuristic-vs-heuristic games over the archived decks and, at main-phase
// decisions late in the game, searches every line of play for the rest of the current turn
// (prompts included). A first move "wins" if some line starting with it ends the game in the
// mover's favour this turn with every coin flip heads AND with every coin flip tails. Lines that
// draw unknown cards (Bill, Professor Oak and other draws) are not followed, since deck order is
// hidden. A position is kept when some first moves win and some don't. Each puzzle is stored as
// the seed and the option indices that reach it, so it replays exactly.
//
// Score: replays each puzzle and asks an agent for its move; solved if the move is a winning one.
//
// Run: node env/tools/puzzles.js generate [--games 400] [--max 300] [--out notes/data/puzzles/lethal.json]
//        [--start 0]   (first game index, to split generation across processes)
//      node env/tools/puzzles.js merge <part.json> ... [--out notes/data/puzzles/lethal.json]
//      node env/tools/puzzles.js score --agent heuristic|random|simplebot|onnx:<file> [--in ...]
'use strict';
const fs = require('fs');
const path = require('path');
const { Game } = require('../game.js');
const { archivedDecks } = require('../decks.js');
const { Rng } = require('../rng.js');
const { C } = require('../engine.js');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const MODE = argv[0];
const DEFAULT_FILE = path.join(__dirname, '..', '..', 'notes', 'data', 'puzzles', 'lethal.json');
const NODE_LIMIT = 4000;
const MAX_DEPTH = 25;
const UNPROVABLE = /^trainer\|(Bill|Professor Oak|Imposter Professor Oak|Lass|Here Comes Team Rocket!|Gambler) /;

// A fixed coin: every flip heads (or tails); shuffles keep the deck order.
function fixedRng(heads) {
  return { int: () => (heads ? 0 : 1), float: () => 0, u32: () => 0, permutation: n => Array.from({ length: n }, (_, i) => i), clone() { return this; } };
}

// Does a line starting with option `first` at this (main-phase) position win this turn for
// `mover`, with every coin flip `heads`? A search node is a stable state (a main-phase decision,
// no prompt open: it can be cloned) plus the option path played since; nodes inside a prompt
// are rebuilt by replaying that short path on a clone. The mover needs one winning option at
// each of their decisions; at the opponent's decisions (a new Active after a knockout) every
// option must still lose for them.
function winsWith(game, first, heads, mover) {
  const turn = game.state.turn;
  const budget = { left: NODE_LIMIT };
  const dfs = (base, path, depth = 0) => {
    if (--budget.left < 0 || depth > MAX_DEPTH) throw new Error('budget');
    const g = base.clone(fixedRng(heads));
    for (const i of path) g.step(i);
    if (g.done) return g.winner === mover;
    if (g.state.turn !== turn) return false;
    const d = g.decision();
    if (!d) return false;
    const stable = !g.openPrompt();
    const child = i => (stable ? dfs(g, [i], depth + 1) : dfs(base, path.concat(i), depth + 1));
    // Cancelling only returns to an earlier position, so it never starts a winning line; leaving
    // it out also stops play-a-Trainer-then-cancel cycles.
    const moves = d.options.map((o, i) => [o.key, i]).filter(([k]) => k !== 'pass' && k !== 'cancel' && !UNPROVABLE.test(k));
    if (d.playerId === mover) return moves.some(([, i]) => child(i));
    return d.options.every((_, i) => child(i));
  };
  return dfs(game, [first]);
}

function winningFirstMoves(game) {
  const d = game.decision();
  const mover = d.playerId;
  const wins = [];
  d.options.forEach((o, i) => {
    if (o.key === 'pass' || UNPROVABLE.test(o.key)) return;
    if (winsWith(game, i, true, mover) && winsWith(game, i, false, mover)) wins.push(o.key);
  });
  return { mover, wins, all: d.options.map(o => o.key) };
}

// A game that records the option indices played, so a position can be replayed from its seed.
function trackedGame(deckA, deckB, seed) {
  const g = new Game(deckA, deckB, seed);
  g.record = { path: [] };
  const step = g.step.bind(g);
  g.step = i => { g.record.path.push(i); step(i); };
  return g;
}

async function generate() {
  const games = Number(flag('games', 400));
  const first = Number(flag('start', 0));
  const max = Number(flag('max', 300));
  const out = flag('out', DEFAULT_FILE);
  const { heuristicIndex } = require('../agents.js');
  const decks = archivedDecks();
  const puzzles = [];
  let positions = 0, skipped = 0;
  const t0 = Date.now();
  for (let gi = first; gi < first + games && puzzles.length < max; gi++) {
    const a = decks[gi % decks.length], b = decks[(gi * 7 + 3) % decks.length];
    const seed = 424242 + gi;
    const game = trackedGame(a.cards, b.cards, seed);
    while (!game.done) {
      const d = game.decision();
      if (!d) break;
      const opp = game.state.players.find(p => p.id !== d.playerId);
      const oppPrizes = opp.prizes.reduce((s, z) => s + z.cards.length, 0);
      const oppInPlay = [opp.active, ...opp.bench].filter(s => s.pokemons.cards.length).length;
      if (!d.prompt && d.options.length > 2 && (oppPrizes <= 2 || oppInPlay <= 1)) {
        positions++;
        try {
          const r = winningFirstMoves(game);
          if (r.wins.length > 0 && r.wins.length < r.all.length) {
            puzzles.push({ deckA: a.name, deckB: b.name, seed, path: game.record.path.slice(), mover: r.mover,
              turn: game.state.turn, wins: r.wins, options: r.all });
          }
        } catch (e) {
          if (e.message !== 'budget') throw e;
          skipped++;
        }
      }
      game.step(heuristicIndex(game, d));
    }
    process.stdout.write(`\rgames ${gi + 1 - first}, positions searched ${positions}, puzzles ${puzzles.length}, over budget ${skipped}, ${((Date.now() - t0) / 1000).toFixed(0)}s   `);
  }
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify({ kind: 'win this turn', nodeLimit: NODE_LIMIT, puzzles }, null, 1));
  console.log(`\nwrote ${puzzles.length} puzzles to ${out}`);
}

async function score() {
  const file = flag('in', DEFAULT_FILE);
  const spec = flag('agent', 'heuristic');
  const { puzzles } = JSON.parse(fs.readFileSync(file, 'utf8'));
  const decks = archivedDecks();
  const byName = n => decks.find(d => d.name === n);
  const { Encoder } = require('../encode.js');
  const { Env } = require('../env.js');
  const agents = require('../agents.js');
  const enc = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
  const agent = spec === 'heuristic' ? new agents.HeuristicAgent()
    : spec === 'random' ? new agents.RandomAgent({ seed: 1 })
    : spec === 'simplebot' ? new agents.SimpleBotAgent()
    : await agents.OnnxAgent.load(spec.replace(/^onnx:/, '').replace(/:greedy$/, ''), enc.obsSize, enc.actionSize, { greedy: true });
  let solved = 0, n = 0;
  for (const p of puzzles) {
    const env = new Env(enc, { u8: true });
    let t = env.reset(byName(p.deckA).cards, byName(p.deckB).cards, p.seed, { backup: !!agent.engine });
    for (const i of p.path) t = env.step(t.legal[i]);
    let key;
    if (agent.engine) {
      const action = agent.actEngine(env.game, t.playerId, env.decklists[t.playerId]);
      key = engineActionKey(env, action);
    } else {
      const [r] = await agent.act([{ obs: t.obs, legal: t.legal, env }]);
      key = env.current.options[t.legal.indexOf(r.action)].key;
    }
    n++;
    if (p.wins.includes(key)) solved++;
  }
  console.log(`${spec}: solved ${solved}/${n} (${(100 * solved / Math.max(n, 1)).toFixed(1)}%) of "${path.basename(file)}"`);
}

// Which option an engine action (SimpleBot's) corresponds to: the option whose action has the
// same shape.
function engineActionKey(env, action) {
  if (!action) return 'none';
  const same = (a, b) => a && b && a.type === b.type && JSON.stringify(a) === JSON.stringify(b);
  const o = env.current.options.find(x => same(x.action, action));
  return o ? o.key : 'other:' + action.type;
}

function merge() {
  const out = flag('out', DEFAULT_FILE);
  const files = argv.slice(1).filter((a, i, all) => !a.startsWith('--') && all[i - 1] !== '--out');
  const puzzles = files.flatMap(f => JSON.parse(fs.readFileSync(f, 'utf8')).puzzles);
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, JSON.stringify({ kind: 'win this turn', nodeLimit: NODE_LIMIT, puzzles }, null, 1));
  console.log(`merged ${puzzles.length} puzzles into ${out}`);
}

if (MODE === 'merge') merge();
else if (MODE === 'generate') generate().catch(e => { console.error(e); process.exitCode = 1; });
else if (MODE === 'score') score().catch(e => { console.error(e); process.exitCode = 1; });
else console.log('usage: puzzles.js generate|score [options]');
