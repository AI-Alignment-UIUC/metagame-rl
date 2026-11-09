# Warm-started PPO self-play drift, under-priced setup actions, and search/regularisation fixes (A1)

Scope note: about 17 tool calls. Most fetches returned only arXiv abstracts, so claims are limited to abstracts and search snippets unless marked "from memory" or "as read in search_and_credit.md" (the earlier note, which read Danihelka, Grill, Muesli and KataGo in more depth; not repeated here, only built on). Loop-change lines are my proposals, not literature.

## 0. New facts from audit A2 (coordinator, 17:17) and what they change

These come from the project's own audits (notes/audits.md), not from literature.
- C70/X5: replacing a list's 6 Trainers with basic Energy scores 0.444±0.015 vs its copy; off-type Energy 0.484; Clefairy Doll (near-blank card) 0.506. Doll minus basic Energy = +0.062±0.010.
- C69/X3: the Trainer deficit is the same off-mirror (vs the other 23 lists) as in the mirror (-0.040 vs -0.039), so it is general.
- X1: random answers inside Trainer prompts change nothing.

Inference: the pilot's Trainer play is no better than random or blank, and the Trainers only tie a near-blank card. That reframes the topic. "Drift erodes the value of Trainers" implies the start pilot once valued them; the A2 data says it never used them competently. So the main problem is missing signal (no one in the loop can score what happens inside Trainer prompts), and drift is secondary (5 min of plain PPO costs only 0.474 -> 0.469). Every finding below should be read against this: anchors and plasticity fixes can at best preserve 0.474; only a stronger pro-Trainer signal raises M.

Loop change: before any regulariser experiment, run a probe on whether the search can score Trainer-internal prompts at all (search skips them today, per the brief). Cost: read-only grep of the probe code in rl/ plus a 5-minute ar/ run; allowed (game-agnostic, no card names).

## Q1. Why does policy-gradient self-play under-price actions whose payoff is option value or information (draw, search) relative to immediate tempo?

### Takeaway
No source I found measures this exact effect in card games; the closest are the Hanabi signalling/babbling-equilibrium result and the general credit-assignment story (long horizon, terminal reward, noisy value). The mechanism is consistent with the project's data but is inference: a draw or search action has zero immediate effect and its benefit is realised only if a later, correctly chosen action uses the card, so the advantage signal is small, noisy and conditional on other skills the policy lacks.

### Cited Findings
- Hanabi paper: players must convey information implicitly through action choice, and self-play can settle in pooling or babbling equilibria where signals are ignored, so no player is rewarded for starting to communicate — [Bard et al., Hanabi Challenge](https://ar5iv.arxiv.org/html/1902.00506) (via search snippet).
- A 2026 paper "Reevaluating Policy Gradient Methods for Imperfect-Information Games" says naive self-play DRL in adversarial imperfect-information games was long thought to fail, motivating FP, double oracle and CFR-based methods; I saw only the abstract-level mention — (title seen in [search results](https://arxiv.org/pdf/1902.00506v1); paper not fetched, source unverified).
- Practice-game facts from the brief: 62% of games end by KO of a lone Pokémon, 32% at the time limit, 5% by prizes. Games decided by a quick KO give a terminal reward that correlates with tempo (Energy attached, attacker out), not with draw or search.
- Policy gradient credit assignment (GAE trade-off bias vs variance, Schulman et al. 2016, from memory): with gamma 1 and a terminal reward, a setup action gets credit only through the value head's estimate or through lambda-weighted future TD errors. The project's A1 results (lambda 1.0 -0.03; 0.8 +0.013 then +0.006) show shorter credit helped; that is evidence the long-horizon signal is mostly noise for this pilot.

### Inferences
- Under the A2 facts, the pilot's value head probably cannot tell a state with a played Trainer from a blank card, so the advantage of a Trainer-play action is about zero in expectation, while extra Energy has a measurable immediate effect (more attacks possible). PPO then pushes toward Energy through the entropy-regularised gradient with no counterweight. This matches "5 min of plain training lowers M" and "LR x6 cut M".
- Myopia is not the same as a short gamma: gamma is already 1. The shortfall is a learning-signal one (value error), so a value-quality fix is more relevant than changing the discount.

### Gaps
- No found paper isolating draw/search "option value" under PPO in a TCG. Not found: Stratego, poker or Atari "myopic policy" measurements with numbers.

Loop change: log, per action category (supplied by the engine as generic "prompt kind", not card names), the mean advantage and the value-head error. A diagnostic only, no training edit; cost one 5-minute run; allowed. If the Trainer-play advantage is about zero, the next items (search on Trainer prompts) outrank all regularisers.

## Q2. Search-based policy improvement at small budgets, and the top-k blind spot

### Takeaway
At 40 steps and 4 lines, the literature says use Gumbel-Top-k sampling without replacement from the policy plus a completed-Q soft target (Danihelka 2022), and train on a bounded target (Muesli/CMPO). Top-4 by the policy is exactly the blind spot: a move whose policy probability is low (Trainer play, if the pilot disfavours it) is never scored, so search cannot raise it. Gumbel-Top-k keeps low-probability moves a nonzero chance of being scored.

### Cited Findings
- Gumbel MuZero: AlphaZero "can fail to improve its policy network, if not visiting all actions at the root"; Gumbel-Top-k plus sequential halving "guarantees a policy improvement when action-values are correctly evaluated"; learns with 2 simulations on 9x9 Go — [Danihelka et al. 2022](https://openreview.net/forum?id=bERaNdoegnO), as read in search_and_credit.md.
- Grill et al. 2020: at Nsim = 5 on Ms Pacman, most of the gain came from using the regularised-optimisation solution as the learning target — [Grill et al.](https://arxiv.org/abs/2007.12509), as read earlier.
- Muesli: the CMPO target's TV distance from the prior is at most tanh(c/2) — [Hessel et al.](https://arxiv.org/abs/2104.06159), as read earlier.
- Student of Games: a single algorithm combining guided search, self-play learning and game-theoretic reasoning (growing-tree CFR with a value/policy net), sound in the limit; strong in chess, Go, heads-up no-limit hold'em and Scotland Yard — [Schmid et al., Science Advances 2023](https://arxiv.org/pdf/2112.03178) (abstract and snippets only).
- KataGo playout-cap randomisation: full search on a fraction of turns; only those are recorded as targets — [Wu 2019](https://arxiv.org/abs/1902.10565), as read earlier.
- Sampled MuZero (Hubert et al. 2021, [arXiv](https://arxiv.org/abs/2104.06303)): search over a sampled subset of actions with a sampling correction (from memory, not re-read).
- ReBeL (Brown et al. 2020, from memory): search in public belief states with a learned value net and self-play; relevant to the hidden-hand structure but heavy (no fetch; treated as out of budget, noted in the earlier file).

### Inferences
- The brief's "search only scores moves the policy already likes" is the same condition under which Danihelka's Example 1 fails, but it is weaker here: the target is soft and clipped (DISTILL_CLIP 1.0, tau 0.1), so it can only reshuffle probability among the top 4, never promote a fifth move. Trainer plays outside the top 4 are untouched. The measured +0.007 from top 8 instead of top 4 is consistent with a small effect from widening, but it is one seed pair, not a trend.
- The A2 finding that search "skips prompts inside Trainers" is a second blind spot, independent of top-k: the Trainer's cost-benefit choices (which card to discard, which target) never get a signal. Gumbel does not fix this.
- Allocation across decisions: KataGo-style (few, deeper probes) vs the project's p = 0.05 with 4 dets x 40 steps. Without a measured line-noise estimate this is a guess.

### Gaps
- No evidence on Gumbel-style search specifically for games with 100+ action prompts and hidden hands.

Loop change (a): replace probing the top 4 by a Gumbel-Top-k draw of 4-6 candidates from the policy's softmax (plus the policy argmax). Needs a change in the Node probe selection, probably outside ar/train.py (confirm where k is applied; `PROBE["k"]` is passed to the engine); if it is engine-side this is blocked by the "a change to rl/, env/ or engine means new --setup" rule. Cost: small edit plus a re-setup; allowed by training rules. Loop change (b): make the target Danihelka-style, softmax(logits + sigma(completed Q)), with unprobed moves at v_mix. In ar/train.py this edits the 6 lines computing `a_hat`/`lt` only; screen = 5-min run x 2 seeds; allowed. Loop change (c): extend probing to Trainer prompts (if the engine can); this is the highest-value item given section 0; cost depends on engine; allowed.

## Q3. Regularisation toward an anchor or a search policy

### Takeaway
KL-to-anchor methods (piKL, R-NaD, MMD) prevent drift and cycling; none of them creates a missing skill. Here the anchor is the start pilot, which scores 0.474, so an anchor caps the loss at 0.005 and cannot gain. It becomes useful only combined with a pro-Trainer signal that is strong enough to need bounding (the failed tripled search weight).

### Cited Findings
- piKL: KL-regularised search toward an imitation-learned policy gives stronger play than imitation alone in chess and Go, and matches human-prediction accuracy while being "substantially stronger" in no-press Diplomacy — [Jacob et al. 2022](https://arxiv.org/abs/2112.07544) (abstract only; the anchor in the paper is a human-imitation policy, which the project cannot use as a prior, but the start pilot is a human-free anchor).
- DeepNash/R-NaD: a model-free self-play agent without search; R-NaD changes the learning dynamics so the agent converges to an approximate Nash equilibrium "instead of cycling around it"; top-3 on Gravon in 2022 and all-time — [Perolat et al. 2022](https://arxiv.org/abs/2206.15378) (abstract only; the reward-transformation mechanism with a periodically updated regularisation policy is from memory).
- Magnetic mirror descent: a mirror-descent-inspired method with a "magnetic" pull toward a reference policy, with linear convergence to QRE in extensive-form games, competitive with CFR in tabular settings and favourable self-play deep RL results in 3x3 Dark Hex and Phantom Tic-Tac-Toe — [Sokota et al. 2022](https://arxiv.org/abs/2206.05825) (abstract only).
- AlphaStar leagues (Vinyals et al. 2019, from memory): exploiter agents and past-version opponents prevent forgetting and cycling in a non-transitive game; not re-read.
- The project: half the practice games against a frozen copy of the start gave +0.023 (seed 1) and +0.004 (seed 2); a noisy result, not yet a trend.

### Inferences
- Plain PPO clip already gives a per-iteration trust region, but nothing ties the policy to the start across iterations; a KL-to-start term (coefficient beta) is a one-line addition: `loss += beta * KL(pi_start || pi)`, with pi_start's logits from the frozen start model (fixed.start_model with no grad; costs one extra forward per micro-batch, about +30% compute; the per-batch clock is fixed at 5 minutes, so there are fewer games).
- A cheaper equivalent already measured is the frozen-copy opponent (+0.023/+0.004). Both seeds are non-negative; a third and fourth seed would settle it.
- piKL is search-regularised: the search policy is the target, KL(pi || anchor) the penalty. The project's soft search target already has this form (`lt = lpc + a_hat` is the anchor-plus-advantage solution), so DISTILL_TAU / DISTILL_CLIP act as the piKL lambda.

### Gaps
- No full-text read of any of these; hyperparameter ranges for beta are not available from what I read.

Loop change: add `KL_ANCHOR` beta in {0.1, 1.0} to ar/train.py (5 lines, KL on the legal-move distribution against the frozen start). Screen = 2 betas x 2 seeds x 5 min = 20 minutes plus overhead; allowed (no human data). Expectation: M stays at 0.474 rather than 0.469, which is not a gain. Run it only as a guard for Q2(b)/(c) with a larger search weight, where the strength guard previously failed at weight x3. Also repeat the frozen-start-opponent condition on seeds 3-4 (cost about 20 minutes).

## Q4. Warm-start pathologies: plasticity, primacy bias, value refit, and when degradation starts

### Takeaway
Plasticity-loss papers show drift in networks trained for long non-stationary streams; they are probably not the main factor for a 5-minute run (about 4,500 games, a few dozen PPO iterations), though the value head mismatching a new policy is a real short-run effect. The cheapest relevant fix is refitting the value head before policy updates.

### Cited Findings
- Lyle et al. 2023: plasticity loss is "closely linked to changes in the curvature of the loss landscape", often occurs without saturated units, and was checked on ALE — [Lyle et al.](https://arxiv.org/abs/2303.01486) (abstract only; specific mitigations not in the abstract).
- Dohare et al. (Nature 2024): standard deep learning loses the ability to keep learning in continual settings, down to the level of a shallow network; continual backprop (reinitialising a small fraction of less-used units) maintains plasticity; L2 plus weight perturbation (shrink-and-perturb style) substantially eases the loss — [Dohare et al. arXiv version](https://arxiv.org/abs/2306.13812), [Nature record](https://ideas.repec.org/a/nat/nature/v632y2024i8026d10.1038_s41586-024-07711-7.html); the authors' repository includes a PPO component (snippet only; task details and the length of runs not verified).
- Nikishin et al. 2022: agents over-rely on early interactions; periodic partial resets improve results on Atari 100k and DM Control — [Nikishin et al., ICML 2022](https://proceedings.mlr.press/v162/nikishin22a.html). That evidence is for off-policy agents with replay; PPO here is on-policy with fresh data each iteration, so primacy bias in the replay sense does not apply directly (my inference).
- Critic pretraining before actor updates: reported to stabilise PPO in RLHF (Secrets of RLHF, [arXiv 2307.04964](https://arxiv.org/pdf/2307.04964)); a frozen-actor critic phase followed by a lower actor LR and tighter clip (ADEPT, [arXiv 2608.19182](https://arxiv.org/pdf/2608.19182)); a warm-started critic kept explained variance positive in T1 ([arXiv 2609.11042](https://arxiv.org/pdf/2609.11042)); a reward/value mismatch explains PPO collapse in long-CoT ([arXiv 2503.01491](https://arxiv.org/pdf/2503.01491)). These are search-result summaries, not read in full; the Secrets paper also found critic initialisation from a reward model or SFT model converged similarly. They are LLM-RL, so the transfer to a game is by analogy only.
- The project's evidence: 5 min of plain training lowers M 0.474 -> 0.469 and the optimiser state is loaded from the start (`opt.load_state_dict`) with LR reset.

### Inferences
- If the start pilot's value head was trained on a different opponent mix or on search-improved play, the first PPO iterations get biased advantages; a value-only first iteration (policy frozen, value loss only, one or two iterations, about 10% of the budget) removes that error before it moves the policy. This is the standard "critic warm-up" pattern in the sources above.
- Adam state loaded from the start run has second-moment estimates matching the old loss scale; adding the search term at weight 20 changes the scale. Zeroing or re-warming the optimiser moments is a cheap alternative (inference, no source).
- Shrink-and-perturb (multiply weights by ~0.9-0.99 plus small noise, from memory) acts against the pilot's skill; with 5-minute runs it likely costs more than it saves. Not recommended.

### Gaps
- When exactly warm-started PPO first degrades the policy: not found for this setting. Own diagnostic needed: the per-iteration M is too expensive; entropy and sd_kl from the log are the free signals.

Loop change: in ar/train.py add `VALUE_ONLY_ITERS = 1`: for the first iteration, use `loss = VF * v_loss` only (skip pi_loss and sd KL). Cost: 4 lines; screen = 2 seeds x 5 min; allowed. Second probe: log explained variance of the value head per iteration (free), to test the Q4 inference.

## Q5. Value targets: TD(lambda) vs Monte Carlo, distributional and auxiliary heads, and the price of delayed actions

### Takeaway
In long noisy games a lower lambda lowers variance at the cost of bias against delayed payoffs; the project's own lambda sweep (0.8 better than 0.95, 1.0 worse) already says variance dominates. Auxiliary heads are the standard way to give delayed actions a denser signal without hand-built shaping.

### Cited Findings
- Project sweep: lambda 1.0 -0.03; lambda 0.8 +0.013 then +0.006 (A1, brief).
- GAE trade-off between bias and variance (Schulman et al. 2016, from memory; not re-read).
- Distributional value heads and auxiliary prediction tasks (C51 / Muesli-style model heads, from memory): Muesli's value and model losses include prediction of future rewards/values — [Hessel et al. 2021](https://arxiv.org/abs/2104.06159), abstract-level as read earlier.
- VinePPO: learned PPO value networks "often misestimate intermediate values" in reasoning, favouring Monte Carlo estimates of intermediate states (as summarised in the search results, [arXiv 2410.01679](https://arxiv.org/html/2410.01679v2); LLM domain).

### Inferences
- A value head that cannot tell a Trainer-played state from a blank-card state (section 0) gives no advantage to Trainer play at any lambda. Lambda changes variance, not that blindness; so a further lambda sweep (0.7, 0.6) will probably give diminishing returns of the +0.006 kind.
- Self-discovered auxiliary targets that are game-agnostic: prediction of own/opponent prize count and hand size a few turns ahead (generic public state features the engine provides). These make "hand grew by 3" a measurable, supervised effect, giving draw actions a dense signal. This follows the same shape as the earlier note's auxiliary-task suggestion; whether it respects "no card-specific shaping" depends on the feature list (hand size is generic; I rate it allowed, but Evan should confirm).
- MC returns from search lines (VinePPO-like) at probed decisions would give a lower-bias Q at exactly the decisions that matter; that is what the soft search target already supplies.

### Gaps
- No found evidence on TD(lambda) vs MC for hidden-information card games.

Loop change: lambda 0.7 (1 constant; 2 seeds x 5 min) as the cheapest follow-up; an auxiliary head for hand-size/prize deltas is a model change (MODEL_OVERRIDES starts new weights fresh and would lose the warm start; implement as an extra linear head on the existing trunk instead), cost about 40 lines and a ≤70-minute screen; allowed if the targets are generic public-state counts.

## Ranked summary of loop changes (cost, allowed)
1. Q2(c) / section 0: search or otherwise score Trainer-internal prompts. Engine-side; the only change aimed at the diagnosed blindness (A2). Allowed.
2. Q4: VALUE_ONLY_ITERS = 1. Tiny, 10 minutes. Allowed.
3. Q2(b): Gumbel completed-Q target; and (a) Gumbel-Top-k candidates. Small; the second needs an engine re-setup. Allowed.
4. Q3: KL-to-start with beta 0.1/1.0, as a guard rail only. 20 minutes. Allowed.
5. Q5: lambda 0.7; auxiliary hand-size head. Small / ≤70 minutes. Allowed pending the Evan's check on the feature list.
6. Frozen-start opponent: add seeds 3 and 4. 20 minutes.
Not recommended: shrink-and-perturb or resets (Q4), full ReBeL/SoG machinery (cost, and the earlier expert-iteration design already failed).
