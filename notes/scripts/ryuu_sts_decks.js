// Turn an archived decklist CSV into ryuu-play card lists.
//
// Reads notes/data/<event>/cards.csv (produced by meta_aggregate.py) and maps each archived
// card name onto a registered ryuu-play card, using the archive's `annotation` column to pick
// between printings. Shared by ryuu_sts_decks_check.js and ryuu_selfplay.js.
'use strict';
const fs = require('fs');
const H = require('./ryuu_harness.js');

const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');

// archive annotation -> ryuu-play set code
const SET_OF = {
  'base set': 'BS', bs: 'BS', bs2: 'BS', 'base set 2': 'BS',
  jungle: 'JU', ju: 'JU', fossil: 'FO', fo: 'FO',
  'team rocket': 'TR', tr: 'TR', 'movie promo': 'PR', promo: 'PR',
};
const SET_ORDER = ['BS', 'JU', 'FO', 'TR', 'PR'];
const TYPOS = { lightningenegry: 'lightningenergy', rocketssneakatack: 'rocketssneakattack', potionenegry: 'potionenergy' };

// every registered card, indexed by normalised name
const byName = new Map();
{
  const S = H.S.baseSets;
  for (const set of [S.setBase, S.setJungle, S.setFossil, S.setTeamRocket, S.setPromos].filter(Boolean)) {
    for (const card of set) {
      const k = norm(card.name);
      if (!byName.has(k)) byName.set(k, []);
      byName.get(k).push(card);
    }
  }
}

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

function resolveCard(name, annotation) {
  const bare = name.replace(/\s*\([^)]*\)\s*$/, '').trim();
  let k = norm(bare);
  k = TYPOS[k] || k;
  const found = byName.get(k);
  if (!found) return { error: 'no card named "' + bare + '"' };
  if (found.length === 1) return { card: found[0] };

  const want = SET_OF[(annotation || '').trim().toLowerCase()];
  if (want) {
    const pick = found.find(c => c.set === want);
    if (!pick) return { error: '"' + bare + '" has no ' + want + ' printing (' + found.map(c => c.set).join('/') + ')' };
    return { card: pick };
  }

  // No printing given. The archive annotates a reprint and leaves the original bare, which is
  // also how players wrote lists in 2000, so fall back to the earliest set. Every duplicate
  // name in this pool is a mechanically different card, so report when this happens.
  const pick = SET_ORDER.map(s => found.find(c => c.set === s)).find(Boolean);
  return { card: pick, assumed: bare + ' -> ' + pick.fullName + ' (also in ' + found.filter(c => c !== pick).map(c => c.set).join('/') + ')' };
}

// -> Map("<division> #<place> <player> (<label>)" -> string[] of fullNames)
// Decks with an unresolvable card are left out; pass an array as `issues` to collect why.
function buildArchivedDecks(csvPath, issues) {
  const rows = parseCsv(fs.readFileSync(csvPath, 'utf8'));
  const grouped = new Map();
  for (const r of rows) {
    const key = `${r.division} #${r.place} ${r.player} (${r.label})`;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(r);
  }

  const decks = new Map();
  for (const [key, cards] of grouped) {
    const names = [];
    const assumed = [];
    let bad = null;
    for (const r of cards) {
      const res = resolveCard(r.card, r.annotation);
      if (res.error) { bad = res.error; break; }
      if (res.assumed) assumed.push(res.assumed);
      for (let i = 0; i < Number(r.copies); i++) names.push(res.card.fullName);
    }
    if (bad) { if (issues) issues.push({ key, error: bad }); continue; }
    if (assumed.length && issues) issues.push({ key, assumed });
    decks.set(key, names);
  }
  return decks;
}

module.exports = { buildArchivedDecks, resolveCard, parseCsv, norm, SET_OF, SET_ORDER };
