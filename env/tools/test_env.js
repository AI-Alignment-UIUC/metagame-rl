// Checks of the RL environment API and encoder (plan items A1.3, A1.4), on random-policy games:
//   - a seed replays exactly: same seed and actions give the same observations and result
//   - every observation feature is a multiple of 1/48 that fits a byte (encodeU8 is exact)
//   - every option the game offers maps into the action space (actionId never throws), and
//     the ids on offer at a decision are distinct
//   - no engine errors, every game finishes
// It prints a hash of every observation of every game (`obs hash`), so two builds can be compared.
//
// --tokens (or --history W / --chain K): the token observations (env/tokens.js) instead of the identity encoder's.
// --chain K > 0 (the chain head, rl/token_model.py chain): at every decision the last K candidate rows must hold the
// deciding player's own decisions of the turn, as rebuilt here from this script's own record of the steps (oldest first,
// right-aligned, the option's candidate encoding, a slot pick's Pokemon, role in extra: 1 the opener of the open prompt,
// 2 an answer since it, 3 an earlier move, 4 an earlier answer); a census of the rows; and three scripted turns (Computer
// Search, Super Energy Removal, Gust of Wind) whose rows are checked against the picks the script made and printed.
//
// Run: node env/tools/test_env.js [--games 200] [--tokens] [--history W] [--chain K] [--hash-out hashes.json]
'use strict';
const crypto = require('crypto');
const fs = require('fs');
const { Env } = require('../env.js');
const { Encoder } = require('../encode.js');
const { TokenEncoder, VERB, MAX_CAND } = require('../tokens.js');
const { allSlots } = require('../legal.js');
const { archivedDecks } = require('../decks.js');
const { Rng } = require('../rng.js');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const GAMES = Number(flag('games', 200));
const CHAIN = Number(flag('chain', 0)), HISTORY = Number(flag('history', 0));
const TOKENS = argv.includes('--tokens') || flag('chain', null) !== null || flag('history', null) !== null;
const HASH_OUT = flag('hash-out', null);

const decks = archivedDecks();
const enc = TOKENS ? new TokenEncoder() : new Encoder([...new Set(decks.flatMap(d => d.cards))]);
if (TOKENS) { enc.history = HISTORY; enc.chain = CHAIN; }
const failures = [];
const fail = msg => { if (failures.length < 20) failures.push(msg); };

const tokenBuffers = o => [o.tokCard, o.tokKind, o.tokAux, o.glob, o.slots, o.cand].map(a => Buffer.from(a.buffer, a.byteOffset, a.byteLength));

// ---- the chain rows (--chain K) ------------------------------------------------------------------------------------
// One record per step, kept by this script: who acted, the game turn, whether it answered a prompt, the option key, for
// a slot pick (pick_slot, pick_move_damage's target) the visible Pokemon in that slot before the step, and for a retreat
// the retreating Active.
function stepRecord(game, d, key) {
  const me = game.state.players.find(p => p.id === d.playerId);
  let slotCode = null;
  if (key.startsWith('pick|')) {
    const item = key.slice(5), m = /^(o?[AB]\d?)>(o?[AB]\d?)$/.exec(item);
    if (m) slotCode = m[2];
    else if (/^o?[AB]\d?$/.test(item)) slotCode = item;
  }
  let kc = null;
  if (slotCode) {
    const s = allSlots(game.state, me).find(x => x.code === slotCode);
    const top = s && s.slot.getPokemonCard();
    if (top && (s.mine || s.slot.pokemons.isPublic !== false)) kc = top.fullName;
  }
  const active = me && me.active.getPokemonCard();
  const c = key.startsWith('retreat|') && active ? active.fullName : null;
  return { p: d.playerId, t: game.state.turn, pr: !!d.prompt, key, kc, c, slotCode };
}

const roleOf = r => Math.floor(r[5] / 64);

// The rows the encoder must write at this decision, from the records (not from game.history).
function expectedRows(game, d, records, K) {
  const state = game.state, me = state.players.find(p => p.id === d.playerId);
  const turn = records.filter(e => e.t === state.turn);
  const own = turn.filter(e => e.p === d.playerId);
  const lastMove = [...turn].reverse().find(e => !e.pr);
  const opener = d.prompt && lastMove && lastMove.p === d.playerId ? own.indexOf(lastMove) : -1;
  let rows = own.map((e, j) => ({ e, role: j === opener ? 1 : opener >= 0 && j > opener ? 2 : e.pr ? 4 : 3 }));
  if (rows.length > K) {
    rows = opener >= 0 && opener < rows.length - K ? [rows[opener], ...rows.slice(rows.length - K + 1)] : rows.slice(rows.length - K);
  }
  const slots = allSlots(state, me);
  return rows.map(({ e, role }) => {
    const r = enc.candidate(e.key, d.prompt, me.active.getPokemonCard(), state, me);
    if (!r[1] && (e.kc || e.c)) r[1] = enc.cardId.get(e.kc || e.c) || 0;
    if (e.slotCode) {                           // the slot no longer holds the Pokemon picked: no slot reference
      const s = slots.find(x => x.code === e.slotCode), top = s && s.slot.getPokemonCard();
      const at = r[0] === VERB.pick_slot ? 2 : 3;
      if (!top || top.fullName !== e.kc) r[at] = 0;
    }
    r[5] += 64 * role;
    return r;
  });
}

function compareRows(got, want, where) {
  if (got.length !== want.length) { fail(`${where}: ${got.length} chain rows, want ${want.length}`); return false; }
  for (let j = 0; j < got.length; j++) {
    const g = got[j], w = want[j];
    if (g.some((x, i) => x !== w[i])) {
      fail(`${where}: chain row ${j} is [${g}], want [${w}]`);
      return false;
    }
  }
  return true;
}

// The rows in the cand tail (right-aligned in the last K rows), checking that the rows between the options and them are
// empty.
function tailRows(o, K, where) {
  const rows = [];
  for (let i = o.nCand; i < MAX_CAND - K; i++) {
    if (o.cand.subarray(i * 6, i * 6 + 6).some(x => x !== 0)) { fail(`${where}: candidate row ${i} past the options is not empty`); break; }
  }
  let started = false;
  for (let i = MAX_CAND - K; i < MAX_CAND; i++) {
    const r = Array.from(o.cand.subarray(i * 6, i * 6 + 6));
    if (r[0] > 0) { started = true; rows.push(r); } else if (started || r.some(x => x !== 0)) { fail(`${where}: chain rows not right-aligned`); break; }
  }
  return rows;
}

const census = { rows: 0, decisions: 0, withRows: 0, ownTrainerPrompts: 0, ownTrainerOpener: 0, turns: 0, turnsOverK: 0,
                 maxTurnEntries: 0, maxOptions: 0, prompts: 0, roles: [0, 0, 0, 0, 0] };

function checkChain(env, t, records, where, count) {
  const g = env.game, d = g.decision();
  const rows = tailRows(t.obs, CHAIN, where);
  compareRows(rows, expectedRows(g, d, records, CHAIN), where);
  if (!count) return;
  census.decisions++;
  census.rows += rows.length;
  if (rows.length) census.withRows++;
  for (const r of rows) census.roles[roleOf(r)]++;
  census.maxOptions = Math.max(census.maxOptions, d.options.length);
  if (d.prompt) census.prompts++;
  // an own Trainer's prompt: the player's latest move this turn (by the records) is a Trainer and a prompt is open
  const turn = records.filter(e => e.t === g.state.turn);
  const lastMove = [...turn].reverse().find(e => !e.pr);
  if (d.prompt && lastMove && lastMove.p === d.playerId && lastMove.key.startsWith('trainer|')) {
    census.ownTrainerPrompts++;
    const id = enc.cardId.get(lastMove.key.split('|')[1]);
    if (rows.some(r => roleOf(r) === 1 && r[0] === VERB.trainer && r[1] === id)) census.ownTrainerOpener++;
    else fail(`${where}: no opener row for ${lastMove.key}`);
  }
}

function play(g, count = true) {
  const env = new Env(enc);
  const pol = new Rng(77 + g);
  const h = crypto.createHash('sha1');
  let t = env.reset(decks[g % decks.length].cards, decks[(g * 5 + 1) % decks.length].cards, g);
  let steps = 0, maxByte = 0;
  const records = [];
  while (!t.done) {
    if (new Set(t.legal).size !== t.legal.length) fail(`game ${g} step ${steps}: duplicate action ids on offer`);
    if (TOKENS) {
      for (const b of tokenBuffers(t.obs)) h.update(b);
      h.update(`${t.obs.nTok},${t.obs.nCand}`);
    } else {
      for (const v of t.obs) {
        const b = v * 48;
        if (Math.abs(b - Math.round(b)) > 1e-4 || b < 0 || b > 255) { fail(`game ${g} step ${steps}: feature ${v} is not a byte multiple of 1/48`); break; }
        if (b > maxByte) maxByte = b;
      }
      h.update(Buffer.from(t.obs.buffer));
    }
    h.update(String(t.legal));
    if (CHAIN > 0) checkChain(env, t, records, `game ${g} step ${steps}`, count);
    const a = t.legal[pol.int(t.legal.length)];
    const d = env.game.decision();
    records.push(stepRecord(env.game, d, d.options[t.legal.indexOf(a)].key));
    t = env.step(a);
    steps++;
  }
  if (CHAIN > 0 && count) {
    const per = new Map();
    for (const e of records) per.set(e.t + ':' + e.p, (per.get(e.t + ':' + e.p) || 0) + 1);
    for (const n of per.values()) {
      census.turns++;
      if (n > CHAIN) census.turnsOverK++;
      census.maxTurnEntries = Math.max(census.maxTurnEntries, n);
    }
  }
  return { hash: h.digest('hex'), winner: t.winner, steps, error: t.error, maxByte };
}

// ---- scripted turns (--chain K) ------------------------------------------------------------------------------------
// Both seats: play the target Trainers whenever offered, attach Energy and bench Basics, never attack; prompts take the
// first pick, then done, then any other answer (cancel last). The first turn each target is played is checked at every
// decision of its chain, and its rows printed.
const TARGETS = ['Computer Search BS', 'Super Energy Removal BS', 'Gust of Wind BS'];
const SCRIPT_DECK = [...Array(4).fill('Computer Search BS'), ...Array(4).fill('Super Energy Removal BS'),
  ...Array(4).fill('Gust of Wind BS'), ...Array(4).fill('Hitmonchan BS'), ...Array(4).fill('Scyther JU'),
  ...Array(4).fill('Electabuzz BS'), ...Array(4).fill('Mewtwo PR'), ...Array(32).fill('Fighting Energy BS')];

function scriptChoice(d, targets) {
  const keys = d.options.map(o => o.key);
  const first = pred => keys.findIndex(pred);
  if (d.prompt) {
    for (const pred of [k => k.startsWith('pick|'), k => k === 'done', k => k.startsWith('res|') && k !== 'res|no', k => k !== 'cancel']) {
      const i = first(pred);
      if (i >= 0) return i;
    }
    return 0;
  }
  for (const pred of [k => targets.some(n => k.startsWith('trainer|' + n + '|')), k => k.startsWith('attach|') && k.endsWith('|A'),
    k => k.startsWith('basic|'), k => k.startsWith('attach|'), k => k === 'pass']) {
    const i = first(pred);
    if (i >= 0) return i;
  }
  return 0;
}

const CARD_NAME = TOKENS ? new Map([...enc.cardId].map(([n, id]) => [id, n])) : new Map();
const showRow = r => {
  const verb = Object.keys(VERB).find(v => VERB[v] === r[0]) || r[0];
  const card = r[1] ? CARD_NAME.get(r[1]) || r[1] : '-';
  return `${roleOf(r)}:${verb}(${card}${r[2] ? ', slot ' + r[2] : ''}${r[3] ? ', slot ' + r[3] : ''}${r[5] % 64 ? ', x' + (r[5] % 64) : ''})`;
};

function scripted() {
  const seen = new Map();          // target -> printed lines
  for (let seed = 1; seed <= 40 && seen.size < TARGETS.length; seed++) {
    const env = new Env(enc);
    let t = env.reset(SCRIPT_DECK, SCRIPT_DECK, 9000 + seed);
    const records = [];
    let active = null;             // the target's chain: { target, player, turn, lines, picks, pickRecords }
    while (!t.done && env.game.state.turn < 30 && seen.size < TARGETS.length) {
      const g = env.game, d = g.decision();
      const where = `scripted seed ${9000 + seed} turn ${g.state.turn} step ${g.steps}`;
      const rows = tailRows(t.obs, CHAIN, where);
      compareRows(rows, expectedRows(g, d, records, CHAIN), where);
      if (active && g.state.turn !== active.turn) { fail(`${where}: ${active.target}'s chain left its turn`); active = null; }
      if (active && d.playerId === active.player) {
        // the latest rows: the Trainer, then the script's own answers since it, in order; roles 1 / 2 while a prompt of
        // the chain is open, 3 / 4 at the next move
        const me = g.state.players.find(p => p.id === d.playerId);
        const tail = rows.slice(rows.length - 1 - active.picks.length);
        const verbs = active.picks.map(k => enc.candidate(k, d.prompt, me.active.getPokemonCard(), g.state, me)[0]);
        const lead = tail[0] && tail[0][0] === VERB.trainer && tail[0][1] === enc.cardId.get(active.target);
        const ok = lead && tail.length === 1 + verbs.length && tail.slice(1).every((r, j) => r[0] === verbs[j]) &&
          (d.prompt ? roleOf(tail[0]) === 1 && tail.slice(1).every(r => roleOf(r) === 2)
            : roleOf(tail[0]) === 3 && tail.slice(1).every(r => roleOf(r) === 4));
        if (!ok) fail(`${where}: ${active.target} rows ${tail.map(showRow).join(' ')}`);
        active.lines.push(`  ${d.prompt ? d.prompt.type + ' (' + d.options.length + ' options)' : 'next move'}: ${rows.map(showRow).join(' ')}`);
        if (!d.prompt) {
          if (active.target === 'Gust of Wind BS') {
            // the pick keeps the Pokemon picked; that Pokemon is now the opponent's Active, so the Bench slot it was
            // picked from holds another Pokemon and the row has no slot reference there
            const rec = active.pickRecords.find(e => e.key.startsWith('pick|oB'));
            const row = tail.find(r => r[0] === VERB.pick_slot);
            const slots = allSlots(g.state, me);
            const opp = slots.find(x => x.code === 'oA').slot.getPokemonCard();
            const there = rec ? slots.find(x => x.code === rec.slotCode).slot.getPokemonCard() : null;
            const moved = !there || !rec || there.fullName !== rec.kc;
            if (!(rec && row && rec.kc && row[1] === enc.cardId.get(rec.kc) && opp && opp.fullName === rec.kc && (moved ? row[2] === 0 : row[2] > 0))) {
              fail(`${where}: Gust of Wind's pick row ${row && showRow(row)}, picked ${rec && rec.kc}, now Active ${opp && opp.fullName}`);
            }
            if (rec) active.lines.push(`  (picked ${rec.kc} from ${rec.slotCode}; now the opponent's Active is ${opp && opp.fullName} and ${rec.slotCode} holds ${there ? there.fullName : 'nothing'})`);
          }
          seen.set(active.target, active.lines);
          active = null;
        }
      }
      const i = scriptChoice(d, TARGETS.filter(n => !seen.has(n)));
      const key = d.options[i].key;
      const rec = stepRecord(g, d, key);
      records.push(rec);
      if (active && d.playerId === active.player && d.prompt) { active.picks.push(key); active.pickRecords.push(rec); }
      if (!active && !d.prompt) {
        const target = TARGETS.find(n => key.startsWith('trainer|' + n + '|') && !seen.has(n));
        if (target) active = { target, player: d.playerId, turn: g.state.turn, picks: [], pickRecords: [],
          lines: [`${target} (seed ${9000 + seed}, turn ${g.state.turn}, player ${d.playerId}): ${key}`] };
      }
      t = env.step(t.legal[i]);
      if (t.error) fail(`${where}: engine error ${t.error.message || t.error}`);
    }
  }
  for (const n of TARGETS) {
    if (!seen.has(n)) fail(`scripted: ${n} was never played`);
    else console.log(seen.get(n).join('\n'));
  }
}

const t0 = Date.now();
let steps = 0, maxByte = 0;
const hashes = [];
for (let g = 0; g < GAMES; g++) {
  let a;
  try { a = play(g); } catch (e) { fail(`game ${g}: ${e.message}`); continue; }
  hashes.push(a.hash);
  steps += a.steps;
  maxByte = Math.max(maxByte, a.maxByte);
  if (a.error) fail(`game ${g}: engine error ${a.error.message || a.error}`);
  if (a.winner === -1) fail(`game ${g}: did not finish`);
  if (g % 4 === 0) {
    const b = play(g, false);
    if (b.hash !== a.hash || b.winner !== a.winner) fail(`game ${g}: replay differs`);
  }
}
const all = crypto.createHash('sha1').update(hashes.join(',')).digest('hex');
console.log(`${GAMES} games, ${steps} decisions in ${((Date.now() - t0) / 1000).toFixed(1)}s; ` +
  (TOKENS ? `token observations (history ${HISTORY}, chain ${CHAIN})` : `obs ${enc.obsSize}, actions ${enc.actionSize}, largest feature byte ${maxByte}`));
console.log(`obs hash ${all}`);
if (HASH_OUT) fs.writeFileSync(HASH_OUT, JSON.stringify({ games: GAMES, tokens: TOKENS, history: HISTORY, chain: CHAIN, all, hashes }, null, 1));
if (CHAIN > 0) {
  const c = census;
  console.log(`chain census (${c.decisions} decisions): rows ${(c.rows / c.decisions).toFixed(2)} a decision, ` +
    `${(100 * c.withRows / c.decisions).toFixed(1)}% with any; roles 1-4 ${c.roles.slice(1).join(' / ')}; ` +
    `an opener row on ${c.ownTrainerOpener} of ${c.ownTrainerPrompts} own-Trainer prompt rows ` +
    `(${(100 * c.ownTrainerOpener / Math.max(c.ownTrainerPrompts, 1)).toFixed(2)}%); player-turns over K = ${CHAIN} steps: ` +
    `${c.turnsOverK} of ${c.turns} (${(100 * c.turnsOverK / Math.max(c.turns, 1)).toFixed(2)}%), the longest ${c.maxTurnEntries}; ` +
    `max options ${c.maxOptions} (cap ${MAX_CAND - CHAIN})`);
  scripted();
}
for (const f of failures) console.log('FAIL', f);
console.log(failures.length ? 'FAIL' : 'PASS');
process.exitCode = failures.length ? 1 : 0;
