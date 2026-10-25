// Test for env/staged/tokens.js: a face-down Pokemon (Challenge! TR) is hidden from the player who doesn't own it.
// The staged file is compiled as if it were env/tokens.js (same requires), so this tests the exact file to deploy, and
// compares it with the live env/tokens.js. Read-only use of the env. CPU, one process, under a minute.
//   node env/staged/tokens_facedown_test.js [randomGames=300] [seconds=90]
// Cases (rigs from the fixverify Challenge! script, challenge_fresh.js V6 / E5):
//   F1 V6 rebuilt: at the opponent's search, its view is the same whether I benched Abra or Voltorb face down
//      (history 0 and 2; control = same pick twice); the live encoder's result is printed (before deploy: the leak)
//   F2 the hidden slot still reads occupied and played this turn, card 0 and HP 0; same shape and token count as live
//   F3 the owner still sees its face-down card; its view equals the live encoder's
//   F4 after both finish (face up) the opponent sees the card; equal to live
//   F5 engine path, opponent answers first: my view at my search hides the opponent's face-down picks
//   F6 random-policy games (Challenge! decks and the archived lists; 1 in 4 under roundTurns), both seats encoded at
//      every decision: equal to live byte for byte except where the viewer faces an opponent's face-down slot, and
//      there only that slot's card id and HP byte differ; every face-down slot falls inside an open Challenge! search
//      (checked from the prompt, not from isPublic)
'use strict';
const fs = require('fs');
const path = require('path');
const Module = require('module');
const ENV = path.join(__dirname, '..');
const { C } = require(ENV + '/engine.js');
const { Game } = require(ENV + '/game.js');
const { Rng } = require(ENV + '/rng.js');
const { archivedDecks } = require(ENV + '/decks.js');
const Live = require(ENV + '/tokens.js');

function loadStaged() {
  const file = path.join(ENV, 'tokens.staged-under-test.js');   // not a real file: only sets __dirname and require paths
  const m = new Module(file, module);
  m.filename = file; m.paths = Module._nodeModulePaths(ENV);
  m._compile(fs.readFileSync(path.join(__dirname, 'tokens.js'), 'utf8'), file);
  return m.exports;
}
const Staged = loadStaged();
const [GAMES, SECS] = [Number(process.argv[2] || 300), Number(process.argv[3] || 90)];

// ---------------------------------------------------------------- rigging (challenge_fresh.js)
const SPEC = [['Challenge! TR', 4], ['Abra BS', 4], ['Kadabra BS', 4], ['Hitmonchan BS', 4], ['Scyther JU', 4],
  ['Electabuzz BS', 4], ['Squirtle BS', 4], ['Voltorb BS', 4], ['Clefairy Doll BS', 2], ['Mysterious Fossil FO', 2],
  ['Bill BS', 2], ['Psychic Energy BS', 12], ['Fighting Energy BS', 10]];
const DECK = SPEC.flatMap(([n, k]) => Array(k).fill(n));
const FILL_ORDER = ['Hitmonchan BS', 'Scyther JU', 'Electabuzz BS', 'Squirtle BS', 'Voltorb BS', 'Abra BS'];
function start(seed) {
  const g = new Game(DECK, DECK, seed);
  for (let k = 0; k < 400; k++) {
    const d = g.decision();
    if (!d) throw new Error('ended in setup ' + (g.error && g.error.message));
    if (!d.prompt && g.state.phase === C.GamePhase.PLAYER_TURN) break;
    g.step(0);
  }
  return g;
}
const ME = g => g.state.players[g.state.activePlayer];
const OP = g => g.state.players[1 - g.state.activePlayer];
function grab(pl, name, to) {
  for (const z of [pl.deck, pl.hand, pl.discard]) {
    const c = z.cards.find(x => x.fullName === name);
    if (c) { z.moveCardTo(c, to); return c; }
  }
  throw new Error('no free ' + name + ' for P' + pl.id);
}
function board(pl, active, bench, hand) {
  pl.hand.moveTo(pl.deck);
  for (const s of [pl.active, ...pl.bench]) {
    for (const l of [s.pokemons, s.energies, s.trainers]) l.moveTo(pl.deck);
    s.damage = 0; s.specialConditions = []; s.pokemonPlayedTurn = -5;
  }
  grab(pl, active, pl.active.pokemons);
  bench.forEach((n, i) => {
    if (n !== '*') return grab(pl, n, pl.bench[i].pokemons);
    const f = FILL_ORDER.find(x => [pl.deck, pl.hand, pl.discard].some(z => z.cards.some(c => c.fullName === x)));
    grab(pl, f, pl.bench[i].pokemons);
  });
  for (const h of hand || []) grab(pl, h, pl.hand);
}
const fillBench = k => Array(k).fill('*');
function reset(g) { g.cached = null; g.deadEnds = []; g.chain = null; g.space = null; g.spaceFor = -1; g.picks = []; g.pickedKeys = []; }
const openPrompts = g => g.state.prompts.filter(p => p.result === undefined);
function key(g, k) {
  const d = g.decision(); if (!d) throw new Error('no decision: ' + (g.error && g.error.message));
  const i = d.options.findIndex(o => o.key === k);
  if (i < 0) throw new Error('not offered: ' + k + ' ; offered ' + d.options.map(o => o.key).join(' '));
  g.step(i); if (g.error) throw new Error('engine error after ' + k + ': ' + g.error.message);
}
function engAnswer(g, prompt, raw) {
  const decoded = prompt.decode(raw, g.state);
  if (!prompt.validate(decoded, g.state)) throw new Error('invalid answer for ' + prompt.type);
  g.dispatch(new C.ResolvePromptAction(prompt.id, decoded));
  if (g.error) throw new Error('engine error on answer: ' + g.error.message);
}
function engPlay(g, name) {
  const me = ME(g); const i = me.hand.cards.findIndex(c => c.fullName === name);
  g.dispatch(new C.PlayCardAction(me.id, i, { player: C.PlayerType.BOTTOM_PLAYER, slot: C.SlotType.ACTIVE, index: 0 }));
  if (g.error) throw new Error('engine error on play: ' + g.error.message);
}
const basicIdx = (prompt, want) => want.map(n => prompt.cards.cards.findIndex(c => c.fullName === n));

// ---------------------------------------------------------------- encoders and comparison
const live = new Live.TokenEncoder(), staged = new Staged.TokenEncoder();
const FIELDS = ['tokCard', 'tokKind', 'tokAux', 'glob', 'slots', 'cand'];
const sig = e => FIELDS.map(f => Array.from(e[f]).join(',')).join('|') + '|' + e.nTok + '|' + e.nCand;
function diffs(a, b) {   // [field, index] where two encodings differ
  const out = [];
  for (const f of FIELDS) for (let i = 0; i < a[f].length; i++) if (a[f][i] !== b[f][i]) out.push([f, i]);
  if (a.nTok !== b.nTok) out.push(['nTok', 0]);
  if (a.nCand !== b.nCand) out.push(['nCand', 0]);
  return out;
}
const enc = (e, g, pid, opts, hist = 0) => { e.history = hist; const r = e.encode(g, pid, null, opts); e.history = 0; return r; };
const ABRA = staged.cardId.get('Abra BS');
const SLOT_F = Staged.SLOT_F;

const rows = [];
function check(id, what, expect, fn) {
  let got; try { got = String(fn()); } catch (e) { got = 'EXCEPTION ' + (e && e.stack); }
  const ok = got === String(expect);
  rows.push(ok);
  console.log((ok ? 'PASS ' : 'FAIL ') + id + ' | ' + what + '\n     expected: ' + expect + '\n     got:      ' + got);
}

// The V6 rig: I hold Challenge!, both sides have 2 benched; I accept-path pick `pick` into my B2, then it's the opponent's search.
function v6(pick) {
  const g = start(561); const me = ME(g), op = OP(g);
  board(me, 'Squirtle BS', fillBench(2), ['Challenge! TR']); board(op, 'Squirtle BS', fillBench(2)); reset(g);
  key(g, 'trainer|Challenge! TR|-'); key(g, 'res|yes'); key(g, 'pick|' + pick); key(g, 'done');
  const d = g.decision(); if (d.playerId !== op.id) throw new Error('not the opponent search');
  if (me.bench[2].pokemons.isPublic !== false || me.bench[2].pokemons.cards[0].fullName !== pick) throw new Error('rig: B2 not face down ' + pick);
  return { g, me, op, d };
}

check('F1', 'V6 rebuilt: opponent view at its search, Abra vs Voltorb face down in my B2 (history 0 / 2); control = same pick twice',
  'staged: control=same h0=same h2=same', () => {
    const a = v6('Abra BS'), a2 = v6('Abra BS'), b = v6('Voltorb BS');
    const s = (x, e, h) => sig(enc(e, x.g, x.op.id, x.d.options, h));
    return 'staged: control=' + (s(a, staged, 0) === s(a2, staged, 0) ? 'same' : 'differs') +
      ' h0=' + (s(a, staged, 0) === s(b, staged, 0) ? 'same' : 'differs') + ' h2=' + (s(a, staged, 2) === s(b, staged, 2) ? 'same' : 'differs') +
      (console.log('     (F1 detail, live env/tokens.js: h0=' + (s(a, live, 0) === s(b, live, 0) ? 'same' : 'differs, the leak') + ')'), '');
  });

check('F2', 'hidden slot (opponent view slot 9 = my B2, token 10): occupied, played this turn, card 0, HP 0; my empty B3 (index 10) unoccupied; vs live only that card id and HP byte differ; same sizes and nTok',
  'card=0 occupied=48 playedTurn=48 hp=0 emptyB3occ=0 diffVsLive=withinCardAndHp sizes=same nTok=same', () => {
    const { g, op, d } = v6('Abra BS');
    const e = enc(staged, g, op.id, d.options), l = enc(live, g, op.id, d.options);
    const o = 9 * SLOT_F;
    if (e.tokKind[10] !== Staged.KIND.SLOT || e.tokAux[10] !== 9) throw new Error('token 10 is not the SLOT of slot 9');
    const sizes = FIELDS.every(f => e[f].length === l[f].length) && JSON.stringify(staged.sizes) === JSON.stringify(live.sizes);
    return 'card=' + e.tokCard[10] + ' occupied=' + e.slots[o] + ' playedTurn=' + e.slots[o + 9] + ' hp=' + e.slots[o + 2] +
      ' emptyB3occ=' + e.slots[10 * SLOT_F] + ' diffVsLive=' + (diffs(l, e).every(([f, i]) => (f === 'tokCard' && i === 10) || (f === 'slots' && i === 9 * SLOT_F + 2)) ? 'withinCardAndHp' : JSON.stringify(diffs(l, e))) +
      ' sizes=' + (sizes ? 'same' : 'differs') + ' nTok=' + (e.nTok === l.nTok ? 'same' : 'differs');
  });

check('F3', 'owner view at the same moment: my B2 (slot 3, token 4) shows Abra with its HP; staged = live byte for byte',
  'card=Abra hp=' + Math.round(30 / 10 / 12 * 48) + ' equalLive=true', () => {
    const { g, me } = v6('Abra BS');
    const e = enc(staged, g, me.id, []), l = enc(live, g, me.id, []);
    return 'card=' + (e.tokCard[4] === ABRA ? 'Abra' : e.tokCard[4]) + ' hp=' + e.slots[3 * SLOT_F + 2] + ' equalLive=' + (sig(e) === sig(l));
  });

check('F4', 'after the opponent finishes (cards face up), at my next main decision: opponent view shows Abra at slot 9 (token 10); staged = live',
  'isPublic=true card=Abra equalLive=true', () => {
    const { g, me, op } = v6('Abra BS');
    key(g, 'done');
    for (let k = 0; k < 10 && g.decision() && g.decision().prompt; k++) g.step(0);
    const d = g.decision(); if (d.prompt || d.playerId !== me.id) throw new Error('not my main phase');
    const e = enc(staged, g, op.id, []), l = enc(live, g, op.id, []);
    return 'isPublic=' + me.bench[2].pokemons.isPublic + ' card=' + (e.tokCard[10] === ABRA ? 'Abra' : e.tokCard[10]) + ' equalLive=' + (sig(e) === sig(l));
  });

check('F5', 'engine path, opponent answers first (Abra vs Voltorb into its B3): my view at my still-open search is the same; the opponent sees its own',
  'staged=same oppOwnCard=Abra', () => {
    const run = pick => {
      const g = start(252); const me = ME(g), op = OP(g);
      board(me, 'Squirtle BS', fillBench(3), ['Challenge! TR']); board(op, 'Squirtle BS', fillBench(3)); reset(g);
      engPlay(g, 'Challenge! TR'); engAnswer(g, openPrompts(g)[0], true);
      const po = openPrompts(g).find(p => p.playerId === op.id);
      engAnswer(g, po, basicIdx(po, [pick]));
      if (op.bench[3].pokemons.isPublic !== false || openPrompts(g).length !== 1) throw new Error('rig: opponent B3 not face down');
      reset(g);
      return { g, me, op };
    };
    const a = run('Abra BS'), b = run('Voltorb BS');
    const s = (x, e) => sig(enc(e, x.g, x.me.id, []));
    const own = enc(staged, a.g, a.op.id, []).tokCard[1 + 4];   // the opponent's own B3: slot 4, token 5
    console.log('     (F5 detail, live env/tokens.js: ' + (s(a, live) === s(b, live) ? 'same' : 'differs, the leak') + ')');
    return 'staged=' + (s(a, staged) === s(b, staged) ? 'same' : 'differs') +
      ' oppOwnCard=' + (own === ABRA ? 'Abra' : own);
  });

// F6: random-policy games. Viewer v faces a hidden slot iff an opponent slot of v has pokemons.isPublic false.
check('F6', 'random-policy games, both seats at every decision, history 2: staged = live except when facing a face-down slot, and there only its card id + HP byte',
  'ok', () => {
    const FUZZ = [['Challenge! TR', 4], ['Abra BS', 4], ['Kadabra BS', 3], ['Hitmonchan BS', 4], ['Scyther JU', 4],
      ['Electabuzz BS', 4], ['Squirtle BS', 4], ['Voltorb BS', 4], ['Bill BS', 3], ['Professor Oak BS', 2],
      ['Psychic Energy BS', 12], ['Fighting Energy BS', 12]].flatMap(([n, k]) => Array(k).fill(n));
    const lists = archivedDecks().map(d => d.cards);
    const t0 = Date.now();
    const t = { games: 0, archivedGames: 0, roundGames: 0, encodings: 0, equal: 0, facing: 0, facingOk: 0, outsideWindow: 0,
      bad: 0, errors: 0 };
    const bad = [];
    // Independent of isPublic: a Challenge! search (its ChooseCardsPrompt message) is open and unanswered.
    const challengeOpen = g => g.state.prompts.some(p => p.result === undefined && p.message === 'CHOOSE_CARD_TO_PUT_ONTO_BENCH');
    for (let gi = 0; gi < GAMES && (Date.now() - t0) / 1000 < SECS; gi++) {
      const arch = gi % 3 === 2;   // one game in 3 on two archived lists, the rest on the Challenge! deck
      const round = gi % 4 === 3;  // one game in 4 under the 2000 round rule (roundTurns) instead of a turn cap
      const rng = new Rng(9000 + gi);
      const [d0, d1] = arch ? [lists[rng.int(lists.length)], lists[rng.int(lists.length)]] : [FUZZ, FUZZ];
      const g = new Game(d0, d1, 9000 + gi, round ? { roundTurns: 45 } : { maxTurns: 60 });
      for (let k = 0; k < 6000; k++) {
        const d = g.decision();
        if (!d) break;
        for (const p of g.state.players) {
          const opts = p.id === d.playerId ? d.options : [];
          const decks = { [g.state.players[0].id]: d0, [g.state.players[1].id]: d1 };
          live.history = staged.history = 2;
          const l = live.encode(g, p.id, decks, opts), e = staged.encode(g, p.id, decks, opts);
          live.history = staged.history = 0;
          t.encodings++;
          const opp = g.state.players.find(x => x.id !== p.id);
          const hid = [opp.active, ...opp.bench].map((s, j) => s.pokemons.cards.length && s.pokemons.isPublic === false ? 6 + j : -1).filter(j => j >= 0);
          const df = diffs(l, e);
          if (!hid.length) { if (df.length) { t.bad++; bad.push('no face-down, differs ' + JSON.stringify(df.slice(0, 4))); } else t.equal++; continue; }
          t.facing++;
          if (!challengeOpen(g)) { t.outsideWindow++; t.bad++; bad.push('face-down outside a Challenge! search ' + JSON.stringify(hid)); continue; }
          const allowed = new Set(hid.flatMap(j => ['tokCard:' + (1 + j), 'slots:' + (j * SLOT_F + 2)]));
          const okHere = df.every(([f, i]) => allowed.has(f + ':' + i)) && hid.every(j => e.tokCard[1 + j] === 0 && e.tokKind[1 + j] === Staged.KIND.SLOT && e.slots[j * SLOT_F] > 0);
          if (okHere) t.facingOk++; else { t.bad++; bad.push('face-down ' + JSON.stringify(hid) + ' diffs ' + JSON.stringify(df.slice(0, 6))); }
        }
        g.step(rng.int(d.options.length));
        if (g.error) { t.errors++; break; }
      }
      t.games++; if (arch) t.archivedGames++; if (round) t.roundGames++;
    }
    console.log('     (F6 detail: ' + JSON.stringify(t) + ' secs=' + ((Date.now() - t0) / 1000).toFixed(1) + ')');
    for (const b of bad.slice(0, 5)) console.log('     BAD ' + b);
    return t.bad === 0 && t.errors === 0 && t.facing > 0 && t.equal > 0 ? 'ok' : 'bad=' + t.bad + ' errors=' + t.errors + ' facing=' + t.facing;
  });

const pass = rows.filter(Boolean).length;
console.log('\n' + pass + '/' + rows.length + ' checks pass');
process.exitCode = pass === rows.length ? 0 : 1;
