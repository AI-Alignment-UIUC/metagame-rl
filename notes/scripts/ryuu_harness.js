// Shared test harness for driving real ryuu-play games from Node.
//
// Extracted from ryuu_rulings_tests.js so several test files can share one engine and one
// registered format (CardManager.defineFormat throws on a duplicate format name).
//
// Setup (once):  git clone https://github.com/keeshii/ryuu-play  &&  cd ryuu-play
//                npm install --workspace=packages/common --workspace=packages/sets --workspace=packages/simple-bot
//                npm run compile -w packages/common && npm run compile -w packages/sets
'use strict';
const path = require('path');

const RYUU = path.resolve(process.argv[2] || process.env.RYUU_PLAY || path.join(__dirname, '..', '..', 'ryuu-play'));
const ROOT = path.join(RYUU, 'packages');
const C = require(path.join(ROOT, 'common'));
const S = require(path.join(ROOT, 'sets'));

const {
  CardManager, State, AddPlayerAction, PlayCardAction, AttackAction, PassTurnAction, ResolvePromptAction,
  RetreatAction, PlayerType, SlotType, ChooseCardsPrompt, ChoosePokemonPrompt, ChoosePrizePrompt, ConfirmPrompt,
  AlertPrompt, ShowCardsPrompt, SelectPrompt, ChooseEnergyPrompt, OrderCardsPrompt, ChooseAttackPrompt,
  AttachEnergyPrompt, SuperType, Stage, SpecialCondition, GamePhase, CheckHpEffect, CheckPokemonStatsEffect,
  CheckPokemonTypeEffect, CheckRetreatCostEffect,
} = C;
const Simulator = C.Simulator;
const BotFlipMode = C.BotFlipMode, BotShuffleMode = C.BotShuffleMode;
if (!Simulator || !BotFlipMode) {
  console.error('Simulator/BotArbiter not exported; exports:', Object.keys(C).filter(k => /Sim|Bot/.test(k)));
  process.exit(1);
}

const cm = CardManager.getInstance();
const SETS = [S.baseSets.setBase, S.baseSets.setJungle, S.baseSets.setFossil, S.baseSets.setTeamRocket];
if (S.baseSets.setPromos) { SETS.push(S.baseSets.setPromos); }
cm.defineFormat('Base Sets', SETS);

// ---------------------------------------------------------------- deck
// A sandbox deck: every card a test might rig onto the board has to be somewhere it can be
// taken from, so this is a grab bag rather than a legal tournament list.
const DECK = [
  ['Hitmonchan BS', 4], ['Electabuzz BS', 2], ['Scyther JU', 2], ['Mr. Mime JU', 2], ['Chansey BS', 2], ['Jigglypuff JU', 2],
  ['Wigglytuff JU', 2], ['Abra BS', 2], ['Kadabra BS', 2], ['Grimer FO', 2], ['Muk FO', 2], ['Oddish TR', 2], ['Dark Gloom TR', 2],
  ['Dark Vileplume TR', 2], ['Clefairy Doll BS', 2], ['Professor Oak BS', 2], ['Item Finder BS', 2], ['PlusPower BS', 3],
  ['Defender BS', 2], ['Energy Removal BS', 2], ['Lass BS', 2], ['Scoop Up BS', 2], ['Switch BS', 2], ["Rocket's Sneak Attack TR", 2],
  ['Bill BS', 1], ['Double Colorless Energy BS', 2], ['Fighting Energy BS', 4], ['Psychic Energy BS', 2],
];

// A 60-card sandbox for the STS-card tests: every card those tests rig onto the board has to
// be takeable from somewhere, and the engine enforces exactly 60 with at most 4 per name.
const STS_DECK = [
  ['Ditto FO', 2], ['Mewtwo PR', 2], ['Mew PR', 2], ['Mewtwo BS', 1], ['Mr. Mime JU', 2],
  ['Grimer FO', 1], ['Muk FO', 1], ['Hitmonchan BS', 2], ['Electabuzz BS', 1], ['Scyther JU', 2],
  ['Chansey BS', 1], ['Jigglypuff JU', 1], ['Wigglytuff JU', 1], ['Squirtle BS', 1], ['Wartortle BS', 1],
  ['Blastoise BS', 1], ['Abra BS', 1], ['Kadabra BS', 1], ['Alakazam BS', 1], ['Lickitung JU', 1],
  ['Magmar FO', 1], ['Oddish TR', 1], ['Dark Gloom TR', 1], ['Dark Vileplume TR', 1],
  ['Clefairy Doll BS', 1], ['Professor Oak BS', 1], ['Item Finder BS', 1], ['PlusPower BS', 2],
  ['Defender BS', 1], ['Energy Removal BS', 1], ['Gust of Wind BS', 1], ['Switch BS', 1], ['Scoop Up BS', 1],
  ['Psychic Energy BS', 4], ['Fighting Energy BS', 4], ['Water Energy BS', 2], ['Lightning Energy BS', 2],
  ['Double Colorless Energy BS', 4], ['Rainbow Energy TR', 2], ['Full Heal Energy TR', 2],
];

function expand(list) { const out = []; for (const [n, k] of list) for (let i = 0; i < k; i++) out.push(n); return out; }

const FULL_DECK = cm.getCardByName('Ditto FO') && cm.getCardByName('Mewtwo PR') ? STS_DECK : DECK;
const unknown = FULL_DECK.map(d => d[0]).filter(n => !cm.getCardByName(n));
if (unknown.length) { console.error('unknown card names:', unknown); process.exit(1); }
if (expand(FULL_DECK).length !== 60) {
  console.error('sandbox deck is ' + expand(FULL_DECK).length + ' cards, must be 60');
  process.exit(1);
}

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
  for (const n of names) {
    const i = cards.findIndex((c, j) => (c.fullName === n || c.name === n) && !idx.includes(j));
    if (i < 0) throw new Error('prompt lacks ' + n + ' (has ' + cards.map(c => c.fullName).join(', ') + ')');
    idx.push(i);
  }
  return idx;
}
function defaultCards(prompt) {
  const cards = prompt.cards.cards; const blocked = (prompt.options && prompt.options.blocked) || [];
  const min = prompt.options ? prompt.options.min : 1; const idx = [];
  for (let i = 0; i < cards.length && idx.length < Math.max(min, 1); i++) {
    if (!blocked.includes(i) && matches(cards[i], prompt.filter)) idx.push(i);
  }
  return idx.slice(0, Math.max(min, 0)).length >= min ? idx : idx;
}
function target(player, slot, index) { return { player, slot, index: index || 0 }; }
function defaultPokemon(prompt, state) {
  const me = state.players.find(p => p.id === prompt.playerId);
  const opp = state.players.find(p => p.id !== prompt.playerId);
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
    if (p instanceof AttachEnergyPrompt) r = h.attach ? h.attach(p, st) : [];
    else if (p instanceof ChooseAttackPrompt) r = h.choice ? h.choice(p, st) : null;
    else if (p instanceof ChooseCardsPrompt) r = h.cards ? h.cards(p, st) : defaultCards(p);
    else if (p instanceof ChoosePokemonPrompt) r = h.pokemon ? h.pokemon(p, st) : defaultPokemon(p, st);
    else if (p instanceof ChoosePrizePrompt) r = [0];
    else if (p instanceof ChooseEnergyPrompt) r = h.energy ? h.energy(p, st) : p.energy.map((_, i) => i).slice(0, p.cost.length);
    else if (p instanceof SelectPrompt) r = 0;
    else if (p instanceof ConfirmPrompt) r = true;
    else if (p instanceof AlertPrompt || p instanceof ShowCardsPrompt) r = true;
    else if (p instanceof OrderCardsPrompt) r = p.cards.cards.map((_, i) => i);
    else throw new Error('unhandled prompt ' + p.type);
    const decoded = p.decode(r, st);
    if (!p.validate(decoded, st)) throw new Error('harness produced an invalid resolution for ' + p.type + ' (' + JSON.stringify(r) + ')');
    sim.dispatch(new ResolvePromptAction(p.id, decoded));
  }
  throw new Error('prompt loop did not terminate');
}

// ---------------------------------------------------------------- game construction
function newGame(deckA, deckB, arb) {
  const sim = new Simulator(new State(), Object.assign({ flipMode: BotFlipMode.ALL_HEADS, shuffleMode: BotShuffleMode.NO_SHUFFLE }, arb || {}));
  sim.dispatch(new AddPlayerAction(1, 'A', expand(deckA || FULL_DECK)));
  sim.dispatch(new AddPlayerAction(2, 'B', expand(deckB || FULL_DECK)));
  resolveAll(sim, { cards: p => { const i = p.cards.cards.findIndex(c => matches(c, p.filter)); return [i]; } });
  return sim;
}
const P = sim => sim.store.state.players[0], O = sim => sim.store.state.players[1];
function clearSlot(pl, slot) {
  slot.pokemons.moveTo(pl.deck); slot.energies.moveTo(pl.deck); slot.trainers.moveTo(pl.deck);
  slot.damage = 0; slot.specialConditions = []; slot.pokemonPlayedTurn = 0;
  if (slot.marker) slot.marker.markers = [];
}
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
function play(sim, pl, name, tgt, h) {
  sim.dispatch(new PlayCardAction(pl.id, idx(pl, name), tgt || target(PlayerType.BOTTOM_PLAYER, SlotType.BOARD, 0)));
  resolveAll(sim, h);
}
function attack(sim, pl, name, h) { sim.dispatch(new AttackAction(pl.id, name)); resolveAll(sim, h); }
// Pokemon Powers are not Actions; the client raises UsePowerEffect on the store.
// The state deep-clones its cards, so the Power object has to come from the card that is
// actually in the slot - the CardManager singleton's Power is a different object and
// every card's `effect.power === this.powers[0]` guard would miss it.
function usePower(sim, pl, slot, powerName, h) {
  const card = slot.getPokemonCard();
  if (!card) throw new Error('no Pokemon in that slot');
  const power = (card.powers || []).find(x => x.name === powerName);
  if (!power) throw new Error(card.fullName + ' has no power ' + powerName);
  sim.store.reduceEffect(sim.store.state, new C.UsePowerEffect(pl, power, card));
  resolveAll(sim, h);
}
function pass(sim, pl) { sim.dispatch(new PassTurnAction(pl.id)); resolveAll(sim); }
function err(fn) { try { fn(); return null; } catch (e) { return (e && (e.message || e.code)) || JSON.stringify(e); } }
const names = list => list.cards.map(c => c.name).join(',');

// ---------------------------------------------------------------- queries
function effectiveHp(sim, pl, slot) {
  const e = new CheckHpEffect(pl, slot);
  sim.store.reduceEffect(sim.store.state, e);
  return e.hp;
}
function effectiveStats(sim, slot) {
  const e = new CheckPokemonStatsEffect(slot);
  sim.store.reduceEffect(sim.store.state, e);
  return e;
}
function effectiveTypes(sim, slot) {
  const e = new CheckPokemonTypeEffect(slot);
  sim.store.reduceEffect(sim.store.state, e);
  return e.cardTypes;
}
function effectiveRetreat(sim, pl) {
  const e = new CheckRetreatCostEffect(pl);
  sim.store.reduceEffect(sim.store.state, e);
  return e.cost;
}

// ---------------------------------------------------------------- runner
const results = [];
function test(id, note, expect, fn) {
  let got, ok = false, error = null;
  try { got = fn(); ok = String(got) === String(expect); } catch (e) {
    error = (e && e.stack) ? e.stack.split('\n').slice(0, 2).join(' ') : (e && (e.message || e.code)) ? (e.message || e.code) : JSON.stringify(e);
  }
  results.push({ id, note, expect, got: error ? 'EXCEPTION ' + error : got, ok });
}
function report(title) {
  let passed = 0;
  console.log('\n' + title);
  for (const r of results) {
    if (r.ok) passed++;
    console.log((r.ok ? 'PASS ' : 'FAIL ') + r.id + ' | expected: ' + r.expect + ' | got: ' + r.got + ' | ' + r.note);
  }
  console.log('\n' + passed + '/' + results.length + ' checks pass');
  return passed === results.length;
}

module.exports = {
  C, S, cm, RYUU,
  CardManager, State, AddPlayerAction, PlayCardAction, AttackAction, PassTurnAction, ResolvePromptAction,
  RetreatAction, PlayerType, SlotType, ChooseCardsPrompt, ChoosePokemonPrompt, ChoosePrizePrompt, ConfirmPrompt,
  AlertPrompt, ShowCardsPrompt, SelectPrompt, ChooseEnergyPrompt, OrderCardsPrompt, ChooseAttackPrompt,
  AttachEnergyPrompt, SuperType, Stage, SpecialCondition, GamePhase, Simulator, BotFlipMode, BotShuffleMode,
  CheckHpEffect, CheckPokemonStatsEffect, CheckPokemonTypeEffect, CheckRetreatCostEffect,
  DECK, FULL_DECK, expand, matches, cardsByNames, defaultCards, defaultPokemon, target, resolveAll,
  newGame, P, O, clearSlot, take, put, energy, hand, discard, bench, idx, play, attack, usePower, pass, err, names,
  effectiveHp, effectiveStats, effectiveTypes, effectiveRetreat,
  test, report, results,
};
