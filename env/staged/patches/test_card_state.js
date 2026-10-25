// Checks of the token encoder's canon option (env/staged/patches/card_state.patch, state_canon; env/tokens.js), CPU only:
//   (a) canon = 0: every field of every encoding equals the encoder of a clean tree (BASE_ENV: 77fbae0 + card_latent.patch)
//   (c) canon = 1, on random-play games of the 24 archived lists: every listed card flags its zone token (HAND, MY_DISCARD,
//       MY_UNSEEN, OPP_DISCARD) or has a PROMPT token; PROMPT / PICKED tokens remain only for such cards; picked cards flag
//       a token; the resolving Trainer carries the source flag; flags sit on zone kinds only; counts per prompt type are printed
//   (z) the largest copy count of a card in a list, and in any zone token seen (the canon cap is 31)
// Run (after both patches are applied to the tree ENV_DIR points at):
//   ENV_DIR=<tree>/env BASE_ENV=<clean tree>/env node test_card_state.js [--games 12] [--seed 1]
'use strict';
const path = require('path');
const ENV = path.resolve(process.env.ENV_DIR || path.join(__dirname, '..', '..'));
const BASE = process.env.BASE_ENV ? path.resolve(process.env.BASE_ENV) : null;
const { Env } = require(path.join(ENV, 'env.js'));
const { TokenEncoder, KIND } = require(path.join(ENV, 'tokens.js'));
const { archivedDecks } = require(path.join(ENV, 'decks.js'));

const argv = process.argv.slice(2);
const arg = (k, d) => (argv.includes(k) ? Number(argv[argv.indexOf(k) + 1]) : d);
const GAMES = arg('--games', 12), SEED = arg('--seed', 1);
const decks = archivedDecks();
const fails = [];
const fail = m => { if (fails.length < 40) fails.push(m); };
const FIELDS = ['tokCard', 'tokKind', 'tokAux', 'glob', 'slots', 'cand'];
const ZONES = [KIND.HAND, KIND.MY_DISCARD, KIND.OPP_DISCARD, KIND.MY_UNSEEN, KIND.OPP_DECKLIST, KIND.PROMPT, KIND.PICKED];
const NAME = { [KIND.HAND]: 'HAND', [KIND.MY_DISCARD]: 'MY_DISCARD', [KIND.MY_UNSEEN]: 'MY_UNSEEN', [KIND.OPP_DISCARD]: 'OPP_DISCARD', [KIND.PROMPT]: 'PROMPT' };

// (z) copies in the lists
let maxList = 0;
for (const d of decks) {
  const m = new Map();
  for (const c of d.cards) m.set(c, (m.get(c) || 0) + 1);
  maxList = Math.max(maxList, ...m.values());
}
console.log(`(z) most copies of one card in the ${decks.length} lists: ${maxList} (canon cap 31)`);
if (maxList > 31) fail(`a list has ${maxList} > 31 copies of a card: canon clamps it`);

class Lcg { constructor(s) { this.s = s >>> 0; } next(n) { this.s = (Math.imul(this.s, 1664525) + 1013904223) >>> 0; return (this.s >>> 8) % n; } }

const mk = (Cls, canon) => { const e = new Cls(); e.history = 3; e.chain = 4; e.canon = canon; return e; };
const plain = mk(TokenEncoder, 0), canon = mk(TokenEncoder, 1);
const base = BASE ? mk(require(path.join(BASE, 'tokens.js')).TokenEncoder, 0) : null;

const stat = {};      // prompt type -> counters
const S = t => stat[t] || (stat[t] = { n: 0, listed: 0, flagged: { HAND: 0, MY_DISCARD: 0, MY_UNSEEN: 0, OPP_DISCARD: 0 }, noHome: 0, promptTok: 0,
  picked: 0, pickedFlag: 0, pickedTok: 0, src: 0, srcHand: 0, srcDisc: 0, srcPrompt: 0 });
let decisions = 0, offEq = 0, grew = 0, srcExtra = 0, tokPlain = 0, tokCanon = 0, maxZoneAux = 0, srcSeen = 0;

function listedOf(prompt) {
  const l = prompt.cards ? (prompt.cards.cards || prompt.cards) : prompt.cardList ? prompt.cardList.cards : null;
  return Array.isArray(l) && !(prompt.options && prompt.options.isSecret) ? l : null;
}
function tokensOf(o, kind) { const r = []; for (let i = 0; i < o.nTok; i++) if (o.tokKind[i] === kind) r.push(i); return r; }

function check(env, d) {
  const g = env.game, pid = d.playerId;
  const decksV = env.visibleDecks(pid);
  const P = plain.encode(g, pid, decksV, d.options), Cn = canon.encode(g, pid, decksV, d.options);
  decisions++;
  if (base) {
    const B = base.encode(g, pid, decksV, d.options);
    const same = FIELDS.every(f => Buffer.compare(Buffer.from(P[f].buffer), Buffer.from(B[f].buffer)) === 0) && P.nTok === B.nTok && P.nCand === B.nCand;
    if (same) offEq++; else fail(`canon=0 differs from the clean tree at decision ${decisions}`);
  }
  const state = g.state, me = state.players.find(p => p.id === pid), opp = state.players.find(p => p.id !== pid);
  for (let i = 0; i < P.nTok; i++) if (ZONES.includes(P.tokKind[i])) maxZoneAux = Math.max(maxZoneAux, P.tokAux[i]);
  // flags on zone kinds only, and the non-zone tokens equal the plain ones
  const rest = o => { const r = []; for (let i = 0; i < o.nTok; i++) if (!ZONES.includes(o.tokKind[i])) r.push(`${o.tokCard[i]}|${o.tokKind[i]}|${o.tokAux[i]}`); return r.join(); };
  if (rest(P) !== rest(Cn)) fail('a non-zone token (slot, attached, history, stadium) differs between canon and plain');   // flags only on zone kinds
  tokPlain += P.nTok; tokCanon += Cn.nTok;
  const prompt = d.prompt;
  const src = prompt && g.chain && g.chain.key.startsWith('trainer|') && state.players[state.activePlayer].id === pid
    ? canon.cardId.get(g.chain.key.split('|')[1]) || 0 : 0;
  if (Cn.nTok > P.nTok) { grew++; if (!(src && Cn.nTok === P.nTok + 1)) fail(`canon has more tokens than plain (${Cn.nTok} vs ${P.nTok}) without a source token`); }
  if (!prompt) {
    if (Cn.nTok !== P.nTok) fail('no prompt, yet token counts differ');
    for (const k of [KIND.PROMPT, KIND.PICKED]) if (tokensOf(Cn, k).length) fail(`kind ${k} token without a prompt`);
    return;
  }
  const s = S(prompt.type); s.n++;
  const listed = listedOf(prompt);
  const home = [[me.hand.cards, KIND.HAND], [me.discard.cards, KIND.MY_DISCARD], [me.deck.cards, KIND.MY_UNSEEN],
    [opp.discard.cards, KIND.OPP_DISCARD], ...me.prizes.map(z => [z.cards, KIND.MY_UNSEEN])];
  const needPrompt = new Set();
  if (listed) for (const c of listed) {
    s.listed++;
    const id = canon.id(c), h = home.find(x => x[0].includes(c));
    const t = h && tokensOf(Cn, h[1]).find(i => Cn.tokCard[i] === id);
    if (t !== undefined) {
      if (!(Cn.tokAux[t] & 32)) fail(`listed ${c.fullName} not flagged on its ${NAME[h[1]]} token`);
      s.flagged[NAME[h[1]]]++;
    } else { needPrompt.add(id); s.noHome++; }
  }
  const pt = tokensOf(Cn, KIND.PROMPT);
  s.promptTok += pt.length;
  for (const i of pt) if (!needPrompt.has(Cn.tokCard[i]) && Cn.tokCard[i] !== src) fail(`PROMPT token ${Cn.tokCard[i]} for a listed card with a zone token`);
  for (const id of needPrompt) if (!pt.some(i => Cn.tokCard[i] === id)) fail(`listed card ${id} has no zone token and no PROMPT token`);
  // picks: every plain PICKED token (id) is a 64 flag on some token of that id in canon, or a PICKED token when no zone holds it
  for (const pi of tokensOf(P, KIND.PICKED)) {
    const id = P.tokCard[pi];
    s.picked++;
    const f = []; for (let i = 0; i < Cn.nTok; i++) if (Cn.tokCard[i] === id && (Cn.tokAux[i] & 64)) f.push(i);
    const stillPicked = tokensOf(Cn, KIND.PICKED).some(i => Cn.tokCard[i] === id);
    if (f.length) s.pickedFlag++;
    else if (stillPicked) {
      s.pickedTok++;
      const zoned = [KIND.HAND, KIND.MY_DISCARD, KIND.MY_UNSEEN, KIND.OPP_DISCARD, KIND.PROMPT].some(k => tokensOf(Cn, k).some(i => Cn.tokCard[i] === id));
      if (zoned) fail(`picked ${id} has a zone token yet kept a PICKED token`);
    } else fail(`picked ${id} lost`);
  }
  if (src) {
    srcSeen++; s.src++;
    const at = []; for (let i = 0; i < Cn.nTok; i++) if (Cn.tokCard[i] === src && (Cn.tokAux[i] & 128)) at.push(Cn.tokKind[i]);
    if (!at.length) fail('resolving Trainer carries no source flag');
    else if (at[0] === KIND.HAND) s.srcHand++; else if (at[0] === KIND.MY_DISCARD) s.srcDisc++; else s.srcPrompt++;
    if (at.length > 1) fail('source flag on more than one token');
  } else for (let i = 0; i < Cn.nTok; i++) if (Cn.tokAux[i] & 128 && ZONES.includes(Cn.tokKind[i])) fail('source flag without a resolving Trainer');
}

for (let gi = 0; gi < GAMES; gi++) {
  const env = new Env(plain, { u8: true });
  const rng = new Lcg(SEED * 1000 + gi);
  let t = env.reset(decks[(gi * 5 + SEED) % decks.length].cards, decks[(gi * 11 + 3) % decks.length].cards, 700 + gi + SEED * 100);
  let steps = 0;
  while (!t.done && steps++ < 1500) {
    const d = env.game.decision();
    check(env, d);
    t = env.step(t.legal[rng.next(t.legal.length)]);
  }
}
console.log(`decisions ${decisions}; prompts ${Object.values(stat).reduce((a, s) => a + s.n, 0)}`);
if (base) console.log(`(a) canon=0 equals the clean tree on ${offEq}/${decisions} encodings`);
console.log(`(z) largest zone-token count seen (canon=0): ${maxZoneAux}`);
console.log(`(c) mean tokens plain ${(tokPlain / decisions).toFixed(2)}, canon ${(tokCanon / decisions).toFixed(2)}; canon larger in ${grew} decisions (the source token only)`);
console.log('(c) per prompt type: n listed[flag HAND/MY_DISCARD/MY_UNSEEN/OPP_DISCARD | no home] PROMPT-tokens | picked[flagged/PICKED-left] | source[n: hand/discard/PROMPT]');
for (const [t, s] of Object.entries(stat).sort()) {
  const f = s.flagged;
  console.log(`   ${t.padEnd(14)} n=${String(s.n).padStart(5)} listed ${String(s.listed).padStart(6)} [${f.HAND}/${f.MY_DISCARD}/${f.MY_UNSEEN}/${f.OPP_DISCARD} | ${s.noHome}] PROMPT ${s.promptTok}`
    + ` | picked ${s.picked}[${s.pickedFlag}/${s.pickedTok}] | source ${s.src}[${s.srcHand}/${s.srcDisc}/${s.srcPrompt}]`);
}
if (!srcSeen) fail('no resolving-Trainer prompt seen: raise --games');
if (fails.length) { console.log('FAIL', fails); process.exit(1); }
console.log('ALL PASS');
