// Observation encoder and action indexing for the identity-indexed policy (plan item A1.3).
//
// Built from a card vocabulary (the 56 cards the 2000 STS field plays, or any other pool), so
// the same code serves a fixed matchup, every deck in the field, or the full Base-Rocket pool.
//
// Observation, from the deciding player's point of view (that is not always the player whose
// turn it is: a player whose Active was knocked out picks the new one):
//   12 slots (mine: Active, Bench 0-4; then the opponent's), each:
//     occupied, top card one-hot (Pokemon + Trainers that sit in a slot), evolved,
//     HP and damage (in counters / 12), 5 special conditions, attached Energy counts,
//     attached Trainers and markers (hashed), played this turn
//   per player: hand, deck, discard and prize counts, this-turn flags, player markers
//   card-count vectors over the vocabulary: my hand, my discard, the opponent's discard,
//     my unseen cards (decklist minus everything visible: deck + prizes), the opponent's
//     decklist (zero if not given)
//   context: turn, whose turn, the Stadium in play, the open prompt (type, message, and what
//     has been picked so far)
// Hidden information stays hidden: the opponent's hand is a size, deck order and prizes are
// unknown to both players (my prizes are only known as part of "unseen").
//
// Every feature is a multiple of 1/48 (counts in quarters, HP and damage in counters / 12,
// sizes over 24 or 48), so encodeU8() stores observations exactly as round(48 * x) in a byte.
//
// Actions: every option key from legal.js maps to a fixed index, so a policy can output one
// logit per index and be masked to the options on offer. actionId() throws on a key outside
// the space, which the tests use to prove the space covers every option the game can offer.
'use strict';
const { C, cm } = require('./engine.js');
const { allSlots } = require('./legal.js');
const { PokemonCard, TrainerCard, EnergyCard, SpecialCondition, PlayerType } = C;

const SLOT_CODES = ['A', 'B0', 'B1', 'B2', 'B3', 'B4', 'oA', 'oB0', 'oB1', 'oB2', 'oB3', 'oB4'];
const PICK_SLOT_CODES = SLOT_CODES.concat(['E']);
const CONDITIONS = [SpecialCondition.PARALYZED, SpecialCondition.CONFUSED, SpecialCondition.ASLEEP,
  SpecialCondition.POISONED, SpecialCondition.BURNED];
const PROMPT_TYPES = ['Choose cards', 'Choose pokemon', 'Choose energy', 'Attach energy', 'Move energy',
  'Move damage', 'Put damage', 'Order cards', 'Choose attack', 'Select', 'Confirm', 'Show cards', 'Alert'];
const HASH_MARKERS = 8, HASH_TRAINERS = 4, HASH_MESSAGES = 32, MAX_SELECT = 8;

function hash(s, n) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0) % n;
}

class Encoder {
  // names: card fullNames in the vocabulary.
  constructor(names) {
    this.cards = names.map(n => {
      const c = cm.getCardByName(n);
      if (!c) throw new Error('unknown card ' + n);
      return c;
    });
    this.names = this.cards.map(c => c.fullName);
    this.cardIndex = new Map(this.names.map((n, i) => [n, i]));
    this.V = this.cards.length;
    const isSlotCard = c => c instanceof PokemonCard || (c instanceof TrainerCard && c.useWhenInPlay);
    this.slotCards = this.cards.filter(isSlotCard).map(c => c.fullName);
    this.slotIndex = new Map(this.slotCards.map((n, i) => [n, i]));
    this.energies = this.cards.filter(c => c instanceof EnergyCard).map(c => c.fullName);
    this.energyIndex = new Map(this.energies.map((n, i) => [n, i]));
    const attackNames = new Set(), powerNames = new Set();
    for (const c of this.cards) {
      if (!(c instanceof PokemonCard)) continue;
      c.attacks.forEach(a => attackNames.add(a.name));
      c.powers.forEach(p => powerNames.add(p.name));
    }
    this.attackNames = [...attackNames];
    this.powerNames = [...powerNames];
    this.buildLayout();
    this.buildActions();
  }

  // ------------------------------------------------------------ observation layout
  buildLayout() {
    let off = 0;
    const L = {};
    const take = (name, n) => { L[name] = off; off += n; };
    this.slotWidth = 1 + this.slotCards.length + 1 + 2 + CONDITIONS.length + this.energies.length + HASH_TRAINERS + HASH_MARKERS + 1;
    take('slots', 12 * this.slotWidth);
    this.playerWidth = 4 + 4 + HASH_MARKERS;
    take('players', 2 * this.playerWidth);
    for (const v of ['myHand', 'myDiscard', 'oppDiscard', 'myUnseen', 'oppDecklist']) take(v, this.V);
    take('global', 3 + this.V);
    take('promptType', PROMPT_TYPES.length + 1);
    take('promptMessage', HASH_MESSAGES);
    take('pickedCards', this.V);
    take('pickedSlots', PICK_SLOT_CODES.length);
    this.layout = L;
    this.obsSize = off;
  }

  // game: env Game; playerId: who decides; decks: { [playerId]: fullNames[] } (own decklist
  // is needed for "unseen"; the opponent's is optional).
  encode(game, playerId, decks = {}, out = new Float32Array(this.obsSize)) {
    out.fill(0);
    const L = this.layout;
    const state = game.state;
    const me = state.players.find(p => p.id === playerId);
    const opp = state.players.find(p => p.id !== playerId);
    const turn = state.turn;

    const slots = allSlots(state, me);
    slots.forEach((s, i) => this.encodeSlot(s.slot, turn, out, L.slots + i * this.slotWidth));

    [me, opp].forEach((p, i) => {
      const o = L.players + i * this.playerWidth;
      out[o] = p.hand.cards.length / 24;
      out[o + 1] = p.deck.cards.length / 48;
      out[o + 2] = p.discard.cards.length / 48;
      out[o + 3] = p.prizes.reduce((a, z) => a + z.cards.length, 0) / 6;
      out[o + 4] = p.energyPlayedTurn === turn ? 1 : 0;
      out[o + 5] = p.retreatedTurn === turn ? 1 : 0;
      out[o + 6] = p.supporter.cards.length > 0 ? 1 : 0;
      out[o + 7] = p.stadiumPlayedTurn === turn ? 1 : 0;
      for (const m of p.marker.markers) out[o + 8 + hash(m.name, HASH_MARKERS)] = 1;
    });

    this.countInto(me.hand.cards, out, L.myHand);
    this.countInto(me.discard.cards, out, L.myDiscard);
    this.countInto(opp.discard.cards, out, L.oppDiscard);
    if (decks[me.id]) {
      // Unseen = decklist minus every card of mine I can see (hand, discard, in play).
      const o = L.myUnseen;
      for (const n of decks[me.id]) { const k = this.cardIndex.get(n); if (k !== undefined) out[o + k] += 1 / 4; }
      const seen = [...me.hand.cards, ...me.discard.cards, ...me.stadium.cards, ...me.supporter.cards];
      for (const s of [me.active, ...me.bench]) seen.push(...s.pokemons.cards, ...s.energies.cards, ...s.trainers.cards);
      // Cards of mine sitting in the opponent's zones (rare) stay counted as unseen.
      for (const c of seen) { const k = this.cardIndex.get(c.fullName); if (k !== undefined) out[o + k] = Math.max(0, out[o + k] - 1 / 4); }
    }
    if (decks[opp.id]) this.countInto(decks[opp.id].map(n => ({ fullName: n })), out, L.oppDecklist);

    const g = L.global;
    out[g] = Math.min(turn, 240) / 48;
    out[g + 1] = state.players[state.activePlayer] === me ? 1 : 0;
    out[g + 2] = state.phase === C.GamePhase.PLAYER_TURN ? 1 : 0;
    const stadium = C.StateUtils.getStadiumCard(state);
    if (stadium) { const k = this.cardIndex.get(stadium.fullName); if (k !== undefined) out[g + 3 + k] = 1; }

    const d = game.decision();
    const prompt = d && d.prompt;
    const t = prompt ? PROMPT_TYPES.indexOf(prompt.type) : -1;
    out[L.promptType + (t === -1 ? PROMPT_TYPES.length : t)] = 1;
    if (prompt) {
      out[L.promptMessage + hash(String(prompt.message), HASH_MESSAGES)] = 1;
      for (const key of game.pickKeys()) this.pickInto(key, out);
    }
    return out;
  }

  encodeSlot(slot, turn, out, o) {
    const cards = slot.pokemons.cards;
    if (cards.length === 0) return;
    const top = cards[cards.length - 1];
    out[o] = 1;
    const k = this.slotIndex.get(top.fullName);
    if (k !== undefined) out[o + 1 + k] = 1;
    let p = o + 1 + this.slotCards.length;
    out[p++] = cards.length > 1 ? 1 : 0;
    out[p++] = Math.round((top.hp || 0) / 10) / 12;
    out[p++] = Math.round(slot.damage / 10) / 12;
    for (const c of CONDITIONS) out[p++] = slot.specialConditions.includes(c) ? 1 : 0;
    for (const e of slot.energies.cards) {
      const j = this.energyIndex.get(e.fullName);
      if (j !== undefined) out[p + j] += 1 / 4;
    }
    p += this.energies.length;
    for (const tr of slot.trainers.cards) out[p + hash(tr.fullName, HASH_TRAINERS)] += 1;
    p += HASH_TRAINERS;
    for (const m of slot.marker.markers) out[p + hash(m.name, HASH_MARKERS)] = 1;
    p += HASH_MARKERS;
    out[p] = slot.pokemonPlayedTurn >= turn ? 1 : 0;
  }

  // The observation as bytes: round(48 * x), exact for this encoding (see the header).
  encodeU8(game, playerId, decks = {}, out = new Uint8Array(this.obsSize)) {
    const f = this.scratch || (this.scratch = new Float32Array(this.obsSize));
    this.encode(game, playerId, decks, f);
    for (let i = 0; i < f.length; i++) {
      const v = Math.round(f[i] * 48);
      out[i] = v < 0 ? 0 : v > 255 ? 255 : v;
    }
    return out;
  }

  countInto(cards, out, o) {
    for (const c of cards) {
      const k = this.cardIndex.get(c.fullName);
      if (k !== undefined) out[o + k] += 1 / 4;
    }
  }

  // Picks so far in a multi-pick prompt: cards named in the pick, and slots it touches.
  pickInto(key, out) {
    const L = this.layout;
    for (const part of key.split(/[|>:]/)) {
      const k = this.cardIndex.get(part);
      if (k !== undefined) out[L.pickedCards + k] += 1 / 4;
      const s = PICK_SLOT_CODES.indexOf(part);
      if (s !== -1) out[L.pickedSlots + s] = 1;
    }
  }

  // ------------------------------------------------------------ actions
  buildActions() {
    const ids = new Map();
    const add = key => { if (!ids.has(key)) ids.set(key, ids.size); };
    const own = SLOT_CODES.slice(0, 6);
    add('pass');
    for (const c of this.cards) {
      const n = c.fullName;
      if (c instanceof EnergyCard) own.forEach(s => add(`attach|${n}|${s}`));
      if (c instanceof PokemonCard) {
        if (c.stage === C.Stage.BASIC) add(`basic|${n}`);
        else own.forEach(s => add(`evolve|${n}|${s}`));
        c.powers.forEach(pw => {
          own.forEach(s => add(`power|${pw.name}|${s}`));
          add(`power|${pw.name}|H${n}`);
          add(`power|${pw.name}|D${n}`);
        });
      }
      if (c instanceof TrainerCard) {
        add(`trainer|${n}|-`);
        own.concat(['E']).forEach(s => add(`trainer|${n}|${s}`));
        if (c.useWhenInPlay) own.forEach(s => add(`tip|${c.name}|${s}`));
      }
    }
    own.slice(1).forEach(s => add(`retreat|${s}`));
    this.attackNames.forEach(a => add(`attack|${a}`));
    add('stadium');
    // Prompt answers.
    add('done');
    add('cancel');
    for (const n of this.names) add(`pick|${n}`);
    add('pick|?');
    PICK_SLOT_CODES.forEach(s => add(`pick|${s}`));
    for (const e of this.energies) SLOT_CODES.forEach(s => add(`pick|${e}>${s}`));
    for (const e of this.energies) {
      for (const f of SLOT_CODES) for (const t of SLOT_CODES) if (f !== t) add(`pick|${f}:${e}>${t}`);
    }
    for (const f of SLOT_CODES) for (const t of SLOT_CODES) if (f !== t) add(`pick|${f}>${t}`);
    for (const n of this.names) {
      const c = cm.getCardByName(n);
      if (!(c instanceof PokemonCard)) continue;
      for (const a of [...c.attacks, ...c.powers]) add(`res|${n}|${a.name}`);
    }
    for (let i = 0; i < MAX_SELECT; i++) add(`res|${i}`);
    add('res|yes'); add('res|no'); add('res|ok');
    this.actionIds = ids;
    this.actionKeys = [...ids.keys()];
    this.actionSize = ids.size;
  }

  actionId(key) {
    const id = this.actionIds.get(key);
    if (id === undefined) throw new Error('action key outside the action space: ' + key);
    return id;
  }
}

module.exports = { Encoder, SLOT_CODES, PROMPT_TYPES };
