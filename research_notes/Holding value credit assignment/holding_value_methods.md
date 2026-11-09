# Teaching a policy when to hold a one-shot resource (PlusPower): credit-assignment methods

Scope: methods with no human data, expert labels or oracle answers, testable as a 30-minute PPO arm on a fixed-deck bench with save/restore and branched rollouts. About 22 search/fetch calls. Evidence is from abstracts and search summaries only, not full-text reads, unless stated. "Measured" means the cited authors' reported result. "Inference" means my reasoning, not tested. Nothing in this file was run on your simulator.

## 1. Longer-horizon branch comparisons for play-vs-hold, and game-AI evidence

### Takeaway
I found no reliable published source on learning when to hold a consumable via longer branch comparisons. The horizon/variance trade-off below is my reasoning, not literature. The one thing that probably matters most: the continuation policy used after a "hold" branch must itself use the card well, or a longer horizon still scores hold as worthless.

### Cited Findings
- Hearthstone MCTS work uses determinization for hidden information and "action chains" for several actions within one turn. The 2018 paper (Swiechowski et al.) reports that simple neural networks can serve as state evaluators inside MCTS. No hold-timing result was found. — [Improving Hearthstone AI by Combining MCTS and Supervised Learning](https://arxiv.org/pdf/1808.04794); [NTNU thesis](https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2420367)
- A 2022 SBGames paper formulates collectible-card-game battles as an MDP with deep RL on Legends of Code and Magic, and notes that game AI has arguably not reached human level in Magic or Hearthstone. — [SBGames 2022](https://sol.sbc.org.br/index.php/sbgames/article/view/23454)
- OpenAI Five scripted item purchase order and removed some items that need multi-unit control. The paper says the agent could perform better if it controlled item actions. The search found nothing on consumable or ultimate timing. — [Dota 2 with Large Scale Deep RL (arXiv 1912.06680)](https://arxiv.org/abs/1912.06680) via [alphaxiv summary](https://alphaxiv.org/abs/1912.06680)
- AlphaStar (Vinyals et al., Nature 575, 2019) reached Grandmaster using a league, but it also learned from human games, so it is excluded by your constraint. No result on resource-timing was found. — [DeepMind blog](https://deepmind.google/blog/alphastar-grandmaster-level-in-starcraft-ii-using-multi-agent-reinforcement-learning/)

### Inferences
- Your hypothesis fits the setup. At the end of the turn, V(hold) is only higher than V(play) if V has learned that a PlusPower in hand is worth something. V is trained on returns from a policy that plays it with every attack, so V sees the card as worthless in hand. The comparator therefore returns about 0 at non-knockout rows. This loop is self-reinforcing. (Conjecture, consistent with your +0.09 / ~0 measurement.)
- Horizon options, cheapest first:
  - A. End of own next turn (2 own turns), 4-8 CRN copies. The opponent's intervening turn adds variance. Pair the copies on the same seed so the opponent's randomness cancels in the difference.
  - B. Game end, as a one-off diagnostic. It has the highest variance and the highest cost.
  - C. A fixed-horizon branch with a hold-aware continuation policy. For example, the continuation plays PlusPower only when a one-ply simulator check says +10 converts a knockout. This uses the simulator's rules, not human data. It may count as an oracle shortcut for training, so flag it for Evan before using it. (Judgment call.)
- Use option C only as an upper-bound diagnostic. Otherwise use a continuation that is the current policy with epsilon-random hold, so V and the branch values see held-card futures at all.
- Search-improved targets (AlphaZero style: the policy is trained toward what a short search prefers) are the standard way to break "the continuation policy is bad" loops. I did not find a source for this in the results, so treat it as background knowledge, not cited.

### Gaps
- No source found on learned hold-vs-play timing in Hearthstone, Magic, poker, or Go. The search was limited, and Magic RL agent papers did not surface.
- No source found for the variance of paired CRN rollouts as a function of horizon in card games.
- OpenAI Five and AlphaStar appendices were not read in full, so consumable/ultimate timing remains unchecked.

## 2. Return decomposition and redistribution (RUDDER, Align-RUDDER)

### Takeaway
RUDDER's core needs no demonstrations: an LSTM regresses the episode return and credit is redistributed by contribution analysis. It could credit a hold for a later payoff in principle, but it needs a decent number of episodes where the payoff appears, and the sparse 19% knockout-with-PlusPower events inside a long game are noisy. Align-RUDDER requires demonstrations and is excluded.

### Cited Findings
- RUDDER: Arjona-Medina, Gillhofer, Widrich, Unterthiner, Brandstetter, Hochreiter, NeurIPS 2019. It redistributes reward so that expected future reward is about zero; return decomposition is posed as regression. It creates a return-equivalent MDP with the same optimal policies. — [NeurIPS page](https://papers.nips.cc/paper/9509-rudder-return-decomposition-for-delayed-rewards); [arXiv 1806.07857](https://arxiv.org/abs/1806.07857)
- Reported: exponentially faster than TD, MC and MCTS on artificial delayed-reward tasks; PPO + RUDDER improves Atari scores most in delayed-reward games. These are the authors' claims; exact scores were not retrieved. — [NeurIPS poster](https://nips.cc/virtual/2019/poster/14291)
- Limits: the redistribution is optimal only if the return predictor is perfect; early in learning, predictor error cannot be told from reward noise; zero expected future reward is generally not achievable in MDPs. A NeurIPS 2019 reviewer reported worse performance on a significant portion of Atari games. — [arXiv 1806.07857 (v2 pdf)](https://arxiv.org/pdf/1806.07857v2); [NeurIPS reviews](https://papers.nips.cc/paper_files/paper/2019/file/16105fb9cc614fc29e1bda00dab60d41-Reviews.html)
- Align-RUDDER: Patil et al., ICML 2022. It assumes high-reward episodes are given as DEMONSTRATIONS and replaces the LSTM with a profile model from multiple sequence alignment. It can build a profile from as few as two demonstrations. — [PMLR v162](https://proceedings.mlr.press/v162/patil22a.html); [JKU record](https://research.jku.at/en/publications/align-rudder-learning-from-few-demonstrations-by-reward-redistrib/)
- A 2025 follow-up argues that return decomposition ignores temporal dependence between actions. — [arXiv 2503.17409](https://export.arxiv.org/pdf/2503.17409)

### Inferences
- Here RUDDER would redistribute the game outcome (win/loss) onto the PlusPower-holding step if the LSTM learns that "PlusPower in hand and later knockout-with-PlusPower" predicts a win. The redistributed reward goes to that later step, not to the hold decision. Credit for the hold only appears if the contribution analysis marks the earlier held-state as important. Uncertain.
- Wins are a binary return per game across ~dozens of turns; per-game signal is weak. A 30-minute arm would likely have too little data to fit the LSTM. A cheaper variant: decompose the branch-rollout value differences, not wins. (Conjecture.)
- Fit cost is high relative to a 30-minute arm; rank it low.

### Gaps
- Exact RUDDER Atari numbers were not retrieved.
- No source found showing RUDDER on a consumable-timing task.

## 3. Hindsight credit, counterfactual baselines, expected traces, synthetic returns

### Takeaway
These reduce variance or move credit across time, but every one assumes the evaluator has some signal on the delayed effect. They do not solve a value function that is blind to a held card's later use. Synthetic returns is the closest in spirit: it learns which earlier states predict a later reward.

### Cited Findings
- Hindsight Credit Assignment (HCA): Harutyunyan, Dabney, ..., Precup, Singh, Munos, NeurIPS 2019 (spotlight). It credits past actions by how likely they were to produce an observed outcome, using information gathered after the fact. Experiments focus on variance reduction and partial observability in diagnostic tasks. — [NeurIPS 2019](https://proceedings.neurips.cc/paper/2019/hash/195f15384c2a79cedf293e4a847ce85c-Abstract.html)
- Counterfactual Credit Assignment (CCA): Mesnard et al., ICML 2021, PMLR 139. Value functions are conditioned on future events, with the hindsight information constrained to exclude the agent's own actions so the baseline stays unbiased; the authors claim provably low variance. No numbers in the abstract. — [PMLR](https://proceedings.mlr.press/v139/mesnard21a.html); [arXiv 2011.09464](https://arxiv.org/abs/2011.09464)
- Expected Eligibility Traces: van Hasselt, Madjiheurem, Hessel, Silver, Barreto, Borsa, AAAI 2021, pp. 9997-10005. A single update reaches states that could have preceded the current one; ET(lambda) strictly generalises TD(lambda). — [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/17200); [arXiv 2007.01839](https://arxiv.org/abs/2007.01839)
- Synthetic Returns: Raposo, Ritter, Santoro, Wayne, Weber, Botvinick, van Hasselt, Song (preprint, arXiv Feb 2021; no venue shown on the arXiv page; a GitHub README cites a different title, so the venue is unconfirmed). State-associative learning links states to distant future rewards; reported 25x faster than the published state of the art on Atari Skiing with an IMPALA agent. — [arXiv 2102.12425](https://arxiv.org/abs/2102.12425)
- A TMLR 2024 survey (Pignatelli, Ferret, Geist, Mesnard, van Hasselt, Toni) unifies these and discusses diagnosing why a method fails; useful for choosing a diagnostic. Author list differs across sources. — [arXiv 2312.01072](https://arxiv.org/abs/2312.01072)

### Inferences
- CCA/HCA: conditioning the PPO baseline on "was there a knockout opportunity in the next k turns" (a future event not caused by the play/hold action itself, but note holding changes whether PlusPower is available, so the independence condition is violated and the baseline could be biased; I flag this as a real risk) would cut variance but not remove the bias that holding is undervalued.
- Synthetic returns: the SR module could learn that "PlusPower in hand" predicts later knockout-conversion reward bumps, giving the hold state a positive value. It needs reward events (knockouts, prizes) as the "far reward" and enough examples where holding led to one. Cost: an attention module over episode memory. Moderate; try a simplified version: regress later-prize-gain on hand contents.
- Expected traces: limited fit; this is for non-sequential reachability, not for option value.

### Gaps
- No numbers for HCA/CCA effect sizes were retrieved (abstracts only).
- No published test of any of these on consumable timing.

## 4. All-action / expected policy gradients

### Takeaway
Citations verified. They reduce variance only; they keep the same expected gradient. When the evaluated advantage is about 0 in the states where holding matters (non-knockout rows) they provide no push. They would help only if the advantage at each candidate is evaluated at every row, which you already do at the dense rows.

### Cited Findings
- Mean Actor-Critic: Allen, Asadi, Roderick, Mohamed, Konidaris, Littman, 2017 (arXiv 1709.00503). It averages the Q-value over all actions with the policy distribution, claiming lower gradient variance for discrete actions. Venue not confirmed in what I read (I believe it is an arXiv preprint; the name "Asadi et al." in your brief is a secondary author listing, since Allen is first author). — [arXiv 1709.00503](https://arxiv.org/pdf/1709.00503v2)
- Expected Policy Gradients: Ciosek and Whiteson, AAAI 2018; extended in JMLR 2020 (v21, 18-012). It integrates over actions, unifies stochastic and deterministic PG, and reports lower variance. — [AAAI](https://ojs.aaai.org/index.php/AAAI/article/view/11607); [JMLR](https://www.jmlr.org/beta/papers/v21/18-012.html)
- All-Action Policy Gradient Methods: A Numerical Integration Approach: Petit, Amdahl-Culleton, Liu, Smith, Bacon, NeurIPS 2019 Optimization Foundations of RL workshop (arXiv 1910.09093). It connects all-action estimators to conditional Monte Carlo and gives a result on biased critics. — [arXiv 1910.09093](https://arxiv.org/abs/1910.09093)
- These papers note that they independently re-discovered the same all-action idea. — [search summary](https://arxiv.org/pdf/1910.09093.pdf)

### Inferences
- Why they will not fix your failure: with two candidates and Adv ~ 0 at non-knockout rows, the all-action gradient is p(play)*A(play) + p(hold)*A(hold); if A(hold) = A(play) = 0 there, the gradient is 0, so nothing pushes against over-playing. The over-playing is held in place by the positive rows through shared parameters. This is the same bias, now without sampling noise. (Reasoning, not measured.)
- A direct fix that stays inside this family: apply the candidate comparison at non-knockout rows with a hold bonus equal to the card's option value (section 6).

### Gaps
- No evidence found about all-action PG when the critic is wrong in a systematic way (the Petit et al. biased-critic result may be relevant but was not read).

## 5. Value-function fixes (auxiliary prediction, successor features, TD(lambda), n-step)

### Takeaway
Auxiliary prediction of future card use and longer-bootstrapped targets are cheap and plausible. The chicken-and-egg loop is only broken if the data contains held-card futures, e.g. by forced exploration of holds. I found no published test of this on consumables.

### Cited Findings
- UNREAL: Jaderberg et al., ICLR 2017. Auxiliary tasks (pixel control, reward prediction) on an A3C base raised mean performance to 87% of expert human vs 54% for vanilla A3C and reached A3C's best in ~10x fewer steps (on Labyrinth); 880% human-normalized on Atari. — [arXiv 1611.05397](https://alphaxiv.org/abs/1611.05397); [DeepMind blog](https://deepmind.google/blog/reinforcement-learning-with-unsupervised-auxiliary-tasks/)
- Successor features: Barreto et al., NIPS 2017, transfer across tasks that differ only in reward; value splits into dynamics (features) and reward. — [NIPS 2017](https://papers.nips.cc/paper/2017/hash/350db081a661525235354dd3e19b8c05-Abstract.html). Deep extension: Barreto et al., ICML 2018 (arXiv 1901.10964) — [arXiv](https://arxiv.org/abs/1901.10964)

### Inferences
- Auxiliary head arm (cheapest): add heads on the value trunk predicting (a) number of own attack-turns in the next k turns with a knockout-convertible margin, (b) whether PlusPower will be played in the next k turns. The trunk then encodes hold-relevant information. The head targets come from real trajectories, not oracle labels. Caveat: the value head still reads those features only as learned from policy data; it does not by itself raise V(hold).
- Successor-feature variant: features = [prizes taken, PlusPower played, knockouts converted with +10] discounted over turns; V = w . psi; swapping w lets you ask "what is a card worth" without retraining. Heavier; not a 30-minute arm.
- Longer-lambda: GAE/TD(lambda) with lambda near 1 across turns spreads the later knockout payoff back to the hold state. It works only if those payoffs occur in the data. The ordinary on-policy data have few holds (the policy plays always), so lambda alone will not break the loop. Forced exploration is the missing piece: with probability eps, override to hold (or to play) at attack-available decisions in rollouts and in the PPO data (using importance-corrected or off-policy-aware treatment, or simply keep eps small and log its action probability). (Conjecture; this is standard practice, no source retrieved.)
- Option-value shadow price (my own idea, untested): estimate from your own logs the mean extra value of a held PlusPower, i.e. P(knockout turn arrives) x (gain at knockout, +0.09-ish), and charge it as a cost when the card is played at non-knockout rows. Because you measured the +0.09 and the 19% frequency, the price is self-derived, not human prior; but it is a hand-built shaping term, so label it as such in the log.

### Gaps
- No evidence found that auxiliary heads fix hold-valuation; UNREAL shows only general representation benefits.
- Successor-feature hold-valuation: no source.

## 6. Consumable-item and use-it-or-save-it decisions in RL

### Takeaway
I found no paper that treats this as a studied problem. Adjacent evidence is thin, so assume this is an open gap and rely on the credit-assignment tools above.

### Cited Findings
- NetHack Learning Environment (Kuttler et al., NeurIPS 2020) is a procedurally generated stochastic roguelike with 93 actions, including potions and other items. Item functions are randomized each game. No paper in the search addressed when to save vs use consumables. — [NLE paper](https://arxiv.org/pdf/2006.13760); [NeurIPS 2020](https://papers.nips.cc/paper/2020/hash/569ff987c643b4bedf504efda8f786c2-Abstract.html); [LuckyMera](https://arxiv.org/pdf/2307.08532)
- OpenAI Five scripted item purchases rather than learning them (see section 1).

### Inferences
- Adjacent literature that I did not search and cannot cite: optimal stopping / secretary problems (use-it-or-lose-it with an arrival process), inventory control, and ultimate-timing in MOBA agents. These would give the structure V_hold = E[max future opportunity]. Marked as unsourced background knowledge.

### Gaps
- No consumable-timing study found for NetHack, Dota, StarCraft, Hearthstone, Magic or poker. A targeted search (e.g. "resource conservation", "optimal stopping RL", Pluribus/ReBeL bet sizing as analog) was not run.

## Ranked arms for a 30-minute PPO test (my recommendation; all unmeasured)

1. Forced-hold exploration plus 2-own-turn CRN branch comparison with an epsilon-hold continuation (cost: about 2x current branch cost; bias: continuation still undervalues hold; variance: high, mitigate with paired seeds and 8 copies at the 19% dense rows only).
2. Same plus an option-value shadow price charged at non-knockout play rows (cost: negligible; bias: hand-built constant; read it as a diagnostic, not a final method).
3. Auxiliary heads on the value trunk for future knockout-convertible attack turns and future PlusPower use (cost: small; bias: none directly).
4. Dense-row candidate comparison at all attack-available rows with hold evaluated (all-action form) to add variance reduction only (cost: small).
5. Simplified synthetic returns or RUDDER-on-branch-differences (cost: highest, benefit uncertain).
Bands for each should be written before running, against the baseline noise (0.442-0.455 measured), per working rule 12; an oracle ceiling of 0.52 is your measurement.
