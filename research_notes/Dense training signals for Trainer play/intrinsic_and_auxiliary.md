# Intrinsic rewards and auxiliary predictive tasks for setup actions (Trainer play)

Scope note: about 16 searches, mostly abstracts and snippets (full texts not opened, flagged per item). I did not re-skim the earlier research_notes folders or the progress log; the "already tried" list is taken from the assignment (log #76-#103, #95-#100). Items marked "(memory)" come from my own background knowledge and carry no link; the report writer should treat them as unverified.

## 1. Empowerment and the "log number of legal options" proxy

### Takeaway
Empowerment (mutual information between an action sequence and the later state) is the formal version of "this action created options", but exact or variational estimates are costly and biased in stochastic settings; the cheap proxy (log number of legal options) is game-agnostic and, if used as a potential (gamma*Phi(s') - Phi(s)), cannot change the optimal policy. No source found that tests either on a card game's setup actions.

### Cited Findings
- VIC (Gregor 2016) maximises mutual information between a set of options and the final states they reach ("empowerment"); two variants: explicit option embedding, and implicit options where the action space is the option space — [Variational Intrinsic Control](https://ar5iv.arxiv.org/html/1611.07507)
- Mohamed & Rezende (NIPS 2015) give a variational lower bound on mutual information so empowerment can be estimated with deep nets from pixels; they say the classic Blahut-Arimoto computation is exponentially expensive — [arXiv 1509.08731](https://arxiv.org/pdf/1509.08731)
- Kwon (ICLR 2021) reports the implicit-option intrinsic reward of VIC is biased in stochastic environments and converges to suboptimal solutions; fixing the number of options caps attainable empowerment — [Variational Intrinsic Control Revisited](https://arxiv.org/pdf/2010.03281)
- Empowerment has been used in games for NPC behaviour (companion NPCs, Guckelsberger/Salge/Colton CIG 2016), and exact computation in discrete deterministic games needs search (UCT-accelerated, CIG 2018); abstract-level only — [Coupled Empowerment Maximisation](https://research.gold.ac.uk/id/eprint/21745), [UCT empowerment](https://research.gold.ac.uk/id/eprint/23415)
- Survey placing empowerment as the state "where the agent has the most control on the environment" — [Survey on intrinsic motivation in RL](https://arxiv.org/pdf/1908.06976)
- Potential-based shaping: F = gamma*Phi(s') - Phi(s) leaves the optimal policy unchanged and is necessary and sufficient for that (as reported by secondary sources; original paper not opened) — [Ng, Harada, Russell 1999](https://mlanthology.org/icml/1999/ng1999icml-policy/), [AAAI summary](https://ojs.aaai.org/index.php/AAAI/article/view/9628/9487). The paper's motivation is that non-potential bonuses let agents loop to farm reward.

### Inferences
- A draw/search Trainer raises the number of legal options at the owner's next decision (more hand cards to play or attach). So log N_legal is a plausible, generic stand-in for empowerment; it needs no estimator because `legal_offsets` is already in the rollout batch.
- Used as an additive bonus it invites stalling (maximise options, not wins); used as a potential with gamma = 1 the shaped return telescopes to Phi(last) - Phi(first), so the optimum is unchanged and only credit timing moves. With GAE lambda 0.95 the effect is a bias-variance change in the advantage, not a change of objective. Caveat: the potential is of the player's own state only; the opponent's option growth is ignored.
- Risk that remains: the option count also rises from Energy attachments and Pokémon being benched, so it does not single out Trainers; it will credit anything that widens choice. Whether this beats the immediate-Energy bias is an empirical question.
- Empowerment proper (VIC) is the heavier route (needs a future-state encoder and a q(option|state) network, biased in stochastic games such as shuffled draws); not recommended before the proxy.

### Gaps
- No paper found applying empowerment or option-count to card/board-game self-play with win/loss reward; evidence on stalling in that setting is absent.
- Full texts of Ng 1999 and VIC not opened.

Loop change: in `advantages()` add a potential-based term to the reward: r_t += Phi(next decision of same trajectory) - Phi(decision t), Phi = c * log(number of legal options), c about 0.05-0.1 of one win unit, taken from `legal_offsets` (zero extra rollout cost; about 10 lines in ar/train.py, one 5-minute ar slot). Obeys the rules: generic quantity, potential-based, no card/Energy knowledge, carries to Magic. Why it should credit Trainers better than prize shaping (-31 Elo, never fades and is not potential-based on options) or the failed aux heads: it pays at the move that creates options, which is the Trainer play, rather than at the outcome; it is policy-invariant in theory, so it cannot add a stalling optimum. Check at once that it does not just reward Energy attachment (compare per-kind Trainer value M).

## 2. Curiosity and novelty in games

### Takeaway
Prediction-error (ICM), RND and count bonuses are exploration tools for sparse reward; the sources show good results in single-player games but also failure on stochastic transitions, and I found no evidence they help credit assignment for setup actions in self-play card games. Draws and shuffles are exactly the stochastic case that breaks forward-prediction curiosity.

### Cited Findings
- ICM: curiosity = error predicting the consequence of one's own action in a feature space trained by an inverse-dynamics model, so unaffected parts of the world are ignored; tested only in VizDoom and Super Mario Bros — [Pathak 2017](https://arxiv.org/abs/1705.05363)
- Large-scale study: 54 environments with no extrinsic reward; curiosity agents often correlate with game score; random features suffice on many benchmarks, learned features generalise better; prediction-based rewards fail in stochastic setups; in Breakout the agent raises score as a side effect of seeking new brick patterns — [Burda et al. 2018](https://arxiv.org/abs/1808.04355), [ar5iv](https://ar5iv.labs.arxiv.org/html/1808.04355)
- RND: bonus = error predicting a fixed random network's features of the observation; sets state of the art on Montezuma's Revenge, and gives a way to combine intrinsic and extrinsic rewards — [arXiv 1810.12894 (abstract via HF)](https://huggingface.co/papers/1810.12894). The claim that RND avoids the "noisy TV" problem came only from a glossary page ([Envisioning](https://www.envisioning.com/vocab/random-network-distillation)); unverified against the paper.
- Asymmetric self-play (Sukhbaatar 2017) uses purely internal reward between two copies of an agent to learn about the environment, not competitive win/loss play — [arXiv 1703.05407](https://arxiv.org/pdf/1703.05407)
- Curiosity plus competition in a survival environment and a master's thesis on curiosity in multi-agent tasks exist, but no dedicated analysis of reward hacking — [Fanti 2023](https://ar5iv.labs.arxiv.org/html/2301.08030), [Schäfer MSc 2019](https://agents-lab.org/blog/master-dissertations/lschafer_msc2019.pdf)

### Inferences
- Novelty is the wrong axis: the pilot's problem is not unexplored states but mis-credited ones. A bonus for new states would also pay for rare cards drawn by chance (noise), not for choosing to draw.
- If anything is used, it should be a dynamics-error signal on the player's own controllable features (the inverse-model trick of ICM), which in a card game would mean "what did my action change"; that is item 3, as an auxiliary loss rather than a reward, avoiding reward hacking.

### Gaps
- No evidence located on curiosity or RND in competitive self-play card games (Hearthstone, Magic, poker). Absence of evidence, not evidence of harm.

Loop change: do not add a curiosity reward. Cost of trying anyway (RND head on the pooled state embedding, about 25 lines, one slot) is low, but it breaks "simple" for a signal I expect to be neutral-to-noisy; rank it last. Obeys the rules (generic) but unlikely to credit Trainer play, because novelty is not tied to the later payoff.

## 3. Auxiliary predictive tasks (UNREAL, SPR, dynamics/effect prediction, successor features)

### Takeaway
Auxiliary losses that predict the future state or the effect of an action are the best-supported way to force the encoder to represent what a move changed; they work through shared representation, so they are compatible with PPO. The prior failed heads predicted scalars (decisions left, result); the literature points to vector next-state prediction, not those scalars. Direct evidence under PPO on combinatorial pointer actions is thin.

### Cited Findings
- UNREAL: extra pseudo-reward tasks (pixel/feature control) and reward prediction share a representation with A3C; Labyrinth 87% of expert human-normalised vs 54% for A3C, about 10x faster; Atari mean 880% — [Jaderberg 2016](https://arxiv.org/pdf/1611.05397). Base learner is recurrent A3C, not PPO.
- SPR: predict own latent states several steps ahead with a learned transition model against an EMA-encoder target, no reconstruction or negatives; Atari 100k median human-normalised 0.415, 55% relative gain over the prior best — [Schwarzer 2021](https://ar5iv.labs.arxiv.org/html/2007.05929). Off-policy, data-limited setting; the pretraining follow-up is [arXiv 2106.04799](https://arxiv.org/pdf/2106.04799).
- Cardsformer (Hearthstone): a prediction model trained on offline trajectories forecasts state transitions from card text, and a policy model generalises to unseen cards; reported better data efficiency than prior methods, code and PyStone benchmark released. Abstract-level only; I could not open the paper to see how the prediction feeds the policy — [IOS Press FAIA230581](https://ebooks.iospress.nl/doi/10.3233/FAIA230581)
- Phasic Policy Gradient: an auxiliary value head trained only to shape policy representations, distilled in separate phases, improves sample efficiency on Procgen over PPO — [Cobbe 2020](https://arxiv.org/pdf/2009.04416)
- PPO loses feature rank and trust-region effectiveness during training; an auxiliary loss regularising representation (PFO) reduces the collapse — [Moalla et al. 2024](https://arxiv.org/html/2405.00662v3). Relevant: the plateau may be partly representation collapse.
- Successor features separate dynamics from reward, so value for a new reward is a linear read-out of expected future features; guarantees for transfer, tested on navigation and an arm — [Barreto et al.](https://arxiv.org/pdf/1606.05312)
- (memory, unverified) MuZero/Dreamer-style reward and dynamics heads; CURL/CPC contrastive objectives; none opened in this session.

### Inferences
- The Trainer failure is that V treats a draw/search Trainer like a blank card: the value head cannot see what the action did. An effect-prediction loss (from encoding of state and chosen option, predict the pooled encoding of the same player's next decision, stop-gradient or EMA target) makes "hand/deck after a draw" a required feature, which then lets V and the pointer head use it. This is SPR with one-step horizon on the decision sequence; the next-decision state is already in the batch (next row with the same `traj`), so no engine change.
- This differs from the failed heads (#95-#100) in target: a rich vector derived from the board, not a scalar tied to the outcome. It is still partly a guess: scalar-target failure does not prove vector targets succeed.
- Under PPO, extra loss terms share the minibatch with the policy gradient; gradient interference is a risk. PPG's separate auxiliary phase is the known mitigation; a small weight (0.1-1x the value loss) and a head on the shared trunk is the simplest first try.
- Successor features need a feature set that is "game-agnostic" at card level; the pooled token embedding could play that role, but this is heavier and lower priority.

### Gaps
- No paper found that tests auxiliary losses under PPO with pointer/legal-option action spaces; searches for "auxiliary task interference in PPO" surfaced only Moalla 2024 and PPG.
- Cardsformer's training details unread.

Loop change: add an SPR-style head to ar/train.py. In `ppo_update`, a small MLP g(z_t, a_t) predicts stopgrad(z_{t+1}) where z is the pooled trunk embedding at the same player's next decision (index of next row with equal `traj`; mask rows with `done`), loss = 1 - cosine, weight about 0.5. Cost: about 30 lines, adds a second forward target pass (use the same micro-batch forward, targets from `old` or EMA copy), one 5-minute slot per weight. Obeys the rules: only game result, features and legal options; no hand-made quantity; carries to Magic. Why better than the failed heads: it supervises what the move did to the state (including a Trainer's draw/search), per move, rather than a scalar about the end.

## 4. Potential-based shaping with a learned potential; why Prize shaping biases toward tempo

### Takeaway
Dynamic potentials keep policy invariance if the potential at a state is evaluated consistently at entry and exit; shaping by an arbitrary score such as Prizes is not a potential unless written as a difference of a state function, and even then it only changes advantage timing, so a "never fading" Prize term that was applied as a reward is not invariant (consistent with the -31 Elo).

### Cited Findings
- Dynamic potential-based shaping: Phi_t may change during learning; shaping F_{t+1} = gamma*Phi_{t+1}(s') - Phi_t(s); policy-invariance guarantees hold (single- and multi-agent) when potentials are evaluated at the time of entering a state and used consistently — [Devlin & Kudenko 2012 (White Rose)](https://eprints.whiterose.ac.uk/75121/2/p433_devlin.pdf), summary via [search record](https://eprints.whiterose.ac.uk/75121). The proofs were not read; secondary summaries only.
- Potentials over state-action pairs (Wiewiora 2003) and arbitrary rewards as dynamic advice potentials (Harutyunyan, Devlin, Vrancx, Nowé 2015) extend this — [AAAI 2015 advice paper](https://ojs.aaai.org/index.php/AAAI/article/view/9628/9487)
- Bootstrapped reward shaping uses the learner's own value estimate as the shaping potential — [arXiv 2501.00989](https://arxiv.org/pdf/2501.00989) (abstract-level only)
- Potential shaping can be viewed as a gradient on the MDP — [Calculus on MDPs](https://arxiv.org/pdf/2208.09570)

### Inferences
- "Value as potential" with gamma = 1 and GAE: the shaped TD error r + V(s') - V(s) is the unshaped TD error, so using V itself adds nothing; it only helps if the potential is a different, faster-learning function (e.g. option count, or an auxiliary-head prediction), which then acts as a control variate.
- Prize difference as potential (Phi = my Prizes - opponent Prizes) is invariant in theory only if it is a state function; at gamma 1 it telescopes to final Prize margin, so it equals the outcome's margin and gives no new information about Trainers; empirically it paid tempo (attack now) over setup, as the run showed (-31 Elo, my reading of the assignment, not a cited fact).

### Gaps
- Could not verify the claim that terminal-potential telescoping preserves the policy under a non-zero terminal potential with reset-at-episode-end; standard treatment sets Phi(terminal) = 0 (memory).

Loop change: no new run; if item 1 is used, set Phi(terminal) = 0 and keep the term fixed (not faded), since a potential needs no fade. Confirm that the earlier Prize term was not potential-based before concluding anything from the -31 Elo.

## 5. Goal-conditioned and hindsight relabelling

### Takeaway
HER relabels a failed trajectory with a goal that was achieved, turning sparse binary reward into learning signal; it needs an off-policy learner and goals as states. For "fetch the card you later used" the generic equivalent is relabelling the goal as a feature of a future state, which is closer to a future-prediction auxiliary (item 3) than to HER itself, because PPO is on-policy.

### Cited Findings
- HER: store transitions with substituted goals so sparse binary rewards still teach; works with any off-policy algorithm; tested on robot push/slide/pick-and-place; ablations say it is essential there — [Andrychowicz et al. 2017](https://arxiv.org/pdf/1707.01495). Future-goal sampling is the common strategy in implementations ([garage HER buffer](https://garage.readthedocs.io/en/latest/_autoapi/garage/replay_buffer/her_replay_buffer/)).

### Inferences
- Under PPO, relabelled goals break on-policy ratios unless the policy is goal-conditioned and the importance weights are handled; no source here shows HER with PPO in card games (not found).
- A tractable version avoids goal conditioning: an auxiliary head that, at a Trainer decision, predicts which card kind/ID the same player plays in the next k decisions (target taken from the batch, a hindsight label). The pointer head already scores cards, so the target is a distribution over the card tokens in the current state. This forces the trunk to link "what I fetch" to "what I use", generic to Magic.
- Risk: the label is the policy's own future behaviour, so it can only be as good as the policy; it teaches consistency, not optimality. Benefit comes only if value/policy later use that link.

### Gaps
- No source for hindsight labels in TCGs; the specific head above is my design, not a published method.

Loop change: lowest priority. After item 3, add a second auxiliary head predicting a card set played within the next k own decisions (cross-entropy over the current tokens, weight 0.1-0.3). Cost: about 30 lines, one slot. Rules: obeys (derived only from play logs and tokens). Why it might beat the failed tries: it supervises the Trainer-to-use link directly at the Trainer decision. Not recommended until item 3 shows a positive M.

## Suggested order for the loop
1. Option-count potential (item 1): cheapest, theoretically safe, about 10 lines.
2. SPR-style next-decision embedding head (item 3): about 30 lines, best-supported mechanism.
3. Hindsight card-use head (item 5), then RND (item 2) only if both above fail. Run each alone for one ar slot at its stated weight; then the best pair.
