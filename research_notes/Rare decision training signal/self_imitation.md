# Self-imitation and related ways to amplify an agent's own good outcomes, and their luck bias

Scope: learning rare sub-decisions faster (what Computer Search fetches, what Item Finder recovers) in self-play PPO for the Pokémon TCG. The outcome is win/loss with sd about 1, and the true value gap between options is about 0.02 of the result. Methods that train on human games, expert moves or oracle answers are excluded.

How each source was read (2026-10-27). Full text, via pdftotext of the arXiv PDF: SIL (1806.05635), Tang (2006.07442), SAIL (2012.11989), Paster et al. (2205.15967). Relevant sections only: CCA (2011.09464), Dichotomy of Control (2210.13435), MFEC (1606.04460), DTSIL (1907.10247), Gangwani et al. (1805.10309), PEGASUS (1301.3878), TRPO (1502.05477), AWR (1910.00177), ExIt (1705.08439), Go-Explore (1901.10995), SILfD (2203.10905), VinePPO (2410.01679). Abstract only: NGU (2002.06038). Anything marked "(from memory)" was not checked in this session.

---

## Q1. SIL (Oh et al., ICML 2018): the loss, the R > V condition, the reported gains, and stochastic environments

### Takeaway
SIL replays the agent's own past (s, a, R) and imitates an action only when the Monte Carlo return R beats the current value V(s). This gave large gains on hard-exploration Atari games and on delayed-reward MuJoCo. The lower-bound justification is stated only for deterministic environments, and the paper does not test stochastic ones. For a ±1 win/loss outcome, the SIL policy term amounts to "reinforce every win, ignore every loss". On-policy, that is still an unbiased but noisier policy gradient, so it cannot speed up learning a 0.02 gap. The bias enters through replaying old episodes and through prioritising wins.

### Cited Findings
- **Mechanism.**
  - The replay buffer stores D = {(s_t, a_t, R_t)}, where R_t is the discounted Monte Carlo return of a finished episode.
  - Losses: L_sil = E[L_policy + β_sil · L_value], with L_policy = −log π(a|s) · (R − V(s))₊ and L_value = ½ · ((R − V(s))₊)².
  - "If the return in the past is greater than the agent's value estimate (R > V), the agent learns to choose the action chosen in the past… Otherwise (R ≤ V)… not used."
  - The paper notes that the policy term is cross-entropy weighted by (R − V)₊, and is also a policy gradient that uses an off-policy MC return with V as the baseline.
  — [Oh et al. 2018](https://arxiv.org/abs/1806.05635)
- **Prioritised replay.** Transitions are sampled with priority (R − V(s))₊ "to get many state-action pairs that satisfy R > V". Exponent 0.6 and bias correction 0.1/0.4 on Atari; exponent chosen from {0.6, 1.0} on MuJoCo. — [Oh et al. 2018](https://arxiv.org/abs/1806.05635)
- **Theory.**
  - SIL equals "lower-bound soft Q-learning", L_lb = E[½ ((R − Q_θ(s,a))₊)²], in the limit α → 0.
  - The justification rests on Q*(s,a) ≥ R > Q_θ(s,a), which the paper states holds "when the environment is deterministic".
  — [Oh et al. 2018](https://arxiv.org/abs/1806.05635)
- **Hyperparameters.**
  - Atari A2C+SIL: M = 4 SIL updates per A2C update, SIL batch 512, SIL loss weight 1, β_sil = 0.01, replay buffer 10^5.
  - MuJoCo PPO+SIL: 10 SIL updates per batch, batch 512, loss weight 0.1, buffer 50,000.
  — [Oh et al. 2018, App. A](https://arxiv.org/abs/1806.05635)
- **Atari, 49 games, 50M steps (200M frames).**
  - Median human-normalised score: A2C 96.1%, ACPER (ACER-style off-policy replay with the same prioritisation) 46.8%, A2C+SIL 138.7%.
  - Games above human: A2C 23, ACPER 18, A2C+SIL 29.
  - SIL improved A2C on 35 of 49 games and on 11 of 14 hard-exploration games.
  — [Oh et al. 2018, Table 2, Fig. 4](https://arxiv.org/abs/1806.05635)
- **Hard-exploration Atari vs count-based methods.**
  - Montezuma's Revenge: A2C+SIL 2500 vs A3C-CTS 273, Reactor-PixelCNN 100, TRPO-AE-SimHash 75.
  - SIL was better on 6 of 7 games.
  - Venture: SIL "never receives a positive reward… during training", so there was nothing to imitate.
  - Note: my text extraction of the rest of Table 1 is column-shifted, so the other per-game numbers are not quoted.
  — [Oh et al. 2018, Table 1](https://arxiv.org/abs/1806.05635)
- **Documented failure mode.**
  - "[SIL] sometimes gets stuck at a sub-optimal policy on a few games, such as James Bond and Star Gunner. This suggests that excessive exploitation at the early stage of learning can hurt."
  - Reducing the number of SIL updates, or the SIL weight later in training, fixed it.
  - The reported numbers use a single best hyperparameter.
  — [Oh et al. 2018 §5.4](https://arxiv.org/abs/1806.05635)
- **MuJoCo, 10 seeds.**
  - PPO+SIL improved Swimmer, Walker2d and Ant.
  - The gap was larger on delayed-reward variants (reward accumulated every 20 steps). The authors conjecture SIL helps most when "the chance of achieving high overall rewards is much low", because it "captures such rare experiences".
  — [Oh et al. 2018 §5.6, Fig. 5](https://arxiv.org/abs/1806.05635)
- **Stochastic environments in SIL itself.**
  - The SIL paper contains no stochastic-environment experiment and no bias analysis. Its only stochasticity statement is the deterministic condition of the lower bound.
  - Later papers describe the gap:
    - Tang: plugging a single sampled return in place of Q^μ "introduces bias due to the double-sample issue, especially when R̂ has high variance either due to the dynamics or a stochastic policy" — [Tang 2020](https://arxiv.org/abs/2006.07442)
    - Ferret et al.: "the optimistic updates of SIL can lead to overestimating the value of actions that bring high rewards once in a while" — [Ferret et al. 2021](https://arxiv.org/abs/2012.11989)
    - SILfD: "stochasticity of policy or environment dynamics can cause high variance of return distribution in a given state, making critic estimate the highest rather than the expected return" — [Pshikhachev et al. 2022](https://arxiv.org/abs/2203.10905)
- **Project context.**
  - An earlier round noted that "a scalar head or self-imitation shares the value's blind spot" — `metagame-rl/notes/progress-log.md` (about line 6991).
  - A90 found that a 30-minute arm sees "20-40x too few Computer Search and Item Finder picks for PPO's credit" — `metagame-rl/notes/progress-log.md` (about line 10264).

### Inferences
All arithmetic below is my own estimate, not a measured result.

- **Binary outcomes collapse SIL's policy term.**
  - With R ∈ {+1, −1} and V ∈ (−1, 1): (R − V)₊ = (1 − V) · 1[win] = ((1 − V)/2) · (R + 1).
  - On-policy, the SIL policy gradient is therefore ((1 − V)/2) · ∇E[R]. That is an unbiased, rescaled policy gradient whose effective baseline is −1 instead of V.
  - Its per-sample second moment is about 1/(1 − p) times A2C's: 2x at p = 0.5.
  - So for a decision with a small true gap, SIL adds no signal-to-noise. It only adds sample reuse (M replays per sample) and win-only prioritisation.
- **Required sample size is unchanged.**
  - Resolving a 0.02 gap with per-game sd 1 at z = 2 takes about n = 2 · (2 · 1/0.02)² = 20,000 games per option (40,000 for a pair) at that decision.
  - Counting wins gives the same figure: Δp = 0.01 at p ≈ 0.5.
  - "Imitate the wins" cannot beat this, because counting wins is the same statistic.
  - This fits A90's "20-40x too few picks".
- **Where the bias comes from in our setting.**
  - (a) **Replay without importance weights.** Wins from older policies, and in self-play against older or weaker opponents, keep being imitated.
  - (b) **Priority (R − V)₊ samples only won games.** Every fetch target chosen in a won game is pushed up, whether or not it caused the win. Targets that co-occur with good draws gain.
  - (c) **The value loss on (R − V)₊ pushes V toward the best return seen, not the mean.** This inflates the shared critic that PPO's GAE bootstraps from.
  - (d) **Jensen's inequality.** For an action with zero advantage at V = 0 and p = 0.5, E[(R − V)₊] = 0.5 per sample, compared with a true per-action signal of about 0.01.
- **What filtered imitation of wins converges to.** In expectation it is one reward-weighted (EM) step: π_new(a|s) ∝ π_old(a|s) · P(win | s, a). For win rates 0.505 vs 0.495 that is about a 2% relative tilt per exact step, before noise. It is slow even with no noise.
- **When SIL does help.** Its evidence is for rare but large, reproducible successes in near-deterministic, sparse-reward tasks (the Montezuma key). The Computer Search / Item Finder problem is the opposite case: a frequent-enough decision, a tiny gap, and a very noisy outcome.

### Gaps
- No study measures SIL on a stochastic two-player card game or under sticky-action Atari. The SIL paper has no seed count for Atari in the text I extracted.
- I found no analysis that derives the size of SIL's bias as a function of return variance; the critiques above are qualitative.

---

## Q2. Follow-ups and critiques: generalised SIL, lower-bound Q-learning, SAIL, bias under stochastic returns, and variance-reduced versions

### Takeaway
- **Tang (NeurIPS 2020).** Recasts SIL as an operator with a positive fixed-point bias that is bounded above by Q* in the exact, expectation-based case. Bootstrapped n-step lower bounds (n = 5 best) trade contraction speed for bias; tests are mostly deterministic.
- **SAIL (AAMAS 2021).** Uses max(G, Q_target) inside an advantage-learning update, drops prioritisation to reduce the effect of stochasticity, and loses about half its gain under sticky actions.
- **Other critiques.** Several papers (ESPER, Dichotomy of Control, CCA, SILfD, Gangwani et al.) show that conditioning on or imitating single lucky returns fails in stochastic environments.
- **No significance-gated or paired-return SIL was found.** The fixes in the literature are averaging (cluster or bootstrap), independence constraints, and hindsight baselines.

### Cited Findings
- **Tang 2020, generalised SIL.**
  - Proposes "a n-step lower bound which generalizes the original return-based lower-bound Q-learning". The SIL operator T_sil Q = Q + [Q^μ − Q]₊, generalised to T_{n,sil} Q = Q + [(T^μ)^{n−1} T^π Q − Q]₊.
  - **Theorem 2.**
    - The mixed operator is contractive.
    - Its fixed point satisfies Q^{π,μ} lower bound ≤ Q̃ ≤ Q*: "unlike uncorrected n-step, for which fixed point bias could be either positive or negative, the operator for SIL induces positive bias".
    - The bias is "safe in that it is upper bounded by the optimal Q-function".
  - Empirical: TD3 + 5-step generalised SIL showed a significantly positive mean Q-bias on WalkerStand.
  - The bound uses the expectation Q^μ. Tang notes that a single-sample R̂ "introduces bias due to the double-sample issue, especially when R̂ has high variance".
  — [Tang 2020](https://arxiv.org/abs/2006.07442)
- **Tang 2020 results.**
  - TD3 on 8 tasks (DM Control, MuJoCo, Bullet), 3 seeds: "5-step generalized SIL consistently improves the performance over uncorrected n-step TD3". n = 5 worked best ("with n = ∞, SIL does not benefit from bootstrapped values at all").
  - The authors note: "Because both the dynamics and policy are deterministic, an one-sample estimate of Q-function is accurate enough". The TD3 benchmarks are deterministic.
  - PPO with delayed rewards (k ∈ {1, 5, 10, 20}), 5 seeds: PPO was "generally inferior" to SIL and generalised SIL. Which variant was best depended on the task: SIL on Ant, n = 5 on Humanoid.
  — [Tang 2020](https://arxiv.org/abs/2006.07442)
- **SILfD (AAAI 2022).** Names two over-estimation causes: (1) return variance in stochastic settings makes the critic estimate "the highest rather than the expected return", "partially mitigated by using generalized SIL with n-step update (Tang 2020)"; (2) shared parameters spill V(s₁) increases into V(s₂). It uses demonstrations, so the method itself is out of scope; only the critique is used here. — [Pshikhachev et al. 2022](https://arxiv.org/abs/2203.10905)
- **SAIL, Self-Imitation Advantage Learning (Ferret, Pietquin, Geist, AAMAS 2021).**
  - Off-policy SIL for DQN and IQN through a modified reward: r̃ = r + α · (max(G_t, Q_target(s,a)) − max_b Q_target(s,b)). This combines advantage learning (action-gap increasing) with self-imitation.
  - Stale returns: old returns "drift towards pessimism", so it takes "the most optimistic return estimate between the observed return and the current action-value".
  - It replaces SIL's ReLU with the identity, "using information from both positive and negative experiences".
  - "Compared to SIL, we do not make use of prioritization, as we think it emphasizes the impact of stochasticity."
  — [Ferret et al. 2021](https://arxiv.org/abs/2012.11989)
- **SAIL results**, on ALE with sticky actions (p = 0.25), Dopamine hyperparameters, 200M frames:
  - SAIL-DQN on hard-exploration games: +654.3% average and +71.8% median relative improvement over DQN.
  - SAIL-IQN vs Rainbow: +80.3% average and +4% median.
  - Montezuma: SAIL-IQN 833 final vs RND-IQN 161 vs IQN 0. 5180 with RND and 3-step returns.
  - Straightforward SIL (ReLU, raw return): SAIL beats it by +72.2% average and +45.2% median (DQN, hard games).
  — [Ferret et al. 2021](https://arxiv.org/abs/2012.11989)
- **SAIL under stochasticity (§4.5).**
  - Turning sticky actions off ("near-deterministic") raised SAIL's average relative gain over DQN from +101.4% to +231.6%, and the median from +6.7% to +12.7%. The gain roughly halves under p = 0.25 stochasticity.
  - At p = 0.5 and 0.75, SAIL-DQN's human-normalised median fell, though it stayed above DQN at standard p = 0.25. The authors leave separating "the impact of stochasticity on SAIL from the general performance loss" to future work.
  — [Ferret et al. 2021](https://arxiv.org/abs/2012.11989)
- **Top-k self-imitation (Gangwani, Liu, Peng, ICLR 2019).**
  - Keeps a priority queue of the top-k trajectories and imitates them (Jensen-Shannon / occupancy matching).
  - Stated failure: "stochasticity in the environment may make it difficult to recover the optimal policy just by imitating the past top-k rollouts. For instance, in a 2-armed bandit problem with reward distributions Bernoulli(p) and Bernoulli(p+ε), rollouts from both the arms get conflated in M_E".
  - The fix is an ensemble of diverse self-imitating agents (Stein variational policy gradient), which "increases the probability of the optimal policy being present in the final trained ensemble" (selection, not de-noising).
  - Gains are largest with episodic, end-of-episode rewards. Walker 2996 vs PPO 252 and Hopper 2618 vs 354 at 5M steps, as I read a column-garbled table; verify before quoting. Dense rewards were roughly at parity.
  — [Gangwani et al. 2019](https://arxiv.org/abs/1805.10309)
- **DTSIL (Guo et al.).** "Existing methods may overly exploit past successful experiences, which can encourage the agent to adopt sub-optimal and myopic behaviors". PPO+SIL got stuck collecting two apples in Apple-Key-Door-Treasure. Their trajectory-conditioned policy adds a modified demonstration selection "in highly stochastic environments" (§5.2). — [Guo et al. 2019/2020](https://arxiv.org/abs/1907.10247). The NeurIPS 2020 venue is from memory.
- **"You Can't Count on Luck", ESPER (Paster, McIlraith, Ba, NeurIPS 2022).** This is the cleanest formal critique of imitating good outcomes.
  - "Trajectories that result in a return may have only achieved that return due to luck."
  - **Theorem 2.1.** A goal z is consistently achievable by an RvS policy iff p(s_t | history) = p(s_t | history, I(τ) = z). The conditioning statistic must be independent of environment stochasticity.
  - **Gambling example.** Cloning trajectories with r = 1 gives expected return −2.5 · 1/3 + 1 · 2/3 = −0.17, "no matter how much data".
  - **Fix: ESPER.** Cluster trajectories adversarially so that cluster membership predicts no stochastic outcomes, then condition on the cluster's average return.
  - **Results** (max performance):

    | Task | Return-conditioned DT | CQL | ESPER |
    |---|---|---|---|
    | Gambling | −0.02 (0.24) | 1.0 | 1.0 |
    | Connect Four vs a stochastic opponent | 0.80 | 0.61 | 0.99 |
    | 2048 | 0.57 | 0.70 | 0.81 |

  — [Paster et al. 2022](https://arxiv.org/abs/2205.15967)
- **Dichotomy of Control (Yang, Schuurmans, Abbeel, Nachum, ICLR 2023).**
  - Return-conditioning fails "where an occasional high return can arise from randomness in the environment rather than the actions themselves".
  - DoC conditions on a latent future z, with a mutual-information constraint MI(r_t, s_{t+1}; z | history) = 0 that removes environment randomness.
  - Theorem 4: the policy is consistent with its conditioning input.
  - I did not extract numbers.
  — [Yang et al. 2022](https://arxiv.org/abs/2210.13435)
- **Counterfactual Credit Assignment, CCA (Mesnard et al., ICML 2021).** Aims at "separating skill from luck".
  - Future-conditional baselines and critics use hindsight statistics Φ_t. These are unbiased if Φ_t is independent of A_t (P(a | X_t, Φ_t) = π(a | X_t)) and "provably low variance".
  - **Handcrafted Φ examples** include exogenous factors, other agents' simultaneous actions, the simulator's full state, and "the opponent's private observations (at time t) in Starcraft II (Vinyals et al., 2019)".
  - **Contextual bandit with exogenous reward noise:** vanilla PG performance falls "dramatically" as noise rises, while CCA-PG is "generally unaffected" (6 runs).
  - **Caveat:** at very low noise CCA loses performance when Φ leaks action information, so it "attributes part of the reward to chance"; weakening the independence loss degrades it "dramatically".
  — [Mesnard et al. 2021](https://arxiv.org/abs/2011.09464)
- **Model-free episodic control (Blundell et al. 2016).**
  - Stores the max return per (s, a): Q_EC ← max(Q_EC, R_t). "Since the stored value can never decrease, it is not suited to rational action selection in stochastic environments"; acting on it "would yield a strong risk seeking behaviour".
  - Storing R_t without the max "performed worse in preliminary experiments", on deterministic Atari.
  — [Blundell et al. 2016](https://arxiv.org/abs/1606.04460)
- **Significance-gated or paired-return SIL.** I found no SIL variant that imitates only when R − V is statistically significant, or that uses paired or averaged returns per (s, a). Searches for "self-imitation stochastic / noisy rewards / overestimation correction" returned only the papers above. — [search results, see Tang/SAIL/Gangwani links above]

### Inferences
- The literature's de-noising levers come in three groups:
  1. Replace one return with an average: Tang's n-step bootstrap, ESPER's cluster average, a value target.
  2. Constrain what the policy conditions on, or credits against, to be independent of chance: DoC, CCA, ESPER.
  3. Remove the amplifiers of luck: SAIL drops prioritisation and uses both signs.
- A paired or significance-gated SIL looks unpublished. In a simulator that can replay a decision, it is straightforward: imitate a only if mean_j[R_j(a) − R_j(b)] > z · SE (see Q4).
- Tang's "safe upper bound by Q*" does not protect us. It holds for the expected operator; with single sampled ±1 outcomes the sample-based update can push V toward +1 wherever a win was ever seen.
- SAIL's evidence that stochasticity halves the gain comes from sticky actions (p = 0.25), a much milder noise than one win/loss per game with a 0.02 gap. I expect the SIL-family gain to shrink further in our setting (estimate, not measured).

### Gaps
- No quantitative bias-vs-variance curve for SIL exists (bias as a function of return sd).
- No SIL study on two-player zero-sum self-play, where the opponent's past strength is another luck source in replay.
- I did not extract DoC's numeric results or CCA's Key-to-Door numbers.

---

## Q3. Related amplification methods that use only the agent's own data

### Takeaway
Most "amplify your own good outcomes" methods either assume near-determinism (episodic control, top-k imitation, Go-Explore phase 1) or weight imitation by a single noisy return (return-conditioned RL, RWR/AWR, best-of-k). They inherit SIL's luck bias, and exponential weighting worsens it. The exceptions get variance reduction because their target averages many simulated continuations from the same state:
- AlphaZero/ExIt search targets;
- UPGO, which filters only the agent's own later actions, not chance;
- VinePPO / TRPO-vine Monte Carlo advantages.

### Cited Findings
- **UPGO, AlphaStar's "upgoing policy gradient".**
  - Implementation (DI-engine): "UPGO can be viewed as a lambda return! The trace continues for V_t (i.e. lambda = 1.0) if r_tp1 + V_tp2 > V_tp1"; code `lambdas = (rewards + bootstrap_values[1:]) >= bootstrap_values[:-1]`; loss uses `advantages = rhos * (returns - bootstrap_values[:-1])`.
  - The advantage at the current step is not clipped at 0. Optimism applies only to the continuation: if the next action looks worse than V, the return is replaced by V.
  — [DI-engine upgo.py](https://github.com/opendilab/DI-engine/blob/main/ding/rl_utils/upgo.py)
  - Scheller et al. describe UPGO as "closely related to self-imitation learning (Oh et al., 2018)… Both methods restrict updates to only better-than-average trajectories". This contrasts somewhat with the code's unclipped advantage. — [Scheller et al. 2020](https://arxiv.org/abs/2003.06066)
  - (From memory) The AlphaStar Nature paper (Vinyals et al. 2019) defines G_t^U = r_t + G_{t+1}^U if Q(s_{t+1}, a_{t+1}) ≥ V(s_{t+1}), else r_t + V(s_{t+1}). It was used with V-trace and TD(λ) in a stochastic, imperfect-information self-play game.
- **Return-conditioned / upside-down RL (RvS, Decision Transformer).** These fail in stochastic environments for the reasons in Q2 (ESPER, DoC). Theorem 2.1 says conditioning on the achieved return is only consistent when the return is independent of environment randomness. — [Paster et al. 2022](https://arxiv.org/abs/2205.15967); [Yang et al. 2022](https://arxiv.org/abs/2210.13435)
- **Episodic control (MFEC / NEC).**
  - Replays the action with the highest return ever seen; risk-seeking in stochastic environments by the authors' own statement.
  - The SIL paper notes these "may generalize poorly as the resulting policy is non-parametric" and are slow at test time.
  — [Blundell et al. 2016](https://arxiv.org/abs/1606.04460); [Oh et al. 2018](https://arxiv.org/abs/1806.05635)
- **Never Give Up (Badia et al., ICLR 2020).** An exploration method: an episodic-memory, k-nearest-neighbour novelty bonus that trains "directed exploratory policies", encouraging the agent to revisit states repeatedly. It does not amplify good outcomes, so it is relevant only for getting rare decision states visited more. — [Badia et al. 2020](https://arxiv.org/abs/2002.06038) (abstract only)
- **Go-Explore (Ecoffet et al.).**
  - Phase 1 explores using determinism and simulator restore ("by any available means (including by introducing determinism)").
  - Phase 2 "robustifies" high-performing archived trajectories by imitation (the backward algorithm), "to be robust to the stochastic dynamics of the true environment" with sticky actions.
  - "Return to a saved state" is the same simulator affordance as replaying a decision.
  — [Ecoffet et al. 2019](https://arxiv.org/abs/1901.10995)
- **Reward- and advantage-weighted regression (RWR, AWR).**
  - Fits π_{k+1} by maximum likelihood on the agent's own samples "weighted by the exponentiated return received for that action, with a temperature parameter β". AWR uses the advantage R − V instead of the return.
  - AWR's expected-improvement derivation uses A^μ(s, a) = R^μ_{s,a} − V^μ(s), the expected return.
  — [Peng et al. 2019](https://arxiv.org/abs/1910.00177)
- **Best-of-k / top-k self-imitation.** The Bernoulli(p) vs Bernoulli(p + ε) conflation shown in Q2. — [Gangwani et al. 2019](https://arxiv.org/abs/1805.10309)
- **AlphaZero-style improvement targets (general mechanism only), Expert Iteration (Anthony et al., NeurIPS 2017).**
  - The apprentice network imitates the expert's (MCTS's) output.
  - "Chosen-action targets" (CAT, −log π(a*|s)) are compared with "tree-policy targets" (TPT, the visit-count distribution n(s,a)/n(s)). "Unlike CAT, TPT is cost-sensitive" when search is uncertain between moves.
  - "EXIT outperforms REINFORCE for training a neural network to play the board game Hex".
  - The target is built from many simulations from the same state, not from one game outcome.
  — [Anthony et al. 2017](https://arxiv.org/abs/1705.08439)
- **VinePPO (Kazemnejad et al.).**
  - Replaces PPO's value network with Monte Carlo value estimates from K extra rollouts from intermediate states. Value networks "barely outperform[] a random chance in ranking candidate steps".
  - Reaches baseline peak "in less wall-clock time (up to 3.0x)", despite slower iterations (up to 2x for 7B, 5x for 1.1B).
  - Larger K helped, per my reading plus a secondary summary.
  — [Kazemnejad et al. 2024](https://arxiv.org/abs/2410.01679)

### Inferences
- **UPGO is the closest relative actually used in stochastic self-play.**
  - Its filtering removes variance caused by the agent's own later bad actions. It does not remove card-draw or hidden-card luck, which is exactly our noise.
  - It does not clip the current-step advantage, so it is less luck-amplifying than SIL's (R − V)₊ with win-prioritised replay.
- **Exponential advantage weights make the luck problem worse.** AWR/RWR weight by exp(A/β) with a noisy A; since the exponential is convex, they amplify lucky samples more than SIL's ReLU does (estimate; no paper found measuring this).
- **Best-of-k selection on noisy evaluations has a winner's curse** (standard order statistics, from memory). The expected maximum of k standard normals is about 1.16σ for k = 5 and 1.54σ for k = 10. With per-game sd 1 and 100 games per candidate, the best of 5 is inflated by about 0.12, six times the 0.02 gap. A best-of-k self-play selector would pick lucky candidates unless each gets thousands of games or paired deals.
- **Search-based targets (ExIt/AlphaZero) and Monte Carlo advantages (VinePPO, TRPO vine) are the only members of this family whose improvement signal is an average over many continuations from one state.** Only these can resolve a 0.02 gap without tens of thousands of games. In hidden-information games they need re-dealing (determinisation), and per-move search targets are covered elsewhere.
- **Project context.** The project's search notes already flag that independent re-deals per option make "much of search's 50-54% departure… deal luck". CRN in search is a queued candidate. — `metagame-rl/notes/data/cycle1/candidates.json` (about lines 172-211); `metagame-rl/notes/design-action-sequence-search.md` (line 11)

### Gaps
- I did not verify the AlphaStar Nature UPGO equation directly (paywalled), nor any ablation of UPGO's contribution.
- No ESPER/DoC-style method has been tested in self-play or two-player card games, apart from Connect Four against a fixed stochastic opponent.
- NGU was read as an abstract only.

---

## Q4. Which methods could use the simulator's re-deal and CRN replay, so that a "good outcome" is a paired comparison?

### Takeaway
Paired replay with common random numbers (CRN) is a documented variance-reduction tool. It appears in TRPO's "vine" procedure (rollouts for every action from the same state, using the same random numbers) and in PEGASUS (fix the random "scenarios" so that any POMDP becomes deterministic). CCA's hindsight baselines and ESPER's averaging are the learned analogues. Each of SIL, UPGO, ExIt-style targets and ESPER can be made to use paired replays. The gain depends on how often the choice actually flips the game. My estimate is 5-50x fewer games for a 0.02 gap; this is unmeasured and needs a pilot.

### Cited Findings
- **TRPO "vine".**
  - From a rollout-set state, estimate Q̂(s_n, a_{n,k}) by rollouts for K actions: "We can greatly reduce the variance of the Q-value differences between rollouts by using the same random number sequence for the noise in each of the K rollouts, i.e., common random numbers."
  - "In small, finite action spaces, we can generate a rollout for every possible action from a given state."
  - Vine "gives much better estimates of the advantage values", at the cost of "far more calls to the simulator".
  — [Schulman et al. 2015](https://arxiv.org/abs/1502.05477)
- **PEGASUS (Ng & Jordan, UAI 2000).**
  - With a "deterministic simulative model" (the simulator takes its random numbers as input), "any (PO)MDP can be transformed into an 'equivalent' POMDP in which all state transitions… are deterministic".
  - Policy search then compares policies on the same fixed scenarios.
  - Sample-complexity bounds have "only a polynomial rather than exponential dependence on the horizon time".
  — [Ng & Jordan 2000](https://arxiv.org/abs/1301.3878)
- **CCA.** Baselines may include action-independent hindsight information such as "the full state… of the simulator" or the opponent's private observations, and stay unbiased as long as that information is independent of A_t. — [Mesnard et al. 2021](https://arxiv.org/abs/2011.09464)
- **ESPER.** Conditions on the average return of trajectories that differ only in environment transitions. This is a learned stand-in for averaging over re-deals. — [Paster et al. 2022](https://arxiv.org/abs/2205.15967)
- **Go-Explore** restores saved simulator states to return to promising states before exploring. — [Ecoffet et al. 2019](https://arxiv.org/abs/1901.10995)
- **VinePPO** Monte Carlo values from re-fed intermediate states. I did not see CRN in what I read. — [Kazemnejad et al. 2024](https://arxiv.org/abs/2410.01679)
- **Project context.**
  - A prior project round found that "a critic that sees hidden information gave only a small gain in Dou Dizhu (PerfectDou, about +0.09 ADP), so it was not queued" — `metagame-rl/notes/progress-log.md` (about line 6992).
  - C90 (paired selection with CRN for the draft) is already proposed — `metagame-rl/notes/audits.md` (about line 599).

### Inferences
All numbers below are estimates, not measurements.

**1. Paired-outcome arithmetic** (win/loss coded ±1, true gap δ = 0.02):
- Let q be the share of re-deals where options A and B lead to different results. The paired difference D = R_A − R_B is in {−2, 0, +2}, with Var(D) ≈ 4q, and q ≥ δ/2 = 0.01.
- Pairs needed for z = 2: n ≈ 4 · 4q / δ² = 40,000 · q.

| q (share of deals the choice flips) | Pairs needed | Games | vs about 40,000 unpaired games |
|---|---|---|---|
| 0.10 | 4,000 | 8,000 | 5x fewer |
| 0.05 | 2,000 | 4,000 | 10x fewer |
| 0.01 (minimum) | 400 | 800 | 50x fewer |

- q is unknown. A pilot of about 200 paired replays at real Computer Search states would measure it.

**2. Keeping the pair correlated.** CRN only helps while the two branches share their randomness after the choice.
- Seed (i) the hidden-card re-deal, (ii) every later shuffle and draw, and (iii) both agents' action-sampling RNG, all identically across branches.
- Computer Search and Item Finder change the deck's contents, and a seeded shuffle of a different multiset gives a completely different order. Use a key-based shuffle: each card instance gets a seeded random key and the deck is sorted by key, so adding or removing one card leaves the others' relative order unchanged. Otherwise correlation collapses and q approaches the unpaired case.
- The project's search notes already record the related problem that "later shuffles follow the actions taken" (`metagame-rl/notes/design-action-sequence-search.md`, line 11).

**3. Method-by-method fit:**
- **SIL → "paired SIL" (unpublished as far as I found).** At a sampled rare decision, branch over the candidates (all fetch targets, or 2-4 sampled ones) with K CRN re-deals each. Imitate the best candidate only if its mean paired advantage exceeds z · SE; otherwise make no update. This keeps SIL's "amplify my own good decisions" while making "good" a paired, significance-tested comparison. It uses no human data or oracle: the rollouts are the agent's own policy.
- **TRPO-vine / VinePPO-style advantages for PPO** (closest published recipe). Use Â(s, a_k) = mean_j[R_j(a_k) − mean_k' R_j(a_k')] as the PPO advantage for that one decision type, and keep GAE elsewhere. This spends simulator compute only at the rare decisions where PPO's credit is weakest (A90's 20-40x shortfall).
- **ExIt-style cost-sensitive targets.** A softmax over paired Q̂(s, a_k) acts as a "tree-policy target" for the fetch head: smoother than imitating the arg-max, and robust when options are nearly tied. This is a one-step version of search targets, which are covered in more depth elsewhere.
- **PEGASUS-style paired selection.** For selecting among k candidate policies, decks or heads, evaluate all candidates on the same seeded deals. This shrinks the winner's curse from Q3 for the same reason. It is what C90 proposes for drafting.
- **CCA / privileged baseline, cheapest because it needs no extra rollouts.**
  - Train a value baseline that also sees the hidden state at decision time: prizes, deck order and the opponent's hand before the choice. That information is independent of the action given the agent's information set, so the policy gradient stays unbiased.
  - It removes the luck already fixed at decision time, but not the luck of later draws.
  - The prior project note (PerfectDou +0.09 ADP) suggests the gain may be small. This is a value baseline trained on the agent's own outcomes, not oracle action labels, but check it against the "never train on oracle answers" rule before use.
- **UPGO.** Adds nothing for chance noise. Combining it with paired replays is redundant.
- **ESPER / DoC.** With an exact re-deal simulator, the clustering and mutual-information machinery is unnecessary. Averaging over re-deals estimates E[R | s, a] directly, which is what ESPER approximates.
- **Episodic control, top-k / best-of-k imitation and RWR/AWR on single returns.** Not recommended for a 0.02 gap unless their "return" is replaced by a paired, averaged estimate, after which they reduce to the vine/ExIt variants above.

### Gaps
- No published SIL variant uses paired or CRN returns, or a significance gate. "Paired SIL" is a proposal, not evidence.
- No published card-game (TCG) study measures q, the discordance rate of paired replays, or how fast CRN correlation decays after a deck-changing choice.
- AIVAT/DIVAT-style poker variance reduction (Burch et al., from memory) and group-relative or leave-one-out baselines (GRPO/RLOO, from memory) are related but were not verified in this session.
