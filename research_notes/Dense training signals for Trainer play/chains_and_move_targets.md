# Chains of decisions that form one move, and per-move targets that train every link

Scope: about 9 web calls plus the two local notes (search_and_credit.md, sub_decisions_in_card_effects.md) and ar/train.py and probe_targets in rl/train.py, all read. Things I did not read in a primary source are marked "unverified". Facts about this project come from the brief and from the files read. Anything labelled "(inference)" is mine.

Project facts that drive the analysis (read from ar/train.py and rl/train.py):
- Every prompt is its own PPO row. The ratio, the clip and the entropy term are per row (ar/train.py lines 97-103), so there is no joint-ratio problem.
- GAE runs over one player's rows in a game with gamma 1, lambda 0.95, and no reward until the end (`advantages`, lines 49-59). A move's links get different advantages only because V changes between them.
- The soft search target (`probe_targets`, lines 116-137) holds, for a probed main-phase row, up to K=4 candidate options and the mean score of each from a 40-step lookahead. The loss is KL(softmax(log pi + clip((q - mean q)/tau, -1, 1)) || pi) over those candidates (lines 104-118). It is a clipped-advantage MPO target (the Muesli form), already a soft target.
- The candidate scores come from lines that play the candidate move and then continue with the policy. That means the score of "play Computer Search" already includes the policy's own random-quality answers to its sub-prompts (inference from the brief: the search skips the prompts inside Trainers, so those are played by the policy). I did not read the Node probe code to confirm.

---

## 1. Options, macro-actions and semi-MDP credit: treat "play + prompts" as one option or as separate steps?

### Takeaway
SMDP/options theory says a multi-step action can be one unit with one return, but with gamma = 1 and a terminal-only reward there is nothing to "bundle": value of the chain's links already telescopes. What matters is the intra-option, per-link signal; Sutton-Precup-Singh's intra-option learning and the language-agent paper POAD (token = link) both say to keep per-link values and apply no discount or reward inside the move. The project does this implicitly, except for the lambda < 1 inside the chain and the missing "source card" input.

### Cited Findings
- An option is a closed-loop policy for acting over an extended period; a set of options over an MDP forms a semi-MDP, and options can replace primitive actions in dynamic programming and Q-learning. Intra-option methods learn about an option from fragments of its execution, not only complete runs — [Sutton, Precup & Singh 1999](https://people.cs.umass.edu/~barto/courses/cs687/Sutton-Precup-Singh-AIJ99.pdf) (via search summary; the PDF was not read).
- Option-critic derives policy-gradient theorems for options and learns intra-option policies and termination functions together with the policy over options, with no extra rewards or subgoals — [Bacon, Harb & Precup 2017](https://arxiv.org/abs/1609.05140v2) (abstract-level). Here the "option" is fixed by the rules (the card), so the termination part is not needed: the engine says when the prompts end.
- POAD (Policy Optimization with Action Decomposition) treats each token of a language action as a step in a decomposed MDP. Intra-action tokens get no reward and no discount (gamma_w = 1). The action reward arrives at the last token, discounted by gamma_a, and V of each prefix passes forward. The paper proves this matches action-level Bellman optimality, and per-token GAE advantages feed a per-token clipped PPO loss — [Zhang et al., POAD, arXiv 2405.15821](https://arxiv.org/html/2405.15821v1).
- The same paper's naive token-level baseline (NTPO) discounts inside the action with gamma_w < 1. The discrepancy from action-level optimality grows with the number of tokens and vanishes only at gamma_w = 1; its gap to POAD widens as gamma_w drops from 0.95 to 0.5 (qualitative, no table values in the text read). POAD beat NTPO on 7 of 8 unseen Overcooked-style variants (e.g. Laundry 0.7014 vs 0.5687) — [POAD](https://arxiv.org/html/2405.15821v1). The domain is language agents, not card games.
- Local, not from the literature: lambda 1 within a turn cost -37 Elo (#95-100). A turn spans many moves; a move spans 1-3 prompts. These are different scopes, so POAD's rule is not the tried one.

### Inferences
- With gamma 1 and no intermediate reward, "one advantage for the whole chain" and "separate steps with lambda = 1 inside the move" are the same estimator. Separate steps with lambda 0.95 differ only by bootstrapping noise from a value head that does not know which card opened the prompt (the brief). The value head at the second link is the weak part: V after "discard 2 for Computer Search" cannot tell a good discard from a bad one if V is nearly the same for every discard. That is why more credit-sharing alone is unlikely to create a signal where V is flat (this is the same point the earlier note made about X1).
- Chain advantage is a variance device, not a signal source. The signal must come from a counterfactual (sections 3, 4).
- Loop change: in `advantages`, set lambda to 1.0 only between consecutive rows of the same move (rows whose prompt follows a Trainer opening, no new main-phase decision in between) and keep 0.95 elsewhere. Needs a "same move" flag per row; the rollout has the prompt type, and if no move id exists, a boundary can be taken as "next row is a main-phase decision". Cost: about 10 lines in ar/train.py, one 5-minute ar/ run per seed, three seeds. Obeys the rules (engine metadata only, game-agnostic: a spell in Magic also opens follow-up prompts). Why it differs from the failed lambda-1-within-a-turn: it spans 1-3 links, so the variance added is small, and POAD says it is the consistent choice. Expect a small effect (low confidence): it fixes bias, not missing signal. Rank it as a cheap sanity test, not the main hypothesis.

### Gaps
- No card-game paper found that compares "whole move = one option" against per-prompt steps. POAD is the nearest and is on text agents.
- I did not read the Sutton 1999 PDF or the option-critic text beyond the abstract.

---

## 2. Autoregressive action decomposition: how large agents assign advantage across sub-actions, and the PPO ratio

### Takeaway
Published large agents emit sub-actions in order with later heads conditioned on earlier ones. Recent work (2026) says autoregressive heads give the best score, and that giving each head its own centred advantage (a branching critic) beats a shared advantage in PPO. Your per-prompt rows already match the "separate loss per sub-action" form. What your design lacks is the conditioning information (which card opened the prompt) and a per-link advantage that measures the link, not the whole game.

### Cited Findings
- Flavin & Sen (arXiv 2606.26574, June 2026) compare six factorisations (independent, shared encoder, VDN, QPLEX, joint, auto-regressive) under PPO, SAC and DQN on four small environments. Auto-regressive gives the highest performance overall; branching dueling architectures give the best compute-performance balance; their VDN-PPO and PPO-MIX use a branching critic to assign credit across heads and beat the other PPO factorisations — [Flavin & Sen 2026](https://arxiv.org/abs/2606.26574). A third-party summary says each head's advantage is centred, weighted by its action probability, and that VDN-PPO weights heads by the range of each head's advantage function (secondary; the full paper was not read) — [search summary](https://arxiv.org/pdf/2606.26574). Environments are lightweight and hybrid discrete-continuous, not card games.
- OpenAI's write-up says the network has several action heads with semantic meaning (e.g. tick delay, target x/y); a Wikipedia summary says the heads are computed independently — [OpenAI Five](https://openai.com/research/openai-five), [Wikipedia](https://en.wikipedia.org/wiki/OpenAI_Five). How the heads' log-probs enter the PPO loss (one summed joint ratio with one advantage, from my memory) is unverified; I did not find it stated in a source I could read.
- AlphaStar's heads are autoregressive with a pointer network over entities (the previous note's sources). In AlphaStar Unplugged's MuZero, the full autoregressive action is embedded at the search root, but only the function and delay arguments are predicted at non-root nodes to save inference time; about 20 sampled actions sufficed for Sampled MuZero — [AlphaStar Unplugged](https://arxiv.org/pdf/2308.03526) (via search summary).
- A "joint action loss" paper argues the joint ratio of compound actions makes clipping zero out gradients and computes the loss per sub-action instead (unverified summary, from the previous note).
- The POAD loss is also per link: per-token ratios, per-token GAE advantages, averaged with weight 1/|a_t| per action — [POAD](https://arxiv.org/html/2405.15821v1).

### Inferences
- The project's per-row ratio is already the "per-sub-action" form. Nothing to change there.
- The remaining choice is the advantage each link receives. At present each row's advantage is `reward + V(next) - V(this)` plus the lambda-weighted tail, so a link's advantage is the change in value across that link, normalised across the whole batch (line 73). A link whose choice barely moves V gets advantage near zero plus noise, and the pooled normalisation lets main-phase rows dominate. Per-prompt-type normalisation (centre and scale the advantage within the group of rows sharing a prompt type, like a per-head centred advantage) is the cheap analogue of the branching critic. It stops the 7-8 shared Trainer prompt types from being drowned by the high-variance main-phase rows. (inference)
- Loop change: normalise `adv` by group instead of by the whole batch: for rows of each prompt type (and, once the source-card token is added, each source card), subtract the group mean and divide by the group std (with a minimum count of about 30, else fall back to the batch statistics). About 8 lines in `ppo_update`. Cost: one 5-minute ar/ run per seed. Obeys the rules (groups come from engine prompt metadata; no card kind is read). Why it can help where lambda 1 did not: it changes how loud the in-Trainer rows are, not the bias. Risk: dividing a near-zero-signal group by its small std amplifies noise into random drift, so cap the scale and log per-type KL. Evidence is indirect (Flavin & Sen is on toy tasks), so confidence is low.

### Gaps
- No readable primary text for how AlphaStar or OpenAI Five weight head log-probs. No card-game ablation of per-head advantages found.
- The Flavin & Sen mixing details come from a summary, not the paper body.

---

## 3. Per-step Q targets from search applied to sub-decisions

### Takeaway
The soft target machinery (Gumbel completed-Q, clipped MPO) works at any node where options can be enumerated and scored from the same state, and the sub-prompts are such nodes. The key finding for your problem is structural: a move-level Q for "play Trainer X" averages over whatever the policy then answers, so a poor answer policy lowers Trainer X's apparent value and the policy cannot learn that Trainer X is good. Scoring a Trainer move with the best of several follow-up answers (the BAD / Q-learning max over the next sub-step), and searching the prompt itself, attacks both.

### Cited Findings
- Gumbel MuZero targets: pi' = softmax(logits + sigma(completedQ)) with unvisited actions given a mixed value, so they get zero advantage; it learns with 2 simulations where MuZero fails at 16 or fewer on 9x9 Go; Gumbel top-k sampling without replacement plus sequential halving guarantees improvement when Q is correct — [Danihelka et al., ICLR 2022](https://openreview.net/forum?id=bERaNdoegnO) (read in the previous note). Muesli's CMPO target, with total-variation distance to the prior at most tanh(c/2), is the form ar/train.py uses — [Hessel et al. 2021](https://arxiv.org/abs/2104.06159).
- Sampled MuZero extends policy improvement to a sampled subset of a large action set with a correction for the sampling distribution — [Hubert et al. 2021](https://ar5iv.labs.arxiv.org/html/2104.06303). Multi-agent Gumbel MuZero combines this with Gumbel for combinatorial action spaces and reports an up to order-of-magnitude reduction in environment interactions versus model-free methods — [Hao et al., AAAI 2024](https://mlanthology.org/aaai/2024/hao2024aaai-multiagent).
- Kwak et al. (UAI 2024) target MCTS for factored actions (each action is several sub-actions): a learned state-conditioned abstraction drops sub-actions that do not matter for the transition, improving sample efficiency over vanilla MuZero — [Kwak et al. 2024](https://proceedings.mlr.press/v244/kwak24a.html). It is a learned-model setting; the project's lookahead uses the real engine.
- Magic: Cowling, Ward & Powley turned move generation into a binary yes/no decision tree searched by MCTS, with significant strength gains over basic determinized MCTS — [Cowling et al. 2012](https://eprints.whiterose.ac.uk/75050/). A York thesis is the nearest to "sub-prompt search" and predates 2024. I found no 2024-2026 card-game paper on searching target selection for training.
- BAD's backup takes the max over the next sub-step for Q inside an action, and the action reward arrives at the last link — [POAD](https://arxiv.org/html/2405.15821v1).
- SPARTA deviates from the blueprint only when search beats the blueprint action by a margin and prunes options not within 2 SD of the best — [Lerer et al. 2020](https://arxiv.org/abs/1912.02318) (read in the previous note).
- Local, from the previous note: random answers to the pilot's Trainer prompts change nothing (+0.002 +/- 0.009, 6,080 games per variant, X1), and the lists' Trainers only tie a near-blank card.

### Inferences
- Two different gaps (inference, from the probe code and the brief):
  1. Link-1 gap: the main-phase probe scores "play Computer Search" with the policy's own near-random follow-ups. Trainer value is understated, and the target teaches "Trainers are worth about a blank card", which matches X5 (+0.062 for a near-blank card over basic Energy, and the lists' Trainers only tying it). This is a possible cause of the Trainer plateau that sits upstream of the prompt answers. Not yet shown; check before building (see the diagnostic below).
  2. Link-2/3 gap: no target at the prompts themselves.
- Both gaps can be closed with allowed machinery: the targets come from search used as policy improvement inside self-play with a soft KL target, as already used at 5%. They are not fixed labels from an oracle.
- Costs. A prompt probe copies the existing probe: K candidates (Gumbel top-k from the policy, K 4) x lines x 40 steps. Prompts inside Trainers are a small share of rows, so a probe rate near 5% of them costs about the same lookahead budget as today's probes; I did not measure the share of rows (a gap).
- Diagnostic first (30 minutes, no training): at in-Trainer prompts, record the spread max-min of candidate means, as for main-phase probes (`q_spread_median` in `probe_targets`). If the spread is not clearly above the noise (use the repeat-line SE), the choices do not matter and the training effort belongs elsewhere (Trainer valuation). This was also proposed in the earlier note; it is the gate for the changes below.
- Loop change A (link-2/3 targets, the main one): extend the probe to prompts that follow a Trainer, sample candidates with Gumbel top-k from the policy (not the top 4), score each with the existing 40-step lookahead from that state, and feed `probe_c/probe_q` into the existing soft KL loss with the existing tau and clip. Needs the Node-side probe to fire at those prompts (not read; engine-side change in the worker) plus a source-card token so the prompt is identifiable. Cost: engine edit plus a 70-minute screen; read-out is X1 re-run (6,080 games) and the sd_kl by prompt type. Obeys the rules: lookahead used as in-loop improvement, soft target, no human data, no card kinds; game-agnostic (any spell with follow-up choices). Why it can beat #96: soft clipped-advantage target at weight 20 only on 5% rows, bounded by tanh(c/2), not a hard one-hot at 10-25% of rows with gradient norm 27.
- Loop change B (link-1 gap, cheaper): when a main-phase candidate is a move that opens prompts, score each line with the best of n sampled follow-up answers (for example n = 3, taking the line with the best lookahead score) instead of one policy answer. This is the Q-max backup in BAD, applied inside the existing probe lines, at roughly n times the cost on those lines only. It gives a better Q for "play Trainer X" and so a better first-link target. Risk: optimiser's curse bias (the max of noisy scores is biased upward) shared by all Trainer candidates, which makes Trainers look better than non-Trainer moves in the targets; keep the non-Trainer candidates at equal n, using a random n-fold best for them too is impossible, so the bias is real. Mitigation: use more lines per candidate (cost). Also needs the Node probe edit. Rank it below A.

### Gaps
- No published training result of searching the sub-prompts of a played card in a card game.
- Share of rows that are in-Trainer prompts, and the probe cost per row, not measured.
- Whether the Node probe can branch at a mid-Trainer state (rather than only at main-phase rows) is unverified; it is the main feasibility risk.

---

## 4. Q-based critics over (state, action) for many-option prompts (DouZero-style) as a per-option signal

### Takeaway
DouZero trains Q(state, action-features) with plain Monte Carlo returns and no bootstrapping, and it works in a long, sparse-reward card game. Your pointer head already scores each legal option; adding a Q-regression loss on the taken option gives each option its own learning target, but with terminal-only reward the target for any single prompt choice is the whole game's result, which is exactly as noisy as the current advantage. The Q-critic helps only if paired with a counterfactual (search) or a lower-variance return, so it is a modest change on its own.

### Cited Findings
- DouZero (Zha et al., ICML 2021) uses Deep Monte Carlo with action encoding. It argues that bootstrapping is slow in long, sparse-reward DouDizhu (the Q at one state must wait for the next state's value to converge), that Monte Carlo convergence does not depend on episode length, and it offsets high variance with many parallel actors (45 actors, 4 GPUs); it reports DQN as unstable — [Zha et al. 2021](https://arxiv.org/abs/2106.06135) (read in the earlier note).
- PerfectDou's critic sees hidden information in training; it needed about 10x fewer samples than DouZero, helped by a game-specific dense reward — [Yang et al. 2022](https://arxiv.org/abs/2203.16406).
- Branching/dueling Q networks (shared state value plus per-head advantage streams) were the best compute/performance trade-off in the 2026 comparison — [Flavin & Sen](https://arxiv.org/abs/2606.26574).
- Local: the pointer head scores the legal options from the same encoder (task brief); the value head V is separate.

### Inferences
- Per-option Q targets from a terminal result have the same signal-to-noise as GAE with lambda 1. So a Q head is not a new source of information. Its value would be in learning from the search scores: regress the head on the lookahead mean for each probed candidate (this is the Gumbel / Muesli "Q-head from search" step, AlphaZero-style improvement inside self-play) in addition to the soft KL on the policy. Those are lower-variance, per-option, per-prompt targets, and they would give the chain's links a value function over options. (inference)
- Cost and risk: an extra head or reuse of the pointer logit as Q. The risk is that regressing logits to Q interferes with the policy gradient (the logit is both a policy score and a Q), so use a separate small head on the option embeddings.
- Loop change: only after Loop change A works. Add `q_head(option embedding) -> scalar`, trained with MSE on `probe_q - mean(probe_q)` for the candidates, weight about 1; no use in the actor at first (diagnostic: does its ranking agree with later outcomes?). Cost: about 25 lines plus the same 70-minute screen as A, no extra game cost. Obeys the rules. Evidence: indirect (Gumbel/Muesli compute Q from search for the target); no card-game precedent found. Do not run it alone.

### Gaps
- No readable evidence that action-feature Q critics beat advantage critics when the per-decision effect is small. Nothing on Q-critics for sub-prompts of a played card.

---

## 5. What fits a 5-minute ar/ loop and what needs a 70-minute screen

### Takeaway
Estimator changes inside `advantages` / `ppo_update` fit the 5-minute loop (three seeds to clear noise, about 15 minutes of wall time per variant). Anything that needs the Node worker to probe at a new kind of row, or a new head, needs the screen. Run the free diagnostics first.

### Cited Findings
- (all costs are my estimates from the code size and the brief, not measured)
- Estimator changes need only ar/train.py: sections 1 and 2.
- Search-target changes need the worker probe to fire at in-Trainer prompts and to branch a mid-Trainer state: section 3, unverified as feasible.
- The decisive readout already exists: X1 (random vs policy answers, 6,080 games per variant, +0.002 +/- 0.009 at baseline) and X5 (A2 Trainer-vs-blank-card test).

### Inferences
Order (cost-weighted, my judgement):
1. Diagnostic, no training: spread of candidate scores at in-Trainer prompts, and the per-prompt-type normalised entropy, advantage std and KL (log in ar/train.py). It tells which gap exists. 30-60 minutes.
2. 5-minute loop: lambda 1 within a move (section 1) and group-normalised advantage (section 2), three seeds each. Add the source-card token first if not yet merged, since both depend on identifying the prompt.
3. 70-minute screen: Loop change A (soft targets at in-Trainer prompts), then B (best-of-n follow-ups) if the diagnostic shows the move-level Q understates Trainers, then the Q head.
Caution: the A2 result (a near-blank card ties the lists' Trainers) says the Trainer value, not only the prompts, is the shortfall; B and the diagnostic address the value, A addresses the prompts.

### Gaps
- No timing data for probe cost at prompts; whether the worker can fire a probe there is unchecked.
