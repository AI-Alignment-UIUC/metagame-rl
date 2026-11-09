// C198 Part A (runs/probe/C198-typed-cost-check/record.md): are attack Energy costs and retreat costs enforced by type, in
// the engine env/engine.js loads and in the options env/legal.js offers? Scripted states in the style of
// test_c195_trainers.js (a seeded Game driven to its first main phase, then both players' zones rearranged).
//
// For each attack case the script records two things and expects both to equal the rule:
//   engine: engine.accepts(state, AttackAction) on a clone, bypassing the env's option list;
//   env:    whether `attack|<name>` is among the main-phase options.
// Costs are the exact ones in notes/data/cards/pool.json (cost vector: index 0 Colourless, 1 Grass, 2 Fighting,
// 3 Psychic, 4 Water, 5 Lightning, 8 Fire). Evaluation only: nothing in env/, ryuu-play/ or rl/ is touched. CPU only.
//
// A failing test is re-run in a fresh node process (--only <i>) and both runs are recorded. A test whose setup or
// driving throws is marked DRIVER (a script bug, not an engine fault).
//
// Run: node env/tools/test_c198_costs.js [--trace] [--out runs/probe/C198-typed-cost-check/partA.json]
//      node env/tools/test_c198_costs.js --only <i>
'use strict';
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { Game } = require('../game.js');
const { C, RYUU, accepts } = require('../engine.js');

const ROOT = path.join(__dirname, '..', '..');
const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const TRACE = argv.includes('--trace');
const ONLY = flag('only', null);
const OUT = path.resolve(ROOT, flag('out', 'runs/probe/C198-typed-cost-check/partA.json'));

// ---------------------------------------------------------------- cards (names checked against pool.json at start)
const POOL_RAW = require('../../notes/data/cards/pool.json');
const POOL = Array.isArray(POOL_RAW) ? POOL_RAW : (POOL_RAW.cards || Object.values(POOL_RAW));
const poolCard = n => { const c = POOL.find(x => x.fullName === n); if (!c) throw new Error('not in pool: ' + n); return c; };
const FIRE = 'Fire Energy BS', WATER = 'Water Energy BS', LIGHT = 'Lightning Energy BS', FE = 'Fighting Energy BS';
const DCE = 'Double Colorless Energy BS', RB = 'Rainbow Energy TR', POTION = 'Potion Energy TR', FHE = 'Full Heal Energy TR';
const PIDGEY = 'Pidgey BS', RATICATE = 'Raticate BS', MACHOP = 'Machop BS';
const MAGMAR = 'Magmar BS', POLIWRATH = ['Poliwag BS', 'Poliwhirl BS', 'Poliwrath BS'], WARTORTLE = ['Squirtle BS', 'Wartortle BS'],
  CHARMELEON = ['Charmander BS', 'Charmeleon BS'];

const COSTSYM = ['C', 'G', 'F', 'P', 'W', 'L', '6', '7', 'F', '9', '10'];   // index -> symbol, for messages only
const costStr = v => v.map((n, i) => COSTSYM[i].repeat(n)).join('');
const shortE = n => n.replace(' Energy BS', '').replace(' Energy TR', '').replace('Double Colorless', 'DCE');
const atkCost = (card, name) => { const a = poolCard(card).attacks.find(x => x.name === name); if (!a) throw new Error('no attack ' + name + ' on ' + card); return a.cost; };

// ---------------------------------------------------------------- scene building (copied from test_c195_trainers.js)
class DriverError extends Error {}
function fixedRng(heads) {
  return { int: () => (heads ? 0 : 1), float: () => 0, u32: () => 0, permutation: n => Array.from({ length: n }, (_, i) => i), clone() { return this; } };
}
const slotNames = s => (s ? [].concat(s.mon, s.en || []) : []);
const sideNames = side => [...slotNames(side.active), ...(side.bench || []).flatMap(slotNames), ...(side.hand || [])];   // hand: A5

function scene(spec) {
  const count = (side, n) => sideNames(side).filter(x => x === n).length;
  const allNames = [...new Set([...sideNames(spec.me), ...sideNames(spec.opp), MACHOP])];
  const deckList = allNames.flatMap(n => Array(Math.max(count(spec.me, n), count(spec.opp, n), n === MACHOP ? 4 : 0)).fill(n));
  while (deckList.length < 60) deckList.push(FE);
  const g = new Game(deckList, deckList, 5);
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
  if (st.turn < 6) st.turn = 6;          // not the first turn: attacks are not restricted
  g.cached = null;
  g.rng = fixedRng(true);
  return { g, me, opp };
}
const slotsOf = p => [p.active, ...p.bench];
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
  };
  setSlot(p.active, side.active);
  (side.bench || []).forEach((b, i) => setSlot(p.bench[i], b));
  p.hand.cards = (side.hand || []).map(grab);                // A5 (C201): cards in hand
  p.prizes.forEach((z, i) => { z.cards = i < 6 ? [pool.pop()] : []; });
  pool.sort((a, b) => (a.fullName === FE ? 0 : 1) - (b.fullName === FE ? 0 : 1));
  p.deck.cards = pool;
  p.retreatedTurn = -1;
  p.energyPlayedTurn = -1;
}
const keysOf = g => { const d = g.decision(); return d ? d.options.map(o => o.key) : []; };
function stepKey(g, key) {
  const d = g.decision();
  if (!d) throw new DriverError(`no decision when asked for ${key}`);
  const i = d.options.findIndex(o => o.key === key);
  if (i < 0) throw new DriverError(`option ${key} not offered; offered ${d.prompt ? d.prompt.type : 'main'}: [${d.options.map(o => o.key).join(' ; ')}]`);
  if (TRACE) console.log(`    ${d.prompt ? d.prompt.type : 'main'} -> ${key}`);
  g.step(i);
}
const names = list => list.cards.map(c => c.fullName);

// ---------------------------------------------------------------- test registry
const TESTS = [];
const test = (cas, what, fn) => TESTS.push({ case: cas, what, fn });
class T {
  constructor() { this.fails = []; this.notes = []; }
  eq(label, got, want) { const a = JSON.stringify(got), b = JSON.stringify(want); if (a !== b) this.fails.push(`${label}: expected ${b}, observed ${a}`); }
}
const BASE_OPP = { active: { mon: RATICATE }, bench: [{ mon: PIDGEY }] };

// Attack cases: the Active `mon` with Energy `en` attached; `attack` should be legal (want = true) or not.
function attackCase(cas, mon, top, attack, en, want, why) {
  const cost = atkCost(top, attack);
  test(cas, `${top} ${attack} [${costStr(cost)}] with ${en.map(shortE).join('+')}: ${want ? 'legal and offered' : 'illegal and absent'}${why ? ' (' + why + ')' : ''}`, t => {
    const { g, me } = scene({ me: { active: { mon, en }, bench: [{ mon: PIDGEY }] }, opp: BASE_OPP });
    const eng = accepts(g.state, new C.AttackAction(me.id, attack), g.store);
    const env = keysOf(g).includes('attack|' + attack);
    t.eq('engine accepts the attack', eng, want);
    t.eq('env offers attack|' + attack, env, want);
  });
}

// ---- A1: off-type basics cover the count but not the type
attackCase('A1', MAGMAR, MAGMAR, 'Flamethrower', [WATER, WATER, WATER], false);
attackCase('A1', MAGMAR, MAGMAR, 'Flamethrower', [FIRE, WATER, WATER], false, 'one Fire only, needs 2');
attackCase('A1', MAGMAR, MAGMAR, 'Fire Punch', [WATER, WATER], false);
attackCase('A1', WARTORTLE, 'Wartortle BS', 'Bite', [LIGHT, LIGHT, LIGHT], false);
attackCase('A1', POLIWRATH, 'Poliwrath BS', 'Water Gun', [FIRE, FIRE, FIRE], false);
attackCase('A1', POLIWRATH, 'Poliwrath BS', 'Whirlpool', [FIRE, FIRE, FIRE, FIRE], false);
// ---- A2: on-type Energy
attackCase('A2', MAGMAR, MAGMAR, 'Flamethrower', [FIRE, FIRE, WATER], true, '2 Fire + any');
attackCase('A2', MAGMAR, MAGMAR, 'Flamethrower', [FIRE, FIRE, FIRE], true);
attackCase('A2', MAGMAR, MAGMAR, 'Flamethrower', [FIRE, FIRE], false, 'too few Energy');
attackCase('A2', MAGMAR, MAGMAR, 'Fire Punch', [FIRE, FIRE], true);
attackCase('A2', WARTORTLE, 'Wartortle BS', 'Bite', [WATER, LIGHT, LIGHT], true, '1 Water + 2 any');
attackCase('A2', POLIWRATH, 'Poliwrath BS', 'Water Gun', [WATER, WATER, FIRE], true);
attackCase('A2', POLIWRATH, 'Poliwrath BS', 'Whirlpool', [WATER, WATER, FIRE, FIRE], true);
attackCase('A2', CHARMELEON, 'Charmeleon BS', 'Slash', [WATER, LIGHT, FE], true, 'all-Colourless cost: any type pays');
// ---- A3: Double Colorless Energy
attackCase('A3', MAGMAR, MAGMAR, 'Fire Punch', [DCE], false, 'DCE cannot pay [Fire][Fire]');
attackCase('A3', MAGMAR, MAGMAR, 'Flamethrower', [DCE, FIRE], false, 'DCE + 1 Fire cannot pay [Colourless][Fire][Fire]');
attackCase('A3', MAGMAR, MAGMAR, 'Flamethrower', [DCE, FIRE, FIRE], true);
attackCase('A3', WARTORTLE, 'Wartortle BS', 'Bite', [DCE, WATER], true, 'DCE + 1 Water pays [Colourless][Colourless][Water]');
attackCase('A3', WARTORTLE, 'Wartortle BS', 'Bite', [DCE, LIGHT], false, 'DCE + off-type cannot pay the Water symbol');
attackCase('A3', WARTORTLE, 'Wartortle BS', 'Bite', [DCE], false);
attackCase('A3', CHARMELEON, 'Charmeleon BS', 'Slash', [DCE], false, '2 Colourless of 3');
attackCase('A3', CHARMELEON, 'Charmeleon BS', 'Slash', [DCE, LIGHT], true, 'all-Colourless cost: DCE + any');
// ---- A3: Rainbow Energy (counts as every basic type, provides 1 at a time)
attackCase('A3', MAGMAR, MAGMAR, 'Fire Punch', [RB], false, 'provides only 1');
attackCase('A3', MAGMAR, MAGMAR, 'Fire Punch', [RB, FIRE], true, 'Rainbow pays one Fire');
attackCase('A3', MAGMAR, MAGMAR, 'Fire Punch', [RB, RB], true);
attackCase('A3', MAGMAR, MAGMAR, 'Fire Punch', [RB, WATER], false, 'Rainbow is one Fire at most; Water is not Fire');
attackCase('A3', MAGMAR, MAGMAR, 'Flamethrower', [RB, FIRE, WATER], true, 'Rainbow as Fire, Water as Colourless');
attackCase('A3', MAGMAR, MAGMAR, 'Flamethrower', [RB, WATER, WATER], false, 'only one Fire symbol');
attackCase('A3', MAGMAR, MAGMAR, 'Flamethrower', [RB, DCE], false, 'Rainbow Fire + DCE: second Fire missing');
attackCase('A3', MAGMAR, MAGMAR, 'Flamethrower', [RB, DCE, FIRE], true);
attackCase('A3', WARTORTLE, 'Wartortle BS', 'Bite', [RB, LIGHT, LIGHT], true, 'Rainbow pays the Water');
attackCase('A3', WARTORTLE, 'Wartortle BS', 'Bite', [RB, LIGHT], false, 'only 2 Energy for a cost of 3');
attackCase('A3', POLIWRATH, 'Poliwrath BS', 'Water Gun', [RB, WATER, FIRE], true);
// ---- A3: Potion and Full Heal Energy (each provides 1 Colourless, a special Energy, not typed)
attackCase('A3', MAGMAR, MAGMAR, 'Flamethrower', [POTION, FIRE, FIRE], true, 'Potion = the Colourless');
attackCase('A3', MAGMAR, MAGMAR, 'Flamethrower', [FHE, FIRE, WATER], false, 'Full Heal = Colourless, not a Fire');
attackCase('A3', MAGMAR, MAGMAR, 'Fire Punch', [POTION, FIRE], false, 'Potion cannot pay a Fire symbol');
attackCase('A3', MAGMAR, MAGMAR, 'Flamethrower', [FHE, FIRE, FIRE], true);

// ---- A4: retreat costs are paid by any type. Retreat: Magmar 2, Poliwrath 3 (pool.json).
function retreatCase(cas, mon, top, en, pickNames, want, why) {
  const cost = poolCard(top).retreat;
  test(cas, `${top} retreat ${cost} with ${en.map(shortE).join('+')}: ${want ? 'legal, offered, cost paid' : 'illegal and absent'}${why ? ' (' + why + ')' : ''}`, t => {
    const { g, me } = scene({ me: { active: { mon, en }, bench: [{ mon: PIDGEY }] }, opp: BASE_OPP });
    const eng = accepts(g.state, new C.RetreatAction(me.id, 0), g.store);
    const env = keysOf(g).includes('retreat|B0');
    t.eq('engine accepts the retreat', eng, want);
    t.eq('env offers retreat|B0', env, want);
    if (!want || !env) return;
    stepKey(g, 'retreat|B0');
    let d = g.decision();
    if (d && d.prompt && d.prompt.type === 'Choose energy') {
      pickNames.forEach(n => stepKey(g, 'pick|' + n));
      stepKey(g, 'done');
    }
    d = g.decision();
    if (d && d.prompt) throw new DriverError('prompt still open: ' + d.prompt.type + ' [' + d.options.map(o => o.key).join(' ; ') + ']');
    t.eq('Active after retreat', names(me.active.pokemons), [PIDGEY]);
    t.eq('Energy discarded', names(me.discard).sort(), pickNames.slice().sort());
    const left = en.slice(); pickNames.forEach(n => left.splice(left.indexOf(n), 1));
    t.eq('Energy left on the retreated Pokemon', names(me.bench[0].energies).sort(), left.sort());
  });
}
retreatCase('A4', MAGMAR, MAGMAR, [WATER, LIGHT], [WATER, LIGHT], true, 'two off-type basics, different types');
retreatCase('A4', MAGMAR, MAGMAR, [FIRE, WATER, LIGHT], [WATER, LIGHT], true, 'pays with off-type, keeps the Fire');
retreatCase('A4', MAGMAR, MAGMAR, [WATER], [], false, 'only 1 Energy for retreat 2');
retreatCase('A4', MAGMAR, MAGMAR, [DCE], [DCE], true, 'one DCE pays 2');
retreatCase('A4', POLIWRATH, 'Poliwrath BS', [FIRE, LIGHT, FE], [FIRE, LIGHT, FE], true, 'three off-type basics pay retreat 3');
retreatCase('A4', POLIWRATH, 'Poliwrath BS', [FIRE, LIGHT], [], false, 'only 2 Energy for retreat 3');
retreatCase('A4', MAGMAR, MAGMAR, [RB, WATER], [RB, WATER], true, 'Rainbow + Water');

// ---- A5 (C201 Amendment 1): the env's attach path. DCE in hand, a legal target: the env offers attaching it to each target,
// applies it, the Active then provides 2 Colourless (the engine: provides [C] with provideAmount 2), and Pidgey's Whirlwind [Colourless][Colourless] is offered. A basic as control.
const providedBy = (g, p) => { const e = new C.CheckProvidedEnergyEffect(p); g.store.reduceEffect(g.state, e); return e.energyMap; };
function attachCase(cas, hand, pre, want, why) {
  test(cas, `attach ${shortE(hand)} from hand to the Active Pidgey with ${pre.length ? pre.map(shortE).join('+') : 'no Energy'}: ${why}`, t => {
    const { g, me } = scene({ me: { active: { mon: PIDGEY, en: pre }, bench: [{ mon: MACHOP }], hand: [hand] }, opp: BASE_OPP });
    t.eq('Whirlwind cost', atkCost(PIDGEY, 'Whirlwind'), [2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]);
    const ks = keysOf(g);
    t.eq('env offers attach to the Active', ks.includes(`attach|${hand}|A`), true);
    t.eq('env offers attach to the Bench', ks.includes(`attach|${hand}|B0`), true);
    t.eq('Whirlwind offered before', ks.includes('attack|Whirlwind'), pre.length >= 2);
    stepKey(g, `attach|${hand}|A`);
    const d = g.decision();
    if (d && d.prompt) throw new DriverError('prompt open after attach: ' + d.prompt.type);
    t.eq('Energy on the Active', names(me.active.energies).sort(), [...pre, hand].sort());
    t.eq('hand after', names(me.hand), []);
    const map = providedBy(g, me);
    t.eq('Energy units provided (provideAmount, as the engine counts)', map.reduce((n, m) => n + (m.provideAmount || 1), 0), want.units);
    const e = map.find(m => m.card.fullName === hand) || {};
    t.eq(`${shortE(hand)} provides [types, amount]`, [e.provides, e.provideAmount], want.provides);
    t.eq('Whirlwind offered after', keysOf(g).includes('attack|Whirlwind'), want.attack);
  });
}
const CC = C.CardType.COLORLESS;
attachCase('A5', DCE, [], { units: 2, provides: [[CC], 2], attack: true }, 'DCE provides 2 Colourless, then Whirlwind is offered');
attachCase('A5', DCE, [FE], { units: 3, provides: [[CC], 2], attack: true }, 'DCE on top of a basic');
attachCase('A5', WATER, [], { units: 1, provides: [[C.CardType.WATER], 1], attack: false }, 'control: one basic provides 1, Whirlwind not yet');
attachCase('A5', WATER, [FE], { units: 2, provides: [[C.CardType.WATER], 1], attack: true }, 'control: a second basic, then Whirlwind is offered');

// ---- A6 (C202 Amendment 3's rule-9 trace): a Pokemon Power usable "as often as you like" whose repeat use changes nothing.
// Charizard's Energy Burn sets a marker on first use; after that the state is unchanged, so the env must stop offering it
// (a greedy policy otherwise repeats it to the turn's step cap). Fire Spin still offered; Energy Burn offered again next turn.
const CHARIZARD = ['Charmander BS', 'Charmeleon BS', 'Charizard BS'];
test('A6', 'Charizard Energy Burn: offered, used once, then not offered again in the same unchanged state', t => {
  const { g, me } = scene({ me: { active: { mon: CHARIZARD, en: [WATER, WATER, WATER, WATER] }, bench: [{ mon: PIDGEY }] }, opp: BASE_OPP });
  t.eq('Energy Burn offered before use', keysOf(g).includes('power|Energy Burn|A'), true);
  t.eq('Fire Spin offered before use (4 Water, cost RRRR)', keysOf(g).includes('attack|Fire Spin'), false);
  stepKey(g, 'power|Energy Burn|A');
  const d = g.decision();
  if (d && d.prompt) throw new DriverError('prompt open after Energy Burn: ' + d.prompt.type);
  t.eq('Fire Spin offered after Energy Burn (Water now provides R)', keysOf(g).includes('attack|Fire Spin'), true);
  t.eq('Energy Burn offered again in the unchanged state', keysOf(g).includes('power|Energy Burn|A'), false);
});

// ---- A7 (#1086, the cycle rule): a Power whose each use changes the state, repeated back and forth, returns to a state it was
// used from; there it isn't offered again. Alakazam's Damage Swap: 2 counters on the Active, one moved to the Bench and back.
const ALAKAZAM = ['Abra BS', 'Kadabra BS', 'Alakazam BS'];
function swap(g, pickKey) {                   // one Power use: move one counter (pickKey), then finish the prompt
  stepKey(g, 'power|Damage Swap|A');
  stepKey(g, pickKey);
  let d = g.decision();
  for (let n = 0; d && d.prompt && n < 4; n++) {
    const keys = d.options.map(o => o.key);
    if (keys.includes('done')) stepKey(g, 'done');
    else if (keys.includes('res|ok')) stepKey(g, 'res|ok');
    else throw new DriverError(`no done in ${d.prompt.type}: [${keys.join(' ; ')}]`);
    d = g.decision();
  }
  if (d && d.prompt) throw new DriverError('prompt still open after Damage Swap: ' + d.prompt.type);
}
test('A7', 'Alakazam Damage Swap A>B0 then B0>A: offered after the first move, not at the revisited start state', t => {
  const { g, me } = scene({ me: { active: { mon: ALAKAZAM }, bench: [{ mon: PIDGEY }] }, opp: BASE_OPP });
  me.active.damage = 20; g.cached = null;
  t.eq('Damage Swap offered at the start', keysOf(g).includes('power|Damage Swap|A'), true);
  swap(g, 'pick|A>B0');
  t.eq('damage after A>B0 [Active, Bench]', [me.active.damage, me.bench[0].damage], [10, 10]);
  t.eq('Damage Swap offered after one move (a new state)', keysOf(g).includes('power|Damage Swap|A'), true);
  swap(g, 'pick|B0>A');
  t.eq('damage after B0>A [Active, Bench]', [me.active.damage, me.bench[0].damage], [20, 0]);
  t.eq('Damage Swap offered at the revisited start state', keysOf(g).includes('power|Damage Swap|A'), false);
  t.eq('pass still offered there', keysOf(g).includes('pass'), true);
});

// ================================================================= run
function runOne(tc) {
  const t = new T();
  try {
    tc.fn(t);
    return { pass: t.fails.length === 0, detail: t.fails.length ? t.fails.join(' || ') : 'ok' };
  } catch (e) {
    return { pass: false, driver: true, detail: `DRIVER ${e instanceof DriverError ? '' : e.name + ' '}${e.message}` };
  }
}
const t0 = Date.now();
const RYUU_COMMIT = spawnSync('git', ['-C', RYUU, 'rev-parse', '--short', 'HEAD'], { encoding: 'utf8' }).stdout.trim();
if (ONLY !== null) { console.log('RESULT ' + JSON.stringify(runOne(TESTS[Number(ONLY)]))); process.exit(0); }

const rows = [];
TESTS.forEach((tc, i) => {
  const v = runOne(tc);
  const row = { case: tc.case, what: tc.what, pass: v.pass, detail: v.detail };
  if (!v.pass) {
    row.run1 = { pass: v.pass, detail: v.detail };
    const r = spawnSync(process.execPath, [__filename, '--only', String(i)], { encoding: 'utf8' });
    const line = (r.stdout || '').split('\n').find(l => l.startsWith('RESULT '));
    row.run2 = line ? JSON.parse(line.slice(7)) : { pass: false, detail: 'fresh re-run produced no result: ' + (r.stderr || '').slice(0, 300) };
    row.driver = !!v.driver;
    row.pass = row.run2.pass;
    if (row.run2.pass) row.detail = 'flaky: failed in-process, passed on fresh re-run (' + v.detail + ')';
  }
  console.log(`${row.pass ? 'PASS' : 'FAIL'}  ${tc.case} | ${tc.what}` + (row.pass ? '' : `\n      ${v.driver ? 'script/driver problem' : 'expected vs observed'}: ${v.detail}\n      fresh re-run: ${row.run2.pass ? 'PASS' : 'FAIL'} ${row.run2.detail}`));
  rows.push(row);
});
const passed = rows.filter(r => r.pass).length, failed = rows.length - passed;
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ tests: rows, passed, failed, engine_commit: RYUU_COMMIT }, null, 1));
console.log(`${passed} passed, ${failed} failed of ${rows.length} (engine ${RYUU_COMMIT}, ${((Date.now() - t0) / 1000).toFixed(1)}s) -> ${path.relative(ROOT, OUT)}`);
process.exitCode = 0;
