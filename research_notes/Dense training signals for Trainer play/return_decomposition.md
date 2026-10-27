# Return decomposition and hindsight credit for Trainer play (metagame-rl, 2026-10-24)

Context read: ar/train.py (PPO, GAMMA 1, LAM 0.95, reward only at game end, soft search distillation at 5% of main-phase decisions, MODEL_OVERRIDES history=1). Sources were read as abstracts/HTML snippets via search; PDFs would not parse, so details not listed below are not verified. Statements under "Inferences" are mine, not the papers'.

## 1. RUDDER and Align-RUDDER

### Takeaway
RUDDER trains a sequence model to predict the episode return from the prefix and pays out the difference of consecutive predictions as a dense, return-equivalent reward. It helped on delayed-reward toys and about half of Atari, needs the predictor to be accurate, and can inject spurious reward. Align-RUDDER replaces the LSTM with sequence alignment of successful demonstrations, which needs human-like demos and so is out under the self-discovery rule.

### Cited Findings
- RUDDER redistributes the single final return to earlier steps; the new decision process is return-equivalent (same optimal policies), and an optimal decomposition leaves zero expected future reward at each step. — [RUDDER, arXiv 1806.07857](https://arxiv.org/pdf/1806.07857)
- Mechanism: an LSTM predicts the return and contribution analysis turns it into per-step contributions; the preferred form is "the difference of consecutive predictions". — [RUDDER ar5iv](https://ar5iv.labs.arxiv.org/html/1806.07857)
- Atari with PPO: over the last 10 training games RUDDER scored higher in 29 games and the PPO baseline in 23; RUDDER learned faster in 32 vs 20. So it is not a uniform win. — [RUDDER ar5iv](https://ar5iv.labs.arxiv.org/html/1806.07857)
- Stated costs: needs "safe exploration" to produce delayed-reward samples, a lessons replay buffer of surprising episodes, LSTM training limited to 500-frame chunks on Atari; may be less effective when rewards are not delayed; "reward redistribution may introduce disturbing spurious reward signals." — [RUDDER ar5iv](https://ar5iv.labs.arxiv.org/html/1806.07857)
- A NeurIPS 2019 reviewer noted worse performance on a significant share of Atari games and a trade-off between faster Q learning and contribution-analysis error. — [NeurIPS 2019 reviews](https://papers.neurips.cc/paper_files/paper/2019/file/16105fb9cc614fc29e1bda00dab60d41-Reviews.html)
- Hopfield-RUDDER swaps the LSTM for modern Hopfield networks because LSTM training is hard and needs many episodes; shown on small 1D environments only. — [NeurIPS 2021 workshop](https://neurips.cc/virtual/2021/35788)
- Align-RUDDER (ICML 2022) builds a profile model by multiple sequence alignment of as few as two successful demonstrations, redistributes reward to events that complete sub-tasks; mines a diamond in Minecraft ObtainDiamond, though not often. — [Patil 2022](https://proceedings.mlr.press/v162/patil22a.html), [arXiv 2009.14108](https://arxiv.org/pdf/2009.14108)
- A transformer return-decomposition for episodic RL (2019) reports better sample efficiency on MuJoCo and attention weights usable for inspection. — [arXiv 1905.13420](https://arxiv.org/pdf/1905.13420)
- RUDDER extensions to multi-agent are cooperative (team reward over time and agents); I found no source on RUDDER in zero-sum self-play or card games. — [AAMAS 2022](https://ifmas.csc.liv.ac.uk/Proceedings/aamas2022/pdfs/p1723.pdf)

### Inferences
- The telescoping difference g(prefix_t) - g(prefix_{t-1}) is the same object as potential-based shaping with potential g. A GAE critic V already does this at lambda 0. So RUDDER only adds value if g can see more than V does (whole history, trained to the final result with a sequence loss) or is read with look-ahead. With history=1 the current critic is nearly Markov; hidden-information facts (what was fetched, what is in the opponent's deck) live in the history.
- The failed "auxiliary heads predicting decisions left and the final result" (log #95-#100) is close to training g but did not pay out the differences; I cannot tell from the notes whether differences were ever used as reward. Check log before reusing.
- The evidence says the redistribution is only as good as the predictor. If the current critic values Trainers like blank cards (A1-A3), a return predictor trained on the same self-play data may share that blindness. An offline test of this is cheaper than a training run (see Loop change).
- Align-RUDDER is a poor fit: it needs successful demonstrations; self-play wins could stand in, but then alignment would find patterns the policy already plays.

Loop change: offline RUDDER probe, no training run. Take the saved rollouts (ar/out/rollout_w*.bin, plus any older ones), train a small causal transformer g over each player's full decision sequence (cards as features, last token = result) with loss on final result at every prefix, 10-20 min on GPU. Then for prompt decisions compute the contribution g(after answer) - g(before answer) for fetches of the lists' Trainers against a random card. Cost about 30-40 min including coding, no game workers. Obeys the rules (outcome only, no card labels in training; card kinds only to evaluate). Why it is better than the failed tries: it asks first whether the outcome data contain any detectable signal for Trainer answers at the current sample size; if the sequence model cannot separate good from random answers, no credit scheme (prize shaping, lambda 1, aux heads) could, and the fix is more data or search probes at prompts rather than credit. If it can separate them, use g's differences as extra reward in advantages() with a coefficient decayed over iterations (screen ≤70 min).

## 2. Hindsight Credit Assignment, Counterfactual Credit Assignment, Temporal Value Transport, Synthetic Returns, 2023-2026 follow-ups

### Takeaway
These methods credit actions by how much later information reveals about them (HCA), by removing luck from the baseline (CCA), or by learning which past states predict later reward (TVT, synthetic returns). CCA/COCOA-style future-conditional baselines are the best fit: pure variance reduction, no shaping, no bias if hindsight excludes the agent's own actions. Their evidence is on small synthetic tasks, and accuracy of the learned hindsight model is the main failure mode.

### Cited Findings
- HCA (Harutyunyan 2019) credits past actions by how likely they were to have produced the observed outcome; state-conditional and return-conditional hindsight distributions give policy-gradient estimators; shown on illustrative tasks. — [NeurIPS 2019](https://proceedings.neurips.cc/paper/2019/hash/195f15384c2a79cedf293e4a847ce85c-Abstract.html), [arXiv 1912.02503](https://arxiv.org/pdf/1912.02503)
- CCA (Mesnard 2021): value function conditioned on a future summary Phi_t that is a backward RNN or transformer over later observations/actions/rewards; Phi_t must be independent of A_t given X_t, enforced by a KL independence loss; advantage G_t - V(X_t, Phi_t) has variance no larger than the forward advantage under that condition. — [CCA ar5iv](https://ar5iv.labs.arxiv.org/html/2011.09464)
- CCA results: robust to growing exogenous reward noise where vanilla PG degrades; worse at very low noise because imperfect independence biases the update; beat actor-critic and HCA baselines in high-variance Key-to-Door; "inaccurate hindsight classifiers will result in miscalibrated estimation of luck, leading to bias"; only single-action estimator tested; scaling to complex environments left for future work. — [CCA ar5iv](https://ar5iv.labs.arxiv.org/html/2011.09464)
- COCOA (Meulemans 2023, NeurIPS): HCA measures contribution relative to rewarding states and gives spurious estimates; conditioning on rewards or learned reward-object representations gives lower bias and variance on long-term credit tasks. — [arXiv 2306.16803](https://arxiv.org/abs/2306.16803v2)
- R-HCA (RLJ 2026) says COCOA handles immediate rewards poorly under noisy intermediate rewards and fixes it; reports lower or equal variance in analysed cases. — [RLJ 2026](https://rlj.cs.umass.edu/2026/papers/Paper133.html)
- "Towards Causal Credit Assignment" (HCA with factored causal structure) has been withdrawn by its author; do not rely on it. — [arXiv 2212.11636](https://arxiv.org/abs/2212.11636)
- TVT (Hung 2019, Nat. Commun.): episodic memory recall carries the value of a later point back to the earlier state that the memory belongs to. A later paper notes TVT learns no reward model, so it cannot split a reward over several past states that partly predict it. — [Hung 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6864102/), [Raposo 2021](https://arxiv.org/pdf/2102.12425)
- Synthetic returns (Raposo 2021): learn associations between states and far-future reward; a model predicts each state's contribution, TD then maximises these "synthetic returns"; IMPALA agent solves Atari Skiing with about 25x fewer steps than Agent57; contributions spike after critical actions. — [arXiv 2102.12425](https://arxiv.org/pdf/2102.12425)
- 2026 hindsight work in LLM agents (HCAPO) uses a hindsight importance ratio to boost credit for actions more likely given success and says GRPO spreads terminal reward uniformly; separate 2026 work argues token entropy bounds how much hindsight credit is possible. Single-source summaries, not read in full. — [HCAPO arXiv 2603.08754](https://arxiv.org/pdf/2603.08754), [token-level hindsight](https://awesomepapers.io/speech-audio/papers/2604.11056)
- Survey of temporal credit assignment in deep RL (2023) frames return decomposition as redistribution and covers a causal-transformer decomposition (SECRET); I could not parse the PDF, so only the search-engine summary supports this. — [arXiv 2312.01072](https://arxiv.org/pdf/2312.01072)

### Inferences
- Luck in this game is large (shuffles, prize cards, the opponent's draws and plays). A CCA baseline whose Phi_t summarises the opponent's later moves and the random draws, but not the player's own actions, removes variance from every decision including Trainer prompts, which is exactly the signal-to-noise problem. It also cannot bias the optimum if independence holds.
- Independence is delicate here: in a two-player game the opponent's later play responds to my action, so Phi_t from the opponent's later moves leaks my action. Restrict Phi_t to chance events (cards drawn, coin flips, hidden hand revealed) or enforce the KL independence loss as CCA does. This is a real risk, not a detail.
- A state-conditional HCA weight suits the fetch-then-use chain: h(a | s_t, s_{t+k}) is sharp when the chosen card shows up in a later hand, discard, or play, and flat when it left no trace. Weighting the return by (1 - pi/h) (the HCA form, quoted from memory, check the paper) gives full credit to answers with a visible later effect and almost none to answers without one. The classifier is over legal-option indices with card features, so it carries to Magic. HCA baselines struggled in CCA's low-variance task, so expect fragility.
- Synthetic returns / TVT are more of the same family as RUDDER: a learned state-to-final-reward associator. Prefer one of them, not both.

Loop change: (a) CCA luck baseline in ar/train.py: add a second value head V(s_t, Phi_t) where Phi_t is a small backward GRU/pooling over the player's own later chance events only (draws, prize reveals, coin flips; the rollout would need to log them, check what the engine exposes), train it with the usual value loss, use G_t - V(s,Phi) in place of GAE advantage for the policy update (keep GAE as fallback). Cost: ~60-80 lines plus a rollout field; one 5-minute ar/ run to check it runs, then a ≤70-minute screen against the C49-sd baseline on Elo and M. Obeys the rules (no human data, no card shaping, game-agnostic). Unlike lambda 1 and prize shaping it adds no bias and no hand tempo term; it only subtracts luck from the baseline. (b) Second variant, higher risk: fetch-use hindsight classifier for prompt decisions only, described above; ~40 lines, same screen.

## 3. Suphx global reward prediction, DouZero's Monte Carlo signal

### Takeaway
Suphx predicts the final multi-round game reward from the rounds so far with a GRU and pays the change in that prediction as the per-round reward; this gave stronger play than raw round score (shown by rank plots, no numbers). DouZero shows plain Monte Carlo returns with gamma 1 and huge sample volume suffice for a sparse-win/loss card game with long episodes, and adding TD gave no clear benefit.

### Cited Findings
- Suphx (Li 2020) global reward prediction: two-layer GRU plus two fully connected layers reads per-round features (round score, accumulated score, dealer position, repeat counter, Riichi bet counter) over the current and previous rounds, trained with MSE to the final game reward on top human logs; the RL reward for round k is Phi(x_k) - Phi(x_{k-1}), replacing the raw round score in the policy gradient. — [Suphx HTML](https://arxiv.org/html/2003.13590v2)
- Ablation: RL-1 (with prediction) beats RL-basic (round score) in stable rank, shown only as interquartile-range plots (Figure 8); no numeric gain in the text. Qualitative: with a big lead in the last round RL-1 plays defensively, RL-basic goes for a risky win. — [Suphx HTML](https://arxiv.org/html/2003.13590v2)
- Suphx's predictor is trained on human logs; the abstract confirms the pipeline is supervised from pro play then self-play RL. — [Suphx abstract](https://arxiv.org/abs/2003.13590)
- DouZero (Zha 2021) uses Deep Monte-Carlo: full-episode returns, discount 1, action features as input to a Q network; the authors say the high variance is "greatly outweighed by the scalability" of parallel actors; DQN was unstable and often diverged, a simple actor-critic variant failed, and adding TD (SARSA) gave no clear benefit. Reward is only the final win/loss. — [DouZero ar5iv](https://ar5iv.labs.arxiv.org/html/2106.06135)
- DouZero encodes each move as a card matrix ignoring suits so value transfers between similar moves. — [DouZero ar5iv](https://ar5iv.labs.arxiv.org/html/2106.06135)

### Inferences
- Suphx's reward prediction mostly handles a multi-round score structure (ranking points across rounds). Pokémon TCG is one round, so the direct analogue is a within-game predictor with turn-level (not round-level) features including Prizes, which the rules allow. That is again a learned potential; see section 1 for why it may not add to V.
- DouZero's lesson is about the scale of Monte Carlo data and a net that scores actions from their features, not about dense credit. Here lambda 0.95 over 100+ decisions is already near Monte Carlo at long range, so a pure-MC (lambda 1 whole game) arm costs nothing to test but is unlikely to be the lever; the lambda 1 within-turn failure (-37 Elo) is a different arm (MC inside a turn, bootstrap at turn ends).
- DouZero's action scoring from card features (not a fixed action index) is already what a pointer head over legal options does.

Loop change: Suphx-style turn-level potential, only if the offline probe in section 1 shows the sequence predictor separates good from random answers: g is a GRU over per-turn summaries of the game state, reward_t = g(turn t) - g(turn t-1) added to the end-of-game reward with a decaying coefficient. Cost: small model and rollout field, ≤70-minute screen. Obeys the rules (outcome and Prizes only). Differs from the failed prize shaping in that the potential is learned from the result rather than fixed to Prize counts, so it carries no tempo bias; it is still a risk because it is a critic-like object that may share V's blind spot. Lower priority than section 2.

## 4. Self-imitation and good-outcome imitation

### Takeaway
SIL imitates only past decisions whose return exceeded the current value estimate; it helped on hard-exploration Atari and PPO on MuJoCo. I found no source applying it to self-play board or card games, and in PPO with normalized advantages most of its effect is already present.

### Cited Findings
- SIL (Oh 2018) is an off-policy actor-critic that learns to reproduce the agent's past good decisions, imitating stored state-action pairs only when the return exceeds the value estimate; improves A2C on hard-exploration Atari, competitive with count-based exploration, improves PPO on MuJoCo. — [arXiv 1806.05635](https://arxiv.org/abs/1806.05635), [Google Research page](https://research.google/pubs/self-imitation-learning/)
- A 2026 arXiv sparse-reward variant replays successful self-encountered trajectories (MuJoCo, Animal-AI, PointMaze, no board games). — [arXiv 2603.27515](https://arxiv.org/pdf/2603.27515)
- A self-reported, unreviewed GitHub project reports pure self-play PPO with +/-1 terminal reward and no shaping beating Gumbel AlphaZero baselines on Othello, Hex 11x11 and Go 9x9. — [the-puzzler/selfplay](https://github.com/the-puzzler/selfplay)
- A comparison of self-play algorithms with PPO found cyclic policy evolution during training under various self-play definitions. — [arXiv 2006.04471](https://arxiv.org/pdf/2006.04471)

### Inferences
- The SIL clip max(R - V, 0) learns only from games better than the critic expects. If V is blind to Trainer value, a won game after a bad fetch and after a good fetch look the same, so SIL cannot discriminate prompt answers either. It also learns from lucky wins, which is the variance CCA removes.
- In a zero-sum self-play game, half of all trajectories are wins, so "good-outcome imitation" copies both sides' play; it behaves like a positive-advantage-only PPO step. Not distinct enough to be worth a screen.

Loop change: none recommended on its own. If wanted as a free add-on to the CCA arm, add a loss term -logp * clamp(G - V, min=0) on prompt decisions only; ~5 lines, same ≤70-minute screen. Obeys the rules; unlikely to beat the failed tries since it uses the same V and the same terminal signal.

## 5. Why lambda 1 inside a turn and never-fading prize shaping hurt, and which methods avoid it

### Takeaway
Both failed arms inject a signal chosen by hand about the game's structure (turn boundary, Prize count), so any mismatch with winning becomes a bias, while the methods here learn credit from the result or only reduce variance. I found no paper that tested these two arms in a card game; the explanation below is inference.

### Cited Findings
- RUDDER's guarantee: return-equivalent redistribution leaves optimal policies unchanged, but only for an optimal decomposition; imperfect decompositions can add spurious reward. — [RUDDER ar5iv](https://ar5iv.labs.arxiv.org/html/1806.07857)
- CCA's guarantee: a future-conditional baseline has no higher variance if the hindsight feature is independent of the action; leakage biases it. — [CCA ar5iv](https://ar5iv.labs.arxiv.org/html/2011.09464)
- DouZero: with gamma 1, high-variance MC is acceptable only with very high sample throughput; TD brought no clear benefit. — [DouZero ar5iv](https://ar5iv.labs.arxiv.org/html/2106.06135)

### Inferences
- Lambda 1 inside a turn: the Trainer chain's payoff sits at the end of the turn (the damage, KO, Prize), so it should help, but the target then is one turn's outcome with all the draw and opponent noise and no baseline for it, so variance rises faster than signal; the -37 Elo result fits this.
- Prize shaping that never fades pays for tempo (taking Prizes early) rather than winning; a Trainer that sets up a slow engine loses reward to a fast attacker, which pushes the policy toward the Energy-heavy minimum the project is trying to leave. Fading to 0 is the standard fix and was already used earlier.
- RUDDER, Suphx-style prediction and synthetic returns avoid hand tempo bias, but inherit the predictor's accuracy limits. CCA/COCOA avoid bias by construction if independence holds, but give no new credit to a prompt answer; they only lower noise. HCA-style weights give prompt answers explicit credit where later states show the effect.
- Ranking for this project (my judgment): (1) offline RUDDER probe as a go/no-go check; (2) CCA luck baseline; (3) fetch-use hindsight classifier; (4) Suphx-style turn potential; (5) SIL add-on.

Loop change: run the offline probe first (30-40 min, no GPU games); then the CCA arm, then the fetch-use arm, each as one ≤70-minute screen with the standard Elo and M scoring, killing a run that does not move M by the midpoint, per the standing rule.

## Gaps
- Could not parse PDFs (Suphx, DouZero, HCA, Survey, RUDDER full text), so exact HCA formulas, SIL's loss details, DouZero's episode lengths and any Suphx numeric gains are not verified. The HCA weight (1 - pi/h) is from memory.
- No source found on RUDDER, HCA, CCA or synthetic returns in competitive two-player zero-sum self-play or in card games with prompts; transfer is untested in the literature.
- Did not check whether the engine logs chance events for the CCA baseline, whether the search probes already cover prompt decisions, or what the earlier auxiliary-head tries (log #95-#100) used as targets; check notes/progress-log.md first.
- 2023-2026 transformer return-decomposition papers beyond 1905.13420, STAS (cooperative multi-agent, [arXiv 2304.07520](https://arxiv.org/html/2304.07520v2)), RL from bagged reward ([arXiv 2402.03771](https://arxiv.org/html/2402.03771v3)) and SECRET (via survey) were not found in the single searches done.
