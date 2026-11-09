# Oracle critics and dense per-move signals in card games (for the Trainer-chain problem, log #241)

Scope note: about 10 searches/fetches. The PerfectDou and Suphx PDFs would not parse, so I used ar5iv text. Anything marked (memory) is from my own background knowledge, not verified this session. I did not re-read the project's earlier notes (search_and_credit.md, Audit A1); I read only ar/train.py (PPO, GAE 0.95, gamma 1, terminal reward, search-distillation at about 5% of main-phase decisions; the value head shares the trunk and sees only the pilot's observation).

## 1. Oracle / privileged critics: how much do they help, and do they fix credit for draw/search actions?

### Takeaway
Privileged critics are proven unbiased and are the standard card-game recipe (PerfectDou, Suphx), but the measured gains are modest and no paper shows they fix credit on information-gathering actions specifically. PerfectDou's own ablation puts the perfect-vs-imperfect critic gap at about 0.09 ADP, against about 0.78 ADP for its dense reward. An oracle critic removes noise from hidden-state luck; it cannot make a "fetch the right card" choice distinguishable unless the critic's value is sharp in the post-fetch state.

### Cited Findings
- PerfectDou: the value network gets imperfect features plus the other players' hand cards; the policy gets only imperfect features. PPO + GAE. — [PerfectDou (ar5iv)](https://ar5iv.labs.arxiv.org/html/2203.16406); [NeurIPS 2022](https://neurips.cc/virtual/2022/poster/55314)
- PerfectDou ablation (Table 4, 100k decks, vs DouZero ~1e9 steps, WP/ADP): PerfectDou 0.732/1.270, ImperfectDou 0.717/1.180, RewardlessDou 0.738/0.490, vanilla PPO 0.509/-0.307. Against the stronger DouZero ~1e10: PerfectDou (1e9) 0.524/0.014 vs ImperfectDou 0.486/-0.057. — [PerfectDou (ar5iv)](https://ar5iv.labs.arxiv.org/html/2203.16406)
- PerfectDou's dense reward is game-specific: change in each player's minimum steps to play out all cards, scale 50, removed for final fine-tuning on ADP only. The paper says both "after a round" and "at each node". — [PerfectDou (ar5iv)](https://ar5iv.labs.arxiv.org/html/2203.16406)
- PerfectDou handles many-option choices with an action-feature policy: a 12x15 card matrix plus 7 flags per action, concatenated with the state encoding, MLP, softmax over legal actions; 27,472 combinations abstracted to 621. This is the same pointer-over-options design as the pilot. — [PerfectDou (ar5iv)](https://ar5iv.labs.arxiv.org/html/2203.16406)
- Suphx oracle guiding: train an oracle agent with all hidden features (others' tiles, wall), then decay a Bernoulli keep-probability from 1 to 0 so it becomes a normal agent; needed lr/10 and importance-weight rejection for stability. No numeric ablation in the text, only a stable-rank figure (RL-basic < RL-1 < RL-2). — [Suphx (ar5iv)](https://ar5iv.labs.arxiv.org/html/2003.13590)
- Suphx is not human-free: all models were supervised-pretrained on Tenhou top-player logs, and the reward predictor was trained on human logs. — [Suphx (ar5iv)](https://ar5iv.labs.arxiv.org/html/2003.13590)
- Asymmetric actor-critic (Pinto et al.): critic sees full simulator state, actor sees images; speeds up training (DDPG). — [arXiv 1710.06542](https://arxiv.org/abs/1710.06542)
- Theory: Baisero and Amato (AAMAS 2022) show the common state-only asymmetric critic can be biased in partially observable problems; a history+state critic keeps the policy-gradient theorem valid. — [Baisero & Amato 2022](https://www.khoury.northeastern.edu/home/abaisero/assets/publications/repository/baisero_unbiased_2022.pdf); [arXiv 2105.11674](https://ar5iv.labs.arxiv.org/html/2105.11674)
- Informed Asymmetric Actor-Critic (Ebi et al., listed as ICML 2026): any privileged signal that depends on the true state gives an unbiased gradient; variance may fall but easier learning is not guaranteed; informativeness can be tested (HSIC, or held-out return-prediction gain). On six small POMDPs (20 runs) it usually matches or beats the full-state critic. — [arXiv 2509.26000](https://arxiv.org/html/2509.26000v2)
- AlphaStar: the value baseline gets extra information including opponent observations while the policy sees a human-like view. Confirmed only by a secondary wiki; I did not read the Nature text. — [aiwiki AlphaStar](https://aiwiki.ai/wiki/alphastar/raw)
- Future-conditional value baselines are provably low variance if the hindsight information carries nothing about the agent's action; this is the formal route to using revealed hidden info as a baseline. — [Mesnard et al. 2021](https://arxiv.org/pdf/2011.09464); [Harutyunyan et al. 2019](https://papers.NeurIPS.cc/paper_files/paper/2019/file/195f15384c2a79cedf293e4a847ce85c-Paper.pdf)

### Inferences
- The pilot's shared-trunk value sees only the pilot's observation, so opponent hand, deck order and prizes are pure noise to it. A PerfectDou-style oracle value removes that. PerfectDou's +0.09 ADP suggests a modest effect, so an oracle critic alone is unlikely to fix the Trainer chain.
- Credit for "what to fetch" requires V to differ between post-fetch states. A blind V gives A vs B about the same value, so advantage is noise. An oracle V sees the deck, hand and opponent, so it could separate them, but V must still learn what Trainer cards do, which is what log #241 says is not learned. Test whether the oracle V's change across a fetch tracks search-probe Q before building anything big.
- Suphx-style decay of oracle features into the actor is more complex and was unstable without tricks; the PerfectDou asymmetric-critic form is the better first test.

### Gaps
- No paper found that measures oracle-critic effect on credit for tutor/draw/search actions.
- Suphx oracle-guiding numeric gain is in a figure only; AlphaStar primary text not read.

## 2. Card-game agents without human data: per-move signal, and what made setup/tutor cards learnable

### Takeaway
Of the strong agents, DouZero and PerfectDou are human-data-free in their main training, and both use win/loss or point-difference returns, plus PerfectDou's hand-built step-count reward. I found no RL paper for Pokemon TCG and no published MTG/Hearthstone agent that solved tutor/setup-card play; how those cards become learnable appears unreported.

### Cited Findings
- DouZero: reward only at the end (+1/-1 WP or point difference ADP), gamma 1; Deep Monte-Carlo trains a Q-network on (state, action encoding) against full-episode returns; 30 days on 4 GPUs from scratch, beat the human-supervised baseline in about 2 days and DeltaDou in about 10. The supervised baseline used 226,230 human games and bidding was supervised. — [DouZero (ar5iv)](https://ar5iv.labs.arxiv.org/html/2106.06135)
- DouZero's reasons for MC-Q: DQN overestimates/diverges with big variable action sets; policy-gradient classifiers cannot use action features; MC variance is offset by parallelism. Its own actor-critic variant failed and SARSA was slightly slower (Figure 7). — [DouZero (ar5iv)](https://ar5iv.labs.arxiv.org/html/2106.06135)
- DouZero+ adds opponent modelling and a coach network. — [arXiv 2204.02558](https://arxiv.org/pdf/2204.02558)
- ReBeL: self-play RL plus search, no human data, heads-up no-limit hold'em. — [ReBeL NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/c61f571dbd2fb949d3fe5ae1608dd48b-Abstract.html). That its per-decision target is a search-derived belief-state value is from memory.
- Student of Games: guided search (GT-CFR) with self-play learning, unified across perfect and imperfect information; strong in chess, Go, poker, Scotland Yard. — [Schmid et al. arXiv 2112.03178](https://arxiv.org/pdf/2112.03178)
- Other card-game RL found: Legends of Code and Magic draft agents; Dominion SAC agent (2023); Hearthstone AAMAS 2025 abstract (T5 card-text encoder + self-play); MTG-Causal-RL benchmark (arXiv 2605.06066, May 2026: 478 masked actions, CGFA-PPO about 0.78 vs a heuristic bot on Mono-Red Aggro, roughly tied with plain PPO). — [Dominion](https://ojs.aaai.org/index.php/AIIDE/article/view/27518); [AAMAS 2025](https://aamas.csc.liv.ac.uk/Proceedings/aamas2025/pdfs/p2795.pdf); [MTG-Causal-RL](https://arxiv.org/pdf/2605.06066); [LoCM draft](https://www.sbgames.org/proceedings2021/CTDMestrado/218333.pdf)
- No Pokemon TCG RL paper appeared in the searches.

### Inferences
- The per-move-resolution signals that scale are search/rollout values (ReBeL, SoG; the project's probe distillation) and MC-Q on action features (DouZero). Neither needs a shaped game reward. This favors extending the existing probe, now on about 5% of main-phase decisions only, to Trainer sub-prompts.
- DouZero's actions are single plays; a deck-search choice inside a card effect is a sub-decision with no precedent I found.

### Gaps
- No evidence on how any TCG agent learned tutor/setup cards. ReBeL/LoCM details beyond abstracts not verified.

## 3. Value-difference ("win probability added") rewards from an evaluator

### Takeaway
Suphx is the closest published case: the round score is replaced by the change in a learned predictor of the final result, but the predictor was trained on human logs. The human-free generic version is the same change-of-value reward with the agent's own (oracle) value, i.e. potential-based shaping.

### Cited Findings
- Suphx global reward prediction: GRU predictor Phi trained by MSE on final game reward; the per-round RL reward is Phi(x_k) - Phi(x_{k-1}). — [Suphx (ar5iv)](https://ar5iv.labs.arxiv.org/html/2003.13590)
- PerfectDou's dense reward is also a difference of an evaluator and was the largest ablation effect (section 1). — [PerfectDou (ar5iv)](https://ar5iv.labs.arxiv.org/html/2203.16406)

### Inferences
- Potential-based shaping leaves optimal policies unchanged (Ng, Harada, Russell 1999; memory, not fetched). With gamma 1 and Phi equal to the agent's own value, the per-step advantage is GAE with lambda 0, and the project's failed tests (lambda 1 in a turn, prize shaping that never fades, aux heads; #95-#100) used same-trunk quantities. The new ingredient here would be a better Phi (oracle-trained), untested.
- Win-probability-added is only as accurate as Phi on the specific change. A fetch changes the hand by one card; if V cannot resolve that (log #241), the delta is noise.

### Gaps
- No chess/sports centipawn-loss-as-training-reward paper read.

## 4. Q on action features (DouZero DMC) versus policy-gradient credit for many-option choices

### Takeaway
DouZero's Q(state, action encoding) regressed on Monte-Carlo returns gives each option its own regression target with weights shared through the action encoding, and the authors chose it over actor-critic, which failed for them. It still regresses on terminal-return variance, so on Trainer sub-prompts it has the same noise problem unless the target is less noisy.

### Cited Findings
- DouZero says policy gradients cannot use action features and that its actor-critic variant failed. — [DouZero (ar5iv)](https://ar5iv.labs.arxiv.org/html/2106.06135)
- PerfectDou gets action-feature generalisation inside a PPO policy (state encoding concatenated with each action encoding) and beats DouZero (about 52% win vs DouZero ResNet, from the repo README, self-reported). — [PerfectDou](https://ar5iv.labs.arxiv.org/html/2203.16406); [godmoves/perfectdou](https://github.com/godmoves/perfectdou)

### Inferences
- The pilot's pointer head is already an action-feature policy, so DouZero's architectural argument does not apply. The difference is the target: DMC gives every legal option a target, PPO gives only the chosen option a scalar advantage. A Q-head on the same option embeddings could be trained from the same rollouts as an auxiliary, cheap but with terminal-return noise, so by itself it likely will not beat the pointer logits.

### Gaps
- No comparison found of Q-regression vs advantage policy gradient on sub-decisions inside a card effect.

## Loop change:
Ranked by cost. All are game-agnostic and use no human data.

1. Diagnostic first (about 1 hour, no training). On stored Trainer-prompt decisions, compare V(after chosen) - V(before), for the current blind V and for an oracle V (item 2), against the search-probe Q on the same decision. If only the oracle V ranks options, the oracle critic is the fix. If neither does, the problem is V's knowledge of Trainer effects, not variance. Obeys the rules (analysis only).
2. Oracle critic (PerfectDou form), the main experiment. Add a second value head whose extra input is hidden state the Node engine already holds (opponent hand, own deck contents and order, prizes) as extra tokens. Use it only in `advantages` (ar/train.py) for GAE and returns; the policy and the deployed pilot never see it. Cost: one rollout-export change in the engine/rollout code, which means a new `--setup` and `--calibrate` for ar/fixed.py, then about one 5-minute ar run per variant. Obeys the rules (generic, training-only). It helps the chain by removing opponent-hand and deck-order noise from every advantage and by letting V see deck contents, the one thing a search choice changes. Expect a modest gain (PerfectDou +0.09 ADP), so treat it as variance reduction, not a cure. The earlier value cross-attention to the deck (-1 Elo, #89) gave a blind value the deck list, not the opponent's hidden state, so it does not rule this out.
3. Extend the search probe from 5% of main-phase decisions to every Trainer sub-prompt (fetch, discard), reusing the soft-target KL already in `ppo_update` (rows with `probe_c`). This is the ReBeL/SoG-style per-move search value, and each option gets its own target as in DouZero's DMC. Cost: probe time scales with the number of Trainer prompts, so time a pilot (launch-run) first and start at a low fraction. Obeys the rules (the game's own rollouts). It is the most direct answer to Evan's request for a signal that matches game moves more closely than win/loss.
4. Only if 2 shows a clear gain: Suphx-style decay of oracle features into the actor. More complex and unstable in the paper; otherwise skip.
5. Lower priority: value-difference reward using the oracle V as Phi (potential-based; closest to Suphx reward prediction). Distinct from the failed #95-#100 variants but ranked below 2 and 3.
