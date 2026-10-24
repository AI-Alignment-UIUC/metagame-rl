# Learning tactical play in long-horizon imperfect-information card games: search plus learning, credit assignment, and why search distillation fails (F4)

Scope note. These notes cover search in imperfect-information games, distilling few-simulation search into a policy, long-horizon credit assignment in PPO self-play, card-game agents trained without human data, and the cheapest fix for F4. Each finding is tagged with the failure modes it bears on (F1-F6 as defined in the task). The project-side facts are taken from the repo, read-only: `rl/train.py`, which has `--gamma` default 1.0, `--lam` default 0.95, `--lam-value`, `lam_turn`, potential-based prize shaping `shape_rewards`, and the aux heads "decisions left" and "result". They also come from `notes/progress-log.md` #96, which describes the expert-iteration design that failed.

How the earlier expert iteration was built (from progress-log #96). This matters for reading the findings below.
- It searched one turn ahead. A share of recorded main-phase decisions were "probed", taking all options up to `maxOptions`, or else the option played plus a random sample. Each option was played for `lines` copies (2 or 4), re-dealt for the deciding player, greedily to the end of the turn. Each line was scored by the game result, or by the pilot's value after the turn plus `prizeWeight` times the prizes taken.
- The best option became a hard one-hot target, but only where the options' scores differed by more than a margin. The target was added as b × cross-entropy, with b = 0.3 or 1.0, on 10-25% of decisions.
- Before the first step, agreement with the search was 35% and the pre-clip gradient norm was 27, so with weight 1 the distillation term made up most of each update ([progress-log #96](file:///C:/Users/evanc/Desktop/333/metagame-rl/notes/progress-log.md)).

---

## Q1. Search in imperfect-information games: PIMC/determinization and strategy fusion, ISMCTS, ReBeL, Student of Games, DeepNash, Pluribus, SPARTA. Which are affordable on one GPU?

### Takeaway
The methods with game-theoretic guarantees (ReBeL, Student of Games) are far beyond one desktop's compute. Cheap determinized or flat Monte Carlo search is unsound in theory but strong in practice. SPARTA in particular uses rollouts from a blueprint policy and deviates from the blueprint only when the gain clears a threshold. That is the affordable family, and the project's one-turn search already belongs to it. The single most transferable trick is SPARTA's: deviate from the policy only when search is confidently better, and stop spending rollouts on options that are statistically out of the running.

### Cited Findings
- **PIMC is unsound but often works.** Long, Sturtevant, Buro and Furtak (AAAI 2010, pp. 134-140) used synthetic game trees to find which game properties make Perfect Information Monte Carlo sampling strong or weak against an optimal player. They report that these properties predict PIMC's strength in real games ([Long et al. 2010](https://ojs.aaai.org/index.php/AAAI/article/view/7562)). The two classical PIMC errors are "strategy fusion" and "non-locality", and the αμ algorithm for Bridge was designed to remove both ([Cazenave et al., αμ](https://arxiv.org/pdf/2408.02380); [Sturtevant lecture](https://www.cs.du.edu/~sturtevant/w13-games/Lecture10.pdf)). [F4]
- **Determinization has no convergence guarantee.** The Student of Games authors write that determinization (sampling candidate world states, then searching) "has been quite successful in practice" and was state of the art in Scotland Yard (PimBot). However, these methods "are not guaranteed to converge to an optimal strategy over time", and the authors show non-convergence empirically in their supplement ([Schmid et al. 2023, Student of Games](https://arxiv.org/abs/2112.03178)). [F4]
- **There is a Magic: The Gathering precedent.** Cowling, Ward and Powley (IEEE TCIAIG 4(4):241-257, 2012) applied ensemble determinization MCTS to MTG, which has hidden opponent cards and random draws. Their changes were varied rollout strategies, pruning, and breaking move generation into a binary yes/no decision tree that MCTS searches at a finer grain. Each gave significant strength gains over basic determinized MCTS with fixed decks ([Cowling, Ward & Powley 2012](https://eprints.whiterose.ac.uk/75050/)). A card-game AI survey reports that this agent outperformed an expert-level rule-based player ([Jass survey, arXiv 1906.04439](https://arxiv.org/pdf/1906.04439)). [F4; carries to MTG]
- **ISMCTS** (Cowling, Powley and Whitehouse, IEEE TCIAIG 2012) searches trees of information sets rather than of determinized states, to reduce strategy fusion. This is cited from memory of the paper and was not re-read this session ([Cowling, Powley & Whitehouse 2012](https://doi.org/10.1109/TCIAIG.2012.2200894)). [F4]
- **ReBeL is sound but very expensive.** It combines RL with depth-limited search over public belief states, and Brown, Bakhtin, Lerer and Gong (NeurIPS 2020) prove it computes an approximate Nash equilibrium. Data generation was the bottleneck: the authors used "a single machine for training and up to 128 machines with 8 GPUs each", and for full heads-up no-limit hold'em "90 DGX-1 machines, each with 8 × 32GB Nvidia V100 GPUs for data generation" ([Brown et al. 2020, ReBeL](https://arxiv.org/abs/2007.13544)). [Not affordable]
- **Student of Games is sound but expensive.** Schmid et al. (Science Advances 2023) use growing-tree CFR search with "sound self-play". Their AlphaZero comparison used "3500 concurrent actors each on a single TPUv4", and SoG "was trained using a similar amount of TPU resources". In Scotland Yard, SoG trained for 17M steps and searching with (400, 1) beat the determinization-MCTS PimBot. Even against PimBot with 10M simulations it won 55% ([Schmid et al. 2023](https://arxiv.org/abs/2112.03178)). [Not affordable; shows a learned value plus small search beating large determinized search]
- **DeepNash uses no search.** Perolat et al. (Science 2022) mastered Stratego with "model-free RL ... without search", using Regularized Nash Dynamics (R-NaD). R-NaD transforms the reward with a term −η log(π/π_reg) and repeatedly replaces the regularization policy π_reg with the fixed point just reached. DeepNash beat existing Stratego bots more than 97% of the time and reached top-3 on Gravon with an 84% win rate against human experts ([Perolat et al. 2022](https://arxiv.org/abs/2206.15378)). [F1, F2, F3]
- **DeepNash needed a fix for low-probability mistakes.** Training alone gave a policy "slightly distorted by low-probability mistakes" because softmax gives every action some probability. The fix was fine-tuning with thresholding and discretization of action probabilities, plus test-time post-processing "to filter out low probability actions and clear mistakes" ([Perolat et al. 2022](https://arxiv.org/abs/2206.15378)). [F4]
- **Pluribus was cheap on CPUs.** Brown and Sandholm (Science 2019) computed its blueprint "in 8 days on a 64-core server for a total of 12,400 CPU core hours ... less than 512 GB of memory ... about $144", and it played in real time on 2 CPUs. These figures come from the authors' AMA as quoted there, not from the paper, so they are secondary. The savings are attributed to action and information abstraction plus Linear Monte Carlo CFR ([Pluribus AMA thread](https://reddit.rtrace.io/r/MachineLearning/comments/ceece3/ama_we_are_noam_brown_and_tuomas_sandholm/eu7b5e3/?context=3); [Wikipedia](https://en.wikipedia.org/wiki/Pluribus_(poker_bot))). [Cheap, but relies on poker-specific abstraction]
- **SPARTA: blueprint search with a deviation threshold.** Lerer, Hu, Foerster and Brown (AAAI 2020) run Monte Carlo rollouts from a blueprint policy and reach 24.61/25 in 2-player Hanabi, against a previous best of 24.08. Two details are directly relevant here ([Lerer et al. 2020, SPARTA](https://arxiv.org/abs/1912.02318)):
  - An action whose expected value is not within 2 standard deviations of the best action gets no further rollouts (UCB-like pruning).
  - "If the expected value of the action chosen by search does not exceed the value of the blueprint action by more than this threshold, the agent plays the blueprint action. We use a threshold of 0.05." The authors note that the 0.05 threshold "improves the total score even for a large number of rollouts", and that UCB pruning reduces rollouts per turn "without affecting the average score".

  [F4]
- **Learned Belief Search is a cheaper SPARTA.** Hu, Lerer, Brown and Foerster (2021) replace exact beliefs with a learned autoregressive belief model. LBS "obtains 55% to 91% of the benefit of exact search while reducing compute requirements by 35.8× to 4.6×" ([Hu et al. 2021, LBS](https://arxiv.org/abs/2106.09086)). [F4]

### Inferences
- **What kind of search the project runs, and its real weakness.** The one-turn search re-deals hidden cards and then plays greedy lines with the pilot. The pilot sees only its own observation, so inside a line it cannot exploit the sampled hidden cards. Strategy fusion is therefore confined to the single root comparison. The search is flat Monte Carlo with a policy continuation, i.e. SPARTA-style single-agent search with a one-turn depth limit and a learned value at the leaf. On this reading the dominant error is not strategy fusion but noise: 2-4 lines per option. The leaf value is also suspect, because it comes from the co-adapted pilot (F2) (my inference).
- **Which methods fit one RTX 5070 Ti.** The affordable ones are flat or one-turn determinized search (already built), ensemble determinization MCTS with a binary move decomposition (Cowling et al. for MTG), ISMCTS, and SPARTA/LBS-style blueprint search. ReBeL and SoG need hundreds of GPUs or TPUs and are out of reach. DeepNash's R-NaD needs no search and is affordable in principle, though its training compute was not found in the text I read (my inference).
- **SPARTA's threshold rule fits F4 directly.** It says the right default is the policy's own action, overridden only when search beats it by a margin measured against the noise. The project has a fixed margin on score differences. SPARTA's version adds a 2-SD pruning rule and compares the search pick against the policy's own choice, not against the second-best option (my inference).
- **R-NaD looks like a principled form of the KL anchor already tried.** The anchor made the pilot about 65 Elo better on the human lists. R-NaD would regularize toward a reference policy and move that reference only to the reached fixed point. Applied to the draft heads as well, it could counter entropy collapse (F3) without fixing the reference forever (my inference).

### Gaps
- DeepNash's training hardware (TPU counts, days) was not in the extracted text, so its affordability is unverified.
- I did not find a published Pokémon TCG or MTG agent that combines learned value with sound imperfect-information search. The only PTCG RL item found is a Kaggle hobby agent (Q4).
- Long et al.'s three PIMC-predictive properties (leaf correlation, bias, disambiguation factor) are from my memory of the paper; only the abstract was confirmed this session.

---

## Q2. Expert iteration and AlphaZero-style distillation with few simulations: guarantees, failure modes when values are weak or targets noisy, and remedies

### Takeaway
The literature names the exact failure the project hit. Training a policy toward the argmax or visit counts of a few-simulation search gives no policy improvement and can make the policy worse. The fixes all have the same form: a soft, KL-regularized target built from Q-value advantages. Gumbel MuZero's completed-Q target and Muesli's clipped MPO are examples. Unvisited or uncertain actions keep the prior's probability, so the size of the update is bounded. Policy-target pruning and spending search budget on fewer, deeper probes (KataGo) also help. The project's hard one-hot target from 2-4 noisy lines, applied at weight up to 1 with a gradient norm of 27, is the configuration these papers warn against.

### Cited Findings
- **Gumbel MuZero: the failure mode and the guarantee.** Danihelka, Guez, Schrittwieser and Silver (ICLR 2022) state that "AlphaZero can fail to improve its policy network, if not visiting all actions at the root of a search tree" ([Danihelka et al. 2022](https://openreview.net/forum?id=bERaNdoegnO); text read via [this mirror](https://object.cloud.sdsc.edu/v1/AUTH_da4962d3368042ac8337e2dfdd3e7bf3/ml-papers-txt/ICLR/2022/policy_improvement_by_planning_with_gumbel__15d5fc26.txt)). [F4]
  - Their Example 1 has q = (0, 0, 1) and π = (0.5, 0.3, 0.2), so the policy's value is 0.2. With n = 2, taking the best of the two most probable actions has expected value 0, which is worse than the policy.
  - Gumbel-Top-k sampling without replacement, followed by sequential halving that reuses the same Gumbel noise in the final argmax, "guarantees a policy improvement when action-values are correctly evaluated".
- **Gumbel MuZero: completed-Q target.** The policy target is π' = softmax(logits + σ(completedQ)), with σ(q̂) = (c_visit + max_b N(b)) · c_scale · q̂. Go and chess use c_visit = 50 and c_scale = 1.0; Atari uses c_scale = 0.1 ([Danihelka et al. 2022](https://openreview.net/forum?id=bERaNdoegnO)). [F4]
  - Unvisited actions get a value estimate v_mix in place of a Q-value. v_mix interpolates between the value network and the π-weighted Q of visited actions, so completed Q "give[s] zero advantage to the unvisited actions".
  - Without completed Q-values, TRPO- and MPO-style MuZero variants "would fail to produce a policy improvement".
  - If c_scale is large, the method "focuses on q̂(a) and neglects the logits", which hurt performance on partially observable beam_rider.
- **Gumbel MuZero: results.** On 9x9 Go, "Gumbel MuZero learns reliably even with 2 simulations", while "MuZero fails to learn from 16 or less simulations". On Atari ms_pacman, MuZero fails at 4 or fewer simulations while Gumbel MuZero learns with 2. Training-step speedups against MuZero with n = 200 were 5.9× (n = 32), 11.3× (n = 16) and 24.3× (n = 4) ([Danihelka et al. 2022](https://openreview.net/forum?id=bERaNdoegnO)). An independent reimplementation (MiniZero) reports that Gumbel Zero performs well "with as low as only two simulations" ([Wu et al., MiniZero](https://arxiv.org/abs/2310.11305)). [F4]
- **Grill et al.: MCTS as regularized policy optimization.** Grill, Altché, Tang, Hubert, Valko, Antonoglou and Munos (ICML 2020) show that AlphaZero's visit distribution approximates the solution π̄ = argmax_y [qᵀy − λ_N KL(π_θ, y)]. The regularization weakens as simulations increase ([Grill et al. 2020](https://arxiv.org/abs/2007.12509)). [F4]
  - They list three reasons visit counts are poor targets at low budgets. (1) A newly found high-value action needs many more simulations before it shows in the visit counts. (2) Visit counts are a ratio of small integers, so they can express little. (3) The target improves only for actions sampled at least once.
  - On Ms Pacman with |A| ≈ 18, using π̄ (variant "ALL") "significantly outperforms MuZero" at Nsim = 5, in both learning speed and final score. The two become comparable only at Nsim ≈ 24 or more.
  - At Nsim = 5, "the main improvement comes from using the policy optimization solution π̄ as the learning target (LEARN)". Using it in search or acting adds only a marginal improvement.
- **Muesli: clipped MPO.** Hessel et al. (ICML 2021) define a target π_CMPO(a|s) ∝ π_prior(a|s) · exp(clip(adv(s,a), −c, c)) and regularize the policy toward it. They prove the total-variation distance between the target and the prior is at most tanh(c/2), so a noisy advantage estimate cannot move the policy far. Muesli "matches MuZero's state-of-the-art performance on Atari ... without using deep search", acting directly with the policy network at about model-free cost ([Hessel et al. 2021](https://arxiv.org/abs/2104.06159)). [F4]
- **KataGo: playout cap randomization.** Wu (2019) reports that "unless the number of playouts is larger than ideal for value training, the search usually does not deviate much from the policy prior, so the policy does not readily improve" ([Wu 2019, KataGo](https://arxiv.org/abs/1902.10565)). [F4]
  - The fix: on a fraction p of turns, run a full search with cap N; on all other turns, run a fast search with n < N and no exploration noise. "Only turns with a full search are recorded for training." The main run used p = 0.25 and (N, n) = (600, 100), annealed to (1000, 200).
  - This beat every fixed cap tried (100, 150, 200, 250, 600).
- **KataGo: policy-target pruning.** Playouts forced only by exploration noise are subtracted from non-best children before the visit counts become a policy target. This "allows decoupling the policy target in AlphaZero from" the exploration used in search, and gave "smaller but clear gains" ([Wu 2019](https://arxiv.org/abs/1902.10565)). [F4]
- **KataGo: total gain and compute.** The product of the measured acceleration factors was about 9.1×. Overall, KataGo surpassed ELF OpenGo after 19 days on at most 28 V100 GPUs, about a 50× reduction in compute ([Wu 2019](https://arxiv.org/abs/1902.10565)).
- **Soemers et al.: what policies inherit from visit-count targets.** Soemers, Piette, Stephenson and Browne (IEEE CoG 2019) observe that policies trained by cross-entropy toward MCTS visit counts are "likely to exhibit a similar extent of exploration". They instead derive a policy gradient estimated from MCTS value estimates rather than visit counts ([Soemers et al. 2019](https://arxiv.org/abs/1905.05809)). [F4: links to the rise in policy entropy]
- **Hamrick et al.: where planning helps.** Hamrick et al. (ICLR 2021) ablated MuZero on control tasks, Atari and 9x9 Go ([Hamrick et al. 2021](https://arxiv.org/abs/2011.04021)). Their findings:
  - "Planning is most useful in the learning process, both for policy updates and for providing a more useful data distribution."
  - "Using shallow trees with simple Monte-Carlo rollouts is as performant as more complex methods, except in the most difficult reasoning tasks."
  - "Planning alone is insufficient to drive strong generalization."

  [F4]
- **Other relevant methods, from memory.** Expert Iteration (Anthony, Tian & Barber, NeurIPS 2017) is the original apprentice/expert loop ([Anthony et al. 2017](https://arxiv.org/abs/1705.08439)). Sampled MuZero (Hubert et al., ICML 2021) extends policy improvement to search over a sampled subset of actions, with a correction for the sampling distribution ([Hubert et al. 2021](https://arxiv.org/abs/2104.06303)). Neither was re-read this session.
- **Noisy argmax is biased upward.** Choosing the maximum of noisy value estimates systematically overestimates it, the "optimizer's curse" (Smith & Winkler, Management Science 2006; from memory) ([Smith & Winkler 2006](https://doi.org/10.1287/mnsc.1050.0451)). [F4]

### Inferences
- **Why each symptom appeared.** The three expert-iteration failures (−37 to −79 Elo, 60-70% disagreement, rising entropy) match the literature point by point (my inference):
  - *The target is a hard argmax over a few noisy lines.* It ignores the prior, unlike Gumbel or CMPO, so it has the low-budget failure of Grill and Danihelka.
  - *The options are often a random sample.* This is not Gumbel-Top-k from the policy, so Example 1's failure applies. The best of a random subset, judged by noisy Q, can be worse than the policy's own pick, and the optimizer's curse inflates the chosen option.
  - *Noisy one-hot labels push toward a spread target.* With 60-70% disagreement, the labels on similar states point to different options, and cross-entropy then fits a spread-out distribution. That explains the rise in entropy, the same mechanism Soemers et al. describe for visit-count targets.
  - *The update size is unbounded.* At weight 1 with a gradient norm of 27, nothing like CMPO's TV ≤ tanh(c/2) limits how far one noisy batch moves the policy.
- **A replacement target needs no new search code.** For each probed decision, compute per-option means and standard errors from the lines. Form Â(a) = (Q̂(a) − Q̂(a_policy-mean)) / SE (my inference). Then build the target as either:
  - π_target ∝ π_prior · exp(clip(Â, −c, c)) (CMPO), or
  - softmax(logits + σ(completed Q̂)) (Gumbel), where unprobed options get v_mix, i.e. zero advantage.

  Train with KL(π_target ‖ π) at a small weight, applied only where SPARTA's test passes (best beats the policy's choice by more than k·SE). Expected effects: lower entropy, a bounded update size, and agreement near the prior's wherever the search is unsure.
- **Sample options by Gumbel-Top-k from the pilot, and use sequential halving.** Lines saved on options that are clearly worse go to the top two (SPARTA's 2-SD pruning does the same) (my inference).
- **Use KataGo's budget split.** Record fewer probes with more lines each, e.g. 8-16 lines on about 5% of decisions, rather than 2-4 lines on 10-25%. Use fast or no search elsewhere (my inference; the numbers are suggestions, not from the literature).
- **The leaf value is a separate weakness.** When lines are scored by "pilot value after the turn plus prizeWeight × prizes", the targets inherit the pilot's co-adaptation (F2). Gumbel's guarantee needs correct Q. Scoring with a frozen generalist value net (e.g. pilot-v2), or with the result of playing the line to the end of the game where affordable, would decouple the target from the drifting pilot (my inference; bears on F2/F4).

### Gaps
- I found no paper that studies expert iteration in a card game with hidden-information determinization and reports how often targets disagree with the policy. The 60-70% figure has no literature benchmark.
- I did not find exact Elo tables for Gumbel MuZero on 9x9 Go at n = 2; the paper shows them only in figures.
- Whether MPO/CMPO-style targets fix expert iteration under determinization noise (as opposed to MCTS noise) is untested in what I read.

---

## Q3. Long-horizon credit assignment in PPO self-play: return/GAE settings, value quality, auxiliary tasks, potential-based shaping, and card-game evidence

### Takeaway
Strong card agents mostly used a sparse ±1 reward with no discounting (Hearthstone γ = 1.0; DouZero's Monte Carlo returns), together with something that improves the value or critic:
- DouZero: unbiased Monte Carlo targets.
- PerfectDou and Suphx: a critic or oracle that sees hidden information during training.
- Suphx: a learned predictor of the global reward.
- KataGo: auxiliary targets that predict parts of the final outcome.

The project already has γ = 1, potential-based prize shaping and two aux heads. The levers it has not pulled are an oracle (perfect-information) critic, Monte Carlo value targets (λ_value = 1), and richer auxiliary targets for the final outcome. Potential-based shaping cannot change which policy is optimal, by Ng et al. 1999. So it cannot be what moves the decks off walls. A turn limit that scores unfinished games as draws is not potential-based, which explains why it changed the game itself (F6).

### Cited Findings
- **Potential-based shaping preserves the optimum.** Shaping of the form F(s, s') = γΦ(s') − Φ(s) leaves the set of optimal policies unchanged (Ng, Harada & Russell, ICML 1999; from memory) ([Ng et al. 1999](https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf)). The project's `shape_rewards` is of this form. It uses Φ = lam × (opponent's prizes left − own) / 6, with the last decision getting −Φ, so "with gamma = 1 a trajectory's rewards still sum to the game's result: only when the credit arrives changes" ([rl/train.py](file:///C:/Users/evanc/Desktop/333/metagame-rl/rl/train.py)). [F4, F6]
- **GAE is itself shaping with V as the potential.** GAE with parameter λ can be read as reward shaping with the value function as potential, followed by a λ-discounted sum (Schulman et al., ICLR 2016; from memory) ([Schulman et al. 2016, GAE](https://arxiv.org/abs/1506.02438)). With the project's default λ = 0.95 ([rl/train.py](file:///C:/Users/evanc/Desktop/333/metagame-rl/rl/train.py)), credit beyond a few dozen decisions comes almost entirely through V. [F4]
- **DouZero chose Monte Carlo returns for long, sparse games.** Zha et al. (ICML 2021) argue that DouDizhu "is a task with long horizons and sparse reward", where bootstrapping is slow because "estimating the Q-value in the current state needs to wait until the value in the next state gets close to its true value". "Unlike DQN, the convergence of Monte-Carlo estimation is not impacted by the episode length". They offset Monte Carlo's high variance with many parallel actors ([Zha et al. 2021, DouZero](https://arxiv.org/abs/2106.06135)). [F4]
- **Suphx's global reward predictor.** Li et al. (2020) found that neither per-round scores nor the final game reward is a good RL signal in multi-round Mahjong. The game reward cannot tell good rounds from bad ones, and a leading player may deliberately lose a round to keep first place ([Li et al. 2020, Suphx](https://arxiv.org/abs/2003.13590)). [F4, F6]
  - Their fix is a 2-layer GRU predictor of the final game reward from current and previous rounds, used to assign credit to each round.
  - Caveat: the predictor was trained on top human players' logs, so it is not human-data-free.
  - With it, the agent learned to play safe when leading in the last round, where RL-basic took a risky discard.
- **Suphx's oracle guiding.** An oracle agent that sees perfect information is trained first. Its perfect-information features are then dropped out gradually until it becomes a normal agent, which "improves much faster than standard RL" ([Li et al. 2020](https://arxiv.org/abs/2003.13590)). [F4, F5]
- **PerfectDou's oracle critic.** Yang et al. (NeurIPS 2022) use "perfect-training-imperfect-execution": a PPO+GAE actor-critic whose critic sees perfect information during training, while the actor uses only imperfect information ([Yang et al. 2022, PerfectDou](https://arxiv.org/abs/2203.16406)). [F4]
  - It needed "an order of magnitude" fewer samples than DouZero. PerfectDou at 2.5e9 steps beat DouZero at 1e10 steps.
  - Caveat: it also used a game-specific dense node reward, the change in the "minimum steps needed to play out all cards", computed by a dynamic program.
- **PerfectDou's ablation (Table 4, 1e9 samples, as I read the extracted table; layout slightly ambiguous).** Win rate against DouZero trained for 1e10:

  | Variant | Win rate vs DouZero (1e10) |
  |---|---|
  | Full PerfectDou | 0.524 |
  | Critic restricted to imperfect information (ImperfectDou) | 0.486 |
  | No node reward (RewardlessDou) | 0.540, but its average score difference fell to −0.201 |
  | Vanilla PPO (neither) | 0.346 |

  ([Yang et al. 2022](https://arxiv.org/abs/2203.16406)). [F4]
- **Asymmetric actor-critic** (Pinto et al. 2018; from memory) is the general form of training a critic on privileged state while the actor sees only observations ([Pinto et al. 2018](https://arxiv.org/abs/1710.06542)).
- **KataGo's auxiliary outcome targets.** Predicting final ownership and score: "removing auxiliary ownership and score targets resulted in a noticeable drop in learning efficiency" ([Wu 2019](https://arxiv.org/abs/1902.10565)). The stated mechanism is credit assignment. With only a binary result, "the neural net can only 'guess' at what aspect ... caused the loss", while the ownership target gives "direct feedback on which area of the board was mispredicted", so the net "should therefore require fewer samples to perform the correct credit assignment". [F4]
- **KataGo on value data.** The value target is "highly data-limited, with only one noisy binary result per entire game", so more, cheaper games help value training ([Wu 2019](https://arxiv.org/abs/1902.10565)). [F4]
- **Hearthstone (ByteDance): sparse reward, no discounting.** Xiao et al. (2023) trained deck building and battle end to end from scratch with no search. They used a sparse ±1 reward at episode end, episodes of about 100 steps, and changed the discount from 0.99 (their LOCM work) to γ = 1.0. Value targets came from V-trace with a PPO-style clipped policy loss and UPGO ([Xiao et al. 2023, Hearthstone](https://arxiv.org/abs/2303.05197)). [F4]
- **OpenAI Five: longer horizons help skilled agents.** Berner et al. (2019) resumed training a skilled agent with longer discount horizons. The base used 180 s (γ = 0.9993). Longer horizons improved win rate "up to the longest horizons we explored (6-12 minutes)" ([Berner et al. 2019, OpenAI Five](https://arxiv.org/abs/1912.06680)). [F4]
- **Generic PPO settings, with a caveat.** On MuJoCo continuous control, Andrychowicz et al. (ICLR 2021) recommend "GAE with λ = 0.9" and separate policy and value networks. They call the discount "one of the most important hyperparameters" and treat it as part of the algorithm, the real goal being undiscounted return ([Andrychowicz et al. 2021](https://arxiv.org/abs/2006.05990)). Caveat: these are not long-horizon games. [F4]
- **Other credit and value methods, from memory.** Phasic Policy Gradient (Cobbe et al., ICML 2021) adds a separate auxiliary phase that trains the value function more without disturbing the policy ([Cobbe et al. 2021](https://arxiv.org/abs/2009.04416)). RUDDER (Arjona-Medina et al., NeurIPS 2019) redistributes delayed reward through return decomposition ([Arjona-Medina et al. 2019](https://arxiv.org/abs/1806.07857)).

### Inferences
- **The discount is already right.** With γ = 1 and a ±1 terminal reward, discounting gives no incentive to delay a loss. So the walls' and deck-out piles' stalling cannot come from the discount (my inference). It must come from what the pilot and population actually reward.
- **The binding constraint is probably V.** With λ = 0.95 and hundreds of decisions per game (median 53 turns), the advantage of an early tempo decision relies on V's estimate of a game that ends 20-40 turns later. If V is trained mostly on wall-versus-wall games (F1/F2), it rates the prize race badly, and the policy's long-game tactics are credited badly. This fits the human lists winning short games but losing long ones (my inference). Cheap tests, each a one-flag A/B on the existing lab:
  - (a) `--lam-value 1` (Monte Carlo value targets, as in DouZero).
  - (b) λ = 1 across turns for the policy, extending the `lam_turn` idea. Check the lab's verdict on `010-pilot-lamturn` first.
  - (c) A PPG-style extra value epoch.
- **An oracle critic is the most promising generic value fix.** The literature points to it (PerfectDou, Suphx, asymmetric actor-critic). Feed the critic the hidden zones (opponent's hand, both decks' order, prize cards) during training only. It is game-agnostic, since every card game has hidden zones. It needs no human data, and at evaluation the actor is unchanged. It bears on F4 (value quality in long games) and F5 (from scratch, an oracle-guided pilot may learn tactics before deck-out piles take over) (my inference).
- **Richer auxiliary targets would follow KataGo's lesson.** The project's aux heads predict "decisions left" and "result". The KataGo analogue is to predict parts of the final outcome: each player's prizes left and cards left in deck at game end, and the turn the game ends. These counters exist in every card game (life totals and library size in MTG), so it is not reward shaping. It gives V localized gradient for "why the prize race was lost" (my inference).
- **Prize shaping cannot be the escape route.** It is game-specific and potential-based. By Ng et al. it can change learning speed but not which policy is optimal (F1, F4). If the "Trainers > Energy" gap is real at the optimum, shaping only speeds or slows its discovery (my inference).
- **A turn limit is not potential-based.** Scoring unfinished games as draws changes the reward of terminal states, so it changes the game's optimum. Short limits made draws (stalling) a new attractor (F6) (my inference).

### Gaps
- No card-game paper I found reports an ablation of GAE λ or of the value-target λ specifically for 50+ turn games.
- The literature's oracle-critic gains are from DouDizhu and Mahjong, with game-specific extras: PerfectDou's node reward and Suphx's human-trained reward predictor. A clean, human-free, shaping-free oracle-critic ablation in a TCG was not found.

---

## Q4. Card-game agents trained without human data that reached strong play: what made them work, and their compute

### Takeaway
Agents that worked without human data in DouDizhu, Hearthstone and Legends of Code and Magic shared five things. (1) Simple model-free updates (Monte Carlo Q, or V-trace/PPO with UPGO). (2) Sparse ±1 rewards with γ ≈ 1. (3) Many parallel self-play actors. (4) A league or fictitious-play opponent pool rather than pure latest-vs-latest self-play. (5) For deck building, a single end-to-end network with forced exploration of the draft.

None of them used search at play time. Their budgets range from 1 server with 4 GPUs (DouZero) to 24 V100s with about 5,800 CPU cores (Hearthstone). The LOCM champion ByteRL was later shown to be highly exploitable by a dedicated learner, which mirrors F2. The Hearthstone team's learned hero-selection policy collapsed to one hero, which mirrors F1/F3.

### Cited Findings
- **DouZero (Zha et al., ICML 2021).** Deep Monte Carlo with action encoding and 45 parallel actors on "48 cores and four 1080Ti GPUs". It "outperforms supervised agents in two days, and surpasses DeltaDou in ten days", and was trained for 30 days in total ([Zha et al. 2021](https://arxiv.org/abs/2106.06135)). [F4, F5]
  - It ranked first of 344 agents on the Botzone leaderboard.
  - DeltaDou (Bayesian inference plus MCTS) "takes more than two months to train ... even when initializing the networks with supervised regression to heuristics".
  - In their experiments, DQN "is very unstable and often diverges".
  - Win rate against DeltaDou was 0.586 (DouZero's paper) / 0.585 (public model), per PerfectDou's Table ([Yang et al. 2022](https://arxiv.org/abs/2203.16406)).
- **PerfectDou (Yang et al., NeurIPS 2022).** PPO+GAE with a perfect-information critic and a game-specific dense reward. It beat DouZero with about 10× fewer samples (2.5e9 vs 1e10) ([Yang et al. 2022](https://arxiv.org/abs/2203.16406)). [F4]
- **Suphx (Li et al. 2020): not human-free.** It started from supervised learning on top human players' logs, and its reward predictor was also trained on human logs. Each RL agent took "44 GPUs (4 Titan XP for the parameter server and 40 Tesla K80 for self-play workers) and two days" over 1.5 million games ([Li et al. 2020](https://arxiv.org/abs/2003.13590)). [F4]
  - It reached 10 dan record rank and 8.74 dan stable rank on Tenhou over 5,000+ games.
  - Run-time policy adaptation (pMCPA) simulates 100K trajectories with the hidden tiles re-dealt, then fine-tunes the policy on them. The adapted RL-2 beat its non-adapted self 66%, but it was too slow to deploy widely. This is a test-time-training analogue of the project's play-time search.
- **Hearthstone, ByteDance (Xiao et al. 2023).** End-to-end deck building and battle from scratch, with no look-ahead search ([Xiao et al. 2023](https://arxiv.org/abs/2303.05197)). [F1, F3, F4]
  - **Draft exploration ("Random-CB").** Each player's first n picks are uniformly random, with n ∈ {0, 1, 2, 4} at probabilities (0.5, 0.25, 0.125, 0.125). It is disabled at evaluation.
  - **Hero collapse.** Hero picking was excluded from the end-to-end policy and heroes were sampled uniformly, "because the learned hero policy collapsed to one hero".
  - **League (OSFP).** Self-play probability 0.6, with an add-to-pool win-rate threshold.
  - **Compute.** The best model used 24 V100s and 5,856 CPU cores; comparisons were made after 2 days, and the human-test model trained for 23 days.
  - **Results.** It beat a top-10-in-China streamer 3:0 and 3:0 (Bo5). The game was a Hearthbreaker reimplementation of the April 2015 card set.
- **Legends of Code and Magic, ByteRL (Xi et al. 2023).** One network outputs the draft policy, the battle policy and the value, with shared card embeddings; each full game is one trajectory with an LSTM ([Xi et al. 2023, LOCM](https://arxiv.org/abs/2303.04096)). [F1, F2, F3]
  - The draft has no separate reward. Credit comes only from the ±1 game result "through BPTT and value bootstrapping".
  - End-to-end training beat alternating draft/battle training: against DrainPower, 81% vs 68% for neural alternating training (approximate reading of the table).
  - It used Optimistic Smooth Fictitious Play, with self-play probability 0.6 and a pool-entry threshold of 0.7.
  - Compute: about 24 V100s with 600 CPU cores each for about 72 hours (~500K fps).
  - It won both COG 2022 tracks with average win rates of 84.41% and 94.56%. The paper does not measure draft collapse, deck diversity or exploitability.
- **ByteRL is exploitable (Haluška & Schmid, ALA 2024).** A behaviour-cloned copy of ByteRL reached 42.4% against it. PPO fine-tuning then beat ByteRL in all six evaluated settings, with average win rates of 0.904 / 0.822 / 0.803 / 0.801 / 0.734 / 0.542 on 32 / 64 / 128 / 256 / 512 / 1024 deck pools. With 256 or fewer pools, it passed 50% in under 100 training episodes ([Haluška & Schmid 2024](https://arxiv.org/abs/2404.16689)). [F2]
  - ByteRL drafted every deck in these tests, so its draft policy's exploitability was not measured.
- **LOCM competition history.** Kowalski and Miernik (IEEE CoG 2023) summarize five years of LOCM competitions and list participants' approaches, but the abstract gives no search-vs-RL comparison ([Kowalski & Miernik 2023](https://arxiv.org/abs/2305.11814)).
- **Pokémon TCG, a Kaggle hobby agent (`pkm-cabt-ppo`).** PPO self-play in the `cabt` engine, with checkpoint-pool opponents, "potential-based reward shaping on the prize differential", and one expert-iteration checkpoint that distills IS-MCTS with determinization ([pkm-cabt-ppo model card](https://huggingface.co/TomatoCream/pkm-cabt-ppo)). [F2]
  - Each agent self-played only its own deck, and "load a checkpoint with the wrong deck and it will play badly".
  - It was evaluated only against a random agent (e.g. 100% over 20 games), so there is no strength rating.

### Inferences
- **Draft collapse is a known side effect of end-to-end selection.** Hero collapse in Hearthstone is the same phenomenon as F1/F3: a learned discrete choice upstream of play collapses to one mode under self-play. ByteDance's fix was not an algorithm but removing the choice (uniform hero sampling) and forcing random early picks (Random-CB). For the draft heads, the transferable versions are (my inference):
  - forced random picks or edits on a sampled fraction of decks, as exploration that is never judged; and
  - pinning "deck type" exogenously in part of the population (the type cap already tried is similar).
- **A narrow self-play agent can be exploited quickly.** The ByteRL result shows a strong champion beaten within hundreds of episodes by a dedicated learner. Together with F2's numbers (walls 0.72-0.76 under their own pilot, 0.23-0.24 under a generalist), this supports judging decks with a pilot not trained on that population, or with a held-out exploiter pilot (my inference).
- **Compute.** DouZero-level budgets (4 GPUs, days) are the closest match to one RTX 5070 Ti. The Hearthstone and LOCM budgets are 10-25× larger in GPUs and roughly 100× larger in CPU cores (my inference from the reported numbers).
- **No winner searched at play time.** In all these from-scratch card agents, play-time search was absent from the winning systems. Where search helped (Suphx pMCPA, SPARTA), it was added on top of a strong blueprint. This suggests the project should treat search as a policy-improvement operator on top of a good pilot, not as a substitute for one (my inference).

### Gaps
- None of the papers report the draft-side distributions (e.g. energy or land counts) against human decklists, so there is no literature analogue of the "Energy-heavy vs human" diagnostic.
- I found no peer-reviewed, human-data-free Pokémon TCG or MTG agent with strength measured against human decks.
- Compute for the ByteRL exploitability study is not reported.

---

## Q5. What would most cheaply fix "the human lists win short games but lose long ones" (F4) without game-specific shaping?

### Takeaway
The cheapest fix with the most support is to change the distillation update, not the search. Replace the hard argmax cross-entropy with a KL-bounded, advantage-weighted target, using CMPO or Gumbel completed-Q. Apply it only where search beats the policy's own action by a noise-calibrated margin (SPARTA), and concentrate lines on fewer probes (KataGo). The second lever is the long-game value: an oracle critic, Monte Carlo value targets, and auxiliary outcome targets. The third is to judge deck edits under play-time search on a fraction of games, so that F1's selection signal reflects tactically competent play. Play-time search alone already turns walls 0.65 into 0.28.

### Cited Findings
- Hard or visit-count targets at low simulation budgets fail to improve the policy, and soft regularized targets fix this. The gain at Nsim = 5 comes mainly from the learning target ([Grill et al. 2020](https://arxiv.org/abs/2007.12509)). Gumbel targets learn with 2 simulations where MuZero fails at 16 or fewer ([Danihelka et al. 2022](https://openreview.net/forum?id=bERaNdoegnO)).
- Clipped advantages bound the policy change, TV ≤ tanh(c/2), and give MuZero-level Atari performance without deep search ([Hessel et al. 2021, Muesli](https://arxiv.org/abs/2104.06159)).
- A deviation threshold from the blueprint (0.05) improves score even with many rollouts, and 2-SD pruning saves rollouts without loss ([Lerer et al. 2020, SPARTA](https://arxiv.org/abs/1912.02318)).
- Recording policy targets only from a fraction (25%) of deeper searches beats all fixed search sizes ([Wu 2019, KataGo](https://arxiv.org/abs/1902.10565)).
- Shallow search with simple Monte Carlo rollouts is about as good as complex planning for policy learning ([Hamrick et al. 2021](https://arxiv.org/abs/2011.04021)). So the one-turn depth is not obviously the bottleneck.
- A perfect-information critic and oracle guiding speed up learning in long imperfect-information card games ([Yang et al. 2022](https://arxiv.org/abs/2203.16406); [Li et al. 2020](https://arxiv.org/abs/2003.13590)). Auxiliary outcome-decomposition targets improve credit assignment ([Wu 2019](https://arxiv.org/abs/1902.10565)).
- Run-time adaptation and search on top of a fixed policy gives large gains (66% for Suphx pMCPA; SPARTA's Hanabi record) ([Li et al. 2020](https://arxiv.org/abs/2003.13590); [Lerer et al. 2020](https://arxiv.org/abs/1912.02318)).

### Inferences
Ranked by cost against expected effect (all my inference; each is generic across card games):
1. **Expert iteration v4: change the target, keep the search (low cost; F4).** Probe options sampled by Gumbel-Top-k from the pilot (m = 4-8), with sequential halving over 8-16 lines in total per probe. Score every line to the end of the turn with the value of a *frozen* generalist (pilot-v2), not the training pilot. Build π_target = normalize(π_prior · exp(clip(Â/SE, −c, c))), with c about 1-2. Train with a KL term at weight ≤ 0.1, only on probes where the best option beats the policy-mean value by more than 2 SE.
   - Success criteria: entropy does not rise; agreement with π_target before the step is above 60-70%; Elo against the human lists is non-negative after 2 segments. Stop it if the competence score has not moved after 2 segments.
2. **Value-side credit (one-flag tests; F4, F5).** Try `--lam-value 1`, then an oracle critic that reads the hidden zones in training only, then aux heads for the final per-player counters (prizes left, deck left, game-ending turn). Measure the long-game slice: win rate of the human lists against walls in games longer than the median.
3. **Selection under search (moderate cost; F1, F2, F4).** For the final judging games of candidate deck edits, have both seats use the one-turn play-time search on a fraction of decisions. If walls lose under search-strength play (0.65 → 0.28 on non-deck-out games), the draft head stops being rewarded for decks that only win against a weak or co-adapted pilot. This uses search where it is reliable (play time) rather than where it failed (distillation), as poker and Hanabi systems do.
4. **R-NaD-style regularization for pilot and draft heads (F1-F3).** Regularize toward a reference policy and move the reference to the reached fixed point periodically. This generalizes the KL anchor (+65 Elo on human lists) and could counter draft-head entropy collapse without a permanent prior.

Not recommended:
- Stronger prize shaping. It is game-specific, and potential-based shaping cannot move the optimum (Ng et al.).
- Turn limits. They are not potential-based and create a draw attractor (F6).

### Gaps
- No published experiment combines CMPO or Gumbel targets with determinized flat Monte Carlo search in a card game. The size of the gain for F4 is unknown until tried.
- The cost of play-time search inside selection games on this machine (decisions/s with k options × lines) needs measuring. The literature gives no transferable throughput figure.

---

## Q6. Mapping summary: findings to failure modes and concrete loop changes

### Takeaway
Most search and credit findings bear on F4. Several also hit F1-F3 through one channel: the deck-selection signal is only as good as the pilot judging it. Fixing how search enters training and selection is the shortest path from F4 to F1.

### Cited Findings
| Finding | Source | Bears on | Concrete change |
|---|---|---|---|
| Few-sim argmax/visit targets fail; completed-Q / π̄ targets work at 2-5 sims | [Danihelka 2022](https://openreview.net/forum?id=bERaNdoegnO); [Grill 2020](https://arxiv.org/abs/2007.12509) | F4 | Soft Gumbel/π̄ target instead of one-hot best option |
| Clipped-advantage MPO target, TV ≤ tanh(c/2) | [Hessel 2021](https://arxiv.org/abs/2104.06159) | F4 | CMPO target with small KL weight; fixes the entropy rise and size of the update |
| Deviate from blueprint only above threshold; 2-SD pruning | [Lerer 2020](https://arxiv.org/abs/1912.02318) | F4 | SE-calibrated gate against the policy's own choice; prune clearly worse options |
| Playout cap randomization; policy target pruning | [Wu 2019](https://arxiv.org/abs/1902.10565) | F4 | Fewer, deeper probes recorded; no exploration noise in targets |
| Auxiliary ownership/score targets aid credit assignment | [Wu 2019](https://arxiv.org/abs/1902.10565) | F4, F5 | Aux heads for final per-player counters and game length |
| Perfect-information critic / oracle guiding | [Yang 2022](https://arxiv.org/abs/2203.16406); [Li 2020](https://arxiv.org/abs/2003.13590) | F4, F5 | Training-only critic that sees hidden zones |
| MC returns robust to episode length | [Zha 2021](https://arxiv.org/abs/2106.06135) | F4 | `--lam-value 1` |
| Potential-based shaping preserves optimum | [Ng 1999](https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf) | F1, F4, F6 | Do not expect prize shaping to move decks; avoid non-potential reward changes like draw limits |
| R-NaD regularization; mistake thresholding | [Perolat 2022](https://arxiv.org/abs/2206.15378) | F1, F2, F3, F4 | Reference-policy regularization with periodic reference update, for the pilot and draft heads |
| Learned hero choice collapsed; random early picks | [Xiao 2023](https://arxiv.org/abs/2303.05197) | F1, F3, F5 | Forced random edits on a fraction of decks (exploration, not judged) |
| Champion self-play agent quickly exploited | [Haluška & Schmid 2024](https://arxiv.org/abs/2404.16689) | F2 | Judge decks with a pilot not trained on that population, or an exploiter pilot |
| Deck-specific PPO pilot plays other decks badly | [pkm-cabt-ppo](https://huggingface.co/TomatoCream/pkm-cabt-ppo) | F2 | Consistent with keeping the pilot trained on a varied field |
| Determinization unsound but effective; sound search costly | [Schmid 2023](https://arxiv.org/abs/2112.03178); [Brown 2020](https://arxiv.org/abs/2007.13544); [Cowling 2012](https://eprints.whiterose.ac.uk/75050/) | F4 | Keep cheap determinized search; do not attempt ReBeL/SoG on one GPU |
| Planning most useful for learning; shallow MC rollouts suffice | [Hamrick 2021](https://arxiv.org/abs/2011.04021) | F4 | The one-turn depth is acceptable; fix the update rule first |

### Inferences
- **Order of work (my inference).**
  1. Expert iteration v4 with a soft, gated target and a frozen-generalist leaf value: cheap, and it targets the three recorded failures directly.
  2. `--lam-value 1` and auxiliary outcome heads: one-flag A/Bs.
  3. An oracle critic: moderate code change, the best-supported generic value fix.
  4. Search-on judging for deck selection: it connects F4 to F1.
- **Stop rule, per CLAUDE.md.** Stop any of these that has not moved the competence score or the long-game slice within 2 segments.

### Gaps
- None of the cited works study a population whose decks and pilot co-adapt (the F1/F2 loop) together with search distillation. The F1 benefit of search-based selection is therefore a hypothesis to test, not a literature result.
