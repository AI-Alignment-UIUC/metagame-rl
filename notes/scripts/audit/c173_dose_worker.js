// C173's stage B1 (runs/probe/C173-search-table/record.md; research's #806): env/remote_worker.js unchanged, plus a LOG-ONLY wrapper on PolicySearchAgent.prototype.searchAll. One short JSON line to $C173_DOSE per searched decision: the game's seed and the player, so the reader can count searched decisions per game against each deck's Trainer count. No game changes.
'use strict';
const fs = require('fs');
const path = require('path');
const ENV = path.join(__dirname, '..', '..', '..', 'env');
const { Env } = require(path.join(ENV, 'env.js'));
const { PolicySearchAgent } = require(path.join(ENV, 'agents.js'));
const OUT = process.env.C173_DOSE;

const origReset = Env.prototype.reset;
Env.prototype.reset = function (a, b, seed, o) { const t = origReset.apply(this, arguments); this.game._seed = seed; return t; };
const orig = PolicySearchAgent.prototype.searchAll;
PolicySearchAgent.prototype.searchAll = function (items) {
  if (OUT) {
    const lines = items.map(({ b }) => JSON.stringify([b.env.game._seed, b.env.game.decision().playerId])).join('\n');
    if (lines) fs.appendFileSync(OUT, lines + '\n');
  }
  return orig.call(this, items);
};

// After #827: also log-only, $C173_CAPS (or the dose log + ".caps"): one line each time MAX_TURN_STEPS cuts a real game's main phase to pass, with the last keys played. Search's line copies carry no _seed, so they aren't logged.
const CAPS = process.env.C173_CAPS || (OUT ? OUT + '.caps' : '');
if (CAPS) {
  const { Game } = require(path.join(ENV, 'game.js'));
  const origDecision = Game.prototype.decision;
  Game.prototype.decision = function () {
    const before = this.turnCapped;
    const d = origDecision.apply(this, arguments);
    try {
      if (this._seed !== undefined && this.turnCapped > before) fs.appendFileSync(CAPS, JSON.stringify([this._seed, this.state.turn, this.steps, this.turnCapped, this._recent || []]) + '\n');
    } catch (e) { /* log only */ }
    return d;
  };
  const origStep = Env.prototype.step;
  Env.prototype.step = function (actionId) {
    try {
      if (this.game && this.game._seed !== undefined && this.current) {
        const o = this.current.options[this.current.legal.indexOf(actionId)];
        const r = this.game._recent || (this.game._recent = []);
        r.push(o ? String(o.key) : '?');
        if (r.length > 6) r.shift();
      }
    } catch (e) { /* log only */ }
    return origStep.apply(this, arguments);
  };
}

require(path.join(ENV, 'remote_worker.js'));
