// C117's validity check (research, 2026-10-28): pace-traced games of a pilot against C115b's scripted Wigglytuff. The seat whose
// deck name starts with 'OPP ' is played by wiggly_agent.js; the other stays the model slot the job named. C114's log-only
// per-turn hook (pace_worker2.js, env/remote_worker.js beneath it) writes one JSON line per game to $PACE_TRACE_OUT.
'use strict';
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Runner } = require(path.join(ENV, 'runner.js'));
const { WigglyAgent } = require('./wiggly_agent.js');

const origRun = Runner.prototype.run;
Runner.prototype.run = function (nextJob, agents, o) {
  if (!agents.wiggly) agents.wiggly = new WigglyAgent();
  const wrapped = (...a) => {
    const job = nextJob(...a);
    if (job) job.seats = { 1: job.deckName.startsWith('OPP ') ? 'wiggly' : job.seats[1], 2: job.deckBName.startsWith('OPP ') ? 'wiggly' : job.seats[2] };
    return job;
  };
  return origRun.call(this, wrapped, agents, o);
};

require('./pace_worker2.js');
