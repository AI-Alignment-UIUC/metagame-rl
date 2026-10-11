// Picks the next match for the remote worker's 'league' command (env/remote_worker.js).
//
// Without cmd.slotQuota: a uniformly random match until `transitions` decisions are recorded in all.
// With cmd.slotQuota ({ slot: transitions }, rl/tournament.py, log #61): only matches whose recorded
// (focal) side has not reached its slot's quota are drawn, and no new game starts once every quota is
// met, so an agent whose deck makes short games still gets its share; `transitions` stays a hard cap.
// Games already started always finish, so a slot ends somewhat above its quota.
'use strict';

function makeLeagueNextJob(cmd, rng, nameOf) {
  const quota = cmd.slotQuota || null;
  const focal = m => (m.a.record ? m.a.slot : m.b.record ? m.b.slot : null);
  const counts = new Map();
  let seen = 0, n = 0;
  const nextJob = (recorded, rec) => {
    if (recorded >= cmd.transitions) return null;
    let m;
    if (!quota) {
      m = cmd.matches[rng.int(cmd.matches.length)];
    } else {
      for (; seen < rec.slot.length; seen++) counts.set(rec.slot[seen], (counts.get(rec.slot[seen]) || 0) + 1);
      const open = cmd.matches.filter(x => {
        const s = focal(x);
        return s !== null && quota[s] !== undefined && (counts.get(s) || 0) < quota[s];
      });
      if (open.length === 0) return null;
      m = open[rng.int(open.length)];
    }
    const [x, y] = rng.int(2) === 0 ? [m.a, m.b] : [m.b, m.a];
    return { deckA: x.deck.cards, deckB: y.deck.cards, deckName: x.deck.name, deckBName: y.deck.name,
             seed: cmd.seed * 100003 + n++, seats: { 1: nameOf(x), 2: nameOf(y) } };
  };
  nextJob.counts = counts;
  return nextJob;
}

module.exports = { makeLeagueNextJob };
