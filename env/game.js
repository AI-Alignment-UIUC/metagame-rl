// One seeded headless game: the environment loop around the engine.
//
//   const g = new Game(deckA, deckB, seed);
//   while (!g.done) {
//     const d = g.decision();          // { playerId, options: [{ key, ... }], prompt? }
//     g.step(pickIndex(d.options));
//   }
//   g.winner                           // 1, 2, 0 (draw) or -1 (cut off / broken)
//
// Coin flips, deck shuffles and prize picks (face down, so there is nothing to decide) are
// answered here from the game's own seeded RNG; everything else is a decision. The same seed
// and the same choices replay the same game exactly.
'use strict';
const { C, newStore, newState } = require('./engine.js');
const { Rng } = require('./rng.js');
const { turnOptions, promptSpace, AUTO_PROMPTS } = require('./legal.js');
const { sameState } = require('./fingerprint.js');

const MAX_STEPS = 5000;

class Game {
  constructor(deckA, deckB, seed, { backup = false } = {}) {
    this.rng = new Rng(seed);
    this.store = newStore(newState(), { backup });
    this.steps = 0;
    this.picks = [];         // picks so far in a multi-pick prompt answer
    this.pickedKeys = [];    // their option keys
    this.space = null;       // option space of the open prompt, kept across its picks
    this.spaceFor = -1;      // id of the prompt `space` belongs to
    this.cached = null;      // decision() result until the next step
    this.error = null;       // set if the engine threw on an offered option
    this.chain = null;       // { base, log, key }: replay record since the last attack or Power
    this.deadEnds = [];      // [{ base, key }]: main-phase options found to lead only to a no-op cancel
    this.dispatch(new C.AddPlayerAction(1, 'A', deckA));
    this.dispatch(new C.AddPlayerAction(2, 'B', deckB));
  }

  get state() { return this.store.state; }

  // Option keys picked so far in the open prompt, without the "pick|" prefix.
  pickKeys() { return this.pickedKeys.map(k => k.slice(5)); }

  get done() {
    return this.error !== null || this.steps >= MAX_STEPS || this.state.phase === C.GamePhase.FINISHED;
  }

  // 1 or 2 for the winning player id, 0 for a draw, -1 if the game was cut off or broke.
  get winner() {
    if (this.error !== null || this.state.phase !== C.GamePhase.FINISHED) return -1;
    switch (this.state.winner) {
      case C.GameWinner.PLAYER_1: return this.state.players[0].id;
      case C.GameWinner.PLAYER_2: return this.state.players[1].id;
      case C.GameWinner.DRAW: return 0;
      default: return -1;
    }
  }

  openPrompt() {
    let best;
    for (const p of this.state.prompts) {
      if (p.result === undefined && (best === undefined || p.id < best.id)) best = p;
    }
    return best;
  }

  decision() {
    if (this.cached) return this.cached;
    if (this.done) return null;
    const prompt = this.openPrompt();
    let d;
    if (prompt) {
      if (this.spaceFor !== prompt.id) {
        this.space = promptSpace(prompt, this.state);
        this.spaceFor = prompt.id;
        this.picks = [];
        this.pickedKeys = [];
      }
      let options = this.space.options(this.picks);
      if (REPLAY_CHECKED.has(prompt.type) && this.chain) {
        options = options.filter(o => o.raw === undefined || o.raw === null || this.replayAccepts(prompt, o.raw));
      }
      // An answer that only undoes the action that opened this prompt (cancel, or done with
      // nothing picked) is a no-op: once an action is started it is finished, or a policy can
      // cycle start -> undo forever.
      if (this.picks.length === 0) {
        const noop = options.filter(o => (o.key === 'cancel' || (o.key === 'done' && emptyRaw(o.raw))) && this.answerIsNoop(prompt, o.raw));
        if (noop.length > 0) {
          if (noop.length < options.length) options = options.filter(o => !noop.includes(o));
          // Only no-op answers are left (the replay check removed every other answer): the
          // action that opened the prompt is a dead end, so it is not offered again in that state.
          else if (this.chain.key) this.deadEnds.push({ base: this.chain.base, key: this.chain.key });
        }
      }
      d = { playerId: prompt.playerId, prompt, options };
    } else {
      let options = turnOptions(this.state, this.store);
      if (this.deadEnds.length > 0) {
        this.deadEnds = this.deadEnds.filter(e => sameState(this.state, e.base));
        const dead = new Set(this.deadEnds.map(e => e.key));
        options = options.filter(o => !dead.has(o.key));
      }
      d = { playerId: this.state.players[this.state.activePlayer].id, prompt: null, options };
    }
    if (d.options.length === 0) {
      this.error = new Error(`no legal option at step ${this.steps} (${prompt ? prompt.type + ' / ' + prompt.message : 'main phase'})`);
      return null;
    }
    this.cached = d;
    return d;
  }

  step(i) {
    const d = this.decision();
    if (d === null) throw new Error('step() on a finished game');
    const opt = d.options[i];
    if (opt === undefined) throw new Error(`option ${i} out of range (${d.options.length})`);
    this.cached = null;
    this.steps++;
    this.lastKey = (d.prompt ? d.prompt.type + ': ' : '') + opt.key;
    if (opt.pick !== undefined) {
      this.picks = this.picks.concat(opt.pick);
      this.pickedKeys = this.pickedKeys.concat(opt.key);
      return;
    }
    if (d.prompt) {
      this.picks = [];
      this.spaceFor = -1;
      if (this.chain) this.chain.log.push({ promptId: d.prompt.id, raw: opt.raw });
      this.dispatch(new C.ResolvePromptAction(d.prompt.id, d.prompt.decode(opt.raw, this.state)));
    } else {
      // Snapshot before actions that can open a prompt of their own (pass, attach, basic and
      // evolve can't), for replay checks of what follows.
      this.chain = /^(trainer|power|retreat|attack|stadium|tip)|/.test(opt.key) || opt.key === 'stadium'
        ? { base: C.deepClone(this.state, [C.Card]), log: [{ action: opt.action }], noop: new Map(), key: opt.key } : null;
      this.dispatch(opt.action);
    }
  }

  // Play an engine action chosen outside the option list (SimpleBot plays this way). Any
  // half-built prompt answer is dropped.
  applyEngineAction(action) {
    this.cached = null;
    this.steps++;
    this.picks = [];
    this.pickedKeys = [];
    this.spaceFor = -1;
    this.chain = null;
    this.lastKey = 'engine:' + action.type;
    this.dispatch(action);
  }

  dispatch(action) {
    try {
      this.store.dispatch(action);
      this.resolveAutoPrompts();
    } catch (e) {
      this.error = e;
    }
  }

  resolveAutoPrompts() {
    for (;;) {
      const prompt = this.state.prompts.find(p => p.result === undefined && AUTO_PROMPTS.has(p.type));
      if (!prompt) return;
      const raw = this.autoAnswer(prompt);
      if (this.chain) this.chain.log.push({ promptId: prompt.id, raw });
      this.store.dispatch(new C.ResolvePromptAction(prompt.id, prompt.decode(raw, this.state)));
    }
  }

  autoAnswer(prompt) {
    const player = this.state.players.find(p => p.id === prompt.playerId);
    switch (prompt.type) {
      case 'Coin flip':
        return this.rng.int(2) === 0;
      case 'Shuffle deck':
        return this.rng.permutation(player.deck.cards.length);
      case 'Choose prize': {
        const prizes = player.prizes.filter(p => p.cards.length > 0);
        return this.rng.permutation(prizes.length).slice(0, prompt.options.count);
      }
      default:
        throw new Error('not an automatic prompt: ' + prompt.type);
    }
  }
}

// A copy of this game for search, taken at a main-phase decision (no prompt open). With
// `viewer` set, what that player can't see is re-dealt at random first: their own deck and
// prizes are shuffled together, and the opponent's hand, deck and prizes likewise, keeping
// every zone's size. The copy shares no state with this game.
Game.prototype.clone = function (rng, viewer) {
  if (this.state.prompts.some(p => p.result === undefined)) throw new Error('clone() needs a stable state');
  const g = Object.create(Game.prototype);
  g.rng = rng || this.rng.clone();
  g.store = newStore(C.deepClone(this.state, [C.Card]));
  g.store.cardRanks = this.store.cardRanks;
  g.steps = this.steps;
  g.picks = []; g.pickedKeys = []; g.space = null; g.spaceFor = -1; g.cached = null; g.error = null; g.chain = null; g.deadEnds = [];
  if (viewer !== undefined) {
    for (const p of g.state.players) {
      const zones = p.id === viewer ? [p.deck, ...p.prizes] : [p.hand, p.deck, ...p.prizes];
      const pool = zones.flatMap(z => z.cards);
      const order = g.rng.permutation(pool.length);
      let k = 0;
      for (const z of zones) z.cards = z.cards.map(() => pool[order[k++]]);
    }
  }
  return g;
};

// Answers whose legality is decided in card code after the prompt resolves (a copied attack or
// Power that can't be used), so decode + validate can't see it. Checked by replaying the chain
// of actions since the attack or Power that opened the prompt, on a copy of the state before it.
const REPLAY_CHECKED = new Set(['Choose attack']);

// True if answering `prompt` with `raw` leaves the state exactly as it was before the action
// that started this chain. Cached per prompt and answer.
Game.prototype.answerIsNoop = function (prompt, raw) {
  if (!this.chain) return false;
  const key = prompt.id + ':' + JSON.stringify(raw);
  if (this.chain.noop.has(key)) return this.chain.noop.get(key);
  const after = this.replayState(prompt, raw);
  const noop = after !== null && sameState(after, this.chain.base);
  this.chain.noop.set(key, noop);
  return noop;
};

Game.prototype.cancelIsNoop = function (prompt) { return this.answerIsNoop(prompt, null); };

// An answer that picks nothing.
function emptyRaw(raw) {
  return raw === null || (Array.isArray(raw) && raw.length === 0);
}

// The state after replaying the chain and answering `prompt` with `raw`, or null if rejected.
Game.prototype.replayState = function (prompt, raw) {
  const store = newStore(C.deepClone(this.chain.base, [C.Card]));
  store.cardRanks = this.store.cardRanks;
  const answer = (id, r) => {
    const p = store.state.prompts.find(q => q.id === id);
    store.dispatch(new C.ResolvePromptAction(id, p.decode(r, store.state)));
  };
  try {
    for (const e of this.chain.log) {
      if (e.action) store.dispatch(e.action);
      else answer(e.promptId, e.raw);
    }
    answer(prompt.id, raw);
    return store.state;
  } catch (e) {
    if (e instanceof C.GameError) return null;
    throw e;
  }
};

Game.prototype.replayAccepts = function (prompt, raw) {
  const store = newStore(C.deepClone(this.chain.base, [C.Card]));
  store.cardRanks = this.store.cardRanks;
  const answer = (id, r) => {
    const p = store.state.prompts.find(q => q.id === id);
    store.dispatch(new C.ResolvePromptAction(id, p.decode(r, store.state)));
  };
  try {
    for (const e of this.chain.log) {
      if (e.action) store.dispatch(e.action);
      else answer(e.promptId, e.raw);
    }
    answer(prompt.id, raw);
    return true;
  } catch (e) {
    if (e instanceof C.GameError) return false;
    throw e;
  }
};

module.exports = { Game, MAX_STEPS };
