// C115 (goldfish probe): C114's pace_worker.js (the log-only hook, and env/remote_worker.js beneath it) with a passive Goldfish agent
// registered from here, no env/ edit. Runner.prototype.run is wrapped so that one seat of every game, chosen by seed parity (even
// seed: seat 2, odd: seat 1), is played by the Goldfish; the other seat stays whatever the job named (SimpleBot or the model slot).
// The jobs are list-against-itself (i == j), so both seats start with the same name and only the Goldfish seat is renamed.
'use strict';
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Runner } = require(path.join(ENV, 'runner.js'));
const { GoldfishAgent } = require('./goldfish_agent.js');

const origRun = Runner.prototype.run;
Runner.prototype.run = function (nextJob, agents, o) {
  if (!agents.goldfish) agents.goldfish = new GoldfishAgent();
  const wrapped = (...a) => {
    const job = nextJob(...a);
    if (job) job.seats = { ...job.seats, [job.seed % 2 === 0 ? 2 : 1]: 'goldfish' };
    return job;
  };
  return origRun.call(this, wrapped, agents, o);
};

require('./pace_worker.js');
