// Engine audit part 3 (log #484/#486, Evan's row 102): is a Ditto (Transform) Slash into Scyther ever 60 where 30 is printed?
// Scripted states, no pilot. Writes runs/probe/AUDIT-engine/ditto.json. Run: node notes/scripts/audit/ditto_probe.js
'use strict';
const fs = require('fs');
const path = require('path');
const { C, scene, play, attackAction, ACTIVE } = require('./scene.js');

const OUT = path.join(__dirname, '..', '..', '..', 'runs', 'probe', 'AUDIT-engine', 'ditto.json');
const F3 = ['Fighting Energy BS', 'Fighting Energy BS', 'Fighting Energy BS'];
const rows = [];

// Ditto (seat 1) uses Transform to copy `attackName`; the damage on the opponent's Active is read after.
const ditto = (store, attackName) => play(store, new C.UseAbilityAction(1, 'Transform', ACTIVE), { pick: { index: 0, name: attackName } });
const dmgOf = (store, seat) => store.state.players[seat].active.damage;
const pass = (store, id) => play(store, new C.PassTurnAction(id));
const rec = (name, expected, observed, extra = {}) => {
  rows.push({ case: name, expected, observed, result: observed === expected ? 'PASS' : 'FAIL', ...extra });
};

// 1. Base case.
{
  const s = scene({ active: 'Ditto FO', energy: F3 }, { active: 'Scyther JU' });
  const r = ditto(s, 'Slash');
  rec('1 Ditto Slash into Scyther', 30, dmgOf(s, 1), { error: r.error });
}
// 1b. Plain Scyther Slash into Scyther (reference).
{
  const s = scene({ active: 'Scyther JU', energy: F3 }, { active: 'Scyther JU' });
  const r = play(s, attackAction(1, 'Slash'));
  rec('1b Scyther Slash into Scyther (reference)', 30, dmgOf(s, 1), { error: r.error });
}
// 2. Opponent switched Magmar -> Scyther on its last turn; Ditto never transformed before.
{
  const s = scene({ active: 'Ditto FO', energy: F3 }, { active: 'Magmar FO', energy: ['Fire Energy BS'], bench: ['Scyther JU'] }, { turn: 4 });
  pass(s, 1);                                                    // turn 5: P2 retreats Magmar for Scyther
  const r1 = play(s, new C.RetreatAction(2, 0));
  pass(s, 2);                                                    // turn 6: Ditto vs the new Active Scyther
  const act = s.state.players[1].active.getPokemonCard().name;
  const r = ditto(s, 'Slash');
  rec('2 opponent Magmar -> Scyther, then Ditto Slash', 30, dmgOf(s, 1), { oppActive: act, error: r.error || r1.error });
}
// 2b. Same, but Ditto copied Magmar (Smokescreen) while Magmar was Active, the turn before.
{
  const s = scene({ active: 'Ditto FO', energy: F3 }, { active: 'Magmar FO', energy: ['Fire Energy BS'], bench: ['Scyther JU'] }, { turn: 4 });
  const r0 = ditto(s, 'Smokescreen');
  pass(s, 1);
  const r1 = play(s, new C.RetreatAction(2, 0));
  pass(s, 2);
  const act = s.state.players[1].active.getPokemonCard().name;
  const r = ditto(s, 'Slash');
  rec('2b Ditto used Smokescreen as Magmar, opponent switched to Scyther, Ditto Slash', 30, dmgOf(s, 1),
      { oppActive: act, error: r.error || r1.error || r0.error });
}
// 3. Ditto against Ditto: neither can copy an attack (no damage).
{
  const s = scene({ active: 'Ditto FO', energy: F3 }, { active: 'Ditto FO', energy: F3 });
  const r = play(s, new C.UseAbilityAction(1, 'Transform', ACTIVE), { pick: { index: 0, name: 'Slash' } });
  rec('3 Ditto against Ditto: no attack to copy, no damage', 0, dmgOf(s, 1), { error: r.error });
}
// 3b. Real Scyther attacks a Ditto that copies Scyther: Grass attacker, Ditto's copied weakness is Fire.
{
  const s = scene({ active: 'Scyther JU', energy: F3 }, { active: 'Ditto FO', energy: F3 });
  const r = play(s, attackAction(1, 'Slash'));
  rec('3b Scyther Slash into a Ditto (copy of Scyther)', 30, dmgOf(s, 1), { error: r.error });
}
// 3c. Magmar (Fire) attacks a Ditto copying Magmar: Magmar's weakness is Water, so no doubling.
{
  const s = scene({ active: 'Magmar FO', energy: ['Fire Energy BS', 'Fire Energy BS'] }, { active: 'Ditto FO', energy: F3 });
  const r = play(s, attackAction(1, 'Smog'), { flips: [false] });
  rec('3c Magmar Smog into a Ditto (copy of Magmar)', 20, dmgOf(s, 1), { error: r.error });
}
// 4. Status conditions turn Transform off (no damage).
for (const sp of ['ASLEEP', 'CONFUSED', 'PARALYZED']) {
  const s = scene({ active: 'Ditto FO', energy: F3, sp: [sp] }, { active: 'Scyther JU' });
  const r = ditto(s, 'Slash');
  rec('4 Ditto ' + sp + ': Transform / Slash gives no damage', 0, dmgOf(s, 1), { error: r.error });
}
// 5. PlusPower on Ditto: 30 + 10.
{
  const s = scene({ active: 'Ditto FO', energy: F3, trainers: ['PlusPower BS'] }, { active: 'Scyther JU' });
  const r = ditto(s, 'Slash');
  rec('5 Ditto with PlusPower, Slash into Scyther', 40, dmgOf(s, 1), { error: r.error });
}
// 6. Swords Dance. Ditto copies it, then Slashes next turn: Scyther's text makes the base damage 60.
{
  const s = scene({ active: 'Ditto FO', energy: ['Grass Energy BS', ...F3] }, { active: 'Scyther JU' }, { turn: 5 });
  const r0 = ditto(s, 'Swords Dance');
  pass(s, 1); pass(s, 2);
  const r = ditto(s, 'Slash');
  rec('6 Ditto Swords Dance, next turn Slash (text: base 60)', 60, dmgOf(s, 1), { error: r.error || r0.error, note: 'matches the printed text; Ditto copies Scyther' });
}
// 6b. The opponent's own Scyther used Swords Dance; Ditto's Slash must not take its marker.
{
  const s = scene({ active: 'Ditto FO', energy: F3 }, { active: 'Scyther JU', energy: ['Grass Energy BS'] }, { turn: 4 });
  pass(s, 1);
  play(s, attackAction(2, 'Swords Dance'));
  const r = ditto(s, 'Slash');
  rec('6b opponent Scyther used Swords Dance last turn; Ditto Slash', 30, dmgOf(s, 1), { error: r.error });
}
// 6c. Ditto Swords Dance, then the opponent switches to a second Scyther; Ditto Slash.
{
  const s = scene({ active: 'Ditto FO', energy: ['Grass Energy BS', ...F3] }, { active: 'Scyther JU', bench: ['Scyther JU'] }, { turn: 5 });
  const r0 = ditto(s, 'Swords Dance');
  pass(s, 1);
  const r1 = play(s, new C.RetreatAction(2, 0));
  pass(s, 2);
  const r = ditto(s, 'Slash');
  rec('6c Ditto Swords Dance, opponent switched to a second Scyther, Ditto Slash', 30, dmgOf(s, 1), { error: r.error || r0.error || r1.error });
}
// 6d. Ditto Swords Dance, the opponent swaps to Magmar and back while Ditto idles a turn; marker should have expired.
{
  const s = scene({ active: 'Ditto FO', energy: ['Grass Energy BS', ...F3] }, { active: 'Scyther JU', bench: [{ name: 'Magmar FO', energy: ['Fire Energy BS'] }] }, { turn: 5 });
  ditto(s, 'Swords Dance');
  pass(s, 1);
  play(s, new C.RetreatAction(2, 0));
  pass(s, 2);
  pass(s, 1);
  play(s, new C.RetreatAction(2, 0));
  pass(s, 2);
  const r = ditto(s, 'Slash');
  rec('6d Ditto Swords Dance, two turns later Slash (marker expired?)', 30, dmgOf(s, 1), { error: r.error });
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify({ rows }, null, 1));
for (const r of rows) console.log(r.result.padEnd(5), String(r.observed).padStart(3), 'expected', String(r.expected).padStart(3), r.case, r.error ? '[' + r.error + ']' : '');
