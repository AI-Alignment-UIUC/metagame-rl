// Verifies the legal-action enumerator (env/legal.js) against the oracle (env/oracle.js) on
// every decision of seeded random-policy games over the archived STS decks (plan item A1.2).
//
// For each decision it checks:
//   main phase  the enumerated option keys equal the oracle's accepted keys, apart from
//               accepted actions the rules forbid (reported as engine leniency, by category)
//   prompts     every enumerated answer passes decode + validate (soundness), and every legal
//               raw answer the oracle generates is reachable through the picks (completeness)
//   playing     the engine never throws on an enumerated option, and every game finishes
//
// Run: node env/tools/verify_enumerator.js [--games 10000] [--seed 1] [--workers 16]
//                                          [--every 1]   (check every Nth decision)
'use strict';
const { fork } = require('child_process');
const os = require('os');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const GAMES = Number(flag('games', 10000));
const SEED = Number(flag('seed', 1));
const WORKERS = Number(flag('workers', Math.max(1, os.cpus().length - 4)));
const EVERY = Number(flag('every', 1));

function runWorker(from, to) {
  const { Game } = require('../game.js');
  const { archivedDecks } = require('../decks.js');
  const { Rng } = require('../rng.js');
  const { turnOracle, promptOracle } = require('../oracle.js');
  const decks = archivedDecks();
  const r = {
    games: 0, finished: 0, errors: [], steps: 0, decisions: 0, checkedTurn: 0, checkedPrompt: 0,
    turnMismatch: 0, turnExamples: [], lax: {}, anomalies: {}, promptInvalid: 0, promptMissing: 0,
    promptExamples: [], replayExcluded: 0, promptChecks: 0, noCompleteness: {}, byPrompt: {},
  };
  const example = (list, x) => { if (list.length < 8) list.push(x); };
  for (let g = from; g < to; g++) {
    const seed = SEED * 1000003 + g;
    const pol = new Rng(seed ^ 0x9e3779b9);
    const a = decks[g % decks.length], b = decks[(g * 7 + 3 + Math.floor(g / decks.length)) % decks.length];
    const game = new Game(a.cards, b.cards, seed);
    let n = 0;
    while (!game.done) {
      const d = game.decision();
      if (!d) break;
      r.decisions++;
      if (n++ % EVERY === 0) {
        if (!d.prompt) {
          r.checkedTurn++;
          const o = turnOracle(game.state);
          const fast = new Set(d.options.map(x => x.key));
          const extra = [...fast].filter(k => !o.keys.has(k));
          const missing = [...o.keys].filter(k => !fast.has(k));
          if (extra.length || missing.length) {
            r.turnMismatch++;
            example(r.turnExamples, { game: g, step: game.steps, extra, missing });
          }
          for (const [k, v] of o.lax) r.lax[k] = (r.lax[k] || 0) + v;
          for (const k of o.anomalies) r.anomalies[k] = (r.anomalies[k] || 0) + 1;
        } else if (game.picks.length === 0) {
          r.checkedPrompt++;
          const p = d.prompt;
          const res = promptOracle(p, game.state, () => pol.float());
          r.promptChecks += res.checked;
          r.byPrompt[p.type] = (r.byPrompt[p.type] || 0) + 1;
          if (res.noCompleteness) r.noCompleteness[p.type] = (r.noCompleteness[p.type] || 0) + 1;
          r.promptInvalid += res.invalid.length;
          let missing = res.missing;
          if (p.type === 'Choose attack' && game.chain) {
            // The game drops answers that fail when replayed; those aren't missing.
            const offered = new Set(d.options.map(x => JSON.stringify(x.raw)));
            missing = missing.filter(m => {
              const raw = JSON.parse(m.replace(/^raw /, ''));
              if (offered.has(JSON.stringify(raw))) return false;
              if (!game.replayAccepts(p, raw)) { r.replayExcluded++; return false; }
              return true;
            });
          }
          r.promptMissing += missing.length;
          if (res.invalid.length || missing.length) {
            example(r.promptExamples, { game: g, step: game.steps, type: p.type, message: p.message, invalid: res.invalid.slice(0, 5), missing: missing.slice(0, 5) });
          }
        }
      }
      game.step(pol.int(d.options.length));
    }
    r.games++;
    r.steps += game.steps;
    if (game.error) example(r.errors, { game: g, step: game.steps, after: game.lastKey, error: String(game.error.message || game.error) });
    else if (game.winner !== -1) r.finished++;
  }
  return r;
}

function merge(a, b) {
  for (const k of Object.keys(b)) {
    if (typeof b[k] === 'number') a[k] = (a[k] || 0) + b[k];
    else if (Array.isArray(b[k])) a[k] = (a[k] || []).concat(b[k]).slice(0, 12);
    else { a[k] = a[k] || {}; for (const j of Object.keys(b[k])) a[k][j] = (a[k][j] || 0) + b[k][j]; }
  }
  return a;
}

if (process.env.VERIFY_WORKER) {
  process.on('message', ({ from, to }) => { process.send(runWorker(from, to)); process.exit(0); });
} else {
  const t0 = Date.now();
  const chunks = [];
  const per = Math.ceil(GAMES / WORKERS);
  for (let w = 0; w < WORKERS; w++) {
    const from = w * per, to = Math.min(GAMES, from + per);
    if (from < to) chunks.push({ from, to });
  }
  let total = {};
  let doneCount = 0;
  Promise.all(chunks.map(c => new Promise((resolve, reject) => {
    const child = fork(__filename, process.argv.slice(2), { env: { ...process.env, VERIFY_WORKER: '1' } });
    child.on('message', m => { total = merge(total, m); doneCount++; resolve(); });
    child.on('exit', code => { if (code !== 0) reject(new Error('worker exited ' + code)); });
    child.send(c);
  }))).then(() => {
    const s = ((Date.now() - t0) / 1000).toFixed(0);
    const t = total;
    console.log(`${t.games} games (${t.finished} finished, ${t.errors.length ? t.errors.length + '+' : 0} engine errors), ${t.steps} steps, ${t.decisions} decisions, ${s}s on ${chunks.length} workers`);
    console.log(`main phase: ${t.checkedTurn} decisions checked, ${t.turnMismatch} mismatches`);
    console.log(`prompts:    ${t.checkedPrompt} prompts checked, ${t.promptChecks} legal raw answers tried, ` +
      `${t.promptMissing} missing, ${t.promptInvalid} invalid enumerated answers, ${t.replayExcluded} excluded by replay`);
    console.log('prompts checked by type:', JSON.stringify(t.byPrompt));
    if (Object.keys(t.noCompleteness || {}).length) console.log('no completeness check for:', JSON.stringify(t.noCompleteness));
    console.log('engine leniency (accepted, but forbidden by the rules):', JSON.stringify(t.lax));
    if (Object.keys(t.anomalies || {}).length) console.log('anomalies:', JSON.stringify(t.anomalies));
    for (const e of t.errors || []) console.log('ERROR', JSON.stringify(e));
    for (const e of t.turnExamples || []) console.log('TURN', JSON.stringify(e));
    for (const e of t.promptExamples || []) console.log('PROMPT', JSON.stringify(e));
    const ok = !(t.errors || []).length && !t.turnMismatch && !t.promptMissing && !t.promptInvalid
      && !Object.keys(t.anomalies || {}).length && t.finished === t.games;
    console.log(ok ? 'PASS' : 'FAIL');
    process.exitCode = ok ? 0 : 1;
  }).catch(e => { console.error(e); process.exitCode = 2; });
}
