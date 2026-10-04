// Minimum state vector for July 2000 STS California, computed from the pool and from
// bounds observed in real games. Uses joint enumerations where components are dependent.
'use strict';
const H = require('./ryuu_harness.js');
const { buildArchivedDecks } = require('./ryuu_sts_decks.js');
const { SuperType, Stage } = H.C;

const decks = buildArchivedDecks(
  require('path').join(__dirname, '..', 'data', '2000-super-trainer-showdown-california', 'cards.csv'));

const used = new Map();
const perDeckDistinct = [];
for (const [, names] of decks) {
  const set = new Set(names);
  perDeckDistinct.push(set.size);
  for (const n of set) if (!used.has(n)) used.set(n, H.cm.getCardByName(n));
}
const cards = [...used.values()];
const pokemon = cards.filter(c => c.superType === SuperType.POKEMON);
const basics = pokemon.filter(p => p.stage === Stage.BASIC);
const evolved = pokemon.filter(p => p.stage !== Stage.BASIC);

// ---------------------------------------------------------------- legal slot occupancies
// A slot holds a legal stack, not an arbitrary pair of Pokemon. Enumerate them.
// Pokemon Breeder is in this field, so a Stage 2 can sit directly on the Basic two steps
// below it - Blastoise goes straight onto Squirtle, and Wartortle never appears.
const allPokemon = [].concat(H.S.baseSets.setBase, H.S.baseSets.setJungle,
  H.S.baseSets.setFossil, H.S.baseSets.setTeamRocket, H.S.baseSets.setPromos)
  .filter(c => c.superType === SuperType.POKEMON);
const hasBreeder = cards.some(c => c.name === 'Pokémon Breeder');

const stacks = [['(empty)']];
for (const b of basics) stacks.push([b.name]);
for (const e of evolved) {
  for (const b of basics) {
    if (b.name === e.evolvesFrom) { stacks.push([b.name, e.name]); continue; }
    if (hasBreeder && e.stage === Stage.STAGE_2) {
      const mid = allPokemon.find(m => m.name === e.evolvesFrom);
      if (mid && mid.evolvesFrom === b.name) stacks.push([b.name, e.name]);
    }
  }
}
console.log('=== legal occupancies of one Pokemon slot ===');
console.log(`  ${basics.length} basics + ${stacks.length - 1 - basics.length} legal evolution stacks + empty = ${stacks.length}`);
console.log('  stacks: ' + stacks.filter(s => s.length === 2).map(s => s.join('->')).join(', '));

// ---------------------------------------------------------------- energy multiset
const energies = cards.filter(c => c.superType === SuperType.ENERGY);
const E = energies.length;
const MAXE = 6;   // observed max on one Pokemon was 4; 6 leaves headroom
const C = (n, k) => { let r = 1; for (let i = 0; i < k; i++) r = (r * (n - i)) / (i + 1); return Math.round(r); };
let energyStates = 0;
for (let k = 0; k <= MAXE; k++) energyStates += C(k + E - 1, E - 1);
console.log(`\n=== Energy attached to one Pokemon ===`);
console.log(`  ${E} distinct Energy cards in the field, at most ${MAXE} on one Pokemon (4 observed)`);
console.log(`  multisets of size <=${MAXE} from ${E} kinds: ${energyStates}  ->  ${Math.log2(energyStates).toFixed(1)} bits`);
console.log(`  (independent 0..4 counts would cost ${(E * Math.log2(5)).toFixed(1)} bits - ${(E * Math.log2(5) / Math.log2(energyStates)).toFixed(1)}x worse)`);

// ---------------------------------------------------------------- slot total
const lg = Math.log2;
const maxHp = Math.max(...pokemon.map(p => p.hp));
const HP = maxHp / 10;
const MARKERS = 5;     // Chansey, Farfetch'd, Squirtle, Scyther, Goop Gas Attack
const parts = [
  ['stack occupancy', lg(stacks.length)],
  [`damage counters 0..${HP}`, lg(HP + 1)],
  ['conditions (4 exclusive x poisoned)', lg(8)],
  ['Energy multiset', lg(energyStates)],
  ['markers in effect', lg(MARKERS + 1)],
  ['played this turn', 1],
];
console.log('\n=== one Pokemon slot ===');
let slot = 0;
for (const [k, v] of parts) { slot += v; console.log(`  ${k.padEnd(38)} ${v.toFixed(1).padStart(6)} b`); }
console.log(`  ${'SLOT TOTAL'.padEnd(38)} ${slot.toFixed(1).padStart(6)} b`);
console.log(`  ${'x12 slots'.padEnd(38)} ${(12 * slot).toFixed(1).padStart(6)} b`);

// ---------------------------------------------------------------- zones
const vocab = Math.round(perDeckDistinct.reduce((a, b) => a + b) / perDeckDistinct.length);
const HANDMAX = 25;    // observed
const zones = [
  [`own hand (multiset, ~${vocab} kinds, <=${HANDMAX})`, vocab * lg(5)],
  ['opponent hand size only', lg(HANDMAX + 1)],
  ['own discard (public)', vocab * lg(5)],
  ['opponent discard (public)', vocab * lg(5)],
  ['two deck sizes', 2 * lg(61)],
  ['two prize counts', 2 * lg(7)],
  ['turn, active player, phase', 1 + lg(100) + lg(4)],
];
console.log('\n=== zones and globals ===');
let zoneBits = 0;
for (const [k, v] of zones) { zoneBits += v; console.log(`  ${k.padEnd(38)} ${v.toFixed(1).padStart(6)} b`); }

const total = 12 * slot + zoneBits;
console.log(`\n  ONE PLAYER'S COMPLETE OBSERVATION: ${total.toFixed(0)} bits = ${(total / 8).toFixed(0)} bytes`);
console.log('  (own deck+prize composition is implied by the decklist minus everything visible,');
console.log('   so it is not stored; prize identities are genuinely unknown to both players)');

// ---------------------------------------------------------------- dense
console.log('\n=== as a dense vector for a network ===');
const denseSlot = stacks.length + (HP + 1) + 5 + E + MARKERS + 1;
console.log(`  slot, one-hot stack(${stacks.length}) + damage(${HP + 1}) + cond(5) + energy counts(${E}) + markers(${MARKERS}) + 1 = ${denseSlot}`);
const dense = 12 * denseSlot + 3 * vocab + 7;
console.log(`  12 slots ${12 * denseSlot} + hand ${vocab} + 2 discards ${2 * vocab} + 7 scalars = ${dense} floats`);

console.log('\n=== scaling of the choice ===');
const variants = [
  ['this field, fixed matchup (two known lists)', stacks.length, vocab],
  ['this field, any deck from the 56-card pool', stacks.length, cards.length],
  ['full Base-Jungle-Fossil-Rocket+promos (233 cards)', 150, 233],
];
for (const [label, st, voc] of variants) {
  const ds = st + (HP + 1) + 5 + 12 + MARKERS + 1;
  console.log(`  ${label.padEnd(50)} ~${12 * ds + 3 * voc + 7} floats`);
}

// ---------------------------------------------------------------- observed bounds
const path = require('path');
const SimpleBot = require(path.join(H.RYUU, 'packages', 'simple-bot')).SimpleBot;
const { Simulator, State, AddPlayerAction, BotFlipMode, BotShuffleMode, GamePhase } = H;
const list = [...decks.values()];
const max = { energyOnOne: 0, energyOneType: 0, hand: 0, damage: 0, stack: 0, conds: 0, bench: 0, discard: 0 };
const energyTypeMax = new Map();
let samples = 0;

function observe(st) {
  samples++;
  for (const p of st.players) {
    max.hand = Math.max(max.hand, p.hand.cards.length);
    max.discard = Math.max(max.discard, p.discard.cards.length);
    max.bench = Math.max(max.bench, p.bench.filter(s => s.pokemons.cards.length).length);
    for (const slot of [p.active, ...p.bench]) {
      if (!slot.pokemons.cards.length) continue;
      max.stack = Math.max(max.stack, slot.pokemons.cards.length);
      max.damage = Math.max(max.damage, slot.damage);
      max.conds = Math.max(max.conds, slot.specialConditions.length);
      max.energyOnOne = Math.max(max.energyOnOne, slot.energies.cards.length);
      const byName = new Map();
      for (const e of slot.energies.cards) byName.set(e.name, (byName.get(e.name) || 0) + 1);
      for (const [n, c] of byName) {
        max.energyOneType = Math.max(max.energyOneType, c);
        energyTypeMax.set(n, Math.max(energyTypeMax.get(n) || 0, c));
      }
    }
  }
}

const GAMES = Number(process.argv[3] || 30);
for (let g = 0; g < GAMES; g++) {
  const deckA = list[g % list.length], deckB = list[(g + 3) % list.length];
  const sim = new Simulator(new State(), { flipMode: BotFlipMode.RANDOM, shuffleMode: BotShuffleMode.RANDOM });
  const factory = new SimpleBot('bot');
  const ais = [factory.createBotAi(1, deckA), factory.createBotAi(2, deckB)];
  sim.dispatch(new AddPlayerAction(1, 'A', deckA));
  sim.dispatch(new AddPlayerAction(2, 'B', deckB));
  const aiById = new Map([[1, ais[0]], [2, ais[1]]]);
  let n = 0;
  while (sim.store.state.phase !== GamePhase.FINISHED && n < 1500) {
    const st = sim.store.state;
    observe(st);
    const pending = st.prompts.find(p => p.result === undefined);
    const wantId = pending ? pending.playerId : st.players[st.activePlayer].id;
    let moved = false;
    for (const ai of [aiById.get(wantId), ...ais]) {
      if (!ai) continue;
      const a = ai.decodeNextAction(sim.store.state);
      if (!a) continue;
      try { sim.dispatch(a); } catch (e) { moved = false; break; }
      n++; moved = true; break;
    }
    if (!moved) break;
  }
  observe(sim.store.state);
}

console.log(`observed over ${GAMES} SimpleBot games (${samples} state samples):\n`);
console.log(`  max Energy cards on one Pokemon   ${max.energyOnOne}`);
console.log(`  max copies of one Energy on one   ${max.energyOneType}`);
console.log(`  max hand size                     ${max.hand}`);
console.log(`  max damage on one Pokemon         ${max.damage}  (${max.damage / 10} counters)`);
console.log(`  max evolution stack height        ${max.stack}`);
console.log(`  max simultaneous conditions       ${max.conds}`);
console.log(`  max occupied bench slots          ${max.bench}`);
console.log(`  max discard pile size             ${max.discard}`);
console.log('\n  per Energy card, max on a single Pokemon:');
for (const [n, c] of [...energyTypeMax].sort((a, b) => b[1] - a[1])) console.log(`    ${n.padEnd(26)} ${c}`);
