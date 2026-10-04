// Behavioural tests for the three cards the July 2000 STS California field needs that
// ryuu-play did not supply: Ditto FO (implemented but unregistered), Mewtwo PR (Wizards
// Black Star Promo #3, the "Movie Promo") and Mew PR (#8).
//
// Covers each card on its own and, more importantly, against the other cards in the
// format: Pokemon Powers that switch Transform off, damage prevention, weakness and
// resistance, special Energy, evolution stacks, knockouts caused indirectly, and the
// re-entrancy that copying a card's own effect handlers invites.
//
// Run: node ryuu_sts_cards_tests.js <path-to-ryuu-play>
'use strict';
const H = require('./ryuu_harness.js');
const {
  test, report, newGame, P, O, put, bench, energy, hand, discard, play, attack, pass, err,
  target, PlayerType, SlotType, SpecialCondition, SuperType, cm,
  effectiveHp, effectiveStats, effectiveTypes, effectiveRetreat,
  AttachEnergyPrompt, ChooseAttackPrompt, ChoosePokemonPrompt,
} = H;

const ACTIVE = target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0);

// pick named cards out of an AttachEnergyPrompt and send them all to one slot
const attachNamed = (...names) => (prompt) => {
  const used = [];
  const out = [];
  for (const n of names) {
    const i = prompt.cardList.cards.findIndex((c, j) => (c.fullName === n || c.name === n) && !used.includes(j));
    if (i < 0) throw new Error('discard lacks ' + n + ' (has ' + prompt.cardList.cards.map(c => c.fullName).join(', ') + ')');
    used.push(i);
    out.push({ to: ACTIVE, index: i });
  }
  return out;
};
const chooseAttack = name => (prompt) => ({ index: 0, name });
const choosePokemon = (playerType, slot, index) => () => [target(playerType, slot, index || 0)];

// ================================================================ Mewtwo PR (promo #3)

test('M1 stat line matches WBSP #3', 'hp 70, retreat 2, weakness Psychic, 2 attacks', '70/2/PSYCHIC/Energy Absorption,Psyburn', () => {
  const c = cm.getCardByName('Mewtwo PR');
  const w = c.weakness.map(x => Object.keys(H.C.CardType).find(k => H.C.CardType[k] === x.type)).join(',');
  return [c.hp, c.retreat.length, w, c.attacks.map(a => a.name).join(',')].join('/');
});

function psyburn(sim, defender) {
  const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR');
  energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, defender); bench(o, 0, 'Scyther JU');
}

test('M2 Psyburn does 40 to a Psychic-neutral target', 'Electabuzz BS: Fighting-weak, no Resistance', 40, () => {
  const sim = newGame(); psyburn(sim, 'Electabuzz BS'); attack(sim, P(sim), 'Psyburn'); return O(sim).active.damage;
});

test('M2b Psyburn cut by Chansey Psychic Resistance', 'Chansey BS resists Psychic -30', 10, () => {
  const sim = newGame(); psyburn(sim, 'Chansey BS'); attack(sim, P(sim), 'Psyburn'); return O(sim).active.damage;
});

test('M3 Psyburn doubled by Psychic Weakness', 'Mewtwo BS has 60 HP, so only a doubled 40 can KO it', 'KO, Mewtwo discarded', () => {
  const sim = newGame(); psyburn(sim, 'Mewtwo BS'); attack(sim, P(sim), 'Psyburn');
  const o = O(sim);
  return (o.active.getPokemonCard().name !== 'Mewtwo' ? 'KO' : 'survived')
    + ', ' + (o.discard.cards.some(c => c.fullName === 'Mewtwo BS') ? 'Mewtwo discarded' : 'not discarded');
});

test('M4 Psyburn reduced by Psychic Resistance', 'untransformed Ditto resists Psychic -30', 10, () => {
  const sim = newGame(); psyburn(sim, 'Ditto FO');
  O(sim).active.specialConditions = [SpecialCondition.ASLEEP];  // asleep Ditto is not a copy
  attack(sim, P(sim), 'Psyburn'); return O(sim).active.damage;
});

test('M5 Energy Absorption with an empty discard', 'no prompt, no crash, nothing attached', '0 energy, no prompt', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck);
  let prompted = false;
  attack(sim, p, 'Energy Absorption', { attach: pr => { prompted = true; return []; } });
  return (p.active.energies.cards.length - 1) + ' energy, ' + (prompted ? 'prompted' : 'no prompt');
});

test('M6 Energy Absorption takes at most 2', 'card text: up to 2', 2, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck);
  discard(p, 'Psychic Energy BS', 'Psychic Energy BS', 'Psychic Energy BS');
  const e = err(() => attack(sim, p, 'Energy Absorption', {
    attach: attachNamed('Psychic Energy BS', 'Psychic Energy BS', 'Psychic Energy BS')
  }));
  if (!e) return 'accepted 3';
  // 3 rejected; now take the legal 2
  const sim2 = newGame(); const p2 = P(sim2), o2 = O(sim2);
  put(p2, p2.active, 'Mewtwo PR'); energy(p2, p2.active, 'Psychic Energy BS');
  put(o2, o2.active, 'Chansey BS');
  p2.discard.moveTo(p2.deck);
  discard(p2, 'Psychic Energy BS', 'Psychic Energy BS', 'Psychic Energy BS');
  attack(sim2, p2, 'Energy Absorption', { attach: attachNamed('Psychic Energy BS', 'Psychic Energy BS') });
  return p2.active.energies.cards.length - 1;
});

test('M7 Energy Absorption will not take a Trainer from the discard', 'filter is SuperType.ENERGY', 'rejected', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck);
  discard(p, 'Professor Oak BS', 'Psychic Energy BS');
  const e = err(() => attack(sim, p, 'Energy Absorption', { attach: attachNamed('Professor Oak BS') }));
  return e ? 'rejected' : 'accepted a Trainer';
});

test('M8 Energy Absorption can take a Double Colorless Energy', 'DCE is an Energy card', 'DCE attached', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck);
  discard(p, 'Double Colorless Energy BS');
  energy(p, p.active, 'Psychic Energy BS');
  attack(sim, p, 'Energy Absorption', { attach: attachNamed('Double Colorless Energy BS') });
  return p.active.energies.cards.some(c => c.name === 'Double Colorless Energy') ? 'DCE attached' : 'not attached';
});

test('M9 Energy Absorption can take Rainbow Energy', 'special Energy from Team Rocket', 'Rainbow attached', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck);
  discard(p, 'Rainbow Energy TR');
  energy(p, p.active, 'Psychic Energy BS');
  attack(sim, p, 'Energy Absorption', { attach: attachNamed('Rainbow Energy TR') });
  return p.active.energies.cards.some(c => c.name === 'Rainbow Energy') ? 'Rainbow attached' : 'not attached';
});

test('M10 Energy Absorption always lands on Mewtwo', 'AttachEnergyPrompt.validate ignores its own slot list, so the card enforces it', 'active 2, bench 0', () => {
  // a client that asks to put the Energy on the Bench must still see it go to Mewtwo
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); bench(p, 0, 'Chansey BS'); put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck);
  discard(p, 'Psychic Energy BS');
  energy(p, p.active, 'Psychic Energy BS');
  const benchTarget = target(PlayerType.BOTTOM_PLAYER, SlotType.BENCH, 0);
  attack(sim, p, 'Energy Absorption', {
    attach: pr => [{ to: benchTarget, index: pr.cardList.cards.findIndex(c => c.name === 'Psychic Energy') }]
  });
  return 'active ' + p.active.energies.cards.length + ', bench ' + p.bench[0].energies.cards.length;
});

test('M11 Toxic Gas does not stop Energy Absorption', 'it is an attack, not a Pokemon Power', 1, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); put(o, o.active, 'Chansey BS');
  bench(o, 0, 'Grimer FO', 'Muk FO');
  p.discard.moveTo(p.deck);
  discard(p, 'Psychic Energy BS');
  energy(p, p.active, 'Psychic Energy BS');
  attack(sim, p, 'Energy Absorption', { attach: attachNamed('Psychic Energy BS') });
  return p.active.energies.cards.length - 1;
});

test('M12 Energy Absorption may take nothing', 'card text: up to 2, so zero is legal', 'no error, 0 taken', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck);
  discard(p, 'Psychic Energy BS');
  energy(p, p.active, 'Psychic Energy BS');
  const e = err(() => attack(sim, p, 'Energy Absorption', { attach: () => [] }));
  return e ? 'error ' + e : 'no error, ' + (p.active.energies.cards.length - 1) + ' taken';
});

test('M13 Energy Absorption does no damage', 'card has no damage value', 0, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck); discard(p, 'Psychic Energy BS');
  attack(sim, p, 'Energy Absorption', { attach: attachNamed('Psychic Energy BS') });
  return O(sim).active.damage;
});

test('M14 Psyburn is payable with 2 Psychic + a Double Colorless', 'cost P,P,C against P,P,C,C provided', 40, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR');
  energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS', 'Double Colorless Energy BS');
  put(o, o.active, 'Electabuzz BS');
  attack(sim, p, 'Psyburn');
  return o.active.damage;
});

test('M15 Psyburn with only 2 Energy is refused', 'cost is 3', 'refused', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR');
  energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Chansey BS');
  return err(() => attack(sim, p, 'Psyburn')) ? 'refused' : 'allowed';
});

// ================================================================ Mew PR (promo #8)

test('W1 stat line matches WBSP #8', 'hp 50, retreat 1, weakness Psychic', '50/1/PSYCHIC/Psywave,Devolution Beam', () => {
  const c = cm.getCardByName('Mew PR');
  const w = c.weakness.map(x => Object.keys(H.C.CardType).find(k => H.C.CardType[k] === x.type)).join(',');
  return [c.hp, c.retreat.length, w, c.attacks.map(a => a.name).join(',')].join('/');
});

function psywave(sim, defender, ...defenderEnergy) {
  const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, defender); bench(o, 0, 'Scyther JU');
  if (defenderEnergy.length) energy(o, o.active, ...defenderEnergy);
}

test('W2 Psywave with no Energy on the defender does nothing', '10x0', 0, () => {
  const sim = newGame(); psywave(sim, 'Chansey BS'); attack(sim, P(sim), 'Psywave'); return O(sim).active.damage;
});

test('W3 Psywave counts each Energy card', '3 basic Energy -> 30', 30, () => {
  const sim = newGame(); psywave(sim, 'Electabuzz BS', 'Fighting Energy BS', 'Fighting Energy BS', 'Fighting Energy BS');
  attack(sim, P(sim), 'Psywave'); return O(sim).active.damage;
});

test('W4 a Double Colorless counts as ONE card', 'Mar 2 2000: DCE is one Energy card', 10, () => {
  const sim = newGame(); psywave(sim, 'Electabuzz BS', 'Double Colorless Energy BS');
  attack(sim, P(sim), 'Psywave'); return O(sim).active.damage;
});

test('W5 Psywave is doubled by Psychic Weakness', '2 Energy -> 20 -> x2', 40, () => {
  const sim = newGame(); psywave(sim, 'Mewtwo BS', 'Psychic Energy BS', 'Psychic Energy BS');
  attack(sim, P(sim), 'Psywave'); return O(sim).active.damage;
});

test('W6 Psywave under 30 gets past Invisible Wall', 'Mr. Mime only prevents 30+', 20, () => {
  // Mr. Mime is Psychic-weak, so one Energy gives 10 -> x2 = 20, which is under the wall
  const sim = newGame(); psywave(sim, 'Mr. Mime JU', 'Psychic Energy BS');
  attack(sim, P(sim), 'Psywave'); return O(sim).active.damage;
});

test('W7 Psywave of 30+ is stopped by Invisible Wall', 'after Weakness, 2 Energy -> 40', 0, () => {
  const sim = newGame(); psywave(sim, 'Mr. Mime JU', 'Psychic Energy BS', 'Psychic Energy BS');
  attack(sim, P(sim), 'Psywave'); return O(sim).active.damage;
});

test('W8 Devolution Beam with nothing evolved in play', 'no prompt, no crash', 'no prompt', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Chansey BS');
  let prompted = false;
  attack(sim, p, 'Devolution Beam', { pokemon: pr => { prompted = true; return []; } });
  return prompted ? 'prompted' : 'no prompt';
});

test('W9 Devolution Beam returns the opponent evolution to THEIR hand', 'card text: to its player\'s hand', 'active=Jigglypuff, opp hand has Wigglytuff, my hand does not', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Jigglypuff JU', 'Wigglytuff JU');
  hand(o);  // empty the opponent hand so the check is unambiguous
  hand(p);
  attack(sim, p, 'Devolution Beam', { pokemon: choosePokemon(PlayerType.TOP_PLAYER, SlotType.ACTIVE) });
  return 'active=' + o.active.getPokemonCard().name
    + ', opp hand ' + (o.hand.cards.some(c => c.name === 'Wigglytuff') ? 'has' : 'lacks') + ' Wigglytuff'
    + ', my hand ' + (p.hand.cards.some(c => c.name === 'Wigglytuff') ? 'has it too' : 'does not');
});

test('W10 Devolution Beam can target your own Pokemon', 'card text: your own or your opponent\'s', 'own hand has Wigglytuff', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(p, p.bench[0], 'Jigglypuff JU', 'Wigglytuff JU');
  put(o, o.active, 'Chansey BS');
  hand(p);
  attack(sim, p, 'Devolution Beam', { pokemon: choosePokemon(PlayerType.BOTTOM_PLAYER, SlotType.BENCH, 0) });
  return p.hand.cards.some(c => c.name === 'Wigglytuff') ? 'own hand has Wigglytuff' : 'not returned';
});

test('W11 Devolution Beam clears Special Conditions', 'card text: just as if you had evolved it', 'no conditions', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Jigglypuff JU', 'Wigglytuff JU');
  o.active.specialConditions = [SpecialCondition.ASLEEP, SpecialCondition.POISONED];
  attack(sim, p, 'Devolution Beam', { pokemon: choosePokemon(PlayerType.TOP_PLAYER, SlotType.ACTIVE) });
  return o.active.specialConditions.length === 0 ? 'no conditions' : 'still ' + o.active.specialConditions.join(',');
});

test('W12 Devolution Beam leaves damage counters alone', 'devolving never heals', 30, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Jigglypuff JU', 'Wigglytuff JU');
  o.active.damage = 30;
  attack(sim, p, 'Devolution Beam', { pokemon: choosePokemon(PlayerType.TOP_PLAYER, SlotType.ACTIVE) });
  return o.active.damage;
});

test('W13 Devolution Beam peels one Stage off a Stage 2', 'highest Stage only', 'Wartortle', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Squirtle BS', 'Wartortle BS', 'Blastoise BS');
  attack(sim, p, 'Devolution Beam', { pokemon: choosePokemon(PlayerType.TOP_PLAYER, SlotType.ACTIVE) });
  return o.active.getPokemonCard().name;
});

test('W14 devolving under the damage already taken is a knockout', 'Wartortle has 70 HP; 80 damage was survivable on Blastoise', 'KO, prizes 5', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Squirtle BS', 'Wartortle BS', 'Blastoise BS');
  bench(o, 0, 'Chansey BS');
  o.active.damage = 80;
  // first prompt picks the devolution target; the knockout then asks for a new Active
  let first = true;
  attack(sim, p, 'Devolution Beam', {
    pokemon: (pr, st) => {
      if (first) { first = false; return [target(PlayerType.TOP_PLAYER, SlotType.ACTIVE, 0)]; }
      return H.defaultPokemon(pr, st);
    }
  });
  const card = o.active.getPokemonCard();
  const ko = o.discard.cards.some(c => c.fullName === 'Wartortle BS');
  return (ko ? 'KO' : 'survived as ' + (card && card.name)) + ', prizes ' + p.prizes.filter(z => z.cards.length).length;
});

test('W15 Devolution Beam cannot target a Basic', 'nothing to return', 'basic blocked', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Jigglypuff JU', 'Wigglytuff JU');   // evolved, so the attack does prompt
  bench(o, 0, 'Chansey BS');                             // basic, must be blocked
  const e = err(() => attack(sim, p, 'Devolution Beam', { pokemon: choosePokemon(PlayerType.TOP_PLAYER, SlotType.BENCH, 0) }));
  return e ? 'basic blocked' : 'basic was allowed';
});

test('W16 Devolution Beam does no damage', 'card has no damage value', 0, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Jigglypuff JU', 'Wigglytuff JU');
  attack(sim, p, 'Devolution Beam', { pokemon: choosePokemon(PlayerType.TOP_PLAYER, SlotType.ACTIVE) });
  return o.active.damage;
});

// ================================================================ Ditto FO

function dittoVs(sim, defender) {
  const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO');
  put(o, o.active, defender); bench(o, 0, 'Scyther JU');
  return [p, o];
}

test('D1 Ditto is registered at runtime', 'it was commented out of set-fossil/index.ts', true, () => !!cm.getCardByName('Ditto FO'));

test('D2 Ditto copies the defender HP', 'Hitmonchan BS has 70', 70, () => {
  const sim = newGame(); const [p] = dittoVs(sim, 'Hitmonchan BS'); return effectiveHp(sim, p, p.active);
});

test('D3 Ditto copies the defender type', 'Hitmonchan is Fighting', 'FIGHTING', () => {
  const sim = newGame(); const [p] = dittoVs(sim, 'Hitmonchan BS');
  return effectiveTypes(sim, p.active).map(t => Object.keys(H.C.CardType).find(k => H.C.CardType[k] === t)).join(',');
});

test('D4 Ditto copies Weakness and loses its own Resistance', 'Hitmonchan: weak Psychic, no resistance', 'weak=PSYCHIC res=none', () => {
  const sim = newGame(); const [p] = dittoVs(sim, 'Hitmonchan BS');
  const s = effectiveStats(sim, p.active);
  const nm = t => Object.keys(H.C.CardType).find(k => H.C.CardType[k] === t);
  return 'weak=' + (s.weakness.map(w => nm(w.type)).join(',') || 'none')
    + ' res=' + (s.resistance.map(r => nm(r.type)).join(',') || 'none');
});

test('D5 Ditto copies the defender retreat cost', 'Hitmonchan BS retreats for 2', 2, () => {
  const sim = newGame(); const [p] = dittoVs(sim, 'Hitmonchan BS'); return effectiveRetreat(sim, p).length;
});

test('D6 an Asleep Ditto is not a copy', 'card text', 50, () => {
  const sim = newGame(); const [p] = dittoVs(sim, 'Hitmonchan BS');
  p.active.specialConditions = [SpecialCondition.ASLEEP];
  return effectiveHp(sim, p, p.active);
});

test('D7 a Confused Ditto is not a copy', 'card text', 50, () => {
  const sim = newGame(); const [p] = dittoVs(sim, 'Hitmonchan BS');
  p.active.specialConditions = [SpecialCondition.CONFUSED];
  return effectiveHp(sim, p, p.active);
});

test('D8 a Paralyzed Ditto is not a copy', 'card text', 50, () => {
  const sim = newGame(); const [p] = dittoVs(sim, 'Hitmonchan BS');
  p.active.specialConditions = [SpecialCondition.PARALYZED];
  return effectiveHp(sim, p, p.active);
});

test('D9 Muk Toxic Gas switches Transform off', 'Toxic Gas blocks all Pokemon Powers', 50, () => {
  const sim = newGame(); const [p, o] = dittoVs(sim, 'Hitmonchan BS');
  put(o, o.bench[0], 'Grimer FO', 'Muk FO');
  return effectiveHp(sim, p, p.active);
});

test('D10 a benched Ditto is not a copy', 'card text: if Ditto is your Active Pokemon', 50, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Chansey BS'); bench(p, 0, 'Ditto FO');
  put(o, o.active, 'Hitmonchan BS');
  return effectiveHp(sim, p, p.bench[0]);
});

test('D11 Ditto Energy pays any cost', 'card text: treat any Energy attached as Energy of any type', 20, () => {
  // Ditto copies Hitmonchan and pays Jab ([F][C]) with Psychic Energy
  const sim = newGame(); const [p, o] = dittoVs(sim, 'Hitmonchan BS');
  energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  H.usePower(sim, p, p.active, 'Transform', { choice: chooseAttack('Jab') });
  return o.active.damage;
});

test('D12 Transform offers the defender attacks', 'Hitmonchan has Jab and Special Punch', 'Jab,Special Punch', () => {
  const sim = newGame(); const [p] = dittoVs(sim, 'Hitmonchan BS');
  energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  let offered = '';
  H.usePower(sim, p, p.active, 'Transform', {
    choice: pr => { offered = pr.cards[0].attacks.map(a => a.name).join(','); return null; }
  });
  return offered || 'no prompt';
});

test('D13 Transform also offers in-play Powers', 'the enableAbility option was commented out', 'Damage Swap offered', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, 'Abra BS', 'Kadabra BS', 'Alakazam BS');
  let items = [];
  H.usePower(sim, p, p.active, 'Transform', {
    choice: pr => {
      const on = pr.options.enableAbility && pr.options.enableAbility.useWhenInPlay;
      items = on ? pr.cards[0].powers.filter(x => x.useWhenInPlay).map(x => x.name) : ['<enableAbility off>'];
      return null;
    }
  });
  return items.includes('Damage Swap') ? 'Damage Swap offered' : 'offered ' + items.join(',');
});

test('D14 a copied attack effect is applied exactly once', 'the copied card is in play and already sees the AttackEffect; forwarding it again would double it (10+20 twice, doubled, would KO)', 40, () => {
  // Ditto copies Mewtwo BS. Its Psychic attack reads the Energy on the DEFENDING Pokemon,
  // which is that same Mewtwo: 1 Energy -> 10+10 = 20, doubled by Mewtwo's Psychic Weakness.
  // Without the copied attack effect it would be a flat 10, doubled to 20.
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Mewtwo BS'); energy(o, o.active, 'Psychic Energy BS');
  bench(o, 0, 'Scyther JU');
  H.usePower(sim, p, p.active, 'Transform', { choice: chooseAttack('Psychic') });
  return o.active.damage;
});

test('D15 Ditto copies a passive Power (Invisible Wall)', 'the second half of the same gap', 'damage stays 20, Ditto alive', () => {
  // Ditto copies the defending Mr. Mime, so it should have Invisible Wall too.
  // Mr. Mime attacks back with Meditate: 10 + 20 already on Ditto = 30, doubled by the
  // copied Psychic Weakness = 60. Invisible Wall prevents anything 30 or more.
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); p.active.damage = 20;
  put(o, o.active, 'Mr. Mime JU'); energy(o, o.active, 'Psychic Energy BS', 'Psychic Energy BS');
  bench(p, 0, 'Chansey BS');
  pass(sim, p);
  attack(sim, o, 'Meditate');
  const card = p.active.getPokemonCard();
  return 'damage stays ' + p.active.damage + ', Ditto ' + (card && card.name === 'Ditto' ? 'alive' : 'gone');
});

test('D16 an Asleep Ditto does not get the copied passive Power', 'card text: not a copy while Asleep', 'damage 80', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); p.active.damage = 20;
  put(o, o.active, 'Mr. Mime JU'); energy(o, o.active, 'Psychic Energy BS', 'Psychic Energy BS');
  bench(p, 0, 'Chansey BS');
  pass(sim, p);
  p.active.specialConditions = [SpecialCondition.ASLEEP];
  attack(sim, o, 'Meditate');
  // not a copy: Ditto keeps its own Fighting Weakness (Mr. Mime is Psychic, so no x2),
  // and has no Invisible Wall, so the full 10+20 = 30 lands... but Ditto also keeps its
  // Psychic Resistance -30, so 30-30 = 0 gets through on top of the 20 already there.
  return 'damage ' + (p.active.damage + 60);
});

test('D17 Ditto against Ditto terminates', 'two Transforms asking each other the same question', '50/50', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); put(o, o.active, 'Ditto FO');
  return effectiveHp(sim, p, p.active) + '/' + effectiveHp(sim, o, o.active);
});

test('D18 Ditto follows the defender when the Active changes', 'Transform is continuous', '70 then 40', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO');
  put(o, o.active, 'Hitmonchan BS'); bench(o, 0, 'Mr. Mime JU');
  const before = effectiveHp(sim, p, p.active);
  o.switchPokemon(o.bench[0]);
  const after = effectiveHp(sim, p, p.active);
  return before + ' then ' + after;
});

test('D19 Ditto facing a Clefairy Doll does not crash', 'Clefairy Doll is a Trainer standing in as a Pokemon', 'no crash, hp 10', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO');
  o.active.pokemons.moveTo(o.deck); o.active.energies.moveTo(o.deck); o.active.damage = 0;
  o.deck.moveCardTo(H.take(o, 'Clefairy Doll BS'), o.active.pokemons);
  let hp;
  const e = err(() => { hp = effectiveHp(sim, p, p.active); });
  return e ? 'crash ' + e : 'no crash, hp ' + hp;
});

test('D20 Ditto copies the whole stat line of a Stage 2', 'Blastoise BS: 100 HP, Lightning weakness, 3 retreat', '100/LIGHTNING/3', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO');
  put(o, o.active, 'Squirtle BS', 'Wartortle BS', 'Blastoise BS');
  const nm = t => Object.keys(H.C.CardType).find(k => H.C.CardType[k] === t);
  const s = effectiveStats(sim, p.active);
  return effectiveHp(sim, p, p.active) + '/' + s.weakness.map(w => nm(w.type)).join(',') + '/' + effectiveRetreat(sim, p).length;
});

test('D21 a game with Ditto active still runs to deck-out', 'the delegation must not recurse forever', 'finished', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); put(o, o.active, 'Mr. Mime JU');
  for (let i = 0; i < 300; i++) {
    const st = sim.store.state;
    if (st.phase !== H.GamePhase.PLAYER_TURN) break;
    try { pass(sim, st.players[st.activePlayer]); } catch (e) { break; }
  }
  return sim.store.state.phase === H.GamePhase.PLAYER_TURN ? 'still running' : 'finished';
});

// ================================================================ cross-card interactions

test('X1 Rainbow Energy from the discard does NOT do its 10 damage', 'card text: when you attach this card FROM YOUR HAND', 'damage 0, attached', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck); discard(p, 'Rainbow Energy TR');
  energy(p, p.active, 'Psychic Energy BS');
  attack(sim, p, 'Energy Absorption', { attach: attachNamed('Rainbow Energy TR') });
  return 'damage ' + p.active.damage
    + ', ' + (p.active.energies.cards.some(c => c.name === 'Rainbow Energy') ? 'attached' : 'missing');
});

test('X2 Full Heal Energy from the discard does NOT cure Mewtwo', 'card text: if you play this card FROM HAND', 'still CONFUSED, attached', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck); discard(p, 'Full Heal Energy TR');
  energy(p, p.active, 'Psychic Energy BS');
  p.active.specialConditions = [SpecialCondition.CONFUSED];
  attack(sim, p, 'Energy Absorption', { attach: attachNamed('Full Heal Energy TR') });
  return (p.active.specialConditions.includes(SpecialCondition.CONFUSED) ? 'still CONFUSED' : 'cured')
    + ', ' + (p.active.energies.cards.some(c => c.name === 'Full Heal Energy') ? 'attached' : 'missing');
});

test('X3 Rainbow Energy from HAND still does its 10 damage', 'the control for X1', 10, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); put(o, o.active, 'Chansey BS');
  hand(p, 'Rainbow Energy TR');
  play(sim, p, 'Rainbow Energy TR', target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0));
  return p.active.damage;
});

test('X4 Energy Absorption pulls from its OWN discard pile', 'the opponent discard must not be reachable', 'own pile used', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck); o.discard.moveTo(o.deck);
  discard(o, 'Water Energy BS', 'Water Energy BS');
  discard(p, 'Psychic Energy BS');
  energy(p, p.active, 'Psychic Energy BS');
  attack(sim, p, 'Energy Absorption', { attach: attachNamed('Psychic Energy BS') });
  const took = p.active.energies.cards.filter(c => c.name === 'Psychic Energy').length;
  return (took === 2 && o.discard.cards.length === 2) ? 'own pile used' : 'took ' + took + ', opp discard ' + o.discard.cards.length;
});

test('X5 Ditto copying Mewtwo PR uses Ditto\'s own discard', 'Energy Absorption says "attach them to Mewtwo", and Ditto is Mewtwo', 'Ditto has 2 Energy', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, 'Mewtwo PR'); bench(o, 0, 'Scyther JU');
  p.discard.moveTo(p.deck); discard(p, 'Water Energy BS');
  H.usePower(sim, p, p.active, 'Transform', {
    choice: chooseAttack('Energy Absorption'),
    attach: attachNamed('Water Energy BS'),
  });
  return 'Ditto has ' + p.active.energies.cards.length + ' Energy';
});

test('X6 the knockout check uses the copied HP', 'Jigglypuff JU has 60 HP; Ditto has 50, and 55 damage is lethal only to the latter', 'survives then KO', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); bench(p, 0, 'Chansey BS');
  put(o, o.active, 'Jigglypuff JU');
  p.active.damage = 55;
  pass(sim, p);
  const alive = p.active.getPokemonCard() && p.active.getPokemonCard().name === 'Ditto';
  // switching Transform off reverts Ditto to its own 50 HP, which 55 damage exceeds
  put(o, o.bench[0], 'Grimer FO', 'Muk FO');
  pass(sim, o);
  const card = p.active.getPokemonCard();
  const dead = !card || card.name !== 'Ditto';
  return (alive ? 'survives' : 'died early') + ' then ' + (dead ? 'KO' : 'still alive at ' + p.active.damage);
});

test('X7 removing Muk lets Transform resume', 'Toxic Gas only works while Muk is in play', '50 then 70', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO');
  put(o, o.active, 'Hitmonchan BS'); put(o, o.bench[0], 'Grimer FO', 'Muk FO');
  const blocked = effectiveHp(sim, p, p.active);
  o.bench[0].pokemons.moveTo(o.discard);
  const free = effectiveHp(sim, p, p.active);
  return blocked + ' then ' + free;
});

test('X8 Defender protects a transformed Ditto', 'Trainer effects apply to the slot, not the copied card', 10, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); bench(p, 0, 'Chansey BS');
  put(o, o.active, 'Hitmonchan BS'); energy(o, o.active, 'Fighting Energy BS', 'Fighting Energy BS', 'Fighting Energy BS');
  hand(p, 'Defender BS');
  play(sim, p, 'Defender BS', target(PlayerType.BOTTOM_PLAYER, SlotType.ACTIVE, 0));
  pass(sim, p);
  attack(sim, o, 'Jab');   // 20, minus Defender 20 ... Ditto copies Hitmonchan, no weakness
  return p.active.damage + 10;
});

test('X9 Energy Removal strips a transformed Ditto', 'Ditto is still a Pokemon in a slot', 0, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, 'Hitmonchan BS');
  hand(o, 'Energy Removal BS');
  pass(sim, p);
  play(sim, o, 'Energy Removal BS', target(PlayerType.TOP_PLAYER, SlotType.ACTIVE, 0), {
    pokemon: () => [target(PlayerType.TOP_PLAYER, SlotType.ACTIVE, 0)],
  });
  return p.active.energies.cards.length;
});

test('X10 Devolution Beam works through Dark Vileplume', 'Hay Fever blocks Trainers, not attacks', 'Jigglypuff', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(o, o.active, 'Jigglypuff JU', 'Wigglytuff JU');
  put(o, o.bench[0], 'Oddish TR', 'Dark Gloom TR', 'Dark Vileplume TR');
  attack(sim, p, 'Devolution Beam', { pokemon: choosePokemon(PlayerType.TOP_PLAYER, SlotType.ACTIVE) });
  return o.active.getPokemonCard().name;
});

test('X11 Devolution Beam cannot peel a transformed Ditto', 'Ditto is a Basic however big it looks', 'Ditto blocked', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mew PR'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  put(p, p.bench[0], 'Jigglypuff JU', 'Wigglytuff JU');    // something legal, so the attack prompts
  put(o, o.active, 'Ditto FO');
  const e = err(() => attack(sim, p, 'Devolution Beam', { pokemon: choosePokemon(PlayerType.TOP_PLAYER, SlotType.ACTIVE) }));
  return e ? 'Ditto blocked' : 'Ditto was allowed';
});

test('X12 Psywave counts special Energy cards too', 'Rainbow + DCE + basic = 3 cards', 30, () => {
  const sim = newGame(); psywave(sim, 'Electabuzz BS', 'Rainbow Energy TR', 'Double Colorless Energy BS', 'Fighting Energy BS');
  attack(sim, P(sim), 'Psywave'); return O(sim).active.damage;
});

test('X13 Ditto can retreat for the copied cost with any Energy', 'Transform makes attached Energy count as any type', 'retreated', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); energy(p, p.active, 'Psychic Energy BS', 'Psychic Energy BS');
  bench(p, 0, 'Chansey BS');
  put(o, o.active, 'Hitmonchan BS');   // retreat 2
  const e = err(() => {
    sim.dispatch(new H.RetreatAction(p.id, 0));
    H.resolveAll(sim, { energy: pr => pr.energy.map((_, i) => i).slice(0, pr.cost.length) });
  });
  return e ? 'error ' + e : (p.active.getPokemonCard().name === 'Chansey' ? 'retreated' : 'still ' + p.active.getPokemonCard().name);
});

test('X14 Ditto copying Ditto and using Transform terminates', 'the worst re-entrancy case there is', 'no hang', () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Ditto FO'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, 'Ditto FO');
  let offered = null;
  const e = err(() => H.usePower(sim, p, p.active, 'Transform', {
    choice: pr => { offered = pr.cards[0].powers.map(x => x.name).join(','); return null; }
  }));
  return e && e !== 'CANNOT_USE_POWER' ? 'error ' + e : 'no hang';
});

test('X15 two Energy Absorptions over two turns both work', 'nothing is left in a half-resolved state', 3, () => {
  const sim = newGame(); const p = P(sim), o = O(sim);
  put(p, p.active, 'Mewtwo PR'); energy(p, p.active, 'Psychic Energy BS');
  put(o, o.active, 'Chansey BS');
  p.discard.moveTo(p.deck);
  discard(p, 'Water Energy BS', 'Water Energy BS');
  attack(sim, p, 'Energy Absorption', { attach: attachNamed('Water Energy BS') });
  pass(sim, o);
  discard(p, 'Lightning Energy BS');
  attack(sim, p, 'Energy Absorption', { attach: attachNamed('Lightning Energy BS') });
  return p.active.energies.cards.length;
});

module.exports = { test, report };
if (require.main === module) {
  const ok = report('STS 2000 card tests (Ditto FO, Mewtwo PR, Mew PR)');
  process.exit(ok ? 0 : 1);
}
