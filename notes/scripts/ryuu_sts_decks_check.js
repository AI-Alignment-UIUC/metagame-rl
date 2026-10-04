// End-to-end check: build every archived 2000 STS California deck inside ryuu-play.
//
// Maps each archived card name onto a registered ryuu-play card (via ryuu_sts_decks.js) and
// starts a real game with that list on both sides. The engine enforces 60 cards, the 4-copy
// limit and a Basic Pokemon in the opening hand, so a deck that starts is a deck the
// simulator can actually play.
//
// Run: node ryuu_sts_decks_check.js <path-to-ryuu-play> [event-dir ...]
'use strict';
const fs = require('fs');
const path = require('path');
const H = require('./ryuu_harness.js');
const { buildArchivedDecks } = require('./ryuu_sts_decks.js');

const DATA = path.join(__dirname, '..', 'data');
const events = process.argv.slice(3).length
  ? process.argv.slice(3)
  : [path.join(DATA, '2000-super-trainer-showdown-california')];

let total = 0, built = 0;
const problems = [];

for (const dir of events) {
  const file = path.join(dir, 'cards.csv');
  if (!fs.existsSync(file)) { console.error('missing ' + file); continue; }

  const issues = [];
  const decks = buildArchivedDecks(file, issues);
  const errored = issues.filter(i => i.error);
  const assumedBy = new Map(issues.filter(i => i.assumed).map(i => [i.key, i.assumed]));

  console.log('\n########## ' + path.basename(dir) + ' - ' + (decks.size + errored.length) + ' decks');

  for (const { key, error } of errored) {
    total++;
    problems.push(key + ': ' + error);
    console.log('  UNBUILDABLE ' + key.padEnd(52) + error);
  }

  for (const [key, names] of decks) {
    total++;
    try {
      const sim = new H.Simulator(new H.State(), {
        flipMode: H.BotFlipMode.ALL_HEADS,
        shuffleMode: H.BotShuffleMode.NO_SHUFFLE,
      });
      sim.dispatch(new H.AddPlayerAction(1, 'A', names));
      sim.dispatch(new H.AddPlayerAction(2, 'B', names));
      H.resolveAll(sim, { cards: p => { const i = p.cards.cards.findIndex(c => H.matches(c, p.filter)); return [i]; } });

      const me = sim.store.state.players[0];
      const inPlay = me.deck.cards.length + me.hand.cards.length
        + me.prizes.reduce((n, z) => n + z.cards.length, 0)
        + me.active.pokemons.cards.length
        + me.bench.reduce((n, s) => n + s.pokemons.cards.length, 0);
      if (inPlay !== 60) throw new Error('card count did not survive setup: ' + inPlay);

      built++;
      const assumed = assumedBy.get(key);
      console.log('  ok           ' + key.padEnd(52) + names.length + ' cards, opening Active '
        + me.active.getPokemonCard().fullName
        + (assumed ? '   [printing assumed: ' + assumed.join('; ') + ']' : ''));
    } catch (e) {
      const msg = (e && (e.message || e.code)) || JSON.stringify(e);
      problems.push(key + ': ' + msg);
      console.log('  ENGINE ERROR ' + key.padEnd(52) + msg);
    }
  }
}

console.log('\n' + built + '/' + total + ' archived decks build and start in ryuu-play');
if (problems.length) {
  console.log('\nproblems:');
  problems.forEach(p => console.log('  ' + p));
}
process.exit(built === total ? 0 : 1);
