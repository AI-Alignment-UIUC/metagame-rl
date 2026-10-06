// The RL environment API (plan item A1.4): a seeded game wrapped with the encoder.
//
//   const env = new Env(encoder);
//   let t = env.reset(deckA, deckB, seed);   // { done, playerId, obs, legal } or { done, winner }
//   while (!t.done) t = env.step(chooseFrom(t.legal, t.obs, t.playerId));
//
// Both seats are driven through the same calls: each step reports which player decides next
// (a player answering a prompt is not always the one whose turn it is). `legal` lists the
// action ids on offer; `obs` is from the deciding player's point of view. With the same seed
// and the same actions a game replays exactly.
'use strict';
const { Game } = require('./game.js');

class Env {
  // showOpponentDecklist: put the opponent's decklist in the observation (deck-conditioned
  // play, plan item A4); the player's own decklist is always used, for its unseen cards.
  constructor(encoder, { showOpponentDecklist = true, u8 = false } = {}) {
    this.encoder = encoder;
    this.showOpponentDecklist = showOpponentDecklist;
    this.u8 = u8;
    this.game = null;
    this.current = null;
  }

  // backup: keep the engine's rollback clone (for seats that play engine actions directly).
  reset(deckA, deckB, seed, { backup = false } = {}) {
    this.game = new Game(deckA, deckB, seed, { backup });
    this.decklists = { 1: deckA, 2: deckB };
    return this.observe();
  }

  observe() {
    const g = this.game;
    const d = g.decision();
    if (d === null) {
      this.current = null;
      return { done: true, winner: g.winner, steps: g.steps, error: g.error };
    }
    const decks = this.visibleDecks(d.playerId);
    // Token encoders (env/tokens.js) score the options themselves: actions are option indices.
    const tokens = typeof this.encoder.actionId !== 'function';
    // Past MAX_CAND options the token encoder has no slot to score them, so they are not offered
    // (built decks can reach ~50+ options; the archived ones at most 29).
    const legal = tokens ? d.options.slice(0, this.encoder.MAX_CAND).map((_, i) => i)
      : d.options.map(o => this.encoder.actionId(o.key));
    if (tokens && d.options.length > this.encoder.MAX_CAND) this.truncated = (this.truncated || 0) + 1;
    const obs = tokens ? this.encoder.encode(g, d.playerId, decks, d.options)
      : this.u8 ? this.encoder.encodeU8(g, d.playerId, decks) : this.encoder.encode(g, d.playerId, decks);
    this.current = { playerId: d.playerId, legal, options: d.options };
    return { done: false, playerId: d.playerId, obs, legal };
  }

  // The decklists the deciding player may see: their own, and the opponent's if shown.
  visibleDecks(playerId) {
    const decks = { [playerId]: this.decklists[playerId] };
    if (this.showOpponentDecklist) {
      const other = playerId === 1 ? 2 : 1;
      decks[other] = this.decklists[other];
    }
    return decks;
  }

  step(actionId) {
    const i = this.current ? this.current.legal.indexOf(actionId) : -1;
    if (i === -1) throw new Error('action ' + actionId + ' is not on offer');
    this.game.step(i);
    return this.observe();
  }
}

module.exports = { Env };
