// C132 (goldfish under the pilot's own search; copy of goldfish_worker2.js): the same passive Goldfish seat and C114's log-only
// trace hook (pace_worker2.js), plus one guard. A search line's copy (Game.prototype.clone) gets _pdone, which the hook already
// skips, so the simulated lines of PolicySearchAgent never write trace rows; only the real games do.
'use strict';
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Runner } = require(path.join(ENV, 'runner.js'));
const { Game } = require(path.join(ENV, 'game.js'));
const { GoldfishAgent } = require('./goldfish_agent.js');
const { PolicySearchAgent } = require(path.join(ENV, 'agents.js'));
PolicySearchAgent.lineOpponents.goldfish = new GoldfishAgent();   // C132b: judgeSearch.lineOpponent "goldfish" plays it inside lines

const origClone = Game.prototype.clone;
Game.prototype.clone = function (...a) { const g = origClone.apply(this, a); g._pdone = true; return g; };

const origRun = Runner.prototype.run;
Runner.prototype.run = function (nextJob, agents, o) {
  if (!agents.goldfish) agents.goldfish = Object.assign(new GoldfishAgent(), { stats: {} });   // stats: the search runner sums searchers' stats
  const wrapped = (...a) => {
    const job = nextJob(...a);
    if (job) job.seats = { ...job.seats, [job.seed % 2 === 0 ? 2 : 1]: 'goldfish' };
    return job;
  };
  return origRun.call(this, wrapped, agents, o);
};

require('./pace_worker2.js');
