// C115b: a scripted best-case Wigglytuff pilot (evaluation only), on env/agents.js's interface (act(batch) -> [{ action, logp, value }]).
// Main phase, in priority: Bill whenever held; bench every Basic (line first); evolve (Active first); attach Energy to the Wigglytuff line
// (Active first, Double Colorless when it pays); Computer Search / Item Finder for a missing piece; PlusPower on an Active that can Do the Wave;
// Professor Oak when the line lacks a piece and the hand is otherwise spent; retreat to a benched Wigglytuff that can attack; attack (Do the Wave,
// else the highest printed damage); else pass. The deck has no Switch. Prompts: discard the least useful card, search Wigglytuff > Jigglypuff >
// Energy > PlusPower, promote a Wigglytuff, setup picks the line first.
'use strict';
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { C } = require(path.join(ENV, 'engine.js'));
const { allSlots } = require(path.join(ENV, 'legal.js'));

const bare = n => String(n).replace(/ [A-Z0-9]+$/, '');
const isWig = n => bare(n) === 'Wigglytuff', isJig = n => bare(n) === 'Jigglypuff';
const isEnergy = n => /Energy$/.test(bare(n)) && !/Retrieval|Removal/.test(bare(n));
const isLine = n => isWig(n) || isJig(n);
const isDCE = n => bare(n) === 'Double Colorless Energy', isPP = n => bare(n) === 'PlusPower';
const KEEP = n => isWig(n) ? 10 : isJig(n) ? 9 : isDCE(n) ? 8 : bare(n) === 'Fighting Energy' ? 7 : isPP(n) ? 6
  : ['Bill', 'Professor Oak'].includes(bare(n)) ? 5 : bare(n) === 'Computer Search' ? 4 : bare(n) === 'Item Finder' ? 3 : 0;
const SEARCH = n => isWig(n) ? 5 : isJig(n) ? 4 : isDCE(n) ? 3.5 : isEnergy(n) ? 3 : isPP(n) ? 2 : 0;
const energyOf = slot => slot.energies.cards.reduce((s, c) => s + (isDCE(c.name) ? 2 : 1), 0);
const topName = slot => { const c = slot.getPokemonCard(); return c ? c.name : ''; };

class WigglyAgent {
  constructor() { this.counts = { main: 0, prompt: 0 }; }
  async act(batch) { return batch.map(b => ({ action: b.legal[this.pick(b)], logp: 0, value: 0 })); }

  pick(b) {
    const game = b.env.game, d = game.decision(), keys = b.env.current.options.map(o => o.key);
    const me = game.state.players.find(p => p.id === d.playerId);
    const idx = d.prompt ? this.prompt(game, d, keys, me) : this.main(game, keys, me);
    return idx >= 0 ? idx : (keys.indexOf('pass') >= 0 ? keys.indexOf('pass') : 0);
  }

  // ---------------------------------------------------------------- main phase
  main(game, keys, me) {
    this.counts.main++;
    const find = f => keys.findIndex(f), has = p => find(k => k.startsWith(p));
    const hand = me.hand.cards, handN = f => hand.filter(c => f(c.name)).length;
    const inPlay = [me.active, ...me.bench].filter(s => s.pokemons.cards.length > 0);
    const lineIn = f => inPlay.some(s => f(topName(s)));
    const wigAny = lineIn(isWig) || handN(isWig) > 0;
    const lineAny = wigAny || lineIn(isJig) || handN(isJig) > 0;
    const slots = allSlots(game.state, me).filter(s => s.mine && s.slot.pokemons.cards.length > 0);
    let i;
    // 1. Bill whenever held (C115B_BILL_OUT: log each main decision with Bill in hand, and whether it was offered)
    if (process.env.C115B_BILL_OUT && handN(n => bare(n) === 'Bill') > 0) require('fs').appendFileSync(process.env.C115B_BILL_OUT, (has('trainer|Bill ') >= 0 ? 'offered' : 'held-not-offered') + '\n');
    if ((i = has('trainer|Bill ')) >= 0) return i;
    // 2. bench every Basic, line first
    const basics = keys.map((k, j) => [k, j]).filter(([k]) => k.startsWith('basic|'))
      .sort((x, y) => (isLine(y[0].slice(6)) ? 1 : 0) - (isLine(x[0].slice(6)) ? 1 : 0));
    if (basics.length) return basics[0][1];
    // 3. evolve, Active first
    if ((i = find(k => k.startsWith('evolve|Wigglytuff') && k.endsWith('|A'))) >= 0) return i;
    if ((i = has('evolve|Wigglytuff')) >= 0) return i;
    // 4. attach Energy to the line: targets that still need Energy first, Active before Bench, Wigglytuff before Jigglypuff
    let best = null;
    keys.forEach((k, j) => {
      const p = k.split('|');
      if (p[0] !== 'attach') return;
      const s = slots.find(x => x.code === p[2]);
      if (!s || !isLine(topName(s.slot))) return;
      const e = energyOf(s.slot), dce = isDCE(p[1]);
      const score = (e < 3 ? 100 : 0) + (p[2] === 'A' ? 30 : 0) + (isWig(topName(s.slot)) ? 10 : 0) + (dce ? (e <= 1 ? 5 : -5) : 0);
      if (!best || score > best.score) best = { score, j };
    });
    if (best) return best.j;
    // 5. Computer Search / Item Finder for a missing piece (each costs 2 cards)
    const lineEnergy = inPlay.filter(s => isLine(topName(s))).reduce((a, s) => a + energyOf(s), 0);
    if (hand.length - 1 >= 2) {
      const need = !wigAny || !lineAny || (handN(isEnergy) === 0 && lineEnergy < 3);
      if (need && (i = has('trainer|Computer Search')) >= 0) return i;
      if (handN(isPP) === 0 && me.discard.cards.some(c => isPP(c.name)) && (i = has('trainer|Item Finder')) >= 0) return i;
    }
    // 6. PlusPower before attacking, if held
    const canWave = keys.indexOf('attack|Do the Wave') >= 0;
    if (canWave && (i = find(k => k.startsWith('trainer|PlusPower') && (k.endsWith('|A') || k.endsWith('|-')))) >= 0) return i;
    // 1b. Oak: the hand lacks a piece of the line and holds nothing else of value
    const missing = !lineAny || handN(isEnergy) === 0 || handN(isPP) === 0;
    const spent = !hand.some(c => KEEP(c.name) >= 5 && bare(c.name) !== 'Professor Oak');
    if (missing && spent && (i = has('trainer|Professor Oak')) >= 0) return i;
    // 7. retreat to a benched Wigglytuff that can attack when the Active is not a Wigglytuff that can
    if (!(isWig(topName(me.active)) && canWave)) {
      for (const s of slots.filter(x => x.code.startsWith('B') && isWig(topName(x.slot)) && energyOf(x.slot) >= 3))
        if ((i = keys.indexOf('retreat|' + s.code)) >= 0) return i;
    }
    // 8. attack: Do the Wave, else the highest printed damage, else pass
    if (canWave) return keys.indexOf('attack|Do the Wave');
    const atks = keys.map((k, j) => [k, j]).filter(([k]) => k.startsWith('attack|'));
    if (atks.length) {
      const card = me.active.getPokemonCard(), dmg = k => { const a = card.attacks.find(x => x.name === k.slice(7)); return a ? parseInt(a.damage, 10) || 0 : 0; };
      atks.sort((x, y) => dmg(y[0]) - dmg(x[0]));
      return atks[0][1];
    }
    return keys.indexOf('pass');
  }

  // ---------------------------------------------------------------- prompts
  prompt(game, d, keys, me) {
    this.counts.prompt++;
    const p = d.prompt, picks = keys.map((k, j) => [k, j]).filter(([k]) => k.startsWith('pick|'));
    const done = keys.indexOf('done'), name = k => k.slice(5);
    const setup = game.state.phase === C.GamePhase.SETUP;
    if (picks.length && !(done >= 0 && !(setup && game.picks.length < 6))) {
      if (p.type === 'Choose pokemon') return this.promote(game, me, picks, name);
      const cs = p.cards && p.cards.cards ? p.cards.cards : [];
      if (cs.length && me.deck.cards.includes(cs[0]) || cs.length && me.discard.cards.includes(cs[0]))
        return picks.reduce((a, c) => SEARCH(name(c[0])) > SEARCH(name(a[0])) ? c : a)[1];
      if (p.message === C.GameMessage.CHOOSE_CARD_TO_DISCARD || p.type === 'Choose energy')
        return picks.reduce((a, c) => KEEP(name(c[0])) < KEEP(name(a[0])) ? c : a)[1];
      return picks.reduce((a, c) => KEEP(name(c[0])) > KEEP(name(a[0])) ? c : a)[1];
    }
    if (done >= 0) return done;
    const yes = keys.indexOf('res|yes');
    return yes >= 0 ? yes : keys.findIndex(k => k !== 'cancel');
  }

  promote(game, me, picks, name) {
    const slots = allSlots(game.state, me).filter(s => s.mine);
    const score = code => { const s = slots.find(x => x.code === code); if (!s) return -1; const n = topName(s.slot); return (isWig(n) ? 100 : isJig(n) ? 50 : 0) + energyOf(s.slot); };
    return picks.reduce((a, c) => score(name(c[0])) > score(name(a[0])) ? c : a)[1];
  }
}
module.exports = { WigglyAgent };
