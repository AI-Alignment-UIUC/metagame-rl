#!/usr/bin/env node
// Coverage of a scraped event's card pool against a ryuu-play checkout.
//
// Reads notes/data/<event>/cards.csv (produced by meta_aggregate.py) and the card classes
// under packages/sets/src/base-sets, and reports which cards have no implementation, which
// exist as a file but are not registered in their set index, and how many decks are buildable
// verbatim under each fix.
//
// Usage:
//   node ryuu_pool_coverage.js <path-to-ryuu-play> [event-dir ...]
//   node ryuu_pool_coverage.js ../../ryuu-play            # defaults to both 2000 STS events
'use strict';
const fs = require('fs');
const path = require('path');

const RYUU = process.argv[2] || process.env.RYUU_PLAY;
if (!RYUU) { console.error('usage: node ryuu_pool_coverage.js <path-to-ryuu-play> [event-dir ...]'); process.exit(1); }
const DATA = path.join(__dirname, '..', 'data');
const events = process.argv.slice(3).length ? process.argv.slice(3)
  : ['2000-super-trainer-showdown-california', '2000-super-trainer-showdown-new-jersey']
    .map(e => path.join(DATA, e));

const norm = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
  .toLowerCase().replace(/[^a-z0-9]/g, '');

// ---------------------------------------------------------------- ryuu-play card index
const SRC = path.join(RYUU, 'packages', 'sets', 'src', 'base-sets');
const SETS = ['set-base', 'set-jungle', 'set-fossil', 'set-team-rocket', 'set-promos']
  .filter(s => fs.existsSync(path.join(SRC, s)));
const impl = new Map();      // normalized name -> [set codes]
const unregistered = new Set();

for (const set of SETS) {
  const dir = path.join(SRC, set);
  const index = fs.readFileSync(path.join(dir, 'index.ts'), 'utf8');
  for (const file of fs.readdirSync(dir)) {
    if (!file.endsWith('.ts') || file === 'index.ts') continue;
    const src = fs.readFileSync(path.join(dir, file), 'utf8');
    const m = src.match(/public name[^=]*=\s*'((?:[^'\\]|\\.)*)'/);
    if (!m) continue;
    const name = m[1].replace(/\\(.)/g, '$1');
    const k = norm(name);
    // a card is live only if its index.ts both imports and instantiates it
    const stem = file.replace(/\.ts$/, '');
    const imported = new RegExp(`^\\s*import\\s*\\{[^}]*\\}\\s*from\\s*'\\./${stem}'`, 'm').test(index);
    if (imported) { if (!impl.has(k)) impl.set(k, []); impl.get(k).push(set); }
    else unregistered.add(k);
  }
}
console.log(`ryuu-play base-era card files: ${impl.size + unregistered.size} distinct names, ` +
  `${impl.size} registered, ${unregistered.size} present but commented out of a set index` +
  (unregistered.size ? ` (${[...unregistered].join(', ')})` : ''));

// Archive annotations that name a printing which is a genuinely different card from the
// same-named one in Base-Fossil-Rocket, mapped to the set folder that has to supply it.
const PRINTING_SET = { 'movie promo': 'set-promos', promo: 'set-promos' };

// ---------------------------------------------------------------- per event
function parseCsv(text) {
  const rows = [];
  let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n') { row.push(cell); rows.push(row); row = []; cell = ''; }
    else if (c !== '\r') cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const head = rows.shift();
  return rows.filter(r => r.length === head.length).map(r => Object.fromEntries(head.map((h, i) => [h, r[i]])));
}

for (const dir of events) {
  const file = path.join(dir, 'cards.csv');
  if (!fs.existsSync(file)) { console.error(`\nmissing ${file}`); continue; }
  const rows = parseCsv(fs.readFileSync(file, 'utf8'));
  const decks = new Set(rows.map(r => `${r.division}/${r.place}/${r.player}`));
  const gaps = new Map();              // display -> {reason, copies, decks:Set}
  const deckNeeds = new Map();         // deck -> Set(display)

  for (const r of rows) {
    const deck = `${r.division}/${r.place}/${r.player}`;
    const ann = (r.annotation || '').trim().toLowerCase();
    const bare = r.card.replace(/\s*\([^)]*\)\s*$/, '').trim();
    const k = norm(bare);
    const wantSet = PRINTING_SET[ann];
    let reason = null;
    if (wantSet) {
      if (!(impl.get(k) || []).includes(wantSet)) reason = 'different printing, no card file in ' + wantSet;
    } else if (!impl.has(k)) {
      reason = unregistered.has(k) ? 'card file exists, unregistered in set index' : 'no card file';
    }
    if (!reason) continue;
    const display = ann ? `${bare} (${ann})` : bare;
    if (!gaps.has(display)) gaps.set(display, { reason, copies: 0, decks: new Set() });
    const g = gaps.get(display);
    g.copies += Number(r.copies) || 0;
    g.decks.add(deck);
    if (!deckNeeds.has(deck)) deckNeeds.set(deck, new Set());
    deckNeeds.get(deck).add(display);
  }

  console.log(`\n########## ${path.basename(dir)}  (${decks.size} decks)`);
  if (!gaps.size) { console.log('  every card in the field is implemented and registered'); continue; }
  console.log(`  ${gaps.size} card(s) unavailable:`);
  [...gaps].sort((a, b) => b[1].copies - a[1].copies).forEach(([n, g]) =>
    console.log(`    ${String(g.copies).padStart(3)} copies  ${String(g.decks.size).padStart(2)} decks   ${n}  -- ${g.reason}`));
  console.log(`  decks buildable verbatim today: ${decks.size - deckNeeds.size}/${decks.size}`);

  // incremental: cheapest fixes first
  const order = [...gaps].sort((a, b) => a[1].decks.size - b[1].decks.size).map(([n]) => n).reverse();
  const fixed = new Set();
  for (const card of order) {
    fixed.add(card);
    const still = [...deckNeeds].filter(([, need]) => [...need].some(n => !fixed.has(n))).length;
    console.log(`  + ${card.padEnd(34)} -> ${decks.size - still}/${decks.size} buildable`);
  }
}
