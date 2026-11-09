# Exploration for rare, situational actions in policy-gradient RL (large discrete action sets)

Evidence tags: [snippet] = taken from search-result text only (no full page fetched in this pass); [memory] = from prior knowledge, not checked in this session, verify before citing. No human data is used by any method below.

## Why entropy-regularized PPO collapses on rare good actions

### Takeaway
For a softmax policy, the expected logit gradient for action i is proportional to pi(i) times its advantage, so an action the policy has already driven to near-zero probability gets almost no push back up. Entropy bonuses and forced exploration act on the same scale. The fixes that address this are changes to the update geometry or to the behaviour policy, not just larger bonuses.

### Cited Findings
- Entropy change under softmax policy-gradient updates is driven by the covariance between action log-probability and advantage; high-covariance (frequent, already-favoured) actions drive collapse; Clip-Cov and KL-Cov restrict updates on those tokens and keep entropy up. Evidence is LLM reasoning RL, token level, not card games. — [Cui et al., arXiv:2505.22617](https://arxiv.org/abs/2505.22617) [snippet]
- The same study reports performance trading off against entropy, with a ceiling on further improvement. — [Cui et al.](https://arxiv.org/abs/2505.22617) [snippet]
- A follow-up reports that more severe entropy collapse tracks miscalibration, and that off-policy update counts shape entropy dynamics. — [Revisiting Entropy in RL for Large Reasoning Models, arXiv:2511.05993](https://arxiv.org/pdf/2511.05993v1) [snippet]
- Mirror-descent policy optimization (MDPO) gives a trust-region form: on-policy it links to TRPO and PPO; off-policy with the trust region centred on the uniform policy it coincides with SAC. Reported on par with or better than TRPO, PPO and SAC on continuous control. — [Tomar et al., arXiv:2005.09814](https://arxiv.org/abs/2005.09814) [snippet]
- Discrete SAC (categorical policy, Q per action, entropy-regularized objective) was reported competitive with tuned model-free baselines on Atari without hyperparameter tuning. — [Christodoulou, arXiv:1910.07207](https://arxiv.org/abs/1910.07207) [snippet]
- A later study says poor discrete-SAC adaptation comes from policy instability and underestimated Q-values, not from target-entropy settings. — [Zhou et al., Revisiting Discrete SAC, arXiv:2209.10081](https://arxiv.org/abs/2209.10081) [snippet]

### Inferences
- Softmax logit gradient for action i in expectation is pi(i)(Q(i) - V). A rare action therefore moves at a rate set by its own probability: near-zero probability means near-zero gradient. This is why the pilot's PlusPower probability stays flat even when its critic is right. [memory: standard softmax policy-gradient identity; verify against Agarwal et al. 2020 "On the theory of policy gradient methods" and Mei et al. 2020 on softmax convergence before citing]
- Entropy bonus has the same scaling: its logit gradient is about pi(i)(-log pi(i) - H), which is slow for tiny pi(i). A coefficient of 0.01 is unlikely to lift PlusPower from ~0.4%-level probability. This is a derivation, not measured here.
- Multiplicative (exponentiated-advantage) updates in the mirror-descent form, pi_new proportional to pi_old^(1-eta) exp(eta Q), do not carry the pi(i) factor. A rare action with high Q grows exponentially in the step count rather than linearly in its tiny probability. This is the most direct response to the collapse mechanism, and it differs from the banned distillation attempts because the target comes from the update itself. [inference; the MDPO snippet supports the mirror-descent framing only]
- Clip-Cov / KL-Cov style restriction is a plausible candidate: the pilot's dominant plays (high probability, positive advantage) would be the high-covariance ones, and throttling them could free probability for rare actions. Untested in card games.

### Gaps
- No card-game or large-discrete-action evidence for covariance clipping or mirror updates was found in this pass.
- The softmax gradient results above are from memory; not verified.

## Deep exploration: posterior sampling, randomized values, optimism, novelty

### Takeaway
Posterior-style exploration (randomized value functions, randomized priors) gives action-level uncertainty from an ensemble, which can select rare actions when the critic disagrees with itself. Count and novelty bonuses are the standard alternative, but they are state-space signals and do not directly say a rare action is valuable.

### Cited Findings
- Randomized value functions: sample from a proxy of the posterior over value functions and act greedily on the sample, giving deep exploration. — [Osband, Van Roy, Russo, Wen, arXiv:1703.07608](https://arxiv.org/abs/1703.07608) [snippet]
- Randomized prior functions: add a fixed, randomly initialized prior network to each ensemble member; the authors claim an efficiency proof for linear representations; presented at NeurIPS 2018. — [Osband, Aslanides, Cassirer, arXiv:1806.03335](https://arxiv.org/abs/1806.03335) [snippet]
- Never Give Up (NGU): per-episode episodic-memory k-NN novelty multiplied by a clipped RND lifelong term; first positive score on Pitfall! without privileged information in the reported comparison. — [Badia et al., arXiv:2002.06038](https://arxiv.org/pdf/2002.06038) [snippet]

### Inferences
- Randomized value heads (ensembles with priors) act on the critic's own uncertainty rather than the policy's probability. This targets the specific gap here: the critic credits PlusPower, the policy does not play it. Use the ensemble to generate behaviour actions, then correct with importance ratios, since PPO's clip limits off-policy drift. [inference]
- NGU-style novelty is aimed at states, not actions. For PlusPower the novelty of the state where it pays is low once visited, so novelty alone does not guarantee the action is taken. Lower priority than the value-disagreement signal.
- No large-discrete-action card-game evidence was found for ensembles. Atari and continuous-control results are the main evidence.

### Gaps
- Did not find a head-to-head of randomized value heads vs NGU on large discrete action sets.

## Meta-control over exploration rates (Agent57, population training, Go-Explore)

### Takeaway
Agent57 reports the first deep RL agent above the human benchmark on all 57 Atari games, using a bandit meta-controller that picks exploration and discount settings per actor. A population with mixed entropy levels is the cheap version of this for a PPO pilot.

### Cited Findings
- Agent57 reports above-human scores on all 57 Atari games, with a non-stationary bandit selecting among policies with different exploration weights and discounts; it builds on NGU. — [Badia et al., arXiv:2003.13350](https://arxiv.org/abs/2003.13350) [snippet]
- Go-Explore archives promising states, returns to them, then explores; reported solving all previously unsolved Atari games and orders-of-magnitude gains on Montezuma's Revenge and Pitfall, using a restart-from-archive mechanism. — [Ecoffet et al., arXiv:2004.12919](https://arxiv.org/abs/2004.12919) [snippet]

### Inferences
- A population of PPO pilots with entropy coefficients spanning a wide range (including values far above 0.01), with a bandit selecting by episode return, is the Agent57 idea applied to entropy rather than to NGU's intrinsic reward. It keeps the policy-collapse fix inside the policy learner, unlike search distillation. [inference]
- Go-Explore's restart mechanism overlaps the banned restart-distribution item; mention only as the archive idea, not as a new restart scheme.

### Gaps
- Agent57's exploration-rate table and bandit details were not read in full in this pass.

## Exploration through search: Gumbel and Sampled MuZero

### Takeaway
Gumbel MuZero guarantees policy improvement from a few simulations by sampling root actions without replacement via Gumbel-Top-k. Sampled MuZero plans over a small random subset of actions for large action spaces. Both keep rare actions in the candidate set only if the sampling distribution gives them mass.

### Cited Findings
- Gumbel AlphaZero and MuZero: root actions drawn without replacement with Gumbel-Top-k; policy improvement guaranteed for correctly estimated values; AlphaZero can fail to improve if not all root actions are visited. Matches state of the art on Go, chess and Atari, with large gains at low simulation counts. — [Danihelka et al., ICLR 2022](https://iclr.cc/virtual/2022/poster/6418) [snippet]
- A later comparison reports Gumbel Zero performing well with as few as two simulations. — [MiniZero, arXiv:2310.11305](https://arxiv.org/abs/2310.11305) [snippet]
- Sampled MuZero plans over K sampled actions and approaches the all-action baseline as K grows (Go); tested also on Ms. Pac-Man and continuous control. — [Hubert et al., arXiv:2104.06303](https://arxiv.org/abs/2104.06303) [snippet]

### Inferences
- Gumbel-Top-k is drawn from the policy's logits, so a PlusPower with pi near zero needs enormous Gumbel noise to be sampled. It does not solve the rare-action problem by itself. The rare-action fix is a proposal distribution that mixes in the critic or uniform mass, with importance correction (Sampled MuZero's route). That proposal mixture is close to the banned forced-uniform item, so the difference must be stated: here the mixture feeds the critic's targets, not the executed actions. [inference]
- Sampled MuZero's point is that a bounded candidate set is enough when it is resampled; this bears on the legal-action count in the pilot.

### Gaps
- Gumbel and Sampled MuZero are search-time methods; their policy-training effect on a PPO learner is not established by these sources.

## Self-play exploration: league, PSRO, exploiters

### Takeaway
In self-play the rare-action gap can be closed by coverage: exploiter agents trained against the main policy will reach the states where a rare play matters. This is different from single-agent exploration because the opponent distribution itself shifts.

### Cited Findings
- PSRO trains approximate best responses to mixtures of policies, unifying independent RL, double oracle and fictitious play; it reports robustness gains in poker. — [Lanctot et al., arXiv:1711.00832](https://arxiv.org/abs/1711.00832) [snippet]
- AlphaStar's league used main exploiters (target the main agent) and league exploiters (target the whole pool), with periodic exploiter resets; reported Grandmaster rank across all three races, above 99.8% of ranked humans. — [AlphaStar, Nature 2019 PDF copy](https://www.seas.upenn.edu/~cis520/papers/RL_for_starcraft.pdf) [snippet]
- Follow-up argues the original exploiters were limited; proposes goal-conditioned exploiters that find main-agent weaknesses more effectively. — [ROA-Star, NeurIPS 2023](https://papers.neurips.cc/paper_files/paper/2023/file/94796017d01c5a171bdac520c199d9ed-Paper-Conference.pdf) [snippet]

### Inferences
- An exploiter trained against the pilot (rewarded for beating it) generates trajectories where the pilot's zero-probability plays matter, supplying the rare-situation coverage that the single-agent fixes lack. This is untested for this game. It also goes beyond the banned items, since the coverage comes from opponents rather than from restarts, rewards or distillation.

### Gaps
- No evidence was found on exploiter effectiveness for card-game deck-building or drafting.

## Ranked candidates to test (inference, not measured)

1. Mirror-descent / exponentiated-advantage update on the pilot policy (geometry fix; tests the pi(i) gradient explanation first, on a single decision type).
2. Covariance-throttled update (KL-Cov style) on the dominant high-probability plays.
3. Population of pilots with entropy coefficients spread across a wide range, selected by bandit (Agent57 style).
4. Randomized value-head ensemble as the behaviour policy with importance correction.
5. Exploiter agents in the league.

Cheapest informative first test: a single-state bandit where a rare action has known high value; measure whether mirror-descent and covariance-throttled updates raise its probability faster than vanilla PPO at the same step count. Stop rule and runtime to be set with launch-run.
