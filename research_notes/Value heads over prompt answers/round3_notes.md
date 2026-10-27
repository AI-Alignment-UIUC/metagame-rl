# Round 3 (Evan, 2026-10-27 about 07:25, relayed by 333-10): which ways of learning a value over a prompt's answers pick up a 0.02 signal?

Three Haiku lean-readers, launched 08:39. Usage at 08:39: 5-hour 3%, week 84% (resets 09:00). Every source was read
at abstract or snippet level only; no full text. Round 1 (this file's sibling folder, `Learning sparse target
choices/`) already covered variance reduction, paired rollouts, Muesli, CMPO and MPO.

## Measured here (A1's stored probes, `runs/probe/A1-targetsignal/a1.json.probes.json.gz`, 488 decisions, m 32)
- Answers per decision: mean 3.6, median 3.
- **Discordance rate**, the share of CRN-paired rollouts where two answers' outcomes differ: mean 0.20, median 0.16.
  A quarter of answer pairs never differ at m 32.
- Arithmetic (reader 1's formula, our d): a 0.02 expected gap at a z of 2 needs about 40,000·d paired seeds, so about
  8,000 at d 0.2. Independent sampling needs about 20,000. CRN is worth about 2.5x; no single decision is resolvable
  at any affordable m.
  - So a head must pool across decisions.
  - The oracle can't give exact per-decision truth. It gives a reliability R, read through split halves.
- A1 already stores what the candidates need: per (answer, rollout), the terminal reward and the seat's values at its
  own later decisions (`vals`), plus the option vectors (`emb`) and V0 from the offline rerun.
- Oracle reliability by Spearman-Brown from A1's R at m 32 (named five 0.26, all prompts 0.08): at m 256 the named
  five reach about 0.74 and all prompts about 0.41; at m 128, 0.58 and 0.26. This is an extrapolation.

## Readers (snippets only; their inferences marked)
1. **Losses** (reader 1):
   - Bradley-Terry or logistic loss on within-seed pairs only ever sees the paired difference, so it cancels the shared
     seed noise. Dueling bandits (Yue et al., COLT 2009).
   - Runarsson & Lucas 2014 (Othello): preference learning beat TD there (snippet).
   - Only discordant pairs carry information (McNemar), with draws counted as 0.5.
   - Seed-centred regression (subtract each seed's mean across answers) is the simple form of the same control
     variate.
   - Dueling heads and advantage learning address representation, not noise (inference).
2. **Targets and heads** (reader 2):
   - Truncated rollouts bootstrapped with V (AlphaGo's leaf mixing, Silver 2016) is the one change argued to cut
     outcome noise by a large factor. It adds V's error as bias.
   - TD(λ) (GAE, Schulman 2015) and doubly robust control variates (Jiang & Li 2016) are unbiased with V fixed. Their
     gain depends on V's accuracy.
   - C51, IQN and bootstrapped ensembles: no source shows they help small-gap ranking. They average estimation noise,
     not outcome noise (inference).
   - Successive halving and OCBA help budget allocation, but not the decisive pair at a 0.02 gap (inference).
3. **Representation** (reader 3):
   - A shared card embedding with pointer-style scoring (Vinyals 2015; Chandak 2019) lets a 0.02 signal pool across
     prompts that share a card.
   - Condition the answer on the resolving Trainer: Q = f(state, trainer, card).
   - Short-horizon auxiliary heads (UNREAL, Jaderberg 2016) and self-predictive latents (SPR, Schwarzer 2021) are
     denser and self-supervised. Prize or hand-size proxies need a worker change, because A1 doesn't store them.
   - AlphaStar's pointer: UNVERIFIED.

## Result: C95 candidates (on the C94 oracle) and the C96 search check
- C95 (`runs/probe/C95-qhead-candidates/record.md`): 8 candidates ranked, plus a quarantined capacity check. The data
  are the C94 oracle (O), C94's frozen trajectories (S) and a new branched self-play set at m 8 (B).
- C96 (`runs/probe/C96-search-M/record.md`): auditor A79's call, M with and without search at every decision. It
  extends C73, which searched prompts only.
