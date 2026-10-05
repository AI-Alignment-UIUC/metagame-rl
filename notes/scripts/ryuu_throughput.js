// Per-dispatch cost of ryuu-play on the Base-Fossil-Rocket pool.
// Setup is the same as ryuu_rulings_tests.js (clone, npm install, npm run compile for common+sets).
// Run: node ryuu_throughput.js <path-to-ryuu-play>

// Behavioural checks of ryuu-play's Base-Rocket cards against 2000-era WotC rulings (Rulings Compendium,
// https://compendium.pokegym.net/compendium.html). Each test builds a real game through the engine's store,
// rigs the board, dispatches actions, and compares the outcome with the dated ruling.
//
// Setup (once):  git clone https://github.com/keeshii/ryuu-play  &&  cd ryuu-play
//                npm install --workspace=packages/common --workspace=packages/sets --workspace=packages/simple-bot
//                npm run compile -w packages/common && npm run compile -w packages/sets
// Run:           node ryuu_throughput.js <path-to-ryuu-play>      (or set RYUU_PLAY=<path>)
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
cm.defineFormat('Base Sets', [S.baseSets.setBase, S.baseSets.setJungle, S.baseSets.setFossil, S.baseSets.setTeamRocket, S.baseSets.setPromos]);

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

// ---------------------------------------------------------------- throughput
const hr = () => process.hrtime.bigint();
const per = (ns, n) => (Number(ns) / 1e6 / n);

let t = hr(); const N0 = 100;
for (let i = 0; i < N0; i++) newGame();
const setupMs = per(hr() - t, N0);
console.log(`game setup (to stable):  ${setupMs.toFixed(2)} ms   -> ${(1000 / setupMs).toFixed(0)} games/s`);

const sim = newGame();
t = hr(); const N1 = 3000;
for (let i = 0; i < N1; i++) sim.clone();
const cloneMs = per(hr() - t, N1);
console.log(`Simulator.clone():       ${cloneMs.toFixed(3)} ms   -> ${(1000 / cloneMs).toFixed(0)} clones/s`);

// alternating PassTurn = cheapest full dispatch+reduce cycle
const s2 = newGame();
let n = 0;
t = hr();
for (let i = 0; i < 400; i++) {
  const st = s2.store.state;
  if (st.phase !== GamePhase.PLAYER_TURN) break;
  const pid = st.players[st.activePlayer].id;
  try { pass(s2, st.players[st.activePlayer]); n++; } catch (e) { break; }
}
const passMs = per(hr() - t, Math.max(n, 1));
console.log(`PassTurn dispatch:       ${passMs.toFixed(3)} ms   -> ${(1000 / passMs).toFixed(0)} dispatches/s   (${n} turns before stop)`);
