// X5 (notes/scripts/probe_filler.py, runs/probe/X5-filler/record.md): env/remote_worker.js unchanged, plus a count, per
// deck, of the moves that attach an Energy or play or use a Trainer, by card ("attach|Water Energy BS": n), sent with
// each reply that has game results as `use`. Nothing in env/ is edited: Runner.run is wrapped to see every asked
// decision (forced one-option moves are never asked, so never counted), and framing.js's writeJson to add the counts.
// The wrap only reads the state, so the games are the ones env/remote_worker.js plays.
'use strict';
const { Runner } = require('../runner.js');
const F = require('../framing.js');

const VERBS = new Set(['attach', 'trainer', 'tip']);
let use = {};

const run = Runner.prototype.run;
Runner.prototype.run = function (nextJob, agents, opts = {}) {
  const inner = opts.onDecision;
  const onDecision = (s, answer, k) => {
    const cur = s.env.current;                     // the state decided in (runner.js calls this before the step)
    const opt = cur && cur.options[cur.legal.indexOf(answer.action)];
    const [verb, card] = opt ? opt.key.split('|') : [];
    if (VERBS.has(verb)) {
      const deck = s.t.playerId === 1 ? s.job.deckName : s.job.deckBName;
      const c = use[deck] || (use[deck] = {});
      c[verb + '|' + card] = (c[verb + '|' + card] || 0) + 1;
    }
    if (inner) inner(s, answer, k);
  };
  return run.call(this, nextJob, agents, { ...opts, onDecision });
};

const writeJson = F.writeJson;
F.writeJson = (stream, obj) => {
  if (obj && obj.ok && Array.isArray(obj.results)) { obj.use = use; use = {}; }
  writeJson(stream, obj);
};

require('../remote_worker.js');
