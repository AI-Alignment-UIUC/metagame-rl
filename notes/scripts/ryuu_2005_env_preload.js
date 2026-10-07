// Preload that points the Node environment (env/) at the Worlds 2005 "Birds" list, for verification
// runs only: the archived list is the answer key, and nothing here feeds a training run.
//
// It registers the engine's 2005-legal EX sets with the CardManager (env/engine.js registers only the
// Base-era format) and makes env/decks.js archivedDecks() return the decks named in DECKS_2005
// (comma-separated: "Birds", or "Birds,2000:<substring of a 2000 STS deck name>" for a cross-era smoke
// test), built from the archived list in notes/data/2005-season-ptcgarchive/decks.json.
//
// Every env tool that forks workers passes the environment on, so:
//   RYUU_PLAY=<engine on worlds-2005> DECKS_2005=Birds NODE_OPTIONS="--require ./notes/scripts/ryuu_2005_env_preload.js" \
//     node env/tools/verify_enumerator.js --games 50 --workers 2
//
// Note: the game rules stay env/engine.js's 2000 rules object (first-turn draw/Supporter defaults,
// fossilsAsStarters off); 2005 rules are not separately configured yet.
'use strict';
const path = require('path');
const fs = require('fs');
const engine = require('../../env/engine.js');
const { S, cm } = engine;

// ---- Flip-capped legality trial (verification runs only; env/ itself is left unchanged).
// env/engine.js decides legality by replaying an action on a clone with every coin flip heads, then
// every flip tails. A "flip until you get tails" attack (Rayquaza Star's Spiral Rush, Linoone RS's
// Continuous Headbutt) never ends under all heads, so the trial loops forever (reproduced: accepts()
// on Spiral Rush did not return in 60 s). Here a trial flips the forced side at most MAX_SAME_FLIPS
// times in a row, then the other side once. Copied from env/engine.js trial() apart from that cap.
const MAX_SAME_FLIPS = 32;
for (const m of ['legal.js', 'oracle.js']) {
  if (Object.keys(require.cache).some(k => k.endsWith(require('path').join('env', m)))) {
    throw new Error('ryuu_2005_env_preload.js must load before env/' + m + ' (it replaces engine.accepts/tryAction)');
  }
}
if (engine.MAX_SAME_FLIPS === undefined) {   // env/engine.js caps flips itself since log #46; keep this only for older checkouts
  const { C, newStore } = engine;
  const TURN_ENDED = { turnEnded: true };
  const reduceEffectUntilTurnEnds = function (state, effect) {
    if (effect instanceof C.EndTurnEffect) throw TURN_ENDED;
    return C.Store.prototype.reduceEffect.call(this, state, effect);
  };
  const reduceWithoutBackupOrCheck = function (state, action) {
    this.promptItems.length = 0;
    const DIST = require('path').join(engine.RYUU, 'packages', 'common', 'dist', 'cjs', 'store');
    const { setupPhaseReducer } = require(require('path').join(DIST, 'reducers', 'setup-reducer.js'));
    const { playCardReducer } = require(require('path').join(DIST, 'reducers', 'play-card-reducer.js'));
    const { playerTurnReducer } = require(require('path').join(DIST, 'reducers', 'player-turn-reducer.js'));
    state = setupPhaseReducer(this, state, action);
    state = playCardReducer(this, state, action);
    state = playerTurnReducer(this, state, action);
    this.resolveWaitItems();
    return state;
  };
  const trial = (state, action, flip, from) => {
    const store = newStore(C.deepClone(state, [C.Card]));
    if (from !== undefined) store.cardRanks = from.cardRanks;
    store.reduceEffect = reduceEffectUntilTurnEnds;
    store.reduce = reduceWithoutBackupOrCheck;
    let flips = 0, same = 0;
    try {
      store.dispatch(action);
      for (;;) {
        const p = store.state.prompts.find(q => q.result === undefined
          && (q.type === 'Coin flip' || q.type === 'Shuffle deck' || q.type === 'Choose prize'));
        if (!p) break;
        let result;
        if (p.type === 'Coin flip') {
          result = same < MAX_SAME_FLIPS ? flip : !flip;
          same = same < MAX_SAME_FLIPS ? same + 1 : 0;
          flips++;
        } else if (p.type === 'Shuffle deck') {
          const player = store.state.players.find(q => q.id === p.playerId);
          result = player.deck.cards.map((_, i) => i);
        } else {
          result = p.decode(Array.from({ length: p.options.count }, (_, i) => i), store.state);
        }
        store.dispatch(new C.ResolvePromptAction(p.id, result));
      }
      return { ok: true, flips, state: store.state };
    } catch (e) {
      if (e === TURN_ENDED) return { ok: true, flips };
      if (e instanceof C.GameError) return { ok: false, flips };
      throw e;
    }
  };
  engine.tryAction = (state, action, from) => {
    const heads = trial(state, action, true, from);
    if (!heads.ok) return { ok: false, after: null };
    if (heads.flips > 0 && !trial(state, action, false, from).ok) return { ok: false, after: null };
    return { ok: true, after: heads.state || null };
  };
  engine.accepts = (state, action, from) => engine.tryAction(state, action, from).ok;
  engine.stateAfter = (state, action, from) => {
    const r = trial(state, action, true, from);
    return r.ok ? (r.state || null) : null;
  };
}

const decksModule = require('../../env/decks.js');

const EX = S.exSets;
if (!EX.setDeoxys || !EX.setEmerald) {
  throw new Error('engine lacks the 2005 sets (needs the worlds-2005 branch; RYUU_PLAY=' + process.env.RYUU_PLAY + ')');
}
// Every EX set the engine exports is 2005-legal (RS through Emerald).
for (const set of Object.values(EX).filter(Array.isArray)) cm.defineSet(set);

// Archive card names -> the engine printing that plays them. Lanette's Net Search in the list is the
// Emerald printing (ex9-77), identical in text to the Sandstorm card the engine has (ex2-87).
const PRINTING = {
  'Birds': {
    'Zapdos ex': 'Zapdos ex RG', 'Moltres ex': 'Moltres ex RG', 'Kangaskhan': 'Kangaskhan RG', 'Wobbuffet': 'Wobbuffet SS',
    'Rayquaza': 'Rayquaza ★ DX', "Lanette's Net Search": "Lanette's Net Search SS", 'Scott': 'Scott EM',
    "Mr Stone's Project": "Mr. Stone's Project EM", 'EXP ALL': 'EXP.ALL RG', 'Battle Frontier': 'Battle Frontier EM',
    'Fire Energy': 'Fire Energy RS', 'Lightning Energy': 'Lightning Energy RS', 'Psychic Energy': 'Psychic Energy RS',
  },
  // "Professor Oak's Research" in the list: the 2005-legal printing is FireRed & LeafGreen's
  // "Prof. Oak's Research" (ex6-98); Lanette's Net Search is the Emerald reprint of the SS card.
  'ZapTurnDos': {
    'Zapdos ex': 'Zapdos ex RG', 'Manectric': 'Manectric DX', 'Electrike': 'Electrike DX', 'Electrode': 'Electrode HL',
    'Voltorb': 'Voltorb HL', "Mr. Stone's Project": "Mr. Stone's Project EM", 'Scott': 'Scott EM',
    "Steven's Advice": "Steven's Advice HL", "Lanette's Net Search": "Lanette's Net Search SS",
    "Professor Oak's Research": "Prof. Oak's Research RG", 'Dual Ball': 'Dual Ball MA',
    'Pokemon Reversal': 'Pokemon Reversal RG', 'Super Scoop Up': 'Super Scoop Up RG', 'Master Ball': 'Master Ball DX',
    'Switch': 'Switch RG', 'Battle Frontier': 'Battle Frontier EM', 'Space Center': 'Space Center DX',
    'VS Seeker': 'VS Seeker RG', 'Lightning Energy': 'Lightning Energy RS',
  },
};
const clean = s => s.replace(/[‘’�]/g, "'");

function archived2005(title) {
  const file = path.join(__dirname, '..', 'data', '2005-season-ptcgarchive', 'decks.json');
  const deck = JSON.parse(fs.readFileSync(file, 'utf8')).find(d => d.title === title);
  if (!deck) throw new Error('no archived 2005 list ' + title);
  const map = PRINTING[title];
  if (!map) throw new Error('no engine printings mapped for ' + title);
  const cards = [];
  for (const [n, name] of deck.cards) {
    const full = map[clean(name)];
    if (!full || !cm.getCardByName(full)) throw new Error(title + ': no engine card for ' + name);
    for (let i = 0; i < n; i++) cards.push(full);
  }
  if (cards.length !== 60) throw new Error(title + ' has ' + cards.length + ' cards');
  return { name: '2005 ' + title, cards };
}

const wanted = (process.env.DECKS_2005 || 'Birds').split(',').map(s => s.trim()).filter(Boolean);
const original = decksModule.archivedDecks;
const decks = wanted.map(w => {
  if (w.startsWith('2000:')) {
    const d = original().find(x => x.name.toLowerCase().includes(w.slice(5).toLowerCase()));
    if (!d) throw new Error('no 2000 deck matches ' + w);
    return d;
  }
  return archived2005(w);
});
decksModule.archivedDecks = () => decks;
module.exports = { decks };
