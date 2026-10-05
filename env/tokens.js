// Token encoder for the scalable policy (plan item A4.2): the state as a set of card tokens, and
// each legal option as a candidate the policy scores with a pointer head.
//
// Cards are ids into the card table (env/tools/card_features.js, notes/data/cards/pool.json),
// so the network's card representation comes from card features and rules text, not from a
// fixed vocabulary of the decks it trained on.
//
// Tokens (at most MAX_TOK), as card id, kind and an auxiliary small integer:
//   0        GLOBAL: numeric context in `glob` (turn, sizes, flags, open prompt)
//   1..12    SLOT: my Active, Bench 0-4, then the opponent's; card = top Pokemon (0 if empty);
//            numeric features in `slots`
//   then     UNDER (card beneath an evolved Pokemon), ENERGY / TOOL (attached, aux = slot),
//            HAND, MY_DISCARD, OPP_DISCARD, MY_UNSEEN (decklist minus visible), OPP_DECKLIST,
//            STADIUM, PROMPT (cards listed by the open prompt), PICKED (picked so far):
//            one token per distinct card, aux = number of copies
// Candidates (at most MAX_CAND), one per option, as [verb, card, slot1, slot2, name, extra]:
//   slots 1..12 as above, 13 = an empty Bench slot, 14 = from hand, 15 = from discard; names are
//   attack and Power names of the pool.
'use strict';
const fs = require('fs');
const path = require('path');
const { C } = require('./engine.js');
const { allSlots } = require('./legal.js');

const MAX_TOK = 128;     // measured: mean 74, max 115 over 36k decisions
const MAX_CAND = 48;    // measured: max 29 options
const KIND = { PAD: 0, GLOBAL: 1, SLOT: 2, UNDER: 3, ENERGY: 4, TOOL: 5, HAND: 6, MY_DISCARD: 7, OPP_DISCARD: 8,
  MY_UNSEEN: 9, OPP_DECKLIST: 10, STADIUM: 11, PROMPT: 12, PICKED: 13 };
const VERB = { pass: 1, attach: 2, basic: 3, evolve: 4, trainer: 5, retreat: 6, attack: 7, power: 8, stadium: 9, tip: 10,
  pick_card: 11, pick_slot: 12, pick_attach: 13, pick_move_energy: 14, pick_move_damage: 15, done: 16, cancel: 17,
  res_attack: 18, res_select: 19, res_yes: 20, res_no: 21, res_ok: 22 };
const SLOT_CODES = ['A', 'B0', 'B1', 'B2', 'B3', 'B4', 'oA', 'oB0', 'oB1', 'oB2', 'oB3', 'oB4'];
const SLOT_ID = new Map(SLOT_CODES.map((c, i) => [c, i + 1]));
SLOT_ID.set('E', 13);
const CONDITIONS = [C.SpecialCondition.PARALYZED, C.SpecialCondition.CONFUSED, C.SpecialCondition.ASLEEP,
  C.SpecialCondition.POISONED, C.SpecialCondition.BURNED];
const PROMPT_TYPES = ['Choose cards', 'Choose pokemon', 'Choose energy', 'Attach energy', 'Move energy',
  'Move damage', 'Put damage', 'Order cards', 'Choose attack', 'Select', 'Confirm', 'Show cards', 'Alert'];
const HASH = 8, MSG_HASH = 32;
const SLOT_F = 1 + 1 + 1 + 1 + CONDITIONS.length + 1 + 1 + HASH + 1;   // 20
const GLOB_F = 3 + 2 * (4 + 4 + HASH) + (PROMPT_TYPES.length + 1) + MSG_HASH + 1;   // 99

function hash(s, n) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return (h >>> 0) % n;
}
const q = x => Math.max(0, Math.min(255, Math.round(x * 48)));   // byte = round(48 x)

class TokenEncoder {
  constructor(tableFile = path.join(__dirname, '..', 'notes', 'data', 'cards', 'pool.json')) {
    const table = JSON.parse(fs.readFileSync(tableFile, 'utf8')).cards;
    this.cardId = new Map(table.map(c => [c.fullName, c.id]));
    this.byName = new Map();
    for (const c of table) if (!this.byName.has(c.name)) this.byName.set(c.name, c.id);
    const names = new Set();
    for (const c of table) { for (const a of c.attacks) names.add(a.name); for (const p of c.powers) names.add(p.name); }
    this.names = [...names];
    this.nameId = new Map(this.names.map((n, i) => [n, i + 1]));
    this.numCards = table.length;
    this.MAX_TOK = MAX_TOK; this.MAX_CAND = MAX_CAND; this.SLOT_F = SLOT_F; this.GLOB_F = GLOB_F;
    this.sizes = { tokCard: MAX_TOK, tokKind: MAX_TOK, tokAux: MAX_TOK, glob: GLOB_F, slots: 12 * SLOT_F, cand: MAX_CAND * 6 };
  }

  id(card) { return card ? (this.cardId.get(card.fullName) || 0) : 0; }

  // -> { tokCard Int16Array, tokKind Uint8Array, tokAux Uint8Array, glob Uint8Array,
  //      slots Uint8Array (12 x SLOT_F), cand Int16Array (MAX_CAND x 6), nTok, nCand }
  encode(game, playerId, decks, options) {
    const state = game.state;
    const me = state.players.find(p => p.id === playerId);
    const opp = state.players.find(p => p.id !== playerId);
    const turn = state.turn;
    const out = {
      tokCard: new Int16Array(MAX_TOK), tokKind: new Uint8Array(MAX_TOK), tokAux: new Uint8Array(MAX_TOK),
      glob: new Uint8Array(GLOB_F), slots: new Uint8Array(12 * SLOT_F), cand: new Int16Array(MAX_CAND * 6), nTok: 0, nCand: 0,
    };
    let n = 0;
    const push = (card, kind, aux) => {
      if (n >= MAX_TOK) { out.overflow = true; return; }
      out.tokCard[n] = card; out.tokKind[n] = kind; out.tokAux[n] = Math.min(255, aux); n++;
    };
    const pushCounts = (cards, kind) => {
      const m = new Map();
      for (const c of cards) { const k = this.id(c); m.set(k, (m.get(k) || 0) + 1); }
      for (const [k, v] of m) push(k, kind, v);
    };

    push(0, KIND.GLOBAL, 0);
    const slots = allSlots(state, me);
    slots.forEach((s, i) => {
      const cards = s.slot.pokemons.cards;
      const top = cards.length ? cards[cards.length - 1] : null;
      push(this.id(top), KIND.SLOT, i);
      if (!top) return;
      const o = i * SLOT_F;
      out.slots[o] = q(1);
      out.slots[o + 1] = q(cards.length > 1 ? 1 : 0);
      out.slots[o + 2] = q(Math.round((top.hp || 0) / 10) / 12);
      out.slots[o + 3] = q(Math.round(s.slot.damage / 10) / 12);
      CONDITIONS.forEach((c, j) => { out.slots[o + 4 + j] = q(s.slot.specialConditions.includes(c) ? 1 : 0); });
      out.slots[o + 9] = q(s.slot.pokemonPlayedTurn >= turn ? 1 : 0);
      out.slots[o + 10] = q(s.slot.energies.cards.length / 4);
      for (const m of s.slot.marker.markers) out.slots[o + 11 + hash(m.name, HASH)] = q(1);
    });
    slots.forEach((s, i) => {
      const cards = s.slot.pokemons.cards;
      for (let k = 0; k < cards.length - 1; k++) push(this.id(cards[k]), KIND.UNDER, i);
      const e = new Map();
      for (const c of s.slot.energies.cards) { const k = this.id(c); e.set(k, (e.get(k) || 0) + 1); }
      for (const [k, v] of e) push(k, KIND.ENERGY, i * 8 + Math.min(v, 7));
      for (const c of s.slot.trainers.cards) push(this.id(c), KIND.TOOL, i);
    });
    pushCounts(me.hand.cards, KIND.HAND);
    pushCounts(me.discard.cards, KIND.MY_DISCARD);
    pushCounts(opp.discard.cards, KIND.OPP_DISCARD);
    if (decks && decks[me.id]) {
      const left = new Map();
      for (const name of decks[me.id]) left.set(name, (left.get(name) || 0) + 1);
      const seen = [...me.hand.cards, ...me.discard.cards, ...me.stadium.cards, ...me.supporter.cards];
      for (const s of [me.active, ...me.bench]) seen.push(...s.pokemons.cards, ...s.energies.cards, ...s.trainers.cards);
      for (const c of seen) if (left.has(c.fullName)) left.set(c.fullName, left.get(c.fullName) - 1);
      for (const [name, v] of left) if (v > 0) push(this.cardId.get(name) || 0, KIND.MY_UNSEEN, v);
    }
    if (decks && decks[opp.id]) {
      const m = new Map();
      for (const name of decks[opp.id]) m.set(name, (m.get(name) || 0) + 1);
      for (const [name, v] of m) push(this.cardId.get(name) || 0, KIND.OPP_DECKLIST, v);
    }
    const stadium = C.StateUtils.getStadiumCard(state);
    if (stadium) push(this.id(stadium), KIND.STADIUM, 0);

    // Open prompt: its type and message, the cards it lists, and what has been picked so far.
    const d = game.decision();
    const prompt = d && d.prompt;
    const g = out.glob;
    g[0] = q(Math.min(turn, 240) / 48);
    g[1] = q(state.players[state.activePlayer] === me ? 1 : 0);
    g[2] = q(state.phase === C.GamePhase.PLAYER_TURN ? 1 : 0);
    [me, opp].forEach((p, k) => {
      const o = 3 + k * (8 + HASH);
      g[o] = q(p.hand.cards.length / 24); g[o + 1] = q(p.deck.cards.length / 48);
      g[o + 2] = q(p.discard.cards.length / 48); g[o + 3] = q(p.prizes.reduce((a, z) => a + z.cards.length, 0) / 6);
      g[o + 4] = q(p.energyPlayedTurn === turn ? 1 : 0); g[o + 5] = q(p.retreatedTurn === turn ? 1 : 0);
      g[o + 6] = q(p.supporter.cards.length > 0 ? 1 : 0); g[o + 7] = q(p.stadiumPlayedTurn === turn ? 1 : 0);
      for (const m of p.marker.markers) g[o + 8 + hash(m.name, HASH)] = q(1);
    });
    const po = 3 + 2 * (8 + HASH);
    const t = prompt ? PROMPT_TYPES.indexOf(prompt.type) : -1;
    g[po + (t === -1 ? PROMPT_TYPES.length : t)] = q(1);
    if (prompt) {
      g[po + PROMPT_TYPES.length + 1 + hash(String(prompt.message), MSG_HASH)] = q(1);
      g[po + PROMPT_TYPES.length + 1 + MSG_HASH] = q(Math.min(game.picks.length, 12) / 12);
      const listed = prompt.cards ? (prompt.cards.cards || prompt.cards) : prompt.cardList ? prompt.cardList.cards : null;
      if (Array.isArray(listed) && !(prompt.options && prompt.options.isSecret)) pushCounts(listed, KIND.PROMPT);
      const picked = game.pickKeys().map(k => k.split(/[>:]/)).flat().map(part => this.cardId.get(part)).filter(Boolean);
      const m = new Map();
      for (const k of picked) m.set(k, (m.get(k) || 0) + 1);
      for (const [k, v] of m) push(k, KIND.PICKED, v);
    }
    out.nTok = n;

    // Candidates.
    const opts = options || (d ? d.options : []);
    const activeCard = me.active.getPokemonCard();
    opts.forEach((o, i) => {
      if (i >= MAX_CAND) { out.overflow = true; return; }
      const c = this.candidate(o.key, prompt, activeCard, state, me);
      out.cand.set(c, i * 6);
    });
    out.nCand = Math.min(opts.length, MAX_CAND);
    return out;
  }

  candidate(key, prompt, activeCard, state, me) {
    const [verb, a, b] = key.split('|');
    const slot = code => SLOT_ID.get(code) || 0;
    const card = name => this.cardId.get(name) || 0;
    switch (verb) {
      case 'pass': return [VERB.pass, 0, 0, 0, 0, 0];
      case 'attach': return [VERB.attach, card(a), slot(b), 0, 0, 0];
      case 'basic': return [VERB.basic, card(a), 13, 0, 0, 0];
      case 'evolve': return [VERB.evolve, card(a), slot(b), 0, 0, 0];
      case 'trainer': return [VERB.trainer, card(a), b === '-' ? 0 : slot(b), 0, 0, 0];
      case 'retreat': return [VERB.retreat, 0, slot(a), 0, 0, 0];
      case 'attack': return [VERB.attack, this.id(activeCard), 1, 0, this.nameId.get(a) || 0, 0];
      case 'power': {
        if (b.startsWith('H') || b.startsWith('D')) return [VERB.power, card(b.slice(1)), b[0] === 'H' ? 14 : 15, 0, this.nameId.get(a) || 0, 0];
        const s = allSlots(state, me).find(x => x.code === b);
        return [VERB.power, s ? this.id(s.slot.getPokemonCard()) : 0, slot(b), 0, this.nameId.get(a) || 0, 0];
      }
      case 'stadium': return [VERB.stadium, this.id(C.StateUtils.getStadiumCard(state)), 0, 0, 0, 0];
      case 'tip': return [VERB.tip, this.byName.get(a) || 0, slot(b), 0, 0, 0];
      case 'done': return [VERB.done, 0, 0, 0, 0, 0];
      case 'cancel': return [VERB.cancel, 0, 0, 0, 0, 0];
      case 'res':
        if (a === 'yes') return [VERB.res_yes, 0, 0, 0, 0, 0];
        if (a === 'no') return [VERB.res_no, 0, 0, 0, 0, 0];
        if (a === 'ok') return [VERB.res_ok, 0, 0, 0, 0, 0];
        if (b !== undefined) return [VERB.res_attack, card(a), 0, 0, this.nameId.get(b) || 0, 0];
        return [VERB.res_select, 0, 0, 0, 0, Number(a) + 1];
      case 'pick': {
        const item = key.slice(5);
        let m;
        if ((m = /^(o?[AB]\d?|E):(.+)>(o?[AB]\d?)$/.exec(item))) return [VERB.pick_move_energy, card(m[2]), slot(m[1]), slot(m[3]), 0, 0];
        if ((m = /^(.+)>(o?[AB]\d?)$/.exec(item))) {
          if (SLOT_ID.has(m[1])) return [VERB.pick_move_damage, 0, slot(m[1]), slot(m[2]), 0, 0];
          return [VERB.pick_attach, card(m[1]), slot(m[2]), 0, 0, 0];
        }
        if (SLOT_ID.has(item)) return [VERB.pick_slot, 0, slot(item), 0, 0, 0];
        return [VERB.pick_card, item === '?' ? 0 : card(item), 0, 0, 0, 0];
      }
      default: throw new Error('no candidate encoding for ' + key);
    }
  }
}

module.exports = { TokenEncoder, KIND, VERB, MAX_TOK, MAX_CAND, SLOT_F, GLOB_F };
