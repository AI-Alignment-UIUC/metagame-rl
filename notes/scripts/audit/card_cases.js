// Engine audit part 3b (log #484, Evan's row 102): scripted checks of card effects the effect readers flagged, against the printed
// text. Writes runs/probe/AUDIT-engine/card_cases.json. Run: node notes/scripts/audit/card_cases.js
'use strict';
const fs = require('fs');
const path = require('path');
const { C, scene, play, attackAction, playHand, benchTarget, ACTIVE } = require('./scene.js');
const { promptSpace } = require(path.join(__dirname, '..', '..', '..', 'env', 'legal.js'));

const OUT = path.join(__dirname, '..', '..', '..', 'runs', 'probe', 'AUDIT-engine', 'card_cases.json');
const rows = [];
const check = (name, expected, observed, extra = {}) =>
  rows.push({ case: name, expected, observed, result: JSON.stringify(expected) === JSON.stringify(observed) ? 'PASS' : 'FAIL', ...extra });
const info = (name, observed, extra = {}) => rows.push({ case: name, expected: null, observed, result: 'INFO', ...extra });
const dmg = (s, i) => s.state.players[i].active.damage;
const pass = (s, id) => play(s, new C.PassTurnAction(id));
const F = n => Array(n).fill('Fighting Energy BS');
const ditto = (s, id, name) => play(s, new C.UseAbilityAction(id, 'Transform', ACTIVE), { pick: { index: 0, name } });
const units = (s, seat) => {
  const p = s.state.players[seat];
  const e = new C.CheckProvidedEnergyEffect(p);
  s.reduceEffect(s.state, e);
  return { units: e.energyMap.reduce((n, m) => n + m.provideAmount, 0), map: e.energyMap };
};

// ---- 1. Ditto and Double Colorless Energy
{ const s = scene({ active: 'Ditto FO', energy: ['Double Colorless Energy BS'] }, { active: 'Scyther JU' });
  const u = units(s, 0);
  check('1a Ditto + DCE: provided Energy units', 2, u.units);
  const CCC = [C.CardType.COLORLESS, C.CardType.COLORLESS, C.CardType.COLORLESS];
  check('1b Ditto + DCE alone cannot pay CCC (2 units)', false, C.StateUtils.checkEnoughEnergy(u.map, CCC)); }
{ const s = scene({ active: 'Ditto FO', energy: ['Double Colorless Energy BS', 'Fighting Energy BS'] }, { active: 'Scyther JU' });
  const r = ditto(s, 1, 'Slash');
  check('1c Ditto + DCE + 1 basic pays CCC: Slash copied, 30 damage', 30, dmg(s, 1), { error: r.error }); }
{ const s = scene({ active: 'Ditto FO', energy: ['Double Colorless Energy BS'] }, { active: 'Magmar FO', bench: ['Pikachu BS'] });
  const u = units(s, 0), FF = [C.CardType.FIRE, C.CardType.FIRE];
  info('1d Ditto + DCE paying a typed cost FF (copying Magmar Smog): engine says', C.StateUtils.checkEnoughEnergy(u.map, FF),
       { note: 'Ditto text: any Energy attached to Ditto counts as Energy of any type; DCE is colorless, 2 units' }); }

// ---- 2. Ditto Swords Dance then Slash on N+2; plain Slash
{ const s = scene({ active: 'Ditto FO', energy: ['Grass Energy BS', ...F(3)] }, { active: 'Scyther JU' }, { turn: 5 });
  ditto(s, 1, 'Swords Dance'); pass(s, 2);                 // turn 5 (P1), turn 6 passes in the middle
  const mid = Object.keys(s.state.players[0].active.marker.markers || {}).length;
  pass(s, 1);                                              // turn 7: P1 acts, so call Slash before passing
  info('2a (setup) markers on the Ditto slot after Swords Dance and the opponent turn', s.state.players[0].active.marker.markers.map(m => m.name)); }
{ const s = scene({ active: 'Ditto FO', energy: ['Grass Energy BS', ...F(3)] }, { active: 'Scyther JU' }, { turn: 5 });
  ditto(s, 1, 'Swords Dance'); pass(s, 2);                 // turn 6 was the opponent's, now turn 7 is P1's
  const r = ditto(s, 1, 'Slash');
  check('2b Ditto: Swords Dance on turn N, Slash on N+2 = 60 (printed text)', 60, dmg(s, 1), { error: r.error }); }
{ const s = scene({ active: 'Ditto FO', energy: ['Grass Energy BS', ...F(3)] }, { active: 'Scyther JU' }, { turn: 5 });
  const r = ditto(s, 1, 'Slash');
  check('2c Ditto plain Slash = 30', 30, dmg(s, 1), { error: r.error }); }
{ const s = scene({ active: 'Scyther JU', energy: ['Grass Energy BS', ...F(3)] }, { active: 'Magmar FO', bench: ['Pikachu BS'] }, { turn: 5 });
  play(s, attackAction(1, 'Swords Dance')); pass(s, 2);
  play(s, attackAction(1, 'Slash'));
  check('2d real Scyther: Swords Dance then Slash = 60', 60, dmg(s, 1)); }

// ---- 3. Ditto's copied attack: turn end, a second attack, first turn
{ const s = scene({ active: 'Ditto FO', energy: F(3) }, { active: 'Scyther JU', bench: ['Pikachu BS'] });
  ditto(s, 1, 'Slash');
  check('3a the turn ends after the copied attack (P2 to move)', 1, s.state.activePlayer);
  const r2 = ditto(s, 1, 'Slash');
  check('3b Ditto cannot attack again the same turn (second use rejected, no second damage)', [30, true], [dmg(s, 1), !!r2.error], { error: r2.error }); }
{ const s = scene({ active: 'Ditto FO', energy: F(3), played: 1 }, { active: 'Scyther JU' }, { turn: 1 });
  const r = ditto(s, 1, 'Slash');
  check('3c first player\'s first turn: Ditto copied attack allowed (2000 rules allow a first-turn attack)', 30, dmg(s, 1), { error: r.error }); }

// ---- 4. Rainbow Energy TR on a Pokemon with 10 HP left
{ const s = scene({ active: 'Scyther JU', hand: ['Rainbow Energy TR'] }, { active: 'Pikachu BS' });
  s.state.players[0].active.damage = 60;                              // Scyther 70 HP: 10 left
  const r = play(s, playHand(1, 0));
  check('4a Rainbow Energy attached to the Active with 10 HP left: knocked out at once, opponent takes a Prize', [true, 5],
        [s.state.players[0].discard.cards.some(c => c.name === 'Scyther'), s.state.players[1].prizes.reduce((n, z) => n + z.cards.length, 0)], { error: r.error }); }
{ const s = scene({ active: 'Scyther JU', hand: ['Rainbow Energy TR'], bench: [{ name: 'Pikachu BS', damage: 30 }] }, { active: 'Pikachu BS' });
  const r = play(s, playHand(1, 0, benchTarget(0)));
  check('4b Rainbow Energy attached to a Benched Pokemon with 10 HP left: knocked out at once', true,
        s.state.players[0].discard.cards.some(c => c.name === 'Pikachu'), { error: r.error }); }

// ---- 5. Blastoise Rain Dance onto a non-Water Pokemon
{ const s = scene({ active: 'Blastoise BS', hand: ['Water Energy BS'], bench: ['Pikachu BS'] }, { active: 'Scyther JU' });
  s.dispatch(new C.UseAbilityAction(1, 'Rain Dance', ACTIVE));
  const p = s.state.prompts.find(q => q.result === undefined);
  const opts = promptSpace(p, s.state).options([]).map(o => o.key);
  let accepted = null;
  try { s.dispatch(new C.ResolvePromptAction(p.id, p.decode([{ to: benchTarget(0), index: 0 }], s.state))); accepted = s.state.players[0].bench[0].energies.cards.length === 1; }
  catch (e) { accepted = 'rejected: ' + e.message; }
  info('5a (setup) the env offers these Rain Dance picks', opts);
  check('5b Rain Dance attach to a non-Water Pokemon (Pikachu) is not allowed', false, accepted); }

// ---- 6. Gastly FO Energy Conversion with no Energy in the discard pile
{ const s = scene({ active: 'Gastly FO', energy: ['Psychic Energy BS', 'Psychic Energy BS'] }, { active: 'Pikachu BS' });
  const r = play(s, attackAction(1, 'Energy Conversion'));
  check('6a Energy Conversion with no Energy in the discard: Gastly still does 10 damage to itself', 10, dmg(s, 0), { error: r.error }); }
{ const s = scene({ active: 'Gastly FO', energy: ['Psychic Energy BS', 'Psychic Energy BS'] }, { active: 'Pikachu BS' });
  s.state.players[0].discard.cards.push(new (require('./scene.js').card('Fighting Energy BS').constructor)());
  const r = play(s, attackAction(1, 'Energy Conversion'));
  check('6b (reference) with 1 Energy in the discard: it goes to hand, 10 self-damage', [1, 10], [s.state.players[0].hand.cards.length, dmg(s, 0)], { error: r.error }); }

// ---- 7. Farfetch'd Leek Slap
const LEEK = { active: "Farfetch'd BS", energy: F(3) };
{ const s = scene(LEEK, { active: 'Pikachu BS', bench: ['Pikachu BS'] });
  const a = play(s, attackAction(1, 'Leek Slap')); pass(s, 2);
  const b = play(s, attackAction(1, 'Leek Slap'));
  check('7a same Farfetch\'d: second Leek Slap blocked while it stays in play', [null, 'BLOCKED_BY_EFFECT'], [a.error, b.error]); }
{ const s = scene({ ...LEEK, bench: [{ name: "Farfetch'd BS", energy: F(1) }] }, { active: 'Pikachu BS', bench: ['Pikachu BS'] });
  const a = play(s, attackAction(1, 'Leek Slap')); pass(s, 2);
  play(s, new C.RetreatAction(1, 0));                                   // the second Farfetch'd comes up
  const b = play(s, attackAction(1, 'Leek Slap'));
  check('7b a second Farfetch\'d may use Leek Slap after the first did', [null, null], [a.error, b.error]); }
{ const s = scene({ ...LEEK, bench: [{ name: "Farfetch'd BS", energy: F(1) }] }, { active: 'Scyther JU', energy: F(3), bench: ['Pikachu BS'] }, { active: 1 });
  s.state.players[0].active.damage = 40;                                // the first Farfetch'd (50 HP): 10 left
  const x = play(s, attackAction(2, 'Slash'));                          // P2 knocks it out; P1 promotes the second
  const first = s.state.players[0].discard.cards.some(c => c.name === "Farfetch'd");
  const b = play(s, attackAction(1, 'Leek Slap'));
  check('7c after the first Farfetch\'d was knocked out, the second may use Leek Slap', [true, null], [first, b.error], { slashError: x.error }); }
{ const s = scene({ ...LEEK, bench: [{ name: 'Pikachu BS', energy: F(1) }] }, { active: 'Pikachu BS', bench: ['Pikachu BS'] });
  play(s, attackAction(1, 'Leek Slap')); pass(s, 2);
  play(s, new C.RetreatAction(1, 0)); pass(s, 1); pass(s, 2);
  const back = play(s, new C.RetreatAction(1, 0));
  const b = play(s, attackAction(1, 'Leek Slap'));
  check('7d benched and brought back, Leek Slap still blocked (printed: even on the Bench)', 'BLOCKED_BY_EFFECT', b.error, { retreatBack: back.error }); }

// ---- 8. Clefairy Metronome copying
const CLE = { active: 'Clefairy BS', energy: F(3) };
{ const s = scene(CLE, { active: 'Electabuzz BS', bench: ['Pikachu BS'] });
  const r = play(s, attackAction(1, 'Metronome'), { pick: { index: 0, name: 'Thunderpunch' }, flips: [true] });
  check('8a Metronome -> Thunderpunch, heads: 30 + 10 = 40 (Electabuzz handler fires; Colorless attacker, no Weakness for Fighting? Electabuzz weak Fighting)', 40, dmg(s, 1), { error: r.error }); }
{ const s = scene(CLE, { active: 'Electabuzz BS', bench: ['Pikachu BS'] });
  const r = play(s, attackAction(1, 'Metronome'), { pick: { index: 0, name: 'Thunderpunch' }, flips: [false] });
  check('8b Metronome -> Thunderpunch, tails: 30 to the Defending Pokemon and 10 to Clefairy itself', [30, 10], [dmg(s, 1), dmg(s, 0)], { error: r.error }); }
{ const s = scene(CLE, { active: 'Scyther JU', bench: ['Pikachu BS'] });
  const r = play(s, attackAction(1, 'Metronome'), { pick: { index: 0, name: 'Swords Dance' } });
  const m = s.state.players[0].active.marker.markers.map(x => x.name);
  info('8c Metronome -> Swords Dance: marker set on Clefairy\'s slot (the copied card\'s handler fired)', m, { error: r.error });
  pass(s, 2);
  const r2 = play(s, attackAction(1, 'Metronome'), { pick: { index: 0, name: 'Slash' } });
  info('8d next turn Metronome -> Slash after the copied Swords Dance (60 if the marker follows the copy)', dmg(s, 1), { error: r2.error }); }

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ rows }, null, 1));
for (const r of rows) console.log(r.result.padEnd(5), r.case, '| expected', JSON.stringify(r.expected), '| observed', JSON.stringify(r.observed), r.error ? '[' + r.error + ']' : '');
console.log(rows.filter(r => r.result === 'PASS').length + ' PASS, ' + rows.filter(r => r.result === 'FAIL').length + ' FAIL, ' + rows.filter(r => r.result === 'INFO').length + ' INFO');
