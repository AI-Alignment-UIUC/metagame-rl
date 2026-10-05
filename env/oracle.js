// Reference legality for verifying legal.js. Slow by design: it tries every structurally
// possible action instead of reasoning about which ones could work.
//
// Main phase: every action shape the engine has (each hand card onto each of 12 Pokemon slots
// and the off-board targets, each retreat, attack, Power, Stadium and Trainer-in-play use, on
// both players' sides) is tried on a clone; the accepted ones are mapped to option keys.
// Accepted actions the rules forbid (playing onto the opponent's side, say) are engine
// leniency rather than enumerator misses and are counted separately by category.
//
// Prompts: candidate answers are generated from the raw result space (all of it when small,
// a random sample otherwise) and checked with the prompt's decode + validate and its declared
// options; every legal one must be reachable through the enumerator's picks.
'use strict';
const { C, accepts } = require('./engine.js');
const { allSlots, safeValidate, occupied, isTargetedTrainer, promptSpace, deadEndAction } = require('./legal.js');
const { PlayerType, SlotType, Stage, EnergyCard, PokemonCard, TrainerCard } = C;

function codeOf(state, me, target) {
  const opp = state.players.find(p => p.id !== me.id);
  const p = target.player === PlayerType.TOP_PLAYER ? opp : me;
  const prefix = target.player === PlayerType.TOP_PLAYER ? 'o' : '';
  if (target.slot === SlotType.ACTIVE) return prefix + 'A';
  if (target.slot === SlotType.BENCH) {
    const b = p.bench[target.index];
    if (!b) return prefix + 'B?';
    return prefix + (occupied(b) ? 'B' + target.index : 'E');
  }
  return '-';
}

const BOARD_TARGETS = [];
for (const player of [PlayerType.BOTTOM_PLAYER, PlayerType.TOP_PLAYER]) {
  BOARD_TARGETS.push({ player, slot: SlotType.ACTIVE, index: 0 });
  for (let i = 0; i < 5; i++) BOARD_TARGETS.push({ player, slot: SlotType.BENCH, index: i });
}
const OFF_TARGETS = [SlotType.BOARD, SlotType.HAND, SlotType.DISCARD].map(slot => ({ player: PlayerType.BOTTOM_PLAYER, slot, index: 0 }));

function turnOracle(state) {
  const me = state.players[state.activePlayer];
  const id = me.id;
  const keys = new Set(['pass']);
  const lax = new Map();
  const anomalies = [];
  const addLax = c => lax.set(c, (lax.get(c) || 0) + 1);
  if (!accepts(state, new C.PassTurnAction(id))) anomalies.push('pass rejected');

  me.hand.cards.forEach((card, h) => {
    const name = card.fullName;
    const targeted = card instanceof TrainerCard && isTargetedTrainer(card);
    let acceptedUntargeted = 0;
    const all = BOARD_TARGETS.concat(OFF_TARGETS);
    for (const t of all) {
      const play = new C.PlayCardAction(id, h, t);
      if (!accepts(state, play)) continue;
      if (card instanceof TrainerCard && deadEndAction(state, play)) { addLax('dead-end'); continue; }
      const code = codeOf(state, me, t);
      const theirs = code.startsWith('o') || code === '-';
      if (card instanceof EnergyCard) {
        if (theirs || code === 'E') addLax('attach@' + code); else keys.add(`attach|${name}|${code}`);
      } else if (card instanceof PokemonCard) {
        if (card.stage === Stage.BASIC) {
          if (code === 'E') keys.add(`basic|${name}`); else addLax('basic@' + code);
        } else if (theirs) addLax('evolve@' + code); else keys.add(`evolve|${name}|${code}`);
      } else if (card instanceof TrainerCard) {
        if (targeted) {
          if (code.startsWith('o')) addLax('trainer@opponent'); else keys.add(`trainer|${name}|${code}`);
        } else {
          acceptedUntargeted++;
          keys.add(`trainer|${name}|-`);
        }
      }
    }
    if (card instanceof TrainerCard && !targeted && acceptedUntargeted > 0 && acceptedUntargeted < all.length) {
      anomalies.push(`untargeted trainer ${name} accepted on ${acceptedUntargeted}/${all.length} targets`);
    }
  });

  for (let i = 0; i < 5; i++) {
    const retreat = new C.RetreatAction(id, i);
    if (!accepts(state, retreat)) continue;
    if (deadEndAction(state, retreat)) addLax('dead-end'); else keys.add(`retreat|B${i}`);
  }
  const active = me.active.getPokemonCard();
  if (active) {
    for (const a of active.attacks) if (accepts(state, new C.AttackAction(id, a.name))) keys.add(`attack|${a.name}`);
  }
  for (const s of allSlots(state, me)) {
    const pokemon = s.slot.getPokemonCard();
    if (pokemon) {
      for (const power of pokemon.powers) {
        const action = new C.UseAbilityAction(id, power.name, s.target);
        if (!accepts(state, action)) continue;
        if (!s.mine) addLax('power@opponent');
        else if (deadEndAction(state, action)) addLax('dead-end');
        else keys.add(`power|${power.name}|${s.code}`);
      }
    }
    const names = new Set();
    for (const c of [...s.slot.pokemons.cards, ...s.slot.energies.cards, ...s.slot.trainers.cards]) {
      if (c instanceof TrainerCard) names.add(c.name);
    }
    for (const n of names) {
      const tip = new C.UseTrainerInPlayAction(id, s.target, n);
      if (!accepts(state, tip)) continue;
      if (!s.mine) addLax('tip@opponent');
      else if (deadEndAction(state, tip)) addLax('dead-end');
      else keys.add(`tip|${n}|${s.code}`);
    }
  }
  for (const [cards, slot, prefix] of [[me.hand.cards, SlotType.HAND, 'H'], [me.discard.cards, SlotType.DISCARD, 'D']]) {
    cards.forEach((card, i) => {
      if (!(card instanceof PokemonCard)) return;
      for (const power of card.powers) {
        const t = { player: PlayerType.BOTTOM_PLAYER, slot, index: i };
        const use = new C.UseAbilityAction(id, power.name, t);
        if (!accepts(state, use)) continue;
        if (deadEndAction(state, use)) addLax('dead-end'); else keys.add(`power|${power.name}|${prefix}${card.fullName}`);
      }
    });
  }
  const stadium = new C.UseStadiumAction(id);
  if (accepts(state, stadium)) { if (deadEndAction(state, stadium)) addLax('dead-end'); else keys.add('stadium'); }
  return { keys, lax, anomalies };
}

// ---------------------------------------------------------------- prompts

// All complete answers the enumerator can produce: walk the picks. Returns [{key, raw}].
function enumeratedAnswers(space, limit = 20000) {
  const out = [];
  const walk = picks => {
    if (out.length >= limit) return;
    for (const o of space.options(picks)) {
      if (o.pick !== undefined) walk(picks.concat(o.pick));
      else out.push({ key: (picks.length ? picks.join(',') + '/' : '') + o.key, raw: o.raw, picks, opt: o });
    }
  };
  walk([]);
  return out;
}

function* subsets(n, maxSize) {
  const cur = [];
  function* rec(start) {
    yield cur.slice();
    if (cur.length >= maxSize) return;
    for (let i = start; i < n; i++) { cur.push(i); yield* rec(i + 1); cur.pop(); }
  }
  yield* rec(0);
}

function countSubsets(n, k) {
  let total = 0, c = 1;
  for (let i = 0; i <= Math.min(n, k); i++) { total += c; c = c * (n - i) / (i + 1); }
  return total;
}

function sampleSubsets(n, maxSize, count, rand) {
  const out = [];
  for (let s = 0; s < count; s++) {
    const k = 1 + Math.floor(rand() * Math.min(n, maxSize));
    const idx = new Set();
    while (idx.size < k) idx.add(Math.floor(rand() * n));
    out.push([...idx].sort((a, b) => a - b));
  }
  return out;
}

// Canonical form of a raw answer, matching the enumerator's pick order. `itemOf(raw)` maps a raw
// answer to the enumerator's item keys; multisets are sorted by item order.
function canonical(itemKeys, order, ordered) {
  const sorted = (ordered ? itemKeys.slice(1) : itemKeys.slice()).sort((a, b) => order.get(a) - order.get(b));
  return (ordered ? [itemKeys[0], ...sorted] : sorted).join(',');
}

function promptOracle(prompt, state, rand) {
  const space = promptSpace(prompt, state);
  const enumerated = enumeratedAnswers(space);
  const result = { checked: 0, enumerated: enumerated.length, invalid: [], missing: [], type: prompt.type };
  // Soundness: every enumerated answer passes the server's check.
  for (const a of enumerated) {
    if (!safeValidate(prompt, a.raw, state)) result.invalid.push(a.key);
  }
  // Completeness, per type.
  const me = state.players.find(p => p.id === prompt.playerId);
  const ek = new Set();
  const nameOfPick = (picks, items) => picks.map(i => items[i]);
  switch (prompt.type) {
    case 'Choose cards': {
      const cards = prompt.cards.cards;
      const o = prompt.options;
      const ordered = prompt.message === C.GameMessage.CHOOSE_STARTING_POKEMONS;
      const groupKey = c => o.isSecret ? '?' : c.fullName;
      const order = new Map();
      cards.forEach(c => { if (!order.has(groupKey(c))) order.set(groupKey(c), order.size); });
      for (const a of enumerated) {
        if (a.raw === null) { ek.add('cancel'); continue; }
        ek.add(canonical(a.raw.map(i => groupKey(cards[i])), order, ordered));
      }
      const max = Math.min(o.max, cards.length);
      let raws = countSubsets(cards.length, max) <= 20000 ? [...subsets(cards.length, max)] : sampleSubsets(cards.length, max, 5000, rand);
      if (ordered) raws = raws.flatMap(r => r.map((first, i) => [first, ...r.filter((_, j) => j !== i)]));
      for (const raw of raws.concat([null])) {
        if (!safeValidate(prompt, raw, state)) continue;
        result.checked++;
        const k = raw === null ? 'cancel' : canonical(raw.map(i => groupKey(cards[i])), order, ordered);
        if (!ek.has(k)) result.missing.push(k || '(none)');
      }
      break;
    }
    case 'Choose pokemon': {
      const slots = allSlots(state, me);
      const order = new Map(slots.map((s, i) => [s.code, i]));
      const declared = s => (prompt.playerType === PlayerType.ANY || s.target.player === prompt.playerType) && prompt.slots.includes(s.target.slot);
      for (const a of enumerated) {
        if (a.raw === null) { ek.add('cancel'); continue; }
        ek.add(canonical(a.raw.map(t => codeOf(state, me, t)), order, false));
      }
      for (const sub of subsets(slots.length, Math.min(prompt.options.max, slots.length))) {
        const raw = sub.map(i => slots[i].target);
        if (!sub.every(i => declared(slots[i])) || !safeValidate(prompt, raw, state)) continue;
        result.checked++;
        const k = canonical(raw.map(t => codeOf(state, me, t)), order, false);
        if (!ek.has(k)) result.missing.push(k);
      }
      if (safeValidate(prompt, null, state) && !ek.has('cancel')) result.missing.push('cancel');
      break;
    }
    case 'Choose energy': {
      const key = e => e.card.fullName;
      const order = new Map();
      prompt.energy.forEach(e => { if (!order.has(key(e))) order.set(key(e), order.size); });
      for (const a of enumerated) ek.add(a.raw === null ? 'cancel' : canonical(a.raw.map(i => key(prompt.energy[i])), order, false));
      for (const raw of [...subsets(prompt.energy.length, prompt.energy.length)].concat([null])) {
        if (!safeValidate(prompt, raw, state)) continue;
        result.checked++;
        const k = raw === null ? 'cancel' : canonical(raw.map(i => key(prompt.energy[i])), order, false);
        if (!ek.has(k)) result.missing.push(k);
      }
      break;
    }
    case 'Attach energy': {
      const cards = prompt.cardList.cards;
      const o = prompt.options;
      const slots = allSlots(state, me);
      const declared = t => {
        const s = slots.find(x => x.target.player === t.player && x.target.slot === t.slot && x.target.index === t.index);
        return s && occupied(s.slot) && (prompt.playerType === PlayerType.ANY || t.player === prompt.playerType)
          && prompt.slots.includes(t.slot) && !o.blockedTo.some(b => b.player === t.player && b.slot === t.slot && b.index === t.index);
      };
      const item = r => `${cards[r.index].fullName}>${codeOf(state, me, r.to)}`;
      const order = new Map();
      cards.forEach(c => slots.forEach(s => { const k = `${c.fullName}>${s.code}`; if (!order.has(k)) order.set(k, order.size); }));
      for (const a of enumerated) ek.add(a.raw === null ? 'cancel' : canonical(a.raw.map(item), order, false));
      const max = Math.min(o.max, cards.length, 3);
      const pairs = [];
      cards.forEach((_, index) => slots.forEach(s => pairs.push({ to: s.target, index })));
      const raws = [];
      for (let s = 0; s < 4000; s++) {
        const k = Math.floor(rand() * (max + 1));
        const used = new Set();
        const raw = [];
        while (raw.length < k) {
          const p = pairs[Math.floor(rand() * pairs.length)];
          if (used.has(p.index)) continue;
          used.add(p.index); raw.push(p);
        }
        raws.push(raw);
      }
      for (const raw of raws.concat([null])) {
        if (raw !== null && !raw.every(r => declared(r.to))) continue;
        if (!safeValidate(prompt, raw, state)) continue;
        result.checked++;
        const k = raw === null ? 'cancel' : canonical(raw.map(item), order, false);
        if (!ek.has(k)) result.missing.push(k);
      }
      break;
    }
    case 'Choose attack': case 'Select': case 'Confirm': case 'Show cards': case 'Alert': {
      for (const a of enumerated) ek.add(JSON.stringify(a.raw));
      const raws = {
        'Choose attack': [null],
        'Select': [...(prompt.options && prompt.options.allowCancel ? [null] : []), ...prompt.values ? prompt.values.map((_, i) => i) : []],
        'Confirm': [true, false],
        'Show cards': [true, ...(prompt.options && prompt.options.allowCancel ? [null] : [])],
        'Alert': [true],
      }[prompt.type];
      if (prompt.type === 'Choose attack') {
        prompt.cards.forEach((c, index) => [...c.attacks, ...c.powers].forEach(x => raws.push({ index, name: x.name })));
      }
      for (const raw of raws) {
        if (!safeValidate(prompt, raw, state)) continue;
        result.checked++;
        if (!ek.has(JSON.stringify(raw))) result.missing.push('raw ' + JSON.stringify(raw));
      }
      break;
    }
    default:
      result.noCompleteness = true;
  }
  return result;
}

module.exports = { turnOracle, promptOracle, enumeratedAnswers };
