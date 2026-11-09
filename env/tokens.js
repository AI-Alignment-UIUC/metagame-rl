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
//            numeric features in `slots`. An opponent's face-down Pokemon (Challenge! TR, until both
//            players finish) reads as occupied with card 0 and no HP, the same id as a hidden pick in the history
//   then     UNDER (card beneath an evolved Pokemon), ENERGY / TOOL (attached, aux = slot),
//            HAND, MY_DISCARD, OPP_DISCARD, MY_UNSEEN (decklist minus visible), OPP_DECKLIST,
//            STADIUM, PROMPT (cards listed by the open prompt), PICKED (picked so far):
//            one token per distinct card, aux = number of copies
//            With canon = 1 (rl/token_model.py state_canon) the prompt's references are flags on the zone tokens instead: a
//            listed card sets 32 in the aux of its HAND / MY_DISCARD / MY_UNSEEN (deck or prizes) / OPP_DISCARD token, a card
//            picked so far 64, the seat's own resolving Trainer 128; copies are capped at 31 (bits 0-4). A listed card with no
//            zone token still gets a PROMPT token, a pick with none a PICKED token, a source in neither HAND nor MY_DISCARD
//            a PROMPT token (aux 128).
//   then     with history = W > 0 (log #76): the action history of the last W turns, newest first, at most
//            HIST_MAX: HIST_ME / HIST_OPP, card = the card the action names (0 for none, and for the opponent's
//            prompt answers, which may pick hidden cards), aux = verb * 8 + turns ago (capped at 7)
// Candidates (at most MAX_CAND), one per option, as [verb, card, slot1, slot2, name, extra]:
//   slots 1..12 as above, 13 = an empty Bench slot, 14 = from hand, 15 = from discard; names are
//   attack and Power names of the pool.
//   With origin = 1 (rl/token_model.py cand_origin) a pick_card row carries the source zone of the card it names in extra:
//   1 hand, 2 deck (or prizes), 3 discard (either), found by identity among the open prompt's listed cards; 0 if unlisted.
//   With chain = K > 0 (the chain head, rl/token_model.py chain): at most MAX_CAND - K options, and the last K rows
//   hold the deciding player's own decisions of this game turn (chainRows), oldest first and right-aligned.
'use strict';
const fs = require('fs');
const path = require('path');
const { C } = require('./engine.js');
const { allSlots } = require('./legal.js');

// Upper bounds, not budgets: the player sees the whole state and every legal option (log #68). A state or
// an option list past them ends the game as an engine error (env/env.js), never a silent cut. Measured:
// tokens mean 74, max 115 on the archived decks, over 128 in 0.03% of decisions on built decks; options max
// 29 on the archived decks, 39 on built ones, and a card search offers one option per distinct card name in
// the zone (up to 60 + done + cancel). The GPU server trims each batch to its longest state and option list
// (rl/remote.py), so the bounds cost padding only in the ONNX path.
const MAX_TOK = 256;
const MAX_CAND = 128;
const KIND = { PAD: 0, GLOBAL: 1, SLOT: 2, UNDER: 3, ENERGY: 4, TOOL: 5, HAND: 6, MY_DISCARD: 7, OPP_DISCARD: 8,
  MY_UNSEEN: 9, OPP_DECKLIST: 10, STADIUM: 11, PROMPT: 12, PICKED: 13, HIST_ME: 14, HIST_OPP: 15 };
const HIST_MAX = 32;
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
const GLOB_F = 3 + 2 * (4 + 4 + HASH) + (PROMPT_TYPES.length + 1) + MSG_HASH + 1;   // 82
// The glob bytes holding the deciding player's and the opponent's prizes left (8 per prize): the
// potential of the prize shaping in rl/train.py shape_rewards, the env's one game-specific reward input.
const PRIZE_GLOB = [3 + 3, 3 + (4 + 4 + HASH) + 3];

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
    this.history = 0;        // turns of action history encoded (0 = none, as before log #76)
    this.chain = 0;          // the chain head's rows (0 = none): the last `chain` candidate rows
    this.origin = 0;         // 1 = a pick_card row's extra is its source zone (cand_origin)
    this.canon = 0;          // 1 = one token per card per zone, the prompt's references as aux flags (state_canon)
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
    const canon = this.canon > 0;
    const zone = new Map();    // canon: kind -> Map(card id -> token index), to set the prompt's flags on
    const cnt = v => canon ? Math.min(31, v) : v;
    const note = (kind, id) => {
      if (!canon || n >= MAX_TOK) return;
      if (!zone.has(kind)) zone.set(kind, new Map());
      zone.get(kind).set(id, n);
    };
    const flag = (kind, id, bit) => {
      const i = canon && zone.has(kind) ? zone.get(kind).get(id) : undefined;
      if (i === undefined) return false;
      out.tokAux[i] |= bit;
      return true;
    };
    const pushCounts = (cards, kind) => {
      const m = new Map();
      for (const c of cards) { const k = this.id(c); m.set(k, (m.get(k) || 0) + 1); }
      for (const [k, v] of m) { note(kind, k); push(k, kind, cnt(v)); }
    };

    push(0, KIND.GLOBAL, 0);
    const slots = allSlots(state, me);
    // Face down (pokemons.isPublic false, set only by Challenge! TR): its owner knows the card, the other player
    // only that a card is there.
    const hidden = s => !s.mine && s.slot.pokemons.isPublic === false;
    slots.forEach((s, i) => {
      const cards = s.slot.pokemons.cards;
      const top = cards.length ? cards[cards.length - 1] : null;
      push(hidden(s) ? 0 : this.id(top), KIND.SLOT, i);
      if (!top) return;
      const o = i * SLOT_F;
      out.slots[o] = q(1);
      out.slots[o + 1] = q(cards.length > 1 ? 1 : 0);
      out.slots[o + 2] = hidden(s) ? 0 : q(Math.round((top.hp || 0) / 10) / 12);
      out.slots[o + 3] = q(Math.round(s.slot.damage / 10) / 12);
      CONDITIONS.forEach((c, j) => { out.slots[o + 4 + j] = q(s.slot.specialConditions.includes(c) ? 1 : 0); });
      out.slots[o + 9] = q(s.slot.pokemonPlayedTurn >= turn ? 1 : 0);
      out.slots[o + 10] = q(s.slot.energies.cards.length / 4);
      for (const m of s.slot.marker.markers) out.slots[o + 11 + hash(m.name, HASH)] = q(1);
    });
    slots.forEach((s, i) => {
      const cards = s.slot.pokemons.cards;
      for (let k = 0; k < cards.length - 1; k++) push(hidden(s) ? 0 : this.id(cards[k]), KIND.UNDER, i);
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
      for (const [name, v] of left) {
        if (v <= 0) continue;
        const k = this.cardId.get(name) || 0;
        note(KIND.MY_UNSEEN, k);
        push(k, KIND.MY_UNSEEN, cnt(v));
      }
    }
    if (decks && decks[opp.id]) {
      const m = new Map();
      for (const name of decks[opp.id]) m.set(name, (m.get(name) || 0) + 1);
      for (const [name, v] of m) push(this.cardId.get(name) || 0, KIND.OPP_DECKLIST, cnt(v));
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
      let shown = Array.isArray(listed) && !(prompt.options && prompt.options.isSecret) ? listed : null;
      if (canon && shown) {            // each listed card flags its zone token (by identity: the prompt lists the zone's own cards)
        const home = [[me.hand.cards, KIND.HAND], [me.discard.cards, KIND.MY_DISCARD], [me.deck.cards, KIND.MY_UNSEEN],
          [opp.discard.cards, KIND.OPP_DISCARD], ...me.prizes.map(z => [z.cards, KIND.MY_UNSEEN])];
        shown = shown.filter(c => { const h = home.find(x => x[0].includes(c)); return !(h && flag(h[1], this.id(c), 32)); });
      }
      if (shown) pushCounts(shown, KIND.PROMPT);
      const picked = game.pickKeys().map(k => k.split(/[>:]/)).flat().map(part => this.cardId.get(part)).filter(Boolean);
      const m = new Map();
      for (const k of picked) m.set(k, (m.get(k) || 0) + 1);
      const ZONES = [KIND.HAND, KIND.MY_DISCARD, KIND.MY_UNSEEN, KIND.OPP_DISCARD, KIND.PROMPT];
      for (const [k, v] of m) {        // canon: a pick flags the token it was listed on (else its hand / discard / unseen token)
        if (canon) {
          const at = ZONES.filter(z => zone.has(z) && zone.get(z).has(k)).map(z => zone.get(z).get(k));
          const i = at.find(j => out.tokAux[j] & 32) ?? at[0];
          if (i !== undefined) { out.tokAux[i] |= 64; continue; }
        }
        push(k, KIND.PICKED, cnt(v));
      }
      // canon: the card whose effect is resolving, the seat's own Trainer (the test of env/tools/probe_worker.js X1)
      if (canon && game.chain && game.chain.key.startsWith('trainer|') && state.players[state.activePlayer].id === playerId) {
        const sid = this.cardId.get(game.chain.key.split('|')[1]) || 0;
        const inPlay = me.supporter.cards.some(c => this.id(c) === sid);     // a Supporter resolves from its own zone
        if (!(!inPlay && (flag(KIND.HAND, sid, 128) || flag(KIND.MY_DISCARD, sid, 128))) && !flag(KIND.PROMPT, sid, 128)) {
          note(KIND.PROMPT, sid);
          push(sid, KIND.PROMPT, 128);
        }
      }
    }
    if (this.history > 0 && game.history) {
      let h = 0;
      for (let i = game.history.length - 1; i >= 0 && h < HIST_MAX; i--) {
        const e = game.history[i];
        const ago = turn - e.t;
        if (ago >= this.history) break;
        const mine = e.p === playerId;
        const card = mine || !e.pr ? (e.c ? this.cardId.get(e.c) || 0 : 0) : 0;
        push(card, mine ? KIND.HIST_ME : KIND.HIST_OPP, (VERB[e.v] || 0) * 8 + Math.min(Math.max(ago, 0), 7));
        h++;
      }
    }
    out.nTok = n;

    // Candidates.
    const opts = options || (d ? d.options : []);
    const activeCard = me.active.getPokemonCard();
    let origin = null;       // origin: full name -> source zone code of the open prompt's listed cards
    if (this.origin > 0 && prompt) {
      const listed = prompt.cards ? (prompt.cards.cards || prompt.cards) : prompt.cardList ? prompt.cardList.cards : null;
      if (Array.isArray(listed) && !(prompt.options && prompt.options.isSecret)) {
        const home = [[me.hand.cards, 1], [me.deck.cards, 2], ...me.prizes.map(z => [z.cards, 2]), [me.discard.cards, 3], [opp.discard.cards, 3]];
        origin = new Map();
        for (const c of listed) { const h = home.find(x => x[0].includes(c)); if (h && !origin.has(c.fullName)) origin.set(c.fullName, h[1]); }
      }
    }
    opts.forEach((o, i) => {
      if (i >= MAX_CAND) { out.overflow = true; return; }
      const c = this.candidate(o.key, prompt, activeCard, state, me);
      if (origin && c[0] === VERB.pick_card && c[1]) c[5] = origin.get(o.key.slice(5)) || 0;
      out.cand.set(c, i * 6);
    });
    out.nCand = Math.min(opts.length, MAX_CAND);
    if (this.chain > 0) {
      if (opts.length > MAX_CAND - this.chain) out.overflow = true;
      const rows = this.chainRows(game, playerId, prompt, activeCard, state, me);
      rows.forEach((r, j) => out.cand.set(r, (MAX_CAND - rows.length + j) * 6));
    }
    return out;
  }

  // The chain head's rows: the deciding player's own decisions of this game turn (game.history entries with an option
  // key), oldest first, at most this.chain of them, each in the candidate encoding of its option key against the
  // current state. A row whose encoding has no card takes the card the decision named (a slot pick's Pokemon, a
  // retreat's Active), and a slot pick whose slot no longer holds the Pokemon picked loses its slot reference. The role
  // goes in extra (+ 64 x role): 1 the move that opened the open prompt (the turn's latest move, if it is this
  // player's), 2 an answer given since, 3 an earlier move, 4 an earlier answer. If the window would cut the opener, it is
  // kept first.
  chainRows(game, playerId, prompt, activeCard, state, me) {
    const hist = game.history || [];
    let i = hist.length;
    while (i > 0 && hist[i - 1].t === state.turn) i--;
    const own = [];
    let open = -1;
    for (let j = hist.length - 1; j >= i; j--) {          // the opener: the turn's latest move, if it is this player's
      if (!hist[j].pr) { if (prompt && hist[j].p === playerId && hist[j].k) open = j; break; }
    }
    const slots = allSlots(state, me);
    for (let j = i; j < hist.length; j++) {
      const e = hist[j];
      if (e.p !== playerId || !e.k) continue;
      const r = this.candidate(e.k, prompt, activeCard, state, me);
      if (!r[1]) r[1] = this.cardId.get(e.kc || e.c) || 0;
      if (r[0] === VERB.pick_slot || r[0] === VERB.pick_move_damage) {
        const at = r[0] === VERB.pick_slot ? 2 : 3;     // the picked slot (pick_move_damage: its target)
        const s = r[at] >= 1 && r[at] <= 12 ? slots.find(x => x.code === SLOT_CODES[r[at] - 1]) : null;
        const top = s && s.slot.getPokemonCard();
        if (s && (!top || top.fullName !== e.kc)) r[at] = 0;
      }
      const role = j === open ? 1 : open >= 0 && j > open ? 2 : e.pr ? 4 : 3;
      r[5] += 64 * role;
      own.push({ r, opener: j === open });
    }
    const K = this.chain;
    if (own.length <= K) return own.map(x => x.r);
    const o = own.findIndex(x => x.opener);
    const tail = own.slice(own.length - K);
    return o >= 0 && o < own.length - K ? [own[o].r, ...tail.slice(1).map(x => x.r)] : tail.map(x => x.r);
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

module.exports = { TokenEncoder, KIND, VERB, MAX_TOK, MAX_CAND, SLOT_F, GLOB_F, PRIZE_GLOB, HIST_MAX };
