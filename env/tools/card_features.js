// Card table for the token representation (plan item A4.2): every card in the Base Sets
// format (Base, Jungle, Fossil, Team Rocket, Black Star Promos), with
//   - a stable id (1-based, by fullName; 0 means "no card"),
//   - structured features (numbers a network can read directly),
//   - a plain-text description (name, kind, stats, attacks and their text, Powers, rules text)
//     for a frozen sentence encoder (rl/card_text.py), so a card never seen in training still
//     gets a meaningful representation.
//
// Run: node env/tools/card_features.js [--out notes/data/cards/pool.json]
'use strict';
const fs = require('fs');
const path = require('path');
const { C, cm, FORMAT } = require('../engine.js');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const OUT = flag('out', path.join(__dirname, '..', '..', 'notes', 'data', 'cards', 'pool.json'));

const TYPES = ['COLORLESS', 'GRASS', 'FIGHTING', 'PSYCHIC', 'WATER', 'LIGHTNING', 'METAL', 'DARK', 'FIRE', 'DRAGON', 'FAIRY'];
const TYPE_LETTER = ['C', 'G', 'F', 'P', 'W', 'L', 'M', 'D', 'R', 'N', 'Y'];
const counts = list => { const v = new Array(TYPES.length).fill(0); for (const t of list || []) v[t]++; return v; };
const typeName = t => TYPES[t].charAt(0) + TYPES[t].slice(1).toLowerCase();

function features(card) {
  const f = {
    superType: card.superType, stage: card.stage || 0, hp: card.hp || 0,
    types: counts(card.cardTypes), weakness: counts((card.weakness || []).map(w => w.type)),
    resistance: counts((card.resistance || []).map(r => r.type)), retreat: (card.retreat || []).length,
    evolvesFrom: card.evolvesFrom || '', trainerType: card.trainerType === undefined ? -1 : card.trainerType,
    provides: counts(card.provides), provideAmount: card.provideAmount || 0,
    energyType: card.energyType === undefined ? -1 : card.energyType,
    tags: card.tags || [],
    attacks: (card.attacks || []).map(a => ({ name: a.name, cost: counts(a.cost), damage: Number((/\d+/.exec(a.damage || '') || [0])[0]), damageText: a.damage || '', text: a.text || '' })),
    powers: (card.powers || []).map(p => ({ name: p.name, text: p.text || '', inPlay: !!p.useWhenInPlay, fromHand: !!p.useFromHand, fromDiscard: !!p.useFromDiscard })),
  };
  return f;
}

function description(card) {
  const parts = [card.name + '.'];
  if (card instanceof C.PokemonCard) {
    const stage = { 2: 'Basic', 3: 'Stage 1', 4: 'Stage 2', 1: 'Restored' }[card.stage] || 'Basic';
    parts.push(`${stage} Pokémon${card.evolvesFrom ? ', evolves from ' + card.evolvesFrom : ''}, ${(card.cardTypes || []).map(typeName).join('/')} type, ${card.hp} HP.`);
    for (const p of card.powers || []) parts.push(`Pokémon Power ${p.name}: ${p.text}`);
    for (const a of card.attacks || []) {
      const cost = (a.cost || []).map(t => TYPE_LETTER[t]).join('') || 'free';
      parts.push(`Attack ${a.name} (${cost})${a.damage ? ' ' + a.damage + ' damage' : ''}${a.text ? ': ' + a.text : '.'}`);
    }
    if ((card.weakness || []).length) parts.push(`Weakness ${card.weakness.map(w => typeName(w.type)).join('/')}.`);
    if ((card.resistance || []).length) parts.push(`Resistance ${card.resistance.map(r => typeName(r.type) + ' ' + r.value).join('/')}.`);
    parts.push(`Retreat cost ${(card.retreat || []).length}.`);
  } else if (card instanceof C.TrainerCard) {
    parts.push(['Trainer.', 'Supporter.', 'Stadium.', 'Pokémon Tool.'][card.trainerType] || 'Trainer.');
    if (card.text) parts.push(card.text);
  } else if (card instanceof C.EnergyCard) {
    parts.push(card.energyType === C.EnergyType.BASIC ? 'Basic Energy.' : 'Special Energy.');
    parts.push(`Provides ${(card.provides || []).map(t => TYPE_LETTER[t]).join('')}${card.provideAmount > 1 ? ' x' + card.provideAmount : ''}.`);
    if (card.text) parts.push(card.text);
  }
  return parts.join(' ');
}

const format = cm.getAllFormats().find(f => f.name === FORMAT);
const cards = format.cards.slice().sort((a, b) => a.fullName.localeCompare(b.fullName));
const table = cards.map((card, i) => ({ id: i + 1, fullName: card.fullName, name: card.name, set: card.set, ...features(card), description: description(card) }));
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ format: FORMAT, types: TYPES, cards: table }, null, 1));
console.log(`${table.length} cards -> ${OUT}`);
console.log('example:', table.find(c => c.fullName === 'Wigglytuff JU').description);
console.log('example:', table.find(c => c.fullName === 'Gust of Wind BS').description);
