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

module.exports = { archivedDecks };
