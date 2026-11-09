// Engine audit part 2 (log #484, Evan's row 102): scripted rule cases on built states, no pilot. Expected values are the 2000
// printed rules and the rulings in research_notes/STS 2000 rules and card references. Writes runs/probe/AUDIT-engine/cases.json.
// Run: node notes/scripts/audit/damage_cases.js
'use strict';
const fs = require('fs');
const path = require('path');
const { C, scene, play, attackAction, playHand, benchTarget, ACTIVE, prizesLeft } = require('./scene.js');

const OUT = path.join(__dirname, '..', '..', '..', 'runs', 'probe', 'AUDIT-engine', 'cases.json');
const rows = [];
const check = (name, expected, observed, extra = {}) => {
  const ok = JSON.stringify(expected) === JSON.stringify(observed);
  rows.push({ case: name, expected, observed, result: ok ? 'PASS' : 'FAIL', ...extra });
};
const info = (name, observed, extra = {}) => rows.push({ case: name, expected: null, observed, result: 'INFO', ...extra });
const FIGHT = n => Array(n).fill('Fighting Energy BS');
const dmg = (s, i) => s.state.players[i].active.damage;
const gone = (s, i, name) => s.state.players[i].discard.cards.some(c => c.name === name);
const hit = (s, name, opts) => play(s, attackAction(1, name), opts);
const pass = (s, id) => play(s, new C.PassTurnAction(id));

// ---- damage pipeline: Hitmonchan (Fighting; Jab 20, Special Punch 40), Scyther (Grass; Slash 30; resists Fighting -30),
// Pikachu (40 HP, weak Fighting).
{ const s = scene({ active: 'Scyther JU', energy: FIGHT(3) }, { active: 'Pikachu BS', bench: ['Pikachu BS'] });
  hit(s, 'Slash'); check('base damage: Scyther Slash 30 into Pikachu (no Weakness to Grass)', 30, dmg(s, 1)); }
{ const s = scene({ active: 'Hitmonchan BS', energy: FIGHT(1) }, { active: 'Pikachu BS', bench: ['Pikachu BS'] });
  hit(s, 'Jab'); check('Weakness x2: Jab 20 (Fighting) into Pikachu (weak Fighting) = 40 -> KO at 40 HP', 'KO', gone(s, 1, 'Pikachu') ? 'KO' : dmg(s, 1)); }
{ const s = scene({ active: 'Hitmonchan BS', energy: FIGHT(1) }, { active: 'Charmander BS', bench: ['Pikachu BS'] });
  hit(s, 'Jab'); check('no Weakness: Jab 20 into Charmander (weak Water) = 20', 20, dmg(s, 1)); }
{ const s = scene({ active: 'Hitmonchan BS', energy: FIGHT(3) }, { active: 'Scyther JU', bench: ['Pikachu BS'] });
  hit(s, 'Special Punch'); check('Resistance -30: Special Punch 40 into Scyther (resists Fighting) = 10', 10, dmg(s, 1)); }
{ const s = scene({ active: 'Hitmonchan BS', energy: FIGHT(1) }, { active: 'Scyther JU', bench: ['Pikachu BS'] });
  hit(s, 'Jab'); check('Resistance floor: Jab 20 into Scyther = 0, never negative or healing', 0, dmg(s, 1)); }
{ const s = scene({ active: 'Hitmonchan BS', energy: FIGHT(3), hand: ['PlusPower BS'] }, { active: 'Scyther JU', bench: ['Pikachu BS'] });
  play(s, playHand(1, 0)); hit(s, 'Special Punch');
  check('PlusPower +10 after W/R: Special Punch 40 -30 +10 = 20 into Scyther', 20, dmg(s, 1)); }
{ const s = scene({ active: 'Hitmonchan BS', energy: FIGHT(1), hand: ['PlusPower BS'] }, { active: 'Pikachu BS', bench: ['Pikachu BS'] });
  play(s, playHand(1, 0)); hit(s, 'Jab');
  check('PlusPower after Weakness: Jab 20 x2 +10 = 50 into Pikachu (40 HP) -> KO', 'KO', gone(s, 1, 'Pikachu') ? 'KO' : dmg(s, 1)); }
{ const s = scene({ active: 'Hitmonchan BS', energy: FIGHT(1), hand: ['PlusPower BS'] }, { active: 'Scyther JU', bench: ['Pikachu BS'] });
  play(s, playHand(1, 0)); hit(s, 'Jab');
  info('PlusPower on an attack Resistance reduces to 0: Jab 20 -30 floor 0, then +10? (ruling not fixed in our notes)', dmg(s, 1)); }
{ // Defender -20 (the opponent plays Defender on its Active in its turn; the attacker hits during the next turn)
  const s = scene({ active: 'Scyther JU', energy: FIGHT(3) }, { active: 'Pikachu BS', hand: ['Defender BS'], bench: ['Pikachu BS'] }, { active: 1 });
  play(s, playHand(2, 0), { target: ACTIVE }); pass(s, 2);
  hit(s, 'Slash'); check('Defender -20: Slash 30 into Defender-protected Pikachu = 10', 10, dmg(s, 1)); }
{ const s = scene({ active: 'Hitmonchan BS', energy: FIGHT(1) }, { active: 'Pikachu BS', hand: ['Defender BS'], bench: ['Pikachu BS'] }, { active: 1 });
  play(s, playHand(2, 0), { target: ACTIVE }); pass(s, 2);
  hit(s, 'Jab'); check('Defender after Weakness: Jab 20 x2 -20 = 20 into Pikachu', 20, dmg(s, 1)); }

// ---- knockouts and Prizes
{ const s = scene({ active: 'Scyther JU', energy: FIGHT(3) }, { active: 'Pikachu BS', damage: 10, bench: ['Pikachu BS'] });
  hit(s, 'Slash');
  check('KO exactly at 0 HP left (Pikachu 40 HP, 10 + 30 = 40)', true, gone(s, 1, 'Pikachu'));
  check('a Prize is taken on a KO (6 -> 5)', 5, prizesLeft(s.state.players[0]));
  check('the KO ends the turn and the opponent promotes the Bench', ['Pikachu', 2], [s.state.players[1].active.getPokemonCard() && s.state.players[1].active.getPokemonCard().name, s.state.turn - 5 + 1]); }
{ const s = scene({ active: 'Scyther JU', energy: FIGHT(3) }, { active: 'Pikachu BS', damage: 0, bench: ['Pikachu BS'] });
  hit(s, 'Slash');
  check('no KO with 10 HP left (Pikachu 40 HP, 30 damage), no Prize', [false, 6], [gone(s, 1, 'Pikachu'), prizesLeft(s.state.players[0])]); }

// ---- Poison
{ const s = scene({ active: 'Scyther JU' }, { active: 'Pikachu BS', sp: ['POISONED'], bench: ['Pikachu BS'] });
  pass(s, 1); const a = dmg(s, 1); pass(s, 2); const b = dmg(s, 1);
  check('Poison 10 after each turn ends, either player (after P1 turn, after P2 turn)', [10, 20], [a, b]); }
{ const s = scene({ active: 'Scyther JU' }, { active: 'Pikachu BS', damage: 30, sp: ['POISONED'], bench: ['Pikachu BS'] });
  pass(s, 1);
  check('KO by Poison at 40: the Prize goes to the poisoned Pokemon\'s opponent', [true, 5], [gone(s, 1, 'Pikachu'), prizesLeft(s.state.players[0])]); }
{ const s = scene({ active: 'Scyther JU', prizes: 1 }, { active: 'Pikachu BS', damage: 30, sp: ['POISONED'], bench: ['Pikachu BS'] });
  pass(s, 1);
  check('Poison KO takes the last Prize: the opponent of the poisoned Pokemon wins', 'PLAYER_1', C.GameWinner[s.state.winner]); }

// ---- Confusion (2000: tails = 20 to itself with its own Weakness and Resistance; the later rule is 30 with none)
{ const s = scene({ active: 'Pikachu BS', energy: ['Lightning Energy BS'], sp: ['CONFUSED'] }, { active: 'Scyther JU' });
  const r = hit(s, 'Gnaw', { flips: [false] });
  check('Confusion tails, Pikachu (weak Fighting): 20 to itself, 0 to the opponent, turn ends', [20, 0], [dmg(s, 0), dmg(s, 1)], { flips: r.flips });
  info('Confusion tails: turn ended', s.state.activePlayer === 1); }
{ const s = scene({ active: 'Mr. Mime JU', energy: ['Psychic Energy BS', 'Double Colorless Energy BS'], sp: ['CONFUSED'] }, { active: 'Scyther JU' });
  hit(s, 'Meditate', { flips: [false] });
  check('Confusion tails, Mr. Mime (weak Psychic... own Weakness applies): 40 = 20 x2 knocks it out (Mar 30, 2000 ruling)', true, gone(s, 0, 'Mr. Mime')); }
{ const s = scene({ active: 'Pikachu BS', energy: ['Lightning Energy BS'], sp: ['CONFUSED'] }, { active: 'Scyther JU' });
  hit(s, 'Gnaw', { flips: [true] });
  check('Confusion heads: the attack goes through (Gnaw 10)', [0, 10], [dmg(s, 0), dmg(s, 1)]); }

// ---- Paralysis wears off at the end of the paralyzed player's own next turn
{ const s = scene({ active: 'Scyther JU' }, { active: 'Pikachu BS', sp: ['PARALYZED'], bench: ['Pikachu BS'] });
  pass(s, 1); const a = s.state.players[1].active.specialConditions.length; pass(s, 2); const b = s.state.players[1].active.specialConditions.length;
  check('Paralysis: still on after the attacking turn ends, gone after the paralyzed side own turn', [1, 0], [a, b]); }

// ---- turn start: draw, deck-out
{ const s = scene({ active: 'Scyther JU', deck: 5 }, { active: 'Pikachu BS', deck: 5 });
  pass(s, 1);
  check('draw 1 card at the start of the turn (P2 hand 0 -> 1, deck 5 -> 4)', [1, 4], [s.state.players[1].hand.cards.length, s.state.players[1].deck.cards.length]); }
{ const s = scene({ active: 'Scyther JU', deck: 5 }, { active: 'Pikachu BS', deck: 0 });
  pass(s, 1);
  check('deck-out: a player who cannot draw at the start of the turn loses', 'PLAYER_1', C.GameWinner[s.state.winner]); }

// ---- wins
{ const s = scene({ active: 'Scyther JU', energy: FIGHT(3), prizes: 1 }, { active: 'Pikachu BS', damage: 10, bench: ['Pikachu BS'] });
  hit(s, 'Slash');
  check('last Prize taken wins', 'PLAYER_1', C.GameWinner[s.state.winner]); }
{ const s = scene({ active: 'Scyther JU', energy: FIGHT(3) }, { active: 'Pikachu BS', damage: 10 });
  hit(s, 'Slash');
  check('KO of the last Pokemon in play (no Bench) wins at once', 'PLAYER_1', C.GameWinner[s.state.winner]); }

// ---- first turn
{ const s = scene({ active: 'Pikachu BS', energy: ['Lightning Energy BS'], played: 1 }, { active: 'Scyther JU' }, { turn: 1 });
  const r = hit(s, 'Gnaw');
  check('first player\'s first turn attack is allowed (2000 rules; first-turn attack ban was later)', [10, null], [dmg(s, 1), r.error]); }
{ const st = scene({ active: 'Pikachu BS' }, { active: 'Scyther JU' }).state;
  info('format rules: firstTurnDrawCard / firstTurnUseSupporter / mulliganDrawCards', { firstTurnDrawCard: st.rules.firstTurnDrawCard, firstTurnUseSupporter: st.rules.firstTurnUseSupporter, mulliganDrawCards: st.rules.mulliganDrawCards }); }

// ---- one Energy attach a turn, one retreat a turn
{ const s = scene({ active: 'Scyther JU', hand: ['Fighting Energy BS', 'Fighting Energy BS'] }, { active: 'Pikachu BS' });
  const a = play(s, playHand(1, 0)), b = play(s, playHand(1, 0));
  check('one Energy attach a turn: first accepted, second rejected', [null, 'ENERGY_ALREADY_ATTACHED'], [a.error, b.error]); }
{ const s = scene({ active: 'Scyther JU', bench: ['Pikachu BS', 'Pikachu BS'] }, { active: 'Pikachu BS' });
  const a = play(s, new C.RetreatAction(1, 0)), b = play(s, new C.RetreatAction(1, 1));
  check('one retreat a turn: first accepted, second rejected', [null, 'RETREAT_ALREADY_USED'], [a.error, b.error]); }

// ---- evolution timing: Bulbasaur -> Ivysaur
const evolve = (turn, played, first) => {
  const s = scene({ active: 'Bulbasaur BS', hand: ['Ivysaur BS'], played }, { active: 'Pikachu BS' }, { turn, active: first ? 0 : 0 });
  return play(s, playHand(1, 0)).error;
};
check('no evolution on the turn the Pokemon was played (played turn 5, now 5)', 'POKEMON_CANT_EVOLVE_THIS_TURN', evolve(5, 5));
check('evolution the turn after it was played (played turn 3, now 5)', null, evolve(5, 3));
{ // the setup stamps the first player\'s starters with turn 1 and the second player\'s with turn 2
  check('no evolution on the first player\'s first turn (starter stamped 1, turn 1)', 'POKEMON_CANT_EVOLVE_THIS_TURN', evolve(1, 1));
  check('no evolution on the second player\'s first turn (starter stamped 2, turn 2)', 'POKEMON_CANT_EVOLVE_THIS_TURN', evolve(2, 2));
  check('evolution on the first player\'s second turn (starter stamped 1, turn 3)', null, evolve(3, 1)); }

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ rows }, null, 1));
for (const r of rows) console.log(r.result.padEnd(5), r.case, '| expected', JSON.stringify(r.expected), '| observed', JSON.stringify(r.observed), r.error ? '[' + r.error + ']' : '');
console.log(rows.filter(r => r.result === 'PASS').length + ' PASS, ' + rows.filter(r => r.result === 'FAIL').length + ' FAIL, ' + rows.filter(r => r.result === 'INFO').length + ' INFO');
