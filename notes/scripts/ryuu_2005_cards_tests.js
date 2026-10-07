// Behavioural tests for the cards added for the Worlds 2005 "Birds" list (engine branch worlds-2005):
// Scott, Mr. Stone's Project, Battle Frontier (EX Emerald) and Rayquaza Star (EX Deoxys), and the
// Birds cards they meet in play (Zapdos ex, Moltres ex, Kangaskhan, Wobbuffet, Lanette's Net Search,
// EXP.ALL), against the EX-era Pokemon these cards were played against (Pidgeot, Mightyena, Slaking).
//
// Ground truth: every expected value is worked out beforehand from the printed text
// (pokemon-tcg-data ex1, ex2, ex6, ex8, ex9) and the era's rules, and written down with its reason;
// the engine then plays the situation out on a real game state (prompts, effects, knockouts and
// prizes through the store), the way the STS tests do (ryuu_sts_cards_tests.js).
//
// Run: node ryuu_2005_cards_tests.js <path-to-ryuu-play>   (or RYUU_PLAY=<path>)
'use strict';
const H = require('./ryuu_harness.js');
const {
  C, S, cm, test, report, newGame, P, O, put, bench, energy, hand, discard, take, play, attack, usePower, pass, err,
  target, PlayerType, SlotType, ChooseCardsPrompt, SelectPrompt,
} = H;

// ---------------------------------------------------------------- the 2005 card pool in this engine
const EX = S.exSets;
for (const k of ['setDeoxys', 'setEmerald']) {
  if (!EX[k]) { console.error('engine lacks exSets.' + k + ' (needs the worlds-2005 branch)'); process.exit(1); }
}
if (!cm.getAllFormats().some(f => f.name === 'EX 2005 (engine)')) {
  cm.defineFormat('EX 2005 (engine)',
    [EX.setRubyAndSapphire, EX.setSandstorm, EX.setFireredAndLeafgreen, EX.setDeoxys, EX.setEmerald]);
}

// A 60-card sandbox (at most 4 per name, one Pokemon Star): every card a test rigs onto the board.
const DECK_2005 = [
  ['Zapdos ex RG', 2], ['Moltres ex RG', 2], ['Kangaskhan RG', 2], ['Wobbuffet SS', 2], ['Rayquaza ★ DX', 1],
  ['Pidgey RG', 1], ['Pidgeotto RG', 1], ['Pidgeot RG', 2], ['Poochyena RS', 1], ['Mightyena RS', 1],
  ['Slakoth RS', 1], ['Vigoroth RS', 1], ['Slaking RS', 1],
  ['Scott EM', 2], ["Mr. Stone's Project EM", 2], ['Battle Frontier EM', 2], ["Lanette's Net Search SS", 2],
  ['Potion RS', 2], ['EXP.ALL RG', 2], ['Multi Energy SS', 2],
  ['Fire Energy RS', 10], ['Lightning Energy RS', 12], ['Psychic Energy RS', 6],
];
const unknown = DECK_2005.map(d => d[0]).filter(n => !cm.getCardByName(n));
if (unknown.length) { console.error('unknown card names:', unknown); process.exit(1); }
const game = arb => newGame(DECK_2005, DECK_2005, arb);

const BOARD = target(PlayerType.BOTTOM_PLAYER, SlotType.BOARD, 0);
const fullNames = cards => cards.map(c => c.fullName).sort().join(',');
// Open the first prompt of a card play and stop there (the harness would answer it).
function playUntilPrompt(sim, pl, name) {
  sim.dispatch(new C.PlayCardAction(pl.id, pl.hand.cards.findIndex(c => c.fullName === name), BOARD));
  return sim.store.state.prompts.find(p => p.result === undefined);
}
// Answer a ChooseCardsPrompt with named cards.
const pick = (...names) => p => H.cardsByNames(p, names);

// ================================================================ Scott (EM 84)
// "Search your deck for up to 3 cards in any combination of Supporter cards and Stadium cards ..."

test('SC1 only Supporters and Stadiums can be chosen',
  'blocked = every deck card that is not a Supporter or Stadium; max 3', 'max 3, offered: 7 Supporter/Stadium',
  () => {
    const sim = game(); const p = P(sim);
    hand(p, 'Scott EM');
    const pr = playUntilPrompt(sim, p, 'Scott EM');
    const offered = p.deck.cards.filter((c, i) => !pr.options.blocked.includes(i));
    const wrong = offered.filter(c => !(c instanceof C.TrainerCard) ||
      ![C.TrainerType.SUPPORTER, C.TrainerType.STADIUM].includes(c.trainerType));
    // the deck holds Scott x1 (the other is in hand), Mr. Stone's x2, Battle Frontier x2, Lanette's x2 = 7
    return 'max ' + pr.options.max + ', offered: ' + offered.length + (wrong.length ? ' WRONG ' + fullNames(wrong) : ' Supporter/Stadium');
  });

test('SC2 Scott takes a Stadium and two Supporters, shows them and shuffles',
  'hand gains exactly the 3 chosen cards; deck shrinks by 3; Scott sits in the Supporter zone',
  "Battle Frontier EM,Lanette's Net Search SS,Mr. Stone's Project EM | deck -3 | supporter Scott",
  () => {
    const sim = game(); const p = P(sim);
    hand(p, 'Scott EM'); const deck0 = p.deck.cards.length;
    play(sim, p, 'Scott EM', BOARD, { cards: pick('Battle Frontier EM', "Lanette's Net Search SS", "Mr. Stone's Project EM") });
    return fullNames(p.hand.cards) + ' | deck ' + (p.deck.cards.length - deck0) + ' | supporter ' + p.supporter.cards.map(c => c.name).join();
  });

test('SC3 a Potion is not a legal answer to Scott', 'Potion is an Item', false, () => {
  const sim = game(); const p = P(sim);
  hand(p, 'Scott EM');
  const pr = playUntilPrompt(sim, p, 'Scott EM');
  return pr.validate(pr.decode(H.cardsByNames(pr, ['Potion RS'])));
});

// ================================================================ Mr. Stone's Project (EM 79)
// "Search your deck for up to 2 Basic cards ... Shuffle your deck afterward. Or, search your discard
// pile for up to 2 Basic cards ..."  Basic cards = Basic Pokemon (Pokemon-ex included) and basic Energy.

test('MS1 from the deck: a Basic Pokemon-ex and a basic Energy; Stage 1, Multi Energy, Trainers blocked',
  'no Basic card in the discard pile, so no choice of zone; Zapdos ex is a Basic Pokemon',
  'offered only Basic Pokemon/basic Energy | hand Lightning Energy RS,Zapdos ex RG',
  () => {
    const sim = game(); const p = P(sim);
    hand(p, "Mr. Stone's Project EM"); p.discard.moveTo(p.deck);
    const pr = playUntilPrompt(sim, p, "Mr. Stone's Project EM");
    if (!(pr instanceof ChooseCardsPrompt)) return 'unexpected ' + pr.type;
    const offered = p.deck.cards.filter((c, i) => !pr.options.blocked.includes(i));
    const bad = offered.filter(c => !((c instanceof C.PokemonCard && c.stage === C.Stage.BASIC) ||
      (c instanceof C.EnergyCard && c.energyType === C.EnergyType.BASIC)));
    sim.dispatch(new C.ResolvePromptAction(pr.id, pr.decode(H.cardsByNames(pr, ['Zapdos ex RG', 'Lightning Energy RS']))));
    H.resolveAll(sim);
    return (bad.length ? 'offered ' + fullNames(bad) : 'offered only Basic Pokemon/basic Energy') + ' | hand ' + fullNames(p.hand.cards);
  });

test('MS2 from the discard pile: only the basic Energy is offered, deck order untouched',
  'discard: Lightning Energy, Multi Energy (special), Pidgeot (Stage 2), Potion; the discard branch does not shuffle',
  'Select, then offered Lightning Energy RS | hand Lightning Energy RS | deck unchanged',
  () => {
    const sim = game(); const p = P(sim);
    hand(p, "Mr. Stone's Project EM");
    discard(p, 'Lightning Energy RS', 'Multi Energy SS', 'Pidgeot RG', 'Potion RS');
    const order = p.deck.cards.map(c => c.id).join();
    const sel = playUntilPrompt(sim, p, "Mr. Stone's Project EM");
    if (!(sel instanceof SelectPrompt)) return 'no Select prompt: ' + sel.type;
    sim.dispatch(new C.ResolvePromptAction(sel.id, 1));       // the second option: the discard pile
    const pr = sim.store.state.prompts.find(x => x.result === undefined);
    const offered = pr.cards.cards.filter((c, i) => !pr.options.blocked.includes(i));
    H.resolveAll(sim, { cards: pick('Lightning Energy RS') });
    return 'Select, then offered ' + fullNames(offered) + ' | hand ' + fullNames(p.hand.cards)
      + ' | deck ' + (p.deck.cards.map(c => c.id).join() === order ? 'unchanged' : 'changed');
  });

test('MS3 not playable with an empty deck and no Basic card in the discard pile',
  'nothing it could do: the engine refuses the play (CANNOT_PLAY_THIS_CARD), the card stays in hand',
  'CANNOT_PLAY_THIS_CARD, in hand',
  () => {
    const sim = game(); const p = P(sim);
    hand(p, "Mr. Stone's Project EM");
    discard(p, 'Multi Energy SS', 'Potion RS', 'Pidgeot RG');
    p.deck.moveTo(p.prizes[0]);                                   // empty the deck
    const e = err(() => play(sim, p, "Mr. Stone's Project EM"));
    return e + ', ' + (p.hand.cards.some(c => c.name === "Mr. Stone's Project") ? 'in hand' : 'gone');
  });

// ================================================================ Lanette's Net Search (SS 87 = EM 77, same text)
test('LN1 Lanette\'s: up to 3 Basic Pokemon of different types',
  'Zapdos ex (Lightning) + Moltres ex (Fire) + Kangaskhan (Colorless) is legal; two Colorless Kangaskhan are not',
  'three types: true | Kangaskhan + Kangaskhan: false',
  () => {
    const sim = game(); const p = P(sim);
    hand(p, "Lanette's Net Search SS");
    const pr = playUntilPrompt(sim, p, "Lanette's Net Search SS");
    const ok = pr.validate(pr.decode(H.cardsByNames(pr, ['Zapdos ex RG', 'Moltres ex RG', 'Kangaskhan RG'])));
    const twoC = pr.validate(pr.decode(H.cardsByNames(pr, ['Kangaskhan RG', 'Kangaskhan RG'])));
    return 'three types: ' + ok + ' | Kangaskhan + Kangaskhan: ' + twoC;
  });

// ================================================================ Battle Frontier (EM 75)
// "Each player's Colorless Evolved Pokemon, Darkness Evolved Pokemon, and Metal Evolved Pokemon can't
// use any Poke-Powers or Poke-Bodies."
const stadium = (pl, name) => pl.deck.moveCardTo(take(pl, name), pl.stadium);
const pidgeot = pl => put(pl, pl.bench[0], 'Pidgey RG', 'Pidgeotto RG', 'Pidgeot RG');
function quickSearch(sim, pl) {
  const before = pl.hand.cards.length;
  const e = err(() => usePower(sim, pl, pl.bench[0], 'Quick Search', { cards: pick('Potion RS') }));
  return (e || 'used') + ', hand ' + (pl.hand.cards.length - before >= 0 ? '+' : '') + (pl.hand.cards.length - before);
}

test('BF1 Quick Search (Pidgeot: Colorless Stage 2 Poke-Power) works without Battle Frontier',
  'Quick Search: put any 1 card from the deck into the hand', 'used, hand +1', () => {
    const sim = game(); const p = P(sim);
    hand(p); pidgeot(p);
    return quickSearch(sim, p);
  });

test('BF1b ... and is stopped by its owner\'s own Battle Frontier',
  '"Each player\'s" Colorless Evolved Pokemon: the Stadium\'s owner is affected too', 'BLOCKED_BY_EFFECT, hand +0', () => {
    const sim = game(); const p = P(sim);
    hand(p); pidgeot(p); stadium(p, 'Battle Frontier EM');
    return quickSearch(sim, p);
  });

function headbuttMightyena(withFrontier) {
  const sim = game(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Kangaskhan RG'); energy(p, p.active, 'Fire Energy RS', 'Fire Energy RS');
  put(o, o.active, 'Poochyena RS', 'Mightyena RS');
  if (withFrontier) stadium(o, 'Battle Frontier EM');
  attack(sim, p, 'Headbutt');
  return o.active.damage;
}
test('BF2 Intimidating Fang (Mightyena: Darkness Stage 1 Poke-Body) cuts Headbutt 20 to 10',
  'Kangaskhan (Colorless) vs Mightyena (Fighting Weakness, Psychic Resistance): 20 - 10', 10, () => headbuttMightyena(false));
test('BF2b ... and Battle Frontier turns the Poke-Body off: the full 20',
  'Mightyena is a Darkness Evolved Pokemon', 20, () => headbuttMightyena(true));

function benchZapdosAgainstSlaking(withFrontier) {
  const sim = game(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Kangaskhan RG');
  for (const s of p.bench) H.clearSlot(p, s);
  hand(p, 'Zapdos ex RG');
  put(o, o.active, 'Slakoth RS', 'Vigoroth RS', 'Slaking RS');
  if (withFrontier) stadium(o, 'Battle Frontier EM');
  play(sim, p, 'Zapdos ex RG', target(PlayerType.BOTTOM_PLAYER, SlotType.BENCH, 0));
  return p.active.getPokemonCard().fullName;
}
test('BF3 Lazy (opponent\'s Active Slaking) stops Zapdos ex\'s Legendary Ascent',
  'Lazy: the opponent\'s Pokemon can\'t use Poke-Powers; Zapdos ex stays on the Bench', 'Kangaskhan RG', () => benchZapdosAgainstSlaking(false));
test('BF3b ... and Battle Frontier turns Lazy off, so Zapdos ex (Basic, untouched) switches in',
  'Slaking is a Colorless Evolved Pokemon; Legendary Ascent switches Zapdos ex with the Active', 'Zapdos ex RG', () => benchZapdosAgainstSlaking(true));

test('BF4 Battle Frontier leaves Wobbuffet\'s Safeguard on (Wobbuffet is a Basic)',
  'Safeguard prevents all damage from the opponent\'s Pokemon-ex; Electron Crush does 0', 0, () => {
    const sim = game(); const p = P(sim), o = O(sim);
    put(p, p.active, 'Zapdos ex RG'); energy(p, p.active, 'Lightning Energy RS', 'Lightning Energy RS', 'Lightning Energy RS');
    put(o, o.active, 'Wobbuffet SS'); stadium(o, 'Battle Frontier EM');
    attack(sim, p, 'Electron Crush');
    return o.active.damage;
  });

test('BF5 your own Active Slaking does not stop your own Quick Search',
  'Lazy only stops the OPPONENT\'s Pokemon (printed text)', 'used, hand +1', () => {
    const sim = game(); const p = P(sim);
    hand(p); pidgeot(p); put(p, p.active, 'Slakoth RS', 'Vigoroth RS', 'Slaking RS');
    return quickSearch(sim, p);
  });

// ================================================================ Rayquaza Star (DX 107)
// Spiral Rush [F L] 30x: flip until tails, 30 x heads. Holy Star [F F L L]: discard all Energy attached
// to Rayquaza Star; 100 damage to each of the opponent's Pokemon-ex (W/R not for Benched Pokemon).
// Pokemon-ex rule: when a Pokemon-ex is Knocked Out, the opponent takes 2 Prize cards.
function flips(sim, results) {
  sim.setBotArbiter(new C.BotArbiter({ flipMode: C.BotFlipMode.CUSTOM, shuffleMode: C.BotShuffleMode.NO_SHUFFLE, flipResults: results }));
}
function rayquaza(sim, ...energies) {
  const p = P(sim);
  put(p, p.active, 'Rayquaza ★ DX'); energy(p, p.active, ...energies);
}
// Attack, answering Prize prompts with the first `count` non-empty Prize piles (face down: no choice).
function attackTakingPrizes(sim, pl, name) {
  sim.dispatch(new C.AttackAction(pl.id, name));
  for (let guard = 0; guard < 20; guard++) {
    const pr = sim.store.state.prompts.find(x => x.result === undefined);
    if (!pr) return;
    if (pr instanceof H.ChoosePrizePrompt) {
      const owner = sim.store.state.players.find(x => x.id === pr.playerId);
      const piles = owner.prizes.filter(z => z.cards.length > 0).slice(0, pr.options.count);
      sim.dispatch(new C.ResolvePromptAction(pr.id, piles));
    } else {
      H.resolveAll(sim);
    }
  }
}

test('RQ1 Spiral Rush: heads, heads, heads, tails = 90',
  'Colorless attacker vs Zapdos ex (Lightning Weakness): no Weakness applies', 90, () => {
    const sim = game(); const o = O(sim);
    rayquaza(sim, 'Fire Energy RS', 'Lightning Energy RS');
    put(o, o.active, 'Zapdos ex RG');
    flips(sim, [true, true, true, false]);
    attack(sim, P(sim), 'Spiral Rush');
    return o.active.damage;
  });

test('RQ2 Spiral Rush: tails first = 0', 'zero heads', 0, () => {
  const sim = game(); const o = O(sim);
  rayquaza(sim, 'Fire Energy RS', 'Lightning Energy RS');
  put(o, o.active, 'Zapdos ex RG');
  flips(sim, [false]);
  attack(sim, P(sim), 'Spiral Rush');
  return o.active.damage;
});

test('RQ3 Holy Star: 100 to each opposing Pokemon-ex only; all 4 Energy discarded',
  'active Zapdos ex, Bench Moltres ex / Kangaskhan / Wobbuffet (Safeguard is moot: Rayquaza Star is not ex)',
  'active 100, bench 100,0,0 | energy left 0 | discarded 4 Energy',
  () => {
    const sim = game(); const p = P(sim), o = O(sim);
    rayquaza(sim, 'Fire Energy RS', 'Fire Energy RS', 'Lightning Energy RS', 'Lightning Energy RS');
    p.discard.moveTo(p.deck);
    put(o, o.active, 'Zapdos ex RG');
    for (const s of o.bench) H.clearSlot(o, s);
    bench(o, 0, 'Moltres ex RG'); bench(o, 1, 'Kangaskhan RG'); bench(o, 2, 'Wobbuffet SS');
    attack(sim, p, 'Holy Star');
    return 'active ' + o.active.damage + ', bench ' + o.bench.slice(0, 3).map(s => s.damage).join(',')
      + ' | energy left ' + p.active.energies.cards.length
      + ' | discarded ' + p.discard.cards.filter(c => c instanceof C.EnergyCard).length + ' Energy';
  });

test('RQ4 Holy Star knocks out a damaged Benched Moltres ex: 2 Prize cards',
  'Moltres ex 110 HP with 10 damage + 100 = KO; Pokemon-ex rule gives 2 Prizes; non-ex Active takes 0',
  'Moltres ex KO (in discard) | prizes taken 2 | active 0',
  () => {
    const sim = game(); const p = P(sim), o = O(sim);
    rayquaza(sim, 'Fire Energy RS', 'Fire Energy RS', 'Lightning Energy RS', 'Lightning Energy RS');
    put(o, o.active, 'Kangaskhan RG');
    for (const s of o.bench) H.clearSlot(o, s);
    bench(o, 0, 'Moltres ex RG'); o.bench[0].damage = 10;
    const prizes0 = p.prizes.filter(z => z.cards.length > 0).length;
    attackTakingPrizes(sim, p, 'Holy Star');
    const ko = o.bench[0].pokemons.cards.length === 0 && o.discard.cards.some(c => c.fullName === 'Moltres ex RG');
    return 'Moltres ex ' + (ko ? 'KO (in discard)' : 'not KO, damage ' + o.bench[0].damage)
      + ' | prizes taken ' + (prizes0 - p.prizes.filter(z => z.cards.length > 0).length) + ' | active ' + o.active.damage;
  });

// ================================================================ EXP.ALL (RG 91)
// "Attach EXP.ALL to 1 of your Pokemon (excluding Pokemon-ex ...). During your opponent's turn, if 1 of
// your Active Pokemon is Knocked Out by your opponent's attack, you may take 1 basic Energy card
// attached to that Knocked Out Pokemon and attach it to the Pokemon with EXP.ALL. If you do, discard EXP.ALL."
test('EX1 EXP.ALL cannot be attached to a Pokemon-ex, but can to Kangaskhan',
  'printed exclusion of Pokemon-ex', 'Zapdos ex: refused | Kangaskhan: attached', () => {
    const sim = game(); const p = P(sim);
    put(p, p.active, 'Zapdos ex RG'); for (const s of p.bench) H.clearSlot(p, s); bench(p, 0, 'Kangaskhan RG');
    hand(p, 'EXP.ALL RG', 'EXP.ALL RG');
    const e = err(() => play(sim, p, 'EXP.ALL RG', target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0)));
    const onEx = e ? 'refused' : 'attached';
    const p2 = P(sim);                // a refused action restores the store's backup: a new state object
    const e2 = err(() => play(sim, p2, 'EXP.ALL RG', target(PlayerType.BOTTOM_PLAYER, SlotType.BENCH, 0)));
    return 'Zapdos ex: ' + onEx + ' | Kangaskhan: ' + (e2 ? 'refused ' + e2 : p2.bench[0].trainers.cards.length ? 'attached' : 'missing');
  });

test('EX2 Active Zapdos ex knocked out on the opponent\'s turn: 1 Lightning Energy moves to the EXP.ALL holder',
  'EXP.ALL on Benched Kangaskhan; Zapdos ex (110 HP, 100 damage, 2 Lightning) KO\'d by Headbutt 20; EXP.ALL discarded; '
  + 'the attacker takes 2 Prizes (Pokemon-ex)',
  'Kangaskhan has 1 Lightning Energy, EXP.ALL discarded | opponent took 2 Prizes | Zapdos ex and 1 Energy in discard',
  () => {
    const sim = game(); const p = P(sim), o = O(sim);
    put(p, p.active, 'Zapdos ex RG'); energy(p, p.active, 'Lightning Energy RS', 'Lightning Energy RS'); p.active.damage = 100;
    for (const s of p.bench) H.clearSlot(p, s); bench(p, 0, 'Kangaskhan RG');
    p.deck.moveCardTo(take(p, 'EXP.ALL RG'), p.bench[0].trainers);
    put(o, o.active, 'Kangaskhan RG'); energy(o, o.active, 'Fire Energy RS', 'Fire Energy RS');
    pass(sim, p);
    const oPrizes0 = o.prizes.filter(z => z.cards.length > 0).length;
    sim.dispatch(new C.AttackAction(o.id, 'Headbutt'));
    for (let guard = 0; guard < 20; guard++) {
      const pr = sim.store.state.prompts.find(x => x.result === undefined);
      if (!pr) break;
      let r;
      if (pr instanceof H.ChoosePrizePrompt) {
        const owner = sim.store.state.players.find(x => x.id === pr.playerId);
        r = owner.prizes.filter(z => z.cards.length > 0).slice(0, pr.options.count);
      } else if (pr instanceof H.AttachEnergyPrompt) {
        r = [{ to: target(PlayerType.BOTTOM_PLAYER, SlotType.BENCH, 0), index: 0 }];
        r = pr.decode(r, sim.store.state);
      } else if (pr instanceof H.ChoosePokemonPrompt) {
        r = pr.decode([target(PlayerType.BOTTOM_PLAYER, SlotType.BENCH, 0)], sim.store.state);
      } else {
        r = pr.decode(true, sim.store.state);
      }
      if (!pr.validate(r, sim.store.state)) throw new Error('invalid answer to ' + pr.type);
      sim.dispatch(new C.ResolvePromptAction(pr.id, r));
    }
    const kang = [p.active, ...p.bench].find(s => s.getPokemonCard() && s.getPokemonCard().name === 'Kangaskhan');
    const lightning = kang.energies.cards.filter(c => c.name === 'Lightning Energy').length;
    const expDiscarded = p.discard.cards.some(c => c.name === 'EXP.ALL') && kang.trainers.cards.length === 0;
    const taken = oPrizes0 - o.prizes.filter(z => z.cards.length > 0).length;
    return 'Kangaskhan has ' + lightning + ' Lightning Energy, EXP.ALL ' + (expDiscarded ? 'discarded' : 'kept')
      + ' | opponent took ' + taken + ' Prizes | ' + (p.discard.cards.some(c => c.fullName === 'Zapdos ex RG') ? 'Zapdos ex' : 'no Zapdos ex')
      + ' and ' + p.discard.cards.filter(c => c.name === 'Lightning Energy').length + ' Energy in discard';
  });

// ================================================================ the Birds attackers (RG 116, 115, 6; SS 26)
// All against Kangaskhan (Colorless, Fighting Weakness, 80 HP), so no Weakness or Resistance applies.
function birdsAttack(attacker, energies, name, h) {
  const sim = game(); const p = P(sim), o = O(sim);
  put(p, p.active, attacker); energy(p, p.active, ...energies);
  put(o, o.active, 'Kangaskhan RG');
  const hand0 = p.hand.cards.length, discard0 = p.discard.cards.length;
  attack(sim, p, name, h);
  return { p, o, drew: p.hand.cards.length - hand0, discarded: p.discard.cards.length - discard0 };
}
const L3 = ['Lightning Energy RS', 'Lightning Energy RS', 'Lightning Energy RS'];
const F3 = ['Fire Energy RS', 'Fire Energy RS', 'Fire Energy RS'];

test('ZE1 Electron Crush, discarding an Energy: 50 + 20', '"You may discard an Energy card ... 50 damage plus 20 more"',
  '70, discarded 1', () => {
    const r = birdsAttack('Zapdos ex RG', L3, 'Electron Crush', { cards: p => [0] });
    return r.o.active.damage + ', discarded ' + r.discarded;
  });
test('ZE2 Electron Crush, keeping the Energy: 50', 'the discard is optional', '50, discarded 0', () => {
  const r = birdsAttack('Zapdos ex RG', L3, 'Electron Crush', { cards: p => null });
  return r.o.active.damage + ', discarded ' + r.discarded;
});
test('MO1 Crushing Flames, discarding an Energy: 60 and Confused', '"If you do, the Defending Pokemon is now Confused"',
  '60, CONFUSED, discarded 1', () => {
    const r = birdsAttack('Moltres ex RG', F3, 'Crushing Flames', { cards: p => [0] });
    return r.o.active.damage + ', ' + r.o.active.specialConditions.map(c => H.SpecialCondition[c]).join() + ', discarded ' + r.discarded;
  });
test('MO2 Crushing Flames, keeping the Energy: 60, no Special Condition', 'the discard is optional',
  '60, none, discarded 0', () => {
    const r = birdsAttack('Moltres ex RG', F3, 'Crushing Flames', { cards: p => null });
    return r.o.active.damage + ', ' + (r.o.active.specialConditions.length ? r.o.active.specialConditions.join() : 'none') + ', discarded ' + r.discarded;
  });
test('KA1 Kangaskhan Fetch: draw a card, no damage', '"Draw a card."', 'drew 1, damage 0', () => {
  const r = birdsAttack('Kangaskhan RG', ['Fire Energy RS'], 'Fetch');
  return 'drew ' + r.drew + ', damage ' + r.o.active.damage;
});
test('WO1 Wobbuffet Flip Over: 50 to the Defending Pokemon, 10 to itself',
  '"Wobbuffet does 10 damage to itself" (no W/R on the self-damage)', '50 / self 10', () => {
    const r = birdsAttack('Wobbuffet SS', ['Psychic Energy RS', 'Fire Energy RS', 'Fire Energy RS'], 'Flip Over');
    return r.o.active.damage + ' / self ' + r.p.active.damage;
  });

const ok = report("Worlds 2005 'Birds' cards: behaviour against printed text and rulings");
process.exitCode = ok ? 0 : 1;
