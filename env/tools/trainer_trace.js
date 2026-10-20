// How a pilot uses its Trainers (log #91; evaluation only). One agent plays both sides over the archived lists; for
// every Trainer played in a main phase it records what the same turn goes on to do: an attack, a prize taken, the turn
// ended without an attack, and the prompt picks that follow the Trainer (what Computer Search or Item Finder discards
// and fetches). Each card's rates are compared with the same player's turns overall, so "PlusPower, then no attack"
// or "Gust of Wind, then no prize" shows up against the baseline.
//
// Run: node env/tools/trainer_trace.js --agent onnxtok:<token model .onnx> [--games 200] [--seed 1] [--sampled]
//        [--json out.json]
'use strict';
const fs = require('fs');
const { Env } = require('../env.js');
const { archivedDecks } = require('../decks.js');

const argv = process.argv.slice(2);
const flag = (name, dflt) => { const i = argv.indexOf('--' + name); return i === -1 ? dflt : argv[i + 1]; };
const SPEC = flag('agent', null), GAMES = Number(flag('games', 200)), SEED = Number(flag('seed', 1));
const SAMPLED = argv.includes('--sampled'), JSON_OUT = flag('json', null);

const prizesLeft = p => p.prizes.reduce((s, z) => s + z.cards.length, 0);

async function main() {
  const { OnnxTokenAgent } = require('../agents.js');
  const { TokenEncoder } = require('../tokens.js');
  const enc = new TokenEncoder();
  const agent = await OnnxTokenAgent.load(SPEC.replace(/^onnxtok:/, '').replace(/:greedy$/, ''), enc, { seed: SEED, greedy: !SAMPLED });
  const decks = archivedDecks();
  const plays = [], turns = [];
  let errors = 0;
  for (let g = 0; g < GAMES; g++) {
    const a = decks[g % decks.length], b = decks[(g * 7 + 3) % decks.length];
    const env = new Env(enc, { u8: true });
    let t = env.reset(a.cards, b.cards, SEED * 100003 + g);
    let cur = null;                                       // the turn in progress: { turn, owner, prizes, attacked, trainers }
    const close = () => {
      if (!cur) return;
      const owner = env.game.state.players.find(p => p.id === cur.owner);
      cur.prizeTaken = cur.prizes - prizesLeft(owner);
      turns.push({ attacked: cur.attacked, prize: cur.prizeTaken > 0 });
      for (const p of cur.trainers) plays.push({ ...p, attacked: cur.attacked, prize: cur.prizeTaken > 0 });
    };
    let last = null;                                      // the Trainer whose prompt picks are being collected
    while (!t.done) {
      const st = env.game.state;
      const owner = st.players[st.activePlayer];
      if (!cur || cur.turn !== st.turn) {
        close();
        cur = { turn: st.turn, owner: owner.id, prizes: prizesLeft(owner), attacked: false, trainers: [] };
        last = null;
      }
      const [{ action }] = await agent.act([{ obs: t.obs, legal: t.legal, env }]);
      const d = env.game.decision();
      const key = env.current.options[t.legal.indexOf(action)].key;
      const mine = t.playerId === cur.owner;
      if (mine && !d.prompt && key.startsWith('trainer|')) {
        last = { card: key.split('|')[1], picks: [], deck: cur.owner === 1 ? a.name : b.name };
        cur.trainers.push(last);
      } else if (mine && d.prompt && last && key.startsWith('pick|')) {
        last.picks.push(key.slice(5));
      } else if (mine && !d.prompt) {
        last = null;
      }
      if (mine && key.startsWith('attack|')) cur.attacked = true;
      t = env.step(action);
    }
    close();
    if (t.error) errors++;
  }
  const base = { turns: turns.length, attack: turns.filter(x => x.attacked).length / turns.length,
                 prize: turns.filter(x => x.prize).length / turns.length };
  const by = new Map();
  for (const p of plays) {
    if (!by.has(p.card)) by.set(p.card, []);
    by.get(p.card).push(p);
  }
  const rows = [...by.entries()].sort((x, y) => y[1].length - x[1].length).map(([card, ps]) => {
    const picks = new Map();
    for (const p of ps) for (const k of p.picks) picks.set(k, (picks.get(k) || 0) + 1);
    return { card, plays: ps.length, attack: ps.filter(p => p.attacked).length / ps.length,
             prize: ps.filter(p => p.prize).length / ps.length,
             topPicks: [...picks.entries()].sort((x, y) => y[1] - x[1]).slice(0, 8) };
  });
  console.log(`${SPEC}${SAMPLED ? ' (sampled)' : ' (greedy)'}: ${GAMES} games, ${errors} errors; turns ${base.turns}, `
    + `attack ${(100 * base.attack).toFixed(1)}%, prize ${(100 * base.prize).toFixed(1)}%`);
  console.log('card                          plays  attack  prize   (same turn)');
  for (const r of rows.slice(0, 20)) {
    console.log(`${r.card.padEnd(28)} ${String(r.plays).padStart(6)}  ${(100 * r.attack).toFixed(1).padStart(5)}%  `
      + `${(100 * r.prize).toFixed(1).padStart(5)}%`);
  }
  if (JSON_OUT) fs.writeFileSync(JSON_OUT, JSON.stringify({ agent: SPEC, sampled: SAMPLED, games: GAMES, errors, base, rows }, null, 1));
}

main().catch(e => { console.error(e); process.exitCode = 1; });
