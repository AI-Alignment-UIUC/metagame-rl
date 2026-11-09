// A1 (runs/probe/A1-targetsignal/record.md; notes/scripts/probe_target_signal.py; evaluation only, nothing trains on
// what it measures). A COPY of env/tools/probe_oracle_worker.js (X1b), its oracle replaced by a measure-only probe.
//
// The live games are played by the pilot exactly as env/remote_worker.js plays them: the live game always goes on with
// the pilot's OWN answer (sampled, or greedy with cmd.greedy). At a decision in a stratum the command still needs
// (cmd.probe.need), the worker branches it: for each of up to cap answers (all, or the pilot's greedy answer, the answer
// the live game took, and uniform draws) and each of m re-dealt copies of the game (the same seeds for every answer: common
// random numbers), it plays the answer and then the game to its end with the pilot SAMPLED at temperature 1 on both seats.
//
// Strata: a prompt inside the deciding seat's own Trainer (game.chain.key starts 'trainer|' and the open prompt is that
// seat's, as X1) with at least 2 answers other than 'cancel' (stratum = the Trainer's name if it is one of NAMED, else
// 'other'), and a main-phase decision with at least 2 options ('main', the control). A decision is probed with probability
// probe.p (main: probe.mainP), at most probe.maxPerGame prompts (main: 1) a game, while its stratum's need is above 0
// ('any' is the need of prompts of any Trainer, the named ones included).
//
// Sampling the lines is common-random-number too: a line's pilot answer is drawn in JS from the pilot's probabilities (the
// server returns them for requests with probs: 1, rl/ driver notes/scripts/probe_target_signal.py ProbePool) by an Rng
// seeded by the rollout's seed, so rollout j draws from the same stream for every answer.
//
// Per probe the reply carries the lines' rewards and the seat's values at its own asked decisions after the answer, the
// prompt row's observation as sent to the model, V0, the answers, and (after the live game ends) the live game's own
// seat values after the probed row and its terminal reward, for the realized GAE advantage of the answer taken.
//
// A rollout worker whose policies run in the learner process (rl/remote.py). Commands: info, games, quit. "games" is as
// env/remote_worker.js "games" (decks, jobs, greedy, concurrency, roundTurns, history, chain, deckoutWin) plus
//   probe: { m, cap, maxLine, p, mainP, maxPerGame, need: { <Trainer>: n, any: n, main: n }, minValid }
'use strict';
const { Runner } = require('../runner.js');
const { Encoder } = require('../encode.js');
const { TokenEncoder } = require('../tokens.js');
const { archivedDecks } = require('../decks.js');
const { Rng } = require('../rng.js');
const F = require('../framing.js');
const { Game } = require('../game.js');
const { C, newStore } = require('../engine.js');
const { Env } = require('../env.js');

const decks = archivedDecks();
const identity = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
const tokens = new TokenEncoder();
const NAMED = ['Computer Search', 'Super Energy Removal', 'Energy Removal', 'Energy Retrieval', 'Gust of Wind'];

const pending = new Map();
let nextId = 1;
let nextGameUid = 1;
let drops = [];

// As the oracle's RemoteAgent, plus probs: the server also returns each row's probabilities over its legal ids (aligned
// with the row's legal list) as `probs`.
class RemoteAgent {
  constructor(slot, encoding, greedy = false, probs = false) {
    this.slot = slot; this.encoding = encoding; this.greedy = greedy; this.probs = probs;
  }

  forget(game) { if (game.uid) { drops.push(game.uid); game.uid = 0; } }

  act(batch) {
    const n = batch.length;
    const id = nextId++;
    const keys = new Int32Array(n);
    batch.forEach((b, i) => {
      const g = b.env.game;
      if (!g.uid) g.uid = nextGameUid++;
      keys[i] = g.uid * 2 + (b.env.current.playerId - 1);
    });
    const L = batch.reduce((a, b) => a + b.legal.length, 0);
    const offsets = new Int32Array(n + 1), ids = new Int32Array(L);
    let p = 0;
    batch.forEach((b, i) => { offsets[i] = p; ids.set(b.legal, p); p += b.legal.length; });
    offsets[n] = p;
    const e = tokens;
    const tc = new Int16Array(n * e.MAX_TOK), tk = new Uint8Array(n * e.MAX_TOK), ta = new Uint8Array(n * e.MAX_TOK);
    const gl = new Uint8Array(n * e.GLOB_F), sl = new Uint8Array(n * 12 * e.SLOT_F), cd = new Int16Array(n * e.MAX_CAND * 6);
    const nc = new Int32Array(n);
    batch.forEach((b, i) => {
      const o = b.obs;
      tc.set(o.tokCard, i * e.MAX_TOK); tk.set(o.tokKind, i * e.MAX_TOK); ta.set(o.tokAux, i * e.MAX_TOK);
      gl.set(o.glob, i * e.GLOB_F); sl.set(o.slots, i * 12 * e.SLOT_F); cd.set(o.cand, i * e.MAX_CAND * 6); nc[i] = o.nCand;
    });
    const arrays = [['tok_card', tc], ['tok_kind', tk], ['tok_aux', ta], ['glob', gl], ['slots', sl], ['cand', cd], ['n_cand', nc],
      ['legal_offsets', offsets], ['legal_ids', ids], ['keys', keys], ['drop', Int32Array.from(drops)]];
    drops = [];
    F.writeFrame(process.stdout, F.REQUEST, F.packArrays({ id, slot: this.slot, n, encoding: this.encoding, greedy: this.greedy,
      ...(this.probs ? { probs: 1 } : {}) }, arrays));
    return new Promise(resolve => { resolve.off = offsets; pending.set(id, resolve); });
  }
}

// ---- Copies of the live game (X1b's, unchanged: see probe_oracle_worker.js for the long comments) ----
const TIERS = [
  { name: 'full', own: true, oppHand: true },
  { name: 'oppHandSeen', own: true, oppHand: false },
  { name: 'ownDeckSeen', own: false, oppHand: true },
  { name: 'bothSeen', own: false, oppHand: false },
  { name: 'none' },
];

function visible(state, me) {
  const names = cs => cs.map(c => c.fullName).sort().join(',');
  const parts = [state.turn, state.activePlayer, state.phase];
  for (const p of state.players) {
    parts.push(p.id, p.id === me ? names(p.hand.cards) : p.hand.cards.length, p.deck.cards.length,
      p.prizes.map(z => z.cards.length).join(','), names(p.discard.cards), names(p.stadium.cards));
    for (const s of [p.active, ...p.bench]) {
      parts.push(s.pokemons.cards.map(c => c.fullName).join('>'), names(s.energies.cards), names(s.trainers.cards), s.damage,
        s.specialConditions.join('+'));
    }
  }
  return parts.join('|');
}
const keySet = opts => opts.map(o => o.key).sort().join('\n');

// A prompt is open inside a Trainer: rebuilt from game.chain with what the seat cannot see re-dealt (tier), null if the
// copy does not show the seat what the live game shows it.
function copyAtPrompt(live, me, seed, tier, liveOptions) {
  const base = C.deepClone(live.chain.base, [C.Card]);
  const rng = new Rng(seed);
  if (tier.name !== 'none') {
    for (const p of base.players) {
      const zones = p.id === me ? (tier.own ? [p.deck, ...p.prizes] : []) : [...(tier.oppHand ? [p.hand] : []), p.deck, ...p.prizes];
      const side = new Rng((seed ^ (p.id === me ? 0x5eed0001 : 0x5eed0002)) >>> 0);
      const pool = zones.flatMap(z => z.cards), order = side.permutation(pool.length);
      let k = 0;
      for (const z of zones) z.cards = z.cards.map(() => pool[order[k++]]);
    }
  }
  const g = Object.create(Game.prototype);
  g.rng = rng;
  g.store = newStore(C.deepClone(base, [C.Card]));
  g.store.cardRanks = live.store.cardRanks;
  Object.assign(g, { steps: live.steps, picks: [], pickedKeys: [], space: null, spaceFor: -1, cached: null, error: null,
    deadEnds: [], turnMark: { ...live.turnMark }, turnCapped: live.turnCapped, maxTurns: live.maxTurns,
    roundTurns: live.roundTurns, history: live.history.slice() });
  g.chain = { base, log: live.chain.log.slice(), noop: new Map(), key: live.chain.key };
  try {
    for (const e of live.chain.log) {
      if (e.action) { g.store.dispatch(e.action); continue; }
      const p = g.store.state.prompts.find(q => q.id === e.promptId);
      g.store.dispatch(new C.ResolvePromptAction(e.promptId, p.decode(e.raw, g.store.state)));
    }
    const lp = live.openPrompt(), cp = g.openPrompt();
    if (!cp || cp.id !== lp.id || cp.type !== lp.type) return null;
    for (const key of live.pickedKeys) {
      const d = g.decision();
      const j = d ? d.options.findIndex(o => o.key === key) : -1;
      if (j === -1) return null;
      g.step(j);
    }
  } catch (e) {
    return null;
  }
  g.steps = live.steps; g.history = live.history.slice(); g.cached = null;
  const d = g.decision();
  if (!d || g.error || d.playerId !== me || keySet(d.options) !== keySet(liveOptions)) return null;
  if (visible(g.state, me) !== visible(live.state, me)) return null;
  return g;
}

// A main-phase decision: Game.clone with the seat's hidden cards re-dealt (env/agents.js PolicySearchAgent's copy).
function copyAtMain(live, me, seed, liveOptions) {
  try {
    const g = live.clone(new Rng(seed), me);
    const d = g.decision();
    if (!d || g.error || d.playerId !== me || keySet(d.options) !== keySet(liveOptions)) return null;
    return g;
  } catch (e) {
    return null;
  }
}

// ---- The probe ----
let P = null;                 // this command's cmd.probe
let stats = null;
let trackList = [];           // [{ rec, g, me }]: probes whose live game's later values and result are still to be filled in
const newStats = () => ({ asked: 0, acts: 0, eligible: {}, probes: 0, probesByStratum: {}, unsearchable: 0, lines: 0, capped: 0,
                          lineErrors: 0, lineAsked: 0, rounds: 0, probeMs: 0, tier_full: 0, tier_oppHandSeen: 0, tier_ownDeckSeen: 0,
                          tier_bothSeen: 0, tier_none: 0, tier_main: 0, droppedCopies: 0 });

// Lines played in lockstep to the game's end, the pilot sampled from its probabilities by each line's own Rng. A line
// longer than maxLine asked decisions is cut and scored by the pilot's value there (from the seat's side).
async function playLines(lines, sampler, maxLine) {
  for (;;) {
    const ask = [];
    for (const l of lines) {
      if (l.done) continue;
      let guard = 0;
      while (!l.t.done && l.t.legal.length === 1 && guard++ < 100000) l.t = l.env.step(l.t.legal[0]);
      if (l.t.done) {
        if (l.t.error || guard > 100000) stats.lineErrors++;
        l.reward = l.env.game.reward(l.me, P.deckoutWin);
        l.done = true;
        continue;
      }
      ask.push(l);
    }
    if (!ask.length) return;
    stats.lineAsked += ask.length; stats.rounds++;
    const ev = await sampler.act(ask.map(l => ({ obs: l.t.obs, legal: l.t.legal, env: l.env })));
    ask.forEach((l, i) => {
      const v = ev[i].value, mine = l.t.playerId === l.me;
      if (mine) l.vals.push(v);
      if (++l.asked >= maxLine) { l.reward = mine ? v : -v; l.capped = true; l.done = true; stats.capped++; return; }
      const pr = ev[i].probs;
      let x = l.rng.float(), k = 0;
      for (; k < pr.length - 1; k++) { x -= pr[k]; if (x < 0) break; }
      l.t = l.env.step(l.t.legal[k]);
    });
  }
}

const NAME_KEY = key => key.split('|')[1].replace(/ [A-Z0-9]+$/, '');   // 'Computer Search BS' -> 'Computer Search'

class SwitchAgent {
  constructor(inner) {
    this.inner = inner; this.slot = inner.slot;
    this.greedy = new RemoteAgent(inner.slot, 'tokens', true);
    this.sampler = new RemoteAgent(inner.slot, 'tokens', true, true);
  }

  forget(game) { this.inner.forget(game); }

  // The batch's stratum for an asked decision, or null (not eligible).
  stratum(b) {
    const g = b.env.game, opts = b.env.current.options, me = b.env.current.playerId;
    if (g.decision().prompt) {
      const turnPlayer = g.state.players[g.state.activePlayer].id;
      if (!g.chain || !g.chain.key.startsWith('trainer|') || me !== turnPlayer) return null;
      if (b.legal.filter(a => opts[a].key !== 'cancel').length < 2) return null;
      const name = NAME_KEY(g.chain.key);
      return { prompt: true, trainer: g.chain.key.split('|')[1], s: NAMED.includes(name) ? name : 'other' };
    }
    return b.legal.length >= 2 ? { prompt: false, trainer: 'main', s: 'main' } : null;
  }

  want(b, st) {
    const g = b.env.game, need = P.need;
    const r = new Rng((g.rng.clone().u32() ^ Math.imul(g.steps + 1, 0x9e3779b1) ^ 0x1b873593) >>> 0).float();
    if (!st.prompt) {
      if (!(need.main > 0) || (g.probesMain || 0) >= 1 || r >= P.mainP) return false;
      need.main--; g.probesMain = (g.probesMain || 0) + 1;
      return true;
    }
    const named = st.s !== 'other' && need[st.s] > 0;
    if (!(named || need.any > 0) || (g.probesPrompt || 0) >= P.maxPerGame || r >= P.p) return false;
    if (named) need[st.s]--;
    if (need.any > 0) need.any--;
    g.probesPrompt = (g.probesPrompt || 0) + 1;
    return true;
  }

  async act(batch) {
    const out = await this.inner.act(batch);
    stats.acts++;
    const cand = [];
    batch.forEach((b, i) => {
      const g = b.env.game, me = b.env.current.playerId;
      if (g.tracks) for (const t of g.tracks) if (t.me === me) t.vals.push(out[i].value);   // the live seat's later values
      stats.asked++;
      if (!P) return;
      const st = this.stratum(b);
      if (!st) return;
      stats.eligible[st.s] = (stats.eligible[st.s] || 0) + 1;
      if (this.want(b, st)) cand.push({ b, st, o: out[i] });
    });
    for (const c of cand) await this.probe(c.b, c.st, c.o);
    return out;
  }

  async probe(b, st, o) {
    const t0 = Date.now();
    const g = b.env.game, me = b.env.current.playerId, opts = b.env.current.options, prompt = st.prompt;
    const [ev] = await this.greedy.act([b]);                      // the prompt row's value and the pilot's greedy answer
    const V0 = ev.value, greedy = ev.action, taken = o.action;
    const ok = b.legal.filter(a => !prompt || opts[a].key !== 'cancel');
    const prng = new Rng((g.rng.clone().u32() ^ Math.imul(g.steps + 1, 0x9e3779b1) ^ 0x2545f491) >>> 0);
    let answers = [];
    if (ok.length <= P.cap) answers = ok.slice();
    else {
      for (const a of [greedy, taken]) if (ok.includes(a) && !answers.includes(a)) answers.push(a);
      const rest = ok.filter(a => !answers.includes(a));
      const perm = prng.permutation(rest.length);
      for (let k = 0; answers.length < P.cap && k < perm.length; k++) answers.push(rest[perm[k]]);
    }
    const srng = new Rng((g.rng.clone().u32() ^ Math.imul(g.steps + 1, 0x9e3779b1) ^ 0x0b1e5eed) >>> 0);
    const seeds = Array.from({ length: P.m }, () => srng.u32());
    const tiers = seeds.map(s => prompt ? TIERS.find(t => copyAtPrompt(g, me, s, t, opts)) || null : (copyAtMain(g, me, s, opts) ? 'main' : null));
    const valid = tiers.map((t, j) => (t ? j : -1)).filter(j => j >= 0);
    stats.droppedCopies += P.m - valid.length;
    if (valid.length < P.minValid) { stats.unsearchable++; return; }
    const tierCount = {};
    for (const j of valid) {
      const name = prompt ? tiers[j].name : 'main';
      stats['tier_' + name]++; tierCount[name] = (tierCount[name] || 0) + 1;
    }
    const lines = [];
    answers.forEach((a, ai) => valid.forEach(j => {
      const env = new Env(tokens, { showOpponentDecklist: b.env.showOpponentDecklist, u8: b.env.u8 });
      env.game = prompt ? copyAtPrompt(g, me, seeds[j], tiers[j], opts) : copyAtMain(g, me, seeds[j], opts);
      if (!env.game) throw new Error('probe: a validated copy did not rebuild');
      env.decklists = b.env.decklists;
      env.observe();
      const idx = env.current.options.findIndex(x => x.key === opts[a].key);
      if (idx === -1) throw new Error('probe: answer not on offer in a validated copy');
      lines.push({ ai, j, me, env, t: env.step(env.current.legal[idx]), rng: new Rng((seeds[j] ^ 0x7a31c0de) >>> 0),
                   asked: 0, vals: [], reward: null, capped: false, done: false });
    }));
    stats.lines += lines.length;
    await playLines(lines, this.sampler, P.maxLine);
    const rew = answers.map(() => new Array(P.m).fill(null)), vals = answers.map(() => new Array(P.m).fill(null));
    let capped = 0;
    for (const l of lines) { rew[l.ai][l.j] = l.reward; vals[l.ai][l.j] = l.vals.map(v => Math.round(v * 1e4) / 1e4); capped += l.capped; }
    const ob = b.obs;
    const rec = {
      game: process.pid + ':' + g.uid, turn: g.state.turn, seat: me, stratum: st.s, trainer: st.trainer, prompt,
      type: prompt ? g.openPrompt().type : 'main', message: prompt ? String(g.openPrompt().message || '') : '',
      step: prompt ? g.pickedKeys.length : 0, legal: b.legal.slice(), keys: b.legal.map(a => opts[a].key),
      answers, taken, greedy, V0, m: P.m, valid, tiers: tierCount, capped, rew, vals, liveVals: null, liveReward: null,
      obs: { tok_card: Array.from(ob.tokCard), tok_kind: Array.from(ob.tokKind), tok_aux: Array.from(ob.tokAux),
             glob: Array.from(ob.glob), slots: Array.from(ob.slots), cand: Array.from(ob.cand), n_cand: ob.nCand },
    };
    const track = { me, vals: [] };
    (g.tracks = g.tracks || []).push(track);
    rec.liveVals = track.vals;
    trackList.push({ rec, g, me });
    stats.probes++; stats.probesByStratum[st.s] = (stats.probesByStratum[st.s] || 0) + 1;
    stats.probeMs += Date.now() - t0;
    this.out.push(rec);
  }
}

async function games(cmd) {
  const t0 = Date.now(), cpu0 = process.cpuUsage();
  P = cmd.probe ? { cap: 8, m: 32, maxLine: 600, p: 0.3, mainP: 0.02, maxPerGame: 3, minValid: 16, deckoutWin: cmd.deckoutWin ?? 1,
                    ...cmd.probe, need: { ...cmd.probe.need } } : null;
  stats = newStats();
  trackList = [];
  const probes = [];
  const agents = {};
  const pilot = i => {
    const slot = cmd.slots ? cmd.slots[i] : 0;
    const name = 'o' + slot;
    if (!agents[name]) { agents[name] = new SwitchAgent(new RemoteAgent(slot, 'tokens', !!cmd.greedy)); agents[name].out = probes; }
    return name;
  };
  let k = 0;
  const nextJob = () => {
    if (k >= cmd.jobs.length) return null;
    const job = cmd.jobs[k++];
    const [ia, ib] = job.iSeat === 1 ? [job.i, job.j] : [job.j, job.i];
    const [a, b] = [cmd.decks[ia], cmd.decks[ib]];
    return { deckA: a.cards, deckB: b.cards, deckName: a.name, deckBName: b.name, seed: job.seed, seats: { 1: pilot(ia), 2: pilot(ib) } };
  };
  const runner = new Runner(tokens, { concurrency: cmd.concurrency || 64, deckoutWin: cmd.deckoutWin ?? 1,
                                      maxTurns: cmd.maxTurns || 0, roundTurns: cmd.roundTurns || 0 });
  const out = await runner.run(nextJob, agents, { record: new Set() });
  for (const { rec, g, me } of trackList) rec.liveReward = g.reward(me, cmd.deckoutWin ?? 1);   // the live game's terminal reward
  const bySeed = new Map(cmd.jobs.map(j => [j.seed, j]));
  const results = out.results.map(r => {
    const job = bySeed.get(r.seed);
    return { i: job.i, j: job.j, iSeat: job.iSeat, seed: job.seed, winner: r.winner, ending: r.ending, turns: r.turns,
             prizesLeft: r.prizesLeft, steps: r.steps, error: r.error, ...(r.roundT !== undefined ? { roundT: r.roundT } : {}) };
  });
  const cpu = process.cpuUsage(cpu0);
  return { ok: true, games: results.length, seconds: (Date.now() - t0) / 1000, results, targetProbes: probes,
           targetStats: { ...stats, cpuMs: Math.round((cpu.user + cpu.system) / 1000), wallMs: Date.now() - t0 } };
}

let queue = Promise.resolve();
F.readFrames(process.stdin, (type, payload) => {
  if (type === F.RESPONSE) {
    const { header, arrays } = F.unpackArrays(payload);
    const resolve = pending.get(header.id);
    pending.delete(header.id);
    const off = resolve.off;
    resolve(Array.from({ length: header.n }, (_, i) => ({ action: arrays.action[i], logp: arrays.logp[i], value: arrays.value[i],
      ...(arrays.probs ? { probs: Array.from(arrays.probs.subarray(off[i], off[i + 1])) } : {}) })));
    return;
  }
  if (type !== F.JSON_FRAME) return;
  const msg = JSON.parse(payload.toString('utf8'));
  queue = queue.then(async () => {
    try {
      if (msg.cmd === 'quit') process.exit(0);
      if (msg.cmd === 'info') {
        F.writeJson(process.stdout, { ok: true, decks: decks.map(d => d.name), identity: { obsSize: identity.obsSize, actionSize: identity.actionSize },
          tokens: { maxTok: tokens.MAX_TOK, maxCand: tokens.MAX_CAND, globF: tokens.GLOB_F, slotF: tokens.SLOT_F, names: tokens.names.length } });
        return;
      }
      if (msg.cmd === 'games') {
        tokens.history = msg.history || 0; tokens.chain = msg.chain || 0; tokens.canon = msg.canon || 0;
        F.writeJson(process.stdout, await games(msg));
        return;
      }
      throw new Error('unknown command ' + msg.cmd);
    } catch (e) {
      F.writeJson(process.stdout, { ok: false, error: String(e && e.stack || e) });
    }
  });
});
