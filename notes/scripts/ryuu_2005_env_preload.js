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
const { S, cm } = require('../../env/engine.js');
const decksModule = require('../../env/decks.js');

const EX = S.exSets;
for (const set of [EX.setRubyAndSapphire, EX.setSandstorm, EX.setFireredAndLeafgreen, EX.setDeoxys, EX.setEmerald]) {
  if (!set) throw new Error('engine lacks a 2005 set (needs the worlds-2005 branch; RYUU_PLAY=' + process.env.RYUU_PLAY + ')');
  cm.defineSet(set);
}

// Archive card names -> the engine printing that plays them. Lanette's Net Search in the list is the
// Emerald printing (ex9-77), identical in text to the Sandstorm card the engine has (ex2-87).
const PRINTING = {
  'Birds': {
    'Zapdos ex': 'Zapdos ex RG', 'Moltres ex': 'Moltres ex RG', 'Kangaskhan': 'Kangaskhan RG', 'Wobbuffet': 'Wobbuffet SS',
    'Rayquaza': 'Rayquaza ★ DX', "Lanette's Net Search": "Lanette's Net Search SS", 'Scott': 'Scott EM',
    "Mr Stone's Project": "Mr. Stone's Project EM", 'EXP ALL': 'EXP.ALL RG', 'Battle Frontier': 'Battle Frontier EM',
    'Fire Energy': 'Fire Energy RS', 'Lightning Energy': 'Lightning Energy RS', 'Psychic Energy': 'Psychic Energy RS',
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
