// A rollout worker whose policies run in the learner process (rl/remote.py), on the GPU: it
// plays the games and sends each batch of decisions to the learner as a framed request
// (env/framing.js), getting actions, log-probabilities and values back.
//
// Commands (JSON frames), answered with one JSON frame each:
//   { "cmd": "info" }
//   { "cmd": "collect", "encoding": "identity" | "tokens", "transitions": 20000, "out": "<file>",
//     "seed": 1, "concurrency": 64, "matchups": [[deckA, deckB], ...],
//     "opponents": [{ "spec": "self" | "slot:<k>", "weight": 1 }] }
//     each recorded decision says whether it was sampled ("sampled"; a greedy model seat's are not, log #81)
//   { "cmd": "games", "encoding": "tokens", "decks": [{ name, cards }], "greedy": true, "concurrency": 64,
//     "jobs": [{ "i": 0, "j": 1, "iSeat": 1, "seed": 7, "rec": true }], "slots": [0, 3, ...], "out": "<file>",
//     "deckoutWin": 1, "maxTurns": 0 }
//     each listed game once: deck i is piloted by model slot slots[i] (slot 0 in both seats without
//     "slots"); with "out", every decision of both seats of the jobs with "rec" is recorded there
//     (rl/metagame.py training games); with maxTurns = T > 0 a game unfinished at turn T is a draw (env/game.js,
//     log #140); roundTurns = T or
//     [a, b] plays every game under the 2000 round rule cut at T (drawn per deal from a..b; env/game.js, log #160), its
//     rewards the event's points, its results with roundT (also in collect)
//     with "judgeSearch": { k, dets, maxSteps, concurrency, seed, crn } (rl/metagame.py --judge-search, log #148) the jobs
//     with "search" are played in a second Runner beside the plain one, both seats by env/agents.js PolicySearchAgent
//     over the learner (RemotePilot below), never recorded; their results carry search: true and the reply searchStats
//   { "cmd": "qprobe", "decks", "jobs", "out", "probeP": 0.1, "maxProbes": 4, "maxOptions": 8, "rollouts": 8,
//     "seed", "concurrency", "deckoutWin", "redeal": false, "history": 0, "focus": null, "greedyLines": false }
//     the jobs' games recorded (both seats), plus Monte Carlo values of the options at sampled decisions (qprobe below)
//   { "cmd": "quit" }
//   "slotEnc": { "<slot>": { canon, chain, history } } (collect and games): each seat is encoded with the options of the
//   model slot it uses, instead of the command's one set; a slot without an entry is an error
//   collect, games and qprobe take "history": W and "chain": K, the token encoder's action-history window and chain
//   rows (env/tokens.js; 0 = none); "canon": 1 the one-token-per-card-per-zone encoding of a state_canon pilot (rl/token_model.py)
// The learner is model slot 0; "slot:k" is another model the learner holds (a league snapshot).
'use strict';
const fs = require('fs');
const { Encoder } = require('./encode.js');
const { TokenEncoder, PRIZE_GLOB } = require('./tokens.js');
const { Runner, packRollout } = require('./runner.js');
const { archivedDecks } = require('./decks.js');
const { SimpleBotAgent, PolicySearchAgent } = require('./agents.js');
const { Rng } = require('./rng.js');
const F = require('./framing.js');

const decks = archivedDecks();
const identity = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
const tokens = new TokenEncoder();
const deckByName = name => {
  if (typeof name === 'object') return name;   // a decklist { name, cards } (built decks, A5)
  const d = decks.find(x => x.name === name) || decks.find(x => x.name.toLowerCase().includes(name.toLowerCase()));
  if (!d) throw new Error('no archived deck matches ' + name);
  return d;
};

// A seat's encoder options when the command has slotEnc: those of the model slot it uses (env/env.js seatEnc).
const seatEnc = (cmd, slotOf) => {
  if (!cmd.slotEnc) return {};
  const e = s => { if (!cmd.slotEnc[slotOf[s]]) throw new Error('slotEnc has no entry for slot ' + slotOf[s]); return cmd.slotEnc[slotOf[s]]; };
  return { seatEnc: { 1: e(1), 2: e(2) } };
};

const pending = new Map();
let nextId = 1;
// Memory keys (log #76): each request row carries its game's uid * 2 + seat - 1, so a pilot with memory (rl/remote.py)
// can carry its state between a seat's decisions; finished games' uids go with the next request, to be dropped.
let nextGameUid = 1;
let drops = [];

// topk = k (log #148; null: not sent, as before): the request is a search's (rl/remote.py forwards such batches in chunks),
// and with k > 0 asks for each row's k most likely legal options too, returned as `top` (best first, by logit), for
// PolicySearchAgent's candidates.
class RemoteAgent {
  constructor(slot, encoding, greedy = false, topk = null) {
    this.slot = slot; this.encoding = encoding; this.greedy = greedy; this.topk = topk;
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
    let arrays;
    if (this.encoding === 'tokens') {
      const e = tokens;
      const tc = new Int16Array(n * e.MAX_TOK), tk = new Uint8Array(n * e.MAX_TOK), ta = new Uint8Array(n * e.MAX_TOK);
      const gl = new Uint8Array(n * e.GLOB_F), sl = new Uint8Array(n * 12 * e.SLOT_F), cd = new Int16Array(n * e.MAX_CAND * 6);
      const nc = new Int32Array(n);
      batch.forEach((b, i) => {
        const o = b.obs;
        tc.set(o.tokCard, i * e.MAX_TOK); tk.set(o.tokKind, i * e.MAX_TOK); ta.set(o.tokAux, i * e.MAX_TOK);
        gl.set(o.glob, i * e.GLOB_F); sl.set(o.slots, i * 12 * e.SLOT_F); cd.set(o.cand, i * e.MAX_CAND * 6); nc[i] = o.nCand;
      });
      arrays = [['tok_card', tc], ['tok_kind', tk], ['tok_aux', ta], ['glob', gl], ['slots', sl], ['cand', cd], ['n_cand', nc]];
    } else {
      const O = identity.obsSize;
      const x = new Uint8Array(n * O);
      batch.forEach((b, i) => x.set(b.obs, i * O));
      arrays = [['obs', x]];
    }
    arrays.push(['legal_offsets', offsets], ['legal_ids', ids], ['keys', keys], ['drop', Int32Array.from(drops)]);
    drops = [];
    F.writeFrame(process.stdout, F.REQUEST, F.packArrays({ id, slot: this.slot, n, encoding: this.encoding, greedy: this.greedy,
      ...(this.topk != null ? { topk: this.topk } : {}) }, arrays));
    return new Promise(resolve => pending.set(id, resolve));
  }
}

// A model slot as env/agents.js PolicySearchAgent's pilot (log #148): evaluate(batch, k) -> [{ order, best, value }], best
// the slot's top option (greedy), order best and then the rest of its k most likely options (k = 0: best alone, for the
// search lines, which need only the move and the value). Items need env (RemoteAgent keys rows by game).
class RemotePilot {
  constructor(slot, k) { this.slot = slot; this.k = k; this.agents = new Map(); }

  evaluate(batch, k = this.k) {
    if (!this.agents.has(k)) this.agents.set(k, new RemoteAgent(this.slot, 'tokens', true, k));
    return this.agents.get(k).act(batch).then(out => out.map(o => ({
      order: [o.action, ...(o.top || []).filter(a => a !== o.action)], best: o.action, value: o.value })));
  }
}

// Soft search targets (C49, log #169; rl/train.py and rl/metagame.py --search-distill): cmd.probe = { p, k, dets,
// maxSteps, seed }. onDecision takes, at a share p of the recorded decisions in the main phase with two or more options,
// a copy of the game; search() then searches every copy (PolicySearchAgent over the learner, its k most likely moves in
// dets re-dealt copies shared by all of them, CRN, lines greedy to the end of the turn), in batches of 32, and returns
// per copy the decision's transition index, the moves searched and each copy's score (undefined without cmd.probe).
function probeCatch(cmd, enc) {
  const probe = cmd.probe || null;
  if (!probe) return { onDecision: null, search: async () => undefined };
  const prng = new Rng((cmd.seed ^ 0x2545f491) >>> 0);
  const caught = [];
  const onDecision = (s, answer, k) => {
    if (k < 0 || s.t.legal.length < 2) return;
    const g = s.env.game;
    if (g.decision().prompt || prng.float() >= probe.p) return;
    caught.push({ k, game: g.clone(), decklists: s.env.decklists, show: s.env.showOpponentDecklist });
  };
  const search = async () => {
    if (!caught.length) return [];
    const { Env } = require('./env.js');
    const items = caught.map(c => {
      const env = new Env(enc, { showOpponentDecklist: c.show });
      env.game = c.game;
      env.decklists = c.decklists;
      const t = env.observe();
      return { obs: t.obs, legal: t.legal, env };
    });
    const S = new PolicySearchAgent(new RemotePilot(0, probe.k || 4), enc, { k: probe.k || 4, dets: probe.dets || 4,
      maxSteps: probe.maxSteps || 40, seed: (probe.seed || 0) ^ cmd.seed, crn: true, keepLines: true,
      followups: (probe.followups && probe.followups.n) || 1 });
    const res = [];
    for (let i = 0; i < items.length; i += 32) res.push(...await S.act(items.slice(i, i + 32)));
    return caught.map((c, i) => ({ k: c.k, cands: res[i].cands || null, scores: res[i].scores || null })).filter(p => p.cands);
  };
  return { onDecision, search };
}

// BENCH-P5 (runs/probe/BENCH/P5/record.md; cmd.ppBranch, off: nothing runs): at the learner's main-phase decisions with a
// "play PlusPower" option and an attack option legal, a copy of the game is caught (a seeded coin keeps cmd.ppFrac of them,
// default all). search() plays two candidates on 4 CRN re-dealt copies each to the end of the turn (PolicySearchAgent, the
// pilot greedy, scored by its value): PlusPower and the pilot's greedy action (the best other option if greedy is PlusPower).
// Returns { eligible, rows: [{ k (the rollout row), pp, other, q: [Q(pp), Q(other)], n }], seconds }; the action taken is untouched.
function ppCatch(cmd, enc) {
  const isPP = o => o.key.startsWith('trainer|PlusPower');
  const coin = new Rng((cmd.seed ^ 0x5bd1e995) >>> 0);
  const caught = [];
  let eligible = 0;
  const onDecision = (s, answer, k) => {
    if (k < 0 || s.env.game.decision().prompt) return;
    const opts = s.env.current.options;
    if (!s.t.legal.some(a => isPP(opts[a])) || !s.t.legal.some(a => opts[a].key.startsWith('attack|'))) return;
    eligible++;
    if ((cmd.ppFrac ?? 1) < 1 && coin.float() >= cmd.ppFrac) return;
    caught.push({ k, game: s.env.game.clone(), decklists: s.env.decklists, show: s.env.showOpponentDecklist });
  };
  const search = async () => {
    const t0 = Date.now();
    const { Env } = require('./env.js');
    const pilot = new RemotePilot(0, 4);
    const S = new PolicySearchAgent(pilot, enc, { k: 2, dets: 4, maxSteps: 40, seed: cmd.seed ^ 0x7f4a7c15, crn: true, keepLines: true });
    const rows = [];
    for (let i = 0; i < caught.length; i += 32) {
      const part = caught.slice(i, i + 32);
      const items = part.map(c => {
        const env = new Env(enc, { showOpponentDecklist: c.show });
        env.game = c.game;
        env.decklists = c.decklists;
        const t = env.observe();
        return { obs: t.obs, legal: t.legal, env };
      });
      const top = await pilot.evaluate(items, 4);
      const todo = [];
      items.forEach((b, j) => {
        const opts = b.env.current.options;
        const pp = b.legal.find(a => isPP(opts[a]));
        const other = !isPP(opts[top[j].best]) ? top[j].best : top[j].order.find(a => b.legal.includes(a) && !isPP(opts[a]));
        if (pp !== undefined && other !== undefined) todo.push({ b, e: { order: [pp, other], best: top[j].best }, k: part[j].k, pp, other });
      });
      const res = todo.length ? await S.searchAll(todo.map(x => ({ b: x.b, e: x.e }))) : [];
      todo.forEach((x, j) => {
        const qs = res[j].scores.map(sc => sc.filter(v => v !== null));
        if (qs.some(q => !q.length)) return;
        rows.push({ k: x.k, pp: x.pp, other: x.other, greedy: x.e.best, q: qs.map(q => q.reduce((a, b) => a + b, 0) / q.length), n: qs.map(q => q.length) });
      });
    }
    return { eligible, caught: caught.length, rows, seconds: (Date.now() - t0) / 1000 };
  };
  return { onDecision, search };
}

// BENCH-P8 (runs/probe/BENCH/P8/record.md; cmd.trBranch, off: nothing runs): P5's catch without the card list. At the learner's
// main-phase decisions with a "play a Trainer" option legal (a seeded coin keeps cmd.trFrac of them, default all), two candidates
// are played on 4 CRN re-dealt copies to the end of the turn: the pilot's greedy action and u. If greedy is not a Trainer play,
// u is uniform over the legal Trainer plays; if it is, u is uniform over all other legal options. No u, no branch.
// Returns { eligible, caught, rows: [{ k, greedy, u, card: { u, g } (Trainer names, null if not a Trainer play), q: [Q(greedy), Q(u)], n }], seconds }.
function trCatch(cmd, enc) {
  const isTr = o => o.key.startsWith('trainer|');
  const nameOf = o => isTr(o) ? o.key.split('|')[1].replace(/ [A-Z0-9]+$/, '') : null;
  const coin = new Rng((cmd.seed ^ 0x3c6ef372) >>> 0), pick = new Rng((cmd.seed ^ 0x1b873593) >>> 0);
  const caught = [];
  let eligible = 0;
  const onDecision = (s, answer, k) => {
    if (k < 0 || s.env.game.decision().prompt) return;
    const opts = s.env.current.options;
    if (!s.t.legal.some(a => isTr(opts[a]))) return;
    eligible++;
    if ((cmd.trFrac ?? 1) < 1 && coin.float() >= cmd.trFrac) return;
    caught.push({ k, legal: s.t.legal.slice(), game: s.env.game.clone(), decklists: s.env.decklists, show: s.env.showOpponentDecklist });
  };
  const search = async () => {
    const t0 = Date.now();
    const { Env } = require('./env.js');
    const pilot = new RemotePilot(0, 4);
    const S = new PolicySearchAgent(pilot, enc, { k: 2, dets: 4, maxSteps: 40, seed: cmd.seed ^ 0x7f4a7c15, crn: true, keepLines: true });
    const rows = [];
    for (let i = 0; i < caught.length; i += 32) {
      const part = caught.slice(i, i + 32);
      const items = part.map(c => {
        const env = new Env(enc, { showOpponentDecklist: c.show });
        env.game = c.game;
        env.decklists = c.decklists;
        const t = env.observe();
        return { obs: t.obs, legal: t.legal, env };
      });
      const top = await pilot.evaluate(items, 4);
      const todo = [];
      items.forEach((b, j) => {
        const opts = b.env.current.options, g = top[j].best, rec = part[j].legal;   // both candidates must be in the recorded row's options
        if (!rec.includes(g)) return;
        const pool = (isTr(opts[g]) ? b.legal.filter(a => a !== g) : b.legal.filter(a => isTr(opts[a]))).filter(a => rec.includes(a));
        if (!pool.length) return;
        const u = pool[pick.int(pool.length)];
        todo.push({ b, e: { order: [g, u], best: g }, k: part[j].k, greedy: g, u, card: { u: nameOf(opts[u]), g: nameOf(opts[g]) } });
      });
      const res = todo.length ? await S.searchAll(todo.map(x => ({ b: x.b, e: x.e }))) : [];
      todo.forEach((x, j) => {
        const qs = res[j].scores.map(sc => sc.filter(v => v !== null));
        if (qs.some(q => !q.length)) return;
        rows.push({ k: x.k, greedy: x.greedy, u: x.u, card: x.card, q: qs.map(q => q.reduce((a, b) => a + b, 0) / q.length), n: qs.map(q => q.length) });
      });
    }
    return { eligible, caught: caught.length, rows, seconds: (Date.now() - t0) / 1000 };
  };
  return { onDecision, search };
}

// C110 (runs/probe/C110-ko-math/record.md; cmd.koMath, off: nothing runs): at the learner's main-phase decisions with a "play
// PlusPower" option and an attack option legal, every legal attack is played on a copy of the game (its own RNG clone, so a coin
// flip lands as it would in the game; no PlusPower newly played) and the engine's PutDamageEffect on the Defending Pokemon is read:
// dmg (final, Weakness, Resistance and PlusPowers already attached in), left (its HP left before the hit), coins (coin flips
// answered), choice (a non-automatic prompt had to be answered, with its first option). Log only; the action taken is untouched.
// Returns [{ k (the rollout row), atk: [{ key, dmg, left, coins, choice }] }].
function koCatch(cmd) {
  const rows = [];
  const onDecision = (s, answer, k) => {
    if (k < 0 || s.env.game.decision().prompt) return;
    const opts = s.env.current.options;
    if (!s.t.legal.some(a => opts[a].key.startsWith('trainer|PlusPower')) || !s.t.legal.some(a => opts[a].key.startsWith('attack|'))) return;
    const atk = [];
    for (const a of s.t.legal) {
      if (!opts[a].key.startsWith('attack|')) continue;
      const g = s.env.game.clone(), r = { key: opts[a].key, dmg: 0, left: null, coins: 0, choice: false };
      const store = g.store, orig = store.reduceEffect, auto = g.autoAnswer;
      store.reduceEffect = function (state, effect) {
        const t = effect.type === 'PUT_DAMAGE_EFFECT' && effect.target === effect.opponent.active && effect.target.getPokemonCard() ? effect.target : null;
        const before = t ? t.getPokemonCard().hp - t.damage : null;
        const res = orig.call(this, state, effect);
        if (t) { r.dmg += Math.max(0, effect.damage); if (r.left === null) r.left = before; }
        return res;
      };
      g.autoAnswer = function (prompt) { if (prompt.type === 'Coin flip') r.coins++; return auto.call(this, prompt); };
      try {
        g.step(s.t.legal.indexOf(a));
        for (let n = 0; n < 8 && !g.done && g.decision().prompt; n++) { r.choice = true; g.step(0); }
      } catch (e) { r.error = String(e.message || e); }
      atk.push(r);
    }
    rows.push({ k, atk });
  };
  return { onDecision, rows };
}

async function collect(cmd) {
  const t0 = Date.now();
  const rng = new Rng(cmd.seed);
  const encoding = cmd.encoding || 'identity';
  const enc = encoding === 'tokens' ? tokens : identity;
  const agents = { learner: new RemoteAgent(0, encoding, false) };
  const opponents = [];
  for (const [i, o] of (cmd.opponents || [{ spec: 'self', weight: 1 }]).entries()) {
    const name = 'opp' + i;
    if (o.spec === 'self') { opponents.push({ name: 'learner', weight: o.weight }); continue; }
    if (o.spec.startsWith('slot:')) agents[name] = new RemoteAgent(Number(o.spec.slice(5)), encoding, false);
    else throw new Error('unknown opponent ' + o.spec);
    opponents.push({ name, weight: o.weight });
  }
  const totalWeight = opponents.reduce((a, o) => a + o.weight, 0);
  const matchups = cmd.matchups.map(([a, b]) => [deckByName(a), deckByName(b)]);
  let n = 0;
  const nextJob = recorded => {
    if (recorded >= cmd.transitions) return null;
    const [da, db] = matchups[rng.int(matchups.length)];
    let u = rng.float() * totalWeight, opp = opponents[0];
    for (const o of opponents) { u -= o.weight; if (u <= 0) { opp = o; break; } }
    const learnerSeat = rng.int(2) + 1;
    const seats = learnerSeat === 1 ? { 1: 'learner', 2: opp.name } : { 1: opp.name, 2: 'learner' };
    const [deckA, deckB] = learnerSeat === 1 ? [da, db] : [db, da];
    return { deckA: deckA.cards, deckB: deckB.cards, deckName: deckA.name, deckBName: deckB.name, seed: cmd.seed * 100003 + n++, seats,
             ...seatEnc(cmd, { 1: agents[seats[1]].slot, 2: agents[seats[2]].slot }) };
  };
  const runner = new Runner(enc, { concurrency: cmd.concurrency || 64, deckoutWin: cmd.deckoutWin ?? 1, roundTurns: cmd.roundTurns || 0 });
  // probe (C49, log #169): copies of a share of the learner's recorded decisions, searched after the games (probeCatch).
  const pc = probeCatch(cmd, enc);
  // trainerCounts (opt-in, log only): every decision taken while a prompt is open, by "<resolving Trainer>|<prompt>|<seat>"
  const tcounts = cmd.trainerCounts ? {} : null;
  const onDecision0 = !tcounts ? pc.onDecision : (s, answer, k) => {
    const g = s.env.game, d = g.decision();
    if (d && d.prompt) {
      const ck = g.chain && g.chain.key;
      const trainer = ck && ck.startsWith('trainer|') ? ck.split('|')[1].replace(/ [A-Z0-9]+$/, '') : 'none';
      const key = trainer + '|' + String(d.prompt.message || d.prompt.type) + '|' + s.t.playerId;
      const c = tcounts[key] || (tcounts[key] = { prompts: 0, picks: 0 });
      const o = d.options[answer.action];
      c.prompts++;
      if (o && o.key !== 'cancel' && o.key !== 'done') c.picks++;
    }
    if (pc.onDecision) pc.onDecision(s, answer, k);
  };
  const pp = cmd.ppBranch ? ppCatch(cmd, enc) : null;      // BENCH-P5
  const onDecision1 = !pp ? onDecision0 : (s, answer, k) => { if (onDecision0) onDecision0(s, answer, k); pp.onDecision(s, answer, k); };
  const tr = cmd.trBranch ? trCatch(cmd, enc) : null;      // BENCH-P8
  const onDecision2 = !tr ? onDecision1 : (s, answer, k) => { if (onDecision1) onDecision1(s, answer, k); tr.onDecision(s, answer, k); };
  const ko = cmd.koMath ? koCatch(cmd) : null;      // C110
  const onDecision = !ko ? onDecision2 : (s, answer, k) => { if (onDecision2) onDecision2(s, answer, k); ko.onDecision(s, answer, k); };
  const out = await runner.run(nextJob, agents, { record: new Set(['learner']), onDecision });
  const probes = await pc.search();
  const ppBranch = pp ? await pp.search() : null;
  const trBranch = tr ? await tr.search() : null;
  fs.writeFileSync(cmd.out, packRollout(out.rec, enc.obsSize || 0, { encoding, actionSize: enc.actionSize || enc.MAX_CAND }));
  const results = out.results.map(r => ({ id: r.id, winner: r.winner, ending: r.ending, seats: r.seats, decks: r.decks, steps: r.steps, error: r.error,
                                          ...(cmd.roundTurns ? { turns: r.turns, roundT: r.roundT } : {}) }));
  return { ok: true, out: cmd.out, transitions: out.rec.action.length, games: out.stats.games, seconds: (Date.now() - t0) / 1000, results,
           ...(probes ? { probes } : {}), ...(tcounts ? { trainerCounts: tcounts } : {}), ...(ppBranch ? { ppBranch } : {}), ...(trBranch ? { trBranch } : {}), ...(ko ? { koMath: ko.rows } : {}) };
}

// Plays the listed games and reports each one's result (rl/gpu_matrix.py, rl/metagame.py). Deck i is
// piloted by model slot cmd.slots[i], or by slot 0 in both seats. With cmd.out, both seats' decisions
// are recorded and written there.
async function games(cmd) {
  const t0 = Date.now();
  const encoding = cmd.encoding || 'tokens';
  const enc = encoding === 'tokens' ? tokens : identity;
  if (cmd.slotEnc && (cmd.judgeSearch || cmd.probe)) throw new Error('slotEnc is not supported with judgeSearch or probe');
  const agents = {};
  // A recorded seat plays as 'r<slot>', an unrecorded one as 'o<slot>': the same model slot, but only the
  // 'r' names are recorded.
  const pilot = (i, rec) => {
    const slot = cmd.slots ? cmd.slots[i] : 0;
    const name = (rec ? 'r' : 'o') + slot;
    if (!agents[name]) agents[name] = new RemoteAgent(slot, encoding, !!cmd.greedy);
    return name;
  };
  let k = 0;
  // judgeSearch (log #148): the jobs with "search" go to their own Runner below, the rest to the plain one as before.
  const js = cmd.judgeSearch || null;
  const plainJobs = js ? cmd.jobs.filter(j => !j.search) : cmd.jobs;
  // A job with bot: "simplebot" has deck j played by SimpleBot instead of a model (pilots with memory, which have no
  // ONNX export, against SimpleBot; log #76).
  const bots = { simplebot: () => new SimpleBotAgent() };
  const nextJob = () => {
    if (k >= plainJobs.length) return null;
    const job = plainJobs[k++];
    const [ia, ib] = job.iSeat === 1 ? [job.i, job.j] : [job.j, job.i];
    const [a, b] = [cmd.decks[ia], cmd.decks[ib]];
    const rec = !!cmd.out && job.rec !== false;
    const seat = i => {
      if (!job.bot || i !== job.j) return pilot(i, rec);
      if (!agents['bot:' + job.bot]) agents['bot:' + job.bot] = bots[job.bot]();
      return 'bot:' + job.bot;
    };
    return { deckA: a.cards, deckB: b.cards, deckName: a.name, deckBName: b.name, seed: job.seed,
             seats: { 1: seat(ia), 2: seat(ib) },
             ...seatEnc(cmd, { 1: cmd.slots ? cmd.slots[ia] : 0, 2: cmd.slots ? cmd.slots[ib] : 0 }) };
  };
  const recorded = new Set();
  for (const s of new Set(cmd.slots || [0])) recorded.add(pilot(cmd.slots ? cmd.slots.indexOf(s) : 0, true));
  const runner = new Runner(enc, { concurrency: cmd.concurrency || 64, deckoutWin: cmd.deckoutWin ?? 1,
                                   maxTurns: cmd.maxTurns || 0, roundTurns: cmd.roundTurns || 0 });
  // Searched games (log #148): both seats of deck i's model slot played by PolicySearchAgent (k candidates from the slot's
  // top k, dets re-dealt copies each, lines greedy to the end of the turn, scored by the slot's value), in a second Runner
  // run alongside the plain one (a Runner waits for every agent's answer each step, so a search's many line requests
  // would hold up the plain games), under the same turn limit, never recorded.
  const searchJobs = js ? cmd.jobs.filter(j => j.search) : [];
  let sOut = null, sSeconds = 0;
  const searchers = {};
  const searchRun = async () => {
    if (encoding !== 'tokens') throw new Error('judgeSearch needs the token encoding');
    const s0 = Date.now();
    let q = 0;
    const nextSearch = () => {
      if (q >= searchJobs.length) return null;
      const job = searchJobs[q++];
      const [ia, ib] = job.iSeat === 1 ? [job.i, job.j] : [job.j, job.i];
      const [a, b] = [cmd.decks[ia], cmd.decks[ib]];
      const seat = i => {
        const slot = cmd.slots ? cmd.slots[i] : 0;
        if (!searchers['s' + slot]) {
          searchers['s' + slot] = new PolicySearchAgent(new RemotePilot(slot, js.k || 4), tokens,
            { k: js.k || 4, dets: js.dets || 4, maxSteps: js.maxSteps || 40, seed: (js.seed || 0) + slot, crn: !!js.crn,
              trainerOnly: !!js.trainerOnly, includeTrainer: !!js.includeTrainer });   // C122's options, off by default
        }
        return 's' + slot;
      };
      return { deckA: a.cards, deckB: b.cards, deckName: a.name, deckBName: b.name, seed: job.seed, seats: { 1: seat(ia), 2: seat(ib) } };
    };
    const sRunner = new Runner(enc, { concurrency: js.concurrency || cmd.concurrency || 64,
                                      deckoutWin: cmd.deckoutWin ?? 1, maxTurns: cmd.maxTurns || 0, roundTurns: cmd.roundTurns || 0 });
    const o = await sRunner.run(nextSearch, searchers, { record: new Set() });
    sSeconds = (Date.now() - s0) / 1000;
    return o;
  };
  let out;
  const pc = probeCatch(cmd, enc);                     // soft search targets on the recorded decisions (log #169)
  const onDec = pc.onDecision;
  if (searchJobs.length) [out, sOut] = await Promise.all([runner.run(nextJob, agents, { record: cmd.out ? recorded : new Set(), onDecision: onDec }), searchRun()]);
  else out = await runner.run(nextJob, agents, { record: cmd.out ? recorded : new Set(), onDecision: onDec });
  const probes = cmd.out ? await pc.search() : undefined;
  if (cmd.out) fs.writeFileSync(cmd.out, packRollout(out.rec, 0, { encoding, actionSize: enc.MAX_CAND }));
  const bySeed = new Map(cmd.jobs.map(j => [j.seed, j]));
  const row = (r, extra) => {
    const job = bySeed.get(r.seed);
    return { i: job.i, j: job.j, iSeat: job.iSeat, seed: job.seed, winner: r.winner, ending: r.ending, turns: r.turns,
             prizesLeft: r.prizesLeft, steps: r.steps, error: r.error, ...(r.roundT !== undefined ? { roundT: r.roundT } : {}), ...extra };
  };
  const results = out.results.map(r => row(r, {}));
  if (sOut) results.push(...sOut.results.map(r => row(r, { search: true })));
  const searchStats = js ? Object.values(searchers).reduce((a, s) => {
    for (const q of Object.keys(a)) if (q !== 'seconds') a[q] += s.stats[q];
    return a;
  }, { searches: 0, changed: 0, lines: 0, lineErrors: 0, capped: 0, seconds: sSeconds }) : null;
  return { ok: true, games: results.length, seconds: (Date.now() - t0) / 1000, results,
           ...(cmd.out ? { out: cmd.out, transitions: out.rec.action.length } : {}), ...(js ? { searchStats } : {}),
           ...(probes ? { probes } : {}) };
}

// Ground-truth action values for the credit diagnostic (notes/scripts/credit_diag.py, log #75); evaluation only.
// Phase 1 plays cmd.jobs (as `games`) with model slot 0 sampling in both seats and records every asked decision of
// both seats to cmd.out. At a main-phase decision (no prompt open) with two or more options it takes a probe with
// probability probeP, at most maxProbes a game: a copy of the game as it stands. Phase 2 plays each probed option
// `rollouts` times to the end of the game, each from a fresh copy (the hidden cards where they are, fresh
// randomness from then on), slot 0 sampling in both seats: Q^pi of the option. An option list longer than
// maxOptions is cut to the option played plus a random sample of the others. A line's result, from the deciding
// player's side, is the reward training pays (win 1, by deck-out deckoutWin, loss -1, draw or cut 0).
const LAMS = [0, 0.5, 0.8, 0.9, 0.95, 0.98, 0.99, 1];

async function qprobe(cmd) {
  const t0 = Date.now();
  const rng = new Rng(cmd.seed);
  const deckoutWin = cmd.deckoutWin ?? 1;
  const R = cmd.rollouts || 8, maxOptions = cmd.maxOptions || 8, maxProbes = cmd.maxProbes || 4, probeP = cmd.probeP ?? 0.1;
  // greedyLines: the probe's lines are played greedily (the recorded games still sample): Q under the pilot's best play
  const agents = { r0: new RemoteAgent(0, 'tokens', false), o0: new RemoteAgent(0, 'tokens', !!cmd.greedyLines) };
  let k = 0;
  const nextGame = () => {
    if (k >= cmd.jobs.length) return null;
    const job = cmd.jobs[k++];
    const [ia, ib] = job.iSeat === 1 ? [job.i, job.j] : [job.j, job.i];
    const [a, b] = [cmd.decks[ia], cmd.decks[ib]];
    return { deckA: a.cards, deckB: b.cards, deckName: a.name, deckBName: b.name, seed: job.seed, seats: { 1: 'r0', 2: 'r0' } };
  };
  const probes = [], perGame = new Map();
  const onDecision = (s, ans, idx) => {
    if (idx < 0 || s.t.legal.length < 2) return;
    const d = s.env.game.decision();
    if (d.prompt || (perGame.get(s.id) || 0) >= maxProbes) return;
    // focus (a verb, e.g. 'trainer'; log #79): probe only decisions that offer an option with that verb
    if (cmd.focus && !d.options.some(o => o.key.split('|')[0] === cmd.focus)) return;
    if (rng.float() >= probeP) return;
    let copy;
    try { copy = s.env.game.clone(new Rng(1)); } catch (e) { return; }
    perGame.set(s.id, (perGame.get(s.id) || 0) + 1);
    probes.push({ k: idx, game: copy, decklists: s.env.decklists, player: s.t.playerId, turn: s.env.game.state.turn, v: ans.value,
                  steps: s.env.game.steps, keys: d.options.map(o => o.key), chosen: ans.action, gameSeed: s.job.seed });
  };
  const runner = new Runner(tokens, { concurrency: cmd.concurrency || 64, deckoutWin, maxTurns: cmd.maxTurns || 0 });
  const base = await runner.run(nextGame, agents, { record: new Set(['r0']), onDecision });
  fs.writeFileSync(cmd.out, packRollout(base.rec, 0, { encoding: 'tokens', actionSize: tokens.MAX_CAND }));

  const lines = [];
  probes.forEach((p, pi) => {
    let opts = p.keys.map((_, i) => i);
    if (opts.length > maxOptions && cmd.focus) {
      // focus: the option played, then every attack and pass (the ways to end the turn instead), then the focus
      // verb's options, then the rest; random order within each group
      const verb = i => p.keys[i].split('|')[0];
      const rank = i => i === p.chosen ? 0 : verb(i) === 'attack' || verb(i) === 'pass' ? 1 : verb(i) === cmd.focus ? 2 : 3;
      const order = rng.permutation(opts.length);
      opts = order.map(j => opts[j]).sort((x, y) => rank(x) - rank(y)).slice(0, maxOptions).sort((x, y) => x - y);
    } else if (opts.length > maxOptions) {
      const others = opts.filter(i => i !== p.chosen);
      const order = rng.permutation(others.length);
      opts = [p.chosen, ...order.slice(0, maxOptions - 1).map(i => others[i])].sort((x, y) => x - y);
    }
    p.probed = opts;
    p.q = opts.map(() => []);
    p.after = opts.map(() => []);
    p.sig = opts.map(() => LAMS.map(() => []));
    opts.forEach((o, oi) => {
      for (let r = 0; r < R; r++) lines.push({ pi, oi, seed: rng.u32(), vals: [] });
    });
  });
  let n = 0;
  const nextLine = () => {
    if (n >= lines.length) return null;
    const l = lines[n++];
    const p = probes[l.pi];
    // redeal: what the deciding player can't see is re-dealt in each copy (Game.clone with a viewer), so Q is the
    // option's value over the player's information set rather than the true deal.
    return { fromGame: () => p.game.clone(new Rng(l.seed), cmd.redeal ? p.player : undefined), decklists: p.decklists,
             first: p.keys[p.probed[l.oi]],
             seats: { 1: 'o0', 2: 'o0' }, seed: n, tag: [l.pi, l.oi, n - 1] };
  };
  // The probing player's values along each line: the advantage training would give the probed decision on that
  // line, GAE(lambda) from the probe's own value p.v (gamma 1, reward only at the end), for each of LAMS.
  const onLine = (s, ans) => { const l = lines[s.job.tag[2]]; if (s.t.playerId === probes[l.pi].player) l.vals.push(ans.value); };
  const roll = await runner.run(nextLine, agents, { onDecision: onLine });
  let errors = 0;
  for (const r of roll.results) {
    const [pi, oi] = r.tag;
    const p = probes[pi];
    if (r.error) errors++;
    const win = r.ending === 'deck-out' ? deckoutWin : 1;
    const z = r.winner === p.player ? win : (r.winner === 1 || r.winner === 2) ? -1 : 0;
    p.q[oi].push(z);
    p.after[oi].push(r.steps - p.steps);
    const seq = [p.v, ...lines[r.tag[2]].vals];
    LAMS.forEach((lam, li) => {
      let a = 0;
      for (let i = seq.length - 1; i >= 0; i--) a = ((i === seq.length - 1 ? z : seq[i + 1]) - seq[i]) + lam * a;
      p.sig[oi][li].push(Math.round(a * 1e4) / 1e4);
    });
  }
  const results = base.results.map(r => ({ seed: r.seed, winner: r.winner, ending: r.ending, turns: r.turns, steps: r.steps, error: r.error }));
  return { ok: true, out: cmd.out, transitions: base.rec.action.length, games: results.length, lines: lines.length, lineErrors: errors,
           seconds: (Date.now() - t0) / 1000, results,
           probes: probes.map(p => ({ k: p.k, player: p.player, turn: p.turn, steps: p.steps, nOptions: p.keys.length, chosen: p.chosen,
                                      probed: p.probed, keys: p.probed.map(i => p.keys[i]), q: p.q, after: p.after, gameSeed: p.gameSeed,
                                      v: p.v, sig: p.sig, lams: LAMS, ...(cmd.focus ? { allKeys: p.keys } : {}) })) };
}

let queue = Promise.resolve();
F.readFrames(process.stdin, (type, payload) => {
  if (type === F.RESPONSE) {
    const { header, arrays } = F.unpackArrays(payload);
    const resolve = pending.get(header.id);
    pending.delete(header.id);
    const K = header.k || 0;                     // a top-k reply (log #148): K options a row, -1 past its legal ones
    resolve(Array.from({ length: header.n }, (_, i) => ({ action: arrays.action[i], logp: arrays.logp[i], value: arrays.value[i],
                                                          sampled: arrays.sampled ? arrays.sampled[i] : 1,
                                                          ...(K && arrays.top ? { top: Array.from(arrays.top.subarray(i * K, (i + 1) * K)).filter(a => a >= 0) } : {}) })));
    return;
  }
  if (type !== F.JSON_FRAME) return;
  const msg = JSON.parse(payload.toString('utf8'));
  queue = queue.then(async () => {
    try {
      if (msg.cmd === 'quit') process.exit(0);
      if (msg.cmd === 'info') {
        F.writeJson(process.stdout, { ok: true, decks: decks.map(d => d.name), identity: { obsSize: identity.obsSize, actionSize: identity.actionSize },
          tokens: { maxTok: tokens.MAX_TOK, maxCand: tokens.MAX_CAND, globF: tokens.GLOB_F, slotF: tokens.SLOT_F, names: tokens.names.length,
                    prizeGlob: PRIZE_GLOB } });
        return;
      }
      if (msg.cmd === 'collect' || msg.cmd === 'games' || msg.cmd === 'qprobe') { tokens.history = msg.history || 0; tokens.chain = msg.chain || 0; tokens.canon = msg.canon || 0; }
      if (msg.cmd === 'collect') { F.writeJson(process.stdout, await collect(msg)); return; }
      if (msg.cmd === 'games') { F.writeJson(process.stdout, await games(msg)); return; }
      if (msg.cmd === 'qprobe') { F.writeJson(process.stdout, await qprobe(msg)); return; }
      throw new Error('unknown command ' + msg.cmd);
    } catch (e) {
      F.writeJson(process.stdout, { ok: false, error: String(e && e.stack || e) });
    }
  });
});
