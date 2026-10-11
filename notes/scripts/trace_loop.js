// Finds and prints a game that runs long between league agents (log #58): plays agent A on its deck
// against agent B on its deck (ONNX exports of notes/scripts/league_loops.py --export), sampled, until a
// game passes --long decisions, then prints its last --tail decisions (player, option key) and the
// most repeated decision sequence of that game.
//
// Run: node notes/scripts/trace_loop.js --dir <export dir> --a 4 --b 0 [--games 40] [--long 1500]
'use strict';
const path = require('path');
const fs = require('fs');
const root = path.resolve(__dirname, '../..');
const { Env } = require(path.join(root, 'env/env.js'));
const { TokenEncoder } = require(path.join(root, 'env/tokens.js'));
const { OnnxTokenAgent } = require(path.join(root, 'env/agents.js'));

const argv = process.argv.slice(2);
const flag = (n, d) => { const i = argv.indexOf('--' + n); return i === -1 ? d : argv[i + 1]; };
const dir = flag('dir');
const A = Number(flag('a')), B = Number(flag('b'));
const GAMES = Number(flag('games', 40)), LONG = Number(flag('long', 1500)), TAIL = Number(flag('tail', 60));

(async () => {
  const strategies = JSON.parse(fs.readFileSync(path.join(dir, 'strategies.json'), 'utf8'));
  const deckOf = slot => strategies.find(s => s.slot === slot).cards;
  const enc = new TokenEncoder();
  const agents = { 1: await OnnxTokenAgent.load(path.join(dir, `agent${A}.onnx`), enc, { seed: 1 }),
                   2: await OnnxTokenAgent.load(path.join(dir, `agent${B}.onnx`), enc, { seed: 2 }) };
  for (let g = 0; g < GAMES; g++) {
    const env = new Env(enc, { u8: true, showOpponentDecklist: true });
    let t = env.reset(deckOf(A), deckOf(B), 1000 + g);
    const hist = [];
    while (!t.done) {
      let action = t.legal[0];
      if (t.legal.length > 1) action = (await agents[t.playerId].act([{ obs: t.obs, legal: t.legal, env }]))[0].action;
      const key = env.current.options[t.legal.indexOf(action)].key;
      hist.push(`${t.playerId}:${key}`);
      t = env.step(action);
    }
    const st = env.game.state;
    console.log(`game ${g}: ${hist.length} decisions, winner ${t.winner}, ending ${env.game.ending}, turn ${st.turn}`);
    if (hist.length >= LONG) {
      console.log(`--- last ${TAIL} decisions of game ${g} ---`);
      console.log(hist.slice(-TAIL).join('\n'));
      const counts = new Map();
      for (let L = 2; L <= 6; L++) {
        for (let i = 0; i + L <= hist.length; i++) {
          const k = hist.slice(i, i + L).join(' | ');
          counts.set(k, (counts.get(k) || 0) + 1);
        }
      }
      const top = [...counts].sort((x, y) => y[1] * y[0].split('|').length - x[1] * x[0].split('|').length).slice(0, 5);
      console.log('--- most repeated sequences ---');
      for (const [k, c] of top) console.log(`${c}x  ${k}`);
      console.log(`turn at the end: ${st.turn}; hands ${st.players.map(p => p.hand.cards.length)}, decks ${st.players.map(p => p.deck.cards.length)}`);
      break;
    }
  }
})();
