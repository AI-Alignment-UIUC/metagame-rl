// The 24 archived July 2000 STS California decklists, as arrays of 60 card fullNames.
'use strict';
const path = require('path');
require('./engine.js');
const { buildArchivedDecks } = require('../notes/scripts/ryuu_sts_decks.js');

const CSV = path.join(__dirname, '..', 'notes', 'data', '2000-super-trainer-showdown-california', 'cards.csv');

let cache = null;
function archivedDecks() {
  if (!cache) cache = [...buildArchivedDecks(CSV).entries()].map(([name, cards]) => ({ name, cards }));
  return cache;
}

// Decks from a JSON file: [{ name, cards: [fullName x 60] }] (built decks, for A5).
function decksFromFile(file) {
  const list = JSON.parse(require('fs').readFileSync(file, 'utf8'));
  return (Array.isArray(list) ? list : list.decks).map(d => ({ name: d.name, cards: d.cards }));
}

module.exports = { archivedDecks, decksFromFile };
