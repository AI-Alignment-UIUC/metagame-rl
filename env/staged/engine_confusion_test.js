// Test for env/staged/engine.js (2000 Confusion rules, Rules.baseEraConfusion). Run: node env/staged/engine_confusion_test.js
//
// 1. The staged file is env/engine.js with only the RULES lines changed, and its format turns the flag on.
// 2. If the engine build it loads has the flag (ryuu-play compiled after the change, or RYUU_PLAY=<such a build>),
//    the format plays Confusion by the 2000 rules: Mr. Mime JU knocks itself out (20 x2 for its own Weakness, Mar 30,
//    2000 ruling), and a Confused Pokemon retreats only on heads, Energy paid, one try a turn (Apr 13, 2000 ruling).
'use strict';
const assert = require('assert');
const fs = require('fs');
const path = require('path');

process.env.RYUU_PLAY = process.env.RYUU_PLAY || path.resolve(__dirname, '..', '..', 'ryuu-play');
const { C, cm, RULES, newState, newStore } = require('./engine.js');

// 1. Same file but for the RULES comment and line.
const strip = src => src.replace(/\/\/ 2000 rules:[^]*?const RULES = [^\n]*\n/, '');
const staged = fs.readFileSync(path.join(__dirname, 'engine.js'), 'utf8');
const live = fs.readFileSync(path.join(__dirname, '..', 'engine.js'), 'utf8');
assert.strictEqual(strip(staged), strip(live), 'staged engine.js differs from env/engine.js outside RULES');
assert.strictEqual(RULES.baseEraConfusion, true);
assert.strictEqual(RULES.fossilsAsStarters, false);
assert.strictEqual(RULES.mulliganDrawCards, 2);
assert.strictEqual(newState().rules.baseEraConfusion, true);
console.log('ok   staged engine.js = env/engine.js + baseEraConfusion in RULES');

if (!('baseEraConfusion' in new C.Rules())) {
  console.log('skip behaviour checks: this ryuu-play build has no Rules.baseEraConfusion (compile it, or set RYUU_PLAY)');
  process.exit(0);
}

const card = name => new (cm.getCardByName(name).constructor)();

// Player 1's turn; its Active `active` Confused with `energy` attached, a Scyther on the Bench.
function scene(active, energy, baseEraConfusion = true) {
  const state = newState();
  state.rules.baseEraConfusion = baseEraConfusion;
  state.players = [1, 2].map(id => {
    const p = new C.Player();
    p.id = id;
    p.name = 'P' + id;
    p.active = new C.PokemonSlot();
    p.active.pokemons.cards.push(card(id === 1 ? active : 'Scyther JU'));
    for (let i = 0; i < 5; i++) p.bench.push(new C.PokemonSlot());
    p.bench[0].pokemons.cards.push(card('Scyther JU'));
    for (let i = 0; i < 6; i++) { const z = new C.CardList(); z.cards.push(card('Scyther JU')); p.prizes.push(z); }
    for (let i = 0; i < 10; i++) p.deck.cards.push(card('Scyther JU'));
    return p;
  });
  for (const e of energy) state.players[0].active.energies.cards.push(card(e));
  state.players[0].active.specialConditions.push(C.SpecialCondition.CONFUSED);
  state.phase = C.GamePhase.PLAYER_TURN;
  state.activePlayer = 0;
  state.turn = 3;
  return newStore(state);
}

// Dispatch, then answer coin flips from `flips` and pay Retreat Costs with the first Energy. Returns the flips used.
function play(store, action, flips) {
  store.dispatch(action);
  let n = 0;
  for (;;) {
    const p = store.state.prompts.find(q => q.result === undefined);
    if (!p) return n;
    if (p.type === 'Coin flip') store.dispatch(new C.ResolvePromptAction(p.id, flips[n++]));
    else if (p.type === 'Choose energy') store.dispatch(new C.ResolvePromptAction(p.id, p.energy.slice(0, p.cost.length)));
    else if (p.type === 'Choose prize') store.dispatch(new C.ResolvePromptAction(p.id, p.decode([0], store.state)));
    else return n; // e.g. choosing a new Active after a knockout
  }
}

const MIME = ['Mr. Mime JU', ['Psychic Energy BS', 'Double Colorless Energy BS']];

// 2a. Tails on an attack: 20, doubled by Mr. Mime's own Weakness, knocks out its 40 HP. The later rules: 30, no Weakness.
{
  const store = scene(...MIME);
  const me = store.state.players[0], mime = me.active.getPokemonCard();
  play(store, new C.AttackAction(1, 'Meditate'), [false]);
  assert.ok(me.discard.cards.includes(mime), 'Mr. Mime should be knocked out by 40');
  const later = scene(...MIME, false);
  play(later, new C.AttackAction(1, 'Meditate'), [false]);
  assert.strictEqual(later.state.players[0].active.damage, 30);
  console.log('ok   Confused Mr. Mime JU: 40 to itself (KO) under the 2000 rules, 30 under the later rules');
}

// 2b. Retreat: the cost is paid first; tails keeps it Active and ends retreating for the turn; heads retreats.
{
  const store = scene('Mr. Mime JU', ['Double Colorless Energy BS']);
  const me = store.state.players[0], mime = me.active;
  assert.strictEqual(play(store, new C.RetreatAction(1, 0), [false]), 1);
  assert.strictEqual(me.active, mime);
  assert.strictEqual(mime.energies.cards.length, 0);
  assert.throws(() => store.dispatch(new C.RetreatAction(1, 0)), e => e.message === C.GameMessage.RETREAT_ALREADY_USED);

  const free = scene('Scyther JU', []);
  const fme = free.state.players[0], scyther = fme.active;
  assert.strictEqual(play(free, new C.RetreatAction(1, 0), [true]), 1);
  assert.strictEqual(fme.bench[0], scyther);
  console.log('ok   Confused retreat: cost paid, tails stays (no second try), heads retreats; free retreat flips too');
}
