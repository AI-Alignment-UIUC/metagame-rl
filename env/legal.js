// Legal-action enumerator (plan item A1.2).
//
// At every decision the environment offers a list of options, each with a canonical `key`:
//
//   Main phase (the active player, no prompt open), one option per distinct legal move:
//     pass                        end the turn
//     attach|<card>|<slot>        attach an Energy card from hand
//     basic|<card>                put a Basic Pokemon from hand onto the Bench
//     evolve|<card>|<slot>        evolve the Pokemon in <slot>
//     trainer|<card>|<slot or ->  play a Trainer (only a few take a target)
//     retreat|<slot>              retreat to that Bench slot
//     attack|<name>               attack with the Active Pokemon
//     power|<name>|<slot>         use a Pokemon Power (in play, or from hand/discard: H<i>/D<i>)
//     stadium                     use the Stadium in play
//     tip|<card>|<slot>           use a Trainer in play (Clefairy Doll, Mysterious Fossil)
//
//   Prompts: a prompt that needs several picks (choose cards, Pokemon, Energy, ...) is answered
//   one pick at a time: pick|..., then done; cancel answers null where the prompt allows it.
//
// Slots are relative to the player deciding: A = Active, B0..B4 = Bench, E = an empty Bench
// slot (all empty slots are equivalent), oA / oB<i> = the opponent's. Cards are named by
// fullName, so copies of one card are a single option (they are interchangeable).
//
// Legality comes from the engine wherever it can: the main-phase rules mirror the reducers,
// and the moves whose legality lives in card code (Trainers, Powers, attacks, retreat) are
// tried on a clone. Prompt results are checked with the prompt's own decode + validate, the
// same check the ryuu-play server applies, plus the prompt's declared options (slots, blocked
// targets), which the server leaves to the client. oracle.js verifies all of this.
'use strict';
const { C, accepts: engineAccepts } = require('./engine.js');
const {
  PlayerType, SlotType, Stage, SuperType, TrainerType, SpecialCondition, StateUtils, FilterUtils,
  EnergyCard, PokemonCard, TrainerCard, GameError, GameMessage, PassTurnAction, PlayCardAction, RetreatAction,
  AttackAction, UseAbilityAction, UseStadiumAction, UseTrainerInPlayAction,
  CheckProvidedEnergyEffect, CheckAttackCostEffect, CheckRetreatCostEffect,
} = C;   // destructured once: the engine's exports are getters

// ---------------------------------------------------------------- slots and targets

function playerOf(state, id) { return state.players.find(p => p.id === id); }
function opponentOf(state, id) { return state.players.find(p => p.id !== id); }

// All Pokemon slots of `me` and the opponent, as {code, target, slot}. `target` is a CardTarget
// relative to `me` (BOTTOM = me).
function allSlots(state, me) {
  const out = [];
  const opp = opponentOf(state, me.id);
  for (const [who, p, prefix] of [[PlayerType.BOTTOM_PLAYER, me, ''], [PlayerType.TOP_PLAYER, opp, 'o']]) {
    out.push({ code: prefix + 'A', target: { player: who, slot: SlotType.ACTIVE, index: 0 }, slot: p.active, mine: who === PlayerType.BOTTOM_PLAYER });
    p.bench.forEach((b, i) => out.push({ code: prefix + 'B' + i, target: { player: who, slot: SlotType.BENCH, index: i }, slot: b, mine: who === PlayerType.BOTTOM_PLAYER }));
  }
  return out;
}

function occupied(slot) { return slot.pokemons.cards.length > 0; }

// Canonical code of a slot: empty Bench slots are interchangeable.
function canonicalCode(s) { return occupied(s.slot) || s.target.slot === SlotType.ACTIVE ? s.code : s.code.replace(/B\d$/, 'E'); }

function targetKey(t) { return `${t.player}:${t.slot}:${t.index}`; }

// ---------------------------------------------------------------- main phase

// Does the card's Trainer-play handler read the play target? (Clefairy Doll, Mysterious Fossil.)
const targetedCache = new Map();
function isTargetedTrainer(card) {
  if (card.trainerType === TrainerType.TOOL) return true;
  let v = targetedCache.get(card.fullName);
  if (v === undefined) {
    const src = card.reduceEffect.toString();
    const at = src.indexOf('instanceof TrainerEffect');
    const next = at === -1 ? -1 : src.indexOf('instanceof', at + 25);
    const branch = at === -1 ? '' : src.slice(at, next === -1 ? undefined : next);
    v = /effect\.target\b/.test(branch);
    targetedCache.set(card.fullName, v);
  }
  return v;
}

function firstIndexByName(cards) {
  const seen = new Map();
  cards.forEach((c, i) => { if (!seen.has(c.fullName)) seen.set(c.fullName, i); });
  return seen;
}

// store: the store that owns `state` (lets trials reuse its card-order cache; optional).
function turnOptions(state, store) {
  const accepts = (st, action) => engineAccepts(st, action, store);
  const me = state.players[state.activePlayer];
  const turn = state.turn;
  const id = me.id;
  const out = [{ key: 'pass', action: new PassTurnAction(id) }];
  const slots = allSlots(state, me);
  const mine = slots.filter(s => s.mine);
  const myOccupied = mine.filter(s => occupied(s.slot));
  const emptyBench = mine.find(s => s.target.slot === SlotType.BENCH && !occupied(s.slot));

  for (const [name, h] of firstIndexByName(me.hand.cards)) {
    const card = me.hand.cards[h];
    if (card instanceof EnergyCard) {
      if (me.energyPlayedTurn === turn) continue;
      for (const s of myOccupied) {
        out.push({ key: `attach|${name}|${s.code}`, action: new PlayCardAction(id, h, s.target) });
      }
    } else if (card instanceof PokemonCard) {
      if (card.stage === Stage.BASIC) {
        if (emptyBench) out.push({ key: `basic|${name}`, action: new PlayCardAction(id, h, emptyBench.target) });
      } else {
        for (const s of myOccupied) {
          const top = s.slot.getPokemonCard();
          if (top && top.stage < card.stage && top.name === card.evolvesFrom && s.slot.pokemonPlayedTurn < turn) {
            out.push({ key: `evolve|${name}|${s.code}`, action: new PlayCardAction(id, h, s.target) });
          }
        }
      }
    } else if (card instanceof TrainerCard) {
      if (card.trainerType === TrainerType.SUPPORTER
        && ((turn === 1 && !state.rules.firstTurnUseSupporter) || me.supporter.cards.length > 0)) continue;
      if (card.trainerType === TrainerType.STADIUM) {
        const stadium = StateUtils.getStadiumCard(state);
        if (me.stadiumPlayedTurn === turn || (stadium && stadium.name === card.name)) continue;
      }
      if (isTargetedTrainer(card)) {
        const targets = mine.filter(s => occupied(s.slot)).concat(emptyBench ? [emptyBench] : []);
        for (const s of targets) {
          const action = new PlayCardAction(id, h, s.target);
          if (accepts(state, action)) out.push({ key: `trainer|${name}|${canonicalCode(s)}`, action });
        }
      } else {
        const action = new PlayCardAction(id, h, { player: PlayerType.BOTTOM_PLAYER, slot: SlotType.ACTIVE, index: 0 });
        if (accepts(state, action)) out.push({ key: `trainer|${name}|-`, action });
      }
    }
  }

  // Energy on the Active, as the engine counts it (Double Colorless, Rainbow, Ditto...). The
  // engine checks retreat and attack costs against it before anything else that could fail,
  // so an unaffordable retreat or attack is ruled out without a trial. These are the engine's
  // own query effects; with no store (the oracle) every candidate is tried instead.
  let provided;
  const query = effect => { store.reduceEffect(state, effect); return effect; };
  const providedEnergy = () => {
    if (provided === undefined) provided = query(new CheckProvidedEnergyEffect(me)).energyMap;
    return provided;
  };
  const canPay = cost => store === undefined || cost.length === 0 || StateUtils.checkEnoughEnergy(providedEnergy(), cost);

  // Retreat: legality doesn't depend on which Bench Pokemon comes up, so one trial decides.
  const sp = me.active.specialConditions;
  const benched = mine.filter(s => s.target.slot === SlotType.BENCH && occupied(s.slot));
  if (benched.length > 0 && occupied(me.active) && me.retreatedTurn !== turn
    && !sp.includes(SpecialCondition.PARALYZED) && !sp.includes(SpecialCondition.ASLEEP)
    && (store === undefined || canPay(query(new CheckRetreatCostEffect(me)).cost))
    && accepts(state, new RetreatAction(id, benched[0].target.index))) {
    for (const s of benched) out.push({ key: `retreat|${s.code}`, action: new RetreatAction(id, s.target.index) });
  }

  // Attacks.
  const active = me.active.getPokemonCard();
  if (active && !sp.includes(SpecialCondition.PARALYZED) && !sp.includes(SpecialCondition.ASLEEP)) {
    const seen = new Set();
    for (const attack of active.attacks) {
      if (seen.has(attack.name)) continue;
      seen.add(attack.name);
      if (store !== undefined && !canPay(query(new CheckAttackCostEffect(me, attack)).cost)) continue;
      const action = new AttackAction(id, attack.name);
      if (accepts(state, action)) out.push({ key: `attack|${attack.name}`, action });
    }
  }

  // Pokemon Powers: in play, then from hand and discard.
  for (const s of myOccupied) {
    const pokemon = s.slot.getPokemonCard();
    if (!pokemon) continue;
    for (const power of pokemon.powers) {
      if (!power.useWhenInPlay) continue;
      const action = new UseAbilityAction(id, power.name, s.target);
      if (accepts(state, action)) out.push({ key: `power|${power.name}|${s.code}`, action });
    }
  }
  for (const [zone, cards, slotType, prefix] of [['hand', me.hand.cards, SlotType.HAND, 'H'], ['discard', me.discard.cards, SlotType.DISCARD, 'D']]) {
    for (const [name, i] of firstIndexByName(cards)) {
      const card = cards[i];
      if (!(card instanceof PokemonCard)) continue;
      for (const power of card.powers) {
        if (!(zone === 'hand' ? power.useFromHand : power.useFromDiscard)) continue;
        const action = new UseAbilityAction(id, power.name, { player: PlayerType.BOTTOM_PLAYER, slot: slotType, index: i });
        if (accepts(state, action)) out.push({ key: `power|${power.name}|${prefix}${name}`, action });
      }
    }
  }

  // Stadium and Trainers in play.
  const stadium = StateUtils.getStadiumCard(state);
  if (stadium && stadium.useWhenInPlay && me.stadiumUsedTurn !== turn) {
    const action = new UseStadiumAction(id);
    if (accepts(state, action)) out.push({ key: 'stadium', action });
  }
  for (const s of myOccupied) {
    const names = new Set();
    for (const c of [...s.slot.pokemons.cards, ...s.slot.energies.cards, ...s.slot.trainers.cards]) {
      if (c instanceof TrainerCard && c.useWhenInPlay) names.add(c.name);
    }
    for (const n of names) {
      const action = new UseTrainerInPlayAction(id, s.target, n);
      if (accepts(state, action)) out.push({ key: `tip|${n}|${s.code}`, action });
    }
  }
  return out;
}

// ---------------------------------------------------------------- prompts
//
// Each prompt type gets a "space": the items a pick can take, and a check of a complete answer.
// Multi-pick answers are built in canonical order (item indices non-decreasing), so each
// distinct answer is reachable by exactly one sequence of picks. `relaxed` checks a partial
// answer against the constraints that only get tighter as picks are added (everything but the
// minimum count), which prunes the search for completions.

function withOptions(prompt, patch, fn) {
  const saved = prompt.options;
  prompt.options = Object.assign({}, saved, patch);
  try { return fn(); } finally { prompt.options = saved; }
}

function safeValidate(prompt, raw, state) {
  try {
    const decoded = prompt.decode(raw, state);
    if (decoded === null && raw !== null) return false;
    return prompt.validate(decoded, state) !== false;
  } catch (e) {
    if (e instanceof GameError) return false;
    throw e;
  }
}

// A multi-pick space: items[i] = {key, n (copies available)}; encode(picks) -> raw result.
// `ordered` = the first pick is free and the rest canonical (the setup prompt: first = Active).
function multiSpace({ items, encode, max, valid, relaxedValid, ordered = false, allowCancel, rawCancel = null }) {
  const memo = new Map();
  const counts = picks => { const c = new Array(items.length).fill(0); for (const p of picks) c[p]++; return c; };
  // Canonical order: picks are non-decreasing, except that when `ordered` the first pick is
  // free and only the picks after it are non-decreasing.
  const nextStart = picks => (picks.length === 0 || (ordered && picks.length === 1)) ? 0 : picks[picks.length - 1];
  function extendable(picks) {
    const k = picks.join(',');
    let v = memo.get(k);
    if (v !== undefined) return v;
    v = valid(picks);
    if (!v && picks.length < max) {
      const c = counts(picks);
      for (let i = nextStart(picks); i < items.length && !v; i++) {
        if (c[i] >= items[i].n) continue;
        const next = picks.concat(i);
        if (relaxedValid(next) && extendable(next)) v = true;
      }
    }
    memo.set(k, v);
    return v;
  }
  return {
    multi: true,
    options(picks) {
      const out = [];
      const c = counts(picks);
      for (let i = nextStart(picks); i < items.length; i++) {
        if (c[i] >= items[i].n || picks.length >= max) continue;
        const next = picks.concat(i);
        if (relaxedValid(next) && extendable(next)) out.push({ key: 'pick|' + items[i].key, pick: i });
      }
      if (valid(picks)) out.push({ key: 'done', raw: encode(picks) });
      if (picks.length === 0 && allowCancel) out.push({ key: 'cancel', raw: rawCancel });
      return out;
    },
  };
}

function chooseCardsSpace(prompt, state) {
  const cards = prompt.cards.cards;
  const o = prompt.options;
  const secret = o.isSecret;
  const groups = [];         // {key, idx: [indices]}
  const byName = new Map();
  cards.forEach((card, i) => {
    if (o.blocked.includes(i) || !FilterUtils.match(card, prompt.filter)) return;
    const name = secret ? '?' : card.fullName;
    let g = byName.get(name);
    if (!g) { g = { key: name, idx: [] }; byName.set(name, g); groups.push(g); }
    g.idx.push(i);
  });
  const encode = picks => {
    const used = new Array(groups.length).fill(0);
    return picks.map(g => groups[g].idx[used[g]++]);
  };
  const ordered = prompt.message === GameMessage.CHOOSE_STARTING_POKEMONS;
  return multiSpace({
    items: groups.map(g => ({ key: g.key, n: g.idx.length })),
    encode, max: o.max, ordered, allowCancel: o.allowCancel && safeValidate(prompt, null, state),
    valid: picks => safeValidate(prompt, encode(picks), state),
    relaxedValid: picks => withOptions(prompt, { min: 0 }, () => safeValidate(prompt, encode(picks), state)),
  });
}

function choosePokemonSpace(prompt, state) {
  const me = playerOf(state, prompt.playerId);
  const o = prompt.options;
  const blocked = new Set(o.blocked.map(targetKey));
  const items = allSlots(state, me).filter(s => occupied(s.slot)
    && (prompt.playerType === PlayerType.ANY || s.target.player === prompt.playerType)
    && prompt.slots.includes(s.target.slot) && !blocked.has(targetKey(s.target)));
  const encode = picks => picks.map(i => items[i].target);
  return multiSpace({
    items: items.map(s => ({ key: s.code, n: 1 })),
    encode, max: o.max, allowCancel: o.allowCancel,
    valid: picks => safeValidate(prompt, encode(picks), state),
    relaxedValid: picks => withOptions(prompt, { min: 0 }, () => safeValidate(prompt, encode(picks), state)),
  });
}

function chooseEnergySpace(prompt, state) {
  const groups = [];
  const byName = new Map();
  prompt.energy.forEach((e, i) => {
    const name = e.card.fullName + '|' + e.provides.join('');
    let g = byName.get(name);
    if (!g) { g = { key: e.card.fullName, idx: [] }; byName.set(name, g); groups.push(g); }
    g.idx.push(i);
  });
  const encode = picks => {
    const used = new Array(groups.length).fill(0);
    return picks.map(g => groups[g].idx[used[g]++]);
  };
  return multiSpace({
    items: groups.map(g => ({ key: g.key, n: g.idx.length })),
    encode, max: prompt.energy.length, allowCancel: prompt.options.allowCancel,
    valid: picks => safeValidate(prompt, encode(picks), state),
    relaxedValid: () => true,
  });
}

function attachEnergySpace(prompt, state) {
  const me = playerOf(state, prompt.playerId);
  const o = prompt.options;
  const cards = prompt.cardList.cards;
  const blockedTo = new Set(o.blockedTo.map(targetKey));
  const targets = allSlots(state, me).filter(s => occupied(s.slot)
    && (prompt.playerType === PlayerType.ANY || s.target.player === prompt.playerType)
    && prompt.slots.includes(s.target.slot) && !blockedTo.has(targetKey(s.target)));
  const groups = [];
  const byName = new Map();
  cards.forEach((card, i) => {
    if (o.blocked.includes(i) || !FilterUtils.match(card, prompt.filter)) return;
    let g = byName.get(card.fullName);
    if (!g) { g = { key: card.fullName, idx: [] }; byName.set(card.fullName, g); groups.push(g); }
    g.idx.push(i);
  });
  // Items are (card group, target); copies of a group are shared across its targets.
  const items = [];
  groups.forEach((g, gi) => targets.forEach(t => items.push({ key: `${g.key}>${t.code}`, n: g.idx.length, g: gi, t })));
  const encode = picks => {
    const used = new Array(groups.length).fill(0);
    return picks.map(i => ({ to: items[i].t.target, index: groups[items[i].g].idx[used[items[i].g]++] }));
  };
  const groupOk = picks => {
    const used = new Array(groups.length).fill(0);
    for (const i of picks) if (++used[items[i].g] > groups[items[i].g].idx.length) return false;
    return true;
  };
  return multiSpace({
    items: items.map(it => ({ key: it.key, n: it.n })),
    encode, max: Math.min(o.max, cards.length), allowCancel: o.allowCancel,
    valid: picks => groupOk(picks) && safeValidate(prompt, encode(picks), state),
    relaxedValid: picks => groupOk(picks) && withOptions(prompt, { min: 0 }, () => safeValidate(prompt, encode(picks), state)),
  });
}

function moveEnergySpace(prompt, state) {
  const me = playerOf(state, prompt.playerId);
  const o = prompt.options;
  const inScope = s => occupied(s.slot) && (prompt.playerType === PlayerType.ANY || s.target.player === prompt.playerType)
    && prompt.slots.includes(s.target.slot);
  const blockedFrom = new Set(o.blockedFrom.map(targetKey));
  const blockedTo = new Set(o.blockedTo.map(targetKey));
  const slots = allSlots(state, me).filter(inScope);
  // Items are (source slot, energy card group in it, destination slot). Each card moves once.
  const sources = [];
  for (const s of slots) {
    if (blockedFrom.has(targetKey(s.target))) continue;
    const bm = o.blockedMap.find(b => targetKey(b.source) === targetKey(s.target));
    const groups = new Map();
    s.slot.energies.cards.forEach((card, i) => {
      if ((bm && bm.blocked.includes(i)) || !FilterUtils.match(card, prompt.filter)) return;
      if (!groups.has(card.fullName)) groups.set(card.fullName, []);
      groups.get(card.fullName).push(i);
    });
    for (const [name, idx] of groups) sources.push({ s, name, idx });
  }
  const items = [];
  sources.forEach((src, si) => slots.forEach(t => {
    if (t === src.s || blockedTo.has(targetKey(t.target))) return;
    items.push({ key: `${src.s.code}:${src.name}>${t.code}`, n: src.idx.length, si, t });
  }));
  const encode = picks => {
    const used = new Array(sources.length).fill(0);
    return picks.map(i => ({ from: sources[items[i].si].s.target, to: items[i].t.target, index: sources[items[i].si].idx[used[items[i].si]++] }));
  };
  const sourceOk = picks => {
    const used = new Array(sources.length).fill(0);
    for (const i of picks) if (++used[items[i].si] > sources[items[i].si].idx.length) return false;
    return true;
  };
  const max = o.max === undefined ? sources.reduce((a, s) => a + s.idx.length, 0) : o.max;
  const countOk = picks => picks.length >= o.min && picks.length <= max;
  return multiSpace({
    items: items.map(it => ({ key: it.key, n: it.n })),
    encode, max, allowCancel: o.allowCancel,
    valid: picks => sourceOk(picks) && countOk(picks) && safeValidate(prompt, encode(picks), state),
    relaxedValid: picks => sourceOk(picks) && picks.length <= max,
  });
}

function moveDamageSpace(prompt, state) {
  const me = playerOf(state, prompt.playerId);
  const o = prompt.options;
  const inScope = s => occupied(s.slot) && (prompt.playerType === PlayerType.ANY || s.target.player === prompt.playerType)
    && prompt.slots.includes(s.target.slot);
  const blockedFrom = new Set(o.blockedFrom.map(targetKey));
  const blockedTo = new Set(o.blockedTo.map(targetKey));
  const slots = allSlots(state, me).filter(inScope);
  const cap = new Map(prompt.maxAllowedDamage.map(d => [targetKey(d.target), d.damage]));
  const items = [];
  for (const f of slots) {
    if (blockedFrom.has(targetKey(f.target)) || f.slot.damage <= 0) continue;
    for (const t of slots) {
      if (t === f || blockedTo.has(targetKey(t.target))) continue;
      items.push({ key: `${f.code}>${t.code}`, n: f.slot.damage / 10, f, t });
    }
  }
  const encode = picks => picks.map(i => ({ from: items[i].f.target, to: items[i].t.target }));
  const damageOk = picks => {
    const d = new Map(slots.map(s => [s, s.slot.damage]));
    for (const i of picks) {
      d.set(items[i].f, d.get(items[i].f) - 10);
      d.set(items[i].t, d.get(items[i].t) + 10);
      if (d.get(items[i].f) < 0) return false;
      const c = cap.get(targetKey(items[i].t.target));
      if (c !== undefined && d.get(items[i].t) > c) return false;
    }
    return true;
  };
  const total = slots.reduce((a, s) => a + s.slot.damage / 10, 0);
  const max = o.max === undefined ? total : o.max;
  return multiSpace({
    items: items.map(it => ({ key: it.key, n: it.n })),
    encode, max, allowCancel: o.allowCancel,
    valid: picks => damageOk(picks) && safeValidate(prompt, encode(picks), state),
    relaxedValid: picks => damageOk(picks) && picks.length <= max,
  });
}

function putDamageSpace(prompt, state) {
  const me = playerOf(state, prompt.playerId);
  const o = prompt.options;
  const blocked = new Set(o.blocked.map(targetKey));
  const slots = allSlots(state, me).filter(s => occupied(s.slot)
    && (prompt.playerType === PlayerType.ANY || s.target.player === prompt.playerType)
    && prompt.slots.includes(s.target.slot) && !blocked.has(targetKey(s.target)));
  const cap = new Map(prompt.maxAllowedDamage.map(d => [targetKey(d.target), d.damage]));
  const n = prompt.damage / 10;
  const encode = picks => {
    const m = new Map();
    for (const i of picks) m.set(i, (m.get(i) || 0) + 10);
    return [...m.entries()].map(([i, damage]) => ({ target: slots[i].target, damage }));
  };
  const capOk = picks => encode(picks).every(r => {
    const c = cap.get(targetKey(r.target));
    return c === undefined || r.damage <= c;
  });
  return multiSpace({
    items: slots.map(s => ({ key: s.code, n })),
    encode, max: n, allowCancel: o.allowCancel,
    valid: picks => picks.length === n && capOk(picks) && safeValidate(prompt, encode(picks), state),
    relaxedValid: picks => picks.length <= n && capOk(picks),
  });
}

// Order cards: picks in sequence are the new order (order matters, so no canonical sorting).
function orderCardsSpace(prompt) {
  const cards = prompt.cards.cards;
  const groups = [];
  const byName = new Map();
  cards.forEach((card, i) => {
    let g = byName.get(card.fullName);
    if (!g) { g = { key: card.fullName, idx: [] }; byName.set(card.fullName, g); groups.push(g); }
    g.idx.push(i);
  });
  const encode = picks => {
    const used = new Array(groups.length).fill(0);
    return picks.map(g => groups[g].idx[used[g]++]);
  };
  return {
    multi: true,
    options(picks) {
      const used = new Array(groups.length).fill(0);
      for (const g of picks) used[g]++;
      const out = [];
      if (picks.length === cards.length) out.push({ key: 'done', raw: encode(picks) });
      else groups.forEach((g, i) => { if (used[i] < g.idx.length) out.push({ key: 'pick|' + g.key, pick: i }); });
      if (picks.length === 0 && prompt.options.allowCancel) out.push({ key: 'cancel', raw: null });
      return out;
    },
  };
}

// Single-step prompts: every option is a complete answer.
function singleSpace(prompt, state) {
  const out = [];
  const add = (key, raw) => { if (safeValidate(prompt, raw, state)) out.push({ key, raw }); };
  switch (prompt.type) {
    case 'Choose attack': {
      prompt.cards.forEach((card, index) => {
        const names = new Set();
        const ea = prompt.options.enableAbility || {};
        for (const p of card.powers) if ((ea.useWhenInPlay && p.useWhenInPlay) || (ea.useFromHand && p.useFromHand) || (ea.useFromDiscard && p.useFromDiscard)) names.add(p.name);
        if (prompt.options.enableAttack) for (const a of card.attacks) names.add(a.name);
        for (const name of names) add(`res|${card.fullName}|${name}`, { index, name });
      });
      if (prompt.options.allowCancel) add('cancel', null);
      break;
    }
    case 'Select':
      prompt.values.forEach((v, i) => add(`res|${i}`, i));
      if (prompt.options.allowCancel) out.push({ key: 'cancel', raw: null });
      break;
    case 'Confirm':
      out.push({ key: 'res|yes', raw: true }, { key: 'res|no', raw: false });
      break;
    case 'Show cards':
      out.push({ key: 'res|ok', raw: true });
      if (prompt.options.allowCancel) out.push({ key: 'cancel', raw: null });
      break;
    case 'Alert':
      out.push({ key: 'res|ok', raw: true });
      break;
    default:
      throw new Error('no option space for prompt type ' + prompt.type);
  }
  return { multi: false, options: () => out };
}

function promptSpace(prompt, state) {
  switch (prompt.type) {
    case 'Choose cards': return chooseCardsSpace(prompt, state);
    case 'Choose pokemon': return choosePokemonSpace(prompt, state);
    case 'Choose energy': return chooseEnergySpace(prompt, state);
    case 'Attach energy': return attachEnergySpace(prompt, state);
    case 'Move energy': return moveEnergySpace(prompt, state);
    case 'Move damage': return moveDamageSpace(prompt, state);
    case 'Put damage': return putDamageSpace(prompt, state);
    case 'Order cards': return orderCardsSpace(prompt, state);
    default: return singleSpace(prompt, state);
  }
}

// The prompt types the environment answers itself: no information to act on, or randomness.
const AUTO_PROMPTS = new Set(['Coin flip', 'Shuffle deck', 'Choose prize']);

module.exports = { turnOptions, promptSpace, AUTO_PROMPTS, safeValidate, allSlots, canonicalCode, occupied, isTargetedTrainer };
