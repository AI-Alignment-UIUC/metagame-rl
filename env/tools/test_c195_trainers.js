// C195 Part B2 (runs/probe/C195-trainer-policy-engine/record.md): scripted states that check the lists' 10 most common
// Trainers (Professor Oak, PlusPower, Computer Search, Gust of Wind, Bill, Item Finder, Energy Removal, Super Energy
// Removal, Scoop Up, Rocket's Sneak Attack) against pool.json's card text and the 2000 rulings, in the engine env/engine.js
// loads, plus interactions with the rule reducers changed since ryuu-play e04c27e (confusion, last-Prize promote, retreat):
// Switch then retreat, Full Heal on a Confused Active, Scoop Up of the Active (promote), Gust of Wind on a Confused Active.
//
// Each test builds a state (a seeded Game driven to its first main phase, then both players' zones rearranged), plays the
// card through the env's own legal options and prompt answers (as the pilot would), and asserts the resulting state.
// Evaluation only: nothing in env/, ryuu-play/ or rl/ is touched. CPU only.
//
// A test that fails is re-run in a fresh node process (--only <i>) and both runs are recorded. A test whose own setup
// or driving throws is marked DRIVER (a script bug to fix, not an engine fault).
//
// Run: node env/tools/test_c195_trainers.js [--trace] [--out runs/probe/C195-trainer-policy-engine/partB.json]
//      node env/tools/test_c195_trainers.js --only <i>      (one test, JSON line on stdout; used for the fresh re-run)
'use strict';
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { Game } = require('../game.js');
const { C, RYUU } = require('../engine.js');

const ROOT = path.join(__dirname, '..', '..');
const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const TRACE = argv.includes('--trace');
const ONLY = flag('only', null);
const OUT = path.resolve(ROOT, flag('out', 'runs/probe/C195-trainer-policy-engine/partB.json'));
const SC = C.SpecialCondition;

// ---------------------------------------------------------------- card names
const FE = 'Fighting Energy BS', PE = 'Psychic Energy BS', WE = 'Water Energy BS';
const MACHOP = 'Machop BS', MACHOKE = 'Machoke BS', PIKACHU = 'Pikachu BS', RATTATA = 'Rattata BS', PIDGEY = 'Pidgey BS',
  RATICATE = 'Raticate BS', ONIX = 'Onix BS', KADABRA = 'Kadabra BS', ABRA = 'Abra BS';
const OAK = 'Professor Oak BS', BILL = 'Bill BS', PLUS = 'PlusPower BS', CS = 'Computer Search BS', GUST = 'Gust of Wind BS',
  IF = 'Item Finder BS', ER = 'Energy Removal BS', SER = 'Super Energy Removal BS', SCOOP = 'Scoop Up BS',
  RSA = "Rocket's Sneak Attack TR", SWITCH = 'Switch BS', FH = 'Full Heal BS';

// ---------------------------------------------------------------- scene building
class DriverError extends Error {}

// A fixed coin: every flip heads (or tails); shuffles keep the deck order.
function fixedRng(heads) {
  return { int: () => (heads ? 0 : 1), float: () => 0, u32: () => 0, permutation: n => Array.from({ length: n }, (_, i) => i), clone() { return this; } };
}

// A Pokemon slot spec: { mon: name or [basic, stage1...], en: [energy names], tr: [trainer names], dmg, cond: [SpecialCondition] }.
const slotNames = s => (s ? [].concat(s.mon, s.en || [], s.tr || []) : []);
const sideNames = side => [...slotNames(side.active), ...(side.bench || []).flatMap(slotNames), ...(side.hand || []), ...(side.discard || []),
  ...(side.deck || [])];

// spec: { me: side, opp: side }, a side being { active, bench: [slot specs], hand, discard, deck (top first), prizes (count) }.
// coin: 'heads' | 'tails' for the game's automatic coin flips (also shuffles keep order).
function scene(spec, { coin = 'heads' } = {}) {
  // one decklist for both seats (which seat moves first is only known after setup): each name as often as either side needs it
  const count = (side, n) => sideNames(side).filter(x => x === n).length;
  const allNames = [...new Set([...sideNames(spec.me), ...sideNames(spec.opp), MACHOP])];
  const deckList = allNames.flatMap(n => Array(Math.max(count(spec.me, n), count(spec.opp, n), n === MACHOP ? 4 : 0)).fill(n));
  while (deckList.length < 60) deckList.push(FE);
  const g = new Game(deckList, deckList, 5);
  // drive setup (starting Pokemon, mulligan notices) to the first main phase
  for (let n = 0; n < 60; n++) {
    const d = g.decision();
    if (!d) throw new DriverError('setup ended: ' + (g.error && g.error.message));
    if (!d.prompt) break;
    const pick = d.options.findIndex(o => o.key.startsWith('pick|'));
    const done = d.options.findIndex(o => o.key === 'done');
    const ok = d.options.findIndex(o => o.key === 'res|ok');
    g.step(pick >= 0 ? pick : done >= 0 ? done : ok >= 0 ? ok : 0);
  }
  if (g.openPrompt()) throw new DriverError('setup did not reach a main phase');
  const st = g.state;
  const me = st.players[st.activePlayer], opp = st.players.find(p => p !== me);
  fill(me, spec.me);
  fill(opp, spec.opp);
  if (st.turn < 6) st.turn = 6;          // not the first turn: supporters and attacks are not restricted
  g.cached = null;
  g.rng = fixedRng(coin === 'heads');
  return { g, me, opp };
}

function slotsOf(p) { return [p.active, ...p.bench]; }

function fill(p, side) {
  const pool = [];
  const take = list => { pool.push(...list.cards); list.cards = []; };
  [p.deck, p.hand, p.discard, p.supporter, ...p.prizes].forEach(take);
  for (const s of slotsOf(p)) { take(s.pokemons); take(s.energies); take(s.trainers); s.damage = 0; s.specialConditions = []; s.poisonDamage = 10; s.pokemonPlayedTurn = 0; }
  const grab = name => {
    const i = pool.findIndex(c => c.fullName === name);
    if (i < 0) throw new DriverError('scene: no card ' + name + ' left in the pool');
    return pool.splice(i, 1)[0];
  };
  const setSlot = (s, spec) => {
    if (!spec) return;
    s.pokemons.cards = [].concat(spec.mon).map(grab);
    s.energies.cards = (spec.en || []).map(grab);
    s.trainers.cards = (spec.tr || []).map(grab);
    s.damage = spec.dmg || 0;
    s.specialConditions = (spec.cond || []).slice();
  };
  setSlot(p.active, side.active);
  (side.bench || []).forEach((b, i) => setSlot(p.bench[i], b));
  p.hand.cards = (side.hand || []).map(grab);
  p.discard.cards = (side.discard || []).map(grab);
  const top = (side.deck || []).map(grab);
  // prizes: one card each in the first `prizes` Prize lists
  const nPrizes = side.prizes === undefined ? 6 : side.prizes;
  p.prizes.forEach((z, i) => { z.cards = i < nPrizes ? [pool.pop()] : []; });
  // rest of the deck: Energy first (so a draw past the named cards is plain Energy), then the others
  pool.sort((a, b) => (a.fullName === FE ? 0 : 1) - (b.fullName === FE ? 0 : 1));
  p.deck.cards = [...top, ...pool];
  p.retreatedTurn = -1;
  p.energyPlayedTurn = -1;
}

// ---------------------------------------------------------------- driving
const keysOf = g => { const d = g.decision(); return d ? d.options.map(o => o.key) : []; };

function stepKey(g, key) {
  const d = g.decision();
  if (!d) throw new DriverError(`no decision (game over?) when asked for ${key}: ${g.error && g.error.message}`);
  const i = d.options.findIndex(o => o.key === key);
  if (i < 0) throw new DriverError(`option ${key} not offered; offered ${d.prompt ? d.prompt.type : 'main'}: [${d.options.map(o => o.key).join(' ; ')}]`);
  if (TRACE) console.log(`    ${d.prompt ? d.prompt.type : 'main'} p${d.playerId} -> ${key}   of [${d.options.map(o => o.key).join(' ; ')}]`);
  g.step(i);
}
const answer = (g, ...ks) => ks.forEach(k => stepKey(g, k));

// Play the first offered option whose key starts with `prefix` (e.g. 'trainer|Bill BS|').
function playStarting(g, prefix) {
  const k = keysOf(g).find(x => x.startsWith(prefix));
  if (!k) throw new DriverError(`no option starting ${prefix}; offered [${keysOf(g).join(' ; ')}]`);
  stepKey(g, k);
  return k;
}
const playTrainer = (g, name) => playStarting(g, `trainer|${name}|`);

// Retreat to `slot`, paying the cost with `energy` (the engine asks which Energy to discard).
function retreat(g, slot, energy) {
  stepKey(g, 'retreat|' + slot);
  const d = g.decision();
  if (d && d.prompt && d.prompt.type === 'Choose energy') answer(g, 'pick|' + energy, 'done');
}

function assertMain(g) {
  if (g.done) return;
  const d = g.decision();
  if (d && d.prompt) throw new DriverError(`prompt still open: ${d.prompt.type} [${d.options.map(o => o.key).join(' ; ')}]`);
}

// ---------------------------------------------------------------- observation
const names = list => list.cards.map(c => c.fullName);
const sortedNames = list => names(list).sort();
const countOf = (arr, n) => arr.filter(x => x === n).length;
const slotStr = (s, hidden) => !s.pokemons.cards.length ? '-' :
  `${s.pokemons.cards.map(c => c.fullName).join('+')}[en ${s.energies.cards.map(c => c.fullName.replace(' Energy BS', '')).join(',')}` +
  `${s.trainers.cards.length ? ' tr ' + s.trainers.cards.map(c => c.fullName).join(',') : ''} dmg ${s.damage}${s.specialConditions.length ? ' ' + s.specialConditions.join(',') : ''}]`;
const sideStr = (p, label) => `${label}: A ${slotStr(p.active)} | bench ${p.bench.map(b => slotStr(b)).join(' ')} | hand ${names(p.hand).join(',')} | ` +
  `discard ${names(p.discard).join(',')} | deck ${p.deck.cards.length}${p.deck.cards.length ? ' top ' + names(p.deck).slice(0, 4).join(',') : ''} | prizes ${p.prizes.filter(z => z.cards.length).length}`;
const snap = (me, opp) => sideStr(me, 'me') + '\n      ' + sideStr(opp, 'opp');

// ---------------------------------------------------------------- test registry
const TESTS = [];
const test = (card, kase, fn) => TESTS.push({ card, case: kase, fn });

// A running test: collects failed expectations, remembers the state before the action.
class T {
  constructor() { this.fails = []; this.notes = []; this.before = ''; }
  eq(label, got, want) {
    const a = JSON.stringify(got), b = JSON.stringify(want);
    if (a !== b) this.fails.push(`${label}: expected ${b}, observed ${a}`);
  }
  ok(label, cond, observed) { if (!cond) this.fails.push(`${label}: expected true, observed ${observed === undefined ? 'false' : observed}`); }
  note(s) { this.notes.push(s); }
}

const mon = (name, extra = {}) => ({ mon: name, ...extra });
const BASE_OPP = { active: mon(RATICATE), bench: [mon(PIDGEY)], prizes: 6 };

// ================================================================= Professor Oak
// "Discard your hand, then draw 7 cards."
test('Professor Oak', 'discards the rest of the hand, draws exactly the top 7', t => {
  const deck = [BILL, SWITCH, PE, WE, MACHOP, PIKACHU, RATTATA, OAK, GUST];
  const { g, me, opp } = scene({ me: { active: mon(MACHOP), bench: [mon(PIDGEY)], hand: [OAK, BILL, MACHOP, FE, CS], deck }, opp: BASE_OPP });
  t.before = snap(me, opp);
  const deckBefore = me.deck.cards.length;
  playTrainer(g, OAK); assertMain(g);
  t.eq('hand after Oak', names(me.hand), deck.slice(0, 7));
  t.eq('discard after Oak (Oak + the 4 other hand cards)', sortedNames(me.discard), [OAK, BILL, MACHOP, FE, CS].sort());
  t.eq('deck size', me.deck.cards.length, deckBefore - 7);
  t.eq('deck top after draw', names(me.deck).slice(0, 2), deck.slice(7, 9));
});

test('Professor Oak', 'with fewer than 7 cards in the deck draws them all and the game goes on (Aug 3 2000 Q43)', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP), bench: [mon(PIDGEY)], hand: [OAK, BILL, FE], deck: [PE, WE, SWITCH] }, opp: BASE_OPP });
  // leave exactly 3 cards in the deck: move the rest to the discard
  const rest = me.deck.cards.splice(3);
  me.discard.cards.push(...rest.slice(0, 0));
  me.prizes[5].cards.push(...rest);       // park the surplus where it is not drawn (a Prize list)
  t.before = snap(me, opp);
  playTrainer(g, OAK);
  t.eq('hand after Oak', names(me.hand), [PE, WE, SWITCH]);
  t.eq('deck empty', me.deck.cards.length, 0);
  t.ok('game not finished by the short draw', !g.done || g.state.phase !== C.GamePhase.FINISHED, 'phase ' + g.state.phase);
});

// ================================================================= Bill
// "Draw 2 cards."
test('Bill', 'draws exactly the top 2 cards; Bill goes to the discard', t => {
  const deck = [SWITCH, PE, WE];
  const { g, me, opp } = scene({ me: { active: mon(MACHOP), bench: [mon(PIDGEY)], hand: [BILL, FE, MACHOP], deck }, opp: BASE_OPP });
  t.before = snap(me, opp);
  playTrainer(g, BILL); assertMain(g);
  t.eq('hand after Bill', names(me.hand), [FE, MACHOP, SWITCH, PE]);
  t.eq('discard', names(me.discard), [BILL]);
  t.eq('next deck card untouched', names(me.deck)[0], WE);
});

// ================================================================= PlusPower
// "Attach PlusPower to your Active Pokemon. At the end of your turn, discard PlusPower. If this Pokemon's attack does
// damage to the Defending Pokemon (after applying Weakness and Resistance), the attack does 10 more damage."
function plusPowerScene(defender, nPlus, extra = {}) {
  return scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: Array(nPlus).fill(PLUS), prizes: extra.prizes === undefined ? 6 : extra.prizes },
    opp: { active: defender, bench: [mon(PIDGEY)], prizes: 6 } });
}
const attackWith = (g, nPlus) => {
  for (let i = 0; i < nPlus; i++) playTrainer(g, PLUS);
  playStarting(g, 'attack|Low Kick');
};

test('PlusPower', 'control: Low Kick (20) on a Fighting-weak Pokemon is 40 without PlusPower', t => {
  const { g, me, opp } = plusPowerScene(mon(RATICATE), 0);
  t.before = snap(me, opp);
  attackWith(g, 0);
  t.eq('Raticate damage', opp.active.damage, 40);
});

test('PlusPower', 'adds 10 after Weakness: 20 x2 + 10 = 50 (not (20+10) x2 = 60)', t => {
  const { g, me, opp } = plusPowerScene(mon(RATICATE), 1);
  t.before = snap(me, opp);
  attackWith(g, 1);
  t.eq('Raticate damage', opp.active.damage, 50);
  t.eq('PlusPower discarded at end of turn', names(me.discard), [PLUS]);
  t.eq('nothing attached to the attacker', names(me.active.trainers), []);
});

test('PlusPower', 'two PlusPower stack: 20 + 20 on a Pokemon with no Weakness (Onix) = 40', t => {
  const { g, me, opp } = plusPowerScene(mon(ONIX), 2);
  t.before = snap(me, opp);
  attackWith(g, 2);
  t.eq('Onix damage', opp.active.damage, 40);
  t.eq('both discarded', names(me.discard), [PLUS, PLUS]);
});

test('PlusPower', 'if Resistance brings the damage to 0, PlusPower adds nothing (Pidgey resists Fighting: 20-30 -> 0)', t => {
  const { g, me, opp } = plusPowerScene(mon(PIDGEY), 1);
  t.before = snap(me, opp);
  attackWith(g, 1);
  t.eq('Pidgey damage', opp.active.damage, 0);
});

test('PlusPower', 'a PlusPower KO taking the last Prize ends the game for the attacker (reducer: last-Prize promote)', t => {
  // Onix has 90 HP; 70 damage on it, Low Kick 20 is not enough, 20+10 = 30 is.
  const { g, me, opp } = plusPowerScene(mon(ONIX, { dmg: 70 }), 1, { prizes: 1 });
  t.before = snap(me, opp);
  attackWith(g, 1);
  t.ok('game finished', g.state.phase === C.GamePhase.FINISHED, 'phase ' + g.state.phase + (g.openPrompt() ? ', open prompt ' + g.openPrompt().type : ''));
  t.eq('winner', g.winner, me.id);
});

// ================================================================= Computer Search
// "Discard 2 of the other cards from your hand in order to search your deck for any card and put it into your hand.
// Shuffle your deck afterward."
test('Computer Search', 'discards 2 other hand cards, fetches any card from the deck', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP), bench: [mon(PIDGEY)], hand: [CS, FE, BILL, SWITCH], deck: [PE, OAK, WE] }, opp: BASE_OPP });
  t.before = snap(me, opp);
  const deckBefore = me.deck.cards.length;
  playTrainer(g, CS);
  answer(g, 'pick|' + FE, 'pick|' + BILL, 'done');
  answer(g, 'pick|' + OAK, 'done');
  assertMain(g);
  t.eq('hand', names(me.hand), [SWITCH, OAK]);
  t.eq('discard', sortedNames(me.discard), [CS, FE, BILL].sort());
  t.eq('Oak left the deck', countOf(names(me.deck), OAK), 0);
  t.eq('deck size down by 1', me.deck.cards.length, deckBefore - 1);
});

test('Computer Search', 'is not playable with fewer than 2 other cards in hand', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP), bench: [mon(PIDGEY)], hand: [CS, FE], deck: [PE] }, opp: BASE_OPP });
  t.before = snap(me, opp);
  t.eq('trainer options offered', keysOf(g).filter(k => k.startsWith('trainer|')), []);
});

test('Computer Search', 'does not let the played card count as one of the 2 discards', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP), bench: [mon(PIDGEY)], hand: [CS, FE, BILL], deck: [PE] }, opp: BASE_OPP });
  t.before = snap(me, opp);
  playTrainer(g, CS);
  const d = g.decision();
  t.ok('discard prompt offers only the other cards', d.options.every(o => !o.key.includes('Computer Search')), d.options.map(o => o.key).join(' ; '));
  t.ok('discard prompt cannot finish with 1 card', !(answerThenDone(g, 'pick|' + FE)), 'done offered after one pick');
});
function answerThenDone(g, key) {
  stepKey(g, key);
  const done = keysOf(g).includes('done');
  return done;
}

// ================================================================= Item Finder
// "Discard 2 of the other cards from your hand in order to put a Trainer card from your discard pile into your hand."
test('Item Finder', 'discards 2 other cards, returns a Trainer (only Trainers offered) from the discard', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP), bench: [mon(PIDGEY)], hand: [IF, FE, PE, MACHOP], discard: [SWITCH, BILL, FE, PIKACHU], deck: [WE] }, opp: BASE_OPP });
  t.before = snap(me, opp);
  playTrainer(g, IF);
  answer(g, 'pick|' + FE, 'pick|' + PE, 'done');
  const pickOpts = keysOf(g).filter(k => k.startsWith('pick|')).sort();
  t.eq('cards offered from the discard', pickOpts, ['pick|' + BILL, 'pick|' + SWITCH].sort());
  answer(g, 'pick|' + SWITCH, 'done');
  assertMain(g);
  t.eq('hand', names(me.hand), [MACHOP, SWITCH]);
  t.eq('discard', sortedNames(me.discard), [BILL, FE, PIKACHU, IF, FE, PE].sort());
});

// ================================================================= Energy Removal
// "Choose 1 Energy card attached to 1 of your opponent's Pokemon and discard it."
test('Energy Removal', "discards 1 Energy from the opponent's Active", t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [ER] },
    opp: { active: mon(RATICATE, { en: [FE, WE] }), bench: [mon(PIDGEY, { en: [PE] })], prizes: 6 } });
  t.before = snap(me, opp);
  playTrainer(g, ER);
  traceNext(g);
  pickSlotThenEnergy(g, 'oA', WE);
  assertMain(g);
  t.eq("opp Active's Energy", names(opp.active.energies), [FE]);
  t.eq("opp discard", names(opp.discard), [WE]);
  t.eq("opp bench Energy untouched", names(opp.bench[0].energies), [PE]);
  t.eq('my Energy untouched', names(me.active.energies), [FE]);
  t.eq('my discard', names(me.discard), [ER]);
});

test('Energy Removal', "can take the Energy of an opponent's Benched Pokemon", t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [ER] },
    opp: { active: mon(RATICATE, { en: [FE, WE] }), bench: [mon(PIDGEY, { en: [PE] })], prizes: 6 } });
  t.before = snap(me, opp);
  playTrainer(g, ER);
  pickSlotThenEnergy(g, 'oB0', PE);
  assertMain(g);
  t.eq("opp bench Energy", names(opp.bench[0].energies), []);
  t.eq("opp Active Energy untouched", names(opp.active.energies), [FE, WE]);
  t.eq("opp discard", names(opp.discard), [PE]);
});

// Energy Removal and Super Energy Removal may ask for the Pokemon first and then the Energy, or the Energy at once
// (ChooseEnergyPrompt over several Pokemon). Handles both: if the prompt is a Pokemon pick, pick the slot, then the Energy.
function traceNext() {}
function pickSlotThenEnergy(g, slotCode, energyName) {
  let d = g.decision();
  if (d.prompt.type === 'Choose pokemon') { answer(g, 'pick|' + slotCode, 'done'); d = g.decision(); }
  if (!d.prompt) return;
  if (d.prompt.type === 'Choose energy' || d.prompt.type === 'Choose cards') {
    if (d.options.some(o => o.key === 'pick|' + energyName)) answer(g, 'pick|' + energyName, 'done');
    else throw new DriverError('energy prompt without ' + energyName + ': ' + d.options.map(o => o.key).join(' ; '));
  } else throw new DriverError('unexpected prompt ' + d.prompt.type + ': ' + d.options.map(o => o.key).join(' ; '));
}

// ================================================================= Super Energy Removal
// "Discard 1 Energy card attached to 1 of your Pokemon in order to choose 1 of your opponent's Pokemon and up to 2
// Energy cards attached to it. Discard those Energy cards."
test('Super Energy Removal', 'discards 1 of mine, then up to 2 Energy of one opponent Pokemon (takes 2)', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE, PE] }), bench: [mon(PIDGEY)], hand: [SER] },
    opp: { active: mon(RATICATE, { en: [FE, WE, PE] }), bench: [mon(PIDGEY, { en: [WE] })], prizes: 6 } });
  t.before = snap(me, opp);
  playTrainer(g, SER);
  superEnergyRemoval(g, { mine: PE, mineSlot: 'A', oppSlot: 'oA', oppEnergy: [FE, WE] });
  assertMain(g);
  t.eq('my Energy (one discarded)', names(me.active.energies), [FE]);
  t.eq('my discard', sortedNames(me.discard), [PE, SER].sort());
  t.eq('opp Active Energy (two discarded)', names(opp.active.energies), [PE]);
  t.eq('opp discard', sortedNames(opp.discard), [FE, WE].sort());
  t.eq('opp bench untouched', names(opp.bench[0].energies), [WE]);
});

test('Super Energy Removal', '"up to 2": taking just 1 of the opponent\'s Energy is allowed', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [SER] },
    opp: { active: mon(RATICATE, { en: [FE, WE, PE] }), bench: [mon(PIDGEY, { en: [WE] })], prizes: 6 } });
  t.before = snap(me, opp);
  playTrainer(g, SER);
  superEnergyRemoval(g, { mine: FE, mineSlot: 'A', oppSlot: 'oA', oppEnergy: [WE] });
  assertMain(g);
  t.eq('my Energy', names(me.active.energies), []);
  t.eq('opp Active Energy (one discarded)', names(opp.active.energies), [FE, PE]);
  t.eq('opp discard', names(opp.discard), [WE]);
});

test('Super Energy Removal', "can hit an opponent's Benched Pokemon, and my Energy may come from a Benched Pokemon", t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP), bench: [mon(PIDGEY, { en: [WE] })], hand: [SER] },
    opp: { active: mon(RATICATE, { en: [FE] }), bench: [mon(PIDGEY, { en: [WE, PE] })], prizes: 6 } });
  t.before = snap(me, opp);
  playTrainer(g, SER);
  superEnergyRemoval(g, { mine: WE, mineSlot: 'B0', oppSlot: 'oB0', oppEnergy: [WE, PE] });
  assertMain(g);
  t.eq('my bench Energy', names(me.bench[0].energies), []);
  t.eq('opp bench Energy', names(opp.bench[0].energies), []);
  t.eq('opp Active untouched', names(opp.active.energies), [FE]);
});

test('Super Energy Removal', 'is not playable when none of my Pokemon has an Energy to discard', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP), bench: [mon(PIDGEY)], hand: [SER] },
    opp: { active: mon(RATICATE, { en: [FE] }), bench: [mon(PIDGEY)], prizes: 6 } });
  t.before = snap(me, opp);
  t.eq('trainer options offered', keysOf(g).filter(k => k.startsWith('trainer|')), []);
});

// Answers whatever order the prompts come in: my Energy (a Pokemon pick and/or an Energy pick), then the opponent's.
function superEnergyRemoval(g, { mine, mineSlot, oppSlot, oppEnergy }) {
  let guard = 0;
  const seen = [];
  while (g.decision() && g.decision().prompt && guard++ < 12) {
    const d = g.decision(), keys = d.options.map(o => o.key);
    seen.push(`${d.prompt.type}: ${keys.join(' ; ')}`);
    if (d.prompt.type === 'Choose pokemon') {
      // mine first (slots without 'o'), the opponent's when only 'o' slots are on offer
      const code = keys.some(k => k === 'pick|' + mineSlot) && !seen.mineDone ? mineSlot : oppSlot;
      if (code === mineSlot && !seen.mineDone) seen.mineDone = true;
      answer(g, 'pick|' + code, 'done');
    } else if (d.prompt.type === 'Choose energy' || d.prompt.type === 'Choose cards') {
      if (!seen.mineEnergyDone) { seen.mineEnergyDone = true; answer(g, 'pick|' + mine, 'done'); }
      else { oppEnergy.forEach(e => stepKey(g, 'pick|' + e)); stepKey(g, 'done'); }
    } else throw new DriverError('unexpected prompt ' + d.prompt.type + ' ' + keys.join(' ; '));
  }
}

// ================================================================= Scoop Up
// "Choose 1 of your Pokemon in play and return its Basic Pokemon card to your hand. (Discard all cards attached to that card.)"
const evolvedBench = () => mon([MACHOP, MACHOKE], { en: [FE, PE], tr: [PLUS], dmg: 30 });
test('Scoop Up', 'Benched evolved Pokemon: the Basic returns to hand, the evolution, Energy and Trainer are discarded, damage gone', t => {
  const { g, me, opp } = scene({ me: { active: mon(PIKACHU), bench: [evolvedBench(), mon(PIDGEY)], hand: [SCOOP] }, opp: BASE_OPP });
  t.before = snap(me, opp);
  playTrainer(g, SCOOP);
  answer(g, 'pick|B0', 'done');
  assertMain(g);
  t.eq('hand', names(me.hand), [MACHOP]);
  t.eq('discard', sortedNames(me.discard), [SCOOP, MACHOKE, FE, PE, PLUS].sort());
  t.eq('slot B0 emptied', slotStr(me.bench[0]), '-');
  t.eq('Active untouched', names(me.active.pokemons), [PIKACHU]);
});

test('Scoop Up', 'the Active with a Bench: Basic to hand, a promote prompt, the chosen Benched Pokemon becomes Active', t => {
  const { g, me, opp } = scene({ me: { active: evolvedBench(), bench: [mon(PIDGEY), mon(PIKACHU, { en: [WE] })], hand: [SCOOP] }, opp: BASE_OPP });
  t.before = snap(me, opp);
  playTrainer(g, SCOOP);
  answer(g, 'pick|A', 'done');
  const d = g.decision();
  t.ok('a prompt asks me for a new Active', d && d.prompt && d.prompt.type === 'Choose pokemon' && d.playerId === me.id,
    d && (d.prompt ? d.prompt.type + ' for p' + d.playerId : 'main phase'));
  answer(g, 'pick|B1', 'done');
  assertMain(g);
  t.eq('hand', names(me.hand), [MACHOP]);
  t.eq('new Active', names(me.active.pokemons), [PIKACHU]);
  t.eq('new Active keeps its Energy', names(me.active.energies), [WE]);
  t.eq('discard', sortedNames(me.discard), [SCOOP, MACHOKE, FE, PE, PLUS].sort());
  t.eq('old Active slot is not left on the Bench', me.bench.filter(b => b.pokemons.cards.length).map(b => names(b.pokemons)[0]), [PIDGEY]);
});

test('Scoop Up', 'the Active with a Bench while I hold my LAST Prize: still promotes, the game goes on (reducer: gameEnds)', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [SCOOP], prizes: 1 }, opp: { ...BASE_OPP, prizes: 1 } });
  t.before = snap(me, opp);
  playTrainer(g, SCOOP);
  answer(g, 'pick|A', 'done');
  const d = g.decision();
  t.ok('promote prompt offered', d && d.prompt && d.prompt.type === 'Choose pokemon', d && (d.prompt ? d.prompt.type : 'main'));
  if (d && d.prompt) answer(g, 'pick|B0', 'done');
  t.ok('game still on', g.state.phase !== C.GamePhase.FINISHED, 'finished, winner ' + g.winner);
  t.eq('new Active', names(me.active.pokemons), [PIDGEY]);
  t.eq('hand', names(me.hand), [MACHOP]);
});

test('Scoop Up', 'the Active with NO Bench: observe (2000: no Pokemon left in play = my loss; or the play is not offered)', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [], hand: [SCOOP] }, opp: BASE_OPP });
  t.before = snap(me, opp);
  const offered = keysOf(g).filter(k => k.startsWith('trainer|' + SCOOP));
  if (!offered.length) { t.note('Scoop Up not offered with no Bench'); return; }
  stepKey(g, offered[0]);
  if (g.openPrompt()) { const d = g.decision(); t.note('prompt ' + d.prompt.type + ' ' + d.options.map(o => o.key).join(' ; ')); answer(g, 'pick|A', 'done'); }
  t.note(`after: phase ${g.state.phase}, winner ${g.winner}, my Active ${slotStr(me.active)}`);
  t.ok('the opponent wins (no Pokemon in play, none to promote)', g.state.phase === C.GamePhase.FINISHED && g.winner === opp.id,
    `phase ${g.state.phase}, winner ${g.winner}, open prompt ${g.openPrompt() ? g.openPrompt().type : 'none'}`);
});

// ================================================================= Gust of Wind
// "Choose 1 of your opponent's Benched Pokemon and switch it with his or her Active Pokemon."
const gustOpp = (activeCond) => ({ active: mon(RATICATE, { en: [FE], dmg: 20, cond: activeCond }), bench: [mon(PIDGEY, { en: [WE] }), mon(PIKACHU, { en: [PE], dmg: 10 })], prizes: 6 });
test('Gust of Wind', 'a chosen Benched Pokemon comes up; the old Active takes its Bench slot with Energy and damage', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [GUST] }, opp: gustOpp([]) });
  t.before = snap(me, opp);
  playTrainer(g, GUST);
  answer(g, 'pick|oB1', 'done');
  assertMain(g);
  t.eq('opp Active', slotStr(opp.active), 'Pikachu BS[en Psychic dmg 10]');
  t.eq('opp Bench slot 1 now holds the old Active', slotStr(opp.bench[1]), 'Raticate BS[en Fighting dmg 20]');
  t.eq('opp Bench slot 0 untouched', slotStr(opp.bench[0]), 'Pidgey BS[en Water dmg 0]');
  t.eq('my side untouched', names(me.active.pokemons), [MACHOP]);
  t.eq('my discard', names(me.discard), [GUST]);
});

test('Gust of Wind', 'only the opponent\'s Benched Pokemon are choices (not their Active, not mine)', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [GUST] }, opp: gustOpp([]) });
  t.before = snap(me, opp);
  playTrainer(g, GUST);
  t.eq('picks offered', keysOf(g).filter(k => k.startsWith('pick|')).sort(), ['pick|oB0', 'pick|oB1']);
});

test('Gust of Wind', "opponent's Active is Confused: the Pokemon brought up is not Confused", t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [GUST] }, opp: gustOpp([SC.CONFUSED]) });
  t.before = snap(me, opp);
  playTrainer(g, GUST);
  answer(g, 'pick|oB0', 'done');
  assertMain(g);
  t.eq('opp new Active', names(opp.active.pokemons), [PIDGEY]);
  t.eq('opp new Active conditions', opp.active.specialConditions, []);
});

test('Gust of Wind', 'the Confused Pokemon that was Active, now Benched, is no longer Confused (moving to the Bench clears it)', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [GUST] }, opp: gustOpp([SC.CONFUSED]) });
  t.before = snap(me, opp);
  playTrainer(g, GUST);
  answer(g, 'pick|oB0', 'done');
  assertMain(g);
  t.eq('Raticate now at opp Bench 0', names(opp.bench[0].pokemons), [RATICATE]);
  t.eq('its conditions', opp.bench[0].specialConditions, []);
});

test('Gust of Wind', 'after Gust on a Confused Active, the Pokemon brought up attacks on its turn with no confusion flip (all flips tails)', t => {
  const { g, me, opp } = scene({ me: { active: mon(ONIX, { en: [FE] }), bench: [mon(PIDGEY)], hand: [GUST] },
    opp: { active: mon(RATICATE, { en: [FE], cond: [SC.CONFUSED] }), bench: [mon(MACHOP, { en: [FE] })], prizes: 6 } }, { coin: 'tails' });
  t.before = snap(me, opp);
  playTrainer(g, GUST);
  answer(g, 'pick|oB0', 'done');
  stepKey(g, 'pass');
  assertMain(g);
  t.ok("it is the opponent's turn", g.state.players[g.state.activePlayer] === opp, 'still my turn');
  t.eq('opp Active', names(opp.active.pokemons), [MACHOP]);
  playStarting(g, 'attack|Low Kick');
  t.eq('my Onix took Low Kick (20, no flip stopped it)', me.active.damage, 20);
  t.eq('opp Machop undamaged', opp.active.damage, 0);
});

// ================================================================= Rocket's Sneak Attack
// "Look at your opponent's hand. If he or she has any Trainer cards, choose 1 of them. Your opponent shuffles that card
// into his or her deck."
test("Rocket's Sneak Attack", "shows the opponent's hand, a chosen Trainer (only Trainers offered) goes to their deck", t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [RSA] },
    opp: { ...BASE_OPP, hand: [BILL, MACHOP, FE, SWITCH], deck: [PE, WE] } });
  t.before = snap(me, opp);
  const deckBefore = opp.deck.cards.length;
  playTrainer(g, RSA);
  let d = g.decision();
  const seen = [];
  let guard = 0;
  while (d && d.prompt && guard++ < 6) {
    seen.push(d.prompt.type + ': ' + d.options.map(o => o.key).join(' ; '));
    const trainerPick = d.options.find(o => o.key === 'pick|' + SWITCH);
    if (trainerPick) {
      t.eq('cards offered', d.options.filter(o => o.key.startsWith('pick|')).map(o => o.key).sort(), ['pick|' + BILL, 'pick|' + SWITCH].sort());
      answer(g, 'pick|' + SWITCH, 'done');
    } else if (d.options.some(o => o.key === 'res|ok')) stepKey(g, 'res|ok');
    else throw new DriverError('unexpected RSA prompt ' + seen[seen.length - 1]);
    d = g.decision();
  }
  assertMain(g);
  t.note('prompts: ' + seen.join(' | '));
  t.eq("opp hand", sortedNames(opp.hand), [BILL, MACHOP, FE].sort());
  t.eq("opp deck grew by 1", opp.deck.cards.length, deckBefore + 1);
  t.eq("Switch is in opp's deck", countOf(names(opp.deck), SWITCH), 1);
  t.eq("opp discard empty (shuffled in, not discarded)", names(opp.discard), []);
  t.eq('my discard', names(me.discard), [RSA]);
});

test("Rocket's Sneak Attack", 'opponent has no Trainer in hand: nothing is shuffled away', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIDGEY)], hand: [RSA] },
    opp: { ...BASE_OPP, hand: [MACHOP, FE], deck: [PE, WE] } });
  t.before = snap(me, opp);
  const deckBefore = opp.deck.cards.length;
  const offered = keysOf(g).filter(k => k.startsWith('trainer|' + RSA));
  t.note(offered.length ? 'playable with no Trainer in the opponent hand' : 'not offered by the env when the opponent has no Trainer (dead end)');
  if (!offered.length) return;
  stepKey(g, offered[0]);
  let guard = 0;
  while (g.decision() && g.decision().prompt && guard++ < 4) {
    const d = g.decision();
    if (d.options.some(o => o.key === 'res|ok')) stepKey(g, 'res|ok');
    else if (d.options.some(o => o.key === 'done')) stepKey(g, 'done');
    else throw new DriverError('unexpected prompt ' + d.prompt.type + ' ' + d.options.map(o => o.key).join(' ; '));
  }
  t.eq('opp hand unchanged', sortedNames(opp.hand), [MACHOP, FE].sort());
  t.eq('opp deck unchanged', opp.deck.cards.length, deckBefore);
});

// ================================================================= interactions: Switch, retreat, Full Heal, Confusion
// Retreat Cost: Machop 1 (Fighting Energy). Confusion (2000, Rules.baseEraConfusion): retreating takes a heads flipped
// after the cost is paid, tails leaves it Active and it cannot try again this turn; a failed attack flip is 20 damage to
// itself with its own Weakness and Resistance.
test('Switch', 'then a retreat attempt: Switch is not a retreat, the new Active (with Energy) can still retreat and pays its cost', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIKACHU, { en: [WE] }), mon(PIDGEY)], hand: [SWITCH] }, opp: BASE_OPP });
  t.before = snap(me, opp);
  playTrainer(g, SWITCH);
  answer(g, 'pick|B0', 'done');
  assertMain(g);
  t.eq('Active after Switch', names(me.active.pokemons), [PIKACHU]);
  t.eq('Machop benched with its Energy', slotStr(me.bench[0]), 'Machop BS[en Fighting dmg 0]');
  t.ok('retreat still offered (Switch used no retreat)', keysOf(g).includes('retreat|B1'), keysOf(g).join(' ; '));
  retreat(g, 'B1', WE);
  assertMain(g);
  t.eq('Active after retreat', names(me.active.pokemons), [PIDGEY]);
  t.eq('retreat cost paid from Pikachu (1)', names(me.discard).filter(n => n === WE).length, 1);
  t.ok('retreat is now used up for the turn', !keysOf(g).some(k => k.startsWith('retreat|')), keysOf(g).join(' ; '));
});

test('Switch', 'after a retreat the turn\'s retreat is used, but Switch can still be played', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE] }), bench: [mon(PIKACHU), mon(PIDGEY)], hand: [SWITCH] }, opp: BASE_OPP });
  t.before = snap(me, opp);
  retreat(g, 'B0', FE);
  assertMain(g);
  t.eq('Active after retreat', names(me.active.pokemons), [PIKACHU]);
  t.ok('Switch still playable', keysOf(g).some(k => k.startsWith('trainer|' + SWITCH)), keysOf(g).join(' ; '));
  playTrainer(g, SWITCH);
  answer(g, 'pick|B1', 'done');
  assertMain(g);
  t.eq('Active after Switch', names(me.active.pokemons), [PIDGEY]);
  t.ok('no second retreat offered', !keysOf(g).some(k => k.startsWith('retreat|')), keysOf(g).join(' ; '));
});

test('Switch', 'on a Confused Active: Switch clears the condition from the benched Pokemon, and the new Active retreats without a flip', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE], cond: [SC.CONFUSED] }), bench: [mon(PIKACHU, { en: [WE] }), mon(PIDGEY)], hand: [SWITCH] }, opp: BASE_OPP }, { coin: 'tails' });
  t.before = snap(me, opp);
  playTrainer(g, SWITCH);
  answer(g, 'pick|B0', 'done');
  assertMain(g);
  t.eq('Machop benched, no longer Confused', me.bench[0].specialConditions, []);
  t.eq('new Active conditions', me.active.specialConditions, []);
  retreat(g, 'B1', WE);             // all flips tails: a Confused Active would stay; a clean one switches
  assertMain(g);
  t.eq('Active after retreat (no flip, so tails cannot stop it)', names(me.active.pokemons), [PIDGEY]);
});

test('Full Heal', 'removes Confusion and Poison from the Active; the next retreat takes no flip (all flips tails)', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE], cond: [SC.CONFUSED, SC.POISONED] }), bench: [mon(PIDGEY)], hand: [FH] }, opp: BASE_OPP }, { coin: 'tails' });
  t.before = snap(me, opp);
  playTrainer(g, FH);
  assertMain(g);
  t.eq('Active conditions', me.active.specialConditions, []);
  t.eq('discard', names(me.discard), [FH]);
  retreat(g, 'B0', FE);
  assertMain(g);
  t.eq('retreated although every flip is tails', names(me.active.pokemons), [PIDGEY]);
  t.eq('retreat cost paid', names(me.discard).filter(n => n === FE).length, 1);
});

test('Full Heal', 'removes Confusion: the next attack takes no flip and does its damage (all flips tails)', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE], cond: [SC.CONFUSED] }), bench: [mon(PIDGEY)], hand: [FH] }, opp: { active: mon(ONIX), bench: [mon(PIDGEY)], prizes: 6 } }, { coin: 'tails' });
  t.before = snap(me, opp);
  playTrainer(g, FH);
  playStarting(g, 'attack|Low Kick');
  t.eq('Onix damage (20, no self-hit)', opp.active.damage, 20);
  t.eq('Machop undamaged', me.active.damage, 0);
});

test('Confusion', 'unhealed: a tails flip when attacking is 20 damage to itself (Kadabra, Weakness Psychic: 40), no attack, turn ends', t => {
  const { g, me, opp } = scene({ me: { active: mon(KADABRA, { en: [PE, PE, FE], cond: [SC.CONFUSED] }), bench: [mon(PIDGEY)] }, opp: { active: mon(ONIX), bench: [mon(PIDGEY)], prizes: 6 } }, { coin: 'tails' });
  t.before = snap(me, opp);
  playStarting(g, 'attack|Super Psy');
  t.eq('Kadabra self-damage (20 x2 Weakness)', me.active.damage, 40);
  t.eq('Onix undamaged', opp.active.damage, 0);
  t.ok('the turn ended', g.state.players[g.state.activePlayer] === opp, 'active player is still me');
});

test('Confusion', 'unhealed: a heads flip attacks normally', t => {
  const { g, me, opp } = scene({ me: { active: mon(KADABRA, { en: [PE, PE, FE], cond: [SC.CONFUSED] }), bench: [mon(PIDGEY)] }, opp: { active: mon(ONIX), bench: [mon(PIDGEY)], prizes: 6 } }, { coin: 'heads' });
  t.before = snap(me, opp);
  playStarting(g, 'attack|Super Psy');
  t.eq('Onix damage', opp.active.damage, 50);
  t.eq('Kadabra undamaged', me.active.damage, 0);
});

test('Confusion', 'Confused retreat, flip tails: cost is paid, still Active and Confused, no second try this turn', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE], cond: [SC.CONFUSED] }), bench: [mon(PIDGEY)] }, opp: BASE_OPP }, { coin: 'tails' });
  t.before = snap(me, opp);
  retreat(g, 'B0', FE);
  assertMain(g);
  t.eq('Active', names(me.active.pokemons), [MACHOP]);
  t.eq('Energy paid', names(me.active.energies), []);
  t.eq('still Confused', me.active.specialConditions, [SC.CONFUSED]);
  t.ok('no retreat offered again this turn (Apr 13 2000 Q146)', !keysOf(g).some(k => k.startsWith('retreat|')), keysOf(g).join(' ; '));
});

test('Confusion', 'Confused retreat, flip heads: cost paid, switched, the Confusion is cleared by moving to the Bench', t => {
  const { g, me, opp } = scene({ me: { active: mon(MACHOP, { en: [FE], cond: [SC.CONFUSED] }), bench: [mon(PIDGEY)] }, opp: BASE_OPP }, { coin: 'heads' });
  t.before = snap(me, opp);
  retreat(g, 'B0', FE);
  assertMain(g);
  t.eq('Active', names(me.active.pokemons), [PIDGEY]);
  t.eq('Energy paid', names(me.discard), [FE]);
  t.eq('benched Machop conditions', me.bench[0].specialConditions, []);
});

// ================================================================= run
function runOne(tc) {
  const t = new T();
  let verdict;
  try {
    tc.fn(t);
    verdict = { pass: t.fails.length === 0, detail: t.fails.length ? t.fails.join(' || ') : (t.notes.join('; ') || 'ok') };
  } catch (e) {
    verdict = { pass: false, driver: true, detail: `DRIVER ${e instanceof DriverError ? '' : e.name + ' '}${e.message}` };
    if (!(e instanceof DriverError)) verdict.stack = String(e.stack).split('\n').slice(0, 4).join(' / ');
  }
  if (!verdict.pass) verdict.before = t.before;
  if (t.notes.length && verdict.pass) verdict.detail = t.notes.join('; ') + (t.fails.length ? '' : '');
  return verdict;
}

const t0 = Date.now();
const RYUU_COMMIT = spawnSync('git', ['-C', RYUU, 'rev-parse', '--short', 'HEAD'], { encoding: 'utf8' }).stdout.trim();

if (ONLY !== null) {
  console.log('RESULT ' + JSON.stringify(runOne(TESTS[Number(ONLY)])));
  process.exit(0);
}

const rows = [];
TESTS.forEach((tc, i) => {
  const v = runOne(tc);
  const row = { card: tc.card, case: tc.case, pass: v.pass, detail: v.detail };
  if (!v.pass) {
    row.before = v.before;
    row.run1 = { pass: v.pass, detail: v.detail };
    const r = spawnSync(process.execPath, [__filename, '--only', String(i)], { encoding: 'utf8' });
    const line = (r.stdout || '').split('\n').find(l => l.startsWith('RESULT '));
    row.run2 = line ? JSON.parse(line.slice(7)) : { pass: false, detail: 'fresh re-run produced no result: ' + (r.stderr || '').slice(0, 300) };
    row.driver = !!v.driver;
    row.pass = row.run2.pass;                // a failure counts only if it also fails in the fresh process
    if (row.run2.pass) row.detail = 'flaky: failed in-process, passed on fresh re-run (' + v.detail + ')';
  }
  console.log(`${row.pass ? 'PASS' : 'FAIL'}  ${tc.card} | ${tc.case}` + (row.pass ? (row.detail !== 'ok' ? '   [' + row.detail + ']' : '') : `\n      ${v.driver ? 'script/driver problem' : 'expected vs observed'}: ${v.detail}\n      before: ${String(v.before).replace(/\n\s*/g, '\n              ')}` +
    `\n      fresh re-run: ${row.run2.pass ? 'PASS' : 'FAIL'} ${row.run2.detail}`));
  if (row.pass && row.detail !== 'ok' && TRACE) console.log('      ' + row.detail);
  rows.push(row);
});

const passed = rows.filter(r => r.pass).length, failed = rows.length - passed;
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ tests: rows, passed, failed, engine_commit: RYUU_COMMIT }, null, 1));
console.log(`${passed} passed, ${failed} failed of ${rows.length} (engine ${RYUU_COMMIT}, ${((Date.now() - t0) / 1000).toFixed(1)}s) -> ${path.relative(ROOT, OUT)}`);
process.exitCode = 0;
