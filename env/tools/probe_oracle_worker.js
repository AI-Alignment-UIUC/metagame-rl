// X1b COPY of env/tools/probe_worker.js (runs/probe/X1b-prompt-oracle/record.md; notes/scripts/probe_prompt_oracle.py;
// evaluation only): that file plus a third value of --prompts, "search" (the prompt oracle, PromptOracle below). With
// no switch it plays exactly as probe_worker.js, so as env/remote_worker.js. A copy, so the hashed files stay untouched
// while ar/ trains (log #236).
//   --prompts search   X1b: at a prompt X1 catches (below), the seat's pick is the option, among the pilot's 8 most
//                      likely at this pick step, with the best mean score over 4 re-dealt copies of the game (the same
//                      copies for every option), each played on by the pilot greedily in both seats to the end of the
//                      turn and scored by the pilot's value for the seat, or the result if the game ended. Options:
//                      --cap N (8), --dets K (4), --max-steps S (60, a line's steps at most, then scored by the value),
//                      --oracle-check 1 (each searched prompt also checks that a copy with nothing re-dealt equals the
//                      live game: replayExact / replayDiff, for the smoke).
//   --prompts random   X1: while a seat's own Trainer is resolving (game.chain.key starts 'trainer|' and the open prompt
//                      is the player's whose turn it is), its prompt answers are drawn uniformly from the offered options
//                      other than 'cancel'; whether and when to play the Trainer stays the pilot's.
//   --pace attack      X4 (must attack if able): when the pilot picks 'pass' at a main-phase decision that offers an
//                      attack, the seat takes instead the attack the pilot rates highest among the attack options.
//   --timing-card NAME  C99 (runs/probe/C99-cs-timing/record.md): the follow-through log. Each play of the card NAME by either
//                      seat is logged in switchStats.ft: the fetched card (name, type), the two discards, whether the fetched
//                      card is played, attached or evolved into before the turn ends, the pilot's value V at the decision that
//                      played it and at the seat's next decision after the turn (the result if the game ended first).
//   --timing-oracle 1   C99's timing oracle T (with --timing-card): at the seat's own main-phase decisions where playing the
//                      card is legal, PromptOracle's routine searches two candidates, the pilot's pick and playing the card (the
//                      pilot's next most likely action if its pick already plays it), in the same dets re-dealt copies
//                      (Game.clone), to the end of the turn; the better mean is played, a tie keeps the pilot's. Counts: tSearched,
//                      tUnsearchable, tPlays (played the card when the pilot would not have), tHolds (held it when the pilot
//                      would have played it), tGainSum.
// Every "games" reply carries switchStats (counted with the switches off too): decisions asked, prompts inside the
// seat's own Trainers by Trainer name, how many were randomized and how many of those differ from the pilot's answer,
// main-phase decisions offering an attack and how many the pilot attacked at, passes, passes with an attack on offer,
// and passes turned into attacks; with --prompts search also the oracle's counts (newSwitchStats).
//
// A rollout worker whose policies run in the learner process (rl/remote.py), on the GPU: it
// plays the games and sends each batch of decisions to the learner as a framed request
// (env/framing.js), getting actions, log-probabilities and values back.
//
// Commands (JSON frames), answered with one JSON frame each (this copy keeps only info and games, the ones its driver
// sends):
//   { "cmd": "info" }
//   { "cmd": "games", "encoding": "tokens", "decks": [{ name, cards }], "greedy": true, "concurrency": 64,
//     "jobs": [{ "i": 0, "j": 1, "iSeat": 1, "seed": 7, "rec": true }], "slots": [0, 3, ...], "out": "<file>",
//     "deckoutWin": 1, "maxTurns": 0 }
//     each listed game once: deck i is piloted by model slot slots[i] (slot 0 in both seats without
//     "slots"); with "out", every decision of both seats of the jobs with "rec" is recorded there
//     (rl/metagame.py training games); with maxTurns = T > 0 a game unfinished at turn T is a draw (env/game.js,
//     log #140); roundTurns = T or
//     [a, b] plays every game under the 2000 round rule cut at T (drawn per deal from a..b; env/game.js, log #160), its
//     rewards the event's points, its results with roundT
//     with "judgeSearch": { k, dets, maxSteps, concurrency, seed, crn } (rl/metagame.py --judge-search, log #148) the jobs
//     with "search" are played in a second Runner beside the plain one, both seats by env/agents.js PolicySearchAgent
//     over the learner (RemotePilot below), never recorded; their results carry search: true and the reply searchStats
//   { "cmd": "quit" }
// The learner is model slot 0; "slot:k" is another model the learner holds (a league snapshot).
'use strict';
const fs = require('fs');
const { Encoder } = require('../encode.js');
const { TokenEncoder, PRIZE_GLOB } = require('../tokens.js');
const { Runner, packRollout } = require('../runner.js');
const { archivedDecks } = require('../decks.js');
const { SimpleBotAgent, PolicySearchAgent } = require('../agents.js');
const { Rng } = require('../rng.js');
const { fingerprint } = require('../fingerprint.js');
const F = require('../framing.js');

const decks = archivedDecks();
const identity = new Encoder([...new Set(decks.flatMap(d => d.cards))]);
const tokens = new TokenEncoder();

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

// ---- The probe switches (this copy only; header above) ----
const SWARG = process.argv.slice(2);
// C109: "--side-b" splits the command line: the switches before it are model slot 0's (the lists' side), those after it slot 1's
// (the copies' side); without it every slot has the same switches. The follow-through log (--timing-card) is global: both seats.
const SIDE = SWARG.indexOf('--side-b');
const mkCfg = argv => {
  const swFlag = name => { const i = argv.indexOf('--' + name); return i === -1 ? null : argv[i + 1]; };
  const swNum = (name, d) => { const v = swFlag(name); return v === null ? d : Number(v); };
  const SW = { prompts: swFlag('prompts'), pace: swFlag('pace') };
  if (![null, 'random', 'search'].includes(SW.prompts) || ![null, 'attack'].includes(SW.pace)) throw new Error('bad switches ' + argv.join(' '));
  const ORACLE = { cap: swNum('cap', 8), dets: swNum('dets', 4), maxSteps: swNum('max-steps', 60), check: swNum('oracle-check', 0) };
  // C102 --oracle-prompts fetch|discard (default all): the oracle answers only prompts with this message (inside the seat's own
  // Trainer, as always); the others stay the pilot's. oracleBy counts the prompts it answered, by message.
  const OPROMPTS = swFlag('oracle-prompts') || 'all';
  if (!['all', 'fetch', 'discard'].includes(OPROMPTS)) throw new Error('bad switches ' + argv.join(' '));
  // C107 --oracle-trainer NAME (default off): the oracle answers only prompts opened while this Trainer (of the deciding seat) is
  // resolving, matched on game.chain's key as the timing card is ("Gust of Wind" matches "Gust of Wind BS"); with --oracle-prompts both apply.
  const OTRAINER = swFlag('oracle-trainer');
  const isOTrainer = name => OTRAINER === null || name === OTRAINER || name.startsWith(OTRAINER + ' ');
  SW.oracle = SW.prompts === 'search' ? ORACLE : null;
  const TIM = { card: swFlag('timing-card'), oracle: swNum('timing-oracle', 0) };   // C99 (header); off: nothing below runs
  return { SW, ORACLE, OPROMPTS, isOTrainer, TIM };
};
const CFGS = SIDE === -1 ? [mkCfg(SWARG)] : [mkCfg(SWARG.slice(0, SIDE)), mkCfg(SWARG.slice(SIDE + 1))];
const cfgOf = slot => CFGS[slot] || CFGS[0];
const { SW } = CFGS[0];
const TIM = { card: CFGS.map(c => c.TIM.card).find(c => c) || null, oracle: Math.max(...CFGS.map(c => c.TIM.oracle)) };
if (CFGS.some(c => c.TIM.card && c.TIM.card !== TIM.card)) throw new Error('the sides need one --timing-card');
const OMSG = { fetch: 'CHOOSE_CARD_TO_HAND', discard: 'CHOOSE_CARD_TO_DISCARD' };
// The oracle's counts (X1b): prompts searched, left to the pilot because no copy could be built (unsearchable), lines,
// line decisions sent to the pilot, lines ended by an engine error, lines cut at maxSteps (scored by the value there),
// the summed score gain of the pick over the pilot's pick (gainSum), prompts whose candidates all scored the same (flat),
// changed picks that lead the pilot's by over 2 SE of the copies' paired differences (clear), copies by re-deal tier
// (tier_*), the replay check's results (replayExact / replayDiff, --oracle-check), the seats' requests (acts) and the
// oracle's (oracleRounds), and the worker's milliseconds inside the oracle (wall clock).
const newSwitchStats = () => ({ asked: 0, trainerPrompts: 0, randomized: 0, changed: 0, byTrainer: {}, attackOffered: 0,
                                attacked: 0, passes: 0, passWithAttack: 0, passToAttack: 0,
                                searched: 0, oracleBy: {}, unsearchable: 0, lines: 0, lineAsked: 0, lineErrors: 0, capped: 0, gainSum: 0,
                                flat: 0, clear: 0, tier_full: 0, tier_oppHandSeen: 0, tier_ownDeckSeen: 0, tier_bothSeen: 0,
                                tier_none: 0, replayExact: 0, replayDiff: 0, acts: 0, oracleRounds: 0, oracleMs: 0, searchCalls: 0,
                                ...(TIM.oracle ? { tSearched: 0, tUnsearchable: 0, tPlays: 0, tHolds: 0, tGainSum: 0 } : {}) });
let swStats = newSwitchStats();

// ---- X1b: the prompt oracle (--prompts search) ----
// A prompt is open inside a Trainer, so the game cannot be copied with Game.clone (it needs a stable state: the engine
// keeps the open prompt's continuation in the store). A copy is instead rebuilt from game.chain, the record the game
// keeps for its own replay checks (env/game.js replayState): the state before the Trainer was played (chain.base) and
// every action and prompt answer since, coin flips and shuffles included. What the seat cannot see is re-dealt on that
// base first, as Game.clone(rng, seat) does (the seat's deck and Prizes together; the opponent's hand, deck and Prizes
// together; every zone keeps its size), then the record is replayed and the picks made so far at this prompt are made
// again, by option key. A Trainer can show the seat a hidden zone (Computer Search its deck, Rocket's Sneak Attack the
// opponent's hand): then that re-deal changes what the prompt offers, or what an earlier answer took. So each copy takes
// the widest tier below that shows the seat exactly what the live game shows it (validCopy: the same prompt, the same
// options by key, the same visible state); the last, nothing re-dealt, is counted (tier_none) as a leak.
const { Game } = require('../game.js');
const { C, newStore } = require('../engine.js');
const { Env } = require('../env.js');
const TIERS = [
  { name: 'full', own: true, oppHand: true },
  { name: 'oppHandSeen', own: true, oppHand: false },
  { name: 'ownDeckSeen', own: false, oppHand: true },
  { name: 'bothSeen', own: false, oppHand: false },
  { name: 'none' },
];

// What the seat sees: its hand, both discards, both boards, the stadium, every zone's size, whose turn and the phase.
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

// The live game at its open prompt, rebuilt with tier's re-deal; null if the replay fails or the copy does not show the
// seat what the live game shows it. Each side is re-dealt from its own stream of seed, and the copy's flips and shuffles
// come from new Rng(seed), so the tiers nest: a narrower tier deals the side it still re-deals exactly as the wider one
// did, and a tier that keeps a zone is reached only when re-dealing that side conflicts with what the seat sees. (With
// one stream, the seat's own re-deal changed with the opponent's pool size, so a Computer Search copy could pass at
// oppHandSeen on a fresh own deal and keep the opponent's unseen hand: a leak, 1 of 852 copies in the review's smoke.)
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

// The oracle for one model slot. searchAll([{ b, pick }]) -> per item { action, gain } or null (no copy could be built:
// the pilot's pick stands). b is the Runner's decision item, pick the pilot's greedy answer. Candidates: the pilot's
// pick, then its next most likely options, cap in all (the pilot's top-cap request). Every candidate is played in the
// same dets copies (CRN: the copies' seeds come from the live game's RNG state and step, so the same state searches the
// same way on every worker), lines in lockstep as env/agents.js PolicySearchAgent.searchAll plays them (forced moves
// without asking; a line ends at its first asked decision once the game turn has changed, scored by the pilot's value
// there, negated if the opponent decides, or by the seat's reward if the game ended), except that a line still in the
// turn after maxSteps is scored by the value where it stopped (PolicySearchAgent scores it 0). The best mean wins; a tie
// keeps the earlier candidate, so the pilot's pick first.
class PromptOracle {
  constructor(slot) { this.O = cfgOf(slot).ORACLE; this.pilot = new RemotePilot(slot, this.O.cap); }

  async searchAll(items, st) {
    const t0 = Date.now(), ORACLE = this.O;
    const top = await this.pilot.evaluate(items.map(x => x.b), ORACLE.cap);
    st.oracleRounds++; st.searchCalls++;     // searchCalls: oracleRounds / searchCalls is the round trips a search adds (sizing)
    const lines = [];
    const probs = items.map((x, pi) => {
      const b = x.b, live = b.env.game, me = b.env.current.playerId, opts = b.env.current.options;
      let order = [x.pick, ...top[pi].order.filter(a => a !== x.pick)].slice(0, ORACLE.cap);
      if (x.cs !== undefined) {      // C99: the timing card's decision, two candidates
        const other = x.pick === x.cs ? top[pi].order.find(a => a !== x.pick) : x.cs;
        if (other === undefined) return null;
        order = [x.pick, other];
      }
      const cands = order.map(a => opts[b.legal.indexOf(a)].key);
      const srng = new Rng((live.rng.clone().u32() ^ Math.imul(live.steps + 1, 0x9e3779b1) ^ 0x0b1e5eed) >>> 0);
      const seeds = Array.from({ length: ORACLE.dets }, () => srng.u32());
      if (x.cs !== undefined) {      // a main-phase decision: Game.clone's re-deal, nothing replayed
        const mine = lines.length;
        for (let ci = 0; ci < cands.length; ci++) for (let r = 0; r < seeds.length; r++) {
          const env = new Env(tokens, { showOpponentDecklist: b.env.showOpponentDecklist, u8: b.env.u8 });
          env.game = live.clone(new Rng(seeds[r]), me);
          env.decklists = b.env.decklists;
          env.observe();
          const j = env.current.options.findIndex(o => o.key === cands[ci]);
          if (j === -1) { lines.length = mine; return null; }      // a copy lacks the move: the pilot's pick stands
          lines.push({ pi, ci, r, env, t: env.step(env.current.legal[j]), score: null, n: 0 });
        }
        return { me, order, startTurn: live.state.turn };
      }
      if (ORACLE.check) {
        const g = copyAtPrompt(live, me, seeds[0], TIERS[TIERS.length - 1], opts);
        const ids = new Map();
        if (g && fingerprint(g.state, ids) === fingerprint(live.state, ids)) st.replayExact++; else st.replayDiff++;
      }
      const tiers = seeds.map(s => TIERS.find(t => copyAtPrompt(live, me, s, t, opts)) || null);
      if (tiers.some(t => !t)) return null;
      const tt = st.byTrainer[live.chain.key.split('|')[1]];    // copies by tier, also by Trainer (which Trainers keep a zone)
      for (const t of tiers) { st['tier_' + t.name]++; if (tt) tt['tier_' + t.name] = (tt['tier_' + t.name] || 0) + 1; }
      cands.forEach((key, ci) => seeds.forEach((s, r) => {
        const env = new Env(tokens, { showOpponentDecklist: b.env.showOpponentDecklist, u8: b.env.u8 });
        env.game = copyAtPrompt(live, me, s, tiers[r], opts);   // the same seed and tier rebuild the same copy
        if (!env.game) throw new Error('oracle: a validated copy did not rebuild');
        env.decklists = b.env.decklists;
        env.observe();
        const j = env.current.options.findIndex(o => o.key === key);
        lines.push({ pi, ci, r, env, t: env.step(env.current.legal[j]), score: null, n: 0 });
      }));
      return { me, order, startTurn: live.state.turn };
    });
    st.lines += lines.length;
    const turned = l => l.env.game.state.turn - probs[l.pi].startTurn >= 1;
    for (;;) {
      const ask = [];
      for (const l of lines) {
        if (l.score !== null) continue;
        while (l.n < ORACLE.maxSteps && !l.t.done && l.t.legal.length === 1 && !turned(l)) { l.t = l.env.step(l.t.legal[0]); l.n++; }
        if (l.t.done) {
          if (l.t.error) st.lineErrors++;
          l.score = l.env.game.reward(probs[l.pi].me);   // +1 / -1 / 0, or the round rule's points (env/game.js)
          continue;
        }
        ask.push(l);
      }
      if (!ask.length) break;
      st.lineAsked += ask.length; st.oracleRounds++;
      const ev = await this.pilot.evaluate(ask.map(l => ({ obs: l.t.obs, legal: l.t.legal, env: l.env })), 0);
      ask.forEach((l, i) => {
        const stop = turned(l) || l.n >= ORACLE.maxSteps;
        if (!stop) { l.t = l.env.step(ev[i].best); l.n++; return; }
        if (!turned(l)) st.capped++;
        l.score = l.t.playerId === probs[l.pi].me ? ev[i].value : -ev[i].value;
      });
    }
    const res = probs.map((p, pi) => {
      if (!p) return null;
      const sc = p.order.map(() => new Array(ORACLE.dets).fill(0));     // sc[candidate][copy]
      for (const l of lines) if (l.pi === pi) sc[l.ci][l.r] = l.score;
      const m = sc.map(row => row.reduce((a, b) => a + b, 0) / row.length);
      let best = 0;
      for (let c = 1; c < m.length; c++) if (m[c] > m[best]) best = c;
      if (items[pi].cs !== undefined) { st.tGainSum += m[best] - m[0]; return { action: p.order[best], gain: m[best] - m[0] }; }
      st.gainSum += m[best] - m[0];
      if (Math.max(...m) - Math.min(...m) < 1e-6) st.flat++;            // every candidate scored the same
      if (best !== 0) {    // the pick's lead over the pilot's, paired by copy: clear if over 2 SE of the copies' differences
        const d = sc[best].map((v, r) => v - sc[0][r]), dm = m[best] - m[0];
        const se = Math.sqrt(d.reduce((a, v) => a + (v - dm) ** 2, 0) / Math.max(d.length - 1, 1) / d.length);
        if (dm > 2 * se) st.clear++;
      }
      return { action: p.order[best], gain: m[best] - m[0] };
    });
    st.oracleMs += Date.now() - t0;
    return res;
  }
}

// ---- C99: the follow-through log (--timing-card) ----
// C106 (runs/probe/C106-pluspower-timing/record.md), with --timing-card PlusPower: the knockout-conversion log, swStats.pp. The
// engine's own damage: store.reduceEffect of a live game is wrapped, and each PutDamageEffect on the Defending Pokemon is logged after
// the engine resolved it (Weakness, Resistance and PlusPower's +10 already in): base (after Weakness and Resistance, before cards
// change it), dmg (final), plus (PlusPowers on the attacker), inHand (PlusPowers in its hand), left (the Defending Pokemon's HP left
// before the hit). Whether it was knocked out is read at the steps after (koOff: turns after the hit's own turn, null if not).
// C107, with --timing-card "Gust of Wind": each play's entry also has target {slot (the bench index), card, left} and koOff.
const liveGames = new WeakSet();
const sameTurnKo = (g, ft, turn0) => {      // koOff of the watched Pokemon: found in their owner's discard pile; turn0 is the turn the step began in
  ft.watch = ft.watch.filter(w => {            // (an attack ends the turn before its knockout is checked, so the step's own turn counts)
    if (cardsOf(g, w.owner, 'discard').includes(w.card)) { w.rec.koOff = turn0 - w.turn; return false; }
    return !g.done && turn0 - w.turn <= 1;
  });
};
// C106 pipeline check: the attack options legal at decision d, the Active's Energy count and each attack's printed cost size.
function atkView(g, d) {
  const me = g.state.players.find(p => p.id === d.playerId), card = me.active.getPokemonCard();
  return { attacks: d.options.map(o => o.key).filter(k => k.startsWith('attack|')), energy: me.active.energies.cards.length, enames: me.active.energies.cards.map(c => c.name), sp: me.active.specialConditions, mon: card && card.name, first: g.state.turn <= 2,
           costs: card ? Object.fromEntries(card.attacks.map(a => [a.name, a.cost.length])) : {}, opts: d.options.map(o => o.key) };
}
function hookDamage(g) {
  const store = g.store, orig = store.reduceEffect;
  store.reduceEffect = function (state, effect) {
    const r = orig.call(this, state, effect);
    if (effect.type === 'PUT_DAMAGE_EFFECT' && effect.target === effect.opponent.active && effect.target.getPokemonCard()) {
      const t = effect.target, card = t.getPokemonCard(), dmg = Math.max(0, effect.damage), cnt = cs => cs.filter(c => c.name === 'PlusPower').length;
      const rec = { game: g.uid, seat: effect.player.id, turn: state.turn, attacker: effect.source.getPokemonCard().name, attack: effect.attack.name,
                    printed: effect.attack.damage, def: card.name, hp: card.hp, left: card.hp - (t.damage - dmg), base: effect.baseDamage, dmg,
                    plus: cnt(effect.source.trainers.cards), inHand: cnt(effect.player.hand.cards), att: effect.source.trainers.cards.map(c => c.fullName), atkTypes: effect.source.getPokemonCard().cardTypes,
                    weak: card.weakness, resist: card.resistance, koOff: null };
      swStats.pp.push(rec);
      g.ft.watch.push({ rec, card, owner: effect.opponent.id, turn: state.turn });
    }
    return r;
  };
}
// Game.step is wrapped for the live games (those a SwitchAgent has seen; search copies are never in liveGames). A play of the
// timing card opens an entry {seat, turn, V}; when its prompts are done the fetched card (the hand's gain) and the discards
// (the discard pile's gain, less the card itself) are read off the zones; then a play, attach or evolve of a card of the fetched
// card's name by that seat in that turn marks it used. V is the pilot's value at the playing decision (followValue, called
// from SwitchAgent.act), after at the seat's first asked decision in a later turn, or the seat's reward if the game ended.
const isTiming = key => TIM.card && (key.startsWith('trainer|' + TIM.card + '|') || key.startsWith('trainer|' + TIM.card + ' '));   // keys carry the full name ("Computer Search BS")
const cardsOf = (g, id, zone) => g.state.players.find(p => p.id === id)[zone].cards;
const bag = cs => { const m = new Map(); for (const c of cs) m.set(c.fullName, (m.get(c.fullName) || 0) + 1); return m; };
const gain = (now, before) => {      // the cards of `now` beyond `before` (multiset difference)
  const m = bag(before), out = [];
  for (const c of now) { if (m.get(c.fullName) > 0) m.set(c.fullName, m.get(c.fullName) - 1); else out.push(c); }
  return out;
};
const TYPES = ['none', 'Pokemon', 'Trainer', 'Energy'];
function followValue(g, seat, v) {
  liveGames.add(g);
  g.ftV = v;
  for (const e of (g.ft ? g.ft.all : [])) if (e.after === null && e.seat === seat && g.state.turn > e.turn) e.after = v;
}
if (TIM.card) {
  const origStep = Game.prototype.step;
  Game.prototype.step = function (i) {
    if (!liveGames.has(this) || this.done) return origStep.call(this, i);
    const ft = this.ft || (this.ft = { all: [], cur: null, watch: [] });
    if (TIM.card === 'PlusPower' && !ft.hooked) { ft.hooked = true; hookDamage(this); }
    const d = this.decision(), opt = d && d.options[i];
    if (opt && !ft.cur && !d.prompt && isTiming(opt.key)) {
      const e = { game: this.uid, seat: d.playerId, turn: this.state.turn, V: this.ftV, after: null, fetched: null, type: null, discards: null, used: null };
      ft.cur = { e, hand: cardsOf(this, e.seat, 'hand').slice(), disc: cardsOf(this, e.seat, 'discard').slice() };
      if (TIM.card === 'Gust of Wind') {      // C107: the Defending Pokemon and the bench's, to name the target after
        const o = this.state.players.find(p => p.id !== e.seat);
        ft.cur.opp = { active: o.active.getPokemonCard(), bench: o.bench.map(s => s.getPokemonCard()) };
      }
      if (TIM.card === 'PlusPower') e.pre = atkView(this, d);
      ft.all.push(e); swStats.ft.push(e);
    } else if (opt && !d.prompt) {
      if (TIM.card === 'PlusPower') for (const e of ft.all) if (e.post && e.chose === undefined && e.seat === d.playerId) e.chose = opt.key;
      const [kind, name] = opt.key.split('|');
      for (const e of ft.all) if (e.used === false && e.seat === d.playerId && e.turn === this.state.turn && name === e.fetched &&
                                 (kind === 'basic' || kind === 'evolve' || kind === 'attach' || kind === 'trainer')) e.used = true;
    }
    const turn0 = this.state.turn, r = origStep.call(this, i);
    const nd = this.done ? null : this.decision();
    if (ft.cur && (!nd || !nd.prompt)) {      // the card's prompts are over
      const { e, hand, disc } = ft.cur, cur = ft.cur;
      ft.cur = null;
      if (TIM.card === 'PlusPower') {
        const me = this.state.players.find(p => p.id === e.seat);
        e.post = nd ? atkView(this, nd) : null;
        e.attached = me.active.trainers.cards.filter(c => c.name === 'PlusPower').length;
        e.discardedPP = cardsOf(this, e.seat, 'discard').filter(c => c.name === 'PlusPower').length;
      }
      const got = gain(cardsOf(this, e.seat, 'hand'), hand), dis = gain(cardsOf(this, e.seat, 'discard'), disc);
      const self = dis.findIndex(c => c.name === TIM.card);
      if (self !== -1) dis.splice(self, 1);
      if (got.length) { e.fetched = got[0].fullName; e.type = TYPES[got[0].superType]; e.used = false; }
      e.discards = dis.map(c => c.name);
      if (TIM.card === 'Gust of Wind') {
        const o = this.state.players.find(p => p.id !== e.seat), card = o.active.getPokemonCard();
        if (card && card !== cur.opp.active) {
          e.target = { slot: cur.opp.bench.indexOf(card), card: card.name, left: card.hp - o.active.damage };
          e.koOff = null;
          ft.watch.push({ rec: e, card, owner: o.id, turn: this.state.turn });
        }
      }
    }
    sameTurnKo(this, ft, turn0);
    if (this.done) for (const e of ft.all) if (e.after === null) e.after = this.reward(e.seat);
    return r;
  };
}

// Wraps a model seat (RemoteAgent): asks the pilot for every decision as usual, then applies the switches to its answers.
// A random prompt answer is drawn from a fresh Rng seeded by the game's own RNG state (cloned, so the game's flips and
// shuffles are untouched) and its step count: the same state gives the same draw, on every worker.
class SwitchAgent {
  constructor(inner) {
    this.inner = inner; this.slot = inner.slot; this.cfg = cfgOf(inner.slot);
    this.oracle = this.cfg.SW.oracle ? new PromptOracle(inner.slot) : null;
    this.tOracle = this.cfg.TIM.oracle ? new PromptOracle(inner.slot) : null;      // C99's timing oracle
  }

  forget(game) { this.inner.forget(game); }

  async act(batch) {
    const out = await this.inner.act(batch);
    const st = swStats, redo = [], search = [], tsearch = [];
    st.acts++;
    if (TIM.card) batch.forEach((b, i) => followValue(b.env.game, b.env.current.playerId, out[i].value));
    batch.forEach((b, i) => {
      const g = b.env.game, opts = b.env.current.options, key = a => opts[b.legal.indexOf(a)].key;
      st.asked++;
      if (g.decision().prompt) {
        const turnPlayer = g.state.players[g.state.activePlayer].id;
        if (!g.chain || !g.chain.key.startsWith('trainer|') || b.env.current.playerId !== turnPlayer) return;
        const name = g.chain.key.split('|')[1];
        const t = st.byTrainer[name] || (st.byTrainer[name] = { prompts: 0, randomized: 0, changed: 0, searched: 0, unsearchable: 0 });
        t.prompts++; st.trainerPrompts++;
        const msg = String(g.decision().prompt.message);
        if (this.oracle) {      // X1b: searched below, all of this batch's at once (C102: only the --oracle-prompts kind)
          if ((this.cfg.OPROMPTS === 'all' || msg === OMSG[this.cfg.OPROMPTS]) && this.cfg.isOTrainer(name)) search.push({ i, b, t, msg });
          return;
        }
        if (this.cfg.SW.prompts !== 'random') return;
        const ok = b.legal.filter(a => key(a) !== 'cancel');
        if (!ok.length) return;
        const a = ok[new Rng((g.rng.clone().u32() ^ Math.imul(g.steps + 1, 0x9e3779b1)) >>> 0).int(ok.length)];
        t.randomized++; st.randomized++;
        if (a !== out[i].action) { t.changed++; st.changed++; }
        out[i] = { ...out[i], action: a };
      } else {
        const attacks = b.legal.filter(a => key(a).startsWith('attack|')), chose = key(out[i].action);
        if (attacks.length) { st.attackOffered++; if (chose.startsWith('attack|')) st.attacked++; }
        if (this.tOracle) {      // C99: the timing card is a legal option
          const cs = b.legal.find(a => isTiming(key(a)));
          if (cs !== undefined) tsearch.push({ i, b, cs });
        }
        if (chose !== 'pass') return;
        st.passes++;
        if (!attacks.length) return;
        st.passWithAttack++;
        if (this.cfg.SW.pace === 'attack') redo.push({ i, item: { ...b, legal: attacks } });
      }
    });
    if (redo.length) {      // the pilot's greedy pick with only the attacks legal: its top-rated attack
      const again = await this.inner.act(redo.map(r => r.item));
      redo.forEach((r, k) => {
        if (!r.item.legal.includes(again[k].action)) throw new Error('must-attack: the pilot answered off the attack options');
        out[r.i] = { ...out[r.i], action: again[k].action };
        st.passToAttack++;
      });
    }
    if (search.length) {    // X1b: the oracle's pick replaces the pilot's (the Runner asks only decisions with 2+ options)
      const res = await this.oracle.searchAll(search.map(x => ({ b: x.b, pick: out[x.i].action })), st);
      search.forEach((x, k) => {
        if (!res[k]) { st.unsearchable++; x.t.unsearchable++; return; }
        st.searched++; x.t.searched++; st.oracleBy[x.msg] = (st.oracleBy[x.msg] || 0) + 1;
        if (res[k].action !== out[x.i].action) { st.changed++; x.t.changed++; }
        out[x.i] = { ...out[x.i], action: res[k].action };
      });
    }
    if (tsearch.length) {   // C99: the timing oracle's pick replaces the pilot's
      const res = await this.tOracle.searchAll(tsearch.map(x => ({ b: x.b, pick: out[x.i].action, cs: x.cs })), st);
      tsearch.forEach((x, k) => {
        if (!res[k]) { st.tUnsearchable++; return; }
        st.tSearched++;
        const was = out[x.i].action;
        if (res[k].action !== was) { if (was === x.cs) st.tHolds++; else st.tPlays++; }
        out[x.i] = { ...out[x.i], action: res[k].action };
      });
    }
    return out;
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
    const { Env } = require('../env.js');
    const items = caught.map(c => {
      const env = new Env(enc, { showOpponentDecklist: c.show });
      env.game = c.game;
      env.decklists = c.decklists;
      const t = env.observe();
      return { obs: t.obs, legal: t.legal, env };
    });
    const S = new PolicySearchAgent(new RemotePilot(0, probe.k || 4), enc, { k: probe.k || 4, dets: probe.dets || 4,
      maxSteps: probe.maxSteps || 40, seed: (probe.seed || 0) ^ cmd.seed, crn: true, keepLines: true });
    const res = [];
    for (let i = 0; i < items.length; i += 32) res.push(...await S.act(items.slice(i, i + 32)));
    return caught.map((c, i) => ({ k: c.k, cands: res[i].cands || null, scores: res[i].scores || null })).filter(p => p.cands);
  };
  return { onDecision, search };
}

// Plays the listed games and reports each one's result (rl/gpu_matrix.py, rl/metagame.py). Deck i is
// piloted by model slot cmd.slots[i], or by slot 0 in both seats. With cmd.out, both seats' decisions
// are recorded and written there.
async function games(cmd) {
  const t0 = Date.now(), cpu0 = process.cpuUsage();     // X1b copy: cpu0 for sizing
  const encoding = cmd.encoding || 'tokens';
  const enc = encoding === 'tokens' ? tokens : identity;
  const agents = {};
  // A recorded seat plays as 'r<slot>', an unrecorded one as 'o<slot>': the same model slot, but only the
  // 'r' names are recorded.
  swStats = newSwitchStats();                          // probe copy: this command's switch counts
  if (TIM.card) swStats.ft = [];                       // C99: this command's timing-card plays
  if (TIM.card === 'PlusPower') swStats.pp = [];       // C106: its damage hits
  const pilot = (i, rec) => {
    const slot = cmd.slots ? cmd.slots[i] : 0;
    const name = (rec ? 'r' : 'o') + slot;
    if (!agents[name]) {                               // probe copy: every model seat behind the switches
      agents[name] = new SwitchAgent(new RemoteAgent(slot, encoding, !!cmd.greedy));
    }
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
             seats: { 1: seat(ia), 2: seat(ib) } };
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
            { k: js.k || 4, dets: js.dets || 4, maxSteps: js.maxSteps || 40, seed: (js.seed || 0) + slot, crn: !!js.crn });
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
  const cpu = process.cpuUsage(cpu0);                  // X1b copy: CPU ms and wall ms of this command, for sizing
  return { ok: true, games: results.length, seconds: (Date.now() - t0) / 1000, results,
           ...(cmd.out ? { out: cmd.out, transitions: out.rec.action.length } : {}), ...(js ? { searchStats } : {}),
           ...(probes ? { probes } : {}), switches: SW, ...(SIDE === -1 ? {} : { switchesB: CFGS[1].SW }),
           switchStats: { ...swStats, cpuMs: Math.round((cpu.user + cpu.system) / 1000), wallMs: Date.now() - t0 } };
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
      if (msg.cmd === 'games') { tokens.history = msg.history || 0; tokens.chain = msg.chain || 0; }
      if (msg.cmd === 'games') { F.writeJson(process.stdout, await games(msg)); return; }
      throw new Error('unknown command ' + msg.cmd);
    } catch (e) {
      F.writeJson(process.stdout, { ok: false, error: String(e && e.stack || e) });
    }
  });
});
