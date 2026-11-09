// C115: the Goldfish, a passive scripted agent on env/agents.js's interface (act(batch) -> [{ action, logp, value }], action an
// index into b.legal, options read from b.env.current.options keys). Setup: an Active and up to 5 benched Basics. Each turn: bench a
// Basic if offered, else pass. Never an Energy, Trainer, attack, retreat, evolution or ability. Prompts: promotion and other
// choices take the first legal pick; 'done' once something is picked; multi-pick prompts for starting Pokemon take up to 6.
'use strict';
class GoldfishAgent {
  constructor() { this.counts = { basic: 0, pass: 0, prompt: 0, other: 0 }; }
  async act(batch) {
    return batch.map(b => {
      const game = b.env.game, options = b.env.current.options, d = game.decision();
      const keys = options.map(o => o.key);
      let idx;
      if (d && d.prompt) {
        this.counts.prompt++;
        const picks = game.picks ? game.picks.length : 0, done = keys.indexOf('done');
        const pick = keys.findIndex(k => k.startsWith('pick|'));
        if (pick >= 0 && picks < 6) idx = pick;
        else if (done >= 0) idx = done;
        else idx = keys.findIndex(k => k !== 'cancel');
        if (idx < 0) idx = 0;
      } else {
        idx = keys.findIndex(k => k.startsWith('basic|'));
        if (idx >= 0) this.counts.basic++;
        else { idx = keys.indexOf('pass'); if (idx >= 0) this.counts.pass++; else { idx = 0; this.counts.other++; } }
      }
      return { action: b.legal[idx], logp: 0, value: 0 };
    });
  }
}
module.exports = { GoldfishAgent };
