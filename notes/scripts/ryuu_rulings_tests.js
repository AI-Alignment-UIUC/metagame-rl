// Behavioural checks of ryuu-play's Base-Rocket cards against 2000-era WotC rulings (Rulings Compendium,
// https://compendium.pokegym.net/compendium.html). Each test builds a real game through the engine's store,
// rigs the board, dispatches actions, and compares the outcome with the dated ruling.
//
// Setup (once):  git clone https://github.com/keeshii/ryuu-play  &&  cd ryuu-play
//                npm install --workspace=packages/common --workspace=packages/sets --workspace=packages/simple-bot
//                npm run compile -w packages/common && npm run compile -w packages/sets
// Run:           node ryuu_rulings_tests.js <path-to-ryuu-play>      (or set RYUU_PLAY=<path>)
'use strict';
const path = require('path');
const RYUU = process.argv[2] || process.env.RYUU_PLAY || path.join(__dirname, '..', '..', 'ryuu-play');
const ROOT = path.join(RYUU, 'packages');
const C = require(path.join(ROOT, 'common'));
const S = require(path.join(ROOT, 'sets'));

const {
  CardManager, State, AddPlayerAction, PlayCardAction, AttackAction, PassTurnAction, ResolvePromptAction,
  PlayerType, SlotType, ChooseCardsPrompt, ChoosePokemonPrompt, ChoosePrizePrompt, ConfirmPrompt, AlertPrompt,
  ShowCardsPrompt, SelectPrompt, ChooseEnergyPrompt, OrderCardsPrompt, SuperType, Stage, SpecialCondition, GamePhase,
} = C;
const Simulator = C.Simulator;
const BotFlipMode = C.BotFlipMode, BotShuffleMode = C.BotShuffleMode;
if (!Simulator || !BotFlipMode) { console.error('Simulator/BotArbiter not exported; exports:', Object.keys(C).filter(k => /Sim|Bot/.test(k))); process.exit(1); }

const cm = CardManager.getInstance();
cm.defineFormat('Base Sets', [S.baseSets.setBase, S.baseSets.setJungle, S.baseSets.setFossil, S.baseSets.setTeamRocket]);

// ---------------------------------------------------------------- deck
const DECK = [
  ['Hitmonchan BS', 4], ['Electabuzz BS', 2], ['Scyther JU', 2], ['Mr. Mime JU', 2], ['Chansey BS', 2], ['Jigglypuff JU', 2],
  ['Wigglytuff JU', 2], ['Abra BS', 2], ['Kadabra BS', 2], ['Grimer FO', 2], ['Muk FO', 2], ['Oddish TR', 2], ['Dark Gloom TR', 2],
  ['Dark Vileplume TR', 2], ['Clefairy Doll BS', 2], ['Professor Oak BS', 2], ['Item Finder BS', 2], ['PlusPower BS', 3],
  ['Defender BS', 2], ['Energy Removal BS', 2], ['Lass BS', 2], ['Scoop Up BS', 2], ['Switch BS', 2], ["Rocket's Sneak Attack TR", 2],
  ['Bill BS', 1], ['Double Colorless Energy BS', 2], ['Fighting Energy BS', 4], ['Psychic Energy BS', 2],
];
function expand(list) { const out = []; for (const [n, k] of list) for (let i = 0; i < k; i++) out.push(n); return out; }
const missing = DECK.map(d => d[0]).filter(n => !cm.getCardByName(n));
if (missing.length) { console.error('unknown card names:', missing); process.exit(1); }
console.log('deck size', expand(DECK).length, '| Ditto FO registered at runtime:', !!cm.getCardByName('Ditto FO'));

// ---------------------------------------------------------------- prompt resolution
function matches(card, filter) {
  if (!filter) return true;
  if (!Array.isArray(filter)) filter = [filter];
  if (filter.length === 0 || filter.every(f => Object.keys(f).length === 0)) return true;
  return filter.some(f => Object.keys(f).every(k => {
    if (k === 'tags') return (card.tags || []).some(t => f.tags.includes(t));
    return card[k] === f[k];
  }));
}
function cardsByNames(prompt, names) {
  const cards = prompt.cards.cards; const idx = [];
  for (const n of names) { const i = cards.findIndex((c, j) => (c.fullName === n || c.name === n) && !idx.includes(j)); if (i < 0) throw new Error('prompt lacks ' + n + ' (has ' + cards.map(c => c.fullName).join(', ') + ')'); idx.push(i); }
  return idx;
}
function defaultCards(prompt) {
  const cards = prompt.cards.cards; const blocked = (prompt.options && prompt.options.blocked) || [];
  const min = prompt.options ? prompt.options.min : 1; const idx = [];
  for (let i = 0; i < cards.length && idx.length < Math.max(min, 1); i++) if (!blocked.includes(i) && matches(cards[i], prompt.filter)) idx.push(i);
  return idx.slice(0, Math.max(min, 0)).length >= min ? idx : idx;
}
function target(player, slot, index) { return { player, slot, index: index || 0 }; }
function defaultPokemon(prompt, state) {
  const me = state.players.find(p => p.id === prompt.playerId); const opp = state.players.find(p => p.id !== prompt.playerId);
  const types = prompt.playerType === PlayerType.ANY ? [PlayerType.BOTTOM_PLAYER, PlayerType.TOP_PLAYER] : [prompt.playerType];
  const blocked = (prompt.options && prompt.options.blocked) || [];
  for (const pt of types) {
    const pl = pt === PlayerType.BOTTOM_PLAYER ? me : opp;
    for (const st of prompt.slots) {
      const slots = st === SlotType.ACTIVE ? [pl.active] : pl.bench;
      for (let i = 0; i < slots.length; i++) {
        if (slots[i].pokemons.cards.length === 0) continue;
        if (blocked.some(b => b.player === pt && b.slot === st && b.index === i)) continue;
        return [target(pt, st, i)];
      }
    }
  }
  return [];
}
function resolveAll(sim, h) {
  h = h || {};
  for (let guard = 0; guard < 60; guard++) {
    const st = sim.store.state; const open = st.prompts.filter(p => p.result === undefined);
    if (!open.length) return;
    const p = open[0]; let r;
    if (p instanceof ChooseCardsPrompt) r = h.cards ? h.cards(p, st) : defaultCards(p);
    else if (p instanceof ChoosePokemonPrompt) r = h.pokemon ? h.pokemon(p, st) : defaultPokemon(p, st);
    else if (p instanceof ChoosePrizePrompt) r = [0];
    else if (p instanceof ChooseEnergyPrompt) r = h.energy ? h.energy(p, st) : p.energy.map((_, i) => i).slice(0, p.cost.length);
    else if (p instanceof SelectPrompt) r = 0;
    else if (p instanceof ConfirmPrompt) r = true;
    else if (p instanceof AlertPrompt || p instanceof ShowCardsPrompt) r = true;
    else if (p instanceof OrderCardsPrompt) r = p.cards.cards.map((_, i) => i);
    else throw new Error('unhandled prompt ' + p.type);
    // the store expects decoded results (Card[], PokemonSlot[], ...); the server decodes client indices the same way
    const decoded = p.decode(r, st);
    if (!p.validate(decoded, st)) throw new Error('harness produced an invalid resolution for ' + p.type + ' (' + JSON.stringify(r) + ')');
    sim.dispatch(new ResolvePromptAction(p.id, decoded));
  }
  throw new Error('prompt loop did not terminate');
}

// ---------------------------------------------------------------- game construction
function newGame(deckA, deckB, arb) {
  const sim = new Simulator(new State(), Object.assign({ flipMode: BotFlipMode.ALL_HEADS, shuffleMode: BotShuffleMode.NO_SHUFFLE }, arb || {}));
  sim.dispatch(new AddPlayerAction(1, 'A', expand(deckA || DECK)));
  sim.dispatch(new AddPlayerAction(2, 'B', expand(deckB || DECK)));
  resolveAll(sim, { cards: p => { const i = p.cards.cards.findIndex(c => matches(c, p.filter)); return [i]; } });
  return sim;
}
const P = sim => sim.store.state.players[0], O = sim => sim.store.state.players[1];
function clearSlot(pl, slot) { slot.pokemons.moveTo(pl.deck); slot.energies.moveTo(pl.deck); slot.trainers.moveTo(pl.deck); slot.damage = 0; slot.specialConditions = []; slot.pokemonPlayedTurn = 0; }
// find a copy of the card anywhere it might be resting (deck, hand, prizes, discard) and move it to the deck first
function take(pl, name) {
  const zones = [pl.deck, pl.hand, ...pl.prizes, pl.discard];
  for (const z of zones) {
    const c = z.cards.find(x => x.fullName === name);
    if (c) { if (z !== pl.deck) z.moveCardTo(c, pl.deck); return c; }
  }
  throw new Error(pl.name + ' has no free copy of ' + name);
}
function put(pl, slot, ...names) { clearSlot(pl, slot); for (const n of names) pl.deck.moveCardTo(take(pl, n), slot.pokemons); }
function energy(pl, slot, ...names) { for (const n of names) pl.deck.moveCardTo(take(pl, n), slot.energies); }
function hand(pl, ...names) { pl.hand.moveTo(pl.deck); for (const n of names) pl.deck.moveCardTo(take(pl, n), pl.hand); }
function discard(pl, ...names) { for (const n of names) pl.deck.moveCardTo(take(pl, n), pl.discard); }
function bench(pl, i, name) { put(pl, pl.bench[i], name); }
function idx(pl, name) { return pl.hand.cards.findIndex(c => c.fullName === name); }
function play(sim, pl, name, tgt, h) { sim.dispatch(new PlayCardAction(pl.id, idx(pl, name), tgt || target(PlayerType.BOTTOM_PLAYER, SlotType.BOARD, 0))); resolveAll(sim, h); }
function attack(sim, pl, name, h) { sim.dispatch(new AttackAction(pl.id, name)); resolveAll(sim, h); }
function pass(sim, pl) { sim.dispatch(new PassTurnAction(pl.id)); resolveAll(sim); }
function err(fn) { try { fn(); return null; } catch (e) { return (e && (e.message || e.code)) || JSON.stringify(e); } }
const names = list => list.cards.map(c => c.name).join(',');

// ---------------------------------------------------------------- tests
const results = [];
function test(id, ruling, expect, fn) {
  let got, ok = false, error = null;
  try { got = fn(); ok = String(got) === String(expect); } catch (e) {
    error = (e && e.stack) ? e.stack.split('\n').slice(0, 2).join(' ') : (e && (e.message || e.code)) ? (e.message || e.code) : JSON.stringify(e);
  }
  results.push({ id, ruling, expect, got: error ? 'EXCEPTION ' + error : got, ok });
}

test('T1 Professor Oak with nothing else in hand', 'Mar 2 2000: you may discard a hand of zero cards', 'playable, hand=7', () => {
  const sim = newGame(); const p = P(sim); hand(p, 'Professor Oak BS');
  const e = err(() => play(sim, p, 'Professor Oak BS'));
  return e ? 'error ' + e : (p.hand.cards.length === 7 ? 'playable, hand=7' : 'hand=' + p.hand.cards.length);
});

test('T2a Item Finder with no Trainer in discard', 'card text / Mar 29 2001: cannot play', 'error', () => {
  const sim = newGame(); const p = P(sim); hand(p, 'Item Finder BS', 'Fighting Energy BS', 'Fighting Energy BS');
  const e = err(() => play(sim, p, 'Item Finder BS')); return e ? 'error' : 'played';
});
test('T2b Item Finder retrieves PlusPower', 'card text', 'PlusPower in hand', () => {
  const sim = newGame(); const p = P(sim); hand(p, 'Item Finder BS', 'Fighting Energy BS', 'Fighting Energy BS'); discard(p, 'PlusPower BS');
  play(sim, p, 'Item Finder BS', null, { cards: pr => pr.cards === p.discard ? cardsByNames(pr, ['PlusPower BS']) : cardsByNames(pr, ['Fighting Energy BS', 'Fighting Energy BS']) });
  return idx(p, 'PlusPower BS') >= 0 ? 'PlusPower in hand' : 'hand=' + names(p.hand);
});

function jabWith(sim, extraPlusPowers, defender) {
  const p = P(sim), o = O(sim);
  put(p, p.active, 'Hitmonchan BS'); energy(p, p.active, 'Fighting Energy BS', 'Fighting Energy BS', 'Fighting Energy BS');
  put(o, o.active, defender); bench(o, 0, 'Scyther JU');
  hand(p, ...Array(extraPlusPowers).fill('PlusPower BS'));
  for (let i = 0; i < extraPlusPowers; i++) play(sim, p, 'PlusPower BS', target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0));
}
test('T3 PlusPower applied after Weakness (Jab vs Electabuzz)', 'Mar 2 2000: +10 after Weakness/Resistance', 50, () => {
  const sim = newGame(); jabWith(sim, 1, 'Electabuzz BS'); attack(sim, P(sim), 'Jab'); return O(sim).active.damage;
});
test('T4 PlusPower when Resistance zeroes damage (Jab vs Scyther)', 'Feb 17 2000: no +10 unless damage is done', 0, () => {
  const sim = newGame(); jabWith(sim, 1, 'Scyther JU'); attack(sim, P(sim), 'Jab'); return O(sim).active.damage;
});
test('T5 Two PlusPowers + Jab vs Mr. Mime', 'Trainer effects before Powers: 40 total, Invisible Wall prevents', 0, () => {
  const sim = newGame(); jabWith(sim, 2, 'Mr. Mime JU'); attack(sim, P(sim), 'Jab'); return O(sim).active.damage;
});
test('T12a Mr. Mime takes 20 from Jab', 'card text: only 30+ prevented', 20, () => {
  const sim = newGame(); jabWith(sim, 0, 'Mr. Mime JU'); attack(sim, P(sim), 'Jab'); return O(sim).active.damage;
});
test('T12b Mr. Mime takes 0 from Special Punch (40)', 'card text', 0, () => {
  const sim = newGame(); jabWith(sim, 0, 'Mr. Mime JU'); attack(sim, P(sim), 'Special Punch'); return O(sim).active.damage;
});
test('T6 Defender on Mr. Mime vs Special Punch (40-20=20 gets through)', 'Jul 6 2000: Defender reduces before Invisible Wall', 20, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Hitmonchan BS'); energy(p, p.active, 'Fighting Energy BS', 'Fighting Energy BS', 'Fighting Energy BS');
  put(o, o.active, 'Mr. Mime JU'); bench(o, 0, 'Scyther JU');
  pass(sim, p);                                   // turn 2: opponent plays Defender on Mr. Mime
  hand(o, 'Defender BS'); play(sim, o, 'Defender BS', target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0));
  pass(sim, o);                                   // turn 3
  attack(sim, p, 'Special Punch'); return o.active.damage;
});
test('T7 Defender on Chansey reduces its own Double-edge recoil', 'Feb 10 2000: Defender protects from your own attacks', 60, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Chansey BS'); energy(p, p.active, 'Double Colorless Energy BS', 'Double Colorless Energy BS');
  put(o, o.active, 'Hitmonchan BS'); bench(o, 0, 'Scyther JU');
  hand(p, 'Defender BS'); play(sim, p, 'Defender BS', target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0));
  attack(sim, p, 'Double-edge'); return p.active.damage;
});
test('T8 KO on Clefairy Doll gives no prize', 'Feb 10 2000: no prize for Clefairy Doll / Mysterious Fossil', 'prizes=6, opp active Scyther', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Hitmonchan BS'); energy(p, p.active, 'Fighting Energy BS');
  put(o, o.active, 'Clefairy Doll BS'); bench(o, 0, 'Scyther JU');
  attack(sim, p, 'Jab');
  const prizes = p.prizes.filter(pr => pr.cards.length > 0).length; const act = o.active.getPokemonCard();
  return 'prizes=' + prizes + ', opp active ' + (act ? act.name : 'none');
});
test('T9 Energy Removal takes a Double Colorless Energy as one card', 'Mar 2 2000 / DCE is one Energy card', 'opp energies=0, DCE in discard', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(o, o.active, 'Scyther JU'); energy(o, o.active, 'Double Colorless Energy BS');
  hand(p, 'Energy Removal BS'); play(sim, p, 'Energy Removal BS');
  return 'opp energies=' + o.active.energies.cards.length + ', ' + (o.discard.cards.some(c => c.name === 'Double Colorless Energy') ? 'DCE in discard' : 'discard=' + names(o.discard));
});
test('T10 Wigglytuff Do the Wave with 5 benched', 'card text: 10 + 10 per Benched Pokemon', 60, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Jigglypuff JU', 'Wigglytuff JU'); energy(p, p.active, 'Double Colorless Energy BS', 'Fighting Energy BS');
  ['Hitmonchan BS', 'Hitmonchan BS', 'Scyther JU', 'Electabuzz BS', 'Chansey BS'].forEach((n, i) => bench(p, i, n));
  put(o, o.active, 'Hitmonchan BS'); bench(o, 0, 'Scyther JU');
  attack(sim, p, 'Do the Wave'); return o.active.damage;
});
test('T11a Dark Vileplume Hay Fever blocks the opponent\'s Trainers', 'card text', 'error', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(o, o.bench[0], 'Oddish TR', 'Dark Gloom TR', 'Dark Vileplume TR');
  hand(p, 'Professor Oak BS'); const e = err(() => play(sim, p, 'Professor Oak BS')); return e ? 'error' : 'played';
});
test('T11b Hay Fever blocks its owner too', 'card text: neither player', 'error', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(o, o.bench[0], 'Oddish TR', 'Dark Gloom TR', 'Dark Vileplume TR'); pass(sim, p);
  hand(o, 'Professor Oak BS'); const e = err(() => play(sim, o, 'Professor Oak BS')); return e ? 'error' : 'played';
});
test('T11c Muk Toxic Gas switches Hay Fever off', 'card text', 'played', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(o, o.bench[0], 'Oddish TR', 'Dark Gloom TR', 'Dark Vileplume TR'); put(p, p.bench[0], 'Grimer FO', 'Muk FO');
  hand(p, 'Professor Oak BS'); const e = err(() => play(sim, p, 'Professor Oak BS')); return e ? 'error ' + e : 'played';
});
test('T13 Lass shuffles both players\' Trainers into decks', 'card text', 'A:Fighting Energy B:Psychic Energy', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  hand(p, 'Lass BS', 'PlusPower BS', 'Fighting Energy BS'); hand(o, 'Switch BS', 'Bill BS', 'Psychic Energy BS');
  play(sim, p, 'Lass BS'); return 'A:' + names(p.hand) + ' B:' + names(o.hand);
});
test('T14a First player may attack on turn 1', '2000 rules: no first-turn attack restriction', 'turn1 attack ok', () => {
  const sim = newGame(); const p = P(sim), o = O(sim); const turn = sim.store.state.turn;
  put(p, p.active, 'Hitmonchan BS'); energy(p, p.active, 'Fighting Energy BS'); put(o, o.active, 'Scyther JU'); bench(o, 0, 'Scyther JU');
  const e = err(() => attack(sim, p, 'Jab')); return e ? 'error ' + e : (turn === 1 ? 'turn1 attack ok' : 'turn was ' + turn);
});
test('T14b Neither player may evolve on their first turn; allowed on the next', 'Jan 9 2003 chat restating the standing rule', 'A1:error B1:error A2:ok', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  // starters keep pokemonPlayedTurn from setup; replace the Pokemon card but keep that turn stamp
  const stampP = p.active.pokemonPlayedTurn, stampO = o.active.pokemonPlayedTurn;
  put(p, p.active, 'Abra BS'); p.active.pokemonPlayedTurn = stampP; put(o, o.active, 'Abra BS'); o.active.pokemonPlayedTurn = stampO;
  hand(p, 'Kadabra BS'); hand(o, 'Kadabra BS');
  // after a rejected action the store swaps in its backup state, so re-fetch player objects each time
  const a1 = err(() => play(sim, P(sim), 'Kadabra BS', target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0)));
  pass(sim, P(sim));
  const b1 = err(() => play(sim, O(sim), 'Kadabra BS', target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0)));
  pass(sim, O(sim));
  const a2 = err(() => play(sim, P(sim), 'Kadabra BS', target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0)));
  return 'A1:' + (a1 ? 'error' : 'ok') + ' B1:' + (b1 ? 'error' : 'ok') + ' A2:' + (a2 ? 'error ' + a2 : 'ok');
});
test('T15 Rocket\'s Sneak Attack shuffles a chosen Trainer from the opponent\'s hand', 'card text', 'opp hand=PlusPower,Psychic Energy', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  hand(p, "Rocket's Sneak Attack TR"); hand(o, 'Bill BS', 'PlusPower BS', 'Psychic Energy BS');
  play(sim, p, "Rocket's Sneak Attack TR", null, { cards: pr => cardsByNames(pr, ['Bill BS']) });
  return 'opp hand=' + names(o.hand);
});
test('T16 Scoop Up returns the Basic and discards evolution + Energy', 'card text (2000 wording)', 'hand=Jigglypuff discard=Wigglytuff,Double Colorless Energy', () => {
  const sim = newGame(); const p = P(sim);
  put(p, p.active, 'Jigglypuff JU', 'Wigglytuff JU'); energy(p, p.active, 'Double Colorless Energy BS'); bench(p, 0, 'Scyther JU');
  // first prompt: which Pokemon to scoop (choose the Active); the engine then asks for a new Active from the Bench
  hand(p, 'Scoop Up BS'); play(sim, p, 'Scoop Up BS', null, { pokemon: (pr, st) => pr.slots.includes(SlotType.ACTIVE) ? [target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0)] : defaultPokemon(pr, st) });
  return 'hand=' + names(p.hand) + ' discard=' + p.discard.cards.filter(c => c.name !== 'Scoop Up').map(c => c.name).join(',');
});
test('T17 Switch works on a Paralyzed Active', 'Feb 3 2000', 'active Scyther', () => {
  const sim = newGame(); const p = P(sim);
  put(p, p.active, 'Hitmonchan BS'); p.active.specialConditions = [SpecialCondition.PARALYZED]; bench(p, 0, 'Scyther JU');
  hand(p, 'Switch BS'); const e = err(() => play(sim, p, 'Switch BS'));
  return e ? 'error ' + e : 'active ' + p.active.getPokemonCard().name;
});
test('T18 Opening hand with Mysterious Fossil and no Basic', 'Feb 10 / Apr 27 2000: it is a Trainer in hand, you must mulligan', 'mulligan (no Fossil as starter)', () => {
  const deck = [['Mysterious Fossil FO', 1], ['Fighting Energy BS', 6], ['Hitmonchan BS', 4], ['Scyther JU', 4], ['Chansey BS', 4], ['Professor Oak BS', 4],
    ['Bill BS', 4], ['PlusPower BS', 4], ['Switch BS', 4], ['Gust of Wind BS', 4], ['Psychic Energy BS', 21]];
  const sim = new Simulator(new State(), { flipMode: BotFlipMode.ALL_HEADS, shuffleMode: BotShuffleMode.NO_SHUFFLE });
  sim.dispatch(new AddPlayerAction(1, 'A', expand(deck))); sim.dispatch(new AddPlayerAction(2, 'B', expand(DECK)));
  const st = sim.store.state; const pr = st.prompts.filter(x => x.result === undefined && x instanceof ChooseCardsPrompt && x.playerId === st.players[0].id)[0];
  if (!pr) return 'no starting prompt for A (phase ' + st.phase + ', open=' + st.prompts.filter(x => x.result === undefined).map(x => x.type + '@' + x.playerId).join(';') + ', ids=' + st.players.map(x => x.id).join('/') + ', hand=' + names(st.players[0].hand) + ')';
  const offered = pr.cards.cards.filter(c => matches(c, pr.filter)).map(c => c.name);
  return offered.includes('Mysterious Fossil') ? 'Fossil offered as starter: ' + offered.join(',') : 'mulligan (no Fossil as starter)';
});

// ---------------------------------------------------------------- report
let passed = 0;
for (const r of results) { if (r.ok) passed++; console.log((r.ok ? 'PASS ' : 'FAIL ') + r.id + ' | expected: ' + r.expect + ' | got: ' + r.got + ' | ' + r.ruling); }
console.log('\n' + passed + '/' + results.length + ' checks agree with the 2000-era ruling');
